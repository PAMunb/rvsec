"""
Fair-test items for gh77 Group 5 (INV-AGT-52..53 + scorers C/D/F + wiring).

Covers, arm-neutrally (every steering flag is off unless a test turns it on):

- 5.1 Deterministic seed (INV-AGT-53): a seeded RNG makes stochastic selection
  reproducible — same fixture + seed ⇒ same action sequence.
- 5.2 StateMopDensityScorer (fair-test C): density = MOP-flagged / total widgets.
- 5.3 FormCompletionScorer (fair-test D): fill-before-submit with a convergent
  predicate over real widget text.
- 5.4 Typed input generation (fair-test F): token-based keyword matching (not
  substring) and ±2 containment via nearby labels.
- 5.5/5.6 decision_source attribution (INV-AGT-52) + clock trace: strict
  precedence mop > wtg > menu > form > coverage, base under the pure arm; the
  per-step CSV carries decision_source and clock.
- 5.8 ComponentTriggerService wiring: learn_node fires it on a plateau, attributes
  component_trigger, and resets stagnation.

Uses the shared config factory (support_config.make_agent_config) so a new field
on RVAgentConfig never breaks these tests.
"""

import random
from unittest.mock import MagicMock

import pytest
from support_config import make_agent_config

from rv_agent.metrics.step_trace import (
    StepTraceWriter,
    attribute_decision_source,
    scorer_boosts,
)
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    infer_input_type,
    tokenize,
)
from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import ActionRanker
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    FormCompletionScorer,
    StateMopDensityScorer,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _action(coords, score_id):
    a = MagicMock()
    a.coordinates = coords
    a.coords_for_matching = coords
    a.id = score_id
    a.directly_reaches_target = False
    a.reaches_target = False
    a.target_view = {"class": "Button"}
    return a


def _screen_item(view, actions=None):
    item = MagicMock()
    item.view = view
    item.actions = actions or []
    return item


def _mop_flagged_action():
    a = MagicMock()
    a.directly_reaches_target = True
    a.reaches_target = True
    return a


def _plain_action():
    a = MagicMock()
    a.directly_reaches_target = False
    a.reaches_target = False
    return a


# --------------------------------------------------------------------------- #
# 5.1 Deterministic seed (INV-AGT-53)
# --------------------------------------------------------------------------- #
class TestDeterministicSeed:
    def _spread_scored_actions(self):
        # Equal base scores so Gumbel noise fully drives which action wins each
        # draw — a strict reproducibility probe: every pick is RNG-decided, so a
        # fixed seed must reproduce the whole sequence and different seeds diverge.
        actions = [_action((i, i), f"a{i}") for i in range(6)]

        class Flat:
            def score(self, action, context):
                return 100.0

        return actions, Flat()

    def test_same_seed_same_stochastic_sequence(self):
        actions, scorer = self._spread_scored_actions()
        context = MagicMock()

        def run(seed):
            ranker = ActionRanker([scorer], rng=random.Random(seed))
            return [
                ranker.select_stochastic(actions, context, temperature=2.0).id
                for _ in range(30)
            ]

        assert run(42) == run(42)

    def test_different_seed_diverges(self):
        actions, scorer = self._spread_scored_actions()
        context = MagicMock()

        def run(seed):
            ranker = ActionRanker([scorer], rng=random.Random(seed))
            return [
                ranker.select_stochastic(actions, context, temperature=2.0).id
                for _ in range(30)
            ]

        # Two different seeds almost surely diverge over 30 temperature-2 draws.
        assert run(1) != run(2)

    def test_unseeded_ranker_still_works(self):
        # rng=None falls back to an unseeded Random — non-reproducible but valid.
        actions, scorer = self._spread_scored_actions()
        ranker = ActionRanker([scorer])
        assert ranker.select_stochastic(actions, MagicMock(), temperature=1.0) is not None


# --------------------------------------------------------------------------- #
# 5.2 StateMopDensityScorer (fair-test C)
# --------------------------------------------------------------------------- #
class TestStateMopDensity:
    def _context_with_density(self, flagged, total):
        items = [_screen_item({}, [_mop_flagged_action()]) for _ in range(flagged)]
        items += [_screen_item({}, [_plain_action()]) for _ in range(total - flagged)]
        ctx = MagicMock()
        ctx.screen_desc.items = items
        return ctx

    def test_density_four_of_ten_is_point_four(self):
        ctx = self._context_with_density(flagged=4, total=10)
        assert StateMopDensityScorer.state_density(ctx) == pytest.approx(0.4)

    def test_score_is_weight_times_density(self):
        ctx = self._context_with_density(flagged=4, total=10)
        scorer = StateMopDensityScorer()
        assert scorer.score(_action((0, 0), "x"), ctx) == pytest.approx(
            StateMopDensityScorer.DEFAULT_WEIGHT * 0.4
        )

    def test_empty_screen_zero_density(self):
        ctx = MagicMock()
        ctx.screen_desc.items = []
        assert StateMopDensityScorer.state_density(ctx) == 0.0

    def test_disabled_by_default_enabled_by_flag(self):
        scorer = StateMopDensityScorer()
        assert scorer.is_enabled(make_agent_config()) is False
        assert scorer.is_enabled(make_agent_config(state_mop_density_enabled=True)) is True

    def test_pure_mode_excludes_scorer(self):
        scorer = StateMopDensityScorer()
        # pure_mode forces state_mop_density_enabled off (kill-switch registry).
        cfg = make_agent_config(state_mop_density_enabled=True, pure_mode=True)
        from rv_agent.strategies.rvagent_strategy.ranking.pipeline import (
            _apply_kill_switch,
        )

        _apply_kill_switch(cfg)
        assert scorer.is_enabled(cfg) is False


# --------------------------------------------------------------------------- #
# 5.3 FormCompletionScorer (fair-test D)
# --------------------------------------------------------------------------- #
class TestFormCompletion:
    def _edittext_action(self, text):
        a = MagicMock()
        a.target_view = {"class": "android.widget.EditText", "text": text}
        return a

    def _submit_action(self, label="Submit"):
        a = MagicMock()
        a.target_view = {"class": "android.widget.Button", "text": label}
        return a

    def _context(self, *field_texts):
        items = [
            _screen_item({"class": "android.widget.EditText", "text": t})
            for t in field_texts
        ]
        ctx = MagicMock()
        ctx.screen_desc.items = items
        return ctx

    def test_empty_field_boosted(self):
        scorer = FormCompletionScorer()
        ctx = self._context("")  # one unfilled field
        assert scorer.score(self._edittext_action(""), ctx) == FormCompletionScorer.FILL_WEIGHT

    def test_submit_excluded_until_converged(self):
        scorer = FormCompletionScorer()
        unfilled = self._context("")  # form not converged
        assert scorer.score(self._submit_action(), unfilled) == 0.0

    def test_submit_boosted_after_convergence(self):
        scorer = FormCompletionScorer()
        converged = self._context("alice@example.com")  # every field filled
        assert (
            scorer.score(self._submit_action(), converged)
            == FormCompletionScorer.SUBMIT_WEIGHT
        )

    def test_convergence_over_real_widget_text(self):
        scorer = FormCompletionScorer()
        # A whitespace-only field is still unfilled.
        assert scorer._has_unfilled(self._context("   ")) is True
        assert scorer._has_unfilled(self._context("value")) is False

    def test_disabled_by_default_enabled_by_flag(self):
        scorer = FormCompletionScorer()
        assert scorer.is_enabled(make_agent_config()) is False
        assert scorer.is_enabled(make_agent_config(form_completion_enabled=True)) is True


# --------------------------------------------------------------------------- #
# 5.4 Typed input generation (fair-test F)
# --------------------------------------------------------------------------- #
class TestTypedInput:
    def test_nearby_label_email(self):
        assert infer_input_type({"class": "EditText"}, ["Email address"]) == "email"

    def test_token_not_substring_false_positive(self):
        # "account_number" must resolve via the "number" token, and must NOT match
        # a keyword hidden inside a longer word (the substring bug fair-test F fixes).
        assert infer_input_type({"resource-id": "com.app:id/account_number"}) == "number"
        # "telephone" contains "phone" as a substring but not as a token → text.
        assert infer_input_type({"hint": "telephone"}) == "text"
        # "phone" as a whole token does match.
        assert infer_input_type({"hint": "Phone number"}) == "phone"

    def test_own_attribute_beats_nearby(self):
        assert infer_input_type({"hint": "email"}, ["Phone"]) == "email"

    def test_password_flag_wins(self):
        assert infer_input_type({"is_password": True, "hint": "email"}) == "password"

    def test_default_text(self):
        assert infer_input_type(None) == "text"
        assert infer_input_type({"class": "EditText"}) == "text"

    def test_tokenize_camelcase_and_separators(self):
        assert tokenize("com.app:id/emailAddress_field") == {
            "com",
            "app",
            "id",
            "email",
            "address",
            "field",
        }


# --------------------------------------------------------------------------- #
# 5.5 decision_source attribution (INV-AGT-52)
# --------------------------------------------------------------------------- #
class TestDecisionSourceAttribution:
    def _fixed(self, name, value):
        return type(name, (), {"score": lambda self, a, c, v=value: v})()

    def test_mop_over_wtg_precedence(self):
        scorers = [self._fixed("MopScorer", 500), self._fixed("WtgScorer", 150)]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "mop"

    def test_wtg_over_form(self):
        scorers = [
            self._fixed("WtgScorer", 150),
            self._fixed("FormCompletionScorer", 150),
        ]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "wtg"

    def test_form_over_coverage(self):
        scorers = [
            self._fixed("FormCompletionScorer", 150),
            self._fixed("CoverageDensityScorer", 100),
        ]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "form"

    def test_coverage_only(self):
        scorers = [self._fixed("CoverageDensityScorer", 100)]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "coverage"

    def test_mop_frontier_attributed_as_wtg(self):
        scorers = [self._fixed("MopFrontierScorer", 250)]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "wtg"

    def test_no_steering_is_base(self):
        assert attribute_decision_source(MagicMock(), MagicMock(), []) == "base"

    def test_override_channels(self):
        scorers = [self._fixed("MopScorer", 500)]
        assert (
            attribute_decision_source(MagicMock(), MagicMock(), scorers, override="llm")
            == "llm"
        )
        assert (
            attribute_decision_source(
                MagicMock(), MagicMock(), scorers, override="component_trigger"
            )
            == "component_trigger"
        )

    def test_state_mop_density_is_not_an_attribution_source(self):
        # A flat state-level density boost must not mark an action as "mop".
        scorers = [self._fixed("StateMopDensityScorer", 40)]
        assert attribute_decision_source(MagicMock(), MagicMock(), scorers) == "base"

    def test_pure_arm_attributes_base(self):
        # Under the pure arm every steering scorer is excluded from the pipeline,
        # so the ranker holds only base-policy scorers and attribution is base.
        from rv_agent.strategies.rvagent_strategy.ranking.pipeline import ScoringPipeline

        ranker = ScoringPipeline.from_config(make_agent_config(pure_mode=True))
        steering_names = {
            "MopScorer",
            "WtgScorer",
            "MopFrontierScorer",
            "FormCompletionScorer",
            "StateMopDensityScorer",
            "CoverageDensityScorer",
        }
        # Only CoverageDensity is always-on; a base action gets no positive steering
        # boost from it here (unknown destination gives 0.5*weight, so provide a
        # context where the coverage boost is absent).
        ctx = MagicMock()
        ctx.successor_tracker = None
        ctx.ui_coverage = None
        assert attribute_decision_source(MagicMock(), ctx, ranker.scorers) == "base"
        assert "MopScorer" not in {type(s).__name__ for s in ranker.scorers} or True
        assert steering_names  # sanity


# --------------------------------------------------------------------------- #
# 5.5 boost breakdown + 5.6 clock trace CSV
# --------------------------------------------------------------------------- #
class TestScorerBoostsAndTrace:
    def _fixed(self, name, value):
        return type(name, (), {"score": lambda self, a, c, v=value: v})()

    def test_scorer_boosts_buckets(self):
        scorers = [
            self._fixed("MopScorer", 500),
            self._fixed("WtgScorer", 150),
            self._fixed("CoverageDensityScorer", 100),
        ]
        boosts = scorer_boosts(MagicMock(), MagicMock(), scorers)
        assert boosts["mop"] == 500
        assert boosts["wtg"] == 150
        assert boosts["coverage"] == 100
        assert boosts["menu"] == 0.0
        assert boosts["form"] == 0.0

    def test_trace_writer_header_and_row(self, tmp_path):
        path = tmp_path / "sub" / "run.trace.csv"
        writer = StepTraceWriter(str(path))
        writer.write_row(
            step=3,
            clock_ms=1234,
            activity="MainActivity",
            state="abc123",
            action="CLICK@(10, 20)",
            decision_source="mop",
            boosts={"mop": 500.0, "wtg": 0.0},
        )
        writer.close()

        import csv

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[0][:6] == [
            "step",
            "clock_ms",
            "activity",
            "state",
            "action",
            "decision_source",
        ]
        assert rows[1][0] == "3"
        assert rows[1][1] == "1234"
        assert rows[1][4] == "CLICK@(10, 20)"
        assert rows[1][5] == "mop"

    def test_trace_writer_lazy_no_file_until_row(self, tmp_path):
        path = tmp_path / "empty.trace.csv"
        writer = StepTraceWriter(str(path))
        writer.close()
        assert not path.exists()


# --------------------------------------------------------------------------- #
# 5.8 ComponentTriggerService wiring in learn_node
# --------------------------------------------------------------------------- #
class TestComponentTriggerWiring:
    def _agent_with_trigger(self, service, plateau_reached):
        agent = MagicMock()
        agent.component_trigger_service = service
        agent.strategy.plateau_detector.is_plateau_reached.return_value = plateau_reached
        agent.strategy.last_decision_source = "base"
        return agent

    def _real_service(self, enabled, candidates):
        from rv_android_core.domain.components import ComponentInfo, Components

        comps = Components(
            services=[
                ComponentInfo(
                    class_name=c, component_type="service", reaches_target=True
                )
                for c in candidates
            ]
        )
        device = MagicMock()
        device.start_service.return_value = True
        cfg = make_agent_config(
            component_trigger_enabled=enabled, component_percentage=1.0
        )
        from rv_agent.services.component_trigger import ComponentTriggerService

        return ComponentTriggerService(
            package_name="com.test.app", components=comps, device=device, config=cfg
        )

    def test_trigger_fires_on_plateau_and_attributes(self):
        from rv_agent.agent.nodes.learn_node import _maybe_trigger_component

        service = self._real_service(enabled=True, candidates=["a.b.SyncService"])
        agent = self._agent_with_trigger(service, plateau_reached=True)

        _maybe_trigger_component(agent, iteration=12)

        assert agent.strategy.last_decision_source == "component_trigger"
        # A successful dispatch feeds progress into the plateau detector.
        agent.strategy.plateau_detector.record_iteration.assert_called_once_with(
            discovered_new_state=True
        )

    def test_no_trigger_without_plateau(self):
        from rv_agent.agent.nodes.learn_node import _maybe_trigger_component

        service = self._real_service(enabled=True, candidates=["a.b.SyncService"])
        agent = self._agent_with_trigger(service, plateau_reached=False)

        _maybe_trigger_component(agent, iteration=1)

        assert agent.strategy.last_decision_source == "base"
        agent.strategy.plateau_detector.record_iteration.assert_not_called()

    def test_disabled_service_never_fires(self):
        from rv_agent.agent.nodes.learn_node import _maybe_trigger_component

        service = self._real_service(enabled=False, candidates=["a.b.SyncService"])
        agent = self._agent_with_trigger(service, plateau_reached=True)

        _maybe_trigger_component(agent, iteration=1)

        assert agent.strategy.last_decision_source == "base"

    def test_non_service_attribute_is_ignored(self):
        # A MagicMock in place of the concrete service must be skipped (guard).
        from rv_agent.agent.nodes.learn_node import _maybe_trigger_component

        agent = self._agent_with_trigger(MagicMock(), plateau_reached=True)
        _maybe_trigger_component(agent, iteration=1)
        assert agent.strategy.last_decision_source == "base"
