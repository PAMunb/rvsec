"""Test bootstrap for the calibration scaffold.

Puts `experimento-cal/scripts/` on `sys.path` so the state scripts import as top-level
modules (they are CLIs, not an installed package), and exposes shared fixture builders for
a synthetic results tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def subset_file(tmp_path):
    """A fixture subset of 4 real-looking APK identifiers (absolute path so the generator
    resolves it directly, bypassing the not-yet-existing calibracao/subset40.txt)."""
    p = tmp_path / "subset_fixture.txt"
    p.write_text("app.alpha_1\napp.bravo_2\napp.charlie_3\napp.delta_4\n")
    return p


@pytest.fixture
def phase_config(tmp_path, subset_file):
    """A minimal 3-arm phase config (ANC1 + ANC2 + cal_a1) over the fixture subset, 2
    containers, so tests exercise rotation/partition without the full 11-arm cost."""
    cfg = {
        "phase": "calfix",
        "description": "fixture phase",
        "image": {"tag": "phtcosta/rvandroid:0.9.3", "id": "87744cd58be9"},
        "expected_server_model": "Qwen/Qwen3-VL-4B-Instruct",
        "apks_dir": "/fixture/apks",
        "subset_file": str(subset_file),
        "reps": 2,
        "timeout": 300,
        "containers": 2,
        "spec_set": "jca",
        "bootstrap_seed": 42,
        "arms": [
            {"role": "ANC1", "tool": "ape", "variant": "default"},
            {"role": "ANC2", "tool": "aperv", "variant": "sata_mop_act_frontier"},
            {"role": "A1", "tool": "aperv", "variant": "cal_a1"},
        ],
        "smoke": {"arm_roles": ["A1"], "apk_count": 2, "timeout": 90, "reps": 1},
    }
    p = tmp_path / "calfix.json"
    p.write_text(json.dumps(cfg))
    return p
