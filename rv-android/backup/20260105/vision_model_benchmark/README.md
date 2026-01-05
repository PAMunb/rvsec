# Vision Model Benchmark Framework

Framework genérico para testar e comparar modelos de visão multimodal na geração de coordenadas para Android UI automation.

## 📋 Visão Geral

Este framework permite testar sistematicamente diferentes modelos de visão (Gemma, LLaMA, LLaVA, Qwen, Granite) na tarefa de geração de coordenadas para interação com aplicativos Android, usando uma coleção diversa de screenshots reais.

## 🤖 Modelos Suportados

### Disponíveis Localmente:
- **gemma3:4b** - Google Gemma 3 4B (baseline conhecido)
- **gemma3:12b** - Google Gemma 3 12B (versão maior)
- **llama3.2-vision:11b** - Meta LLaMA 3.2 Vision 11B
- **llava-llama3:8b** - LLaVA LLaMA 3 8B (especializado em visão)
- **qwen2.5vl:3b** - Qwen 2.5 Vision Language 3B (compacto)
- **qwen2.5vl:7b** - Qwen 2.5 Vision Language 7B (maior)
- **granite3.2-vision:2b** - IBM Granite 3.2 Vision 2B (eficiente)

## 🎯 Cenários de Teste

### 1. **Coordinate Validation**
- **Descrição**: Teste de precisão quando coordenadas explícitas são fornecidas
- **Objetivo**: Verificar capacidade de seleção entre coordenadas fornecidas
- **Critério de Sucesso**: 80% hit rate, <50px distância média

### 2. **Visual Generation**
- **Descrição**: Geração de coordenadas baseada apenas em análise visual
- **Objetivo**: Testar capacidade de estimação espacial pura
- **Critério de Sucesso**: 30% hit rate, <200px distância média

### 3. **Game Elements**
- **Descrição**: Elementos de jogo não-DOM renderizados dinamicamente
- **Objetivo**: Testar limitações em elementos puramente visuais
- **Critério de Sucesso**: 20% hit rate, <300px distância média

### 4. **Mixed Scenario**
- **Descrição**: Cenários híbridos com elementos DOM e visuais
- **Objetivo**: Testar capacidade de decisão inteligente
- **Critério de Sucesso**: 60% hit rate, <100px distância média

## 📁 Estrutura do Framework

```
vision_model_benchmark/
├── model_config.py          # Configurações dos modelos
├── benchmark_framework.py   # Framework principal de testes
├── report_generator.py      # Gerador de relatórios
├── benchmark_runner.py      # Interface de linha de comando
├── run_quick_benchmark.py   # Teste rápido
└── README.md               # Esta documentação
```

## 🚀 Como Usar

### Teste Rápido (Recomendado para Começar)

```bash
cd vision_model_benchmark/
python run_quick_benchmark.py
```

**O que faz**:
- Testa 5 modelos representativos
- 2 cenários principais
- 3 amostras por cenário
- ~30 testes totais em ~5-10 minutos

### Benchmark Abrangente

```bash
cd vision_model_benchmark/
python benchmark_runner.py comprehensive
```

**Opções avançadas**:
```bash
# Testar modelos específicos
python benchmark_runner.py comprehensive --models gemma3:4b llama3.2-vision:11b

# Testar cenários específicos  
python benchmark_runner.py comprehensive --scenarios coordinate_validation visual_generation

# Mais amostras por cenário
python benchmark_runner.py comprehensive --samples 5
```

### Comparação Direta Entre Modelos

```bash
python benchmark_runner.py compare gemma3:4b llama3.2-vision:11b
```

### Análise de Cenário Específico

```bash
python benchmark_runner.py scenario coordinate_validation
```

### Listar Opções Disponíveis

```bash
python benchmark_runner.py list
```

## 📊 Dados de Teste

O framework utiliza a coleção existente de screenshots em:
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots/
```

**Características dos dados**:
- **Apps diversos**: Network tools, games, system utilities, etc.
- **Screenshots reais**: Capturas de diferentes estados de aplicação
- **State files**: Informações estruturais do DOM para cada screenshot
- **Cobertura ampla**: Diferentes tipos de interface e complexidade

## 📈 Métricas e Análises

### Métricas Principais:
- **Success Rate**: Porcentagem de testes bem-sucedidos
- **Hit Rate**: Porcentagem de coordenadas dentro de 50px do alvo
- **Average Distance**: Distância média em pixels do alvo esperado
- **Response Time**: Tempo médio de resposta do modelo
- **Parsing Success**: Taxa de sucesso na extração de coordenadas

### Análises Geradas:
1. **Summary Report**: Visão executiva com rankings
2. **Detailed Report**: Análise aprofundada por modelo
3. **Comparison Tables**: Tabelas comparativas entre modelos
4. **Performance Charts**: Visualizações gráficas
5. **Head-to-Head**: Comparações diretas entre dois modelos

## 🎯 Configurações Especializadas

Cada modelo possui prompts especializados otimizados para suas características:

### Exemplo - Gemma 3:4b:
```python
specialized_prompts = {
    "coordinate_validation": """
    {ui_elements}
    
    Task: Choose ONE element and use EXACT coordinates from "at position (x, y)".
    Return JSON: {"coordinates": [x, y], "element": "description"}
    """,
    
    "visual_generation": """
    Analyze screenshot and generate coordinates for interactive element.
    Return JSON: {"coordinates": [x, y], "element": "description"}
    """
}
```

## 📋 Resultados Esperados

Com base nos testes anteriores do Gemma 3:4b:

### Coordinate Validation:
- **Esperado**: 90-100% success rate, 0-20px distance
- **Razão**: Coordenadas explícitas eliminam problemas de estimação

### Visual Generation:
- **Esperado**: 20-40% success rate, 200-400px distance  
- **Razão**: Modelos têm viés sistemático e limitações espaciais

### Comparação Entre Modelos:
- **Famílias diferentes** podem ter estratégias de treinamento distintas
- **Modelos maiores** podem ter melhor raciocínio espacial
- **Especialização em visão** (LLaVA) pode superar modelos generais

## 🔧 Personalização

### Adicionar Novo Modelo:
1. Adicionar configuração em `model_config.py`
2. Definir prompts especializados
3. Executar testes

### Novo Cenário de Teste:
1. Adicionar em `TEST_SCENARIOS` (model_config.py)
2. Implementar lógica específica no framework
3. Definir critérios de sucesso

### Métricas Customizadas:
1. Estender `ModelPerformance` dataclass
2. Implementar cálculos em `analyze_results()`
3. Adicionar aos relatórios

## 🎉 Exemplo de Execução

```bash
$ python run_quick_benchmark.py

🚀 QUICK VISION MODEL BENCHMARK
============================================================
Testing coordinate generation across diverse Android applications

📱 Found 15 different applications
📊 Total screenshots with state files: 127
🤖 Available models: 7
🎯 Testing 5 representative models

🚦 Start benchmark? (y/N): y

🏁 Starting benchmark...
============================================================

[Execução dos testes...]

✅ Benchmark completed successfully!
📁 Results saved to: quick_benchmark_results/

🏆 QUICK SUMMARY
==============================
Model Rankings:
  🥇 1. gemma3:4b
      Success: 85.2%  
      Distance: 32.1px
      Speed: 2.3s

  🥈 2. llama3.2-vision:11b
      Success: 78.9%
      Distance: 45.7px  
      Speed: 3.1s
      
  [...]
```

Este framework fornece uma avaliação sistemática e comparativa dos modelos de visão disponíveis, permitindo identificar o melhor modelo para integração no rv-android-tool.