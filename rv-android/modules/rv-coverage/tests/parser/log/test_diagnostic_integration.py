"""Integration tests for diagnostic-event parsing inside parse_logcat_file (gh72).

- G1 / INV-ANA-46: re-parsing an RVSEC/RVSEC-COV logcat yields the same
  parse_logcat_line tuples as baseline and produces zero diagnostic events.
- A mixed logcat (RVSEC + crash) registers both an RV error and a diagnostic
  event, with coverage/error metrics unaffected by the diagnostics.
"""

import glob
from pathlib import Path

import pytest
from rv_coverage.parser.log.logcat_parser import parse_logcat_file, parse_logcat_line

FIXTURES = Path(__file__).parent / "fixtures"
# Repo-root data/results/cmp_* logcats from the APE×APE-RV run (may be absent in CI).
_CMP_GLOB = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "results"
    / "cmp_*"
    / "**"
    / "*.logcat"
)


class TestRvsecCovGolden:
    """INV-ANA-46: the RVSEC/COV hot path is unchanged by the diagnostic feature."""

    def test_parse_logcat_line_unchanged_and_zero_diagnostics(self):
        lines = (
            (FIXTURES / "rvsec_cov_golden.logcat").read_text().splitlines(keepends=True)
        )
        # Baseline: per-line parse output (the function we must not perturb).
        baseline = [parse_logcat_line(line) for line in lines]

        errors = [e for e, _ in baseline if e]
        coverages = [c for _, c in baseline if c]
        # The fixture has 2 RVSEC violations (jca + generic) and 4 RVSEC-COV calls.
        assert len(errors) == 2
        assert len(coverages) == 4

        repo = parse_logcat_file(str(FIXTURES / "rvsec_cov_golden.logcat"))
        # No static data → method calls are not registered, but errors are; the key
        # invariant is that NO diagnostic event is fabricated from RVSEC/COV lines.
        assert repo.get_diagnostic_events() == []
        assert len(repo.errors) == 2

    @pytest.mark.skipif(
        not glob.glob(str(_CMP_GLOB), recursive=True),
        reason="cmp_* result logcats not present in this environment",
    )
    def test_real_cmp_logcat_has_zero_diagnostics(self):
        """When the real APE×APE-RV logcats are present, re-parsing one produces
        zero diagnostic events and the same RVSEC/COV line counts as a direct sweep."""
        real = sorted(glob.glob(str(_CMP_GLOB), recursive=True))[0]
        with open(real, "r") as f:
            lines = f.readlines()
        baseline = [parse_logcat_line(line) for line in lines]
        baseline_cov = sum(1 for _, c in baseline if c)
        baseline_err = sum(1 for e, _ in baseline if e)

        repo = parse_logcat_file(real)
        assert repo.get_diagnostic_events() == []
        # Errors do not require static data, so their count must match the sweep.
        assert len(repo.errors) == baseline_err
        # Sanity: the sweep saw coverage lines (file is RVSEC-COV heavy).
        assert baseline_cov > 0


class TestMixedRvsecAndCrash:
    def test_rvsec_and_crash_both_registered_metrics_unaffected(self):
        repo = parse_logcat_file(str(FIXTURES / "mixed_rvsec_crash.logcat"))

        # The RVSEC violation is registered as an error.
        assert len(repo.errors) == 1
        # The crash is registered as an isolated diagnostic event.
        events = repo.get_diagnostic_events()
        assert len(events) == 1
        assert events[0]["category"] == "crash"
        assert events[0]["process"] == "br.unb.cic.cryptoapp"

        # Diagnostics do not enter error metrics.
        metrics = repo.calculate_metrics()
        assert metrics.total_errors == 1
        assert metrics.unique_errors == 1
