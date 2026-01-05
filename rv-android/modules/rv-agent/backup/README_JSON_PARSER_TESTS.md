# JSON Parser - Testes Detalhados

Scripts preparados para análise completa da distribuição de tools e elementos nos 28 apps.

## 📋 Scripts Disponíveis

### 1. `test_json_parser_detailed.py` ⭐ **PRINCIPAL**
**Teste completo com logging detalhado**

**O que faz:**
- Testa JSON parser em **28 apps**
- Processa **TODAS** as imagens de cada app (~468 screenshots)
- Captura dados detalhados:
  - ✅ Resposta completa da LLM (texto)
  - ✅ Tool calls extraídas (nome + argumentos completos)
  - ✅ Classificação de tipos de elementos UI
  - ✅ Distribuição de tools usadas
  - ✅ Distribuição de elementos identificados

**Tempo estimado:** ~8-10 minutos (468 screenshots × ~1-1.5s cada)

**Como executar:**
```bash
# Quando a GPU estiver livre:
poetry run python test_json_parser_detailed.py 2>&1 | tee test_detailed.log
```

**Saídas geradas:**
- `test_json_parser_detailed_results.json` - Resultados completos estruturados
- `test_detailed.log` - Log de execução
- Estatísticas no console (tool distribution, element distribution)

---

### 2. `analyze_detailed_results.py`
**Análise dos resultados detalhados**

**O que faz:**
- Lê o JSON gerado pelo teste detalhado
- Gera análise completa com:
  - Estatísticas gerais
  - Distribuição de tools (com gráficos ASCII)
  - Distribuição de elementos (com gráficos ASCII)
  - Top 5 apps com melhor performance
  - Apps com falhas
  - Exemplos de respostas LLM

**Como executar:**
```bash
# DEPOIS de executar test_json_parser_detailed.py:
poetry run python analyze_detailed_results.py
```

---

### 3. Outros Scripts de Referência

#### `test_json_parser.py`
Teste rápido com 1 screenshot (CryptoApp) - para validação rápida

#### `test_json_parser_all_apps.py`
Teste básico sem logs detalhados (apenas estatísticas)

#### `test_integrated_json_parser.py`
Teste de integração com RVAgent completo

---

## 🚀 Workflow Recomendado

### Passo 1: Executar Teste Detalhado
```bash
# Quando GPU estiver disponível
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent
poetry run python test_json_parser_detailed.py 2>&1 | tee test_detailed.log
```

### Passo 2: Analisar Resultados
```bash
# Imediatamente após o teste
poetry run python analyze_detailed_results.py
```

### Passo 3: Explorar JSON Detalhado
```bash
# Ver estrutura do JSON
cat test_json_parser_detailed_results.json | jq '.tool_distribution'
cat test_json_parser_detailed_results.json | jq '.element_distribution'

# Ver exemplos de respostas LLM
cat test_json_parser_detailed_results.json | jq '.detailed_results[0]'
```

---

## 📊 Dados Coletados

### JSON de Saída (`test_json_parser_detailed_results.json`)

```json
{
  "total_apps": 28,
  "total_screenshots": 468,
  "successful_parses": 465,
  "failed_parses": 3,
  "tool_distribution": {
    "android_click": 250,
    "android_type_text": 180,
    "android_swipe": 30,
    ...
  },
  "element_distribution": {
    "Button": 200,
    "Text Field/Input": 150,
    "Icon": 50,
    ...
  },
  "detailed_results": [
    {
      "app_name": "cryptoapp.apk",
      "screenshot": "001.png",
      "success": true,
      "method": "json_parser",
      "llm_response": "...",  # TEXTO COMPLETO DA RESPOSTA
      "tool_calls": [
        {
          "name": "android_type_text",
          "arguments": {
            "element_description": "Input text field",
            "x": 189,
            "y": 220,
            "text": "user@example.com"
          }
        }
      ],
      "elements": [
        {
          "description": "Input text field",
          "type": "Text Field/Input"
        }
      ]
    },
    ...
  ]
}
```

### Classificação de Elementos

O script classifica automaticamente elementos em:
- **Button** - Botões
- **Text Field/Input** - Campos de texto/entrada
- **Icon** - Ícones
- **Menu** - Menus
- **List** - Listas
- **Card** - Cards
- **Tab** - Tabs/Abas
- **Checkbox** - Checkboxes
- **Switch/Toggle** - Switches/Toggles
- **Image** - Imagens
- **Label** - Labels
- **Scrollable** - Elementos roláveis
- **Other/Generic** - Outros elementos

---

## 📈 Análise Esperada

Com base no teste anterior (`test_json_parser_all_apps.py`):

```
✅ Taxa de sucesso esperada: ~99.4%
📱 Total de apps: 28
📷 Total de screenshots: 468
🔧 Total de tool calls: ~472
```

O teste detalhado vai adicionar:
- Distribuição exata de cada tool (android_click, android_type_text, etc.)
- Distribuição de tipos de elementos UI
- Respostas completas da LLM para análise qualitativa

---

## ⚠️ Observações

1. **GPU Requirement**: Testes usam LLM local (Ollama qwen-vision-tools-v2)
2. **Tempo de execução**: ~8-10 minutos para teste completo
3. **Espaço em disco**: JSON resultante ~5-10 MB (com respostas completas)
4. **Memória**: Processar 468 screenshots pode usar ~2-4 GB RAM

---

## ✅ Status Atual

- ✅ Scripts criados e prontos para execução
- ✅ Permissões de execução configuradas
- ⏳ Aguardando GPU disponível para execução
- ⏳ Resultados detalhados pendentes

**Próximo passo**: Executar `test_json_parser_detailed.py` quando GPU estiver livre!
