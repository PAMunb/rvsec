"""Gate G_json_keys — Java↔Python JSON schema key parity (gh60 INV-ANA-32).

The static analyzer's JSON schema is owned by two side-by-side constants:

    presto.android.gui.clients.json.JsonSchema.Keys    (Java, producer)
    rv_static_analysis.parser.static.static_analysis_parser._JK  (Python, consumer)

Any drift between them silently breaks the parser (missing keys → defaults
applied → coverage misattributed). Design D5 revision 2 rejected regex
extraction from the `.java` source (fragile under Javadoc / annotations /
concatenation) in favour of a reflection-based dumper:

    Java side  → `JsonSchemaKeysDump.main()` walks `JsonSchema.Keys.class`
                 via reflection and prints each `public static final String`
                 value, sorted, one per line.
    Python side → this test invokes the dumper via `subprocess.run(...)`
                 against the deployed `lib/gator/rvsec-analysis-client.jar`
                 and asserts the value-set equals `set(_JK.__dict__.values())`.

Failure modes the test surfaces:
    - Java added a key, Python forgot → `extra_java` is non-empty
    - Python added a key, Java forgot → `extra_python` is non-empty
    - One side has a stale name (e.g. `reachesMop` post-rename) → flagged in
      whichever direction the stale name lives on

The test SKIPs (rather than fails) when:
    - The jar is missing — common on a fresh clone before `mvn install`
    - `java` is not on PATH

This keeps the gate honest in CI while avoiding spurious failures during
local refactoring loops that haven't rebuilt the jar yet.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from rv_static_analysis.parser.static.static_analysis_parser import _JK

from ._lenient_cache import required_or_skip

# rv-analysis-client jar is produced by `mvn install` in rvsec-gator/client
# and copied into `rv-android/lib/gator/` by the client pom's copy-resources
# step (see client/pom.xml). The deployment path is the authoritative one —
# `client/target/rvsec-analysis-client.jar` is the build artefact and may
# lag the source tree until the next mvn run.
JAR_PATH = Path(__file__).resolve().parents[2] / "lib" / "gator" / "rvsec-analysis-client.jar"
DUMPER_MAIN = "presto.android.gui.clients.json.JsonSchemaKeysDump"


def _java_available() -> bool:
    return shutil.which("java") is not None


def _dump_java_keys() -> list[str]:
    """Invoke JsonSchemaKeysDump.main and return the sorted key values.

    Surfaces stderr in the AssertionError so a misconfigured classpath
    fails loudly rather than producing an empty list (which would
    masquerade as "Java has zero keys" — confusing).
    """
    proc = subprocess.run(
        ["java", "-cp", str(JAR_PATH), DUMPER_MAIN],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, (
        f"JsonSchemaKeysDump exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


@pytest.fixture(scope="module")
def java_keys() -> list[str]:
    if not JAR_PATH.exists():
        required_or_skip(f"jar not deployed at {JAR_PATH} — run mvn install in rvsec-gator")
    if not _java_available():
        required_or_skip("java not on PATH")
    return _dump_java_keys()


def _python_keys() -> list[str]:
    return sorted(set(_JK.__dict__.values()))


def test_java_dump_is_sorted_and_nonempty(java_keys: list[str]) -> None:
    """Pre-condition: the dumper output is sorted and has at least 40 keys.

    The lower bound rules out a misconfigured run that produces an empty or
    near-empty list (e.g. wrong classpath, refactor accidentally moved
    JsonSchema.Keys to a non-public scope).
    """
    assert java_keys == sorted(java_keys), "JsonSchemaKeysDump output must be sorted"
    assert len(java_keys) >= 40, f"unexpectedly few keys from Java side: {java_keys}"


def test_java_python_key_sets_are_equal(java_keys: list[str]) -> None:
    """The headline parity assertion (INV-ANA-32)."""
    java_set = set(java_keys)
    python_set = set(_python_keys())

    extra_java = sorted(java_set - python_set)
    extra_python = sorted(python_set - java_set)

    assert not extra_java and not extra_python, (
        "JSON key drift between Java JsonSchema.Keys and Python _JK\n"
        f"  in Java but not Python ({len(extra_java)}): {extra_java}\n"
        f"  in Python but not Java ({len(extra_python)}): {extra_python}"
    )


def test_no_legacy_mop_key_values(java_keys: list[str]) -> None:
    """Regression guard — neither side should expose `reachesMop`-style values.

    `_no_legacy_mop` (scanner gate) covers identifier names; this assertion
    covers the JSON *values* the schema emits at runtime. They cluster the
    same way historically but the regex check on identifiers misses string
    literals on the wire.
    """
    forbidden = {"reachesMop", "directlyReachesMop", "mopMethods"}
    java_violations = forbidden & set(java_keys)
    python_violations = forbidden & set(_python_keys())
    assert not java_violations, f"legacy MOP key values still emitted by Java: {java_violations}"
    assert not python_violations, f"legacy MOP key values still in Python _JK: {python_violations}"


def test_count_matches_design_documented_size(java_keys: list[str]) -> None:
    """Design D5 documents ~45 entries (line 91). Both sides should agree.

    This is a tripwire: if someone adds a key on one side and forgets the
    other, the count diverges and `test_java_python_key_sets_are_equal`
    catches it. The independent count assertion gives a clearer error
    message at the top of the failure log when both sides accidentally
    grew the same number of fields with different names.
    """
    java_count = len(set(java_keys))
    python_count = len(set(_python_keys()))
    assert java_count == python_count, (
        f"key count drift — Java={java_count}, Python={python_count}"
    )
