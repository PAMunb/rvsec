# Group 7 — E1: legible messages in `jca_android`

Tracked checkboxes: `tasks.md` §7. Starts after Group 2's commits **and** Group 3's `__EVENTNAME` commit (until the macro expands, every envelope you write would carry an undefined identifier) **and** Group 6 tasks 6.4/6.5/6.7/6.8/6.9 (7.6 runs the lint, message gate, G-CONF, G-PRED; 7.7 runs the harness). `evidence/...` means `data/gh104/evidence/...`, `traces` means `data/gh104/traces`; generation under the wave's generation lock, `TMPDIR` off tmpfs, JDK 21. Edits `rvsec-mop/src/main/resources/jca_android/*.mop`, `jca_android/codes.csv`, `rvsec-core/.../eh/ErrorType.java` (+ its test), `data/jca_android/divergence_record.csv` and `evidence/harness/e1-*.md`.

Two subagents on disjoint halves of the **21** surviving specifications: **7.a** = `CipherInputStreamSpec, CipherOutputStreamSpec, CipherSpec, DHGenParameterSpecSpec, GCMParameterSpecSpec, HMACParameterSpecSpec, IvParameterSpec, KeyGeneratorSpec, KeyManagerFactorySpec, KeyPairGeneratorSpec, KeyPairSpec, KeyStoreSpec`; **7.b** = `MacSpec, MessageDigestSpec, PBEKeySpecSpec, PBEParameterSpecSpec, SecretKeySpecSpec, SecureRandomSpec, SignatureSpec, SSLContextSpec, TrustManagerFactorySpec` **plus `ErrorType.java`**, which 7.b owns alone. `RandomStringPassword` and `SecretKeySpec` are not in either half — Group 2 deleted them.

## Subagent brief

Read `design.md` D-2, D-3, D-4 and the `instrumentation` delta requirements `Violation Report Message Envelope`, `Event-Name Emission by the Monitor Generator` (INV-INS-119/120/121). Do not touch automata, pointcuts, `fsm`/`ere` or bindings — that is Group 8. Do not touch `jca/` or the archived `jca_android_bug_predicate/`. Do not re-open the allow-lists — Group 2 settled them from the api30 rules and gate G-CONF holds them; your job is to make the message *say* what the list already is. Every hunk gets a divergence-record entry (kind `message`, task `7.x`). Regenerate the monitor of your half in scratch at the end (`RVSEC_HOME`, `TMPDIR` off tmpfs) and run the harness post-Group-2-snapshot-vs-now per file (not the byte-identical seed: Group 2 already moved verdicts, and against the seed nothing would classify `unchanged`): the classification must be `unchanged` for accusation — only the envelope and the observed value differ. Java inside `.mop` bodies is inlined verbatim into the monitor: keep it minimal (a string concatenation and one `addError`).

## Task 7.1 — `ErrorType` gains `ForbiddenMethod`, and only that

`rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorType.java` has six values today (`:4-9`): `UnsafeAlgorithm`, `InvalidSequenceOfMethodCalls`, `UnsatisfiedConstraint`, `InvalidKeySize`, `InvalidKeyStoreType`, `UnsafeProtocol`. Add **`ForbiddenMethod`**.

`RequiredPredicate` does **not** enter: predicates left the set in Group 2, so no site could carry it, and an enum value nothing produces is dead code (P3). `ForbiddenMethod` does enter, because CrySL's `FORBIDDEN` is not a predicate — it is a per-call prohibition, and `generated/api30/PBEKeySpec.cryptsl` declares exactly two of them (`PBEKeySpec(char[])`, `PBEKeySpec(char[], byte[], int)`), which are what `PBEKeySpecSpec` `f1`/`f2` encode. Today they report `InvalidSequenceOfMethodCalls`, which is the wrong type and sends the developer looking for a call-order bug that is not there. (`generated/api30/SSLContext.cryptsl` also declares `FORBIDDEN: getDefault()`, which no `.mop` event encodes — record it as an omission in the conformance record; adding the event is not this group's work.)

KIND `FORB` joins the `codes.csv` vocabulary of design D-3: `ORDER`, `ALG`, `CONSTR`, `KEYSIZE`, `KSTYPE`, `PROTO`, `FORB`. `REQ` is not used by this set.

## Task 7.2 — recount the sites before editing anything

**The seed's site census does not survive Group 2, and no number in this file may be trusted until you re-derive it.** The frozen `jca` had 51 `new ErrorDescription(` = 25 three-argument (21 `@fail` + `IvParameterSpec:48,55` + `PBEKeySpecSpec:24,30`) + 26 four-argument (one of them commented, `MessageDigestSpec:57-58`).

What is known to be gone after Group 2:

| site | seed line | why it disappears |
|---|---|---|
| `IvParameterSpec` c3 | `:48` (3-arg) | condition was `!validate(RANDOMIZED, iv)` and nothing else |
| `IvParameterSpec` c4 | `:55` (3-arg) | idem |
| `PBEKeySpecSpec` err2 | `:57-58` (4-arg) | condition was `!validate(RANDOMIZED, password)` and nothing else |
| `PBEKeySpecSpec` err3 | `:65-66` (4-arg) | condition was `!validate(RANDOMIZED, salt)` and nothing else |
| `SecureRandomSpec` setSeed3 | `:100-101` (4-arg) | condition was `!validate(RANDOMIZED, seed)` and nothing else |

Deleting `RandomStringPassword.mop` and `SecretKeySpec.mop` costs zero sites (both had none). That leaves a **provisional 23 three-argument + 23 four-argument = 46**, and the 21 `@fail` are untouched.

One more site is settled since that provisional was written: `SecretKeySpecSpec.c3` (`:48-49`) had two halves, an allow-list test and a predicate test. The predicate half went with Group 2 task 2.3, and the allow-list half went with Group 2 task 2.4 — `generated/api30/SecretKeySpec.cryptsl` declares only `length(keyMaterial) >= off + len` and nothing about the algorithm, so the seed's algorithm list has no base and was removed. Both halves gone means the site is gone, `c4` keeps only its length test, and the arithmetic becomes **23 three-argument + 22 four-argument = 45**.

That is still **A RECALCULAR na execução**, and the reasons are mechanical rather than open questions: every line number in the tables below moved when the `ExecutionContext` blocks were deleted, and the allow-list transcription may have emptied a condition somewhere else without anyone predicting it here. **Count from the files, write the count into this section, and only then start editing.** If the count is neither 45 nor 46, say which site explains the difference before continuing.

## Idiom (per file)

```
@fail {
    ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "<Spec>", "" + __LOC,
        "v=1 code=<SPEC>-ORDER-00 ev=" + __EVENTNAME + " obj=<SimpleClass> val='' exp='' msg='<sentence>'"));
    __RESET;
}
value site: addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "<Spec>", "" + __LOC,
        "v=1 code=<SPEC>-ALG-01 ev=" + __EVENTNAME + " obj=<SimpleClass> val='" + q(alg) + "' exp='" + q(String.join(",", safeAlgorithms)) + "' msg='expecting one of " + String.join(",", safeAlgorithms) + " but found " + alg + "'"));
```

`__EVENTNAME` is expanded by the generator (Group 3, INV-INS-120): inside an event body it becomes the literal name of that event, inside `@fail` it becomes the name of the event that last transitioned the monitor (`none` if there was none). **Write no bookkeeping field and no bookkeeping statement** — the lint fails on them, and a hand-written name table would desynchronise from the generator's event indices under Group 8's edits.

`q(s)`: null → `""`, `'` → `\'`, cap 512 chars — a private helper in `declarations` (private methods in `declarations` are emitted verbatim; verified on `KeyPairGeneratorSpec`). No `static` declarations. `msg` must not start with `expecting` (`ErrorDescription.toString :143` prefixes it).

## Task 7.3 — the lying-message census

Apply these **before** writing envelopes, so the envelope is built over a true sentence. Line numbers are the seed's; locate by symbol.

| site | today | correct | proof |
|---|---|---|---|
| `PBEKeySpecSpec:50` | message says `>= 1000` | `>= 10000` | guard at `:48` tests `10000`; `generated/api30/PBEKeySpec.cryptsl` `CONSTRAINTS: iterationCount >= 10000` |
| `PBEParameterSpecSpec:50` | message says `at least 1000 iterations` | `10000` | guard at `:46`; `generated/api30/PBEParameterSpec.cryptsl` idem |
| `PBEKeySpecSpec:24` (`f1`) | `ErrorType.InvalidSequenceOfMethodCalls` | **`ErrorType.ForbiddenMethod`** | `PBEKeySpec.cryptsl` `FORBIDDEN: PBEKeySpec(char[]) => c1;` — decision D-13 |
| `PBEKeySpecSpec:30` (`f2`) | `ErrorType.InvalidSequenceOfMethodCalls` | **`ErrorType.ForbiddenMethod`** | `FORBIDDEN: PBEKeySpec(char[], byte[], int) => c1;` — decision D-13 |
| `PBEParameterSpecSpec:49` (`c3`) | `ErrorType.UnsafeAlgorithm` | **`ErrorType.UnsatisfiedConstraint`** | the clause is an iteration-count bound, not an algorithm — decision D-13 |
| `MessageDigestSpec:70,92` | message lists 3 entries | the transcribed allow-list | Group 2 rewrote `:16`; the message must join that list, not a literal |
| `CipherSpec:61,76` | message ends in a literal `...` | drop it; name the new Java utility of task 2.8 | the list is in Java (D-b) |
| `KeyGeneratorSpec:64`, `KeyStoreSpec:68` | missing space | — | reading the rendered line |
| `MacSpec:62` | missing verb | — | idem |
| `SecretKeySpecSpec:49` | "keyMaterial.length is not randomized" | — | **the whole site is gone after Group 2** (both halves of `c3`'s condition left; see 7.2); nothing to rewrite, only to confirm absent |
| `MacSpec:50`, `KeyManagerFactorySpec:55`, `KeyPairGeneratorSpec:72`, `SecretKeySpecSpec:49,56` | leading space | — | idem |
| `SecureRandomSpec:82` | joins the list with `" or "` | `","` — one separator across the set | consumers split on the rendered `exp` |

`KeyPairGeneratorSpec:71-72` is unreachable — `validate()` returns `true` exactly for the members of `safeAlgorithms`, so the guard at `:70` is false whenever it runs; note it here and leave the removal to Group 8 task 8.6 — but write the envelope anyway, so the site is legible the moment it becomes reachable.

## Task 7.4 — field → argument at the `but found` sites

Sixteen sites in the seed interpolate a **monitor field**, so the message names the previous call's value — or `""` when no `getInstance` was observed, which is the mechanism behind the 8,843 empty labels: `CipherSpec:61,76` (`currentTransformation`); `KeyGeneratorSpec:64` and `MacSpec:50,62` and `SignatureSpec:58,68,78,88` and `TrustManagerFactorySpec:57` and `KeyManagerFactorySpec:55` and `MessageDigestSpec:70,92` (`currentAlgorithmInstance`); `KeyPairGeneratorSpec:72` (`algorithm`); `KeyStoreSpec:68` (`currentKSType`); `SSLContextSpec:58` (`currentProtocol`). `SecureRandomSpec:82` already uses the argument, because it sits in `g4`, which binds `alg`. **None of the 16 reporting events binds that argument** — `update`, `digest`, `init`, `i1..i4`, `gk1` bind the digest, key, certificate or factory, never the algorithm/type/protocol string; only the `getInstance` events do, so `MessageDigestSpec:57-58`'s argument form (in `g4`) does not transfer. What every one of the 16 does bind is the **target object**, and the value is `public` on it (`javap`, android-30): interpolate `c.getAlgorithm()` (Cipher), `k.getAlgorithm()` (KeyGenerator, KeyPairGenerator), `k.getType()` (KeyStore), `m.getAlgorithm()` (Mac), `digest.getAlgorithm()` (MessageDigest), `s.getAlgorithm()` (Signature), `ctx.getProtocol()` (SSLContext), `mf.getAlgorithm()` / `k.getAlgorithm()` (the two factories) — never the field. Re-verify the list against the post-Group-2 files before editing. Un-comment `MessageDigestSpec:57-58` (it is in `g4` and keeps the argument).

The guards of `KeyGeneratorSpec:47` and `MessageDigestSpec:55` also read the field, and that is **not** a defect — `g1` fires first in the same wrapper and writes it (Group 8 item 8.8, withdrawn; design D-4 residues). Only the message side is repaired, here; do not touch those guards.

## Per-file inventory (frozen `jca` = the seed; line numbers of the seed, **stale after Group 2**)

| file | seed lines | events | 3-arg sites | 4-arg value sites | `@fail` `__RESET` | after Group 2 |
|---|---|---|---|---|---|---|
| CipherInputStreamSpec | 28 | 4 | `@fail :26` | – | yes | unchanged |
| CipherOutputStreamSpec | 28 | 5 | `@fail :26` | – | yes | unchanged |
| CipherSpec | 218 | 17 | `@fail :212` | i1 `:60-61` UA, i2 `:75-76` UA | yes | i2 keeps its transformation half only |
| DHGenParameterSpecSpec | 39 | 1 | `@fail :31` | – | yes | unchanged |
| GCMParameterSpecSpec | 59 | 2 | `@fail :51` | – | yes | guards widened; duplicate `c1` is Group 8 |
| HMACParameterSpecSpec | 37 | 1 | `@fail :29` | – | yes | unchanged |
| IvParameterSpec | 69 | 4 | c3 `:48`, c4 `:55`, `@fail :61` | – | yes | **c3 and c4 gone** → only `@fail` |
| KeyGeneratorSpec | 82 | 5 | `@fail :73` | gk1 `:63-64` UA | yes | allow-list rewritten |
| KeyManagerFactorySpec | 98 | 5 | `@fail :89` | init `:54-55` UA | yes | allow-list = `{PKIX}` |
| KeyPairGeneratorSpec | 118 | 9 | `@fail :111` | init1 `:71-72` UA, initError `:97-98` IKS | **no → add `__RESET`** | allow-list + `EC` |
| KeyPairSpec | 52 | 3 | `@fail :44` | – | yes | unchanged |
| KeyStoreSpec | 87 | 7 | `@fail :77` | gk1 `:67-68` IKST | yes | allow-list = the Android types |
| MacSpec | 94 | 8 | `@fail :86` | i1 `:49-50` UA, i2 `:61-62` UA | yes | both keep their allow-list half |
| MessageDigestSpec | 119 | 9 | `@fail :111` | update `:69-70` UA, d2 `:91-92` UA (+ commented g4 `:57-58`) | yes | list = the six api30 digests, MD5 and SHA-1 included (task 2.4) |
| PBEKeySpecSpec | 86 | 7 | f1 `:24` → FORB, f2 `:30` → FORB, `@fail :78-79` | err1 `:49-50` UC, err2 `:57-58`, err3 `:65-66` | yes | **err2 and err3 gone** |
| PBEParameterSpecSpec | 63 | 3 | `@fail :56` | c3 `:49-50` UA → **UC** | yes | c3 keeps its iteration-count half |
| SecretKeySpecSpec | 70 | 4 | `@fail :62` | c3 `:48-49` UC, c4 `:55-56` UC | yes | **c3 gone (both halves) — see 7.2**; c4 keeps its length test |
| SecureRandomSpec | 174 | 15 | `@fail :167` | g4 `:81-82` UA, setSeed3 `:100-101` UC | yes | **setSeed3 gone**; list = `{SHA1PRNG}` |
| SignatureSpec | 138 | 12 | `@fail :130` | i1 `:57-58`, i2 `:67-68`, i3 `:77-78`, i4 `:87-88` UA | yes | list = the 20 api30 entries + the four ECDSA of task 2.7 |
| SSLContextSpec | 93 | 5 | `@fail :84` | init `:57-58` UP | yes | list = the 7 api30 protocols |
| TrustManagerFactorySpec | 97 | 5 | `@fail :85` | init `:56-57` UA | yes | list = `{PKIX}`; `X509` resolves through the alias class (task 2.5), not through the list |

## Commands

```bash
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec-mop/src/main/resources/jca_android       # 0 three-arg, 0 bookkeeping
python3 scripts/gh104_message_gate.py ../rvsec/rvsec-mop/src/main/resources/jca_android   # literals match; codes.csv bijective; ErrorType matches the site kind
python3 scripts/gh104_gates.py <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_android/gate_allowlist.csv --crysl ../../MetaCrySL/generated/api30
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_diff_harness.py --a <post-Group-2 snapshot: git show <group-2-final-commit>:… into scratch — NOT the seed; the seed would not classify unchanged, Group 2 already moved verdicts> --b ../rvsec/rvsec-mop/src/main/resources/jca_android --traces data/gh104/traces --out data/gh104/evidence/harness/e1
cd .. && mvn -q test -pl rvsec/rvsec-core           # reactor root; ErrorType test
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q
```

## Acceptance

- The recount of task 7.2 is written into this file, with the number derived from the files and the reason for any difference from the expected 45.
- `ErrorType` carries `ForbiddenMethod` and not `RequiredPredicate`; the three wrong `ErrorType` values of D-13 are corrected.
- Zero three-argument sites; zero field-interpolating `but found` sites; every envelope's `ev=` comes from `__EVENTNAME`; no bookkeeping field or statement exists; `codes.csv` bijective with the recounted sites; every hunk recorded.
- Harness post-Group-2-vs-E1: every trace `unchanged` in accusation; envelope now carries `ev=`.
- Monitor of `jca_android` compiles (`MultiSpec_1RuntimeMonitor.java`) and carries no unexpanded `__EVENTNAME` — record generation time.
- Two commits (one per half): `feat(jca_android): mensagens legíveis com envelope v1 (arquivos A–K|M–T) (refs #104)`.
