# Group 7 — E1: legible messages in `jca_android`

> **CORRECTION, 2026-08-20 — read this before anything else in this file.**
> An earlier revision of this change removed the predicate machinery from the successor set. **That decision is
> withdrawn (design D-11)**, and the set carries the seed's predicates byte-for-byte. Every passage below that
> counts on sites disappearing with the predicates is superseded by this banner. Concretely: the set has **23**
> `.mop`, `RandomStringPassword.mop` and `SecretKeySpec.mop` included; the site census is **50 live sites — 25
> three-argument and 25 four-argument — plus 1 commented occurrence**, which is the frozen `jca`'s census
> unchanged, because the successor keeps every event the seed declares and the allow-list transcription removed
> no report site. Task 7.2's recount has been run against the files and is reproduced below; the provisional
> arithmetic of 44/45 it replaced is gone.

Tracked checkboxes: `tasks.md` §7. Starts after Group 2's commits **including task 2.14** (the harness before/after + promotion pass, which edits `jca_android/*.mop` last — two writers must not overlap) **and** the between-waves 3.9/3.5/3.8 step of Group 3 (the installed generator expands `__EVENTNAME`; until it does, every envelope you write would carry an undefined identifier) **and** Group 6 tasks 6.1/6.2/6.3 (`gh104_gates.py` with G-2/G-6′/G-ERE — 7.2 writes the G-ERE allowlist row that 7.6's gate run consumes) and 6.4/6.5/6.7/6.8/6.9 (7.6 runs the lint, message gate, G-CONF, G-PRED; 7.7 runs the harness). One more ordering inside the group: 7.1 edits `ErrorType.java` in `rvsec-core`, and 7.7 compiles `PBEKeySpecSpec`'s monitor against `ErrorType.ForbiddenMethod` — so after 7.1 and before 7.7 the orchestrator runs `mvn -q install -pl rvsec/rvsec-core -DskipTests` at the reactor root (a pre-wave install of `rvsec-core` alone, not the full reactor install); without it the monitor of 7.b's half does not compile. `evidence/...` means `data/gh104/evidence/...`, `traces` means `data/gh104/traces`. Environment: prefix EVERY Java/Maven/generation command line with `export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH` (shell state does not persist between tool calls) and every generation line with `export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR` (`/tmp` and the session scratchpad are tmpfs); task 7.7 is this group's generating task (`[GEN]`) — the orchestrator dispatches at most one generating task at a time, and `mvn install` at the reactor root runs only between waves, by the orchestrator. Git: one repository (rv-android is a subdirectory of `…/rvsec`); every `git status`/`git diff` carries a pathspec (`git status --short -- <paths>`; `git diff --cached --stat -- <paths>`); commits are made by one writer at a time — the orchestrator, after each half's summary, `git add <explicit pathspecs>` + commit; the halves do not commit, and never `git add -A`/`git commit -a`. Edits `rvsec-mop/src/main/resources/jca_android/*.mop`, `jca_android/codes.csv`, `rvsec-core/.../eh/ErrorType.java` (+ its test), `data/jca_android/divergence_record.csv`, `data/jca_android/gate_allowlist.csv`, `data/jca_android/README.md` and `evidence/harness/e1-<Spec>.md` (one file per specification).

Two subagents on disjoint halves of the **21** specifications that carry a report site: **7.a** = `CipherInputStreamSpec, CipherOutputStreamSpec, CipherSpec, DHGenParameterSpecSpec, GCMParameterSpecSpec, HMACParameterSpecSpec, IvParameterSpec, KeyGeneratorSpec, KeyManagerFactorySpec, KeyPairGeneratorSpec, KeyPairSpec, KeyStoreSpec`; **7.b** = `MacSpec, MessageDigestSpec, PBEKeySpecSpec, PBEParameterSpecSpec, SecretKeySpecSpec, SecureRandomSpec, SignatureSpec, SSLContextSpec, TrustManagerFactorySpec` **plus `ErrorType.java`**, which 7.b owns alone. `RandomStringPassword` and `SecretKeySpec` are in the set (D-11) but in neither half: `grep -c "new ErrorDescription("` returns 0 for both, so there is no message in either to make legible. **`codes.csv` and `data/jca_android/divergence_record.csv` are owned by 7.b**: both halves produce rows for them, so 7.a writes its rows into `jca_android/codes.7a.part` and `data/jca_android/divergence.7a.part` (or hands them over in its summary) and 7.b merges them into the two files; 7.a never appends to the files themselves.

## Subagent brief

Read `design.md` D-2, D-3, D-4 and the `instrumentation` delta requirements `Violation Report Message Envelope`, `Event-Name Emission by the Monitor Generator` (INV-INS-119/120/121). Do not touch automata, pointcuts, `fsm`/`ere`, bindings, guards or handler control flow — that is Group 8. The statement holds literally: the three items that would have changed what is accused from inside this group (reviving the commented `g4` report of `MessageDigestSpec`, adding `__RESET` to `KeyPairGeneratorSpec`'s `@fail`, guarding on the getter instead of the field) are Group 8 tasks 8.14, 8.15 and 8.16, measured there by the harness; here they are left as they are and, for the third, declared. Do not touch `jca/` or the archived `jca_android_bug_predicate/`. Do not re-open the allow-lists — Group 2 settled them from the api30 rules and gate G-CONF holds them; your job is to make the message *say* what the list already is. Every hunk gets a divergence-record entry (kind `message`, task `7.x`). Regenerate the monitor of your half in scratch at the end (`RVSEC_HOME`, `TMPDIR` off tmpfs) and run the harness post-Group-2-snapshot-vs-now per file (not the byte-identical seed: Group 2 already moved verdicts, and against the seed nothing would classify `unchanged`): the classification must be `unchanged` for accusation — only the envelope and the observed value differ. Java inside `.mop` bodies is inlined verbatim into the monitor: keep it minimal (a string concatenation and one `addError`).

## Task 7.1 — `ErrorType` gains `ForbiddenMethod`, and only that

`rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorType.java` has six values today (`:4-9`): `UnsafeAlgorithm`, `InvalidSequenceOfMethodCalls`, `UnsatisfiedConstraint`, `InvalidKeySize`, `InvalidKeyStoreType`, `UnsafeProtocol`. Add **`ForbiddenMethod`**.

`RequiredPredicate` does **not** enter, and the reason is no longer that the predicates left — they stayed (D-11). It is that **no site would produce it**: every predicate-guarded accuser of the set already reports `UnsatisfiedConstraint` (`IvParameterSpec` c3/c4, `PBEKeySpecSpec` err2/err3, `SecureRandomSpec` setSeed3, `SecretKeySpecSpec` c3), which is the right type for a failed CrySL `REQUIRES` — the constraint the clause states is exactly what went unsatisfied. Adding a second name for it would split one condition across two vocabularies, and an enum value nothing produces is dead code (P3). `ForbiddenMethod` does enter, because CrySL's `FORBIDDEN` is not a predicate — it is a per-call prohibition, and `generated/api30/PBEKeySpec.cryptsl` declares exactly two of them (`PBEKeySpec(char[])`, `PBEKeySpec(char[], byte[], int)`), which are what `PBEKeySpecSpec` `f1`/`f2` encode. Today they report `InvalidSequenceOfMethodCalls`, which is the wrong type and sends the developer looking for a call-order bug that is not there. (`generated/api30/SSLContext.cryptsl` also declares `FORBIDDEN: getDefault()`, which no `.mop` event encodes — record it as an omission in the conformance record; adding the event is not this group's work.)

KIND `FORB` joins the `codes.csv` vocabulary of design D-3: `ORDER`, `ALG`, `CONSTR`, `KEYSIZE`, `KSTYPE`, `PROTO`, `FORB`. `REQ` is not used by this set.

## Task 7.2 — recount the sites before editing anything

**The recount has been run. It is reproduced here so the group starts from a measured number, and it must still
be re-derived from the files before editing** — the point of the task is that no number in a plan is trusted
over the tree it describes.

Measured on `rvsec-mop/src/main/resources/jca_android/` after Group 2 (tasks 2.2–2.8 and 2.14):

| | three-argument | four-argument | commented | live total |
|---|---|---|---|---|
| frozen `jca` (the seed) | 25 | 25 | 1 | **50** |
| `jca_android` (the successor) | 25 | 25 | 1 | **50** |

**The census is the seed's, unchanged.** That is the direct consequence of D-11: the successor keeps every event
the seed declares, predicates and all, and the allow-list transcription of task 2.4 changed which *values* a
condition admits without removing a single report site. The one site Group 2 could have cost —
`SecretKeySpecSpec.c3`, whose condition had an allow-list half and a predicate half — kept its predicate half and
so kept its accusation; only its algorithm test left, because `generated/api30/SecretKeySpec.cryptsl` declares
`length(keyMaterial) >= off + len` and nothing about the algorithm.

An earlier revision of this file predicted 44 or 45 live sites, arrived at by subtracting the five purely
predicate-guarded accusers (`IvParameterSpec` c3/c4, `PBEKeySpecSpec` err2/err3, `SecureRandomSpec` setSeed3) and
`SecretKeySpecSpec.c3`. All six are alive. The commented occurrence is `MessageDigestSpec:57-58`, the `g4` report,
and it **stays commented in this group** — reviving it is Group 8 task 8.14.

The 25 three-argument sites are the 21 `@fail`/`@match1` handlers plus `IvParameterSpec` c3/c4 and
`PBEKeySpecSpec`'s two order sites; the 25 four-argument sites are the value accusers. Every line number in the
tables below moved when Group 2 rewrote the conditions, so **count from the files, write the count into
`data/jca_android/README.md`** (a "site census after Group 2" paragraph — not into this file) and say there which
site explains any difference from the 50 above before continuing.

In the same pass add the G-ERE `GCMParameterSpecSpec` row to `data/jca_android/gate_allowlist.csv`
(`set=jca_android, gate=G-ERE, spec=GCMParameterSpecSpec, event_or_state=c2, reason='until 8.1', task=7.6`):
`ere : c1 | c2` (`:48`) names a `c2` the file never declares (`:23` and `:34` both declare `c1`) — Group 8 task
8.1 repairs it, and until then 7.6's gate run must see the hit as expected.

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

`<SPEC>` in `code=` is the specification's name in upper case without the `Spec` suffix — `MESSAGEDIGEST-ALG-01`, `TRUSTMANAGERFACTORY-ALG-01`, `PBEKEYSPEC-FORB-01`, `KEYPAIRGENERATOR-ORDER-00` — one rule for both halves, so the two subagents assign codes independently without colliding (design D-3 carries the table, one row per specification of the successor set). `codes.csv` keeps the header of D-3 (`spec,code,error_type,site_kind,event,file_line`); no column is added. The `__RESET;` of the `@fail` idiom is the one each file already has: the 20 handlers that carry it keep it, and `KeyPairGeneratorSpec`'s handler, which has none, gains none here — adding it changes what the sticky `fail` state reports and is Group 8 task 8.15.

`__EVENTNAME` is expanded by the generator (Group 3, INV-INS-120): inside an event body it becomes the literal name of that event, inside `@fail` it becomes the name of the event that last transitioned the monitor (`none` if there was none). **Write no bookkeeping field and no bookkeeping statement** — the lint fails on them, and a hand-written name table would desynchronise from the generator's event indices under Group 8's edits.

`q(s)`: null → `""`, `'` → `\'`, cap 512 chars — a private helper in `declarations` (private methods in `declarations` are emitted verbatim; verified on `KeyPairGeneratorSpec`). No `static` declarations.

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

Sixteen sites in the seed interpolate a **monitor field**, so the message names the previous call's value — or `""` when no `getInstance` was observed, which is the mechanism behind the 8,843 empty labels: `CipherSpec:61,76` (`currentTransformation`); `KeyGeneratorSpec:64` and `MacSpec:50,62` and `SignatureSpec:58,68,78,88` and `TrustManagerFactorySpec:57` and `KeyManagerFactorySpec:55` and `MessageDigestSpec:70,92` (`currentAlgorithmInstance`); `KeyPairGeneratorSpec:72` (`algorithm`); `KeyStoreSpec:68` (`currentKSType`); `SSLContextSpec:58` (`currentProtocol`). `SecureRandomSpec:82` already uses the argument, because it sits in `g4`, which binds `alg`. **None of the 16 reporting events binds that argument** — `update`, `digest`, `init`, `i1..i4`, `gk1` bind the digest, key, certificate or factory, never the algorithm/type/protocol string; only the `getInstance` events do, so `MessageDigestSpec:57-58`'s argument form (in `g4`) does not transfer. What every one of the 16 does bind is the **target object**, and the value is `public` on it (`javap`, android-30): interpolate `c.getAlgorithm()` (Cipher), `k.getAlgorithm()` (KeyGenerator, KeyPairGenerator), `k.getType()` (KeyStore), `m.getAlgorithm()` (Mac), `digest.getAlgorithm()` (MessageDigest), `s.getAlgorithm()` (Signature), `ctx.getProtocol()` (SSLContext), `mf.getAlgorithm()` / `k.getAlgorithm()` (the two factories) — never the field. Re-verify the list against the post-Group-2 files before editing. `MessageDigestSpec:57-58` stays commented: it is a report that does not exist today, and reviving it would add an `UnsafeAlgorithm` on every `getInstance(String)` outside the list — Group 8 task 8.14 measures that.

The guards of `KeyGeneratorSpec:47` and `MessageDigestSpec:55` also read the field, and that is **not** a defect — `g1` fires first in the same wrapper and writes it (Group 8 item 8.8, withdrawn). Only the message side is repaired, here; do not touch those guards.

## Declared case (tasks 7.4 and 7.7) — guard on the field, value from the getter

After 7.4 the 16 sites above read the observed value from the target object, but their **guards** still read the monitor field. The nine specifications where this happens, with the seed's guard lines: `MessageDigestSpec:68` (`update`; also `d2 :90`), `CipherSpec:59` (`i1`; also `i2 :74`), `SignatureSpec:56` (`i1`; also `i2 :66`, `i3 :76`, `i4 :86`), `SSLContextSpec:56` (`init`), `TrustManagerFactorySpec:55` (`init`), `KeyManagerFactorySpec:53` (`init`), `MacSpec:48` (`i1`; also `i2 :60`), `KeyStoreSpec:66` (`gk1`), `KeyGeneratorSpec:62` (`gk1`) — 15 of the 16 sites above (all but `KeyPairGeneratorSpec:72`, whose guard is the unreachable one of 8.6), nine files. For an object whose `getInstance` was never observed (the 156 `MessageDigestSpec` rows with `.` in `but found`: Guava's `prototype.clone()`, kmp-tor) the field is still `""`, the guard `!contains("")` is true, and after 7.4 the envelope reads `val='SHA-256' exp='…SHA-256…'` — a self-contradicting envelope, where the value named is a member of the list it is accused of not belonging to. The message gate (6.8) cannot see it: it checks literals, and both literals are right.

What this group does: **declare** the case, not repair it. (i) One row in `data/jca_android/conformance_record.csv` per specification of the nine (kind `guard-on-field`, the guard line, the getter the message now reads, and the sentence above). (ii) One harness trace per specification under `data/gh104/traces` whose object has **no** observed `getInstance` (`update`/`init`/`gk1` alone on a fresh object), so that the envelope `val ∈ exp` is on the record and the harness report of 7.7 flags it — the message gate (6.8) and the harness report (6.9) both mark any envelope whose `val` is a member of its own `exp` as `self-contradicting envelope`; those flags are expected here and are written into `evidence/harness/e1-<Spec>.md`, not allowlisted away.

What this group does **not** do: move the guard to the bound argument or the getter. That changes what is accused (the no-`getInstance` traces stop accusing) and is Group 8 task 8.16, measured — `removed` only for traces whose object has no observed `getInstance`, any other class reverts the site.

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
| KeyPairGeneratorSpec | 118 | 9 | `@fail :111` | init1 `:71-72` UA, initError `:97-98` IKS | **no — stays without it here; Group 8 task 8.15** | allow-list + `EC` |
| KeyPairSpec | 52 | 3 | `@fail :44` | – | yes | unchanged |
| KeyStoreSpec | 87 | 7 | `@fail :77` | gk1 `:67-68` IKST | yes | allow-list = the Android types |
| MacSpec | 94 | 8 | `@fail :86` | i1 `:49-50` UA, i2 `:61-62` UA | yes | both keep their allow-list half |
| MessageDigestSpec | 119 | 9 | `@fail :111` | update `:69-70` UA, d2 `:91-92` UA (+ commented g4 `:57-58`, stays commented — Group 8 task 8.14) | yes | list = the six api30 digests, MD5 and SHA-1 included (task 2.4) |
| PBEKeySpecSpec | 86 | 7 | f1 `:24` → FORB, f2 `:30` → FORB, `@fail :78-79` | err1 `:49-50` UC, err2 `:57-58`, err3 `:65-66` | yes | **err2 and err3 gone** |
| PBEParameterSpecSpec | 63 | 3 | `@fail :56` | c3 `:49-50` UA → **UC** | yes | c3 keeps its iteration-count half |
| SecretKeySpecSpec | 70 | 4 | `@fail :62` | c3 `:48-49` UC, c4 `:55-56` UC | yes | **c3 gone (both halves) — see 7.2**; c4 keeps its length test |
| SecureRandomSpec | 174 | 15 | `@fail :167` | g4 `:81-82` UA, setSeed3 `:100-101` UC | yes | **setSeed3 gone**; list = `{SHA1PRNG}` |
| SignatureSpec | 138 | 12 | `@fail :130` | i1 `:57-58`, i2 `:67-68`, i3 `:77-78`, i4 `:87-88` UA | yes | list = the 20 api30 entries + the four ECDSA of task 2.7 |
| SSLContextSpec | 93 | 5 | `@fail :84` | init `:57-58` UP | yes | list = the 7 api30 protocols |
| TrustManagerFactorySpec | 97 | 5 | `@fail :85` | init `:56-57` UA | yes | list = `{PKIX}`; `X509` resolves through `ConscryptAliasTable` (task 2.5), not through the list |

## Commands

```bash
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec-mop/src/main/resources/jca_android       # 0 three-arg, 0 bookkeeping
python3 scripts/gh104_message_gate.py ../rvsec/rvsec-mop/src/main/resources/jca_android   # literals match; codes.csv bijective; ErrorType matches the site kind
python3 scripts/gh104_gates.py --monitor <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_android/gate_allowlist.csv --crysl ../../MetaCrySL/generated/api30 --alias data/jca_android/alias_table.csv   # G-2, G-6', G-ERE (G-ERE's GCMParameterSpecSpec hit allowlisted by 7.2)
python3 scripts/gh104_divergence_record.py --check
# 7.7 [GEN] — one shell line: JDK + TMPDIR (+ RVSEC_HOME) before the regeneration into scratch, then the harness
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH; export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR; <regenerate the monitor of your half into <scratch>>
python3 scripts/gh104_diff_harness.py --a <post-Group-2 snapshot: git show <group-2-final-commit>:… into scratch — NOT the seed; the seed would not classify unchanged, Group 2 already moved verdicts> --b ../rvsec/rvsec-mop/src/main/resources/jca_android --traces data/gh104/traces --out data/gh104/evidence/harness/e1-<Spec>.md   # one file per specification
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH; cd .. && mvn -q test -pl rvsec/rvsec-core   # reactor root; ErrorType test
# orchestrator, after 7.1 and before 7.7: the pre-wave install of rvsec-core alone, so the regenerated monitor compiles against ErrorType.ForbiddenMethod
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH; cd .. && mvn -q install -pl rvsec/rvsec-core -DskipTests
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q
# 7.8
/rv-test-run tests/parity
```

## Acceptance

- The recount of task 7.2 is written into `data/jca_android/README.md`, live sites and the commented occurrence counted separately, with the number derived from the files and the reason for any difference from the measured 50 live; `data/jca_android/gate_allowlist.csv` carries the G-ERE `GCMParameterSpecSpec` row with reason `until 8.1`.
- `ErrorType` carries `ForbiddenMethod` and not `RequiredPredicate`; the three wrong `ErrorType` values of D-13 are corrected.
- Zero three-argument sites; zero field-interpolating `but found` sites; every envelope's `ev=` comes from `__EVENTNAME`; no bookkeeping field or statement exists; `codes.csv` bijective with the recounted sites; every hunk recorded.
- Harness post-Group-2-vs-E1: every trace `unchanged` in accusation; envelope now carries `ev=`; `evidence/harness/e1-<Spec>.md` per specification; the no-`getInstance` traces of the declared case flagged `self-contradicting envelope` and the nine `guard-on-field` rows present in `data/jca_android/conformance_record.csv`.
- `MessageDigestSpec:57-58` still commented, `KeyPairGeneratorSpec`'s `@fail` still without `__RESET`, no guard moved — E1 did not touch automata or handler control flow.
- Monitor of `jca_android` compiles (`MultiSpec_1RuntimeMonitor.java`) and carries no unexpanded `__EVENTNAME` — record generation time.
- Two commits (one per half, made by the orchestrator with explicit pathspecs after each half's summary; 7.b's includes the merged `codes.csv` and `divergence_record.csv`): `feat(jca_android): mensagens legíveis com envelope v1 (arquivos A–K|M–T) (refs #104)`.
