"""G5 of the campaign message gate reads the evidence keys of a `-NOBS-` envelope (INV-INS-166).

    INV-INS-166   the evidence keys `vfp` and `vcls` MAY follow `msg` only in a `-NOBS-`
                  envelope, in that order, each at most once, quoted like every other value

`experimento-gh104/scripts/gh104_gates.py` is the gate run over every new campaign. Its
envelope pattern has to accept the two trailing keys, and G5 has to reject them on a code
of any other family -- decided by the `site_kind` column of `codes.csv` when the gate is
given the catalogue, and by the KIND letters of the code otherwise. The catalogue is read
by column name, so a seventh column (`label`) is transparent. Every input is synthetic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GATES = REPO / "experimento-gh104" / "scripts" / "gh104_gates.py"


@pytest.fixture(scope="module")
def gates():
    """The experiment-local gate module, loaded by path (it is not on any import path)."""
    spec = importlib.util.spec_from_file_location("experimento_gh104_gates", GATES)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = (
        module  # dataclasses resolve their module through sys.modules
    )
    spec.loader.exec_module(module)
    return module


BASE = "v=1 code={code} ev=init obj=SSLContext val='' exp='a factory array' msg='no producer observed'"


def _envelope(code: str, suffix: str = "") -> str:
    return BASE.format(code=code) + suffix


def _codes_csv(tmp_path: Path) -> Path:
    """A seven-column catalogue with the `label` column last, as `codes.csv` carries it."""
    path = tmp_path / "codes.csv"
    path.write_text(
        "spec,code,error_type,site_kind,event,file_line,label\n"
        "SSLContextSpec,SSLCONTEXT-NOBS-00,UnsatisfiedConstraint,NOBS,init,SSLContextSpec.mop:1,not-observed\n"
        "SSLContextSpec,SSLCONTEXT-NOBS-01,UnsatisfiedConstraint,NOBS,init,SSLContextSpec.mop:2,application-manager\n"
        "SSLContextSpec,SSLCONTEXT-ORDER-00,InvalidSequenceOfMethodCalls,ORDER,init,SSLContextSpec.mop:3,sequence\n"
        "SSLContextSpec,SSLCONTEXT-PROTO-00,UnsafeProtocol,PROTO,init,SSLContextSpec.mop:4,violation\n",
        encoding="utf-8",
    )
    return path


class TestEnvelopeGrammar:
    """What `ENVELOPE_RE` accepts after `msg`."""

    def test_an_envelope_without_evidence_still_matches(self, gates):
        vocab = gates.load_code_vocabulary(None)
        verdict = gates.inspect_envelope(_envelope("SSLCONTEXT-NOBS-00"), vocab)

        assert verdict.matched
        assert not verdict.evidence_off_nobs

    @pytest.mark.parametrize(
        "suffix",
        [
            " vfp='sha256:0123456789abcdef'",
            " vcls='com.example.TrustAll'",
            " vfp='sha256:0123456789abcdef' vcls='a.B,c.D'",
            " vcls='it\\'s.Quoted'",
        ],
    )
    def test_evidence_keys_after_msg_match_on_nobs(self, gates, suffix):
        vocab = gates.load_code_vocabulary(None)
        verdict = gates.inspect_envelope(_envelope("SSLCONTEXT-NOBS-01", suffix), vocab)

        assert verdict.matched
        assert not verdict.evidence_off_nobs
        assert not verdict.truncated

    @pytest.mark.parametrize(
        "suffix",
        [
            " vcls='a.B' vfp='sha256:0123456789abcdef'",  # wrong order
            " vfp='sha256:00' vfp='sha256:11'",  # twice
            " vfp=sha256:00",  # unquoted
            " extra='x'",  # unknown key
        ],
    )
    def test_other_trailing_shapes_are_malformed(self, gates, suffix):
        vocab = gates.load_code_vocabulary(None)
        verdict = gates.inspect_envelope(_envelope("SSLCONTEXT-NOBS-01", suffix), vocab)

        assert verdict.claims
        assert not verdict.matched


class TestEvidenceOnlyOnNobs:
    """G5 rejects evidence keys on a code of any other family."""

    def test_without_catalogue_the_family_comes_from_the_code(self, gates):
        vocab = gates.load_code_vocabulary(None)

        on_order = gates.inspect_envelope(
            _envelope("SSLCONTEXT-ORDER-00", " vfp='sha256:00'"), vocab
        )
        on_nobs = gates.inspect_envelope(
            _envelope("SSLCONTEXT-NOBS-00", " vfp='sha256:00'"), vocab
        )

        assert on_order.evidence_off_nobs
        assert not on_nobs.evidence_off_nobs

    def test_with_catalogue_the_family_comes_from_site_kind(self, gates, tmp_path):
        """The column decides: a row whose code spells `NOBS` but is filed elsewhere is not NOBS."""
        path = _codes_csv(tmp_path)
        path.write_text(
            path.read_text(encoding="utf-8")
            + "SSLContextSpec,SSLCONTEXT-NOBS-02,UnsatisfiedConstraint,CONSTR,init,SSLContextSpec.mop:5,violation\n",
            encoding="utf-8",
        )
        vocab = gates.load_code_vocabulary(path)

        filed_elsewhere = gates.inspect_envelope(
            _envelope("SSLCONTEXT-NOBS-02", " vcls='a.B'"), vocab
        )
        filed_nobs = gates.inspect_envelope(
            _envelope("SSLCONTEXT-NOBS-01", " vcls='a.B'"), vocab
        )

        assert filed_elsewhere.evidence_off_nobs
        assert not filed_nobs.evidence_off_nobs

    def test_the_label_column_is_transparent(self, gates, tmp_path):
        vocab = gates.load_code_vocabulary(_codes_csv(tmp_path))

        assert vocab.authoritative
        assert vocab.codes == {
            "SSLCONTEXT-NOBS-00",
            "SSLCONTEXT-NOBS-01",
            "SSLCONTEXT-ORDER-00",
            "SSLCONTEXT-PROTO-00",
        }
        assert vocab.family("SSLCONTEXT-PROTO-00") == "PROTO"

    def test_g5_fails_on_evidence_off_nobs_and_passes_without(self, gates, tmp_path):
        vocab = gates.load_code_vocabulary(_codes_csv(tmp_path))
        clean_csv, clean_log = gates.CsvReading(), gates.LogcatReading()
        gates._accumulate_violation(
            _envelope("SSLCONTEXT-NOBS-01", " vcls='a.B'"),
            "fixture:1",
            False,
            clean_log,
            vocab,
        )
        gates._accumulate_violation(
            _envelope("SSLCONTEXT-PROTO-00"), "fixture:2", False, clean_log, vocab
        )

        dirty_csv, dirty_log = gates.CsvReading(), gates.LogcatReading()
        gates._accumulate_violation(
            _envelope("SSLCONTEXT-PROTO-00", " vfp='sha256:00'"),
            "fixture:3",
            False,
            dirty_log,
            vocab,
        )

        assert gates.gate_g5(clean_csv, clean_log, vocab).status == gates.PASS
        dirty = gates.gate_g5(dirty_csv, dirty_log, vocab)
        assert dirty.status == gates.FAIL
        assert dirty.detail["logcat_evidence_off_nobs"] == 1
        assert dirty.samples

    def test_errors_csv_rows_are_judged_the_same_way(self, gates, tmp_path):
        vocab = gates.load_code_vocabulary(_codes_csv(tmp_path))
        reading = gates.CsvReading()
        row = {
            "message": _envelope("SSLCONTEXT-ORDER-00", " vfp='sha256:00'"),
            "unique_msg": "c:::m:::SSLContextSpec:::t:::code:::ev:::msg",
        }

        gates._accumulate_row(row, "errors.csv:2", reading, vocab)

        assert reading.evidence_off_nobs == 1
        assert reading.envelope_matched == 1
