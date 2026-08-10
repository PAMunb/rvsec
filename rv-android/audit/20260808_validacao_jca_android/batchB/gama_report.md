# GAMA — Batch B report: diagnostics, experimental history, static synergy

Agent Gama · 2026-08-09 · adversarial posture. Round "batch B" of the `jca_android`
audit. Scope: CipherInputStreamSpec (CIS), CipherOutputStreamSpec (COS),
KeyPairSpec (KPR), SecretKeySpec.mop / declared spec `SecretKeySpec` targeting the
INTERFACE `javax.crypto.SecretKey` (SKY), PBEKeySpecSpec (PBK).

Governing rules applied without re-litigation: D-piloto-1/3/4, D-batchA-1
(`fase0/desvios.md`); batch B generation manifest round rules
(`batchB/generation_manifest.md`), including the standard indexing-tree check
(FEN-HMC-MONITOR-GLOBAL lineage) and REF-B-01/REF-B-09. Established SET findings
cited, never re-derived: GAMA-SET-01/03 (static path defaults to literal `jca`
mop_dir, `rv_static_analysis/config.py:199-206`; android_jar probe list
`["33","29","28","27","26"]` without "30", `config.py:186-194` — both re-verified
current at those lines), GAMA-SET-02/06 (identity/dedupe inconsistency; dedupe key
excludes `expecting`, `ErrorDescription.java:132-139`), 3-arg `ErrorDescription` ⇒
`expecting="unknown"` (`ErrorDescription.java:34-36`), GAMA-CIP-07 (logcat
ErrorCollector escape commented out, `rvsec-logger-logcat/.../ErrorCollector.java:39-40`),
GAMA-SET-09 (static ctor blindness, "new" vs `<init>`, judge-verified in batch A).

Method note (protocol §2): the Sequential Thinking MCP tool was listed as deferred
in this session and was not loaded; the same decomposition was applied explicitly —
each per-spec analysis below follows question → hypothesis → discriminating test →
evidence → result → uncertainty (scientific log in §7). No chain-of-thought is
published.

## 0. Inputs, provenance, freeze checks (G0)

- Specs read from `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`.
  `sha256sum` of all five equals `batchB/generation_manifest.md` and
  `fase0/manifest_hashes.md`: CIS `d71a86d8…`, COS `c1054929…`, KPR `8bc49632…`,
  SKY `03768f3b…`, PBK `8fdcabe6…` — freeze PASS.
- CrySL oracle: `MetaCrySL/generated/api30/`, sha256 verified equal to the manifest
  (CIS `f291a289…`, COS `9a57e52b…`, KPR `e204371f…`, SKY `ed4677b1…`,
  PBK `05f05202…`). Raw availability profile; bias recorded, never corrected.
- Effective artifacts: the round's common generated set under
  `<scratch>/batchB/gen_<Spec>/out/` (hashes in `generation_manifest.md`). All
  language/automaton statements are made over these artifacts (D-piloto-3).
- Historical dataset `ase-journal/dataset/results/errors.csv`: sha256
  `78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69` verified
  **inside** `gama_errors_batchB.py` before any read (abort-on-mismatch) — PASS.
  PRE-GH100/GH101: hypothesis generator only.
- android.jar API 30 (frozen): sha256 `96ccfdc8…` (= `fase0/toolchain_ambiente.md`).
  Member facts taken from **extracted class bytes**, never `javap -classpath`
  (batch A trap).
- JVM harness classpath: the frozen `rv-android/lib_tmp/rv-monitor-rt.jar`
  (sha256 `0fa65fbc…` = toolchain manifest), `rvsec-core-0.9.3-SNAPSHOT.jar` and
  `rvsec-logger-csv-0.9.3-SNAPSHOT.jar` from the rvsec tree targets (production
  ExecutionContext/ErrorDescription/ErrorCollector).
- No emulator, no device, no weaving (G10 pendencies named per claim). Specs,
  rules and production code untouched. JavaMOP/RV-Monitor never executed by me;
  the only extra executions were `javac`+`java` over the round's generated
  monitors in scratch, and the production `mop-extractor.jar` over **scratch
  copies** of the specs.

Evidence files (REF-B-01), all in `audit/.../batchB/`, sha256:

```
cf075d560a6a7818c8fe9825e16f698e1a25aedc93467094154b3d3d4019c623  gama_errors_batchB.py
0791990cfdbcea0c9350ce60544cfee8f0148ac4ccc9e8c90c2d5dd50e0d3e67  gama_errors_batchB_output.txt
068cb08acae172337502524846c4ceb086eec0a68e34e9ff49529bb83501e33f  gama_GamaBatchBDrive.java
4e6312184fe091f85e47973990795a6f30e5a760175dcd49f305557bc24fee9e  gama_harness_output.txt
ad062e8b08b9c32fd3e71de06f559c36e77cab92dca517001d6af800985628e4  gama_extractor_ja.csv
7c8342adf1eaf13efcdcf26911b261a93d64c6725f2a64486d524025cbeaa284  gama_extractor_j.csv
838bd77204416df4553e8db8f5188b8f5158b193c9a29e4b5ef3956bedf64aad  gama_claims.csv
```

## 1. Structural facts established once (cited per spec)

**1a. CIS and COS are parameterless specs ⇒ one global monitor per process
(PROVADO + EXECUTADO).** `CipherInputStreamSpec()` (mop:11) declares no monitored
object. The generated runtime has a single static monitor and no indexing tree
(`CipherInputStreamSpecRuntimeMonitor.java:275` — `CipherInputStreamSpec__Map =
new CipherInputStreamSpecMonitor()`); every stream in the process shares one
automaton. Effective tables (CIS): `c1={3,4,4,4,4}`, `r1/r2={4,1,4,1,4}`,
`cl1={4,2,4,4,4}` (state 0 start, 3 constructed, 1 reading, 2 closed-accept,
4 fail). COS is structurally identical (`c1={2,4,4,4,4}`, `w1/w2/fl={4,1,1,4,4}`,
`cl={4,3,4,4,4}`). Consequence, executed in the harness (scenario `cis`): with the
cipher properly marked GENERATED_CIPHER, the process's **second** conformant
stream lifecycle (construct, read, close) produced **three false
`InvalidSequenceOfMethodCalls`** (one per event, at three distinct `__LOC`s),
because the global automaton had finished the first lifecycle at the accept state
and `__RESET` after each fail re-desynchronizes the next event. Lifecycles then
alternate accused/clean. Interleaved streams fail likewise (c1 from states 1-4 is
fail). This is the batch-A FEN-HMC-MONITOR-GLOBAL check failing outright — here
not a mis-bound parameter but no parameter at all.

**1b. KPR's constructor event does not bind the spec parameter (PROVADO +
EXECUTADO).** `KeyPairSpec(KeyPair keyPair)` is parametric, but `c1` binds only
`(publicKey, privateKey, kp)` — `kp` is a body argument, not the spec parameter.
The generated `KeyPairSpec_c1Event` dispatches to the **empty parameter slice**
(`KeyPairSpec__Map`, `KeyPairSpecRuntimeMonitor.java:325-355`) and broadcasts to
**all** live monitors (`KeyPairSpecMonitor_Set.event_c1:31-53`). gh101 fixed this
exact defect for PBK's `f1`/`f2` by adding `returning(PBEKeySpec s)`
(divergence_record row `d57afb190618`) and left KPR's `c1` with it.

**1c. Reachable `@fail` handlers exist in batch B (unlike batch A).** CIS, COS,
KPR and PBK all have live `@fail` paths using the 3-arg `ErrorDescription` ⇒ every
sequence violation (true or false) enters the dataset as `message=unknown`. SKY
has **no** reporting path at all (no `@fail`, empty `@match`; the artifact does not
even generate a `Category_fail` flag — `SecretKeySpecRuntimeMonitor.java:88` has
only `Category_match`).

**1d. Batch-A GAMA-SET-08 (stale-flags handler re-execution) — checked, not
instantiated in batch B.** PBK's merged 4-call advice re-checks flags after each
suppressed sibling call, but on a valid `c1` the automaton sits at state 1 where
neither category flag is set, so no handler re-runs. No batch-B claim.

## 2. Per-spec diagnostic audit (G9), history, synergy

### 2.1 CipherInputStreamSpec (CIS)

Rule: EVENTS c1(is), c2(is,ciph), `Constructs := c1|c2`, r1/r2/r3 (`Reads`), c
(close); ORDER `Constructs, Reads+, c`; CONSTRAINTS `len > off`; ENSURES
`cipheredInputStream[is, ciph]`.

**G9 handler audit.**

| Path | category/clause | spec+set | expected/observed | state | __LOC | identity | dedupe |
|---|---|---|---|---|---|---|---|
| c1 body (mop:22-25) | `UnsatisfiedConstraint`, REQUIRES generatedCipher — specific, literal message | spec name only (no set field — pilot A5 applies) | message names the requirement | none | present | none (global monitor — no object identity at all) | GAMA-SET-06 applies |
| `@fail` (mop:38-41) | `InvalidSequenceOfMethodCalls`, **reachable and live** | idem | **`expecting=unknown`** (3-arg) | none | present | none | collapses all same-site fails |

Executed (harness `cis(a)`): unmarked cipher ⇒ exactly one `UnsatisfiedConstraint`,
standing alone (c1 transitions 0→3 normally; the D-S14-style body read works) —
**GAMA-CIS-05 PASS**. Executed (`cis(b)`): the global-monitor cascade of §1a —
**GAMA-CIS-01 FAIL crítica**; its three false records are all `unknown` —
**GAMA-CIS-02 FAIL major**. Post-`__RESET` cascade is not hypothetical: it is the
mechanism that turns one misalignment into one false record per subsequent event.

**Alphabet gaps.** The rule's 1-arg `c1` constructor is `protected` in the frozen
android-30 (measured on extracted bytes); the `.mop` has no event for it, and a
subclass-`super()` construction is invisible to `call()` pointcuts while the
subsequent reads DO match — the stream then desynchronizes the global automaton
from state 0 (GAMA-CIS-06 INCONCLUSIVE, realizability unmeasured). CONSTRAINTS
`len > off` has no counterpart anywhere in the spec (r2 binds `arr,offset,len`
into an empty body) — GAMA-CIS-04 FAIL, unregistered (searched
`data/gh101/divergence_record.csv`, `conformance_record.csv`,
`frozen_set_debt.md`, `README.md` §4.11 table — it lists Cipher/KMF/KeyStore/
PBEKeySpec constraints, not the stream rules). ENSURES `cipheredInputStream` is a
**registered** no-constant omission (predicate_omissions.csv
`predicate-no-constant` row; predicate_edges `capability-absent`) — register
accurate, folded into the synergy table.

**Registration of the global monitor: absent.** I searched
`data/gh101/*.csv` and `*.md` for `parameterless`, `global monitor`,
`no parameter`, `empty parameter` applied to CIS/COS and found nothing; the CIS
divergence row (`6bf44a28d132`) covers only the generatedCipher read —
GAMA-CIS-03 FAIL major.

**History.** 0 lines / 0 unique_msg / 0 APKs / 0 sites; token
"CipherInputStream" in zero fields of 97,018 lines (output §A, §C). The jca twin
was also a parameterless global monitor with a live `@fail` — any campaign app
using two cipher streams in one process would have emitted false positives. The
zero therefore implies not-woven / not-exercised / emission-lost, never
conformance — folded into GAMA-SET-16 (INCONCLUSIVE), extending batch-A
GAMA-SET-11 with named tests.

**Synergy table (protocol §13).**

| Rule/clause | Possible static fact | Binding/predicate in .mop | Dynamic event/state | Diagnosis emitted | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `Constructs, Reads+, c` | read/close sites mappable (4/5 extractor rows); ctor row `new` blind (GAMA-SET-09/13) | no spec parameter — no object identity | global automaton, per-process | `@fail` unknown | false-fail zone on any multi-stream process is a third state the static view cannot predict |
| `Constructs` incl. 1-arg c1 | ctor sites blind anyway | 1-arg event absent; protected ctor unobservable by call() | reads without c1 → fail from state 0 | unknown | unobservable creation = silent third state |
| CONSTRAINTS `len > off` | argument constants occasionally | not translated (empty r2 body) | none | none | GAMA-CIS-04: full silence |
| REQUIRES `generatedCipher[ciph]` | co-occurrence approx. only | body read, GENERATED_CIPHER; writer CipherSpec:161,188,207 (inside condition) | report at construction | `UnsatisfiedConstraint`, literal | cipher init'd with unvalidated key is unmarked upstream ⇒ stream site accusation is displaced from the real defect |
| ENSURES `cipheredInputStream[is,ciph]` | n/a | no constant (registered) | none | n/a | registered capability-absent omission |

jca twin: differs only in c1 (jca binds nothing, no body). Extractor target rows
identical for CIS (see §4).

### 2.2 CipherOutputStreamSpec (COS)

Rule mirrors CIS with Writes w1/w2/w3 and no flush event. All CIS findings carry
over structurally (tables in §1a): GAMA-COS-01 (global monitor, crítica; proven by
identical table shape, executed via CIS), GAMA-COS-03 (unknown), GAMA-COS-04
(unregistered), GAMA-COS-05 (REQUIRES read PASS), GAMA-COS-06 (len>off omitted).

**COS-specific, executed (harness `cos`): flush is in the monitored alphabet but
not in the rule.** `ere: c1 (w1|w2|fl)+ cl` vs ORDER `Constructs, Writes+, c`.
Two-direction language break at the α level: (i) construct→write→close then
`flush()` — a trace the rule does not even observe — produced a false
`InvalidSequenceOfMethodCalls` (executed: `errors 0 → 1` at loc :119); (ii)
construct→flush→close with **no write** is accepted by the monitor and rejected
by the rule (`Writes+`) — FN. GAMA-COS-02 FAIL crítica.

**History.** 0/0/0/0; token nowhere. Same reading as CIS (GAMA-SET-16).

Synergy: as CIS, plus row — flush | statically mappable (`flush` row present in
extractor) | not a rule event | `fl` transitions the automaton | `@fail` unknown |
the static view keyed on the .mop would count flush sites as monitored-relevant,
a target the ORACLE never defined (over-approximation unique to COS).

### 2.3 KeyPairSpec (KPR)

Rule: EVENTS co(consPub, consPriv), pu, pr; ORDER `co?, (pu*, pr*)*`; REQUIRES
`generatedPrivkey[consPriv]`, `generatedPubkey[consPub]`; ENSURES
`generatedKeypair[this,_] after co`, `generatedPubkey[retPub] after pu`,
`generatedPrivkey[retPriv] after pr`.

**G9 handler audit.**

| Path | category/clause | expected/observed | __LOC | identity | dedupe |
|---|---|---|---|---|---|
| c1 body (mop:32-39) | 2× `UnsatisfiedConstraint`, one per REQUIRES — clause-attributable messages | literal messages | present | none bound (see 1b) | **both reports share (type,spec,loc) ⇒ second is dropped when both fire** (GAMA-KPR-04, executed: kpr_c kept only the public-key clause) |
| `@fail` (mop:63-66) | `InvalidSequenceOfMethodCalls`, live | `expecting=unknown` | present | broadcast/empty-slice | one record per site |
| `@match` (mop:68-70) | `setObjectAsInAcceptingState(keyPair)` | **passes null forever** (GAMA-KPR-03, executed) | — | — | — |

**GAMA-KPR-01 (FAIL, crítica — the headline).** The rule makes the constructor
optional (`co?`); the ere makes `c1` mandatory. `KeyPairGenerator.generateKeyPair()`
→ `getPublic()`/`getPrivate()` — the dominant, oracle-accepted flow — hits
`gpu/gpr` transition `{2,1,2}` from state 0 ⇒ fail. Executed (kpr_a): two false
`InvalidSequenceOfMethodCalls` (`unknown`). §13 rule violated: an oracle-accepted
trace is rejected. **History is consistent in every stratum (MEDIDO, hypothesis
only)**: all 668 historical KeyPairSpec lines are InvalidSequenceOfMethodCalls,
all 668 `message=unknown`, spread over exactly 8 sites whose method names are
`generateECKeys` (io.ktor TLS, 3 APKs), `generateKeyPair`, `CertReq`,
`KeyPairGenRSA.init`, `generateKey` — key-generation wrappers, precisely where a
generated pair's accessors run; per-site line counts are all even (286/218/134/
16/8/2/2/2), consistent with gpu+gpr pairs re-emitted per process restart (pilot
H7). H2 check inside KPR: 0 of 258 execution×site cells pair a specific error
with InvalidSeq (B.5) — nothing specific ever fired; H4 "but found ." = 0 (B.6).
The jca twin has the same `ere`, so the mechanism existed throughout the
campaign. Causal attribution deferred to replay (H-KPR-1; tests named in claim).
GAMA-KPR-07: this ORDER divergence is in no gh101 register (searched all
KeyPairSpec rows — all predicate-graph — plus conformance_record,
frozen_set_debt.md, README.md for `co?`/optional/generateKeyPair).

**GAMA-KPR-02 (FAIL, crítica).** Empty-slice broadcast (§1b), executed (kpr_b):
second construction ⇒ false fail at the c1 site (loc :161) **and** the new pair's
first `getPublic()` also fails (loc :163) because the broadcast `__RESET` had
reset the empty-slice leaf that seeds every later binding. Instance isolation
(semantic model §3) violated: constructions contaminate every live monitor.

**GAMA-KPR-03 (FAIL, minor).** The spec variable `keyPair` (mop:21) collides with
the spec parameter name (mop:19); in the generated `Prop_1_event_c1` the restored
local shadows the field (`:178-182`), `keyPair = kp` writes the local, nothing is
written back, and `Prop_1_handler_match` (`:239-244`) reads the never-assigned
field. Executed: `isInAcceptingState(kp1)=false`, `isInAcceptingState(null)=true`
after a valid construction. No production reader of `isInAcceptingState` exists
(searched jca_android/*.mop and rvsec Java sources: tests only), and gh101's
README already records the accepting-state marker as inert set-wide — hence minor.

**Repairs verified (PASS, folded into synergy):** gpr now writes
GENERATED_PRIVATE_KEY (mop:58; jca wrote the public constant — the registered
wrong-constant defect `021c4ee5ed69`); c1 writes GENERATED_KEY_PAIR (registered
`d1eb9309d849`; deliberate writer-no-reader in predicate_omissions.csv —
register accurate); the two REQUIRES reads exist and are clause-specific
(registered `130490fde626`) — undermined only by the dedupe collapse
(GAMA-KPR-04).

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `co?, (pu*, pr*)*` | getPublic/getPrivate sites mappable; ctor blind (`new`) | c1 unbound to spec param (1b) | mandatory-c1 automaton | `@fail` unknown | the entire generated-pair flow is a false-fail zone; static view cannot flag it |
| REQUIRES generatedPubkey/Privkey[cons*] | not expressible statically | body reads, null-guarded | report at c1 | 2 literal messages | dedupe collapses the two clauses at one site (GAMA-KPR-04) |
| ENSURES generatedPubkey[retPub]/Privkey[retPriv] | n/a | gpu/gpr writes (repaired) | every gpu/gpr, any state | n/a | writes execute even on the false-fail path (body-before-handleEvent) — matches the rule's unconditional ENSURES |
| ENSURES generatedKeypair[this,_] | n/a | GENERATED_KEY_PAIR write; `_` slot dropped (1-slot store) | c1 | n/a | registered writer-no-reader |

jca twin diverges (c1 body, gpr constant, GENERATED_KEY_PAIR write; same ere) —
extractor target rows identical (§4).

### 2.4 SecretKeySpec.mop / spec `SecretKeySpec` (SKY)

Rule: EVENTS d (destroy), ge (getEncoded); ORDER `ge*, d?`; ENSURES
`preparedKeyMaterial[keyMaterial] after ge` (**unconditional**; the rule has NO
REQUIRES); NEGATES `generatedKey[this,_] after d`.

**G9 audit.** No reporting path exists anywhere in the spec or artifact (§1c):
no category `fail`, no handler, no `ErrorDescription`. Executed (sky(b)):
`getEncoded` after `destroy` — an ORDER violation — and a second `destroy` both
produced **zero** records (dead state 2 absorbs them silently). GAMA-SKY-01 FAIL
crítica: this spec cannot say anything, and unlike batch-A DHG/HMC the oracle
here HAS violating traces to report. (Vacuous-unknown PASS does not apply.)

**GAMA-SKY-02 (FAIL, crítica).** e1 is gated by
`condition(validate(GENERATED_KEY, secretKey))` (mop:22-27) — a REQUIRES the rule
does not state. Executed (sky(a)): a key without the mark ⇒ event suppressed,
`RANDOMIZED(keyMaterial)=false`, zero records. The rule marks the material
unconditionally. Downstream RANDOMIZED readers — PBK err2/err3, batch-A
SecretKeySpecSpec c3 — then accuse oracle-conformant flows at displaced sites
(chain read from production specs; end-to-end inferred, pendency G10-SKY-1).
Unregistered: GAMA-SKY-04 (searched the SecretKeySpec.mop divergence row
`3d12842da2f6` — d/NEGATES only; predicate_edges "present-surrogate" carries no
gating caveat; README:162 counts only the borrowed constant).

**PASS side.** GAMA-SKY-03: NEGATES executed — after d, `GENERATED_KEY(key)`
=false; per-object removal (`ExecutionContext.remove(Property,Object):81-88`),
identity-consistent; the 1-slot store makes `[this,_]` trivially faithful (the
reader/negates side of FEN-SET-GENERATEDKEY-2A-CASA is coherent here).
GAMA-SKY-05: the effective automaton accepts exactly `ge* d?` (states 0,1
accepting; 2 dead) — the `(d | epsilon)` encoding is language-equal and the
register's "verified in the generated monitor" claim reproduces.

**Cross-spec note (round manifest check).** `javax.crypto.spec.SecretKeySpec`
implements `SecretKey`; a monitored valid SecretKeySpec construction (batch-A
spec) earns GENERATED_KEY in `@match`, which is precisely what opens SKY's e1
gate; the violating branches earn nothing, so their `getEncoded` is suppressed
too — the two specs' predicate lifecycles compose, but only through the
non-rule gate of GAMA-SKY-02. Double-fire of ERROR records cannot occur (SKY has
no error channel). Pointcut-level double-match is Beta's lane.

**History.** Spec name `SecretKeySpec`: 0/0/0/0. Tokens `getEncoded`,
`clearPassword`: zero occurrences dataset-wide; token `SecretKey` appears only in
24 KeyStoreSpec lines (1 APK) (output §C). The jca twin was channel-less too
(`ere e1*`, no @fail) — zero is expected there; still not conformance
(GAMA-SET-16).

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `ge*, d?` | getEncoded/destroy sites mappable by name — **but only where the call-site static type is the interface** (GAMA-SET-14) | secretKey bound by both events; per-object monitor (correct indexing) | silent dead state on violation | **none — no channel** | GAMA-SKY-01; SET-14 undercount for concrete-typed receivers |
| ENSURES preparedKeyMaterial[keyMaterial] | n/a | RANDOMIZED surrogate (registered), **gated by non-rule GENERATED_KEY** | suppressed for unmonitored keys | n/a | GAMA-SKY-02: displaced downstream FPs |
| NEGATES generatedKey[this,_] | n/a | remove per object | d, any state (body always runs) | n/a | faithful (GAMA-SKY-03) |
| `destroy` target in static view | present in jca_android extractor rows; **absent from jca twin's** | — | — | — | GAMA-SET-12: the config default (`jca`) loses exactly this target |

### 2.5 PBEKeySpecSpec (PBK)

Rule: FORBIDDEN `PBEKeySpec(char[]) => c1`, `PBEKeySpec(char[],byte[],int) => c1`;
EVENTS c1 (4-arg ctor), cP (clearPassword); ORDER `c1, cP`; CONSTRAINTS
`iterationCount >= 10000`, `neverTypeOf(password, String)`; REQUIRES
`randomized[salt]`; ENSURES `speccedKey[this, keylength] after c1`; NEGATES
`speccedKey[this,_] after cP`.

**G9 handler audit.**

| Path | category/clause | expected/observed | dedupe |
|---|---|---|---|
| f1/f2 bodies (mop:29,35) | `InvalidSequenceOfMethodCalls` for a FORBIDDEN ctor — miscategorized; 3-arg ⇒ `unknown` | indistinguishable from `@fail` records except `__LOC` (executed pbk(c)) | per site |
| err1 (mop:54-55) | `UnsatisfiedConstraint`, names the argument — but message **false**: "should be >= 1000" vs enforced 10000 | GAMA-PBK-02 (FEN-PBE-MSG-1000, batch-A twin phenomenon) | — |
| err2/err3 (mop:62,70) | `UnsatisfiedConstraint`, argument-specific messages | err2 enforces a clause the rule does not state (GAMA-PBK-05) | **all three err share (type,spec,__LOC) at a real site ⇒ only the first violated clause in advice order (c1,err1,err2,err3 — Aspect.aj:48-58) is ever recorded** (GAMA-PBK-01, executed: 1 record vs 3-line control) |
| `@fail` (mop:90-94) | `InvalidSequenceOfMethodCalls`, live | `unknown`; fires at cP after any non-c1 construction (GAMA-PBK-04) | — |
| `@match` (mop:96-98) | `setObjectAsInAcceptingState(spec)` | field write correct here (no name collision — contrast KPR-03) | — |

**Executed highlights** (`gama_harness_output.txt`, scenario pbk):
(a) weak construction (`itc=500`, unrandomized pw+salt), all four events issued
from one source line as the merged advice does ⇒ **one** record, `third argument
should be >= 1000`; the two randomization clauses are permanently masked at that
site. (a2) `clearPassword()` on that spec — the rule's OWN ORDER `c1, cP`
satisfied — adds a spurious `InvalidSequenceOfMethodCalls (unknown)`:
the specific-error+spurious-sequence pairing the layer-2 repair targeted
**returns in delayed form**, triggered by the hygiene action the rule demands.
This refutes pilot H2's prediction ("the derived set decouples the pairing") for
PBK whenever cP is called. (b) control on three distinct lines ⇒ 3 records —
the collapse key is the shared `__LOC`. (c) forbidden `f1` then `cP` ⇒ two
records, same category, both `unknown`, distinguishable only by `__LOC`.

**GAMA-PBK-05 (FAIL, crítica).** err2 (and c1's condition) require
`RANDOMIZED[password]`; the rule requires randomization of the **salt** only
(password has `neverTypeOf`, a static type clause — registered as out of scope in
README §4.11). RANDOMIZED writers are SecureRandomSpec/RandomStringPassword/SKY-e1;
a user-typed password can never carry it, so every real password-based
construction is accused on a clause the frozen oracle does not state, and — since
c1's condition also demands it — a fully rule-conformant spec never earns
SPECCED_KEY (ENSURES FN) and its `cP` then fires the spurious `@fail` of
GAMA-PBK-04. Inherited from jca (diff shows the conditions predate gh101);
unregistered either way (GAMA-PBK-06: searched `password`/`1000` across
data/gh101 — only the f1/f2 layer-2 rows and the neverTypeOf note exist).

**Repair verified.** GAMA-PBK-07 PASS: star-prefix and returning() repairs are
real in the artifact (`{0,3,3,3}` loops; no immediate spurious InvalidSeq at the
violating construction — executed), with the delayed-cP caveat above.

**History.** 0/0/0/0; token `PBEKeySpec` in zero fields. In jca, f1/f2 were
empty-slice events whose firing would have added spurious pairs — zero lines
means the constructors never executed under weaving, or emission was lost
(GAMA-SET-16).

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| FORBIDDEN 1/3-arg ctors | ctor sites blind (`new` — 3 of PBK's 4 extractor rows) | f1/f2 bound via returning (repaired) | state-0 loop | InvalidSeq `unknown` — miscategorized | GAMA-PBK-03; static path cannot list forbidden-ctor sites either (SET-13) |
| ORDER `c1, cP` | clearPassword mappable (the ONLY statically visible PBK member) | c1 valid-only | c2 from 0 ⇒ fail | delayed spurious @fail | GAMA-PBK-04 |
| CONSTRAINTS itc>=10000 | constants sometimes extractable | folded into c1/err1 conditions | suppression + report | false "1000" message | GAMA-PBK-01 collapse; GAMA-PBK-02 |
| REQUIRES randomized[salt] | not expressible | err3/c1 read | report | argument-specific | masked whenever err1 fires first |
| (non-rule) randomized[password] | — | err2/c1 read | report | "first argument…" | GAMA-PBK-05 systematic FP |
| ENSURES speccedKey[this,keylength] | n/a | SPECCED_KEY write, 2nd slot dropped | @match after cP | n/a | registered writer-no-reader (SecretKeyFactory unmodelled); conformant spec never earns it (PBK-05) |
| NEGATES speccedKey[this,_] after cP | n/a | remove at c2 | c2 any state | n/a | faithful mechanism; runs even on fail path |

## 3. Static-analysis synergy — set level (measured)

Executed: production `mop-extractor.jar` (`-t METHODS_PARAMS`) over scratch
copies of the five jca_android specs and their five jca twins
(`gama_extractor_ja.csv`, `gama_extractor_j.csv`).

- **GAMA-SET-13 (MEDIDO)** — 6 of 20 jca_android rows carry method name `new`,
  unresolvable by the GATOR client (no `"new"→"<init>"` normalization —
  GAMA-SET-09 cited, previously judge-verified). Mappable targets per spec:
  CIS 4/5, COS 5/6, KPR 2/3, SKY 2/2, PBK 1/4 (7 of its 8 declared events sit on
  the 3 blind ctor rows; only `clearPassword` is visible). Batch B is therefore
  **partially** mappable — §13's 100% unlock condition is still unreachable, but
  unlike batch A the method-event clauses can be mapped.
- **GAMA-SET-12 (MEDIDO)** — jca vs jca_android target diff is **exactly one
  row**: `javax.crypto.SecretKey,destroy` absent from jca. Under the production
  default (`mop_dir` literal `jca`, GAMA-SET-01), the static view of a
  jca_android-instrumented APK silently omits the destroy target and nothing
  else; the wrong-dir default is measured near-vacuous for batch B targets,
  destroy excepted.
- **GAMA-SET-14 (OBSERVADO)** — the bytecode-scan and resolver key on the
  **static declaring class** string
  (`RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan:574-603`,
  `buildTargetKeys:613-631`); calls typed through an implementor
  (`SecretKeySpec.getEncoded()` ⇒ `javax.crypto.spec.SecretKeySpec#getEncoded`)
  never match SKY's `javax.crypto.SecretKey#getEncoded` key, while the woven
  `call()` pointcut does match subtype receivers — a static/dynamic mismatch
  specific to the round's one interface spec (AspectJ side inferred from
  semantics, not executed; Beta's matcher lane).
- **GAMA-SET-15 (PASS)** — newline-escape pending case for batch B: every
  reachable `expecting` in the five artifacts is a compile-time literal or absent
  (⇒ "unknown"); SKY serializes nothing. No app-controlled content reaches the
  logcat line; `__LOC` remains the theoretical residue (as batch A). GAMA-CIP-07
  stays open for CipherSpec only.

Nominal-selection check (§13): unchanged from GAMA-SET-01/03 — re-verified at
`rv_static_analysis/config.py:186-206` this round (probe list still lacks "30";
default still literal `jca`).

## 4. History discipline summary (protocol §12)

Freeze verified in-script before read. Units always separated; global sanity
matches the pilot exactly (97,018 / 225 / 113 / 454 / 8,147). Batch B:

| Spec | lines | unique_msg | APKs | sites |
|---|---:|---:|---:|---:|
| CipherInputStreamSpec | 0 | 0 | 0 | 0 |
| CipherOutputStreamSpec | 0 | 0 | 0 | 0 |
| KeyPairSpec | 668 | 5 | 8 | 8 |
| SecretKeySpec | 0 | 0 | 0 | 0 |
| PBEKeySpecSpec | 0 | 0 | 0 | 0 |

KPR: 100% InvalidSequenceOfMethodCalls, 100% `unknown`, 8 key-generation-wrapper
sites, even per-site counts, spread across all 11 tools (per-tool table in
output §B.4 — qtesting 136 lines / 19 cells illustrating H7 process-restart
inflation). Pilot hypotheses on batch-B classes: **H1** stands (the four zeros
decompose per spec; CIS/COS zeros are the anomalous ones — their jca twins could
fire); **H2** refuted-in-new-form for PBK (delayed pairing at cP, executed) and
untestable historically for KPR (0 cells with specific+generic — nothing
specific existed to pair); **H4** zero inside batch B; **H7** used as a design
constraint (counts per cell, never compared raw). New hypothesis **H-KPR-1**
(the 668 lines are the KPR-01 FP): discriminating tests named in claim
GAMA-KPR-06 — micro-APK with `generateKeyPair()+getPublic()` woven by ajc AND
dexlib2 with RVSEC-COV site check; paired replay jca vs jca_android at one
historical site; DEX inspection of a campaign-era instrumented APK. No causal
attribution is made from the historical data.

## 5. Threats to validity of this report

1. **Harness ≙ woven app**: the harness invokes the generated static event
   methods exactly as the generated advices do (verified against the `.aj`
   bodies), but no weaving/DEX execution happened this round — each executed FP/FN
   claim carries a named G10 pendency for the micro-APK confirmation.
2. **Oracle bias (recorded)**: api30 rules model availability; CIS/COS `len>off`
   is itself a dubious derivation, and SKY-02/PBK-05 verdicts are relative to the
   frozen api30 oracle by pre-registration (the 1.5.2 anchor may differ; recorded,
   not resolved).
3. **Historical data are pre-repair/pre-GH100**: hypothesis generation only;
   pseudoreplication controlled by reporting per unit and per cell.
4. **Single-generation artifacts**: generator determinism verified in the pilot
   (REF-11 caveat: determinism, not independent replication).
5. **Advice-order dependence**: which clause survives the PBK collapse follows
   AJC textual advice order; dexlib2 may order differently — the collapse itself
   is order-independent (dedupe key), only the survivor may vary.
6. **Extractor run** exercises `JavamopFacade.listUsedMethods` as the GATOR
   client does (`MopSpecsTargetSource`), not the full GATOR invocation.

## 6. Verdict inputs per spec (Gama's lane only)

- **CIS / COS**: the global monitor makes every multi-stream process a false-
  positive generator with `unknown` records — REPROVADA-supporting evidence from
  my lane (executed FP; G9 breach; unregistered divergence).
- **KPR**: mandatory-c1 vs `co?` plus empty-slice broadcast produce executed FPs
  on the dominant API flow; the whole 668-line history is `unknown` and
  plausibly this FP — REPROVADA-supporting.
- **SKY**: no diagnostic channel where the oracle has violations (executed
  silence) + non-rule gating of its ENSURES — REPROVADA-supporting; NEGATES and
  ORDER themselves faithful (two PASS claims).
- **PBK**: repairs real, but collapse+false message+forbidden-miscategorization
  +delayed spurious @fail + non-rule password clause — REPROVADA-supporting.

(Verdicts are the judge's; these are inputs, dimension-assigned at creation.)

## 7. Scientific log

| # | Question | Hypothesis | Discriminating test | Evidence | Result | Uncertainty | Next decision |
|---|---|---|---|---|---|---|---|
| 1 | Is the indexing tree per-object in all five? | No for CIS/COS (no parameter) | read artifact indexing decl | §1a | global monitor (PROVADO) | none | executable FP test → harness |
| 2 | Does a conformant 2nd stream lifecycle emit? | Yes, falsely | JVM harness, marked cipher | cis(b): 3 false InvalidSeq | FP EXECUTADO | weaving pendency | GAMA-CIS-01/COS-01 crítica |
| 3 | Does KPR reject the generated-pair flow? | Yes (`co?` dropped) | harness gpu/gpr without c1 | kpr_a: 2 false records | FP EXECUTADO | weaving pendency | KPR-01 crítica |
| 4 | Are the 668 historical lines consistent with #3? | Yes | freeze-checked stratification, 4 units, sites, categories | §4: 100% InvalidSeq/unknown at 8 keygen sites | consistent (MEDIDO) | pre-repair data; no causal claim | H-KPR-1 + replay tests named |
| 5 | Does c1 bind the KPR spec parameter? | No — empty slice + broadcast | artifact dispatch + harness 2 ctors | kpr_b: broadcast fail + reset cascade | EXECUTADO | none material | KPR-02 crítica |
| 6 | What does `@match` mark? | null (name collision) | harness isInAcceptingState probes | kpr_b: null=true, kp=false | EXECUTADO | no reader today | KPR-03 minor |
| 7 | Do same-site multi-clause reports survive dedupe? | No (`expecting` excluded) | one-line vs three-line harness | kpr_c: 1 of 2; pbk: 1 of 3 + control 3 | EXECUTADO | dexlib2 survivor order | KPR-04 / PBK-01 major |
| 8 | Is ge-after-destroy reported? | No (no channel) | harness sky(b) | 0 records on 2 violations | FN EXECUTADO | destroy rarity | SKY-01 crítica |
| 9 | Is SKY's ENSURES gate in the rule? | No | rule read + harness sky(a) | unmarked material, 0 events | EXECUTADO + rule | 1.5.2 anchor | SKY-02 crítica + SKY-04 register |
| 10 | Is flush in the COS rule? | No | rule read + harness flush-after-close | +1 false InvalidSeq | EXECUTADO | IOException variants | COS-02 crítica |
| 11 | Can the static path map batch B? | Partially (`new` rows blind; jca dir loses destroy) | extractor over both sets + diff | §3 | MEDIDO | client-vs-extractor path | SET-12/13/14 filed |
| 12 | Any app content reaching the logger? | None | inspect every reachable ErrorDescription | §3 SET-15 | literals only | SourceFile residue | SET-15 PASS |

## 8. Commands (reproduction)

```
sha256sum $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/{CipherInputStreamSpec,CipherOutputStreamSpec,KeyPairSpec,SecretKeySpec,PBEKeySpecSpec}.mop
sha256sum $WS/MetaCrySL/generated/api30/{CipherInputStream,CipherOutputStream,KeyPair,SecretKey,PBEKeySpec}.cryptsl
sha256sum $ANDROID_HOME/platforms/android-30/android.jar          # 96ccfdc8...
unzip -o android-30/android.jar javax/crypto/CipherInputStream.class && javap -p <extracted>  # ctor visibility from bytes
uv run python batchB/gama_errors_batchB.py                        # freeze-check + stratification
diff jca/<S>.mop jca_android/<S>.mop                              # twin divergence, all five
javac -cp rv-monitor-rt.jar:rvsec-core.jar:rvsec-logger-csv.jar -d classes mop/*.java gama/GamaBatchBDrive.java
for s in cis cos kpr_a kpr_b kpr_c pbk sky; do java -cp ... gama.GamaBatchBDrive $s; done   # gama_harness_output.txt
java -jar rvsec-mop-extractor/target/mop-extractor.jar -d <scratch>/specs_ja -o gama_extractor_ja.csv -t METHODS_PARAMS
java -jar rvsec-mop-extractor/target/mop-extractor.jar -d <scratch>/specs_j  -o gama_extractor_j.csv  -t METHODS_PARAMS
```
