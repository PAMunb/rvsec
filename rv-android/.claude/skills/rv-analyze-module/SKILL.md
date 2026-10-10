---
name: rv-analyze-module
description: >-
  Analyze the architecture of one uv workspace module: size relative to the workspace
  (radon LOC/LLOC/SLOC, share and z-score), dependencies, complexity and dead code via
  sub-skills, and four modeling perspectives (context, interaction, structural, behavioral).
  Use when onboarding to a module, before a module-level refactor or split, or to feed
  module documentation.
  Do NOT use for: a single file (use /rv-analyze-file), workspace-wide dependency mapping
  (use /rv-analyze-dependencies), the impact of one planned change (use /rv-impact-analyzer),
  or making changes (use /rv-refactor).
argument-hint: "<module-name>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, Skill
---

# Analyze Module: $ARGUMENTS

All commands run from the repository root.

## Steps

### Step 0: Check the cache

The cache key is the last commit touching the module, and it is only valid when the
module's sources and `pyproject.toml` have no uncommitted changes:
```bash
S="modules/$ARGUMENTS"
git status --porcelain -uall -- "$S" | grep -E '(/src/.*\.py|pyproject\.toml)$' | head -3
git log -1 --format=%h -- "$S"
```
- Any status line printed: cache miss, and skip Step 5.
- Otherwise search `mcp__memory__search_nodes` for `"analysis:module:$ARGUMENTS"` and compare
  its `git_hash`. Equal: return the cached report and STOP.
- If the `mcp__memory` tools are unavailable or fail, treat it as a miss and continue.

### Step 1: Read reference and gather metadata

Read `reference.md` from this skill's directory (modeling checklists and sizing rules).

Metadata, one call:
```bash
M=modules/$ARGUMENTS
echo "=== PYPROJECT ===" && cat $M/pyproject.toml
echo "=== FILES ===" && echo "src: $(find $M/src -name '*.py' ! -path '*__pycache__*' | wc -l)  tests: $(find $M/tests -name '*.py' ! -path '*__pycache__*' 2>/dev/null | wc -l)"
```

Size against the workspace, one call (radon is in the dev group; LLOC ≈ statements, the
sizing unit; the module list comes from the workspace definition, not a name prefix):
```bash
for src in $(python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py --src-dirs); do
  m=$(basename "$(dirname "$src")")
  uv run --no-sync radon raw -s "$src" | awk -v m="$m" '/\*\* Total \*\*/{t=1} t&&/ LOC:/{loc=$2} t&&/ LLOC:/{ll=$2} t&&/ SLOC:/{sl=$2} END{print m, loc, ll, sl}'
done | awk -v target="$ARGUMENTS" '{m[NR]=$1; loc[NR]=$2; ll[NR]=$3; sl[NR]=$4; tot+=$3} END {
  n=NR; mean=tot/n; for(i=1;i<=n;i++) ss+=(ll[i]-mean)^2; sd=sqrt(ss/(n-1))
  printf "%-28s %7s %7s %7s %6s %6s\n","module","LOC","LLOC","SLOC","%LLOC","z"
  for(i=1;i<=n;i++){z=(ll[i]-mean)/sd; printf "%-28s %7d %7d %7d %5.1f%% %6.2f%s%s\n",m[i],loc[i],ll[i],sl[i],100*ll[i]/tot,z,(z>2?"  >2σ":""),(m[i]==target?"  <-- target":"")}
  printf "workspace LLOC=%d  n=%d  mean=%.0f  sd=%.0f\n",tot,n,mean,sd }'
```
Interpret with **Module Sizing** in `reference.md`.

### Step 2: Invoke sub-skills

Use the Skill tool for each (each has its own cache).

1. `skill="rv-analyze-dependencies", args="$ARGUMENTS"`
2. `skill="rv-analyze-complexity", args="$ARGUMENTS"`
3. `skill="rv-analyze-dead-code", args="$ARGUMENTS"`

### Step 3: Map directory structure

Glob `modules/$ARGUMENTS/src/**/*.py`. Identify architectural packages (domain/, services/,
cli/, …), key components and their purposes, and correlate with the sub-skill hotspots.

### Step 4: Apply the four modeling perspectives

Use the `reference.md` checklists: **Context** (boundaries, adjacent modules, external systems,
triggers), **Interaction** (actors, use cases, key sequences), **Structural** (key classes,
hierarchies, patterns, coupling assessment), **Behavioral** (data- vs event-driven, flows,
scenarios). Spend depth where the module needs it.

### Step 5: Persist to MCP memory

Skip when Step 0 found uncommitted changes. Otherwise create (or delete + create) entity
`"analysis:module:$ARGUMENTS"`, type `module-analysis`, observations `git_hash: <hash>`,
`date: YYYY-MM-DD`, `summary: files=X, LLOC=Y, share=P%, z=Z, classes=C, hotspots=W, issues=V`,
`details: <full report>`. If MCP fails, skip caching and still output the report.

## Output Format

```markdown
## Module Analysis: <module-name>

**Files**: X src / T tests | **LOC / LLOC / SLOC**: a / b / c | **Workspace share**: P% (z = Z) | **Workspace deps**: W

### Purpose
[One paragraph]

### Size in the Workspace
[Target row of the sizing table, mean/sd, and the reading per reference.md]

### Directory Structure
(source tree with architectural patterns noted)

### Key Components
| Component | Purpose | LLOC | Complexity |
|-----------|---------|------|------------|

### Sub-Skill Results
- **Dependencies**: [summary]
- **Complexity**: [summary]
- **Dead Code**: [summary]

### Context Model
### Interaction Model
### Structural Model
### Behavioral Model

### Recommendations
1. **[priority]**: [specific action]
```
