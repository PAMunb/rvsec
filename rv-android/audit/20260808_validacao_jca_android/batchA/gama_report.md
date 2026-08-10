# GAMA — Batch A report: diagnostics, experimental history, static synergy

Agent Gama · 2026-08-09 · adversarial posture. Round "batch A" of the `jca_android`
audit. Scope: DHGenParameterSpecSpec (DHG), HMACParameterSpecSpec (HMC),
PBEParameterSpecSpec (PBE), IvParameterSpec.mop / spec `IvParameterSpecSpec` (IVP),
SecretKeySpecSpec (SKS).

Governing rules applied without re-litigation: D-piloto-1 (ORDER reading A),
D-piloto-3 (effective automaton is the language-evidence source), D-piloto-4
(dimension assigned at creation; SET claims scored separately; six normative states)
— `fase0/desvios.md`. Established SET findings cited, not re-derived: GAMA-SET-01/03
(static path defaults to literal `jca` mop_dir, `rv_static_analysis/config.py:199-206`;
android_jar probe list `["33","29","28","27","26"]` without "30",
`rv_static_analysis/config.py:186-194`), GAMA-SET-02/06 (identity/dedupe multi-layer
inconsistency), 3-arg `ErrorDescription` ⇒ `expecting="unknown"`
(`rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java:34-36`),
GAMA-CIP-07 (ErrorCollector escape commented out,
`rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java:39-40,44-51`).

Method note (protocol §2): Sequential Thinking MCP was available and used (5 recorded
steps); this report publishes only the scientific log, not chain-of-thought.

## 0. Inputs and provenance

- Specs read from `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`;
  sha256 of all five verified equal to `batchA/generation_manifest.md` and
  `fase0/manifest_hashes.md` (command: `sha256sum <spec>.mop`, outputs in §per-spec).
- Effective artifacts: the round's common generated set under
  `<scratch>/batchA/gen_<Spec>/out/` (hashes in `generation_manifest.md`). All
  language-level statements below are made over these artifacts (D-piloto-3).
- CrySL oracle: `MetaCrySL/generated/api30/*.cryptsl`, raw (availability profile;
  bias recorded, never corrected — pre_registro §1).
- Historical dataset: `ase-journal/dataset/results/errors.csv`, sha256 verified
  `78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69` (26,323,122
  bytes) **before** any read, inside `gama_batcha_errors.py` (freeze-check aborts on
  mismatch) and by `sha256sum`. PRE-GH100/GH101 — hypothesis generator only.
- android.jar API 30 (frozen): `$ANDROID_HOME/platforms/android-30/android.jar`,
  sha256 `96ccfdc84d15fad4e22d76cbb8ef38b150a4b56327957067875ca7e18113a424`
  (matches `fase0/toolchain_ambiente.md` §4).
- No emulator, no device, no weaving executed (G10 pendencies named per spec).
  No file outside `batchA/gama_*` written; specs/rules/production code untouched;
  the only executions were read-only analyses plus `mop-extractor.jar` over a
  **scratch copy** of the five specs (never over the spec tree).

## 1. Structural fact shared by all five specs (proven once, cited per spec)

Every event in all five specs is an `after(...) returning(s)` advice on a
**constructor** of the monitored class, and every monitor is indexed by the returned
object `s`. Each object therefore delivers **exactly one** event to its monitor, once.
The effective transition tables are:

| Spec | tables (state 0=start, 1=match, 2=fail) | source |
|---|---|---|
| DHG | `c1 {1,2,2}` | `gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecRuntimeMonitor.java:68` |
| HMC | `c {1,2,2}` | `gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecRuntimeMonitor.java:94` |
| PBE | `c1,c2 {1,2,2}; c3 {0,2,2}` | `gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecRuntimeMonitor.java:115-117` |
| IVP | `c1,c2 {1,2,2}; c3,c4 {0,2,2}` | `gen_IvParameterSpec/out/IvParameterSpecRuntimeMonitor.java:137-140` |
| SKS | `c1,c2 {1,2,2}; c3,c4 {0,2,2}` | `gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java:139-142` |

State 2 (fail) is reachable only from states 1 or 2, i.e. only on a **second** event
of the same monitor — impossible under one-constructor-per-object identity.
**PROVADO**: `@fail` (and its 3-arg `"unknown"` `ErrorDescription`) is dead code in
all five artifacts; consequently no post-`__RESET` cascade (ALFA-CIP-22 analogue) is
realizable in any of them — `__RESET` sits exclusively inside the unreachable handler.
This is the same monitor shape the pilot proved for GCM (pilot
`gama_diagnostico.md` §2, table `{1,2,2}`); phenomenon family FEN-GCM-SUPRESSAO
extends to DHG (see §2.1).

Second shared artifact fact (**PROVADO**): the merged advice per constructor calls the
conformant event and then the violating event (`gen_SecretKeySpecSpec/out/
SecretKeySpecSpecMonitorAspect.aj:39-44` — `c1Event` then `c3Event`; same in IVP/PBE;
descriptor `monitorCalls` order identical). The static dispatch **ignores** the boolean
returned by `Prop_1_event_*` and re-checks the persistent `Category_*` flags after
every call (`gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java:414-419`).
On a **valid** construction, `c1Event` sets `Category_match` and runs `@match`; the
following suppressed `c3Event` (`return false` before `handleEvent`) leaves the flags
untouched and the dispatch **re-executes `@match`** on stale flags. Effects here are
idempotent (`setProperty`/`setObjectAsInAcceptingState` with identical arguments) —
benign but an unjustified handler double-execution: claim GAMA-SET-08 (pilot recorded
the mechanism as an unclaimed lateral finding, pilot `gama_diagnostico.md` §3).
On an **invalid** construction the order is safe: the violating event reports in its
body *before* `handleEvent`, transitions 0→0, flags stay false, no handler runs — the
specific report stands alone. This is the verified effect of the gh101 layer-2 repair
(no spurious `InvalidSequenceOfMethodCalls`, no displaced accusation) for PBE/IVP/SKS.

## 2. Per-spec diagnostic audit (G9), history, synergy

### 2.1 DHGenParameterSpecSpec (DHG)

`DHGenParameterSpecSpec.mop` sha256 `f2f6aed6…` (= manifest). Rule
`DHGenParameterSpec.cryptsl` sha256 `b5177f43…`: EVENTS `c1(primeSize, exponentSize)`,
ORDER `c1`, ENSURES `preparedDH[this]`, **no CONSTRAINTS, no REQUIRES**.

**G9 handler audit.**

| Handler | (a) cat+clause | (b) spec+set | (c) event/expected | (d) state | (e) __LOC | (f) identity | (g) dedupe |
|---|---|---|---|---|---|---|---|
| `@fail` (mop:30-33) | dead code — unreachable (§1) | n/a | n/a | n/a | n/a | n/a | n/a |
| `@match` (mop:35-38) | n/a (writes PREPARED_DH) | — | — | — | — | — | — |

No reachable handler emits anything: this spec has **no diagnostic channel at all**.
Vacuously, no `unknown` can be emitted (GAMA-DHG-03, PASS). The G9 problem is what the
spec *silences*:

**Suppression of oracle-conformant traces (GAMA-DHG-01, FAIL, crítica).**
`condition(exponentSize < primeSize)` (mop:24; artifact
`DHGenParameterSpecSpecRuntimeMonitor.java:111-115`, `return false` before
`handleEvent`) has **no counterpart in the api30 rule** — the rule has no CONSTRAINTS
section. A construction with `exponentSize >= primeSize` is **accepted by the oracle**
but produces: no event, no monitor, no `@match`, no `PREPARED_DH`, no accepting mark.
Downstream, `KeyPairGeneratorSpec.mop:95-99` and `:106-110` read
`!validate(Property.PREPARED_DH, params)` for `"DH".equals(algorithm)` and emit
`UnsatisfiedConstraint` — "initialize() for DH requires an AlgorithmParameterSpec
established by a monitored DHGenParameterSpec sequence." — at the **KeyPairGenerator
site under the KeyPairGeneratorSpec name**. Against the raw api30 oracle this is a
realizable **false positive with displaced attribution** (wrong spec, wrong site, and
a "requirement" message for a rule that states no such requirement). §13 rule
violated: a trace accepted by the CrySL oracle is rejected by the MOP set.
Mechanism PROVADO in artifacts; end-to-end FP INFERIDO (no execution this round —
pendency G10-DHG-1: JVM harness constructing `DHGenParameterSpec(1024, 2048)` then
`KeyPairGenerator.initialize`). Bias note (recorded, not corrected): CrySL 1.5.2's
DHGenParameterSpec carries `exponentSize < primeSize`; the api30 derivation dropped it
(MetaCrySL availability profile). The `.mop` follows the 1.5.2 anchor, not the frozen
oracle.

**Unregistered divergence (GAMA-DHG-02, FAIL, major).** I searched
`data/gh101/divergence_record.csv` for a `DHGenParameterSpecSpec.mop` row and found
none (the only mention of DHGen is inside the KeyPairGeneratorSpec hunk
`7a1c46677ac2`). I searched `data/gh101/frozen_set_debt.md` and
`data/gh101/README.md` for the condition-vs-api30 divergence and found nothing.
`conformance_record.csv` row for DHG says "the rule constrains key size through an
implication, not a membership set" — the api30 rule contains **no constraint at all**;
the register's reason describes the 1.5.2 anchor without saying so.

**History.** 0 lines / 0 unique_msg / 0 APKs / 0 sites (all four units; script
`gama_batcha_errors.py`, output `gama_batcha_errors_output.txt`). Token
"DHGenParameterSpec" appears in no field of any of the 97,018 lines. Consistent with:
class rarely used + spec channel-less (both `@fail` dead and, pre-repair, identical).
Zero ≠ conformance. H-DHG-1: any future non-zero for this spec name can only come
from `@fail` — i.e. would indicate a *different* artifact than audited. Discriminating
test: none needed beyond artifact identity (freeze).

**Synergy table (Cipher-format §13).**

| Rule/clause | Possible static fact | Binding/predicate in .mop | Dynamic event/state | Diagnosis emitted | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `c1` | sites of `new DHGenParameterSpec(int,int)` | c1 binds (primeSize, exponentSize); condition NOT in rule | c1 → state 1 (match) or silent suppression | none (no handler reachable) | **static path cannot see constructor targets at all** (GAMA-SET-09); suppression zone = silent third state |
| ENSURES `preparedDH[this]` | n/a (predicate) | `setProperty(PREPARED_DH, spec)` mop:36 | @match only | n/a | denied to oracle-conformant objects with exp≥prime (GAMA-DHG-01); reader KPG:95-110 then accuses at wrong spec/site |

jca twin: **byte-identical** (`cmp` PASS; manifest anomaly 2) — GAMA-SET-01's wrong-dir
default changes nothing for this spec; GAMA-SET-09 (below) makes the static column
vacuous either way.

### 2.2 HMACParameterSpecSpec (HMC)

Sha256 `254040e7…` (= manifest); rule `61d06431…`: EVENTS `c1(outputLength)`, ORDER
`c1`, ENSURES `preparedHMAC[this]`, no CONSTRAINTS/REQUIRES.

**G9.** Single unconditioned event `c` (mop:21-24); `@fail` dead (§1); `@match` writes
`PREPARED_HMAC` + accepting for every construction. Under the oracle there is **no
violating trace** (single creation event, no constraints), so the absent diagnostic
channel is vacuously conformant (GAMA-HMC-02, PASS). No `unknown` reachable.

**Platform availability (GAMA-HMC-01, FAIL, major — MEDIDO).**
`javax.xml.crypto.dsig.spec.HMACParameterSpec` is **absent from the frozen android-30
jar**: `unzip -l android-30/android.jar | grep -c "javax/xml/crypto"` = **0** (the
other four monitored classes are present). Consequences: (i) on an API 30 platform the
pointcut can only ever match an app-**bundled** copy of the class — the rule's
availability premise (api30 profile) is violated by its own derivation; (ii)
`PREPARED_HMAC` is unwritable for SDK types, so the reader edge
`MacSpec.mop:99-102` (`params != null && !validate(PREPARED_HMAC, params)` →
`UnsatisfiedConstraint` naming "a monitored HMACParameterSpec sequence") can never be
satisfied on-platform — every monitored `Mac.init(key, params≠null)` is accused,
regardless of app behavior. I searched `data/gh101/README.md`,
`data/gh101/frozen_set_debt.md` and `fase0/inventario_pareamento.md` for a record of
this absence and found none (the inventário notes only "única classe fora de
`java.security`/`javax.crypto`/`javax.net.ssl`"). Oracle bias recorded: MetaCrySL
api30 emitted a rule for an unavailable class.

**History.** 0/0/0/0 in all four units; token appears nowhere. Fully consistent with
class absence — and still not evidence of conformance.

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `c1` | sites of `new HMACParameterSpec(int)` — resolvable only if app bundles the class | c binds nothing (outputLength unbound — rule has no constraint on it; anonymous-equivalent, not a defect) | c → match always | none | class absent from android-30 ⇒ static Scene without app-bundled copy cannot even load the type; plus GAMA-SET-09 |
| ENSURES `preparedHMAC[this]` | n/a | `setProperty(PREPARED_HMAC, spec)` mop:35 | @match | n/a | unwritable on-platform ⇒ MacSpec:99 reader is a guaranteed-fire accusation edge |

jca twin byte-identical — same note as DHG.

### 2.3 PBEParameterSpecSpec (PBE)

Sha256 `f088e3b7…` (= manifest); rule `a6b7d2b1…`: EVENTS c1(salt, iterationCount),
c2(salt, iterationCount, paramSpec), `Cons := c1|c2`, ORDER `Cons`, CONSTRAINTS
`iterationCount >= 10000`, REQUIRES `randomized[salt]`, ENSURES `preparedPBE[this]`.

**G9 handler audit.**

| Path | (a) | (b) | (c) | (d) | (e) __LOC | (f) | (g) |
|---|---|---|---|---|---|---|---|
| c3 body (mop:42-51) | `UnsafeAlgorithm` — **miscategorized** (siblings use `UnsatisfiedConstraint`); no clause ID; conflates CONSTRAINT and REQUIRES | spec name only; no set field (GAMA-CIP-05 applies) | message **false**: "at least **1000** iterations" vs enforced `>= 10000` (mop:46, artifact `PBEParameterSpecSpecRuntimeMonitor.java:195`) | none | present (`ViolationRecorder.getLineOfCode()`) | none | in-JVM key excludes expecting (GAMA-SET-06 applies) |
| `@fail` (mop:60-63) | dead (§1) | — | — | — | — | — | — |
| `@match` (mop:65-68) | writes PREPARED_PBE + accepting | — | — | — | — | — | — |

**Repair verified (GAMA-PBE-03, PASS, PROVADO).** c3 is in the automaton
(`{0,2,2}`), its report runs before `handleEvent`, transition 0→0, flags false, no
handler follows: the specific error stands alone — the gh101 layer-2 repair holds in
the effective artifact; no body-before-handleEvent double accusation, no displacement.

**The 3-arg constructor has no violating branch (GAMA-PBE-01, FAIL, crítica).**
c3's pointcut is `PBEParameterSpec.new(byte[], int)` only (mop:42-43). For
`new PBEParameterSpec(salt, 500, paramSpec)` — a realizable, oracle-violating
construction (CONSTRAINTS `iterationCount >= 10000` applies to `Cons`, both
constructors) — c2's condition is false (`return false` before `handleEvent`,
artifact `:169-186` region) and **no other event matches**: no report, no monitor
state, nothing. And the miss cannot be recovered downstream: `PREPARED_PBE` has **no
reader in the whole set** (grep across `jca_android/*.mop`: only the write at
PBE mop:66; registered as deliberate writer-no-reader in
`data/gh101/predicate_omissions.csv` row `PREPARED_PBE` — the register is accurate,
GAMA-PBE-04 PASS). Total silence for a realizable violation ⇒ FN. I searched
`data/gh101/divergence_record.csv` for a record of this asymmetry (the register's PBE
row `49b892006688` covers only the c3 repair) and found none ⇒ unregistered
divergence (GAMA-PBE-05, FAIL, major).

**Message falsehood (GAMA-PBE-02, FAIL, major).** "expecting at least 1000 iterations"
misstates the enforced bound by 10×: a developer "fixing" to 2000 iterations still
violates and is still told 1000 suffices. Plus miscategorization (`UnsafeAlgorithm`)
and clause conflation (cannot tell CONSTRAINT from REQUIRES from the record; the
dataset's `unique_msg` would carry the wrong error_type family for cross-spec
category statistics). Cosmetic: file header comment says "GCMParameterSpec" (mop:11).

**History.** 0/0/0/0; token nowhere. The jca twin carried c3 as an all-fail-row event
during the campaign (`diff`: only the `ere` line differs, `jca:53` `ere : c1 | c2`),
so any historical c3 firing would have produced an `UnsafeAlgorithm` line **plus** a
spurious `InvalidSequenceOfMethodCalls` line. Zero of either across 8,147 executions
⇒ the event never fired or emission was lost (see GAMA-SET-11). Discriminating tests
named: JVM harness `new PBEParameterSpec(fixedSalt, 100)`; micro-APK woven ajc+dexlib2
with RVSEC-COV check at the site; campaign-era instrumented APK inspection.

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `Cons` (c1\|c2) | sites of both ctors | c1/c2 conformant, c3 violating (2-arg only) | one event per object; match or prefix-loop | c3 only | GAMA-SET-09: constructors invisible to static path; 3-arg violating zone fully silent |
| CONSTRAINTS `iterationCount>=10000` | constant sometimes extractable statically | folded into c1/c2/c3 conditions | condition — suppression, not transition | c3 message (wrong constant, wrong category) | 3-arg violation = silence (GAMA-PBE-01) |
| REQUIRES `randomized[salt]` | co-occurrence approximation only | `validate(RANDOMIZED, salt)` in all three conditions | writer: SecureRandomSpec / SecretKeySpec.mop e1 | conflated into c3's single message | writer suppressed upstream is indistinguishable from truly unrandomized salt |
| ENSURES `preparedPBE[this]` | n/a | `setProperty` mop:66 | @match | n/a | writer-no-reader — registered (predicate_omissions); miss is unrecoverable downstream |

jca twin **diverges** (ere only). Extractor output (class, "new", params) is identical
for both — the GAMA-SET-01 wrong-dir default is measured **vacuous** for this spec's
static target set; GAMA-SET-09 dominates.

### 2.4 IvParameterSpecSpec (IVP)

File `IvParameterSpec.mop`, sha256 `633237ac…` (= manifest); rule `833c3e23…`:
EVENTS cons1(iv), cons2(iv, offset, len), `Cons := cons1|cons2`, ORDER `Cons`,
REQUIRES `randomized[iv]`, ENSURES `preparedIV[this]` — **no CONSTRAINTS**.

**G9 handler audit.**

| Path | (a) | (b) | (c) | (d) | (e) | (f) | (g) |
|---|---|---|---|---|---|---|---|
| c3 body (mop:42-49), c4 body (mop:51-56) | `UnsatisfiedConstraint`, no clause ID — but the rule has exactly one REQUIRES, so cause is inferable from spec+category | spec name only | **3-arg `ErrorDescription` ⇒ `expecting="unknown"`** (`ErrorDescription.java:34-36`); artifact `IvParameterSpecRuntimeMonitor.java:221,238` | none | present | none | GAMA-SET-06 applies |
| `@fail` (mop:68-71) | dead (§1) | — | — | — | — | — | — |
| `@match` (mop:73-76) | writes PREPARED_IV + accepting | — | — | — | — | — | — |

**Repair verified (GAMA-IVP-01, PASS, PROVADO)** — same structure as PBE: c3/c4 in
the automaton (`{0,2,2}`), report before `handleEvent`, no spurious fail, no
displacement. Historical contrast: the jca twin had c3/c4 outside the `ere`
(all-fail rows) — the repair is real in the artifact.

**`unknown` on the only reporting path (GAMA-IVP-02, FAIL, major).** The G9 gate is
"no `unknown`"; IVP's sole violation channel emits `message=unknown` into the
dataset (`unique_msg` field 5). Sibling repairs (PBE/SKS) pass a message string; IVP
passes none — inconsistent diagnostic style within the same repair family.

**c2's extra bounds conjuncts (GAMA-IVP-03, INCONCLUSIVE; GAMA-IVP-04, FAIL, major).**
c2 requires `offset >= 0 && len >= 0 && iv.length >= offset + len` (mop:33-38) —
**absent from the rule** (no CONSTRAINTS). c4 negates only the RANDOMIZED conjunct
(mop:54), so the zone {iv randomized ∧ bounds bad} fires **neither** c2 nor c4:
silent suppression. Realizability hinges on whether the real constructor can return
normally with such bounds — the JDK reference implementation throws
(`NegativeArraySizeException` / `ArrayIndexOutOfBoundsException` /
`IllegalArgumentException`) for every such input, which would make the zone
unrealizable — but the on-device (ART/conscrypt) implementation was **not** executed
this round: INCONCLUSIVE with named pendency G10-IVP-1 (JVM harness over the real
implementation; D-piloto-2 style). The divergence itself (added conjuncts) is
unregistered: I searched `data/gh101/divergence_record.csv` and found only the
layer-2 row `f4fe01f5b82c` for this file ⇒ GAMA-IVP-04 (unclassified divergence,
major by pre_registro §4).

**History.** 0/0/0/0; token nowhere — despite `IvParameterSpec` being among the most
common crypto classes in Android apps and the jca twin's c3/c4 being report-capable
(with spurious extra line) throughout the campaign. Strong contributor to
GAMA-SET-11. Also note: `CipherSpec`'s 10,923 historical lines contain **zero**
occurrences of the string "IvParameterSpec" — the current jca_android
`reportUnpreparedParams` message ("requires an IvParameterSpec established by a
monitored sequence", CipherSpec.mop:85-87) did not exist in the campaign vocabulary;
no historical continuity is available for the PREPARED_IV reader either.

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `Cons` | ctor sites | c1..c4 partition (2-arg complete; 3-arg gapped per above) | one event/object | c3/c4 (`unknown` message) | GAMA-SET-09; suppression zone third state |
| REQUIRES `randomized[iv]` | co-occurrence approx. | read in all four conditions | writers: SecureRandomSpec:106-133, SecretKeySpec.mop:26 | `UnsatisfiedConstraint` + unknown | upstream-suppressed writer indistinguishable from real violation |
| ENSURES `preparedIV[this]` | n/a | `setProperty` mop:74 | @match | n/a | reader CipherSpec.mop:83-87 (CBC family) — miss displaced to Cipher site with correct requirement text but no root cause |

jca twin diverges (ere only); extractor target set identical ⇒ GAMA-SET-01 vacuous
here; GAMA-SET-09 dominates.

### 2.5 SecretKeySpecSpec (SKS)

Sha256 `d1cc088a…` (= manifest); rule `ee7edaf9…`: EVENTS c1(keyMaterial, alg),
c2(keyMaterial, off, len, alg), `Cons := c1|c2`, ORDER `Cons`, CONSTRAINTS
`length(keyMaterial) >= off + len`, REQUIRES `preparedKeyMaterial[keyMaterial]`
(carried as `Property.RANDOMIZED` surrogate — `data/gh101/predicate_edges.csv`,
"present-surrogate"), ENSURES `speccedKey[this,_]` and `generatedKey[this, alg]`.

**G9 handler audit.**

| Path | (a) | (b) | (c) | (d) | (e) | (f) | (g) |
|---|---|---|---|---|---|---|---|
| c3 body (mop:41-50) | `UnsatisfiedConstraint`; conflates membership-list and RANDOMIZED clauses; text garbled: "keyMaterial.length is not randomized" | spec name only | message present but imprecise | none | present | none | GAMA-SET-06 |
| c4 body (mop:51-57) | `UnsatisfiedConstraint`; conflates membership and length clauses; **never mentions randomization** (see GAMA-SKS-01) | idem | idem | none | present | none | idem |
| `@fail` (mop:66-69) | dead (§1) | — | — | — | — | — | — |
| `@match` (mop:79-83) | writes accepting + GENERATED_KEY + SPECCED_KEY | — | — | — | — | — | — |

**REQUIRES unenforced on the 4-arg overload (GAMA-SKS-01, FAIL, crítica).**
c2's condition is `algorithms.contains(alg.toUpperCase()) && keyMaterial.length >=
offset + len` — **no `validate(RANDOMIZED, keyMaterial)`** (mop:37; artifact
`SecretKeySpecSpecRuntimeMonitor.java:203`); c4 is c2's exact complement (mop:54,
artifact `:237`), so it also never tests randomization. The rule's REQUIRES
`preparedKeyMaterial[keyMaterial]` binds `keyMaterial`, present in **both**
constructors. Consequence: `new SecretKeySpec(hardcodedBytes, 0, 16, "AES")` — the
canonical hardcoded-key misuse, trivially realizable — fires c2, transitions to
match, and the `@match` handler grants `setObjectAsInAcceptingState` +
`GENERATED_KEY` + `SPECCED_KEY` (artifact `:260-266`). The false grant then
**satisfies downstream REQUIRES readers**: `CipherSpec.mop:156,177,198` and
`MacSpec.mop:75,94` validate `GENERATED_KEY`. Double damage: the violation itself is
never reported (FN), and the object launders a hardcoded key into the predicate
store, converting downstream true positives into silence (cascaded FN). The same
misuse through the 2-arg ctor **is** caught (c3). The gh101 registers record the
surrogate as "present" with reads only at mop:29,46 (c1/c3 —
`predicate_inventory_jca_android.csv`) and record no per-overload caveat; I searched
`divergence_record.csv` (rows `85e775e32049`, `f0ffa75b48bc`, `644c9b978750`),
`frozen_set_debt.md` and `README.md` for the c2 asymmetry and found nothing.
Classification INCORRETA; artifact mechanism PROVADO, downstream chain read from
production specs (PROVADO as code, end-to-end INFERIDO without execution).

**Message quality (GAMA-SKS-02, FAIL, minor).** c3's text is semantically garbled
("keyMaterial.length is not randomized"); both violating branches conflate two
distinct clauses into one category+message, so a record cannot be attributed to
CONSTRAINT vs REQUIRES without re-deriving the inputs. Attributable to spec+site
(mitigating), hence minor rather than major.

**Spec text malformed, parser fail-open (GAMA-SKS-03, FAIL, minor; SET-family).**
`SecretKeySpecSpec.mop:27-30` closes `condition(...)` at line 29 and then has a stray
`)` at line 30 before `{`. JavaMOP accepted the file silently (round generation: exit
0, empty stderr — `generation_manifest.md`), and the `.rvm` (line 13) shows the
intended condition preserved. No semantic damage **in this instance**, but the parser
tolerates unbalanced input without a warning — same fail-open family as the pilot's
GCM undefined-`c2`-in-`ere` (pilot `gama_diagnostico.md` §2): FEN-SET-PARSER-FAILOPEN.

**Repair + registers verified (GAMA-SKS-04, GAMA-SKS-05, PASS).** Layer-2 repair
effective in the artifact (c3/c4 `{0,2,2}`, report stands alone). SPECCED_KEY
writer-no-reader deliberately registered (`predicate_omissions.csv` row
`SPECCED_KEY`; `divergence_record.csv` row `644c9b978750`) and consistent with the
artifact. Counter-evidence duly sought on my own suspicion of register staleness:
`predicate_edges.csv` "missing" verdicts are the **declared pre-repair baseline**
(`data/gh101/README.md:17-18` — "whether the set implemented it before the repairs…
kept as authored"), not an inconsistency; suspicion withdrawn.

**History.** 0/0/0/0; token "SecretKeySpec" in no field of 97,018 lines. This is the
single most surprising historical zero of the batch: `SecretKeySpec` construction is
ubiquitous; hardcoded/derived key material without monitored `SecureRandom` lineage is
the common case; the jca twin's c3/c4 were report-capable (all-fail row ⇒ each firing
would have yielded **two** lines) during the whole campaign; Cipher was exercised in
21 APKs and Mac in 7. Either (i) app call sites were never woven/matched, (ii)
emission was lost (GH100 families), (iii) monitored constructors were never executed
in 8,147 executions, or (iv) campaign spec-set differed at generation. The current
merged jca aspect **does** contain these advices (`jca/MultiSpec_1MonitorAspect.aj:622-647`
— generated 2026-08-08, anomaly 1 of the manifest, so it evidences the present, not
the campaign). Discriminating tests (named, not executed — G10): JVM harness on the
batch-A monitors with unrandomized inputs; single-misuse micro-APK woven by ajc AND
dexlib2 with RVSEC-COV inspection at the constructor site; retrieval of a
campaign-era instrumented APK from ase-journal artifacts and DEX inspection of the
constructor call sites. Claim GAMA-SET-11 (INCONCLUSIVE).

**Synergy.**

| Rule/clause | Possible static fact | Binding/predicate | Dynamic event/state | Diagnosis | Third state / limitation |
|---|---|---|---|---|---|
| ORDER `Cons` | ctor sites | c1..c4 partition complete (both arities) | one event/object | c3/c4 | GAMA-SET-09 |
| CONSTRAINTS `length(keyMaterial) >= off+len` | rarely constant statically | c2/c4 test it (4-arg only — matches rule scope: off/len exist only there) | suppression/report | c4 message (conflated) | — |
| REQUIRES `preparedKeyMaterial[keyMaterial]` (RANDOMIZED surrogate) | not expressible statically | **c1/c3 only; absent from c2/c4** | 4-arg violating grant → match | none on 4-arg path | **GAMA-SKS-01: FN + predicate laundering** |
| ENSURES `generatedKey[this,alg]` / `speccedKey[this,_]` | n/a | @match writes both | readers: CipherSpec:156,177,198; MacSpec:75,94 / none (registered) | n/a | false grant propagates through GENERATED_KEY readers |

jca twin diverges (ere + SPECCED_KEY write); extractor target set identical ⇒
GAMA-SET-01 vacuous here; GAMA-SET-09 dominates.

## 3. New set-level findings (scored separately per D-piloto-4)

**GAMA-SET-08 — stale `Category_*` flags re-execute `@match` after a suppressed
sibling monitorCall (FAIL, minor).** Mechanism and witnesses in §1. Generator-wide;
benign in batch A (idempotent handler bodies) but it is an unjustified handler
double-execution and a latent hazard for any future non-idempotent `@match`.
FEN-SET-STALE-FLAGS (pilot lateral finding, previously unclaimed).

**GAMA-SET-09 — the static-analysis path is structurally blind to constructor
events (FAIL, major).** Two independent angles, one executable (protocol §3.3):
(1) Code: constructor patterns carry member name `"new"` in the JavaMOP AST
(`javamop/src/main/java/javamop/parser/ast/visitor/DumpVisitor.java:600`);
`UsedJcaMethodsVisitor.java:70-78` copies it into `MopMethod`; the GATOR client
matches Soot scene methods by `(className, methodName)` with
`t.getMethodName().equals(name)` (`rvsec-gator/client/.../target/TargetResolver.java:53`)
where Soot constructors are named `<init>`; the bytecode-scan complement keys on the
same names (`RvsecAnalysisClient.java`, `buildTargetKeys` /
`findDirectTargetCallersByBytecodeScan`). I searched the whole client main tree for a
`"new"`→`"<init>"` normalization and found none; the client test tree contains no
constructor case (searched for `<init>` and `"new"`).
(2) Executed: `java -jar rvsec-mop-extractor/target/mop-extractor.jar -d
<scratch>/specs_copy -o extractor_methods_batchA.csv -t METHODS_PARAMS` over a
scratch copy of the five specs → 8 rows, **all** with method name `new`
(`gama_extractor_output.txt`). Since every event of every batch-A spec is a
constructor, **zero clauses of these five specs are mappable by the production
static path** — mop-reachability, `mopActivities` and `cov_mop` can never include
them. This holds regardless of GAMA-SET-01 (and I measured GAMA-SET-01 vacuous for
batch A: the jca twins differ only in `ere`/`@match`, so extractor output is
identical). Asymmetry note: the **dynamic** dexlib2 weaver handles constructor calls
correctly (`DexWeaver.java:763-777`; `DexWeaverConstructorAdviceTest` uses
IvParameterSpec and SecretKeySpec as canonical cases) — the blindness is
static-only. §13 unlock condition ("100% das cláusulas mapeadas") is unreachable for
batch A until fixed.

**GAMA-SET-10 — ErrorCollector newline-escape exposure for batch A: none (PASS).**
The declared pending case of GAMA-CIP-07 was whether any serialized string carries
app-controlled content for these specs. Inspection of every reachable
`ErrorDescription` in the five artifacts: all `expecting` arguments are compile-time
literals (or absent ⇒ "unknown"); `keyAlgorithm`/`salt`/`iv`/`keyMaterial` are bound
but never serialized. The only residual app-influenced content is `__LOC` itself
(file:line from `StackTraceElement`; a hostile SourceFile string is a theoretical
vector — INFERIDO, noted as residual threat, not exercised). GAMA-CIP-07 remains
open for CipherSpec only.

**GAMA-SET-11 — historical zero-emission of ubiquitous param-spec constructors
(INCONCLUSIVE).** §2.5 History. Units: 0 lines / 0 unique_msg / 0 APKs / 0 sites for
all five specs, and 0 token occurrences dataset-wide (97,018 lines, 8,147 executions,
113 APKs). The zero cannot be read as conformance and is *a priori* implausible as
universal conformance for SKS/IVP; decomposition per pilot H1 with the three
discriminating tests named in §2.5. Any causal attribution is deferred to replay
(protocol §12).

## 4. Pilot-hypothesis check (H1–H7 where they touch batch A)

- **H1 (zero-rows decomposition)**: all five batch-A specs are in the 13-spec
  zero-row set. Refined per spec: DHG/HMC zeros are consistent with rarity/absence
  (still not conformance); PBE/IVP/SKS zeros are the anomaly formalized as
  GAMA-SET-11. H1 stands, sharpened.
- **H2 (spurious pairing, specific+InvalidSeq)**: not testable on batch A specs
  directly (zero rows). Corroborated in a batch-A **reader** spec:
  KeyPairGeneratorSpec history pairs `InvalidKeySize` with `InvalidSequence` at the
  same site (`systems.sieber.droid_scep.ScepClient:::CertReq` 5+5 lines;
  `io.treehouses.remote...BaseSSHKeyGen:::generateKey` 4+2) — MEDIDO, same D-S9
  family the repair targets. Post-repair prediction: the derived set decouples these
  pairs (future replay test).
- **H3/H5/H6**: do not touch batch-A classes — not evaluated (out of scope).
- **H4 ("but found .")**: batch-A specs emit no "but found" template — not touched.
- **H7 (process-lifecycle-dependent counts)**: vacuous at zero rows; retained as a
  design constraint for any future batch-A measurement.

## 5. Threats to validity of this report

1. **No dynamic execution**: every "realizable" claim (DHG-01 FP, PBE-01 FN, SKS-01
   FN) is proven at the artifact/code level and inferred end-to-end; G10 pendencies
   name the harness for each. INCONCLUSIVE was used where realizability itself is in
   doubt (IVP-03).
2. **Oracle bias (recorded)**: api30 rules model availability, not recommendation;
   DHG-01 inverts under the 1.5.2 anchor (there the .mop condition is the rule's own
   constraint). The verdicts here are relative to the frozen api30 oracle by
   pre-registration; the anchor tension is recorded, not resolved.
3. **Historical data are pre-repair and pre-GH100**: used only to generate
   hypotheses; every count reported in its own unit; no line was attributed to a
   cause.
4. **Single-generation artifacts**: the round's artifacts were generated once;
   generator determinism was verified in the pilot (REF-11 caveat: determinism, not
   independent replication).
5. **My extractor run** used a scratch copy of the specs — byte-equality with the
   tree is guaranteed by the copy operation and the manifest hashes, but the run
   exercises the extractor jar built in-tree (`mop-extractor.jar`, Main-Class
   `br.unb.cic.mop.extractor.Main`), not the exact GATOR client invocation path;
   the client code path was verified by reading `MopSpecsTargetSource.java:28-48`
   which delegates to the same `JavamopFacade.listUsedMethods`.

## 6. Scientific log (question → hypothesis → test → evidence → result → uncertainty → next decision)

| # | Question | Hypothesis | Discriminating test | Evidence | Result | Uncertainty | Next decision |
|---|---|---|---|---|---|---|---|
| 1 | Is `@fail` reachable in any batch-A artifact? | No — single-constructor alphabet | read effective transition tables + indexing | §1 tables; dispatch code | unreachable in all 5 (PROVADO) | none material | close; no __RESET cascade possible |
| 2 | Does the layer-2 repair hold in the artifacts? | Yes | body-order + transition + flags in generated code | §1; PBE/IVP/SKS event methods | holds (PROVADO) | none material | PASS claims filed |
| 3 | Do violating branches cover both constructors? | No for PBE (3-arg) and partially for SKS (RANDOMIZED) | condition complement analysis on artifacts | §2.3, §2.5 | PBE gap + SKS REQUIRES drop (PROVADO in artifact) | end-to-end unexecuted | criticals filed; harness pendency G10 |
| 4 | Is DHG's condition in the api30 rule? | No | read rule; trace suppression + reader | §2.1 | oracle-conformant traces suppressed; KPG FP displaced | FP not executed | critical filed; harness pendency |
| 5 | Is HMC's class in android-30? | Absent | `unzip -l` frozen jar | §2.2 | absent (MEDIDO) | app-bundled copies possible | major filed; oracle bias recorded |
| 6 | What does history say about these 5? | zeros | freeze-checked stratification, 4 units + token scan | §0, outputs | 0 everywhere (MEDIDO) | pre-repair data | GAMA-SET-11 INCONCLUSIVE + 3 named tests |
| 7 | Can the static path see these specs? | No — "new" vs `<init>` | code chain + executed extractor run | §3 SET-09 | blind (PROVADO+MEDIDO) | none material | SET-09 major; G12 blocked for batch A |
| 8 | Any app-controlled content reaching the logger? | None for batch A | inspect every reachable ErrorDescription arg | §3 SET-10 | literals only | SourceFile residual | SET-10 PASS; CIP-07 stays open for Cipher |

## 7. Commands (reproduction)

```
sha256sum $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/{DHGenParameterSpecSpec,HMACParameterSpecSpec,PBEParameterSpecSpec,IvParameterSpec,SecretKeySpecSpec}.mop
cmp .../jca/DHGenParameterSpecSpec.mop .../jca_android/DHGenParameterSpecSpec.mop   # identical
diff .../jca/SecretKeySpecSpec.mop .../jca_android/SecretKeySpecSpec.mop            # ere + @match only
sha256sum $ANDROID_HOME/platforms/android-30/android.jar                            # 96ccfdc8...
unzip -l $ANDROID_HOME/platforms/android-30/android.jar | grep -c "javax/xml/crypto"  # 0
sha256sum .../ase-journal/dataset/results/errors.csv                                # 78023def...
uv run python batchA/gama_batcha_errors.py                                          # freeze-check + stratification
java -jar $RVSEC_HOME/rvsec/rvsec-mop-extractor/target/mop-extractor.jar \
     -d <scratch>/specs_copy -o extractor_methods_batchA.csv -t METHODS_PARAMS      # all rows name=new
```
