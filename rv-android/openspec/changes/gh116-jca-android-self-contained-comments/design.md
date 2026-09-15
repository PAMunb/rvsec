## Context

The `jca_android` set (`rvsec/rvsec-mop/src/main/resources/jca_android/`) holds 47 `.mop` specifications and `codes.csv`. Measured on the tree before #114: 9,093 lines, of which about 4,450 start with `//`, `/*` or `*`. The comments cite `INV-*` identifiers in 148 lines (44 files), decision identifiers in 83 lines (32 files), task numbers in 98 lines (25 files), dates or "researcher decisions" in 56 lines (15 files), CSV records in 109 lines (40 files), campaign measurements in 102 lines (25 files), `Other.mop:N` in 46 lines (28 files) and `Rule.crysl:N` in 352 lines (46 files). The helper classes `Property`, `ConscryptAliasTable`, `CipherTransformationNormalizer`, `ErrorType`, `ErrorDescription` and `ErrorSummary` carry the same kinds of reference.

The proposal (#116) rewrites only comments. The decisions below were taken by the researcher in the conversation that produced the change: comments are self-contained and carry no line numbers; the relation to the CrySL rule stays; the helper classes are included; `NEW_SPEC_CONVENTIONS.md` is updated; no monitor is generated and no gate or test is run, because nothing can change behaviour; `codes.csv` line anchors are updated after the comments; `Api30CipherTransformationUtil` moves to `backup/`; history that exists only in a comment is dropped; comments that already comply are kept; the documentation is detailed, one comment per event, read and write; the `.mop` header keeps this change's own structure; promotional language is forbidden; `codes.csv` may be named; `IvChainJunction.mop` keeps its name; `divergence_record.csv` is out of scope. The change serves FR03 and FR13 without altering them.

The change is applied **after #114**, which edits the same `.mop` files, adds report codes and `-ORDER-01`/`-ORDER-02` labels, and creates `eh/Evidence`. Every count above is re-measured at apply time.

## Architecture

There is no runtime architecture to change. The work is a set of file edits partitioned so that files describing the two ends of one predicate are rewritten by the same worker.

```
                          ┌────────────────────────────────────────────────┐
  Group 1 (precondition)  │ #114 applied · counts re-measured ·            │
                          │ pinned rule hashes re-checked                  │
                          └──────────────────────┬─────────────────────────┘
                                                 ▼
  Group 2 (pilot)         MGF1ParameterSpecSpec.mop + CipherSpec.mop → researcher approves tone
                                                 ▼
          ┌──────────┬──────────┬──────────┬─────┴────┬──────────┬──────────┬──────────┬──────────┐
  3 Cipher   4 Mac/    5 KeyGen/  6 Key      7 Param   8 TLS/     9 Java     10 Conven-
    chain      digest    random     material   specs     trust      helpers    tions+backup
          └──────────┴──────────┴──────────┴─────┬────┴──────────┴──────────┴──────────┘
                                                 ▼
  Group 11 (consolidation) cross-file consistency · codes.csv file_line · acceptance reads
                                                 ▼
  Group 12 (close)         opsx:verify · archive · commit by path · issue
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
| `Api30CipherTransformationUtil.java` + test | Uncalled class kept as history | — | moved to `backup/gh116/` |
| `rv-android/scripts/gh105_sole_oracle_gate.py` | Names the moved files in `EXEMPT_CORE` | — | two entries deleted |

## Mapping: Spec → Implementation → Test

No test is written or run, by decision. The right-hand column is the acceptance read that confirms the requirement.

| Requirement | Implementation | Acceptance read |
|-------------|---------------|-----------------|
| Documentation Convention — relation to the rule | Header and per-event comments of the 47 `.mop` | Every event, read and write names a rule label or quotes a clause |
| Documentation Convention — `@see` at the pinned commit | Header of each `.mop` | `grep -L 'Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b'` lists no file; only `CipherSpec` states the `CCM` difference |
| Documentation Convention — mechanism, divergences, toolchain limits | Comments of the 47 `.mop` | Pilot approved; consistency review of Group 11 |
| Documentation Convention — helper classes | Group 9 | Same reads over the nine classes; `CipherTransformationUtil.java` unchanged in `git diff --stat` |
| Documentation Convention — `NEW_SPEC_CONVENTIONS.md` | Group 10 | The document states the convention and cites no invariant, decision or `.mop` line |
| Documentation Convention — scope of the rewrite | All rewrite groups; `codes.csv` in Group 11 | Comment-stripped token sequence identical before and after; every `file_line` names the emitting line |
| INV-INS-168 | All rewrite groups | Pattern read of Group 11 returns nothing in comments |
| MODIFIED Allow-List Conformance / Archived Derived Set | Group 10 move | `git grep Api30CipherTransformationUtil` outside `backup/`, `openspec/changes/archive/`, dated docs and data records returns nothing |

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
- Any file of change #114.

## Decisions

**D1 — A clause is cited by its text.** A comment quotes the section, the label and the clause (`REQUIRES` of `Cipher.crysl`: `generatedKey[key, alg(transformation)]`). A line number was rejected because it is correct in one version of one file; the clause text identifies the clause in every version and tells the reader what it says without opening the rule.

**D2 — Self-contained, repetition accepted.** The same mechanism (body versus `condition`, staging, unreachable `@fail`, three-valued read) is explained in each file where it occurs. A shared README the comments point to was rejected: it makes every comment depend on a second document, which is what the convention removes. The explanation is complete at each site, and the repetition this produces is accepted.

**D2a — Detailed on purpose; review, not rewrite.** The `rv-doc-code` skill's P1 guidance (skip self-evident code, prefer less documentation) does not apply to this set. Every event, predicate read and predicate write keeps its own comment, including events of one family that realise the same rule label (`CipherSpec`'s five `update` events), because a reader of a specification is deciding whether a missing check is an omission, and an uncommented event cannot answer that. The work is a review: a comment that already complies with the convention is kept verbatim, and only non-compliant comments are rewritten, so the diff shows exactly what the convention changed.

**D2b — The `.mop` header keeps its own vocabulary.** The header follows the structure in API Design — monitored class and rule, what the specification checks, divergences and reach limits, `@see` — and does not adopt `rv-doc-code`'s fixed `###` section names (`Architectural Decisions`, `Role in the System`, `Key Features`, `Integration Points`). Those names describe a Python component's place in a module; a specification header describes a transcription of a rule, and its sections are the rule's.

**D3 — Only comments change; no monitor, gate or test.** A comment cannot change the generated monitor's behaviour, so generating it or running gates would verify nothing the edit can break. What an edit can break is a non-comment token touched by mistake; that is caught by reading the diff with comments stripped (Group 11), not by a test.

**D4 — The upstream rule is cited at commit `6d844ab402229aaefa4c5e45bf080987b787624b`.** All headers cite `https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b/JavaCryptographicArchitecture/src/<Rule>.crysl`. The commit (merge of pull request #112 in `CROSSINGTUD/Crypto-API-Rules`, 2022-05-12, no tag) was found by hashing the JCA rules of all 851 upstream commits: the 49 rules CogniCrypt 5.0.1 ran over the dataset (`rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/`) are byte-identical to it, and the expert copy the set transcribes (pinned by `data/jca_android/oracle/expert_rules.sha256`) is identical in 48 of 49 rules; `Cipher.crysl` differs only by `CCM` in the AES mode clause and in the AES `NoPadding` clause. Its parent, the merge of #111, holds the same JCA rules, and `6d844ab` is the last commit before the next JCA change. Alternatives rejected: `blob/master`, because the branch moves; the `JavaCryptographicArchitecture` 3.1.4 ruleset that CogniCrypt 5.0.1 uses in its own tests, because 12 of its rules differ from what the set transcribes (BSI key sizes in `KeyPairGenerator` and `RSAKeyGenParameterSpec`, AES modes and PBE families in `Cipher`, the `Mac` ORDER) and it adds `PrivateKey` and `PublicKey`; `CROSSINGTUD/CryptSL`, because it holds the CrySL language and parser (4.0.5 for CogniCrypt 5.0.1) and no JCA rules. Only `CipherSpec`'s header states a difference from the cited rule, as behaviour: it also admits `CCM` for AES.

**D5 — Pilot before fan-out.** `MGF1ParameterSpecSpec.mop` (small, one event, one predicate write) and `CipherSpec.mop` (largest, every mechanism) are rewritten first and approved by the researcher. The approved pair is the reference every worker of Groups 3–9 reads before writing.

**D6 — Groups by predicate chain.** Files at the two ends of a predicate are rewritten by the same worker, so a producer and its consumer describe the predicate in the same terms. The six `.mop` groups are listed in `tasks.md`; the Java helpers and the authoring guide are two more groups, and all eight run in parallel.

**D7 — `Api30CipherTransformationUtil` moves; `AndroidCipherTransformationUtil` stays.** The first has no caller and no role except recording a withdrawn anchor, so it moves to `backup/gh116/` with its test (P3), the two requirements that state it stays are modified, and the two `EXEMPT_CORE` entries of `gh105_sole_oracle_gate.py` naming it are deleted. The second is imported by the archived set, which a requirement keeps byte-identical; moving it would break that set and is out of scope.

**D8 — What counts as a comment.** In `.mop` files: `//` line comments, `/* */` blocks and the `/** */` header. No `.mop` of the set has a comment trailing code on the same line (measured: 0), so a comment edit never shares a line with code. In Java: Javadoc, block and line comments. String literals — including report messages and `exp` texts — are code and are not edited, even when they read like prose.

**D9 — `codes.csv` anchors after the comments.** Once every `.mop` is rewritten, each row's `file_line` is recomputed as `<Spec>.mop:<line>` of the line that contains `code=<CODE> ` in that file. The computation is a throwaway command in the session scratchpad, not a committed script.

## API Design

No API changes. The convention each worker applies, in the form the pilot will make concrete:

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

### Forbidden in any comment
Line numbers of any file; `INV-*`, `D-*`, task, change or issue identifiers; dates; "decision of"; names or row numbers of the records under `data/jca_android/`; reports and campaign counts; the `jca` set; narrative of earlier states ("used to", "was", "no longer", "since", "withdrawn", "this commit"); promotional or bias language ("modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge", "advanced"). The set's own `codes.csv` may be named.

## Data Flow

1. Group 1 re-measures the set after #114 and re-checks that the pinned rule hashes still match the cited commit.
2. Group 2 rewrites the pilot pair; the researcher approves or corrects the tone.
3. Groups 3–10 read the approved pilot and rewrite their files in parallel, each returning its file list and any divergence it could not state without history.
4. Group 11 reviews the cross-file descriptions, updates `codes.csv`, and performs the acceptance reads.
5. Group 12 verifies against the artifacts, archives, and commits by path.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| A non-comment token changed | A worker edited code or a string literal | Detected by the comment-stripped comparison of Group 11 | Restore the token from `HEAD` and re-check the file |
| A clause quoted incorrectly | Worker quoted from memory | Clause text is copied from the rule at `6d844ab` | Re-quote from the rule file |
| A divergence cannot be stated without history | The only rationale recorded is a decision | Worker states the behaviour and its technical cause; if none is known, reports the site | Researcher decides the wording in Group 11 |
| #114 not yet applied | Ordering | Group 1 stops the change | Apply #114 first |

## Risks / Trade-offs

- [A worker changes code while editing comments] → Comment-stripped comparison of every rewritten file in Group 11.
- [Line references outside the scope go stale: `divergence_record.csv` hunk keys, `constraint_table.csv` `mop_line`, `predicate_graph.csv`, `data/jca_android/README.md`, `openspec/specs/instrumentation/spec.md`] → Accepted by decision; none of them is read at runtime.
- [The `--check` of `gh104_divergence_record.py` and the `code-anchor` family of gates fail if someone runs them] → The first is accepted (out of scope); the second is prevented by updating `codes.csv` in Group 11.
- [Repetition of the same mechanism across files] → Accepted (D2); explanations kept to a few lines.
- [The expert copy stops matching the cited commit (48 of 49, `Cipher.crysl` differing only by `CCM`)] → Group 1 re-checks the hashes before any rewrite; a new difference stops the change.
- [Two workers describe one predicate differently] → Chain grouping (D6) and the consistency review of Group 11.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| — | None, by decision | Only comments change; acceptance reads in Group 11 replace tests | 0 |

## Open Questions

- The convention lets a comment name another specification of the set and its event as the producer or consumer of a predicate, provided the comment reads without opening that file. Confirm this reading of "self-contained" with the pilot.
