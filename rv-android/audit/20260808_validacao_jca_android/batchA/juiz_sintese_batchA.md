# JUDGE — Batch A synthesis (DHG, HMC, PBE, IVP, SKS)

Judge (LLM-as-a-Judge), round "batch A" of the `jca_android` audit · 2026-08-09.
Role: evidence synthesis — **not** a formal oracle, **not** majority vote. A
reproducible counterexample cannot be dismissed by consensus; a reading-only claim
cannot close a toolchain claim; `INCONCLUSIVE` never becomes approval. Weights and
denominators: pre-published in `fase0/pre_registro.md` §6, applied under the
D-piloto-4 rules (`fase0/desvios.md`): dimension fixed at claim creation, SET claims
scored separately, per-phenomenon counts reported beside per-claim scores.

Inputs: `batchA/generation_manifest.md` (common round input, 20 artifacts,
hash-verified by me), the three agent reports and CSVs (`alfa_*` 34 claims,
`beta_*` 39, `gama_*` 23 — 96 total), the frozen specs/rules, and the production
sources. Claim-by-claim resolution: `batchA/juiz_claims_resolvidos_batchA.csv`
(original columns preserved; `resolucao_juiz`, `classificacao_final`,
`severidade_final`, `justificativa_curta` appended). Mechanical re-sum:
`batchA/juiz_rescore_batchA.py` (§4 tables are its verbatim output).

**Register carried for the record** (researcher decision 2026-08-09, recorded in
`fase0/manifesto.md`): `RandomStringPassword.mop` is **excluded** from the round —
it has no CrySL rule, hence no normative oracle. The global judgment will carry
this exclusion; the audited round is therefore 22 specs (2 pilot + 20 in batches).

Scope of this round's verdicts: gates G2, G3, G4, G5, G7, G9. **G6, G8 and G10
were not executed** (device phase later) — they can only ADD defects, never remove
demonstrated ones. G0/G1 were closed in fase 0; G11–G13 are fed by, not closed by,
this round.

## 0. Evidence the judge verified or executed himself

Facts measured by me this session (commands reproducible; agent files untouched;
all my work under scratch `batchA/juiz/`, never over the spec tree):

1. **Freeze**: `sha256sum` over the 5 `.mop`, 5 `.cryptsl` and 20 round artifacts —
   all equal to `generation_manifest.md` / `fase0/manifest_hashes.md` (30/30).
2. **Sources read end-to-end**: all five `.mop` and all five api30 `.cryptsl`.
   Confirmed directly: DHG `condition(exponentSize < primeSize)` (`.mop:24`) with
   **no** CONSTRAINTS section in the rule; HMC spec parameter `hmacParameterSpec`
   (`:17`) never bound (event binds `s`, `:21`); PBE c3 declared on the 2-arg ctor
   only (`:42-43`), message "at least **1000**" (`:50`) vs guard `>= 10000` (`:46`),
   c3 uses `ErrorType.UnsafeAlgorithm` (`:49`), header javadoc says
   "GCMParameterSpec" (`:11`); IVP c2 extra bounds conjuncts (`:35-37`), c4 negates
   only RANDOMIZED (`:54`), c3/c4 use the **3-arg** `ErrorDescription` (`:48`,`:55`);
   SKS stray `)` (`:30`), c2/c4 with **no** `validate(RANDOMIZED, …)` (`:37`,`:54`),
   unary `GENERATED_KEY`/`SPECCED_KEY` writes (`:81-82`). SKS rule's only
   CONSTRAINT is the length clause (`SecretKeySpec.cryptsl:29`); ENSURES
   `generatedKey[this, alg]` (`:41`).
3. **Artifacts**: transition tables extracted by me from the five
   `*RuntimeMonitor.java` — conforming events `{1,2,2}`, violating `{0,2,2}`,
   exactly as all three agents reported. Indexing verified per spec:
   DHG/PBE/IVP/SKS use a per-object `MapOfMonitor` keyed on the returned object;
   **HMC uses one static `Tuple2` — a global, per-process monitor**
   (`HMACParameterSpecSpecRuntimeMonitor.java:212, 236-243`). Suppression prologue
   (`return false` **before** `handleEvent`) verified (e.g. DHG `:110-118`).
   Merged advice order conforming→violating and the stale-flag dispatch (event
   boolean discarded, `Category_*` flags re-tested) verified
   (`SecretKeySpecSpecMonitorAspect.aj:39-53`, monitor `:413-419`). PBE's 3-arg
   advice calls **only** `c2Event` (aspect, verified). IVP c3/c4 emit the 3-arg
   `ErrorDescription` in the artifact (`:222`, `:239`).
4. **Runtime sources** (project rule: cite file:line before accepting a mechanism):
   `ErrorDescription.java:34-36` (3-arg ctor delegates with `"unknown"`);
   `ExecutionContext.java:102-120` (binary `setProperty(Property, Object)` —
   no slot for an algorithm; identity-keyed store, `:43-53`);
   `KeyPairGeneratorSpec.mop` init3/init4 bodies read `PREPARED_DH` and accuse with
   the "monitored DHGenParameterSpec sequence" message (`:91-113`);
   `rv_android_core/util/utils.py:41-52` (non-empty stderr raises
   `CommandException` unless `skip_stderr` — production compensation for exit-0
   fail-open, pilot precedent).
5. **Platform**: `unzip -l android-30/android.jar | grep -c "javax/xml/crypto"` = 0;
   jar sha256 `96ccfdc8…` = frozen manifest.
6. **gh101 registers**: `conformance_record.csv:5` (DHG reason describes an
   implication the api30 rule does not contain) and `:21` (SKS whitelist declared
   hand translation); `predicate_edges.csv:18,21-23,46,57-58,64-68` including
   `present-surrogate` with no overload caveat (`:66`) and `generatedKey`
   `present`/`this` with no second-slot note (`:68`); `predicate_omissions.csv`
   rows PREPARED_PBE and SPECCED_KEY; `divergence_record.csv` — **no** row for
   DHGenParameterSpecSpec.mop, PBE row covers only the c3 repair, SKS rows cover
   speccedKey and layer-2 only; `README.md:17-18` — `predicate_edges.csv` is
   declared as the **pre-repair baseline** "kept as authored" (decisive for the
   BETA-SET-07 × GAMA-SKS-05 conflict); `frozen_set_debt.md` has 0 hits for
   exponentSize/javax.xml.crypto/3-arg.
7. **GAMA-SET-09 decisive evidence** (single-route, verified before acceptance):
   `javamop/.../DumpVisitor.java:599-609` prints member name `new` for constructor
   patterns; `rvsec-gator/client/.../TargetResolver.java:53` matches by
   `t.getMethodName().equals(name)` where Soot names constructors `<init>`;
   grep over the whole client main tree finds **no** `new`→`<init>` normalization
   (only unrelated `SpinnerItemExtractor.java:136`); Gama's executed extractor run
   (`gama_extractor_output.txt`): 8/8 target rows with method name `new`.
8. **History**: independent `grep -c` of the five class tokens over the frozen
   `errors.csv` (sha `78023def…` re-verified) = 0, triangulating Gama's four-unit
   zeros.
9. **J1 — standard judge test (executed)**: `juiz/juiz_walk.py` parses the
   transition tables from the round artifacts and walks them: every conforming
   event reaches state 1 (match) in one step; every violating event loops at 0
   with no category; **fail (state 2) is unreachable with a single event per
   monitor** in all five tables; under HMC's verified global indexing, the walk
   `[c(h1), c(h2)]` of two CrySL-legal constructions reaches fail — the separating
   trace. ALL PASS (output `juiz/` scratch).
10. **J2 — discriminating test, DHG severity conflict (executed, 3 identical
    reps)**: generated `KeyPairGeneratorSpec` in my scratch (frozen toolchain),
    compiled it with the round DHG monitor against the production runtime jars
    (`rvsec-core.jar 7b4d72aa…`, `rvsec-logger-csv 6787f411…`, `rv-monitor-rt
    0fa65fbc…`), drove the wrappers with real JDK objects:
    control `(1024,512)` → `PREPARED_DH=true`, 0 errors; **FP case `(1024,1024)`
    (legal under the raw api30 oracle) → suppressed, `PREPARED_DH=false`,
    `KeyPairGenerator.getInstance("DH")` + `initialize` events →
    `errors=1 [UnsatisfiedConstraint spec=KeyPairGeneratorSpec expecting=
    "initialize() for DH requires an AlgorithmParameterSpec established by a
    monitored DHGenParameterSpec sequence."]`**. The end-to-end false positive
    with displaced, factually false attribution is now EXECUTED, not inferred
    (`juiz/JuizDrive.java`, `juiz/juiz_drive_out.txt`).
11. **J3 — independent re-execution of Beta's HMC counterexample (3 identical
    reps)**: round-input HMC monitor, two distinct CrySL-legal
    `HMACParameterSpec` constructions → `errors=1 [InvalidSequenceOfMethodCalls
    spec=HMACParameterSpecSpec expecting=unknown]`, `h1 PREPARED_HMAC=true`,
    `h2 PREPARED_HMAC=false` (`juiz/JuizHmc.java`, `juiz/juiz_hmc_out.txt`).

Epistemic labels used: **fato medido** (my execution this session), **observado em
artefato** (cited file:line), **inferido**, **histórico** (pre-repair errors.csv —
hypothesis generator only).

## 1. Conflict / convergence matrix

| # | Phenomenon / Claims | Alfa | Beta | Gama | Conflicting evidence | Discriminating test | Resolution | Residual uncertainty |
|---|---|---|---|---|---|---|---|---|
| 1 | **DHG extra-oracle condition** → silent suppression + displaced downstream accusation — ALFA-DHG-02/03/05, BETA-DHG-05, GAMA-DHG-01 (+ registers ALFA-DHG-06, GAMA-DHG-02) | FAIL critical | FAIL **major** (final link read, not executed) | FAIL critical (G10 pendency named) | Severity only: is the FP "demonstrable in a realizable trace"? | **J2 executed by the judge** (§0.10): full chain FP, 3 reps | FAIL — INCORRETA, **critical** (pre-registro §4); Beta's hedge closed; unregistered (verified) | DH KeyPairGenerator availability on a real API-30 device (G10); CrySL 1.5.2 anchor tension recorded as oracle bias |
| 2 | **PBE 3-arg ctor with no violating carrier** — terminal FN — ALFA-PBE-03, BETA-PBE-04, GAMA-PBE-01, GAMA-PBE-05 | FAIL critical | FAIL critical (executed PBE-c) | FAIL critical | None on substance; **dimension assignment differs** (Gama: captura; Alfa/Beta: bindings) | Beta's executed drive + judge's aspect verification (§0.3) | FAIL — INCORRETA/OMITIDA, critical; unregistered (verified). Dimension pendency recorded per D-piloto-4 item 1 — not re-assigned | Corpus frequency of the 3-arg ctor (does not change the structural FN) |
| 3 | **SKS 4-arg REQUIRES drop + whitelist + generatedKey 2nd slot** — ALFA-SKS-02/03/04/05, BETA-SKS-05/07, GAMA-SKS-01 | FAIL critical ×4 | FAIL critical ×2 (executed SKS-b/c) | FAIL critical | None — three routes converge | Beta's executed drives; judge verified `.mop`/`.rvm`/artifact and `ExecutionContext` unary store (§0.2-0.4) | FAIL — 4 distinct defects: whitelist INCORRETA (registered ≠ approved), surrogate INCORRETA (producers differ), 4-arg drop INCORRETA (unregistered), 2nd slot OMITIDA (unregistered; `FEN-SET-generatedkey-2a-casa`, = pilot ALFA-CIP-07 writer side) | Downstream Cipher/Mac chain read, not driven (readers verified in source) |
| 4 | **HMC platform absence** — ALFA-HMC-02, ALFA-SET-03, BETA-HMC-02, GAMA-HMC-01 | FAIL LIMITAÇÃO major | FAIL INCORRETA major | FAIL INCORRETA major | Classification label at different units | `unzip -l` re-executed by judge (§0.5) | FAIL at every unit: spec-level = LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (translation faithful; vacuity inherited); oracle/measurement claims = INCORRETA (derived-profile defect). Oracle bias **registered**, per pre_registro §1 — and it does **not** excuse phenomenon 5 | App-bundled copies (JSR-105) keep the spec reachable off-platform |
| 5 | **HMC global monitor (unbound spec parameter)** — BETA-HMC-03, BETA-SET-02 × ALFA-HMC-01/05 (PASS), GAMA-HMC-02 (PASS), ALFA-SET-04 (PASS) | PASS (premise: per-object indexing) | **FAIL critical (executed)** | PASS (same premise as Alfa) | **Real conflict**: Alfa and Gama assumed per-object indexing from the spec shape; Beta proved a global monitor | **J3 re-executed by the judge** (§0.11) + Tuple2 verified in artifact (§0.3) | Beta prevails — reproducible counterexample. **Four claims overturned**: ALFA-HMC-01 → FAIL (separating trace at the effective automaton, D-piloto-3), ALFA-HMC-05 → FAIL (lifecycle per process), GAMA-HMC-02 → FAIL (@fail NOT dead; fires spurious `InvalidSequenceOfMethodCalls` with `expecting=unknown` on a legal trace), ALFA-SET-04 → FAIL (set property refuted; holds only for the 4 parameterized specs). BETA-HMC-04 stays PASS (scoped table-vs-ere, pilot BETA-CIP-09 precedent) | ajc behavior on the unresolvable type (named pendency, G6) |
| 6 | **IVP extra bounds conjuncts** — ALFA-IVP-02 (PASS), BETA-IVP-04 (PASS), GAMA-IVP-03 (INCONCLUSIVE), GAMA-IVP-04 (register) | PASS equiv (harness) | PASS equiv (harness incl. overflow) | INCONCLUSIVE (not run vs ART) | Whether two JDK executions suffice | Two independent executed harnesses (T1a-d; IVP-e) answer the exact question the INCONCLUSIVE hinged on | GAMA-IVP-03 → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA), ART threat named and kept; GAMA-IVP-04 stays FAIL major (unregistered divergence — REF-05 precedent) | ART/libcore not executed (G10); threat named, both agents at 0.8 |
| 7 | **IVP `expecting=unknown` on its only reporting path** — GAMA-IVP-02 (unique route) | — | (noted §3, "Gama's lane") | FAIL major | None | Judge verified `.mop:48/55` + `ErrorDescription.java:34-36` + artifact `:222/:239` (§0.2-0.4) | FAIL — INCORRETA major; **decisive for IVP's G9** (pre-registered criterion "nenhum unknown") | None structural |
| 8 | **@fail dead channel** — BETA-DHG-04/PBE-05/IVP-05/SKS-06 (FAIL major) × GAMA-DHG-03 (PASS vacuous) × ALFA-SET-04 (claimed as positive) | positive property | FAIL major ×4 | PASS (vacuously conform) | Same fact, three labels | J1 walk (fail needs a 2nd event per monitor) + oracle reading | FAIL — INCORRETA **minor** (adjusted from major): unlike the pilot's GCM, PBE/IVP/SKS have live carrier channels and DHG's rule admits no violating trace; dead handler = hygiene. GAMA-DHG-03 stays PASS (its statement — no `unknown` emittable from DHG — is true and was verified) | None (HMC exception handled in phenomenon 5) |
| 9 | **Stale category flags re-execute `@match`** — ALFA-SET-01 (major), BETA-SET-06 (major, exercised live), GAMA-SET-08 (minor) | FAIL major | FAIL major | FAIL minor | Severity | Beta's executed stale-rewrite proof (PBE-a-stale, SKS-a-stale) + judge's dispatch verification | FAIL — INCORRETA **major** as set-wide generator pattern (pilot precedent "major como padrão"), benign in batch A (idempotent handlers); GAMA-SET-08 harmonized up | Non-idempotent handler exposure in later batches |
| 10 | **Parser fail-open family** — ALFA-SET-02 (major), BETA-SET-05 (minor), GAMA-SKS-03 (minor), BETA-SKS-04 (PASS instance), BETA-SET-04 (símbolo), BETA-SET-03 (exit 0 + error) | major | minor/major | minor | Severity per claim unit | Probes p1-p4 (Beta, executed) + judge's paren/`.rvm` verification + `utils.py:41-52` compensation check | Pattern claims (ALFA-SET-02, BETA-SET-04, BETA-SET-05) → **major** (pilot: "minor here, major as pattern"); instance claims (BETA-SKS-04 PASS, GAMA-SKS-03 minor) unchanged; **BETA-SET-03 → minor** (production compensates — verified; pilot BETA-SET-04 precedent), residual `skip_stderr` callers named | Systematic sweep of `skip_stderr` call sites pending |
| 11 | **gh101 registers stale?** — BETA-SET-07 (FAIL) × GAMA-SKS-05 (PASS) | — | FAIL minor | PASS (suspicion withdrawn) | Direct contradiction | Judge read `README.md:17-18`: `predicate_edges.csv` is the **declared pre-repair baseline** "kept as authored"; the alleged contradictions are that declared semantics | BETA-SET-07 → **PASS** (register coherent); residual friction (semantics live in README) noted, not a defect | Other registers rows not exhaustively audited |
| 12 | **Static path blind to constructors** — GAMA-SET-09 (single route) | — | — | FAIL major (PROVADO+MEDIDO) | Single route — protocol requires judge verification | Judge verified `DumpVisitor.java:599-609`, `TargetResolver.java:53`, no-normalization grep, and the executed extractor output (§0.7) | FAIL — INCORRETA major; G12 unreachable for batch A (all 8 targets are `new`); dynamic dexlib2 path unaffected (`DexWeaver.java:763-777`) | Full GATOR invocation not re-run (code path read; extractor executed) |
| 13 | **Layer-2 repair holds** — GAMA-PBE-03, GAMA-IVP-01, GAMA-SKS-04 (+ Beta walks) | (structure §0) | PASS walks | PASS ×3 | None | J1 walk + body-order verification | PASS — repair real in the effective artifacts: specific report stands alone, no spurious fail, no displacement | Weave/device (G6/G10) |
| 14 | **Historical zero-emission** — GAMA-SET-11 | — | — | INCONCLUSIVE | None | Judge re-grep (0 tokens, frozen hash) | INCONCLUSIVE — outside denominator; three discriminating tests named for the execution phase | Open until replay |
| 15 | **Capture matrices** — BETA-DHG-02/PBE-02/IVP-02/SKS-02, BETA-SET-08 | (INFERIDO side notes) | PASS MEDIDO (production matcher, extracted members) | — | None | Beta's triangulation incl. same-simple-name trap under production imports | PASS — G5 material for DHG/PBE/IVP/SKS; container android-36 pendency stays open (REF-12) | Real weave (G6) |

## 2. Detailed resolutions — what changed and why

### 2.1 Overturned positions (all by executed evidence, none by vote)

| Claim | From → To | Why |
|---|---|---|
| ALFA-HMC-01 | PASS → **FAIL** (INCORRETA, critical) | D-piloto-3 requires the language verdict over the **effective automaton**, which includes its indexing. The artifact's indexing is a static Tuple2 (verified §0.3); J3 (§0.11) exhibits the separating trace: two CrySL-legal constructions → `InvalidSequenceOfMethodCalls`. `L(CrySL) ⊆ α(L(MOP))` fails. Alfa's premise "every per-instance trace has length 1" (report §0) is false for HMC — the only batch-A spec whose parameter no event binds. |
| ALFA-HMC-05 | PASS → **FAIL** (INCORRETA, critical) | The claim asserts per-object indexing "same structure as DHG". Factually wrong (Tuple2, §0.3); lifecycle is per process. Reproducible counterexample cannot be dismissed. |
| ALFA-SET-04 | PASS → **FAIL** (INCORRETA, critical) | "No batch-A spec can emit a spurious InvalidSequenceOfMethodCalls" is refuted by J3 for HMC. True for the 4 parameterized specs (J1); false as the filed 5-spec set property. |
| GAMA-HMC-02 | PASS → **FAIL** (INCORRETA, major) | Premise "@fail dead, indexed by returned object" false for HMC; the fired record carries `expecting=unknown` — the exact G9 criterion — on a legal trace. Phenomenon criticality carried by BETA-HMC-03. |
| BETA-SET-07 | FAIL → **PASS** | `README.md:17-18` declares `predicate_edges.csv` a pre-repair baseline "kept as authored" (verified §0.6). The cited "contradictions" (edges:67 `missing` vs frozen write; edges:46 vs MacSpec read) are exactly that baseline semantics — the jca twins indeed lacked those sites. Same route by which Gama withdrew its own suspicion (GAMA-SKS-05). |
| GAMA-IVP-03 | INCONCLUSIVE → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) | The realizability question ("can the ctor return normally with bad bounds?") was answered by two executed harnesses inside the round (Alfa T1a-d; Beta IVP-e incl. overflow): every such construction throws. ART threat named and kept — same status and confidence as ALFA-IVP-02. |

### 2.2 Severity adjustments (justified; severity does not enter the score)

| Claim(s) | From → To | Justification |
|---|---|---|
| BETA-DHG-05 | major → **critical** | Beta's only hedge (final link unexecuted) closed by J2 (§0.10). Pre-registro §4: FP demonstrable in a realizable trace. |
| BETA-DHG-04, BETA-PBE-05, BETA-IVP-05, BETA-SKS-06 | major → **minor** | Dead `@fail` loses nothing the oracle demands here: no per-object ORDER violation exists (single-constructor alphabet), and PBE/IVP/SKS report real violations through live carrier bodies. Distinguished from the pilot's GCM major, where suppressed real violations had no live channel. |
| GAMA-SET-08 | minor → **major** | Harmonized to the phenomenon: pilot precedent "major como padrão set-wide", now exercised live on every valid construction (Beta). Benign in batch A stays on record. |
| BETA-SET-05 | minor → **major** | Same phenomenon and unit (set-wide pattern) as ALFA-SET-02; pilot GAMA-GCM-01 phrasing "minor in the instance, major as the pattern" — the SET claims are the pattern claims. |
| BETA-SET-03 | major → **minor** | Production pipeline compensates: non-empty stderr raises `CommandException` (`utils.py:41-52`, verified §0.4; pilot BETA-SET-04 precedent). Residual: `skip_stderr` call sites unaudited — named. |

### 2.3 Single-route claims and how they were closed

GAMA-SET-09 (static constructor blindness): closed by the judge's own verification
of both angles — code chain and the executed extractor run (§0.7). ALFA-SKS-05
(generatedKey second slot): closed by the judge's verification of the unary store
(`ExecutionContext.java:102-120`), the unary write (`.mop:81`), the pair-blind
readers (`CipherSpec.mop:156/177/198`, `MacSpec.mop:75/94` — read), and the absent
register (edges:68 verified). ALFA-SKS-03 (surrogate non-equivalence): oracle
producers (`SecretKey.cryptsl:25`, `Key.cryptsl:23`) vs RANDOMIZED producers
diverge — verified in the rules; the direction of the oracle bias (flagging good
practice) is **recorded, not corrected** (pre_registro §1). GAMA-IVP-02
(`unknown`): verified end-to-end by me (§0.2-0.4).

### 2.4 Dimension-assignment pendency (D-piloto-4 item 1)

GAMA-PBE-01 was created under `captura_eventos`; Alfa/Beta filed the same
phenomenon under `bindings_clausulas`. Not re-assigned; recorded as a pendency.
Effect: PBE's captura subscore carries one FAIL that its siblings carry in
bindings. The per-phenomenon count (§3) is the corrective lens.

## 3. Consolidated classification

**Critical phenomena (7), 18 critical claims:**

| FEN | Specs | Claims | State |
|---|---|---|---|
| FEN-DHG-SUPRESSAO | DHG | ALFA-DHG-02/03, BETA-DHG-05, GAMA-DHG-01 | INCORRETA — executed FP chain (J2); unregistered |
| FEN-HMC-MONITOR-GLOBAL | HMC | BETA-HMC-03; overturned ALFA-HMC-01/05, ALFA-SET-04 | INCORRETA — executed FP (J3); generator accepts silently (BETA-SET-02, major) |
| FEN-PBE-C2-GAP | PBE | ALFA-PBE-03, BETA-PBE-04, GAMA-PBE-01 | INCORRETA/OMITIDA — executed terminal FN; unregistered |
| FEN-SKS-WHITELIST | SKS | ALFA-SKS-02, BETA-SKS-07 | INCORRETA — executed FP; registered ≠ approved |
| FEN-SKS-SURROGATE | SKS | ALFA-SKS-03 | INCORRETA — producers differ from oracle; no equivalence proof, no scope reduction |
| FEN-SKS-REQUIRES-4ARG | SKS | ALFA-SKS-04, BETA-SKS-05, GAMA-SKS-01 | INCORRETA — executed FN + predicate laundering; unregistered |
| FEN-SET-GENERATEDKEY-2A-CASA | SKS (set-tied) | ALFA-SKS-05 | OMITIDA — unregistered; joins pilot ALFA-CIP-07 |

**Major (non-critical) phenomena**: FEN-HMC-CLASSE-AUSENTE (4 claims — oracle-bias
register; spec-level LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA); FEN-DHG/PBE/IVP register
gaps (GAMA-DHG-02, GAMA-PBE-05, GAMA-IVP-04 — OMITIDA); FEN-PBE-MSG (4 claims);
FEN-IVP-UNKNOWN (GAMA-IVP-02 — G9-decisive); FEN-SET-FLAGS-OBSOLETAS (3);
FEN-SET-FAILOPEN-PARSER / -SIMBOLO (pattern claims); FEN-SET-CTOR-INVISIVEL-ESTATICA
(GAMA-SET-09); GAMA-HMC-02 (spurious `unknown`-bearing accusation).

**DIVERGÊNCIA_EQUIVALENTE_COMPROVADA**: Kleene-prefix carrier structure (ALFA-PBE-01,
ALFA-IVP-01, ALFA-SKS-01 — registered layer-2 repair, held in artifact); IVP bounds
conjuncts (ALFA-IVP-02, BETA-IVP-04, GAMA-IVP-03 — proven by two harnesses).

**LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA**: PREPARED_PBE and SPECCED_KEY write-no-read
(registered; still block any total-adherence claim, modelo_semantico §7);
HMC platform vacuity at spec level.

**INCONCLUSIVE (2, outside every denominator, named pendencies)**: BETA-SET-09
(weave/device, G6/G10), GAMA-SET-11 (historical zero — replay tests named).

**Resolution totals**: 96 claims → 46 PASS, 48 FAIL, 2 INCONCLUSIVE.
Position changes: 4 PASS→FAIL, 1 FAIL→PASS, 1 INCONCLUSIVE→PASS (§2.1).
No counterexample was dismissed; no resolution used agent counting.

## 4. Descriptive scores (weights pre-registered; verbatim from `juiz_rescore_batchA.py`)

Per-spec scores over that spec's resolved claims only; SET claims scored
separately (D-piloto-4). Denominator = PASS+FAIL; INCONCLUSIVE outside.

| Spec | ling(20) | capt(20) | bind(15) | pred(15) | tool(15) | diag(10) | repr(5) | Raw / attainable | Normalized |
|---|---|---|---|---|---|---|---|---|---|
| DHG | 20.00 (2/2) | 20.00 (1/1) | 0.00 (0/2) | 5.00 (1/3) | 15.00 (1/1) | 3.33 (1/3) | 0.00 (0/2) | **63.33 / 100** | 63.33% |
| HMC | 10.00 (1/2) | 0.00 (0/2) | 7.50 (1/2) | 7.50 (1/2) | 7.50 (1/2) | 0.00 (0/1) | (no claims) | **32.50 / 95** | 34.21% |
| PBE | 20.00 (2/2) | 10.00 (1/2) | 5.00 (1/3) | 15.00 (3/3) | 15.00 (1/1) | 1.67 (1/6) | 2.50 (1/2) | **69.17 / 100** | 69.17% |
| IVP | 20.00 (2/2) | 20.00 (2/2) | 15.00 (2/2) | 15.00 (2/2) | 15.00 (2/2) | 3.33 (1/3) | 0.00 (0/1) | **88.33 / 100** | 88.33% |
| SKS | 20.00 (2/2) | 20.00 (1/1) | 3.00 (1/5) | 7.50 (3/6) | 10.00 (2/3) | 3.33 (1/3) | 5.00 (1/1) | **68.83 / 100** | 68.83% |

**SET score** (separate; INCOMPLETE — 2 INCONCLUSIVE outside):
captura 20.00 (1/1), toolchain 0.00 (0/10, +1 INC), diagnóstico 5.00 (1/2),
reprodutibilidade 5.00 (2/2, +1 INC) → **30.00 / 50 attainable = 60.00%**.

**Batch-A aggregate** (context only; 79 spec claims, SET excluded, 0 INCONCLUSIVE):
ling 18.00 (9/10), capt 12.50 (5/8), bind 5.36 (5/14), pred 9.38 (10/16),
tool 11.67 (7/9), diag 2.50 (4/16), repr 1.67 (2/6) → **61.07 / 100**.

**Mandatory labels**: descriptive score ≠ probability of correction ≠ verdict;
never rounded to 100; a score never opens a gate. The per-spec scores of DHG/PBE/
IVP/SKS are complete in-denominator (0 INCONCLUSIVE among their claims); the SET
score is INCOMPLETE. Two context readings: (i) IVP at 88.33 is still REPROVADA —
one G9 criterion (`unknown`) fails on its only reporting path: compensation across
dimensions is prohibited; (ii) claim counts overstate convergent phenomena
(e.g. FEN-SKS-REQUIRES-4ARG appears as 3 claims) — use §3's phenomenon counts.

## 5. Per-spec verdicts (covered scope: G2, G3, G4, G5, G7, G9)

Pilot standard applied: any critical INCORRETA/OMITIDA inside a gate ⇒ gate FAIL ⇒
spec REPROVADA in the covered scope. G6/G8/G10 (weaving end-to-end, differential/
mutation tests, Android execution) were NOT executed and can only add defects.

### DHGenParameterSpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured (0.42+0.88 s, ≤87 MB); 1 event; coenable saturated (BETA-DHG-01) |
| G3 | PASS | dual inclusion over the effective per-object automaton (ALFA-DHG-01, BETA-DHG-03; judge walk J1) |
| G4 | **FAIL** | extra-oracle `condition(exponentSize<primeSize)`: oracle-legal constructions silently suppressed — INCORRETA critical, unregistered (ALFA-DHG-02, BETA-DHG-05) |
| G5 | PASS | exact partition on android-30, neighbors free (BETA-DHG-02) |
| G7 | **FAIL** | ENSURES `preparedDH` denied on the suppressed path → executed downstream FP at KeyPairGeneratorSpec (J2) — critical (ALFA-DHG-03, GAMA-DHG-01) |
| G9 | **FAIL** | displaced, factually false accusation at the reader; no own channel for the suppressed case (ALFA-DHG-05); dead `@fail` (minor) |

### HMACParameterSpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured (BETA-HMC-01) |
| G3 | **FAIL** | separating trace at the effective automaton: two legal constructions → violation (ALFA-HMC-01 overturned; J3) — critical |
| G4 | **FAIL** | spec parameter never bound → global monitor; per-process lifecycle vs per-`this` rule — critical, executed (BETA-HMC-03) |
| G5 | **FAIL*** | Esperado(platform)=∅ — the api30 rule models a class android-30 does not publish (ALFA-HMC-02/BETA-HMC-02). *Oracle-inherited: the pointcut itself is exact for an app-bundled owner; recorded as oracle bias, not translation defect |
| G7 | **FAIL** | lifecycle/parametric equivalence broken (ALFA-HMC-05 overturned); PREPARED_HMAC denied to every object but the first per process |
| G9 | **FAIL** | spurious `InvalidSequenceOfMethodCalls` with `expecting=unknown` on a legal trace (GAMA-HMC-02 overturned; J3) |

The platform absence does **not** excuse the global-monitor defect: it is realizable
wherever the class exists (JVM harness proved it; app-bundled JSR-105 on Android).
Both defects predate gh101 (HMC is byte-identical to the frozen `jca` copy).

### PBEParameterSpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured; 3 events; coenable saturated (BETA-PBE-01) |
| G3 | PASS | `c3*(c1|c2)` dual inclusion modulo α; registered repair held in artifact (ALFA-PBE-01, BETA-PBE-03, GAMA-PBE-03) |
| G4 | **FAIL** | 3-arg constructor has no violating carrier: realizable oracle misuse is totally silent, terminal FN (executed), unregistered — critical (FEN-PBE-C2-GAP) |
| G5 | PASS | member-level capture exact, both ctors, neighbors free (BETA-PBE-02); GAMA-PBE-01's capture-dimension assignment recorded as pendency — the phenomenon is judged in G4 |
| G7 | PASS | RANDOMIZED read correct on the 2-arg path; PREPARED_PBE write-no-read registered (LIMITAÇÃO — blocks total adherence, not this gate) |
| G9 | **FAIL** | violation message off by 10× ("1000" vs 10000), miscategorized (`UnsafeAlgorithm`), CONSTRAINT/REQUIRES conflated (GAMA-PBE-02 major; ALFA-PBE-04/05, BETA-PBE-07) |

### IvParameterSpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured; 4 events; coenable saturated (BETA-IVP-01) |
| G3 | PASS | `(c3|c4)*(c1|c2)` dual inclusion modulo α; repair held (ALFA-IVP-01, BETA-IVP-03, GAMA-IVP-01) |
| G4 | PASS | extra bounds conjuncts proven vacuous at the after-returning join point by two executed harnesses (ALFA-IVP-02, BETA-IVP-04, GAMA-IVP-03 resolved); register gap is a reprodutibilidade finding (GAMA-IVP-04, major) |
| G5 | PASS | exact partition, overloads exhaustive, neighbors free (BETA-IVP-02) |
| G7 | PASS | RANDOMIZED read in all four guards on the right object; PREPARED_IV writer/reader edges correct (ALFA-IVP-03) |
| G9 | **FAIL** | the spec's only violation channel (c3/c4) writes `expecting=unknown` (3-arg `ErrorDescription`) — pre-registered criterion "nenhum `unknown`" (GAMA-IVP-02, major; verified by the judge) |

IVP is the batch's cleanest spec (88.33) and fails exactly one gate, on a
mechanical, low-risk repair (pass a message string as c3/c4 already do in
PBE/SKS). The verdict is criterion-driven: no compensation across dimensions.

### SecretKeySpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured; 4 events; coenable saturated (BETA-SKS-01) |
| G3 | PASS | `(c3|c4)*(c1|c2)` dual inclusion modulo α; repair held (ALFA-SKS-01, BETA-SKS-03, GAMA-SKS-04) |
| G4 | **FAIL** | extra-oracle algorithm whitelist: executed FP against the raw oracle; registered ≠ approved, no scope reduction on file — critical (ALFA-SKS-02, BETA-SKS-07) |
| G5 | PASS | exact partition incl. the same-simple-name trap under production imports (BETA-SKS-02) |
| G7 | **FAIL** | three criticals: RANDOMIZED surrogate non-equivalent to `preparedKeyMaterial` (ALFA-SKS-03); REQUIRES dropped on the whole 4-arg path — executed FN + predicate laundering, unregistered (FEN-SKS-REQUIRES-4ARG); `generatedKey` second slot OMITIDA, store unary, readers pair-blind (ALFA-SKS-05) |
| G9 | **FAIL** | clause attribution impossible from the record: c3/c4 conflate membership/RANDOMIZED/length into one category+message, c3 text garbled (GAMA-SKS-02, minor; criterion "atribuição ambígua" met; c4 also names a dead trigger) |

**Batch verdict line**: 5/5 REPROVADA in the covered scope. No spec reaches the
uncovered gates with a clean slate; per protocol §16, the set cannot move toward
`READY` from this batch.

## 6. Protocol observations for the next batches (no gate changes)

1. **Publish the indexing tree with the effective automaton.** The round's common
   input carried transition tables but not parametrization; Alfa and Gama both
   assumed per-object indexing from the spec shape and were wrong for HMC. The
   generation manifest should state, per spec, the indexing structure
   (`MapOfMonitor<param>` vs static global) — it is one grep in the artifact —
   and D-piloto-3 should be read as "effective automaton **including indexing**".
2. **Standing two-object test.** J3's shape (two legal instances, same process)
   is cheap, needs no emulator, and is the dimension-5 witness the refutation
   round demanded of the pilot. Adopt per spec, harness-standard.
3. **Unbound-spec-parameter lint.** BETA-SET-02's defect class (parameter bound by
   no event ⇒ silent global monitor) is grep-detectable in seconds over the other
   17 specs before their batches open; the same goes for 3-arg
   `ErrorDescription` calls in violating carriers (IVP's G9 defect class).
4. **Pre-agree the dead-`@fail` classification** (INCORRETA minor hygiene when a
   live carrier channel exists or the rule admits no ORDER violation) — three
   agents produced three labels for the same fact; this round's resolution (§1
   row 8) can be adopted as precedent.
5. **Register-reading brief.** `predicate_edges.csv` baseline semantics
   (README:17-18) cost one wrong claim (BETA-SET-07) and one withdrawn suspicion
   (Gama). Put the one-paragraph semantics in the batch briefing.
6. **Downstream-reader chains.** J2's pattern (generate the reader spec in judge
   scratch, drive writer-suppression → reader accusation with production jars)
   generalizes to every REQUIRES edge; batches with predicate-graph criticals
   should ship this harness instead of leaving the last link INFERIDO.
7. **Dimension assignment**: one pendency (GAMA-PBE-01) — keep recording, do not
   re-assign; phenomenon IDs did their job this round.

## 7. Files

- This synthesis: `batchA/juiz_sintese_batchA.md`.
- Claim-by-claim resolution: `batchA/juiz_claims_resolvidos_batchA.csv`
  (96 claims; comma-containing fields quoted; mechanically re-summable).
- Re-sum script: `batchA/juiz_rescore_batchA.py` (§4 is its verbatim output).
- Judge scratch (ephemeral, commands recorded in §0): `<scratchpad>/batchA/juiz/`
  — `juiz_walk.py` (J1), `JuizDrive.java` + `juiz_drive_out.txt` (J2, 3 reps),
  `JuizHmc.java` + `juiz_hmc_out.txt` (J3, 3 reps), `gen_kpg/` (KeyPairGeneratorSpec
  generation), `build_csv.py` (CSV builder).
- Agent primary files consulted: all `batchA/alfa_*`, `beta_*`, `gama_*`;
  `generation_manifest.md`; frozen specs/rules; `data/gh101/*`; production sources
  cited at file:line throughout.

*Next step per protocol §15: adversarial refutation round against this synthesis;
the judge's decision becomes final only after answering each objection.*

## 8. Final decision after the refutation round

2026-08-09. Issued after responding to each of the 9 objections of the
independent reviewer (`refutacao_parecer_batchA.md`), as protocol §15 requires —
responses in `juiz_respostas_refutacao_batchA.md` (outcomes: 9 accepted, two of
them partially/on-rhetoric; full rev. 1 → rev. 2 change table there). Sections
1–7 above are the first synthesis (rev. 1) and remain as record; **where wording
or numbers diverge, this section prevails** — the basis is rev. 2 of
`juiz_claims_resolvidos_batchA.csv`. The reviewer independently re-executed
J1/J2/J3 and the re-sum, and reported no objection reaching verdicts or raw
scores; the adjudication below is nonetheless mine, objection by objection.

### 8.1 Final per-spec verdicts and gates

**Operative gate rule (corrects the rev. 1 §5 preamble — REF-B-05)**: a gate
fails when its pre-registered criteria (`pre_registro.md` §3, protocol §16) are
met; a critical INCORRETA/OMITIDA inside the gate is one *sufficient* trigger
among them, not the only one. Three gates below fail on non-critical claims,
by criterion: IVP G9 (major), PBE G9 (major), SKS G9 (major after REF-B-03).

| Spec | G2 | G3 | G4 | G5 | G7 | G9 | Verdict (covered scope) |
|---|---|---|---|---|---|---|---|
| DHGenParameterSpecSpec | PASS | PASS | FAIL | PASS | FAIL | FAIL | **REPROVADA** |
| HMACParameterSpecSpec | PASS | FAIL | FAIL | **PASS (vacuous)** ¹ | FAIL | FAIL | **REPROVADA** |
| PBEParameterSpecSpec | PASS | PASS | FAIL | PASS | PASS | FAIL | **REPROVADA** |
| IvParameterSpecSpec | PASS | PASS | PASS | PASS | PASS | FAIL | **REPROVADA** |
| SecretKeySpecSpec | PASS | PASS | FAIL | PASS | FAIL | FAIL | **REPROVADA** |

¹ Rev. 2 change (REF-B-04): `Esperado(platform)=∅` satisfies the capture
criterion vacuously; the vacuity is an **oracle-inherited** anomaly carried by
the oracle-bias register (phenomenon 4; ALFA-SET-03, ALFA-HMC-02, BETA-HMC-02,
GAMA-HMC-01 — claim resolutions unchanged), not a spec-side gate failure. HMC's
verdict rests on G3/G4/G7/G9, all failed on executed evidence (J3).

Grounds per gate are those of §5, unchanged except HMC G5. Scope statement:
**G6 (weaving end-to-end), G8 (differential/mutation) and G10 (Android
execution) were not executed this round** — they can only ADD defects, never
remove the demonstrated ones; the five verdicts hold in the covered scope
G2/G3/G4/G5/G7/G9. `INCONCLUSIVE` never became approval: the two inconclusive
claims stay open as named pendencies (§8.4).

### 8.2 Corrections of record absorbed from the refutation

- Convergence columns in §1 counted agents, not evidence routes (REF-B-07,
  pilot REF-11 lesson): in matrix rows 2 and 3, the load-bearing routes are
  Beta's executed drives plus the judge's source/artifact verification; Alfa's
  and Gama's readings of the same frozen bytes are one route. No resolution
  cited convergence as grounds; resolutions unchanged.
- Dead-`@fail` severity, BETA-SET-03 lowering, and BETA-SET-07 overturn were
  attacked and survived (reviewer §2), the last with the reviewer's own
  verification of `README.md:17-18` and of the generator call sites
  (`runtime_verification_generator.py:217,272` without `skip_stderr`) — which
  *strengthens* the BETA-SET-03 minor grounding beyond rev. 1.

### 8.3 Final scores (rev. 2 CSV; verbatim from `juiz_rescore_batchA.py` re-run)

No resolution changed in rev. 2, so every raw number equals rev. 1. **Primary
presentation is the pre-registered one (raw weighted sums)**; the
attainable-weight percentage of rev. 1 is demoted to a *derived reading* pending
the PROPOSED deviation D-batchA-1 (REF-B-02, §8.5).

| Unit | Raw weighted sum | Notes |
|---|---|---|
| DHG | **63.33** | all 7 dimensions carry claims; 0 INCONCLUSIVE |
| HMC | **32.50** | reprodutibilidade carries no claims — 5 weight points unattainable this round (derived reading, unregistered: 32.50/95 = 34.21%) |
| PBE | **69.17** | all 7 dimensions; 0 INCONCLUSIVE |
| IVP | **88.33** | all 7 dimensions; 0 INCONCLUSIVE |
| SKS | **68.83** | all 7 dimensions; 0 INCONCLUSIVE |
| SET (separate, D-piloto-4) | **30.00** | 50 weight points unattainable (no ling/bind/pred SET claims); derived reading 30.00/50 = 60.00%; **INCOMPLETE** — 2 INCONCLUSIVE outside the denominator |
| Batch-A aggregate (context) | **61.07** | 79 spec claims, SET excluded, 0 INCONCLUSIVE |

Claim totals: 96 = 46 PASS + 48 FAIL + 2 INCONCLUSIVE; 18 critical claims
across the 7 critical phenomena of §3 (FEN counts unchanged; GAMA-SKS-02's rise
to major adds no critical). **Mandatory labels**: these scores are descriptive;
the SET score is INCOMPLETE; score ≠ probability of correction ≠ verdict; never
rounded to 100; no score opens a gate; IVP at 88.33 is REPROVADA — compensation
across dimensions is prohibited.

### 8.4 Open pendencies (named)

- **BETA-SET-09** (INCONCLUSIVE): ajc/dexlib2 weave + device observational
  equivalence; `__LOC` under DEX; ajc on HMC's unresolvable type — G6/G10 phase.
- **GAMA-SET-11** (INCONCLUSIVE): historical zero-emission of the five specs;
  three discriminating tests named in `gama_report.md` §2.5 for the replay phase.
- **G10 harness pendencies**: G10-IVP-1 (ART/libcore bounds behavior — the
  equivalence states carry "provado em JVM, ART pendente G10" per REF-B-06);
  DHG→KPG chain on device (JVM-proven by J2).
- **Researcher countersignature** of the two audit-created registers: the HMC
  oracle-bias register (REF-B-08 — "documentada NESTA RODADA") and the
  RandomStringPassword exclusion already recorded in `fase0/manifesto.md`.
- **`skip_stderr` call-site sweep** (residual of BETA-SET-03's minor grounding).
- **Container android-36 triangulation** (REF-12, carried from the pilot).
- **G13**: the must-close set from this round = all critical claims (18) and all
  major findings, now including GAMA-SKS-02 (REF-B-03).

### 8.5 PROPOSED deviation text (for the researcher/orchestrator; NOT registered by the judge)

> **D-batchA-1 (PROPOSED — score presentation for units with empty dimensions)**:
> "When a scored unit (spec or SET) has no resolved claims in some dimension,
> the score of record is the raw weighted sum over the pre-registered weights,
> with the unattainable weight explicitly stated. A percentage normalized over
> the attainable weight MAY be published only as a labeled derived reading.
> Adopted from batch B onward; batch A's rev. 2 already follows it
> retroactively (REF-B-02). Origin: refutation round of batch A."

### 8.6 Decision

**Batch A is closed** with **DHGenParameterSpecSpec, HMACParameterSpecSpec,
PBEParameterSpecSpec, IvParameterSpecSpec and SecretKeySpecSpec all REPROVADA
in the covered scope (G2, G3, G4, G5, G7, G9)** — five specs, seven critical
phenomena, every gate-deciding defect anchored in executed evidence (J1/J2/J3,
agent harnesses) or judge-verified source, independently re-executed by the
refutation reviewer. Per protocol §16 the set cannot move toward `READY` from
this batch; per pre_registro §7 no divergence was silently accepted — the two
audit-created registers await researcher countersignature. Process changes
carried to the next batches: §6 items 1–7 plus the REF-B-07 route-counting rule
and the REF-B-09 dimension-5 coverage declaration.

Files of record for the round: `juiz_sintese_batchA.md` (this document, §8
prevailing), `juiz_claims_resolvidos_batchA.csv` (rev. 2),
`juiz_rescore_batchA.py`, `juiz_respostas_refutacao_batchA.md`, and the 12
`juiz_*` evidence files listed with hashes in the responses document
(REF-B-01 remediation).
