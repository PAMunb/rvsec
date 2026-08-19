# `jca_android` — the successor specification set

This directory holds the records of the specification set that `--specification-set jca_android`
resolves to from gh104 on: `rvsec/rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen
`jca` Java set and shaped by three mechanical passes (two pure predicate propagators deleted, every
use of `ExecutionContext` removed, every allow-list re-transcribed from `MetaCrySL/generated/api30/`).

The oracle of the set is the already-generated MetaCrySL api30 rules under
`MetaCrySL/generated/api30/`. MetaCrySL is read-only in gh104: where a generated rule is judged
defective, the judgement is a row of `divergence_record.csv`, never an edit upstream.

## Freeze items

| item | value | what it pins |
|---|---|---|
| `pre-rename-head` | `a3e6a1651cc63d83525fcbb42c0cd5f659ef463e` | the Java tree's `HEAD` immediately before the `git mv` of task 2.1. Task 10.1 asserts the archival is a pure rename **against this SHA**, and it is also the read-only base of `AndroidCipherTransformationUtil.java`, which does not exist at `7e7acb69` (gh101 added it). |
| `jca` freeze base | `7e7acb69` | `rvsec-mop/src/main/resources/jca/` and `CipherTransformationUtil.java` are byte-identical to it and stay so (gh101 D-S0, INV-INS-109). |

## The archived derived set

`rvsec/rvsec-mop/src/main/resources/jca_android/` used to name the set gh101 derived against
generated CrySL rules. The 2026-08-08 audit (`audit/20260808_validacao_jca_android/`) reproved it on
its predicate machinery: 22 of the 23 files were in the audit's scope — `RandomStringPassword`, the
`@fail`-less propagator, was outside it — and every one of the 22 was reproved.

Task 2.1 moved that set unchanged to
`rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/` (23 `.mop`, `R100`, zero content
hunks). The name states why it is archived rather than what it used to be called, per P4.

**It is not selectable.** No `--specification-set` value points at it and none is added: the
enumeration keeps its four values (`jca`, `jca_android`, `generic`, `custom`), and the archived
directory name is rejected exactly like any other unknown string (task 2.9). Regenerating it is a
deliberate act — `--specification-set custom --custom-specs-dir <path to the archive>` — and that
deliberateness is the point.

It is a record, not an instrument: no gh104 task edits it, regenerates it or replays it. It is read
by the gh101 gate scripts, which task 2.13 repoints at it so gh101's freeze and divergence records
keep resolving (INV-INS-118), and by the identity checks of tasks 2.11 and 10.1.

## Records in this directory

| file | what it records |
|---|---|
| `divergence_record.csv` | one entry per hunk of the successor set against the frozen `jca` seed, plus the two registered exceptions to literal transcription (`EC`, the four `SHA*withECDSA`). |
| `conformance_record.csv` | one row per specification against its api30 rule: transcription verdicts, deferred constants, declared costs, and the divergences measured but not repaired. |
| `alias_table.csv` | the Conscrypt `android11-release` alias table (158 rows), carried as code by `ConscryptAliasTable`. |
| `predicate_removal.csv` | the 55 sites the predicate removal deleted, with the accusation each used to raise. Not to be confused with gh101's `predicate_omissions.csv`, which records a different thing — a `Property` written and never read. This set writes none (INV-INS-128). |
| `constraint_table.csv` | one row per api30 `CONSTRAINTS` clause of the 21 paired rules plus one per `.mop` value test with no clause behind it. |
| `gate_allowlist.csv` | the remaining gate hits with a reason and the task that owns each. |
