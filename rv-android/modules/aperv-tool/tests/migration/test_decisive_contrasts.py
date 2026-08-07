"""The E3 decisive run's contrasts, checked on the plan the jar actually resolves.

The arm dicts say what each arm *overrides*; what decides the experiment is what each arm
*resolves to*. Those are no longer the same thing — a key can differ between two arms
because one overrides it and the other takes the preset's value, or be identical despite
one arm stating it and the other not. Only the effective configuration answers "is this
contrast single-factor", so that is what these tests diff.

They live in the migration tier because computing an effective plan needs the jar's preset
vectors and defaults, which come from the ape source checkout and are not a runtime
dependency of `aperv-tool`. The shape-level assertions that need no checkout — the reach
package present in all three, the jar declarations staying Python-only — stay in the
module's own suite, so the contract is never checked *only* where the checkout may be
missing.
"""

import pytest

from aperv_tool.tools.aperv.tool import ApeRVTool

from .jar_tables import load_key_specs, load_presets
from .capture_arm_baseline import regenerate

# What "MOP guidance off" is allowed to move, stated in jar keys because that is the level
# the run sees. Five weights plus the activity-trigger launcher: the control zeroes the four
# scoring weights explicitly and lets mop_frontier_weight and activity_trigger_enabled fall
# back to the preset's 0/false, which reaches the same plan by a shorter route.
MOP_CONTRAST_KEYS = {
    "ape.mopWeightDirect",
    "ape.mopWeightTransitive",
    "ape.mopWeightOpenMenu",
    "ape.mopWeightWtg",
    "ape.mopFrontierWeight",
    "ape.activityTriggerEnabled",
}


@pytest.fixture(scope="session")
def plans(ape_repo):
    """Each decisive-run arm's effective configuration, keyed by arm name."""
    presets = load_presets(ape_repo)
    key_specs = load_key_specs(ape_repo)
    variants = ApeRVTool.get_variants()
    return {
        name: regenerate(variants[name], presets, key_specs)
        for name in ("mop_on_llm_off", "mop_off_llm_off", "mop_on_llm_70")
    }


def _differing(left, right):
    return {
        key
        for key in set(left) | set(right)
        if left.get(key, "<absent>") != right.get(key, "<absent>")
    }


class TestSingleFactorContrasts:
    def test_reference_and_control_differ_exactly_in_the_mop_keys(self, plans):
        # RQ-C1. Anything else moving here would mean the control removed more than MOP
        # guidance, and the measured difference would no longer be attributable to it.
        assert _differing(plans["mop_on_llm_off"], plans["mop_off_llm_off"]) == (
            MOP_CONTRAST_KEYS
        )

    def test_reference_and_llm_arm_differ_only_in_llm_keys(self, plans):
        # RQ-C3. The two arms sit on different presets — mop and llm_mop — and this is
        # where that is shown to be an LLM-only difference rather than taken on trust.
        differing = _differing(plans["mop_on_llm_off"], plans["mop_on_llm_70"])

        assert differing, "the LLM arm must differ from the reference somewhere"
        assert all(key.startswith("ape.llm") for key in differing), sorted(differing)
        assert not differing & MOP_CONTRAST_KEYS

    def test_the_control_keeps_navigation_alive(self, plans):
        # INV-APV-30: MOP guidance off, navigation on. The document is still pushed and the
        # frontier boost still set, so WtgPass and FrontierPass keep running on generic
        # signal — the contrast is "MOP guidance on versus off", not "substrate versus
        # almost none".
        control = plans["mop_off_llm_off"]

        assert control["ape.mopDataPath"] == "/data/local/tmp/mop-artifact.json"
        assert control["ape.frontierBoostWeight"] == 200

    def test_the_contrast_is_not_vacuous(self, plans):
        # If the plans came back empty or identical, both contrast tests above would still
        # look sensible while proving nothing.
        for name, plan in plans.items():
            assert len(plan) > 40, f"{name} resolved to a suspiciously small plan"
        assert plans["mop_on_llm_off"] != plans["mop_off_llm_off"]
