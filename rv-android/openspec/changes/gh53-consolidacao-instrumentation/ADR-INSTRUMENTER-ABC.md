# ADR — gh53: Four-module instrumentation domain (`-core` + parent + `-ajc` + `-dexlib2`) with `Instrumenter` ABC and public factory

## Status

Accepted.

## Date

2026-05-01

## Context

After gh50 (resilience ajc/d8), gh51 (Soot 4.7.1), and gh52 (DEX-native dexlib2 pipeline) all merged into branch `modules`, the instrumentation domain carries three structural debts that block the canonical Docker image rebuild for the upcoming Phase 5 validations:

1. **Wrong-direction coupling**: `rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:11-14` imports `InstrumentationResults` and `InstrumentationError` from `rv_instrumentation.config` — i.e., the new module depends on the legacy AjC module for shared domain types. The keystore situation mirrors this: `rv-experiment/config.py:669` resolves the dexlib2 `keystore_file` to `modules/rv-instrumentation/assets/keystore.jks`, embedded in the AjC module by historical inertia despite both variants needing it.

2. **Inline dispatch without canonical contract**: `pre_processor.py:188-207` selects between `RVInstrumentation` and `DexlibInstrumentation` via `if/else`, importing concrete classes directly. There is no canonical contract any consumer can reference.

3. **Inconsistent project pattern**: `rv-android` already uses ABC + variants elsewhere (`AbstractTool` ABC at `modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py` (re-exported via `rv-tools`); `ExperimentController` and friends in `rv-experiment`). Instrumentation diverges by keeping all three concerns (types, contract, factory, impl) collapsed inside `rv-instrumentation`.

Phase 0 (`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260428_plano_consolidacao_pos_gh50_gh51_gh52.md`, §3.1) chose Option A: parent canonical at `rv-instrumentation` with ABC + factory + types, atomic rename of the AjC implementation to `rv-instrumentation-ajc`. During design refinement, a **circular dependency** was identified that would arise if the parent owned both the abstractions (ABC + types) AND the factory dispatching to the variant impls:

- `rv-instrumentation-ajc/pyproject.toml` declares dep on `rv-instrumentation` (needs ABC for inheritance + types)
- `rv-instrumentation/pyproject.toml` would need to declare dep on `rv-instrumentation-ajc` (factory imports `AjcInstrumentation`)
- → cycle that `uv workspace` refuses or resolves badly

Workaround: lazy import inside the factory function without declaring the dep in pyproject. Functionally it works at runtime, but fails at: testing the factory in the parent (impls not installed); standalone consumer using only the parent (`ImportError` at runtime); pyproject honesty (implicit deps not declared — anti-pattern).

This ADR records the architectural choice that solves the cycle: **separate the abstractions** into a dedicated `rv-instrumentation-core` module, distinct from the parent that hosts the factory. Three alternatives are considered and two are rejected.

## Decision Drivers

- **Acyclic dependency graph honestly declared**: each module's `pyproject.toml` lists exactly what it imports; `uv workspace` resolves cleanly; nothing implicit.
- **Project pattern consistency** (P2): ABC + factory matches the rest of `rv-android`. `AbstractTool` precedent at `rv-android-core/tools/abstract_tool.py`.
- **Explicit shared contract**: ABC declared in a module that has no impl deps; subclasses that miss `instrument_apks` fail at instantiation time.
- **Single dispatch site**: public `get_instrumenter(variant, config)` is the canonical extensibility point for any consumer.
- **Atomic migration (P3 — no backward compat)**: renaming `rv-instrumentation` (impl portion) → `rv-instrumentation-ajc` and moving types to `-core` must be a single coherent transition with no aliases or shims.
- **Future variant extensibility (NFR05)**: a third variant (LSPatch — `docs/20260422_lspatch.md`) lands as: one new module subclassing `Instrumenter` (depending only on `-core`) + one branch in `factory.get_instrumenter` + one Literal extension. No retrofitting of consumers.
- **Test isolation**: `-core` tests run with no impl modules installed; parent factory tests run with all impls; impl tests run with `-core` only. Each layer is unit-testable in isolation.

## Considered Options

### Option A (chosen) — 4 modules: `-core` + parent + `-ajc` + `-dexlib2`

**Description**: separate pure abstractions into a new `rv-instrumentation-core` module (types `InstrumentationResults`, `InstrumentationError` + ABC `Instrumenter`). The parent `rv-instrumentation` becomes a thin canonical wrapper that re-exports the public surface from `-core` AND owns the factory (with declared deps on both impls) AND the shared keystore asset. Impls (`-ajc` renamed from current `rv-instrumentation` AjC content; `-dexlib2` existing) depend ONLY on `-core` (NOT on the parent). The dependency graph is acyclic with arrows pointing toward `rv-android-core` at the base.

**Pros**:
- Acyclic graph honestly declared in each pyproject.
- Factory lives in the parent (canonical name); consumers `from rv_instrumentation import get_instrumenter` regardless of where pieces physically live.
- `-core` is reusable by any future tooling that wants only the abstractions.
- Each layer unit-testable in isolation.
- Project pattern consistency: ABC + factory + variant pattern.
- Atomic rename + types migration in same change (P3).
- LSPatch (3rd variant) lands cleanly: depends on `-core` only.

**Cons**:
- `+2` production workspace modules (14 → 16 production; filesystem `ls -d modules/*/` 15 → 17). Larger inventory churn in `CLAUDE.md`, `README.md`, `openspec/config.yaml`, `docs/PRD.md`, build scripts, lint matrix.
- Migration surface ~45 files: rename of pacote Python + classes, `git mv` of source files + assets, Docker cleanup, doc rewrite. Bounded but not small.
- gh52 task §17.2 (rename `dexlib2` → `rv-instrumentation` when default flips) collides with the parent occupying that name. Phase-6 problem to solve.
- Coordination complexity: 4 modules to keep in sync; testing matrix grows by 1 layer.

### Option B (rejected) — 3 modules with parent owning everything: types + ABC + factory + impls deps

**Description**: keep one parent at `rv-instrumentation` containing types + ABC + factory + shared keystore. Impls (`-ajc`, `-dexlib2`) depend on parent. Lazy imports inside factory; pyproject of parent does NOT declare deps on impls (to avoid cycle).

**Pros**:
- Smallest diff (1 fewer module).
- Single canonical name covers everything.

**Cons**:
- **Anti-pattern: implicit dependency**. Parent imports impls at runtime via lazy import inside factory function but does NOT declare them in pyproject. Future contributors don't see the dep; tests of factory in parent fail (impls not installed unless dev deps include them, which then mirrors the cycle problem); standalone consumer using only the parent finds `ImportError` at runtime.
- Cycle is REAL if parent declares deps on impls (impls already depend on parent). Workspace tools (uv, pip) refuse or resolve poorly.
- `-core` reusability lost: any future tooling wanting only the abstractions has to depend on the parent + accept its impl deps.

### Option C (rejected) — 4 modules but `Protocol` instead of ABC

**Description**: same 4-module layout as Option A, but `SupportsInstrumentApks` is `typing.Protocol` (`@runtime_checkable`) instead of `abc.ABC`. Impls do NOT inherit (structural typing).

**Pros**:
- No inheritance dependency: `-ajc` and `-dexlib2` don't need to import anything from `-core` at class-definition time (only types in method signatures).
- Adding a third variant requires no inheritance — duck typing covers the contract.

**Cons**:
- **Inconsistent with project pattern**: `AbstractTool`, `ExperimentController` etc. are all ABC. Instrumentation would be the only `Protocol`-based contract.
- `Protocol` checks attribute presence at runtime (`isinstance` works) but does NOT enforce signature matching; subtle drift in `instrument_apks` parameters between variants escapes ABC's `@abstractmethod` discipline.
- Loses the fail-fast at instantiation: a subclass missing `instrument_apks` doesn't fail at class definition; only at the call site.

### Option D (rejected) — 3 modules with private dispatch helper in `rv-experiment`

**Description**: same module layout as Option B but factory is a private `_select_instrumenter` helper inside `rv-experiment/.../pre_processor.py` (not exposed publicly). Parent `rv-instrumentation` only has types + ABC. No public factory, no API consolidation.

**Pros**:
- Smallest possible change.
- No cycle (rv-experiment depends on impls naturally; types live in parent which has no impl deps).

**Cons**:
- No public extensibility point — every new consumer that wants to dispatch must replicate the `if/else`.
- Pattern divergence with the rest of the project (`AbstractTool` + factory in `rv-tools` etc.).
- Doesn't solve the "no canonical contract" debt — only papers over the dispatch mess.

## Decision

We will adopt **Option A**: four modules (`-core` + parent `rv-instrumentation` + `-ajc` + `-dexlib2`), with `Instrumenter` ABC in `-core`, public factory `get_instrumenter` in the parent, atomic rename of the AspectJ implementation to `rv-instrumentation-ajc`, both `AjcInstrumentation` and `DexlibInstrumentation` inheriting from `Instrumenter` (imported from `-core`).

The decision is driven primarily by **acyclic dependency declaration**: only the 4-module layout allows each `pyproject.toml` to honestly declare what it imports without resort to lazy-import workarounds. Secondary drivers are project pattern consistency (ABC + factory + variant matches `rv-android`'s established convention), test isolation (each layer unit-testable independently), and future extensibility (LSPatch lands as a sibling of `-ajc` and `-dexlib2`, depending only on `-core`).

The collision with gh52 task §17.2 is documented as a known consequence; gh52 Phase 6 will resolve naming when the default actually flips.

The heritage debt from gh52 INV-INS-18 (`Field(default="ajc")` in code vs. `model_validator(mode="before")` in spec) is **not closed by this change**. gh53 carries the existing `Field` mechanism forward unchanged, byte-identical, and documents the divergence in `design.md §"Dívida herdada gh52 INV-INS-18"`. Closing it is gh52's responsibility.

## Consequences

### Positive

- **Acyclic dependency graph**: each pyproject declares exactly what its module imports. No implicit deps. `uv workspace` resolves cleanly.
- The instrumentation domain matches the rest of the project's modular pattern (ABC + factory + variants).
- A single canonical entry point (`rv_instrumentation.get_instrumenter`) replaces inline dispatch; future consumers (e.g., scripts, rv-platform extensions) have one place to call.
- The ABC (in `-core`) catches contract violations at class definition / instantiation, not at runtime mid-experiment.
- Adding LSPatch (or any third variant) is a localized addition: one new module depending on `-core` + one factory branch + one Literal extension. The `-ajc` and `-dexlib2` modules are not touched.
- Each layer is unit-testable: `-core` tests with synthetic subclasses; parent factory tests with all impls; impl tests with `-core` only.
- Shared keystore moves from being implicitly owned by AjC to being explicitly owned by the parent canonical module.
- gh52 task §15.4 (CLAUDE.md update) is unblocked: the architecture is documented as part of gh53's CLAUDE.md updates. The actual close-out of the gh52 task entry happens when gh52 itself is archived (out of gh53's scope per `proposal.md §"Out of scope"`).
- `instrument_errors.json` files persisted from previous runs continue to deserialize correctly: the `Field(default="ajc")` declaration on `InstrumentationResults.variant` (the actual retrocompat mechanism) travels with the class to `-core`. Pydantic's `model_dump_json` does not embed `__module__`, so moving types between modules does not break on-disk schema.

### Negative

- `+2` production workspace modules: production count 14 → 16 (excluding the temporary `aperv-llm-validation` per memory). Filesystem `ls -d modules/*/` goes from **15 module directories** pre-change to **17 module directories** post-change (`-core` and `-ajc` are both new; current `rv-instrumentation` impl content moves to `-ajc`). Build scripts, lint matrix, CI rows and module inventories in `CLAUDE.md`, `README.md`, `openspec/config.yaml:8`, `docs/PRD.md` need updating. README's prior "13 independent modules" was already wrong pre-change; reconciling it to "16" is part of this change.
- Migration surface is wide: ~45 files touched, including Python source rename, Maven-side path references unchanged, asset relocation, Docker cleanup, documentation rewrite. Risk of orphan references is mitigated by mechanical AC checks in `tasks.md` Group 9.
- Coordination complexity grows: 4 modules to keep in sync. Tests gain a layer (parent factory tests new).
- gh52 task §17.2 is **not** unblocked by this change. When the default flips to dexlib2 in Phase 6, gh52 must choose how to handle the canonical name; the ADR records this as a known cost. Three options open to gh52 Phase 6: (a) rename dexlib2 to a different canonical name (e.g., `rv-instrumentation-default`); (b) refactor the parent to another name and let dexlib2 take `rv-instrumentation`; (c) keep dexlib2 module name (semantic flip only via env var).
- Static type checkers cover signature precision via the ABC; runtime check (via `isinstance(x, Instrumenter)`) covers attribute presence only. A subclass that overrides `instrument_apks` with the wrong signature passes ABC instantiation but fails type checking. Mitigated via `tests/test_instrumenter.py` in `-core` using `inspect.signature`.
- Asymmetry between Java and Python module-naming convention is preserved (Java side still has `rvsec-instrumentation-dexlib2` under `rvsec/rvsec-android/`; Python side now has 4 `rv-instrumentation*` modules). Consistent with gh52 ADR D8 but worth restating: the parent + ABC + factory pattern is Python-side only.

### Risks

- **Risk**: a stale `.venv` keeps `rv_instrumentation.RVInstrumentation` resolved against the old class name after pulling gh53. **Mitigation**: release notes for the change instruct `rm -rf .venv && uv sync`. CI image is rebuilt fresh per pipeline so CI is not affected. Detailed in `RISKS.md` RISK-009.
- **Risk**: a future `scripts/` consumer or tests-outside-modules imports `RVInstrumentation` directly and is missed by the AC-IMP-04 grep. **Mitigation**: subagent dispatched in Phase 4 Group 9 with the explicit grep `from rv_instrumentation\b` across `scripts/`, `tests/` outside modules, and root-level Python files. Detailed in `RISKS.md` RISK-002.
- **Risk**: the ABC contract is not byte-identical to what existing consumers expect (e.g., a default value diverges between `RVInstrumentation.instrument_apks` and the ABC). **Mitigation**: `tests/test_instrumenter.py` in `-core` includes a contract test against the actual `AjcInstrumentation` and `DexlibInstrumentation` signatures via `inspect.signature`. Detailed in `RISKS.md` RISK-008.
- **Risk**: gh52 Phase 6 chooses to rename dexlib2 → `rv-instrumentation` and reopens the namespace question. **Mitigation**: this ADR is scoped to gh53; if gh52 Phase 6 promotes a variant to canonical, a successor ADR documents that decision. The 4-module layout here is forward-compatible with any of the three resolution paths listed above. Detailed in `RISKS.md` RISK-012.
- **Risk**: someone "fixes" gh52 INV-INS-18 dívida by adding `model_validator(mode="before")` mid-gh53, conflating scopes. **Mitigation**: design.md, ADR, RISKS.md all document the intent (carry `Field` byte-identical; do NOT add the validator). `/rv-code-reviewer` flags this as scope creep. Detailed in `RISKS.md` RISK-003.

## Implementation Notes

- ADR file lives alongside the change at `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/ADR-INSTRUMENTER-ABC.md`, matching the precedent of `openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md`.
- The ABC uses standard `abc.ABCMeta` (via `class Instrumenter(ABC):`); no `@runtime_checkable` decorator (that is a `Protocol` feature).
- Lazy imports inside `factory.get_instrumenter` (`from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation` inside the AjC branch; `from rv_instrumentation_dexlib2 import DexlibInstrumentation` inside the dexlib2 branch) avoid forcing each variant module's transitive deps onto contexts that only run the other variant. Particularly important for minimal CI images.
- `rv-instrumentation-core` declares only `pydantic` and `rv-android-core` as runtime dependencies. It MUST NOT depend on either variant module or on the parent (any of those would form a cycle). INV-INS-41 enforces this.
- `rv-instrumentation` parent declares deps on `-core`, `-ajc`, `-dexlib2` (factory needs to import the impls). Re-exports the public surface from `-core` so consumers can use `from rv_instrumentation import ...` for the canonical API.
- `rv-instrumentation-ajc` and `rv-instrumentation-dexlib2` each declare dep on `-core` ONLY (no dep on parent, no dep on the sibling). Inheritance from `Instrumenter` reaches into `-core`.
- Acceptance criterion AC-IMP-04 in `design.md` (`grep` for `RVInstrumentation` returns 0 hits) explicitly rules out reintroducing the legacy class name. AC-IMP-09 (no `def get_instrumenter` outside the canonical factory) rules out parallel factories.
- Future contributors promoting the helper to a different shape (e.g., registry pattern) must update this ADR first.

## References

- GitHub Issue: #53
- Phase 0 (chose Option A): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260428_plano_consolidacao_pos_gh50_gh51_gh52.md` §3.1
- Related change artifacts:
  - `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/proposal.md`
  - `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/design.md`
  - `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/specs/instrumentation/spec.md`
  - `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/tasks.md`
  - `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh53-consolidacao-instrumentation/RISKS.md`
- Precedent ADR: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md`
- gh52 INV-INS-18 (variant tag retrocompat — dívida herdada): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/specs/instrumentation/spec.md`
- gh52 task §15.4 (CLAUDE.md deferral closed by gh53): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/tasks.md` line 207
- gh52 task §17.2 (rename collision documented): same file, around line 230
- LSPatch (third variant horizon): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260422_lspatch.md`
- Project pattern reference (`AbstractTool` ABC): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py`
