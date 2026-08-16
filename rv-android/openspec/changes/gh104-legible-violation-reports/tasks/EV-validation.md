# Group 5 — EV: validation toolkit (gates, lint, message gate, differential harness)

Tracked checkboxes: `tasks.md` §5. Wave 1; creates NEW files only; hard prerequisite of Group 7. Shares `tests/parity/test_gh104_specset_gates.py` with Group 2 (Group 2 creates it with two tests; this group appends — coordinate by landing Group 2's commit first or by writing the gates in a second file `test_gh104_structural_gates.py`; prefer the second to avoid a merge).

## Subagent brief

Read `design.md` D-7, the `instrumentation` delta (`Requirement: Executable Structural Gates…`, `Requirement: Differential Harness…`, INV-INS-123/124), `scripts/gh101_monitor_transition_check.py` (98 lines — reuse its monitor parsing, it reads both `AbstractAtomicMonitor` and `AbstractSynchronizedMonitor` shapes `:36-45`), `tests/parity/test_gh101_specset_gates.py` (145 lines, five gates — the pattern to follow), `data/gh101/frozen_set_debt.md:69-101` (the 18 orphans, nominal), `openspec/changes/archive/2026-08-16-gh101-jca-spec-conformance/design.md` D-S9 (why G-2b/absorption is not adopted). Monitor generation: `RVSEC_HOME` set, `TMPDIR` off tmpfs, never in parallel. A gate that reports fewer hits on the frozen `jca` than the baseline below is wrong — the frozen set is the fixture with known answers.

## Files (create)

- `scripts/gh104_gates.py` — G-2, G-2a, G-2b′, G-2c, G-2d, G-6′ over a `MultiSpec_1RuntimeMonitor.java`; `--allowlist`; JSON report.
- `scripts/gh104_mop_lint.py` — over a set directory: undeclared ERE/FSM symbol; duplicate event name; unbalanced parentheses; first statement of every body is `lastEventName = "<name>";` (INV-INS-120 — fails on the frozen `jca` by design; the test asserts the *count* on `jca` and zero on `jca_v2` after Group 6); three-argument `new ErrorDescription(` (INV-INS-119); reserved generator names in `declarations` (`Prop_N_state`, `Prop_N_transition_*`, `pairValue`, `RVM_lastevent`, `reset`, `getState`, `getLastEvent`, `handleEvent`, `clone`).
- `scripts/gh104_message_gate.py` — numeric literals in a message vs the guarding `condition()`; `codes.csv` ↔ sites bijection; `ErrorType` vs site kind.
- `tests/parity/test_gh104_structural_gates.py` — parametrised over `jca` (fixture monitor `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`, 2026-08-08; **not** `results/gh56-smoke/` — it predates the freeze by three months and two source fixes) and `jca_v2` (generated in scratch).
- `data/jca/gate_allowlist.csv` — names the baseline hits below with reason "frozen set; knowingly retained (data/gh101/frozen_set_debt.md)".
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (+ `pom.xml` test scope in `rvsec-mop` — the directory does not exist today) — loads a generated monitor class set (`MultiSpec_1RuntimeMonitor` + `mop/*`), replays a trace file, records per trace: accused (bool), accusing event (`ev=` from the envelope or the `@fail` line), envelope text.
- `scripts/gh104_diff_harness.py` — `run(set_a, set_b, traces_dir, out_dir)`: generates both in scratch (`rv-monitor-generator` via `uv run` API or `rvsec` CLI as gh101 task 8.x did), runs `TraceRunner`, classifies per trace `unchanged` / `removed` / `moved` (accused in both but at different events) / `introduced`; writes `evidence/harness/<name>.md`.
- `traces/<Spec>.txt` for the 23 specifications — one line per call `Spec.event(args…)`; ≥ 1 legitimate sequence, 1 per authored violating branch, and the separating traces of `audit/20260808_validacao_jca_android/` (grep `separating` / `traço` under `audit/.../set/`).
- `evidence/harness/selftest.md`.

## Baseline the gates must reproduce on the frozen `jca` (measured 2026-08-16)

| gate | definition | expected on `jca` |
|---|---|---|
| G-2 | `∀s: δ(s,e) = fail` (INV-INS-110) | 18 events in 10 specs: `IvParameterSpec.c3,c4`; `KeyPairGeneratorSpec.initError`; `MessageDigestSpec.reset`; `PBEKeySpecSpec.f1,f2,err1,err2,err3`; `PBEParameterSpecSpec.c3`; `SSLContextSpec.unsafe_protocol`; `SecretKeySpecSpec.c3,c4`; `SecureRandomSpec.c3,g4,setSeed3`; `SignatureSpec.g3`; `TrustManagerFactorySpec.g3` |
| G-2a | `∀s: δ(s,e) = s` | 1: `SecretKeySpec.e1` |
| G-2b′ | `δ(q0,e) = q0` | 8: `CipherSpec.g3`, `KeyGeneratorSpec.g3`, `KeyManagerFactorySpec.g3`, `KeyPairGeneratorSpec.g3`, `KeyStoreSpec.g2`, `MacSpec.g3`, `MessageDigestSpec.g4`, `SecretKeySpec.e1` |
| G-2c | unreachable from `q0`, or accepting unreachable from it | 1 |
| G-2d | highest state index is not `Category_fail` | 2: `SecretKeySpec`, `RandomStringPasswordSpec` (no `fail` category) |
| G-6′ | `#Prop_N_event_* methods ≠ #Prop_N_transition_* rows` | 1: `GCMParameterSpecSpec` |

A throwaway implementation that reproduced these numbers exists in the session scratchpad of 2026-08-16 (`structural_gates.py`); re-derive rather than trust it. `scripts/gh101_monitor_transition_check.py results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java` prints the 18 (exit 1).

Lint/message-gate baseline on the frozen `jca`: 25 three-argument sites; `GCMParameterSpecSpec.mop:23,34` duplicate `c1`, `:48` `c2` undeclared; `SecretKeySpecSpec.mop:27-30` unbalanced; 134/134 bodies without bookkeeping; literal mismatches `PBEKeySpecSpec.mop:50` (`1000` vs `:48` `10000`) and `PBEParameterSpecSpec.mop:50` (`1000` vs `:46` `10000`); no `static` declarations in the corpus.

Harness self-test expected: `jca` vs `jca_android`, `TrustManagerFactorySpec`, trace `getInstance("X509"); init(ks)` → accused at `getInstance` (frozen row `{3,3,3,3}` for `g3`) vs at `init` (derived row `{0,3,3,3}`, `unsafeAlg` state) → `moved`. Trace `getInstance("PKIX"); init(ks); getTrustManagers()` → not accused in either → `unchanged`.

## Commands

```bash
python3 scripts/gh104_gates.py results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java --allowlist data/jca/gate_allowlist.csv
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec/rvsec-mop/src/main/resources/jca      # reports the baseline hits
uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh104_structural_gates.py -q
cd ../rvsec/rvsec/rvsec-mop && mvn -q test -Dtest=TraceRunnerTest
python3 scripts/gh104_diff_harness.py --a ../rvsec/rvsec/rvsec-mop/src/main/resources/jca --b ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_android --traces traces --out evidence/harness/selftest
```

## Acceptance

- The six gates reproduce the baseline on `jca` exactly and pass with the allowlist; on `jca_v2` (seed) they report the same numbers (it is a copy) — this is the fixture for Group 7.
- Lint and message gate report the baseline on `jca`; both are wired into the pytest for `jca_v2` (they will go green after Groups 6/7).
- Harness self-test writes `evidence/harness/selftest.md` with the `moved` verdict for `TrustManagerFactorySpec`.
- No emulator, no device: everything here is JVM/pytest.
