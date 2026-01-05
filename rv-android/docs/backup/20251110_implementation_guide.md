# GUIA DE IMPLEMENTAÇÃO - 6 MELHORIAS RVAGENT

## Arquitetura Identificada

- **DynamicStateGraph**: Compartilhado entre LLM e algoritmo (histórico de ações)
- **RoutingManager**: Gerencia decisões LLM vs Algoritmo
- **LoopDetector**: Detecta repetições de ações
- **ScreenProcessor**: Processa UI e formata para LLM
- **LLMClient**: Cliente LLM com Ollama backend
- **ExplorationStrategy**: Base para DFS/BFS/Greedy

## Ordem de Implementação

1. **Item 2**: LLM Timeout (llm_client.py) - Mais simples
2. **Item 4**: Spatial Loop Detector (loop_detector.py) - Isolado
3. **Item 1**: UI Coverage Annotations (screen_processor.py) - Requer modificação de factory
4. **Item 3**: Recovery Mode (routing_manager.py) - Depende de loop detector
5. **Item 7**: Stuck State Detector (rv_agent.py) - Independente
6. **Item 6**: Text Input Fallback (strategies/) - Mais complexo

## Arquivos a Modificar

1. `modules/rv-agent/src/rv_agent/llm/llm_client.py`
2. `modules/rv-agent/src/rv_agent/routing/loop_detector.py`
3. `modules/rv-agent/src/rv_agent/ui/screen_processor.py`
4. `modules/rv-agent/src/rv_agent/core/agent_factory.py`
5. `modules/rv-agent/src/rv_agent/routing/routing_manager.py`
6. `modules/rv-agent/src/rv_agent/core/rv_agent.py`
7. `modules/rv-agent/src/rv_agent/strategies/base_strategy.py`
8. `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py`

## Detalhes Técnicos Importantes

- `ItemAction` pode não suportar TYPE_TEXT nativamente - precisa verificar
- `screen_hash` está em `DynamicStateGraph.states`
- `ui_coverage` está em `MemoryCoordinator`
- Timeout usa `config` dict no `llm.invoke()`
- Ações recentes estão em `state["recent_action_window"]`
