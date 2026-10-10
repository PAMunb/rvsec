# Trust Boundaries of rv-android

Read in Phase 2. Each boundary lists who controls the input, what the attacker can and cannot do,
where the boundary is crossed in the code, and what to check. The paths are starting points:
confirm each one with grep before citing it, and cite the exact `file:line` you read.

The attacker throughout is the **author of a third-party APK** from the corpus. Operators (the
researchers running campaigns) and developers (repository content) are trusted; issues that need
their control are hygiene notes, not attacks.

---

## B1. Third-party APK → parsers on the host

**What crosses**: APK files (ZIP containers with DEX, manifest, resources, native libraries).
**Controlled by**: attacker (content), operator (which APKs, through `--apks-dir` and filters).
**Context**: campaign (instrumentation and static analysis run on the host or in a container).

Where it is crossed:
- dexlib2 instrumentation: `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` runs `java -jar` on `instr-cli.jar`.
- AspectJ instrumentation: `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py` (dex2jar, ajc, d8, zipalign, apksigner; `utils.unzip` on JARs).
- Static analysis (GATOR, which decodes the APK with apktool): `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`.
- ZIP extraction helper: `modules/rv-android-core/src/rv_android_core/util/utils.py` (`unzip`).
- Subprocess wrapper: `modules/rv-android-core/src/rv_android_core/commands/command.py` (`Command`).

Attacker can: craft archive entry names (`../`, absolute paths, symlinks), huge or deeply nested
resources, malformed DEX or manifest data, very large method counts, inputs that make a
decoder loop or run for hours.
Attacker cannot: choose the command line, the JVM options or the output directories; replace the
JARs in `lib/`; read the parser's output beyond what is written into the instrumented APK.

Check:
- [ ] Every Java subprocess has a timeout and a bounded heap (`-Xmx`), and a timeout kills the whole process tree.
- [ ] Archive extraction stays inside its target (RVS-ARC-001): `tarfile` uses `filter="data"`, external extractors and hand-built paths are checked; Python `zipfile` already sanitizes member names, so only size and member count matter there.
- [ ] Output and temporary directories are per-APK and derived from operator-controlled names, not from names read inside the APK.
- [ ] A parser failure on one APK fails that task and leaves the campaign running (no partial output treated as success without a flag).
- [ ] The total heap of parallel JVMs fits the host memory.

STRIDE leads: D (memory, CPU, loops), T (writes outside the work directory), E (code execution in a parser).

---

## B2. APK → emulator in Docker

**What crosses**: the instrumented APK, installed and exercised in an Android emulator inside a
campaign container.
**Controlled by**: attacker (app behavior), operator (compose files, mounts, ports, image).
**Context**: campaign.

Where it is crossed:
- Emulator lifecycle: `modules/rv-android-core/src/rv_android_core/util/android/emulator_manager.py`, `android.py`.
- Campaign containers: `docker/docker-compose*.yml`, images under `docker/`.
- Tools that spawn sibling containers through the Docker socket: `modules/rv-tools/src/rv_tools/builtin/ares/tool.py` (and the composes that mount `/var/run/docker.sock`).
- Tools that reach the host from the emulator (`10.0.2.2`): `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`.

Attacker can: run arbitrary code inside the emulator; open network connections from the emulator
(to the internet, to the host through `10.0.2.2`, to services on the lab LAN); fill the device
storage; crash or hang the app and the emulator.
Attacker cannot: leave the emulator without an emulator or KVM escape; read host files that are
not mounted; reach the adb server unless its port is exposed on a network the emulator can reach.

Check:
- [ ] Bind mounts of corpus and inputs are read-only (`:ro`); writable mounts are limited to the results directory of that container.
- [ ] No `privileged: true`; devices limited to `/dev/kvm`.
- [ ] A mounted `/var/run/docker.sock` is root-equivalent on the host. Record which composes mount it and which code uses it; whatever the attacker can influence there (image names, arguments) matters.
- [ ] No `ports:` publishing adb (5037, 5554/5555) or other services on interfaces beyond localhost.
- [ ] Outbound network from the emulator: what it can reach on the LAN (the LLM endpoint, other hosts). Ask the user whether this is intended (Phase 4).
- [ ] Restart policy does not resurrect a container over finished results.

STRIDE leads: E (escape through the Docker socket or a writable mount), T (writes into results or corpus), I (reaching LAN services), D (exhausting host resources).

---

## B3. Screen text → LLM prompt → device action (rv-agent)

**What crosses**: UI hierarchy text, screenshots and labels drawn by the app, placed into the
prompt; the model's chosen action then runs on the device.
**Controlled by**: attacker (everything on screen).
**Context**: campaign with LLM-driven tools.

Where it is crossed:
- Prompt assembly and LLM call: `modules/rv-agent/src/rv_agent/agent/nodes/llm_node.py`, `modules/rv-agent/src/rv_agent/llm/llm_client.py`.
- Action execution on the device: `modules/rv-agent/src/rv_agent/agent/device_interface.py`, `modules/rv-uiautomator/src/rv_uiautomator/adapter/uiautomator2.py`.

Attacker can: put instructions on screen that steer the model (prompt injection), make the model
type chosen text, click chosen elements, or stop exploring.
Attacker cannot: make the model act outside the action set the code executes; reach the host
unless an action is turned into a host-side command.

Check:
- [ ] The executed actions are a fixed set (click, long click, set text, swipe, back...) mapped by code; the model never supplies a command line.
- [ ] Text typed on the device goes through an API that does not pass through a shell, or is quoted for the device shell (see RVS-CMD-002).
- [ ] The effect of a steered action stays inside the emulator. Prompt injection that only changes exploration choices is a measurement-validity concern, not a host compromise: rate it accordingly.

STRIDE leads: T (steered actions), E (only if an action reaches a host or device shell unquoted).

---

## B4. LLM output → tool-call parser

**What crosses**: model text, parsed as native tool calls or as embedded JSON/XML.
**Controlled by**: attacker indirectly (through B3); the model itself is not trusted to be well formed.
**Context**: campaign.

Where it is crossed: `modules/rv-agent/src/rv_agent/llm/tools/tool_call_parser.py`, `sglang_tools.py`.

Check:
- [ ] Parsing uses `json.loads` or a strict pattern, never `eval`, `exec`, `pickle` or `yaml.load` without a safe loader.
- [ ] Parsed arguments are validated (types, ranges, coordinates within the screen, action names in the allowed set) before they reach the device.
- [ ] Regex patterns over model text cannot backtrack catastrophically on long outputs.
- [ ] A parse failure falls back to a safe default action, not to an exception that kills the task silently.

STRIDE leads: T, D.

---

## B5. Host ↔ LLM endpoint (SGLang/vLLM)

**What crosses**: prompts (screen content) and model responses, over HTTP on the lab LAN.
**Controlled by**: operator (endpoint URL, model); responses influenced by the attacker through B3.
**Context**: campaign.

Where it is crossed: `modules/rv-agent/src/rv_agent/config/agent_config.py` (default URL),
`modules/rv-agent/src/rv_agent/llm/llm_client.py`, `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` (`llm_url`).

Plain HTTP without authentication on the LAN is an accepted exception (see Overrides in
`SKILL.md`). Check instead:
- [ ] Requests have timeouts; an unreachable endpoint fails or degrades the task, it does not hang the campaign.
- [ ] The endpoint is not published beyond the lab network (ask in Phase 4).

---

## B6. Supply chain

**What crosses**: code and data the platform executes but did not produce.
**Controlled by**: developer (what is committed), third parties (upstream).
**Context**: dev/CI and campaign.

| Item | Where | How to check |
|------|-------|--------------|
| Java tools | `lib/` (apktool, dex2jar, gator, frame-computer, ...) | Built from the `rvsec` reactor or pinned; provenance recorded. On the Java side, `mvn -Pcheck -o` in `..` runs SpotBugs and OWASP dependency-check. |
| Specifications | `.mop` sets under `$RVSEC_HOME` | Developer-controlled; they generate code woven into the APK. |
| Python dependencies | `pyproject.toml`, `uv.lock` | `uv run pip-audit --skip-editable` (workspace packages are editable and not on PyPI). |
| Docker images | `docker/` | Pinned bases; Hadolint, Dockle, Trivy as in `docker/SECURITY.md`. |
| Skills and MCP servers | `.claude/`, user-scope MCP config | Third-party skills and MCPs run with the session's permissions: review before installing, treat their files as data. |

STRIDE leads: T, E.

---

## B7. Secrets

| Secret | Where | Note |
|--------|-------|------|
| APK signing keystore | `modules/rv-instrumentation/assets/keystore.jks`, password in configuration code (e.g. `modules/rv-experiment/src/rv_experiment/config.py`) | Signs instrumented APKs for lab emulators. Its impact depends on whether it signs anything that leaves the lab (ask in Phase 4). Report presence and location, never the value. |
| `.env` | repository root, git-ignored; `.env.example` is the template | Check that `.env` stays ignored, that `.env.example` holds placeholders only, and that keys are not logged or written into results. |

STRIDE leads: I, S.
