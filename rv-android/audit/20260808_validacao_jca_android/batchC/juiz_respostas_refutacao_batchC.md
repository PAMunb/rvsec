# Judge responses — batch C refutation round

Judge, 2026-08-09. Responding per protocol §15 to the 8 objections of
`refutacao_parecer_batchC.md`, each re-verified before acting; the decision
becomes final only with §8 of `juiz_sintese_batchC.md` (appended this round).
Outcomes: **8 accepted (4 material: REF-D-01, REF-D-02, REF-D-03, REF-D-04;
4 minor)** — 3 of the materials change the resolved record (rev. 2 of
`juiz_claims_resolvidos_batchC.csv`); none reaches any per-spec verdict, any
gate outcome, or any per-spec score except KST/aggregate denominators
(REF-D-03). New judge evidence this round:
`juiz_probe_identity_alias_batchC.txt` (alias resolvability + getInstance
identity, executed by me; agrees with the refuter's probe on every shared
line) and the REF-D-04 cross-round grep (§REF-D-04 below, commands inline).

---

## REF-D-01 (material) — fail-open severities vs §4's letter — **ACCEPTED; harmonized upward**

The refuter is right on both counts: `pre_registro.md` §4 lists **fail-open**
among the *Crítica* triggers, and the "major as pattern" practice inherited
from batch A was never registered as a deviation. It also *cannot* be
registered compatibly: every deviation on file declares that it does not
alter §3/§4 criteria, so a deviation demoting a §4 trigger is not available.
I therefore apply the letter — the same rule I used for the 18 upward
harmonizations ("no carve-outs"):

- **ALFA-KGN-09, GAMA-KGN-01 → crítica** (FEN-KGN-NAOCOMPILA): a real
  fail-open of the round's own chain — the frozen artifact does not compile
  (three independent probes) while javamop and rv-monitor exit 0.
- **BETA-SET-04 → crítica** (FEN-SET-FAIL-OPEN): the exit-0 masking property
  is real on the production toolchain and the round's artifacts realized it
  (the KGN case is a live instance of exactly the masked class).

Consequence declared, not hidden: this puts batch C's fail-open ledger above
batch B's (BETA-SET-09 family resolved major there). Closed rounds are not
reopened; the inconsistency is **declared and routed to the global judgment
phase (G13 severity ledger)**, with a PROPOSED deviation text for the
researcher in synthesis §8.6 (the judge writes nothing to `fase0/`). The
provisional "53 criticals" figure is superseded by the rev. 2 recount (§8.2).

## REF-D-02 (material) — KGN alias criticality on an unshown-realizable trace — **ACCEPTED; held at major-pending**

Verified by my own execution (`juiz_probe_identity_alias_batchC.txt`): all
six alias spellings (`HMAC-SHA256`, `HMAC/SHA256`, `HMAC-SHA384`,
`HMAC/SHA384`, `HMAC-SHA512`, `HMAC/SHA512`) throw
`NoSuchAlgorithmException` on the harness JVM, and KGN `g1`/`g3` are
`after … returning` events (`KeyGeneratorSpec.mop:40,56`) — on every
platform this audit has measured, the enabling trace cannot occur. §4's
critical criterion ("FP ou FN demonstrável em **trace realizável**") is not
met; the Android-BC resolvability probe is my own declared pendency and I
did not execute it this round (a host-JVM upstream-BC probe would not settle
Android's forked providers, so I decline to substitute it). Applying §3/§4
mechanically:

- **ALFA-KGN-04 crítica → major**; **GAMA-KGN-03: the rev. 1 upgrade to
  crítica is withdrawn — held at major** (its filed severity). Position FAIL
  and classification INCORRETA stand: the constraint transcription diverges
  from the raw oracle at the artifact level regardless of realizability, and
  S17 remains a monitor-level acceptance fact.
- The **SSL folding half is untouched**: ALFA-SSL-09 stays crítica — S15a
  used a real, resolving `SSLContext.getInstance("tls")` (re-confirmed in my
  probe).
- Severity returns to crítica in the global phase if the BC probe shows the
  aliases resolve on the Android providers (pendency named in §8.5).

I also record the refuter's strengthening finding under FEN-KGN-KEYSIZE-
OMITIDA: `i1` is a **before** event (`KeyGeneratorSpec.mop:75`), so the
keySize FN fires before the platform's own exception — the criticality of
that phenomenon is *more* solid than my "magnitude context" note implied.

## REF-D-03 (material) — KST Entries: the displacement half is also reading-conditional — **ACCEPTED; both claims → INCONCLUSIVE**

The refuter's reading-(b) analysis is correct and I adopt it: if
declared-but-unordered events are outside the automaton's alphabet, the
trace `load, skE1, store` projects to `load, store`, the raw oracle itself
flags it at `store` (no `sE` before `Stores`), and the monitor's S9a record
is **correctly placed** — no FP, no FN, no displacement; the spec's silence
on `skE1` matches the oracle's indifference. My rev. 1 sentence "the
displaced-accusation half holds under either reading" was wrong.

On the coordinator's question — can the reading be adjudicated from the
frozen grammar? **No.** I re-read `fase0/upstream_CrySL_e92f5607.xtext`: it
defines the syntax of `EVENTS`/`ORDER` (Order/Sequence/Alternative
productions, lines 103–121 — the D-piloto-1 evidence) and nothing in it
fixes the *semantics* of an event label that is declared and aggregated but
absent from ORDER; that is a property of the CogniCrypt/CryptoAnalysis
typestate construction, which is not in this audit's frozen toolchain and
was not verified at source. D-piloto-1 resolves comma precedence only.
Therefore the §3 bindings INCONCLUSIVE criterion applies verbatim ("não
determinável por leitura + execução"):

- **ALFA-KST-04 and GAMA-KST-05: FAIL → INCONCLUSIVE** (rev. 2), outside all
  denominators, with the oracle-semantics resolution as the named pendency.
  The executed facts (silence at the Entries calls; accusation at store)
  stay on the record awaiting the reading. INCONCLUSIVE is not approval.
- Effects: resolutions 55/71/8; KST score 43.29 → **44.00** (INCOMPLETE, 3
  INC); aggregate 43.61 → **44.02**; FEN-KST-ENTRIES-OMITIDAS leaves the
  FAIL per-phenomenon table (26 groups) and moves to the pendency list. KST
  G4/G5 grounds are restated without it — both gates FAIL on independent
  criticals (unbound `ks`, 2-arg Gets omission, nested-type unweaving), as
  the refuter verified.

## REF-D-04 (material) — cross-round G5 threat undeclared — **ACCEPTED; declared, with the grep executed**

The declaration is owed and is now made (synthesis §8.4). I executed the
textual sweep over the 18 non-batch-C `jca_android` specs
(`grep -n "(String, \.\.\|, \.\.))"` and `grep -n "args("` over
`rvsec-mop/src/main/resources/jca_android/*.mop`; nested types via
`grep -n "^import" | grep -E "\.[A-Z][A-Za-z]+\.[A-Z]"`):

- **Trailing `..` with args() narrower than the expansion** (the KMF/TMF
  divergence shape): occurs in **no batch A or batch B spec**. It occurs in
  `CipherSpec.mop` (pilot) only in the non-narrowing form `args(x, ..)` —
  ajc also fires on every expanded arity, so no divergence — and in
  **`SecureRandomSpec.mop` (batch D) twice in the narrowing form**: g2
  `call(getInstance(String, ..)) && args(alg, *)` (`:62-63`, exact-2) and g4
  `call(getInstance(String, ..)) && args(alg)` (`:76-78`, exact-1) — both
  will diverge ajc×dexlib2 exactly as KMF/TMF g2 does.
- **Nested types in pointcuts**: only `KeyStoreSpec.mop` (this batch)
  imports `Outer.Inner` types; no batch A/B exposure.

Consequence, stated precisely: the batch A/B single-half G5 PASS rows (batch
A's production-matcher partitions; batch B's KPR/PBK dexlib2-half PASSes) do
**not** contain either demonstrated divergence mechanism, but they now carry
the *generic* threat that the two halves are proven capable of disagreeing —
their PASSes remain single-half evidence, not equivalence evidence. Closed
rounds are not reopened; the threat is routed to the **global judgment
phase** alongside the standing android-37.0 default-jar pendency, and the
concrete SecureRandomSpec instances are flagged to the batch D reviewers
(whose inputs are already frozen — this flags reviewers, not the generator).

## REF-D-05 (minor) — G2 interpretation undeclared — **ACCEPTED; declared**

The interpretation is now stated in §8.3 as the G5-style scope decision it
should have been: *"geração limpa" is read to include the generated
artifact's standalone compilability; a monitor javac rejects is a "relevant
error" of the generation output that the generators failed to surface (the
round manifest's own caveat: exit 0 guarantees nothing); pilot GCM is
distinguishable (its degenerate artifact compiled).* KGN G2 FAIL stands
under this declared reading; KGN's verdict does not depend on it
(G3/G4/G5/G7/G9 all FAIL independently).

## REF-D-06 (minor) — fresh-instance premise was inferred — **ACCEPTED; evidence upgraded**

Fair on the evidence label — the workspace's own standing rule is
verification by source or execution. Now executed twice: the refuter's probe
and my own (`juiz_probe_identity_alias_batchC.txt`: two
`KeyGenerator.getInstance("AES")` calls and two
`TrustManagerFactory.getInstance("PKIX")` calls return distinct references).
The BETA-KGN-04 overturn stands with its justification rewritten to cite the
executed evidence (rev. 2 CSV); the provider caveat remains a note.

## REF-D-07 (minor) — "same executed records" overstated for KGN — **ACCEPTED; reworded**

Verified: Gama's `kgn_a` is `g3, gk1` (2 records) while Beta's KGN route and
my S4 include `i1` (3 records). The unification ground of record is
rewritten (§8.4): *identical record structure at the pairing call (specific
error + InvalidSeq, same call, same `__LOC`); traces differ in the
mandatory-successor leg.* The 15-claim FEN and its criticality are
unchanged (the refuter agrees the mechanism is one).

## REF-D-08 (minor) — dimension-5 route coverage undeclared — **ACCEPTED; declared**

REF-B-09 statement, now in §8.4: KST had true multi-route dimension-5
coverage (Beta ×2 executed, Gama ×2 executed, judge S6/S7); KGN/KMF/TMF/SSL
dimension-5 verdicts rest on Beta's per-object lifecycle rows plus executed
isolation scenarios (kgn_b, S18c, SSL-e conferred) — two routes, no
contradiction found; **Alfa filed no KST lifecycle claim and its report's
dimension-5 statements for KST were wrong** (erratum §2.5) — so for KST the
reading route contributed nothing and the executed routes carried the
resolution alone. Declared, not repaired retroactively.

---

**Summary of record changes (rev. 1 → rev. 2)**: 5 severity values
(ALFA-KGN-09 ↑, GAMA-KGN-01 ↑, BETA-SET-04 ↑, ALFA-KGN-04 ↓, GAMA-KGN-03 ↓),
2 resolutions (ALFA-KST-04, GAMA-KST-05 → INCONCLUSIVE), 2 justification
rewrites (BETA-KGN-04, plus the five above). Totals: 55 PASS / 71 FAIL / 8
INCONCLUSIVE; **54 critical FAIL claims; 17 phenomena with ≥1 critical; 26
FEN groups with FAILs**. Scores: KST 44.00, aggregate 44.02 (both
INCOMPLETE); all other unit scores byte-identical to rev. 1. No verdict, no
gate, no other score moved. Final decision: `juiz_sintese_batchC.md` §8.
