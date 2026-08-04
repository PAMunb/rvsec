# ============================================================================
# VENDORED — provenance header (gh88 design decision 6, NFR08)
# ----------------------------------------------------------------------------
# Verbatim vendored copy of:
#     rvsec-calibracao/scripts/stats_utils.py
# Upstream git tree: workspace-rv/rvsec-calibracao (a SEPARATE repository that
# lives OUTSIDE rvsec/), HEAD 7bd0b3cbae5d1c91ce676db1a49ab8c077cc9986 at copy
# time; this file last modified upstream in commit
# c7777579b72e51a890bbe80af440549df6b5c55e (2026-07-20).
#
# Why vendored (copied, not imported): the calibration scaffold must be
# self-sufficient and reproducible. Importing the sibling repo at runtime would
# make every iteration depend on the unversioned state of an out-of-tree repo
# (a reproducibility hole, NFR08), and the cross-repo relative path is brittle.
# The function bodies below (holm_mde, diff_of_trimmed_means,
# paired_bootstrap_ci) are copied UNCHANGED. `multiarm_stats.py` imports this
# module LOCALLY (same scripts/ directory) — there is NO sys.path insertion, NO
# env var, and NO reference to the sibling-repo path at runtime.
#
# If an additional primitive is ever needed, pull it on demand (also verbatim,
# also provenance-headed) from rvsec-calibracao/scripts/power_analysis.py.
# ============================================================================
"""Estatística compartilhada da calibração v4 (power_analysis + analyze_calibration).

Estimando pinado (objective.spec.md): DIFERENÇA DE MÉDIAS APARADAS 10%,
recomputada por reamostra — nunca média aparada das diferenças, nunca média
simples. Bootstrap pareado POR APK; bootstrap por cluster de fold é PROIBIDO
(design D16.5)."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm, trim_mean


def diff_of_trimmed_means(a: np.ndarray, b: np.ndarray, trim: float = 0.10) -> float:
    return float(trim_mean(a, trim) - trim_mean(b, trim))

def paired_bootstrap_ci(a, b, B: int = 10_000, seed: int = 42, trim: float = 0.10,
                        alpha: float = 0.05):
    """IC percentil (1-alpha) do estimando por reamostragem de APKs com reposição.
    Pares quebrados devem ser removidos ANTES (listwise) pelo chamador."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape and a.ndim == 1
    n = len(a)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    stats = np.array([diff_of_trimmed_means(a[i], b[i], trim) for i in idx])
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return diff_of_trimmed_means(a, b, trim), float(lo), float(hi)

def holm_mde(sd: float, n: int, k: int = 3, alpha: float = 0.05,
             power: float = 0.80) -> float:
    """MDE analítico pareado no teste mais conservador de Holm (alpha/k),
    bilateral: (z_{1-a/2k} + z_{power}) * sd / sqrt(n)."""
    return float((norm.ppf(1 - alpha / (2 * k)) + norm.ppf(power)) * sd / np.sqrt(n))
