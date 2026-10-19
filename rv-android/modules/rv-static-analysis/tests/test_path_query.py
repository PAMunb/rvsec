"""
Tests for the ``path`` subcommand (``rv_static_analysis.path_query``, INV-ANA-98).

The fixture is a small document laid out as GATOR writes it with
``distancePaths=true``: ``distanceTargets``, ``reachability``, then
``pathMethods`` (sorted signatures) and ``distancePaths`` (``[i, v, n]`` steps
sorted by ``(i, v)``). ``Home$1.onClick`` reaches target 0 (``HOTP.hmac_sha1``) in
three calls and target 1 (``Store.save``) in one; it has no pair for target 2.
"""

import json
import sys
from pathlib import Path

import pytest
from rv_static_analysis.__main__ import main
from rv_static_analysis.path_query import PathQueryRefused, query_paths

ON_CLICK = "<org.cry.otp.Home$1: void onClick(android.view.View)>"
GEN = "<org.cry.otp.HOTP: java.lang.String gen(byte[])>"
GENERATE = "<org.cry.otp.HOTP: java.lang.String generateOTP(byte[],long)>"
HMAC = "<org.cry.otp.HOTP: byte[] hmac_sha1(byte[],byte[])>"
SAVE = "<org.cry.otp.Store: void save()>"
OTHER = "<org.cry.otp.Other: void run()>"
IDLE = "<org.cry.otp.Home: void idle()>"

PATH_METHODS = sorted([ON_CLICK, GEN, GENERATE, HMAC, SAVE])


def _p(signature: str) -> int:
    return PATH_METHODS.index(signature)


STEPS = sorted(
    [
        [0, _p(ON_CLICK), _p(GEN)],
        [0, _p(GEN), _p(GENERATE)],
        [0, _p(GENERATE), _p(HMAC)],
        [1, _p(ON_CLICK), _p(SAVE)],
    ]
)


def _method(signature: str, pairs: list[list[int]] | None = None) -> dict:
    method = {"name": "m", "signature": signature, "reachable": True}
    if pairs is not None:
        method["targetDistances"] = pairs
    return method


def _document(steps: list[list[int]] | None = STEPS) -> dict:
    document = {
        "package": "org.cry.otp",
        "distanceTargets": [
            {"signature": HMAC, "kind": "direct"},
            {"signature": SAVE, "kind": "direct"},
            {"signature": OTHER, "kind": "direct"},
        ],
        "components": [],
        "reachability": [
            {
                "className": "org.cry.otp.Home$1",
                "methods": [
                    _method(ON_CLICK, [[0, 3], [1, 1]]),
                    _method(HMAC, [[0, 0]]),
                    _method(IDLE),
                ],
            }
        ],
    }
    if steps is not None:
        document["pathMethods"] = PATH_METHODS
        document["distancePaths"] = steps
    document["windows"] = []
    document["transitions"] = []
    document["complete"] = True
    return document


def _write(tmp_path: Path, document: dict) -> str:
    path = tmp_path / "cryotp.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return str(path)


def _run_cli(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["rv-static-analysis", "path", *argv])
    return main()


# --- Chains ---


def test_every_pair_prints_its_chain(tmp_path):
    assert query_paths(_write(tmp_path, _document()), ON_CLICK) == [
        f"[0] d=3 {HMAC}",
        f"  {ON_CLICK}",
        f"  {GEN}",
        f"  {GENERATE}",
        f"  {HMAC}",
        f"[1] d=1 {SAVE}",
        f"  {ON_CLICK}",
        f"  {SAVE}",
    ]


def test_target_restricts_the_output_to_its_block(tmp_path):
    assert query_paths(_write(tmp_path, _document()), ON_CLICK, target=1) == [
        f"[1] d=1 {SAVE}",
        f"  {ON_CLICK}",
        f"  {SAVE}",
    ]


def test_a_pair_at_distance_zero_is_the_method_itself(tmp_path):
    assert query_paths(_write(tmp_path, _document()), HMAC) == [
        f"[0] d=0 {HMAC}",
        f"  {HMAC}",
    ]


def test_pairs_before_the_signature_are_still_found(tmp_path):
    document = _document()
    entry = document["reachability"][0]["methods"][0]
    document["reachability"][0]["methods"][0] = {
        "targetDistances": entry["targetDistances"],
        "signature": entry["signature"],
    }
    assert (
        query_paths(_write(tmp_path, document), ON_CLICK, target=1)[0]
        == f"[1] d=1 {SAVE}"
    )


def test_cli_prints_the_chains_and_exits_0(tmp_path, monkeypatch, capsys):
    doc = _write(tmp_path, _document())

    assert _run_cli(monkeypatch, doc, ON_CLICK, "--target", "0") == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        f"[0] d=3 {HMAC}",
        f"  {ON_CLICK}",
        f"  {GEN}",
        f"  {GENERATE}",
        f"  {HMAC}",
    ]
    assert err == ""


def test_a_method_with_no_pair_exits_0_and_prints_nothing(
    tmp_path, monkeypatch, capsys
):
    doc = _write(tmp_path, _document())

    assert _run_cli(monkeypatch, doc, IDLE) == 0
    assert capsys.readouterr() == ("", "")


# --- Refusals ---


def _refused(monkeypatch, capsys, *argv: str) -> str:
    assert _run_cli(monkeypatch, *argv) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    return err


def test_a_document_without_paths_is_refused(tmp_path, monkeypatch, capsys):
    doc = _write(tmp_path, _document(steps=None))

    err = _refused(monkeypatch, capsys, doc, ON_CLICK)
    assert doc in err
    assert "carries no distancePaths" in err


def test_an_unknown_method_is_refused(tmp_path, monkeypatch, capsys):
    doc = _write(tmp_path, _document())
    unknown = "<org.cry.otp.Nowhere: void x()>"

    err = _refused(monkeypatch, capsys, doc, unknown)
    assert doc in err
    assert unknown in err


def test_a_target_without_a_pair_is_refused(tmp_path, monkeypatch, capsys):
    doc = _write(tmp_path, _document())

    err = _refused(monkeypatch, capsys, doc, ON_CLICK, "--target", "2")
    assert doc in err
    assert "target 2" in err


def test_a_missing_step_is_a_broken_chain(tmp_path, monkeypatch, capsys):
    steps = [step for step in STEPS if step != [0, _p(GEN), _p(GENERATE)]]
    doc = _write(tmp_path, _document(steps=steps))

    err = _refused(monkeypatch, capsys, doc, ON_CLICK)
    assert doc in err
    assert "INV-ANA-91" in err
    assert GEN in err


def test_a_chain_ending_away_from_the_target_is_broken(tmp_path):
    document = _document()
    document["reachability"][0]["methods"][0]["targetDistances"] = [[0, 2]]

    with pytest.raises(PathQueryRefused, match="INV-ANA-91"):
        query_paths(_write(tmp_path, document), ON_CLICK)


def test_a_missing_file_exits_1_with_one_line(tmp_path, monkeypatch, capsys):
    _refused(monkeypatch, capsys, str(tmp_path / "absent.json"), ON_CLICK)
