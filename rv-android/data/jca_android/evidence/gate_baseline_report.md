# gh105 — the gate baseline, measured before the first edit

What every gh105 gate reports on the unmodified specification universe. It is the
reference each pytest wrapper is registered against (design D-13): the wrappers assert
*no finding outside this set*, so a group lands as a drop in these numbers and a
regression lands as a finding nobody recorded. Task 7.6 deletes the mechanism once the gates stand on their own.

## The universe, enumerated

| set | files | read | skipped | predicate sites |
|---|---|---|---|---|
| `jca` | 23 | 22 | 1 | 106 |
| `jca_android` | 24 | 24 | 0 | 46 |
| `jca_android_bug_predicate` | 23 | 22 | 1 | 147 |
| `generic` | 118 | 118 | 0 | 0 |
| `generic_new` | 27 | 27 | 0 | 0 |
| **total** | **215** | **213** | **2** | | 

Every skipped file carries its reason:

- `jca/SecretKeySpecSpec.mop` — unbalanced parenthesis: unmatched `)` at line 30
- `jca_android_bug_predicate/SecretKeySpecSpec.mop` — unbalanced parenthesis: unmatched `)` at line 30

## The structural suite

| gate | findings |
|---|---|
| G-ORDER | 4 |
| G-PRED2 | 9 |
| **failing total** | **13** |

Informative (reported in sets these gates do not govern): 21. Allow-listed (permanent, with reasons): 0.

Gates scoped away from a set say so, with the reason:

- INV-INS-130 over `jca` — the import, placement and closure contract governs the migrated set only; `jca` is frozen or predicate-free
- INV-INS-133 over `jca` — the import, placement and closure contract governs the migrated set only; `jca` is frozen or predicate-free
- INV-INS-134 over `jca` — the import, placement and closure contract governs the migrated set only; `jca` is frozen or predicate-free
- G-PRED2 over `jca` — the import, placement and closure contract governs the migrated set only; `jca` is frozen or predicate-free
- INV-INS-130 over `jca_android_bug_predicate` — the import, placement and closure contract governs the migrated set only; `jca_android_bug_predicate` is frozen or predicate-free
- INV-INS-133 over `jca_android_bug_predicate` — the import, placement and closure contract governs the migrated set only; `jca_android_bug_predicate` is frozen or predicate-free
- INV-INS-134 over `jca_android_bug_predicate` — the import, placement and closure contract governs the migrated set only; `jca_android_bug_predicate` is frozen or predicate-free
- G-PRED2 over `jca_android_bug_predicate` — the import, placement and closure contract governs the migrated set only; `jca_android_bug_predicate` is frozen or predicate-free
- INV-INS-130 over `generic` — the import, placement and closure contract governs the migrated set only; `generic` is frozen or predicate-free
- INV-INS-133 over `generic` — the import, placement and closure contract governs the migrated set only; `generic` is frozen or predicate-free
- INV-INS-134 over `generic` — the import, placement and closure contract governs the migrated set only; `generic` is frozen or predicate-free
- G-PRED2 over `generic` — the import, placement and closure contract governs the migrated set only; `generic` is frozen or predicate-free
- INV-INS-130 over `generic_new` — the import, placement and closure contract governs the migrated set only; `generic_new` is frozen or predicate-free
- INV-INS-133 over `generic_new` — the import, placement and closure contract governs the migrated set only; `generic_new` is frozen or predicate-free
- INV-INS-134 over `generic_new` — the import, placement and closure contract governs the migrated set only; `generic_new` is frozen or predicate-free
- G-PRED2 over `generic_new` — the import, placement and closure contract governs the migrated set only; `generic_new` is frozen or predicate-free

## Retired

A gate a group has driven to zero. Its rows left the baseline, so it is expected to
be silent from here on and its next finding is a regression rather than an
expectation. `--write` carries these forward and never re-baselines them.

- **G-ACC** — retired by task 3.7, 17 findings at the baseline. the 17 orphan accusers of jca_android, closed by Group 3: 12 negated twins fused into their siblings on 11 arrows, PBEKeySpecSpec.err1 fused on the same arrow as err2/err3, and 4 absorbed into their automata (SecureRandomSpec.g4 and PBEKeySpecSpec.f1/f2 with self-loops and an ORDER-unmapped row; KeyPairGeneratorSpec.initError as an Inits alternative mapped to i3). The gate is now expected to be silent over jca_android in both directions, so a finding it reports is a regression and not an expectation. The generic set's one orphan is informative and was never in this record.
- **INV-INS-130** — retired by task 4.15, 23 findings at the baseline. the 23 specifications of jca_android that named ExecutionContext, driven to zero by task 4.14: the seven files of its batch plus the two dangling imports left in CipherInputStreamSpec and CipherOutputStreamSpec, which had no use at all. The check is a whole-word grep over the set and counts mentions in comments and strings too, so the migration is complete in prose as well as in code. No specification of the set may name the old substrate again.
- **INV-INS-133** — retired by task 4.15, 27 findings at the baseline. the 27 predicate reads jca_android evaluated inside condition(...), driven to zero by task 4.12, which moved the last of them -- SecretKeySpec.e1 -- into its event body. Group 3 took 16 of the 27 away by fusing the guarded twins; the Group-4 file passes relocated the rest, and tasks 4.9 and 4.11 deleted four whose reads governed nothing any api30 rule asks for. Every read this change still adds belongs in a body by INV-INS-133, so a guard reported here from now on is a new one and not a leftover.
- **INV-INS-134** — retired by task 4.15, 42 findings at the baseline. the 42 predicate writes placed away from their rule's acceptance point with no recorded reason, driven to zero by task 4.14, which cleared the last eight over six files: six moved to the acceptance point, and two -- KeyManagerFactorySpec.gkm1 and TrustManagerFactorySpec.gtm1, whose transitions leave the accepting state for start, so an acceptance-point write would never run -- stayed in the event body and gained the reason the gate reads. The gate was never a ban on writing in the body: seven sites still do, each with its reason in the predicate_graph.csv row beside it. Retiring it says the accounting is complete, not that the sites are gone -- a write Group 5 or 6 adds off the acceptance point with no reason is a regression.

## G-ORDER

6 specifications equivalent to their api30 rule, 4 divergent, 205 skipped of 215 enumerated. Each divergence carries the shortest word the two languages disagree on:

- `jca_android/CipherSpec` — `f2` is accepted by the api30 ORDER and rejected by the specification
- `jca_android/SSLContextSpec` — `g1 Init se1 se1` is accepted by the specification and rejected by the api30 ORDER
- `jca_android/SecureRandomSpec` — `c1 c1` is accepted by the specification and rejected by the api30 ORDER
- `jca_android/TrustManagerFactorySpec` — `g1 i1 gtm` is accepted by the api30 ORDER and rejected by the specification
