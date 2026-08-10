# Refutation review — Batch A judge synthesis (adversarial round, protocol §15)

Independent refutation reviewer, 2026-08-09. Target: `batchA/juiz_sintese_batchA.md`,
`batchA/juiz_claims_resolvidos_batchA.csv` (96 claims), `batchA/juiz_rescore_batchA.py`.
Method: mechanical re-sum re-executed; all 96 claims cross-checked row-by-row against
the three agent CSVs; judge tests J1/J2/J3 independently re-executed by the reviewer;
every §0 self-verification claim sampled against the frozen sources at file:line.
Auxiliary evidence: `refutacao_rescore_rerun.txt`, `refutacao_j1_j2_j3_rerun.txt`.

## 0. What the reviewer executed (basis for this parecer)

1. `python3 juiz_rescore_batchA.py` re-run: **every table in §4 reproduces verbatim**
   (per-spec, SET, aggregate; totals 46 PASS / 48 FAIL / 2 INCONCLUSIVE = 96). Output:
   `refutacao_rescore_rerun.txt`.
2. CSV cross-check (script, this session): 96/96 agent claim IDs present in the judge
   CSV, none missing, none added; exactly 6 position changes (4 PASS→FAIL, 1 FAIL→PASS,
   1 INCONCLUSIVE→PASS) and 12 severity changes — the 8 declared in §2.2 plus the 4
   that are consequences of §2.1 overturns; **zero dimension re-assignments**
   (D-piloto-4 item 1 honored); all `classificacao_final` values are within the six
   states of `modelo_semantico.md` §7.
3. **J1 re-executed** (`juiz_walk.py`): ALL PASS reproduced, including the HMC
   separating trace under global indexing. **J2 re-executed** (JuizDrive, production
   jars re-hashed: rvsec-core `7b4d72aa`, rvsec-logger-csv `6787f411`, rv-monitor-rt
   `0fa65fbc`): end-to-end DHG FP chain reproduced, including the displaced
   `UnsatisfiedConstraint` at KeyPairGeneratorSpec. **J3 re-executed** (JuizHmc):
   2 CrySL-legal HMC constructions → 1 `InvalidSequenceOfMethodCalls expecting=unknown`,
   `h2 PREPARED_HMAC=false`, reproduced. Output: `refutacao_j1_j2_j3_rerun.txt`.
4. §0 spot-checks (all held exactly as stated): 5 `.mop` + 5 `.cryptsl` sha256 =
   `generation_manifest.md` (10/10 sampled) and 2 artifact hashes incl. DHG monitor
   `90aaf45b` and HMC monitor `adebef51`; HMC static `Tuple2` at
   `HMACParameterSpecSpecRuntimeMonitor.java:212` vs `MapOfMonitor` in DHG `:206`;
   `ErrorDescription.java:34-36` (3-arg → `"unknown"`); `ExecutionContext.java`
   binary `setProperty` (~:102-110) and identity store (~:46-55); android-30 jar
   `96ccfdc8…`, `javax/xml/crypto` entries = 0; `DumpVisitor.java:595-609` prints
   `new`; `TargetResolver.java:53` name-equality match, no `<init>` normalization in
   the client tree (only `SpinnerItemExtractor.java:136`, unrelated);
   `KeyPairGeneratorSpec.mop:91-113` reader bodies; gh101 `README.md:17-18` baseline
   semantics, `conformance_record.csv:5,:21`, `predicate_edges.csv:64-68`,
   `predicate_omissions.csv` PREPARED_PBE/SPECCED_KEY rows, `divergence_record.csv`
   with no DHGenParameterSpecSpec row; `utils.py:41-52` stderr compensation **and**
   (beyond the judge) the two generator call sites
   `runtime_verification_generator.py:217,272` call `execute_command` without
   `skip_stderr` — the compensation covers exactly the BETA-SET-03 path, so the
   major→minor lowering is better grounded than the synthesis itself states.
5. Round harness evidence backing GAMA-IVP-03's conversion re-read at source:
   `alfa_jvm_harness_output.txt:1-5` (T1a-d) and `beta_betadrive_run1.out:25` (IVP-e
   incl. overflow) — both executed inside the round, both answer the realizability
   question on the JVM.

## 1. Objections

### REF-B-01 — Judge's decisive evidence lives only in ephemeral scratch (material)

The synthesis's §7 itself declares: "Judge scratch (**ephemeral**, commands recorded
in §0)". J2 and J3 — the executed tests that overturned four claims (ALFA-HMC-01/05,
ALFA-SET-04, GAMA-HMC-02) and raised BETA-DHG-05 to critical — plus J1 and the
`gen_kpg` generation exist **only** under the session scratchpad, not under
`audit/20260808_validacao_jca_android/`. `fase0/pre_registro.md` §8 requires the
replication package ("outputs brutos citados por arquivo:linha… **Tudo sob**
`audit/20260808_validacao_jca_android/`"). The agents' raw outputs were copied into
`batchA/` (`alfa_*output.txt`, `beta_*.out`, `gama_*output.txt`); the judge's were
not. If the scratchpad is garbage-collected, the round's most consequential new
evidence becomes non-replayable from the audit tree alone.
**Mitigation performed by this review**: J1/J2/J3 were independently re-executed and
their outputs preserved in `batchA/refutacao_j1_j2_j3_rerun.txt`.
**Resolution**: the judge copies `juiz_walk.py`, `JuizDrive.java`, `JuizHmc.java`,
the three outputs, and the `gen_kpg` command record into `batchA/` (as `juiz_*`
files) before the final decision. Does not reach any verdict (the evidence is real —
I reproduced it); reaches the replication gate promise.

### REF-B-02 — Unregistered scoring convention: attainable-weight exclusion ("32.50/95") (material)

The HMC score is published as "32.50 / 95 → 34.21%" and the SET score as
"30.00 / 50 → 60.00%": dimensions with zero claims are **excluded from the attainable
weight** and a normalized percentage is published. Neither `pre_registro.md` §6 nor
any D-piloto deviation registers this cross-dimension aggregation rule; §6 defines
only the per-dimension denominator. The pilot's own script (`pilot/juiz_rescore.py`)
uses the opposite convention — an empty dimension contributes 0 toward an implicit
/100 total. The batch-A convention is *more favorable* to HMC (34.21 > 32.50) and was
adopted after seeing which dimensions lacked claims — precisely the pattern the
pre-registration exists to prevent, and the pilot's REF-06 (partially accepted)
already established that scoring conventions must be registered. Transparency is
good (both raw and normalized numbers are printed), and no score opens a gate, so no
verdict is reached.
**Resolution**: register the convention as a deviation (D-batchA-*) in
`fase0/desvios.md` before batch B, or publish only the raw fraction with the
attainable weight stated.

### REF-B-03 — GAMA-SKS-02 severity contradicts the judge's own classification text and §4 (material)

The judge's `classificacao_final` for GAMA-SKS-02 reads "INCORRETA (mensagens
confladas/garbled; **atribuição por cláusula impossível**)" and SKS G9 is failed on
the pre-registered criterion "atribuição ambígua" — yet `severidade_final` stays
**minor**, with the mitigant "atribuível a spec+sítio". `pre_registro.md` §4 defines
**major** as "diagnóstico inatribuível" and minor as "mensagem subótima, **porém
atribuível**". The judge cannot have it both ways: if attribution per clause is
impossible (his words), §4 places it at major; if it is attributable to spec+site
(his mitigant), the phrase "impossível" overstates. The same judge harmonized
GAMA-SET-08 minor→major expressly to match the phenomenon's severity. Downstream
effect: G13 requires closing all **critical/major** findings after refutation —
at minor, the defect that alone fails SKS's G9 formally escapes the G13 must-close
set. No verdict effect (SKS is REPROVADA via G4/G7 criticals regardless).
**Resolution**: raise GAMA-SKS-02 to major, or rewrite the classification detail to
match the minor definition and state which reading governs G13.

### REF-B-04 — HMC G5 "FAIL*": a hybrid gate state, failed outside the capture criterion (minor)

The HMC gate table records "G5 **FAIL\***" with the footnote that "the pointcut
itself is exact for an app-bundled owner; recorded as oracle bias, **not translation
defect**". Two problems. (i) The gate vocabulary is PASS/FAIL (protocol §16);
"FAIL*" is an unregistered hybrid. (ii) Under the pre-registered capture criterion
(§3: "Esperado ⊆ Capturado e Capturado ∩ Vizinhos = ∅"), a platform where the class
does not exist gives Esperado(platform)=∅, which satisfies the inclusion vacuously;
the FAIL is grounded in oracle-inherited vacuity, which §1 of the pre-registration
says to *register*, not to convert into a spec-side gate failure. No verdict effect
— HMC fails G3/G4/G7/G9 on executed evidence — but the asterisk is doing
unregistered work.
**Resolution**: either G5 PASS with the vacuity carried by the oracle-bias register
(where phenomenon 4 already puts it), or an explicit convention for oracle-inherited
gate failures, registered as a deviation.

### REF-B-05 — §5 preamble misstates the operative gate rule (minor)

§5 opens: "Pilot standard applied: any **critical** INCORRETA/OMITIDA inside a gate
⇒ gate FAIL ⇒ spec REPROVADA." But three verdicts hinge on gates failed by
non-critical claims: IVP G9 (GAMA-IVP-02, major), PBE G9 (GAMA-PBE-02, major), SKS
G9 (GAMA-SKS-02, minor). Those gate FAILs are *correct* — they follow the §3/§16
criteria directly ("nenhum `unknown`", "atribuição ambígua"), and I verified the IVP
`unknown` chain end-to-end (`IvParameterSpec.mop:48,:55` → 3-arg
`ErrorDescription.java:34-36` → artifact `:222/:239`) — but the stated rule is only
a sufficient condition presented as the standard. A reader applying the preamble
literally would mark IVP G9 PASS and IVP APROVADA.
**Resolution**: one-sentence correction: gates fail by their §3/§16 criteria;
critical INCORRETA/OMITIDA is one sufficient trigger among them.

### REF-B-06 — GAMA-IVP-03: "COMPROVADA" without the JVM scope qualifier in the state itself (minor)

The conversion INCONCLUSIVE→PASS is legitimate: the realizability question was
answered by two harnesses executed inside the round (verified: T1a-d;
IVP-e incl. overflow), D-piloto-2 establishes the JVM harness as the round's
instrument, and the ART threat is named and kept. But Gama's INCONCLUSIVE hinged
*expressly* on ART/libcore (`gama_report.md:282-286`), and the final state label
"DIVERGÊNCIA_EQUIVALENTE_COMPROVADA (zona de supressão inalcançável via
after-returning)" carries no scope qualifier — the proof covers the JDK
implementation only; android.jar stubs cannot be executed. Principle §3.7 ("nunca
converta desconhecido em sucesso") argues for the qualifier living in the state
detail, not only in the residual-uncertainty column.
**Resolution**: amend the parenthetical to "(… via after-returning; **provado em
JVM, ART pendente G10**)". No score or verdict effect.

### REF-B-07 — "Three routes converge" repeats the pilot's REF-11 overstatement (minor)

Matrix row 3 (SKS 4-arg REQUIRES drop) says "None — three routes converge". Alfa's
and Gama's routes are readings of the **same frozen `.mop` bytes**; per the pilot's
accepted REF-11 lesson, agreement between two readings of one artifact is one
evidence route, not two. The resolution stands regardless — Beta executed SKS-b/c
and the judge verified `.mop`/`.rvm`/artifact and the unary store himself — so this
is rhetoric, not substance. Same pattern in row 2 ("Beta's executed drive" is the
load-bearing route; Alfa/Gama read).
**Resolution**: count evidence routes, not agents, in the convergence column
(the §3 phenomenon counts already do this for claims).

### REF-B-08 — "LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA" for HMC vacuity: documented by whom? (minor)

Phenomenon 4 classifies the HMC spec-level state as
LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA while the judge's own §0.6 records that
`frozen_set_debt.md` has **0 hits** for `javax.xml.crypto` and GAMA-HMC-01's
resolution confirms "ausência de registro". No pre-existing register (gh101 or
otherwise) documents this limitation; the "documentation" is the audit's own
oracle-bias register, created at resolution time. `modelo_semantico.md` §7's
paradigm is a limitation *registered by GH101*. Calling it "DOCUMENTADA" without
saying the documenter is this round's synthesis invites the misreading that the
omission was deliberate and pre-registered by the change. Inevitability is not
contested; provenance of the documentation is.
**Resolution**: state in §3 that the register is created by this round (researcher
to countersign), or use the state with the detail "(documentada **nesta rodada**)".

### REF-B-09 — Dimension-5 coverage was effectively single-route for 4 of 5 specs; the gap is not declared (minor)

Pilot §8.4 made dimension-5 (parametric/lifecycle) claims "obrigatórios na rodada
das 23". In batch A: Alfa filed dim-5 claims for all five specs (ALFA-DHG-04,
-HMC-05, -PBE-07, -IVP-04, -SKS-08); Beta only for HMC (BETA-HMC-03/SET-02); Gama
none. For DHG/PBE/IVP/SKS the round's lifecycle verdict therefore rests on one
agent's claims plus the judge's post-hoc indexing verification (§0.3) — and the one
spec where a second agent *did* look (HMC) is exactly where the single-route claims
(ALFA-HMC-05 and the premise under GAMA-HMC-02) were **wrong**. The synthesis draws
the process lesson (§6.1-6.2) but never declares that two of three agents produced
no dimension-5 claims for four specs. The mandate text does not say "per agent", so
this is a transparency gap, not a rule breach.
**Resolution**: one declared sentence in §6, and (as the judge already proposes)
the standing two-object test per spec in the next batches.

## 2. Areas attacked that survived (one line each, per checklist)

- **Rescore/denominators**: script reproduces §4 verbatim; per-spec denominators
  contain only that spec's claims; SET separated; 2 INCONCLUSIVE outside; §3 totals
  (46/48/2), 18 critical claims across 7 phenomena, and the 79-claim aggregate all
  re-add correctly. (Except the attainable-weight convention — REF-B-02.)
- **Position changes**: all six grounded in evidence I independently re-executed
  (J3, J1) or verified at source (README:17-18; T1a-d + IVP-e); none by majority;
  no agent-counting language found in any resolution.
- **Severity changes**: BETA-DHG-05→critical grounded in J2 (re-executed; §4
  criterion met); dead-@fail →minor consistent with §4's definitions; BETA-SET-03
  →minor verified beyond the synthesis (call sites `:217,:272` lack `skip_stderr`).
  (Except GAMA-SKS-02 — REF-B-03.)
- **Verdicts vs gates**: no gate marked PASS with an open critical claim in its
  dimension (PBE G5's captura-dimension critical is declared and judged in G4 —
  D-piloto-4 pendency honored); IVP REPROVADA-by-G9-only is criterion-driven and
  the `unknown` chain was verified end-to-end by this review. (Preamble wording —
  REF-B-05.)
- **Counterexamples**: 96/96 claims traced agent-CSV→judge-CSV row by row; 20+
  claims sampled in depth; no reproducible counterexample absent or dismissed
  without an executed or source-verified discriminating test; the only FAIL→PASS
  (BETA-SET-07) is a register-content claim legitimately closed by the register's
  own declared semantics (verified README:17-18).
- **Classification convention**: all 96 final classifications within the six states;
  toolchain-measurement convention (D-piloto-4 item 4) applied consistently
  (BETA-SKS-04 FIDELIDADE / GAMA-SKS-03 INCORRETA is not a contradiction — the two
  claims assert different propositions about the same paren, and both resolutions
  are true of their propositions).
- **Scope honesty**: no G6/G8/G10 conclusions; GAMA-SET-11 historical zero kept
  INCONCLUSIVE and outside every denominator; no absence-of-firing converted into
  acceptance anywhere in the CSV; availability/recommendation/fidelity distinction
  (protocol §3.10) maintained in phenomenon 4 and in the DHG CrySL-1.5.2 anchor
  note.
- **Judge self-verification**: 12+ of the §0 items spot-checked at file:line and
  hash — all held exactly as stated (list in §0.4 above).
- **RandomStringPassword register**: present in the synthesis header, correctly
  framed as researcher scope reduction dated 2026-08-09 and carried to the global
  judgment (`fase0/manifesto.md` inventory section confirms); not treated as
  approval.
- **javap trap**: both Alfa and Beta documented and neutralized it in their own
  work; none of the judge's J1-J3 tests uses javap; the judge's platform checks
  used `unzip -l` on the hash-verified jar.

## 3. Conclusion

Nine objections: **3 material** (REF-B-01 replication-package gap; REF-B-02
unregistered scoring convention; REF-B-03 severity/classification contradiction with
G13 effect), **6 minor** (REF-B-04..09). **None reaches the five REPROVADA verdicts**:
every gate-deciding defect is anchored in evidence that this review independently
re-executed (J1, J2, J3) or verified at source and hash, and the verdict-relevant
criteria applications are the pre-registered ones. **None reaches the raw scores**
(the re-sum reproduces §4 exactly); REF-B-02 concerns the *presentation* of two
scores (HMC normalized 34.21%, SET 60.00%), not their inputs. The judge should
answer each objection before the final decision, per protocol §15; REF-B-01 and
REF-B-02 require artifacts (copies into `batchA/`, a deviation register) rather than
argument.

Reviewer files: `refutacao_parecer_batchA.md` (this parecer),
`refutacao_rescore_rerun.txt`, `refutacao_j1_j2_j3_rerun.txt`.
