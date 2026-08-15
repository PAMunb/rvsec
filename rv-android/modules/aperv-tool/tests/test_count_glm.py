"""The count model against rate ratios that were chosen before the data existed.

The synthetic campaign below is generated at known per-arm rate ratios (1.6 and
2.4 against the reference), with a log-normal size covariate whose true
elasticity is 0.5 and a per-application frailty that makes the counts
overdispersed and clustered — the three features the specification exists to
handle. Recovery of those rate ratios by the covariate specification is the
correctness evidence for the module.

The pure-offset specification is the same data fitted with the size term
*constrained* to an elasticity of 1. That constraint is wrong by construction
here, exactly as it is wrong in the sibling study, and the qualitative signature
of the misspecification is asserted rather than described: the dispersion
inflates, and every arm contrast's interval widens. The intercept is deliberately
excluded from that comparison — it absorbs the offset and is not the same
quantity in the two fits.

Nothing here reads a campaign artefact, and no fit is warm-started from anything
but a Poisson fit carrying the same offset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.estimators import count_glm

#: The rate ratios the generator writes into the data, against the reference arm.
TRUE_IRR = {"ape": 1.0, "arm_b": 1.6, "arm_c": 2.4}

#: The true elasticity of the count with respect to application size. Chosen
#: below 1 so the pure-offset specification, which pins it at 1, is misspecified.
TRUE_ELASTICITY = 0.5


def synthetic_campaign(
    applications: int = 120, replicas: int = 3, seed: int = 20260815
) -> pd.DataFrame:
    """Counts generated at ``TRUE_IRR`` with a log-normal size covariate.

    Args:
        applications: Number of applications.
        replicas: Runs per (application, arm).
        seed: Seed of the generator, so every assertion below is deterministic.

    Returns:
        A frame with ``apk``, ``arm``, ``rep``, ``size``, ``log_size`` and
        ``count``.
    """
    rng = np.random.default_rng(seed)
    names = [f"app{i:03d}.apk" for i in range(applications)]
    sizes = np.exp(rng.normal(1.2, 0.7, size=applications)) + 1.0

    rows = []
    for name, size in zip(names, sizes):
        # One frailty per application: it is what makes the runs of an
        # application correlated, which is what the cluster-robust errors answer.
        frailty = rng.gamma(4.0, 1.0 / 4.0)
        for arm, ratio in TRUE_IRR.items():
            for rep in range(1, replicas + 1):
                mean = 1.5 * ratio * size**TRUE_ELASTICITY * frailty
                rows.append(
                    {
                        "apk": name,
                        "arm": arm,
                        "rep": rep,
                        "size": size,
                        "count": int(rng.poisson(mean)),
                    }
                )
    frame = pd.DataFrame(rows)
    frame["log_size"] = np.log(frame["size"])
    return frame


@pytest.fixture(scope="module")
def campaign() -> pd.DataFrame:
    return synthetic_campaign()


@pytest.fixture(scope="module")
def covariate_fit(campaign: pd.DataFrame):
    return count_glm.fit(
        "count ~ {arm} + log_size", campaign, offset=None, reference_level="ape"
    )


@pytest.fixture(scope="module")
def offset_fit(campaign: pd.DataFrame):
    return count_glm.fit(
        "count ~ {arm}",
        campaign,
        offset=campaign["log_size"].to_numpy(),
        reference_level="ape",
    )


class TestFreezeItems:
    """The two arguments the module refuses to choose."""

    def test_offset_required(self, campaign: pd.DataFrame) -> None:
        with pytest.raises(FreezeItemUnset, match="offset"):
            count_glm.fit("count ~ {arm}", campaign, reference_level="ape")

    def test_offset_none_is_explicit(self, campaign: pd.DataFrame) -> None:
        """``None`` is a legal value; omission is not, and they differ."""
        envelope = count_glm.fit(
            "count ~ {arm}", campaign, offset=None, reference_level="ape"
        )

        assert envelope.estimate["offset_supplied"] is False
        assert envelope.convention["offset"] == "none"

    def test_reference_level_is_required_too(self, campaign: pd.DataFrame) -> None:
        with pytest.raises(FreezeItemUnset, match="reference_level"):
            count_glm.fit("count ~ {arm}", campaign, offset=None)

    def test_a_reference_with_no_arm_term_is_refused(
        self, campaign: pd.DataFrame
    ) -> None:
        """A declared level that codes nothing would do nothing, silently."""
        with pytest.raises(ValueError, match="no .* to code against"):
            count_glm.fit(
                "count ~ log_size", campaign, offset=None, reference_level="ape"
            )

    def test_an_arm_term_with_no_reference_is_refused(
        self, campaign: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="reference_level is None"):
            count_glm.fit("count ~ {arm}", campaign, offset=None, reference_level=None)


class TestRecovery:
    """The correctness evidence: known rate ratios, recovered."""

    def test_synth_irr_recovered_both_specs(self, covariate_fit, offset_fit) -> None:
        """Covariate intervals cover the truth; the offset fit converges."""
        assert covariate_fit.estimate["converged"] is True
        for arm, ratio in TRUE_IRR.items():
            if arm == "ape":
                continue
            term = f"arm[{arm}]"
            low = covariate_fit.estimate[f"irr_lo__{term}"]
            high = covariate_fit.estimate[f"irr_hi__{term}"]
            assert low < ratio < high, f"{term}: {ratio} outside ({low}, {high})"

        # The elasticity is a fitted coefficient here, and its interval covers
        # the generator's value.
        assert (
            covariate_fit.estimate["irr_lo__log_size"]
            < np.exp(TRUE_ELASTICITY)
            < covariate_fit.estimate["irr_hi__log_size"]
        )

        assert offset_fit.estimate["converged"] is True
        assert offset_fit.estimate["n_arm_contrasts"] == 2

    def test_offset_alpha_inflates(self, covariate_fit, offset_fit) -> None:
        """The misspecification's signature: dispersion up, every contrast wider.

        Only the arm contrasts are compared. The intercept absorbs the offset and
        is a different quantity in the two fits, so widening is not defined for
        it.
        """
        assert (
            offset_fit.estimate["alpha"] > covariate_fit.estimate["alpha"]
        ), "the constrained elasticity did not push residual dispersion up"

        for arm in TRUE_IRR:
            if arm == "ape":
                continue
            term = f"arm[{arm}]"
            covariate_width = (
                covariate_fit.estimate[f"irr_hi__{term}"]
                - covariate_fit.estimate[f"irr_lo__{term}"]
            )
            offset_width = (
                offset_fit.estimate[f"irr_hi__{term}"]
                - offset_fit.estimate[f"irr_lo__{term}"]
            )
            assert offset_width > covariate_width, term

    def test_the_warm_start_is_declared(self, offset_fit) -> None:
        assert "same offset" in offset_fit.convention["start"]
        assert offset_fit.estimate["offset_supplied"] is True


class TestReferenceLevel:
    """The coding is a parameter, and the reference decides the contrasts."""

    def test_reference_level_param(self) -> None:
        """Five arms coded against one reference give four contrasts."""
        frame = synthetic_campaign(applications=40, replicas=1, seed=5)
        extra = frame[frame["arm"] == "arm_b"].copy()
        extra["arm"] = "arm_d"
        more = frame[frame["arm"] == "arm_c"].copy()
        more["arm"] = "arm_e"
        five = pd.concat([frame, extra, more], ignore_index=True)

        envelope = count_glm.fit(
            "count ~ {arm}", five, offset=None, reference_level="ape"
        )

        contrasts = [key for key in envelope.estimate if key.startswith("irr__arm[")]
        assert len(contrasts) == 4
        assert envelope.estimate["n_arm_contrasts"] == 4
        assert "irr__arm[ape]" not in envelope.estimate
        assert envelope.estimate["reference_level"] == "ape"

    def test_a_different_reference_inverts_a_contrast(self) -> None:
        frame = synthetic_campaign(applications=40, replicas=1, seed=9)

        against_first = count_glm.fit(
            "count ~ {arm}", frame, offset=None, reference_level="ape"
        )
        against_last = count_glm.fit(
            "count ~ {arm}", frame, offset=None, reference_level="arm_c"
        )

        assert against_first.estimate["irr__arm[arm_c]"] > 1.0
        assert against_last.estimate["irr__arm[ape]"] < 1.0

    def test_the_arm_column_is_a_parameter(self) -> None:
        frame = synthetic_campaign(applications=30, replicas=1, seed=13)
        frame = frame.rename(columns={"arm": "tool_variant"})

        envelope = count_glm.fit(
            "count ~ {arm}",
            frame,
            offset=None,
            reference_level="ape",
            arm_column="tool_variant",
        )

        assert envelope.estimate["n_arm_contrasts"] == 2
        assert "irr__tool_variant[arm_b]" in envelope.estimate

    def test_no_monkey_literal(self) -> None:
        """No level of the sibling study's arm vocabulary survives in the module."""
        source = Path(count_glm.__file__).read_text(encoding="utf-8")

        assert "monkey" not in source.lower()


class TestModelDiagnostics:
    """The three checks the fitter carries beyond the coefficient table."""

    def test_the_dispersion_test_is_boundary_corrected(self, covariate_fit) -> None:
        assert covariate_fit.estimate["lr_nb_vs_poisson"] > 0.0
        assert 0.0 <= covariate_fit.estimate["lr_p_boundary_corrected"] <= 0.5
        assert "boundary-corrected" in covariate_fit.convention["lr_test"]

    def test_the_zero_predictor_reports_both_counts(self, covariate_fit) -> None:
        assert covariate_fit.estimate["zeros_observed"] >= 0
        assert covariate_fit.estimate["zeros_expected_nb"] > 0.0

    def test_the_clusters_are_the_applications(self, covariate_fit) -> None:
        assert covariate_fit.estimate["n_clusters"] == 120
        assert "cluster-robust" in covariate_fit.convention["standard_errors"]

    def test_separation_reported(self) -> None:
        """An arm that never produces a count drives its coefficient off the scale."""
        rng = np.random.default_rng(7)
        rows = []
        for index in range(40):
            name = f"app{index:02d}.apk"
            for arm, mean in (("ape", 4.0), ("silent", 0.0)):
                for _ in range(3):
                    rows.append(
                        {"apk": name, "arm": arm, "count": int(rng.poisson(mean))}
                    )
        frame = pd.DataFrame(rows)

        envelope = count_glm.fit(
            "count ~ {arm}", frame, offset=None, reference_level="ape"
        )

        assert envelope.estimate["separation_suspected"] is True
        assert "arm[silent]" in envelope.estimate["separation_terms"]

    def test_a_healthy_fit_is_not_flagged(self, covariate_fit) -> None:
        assert covariate_fit.estimate["separation_suspected"] is False
        assert covariate_fit.estimate["separation_terms"] == ""


class TestEnvelopeShape:
    """What a regression puts in a structure built for one number."""

    def test_every_term_carries_its_whole_row(self, covariate_fit) -> None:
        for prefix in ("coef__", "se__", "p__", "irr__", "irr_lo__", "irr_hi__"):
            assert f"{prefix}arm[arm_b]" in covariate_fit.estimate

    def test_the_dispersion_has_no_rate_ratio(self, covariate_fit) -> None:
        assert "irr__alpha" not in covariate_fit.estimate
        assert "alpha_ci_lo" in covariate_fit.estimate

    def test_the_envelope_has_no_single_interval(self, covariate_fit) -> None:
        assert covariate_fit.ci is None
        assert "no single interval" in covariate_fit.convention["intervals"]

    def test_the_resolved_formula_is_recorded(self, covariate_fit) -> None:
        assert "Treatment('ape')" in covariate_fit.convention["formula"]
        assert count_glm.ARM_PLACEHOLDER not in covariate_fit.convention["formula"]


class TestHelpers:
    """The two string functions the table depends on."""

    def test_short_term_drops_the_coding(self) -> None:
        assert count_glm.short_term("C(arm, Treatment('ape'))[T.arm_b]") == "arm[arm_b]"
        assert count_glm.short_term("C(timeout)[T.300]") == "timeout[300]"

    def test_short_term_leaves_a_plain_name_alone(self) -> None:
        assert count_glm.short_term("log_size") == "log_size"
        assert count_glm.short_term("Intercept") == "Intercept"

    def test_treatment_term_builds_the_factor(self) -> None:
        assert count_glm.treatment_term("arm", "ape") == "C(arm, Treatment('ape'))"


class TestDefectiveInput:
    """States that would misalign the cluster vector or fit nothing."""

    def test_a_missing_cluster_column_is_refused(self, campaign: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="cluster column"):
            count_glm.fit(
                "count ~ {arm}",
                campaign,
                offset=None,
                reference_level="ape",
                cluster="application",
            )

    def test_an_empty_frame_is_refused(self) -> None:
        empty = pd.DataFrame({"apk": [], "arm": [], "count": []})

        with pytest.raises(ValueError, match="no observations"):
            count_glm.fit("count ~ {arm}", empty, offset=None, reference_level="ape")

    def test_a_mismatched_offset_is_refused(self, campaign: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="offset has"):
            count_glm.fit(
                "count ~ {arm}",
                campaign,
                offset=np.zeros(7),
                reference_level="ape",
            )

    def test_rows_the_formula_would_drop_are_refused(
        self, campaign: pd.DataFrame
    ) -> None:
        """A dropped row would shift the cluster vector without saying so."""
        holed = campaign.copy()
        holed.loc[holed.index[0], "count"] = np.nan

        with pytest.raises(ValueError, match="dropped"):
            count_glm.fit("count ~ {arm}", holed, offset=None, reference_level="ape")


class TestCompareSpecifications:
    """Whether a sensitivity changed a conclusion, decided on the envelopes."""

    def test_a_stable_pair_of_specifications_flips_nothing(
        self, covariate_fit, offset_fit
    ) -> None:
        envelope = count_glm.compare_specifications(
            covariate_fit, {"pure_offset": offset_fit}, alpha=0.05
        )

        assert envelope.estimate["direction_changed"] is False
        assert envelope.estimate["direction_flips"] == ""
        assert envelope.estimate["n_conclusions"] >= 2

    def test_a_flipped_conclusion_is_named(self, covariate_fit) -> None:
        """A hand-built sensitivity whose contrast crosses one is reported."""
        flipped = dict(covariate_fit.estimate)
        flipped["coef__arm[arm_b]"] = -abs(flipped["coef__arm[arm_b]"])
        sensitivity = type(covariate_fit)(
            estimand=covariate_fit.estimand,
            n=covariate_fit.n,
            denominator=covariate_fit.denominator,
            estimate=flipped,
            ci=None,
            convention=covariate_fit.convention,
            exclusions=(),
            provenance_ref="",
        )

        envelope = count_glm.compare_specifications(
            covariate_fit, {"flipped": sensitivity}, alpha=0.05
        )

        assert envelope.estimate["direction_changed"] is True
        assert "arm[arm_b] in flipped" in envelope.estimate["direction_flips"]

    def test_a_term_gaining_significance_is_listed_apart(self, covariate_fit) -> None:
        raised = dict(covariate_fit.estimate)
        raised["p__arm[arm_b]"] = 0.9
        main = type(covariate_fit)(
            estimand=covariate_fit.estimand,
            n=covariate_fit.n,
            denominator=covariate_fit.denominator,
            estimate=raised,
            ci=None,
            convention=covariate_fit.convention,
            exclusions=(),
            provenance_ref="",
        )

        envelope = count_glm.compare_specifications(
            main, {"original": covariate_fit}, alpha=0.05
        )

        assert "arm[arm_b] in original" in envelope.estimate["gained_significance"]
        assert "listed apart" in envelope.convention["gained_significance"]


def test_a_formula_may_call_log(campaign: pd.DataFrame) -> None:
    """`log()` inside a formula resolves, which is what `_fit_nb`'s alias is for.

    `patsy` evaluates a formula's function calls against the namespace of the
    frame that built it, so `_fit_nb` binds `log = np.log` locally. Nothing else
    exercises that line, and an unused alias is one cleanup pass away from being
    deleted as dead — which would break every formula that transforms a covariate
    inline, silently and only for the callers that use one.
    """
    frame = campaign.copy()
    frame["size"] = np.exp(frame["log_size"])

    envelope = count_glm.fit(
        "count ~ {arm} + log(size)", frame, offset=None, reference_level="ape"
    )

    assert any(term.startswith("coef__log(size)") for term in envelope.estimate)
