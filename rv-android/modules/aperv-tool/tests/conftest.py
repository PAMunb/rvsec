"""Fixture gating for the two FIXTURE-REAL trees.

The contract and the reasoning live in ``fixture_gate.py``; this file turns them
into pytest fixtures and puts the tests directory on ``sys.path`` first. That
insertion is load-bearing: the CI contract runs pytest with
``--import-mode=importlib``, under which a sibling module is not importable by name
unless its directory is on the path, and every test module in this suite imports
``fixture_gate`` to reach the manifests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixture_gate import (  # noqa: E402  (import follows the sys.path insertion)
    BASELINE_MANIFEST,
    CMP162_MANIFEST,
    MISSING_REAL,
    campaign_root,
    load_manifest,
)


@pytest.fixture(scope="session")
def cmp162_manifest() -> dict:
    """The pinned description of cmp162. Skips when the manifest was never generated."""
    manifest = load_manifest(CMP162_MANIFEST)
    if manifest is None:
        pytest.skip(f"{MISSING_REAL}: {CMP162_MANIFEST} not generated")
    return manifest


@pytest.fixture(scope="session")
def cmp162_root(cmp162_manifest: dict) -> Path:
    """The campaign tree, or a skip naming the path that is missing."""
    root = campaign_root(cmp162_manifest)
    if root is None:
        pytest.skip(
            f"{MISSING_REAL}: campaign tree {cmp162_manifest['campaign_root']} not found"
        )
    return root


@pytest.fixture(scope="session")
def cmp162_facts(cmp162_manifest: dict) -> dict:
    """The measured identity arithmetic: 1458 identities, 1455 completed, 3 dead."""
    return cmp162_manifest["facts"]


@pytest.fixture(scope="session")
def baseline_sample_manifest() -> dict:
    """The pinned description of the twelve baseline runs."""
    manifest = load_manifest(BASELINE_MANIFEST)
    if manifest is None:
        pytest.skip(f"{MISSING_REAL}: {BASELINE_MANIFEST} not generated")
    return manifest


@pytest.fixture(scope="session")
def baseline_sample_dir(baseline_sample_manifest: dict) -> Path:
    """The copied baseline runs. These are versioned, so absence is a real defect."""
    directory = CMP162_MANIFEST.parent / baseline_sample_manifest["directory"]
    if not directory.is_dir():
        pytest.skip(f"{MISSING_REAL}: {directory} not populated")
    return directory
