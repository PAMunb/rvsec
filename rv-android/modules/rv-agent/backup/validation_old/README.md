# Coordinate Validation for Gemma3-tools

Protótipo para validação de precisão de coordenadas do modelo PetrosStav/gemma3-tools:4b sem emulador.

## Arquivos Principais

### Core Components
- `mock_device_adapter.py` - Simula device sem emulador, valida coordenadas contra XML
- `simple_tools_with_explanation.py` - Tools com parâmetro explanation para capturar raciocínio
- `coordinate_validator.py` - Engine principal de validação com diferentes estratégias

### Test Scripts
- `quick_test.py` - Teste rápido com 1 screenshot para verificar funcionamento
- `incremental_test.py` - Teste incremental de 1 até todos os screenshots
- `run_validation.py` - Script principal para execução completa

## Uso Básico

### 1. Teste Rápido (Recomendado primeiro)
```bash
cd modules/rv-agent/validation
python quick_test.py
```

### 2. Teste Incremental
```bash
python incremental_test.py
```

### 3. Validação Completa
```bash
python coordinate_validator.py
```

## Estratégias de Prompt

1. **baseline** - Prompt simples sem coordenadas explícitas
2. **coordinate_validation** - Fornece coordenadas exatas do XML (baseado na Fase 0)
3. **enhanced_description** - Descrição rica com hints espaciais
4. **element_priority** - Priorização com anotações [UNTESTED], [SPINNER]
5. **spinner_focused** - Foco específico em Spinner/ComboBox (problema identificado)

## Métricas Coletadas

- **Hit Rate**: % de clicks que atingem elementos válidos (<50px)
- **Coordinate Precision**: Distância média do centro real do elemento
- **Element Coverage**: % de elementos únicos testados
- **Response Time**: Tempo de decisão do LLM
- **Tool Call Success**: % de tool calls executados corretamente
- **Explanation Quality**: Análise do raciocínio capturado

## Dataset

Usa screenshots de `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/`:

- `cryptoapp.apk` - App nosso, simples, 25 screenshots
- `byrne.utilities.hashpass_2.apk` - Similar ao cryptoapp
- `com.hwloc.lstopo_271.apk` - Elementos dinâmicos
- `org.secuso.privacyfriendlyludo_5.apk` - Jogo com campos dinâmicos

Cada app tem triplas: `001.png`, `001.state`, `001.uiautomator`

## Output

- Arquivos JSON com métricas detalhadas
- Análise de progressão por estratégia
- Logs com explanation de cada decisão do LLM
- Recomendações para otimização de prompts

## Objetivos

1. **Baseline**: Entender performance atual do Gemma3-tools
2. **Comparison**: Comparar com resultados da Fase 0 (Qwen: 72.1% → 81.6%)
3. **Optimization**: Identificar melhor estratégia de prompt
4. **Integration**: Aplicar descobertas no RVAgent principal
5. **Spinner Fix**: Resolver problema específico com ComboBox/Spinner

## Critérios de Sucesso

- **Mínimo**: 70% hit rate (baseline Phase 0)
- **Target**: 80%+ hit rate com prompt otimizado
- **Stretch**: 90%+ com coordinate_validation strategy
- **Precisão**: < 10px distância média
- **Coverage**: Identificar e resolver problema do Spinner