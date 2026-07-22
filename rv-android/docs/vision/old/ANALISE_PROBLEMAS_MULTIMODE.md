# Análise: Problemas no Teste Multimode

**Data**: 2025-11-06
**Contexto**: Teste de comparação de proporções LLM vs Algoritmo

---

## Problemas Identificados

### 1. ❌ Modelo LLM Incorreto
**Sintoma**: Erro 404 - model 'qwen2.5:7b' not found

**Causa**:
Script estava configurado com `qwen2.5:7b` mas o modelo correto é `qwen3-vl:4b`

**Solução Aplicada**:
- ✅ Atualizado `compare_llm_proportions.py` para usar `qwen3-vl:4b`
- Localização: `compare_llm_proportions.py:55`

---

### 2. ❌ Ações `SET_TEXT` Retornando `unknown`
**Sintoma**:
```
Recording action signature=((540, 383), 'unknown') on state d6a84af0
```

**Causa**:
`ToolExecutor` não reconhecia `SET_TEXT`, apenas `TYPE_TEXT`. O DFS gera ações com tipo `SET_TEXT`, mas o ToolExecutor não sabia processar.

**Impacto**:
- Ações SET_TEXT falhavam silenciosamente
- Estados não transitavam corretamente
- Contador de ações executadas crescia sem limite

**Solução Aplicada**:
- ✅ Adicionado `SET_TEXT` como sinônimo de `TYPE_TEXT` no ToolExecutor
- Localização: `modules/rv-agent/src/rv_agent/execution/tool_executor.py:80`
- Código:
  ```python
  elif action_type in ("TYPE_TEXT", "SET_TEXT"):
      # SET_TEXT and TYPE_TEXT are synonyms
      result = self._execute_type_text(action, convert_coordinates)
  ```

---

### 3. ⚠️ Latência LLM Excessiva (44 segundos)
**Sintoma**:
Iteração 7 levou 44 segundos para completar

**Causa Provável**:
Janela de contexto padrão do Ollama (4096 tokens) pode estar truncando ou causando lentidão com prompts grandes

**Evidência**:
```
2025-11-06 18:55:22,603 - Iteration 7 (elapsed: 44.5s)
```

**Solução Aplicada**:
- ✅ Criado Modelfile customizado com janela de 8k tokens
- Localização: `modules/rv-agent/Modelfile.qwen3-vl-4b-8k`
- Configuração:
  ```
  FROM qwen3-vl:4b
  PARAMETER num_ctx 8192      # 8k context (vs 4k default)
  PARAMETER temperature 0.25   # Phase 0 optimal
  PARAMETER top_p 0.8         # Phase 0 optimal
  PARAMETER top_k 50          # Phase 0 optimal
  ```
- ✅ Modelo criado no Ollama: `qwen3-vl-4b-8k`

**Próximo Passo**:
✅ Scripts atualizados para usar `qwen3-vl-4b-8k`
⏳ Executar testes e verificar se latência melhora

---

### 4. ⚠️ Estado Preso em Loop
**Sintoma**:
```
Estado d6a84af084f0:
  Total actions: 4
  Executed: 7  ← Mais execuções que ações disponíveis!
```

**Causa**:
Combinação dos problemas 2 e 5:
1. `SET_TEXT` falhando (tipo unknown)
2. Estado não transitando
3. Mesmas ações sendo re-executadas
4. Contador crescendo além do limite

**Impacto**:
- Teste fica preso na mesma tela
- Não explora novos estados
- Desperdiça tempo de execução

**Solução Aplicada**:
- ✅ Resolvido pelo fix do problema 2 (SET_TEXT)
- Ações agora executam corretamente
- Estados devem transitar normalmente

---

### 5. ⚠️ Grafo Não Reseta Entre Testes

**Sintoma**:
As mesmas ações aparecem nos logs de testes diferentes (p=0.6 e p=0.7):
- `((0, 0), 'click')`
- `((352, 248), 'click')`
- `((540, 383), 'click')`

**Causa**:
O `DynamicStateGraph` está sendo reutilizado entre testes. Cada teste deveria criar componentes completamente novos via `AgentFactory.create_agent()`.

**Solução Pendente**:
- ⏳ Verificar se `run_test()` está criando novo agente para cada probabilidade
- ⏳ Garantir que cada chamada a `AgentFactory.create_agent()` retorna componentes novos
- ⏳ Considerar adicionar método `reset()` ao DynamicStateGraph se necessário

---

## Resumo das Soluções

| Problema | Status | Solução | Arquivo |
|----------|--------|---------|---------|
| Modelo LLM incorreto | ✅ Resolvido | Usar qwen3-vl:4b | compare_llm_proportions.py:55 |
| SET_TEXT → unknown | ✅ Resolvido | Adicionar sinônimo | tool_executor.py:80 |
| Latência LLM (44s) | ✅ Resolvido | Modelfile 8k context | Modelfile.qwen3-vl-4b-8k |
| Estado em loop | ✅ Resolvido | Via fix SET_TEXT | - |
| Grafo não reseta | ⏳ Pendente | Criar novos componentes | compare_llm_proportions.py |

---

## Próximos Passos

1. ⏳ Verificar se grafo reseta corretamente entre testes
2. ✅ Atualizar script para usar `qwen3-vl-4b-8k`
3. ⏳ Re-executar teste de proporções
4. ⏳ Verificar se latência LLM melhorou
5. ⏳ Validar que estados transitam corretamente

---

## Notas Importantes

- **SET_TEXT vs TYPE_TEXT**: Manter ambos como sinônimos. DFS usa SET_TEXT, LLM usa TYPE_TEXT.
- **Modelo customizado**: O qwen3-vl-4b-8k deve ser usado para todos os testes para evitar truncamento.
- **Verificação de logs**: Sempre verificar contador de ações executadas vs total de ações no estado.

---

## Referências

- Modelfile anterior (v2): `modules/rv-agent/Modelfile.qwen-vision-tools-v2`
- Parâmetros Phase 0: T0.25, P0.8, K50 (validados em 9,855 testes)
- Janela de contexto padrão Ollama: 4096 tokens
- Janela customizada: 8192 tokens
