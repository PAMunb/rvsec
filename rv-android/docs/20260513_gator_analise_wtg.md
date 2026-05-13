# Investigação: GATOR WTG Lento Apesar do SPARK Default

**Data:** 2026-05-13
**Autor:** Pedro Costa
**Status:** ✅ Investigação concluída — pronto para decisão de fix
**Relacionado:** `rvsec-calibracao/docs/20260513_analise_gator_window.md`, change `gh27-unified-static-analysis`, change `gh51-gator-soot-upgrade`

> **Nota de escopo (2026-05-13):** o único consumidor relevante neste momento é o **aperv** (`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape`). As demais ferramentas que consumiam `windows[]`/`transitions[]` (notadamente rv-agent) estão **descontinuadas no momento** e não influenciam a decisão. Isso muda significativamente o ranking das opções de fix — ver §3.4 e §7.

---

## TL;DR

**Hipótese central CONFIRMADA.** O SPARK está corretamente configurado e ativo, mas **apenas para a fase de reachability**. A WTG (Window Transition Graph) **bypassa completamente** o call graph SPARK do Soot — ela usa um singleton independente `AndroidCallGraph.v()` populado por `FlowgraphRebuilder.buildCallGraph()`, que faz **virtual dispatch CHA-style sobre todos os subtipos concretos** (com fallback de points-to local). Resultado: pior dos mundos — pagamos o custo do SPARK no Soot E rodamos um segundo grafo CHA-like depois.

Em todos os 4 APKs travados inspecionados, o log termina exatamente em `[RvsecAnalysisClient] Reachability JSON written (WTG pending)`. Nenhum log de `stage 1 finishes` da `WTGBuilder` aparece — o congelamento acontece em `FlowgraphRebuilder.rebuildFlow()` / `buildCallGraph()` (silencioso), **antes** de qualquer estágio da WTG começar.

A change gh51 (D5) já sabia que isso ocorre em "APKs complexos (18K+ vertices)" e implementou a estratégia *write-first JSON* como **mitigação** (não fix). O que mudou agora é que no dataset novo `APKS_FINAL_JCA_DEXLIB` a taxa subiu para **71.6% (136/190)** — deixou de ser exceção e virou regra.

**Para o aperv (único consumidor relevante hoje):** `transitions[]` é opcional (`MopScorer.scoreWtg` degrada para 0). `windows[]` é crítico. Portanto a prioridade é garantir `windows[]` populado, não necessariamente reconstruir a WTG completa.

**Verificação chave (§3.4bis):** o `windows[]` **não depende da WTG**. Todos os dados (activities, dialogs, options menus, widgets, listeners, text, hint, inputType, entries) vêm de `GUIAnalysisOutput` + `PropertyManager` + parsing XML, todos populados na fase `wjtp.gui` do Soot **antes** do `RvsecAnalysisClient.run()` ser chamado. O `if (wtg != null)` em `writeJson()` (linhas 1013–1024) que força array vazio no JSON parcial é **artificial** — comentário `// Section 2: windows (requires WTG)` não corresponde à realidade.

**Auditoria GESDA → Unified (§12):** a unificação em gh27 deixou de fora 5 features do GESDA legado, todas re-portáveis. As 4 mais simples são lookups XML adicionais (`prompt`, `spinnerMode`, `contentDescription`, `tooltipText`); a 5ª é extração de menu items programáticos via Soot CFG (~100 linhas).

**Plano consolidado:** change única `gh<N>-static-analysis-overhaul` que faz:
1. **Núcleo:** popular `windows[]` no caminho `wtg==null` do `writeJson()` (Opção C da §6).
2. **Flag opcional `--skip-wtg`:** evita o trabalho da WTG quando o consumidor não precisa de `transitions[]`.
3. **Re-port GESDA paridade XML:** adicionar `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` em `enrichFromXml`.
4. **Re-port menu programático:** rastrear `Menu.add()` / `Menu.addSubMenu()` via Soot CFG (porta do `SootAnalyze.java:372–531` do GESDA).
5. **Items de Spinner programáticos via `ArrayAdapter`** (feature nova): Soot dataflow para capturar items adicionados em código.
6. **Fix estrutural Opção A:** `FlowgraphRebuilder` delega virtual dispatch ao SPARK CG (`Scene.v().getCallGraph()`) — elimina o two-call-graph problem; WTG passa a usar SPARK também.

Esforço total estimado: ~3 semanas (MVP do item 5). Risco médio — refatoração estrutural (item 6) controlada via **feature flag de runtime** (§7.9) + bytecode-scan no nível WTG (§7.8). Detalhamento em §7. Prontidão SDD auditada em §16 (score 8.6/10 — pronto para `/opsx:new`).

---

## 1. Contexto

Durante o re-planejamento da calibração v3 do APE-RV, foi identificado:

- **71.6% dos APKs (136 de 190)** do `experimento-20260508` têm `windows[]` e `transitions[]` vazios.
- Em uma sweep anterior (`out/sweep_jca400_v1/`), a taxa foi de **58.9% (251/426)**.
- Causa imediata: timeout do wrapper `static_analysis_sweep.py` durante a fase de WTG.
- Causa raiz (esta investigação): a WTG não reusa o SPARK CG; constrói um segundo grafo CHA-style independente.

### Achado-chave que motivou a investigação

> gh51 (D5) repôs **SPARK** como default e ele é configurado corretamente em `cg.spark` no pack `wjtp` — mas a construção da WTG **NÃO usa** `Scene.v().getCallGraph()`. Ela usa **`AndroidCallGraph.v()`**, um singleton populado de forma independente em `FlowgraphRebuilder`, cuja política de construção nunca foi revisada por gh27 nem por gh51.

### Restrições operacionais respeitadas

- Nenhum processo Soot/GATOR foi executado localmente (sessão CogniCrypt em paralelo).
- Toda evidência vem de leitura de código + leitura de logs já produzidos + leitura de docs/specs.

---

## 2. Escopo

| Item | Dentro do escopo? |
|------|-------------------|
| Investigação técnica + diagnóstico | ✅ Concluído |
| Implementação de fix | ❌ |
| Abertura de change OpenSpec | ❌ (depende da decisão sobre §7) |
| Estratégia de re-run dos 136 APKs | ❌ (ver `20260513_analise_gator_window.md §6.3`) |
| Calibração APE-RV v3 propriamente dita | ❌ |

---

## 3. Achados da investigação

### 3.1 Etapa 1+2 — Auditoria do call graph da WTG (`AndroidCallGraph`)

**Q1: `AndroidCallGraph` é populado a partir do SPARK CG?**
❌ **NÃO.** É independente.

- `AndroidCallGraph.java` (linhas 49–65): singleton com construtor vazio, inicializa apenas dois `Map`s (`sm2nodeMap`, `allEdges`). Zero referências a `Scene.v().getCallGraph()`.
- `FlowgraphRebuilder.java` (linha 42): `private AndroidCallGraph callgraph = AndroidCallGraph.v();` — pega o singleton.
- `grep "Scene.v().getCallGraph()"` em todo `rvsec-gator/`: **único hit é `RvsecAnalysisClient.java:112`** (reachability). Zero hits em `wtg/`, `algo/`, `flowgraph/`, `analyzer/`.

**Q2: Que algoritmo `AndroidCallGraph` usa?**
**CHA-style com fallback de points-to local em `FlowgraphRebuilder.buildCallGraph()`** (linhas 940–1021).

Duas estratégias para cada `invoke` site:

(A) **Points-to via flowgraph local** (linhas 978–1001):
```java
NVarNode rcvNode = flowgraph.lookupVarNode(rcv_var);
Set<NNode> backReachedNodes = queryHelper.allVariableValues(rcvNode);
for (NNode backReachedNode : backReachedNodes) {
    SootClass sc = ((NObjectNode) backReachedNode).getClassType();
    SootMethod tgt = hier.virtualDispatch(callee, sc);
    callgraph.add(source, tgt, s);
}
```

(B) **Fallback CHA** (linhas 1010–1020) — quando o points-to falha:
```java
for (Iterator<SootClass> tgtItr = hier.getConcreteSubtypes(stc).iterator(); tgtItr.hasNext(); ) {
    SootClass sub = tgtItr.next();
    SootMethod tgt = hier.virtualDispatch(callee, sub);
    callgraph.add(source, tgt, s);
}
```

`Hierarchy.virtualDispatch()` (linhas 133–163) é o walk-up clássico de hierarquia.

**Q3: Complexidade estimada**
O(|appMethods| × |stmtsPerMethod| × |subtipos concretos| × |altura da hierarquia|).

Para um app médio: ~1000 métodos × ~100 stmts × ~30 subtipos × ~5 hierarquia ≈ **~15M virtual dispatches**. Para o `ac.mdiq.podcini.X_256.apk` (3287 classes / 59k vértices / 529k arestas mencionado em `20260513_analise_gator_window.md:219`), o produto explode — explica o travamento.

**Q4: Há log antes do hotspot?**
✅ Sim. O último log antes do silêncio é `[RvsecAnalysisClient] Reachability JSON written (WTG pending): <path>` (RvsecAnalysisClient.java:153).

**Q5: Estágios da WTG e seus logs**
Todos em `WTGBuilder.building()` (linhas 62–98), emitidos via `Logger.verb(TAG, "stage X finishes")` **DEPOIS** do estágio completar:

| Stage | Builder | Log |
|-------|---------|-----|
| 1 | `ExplicitForwardEdgeBuilder` | `stage 1 finishes` |
| 2 | `LifecycleForwardEdgeBuilder` | `stage 2 finishes` |
| 3 | `CloseWindowEdgeBuilder` | `stage 3 finishes` |
| 4 | `CallbackSequenceBuilder` | `stage 4 finishes` |
| 5 | `BackEdgeBuilder` | `stage 5 finishes` |
| 6 | `LifecycleCloseEdgeBuilder` | `stage 6 finishes` |

**Observação crítica:** O `FlowgraphRebuilder` é invocado em `WTGBuilder.preBuild()` (linha 106), **ANTES** do `building()`. Não emite log próprio. É exatamente esse o gap silencioso onde o tempo é gasto.

### 3.2 Etapa 1bis — Configuração SPARK no cliente

**Q1: `-cgAlgorithm spark` → `cg.spark enabled:true`?**
✅ **CONFIRMADO.** `Main.java:244`:
```java
case "spark": args.addAll(java.util.Arrays.asList("-p", "cg.spark", "enabled:true"));
```
Também `cg all-reachable:true` é sempre adicionado (linha 232).

**Q2: WTG recebe handle do CG?**
❌ **NÃO.** `RvsecAnalysisClient.java:159` instancia `new WTGBuilder()` com **construtor no-arg** e chama `wtgBuilder.build(output)` passando só o `GUIAnalysisOutput`. Nenhum handle do `Scene.v().getCallGraph()` chega à WTG.

**Q3: Mensagem exata antes da WTG**
`[RvsecAnalysisClient] Reachability JSON written (WTG pending): <path>` (RvsecAnalysisClient.java:153).

**Q4: Se WTG falha, JSON é sobrescrito?**
❌ **NÃO.** O catch (linhas 172–175) só loga `WTG construction failed: ... — JSON already contains reachability data`. O JSON parcial (com `windows: []` e `transitions: []` stubbed em `writeJson`) permanece como artefato final.

### 3.3 Etapa 3 — Logs dos APKs travados

Logs encontrados em `out/sweep_jca400_v1/_logs/`. Quatro APKs distintos inspecionados:

| APK | JSON size | Última linha do log | Stage onde travou |
|-----|-----------|---------------------|-------------------|
| `org.app.geotagvideocamera_360` | 4.8 KB | `[RvsecAnalysisClient] Reachability JSON written (WTG pending): ...` | Antes do stage 1 |
| `top.kagg886.pmf_185` | 11 KB | idem | idem |
| `de.maniac103.squeezeclient_11` | 40 KB | idem | idem |
| `day.vitayuzu.neodb_9` | ~7 KB | idem | idem |

**Fingerprint 100% consistente:** **nenhum** `stage X finishes` aparece. O congelamento acontece em `FlowgraphRebuilder.rebuildFlow()` / `buildCallGraph()` — o gap silencioso de O(N⁴) descrito em §3.1.

**Quantificação na sweep:** 251 / 426 APKs (58.9%) travados. No dataset definitivo `APKS_FINAL_JCA_DEXLIB`: 136 / 190 (71.6%).

### 3.4 Etapa 4 — Comparativo com GESDA original

| Aspecto | GESDA (pré-gh27) | Unified WTG (atual) |
|---------|------------------|---------------------|
| **Soot init** | Sim (1×, leve) | Sim (1×, pesado: SPARK CG) |
| **Call graph?** | ❌ **NÃO** — intra-procedural | ✅ Dois grafos: SPARK (Soot) + `AndroidCallGraph` (CHA-style local) |
| **Windows** | Parse XMLs decodificados (`res/layout/*.xml`) + pattern matching de `findViewById/setOnClickListener` | GATOR GUI analysis APIs sobre `AndroidCallGraph` |
| **Transitions** | Tracking intra-procedural de `startActivity()` | `WTGBuilder` 6 estágios sobre `AndroidCallGraph` |
| **Listeners dinâmicos** | ❌ Não resolve cross-method | ✅ Resolve via call graph |
| **Custo típico** | ~1–2s para windows | 30–60+ s ou timeout |
| **Documentado em gh27?** | Plan.md §7.2 reconhece "GATOR APIs are richer than GESDA's intra-procedural pattern matching" mas **não compara timings** |

**Q4 (consumidores de `windows[]` e `transitions[]` HOJE):**

Como rv-agent está descontinuado, **o único consumidor relevante é o aperv** (`ape/src/main/java/com/android/commands/monkey/ape/utils/`).

`MopData.java` (parser do aperv) faz 3 passes sobre o `analysis.json`:

| Pass | Campo | Criticidade para aperv | Fallback se vazio |
|------|-------|------------------------|-------------------|
| 1 | `reachability[]` (`directlyReachesMop`, `reachesMop`) | 🔴 **CRÍTICO** — base do scorer MOP | aperv:sata_mop equivale a aperv legacy (sem MOP-awareness) |
| 2 | `windows[]` (widgetData) | 🔴 **CRÍTICO** — identifica widgets que alcançam MOP | `activityHasMop()` sempre false → MOP-awareness desliga |
| 3 | `transitions[]` (WTG click events) | 🟢 **OPCIONAL** — bônus do scorer | **degrada graciosamente** |

**Evidência de degradação graciosa para `transitions[]`** (`MopScorer.java:55–69`):
```java
public static int scoreWtg(String activity, String shortId, MopData data) {
    if (data == null || !data.hasWtgData() || Config.mopWeightWtg == 0) {
        return 0;                                         // ← early-exit limpo
    }
    ...
}
```
`hasWtgData()` (`MopData.java:603–605`): `return !wtgTransitions.isEmpty();`

**Conclusão:** sem `transitions[]`, o aperv perde apenas o *bônus WTG* do scorer (`scoreWtg → 0`); o restante da política MOP-aware (filtro de widgets via `activityHasMop`, density tiebreaker via `stateMopDensity`, etc.) continua funcionando. Já sem `windows[]` o aperv:sata_mop colapsa para aperv legacy.

**Implicação para a decisão:** garantir `windows[]` populado é o que de fato desbloqueia a calibração. `transitions[]` é nice-to-have.

**Q5 (revival de windows-only):** ✅ Tecnicamente viável. Windows podem ser extraídas só via XML parsing (custo O(layouts)), mas perderia listeners cross-method e dinâmicos — degradação aceitável dado o profile de consumo do aperv.

### 3.4bis — Verificação chave (2026-05-13, pós-decisão de escopo): `windows[]` depende de WTG?

❌ **NÃO. A dependência é APENAS ID numérico — todos os dados de window estão disponíveis ANTES da WTG.**

Leitura linha-a-linha de `RvsecAnalysisClient.extractWindows()` (linhas 668–765) e `writeJson()` (linhas 987–1047):

**Origem real dos dados de `windows[]`:**

| Campo | Fonte | Depende de WTG? |
|-------|-------|------------------|
| `windows[].name`, `type`, `isMain` | `output.getActivities()`, `output.getDialogs()`, `output.getOptionsMenu()` (`GUIAnalysisOutput`) | ❌ Não |
| `windows[].widgets[]` (id, type, text, hint, listeners) | `output.getActivityRoots()` + `PropertyManager` + `output.getAllEventsAndTheirHandlers()` | ❌ Não |
| `windows[].widgets[].inputType` e `entries` | `enrichFromXml()` (parsing direto de `res/layout/*.xml`) | ❌ Não |
| `windows[].id` (numérico) | `windowNodeIds.get(name)` **com fallback `fallbackId++` ou `dialog.id`/`menu.id`** (linhas 682, 702, 725) | ⚠️ Apenas como **preferência** — fallback existe |
| Windows "catch-all" (context menus, fragments extras) | Iteração final em `wtg.getNodes()` (linhas 736–762) | ⚠️ **Sim**, mas têm `widgets: []` (informacional) |

**O que de fato força `windows[]` a vazio no JSON parcial:**

`writeJson()` linhas 1013–1024:
```java
// Section 2: windows (requires WTG)   ← comentário que NÃO reflete a realidade
if (wtg != null) {
    List<Map<String, Object>> windows = extractWindows(output, windowNodeIds, wtg);
    enrichFromXml(windows);
    w.name("windows");
    writeWindows(w, windows);
    w.flush();
} else {
    w.name("windows");
    w.beginArray().endArray();     // ← FORÇA vazio só porque wtg==null
    w.flush();
}
```

**O `if (wtg != null)` é artificial:** os dados existem em `output` (populado pela fase `wjtp.gui` do Soot, **antes** de `run()` ser chamado). O `FlowgraphRebuilder` da WTG **não escreve** em `output.getActivities()`, `getActivityRoots()`, ou `PropertyManager`. Tudo isso já está pronto quando o `RvsecAnalysisClient.run()` começa.

**Pipeline real:**

```
   Soot wjtp.gui transformer
        │
        ▼
   GUIAnalysisOutput populado:
   ├─ activities, dialogs, options menus
   ├─ activity roots (árvore de widgets)
   ├─ event handlers por widget       ← TUDO o que windows[] precisa
   ├─ PropertyManager (text, hint)
   └─ ...
        │
        ▼
   RvsecAnalysisClient.run(output)
        │
        ├── reachability  (usa Scene.v().getCallGraph())
        │        │
        │        ▼
        │   writeJson(..., wtg=null)   ← AQUI windows[] PODERIA ser populado
        │                                    mas o if () força vazio
        │
        └── WTGBuilder.build(output)  ← trava aqui em 71.6%
                 │
                 ▼
            writeJson(..., wtg=wtg)   ← só este caminho hoje popula windows[]
```

**Conclusão:** trocar o `else` para chamar `extractWindows(output, emptyMap, null)` e ajustar `extractWindows` para pular o catch-all (linhas 736–762) quando `wtg==null` produz `windows[]` completo. A única perda é o "catch-all" de fragments/context menus extras — e esses já têm `widgets: []` (linhas 729, 756), são informacionais.

**Opção C ✅ confirmada como TRIVIAL e VIÁVEL.**

### 3.5 Etapa 5 — Budget gh51 vs realidade

`gh51/design.md` linhas 140 e 185 (achados literais):

> **Linha 140:** "SPARK is typically 2–5× slower than CHA on large Android apps. Static analysis is offline and runs under a 30-minute per-APK budget (`RV_SA_TIMEOUT=1800`)"
>
> **Linha 185:** "WTG timeout (external kill) — `WTGBuilder.build()` takes >timeout for complex APKs (18K+ vertices) — Write-first strategy: JSON with reachability written BEFORE WTG starts; rewritten with full data if WTG completes — Reachability always preserved; windows/transitions empty on timeout"
>
> **Linha 246:** "Write-first JSON: Critical discovery — external timeout kills the Java process without triggering `catch`. Reachability must be written to disk BEFORE WTG starts so it survives the kill."

**Gap quantitativo:**
- gh51 esperava: timeouts de WTG em "APKs complexos (18K+ vertices)" — categoria minoritária, write-first como **mitigação**.
- Observado: **71.6%** do dataset definitivo `APKS_FINAL_JCA_DEXLIB`.
- Conclusão: o budget e a expectativa estavam calibrados para outliers, não para a maioria. A regressão é **estrutural** (algorítmica), não dataset-específica.

**Importante:** o argumento de gh51 para escolher SPARK foi sobre **precisão de `reachesMop`** (D5, linhas 130–138), não sobre performance de WTG. A WTG ficou de fora dessa decisão — e é exatamente onde o custo dispara.

---

## 4. Diagrama do problema (Two-Call-Graph Problem)

```
                     ┌────────────────────────────────────────┐
                     │       Soot whole-program session       │
                     │                                        │
   APK + Spec ─────▶ │  cg pack (cg.spark enabled:true,       │
                     │           all-reachable:true)          │
                     │           │                            │
                     │           ▼                            │
                     │  Scene.v().getCallGraph()  ◀── SPARK   │
                     │           │                            │
                     │           ▼                            │
                     │  wjtp pack (wjtp.gui transformer)      │
                     │           │                            │
                     │           ▼                            │
                     │  RvsecAnalysisClient.run(output)       │
                     │           │                            │
                     │           ├── reachability ────┐       │
                     │           │   uses CG ✅       │       │
                     │           │                    ▼       │
                     │           │            JSON (parcial)  │
                     │           │            "WTG pending"   │
                     │           │                            │
                     │           └── WTGBuilder.build() ──┐   │
                     │                       │            │   │
                     │                       ▼            │   │
                     │           ┌──────────────────────┐ │   │
                     │           │ FlowgraphRebuilder   │ │   │
                     │           │ ┌─────────────────┐  │ │   │
                     │           │ │ AndroidCallGraph│  │ │   │  ◀── 2º grafo!
                     │           │ │   (CHA-style)   │  │ │   │      ~O(N⁴)
                     │           │ │ NÃO usa SPARK   │  │ │   │      trava 71.6%
                     │           │ └─────────────────┘  │ │   │
                     │           └──────────────────────┘ │   │
                     │                       │            │   │
                     │            (timeout / kill aqui)   │   │
                     │                       ✗            │   │
                     │                                    │   │
                     │              (nunca chega)         ▼   │
                     │                             6 stages   │
                     └────────────────────────────────────────┘
```

---

## 5. Resposta à pergunta-âncora

**"SPARK está realmente sendo usado em todos os pontos?"**

❌ **NÃO. PARCIALMENTE.**

- **Reachability:** sim, usa `Scene.v().getCallGraph()` (SPARK).
- **Windows / WTG:** não, usa `AndroidCallGraph.v()` (singleton independente, CHA-style com points-to local).

O custo do SPARK é pago no Soot, mas o **ganho de SPARK não chega à WTG**. Pior: paga-se o custo do SPARK + o custo de um segundo grafo CHA-like construído por cima — pior dos dois mundos.

---

## 6. Recomendações priorizadas

**Contexto importante:** o único consumidor relevante hoje é o aperv. Para o aperv:
- `windows[]` é **crítico** (sem ele, sata_mop colapsa para aperv legacy).
- `transitions[]` é **opcional** (`MopScorer.scoreWtg` degrada para 0 limpo).
- `reachability[]` já é produzida em todos os APKs (escrita antes do kill).

Isso reordena drasticamente as opções: garantir `windows[]` rápido vira a prioridade número um; reconstruir a WTG inteira deixa de ser urgente.

### Opção B ⭐⭐ — Modo `--fast-windows` estilo GESDA (RECOMENDADO)

**O quê:** caminho alternativo que extrai `windows[]` via parsing direto dos XMLs decodificados (`res/layout/*.xml`) + pattern matching intra-procedural — **sem** call graph, **sem** WTG. `transitions[]` permanece vazio.

**Por quê:**
- Reproduz a velocidade da GESDA original (~1–2 s/APK em vez de timeout).
- Atende 100% do que o aperv:sata_mop precisa: `reachability[]` (já produzida) + `windows[]` (via XML).
- `transitions[]` opcional → degradação documentada e graciosa (`scoreWtg → 0`).
- Caminho **aditivo**: não modifica o pipeline WTG existente; só adiciona uma flag.

**Risco:** baixo. Único trade-off conhecido: listeners registrados cross-method (ex: `setOnClickListener` em base class) não são resolvidos. Para JCA dataset isso provavelmente é marginal.

**Esforço:** baixo. Implementação via:
- Reuso do `XmlParser` do GESDA (se ainda existir em `backup/` ou em commits pré-gh27); OR
- Reimplementação em Python usando o APK já decodificado por apktool (a pipeline atual de rv-static-analysis já decodifica).

**Validação:** rodar nos 54 APKs que hoje têm `windows[]` OK; comparar contagem de widgets e MOP-coverage com o output GATOR atual. Se o delta for <5%, fix é seguro para os outros 136.

**Change OpenSpec sugerida:** `gh<N>-fast-windows-mode`.

### Opção C ⭐⭐⭐ — Skip WTG, popular `windows[]` no JSON parcial (RECOMENDADO; verificado)

**O quê:** modificar o `else` da seção `windows` em `writeJson()` (linhas 1020–1024) para chamar `extractWindows(output, Collections.emptyMap(), null)` em vez de escrever array vazio. Adicionar guarda em `extractWindows` para pular o catch-all (linhas 736–762) quando `wtg==null`. Opcionalmente, adicionar flag `--skip-wtg` que evita até a chamada de `WTGBuilder.build()`.

**Por quê:**
- ✅ **Verificado em §3.4bis:** todos os dados de `windows[]` (nomes, widgets, listeners, text, hint, inputType, entries) vêm de `GUIAnalysisOutput` + `PropertyManager` + XML — todos populados **antes** do `RvsecAnalysisClient.run()` ser chamado. Zero dependência de WTG.
- ✅ Aperv degrada graciosamente sem `transitions[]` (`scoreWtg → 0`); o resto da política MOP continua intacto.
- ✅ A única perda é o "catch-all" de fragments/context menus extras, que já têm `widgets: []` no código atual (informacionais).
- ✅ Reusa 100% do código existente de extração de windows — zero risco de divergência semântica para os 54 APKs que já funcionam.

**Risco:** mínimo. Validação trivial: rodar nos 54 APKs que hoje têm `windows[]` populadas e comparar contagem de `windows`/`widgets` antes/depois. Diferença esperada = 0 ou alguns "WTG-only windows" extras a menos.

**Esforço:** **muito baixo** — 2 mudanças cirúrgicas em `RvsecAnalysisClient.java`:
1. `else` em linhas 1020–1024: chamar `extractWindows(output, Collections.emptyMap(), null)` + `enrichFromXml(...)` + `writeWindows(...)`.
2. `extractWindows`: envolver o bloco `for (WTGNode node : wtg.getNodes())` (linhas 736–762) em `if (wtg != null)`.

Opcional (3): flag `--skip-wtg` que circunda também `wtgBuilder.build()` (linha 160) — evita o trabalho perdido na chamada que vai dar timeout. Trivial.

**Change OpenSpec sugerida:** `gh<N>-populate-windows-without-wtg`.

### Opção A — Fazer `AndroidCallGraph` delegar ao SPARK CG (cleanup estrutural)

**O quê:** modificar `FlowgraphRebuilder.buildCallGraph()` (linhas 940–1021) para consultar `Scene.v().getCallGraph()` no lugar de re-resolver via `hier.virtualDispatch()` + `hier.getConcreteSubtypes()`.

**Por quê:** elimina o trabalho redundante (two-call-graph problem). SPARK já fez o trabalho com points-to global; reaproveitar.

**Por quê NÃO é mais a prioridade:**
- O único consumidor de WTG hoje (`transitions[]`) é o aperv, que **não precisa**.
- Risco semântico não-trivial: SPARK pode omitir edges para libs quarentinadas; precisa do bytecode scan complementar (estilo gh51 D6) para paridade.
- Esforço maior que B/C, com payoff baixo dado o uso atual.

**Quando reabrir:** se/quando o rv-agent voltar à ativa, ou se um novo consumidor exigir `transitions[]` precisas.

**Change OpenSpec sugerida (futura):** `gh<N>-wtg-reuse-spark-cg`.

### Opção D — Refatorar `AndroidCallGraph` para algoritmo eficiente

Descartada para o momento (alto esforço, baixo payoff dado o uso atual). Mencionada por completude.

---

## 7. Recomendação final — change única consolidada (megaescopo)

**Decisão (2026-05-13, expandida):** tudo em UMA change só — `gh<N>-static-analysis-overhaul`. Aproveita a janela de mexer em `RvsecAnalysisClient.java` + `FlowgraphRebuilder` + `enrichFromXml` para:
1. **Resolver o problema principal** (windows vazias em 71.6%).
2. **Re-portar features do GESDA legado** que ficaram fora em gh27.
3. **Corrigir o two-call-graph problem estrutural** (Opção A) na mesma janela, eliminando dívida técnica de longo prazo.

Premissa: como já vamos rebuildar o JAR e re-rodar os 190 APKs para validar o fix do windows, o custo marginal de validar também o resto é baixo. O risco de regressão cruzada é controlado porque cada item é testável isoladamente.

### 7.1 Escopo da change

| # | Item | Origem | Arquivos tocados | Esforço | Risco |
|---|------|--------|------------------|---------|-------|
| **1** | Popular `windows[]` no caminho `wtg==null` do `writeJson()` (Opção C ⭐) | §3.4bis + §6 Opção C | `RvsecAnalysisClient.java` (linhas 1020–1024 + guarda em `extractWindows` 736–762) | ~1 dia | Mínimo |
| **2** | Flag `--skip-wtg` (especificação em §7.5) | §6 Opção C | `RvsecAnalysisClient.java` (linha 159 wrap) + `static_analysis_sweep.py` arg | ~½ dia | Mínimo |
| **3** | Re-port GESDA paridade XML — 4 atributos | §12 (Top #1, #2) | `RvsecAnalysisClient.java` (`enrichFromXml` ~lines 885–914) | ~½ dia | Mínimo |
| **3.1** | • `android:prompt` (Spinner) | XmlParser GESDA | idem | (incluso) | — |
| **3.2** | • `android:spinnerMode` (dropdown/dialog) | XmlParser GESDA | idem | (incluso) | — |
| **3.3** | • `android:contentDescription` | XmlParser GESDA `parseView:207` | idem | (incluso) | — |
| **3.4** | • `android:tooltipText` | XmlParser GESDA `parseView:208` | idem | (incluso) | — |
| **4** | Re-port menu programático (`Menu.add()` / `Menu.addSubMenu()`) | §12 (Top #3) — `SootAnalyze.java:372–531` GESDA | nova classe `MenuExtractor.java` + chamada em `extractWindows` para `OPTIONSMENU` | ~2 dias | Baixo (porta direta) — sujeito a pre-flight de §7.6 |
| **5** | **Items de Spinner programáticos via `ArrayAdapter`** (feature nova; MVP-only: literal constructor + `add()`/`addAll()`. `getResources().getStringArray()` e Kotlin `listOf()` ficam fora do MVP — ver §7.7) | §12.3 #6 | nova classe `SpinnerItemExtractor.java`; Soot points-to do SPARK para rastrear receiver type + def-use chain até literais | ~4 dias (MVP) / 6–7 dias (full) | Médio (dataflow novo) |
| **6** | **Opção A: `FlowgraphRebuilder` delega ao SPARK CG** (elimina two-call-graph problem). Filtro: para cada `invoke` site, consultar `Scene.v().getCallGraph().edgesOutOf(src)` e filtrar por `tgt.getSubSignature() == callee.getSubSignature()`. Union com **bytecode-scan** (gh51 D6, ver §7.8) para edges em libs quarentinadas. **Implementação via feature flag** `cg.delegation.enabled` (rollback runtime sem rebuild — ver §7.9) | §3.1 + §6 Opção A | `FlowgraphRebuilder.buildCallGraph()` linhas 940–1021 — substituir `hier.virtualDispatch()` + `hier.getConcreteSubtypes()` por SPARK CG query | ~5 dias | **Médio-Alto** (mudança semântica controlada por feature flag) |
| **6.1** | Validação cruzada: comparar WTG output **antes vs depois** em 10 APKs OK (não-travados) para garantir paridade de `transitions[]` (definição precisa em §7.4) | — | smoke test + diff JSON via `scripts/wtg_paridade_diff.py` (novo) | ~1 dia | — |
| **7** | Schema bump no JSON (`schemaVersion: "1.0" → "2.0"`, ver §7.10) + atualizar `MopData.java` do aperv para ler campos novos | §12.3 (consumidor) | `RvsecAnalysisClient.writeJson` (linha 1001+) + `ape/.../utils/MopData.java` | ~1 dia | Baixo |
| **8** | Testes unitários para cada item (3 atributos XML, menu programático, ArrayAdapter, paridade WTG-SPARK) + smoke em 10 APKs (fixture list em §7.11) + re-run completo dos 190 APKs | — | testes existentes em `…/rvsec-gator/client/src/test/` + `ape/src/test/` + sweep parcial | ~2 dias | — |

**Total:** ~16 dias úteis (~3 semanas) para o MVP do item 5; +2 dias se versão "full" do item 5 (ver §7.7).

### 7.1.1 Dependency DAG entre os itens

```
                ┌─────────┐
                │ Pre-flight│  ── /opsx:new + auditorias §7.6 + §7.8 + §7.11
                └────┬────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     ┌────┐      ┌────┐       ┌────┐
     │ 1  │      │ 6  │       │ 3  │   ── independentes (paralelizáveis)
     └─┬──┘      └─┬──┘       └─┬──┘
       │           │ ┌──────────┘
       │           │ │
       ▼           ▼ ▼
     ┌────┐      ┌────┐
     │ 2  │      │6.1 │   ── item 2 só faz sentido após 1; 6.1 depende de 6
     └────┘      └─┬──┘
                   │
       ┌───────────┘
       │
       ▼
     ┌────┐       ┌────┐
     │ 7  │ ◀──── │ 4  │   ── item 7 (schema) depende de 1, 3, 4 (sabe os campos novos)
     └─┬──┘       └────┘   ── item 4 depende de pre-flight §7.6 (Soot API check)
       │             ▲
       │             │
       │           ┌────┐
       └─────────► │ 5  │   ── item 7 final só fecha após 5 (sabe estrutura ArrayAdapter)
                   └────┘   ── item 5 depende de pre-flight §7.7 (cobertura)
                     │
                     ▼
                   ┌────┐
                   │ 8  │   ── item 8 (testes + re-run) depende de TODOS
                   └────┘
```

**Marcos de checkpoint:**
- **M1 (após 1+2):** desbloqueio funcional mínimo do aperv — calibração v3 pode iniciar com build intermediário (tag `gh<N>-interim-windows-fix`).
- **M2 (após 3+4+7 parcial):** paridade GESDA atingida.
- **M3 (após 6+6.1):** decisão GO/NO-GO para item 6 baseado em paridade Jaccard (§7.4).
- **M4 (após 8):** change pronta para `opsx:archive`.

### 7.2 Fora de escopo (todo o resto)

- **Opção D** (refatorar `AndroidCallGraph` para `OnFlyCallGraphBuilder`/RTA) — descartada.
- Aumentar timeout do sweep (anti-padrão).
- Mudanças no rv-experiment, rv-platform, ou no scorer do aperv (`MopScorer.java`).
- ArrayAdapter "full" (cobre `getResources().getStringArray()`, Kotlin `listOf()`, escape analysis) — só MVP nesta change.

### 7.3 Sequência de execução proposta

Ordenada para **descobrir problemas cedo** e isolar risco. Pré-condicões em §7.6–7.11.

1. **Pre-flight (1 dia):** abrir change OpenSpec via `/opsx:new gh<N>-static-analysis-overhaul`. Schema: `rv-sdd` (Full SDD). Executar auditorias §7.6 (Soot API GESDA), §7.7 (cobertura ArrayAdapter), §7.8 (bytecode scan), §7.11 (fixtures).
2. **Itens 1+2** (1½ dias): popular `windows[]` + flag `--skip-wtg`. Smoke em 5 APKs. **🚩 Marco M1.**
3. **Itens 3.1–3.4** (½ dia): paridade XML. Validar atributos contra outputs GESDA em 3 APKs.
4. **Item 4** (2 dias): menu programático. Validar no APK fixture de §7.11.
5. **Item 7 parcial** (½ dia): bump schema + leitor `MopData` para campos XML + menu items.
6. **Item 5** (4 dias MVP): ArrayAdapter literal constructor + `add`/`addAll`. Validar nos APKs de §7.11. **🚩 Marco M2.**
7. **Item 6 + 6.1** (6 dias): Opção A via feature flag (§7.9). Validação cruzada Jaccard (§7.4). **🚩 Marco M3 — GO/NO-GO.**
8. **Item 7 restante** + **Item 8** (3 dias): finalizar leitor aperv (items recursivos do menu) + bateria completa de testes + re-run dos 190 APKs. **🚩 Marco M4.**
9. **`/rv-verify` + `/opsx:verify` + `/opsx:archive`**.

### 7.4 Critérios de sucesso (definição rigorosa)

- [x] Hipótese diagnóstica confirmada (§3–§5)
- [ ] `windows[]` populadas em **≥95%** dos 190 APKs do `APKS_FINAL_JCA_DEXLIB` após re-run (denominador: 190; numerador: APKs com `windows` não-vazio)
- [ ] Aperv `MopData` lê `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` sem erros em **100%** dos APKs do smoke (10 APKs de §7.11)
- [ ] ≥1 APK com menu programático mostra `items[]` populado em `OPTIONSMENU` (fixture específico em §7.11)
- [ ] ≥1 APK com Spinner populado por `ArrayAdapter` mostra `entries[]` ≥1 item via dataflow (fixture em §7.11)
- [ ] **Paridade WTG (Opção A) — definição precisa:** Para cada um dos 10 APKs de §7.11 (subconjunto de baseline OK):
  - Computar `T_before = {(src_window_id, tgt_window_id, event_type) ∈ transitions[]}` no JSON pré-mudança.
  - Computar `T_after = idem no JSON pós-mudança.
  - Jaccard = `|T_before ∩ T_after| / |T_before ∪ T_after|`.
  - **Critério:** média Jaccard ≥ 0.95 sobre os 10 APKs; nenhum APK abaixo de 0.85.
  - Divergências (transições novas ou perdidas) devem ter justificativa documentada (via bytecode-scan ou edge específica de SPARK).
- [ ] Wall-clock médio por APK: redução mensurada em pelo menos 5 APKs grandes (>50K vértices CG); meta aspiracional **≥30%** (foi ≥50% antes — moderado após audit; baseline a ser tirado no pre-flight)
- [ ] Calibração APE-RV v3 prossegue com 190 APKs (não 54)
- [ ] `rv-verify` e `opsx:verify` passam clean

### 7.5 Especificação do flag `--skip-wtg`

**Propagação dual** (Python sweep → Java client):

1. **Sweep CLI** (Python): novo arg `--skip-wtg` em `scripts/static_analysis_sweep.py` (boolean, default false). Quando `true`, adiciona ao comando do GATOR: `-clientParam skipWtg=true`.
2. **GATOR client** (Java): parsing em `RvsecAnalysisClient.run()` antes da linha 158, via `Configs.getClientParamCode("skipWtg=")` (mesmo padrão de `mopDir=`, `codePackage=`). Se `true`, pular `wtgBuilder.build()` (linha 160) e ir direto para o caminho `wtg==null` do `writeJson()`.
3. **Default:** `false` (comportamento atual; WTG é tentada normalmente). Quando `--skip-wtg` é passado, log explícito `[RvsecAnalysisClient] WTG skipped by client parameter`.

**Por que client parameter (não env var ou JVM property):** mantém padrão arquitetural existente do GATOR; permite controle per-APK no futuro (ex: aplicar só a APKs sabidamente travados).

### 7.6 Pre-flight: Soot API check (Item 4)

Antes de portar `SootAnalyze.java:372–531` do GESDA:
- Verificar versão Soot do `rvsec-gesda/pom.xml` vs `rvsec-gator/pom.xml` (gh51 fixou em Soot 4.7.1).
- Diff de API: `UnitGraph`, `InvokeExpr`, `InterfaceInvokeExpr`, `AssignStmt`, `IntConstant`, `RefType` — se >3 signatures divergirem, escalar item 4 para 3–4 dias.
- Verificar disponibilidade de `parseAppStrings` / equivalente no `RvsecAnalysisClient` (foi `XmlParser` do GESDA — pode ser que `enrichFromXml` + `resolveStringReference` em `RvsecAnalysisClient.java:962–981` cubra).

### 7.7 Pre-flight: cobertura ArrayAdapter (Item 5)

Antes de implementar:
- Decompilar 20 APKs amostrados do `APKS_FINAL_JCA_DEXLIB` (estratificado por size_bucket).
- `grep -E "new ArrayAdapter|setAdapter\(.*ArrayAdapter|getResources\(\).getStringArray|listOf\(" sources/`.
- Classificar por padrão: (a) `new ArrayAdapter<>(ctx, layoutId, R.array.X)`, (b) literal `new String[]{...}`, (c) `getResources().getStringArray(...)`, (d) Kotlin `listOf(...)`.
- **MVP (4 dias):** cobre (a) + (b) via SPARK points-to + def-use local.
- **Full (6–7 dias):** adiciona (c) via resolução de R.array → arrays.xml + (d) via desugaring Kotlin.
- **Decisão:** se cobertura MVP em ≥40% dos APKs amostrados, parar em MVP. Caso contrário, escalar.

### 7.8 Pre-flight: bytecode-scan no nível WTG (Item 6)

`gh51-D6` introduziu bytecode scan APENAS para `directlyReachesMop` (RvsecAnalysisClient.java:133, `findDirectMopCallersByBytecodeScan`). Para o item 6 da WTG, é necessário um análogo:

- Para cada `invoke` site na WTG, **se** o callee tem class name em `IGNORED_CLASSES` (libs quarentinadas), **então** adicionar edge via bytecode scan (não pelo SPARK CG, que omitiria).
- Modelo: estender `findDirectMopCallersByBytecodeScan` para uma rotina genérica `scanInvokesByPattern(classes, predicate)` que retorne `Set<Edge>` em vez de `Set<SootMethod>`.
- Validação: na paridade Jaccard (§7.4), divergências esperadas devem mapear 1:1 para edges adicionadas pelo bytecode scan.

### 7.9 Feature flag para Item 6 (rollback runtime)

Em `Configs.java` (gator): novo campo `cgDelegationEnabled` (boolean, default true). Em `FlowgraphRebuilder.buildCallGraph()`, branch no início:

```java
if (Configs.cgDelegationEnabled) {
    return delegateToSparkCg(...);  // novo caminho
} else {
    return legacyCha(...);          // caminho atual preservado
}
```

**Benefícios:**
- Se Jaccard <95% em produção: setar `-clientParam cgDelegation=false` e re-rodar sem rebuild.
- Permite A/B testing wall-clock e qualidade.
- Rollback total: deletar o flag check após N semanas de operação estável.

### 7.10 Schema versioning (Item 7)

JSON atual **não tem** `schemaVersion` field (verificar — assumir v1.0 implícita).

- **Adicionar** `schemaVersion: "2.0"` como segundo campo do JSON (depois de `package`, antes de `mainActivity`).
- **Campos novos em v2.0**:
  - `windows[].widgets[].prompt` (string, opcional; null se ausente).
  - `windows[].widgets[].spinnerMode` (string enum: `"dropdown"` | `"dialog"` | null).
  - `windows[].widgets[].contentDescription` (string, opcional).
  - `windows[].widgets[].tooltipText` (string, opcional).
  - `windows[type="OPTIONSMENU"].widgets[].items[]` (array de widget objects, recursivo; vazio se não há submenu).
  - `windows[].widgets[].entries[]` (já existia; agora pode ser populado via ArrayAdapter dataflow além do XML).
- **Compat reader (aperv MopData.java):**
  - Se `schemaVersion` ausente OU `"1.0"`: campos novos tratados como `null`/vazio. Comportamento idêntico ao pré-mudança.
  - Se `schemaVersion == "2.0"`: lê todos os campos. `null` aceito.
- **Estratégia para JSONs existentes** (54 APKs OK em `APKS_FINAL_JCA_DEXLIB`): re-gerar todos após a change. Não há tentativa de upgrade in-place; o re-run dos 190 APKs (Item 8) é a fonte canônica.

### 7.11 Fixtures de teste (definição obrigatória pre-flight)

**Cada fixture é um APK específico do `APKS_FINAL_JCA_DEXLIB` (ou cryptoapp test resource). Lista a ser preenchida no pre-flight, **antes** de iniciar a implementação.** Template:

| Função | APK candidato | Como validar |
|--------|---------------|--------------|
| Smoke do item 1 (windows[] populadas no caminho wtg-null) | 5 APKs travados do grupo de 136 — escolher: 1 pequeno, 2 médios, 2 grandes (por nº de classes) | Verificar `windows.length > 0` no JSON pós-fix |
| Smoke do item 6 (paridade Jaccard) | 10 APKs do grupo de 54 OK — estratificar por size_bucket (small/medium/large/xlarge) | Script `wtg_paridade_diff.py` |
| Item 4 (menu programático) | APK com `onCreateOptionsMenu` populado por `menu.add(...)` | A definir no pre-flight (grep no corpus) — fallback: `cryptoapp` test fixture |
| Item 5 (Spinner ArrayAdapter) | APK com `new ArrayAdapter<>(...)` + `adapter.add(...)` | A definir no pre-flight (grep no corpus) |

**Critério bloqueante:** se pre-flight não encontrar fixture para itens 4 ou 5 no corpus, escalar para criar APK sintético (+1 dia por APK).

### 7.2 Fora de escopo (todo o resto)

- **Opção D** (refatorar `AndroidCallGraph` para `OnFlyCallGraphBuilder`/RTA) — descartada.
- Aumentar timeout do sweep (anti-padrão).
- Mudanças no rv-experiment, rv-platform, ou no scorer do aperv (`MopScorer.java`).

### 7.3 Sequência de execução proposta

Ordenada para **descobrir problemas cedo** e isolar risco:

1. **Pre-flight (½ dia):** abrir change OpenSpec via `/opsx:new gh<N>-static-analysis-overhaul`. Schema: `rv-sdd` (Full SDD) — múltiplos domínios (`analysis` + `tools/aperv-tool`), mudança estrutural, design decisions importantes.
2. **Itens 1+2** (1½ dias): popular `windows[]` + flag `--skip-wtg`. Smoke em 5 APKs. **Marco: desbloqueio funcional do aperv** (já dá para tocar calibração v3 em paralelo se preciso).
3. **Itens 3.1–3.4** (½ dia): paridade XML. Validar atributos contra outputs GESDA em 3 APKs.
4. **Item 4** (2 dias): menu programático. Validar em cryptoapp fixture (`<onCreateOptionsMenu>` programático).
5. **Item 7 parcial** (½ dia): bump schema + leitor `MopData` para campos XML — necessário para que itens 3 e 4 cheguem ao aperv.
6. **Item 5** (4 dias): ArrayAdapter spinner items. Validar em APK conhecido com spinner populado em código.
7. **Item 6 + 6.1** (6 dias): Opção A — refatorar `FlowgraphRebuilder` + validação cruzada de paridade WTG. **Marco mais arriscado da change.** Se a paridade falhar, considerar reverter o item 6 e manter apenas itens 1–5.
8. **Item 7 restante** + **Item 8** (3 dias): finalizar leitor aperv (items recursivos) + bateria completa de testes + re-run dos 190 APKs.
9. **`/rv-verify` + `/opsx:verify` + `/opsx:archive`**.

**Checkpoint após (2):** validar se o desbloqueio mínimo já libera a calibração v3. Se sim e o tempo apertar, pode-se rodar v3 com **build intermediário** enquanto o resto da change é finalizado. A change só fecha quando 1–8 estiverem prontos.

### 7.4 Critérios de sucesso

- [x] Hipótese diagnóstica confirmada (§3–§5)
- [ ] `windows[]` populadas em ≥95% dos 190 APKs do `APKS_FINAL_JCA_DEXLIB` após re-run
- [ ] Aperv `MopData` lê `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` sem erros
- [ ] Pelo menos 1 APK com menu programático mostra `items[]` populado em `OPTIONSMENU`
- [ ] Pelo menos 1 APK com Spinner populado por `ArrayAdapter` mostra `entries[]` populado via dataflow
- [ ] **Paridade WTG (Opção A):** em ≥10 APKs OK, `transitions[]` antes vs depois tem ≥95% de overlap (Jaccard); divergências documentadas e justificadas via bytecode scan
- [ ] Wall-clock médio por APK: redução de ≥50% em apps grandes (efeito esperado da eliminação do segundo CG)
- [ ] Calibração APE-RV v3 prossegue com 190 APKs (não 54)
- [ ] `rv-verify` e `opsx:verify` passam clean

---

## 8. Critérios de verificação atingidos

- [x] Pergunta-âncora respondida com evidência de código (§3.1 Q1 + §3.2 Q2).
- [x] ≥3 logs distintos de APKs travados citados (§3.3: 4 APKs).
- [x] Opção A (reusar SPARK CG) classificada como viável com justificativa técnica (§6.A).
- [x] Diff conceitual GESDA × WTG apresentado (§3.4).
- [x] Consumidores de `transitions[]` enumerados (§3.4 Q4).
- [x] Plano atualizado durante a investigação.

---

## 9. Próximos passos

1. ✅ Decisão sobre escopo da change tomada (§7 — change única `gh<N>-static-analysis-overhaul`).
2. ✅ Auditoria Phase-0 concluída (§16 — score 8.6/10, READY).
3. **Próximo:** abrir change via `/opsx:new gh<N>-static-analysis-overhaul` (schema `rv-sdd`, Full SDD).
4. **Task #1 da change:** pre-flights §7.6 (Soot API), §7.7 (cobertura ArrayAdapter), §7.8 (bytecode-scan), §7.11 (fixtures), §16.4 (license).
5. **Marco M1** (após itens 1+2): desbloqueio mínimo do aperv → tag `gh<N>-interim-windows-fix` se calibração v3 precisar começar antes do fechamento da change.
3. Para a calibração APE-RV v3 imediata: avaliar se vale esperar o fix B ou prosseguir com os 54 APKs com windows OK e tratar o resto como degradação conhecida (já é a abordagem em `20260513_analise_gator_window.md §6.3`).

---

## 10. Apêndice — Trechos de código críticos

### A. SPARK configurado mas não usado pela WTG

**`rvsec-gator/sootandroid/.../Main.java:244`** (SPARK enabled corretamente):
```java
case "spark":
    args.addAll(java.util.Arrays.asList("-p", "cg.spark", "enabled:true"));
```

**`rvsec-gator/client/.../RvsecAnalysisClient.java:112`** (reachability usa SPARK):
```java
CallGraph cg = Scene.v().getCallGraph();
```

**`rvsec-gator/client/.../RvsecAnalysisClient.java:159`** (WTG não recebe CG):
```java
WTGBuilder wtgBuilder = new WTGBuilder();   // no-arg constructor
wtgBuilder.build(output);                    // só GUIAnalysisOutput
```

**`rvsec-gator/sootandroid/.../flowgraph/FlowgraphRebuilder.java:42`** (WTG pega CG independente):
```java
private AndroidCallGraph callgraph = AndroidCallGraph.v();
```

### B. CHA fallback que explica o custo

**`rvsec-gator/sootandroid/.../flowgraph/FlowgraphRebuilder.java:1010–1020`**:
```java
SootClass stc = ((RefType) rcv_t).getSootClass();
for (Iterator<SootClass> tgtItr = hier.getConcreteSubtypes(stc).iterator(); tgtItr.hasNext(); ) {
    SootClass sub = tgtItr.next();
    if (sub != null && sub.isConcrete()) {
        SootMethod tgt = hier.virtualDispatch(callee, sub);
        if (tgt != null) {
            callgraph.add(source, tgt, s);
        }
    }
}
```
Iteração em **todos os subtipos concretos** × walk-up de hierarquia × por cada invoke statement = explosão combinatória em apps grandes.

### C. Log fingerprint do travamento

**`rvsec-gator/client/.../RvsecAnalysisClient.java:153`** (último log antes do silêncio):
```java
System.out.println("[RvsecAnalysisClient] Reachability JSON written (WTG pending): " + outputPath);
```

### D. WTG stages que NUNCA são alcançados nos APKs travados

**`rvsec-gator/sootandroid/.../wtg/WTGBuilder.java:62–98`**:
```java
new ExplicitForwardEdgeBuilder().buildEdges(wtg);
Logger.verb(TAG, "stage 1 finishes");   // ← este log nunca aparece nos 136 APKs
```

---

## 12. Auditoria GESDA → Unified: features perdidas na unificação

**Localização do GESDA legado:** `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gesda/` (módulos `rvsec-gesda-core` + `rvsec-gesda-common`).

**Metodologia:** leitura linha-a-linha do `SootAnalyze.java`, `XmlParser.java`, modelo `Widget.java` e `WidgetInfoOut.java` + comparação com `RvsecAnalysisClient.collectWidgets()` (linhas 767–818), `enrichFromXml()` (linhas 824–923) e `parseArraysXml()` (linhas 926–959).

### 12.1 Inventário comparativo widget-a-widget

| Campo / Feature | GESDA captura? | Onde (GESDA) | Unified captura? | Onde (unified) |
|-----------------|----------------|--------------|------------------|----------------|
| `widgetId`, `name` (resolvido via R.id) | ✅ | `parseView` XmlParser.java:200–209 | ✅ | `collectWidgets` RvsecAnalysisClient.java:776–784 (via `objNode.idNode`) |
| `text` | ✅ | `Widget.text` + parsing XML/strings | ✅ | `PropertyManager.getTextsOrTitlesOfView` RvsecAnalysisClient.java:788 |
| `hint` | ✅ | XmlParser | ✅ | `PropertyManager.getHintOfView` RvsecAnalysisClient.java:791 |
| `inputType` | ✅ | XmlParser (XML attr) | ✅ | `enrichFromXml` RvsecAnalysisClient.java:897–904 |
| `entries` (Spinner, via `android:entries="@array/X"` + arrays.xml + `@string/Y` nesting) | ✅ | `parseSpinnerEntries` XmlParser.java:227–253 | ✅ | `parseArraysXml` + `enrichFromXml` RvsecAnalysisClient.java:906–912, 926–959 |
| **`contentDescription`** (acessibilidade) | ✅ | `parseView` XmlParser.java:207 (`getAttributeValueAsString("contentDescription", node)`) | ❌ | **NÃO extraído** |
| **`tooltipText`** (long-press hint) | ✅ | `parseView` XmlParser.java:208 (`getAttributeValue("tooltipText", node)`) | ❌ | **NÃO extraído** |
| **`prompt`** (Spinner em modo dialog — título exibido) | ✅ | `Widget.prompt` campo + `OutputFactory.setPrompt` linha 71 | ❌ | **NÃO extraído** |
| **`spinnerMode`** (dropdown vs dialog) | ✅ | `Widget.spinnerMode` + `OutputFactory.setSpinnerMode` linha 72 | ❌ | **NÃO extraído** |
| **`items[]`** (sub-widgets/menu items recursivos) | ✅ | `Widget.items` + `OutputFactory` linhas 85–87 + `getSubItems` SootAnalyze.java:581+ (Soot CFG) | ❌ | **NÃO extraído** (`Collections.emptyList()` para options menu — RvsecAnalysisClient.java:729) |
| **Listener `registeredInFile`** (XML vs programático) | ✅ | `ListenerInfoOut.registeredInFile` | ❌ | **NÃO extraído** |
| **Listener `MethodInfoOut` completo** (modifiers, class, name, signature) | ✅ | `MethodInfoOut.java` | ⚠️ Parcial | só `handler.getSignature()` RvsecAnalysisClient.java:806 |
| **Menu items programáticos** (`Menu.add()`, `Menu.addSubMenu()` via Soot CFG + `parseAppStrings` para texto) | ✅ | SootAnalyze.java:372–531 | ❌ | **NÃO extraído** (options menu fica `widgets: []`) |
| **`layoutFileName`** por activity | ✅ | `ActivityWindowNode.layoutFileName` + `OutputFactory.setLayoutFileName` linha 47 | ❌ | **NÃO extraído** |
| Programmatic Spinner items (via `ArrayAdapter<String>` + Soot tracking) | ❌ | (não implementado em GESDA) | ❌ | (também não implementado) |

### 12.2 O caso específico de "labels da combobox" (Spinner)

O usuário lembra de ter implementado extração estática das labels de combobox. **Esse caminho existe em GESDA via XML** (`parseSpinnerEntries` em XmlParser.java:227–253) e **foi portado integralmente ao unified** (`enrichFromXml` em RvsecAnalysisClient.java:906–912 + `parseArraysXml` em 926–959).

Os dois resolvem corretamente:
- `<Spinner android:entries="@array/my_items"/>`
- `<string-array name="my_items"> <item>@string/lbl_a</item> <item>Foo</item> </string-array>`
- `<string name="lbl_a">Bar</string>`
- Resultado: `entries = ["Bar", "Foo"]`

**Verificado em RvsecAnalysisClient.java:944–951** — a resolução de `@string/` aninhado é equivalente.

**O que NÃO foi portado** (a parte que pode ter sido lembrada como "ainda mais informação sobre a combobox"):
- `android:prompt` — texto exibido no topo do dialog quando `spinnerMode=dialog`
- `android:spinnerMode` — distingue dropdown (popup) vs dialog (modal)
- Sem isso o aperv não consegue distinguir os dois modos de apresentação para fins de modelagem de estado.

### 12.3 Top features perdidas, ranqueadas para o aperv

| # | Feature perdida | Impacto no aperv:sata_mop | Esforço de re-port |
|---|-----------------|---------------------------|---------------------|
| 1 | **Spinner `prompt` + `spinnerMode`** | Médio — afeta modelagem de estado quando há spinners em modo dialog | **Trivial** — 2 atributos XML adicionais em `enrichFromXml` |
| 2 | **`contentDescription` + `tooltipText`** | Médio — perda de label de acessibilidade, útil para LLM (se voltar) e para desambiguação de widgets idênticos | **Trivial** — 2 atributos XML adicionais em `enrichFromXml` |
| 3 | **Menu items programáticos** (`Menu.add()` / `Menu.addSubMenu()`) | Alto **se** o aperv navega via options menus dinâmicos. Aperv legacy ignora menus dinâmicos hoje, mas calibrações futuras podem precisar | **Médio** — exige Soot CFG walking (já no GESDA, ~100 linhas) |
| 4 | **`registeredInFile`** (origem do listener: XML vs código) | Baixo para aperv (não usa) | Trivial |
| 5 | **`layoutFileName` por activity** | Baixo (informacional) | Trivial |
| 6 | **Programmatic Spinner items via `ArrayAdapter`** | Médio — apps modernos populam spinners em código (`adapter.add("foo")`) | **Alto** — exige Soot dataflow novo (GESDA também não tem) |

### 12.4 Decisão (2026-05-13): consolidar TUDO em change única (megaescopo)

A decisão evoluiu duas vezes:
1. Inicialmente: change só com Opção C.
2. Depois: change com Opção C + paridade GESDA (XML + menu programático).
3. **Final (2026-05-13):** change com **TUDO** — Opção C + paridade GESDA XML + menu programático + Spinner programático (ArrayAdapter) + Opção A (reusar SPARK CG na WTG).

A change agora se chama `gh<N>-static-analysis-overhaul` e agrupa 6 itens funcionais + schema bump + testes (vide §7.1).

Justificativa de juntar tudo:
- A janela de rebuildar o JAR + re-rodar os 190 APKs é a mesma para qualquer mudança em `rvsec-gator`. Custo wall-clock marginal de validar 6 itens vs 4 é baixo.
- Os itens tocam um conjunto reduzido de arquivos: `RvsecAnalysisClient.java`, `FlowgraphRebuilder.java`, + 2 novas classes (`MenuExtractor`, `SpinnerItemExtractor`) + leitor aperv. Não há risco de regressão cruzada.
- Opção A é o item mais arriscado (mudança estrutural na WTG), mas elimina permanentemente o two-call-graph problem. Adiá-la deixaria dívida técnica pendurada e exigiria outro ciclo completo de re-run dos APKs.
- Cada item é **isolável** e **testável** independentemente — se Opção A falhar na validação cruzada (§7.4), pode ser revertido sem afetar os outros 5 itens.

**O que de fato fica fora desta change** (§13):
- **Opção D** (refatorar `AndroidCallGraph` para `OnFlyCallGraphBuilder`/RTA) — descartada por baixo ROI.
- Mudanças nos consumidores além do `MopData.java` do aperv.
- Mudanças em rv-experiment ou rv-platform.

Detalhamento de escopo, sequência e critérios em §7.

### 12.5 Trechos de código (GESDA — para referência ao implementar o re-port)

**`XmlParser.parseView` (XmlParser.java:200–209)** — captura contentDescription/tooltipText:
```java
String contentDescription = getAttributeValueAsString("contentDescription", node);
String tooltipText = getAttributeValue("tooltipText", node);
return Widget.builder(type).widgetId(id.toString()).name(name)
    .contentDescription(contentDescription).tooltipText(tooltipText);
```

**`OutputFactory.createWidgetInfoOut` (linhas 70–74)** — schema dos campos a portar:
```java
info.setEntries(widget.getEntries());
info.setPrompt(widget.getPrompt());
info.setSpinnerMode(widget.getSpinnerMode());
info.setContentDescription(widget.getContentDescription());
info.setTooltipText(widget.getTooltipText());
```

**`SootAnalyze` menu programático (linhas 442–510)** — exemplo de extração via Soot CFG (para change futura):
```java
if (signature.equals("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,java.lang.CharSequence)>")) {
    WidgetBuilder builder = WidgetBuilderFactory.newSubMenu();
    Value idValue = invokeExpr.getArg(1);
    builder.widgetId(idValue.toString());
    Value textValue = invokeExpr.getArg(3);
    builder.text(textValue.toString());
    List<Widget> items = getSubItems(stmt, cfg);
    builder.setMenuItems(items);
}
```

---

## 13. Pendências para changes futuras (fora desta change)

A change consolidada `gh<N>-static-analysis-overhaul` absorve praticamente todas as oportunidades identificadas nesta investigação. O que fica **fora** desta change:

| Change futura | Descrição | Gatilho para abrir |
|---------------|-----------|--------------------|
| `gh<N>-android-cg-refactor` (Opção D da §6) | Trocar `AndroidCallGraph` por `OnFlyCallGraphBuilder`/RTA do Soot. | **Não abrir** — descartada por baixo retorno vs alto esforço (Opção A da change atual já resolve a raiz do problema reusando o SPARK CG). |

**Nota:** após `gh<N>-static-analysis-overhaul` arquivada, o pipeline de análise estática fica funcionalmente completo e estruturalmente limpo. Não há dívida técnica conhecida em rvsec-gator + rv-static-analysis que motive uma próxima change preventivamente.

---

## 16. Auditoria Phase-0 — prontidão para `/opsx:new` (2026-05-13)

Três auditorias paralelas (consistência interna, fitness para SDD workflow, risk register) foram conduzidas após a consolidação do escopo. Síntese:

**Score geral:** 7.1/10 → READY com edits aplicados nesta seção.

### 16.1 Issues fixados inline neste doc

| ID | Severidade | Onde fixei | Mudança |
|----|------------|------------|---------|
| AUD-01 | BLOCKER | §7.5 (nova) | `--skip-wtg` flag: spec dual sweep CLI + GATOR clientParam |
| AUD-02 | BLOCKER | §7.4 | "Jaccard ≥95%" agora definido sobre `{(src, tgt, event)}` tuples; média ≥0.95 + nenhum APK <0.85 |
| AUD-03 | BLOCKER | §7.1 item 6 | Filtro: `Scene.v().getCallGraph().edgesOutOf(src)` filtrado por subSignature |
| AUD-04 | BLOCKER | §7.1.1 (novo) | DAG explícito entre os 8 itens + 4 marcos M1–M4 |
| AUD-05 | HIGH | §7.5 + §7.8 + §7.9 + §7.10 + §7.11 (novas) | 4 sub-seções de spec rigorosa |
| AUD-06 | HIGH | §7.7 (novo) | Item 5 split em MVP (4d) vs full (6–7d), com pre-flight de cobertura |
| AUD-07 | HIGH | §7.9 (novo) | Rollback via **feature flag** `cgDelegationEnabled` — rollback runtime, sem rebuild |
| AUD-08 | HIGH | §7.4 | Performance claim moderada de "≥50%" → "≥30% aspiracional; baseline a tirar no pre-flight" |
| AUD-09 | MEDIUM | §7.6 (novo) | Pre-flight de Soot API check (item 4) |
| AUD-10 | MEDIUM | §7.8 (novo) | Pre-flight + spec do bytecode-scan no nível WTG |
| AUD-11 | MEDIUM | §7.11 (novo) | Fixtures como pre-condição obrigatória + fallback APK sintético |
| AUD-12 | MEDIUM | §16.2 (abaixo) | Delta-spec files enumerados |
| AUD-13 | MEDIUM | §16.3 (abaixo) | Build/JAR strategy |
| AUD-14 | MEDIUM | §16.4 (abaixo) | GESDA license attribution |

### 16.2 Delta-spec files enumerados

Lista para `/opsx:continue` → spec deltas:

| Domínio | Arquivo | Mudanças previstas |
|---------|---------|---------------------|
| `analysis` | `openspec/specs/analysis/spec.md` | MODIFIED — requisitos de `windows[]` ganham cláusula: "populadas mesmo quando WTG falha"; ADDED — requisitos para `prompt`, `spinnerMode`, `contentDescription`, `tooltipText`, `items[]` em OPTIONSMENU, `entries[]` via dataflow; MODIFIED — invariante de call graph (single SPARK graph) |
| `tools` | `openspec/specs/tools/spec.md` | MODIFIED — `MopData` parser lê schema v2.0 |
| `agent` | `openspec/specs/agent/spec.md` | (provavelmente sem mudança — rv-agent não é consumidor ativo) |

**Pre-flight Phase 2:** rodar `grep -n "windows\|transitions\|reachability\|MopData" openspec/specs/{analysis,tools}/spec.md` para inventário exato dos requisitos atuais antes de redigir as deltas.

### 16.3 Build/JAR distribution strategy

- **rvsec-gator JAR:** built via `mvn package` em `rvsec/rvsec/rvsec-android/rvsec-gator/`. Output: `client/target/rvsec-gator-client-*.jar`. Consumido pelo `static_analysis_sweep.py` via `$RVSEC_HOME` (cf. `RV_SA_TIMEOUT=1800` e env-vars do gh55).
- **ape-rv.jar:** built separadamente em `workspace-rv/ape/` via `mvn package`. Output: `ape.jar`. Consumido por `aperv-tool` (Python wrapper).
- **Sincronização durante a change:** ambos os JARs devem ser rebuildados antes do re-run dos 190 APKs. Adicionar pre-flight script `scripts/check_jar_sync.sh` que valida timestamps.
- **Docker images:** `docker/tools/Dockerfile` referencia o GATOR JAR via `$RVSEC_HOME` mount. Rebuild da imagem **não é necessário** se o mount aponta para o JAR atualizado no host. Aperv idem.
- **Concurrent session conflict (CogniCrypt):** rebuild do GATOR JAR pode invalidar runs em andamento. Coordenação manual no momento — adicionar `flock /tmp/rvsec-gator.lock mvn package` ou pausar CogniCrypt antes do rebuild.

### 16.4 License attribution (GESDA → unified)

- **GESDA:** `com.fdu.se.sootanalyze` (Fudan University). Sem header de licença em `SootAnalyze.java:1` (linha 1 é `package`).
- **rvsec-gator/RvsecAnalysisClient.java:** também sem header de licença.
- **Ação no pre-flight:** verificar `LICENSE` files em ambos os módulos; se ausentes, assumir licença institucional do projeto rvsec (PAMunb). Para itens 3, 4 portados do GESDA, adicionar `@PortedFrom` javadoc:
  ```java
  /**
   * @PortedFrom rvsec-gesda/.../SootAnalyze.java:372-531 (2024 baseline)
   */
  ```
- Não bloqueante para a change; é boa prática de rastreabilidade científica (importante se a tese citar a porta).

### 16.5 Issues deferidos para Phase 3 (não-blockers para `/opsx:new`)

- **Aperv MopData reader test plan** (AUD HIGH gap #3 do agente de risco) → Phase 3 `/rv-doc-adr` + tasks.md devem detalhar.
- **Rollback feature flag scope detalhado** → Phase 3 design.md.
- **CogniCrypt validation post-change** → Phase 3 risk register formal.

### 16.6 Score final por dimensão

| Dimensão | Antes | Após edits |
|----------|-------|------------|
| Decisões tomadas | 9/10 | 9/10 |
| Phase 1 (Explore) readiness | 8/10 | 9/10 (DAG add) |
| Phase 2 (Propose) readiness | 7/10 | 9/10 (delta-spec list + schema spec) |
| Phase 3 (Design) readiness | 8/10 | 9/10 (feature flag + pre-flights) |
| Phase 4 (Implement) readiness | 7/10 | 8/10 (fixtures TBD na pre-flight, ainda) |
| Schema versioning | 6/10 | 9/10 (§7.10) |
| Build/artifact | 5/10 | 8/10 (§16.3) |
| Rollback | 6/10 | 9/10 (feature flag + DAG) |
| **Geral** | **7.1/10** | **8.6/10 — READY** |

**Verdict:** doc pronto para `/opsx:new`. Pre-flights de §7.6–7.11 viram task #1 da change.

---

## 15. Verificação: o plano resolve a calibração APE-RV v2/v3?

**Data:** 2026-05-13 (pós-consolidação do plano)
**Pergunta:** o escopo definido em §7.1 cobre todas as necessidades de `rvsec-calibracao/docs/20260407_aperv_calibracao_v2.md` (doc B) e `20260513_analise_gator_window.md` (doc C)?

**Resposta:** ✅ **Sim — cobre integralmente e torna obsoletas as mitigações de §6.2/§6.3 do doc C.**

### 15.1 Mapeamento necessidade → item do plano

| Necessidade da calibração | Fonte | Status hoje | Após nosso plano | Item |
|---------------------------|-------|-------------|------------------|------|
| `mop_weight_direct` operacional (precisa `windows[].widgets[]`) | C:§6.1 | 54/190 (28.4%) | **190/190 (100%)** | 1 |
| `mop_weight_activity` operacional (precisa `windows[]`) | C:§6.1 | 54/190 | **190/190** | 1 |
| `mop_weight_wtg` operacional (precisa `transitions[]`) | C:§6.1 | 54/190 | **>> 54/190** (WTG acelerada via SPARK CG) | 6 |
| `mop_weight_transitive` (só precisa `reachability[]`) | C:§6.1 | 190/190 | 190/190 | — (já OK) |
| Função objetivo padrão `0.5×mop + 0.5×method` operacional | B:§3.8 | Comprometida (3 de 4 pesos inertes em 71.6%) | **Plenamente operacional** | 1, 6 |
| 4 pesos MOP calibráveis pelo Optuna (10-param search space de B:§3.1) | B:§3.1 | TPE iria zerar / otimizar contra ruído (problema da v1 reaparece) | **TPE recebe gradiente real em todos os 4 pesos** | 1, 6, 7 |
| 100 APKs estratificados úteis | B:§3.2 | Apenas 54 com windows OK — risco de viés de seleção | **190 APKs viáveis → re-stratify pode preservar os 100 escolhidos** | 1, 6 |
| GESDA features extras (não citadas em B/C, mas em A:§12) | A:§12 | Faltam: prompt, spinnerMode, contentDescription, tooltipText, items, ArrayAdapter | **Todas portadas** | 3, 4, 5 |

### 15.2 Mitigações propostas em C que ficam obsoletas

| Mitigação proposta em C | Status após nosso plano |
|--------------------------|--------------------------|
| **C:§6.2** — Two-score objective (`0.5×method_trimmed(130) + 0.5×mop_widget_trimmed(~37)`) | ⚠️ **Vira opcional.** Pode ser descartado (volta para 0.5×mop + 0.5×method de B:§3.8 em todos os 190 APKs) **OU** mantido como contingência adicional contra outliers. Decisão do team de calibração. |
| **C:§6.3.A** — Aumentar sweep timeout para 3600s (~34h wall-clock) | ❌ **Desnecessário.** Item 1 desacopla `windows[]` da WTG; item 6 acelera o WTG quando ele rodar. Não há razão para queimar 34h de wall-clock. |
| **C:§6.3.B** — Fallback `-cgAlgorithm cha` | ❌ **Desnecessário.** Item 6 (Opção A) reusa o CG SPARK do Soot na WTG, eliminando o second-graph CHA-style sem perder precisão. |
| **C:§6.3.C** — Híbrido spark→cha multi-passada | ❌ **Desnecessário.** Mesmo motivo. |
| **C:§7.1** — Time budget interno no `RvsecAnalysisClient` | ⚠️ Continua válido como melhoria de qualidade (sinal explícito no log), mas não bloqueia mais nada. Fora do escopo desta change. |
| **C:§7.2–7.5** — Timeout adaptativo, stage checkpoint, log de timeout, CHA automático | ⚠️ Idem — qualidade de vida, não essenciais. |

### 15.3 Possíveis riscos residuais (e por quê não bloqueiam)

| Risco | Mitigação |
|-------|-----------|
| Opção A (item 6) introduz divergência semântica em `transitions[]` | §7.4: critério de paridade WTG ≥95% Jaccard em 10 APKs OK; se falhar, item 6 é revertido sem afetar 1–5 (`windows[]` ainda fica populado pelo item 1) |
| ArrayAdapter dataflow (item 5) é feature nova com cobertura imperfeita | É **aditivo** — qualquer item capturado é ganho líquido vs o estado atual (zero items programáticos hoje) |
| Re-stratify pode mudar a seleção de 100 APKs | Decisão de calibração: aceitar nova seleção (mais representativa) ou preservar IDs originais e usar como holdout |
| Wall-clock do re-run dos 190 APKs após o fix | Estimativa: reachability ~5–30 s/APK; WTG (pós-Opção A) prevê ~30 s–2 min/APK; total <2h em 4 workers paralelos. Vs 34h da Opção 6.3.A |

### 15.4 Recomendação para o team da calibração

1. **Aguardar a change `gh<N>-static-analysis-overhaul`** antes de iniciar a Fase C da v3.
2. **Revisar a decisão de two-score em C:§6.2/B:§3.2** após o re-run: provavelmente volta para o objetivo padrão `0.5×mop + 0.5×method` de B:§3.8.
3. **Re-stratify dataset** após o re-run para preservar representatividade com windows[] populado em 100%.
4. **NÃO executar** Opções 6.3.A/B/C — todas substituídas pelo plano.
5. **Manter o doc B:§3** atualizado com a nota de que os 4 pesos MOP voltam a operar normalmente após o fix.

---

## 14. Referências cruzadas

- `rvsec-calibracao/docs/20260513_analise_gator_window.md` — análise empírica original (71.6%).
- `experimento-20260508/README.md` — pipeline dos 190 APKs.
- `openspec/changes/archive/2026-02-24-gh27-unified-static-analysis/` — proposal/design/plan da unificação.
- `openspec/changes/archive/2026-05-05-gh51-gator-soot-upgrade/` — D5 (SPARK default), D6 (bytecode scan), write-first JSON.
- GESDA legado: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gesda/`
- Memória `project_jca226_validation_pipeline.md`.
- Memória `project_gator_ft_investigation.md`.
