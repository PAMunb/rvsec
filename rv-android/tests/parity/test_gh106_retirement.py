"""The retirement of the superseded ad-hoc comparators and CrySL readers (gh106, G13a).

Twelve distinct files were moved out of `audit/` on 2026-08-24: six `ORDER`
comparators and seven CrySL readers, with `batchD/alfa_language_check.py` in both
lists and therefore moved once. They were a photograph of two closed audits --
nothing imported them, no workflow ran them -- and the conformance component of
gh106 answers, from a single versioned oracle, the question each of them answered
by hand.

Three things are asserted, and the split between them is deliberate.

**Absence is unconditional.** The retirement either happened or it did not, and
`audit/` is a tracked directory that CI checks out like any other. If one of the
twelve reappears there, this fails everywhere.

**Presence under `backup/` is conditional.** The CI workflow's first step is
`rm -rf rv-android/backup/ …` (`.github/workflows/ci.yml:20`), so a bare presence
assertion would go red in CI for a reason that has nothing to do with the
retirement -- it would be reporting on the workflow's cleanup, not on this change.
The presence half therefore skips, loudly, when the tree is not there
(`risk-register.md` RISK-012).

**The census predicate is executable.** RISK-013 records that 13a.1's rule --
*a reader opens a `.crysl`/`.cryptsl`* -- is narrower than the mention-based grep
that produced the published count of seven. Encoding the strict predicate here
makes "the rule differs" distinguishable from "the tree moved" without anyone
having to exercise judgement a second time.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# The six comparators, by their path relative to the repository root before the
# move, paired with the backup directory each landed in.
COMPARATORS = [
    "audit/20260808_validacao_jca_android/batchA/alfa_automata_check.py",
    "audit/20260808_validacao_jca_android/batchB/alfa_automata_check.py",
    "audit/20260808_validacao_jca_android/pilot/alfa_automata_check.py",
    "audit/20260808_validacao_jca_android/batchC/alfa_language_check.py",
    "audit/20260808_validacao_jca_android/batchD/alfa_language_check.py",
    "audit/20260808_validacao_jca_android/batchB/juiz_walk_batchB.py",
]

# The seven readers, minus `batchD/alfa_language_check.py`: it is in both censuses
# but exists once, and it was moved with the comparators.
READERS = [
    "audit/20260808_validacao_jca_android/batchA/juiz_build_csv.py",
    "audit/20260808_validacao_jca_android/batchC/juiz_build_csv_batchC.py",
    "audit/20260808_validacao_jca_android/batchD/juiz_build_csv_batchD.py",
    "audit/20260808_validacao_jca_android/global/juizglobal_build.py",
    "audit/20260808_validacao_jca_android/set/set_cons_build.py",
    "audit/20260820_verificacao_plano_predicados_v2/agentA/parse_cryptsl.py",
]

RETIRED = COMPARATORS + READERS

COMPARATOR_BACKUP = REPO / "backup" / "20260824-gh106-audit-comparators"
READER_BACKUP = REPO / "backup" / "20260824-gh106-audit-crysl-readers"


# `audit/<rest>` -> `<rest>`: the backup directories mirror the tree below `audit/`
# so a citation inside a frozen audit report still resolves by eye.
def _mirrored(old_path: str) -> str:
    return old_path[len("audit/") :]


BACKUP_LOCATION = {p: COMPARATOR_BACKUP / _mirrored(p) for p in COMPARATORS}
BACKUP_LOCATION.update({p: READER_BACKUP / _mirrored(p) for p in READERS})

# Module names, for the dangling-import sweep. A dangling import in a script
# nobody runs is still a dangling import (P3).
MODULE_NAMES = sorted({Path(p).stem for p in RETIRED})

# The change's own planning artifacts name these paths because they *describe*
# the retirement; that is a statement about history, not a reference to a file
# the tree is expected to have.
PLANNING_ARTIFACTS = "openspec/changes/gh106-mop-crysl-conformance/"


SELF = "tests/parity/test_gh106_retirement.py"


def _git_grep(*patterns: str, fixed: bool = False) -> list[str]:
    """Repository-wide grep, `backup/` and this file excluded.

    `git grep` is used rather than a manual walk so the sweep sees exactly the
    files the repository tracks -- no `.venv`, no `__pycache__`, no experiment
    results, none of the untracked scratch a developer's tree accumulates. This
    file is excluded because it necessarily names every retired path in order to
    look for it. Exit status 1 means "no match", the outcome every caller wants.

    All the patterns go into one invocation: the repository is large enough that
    a call per pattern is the difference between a test that runs in a second and
    one nobody waits for.
    """
    command = ["git", "grep", "-n"]
    if fixed:
        command.append("-F")
    for pattern in patterns:
        command += ["-e", pattern]
    command += ["--", ".", ":!backup/*", f":!{SELF}"]
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip())
    return [line for line in completed.stdout.splitlines() if line]


# ── absence: unconditional, this is the retirement itself ────────────────────


@pytest.mark.parametrize("retired", RETIRED)
def test_retired_file_is_gone_from_audit(retired: str) -> None:
    assert not (REPO / retired).exists(), (
        f"{retired} is back under audit/. The comparators and readers of the two "
        "closed audits were retired by gh106 G13a; if this file is needed again, "
        "read it from backup/ rather than restoring it here."
    )


def test_no_audit_python_opens_a_crysl_rule() -> None:
    """The census predicate of 13a.1, executable (RISK-013).

    A *reader* is a Python file that opens a `.crysl`/`.cryptsl`. After the move,
    no file under `audit/` does. This is the assertion that tells a future reader
    whether the tree moved or the counting rule differed.
    """
    opener = re.compile(
        r"(?:open|read_text|read_bytes|glob|iglob|rglob)\s*\([^)]*\.(?:crysl|cryptsl)"
    )
    offenders = [
        str(path.relative_to(REPO))
        for path in sorted((REPO / "audit").rglob("*.py"))
        if opener.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert offenders == [], (
        "these files under audit/ open a CrySL rule and so meet 13a.1's reader "
        f"definition, but have no recorded disposition: {offenders}"
    )


def test_no_retired_module_is_still_imported() -> None:
    hits = _git_grep(
        *(rf"^[ \t]*(from|import)[ \t]+{module}\b" for module in MODULE_NAMES)
    )
    assert hits == [], f"dangling import of a retired module: {hits}"


def test_no_repository_relative_path_survives() -> None:
    """No file outside `backup/` still points at an old location.

    The change's own planning artifacts are exempt: `risk-register.md` names
    `parse_cryptsl.py`'s old path in the entry that argued for moving it, and a
    record of why a file moved has to be able to say where it moved from.

    The frozen audit reports, CSVs and hash manifests cite these scripts by their
    *audit-internal* path (`batchC/juiz_build_csv_batchC.py`, without the `audit/`
    prefix) as the provenance of a published number. Those citations are not
    rewritten -- a closed audit that lies about how it was produced is worth less
    than one pointing at a file that moved -- and `audit/README-scripts-aposentados.md`
    resolves them in one place.
    """
    hits = [h for h in _git_grep(*RETIRED, fixed=True) if PLANNING_ARTIFACTS not in h]
    assert hits == [], f"stale reference to a retired path: {hits}"


# ── presence: conditional, because CI deletes backup/ before it runs ─────────


@pytest.mark.parametrize("retired", RETIRED)
def test_retired_file_is_preserved_in_backup(retired: str) -> None:
    backup_root = REPO / "backup"
    if not backup_root.exists():
        pytest.skip(
            "backup/ is absent -- CI removes it at .github/workflows/ci.yml:20, so "
            "the preservation half of the retirement cannot be checked here. The "
            "absence half above is the one that carries the retirement."
        )
    destination = BACKUP_LOCATION[retired]
    assert destination.is_file(), (
        f"{retired} was retired but is not at {destination.relative_to(REPO)}; "
        "P3 requires the backup before the deletion, not instead of it."
    )


def test_each_backup_directory_documents_itself() -> None:
    backup_root = REPO / "backup"
    if not backup_root.exists():
        pytest.skip("backup/ is absent -- see .github/workflows/ci.yml:20")
    for directory in (COMPARATOR_BACKUP, READER_BACKUP):
        readme = directory / "README.md"
        assert readme.is_file(), f"{directory.relative_to(REPO)} has no README.md"
        assert readme.read_text(encoding="utf-8").strip(), "the README.md is empty"
