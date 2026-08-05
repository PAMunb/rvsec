"""Flag > env > default resolution on the standalone entry point (D4, INV-EXP-34).

A standalone `rv-static-analysis` invocation is a run, not a step inside one, so
this command resolves `RV_PACKAGE_DETECTOR` itself instead of receiving a value:
an operator who exported the variable in a shell or a container gets the same
behaviour here as from `rv-experiment`, without having to remember which command
honours it. The read goes through the `ENV_PACKAGE_DETECTOR` constant and the
string is parsed by the helper both entry points share.

argparse has no `click.BadParameter`, so an unparseable value is reported and
exits nonzero at the same point — before either `App` is constructed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rv_static_analysis.__main__ import (
    main,
    resolve_package_detector,
    setup_argument_parser,
)


def _parse(argv: list[str]):
    return setup_argument_parser().parse_args(argv)


# ---------------------------------------------------------------------------
# The negatable pair is registered on both subcommands
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["analyze", "batch"])
def test_flag_pair_is_registered(command):
    argv = (
        ["analyze", "--apk", "a.apk", "--output", "/out"]
        if command == "analyze"
        else ["batch", "--apks-dir", "/apks", "--output", "/out"]
    )

    assert _parse(argv).package_detector is None
    assert _parse([*argv, "--package-detector"]).package_detector is True
    assert _parse([*argv, "--no-package-detector"]).package_detector is False


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_default_is_the_manifest_package():
    with patch.dict("os.environ", {}, clear=True):
        assert resolve_package_detector(None) is False


def test_env_var_enables_the_detector():
    """A bare invocation with the variable exported resolves to True."""
    with patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": "true"}, clear=True):
        assert resolve_package_detector(None) is True


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on", " On "])
def test_env_truthy_vocabulary(value):
    with patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": value}, clear=True):
        assert resolve_package_detector(None) is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
def test_env_falsy_vocabulary(value):
    with patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": value}, clear=True):
        assert resolve_package_detector(None) is False


def test_flag_overrides_a_truthy_env():
    with patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": "true"}, clear=True):
        assert resolve_package_detector(True) is True
        assert resolve_package_detector(False) is False


def test_unparseable_env_raises_naming_the_variable():
    with patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": "maybe"}, clear=True):
        with pytest.raises(ValueError, match="RV_PACKAGE_DETECTOR"):
            resolve_package_detector(None)


# ---------------------------------------------------------------------------
# main() resolves once, before any App is built
# ---------------------------------------------------------------------------


def test_main_exits_nonzero_on_an_unparseable_env(capsys):
    argv = ["analyze", "--apk", "a.apk", "--output", "/out"]

    with (
        patch("sys.argv", ["rv-static-analysis", *argv]),
        patch.dict("os.environ", {"RV_PACKAGE_DETECTOR": "maybe"}, clear=True),
        patch("rv_static_analysis.__main__.handle_analyze_command") as handler,
    ):
        exit_code = main()

    assert exit_code == 1
    assert "RV_PACKAGE_DETECTOR" in capsys.readouterr().err
    handler.assert_not_called()


@pytest.mark.parametrize(
    ("argv_extra", "env", "expected"),
    [
        ([], {}, False),
        ([], {"RV_PACKAGE_DETECTOR": "true"}, True),
        (["--package-detector"], {"RV_PACKAGE_DETECTOR": "false"}, True),
        (["--no-package-detector"], {"RV_PACKAGE_DETECTOR": "true"}, False),
    ],
)
def test_main_hands_the_handler_a_resolved_boolean(argv_extra, env, expected):
    argv = ["analyze", "--apk", "a.apk", "--output", "/out", *argv_extra]

    with (
        patch("sys.argv", ["rv-static-analysis", *argv]),
        patch.dict("os.environ", env, clear=True),
        patch("rv_static_analysis.__main__.handle_analyze_command") as handler,
    ):
        handler.return_value = 0
        main()

    assert handler.call_args.args[0].package_detector is expected
