"""APERV_LLM_BASE_URL resolved at the entry point (INV-EXP-41).

`rv-experiment` reads the variable once, after `--tools` is parsed, and injects it into
`parameters["llm_url"]` of every `aperv` ToolConfig whose variant definition in the
registry carries `overrides.llm_url`. The DSL `@llm_url` wins over the variable, and a
cell without the LLM group receives nothing.

Two registries are used. The scenario tests register a stand-in `aperv` whose variant
table has the shape of the six cells plus `default`, so they pin the rule without
depending on which variant table `aperv-tool` carries. The end-to-end tests use the
registry `rv_experiment.__main__` populates on import (through `rv_platform`), and are
parametrized over whatever real `aperv` variants carry `overrides.llm_url`, down to the
`ape.llmUrl` line of `ape.properties`.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from rv_android_core.constants import ENV_APERV_LLM_BASE_URL
from rv_android_core.domain.task import ToolConfig
from rv_android_core.tools.tool_spec import ToolSpec
from rv_experiment.__main__ import (
    APERV_LLM_URL_KEY,
    APERV_OVERRIDES_KEY,
    APERV_TOOL_NAME,
    CLIContext,
    _inject_aperv_llm_url,
    _split_tool_specifications,
)
from rv_tools import ToolFactory, ToolRegistry

ENV_URL = "http://192.168.1.100:30000/v1"
DSL_URL = "http://sglang:30000/v1"
CELL_DEFAULT_URL = "http://10.0.2.2:30000/v1"

# modules/ — this file sits at modules/rv-experiment/tests/.
_MODULES_DIR = Path(__file__).resolve().parents[2]

_BASE = {"preset": "base", "strategy": "sata", "overrides": {}}
_LLM_OVERRIDES = {APERV_LLM_URL_KEY: CELL_DEFAULT_URL}
# The cell shapes of the aperv variant table: only as_llm and as_mop_llm mount the LLM
# group, and default is base.
_STAND_IN_VARIANTS: dict[str, dict] = {
    "default": _BASE,
    "base": _BASE,
    "mop": {"preset": "mop", "strategy": "sata", "overrides": {}},
    "as": {"preset": "as", "strategy": "sata", "overrides": {}},
    "as_mop": {"preset": "as_mop", "strategy": "sata", "overrides": {}},
    "as_llm": {
        "preset": "as_llm",
        "strategy": "sata",
        "overrides": dict(_LLM_OVERRIDES),
    },
    "as_mop_llm": {
        "preset": "as_mop_llm",
        "strategy": "sata",
        "overrides": dict(_LLM_OVERRIDES),
    },
}


class _StandInAperv:
    """Placeholder class; the injection reads only the registry's variant table."""


@pytest.fixture
def stand_in_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tool(
        APERV_TOOL_NAME,
        _StandInAperv,
        ToolSpec(name=APERV_TOOL_NAME, description="stand-in", url="-", version="0"),
    )
    for name, config in _STAND_IN_VARIANTS.items():
        registry.register_variant(APERV_TOOL_NAME, name, config)
    return registry


def _parse(tools: str) -> list[ToolConfig]:
    """Parse `--tools` exactly as `_create_experiment_config_from_cli` does."""
    ctx = CLIContext()
    configs: list[ToolConfig] = []
    for spec in _split_tool_specifications(tools):
        configs.extend(ctx.parse_tool_specification(spec))
    return configs


# --- Scenarios, against the stand-in variant table ------------------------------


def test_variable_reaches_llm_cells(monkeypatch, stand_in_registry):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = _parse("aperv:as_llm,aperv:as_mop_llm")

    _inject_aperv_llm_url(configs, stand_in_registry)

    assert [tc.parameters.get(APERV_LLM_URL_KEY) for tc in configs] == [
        ENV_URL,
        ENV_URL,
    ]


@pytest.mark.parametrize(
    "tools", ["aperv:base,aperv:as_mop", "aperv:mop,aperv:as", "aperv"]
)
def test_cells_without_llm_group_left_alone(monkeypatch, stand_in_registry, tools):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = _parse(tools)

    _inject_aperv_llm_url(configs, stand_in_registry)

    assert all(APERV_LLM_URL_KEY not in tc.parameters for tc in configs)


def test_dsl_value_wins_over_variable(monkeypatch, stand_in_registry):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = _parse(f"aperv:as_llm@llm_url={DSL_URL}")

    _inject_aperv_llm_url(configs, stand_in_registry)

    assert configs[0].parameters[APERV_LLM_URL_KEY] == DSL_URL


@pytest.mark.parametrize("value", [None, ""])
def test_unset_or_empty_variable_injects_nothing(monkeypatch, stand_in_registry, value):
    if value is None:
        monkeypatch.delenv(ENV_APERV_LLM_BASE_URL, raising=False)
    else:
        monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, value)
    configs = _parse("aperv:as_llm,aperv:as_mop_llm")

    _inject_aperv_llm_url(configs, stand_in_registry)

    assert all(APERV_LLM_URL_KEY not in tc.parameters for tc in configs)


def test_other_tools_and_unknown_variants_untouched(monkeypatch, stand_in_registry):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = [
        ToolConfig(name="monkey"),
        ToolConfig(name=APERV_TOOL_NAME, variant="nope"),
    ]

    _inject_aperv_llm_url(configs, stand_in_registry)

    assert all(tc.parameters == {} for tc in configs)


# --- End to end, against the registry rv_experiment.__main__ populates -----------


def _real_llm_variants() -> list[str]:
    registry = ToolRegistry.get_instance()
    if not registry.is_tool_registered(APERV_TOOL_NAME):
        return []
    return sorted(
        name
        for name in registry.get_tool_variants(APERV_TOOL_NAME)
        if APERV_LLM_URL_KEY
        in registry.get_variant_config(APERV_TOOL_NAME, name).get(
            APERV_OVERRIDES_KEY, {}
        )
    )


def _real_non_llm_variants() -> list[str]:
    registry = ToolRegistry.get_instance()
    if not registry.is_tool_registered(APERV_TOOL_NAME):
        return []
    llm = set(_real_llm_variants())
    return sorted(set(registry.get_tool_variants(APERV_TOOL_NAME)) - llm)


def test_real_registry_has_llm_cells():
    """Guards the parametrized tests below against collecting nothing."""
    assert _real_llm_variants(), "no registered aperv variant carries overrides.llm_url"


def _ape_properties(tool_config: ToolConfig) -> str:
    """Build the tool through ToolFactory and capture the ape.properties it would push."""
    tool = ToolFactory(ToolRegistry.get_instance()).create_tool(tool_config)
    captured: dict[str, str] = {}

    def _capture(local_path, *_args, **_kwargs):
        captured["content"] = Path(local_path).read_text()

    with patch.object(tool, "_push_file_to_device", side_effect=_capture):
        tool._push_properties("emulator-5554", "/dev/null")
    return captured["content"]


@pytest.mark.parametrize("variant", _real_llm_variants())
def test_real_llm_cell_writes_variable_into_ape_properties(monkeypatch, variant):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = _parse(f"aperv:{variant}")

    _inject_aperv_llm_url(configs, ToolRegistry.get_instance())

    assert configs[0].parameters[APERV_LLM_URL_KEY] == ENV_URL
    assert f"ape.llmUrl={ENV_URL}\n" in _ape_properties(configs[0])


@pytest.mark.parametrize("variant", _real_llm_variants())
def test_real_llm_cell_keeps_default_without_variable(monkeypatch, variant):
    monkeypatch.delenv(ENV_APERV_LLM_BASE_URL, raising=False)
    configs = _parse(f"aperv:{variant}")

    _inject_aperv_llm_url(configs, ToolRegistry.get_instance())

    assert APERV_LLM_URL_KEY not in configs[0].parameters
    default = ToolRegistry.get_instance().get_variant_config(APERV_TOOL_NAME, variant)[
        APERV_OVERRIDES_KEY
    ][APERV_LLM_URL_KEY]
    assert f"ape.llmUrl={default}\n" in _ape_properties(configs[0])


@pytest.mark.parametrize("variant", _real_non_llm_variants())
def test_real_non_llm_cell_gets_no_url(monkeypatch, variant):
    monkeypatch.setenv(ENV_APERV_LLM_BASE_URL, ENV_URL)
    configs = _parse(f"aperv:{variant}")

    _inject_aperv_llm_url(configs, ToolRegistry.get_instance())

    assert APERV_LLM_URL_KEY not in configs[0].parameters


# --- The reader set is pinned ---------------------------------------------------

_READ_RE = re.compile(
    r"(os\.environ\.get|os\.environ\[|os\.getenv)\s*\(?\s*"
    r"(ENV_APERV_LLM_BASE_URL|[\"']APERV_LLM_BASE_URL[\"'])"
)


def test_reader_set_is_pinned():
    readers = sorted(
        path.relative_to(_MODULES_DIR).as_posix()
        for path in _MODULES_DIR.glob("*/src/**/*.py")
        if _READ_RE.search(path.read_text(encoding="utf-8"))
    )
    assert readers == ["rv-experiment/src/rv_experiment/__main__.py"]

    main_source = (_MODULES_DIR / readers[0]).read_text(encoding="utf-8")
    reads = [m.group(2) for m in _READ_RE.finditer(main_source)]
    assert reads == ["ENV_APERV_LLM_BASE_URL"], "the read must go through the constant"


def test_aperv_tool_mentions_no_read():
    for path in (_MODULES_DIR / "aperv-tool" / "src").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "ENV_APERV_LLM_BASE_URL" not in source, path
        assert not _READ_RE.search(source), path
