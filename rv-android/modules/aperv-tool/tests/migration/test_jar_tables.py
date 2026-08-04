"""The parser is checked against the ape source it reads, not against a fixture copy.

A fixture would pin the parser to a snapshot of the Java and pass forever after the real
file moved — which is precisely the failure mode the migration check exists to catch. These
tests assert the shapes the design derived from the stage-2 tables (four presets sized
18/22/25/29, 111 accepted keys, `ape.mopWeightActivity` retired), so a drift on the ape side
surfaces here rather than as a silent empty diff downstream.
"""

import pytest

from .jar_tables import (
    JarTableError,
    load_key_specs,
    load_presets,
    load_retired_keys,
    source_provenance,
)

# The vector sizes the design read off Presets.java: aperv is the 17 arm-defining flags plus
# the campaign throttle; mop adds the four scoring weights; llm adds the seven-key sampling
# block; llm_mop carries both.
EXPECTED_PRESET_SIZES = {"aperv": 18, "mop": 22, "llm": 25, "llm_mop": 29}


class TestPresets:
    def test_four_presets_at_the_expected_sizes(self, ape_repo):
        presets = load_presets(ape_repo)
        assert {name: len(v) for name, v in presets.items()} == EXPECTED_PRESET_SIZES

    def test_mop_extends_aperv_with_the_scoring_weights(self, ape_repo):
        presets = load_presets(ape_repo)
        added = set(presets["mop"]) - set(presets["aperv"])
        assert added == {
            "ape.mopWeightDirect",
            "ape.mopWeightTransitive",
            "ape.mopWeightOpenMenu",
            "ape.mopWeightWtg",
        }

    def test_llm_mop_is_mop_plus_the_llm_block(self, ape_repo):
        presets = load_presets(ape_repo)
        assert set(presets["llm_mop"]) == set(presets["mop"]) | (
            set(presets["llm"]) - set(presets["aperv"])
        )

    def test_deployment_specific_keys_stay_out_of_every_preset(self, ape_repo):
        # A preset names an arm, not a machine: the server URL and the artifact path must
        # come explicitly, which is what makes an LLM arm without llm_url abort (INV-APV-38).
        for name, vector in load_presets(ape_repo).items():
            assert "ape.llmUrl" not in vector, name
            assert "ape.mopDataPath" not in vector, name

    def test_the_throttle_every_arm_used_is_preset_resident(self, ape_repo):
        # This is what lets throttle_ms disappear from all eight surviving arms.
        assert load_presets(ape_repo)["aperv"]["ape.defaultGUIThrottle"] == "200"


class TestKeySpecs:
    def test_accepted_vocabulary_size(self, ape_repo):
        assert len(load_key_specs(ape_repo)) == 111

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
