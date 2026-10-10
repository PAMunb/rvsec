---
name: rv-security
description: >-
  Threat-model and security-review rv-android against its real trust boundaries: third-party
  APKs parsed on the host (apktool, dexlib2/instr-cli, GATOR), APKs running in the Docker
  emulator, screen text flowing into the LLM prompt and LLM output flowing into the tool-call
  parser and device actions, the LAN LLM endpoint, the supply chain (lib/ JARs, .mop specs,
  Python and Java dependencies, skills and MCPs) and the signing keystore and .env secrets.
  Reports findings anchored at file:line, each with evidence, impact, fix and a false-positive note.
  Use when reviewing a module, file or the whole system for security issues, or before exposing a
  component to new input (a new corpus, a new tool, a new LLM path).
  Do NOT use for general code review (use /rv-code-reviewer), bug fixes or feature work,
  dependency audits alone (run `uv run pip-audit --skip-editable` or /rv-verify), or
  restructuring (use /rv-refactor).
argument-hint: "[module-name | file-path | empty for the whole system]"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Security Analysis: $ARGUMENTS

You threat-model and review rv-android, a research platform that runs untrusted Android apps
under runtime verification. Severity is calibrated to how the platform is actually used: a
lab host, operators who are the researchers themselves, and third-party APKs as the main
attacker-controlled input.

## Target

`$ARGUMENTS` is the only substituted value. Resolve it once, at the start, into these names and
use them for the rest of the run:

```bash
ARG="$ARGUMENTS"
if [ -z "$ARG" ]; then
    TARGET_KIND=system; TARGET="rv-android"
    FILES=$(ls modules/*/src -d)                  # plus docker/ and lib/ for the boundaries
elif [ -d "modules/$ARG" ]; then
    TARGET_KIND=module; TARGET="$ARG"; MODULE="$ARG"
    FILES="modules/$MODULE/src"
elif [ -f "$ARG" ]; then
    TARGET_KIND=file; TARGET="$ARG"
    MODULE=$(echo "$ARG" | sed -n 's#^modules/\([^/]*\)/.*#\1#p')   # empty outside modules/
    FILES="$ARG"
else
    echo "ERROR: '$ARG' is neither a module under modules/ nor a file"; exit 1
fi
OUT_DIR="out/security/$(echo "$TARGET" | tr '/' '_')"
mkdir -p "$OUT_DIR"
```

Shell variables do not survive between Bash calls: write the resolved values literally in later
commands, or repeat this block at their start.

- **file**: analyze that file; read its callers only to establish where its inputs come from.
- **module**: select the relevant files (Phase 3, step 1) and analyze each; the module's other
  files are read only to trace data.
- **system**: model all boundaries in `checklists/trust-boundaries.md`, then review the files
  each boundary names.

Tool output goes to `$OUT_DIR` (under the git-ignored `out/`), never inside `modules/`.

## Supporting files: when to read each

| File | Read it |
|------|---------|
| `checklists/trust-boundaries.md` | In Phase 2, always. It lists each boundary, who controls its input, what the attacker cannot do, and the files where it is crossed. |
| `checklists/code-rules.md` | In Phase 3, before reviewing any file. It holds the rules (`RVS-*` IDs) that findings cite. |
| `checklists/design-guidelines.md` | In Phase 3, for system or module targets, to check boundary-level controls. Skip for a single file. |
| `checklists/survivability.md` | In Phase 5, only when a finding is high or critical and recovery matters (lost campaign data, a compromised host). |

## Threat taxonomy: STRIDE

Classify every threat with exactly one STRIDE category, the one closest to the attacker's goal:
**S**poofing, **T**ampering, **R**epudiation, **I**nformation disclosure, **D**enial of service,
**E**levation of privilege. Do not mix in other taxonomies.

## Scope discipline

Keep three contexts apart and say which one each finding belongs to; the same code can be
critical in one and irrelevant in another.

| Context | What runs | Typical input |
|---------|-----------|---------------|
| **Campaign** | `rv-experiment`/`rv-platform` in Docker: instrumentation, static analysis, emulator, tools, LLM | third-party APKs from the corpus |
| **Dev/CI** | `uv sync`, pytest, the Maven reactor, local scripts | repository content, dependencies |
| **Tests/examples** | `tests/`, fixtures, `apks_examples/` | developer-controlled |

For every input, record who controls it:

- **attacker**: the author of a third-party APK, and anything the app puts on screen or in its files;
- **operator**: the researcher running the campaign (CLI flags, compose files, filters, `.env`);
- **developer**: repository content (code, specs, `lib/` JARs, skills).

An issue that needs operator or developer control to exploit is not an attack; at most it is a
robustness or hygiene note. Downgrade it accordingly and say why.

---

## Workflow

```
PHASE 1  Scope and system model      components, entry points, contexts
PHASE 2  Boundaries and attacker     trust-boundaries.md; capabilities and non-capabilities
PHASE 3  Vulnerability assessment    relevant files, rv-analyze-file, code-rules.md, tools
PHASE 4  Assumption check-in         confirm deployment assumptions with the user
PHASE 5  Risk and report             likelihood x impact, findings, mitigations
```

## Phase 1: Scope and system model

1. List the components in scope and how they run (CLI, Docker container, Java subprocess,
   emulator, remote LLM server). Do not claim a component, flow or control without a file that
   shows it.
2. List the entry points: files and APKs read, subprocesses spawned, network endpoints called,
   parsers fed with external data.
3. Mark each entry point with its context (campaign, dev/CI, tests) and its controller
   (attacker, operator, developer).

## Phase 2: Trust boundaries and attacker model

Read `checklists/trust-boundaries.md`. For a module or file target, keep only the boundaries the
target touches. For each boundary in scope, record:

- what crosses it, through which channel, and the controls present (with `file:line`);
- the attacker's **capabilities** and **non-capabilities**. Non-capabilities keep severity
  honest: for instance, the APK author cannot choose CLI flags, cannot edit `.mop` specs and
  cannot reach the host filesystem except through what a parser or a bind mount exposes.

## Phase 3: Vulnerability assessment

1. **Pick the files.** For a file target, the file itself. For a module or the system, the files
   that cross a boundary:
   ```bash
   grep -rlE 'subprocess|Popen|os\.system|shell=True|Command\(|zipfile|extractall|tarfile|json\.loads|httpx|requests|openai|docker|adb|keystore|getenv|environ' $FILES
   ```
   Add the boundary files that `trust-boundaries.md` names for the target.
2. **Structure first (mandatory).** Before reviewing a selected file by hand, run
   `Skill: rv-analyze-file` with that file's path, once per file. For a module with many
   selected files, `Skill: rv-analyze-module` with `$MODULE` gives the overall structure first;
   the per-file analysis is still required for the files that cross a boundary.
3. **Apply the rules.** Read `checklists/code-rules.md` and check each selected file against the
   rules that match its boundary. Trace each external value from where it enters to where it is
   used (subprocess argument, filesystem path, prompt, device command).
4. **Run the tools** (all in the dev group; output goes to `$OUT_DIR`):
   ```bash
   # Python code patterns (bandit)
   uv run bandit -r $FILES -f json -o "$OUT_DIR/bandit.json"
   # Python dependencies with known vulnerabilities (needs network, no account; exit 1 = findings)
   uv run pip-audit --skip-editable -f json -o "$OUT_DIR/pip-audit.json"
   ```
   bandit findings are leads, not results: confirm each against the code and the controller of
   its input before reporting it. Optional, when the target reaches those layers:
   - Java side: the `rvsec` reactor runs SpotBugs and OWASP dependency-check under
     `mvn -Pcheck -o`, executed in `..` (the reactor root).
   - Docker images: `docker/SECURITY.md` describes Hadolint, Dockle and Trivy.
5. For system and module targets, check boundary-level controls with
   `checklists/design-guidelines.md`.

## Phase 4: Assumption check-in

Before writing the final report, list the 3 to 6 assumptions that most change the ranking and
ask the user 1 to 3 targeted questions with `AskUserQuestion`. Typical ones:

- Does any campaign host or container have a port reachable from outside the lab network?
- Does the signing keystore sign anything that leaves the lab (published APKs, store uploads)?
- Are corpus APKs ever obtained from sources other than the curated dataset?
- Do containers share the host's Docker socket in the campaign being assessed?

Wait for the answer. If `AskUserQuestion` is unavailable or the user does not answer, keep the
assumptions in the report as open, and mark the recommendations that depend on them as
conditional.

## Phase 5: Risk and report

Rate likelihood and impact as low, medium or high, each with a one-line reason; priority follows:

| | Low impact | Medium impact | High impact |
|---|---|---|---|
| **High likelihood** | medium | high | critical |
| **Medium likelihood** | low | medium | high |
| **Low likelihood** | low | low | medium |

Adjust for existing controls and state which assumption drives each ranking. Impact contained in
the disposable emulator is lower than impact on the host, the corpus or the results.

### Finding format

Report each finding in this form, ordered by priority:

```markdown
### RVS-F-001: <short title>
- **Rule**: <RVS-* rule from code-rules.md>   **STRIDE**: <one category>   **Priority**: critical/high/medium/low
- **Context**: campaign | dev/CI | tests      **Input controlled by**: attacker | operator | developer
- **Location**: `path/to/file.py:123` (function `name`)
- **Evidence**: the exact code or config lines, quoted (secrets redacted)
- **Impact**: what goes wrong, who can trigger it, and where the damage lands (emulator, host, results)
- **Fix**: the smallest change that removes the problem
- **Mitigation**: defense in depth, when the fix cannot land soon
- **False-positive note**: what to check to confirm or dismiss it
```

### Final report

Write the report to `$OUT_DIR/report.md` and return it:

```markdown
# Security Analysis: <TARGET>

## Executive summary            top risk themes in one paragraph
## Scope and assumptions        target kind, contexts covered, out-of-scope items,
                                confirmed and open assumptions (Phase 4)
## System model                 components; boundaries as arrows (APK -> apktool on host, ...)
                                with channel, controls and evidence
## Attacker model               capabilities; non-capabilities
## Findings                     RVS-F-* in the format above, by priority
## Accepted exceptions          overrides that applied, so nobody re-reports them
## Tool output                  bandit / pip-audit / optional Java and image scans, summarized
## Focus paths                  path | why it matters | related findings
```

---

## Overrides: accepted exceptions

An accepted exception is a deliberate, documented decision. Do not report it again as a finding;
list it under "Accepted exceptions" so the reader sees it was considered.

| Exception | Why it is accepted |
|-----------|--------------------|
| The LLM endpoint (SGLang/vLLM) speaks plain HTTP on the lab LAN without authentication | Lab-only service on a private network; TLS and auth add operating cost without changing the threat on that network. Report it only if the endpoint is exposed beyond the LAN. |
| An app forging or hiding logcat lines | Out of scope by decision; do not model or report it. |

When the code or project docs record another deliberate exception, honor it the same way and
cite where it is recorded. If a new exception seems warranted, propose documenting it; do not
argue against a recorded one.

## Rules

1. **Evidence anchored at `file:line`.** Every claim about a component, flow, control or
   weakness cites at least one location. No location, no claim.
2. **Calibrate by controller and context.** State who controls the input and where the damage
   lands; downgrade when exploitation needs operator or developer control.
3. **Never fix by switching protections off.** Disabling a timeout, a size limit, signature
   checks, container isolation or a test is not a fix; neither is widening permissions to make
   an error go away.
4. **Never print secrets.** Report a key or password by its location and kind, redacted.
5. **Few, verified findings.** Confirm each lead in the code before reporting it; drop what
   cannot be confirmed or move it to open questions.
6. **Read-only.** This skill reports; it does not edit code, configuration or containers, and it
   never starts or stops emulators.
