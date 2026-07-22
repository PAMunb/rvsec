# Análise Rigorosa: VLM-Fuzz vs APE-RV / RVSmart / RVAgent

**Data**: 2026-03-18
**Código-fonte VLM-Fuzz**: `/tmp/VLM-Fuzz` (clonado de https://github.com/biniamf/VLM-Fuzz)
**Paper**: arXiv:2504.11675, aceito em Empirical Software Engineering (Springer)
**Codebase**: ~2.930 linhas Python (13 arquivos)

---

## 1. Visão Geral da Arquitetura

### 1.1 VLM-Fuzz

```
main.py (orquestração)
  ├── manifest_parser.py (aapt parse → components)
  ├── pre_ui_test.py (widget counting → budget allocation)
  └── ui_automator.py (1.965 linhas — TODO o core)
        ├── aivision.py (GPT-4o API wrapper)
        ├── prompt.py (prompt template único)
        ├── transition.py (linked list de eventos)
        ├── component.py (UI widget com ssdeep hash)
        └── actions.py (enum de 13 ações)
```

**Arquitetura em uma frase**: Script Python monolítico que lança cada activity do AndroidManifest via `am start`, faz DFS recursivo no UI tree com callbacks para GPT-4o quando há campos de texto, e registra transições numa linked list para replay/backtracking.

### 1.2 Nossas ferramentas

| Ferramenta | Linguagem | LOC | Execução | Arquitetura |
|-----------|-----------|-----|----------|-------------|
| **APE-RV** | Java | ~15.000 | On-device (app_process) | SATA + MOP scoring + LLM opcional |
| **RVSmart** | Java | ~8.000 | On-device (app_process) | DFS + MOP + LLM multimode |
| **RVAgent** | Python | ~12.000 | Host-side (LangGraph) | 5-tier strategy + 9 scorers + WTG |
| **VLM-Fuzz** | Python | ~2.930 | Host-side (subprocess) | DFS recursivo + GPT-4o seletivo |

---

## 2. Comparação Detalhada por Dimensão

### 2.1 Estratégia de Exploração

#### VLM-Fuzz: DFS Recursivo por Componente

```python
# main.py: loop principal
for activity in components:
    uia = UIAutomator(package, adb_command)
    uia.start_app(activity['name'], command)
    p = multiprocessing.Process(target=uia.analyze)
    p.start()
    p.join(60 * current_component_budget)  # budget proporcional
```

A exploração é **component-centric**: para cada Activity/Service/Receiver do AndroidManifest, VLM-Fuzz aloca um budget proporcional ao número de widgets e faz DFS recursivo:

```
analyze() → update_view() → categorize widgets →
  if editáveis: complete_ai_actions(VLM) → fallback heurístico
  else: perform_action() → [text, tap, scroll, menu, rotate, home/restore]
    → cada tap/scroll que muda UI: recursão → new UIAutomator().analyze()
```

**Ponto-chave**: A recursão é via **instanciação de novo UIAutomator** a cada transição de tela. O `ui_stack` (global) previne análise repetida (tau=2 visitas por componente). Não há modelo formal de grafo — o estado é a pilha de chamadas recursivas.

#### APE-RV: SATA com MOP Guidance

Exploração **model-based**: constrói grafo de estados (State → Action → State) com prioridades calculadas por `adjustActionsByGUITree()`. O modelo persiste entre ações. Epsilon-greedy (5%) seleciona entre least-visited (exploitation) e random (exploration). MOP weights (+500/+300/+100) dominam a prioridade base (~32-50) quando static analysis está disponível.

**Diferença fundamental**: APE-RV mantém um **modelo persistente** do grafo de estados; VLM-Fuzz reconstrói o estado a cada chamada recursiva.

#### RVAgent: 5-Tier Strategy com Scorers

Exploração **score-based contínua**: ActionRanker com 9 scorers ponderados (recency, frequency, diversity, coverage density, MOP score, novelty, spatial diversity, backtrack penalty, type diversity). Nunca esgota — o Tier 4 (Scored Continuous) sempre produz uma ação. WTG do static analysis guia navegação entre activities via TransitionManager.

**Diferença fundamental**: RVAgent usa **reward propagation** e **multi-tier fallback** — nunca fica preso. VLM-Fuzz depende da recursão/backtracking e pode ficar em loops.

#### RVSmart: DFS + MOP Algorítmico

Exploração **on-device** com Java: DFS com priorização por static analysis. Multimode opcional (70% LLM / 30% algoritmo). Similar ao APE-RV na execução (app_process), mas com estratégia de exploração diferente (DFS vs SATA).

### 2.2 Integração VLM/LLM

#### VLM-Fuzz: GPT-4o Seletivo

```python
# ui_automator.py:709-760 — condição de invocação
has_textedit = any(_item.action == Action.TEXT for _item in viewItems)
rnd = random.randint(1,100) if has_textedit else 0

if rnd > 70 or self.currentFocus not in vision_ai_result or popup:
    # screenshot → label → GPT-4o → parse steps
    order, summary, thought, observation, oai_response = aivision.get_ai_sequence(
        labelled_screenshot_path, prompt.prompt_steps_gpt, ...)
```

**Quando chama GPT-4o**:
1. Se a tela tem campos de texto (EditText) — **sempre** na primeira visita
2. Se é popup — **sempre**
3. Se já viu esta activity — **30% das vezes** (random > 70)
4. Se não tem EditText — **nunca** (cai direto no heurístico)

**Como comunica com GPT-4o**:
1. Screenshot da tela
2. Labels numéricas sobrepostas nos widgets (via OpenCV/pyshine)
3. Prompt template com funções: `tap(N)`, `input(N, "text")`, `long_press(N)`, `swipe(N, dir, dist)`, `scroll(UP/DOWN)`
4. Context: summary da ação anterior

**Parsing da resposta**: regex simples no campo `Steps:` do output. Exemplo:
```
Steps: [tap(5); input(5, "Buy groceries"); tap(3);]
```

#### APE-RV: LLM On-Device (Qwen3-VL via SGLang)

LLM chamado pelo `LlmRouter.java` on-device quando:
- `llmOnNewState=true` e estado é novo
- `llmOnStagnation=true` e grafo estagnou

O LLM retorna coordenadas de ação, que são convertidas via `ActionResolver` para ações do modelo APE-RV. **37.3% no_match rate** no exp3 — coordenadas do LLM frequentemente não casam com widgets detectados.

#### RVAgent: LLM como Core (Qwen3-VL via SGLang)

LLM é o componente central: recebe screenshot + UI hierarchy + prompt v13 + tool definitions → retorna tool calls (`android_click`, `android_type_text`, etc.) com coordenadas normalizadas [0, 1000).

**Diferenças críticas vs VLM-Fuzz**:

| Aspecto | VLM-Fuzz | RVAgent |
|---------|----------|---------|
| Modelo | GPT-4o (proprietário, $0.25/app/h) | Qwen3-VL-4B (local, custo zero) |
| Invocação | Seletiva (só com EditText/popup) | Contínua (70% das decisões em multimode) |
| Input ao LLM | Screenshot labelada + prompt | Screenshot raw + XML hierarchy + tool definitions |
| Output | Texto livre parsado com regex | Tool calls estruturados (JSON) |
| Fallback | Heurístico se LLM falha | Algorithm tier se LLM falha |
| Context | Summary da ação anterior (1 frase) | Últimas 5 ações + estado do grafo |
| Temperature | 0 (fixo, determinístico) | 0.3 (configurável, calibrável) |

### 2.3 Representação de Estado

#### VLM-Fuzz: Implicit Stack

```python
ui_stack = deque()        # componentes visitados (global)
ui_class_stack = []       # UIAutomator instances por componente
visited = []              # lista plana de visits (count > 2 → skip)
```

Estado é **implícito na pilha de recursão**. Não há modelo formal. A comparação entre estados é feita por **item-by-item matching**: mesmo class + content_desc + enabled + resource_id = mesmo estado.

**Detecção de mudança de UI** (`check_items_count`):
```python
# Compara flat_hierarchy novo com currentViewItems antigo
# Se similarity_count == total → sem mudança
# Se tamanho da view != screen_size (diff > 150px) → popup
```

#### APE-RV: Widget Table Graph (WTG)

Modelo formal com `Graph` → `State` → `ModelAction`. Cada `State` é uma abstração via `NamingFactory` (lattice de níveis de abstração). `maxStatesPerActivity=10` limita a granularidade. O modelo persiste durante toda a execução.

#### RVAgent: DynamicStateGraph

Hash MD5 do UI structure (structural hashing) identifica estados únicos. Grafo com 1000+ nós possíveis. TransitionManager mapeia Window IDs do static analysis para activities runtime. SuccessorTracker mantém fronteira de exploração.

### 2.4 Tratamento de Texto (Input Fields)

#### VLM-Fuzz: Dupla abordagem

**Com VLM (GPT-4o vision)**:
```python
# aivision.py — screenshot labelada → GPT-4o → steps incluem input()
# Exemplo: input(5, "john@example.com")
```

**Sem VLM (fallback GPT-3.5-turbo text)**:
```python
# ui_automator.py:627-655 — openai_req()
# Envia JSON do widget para GPT-3.5-turbo
# Pede: "provide a possible numeric or text input"
# Se input rejeitado pelo app → retry com "numeric only"
```

**Fallback final**: `''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(4,8)))` — string aleatória.

**Problema**: Usa **duas APIs diferentes** (GPT-4o para vision, GPT-3.5-turbo para text input). O text input individual por campo é caro (1 API call por EditText).

#### APE-RV: Monkey-style

Input via `adb shell input text` com strings geradas pelo Monkey framework. Sem inteligência semântica.

#### RVAgent: InputValueGenerator semântico

```python
# Infere tipo do campo: email, phone, URL, password, username, etc.
# Gera 11 variações por campo baseado em hints/content-desc
# LLM path: Qwen3-VL gera texto contextualizado via tool call
```

11 tipos de input com valores contextualmente apropriados. Erro recovery: detecta error indicators espacialmente próximos ao campo e re-tenta com valor diferente.

### 2.5 Popups e Dialogs

#### VLM-Fuzz

```python
# Detecção: se bounds da root view diferem > 150px do screen_size → popup
if y_diff1 > 150 or x_diff1 > 150 or x_diff0 > 150 or y_diff0 > 150:
    _popup = True
```

Popups são analisados recursivamente com `analyze(popup=True)`. Sem lógica especial para permission dialogs (apenas lista de ignore: `["PopupWindow", "GrantPermissionsActivity", "DeprecatedTargetSdkVersionDialog", "Application Not Responding"]`).

**Problema**: A detecção de popup por tamanho é frágil — dialogs full-screen não são detectados.

#### APE-RV

Tratados como transições de estado no WTG. Permission dialogs handled implicitamente pelo modelo.

#### RVAgent

Detecção explícita de dialogs no prompt v13. Error detection via análise de bounding boxes. Spatial association mapeia errors aos input fields. Recovery automático com re-fill.

### 2.6 Backtracking e Recovery

#### VLM-Fuzz: Transition Replay

```python
# transition.py — linked list de eventos
class TransitionRecord:
    def replay(self, adb_command, uia):
        # Kill app → restart activity → replay cada evento
        subprocess.run([f'{adb_command} shell am force-stop {uia.package}'])
        uia.start_app(currentFocus, replay=True)
        while event:
            if event.action == Action.TAP: uia.send_tap(...)
            elif event.action == Action.TEXT: uia.send_text(...)
            ...
            event = event.next
```

**Replay completo**: mata o app, reinicia a activity, e re-executa cada ação gravada para chegar ao estado anterior. Limitado a 6 replays por evento. Se replay falha → desiste.

**Problema**: Replay é **frágil** — depende de UI determinístico (mesmas coordenadas, mesmos widgets). Apps dinâmicos (ex: feed de notícias, timestamps) quebram o replay.

#### APE-RV

`graphStableRestartThreshold` e `stateStableRestartThreshold` controlam quando o app é reiniciado. Backtracking via modelo de grafo — pode calcular caminho para estados não-saturados.

#### RVAgent

PathBuffer com 3 estratégias (A/B/C) para backtracking. Proactive Backtrack no Tier 3 planeja caminhos quando saturation ≥ 0.8. WTG-guided navigation via TransitionManager. SuccessorTracker mantém fronteira.

### 2.7 Budget e Timeout

#### VLM-Fuzz

```python
# pre_ui_test.py — conta widgets por activity
# Budget proporcional: activity com mais widgets → mais tempo
current_component_budget = total_budget * computed_budget[_activity_name]['budget']

# main.py — multiprocessing com timeout
p = multiprocessing.Process(target=uia.analyze)
p.start()
p.join(60 * current_component_budget)  # minutos → segundos
if p.is_alive():
    p.terminate()
```

Budget é **per-activity**, proporcional ao widget count. Activity com 50 widgets recebe mais tempo que uma com 10. Default total: 60 min.

**Problema**: Budget allocation ignora a **profundidade** da UI. Uma activity com 5 widgets mas 20 screens de profundidade recebe menos tempo que uma com 50 widgets numa única screen.

#### APE-RV / RVSmart

Timeout global (ex: 600s). Sem budget per-activity — a exploração do SATA distribui naturalmente o tempo baseado na topologia do grafo.

#### RVAgent

Timeout global. A estratégia de 5 tiers distribui o tempo automaticamente — Proactive Backtrack (Tier 3) move a exploração para áreas inexploradas quando há estagnação.

---

## 3. Análise de Qualidade do Código VLM-Fuzz

### 3.1 Problemas Arquiteturais

**P1. God Class `UIAutomator` (1.965 linhas)**

Uma única classe com responsabilidades de:
- UI dumping e parsing XML
- Envio de ações (tap, text, scroll, swipe, long_press, menu, back, enter)
- Detecção de mudança de componente
- Screenshot e labeling
- Integração com VLM (GPT-4o)
- Integração com LLM (GPT-3.5-turbo para text input)
- Backtracking/replay
- Detecção de popup
- Exploração recursiva (analyze)

Nenhuma de nossas ferramentas tem esta concentração. RVAgent distribui em 15+ módulos; APE-RV em 9 packages Java.

**P2. Estado global mutável**

```python
# ui_automator.py — variáveis globais
vision_ai_result = {}    # cache de respostas GPT-4o (global dict)
ui_stack = deque()       # pilha de componentes (global)
ui_class_stack = []      # UIAutomator instances (global)
visited = []             # lista de visits (global)
expired = list()         # lista de expirados (global, não usada)
```

5 variáveis globais mutáveis compartilhadas entre instâncias recursivas de UIAutomator. Thread-unsafe (mitigado pelo uso de multiprocessing em vez de threading).

**P3. Shell injection não tratado**

```python
# Todas as chamadas ADB usam shell=True com f-strings
subprocess.run([f'{self.adb_command} shell input tap {coordinates[0]} {coordinates[1]}'], shell=True)
```

Se `coordinates` contiver caracteres especiais (improvável para coordenadas numéricas, mas possível via input do GPT), há risco de injection. Nossas ferramentas Java executam on-device (sem shell intermediário).

**P4. Sem testes**

Zero arquivos de teste no repositório. Nenhum CI/CD. Nossas ferramentas: RVAgent tem 7 categorias de testes (unit, integration, smoke, online, performance, regression, system).

### 3.2 Problemas de Implementação

**I1. Bug na `sort_sentiment` — variable shadowing**

```python
# ui_automator.py:988-993
positive_buttons = ["Home", "Menu", "Done", ...]  # lista de strings
positive = []
neutral = []
negative = []
neutral_button = []
positive_buttons = []   # ← SOBRESCREVE a lista acima! Bug claro
negative_button = []
```

A variável `positive_buttons` é declarada como lista de strings na linha 988, depois sobrescrita com lista vazia na linha 993. O sort_sentiment **nunca classifica botões positivos**. Isso significa que a heurística de "positive buttons last" do paper **não funciona** no código publicado.

**I2. `send_scroll_right` registra como `SCROLL_LEFT`**

```python
# ui_automator.py:241-245
def send_scroll_right(self, coordinates, replay=False):
    if not replay:
        self.transition.add(self.currentFocus, coordinates, Action.SCROLL_LEFT)  # BUG: deveria ser SCROLL_RIGHT
```

**I3. `is_soft_keyboard_visible` retorna hardcoded False**

```python
# ui_automator.py:386-387
def is_soft_keyboard_visible(self):
    return False
```

O paper menciona "handling soft keyboard overlay" como feature. O código não implementa detecção de teclado virtual. `hide_soft_keyboard()` chama `tap_back()` em loop, mas como `is_soft_keyboard_visible()` retorna `False`, o loop nunca executa.

**I4. `vision_ai_result` no `__init__` é no-op**

```python
# ui_automator.py:74-75
if vision_ai_result:
    vision_ai_result = vision_ai_result  # atribui local à local — no-op
```

O parâmetro `vision_ai_result` do construtor é ignorado. O código usa a variável **global** `vision_ai_result` em vez da instância.

**I5. Retry ingênuo no `inspect`**

```python
# main.py:102-106
try:
    computed_budget = ptest.inspect()
except:
    # quick workaround for cases ZeroDivisionError error when app launch fails
    computed_budget = ptest.inspect()  # tenta exatamente a mesma coisa
```

**I6. `adb_command` pode ser undefined**

```python
# main.py:55-66
emulator_port = None
if args_dict['port'] != None:
    emulator_port = int(args_dict['port'])
if emulator_port != None:
    adb_command = f"adb -s emulator-{emulator_port}"
# Se port não especificado → adb_command NUNCA é definido
# Linha 66: subprocess.run([f"{adb_command} root"]) → NameError
```

Se `--port` não é passado, `adb_command` nunca é atribuído. O `run.sh` não passa `--port`. A variável global `adb_command = "adb"` em `ui_automator.py` não é acessível em `main.py`.

**I7. `ssdeep` no `requirements.txt` está comentado**

```
#pipssdeep==3.4
```

Mas `component.py` faz `import ssdeep`. A instalação falha sem compilar ssdeep manualmente.

### 3.3 Métricas de Complexidade

| Métrica | VLM-Fuzz | APE-RV | RVAgent |
|---------|----------|--------|---------|
| Linhas de código | 2.930 | ~15.000 | ~12.000 |
| Maior arquivo | 1.965 (ui_automator.py) | ~1.400 (StatefulAgent.java) | ~400 (rv_agent.py) |
| Variáveis globais | 5 | 0 | 0 |
| Testes | 0 | limitados | 7 categorias |
| Documentação inline | Mínima | Moderada | Extensa |
| Error handling | bare `except:` | ErrorHandler decorators | ErrorHandler + recovery |
| Profundidade de recursão | Ilimitada (pode crash) | N/A (iterativo) | N/A (iterativo) |

---

## 4. Comparação Funcional

### 4.1 Funcionalidades que VLM-Fuzz tem e nós não

| Feature | VLM-Fuzz | Nossas ferramentas | Relevância |
|---------|----------|-------------------|-----------|
| **Budget per-component** | Widget count proporcional | Timeout global | Média — interessante mas com limitações (ignora profundidade) |
| **Screen rotation testing** | `rotate_screen()` + `reset_rotate_screen()` | Não implementado | Baixa — raramente detecta bugs em apps modernos |
| **Home + restore testing** | `home_screen()` + `restore_app()` | Não implementado | Média — testa lifecycle (onPause/onResume) |
| **System broadcast fuzzing** | 187 system broadcasts | Não implementado | Alta — testa receivers, pode encontrar crashes em background components |
| **Service testing** | `start_service()` via am startservice | Não implementado | Média — testa Services declarados no manifest |
| **Battery level fuzzing** | `sent_battery_level()` (random 1-30%) | Não implementado | Baixa — raramente detecta bugs |
| **Fuzzy hashing (ssdeep)** | Component identity via ssdeep | Structural hashing (MD5) | Baixa — ssdeep tem overhead e não é significativamente melhor que hash direto para UI elements |

### 4.2 Funcionalidades que nós temos e VLM-Fuzz não

| Feature | Nossas ferramentas | VLM-Fuzz | Impacto |
|---------|-------------------|----------|---------|
| **Runtime Verification (MOP)** | APE-RV + RVAgent: MOP scoring, violation detection | Nenhum | **Crítico** — objetivo principal da tese |
| **Static analysis integration** | WTG, reachability, MOP data | Apenas aapt manifest | **Alto** — fundamenta a exploração guiada |
| **Model-based exploration** | APE-RV: WTG formal; RVAgent: DynamicStateGraph | Stack implícito | **Alto** — evita redundância |
| **Multi-tier strategy** | RVAgent: 5 tiers + 9 scorers | DFS + random shuffle | **Alto** — adaptação dinâmica |
| **Semantic input generation** | RVAgent: 11 tipos com contextualização | GPT-4o/3.5-turbo | **Médio** — mais eficiente sem API calls |
| **Error recovery automático** | RVAgent: spatial association + re-fill | Retry + give up | **Médio** — aumenta coverage em forms |
| **Calibração de parâmetros** | Optuna-based (gh9) | Nenhuma | **Alto** — performance ótima vs heurística |
| **Parallel execution** | Docker containers (10+ simultâneos) | `multiprocessing.Process` (1 por activity) | **Alto** — escalabilidade |
| **Instrumentação de APKs** | rv-instrumentation + rv-monitor-generator | Nenhuma | **Crítico** — base do RV |
| **Coverage tracking** | rv-coverage module | Nenhum | **Alto** — métricas de avaliação |

### 4.3 Custo de LLM

| Ferramenta | Modelo | Custo | Latência |
|-----------|--------|-------|----------|
| VLM-Fuzz | GPT-4o ($5/$15 per M tokens) | ~$0.25/app/hora | ~2-5s por chamada (rede) |
| VLM-Fuzz (text) | GPT-3.5-turbo | ~$0.01/app/hora | ~0.5-1s por chamada |
| APE-RV | Qwen3-VL-4B (local) | $0 (custo GPU) | ~1-2s por chamada (local) |
| RVAgent | Qwen3-VL-4B (local) | $0 (custo GPU) | ~1-2s por chamada (local) |

**VLM-Fuzz com 60 min/app × 169 APKs × 3 reps = ~$127** (estimativa).
**Nossas ferramentas**: custo fixo de GPU (~$0 marginal por run).

---

## 5. Análise dos Resultados Reportados no Paper

### 5.1 Benchmark AndroTest (59 apps, 60 min, 5 reps)

| Ferramenta | Class Cov | Method Cov | Line Cov |
|-----------|-----------|------------|----------|
| VLM-Fuzz | **68.5%** | **53.2%** | **46.5%** |
| APE | 59.5% | 49.5% | 44.4% |
| Monkey | 53.4% | 43.3% | 35.6% |
| Humanoid | 56.9% | 45.9% | 38.2% |
| ComboDroid | 60.5% | 48.3% | 42.9% |
| TimeMachine | 59.3% | 47.3% | 41.0% |
| Q-Testing | 54.9% | 44.2% | 37.2% |
| DeepGUI | 57.8% | 48.0% | 43.7% |

### 5.2 Contexto para comparação com nossos dados

**Cuidado**: Os benchmarks não são diretamente comparáveis:
- VLM-Fuzz usa **AndroTest** (59 apps open-source), nós usamos **169 APKs com instrumentação JCA/generic**
- VLM-Fuzz mede **class/method/line** coverage (JaCoCo), nós medimos **method coverage + MOP coverage** (nossa instrumentação)
- VLM-Fuzz roda **60 min**, nós rodamos **10 min** (600s) — 6× mais tempo
- VLM-Fuzz não faz instrumentação de APKs — testa APKs originais

### 5.3 O que os resultados significam para nós

1. **+9% class coverage vs APE** (paper) é significativo, mas APE no paper é o **APE original (2020)**, não o APE-RV (nosso fork com MOP scoring). A comparação relevante seria VLM-Fuzz vs `aperv:sata_mop`.

2. **53.2% method coverage** com 60 min. Nosso `aperv:sata_mop_v2` atinge ~30.8% em 10 min. Escalar linearmente (6× tempo) daria ~40-50%, que é comparável — mas a relação coverage/tempo não é linear.

3. **VLM-Fuzz não usa static analysis**. Toda a exploração é runtime-only. Isso sugere que para coverage puro (sem objetivo de MOP), DFS + VLM pode ser competitivo sem instrumentação.

---

## 6. O Que Podemos Aprender

### 6.1 Ideias implementáveis

| # | Ideia | De VLM-Fuzz | Para nossas ferramentas | Esforço | Impacto |
|---|-------|-------------|------------------------|---------|---------|
| L1 | **System broadcast testing** | 187 broadcasts no `system-broadcast.json` | Adicionar broadcast fuzzing no rv-experiment como etapa pós-exploration | Médio | Médio — pode descobrir crashes em receivers |
| L2 | **Service testing** | `am startservice` para cada Service do manifest | Adicionar no rv-platform como componente | Médio | Médio |
| L3 | **Lifecycle testing (home/restore)** | `KEYCODE_HOME` + `KEYCODE_APP_SWITCH` | Adicionar como ação do RVAgent | Baixo | Médio — testa onPause/onResume |
| L4 | **Budget by complexity** | Widget count → budget proporcional | Em RVAgent, usar MOP density por activity como proxy de complexidade para alocação de tempo | Médio | Alto — direciona tempo para onde há mais MOP |
| L5 | **Screenshot labeling para debug** | Numbered labels sobrepostos nos widgets | Adicionar como ferramenta de debug no rv-agent-validation | Baixo | Baixo — útil para visualização |

### 6.2 Ideias que NÃO devemos copiar

| # | Ideia | Por que não |
|---|-------|-------------|
| X1 | GPT-4o como backend | Custo proibitivo para 169 APKs × 3 reps; Qwen3-VL local é 100× mais barato |
| X2 | DFS recursivo puro | Nosso model-based approach (APE-RV) e multi-tier (RVAgent) são superiores |
| X3 | Backtracking por replay | Frágil em apps dinâmicos; nosso WTG-guided backtracking é mais robusto |
| X4 | Estado implícito (global stack) | Escala mal; nosso DynamicStateGraph é formalmente correto |
| X5 | UI dump via broadcast+pull | Lento (broadcast + pull XML); nosso UIAutomator via uiautomator2 é mais eficiente |

### 6.3 Validações de design que VLM-Fuzz confirma

1. **LLM seletivo > LLM universal**: VLM-Fuzz só chama GPT-4o quando há text inputs. 22% dos apps não precisam de VLM. Isso valida o design do APE-RV com `llmOnNewState`/`llmOnStagnation` como triggers configuráveis (calibráveis).

2. **Heurísticas simples funcionam**: O DFS recursivo + sentiment sorting de VLM-Fuzz supera APE original em +9%. Isso confirma que a **estratégia de exploração importa mais que o modelo formal** — mas não substitui calibração.

3. **Text input é gargalo**: VLM-Fuzz dedica 2 APIs (GPT-4o + GPT-3.5) só para input generation. Nosso `InputValueGenerator` resolve o mesmo problema sem custo de API.

4. **Component-level testing é complementar**: VLM-Fuzz testa Services e Receivers além de Activities. Nossas ferramentas focam em Activities — há oportunidade de extensão.

---

## 7. Resumo Comparativo

| Dimensão | VLM-Fuzz | APE-RV | RVSmart | RVAgent |
|----------|----------|--------|---------|---------|
| **Exploração** | DFS recursivo | SATA model-based | DFS + MOP | 5-tier scored |
| **LLM** | GPT-4o seletivo | Qwen3-VL opcional | Qwen3-VL opcional | Qwen3-VL core |
| **Estado** | Stack global | WTG formal | On-device graph | DynamicStateGraph |
| **Static Analysis** | Nenhum | MOP scoring | MOP scoring | WTG + MOP scoring |
| **Text Input** | GPT-4o/3.5 | Monkey | Semântico | InputValueGenerator |
| **Backtracking** | Replay (frágil) | Model-based | Algorítmico | PathBuffer 3 strategies |
| **Calibração** | Nenhuma | Optuna (planejado) | N/A | Optuna (gh9) |
| **Custo** | ~$0.25/app/h | $0 (GPU local) | $0 (no GPU) | $0 (GPU local) |
| **Coverage tipo** | JaCoCo | MOP + method | MOP + method | MOP + method |
| **Qualidade código** | Protótipo | Produção | Produção | Produção |
| **Testes** | 0 | Limitados | Limitados | 7 categorias |
| **RV capability** | Nenhum | Completo | Completo | Completo |

---

## 8. Conclusão

**VLM-Fuzz é um protótipo de pesquisa com resultados promissores mas implementação frágil.** O paper reporta +9% class coverage vs APE, mas o código publicado tem bugs significativos (sentiment sorting quebrado, keyboard detection desabilitada, variable shadowing), estado global mutável, zero testes, e dependência de API proprietária.

**Para o contexto da tese**, as lições mais valiosas são:

1. **Budget por complexidade** (L4) — adaptável para MOP density allocation
2. **Component-level testing** (L1, L2) — broadcasts e services são gap nas nossas ferramentas
3. **Validação de design** — confirma que LLM seletivo e heurísticas simples são eficazes
4. **Calibração como diferencial** — VLM-Fuzz não calibra nada; nosso Optuna pipeline é vantagem competitiva significativa

**Nossas ferramentas são substancialmente superiores** em: formalismo (model-based), instrumentação (RV), escalabilidade (Docker parallelism), custo (LLM local), qualidade de código, e calibração. VLM-Fuzz é superior em: testing de componentes não-Activity (Services, Receivers, Broadcasts) e simplicidade de deployment.
