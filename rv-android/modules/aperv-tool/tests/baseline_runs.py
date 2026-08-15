"""Locating one pinned baseline run by its identity rather than by its filename.

The twelve copied runs are chosen for the cases the parsers must get right, so a
test needs a specific one — the trace with no step marker, the one carrying an
ANR, the rare one that stopped in an orderly way. Naming those by string literal
would let a regenerated fixture drop a case and leave the suite green on a
`FileNotFoundError` that reads as an environment problem.

So a test asks for a run by the identity the manifest pins — application,
repetition, timeout and arm — and this module resolves it, failing loudly and by
name when the manifest no longer carries it. `conftest.py` puts this directory on
`sys.path`, which is what makes `from baseline_runs import …` work under the CI
contract's `--import-mode=importlib`.
"""

from __future__ import annotations

from pathlib import Path


def trace_of(
    directory: Path,
    manifest: dict,
    *,
    apk: str,
    repetition: int,
    timeout_s: int,
    arm: str,
) -> Path:
    """The pinned `.trace` of one run.

    Args:
        directory: The populated `baseline_sample/` directory.
        manifest: The parsed `baseline_sample_manifest.json`.
        apk: Application file name, as the run identity spells it.
        repetition: Replica number.
        timeout_s: Declared budget in seconds.
        arm: Arm label, colon included for the `droidbot` variants.

    Returns:
        The path to the trace.

    Raises:
        AssertionError: The manifest no longer pins that run, or the file it
            pins is absent. Both are defects in the fixture, not skips: these
            twelve runs are versioned.
    """
    identity = (apk, repetition, timeout_s, arm)
    pinned = [
        run
        for run in manifest["runs"]
        if (run["apk"], run["repetition"], run["timeout_s"], run["arm"]) == identity
    ]
    assert pinned, f"the manifest no longer pins the run {identity}"

    name = f"{apk}__{repetition}__{timeout_s}__{arm}.trace"
    assert name in pinned[0]["files"], f"{name} is not among that run's pinned files"

    path = directory / name
    assert path.is_file(), f"{path} is pinned by the manifest but not present"
    return path
