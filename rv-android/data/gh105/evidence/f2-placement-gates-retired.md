# Tasks 4.15 and 4.16 — the placement gates are green, and now they are retired

**Date**: 2026-08-22 · **Change**: gh105-predicate-wiring · **Tasks**: 4.15, 4.16
**Files edited**: `data/jca_android/gate_baseline.json`,
`data/jca_android/evidence/gate_baseline_report.md`, `scripts/gh105_gate_baseline.py`,
`tests/parity/test_gh105_predicate_gates.py`.
**Specifications edited**: none. No `.mop` of any set is touched by this pass, so it writes no
divergence hunk, no trace and no graph row.

This is a checking task, and the checking found one thing to do. Every item the task lists was
already satisfied when the task opened — by tasks 4.12 and 4.14, not by this one — but the
*second half of its own title* was not: three gates had reached zero and none of them had been
retired. Until they are, a regeneration of the baseline silently re-records whatever they report
on a bad day, which is the one failure the mechanism exists to prevent.

---

## The five items, and what each was checked against

| item | invariant | measured | who took it there |
|---|---|---|---|
| zero `condition` reads | INV-INS-133 | gate reports 0; `read:condition-guard` rows in `predicate_graph.csv` = 0; the set census re-derives `read_placement["condition"] == 0` from the 23 `.mop` files | **task 4.12** |
| write placement green | INV-INS-134 | `test_inv_ins_134_write_placement` passes; all **7** `write:body` rows carry a non-empty `reason` | **task 4.14** |
| import discipline | INV-INS-130 | `grep -rlw ExecutionContext` over the set → **0 of 23**; the gate names the same file set | **task 4.14** |
| accepting-state calls | INV-INS-147 | `grep -c ObjectAsInAcceptingState` over the set → **0**; the census asserts `accepting-state + accepting-state-unset == 0` | **task 4.14** |
| trace pair per moved read | — | table below: 13 of the 14 moved reads carry a committed pair, and the fourteenth cannot have one for a reason measured at task 3.5 | tasks 4.1–4.12 |

The first four are each checked twice on purpose — once by the gate, once by a literal read of
the tree that does not go through the gate. A gate that stopped looking would otherwise read as
green, which is the failure mode of every zero that nobody re-derives.

```
$ grep -rlw ExecutionContext $SPECS/jca_android/*.mop | wc -l      → 0
$ grep -rn ObjectAsInAcceptingState $SPECS/jca_android/*.mop | wc -l → 0
$ grep -rn "remove(" $SPECS/jca_android/*.mop | wc -l               → 0
$ uv run python scripts/gh105_predicate_graph.py --sets jca_android \
    | grep -oE "\[INV-INS-[0-9]+\]|\[G-[A-Z0-9']+\]" | sort | uniq -c → 10 [G-PRED2]
$ uv run python scripts/gh105_gate_baseline.py                       → no finding outside the recorded baseline
$ uv run pytest tests/parity/test_gh10{1,4,4,5}_*.py                  → 94 passed
```

The ten G-PRED2 findings are not a leftover of this task and are not treated as one. Each is a
write whose consumer Group 5 has still to wire — `ENCRYPTED`×2, `PREPARED_DH`, `PREPARED_GCM`,
`PREPARED_HMAC`, `PREPARED_IV`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_STORE`, `SPECCED_KEY`,
`GENERATED_TRUST_MANAGER` — and the sweep at task 5.11 is what closes them. They stay in `gates`
because they are a live expectation.

---

## The trace pair per moved read

The graph holds 14 `read:body` rows and one `negate:body`. A pair is *committed* when both a
trace where the read answers `SATISFIED` and a trace where it does not are in
`data/gh104/traces/` — all 101 are tracked and the working tree is clean. The two columns below
are read off the cumulative harness reports in `data/gh105/evidence/harness/`, whose **B** column
is the tree as it stands: a silent B is the satisfied side, and a B that accuses at the read's own
event is the unobserved side.

| read | satisfied (B silent) | not observed (B accuses at the read) |
|---|---|---|
| `CipherSpec.i2` / `GENERATED_KEY` | `SecretKeySpecSpec-cipher-chain.txt` | `CipherSpec.txt` → `i2` |
| `CipherSpec.i2` / `GENERATED_PUBLIC_KEY` | `KeyPairSpec-public-cipher.txt`, `KeyPairSpec-generated-cipher.txt` | `CipherSpec.txt` → `i2` |
| `CipherSpec.i2` / `GENERATED_PRIVATE_KEY` | `KeyPairSpec-private-cipher.txt` | `CipherSpec.txt` → `i2` |
| `GCMParameterSpecSpec.c1` | `GCMParameterSpecSpec.txt` | `-unrandomised.txt` → `c1` |
| `GCMParameterSpecSpec.c2` | `-second-overload.txt` | `-second-overload-unrandomised.txt` → `c2` |
| `IvParameterSpec.c1` | `IvParameterSpecSpec.txt` | `-unrandomised.txt` → `c1` |
| `IvParameterSpec.c2` | `-offset.txt` | `-offset-unrandomised.txt` → `c2` |
| `PBEKeySpecSpec.c1` / salt | `PBEKeySpecSpec-salt-only.txt` | `PBEKeySpecSpec.txt` → `c1` |
| `PBEKeySpecSpec.c1` / password | **none exists** — see below | `PBEKeySpecSpec.txt`, `-salt-only.txt` → `c1` |
| `PBEParameterSpecSpec.c1` | `-randomised.txt` | `PBEParameterSpecSpec.txt` → `c1` |
| `PBEParameterSpecSpec.c2` | `-threearg-randomised.txt` | `-threearg.txt` → `c2` |
| `SecretKeySpec.e1` | `SecretKeySpec-encoded-iv.txt`, `-keygen-iv.txt` | `-hardcoded-iv.txt` → `IvParameterSpecSpec.c1` |
| `SecretKeySpecSpec.c1` | `SecretKeySpecSpec.txt` | `SecretKeySpec-hardcoded-iv.txt` → `c1` |
| `SecureRandomSpec.setSeed2` | `-randomised-seed.txt` | `-unrandomised-seed.txt` → `setSeed2` |
| `PBEKeySpecSpec.c2` (`negate`) | `PBEKeySpecSpec.txt` withdraws after `c1` | no reader of `SPECCED_KEY` yet — G-PRED2 row, task 5.4 |

Three of these need their imprecision stated rather than hidden.

**`SecretKeySpec.e1` accuses nothing on either side**, and its pair is measured one link
downstream: the read decides whether there is anything to carry, so `-encoded-iv.txt` propagates
`RANDOMIZED` and `IvParameterSpec` is silent, while `-hardcoded-iv.txt` stages nothing and
`IvParameterSpecSpec.c1` accuses. That is the whole point of the site, and it is why the pair
belongs to the consumer's report and not to this one.

**The salt read's two sides are indistinguishable in the harness.** Both `PBEKeySpecSpec.txt` and
`-salt-only.txt` show one `PBEKEYSPEC-NOBS-00` at `c1` in B, because `ErrorCollector.getErrors()`
returns a `Set` keyed on the summary and the two reads of that event produce the same one. What
separates them is *which* read fired, and that was measured at task 4.6 with the counting probe
over the whole collector, not with the harness. The pair is committed; the harness is simply not
the instrument that tells them apart.

**The password read has no satisfying side and cannot get one.** `randomized[password]` reads a
`char[]` that only `RandomStringPassword` could ever have marked, through a
`String.valueOf(Object)` → `toCharArray()` chain the `TraceRunner` cannot replay — its resolver
matches declared parameter types rather than assignability. Task 3.5 measured that and dropped
its trace rather than commit one with unresolved lines; task 4.11 then deleted the
`RandomStringPassword` bridge outright, because it stamped `randomized` on a heap address. So the
producer is gone by decision and the harness could not reach it anyway. This is a recorded
absence, not an unchecked item, and it is the only one of the fourteen.

---

## What this task actually did: the three retirements

The baseline opened this change with six gate blocks. Three of them — INV-INS-133 (27),
INV-INS-134 (42), INV-INS-130 (23) — reached zero during Group 4 and their keys simply
*disappeared* from `gates`, because `--write` records what a gate reports and they report
nothing. G-ACC did not disappear that way: task 3.7 put it in `retired`, and `retire()` refuses
to re-baseline anything listed there.

The difference is not cosmetic. Measured on the tree as it stood before this pass, by handing
`retire()` a fresh payload that pretends every gate found something:

```
  [G-ACC] retired by task 3.7 and still reporting 1 finding(s)      ← refused
what a regeneration would have recorded:
   INV-INS-133 [['jca_android', 'CipherSpec.mop', 'i2/GENERATED_KEY']]
   INV-INS-130 [['jca_android', 'KeyStoreSpec.mop', 'ExecutionContext']]
   INV-INS-134 [['jca_android', 'KeyStoreSpec.mop', 'match/X']]
```

A `--write` on a day the tree had drifted would have quietly restored the expectation that tasks
4.12 and 4.14 removed — the failure the `8fdf73fd` commit message names as the reason `retire()`
exists at all. After the three retirements, the same measurement:

```
  [G-ACC]      retired by task 3.7  and still reporting 1 finding(s)
  [INV-INS-130] retired by task 4.15 and still reporting 1 finding(s)
  [INV-INS-133] retired by task 4.15 and still reporting 1 finding(s)
  [INV-INS-134] retired by task 4.15 and still reporting 1 finding(s)
what a regeneration would record: {'G-PRED2': [[...]]}
```

The asymmetry is the point: the four retired gates are refused, and G-PRED2 — Group 5's live
expectation — still goes through.

**Three decisions were taken to the researcher and ratified** (see below). The entries carry
`task: "4.15"` because the *decision* is this pass's, and `was:` the count each gate reported on
the unmodified tree, the same convention as G-ACC's 17. Each note names the pass that drove the
number to zero, which was never 4.15:

| gate | `was` | driven to zero by | how |
|---|---|---|---|
| INV-INS-133 | 27 | task 4.12 | Group 3 fused 16 away with their guarded twins; Group 4 relocated 7 and deleted 4 that governed nothing api30 asks for; 4.12 moved the last, `SecretKeySpec.e1` |
| INV-INS-134 | 42 | task 4.14 | cleared the last 8 findings over 6 files — 6 to the acceptance point, and `gkm1`/`gtm1` kept in the body with the reason the gate reads |
| INV-INS-130 | 23 | task 4.14 | the 7 files of its batch plus the 2 dangling imports in `CipherInputStreamSpec` and `CipherOutputStreamSpec` |

Note what INV-INS-134's retirement does *not* say. Seven writes still sit in event bodies. The
gate was never a ban on that — it demands the reason, recorded in the row's own `reason` column —
so retiring it says the accounting is complete, not that the sites are gone. A write Group 5 or 6
places off the acceptance point with no reason is now a regression.

`--write` was run afterwards and reproduced the hand-written JSON byte for byte, so the mechanism
and the edit agree; the report gained its three lines under `## Retired`.

---

## Everything else this task changed, and why

`test_a_retired_gate_leaves_the_baseline_and_stays_out` knew only about G-ACC. It now asserts all
four retirements — gate absent from `gates`, `task`, `was`, non-empty note — plus the negative
half, that G-PRED2 is still *in* `gates`, and hands `retire()` a payload reporting on all four at
once. A retirement nothing asserts is a comment.

Three wrapper docstrings had gone stale, and one of them was stale in the direction that hides
work: `test_inv_ins_130_import_discipline` still said the gate "today reports all 23 files of the
set". All three now say what the gate reports, who took it there, and that the subset assertion
has become the zero assertion — the shape `test_inv_ins_135_gacc` has carried since task 3.7.

The three censuses each gained their line. All three say the same thing, which is the honest
thing: **task 4.15 moved no counter.** It edits no specification, emits no graph, and its value
is entirely in what it checked and what it retired.

`retire()`'s own docstring named G-ACC and task 3.7 as though the closer and the retirer were
always the same task. Here they are not, and it now says so.

---

## Gate state after the task

| gate | before | after |
|---|---|---|
| INV-INS-130 | 0 | 0 (**retired**) |
| INV-INS-133 | 0 | 0 (**retired**) |
| INV-INS-134 | 0 | 0 (**retired**) |
| INV-INS-147 (accepting-state calls) | 0 | 0 |
| G-ACC | 0 (retired at 3.7) | 0 (retired) |
| G-PRED2 | 10 | 10 — Group 5's, closed by task 5.11 |
| G-ORDER | 4 divergences (+1 invisible, finding 53) | unchanged |
| rows in `predicate_graph.csv` | 45 | 45 |
| hunks in `divergence_record.csv` | 277, all recorded | 277, all recorded |
| traces | 101, all committed | 101, all committed |
| assertions in the four gate suites | 94 | 94 |

`git diff --stat` over `$SPECS/jca_android` is empty, and over
`data/gh105/evidence/harness/` it is empty too: no specification changed, so no report could.

---

## Decisions ratified by the researcher (2026-08-22)

46. **Retire all three placement gates, not a subset.** INV-INS-134 was the one worth arguing —
    its seven sites survive with reasons, so the gate is silent by justification rather than by
    absence — but the criterion for retiring is whether the gate is *expected* to be silent from
    here on, and it is: Group 5 adds reads (which INV-INS-133 requires in bodies), writes (which
    INV-INS-134 requires accounted for) and must not reintroduce the old substrate. G-PRED2 and
    G-ORDER are explicitly not touched.
47. **`task: "4.15"`, `was:` the opening count, and the closer named in the note.** The script
    prints "retired by task X" and the decision is this pass's; the `was` follows G-ACC's 17,
    which is what the gate reported on the unmodified tree and therefore the size of the problem
    closed. Attributing the entry to 4.12/4.14 would read as history but would misname who
    decided.
48. **The pass extends to the test and the docstrings, not only the JSON.** A retirement with
    nothing asserting it is decoration, and two of the three stale docstrings state numbers the
    tree contradicts.

---

## Task 4.16 — `tests/parity` in full

The four gate suites are 94 assertions of the 155 `tests/parity` collects. Run whole:

```
$ export ANDROID_SDK_HOME=$ANDROID_HOME     # without it, see below
$ uv run pytest tests/parity --import-mode=importlib -o "addopts=" -q
3 failed, 152 passed in 166.64s
```

**The three reds are pre-existing and none of them is gh105's.** That is measured, not argued:
the four files this pass edits were reverted to `HEAD`, the same selection was re-run, and the
same three failed with the same messages.

| red | what it is | owner |
|---|---|---|
| `test_baseline_freshness::test_baseline_not_older_than_jar` | `lib/gator/rvsec-analysis-client.jar` is 83 days newer than `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`; the test compares mtimes and asks for the regeneration gh60 task 11.8 defines | gh60 |
| `test_no_legacy_mop::test_repo_is_clean` | six `reachesMop` occurrences in `modules/aperv-tool/` (three in `derive_mop_artifact.py`, one of them live code at `:1158`, three in its test), introduced by gh96's `affc574c` | **a decision, not a fix** — see below |
| `test_sentinel_emission::test_real_gator_json_parses_with_complete_true` | `StaticAnalysisParser.parse_file()` takes 2 positional arguments and the test passes 3: commit `bd10fb0f` dropped the package argument and left this caller behind. Verified against the tree — the signature at `static_analysis_parser.py:205` is `parse_file(self, file_path)` | rv-static-analysis |

The `reachesMop` red is worth naming as what it is, because it will not go away by itself: gh60's
gate forbids the token and gh96 deliberately renames `reachesTarget` → `reachesMop` **on the
wire**. The two changes are in direct conflict, and somebody has to decide whether the gate gains
an aperv-tool exemption or gh96 picks a different wire key. Nothing here should be repaired
inside gh105.

**And a fourth thing the run exposes, which is a measurement of defect D1.** Without
`ANDROID_SDK_HOME` in the environment the same suite reports **3 failed, 145 passed, 7 errors**:
`test_reachability_parity` (3) and `test_sentinel_emission` (4) error out on
`KeyError: 'ANDROID_SDK_HOME'`, and `test_signature_file_subset` fails for the same reason. That
is D1 of `docs/20260821_relatorio_analise_estatica_defeitos.md` — the GATOR path not being given
the SDK — showing up in the test suite rather than in an experiment run. Exporting the variable
turns eight of those nine green. It is out of scope for this change and stays unrepaired here,
but it is worth knowing that **`tests/parity` reads differently depending on one environment
variable**, and that the harsher reading is the default one.

---

## For the next task

Group 5, which task 4.3 unblocked: its order is topological by the design ledger, 5.1 is the
pilot chain, and `data/gh105/evidence/f2-write-only-batch-b.md` already measured for 5.9 what
each of the three producers it inherits writes and where.

One thing this pass did *not* do, deliberately: the ten G-PRED2 rows were re-read and left alone.
When task 5.11 closes them, that gate is the fourth candidate for retirement, and the entry it
will want is the one this task wrote three of.
