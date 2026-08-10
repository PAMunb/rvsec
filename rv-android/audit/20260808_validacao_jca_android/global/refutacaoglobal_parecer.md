# GLOBAL REFUTATION — adversarial review of the global judgment

Independent global refutation reviewer · 2026-08-09 · target:
`global/juizglobal_relatorio.md` + `juizglobal_set_claims_resolvidos.csv` +
`juizglobal_gates.csv` + `juizglobal_build.py`/`_output.txt` +
`juizglobal_hashes.txt`. Mandate: refute the SET verdict (NOT READY), any gate
result, any score of record — in EITHER direction, including evidence that
would soften a FAIL. Everything below was re-executed or re-derived by me in my
own scratch from the audit-tree sources and the frozen inputs; nothing was
taken on the judge's word. Auxiliary outputs: `refutacaoglobal_recount.py` +
`refutacaoglobal_recount_output.txt` (independent recounts),
`refutacaoglobal_reexec_log.txt` (re-executions with hashes).

## 0. What I re-executed and recounted (summary of the evidence base)

1. **`juizglobal_build.py` re-run** (mirror copy, audit root pinned): exit 0,
   asserts A1–A5 pass, all three generated files **byte-identical** to
   `global/`.
2. **`set_cons_build.py` + `set_cons_hist.py` re-run** (mirror with the five
   round CSVs): all five outputs **byte-identical** to `set/`, every in-script
   assert passing, including the `errors.csv` sha gate.
3. **Independent recounts** (own script, own queries): 558 = 210/322/26;
   per-round rev. 2 figures; 164 of-record + 10 derived criticals; 50 critical
   FEN groups; 8 `severity_s4_letter` rows; diagnostico 11/73/7; set claims
   22 FAIL / 8 PASS / 0 INC; severities 15/6/1; 20 phenomena over 22 FAILs;
   score 15.45; FEN registry 119 rows. **All match.**
4. **Gate tallies G2/G3/G4/G5/G7/G9 re-derived from the five §8.1 verdict
   tables** (transcribed independently): 1, 16, 18, 13, 19, 22 of 22 —
   including the exact PASS complements (G3: GCM,DHG,PBE,IVP,SKS,SKY;
   G4: IVP,KMF,TMF,SIG; G7: PBE,IVP,MDG). **All match.**
5. **Full independent re-execution from audit-tree sources**: 23/23 spec
   freeze re-hash; `-merge` regeneration (`MultiSpec_1*` = `310fae06…` /
   `e91570ce…` / `d6228eac…`, byte-identical); KGN per-spec regeneration +
   `javac` (exit 1, `cannot find symbol: Key` at :259; both generators exit 0;
   merged monitor compiles with `import java.security.Key;` at line 11);
   composition drive (`8168d2a7…`), dedupe probe (`3a658775…`), weave probe on
   both frozen jars (`14e84cca…` / `7da00861…`) — **every one byte-identical
   to the published record**, compiled and run by me from `set/` sources.
6. **Source verifications re-done**: `ErrorDescription` identity;
   RANDOMIZED reader/writer split across CIP/KGN/SSL/IVP/PBK/SRD/SKY spec
   sources; api30 `SSLContext.cryptsl` `randomized[sr]` with `sr` unbound;
   `predicate_edges.csv` rows 47/74–75/81 vs the api30 rules (anchor drift
   confirmed); G12 static-path defaults and caller sweep; `jca`-twin
   provenance spot-checks (MAC `target(m)`, SIG VERIFIED slot, KPR `ere`,
   KPG `switch`). `juizglobal_hashes.txt`: 25-entry random spot-check, 0
   mismatches.

---

## 1. Objections

### REF-G-01 (minor) — Gate-row claim-ID citations are round-ambiguous

**Evidence anchor**: `juizglobal_gates.csv` G6 row cites
`BETA-SET-06; BETA-SET-08; BETA-SET-11`; the report §2 G6 row says
"BETA-SET-06/-08/-11 all INCONCLUSIVE". Claim-ID namespaces repeat per round:
the ledger holds batchA `BETA-SET-06` (**FAIL**, flags), batchB `BETA-SET-06`
(**FAIL**, KPR c1), batchC `BETA-SET-06` (**PASS**) — only batchD
`BETA-SET-06` is INCONCLUSIVE; likewise `BETA-SET-08` is FAIL in batchB and
INCONCLUSIVE only in batchC. The intended referents (batchD -06, batchC -08,
batchB -11) are indeed all INCONCLUSIVE, so the ground is true under the
intended mapping — but the citation as written is checkable only by a reader
who already knows the mapping, and the builder's A4 assert cannot catch a
wrong-round pointer (it checks token existence anywhere in the record).
**Resolution**: round-qualify the three IDs in the gate row (and note A4's
existence-only scope) in the judge's response. **Reach**: none — G6 stays
INCONCLUSIVE; no device evidence exists under any reading.

### REF-G-02 (minor) — The G13/§0.7 critical headline over-implies full FEN coverage

**Evidence anchor**: report §0.7 and G13 row: "164 critical FAIL claims of
record (+10 pilot derived-parsed) across 50 critical-carrying phenomena". My
recount (`refutacaoglobal_recount_output.txt` R2): **9 of the 174 criticals —
all pilot derived-parsed — carry no canonical FEN** (ALFA-CIP-01/02/03/08/17,
ALFA-GCM-03/04, BETA-GCM-04, GAMA-GCM-03), so the claims do not all
distribute "across" the 50 phenomena. Adjacent: the 8 D-batchC-1
reconciliation rows (6 of-record) are crítica at §4's letter yet outside the
"164 of-record" figure. Both facts are on record and declared — consolidator
§1.2–§1.3 and threat §6.2 item 2; report §6.2 item 4 ("pilot FEN
under-linkage, 9 joins only") — so this is a headline-phrasing objection, not
an arithmetic error. **Resolution**: one clarifying sentence in the G13 row
("165 of the 174 criticals link to 50 phenomena; 9 pilot criticals are
pilot-local"). **Reach**: none — G13 fails a fortiori under any of the
readings.

### REF-G-03 (minor) — G8 FAIL rests on a criterion whose pre-registered test object was never built

**Evidence anchor**: gate G8 row; `pre_registro.md` §3 row 8; protocol §16
("corpus discriminante sem FP/FN e mutantes relevantes mortos"). The §11
differential/mutation corpus was never executed in any round (declared in the
row itself), so an equally defensible reading returns **INCONCLUSIVE** (test
not executed) with the observed FP/FN grounding G3/G7 instead. The recorded
FAIL follows the literal FAIL cell of §3 row 8 — "FP/FN observado", with no
corpus qualifier — and the executed drives are reproducible observations of
both FP and FN (re-executed by me). The row carries the honesty clause and
declares suite adequacy separately INCONCLUSIVE. **Resolution**: none
strictly required; the judge's response should acknowledge the alternative
INCONCLUSIVE reading and state why the letter-based FAIL is preferred.
**Reach**: none — FAIL and INCONCLUSIVE are equivalent for the READY
conjunction, and neither is PASS.

### REF-G-04 (minor) — EXEC-SET-23's severity raise is entangled with a pending researcher ruling

**Evidence anchor**: report §1.1; `juizglobal_build.py` RES table
(EXEC-SET-23 major→crítica); api30 `SSLContext.cryptsl` (verified by me:
`REQUIRES randomized[sr]` with `sr` bound by **no** event — `Init` binds
`_`); batch C ledger `ALFA-SSL-07` crítica of-record. The raise applies §4's
letter ("FP demonstrable on a realizable trace" — X1, re-executed by me).
But whether X1's error is an FP or an oracle-faithful positive depends on the
researcher's §7-item-4 ruling on how `randomized[sr]`-with-unbound-`sr` is to
be read; the judge separated disposition (researcher's) from severity
(letter + unrefuted batch C precedent), which is a defensible and
precedent-consistent choice — but the severity of record inherits that
contingency and the report should say so where the raise is made, not only in
§7. **Resolution**: one sentence in §1.1 conditioning the severity on the §7
item 4 outcome (or the researcher's countersignature). **Reach**: none — the
claim is FAIL under either severity; moves only the 15/6/1 tally; no gate, no
verdict, no score depends on it (severity does not enter the score).

---

## 2. Survival statements (areas attacked and not overturned)

1. **Build, asserts, arithmetic**: builder re-run byte-identical; every
   published figure re-derived independently (R1–R7) — no arithmetic error
   found anywhere, including the 164+10/50/8 reconciliation and the 22/8/0 +
   15/6/1 recount.
2. **READY member 5 ("reproducible evidence — HOLDS")**: not overstated —
   I, an adversarial party, re-materialized every decisive artifact
   byte-identically from the audit-tree harnesses plus hash-verified frozen
   inputs (merge, KGN pair, drive, dedupe, weave on both jars); scratch
   ephemerality is declared and the durable path works as claimed
   (pre_registro §8 satisfied by manifests + commands + committed harnesses).
3. **Gate tallies and grounds G2–G5, G7, G9**: recounted exactly from the
   five §8.1 tables; every spot-checked pointer resolves to a real resolved
   claim; the set-level grounds (KGN masking, SRD canonical FP, KPG NPE,
   dedupe collapse, 11 reader-less constants) all re-executed or
   assert-re-run by me.
4. **G0 PASS**: the fase0 "PASS com ressalvas" is not silently upgraded —
   the dirty-tree anomaly and D-batchD-1 quarantine are restated in the gate
   row; the remaining fase0 ressalvas (byte-identical twins, host×Docker
   heterogeneity) are carried where they operate (G5/G6/G10 grounds, risk
   §6.1.4). The letter ("corpus/versionamento/hashes completos") is met —
   verified 23/23 + toolchain re-hash.
5. **G1 PASS**: the RandomStringPassword gap is handled exactly as protocol
   §16 requires for researcher-accepted divergence — formal scope reduction,
   registered (`fase0/manifesto.md:26-31`, confirmed) and re-registered in
   the judgment; the 22/22 content-pairing and both name traps verified in
   `fase0/inventario_pareamento.md`; the 11 unmodelled rules are recorded as
   a coverage bound, which is the honest reading of "pareamento sem lacunas"
   for a spec-side inventory gate. A stricter reading would flip G1 to FAIL
   and only harden the verdict.
6. **G6/G10 INCONCLUSIVE are honest**: the executed static halves are
   credited exactly as far as they reach (119/119+140/140; 168-scenario
   jar-equivalence — re-executed); capture defects are adjudicated under G5,
   not smuggled into G6; absence of device evidence is never converted to
   FAIL or PASS.
7. **Five-families/six-instances**: verified against batch D §1#12 (five
   named, nested-type missing) and §5 (six items called five) and the FEN
   registry (five canonical families; VARARGS covers g2+g4). The judge's
   canonicalization is the only reading consistent with the registry, and G5
   demonstrably does not depend on the count (13/22 per-spec FAILs +
   mechanisms re-verified in the production weave by me).
8. **RANDOMIZED reader split**: verified at spec source by me for CIP, KGN,
   SSL (object-level SecureRandom readers), IVP and PBK (material-level),
   SRD `@match1` (object writer), SKY `e1` (material writer gated by
   GENERATED_KEY) — the consolidator's correction is right and batch D §6.1's
   shorthand was wrong, exactly as adjudicated in §1.2b.
9. **Dedupe finding not smuggled**: X1/X2 are set-phase **executor**
   artifacts (`set_exec_DedupeProbe.java`, filed as EXEC-SET-24, crítica by
   the executor); the judge added a labeled, source-verified note whose
   "wider loss class" reading is compelled by X2's output (re-executed by me)
   and by the `ErrorDescription` javadoc itself. No new claim was created by
   judge fiat; severity was not moved.
10. **G11 anchor drift**: spot-verified by me at source — `predicate_edges.csv`
    rows 47 (Mac `generatedKey` "present"; api30 REQUIRES has only
    `preparedHMAC` and `!encrypted`), 74–75 (SecureRandom
    `randomized[randInt]/[randIntInRange]`; api30 ENSURES binds
    this/genSeed/next/numB), 81 (`verified[verified]`; api30 has
    `verified[sign]`). The falsified-invariance ground stands.
11. **G12**: re-verified at today's source — probe list without "30", literal
    `jca` default, and no rv-experiment caller passes
    `mop_dir`/`targets_file`/`android_jar`.
12. **Researcher decision list (§7)**: cross-checked against pilot §8.4,
    batch A §8.4, batch B §8.4, batch C §8.4–8.5, batch D §8.4 and
    consolidation §5 — all countersignature items appear; remaining
    round-level items are correctly filed as host-executable follow-ups or
    repair candidates (§8/§9), not researcher rulings. No researcher-owned
    decision was taken by the judge (the closest, EXEC-SET-23, explicitly
    leaves the disposition with the researcher — see REF-G-04).
13. **Severity scheme coherence**: the apparent asymmetry (EXEC-SET-17/18/22
    at major while 07/21/23/24 sit at crítica) tracks the pre-registered
    letter faithfully: crítica where FP/FN was executed end-to-end on a
    realizable trace or emission is lost (16, 19, 20, 21, 23, 24, 26) or the
    clause is INCORRETA at clause level (07, 08, 09, 10, 14, 15), major where
    the direction is real but the end-to-end demonstration or the
    device-realizability is the declared gap (17: gate permissiveness not
    driven to a concrete FN; 18: second producer not driven through a reader;
    22: SunX509 cascade is JVM-default-specific — threat declared in the
    row). No selective application found.
14. **Score presentation**: D-batchA-1-compliant (raw weighted sum, labels,
    COMPLETE, no unattainable weight); 15.45 re-derived; unit scores not
    pooled; every quoted per-round figure checked against the round records
    (pilot 55.90 … batch D SET 8.75) — all match.
15. **Scope honesty**: no statement treats G6/G8/G10 as executed; historical
    linkages are hedged ("replay pending", G10 battery named); the CIS/COS
    first-disjunct item was routed as a NEW set-level measurement on the
    merged descriptor (EXEC-SET-05), not a reopening of batch B; D-batchD-1
    sweep re-run by me over the decisive outputs (0 trap markers in
    android-30-labeled evidence; the 3 android-37.0 hits are genuine jar
    members — 1 class entry vs 0, re-verified by `unzip -l`).
16. **Provenance tags**: [jca] spot-checks confirmed in the frozen twins
    (MAC unbound `target(m)`, SIG VERIFIED-on-boolean, KPR `ere c1 (gpu|gpr)*`
    vs rule `co?, (pu*, pr*)*`, KPG `switch(algorithm)`).

## 3. Conclusion

**Objections: 4 — 0 blocking, 0 material, 4 minor. None reaches the SET
verdict, none reaches any gate result, none reaches any score of record.**

The NOT READY verdict is over-determined: I independently re-established the
failure of READY members 1–4 (0/22 APROVADA recounted from the five §8.1
tables; 10 gate FAILs each re-grounded in resolved claims I spot-verified or
re-executed; hundreds of INCORRETA/OMITIDA resolutions recounted; open
executed counterexamples reproduced byte-identically in my own scratch), and
member 5 (reproducible evidence) survives the strongest attack available —
an adversarial full re-derivation from the frozen record, which succeeded
byte-for-byte. The four minor objections are presentational/citation-hygiene
matters plus one severity-contingency note; each is resolvable by a sentence
in the judge's response round without touching any result of record.
