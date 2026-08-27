# G7 — Verification (single session per milestone)

The battery has a fixed cost per pass (design D-22): batch everything, run once per milestone.
Java lines carry the JDK 21 prefix; monitor generation is inspected as an artifact (INV-INS-145).

## 7.1 [M1] Full battery over the enlarged set

1. Reactor build: `mvn clean install -DskipMopAgent -DskipTests` (~53 s) — the gh106 Maven tests
   with the 6.1 constants must be green (`rvsec-crysl` module tests).
2. **[GEN]** regenerate the `jca_android` monitor (77–79 s, ~5 GB peak); inspect the artifact:
   every new spec present, line count recorded.
3. `RVSEC_HOME=<reactor> uv run pytest tests/parity --import-mode=importlib -o "addopts="` — all
   gates green: gh104 structural (G-2/G-2a/G-ERE/G-6'/lint/message/G-CONF), gh105 predicate
   (INV-INS-130/133/134, G-ACC, G-PRED2, placement census), G-PARAM (over the 0.3 fixture, 0 skips),
   G-ORDER (new specs compared, not skipped), gh101 freeze (untouched `jca`/`ExecutionContext`/
   `CipherTransformationUtil`), coverage-matrix test (0.4).
4. Record `--check`s (seconds each): divergence, ledger, conformance, alphabet, sole-oracle.
5. Manual gates: `gh105_spec_gates.py --sets jca_android` (G-SIG/G-FORB/G-BIND; needs
   `ANDROID_HOME` android-30).

## 7.2 [M1] Milestone assertions

- Ledger, producer side: `preparedRSA`, `preparedEC`, `preparedDSA`, `preparedOAEP`,
  `generatedManagerFactoryParameters` and `preparedDH` no longer `unmonitored-producer`
  (`preparedAlg` closes after G3; `preparedKeyMaterial` fully after 4.3 — INV-INS-151 counts all
  eight).
- Ledger, consumer side (D-24): every predicate the set writes is read at a consuming site or carries
  a recorded impossibility. Concretely, after G1b: `preparedRSA`, `preparedDSA` and
  `generatedManagerFactoryParameters` have live read sites; `Cipher.crysl:136`'s `preparedAlg` carries
  its deferral row (ceiling 17/17, `i2` binds no `params`). A predicate written by a new specification
  and read by nobody fails this assertion.
- Transitory dispositions, enumerated rather than absent. G3 is M2 work, so the
  `unmonitored-consumer` 1.R wrote on the three `MessageDigestSpec` write rows is **legitimately
  still standing at M1**. What is asserted here is that each one is named, with the task that owes
  its retirement (3.R), and that no *other* row acquired one. The assertion that none survived is
  7.3's, at M2.
- Coverage matrix: every G1/G2-landed rule `covered`; no rule with zero or two states among the
  landed tiers.
- Run `/rv-verify` on the touched Python surface (scripts/, tests/parity/).

## 7.3 [M2] Final: harness checkpoint 2 + complete matrix

1. `gh104_diff_harness.py` — post-M2 set vs the pre-gh109 preimage over the 178 traces + the trace
   pairs added by 1.R/2.R/3.R/4.3; every `introduced/removed/moved` classified and attributed to its
   group; evidence committed.
2. Re-run the full 7.1 battery.
   - Including the assertion 7.2 could not make: **no transitory disposition survived its reason**,
     in `predicate_graph.csv` or in `predicate_ledger.csv`. Concretely, the three `MessageDigestSpec`
     write rows no longer carry `unmonitored-consumer`, and no write row carries an `omission` whose
     recorded reason a landed consumer falsified (D-24).
3. Coverage matrix complete: **49/49 terminal states** over the three values (covered / na-platform /
   na-value), each with evidence, and `oracle_defect_row` filled by the join on `kind = oracle-wart`
   — the master question answers *yes, or adjudicated*. Remember what the column asserts: pairing and
   adjudication, not clause completeness (INV-INS-150).
4. **NOBS census of the G1b sites**: read the NOT_OBSERVED rate of each read opened by D-24 over the
   APK corpus and report it per site. The NOBS branches are provisional until this number exists; the
   researcher decides here whether any of them retires to a recorded silence.
5. Check off the satisfied acceptance criteria on issue #109 (`- [x]`), per the closing protocol.

## 7.4 [M2] Run `/rv-qa-lint-fix`

On touched Python (scripts/, tests/parity/).

## 7.5 [M2] Run `/rv-verify`

Tests + lint + types on the same surface.

## 7.6 [M2] Run `/rv-code-reviewer`

Via the Skill tool: "Review gh109-crysl-coverage implementation". Then the FF SDD Close phase:
`/opsx:verify` → `/opsx:archive` (archive order: gh105 first — design Risks). Final commit
`closes #109`; move the Kanban card to Done.
