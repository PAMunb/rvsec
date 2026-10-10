"""Tests for the streaming reader of the static-analysis document (gh123).

The reference for every assertion is ``json.loads`` of the same bytes: the reader
must build what it builds, minus the members the caller drops (INV-ANA-80), and a
reduced ``targetDistances`` must hold exactly the pairs the MOP derivation can emit
(INV-APV-64).
"""

import hashlib
import json
import random
from pathlib import Path

import pytest

from rv_android_core.util.analysis_document import (
    PairPolicy,
    digest_of_file,
    read_analysis_document,
)

# The fixtures belong to rv-static-analysis; they are read in place, not copied.
_RESOURCES = Path(__file__).resolve().parents[3] / "rv-static-analysis" / "tests" / "resources"
FIXTURES = [
    _RESOURCES / "cryptoapp.apk.json",
    _RESOURCES / "app.notesr_59.apk.json",
]


# === REFERENCES BUILT FROM json.loads ===


def _without_distances(document: dict) -> dict:
    """The document as `PairPolicy.DROP` must return it."""
    document = json.loads(json.dumps(document))
    document.pop("distanceTargets", None)
    for entry in document.get("reachability") or []:
        if not isinstance(entry, dict):
            continue
        for method in entry.get("methods") or []:
            if isinstance(method, dict):
                method.pop("targetDistances", None)
    return document


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _reference_minima(raw, targets: int | None) -> dict[int, int]:
    """Per-target minima as the derivation's `_read_pairs` reads them."""
    minima: dict[int, int] = {}
    if not isinstance(raw, list):
        return minima
    for entry in raw:
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        index, distance = entry
        if not (_is_int(index) and _is_int(distance)):
            continue
        if index < 0 or distance < 0 or (targets is not None and index >= targets):
            continue
        minima[index] = min(minima.get(index, distance), distance)
    return minima


def _reference_reduced(raw, targets: int | None, weighed_max: int, k: int) -> list:
    ordered = sorted((d, i) for i, d in _reference_minima(raw, targets).items())
    if targets is None:
        return [[i, d] for d, i in ordered]
    return [[i, d] for rank, (d, i) in enumerate(ordered) if d <= weighed_max or rank < k]


def _with_reduced_distances(document: dict, weighed_max: int, k: int) -> dict:
    document = json.loads(json.dumps(document))
    distance_targets = document.get("distanceTargets")
    targets = len(distance_targets) if isinstance(distance_targets, list) else 0
    for entry in document.get("reachability") or []:
        if not isinstance(entry, dict):
            continue
        for method in entry.get("methods") or []:
            if isinstance(method, dict) and "targetDistances" in method:
                method["targetDistances"] = _reference_reduced(
                    method["targetDistances"], targets, weighed_max, k
                )
    return document


def _write(tmp_path: Path, text: str | bytes, name: str = "doc.apk.json") -> str:
    path = tmp_path / name
    if isinstance(text, str):
        text = text.encode("utf-8")
    path.write_bytes(text)
    return str(path)


# === EQUIVALENCE WITH json.loads ===


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_equals_json_loads_without_distances(fixture):
    expected = _without_distances(json.loads(fixture.read_bytes()))

    document, truncated = read_analysis_document(str(fixture), PairPolicy.DROP)

    assert truncated is False
    assert document == expected
    assert list(document) == list(expected)


def test_drop_omits_both_distance_members():
    document, _ = read_analysis_document(str(FIXTURES[0]), PairPolicy.DROP)

    assert "distanceTargets" not in document
    methods = [m for entry in document["reachability"] for m in entry["methods"]]
    assert methods
    assert all("targetDistances" not in method for method in methods)


def test_cryptoapp_fixture_carries_the_distances_the_drop_removes():
    """Guard: the drop test above is vacuous on a document without distances."""
    raw = json.loads(FIXTURES[0].read_bytes())
    carriers = [
        m for e in raw["reachability"] for m in e["methods"] if "targetDistances" in m
    ]
    assert raw["distanceTargets"]
    assert len(carriers) == 38


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_reduce_equals_reference_on_fixtures(fixture):
    expected = _with_reduced_distances(json.loads(fixture.read_bytes()), 3, 3)

    document, truncated = read_analysis_document(str(fixture), PairPolicy.reduce(3, 3))

    assert truncated is False
    assert document == expected


def test_numbers_strings_and_literals_keep_their_json_loads_types(tmp_path):
    text = (
        '{"i": 7, "f": 2.5, "e": 1e3, "neg": -0.0, "big": 12345678901234,'
        ' "s": "caf\\u00e9 \\ud83d\\ude00", "t": true, "n": null,'
        ' "nested": {"a": [1, 2.0, [], {}], "b": {"c": null}}, "empty": {}}'
    )
    path = _write(tmp_path, text)

    document, truncated = read_analysis_document(path, PairPolicy.DROP)

    assert truncated is False
    expected = json.loads(text)
    assert document == expected
    for key in ("i", "big"):
        assert type(document[key]) is int
    for key in ("f", "e", "neg"):
        assert type(document[key]) is float
    assert type(document["nested"]["a"][1]) is float


def test_duplicate_keys_keep_the_last_value_as_json_loads(tmp_path):
    text = '{"a": 1, "b": 2, "a": 3}'
    document, _ = read_analysis_document(_write(tmp_path, text), PairPolicy.DROP)
    assert document == json.loads(text)
    assert list(document) == list(json.loads(text))


# === PAIR REDUCTION ===


def _random_entry(rng: random.Random, targets: int):
    roll = rng.random()
    if roll < 0.80:
        return [rng.randrange(targets + 2), rng.randrange(11)]
    noise = [
        [rng.randrange(targets + 1), -1],
        [-1, 2],
        [True, 1],
        [1, False],
        [1.0, 2],
        [1, 2.0],
        [1, 2, 3],
        [1],
        "x",
        None,
        {"i": 1},
        [[1], 2],
    ]
    return rng.choice(noise)


def _random_document(rng: random.Random, targets_first: bool = True) -> dict:
    targets = rng.randrange(0, 9)
    reachability = []
    for c in range(rng.randrange(1, 5)):
        methods = []
        for m in range(rng.randrange(0, 6)):
            method = {"name": f"m{m}", "signature": f"<C{c}: void m{m}()>"}
            shape = rng.random()
            if shape < 0.85:
                method["targetDistances"] = [
                    _random_entry(rng, targets) for _ in range(rng.randrange(0, 14))
                ]
            elif shape < 0.92:
                method["targetDistances"] = rng.choice([None, "x", {"a": [1, 2]}, 3])
            methods.append(method)
        reachability.append({"className": f"C{c}", "methods": methods})
    distance_targets = [{"kind": "direct", "i": i} for i in range(targets)]
    if targets_first:
        return {
            "package": "p",
            "distanceTargets": distance_targets,
            "reachability": reachability,
            "complete": True,
        }
    return {
        "package": "p",
        "reachability": reachability,
        "distanceTargets": distance_targets,
        "complete": True,
    }


@pytest.mark.parametrize("seed", range(40))
def test_reduce_keeps_weighed_pairs_and_the_k_nearest(tmp_path, seed):
    rng = random.Random(seed)
    raw = _random_document(rng)
    weighed_max, k = rng.choice([(3, 3), (0, 1), (2, 5), (10, 0)])
    path = _write(tmp_path, json.dumps(raw))

    document, truncated = read_analysis_document(path, PairPolicy.reduce(weighed_max, k))

    assert truncated is False
    assert document == _with_reduced_distances(raw, weighed_max, k)


def test_reduce_orders_pairs_by_distance_then_index(tmp_path):
    raw = {
        "distanceTargets": [{}] * 6,
        "reachability": [
            {"methods": [{"targetDistances": [[5, 9], [4, 2], [1, 2], [0, 7], [1, 1], [3, 8]]}]}
        ],
    }
    document, _ = read_analysis_document(
        _write(tmp_path, json.dumps(raw)), PairPolicy.reduce(3, 3)
    )
    # [1, 1] beats [1, 2] (per-target minimum); then (2, 4); the third nearest is
    # (7, 0) though beyond d = 3; (8, 3) and (9, 5) are dropped.
    assert document["reachability"][0]["methods"][0]["targetDistances"] == [
        [1, 1],
        [4, 2],
        [0, 7],
    ]


def test_reduce_without_a_preceding_target_list_keeps_every_valid_minimum(tmp_path):
    """The bound on `i` is unknown until `distanceTargets` is read; nothing is cut."""
    rng = random.Random(7)
    raw = _random_document(rng, targets_first=False)
    targets = len(raw["distanceTargets"])
    document, _ = read_analysis_document(
        _write(tmp_path, json.dumps(raw)), PairPolicy.reduce(3, 3)
    )
    for got_entry, raw_entry in zip(document["reachability"], raw["reachability"]):
        for got, method in zip(got_entry["methods"], raw_entry["methods"]):
            if "targetDistances" not in method:
                assert "targetDistances" not in got
                continue
            assert got["targetDistances"] == _reference_reduced(
                method["targetDistances"], None, 3, 3
            )
            # Every pair the derivation would keep under the real bound is present.
            kept = {tuple(p) for p in got["targetDistances"]}
            for pair in _reference_reduced(method["targetDistances"], targets, 3, 3):
                assert tuple(pair) in kept


def test_reduce_builds_the_target_list(tmp_path):
    document, _ = read_analysis_document(str(FIXTURES[0]), PairPolicy.reduce(3, 3))
    assert document["distanceTargets"] == json.loads(FIXTURES[0].read_bytes())["distanceTargets"]


def test_distance_members_outside_their_place_are_ordinary_members(tmp_path):
    raw = {
        "windows": [{"targetDistances": [[0, 1]], "distanceTargets": [1]}],
        "reachability": [{"targetDistances": [[0, 9]], "methods": []}],
    }
    document, _ = read_analysis_document(_write(tmp_path, json.dumps(raw)), PairPolicy.DROP)
    assert document == raw


# === TRUNCATION ===


def _members_with_offsets(document: dict) -> tuple[str, list[tuple[str, int, int]]]:
    """Serialize member by member, recording where each value starts and ends."""
    text = "{"
    spans = []
    for position, (key, value) in enumerate(document.items()):
        if position:
            text += ", "
        text += json.dumps(key) + ": "
        start = len(text)
        text += json.dumps(value)
        spans.append((key, start, len(text)))
    return text + "}", spans


def _fixture_document() -> dict:
    return json.loads(FIXTURES[0].read_bytes())


def test_truncation_at_each_top_level_boundary_keeps_the_members_before_it(tmp_path):
    raw = _fixture_document()
    text, spans = _members_with_offsets(raw)
    expected_full = _without_distances(raw)

    def complete_at(key: str, stop: int, cut: int) -> bool:
        # A number at the very end of the input may continue past it, so only a
        # following byte completes it; every other value carries its own end.
        if isinstance(raw[key], (int, float)) and not isinstance(raw[key], bool):
            return stop < cut
        return stop <= cut

    for count, (_, _, end) in enumerate(spans, start=1):
        for cut in (end, end + 1):  # right after the value, and after the comma
            if cut >= len(text):
                continue
            path = _write(tmp_path, text[:cut])
            document, truncated = read_analysis_document(path, PairPolicy.DROP)
            assert truncated is True
            kept = [key for key, _, stop in spans[:count] if complete_at(key, stop, cut)]
            assert list(document) == [k for k in kept if k != "distanceTargets"]
            for key in document:
                assert document[key] == expected_full[key]


def test_truncation_inside_a_nested_array_drops_the_member_in_progress(tmp_path):
    raw = _fixture_document()
    text, spans = _members_with_offsets(raw)
    expected_full = _without_distances(raw)

    for position, (key, start, end) in enumerate(spans):
        if not isinstance(raw[key], (list, dict)) or end - start < 4:
            continue
        cut = start + (end - start) // 2
        document, truncated = read_analysis_document(_write(tmp_path, text[:cut]), PairPolicy.DROP)
        assert truncated is True
        expected_keys = [k for k, _, _ in spans[:position] if k != "distanceTargets"]
        assert list(document) == expected_keys
        for kept in document:
            assert document[kept] == expected_full[kept]


def test_truncation_inside_a_top_level_number_drops_it(tmp_path):
    """yajl emits a number cut by the end of input; the reader must not keep it."""
    document, truncated = read_analysis_document(
        _write(tmp_path, '{"package": "p", "class_defs_under_key": 12'), PairPolicy.DROP
    )
    assert truncated is True
    assert document == {"package": "p"}


def test_truncation_after_a_number_and_its_comma_keeps_it(tmp_path):
    document, truncated = read_analysis_document(
        _write(tmp_path, '{"package": "p", "class_defs_under_key": 12, "rea'), PairPolicy.DROP
    )
    assert truncated is True
    assert document == {"package": "p", "class_defs_under_key": 12}


def test_truncation_inside_target_distances_under_reduce(tmp_path):
    raw = {
        "distanceTargets": [{}, {}],
        "reachability": [{"methods": [{"targetDistances": [[0, 1], [1, 2]]}]}],
    }
    text = json.dumps(raw)
    cut = text.index("[1, 2]") + 3
    document, truncated = read_analysis_document(
        _write(tmp_path, text[:cut]), PairPolicy.reduce(3, 3)
    )
    assert truncated is True
    assert document == {"distanceTargets": [{}, {}]}


def test_root_opened_and_nothing_complete_is_an_empty_truncated_document(tmp_path):
    document, truncated = read_analysis_document(
        _write(tmp_path, '{"reachability": [{"className": "A"'), PairPolicy.DROP
    )
    assert truncated is True
    assert document == {}


def test_bytes_after_the_root_object_are_not_read(tmp_path):
    document, truncated = read_analysis_document(
        _write(tmp_path, '{"a": 1}\n'), PairPolicy.DROP
    )
    assert (document, truncated) == ({"a": 1}, False)


# === ERRORS ===


@pytest.mark.parametrize("text", ["", "   ", "[1, 2]", '"x"', "3", "null", "not json"])
def test_non_object_root_and_empty_file_raise_value_error(tmp_path, text):
    with pytest.raises(ValueError):
        read_analysis_document(_write(tmp_path, text), PairPolicy.DROP)


def test_missing_file_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        read_analysis_document(str(tmp_path / "absent.json"), PairPolicy.DROP)


# === POLICY ===


def test_pair_policy_values():
    assert PairPolicy.DROP.drop is True
    reduced = PairPolicy.reduce(3, 3)
    assert (reduced.drop, reduced.weighed_max, reduced.k) == (False, 3, 3)


# === DIGEST ===


def test_digest_of_file_is_the_sha256_of_the_bytes(tmp_path):
    payload = b"\x00\xff" * 300_000
    path = _write(tmp_path, payload, "blob.bin")
    assert digest_of_file(path) == "sha256:" + hashlib.sha256(payload).hexdigest()
