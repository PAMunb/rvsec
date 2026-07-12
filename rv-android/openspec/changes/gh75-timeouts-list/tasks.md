# Tasks: gh75-timeouts-list

GitHub Issue: #75. Small change (~8 files): two CLI modules, one test module, docs. Sequential execution; no subagent orchestration needed.

## 1. rv-experiment CLI (Click)

- [x] 1.1 Add `_parse_timeouts(raw: str) -> list[int]` helper in `modules/rv-experiment/src/rv_experiment/__main__.py` (comma split, strip, positive ints, `click.BadParameter` on empty/invalid/≤0 — design.md API Design)
- [x] 1.2 Replace the `--timeout` option (`__main__.py:332`) with `--timeouts`: `default=str(DEFAULT_TIMEOUT)`, keep `envvar=ENV_TIMEOUTS`, help documenting the CSV format
- [x] 1.3 Rename param `timeout: int` → `timeouts: str` through `run()` (`__main__.py:486`), the helper call (`__main__.py:572`), `_create_experiment_config_from_cli` signature/docstring (`__main__.py:987,1030`); parse early in `run()` and replace `timeouts=[timeout]` (`__main__.py:1133`) with the parsed list
- [x] 1.4 Update log/echo lines (`__main__.py:542,606`) to display the timeout list
- [x] 1.5 Update `modules/rv-experiment/tests/test_cli_envvar_precedence.py`: captures/asserts rename to `timeouts` with list values (`[180]`, `[60]`, `[DEFAULT_TIMEOUT]`); add cases `RV_TIMEOUTS="60,300"` → `[60, 300]`, `--timeouts 60,120` overriding env, invalid token → exit 2, `--timeout` rejected as unknown option
- [x] 1.6 Add unit tests for `_parse_timeouts` (single, list, whitespace, invalid token, empty string, zero/negative)
- [x] 1.7 Run `/rv-test-run rv-experiment` (207 passed via CI-contract pytest)

## 2. rv-platform CLI (argparse)

- [x] 2.1 Replace `--timeout` with `--timeouts` (`type=_parse_timeouts`, `default=[300]`, CSV help text). Also set `allow_abbrev=False` on the `run` subparser so `--timeout` is not silently accepted as a prefix abbreviation (spec Scenario "Old Scalar Flag No Longer Exists"; user-approved) — the argparse `type=` wiring (not `type=str`+post-parse) is required so invalid input aborts in `parse_args()` with exit 2 before `PlatformConfig`, since `cmd_run`'s except returns 1
- [x] 2.2 Add the mirrored `_parse_timeouts` helper (argparse flavor: raises `argparse.ArgumentTypeError`) and replace `timeouts=[args.timeout]` (`__main__.py:406`) with `timeouts=args.timeouts` (already a list from `type=`) in `_create_config_from_cli`
- [x] 2.3 Add unit tests (`tests/test_cli_timeouts.py`): `_parse_timeouts` mirror cases + parser-level (`--timeouts 60,300`→`[60,300]`, invalid→exit 2, `--timeout`→exit 2) + `_create_config_from_cli` wiring
- [x] 2.4 Run `/rv-test-run rv-platform` (266 passed via CI-contract pytest)

## 3. Docs and In-Tree Callers

- [x] 3.1 Update `.env.example:52` (`# CLI flag: --timeout` → `--timeouts`, note list format)
- [x] 3.2 Update flag references in `README.md`, `modules/rv-experiment/README.md`, `modules/rv-platform/README.md`, `modules/rv-experiment/docs/architecture.md`. (`experimento-20260706/README.md` already used the plural `--timeouts` — the `--timeout` there belongs to the `rv_status.py` monitor script, unrelated.) Additional in-tree callers/living docs discovered via the grep gate and updated for correctness/consistency: `scripts/parallel_run.py` (forwarded `--timeout`→`--timeouts` to the rv-experiment subprocess + its own wrapper arg, else the subprocess breaks), `modules/rv-experiment/tests/test_resume_cli.py` (direct factory caller), root `CLAUDE.md`, `docker/README.md`, `docs/PRD.md`, `docs/rv_android_architecture.md`
- [x] 3.3 Rewrite the workaround comment in `experimento-20260706/docker-compose.smoke.yml:8-9` (double-invocation no longer needed; `RV_TIMEOUTS: "60,120"` works in one invocation) — comment only, `RV_TIMEOUTS` env values untouched (config-freeze rule)
- [x] 3.4 Repo-wide grep gates: `timeouts=[timeout]`/`timeouts=[args.timeout]` → none in modules ✓. `--timeout\b` residual is all out-of-scope: rv-agent's own `--timeout`, GATOR/static-analysis/sweep `--timeout` (unrelated flag), the `rv-experiment-compare` skill's own scalar arg (uses `RV_TIMEOUTS` env, not a forwarded flag), and historical/archived docs (P4: not rewritten — e.g. `experimento-20260508/README.md` documents the old 0.8.0 limitation as rationale). Only CLI-src hit is the `allow_abbrev=False` explanatory comment.

## 4. Integration & Verification

- [x] 4.1 CI-contract run per module (isolation, as CI does — the combined-dir form hits the pre-existing `from helpers import` collision, unrelated to this change): rv-experiment **207 passed**, rv-platform **266 passed, 1 skipped**
- [x] 4.2 `/rv-qa-lint-fix` skill **skipped per user request**; ran the equivalent directly (project uses black+isort+flake8, not ruff): `isort` + `black` clean; `flake8` introduces **zero** new E501 (baselines 25/1 preserved) and no F/E7/E9 issues
- [x] 4.3 `/rv-verify` skill **skipped per user request**; ran the equivalent directly (no tracked CI workflow exists; the "CI contract" is the pytest invocation only): tests pass in isolation, black `--check` clean, isort `--check` clean, flake8 no new issues. mypy is a dev dep, not a gate; new code is fully typed (`List[int]`/`list[int]`).
- [x] 4.4 `/rv-code-reviewer` skill **skipped per user request** (usuário pediu skip das skills rv-*)
- [x] 4.5 Acceptance (issue #75) verified — no emulator: both `--help` show `--timeouts` only; `--timeouts 60,abc`→exit 2 (`click.BadParameter`), `--timeouts 300,-5`→exit 2 (argparse); old `--timeout` rejected on both (Click "No such option", argparse "unrecognized arguments" via `allow_abbrev=False`); `RV_TIMEOUTS`/CLI>env>default and 1-vs-2-arm parsing covered by `test_cli_envvar_precedence.py`/`test_parse_timeouts.py`; the timeout×matrix multiplication is the pre-existing `test_platform.py::"Tasks = APKs × tools × repetitions × timeouts"` (`[300,600]`→16). 54/54 green.

## 5. E2E Validation (manual — requires emulator; NOT executed yet)

Full-pipeline proof that a single invocation with `--timeouts 60,120` produces two timeout
arms end-to-end (pre-processing → instrumented APK → headless emulator run → results). This is
the live counterpart to the no-emulator acceptance in 4.5. **Do not start/stop emulators
manually — rv-experiment owns the emulator lifecycle** (start, boot wait, install, cleanup).

Prerequisites: `RVSEC_HOME` set (monitor generation + static analysis) and `ANDROID_HOME` set
with an AVD whose ABI matches `cryptoapp.apk`. No `--apks-filter` needed: `apks_examples/`
contains exactly one APK (`cryptoapp.apk`), and APK discovery is `apks_dir.glob("*.apk")`
(`platform.py:295`), so `--apks-dir ./apks_examples` selects only the target.

- [ ] 5.1 Run the full experiment (pre-processing ON — no `--skip-*`; headless; two timeout arms):
  ```bash
  uv run rv-experiment run \
    --tools ape \
    --apks-dir ./apks_examples \
    --timeouts 60,120 \
    --repetitions 1 \
    --specification-set jca \
    --no-window \
    --name gh75_e2e_timeouts
  ```
  (Tool note: `ape` is the built-in APE. If MOP-aware APE-RV is intended instead, use
  `--tools aperv`. Re-running the same `--name` auto-resumes.)
- [ ] 5.2 Assert two timeout arms materialized: `results/gh75_e2e_timeouts/tasks.json` contains
  exactly 2 tasks for `cryptoapp` — identities `(cryptoapp, ape, default, 1, 60)` and
  `(cryptoapp, ape, default, 1, 120)` (1 APK × 1 tool × 1 rep × 2 timeouts).
- [ ] 5.3 Assert health: exit 0, both tasks have non-empty logcats under
  `results/gh75_e2e_timeouts/`, and 0 `VerifyError` in the logcats (instrumentation intact).

## 6. E2E Validation — Docker Image (env-var path; requires image rebuild after push)

Highest-value validation of the fix: **inside the container, timeouts arrive via the
`RV_TIMEOUTS` env var** (Click `envvar=ENV_TIMEOUTS`), which is exactly the path the gh75 bug
broke (`int("60,300")` crash). The Docker image also bundles its own emulator/environment, so
it is the cleaner runtime proof for the health assertions that Section 5.3 could not exercise
locally (the local emulator run proved the 2-arm matrix but 5.3 was blocked by an environment
emulator boot-timeout, unrelated to this change). The image must be rebuilt so the container
carries the `--timeouts`/`RV_TIMEOUTS` fix — the reactor is at `0.9.2-SNAPSHOT`, so the image
tag to build and run is **0.9.2**.

- [ ] 6.1 Push the gh75 commit, then **rebuild** the rvandroid Docker image at tag **0.9.2**
  (current reactor version `0.9.2-SNAPSHOT`, `rvsec/pom.xml`). Build via `docker/build_all.sh`
  (chain: `base → android → tools → rvandroid_dev`) or just the tools stage
  (`cd docker/tools && ./build.sh`); the application image is `phtcosta/rvandroid:0.9.2`
  (base `FROM phtcosta/rvsec_android:0.9.2`, `docker/tools/Dockerfile`). The rebuild is
  mandatory — a stale image would still carry the old `--timeout` scalar CLI.
- [ ] 6.2 Run the containerized E2E driving the **env-var path** (not the CLI flag):
  `RV_TIMEOUTS="60,120"`, `RV_TOOLS="ape"`, 1 repetition, `jca`, on `cryptoapp.apk`, using
  image `phtcosta/rvandroid:0.9.2`. Assert exactly **2 timeout arms** materialize in the run's
  `tasks.json` — identities `(cryptoapp, ape, default, 1, 60)` and
  `(cryptoapp, ape, default, 1, 120)`. This is the direct regression proof for the original
  bug: `RV_TIMEOUTS` with a list value no longer crashes on `int("60,300")` and a single
  container invocation yields both arms (superseding the old double-invocation workaround noted
  in `experimento-20260706/docker-compose.smoke.yml`).
- [ ] 6.3 Assert in-container health: exit 0, non-empty logcats for **both** arms, and 0
  `VerifyError` in the logcats (instrumentation intact end-to-end inside the image).
