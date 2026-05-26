"""Gate G_signature_file_subset — pytest harness.

Thin wrapper around `scripts/check_signature_file_subset.py`. The script
itself owns the gator-invocation + JSON-diff logic so the operator can
also run it standalone (`uv run python scripts/check_signature_file_subset.py`).
This test:

    - Skips when the script exits 77 (POSIX skipped) — i.e. RVSEC_HOME
      unset, cryptoapp.apk absent, or the deployed jar missing.
    - Fails on any other non-zero exit, surfacing the script's stdout
      so the operator sees the offending methods inline.

The full GATOR pass runs in ~12 s on a warm cache (two ~6 s runs). No
marker — operators who want to filter it out run
`pytest --deselect tests/parity/test_signature_file_subset.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_signature_file_subset.py"
SKIP_EXIT = 77


def test_strict_is_subset_of_lenient_on_cryptoapp() -> None:
    """STRICT (--targets-file) result ⊆ LENIENT (--mop-dir) result."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )

    if proc.returncode == SKIP_EXIT:
        pytest.skip(f"prerequisites missing:\n{proc.stdout}\n{proc.stderr}")

    assert proc.returncode == 0, (
        f"G_signature_file_subset script exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "G_signature_file_subset: PASS" in proc.stdout, (
        f"expected PASS line in script output, got:\n{proc.stdout}"
    )
