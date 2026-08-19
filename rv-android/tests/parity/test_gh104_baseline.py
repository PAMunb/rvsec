"""The gh104 E0 baseline must be reproducible, and it must not run on undefined knobs.

Two tests, and both of them are parity tests over FIXTURE-REAL: they read the recorded
comp162 campaign, which is roughly 40 GB and lives outside this repository, pinned file by
file with a sha256 in `modules/aperv-tool/tests/fixtures/cmp162_manifest.json`.

A test that reads that tree does one of exactly two things and never a third: it runs
against the pinned bytes, or it skips with a reason naming what is absent. What it must
never do is quietly pass because the input was not there - a green suite that measured
nothing is worse than a red one, because it looks like evidence
(`docs/20260815_gh103_analysis_layer.md:88-100`).

The third case is the one this file is careful about: the tree is **present** and disagrees
with the pin. That is not an absent input, it is a changed one, and the numbers in
`data/gh104/baseline.md` were computed against the pinned bytes. So it fails.

Parity is not correctness. These tests prove the baseline script still produces the same
artefact from the same bytes. They prove nothing about whether the quantities it measures
are the right ones - that argument lives in `data/gh104/definitions.md`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gh104_baseline as baseline  # noqa: E402

COMP162_RESULTS = baseline.COMP162_RESULTS
MANIFEST = baseline.CMP162_MANIFEST

MISSING_COMP162 = (
    "comp162 results absent: experimento-comp162/results/; "
    "regenerate or restore the campaign"
)
MISSING_ARTICLE = (
    "article dataset absent: ase-journal/dataset/results/errors.csv; "
    "restore the sibling ase-journal checkout"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_pinned_inputs() -> None:
    """Skip when the inputs are absent; fail when they are present and off the pin.

    This is a helper called from the test body rather than a fixture, so that the
    present-but-changed case is reported as a test *failure*. A fixture raising the same
    assertion is reported as a collection error, which reads like a broken harness rather
    than like the finding it is.

    The manifest holds 465 entries for the whole campaign. Verifying all of them would
    hash ~40 GB on every run, so this checks the eight the baseline actually reads - by
    content - plus the two structural facts of the manifest itself (465 entries, 8 of them
    `errors.csv`), which is what would catch a manifest rebuilt against a different tree.
    """
    if not COMP162_RESULTS.is_dir():
        pytest.skip(MISSING_COMP162)
    shards = sorted(COMP162_RESULTS.glob(baseline.COMP162_GLOB))
    if not shards:
        pytest.skip(MISSING_COMP162)
    if not baseline.ARTICLE_ERRORS_CSV.is_file():
        pytest.skip(MISSING_ARTICLE)

    assert MANIFEST.is_file(), f"the comp162 pin is missing: {MANIFEST}"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = manifest["files"]
    pinned = {k: v for k, v in files.items() if k.endswith("errors.csv")}

    assert len(files) == 465, (
        f"cmp162_manifest.json holds {len(files)} entries, the pin is 465; "
        "the manifest was rebuilt against a different tree"
    )
    assert len(pinned) == 8, (
        f"cmp162_manifest.json pins {len(pinned)} errors.csv files, the campaign has 8"
    )
    assert len(shards) == 8, (
        f"{len(shards)} shards on disk under {COMP162_RESULTS}, the campaign has 8"
    )

    for key, expected in sorted(pinned.items()):
        path = COMP162_RESULTS.parent / key
        assert path.is_file(), f"pinned shard missing from a present tree: {path}"
        actual = _sha256(path)
        assert actual == expected, (
            f"{key} disagrees with cmp162_manifest.json: sha256 {actual} on disk, "
            f"{expected} pinned. The baseline in data/gh104/ was measured on the pinned "
            "bytes; re-pin deliberately or restore the campaign."
        )


def test_baseline_reproduces_byte_identical(tmp_path: Path) -> None:
    """Two runs over the same bytes produce the same `baseline.json`, byte for byte.

    A baseline that moves between runs cannot be cited, so this pins the whole artefact
    rather than a chosen number out of it: no timestamp, no set iteration order, no
    host-dependent path may reach the file.
    """
    require_pinned_inputs()

    first = tmp_path / "first"
    second = tmp_path / "second"
    baseline.write_baseline(first)
    baseline.write_baseline(second)

    a = (first / "baseline.json").read_bytes()
    b = (second / "baseline.json").read_bytes()
    assert a == b, "baseline.json is not reproducible between two runs on the same inputs"

    published = ROOT / "data" / "gh104" / "baseline.json"
    assert published.read_bytes() == a, (
        "data/gh104/baseline.json is stale: re-run `python3 scripts/gh104_baseline.py`"
    )

    # Every number the artefact publishes carries its envelope, and every one that the E0
    # brief predicted reproduces. A disagreement is allowed to exist - the data wins - but
    # it must be visible, so it is asserted here rather than discovered later.
    measured = json.loads(a)
    assert not baseline.disagreements(measured), (
        "measured values disagree with the E0 brief: "
        + "; ".join(
            f"{p}: measured {e['numerator']} expected {e['expected']}"
            for p, e in baseline.disagreements(measured)
        )
    )


def test_freeze_items_required() -> None:
    """Removing any one definition raises `FreezeItemUnset`, naming what is missing.

    The failure this prevents is a knob acquiring a default. Each of these decides a
    number - the site tuple alone is the difference between 296 sites and a count that
    merges every call in a method - so a run without one must stop, not proceed with
    something plausible.
    """
    require_pinned_inputs()
    assert baseline.FREEZE_ITEMS, "the freeze-item registry is empty"

    for item_id in sorted(baseline.FREEZE_ITEMS):
        reduced = baseline.DEFAULT_FREEZE.without(item_id)
        with pytest.raises(baseline.FreezeItemUnset) as excinfo:
            baseline.build_baseline(reduced)
        assert excinfo.value.item_id == item_id
        assert item_id in str(excinfo.value)
