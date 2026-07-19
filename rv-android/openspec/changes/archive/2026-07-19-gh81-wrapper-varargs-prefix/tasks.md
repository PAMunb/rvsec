# Tasks: gh81-wrapper-varargs-prefix

<!-- Java-only change (rvsec-instrumentation-dexlib2/advice-emitter). Verification is
     Maven-based; the Python-module skills (/rv-test-run, /rv-qa-lint-fix, /rv-verify)
     do not apply. Sub-reactor root (note the rvsec/rvsec in the path):
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/ -->

## 1. Regression Test (RED)

- [x] 1.1 Confirm `WrapperEmitterTest.indexExpansionAppliesTrailingVarargsPrefixFilter` (already in the working tree) fails with `expected: <2> but was: <3>` via `mvn -pl advice-emitter -am test -Dtest=WrapperEmitterTest -Dsurefire.failIfNoSpecifiedTests=false`

## 2. Fix expandCallTarget (GREEN)

- [x] 2.1 In `advice-emitter/src/main/java/br/unb/cic/rv/emitter/WrapperEmitter.java`, set `fixedPrefix = specs.size()` for trailing varargs (delete the `- 1` and the `< 0` clamp); update the comment to state the parser contract (P4: current-state only)
- [x] 2.2 Delete the dead dual-representation branch in the specs loop: any `".."` `ParamSpec` in `specs` returns `Collections.emptyList()` (non-trailing wildcard, no finite lowering); remove `if (i == specs.size() - 1) hasTrailingVarargs = true;` so `hasTrailingVarargs = ct.varargs()` is the single source of truth
- [x] 2.3 Run `mvn -pl advice-emitter -am test -Dtest=WrapperEmitterTest -Dsurefire.failIfNoSpecifiedTests=false` — the regression test and all existing WrapperEmitterTest tests pass

## 3. Full-Suite Verification

- [x] 3.1 Run the full module suite `mvn -pl advice-emitter -am test` and confirm all tests green (surefire reports)
- [x] 3.2 Confirm the corpus-shaped cases are unchanged: `(..)` empty-prefix expansion still returns all overloads (`expandsVarargsViaIndex`) and middle-`..` is still rejected (`literalFallbackSkipsMidListWildcardParam` + index path)
- [x] 3.3 Run the sibling consumers' suites that exercise wrappers (`mvn -pl dex-mutator,cli -am test` or full reactor `mvn test` at the sub-reactor root) to confirm no downstream breakage

## 4. Docs & Spec Reconciliation

- [x] 4.1 Update INV-INS-66/68 wrapper-generation invariant wording in `rvsec-instrumentation-dexlib2/architecture.md` to state trailing-varargs prefix fidelity (all fixed params verified, including the last)
- [x] 4.2 Run `/rv-code-reviewer` on the change

## 5. Commit

- [x] 5.1 Commit production fix + regression test + architecture.md together (one consistent state, P3) using absolute paths (mind `rvsec/rvsec`), message referencing `refs #81`; no Co-Authored-By; do not push
