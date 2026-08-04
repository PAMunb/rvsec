"""The gate: every surviving arm must resolve to exactly what it resolved to before.

This is the whole safety argument of gh95. Arms are being re-expressed from explicit
property dictionaries into `preset + overrides`, and the claim that nothing moved is only
worth as much as the check behind it — so the claim is executed, per arm, against a baseline
captured before the first edit.

**Green from day one, by construction.** An arm that has not been re-expressed yet carries
no `preset` key, and for those the regeneration takes the same path the capture took. So the
test passes at the start of the migration and keeps passing through it; what makes it
informative is that each arm switches path the moment it is re-expressed, and any drift
introduced by that switch fails immediately, in the group that caused it.

**Retirements are listed, never inferred.** A baseline arm that no longer exists is a pass
only if `retirements.py` says so, with its kind. A name that vanished without being on that
list fails — otherwise deleting an arm by mistake and retiring one on purpose would look
identical from here.

The check is **one-time** (INV-APV-44). After owner sign-off it is deleted and the baseline
archived: keeping it would recreate the constant-vs-constant guard this change retires, with
the baseline playing the role of the frozen copy.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from aperv_tool.tools.aperv.tool import APERV_PROPERTY_MAPPING, ApeRVTool

from .capture_arm_baseline import BASELINE_FILE, DEVICE_ARTIFACT_PATH, typed
from .jar_tables import KeySpec, load_key_specs, load_presets
from .retirements import KIND_NAME_CONSOLIDATED, RETIREMENTS

# The pre-change surface. Pinned so a baseline that silently lost arms cannot make the whole
# check vacuous — an empty baseline diffs empty against everything.
BASELINE_ARM_COUNT = 29


@pytest.fixture(scope="session")
def baseline() -> Dict[str, Any]:
    if not BASELINE_FILE.is_file():
        pytest.fail(
            f"{BASELINE_FILE.name} is missing: capture it from the unmodified tool.py "
            "before any arm is edited (APE_REPO=... python -m tests.migration."
            "capture_arm_baseline)"
        )
    return json.loads(BASELINE_FILE.read_text())["arms"]


@pytest.fixture(scope="session")
def key_specs(ape_repo) -> Dict[str, KeySpec]:
    return load_key_specs(ape_repo)


@pytest.fixture(scope="session")
def presets(ape_repo) -> Dict[str, Dict[str, str]]:
    return load_presets(ape_repo)


def regenerate(
    arm: Dict[str, Any],
    presets: Dict[str, Dict[str, str]],
    key_specs: Dict[str, KeySpec],
) -> Dict[str, Any]:
    """The typed plan an arm resolves to, from whichever shape it currently has.

    Re-expressed arm: the jar's preset vector, overlaid with the arm's `overrides`, overlaid
    on the jar defaults for whatever neither supplies. Not-yet-migrated arm: its own explicit
    keys over the same defaults. The two shapes are supposed to produce the same map, and
    that equality is exactly what this module tests.
    """
    if "preset" not in arm:
        return _from_explicit_keys(arm, key_specs)

    vector = presets[arm["preset"]]
    overrides = arm.get("overrides", {})
    config: Dict[str, Any] = {}
    for python_key, java_key in APERV_PROPERTY_MAPPING.items():
        spec = key_specs.get(java_key)
        if python_key in overrides:
            config[java_key] = typed(overrides[python_key], spec)
        elif java_key in vector:
            config[java_key] = typed(vector[java_key], spec)
        elif spec is not None and spec.default is not None:
            config[java_key] = typed(spec.default, spec)
    if arm.get("mop_data") == "static_analysis":
        config["ape.mopDataPath"] = DEVICE_ARTIFACT_PATH
    return config


def _from_explicit_keys(
    arm: Dict[str, Any], key_specs: Dict[str, KeySpec]
) -> Dict[str, Any]:
    from .capture_arm_baseline import effective_config

    return effective_config(
        arm, key_specs, mop_pushed=arm.get("mop_data") == "static_analysis"
    )


def diff(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Per-key `{key: (baseline, regenerated)}` for everything that moved."""
    return {
        key: (expected.get(key, "<absent>"), actual.get(key, "<absent>"))
        for key in set(expected) | set(actual)
        if expected.get(key, "<absent>") != actual.get(key, "<absent>")
    }


def surviving_arms() -> list[str]:
    return sorted(ApeRVTool.get_variants())


class TestBaselineIntegrity:
    """Before trusting a green diff, check there is something to diff against."""

    def test_baseline_covers_the_whole_pre_change_surface(self, baseline):
        assert len(baseline) == BASELINE_ARM_COUNT

    def test_every_baseline_arm_carries_a_non_empty_plan(self, baseline):
        # A baseline of empty configs would diff empty against anything at all.
        empty = [name for name, entry in baseline.items() if not entry["config"]]
        assert not empty, f"baseline arms with no configuration captured: {empty}"

    def test_retirement_list_covers_exactly_the_names_it_claims(self, baseline):
        assert len(RETIREMENTS) == 21
        unknown = set(RETIREMENTS) - set(baseline)
        assert not unknown, f"retired names absent from the baseline: {unknown}"


class TestRegenerationDiff:
    @pytest.mark.parametrize("name", surviving_arms())
    def test_arm_regenerates_its_baseline(self, name, baseline, presets, key_specs):
        assert name in baseline, (
            f"'{name}' is not in the baseline: a new arm may not be introduced by a "
            "migration whose contract is that nothing changes"
        )
        arm = ApeRVTool.get_variants()[name]
        regenerated = regenerate(arm, presets, key_specs)
        difference = diff(baseline[name]["config"], regenerated)
        assert (
            not difference
        ), f"{name} no longer resolves to its baseline: {difference}"

    @pytest.mark.parametrize("name", surviving_arms())
    def test_orchestration_fields_are_preserved(self, name, baseline):
        # strategy and mop_data never reach ape.properties, but they decide which agent runs
        # and whether the MOP artifact is derived at all — losing one would change the run
        # without changing a single property line.
        arm = ApeRVTool.get_variants()[name]
        assert arm.get("strategy") == baseline[name]["strategy"]
        assert arm.get("mop_data") == baseline[name]["mop_data"]

    def test_a_vanished_arm_is_either_retired_on_the_record_or_a_failure(
        self, baseline
    ):
        vanished = set(baseline) - set(ApeRVTool.get_variants())
        undocumented = vanished - set(RETIREMENTS)
        assert not undocumented, (
            f"arms gone with no retirement recorded: {undocumented}. A deletion and a "
            "retirement are different facts; add the entry to retirements.py or restore "
            "the arm"
        )


class TestConsolidatedNames:
    """A retirement that claims its configuration survives has to prove it."""

    @pytest.mark.parametrize(
        "retired,survivor",
        [
            (name, entry.survivor)
            for name, entry in RETIREMENTS.items()
            if entry.kind == KIND_NAME_CONSOLIDATED
        ],
    )
    def test_survivor_reproduces_the_retired_name_baseline(
        self, retired, survivor, baseline, presets, key_specs
    ):
        assert survivor, f"{retired} is consolidated but names no surviving arm"
        variants = ApeRVTool.get_variants()
        assert survivor in variants, f"{retired}'s survivor {survivor} does not exist"
        regenerated = regenerate(variants[survivor], presets, key_specs)
        difference = diff(baseline[retired]["config"], regenerated)
        assert not difference, (
            f"{survivor} does not reproduce {retired}'s configuration: {difference}. "
            "The retirement's whole justification is that the two are identical"
        )


def build_report(baseline, presets, key_specs) -> str:
    """The human-readable per-arm migration record (task 7.1), archived at sign-off."""
    variants = ApeRVTool.get_variants()
    lines = [
        "# Arm regeneration diff",
        "",
        f"Baseline arms: {len(baseline)} | surviving arms: {len(variants)} | "
        f"retirements: {len(RETIREMENTS)}",
        "",
        "## Regenerated arms",
        "",
    ]
    for name in sorted(variants):
        difference = diff(
            baseline[name]["config"], regenerate(variants[name], presets, key_specs)
        )
        status = "empty" if not difference else f"DIVERGENT {difference}"
        lines.append(
            f"- `{name}` — preset `{variants[name].get('preset', '(not migrated)')}` — {status}"
        )

    lines += ["", "## Documented retirements", ""]
    for name in sorted(RETIREMENTS):
        entry = RETIREMENTS[name]
        survivor = f" → survives as `{entry.survivor}`" if entry.survivor else ""
        lines.append(f"- `{name}` — *{entry.kind}*{survivor} — {entry.reason}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from .jar_tables import resolve_ape_repo

    repo = resolve_ape_repo()
    print(
        build_report(
            json.loads(BASELINE_FILE.read_text())["arms"],
            load_presets(repo),
            load_key_specs(repo),
        )
    )
