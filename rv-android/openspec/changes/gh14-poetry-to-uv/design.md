# Design: Migrate Build System from Poetry to uv

## Context

This design supports the gh14-poetry-to-uv change (GitHub Issue #14). The rv-android monorepo currently uses Poetry with 14 `pyproject.toml` files using the non-standard `[tool.poetry]` table and 14 individual `poetry.lock` files. The migration replaces this with uv's native workspace support, PEP 621 `[project]` tables, and a single `uv.lock` at the root.

The migration is mechanical but wide-reaching (~100+ files). No functional behavior changes — only the build toolchain and its references across the codebase (including runtime command strings in 2 tool files and 1 script that invoke `poetry run`). NFR01 (Modularity) from the PRD is the primary requirement affected: the system must remain organized as independent modules in a shared workspace with editable installation and immediate source change reflection.

Constraints:
- `droidbot` is an external dependency using `setup.py` (not a workspace member)
- `rvagent-tool` uses Poetry plugins (`[tool.poetry.plugins]`) for tool discovery
- `rv-instrumentation` includes non-Python assets (`assets/keystore.jks`)
- Docker images must continue building and running experiments

## Goals / Non-Goals

**Goals:**
- Replace Poetry with uv as the sole build/package manager
- Convert all `pyproject.toml` to PEP 621 (`[project]`) + PEP 735 (`[dependency-groups]`)
- Maintain all existing functionality (CLIs, plugin discovery, Docker builds)
- Eliminate all active references to Poetry (P3: no backward compatibility)
- Update all documentation to reference uv commands

**Non-Goals:**
- Changing Python application logic (the migration is limited to build-related command strings and documentation references)
- Adding new modules or features
- Optimizing dependency trees or removing unused packages
- Publishing any module to PyPI
- Migrating `droidbot` from `setup.py` to `pyproject.toml`

**Note on Python source changes**: Two tool implementation files (`droidbot/tool.py`, `humanoid/tool.py`) construct execution commands via `Command("poetry", cmd_args, ...)`. These are runtime build-system invocations, not application logic — they change to `Command("uv", ...)`. Similarly, `scripts/parallel_run.py` uses `["poetry", "run", "rv-experiment", ...]` to spawn subprocesses. Test files and docstrings with `poetry run` also change. No algorithmic or business logic is modified.

## Architecture

The workspace structure remains identical. Only the build metadata format changes:

```
rv-android/                          # Root workspace
├── pyproject.toml                   # [project] + [tool.uv.workspace] + [tool.uv.sources]
├── uv.lock                          # Single lock file (replaces 14 poetry.lock)
├── .venv/                           # Shared virtual environment (unchanged)
├── droidbot/                        # External path dep (setup.py, not a workspace member)
└── modules/
    ├── rv-android-core/pyproject.toml   # [project] + [build-system] hatchling
    ├── rv-agent/pyproject.toml          # [project] + [tool.uv.sources] for workspace deps
    ├── rvagent-tool/pyproject.toml      # [project.entry-points] for plugin discovery
    └── ... (11 more modules)
```

### Key Components

| Component | Before (Poetry) | After (uv) |
|-----------|-----------------|------------|
| Root metadata | `[tool.poetry]` with `package-mode = false` | `[project]` with `[tool.uv] package = false` |
| Workspace members | `path = "modules/X", develop = true` in root deps | `[tool.uv.workspace] members = ["modules/*"]` |
| Member inter-deps | `{path = "../X", develop = true}` | `[tool.uv.sources] X = { workspace = true }` |
| External path dep | `{path = "droidbot", develop = true}` | `[tool.uv.sources] droidbot = { path = "droidbot" }` |
| Dev dependencies | `[tool.poetry.group.dev.dependencies]` | `[dependency-groups] dev = [...]` |
| CLI scripts | `[tool.poetry.scripts]` | `[project.scripts]` |
| Plugin entry points | `[tool.poetry.plugins."rv_tools.plugins"]` | `[project.entry-points."rv_tools.plugins"]` |
| Build backend | `poetry-core` | `hatchling` |
| Src layout | `packages = [{include = "pkg", from = "src"}]` | `[tool.hatch.build.targets.wheel] packages = ["src/pkg"]` |
| Asset inclusion | `include = ["assets/*"]` | `[tool.hatch.build.targets.wheel.force-include]` |
| Version spec `^X.Y.Z` | Poetry caret operator | `>=X.Y.Z` (PEP 508, lock file pins exact) |
| Exact version `"3.4.0a1"` | Implicit exact | `==3.4.0a1` |
| Install command | `poetry install` | `uv sync` |
| Run command | `poetry run X` | `uv run X` |
| Lock file | 14 `poetry.lock` files | Single `uv.lock` at root |

## Mapping: Spec → Implementation

| Requirement | Implementation | Verification |
|-------------|---------------|--------------|
| NFR01: Modularity | `[tool.uv.workspace] members = ["modules/*"]` in root | `uv sync` exits 0, all 13 modules in `.venv/` |
| NFR01: Editable install | uv workspace default behavior (editable) | Modify source, verify immediate effect |
| NFR01: Single install | `uv sync` at root | Single command installs all modules |
| Plugin discovery (FR18-FR20) | `[project.entry-points."rv_tools.plugins"]` | `uv run python -c "from importlib.metadata import entry_points; ..."` |
| CLI entry points (FR15, FR07, FR21) | `[project.scripts]` in each module | `uv run rv-experiment --help`, etc. |

## Configuration Format

### Root pyproject.toml

```toml
[project]
name = "rv-android"
version = "0.1.0"
description = "RV-Android Modular Platform Workspace"
authors = [{name = "RV-Android Team"}]
requires-python = ">=3.12"
dependencies = [
    # Workspace members (resolved via [tool.uv.sources])
    "rv-android-core",
    "rv-monitor-generator",
    # ... all 13 members ...
    # External workspace dependencies
    "droidbot",
    # Shared third-party
    "requests>=2.32.0",
    "androguard==3.4.0a1",
    # ...
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "black>=24.0.0",
    # ...
]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["modules/*"]

[tool.uv.sources]
rv-android-core = { workspace = true }
rv-monitor-generator = { workspace = true }
# ... all 13 members ...
droidbot = { path = "droidbot" }
```

### Module pyproject.toml (example: rv-agent)

```toml
[project]
name = "rv-agent"
version = "0.1.0"
description = "Autonomous Android testing agent with LangChain and SGLang"
authors = [{name = "RV-Android Team"}]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "rv-android-core",
    "rv-screen-parser",
    "langchain>=0.3",
    # ...
]

[project.scripts]
rv-agent = "rv_agent.cli.main:cli"

[dependency-groups]
dev = ["pytest>=8.0.0", "pytest-cov>=7.0.0", "hypothesis>=6.100.2"]

[tool.uv.sources]
rv-android-core = { workspace = true }
rv-screen-parser = { workspace = true }
rv-uiautomator = { workspace = true }
rv-static-analysis = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rv_agent"]
```

### rvagent-tool pyproject.toml (plugin entry points)

```toml
[project.entry-points."rv_tools.plugins"]
rvagent = "rvagent_tool.tools.rvagent.tool:RVAgentTool"
```

### rv-instrumentation pyproject.toml (asset inclusion)

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/rv_instrumentation"]

[tool.hatch.build.targets.wheel.force-include]
"assets" = "rv_instrumentation/assets"
```

## Data Flow

```
Developer runs `uv sync`
    → uv reads root pyproject.toml
    → uv discovers workspace members via [tool.uv.workspace] members
    → uv reads each member's pyproject.toml
    → uv resolves all dependencies (cross-member + third-party)
    → uv writes single uv.lock at root
    → uv installs all packages into .venv/ (members in editable mode)

Developer runs `uv run rv-experiment run --tools monkey`
    → uv activates .venv/
    → uv executes rv-experiment entry point
    → Same behavior as before (only the invocation wrapper changes)
```

## Decisions

### D1: hatchling as build backend

**Choice**: `hatchling` over `flit-core`, `setuptools`, or `uv_build`.

**Rationale**: hatchling is the most widely adopted PEP 621 build backend, has first-class support for src layouts via `[tool.hatch.build.targets.wheel]`, supports force-include for non-Python assets (needed by rv-instrumentation), and is recommended by the Python Packaging Authority. `flit-core` lacks asset inclusion support. `setuptools` requires `setup.cfg` or `setup.py` for complex cases. `uv_build` is experimental.

### D2: `>=X.Y.Z` version specifiers (no upper bounds)

**Choice**: Convert Poetry `^X.Y.Z` to simple `>=X.Y.Z` without upper bounds.

**Rationale**: The lock file pins exact versions for reproducibility. Upper bounds in dependency specs are widely considered harmful in the Python ecosystem (see "Why I Don't Like Upper Bound Version Constraints" by Henry Schreiner). Since this project never publishes to PyPI, the only resolution context is the workspace itself, where the lock file provides full reproducibility.

### D3: Single root uv.lock replaces 14 poetry.lock files

**Choice**: Delete all per-module `poetry.lock` files. uv uses a single `uv.lock` at the workspace root.

**Rationale**: This is how uv workspaces work — there is no per-member lock file option. This is actually an improvement: a single lock file ensures all modules use consistent dependency versions, eliminating the version skew risk inherent in 14 separate lock files.

### D4: droidbot as path dependency (not workspace member)

**Choice**: Keep `droidbot` outside the workspace as a path dependency in `[tool.uv.sources]`.

**Rationale**: droidbot uses `setup.py` (not `pyproject.toml`) and is a third-party fork. Making it a workspace member would require converting it to PEP 621, which is out of scope. uv handles legacy `setup.py` packages via path dependencies.

### D5: Docker uv installation

**Choice**: Install uv via `curl` single-binary download in Docker base image.

**Rationale**: uv provides a standalone binary (~30MB) that can be downloaded with `curl -LsSf https://astral.sh/uv/install.sh | sh`. This is simpler and faster than Poetry's installer (`curl -sSL https://install.python-poetry.org | python3 -`), and doesn't require a Python interpreter to bootstrap.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `uv sync` fails | Invalid pyproject.toml syntax | Fix syntax, re-run | Check uv error message for specific field |
| Module not found after sync | Missing `[tool.uv.sources]` entry | Add workspace source | Verify member is in `modules/` glob |
| Plugin not discovered | Wrong `[project.entry-points]` format | Fix entry-points table | Compare with Poetry plugins format |
| Docker build fails | Missing uv binary or wrong commands | Fix Dockerfile | Verify uv install script URL |
| droidbot import fails | Path dependency not resolved | Check `[tool.uv.sources]` path | Verify `droidbot/setup.py` exists |

## Risks / Trade-offs

- **[Wide blast radius]** → 80+ files touched in single change. Mitigation: subagent orchestration with group-by-group execution, final grep verification for dangling references.
- **[droidbot compatibility]** → uv may handle `setup.py` path deps differently than Poetry. Mitigation: test `uv sync` early in implementation; if issues arise, create a minimal `pyproject.toml` for droidbot.
- **[hatchling asset inclusion]** → `force-include` behavior for rv-instrumentation assets may differ from Poetry `include`. Mitigation: verify `assets/keystore.jks` is accessible after editable install.
- **[Docker cache invalidation]** → Changing from poetry.lock to uv.lock invalidates Docker layer cache. Mitigation: acceptable one-time cost; subsequent builds benefit from uv's faster resolution.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Build | All modules install | `uv sync` exits 0 | 1 |
| CLI | All entry points respond | `uv run <cmd> --help` for 5 CLIs | 5 |
| Plugin | rvagent tool discovery | `uv run python -c "..."` entry_points check | 1 |
| Unit | Existing tests pass | `uv run pytest modules/ -m "not slow"` | All existing |
| Docker | Images build | `docker build` for 3 images | 3 |
| Dangling | No poetry refs remain | `grep -ri "poetry"` on active files | 1 |

## Migration Plan

1. Convert all 14 `pyproject.toml` files (root first, then modules)
2. Delete all 14 `poetry.lock` files
3. Run `uv sync` to generate `uv.lock` and validate
4. Update Python source code with runtime `poetry` references (2 tool files, 1 test, 2 docstrings)
5. Update Python scripts in `scripts/` (5 files with `poetry run` invocations)
6. Update shell scripts (`install.sh`, `test.sh`, `lock.sh`, `clean.sh`, 4 phase scripts)
7. Update Docker files (3 Dockerfiles + 1 entrypoint)
8. Update root documentation (CLAUDE.md, README.md, project-info.md, .gitignore, architecture doc)
9. Update module documentation (15 READMEs, 12 CLAUDE.md files, 3 architecture docs, 6 rv-agent-validation docs)
10. Update planning docs (WORKFLOW.md, PRD.md, 2 planning docs)
11. Update Claude Code skills and agents (AGENTS.md + 34 skill files across 20 skill folders)
12. Update OpenSpec specs and changes (2 main specs + 3 gh9-docker-calibration files)
13. Verify AC1-AC5 from the proposal
14. Single commit with all changes (one consistent state per P3)

**Rollback**: If `uv sync` fails or tests break, restore `pyproject.toml` files from git (`git checkout -- "*/pyproject.toml"`). Poetry lock files are still in git history. No data loss risk.

## Implementation Strategy (Subagent Orchestration)

Given 100+ files across 14 groups, use subagent orchestration per WORKFLOW.md Section 5:

| Subagent | Group | Files | Dependency |
|----------|-------|-------|------------|
| SA1 | pyproject.toml files | 14 | None (first) |
| SA2 | Delete locks + uv sync | 14 + 1 | After SA1 |
| SA3 | Python source + scripts + shell scripts | 18 | After SA2 |
| SA4 | Docker files | 4 | After SA2 |
| SA5 | Root docs + module READMEs + module docs | 30 | After SA2 |
| SA6 | Module CLAUDE.md + architecture docs | 15 | After SA2 |
| SA7 | Planning docs + skills + agents | 40 | After SA2 |
| SA8 | OpenSpec specs + changes | 5 | After SA2 |
| Verify | AC1-AC5 | — | After SA3-SA8 |

SA3-SA8 are independent and can run in parallel.

## Open Questions

None. All key decisions are resolved in this design.
