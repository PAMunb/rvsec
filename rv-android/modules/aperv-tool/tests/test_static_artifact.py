"""The static artefact yields the size covariate, and never the derived one.

Three properties are under test. The **covariate** — the count of methods from
which a monitored operation is reachable — must come out for every application of
the pinned campaign, offline, with no device. The **handler verdict** must stay
three-way: an unresolved handler is not a cold one, and folding the two was
measured to move the answer by a third of all handlers. And the reader must
**never open a `*.mop.json`** (INV-CAN-24), which is checked by wrapping `open`
rather than by reading the source, because the interesting failure is a path
composed at run time.

The census parity test is a **parity** test (INV-CAN-21): reproducing the
campaign's own file proves this reader reads the same bytes the campaign read, not
that any number is right. Its scope is stated in the test — the census's derived
columns come from the artefact-derivation code on the collection path, which the
analysis layer deliberately does not import.
"""

from __future__ import annotations

import builtins
import csv
import io
import json
from pathlib import Path

import pytest
from fixture_gate import MISSING_REAL

from aperv_tool.analysis import static_artifact
from aperv_tool.analysis.static_artifact import MopArtifactRefused

CENSUS = "censo_substrato.csv"

# Two methods, one of which reaches a monitored operation, and three widget
# handlers: one reaching, one not, one the reachability index never heard of.
DOCUMENT = {
    "package": "com.example",
    "mainActivity": "com.example.Main",
    "components": {
        "activities": [
            {
                "className": "com.example.Main",
                "exported": True,
                "reachesTarget": True,
                "targetMethods": [
                    "<com.example.Main: void onCreate(android.os.Bundle)>"
                ],
            },
            {
                "className": "com.example.Other",
                "exported": False,
                "reachesTarget": False,
            },
        ],
        "receivers": [],
        "services": [],
        "providers": [],
    },
    "reachability": [
        {
            "className": "com.example.Main",
            "methods": [
                {
                    "signature": "<com.example.Main: void hot(android.view.View)>",
                    "reachable": True,
                    "reachesTarget": True,
                    "directlyReachesTarget": True,
                },
                {
                    "signature": "<com.example.Main: void cold(android.view.View)>",
                    "reachable": True,
                    "reachesTarget": False,
                    "directlyReachesTarget": False,
                },
            ],
        }
    ],
    "windows": [
        {
            "id": 1,
            "name": "com.example.Main",
            "type": "ACTIVITY",
            "widgets": [
                {
                    "listeners": [
                        {"handler": "<com.example.Main: void hot(android.view.View)>"},
                        {"handler": "<com.example.Main: void cold(android.view.View)>"},
                        {"handler": "<com.example.Gone: void away(android.view.View)>"},
                    ]
                }
            ],
        }
    ],
    "transitions": [],
    "complete": True,
}


def _write(directory: Path, name: str, document: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(document))
    return path


def test_size_covariate_counts_reaching_methods(tmp_path: Path) -> None:
    """The covariate is the count of methods that reach a monitored operation."""
    facts = static_artifact.read(_write(tmp_path, "app.apk.json", DOCUMENT))

    assert facts.apk == "app.apk"
    assert facts.sa_methods == 2
    assert facts.sa_methods_reaches_mop == 1
    assert facts.sa_methods_directly_reaches_mop == 1
    assert facts.activities == 2
    assert facts.activities_reaching == 1
    assert facts.entry_points == {"onCreate": 1}
    assert facts.stratum == "discriminative"


def test_unresolved_first_class(tmp_path: Path) -> None:
    """A handler with no reachability entry is its own verdict, never a cold one."""
    facts = static_artifact.read(_write(tmp_path, "app.apk.json", DOCUMENT))

    assert facts.handlers.distinct == 3
    assert facts.handlers.hot == 1
    assert facts.handlers.cold == 1
    assert facts.handlers.unresolved == 1
    # The three partition the distinct handlers: nothing is counted twice and
    # nothing is absorbed into a neighbouring verdict.
    assert (
        facts.handlers.hot + facts.handlers.cold + facts.handlers.unresolved
        == facts.handlers.distinct
    )


def test_complete_is_carried_and_never_a_quality_signal(tmp_path: Path) -> None:
    """A truncated artefact still declares itself complete; both facts survive."""
    truncated = dict(DOCUMENT, transitions=[], complete=True)
    facts = static_artifact.read(_write(tmp_path, "app.apk.json", truncated))

    assert facts.complete is True
    assert facts.transitions == 0


def test_strata_cover_the_degenerate_ends(tmp_path: Path) -> None:
    """No activity, no reachable activity and a saturated one are distinct labels."""
    empty = dict(DOCUMENT, components={"activities": []})
    inert = dict(
        DOCUMENT,
        components={
            "activities": [{"className": "com.example.A", "reachesTarget": False}]
        },
    )
    saturated = dict(
        DOCUMENT,
        components={
            "activities": [{"className": "com.example.A", "reachesTarget": True}]
        },
    )

    assert static_artifact.read(_write(tmp_path, "a.apk.json", empty)).stratum == (
        "no_activities"
    )
    assert (
        static_artifact.read(_write(tmp_path, "b.apk.json", inert)).stratum == "inert"
    )
    assert (
        static_artifact.read(_write(tmp_path, "c.apk.json", saturated)).stratum
        == "saturated"
    )


def test_mop_json_never_opened(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrapping `open`, no derived artefact is read (INV-CAN-24).

    Both `builtins.open` and `io.open` are wrapped: `Path.read_text` reaches the
    filesystem through the latter, so a test that patched only the former would
    record nothing and pass while proving nothing.
    """
    _write(tmp_path, "app.apk.json", DOCUMENT)
    _write(tmp_path, "app.apk.mop.json", {"mopActivities": []})

    opened: list[str] = []
    real_open = builtins.open

    def recording_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recording_open)
    monkeypatch.setattr(io, "open", recording_open)

    facts, skips = static_artifact.read_tree(tmp_path)

    assert [item.apk for item in facts] == ["app.apk"]
    assert skips.mop_artefacts == 1
    assert skips.unrecognised == 0
    assert opened, "the wrapper recorded nothing — it is not intercepting the reads"
    assert any(path.endswith("app.apk.json") for path in opened)
    assert not [path for path in opened if path.endswith(".mop.json")]

    with pytest.raises(MopArtifactRefused):
        static_artifact.read(tmp_path / "app.apk.mop.json")


def test_signatures_join_by_exact_equality(tmp_path: Path) -> None:
    """The join key is the signature verbatim, with the reaching subset available."""
    path = _write(tmp_path, "app.apk.json", DOCUMENT)

    every = static_artifact.signatures(path)
    reaching = static_artifact.signatures(path, reaching_only=True)

    assert every == {
        "<com.example.Main: void hot(android.view.View)>",
        "<com.example.Main: void cold(android.view.View)>",
    }
    assert reaching == {"<com.example.Main: void hot(android.view.View)>"}


def test_covariate_162(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """Every application of the pinned campaign yields the covariate, with no device."""
    expected = cmp162_manifest["artefact_counts"]["static_json"]
    artefacts = [
        cmp162_root / name
        for name in sorted(cmp162_manifest["files"])
        if name.endswith(".apk.json") and not name.endswith(".mop.json")
    ]
    if len(artefacts) != expected:
        pytest.skip(f"{MISSING_REAL}: {len(artefacts)} static artefacts pinned")

    facts = [static_artifact.read(path) for path in artefacts]
    frame = static_artifact.frame(facts)

    assert len(frame) == expected
    assert frame["sa_methods_reaches_mop"].notna().all()
    assert (frame["sa_methods_reaches_mop"] >= 0).all()
    assert frame["sa_methods_reaches_mop"].sum() > 0
    assert set(frame["stratum"]) <= set(static_artifact.STRATA)
    # `unresolved` is not a theoretical state on this corpus: it is populated,
    # which is why it may not be folded into `cold`.
    assert frame["handlers_unresolved"].sum() > 0


def test_parity_censo_substrato(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """PARITY (INV-CAN-21): the reader reads what the campaign's census read.

    Scope: the census file's two artefact-level columns, `transitions` and
    `complete`, plus its membership and its 163 lines. Its other nine columns are
    produced by the collection path's artefact derivation — the click-only graph
    the jar consumes — which the analysis layer does not import, by design. This
    test therefore proves agreement over what this reader owns, and says so rather
    than claiming the whole file.
    """
    census = cmp162_root / CENSUS
    if not census.is_file():
        pytest.skip(f"{MISSING_REAL}: {CENSUS}")

    lines = census.read_text().splitlines()
    assert len(lines) == 163

    rows = list(csv.DictReader(census.read_text().splitlines()))
    artefacts = {
        Path(name).name[: -len(".json")]: cmp162_root / name
        for name in cmp162_manifest["files"]
        if name.endswith(".apk.json") and not name.endswith(".mop.json")
    }

    assert {row["apk"] for row in rows} == set(artefacts)

    divergences = []
    for row in rows:
        facts = static_artifact.read(artefacts[row["apk"]])
        if facts.transitions != int(row["transitions"]):
            divergences.append((row["apk"], "transitions", facts.transitions))
        if facts.complete != (row["complete"] == "True"):
            divergences.append((row["apk"], "complete", facts.complete))

    assert divergences == []
