# Calibração do frontier boost — gh77 (task 7.7)

**Data**: 2026-07-13 · **Change**: gh77-revive-rvagent · **APK**: cryptoapp (br.unb.cic.cryptoapp)
**Ambiente**: emulador gerenciado pelo rv-platform, timeout 60s, braço `pure_algorithm` (sem LLM).

## Objetivo

A task 7.7 exige um *smoke* de calibração local, obrigatório antes de qualquer comparação com o
aperv, para medir a interação entre os dois pesos de *frontier boost* aditivos e congelar os pesos
de um braço de steering. Este documento registra o resultado e os pesos escolhidos.

## O par de frontier (Decisão E resolvida)

Não existe campo `frontier_boost_weight` no `RVAgentConfig`. O par genuíno de dois pesos aditivos é:

- **Frontier MOP-estreito** — `MopFrontierScorer`, peso `mop_frontier_weight`. Adiciona o boost
  quando a ação leva a uma *activity* que atinge operação monitorada (`activity_has_mop`) **e** ainda
  não foi visitada.
- **Frontier genérico** — `WtgScorer`, peso `wtg_guided_score`. Adiciona o boost em transições
  guiadas pelo WTG rumo a qualquer tela não visitada.

O docstring do `MopFrontierScorer` é explícito: ele "combines additively with the generic frontier /
WTG boosts". Logo o par calibrado é `mop_frontier_weight` × `wtg_guided_score`.

## Substrato MOP no cryptoapp

A fonte real de alcançabilidade MOP é `reachability[].methods[].reachesTarget/directlyReachesTarget`
(a fonte widget/método que `activity_has_mop` usa), **não** `components.activities[].reaches_target`
(fonte A′ opcional, vazia neste APK).

- 3 *activities* MOP-reaching: `CipherActivity`, `CryptographyActivity`, `MessageDigestActivity`.
- 32 métodos `reachesTarget`, 21 `directlyReachesTarget`, ligados a *handlers* de clique nos widgets.
- 0 serviços/receivers MOP-reaching → censo do component-trigger esparso → E-ext deferido (decisão do
  usuário; não reaberto nesta sessão).

## Runs comparados

| Braço | Pesos | Estados | `decision_source` no trace | Interação frontier |
|---|---|---|---|---|
| pure (7.6) | tudo off (`pure_mode`) | 3 | `coverage` 17/17 | nenhuma (0 steering) |
| frontier (7.7) | `mop_frontier=200`, `wtg_guided=150` | 5 | `coverage` 16, `wtg` 3 | boost `wtg` = **350 = 200 + 150** em *activities* MOP não visitadas |

Diretórios: pure = `results/cli_experiment_20260713_113554_621d851f`;
frontier = `results/cli_experiment_20260713_115925_0b56f7d5`.

## Leitura da interação

Em uma transição para uma *activity* MOP-reaching **não visitada**, os dois scorers disparam e somam
350; para uma *activity* genérica não visitada, apenas o `WtgScorer` dispara (150). O delta de +200 é
a separação de steering pretendida (frontier MOP priorizado sobre o frontier genérico). Não há
*double-counting* indevido — a soma aditiva é o design (o `MopFrontierScorer` é estritamente mais
estreito que o `WtgScorer`). O braço frontier explorou 5 estados vs 3 do braço puro, alcançando
`CipherActivity` e `MessageDigestActivity` diretamente pelo boost `wtg`.

## Pesos congelados

- `mop_frontier_weight = 200`
- `wtg_guided_score = 150`

Magnitude canônica do frontier no aperv; produz a separação limpa 350-vs-150 (MOP vs genérico)
observada acima. Congelados no braço arm-neutro **`mop_frontier`** em
`RVAgentTool.get_variants()` (`pure_algorithm` base, sem LLM, demais flags de steering off).

## Censo MOP e E-ext

Censo de componentes MOP-reaching não-activity em `apks_examples/` (só cryptoapp): 0 serviços,
0 receivers. O component-trigger nunca dispara neste dataset. A condição de reabertura do E-ext
(flag `arm_defining` própria `component_trigger_exported`) está satisfeita, mas foi **deferida** por
decisão do usuário — é um campo `arm_defining` novo (dispara INV-AGT-43) fora do escopo do Grupo 7.
