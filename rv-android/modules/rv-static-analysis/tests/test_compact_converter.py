"""
Tests for the offline conversion of a full-mode document to the compact form
(``rv_static_analysis.compact``, INV-ANA-85, INV-ANA-87).

Inputs are small synthetic full-mode documents laid out as GATOR writes them:
indented by two spaces, scope members first, then ``distanceTargets``,
``components``, ``reachability``, ``windows``, ``transitions`` and the
``complete`` sentinel. Expected escapes are written out literally from Gson's
``JsonWriter`` table rather than computed with ``json.dumps``, so the test does
not share the implementation's assumption.
"""

import decimal
import json
import os
import sys
from pathlib import Path

import pytest
import rv_static_analysis.compact as compact_module
from rv_static_analysis.__main__ import main
from rv_static_analysis.compact import (
    COMPACT_K,
    COMPACT_WEIGHED_MAX,
    CompactRefused,
    compact_document,
    dumps_gson_compact,
)

FIXTURE = Path(__file__).parent / "resources" / "cryptoapp.apk.json"

SCOPE = {
    "package": "com.example",
    "mainActivity": "com.example.Main",
    "codePackage": "com.example",
    "codePackageSource": "manifest",
    "class_defs_under_key": 2,
}


def _targets(count: int) -> list[dict]:
    return [
        {"signature": f"<com.example.T: void m{i}()>", "kind": "direct"}
        for i in range(count)
    ]


def _method(name: str, pairs: list[list[int]] | None = None) -> dict:
    method = {
        "name": name,
        "signature": f"<com.example.Main: void {name}()>",
        "reachable": True,
        "reachesTarget": pairs is not None,
        "directlyReachesTarget": False,
    }
    if pairs is not None:
        method["targetDistances"] = pairs
    return method


def _full_document(methods: list[dict], targets: int | None = 5, **extra) -> dict:
    document = dict(SCOPE)
    if targets is not None:
        document["distanceTargets"] = _targets(targets)
    document["components"] = []
    document["reachability"] = [
        {
            "className": "com.example.Main",
            "componentType": "activity",
            "isMain": True,
            "methods": methods,
        }
    ]
    document["windows"] = [
        {"id": 1, "name": "com.example.Main", "type": "ACTIVITY", "widgets": []}
    ]
    document["transitions"] = [
        {
            "sourceId": 1,
            "targetId": 1,
            "events": [{"widgetId": 7, "eventType": "click"}],
        }
    ]
    document.update(extra)
    document["complete"] = True
    return document


def _write_full(path: Path, document: dict) -> Path:
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def _convert(tmp_path: Path, document: dict) -> tuple[Path, dict]:
    src = _write_full(tmp_path / "app.apk.json", document)
    dst = tmp_path / "app.compact.json"
    compact_document(str(src), str(dst))
    return dst, json.loads(dst.read_text(encoding="utf-8"))


def _reference_reduce(pairs: list[list[int]]) -> list[list[int]]:
    """INV-ANA-85 written independently: rank by (d, i), keep d <= 3 or rank < 3,
    sort by i."""
    ranked = sorted(pairs, key=lambda p: (p[1], p[0]))
    kept = [
        p
        for rank, p in enumerate(ranked)
        if p[1] <= COMPACT_WEIGHED_MAX or rank < COMPACT_K
    ]
    return sorted(kept, key=lambda p: p[0])


# --- Constants ---


def test_constants_are_the_derive_reduction():
    assert (COMPACT_WEIGHED_MAX, COMPACT_K) == (3, 3)


# --- Member order and marker position ---


def test_marker_goes_right_before_distance_targets(tmp_path):
    _, converted = _convert(tmp_path, _full_document([_method("a", [[0, 1]])]))

    assert list(converted) == [
        "package",
        "mainActivity",
        "codePackage",
        "codePackageSource",
        "class_defs_under_key",
        "distancePairs",
        "distanceTargets",
        "components",
        "reachability",
        "windows",
        "transitions",
        "complete",
    ]
    assert converted["distancePairs"] == {"weighedMax": 3, "k": 3}


def test_marker_goes_right_before_components_without_distance_targets(tmp_path):
    _, converted = _convert(tmp_path, _full_document([_method("a")], targets=None))

    assert list(converted) == [
        "package",
        "mainActivity",
        "codePackage",
        "codePackageSource",
        "class_defs_under_key",
        "distancePairs",
        "components",
        "reachability",
        "windows",
        "transitions",
        "complete",
    ]


def test_marker_goes_last_when_no_later_member_is_present(tmp_path):
    src = tmp_path / "scope_only.json"
    src.write_text(json.dumps(SCOPE, indent=2), encoding="utf-8")
    dst = tmp_path / "out.json"

    compact_document(str(src), str(dst))

    assert list(json.loads(dst.read_text())) == list(SCOPE) + ["distancePairs"]


def test_values_other_than_pairs_are_kept(tmp_path):
    document = _full_document([_method("a", [[0, 1]]), _method("b")])
    _, converted = _convert(tmp_path, document)

    del converted["distancePairs"]
    assert converted == document


# --- Pair reduction (INV-ANA-85) ---


@pytest.mark.parametrize(
    "full, expected",
    [
        # A method far from most targets keeps its three nearest.
        ([[0, 7], [1, 5], [2, 9], [3, 6], [4, 10]], [[0, 7], [1, 5], [3, 6]]),
        # Every pair within three calls is kept.
        ([[0, 1], [1, 3], [2, 2], [3, 3], [4, 8]], [[0, 1], [1, 3], [2, 2], [3, 3]]),
        # Fewer pairs than COMPACT_K are kept whole.
        ([[2, 10]], [[2, 10]]),
    ],
)
def test_pairs_are_reduced_and_sorted_by_target(tmp_path, full, expected):
    _, converted = _convert(tmp_path, _full_document([_method("a", full)]))

    method = converted["reachability"][0]["methods"][0]
    assert method["targetDistances"] == expected


def test_method_without_pairs_stays_without_the_key(tmp_path):
    _, converted = _convert(tmp_path, _full_document([_method("a")]))

    assert "targetDistances" not in converted["reachability"][0]["methods"][0]


def test_fixture_pairs_match_the_reference_reduction(tmp_path):
    dst = tmp_path / "cryptoapp.apk.json"
    compact_document(str(FIXTURE), str(dst))

    full = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for entry in full["reachability"]:
        for method in entry["methods"]:
            if "targetDistances" in method:
                method["targetDistances"] = _reference_reduce(method["targetDistances"])
    converted = json.loads(dst.read_text(encoding="utf-8"))
    del converted["distancePairs"]
    assert converted == full


# --- Serialised form ---


def test_small_document_serialises_exactly(tmp_path):
    src = tmp_path / "small.json"
    src.write_text(
        json.dumps(
            {
                "package": "a b",
                "distanceTargets": [{"signature": "<A: void m()>", "kind": "direct"}],
                "reachability": [
                    {
                        "className": "A",
                        "componentType": None,
                        "isMain": False,
                        "methods": [{"name": "m", "targetDistances": [[0, 1]]}],
                    }
                ],
                "complete": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    dst = tmp_path / "small.compact.json"

    compact_document(str(src), str(dst))

    assert dst.read_bytes() == (
        b'{"package":"a b","distancePairs":{"weighedMax":3,"k":3},'
        b'"distanceTargets":[{"signature":"<A: void m()>","kind":"direct"}],'
        b'"reachability":[{"className":"A","componentType":null,"isMain":false,'
        b'"methods":[{"name":"m","targetDistances":[[0,1]]}]}],"complete":true}'
    )


def test_output_has_no_trailing_newline(tmp_path):
    dst, _ = _convert(tmp_path, _full_document([_method("a", [[0, 1]])]))

    assert dst.read_bytes().endswith(b"}")


@pytest.mark.parametrize(
    "value, expected",
    [
        ('"', r'"\""'),
        ("\\", r'"\\"'),
        ("\t\b\n\r\f", r'"\t\b\n\r\f"'),
        ("\u0001", r'"\u0001"'),
        ("\u001f", r'"\u001f"'),
        ("\u2028", r'"\u2028"'),
        ("\u2029", r'"\u2029"'),
        ("\u007f", '"\u007f"'),
        ("<>&='", '"<>&=\'"'),
        ("é日", '"é日"'),
        ("a\u2028b\u2029c", r'"a\u2028b\u2029c"'),
    ],
)
def test_strings_are_escaped_as_gson_escapes_them(value, expected):
    assert dumps_gson_compact(value) == expected


def test_keys_are_escaped_as_strings():
    assert dumps_gson_compact({'a"\u2028': 1}) == r'{"a\"\u2028":1}'


def test_scalars_serialise_as_gson_writes_them():
    assert dumps_gson_compact({"a": [1, -2, True, False, None, ""]}) == (
        '{"a":[1,-2,true,false,null,""]}'
    )


@pytest.mark.parametrize(
    "value", [1.5, 2.0, decimal.Decimal("1.5"), {"a": [[0, 1.0]]}, (1, 2)]
)
def test_values_gson_does_not_write_are_refused(value):
    with pytest.raises(CompactRefused):
        dumps_gson_compact(value)


# --- Refusals ---


def test_compact_input_is_refused(tmp_path):
    first, _ = _convert(tmp_path, _full_document([_method("a", [[0, 1]])]))
    second = tmp_path / "again.json"

    with pytest.raises(CompactRefused, match="already compact"):
        compact_document(str(first), str(second))
    assert not second.exists()


def test_truncated_input_is_refused_without_output(tmp_path):
    text = json.dumps(_full_document([_method("a", [[0, 1]])]), indent=2)
    src = tmp_path / "cut.json"
    src.write_text(text[: text.index('"transitions"') + 40], encoding="utf-8")
    dst = tmp_path / "out.json"

    with pytest.raises(CompactRefused, match="truncated") as refused:
        compact_document(str(src), str(dst))

    assert str(src) in str(refused.value)
    assert sorted(os.listdir(tmp_path)) == ["cut.json"]


def test_same_file_is_refused_and_input_untouched(tmp_path):
    src = _write_full(tmp_path / "a.json", _full_document([_method("a", [[0, 1]])]))
    before = src.read_bytes()

    with pytest.raises(CompactRefused, match="input file itself"):
        compact_document(str(src), str(src))
    with pytest.raises(CompactRefused, match="input file itself"):
        compact_document(str(src), str(tmp_path / "." / "a.json"))

    assert src.read_bytes() == before
    assert sorted(os.listdir(tmp_path)) == ["a.json"]


def test_non_integer_number_is_refused_without_output(tmp_path):
    document = _full_document([_method("a", [[0, 1]])])
    document["windows"][0]["scale"] = 1.5
    src = _write_full(tmp_path / "f.json", document)
    dst = tmp_path / "out.json"

    with pytest.raises(CompactRefused, match="1.5") as refused:
        compact_document(str(src), str(dst))

    assert str(src) in str(refused.value)
    assert sorted(os.listdir(tmp_path)) == ["f.json"]


def test_failed_write_removes_the_temporary_file(tmp_path, monkeypatch):
    src = _write_full(tmp_path / "a.json", _full_document([_method("a", [[0, 1]])]))
    dst = tmp_path / "out.json"
    dst.write_text("previous", encoding="utf-8")

    def failing_replace(source, target):
        raise OSError("rename failed")

    monkeypatch.setattr(compact_module.os, "replace", failing_replace)
    with pytest.raises(OSError, match="rename failed"):
        compact_document(str(src), str(dst))

    assert dst.read_text(encoding="utf-8") == "previous"
    assert sorted(os.listdir(tmp_path)) == ["a.json", "out.json"]


def test_existing_output_is_replaced(tmp_path):
    src = _write_full(tmp_path / "a.json", _full_document([_method("a", [[0, 1]])]))
    dst = tmp_path / "out.json"
    dst.write_text("previous", encoding="utf-8")

    compact_document(str(src), str(dst))

    assert json.loads(dst.read_text(encoding="utf-8"))["distancePairs"] == {
        "weighedMax": 3,
        "k": 3,
    }
    assert sorted(os.listdir(tmp_path)) == ["a.json", "out.json"]


# --- CLI ---


def _run_cli(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["rv-static-analysis", *argv])
    return main()


def test_cli_exits_0_on_success(tmp_path, monkeypatch, capsys):
    src = _write_full(tmp_path / "a.json", _full_document([_method("a", [[0, 1]])]))
    dst = tmp_path / "out.json"

    assert _run_cli(monkeypatch, "compact", str(src), str(dst)) == 0
    assert capsys.readouterr().err == ""
    assert dst.is_file()


def test_cli_exits_1_with_one_line_on_refusal(tmp_path, monkeypatch, capsys):
    src = _write_full(tmp_path / "a.json", _full_document([_method("a", [[0, 1]])]))

    assert _run_cli(monkeypatch, "compact", str(src), str(src)) == 1
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert str(src) in err


def test_cli_exits_1_with_one_line_on_non_json_input(tmp_path, monkeypatch, capsys):
    src = tmp_path / "bad.json"
    src.write_text("not json at all\n", encoding="utf-8")
    dst = tmp_path / "out.json"

    assert _run_cli(monkeypatch, "compact", str(src), str(dst)) == 1
    assert capsys.readouterr().err.count("\n") == 1
    assert not dst.exists()


def test_cli_exits_1_on_missing_input(tmp_path, monkeypatch, capsys):
    assert (
        _run_cli(
            monkeypatch,
            "compact",
            str(tmp_path / "absent.json"),
            str(tmp_path / "o.json"),
        )
        == 1
    )
    assert capsys.readouterr().err.count("\n") == 1


def test_cli_exits_2_on_usage_error(monkeypatch):
    with pytest.raises(SystemExit) as exited:
        _run_cli(monkeypatch, "compact", "only-one-path")
    assert exited.value.code == 2
