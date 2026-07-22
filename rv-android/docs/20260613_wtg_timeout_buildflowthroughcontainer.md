# Diagnóstico: timeout da WTG em `buildFlowThroughContainer` (GATOR) — problema e fix proposto

**Data:** 2026-06-13
**Status:** diagnóstico fechado, fix **não implementado** (decisão pendente)
**Componente:** GATOR — `rvsec/rvsec-android/rvsec-gator` (repo `rvsec`)
**Relacionado:** `docs/20260609_sweep_wtg_completo_169.md` (sweep WTG dos 169 APKs); commit `e584894a` (fix de arity do SPARK no mesmo arquivo)

---

## 1. Contexto

No `experimento-20260604` (169 APKs JCA), a análise estática foi rodada com `--skip-wtg`,
deixando `transitions[]` vazio. Um novo consumidor precisa das transições (WTG), então fizemos
um sweep completo (SPARK + `cgDelegation=true`).

Resultado consolidado em `out/sweep_20260604_wtg_spark/`:

- **72/169 APKs** com `transitions>0`.
- **97/169 APKs** com `transitions=0` — **todos por timeout** na fase de construção da WTG
  (a reachability, as windows e os components são gravados antes — *write-first* —, então o JSON
  sobrevive íntegro, só sem transições).

Doubling do timeout (Stage A→B, 1800s→3600s) recuperou **~nada** (1 em 65). Isso indicava que o
gargalo **não** era "falta de tempo", e sim algo de custo super-linear.

## 2. O que foi testado e descartado

### 2.1. `sDepth=3` (flag nativo `-succDepth`) — REFUTADO

Hipótese inicial: a explosão estaria na enumeração recursiva de sucessores
(`WTGHelper.getSuccNode`, `ds/WTGHelper.java:111`), que é limitada pelo parâmetro
`Configs.sDepth` (default 4). Baixar para 3 cortaria a ramificação.

Expusemos o flag nativo `-succDepth` na tooling (sem tocar no GATOR):
`modules/rv-static-analysis/src/rv_static_analysis/config.py` (campo `succ_depth` + emissão
`-succDepth <n>`) e `scripts/static_analysis_sweep.py` (`--succ-depth`). O launcher
`lib/gator/gator` repassa o flag via `parse_known_args()` → `Main.java` → `Configs.sDepth`.

Run de recuperação nos 97 (saída em `out/sweep_20260604_wtg_recover97/`, spark + cgDelegation,
`--succ-depth 3 --timeout 1200 --workers 6`):

- **24/97 processados, TODOS bateram 1200s, 0 recuperados.**
- Inclusive apps minúsculos (ex. `ch.famoser.mensa_60`, ~2 MB) bateram o teto.

**Conclusão:** `sDepth` é a alavanca errada. Os apps estouram **antes** de chegar aos estágios
4/5 (`CallbackSequenceBuilder`/`BackEdgeBuilder`), que são os únicos onde `getSuccNode`/`sDepth`
atuam. (Nota lateral: o campo `methods_reachable` do dataset antigo é **não-confiável** — ex.
`com.a4a.g8invoicing` aparecia como `reach=2` mas o log real reporta 19.593 reachable; o
bucketing "apps pequenos" baseado nele estava errado.)

### 2.2. Timeout maior — FÚTIL

O custo é quadrático (ver §3). Dobrar o tempo só aumenta ~1,4× o tamanho de grafo tratável —
exatamente o que o Stage A→B (1800→3600s ≈ 0 ganho) já demonstrava empiricamente.

### 2.3. Lever nativo de configuração — INEXISTENTE

Nenhum flag do `Configs` desliga ou limita a fase responsável (`buildFlowThroughContainer` é
incondicional). Os flags disponíveis (`implicitIntent=false`, `resolveContext=true`,
`hardwareEvent=true`, `asyncStrategy`, `workerNum=16`, `sDepth`) afetam outras fases/estágios,
não essa.

## 3. Causa-raiz (confirmada por `jstack`)

### 3.1. Sequência de chamada

Depois que a reachability é gravada, a construção da WTG começa:

```
RvsecAnalysisClient.run()           (RvsecAnalysisClient.java:189)
 → WTGBuilder.build()               (WTGBuilder.java:48)
   → WTGBuilder.preBuild()          (WTGBuilder.java:106)
     → FlowgraphRebuilder.v()       (FlowgraphRebuilder.java:1267)
       → <init> → build()           (FlowgraphRebuilder.java:68 / 1185)
         → rebuildFlow()            (FlowgraphRebuilder.java:71)   — O(métodos × stmts × edges), linear-ish
         → postBuildFlow()          (FlowgraphRebuilder.java:265)
           → buildFlowThroughContainer()   (FlowgraphRebuilder.java:312)  ← GARGALO
```

Tudo isso roda na thread `main`, em `preBuild`, **antes do stage 1** da WTG.

### 3.2. O código quente

`buildFlowThroughContainer()` liga o fluxo de dados através de leituras/escritas em containers
(coleções). A estrutura é:

```java
for (Expr e : flowgraph.allNAllocNodes.keySet()) {            // TODO alloc node do app
    Set<NNode> reachedContainers =
        graphUtil.reachableNodes(flowgraph.allNAllocNodes.get(e));   // :319  BFS O(V+E) POR alloc
    // ... coleta writes/reads a partir de reachedContainers ...
    for (Stmt src : writes) {
        // ...
        for (Stmt tgt : reads) {                              // laço aninhado
            Integer tgtPos = wtgUtil.getReadContainerField(tgt);     // :349  re-resolve method ref
            // ...
            sn.addEdgeTo(tn);                                 // :365  criação de aresta
        }
    }
}
```

E `GraphUtil.reachableNodes()` (`gui/GraphUtil.java:36` → `findReachableNodes:42`) é um **BFS
completo do flow graph**, O(V+E) por chamada.

### 3.3. Custos que se somam (ambos quadráticos/redundantes)

1. **Fecho transitivo por alloc node** (`:319`): `reachableNodes()` é chamado **uma vez por
   alloc node** → **O(|allocNodes| × (V+E))**. Em apps Kotlin/Compose (muitos `new`/coleções),
   `allNAllocNodes` é enorme.
2. **Re-resolução de method ref no laço aninhado** (`:349`): `getReadContainerField(tgt)` chama
   `tgt.getInvokeExpr().getMethod()` → `SootMethodRefImpl.resolve()` (caro no Soot) para **cada
   par (src × tgt)**, embora dependa **apenas de `tgt`**. É recomputado |writes|× sem necessidade.

### 3.4. Evidência do `jstack` (definitiva)

Probe: `scripts/jstack_wtg_probe.sh` em `ch.famoser.mensa_60` (2 MB). Dumps brutos preservados em
`out/_jstack_dumps.txt`. Em **6 thread dumps** ao longo de ~2,5 min, a thread `main` está
**RUNNABLE (em CPU)**, sempre dentro de `buildFlowThroughContainer`:

| Dump | Frame de topo (gator) | Linha | Custo |
|------|----------------------|-------|-------|
| 1–2 | `GraphUtil.findReachableNodes` ← `reachableNodes` | `:319` | fecho transitivo por alloc |
| 3 | `NNode.addEdgeTo` | `:365` | criação de aresta (laço writes×reads) |
| 4–6 | `WTGUtil.getReadContainerField` → `SootMethodRefImpl.resolve` | `:349` | re-resolução de method ref |

`cpu ≈ elapsed` (78s→203s) — CPU-bound puro numa thread única (não é contenção dos 16 workers
internos). Um app de 2 MB queimou 200+ s **só** nessa função. Confirma todos os sintomas:

- **Independe do reach-count** — opera sobre alloc nodes do flow graph, não sobre métodos
  reachable (por isso apps "pequenos" também travam).
- **Silencioso** — o laço não loga nada; os logs param em "Reachability JSON written".
- **Quadrático** — casa com a futilidade de aumentar o timeout.

## 4. Fix proposto (NÃO implementado)

Todas as opções abaixo são **correções de performance que preservam a semântica** (as mesmas
arestas de fluxo são produzidas, apenas mais rápido). É uma categoria **distinta** de "poda/limite
no algoritmo da WTG" (que mudaria o *resultado* — vetada). Exigem editar o GATOR e rebuildar.

Ordem recomendada (da mais barata/segura à mais profunda):

### Fix 1 — Memoizar/içar a resolução de container field (risco ~zero)

- `getReadContainerField(tgt)` e `getWriteContainerField(src)` dependem só do statement. Computar
  uma vez por `tgt`/`src` (cache `Map<Stmt,Integer>`), **fora** do laço aninhado.
- Em particular, resolver os `reads` (posição + `NNode` alvo) **antes** do laço de `writes`, já
  que não dependem de `src`.
- Ataca diretamente os dumps 4–6 (`SootMethodRefImpl.resolve` repetido). Resultado byte-idêntico.

### Fix 2 — Evitar o fecho transitivo por alloc node

- Substituir o `reachableNodes()` por-alloc (dumps 1–2) por uma estratégia que compute a relação
  alloc → containers alcançados em (aprox.) O(V+E) total — ex.: uma única passagem reversa, ou
  memoização dos conjuntos alcançáveis por componente fortemente conexo (SCC) do flow graph.
- Maior ganho assintótico, porém mais delicado — exige cuidado para manter o resultado idêntico.

### Fix 3 — Reestruturação completa de `buildFlowThroughContainer`

- Uma única passagem que agrupe writes/reads por nó de container compartilhado, sem o produto
  cartesiano por alloc. Maior esforço; só se 1+2 não bastarem.

### Validação obrigatória (qualquer fix)

Mesmo protocolo do fix de arity (`e584894a`): rodar o GATOR corrigido sobre os **72 APKs que já
produzem `transitions>0`** e confirmar **diff zero** nas arestas (resultado idêntico, só mais
rápido). Depois medir, nos 97 que dão timeout, quantos passam a concluir dentro do tempo.

## 5. Decisão pendente

Opções abertas (a definir com o orientador/dono do experimento):

- **(A)** Aplicar **Fix 1** (cirúrgico, validável byte-a-byte) e medir o ganho antes de avançar.
- **(B)** Aplicar **Fix 1 + Fix 2** para atacar a quadrática de fato.
- **(C)** **Aceitar os 72** e encerrar — o consumidor (aperv) degrada de forma limpa quando
  `transitions[]` está vazio (`scoreWtg→0`).

Recomendação técnica: **(A) → medir → (B) se necessário**. Por preservar as arestas, nenhuma das
opções fere a restrição de "não mexer no algoritmo da WTG".

## 6. Artefatos

- Dumps `jstack`: `out/_jstack_dumps.txt`
- Probe: `scripts/jstack_wtg_probe.sh`
- Dataset entregue (intacto): `out/sweep_20260604_wtg_spark/` (72 com transitions)
- Run sDepth=3 (parado, 24/97, 0 recuperados): `out/sweep_20260604_wtg_recover97/`
- Tooling do flag nativo: `config.py` (`succ_depth`), `static_analysis_sweep.py` (`--succ-depth`)
- Código: `FlowgraphRebuilder.java:265-366` (`postBuildFlow`/`buildFlowThroughContainer`),
  `gui/GraphUtil.java:36-60` (`reachableNodes`), `WTGUtil.java:925` (`getReadContainerField`)
