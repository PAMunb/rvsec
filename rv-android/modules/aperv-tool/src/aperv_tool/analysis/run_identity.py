"""The run identity, in one place.

Every artefact a campaign writes is named for the run that produced it:
``<apk>.apk__<repetition>__<timeout>__<arm>`` followed by ``.trace``, ``.logcat``
or nothing at all. That string is the join key between the trace, the logcat, the
coverage dump, the task record and every consolidated CSV, which makes the pattern
that reads it the most-copied line in the analysis code. It was copied twice before
this module existed — once in ``coverage_dump`` and once in ``clock_logcat_join`` —
and duplication of a *parser* is not a cosmetic problem: two copies that drift
disagree about which runs exist, and nothing reports the disagreement.

**The timeout is part of the identity.** Two campaigns at different budgets produce
files whose names differ only there, and dropping it silently merges them.

**The arm is not decomposed here by splitting.** ``aperv:mop_on_llm_off`` and
``droidbot:bfs_greedy`` look like ``tool:variant``, and a bare ``ape`` looks like a
tool with no variant — but that regularity is a convention of the current roster,
not a rule the filename enforces. A tool named with a colon, or a variant naming
convention that changes, would decompose wrongly and silently. So ``decompose_arm``
takes a table supplied by the caller as data, and an arm absent from it raises
rather than guessing (INV-CAN-02). Adding a variant is a data change.

**The other direction is composition, and it lives here too.** ``arm_label`` turns a
``tool_config`` pair back into the label, which needs no table but does need the one
collapse the campaign settled on. It is the same kind of fact as the regex, so it
gets the same treatment: one seat, imported by ``tasks_record`` and ``liveness``,
with a test that greps the package for a second definition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# The run identity as rv-platform writes it. `apk` is greedy up to the literal
# `.apk`, and `arm` is greedy to the end so that a variant containing underscores
# — every one of them does — survives intact.
#
# This regex exists exactly once in `aperv_tool` (INV-CAN-01); `coverage_dump` and
# `clock_logcat_join` import it. A test greps the package to keep that true.
RUN_FILENAME = re.compile(
    r"^(?P<apk>.+\.apk)__(?P<repetition>\d+)__(?P<timeout>\d+)__(?P<arm>.+)$"
)

# The identity at the grain of a Layer-0 frame, as columns. One seat, because the
# alternative was measured: `gates` declared its own tuple saying `repetition`
# while `tasks_record` wrote `rep`, so `gates.run_all(loader.load(...)[0], ...)`
# raised on every real campaign and nothing noticed — every gate test hand-built
# its rows with the other spelling.
#
# Three names for one fact, and all three are correct in their own layer:
#
#   `rep`         the FRAME column, and the column of every consolidated CSV the
#                 campaign writes (`apk,rep,tool,...`). This tuple.
#   `repetition`  the `RunKey` attribute, and the key inside a `tasks.json`
#                 record's `config`. Read by `tasks_record` and by `liveness`
#                 when either parses the raw file.
#   `<rep>`       the second field of the run filename, parsed by the regex above.
#
# A reader converting between the layers is doing its job; a reader that *assumes*
# one of the three at the wrong layer is the defect this tuple closes.
IDENTITY_COLUMNS: tuple[str, ...] = ("apk", "arm", "rep", "timeout_s")

# The suffixes a run's artefacts carry. `.trace.ndjson.gz` is deliberately absent:
# it is a byte-identical gzip of the sibling `.trace`, not a second stream, and a
# caller that treats it as one double-counts about 1.5 GB of a campaign.
_ARTEFACT_SUFFIXES = (".trace", ".logcat")


class UnknownArm(ValueError):
    """An arm string absent from the caller's arm table.

    Raised rather than decomposed heuristically. The alternative — splitting on the
    first colon — returns a plausible pair for every string ever passed to it,
    including a typo, which is precisely how an arm silently vanishes from an
    analysis while every count still looks reasonable.
    """


@dataclass(frozen=True, slots=True)
class RunKey:
    """One run's identity: the grain of every Layer-0 frame.

    ``arm`` is the label as written on disk and as it appears in the ``tool``
    column of the consolidated CSVs — ``ape``, ``aperv:mop_on_llm_off``,
    ``droidbot:bfs_greedy``. It is kept whole here; decomposition is a separate,
    table-driven step.
    """

    apk: str
    repetition: int
    timeout_s: int
    arm: str

    def __str__(self) -> str:
        return f"{self.apk}__{self.repetition}__{self.timeout_s}__{self.arm}"


def parse_run_filename(path: Path | str) -> RunKey:
    """The identity of the run that wrote ``path``.

    Only the basename is inspected; the directory tree a campaign happens to use
    (cmp162's is double-nested by a bind mount) carries no identity information
    that the filename does not already carry.

    Args:
        path: A run artefact — ``.trace``, ``.logcat``, or the bare identity.

    Returns:
        The ``RunKey``.

    Raises:
        ValueError: The basename does not follow the run identity. The message
            names the basename, because the caller almost always has a directory
            full of them and needs to know which one.
    """
    name = Path(path).name
    for suffix in _ARTEFACT_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    match = RUN_FILENAME.match(name)
    if match is None:
        raise ValueError(f"not a run identity: {Path(path).name!r}")
    return RunKey(
        apk=match.group("apk"),
        repetition=int(match.group("repetition")),
        timeout_s=int(match.group("timeout")),
        arm=match.group("arm"),
    )


def try_parse_run_filename(path: Path | str) -> RunKey | None:
    """``parse_run_filename``, or ``None`` for a name that is not a run identity.

    The readers use this rather than the raising form. A hand-named or foreign
    trace is still parsed and still reported — it simply carries no identity —
    because dropping it would remove a run from the denominator (INV-APV-37).
    """
    try:
        return parse_run_filename(path)
    except ValueError:
        return None


def decompose_arm(arm: str, table: Mapping[str, tuple[str, str]]) -> tuple[str, str]:
    """``arm`` → ``(tool, variant)``, by table lookup only.

    Args:
        arm: The arm label as written on disk.
        table: The campaign's arm roster, supplied as data. A tool with no variant
            maps to an empty variant string rather than to ``None``, so the pair is
            always two strings and a groupby never has to handle a null level.

    Returns:
        The ``(tool, variant)`` pair.

    Raises:
        UnknownArm: ``arm`` is not in ``table``.
    """
    try:
        return table[arm]
    except KeyError:
        known = ", ".join(sorted(table)) or "<empty table>"
        raise UnknownArm(
            f"arm {arm!r} is not in the arm table; known arms: {known}"
        ) from None


def arm_label(tool_name: str | None, variant: str | None) -> str:
    """``(tool, variant)`` → the arm label, as the campaign writes it on disk.

    The inverse of ``decompose_arm``, and it lives beside it for the same reason
    the regex lives here: the label is identity vocabulary, so a second copy of it
    is a second opinion about which runs exist. It was written twice before this
    seat existed — once in ``tasks_record`` and once in ``liveness`` — and both
    modules now import it.

    Unlike ``decompose_arm`` this direction needs no table. Going from a label to a
    pair is ambiguous and must be told the roster; going from a pair to a label is
    concatenation, with one collapse the campaign fixed long ago.

    **The collapse.** The builtin ``ape`` writes ``variant='default'`` into its
    ``tool_config``, and the consolidator collapses that to a bare ``ape``. This
    function has to make the same collapse, because the labels it produces are
    matched against the ``tool`` column of the consolidated CSVs and against the
    run's own filename: without it the arm becomes ``ape:default``, joins to
    nothing, and every application drops out of the analysis as "an arm with no
    execution" — which is exactly what happened to the campaign's own scripts
    before the collapse was added.

    Args:
        tool_name: ``tool_config.name``.
        variant: ``tool_config.variant``, absent or ``default`` for a tool with a
            single configuration.

    Returns:
        The arm label — ``ape``, or ``<tool>:<variant>``.
    """
    return "ape" if tool_name == "ape" else f"{tool_name}:{variant}"
