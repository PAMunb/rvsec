# RVAgent - Plano de Refatoração Consolidado

**Data**: 2025-11-03
**Status**: Pronto para implementação

## 1. Objetivo Principal

Refatorar o `RVAgent` para eliminar o problema crítico de loops infinitos e implementar uma exploração de UI mais robusta e sistemática. A arquitetura será agnóstica ao modelo de linguagem, mas otimizada para o `qwen3-vl` com base em sua performance validada.

**Princípios:**
- **Sem Código Legado**: As alterações devem ser aplicadas diretamente, substituindo a lógica antiga. Arquivos de script obsoletos devem ser movidos para a pasta `backup`.
- **Comentários e Nomes Neutros**: A linguagem no código (comentários, nomes de variáveis) deve ser técnica, objetiva e livre de termos promocionais ou vieses.

---

## 2. Arquitetura Final: Sistema Multi-Modo

O RVAgent operará em três modos distintos, configuráveis através do `RVAgentConfig` (parâmetro `execution_mode`). Todos os modos compartilharão a mesma instância do `DynamicStateGraph` para garantir um estado de exploração consistente.

| Modo | Descrição | Caso de Uso | Referência |
|---|---|---|---|
| **`PURE_DFS`** | DFS algorítmico, sem uso de LLM. | Baseline de performance, testes rápidos, fallback quando o LLM está indisponível. | `v4_multimode.md` (Seção 2) |
| **`LLM_ONLY`** | LLM puro, como na v10. | Exploração criativa e semântica, útil para UIs complexas e não-estruturadas. | `v4_multimode.md` (Seção 3) |
| **`HYBRID`** | **(Padrão)** LLM para decisão, com validação e fallback de DFS. | Modo de produção recomendado, balanceando criatividade com robustez. | `v3.md` (Seção 2), `v4_multimode.md` (Seção 4) |

---

## 3. Plano de Implementação

A implementação seguirá uma abordagem faseada, focada na construção da arquitetura multi-modo e na resolução do problema de loop.

### Fase 1: Configuração e Roteamento Multi-Modo

1.  **Modificar `RVAgentConfig`**:
    - Adicionar o campo `execution_mode: str = "hybrid"` para selecionar o modo de operação (`pure_dfs`, `llm_only`, `hybrid`).
    - Permitir override do modo via variável de ambiente (`RVAGENT_MODE`) para facilitar testes.
    - Referência: `v4_multimode.md` (Seção 6).

2.  **Adaptar `RVAgent._build_agent_graph`**:
    - Implementar uma lógica que constrói um grafo LangGraph diferente para cada `execution_mode`.
    - **`_build_graph_hybrid`**: Criar um novo nó `decision_router` que será o ponto de entrada após o `observe`.
    - **`_decision_router_node`**: Este nó direcionará o fluxo para o caminho do LLM (`assistant`) ou para o caminho do DFS (`dfs_decide`) com base no modo e no estado atual (ex: falhas de LLM).
    - Referência: `v4_multimode.md` (Seção 7.2).

### Fase 2: Implementação do `PURE_DFS`

1.  **Estender `DFSStrategy`**:
    - Implementar o método `select_next_action` que opera de forma autônoma (sem LLM).
    - A lógica deve seguir o algoritmo DFS clássico: aprofundar em ações não testadas e retroceder (`BACK`) quando um estado é esgotado.
    - Para campos de texto (`TYPE_TEXT`), usar heurísticas baseadas em `resource-id` ou `text` para gerar entradas de texto simples (ex: "dfs_test@example.com").
    - Referência: `v4_multimode.md` (Seção 2.3).

2.  **Criar `_dfs_decide_node` em `RVAgent`**:
    - Este nó chama `self.strategy.select_next_action` e formata a ação para o `ToolNode`.
    - Referência: `v4_multimode.md` (Seção 4.3).

### Fase 3: Detecção de Loop e Fallback (Modo `HYBRID`)

1.  **Criar `_strategy_validation_node` em `RVAgent`**:
    - Este nó é o núcleo da solução de loop. Ele é posicionado após o nó `assistant`.
    - **Lógica**: Contar as repetições **consecutivas** de uma mesma ação.
    - Usar thresholds configuráveis por tipo de ação: `TYPE_TEXT: 2`, `CLICK: 3`, `SCROLL: 5`.
    - Se um loop for detectado, a ação do LLM é descartada.
    - **Fallback**: Chamar `self.strategy.select_untested_action` para obter uma ação de fallback do DFS, quebrando o loop. Se não houver ações não testadas, executar `BACK`.
    - Referência: `v3.md` (Seção 2.1, 6.2).

### Fase 4: Memória e Aprendizagem Compartilhada

1.  **Modificar `dynamic_state_graph.py`**:
    - Na classe `Transition`, alterar o campo `action_id` para `action_sequence: List[Dict]`.
    - Na classe `DynamicStateGraph`, adicionar um `current_trace: List[Dict]` para acumular ações.
    - Implementar `record_action_to_trace()` para adicionar uma ação ao `current_trace`.
    - Modificar `record_transition()` para salvar a sequência completa de ações (`current_trace`) na transição e depois limpar o trace.
    - Referência: `v3.md` (Seção 2.4, 6.1).

2.  **Atualizar Nós `observe` e `learn`**:
    - **`_observe_node`**: Detectar a mudança de `screen_hash`. Se mudou, chamar `dynamic_graph.record_transition()`.
    - **`_learn_node`**: Este será o **único ponto de atualização** do grafo. Após cada ação (seja do LLM ou DFS), chamar `dynamic_graph.record_action_to_trace()` e `ui_coverage.record_interaction()`.
    - Referência: `v3.md` (Seção 6.2), `v4_multimode.md` (Seção 5.2).

### Fase 5: Reativar Anotações de Cobertura de UI

1.  **Atualizar `_observe_node`**:
    - Chamar `self.ui_coverage.annotate_screen_elements()` para adicionar os marcadores `[UNTESTED]` e `[TESTED-Nx]` à descrição da tela enviada ao LLM.
    - Referência: `v3.md` (Seção 2.3).

2.  **Atualizar `_learn_node`**:
    - Garantir que `self.ui_coverage.record_interaction()` seja chamado para registrar a execução de cada ação, mantendo o rastreador de cobertura atualizado.
    - Referência: `v3.md` (Seção 2.3).

---

## 4. Arquivos a Modificar

O caminho base para os arquivos do agente é `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/src/rv_agent/`.

- **`core/rv_agent.py`**:
    - Implementar a lógica de construção de grafos (`_build_graph_*`).
    - Adicionar os novos nós: `_decision_router_node`, `_dfs_decide_node`, `_strategy_validation_node`.
    - Atualizar `_observe_node` e `_learn_node`.

- **`core/dynamic_state_graph.py`**:
    - Atualizar a classe `Transition` e adicionar a lógica de `current_trace`.

- **`strategies/dfs_strategy.py`**:
    - Implementar `select_next_action` para o modo autônomo e `select_untested_action` para o fallback.

- **`config/agent_config.py`**:
    - Adicionar `execution_mode` e outras configurações relevantes.

- **`llm/graph/state.py`**:
    - Adicionar os novos campos ao `AgentState` para rastrear o modo, decisões e falhas.

---

## 5. Métricas de Sucesso

- **Eliminação de Loops**: Zero loops com mais de 5 repetições consecutivas.
- **Aumento da Exploração**: Atingir >10 estados únicos em 120 segundos (baseline: 3).
- **Rastreamento de Transições**: Gerar um grafo com >15 transições em 120 segundos (baseline: 0).
- **Cobertura de UI**: Atingir uma cobertura de elementos > 40% por tela visitada.
