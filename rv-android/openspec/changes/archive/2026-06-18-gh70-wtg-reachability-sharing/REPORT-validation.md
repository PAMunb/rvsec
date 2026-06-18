# gh70 — Relatório de validação: **APPROACH NÃO-VIÁVEL** (resultado negativo)

**Data:** 2026-06-18
**Veredito:** O approach do gh70 — pré-computar a reachability forward de todos os nós de alocação **uma vez** (SCC condensation + DP no DAG condensado) e reusar — é **semanticamente inválido**. Foi revertido. gh70 **não vira fix**.

---

## 1. O que se provou

A premissa central do design (D1 / API precondition) — *"the flow graph successor relation is fully built and static for the duration of the pass"* — **é falsa**.

`FlowgraphRebuilder.buildFlowThroughContainer()` chama `graphUtil.reachableNodes(allocNode)` **dentro** do laço `for (Expr e : allNAllocNodes.keySet())`, e cada iteração executa `sn.addEdgeTo(tn)`. Ou seja, **o grafo de sucessores cresce durante o próprio passo**, e a reachability de cada nó de alocação **enxerga as arestas adicionadas pelas iterações anteriores** (propagação iterativa de fluxo de containers — crucial em apps list-heavy: a suíte Fossify, messengers como Signal/Loki).

O helper `computeSharedForwardReachability` pré-computa a reachability **uma única vez no grafo inicial** (antes de qualquer `addEdgeTo`) → perde essas arestas → conjuntos reachable menores → `reads`/`writes` menores → menos/zero arestas de container-flow → **`transitions=0`** nos apps onde a acumulação importa.

## 2. Evidência empírica (sweep parcial, `out/sweep_gh70_wtg_spark`, ~149/169 antes de abortar)

Config espelhando gh66 Stage A: 169 APKs, spark + cgDelegation, 1800s, 6 workers, 12g, dir fresco.

Dos **72** APKs baseline-`tr>0`, o gh70 completou 64:
- **44 com `tr>0` e contagem de transitions IDÊNTICA** à baseline (0 mismatches) — apps onde a acumulação de arestas no laço não afeta a reachability dos demais nós de alocação.
- **20 com `tr=0`** — e **NÃO por timeout**: `status=complete`, `error_message=null`, `analysis_seconds` < 1800 (frequentemente *mais rápido* que a baseline), `windows`/`components`/`reachability` presentes.

Comparação baseline × gh66 × gh70 nos 20 (contagem de transitions):

| APK | baseline | gh66 | gh70 |
|-----|--:|--:|--:|
| network.loki.messenger.fdroid_4515 | 126 | 126 | **0** |
| host.stjin.anonaddy_366210100 | 111 | 111 | **0** |
| org.fossify.gallery_28 | 78 | 78 | **0** |
| org.fossify.messages_20 | 54 | 54 | **0** |
| org.fossify.filemanager_13 | 51 | 51 | **0** |
| org.fossify.clock_10 / phone_22 | 48 | 48 | **0** |
| org.fossify.contacts_13 | 45 | 45 | **0** |
| org.fossify.math_10 | 42 | 42 | **0** |
| org.fossify.voicerecorder_18 | 39 | 39 | **0** |
| org.fossify.home_16 / keyboard_14 / notes_13 | 36 | 36 | **0** |
| org.fossify.camera_11 / paint_7 | 33 | 33 | **0** |
| com.alovoa.expo_48 | 30 | 30 | **0** |
| com.github.umer0586.droidpad_46 | 25 | 25 | **0** |
| com.bartixxx.oneplusarbchecker_13 | 15 | 15 | **0** |
| io.github.patricksmill.quicknotes_100007 | 14 | 14 | **0** |
| com.opennotes_8 | 5 | 0 | 0 |

(`com.opennotes_8` 5→0 já era ruído não-determinístico conhecido no gh66, não conta.)

**Prova fechada de que a regressão é do gh70 (não timeout, não não-determinismo do GATOR):**
1. A **única** diferença de código gh70 vs gh66 é trocar o `reachableNodes` no laço pelo lookup no mapa pré-computado.
2. gh66 (reachability **viva** no grafo que muta) == baseline **exato** nos 20.
3. gh70 (snapshot **estático**) == **0** em 19/20.
4. O helper é **provadamente correto em grafo estático**: `FlowgraphReachabilityShareTest` (7 testes, incluindo 20 grafos aleatórios de 200–400 nós com ciclos/NOpNodes/diamantes densos) passa set-equality vs `GraphUtil.reachableNodes`. O bug **não é o helper** — é o approach de pré-computar sobre um grafo que não é estático.

## 3. Por que não é consertável preservando o diff-zero

- Recompute por-iteração (= reverter) restaura a corretude mas elimina a otimização (sem ganho).
- Qualquer fixpoint que antecipe as arestas a serem adicionadas produziria um **superconjunto** de arestas → **quebra o diff-zero** (muda a saída).
- Memoização com invalidação por "versão do grafo" só ajuda se as adições de aresta forem esparsas — mas nos apps-problema (container-heavy) elas são densas, então o ganho é nulo.

## 4. Ação tomada

- **Revertido** `FlowgraphRebuilder.java` ao estado gh66 (git checkout; `reachableNodes` de volta no laço, helper e import auxiliares removidos, import `GraphUtil` restaurado). `git status` limpo para o arquivo.
- **Removido** o teste `FlowgraphReachabilityShareTest.java` (testava só o helper).
- **JAR rebuildado** (`mvn clean install -DskipTests -pl sootandroid,client -am`); `javap` confirma que o símbolo `computeSharedForwardReachability` **sumiu** do `lib/gator/rvsec-gator.jar` — comportamento gh66/baseline restaurado.
- Código do approach preservado em `rv-android/backup/gh70-not-viable/` (gitignored) para referência.
- INV-ANA-45 **NÃO** é sincronizada às specs principais (a propriedade que ela afirmava não se sustenta).

## 5. Lição

A reachability em `buildFlowThroughContainer` **não pode ser compartilhada/pré-computada** porque o passo **muta o grafo que percorre**. Qualquer otimização futura da fase WTG precisa partir desse fato — o gargalo `reachableNodes` per-alocação é intrínseco ao algoritmo iterativo de propagação de container-flow, não um recompute redundante sobre um grafo fixo. O gh66 (Fix 1, resolução de campos) permanece como a única otimização válida desse passo até agora.

---

## 6. Confirmação do revert (mini-sweep, 2026-06-18 19:06)

JAR rebuildado do source revertido (== gh66). Mini-sweep de validação (5 dos 20 APKs regredidos, config baseline: spark + cgDelegation, 1800s, 3 workers, 12g, dir `out/sweep_gh70_revertcheck`):

| APK | baseline | revert | verdict |
|-----|--:|--:|:--|
| org.fossify.voicerecorder_18 | 39 | 39 | PASS |
| com.alovoa.expo_48 | 30 | 30 | PASS |
| org.fossify.home_16 | 36 | 36 | PASS |
| org.fossify.clock_10 | 48 | 48 | PASS |
| network.loki.messenger.fdroid_4515 | 126 | 126 | PASS |

**5/5 match exato com a baseline, todos não-zero.** A regressão do gh70 foi eliminada; o comportamento gh66/baseline está restaurado. (loki completou em 652s com tr=126, vs o JAR bugado que dava 734s/tr=0.)
