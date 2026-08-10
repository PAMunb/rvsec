# GLOBAL JUDGMENT — adversarial audit of the `jca_android` JavaMOP specification set

Global judge · 2026-08-09 · audit root `audit/20260808_validacao_jca_android/`
(all relative pointers are to this root; spec pointers to the frozen tree
`rvsec/rvsec-mop/src/main/resources/jca_android/`; rule pointers to
`MetaCrySL/generated/api30/`). Protocol: `docs/20260808_validar_specs_jca_android.md`
§§15–17, §19 items 6–7. Pre-registered decision rules: `fase0/pre_registro.md`
(§3 criteria, §4 severities, §6 score, §7 READY conjunction). Deviations in
force and applied, none re-litigated: D-piloto-1..4, D-batchA-1, D-batchB-1,
D-batchC-1, D-batchD-1 (`fase0/desvios.md`).

Role boundary: this judgment synthesizes evidence; it is not a formal oracle
and does not decide by majority. INCONCLUSIVE never becomes approval; no score
opens a gate; READY is a conjunction, not an average. Files produced (only
`juizglobal_*`, in `global/`): this report, `juizglobal_set_claims_resolvidos.csv`,
`juizglobal_gates.csv`, `juizglobal_build.py` + `juizglobal_build_output.txt`,
`juizglobal_hashes.txt`.

---

## 0. What the global judge verified himself (commands and results)

Everything below was executed this session, from the frozen inputs, in the
judge's own scratch (`…/scratchpad/global/juiz/`; nothing written to the spec
tree, `fase0/`, or any prior-round/set file). Labels: **[re-executed]** = run
by me with outputs hash-compared to the record; **[source-verified]** = code
read at the cited file:line this session; **[recomputed]** = arithmetic
re-derived from the record CSVs.

1. **Freeze re-check** [re-executed]: `sha256sum *.mop` over the 23
   working-tree specs — **23/23 match `fase0/manifest_hashes.md`**, 0
   mismatches. Toolchain re-hashed (javamop, rv-monitor, rv-monitor-rt,
   rvsec-core, rvsec-logger-csv, aspectjrt, instr-cli, android-30
   `96ccfdc8…`, android-37.0 `bf1b4387…`) — all match `set/set_exec_hashes.txt`.
   Merged artifacts re-hashed: `MultiSpec_1MonitorAspect.aj 310fae06…`,
   `.json e91570ce…`, `RuntimeMonitor.java d6228eac…` — equal to the set-phase
   and batch-D records (three sessions, one byte state).
2. **Composition drive** [re-executed]: `SetExecCompositionDrive` over the
   compiled MERGED monitors, 3 reps from clean working dirs — all three
   **byte-identical to the published `set/set_exec_drive_rep1.out`**
   (sha256 `8168d2a7…`). This independently re-establishes, on the merged
   monitor: the KPG **NPE-to-caller** on `init1Event`/`initErrorEvent` as
   first events (S5); the **RANDOMIZED object/material split end to end**
   (S1: `RANDOMIZED[r2]=false` for the rejected instance, `RANDOMIZED[km2]=true`
   for its material, and the production reader `SecretKeySpecSpec` accepting
   `km2` with 0 errors — the executed FN); the **KPR 1-FP-per-access toll**
   with mark delivery (S3b/S3c); **SIGNED starvation with zero errors** (S3d);
   **VERIFIED on the boxed Boolean** (S3e); the **KMF→SSL fail-then-proceed
   cascade** (S4b/S4d); and the working positive-control edges (S1b, S2a/b,
   S3a, S4a, S4c).
3. **Dedupe probe** [re-executed]: `SetExecDedupeProbe`, 3 reps —
   byte-identical to `set/set_exec_dedupe_rep1.out` (sha256 `3a658775…`). X1:
   the SSL RANDOMIZED extra-oracle read fires alone. X2: with the key-managers
   AND SecureRandom constraints both violated at ONE call site, **exactly one
   record survives** — a detected violation is never emitted.
   [source-verified]: identity = `ErrorSummary` (spec, type, class, method,
   loc) at `rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java:108-139`
   — the hashCode javadoc itself declares `expecting` outside the identity and
   arrival-order survival; `rvsec-logger-csv/...​/ErrorCollector.java:40-44`
   (`errors.add(err)` guard) and the logcat collector
   (`rvsec-android/rvsec-logger-logcat/...​/ErrorCollector.java:36-42`) share
   the same identity. Judge's note: the code comment claims the collapse only
   merges "the same violation differing in expected value" — X1/X2 prove the
   loss class is **wider**: two semantically distinct constraint violations
   (missing key managers vs unmonitored SecureRandom) collapse because both
   are `UnsatisfiedConstraint/SSLContextSpec` at one site.
4. **KGN merge-masking** [re-executed]: `javac` of the per-spec
   `KeyGeneratorSpecRuntimeMonitor.java` against the frozen classpath —
   **exit 1, `cannot find symbol: class Key` at :259**; the frozen
   `KeyGeneratorSpec.mop` import block (lines 3–10) lacks `java.security.Key`;
   the MERGED monitor compiles (exit 0) because the import union places
   `import java.security.Key;` at its line 11 (contributed by
   CipherSpec/KeyStoreSpec). Fail-open confirmed: both generators exit 0 for
   an uncompilable artifact.
5. **Weave probe both jars** [re-executed]: `SetExecWeaveProbe` (production
   dexlib2 pipeline from the frozen `instr-cli.jar`) over the MERGED
   descriptor and the 168-scenario union, 2 reps per jar — byte-identical to
   the executor's outputs (android-30 `14e84cca…`, android-37.0 `7da00861…`).
   Verified per-row: `cis_readB`, `cos_writeB`, `kpg_genkp`, `kst_getentry`,
   `kst_setentry`, `srd_nextint0`, `sig_sign0`, `sig_sign3`, `ssl_cse0`,
   `ssl_cse2` **UNTOUCHED on both jars**; `mac_df_out` WRAPPED on both;
   capture partition 50 UNTOUCHED / 73 WRAPPED / 45 INLINE identical across
   jars; WeaveReport identical; wrappers 83 vs 86 (the 3 extras are the
   `SecureRandomParameters` overloads, a genuine android-37.0 member — 1
   class entry by `unzip -l`, 0 in android-30); the only capture-section diff
   is the MDG `update_1`/`update_2` wrapper-name permutation.
6. **Consolidation re-run** [re-executed]: `set_cons_build.py` and
   `set_cons_hist.py` re-run in scratch (paths pinned; audit tree untouched)
   — `set_cons_ledger.csv`, `set_cons_fen_registry.csv`,
   `set_cons_predicate_graph.csv`, `set_cons_build_output.txt`,
   `set_cons_hist_output.txt` all **byte-identical to the record**, every
   in-script assert passing (558 = 210/322/26; per-round rev. 2 figures;
   11 reader-less constants; errors.csv sha `78023def…` gate).
7. **Ledger figures** [recomputed]: 174 critical FAIL claims (164 of record +
   10 pilot derived-parsed), of which 165 link to the 50 critical-carrying
   canonical phenomena — 9 pilot criticals carry no canonical FEN and remain
   pilot-local (pre-D-piloto-4 record; phrasing per REF-G-02); 8 D-batchC-1
   fail-open reconciliation rows counted at §4's letter in addition to the
   164 of-record (pilot BETA-SET-04, GAMA-GCM-01; batch A ALFA-SET-02,
   BETA-SET-03, BETA-SET-04, BETA-SET-05, GAMA-SKS-03; batch B BETA-SET-09);
   diagnostico pool 11 PASS / 73 FAIL / 7 INC; 26 INCONCLUSIVE.
8. **Gate counts from the five §8.1 tables** [recomputed]: G2 21/22 PASS
   (KGN FAIL); G3 16/22 FAIL (PASS: GCM, DHG, PBE, IVP, SKS, SKY — verifying
   the consolidator's count); G4 18/22 FAIL (PASS: IVP, KMF, TMF, SIG);
   G5 13/22 FAIL; G7 19/22 FAIL (PASS: PBE, IVP, MDG); G9 22/22 FAIL.
9. **Config code** [source-verified]: `rv_experiment/config.py:688-693`
   (`jca_android` explicit mapping, no silent fallback; errors raised
   :695-712) and `get_static_analysis_config` (:942-951) passing neither
   `mop_dir` nor `targets_file` nor `android_jar`;
   `rv_static_analysis/config.py:186` (probe list without "30") and :199-208
   (literal `jca` default) — EXEC-SET-27/28 confirmed on today's tree.
10. **RANDOMIZED reader classification** [source-verified]: see §1.2 below.

All asserts of `juizglobal_build.py` (A1–A5) pass; its verbatim output is
`juizglobal_build_output.txt`.

---

## 1. Adjudication of the 30 set-phase claims

`juizglobal_set_claims_resolvidos.csv` — the executor's 30 claims with the
judge's four resolution columns, builder-asserted. Summary: **30 = 22 FAIL /
8 PASS / 0 INCONCLUSIVE; severities 15 crítica / 6 major / 1 minor; 20
phenomena over the 22 FAILs** (per-phenomenon table in the build output).
The consolidator produced inputs, not claims; its corrections were treated as
evidence and adjudicated below. Every decisive dynamic evidence item was
re-executed by me (§0) before resolution; every executor position survived.

### 1.1 Resolutions that differ from, or sharpen, the filed record

- **EXEC-SET-23 (SSL RANDOMIZED extra-oracle read): major → crítica.**
  Grounds: the batch C ledger resolves FEN-SSL-RANDOMIZED-EXTRA at crítica;
  the set-phase instance is the same phenomenon executed on the merged
  monitor, and `pre_registro.md` §4's letter (FP demonstrable on a realizable
  trace — any `init` with an unmonitored SecureRandom, the common case)
  applies. The extra-oracle character (the api30 rule binds `_`) routes the
  *disposition* to the researcher (§7 item 4), not the severity.
  **Rev. 2 contingency annotation (REF-G-04)**: whether X1's executed error
  is an FP or an oracle-faithful positive depends on the researcher's §7
  item 4 ruling on how `randomized[sr]`-with-unbound-`sr` is to be read
  (api30 `SSLContext.cryptsl` — the refuter verified `sr` is bound by no
  event; `Init` binds `_`). The crítica of record inherits that contingency:
  a ruling that reads the clause as oracle-faithful revisits this severity.
  The claim is FAIL under either severity; no gate, verdict or score depends
  on it (severity does not enter the score).
- **EXEC-SET-07 (declared-only index), EXEC-SET-21 (VERIFIED wrong slot),
  EXEC-SET-24 (dedupe collapse): filed crítica UPHELD although the round
  families sat at major.** These are §4-letter applications at set level —
  FN on a realizable trace (dead `nextInt()`/`ints` capture), clause-level
  INCORRETA (the rule's `verified[sign]` predicate bound to the wrong
  object), and pre-registered "perda de emissão" (a detected violation never
  recorded), respectively. The closed rounds' records stand as those rounds'
  records; the set-level count follows the letter — the same pattern
  D-batchC-1 fixed for fail-open. The refutation round should attack these
  three placements first if it attacks anything in §1.
- **Phenomenon canonicalization**: EXEC-SET-05 `FEN-SET-firstcall-disjunct` →
  `FEN-SET-FIRSTCALL-DISJUNCT`; EXEC-SET-12 `FEN-SET-VARARGS` →
  `FEN-SET-VARARGS-ARGS-IGNORED` (registry canonical names). Two set-phase-new
  FENs accepted as filed: `FEN-SET-WRAPPER-NAME-ORDER` (minor),
  `FEN-SET-KMF-CASCADE` (major; the durable finding is the
  error+mark+acceptance co-occurrence, with the SunX509 JVM-default threat
  declared — Android's default is PKIX).

### 1.2 Explicit resolutions of the executor/consolidator divergences

**(a) "Five" vs "six" named ajc×dexlib2 divergence mechanisms.** Primary
evidence: batch D `juiz_sintese_batchD.md` §1#12 lists five (varargs g2; g4
arity; first-disjunct; declared-only; f3 dead-vs-broadcast) but omits
nested-type; §5's preamble enumerates **six items while calling them five**
(batch C: varargs, nested-type; batch D: f3, first-disjunct, declared-only,
plus SRD g4-arity). Resolution: the registry's canonical structure is
correct — **five canonical mechanism FAMILIES** (`FEN-SET-VARARGS-ARGS-IGNORED`
covering both the g2-varargs and g4-exact-arity instances,
`FEN-SET-NESTED-TYPE-DESCRIPTOR`, `FEN-SET-FIRSTCALL-DISJUNCT`,
`FEN-SET-DECLARED-ONLY`, `FEN-MAC-F3-UNBOUND`), which count as **six named
mechanism instances** when g2 and g4 are separated (they diverge in opposite
directions on the same spec, which is why batch D listed them apart). Both
published "five" groupings are incomplete or mislabeled enumerations of the
same measured facts; the discrepancy is presentational — **no gate outcome
depends on the count**, because G5 fails on the mechanisms themselves, each
re-verified in the production weave this session (§0.5). The return-type-dead
mechanisms (SIG `sign`, SSL `createSSLEngine`) are deliberately outside this
list: they are dead on BOTH halves, hence capture defects but not
half-divergences.

**(b) RANDOMIZED reader classification (consolidator's correction of batch D
§6.1).** Source-verified this session: `CipherSpec.mop` `reportUnrandomized`
(validates RANDOMIZED on `ranGen`, a `SecureRandom`), `KeyGeneratorSpec.mop`
`reportUnrandomized` (on `random`, a `SecureRandom`), `SSLContextSpec.mop`
init body (on `random`, a `SecureRandom`) are **object-level readers**;
`IvParameterSpec.mop:25` (on `iv`, a `byte[]`) and its family are
material-level; the sound object-level writer is `SecureRandomSpec.mop:196-198`
(`@match1`, constraint-coupled); `SecretKeySpec.mop:24-27` writes RANDOMIZED
on `key` (material), gated by GENERATED_KEY at :25. **The consolidator's
correction is CORRECT and the batch D §6.1 shorthand (grouping KGN/SSL/Cipher
under "material") was wrong.** The behavioral consequence was re-executed
(§0.2): object side sound (rejected instance denied), material side
overgranted (rejected instance's bytes accepted by a production reader).

### 1.3 What the 8 PASS claims establish (and do not)

EXEC-SET-01..04 and 11 establish that generation, merge packaging,
determinism and descriptor integrity are **not** the failure locus: `-merge`
is an exact union that changes packaging only, so every per-spec defect
adjudicated by the five rounds survives verbatim into the artifacts
production consumes — this is what makes the per-spec verdicts binding at set
level. EXEC-SET-27/29/30 are scoped controls (monitor-path selection; the ~5
working graph edges; evidence admissibility). None of these PASSes is
evidence of fidelity of any spec; they close the escape route "the set build
might differ from what was audited".

---

## 2. Gate matrix G0–G13 (protocol §16)

Machine-readable copy: `juizglobal_gates.csv`. Grounds below are the
consolidated record; every claim ID cited exists in the ledger or the
set-phase claims (builder assert A4).

| Gate | Result | Grounds (consolidated) |
|---|---|---|
| **G0 Proveniência** | **PASS** | Fase-0 manifests complete (`fase0/manifest_hashes.md`: audited artifacts clean vs HEAD; dirty-tree anomaly declared and shown not to touch audited bytes); every round and the set phase hash-froze inputs and decisive outputs; freeze re-verified 23/23 this session; `errors.csv` sha re-verified twice (`78023def…`); D-batchD-1 admissibility held — the one contaminated artifact (batch D javap) was detected, quarantined, and its dependent sub-assertion scoped false (batchD §8.2#1); set-phase trap sweep 0 hits (EXEC-SET-30). |
| **G1 Inventário** | **PASS** (with registered scope reduction) | 23/23 specs inventoried; 22 paired to 22 distinct api30 rules by content, both name traps resolved (`SecretKeySpec.mop`→`SecretKey.cryptsl`; `IvParameterSpec.mop` naming) (`fase0/inventario_pareamento.md`); **RandomStringPassword.mop has no CrySL rule and is EXCLUDED by researcher decision of 2026-08-09** — a formal scope reduction registered in `fase0/manifesto.md:26-30` and, as that register requires, **re-registered here in the global judgment**; 11 api30 rules without specs recorded as the set's coverage bound (incl. the Group-5 producers). |
| **G2 Gerabilidade** | **FAIL** | KGN: generated monitor does not compile standalone while both generators exit 0 — fail-open, crítica per D-batchC-1; re-verified this session (javac exit 1, `cannot find symbol: Key`; `-merge` masks via import union). 21/22 clean; ≤17-event budget met set-wide (max SRD 15 events; coenable 491 505 exact; ceiling closed batch D); merge measured and deterministic across three sessions (EXEC-SET-01..03,14; batchC §8.1; batchD §8.1³). One spec FAIL fails the set gate. |
| **G3 Linguagem** | **FAIL** | 16/22 specs with executed separating counterexamples at the effective automaton (D-piloto-3), count re-derived from the five §8.1 tables (PASS only GCM, DHG, PBE, IVP, SKS, SKY); set level: the canonical SecureRandom `new` + `nextBytes`×2 sequence FPs on the merged monitor (EXEC-SET-26, re-executed 3×). |
| **G4 Cláusulas/bindings** | **FAIL** | 18/22 FAIL (PASS only IVP, KMF, TMF, SIG); the fail-crash class FEN-KPG-NPE survives `-merge` byte-for-byte and was NPE-demonstrated on the merged monitor (re-executed; the only member of its class in the 23 monitors, EXEC-SET-15); MAC f3 unbound `target(m)` broadcast (EXEC-SET-10); VERIFIED bound to the boxed Boolean (EXEC-SET-21). |
| **G5 Pointcuts** | **FAIL** | 13/22 FAIL; 5 canonical divergence-mechanism families / 6 named instances (§1.2a), all jar-robust, re-verified over the MERGED descriptor on both frozen jars this session; batch A/B PASS halves stand as **single-half evidence** (batch C §8.4, extended batch D §5) — declared, not reopened; android-37.0 production-default jar reaches 3 post-api30 members via SRD g2 (extra-oracle capture, EXEC-SET-12); wrapper naming jar-dependent (EXEC-SET-13); descriptor-lint mechanism census silent at exit 0 (set_exec_report §2). |
| **G6 Artefatos/weaving** | **INCONCLUSIVE** | The static halves are executed and clean as far as they reach: descriptor↔aspect↔monitor 119/119 + 140/140 (EXEC-SET-04); host production dexlib2 weave over 168 scenarios on both jars (EXEC-SET-11, re-executed). But §16's letter requires cardinality/order/bindings/DEX confirmed **end to end**, and no round or phase drove a woven DEX on ART/device (**batchD** BETA-SET-06, **batchC** BETA-SET-08, **batchB** BETA-SET-11 — all INCONCLUSIVE; round qualification per REF-G-01: same-named claim IDs in other rounds are distinct claims with other resolutions). Applying §16 honestly: the gate cannot be PASS (end-to-end not shown) and cannot be FAIL (no adverse device evidence) — INCONCLUSIVE, which **blocks READY** exactly as a FAIL would. |
| **G7 Predicados/composição** | **FAIL** | Set graph (`set_cons_predicate_graph.csv`, asserts re-run): 127 sites / 25 constants; **11 reader-less constants**; 4 extra-oracle gates (MAC/SKY GENERATED_KEY; CIS/COS GENERATED_CIPHER) + 2 extra-oracle reads (SSL RANDOMIZED, PBK password); guaranteed-fire PREPARED_HMAC edge (unwritable writer × faithful reader); RANDOMIZED material overgrant closed writer→reader end to end (EXEC-SET-16, re-executed); KPR 1-FP-per-access toll edge (EXEC-SET-19); dead SIGNED/VERIFIED writers; @fail-remove revocation family with zero NEGATES in the api30 rules; second-writer/second-producer discoveries live (EXEC-SET-17/18); only ~5 edges simultaneously rule-grounded, live and defect-free (EXEC-SET-29). |
| **G8 Testes** | **FAIL** | By `pre_registro.md` §3 row 8 the gate FAILs when FP/FN is observed: the executed drives exhibit both (FPs: SRD next2, KPR toll, KMF cascade, SSL unmonitored-random; FNs: rejected-randomness acceptance, SIGNED starvation). Honesty clause: the §11 **systematic differential/mutation campaign was never executed in any round** — the drives are adjudication witnesses, not the pre-registered corpus; mutation adequacy is additionally INCONCLUSIVE. The FAIL rests on the observed-FP/FN criterion alone. **Interpretation declared (REF-G-03)**: this FAIL follows the literal FAIL cell of §3 row 8 ("FP/FN observado", no corpus qualifier); the alternative reading — INCONCLUSIVE because the pre-registered test object was never built — is acknowledged as equally defensible and is equivalent for the READY conjunction: neither is PASS, both block READY. |
| **G9 Diagnóstico** | **FAIL** | 22/22 audited specs FAIL — the only gate failed by every unit in every round; set level: 5 of the 14 drive records carry `expecting=unknown`, exactly accompanying the executed FPs (EXEC-SET-25); dedupe collapse loses a detected violation at the collector (EXEC-SET-24, re-executed; identity source-verified §0.3); families of record: unknown-expecting, same-call pairing, empty labels (H4 closed live), 10× messages, NPE annihilation. |
| **G10 Android** | **INCONCLUSIVE** | Not executed in any round or phase (emulator use is out of audit scope by design). The consolidated replay battery is named and carried: G10-SRD-1, G10-KPG-1/2, G10-SIG-1, G10-MAC-1, G10-TMF-1, G10-SSL-2, G10-KST-1, G10-KGN-1, G10-IVP-1, G10-SKY-1, GAMA-KPR-06 / GAMA-SET-16 / GAMA-SET-21 batteries, Android-BC alias probe (JVM+provider — no device needed for the alias half). Blocks READY. |
| **G11 GH100/GH101** | **FAIL** | Register accuracy consolidated across rounds: the `predicate_edges.csv` 1.5.2-anchor invariance premise is **falsified** (rows :47, :74-75, :81 vs api30 — no "present" verdict consumable without an api30 anchor check; FEN-D-REGISTER-ANCHOR-DRIFT); a false gh101-authored comment (SRD c3) contradicts the code; inherited critical families left unregistered (provenance census §5); gh101-introduced defects on record (GENCIPHER-EXTRA task 5.1, SSL-RANDOMIZED-EXTRA task 3.2, KPG initError placement residual); gh100 open tasks not hidden but open (7.4 duplicated `[x]`/`[ ]`, 7.5, 7.6 — `fase0/estado_gh100_gh101.md`). Both sides of record: repairs that held (TMF four-defect, SSL `returning(ctx)`, KGN i1–i5 split, D-S12 reset removal, layer-2 star prefixes) are preserved. "Requisitos reproduzidos" is not met. |
| **G12 Estática** | **FAIL** | Source-verified this session: the static path defaults `mop_dir` to the literal `jca` directory and probes the android jar over `[33,29,28,27,26]` (never 30), and `get_static_analysis_config` overrides none of it — **every `jca_android` run's static view is computed against the `jca` specs and never against the api30 jar** (EXEC-SET-28; GAMA-SET-01/03 confirmed unchanged). Open static/dynamic contradictions: FEN-SET-STATIC-DEAD-TARGETS (static-listed, dynamically dead), SKY both-views-blind (GAMA-SET-14 scoped), ctor-invisibility. §13's unlock condition (100% clauses mapped, no contradictions) is contradicted. |
| **G13 Revisão** | **FAIL** | The review PROCESS is complete — all five refutation rounds answered objection by objection (13/9/5/8/8 objections; every material one remediated in a rev. 2) and this judgment will itself face an independent global refutation. But §16's letter requires **no critical/major finding open after refutation**, and the must-close set stands open: 174 critical FAIL claims (164 of-record + 10 pilot derived-parsed), of which 165 link to the 50 critical-carrying canonical phenomena while 9 pilot criticals remain pilot-local without canonical FEN (pre-D-piloto-4; phrasing per REF-G-02), every major family, and 26 named INCONCLUSIVE pendencies. D-batchC-1 ledger reconciliation delivered and re-verified (8 rows counted at §4's letter in addition to the 164 of-record, §0.7). |

**Tally: 2 PASS (G0, G1) · 10 FAIL (G2, G3, G4, G5, G7, G8, G9, G11, G12,
G13) · 2 INCONCLUSIVE (G6, G10).**

---

## 3. Verdicts

### 3.1 Individual verdicts (recap of the five closed rounds — final, of record)

All verdicts are "REPROVADA in the covered scope (G2, G3, G4, G5, G7, G9)";
G6/G8/G10 were not executed per-spec and can only ADD defects.

| # | Spec | Round | Verdict | Decision of record |
|---|---|---|---|---|
| 1 | CipherSpec | pilot | REPROVADA | `pilot/juiz_sintese.md` §8.1 |
| 2 | GCMParameterSpecSpec | pilot | REPROVADA | `pilot/juiz_sintese.md` §8.1 |
| 3 | DHGenParameterSpecSpec | batch A | REPROVADA | `batchA/juiz_sintese_batchA.md` §8.1 |
| 4 | HMACParameterSpecSpec | batch A | REPROVADA | idem (G5 PASS vacuous — oracle-bias register) |
| 5 | PBEParameterSpecSpec | batch A | REPROVADA | idem |
| 6 | IvParameterSpecSpec | batch A | REPROVADA | idem (88.33 score — compensation prohibited) |
| 7 | SecretKeySpecSpec | batch A | REPROVADA | idem |
| 8 | CipherInputStreamSpec | batch B | REPROVADA | `batchB/juiz_sintese_batchB.md` §8.1 |
| 9 | CipherOutputStreamSpec | batch B | REPROVADA | idem |
| 10 | KeyPairSpec | batch B | REPROVADA | idem |
| 11 | SecretKeySpec (target `SecretKey`) | batch B | REPROVADA | idem |
| 12 | PBEKeySpecSpec | batch B | REPROVADA | idem |
| 13 | KeyGeneratorSpec | batch C | REPROVADA | `batchC/juiz_sintese_batchC.md` §8.1 (G2 also FAIL) |
| 14 | KeyManagerFactorySpec | batch C | REPROVADA | idem |
| 15 | TrustManagerFactorySpec | batch C | REPROVADA | idem |
| 16 | SSLContextSpec | batch C | REPROVADA | idem |
| 17 | KeyStoreSpec | batch C | REPROVADA | idem |
| 18 | MacSpec | batch D | REPROVADA | `batchD/juiz_sintese_batchD.md` §8.1 (12.57 — lowest unit score) |
| 19 | MessageDigestSpec | batch D | REPROVADA | idem |
| 20 | KeyPairGeneratorSpec | batch D | REPROVADA | idem (NPE crash class) |
| 21 | SecureRandomSpec | batch D | REPROVADA | idem |
| 22 | SignatureSpec | batch D | REPROVADA | idem |
| — | RandomStringPassword | — | **EXCLUDED** | researcher decision 2026-08-09, `fase0/manifesto.md:26-30`; registered here per G1 |

**22/22 audited specs REPROVADA; 0 APROVADA; 0 INCONCLUSIVA; 1 of 23
excluded by formal researcher scope reduction (22 audited + 1 excluded = 23
inventoried).**

### 3.2 SET verdict (pre_registro §7)

**The `jca_android` set is NOT READY.** READY is a five-member conjunction;
four members fail and one holds:

1. **"23/23 APROVADA" — FAILS.** 0 of the 22 audited specs is APROVADA (all
   22 REPROVADA); the 23rd is researcher-excluded. Even under the reduced
   scope (22), the member requires 22/22 APROVADA and has 0/22.
2. **"All gates G0–G13 PASS" — FAILS.** 10 gates FAIL (G2, G3, G4, G5, G7,
   G8, G9, G11, G12, G13) and 2 are INCONCLUSIVE (G6, G10); INCONCLUSIVE is
   not PASS and never converts to it.
3. **"No clause OMITIDA/INCORRETA/INCONCLUSIVA" — FAILS.** The consolidated
   ledger carries hundreds of INCORRETA/OMITIDA resolutions (322 FAIL claims,
   174 critical counting the pilot's derived parse) and 26 INCONCLUSIVE
   named pendencies.
4. **"No open counterexample" — FAILS.** Executed, reproducible
   counterexamples are open in every failing gate — among them the canonical
   SecureRandom-use FP, the rejected-randomness FN, the KPR FP toll, the KPG
   NPE crash, SIGNED starvation, and the dedupe emission loss, all
   re-executed by this judge (§0).
5. **"Reproducible evidence" — HOLDS.** The only satisfied member: every
   decisive number in this judgment reproduced byte-identically from frozen
   inputs (§0), and the consolidation scripts re-run with asserts passing.

Consequence (protocol §16): **the set does not unlock the static analysis.**
No divergence was silently accepted anywhere in the audit; the researcher
decision list (§7) is the exhaustive set of items awaiting explicit scope
reduction or repair.

---

## 4. Global descriptive score (published under protocol §15 — fully labeled)

**Set-phase score** (the 30 set claims resolved in §1; pre-registered weights
`pre_registro.md` §6; raw weighted sum per D-batchA-1; machine output in
`juizglobal_build_output.txt`):

| Dimension | Weight | Resolved | PASS | Subscore |
|---|---|---|---|---|
| linguagem_formal | 20 | 1 | 0 | 0.00 |
| captura_eventos | 20 | 6 | 0 | 0.00 |
| bindings_clausulas | 15 | 3 | 0 | 0.00 |
| predicados_composicao | 15 | 8 | 1 | 1.88 |
| toolchain_android | 15 | 7 | 4 | 8.57 |
| diagnostico | 10 | 2 | 0 | 0.00 |
| reprodutibilidade | 5 | 3 | 3 | 5.00 |
| **TOTAL (raw weighted sum)** | 100 | 30 | 8 | **15.45** |

COMPLETE (0 INCONCLUSIVE); all seven dimensions carry claims (no unattainable
weight). Per-phenomenon counts (D-piloto-4 rule 3): 20 phenomena over 22 FAIL
claims (table in the build output).

**Unit scores of record are NOT pooled** (D-batchA-1; consolidation threat 1
— rounds' standards evolved, so cross-round score comparisons are not
like-for-like). For reference, the per-round records: pilot 55.90
(INCOMPLETE); batch A DHG 63.33 / HMC 32.50 / PBE 69.17 / IVP 88.33 /
SKS 68.83 / SET 30.00; batch B CIS 40.00 / COS 34.17 / KPR 50.50 /
SKY 47.50 / PBK 59.60 / SET 8.33; batch C KGN 51.25 / KMF 48.67 /
TMF 47.92 / SSL 39.50 / KST 44.00 / SET 17.08; batch D MAC 12.57 /
MDG 47.83 / KPG 24.75 / SRD 16.50 / SIG 29.17 / SET 8.75.

**MANDATORY LABELS**: every number above is a descriptive score ≠ probability
of correction ≠ verdict; never rounded to 100; no score opens a gate; IVP at
88.33 is REPROVADA — compensation across dimensions is prohibited;
INCOMPLETE units are labeled in their round records.

---

## 5. Top findings by family, with provenance

Provenance classes (consolidator's registry, REF-C-05 discipline — provenance
routes accountability and excuses nothing): **[jca]** inherited from the
frozen `jca` twin, pre-gh101; **[gh101]** introduced by gh101; **[tool]**
toolchain (generator/weaver/collector, outside both spec sets); **[oracle]**
oracle-bias (api30 rule anomaly).

1. **Language (ORDER) family** — 16/22 specs with executed separating traces
   at the effective automaton; headline: the canonical SecureRandom
   `new`+`nextBytes` use FPs from the second call site (FEN-SRD-NEXTBYTES-FP
   [jca]; matches the 12 400 historical lines' profile, H-SRD-1, replay
   pending); MAC carrier FP on rule-conformant traces [jca]; KPR `co?`
   made mandatory — 1 FP per pair access (FEN-KPR-CO-OPCIONAL [jca]).
2. **Capture family** — first-call disjunct drop (CIS/COS/KPG) [tool];
   declared-only member index kills inherited members (SRD `nextInt()`,
   `ints`) [tool]; nested-type descriptors unweavable (KST
   getEntry/setEntry) [tool]; return-type-dead pointcuts (SIG `sign` declared
   `byte`; SSL `createSSLEngine` declared `void`) [jca — spec-authored
   signatures]; whole-spec inertness (SKY zero capture on the production
   path) [tool]; varargs `args()` narrowing ignored, reaching post-api30
   members under the production-default jar [tool]; HMC class absent from
   android-30 — capture vacuous [oracle].
3. **Bindings family** — KPG NPE crash-to-app (switch on
   creation-initialized field; the only crash-class member set-wide)
   [jca, mechanism-identical twin]; MAC f3 unbound `target(m)` broadcast
   [jca, header byte-same]; VERIFIED on the boxed Boolean instead of the
   sign bytes [jca]; KGN keySize omission (before-event FN) [jca]; the
   GENERATED_KEY second-slot drop at every writer (unary store)
   [jca, structural].
4. **Predicates/composition family** — RANDOMIZED object/material split:
   material marks granted unconditionally, including from rejected
   instances, and accepted by production readers end to end
   (FEN-D-RANDOMIZED-WRITER [jca]); extra-oracle gates and reads:
   generatedCipher subsystem (CIS/COS gates × CIP writers — executed FP J2b)
   [gh101, task 5.1], MAC/SKY GENERATED_KEY gates [jca], SSL
   RANDOMIZED-on-`_` read [gh101, task 3.2], PBK password clause [jca];
   guaranteed-fire PREPARED_HMAC edge (unwritable writer × faithful reader —
   every parameterized `Mac.init` FPs) [oracle+jca]; @fail-remove revocation
   cascades with zero NEGATES in the rules [jca]; 11 reader-less constants,
   dead SIGNED/VERIFIED writers [jca]; KMF→SSL fail-then-proceed
   (error+mark+acceptance co-occur) [jca].
5. **Toolchain divergence family** — five mechanism families / six named
   instances where the two production weave halves measurably disagree
   (§1.2a) [tool], all jar-robust, device semantics unknown (G6/G10);
   android-37.0 lexicographic-max default jar (no call-site pins
   `--android-jar`) [tool]; wrapper-name instability across jars [tool].
6. **Diagnostics family** — `expecting=unknown` accompanies exactly the
   most frequent executed FPs [jca]; dedupe identity excludes `expecting`
   and collapses distinct violations at one site — emission loss at the
   collector, both CSV and logcat [tool]; empty labels (creation-at-consume,
   H4 closed live) [jca]; KPG NPE annihilates records (only 16 historical
   lines) [jca]; 13 specs with zero historical emission — never adjudicated
   as acceptance [record discipline].
7. **Fail-open family** — generators exit 0 for: uncompilable artifact (KGN,
   masked by `-merge` import union — the set phase's central new
   measurement), parse errors, undefined ERE symbols, excess parens,
   swallowed tokens [tool]; counted at §4's letter (crítica) per D-batchC-1
   — 8 pilot/A/B claims reconciled, batch C/D already of record.
8. **Oracle-bias family** — HMC targets a class android-30 does not publish;
   Mac g1=g2 duplicate Gets; SecureRandom protected `ne`
   (`randomized[numB]` unimplementable as written); MDG MD5/SHA-1 are SAFE
   under the raw api30 oracle (5 891/6 048 historical UnsafeAlgorithm lines
   would flip meaning under an oracle change — recorded warning);
   declared-but-unordered events semantics (decides two KST INCONCLUSIVEs)
   [oracle — all awaiting researcher disposition, §7].

---

## 6. Risks for the thesis use of this spec set, and threats to validity

### 6.1 Risks (if the set were used as-is)

1. **Measured violation counts are not interpretable as misuse counts.** The
   dominant historical strata match executed FPs (SRD 12 400 lines ↔ next2
   FP; KPR 668 ↔ co? toll; TMF pairing 1.000 ↔ carrier+empty-label), while
   executed FNs (rejected-randomness acceptance, SIGNED starvation, dead
   pointcuts, whole-spec SKY inertness) suppress true positives — both
   directions, spec-dependent, uncorrectable post hoc.
2. **Crash risk in instrumented apps**: the KPG NPE fires on `initialize` as
   a first event on an unseen generator — an app-crash class that also
   annihilates its own evidence.
3. **Emission loss**: the dedupe identity silently drops co-located distinct
   violations; any per-line analysis undercounts at exactly the
   multi-violation sites.
4. **Environment skew**: production weaves against the lexicographic-max
   platform jar (host 37.0, Docker 36, oracle 30) — capture surface varies
   by machine; wrapper names vary by jar.
5. **Static/dynamic incoherence**: the static path silently analyzes the
   `jca` specs for `jca_android` runs — any static/dynamic synergy claim is
   currently unfounded (G12).
6. **Diagnostic non-attribution**: `expecting=unknown` on the most frequent
   record families prevents clause-level attribution — the protocol's
   requirement for thesis-grade evidence.

### 6.2 Threats to the audit's own validity (declared)

1. **Round heterogeneity**: scoring presentation, FEN linkage, severity
   letters and admissibility tightened round over round (D-batchA-1 →
   D-batchD-1); cross-round raw comparisons are not like-for-like; this
   judgment pools claim counts only with the per-phenomenon lens and never
   pools scores.
2. **JVM vs ART**: every dynamic demonstration ran on Temurin 25; ART
   dispatch, boxing caches, WeakReference timing and the provider set may
   shift specific shapes (declared per finding; KMF SunX509 cascade is
   JVM-default-specific). Direction of the core findings (dead pointcuts,
   NPE, dedupe identity) is structural, but G6/G10 remain INCONCLUSIVE.
3. **Single-half G5 in batches A/B** and **dimension-5 route gaps** (pilot
   none; batch A single-route 4/5): declared, carried, not repaired; any
   lifecycle conclusion leaning on batch A's single-route specs inherits the
   weakness.
4. **Consolidator judgment calls**: pilot severity parse (derived, labeled),
   pilot FEN under-linkage (9 joins only), alias-map risk on non-critical
   rows, fail-open family membership rule — all printed with their selection
   rules; nothing verdict-bearing rests on them (asserts bind the critical
   groupings to published pairs).
5. **Scenario coverage**: jar-equivalence is asserted for the 168-scenario
   union, not all api30 members; the drives cover the composition chains,
   not the §11 systematic corpus (G8's declared limitation).
6. **This judge's own exposure**: I re-executed the decisive evidence and the
   consolidation arithmetic, but did not re-derive the five rounds' per-spec
   adjudications from raw agent reports — those stand on their closed,
   refutation-tested records. The global refutation round should probe
   whether any §1/§2 resolution leans on an unverified round-level claim.

---

## 7. Researcher decision list (countersignature items — USER decisions, not the judge's)

Pooled from all rounds' §8.4/§8.5 lists and the consolidation §5; each item
requires explicit scope reduction, oracle ruling, or repair authorization —
never silent acceptance (pre_registro §7).

1. **RandomStringPassword exclusion** — countersign the registration
   (`fase0/manifesto.md:26-30`; re-registered in §3.1 here).
2. **HMC oracle-bias register** (class absent from android-30; batch A
   REF-B-08 — "documented THIS round", awaiting countersignature).
3. **1.5.2-vs-api30 register anchor** (`data/gh101/predicate_edges.csv` —
   anchor column or api30 re-derivation; falsified invariance premise,
   batch D §0.7/§1#14).
4. **Extra-oracle clause family disposition**: generatedCipher subsystem
   (CIS/COS gates + CIP writers), MAC/SKY GENERATED_KEY gates, PBK password
   clause, SKS surrogate, SSL RANDOMIZED-on-`_`, revocation-without-NEGATES
   (@fail removes), D-S9 carrier-residue disposition — whose "two
   philosophies" register ground is factually false (GAMA-SET-22).
5. **Mac g1=g2 duplicate-Gets oracle anomaly** (batch D).
6. **SecureRandom protected-`ne`** — `randomized[numB]` unimplementable as
   written (batch D).
7. **Folding/alias family** — MDG folding critical now; MAC ALFA-MAC-12
   `major-pending` and batch C KGN alias half return to crítica or close on
   the Android-BC alias probe.
8. **reset()/clone() oracle blind spots** (batch D).
9. **Declared-but-unordered events semantics** (REF-D-03) — decides the two
   KST INCONCLUSIVEs (ALFA-KST-04/GAMA-KST-05).
10. **MDG MD5/SHA-1 oracle-shift warning** — 5 891/6 048 historical
    UnsafeAlgorithm lines name algorithms the raw api30 oracle does not
    forbid; any future drop is oracle change, not repair (consolidation §4.1).

---

## 8. Replication package inventory (protocol §17 item 14)

Files of record, by phase. Hash lists of record: each round's synthesis §7/§8
(batch B §8.5, batch C §8.7, batch A §8.6 + responses REF-B-01 list, batch D
§8 + responses), `set/set_exec_hashes.txt`, `set/set_cons_hashes.txt`,
`fase0/manifest_hashes.md`. A fresh sha256 sweep over every file below, plus
this judgment's outputs and the judge's re-execution outputs, is
`juizglobal_hashes.txt` (machine-checkable in one pass).

- **fase0/**: `pre_registro.md`, `modelo_semantico.md`, `manifesto.md`,
  `manifest_hashes.md`, `toolchain_ambiente.md`, `estado_gh100_gh101.md`,
  `inventario_pareamento.md`, `desvios.md`,
  `upstream_CrySL_e92f5607.xtext` (D-piloto-1 evidence, sha `881c41c2…`).
- **pilot/**: `juiz_sintese.md` (§8 prevailing), `juiz_claims_resolvidos.csv`
  (rev. 2), `juiz_rescore.py`, `refutacao_parecer.md`,
  `juiz_respostas_refutacao.md`, agent reports (alfa_/beta_/gama_), harness
  outputs and hashes (`beta_hashes.txt`).
- **batchA/** … **batchD/**: per round — `juiz_sintese_batch<X>.md` (§8
  prevailing), `juiz_claims_resolvidos_batch<X>.csv` (rev. 2),
  builder/rescore scripts + outputs, refutation parecer + responses, judge
  drives/walks/probes with 3-rep hashes, agent reports and evidence files,
  generation manifests with input hashes (the durable reproduction path:
  commands + input hashes recorded in each round's generation manifest).
- **set/**: executor — `set_exec_report.md`, `set_exec_claims.csv`,
  `set_exec_hashes.txt`, merge timing, descriptor lint (py+out), fail-crash
  sweep (py+out), standalone compile record, weave probe (java+tsv+2 jars'
  outs+diff), composition drive (java+rep1), dedupe probe (java+rep1);
  consolidator — `set_cons_report.md`, `set_cons_ledger.csv` (558),
  `set_cons_fen_registry.csv` (119), `set_cons_predicate_graph.csv` (127
  sites), build/hist scripts + outputs, `set_cons_hashes.txt`.
- **global/**: this report, `juizglobal_set_claims_resolvidos.csv`,
  `juizglobal_gates.csv`, `juizglobal_build.py` +
  `juizglobal_build_output.txt`, `juizglobal_hashes.txt`.

**Scratch ephemerality (declared)**: all generation/execution ran in
session-scratch (`/tmp/claude-1000/…/scratchpad/{set,batch*,global}`), which
does not survive the machine. The durable reproduction path is: frozen input
hashes (fase0 + per-phase hashes files) + exact commands (recorded in the
round generation manifests, the set report §1, and §0 here) + the committed
harness sources (`*_*.java`, `*.py`, `*.tsv` under `audit/…`). The judge's
re-executions (§0) demonstrate this path works: every decisive output
re-materialized byte-identically from the audit-tree sources alone.

**Open ends of the package** (not reproducible on this host):
- the **G10 replay battery** (§2 G10 row) — device/emulator, via
  rv-experiment/rv-platform only;
- **host-executable follow-ups**: Android-BC alias probe (JVM+provider),
  CIS/COS first-disjunct re-measure (now DONE in the set phase —
  EXEC-SET-05 closes it), `skip_stderr` call-site sweep, container
  android-36 jar triangulation (REF-12, carried since the pilot), ajc
  compile of the merged `.aj` (Docker-only);
- the **§11 systematic differential/mutation corpus** (G8) — never built.

---

## 9. Next steps (protocol §19 item 8)

Per the protocol, correction proposals and skill evolution come **after**
this judgment and its independent refutation, in separate patches — discovery
and repair are never mixed. Candidate patch areas are NAMED here, not
designed:

1. **Spec repairs (jca_android tree)**: KGN import (`java.security.Key`);
   SIG sign return types; SSL `createSSLEngine` return type; CIS/COS/KPG
   disjunction splits; KST nested-type qualification; MAC f3 `target(m)`
   binding; VERIFIED slot; KPG NPE guard (initialize-before-getInstance
   path); KPR `co?` restoration; SRD next2-repetition ORDER; RANDOMIZED
   material-mark discipline; the extra-oracle clause family per the §7
   researcher decisions; diagnostic messages (specific `expecting`
   everywhere, stable dedupe keys).
2. **Toolchain patches (rvsec/rv-android)**: dexlib2 first-disjunct,
   declared-only index, varargs-`args()` handling; generation-time
   fail-closed checks (descriptor lint + standalone compile in the
   generator pipeline); dedupe identity (include `expecting` or a
   clause/constraint id); `--android-jar` pinning at rv-android call sites.
3. **Static path (rv-experiment / rv-static-analysis)**: wire
   `mop_dir`/`android_jar` for `jca_android`; add "30" to the probe list or
   pass the oracle jar explicitly.
4. **Skill evolution (`/rv-analyze-spec`)**: dimensions 6–15 of protocol
   §18, each with the audit's minimal cases and regressive examples (the
   five rounds supply them); patch separate from spec repairs, with
   independent review.
5. **Evidence completion**: G10 replay battery on-device; the §11
   differential/mutation corpus; ajc half in Docker; android-36
   triangulation.

*After this document, the independent global refutation round attacks this
judgment; the judgment becomes final only after every objection is answered
(protocol §15). — superseded by §10: the refutation round has completed and
been answered; §10 below is the final decision.*

---

## 10. FINAL DECISION after the global refutation round

2026-08-09. Issued after responding to each of the **4 objections** of the
independent global refutation reviewer (`global/refutacaoglobal_parecer.md`;
responses in `global/juizglobal_respostas_refutacao.md` — outcomes: **4
accepted, all minor; 0 material, 0 blocking; 0 resolution/severity-of-record/
gate/score/verdict changes**). Sections 0–9 above are rev. 2 (the accepted
presentational corrections are applied in place and tabled in the responses
document); **where wording diverges, this section prevails**. The builder is
rev. 2 (`juizglobal_build.py`: A4 hardened to round-qualified (round, claim)
pairs; new A6 pins G6's referents), re-run with all asserts passing;
`juizglobal_set_claims_resolvidos.csv` is byte-identical between rev. 1 and
rev. 2 (no resolution moved).

### 10.1 Final SET verdict

**The `jca_android` specification set is NOT READY.** Stated plainly: the
set REPROVA at set level. 22/22 audited specs REPROVADA in their covered
scopes (0 APROVADA, 0 INCONCLUSIVA); RandomStringPassword excluded by formal
researcher scope reduction (22 audited + 1 excluded = 23 inventoried). The
pre_registro §7 READY conjunction fails on four of its five members —
(1) 0/22 approved; (2) 10 gates FAIL + 2 INCONCLUSIVE; (3) hundreds of
INCORRETA/OMITIDA resolutions and 26 INCONCLUSIVE pendencies; (4) executed,
reproducible counterexamples open — and holds only on member (5),
reproducible evidence. Per protocol §16, **the set does not unlock the
static analysis**, and per pre_registro §7 no divergence was silently
accepted anywhere in the audit.

### 10.2 Final gate matrix (unchanged by the refutation)

| PASS | INCONCLUSIVE | FAIL |
|---|---|---|
| G0 Proveniência, G1 Inventário | G6 Artefatos/weaving, G10 Android | G2 Gerabilidade, G3 Linguagem, G4 Cláusulas/bindings, G5 Pointcuts, G7 Predicados/composição, G8 Testes, G9 Diagnóstico, G11 GH100/GH101, G12 Estática, G13 Revisão |

Grounds: §2 (rev. 2), machine-readable in `juizglobal_gates.csv` (rev. 2,
G6 pointers round-qualified; G8 interpretation declared; G13 headline
precise).

### 10.3 Member 5 independently re-derived by the refuter

The refuter — an adversarial party — re-materialized every decisive artifact
**byte-identically** from the audit-tree sources and hash-verified frozen
inputs, independently of this judge's own re-executions: the full `-merge`
(`310fae06…`/`e91570ce…`/`d6228eac…`), the KGN standalone/merged compile
pair, the composition drive (`8168d2a7…`), the dedupe probe (`3a658775…`),
the weave probe on both frozen jars (`14e84cca…`/`7da00861…`), both
consolidation scripts with asserts, this judgment's builder, and every
published figure by independent recount (`refutacaoglobal_recount.py` R1–R7;
`refutacaoglobal_reexec_log.txt`). The durable reproduction path claimed in
§8 is therefore demonstrated twice over, by opposed parties.

### 10.4 Closing of the judgment phase

**Protocol §19 items 1–7 are COMPLETE**: (1–2) fase 0 frozen and
pre-registered; (3) pilot; (4) the 22 per-spec adjudications through five
refutation-closed rounds; (5) the set-level verifications (executor +
consolidator); (6) global judgment, discriminating re-executions and the
independent global refutation, answered in full; (7) individual and global
verdicts issued — this section. The audit's judgment phase is CLOSED.

### 10.5 Hand-off to §19 item 8 (separate patches; researcher decides priorities)

Correction proposals and skill evolution come **after** this judgment, in
separate patches — discovery and repair are never mixed. Candidate patch
areas (named in §9, not designed): (i) spec repairs in the `jca_android`
tree (KGN import; SIG/SSL return types; CIS/COS/KPG disjunction splits; KST
nested-type qualification; MAC f3 binding; VERIFIED slot; KPG NPE guard;
KPR `co?`; SRD ORDER; RANDOMIZED material discipline; extra-oracle family
per researcher rulings; diagnostics); (ii) toolchain patches (dexlib2
first-disjunct/declared-only/varargs-`args()`; generation-time fail-closed
lint + compile check; dedupe identity; `--android-jar` pinning);
(iii) static-path wiring for `jca_android`/api30; (iv) `/rv-analyze-spec`
dimensions 6–15 with the audit's regressive examples; (v) evidence
completion (G10 device battery via rv-experiment/rv-platform only; §11
corpus; ajc half in Docker; android-36 triangulation). **The standing input
for that phase is the researcher decision list of §7 (10 items)** — every
item requires the researcher's explicit scope reduction, oracle ruling, or
repair authorization; none is decidable by an agent.
