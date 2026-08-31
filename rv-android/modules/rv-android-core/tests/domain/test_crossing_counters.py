"""The crossing: every discard counted, and classified by scope (INV-ANA-68).

`register_method_call` is where an executed method meets the static analysis.
Before this change a class or signature the artefact did not carry left nothing
behind but a `logger.debug` — a run could discard thousands of events and every
published number would look the same. These tests pin the three counters and,
just as importantly, pin what they must NOT do to the arithmetic identity that
INV-ANA-62 already guards.
"""

import pytest
from rv_android_core.domain.coverage import (
    ClassCoverageData,
    LogcatRepository,
    MethodCoverageData,
    ParserDiagnostics,
)
from rv_android_core.domain.log import RvCoverageLog

KEY = "com.example.app"
SIGNATURE = f"{KEY}.Known.known()V"


@pytest.fixture
def populated():
    """A repository holding one known class with one known method."""

    def _build(scope_key):
        repo = LogcatRepository(scope_key=scope_key)
        clazz = ClassCoverageData(
            name=f"{KEY}.Known", component_type="activity", is_main=False
        )
        clazz.methods[SIGNATURE] = MethodCoverageData(
            class_name=f"{KEY}.Known",
            method_name="known",
            signature=SIGNATURE,
            parameters=[],
            from_static_analysis=True,
        )
        repo.add_class(clazz)
        return repo

    return _build


def _call(clazz, signature):
    return RvCoverageLog(clazz=clazz, method="m", params="", signature=signature)


class TestClassification:
    def test_out_of_scope_class_counts_out_of_scope(self, populated):
        repo = populated(KEY)
        repo.register_method_call(
            _call("retrofit2.Retrofit", "retrofit2.Retrofit.x()V")
        )
        d = repo.parser_diagnostics
        assert d.unmatched_out_of_scope == 1
        assert d.unmatched_in_scope == 0
        assert d.unmatched_unclassified == 0

    def test_in_scope_class_counts_in_scope(self, populated):
        """This is the one that indicts the denominator, so it gets its own name."""
        repo = populated(KEY)
        repo.register_method_call(_call(f"{KEY}.Missing", f"{KEY}.Missing.x()V"))
        d = repo.parser_diagnostics
        assert d.unmatched_in_scope == 1
        assert d.unmatched_out_of_scope == 0

    def test_known_class_unknown_signature_also_counts_in_scope(self, populated):
        """Half a hole is still a hole: the class is there, the method is not."""
        repo = populated(KEY)
        repo.register_method_call(_call(f"{KEY}.Known", f"{KEY}.Known.other()V"))
        assert repo.parser_diagnostics.unmatched_in_scope == 1

    def test_no_key_counts_unclassified_never_in_scope(self, populated):
        """The state of all 162 stored artefacts.

        Attributing these to in-scope would manufacture evidence for exactly the
        claim the counter exists to test.
        """
        repo = populated(None)
        repo.register_method_call(_call(f"{KEY}.Missing", f"{KEY}.Missing.x()V"))
        repo.register_method_call(
            _call("retrofit2.Retrofit", "retrofit2.Retrofit.x()V")
        )
        d = repo.parser_diagnostics
        assert d.unmatched_unclassified == 2
        assert d.unmatched_in_scope == 0
        assert d.unmatched_out_of_scope == 0

    def test_a_matched_call_counts_nothing(self, populated):
        repo = populated(KEY)
        repo.register_method_call(_call(f"{KEY}.Known", SIGNATURE))
        d = repo.parser_diagnostics
        assert (
            d.unmatched_in_scope,
            d.unmatched_out_of_scope,
            d.unmatched_unclassified,
        ) == (0, 0, 0)


class TestSerialization:
    def test_all_three_reach_to_dict(self):
        d = ParserDiagnostics(
            unmatched_out_of_scope=3, unmatched_in_scope=5, unmatched_unclassified=7
        )
        out = d.to_dict()
        assert out["unmatched_out_of_scope"] == 3
        assert out["unmatched_in_scope"] == 5
        assert out["unmatched_unclassified"] == 7


class TestIdentityUnchanged:
    def test_counters_stay_out_of_discarded_lines(self):
        """INV-ANA-62's identity is about lines that became NO record.

        These count lines that DID become records, which is precisely why the
        sentinel and grammar counters are already excluded. Adding them would
        double-count against lines read and break an invariant this change does
        not touch.
        """
        d = ParserDiagnostics(
            lines_not_threadtime=1,
            lines_other_tag=2,
            format1_regex_failed=3,
            format2_short=4,
            format3_unresolved=5,
            unrecognised=6,
            continuation_lines=7,
            unmatched_out_of_scope=100,
            unmatched_in_scope=200,
            unmatched_unclassified=300,
        )
        assert d.discarded_lines == 1 + 2 + 3 + 4 + 5 + 6 + 7
