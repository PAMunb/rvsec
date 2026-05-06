# RISKS — gh53-consolidacao-instrumentation (4-module structure)

GitHub Issue: #53
Decision: ADR `ADR-INSTRUMENTER-ABC.md` (mesmo diretório)

## Methodology

Standard RMMM (Risk Mitigation, Monitoring, Management). Each risk has: category, description (with verifiable evidence at writing time — 2026-05-01), probability, effect, risk level, justification, mitigation strategy, monitoring indicators (Green/Yellow/Red), trigger for contingency, contingency plan, and status.

Probability: Very Low <10%, Low 10–25%, Moderate 25–50%, High 50–75%, Very High >75%.
Effect: Insignificant (cosmetic), Tolerable (<1h rework), Serious (1–8h rework or one re-run), Catastrophic (>8h or proposal reopen).
Risk Level matrix: Critical (High/Very High × Serious/Catastrophic), High (Moderate × Serious/Catastrophic, OR High × Tolerable), Medium (Low × Serious, OR Moderate × Tolerable), Low (anything else).

## Summary table

| Risk Level | Count | IDs |
|------------|-------|-----|
| Critical | 0 | — |
| High | 5 | RISK-002, RISK-003, RISK-006, RISK-008, RISK-010 |
| Medium | 6 | RISK-001, RISK-004, RISK-005, RISK-009, RISK-012, RISK-014 |
| Low | 3 | RISK-007, RISK-011, RISK-013 |

No Critical risks: deliberate consequence of restricting gh53 to consolidation (no validations executed, no archives, no default flip). The heaviest risks are operational (atomic rename surface, ABC contract enforcement, Maven D9 dependency, test mock asymmetry, scope-creep of gh52 INV-INS-18 dívida).

---

## RISK-001 — Pydantic schema serialization drift after type relocation to `-core`

**Category**: Technology (Python class identity / Pydantic semantics)
**Description**: `InstrumentationResults` and `InstrumentationError` move from `modules/rv-instrumentation/src/rv_instrumentation/config.py:102, 127` to `modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py`. Pydantic JSON serialization does not embed the Python module path (`__module__`), so existing `instrument_errors.json` files persisted under `results/<exp>/instrumentation/` should deserialize correctly via the new class. Verified by reading `BaseValidatedModel.model_dump_json()` at module top — no custom serializer that injects module paths.
**Probability**: Low (10–25%) — verified at design time but the test fixture exercise must run with at least one real persisted JSON.
**Effect**: Tolerable — failure surfaces in test 1.8 (`test_legacy_json_without_variant_defaults_to_ajc`) before any production run.
**Risk Level**: **Medium**

### Mitigation strategy
- **Avoidance**: copy types byte-identical (task 1.3 prescribes); same `Field(default="ajc")`, same `BaseValidatedModel` parent.
- **Avoidance**: snapshot existing `instrument_errors.json` files into `backup/gh53-pre-migration-jsons/` (gitignored) before Group 2 starts.
- **Minimisation**: include a real persisted JSON in `modules/rv-instrumentation-core/tests/fixtures/`. Pull from `project_gh52_smoke5_newdata_results.md` baseline (5 JCA-400 APKs).

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `pytest modules/rv-instrumentation-core/tests/test_results.py -k legacy` | exit 0 | warnings | non-zero |
| Sanity load of 5-APK INV-INS-31 baseline JSONs through new -core module | 5/5 | 4/5 | <5 |

**Trigger**: any Red.

### Contingency
1. Restore from backup; identify schema delta; restore `Field(default="ajc")` from git show.
2. Re-run smoke; only after Green re-run AC-IMG-02.
3. If delta cannot be patched: hard-revert and reopen proposal.

### Status
Open

---

## RISK-002 — Atomic rename leaves orphan references in scripts/ and root-level files

**Category**: Technology (import topology) / Estimation (scope under-counted)
**Description**: gh53 renames `rv-instrumentation` (impl) → `rv-instrumentation-ajc`, including class `RVInstrumentation` → `AjcInstrumentation` and config class `RVInstrumentationConfig` → `AjcInstrumentationConfig`. A grep miss in `scripts/`, `tests/` outside `modules/`, or root-level Python files would leave a `from rv_instrumentation import RVInstrumentation` (or `from rv_instrumentation.config import RVInstrumentationConfig`) that fails only at runtime. Identified surfaces: `scripts/validation/fase_a_preprocess.py:98, 148`, `scripts/jca557_quarantine_impact.py:14, 44`. Possibly affected (verify presence at implementation time): `teste_rv_instrument.py`, `teste_rv_modules.py` at repo root (referenced in memory). `aperv-llm-validation/` is temporary (per memory) and excluded from scope.
**Probability**: Moderate (25–50%) — `scripts/` is large surface, not fully covered by tests.
**Effect**: Serious — broken script discovered during Phase 5 gh52 paired-comparison or 400-APK reexecution costs full re-run cycle (8–24h on JCA-400).
**Risk Level**: **High**

### Mitigation strategy
- **Avoidance**: tasks 5.7 explicitly migrates `fase_a_preprocess.py`; tasks 9.19 verifies `jca557_quarantine_impact.py`. AC-IMP-04 grep covers broad case.
- **Avoidance**: extend AC-IMP-01..04 grep range to `scripts/**/*.py` and `tests/**/*.py` outside `modules/`.
- **Minimisation**: dispatch subagent in Group 9 to grep `from rv_instrumentation\b`, `RVInstrumentation`, `RVInstrumentationConfig` across the whole repo; review every hit.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `grep -rnE 'from rv_instrumentation\b' scripts/ tests/ teste_rv_*.py` (excluding tests inside modules) | 0 hits | comment-only "todo: migrate" | uncommented |
| `grep -rnE '\bRVInstrumentation\b' modules/ scripts/ tests/` | 0 hits | hits in archived gh52 docs only | live hits |

**Trigger**: any Red before Group 9 closes.

### Contingency
1. List affected files; group by import path.
2. `.config` imports → migrate to `rv_instrumentation_core` (parent re-exports also work).
3. `RVInstrumentation` imports → migrate to `AjcInstrumentation` from `rv_instrumentation_ajc.ajc_instrumentation` OR `get_instrumenter("ajc", config)`.
4. Add migrated paths to AC-IMP grep verifications.

### Status
Open

---

## RISK-003 — gh52 INV-INS-18 dívida (Field vs model_validator) misread, causes scope-creep fix

**Category**: Estimation (scope creep) / Requirements (spec-vs-code divergence)
**Description**: gh52 INV-INS-18 textually mandates `model_validator(mode="before")` for `InstrumentationResults.variant` retrocompat. Actual code uses `Field(default="ajc")`. gh53 carries `Field` unchanged (descrever a realidade). Risk: implementer reads gh52 spec, notices divergence, adds `model_validator` mid-gh53 — pulls gh52 dívida into gh53 scope.
**Probability**: Low (10–25%) — well documented in design.md §"Dívida herdada", proposal §"Out of scope", ADR §Negative Consequences.
**Effect**: Catastrophic (if it happens) — closes gh52's spec-vs-code divergence under gh53's scope, conflating two changes. Phase 5 review may force partial revert.
**Risk Level**: **High** (Low × Catastrophic, bumped — temptation to "fix while you're there" is real)

### Mitigation strategy
- **Avoidance**: design.md §"Dívida herdada gh52 INV-INS-18" gives explicit instruction.
- **Avoidance**: tasks 1.3 cites instruction inline.
- **Avoidance**: ADR §Decision and §Negative Consequences both state dívida explicitly.
- **Minimisation**: code review Group 9 (`/rv-code-reviewer` task 9.24) MUST flag any `model_validator(mode="before")` introduced in `-core/results.py`; revert if found.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `grep -n 'model_validator' modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py` | 0 hits | 0 hits (comment-only mention) | 1+ hits in code |
| `grep -n 'Field(default="ajc")' modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py` | 1 hit on `variant` | 0 hits (forgot to copy) | wrong default |

**Trigger**: any Red.

### Contingency
1. Revert the `model_validator` addition.
2. Restore `Field(default="ajc")` if missing.
3. If implementer believes validator is necessary, discussion belongs in gh52 spec amendment, NOT in gh53.

### Status
Open

---

## RISK-004 — `scripts/validation/fase_a_preprocess.py` migration breaks ajc-specific call paths

**Category**: Technology (API surface change)
**Description**: `scripts/validation/fase_a_preprocess.py:98, 148` currently imports `RVInstrumentation` directly because it needs ajc-specific methods (`prepare_instrumentation(results_dir)` with arg, `check_if_instrumented(app)`) that are NOT in the `Instrumenter` ABC. After rename, the script must import `AjcInstrumentation` from `rv_instrumentation_ajc.ajc_instrumentation`. Risk: migration also has to update method calls if rename inadvertently changed any signature.
**Probability**: Low (10–25%) — task 2.4 prescribes preserving signatures.
**Effect**: Tolerable — script is run by humans during validation.
**Risk Level**: **Medium**

### Mitigation strategy
- **Avoidance**: task 2.4 says "preserve signatures byte-identical during rename"; only class name changes.
- **Minimisation**: task 5.8 includes `--help` smoke step.
- **Minimisation**: AC-IMP-07 verifies importability.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `python -c "from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation"` | exit 0 | warning | exception |
| `uv run scripts/validation/fase_a_preprocess.py --help` | exit 0 | warning | exception |

**Trigger**: any Red.

### Contingency
1. Inspect renamed `ajc_instrumentation.py` — verify signatures match originals.
2. If drifted, restore from git show.
3. Document expected runtime requirements (e.g., `RVSEC_HOME`).

### Status
Open

---

## RISK-005 — `rv-experiment/pyproject.toml` missing dexlib2 AND ajc deps, lazy import resolution breaks at runtime

**Category**: Technology (uv workspace dependency resolution)
**Description**: `factory.get_instrumenter` uses lazy imports inside each variant branch. Risk: missing dep declaration in `rv-experiment/pyproject.toml` would not surface at `uv sync` or `pytest --collect-only`, only when an experiment runs. Verification (2026-05-01) found that `rv-experiment/pyproject.toml` does NOT currently declare `rv-instrumentation-dexlib2` as a dependency; lazy import works only because the uv workspace resolves transitively via root `pyproject.toml`. Post-rename, `rv-experiment` also needs explicit dep on `rv-instrumentation-ajc` (because `config.py` imports `AjcInstrumentationConfig`).
**Probability**: Low (10–25%) — task 5.4 explicitly adds both deps; AC-WSP-04 verifies.
**Effect**: Serious — failure surfaces during Phase 5 gh52 dexlib2 smoke, costs fix + re-run cycle.
**Risk Level**: **Medium**

### Mitigation strategy
- **Avoidance**: task 5.4 prescribes adding `rv-instrumentation-dexlib2` AND `rv-instrumentation-ajc`. AC-WSP-04 verifies via grep.
- **Minimisation**: task 3.5 (`sys.modules` snapshot test in `test_factory.py`) verifies laziness without breaking dependency chain.
- **Minimisation**: AC-IMG-02 (Docker smoke per variant) is real-world net.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `sys.modules` snapshot test for both variants in `test_factory.py` | 2/2 pass | 1/2 | 0/2 or test missing |
| `grep -n 'rv-instrumentation-dexlib2\|rv-instrumentation-ajc' modules/rv-experiment/pyproject.toml` | 2+ hits in `dependencies` | comment-only | 0 hits |
| `uv pip show rv-instrumentation-dexlib2` and `rv-instrumentation-ajc` after `uv sync` from clean | both show version | warning | not installed |

**Trigger**: any Red, or AC-IMG-02 with `ModuleNotFoundError`.

### Contingency
1. Verify `rv-experiment/pyproject.toml` `dependencies` contains both.
2. If missing, add and re-run `uv sync --refresh`.
3. If factory typo, fix and re-run task 3.5 tests.

### Status
Open

---

## RISK-006 — Maven D9 auto-copy regresses silently and Docker gate misses it

**Category**: Tools (build pipeline) / Technology (Java–Python boundary)
**Description**: gh52 Design D9 introduced Maven auto-copy of `instr-cli.jar` from `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/target/` into `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`. design D6 of this change adds a Dockerfile gate `RUN test -f /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`. Risk twofold: (1) path the gate checks may be wrong relative to image layout — mitigated by verifying against existing `docker/rvandroid_dexlib2/Dockerfile:46` which uses same path; (2) `mvn clean install` may exit 0 even if auto-copy plugin silently skipped.
**Probability**: Moderate (25–50%) — Maven/Java side has no automated test outside Docker build.
**Effect**: Serious — blocking gh52 Phase 5 and 400-APK reexecution.
**Risk Level**: **High**

### Mitigation strategy
- **Avoidance**: design D6 adds gate AFTER `mvn clean install` and `uv sync` (task 6.3). Path verified against legacy gate at `docker/rvandroid_dexlib2/Dockerfile:46-48`.
- **Avoidance**: AC-IMG-01 (`docker build` from clean clone) runs BEFORE AC-IMG-02 (per-variant smoke). Gate failure during build is loud.
- **Minimisation**: extend gate to include size and signature checks: `RUN test -s ... && unzip -p ... META-INF/MANIFEST.MF | grep -q 'Main-Class'`.
- **Minimisation**: smoke `python -c "import os; assert os.path.isfile('/opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar'), 'jar missing'"` inside Dockerfile.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `docker build -t phtcosta/rvandroid:0.8.0 docker/rvandroid/` from clean clone | exit 0, gate prints "OK" | exit 0 with gate warning | non-zero at gate |
| `docker run --rm phtcosta/rvandroid:0.8.0 ls -la /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` | file ≥ 1 MB | <1 MB | "no such file" |
| AC-IMG-02 (`variant=dexlib2` smoke produces `variant: "dexlib2"`) | exit 0 | warnings | non-zero or wrong variant |

**Trigger**: any Red.

### Contingency
1. Inspect `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/target/` after `mvn clean install` — confirm jar lands.
2. Inspect Maven plugin in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/pom.xml`.
3. If plugin disabled: fix `pom.xml`, reopen gh52 Phase 5 (gh52 concern discovered here).
4. If path correct but gate path wrong: edit Dockerfile gate.
5. Defensive backstop: document in `docker/rvandroid/CLAUDE.md` that `mvn clean install` must run BEFORE `docker build`.

### Status
Open

---

## RISK-007 — Documentation count drift across CLAUDE.md, README.md, openspec/config.yaml, docs/PRD.md

**Category**: Requirements (documentation consistency)
**Description**: gh53 adds TWO production workspace modules (`rv-instrumentation-core` AND `rv-instrumentation-ajc`), bumping canonical production count from 14 to 16. Filesystem `ls -d modules/*/` returns 15 directories pre-change, 17 post-change (production + 1 temporary `aperv-llm-validation` excluded from canonical count per memory). README's prior "13 independent modules" was wrong; PRD's "14 uv workspace modules" was correct pre-change. tasks 8.6–8.8 update `CLAUDE.md`, `README.md`, `openspec/config.yaml:8` to new canonical (16). Risk: gh53 edit consolidates one but not the other.
**Probability**: Low (10–25%)
**Effect**: Insignificant — cosmetic.
**Risk Level**: **Low**

### Mitigation strategy
- **Avoidance**: tasks 8.7 explicitly reconciles README with PRD baseline; pick one count post-change (16).
- **Minimisation**: AC-DCM-03 grep for "16 uv workspace modules" / "16 production modules" across all 4 files.
- **Minimisation**: Group 8 final step grep `'14 uv workspace modules\|14 modules\|13 independent modules'` returns 0 hits.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `grep -c '16 uv workspace modules\|16 production modules' openspec/config.yaml CLAUDE.md README.md` | 1+ each | 0 with comment | 0 |
| `grep '14 uv workspace modules\|13 independent' CLAUDE.md README.md openspec/config.yaml` | 0 hits | TODO comments | 1+ hits |

**Trigger**: any Red post-Group-8.

### Contingency
1. Sweep four files; pick canonical count "16" and apply.
2. Update `docs/PRD.md:127` if needed (out of strict scope but recommended for consistency).

### Status
Open

---

## RISK-008 — ABC contract drift breaks `isinstance` and consumers expecting old class

**Category**: Technology (Python class identity / ABC enforcement)
**Description**: `Instrumenter` ABC added in `rv_instrumentation_core/instrumenter.py` declaring `instrument_apks` as `@abstractmethod`. Both `AjcInstrumentation` (renamed from `RVInstrumentation`) and `DexlibInstrumentation` MUST inherit. Risk twofold: (1) `instrument_apks` signature in ABC differs from actual signatures in implementations — Python's ABC does NOT check signatures, only method presence, so signature drift escapes ABC and surfaces as `TypeError` at runtime; (2) consumers that test via `unittest.mock.patch("rv_instrumentation.RVInstrumentation")` silently succeed if `patch` does not validate target.
**Probability**: Moderate (25–50%) — two implementations with multiple call sites; signature drift is known Python gotcha.
**Effect**: Serious — wrong dispatch / wrong signature surfaces in experiment hot path during Phase 5 smoke.
**Risk Level**: **High**

### Mitigation strategy
- **Avoidance**: task 1.4 prescribes ABC signature exactly as `instrument_apks(self, apks_dir, results_dir, force_instrumentation: bool = False, apk_paths: Optional[List[str]] = None) -> InstrumentationResults`, byte-identical to both impls (verified at design time).
- **Avoidance**: task 1.9 (`tests/test_instrumenter.py`) constructs synthetic subclass missing `instrument_apks` and confirms `TypeError`.
- **Minimisation**: task 3.5 (`tests/test_factory.py`) asserts `isinstance(returned, Instrumenter)` for both variants.
- **Minimisation**: contract test in `test_instrumenter.py` uses `inspect.signature(AjcInstrumentation.instrument_apks) == inspect.signature(Instrumenter.instrument_apks)` — catches signature drift at test time.
- **Minimisation**: task 5.5 updates `test_pre_processor_variant.py` mocks to patch factory site.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `tests/test_instrumenter.py` ABC enforcement test | exit 0 | warnings | non-zero |
| `tests/test_factory.py` `isinstance` checks for both variants | 2/2 pass | 1/2 | 0/2 |
| `pytest tests/test_pre_processor_variant.py` (rv-experiment) | exit 0 | deprecation | non-zero |
| `inspect.signature` comparison in `test_instrumenter.py` | identical | whitespace diff | divergent |

**Trigger**: any Red.

### Contingency
1. If signatures diverge: identify which impl drifted; adjust to match ABC.
2. If mock misdirected: update mock target.
3. If implementer added extra `@abstractmethod`: revert (design D2 limits ABC to one method).

### Status
Open

---

## RISK-009 — Stale `.venv` after pulling gh53 keeps old class names resolved

**Category**: Tools (workspace cache)
**Description**: developers (and CI agents iterating without clean clone) pulling gh53 may end up with `.venv` where `rv_instrumentation.RVInstrumentation` is still resolved against old class name (cached `__pycache__`, editable install metadata pinned to old paths). Running experiment without `rm -rf .venv && uv sync` produces confusing `AttributeError`/`ImportError`.
**Probability**: Low (10–25%) — local dev only; CI fresh per pipeline.
**Effect**: Tolerable — local dev cycle interruption.
**Risk Level**: **Medium** (Low × Tolerable bumped — "first impression" friction for new contributors).

### Mitigation strategy
- **Avoidance**: release notes instruct `rm -rf .venv && uv sync`.
- **Avoidance**: AC-WSP-01 covers smoke from clean state.
- **Minimisation**: add `# gh53 migration` callout to root CLAUDE.md or commit message.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `python -c "from rv_instrumentation import RVInstrumentation"` post-pull post-`uv sync` | `ImportError` (intentional, P3) | warning | succeeds (stale cache) |

**Trigger**: developer reports stale-cache symptom.

### Contingency
1. Document `rm -rf .venv && uv sync` in CHANGELOG/release notes.
2. If recurs across team: pre-commit hook or check in `modules/test.sh`.

### Status
Open

---

## RISK-010 — Compose template rewrite breaks paired-comparison required by gh52 Phase 5

**Category**: Tools (Docker compose) / Requirements (gh52 dependency)
**Description**: `docker/docker-compose.dexlib2-validation.template.yml` rewritten in task 6.4 to use `phtcosta/rvandroid:0.8.0` for both services with `RV_INSTRUMENTATION_VARIANT` distinguishing. gh52 Phase 5 (Layer-4) uses this template. Risk: syntactic regression (services not differentiated correctly, env var typo, anchor reuse breakage) caught only when Phase 5 runs.
**Probability**: Low (10–25%) — task 6.5 includes `docker compose config --quiet` smoke; AC-DOC-01 enforces.
**Effect**: Serious — caught early via smoke, but escape costs Phase 5 re-run.
**Risk Level**: **High** (Low × Serious; bumped — Phase 5 cycles expensive).

### Mitigation strategy
- **Avoidance**: task 6.5 (AC-DOC-01) runs `docker compose config --quiet`.
- **Avoidance**: keep exactly two services with same anchors gh52 had (`x-rvandroid-ajc`, `x-rvandroid-dexlib2`); only image tag and env var change.
- **Minimisation**: visual review of rewritten YAML before merge.
- **Minimisation**: end-to-end smoke runs both services on 1-APK fixture (manual, optional in Group 9).

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `docker compose -f docker/docker-compose.dexlib2-validation.template.yml config --quiet` | exit 0; both `0.8.0` | warnings | non-zero |
| `config --json` shows different `RV_INSTRUMENTATION_VARIANT` per service | yes | same env var | identical or missing |

**Trigger**: any Red.

### Contingency
1. Inspect rewritten YAML; compare to gh52 archived template.
2. If structural deviation: restore structure; only change image tag.
3. If gh52 Phase 5 fails specifically due to template structure: escalate to gh52 owner.

### Status
Open

---

## RISK-011 — `ajcore.*.txt` cleanup overshoots and removes wanted file

**Category**: Tools (filesystem cleanup)
**Description**: task 7.1 runs `find . -maxdepth 2 -name 'ajcore.*.txt' -delete`. Risk: some other tool/test fixture happens to use `ajcore.*.txt` naming pattern in subdirectories (unlikely — `ajcore` is AspectJ-specific).
**Probability**: Very Low (<10%)
**Effect**: Tolerable — `find` operates at maxdepth 2.
**Risk Level**: **Low**

### Mitigation strategy
- **Avoidance**: `find -maxdepth 2` restricts to root + 1 level.
- **Avoidance**: dry-run first: `find . -maxdepth 2 -name 'ajcore.*.txt'` (no `-delete`).
- **Minimisation**: AC-CLN-01 verifies post-deletion state.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Dry-run `find` shows only the 22 known `ajcore.20260421.*.txt` | yes | warning | unexpected matches |
| Post-delete `find -maxdepth 2 -name 'ajcore.*.txt'` | empty | permission warnings | non-empty |

**Trigger**: dry-run shows unexpected matches.

### Contingency
1. List unexpected matches; review each.
2. If wanted file matches: exclude or rename.
3. Add more specific pattern (`ajcore.20260421.*.txt`) to `.gitignore` if broader is too wide.

### Status
Open

---

## RISK-012 — gh52 task §17.2 (rename dexlib2 → `rv-instrumentation`) reopens after gh53 occupies the name

**Category**: Requirements (Phase-6 future change conflict)
**Description**: gh52 task §17.2 contemplates renaming `rv-instrumentation-dexlib2` → `rv-instrumentation` once default flips to dexlib2 in Phase 6. gh53 occupies `rv-instrumentation` with parent canonical (factory + re-exports + shared keystore). When gh52 Phase 6 lands, must choose: (a) rename dexlib2 to different canonical (e.g., `rv-instrumentation-default`); (b) rename parent and let dexlib2 take `rv-instrumentation`; (c) keep `rv-instrumentation-dexlib2` (semantic flip only via env var).
**Probability**: Moderate (25–50%) — Phase 6 contingent on Phase 5 results.
**Effect**: Tolerable — gh52 Phase 6 chooses, documents in successor ADR, refactors.
**Risk Level**: **Medium**

### Mitigation strategy
- **Avoidance**: ADR §Negative Consequences and §Risks document collision explicitly.
- **Avoidance**: gh52 task §17.2 is left open (gh53 does NOT close it).
- **Minimisation**: design D8 lists three resolution options.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| gh52 Phase 6 ADR (when written) cites this ADR | yes | ambiguity | conflicts undocumented |

**Trigger**: gh52 Phase 6 starts without referencing this ADR.

### Contingency
1. When gh52 Phase 6 starts: link this ADR's §D8 as input.
2. Successor ADR documents chosen path and supersedes any conflicting wording in gh53.

### Status
Open (deliberately — resolution belongs to gh52 Phase 6)

---

## RISK-013 — Documentation churn during implementation creates stale CLAUDE.md sections

**Category**: Requirements (documentation consistency)
**Description**: Group 8 modifies 6 CLAUDE.md files (root + 5 module-level: `-core`, parent, `-ajc`, `-dexlib2`, `rv-experiment`), README, openspec/config.yaml. During Phase 4, code changes that drift from planned structure leave docs ahead of code. Discovery happens during `/rv-code-reviewer` or `/opsx:verify`.
**Probability**: Low (10–25%)
**Effect**: Insignificant — caught and updated.
**Risk Level**: **Low**

### Mitigation strategy
- **Avoidance**: Group 8 scheduled AFTER Groups 2-5 land (per dispatch hint comment), reducing drift window.
- **Minimisation**: task 9.26 runs `/rv-docs-sync` unconditionally.
- **Minimisation**: `/rv-code-reviewer` (task 9.24) reviews docs alongside code.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| `/rv-docs-sync` reports clean | yes | minor drift fixed in-task | major drift requiring rework |

**Trigger**: `/rv-docs-sync` reports major drift.

### Contingency
1. Compare docs to actual code state.
2. Update docs to reflect reality.
3. Re-run `/rv-docs-sync` to confirm.

### Status
Open

---

## RISK-014 — Coordination of 4 modules: implementer mistakes which dep goes where, breaks topology

**Category**: Estimation (architectural complexity) / Technology (workspace topology)
**Description**: The 4-module layout has strict dep rules per INV-INS-41: `-core` has no impl deps; impls depend ONLY on `-core` (NOT parent, NOT siblings); parent depends on all three siblings. An implementer might inadvertently add a "convenience" dep (e.g., `-core` depends on `rv-instrumentation` for re-exports, or `-ajc` depends on `rv-instrumentation` thinking it needs the factory). Such a dep adds the cycle back.
**Probability**: Low (10–25%) — INV-INS-41 + AC-WSP-05/06 + tasks 1.13, 2.17, 3.11, 4.4 all explicitly verify.
**Effect**: Serious — `uv sync` resolves badly or refuses; CI breaks immediately.
**Risk Level**: **Medium**

### Mitigation strategy
- **Avoidance**: tasks 1.2, 2.2, 3.2, 4.4 each prescribe exact `dependencies` list for their module's pyproject.
- **Avoidance**: tasks 1.13, 2.17, 3.11 each include `python -c "import tomllib; ..."` assertion verifying deps match the canonical layout.
- **Minimisation**: AC-WSP-05/06 in design D7 are dedicated checks for this invariant.
- **Minimisation**: task 9.17 runs the full topology check at integration time.

### Monitoring (RMMM indicator)
| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| AC-WSP-05 (parent deps exactly the 3 siblings) | matches | extra dep with comment | extra/missing dep |
| AC-WSP-06 (`-core` deps exactly `pydantic` + `rv-android-core`) | matches | extra dev dep | extra runtime dep |
| `uv sync` from clean state | exit 0 | warnings | non-zero or cycle error |

**Trigger**: any Red.

### Contingency
1. Inspect offending pyproject.toml; identify wrong dep.
2. Remove the dep; verify with topology check.
3. If `uv sync` still fails: `uv lock --refresh` then re-sync.
4. If implementer needs the symbol from sibling: route via factory call (impls call back through factory only via consumer like rv-experiment, never directly).

### Status
Open

---

## Indicators dashboard

Note: ACs are **populated** (made satisfiable) during the implementation Group, but the **gating** (final verification) lives in Group 9. The "ACs populated" column lists ACs whose pre-conditions originate in that Group; the actual gate command runs in Group 9.

| Group | Risks covered | ACs populated (gated in Group 9) |
|-------|---------------|------------------|
| 1 (`-core` foundation) | RISK-001, RISK-003, RISK-008, RISK-014 | AC-IMP-02, AC-IMP-06, AC-BHV-01, AC-WSP-06 |
| 2 (atomic rename `-ajc`) | RISK-002, RISK-008, RISK-009, RISK-014 | AC-IMP-04, AC-IMP-07, AC-BHV-03, AC-WSP-02, AC-AST-01..03 (asset moves happen here: keystore stays at parent; weaving_excludes moves to -ajc) |
| 3 (parent restructure) | RISK-008, RISK-014 | AC-IMP-09, AC-BHV-02, AC-WSP-05 |
| 4 (dexlib2 update) | RISK-002, RISK-008, RISK-014 | AC-IMP-03, AC-IMP-08, AC-BHV-04 |
| 5 (rv-experiment dispatch) | RISK-004, RISK-005, RISK-008 | AC-IMP-01, AC-IMP-09, AC-WSP-04, AC-BHV-05, AC-BHV-06, AC-AST-04..05 (jca557 path edit happens here) |
| 6 (Docker) | RISK-006, RISK-010 | AC-DOC-01..03, AC-IMG-01, AC-IMG-02 |
| 7 (cleanup) | RISK-011 | AC-CLN-01, AC-CLN-02 |
| 8 (documentation) | RISK-007, RISK-013 | AC-DCM-01..03 (note: AC-AST-01..06 are populated by Group 2 task 2.7 + Group 5 task 5.7b — Group 8 only updates documentation that mentions asset paths) |
| 9 (verification) | all (final gate) | AC-IMP-01..09 + AC-DCM-04 + every other AC |
