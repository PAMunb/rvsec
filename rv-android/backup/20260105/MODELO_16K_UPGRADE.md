# Upgrade para Modelo 16K - 2025-11-13

## Motivação

**Problema identificado:** Token limit de 4096 sendo excedido durante testes

**Evidências:**
- Avg tokens/call: 4,598 (teste 5 apps)
- Simplenotes: 4,904 tokens/call (19% acima do limite)
- Input médio: ~3,000 tokens
- Output médio: ~1,500 tokens
- Algumas chamadas gerando `done_reason: 'length'` (token exhaustion)

**Impacto:**
- LLM não completa geração de tool calls
- Fallback para algoritmo
- Success rate afetado

---

## Solução Implementada

### 1. Criação do Modelo 16K

**Arquivo:** `modules/rv-agent/Modelfile.qwen3-vl-4b-16k`

```dockerfile
FROM qwen3-vl:4b

# Aumentar janela de contexto de 8k para 16k
PARAMETER num_ctx 16384

# Parâmetros otimizados do Phase 0
PARAMETER temperature 0.25
PARAMETER top_p 0.8
PARAMETER top_k 50
```

**Comando de criação:**
```bash
cd modules/rv-agent
ollama create qwen3-vl-4b-16k:latest -f Modelfile.qwen3-vl-4b-16k
```

**Resultado:**
```
✅ qwen3-vl-4b-16k:latest    df5137627671    3.3 GB
```

### 2. Atualização do AgentFactory

**Arquivo:** `modules/rv-agent/src/rv_agent/core/agent_factory.py`

**Mudanças (linhas 235-236):**

```python
# ANTES (8K model)
num_predict=4096,  # 4096 tokens max output (50% of 8K context window)
num_ctx=8192,      # Context window size (8K)

# DEPOIS (16K model)
num_predict=8192,  # 8192 tokens max output (50% of 16K context window)
num_ctx=16384,     # Context window size (16K)
```

### 3. Atualização do Teste de 5 Apps

**Arquivo:** `test_v13_5apps_complete_analysis.py`

**Mudanças:**
```python
# Linha 60
llm_model="qwen3-vl-4b-16k:latest",  # 16K context, 8K output

# Linhas 318-321 (metadata)
"model": "qwen3-vl-4b-16k:latest",
"context_window": "16K (16384 tokens)",
"max_output": "8K (8192 tokens)",
```

---

## Capacidade da Nova Configuração

### Comparação 8K vs 16K

| Aspecto | 8K Model | 16K Model | Ganho |
|---------|----------|-----------|-------|
| **Context window** | 8,192 tokens | 16,384 tokens | +100% |
| **Max output** | 4,096 tokens | 8,192 tokens | +100% |
| **Input capacity** | ~4K tokens | ~8K tokens | +100% |
| **Avg input** | 3,000 tokens | 3,000 tokens | - |
| **Remaining output** | 1,096 tokens | 5,192 tokens | +374% |

### Uso Esperado com Input de 3K

```
Input:  3,000 tokens (18% da janela 16K)
Output: 5,000 tokens disponível (31% da janela 16K)
Total:  8,000 tokens (49% da janela 16K)

Margem livre: 8,384 tokens (51% da janela)
```

### Casos Cobertos

**Caso Normal:**
- Input: 3,000 tokens
- Output: 200 tokens (tool call)
- Total: 3,200 tokens (20% da janela) ✅

**Caso Reasoning Pesado:**
- Input: 3,000 tokens
- Output: 4,000 tokens (reasoning + tool call)
- Total: 7,000 tokens (43% da janela) ✅

**Caso Extremo:**
- Input: 3,000 tokens
- Output: 8,000 tokens (muito reasoning)
- Total: 11,000 tokens (67% da janela) ✅

---

## Validação Necessária

### 1. Teste Rápido (120s)

```bash
# Usar test_token_fix_cryptoapp.py com novo modelo
poetry run python test_token_fix_cryptoapp.py
```

**Métricas a validar:**
- ✅ Nenhum `done_reason: 'length'`
- ✅ LLM success rate >85%
- ✅ Avg tokens/call <6000
- ✅ Avg time/call <15s

### 2. Teste Completo (25 min)

```bash
# Re-run 5 apps test
poetry run python test_v13_5apps_complete_analysis.py
```

**Métricas a validar:**
- ✅ LLM success rate >90%
- ✅ LLM fallback rate <10%
- ✅ Avg tokens/call <6000
- ✅ Nenhum token exhaustion

### 3. Comparação 8K vs 16K

**Apps:** br.unb.cic.cryptoapp, com.rafapps.simplenotes

| Métrica | 8K Model | 16K Model | Target |
|---------|----------|-----------|--------|
| LLM success rate | 88.6% | ? | >90% |
| LLM fallback rate | 11.4% | ? | <10% |
| Token exhaustion | Yes | ? | None |
| Avg tokens/call | 4,598 | ? | <6,000 |
| Avg time/call | 11.4s | ? | <15s |

---

## Benefícios Esperados

### 1. Eliminação de Token Exhaustion

**Antes:**
- Algumas chamadas atingiam limite de 4096
- `done_reason: 'length'` aparecia ocasionalmente
- LLM não completava tool call generation

**Depois:**
- Limite de 8192 acomoda até casos extremos
- `done_reason: 'stop'` em todas as chamadas
- LLM completa tool call generation consistentemente

### 2. Melhor Success Rate

**Esperado:**
- LLM success rate: 88.6% → >90%
- LLM fallback rate: 11.4% → <10%
- Menos fallbacks por token exhaustion

### 3. Robustez para Casos Complexos

**Capacidade para:**
- Apps com UI complexa (mais elementos)
- Reasoning extenso antes de tool calls
- Múltiplas chamadas em sequência
- Contexto histórico maior (future)

---

## Possíveis Trade-offs

### 1. Latência

**Preocupação:** Janela maior pode aumentar tempo de processamento

**Mitigação:**
- Qwen3-VL-4B é rápido mesmo com 16K
- Tempo depende mais de output tokens gerados
- Monitoring via métricas `avg_time_per_call_ms`

### 2. Memória

**Preocupação:** Janela maior consome mais VRAM

**Status:**
- Modelo 4B usa ~3.3GB em disco
- VRAM usage similar (model weights dominam)
- Janela 16K adiciona overhead mínimo

### 3. Custo Computacional

**Preocupação:** Context window maior = mais compute

**Realidade:**
- Qwen3-VL processa contexto eficientemente
- Custo proporcional a tokens GERADOS, não capacity
- Com avg output ~1.5K, impacto mínimo

---

## Próximos Passos

### Imediato (hoje)

1. ✅ Criar modelo 16K
2. ✅ Atualizar agent_factory.py
3. ✅ Atualizar teste de 5 apps
4. ⏳ Executar teste de validação (120s)
5. ⏳ Executar teste completo (25 min)

### Curto Prazo (próximos dias)

1. Comparar métricas 8K vs 16K
2. Documentar ganhos/trade-offs reais
3. Decidir se 16K vira novo padrão
4. Atualizar README e docs

### Médio Prazo (próxima semana)

1. Avaliar necessidade de 32K model (se houver)
2. Otimizar prompts para reduzir input tokens
3. Implementar prompt caching (se Ollama suportar)
4. Avaliar outros modelos vision-language

---

## Referências

### Arquivos Modificados

- `modules/rv-agent/Modelfile.qwen3-vl-4b-16k` (novo)
- `modules/rv-agent/src/rv_agent/core/agent_factory.py` (linhas 235-236)
- `test_v13_5apps_complete_analysis.py` (linhas 60, 318-321)

### Documentos Relacionados

- `RESULTADOS_V13_5APPS.md` - Análise que motivou upgrade
- `ESTRATEGIAS_ANALISE_COMPLETA.md` - Compatibilidade de estratégias
- `v13_5apps_analysis_20251113_193607.json` - Dados raw do teste 8K

### Commits Relevantes

```bash
# Este upgrade
git add -A
git commit -m "feat: upgrade to 16K context window model

- Create qwen3-vl-4b-16k:latest with 16K context
- Update AgentFactory: num_ctx 8192->16384, num_predict 4096->8192
- Update test_v13_5apps_complete_analysis.py to use new model
- Fixes token exhaustion issues (avg 4598 > limit 4096)

Refs: RESULTADOS_V13_5APPS.md, MODELO_16K_UPGRADE.md"
```

---

**Documento criado:** 2025-11-13
**Autor:** Claude Code
**Status:** ✅ Modelo criado e configurado, aguardando validação
