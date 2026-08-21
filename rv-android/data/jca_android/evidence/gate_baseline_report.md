# gh105 — the gate baseline, measured before the first edit

What every gh105 gate reports on the unmodified specification universe. It is the
reference each pytest wrapper is registered against (design D-13): the wrappers assert
*no finding outside this set*, so a group lands as a drop in these numbers and a
regression lands as a finding nobody recorded. Task 7.6 deletes the mechanism once the gates stand on their own.

## The universe, enumerated

| set | files | read | skipped | predicate sites |
|---|---|---|---|---|
| `jca` | 23 | 22 | 1 | 106 |
| `jca_android` | 23 | 23 | 0 | 110 |
| `jca_android_bug_predicate` | 23 | 22 | 1 | 147 |
| `generic` | 118 | 118 | 0 | 0 |
| `generic_new` | 27 | 27 | 0 | 0 |
| **total** | **214** | **212** | **2** | | 

Every skipped file carries its reason:

- `jca/SecretKeySpecSpec.mop` — unbalanced parenthesis: unmatched `)` at line 30
- `jca_android_bug_predicate/SecretKeySpecSpec.mop` — unbalanced parenthesis: unmatched `)` at line 30

## The structural suite

| gate | findings |
|---|---|
| G-ACC | 17 |
| G-ORDER | 4 |
| G-PRED2 | 36 |
| INV-INS-130 | 23 |
| INV-INS-133 | 27 |
| INV-INS-134 | 42 |
| **failing total** | **149** |

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

## G-ORDER

6 specifications equivalent to their api30 rule, 4 divergent, 204 skipped of 214 enumerated. Each divergence carries the shortest word the two languages disagree on:

- `jca_android/CipherSpec` — `f2` is accepted by the api30 ORDER and rejected by the specification
- `jca_android/SSLContextSpec` — `g1 Init se1 se1` is accepted by the specification and rejected by the api30 ORDER
- `jca_android/SecureRandomSpec` — `c1 c1` is accepted by the specification and rejected by the api30 ORDER
- `jca_android/TrustManagerFactorySpec` — `g1 i1 gtm` is accepted by the api30 ORDER and rejected by the specification
