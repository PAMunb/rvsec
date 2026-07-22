"""
Tests for FastBotTool - reinforcement-learning model-based testing tool.

WHY these tests exist: FastBotTool wraps the ByteDance Fastbot binary and had
17% coverage. The class is mostly pure logic (construction, exhaustive
configure() validation, ADB command construction) plus a handful of device/IO
helpers. Pure logic is exercised without mocks; the device/IO helpers are
exercised with the Command class and jar_resolver patched so no real emulator,
adb, or filesystem push is ever touched.

Test design rationale:
- configure() is validated with Equivalence Partitioning + Boundary Value
  Analysis: for every numeric field we assert the valid class mutates config
  and each invalid class (out-of-range, non-numeric) leaves the default intact.
- execute_tool_specific_logic() is decorated with @ErrorHandler.handle_errors
  (reraise=False), so exceptions are absorbed and the method returns None. Tests
  assert that observed behavior rather than expecting propagation.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.error.exceptions import RVToolExecutionError

from rv_tools.builtin.fastbot.tool import FastBotTool, register_fastbot_variants

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tool():
    """A freshly constructed FastBotTool with its real default config.

    Construction is cheap (JarResolver only wires a logger), so we build a real
    instance; helper tests that touch the device patch jar_resolver/Command
    per-test rather than in the fixture, keeping the default config observable.
    """
    return FastBotTool()


@pytest.fixture
def app_stub():
    """Minimal application stub exposing only the attribute the tool reads."""
    return SimpleNamespace(package_name="com.test.app")


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    """Construction wires infrastructure and the documented default config."""

    def test_default_config_values(self, tool):
        """WHY: the RL defaults are the tool's public contract when no variant
        override is supplied; regressions here silently change exploration."""
        assert tool.config["max_step"] == 10000
        assert tool.config["strategy"] == "balanced"
        assert tool.config["throttle"] == 500
        assert tool.config["timeout"] == 3600
        assert tool.config["learning_rate"] == 0.1
        assert tool.config["exploration_rate"] == 0.2
        assert tool.config["model_update_frequency"] == 100
        assert tool.config["debug_mode"] is False
        assert tool.config["device_serial"] is None

    def test_infrastructure_components_set(self, tool):
        """Logger and jar_resolver must be wired for later resolution/logging."""
        assert tool.logger is not None
        assert tool.jar_resolver is not None

    def test_name_defaults_from_spec(self, tool):
        """Without overrides the tool identifies itself via TOOL_SPEC."""
        assert tool.name == FastBotTool.TOOL_SPEC.name


# ---------------------------------------------------------------------------
# get_variants / get_tool_spec
# ---------------------------------------------------------------------------


class TestVariants:
    """The four preconfigured learning profiles and the tool spec."""

    def test_get_variants_keys(self):
        variants = FastBotTool.get_variants()
        assert set(variants) == {"default", "conservative", "aggressive", "balanced"}

    def test_conservative_values(self):
        """Conservative trades breadth for stability: higher throttle, lower epsilon."""
        conservative = FastBotTool.get_variants()["conservative"]
        assert conservative["throttle"] == 1000
        assert conservative["exploration_rate"] == 0.1

    def test_aggressive_values(self):
        aggressive = FastBotTool.get_variants()["aggressive"]
        assert aggressive["max_step"] == 20000
        assert aggressive["debug_mode"] is True

    def test_get_tool_spec(self):
        assert FastBotTool.get_tool_spec().name == "fastbot"


# ---------------------------------------------------------------------------
# get_available_strategies
# ---------------------------------------------------------------------------


class TestGetAvailableStrategies:
    """Returns a defensive copy so callers cannot mutate the class list."""

    def test_returns_expected_strategies(self, tool):
        assert tool.get_available_strategies() == FastBotTool.AVAILABLE_STRATEGIES

    def test_returns_copy_not_class_list(self, tool):
        """WHY: returning the class attribute directly would let a caller's
        .append() corrupt every future instance's strategy validation."""
        assert tool.get_available_strategies() is not FastBotTool.AVAILABLE_STRATEGIES


# ---------------------------------------------------------------------------
# configure() - Equivalence Partitioning + Boundary Value Analysis
# ---------------------------------------------------------------------------


class TestConfigureEarlyReturn:
    def test_empty_config_leaves_defaults(self, tool):
        """Empty/falsy config is a no-op; defaults survive untouched."""
        tool.configure({})
        assert tool.config["max_step"] == 10000
        assert tool.config["strategy"] == "balanced"

    def test_none_config_is_noop(self, tool):
        tool.configure(None)
        assert tool.config["max_step"] == 10000


class TestConfigureMaxStep:
    """max_step: valid (>0) mutates; boundary 0, negative, and non-numeric do not."""

    def test_valid_positive(self, tool):
        tool.configure({"max_step": 500})
        assert tool.config["max_step"] == 500

    def test_zero_rejected(self, tool):
        tool.configure({"max_step": 0})
        assert tool.config["max_step"] == 10000

    def test_negative_rejected(self, tool):
        tool.configure({"max_step": -5})
        assert tool.config["max_step"] == 10000

    def test_non_numeric_rejected(self, tool):
        """int('abc') raises ValueError, caught and ignored."""
        tool.configure({"max_step": "abc"})
        assert tool.config["max_step"] == 10000

    def test_none_value_type_error_rejected(self, tool):
        """int(None) raises TypeError, exercised by the (ValueError, TypeError) guard."""
        tool.configure({"max_step": None})
        assert tool.config["max_step"] == 10000


class TestConfigureDeviceSerial:
    def test_device_serial_set(self, tool):
        tool.configure({"device_serial": "emulator-5556"})
        assert tool.config["device_serial"] == "emulator-5556"


class TestConfigureStrategy:
    def test_valid_strategy(self, tool):
        tool.configure({"strategy": "aggressive"})
        assert tool.config["strategy"] == "aggressive"

    def test_invalid_strategy_keeps_default(self, tool):
        """Unknown strategy is rejected; config stays on the default 'balanced'."""
        tool.configure({"strategy": "nonsense"})
        assert tool.config["strategy"] == "balanced"


class TestConfigureThrottle:
    """throttle boundary is 0 (non-negative allowed), negatives rejected."""

    def test_valid(self, tool):
        tool.configure({"throttle": 250})
        assert tool.config["throttle"] == 250

    def test_zero_allowed(self, tool):
        tool.configure({"throttle": 0})
        assert tool.config["throttle"] == 0

    def test_negative_rejected(self, tool):
        tool.configure({"throttle": -1})
        assert tool.config["throttle"] == 500

    def test_non_numeric_rejected(self, tool):
        tool.configure({"throttle": "x"})
        assert tool.config["throttle"] == 500


class TestConfigureTimeout:
    """timeout must be strictly positive; 0 is the rejected boundary."""

    def test_valid(self, tool):
        tool.configure({"timeout": 120})
        assert tool.config["timeout"] == 120

    def test_zero_rejected(self, tool):
        tool.configure({"timeout": 0})
        assert tool.config["timeout"] == 3600

    def test_non_numeric_rejected(self, tool):
        tool.configure({"timeout": "x"})
        assert tool.config["timeout"] == 3600


class TestConfigureLearningParams:
    """learning_rate / exploration_rate are clamped to [0.0, 1.0]."""

    def test_learning_rate_valid(self, tool):
        tool.configure({"learning_rate": 0.5})
        assert tool.config["learning_rate"] == 0.5

    def test_learning_rate_above_range_rejected(self, tool):
        tool.configure({"learning_rate": 1.5})
        assert tool.config["learning_rate"] == 0.1

    def test_learning_rate_below_range_rejected(self, tool):
        tool.configure({"learning_rate": -0.1})
        assert tool.config["learning_rate"] == 0.1

    def test_learning_rate_non_numeric_rejected(self, tool):
        tool.configure({"learning_rate": "x"})
        assert tool.config["learning_rate"] == 0.1

    def test_exploration_rate_valid_boundaries(self, tool):
        """Boundaries 0.0 and 1.0 are inclusive and must be accepted."""
        tool.configure({"exploration_rate": 0.0})
        assert tool.config["exploration_rate"] == 0.0
        tool.configure({"exploration_rate": 1.0})
        assert tool.config["exploration_rate"] == 1.0

    def test_exploration_rate_above_range_rejected(self, tool):
        tool.configure({"exploration_rate": 2.0})
        assert tool.config["exploration_rate"] == 0.2


class TestConfigureModelUpdateFrequency:
    def test_valid(self, tool):
        tool.configure({"model_update_frequency": 50})
        assert tool.config["model_update_frequency"] == 50

    def test_zero_rejected(self, tool):
        tool.configure({"model_update_frequency": 0})
        assert tool.config["model_update_frequency"] == 100

    def test_non_numeric_rejected(self, tool):
        tool.configure({"model_update_frequency": "x"})
        assert tool.config["model_update_frequency"] == 100


class TestConfigureDebugModeAndJars:
    def test_debug_mode_truthy_coerced_to_true(self, tool):
        tool.configure({"debug_mode": 1})
        assert tool.config["debug_mode"] is True

    def test_debug_mode_falsy_coerced_to_false(self, tool):
        tool.configure({"debug_mode": 0})
        assert tool.config["debug_mode"] is False

    def test_jar_paths_set(self, tool):
        tool.configure(
            {
                "fastbot_thirdpart_jar": "/a/fastbot-thirdpart.jar",
                "framework_jar": "/a/framework.jar",
                "monkeyq_jar": "/a/monkeyq.jar",
            }
        )
        assert tool.config["fastbot_thirdpart_jar"] == "/a/fastbot-thirdpart.jar"
        assert tool.config["framework_jar"] == "/a/framework.jar"
        assert tool.config["monkeyq_jar"] == "/a/monkeyq.jar"


# ---------------------------------------------------------------------------
# _build_fastbot_command
# ---------------------------------------------------------------------------


class TestBuildFastbotCommand:
    """The ADB app_process command that launches Fastbot's Monkey entry point."""

    def test_returns_adb_command(self, tool, app_stub):
        cmd = tool._build_fastbot_command(app_stub, 5, 300)
        assert cmd.command == "adb"
        assert cmd.timeout == 300

    def test_default_device_serial(self, tool, app_stub):
        """device_serial None falls back to the standard emulator-5554."""
        cmd = tool._build_fastbot_command(app_stub, 5, 300)
        assert "emulator-5554" in cmd.args

    def test_custom_device_serial(self, tool, app_stub):
        tool.config["device_serial"] = "emulator-5560"
        cmd = tool._build_fastbot_command(app_stub, 5, 300)
        assert "emulator-5560" in cmd.args

    def test_classpath_and_agent(self, tool, app_stub):
        cmd = tool._build_fastbot_command(app_stub, 5, 300)
        assert (
            "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar"
            in cmd.args
        )
        assert "--agent" in cmd.args
        assert "reuseq" in cmd.args

    def test_package_and_running_minutes(self, tool, app_stub):
        cmd = tool._build_fastbot_command(app_stub, 7, 420)
        assert "-p" in cmd.args
        assert "com.test.app" in cmd.args
        assert "--running-minutes" in cmd.args
        assert "7" in cmd.args

    def test_throttle_from_config_as_string(self, tool, app_stub):
        tool.config["throttle"] = 350
        cmd = tool._build_fastbot_command(app_stub, 5, 300)
        assert "--throttle" in cmd.args
        assert "350" in cmd.args


# ---------------------------------------------------------------------------
# get_tool_info
# ---------------------------------------------------------------------------


class TestGetToolInfo:
    """Merges base tool info with FastBot-specific fields."""

    def test_merges_expected_keys(self, tool):
        info = tool.get_tool_info()
        for key in (
            "tool_spec",
            "available_strategies",
            "current_strategy",
            "version",
            "url",
        ):
            assert key in info

    def test_current_strategy_reflects_config(self, tool):
        tool.configure({"strategy": "aggressive"})
        info = tool.get_tool_info()
        assert info["current_strategy"] == "aggressive"


# ---------------------------------------------------------------------------
# _resolve_fastbot_jars
# ---------------------------------------------------------------------------


class TestResolveFastbotJars:
    def test_resolves_all_three_via_search_paths(self, tool):
        """No configured paths -> resolver is queried with the search paths."""
        tool.jar_resolver.resolve_jar_path = MagicMock(return_value="/resolved.jar")
        result = tool._resolve_fastbot_jars()
        assert set(result) == {"fastbot_thirdpart", "framework", "monkeyq"}
        assert tool.jar_resolver.resolve_jar_path.call_count == 3

    def test_resolves_via_configured_paths(self, tool):
        """When config supplies jar paths, the resolver searches their directory."""
        tool.config["fastbot_thirdpart_jar"] = "/c/fastbot-thirdpart.jar"
        tool.config["framework_jar"] = "/c/framework.jar"
        tool.config["monkeyq_jar"] = "/c/monkeyq.jar"
        tool.jar_resolver.resolve_jar_path = MagicMock(return_value="/c/x.jar")
        result = tool._resolve_fastbot_jars()
        assert len(result) == 3
        # The directory of the configured path is what gets searched.
        first_call_search_paths = tool.jar_resolver.resolve_jar_path.call_args_list[0][
            0
        ][1]
        assert first_call_search_paths == ["/c"]

    def test_missing_jar_reraised_as_file_not_found(self, tool):
        tool.jar_resolver.resolve_jar_path = MagicMock(side_effect=FileNotFoundError())
        with pytest.raises(FileNotFoundError, match="not found"):
            tool._resolve_fastbot_jars()


# ---------------------------------------------------------------------------
# _push_jars_to_sdcard
# ---------------------------------------------------------------------------


class TestPushJarsToSdcard:
    @pytest.fixture
    def jar_paths(self):
        return {
            "fastbot_thirdpart": "/l/fastbot-thirdpart.jar",
            "framework": "/l/framework.jar",
            "monkeyq": "/l/monkeyq.jar",
        }

    def test_success(self, tool, jar_paths, tmp_path):
        """All three JARs push cleanly (result.is_failure() False)."""
        trace = tmp_path / "trace.txt"
        result = MagicMock()
        result.is_failure.return_value = False
        with patch("rv_tools.builtin.fastbot.tool.Command") as command_cls:
            command_cls.return_value.invoke.return_value = result
            tool._push_jars_to_sdcard(jar_paths, str(trace))
        assert command_cls.call_count == 3

    def test_failure_with_error_output(self, tool, jar_paths, tmp_path):
        """A failed push with stderr raises RVToolExecutionError including the stderr."""
        trace = tmp_path / "trace.txt"
        result = MagicMock()
        result.is_failure.return_value = True
        result.has_error_output.return_value = True
        result.get_stderr_text.return_value = "boom"
        result.code = 1
        with patch("rv_tools.builtin.fastbot.tool.Command") as command_cls:
            command_cls.return_value.invoke.return_value = result
            with pytest.raises(RVToolExecutionError, match="boom"):
                tool._push_jars_to_sdcard(jar_paths, str(trace))

    def test_failure_without_error_output(self, tool, jar_paths, tmp_path):
        """A failed push without stderr still raises (message omits the Error clause)."""
        trace = tmp_path / "trace.txt"
        result = MagicMock()
        result.is_failure.return_value = True
        result.has_error_output.return_value = False
        result.code = 2
        with patch("rv_tools.builtin.fastbot.tool.Command") as command_cls:
            command_cls.return_value.invoke.return_value = result
            with pytest.raises(RVToolExecutionError, match="exit code 2"):
                tool._push_jars_to_sdcard(jar_paths, str(trace))


# ---------------------------------------------------------------------------
# _push_libs_to_device
# ---------------------------------------------------------------------------


class TestPushLibsToDevice:
    def test_missing_libs_dir_warns_and_returns(self, tool, tmp_path):
        """If the libs directory cannot be resolved, execution continues without
        native libs (early return) rather than failing the whole run."""
        trace = tmp_path / "trace.txt"
        tool.jar_resolver.resolve_resource_directory = MagicMock(
            side_effect=Exception("no libs")
        )
        tool._execute_and_check_command = MagicMock()
        tool._push_libs_to_device(str(trace))
        tool._execute_and_check_command.assert_not_called()

    def test_success_pushes_present_architecture(self, tool, tmp_path):
        """Only architectures whose .so file exists on disk are pushed."""
        trace = tmp_path / "trace.txt"
        tool.jar_resolver.resolve_resource_directory = MagicMock(return_value="/libs")
        tool._execute_and_check_command = MagicMock()
        with patch(
            "rv_tools.builtin.fastbot.tool.os.path.isfile",
            side_effect=lambda p: "x86_64" in p,
        ), patch("rv_tools.builtin.fastbot.tool.Command"):
            tool._push_libs_to_device(str(trace))
        assert tool._execute_and_check_command.call_count == 1

    def test_push_failure_is_non_fatal(self, tool, tmp_path):
        """A per-architecture push failure is logged and skipped, not raised."""
        trace = tmp_path / "trace.txt"
        tool.jar_resolver.resolve_resource_directory = MagicMock(return_value="/libs")
        tool._execute_and_check_command = MagicMock(side_effect=Exception("push failed"))
        with patch(
            "rv_tools.builtin.fastbot.tool.os.path.isfile",
            side_effect=lambda p: "x86_64" in p,
        ), patch("rv_tools.builtin.fastbot.tool.Command"):
            # Must not raise despite the underlying push failing.
            tool._push_libs_to_device(str(trace))


# ---------------------------------------------------------------------------
# execute_tool_specific_logic
# ---------------------------------------------------------------------------


class TestExecuteToolSpecificLogic:
    """Orchestration of resolve -> push -> build -> execute.

    The method is wrapped by @ErrorHandler.handle_errors(reraise=False): with no
    error callbacks registered, an escaping exception is logged and the wrapper
    returns None. Tests assert that empirically-verified behavior.
    """

    def _make_task(self, tmp_path, timeout):
        trace = tmp_path / "trace.txt"
        return SimpleNamespace(
            config=SimpleNamespace(timeout=timeout),
            result=SimpleNamespace(trace_file=str(trace)),
        )

    def _patch_helpers(self, tool):
        tool._resolve_fastbot_jars = MagicMock(return_value={"framework": "/f.jar"})
        tool._push_jars_to_sdcard = MagicMock()
        tool._push_libs_to_device = MagicMock()
        tool._build_fastbot_command = MagicMock(
            return_value=SimpleNamespace(command="adb", args=["x"])
        )
        tool._execute_and_check_command = MagicMock()

    def test_happy_path_invokes_pipeline(self, tool, app_stub, tmp_path):
        self._patch_helpers(tool)
        task = self._make_task(tmp_path, timeout=300)
        tool.execute_tool_specific_logic(task, app_stub)

        tool._resolve_fastbot_jars.assert_called_once()
        tool._push_jars_to_sdcard.assert_called_once()
        tool._push_libs_to_device.assert_called_once()
        tool._execute_and_check_command.assert_called_once()
        # 300s / 60 = 5 minutes.
        assert tool._build_fastbot_command.call_args[0][1] == 5

    def test_sub_minute_timeout_floored_to_one_minute(self, tool, app_stub, tmp_path):
        """timeout < 60s -> int(seconds/60) == 0 -> clamped to 1 minute so Fastbot
        does not run for zero minutes."""
        self._patch_helpers(tool)
        task = self._make_task(tmp_path, timeout=30)
        tool.execute_tool_specific_logic(task, app_stub)
        assert tool._build_fastbot_command.call_args[0][1] == 1

    def test_exception_absorbed_by_decorator(self, tool, app_stub, tmp_path):
        """A failing helper does not propagate: the decorator absorbs it and the
        method returns None."""
        self._patch_helpers(tool)
        tool._resolve_fastbot_jars = MagicMock(side_effect=RuntimeError("resolve boom"))
        task = self._make_task(tmp_path, timeout=300)
        result = tool.execute_tool_specific_logic(task, app_stub)
        assert result is None
        tool._push_jars_to_sdcard.assert_not_called()

    def test_execute_failure_logged_and_absorbed(self, tool, app_stub, tmp_path):
        """When the command execution itself raises, the inner except logs the
        error and re-raises; the decorator then absorbs it (returns None)."""
        self._patch_helpers(tool)
        tool._execute_and_check_command = MagicMock(side_effect=RuntimeError("exec boom"))
        tool.logger = MagicMock()
        task = self._make_task(tmp_path, timeout=300)
        result = tool.execute_tool_specific_logic(task, app_stub)
        assert result is None
        tool.logger.error.assert_called()


# ---------------------------------------------------------------------------
# register_fastbot_variants
# ---------------------------------------------------------------------------


class TestRegisterFastbotVariants:
    def test_registers_all_four_variants(self):
        registry = MagicMock()
        register_fastbot_variants(registry)
        assert registry.register_variant.call_count == 4
        registered = {
            call.args[1] for call in registry.register_variant.call_args_list
        }
        assert registered == {"conservative", "aggressive", "balanced", "model_based"}

    def test_conservative_config(self):
        registry = MagicMock()
        register_fastbot_variants(registry)
        conservative_call = next(
            call
            for call in registry.register_variant.call_args_list
            if call.args[1] == "conservative"
        )
        assert conservative_call.args[0] == "fastbot"
        assert conservative_call.args[2] == {
            "strategy": "conservative",
            "exploration_rate": 0.1,
        }
