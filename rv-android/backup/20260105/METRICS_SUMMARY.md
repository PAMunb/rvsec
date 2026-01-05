# Métricas Coletadas - Teste Comparativo V10/V11/V12

## Configuração do Teste

- **Duração**: 300 segundos (5 minutos) por app
- **Apps**: 10 apps do dataset
- **Prompt Versions**: V10, V11, V12
- **Total**: 30 testes (10 apps × 3 prompts)
- **Tempo Estimado**: ~2.5 horas

## Categorias de Métricas (12 grupos)

### 1. AÇÕES GERAIS
- `total`: Total de ações executadas
- `by_type`: Distribuição por tipo (CLICK, SET_TEXT, SCROLL, BACK, SWIPE, etc.)
- `by_decisor`: LLM vs Algoritmo (contagem)
- `decisor_percentage`: LLM vs Algoritmo (porcentagem)

### 2. DECISOR (LLM vs Algoritmo)
- `llm_count`: Quantas ações foram decididas pelo LLM
- `algorithm_count`: Quantas ações foram decididas pelo algoritmo
- `llm_percentage`: Porcentagem de ações LLM
- `algorithm_percentage`: Porcentagem de ações algoritmo
- `llm_to_algorithm_ratio`: Razão LLM/Algoritmo

### 3. UI COVERAGE GERAL
- `total_unique_elements`: Elementos UI únicos descobertos
- `total_interactions`: Total de interações com elementos
- `average_interactions_per_element`: Média de interações por elemento
- `total_screens`: Total de telas visitadas
- `discovery_timeline_length`: Tamanho da timeline de descobertas
- `recent_discoveries`: Descobertas recentes (últimos 5 min)

### 4. UI COVERAGE POR CATEGORIA
Para cada categoria (EditText, Spinner, Button, ImageView, etc.):
- `detected`: Quantos detectados
- `tested`: Quantos testados
- `coverage`: % de cobertura

### 5. EXPLORAÇÃO
- `unique_states`: Estados únicos visitados
- `total_transitions`: Total de transições entre estados
- `states_per_minute`: Taxa de descoberta de estados
- `transitions_per_state`: Média de transições por estado

### 6. LLM PERFORMANCE
- `tokens_input`: Tokens de entrada totais
- `tokens_output`: Tokens de saída totais
- `tokens_total`: Soma total de tokens
- `time_ms`: Tempo total de inferência (ms)
- `time_seconds`: Tempo total de inferência (s)
- `average_tokens_per_call`: Média de tokens por chamada LLM
- `average_time_per_call_ms`: Tempo médio por chamada (ms)
- `tokens_per_second`: Taxa de tokens/segundo
- `calls_total`: Total de chamadas LLM

### 7. UI TRACKER DETALHADO
- `action_distribution`: Distribuição de tipos de ação
- `most_tested_elements`: Top 3 elementos mais testados
- `least_tested_elements`: Bottom 3 elementos menos testados
- `test_count_distribution`: Distribuição de elementos por quantidade de testes
  - 0 testes (não testados)
  - 1 teste
  - 2 testes
  - 3 testes
  - 4 testes
  - 5+ testes

### 8. TEMPORAL
- `execution_time_s`: Tempo total de execução
- `discovery_rate`: Taxa de descoberta (elementos/minuto)
- `interaction_rate`: Taxa de interação (interações/minuto)

### 9. PERFORMANCE DERIVADAS
- `actions_per_second`: Ações por segundo
- `actions_per_minute`: Ações por minuto
- `tokens_per_action`: Tokens por ação
- `llm_time_per_action_ms`: Tempo LLM por ação (ms)
- `unique_elements_per_minute`: Elementos únicos descobertos por minuto

### 10. SHORT TERM MEMORY (Memória de Curto Prazo - Screen-scoped)
- `iteration_count`: Número de iterações na tela atual
- `current_activity`: Activity atual
- `total_actions_generated`: Total de ações geradas
- `total_execution_results`: Total de resultados de execução
- `average_success_rate`: Taxa de sucesso média na tela atual
- `memory_utilization`: Utilização da memória (iterações/máximo)
- `latest_iteration`: Informações da iteração mais recente
  - timestamp
  - action_count
  - success_rate

### 11. LONG TERM MEMORY (Memória de Longo Prazo - Cross-screen)
- `total_states`: Total de estados visitados
- `total_activities`: Total de activities diferentes
- `total_action_types`: Total de tipos de ação diferentes
- `total_actions_executed`: Total de ações executadas
- `total_successful_actions`: Total de ações bem-sucedidas
- `overall_success_rate`: Taxa de sucesso global
- `total_transitions`: Total de transições entre estados
- `most_visited_states`: Top 5 estados mais visitados
  - state_hash
  - activity
  - visit_count
  - elements_count

### 12. METADATA
- `status`: Status da execução (completed, error, etc.)
- `iterations`: Número de iterações
- `prompt_version`: Versão do prompt (v10, v11, v12)
- `app_package`: Package do app
- `timestamp`: Timestamp da execução

---

## Análises Comparativas Geradas

### 1. comparative_analysis.json
Estrutura JSON com métricas agregadas por versão:
- `apps_tested`: Quantidade de apps testados
- `averages`: Média de todas as métricas
- `action_types_average`: Média de cada tipo de ação

### 2. comparative_report.md
Relatório em Markdown com:
- Tabela comparativa geral (V10 vs V11 vs V12)
- Distribuição de tipos de ação
- LLM vs Algoritmo por versão
- UI Coverage performance
- Memory system performance
- Recomendações baseadas nos resultados

### 3. rankings.json
Rankings das versões por métrica:
- Cada métrica ranqueada (1º, 2º, 3º)
- Valor da métrica para cada versão

### 4. Resultados Individuais
Diretórios por versão:
- `v10_results/` - Resultados de cada app com V10
- `v11_results/` - Resultados de cada app com V11
- `v12_results/` - Resultados de cada app com V12

---

## Comparações Chave para Decisão

### Para Máxima Cobertura
- `unique_elements`: Quantos elementos UI foram descobertos
- `discovery_rate`: Velocidade de descoberta
- `ui_coverage_by_category`: Cobertura de cada tipo de elemento

### Para Eficiência
- `actions_per_minute`: Quantas ações por minuto
- `tokens_per_action`: Custo em tokens por ação
- `llm_time_per_action_ms`: Tempo de inferência por ação

### Para Qualidade de Exploração
- `unique_states`: Quantos estados diferentes visitados
- `transitions_per_state`: Diversidade de transições
- `long_term_success_rate`: Taxa de sucesso global

### Para Balanceamento LLM/Algoritmo
- `llm_percentage`: Quanto o LLM está sendo usado
- `llm_to_algorithm_ratio`: Razão entre decisores
- `decisor_distribution`: Distribuição de decisões

### Para Avaliação de Memória
- `short_term_success_rate`: Sucesso em telas específicas
- `long_term_success_rate`: Sucesso global
- `most_visited_states`: Detecção de loops/estados repetidos

---

## Uso

```bash
# Executar teste completo
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
poetry run python test_prompt_comparison_complete.py

# Resultados em
./results/prompt_comparison_YYYYMMDD_HHMMSS/
```

---

## Notas Importantes

1. **max_iterations foi REMOVIDO** - Agent para APENAS por timeout
2. **300 segundos por teste** - 5 minutos de exploração
3. **Métricas abrangentes** - 12 categorias com 80+ métricas individuais
4. **Comparação completa** - Rankings, tabelas, relatórios
5. **Memórias incluídas** - STM e LTM rastreadas
6. **UI Coverage detalhado** - Por categoria e elemento
7. **LLM metrics completos** - Tokens, tempo, eficiência
