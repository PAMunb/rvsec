# Backup - LangGraph Migration (2025-10-28)

## Arquivos Movidos

### device_adapter.py
**Motivo**: Duplicação com `device_interface.py` (arquivo legado da arquitetura pré-LangGraph)

**Usado por**:
- `rv_agent.py` (arquivo legado, também obsoleto)
- Arquitetura antiga baseada em ReAct/HuggingFace

**Substituído por**:
- `device_interface.py` - usado pela arquitetura LangGraph atual
- Integrado com `android_tools.py` → `langgraph_agent.py`

**Data**: 2025-10-28

---

## Contexto da Migração

O projeto RV-Agent migrou de uma arquitetura customizada (ReAct + HuggingFace) para **LangGraph 1.0** com componentes prebuilt.

### Arquitetura Antiga (device_adapter.py)
- Integração customizada com rv-uiautomator
- Usado pelo `RVAgent` legado (rv_agent.py)
- Process isolation com LoggingManager próprio

### Arquitetura Atual (device_interface.py)
- Integração simplificada com UIAutomator2Adapter
- Usado pelo `LangGraphRVAgent` (langgraph_agent.py)
- Tools baseadas em LangChain/LangGraph
- Connection management corrigido (connect() adicionado)
- Screenshot com shutil.move() para cross-filesystem support

## Referências Removidas

- `rv_agent/core/__init__.py`: linha 10 comentada
- Sem imports ativos no código atual
