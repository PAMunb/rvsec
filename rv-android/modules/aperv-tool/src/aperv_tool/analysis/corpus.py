"""Corpus scoping, and the denominator that travels with the number.

A campaign's numbers were not wrong. They were correct in isolation and misleading
in a report, which is a harder failure to see and a much harder one to undo. A
detection rate computed over the forty applications that reached a monitored
operation is a true statement about those forty; printed beside a campaign
described as 162 applications, it reads as a statement about 162. Nothing in the
number itself objects, and the reader has no way to tell — the denominator was
decided somewhere upstream and did not travel.

So this module makes the denominator part of the value. ``scope`` returns the
analysed frame together with a ``CorpusScope``, and the only way to obtain a
fraction from that scope is ``CorpusScope.rate``, which returns a ``Rate`` holding
the ``Denominator`` an envelope carries — the reachable corpus the campaign ran
over, the analysed subset the fraction was actually computed on, and the recorded
reason the subset was declared. There is deliberately no path through this API
that yields a bare float: a fraction with one denominator is not a weaker result,
it is an uncheckable one (INV-CAN-09). The pair is not redefined here; a scope
hands out the same ``Denominator`` an estimator will put in its envelope.

The second half of the same discipline is the ``Basis``. Two bases in this project
differ by exactly one application — the substrate census carries 163 rows against
the campaign's 162 — and the difference was reported for a long time as a
cardinality, "163 versus 162". A cardinality difference is a hint, not a report:
it says something is missing without saying what, so the next reader re-derives
the set difference by hand or, more often, assumes it is benign. ``Basis.relate``
therefore prints the members by name, and a ``Basis`` cannot be constructed
without declaring the cardinality it is claimed to have, which is checked.

The corpus is a pre-registration freeze item (INV-CAN-11). It has no default here,
and ``scope`` raises ``FreezeItemUnset`` for a caller that does not name one. The
convenient default — "all of them" — is a decision about the analysis made by the
code rather than by the author, and it is invisible in the output.

Offline and read-only: this module filters frames and reads a declaration file the
caller names. It writes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

import pandas as pd

from aperv_tool.analysis.envelope import Denominator

#: The column carrying the application id at every Layer-0 grain. It is the same
#: `apk` the run identity parses out of a run filename, so a frame produced by the
#: loader is scopeable without a rename.
APPLICATION_COLUMN = "apk"

#: Which of the two counts a rate was computed over. Both are always reported;
#: this names the one that sat under the numerator.
Over = Literal["reachable", "analysed"]

# The set-difference symbol the basis report prints, U+2216. Spelled out here so a
# reader of the report and a reader of a test are matching the same character and
# not a look-alike minus sign.
_SETMINUS = "∖"


class FreezeItemUnset(ValueError):
    """A pre-registration freeze item was not supplied by the caller.

    The corpus is one of them. Raised before anything is computed, naming the item,
    so the caller supplies the decided value explicitly instead of inheriting a
    default that no one wrote down.
    """


class CardinalityMismatch(ValueError):
    """A basis does not have the size it was declared to have.

    Raised for a declared count that disagrees with the members, and for a member
    listed twice — a repeated id in a hand-maintained subset file silently shrinks
    a basis by one, which is precisely the class of drift this module exists to
    make loud.
    """


@dataclass(frozen=True, slots=True)
class Basis:
    """A named set of application ids whose size is asserted, not assumed.

    Attributes:
        name: How the basis is referred to in a report. Descriptive, because the
            relation report is read by a human deciding whether a difference
            matters.
        members: The application ids, deduplicated.
        cardinality: The size the basis was declared to have, checked against
            ``members`` on construction.
    """

    name: str
    members: frozenset[str]
    cardinality: int

    def __post_init__(self) -> None:
        if len(self.members) != self.cardinality:
            raise CardinalityMismatch(
                f"basis {self.name!r} declares {self.cardinality} members but holds "
                f"{len(self.members)}"
            )

    @classmethod
    def declare(cls, name: str, members: Iterable[str], *, cardinality: int) -> "Basis":
        """Build a basis from any iterable of ids, rejecting a repeated one.

        Args:
            name: The basis name used in reports.
            members: Application ids. Consumed once.
            cardinality: The size the caller claims. Checked.

        Returns:
            The ``Basis``.

        Raises:
            CardinalityMismatch: An id appears more than once, or the declared
                cardinality disagrees with the number of distinct ids.
        """
        listed = list(members)
        unique = frozenset(listed)
        if len(listed) != len(unique):
            repeated = sorted({item for item in unique if listed.count(item) > 1})
            raise CardinalityMismatch(
                f"basis {name!r} lists an application more than once: "
                f"{', '.join(repeated)}"
            )
        return cls(name=name, members=unique, cardinality=cardinality)

    def relate(self, other: "Basis") -> "BasisRelation":
        """The set relations between this basis and a neighbouring one.

        Args:
            other: The neighbouring basis.

        Returns:
            The ``BasisRelation``, whose ``report`` names every member of both
            differences.
        """
        return BasisRelation(
            left=self,
            right=other,
            only_left=tuple(sorted(self.members - other.members)),
            only_right=tuple(sorted(other.members - self.members)),
            shared=tuple(sorted(self.members & other.members)),
        )


@dataclass(frozen=True, slots=True)
class BasisRelation:
    """How two bases differ, by member name rather than by count.

    Attributes:
        left: The basis on the left of the difference.
        right: The basis on the right.
        only_left: Members of ``left`` absent from ``right``, sorted.
        only_right: Members of ``right`` absent from ``left``, sorted.
        shared: Members of both, sorted.
    """

    left: Basis
    right: Basis
    only_left: tuple[str, ...]
    only_right: tuple[str, ...]
    shared: tuple[str, ...]

    def report(self) -> str:
        """The relation as text, with both differences enumerated by name.

        The cardinalities appear in the set-difference notation the reader already
        uses when comparing two bases — ``|163∖162| = 1`` — and the members that
        make up the difference follow on the same line, because a difference of
        one that does not say which one sends the next reader back to the data.

        Returns:
            A multi-line report. Never empty: two identical bases report zero on
            both sides, which is itself the finding.
        """
        return "\n".join(
            (
                f"{self.left.name} ({self.left.cardinality}) vs "
                f"{self.right.name} ({self.right.cardinality})",
                _difference_line(self.left, self.right, self.only_left),
                _difference_line(self.right, self.left, self.only_right),
                f"  shared = {len(self.shared)}",
            )
        )


def _difference_line(left: Basis, right: Basis, members: tuple[str, ...]) -> str:
    """One side of a relation report: the count, then the members that make it."""
    named = ", ".join(members) if members else "(none)"
    return (
        f"  |{left.cardinality}{_SETMINUS}{right.cardinality}| = "
        f"{len(members)}: {named}"
    )


@dataclass(frozen=True, slots=True)
class Rate:
    """A fraction that cannot be read without the corpus it was computed on.

    The corpus is a field, not an annotation added by whoever formats the table,
    so a rate that travels through a frame, a pickle or a log still says what it
    is a rate of. It is the same ``Denominator`` the estimator's envelope will
    carry, so the pair does not have to be reconstructed downstream.

    Attributes:
        numerator: The count on top.
        over: Which of the corpus's two counts the numerator was divided by.
        corpus: Reachable, analysed, and the subset's recorded reason.
    """

    numerator: int
    over: Over
    corpus: Denominator

    @property
    def reachable(self) -> int:
        """Applications the campaign ran over."""
        return self.corpus.reachable

    @property
    def analysed(self) -> int:
        """Applications the declared subset retained."""
        return self.corpus.analysed

    @property
    def reason(self) -> str:
        """Why the subset was declared, as the caller recorded it."""
        return self.corpus.reason

    @property
    def denominator(self) -> int:
        """The count under the numerator — the one ``over`` names."""
        return self.reachable if self.over == "reachable" else self.analysed

    @property
    def value(self) -> float:
        """The fraction itself. Only reachable through an object holding both."""
        return self.numerator / self.denominator

    def __str__(self) -> str:
        return (
            f"{self.numerator}/{self.denominator} = {self.value:.4f} "
            f"(over {self.over}; reachable={self.reachable}, "
            f"analysed={self.analysed}; {self.reason})"
        )


@dataclass(frozen=True, slots=True)
class CorpusScope:
    """The two bases a scoped analysis runs against, and why it was scoped.

    This is the object a Layer-4 denominator is built from; it is not one itself.
    It holds the corpus decision — which applications, and on whose authority —
    at the grain the decision was made.

    Attributes:
        reachable: Every application present in the frame handed to ``scope``.
        analysed: The declared subset actually analysed.
        reason: The recorded justification for the subset.
    """

    reachable: Basis
    analysed: Basis
    reason: str

    @property
    def denominator(self) -> Denominator:
        """The two cardinalities and the reason, in the form an envelope takes."""
        return Denominator(
            reachable=self.reachable.cardinality,
            analysed=self.analysed.cardinality,
            reason=self.reason,
        )

    def rate(self, numerator: int, *, over: Over) -> Rate:
        """A fraction over one of the two bases, carrying both.

        Args:
            numerator: The count on top. Must fit inside the chosen denominator —
                a numerator larger than its basis means the count was taken over a
                different corpus than the one named here.
            over: Which basis the numerator was counted within.

        Returns:
            The ``Rate``.

        Raises:
            ValueError: The numerator is negative or exceeds the denominator.
        """
        corpus = self.denominator
        denominator = corpus.reachable if over == "reachable" else corpus.analysed
        if numerator < 0 or numerator > denominator:
            raise ValueError(
                f"numerator {numerator} does not fit the {over} basis of "
                f"{denominator}"
            )
        return Rate(numerator=numerator, over=over, corpus=corpus)

    def relation(self) -> BasisRelation:
        """What the subset removed, by name: reachable relative to analysed."""
        return self.reachable.relate(self.analysed)


def read_subset(path: Path) -> list[str]:
    """Application ids from a declaration file, one per line.

    Blank lines and ``#`` comments are skipped so the file can carry the reason a
    given application is in or out beside the id itself, where the next reader will
    actually see it.

    Args:
        path: The subset declaration.

    Returns:
        The ids in file order. Duplicates are kept here and rejected by ``Basis``,
        which is where the message can name the basis.
    """
    ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped:
            ids.append(stripped)
    return ids


def scope(
    frame: pd.DataFrame,
    *,
    subset: Path | Iterable[str] | None = None,
    reason: str,
) -> tuple[pd.DataFrame, CorpusScope]:
    """Restrict a frame to a declared corpus, keeping both denominators.

    The corpus is a freeze item, so there is no "scope to everything" shortcut: a
    caller analysing the whole campaign declares the whole campaign and says why.
    That declaration costs one line and is the difference between a corpus that was
    chosen and a corpus that happened.

    Args:
        frame: Any frame carrying the ``apk`` column — the Layer-0 run grain, or an
            already-aggregated per-application frame.
        subset: The declared corpus, as a file of application ids or an iterable of
            them. ``None`` — including by omission — is not a corpus.
        reason: Why this subset was declared. Recorded on the scope and on every
            rate derived from it.

    Returns:
        The filtered frame, re-indexed, and the ``CorpusScope`` holding the
        reachable and analysed bases.

    Raises:
        FreezeItemUnset: ``subset`` was not supplied.
        ValueError: ``reason`` is blank, the frame has no application column, or
            the subset names applications the frame does not contain — the last
            being a declaration written against a different campaign, which would
            otherwise scope to an intersection nobody declared.
        CardinalityMismatch: The subset lists an application more than once.
    """
    if subset is None:
        raise FreezeItemUnset(
            "corpus: the analysed corpus is a pre-registration freeze item and has "
            "no default; declare the application ids and the reason"
        )
    if not reason.strip():
        raise ValueError("a declared corpus carries the reason it was declared")
    if APPLICATION_COLUMN not in frame.columns:
        raise ValueError(
            f"frame has no {APPLICATION_COLUMN!r} column; columns are "
            f"{list(frame.columns)}"
        )

    declared = read_subset(subset) if isinstance(subset, Path) else list(subset)
    reachable_ids = set(frame[APPLICATION_COLUMN])
    reachable = Basis.declare(
        "reachable", reachable_ids, cardinality=len(reachable_ids)
    )
    analysed = Basis.declare("analysed", declared, cardinality=len(set(declared)))

    unknown = sorted(analysed.members - reachable.members)
    if unknown:
        raise ValueError(
            f"the declared corpus names {len(unknown)} application(s) absent from "
            f"the frame: {', '.join(unknown)}"
        )

    analysed_frame = frame[frame[APPLICATION_COLUMN].isin(analysed.members)]
    return (
        analysed_frame.reset_index(drop=True),
        CorpusScope(reachable=reachable, analysed=analysed, reason=reason),
    )
