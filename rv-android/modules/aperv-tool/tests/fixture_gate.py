"""Where the two FIXTURE-REAL trees are, and how a test says one is missing.

Neither tree lives in this repository. cmp162 is roughly 40 GB of campaign output
under ``experimento-comp162/``; the baseline sample is copied in, but the corpus it
was drawn from is not. A test that reads either must do one of two things and never
a third: run against the pinned bytes, or **skip with a reason naming what is
absent**. It must never quietly pass because the input was not there — a green suite
that measured nothing is worse than a red one, because it looks like evidence.

This module holds the plain functions; ``conftest.py`` wraps them as pytest fixtures
and puts this directory on ``sys.path`` so every test module can import it by name
under ``--import-mode=importlib``, which the CI contract requires.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES = TESTS_DIR / "fixtures"
CMP162_MANIFEST = FIXTURES / "cmp162_manifest.json"
BASELINE_MANIFEST = FIXTURES / "baseline_sample_manifest.json"
BASELINE_SAMPLE = FIXTURES / "baseline_sample"

# modules/aperv-tool/tests/ -> up three is the rv-android repository root.
REPO_ROOT = TESTS_DIR.parents[2]

#: The single reason string every FIXTURE-REAL skip carries, so a skipped run is
#: greppable and distinguishable from a skip for any other cause.
MISSING_REAL = "FIXTURE-REAL not present"


def sha256_of(path: Path) -> str:
    """Stream a file into a sha256 digest; traces run to hundreds of megabytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict | None:
    """The manifest as a dict, or ``None`` when it has not been generated."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


def campaign_root(manifest: dict) -> Path | None:
    """The cmp162 tree, or ``None``.

    The manifest records the path the pin was taken against, relative to the
    repository root. An absolute value is honoured as-is, so a tree mounted
    elsewhere needs a regenerated manifest rather than an environment variable.
    """
    declared = Path(manifest["campaign_root"])
    root = declared if declared.is_absolute() else REPO_ROOT / declared
    return root if root.is_dir() else None
