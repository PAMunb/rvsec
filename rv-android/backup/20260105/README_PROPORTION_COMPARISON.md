# LLM Proportion Comparison

Scripts para comparar diferentes proporções de uso de LLM vs algoritmo no modo multimode do RVAgent.

## Objetivo

Encontrar o equilíbrio ideal entre:
- **LLM (estrela do sistema)**: Melhor descoberta de estados, mas mais lento
- **Algoritmo (DFS)**: Mais rápido, mas exploração limitada

**Regra**: LLM sempre > 50% (é a estrela do RVAgent)

## Scripts Disponíveis

### 0. `modules/rv-agent/example_usage.py` - Porta de Entrada Principal ⭐

**Script principal para testes simples e rápidos do RVAgent.**

Modos disponíveis:
- `pure_algorithm`: Apenas DFS (sem LLM) - rápido e determinístico
- `pure_llm`: Apenas LLM (qwen3-vl-4b-8k) - inteligente mas lento
- `multimode`: Híbrido LLM + algoritmo (recomendado)

**Uso:**
```bash
# Modo interativo (menu de seleção)
poetry run python modules/rv-agent/example_usage.py

# Teste rápido (60s multimode)
poetry run python modules/rv-agent/example_usage.py --quick

# Modo específico
poetry run python modules/rv-agent/example_usage.py --mode multimode
poetry run python modules/rv-agent/example_usage.py --mode pure_algorithm
poetry run python modules/rv-agent/example_usage.py --mode pure_llm

# Personalizado
poetry run python modules/rv-agent/example_usage.py --mode multimode --timeout 300 --llm-probability 0.65
```

---

### 1. `test_quick_proportion.py` - Validação Rápida
Teste preliminar para validar o setup antes do teste completo.

**Configurações testadas:**
- 60% LLM / 40% algoritmo (balanceado)
- 70% LLM / 30% algoritmo (atual padrão)
- 80% LLM / 20% algoritmo (LLM dominante)

**Tempo:**
- 2 minutos por configuração
- **Total: ~6 minutos**

**Uso:**
```bash
poetry run python test_quick_proportion.py
```

**Resultados:**
- `./quick_proportion_test/proportion_comparison.json`

---

### 2. `compare_llm_proportions.py` - Comparação Completa
Teste completo com 6 configurações para análise estatística significativa.

**Configurações testadas:**
- 55% LLM / 45% algoritmo
- 60% LLM / 40% algoritmo
- 65% LLM / 35% algoritmo
- 70% LLM / 30% algoritmo ← **padrão atual**
- 75% LLM / 25% algoritmo
- 80% LLM / 20% algoritmo

**Tempo:**
- 3 minutos por configuração
- **Total: ~18 minutos**

**Uso:**
```bash
poetry run python compare_llm_proportions.py
```

**Resultados:**
- `./proportion_comparison_results/proportion_comparison.json`

## Métricas Analisadas

Para cada configuração, os scripts coletam:

### Métricas Primárias
- **Estados descobertos**: Total de telas/estados únicos encontrados
- **Transições**: Total de transições de estado registradas
- **Tempo de execução**: Tempo total em segundos

### Métricas de Decisão
- **Decisões LLM**: Quantas vezes a LLM foi consultada
- **Decisões algoritmo**: Quantas vezes DFS foi usado (fallback)
- **Razão LLM real**: Proporção real de uso da LLM vs esperada

### Métricas de Performance
- **Estados/segundo**: Eficiência de descoberta
- **Iterações/segundo**: Velocidade de execução
- **Tempo médio LLM**: Latência média por chamada LLM
- **Score de eficiência**: Estados descobertos / tempo total

## Formato dos Resultados

### JSON de Saída
```json
{
  "test_date": "2025-11-06 18:30:00",
  "timeout_per_test": 180,
  "probabilities_tested": [0.55, 0.60, 0.65, 0.70, 0.75, 0.80],

  "best_for_states": {
    "llm_probability": 0.70,
    "states": 8,
    "time": 180.5,
    "efficiency": 0.044
  },

  "best_for_efficiency": {
    "llm_probability": 0.60,
    "states": 7,
    "time": 178.2,
    "efficiency": 0.039
  },

  "best_for_speed": {
    "llm_probability": 0.55,
    "iterations_per_second": 0.83,
    "states": 6
  },

  "all_results": [
    {
      "llm_probability": 0.60,
      "iterations": 142,
      "states": 7,
      "transitions": 12,
      "llm_decisions": 87,
      "algorithm_decisions": 55,
      "total_decisions": 142,
      "actual_llm_ratio": 0.612,
      "execution_time": 178.2,
      "llm_time_total_ms": 15234,
      "avg_llm_time_ms": 175.1,
      "states_per_second": 0.039,
      "iterations_per_second": 0.80,
      "efficiency_score": 0.039,
      "status": "success"
    }
    // ... outras configurações
  ]
}
```

### Tabela de Comparação (Console)
```
LLM% | States |   Time | LLM Dec | Alg Dec | Efficiency
------------------------------------------------------------------------
  55% |      6 |  177.5s |      79 |      63 |       0.03
  60% |      7 |  178.2s |      87 |      55 |       0.04
  65% |      7 |  179.1s |      93 |      49 |       0.04
  70% |      8 |  180.5s |     101 |      41 |       0.04  ← atual
  75% |      7 |  182.3s |     107 |      35 |       0.04
  80% |      6 |  184.7s |     115 |      27 |       0.03
```

## Recomendações de Uso

### Passo 1: Validação Rápida
Execute primeiro o teste rápido para validar o ambiente:

```bash
# 6 minutos
poetry run python test_quick_proportion.py
```

### Passo 2: Análise Preliminar
Revise os resultados rápidos:

```bash
cat ./quick_proportion_test/proportion_comparison.json | jq '.best_for_efficiency'
```

### Passo 3: Teste Completo
Se os resultados rápidos forem promissores, execute o teste completo:

```bash
# 18 minutos
poetry run python compare_llm_proportions.py
```

### Passo 4: Análise Final
Compare todas as configurações:

```bash
cat ./proportion_comparison_results/proportion_comparison.json | \
  jq '.all_results[] | {prob: .llm_probability, states: .states, eff: .efficiency_score}'
```

## Critérios de Decisão

### Priorizar Estados Descobertos
Se o objetivo é máxima cobertura:
- Use a configuração com mais estados
- Aceite tempo de execução maior

### Priorizar Eficiência
Se o objetivo é balancear cobertura e tempo:
- Use a configuração com melhor efficiency_score
- **Recomendado para uso geral**

### Priorizar Velocidade
Se testes precisam ser rápidos:
- Use a configuração com melhor iterations_per_second
- Aceite menos estados descobertos

## Notas Importantes

1. **Variabilidade**: Execuções podem variar devido a:
   - Latência da LLM
   - Ordem de exploração aleatória
   - Estado inicial do emulador

2. **Significância Estatística**:
   - Testes de 3 minutos fornecem dados mais confiáveis
   - Para decisões críticas, considere múltiplas execuções

3. **Hardware**:
   - Resultados dependem de CPU/GPU disponível
   - LLM local (Ollama) vs cloud terá comportamento diferente

4. **LLM como Estrela**:
   - Sempre mantenha LLM > 50%
   - LLM descobr e novos estados que algoritmo não encontra
   - Algoritmo é fallback para compensar latência

## Próximos Passos

Após identificar a proporção ideal:

1. Atualizar `RVAgentConfig` default:
   ```python
   llm_probability: float = Field(
       default=0.XX,  # Atualizar aqui
       ...
   )
   ```

2. Documentar decisão no código

3. Re-testar com dataset completo (29 apps)

4. Considerar proporção adaptativa (futuro):
   - Aumentar LLM quando descobrindo muitos estados
   - Reduzir LLM quando preso em loops
