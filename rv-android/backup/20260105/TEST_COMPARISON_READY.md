# Teste Comparativo V10 vs V11 vs V12 - PRONTO PARA EXECUÇÃO

## ✅ Script Atualizado

**Arquivo**: `test_prompt_comparison_complete.py`

### Mudanças Realizadas

1. **28 Apps do Dataset Completo**
   - Extraídos usando `App` class (androguard)
   - Lista completa em `TEST_APPS` com comentários do APK original

2. **Descoberta Automática de APKs**
   - Função `discover_apks()`: Varre diretórios do dataset
   - Usa `App(app_path)` para extrair package name com androguard
   - Retorna lista com package, apk_path, app_dir

3. **Instalação Automática**
   - Função `install_apk()`: Desinstala + Instala com `-r -g`
   - Grant de todas as permissões automaticamente
   - Tratamento de erros de instalação

4. **Progresso Intermediário**
   - Salva `progress.json` após cada teste
   - Permite retomada em caso de interrupção
   - Mostra estatísticas: completed, failed, total

5. **Integração Completa**
   - `main()` atualizada para usar descoberta automática
   - Instalação antes de cada teste
   - Logs detalhados de progresso

## 📊 Métricas Coletadas (12 Categorias)

Conforme documentado em `METRICS_SUMMARY.md`:

1. **Ações Gerais**: total, por tipo, por decisor
2. **Decisor**: LLM vs Algoritmo (contagem, %, razão)
3. **UI Coverage Geral**: elementos únicos, interações, telas
4. **UI Coverage por Categoria**: EditText, Spinner, Button, etc.
5. **Exploração**: estados únicos, transições
6. **LLM Performance**: tokens, tempo, eficiência
7. **UI Tracker Detalhado**: discovery, interactions, distribution
8. **Temporal**: discovery rate, interaction rate
9. **Performance Derivadas**: actions/sec, tokens/action
10. **Short Term Memory**: iterações, taxa de sucesso, utilização
11. **Long Term Memory**: estados, activities, transições, sucesso global
12. **Metadata**: status, iterações, versão, package, timestamp

## 🔧 Configuração

```python
TEST_CONFIG = {
    "timeout": 300,  # 5 minutos por app
    "device_id": "emulator-5554",
    "agent_mode": "multimode",
    "strategy": "greedy",
    "llm_model": "qwen3-vl-4b-8k:latest",
    "llm_probability": 0.7,
    "device_dimensions": (1080, 1920),
    "optimized_dimensions": (704, 1248),
}
```

## 📈 Escopo do Teste

- **Apps**: 28 apps (dataset completo)
- **Prompts**: V10, V11, V12
- **Total de Testes**: 84 testes (28 × 3)
- **Tempo por App**: 300 segundos (5 minutos)
- **Duração Estimada**: ~420 minutos (~7 horas)

## 📁 Estrutura de Resultados

```
results/prompt_comparison_YYYYMMDD_HHMMSS/
├── comparative_analysis.json      # Análise agregada
├── comparative_report.md          # Relatório em Markdown
├── rankings.json                  # Rankings por métrica
├── progress.json                  # Progresso intermediário
├── v10_results/                   # Resultados individuais V10
│   ├── ar.rulosoft.mimanganu_v10.json
│   ├── au.com.wallaceit.reddinator_v10.json
│   └── ...
├── v11_results/                   # Resultados individuais V11
│   └── ...
└── v12_results/                   # Resultados individuais V12
    └── ...
```

## 🚀 Como Executar

```bash
# Certifique-se de que o emulador está rodando
adb devices

# Execute o teste comparativo completo
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
poetry run python test_prompt_comparison_complete.py
```

## 📊 Análises Geradas

### 1. comparative_analysis.json
Estrutura JSON com:
- `apps_tested`: Quantidade de apps
- `averages`: Média de todas as métricas por versão
- `action_types_average`: Média de cada tipo de ação

### 2. comparative_report.md
Relatório detalhado com:
- Tabela comparativa geral (V10 vs V11 vs V12)
- Winner por métrica (higher/lower)
- Distribuição de tipos de ação
- LLM vs Algoritmo por versão
- UI Coverage performance
- Memory system performance
- Recomendações baseadas nos resultados

### 3. rankings.json
Rankings das versões por métrica:
- Cada métrica ranqueada (1º, 2º, 3º)
- Valor da métrica para cada versão

## ⚠️ Importante

- **max_iterations foi REMOVIDO**: Agent para APENAS por timeout
- **300 segundos por teste**: 5 minutos de exploração
- **28 apps do dataset completo**: Todos os APKs válidos
- **Progresso salvo**: Pode retomar se interrompido
- **Instalação automática**: APKs instalados com `-g` (grant all permissions)

## 🎯 Objetivo

Fornecer análise comparativa abrangente dos prompts V10, V11 e V12 para apoiar decisões de desenvolvimento do RVAgent.

---

**Status**: ✅ PRONTO PARA EXECUÇÃO

**NÃO EXECUTE AINDA** - Aguardando confirmação do usuário.
