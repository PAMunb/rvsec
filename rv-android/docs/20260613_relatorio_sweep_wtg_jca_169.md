# Relatório: sweep WTG (transitions) nos 169 APKs JCA do experimento-20260604

**Data:** 2026-06-13
**Escopo:** análise estática GATOR — popular `transitions[]` (Window Transition Graph) nos 169 APKs
**Status final:** **ENTREGUE** — 72/169 com WTG na pasta final; 97 sem WTG (timeout), com as demais seções íntegras
**Documentos relacionados:**
- `docs/20260609_sweep_wtg_completo_169.md` — plano e execução do sweep (estágios A/B/C)
- `docs/20260613_wtg_timeout_buildflowthroughcontainer.md` — diagnóstico técnico do gargalo + fix proposto

---

## 1. Objetivo e contexto

O `experimento-20260604` (169 APKs JCA, instrumentação dexlib2) teve a análise estática rodada
com `--skip-wtg`, produzindo JSONs com `reachability` + `windows` + `components` mas com
`transitions[]` **vazio**. Um novo consumidor passou a precisar das transições (o grafo de
transição de janelas, WTG). O objetivo deste trabalho foi **gerar as transições** para esses 169
APKs. Cobertura parcial era aceitável desde que as transições produzidas fossem corretas.

Resultado-resumo: **72/169 APKs com WTG** (6.339 transições no total); os 97 restantes não
concluíram a construção da WTG por timeout — mas mantêm todas as outras seções intactas, pois o
GATOR grava em modo *write-first* (reachability/windows/components antes da WTG).

## 2. O sweep WTG (estágios A/B/C)

### 2.1. Configuração

- Cliente GATOR `RvsecAnalysisClient`, call graph **SPARK** com **`cgDelegation=true`** (o
  `FlowgraphRebuilder` delega o virtual dispatch ao call graph do SPARK).
- Orquestração por `scripts/static_analysis_sweep.py` (sweep paralelo, resume via `_progress/`,
  classificação de status, `progress.csv` agregado).
- Saída canônica: **`out/sweep_20260604_wtg_spark/`**. O dataset skip-wtg original
  (`out/sweep_20260604/`) foi mantido intacto.

### 2.2. Pré-requisito: correção de um crash do SPARK (commit `e584894a`)

Com `cgDelegation=true`, a WTG crashava de forma determinística em **72/169** APKs, em ~2s, com
`ArrayIndexOutOfBoundsException: Index 1 out of bounds for length 1`.

- **Causa:** `FlowgraphRebuilder.buildCallGraphFromSparkCg` adiciona todo target de
  `edgesOutOf(s)` do call graph SPARK, incluindo edges sintéticas/bridge de **aridade
  incompatível**; `processFlowAtCall`/`removeFlowAtCall` então fazem `ie.getArg(i-1)` dirigido por
  `callee.getParameterCount()` e estouram o array de argumentos.
- **Correção (+28 linhas):** guard de aridade nas duas funções — `availableActuals = ie instanceof
  InstanceInvokeExpr ? argCount+1 : argCount; if (num_param > availableActuals) return;`.
- **Verificação:** 0 crashes (era 72/169); crasher `app.dumdum_14` recuperou 0→360 transitions;
  byte-idêntico nos APKs que já funcionavam.
- Commitado no repo `rvsec` como **`e584894a`** (fonte agora bate com o JAR em `lib/gator/`).

### 2.3. Estágios

| Estágio | O que | Recursos | Resultado |
|---------|-------|----------|-----------|
| **A** | 169 APKs, bulk | 8 workers, 1800s, 12g | ~7h26m; 164 complete (68 com tr>0), 5 `failed_no_json` (OOM), **0 crashes** |
| **C** | 5 falhas de A (alta memória) | 2 workers, 3600s, 60g | **5/5 recuperados**; 3 ganharam transitions (`infomaniak.meet` fechou com 60g, não precisou de 100g) |
| **B** | 96 timeouts de A (tempo estendido) | 8 workers, 3600s, 14g | **parado em 65/96 — yield ~nulo** (1 transition novo em 65); dobrar o tempo não resgatou nada |

**Resultado consolidado:** **169/169 `complete`**, **72/169 com `transitions>0`**, 6.339 transições.

### 2.4. Achado central do sweep

A construção da WTG é **limitada por tempo, não por configuração**: ~43% completam as transições;
o resto dá timeout — inclusive apps minúsculos — e **dobrar o timeout (1800→3600s) recupera
~nada**. Isso sinalizou um custo super-linear, investigado depois (§4). O *write-first* garante que
o timeout preserve reachability/windows/components.

## 3. Tentativa de recuperação: `sDepth=3` (REFUTADA)

Hipótese: a explosão estaria na enumeração recursiva de sucessores (`WTGHelper.getSuccNode`,
limitada por `Configs.sDepth`, default 4). Baixar para 3 cortaria o custo.

- Expusemos o flag **nativo** `-succDepth` do GATOR na nossa tooling (sem editar o GATOR):
  `modules/rv-static-analysis/src/rv_static_analysis/config.py` (campo `succ_depth`) e
  `scripts/static_analysis_sweep.py` (`--succ-depth`). O launcher `lib/gator/gator` repassa o flag
  ao `Main.java` via `parse_known_args()`.
- Run nos 97 timeouts (saída separada `out/sweep_20260604_wtg_recover97/`, `--succ-depth 3
  --timeout 1200 --workers 6`): **24/97 processados, TODOS bateram 1200s, 0 recuperados** —
  inclusive apps de ~2 MB. Run interrompido pela regra "se 0 recuperados, parar".
- **Conclusão:** `sDepth` é a alavanca errada. Os apps estouram **antes** dos estágios 4/5 (únicos
  onde `getSuccNode`/`sDepth` atuam). (Nota: o campo `methods_reachable` do dataset antigo é
  não-confiável — ex. `com.a4a.g8invoicing` aparecia como reach=2 mas o log real reporta 19.593.)

## 4. Investigação do código do GATOR — causa-raiz do timeout

Detalhe completo em `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`. Resumo:

- O gargalo é **`FlowgraphRebuilder.postBuildFlow() → buildFlowThroughContainer()`**
  (`FlowgraphRebuilder.java:312`), que roda em `preBuild`, **antes do stage 1** da WTG.
- É **O(allocNodes × tamanho_do_flow_graph) quadrático**: faz um `GraphUtil.reachableNodes()` (BFS
  completo, O(V+E)) **por alloc node**, mais um laço aninhado `writes × reads` que **re-resolve
  method refs** (`SootMethodRefImpl.resolve`) redundantemente.
- **Confirmado por `jstack`** (`scripts/jstack_wtg_probe.sh`, dumps em `out/_jstack_dumps.txt`):
  num app de 2 MB, a thread `main` ficou 100% CPU-bound nessa função por 200+ s, em 6 dumps
  consecutivos.
- **Implicações:** timeout maior é fútil (quadrático); nenhum flag nativo desliga essa fase; a
  única solução real é um **fix de performance que preserva a semântica** (memoizar a resolução de
  container field e/ou evitar o fecho transitivo por alloc) — **categoria diferente** da poda de
  algoritmo, que mudaria o resultado. **Fix não implementado** (decisão pendente).

## 5. Verificação de consistência e entrega

### 5.1. Pasta final

`/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604/` (layout plano
`<apk>.apk.json` + os 169 `.apk`). Verificou-se que ela **era** cópia do dataset skip-wtg
(`out/sweep_20260604`).

### 5.2. Verificação ANTES de copiar (skip-wtg "antes" × novo "com WTG", 169 APKs)

| Campo | Resultado |
|-------|-----------|
| **reachability** | **169/169 idêntica** (campo crítico de coverage/MOP — zero mudança) |
| **components** | **169/169 mesmo conteúdo** |
| **windows** | 147 idênticas; **22 viraram superset** |
| **transitions** | novo (o objetivo) |

Descobertas importantes que **contrariaram a premissa inicial** ("só o WTG mudou"):

1. **IDs de windows são reatribuídos por execução** (batem em só 97/169) — voláteis, baseados em
   ordem de alocação/hashcode. As `transitions[]` usam os IDs **novos**.
2. **22 dos 72** APKs com WTG ganharam **mais windows** (ex. `com.xmission...todo` 57→101 +640
   transitions) — construir as transições **descobre telas adicionais**. Confirmado **superset
   estrito**: nenhuma window do skip-wtg é perdida ou alterada (19 superset puro + 3 com
   multiplicidade diferente; 0 remoções).

Consequência: **não dá para mesclar só o `transitions[]`** no JSON antigo (IDs e windows não
batem) — é preciso **copiar o JSON inteiro**. Isso é **lossless**: reachability/components
idênticos, windows ⊇ skip-wtg, transitions consistentes com as windows do mesmo arquivo.

### 5.3. Cópia

Copiados os **72 JSONs inteiros** (tr>0), sobrescrevendo na pasta final. Os 97 sem WTG e os 169
`.apk` ficaram intactos. Originais skip-wtg preservados em `out/sweep_20260604/` (reverte se
preciso).

### 5.4. Re-verificação DEPOIS da cópia — todos os checks passaram

| Verificação | Resultado |
|-------------|-----------|
| Estrutura | 169 `.json` + 169 `.apk` |
| Transições | tr>0 = **72** / tr=0 = **97** |
| 72 copiados == dataset novo (arquivo inteiro) | **72/72** |
| 97 mantidos == skip-wtg (inalterados) | **97/97** |
| reachability == dataset novo (todos) | **169/169** |
| Total de transições | **6.339** |

**Veredito: pasta final consistente.**

## 6. Estado final e artefatos

**Entregue:** `APKS_FINAL_JCA_DEXLIB_20260604/` — 169 JSONs, 72 com WTG (windows+components+
transitions consistentes), 97 sem WTG (idênticos ao skip-wtg), reachability idêntica nos 169.

| Artefato | Caminho |
|----------|---------|
| Dataset WTG canônico | `out/sweep_20260604_wtg_spark/` (169 complete, 72 tr>0) |
| Dataset skip-wtg (origem, intacto) | `out/sweep_20260604/` |
| Run sDepth=3 (parado, 0 recuperados) | `out/sweep_20260604_wtg_recover97/` |
| Dumps jstack | `out/_jstack_dumps.txt` |
| Probe jstack | `scripts/jstack_wtg_probe.sh` |
| Fix de arity (commitado) | repo `rvsec`, commit `e584894a`, `FlowgraphRebuilder.java` |
| Tooling `-succDepth` | `config.py` (`succ_depth`), `static_analysis_sweep.py` (`--succ-depth`) |

## 7. Pendências / decisões em aberto

1. **Fix de performance da WTG** (`buildFlowThroughContainer`): não implementado — recuperaria os
   97 restantes. Opções e protocolo de validação em
   `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`. Decisão A (fix cirúrgico) / B (fix +
   anti-quadrática) / C (aceitar os 72) pendente.
2. Os 97 sem WTG são aceitáveis para o consumidor atual (degrada de forma limpa quando
   `transitions[]` está vazio — `scoreWtg→0`).
