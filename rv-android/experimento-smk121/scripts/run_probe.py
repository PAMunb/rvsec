#!/usr/bin/env python3
"""Run `rv-platform` with the `stampprobe` tool registered in-process.

usage: run_probe.py <rv-platform arguments>
  e.g. run_probe.py run --tools stampprobe --apks-dir DIR --results-dir DIR \
           --timeouts 60 --repetitions 1 --no-window

`StampProbeTool` is registered in the `ToolRegistry` singleton, and then
`rv_platform.__main__.main` runs with these arguments, so `rv-platform` keeps
starting and stopping the emulator, installing each APK and capturing logcat. For
each task the tool pushes `probe/probe.jar`, resolves the app's launcher activity,
launches it, waits until the app has the focus, and runs `StampProbe` once under
`app_process`. The probe's stdout (its dumps) is written to
`<task logcat without .logcat>.probe.txt`, beside the task's `.logcat`; its stderr
goes to the task's `.trace`.
"""
import shlex
import sys
import time
from pathlib import Path
from subprocess import PIPE

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.exceptions import RVToolExecutionError, RVToolTimeoutError
from rv_platform.__main__ import main as platform_main
from rv_tools import ToolRegistry

TOOL_NAME = "stampprobe"
PROBE_JAR = Path(__file__).resolve().parent.parent / "probe" / "probe.jar"
DEVICE_JAR = "/data/local/tmp/stampprobe.jar"
PROBE_SUFFIX = ".probe.txt"
FOCUS_WAIT_S = 30
# Seconds of the task timeout kept back from the probe's budget, for the launch
# before it and the last step it may be in when the budget runs out.
BUDGET_MARGIN_S = 15


def probe_dump_path(logcat_file: str) -> Path:
    """Where the probe's dumps of a task go: beside its `.logcat`."""
    return Path(logcat_file).with_suffix(PROBE_SUFFIX)


def launcher_component(resolve_output: str) -> str:
    """The `package/activity` line of `cmd package resolve-activity --brief`."""
    lines = [line.strip() for line in resolve_output.splitlines() if "/" in line]
    if not lines:
        raise RVToolExecutionError(
            f"no launcher activity in: {resolve_output!r}", tool_name=TOOL_NAME, cause=None
        )
    return lines[-1]


class StampProbeTool(AbstractTool):
    """Runs StampProbe once against the task's app (design D14 of gh121)."""

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name=TOOL_NAME,
        description="Reads the handler stamp through UiAutomation, one navigation level",
        url="experimento-smk121/probe",
        version="1.0.0",
        process_pattern="stampprobe",
    )

    def __init__(self):
        spec = self.get_tool_spec()
        super().__init__(
            name=spec.name, description=spec.description, process_pattern=spec.process_pattern
        )
        self.config = {}

    @classmethod
    def get_tool_spec(cls):
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls):
        return {"default": {}}

    def configure(self, config):
        self.config = dict(config)

    def _adb(self, serial, args, timeout=60, stdout=PIPE, stderr=PIPE):
        # `_execute_and_check_command` defaults both streams to None (inherit), which
        # leaves `result.stdout` as None; the callers that parse the output need PIPE.
        return self._execute_and_check_command(
            Command("adb", ["-s", serial, *args], timeout=timeout),
            stdout=stdout, stderr=stderr,
        )

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        serial = task.config.device_id
        package = app.package_name
        dumps = probe_dump_path(task.result.logcat_file)

        self._adb(serial, ["push", str(PROBE_JAR), DEVICE_JAR])
        resolved = self._adb(
            serial,
            ["shell", "cmd", "package", "resolve-activity", "--brief",
             "-c", "android.intent.category.LAUNCHER", package],
        )
        component = launcher_component(resolved.stdout.decode("utf-8", "replace"))
        activity = component.split("/", 1)[1]
        self._adb(serial, ["shell", "am", "start", "-W", "-n", component])
        self._wait_for_focus(serial, package)

        budget = max(1, task.config.timeout - BUDGET_MARGIN_S)
        shell = (
            f"CLASSPATH={DEVICE_JAR} app_process /data/local/tmp --nice-name=stampprobe "
            f"StampProbe {shlex.quote(package)} {shlex.quote(activity)} {budget}"
        )
        self.logger.info(f"StampProbe on {package}/{activity}, budget {budget}s -> {dumps}")
        with open(dumps, "wb") as out, open(task.result.trace_file, "ab") as err:
            try:
                self._adb(serial, ["shell", shell], timeout=task.config.timeout,
                          stdout=out, stderr=err)
            except RVToolTimeoutError:
                # The dumps written so far are already in the file.
                self.kill_related_processes(self.process_pattern)
                raise

    def _wait_for_focus(self, serial, package):
        """Poll the focused window until it belongs to `package`, up to FOCUS_WAIT_S."""
        deadline = time.monotonic() + FOCUS_WAIT_S
        while time.monotonic() < deadline:
            result = self._adb(serial, ["shell", "dumpsys", "window"])
            for line in result.stdout.decode("utf-8", "replace").splitlines():
                if "mCurrentFocus" in line and package in line:
                    return
            time.sleep(1)
        self.logger.warning(f"{package} did not take the focus in {FOCUS_WAIT_S}s")


def main() -> int:
    if not PROBE_JAR.is_file():
        sys.exit(f"{PROBE_JAR} not found; build it with probe/build_probe.sh")
    registry = ToolRegistry.get_instance()
    if not registry.is_tool_registered(TOOL_NAME):
        registry.register_tool_class(StampProbeTool)
    sys.argv = ["rv-platform", *sys.argv[1:]]
    return platform_main()


if __name__ == "__main__":
    sys.exit(main())
