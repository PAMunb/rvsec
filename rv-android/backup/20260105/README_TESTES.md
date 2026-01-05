# Scripts de Teste - RVSmart e RVDroid

Este diretório contém scripts de teste para as ferramentas RVSmart e RVDroid atualizadas com componentes compartilhados.

## 📋 Pré-requisitos OBRIGATÓRIOS

### 1. 📱 Emulador Android
**SEMPRE inicie o emulador ANTES de executar os testes:**

```bash
# Opção 1: Via Android Studio
Android Studio → AVD Manager → Start emulator

# Opção 2: Via linha de comando
emulator @nome_do_avd

# Verificar se está rodando:
adb devices
# Deve mostrar: emulator-5554    device
```

### 2. 🤖 Ollama (para LLM)
```bash
# Iniciar serviço
ollama serve

# Baixar modelo (se não tiver)
ollama pull gemma2
```

### 3. 📦 Dependências Instaladas
```bash
# Instalar módulos necessários
cd modules/rv-uiautomator && poetry install
cd modules/rvsmart-tool && poetry install  
cd modules/rvdroid-tool && poetry install
```

## 🧪 Scripts de Teste Disponíveis

### 1. `teste_rvsmart.py` - RVSmart Tool
Testa a nova ferramenta RVSmart com arquitetura TestOrchestrator:
- ✅ Todos os variants do RVSmart
- ✅ Integração com UIAutomator
- ✅ LLM action generation
- ✅ External navigation handling

```bash
python teste_rvsmart.py
```

### 2. `teste_rvdroid_updated.py` - RVDroid Refatorado  
Testa o RVDroid refatorado usando componentes compartilhados:
- ✅ Componentes compartilhados rv-uiautomator
- ✅ Compatibilidade com arquitetura RVDroid
- ✅ Integração com LLM (opcional)

```bash
python teste_rvdroid_updated.py
```

## 📊 O que os Testes Verificam

### RVSmart Tests
1. **Tool Integration**: Integração com rv-tools framework
2. **Variant Testing**: Testa todos os variants (default, claude, vision, vision_ctx)
3. **TestOrchestrator**: Coordenação LLM + UIAutomator 
4. **External Navigation**: Handling de navegação externa
5. **Metrics Collection**: Coleta de métricas de execução

### RVDroid Tests  
1. **Shared Components**: Funcionamento dos componentes compartilhados
2. **Adapter Compatibility**: Compatibilidade do adapter refatorado
3. **Integration**: Integração completa com componentes compartilhados

## 🚨 Troubleshooting

### Emulador não detectado
```bash
# Verificar devices
adb devices

# Reiniciar ADB se necessário
adb kill-server
adb start-server
```

### Erro de dependências
```bash
# Reinstalar dependências
cd modules/[MODULE_NAME]
poetry install --verbose
```

### Erro de conexão UIAutomator
- Aguarde o emulador inicializar COMPLETAMENTE
- Teste conexão manual: `adb shell uiautomator dump`

### Erro de LLM
```bash
# Verificar Ollama
ollama list
ollama pull gemma2
```

## 📈 Interpretação dos Resultados

### ✅ Sucesso
- Todos os componentes funcionando
- Actions geradas pelo LLM
- Métricas coletadas corretamente

### ❌ Falhas Comuns
- **Emulator not running**: Suba o emulador primeiro
- **Connection timeout**: Aguarde inicialização completa
- **LLM error**: Verifique se Ollama está rodando
- **Import error**: Instale dependências faltantes

## 🎯 Foco Atual

**PRIORIDADE: RVSmart Testing**
- Execute primeiro: `teste_rvsmart.py` 
- RVDroid está pronto mas será testado posteriormente
- Ambos os scripts têm verificações de pré-requisitos

## 📞 Ajuda

Se os testes falharem:
1. Verifique pré-requisitos acima
2. Leia mensagens de erro cuidadosamente  
3. Scripts têm logs detalhados para debug