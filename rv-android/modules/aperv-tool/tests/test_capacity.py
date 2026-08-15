"""What a design can resolve, against probabilities that can be computed by hand.

The replica rules are checked at three replicas and p = 0.5, where all three
answers are exact binomial fractions: majority 1/2, union 7/8, unanimity 1/8. The
expected discordance is then checked against the power floor, in both directions,
because the whole value of the estimator is telling a design it cannot resolve
anything before it runs.
"""

from __future__ import annotations

import pytest

from aperv_tool.analysis.estimators import capacity


class TestUnitProbability:
    """The three rules at three replicas and a fair coin."""

    def test_majority_of_three(self) -> None:
        assert capacity.unit_probability(
            0.5, replicas=3, replica_rule="majority"
        ) == pytest.approx(0.5)

    def test_union_of_three(self) -> None:
        assert capacity.unit_probability(
            0.5, replicas=3, replica_rule="union"
        ) == pytest.approx(0.875)

    def test_unanimity_of_three(self) -> None:
        assert capacity.unit_probability(
            0.5, replicas=3, replica_rule="unanimity"
        ) == pytest.approx(0.125)

    def test_one_replica_makes_every_rule_agree(self) -> None:
        """The final campaign's design; the rules must collapse onto each other."""
        for rule in capacity.REPLICA_RULES:
            assert capacity.unit_probability(
                0.3, replicas=1, replica_rule=rule
            ) == pytest.approx(0.3)

    def test_an_unknown_rule_is_refused(self) -> None:
        with pytest.raises(ValueError, match="replica_rule"):
            capacity.unit_probability(0.5, replicas=3, replica_rule="plurality")


class TestExpectedDiscordance:
    """The count, the floor, and the outcome it belongs to."""

    def test_capacity_records_outcome(self) -> None:
        """The outcome's name reaches both the estimate and the convention."""
        envelope = capacity.expected_discordance(
            0.4,
            n=162,
            replicas=3,
            effect=0.1,
            outcome_name="mop_unique_above_zero",
            replica_rule="majority",
            alpha=0.025,
        )

        assert envelope.estimate["outcome_name"] == "mop_unique_above_zero"
        assert envelope.convention["outcome"] == "mop_unique_above_zero"
        assert envelope.estimand == "expected_discordance"

    def test_a_hand_computable_design(self) -> None:
        """Independent fair coins at one replica: half the pairs disagree."""
        envelope = capacity.expected_discordance(
            0.5,
            n=100,
            replicas=1,
            effect=0.0,
            outcome_name="anything",
            replica_rule="majority",
            alpha=0.025,
        )

        assert envelope.estimate["p_discordant"] == pytest.approx(0.5)
        assert envelope.estimate["expected_n_disc"] == pytest.approx(50.0)
        assert envelope.estimate["reaches_power_floor"] is True
        assert envelope.estimate["power_floor_n_disc"] == 7

    def test_a_design_that_cannot_resolve_anything(self) -> None:
        """Near-saturated arms on ten units: 0.15 expected discordant pairs."""
        envelope = capacity.expected_discordance(
            0.99,
            n=10,
            replicas=1,
            effect=0.005,
            outcome_name="saturated_coverage",
            replica_rule="majority",
            alpha=0.025,
        )

        assert envelope.estimate["expected_n_disc"] < 1.0
        assert envelope.estimate["reaches_power_floor"] is False

    def test_the_replica_rule_changes_the_answer(self) -> None:
        common = dict(
            n=162,
            replicas=3,
            effect=0.1,
            outcome_name="anything",
            alpha=0.025,
        )
        majority = capacity.expected_discordance(0.4, replica_rule="majority", **common)
        union = capacity.expected_discordance(0.4, replica_rule="union", **common)

        assert majority.estimate["expected_n_disc"] != union.estimate["expected_n_disc"]

    def test_an_effect_pushed_out_of_range_is_clipped_and_reported(self) -> None:
        envelope = capacity.expected_discordance(
            0.9,
            n=50,
            replicas=1,
            effect=0.5,
            outcome_name="anything",
            replica_rule="majority",
            alpha=0.025,
        )

        assert envelope.estimate["effect_clipped"] is True
        assert envelope.estimate["p_replica_other"] == pytest.approx(1.0)

    def test_the_independence_assumption_is_declared(self) -> None:
        envelope = capacity.expected_discordance(
            0.4,
            n=10,
            replicas=1,
            effect=0.1,
            outcome_name="anything",
            replica_rule="majority",
            alpha=0.025,
        )

        assert "ceiling rather than a prediction" in envelope.convention["model"]

    def test_an_empty_design_is_refused(self) -> None:
        with pytest.raises(ValueError, match="n must be at least 1"):
            capacity.expected_discordance(
                0.4,
                n=0,
                replicas=1,
                effect=0.1,
                outcome_name="anything",
                replica_rule="majority",
                alpha=0.025,
            )
