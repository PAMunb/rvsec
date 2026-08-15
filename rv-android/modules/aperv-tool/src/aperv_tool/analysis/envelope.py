"""The type a number has to fit into before it can leave the library.

The organising rule of this analysis layer is not "compute the statistic". It is
**compute the statistic and refuse to emit it without what makes it
interpretable**, and this module is where that refusal is made structural rather
than remembered.

The rule was learned from readings that went wrong on numbers that were each
correct in isolation:

- a mean gain of ``+14 pp`` reported beside a median of ``0.000`` — the mean was
  right, and the distribution it summarised had almost no non-zero pair in it;
- an ``n_disc`` printed with neither ``b``, ``c`` nor the direction, so a
  discordance count carried no information about which arm it favoured;
- a ``mop_unique`` column that was a *mean over replicas* read as a count, in a
  file whose header said neither;
- a detection rate quoted over an unnamed subset, whose reader had no way to
  know whether the denominator was the corpus or the part of it that survived
  an exclusion.

None of those is a computation error. Every one of them is a number that
travelled without its denominator, its convention, its exclusions or its
companions, and an ``Envelope`` is the smallest object that cannot.

Every Layer-2 estimator returns one (INV-CAN-14), ``emit`` consumes nothing else,
and none of them knows which question it is answering — the envelope carries what
makes a number readable, never what makes it interesting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Union

#: What an estimate's fields may be. Deliberately narrow: a nested structure
#: inside an estimate is a table pretending to be a number, and it would arrive
#: at ``emit`` with no column to occupy.
EstimateValue = Union[float, int, str, bool]


@dataclass(frozen=True)
class Denominator:
    """The two counts every fraction in this library is computed against.

    A rate needs both because they answer different questions and disagree
    whenever anything was excluded. ``reachable`` is how many units the campaign
    could have measured; ``analysed`` is how many it did. Reporting only the
    first overstates coverage, reporting only the second hides the exclusion, and
    reporting neither — the common case in the campaign scripts this library
    replaces — makes a fraction unreadable (INV-CAN-09).

    Attributes:
        reachable: Cardinality of the basis before any subset or exclusion.
        analysed: Cardinality actually used for the estimate.
        reason: Why ``analysed`` is smaller, recorded by the caller that made
            the subset. Required whenever the two differ: a subset whose reason
            nobody wrote down cannot be judged later, and "declared subset" with
            no declaration is how a corpus quietly becomes the corpus that
            worked.
    """

    reachable: int
    analysed: int
    reason: str = ""

    def __post_init__(self) -> None:
        """Reject the two states that would make the pair unreadable.

        Raises:
            ValueError: ``analysed`` exceeds ``reachable`` (a fraction above 1
                waiting to happen), or a subset was taken with no reason given.
        """
        if self.analysed > self.reachable:
            raise ValueError(
                f"analysed={self.analysed} exceeds reachable={self.reachable}"
            )
        if self.analysed != self.reachable and not self.reason:
            raise ValueError(
                f"a subset ({self.analysed} of {self.reachable}) needs a recorded "
                "reason"
            )


@dataclass(frozen=True)
class Exclusion:
    """One unit left out of an estimate, named and explained.

    Exclusions travel *inside* the envelope rather than in a log beside it, so a
    table of results carries its own attrition. A count of exclusions with no
    identities is not enough: the recurring question about a dropped run is
    which one, and a reader who cannot answer it cannot tell an incidental loss
    from a systematic one.

    Attributes:
        identity: The unit excluded — a run identity, an application id, a pair.
        reason: Why, in the words of whatever made the decision (a gate verdict,
            an admissibility reason, a missing input).
    """

    identity: str
    reason: str


@dataclass(frozen=True)
class Envelope:
    """An estimate together with everything needed to read it.

    Frozen, and every field required: an envelope assembled by parts is an
    envelope that can be emitted half-built, which is the failure mode the type
    exists to prevent.

    Attributes:
        estimand: What was estimated, named as the caller decided it — e.g.
            ``diff_of_trimmed_means_10``, ``mcnemar_exact``. Two columns whose
            estimands differ are detectable from labels alone, which is what
            makes a mean silently mixed into a ratio of medians visible.
        n: The units the estimate was computed over — pairs for a paired test,
            observations for a fit. Distinct from the denominator, which counts
            the basis, and reported separately because they differ whenever
            anything was paired or dropped.
        denominator: Both cardinalities of the basis, and the subset's reason.
        estimate: The estimate's fields, flat. A paired-binary result carries
            ``b``, ``c``, ``n_disc``, the direction and ``p`` here together
            (INV-CAN-15) — the type does not enforce which fields belong to
            which estimator, but it does force them into one place with names.
        ci: The interval, or None when the estimator produced none. None is not
            "not significant"; it is "no interval was computed", and the two are
            different claims.
        convention: The decisions that produced the number and would change it —
            dedup key, replica rule, trimming, exclusion policy. A number
            computed under a different convention is a different number, and
            this is where a reader finds out which one they have.
        exclusions: The units left out, by identity and reason.
        provenance_ref: The ``Provenance.ref`` of the run that produced the
            estimate. A reference rather than the record itself, because a
            provenance carries timestamps and an estimate that carries a
            timestamp is not re-derivable bit for bit.
    """

    estimand: str
    n: int
    denominator: Denominator
    estimate: Mapping[str, EstimateValue]
    ci: Optional[tuple[float, float]]
    convention: Mapping[str, str]
    exclusions: tuple[Exclusion, ...]
    provenance_ref: str
