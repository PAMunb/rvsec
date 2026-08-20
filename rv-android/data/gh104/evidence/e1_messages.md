# E1 — legible messages in `jca_android` (Group 7)

What this records: the run of tasks 7.1–7.8, the numbers each gate returned, and the three
instrument repairs the group needed. The per-specification before/after evidence is in
`evidence/harness/e1-<Spec>.md`, one file per specification (23).

## What changed in the set

All **50 live report sites** carry the `v=1` envelope of design D-3. The census was re-derived from
the files before anything was edited and is written up in `data/jca_android/README.md`: 25
three-argument sites and 25 four-argument, plus the commented `g4` of `MessageDigestSpec`, which
stays commented (Group 8 task 8.14). After the pass there are **zero** three-argument sites and
**zero** `but found` sites reading a monitor field; `ev=` comes from the generator's `__EVENTNAME`
macro at every one of them, and no specification carries a bookkeeping field or statement.

`jca_android/codes.csv` has 50 rows, bijective with the census.

Three `ErrorType` values were corrected as design D-13 requires, and `rvsec-core`'s `ErrorType`
gained `ForbiddenMethod` for the first two — `PBEKeySpecSpec` `f1`/`f2` (a CrySL `FORBIDDEN`
constructor, previously reported as a call-order defect) and `PBEParameterSpecSpec` `c3` (an
iteration-count bound, previously reported as an unsafe algorithm). `RequiredPredicate` was **not**
added: no site of the set would emit it.

Five lying messages were repaired before any envelope was written over them: the two `1000`s that
sat under guards reading `10000`; `MessageDigestSpec`'s and `SSLContextSpec`'s hand-written short
lists, which named three and two entries under guards admitting six and seven; `CipherSpec`'s
literal `...`, which told the reader the expected set was longer than printed and never said where
to read the rest; `SecretKeySpecSpec`'s two messages, which still accused an algorithm after task
2.4 removed the only algorithm test they had; and `SecureRandomSpec`'s `" or "` separator.

## What the instruments said

| instrument | result |
|---|---|
| `gh104_mop_lint.py` on `jca_android` | `three-argument-site` 25 → **0**; `hand-written-name` 0; remaining: `duplicate-event` 1, `undeclared-symbol` 1, `unbalanced` 1 — all three are Group 8 (tasks 8.1 and the `SecretKeySpecSpec` parenthesis) |
| `gh104_message_gate.py` on `jca_android` | `literal-mismatch` 2 → **0**; `wrong-error-type` 3 → **0**; `code-bijection` **0**; `self-contradicting envelope` **15**, which is the declared case below |
| `gh104_mop_lint.py` / `gh104_message_gate.py` on the frozen `jca` | unchanged at their pinned baselines (25/1/1/1 and 2/3) |
| `gh104_gates.py` on the regenerated monitor | **G-CONF 0** failures (55 notes), **G-PRED 0**, **G-ERE 0** with the one `GCMParameterSpecSpec` row allowlisted until 8.1. G-2 3, G-2a 1, G-2b' 8, G-2c 1, G-2d 2, G-6' 1 — every one a Group 8 target, none of them moved by E1 |
| `gh104_divergence_record.py --check` | green: 121 hunks, all recorded; 61 of them kind `message` |
| generation | 1 min 16 s; `MultiSpec_1RuntimeMonitor.java` 17,198 lines, compiles against `ErrorType.ForbiddenMethod`; **zero** unexpanded `__EVENTNAME` in any generated Java or `.aj` |
| `gh104_diff_harness.py` post-Group-2 vs E1 | **59 traces, 59 `unchanged`** — no accusation moved, in either direction |

E1 touched no automaton. Checked mechanically against the pre-E1 snapshot: every event name, kind,
pointcut, `args()` and `condition()` is identical in all 23 files, every `ere`/`fsm` is identical,
and the `__RESET` and `ExecutionContext` counts are unchanged per file.

## The declared case: guard on the field, value from the getter

Nine specifications guard on the monitor's own field and, after task 7.4, print the value the bound
object reports. They are recorded as `guard-on-field` rows of `data/jca_android/conformance_record.csv`
and replayed by `data/gh104/traces/<Spec>-guard-on-field.txt` (nine traces; task 7.4 added the
`KeyGeneratorSpec` and `KeyStoreSpec` ones). E1 declares the case and does not repair it: moving the
guard stops accusing objects with no observed `getInstance`, which is a change of what is reported
and is Group 8 task 8.16.

The message gate reports all 15 sites. The harness flags four of the nine traces —
`KeyGeneratorSpec` (`val='AES'` inside its own `exp`), `MessageDigestSpec` (`SHA-256`),
`SSLContextSpec` (`TLSv1.2`) and `TrustManagerFactorySpec` (`PKIX`). **The other five do not reach
their value site, and 8.16 needs to know why before it measures anything.** For `KeyStoreSpec`,
`KeyManagerFactorySpec`, `MacSpec` and `SignatureSpec` the first call on an object whose
`getInstance` was never dispatched is an undefined transition, so the monitor goes to `fail` and the
event body — which is where the guarded value site lives — never runs; the trace produces an ORDER
envelope instead. That is not something a trace can be written around: the case needs an object that
skipped `getInstance` *and* reaches the value event legally, and the two are contradictory in those
four automata. It occurs on the device path, where the object arrives from a `clone()` or a factory
the aspect did not weave — the 156 `MessageDigestSpec` rows ending in `but found .`.

`CipherSpec` is a fifth kind: its value site **did** fire, with
`val='AES/CBC/PKCS5Padding' exp='a transformation admitted by Api30CipherTransformationUtil (api30
Cipher.cryptsl)'`, which is self-contradicting in substance — that transformation is admitted — but
the harness cannot see it, because `exp` names the class holding the clauses instead of listing
them. The clauses live in Java by design D-b, so the flag has nothing to split on. The site is on
the message gate's list all the same, and 8.16 should read this envelope by calling the utility
rather than by parsing `exp`.

## Three instrument repairs, all in Group 6 files

The validation toolkit was written before any envelope existed, and three of its rules read the
message shape that preceded the grammar. Each was repaired rather than allowlisted, and each keeps
the frozen `jca` at its pinned baseline:

1. **`gh104_message_gate.py`, `literal-mismatch`.** `v=1` reads as a standalone integer, so every
   envelope of the set was reported as carrying a number its guard does not use — 50 findings that
   would have buried the one real off-by-a-factor-of-ten. The version marker is structure, not
   sentence, and is now dropped before the numeric scan.
2. **`gh104_message_gate.py`, `code-bijection`.** The check compared whole string literals against
   `codes.csv`, which was right when a code would have been a literal of its own and is wrong now
   that it is a field of the envelope. It reads `code=<TOKEN>` out of the message, and it checks
   both directions the docstring promises: a site with no code and a code emitted twice are now
   findings, not silence.
3. **`gh104_diff_harness.py`, `val ∈ exp`.** The check parsed the observed value back out of the
   `expecting … but found …` prose, which on an envelope captures the closing quote as part of the
   value, so the comparison could never match. It reads `val=` and `exp=` from the envelope where
   there is one and falls back to the prose for the pre-envelope side, so a before/after pair is
   judged by one rule.

A fourth, smaller one: `error_sites()` in `gh104_mop_lint.py` now marks a commented-out site instead
of returning it indistinguishable from a live one, and both the lint and the message gate skip it. A
report the set holds and does not emit is not a site with a missing code.
