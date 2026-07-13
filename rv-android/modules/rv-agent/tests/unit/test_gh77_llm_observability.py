"""
LLM-block observability for gh77 Group 8 (task 8.3), offline and arm-neutral.

Covers the two observability seams added for the LLM path, both fully offline
(no SGLang, no emulator):

- decision_source="llm" attribution: the LLM path selects actions in
  ``llm_node`` and bypasses the strategy's scored selection, so the trace row is
  written by ``RVAgentStrategy.record_llm_decision`` (the analog of what
  ``_select_priority_action`` does on the algorithm path). The whole-decision
  channel is ``"llm"`` with zero scorer boosts (INV-AGT-52).
- Screenshot-failure counter: ``RoutingManager.record_screenshot_failure``
  increments a routing-telemetry counter surfaced in ``get_decision_counters``;
  ``capture_screenshot_node`` calls it on both the optimization-failure and the
  exception branch.

The live SGLang revalidations (8.1/8.2 end-to-end proportions, tool-calling
against SGLang v0.5.6.post2) and the 8.5 E2E gate are NOT exercised here — they
require the LLM server and are deferred to a machine-free window.
"""

import csv
from unittest.mock import MagicMock

from support_config import make_agent_config

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.agent.nodes.capture_node import capture_screenshot_node
from rv_agent.agent.nodes.llm_node import _record_llm_trace
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.metrics.step_trace import StepTraceWriter, attribute_decision_source
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy


def _make_strategy(**overrides):
    """A minimal real RVAgentStrategy (real graph + coverage tracker)."""
    config = make_agent_config(**overrides)
    return RVAgentStrategy(
        graph=DynamicStateGraph(), ui_coverage=UICoverageTracker(), config=config
    )


def _routing_manager(**overrides):
    config = make_agent_config(**overrides)
    return RoutingManager(config=config, fallback_manager=MagicMock())


# --------------------------------------------------------------------------- #
# decision_source="llm" attribution (8.3)
# --------------------------------------------------------------------------- #
class TestLlmDecisionAttribution:
    def test_override_llm_pre_empts_boost_precedence(self):
        # The seam that record_llm_decision relies on: an explicit override wins
        # over any boost-family attribution.
        source = attribute_decision_source(
            action=MagicMock(), context=MagicMock(), scorers=[], override="llm"
        )
        assert source == "llm"

    def test_record_llm_decision_sets_source_and_zero_boosts(self):
        strategy = _make_strategy()
        strategy.last_decision_source = "coverage"  # stale value from an algo step
        strategy._last_boosts = {"coverage": 200.0}

        strategy.record_llm_decision(
            iteration=7, activity="MainActivity", state_hash="abc", action="CLICK@(1,2)"
        )

        assert strategy.last_decision_source == "llm"
        assert strategy._last_boosts == {}

    def test_record_llm_decision_writes_row(self, tmp_path):
        path = tmp_path / "run.trace.csv"
        strategy = _make_strategy()
        strategy.enable_step_trace(StepTraceWriter(str(path)))

        strategy.record_llm_decision(
            iteration=3,
            activity="LoginActivity",
            state_hash="deadbeef",
            action="SET_TEXT@(120, 240)",
        )
        strategy._step_trace.close()

        rows = list(csv.DictReader(path.open()))
        assert len(rows) == 1
        row = rows[0]
        assert row["decision_source"] == "llm"
        assert row["step"] == "3"
        assert row["activity"] == "LoginActivity"
        assert row["state"] == "deadbeef"
        assert row["action"] == "SET_TEXT@(120, 240)"
        # llm is a whole-decision channel: every boost column is zero.
        for col in ("mop", "wtg", "menu", "form", "coverage"):
            assert float(row[col]) == 0.0

    def test_record_llm_decision_no_writer_is_noop_but_sets_source(self):
        # Attribution is always computed; the row is only written when a writer
        # is attached (mirrors the algorithm path).
        strategy = _make_strategy()
        assert strategy._step_trace is None
        strategy.record_llm_decision(
            iteration=0, activity="A", state_hash="h", action="CLICK@(0, 0)"
        )
        assert strategy.last_decision_source == "llm"

    def test_llm_node_wiring_records_via_strategy(self, tmp_path):
        # _record_llm_trace pulls activity + hash from state and delegates to the
        # strategy, producing exactly the same row the direct call would.
        path = tmp_path / "wired.trace.csv"
        strategy = _make_strategy()
        strategy.enable_step_trace(StepTraceWriter(str(path)))

        agent = MagicMock()
        agent.strategy = strategy
        screen_desc = MagicMock()
        screen_desc.activity = "HomeActivity"
        state = {
            "iteration": 5,
            "screen_description": screen_desc,
            "current_screen_hash": "cafe",
        }
        llm_action = {"action_type": "CLICK", "x": 10, "y": 20}

        _record_llm_trace(agent, state, llm_action)
        strategy._step_trace.close()

        rows = list(csv.DictReader(path.open()))
        assert len(rows) == 1
        assert rows[0]["decision_source"] == "llm"
        assert rows[0]["activity"] == "HomeActivity"
        assert rows[0]["state"] == "cafe"
        assert rows[0]["action"] == "CLICK@(10, 20)"

    def test_llm_node_wiring_noop_for_strategy_without_method(self):
        # dfs/bfs/greedy strategies have no record_llm_decision; the wiring must
        # be a silent no-op (guard on the method's presence).
        agent = MagicMock()
        agent.strategy = object()  # no record_llm_decision attribute
        state = {"iteration": 0, "current_screen_hash": "h"}
        # Must not raise.
        _record_llm_trace(agent, state, {"action_type": "CLICK", "x": 0, "y": 0})


# --------------------------------------------------------------------------- #
# Screenshot-failure counter in routing telemetry (8.3)
# --------------------------------------------------------------------------- #
class TestScreenshotFailureCounter:
    def test_counter_starts_at_zero_and_is_exposed(self):
        rm = _routing_manager()
        assert rm.screenshot_failed == 0
        assert rm.get_decision_counters()["screenshot_failed"] == 0

    def test_record_increments_and_surfaces(self):
        rm = _routing_manager()
        rm.record_screenshot_failure()
        rm.record_screenshot_failure()
        assert rm.screenshot_failed == 2
        assert rm.get_decision_counters()["screenshot_failed"] == 2

    def test_capture_node_counts_optimization_failure(self):
        agent = MagicMock()
        agent.device.take_screenshot.return_value = "/tmp/shot.png"
        agent.image_handler.optimize.return_value = ""  # optimization failed
        agent.routing_manager = _routing_manager()

        result = capture_screenshot_node(agent, {})

        assert result["decision_path"] == "end"
        assert agent.routing_manager.screenshot_failed == 1

    def test_capture_node_counts_capture_exception(self):
        agent = MagicMock()
        agent.device.take_screenshot.side_effect = RuntimeError("adb died")
        agent.routing_manager = _routing_manager()

        result = capture_screenshot_node(agent, {})

        assert result["decision_path"] == "end"
        assert agent.routing_manager.screenshot_failed == 1

    def test_capture_node_no_count_on_success(self):
        agent = MagicMock()
        agent.device.take_screenshot.return_value = "/tmp/shot.png"
        agent.image_handler.optimize.return_value = "base64data"
        agent.routing_manager = _routing_manager()

        result = capture_screenshot_node(agent, {})

        assert result["screenshot_b64"] == "base64data"
        assert agent.routing_manager.screenshot_failed == 0
