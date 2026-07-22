# APE-RV: Investigação e Melhoria do Mapeamento de Coordenadas LLM (gh46)

**Data**: 2026-03-18
**Status**: Planejamento
**Dependências**: exp3 concluído (507/507 tasks), gh41 (LLM variants), gh42 (calibration params)
**Contexto**: `docs/20260316_aperv_llm.md` (LLM integration), `docs/20260318_rvape_calibracao.md` (calibração)
**Repositórios**: `ape` (Java — matching algorithm) + `rv-android` (Python — testes, scripts)

---

## 1. Problema

O APE-RV usa Qwen3-VL para sugerir ações via coordenadas visuais. Quando o LLM retorna coordenadas, o `LlmRouter.mapToModelAction()` tenta mapear para um widget clicável. Se não encontra, registra `no_match` e faz fallback para exploração algorítmica.

### 1.1 Dados do Exp3 (507 tasks, 169 APKs × 3 reps)

| Métrica | Valor |
|---------|-------|
| Total LLM calls | 9.525 |
| matched | 5.919 (62,1%) |
| no_match | 3.554 (37,3%) |
| null (infraestrutura) | 52 (0,5%) |

### 1.2 Distribuição de no_match por APK

| Faixa | APKs | % |
|-------|------|---|
| 0% (perfeito) | 4 | 2,4% |
| 1-25% | 20 | 11,8% |
| 26-50% | 80 | 47,3% |
| 51-75% | 35 | 20,7% |
| 76-100% | 18 | 10,7% |

8 APKs com 100% no_match. 80 APKs (47%) na faixa 26-50% — a maioria. Apenas 4 APKs com 0%.

### 1.3 Impacto

O exp3 mostrou que `aperv:sata_mop_llm` (27,60% method) não superou `aperv:sata_mop_v1` (28,35%, p=0,014). Cada no_match desperdiça 1-3s de overhead (LLM call) sem benefício, e a ação de fallback algorítmico pode ser subótima comparada com uma ação guiada pelo LLM. Reduzir no_match de 37% para <20% pode destravar o potencial do LLM.

---

## 2. Arquitetura Atual do Mapeamento

### 2.1 Fluxo de Coordenadas — Timing Gap Crítico

```
          ┌─── buildAndValidateNewState() ───────────────────────────────┐
          │                                                               │
          │  1. AccessibilityNodeInfo dump   ← HIERARQUIA CAPTURADA AQUI │
          │  2. GUITree construída                                        │
          │  3. State criado, actions[] extraídas com bounds              │
          │                                                               │
          └───────────────────────────────────────────────────────────────┘
                                      │
                              ΔTIME (gap temporal)
                     validação, graph updates, saveGUI...
                                      │
          ┌─── selectNewActionNonnull() → LlmRouter.selectAction() ──────┐
          │                                                               │
          │  4. ScreenshotCapture.capture()  ← SCREENSHOT FRESCO AQUI    │
          │  5. ApePromptBuilder.build()     ← usa bounds do passo 3     │
          │  6. LLM vê screenshot (passo 4) + widget list (passo 3)      │
          │  7. LLM retorna coordenada                                    │
          │  8. mapToModelAction()           ← usa bounds do passo 3     │
          │                                                               │
          └───────────────────────────────────────────────────────────────┘
```

**Problema fundamental**: O LLM vê um screenshot FRESCO (passo 4), mas o matching acontece contra bounds de um dump ANTERIOR (passo 1). Se entre os passos 1 e 4 o UI mudou (toast, dialog, animação, content dinâmico), o LLM pode clicar corretamente num elemento que existe visualmente mas **não existe na lista de ModelActions**.

### 2.2 Fontes de Dados — O Que o LLM Vê vs O Que o Matching Usa

| Dado | Fonte | Momento | Fresco? |
|------|-------|---------|---------|
| Screenshot para o LLM | `ScreenshotCapture.capture()` | No `selectAction()` | ✅ Sim |
| Widget list no prompt | `state.getActions()` → `node.getBoundsInScreen()` | No `buildAndValidateNewState()` | ❌ Potencialmente stale |
| Bounds para matching | Mesmos `state.getActions()` | Idem | ❌ Potencialmente stale |

**O LLM vê a tela real. O matching usa o modelo.** Se discordam, o resultado é `no_match` — mesmo que o LLM tenha acertado.

### 2.3 O Que NÃO Está na Lista de ModelActions

Elementos visuais que o LLM pode ver no screenshot mas que **não existem como ModelActions**:

1. **Elementos dinâmicos**: Toasts, snackbars, floating action buttons que apareceram depois do dump
2. **Overlays do sistema**: Permission dialogs, "Application Not Responding", notifications
3. **Widgets não-modelados**: O `GUITreeBuilder` faz filtragem/abstração — containers, layouts, decorações que o UIAutomator vê mas o APE ignora (android.view.View, Layout classes, etc.)
4. **Custom Views**: Widgets desenhados via Canvas que não têm nós no accessibility tree
5. **Elementos de transição**: Loading spinners, progress bars durante animação

O LLM pode estar clicando corretamente num desses elementos — e o matching classifica como `no_match`.

### 2.4 Prompt Format (ApePromptBuilder)

**System message**: Instruções de exploração com regras de prioridade ([DM]/[M] > unvisited > visited).

**Widget list** (por step):
```
[0] Button "CIPHER" @(500,207) [DM] (v:0)
[1] EditText hint="Enter message" @(300,150) (v:0)
[2] Button "EXECUTE" @(540,767) [M] (v:2)
```

Coordenadas normalizadas [0,1000). O LLM vê a lista E o screenshot.

**Action history**: Últimas 5 ações com resultado.

### 2.5 Matching Algorithm (LlmRouter.mapToModelAction, linhas 364-473)

Estratégia em 5 passos, nesta ordem:

1. **Back action**: Se `actionType == "back"` → `state.getBackAction()`
2. **Boundary rejection**: Rejeita se `pixelY < height × 0.05` (status bar, <96px) ou `pixelY > height × 0.94` (nav bar, >1804px)
3. **Bounds containment**: Itera todos os widgets, encontra o menor cujos bounds contêm `(pixelX, pixelY)`. Para `type_text`, restringe a campos de input (EditText, SearchView). Para `long_click`, prefere `MODEL_LONG_CLICK`.
4. **Long-click retry**: Se step 3 falhou com `long_click`, tenta novamente com qualquer tipo de click.
5. **Euclidean fallback**: Encontra widget mais próximo (center-to-point distance) dentro de tolerância:
   ```
   tolerance = max(50.0, min(widget_width, widget_height) / 2.0)
   ```
   Mínimo 50px, ou metade do menor lado do widget. Retorna o mais próximo se `dist ≤ tolerance`.

Se nenhum step encontra match → `no_match`.

### 2.6 Telemetria Atual (por chamada LLM)

```
[APE-RV] LLM call=N mode=new-state action=click qwen=(x,y) pixel=(px,py)
         tokens_in=X tokens_out=Y time_ms=Z result=matched|no_match|null
```

**O que NÃO é logado** (gap de observabilidade):
- Lista de widgets candidatos com bounds
- Distância ao widget mais próximo em caso de no_match
- Qual passo do matching falhou (boundary? containment? Euclidean?)
- Se o UI mudou entre dump e screenshot

---

## 3. Dados Disponíveis

### 3.1 Traces do Exp3 (507 tasks)

Cada trace contém, por step:
- Lista de actions disponíveis com bounds: `g0a5[...]@MODEL_CLICK...resource-id=...;[836,1109,1050,1235][Donate]`
- Chamadas LLM com coordenadas e resultado
- Activity atual e estado do modelo

**Correlação step↔LLM**: parseável. LLM call N aparece entre `begin step [X]` e `begin step [X+1]`.

Localização: `data/results/exp3_{00..07}/exp3_{00..07}/<apk>/<apk>__<rep>__600__aperv:sata_mop_llm.trace`

### 3.2 Limitação CRÍTICA dos Traces para Replay Forense

O trace contém os **ModelActions com bounds** (modelo APE) e as **coordenadas LLM com resultado**. Com isso é possível replayar o matching algorithm.

**Porém**: O trace **NÃO contém**:
- O screenshot que o LLM viu
- O dump UIAutomator raw (XML completo com TODOS os nós)
- Elementos visuais que existiam na tela mas não viraram ModelActions
- O estado real do UI no momento da chamada LLM (só o estado do modelo)

**Consequência para o replay forense**: Podemos classificar no_match por proximidade ao widget mais próximo do MODELO, mas **não podemos saber se o LLM acertou num elemento dinâmico/não-modelado**. A Fase A vai rotular como "gap" (coordenada longe de qualquer widget) casos que na verdade podem ser hits corretos em elementos invisíveis ao modelo.

Isso cria uma **categoria fantasma**: no_match que parecem "erros do LLM" mas são na verdade "erros do modelo" (modelo incompleto ou stale). A Fase A' (re-run com logging enriquecido) é necessária para distinguir.

### 3.3 Screenshots + UI Dumps (468 tuplas)

**Localização**: `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/`

28 apps, 468 screenshots. Cada diretório contém triplas:
- `step-NNN.png` — screenshot
- `step-NNN.uiautomator` — XML dump (bounds, class, text, clickable, resource-id)
- `step-NNN.state` — JSON com view tree, activity, screen_size

### 3.4 Per-step XML dumps (destruídos no exp3)

O APE salva `step-N.xml` e `step-N.png` no device (`/sdcard/sata-<pkg>-ape-sata-running-minutes-10/`). No exp3, esses arquivos ficaram dentro do container Docker e foram destruídos no cleanup. **Não temos acesso** para os 507 tasks do exp3.

### 3.5 rvsec-vision-llm (framework de avaliação)

**Localização**: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-vision-llm/`

Framework completo de avaliação visual com:
- `VisionLLMClient`: wrapper LangChain para Qwen3-VL
- `ToolCallParser`: parser multi-formato (native, XML, JSON, markdown)
- `ClickValidator`: hit detection (50px tolerance)
- `CoordinateConverter`: normalização [0,1000)
- `UIAutomatorParser`: parsing de XML dumps
- Benchmark: 57,7% hit rate (Qwen3-VL, visual_only mode) nos 468 screenshots

---

## 4. Plano de Investigação — 5 Fases

### Fase A: Replay Forense dos Traces Exp3 (dados existentes)

**Objetivo**: Classificar cada no_match por causa raiz, usando os dados do MODELO (sabendo que há um ponto cego para elementos dinâmicos).

**Script**: `scripts/analyze_llm_nomatch.py` (one-off exploratório)

**Algoritmo**:

1. Para cada trace (507 traces):
   a. Parsear linhas `SATA begin step [N]` para delimitar steps
   b. Parsear linhas de actions com bounds: regex `(\d+) (g\da\d+).*\[(\d+),(\d+),(\d+),(\d+)\]`
   c. Parsear linhas LLM: `LLM call=(\d+).*qwen=\((\d+),(\d+)\) pixel=\((\d+),(\d+)\).*result=(\w+)`
   d. Para cada LLM call, associar ao step (baseado em posição no arquivo)

2. Para cada no_match:
   a. Extrair `pixel=(px, py)` da chamada LLM
   b. Extrair todos os widgets do step com seus bounds `[left,top,right,bottom]`
   c. **Replayar matching**:
      - Boundary rejection? (`py < 96` ou `py > 1804`)
      - Bounds containment? (existe widget cujo bounds contém o pixel?)
      - Euclidean: calcular distância ao centro de cada widget, verificar tolerância
   d. **Classificar**:

| Categoria | Critério | Pode ser elemento dinâmico? |
|-----------|----------|-----------------------------|
| `boundary_rejection` | `py < 96` ou `py > 1804` | Possível (status bar notification) |
| `edge_miss` | Widget mais próximo a ≤20px do bound (quase acertou) | Improvável |
| `tolerance_miss` | Distância 50-100px do widget mais próximo | Possível |
| `gap` | Distância >100px (coordenada em região sem widgets do modelo) | **Altamente provável** |
| `launcher` | Activity contém "Launcher" ou "com.google.android" | N/A (app crashou) |
| `few_widgets` | Step tem ≤2 widgets clicáveis | Possível (modelo incompleto) |
| `type_mismatch` | Widget existe no ponto mas tipo errado (ex: `type_text` em Button) | Não |

3. **Outputs**:
   - CSV detalhado: 1 linha por no_match (~3.554 linhas)
   - Relatório sumário: distribuição por categoria, top APKs por categoria
   - Heatmap de coordenadas no_match (onde na tela ocorrem mais falhas)
   - Distribuição de distância ao widget mais próximo (histograma)
   - **Flag de suspeita de elemento dinâmico**: `gap` + activity não é launcher → candidato para Fase A'

**Limitação explícita**: A Fase A classifica no_match contra o MODELO. Categorias `gap` e `tolerance_miss` podem incluir hits corretos em elementos dinâmicos. A Fase A' (re-run com observabilidade) é necessária para a ground truth.

---

### Fase A': Re-Run com Logging Enriquecido (ground truth)

**Objetivo**: Obter a ground truth de cada no_match distinguindo "LLM errou" de "modelo incompleto/stale".

**Ambas as opções serão implementadas**: logging enriquecido no Java + preservação de artefatos no Docker.

#### A'.1: Enriquecer logging no LlmRouter (Java, repo `ape`)

Modificar `LlmRouter.mapToModelAction()` para loggar em cada no_match:

```java
// Em caso de no_match, loggar diagnóstico completo:
Logger.iformat("[APE-RV] LLM no_match_diag call=%d pixel=(%d,%d) " +
    "nearest_widget=%s nearest_dist=%.1f nearest_bounds=[%d,%d,%d,%d] " +
    "total_actions=%d boundary_rejected=%b " +
    "containment_candidates=%d euclidean_within_tolerance=%b",
    callNumber, pixelX, pixelY,
    nearestWidget.getResolvedNodeResourceId(),
    nearestDistance,
    nearestBounds.left, nearestBounds.top, nearestBounds.right, nearestBounds.bottom,
    actions.size(),
    wasBoundaryRejected,
    containmentCandidates,
    euclideanWithinTolerance);
```

**Dados novos por no_match**:
- Widget mais próximo: resource-id, classe, bounds, distância
- Quantos widgets foram testados para containment
- Se boundary rejection descartou antes de testar
- Se Euclidean fallback tentou mas ultrapassou tolerância

**Esforço**: ~20 linhas de logging no `mapToModelAction()`. Rebuild JAR.

#### A'.2: Preservar screenshots + UIAutomator XML do device (Docker)

Modificar o entrypoint Docker para copiar os artefatos per-step ANTES do cleanup:

```bash
# No docker-entrypoint.sh, APÓS rv-experiment terminar:
SATA_DIR=$(find /sdcard -maxdepth 1 -name "sata-*" -type d | head -1)
if [ -d "$SATA_DIR" ]; then
    # Copiar screenshots e XMLs para o volume de resultados
    cp -r "$SATA_DIR" /results/sata_artifacts/
fi
```

**Artefatos preservados por task**:
- `step-N.xml` — UIAutomator dump raw (TODOS os nós, não só ModelActions)
- `step-N.png` — screenshot exato que o APE capturou naquele step

Com estes artefatos + o log enriquecido, podemos:
1. Comparar os nós do UIAutomator XML com os ModelActions do trace → quantificar over-abstraction
2. Ver o screenshot de cada step → verificar se o LLM acertou num elemento visual real
3. Calcular o timing gap entre dump e screenshot (se diferem visualmente)

#### A'.3: Re-run de subset diagnóstico

Rodar **15-20 APKs com maior no_match** × 1 rep × 600s com:
- JAR rebuild com logging enriquecido (A'.1)
- Docker entrypoint modificado (A'.2)
- Mesma configuração do exp3 (`aperv:sata_mop_llm`, defaults LLM)

**Outputs**:
- Traces com `no_match_diag` detalhado
- UIAutomator XMLs per-step (ground truth do UI real)
- Screenshots per-step
- **Classificação com ground truth**: para cada no_match, cruzar coordenada LLM com XML raw → determinar se havia um elemento no ponto que o modelo não capturou

**Estimativa**: 15 APKs × 1 rep × 680s ÷ 5 containers paralelos ≈ 35 min de execução. ~1 sessão de desenvolvimento (logging + Docker mod + análise).

---

### Fase B: Avaliação Offline com Prompt APE vs Prompt rvsec-vision-llm

**Objetivo**: Determinar se o formato do prompt do APE degrada a precisão do LLM comparado com o prompt otimizado do rvsec-vision-llm.

**Método**:

1. Selecionar 50 screenshots representativas das 468 tuplas (estratificado por app e tipo de elemento)
2. Para cada screenshot + .uiautomator:
   a. Parsear widgets clicáveis com bounds
   b. Para cada widget, chamar Qwen3-VL com **dois prompts**:
      - **Prompt APE**: replicar o formato do `ApePromptBuilder` (system message + widget list + exploration context)
      - **Prompt rvsec-vision-llm**: prompt otimizado do benchmark (visual_only mode)
   c. Coletar coordenadas retornadas pelo LLM
   d. Replayar matching algorithm para cada resposta
   e. Calcular hit rate (coordenada dentro dos bounds do widget-alvo)

3. **Outputs**:
   - Hit rate comparativo: APE prompt vs rvsec-vision-llm prompt
   - Diferença por tipo de widget (Button, ImageButton, EditText, etc.)
   - Análise qualitativa: em que casos o prompt APE causa o LLM a errar

**Infraestrutura**:
- SGLang server com Qwen3-VL-4B-Instruct (já disponível)
- Reutilizar `UIAutomatorParser`, `CoordinateConverter`, `ToolCallParser` do rvsec-vision-llm
- Script: `scripts/compare_prompts_llm.py` (one-off)

**Perguntas que a Fase B responde**:
- O prompt do APE é pior que o prompt otimizado? Se sim, quanto?
- O formato da widget list `@(x,y)` confunde o LLM? (LLM pode "copiar" coordenadas ao invés de "olhar" o screenshot)
- O action history ajuda ou atrapalha?

---

### Fase C: Melhorias no Matching + Testes de Integração (Java, repo `ape`)

**Objetivo**: Implementar melhorias no algorithm baseadas nos achados de A, A' e B, com testes de integração robustos como rede de segurança.

**C.1: Expandir fixtures de teste**

Atualmente o `CoordinateMapIntegrationTest.java` tem 5 fixtures do cryptoapp. Expandir para:
- 20-30 tuplas de 10+ apps diferentes (selecionadas das 468)
- Incluir apps com alto no_match (top 15 da lista)
- Incluir variedade de elementos: Button, ImageButton, EditText, CheckBox, SearchView
- Copiar `.uiautomator` files para `src/test/resources/fixtures/<app>/`

**C.2: Novos testes de integração**

| Teste | Descrição |
|-------|-----------|
| `allFixtures_boundsContainment_hitRate` | Para cada widget em cada fixture, normalizar center → denormalizar → verificar containment. Meta: 100% |
| `allFixtures_offsetCoords_euclideanFallback` | Center + offset aleatório (10-50px) → deve encontrar via Euclidean. Meta: >90% |
| `allFixtures_gapCoords_noFalsePositive` | Coordenadas em gaps entre widgets → deve retornar null (sem false positives) |
| `edgeMiss_smallOffset_shouldMatch` | Coordenadas 1-5px fora dos bounds → testar se tolerância resolve. Documenta comportamento atual |
| `typeText_onlyInputFields` | Coordenada em Button com `type_text` → null (filtro de tipo funciona) |
| `boundaryRejection_thresholds` | Coordenadas em boundary zones → rejection correto |
| `realNoMatchCoords_fromExp3` | Pegar coordenadas reais do exp3 (top 20 no_match) + widgets do step → reproduzir e entender |

**C.3: Melhorias potenciais no algorithm** (dependem dos achados de A, A' e B)

| Melhoria | Condição para implementar | Impacto esperado |
|----------|--------------------------|------------------|
| **Aumentar tolerância Euclidean** | Se Fase A mostra >30% `edge_miss` com dist < 80px | Recupera edge_miss sem false positives |
| **Weighted fallback** | Se Fase A mostra padrão por tipo de widget | Tolerância adaptativa por tipo/tamanho |
| **Fresh dump antes do LLM** | Se Fase A' mostra >15% dos `gap` são hits em elementos dinâmicos | Re-dump UI no momento da chamada LLM (custo: ~200ms) |
| **Prompt refinement** | Se Fase B mostra prompt APE < prompt otimizado | Melhorar ApePromptBuilder |
| **Skip launcher** | Se Fase A mostra >5% `launcher` | Detectar launcher no LlmRouter e skip LLM call |
| **Coordinate logging enrichment** | Sempre (já na A'.1) | Log do widget mais próximo + distância em cada no_match |
| **Adaptive threshold** | Se distribuição de distâncias é bimodal | Threshold dinâmico baseado em distribuição de widgets |
| **UIAutomator cross-check** | Se A' mostra over-abstraction significativa | Matching contra UIAutomator raw além do modelo |

**C.4: Melhoria potencial de maior impacto — Fresh Dump**

Se a Fase A' confirmar que uma fração significativa dos no_match é causada pelo timing gap (modelo stale), a solução mais direta é **re-capturar o UIAutomator dump no momento da chamada LLM**, em vez de usar o dump do `buildAndValidateNewState()`:

```java
// Em LlmRouter.selectAction(), ANTES de chamar o LLM:
// Opção 1: Fresh dump completo (~200-500ms overhead)
AccessibilityNodeInfo freshRoot = uiAutomation.getRootInActiveWindow();
List<Rect> freshBounds = extractAllBounds(freshRoot);
// Matching contra freshBounds em vez de state.getActions()

// Opção 2: Validação rápida (~50ms overhead)
// Apenas verificar se os bounds dos ModelActions ainda são válidos
// Se algum mudou → atualizar antes do matching
```

**Trade-off**: Fresh dump adiciona 200-500ms de latência por chamada LLM. Com ~18 chamadas/task, isso é +3.6-9s por task (~0.6-1.5% do timeout de 600s). Aceitável se eliminar >10% dos no_match.

---

## 5. Métricas de Sucesso

| Métrica | Baseline (exp3) | Meta |
|---------|-----------------|------|
| no_match rate | 37,3% | <20% |
| APKs com 100% no_match | 8 | 0 |
| APKs com >75% no_match | 18 | <5 |
| match rate | 62,1% | >80% |

Validação final: re-executar exp3 (ou subset de 30 APKs × 3 reps) com algorithm melhorado e comparar.

---

## 6. Testes de Integração — Estrutura no Repo `ape`

### 6.1 Organização de fixtures

```
ape/src/test/resources/fixtures/
├── cryptoapp/               # (existente, 5 tuples)
│   ├── 001.uiautomator
│   ├── 004.uiautomator
│   ├── 010.uiautomator
│   ├── 015.uiautomator
│   └── 020.uiautomator
├── yaab/                    # (novo)
│   ├── step-001.uiautomator
│   └── step-005.uiautomator
├── gitlab/                  # (novo, 100% no_match)
│   └── ...
├── leafpicrevived/          # (novo, app grande)
│   └── ...
└── ... (10+ apps)
```

### 6.2 Fonte das fixtures

As 468 tuplas em `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/` contêm `.uiautomator` (XML UIAutomator dump), que é o mesmo formato que o APE usa. Selecionar 20-30 representativas, priorizando:
- Apps com alto no_match no exp3
- Diversidade de tipos de elementos
- Apps com poucos e muitos widgets por tela

### 6.3 Padrão de teste (inspirado no rvsec-vision-llm)

O rvsec-vision-llm usa `ClickValidator` com tolerância de 50px e `CoordinateConverter` para normalização. Adaptar este padrão para o Java:

```java
// Pseudocode do padrão de teste
GUITreeNode[] nodes = loadFromUiautomator("fixtures/yaab/step-001.uiautomator");
List<ModelAction> actions = buildActionsFromNodes(nodes);

// Para cada widget clicável:
for (ModelAction action : actions) {
    int[] center = action.getWidgetCenter();
    int[] normalized = CoordinateNormalizer.toQwen(center[0], center[1], 1080, 1920);
    int[] denormalized = CoordinateNormalizer.toPixel(normalized[0], normalized[1], 1080, 1920);

    ModelAction matched = router.mapToModelAction("click", denormalized[0], denormalized[1], actions, state);
    assertNotNull("Should match widget at its own center", matched);
    assertEquals(action, matched);
}
```

---

## 7. Estimativa de Esforço

| Fase | Esforço | Dependências |
|------|---------|-------------|
| **A: Replay forense** | Script Python, ~1 sessão | Traces exp3 (disponíveis) |
| **A'.1: Logging enriquecido** | ~20 linhas Java + rebuild | Repo `ape` |
| **A'.2: Docker artifact preservation** | ~10 linhas shell | Docker entrypoint |
| **A'.3: Re-run diagnóstico** | ~35 min execução + análise | A'.1 + A'.2 prontos |
| **B: Comparação prompts** | Script Python + SGLang, ~1 sessão | SGLang server UP |
| **C.1: Expandir fixtures** | Seleção + cópia, ~30min | Tuplas em teste_llm/screenshots |
| **C.2: Testes integração** | Java, ~1-2 sessões | Fixtures prontas |
| **C.3: Melhorias algorithm** | Java, ~1-2 sessões | Achados de A, A' e B |
| **Validação** | Re-run exp subset, ~4-8h | Docker image rebuilt |

**Total**: ~5-7 sessões de desenvolvimento + tempo de execução

---

## 8. Sequência de Execução

```
┌─────────────────────────────────────────────────────────────┐
│ PARALELO 1                                                   │
│                                                               │
│  A (replay forense traces)  ──→ Relatório preliminar          │
│                                  (classificação MODELO-only)  │
│                                                               │
│  A'.1 (logging Java)  ─┐                                     │
│  A'.2 (Docker mod)     ─┤──→ A'.3 (re-run 15 APKs)          │
│                          │    ──→ Relatório GROUND TRUTH      │
│                          │        (elementos dinâmicos        │
│                          │         vs erros reais do LLM)     │
│                                                               │
│ PARALELO 2 (se SGLang UP)                                    │
│                                                               │
│  B (comparação prompts)  ──→ Prompt é fator?                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          │
                 Merge dos 3 relatórios
                          │
              ┌───────────┴───────────┐
              │   Decisões informadas  │
              │   (dados + evidência)  │
              └───────────┬───────────┘
                          │
              C.1 (fixtures) + C.2 (testes)
                          │
              C.3 (melhorias no algorithm)
                          │
              Validação (re-run subset 30 APKs)
                          │
              Calibração MICRO (gh46 → rvape_calibracao)
```

A e A' podem rodar em paralelo (A usa dados existentes, A' prepara re-run). B pode rodar em paralelo com ambas se SGLang estiver UP. C depende dos achados de A+A'+B.

---

## 9. Relação com Calibração

O plano de calibração (`docs/20260318_rvape_calibracao.md`) tem duas fases:
- **MACRO**: 14 params de exploração + MOP, sem LLM → **independente de gh46**
- **MICRO**: 5 params LLM (temperature, top_p, top_k, llm_on_new_state, llm_on_stagnation) → **depende de gh46**

A MACRO pode iniciar imediatamente. A MICRO deve aguardar os resultados de gh46 para garantir que o matching está otimizado antes de calibrar os params do LLM — caso contrário, o Optuna otimizaria em cima de um sistema com 37% de desperdício.

### 9.1 Pré-requisitos para MICRO

1. gh46 concluída (no_match < 20%)
2. MACRO concluída (params de exploração otimizados)
3. `llmMaxCalls` setado para 999999 no variant `sata_mop_llm`

---

## 10. Referência de Parâmetros Técnicos

### 10.1 Matching Algorithm

| Parâmetro | Valor Atual | Nota |
|-----------|-------------|------|
| Boundary top | 5% (96px) | Status bar |
| Boundary bottom | 94% (1804px) | Nav bar |
| Euclidean tolerance | `max(50, min(w,h)/2)` px | Mínimo 50px |
| Input field classes | EditText, AutoCompleteTextView, SearchView (Android + AndroidX) | Para `type_text` |
| Device dimensions | 1080×1920 (default, auto-detected) | Docker emulator padrão |

### 10.2 Prompt

| Parâmetro | Valor |
|-----------|-------|
| Coordinate space | [0, 1000) normalizado |
| Max history | 5 ações |
| MOP markers | [DM] (direct), [M] (transitive) |
| Action format | `[idx] ClassName "text" @(normX,normY) [MOP] (v:N)` |

### 10.3 rvsec-vision-llm Benchmark (referência)

| Métrica | Qwen3-VL (visual_only) |
|---------|----------------------|
| Hit rate | 57,7% |
| Tool call rate | 90,3% |
| Avg distance (hits) | 6,2px |
| Latency | 1.821ms |
| Tolerance | 50px |

---

## 11. Notas Técnicas

### 11.1 Parsing dos traces

O trace do APE contém informação suficiente para **replay parcial** (contra o modelo):

**Actions disponíveis** (com bounds):
```
     N gXaY[...]@MODEL_CLICK...class=...;resource-id=...;[left,top,right,bottom][text]
```

**LLM calls** (com coordenadas e resultado):
```
[APE-RV] LLM call=N mode=... action=... qwen=(qx,qy) pixel=(px,py) ... result=matched|no_match
```

**Steps**:
```
>>>>>>>> SATA begin step [N][Elapsed: ...]
```

A correlação step↔LLM call é determinística: LLM call N aparece entre `begin step [X]` e `begin step [X+1]`.

**NÃO contém**: dump UIAutomator raw, screenshot, elementos não-modelados.

### 11.2 Per-step XML dumps

O APE salva `step-N.xml` e `step-N.png` no device (`/sdcard/sata-<pkg>-ape-sata-running-minutes-10/`). Esses arquivos ficam dentro do emulator Docker e são destruídos quando o container termina. Para os traces do exp3, **não temos acesso** aos XMLs.

A Fase A'.2 resolve isso: modificar Docker entrypoint para preservar estes artefatos.

### 11.3 Diferença entre hit rate do rvsec-vision-llm e match rate do APE-RV

O rvsec-vision-llm mede hit rate com tolerância de 50px do **centro do widget-alvo**. O APE-RV usa bounds containment (match exige que o pixel esteja **dentro dos bounds**, não apenas próximo do centro). Isso explica parte da diferença:
- rvsec-vision-llm: 57,7% hit rate (coordenada a <50px do centro)
- APE-RV: 62,1% match rate (coordenada dentro dos bounds OU Euclidean fallback)

O APE-RV na verdade tem match rate **maior** que o hit rate do rvsec-vision-llm, provavelmente porque o Euclidean fallback aceita coordenadas próximas mas fora dos bounds.

### 11.4 Categorias de causa raiz (taxonomia completa)

Baseado na análise da arquitetura, as causas raiz possíveis de no_match são:

| Categoria | Causa | Detectável na Fase A? | Detectável na Fase A'? |
|-----------|-------|----------------------|------------------------|
| **Timing gap** | UI mudou entre dump e screenshot (toast, dialog, animação) | ❌ Não (parece `gap`) | ✅ Sim (UIAutomator XML mostra) |
| **Over-abstraction** | Widget existe no UIAutomator mas GUITreeBuilder não criou ModelAction | ❌ Não (parece `gap`) | ✅ Sim (comparar XML vs model) |
| **Edge miss** | Coordenada 1-20px fora dos bounds do widget correto | ✅ Sim | ✅ Sim |
| **Tolerance miss** | Coordenada 50-100px do widget (fora da tolerância Euclidean) | ✅ Sim | ✅ Sim |
| **Boundary rejection** | Coordenada no status bar / nav bar (threshold muito agressivo) | ✅ Sim | ✅ Sim |
| **Launcher/crash** | App crashou, LLM vê launcher | ✅ Sim | ✅ Sim |
| **Type mismatch** | Widget certo mas tipo errado (type_text em Button) | ✅ Sim | ✅ Sim |
| **LLM hallucination** | LLM clicou em coordenada sem nenhum elemento visual real | ❌ Não (parece `gap`) | ✅ Sim (screenshot confirma) |
| **Custom View** | Elemento desenhado via Canvas, sem nó na accessibility tree | ❌ Não | ⚠️ Parcial (screenshot mostra, XML não) |

**Conclusão**: A Fase A dá uma visão parcial (útil para edge_miss, boundary, launcher). A Fase A' é essencial para a ground truth (timing gap, over-abstraction, hallucination).
