<!-- Dependency hints:
     - Group 1 is a gate — nothing generated afterwards is trustworthy until Android0108 reproduces.
     - Groups 2 and 3 touch disjoint files and can run in parallel after Group 1.
     - Group 4 needs both 2 and 3. Group 5 needs 4's generated rules as its anchor.
     - Group 6 needs 5's decisions in order to describe them.
     - Group 7 (Verification) runs last.
     - Every generation runs in a FRESH Rascal session — Loader.rsc never resets its
       module-level state, so a reused session contaminates the second target (plan §1.5). -->

## 1. Toolchain and baseline reproduction (gate, sequential)

- [ ] 1.1 Apply the two-line fix to `src/generator/PreProcessor.rsc`: replace `metaVariable(v) == var` with `v == var.varName` at `:45` (`bindObjectDecl`) and `:81` (`bindLiteralSet`). Root cause and proof in plan §1.4 — approved as the sole exception to the no-`.rsc`-edits rule
- [ ] 1.2 Record the working toolchain: `rascal-0.19.6.jar` + Java 8, run from inside the project directory so `META-INF/RASCAL.MF` puts `src/` on the search path. No pty required at 0.19.6
- [ ] 1.3 Rewrite `src`/`out` in `$WS/MetaCrySL/samples/jca/android/config/Android0108.config` to absolute paths under `$WS/MetaCrySL/samples/jca`. Paths must be absolute and must match `[a-zA-Z0-9/\-]*` — no `_`, `.` or `~`
- [ ] 1.4 Save the config with **no trailing newline** — `Parser.rsc` uses `parse(#ConfigurationDef, ...)`, not `#start[...]`, so a final `\n` is a parse error that fails silently
- [ ] 1.5 Generate `Android0108` in a fresh Rascal session; confirm the run prints `done` and writes 32 files (absence of `done` is the only failure signal — `Main.rsc` swallows exceptions)
- [ ] 1.6 Diff against `samples/jca/android/target/research/0108/`, normalising the ordering of elements inside `{...}` — `set[Literal]` has no stable iteration order, so raw byte comparison yields false differences. Expect 32/32 equivalent (already demonstrated on a scratch copy)
- [ ] 1.7 Consider upstreaming the fix to CROSSINGTUD/MetaCrySL as a pull request — it is a genuine defect that makes the published generator unusable on any current Rascal

## 2. Tier map and config repair (parallel with Group 3)

- [ ] 2.1 Read all 19 refinement tiers under `samples/jca/android/` and build the tier → specifications → constraint table
- [ ] 2.2 Validate the closed-window vs `XXplus` semantics (plan §1.1) against Android platform documentation for at least the five four-digit tiers
- [ ] 2.3 Rewrite `src`/`out` in `Android0116.config` and `Android25plus.config` to our absolute paths
- [ ] 2.4 Add the missing `17plus`, `19plus` and `23plus` loads to `android/config/Android25plus.config`
- [ ] 2.5 Regenerate `0116` and `25plus` in fresh sessions and record the delta introduced by the corrected omissions — expect `Signature`, `SecretKeyFactory` and `Cipher` to change

## 3. Authored specifications (parallel with Group 2)

- [ ] 3.1 Author `samples/jca/base/TrustManagerFactory.cryptsl`, modelled on `base/KeyManagerFactory.cryptsl`: `algo in {"PKIX"}`, events `getInstance`/`init`/`getTrustManagers`, `ENSURES generatedTrustManager[...]`
- [ ] 3.2 Confirm `generatedTrustManager` is no longer orphaned — it must now appear in an `ENSURES` clause, not only in `SSLContext.cryptsl:32`'s `REQUIRES`
- [ ] 3.3 Author `samples/jca/android/30plus/SSLContext.ref` with `define algorithm = {"TLSv1.3"};` (API 29)
- [ ] 3.4 Check whether any other spec gained algorithms at API 29 or 30; add refinements only for verified additions, do not pad the tier speculatively (P1)

## 4. Android30 generation and cross-check (needs 2 and 3)

- [ ] 4.1 Author `samples/jca/android/config/Android30.config`: `load spec base/` plus the 14 existing `XXplus` tiers with XX ≤ 30 and the authored `30plus`, with `out` at `generated/api30` — **not** `target/`, which `.gitignore` excludes, so output there would never be committed
- [ ] 4.2 Generate in a fresh session; confirm 33 `.cryptsl` files (32 base + `TrustManagerFactory`) and a `done`
- [ ] 4.3 Record the generated `SSLContext` protocol set verbatim — it is the evidence for the permissiveness finding (plan §1.3)
- [ ] 4.4 Diff the 33 generated rules against `$WS/rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/`; document the delta as the Android adaptation

## 4b. Fork deliverables — Group G (after 4, parallel with 5)

- [ ] 4b.1 Append a section to `$WS/MetaCrySL/README.md` documenting the reproducible procedure: Rascal 0.19.6 + Java 8, why the current `rascal-shell-stable.jar` does not work under Java 8 (class file 55), invocation from the project directory so `META-INF/RASCAL.MF` puts `src/` on the search path, and the exact command line
- [ ] 4b.2 In the same appendix, record the two-line fix and its cause (keyword parameters participate in equality; `implode` attaches `location`/`comments` that the code-built node lacks), so a reader understands why the fork diverges from upstream
- [ ] 4b.3 In the same appendix, record the two config constraints — no trailing newline after `}`, and `Path` accepts only `[a-zA-Z0-9/\-]` — plus the set-ordering caveat when diffing generated output
- [ ] 4b.4 Add `*.jar` to `$WS/MetaCrySL/.gitignore` so the two shells (195 MB combined) stay out of the commit
- [ ] 4b.5 Commit to the fork's `master`: the `PreProcessor.rsc` fix, the corrected configs, the authored `TrustManagerFactory.cryptsl` and `30plus/`, `Android30.config`, `generated/api30/` and the README appendix
- [ ] 4b.6 Open a pull request against CROSSINGTUD/MetaCrySL with the two-line fix alone — it makes the published generator unusable on any current Rascal

## 5. The `jca_android` specification set (needs 4)

- [ ] 5.1 Create `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/` and copy the 23 `.mop` files from `jca/` — explicitly NOT `MultiSpec_1MonitorAspect.aj` (stale residue carrying defect L2.7, plan §9.1)
- [ ] 5.2 Adapt `SSLContextSpec.mop` (L1.2) and `KeyStoreSpec.mop` (L1.1) from the generated rules
- [ ] 5.3 Adapt `TrustManagerFactorySpec.mop` and `KeyManagerFactorySpec.mop` to `{PKIX}` (L1.3)
- [ ] 5.4 Adapt `SecureRandomSpec.mop` (L1.4), `CipherSpec.mop` (L1.5) and `MessageDigestSpec.mop` (L1.7)
- [ ] 5.5 Review the remaining 16 `.mop` files against their generated counterparts; keep verbatim unless a generated rule contradicts them
- [ ] 5.6 Produce the traceability table: every `.mop` divergence anchored to a generated rule, or declared a hand translation (`RandomStringPassword.mop` has no counterpart and is declared as such)

## 6. Documentation (needs 5)

- [ ] 6.1 Write `docs/20260806_metacrysl_tier_map.md` with the tier table and the window/`plus` semantics
- [ ] 6.2 Record the `SSLContext` permissiveness as a threat to validity, stating explicitly that the bias inverts from false positives toward false negatives
- [ ] 6.3 Record the generator defects as optional debt: duplicated constraints (0/7/22 across targets `0108`/`0116`/`25plus`), unreset global state in `Loader.rsc`, swallowed exceptions in `Main.rsc`, absolute-path requirement
- [ ] 6.4 Update the F2 section of `docs/20260806_plano_specs_jca_android.md` to record that the set is MetaCrySL-derived, linking the tier map

## 7. Verification

- [ ] 7.1 Confirm the only change under `$WS/MetaCrySL/src/` is the approved two-line fix in `PreProcessor.rsc`, and that no `.jar` was committed
- [ ] 7.2 Run an end-to-end experiment with `--specification-set custom --custom-specs-dir <path to jca_android>` and confirm monitor generation succeeds
- [ ] 7.3 Run `/rv-verify rv-experiment` — the module that consumes the set via the `custom` path. No Python source changes in this change, so no lint-fix pass is warranted
- [ ] 7.4 Verify every acceptance criterion in `plan.md` §5
