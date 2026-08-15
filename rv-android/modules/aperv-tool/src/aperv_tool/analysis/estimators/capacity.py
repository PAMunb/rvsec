"""What a paired binary design can resolve, computed before it is run.

A paired binary comparison spends its whole sample on the discordant pairs: the
applications where the two arms disagree. Everything else is discarded by the
test. So the design question is not "how many applications" but "how many
disagreements will those applications produce", and it has an arithmetic answer
that does not need the data.

The reason this is a module rather than a note is the exact-McNemar power floor.
Six discordant pairs cannot reach alpha = 0.025 however lopsided they are, so a
design whose expected discordance is five has already decided its own result. The
envelope therefore reports the expected count **beside** the floor and says
whether the design clears it, which is the same reporting rule
``paired_binary`` follows after the fact (INV-CAN-15), applied before.

The model is deliberately the simplest one that uses the design's parameters:
per-unit success probabilities on each arm, with the two arms independent within
a unit. Independence is optimistic — a paired design exists because the arms are
correlated — and the envelope says so, because the expected discordance under
correlation is *lower* and the number here is therefore a ceiling, not a
prediction.

Replicas enter through the rule that collapses them into one binary value per
unit, which is why the rule is a required argument: majority, union and unanimity
turn the same per-replica probability into three different per-unit ones, and at
three replicas the spread between them is wide.

The outcome's name is carried through and is not decorative. A capacity result
quoted against the wrong outcome is the failure this argument prevents: the
expected discordance for a coverage threshold has nothing to say about a
violation count, and an envelope with no outcome name cannot be caught doing it.
"""

from __future__ import annotations

from typing import Union

from scipy.stats import binom

from aperv_tool.analysis.envelope import Denominator, Envelope
from aperv_tool.analysis.estimators.paired_binary import power_floor

#: How replicas of one unit are collapsed into that unit's binary value.
REPLICA_RULES = ("majority", "union", "unanimity")


def unit_probability(p_replica: float, *, replicas: int, replica_rule: str) -> float:
    """Probability that a unit reads positive, given its per-replica probability.

    Args:
        p_replica: Probability that a single replica reads positive.
        replicas: Replicas per unit. At one replica every rule agrees, which is
            the final campaign's design and a useful sanity check.
        replica_rule: ``"majority"`` (more than half the replicas positive),
            ``"union"`` (at least one) or ``"unanimity"`` (all).

    Returns:
        The unit-level probability.

    Raises:
        ValueError: ``replica_rule`` is not one of ``REPLICA_RULES``, ``replicas``
            is below 1, or ``p_replica`` is outside [0, 1].
    """
    if replica_rule not in REPLICA_RULES:
        raise ValueError(f"replica_rule must be one of {REPLICA_RULES}")
    if replicas < 1:
        raise ValueError(f"replicas must be at least 1, got {replicas}")
    if not 0.0 <= p_replica <= 1.0:
        raise ValueError(f"p_replica must lie in [0, 1], got {p_replica}")

    if replica_rule == "union":
        return float(1.0 - (1.0 - p_replica) ** replicas)
    if replica_rule == "unanimity":
        return float(p_replica**replicas)
    # Majority: strictly more than half the replicas. At an even count this is a
    # strict majority, not a tie-break, so the rule stays deterministic.
    threshold = replicas // 2
    return float(binom.sf(threshold, replicas, p_replica))


def expected_discordance(
    p_unit: float,
    *,
    n: int,
    replicas: int,
    effect: float,
    outcome_name: str,
    replica_rule: str,
    alpha: float,
    provenance_ref: str = "",
) -> Envelope:
    """Expected discordant pairs of a paired binary design, beside the power floor.

    Args:
        p_unit: Per-replica probability of a positive reading on the reference
            arm.
        n: Units in the design.
        replicas: Replicas per unit.
        effect: Additive shift in the per-replica probability on the other arm.
            The shifted value is clipped to [0, 1] and the clip is reported.
        outcome_name: The outcome this capacity is computed for. Required, so a
            capacity result cannot be quoted against a different one.
        replica_rule: How replicas collapse into a unit's value.
        alpha: The level the design will be read at, for the power floor.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``expected_n_disc``, ``p_discordant``, both
        unit-level probabilities, ``power_floor_n_disc`` and
        ``reaches_power_floor``.

    Raises:
        ValueError: ``n`` is below 1, or a probability argument is out of range.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")

    shifted = p_unit + effect
    clipped = not 0.0 <= shifted <= 1.0
    shifted = min(max(shifted, 0.0), 1.0)

    p_reference = unit_probability(p_unit, replicas=replicas, replica_rule=replica_rule)
    p_other = unit_probability(shifted, replicas=replicas, replica_rule=replica_rule)
    p_discordant = p_reference * (1.0 - p_other) + p_other * (1.0 - p_reference)
    expected = float(n * p_discordant)

    floor = power_floor(alpha)
    estimate: dict[str, Union[float, int, str, bool]] = {
        "outcome_name": outcome_name,
        "expected_n_disc": expected,
        "p_discordant": float(p_discordant),
        "p_unit_reference": float(p_reference),
        "p_unit_other": float(p_other),
        "p_replica_reference": float(p_unit),
        "p_replica_other": float(shifted),
        "effect": float(effect),
        "effect_clipped": bool(clipped),
        "n": int(n),
        "replicas": int(replicas),
        "replica_rule": replica_rule,
        "alpha": float(alpha),
        "power_floor_n_disc": floor,
        "reaches_power_floor": bool(expected >= floor),
    }

    return Envelope(
        estimand="expected_discordance",
        n=int(n),
        denominator=Denominator(reachable=int(n), analysed=int(n)),
        estimate=estimate,
        ci=None,
        convention={
            "outcome": outcome_name,
            "model": "independent arms within a unit; the real paired design is "
            "positively correlated, under which discordance is lower, so this is "
            "a ceiling rather than a prediction",
            "replica_rule": replica_rule,
            "power_floor": f"smallest n_disc able to reach alpha={alpha} is {floor}",
            "effect": "an additive shift in the per-replica probability, applied "
            "before the replica rule",
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )


__all__ = ["REPLICA_RULES", "expected_discordance", "unit_probability"]
