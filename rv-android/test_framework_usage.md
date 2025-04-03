# RV-Android Test Framework - Guia de Uso

Este guia fornece informações sobre como usar o framework de testes para avaliar diferentes configurações de ferramentas RVAndroid e RVDroid.

## 1. Introdução

O framework de testes permite a avaliação sistemática de diferentes configurações de ferramentas RVAndroid e RVDroid, incluindo variações de modelos LLM, estratégias de prompt, parsers e visitantes para identificar configurações ótimas para testes de aplicativos Android.

## 2. Instalação

O framework de testes é parte do sistema RV-Android e não requer instalação adicional. Certifique-se de que todas as dependências do RV-Android estão instaladas.

## 3. Uso Básico

### 3.1 Execução de Testes

Para executar um conjunto de testes simples:

```bash
python run_test_framework.py run --apps apks_examples/*.apk --analyze
```

Este comando irá:
1. Executar testes em todos os APKs no diretório `apks_examples/`
2. Usar configurações de teste padrão
3. Analisar os resultados após a conclusão

### 3.2 Criação de Configuração Personalizada

Para criar um arquivo de configuração personalizado:

```bash
python run_test_framework.py create-config --name "Meu Experimento" --output my_config.json
```

Você pode editar o arquivo `my_config.json` para personalizar as configurações de teste conforme necessário.

### 3.3 Execução com Configuração Personalizada

Para executar testes com uma configuração personalizada:

```bash
python run_test_framework.py run --apps apks_examples/*.apk --config my_config.json --analyze
```

## 4. Configuração Avançada

### 4.1 Estrutura do Arquivo de Configuração

O arquivo de configuração é um documento JSON com a seguinte estrutura:

```json
{
  "name": "Nome do Experimento",
  "description": "Descrição do experimento",
  "tool_configurations": [
    {
      "tool_name": "rvandroid",
      "timeout": 300,
      "llm_type": "ollama",
      "llm_model": "llama3.2:3b",
      "temperature": 0.2,
      "max_tokens": 800,
      "strategy_type": "composable_single_action",
      "parser_type": "droidbot",
      "visitor_type": "enhanced",
      "use_static_analysis": true,
      "static_analysis_level": "detailed",
      "use_screenshot_analysis": false,
      "extra_params": {}
    },
    // Mais configurações...
  ],
  "apps": [],
  "output_dir": "test_results",
  "repetitions": 3
}
```

### 4.2 Parâmetros de Configuração

#### Tool Configuration

| Parâmetro | Descrição | Valores Possíveis |
|-----------|-----------|-------------------|
| `tool_name` | Nome da ferramenta | `rvandroid`, `rvdroid` |
| `timeout` | Timeout em segundos | Número inteiro |
| `llm_type` | Tipo de modelo LLM | `ollama`, `huggingface`, `dspy`, `langchain`, `frontier` |
| `llm_model` | Nome do modelo | Depende do `llm_type` |
| `temperature` | Temperatura para geração | Float entre 0.0 e 1.0 |
| `max_tokens` | Máximo de tokens na resposta | Número inteiro |
| `strategy_type` | Estratégia de prompt | `basic`, `single_action`, `composable_single_action`, etc. |
| `parser_type` | Tipo de parser | `droidbot`, `uiautomator` |
| `visitor_type` | Tipo de visitor | `basic`, `enhanced`, `detailed` |
| `use_static_analysis` | Usar análise estática | `true`, `false` |
| `static_analysis_level` | Nível de análise estática | `basic`, `standard`, `detailed` |
| `use_screenshot_analysis` | Usar análise de screenshot | `true`, `false` |

## 5. Interpretação dos Resultados

### 5.1 Relatório de Análise

Após a execução dos testes, se a opção `--analyze` for especificada, um relatório HTML será gerado no diretório de saída. Este relatório inclui:

- Gráfico de pontuação geral por configuração
- Comparação de cobertura entre configurações
- Comparação de desempenho entre ferramentas
- Lista das melhores configurações por categoria

### 5.2 Configurações Ótimas

As configurações ótimas são identificadas com base em diferentes critérios:

- **Overall**: Melhor pontuação geral considerando cobertura, tempo de execução e taxa de sucesso
- **Method Coverage**: Maior cobertura de métodos
- **Activity Coverage**: Maior cobertura de atividades
- **MOP Coverage**: Maior cobertura de métodos com especificações MOP
- **Execution Speed**: Menor tempo de execução

## 6. Execução em Paralelo

Para executar testes em paralelo (quando há recursos disponíveis):

```bash
python run_test_framework.py run --apps apks_examples/*.apk --workers 4 --analyze
```

Este comando executará até 4 testes simultaneamente.

## 7. Exemplos

### Exemplo 1: Teste Básico

```bash
python run_test_framework.py run --apps apks_examples/cryptoapp.apk --analyze
```

### Exemplo 2: Comparação de Ferramentas

```bash
python run_test_framework.py run --apps apks_examples/*.apk --config test_suite_example.json --repetitions 3 --analyze --save-optimal
```

### Exemplo 3: Análise de Plateau com Múltiplos Timeouts

Para análise de plateau, use um arquivo de configuração com múltiplos timeouts e execute:

```bash
python run_test_framework.py run --apps apks_examples/*.apk --config plateau_config.json --analyze
```

## 8. Configurações Recomendadas

Com base em experimentos anteriores, estas são algumas configurações recomendadas para início:

### RVAndroid
- LLM: `ollama` com `llama3.2:3b`
- Estratégia: `composable_single_action`
- Parser: `droidbot`
- Visitor: `enhanced`
- Análise Estática: `detailed`

### RVDroid
- LLM: `ollama` com `llama3.2:3b`
- Estratégia: `composable_single_action`
- Parser: `uiautomator` (único disponível)
- Visitor: `enhanced`
- Análise Estática: `standard`
- Análise de Screenshot: `true` com nível `standard`

## 9. Resolução de Problemas

### Problemas Comuns

1. **Erro no emulador**: Certifique-se de que o emulador está funcionando corretamente antes de iniciar os testes.
2. **Modelos LLM não encontrados**: Verifique se os modelos Ollama estão instalados e disponíveis.
3. **Erro de memória**: Reduza o número de workers ou utilize menos configurações simultaneamente.

### Logs

Os logs detalhados são salvos no diretório de saída e podem ser usados para diagnóstico de problemas.