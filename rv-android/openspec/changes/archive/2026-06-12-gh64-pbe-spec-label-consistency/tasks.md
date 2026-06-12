# Tasks — gh64: PBE Spec Label Consistency

Execution of `plan.md`. All trees under
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/`.
Edit is a quoted-token replacement (`"PBEKeySpec"` → `"PBEKeySpecSpec"`,
`"PBEParameterSpec"` → `"PBEParameterSpecSpec"`); the closing quote makes it safe to apply
per file. Six files, inline (no subagents). Java type names / imports must NOT change.

## 1. Group A — rvsec-mop canonical source

- [x] 1.1 `rvsec-mop/src/main/resources/jca/PBEKeySpecSpec.mop`: 4 short-form `"PBEKeySpec"` labels → `"PBEKeySpecSpec"` (err1, err2, err3, @fail)
- [x] 1.2 `rvsec-mop/src/main/resources/jca/PBEParameterSpecSpec.mop`: 2 `"PBEParameterSpec"` labels → `"PBEParameterSpecSpec"` (c3, @fail)

## 2. Group B — rvsec-logger-csv copy

- [x] 2.1 `rvsec-logger-csv/src/main/mop/PBEKeySpecSpec.mop`: same 4-label fix
- [x] 2.2 `rvsec-logger-csv/src/main/mop/PBEParameterSpecSpec.mop`: same 2-label fix

## 3. Group C — docker example copy

- [x] 3.1 `docker/mop/example/PBEKeySpecSpec.mop`: same 4-label fix
- [x] 3.2 `docker/mop/example/PBEParameterSpecSpec.mop`: same 2-label fix

## 4. Verification

- [x] 4.1 `grep --include='*.mop'` over the 3 trees — zero short-form `"PBEKeySpec"`/`"PBEParameterSpec"` inside `addError(...)` (gitignored `.rvm` excluded — generated, regenerate from `.mop`)
- [x] 4.2 `git -C ../rvsec diff --stat` shows only the 6 `.mop` files changed (18 ins / 18 del); `SecretKeySpec*.mop`, `target/classes/`, `.rvm`, and `cc_rv_mapping.csv` untouched
- [x] 4.3 Confirmed Java type references (imports, event signatures, `returning(...)`) for PBEKeySpec/PBEParameterSpec unchanged — only quoted label literals edited (14 import lines intact; diff shows label-only hunks)
- [x] 4.4 Acceptance criteria in `plan.md` checked off
