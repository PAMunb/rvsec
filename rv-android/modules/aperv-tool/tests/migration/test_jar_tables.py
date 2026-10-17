"""The parser is checked against the ape source it reads, not against a fixture copy.

A fixture would pin the parser to a snapshot of the Java and pass forever after the real
file moved — which is precisely the failure mode the migration check exists to catch. These
tests assert the shapes read off the jar's tables (six cells composed from four group blocks,
124 accepted keys, `ape.mopWeightActivity` retired), so a drift on the ape side surfaces here
rather than as a silent empty diff downstream.

The counts are pinned, so moving one is a decision. `ape.stepTelemetryEnabled` is absent from
the vocabulary because the jar deleted `Feature.STEP_TELEMETRY` outright: the event sink is an
instrument every cell carries alike, not an optional mechanism a cell can switch off. Its two
sub-parameters, `ape.llmPromptDump` and `ape.telemetryHeartbeat`, are accepted as BASE keys —
levers over what the trace carries, never over what the run decides.

The vocabulary is 124 keys. Group isolation added ten (the four group keys `ape.addons`,
`ape.static`, `ape.mop` and `ape.llm`, the data root `ape.staticDataPath`, the resolver key
`ape.variant`, `ape.mopCoinPercentage`, and the three LLM gate and breaker keys) and retired
three (`ape.mopDataPath`, renamed to `ape.staticDataPath`; `ape.leastVisitedPriorityTiebreak`;
`ape.mopTargetPickCap`).

`Presets.java` declares exactly the six cells, so a preset added or left behind on the ape
side fails `test_preset_names_are_exactly_the_six_cells`.
"""

import pytest

from .jar_tables import (
    JarTableError,
    KeySpec,
    load_key_specs,
    load_presets,
    load_retired_keys,
    source_provenance,
)

CELLS = ("base", "mop", "as", "as_mop", "as_llm", "as_mop_llm")

# The group blocks of the key contract (ape design § Key contract v3.2), as key sets. The
# vectors are read from the jar; these sets are what the tests compare them against.
ADDONS_BLOCK = {
    "ape.addons",
    "ape.backMenuPickCap",
    "ape.foreignActivityGuard",
    "ape.treePackageGuard",
    "ape.dynamicEpsilon",
    "ape.heuristicInput",
    "ape.formCompletionEnabled",
    "ape.modelMenuEnabled",
    "ape.treeEnhancementsEnabled",
    "ape.activityBudgetEnabled",
    "ape.activityStableRestartThreshold",
    "ape.coverageBoostWeight",
}
STATIC_BLOCK = {
    "ape.static",
    "ape.frontierBoostWeight",
    "ape.fuzzInputTyped",
    "ape.componentPercentage",
}
MOP_BLOCK = {
    "ape.mop",
    "ape.mopScoring",
    "ape.mopWeightWtg",
    "ape.mopFrontierWeight",
    "ape.activityTriggerEnabled",
    "ape.mopActivitySourceComponents",
    "ape.mopCoinPercentage",
}
LLM_BLOCK = {
    "ape.llm",
    "ape.llmOnNewState",
    "ape.llmOnStagnation",
    "ape.llmPercentage",
    "ape.llmPromptVariant",
    "ape.llmTemperature",
    "ape.llmTopP",
    "ape.llmTopK",
    "ape.llmSnapTolerancePx",
    "ape.llmModel",
    "ape.llmTimeoutMs",
}

EXPECTED_CELL_KEYS = {
    "base": set(),
    "mop": MOP_BLOCK,
    "as": ADDONS_BLOCK | STATIC_BLOCK,
    "as_mop": ADDONS_BLOCK | STATIC_BLOCK | MOP_BLOCK,
    "as_llm": ADDONS_BLOCK | STATIC_BLOCK | LLM_BLOCK,
    "as_mop_llm": ADDONS_BLOCK | STATIC_BLOCK | MOP_BLOCK | LLM_BLOCK,
}


class TestPresets:
    def test_preset_names_are_exactly_the_six_cells(self, ape_repo):
        assert set(load_presets(ape_repo)) == set(CELLS)

    def test_every_cell_is_a_preset(self, ape_repo):
        assert set(CELLS) <= set(load_presets(ape_repo))

    def test_each_cell_is_the_union_of_its_group_blocks(self, ape_repo):
        presets = load_presets(ape_repo)
        assert {cell: set(presets[cell]) for cell in CELLS} == EXPECTED_CELL_KEYS

    def test_the_cell_sizes(self, ape_repo):
        # 12 ADDONS + 4 STATIC + 7 MOP + 11 LLM keys; base states none.
        presets = load_presets(ape_repo)
        assert {cell: len(presets[cell]) for cell in CELLS} == {
            "base": 0,
            "mop": 7,
            "as": 16,
            "as_mop": 23,
            "as_llm": 27,
            "as_mop_llm": 34,
        }

    def test_a_block_has_the_same_values_in_every_cell_that_mounts_it(self, ape_repo):
        # A cell is a union, never a re-statement: the MOP block of `mop` and of `as_mop_llm`
        # is the same map.
        presets = load_presets(ape_repo)
        for block, cells in (
            (MOP_BLOCK, ("mop", "as_mop", "as_mop_llm")),
            (LLM_BLOCK, ("as_llm", "as_mop_llm")),
            (ADDONS_BLOCK | STATIC_BLOCK, ("as", "as_mop", "as_llm", "as_mop_llm")),
        ):
            values = {cell: {k: presets[cell][k] for k in block} for cell in cells}
            assert len({tuple(sorted(v.items())) for v in values.values()}) == 1, values

    def test_the_doses_the_blocks_set(self, ape_repo):
        presets = load_presets(ape_repo)
        assert presets["as_mop_llm"]["ape.componentPercentage"] == "0.03"
        assert presets["as_mop_llm"]["ape.mopCoinPercentage"] == "1.0"
        assert presets["as_mop_llm"]["ape.llmPercentage"] == "0.9"

    def test_deployment_specific_keys_stay_out_of_every_cell(self, ape_repo):
        # A preset names a cell, not a machine: the server URL, the artifact path and the
        # harness label come from the tool (`ape.llmUrl` via `overrides`, the other two as
        # fixed lines), which is what makes a data cell without the artifact abort.
        presets = load_presets(ape_repo)
        for cell in CELLS:
            for key in ("ape.llmUrl", "ape.staticDataPath", "ape.variant"):
                assert key not in presets[cell], (cell, key)


class TestKeySpecs:
    def test_accepted_vocabulary_size(self, ape_repo):
        assert len(load_key_specs(ape_repo)) == 124

    def test_the_group_data_and_resolver_keys_are_accepted(self, ape_repo):
        specs = load_key_specs(ape_repo)
        for key in ("ape.addons", "ape.static", "ape.mop", "ape.llm"):
            assert specs[key] == KeySpec("BOOLEAN", "false"), key
        assert specs["ape.staticDataPath"].default is None
        assert "ape.variant" in specs
        assert specs["ape.mopCoinPercentage"] == KeySpec("DOUBLE", "1.0")
        assert specs["ape.llmBreakerOpenMs"] == KeySpec("LONG", "60000")

    def test_a_key_declared_through_a_constant_is_read(self, ape_repo):
        # `ape.mopScoring` is declared as `MopScoring.KEY`, not as a literal; missing it
        # would make the sweep call a key the jar accepts an unknown one.
        spec = load_key_specs(ape_repo)["ape.mopScoring"]
        assert spec.value_type == "MOP_SCORING"
        assert spec.default == "flag"

    def test_telemetry_is_not_a_setting_an_arm_can_express(self, ape_repo):
        # The counterpart of the key's removal from APERV_PROPERTY_MAPPING. Telemetry
        # neutrality is the property that every arm's trace is produced by the same
        # instrument; it holds because there is no key to state, not because no arm states
        # one. The two levers over trace *content* survive, and are what makes the pair
        # reachable at all — a key owned by a deleted feature would be unreachable rather
        # than removed.
        specs = load_key_specs(ape_repo)
        assert "ape.stepTelemetryEnabled" not in specs
        assert "ape.llmPromptDump" in specs
        assert "ape.telemetryHeartbeat" in specs

    def test_types_and_defaults_are_read_not_guessed(self, ape_repo):
        specs = load_key_specs(ape_repo)
        # The pair that forces typed comparison: the preset writes -1, the default is -1.0.
        assert specs["ape.llmPercentageNoSubstrate"].value_type == "DOUBLE"
        assert specs["ape.llmPercentageNoSubstrate"].default == "-1.0"
        assert specs["ape.defaultGUIThrottle"].value_type == "LONG"
        # A key declared with a null default is a key with no default, not the string "null".
        assert specs["ape.llmUrl"].default is None

    def test_resolver_owned_keys_are_accepted_too(self, ape_repo):
        # ape.preset must be in the accepted set, or the sweep would call the very key this
        # change starts writing an unknown one.
        specs = load_key_specs(ape_repo)
        assert "ape.preset" in specs
        assert "ape.runId" in specs

    def test_every_preset_key_is_an_accepted_key(self, ape_repo):
        specs = load_key_specs(ape_repo)
        for name, vector in load_presets(ape_repo).items():
            unknown = set(vector) - set(specs)
            assert not unknown, f"preset {name} carries keys the jar rejects: {unknown}"


class TestRetiredKeys:
    def test_mop_weight_activity_is_retired_with_its_reason(self, ape_repo):
        retired = load_retired_keys(ape_repo)
        assert "ape.mopWeightActivity" in retired
        assert "mop-fairtest" in retired["ape.mopWeightActivity"]

    def test_the_group_isolation_retirements(self, ape_repo):
        retired = load_retired_keys(ape_repo)
        for key in (
            "ape.mopDataPath",
            "ape.leastVisitedPriorityTiebreak",
            "ape.mopTargetPickCap",
        ):
            assert key in retired, key
            assert retired[key], key

    def test_ape_pure_mode_is_retired(self, ape_repo):
        # gh93 already removed it from this repository's mapping; the jar's side of that
        # decision is what makes the removal permanent rather than a local tidy-up.
        assert "ape.apePureMode" in load_retired_keys(ape_repo)

    def test_retired_and_accepted_do_not_overlap(self, ape_repo):
        specs = load_key_specs(ape_repo)
        overlap = set(load_retired_keys(ape_repo)) & set(specs)
        assert not overlap, f"keys both accepted and retired: {overlap}"


class TestProvenance:
    def test_records_what_was_read(self, ape_repo):
        provenance = source_provenance(ape_repo)
        assert provenance["ape_repo"] == str(ape_repo)
        # 64 hex chars each — the digests are what actually pin the content, since a
        # checkout with no git metadata still yields them.
        assert len(provenance["Presets.java"]) == 64
        assert len(provenance["KeyOwnership.java"]) == 64


class TestHardErrors:
    def test_a_checkout_without_the_tables_raises(self, tmp_path):
        # Never a degraded mode: an empty preset would make the regeneration diff compare
        # nothing against nothing and pass.
        with pytest.raises(JarTableError):
            load_presets(tmp_path)

    def test_provenance_of_an_unreadable_checkout_raises_the_same_error(self, tmp_path):
        # The provenance record is on the same contract as the loaders: one error type for
        # "the ape source is not where you said", whichever function noticed.
        with pytest.raises(JarTableError):
            source_provenance(tmp_path)
