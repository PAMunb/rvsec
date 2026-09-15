## Context

The `jca_android` set (`rvsec/rvsec-mop/src/main/resources/jca_android/`) holds 47 `.mop` specifications and `codes.csv`. Measured when the change was written: 9,093 lines, of which about 4,450 start with `//`, `/*` or `*`. The comments cite `INV-*` identifiers in 148 lines (44 files), decision identifiers in 83 lines (32 files), task numbers in 98 lines (25 files), dates or "researcher decisions" in 56 lines (15 files), CSV records in 109 lines (40 files), campaign measurements in 102 lines (25 files), `Other.mop:N` in 46 lines (28 files) and `Rule.crysl:N` in 352 lines (46 files). The helper classes `Property`, `ConscryptAliasTable`, `CipherTransformationNormalizer`, `ErrorType`, `ErrorDescription` and `ErrorSummary` carry the same kinds of reference.

The proposal (#116) rewrites only comments. The decisions below were taken by the researcher in the conversation that produced the change: comments are self-contained and carry no line numbers; the relation to the CrySL rule stays; the helper classes are included; `NEW_SPEC_CONVENTIONS.md` is updated; no monitor is generated and no gate or test is run, because nothing can change behaviour; `codes.csv` line anchors are updated after the comments; `Api30CipherTransformationUtil` moves to `backup/`; history that exists only in a comment is dropped; comments that already comply are kept; the documentation is detailed, one comment per event, read and write; the `.mop` header keeps this change's own structure; promotional language is forbidden; `codes.csv` may be named; the Java convention is written in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` and the helper classes follow it; trivial Java members are not documented; `IvChainJunction.mop` keeps its name; `divergence_record.csv` is out of scope. The change serves FR03 and FR13 without altering them.

## Architecture

There is no runtime architecture to change. The work is a set of file edits partitioned so that files describing the two ends of one predicate are rewritten by the same worker.

```
  WAVE 1 (parallel, 5 agents)
  ┌────────────┬──────────────┬────────────────┬──────────────────────┬────────────────┐
  1 citation   2 Java conv.   3 nine Java      4 Api30 backup, gate   5 predicate
    hash check   section        helper classes   entries, NEW_SPEC_     glossary
                 (dexlib2                        CONVENTIONS.md         (short)
                 CLAUDE.md)
  └────────────┴──────────────┴────────────────┴──────────────────────┴───────┬────────┘
                                                        wave 2 starts when 5 ends ▼
  WAVE 2 (parallel, 9 agents; each self-checks its files)
  ┌───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┐
  6 MGF1+  7 Cipher 8 Mac/  9 KeyGen 10 Params 11 Key 12 Alg. 13 TLS  14 Trust/
    Cipher   chain    digest  random   agreem.  mater.  params  ctx/cert keystores
  └───────┴───────┴───────┴───────┴───┬───┴───────┴───────┴───────┴───────┘
                                      ▼
  WAVE 3 (parallel, 4 reviewer agents over disjoint file sets)   15 · 16 · 17 · 18
                                      ▼
  19 codes.csv file_line · global @see read → 20 commit by path → opsx:verify → opsx:archive → issue
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `jca_android/*.mop` (47) | Specifications whose comments are reviewed | current comments, CrySL rules | same code, compliant comments kept, the rest rewritten |
| `rvsec-core/.../mop/{Property,PredicateStore,PredicateVerdict}.java` | Predicate store API whose comments are rewritten | current comments | rewritten comments |
| `rvsec-core/.../jca/util/{ConscryptAliasTable,CipherTransformationNormalizer}.java` | Value-resolution helpers whose comments are rewritten | current comments | rewritten comments |
| `rvsec-core/.../eh/{ErrorType,ErrorDescription,ErrorSummary,Evidence}.java` | Report types whose comments are rewritten | current comments | rewritten comments |
| `jca_android/codes.csv` | Code → emitting line anchor | rewritten `.mop` files | `file_line` column updated |
| `rv-android/data/jca_android/NEW_SPEC_CONVENTIONS.md` | Authoring guide for the next specification | the convention | rewritten guide |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` | Home of the Java documentation convention | the module's Javadoc practice, `rv-doc-code`, this change's rules | new "Documentation conventions" section |
| `Api30CipherTransformationUtil.java` + test | Uncalled class kept as history | — | moved to `backup/gh116/` |
| `rv-android/scripts/gh105_sole_oracle_gate.py` | Names the moved files in `EXEMPT_CORE` | — | two entries deleted |

## Mapping: Spec → Implementation → Test

No test is written or run, by decision. The right-hand column is the acceptance read that confirms the requirement.

| Requirement | Implementation | Acceptance read |
|-------------|---------------|-----------------|
| Documentation Convention — relation to the rule | Header and per-event comments of the 47 `.mop` | Every event, read and write names a rule label or quotes a clause |
| Documentation Convention — `@see` at the pinned commit | Header of each `.mop` (self-check; global read in group 19) | `grep -L 'Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b'` lists no file; only `CipherSpec` states the `CCM` difference |
| Documentation Convention — mechanism, divergences, toolchain limits | Comments of the 47 `.mop` | Glossary (group 5); per-worker self-check; independent review (groups 15–18) |
| Documentation Convention — Java convention section | Group 2 | `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` has a "Documentation conventions" section with the eleven rules and no identifiers |
| Documentation Convention — helper classes | Group 3 | Same reads over the nine classes, checked against the Java convention (trivial members without Javadoc); `CipherTransformationUtil.java` unchanged in `git diff --stat` |
| Documentation Convention — `NEW_SPEC_CONVENTIONS.md` | Group 4 | The document states the convention and cites no invariant, decision or `.mop` line |
| Documentation Convention — scope of the rewrite | All rewrite groups (self-check); `codes.csv` in group 19 | Comment-stripped token sequence identical before and after; every `file_line` names the emitting line |
| INV-INS-168 | All rewrite groups | Each worker's pattern read of its own files returns nothing in comments |
| MODIFIED Allow-List Conformance / Archived Derived Set | Group 4 move | `git grep Api30CipherTransformationUtil` outside `backup/`, `openspec/changes/archive/`, dated docs and data records returns nothing |

## Goals / Non-Goals

**Goals:**
- Every comment of the set and of its helper classes explains the code as it is and its relation to the CrySL rule, readable with the file alone.
- No non-comment token of any rewritten file changes.
- The authoring guide makes the next specification follow the same convention.
- The uncalled `Api30CipherTransformationUtil` leaves the tree.

**Non-Goals:**
- Changing any event, pointcut, condition, body, automaton, handler, message or code.
- Generating monitors, running gates or tests.
- Refreshing `data/jca_android/divergence_record.csv`, its script, or amending INV-INS-118. The record compares the set with the `jca` seed, which is no longer used; it goes stale.
- Touching the `jca` set, `CipherTransformationUtil`, `AndroidCipherTransformationUtil` or the archived `jca_android_bug_predicate` set.
- Removing the history embedded in `openspec/specs/instrumentation/spec.md` or the line references in data records (`constraint_table.csv`, `predicate_graph.csv`, `data/jca_android/README.md`).
- Changing the existing comments of `rvsec-instrumentation-dexlib2`, which cite invariant identifiers in 115 lines; the change only writes that module's convention section.

## Decisions

**D1 — A clause is cited by its text.** A comment quotes the section, the label and the clause (`REQUIRES` of `Cipher.crysl`: `generatedKey[key, alg(transformation)]`). A line number was rejected because it is correct in one version of one file; the clause text identifies the clause in every version and tells the reader what it says without opening the rule.

**D2 — Self-contained, repetition accepted.** The same mechanism (body versus `condition`, staging, unreachable `@fail`, three-valued read) is explained in each file where it occurs. A shared README the comments point to was rejected: it makes every comment depend on a second document, which is what the convention removes. The explanation is complete at each site, and the repetition this produces is accepted.

**D2a — Detailed on purpose; review, not rewrite.** The `rv-doc-code` skill's P1 guidance (skip self-evident code, prefer less documentation) does not apply to this set. Every event, predicate read and predicate write keeps its own comment, including events of one family that realise the same rule label (`CipherSpec`'s five `update` events), because a reader of a specification is deciding whether a missing check is an omission, and an uncommented event cannot answer that. The work is a review: a comment that already complies with the convention is kept verbatim, and only non-compliant comments are rewritten, so the diff shows exactly what the convention changed.

**D2b — The `.mop` header keeps its own vocabulary.** The header follows the structure in API Design — monitored class and rule, what the specification checks, divergences and reach limits, `@see` — and does not adopt `rv-doc-code`'s fixed `###` section names (`Architectural Decisions`, `Role in the System`, `Key Features`, `Integration Points`). Those names describe a Python component's place in a module; a specification header describes a transcription of a rule, and its sections are the rule's.

**D2c — The Java convention lives in the dexlib2 module's CLAUDE.md.** The module `rvsec-instrumentation-dexlib2` already documents its 90 main classes in a consistent Javadoc style: a class Javadoc on every class opening with a noun phrase, topical `<h2>`/`<h3>` sections, `{@code}`/`{@link}` throughout, `package-info.java` in every package, one-line field Javadoc, imperative method summaries with sparse `@param`/`@return`/`@throws`, and `// Phase N:` / `// Step N:` rationale blocks at the dense algorithms. The change writes that practice down as a "Documentation conventions" section of `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`, merged with the `rv-doc-code` conventions mapped onto Java (tiers, `Args`/`Returns`/`Raises` as tags without types, `State:` as field Javadoc, dictionary return schemas as `@return` key lists, `TODO(topic)`) and with the rules of this change (no identifiers, dates, `file:line`, `architecture.md` pointers, history or promotional language). The rules are listed in the delta spec requirement. The `rvsec-core` helper classes of this change follow that section. Trivial members are not documented (tier Skip): unlike a `.mop` event, a plain getter has no rule clause behind it whose absence a reader must interpret. Writing the section does not change any existing comment of the dexlib2 module.

**D3 — Only comments change; no monitor, gate or test.** A comment cannot change the generated monitor's behaviour, so generating it or running gates would verify nothing the edit can break. What an edit can break is a non-comment token touched by mistake; that is caught by each worker comparing its files with comments stripped against `HEAD`, not by a test.

**D4 — The upstream rule is cited at commit `6d844ab402229aaefa4c5e45bf080987b787624b`.** All headers cite `https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b/JavaCryptographicArchitecture/src/<Rule>.crysl`. The commit (merge of pull request #112 in `CROSSINGTUD/Crypto-API-Rules`, 2022-05-12, no tag) was found by hashing the JCA rules of all 851 upstream commits: the 49 rules CogniCrypt 5.0.1 ran over the dataset (`rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/`) are byte-identical to it, and the expert copy the set transcribes (pinned by `data/jca_android/oracle/expert_rules.sha256`) is identical in 48 of 49 rules; `Cipher.crysl` differs only by `CCM` in the AES mode clause and in the AES `NoPadding` clause. Its parent, the merge of #111, holds the same JCA rules, and `6d844ab` is the last commit before the next JCA change. Alternatives rejected: `blob/master`, because the branch moves; the `JavaCryptographicArchitecture` 3.1.4 ruleset that CogniCrypt 5.0.1 uses in its own tests, because 12 of its rules differ from what the set transcribes (BSI key sizes in `KeyPairGenerator` and `RSAKeyGenParameterSpec`, AES modes and PBE families in `Cipher`, the `Mac` ORDER) and it adds `PrivateKey` and `PublicKey`; `CROSSINGTUD/CryptSL`, because it holds the CrySL language and parser (4.0.5 for CogniCrypt 5.0.1) and no JCA rules. Only `CipherSpec`'s header states a difference from the cited rule, as behaviour: it also admits `CCM` for AES.

**D5 — A predicate glossary, not a human pilot.** Nobody reviews the output during implementation, so consistency comes from a shared glossary written first: one standard sentence per `Property` predicate the set writes or reads (`randomized`, `generatedKey`, `preparedIV`, …), stating what the predicate asserts about its object. Every wave-2 worker uses those sentences, so a producer and a consumer in different groups describe a predicate identically. `MGF1ParameterSpecSpec.mop` and `CipherSpec.mop` are an ordinary wave-2 group. The glossary is a working file of the implementation session, handed to the workers; it is not committed. A comment MAY name another specification of the set and its event as a predicate's producer or consumer, as the requirement states, provided the comment reads without opening that file.

**D6 — Three waves, groups by predicate chain and by size, no human wait.** Everything inside a wave runs in parallel, and no step waits for a person:

- **Wave 1 (five agents, no dependencies among them):** the citation check, the Java convention section of the dexlib2 `CLAUDE.md`, the nine Java helper classes (against the eleven Java rules of the delta spec, which exist before the section is written), the backup move with the authoring guide, and the predicate glossary. The glossary is the shortest of the five and is the only one wave 2 waits for.
- **Wave 2 (nine agents):** all 47 `.mop` files. Files at the two ends of a predicate stay with one worker where the chain allows, and no group exceeds about 1,500 lines, so the slowest worker does not hold the wave: the two largest groups of a chain-only split (key generation and randomness, about 2,600 lines; TLS and trust, about 2,500) are each divided in two. Each worker checks its own files before returning — comment-stripped token comparison against `HEAD`, the patterns INV-INS-168 forbids, the `@see` URL.
- **Wave 3 (four reviewer agents over disjoint file sets, about 3,000 lines each):** each reviewer reads every file of its set against the requirement and the glossary, fixes what departs from them, and re-runs the self-check on what it changed. A reviewer never reviews a group it wrote. This replaces a human approval.

Group 19 then updates the `file_line` column of `codes.csv`, which needs every `.mop` final, and reads the `@see` of all headers. The commit by path follows; `/opsx:verify` and `/opsx:archive` run after the commit.

**D7 — `Api30CipherTransformationUtil` moves; `AndroidCipherTransformationUtil` stays.** The first has no caller and no role except recording a withdrawn anchor, so it moves to `backup/gh116/` with its test (P3), the two requirements that state it stays are modified, and the two `EXEMPT_CORE` entries of `gh105_sole_oracle_gate.py` naming it are deleted. The second is imported by the archived set, which a requirement keeps byte-identical; moving it would break that set and is out of scope.

**D8 — What counts as a comment.** In `.mop` files: `//` line comments, `/* */` blocks and the `/** */` header. No `.mop` of the set has a comment trailing code on the same line (measured: 0), so a comment edit never shares a line with code. In Java: Javadoc, block and line comments. String literals — including report messages and `exp` texts — are code and are not edited, even when they read like prose.

**D9 — `codes.csv` anchors after the comments.** Once every `.mop` is rewritten, each row's `file_line` is recomputed as `<Spec>.mop:<line>` of the line that contains `code=<CODE> ` in that file. The computation is a throwaway command in the session scratchpad, not a committed script.

## API Design

No API changes. The convention each worker applies:

### File header (`.mop`)
```
/**
 * <Spec name>
 *
 * Monitors <fully qualified class> against the CrySL rule <Rule>.crysl.
 * <What it checks: ORDER summary; CONSTRAINTS enforced; REQUIRES read; ENSURES written.>
 * <Divergences from the rule and reach limits, each with its technical reason.>
 *
 * @see https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b/JavaCryptographicArchitecture/src/<Rule>.crysl
 */
```

### Event
```
// <Rule label(s)> of the rule: `<event text>`. <Clause checked in the body, quoted.>
// <Why the check is here and not elsewhere, when not obvious.> <What it reports.>
```

### Predicate read / write
```
// REQUIRES `<clause>`: <what SATISFIED, VIOLATED and NOT_OBSERVED produce>.
// ENSURES `<clause>` [after <label>]: <acceptance point and why it is staged>.
```

### Java helper class (per the dexlib2 "Documentation conventions" section)
```
/**
 * <Noun phrase: what the class is.>
 *
 * <p><What it does and why, in current state.>
 *
 * <h3><Topic></h3>
 * <Mechanism, contract (MUST / Postcondition:), hazards.>
 */

/**
 * <Imperative sentence ending in a period.>
 *
 * <p><Rationale when not obvious.>
 *
 * @param name <meaning, no type>
 * @return <value; keys when a map or JSON document>
 * @throws IllegalStateException if <condition>
 */
```
Self-evident getters, setters and `toString` carry no Javadoc.

### Forbidden in any comment
Line numbers of any file; `INV-*`, `D-*`, task, change or issue identifiers; dates; "decision of"; names or row numbers of the records under `data/jca_android/`; reports and campaign counts; the `jca` set; narrative of earlier states ("used to", "was", "no longer", "since", "withdrawn", "this commit"); promotional or bias language ("modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge", "advanced"). The set's own `codes.csv` may be named.

## Data Flow

1. Wave 1 runs five independent agents: the citation check, the Java convention section, the Java helper classes, the backup move with the authoring guide, and the predicate glossary.
2. When the glossary is written, wave 2 runs nine agents over the 47 `.mop` files; each reviews its files with the glossary, checks them, and returns its file list.
3. Wave 3 runs four reviewer agents over disjoint sets of the rewritten files; each fixes what departs from the requirement or the glossary.
4. Group 19 updates `codes.csv` and reads every `@see`; the change is committed by path; verification and archival follow.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| A non-comment token changed | A worker edited code or a string literal | Detected by the worker's own comment-stripped comparison before it returns | Restore the token from `HEAD` and re-check the file |
| A clause quoted incorrectly | Worker quoted from memory | Clause text is copied from the rule at `6d844ab` | Re-quote from the rule file |
| A divergence cannot be stated without history | The only rationale recorded is a decision | Worker states the behaviour and its technical cause; when the cause is not known, the comment states the behaviour only | The reviewer of wave 3 confirms the statement matches the code |
| The cited commit differs from the expert copy beyond `CCM` in `Cipher.crysl` | Hash check of group 1 | Group 1 lists each differing clause before wave 2 starts | The header of each affected specification states the difference as behaviour, as `CipherSpec` does for `CCM` |

## Risks / Trade-offs

- [A worker changes code while editing comments] → Each worker compares its own files with comments stripped against `HEAD` before returning.
- [Line references outside the scope go stale: `divergence_record.csv` hunk keys, `constraint_table.csv` `mop_line`, `predicate_graph.csv`, `data/jca_android/README.md`, `openspec/specs/instrumentation/spec.md`] → Accepted by decision; none of them is read at runtime.
- [The `--check` of `gh104_divergence_record.py` and the `code-anchor` family of gates fail if someone runs them] → The first is accepted (out of scope); the second is prevented by updating `codes.csv` in wave 3.
- [Repetition of the same mechanism across files] → Accepted (D2, D2a); each site is explained completely.
- [The expert copy stops matching the cited commit (48 of 49, `Cipher.crysl` differing only by `CCM`)] → Group 1 checks the hashes in wave 1; a new difference is stated as behaviour in the affected header.
- [Two workers describe one predicate differently] → The glossary (D5), chain grouping (D6) and the four wave-3 reviewers, who check every predicate description against the glossary.
- [No human review of the tone] → The requirement, the API Design templates and the glossary fix the form; four reviewer agents who did not write the files check every file against the requirement and fix what departs from it.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| — | None, by decision | Only comments change; per-worker self-checks and the wave-3 reviewers replace tests | 0 |

## Open Questions

Neither question blocks the implementation; both stay outside it.

- `rvsec-instrumentation-dexlib2/javadoc-improvement-plan.md` states that comments link to invariant identifiers and `architecture.md` sections, which contradicts the Java convention this change writes. Whether that plan is retired is not decided.
- Whether `rvsec/rvsec-core/CLAUDE.md` also gains the convention section (the helper classes live there) is not decided; until then the helper classes follow the section in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`.
