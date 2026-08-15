"""Clone collapse: folding near-identical applications onto one representative.

An application corpus assembled from a store snapshot contains families: the same
program under two package ids, a rebuild whose only difference is a version bump,
a white-label repackaging. Counted as separate applications they inflate a
denominator and, worse, break the independence a paired analysis assumes — two
members of a family are one draw, not two, and a difference measured on both is
measured twice.

Nothing existed to reuse for this. The sibling Android study has no clone rule at
all, and its ``would_collapse`` column answers a different question — whether a
record *would* be merged under an alternative dedup key — which is a property of a
record, not a statement that two applications are the same program. Reading it as
a clone rule would collapse families that were never declared.

So the rule is data. ``collapse`` takes a clone map the caller supplies, in which
each family names its members, the member that survives, and why that one. The
module decides nothing: it applies the declaration, rewrites the folded members
onto their survivor, and returns a report saying which application was folded into
which, under which family, for which stated reason, and how many rows moved. A
collapse that is not in the report did not happen, and a collapse that happened is
in the report — nothing collapses silently.

The frame's rows are relabelled rather than dropped. A folded member's runs are
still runs of the surviving application; discarding them would shrink a run-level
denominator as a side effect of an application-level decision, which is a second,
undeclared scoping. The application basis before and after the collapse is
reported as two ``Basis`` values, so the size change is stated with the members
that caused it (INV-CAN-09).

Offline and read-only over the map file the caller names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from aperv_tool.analysis.corpus import APPLICATION_COLUMN, Basis, BasisRelation


@dataclass(frozen=True, slots=True)
class CloneFamily:
    """One declared family of applications treated as a single program.

    Attributes:
        name: The family's label, used in the report so a reader can go back to
            the declaration that produced a fold.
        survivor: The member the family collapses onto. Must be one of ``members``.
        members: Every application id in the family, the survivor included.
        reason: Why these are one program and why this member represents them.
            Recorded per fold; a family without one is not a declaration.
    """

    name: str
    survivor: str
    members: frozenset[str]
    reason: str

    def __post_init__(self) -> None:
        if self.survivor not in self.members:
            raise ValueError(
                f"family {self.name!r} survives as {self.survivor!r}, which is not "
                f"one of its members"
            )
        if not self.reason.strip():
            raise ValueError(f"family {self.name!r} declares no reason")


@dataclass(frozen=True, slots=True)
class Collapse:
    """One application folded onto its family's survivor.

    Attributes:
        member: The application that stops being counted separately.
        survivor: The application it is counted as.
        family: The declaring family's name.
        reason: The family's stated reason, copied here so a single fold is
            readable without holding the map.
        rows: How many frame rows were relabelled. Zero is possible and is worth
            seeing: it means the map declared a member the frame never carried
            runs for.
    """

    member: str
    survivor: str
    family: str
    reason: str
    rows: int


@dataclass(frozen=True, slots=True)
class CollapseReport:
    """What the collapse did, in full.

    Attributes:
        before: The application basis of the frame as it arrived.
        after: The application basis once the folds were applied.
        collapses: One record per folded member, sorted by member id.
        unseen: Declared members the frame never contained, sorted. Not an error —
            a map is written for a corpus and applied to a scoped frame — but a
            silent one would hide a map written against the wrong campaign.
    """

    before: Basis
    after: Basis
    collapses: tuple[Collapse, ...]
    unseen: tuple[str, ...]

    @property
    def collapsed(self) -> int:
        """How many applications stopped being counted separately."""
        return len(self.collapses)

    @property
    def rows_relabelled(self) -> int:
        """How many frame rows changed application id."""
        return sum(record.rows for record in self.collapses)

    def relation(self) -> BasisRelation:
        """The size change, stated with the members that caused it."""
        return self.before.relate(self.after)

    def report(self) -> str:
        """The folds and the basis change, as text.

        Returns:
            A multi-line report. With no folds it still prints the relation, which
            reads as a basis that did not move — the correct statement when a map
            declared families the frame does not contain.
        """
        lines = [self.relation().report()]
        for record in self.collapses:
            lines.append(
                f"  {record.member} -> {record.survivor} "
                f"[{record.family}] {record.rows} row(s): {record.reason}"
            )
        if self.unseen:
            lines.append(f"  declared but absent: {', '.join(self.unseen)}")
        return "\n".join(lines)


def read_clone_map(path: Path) -> tuple[CloneFamily, ...]:
    """Clone families from a JSON declaration.

    The file is a list of objects with ``family``, ``survivor``, ``members`` and
    ``reason``. JSON rather than one line per family because the reason is prose
    and a delimited format invites it to be dropped.

    Args:
        path: The clone map.

    Returns:
        The families in file order.

    Raises:
        ValueError: A family names a survivor outside its members, or omits the
            reason.
        KeyError: A family object is missing a field.
    """
    declared = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        CloneFamily(
            name=entry["family"],
            survivor=entry["survivor"],
            members=frozenset(entry["members"]),
            reason=entry["reason"],
        )
        for entry in declared
    )


def collapse(
    frame: pd.DataFrame, clone_map: Path | Iterable[CloneFamily]
) -> tuple[pd.DataFrame, CollapseReport]:
    """Apply a declared clone map to a frame's application ids.

    Args:
        frame: Any frame carrying the ``apk`` column.
        clone_map: The declaration, as a JSON file or the families themselves.

    Returns:
        The relabelled frame and the ``CollapseReport``. The frame is a copy; the
        caller's frame is untouched.

    Raises:
        ValueError: The frame has no application column, two families claim the
            same application, or two families share a name — each of which makes
            the fold order decide the result, and the fold order is not part of
            the declaration.
    """
    if APPLICATION_COLUMN not in frame.columns:
        raise ValueError(
            f"frame has no {APPLICATION_COLUMN!r} column; columns are "
            f"{list(frame.columns)}"
        )
    families = (
        read_clone_map(clone_map) if isinstance(clone_map, Path) else tuple(clone_map)
    )
    survivor_of, family_of, reason_of = _index(families)

    present = frame[APPLICATION_COLUMN]
    before_ids = set(present)
    before = Basis.declare("pre_collapse", before_ids, cardinality=len(before_ids))

    collapses = tuple(
        Collapse(
            member=member,
            survivor=survivor_of[member],
            family=family_of[member],
            reason=reason_of[member],
            rows=int((present == member).sum()),
        )
        for member in sorted(survivor_of)
        if member != survivor_of[member] and member in before_ids
    )
    unseen = tuple(sorted(set(survivor_of) - before_ids))

    collapsed_frame = frame.copy()
    collapsed_frame[APPLICATION_COLUMN] = present.map(
        lambda application: survivor_of.get(application, application)
    )
    after_ids = set(collapsed_frame[APPLICATION_COLUMN])
    after = Basis.declare("post_collapse", after_ids, cardinality=len(after_ids))

    return collapsed_frame, CollapseReport(
        before=before, after=after, collapses=collapses, unseen=unseen
    )


def _index(
    families: Sequence[CloneFamily],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Member → survivor, member → family name, member → reason.

    Built in one pass so that an application claimed by two families is caught
    against the family that claimed it first, and named in the message.
    """
    survivor_of: dict[str, str] = {}
    family_of: dict[str, str] = {}
    reason_of: dict[str, str] = {}
    seen_names: set[str] = set()

    for family in families:
        if family.name in seen_names:
            raise ValueError(f"clone map declares family {family.name!r} twice")
        seen_names.add(family.name)
        for member in family.members:
            if member in survivor_of:
                raise ValueError(
                    f"application {member!r} is claimed by families "
                    f"{family_of[member]!r} and {family.name!r}"
                )
            survivor_of[member] = family.survivor
            family_of[member] = family.name
            reason_of[member] = family.reason

    return survivor_of, family_of, reason_of
