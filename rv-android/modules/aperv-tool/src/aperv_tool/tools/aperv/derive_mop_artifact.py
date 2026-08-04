"""
Derive the compact MOP artifact consumed by ape-rv.jar.

This module is the **single authority** for the parse-time semantics of the APE-RV
MOP substrate: every rule that turns the producer's static analysis into what the
explorer consumes — per-widget MOP flags, the two MOP-activity sets, the OPTIONSMENU
gateway inputs, the click-only WTG view and the component trigger surface — lives
here and nowhere else.

`derive()` runs those rules host-side and emits the *result*, so the device receives
kilobytes of explorer-shaped data. The call-graph section that dominates the full
JSON is an input to the derivation and nothing more: the explorer never reads it, so
it never crosses to the device. Each rule is a relocation of a specific block of the
jar's `MopData.load` (gh96) and carries a named unit test rather than a JSON
fixture, so a rule can be read, changed and defended one at a time.

### Role in the System:

- Host-side projection stage standing between the static-analysis producer, whose
  full JSON it reads, and `ape-rv.jar`, whose `formatVersion: 1` parser reads what
  it writes.
- `tool.py` owns everything this module refuses to do: reading the JSON bytes,
  caching by digest, writing the artifact and pushing it to the device.

### Architectural Decisions:

- **The two MOP axes.** `direct` is the producer's 0-hop bit — the handler invokes a
  monitored operation in its own body, which is what `ape.mopWeightDirect` was
  defined to reward. `transitive` is any-depth reach. `direct` implies `transitive`
  on every derivation path, because the producer emits methods carrying
  `directlyReachesTarget` without `reachesTarget` and a widget that is direct but
  not transitive is an incoherent state.
- **A pure function.** Full-JSON dict in, artifact dict out — no I/O, no device
  interaction and no dependency on the tool object. Provenance (`source.file`,
  `source.digest`) is supplied by the caller precisely because computing it
  requires reading bytes, which this module never does.
- **Noise survivable, structure not.** Malformed *entries* inside a well-typed
  section are skipped rather than raised on: the producer is an external tool and
  one odd widget must not cost a whole app. A malformed *section* is a
  `DerivationError`, and no partial artifact is ever returned.

### Integration Points:

- Input: the parsed full static-analysis JSON, plus the source file name and the
  digest the caller computed over its bytes.
- Output: the artifact dict, which `serialize_canonical()` encodes into the bytes
  that land at `DEVICE_ARTIFACT_PATH` and are cached host-side under
  `ARTIFACT_SUFFIX`.
- Dependencies: the standard library only — no rv-android module, so the derivation
  stays testable without a device, a tool object or a fixture APK.
"""

import hashlib
import json
import re
from typing import Any

# === WIRE FORMAT IDENTITY ===

# The jar parses formatVersion 1 only; a bump is a coordinated cut with the sibling
# `ape` repository.
FORMAT_VERSION = 1
GENERATOR_ID = "aperv-derive/1"

# === ARTIFACT LOCATION AND PROVENANCE ===

# Device destination and host cache suffix. Both live here rather than in tool.py
# so the artifact's identity — its format, its name and where it lands — is stated
# in one file.
DEVICE_ARTIFACT_PATH = "/data/local/tmp/mop-artifact.json"
ARTIFACT_SUFFIX = ".mop.json"

DIGEST_ALGORITHM = "sha256"

# === PRODUCER QUIRKS ===

# D8 desugars a lambda into a wrapper class `X$$ExternalSyntheticLambdaN` whose
# method the producer's call graph marks unreachable, while the reaching body stays
# in `X` under a `lambda$…` name. The pattern captures `X` so the flags can be
# recovered from it.
SYNTHETIC_LAMBDA_PATTERN = re.compile(r"^<(.+?)\$\$ExternalSyntheticLambda\d+:")
LAMBDA_METHOD_PREFIX = "lambda$"

# === PROJECTED WIDGET FIELDS ===

# Widget metadata the explorer consumes: typed input, form completion and
# accessibility-driven selection all read these. Anything else on a widget
# (`id`, `type`, `text`, the raw listener array) is projected away.
WIDGET_METADATA_FIELDS = (
    "inputType",
    "hint",
    "prompt",
    "spinnerMode",
    "contentDescription",
    "tooltipText",
)
WIDGET_ENTRIES_FIELD = "entries"

# === WINDOW AND EVENT VOCABULARY ===

# Window names carry a fragment/menu suffix (`MainActivity#OptionsMenu`); the base
# activity is what every consumer queries by.
BASE_ACTIVITY_SEPARATOR = "#"
DIALOG_WINDOW_TYPE = "DIALOG"
OPTIONS_MENU_WINDOW_TYPE = "OPTIONSMENU"
CLICK_EVENT_TYPE = "click"
ACTIVITY_COMPONENT_TYPE = "activity"
ACTION_VIEW = "android.intent.action.VIEW"

# === MOP WIRE VALUES ===

# Wire values of the per-event `mop` map. `direct` alone is unreachable by
# construction (direct implies transitive); it exists so the encoding is total.
MOP_NONE = "none"
MOP_DIRECT = "direct"
MOP_TRANSITIVE = "transitive"
MOP_BOTH = "both"

# Reserved key for a widget whose only flagged listeners carry a null `eventType`.
# A null key cannot exist in JSON and would be unaddressable by the query side, so
# the flag would survive only in the aggregate — which the jar recomputes as the OR
# over this map. `normalizeEventType("")` yields the same key, so a query for the
# empty event type reads it and nothing else can. An event type made only of
# separators (`"_"`, `"-"`) normalizes to it too and would merge in: no producer
# emits one, and the merge is an OR of flags for events the query side cannot tell
# apart anyway, so the collision is harmless.
EMPTY_EVENT_KEY = ""

# === DERIVATION COUNTERS ===

# Every field the `stats` block reports, declared up front so the block has a fixed
# shape whatever path the derivation takes — a rule that never fires reports 0
# rather than omitting its key, which is what makes two artifacts comparable. These
# are pure counters: nothing derived from them feeds a set, a flag or an edge.
STAT_FIELDS = (
    "windows",
    "widgetsTotal",
    "flagged",
    "droppedFlaggedNoId",
    "orphanDialogs",
    "handlersUnmatched",
    "syntheticLambda",
    "recovered",
    "wtgEdges",
    "dedupedTransitions",
)


class DerivationError(Exception):
    """
    The document is structurally unusable and no artifact may be produced.

    Raised for a missing completion sentinel, a missing package, or a section
    whose type contradicts the schema. Never raised for a malformed entry inside
    a well-typed section — those are skipped, because the producer is an external
    tool whose noise must not cost a whole app.
    """


def digest_of(payload: bytes) -> str:
    """Compute the provenance digest recorded as the artifact's `source.digest`.

    Lives here rather than in the caller so the digest convention and the artifact
    format it appears in stay defined in one place. The caller compares a cached
    artifact's `source.digest` against this value to decide whether a re-derivation
    is needed, so the algorithm prefix is part of the recorded form rather than
    implied.

    Args:
        payload: Raw bytes of the full static-analysis JSON, hashed as read from
            disk — not the re-encoded parse, which would not round-trip.

    Returns:
        The digest as `"<algorithm>:<hex>"`, e.g. `"sha256:9f86d0…"`.
    """
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(payload).hexdigest()}"


def serialize_canonical(artifact: dict) -> bytes:
    """Encode the artifact as canonical bytes.

    Identical input yields identical output on any host and in any process
    (INV-DRV-05), which is what lets the caller treat a digest comparison as proof
    that a cached artifact is current.

    Object keys are sorted at every level, so the byte sequence does not depend on
    construction order. Separators carry no whitespace. Non-ASCII text is preserved
    as UTF-8 rather than escaped, because widget hints and content descriptions are
    natural-language strings that a reader inspects. Array order is fixed by
    construction, not by sorting, wherever order carries meaning.

    Args:
        artifact: A `derive()` result. Any JSON-encodable dict works, but only a
            derived artifact is guaranteed to have order-independent arrays.

    Returns:
        UTF-8 bytes ready to be written and pushed, with no trailing newline.
    """
    return json.dumps(
        artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def derive(document: dict, source_file: str = "", source_digest: str = "") -> dict:
    """
    Project the full static-analysis JSON into the compact MOP artifact.

    Args:
        document: Parsed full static-analysis JSON. Not mutated.
        source_file: Basename of the JSON this document was parsed from, recorded
            as provenance. Supplied by the caller because this module performs no
            I/O.
        source_digest: `digest_of()` of that file's bytes, same reason.

    Returns:
        The artifact dict per the `formatVersion: 1` wire schema, with keys:
        - "formatVersion" (int): Always `FORMAT_VERSION`; the jar rejects any other.
        - "package" (str): Application package, carried over verbatim.
        - "mainActivity" (str | None): Launcher activity, or None when the producer
          did not resolve one.
        - "source" (dict): Provenance — `digest`, `file`, `generator`.
        - "widgets" (dict): `baseActivity -> shortId -> {mop, …metadata}`, holding
          only widgets the explorer can act on.
        - "mopActivities" (list[str]): Widget-derived MOP-activity set, sorted.
        - "mopActivitiesAugmented" (list[str]): The A′ superset of that set, sorted;
          the on-device flag picks which of the two a run uses.
        - "optionsMenus" (list[dict]): One `{activity, hasFlaggedWidget}` gateway
          record per activity owning an OPTIONSMENU window.
        - "wtg" (dict): `baseActivity -> [{widget, target}]`, click edges only.
        - "components" (dict): `activities`/`receivers`/`services`/`providers`
          trigger surface.
        - "stats" (dict): The `STAT_FIELDS` counters, all present.

    Raises:
        DerivationError: The document carries no `"complete": true` sentinel, no
            package, or a section of the wrong type. Nothing partial is returned —
            a truncated analysis must fail generation rather than arm a run with
            half a substrate.
    """
    # Step 1: Refuse a document that cannot be trusted as a whole
    if not isinstance(document, dict):
        raise DerivationError(
            f"static-analysis document must be an object, got {type(document).__name__}"
        )

    # The sentinel is the producer's "write finished" bit. It gates generation
    # host-side, which is where a truncated analysis fails loudly instead of
    # degrading a run into a silently thin substrate.
    if document.get("complete") is not True:
        raise DerivationError(
            "static-analysis document lacks the '\"complete\": true' sentinel "
            "(truncated analysis)"
        )

    package = document.get("package")
    if not isinstance(package, str) or not package:
        raise DerivationError("static-analysis document carries no package name")

    # Step 2: Read the four sections the derivation joins over
    reachability = _require_section(document, "reachability", list, [])
    windows_raw = _require_section(document, "windows", list, [])
    transitions = _require_section(document, "transitions", list, [])
    components = _require_section(document, "components", dict, {})

    stats = {field: 0 for field in STAT_FIELDS}

    # Step 3: Index the call graph, then parse the widget tree against that index —
    # the only point where the call-graph section is read at all
    by_signature, lambda_by_class, activity_classes = _index_reachability(reachability)
    windows, windows_by_id, handlers = _parse_windows(
        windows_raw, by_signature, lambda_by_class
    )
    stats["windows"] = len(windows)

    # Step 4: Key widgets by base activity, then move dialog widgets onto the host
    # activity the explorer will actually be standing in when it sees them
    widget_map, flagged_activities, options_menus = _build_widget_map(windows, stats)
    _rekey_dialogs(
        windows, transitions, windows_by_id, widget_map, flagged_activities, stats
    )

    # Step 5: Count the substrate, then project it onto the wire.
    # Counted after the widget map is final and before the emission filter, because
    # these are the numbers the jar's load record reported and the filter is a wire
    # concern, not a substrate one.
    stats["widgetsTotal"] = sum(len(widgets) for widgets in widget_map.values())
    stats["flagged"] = sum(
        1
        for widgets in widget_map.values()
        for widget in widgets.values()
        if widget["direct"] or widget["transitive"]
    )

    (
        stats["handlersUnmatched"],
        stats["syntheticLambda"],
        stats["recovered"],
    ) = _compute_handler_diagnostics(handlers, by_signature, lambda_by_class)

    return {
        "formatVersion": FORMAT_VERSION,
        "package": package,
        "mainActivity": document.get("mainActivity"),
        "source": {
            "digest": source_digest,
            "file": source_file,
            "generator": GENERATOR_ID,
        },
        "widgets": _emit_widgets(widget_map),
        "mopActivities": sorted(flagged_activities),
        "mopActivitiesAugmented": _augment_activities(
            flagged_activities, components.get("activities"), activity_classes
        ),
        "optionsMenus": options_menus,
        "wtg": _build_wtg(transitions, windows_by_id, stats),
        "components": _project_components(components),
        "stats": stats,
    }


def _require_section(document: dict, key: str, expected: type, default: Any) -> Any:
    """Read a top-level section, refusing one whose type contradicts the schema.

    An absent or null section is the producer's way of saying "nothing here" and
    yields the empty default. A section of the wrong type is a producer bug that
    would silently derive an empty substrate, so it refuses instead.

    Args:
        document: The full static-analysis JSON.
        key: Top-level section name.
        expected: Type the schema requires for the section.
        default: Value standing in for an absent or null section, normally the
            empty container the callers iterate over unconditionally.

    Returns:
        The section, or `default` when it is absent or null.

    Raises:
        DerivationError: The section is present with a type other than `expected`.
    """
    value = document.get(key)
    if value is None:
        return default
    if not isinstance(value, expected):
        raise DerivationError(
            f"section '{key}' must be a {expected.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _normalize_event_type(event_type: Any) -> str | None:
    """Canonicalize an event-type token so the two spellings of an event agree.

    The producer writes snake_case and the query side camelCase, so `long_click`
    and `longClick` must land on the same key: both become `longclick`.

    Returns:
        The canonical token, or None for a null event type. The jar's
        `normalizeEventType` returns null in the same case, and that case is what
        makes the reserved `EMPTY_EVENT_KEY` necessary.
    """
    if not isinstance(event_type, str):
        return None
    return "".join(c.lower() for c in event_type if c not in ("_", "-"))


def _base_activity(window_name: str) -> str:
    """Recover the owning activity from a window name.

    Drops any `#OptionsMenu`/fragment suffix. Every consumer — widget lookup, WTG
    queries, the activity sets — keys by the base activity, so a name that keeps
    its suffix is stored under a key nothing ever queries.
    """
    index = window_name.find(BASE_ACTIVITY_SEPARATOR)
    return window_name[:index] if index >= 0 else window_name


def _index_reachability(
    reachability: list,
) -> tuple[dict[str, tuple[bool, bool]], dict[str, tuple[bool, bool]], set[str]]:
    """Build the three indices the widget-flag derivation joins against.

    Args:
        reachability: The `reachability[]` section. Entries and methods that are
            not objects are skipped, and a method reaching nothing is not indexed
            at all, so absence from an index means "does not reach".

    Returns:
        `by_signature`: method signature -> `(direct, transitive)` for every method
            that reaches a monitored operation. `transitive` is stored as
            `reachesTarget or directlyReachesTarget`, so a widget can never be
            derived direct-but-not-transitive — the producer emits methods with
            exactly that shape and the jar's own index stored `reachesTarget`
            unmodified. Duplicate signatures merge by **OR** rather than by
            last-write, so the index does not depend on the producer's emission
            order.
        `lambda_by_class`: enclosing class -> OR-aggregated flags of its reaching
            `lambda$…` methods, which is what a D8 synthetic-lambda wrapper handler
            is recovered from.
        `activity_classes`: base names of classes typed `activity` carrying at
            least one reaching method — source 3 of the augmented activity set.
            This source is immune to the lambda call-graph gap that makes the
            component-level flag false-negative lambda-triggered activities.
    """
    by_signature: dict[str, tuple[bool, bool]] = {}
    lambda_by_class: dict[str, tuple[bool, bool]] = {}
    activity_classes: set[str] = set()

    for entry in reachability:
        if not isinstance(entry, dict):
            continue
        class_name = entry.get("className")
        component_type = entry.get("componentType")
        methods = entry.get("methods")
        if not isinstance(methods, list):
            continue
        for method in methods:
            if not isinstance(method, dict):
                continue
            direct = method.get("directlyReachesTarget") is True
            reaches = method.get("reachesTarget") is True
            if not (direct or reaches):
                continue
            transitive = reaches or direct

            signature = method.get("signature")
            if isinstance(signature, str):
                by_signature[signature] = _or_flags(
                    by_signature.get(signature), (direct, transitive)
                )

            name = method.get("name")
            if (
                isinstance(class_name, str)
                and isinstance(name, str)
                and name.startswith(LAMBDA_METHOD_PREFIX)
            ):
                lambda_by_class[class_name] = _or_flags(
                    lambda_by_class.get(class_name), (direct, transitive)
                )

            if (
                isinstance(class_name, str)
                and component_type == ACTIVITY_COMPONENT_TYPE
            ):
                activity_classes.add(_base_activity(class_name))

    return by_signature, lambda_by_class, activity_classes


def _or_flags(
    previous: tuple[bool, bool] | None, current: tuple[bool, bool]
) -> tuple[bool, bool]:
    """OR two `(direct, transitive)` pairs, treating an absent one as all-false."""
    if previous is None:
        return current
    return (previous[0] or current[0], previous[1] or current[1])


def _synthetic_lambda_enclosing_class(handler: str) -> str | None:
    """Enclosing class of a D8 synthetic-lambda handler, or None when it is not one."""
    match = SYNTHETIC_LAMBDA_PATTERN.match(handler)
    return match.group(1) if match else None


def _derive_listener_flags(
    listener: dict,
    by_signature: dict[str, tuple[bool, bool]],
    lambda_by_class: dict[str, tuple[bool, bool]],
) -> tuple[bool, bool]:
    """Derive one listener's MOP flags, in three tiers.

    1. **Producer precedence.** When either handler-reach field is non-null the
       producer has answered the question and its answer wins over any local
       cross-reference. No producer emits these fields today (0 of 168,503 corpus
       listeners), so the tier exists for a producer that later does.
    2. **Exact signature join.** `listeners[].handler` is emitted in the same Soot
       form as `reachability[].methods[].signature`, so the join is a string match.
    3. **D8 synthetic-lambda recovery.** A handler the exact join missed may be a
       `X$$ExternalSyntheticLambdaN` wrapper, which D8 emits for every desugared
       lambda and which the producer's call graph marks unreachable — the reaching
       body lives in `X` under a `lambda$…` name. Recovering from `X` closes a gap
       that affects every app built with lambda desugaring; a class with no
       reaching lambda leaves the widget unflagged, which is why the recovery
       cannot simply flag every wrapper.

    `transitive` is `reaches or direct` on all three tiers, so `direct` implies
    `transitive` however the flags were obtained.

    Args:
        listener: One entry of a widget's `listeners[]`.
        by_signature: Exact-join index from `_index_reachability()`.
        lambda_by_class: Synthetic-lambda recovery index from the same call.

    Returns:
        The `(direct, transitive)` pair. `(False, False)` when the listener names
        no handler and every tier declined — indistinguishable, by design, from a
        handler that provably reaches nothing.
    """
    supplied_direct = listener.get("handlerDirectlyReachesTarget")
    supplied_reaches = listener.get("handlerReachesTarget")
    if supplied_direct is not None or supplied_reaches is not None:
        direct = supplied_direct is True
        return direct, (supplied_reaches is True) or direct

    handler = listener.get("handler")
    if not isinstance(handler, str):
        return False, False

    flags = by_signature.get(handler)
    if flags is None:
        enclosing = _synthetic_lambda_enclosing_class(handler)
        if enclosing is not None:
            flags = lambda_by_class.get(enclosing)
    if flags is None:
        return False, False
    return flags


def _derive_widget_flags(
    listeners: list,
    by_signature: dict[str, tuple[bool, bool]],
    lambda_by_class: dict[str, tuple[bool, bool]],
) -> tuple[dict[str, str], bool, bool]:
    """Derive a widget's per-event `mop` map and its two aggregate flags.

    Flags are OR-aggregated per normalized `eventType` across the widget's
    listeners, and again across all of them for the aggregates. An explicit `none`
    entry is never omitted: on the query side it is the *presence* of the key that
    suppresses the fall-back to the aggregate, so dropping it would make a widget
    whose click reaches a monitored operation also count as MOP-reaching on
    long-click.

    A listener with a null `eventType` has no addressable key — a null key cannot
    exist in JSON and the query side skips the per-event lookup for one — so it
    folds into the aggregate. Because the jar recomputes the aggregate as the OR
    over this map, a widget whose *only* flagged listeners are null-keyed would
    lose the flag entirely; that case, and only that case, emits the reserved empty
    key.

    Args:
        listeners: The widget's `listeners[]`, already narrowed to a list.
        by_signature: Exact-join index from `_index_reachability()`.
        lambda_by_class: Synthetic-lambda recovery index from the same call.

    Returns:
        `(mop, direct, transitive)` — the normalized-eventType map with wire values
        from `_encode_mop()`, and the two aggregates OR-ed over every listener
        including the null-keyed ones the map may not represent.
    """
    per_event: dict[str | None, tuple[bool, bool]] = {}
    aggregate_direct = False
    aggregate_transitive = False

    for listener in listeners:
        if not isinstance(listener, dict):
            continue
        direct, transitive = _derive_listener_flags(
            listener, by_signature, lambda_by_class
        )
        key = _normalize_event_type(listener.get("eventType"))
        per_event[key] = _or_flags(per_event.get(key), (direct, transitive))
        aggregate_direct = aggregate_direct or direct
        aggregate_transitive = aggregate_transitive or transitive

    null_entry = per_event.pop(None, None)
    if null_entry is not None and (null_entry[0] or null_entry[1]):
        keyed_flagged = any(
            direct or transitive for direct, transitive in per_event.values()
        )
        if not keyed_flagged:
            per_event[EMPTY_EVENT_KEY] = _or_flags(
                per_event.get(EMPTY_EVENT_KEY), null_entry
            )

    mop = {key: _encode_mop(*flags) for key, flags in per_event.items()}
    return mop, aggregate_direct, aggregate_transitive


def _encode_mop(direct: bool, transitive: bool) -> str:
    """Encode a flag pair as its wire value."""
    if direct and transitive:
        return MOP_BOTH
    if direct:
        return MOP_DIRECT
    if transitive:
        return MOP_TRANSITIVE
    return MOP_NONE


def _mop_rank(widget: dict) -> int:
    """Rank MOP-flag strength for collision resolution.

    Yields 2 for direct, 1 for transitive, 0 for unflagged. Ranking rather than
    overwriting is what makes the emitted widget independent of the order the
    producer listed the windows in.
    """
    if widget["direct"]:
        return 2
    if widget["transitive"]:
        return 1
    return 0


def _widget_metadata(widget: dict) -> dict:
    """Project the widget metadata the explorer consumes, dropping empty values.

    Emptiness is the producer's way of saying "absent" — it emits `""` for an
    unset hint and `[]` for a widget with no spinner entries — so an empty value
    carries nothing and only costs bytes on the wire.

    Returns:
        The present `WIDGET_METADATA_FIELDS` as string values, plus `entries` as a
        string list when the widget declares any. Empty when the widget carries no
        metadata at all, which is one of the two conditions for projecting it away.
    """
    metadata = {}
    for field in WIDGET_METADATA_FIELDS:
        value = widget.get(field)
        if isinstance(value, str) and value:
            metadata[field] = value
    entries = widget.get(WIDGET_ENTRIES_FIELD)
    if isinstance(entries, list) and entries:
        metadata[WIDGET_ENTRIES_FIELD] = [
            entry for entry in entries if isinstance(entry, str)
        ]
    return metadata


def _parse_widget(
    widget: dict,
    by_signature: dict[str, tuple[bool, bool]],
    lambda_by_class: dict[str, tuple[bool, bool]],
    handlers: set[str],
) -> dict:
    """Parse one widget into the internal record the map and the wire are built from.

    Args:
        widget: One entry of a window's `widgets[]`.
        by_signature: Exact-join index from `_index_reachability()`.
        lambda_by_class: Synthetic-lambda recovery index from the same call.
        handlers: Accumulator of distinct handler signatures, **added to in place**.
            Collected here because the widget tree is walked exactly once and the
            join diagnostics would otherwise need a second pass over it.

    Returns:
        Internal record with keys:
        - "shortId" (str): The widget's `idName`, or `""` when it has none — which
          is the value the map keying later drops on.
        - "direct" (bool), "transitive" (bool): Widget-level aggregates.
        - "mop" (dict): Per-normalized-eventType wire values.
        - "metadata" (dict): The projected metadata, possibly empty.
    """
    listeners = widget.get("listeners")
    listeners = listeners if isinstance(listeners, list) else []
    for listener in listeners:
        if isinstance(listener, dict) and isinstance(listener.get("handler"), str):
            handlers.add(listener["handler"])

    mop, direct, transitive = _derive_widget_flags(
        listeners, by_signature, lambda_by_class
    )
    short_id = widget.get("idName")
    return {
        "shortId": short_id if isinstance(short_id, str) else "",
        "direct": direct,
        "transitive": transitive,
        "mop": mop,
        "metadata": _widget_metadata(widget),
    }


def _parse_windows(
    windows_raw: list,
    by_signature: dict[str, tuple[bool, bool]],
    lambda_by_class: dict[str, tuple[bool, bool]],
) -> tuple[list[dict], dict[int, dict], set[str]]:
    """Parse `windows[]` once into window records, an id index and a handler set.

    The id index is what the transition passes resolve edge endpoints through, and
    the handler set feeds the join diagnostics — collected here so neither needs a
    second walk of the widget tree.

    Args:
        windows_raw: The `windows[]` section. Non-object windows and non-object
            widgets are skipped rather than refused.
        by_signature: Exact-join index from `_index_reachability()`.
        lambda_by_class: Synthetic-lambda recovery index from the same call.

    Returns:
        `(windows, windows_by_id, handlers)` — the window records carrying `id`,
        `type`, `name`, `base` and parsed `widgets`; the index of only those windows
        with a non-negative id, since a window the producer left unidentified can
        never be a transition endpoint; and the distinct listener handler
        signatures seen anywhere in the tree.
    """
    windows: list[dict] = []
    windows_by_id: dict[int, dict] = {}
    handlers: set[str] = set()

    for raw in windows_raw:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        name = name if isinstance(name, str) else None
        widgets_raw = raw.get("widgets")
        window = {
            "id": _as_int(raw.get("id"), -1),
            "type": raw.get("type"),
            "name": name,
            "base": _base_activity(name) if name is not None else None,
            "widgets": [
                _parse_widget(widget, by_signature, lambda_by_class, handlers)
                for widget in (widgets_raw if isinstance(widgets_raw, list) else [])
                if isinstance(widget, dict)
            ],
        }
        windows.append(window)
        if window["id"] >= 0:
            windows_by_id[window["id"]] = window

    return windows, windows_by_id, handlers


def _as_int(value: Any, default: int) -> int:
    """Read an integer field, falling back for the absent and the malformed alike."""
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _build_widget_map(
    windows: list[dict], stats: dict
) -> tuple[dict[str, dict[str, dict]], set[str], list[dict]]:
    """Build the widget map, the widget-derived MOP-activity set and the menu records.

    Windows sharing a base activity — an activity and its `#OptionsMenu`, an
    activity and its fragments — accumulate into one bucket, which is why a
    collision policy is needed at all. The strongest flag wins and a tie keeps the
    first occurrence, so the emitted widget does not depend on producer ordering.

    A flagged widget marks its base activity **before** the empty-short-id drop is
    evaluated. Deriving the set from the emitted map instead would silently shrink
    it, and the loss cascades into WTG scoring, the frontier passes, the MOP density
    floor, the OPTIONSMENU gateway's second condition and the launcher census —
    with a normal load record in the trace. The widget is unscorable without an id;
    the activity is not.

    A bucket is created for every named window even when all its widgets are
    dropped, because the dialog re-keying reads bucket presence to decide whether a
    dialog's widgets have already been moved.

    Args:
        windows: Window records from `_parse_windows()`. Unnamed windows are
            skipped: with no name there is no activity to key their widgets by.
        stats: Counter dict, **written to in place** (`droppedFlaggedNoId`).

    Returns:
        `(widget_map, flagged_activities, options_menus)` — the map keyed
        `baseActivity -> shortId -> widget`; the set of base activities owning at
        least one flagged widget; and one sorted `{activity, hasFlaggedWidget}`
        record per activity with an OPTIONSMENU window.
    """
    widget_map: dict[str, dict[str, dict]] = {}
    flagged_activities: set[str] = set()
    menu_flagged: dict[str, bool] = {}

    for window in windows:
        if window["name"] is None:
            continue
        activity = window["base"]

        if window["type"] == OPTIONS_MENU_WINDOW_TYPE:
            # Tested over the window's parsed widgets, before the empty-id drop, for
            # the same reason the activity marking is: an id-less menu item still
            # makes the menu a MOP gateway. Records merge per activity by OR, so two
            # menu windows on one activity cannot disagree on the wire.
            has_flagged = any(
                widget["direct"] or widget["transitive"] for widget in window["widgets"]
            )
            menu_flagged[activity] = menu_flagged.get(activity, False) or has_flagged

        widgets = widget_map.setdefault(activity, {})
        for widget in window["widgets"]:
            flagged = widget["direct"] or widget["transitive"]
            if flagged:
                flagged_activities.add(activity)
            if not widget["shortId"]:
                # A single "" key would collapse every id-less widget of the activity
                # onto one entry and surface an arbitrary one. Dropping makes the loss
                # explicit and countable instead of hiding it as noise.
                if flagged:
                    stats["droppedFlaggedNoId"] += 1
                continue
            resident = widgets.get(widget["shortId"])
            if resident is None or _mop_rank(widget) > _mop_rank(resident):
                widgets[widget["shortId"]] = widget

    options_menus = [
        {"activity": activity, "hasFlaggedWidget": flagged}
        for activity, flagged in sorted(menu_flagged.items())
    ]
    return widget_map, flagged_activities, options_menus


def _emit_widgets(widget_map: dict[str, dict[str, dict]]) -> dict:
    """Project the widget map onto the wire, keeping only what the explorer can act on.

    A widget that is neither MOP-flagged nor carrying metadata has nothing to
    contribute: it cannot be boosted and it cannot be typed into. Dropping it is
    what makes the artifact small on widget-heavy apps.

    Returns:
        `baseActivity -> shortId -> {mop, …metadata}`. An activity whose widgets all
        drop out contributes no key, which reads identically to an absent activity
        on the query side.
    """
    emitted: dict[str, dict] = {}
    for activity, widgets in widget_map.items():
        entries = {}
        for short_id, widget in widgets.items():
            if not (widget["direct"] or widget["transitive"] or widget["metadata"]):
                continue
            entries[short_id] = {"mop": widget["mop"], **widget["metadata"]}
        if entries:
            emitted[activity] = entries
    return emitted


def _rekey_dialogs(
    windows: list[dict],
    transitions: list,
    windows_by_id: dict[int, dict],
    widget_map: dict[str, dict[str, dict]],
    flagged_activities: set[str],
    stats: dict,
) -> None:
    """Re-key DIALOG windows onto their host activity, in place.

    A DIALOG window is named after the dialog class (`android.app.AlertDialog`),
    which never equals the activity the explorer sees at runtime — so its widgets,
    already parsed, are unreachable for scoring under that key. The activity→dialog
    edge in `transitions[]` recovers the host.

    Five rules are coupled here:

    1. The host is the source of the **first** incoming transition whose source
       window has a name, matching the order the producer emitted edges in.
    2. Merging uses the same `mopRank` collision policy as widget keying, so a
       dialog widget never displaces a stronger host widget under the same id.
    3. The dialog's map key is **moved**, not copied, so the widget counts do not
       inflate.
    4. A merge that carried at least one flagged widget promotes the host into the
       widget-derived MOP-activity set.
    5. The dialog class keeps its own entry in that set, because WTG edges into the
       dialog are keyed by it and the OPTIONSMENU gateway tests membership of the
       edge target — dropping it would silently disable that detection.

    A dialog with no incoming transition is an orphan: unreachable, so it keeps its
    own key and is only counted.

    Args:
        windows: Window records from `_parse_windows()`; only DIALOG ones are read.
        transitions: The `transitions[]` section, scanned in emission order because
            rule 1 depends on that order.
        windows_by_id: Endpoint index from `_parse_windows()`.
        widget_map: Widget map, **mutated in place** — dialog keys are moved onto
            their hosts.
        flagged_activities: MOP-activity set, **added to in place** by rule 4.
        stats: Counter dict, **written to in place** (`orphanDialogs`).
    """
    for window in windows:
        if window["name"] is None or window["type"] != DIALOG_WINDOW_TYPE:
            continue

        host = _resolve_dialog_host(window, transitions, windows_by_id)
        if host is None:
            stats["orphanDialogs"] += 1
            continue

        dialog_class = window["base"]
        if dialog_class == host:
            continue
        dialog_widgets = widget_map.get(dialog_class)
        if dialog_widgets is None:
            # Already moved by an earlier DIALOG window sharing this base name.
            continue

        host_widgets = widget_map.setdefault(host, {})
        flagged_merged = False
        for short_id, widget in dialog_widgets.items():
            resident = host_widgets.get(short_id)
            if resident is None or _mop_rank(widget) > _mop_rank(resident):
                host_widgets[short_id] = widget
            if widget["direct"] or widget["transitive"]:
                flagged_merged = True

        del widget_map[dialog_class]
        if flagged_merged:
            flagged_activities.add(host)


def _resolve_dialog_host(
    window: dict, transitions: list, windows_by_id: dict[int, dict]
) -> str | None:
    """Resolve a dialog's host activity: the first incoming named source wins.

    This is rule 1 of the re-keying. "First" means first in the producer's emission
    order, which is why the scan runs over `transitions` as given rather than over an
    index — a dialog opened from two activities belongs to the one that opened it
    first, and any other tie-break would depend on hash ordering.

    Returns:
        The base activity of that source, or None when the dialog has no incoming
        transition at all — an orphan, unreachable and left under its own key.
    """
    if window["id"] < 0:
        return None
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        if _as_int(transition.get("targetId"), -1) != window["id"]:
            continue
        source = windows_by_id.get(_as_int(transition.get("sourceId"), -1))
        if source is not None and source["name"] is not None:
            return source["base"]
    return None


def _build_wtg(
    transitions: list, windows_by_id: dict[int, dict], stats: dict
) -> dict[str, list[dict]]:
    """Build the click-only WTG view, keyed by base source activity.

    Both consumers — the runtime WTG pass and the WTG score — query by base
    activity, so a menu- or fragment-sourced edge must collapse to its base;
    otherwise it is stored under a key nothing ever queries. Only click events
    carry navigation the explorer can act on.

    Exact `(widget, target)` duplicates within a source are removed: no consumer
    reads edge multiplicity (all are set-membership or first-match-fixed-weight),
    and the producer emits them in bulk on some apps. First-occurrence order is
    preserved, because the dialog host resolution above depends on edge order.

    Args:
        transitions: The `transitions[]` section.
        windows_by_id: Endpoint index from `_parse_windows()`. An edge whose source
            or target is missing from it, or unnamed, is dropped — there is no
            activity to key it by or point it at.
        stats: Counter dict, **written to in place** (`wtgEdges`,
            `dedupedTransitions`).

    Returns:
        `baseSourceActivity -> [{widget, target}]`, in first-occurrence order. An
        event with no widget name keeps the empty string, which the consumers read
        as "this edge is not attributable to a widget".
    """
    wtg: dict[str, list[dict]] = {}
    seen: dict[str, set[tuple[str, str]]] = {}

    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        source = windows_by_id.get(_as_int(transition.get("sourceId"), -1))
        target = windows_by_id.get(_as_int(transition.get("targetId"), -1))
        if source is None or target is None:
            continue
        if source["name"] is None or target["name"] is None:
            continue
        source_activity = source["base"]
        target_activity = target["base"]

        events = transition.get("events")
        for event in events if isinstance(events, list) else []:
            if not isinstance(event, dict) or event.get("type") != CLICK_EVENT_TYPE:
                continue
            widget_name = event.get("widgetName")
            widget_name = widget_name if isinstance(widget_name, str) else ""
            edge = (widget_name, target_activity)
            bucket = seen.setdefault(source_activity, set())
            if edge in bucket:
                stats["dedupedTransitions"] += 1
                continue
            bucket.add(edge)
            wtg.setdefault(source_activity, []).append(
                {"widget": widget_name, "target": target_activity}
            )
            stats["wtgEdges"] += 1

    return wtg


def _augment_activities(
    flagged_activities: set[str],
    components_activities: Any,
    activity_classes: set[str],
) -> list[str]:
    """Build the A′ union of three MOP-activity sources.

    The three are the widget-derived set, the manifest activities the producer
    flags as reaching, and the reachability classes typed `activity` that carry a
    reaching method.

    Source 3 is the one immune to the lambda call-graph gap: the component-level
    flag false-negatives lambda-triggered activities, which is why cryptoapp has
    every `components.activities[].reachesTarget` false while
    `CryptographyActivity` carries reaching methods.

    Both sets are emitted; the on-device flag selects which one a run uses, so the
    artifact cannot decide it.

    Args:
        flagged_activities: Source 1 — the widget-derived set, read not mutated.
        components_activities: Source 2 — `components.activities`, or any value at
            all: a non-list contributes nothing rather than refusing.
        activity_classes: Source 3 — from `_index_reachability()`.

    Returns:
        The sorted union, a superset of `flagged_activities` by construction.
    """
    augmented = set(flagged_activities)
    for entry in (
        components_activities if isinstance(components_activities, list) else []
    ):
        if not isinstance(entry, dict):
            continue
        class_name = entry.get("className")
        if entry.get("reachesTarget") is True and isinstance(class_name, str):
            augmented.add(_base_activity(class_name))
    augmented |= activity_classes
    return sorted(augmented)


def _derive_deep_link_uri(intent_filters: Any) -> str | None:
    """Assemble the activity's deep-link URI from its intent filters.

    The first filter declaring `ACTION_VIEW` together with a non-empty scheme list
    wins; host and path default to empty when the filter omits them.

    This is not decoration: the MOP stagnation launcher dispatches `ACTION_VIEW` on
    it, so an activity reachable only by deep link becomes unopenable without it —
    while the trace still reports a normal load.

    Returns:
        `"<scheme>://<host><path>"`, or None when no filter qualifies. None means
        "use the explicit-component intent", not "this activity is unreachable".
    """
    for filter_entry in intent_filters if isinstance(intent_filters, list) else []:
        if not isinstance(filter_entry, dict):
            continue
        actions = filter_entry.get("actions")
        if not isinstance(actions, list) or ACTION_VIEW not in actions:
            continue
        data = filter_entry.get("data")
        if not isinstance(data, dict):
            continue
        schemes = _string_list(data.get("schemes"))
        if not schemes:
            continue
        hosts = _string_list(data.get("hosts"))
        paths = _string_list(data.get("paths"))
        host = hosts[0] if hosts else ""
        path = paths[0] if paths else ""
        return f"{schemes[0]}://{host}{path}"
    return None


def _string_list(value: Any) -> list[str]:
    """Read a list-of-strings field, dropping anything that is not a string."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _project_components(components: dict) -> dict:
    """Project the component trigger surface.

    That surface is what the explorer needs to launch an activity, fire a
    broadcast, start a service or address a provider.

    `reachesTarget` becomes `reachesMop` on the wire — inside the explorer the only
    targets are monitored operations, and the neutral producer vocabulary stops at
    this boundary. The `targetMethods` signature list compacts to the boolean the
    trigger ordering actually reads, and the intent-filter structure reduces to the
    actions and categories a broadcast needs; the `data` block survives only as the
    already-assembled `deepLinkUri`.

    Returns:
        Dictionary with keys:
        - "activities" (list): Projections carrying `deepLinkUri` where derivable.
        - "receivers" (list), "services" (list): Projections carrying
          `hasTargetMethods` and the reduced `intentFilters`.
        - "providers" (list): Projections carrying `authorities`.
        Each list is always present, empty when the section declares no component
        of that type, so the jar never branches on a missing key.
    """
    return {
        "activities": [
            _project_component(entry, deep_link=True)
            for entry in _component_list(components, "activities")
        ],
        "receivers": [
            _project_component(entry, intent_filters=True)
            for entry in _component_list(components, "receivers")
        ],
        "services": [
            _project_component(entry, intent_filters=True)
            for entry in _component_list(components, "services")
        ],
        "providers": [
            _project_component(entry, authorities=True)
            for entry in _component_list(components, "providers")
        ],
    }


def _component_list(components: dict, key: str) -> list[dict]:
    """Read one component section as a list of objects, dropping everything else."""
    value = components.get(key)
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _project_component(
    entry: dict,
    *,
    deep_link: bool = False,
    intent_filters: bool = False,
    authorities: bool = False,
) -> dict:
    """Project one component onto its wire shape.

    Args:
        entry: One component object from the `components` section.
        deep_link: Attach `deepLinkUri` when derivable. Activities only.
        intent_filters: Attach `hasTargetMethods` and the reduced `intentFilters`.
            Receivers and services.
        authorities: Attach `authorities` verbatim. Providers only.

    Returns:
        The common projection — `className`, `isMain`, `exported`, `permission`,
        `reachesMop` — plus whichever additions the flags selected. The booleans
        are `is True` tests, so a missing or non-boolean producer field reads as
        false rather than propagating onto the wire.
    """
    projected = {
        "className": entry.get("className"),
        "isMain": entry.get("isMain") is True,
        "exported": entry.get("exported") is True,
        "permission": entry.get("permission"),
        "reachesMop": entry.get("reachesTarget") is True,
    }
    if deep_link:
        uri = _derive_deep_link_uri(entry.get("intentFilters"))
        if uri is not None:
            projected["deepLinkUri"] = uri
    if intent_filters:
        target_methods = entry.get("targetMethods")
        projected["hasTargetMethods"] = bool(
            isinstance(target_methods, list) and target_methods
        )
        raw_filters = entry.get("intentFilters")
        projected["intentFilters"] = [
            {
                "actions": _string_list(filter_entry.get("actions")),
                "categories": _string_list(filter_entry.get("categories")),
            }
            for filter_entry in (raw_filters if isinstance(raw_filters, list) else [])
            if isinstance(filter_entry, dict)
        ]
    if authorities:
        projected["authorities"] = entry.get("authorities")
    return projected


def _compute_handler_diagnostics(
    handlers: set[str],
    by_signature: dict[str, tuple[bool, bool]],
    lambda_by_class: dict[str, tuple[bool, bool]],
) -> tuple[int, int, int]:
    """Count the widget-handler join over distinct handler signatures.

    Counting distinct signatures rather than listener occurrences is what makes a
    silent collapse of the join visible in the artifact, instead of leaving it to
    be inferred from a flagged count that looks plausible.

    Args:
        handlers: Distinct handler signatures from `_parse_windows()`.
        by_signature: Exact-join index from `_index_reachability()`.
        lambda_by_class: Synthetic-lambda recovery index from the same call.

    Returns:
        `(handlersUnmatched, syntheticLambda, recovered)`, nested by construction:
        `recovered <= syntheticLambda <= handlersUnmatched`. These are pure
        counters — nothing here feeds a set, a flag or an edge.
    """
    unmatched = 0
    synthetic = 0
    recovered = 0
    for handler in handlers:
        if handler in by_signature:
            continue
        unmatched += 1
        enclosing = _synthetic_lambda_enclosing_class(handler)
        if enclosing is None:
            continue
        synthetic += 1
        if enclosing in lambda_by_class:
            recovered += 1
    return unmatched, synthetic, recovered
