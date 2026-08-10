# Adversarial refutation — batch C judge synthesis (KGN, KMF, TMF, SSL, KST)

Independent refutation reviewer, round "batch C" · 2026-08-09.
Target: `batchC/juiz_sintese_batchC.md` + `juiz_claims_resolvidos_batchC.csv` (134 claims)
+ `juiz_rescore_batchC.py`/output. Mandate: refute, not endorse. Every objection carries
severity, an evidence anchor (file:line or an execution of mine), and a resolution path.
Auxiliary evidence of this round: `refutacao_rescore_rerun.txt`,
`refutacao_probe_alias_identity.txt`, `refutacao_kgn_compile_rerun.txt`,
`refutacao_reproducao_j1_j2.txt`. My scratch: `<scratchpad>/batchC/refutacao/`.

## 0. What I executed before objecting

1. **Hashes**: all 11 judge files re-hashed = synthesis §7 list (REF-B-01 holds).
2. **Rescore re-run**: `juiz_rescore_batchC.py` re-executed → byte-identical to
   `juiz_rescore_batchC_output.txt` (`refutacao_rescore_rerun.txt`). Denominators
   re-added by hand: per-spec dims (KGN 4/4/10/4/2/3/1 … SET 9/4/3/1) sum to the
   aggregate 19/22/27/23/6/13(+3INC)/1; all weighted sums recompute (KST bind
   15·2/7=4.29; SET derived 17.08/45=37.96%); COMPLETE/INCOMPLETE labels match the
   CSV — TMF/SSL/KST driven by GAMA-TMF-05/GAMA-SSL-07/GAMA-KST-07 (all `diagnostico`),
   SET by BETA-SET-07 (repr) + BETA-SET-08 (tool) + GAMA-SET-21 (diag), KMF's missing
   `repr` dimension correctly stated as unattainable weight 5, not INCOMPLETE.
3. **Builder re-run (D-batchB-1)**: `juiz_build_csv_batchC.py` executed on a scratch
   copy of the three agent CSVs — asserts pass (134; 55/73/6; 53 critical) and the
   sorted output is byte-equal to the frozen judge CSV. Full row-by-row trace of all
   134 claims: 58+40+36 in = 134 out, zero dropped, zero original-column edits,
   position changes exactly the 3 declared overturns (all filed FAIL), INCONCLUSIVEs
   exactly the 6 filed, severity deltas exactly 18 up / 3 down as published (§2.2).
4. **J1-C walk re-run**: output identical, 22/22 PASS.
5. **J2-C drive re-run from clean scratch**: recompiled `JuizDriveC.java` + the five
   monitors (KGN = the documented 1-line-import patch, diff re-verified as exactly
   `2a3 > import java.security.Key;`) against the three production jars; my run's
   sha256 = `d3ac5f70…` = reps 1–3.
6. **KGN compile probe re-run**: frozen artifact (sha `de9e5205…` re-verified) →
   javac exit 1, `cannot find symbol: class Key`, line 259 (`refutacao_kgn_compile_rerun.txt`).
7. **Primary facts re-derived** (not taken from any report): spec tree hashes = round
   manifest; KST `KeyStoreSpec(KeyStore ks)` with all 7 events binding `k`
   (`KeyStoreSpec.mop:21,30-79`); KGN `Key generatedKey;` with no `java.security.Key`
   import; SSL `void`-return engine pointcut (`SSLContextSpec.mop:88-92`) vs
   `createSSLEngine()` returning `SSLEngine` in the frozen-jar javap (whose KeyStore
   listing lacks the JDK-only `getInstance(File,…)` overloads — so it is genuinely
   android-30, not the JDK-fallback trap); KGN artifact 19× `MapOfMonitor` vs KST
   global `Tuple2` at `:498` under `AbstractSynchronizedMonitor` (`:221`); rule facts
   — 0 NEGATES in the five rules, `generatedCipher` 0/33, `KeyStore.cryptsl:47` 2-arg
   g2, `SSLContext.cryptsl` `Init: init(kms, tms, _)` + `randomized[sr]` with `sr`
   in no event + `FORBIDDEN getDefault() => Gets`, KGN rule 11 literals + AES⇒keySize;
   registers — `frozen_set_debt.md:222-247` (delayed accusation registered, same-call
   pairing not), `divergence_record.csv:15` (`b532e439f79a`, Cipher-only),
   `predicate_edges.csv:1,63` + `README.md:17` ("kept as authored" pre-repair
   baseline), `predicate_omissions.csv:7` ("terminal" framing), SecureRandomSpec
   absorbing `unsafeInit` (fsm, all consuming events loop — GAMA-SET-22 confirmed);
   production sources — `WrapperEmitter.java:384` (`paramFqns.size() >= fixedPrefix`),
   no `args()` handling in the file, `:246-249` descriptor-order comment,
   `TypeResolver.java:96-99` (`replace('.','/')`, no `$`),
   `runtime_verification_generator.py:211,269` (`-merge` both calls); provenance —
   jca twins share the engine pointcut byte-identically, the KST `ks`/`k` mismatch,
   the missing KGN import, and the 2-arg condition-suppression, while `randomized`
   exists only in `jca_android` (gh101-introduced) and the KGN base list changed
   jca→jca_android with the 6 alias spellings carried (gh99/aliases split correct);
   `errors.csv` sha `78023def…` = fase0 manifest, and Gama's strata script
   hash-asserts it before reading.
8. **My own probes** (`refutacao_probe_alias_identity.txt`): on the harness JVM,
   `KeyGenerator.getInstance("HMAC-SHA256")` and `("HMAC/SHA256")` throw
   `NoSuchAlgorithmException`; `SSLContext.getInstance("tls")` resolves; two
   `KeyGenerator.getInstance("AES")` calls return distinct references.

## 1. Objections

### REF-D-01 — Fail-open phenomena carry `major` against §4's letter, under an unregistered practice (material)

`pre_registro.md` §4 lists **fail-open** among the *Crítica* triggers. The synthesis
itself names FEN-KGN-NAOCOMPILA a "new fail-open shape" (§3) and BETA-SET-04 an
extension of "the fail-open register", yet resolves ALFA-KGN-09, GAMA-KGN-01 and
BETA-SET-04 at **major** (CSV `severidade_final`). The practice descends from batch A
("minor here, major as pattern", `batchA/juiz_sintese_batchA.md` §1 row 10) — but that
practice was never registered in `fase0/desvios.md`, and D-piloto/batch deviations
explicitly claim not to alter §3/§4 criteria. Either these severities are harmonized
upward like the 18 §2.2 upgrades were (same "§4 letter" argument the judge himself
uses for the no-rarity-carve-out upgrades), or the interpretive rule ("generator-side
fail-open masked by production compensation = major") is registered as a deviation.
**Resolution**: severity correction or a fase0 deviation entry. No verdict or gate
changes either way (KGN is REPROVADA on five other gates; G13 must-close already
includes majors) — but the published "53 critical claims" count is not stable under
the judge's own severity rule until this is settled.

### REF-D-02 — KGN alias-whitelist criticality rests on a trace not shown realizable; the pre-registered critical criterion is not met (material)

ALFA-KGN-04 stays *critica* and GAMA-KGN-03 is harmonized **up** to *critica* on the
strength of "FN executed (S17)". S17 emulates: the real object is
`KeyGenerator.getInstance("AES")` and the alias string is injected into the monitor
events (`JuizDriveC.java:276`, comment "object identity only; alias string emulated").
My executed probe shows `"HMAC-SHA256"`/`"HMAC/SHA256"` **throw** on the harness
platform, and KGN `g1`/`g3` are `after … returning` events (`KeyGeneratorSpec.mop:40,55`)
— so on every platform measured in this audit the alias events can never fire and the
enabling trace cannot occur. Android/BC resolvability is the synthesis's **own
declared pendency** ("KGN alias resolvability on Android BC (declared)", §1 row 12).
§4's critical criterion is "FP ou FN **demonstrável em trace realizável**"; what was
demonstrated is a monitor-level acceptance conditional on an unresolved realizability
question. The SSL half of the same phenomenon is untouched — S15a used a real
resolvable `getInstance("tls")` (my probe confirms it resolves). **Resolution**:
either execute the BC alias-resolution probe (a JVM+BC jar suffices; no emulator) or
hold the two KGN claims at major-pending. No gate impact: KGN G4 FAIL is independently
carried by FEN-KGN-KEYSIZE-OMITIDA, whose trace I verified realizable (`i1` is a
**before** event, `KeyGeneratorSpec.mop:75`, so the FN fires before the platform's
own InvalidParameterException — the judge's "magnitude context" note is correct).

### REF-D-03 — FEN-KST-ENTRIES-OMITIDAS: "the displaced-accusation half holds under either reading" is false under one of the two declared readings (material)

`KeyStore.cryptsl:67-73` declares `scE/skE1/skE2` and aggregates them into
`Entries := gE | sE | scE | skE1 | skE2`, but ORDER (`:79`) uses only `gE`, `gk`,
`sE`, `Stores` — the ambiguity the judge correctly names. Under reading (a)
(declared-but-unordered events are alphabet members that violate wherever they occur),
the rule flags `load, skE1, store` **at skE1**, and the monitor's record at `store`
(S9a) is displaced — the judge's account. Under reading (b) (unordered events are
outside the automaton's alphabet), the trace projects to `load, store`, and the raw
oracle itself flags it **at store** (no `sE` before `Stores`) — the monitor's
accusation is then *correctly placed* and the spec's silence on `skE1` *matches* the
oracle's indifference: on this trace there is neither FP, FN, nor displacement, and
the claims would resolve toward equivalence, not OMITIDA. The judge already concedes
the FN half is reading-conditional; the concession must extend to the displacement
half. **Resolution**: re-scope ALFA-KST-04/GAMA-KST-05 as FAIL-conditional-on-reading-(a)
or INCONCLUSIVE pending the named oracle-semantics resolution. No gate impact (KST
G4/G5 FAIL on independent criticals I verified: unbound `ks`, 2-arg Gets omission,
nested-type unweaving).

### REF-D-04 — The measured ajc×dexlib2 divergence retroactively threatens batch A/B single-half G5 PASSes, and the synthesis does not declare it (material)

Batch C proves the two production weave paths **disagree** (varargs/args() on KMF/TMF;
nested types on KST — both re-verified by me at source and in Beta's outputs). The
synthesis declares this "first for the audit" and routes sweeps to batch D — but says
nothing about the standing G5 **PASS rows of batches A and B**, which were admitted on
single-half evidence: batch A's DHG/PBE/IVP/SKS "exact partition" rows (production
matcher, one path; `batchA/juiz_sintese_batchA.md` §1 row 15, §5) and batch B's
explicit "dexlib2 half" admission with the ajc half INCONCLUSIVE
(`batchB/juiz_sintese_batchB.md` §5 preamble). The round instruction is that
cross-round consistency "must at least be declared". A one-paragraph declaration —
"prior single-half G5 PASSes now carry a demonstrated-divergence threat; the specific
pointcut shapes at risk (trailing `..` with `args()`, nested types) do/do not occur
in those specs" — is owed, and is cheap: the two mechanisms are textually greppable.
**Resolution**: add the declaration (and the grep result) to the final decision or to
the G11 ledger. No verdict flips: every batch A/B spec is REPROVADA on other gates.

### REF-D-05 — G2 FAIL for KGN applies an undeclared interpretation of "geração limpa" (minor)

Protocol §16 G2: "≤17 eventos, geração limpa, tempo/RSS, sem erro/warning relevante";
pre_registro §3 FAIL: ">17 eventos, erro/warning relevante". The generation itself was
measured clean (exit 0, empty stderr, budget fine — the judge says so). The FAIL is
grounded on the *artifact* not compiling standalone — a reading of "geração limpa"
extended to product compilability. The reading is defensible (a monitor javac cannot
compile is a "relevant error" of generation output; the round manifest's own caveat
says exit 0 guarantees nothing; pilot GCM is distinguishable because its degenerate
artifact still compiled) — but REF-B-05 discipline requires gates to fail by
pre-registered criteria, and an extension of the criterion's letter should be declared
as an interpretation in the synthesis, as the G5 scope decision was. **Resolution**:
one declared sentence. KGN's verdict is unaffected (G3/G4/G5/G7/G9 all FAIL).

### REF-D-06 — BETA-KGN-04 overturn: the decisive fresh-instance premise was inferred, not executed or source-cited (minor)

The overturn justification says "JCA constructs a fresh instance per call
(judge-verified API semantics)" — no execution, no file:line of JDK/JCA source. The
audit's own discipline (and this workspace's standing rule) is that mechanism claims
are verified at source or by execution. I executed it: two
`KeyGenerator.getInstance("AES")` calls return distinct references on the harness JVM
(`refutacao_probe_alias_identity.txt`), so the g1·g1 words are indeed unrealizable by
reference identity on the per-object monitor here, and the provider caveat the judge
retained covers the residual. The overturn **stands**; the objection is to the
evidence label only. **Resolution**: cite this probe (or equivalent) in the final
decision.

### REF-D-07 — §2.6's unification ground "same executed records" is overstated for KGN (minor)

Gama's `kgn_a` is the trace `g3, gk1` (2 records; `gama_harness_output.txt:41-43`,
drive source `:222-229`) while Beta's KGN-b and judge S4 include `i1` (3 records).
The unification is still sound — I compared the record sets: at the shared pairing
call the events, types and same-call structure coincide exactly (Gama's pair ≡ S4b's
pair), and all fifteen claims describe the one carrier mechanism — but "one set of
executed records per spec" is not literally what the annexes show. **Resolution**:
reword to "identical record structure at the pairing call; traces differ in the
mandatory-successor leg". No effect on the 15-claim FEN or its criticality.

### REF-D-08 — REF-B-09 claimed as honored, but dimension-5 route coverage is again undeclared (minor)

The preamble lists REF-B-09 among honored carried rules, yet the synthesis nowhere
declares which agents produced parametric/lifecycle (dimension-5) claims per spec.
The batch C reality: KST got true multi-route coverage (Beta ×2, Gama ×2, judge
S6/S7) while Alfa — the agent whose §0/§5.3 statements about exactly this dimension
were wrong (erratum §2.5, which I verified in `alfa_report.md:52,333` and refuted in
the artifact myself) — filed no KST lifecycle claim; the KGN/KMF/TMF/SSL lifecycle
verdicts rest on isolation scenarios (S18c, kgn_b, Beta dim5 rows) without a coverage
statement. Same transparency gap REF-B-09 named in batch A. **Resolution**: one
declared sentence per REF-B-09's own template.

## 2. Areas attacked that survived (one line each)

- **Mechanical layer**: hashes, builder assert (D-batchB-1 enforced — I ran it),
  rescore arithmetic, denominators, SET separation, INC-outside-denominator,
  COMPLETE/INCOMPLETE labels, 55/73/6, 53 criticals, 15 critical phenomena, 27 FEN
  groups — all re-derived independently and correct.
- **J1-C / J2-C / KGN probe**: all three re-executed from clean scratch; byte-identical
  outputs; the drive's scenarios use real platform objects where claimed, and the two
  monitor-event emulations (S16 keySize, S3 protocol string) are either sound (before
  advice) or declared.
- **FEN unification**: the 15 carrier claims are one mechanism (verified against all
  three agents' rows and outputs); FEN-C-DELAYED correctly kept distinct (distinct
  record, S1b, distinct repair point); the two claim-level remaps are unit-correct.
- **All 3 overturns**: no counterexample existed in any (BETA-KGN-04 premise now also
  executed by me; GAMA-KGN-05 closed at `WrapperEmitter.java:246-249` + spec text +
  two benign executions; BETA-SET-06 closed by `README.md:17` baseline semantics I
  re-read — and the third-recurrence complaint is fair).
- **Severity harmonizations**: 18 up / 3 down verified against filed severities;
  the upgrades are each anchored to an executed FP/FN except the KGN-alias pair
  (REF-D-02); the 3 downgrades are grounded (cross-batch precedent; oracle pendency —
  as amended by REF-D-03).
- **KST family**: unbound-parameter sub-shape, global Tuple2, erasure, 2-arg Gets
  omission — every fact re-verified in spec text, artifact, and rule; the census-gap
  lesson is real.
- **Toolchain divergences**: varargs/args() and nested-type mechanisms verified at
  source by me; jar-robust vs android-30-pinned annotations correct (javap provenance
  independently confirmed via the missing JDK-only overloads).
- **Register readings**: 3b.11b partial-registration, the factually-false D-S9 ground
  (SecureRandomSpec's absorbing `unsafeInit` — fsm read by me), b532e439f79a
  Cipher-only, edges:63 scoping, omissions:7 "terminal" framing — all accurate.
- **Provenance table**: 5 rows re-derived against the jca twins and registers
  (engine byte-identical, KST twin, KGN import, gets-invisível, whitelist gh99/alias
  split, randomized gh101-introduced) — all correct.
- **INCONCLUSIVEs**: all 6 honestly non-convertible in this round's means (missing
  jar, ART/device, historical replay); none converted to PASS; no absence-of-firing
  was read as acceptance anywhere I checked (S18d's zero is sound because events are
  invoked directly).
- **Scope honesty**: G6/G8/G10 exclusion declared with the correct monotonicity
  argument; H2/H4 updates keep historical attribution deferred; no majority counting
  found anywhere; aspectj-1.9.25.1-is-the-Docker-version is backed by
  `fase0/toolchain_ambiente.md:56` (the root CLAUDE.md TODO is registered there as
  satisfied).

## 3. Conclusion

Eight objections: **0 blocking, 4 material (REF-D-01..04), 4 minor (REF-D-05..08)**.
None reaches any per-spec verdict (5/5 REPROVADA stands on multiply-redundant,
independently re-executed grounds), any gate outcome, or any score of record. Their
reach is confined to: the severity ledger that G13 will consume (REF-D-01 up-or-register,
REF-D-02 down-or-probe — note they push the "53 critical claims" figure in opposite
directions, so that figure should be marked provisional until both are answered), the
resolution state of two KST-Entries claims (REF-D-03: FAIL → conditional/INCONCLUSIVE,
which would move the 73/6 split), one owed cross-round declaration (REF-D-04), and
three wording/declaration repairs. Per protocol §15, the judge's decision becomes
final only after answering each objection.
