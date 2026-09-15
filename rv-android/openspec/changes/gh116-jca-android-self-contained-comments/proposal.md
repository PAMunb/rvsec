# Self-Contained Comments for the `jca_android` Specification Set and Its Helper Classes

GitHub Issue: #116

## Why

The comments of the `jca_android` specification set (`rvsec/rvsec-mop/src/main/resources/jca_android/`, 47 `.mop` files) and of the `rvsec-core` classes the set calls describe the process that produced the code rather than what the code does. About half of the set's 9,093 lines are comments, and a large share of them cite OpenSpec invariants (`INV-INS-*`, 148 lines across 44 files), design decisions (`D-*`), task numbers, issues, dates and "researcher decisions", rows of the CSV records under `data/jca_android/`, the withdrawn generated catalogue, campaign measurements, and line numbers of other files (`Cipher.crysl:134`, `SecretKeyFactorySpec.mop:108`). A reader who did not follow the changes that built the set cannot tell from a comment what an event checks or why a check sits where it sits, and every line-number citation goes stale the moment either file is edited. This contradicts principle P4 (current-state comments) and P2 (self-contained documentation).

The part of those comments that is worth keeping is the relation to the CrySL rule each specification transcribes, and the explanation of the mechanism when it is not obvious at the site: why a clause is checked in the event body and not in `condition(...)`, why a predicate write is staged in a field, why an `@fail` handler cannot fire, why a read distinguishes a violated predicate from an unobserved one. This change keeps that and removes the rest.

## What Changes

- **Every comment of the 47 `.mop` files of `jca_android` is reviewed, and the non-compliant ones are rewritten**, so that each comment is self-contained and detailed; a comment that already complies is kept. Each comment explains what the code does now and which CrySL clause it realises, citing the clause by its text (section, label and the clause itself), never by line number. No comment refers to a change, issue, invariant, decision, task, date, record under `data/jca_android/`, measurement, report, another specification set, or a line of any file, and none uses promotional language; the set's own `codes.csv` may be named. Every event, predicate read and predicate write keeps its own detailed comment. Divergences from the rule and reach limits of the monitor stay, stated as behaviour with their technical reason. Rationale that only tells history is dropped. The file header's `@see` points to the rule in `CROSSINGTUD/Crypto-API-Rules` at commit `6d844ab402229aaefa4c5e45bf080987b787624b` — the rule set the CogniCrypt 5.0.1 baseline ran (49 of 49 rules byte-identical) and the one the specifications transcribe (48 of 49 identical to the expert copy they answer to; only `Cipher.crysl` differs, by also admitting `CCM` for AES). `CipherSpec.mop` is the one header that states that difference, as behaviour. `IvChainJunction.mop` keeps its name.
- **Only comments change.** Events, pointcuts, conditions, bodies, automata, handlers, report messages and codes are byte-identical in every non-comment token. No monitor is generated and no gate or test is run, because no behaviour can move. The only test and gate files touched are the consequences of the move below: the test of the moved class moves with it, and two exemption entries naming the moved files are deleted.
- **A Java documentation convention is written** as a "Documentation conventions" section of `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`: the Javadoc practice that module already follows, the `rv-doc-code` conventions mapped onto Javadoc, and the rules above (no identifiers, dates, `file:line`, history or promotional language). Trivial members — self-evident getters, setters, `toString` — get no Javadoc; only what matters is documented.
- **The comments of the helper classes the set calls are reviewed under that Java convention**, keeping those that comply: `Property`, `PredicateStore`, `PredicateVerdict`, `ConscryptAliasTable`, `CipherTransformationNormalizer`, `eh/ErrorType`, `eh/ErrorDescription`, `eh/ErrorSummary`, and `eh/Evidence`. `CipherTransformationUtil` is excluded: it is frozen byte-identical with the `jca` set.
- **`Api30CipherTransformationUtil` and its test move to `backup/`.** No specification calls the class; it survives only as a record of a withdrawn anchor, which is history and not system state. The two exemption entries naming it in `scripts/gh105_sole_oracle_gate.py` are removed so no reference dangles (P3).
- **`data/jca_android/NEW_SPEC_CONVENTIONS.md` is updated** so the next specification written for the set follows the convention, and its own text stops citing invariants, decisions and line numbers.
- **After the comments, the `file_line` column of `jca_android/codes.csv` is updated** to the line each code is now emitted from, because shorter comments move every report site.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`:
  - ADDED requirement for the documentation convention of the `jca_android` set and its helper classes.
  - MODIFIED "Allow-List Conformance to the Expert-Validated CrySL Rules" and "Cipher Transformation Tables of the Archived Derived Set", which state that `Api30CipherTransformationUtil` stays in the tree; they stop naming it.

## Impact

- **`rvsec/rvsec-mop/src/main/resources/jca_android/`** — comments of 47 `.mop` files; `file_line` column of `codes.csv`.
- **`rvsec/rvsec-core/src/main/java/br/unb/cic/mop/`** — comments of eight classes (nine with `Evidence`); `jca/util/Api30CipherTransformationUtil.java` and `src/test/java/.../Api30CipherTransformationUtilTest.java` moved to `backup/gh116/`.
- **`rv-android/data/jca_android/NEW_SPEC_CONVENTIONS.md`** — convention section rewritten.
- **`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`** — new "Documentation conventions" section; the module's existing comments are not changed.
- **`rv-android/scripts/gh105_sole_oracle_gate.py`** — two `EXEMPT_CORE` entries for the moved files removed.
- **No module of the uv workspace changes behaviour.** The generated monitor, the instrumented APKs and every report are unaffected; FR03 (Specification Set Support) and FR13 (Specification Violation Detection) are served exactly as before.
- **Out of scope:** `data/jca_android/divergence_record.csv`, its script and INV-INS-118 (the record compares `jca_android` with the `jca` seed; it goes stale and is not refreshed); the `jca` set; `AndroidCipherTransformationUtil` and the archived `jca_android_bug_predicate` set; the `Spec.mop:N` references inside `openspec/specs/instrumentation/spec.md`.
