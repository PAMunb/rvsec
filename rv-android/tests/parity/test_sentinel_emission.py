"""G_sentinela_complete — wire-level contract on real GATOR output.

Background
----------
Existing parser-side coverage (`modules/rv-static-analysis/tests/parser/
test_sentinel.py`, 4 cases) asserts the *parser* interprets the `complete`
key correctly under four shapes: present-and-True, present-and-False,
absent (legacy gh57), truncated-and-recovered. Those tests use synthetic
JSON fixtures.

This test closes the loop on the *producer* side by inspecting the actual
bytes written by `JsonReportWriter` when GATOR runs end-to-end on
cryptoapp. The design contract (ADR-6, design.md §D5 + INV-ANA-31):

    The sentinel is the LAST thing written before close(). On disk, a
    successful run's JSON ends with the byte sequence:
        ,"complete":true}\\n
    (the writer fsyncs immediately before close() to harden against
    NFS/cifs writeback reorder — verifiable only via the Java
    SentinelEmissionTest, which is out of scope here).

A wire-level test catches a class of regressions the parser tests can't:
    - Writer emits sentinel *somewhere* but not last (e.g. between two
      sections) — parser would still see complete=True but consumers
      that filesize-check or tail-scan get confused.
    - Writer accidentally double-emits the sentinel.
    - Writer emits `complete:true` (no quotes) — parser would still
      accept it because the Pydantic field is bool, but downstream
      tools that grep-scan the raw file fail.

Skipped when GATOR can't be invoked (no RVSEC_HOME, no cryptoapp.apk,
jar not deployed).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = ROOT / "scripts" / "check_signature_file_subset.py"
LENIENT_OUTPUT = Path("/tmp/gh60_g_subset/lenient.json")

# The writer emits the sentinel as the final key/value pair of the
# top-level object, with no trailing whitespace before the closing brace
# beyond a single newline. We accept three minor format variations because
# Gson's pretty-print mode (if anyone toggles it later) inserts whitespace
# around the colon and indentation — the gate cares about the order
# (last-key-is-complete) and the value, not the whitespace shape.
SENTINEL_TAIL_RX = re.compile(
    rb",\s*\"complete\"\s*:\s*true\s*}\s*\Z",
    re.MULTILINE,
)


def _ensure_lenient_output() -> Path | None:
    """Generate /tmp/gh60_g_subset/lenient.json by running the gate script.

    Re-uses the script that already encapsulates the gator-invocation
    boilerplate; the script writes both LENIENT and STRICT JSONs as a
    side effect, so calling it once for both gates avoids duplicating
    the bash incantation.

    Returns the path on success, or None when prerequisites are missing.
    """
    if LENIENT_OUTPUT.exists() and LENIENT_OUTPUT.stat().st_size > 0:
        return LENIENT_OUTPUT
    if not os.environ.get("RVSEC_HOME"):
        return None
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode == 77:
        return None
    if proc.returncode != 0:
        pytest.fail(
            f"check_signature_file_subset.py exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return LENIENT_OUTPUT if LENIENT_OUTPUT.exists() else None


@pytest.fixture(scope="module")
def lenient_output() -> Path:
    out = _ensure_lenient_output()
    if out is None:
        pytest.skip("GATOR prerequisites missing — cannot exercise wire format")
    return out


def test_real_gator_json_ends_with_complete_sentinel(lenient_output: Path) -> None:
    """Final bytes of a successful run match `,"complete":true}\\n?`.

    Reads the trailing 64 bytes (sentinel + close brace + optional
    newline) and matches against SENTINEL_TAIL_RX. Reading the whole
    file would also work but is wasteful — cryptoapp's JSON is ~50 KB.
    """
    size = lenient_output.stat().st_size
    with lenient_output.open("rb") as f:
        f.seek(max(0, size - 64))
        tail = f.read()
    assert SENTINEL_TAIL_RX.search(tail), (
        "JsonReportWriter must emit the sentinel as the FINAL key/value "
        "pair of the top-level object — observed trailing bytes:\n"
        f"{tail!r}"
    )


def test_real_gator_json_has_exactly_one_complete_key(lenient_output: Path) -> None:
    """Belt-and-braces — count occurrences of the sentinel key.

    A regression that emits `"complete":true` mid-stream AND at the end
    would pass the wire-format test above (the tail still matches). This
    catches the duplication.
    """
    raw = lenient_output.read_bytes()
    occurrences = len(re.findall(rb'"complete"\s*:\s*(true|false)', raw))
    assert occurrences == 1, (
        f"expected exactly one `complete` key in the JSON; found {occurrences}. "
        "Multiple emissions indicate the writer is re-entering the sentinel "
        "branch — INV-ANA-31 says it runs once, after the final flush."
    )


def test_real_gator_json_parses_with_complete_true(lenient_output: Path) -> None:
    """End-to-end consistency: wire-format claim agrees with parser."""
    data = StaticAnalysisParser().parse_file(str(lenient_output), "br.unb.cic.cryptoapp")
    assert data.complete is True, (
        "wire format claims complete=true but parser disagrees — sentinel "
        "is being written under a key the parser does not look for"
    )


def test_sentinel_value_is_literal_true_not_string(lenient_output: Path) -> None:
    """`"complete":true` (bool literal), not `"complete":"true"` (string).

    Pydantic would coerce `"true"` to bool in the parser, masking the
    bug. The grep-tools in `scripts/` rely on the literal boolean.
    """
    payload = json.loads(lenient_output.read_text())
    value = payload.get("complete")
    assert isinstance(value, bool), (
        f"sentinel value must be a JSON boolean literal; got {type(value).__name__}: {value!r}"
    )
    assert value is True
