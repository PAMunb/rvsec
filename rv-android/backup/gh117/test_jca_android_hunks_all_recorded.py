# Backup of the INV-INS-118 gate, removed from tests/parity/test_gh104_specset_gates.py
# by gh117. It depended on these module-level names of that file:
#
#   import subprocess, sys
#   REPO = Path(__file__).resolve().parents[2]
#   SCRIPTS = REPO / "scripts"
#   def _rvsec_home() -> Path: ...  (skips when RVSEC_HOME or the successor set is absent)
#
# and on scripts/gh104_divergence_record.py (backed up alongside this file).


def test_jca_android_hunks_all_recorded():
    """INV-INS-118: the seed diff and the divergence record name the same hunks.

    A hunk with no row is an unattributed change to an instrument; a row naming no
    hunk is a reason recorded for content that has since moved, which is worse than
    no reason at all because it reads as one.
    """
    _rvsec_home()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "gh104_divergence_record.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
