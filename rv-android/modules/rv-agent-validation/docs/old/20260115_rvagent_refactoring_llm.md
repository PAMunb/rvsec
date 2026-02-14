# Analise Comparativa: RV-Agent vs DroidAgent, AutoDroid, LLMDroid

**Data**: 15/01/2026
**Autor**: Claude Code
**Objetivo**: Analisar ferramentas LLM-based para teste de Android e identificar oportunidades de melhoria para o rv-agent

---

## Regras de Implementacao

1. **Simplicidade**: O sistema deve ser o mais simples e elegante possivel, sem complexidades desnecessarias, seguindo boas praticas.

2. **Sem codigo legado**: Todas as alteracoes devem ser realizadas, sem adapters de compatibilidade. Codigo legado deve ser removido/sobrescrito. Arquivos antigos movidos para `backup/`.

3. **Comentarios**: Devem refletir apenas o estado atual. Sem mencoes a migracao, fases, legado. Sem linguagem promocional ou termos de vies (moderna, sofisticada, etc). Publico alvo: desenvolvedores e pesquisadores.

---

## 0. Conhecimento Critico do RV-Agent (PRESERVAR)

### Qwen3-VL Coordinate System
- Coordenadas normalizadas [0, 1000) - conversao em `ActionNormalizer.denormalize_qwen_coords()`
- Prompt usa formato "at position (x, y)" para LLM copiar coordenadas
- Hit rate ~57.7% em visual_only mode (benchmark rvsec-vision-llm)

### Tool Calling Hibrido
- SGLang nao tem suporte oficial a tool calling para Qwen3-VL
- ~50% native tool_calls, ~50% XML no content
- Parser robusto em `tool_call_parser.py` trata ambos formatos

### Dialog Handling (v13)
- Tres tipos: permission, error/alert, modal dialogs
- LLM instruido a verificar dialogs PRIMEIRO antes de qualquer acao
- **MANTER no v14**

### Parametros LLM Otimizados
- temperature=0.01, top_p=0.6, top_k=50
- Config impact minimal em accuracy (<0.5% variance)

---

## 1. Resumo Executivo

Este documento apresenta uma analise detalhada de tres ferramentas de teste de Android baseadas em LLM: DroidAgent, AutoDroid e LLMDroid. O objetivo e identificar tecnicas e padroes que podem melhorar o rv-agent.

### O Que JA Temos

| Feature | Status | Local |
|---------|--------|-------|
| UI Coverage Feedback | ✅ Implementado | `UICoverageTracker.annotate_screen_elements()` |
| Dialog Handling | ✅ Implementado | `prompts/v13.py` |
| Navigation Guidance | ✅ Implementado | `NavigationGuidance` via WTG |
| MOP Markers | ✅ Implementado | `[DM]` e `[M]` tags nos elementos |
| Element Prioritization | ✅ Implementado | MopScorer, UntestedScorer, WtgScorer |

### UI Coverage Tracker (JA EXISTE!)

O `UICoverageTracker` ja adiciona anotacoes ao prompt:
- `[UNTESTED]` - Elemento nunca clicado (prioridade alta)
- `[TESTED-1x]` - Clicado uma vez
- `[TESTED-Nx]` - Clicado N vezes
- `[WELL-TESTED]` - Clicado mais de 3x (prioridade baixa)

**Exemplo no prompt atual**:
```
=== CLICKABLE ELEMENTS ===
1. [UNTESTED] Button 'Submit' at position (540, 350)
2. [TESTED-2x] ImageButton 'Menu' (menu_btn) at position (956, 78)
3. [WELL-TESTED] Button 'Cancel' at position (270, 350)
```

### Principais Descobertas das Ferramentas

| Ferramenta | Arquitetura | Diferencial Principal | Aplicabilidade ao RV-Agent |
|------------|-------------|----------------------|---------------------------|
| DroidAgent | Multi-agente POAR | Persona-based + Reflection | Baixa (sessoes curtas) |
| AutoDroid | Single-agent task | Template de 4 passos | **Alta** (reasoning estruturado) |
| LLMDroid | Meta-framework | Coverage-guided | Parcial (UI coverage ja existe) |

### Plano de Implementacao

| Fase | Oportunidade | Status | Decisao |
|------|--------------|--------|---------|
| 1 | Structured Reasoning Prompt (v14) | IMPLEMENTAR | Validar contra v13 |
| 2 | Function-based Exploration | OPCIONAL | Requer permissao |
| N/A | Code Coverage no Prompt | FUTURO | Quando integrado ao rv-platform |

---

## 2. Analise Detalhada: DroidAgent

### 2.1 Arquitetura

DroidAgent implementa uma arquitetura POAR (Plan-Observe-Act-Reflect) com multiplos agentes especializados:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Planner   │ ──► │  Observer   │ ──► │    Actor    │ ──► │  Reflector  │
│   (GPT-4)   │     │ (GPT-3.5)   │     │  (GPT-3.5)  │     │   (GPT-4)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                                            │
       └────────────────── Task Memory (ChromaDB) ◄─────────────────┘
```

**Localizacao dos arquivos analisados**:
- `external_tools/droidagent/droidagent/_actor.py`
- `external_tools/droidagent/droidagent/_planner_noknowledge.py`
- `external_tools/droidagent/droidagent/_reflector.py`
- `external_tools/droidagent/droidagent/prompts/act.py`
- `external_tools/droidagent/droidagent/prompts/plan.py`

### 2.2 Prompt do Actor (act.py)

```python
# System Message
system_message = f'''
You are a helpful assistant to guide a user named {persona_name} to select
an appropriate GUI action to accomplish a task on an Android mobile
application named {app_name}.

The profile of {persona_name} is as follows:
{persona_profile}

{persona_name} can perform the following types of actions:
- Scroll on a scrollable widget
- Touch on a clickable widget
- Long touch on a long-clickable widget
- Fill in an editable widget
- Navigate back by pressing the back button
or end the task if the task is already completed.
'''

# User Message (com template de 4 passos)
user_message = f'''
{observation}

This time, I'll give you the full content of the current page as follows:
```json
{screen_description_json}
```

Guideline for selecting the next action:
- Note that `num_prev_actions` means the number of times the widget
  has been interacted with so far.
- Note that `widget_role_inference` means the role of the widget
  inferred by previous actions.
- When I am stuck, guide me to explore a new widget.
- I don't want to do the same actions repeatedly.

Recall that my current task is: {task_summary}
Select the next suitable action to perform.

=== Template for your answer ===
1. Summary of my previous interactions: <1~2 sentences>
2. Description of the current app state: <1~2 sentences>
3. Inference on the remaining steps: <1~2 sentences>
4. Reasoning for the next action: <1 sentence>
'''
```

### 2.3 Sistema de Memoria (ChromaDB)

DroidAgent usa ChromaDB para dois tipos de memoria:

1. **Task Memory**: Armazena historico de tarefas e resultados
2. **Knowledge Storage**: Armazena reflections e aprendizados

```python
# task_memory.py
class TaskMemory:
    def retrieve_task_history(self, max_len=20):
        """Recupera historico de tarefas executadas."""
        entries = self.storage.get(where={'$or': [
            {'type': 'TASK_RESULT'},
            {'type': 'INITIAL_KNOWLEDGE'}
        ]})
        return self.storage.stringify_entries(entries, mode='task_history')

    def retrieve_task_reflections(self, state, N=5):
        """Busca semantica por reflections relevantes ao estado atual."""
        query = state.signature
        relevant_entries = self.knowledge_storage.query(
            query_texts=[query],
            n_results=N,
            where={'type': 'TASK'}
        )
        return self.knowledge_storage.stringify_entries(
            relevant_entries, mode='task_knowledge'
        )
```

### 2.4 Prompt do Planner (plan.py)

```python
system_message = f'''
You are a helpful task planner for using an Android application named {app_name}.
You are planning for a person named "{persona_name}" with the following profile:
{persona_profile}

{persona_name}'s ultimate goal is to {ultimate_goal}.

- {app_name} has following pages: {activities}
- Currently visited: {visited_activities}
- Current page: {current_activity}
- Pages never visited yet: {unvisited_pages}

To effectively explore the app, {persona_name} needs a new task that aligns with:
- (Realism) Realistic usage scenario, NOT "Navigate to X" or "Explore X"
- (Importance) Prioritize core functions, don't stay on same page too long
- (Diversity) Different from previous tasks, try untested widgets
- (Difficulty) Achievable in few steps from current state
'''

user_message = f'''
Plan {persona_name}'s next task based on:

Prior knowledge and history of previous tasks:
===
{task_history}
===

Learnt knowledge from previous tasks:
===
{task_reflections}
===

Current page (hierarchical structure):
```json
{screen_description}
```

=== Template for your answer ===
Reasoning about {persona_name}'s new task: <1~2 sentences using realism,
importance, diversity, difficulty>
{persona_name}'s next task: <1 sentence, start with a verb>
End condition: <"The task is known to be completed when...">
Reasoning of first action: <description>
Rough plan: <"I plan to...">
'''
```

### 2.5 Mecanismo de Retry

DroidAgent implementa retry com feedback de erro:

```python
def prompt_action_function(memory, system_message, user_messages,
                           assistant_messages, possible_action_functions,
                           function_map, error_message=None, query_count=3):
    if query_count == 0:
        return None

    if error_message is None:
        user_messages.append('Select the next action by calling a function.')
    else:
        user_messages.append(error_message)

    response = get_next_assistant_message(...)

    # Retry se resposta for texto ao inves de function call
    if isinstance(response, str):
        error_message = 'Call one of the given function instead of text answers.'
        return prompt_action_function(..., error_message=error_message,
                                      query_count=query_count-1)

    # Retry se funcao invalida
    if response['function']['name'] not in possible_action_functions:
        error_message = {
            'tool_call_id': response['id'],
            'name': response['function']['name'],
            'return_value': json.dumps({
                'error_message': f'{response["function"]["name"]} is not valid.'
            })
        }
        return prompt_action_function(..., error_message=error_message,
                                      query_count=query_count-1)
```

### 2.6 Aplicabilidade ao RV-Agent

| Tecnica | Aplicavel? | Motivo |
|---------|-----------|--------|
| Template de 4 passos | **SIM** | Melhora raciocinio |
| ChromaDB memory | NAO | Sessoes de 2min muito curtas |
| Persona-based | NAO | Foco e cobertura, nao realismo |
| Multi-agente | NAO | Custo/latencia proibitivos |
| Retry mechanism | **SIM** | Ja temos similar |
| Function calling | **SIM** | Ja usamos |

---

## 3. Analise Detalhada: AutoDroid

### 3.1 Arquitetura

AutoDroid e mais simples que DroidAgent, focando em automacao de tarefas:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Task     │ ──► │  GPT Query  │ ──► │   Action    │
│ Description │     │ (gpt-3.5)   │     │  Executor   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ UI State    │
                    │ (HTML tags) │
                    └─────────────┘
```

**Localizacao dos arquivos analisados**:
- `external_tools/AutoDroid/tools.py`
- `external_tools/AutoDroid/start.py`

### 3.2 Prompt Structure (tools.py)

```python
def make_prompt(task, ui_desc, history):
    introduction_prompt = """
You are a smartphone assistant to help users complete tasks by interacting
with mobile apps.
Given a task, the previous UI actions, and the content of current UI state,
your job is to decide whether the task is already finished by the previous
actions, and if not, decide which UI element in current UI state should be
interacted.
"""

    task_prompt = "Task: "
    history_prompt = "Previous UI actions: "
    interface_prompt = "Current UI state: "

    question_prompt = """
Your answer should always use the following format:
1. Completing this task on a smartphone usually involves these steps: <?>.
2. Analyse the relations between the task and the previous UI actions
   and current UI state: <?>.
3. Based on the analyses, is the task already finished? <Y/N>.
   The next step should be <?/None>.
4. Can the task be proceeded with the current UI state? <Y/N>.
   Fill in the blank about next interaction:
   - id=<id/-1 for finished>
   - action=<tap/input>
   - input text=<text or N/A>
"""

    return (introduction_prompt + '\n' +
            task_prompt + task + '\n' +
            history_prompt + '\n' + history + '\n' +
            interface_prompt + '\n' + ui_desc + '\n' +
            question_prompt)
```

### 3.3 Representacao de UI (HTML)

AutoDroid usa tags HTML para representar elementos:

```html
<button id=0 class='Settings'></button>
<p id=1>Welcome to the app</p>
<input id=2 class='Search' value=''></input>
<checkbox id=3 class='Remember me' checked=False></checkbox>
<button id=4 class='Submit'></button>
```

### 3.4 UI Diff Tracking

```python
def delete_old_views_from_new_state(old_state, new_state, without_id=True):
    """Remove elementos que ja existiam no estado anterior."""
    old_state_list = old_state.split('>\n')
    new_state_list = new_state.split('>\n')

    old_state_list_without_id = []
    for view in old_state_list:
        view_without_id = get_view_without_id(view)
        old_state_list_without_id.append(view_without_id)

    customized_new_state_list = []
    for view in new_state_list:
        view_without_id = get_view_without_id(view)
        if view_without_id not in old_state_list_without_id:
            customized_new_state_list.append(view_without_id)

    return customized_new_state_list
```

### 3.5 Extracao de Resposta

```python
def extract_action(v):
    """Extrai acao da resposta do LLM."""
    try:
        if isinstance(v, str):
            v = ast.literal_eval(v)
    except:
        return -1, "N/A", "N/A"

    # Verifica se tarefa terminou
    if 'Finished' in v.keys():
        whether_finished = v['Finished'].lower() in ['yes', 'y', 'true']
        if whether_finished:
            return -1, "N/A", "N/A"

    # Extrai acao
    llm_id = v.get('id', -1)
    llm_action = v.get('action', 'tap')
    llm_input = v.get('input_text', 'N/A')

    # Normaliza tipo de acao
    if "tap" in llm_action.lower() or "click" in llm_action.lower():
        llm_action = "tap"
    elif "input" in llm_action.lower():
        llm_action = "input"

    return int(llm_id), llm_action, llm_input
```

### 3.6 Aplicabilidade ao RV-Agent

| Tecnica | Aplicavel? | Motivo |
|---------|-----------|--------|
| Template de 4 passos | **SIM** | Simples e efetivo |
| HTML UI format | TALVEZ | Atual funciona bem |
| UI diff tracking | NAO | Ja temos visited_states |
| Task completion | NAO | Exploracao continua |
| Element IDs | TALVEZ | Hit rate atual 97.5% |

---

## 4. Analise Detalhada: LLMDroid

### 4.1 Arquitetura

LLMDroid e um meta-framework que adiciona LLM a ferramentas existentes:

```
                    ┌─────────────────────────────────────┐
                    │           LLM Agent                 │
                    │  (OVERVIEW, GUIDE, TEST, REANALYSIS)│
                    └─────────────────────────────────────┘
                              │           ▲
                              ▼           │
┌──────────────┐      ┌─────────────┐     │     ┌──────────────┐
│   Droidbot   │ ◄──► │  Policy     │ ────┘     │   Coverage   │
│   Humanoid   │      │  Manager    │ ◄─────────│   Monitor    │
│   Fastbot    │      └─────────────┘           │ (Jacoco/Log) │
└──────────────┘                                └──────────────┘
```

**Localizacao dos arquivos analisados**:
- `external_tools/LLMDroid/LLMDroid-Droidbot/droidbot/policy/llm_agent.py`
- `external_tools/LLMDroid/LLMDroid-Droidbot/droidbot/policy/prompt.py`

### 4.2 Modos de Operacao

```python
class QuestionMode(Enum):
    OVERVIEW = 0      # Analisa pagina, identifica funcoes
    GUIDE = 1         # Escolhe proximo target state/funcao
    TEST_FUNCTION = 2 # Executa acoes para testar funcao
    EXPLORE = 3       # Exploracao geral
    REANALYSIS = 4    # Re-avalia estados com novos widgets
```

### 4.3 Prompts por Modo

#### OVERVIEW Mode

```python
function_explanation = """
An app's page contains many controls to display information to users and
provide interactive interfaces.
Users can interact with the controls to perform a "Function", such as
navigating to other tabs by clicking a navigation bar icon or accessing
the settings page.
"""

input_explanation_overview = """
I will provide an HTML description of an app's page, including the
components and their structural information.
I use five types of HTML tags: <button>, <checkbox>, <scroller>, <input>,
and <p>, which represent elements that can be clicked, checked, swiped,
edited, and any other views respectively.
"""

required_output_overview = """
Based on the HTML description of this page, your tasks include:

1. Page Overview: Summarize the current page, concluding what kind of
   information the page mainly presents and what it is primarily used for.

2. Function Analysis: Identify the functions present on the page, listing
   their corresponding element IDs. Prioritize these functions by importance.
   - Navigation-related functions are crucial. These buttons are typically
     located at top or bottom of the page, appear in groups, have similar
     resource-ids with "tab", same class names, and general text attributes.
   - Functions central to the page's main purpose (play, like, subscribe)
   - Any other functions that could trigger new pages or enhance coverage.

3. Page Importance Ranking: Assess this page's significance relative to the
   entire app. Compare with the other five pages and rank the top five most
   important pages.
"""

answer_format_overview = """
Your answer should be in json form:
{
  "Overview": "Main page of the app, providing buttons to navigate...",
  "Function List": {
    "navigate to 'News'": 29,
    "navigate to 'My'": 28,
    "play a video": 15
  },
  "Top5": [1, 3, 2, 7, 4]
}
"""
```

#### GUIDANCE Mode

```python
input_explanation_guidance = """
After a period of testing, we have identified some pages (referred to as
States below) and had you analyze their roles and functionalities. Based
on this, I also asked you to rank these States by importance.
Below is a list of States ranked from highest to lowest importance. Each
State includes its Overview and FunctionList, with FunctionList containing
the five most important untested functions.
"""

required_output_guidance1 = """
Based on the information above, please decide: Which State should we go
next, and what function would be most appropriate to test?
Your main objective should be to explore new pages and enhance code coverage.
Specifically, you can follow these strategies:
1. Do not select function that has been chosen before:"""

required_output_guidance2 = """
2. Do not choose functions related to login or registration.
3. Prioritize choosing functions related to navigation.
4. Choose other function which can trigger transition or lead to undiscovered pages.
5. If there are no navigation-related functions, choose a core function from
   higher-ranked pages.
"""

answer_format_guidance = """
Your answer should be in json form:
{
    "Target State": "State2",
    "Target Function": "navigate to 'News'"
}
"""
```

#### TEST_FUNCTION Mode

```python
input_explanation_test = """
The app's current page is provided using HTML, including the components
and their structural information.
I use five types of HTML tags: <button>, <checkbox>, <scroller>, <input>,
and <p>.
"""

required_output_test = """
What action should I perform next to test the target function?
"""

answer_format_test = """
Your response should include the selected element's id and the action type.
Available actions: click (0), long press (1), swipe top-to-bottom (2),
swipe bottom-to-top (3), swipe left-to-right (4), swipe right-to-left (5),
input text (6).

Your answer should be in json form:
{
    "Element Id": 2,
    "Action Type": 4
}

If you believe the target function is finished testing:
{
    "Element Id": -1,
    "Action Type": 0
}
"""
```

### 4.4 LLM Agent Implementation

```python
class LLMAgent:
    MODEL_STR = 'gpt-4o'

    def __init__(self, app: 'App', utg: 'UTG'):
        self.__client = OpenAI(api_key=config['ApiKey'])
        self.__app_name = config['AppName']
        self.__app_desc = config['Description']

        # Overview tracking
        self.__top_valued_cluster: list['StateCluster'] = []

        # Function testing tracking
        self.__tested_functions: set[str] = set()
        self.__target_id: int = -1
        self.__target_func: str = ''
        self.__executed_events: list[str] = []

        # Async question queue (high/low priority)
        self.__queue = Queue()
        self.__low_queue = Queue()

        # Start worker thread
        self.__work_thread = threading.Thread(target=self.__work_loop)
        self.__work_thread.start()

    def __ask_for_overview(self, payload: QuestionPayload):
        """Analisa nova pagina, identifica funcoes, atualiza ranking."""
        prompt = self.__start_prompt + function_explanation + input_explanation_overview
        prompt += f"\n```HTML Description\n{payload.cluster.to_description()}\n```\n"

        if len(self.__top_valued_cluster) >= 5:
            # Pede para manter ranking de Top5
            prompt += required_output_overview
            top5 = {}
            for cluster in self.__top_valued_cluster[:5]:
                if cluster.has_untested_function():
                    cluster.write_overview_top5_tojson(top5)
            prompt += f"Current State: {payload.cluster.get_id()}\n"
            prompt += f"Five other States:\n{json.dumps(top5)}\n"
            prompt += required_output_overview_summary + answer_format_overview
        else:
            prompt += required_output_overview2 + answer_format_overview2

        json_resp = self.__get_response(prompt)
        payload.cluster.update_from_overview(json_resp)

    def __ask_for_guidance(self, payload: QuestionPayload):
        """Escolhe proximo target state e funcao para testar."""
        prompt = self.__start_prompt + input_explanation_guidance

        cluster_info = {}
        for cluster in self.__top_valued_cluster[:10]:
            if cluster.has_untested_function():
                cluster.write_overview_top5_tojson(cluster_info)

        prompt += f"\n```State Information\n{json.dumps(cluster_info)}\n```\n"

        # Lista funcoes ja testadas para evitar repeticao
        prompt += required_output_guidance1 + "{"
        for func in self.__tested_functions:
            prompt += f"{func}, "
        prompt += "}" + required_output_guidance2
        prompt += answer_format_guidance

        json_resp = self.__get_response(prompt)
        self.__target_id = int(json_resp['Target State'][5:])
        self.__target_func = json_resp['Target Function']

    def __ask_for_test_function(self, payload: QuestionPayload):
        """Decide qual acao executar para testar a funcao alvo."""
        prompt = self.__start_prompt + input_explanation_test
        html = payload.state.to_html()
        prompt += f"\n```Page Description\n{html}```\n"
        prompt += f"The target function I want to test is: {self.__target_func}\n"

        # Inclui acoes ja executadas para contexto
        if self.__executed_events:
            joined = ',\n'.join(self.__executed_events)
            prompt += f"\nI have already executed: [{joined}]\n"

        prompt += f"{required_output_test}\n{answer_format_test}\n"

        json_resp = self.__get_response(prompt)
        widget_id = int(json_resp['Element Id'])
        act_type = ActionType.get_type_by_value(int(json_resp['Action Type']))

        if widget_id == -1:
            # Funcao testada, retorna None
            return None

        return payload.state.find_event_by_id_and_type(widget_id, act_type)

    def add_tested_function(self):
        """Marca funcao como testada."""
        self.__tested_functions.add(self.__target_func)
        cluster = self.__utg.find_cluster_by_id(self.__target_id)
        if cluster:
            cluster.update_tested_function(self.__target_func)
```

### 4.5 State Clustering

LLMDroid agrupa estados similares para evitar analises redundantes:

```python
class StateCluster:
    """Agrupa estados com estrutura similar."""

    def has_untested_function(self) -> bool:
        """Verifica se ha funcoes nao testadas neste cluster."""
        for func in self.function_list:
            if func not in self.tested_functions:
                return True
        return False

    def get_target_state(self, target_func: str) -> Optional['DeviceState']:
        """Retorna estado que contem a funcao alvo."""
        for state in self.states:
            if state.has_function(target_func):
                return state
        return None

    def update_tested_function(self, func_name: str):
        """Marca funcao como testada no cluster."""
        self.tested_functions.add(func_name)
```

### 4.6 Integracao com Coverage

```python
# config.json
{
    "AppName": "NewPipe",
    "Description": "A lightweight YouTube frontend...",
    "ApiKey": "sk-...",
    "TotalMethod": 75480,           # Total de metodos no app
    "Tag": "PIPE_SUPER_LOG",        # Tag para AndroLog
    "ClassFilePath": "path/to/classes",  # Para Jacoco
    "EcFilePath": "/storage/emulated/0/Android/data/.../files",
    "Model": "gpt-4o-mini",
    "BaseUrl": "https://api.openai.com/v1"
}
```

A cobertura e monitorada via AndroLog ou Jacoco e usada para:
1. Guiar exploracao para funcoes com baixa cobertura
2. Determinar quando parar de testar uma funcao
3. Avaliar importancia relativa de paginas

### 4.7 Aplicabilidade ao RV-Agent

| Tecnica | Aplicavel? | Motivo |
|---------|-----------|--------|
| Coverage no prompt | **SIM** | Principal diferencial |
| Function tracking | **SIM** | Evita repeticao |
| State clustering | TALVEZ | Complexidade media |
| Multi-mode agent | NAO | Simplificacao preferivel |
| Tested functions | **SIM** | Simples de implementar |
| Priority queue | NAO | Desnecessario |

---

## 5. Comparacao Direta

### 5.1 Estrutura de Prompts

| Aspecto | DroidAgent | AutoDroid | LLMDroid | RV-Agent |
|---------|-----------|-----------|----------|----------|
| **Template estruturado** | 4 passos | 4 passos | JSON output | Livre |
| **Reasoning explicito** | Sim | Sim | Parcial | Nao |
| **Context window** | Multi-turn | Single-turn | Single-turn | Single-turn |
| **Task awareness** | Sim | Sim | Sim | Nao |

### 5.2 Representacao de UI

| Aspecto | DroidAgent | AutoDroid | LLMDroid | RV-Agent |
|---------|-----------|-----------|----------|----------|
| **Formato** | JSON hierarquico | HTML tags | HTML tags | Lista texto |
| **Element IDs** | Sim | Sim | Sim | Nao (coords) |
| **Metadata** | num_prev_actions | Nao | Nao | MOP markers |

### 5.3 Memoria e Estado

| Aspecto | DroidAgent | AutoDroid | LLMDroid | RV-Agent |
|---------|-----------|-----------|----------|----------|
| **Persistencia** | ChromaDB | Nenhuma | Em memoria | Summaries |
| **Task history** | Completo | Basico | Function list | Action history |
| **Semantic search** | Sim | Nao | Nao | Nao |

### 5.4 Feedback de Cobertura

| Aspecto | DroidAgent | AutoDroid | LLMDroid | RV-Agent |
|---------|-----------|-----------|----------|----------|
| **Coverage monitoring** | Nao | Nao | Sim (Jacoco/AndroLog) | Logcat |
| **Coverage no prompt** | Nao | Nao | Sim | Nao |
| **Coverage-guided** | Nao | Nao | Sim | Via MOP |

---

## 6. Oportunidades Identificadas

### 6.1 Structured Reasoning (ALTA PRIORIDADE)

**Inspiracao**: DroidAgent (act.py) e AutoDroid (tools.py)

**Implementacao proposta** para rv-agent:

```python
# prompts/v14.py
SYSTEM_PROMPT = """You are an Android UI automation assistant with vision.

REASONING TEMPLATE (follow exactly):
1. Screen Analysis: Describe what you see (dialogs, content, elements)
2. Dialog Check: Is there a blocking dialog? How to dismiss it?
3. Exploration Status: Which elements appear unexplored?
4. Action Decision: Based on above, select the next action

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK"
- Error dialogs: Dismiss first before background interaction
- Modal dialogs: Either interact or dismiss"""
```

**Beneficios**:
- Raciocinio explicito e auditavel
- Melhor tratamento de dialogos
- Mais facil de debugar decisoes

### 6.2 Coverage Feedback (ALTA PRIORIDADE)

**Inspiracao**: LLMDroid (llm_agent.py)

**Implementacao proposta**:

```python
# services/coverage_feedback.py
class CoverageFeedback:
    def __init__(self, coverage_tracker):
        self.tracker = coverage_tracker

    def get_prompt_section(self) -> str:
        """Gera secao de cobertura para o prompt."""
        return f"""
COVERAGE STATUS:
- Method coverage: {self.tracker.method_coverage:.1f}%
- Recently covered: {', '.join(self.tracker.recent_methods[-5:])}
- MOP methods uncovered: {self.tracker.uncovered_mop_count}

Prioritize actions that might trigger uncovered code paths.
"""

# Integrar em llm_node.py
def llm_generate(state: AgentState) -> dict:
    coverage_section = coverage_feedback.get_prompt_section()
    user_message = build_user_message(
        state_info,
        navigation_hint=nav_hint,
        coverage_info=coverage_section
    )
```

### 6.3 Function-based Exploration (MEDIA PRIORIDADE)

**Inspiracao**: LLMDroid (prompt.py - Function Analysis)

**Implementacao proposta**:

```python
# strategies/rvagent_strategy/ranking/function_scorer.py
class FunctionScorer(Scorer):
    """Prioriza elementos de funcoes nao testadas."""

    def __init__(self):
        self.tested_functions: Set[str] = set()

    def identify_functions(self, screen_desc: ScreenDescription) -> Dict[str, List]:
        """
        Agrupa elementos por funcao semantica.

        Heuristicas:
        1. Elementos com mesmo resource-id prefix (ex: nav_*, tab_*)
        2. Elementos em posicao de navigation bar (top/bottom)
        3. Elementos com texto semantico similar
        """
        functions = {}
        for item in screen_desc.items:
            func_name = self._infer_function(item)
            if func_name:
                functions.setdefault(func_name, []).append(item)
        return functions

    def _infer_function(self, item) -> Optional[str]:
        """Infere nome da funcao baseado em atributos do elemento."""
        # Por resource-id
        res_id = item.view.get('resource-id', '')
        if 'nav' in res_id or 'tab' in res_id or 'menu' in res_id:
            return f"navigate_{item.text or item.content_desc or res_id}"

        # Por texto
        text = item.text or item.content_desc
        if text:
            text_lower = text.lower()
            if any(kw in text_lower for kw in ['settings', 'profile', 'home']):
                return f"access_{text}"

        return None

    def score(self, action: ItemAction, context: RankingContext) -> float:
        func_name = self._infer_function(action.item)
        if func_name and func_name not in self.tested_functions:
            return 200.0
        return 0.0

    def mark_function_tested(self, item):
        """Marca funcao como testada apos interacao."""
        func_name = self._infer_function(item)
        if func_name:
            self.tested_functions.add(func_name)
```

---

## 7. Recomendacoes de Nao Implementar

| Tecnica | Fonte | Motivo |
|---------|-------|--------|
| ChromaDB memory | DroidAgent | Sessoes de 2min muito curtas para acumular conhecimento |
| Multi-agente | DroidAgent | Custo de 4+ chamadas LLM por iteracao proibitivo |
| Persona-based | DroidAgent | Foco e cobertura tecnica, nao realismo de uso |
| Task reflection | DroidAgent | Sessoes curtas demais para ciclo plan-act-reflect |
| UI diff tracking | AutoDroid | Ja temos visited_states e SuccessorTracker |
| State clustering | LLMDroid | Complexidade alta para beneficio marginal |
| Priority queue | LLMDroid | Modelo single-turn nao precisa de queue |

---

## 8. Plano de Implementacao

### Fase 1: Structured Reasoning Prompt (v14)

**Status**: IMPLEMENTAR

**Objetivo**: Criar prompt com template de raciocinio estruturado, mantendo compacto.

**Prompt v14 proposto**:
```python
SYSTEM_PROMPT = """You are an Android UI automation assistant with vision capabilities.

REASONING STEPS (follow in order):
1. SCREEN: What type of screen is this? (dialog, form, list, main menu, etc.)
2. DIALOG CHECK: Is there a blocking dialog? If yes, handle it first.
3. ELEMENTS: Which [UNTESTED] or [DM]/[M] elements are available?
4. ACTION: Select one action and call the tool.

RULES:
- DIALOGS FIRST: Always dismiss/interact with dialogs before background
- PRIORITY: [UNTESTED] > [DM]/[M] > [TESTED-Nx] > [WELL-TESTED]
- TEXT FIELDS: Use android_type_text() for EditText, NOT android_click()

Call the appropriate tool after your analysis."""
```

**Arquivos**:
- `prompts/v14.py` (NOVO)
- `llm/llm_client.py` (adicionar suporte a prompt version)

**Validacao** (OBRIGATORIA):
```bash
# Comparar v13 vs v14 em 3-5 apps
cd modules/rv-agent-validation
uv run python -m rv_agent_validation multimodal --config data/configs/quick_test.json

# Metricas a comparar:
# - Latencia media por iteracao (target: < 1.5x v13)
# - Hit rate (target: >= v13)
# - Method coverage (target: >= v13)
# - Reasoning quality (manual check nos logs)
```

**Criterios de escolha**:
- Se v14 tiver latencia < 1.5x v13 e qualidade >= v13: **manter v14**
- Se v14 tiver latencia > 1.5x v13: **criar v14-minimal ou voltar para v13**

### Fase 2: Function-based Exploration (OPCIONAL)

**Status**: REQUER PERMISSAO PARA IMPLEMENTAR

**O que e**: LLMDroid organiza exploracao por "funcoes" semanticas na tela. Exemplo: em uma tela de rede social, identificaria funcoes como "postar foto", "ver perfil", "enviar mensagem". Cada funcao agrupa varios elementos relacionados.

**Abordagem LLMDroid**:
- LLM faz chamada OVERVIEW para cada estado novo
- Identifica funcoes e rankeia por importancia
- Rastreia quais funcoes foram testadas

**Impacto**:
- Chamada LLM extra por estado novo (+1-2s latencia)
- Complexidade: state clustering, function tracking

**Alternativa atual**:
- `MopScorer`: Prioriza elementos que atingem MOPs
- `UntestedScorer`: Prioriza elementos `[UNTESTED]`
- `WtgScorer`: Prioriza transicoes do WTG

**Se aprovado, implementacao**:
```python
# strategies/rvagent_strategy/ranking/function_scorer.py
class FunctionScorer(Scorer):
    """Prioriza elementos de funcoes nao testadas."""

    def identify_functions(self, screen_desc: ScreenDescription) -> Dict[str, List]:
        """
        Agrupa elementos por funcao semantica via heuristica.
        Heuristicas:
        1. Elementos com mesmo resource-id prefix (ex: nav_*, tab_*)
        2. Elementos em posicao de navigation bar (top/bottom)
        3. Elementos com texto semantico similar
        """
        pass
```

**Arquivos**:
- `ranking/function_scorer.py` (NOVO)
- `ranking/scorers.py` (integrar)

### Fase N/A: Code Coverage no Prompt (FUTURO)

**Status**: NAO IMPLEMENTAR AGORA

**Motivo**: rv-agent e projetado para executar standalone, sem dependencia do rv-platform/logcat parsing. Cobertura de codigo sera disponivel apenas quando integrado ao rv-experiment.

**Quando implementar**: Apos integracao completa do rv-agent com rv-platform.

---

## 9. O Que NAO Implementar

| Oportunidade | Fonte | Motivo da Rejeicao |
|--------------|-------|-------------------|
| ChromaDB Memory | DroidAgent | Sessoes curtas (2min), complexidade alta |
| Multi-LLM Strategy | DroidAgent | Custo e latencia proibitivos |
| Task Reflection | DroidAgent | Sessoes muito curtas |
| State Clustering | LLMDroid | Complexidade vs beneficio |
| Persona-based Testing | DroidAgent | Nao aplicavel para teste de cobertura |

---

## 10. Referencias

### Repositorios Analisados

- DroidAgent: `external_tools/droidagent/`
- AutoDroid: `external_tools/AutoDroid/`
- LLMDroid: `external_tools/LLMDroid/`

### Arquivos Principais

- DroidAgent Actor: `droidagent/prompts/act.py`
- DroidAgent Planner: `droidagent/prompts/plan.py`
- DroidAgent Memory: `droidagent/memories/task_memory.py`
- AutoDroid Tools: `AutoDroid/tools.py`
- LLMDroid Agent: `LLMDroid-Droidbot/droidbot/policy/llm_agent.py`
- LLMDroid Prompts: `LLMDroid-Droidbot/droidbot/policy/prompt.py`

### Documentos Relacionados

- E3 Baseline Report: `docs/20260115_e3_baseline_report.md`
- Refactoring Plan (APE/Fastbot): `docs/20260114_rvagent_refactoring.md`
