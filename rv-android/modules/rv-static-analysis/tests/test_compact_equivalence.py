"""
The compact document parses to the same model as the full one (INV-ANA-89, first
half).

``StaticAnalysisParser`` drops every distance member while it reads, so the
reduction of ``targetDistances``, the ``distancePairs`` marker and the absence of
whitespace must not reach ``StaticAnalysisData``. The check converts the
``cryptoapp.apk.json`` fixture, a full-mode document, and compares what a consumer
can read from the two models.
"""

from pathlib import Path

from rv_android_core.domain.static import StaticAnalysisData
from rv_static_analysis.compact import compact_document
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

FIXTURE = Path(__file__).parent / "resources" / "cryptoapp.apk.json"


def _model_snapshot(data: StaticAnalysisData) -> dict:
    """Every field of the model plus the graph edges, in a comparable form.

    Pydantic equality is not enough: `Method` and `Widget` override `__eq__` to
    compare one identifying field, so a difference in a reachability flag or a
    widget's text would compare equal.
    """
    snapshot = data.model_dump(mode="json")
    snapshot["wtg"]["window_ids"] = sorted(snapshot["wtg"]["window_ids"])
    snapshot["wtg_edges"] = sorted(
        (
            source,
            target,
            [
                (
                    event.widget_id,
                    event.event_type.name,
                    event.method,
                    event.target_window_class,
                    event.target_reaches_target,
                )
                for event in attributes["events"]
            ],
        )
        for source, target, attributes in data.wtg.graph.edges(data=True)
    )
    return snapshot


def test_fixture_is_a_full_mode_document():
    text = FIXTURE.read_text(encoding="utf-8")
    assert "distancePairs" not in text
    assert '\n  "distanceTargets": [' in text


def test_compact_fixture_parses_to_the_same_model(tmp_path):
    compact = tmp_path / FIXTURE.name
    compact_document(str(FIXTURE), str(compact))
    parser = StaticAnalysisParser()

    from_full = parser.parse_file(str(FIXTURE))
    from_compact = parser.parse_file(str(compact))

    assert len(from_full.classes.methods) > 0
    assert _model_snapshot(from_compact) == _model_snapshot(from_full)
