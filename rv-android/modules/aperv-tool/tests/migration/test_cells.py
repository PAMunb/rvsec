"""The offline cell gate: each `get_variants()` cell against what the jar resolves for it.

The jar ships one `RUN_START` fixture per cell, `src/test/resources/cells/<cell>.run_start.json`,
captured from the properties file this module's `_push_properties` writes for the cell (the ape
side's `CellRunStartFixtureTest` builds that file by hand and pins the record). Reading those
fixtures here closes the loop from the Python side: a renamed cell, a moved block or a variant
whose static data or LLM URL drifted from what the fixture assumed fails before any device is
started. The device gate compares a recorded trace with the same files on `preset`, `variant`,
`features`, `params`, `inert` and `digest`, masking the members that differ per run.

The expected `features` are the ape design's § Key contract v3.2 list, written out per cell so
that a feature the jar adds or drops is a decision taken here, not a silent pass.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from aperv_tool.tools.aperv.tool import (
    APERV_PROPERTY_MAPPING,
    DEVICE_ARTIFACT_PATH,
    STATIC_DATA_FROM_STATIC_ANALYSIS,
    ApeRVTool,
)

from .jar_tables import load_key_specs, load_presets
from .test_jar_tables import ADDONS_BLOCK, CELLS, LLM_BLOCK, MOP_BLOCK, STATIC_BLOCK

CELLS_DIR = Path("src/test/resources/cells")
FEATURE_JAVA = Path(
    "src/main/java/com/android/commands/monkey/ape/runtime/Feature.java"
)

MASKED = "<masked>"
VOLATILE_MEMBERS = ("run_id", "t0", "seed", "props_digest", "build")

ADDON_MEMBERS = {
    "ACTIVITY_BUDGET",
    "COVERAGE_BOOST",
    "DYNAMIC_EPSILON",
    "FOREIGN_ACTIVITY_GUARD",
    "FORM_COMPLETION",
    "HEURISTIC_INPUT",
    "MODEL_MENU",
    "TREE_ENHANCEMENTS",
    "TREE_PACKAGE_GUARD",
}
MOP_FEATURES = {
    "STATIC_DATA",
    "MOP",
    "WTG",
    "MOP_FRONTIER",
    "MOP_LAUNCHER",
    "MOP_ACTIVITY_SOURCE",
    "MOP_COIN",
}
LLM_FEATURES = {"LLM", "LLM_NEW_STATE", "LLM_STAGNATION", "LLM_COIN"}
AS_FEATURES = (
    {"FUZZING", "ADDONS", "BACK_MENU_CAP", "ACTIVITY_STABLE_RESTART"}
    | ADDON_MEMBERS
    | {"STATIC_DATA", "STATIC", "NAV_FRONTIER", "TYPED_FUZZ", "COMPONENT_TRIGGER"}
)

EXPECTED_FEATURES = {
    "base": {"FUZZING"},
    "mop": {"FUZZING"} | MOP_FEATURES,
    "as": AS_FEATURES,
    "as_mop": AS_FEATURES | MOP_FEATURES | {"MENU_GATEWAY"},
    "as_llm": AS_FEATURES | LLM_FEATURES,
    "as_mop_llm": AS_FEATURES | MOP_FEATURES | {"MENU_GATEWAY"} | LLM_FEATURES,
}


def _fixture(ape_repo: Path, cell: str) -> Dict[str, Any]:
    path = ape_repo / CELLS_DIR / f"{cell}.run_start.json"
    if not path.is_file():
        pytest.fail(f"{path}: the cell's RUN_START fixture is missing")
    return json.loads(path.read_text(encoding="utf-8"))


class TestCellPresets:
    def test_preset_names_are_exactly_the_six_cells(self, ape_repo):
        assert set(load_presets(ape_repo)) == set(CELLS)

    def test_the_full_cell_is_the_union_of_the_four_blocks(self, ape_repo):
        presets = load_presets(ape_repo)
        assert set(presets["as_mop_llm"]) == (
            ADDONS_BLOCK | STATIC_BLOCK | MOP_BLOCK | LLM_BLOCK
        )


class TestCellFixtures:
    @pytest.mark.parametrize("cell", CELLS)
    def test_the_fixture_names_the_variants_cell(self, ape_repo, cell):
        variant = ApeRVTool.get_variants()[cell]
        record = _fixture(ape_repo, cell)
        assert record["type"] == "RUN_START"
        assert record["preset"] == variant["preset"]
        assert record["variant"] == variant["variant"]

    @pytest.mark.parametrize("cell", CELLS)
    def test_the_fixture_carries_the_contracts_features(self, ape_repo, cell):
        assert set(_fixture(ape_repo, cell)["features"]) == EXPECTED_FEATURES[cell]

    def test_the_launcher_and_the_component_trigger_sit_where_the_contract_puts_them(
        self, ape_repo
    ):
        mop = set(_fixture(ape_repo, "mop")["features"])
        assert "MOP_LAUNCHER" in mop
        assert "MENU_GATEWAY" not in mop
        for cell in ("as", "as_mop", "as_llm", "as_mop_llm"):
            assert "COMPONENT_TRIGGER" in _fixture(ape_repo, cell)["features"], cell

    @pytest.mark.parametrize("cell", CELLS)
    def test_the_fixtures_deployment_lines_are_the_ones_this_tool_writes(
        self, ape_repo, cell
    ):
        # The fixture was resolved from a hand-built copy of this tool's properties file, so
        # its artifact path and LLM URL are claims about this module. A cell that pushes the
        # artifact must carry DEVICE_ARTIFACT_PATH, and an LLM cell the URL its overrides
        # state; any other value would make every device run differ from its fixture.
        variant = ApeRVTool.get_variants()[cell]
        params = _fixture(ape_repo, cell)["params"]
        if variant.get("static_data") == STATIC_DATA_FROM_STATIC_ANALYSIS:
            assert params.get("ape.staticDataPath") == DEVICE_ARTIFACT_PATH
        else:
            assert "ape.staticDataPath" not in params
        llm_url = variant.get("overrides", {}).get("llm_url")
        assert params.get("ape.llmUrl") == llm_url

    @pytest.mark.parametrize("cell", CELLS)
    def test_the_fixture_is_a_version_2_record_with_its_volatile_members_masked(
        self, ape_repo, cell
    ):
        record = _fixture(ape_repo, cell)
        assert record["v"] == 2
        for member in VOLATILE_MEMBERS:
            assert record[member] == MASKED, member
        assert record["inert"] == []


class TestLedgerBudget:
    """The three MOP cells run the coin's ledger at 2, a key their fixtures leave at the default.

    No group block states `ape.mopCoinLedgerMaxInteractions`, so each MOP fixture carries the
    jar's default (1) by omission, and the device echo of the cell is its fixture plus exactly
    this one `params` entry, with the digest left out because it hashes every plan value
    (design D18).
    """

    @pytest.mark.parametrize("cell", ("mop", "as_mop", "as_mop_llm"))
    def test_the_ledger_override_is_a_key_the_jar_accepts_away_from_its_default(
        self, ape_repo, cell
    ):
        overrides = ApeRVTool.get_variants()[cell]["overrides"]
        key = APERV_PROPERTY_MAPPING["mop_coin_ledger_max_interactions"]
        spec = load_key_specs(ape_repo)[key]
        assert spec.value_type == "INT"
        assert spec.default == "1"
        assert overrides["mop_coin_ledger_max_interactions"] == 2
        assert key not in _fixture(ape_repo, cell)["params"]


class TestAblationVariant:
    """`mop_nolaunch` runs the `mop` preset under its own name, without a fixture.

    Its device echo is the `mop` fixture with `variant`, the ledger entry and the launcher's
    effect set apart and the digest left out, because the digest hashes every plan value.
    Offline, what can be checked is that it names a preset the jar ships and that the key it
    adds is one the jar accepts, with the type and the meaning the variant relies on.
    """

    def test_the_ablation_names_the_mop_preset(self, ape_repo):
        variant = ApeRVTool.get_variants()["mop_nolaunch"]
        assert variant["preset"] == "mop"
        assert variant["preset"] in load_presets(ape_repo)
        assert _fixture(ape_repo, "mop")["preset"] == variant["preset"]

    def test_mop_nolaunch_states_the_launcher_activation_key_at_its_neutral_value(
        self, ape_repo
    ):
        variants = ApeRVTool.get_variants()
        overrides = variants["mop_nolaunch"]["overrides"]
        assert overrides == {
            **variants["mop"]["overrides"],
            "activity_trigger_enabled": False,
        }
        key = APERV_PROPERTY_MAPPING["activity_trigger_enabled"]
        assert load_key_specs(ape_repo)[key].value_type == "BOOLEAN"
        # The key is MOP_LAUNCHER's activation key and false is its neutral value, so the
        # jar drops the feature from the plan and reports the key as inert instead of
        # aborting, and the device echo is the mop fixture without MOP_LAUNCHER.
        feature_java = (ape_repo / FEATURE_JAVA).read_text(encoding="utf-8")
        assert re.search(
            r'MOP_LAUNCHER\(\s*"'
            + re.escape(key)
            + r'"\s*,\s*Rule\.TRUE\s*,\s*"false"\s*\)',
            feature_java,
        )
        mop = _fixture(ape_repo, "mop")
        assert "MOP_LAUNCHER" in mop["features"]
        assert mop["params"][key] is True
