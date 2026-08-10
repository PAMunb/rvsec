# JUDGE — Responses to the batch D refutation round

Judge, 2026-08-09. Target: `refutacao_parecer_batchD.md` (+ refuter evidence
`refutacao_reruns_batchD.txt`, `refutacao_javap_trap_batchD.txt`,
`refutacao_rescore_rerun_batchD.txt`). Protocol §15: one response per
objection, each re-verified by me before acting; the final decision of the
round follows in `juiz_sintese_batchD.md` §8. Outcome summary: **8 accepted —
1 material (REF-E-01), 7 minor; 2 change the resolved record's text/markers
(REF-E-01, REF-E-05), 0 change any resolution, severity class boundary,
score, gate or verdict.**

## REF-E-01 (material) — ACCEPTED. Contamination declared; ALFA-SRD-08 scoped; no reach beyond record hygiene

Re-verified by me this session (commands, all executed):
`grep -c SecureRandomParameters alfa_javap_android30_batchD.txt` → **6**;
`unzip -l android-30/android.jar | grep -ci SecureRandomParameters` → **0**;
trap reproduction `javap -classpath <android-30 jar> -p
java.security.SecureRandom | grep -c SecureRandomParameters` → **6** (system
classes shadow the classpath); the file also carries `sun.security.*` private
members (9 hits) impossible for the android-30 stubs. The refuter's finding is
exact: **`alfa_javap_android30_batchD.txt` is host-JDK output mislabeled as
android-30 — the known JDK-fallback trap — and is hereby declared UNUSABLE as
android-30 evidence** for this and future phases.

Consequences adjudicated:

1. **ALFA-SRD-08**: the `evidencia_primaria` sub-assertion
   "getInstance(String,SecureRandomParameters[,String|Provider]) exist on
   android-30" is **FALSE**; the projected 3-arg untracked-route FP surface is
   host-JDK-only and vacuous on the frozen platform. The resolution
   (CONFIRMADO/FAIL) and severity (major) **stand**, because they rest on the
   independent, judge-verified operative mechanism: g4 `args(alg)` arity-1
   (spec text `:76-78`, my REF-D-04 grep) and the executed born-at-consume FP
   without the specific accusation (SRD-T6/srd_c). Rev. 2 records the scope
   note in the claim's `justificativa_curta`.
2. **Blast-radius check (mine)**: the other claims citing the contaminated
   file (ALFA-MAC-01, ALFA-MDG-01, ALFA-KPG-01, ALFA-SIG-01's javap line)
   assert member facts that I re-derived in §0.5 from unzip-extracted
   android-30 bytes and the refuter re-derived again — every one of those
   facts (Mac 4-update/3-getInstance/2-init/3-doFinal partition; MDG
   overloads; KPG 4-initialize/3-getInstance/genKeyPair+generateKeyPair; SIG
   `byte[] sign()`/`int sign(byte[],int,int)`) is true of the frozen jar. The
   contamination therefore reaches exactly one sub-assertion in one claim.
   ALFA-SRD-06's decisive member facts (protected `next(int)`; nextInt/ints
   not declared) were likewise judge-derived from extracted bytes (§0.5) and
   are correct — notably the contaminated file could NOT have shown the
   declared-members absence, which is one more marker of the trap.
3. **Why I missed it**: my §0.5 policy (extract-then-javap) was applied to
   *my own* facts but I did not sweep the *agents'* evidence files for the
   trap signature. The batch A trap register named the risk; the sweep should
   have been mechanical. Recorded as a judge-process correction: future
   phases must grep agent javap artifacts for trap markers
   (`SecureRandomParameters`, `sun.security`, `jdk.internal`) before
   consuming them. **Threat-to-validity declaration** now in the record
   (synthesis §8.2, §8.4).

No verdict, gate, score or phenomenon changes: confirmed by the refuter and
by my re-check that no other resolution cites the file for a fact not
independently re-derived.

## REF-E-02 (minor) — ACCEPTED. Matrix cell corrected

The §1 #11 Gama cell "FAIL crit ×3 + major" is wrong; Gama filed crítica ×2
(GAMA-SET-27, GAMA-SIG-02) + major ×2 (GAMA-MAC-04, GAMA-MDG-02) — verified
in the CSV by me. The per-phenomenon table (5 FAIL / 3 critical) and all
resolutions were already correct. Corrected in §8.2 (rev. 1 §1 stands as
record; §8 prevails where divergent, batch C convention).

## REF-E-03 (minor) — ACCEPTED. Asymmetry rationale recorded (no severity change)

The within-FEN-C-EMPTY-LABEL asymmetry now carries its rationale in the
record (rev. 2 justificativas of GAMA-MAC-04/GAMA-MDG-02 + §8.2): severity
follows the record shape at the claim's unit — the census row (ALFA-SET-14,
GAMA-SET-27) and SIG's triple-record row (GAMA-SIG-02) carry executed FP
companions on conformant traces (crítica per §4's FP letter), while the
per-spec MAC/MDG rows are the diagnostic-degradation facet of the same
mechanism (§4 "diagnóstico inatribuível" = major), held at their authors'
filed severity. This mirrors the declared SRD exception inside
FEN-C-GETS-INVISIVEL. Severity moves no score; the phenomenon's criticality
was and remains carried by three claims.

## REF-E-04 (minor) — ACCEPTED. One number: 20/20; Beta's prose "19/19" is the slip

Adjudicated on primary evidence: `beta_hashes.txt`'s regeneration section
lists **20** `gen_*/out` artifacts (counted by me: 4 × 5 specs), every hash
equal to the generation manifest; my own freeze check is independently 20/20.
Beta's report §0 "19/19" is a prose counting slip with no claim row attached
(BETA-SET-01's row text says "5/5 artefatos" per-spec regeneration and cites
the hash file). My §1 #19 ("20/20") was correct; my §3 highlight ("19/19")
copied Beta's prose — corrected to **20/20** in §8.2. No artifact was outside
the comparison; no gate or score involved.

## REF-E-05 (minor) — ACCEPTED. "major-pending" machine-recorded

Rev. 2 CSV: ALFA-MAC-12 `severidade_final` = **`major-pending`** (was free-text
only). The rescore's critical predicate is unaffected (`major-pending` is not
critical); all sums unchanged (re-run verified). The G13/global-phase sweep
can now find the Android-BC trigger mechanically, matching the batch C rev. 2
KGN-alias record.

## REF-E-06 (minor) — ACCEPTED. Two provenance wordings scoped to mechanism

Verified by my own diffs against the jca twins: KPG `validate` in the twin
carries extra cases (`3072`, `"DiffieHellman"`) — "twin validate identical"
overstates; the **mechanism** (switch on a creation-initialized field,
uninitialized on unseen creation) is identical. MAC f3: the
pointcut/args/target header (with the unbound `target(m)`) is byte-same; the
bodies differ (jca_android adds the ENCRYPTED check + marking). §8.2 records
the corrected wordings: FEN-KPG-NPE "twin mechanism-identical (switch on
creation-initialized field; extra literal cases in the twin)";
FEN-MAC-F3-UNBOUND "twin f2 header byte-same (incl. unbound target(m));
bodies differ". Provenance class (jca-inherited) unchanged in both.

## REF-E-07 (minor) — ACCEPTED. Aggregate presentation aligned with D-batchA-1

`juiz_rescore_batchD.py` rev. 2: the context-only aggregate now excludes
empty dimensions and states the unattainable weight like the per-unit lines.
Re-run output (of record): AGG RAW **24.51** [… repr --/5] INCOMPLETE (1 INC),
**unattainable weight 5**, labeled derived reading 24.51/95 = 25.80%. The raw
sum is numerically identical to rev. 1 (the empty dimension contributed 0.00);
only the presentation changed.

## REF-E-08 (minor) — ACCEPTED. BETA-SET-07 marked HOST-EXECUTABLE

Correct and useful: unlike BETA-SET-06 (ART/device) and GAMA-SRD-02 (device
replay), the android-37.0 default-jar divergence is discriminable by a
production dexlib2 weave over a jar already on the frozen host toolchain list
— no emulator. Rev. 2 CSV justificativa and §8.4 pendency list now mark it
**host-executable**, so the set-level phase treats it as actionable rather
than ART-deferred. The INCONCLUSIVE state itself is unchanged (the freeze
pinned batch D to android-30 by fase0 decision; re-measurement belongs to the
next phase).

## Closing

Every objection was re-verified against primary evidence before acceptance;
none required dismissing a counterexample or re-litigating a closed round.
The refuter's survival statements (§2) — byte-identical re-runs of rescore,
builder, J1-D and J2-D; independent recount 39/81/3, 54/21/34; both overturns
re-grounded; D-batchC-1 and REF-D-02 compliance; the register-anchor and
CIS/COS findings — stand as independent replication of the round's mechanical
record. The final decision of the round is issued in
`juiz_sintese_batchD.md` §8.
