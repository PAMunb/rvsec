"""check_delivery on a synthetic logcat and probe dumps: a match, a mismatch, an
unpaired line, a step outside the app."""

import importlib.util
import io
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_delivery", Path(__file__).resolve().parent.parent / "scripts" / "check_delivery.py"
)
check_delivery = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_delivery)

PKG = "com.example.app"
BASE = "app.apk__1__60__stampprobe"

LOGCAT = f"""--------- beginning of main
10-07 18:00:00.100  1234  1234 I RVSEC-BIND: view kind=click node=android.widget.Button viewClass=android.widget.Button id={PKG}:id/ok handler={PKG}.MainActivity$1 obj=aa01
10-07 18:00:00.200  1234  1234 I RVSEC-BIND: view kind=click node=android.widget.Button viewClass=android.widget.Button id={PKG}:id/unseen handler={PKG}.MainActivity$2 obj=aa02
10-07 18:00:00.300  1234  1234 I RVSEC-BIND: compose kind=click node=android.widget.Button semanticsId=7 id=- bounds=[0,100][200,180] handler={PKG}.ui.HomeKt$Home$1 longClickHandler={PKG}.ui.HomeKt$Home$2
10-07 18:00:00.400  1234  1234 I RVSEC     : not a bind line
10-07 18:00:09.000  1234  1234 I RVSEC-BIND: view kind=click node=android.widget.Button viewClass=android.widget.Button id={PKG}:id/ok handler={PKG}.Later obj=aa01
"""


def _dumps(ok_extra):
    """A start step in the app and a click step outside it. The line logged at
    18:00:09 comes after the start dump, so it must not be used for it."""
    return "\n".join([
        f"APP\t{PKG}\t.MainActivity",
        f"STEP\t0\t10-07 18:00:01.000\t{PKG}\tstart\t-\t-\t-",
        f"NODE\tandroid.widget.FrameLayout\t-\t[0,0][1080,1920]\t-\t-",
        f"NODE\tandroid.widget.Button\t{PKG}:id/ok\t[0,0][200,90]\t{ok_extra}\t-",
        f"NODE\tandroid.widget.Button\t-\t[0,100][200,180]\t{PKG}.ui.HomeKt$Home$1\t{PKG}.ui.HomeKt$Home$2",
        f"STEP\t1\t10-07 18:00:05.000\tcom.android.chrome\tclick\tandroid.widget.Button\t{PKG}:id/ok\t[0,0][200,90]",
        f"NODE\tandroid.widget.Button\t{PKG}:id/ok\t[0,0][200,90]\tsomething.Else\t-",
        "",
    ])


def _write_run(tmp_path, ok_extra):
    task_dir = tmp_path / "app.apk"
    task_dir.mkdir()
    (task_dir / f"{BASE}.logcat").write_text(LOGCAT)
    dump = task_dir / f"{BASE}.probe.txt"
    dump.write_text(_dumps(ok_extra))
    return dump


def test_matching_view_and_compose_nodes_pass(tmp_path, capsys):
    dump = _write_run(tmp_path, f"{PKG}.MainActivity$1")

    totals = check_delivery.check_apk(dump, io.StringIO())

    assert totals["view"] == 1 and totals["compose"] == 1
    assert totals["match"] == 2 and totals["mismatch"] == 0
    assert check_delivery.main([str(tmp_path)]) == 0
    assert "PASS" in capsys.readouterr().out


def test_a_mismatching_view_node_fails(tmp_path, capsys):
    dump = _write_run(tmp_path, f"{PKG}.Other")

    totals = check_delivery.check_apk(dump, io.StringIO())

    assert totals["mismatch"] == 1 and totals["match"] == 1
    assert check_delivery.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert f"MISMATCH view {PKG}:id/ok" in out
    assert "FAIL" in out


def test_a_line_with_no_node_is_reported_unpaired_not_failed(tmp_path):
    dump = _write_run(tmp_path, f"{PKG}.MainActivity$1")

    totals = check_delivery.check_apk(dump, io.StringIO())

    # id/unseen was logged before the start dump and no node carries it.
    assert totals["unpaired_lines"] == 1
    assert totals["mismatch"] == 0


def test_a_step_outside_the_app_is_skipped(tmp_path):
    dump = _write_run(tmp_path, f"{PKG}.MainActivity$1")
    report = io.StringIO()

    totals = check_delivery.check_apk(dump, report)

    # Step 1 is in com.android.chrome: its node would mismatch, but it is not read.
    assert totals["steps"] == 2 and totals["in_app"] == 1
    assert totals["mismatch"] == 0
    assert "step 1 click" in report.getvalue()
    assert "skipped, foreground com.android.chrome" in report.getvalue()


def test_no_compose_node_paired_fails(tmp_path):
    dump = _write_run(tmp_path, f"{PKG}.MainActivity$1")
    logcat = dump.with_name(f"{BASE}.logcat")
    logcat.write_text("".join(l + "\n" for l in LOGCAT.splitlines() if "compose" not in l))

    assert check_delivery.main([str(tmp_path)]) == 1
