"""
Reader for the per-application static-analysis artefact.

One `<apk>.json` per application carries what the static pass found: the
manifest's `components`, the call-graph `reachability` of every method, the GUI
`windows` with their widgets and listeners, and the window `transitions`. It is
the sole static input of the analysis layer. **`*.mop.json` is never opened**
(INV-CAN-24): that file is the derived artefact the jar consumes, and reading it
here would make the analysis depend on the derivation it is supposed to be able
to audit. `read` refuses such a path by name rather than by convention.

**The size covariate.** `sa_methods_reaches_mop` is the count of
`reachability[].methods[].reachesTarget` — the number of methods from which a
monitored operation is reachable. An application's opportunity to violate scales
with it, so it is the offset a count model needs; the prior-art survey recorded
it as requiring a fresh Soot pass per application, and for this corpus that pass
is already in the artefact.

**The handler verdict is three-way and `unresolved` is first-class.** A widget's
listener names a handler signature; the reachability index either carries that
signature and says whether it reaches a monitored operation (`hot` / `cold`), or
does not carry it at all (`unresolved`). Folding `unresolved` into `cold` was
measured to move the answer by a third of all handlers, which is why the honest
output of this reader is an interval and not a point.

**`complete: true` is not a quality signal.** The producer asserts completeness
on truncated output — an application whose raw `transitions` list is empty may
still declare itself complete. The flag is carried because the artefact carries
it, and it is never read as evidence that the analysis finished. The raw
`transitions` count is carried beside it for exactly that reason.

Offline and read-only over recorded artefacts (INV-APV-35): no device, and
nothing is written.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

#: The derived artefact this reader must never open, by name (INV-CAN-24).
FORBIDDEN_SUFFIX = ".mop.json"

#: Strata over the fraction of activities from which a monitored operation is
#: reachable. `inert` and `saturated` are the two ends a comparison cannot
#: measure anything in — an effect that can only exist where there is substrate
#: shows up diluted when they are pooled with the middle.
STRATA = ("no_activities", "inert", "rare", "discriminative", "saturated")

_SATURATED_ABOVE = 0.8
_RARE_BELOW = 0.2

#: Component groups of the manifest section, in the artefact's own key order.
_COMPONENT_GROUPS = ("activities", "receivers", "services", "providers")


class MopArtifactRefused(ValueError):
    """A caller pointed this reader at a `*.mop.json` (INV-CAN-24).

    Raised by name rather than silently tolerated: the derived artefact and the
    full artefact have overlapping key names, so a reader that accepted one for
    the other would return plausible numbers computed over the wrong file.
    """


@dataclass(frozen=True)
class HandlerVerdict:
    """Widget-listener handlers, resolved against the reachability index.

    Attributes:
        distinct: Distinct handler signatures across every widget of every
            window.
        hot: Handlers the index carries and that reach a monitored operation.
        cold: Handlers the index carries and that do not.
        unresolved: Handlers absent from the index. First-class: it is neither
            a hot nor a cold verdict, and merging it into `cold` understates the
            interval the data supports.
    """

    distinct: int
    hot: int
    cold: int
    unresolved: int


@dataclass(frozen=True)
class TreeSkips:
    """What a tree walk passed over, by reason.

    Attributes:
        mop_artefacts: Derived `*.mop.json` files met and refused. The reader
            walks past them rather than never meeting them, so the refusal is a
            number instead of a claim.
        unrecognised: Files matching the artefact pattern that are neither the
            full artefact nor the derived one. Zero under the current naming;
            counted so a future third artefact is visible rather than silent.
    """

    mop_artefacts: int
    unrecognised: int


@dataclass(frozen=True)
class StaticFacts:
    """What one application's static artefact says about it.

    Attributes:
        apk: Application file name, as the artefact's own file name carries it.
        package: Application package.
        main_activity: Launcher activity class.
        activities: Declared activities.
        activities_reaching: Activities from which a monitored operation is
            reachable.
        activities_exported: Activities the manifest exports.
        receivers, services, providers: Counts of the other component groups.
        receivers_reaching, services_reaching, providers_reaching: The same
            groups, restricted to those reaching a monitored operation.
        entry_points: Target-method names across every component, counted — the
            distribution that says whether reaching a screen is enough to fire a
            monitor or whether the screen has to be operated.
        reach_classes: Classes in the reachability index.
        sa_methods: Methods in it.
        sa_methods_reaches_mop: **The size covariate**: methods from which a
            monitored operation is reachable.
        sa_methods_directly_reaches_mop: Methods that call one directly.
        windows, windows_activity, windows_dialog, windows_menu: GUI windows,
            total and by type.
        widgets: Widgets across every window.
        listeners: Listener entries across every widget.
        handlers: The three-way handler verdict.
        transitions: Raw window transitions in the artefact. Zero is the
            truncation predicate, and it is a different quantity from the
            click-only edge count the derivation produces.
        complete: The producer's own completeness flag, carried and never read
            as a quality signal.
        fraction_activities_reaching: `activities_reaching / activities`, or
            None when the application declares no activity — never 0.0, which
            would put a degenerate application in the `inert` stratum.
        stratum: One of `STRATA`.
    """

    apk: str
    package: str
    main_activity: str
    activities: int
    activities_reaching: int
    activities_exported: int
    receivers: int
    receivers_reaching: int
    services: int
    services_reaching: int
    providers: int
    providers_reaching: int
    entry_points: Mapping[str, int]
    reach_classes: int
    sa_methods: int
    sa_methods_reaches_mop: int
    sa_methods_directly_reaches_mop: int
    windows: int
    windows_activity: int
    windows_dialog: int
    windows_menu: int
    widgets: int
    listeners: int
    handlers: HandlerVerdict
    transitions: int
    complete: bool
    fraction_activities_reaching: float | None
    stratum: str


def _load(apk_json: Path) -> dict[str, Any]:
    """Load the artefact, refusing the derived one by name (INV-CAN-24)."""
    if apk_json.name.endswith(FORBIDDEN_SUFFIX):
        raise MopArtifactRefused(
            f"{apk_json}: the derived MOP artefact is never read by the analysis "
            "layer; the full static artefact is the sole static input"
        )
    return json.loads(apk_json.read_text(encoding="utf-8"))


def _signature_index(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Index every reachability method by its signature, in one pass.

    The signature is the join key against the executed-method stream and against
    a widget's handler, and it is used by exact string equality in both places.
    """
    index: dict[str, Mapping[str, Any]] = {}
    for entry in document.get("reachability") or []:
        for method in entry.get("methods") or []:
            signature = method.get("signature")
            if signature:
                index[signature] = method
    return index


def _entry_point_names(document: Mapping[str, Any]) -> Counter[str]:
    """Count the target-method names every component declares.

    A `targetMethods` entry is a full signature; the name is what distinguishes
    a monitor that fires on arrival (`onCreate`) from one that needs the screen
    to be operated. A signature that does not decompose is counted under `?`
    rather than dropped.
    """
    names: Counter[str] = Counter()
    components = document.get("components") or {}
    for group in _COMPONENT_GROUPS:
        for component in components.get(group) or []:
            for signature in component.get("targetMethods") or []:
                try:
                    names[
                        signature.split(":")[1].strip().split("(")[0].split(" ")[-1]
                    ] += 1
                except IndexError:
                    names["?"] += 1
    return names


def _stratum(activities: int, fraction: float | None) -> str:
    """Label an application by how much of it can reach a monitored operation."""
    if activities == 0 or fraction is None:
        return "no_activities"
    if fraction == 0.0:
        return "inert"
    if fraction > _SATURATED_ABOVE:
        return "saturated"
    if fraction < _RARE_BELOW:
        return "rare"
    return "discriminative"


def read(apk_json: Path | str) -> StaticFacts:
    """
    Read one application's static artefact.

    Args:
        apk_json: The `<apk>.json` written by the static pass. Not written to.

    Returns:
        The application's facts, including the size covariate and the three-way
        handler verdict. Absent sections yield zeros rather than an exception:
        an application with no GUI window is a measurement, not a damaged file.

    Raises:
        MopArtifactRefused: The path names a `*.mop.json` (INV-CAN-24).
        OSError: The file cannot be read.
        json.JSONDecodeError: The file is not the artefact.
    """
    apk_json = Path(apk_json)
    document = _load(apk_json)
    index = _signature_index(document)

    components = document.get("components") or {}
    groups = {group: list(components.get(group) or []) for group in _COMPONENT_GROUPS}
    reaching = {
        group: sum(1 for item in items if item.get("reachesTarget"))
        for group, items in groups.items()
    }

    methods = 0
    reaches = 0
    directly = 0
    for method in index.values():
        methods += 1
        reaches += bool(method.get("reachesTarget"))
        directly += bool(method.get("directlyReachesTarget"))

    windows = list(document.get("windows") or [])
    widgets = 0
    listeners = 0
    handlers: set[str] = set()
    for window in windows:
        for widget in window.get("widgets") or []:
            widgets += 1
            for listener in widget.get("listeners") or []:
                listeners += 1
                handler = listener.get("handler")
                if handler:
                    handlers.add(handler)

    hot = 0
    cold = 0
    unresolved = 0
    for handler in handlers:
        method = index.get(handler)
        if method is None:
            unresolved += 1
        elif method.get("reachesTarget"):
            hot += 1
        else:
            cold += 1

    activities = len(groups["activities"])
    fraction = reaching["activities"] / activities if activities else None

    return StaticFacts(
        apk=apk_json.name[: -len(".json")],
        package=document.get("package") or "",
        main_activity=document.get("mainActivity") or "",
        activities=activities,
        activities_reaching=reaching["activities"],
        activities_exported=sum(
            1 for item in groups["activities"] if item.get("exported")
        ),
        receivers=len(groups["receivers"]),
        receivers_reaching=reaching["receivers"],
        services=len(groups["services"]),
        services_reaching=reaching["services"],
        providers=len(groups["providers"]),
        providers_reaching=reaching["providers"],
        entry_points=dict(_entry_point_names(document)),
        reach_classes=len(document.get("reachability") or []),
        sa_methods=methods,
        sa_methods_reaches_mop=reaches,
        sa_methods_directly_reaches_mop=directly,
        windows=len(windows),
        windows_activity=sum(1 for w in windows if w.get("type") == "ACTIVITY"),
        windows_dialog=sum(1 for w in windows if w.get("type") == "DIALOG"),
        windows_menu=sum(1 for w in windows if w.get("type") == "OPTIONSMENU"),
        widgets=widgets,
        listeners=listeners,
        handlers=HandlerVerdict(
            distinct=len(handlers), hot=hot, cold=cold, unresolved=unresolved
        ),
        transitions=len(document.get("transitions") or []),
        complete=bool(document.get("complete", False)),
        fraction_activities_reaching=fraction,
        stratum=_stratum(activities, fraction),
    )


def signatures(apk_json: Path | str, *, reaching_only: bool = False) -> frozenset[str]:
    """
    The artefact's method signatures, for the exact-equality join.

    Args:
        apk_json: The `<apk>.json`. Not written to.
        reaching_only: Whether to keep only the methods that reach a monitored
            operation. Which set was taken is the caller's decision and belongs
            in the report beside the number it produced.

    Returns:
        The signatures, verbatim. They are compared with `==` against the
        executed-method stream; nothing here normalises them.

    Raises:
        MopArtifactRefused: The path names a `*.mop.json` (INV-CAN-24).
        OSError: The file cannot be read.
    """
    index = _signature_index(_load(Path(apk_json)))
    if not reaching_only:
        return frozenset(index)
    return frozenset(
        signature for signature, method in index.items() if method.get("reachesTarget")
    )


def read_tree(root: Path | str) -> tuple[list[StaticFacts], TreeSkips]:
    """
    Read every application artefact under a results tree, in stable order.

    The search pattern admits both `<apk>.json` and `<apk>.mop.json` on purpose.
    Excluding the derived artefact by pattern would make the refusal invisible —
    a counter that can never fire proves nothing about a rule — so it is admitted
    to the walk, rejected by name and counted (INV-CAN-04, INV-CAN-24).

    Args:
        root: Directory searched recursively. Not written to.

    Returns:
        `(facts, skips)` — one entry per application in sorted path order, and
        what was passed over, by reason.

    Raises:
        OSError: An artefact under the tree cannot be read.
    """
    facts: list[StaticFacts] = []
    mop_artefacts = 0
    unrecognised = 0
    for candidate in sorted(Path(root).rglob("*.apk*.json")):
        if candidate.name.endswith(FORBIDDEN_SUFFIX):
            mop_artefacts += 1
        elif candidate.name.endswith(".apk.json"):
            facts.append(read(candidate))
        else:
            unrecognised += 1
    return facts, TreeSkips(mop_artefacts=mop_artefacts, unrecognised=unrecognised)


def frame(facts: Iterable[StaticFacts]) -> pd.DataFrame:
    """
    Lay application facts out as one tidy row per application.

    Args:
        facts: The applications' facts, in any order.

    Returns:
        A frame keyed by `apk`, with the handler verdict flattened into its three
        columns and `entry_points` left off — it is a distribution per
        application and does not belong in a scalar column.
    """
    records = [
        {
            "apk": item.apk,
            "package": item.package,
            "activities": item.activities,
            "activities_reaching": item.activities_reaching,
            "sa_methods": item.sa_methods,
            "sa_methods_reaches_mop": item.sa_methods_reaches_mop,
            "sa_methods_directly_reaches_mop": item.sa_methods_directly_reaches_mop,
            "windows": item.windows,
            "widgets": item.widgets,
            "listeners": item.listeners,
            "handlers_distinct": item.handlers.distinct,
            "handlers_hot": item.handlers.hot,
            "handlers_cold": item.handlers.cold,
            "handlers_unresolved": item.handlers.unresolved,
            "transitions": item.transitions,
            "complete": item.complete,
            "fraction_activities_reaching": item.fraction_activities_reaching,
            "stratum": item.stratum,
        }
        for item in facts
    ]
    return pd.DataFrame(
        records,
        columns=[
            "apk",
            "package",
            "activities",
            "activities_reaching",
            "sa_methods",
            "sa_methods_reaches_mop",
            "sa_methods_directly_reaches_mop",
            "windows",
            "widgets",
            "listeners",
            "handlers_distinct",
            "handlers_hot",
            "handlers_cold",
            "handlers_unresolved",
            "transitions",
            "complete",
            "fraction_activities_reaching",
            "stratum",
        ],
    )
