"""cmp162's arm roster and declarations, as data, for the tests that need both.

Two test modules run the whole chain over the recorded campaign — the smoke and
the corrupted fixture — and both need the same two things: the arm table the
loader decomposes with, and the `ArmManifest` the gates judge against. They live
here rather than in one of the test modules so that neither imports the other,
which is the pattern `fixture_gate` and `baseline_runs` already follow in this
suite.

The roster is **declared, not derived.** `run_identity.decompose_arm` refuses to
split an arm label into a `(tool, variant)` pair (INV-CAN-02) because the
regularity of the current labels is a convention of the current roster and not a
rule the filename enforces. A test that split one here would be reimplementing
the exact heuristic the invariant exists to forbid, so the pairs are written out
and `assert_matches_manifest` checks them against the fixture's own list.
"""

from __future__ import annotations

from aperv_tool.analysis.gates import ArmManifest, ArmSpec
from aperv_tool.analysis.runspec import ManifestArm

#: Arm label → `(tool, variant)`. The bare `ape` is the collapsed label of a tool
#: with one configuration, not a tool with an empty variant.
ARM_TABLE: dict[str, tuple[str, str]] = {
    "ape": ("ape", ""),
    "aperv:mop_off_llm_off": ("aperv", "mop_off_llm_off"),
    "aperv:mop_on_llm_off": ("aperv", "mop_on_llm_off"),
}

#: The campaign declared no build digest for its arms in a form this fixture
#: carries, so gate 2's digest check has nothing to compare and reports
#: `not-run`. That is the honest state, and the tests assert it rather than
#: papering over it with an invented digest.
UNDECLARED = None

#: The arms that must carry no MOP signal at all, and are therefore subject to
#: gate 1. `ape` is the upstream jar; `aperv:mop_off_llm_off` is the instrumented
#: jar with guidance switched off.
CONTROL_ARMS = frozenset({"ape", "aperv:mop_off_llm_off"})


def assert_matches_manifest(manifest: dict) -> None:
    """Fail loudly if the fixture's roster has moved away from this declaration.

    Args:
        manifest: The loaded `cmp162_manifest.json`.

    Raises:
        AssertionError: The declared roster and the manifest's disagree. Guessing
            the difference is what this exists to prevent — an arm silently
            absent from the table drops every one of its runs.
    """
    assert set(ARM_TABLE) == set(
        manifest["facts"]["arms"]
    ), "the declared roster no longer matches the manifest's arms"


def arm_manifest() -> ArmManifest:
    """cmp162's declarations, as data."""
    return ArmManifest(
        arms={
            arm: ArmSpec(
                tool=tool,
                variant=variant,
                declaration=ManifestArm(
                    arm=arm,
                    digest=UNDECLARED,
                    preset=None,
                    features=None,
                    params={},
                ),
                control=arm in CONTROL_ARMS,
            )
            for arm, (tool, variant) in ARM_TABLE.items()
        }
    )
