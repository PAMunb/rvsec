"""Tests of measure_occ.py on a synthetic threadtime logcat."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "measure_occ.py"
_SPEC = importlib.util.spec_from_file_location("measure_occ", _SCRIPT)
measure_occ = importlib.util.module_from_spec(_SPEC)
sys.modules["measure_occ"] = measure_occ
_SPEC.loader.exec_module(measure_occ)

CIPHER = "CipherSpec,com.example.Crypto,Crypto,encrypt,Crypto.java:42,InvalidSequenceOfMethodCalls"
CIPHER_OCC = f"{CIPHER},CIPHER-ORDER-00,doFinal"
PRE = "PreSpec,com.x.Pre,Pre,onCreate,Pre.java:3,ERROR_STATE"
LOST = "LostSpec,com.x.Lost,Lost,run,Lost.java:9,ERROR_STATE"

# One run: a launch-time violation before the first heartbeat, three heartbeats,
# a violation with its envelope and three later occurrences, an n=1 whose RVSEC
# line never arrived, and an eight-field occurrence line.
LOGCAT = f"""\
10-07 12:00:00.400  5000  5000 I RVSEC   : {PRE},expecting something
10-07 12:00:00.500  5000  5000 V RVSEC-OCC: {PRE},UNSPECIFIED,UNSPECIFIED,1
10-07 12:00:01.000  9100  9100 I ApeRvHb : s=1 t=0
10-07 12:00:01.200  5000  5000 I RVSEC   : {CIPHER},v=1 code=CIPHER-ORDER-00 ev=doFinal obj=Cipher val='' exp='a, b' msg=''
10-07 12:00:01.201  5000  5000 V RVSEC-OCC: {CIPHER_OCC},1
10-07 12:00:01.400  5000  5000 V RVSEC-OCC: {CIPHER_OCC},5
10-07 12:00:02.000  9100  9100 I ApeRvHb : s=2 t=1000
10-07 12:00:02.100  5000  5000 V RVSEC-OCC: {CIPHER_OCC},12
10-07 12:00:02.200  5000  5000 V RVSEC-OCC: {LOST},UNSPECIFIED,UNSPECIFIED,1
10-07 12:00:02.300  5000  5000 V RVSEC-OCC: BadSpec,com.x.Bad,Bad,run,Bad.java:9,ERROR_STATE,UNSPECIFIED,1
10-07 12:00:02.400  5000  5000 I RVSEC-COV: <com.x.Bad: void run()>
--------- beginning of crash
10-07 12:00:03.000  9100  9100 I ApeRvHb : s=3 t=2000
10-07 12:00:04.000  5000  5000 V RVSEC-OCC: {CIPHER_OCC},20
"""


@pytest.fixture
def run(tmp_path: Path) -> dict:
    logcat = tmp_path / "app_1.apk" / "app_1.apk__1__600__aperv:mop_off_llm_off.logcat"
    logcat.parent.mkdir()
    logcat.write_text(LOGCAT, encoding="utf-8")
    return measure_occ.measure_logcat(logcat)


def test_rvsec_with_its_n1_is_paired(run: dict) -> None:
    # PRE pairs through the UNSPECIFIED sentinel, CIPHER through its envelope.
    assert run["pairing"]["rvsec_lines"] == 2
    assert run["pairing"]["paired"] == 2
    assert run["pairing"]["unpaired_rvsec"] == 0


def test_n1_without_rvsec_is_counted_as_loss(run: dict) -> None:
    assert run["pairing"]["occ_n1_lines"] == 3
    assert run["pairing"]["unpaired_occ_n1"] == 1
    assert run["pairing"]["unpaired_occ_n1_keys"] == [
        {"key": f"{LOST},UNSPECIFIED,UNSPECIFIED", "count": 1}
    ]


def test_line_before_first_heartbeat_is_pre_exploration(run: dict) -> None:
    assert run["placement"] == {
        "pre_exploration": 1,
        "exploration": 5,
        "post_exploration": 1,
        "unaligned": 0,
        "heartbeats": 3,
        "steps_with_occ": 2,
    }


def test_eight_field_line_is_counted_as_malformed(run: dict) -> None:
    assert run["occ"]["malformed"] == 1
    assert run["occ"]["malformed_examples"][0].startswith("BadSpec,")
    with pytest.raises(measure_occ.MalformedOccLine):
        measure_occ.parse_occ("a,b,c,d,e,f,g,1")
    with pytest.raises(measure_occ.MalformedOccLine):
        measure_occ.parse_occ("a,b,c,d,e,f,g,h,x")


def test_max_n_and_top_identity(run: dict) -> None:
    assert run["identities"]["count"] == 3
    assert run["identities"]["max_n"] == 20
    assert run["identities"]["top"][0] == {"identity": CIPHER_OCC, "n": 20}


def test_rates(run: dict) -> None:
    # Seven occurrence lines over the bins 00..04 (five seconds); second 02 holds three.
    assert run["occ"]["lines"] == 7
    assert run["occ"]["span_s"] == 5
    assert run["occ"]["mean_per_s"] == 1.4
    assert run["occ"]["peak_per_s"] == 3
    # Second 02 holds a heartbeat, three occurrence lines and a coverage line.
    assert run["all_lines"] == {"lines": 13, "peak_per_s": 5}


def test_main_writes_report_and_fails_on_a_malformed_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    logcat = tmp_path / "r" / "x.logcat"
    logcat.parent.mkdir()
    logcat.write_text(LOGCAT, encoding="utf-8")
    assert measure_occ.main([str(tmp_path)]) == 1
    report = json.loads((tmp_path / "measure_occ.json").read_text(encoding="utf-8"))
    assert len(report["runs"]) == 1
    assert report["runs"][0]["trace"] is None
    assert "1 logcat files" in capsys.readouterr().out


def test_main_exits_zero_when_every_line_parses(tmp_path: Path) -> None:
    logcat = tmp_path / "r" / "x.logcat"
    logcat.parent.mkdir()
    clean = "".join(line for line in LOGCAT.splitlines(keepends=True) if "BadSpec" not in line)
    logcat.write_text(clean, encoding="utf-8")
    assert measure_occ.main([str(tmp_path)]) == 0
