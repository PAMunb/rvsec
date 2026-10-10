# CLAUDE.md - rv-tools

## Purpose
Centralized tool registry and plugin system for Android app-testing tools. Manages tool registration, instantiation, and variant-based configuration. The top-level `rv-android/CLAUDE.md` owns the uv/pytest/env conventions and module map — not repeated here.

## Registration + creation flow
```
Module import → _register_builtin_tools()   (src/rv_tools/__init__.py, iterates builtin.BUILTIN_TOOLS)
              → ToolRegistry.register_tool_class(cls)
                  cls.get_tool_spec() → ToolSpec
                  cls.get_variants()  → Dict[str, Dict]
              stores: tool_classes, tool_specs, variants
                                    │
ToolConfig(name, variant, params) ─┘
  → ToolFactory.create_tool(cfg): resolve class → get variant config
    → merge {**variant_defaults, **cfg.parameters} → instantiate → tool.configure(merged)
  ⇒ configured AbstractTool
```

Registry storage shape (`registry/registry.py`, singleton):
```python
tool_classes: Dict[str, Type[AbstractTool]]        # tool_name -> class
tool_specs:   Dict[str, ToolSpec]                  # tool_name -> spec
variants:     Dict[str, Dict[str, Dict[str, Any]]] # tool_name -> variant -> config
```

## Key components
| Component | File | Role |
|---|---|---|
| `ToolRegistry` | `registry/registry.py` | Singleton storing classes, specs, variants |
| `ToolFactory` | `registry/factory.py` | Builds configured instances from `ToolConfig` (variant resolution + param merge) |
| `AbstractTool`, `ToolSpec` | rv-android-core (imported) | Base class + metadata model |
| Built-in tools | `builtin/*/tool.py` | 8 implementations, listed in `BUILTIN_TOOLS` (`builtin/__init__.py`) |

A built-in tool whose registration raises is logged at WARNING and skipped, so one broken tool never blocks the import. **External plugins** (`rvagent`, `aperv`) are not registered here and not by entry points: `_register_external_tools()` in `modules/rv-platform/src/rv_platform/__init__.py` imports them explicitly, which keeps rv-tools' only internal dependency at rv-android-core (INV-TOOL-12 makes that registration idempotent).

Authoring a tool = 4 abstract methods on an `AbstractTool` subclass: `get_tool_spec()` (classmethod → `ToolSpec`), `get_variants()` (classmethod → variant dict), `configure(config)`, `execute_tool_specific_logic(task, app)`.

## Built-in tools
| Tool | Description | Variants |
|---|---|---|
| Monkey | Pseudo-random event generation | default, fast, stress |
| DroidBot | Policy-based UI exploration | default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random |
| APE | CEGAR model abstraction | default, sata, bfs, dfs, random |
| FastBot | Reinforcement learning | default, conservative, aggressive, balanced |
| ARES | Docker-based systematic exploration (sibling container) | default |
| DroidMate | JAR-based research tool | default |
| Humanoid | DroidBot + Humanoid inference server (`-humanoid <url>`, default `humanoid_url` in `get_variants()`); stateless TF inference — one server shared across concurrent containers | default |
| QTesting | Docker-based Q-learning (sibling container) | default |

## Invariants
- **INV-TOOL-15 (Docker network)**: ARES/QTesting spawn sibling containers. Inside Docker (`/.dockerenv` present) the sibling uses `--network container:$(hostname)` to share the parent's netns; outside Docker, `--network host`.
- **INV-TOOL-20 / INV-TOOL-21 (variant-default pattern)**: L2 tool plugins (`builtin/`, plus `aperv-tool`, `rvagent-tool`) MUST NOT read environment variables. The canonical default for any per-tool URL/path/image lives in `get_variants()` (precedents: `ares/tool.py` and `qtesting/tool.py` `docker_image`). The factory merge `{**variant_defaults, **tool_config.parameters}` guarantees the key is present at `configure()` time — no `os.environ`. A required key is read as `config["key"]` so that its absence raises `KeyError` (INV-TOOL-21; `humanoid/tool.py` reads `humanoid_url` that way). `ares` and `qtesting` read `docker_image` with `config.get(..., "<literal>")`, repeating their variant default. L5 (`rv-experiment`) overrides via `ToolConfig.parameters` when an env var/CLI flag is set. Rationale: `rv-android/docs/adr/0001-env-var-pattern.md` (decision D8).

## Integration
Consumed by rv-experiment (tool selection) and rv-platform (task execution; `ToolFactory` in `Platform._load_tool`). `aperv-tool` and `rvagent-tool` declare rv-tools and subclass `AbstractTool`.

## Development
```bash
# From rv-android root
uv run pytest modules/rv-tools/tests/ --import-mode=importlib -o "addopts=" -v
```
Tests: `tests/builtin/test_<tool>_tool.py` (one per built-in), registry/factory tests at `tests/test_registry*.py`, `tests/test_factory*.py`, `tests/registry/test_tool_factory_parameters_channel.py` (variant-default merge), and `tests/test_builtin_registration.py`. `tests/helpers.py` is importable because `pyproject.toml` sets `pythonpath = ["tests"]`.
