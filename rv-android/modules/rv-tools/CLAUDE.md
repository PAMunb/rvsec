# CLAUDE.md - rv-tools

## Purpose
Centralized tool registry and plugin system for Android app-testing tools. Manages tool discovery, registration, instantiation, and variant-based configuration. The top-level `rv-android/CLAUDE.md` owns the Factory/Registry pattern summary, uv/pytest/env conventions, and module map — not repeated here.

## Registration + creation flow
```
Module import → _register_builtin_tools()
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
| Built-in tools | `builtin/*/tool.py` | 8 implementations |

Authoring a tool = 4 methods on an `AbstractTool` subclass: `get_tool_spec()` (classmethod → `ToolSpec`), `get_variants()` (classmethod → variant dict), `configure(config)`, `execute_tool_specific_logic(task, app)`.

## Built-in tools
| Tool | Description | Variants |
|---|---|---|
| Monkey | Pseudo-random event generation | default, fast, stress |
| DroidBot | Policy-based UI exploration | default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random |
| APE | CEGAR model abstraction | default, sata, bfs, dfs, random |
| FastBot | Reinforcement learning | default, conservative, aggressive, balanced, model_based |
| ARES | Docker-based systematic exploration (sibling container) | default |
| DroidMate | JAR-based research tool | default |
| Humanoid | DroidBot + Humanoid inference server (`-humanoid <url>`); stateless TF inference — one server shared across concurrent containers (gh55) | default |
| QTesting | Docker-based Q-learning (sibling container) | default |

## Invariants
- **INV-TOOL-15 (Docker network)**: ARES/QTesting spawn sibling containers. Inside Docker (`/.dockerenv` present) the sibling uses `--network container:$(hostname)` to share the parent's netns; outside Docker, `--network host`.
- **INV-TOOL-20 / INV-TOOL-25 (variant-default pattern, gh55)**: L2 tool plugins (`builtin/`, plus `aperv-tool`, `rvagent-tool`) MUST NOT read environment variables. The canonical default for any per-tool URL/path/image lives in `get_variants()` (precedents: `ares/tool.py` and `qtesting/tool.py` `docker_image`). The factory merge `{**variant_defaults, **tool_config.parameters}` guarantees the key is present at `configure()` time — no `os.environ`, no literal fallback. L5 (`rv-experiment`) overrides via `ToolConfig.parameters` when an env var/CLI flag is set. Rationale: `rv-android/docs/adr/0001-env-var-pattern.md` (decision D8).

## Integration
Consumed by rv-experiment (tool selection) and rv-platform (task execution) — described in the top-level CLAUDE.md.
