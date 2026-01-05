# Como Executar a Validação de Coordenadas

## Scripts Disponíveis (Recomendação de Execução)

### 1. 🚀 Teste Simples (COMECE AQUI)
```bash
cd modules/rv-agent/validation
./run_single_test.sh
```
**O que faz:**
- Testa 1 screenshot do cryptoapp.apk
- Usa estratégia baseline
- Captura TODA a saída em `logs/single_test_TIMESTAMP.log`
- Mostra métricas básicas no final

**Análise do log:**
```bash
# Ver resultado final
tail -30 logs/single_test_*.log

# Ver explicações do LLM
grep -A2 -B2 "Explanation:" logs/single_test_*.log

# Ver clicks e coordenadas
grep "Coordinates:\|HIT\|MISS" logs/single_test_*.log
```

### 2. 📈 Teste Incremental (SE O SIMPLES FUNCIONAR)
```bash
./run_incremental_with_poetry.sh
```
**O que faz:**
- 5 níveis de teste progressivos
- Começa com 1 screenshot, termina com 4 apps
- 15-45 minutos de execução
- Log completo em `logs/incremental_validation_TIMESTAMP.log`

**Níveis:**
- Level 0: 1 app, 1 screenshot, 1 strategy
- Level 1: 1 app, 2 screenshots, 2 strategies
- Level 2: 1 app, 3 screenshots, all strategies
- Level 3: 2 apps, 3 screenshots, key strategies
- Level 4: 4 apps, 5 screenshots, all strategies

### 3. 🔬 Teste de Estratégias
```bash
./run_with_poetry.sh
```
**O que faz:**
- Testa todas as 5 estratégias de prompt
- 1 screenshot do cryptoapp.apk
- Compara performance entre estratégias

## Análise dos Logs

### Métricas Principais
```bash
# Hit rates por estratégia
grep "Hit Rate:" logs/*.log

# Coordenadas escolhidas pelo LLM
grep "Coordinates:" logs/*.log

# Resultados de acerto/erro
grep "HIT\|MISS" logs/*.log

# Raciocínio do LLM (explicações)
grep -A3 "Explanation:" logs/*.log
```

### Debugging
```bash
# Erros e exceções
grep -i "error\|exception\|failed" logs/*.log

# Imports e setup
grep -A5 -B5 "import\|Initialize" logs/*.log

# Tool calls
grep "TOOL_CALL\|ANDROID_" logs/*.log
```

## Estrutura dos Logs

### Seção: Tool Calls
```
[TOOL_CALL] 🖱️ ANDROID_CLICK
  📍 Coordinates: 540,273
  🎯 Element: MESSAGE DIGEST button
  💭 Explanation: I chose this element because...
```

### Seção: Validation Results
```
[MOCK_DEVICE] ✅ HIT: MESSAGE DIGEST (distance: 12.3px)
Hit Rate: 100.0%
Avg Distance: 12.3px
```

### Seção: Strategy Comparison
```
📊 Strategy Comparison:
  baseline: 66.7%
  coordinate_validation: 100.0%
  spinner_focused: 33.3%
```

## Arquivos de Saída

### Logs (Análise Manual)
- `logs/single_test_*.log` - Teste simples
- `logs/incremental_validation_*.log` - Teste incremental
- `logs/validation_stdout_*.log` - Apenas stdout

### JSON (Análise Programática)
- `validation_results_*.json` - Métricas detalhadas
- `incremental_*.json` - Resultados por nível

## Troubleshooting

### Erro: Modelo não encontrado
```bash
# Verificar se o modelo está disponível
poetry run python -c "
from langchain_ollama import ChatOllama
llm = ChatOllama(model='PetrosStav/gemma3-tools:4b')
print('Model available')
"
```

### Erro: Dataset não encontrado
```bash
# Verificar dataset
ls /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/
```

### Erro: Import failed
```bash
# Testar imports
cd modules/rv-agent/validation
poetry run python -c "
import sys
sys.path.append('.')
from mock_device_adapter import MockDeviceAdapter
print('Imports OK')
"
```

## Interpretação dos Resultados

### Hit Rate (Taxa de Acerto)
- **90-100%**: Excelente - LLM acerta elementos consistentemente
- **70-89%**: Bom - Performance aceitável para produção
- **50-69%**: Médio - Precisa otimização de prompt
- **<50%**: Ruim - Problema significativo

### Average Distance (Distância Média)
- **<10px**: Precisão excelente
- **10-25px**: Precisão boa
- **25-50px**: Precisão aceitável (limite de hit)
- **>50px**: Problema de precisão

### Spinner Problem
Se `spinner_focused` strategy tem hit rate baixo:
- LLM está ignorando Spinners/ComboBox
- Precisa prompt engineering específico
- Problema conhecido do RVAgent atual

## Próximos Passos

1. **Execute teste simples** primeiro
2. **Analise explicações** do LLM nos logs
3. **Identifique padrões** de erro
4. **Otimize prompts** baseado nas explicações
5. **Execute teste incremental** para validação final