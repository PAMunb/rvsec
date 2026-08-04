"""The sweep of `APERV_PROPERTY_MAPPING` against the jar's own vocabulary (INV-APV-41).

Under stage-2 resolution a key the jar does not recognise is no longer inert: an unknown or
retired key aborts the run before step 1. That turns the mapping's contents from a tidiness
question into a correctness one, and this is where it is checked — against the jar's tables
rather than against another Python constant, which is the substitution the whole change is
about.

It lives in the migration tier because it needs the ape source checkout, which is not a
runtime dependency of `aperv-tool`. The assertions that need no checkout — the entry count,
the absence of the dead key — stay in the module's own suite.

The sweep found one dead entry, `mop_weight_activity`, which was deleted from the mapping. No
entry is dead now, and this test is what makes that a checked claim rather than a statement —
and what would report a new one if a later stage retires a further key.
"""

from aperv_tool.tools.aperv.tool import APERV_PROPERTY_MAPPING

from .jar_tables import load_key_specs, load_retired_keys


def _dead_entries(ape_repo):
    """Mapped keys the jar would reject, split by why: retired, or never accepted."""
    accepted = set(load_key_specs(ape_repo))
    retired = set(load_retired_keys(ape_repo))
    return {
        python_key: ("retired" if java_key in retired else "unknown")
        for python_key, java_key in APERV_PROPERTY_MAPPING.items()
        if java_key not in accepted or java_key in retired
    }


class TestMappingSweep:
    def test_no_mapped_key_is_unknown_to_the_jar(self, ape_repo):
        # An unknown key is worse than a retired one: retirement is a decision with a
        # recorded reason, while an unknown key means the two sides never agreed at all.
        unknown = {k for k, why in _dead_entries(ape_repo).items() if why == "unknown"}
        assert not unknown, f"mapped keys absent from the jar's vocabulary: {unknown}"

    def test_no_mapped_key_is_dead(self, ape_repo):
        # The mapping carries only keys the jar accepts. mop_weight_activity was the single
        # dead entry and is gone; a new one appearing is a decision to take on the record,
        # not something to delete silently, so this fails rather than tolerating a known set.
        dead = _dead_entries(ape_repo)
        assert not dead, f"mapped keys the jar would reject: {dead}"

    def test_the_sweep_is_not_vacuous(self, ape_repo):
        # Guards the check itself: if the parser returned an empty vocabulary, every mapped
        # key would look dead and the two tests above would still be answering about nothing.
        assert len(load_key_specs(ape_repo)) > 100
        assert len(APERV_PROPERTY_MAPPING) > 40

    def test_the_two_calibration_era_keys_are_live(self, ape_repo):
        # gh88's archive left a requirement asserting these are mapped-but-outside a guard
        # set. The guard dies with this change; the keys stay, because the jar declares both
        # as Feature.LLM sub-parameters.
        accepted = set(load_key_specs(ape_repo))
        assert APERV_PROPERTY_MAPPING["llm_max_tokens"] in accepted
        assert APERV_PROPERTY_MAPPING["llm_snap_tolerance_px"] in accepted
