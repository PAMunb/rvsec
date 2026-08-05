"""The gate: every surviving arm must resolve to exactly what it resolved to before.

This is the whole safety argument of gh95. Arms are being re-expressed from explicit
property dictionaries into `preset + overrides`, and the claim that nothing moved is only
worth as much as the check behind it — so the claim is executed, per arm, against a baseline
captured before the first edit.

Every surviving arm now carries a `preset`, so regeneration resolves the jar's preset vector,
overlays the arm's `overrides` and compares the typed result against what the arm's explicit
property dictionary produced before the migration. Any drift between the two shapes fails the
arm that drifted.

**Retirements are listed, never inferred.** A baseline arm that no longer exists is a pass
only if `retirements.py` says so, with its kind. A name that vanished without being on that
list fails — otherwise deleting an arm by mistake and retiring one on purpose would look
identical from here.

The check is **one-time** (INV-APV-44). It is deleted and the baseline archived once the
owner has signed off and `gh97-rearch-ab-gate` has executed — the sign-off approves the
migration, and `gh97` is the first run in which a device honours `ape.preset`, so this
evidence outlives the sign-off by exactly that one run. Keeping it beyond that would recreate
the constant-vs-constant guard this change retires, with the baseline playing the role of the
frozen copy.
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

# Keys the jar retired after the baseline was captured, each with the reason it went.
#
# The baseline is a historical document: it records what the pre-change arms resolved to
# against the vocabulary of that day, and it is deliberately never recaptured, because a
# baseline regenerated from the migrated code would compare the code against itself. So when
# the jar deletes a key, the regenerated side legitimately stops carrying it while the
# baseline still does, and that gap is not migration drift.
#
# Listed, never inferred, on the same principle as the arm retirements: excluding a named key
# with a recorded reason is a decision, whereas ignoring every key that vanished would hide an
# arm quietly losing a setting it should still have. `TestJarRetiredKeys` below proves each
# entry is still earning its place.
KEYS_RETIRED_BY_THE_JAR = {
    "ape.stepTelemetryEnabled": (
        "Feature.STEP_TELEMETRY was deleted outright, not merely its activation key: "
        "membership of that enum is what makes a mechanism expressible by an arm, and the "
        "event sink is an instrument every arm carries alike (event-sink INV-SNK-07, "
        "Telemetry Neutrality). The Python side dropped the key first and the jar then "
        "refused it, the ordering gh93 established for ape.apePureMode"
    ),
}


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
    """The typed plan an arm resolves to: the jar's preset vector, overlaid with the arm's
    `overrides`, overlaid on the jar's declared defaults for whatever neither supplies.

    This is the shape the baseline is compared against. The baseline itself was produced by
    the other shape — the pre-change explicit key dictionaries — and the two producing the
    same map is exactly what this module tests.
    """
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


def diff(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Per-key `{key: (baseline, regenerated)}` for everything that moved.

    Keys the jar has since retired are excluded by name: the baseline records them because it
    predates their removal, and their absence from the regenerated plan is the jar's decision
    rather than this migration's drift.
    """
    keys = (set(expected) | set(actual)) - set(KEYS_RETIRED_BY_THE_JAR)
    return {
        key: (expected.get(key, "<absent>"), actual.get(key, "<absent>"))
        for key in keys
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


class TestJarRetiredKeys:
    """An exclusion is only as trustworthy as the check that it is still deserved."""

    @pytest.mark.parametrize("key", sorted(KEYS_RETIRED_BY_THE_JAR))
    def test_the_jar_really_rejects_it(self, key, key_specs):
        # If the jar ever accepts the key again, the exclusion stops being a record of a
        # retirement and becomes a blind spot hiding a real difference.
        assert key not in key_specs

    @pytest.mark.parametrize("key", sorted(KEYS_RETIRED_BY_THE_JAR))
    def test_the_mapping_no_longer_carries_it(self, key):
        # Under stage-2 resolution an unknown key aborts the run before step 1, so a key
        # excluded here while still mapped would fail every arm on a device while the diff
        # stayed green — the one combination that must not be reachable.
        assert key not in set(APERV_PROPERTY_MAPPING.values())

    @pytest.mark.parametrize("key", sorted(KEYS_RETIRED_BY_THE_JAR))
    def test_the_baseline_actually_carried_it(self, key, baseline):
        # A key no baseline arm ever had needs no exclusion; the entry would be dead text
        # that outlives what it documents.
        assert any(key in entry["config"] for entry in baseline.values())


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
