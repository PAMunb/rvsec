## Why

GitHub Issue: #14

The rv-android monorepo uses Poetry as its build system and package manager across 13 modules plus a root workspace. Poetry's dependency resolution is slow for workspaces of this size (minutes per `poetry install`), its `[tool.poetry]` table is non-standard (not PEP 621), and maintaining pyenv + poetry as separate tools adds unnecessary toolchain complexity. The project has never published to PyPI and has no plans to do so, removing the main reason Poetry was retained. uv provides 10-100x faster resolution, native workspace support, PEP 621 compliance (`[project]` table), and a single binary replacing both pyenv and poetry.

## What Changes

- **BREAKING**: Replace all 14 `pyproject.toml` files from `[tool.poetry.*]` format to PEP 621 `[project]` + `[tool.uv.*]` format with `hatchling` build backend
- **BREAKING**: Delete all 14 `poetry.lock` files, replace with single `uv.lock` at root
- **BREAKING**: All CLI invocations change from `poetry run <cmd>` to `uv run <cmd>`
- **BREAKING**: All install commands change from `poetry install` to `uv sync`
- Update `modules/install.sh` and `modules/test.sh` to use `uv` commands
- Update 3 Dockerfiles and 1 entrypoint to install and use `uv` instead of Poetry
- Update all documentation (CLAUDE.md, README.md, 12 module READMEs, module CLAUDE.md files, project-info.md, WORKFLOW.md, PRD.md, planning docs, skills) to reference `uv`
- Convert `[tool.poetry.plugins]` to `[project.entry-points]` (PEP 621 standard)
- Convert `[tool.poetry.scripts]` to `[project.scripts]` (PEP 621 standard)
- Convert `[tool.poetry.group.dev.dependencies]` to `[dependency-groups]` (PEP 735)

## Capabilities

### New Capabilities

None. This is a build infrastructure migration, not a feature change. No new spec domains are introduced.

### Modified Capabilities

- `experiment`: Scenario at line 409 references `poetry run rv-experiment run` which changes to `uv run rv-experiment run`. Docker entrypoint command format changes.
- `tools`: Tool execution description at line 259 references "poetry scripts" and line 266 shows `poetry run droidbot` command. These change to `uv run` equivalents.

Note: NFR01 (Modularity) in the PRD describes "independent Poetry modules with `develop = true` in a shared workspace". This changes to "independent uv workspace members installed in editable mode". The PRD itself will be updated but does not have a corresponding spec file — it is updated directly.

## Impact

- **All 13 modules + root**: `pyproject.toml` format changes (mechanical but comprehensive)
- **Build system dependency**: `poetry-core` build backend replaced by `hatchling`
- **Lock file**: Single `uv.lock` at root replaces 14 individual `poetry.lock` files
- **CI/Docker pipeline**: Dockerfiles need uv binary instead of Poetry installer
- **Developer workflow**: All `poetry` CLI commands replaced with `uv` equivalents
- **Shell scripts**: `install.sh` and `test.sh` reference Poetry commands
- **Documentation**: 40+ files reference Poetry commands or conventions
- **Skills/agents**: 6+ skill files reference `poetry run pytest` or similar
- **OpenSpec changes**: In-progress change `gh9-docker-calibration` references Poetry commands
- **External dependency**: `droidbot` (setup.py-based, outside `modules/`) handled via `[tool.uv.sources]` path dependency
