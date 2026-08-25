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

## The corpus moved during implementation — measured, not assumed (2026-08-24)

The risk register said `jca_android` moves under the component, and it did, mid-change. **This is the
authoritative stamp note for every group; do not re-derive it.**

- `HEAD` at change opening: `39b000ce`. `HEAD` while G00–G04 ran: **`78b3f5e3`** (three `gh104`
  commits landed from another session). The `.mop` corpora and `data/jca_android/` are **clean in the
  working tree** against `78b3f5e3`, so on-disk == committed: the commit × worktree split that cost
  the previous round (learning nº 15) does **not** apply here. Counting rule: `git diff --stat HEAD --`
  over both paths returned empty.
- **All eight targets are pinned at `5fbe8173`, and `5fbe8173` is an ancestor of HEAD, not HEAD.**
  Between them, `5bc5c893` rewrote **13 of the 24 `jca_android` specs**.
- **What the move did *not* touch — measured, per spec, by diffing the `ere`/`fsm` line at both
  commits:** the order formulas of `KeyGeneratorSpec`, `MessageDigestSpec`, `SignatureSpec`,
  `SecureRandomSpec`, `CipherSpec` and `IvChainJunction` are **byte-identical** at `5fbe8173` and at
  `78b3f5e3`. So **M2 is unaffected** and G10 10.10/10.11 stand as written.
- **What the move *did* touch: the idiom-A allow-lists** — `5bc5c893` is the D-15 value-oracle
  re-anchoring, and its edits are `Arrays.asList(...)` literals (e.g. `MessageDigestSpec` lost `MD5`,
  `SHA-224` and `SHA-1` and gained the three expert-validated digests plus spelling variants).
  That is **exactly M3's subject**, so the **M3 numerator must be measured at `78b3f5e3` or later and
  stamped there** — a numerator carried from `5fbe8173` describes a corpus that no longer exists, and
  the committed `constraint_table.csv` (`api30`-anchored) is now **two** corpus states stale.
- **File counts are unchanged** at both commits — `jca` 23, `jca_android` 24,
  `jca_android_bug_predicate` 23, `generic` 118, `generic_new` 27, total **215** — so targets 1, 2
  and 3 are not at risk from this move.
- **HEAD moved twice more while G06–G09 ran**: `78b3f5e3` → `6192b57a` (four further `gh104`
  commits). The `.mop` corpora stay **clean in the working tree** against `6192b57a`, and the oracle
  repository `rvsec-cognicrypt` is at **`f2f4d3b`** — a separate clock, which is exactly why D-17
  makes the stamp per corpus. G07 measured at `6192b57a` × `f2f4d3b` and the pinned pairing figure
  carried unchanged, as predicted: the `Arrays.asList` rewrite touched no event declaration.

### Target 6 needs a rule the invariant does not state: pairing is **injective**

Measured at G07 closure. `IvChainJunction.mop:67` declares `IvChainJunctionSpec(Cipher c)` and
`CipherSpec.mop:47` declares `CipherSpec(Cipher c)` — **byte-identically the same declared type**. A
plain declared-type *function* therefore pairs both with `Cipher.crysl` and yields **23 of 24**, not
the pinned 22. The only reading that reproduces 22 — and that simultaneously makes the proposal's
other figure, "12 of the 22 paired **rules**", true — is that **a rule is the oracle of at most one
specification**. The tie-break must stay signature-derived, never name-derived: the rule goes to the
specification covering more of its declared signatures, then more events, then lexicographic. The
loser is not dropped silently; it is reported as unpaired with the winner named.

**Artifact debt:** INV-CONF-11 states pairing "by declared type" and does **not** state injectivity or
the tie-break. It must be amended via `/opsx:update` (G14 14.7-bis) — a target that only reproduces
under an unwritten rule is not a calibrated target.

- G14 14.5 requires re-running the eight targets at the closing HEAD anyway. **Re-measure and record
  the new stamp beside the target's own stamp (12.5); do not assume a target carried.**

### `101/71` and `117/87` are unreproducible, and one of them is impossible (12.10 route)

`spec.md` §M3 and task 8.6 state that under other counting rules the corpus gives `101/71`
(splitting `&&`) or `117/87` (splitting the sides of `=>`). **Neither reproduces, and `101` cannot be
right in principle**: splitting a clause can only *raise* a count, so an `&&`-split total below the
unsplit R1 total is impossible.

Measured by **three independent routes** that agree digit for digit — G08's text route, G08's façade
route (`47/47` rules that load; façade `114 + 5` for the two that do not parse `= 119`), and the
orchestrator's raw-text Python count over the 49 files on disk (neither parser involved):

| rule | total (49 rules) |
|---|---|
| **R1** — one clause per `;`, comments removed, `&&` **not** split | **119** |
| splitting `&&` (6 occurrences inside `CONSTRAINTS`) | **125** |
| splitting the sides of `=>` (26 occurrences) | **145** |

**Hypothesis, recorded as a hypothesis and not as a result:** the published pair was probably measured
over the abandoned `api30` corpus, which deletes clauses relative to upstream — that is the only way a
split total lands *below* 119. It is not worth chasing: D-06 abandoned that oracle, and 12.10 says a
target unreproducible under **any** written rule is recorded as unreproducible, with the component's
own value published beside its own rule. **Artifact debt:** the two figures must be corrected or
withdrawn in `spec.md` via `/opsx:update` (G14 14.7-bis).

## Tasks

- [x] 12.0 **Reconcile the two pairing implementations before any target is asserted.** G07 built
  `core/metric/SpecRulePairing.java` — declared type, **injective**, signature-derived tie-break —
  and reaches the pinned **22 of 24**. G09's `M4Predicates` does **not** call it (verified: no
  reference to `SpecRulePairing` in the file); it uses its own simple-name approximation and reaches
  **23**, because `IvChainJunction.mop` declares `Cipher` and a non-injective rule lets it claim
  `Cipher.crysl` alongside `CipherSpec`. G09 declared the approximation rather than hiding it, so
  this is integration debt, not a defect of that group — but **M1 and M4 currently report over
  different pair sets**, and a report whose two metrics disagree about which specifications were
  compared cannot be published. Make `M4Predicates` consume `SpecRulePairing`, re-measure every M4
  aggregate on the 22-pair set, and record the before/after so the shift is visible rather than
  silent. Then assert in a test that **every** metric pairs through the one implementation.

- [x] 12.1 `calibration/CalibrationTargets.java` — the eight targets as data, each with **its value, its counting rule, and the repository and commit its own route was taken at**. A target without its counting rule is not a target; it is a number. The stamp is per route, not per run: the oracle corpus lives in a repository other than `rvsec`, and `android.jar` carries an API level and file hash rather than a commit.
- [x] 12.1-bis For each target, record **the route** and assert in a test that the route is not a rule the component implements. A target whose route is the component's own rule cannot fail and must be reclassified as a self-consistency check (RISK-006).
- [x] 12.2 `calibration/CalibrationGate.java` — runs after a full `compare` and checks all eight. It **reports**; it does not reconcile.
- [x] 12.3 `CalibrationMismatch` carries **both** measurements, **both** counting rules, and the differing items named individually — not just the aggregates. "4 versus 5" is unactionable; "these four, and the fifth is `KeyStoreSpec`" is a finding someone can adjudicate.
- [x] 12.4 A mismatch **stops publication of the affected metric** and does not stop the others. One wrong metric should not suppress seven right ones, and one right metric should not license a wrong one.
- [x] 12.5 The gate emits, per corpus, the stamp it ran at **and** the stamp the target's route was taken at, side by side. When they differ, that is the first thing to check and it must not require archaeology. One column for the whole run would hide exactly the case that matters — the `rvsec` checkout moving while `rvsec-cognicrypt` did not.
- [x] 12.6 `CalibrationGateTest` — all eight targets reproduced at their pinned per-repository stamps, each asserted with its counting rule as data rather than only in the failure message.
- [x] 12.7 `test_inv_conf_14_mismatch_reported` — inject a deliberately wrong value into one target and assert the gate throws with both measurements, both rules and the named items, and that the other seven metrics still publish.
- [x] 12.8 Add the gate to the CLI as the `calibrate` subcommand (G05 task 5.2), runnable on its own so a corpus move can be checked without a full comparison run.
- [x] 12.8-bis Target 8 needs a monitor generation pass (`rv-monitor-generator` over the 24 `jca_android` specs into scratch) and the comparisons of targets 4, 5 and 6 need the oracle repository; target 7 (`Binding.java`, `.mop` corpus only) is fully reachable in CI. Mark the oracle- and generation-dependent tests with the CI-exclusion tag from G05 5.11 and document the local setup — otherwise the split from G05 leaves them silently unrun rather than declaredly local.
- [x] 12.9 **Record the adjudication of every real disagreement** in `docs/` — both measurements, both counting rules, and which side was right and why. A disagreement resolved silently is indistinguishable from a component tuned to agree, and six months later nobody can tell them apart.
- [x] 12.10 If a target proves unreproducible under **any** written rule — as happened in Phase 0 with `129`, `12 of 23`, `10/26` and `28 of 55` — record it as unreproducible and publish the component's value **with its rule**, rather than chasing a rule that was never written down.
- [x] 12.11 `mvn -f rvsec/rvsec-crysl/pom.xml test` green with the calibration suite enabled.
  **Adjudicado por medição (24/08):** o falso verde é `mvn -pl rvsec/rvsec-crysl -am test`, que
  seleciona só o pom agregador (0 testes, BUILD SUCCESS). `-pl` apontado a um filho `jar` funciona
  — `-pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` rodou 58. Registre sempre a contagem
  `Tests run:`, nunca o código de saída.
  **Not** `mvn -pl rvsec/rvsec-crysl -am test`, which is what this task said until G00 measured it:
  `-pl` selects the aggregator alone and `-am` adds only its ancestors, never its children, so that
  command reports `BUILD SUCCESS` over three pom modules with **zero** surefire executions. Measured
  at G00 closure: the `-pl … -am` form printed no `Tests run:` line at all; the `-f` form ran 17.
  Record the executed test count beside the green, never the exit code alone.

## Closing
G12 closes when **12.0** and 12.1–12.11 are `[x]`, including 12.1-bis, 12.8-bis (aprendizado nº 18). **A closed G12 with an unadjudicated mismatch is the one
failure this whole change is designed to prevent.**

## O que foi medido no fechamento (24/08/2026)

**Os oito alvos reproduzem.** Zero em estado *mismatch não adjudicado*, que é a condição de
fechamento do RISK-005. As oito rotas foram **re-executadas no HEAD** (`rvsec` `6192b57a`,
`rvsec-cognicrypt` `f2f4d3b`) em vez de presumidas: nenhuma derivou. A adjudicação completa —
as duas medições, as duas regras de contagem e o lado certo de cada divergência — está em
`rv-android/docs/20260824_adjudicacao_calibracao_gh106.md` (12.9).

| # | alvo | rota | componente | veredito |
|---|---|---|---|---|
| 1 | leitura dos cinco corpora | `215 files, 215 ok, 0 fail` | idem | PASS |
| 2 | multi-parâmetro em `generic` | `93 de 118` + *buckets* | idem | PASS |
| 3 | multi-parâmetro em `jca_android` | `0 de 24` | idem | PASS |
| 4 | regras que carregam | `47 de 49` | idem | PASS |
| 5 | denominador do M3 sob R1 | `80 de 119` | idem (fachada CrySL) | PASS |
| 6 | pareamento | `22 de 24` | idem (injetivo) | PASS |
| 7 | ligação parcial | `5 de 22` | idem | PASS |
| 8 | sem `MapOfMonitor` | `5 de 24` (monitores regerados) | idem (proxy da AST) | PASS |

**12.0, antes e depois** (mesmo corpus, mesmo commit): pares `23 → 22`, present `50 → 44`,
absent `53 → 44`, inverted `0 → 0`, linhas `123 → 106`, derivadas `103 → 88`, fração derivada
`0,837 → 0,830`. As nove cláusulas que saem de `absent` eram a contagem dupla de `Cipher.crysl`,
uma vez contra `CipherSpec` e outra contra `IvChainJunction`.

**Duas divergências reais, adjudicadas e não afrouxadas:** (a) as duas implementações de
pareamento — `SpecRulePairing` está certo; (b) a tabela do M3 omite `HMACParameterSpecSpec` e
`KeyPairSpec`, o que **não** é divergência de pareamento (as duas regras pareadas têm
`CONSTRAINTS` vazio), e a asserção passou a nomear as duas ausências em vez de tolerar a
diferença.

**Consequência do 12.8:** ligar o `calibrate` deixou `NotWiredException` e `ExitCode.NOT_WIRED`
sem produtor. Pelo P3 os dois foram removidos, com cópia em `backup/gh106/`, e o teste do CLI que
os exercia foi reescrito para a checagem que continua valendo.

**Contagens executadas** (`mvn -o -f rvsec/rvsec-crysl/pom.xml test`, com
`RVSEC_GENERATED_MONITOR` apontado para os monitores regerados): `-core` **166**, `-mop` **58**,
`-crysl` **100**, zero falhas e zero *skips*. Sem a variável, o teste da rota do alvo 8 pula
nomeando o caminho que faltou.
