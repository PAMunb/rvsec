# G12 · corpus calibration — the gate that stops the component being born wrong

**Depends on:** G04, G05 and G06–G11. **Blocks:** G13b, G14.
**Parallel with:** nothing. This is the integration point.
**Size:** ~3 files plus the target fixtures.

The component is a measuring instrument. An instrument that ships without calibration publishes
numbers that look like measurement and are not — which is precisely the failure mode the capability
exists to remove. G12 makes the component **reproduce numbers already measured by another route**
before its output is treated as measurement.

**The rule that governs this group: a disagreement is a finding, not a tuning signal.** The cheapest
way to pass a calibration gate is to break the instrument until it agrees. INV-CONF-14 forbids it.

## Reference
- `specs/conformance/spec.md` — "Calibration against Independently Measured Targets", INV-CONF-14
- `design.md` D-13
- Independent routes: `docs/handoff/20260824_arnes_adjudicacao/` (probes `Census.java`, `Binding.java`, `V3Fresh.java`; the two independent R1 implementations) and the committed CSVs

## The eight targets — value, route, and the stamp of **that route's own repository**

All `rvsec`-side values are at `5fbe8173`; the oracle-side routes carry the commit of
`rvsec-cognicrypt`, a separate repository that moves on its own clock.

| # | Target | Value | Independent route |
|---|---|---|---|
| 1 | `SpecExtractor` over the five corpora | `215/215 ok, 0 fail` | `Census.java` |
| 2 | multi-parameter in `generic` | `93`, buckets `{1:25, 2:39, 3:28, 4:18, 5:7, 6:1}` | `Census.java`, and an earlier independent count |
| 3 | multi-parameter in `jca_android` | `0 of 24` | `Census.java` |
| 4 | upstream rules that load, fresh reader per rule | `47 of 49` (the two failures being `OAEPParameterSpec` — reserved word `alg` — and `SSLEngine` — `ORDER` references `cp1`, declared `ep1`) | `V3Fresh.java` |
| 5 | M3 denominator under R1 | `80` clauses in the 22 paired upstream rules (`119` across all 49); the numerator is remeasured, with the four `MOP-SEM-BASE` rows re-examined against upstream | the two independent R1 implementations in the harness; the committed `constraint_table.csv` (`25/55`, `api30`-anchored human judgement over `jca_android`) stands only as a **labelled historical reconciliation** |
| 6 | `.mop` ↔ rule pairing by declared type | `22 of 24` | the two unpaired specifications named in the `disposition` column of `order_alphabet_map.csv` (re-anchored to `.crysl` by its producing component) — **not** the component's own pairing rule |
| 7 | partial parameter binding | `5 of 22` | `Binding.java` |
| 8 | specifications without `MapOfMonitor` | `5 of 24` | **the regenerated monitors**, read for the presence of a `MapOfMonitor` — **not** the AST proxy, which the component implements |

> **Corrigido depois do `/rv-risk` (RISK-006).** Dois destes oito estavam escritos de forma que o
> portão **não podia falhar**: o 6 pareava "por nome", que é exatamente a regra que o componente
> aplica, e o 8 lia o proxy da AST, que é exatamente o que o componente implementa. Calibrar contra a
> própria regra não é calibrar. Os dois passaram a apontar para rotas que o componente **não produz**
> — o alvo 8 ao custo de uma passagem do `rv-monitor-generator`, que é o preço da única versão dessa
> checagem capaz de dar errado. **Regra geral: uma grandeza sem rota independente sai como
> *checagem de consistência interna*, rotulada como tal, e não conta como alvo de calibração.**

## Tasks

- [ ] 12.1 `calibration/CalibrationTargets.java` — the eight targets as data, each with **its value, its counting rule, and the repository and commit its own route was taken at**. A target without its counting rule is not a target; it is a number. The stamp is per route, not per run: the oracle corpus lives in a repository other than `rvsec`, and `android.jar` carries an API level and file hash rather than a commit.
- [ ] 12.1-bis For each target, record **the route** and assert in a test that the route is not a rule the component implements. A target whose route is the component's own rule cannot fail and must be reclassified as a self-consistency check (RISK-006).
- [ ] 12.2 `calibration/CalibrationGate.java` — runs after a full `compare` and checks all eight. It **reports**; it does not reconcile.
- [ ] 12.3 `CalibrationMismatch` carries **both** measurements, **both** counting rules, and the differing items named individually — not just the aggregates. "4 versus 5" is unactionable; "these four, and the fifth is `KeyStoreSpec`" is a finding someone can adjudicate.
- [ ] 12.4 A mismatch **stops publication of the affected metric** and does not stop the others. One wrong metric should not suppress seven right ones, and one right metric should not license a wrong one.
- [ ] 12.5 The gate emits, per corpus, the stamp it ran at **and** the stamp the target's route was taken at, side by side. When they differ, that is the first thing to check and it must not require archaeology. One column for the whole run would hide exactly the case that matters — the `rvsec` checkout moving while `rvsec-cognicrypt` did not.
- [ ] 12.6 `CalibrationGateTest` — all eight targets reproduced at their pinned per-repository stamps, each asserted with its counting rule as data rather than only in the failure message.
- [ ] 12.7 `test_inv_conf_14_mismatch_reported` — inject a deliberately wrong value into one target and assert the gate throws with both measurements, both rules and the named items, and that the other seven metrics still publish.
- [ ] 12.8 Add the gate to the CLI as the `calibrate` subcommand (G05 task 5.2), runnable on its own so a corpus move can be checked without a full comparison run.
- [ ] 12.8-bis Target 8 needs a monitor generation pass (`rv-monitor-generator` over the 24 `jca_android` specs into scratch) and the comparisons of targets 4, 5 and 6 need the oracle repository; target 7 (`Binding.java`, `.mop` corpus only) is fully reachable in CI. Mark the oracle- and generation-dependent tests with the CI-exclusion tag from G05 5.11 and document the local setup — otherwise the split from G05 leaves them silently unrun rather than declaredly local.
- [ ] 12.9 **Record the adjudication of every real disagreement** in `docs/` — both measurements, both counting rules, and which side was right and why. A disagreement resolved silently is indistinguishable from a component tuned to agree, and six months later nobody can tell them apart.
- [ ] 12.10 If a target proves unreproducible under **any** written rule — as happened in Phase 0 with `129`, `12 of 23`, `10/26` and `28 of 55` — record it as unreproducible and publish the component's value **with its rule**, rather than chasing a rule that was never written down.
- [ ] 12.11 `mvn -pl rvsec/rvsec-crysl -am test` green with the calibration suite enabled.

## Closing
G12 closes when 12.1–12.11 are `[x]`. **A closed G12 with an unadjudicated mismatch is the one
failure this whole change is designed to prevent.**
