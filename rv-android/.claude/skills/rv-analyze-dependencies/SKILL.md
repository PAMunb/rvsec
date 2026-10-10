---
name: rv-analyze-dependencies
description: >-
  Map declared (pyproject.toml) and actual (import) dependencies between the uv workspace
  modules, check them against the allowed layer matrix and the Stable Dependencies Principle,
  and classify the coupling imports do not show: data contracts across languages (JavaMOP
  descriptor JSON, GATOR *.apk.json, .mop files), process boundaries and co-change.
  Use when auditing module boundaries, before moving code between modules, or when a
  module's dependency list looks wrong.
  Do NOT use for fixing dependencies (use /rv-refactor), a full single-module review
  (use /rv-analyze-module), or the ripple effect of one planned change (use /rv-impact-analyzer).
argument-hint: "<module-name or empty for all>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze Dependencies: $ARGUMENTS

> **Scope**: all workspace modules when $ARGUMENTS is empty, otherwise the edges touching
> that module. Metrics are always computed on the whole workspace (Ca needs every module).
> All commands run from the repository root.

## Steps

### Step 0: Check the cache

The cache key is the last commit touching the scope's sources or the workspace definition,
and it is only valid when those have no uncommitted changes:
```bash
S="modules/$ARGUMENTS"
git status --porcelain -uall -- "$S" pyproject.toml | grep -E '(/src/.*\.py|pyproject\.toml)$' | head -3
git log -1 --format=%h -- "$S" pyproject.toml
```
- Any status line printed (uncommitted source or pyproject change): cache miss, and skip Step 6.
- Otherwise search `mcp__memory__search_nodes` for `"analysis:dependencies:$ARGUMENTS"`
  (`"analysis:dependencies:workspace"` when empty) and compare its `git_hash`. Equal: return
  the cached report and STOP.
- If the `mcp__memory` tools are unavailable or fail, treat it as a miss and continue.

### Step 1: Read the reference

Read `reference.md` sections **Layers and Allowed Matrix** and **Health Metrics**. Read
**Coupling Beyond Imports** when you reach Step 4.

### Step 2: Extract declared and actual dependencies

One call. The script derives modules and import package names from the workspace
definition in the root `pyproject.toml`, so `aperv_tool`/`rvagent_tool` are covered:
```bash
python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py $ARGUMENTS
```
It prints, per module, `declared` / `imported` / `undeclared` / `unused` (imports read from
`src/` with `ast`, tagged `top`, `lazy` = inside a function, `type` = under `TYPE_CHECKING`),
then Ca, Ce, I and depth on the declared graph, the SDP check, and cycles over declared plus
imported edges.

### Step 3: Analyze the import graph

- **Undeclared import**: a hidden dependency. A `lazy` one is usually deliberate (guarded
  plugin registration, optional feature); say so, but it is still a finding.
- **Unused declaration**: coupling in the lock file with no code behind it.
- **Matrix violation**: an edge (declared or imported) absent from its row in the matrix.
- **SDP violation**: `I(dependency) >= I(dependent)` — the stable side depends on the less
  stable one. Report the pair with both I values; equal I is a weaker finding than greater.
- **Cycle**: classify with the reference (type-only, direct, transitive) using the tags.
- **Depth**: from the metrics table, against the depth thresholds.

### Step 4: Coupling beyond imports

The import graph misses the strongest couplings in this system: Python modules exchanging
files with each other and with the Java reactor. Run both in one call:
```bash
SRCS=$(python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py --src-dirs)
echo "## DATA ARTIFACTS"; grep -rnoE --include='*.py' '\.apk\.json|\.mop\b|\.rvm\b|descriptor|\.jar\b' $SRCS | awk -F: '!seen[$1 FS $3]++ {s[$1]=s[$1] " " $3} END {for (f in s) print f ":" s[f]}' | sort
echo "## PROCESS / NETWORK"; grep -rnoE --include='*.py' 'subprocess\.[a-z_]+|create_subprocess_exec|execute_command\(|Command\(|ChatOpenAI|base_url' $SRCS | awk -F: '!seen[$1 FS $3]++ {s[$1]=s[$1] " " $3} END {for (f in s) print f ":" s[f]}' | sort
bash .claude/skills/rv-analyze-dependencies/scripts/cochange.sh
```
Then, following **Coupling Beyond Imports** in `reference.md`: open the producer and the
consumer of each artifact (the known contracts are listed there; confirm each one still
holds and add any new one), and classify every relation — import edges with a finding from
Step 3, data contracts, and co-change pairs with no edge at all — by strength, distance and
volatility, then diagnose it with the table.

### Step 5: Report

Use the output format below. Every number comes from a command output of this run.

### Step 6: Persist to MCP memory

Skip when Step 0 found uncommitted changes. Otherwise create (or delete + create) entity
`"analysis:dependencies:$ARGUMENTS"` (or `"analysis:dependencies:workspace"`), type
`module-dependency-analysis`, observations `git_hash: <hash>`, `date: YYYY-MM-DD`,
`summary: modules=X, violations=Y, sdp=S, cycles=Z, undeclared=U, critical_couplings=C`,
`details: <full report>`. If MCP fails, skip caching and still output the report.

## Output Format

```markdown
## Dependency Analysis: <scope>

**Modules**: X | **Violations**: Y | **SDP**: S | **Cycles**: Z | **Max Depth**: W

### Dependency Matrix

| Module | Layer | Declared | Imported | Ca | Ce | I | Depth |
|--------|-------|----------|----------|----|----|---|-------|

### Import-Graph Issues

| # | Type | Edge | Severity | Notes |
|---|------|------|----------|-------|
| 1 | Undeclared (lazy) | rv-platform → aperv-tool | Medium | guarded registration in `rv_platform/__init__.py` |
| 2 | SDP | rvagent-tool (0.75) → rv-agent (0.80) | Low | |

### Coupling Beyond Imports

| Relation | Kind | Strength | Distance | Volatility | Diagnosis |
|----------|------|----------|----------|------------|-----------|
| java:rvsec-gator → rv-static-analysis, aperv-tool | `*.apk.json` | model | process+language | high (14 co-changes, 64%) | critical |

### Dependency Graph (ASCII)

(layers top to bottom; data contracts drawn as dashed edges)

### Recommendations

1. **[issue]**: [specific action]
```
