"""The corpus witness for the normalizer removal (task 4.6, INV-ANA-67).

`com.hwloc.lstopo_80283` is the one affected case that exists in dexlib2, in the
live corpus, with executions to check against: 99 archived logcats carrying 1080
`RVSEC-COV` events for `com.hwloc.lstopo.ZoomView.ZoomView`.

That name is the whole point. `ZoomView` is a class in package
`com.hwloc.lstopo.ZoomView` — two capitalized segments, no nesting — so the
parser's old heuristic rewrote it to `com.hwloc.lstopo.ZoomView$ZoomView`, a name
no weaver ever emitted. The crossing's lookup is literal equality against the
repository key, so all 1080 events fell through to a `logger.debug` with no
counter, and this application published 0.00% coverage over a denominator whose
classes were all present and all misspelled.

The fixtures are trimmed from the real artefacts, not synthesised: the logcat
holds exactly the 1080 dotted events, concatenated across the 99 archived runs,
and the artefact holds the two `ZoomView` classes verbatim. The 99 logcats
themselves live under `RV_ANDROID_NOVO_DATASET`, outside this repository, and
stay as the manual cross-check — a fixture is the only branch CI can verify.
"""

import os

from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

RESOURCES = os.path.join(os.path.dirname(__file__), "resources")
ARTEFACT = os.path.join(RESOURCES, "lstopo_zoomview.apk.json")
LOGCAT = os.path.join(RESOURCES, "lstopo_zoomview.logcat")

DOTTED = "com.hwloc.lstopo.ZoomView.ZoomView"
DOLLAR = "com.hwloc.lstopo.ZoomView$ZoomView"


def _read_logcat_lines():
    with open(LOGCAT, encoding="utf-8", errors="replace") as handle:
        return [line for line in handle if line.strip()]


class TestLstopoWitness:
    """The 1080 events reach the repository, and the dollar form does not occur."""

    def test_the_fixture_carries_the_measured_event_count(self):
        lines = _read_logcat_lines()

        assert len(lines) == 1080
        assert all(DOTTED in line for line in lines)
        assert not any(DOLLAR in line for line in lines)

    def test_the_artefact_spells_the_class_with_a_dot(self):
        """`ZoomView$ZoomViewListener` in the same file is genuine nesting, and
        it is why a rule keyed on capitalization cannot tell the two apart."""
        data = parse_file(ARTEFACT)

        assert DOTTED in data.classes.classes
        assert DOLLAR not in data.classes.classes
        assert f"{DOTTED}$ZoomViewListener" in data.classes.classes

    def test_every_event_crosses_into_the_repository(self):
        """The assertion the removal earns: 1080 matches, zero unmatched."""
        data = parse_file(ARTEFACT)

        repository = parse_logcat_file(LOGCAT, static_data=data)

        diagnostics = repository.parser_diagnostics.to_dict()
        assert diagnostics["unmatched_in_scope"] == 0
        assert diagnostics["unmatched_out_of_scope"] == 0

        clazz = repository.classes[DOTTED]
        called = {
            method.method_name for method in clazz.methods.values() if method.called
        }
        assert called == {
            "<init>",
            "bias",
            "clamp",
            "dispatchDraw",
            "dispatchTouchEvent",
            "lerp",
            "processDoubleTouchEvent",
            "processSingleTouchEvent",
            "processSingleTouchOutsideMinimap",
            "resetZoom",
            "smoothZoomTo",
        }

    def test_coverage_is_no_longer_zero(self):
        """The dose-response this case anchors: 100% of a class's names
        corrupted gave 0.00% coverage; corrected, the same inputs measure."""
        data = parse_file(ARTEFACT)

        repository = parse_logcat_file(LOGCAT, static_data=data)
        metrics = repository.calculate_metrics().to_dict()

        assert metrics["called_methods"] == 11
        assert metrics["method_coverage"] > 0

    def test_the_old_spelling_matched_nothing(self):
        """The failure this witness exists to pin, reproduced on demand.

        Rename the artefact's class to the form the normalizer produced and
        feed it the same 1080 events: every one falls through the crossing and
        `method_coverage` is 0.0. The discards land under `unmatched_unclassified`
        rather than `unmatched_in_scope` because this artefact — like all 162 of
        the article corpus — records no scope key, so the crossing has nothing to
        classify against. Before D1 they were not counted at all: they were
        `logger.debug` lines, which is why an application publishing 0.00% over a
        full denominator looked like an application nobody exercised.
        """
        import json
        import tempfile

        with open(ARTEFACT, encoding="utf-8") as handle:
            artefact = json.load(handle)
        for entry in artefact["reachability"]:
            entry["className"] = entry["className"].replace(DOTTED, DOLLAR)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            json.dump(artefact, handle)
            renamed = handle.name
        try:
            data = parse_file(renamed)
        finally:
            os.unlink(renamed)

        repository = parse_logcat_file(LOGCAT, static_data=data)

        diagnostics = repository.parser_diagnostics.to_dict()
        assert diagnostics["unmatched_unclassified"] == 1080
        assert repository.calculate_metrics().to_dict()["called_methods"] == 0
