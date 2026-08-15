"""Negative-binomial count regression, carrying a fitter that was paid for once.

Counts of violations per run are overdispersed, repeated within an application,
and driven by how much of the application there was to find anything in. A
Poisson fit on them understates every standard error; an ordinary fit ignores the
clustering; and a fit without a size term attributes to the arm what belongs to
the application. The specification below addresses all three and is not a fresh
design: it is the fitter the sibling Android test-generation study used, carried
over in behaviour rather than reinvented, because it is twelve lines and every
one of them was learned the expensive way.

Three of those lines are load-bearing and none is obvious:

- **The negative binomial is NB2 with the dispersion estimated by maximum
  likelihood**, not fixed at 1. Fixing it silently converts the fit into a
  quasi-Poisson with the wrong likelihood, and the dispersion is exactly the
  quantity the overdispersion story rests on.
- **Standard errors are cluster-robust, grouped by application** (INV-CAN-17).
  Replicas and timeouts of one application are not independent observations, and
  treating them as such shrinks every interval by roughly the square root of the
  replica count.
- **The fit is warm-started from a Poisson fit carrying the same offset.**
  statsmodels' default start ignores the offset; with a pure-offset
  specification — no fitted size coefficient — the optimiser then walks away and
  the dispersion diverges. The warm start is also what makes the fit
  deterministic, which a parity test needs.

Everything the sibling study hardcoded is a parameter here: the reference level,
the arm column, the cluster column, the covariates (they live in the caller's
formula), the observation-count assertions and the tool labels. That is what
makes the module reusable, and INV-CAN-11 makes two of them *required*: an
``offset`` and a ``reference_level`` chosen by the code are pre-registration
decisions made by no one. ``offset=None`` — meaning no offset — is a legal
explicit value; omitting the argument is not.

The formula carries a placeholder rather than a coded factor. A caller writes
``"count ~ C(timeout) + {arm}"`` and supplies ``reference_level``; the module
substitutes the treatment coding. The alternative — rewriting a bare column name
inside the formula by pattern — would edit a string the caller believes it owns.

``statsmodels`` is imported inside the fitting functions. It costs about a second
and pulls a large surface with it, and the three shipped readers have nothing to
do with estimation; a module-level import here would tax every run that only
wanted to read a trace, and would pass every functional test while doing it.
"""

from __future__ import annotations

import re
import warnings
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.envelope import Denominator, Envelope

#: Sentinel for a freeze item the caller did not supply. Distinct from ``None``,
#: which is a legal explicit value for both freeze items in this module.
_UNSET: Any = object()

#: What a caller writes in a formula where the arm factor belongs.
ARM_PLACEHOLDER = "{arm}"

#: The name the dispersion parameter carries in the fitted result.
DISPERSION = "alpha"

#: |coefficient| above which a term is reported as suspected separation. On the
#: log scale this is a rate ratio of about 22,000: no arm effect on a count of
#: violations is that large, so a coefficient there is the optimiser walking
#: toward an infinity the data admit.
SEPARATION_COEFFICIENT_LIMIT = 10.0

# The coding argument is matched non-greedily because it carries its own
# parentheses — `Treatment('ape')` — and a character class excluding `)` stops at
# the wrong one.
_TERM_PATTERN = re.compile(r"C\(\s*([A-Za-z_]\w*)\s*(?:,.*?)?\)\[T\.")


def short_term(name: str) -> str:
    """Compact a patsy term name into something a table column can hold.

    ``C(arm, Treatment('ape'))[T.other]`` becomes ``arm[other]``, and
    ``C(timeout)[T.300]`` becomes ``timeout[300]``. The coding is dropped because
    it is constant across the table and recorded in the envelope's convention.

    Args:
        name: The term name as statsmodels reports it.

    Returns:
        The compacted name, unchanged when no pattern matches.
    """
    return _TERM_PATTERN.sub(r"\1[", name)


def treatment_term(arm_column: str, reference_level: str) -> str:
    """The patsy factor for an arm column coded against a chosen reference.

    Args:
        arm_column: Column holding the arm label.
        reference_level: The level every contrast is taken against.

    Returns:
        The patsy term, e.g. ``C(arm, Treatment('ape'))``.
    """
    return f"C({arm_column}, Treatment('{reference_level}'))"


def _resolve_formula(
    formula: str, arm_column: str, reference_level: Optional[str]
) -> str:
    """Substitute the arm placeholder, refusing the two inconsistent combinations.

    Args:
        formula: The caller's formula, with or without ``ARM_PLACEHOLDER``.
        arm_column: Column holding the arm label.
        reference_level: The declared reference, or ``None`` for a formula with
            no arm factor.

    Returns:
        The formula patsy will parse.

    Raises:
        ValueError: The placeholder is present with no reference level, or a
            reference level was declared for a formula that has no arm factor —
            in which case the declared level would silently do nothing.
    """
    has_placeholder = ARM_PLACEHOLDER in formula
    if has_placeholder and reference_level is None:
        raise ValueError(
            f"the formula carries {ARM_PLACEHOLDER} but reference_level is None"
        )
    if not has_placeholder and reference_level is not None:
        raise ValueError(
            f"reference_level={reference_level!r} was declared but the formula "
            f"has no {ARM_PLACEHOLDER} to code against it"
        )
    if not has_placeholder:
        return formula
    return formula.replace(
        ARM_PLACEHOLDER, treatment_term(arm_column, str(reference_level))
    )


def _fit_nb(formula: str, data: pd.DataFrame, offset, cluster: str):
    """NB2 with the dispersion by maximum likelihood and cluster-robust errors.

    The Poisson fit is returned alongside because it is needed twice: as the
    warm start, and as the null of the likelihood-ratio test for overdispersion.
    Fitting it once serves both.

    Args:
        formula: A resolved patsy formula.
        data: The frame the formula is evaluated against.
        offset: The offset array, or ``None``.
        cluster: Column whose values group the robust standard errors.

    Returns:
        ``(nb_result, poisson_result)``.
    """
    import statsmodels.api as sm

    log = np.log  # noqa: F841 — patsy resolves log() from this frame

    with warnings.catch_warnings():
        # A separated or near-separated fit warns about the Hessian and the
        # iteration limit. Those states are detected and reported in the
        # envelope; as warnings they would be noise on a table of fits.
        warnings.simplefilter("ignore")
        poisson = sm.Poisson.from_formula(formula, data=data, offset=offset).fit(disp=0)
        if int(poisson.nobs) != len(data):
            # Checked here rather than after the negative-binomial fit, which
            # would fail first and blame the cluster vector's length for a
            # missing value in the frame.
            raise ValueError(
                f"the formula dropped {len(data) - int(poisson.nobs)} rows; clean "
                "the frame first, because the cluster vector is taken from it "
                "positionally"
            )
        start = np.append(np.asarray(poisson.params), 0.5)
        model = sm.NegativeBinomial.from_formula(formula, data=data, offset=offset)
        result = model.fit(
            start_params=start,
            method="bfgs",
            maxiter=500,
            disp=0,
            cov_type="cluster",
            cov_kwds={"groups": data[cluster]},
        )
    return result, poisson


def fit(
    formula: str,
    data: pd.DataFrame,
    *,
    offset: Any = _UNSET,
    reference_level: Any = _UNSET,
    cluster: str = "apk",
    arm_column: str = "arm",
    separation_coefficient_limit: float = SEPARATION_COEFFICIENT_LIMIT,
    provenance_ref: str = "",
) -> Envelope:
    """Fit the count model and return its whole table as one envelope.

    Args:
        formula: A patsy formula whose arm factor, if any, is written as
            ``{arm}``.
        data: One row per observation. Every column the formula and the cluster
            need must be present and complete: the cluster vector is taken from
            this frame positionally, so a row patsy drops would misalign it, and
            that is refused rather than tolerated.
        offset: The offset, on the log scale, or ``None`` for no offset. A freeze
            item: required, and ``None`` must be said out loud.
        reference_level: The arm level every contrast is taken against, or
            ``None`` for a formula with no arm factor. A freeze item: the
            reference decides what every rate ratio in the table means.
        cluster: Column grouping the robust standard errors. Applications, in
            every current campaign.
        arm_column: Column holding the arm label, substituted into the
            placeholder.
        separation_coefficient_limit: |coefficient| above which a term is
            reported as suspected separation.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying, per term, ``coef__``, ``se__``, ``p__``, ``irr__``,
        ``irr_lo__`` and ``irr_hi__``; plus the dispersion and its interval, the
        boundary-corrected likelihood-ratio test against Poisson, observed and
        NB-expected zeros, convergence, the fit statistics, the number of arm
        contrasts and the separation flags. ``ci`` is ``None`` because a
        regression has one interval per term and they travel in ``estimate``.

    Raises:
        FreezeItemUnset: ``offset`` or ``reference_level`` was omitted.
        ValueError: The frame is empty, the cluster column is absent, the formula
            and the reference level disagree, or the formula dropped rows.
    """
    if offset is _UNSET:
        raise FreezeItemUnset(
            "offset: a size term constrained to an elasticity of one is a "
            "modelling decision; pass None to say there is no offset"
        )
    if reference_level is _UNSET:
        raise FreezeItemUnset(
            "reference_level: every rate ratio in the table is read against it, "
            "so the code must not pick one"
        )
    if len(data) == 0:
        raise ValueError("no observations to fit")
    if cluster not in data.columns:
        raise ValueError(f"cluster column {cluster!r} is not in the frame")

    resolved = _resolve_formula(formula, arm_column, reference_level)
    offset_array = None if offset is None else np.asarray(offset, dtype=float)
    if offset_array is not None and offset_array.shape[0] != len(data):
        raise ValueError(
            f"offset has {offset_array.shape[0]} values against {len(data)} rows"
        )

    from scipy import stats as scistats

    result, poisson = _fit_nb(resolved, data, offset_array, cluster)

    n_obs = int(result.nobs)
    intervals = result.conf_int()
    estimate: dict[str, Union[float, int, str, bool]] = {}
    separated: list[str] = []
    for name in result.params.index:
        coefficient = float(result.params[name])
        standard_error = float(result.bse[name])
        low, high = (float(value) for value in intervals.loc[name])
        label = short_term(str(name))
        estimate[f"coef__{label}"] = coefficient
        estimate[f"se__{label}"] = standard_error
        estimate[f"p__{label}"] = float(result.pvalues[name])
        if name != DISPERSION:
            estimate[f"irr__{label}"] = float(np.exp(coefficient))
            estimate[f"irr_lo__{label}"] = float(np.exp(low))
            estimate[f"irr_hi__{label}"] = float(np.exp(high))
            if abs(coefficient) > separation_coefficient_limit or not np.isfinite(
                standard_error
            ):
                separated.append(label)

    dispersion = float(result.params[DISPERSION])
    dispersion_ci = intervals.loc[DISPERSION]
    likelihood_ratio = 2.0 * (float(result.llf) - float(poisson.llf))
    # Half the chi-square tail: the null puts the dispersion on the boundary of
    # the parameter space, where the naive test is conservative by a factor of 2.
    likelihood_ratio_p = 0.5 * float(scistats.chi2.sf(max(likelihood_ratio, 0.0), 1))

    endog = np.asarray(result.model.endog, dtype=float)
    mu = np.asarray(result.predict(), dtype=float)
    expected_zeros = float(
        np.sum((1.0 / (1.0 + dispersion * mu)) ** (1.0 / dispersion))
    )

    converged = bool(result.mle_retvals.get("converged", False))
    if not converged:
        separated.append("model did not converge")

    arm_terms = (
        [
            str(name)
            for name in result.params.index
            if str(name).startswith(f"C({arm_column},")
        ]
        if reference_level is not None
        else []
    )

    estimate.update(
        {
            DISPERSION: dispersion,
            "alpha_ci_lo": float(dispersion_ci.iloc[0]),
            "alpha_ci_hi": float(dispersion_ci.iloc[1]),
            "lr_nb_vs_poisson": float(likelihood_ratio),
            "lr_p_boundary_corrected": likelihood_ratio_p,
            "zeros_observed": int(np.sum(endog == 0)),
            "zeros_expected_nb": expected_zeros,
            "converged": converged,
            "llf": float(result.llf),
            "aic": float(result.aic),
            "bic": float(result.bic),
            "n_clusters": int(data[cluster].nunique()),
            "n_arm_contrasts": len(arm_terms),
            "reference_level": "" if reference_level is None else str(reference_level),
            "offset_supplied": bool(offset_array is not None),
            "separation_suspected": bool(separated),
            "separation_terms": ", ".join(separated),
        }
    )

    return Envelope(
        estimand="negative_binomial_irr",
        n=n_obs,
        denominator=Denominator(reachable=int(len(data)), analysed=n_obs),
        estimate=estimate,
        ci=None,
        convention={
            "formula": resolved,
            "estimator": "negative binomial (NB2), dispersion by maximum likelihood",
            "start": "Poisson fit carrying the same offset; the default start "
            "ignores the offset and the pure-offset model then diverges",
            "standard_errors": f"cluster-robust, grouped by {cluster}",
            "irr": "exp(coefficient), with the interval exponentiated from the "
            "Wald interval on the log scale",
            "reference_level": (
                "none" if reference_level is None else str(reference_level)
            ),
            "offset": "none" if offset_array is None else "supplied on the log scale",
            "lr_test": "boundary-corrected: 0.5 * chi2(1) tail, because the null "
            "puts the dispersion on the edge of the parameter space",
            "intervals": "one per term, in the estimate; the envelope's ci is None "
            "because a regression has no single interval",
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )


def compare_specifications(
    main: Envelope,
    sensitivities: Mapping[str, Envelope],
    *,
    alpha: float,
    terms: Optional[Sequence[str]] = None,
    provenance_ref: str = "",
) -> Envelope:
    """Report whether a sensitivity fit changes any conclusion of the main fit.

    A sensitivity analysis is only informative if someone states, in advance,
    what would count as it having mattered. Two things do: a term the main fit
    called significant changing the side of 1 its rate ratio sits on, and such a
    term losing significance. A third is worth listing separately — a term
    becoming significant only in a sensitivity — because it is a finding of the
    sensitivity, not a confirmation of the main fit.

    The comparison runs over envelopes rather than fitted objects, so it costs no
    refit and no estimation dependency.

    Args:
        main: The envelope of the main specification.
        sensitivities: Named envelopes of the alternative specifications.
        alpha: The level at which a term counts as significant.
        terms: The terms to compare. Defaults to every term the main fit carries
            a rate ratio for, less the intercept — which is not a conclusion, and
            which a specification carrying an offset does not even estimate on
            the same scale, so comparing it across specifications reports a flip
            that means nothing.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``n_conclusions``, ``direction_changed``,
        ``direction_flips``, ``significance_lost`` and ``gained_significance``.
    """

    def coefficient(envelope: Envelope, term: str) -> Optional[float]:
        value = envelope.estimate.get(f"coef__{term}")
        return None if value is None else float(value)

    def p_value(envelope: Envelope, term: str) -> Optional[float]:
        value = envelope.estimate.get(f"p__{term}")
        return None if value is None else float(value)

    candidates = (
        list(terms)
        if terms is not None
        else [
            key[len("irr__") :]
            for key in main.estimate
            if key.startswith("irr__") and key != "irr__Intercept"
        ]
    )
    conclusions = [
        term
        for term in candidates
        if (p_value(main, term) is not None and p_value(main, term) < alpha)
    ]

    flips: list[str] = []
    lost: list[str] = []
    gained: list[str] = []
    for name, envelope in sensitivities.items():
        for term in candidates:
            other_coefficient = coefficient(envelope, term)
            other_p = p_value(envelope, term)
            if other_coefficient is None or other_p is None:
                continue
            if term in conclusions:
                base = coefficient(main, term)
                if base is not None and (other_coefficient > 0) != (base > 0):
                    flips.append(f"{term} in {name}")
                if other_p >= alpha:
                    lost.append(f"{term} in {name}")
            elif other_p < alpha:
                gained.append(f"{term} in {name}")

    return Envelope(
        estimand="specification_sensitivity",
        n=main.n,
        denominator=main.denominator,
        estimate={
            "n_terms": len(candidates),
            "n_conclusions": len(conclusions),
            "conclusions": ", ".join(conclusions),
            "direction_changed": bool(flips),
            "direction_flips": ", ".join(flips),
            "significance_lost": ", ".join(lost),
            "gained_significance": ", ".join(gained),
            "alpha": float(alpha),
            "n_specifications": len(sensitivities),
        },
        ci=None,
        convention={
            "conclusions": f"terms with p < {alpha} in the main specification; "
            "a non-significant term drifting around a rate ratio of 1 across "
            "specifications is not a conclusion and is not tracked as one",
            "direction": "the side of 1 the rate ratio sits on",
            "gained_significance": "a finding of the sensitivity, listed apart "
            "from the main fit's conclusions",
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )


__all__ = [
    "ARM_PLACEHOLDER",
    "DISPERSION",
    "SEPARATION_COEFFICIENT_LIMIT",
    "compare_specifications",
    "fit",
    "short_term",
    "treatment_term",
]
