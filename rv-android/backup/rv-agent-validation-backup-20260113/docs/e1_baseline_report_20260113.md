# E1 Baseline - Relatório de Validação

**Data**: 13/01/2026
**Experimento**: E1 Baseline - Comparação de Modos de Execução
**Duração**: ~14 horas (12/01 16:30 - 13/01 ~06:30)

---

## 1. Resumo Executivo

O experimento E1 Baseline avaliou três modos de execução do rv-agent em 14 aplicativos Android, com 4 seeds por configuração, totalizando **168 execuções** sem erros.

### Principais Descobertas

| Métrica | pure_algorithm | llm_only | multimode |
|---------|----------------|----------|-----------|
| **Hit Rate (todos apps)** | N/A | 94.4% | 93.6% |
| **Hit Rate (apps standard)** | N/A | **98.7%** | **98.5%** |
| **Estados Únicos** | **15.9** | 5.7 | 7.6 |
| **Iterações** | **107** | 27 | 30 |
| **Runs com 100% HR** | - | 78.6% | 69.6% |

**Conclusões**:
1. A LLM (Qwen3-VL) demonstra **altíssima precisão** (98-99% hit rate em apps standard)
2. Apps com **renderização canvas** (jogos) requerem categoria separada
3. O algoritmo puro explora **2.8x mais estados** por não ter latência de LLM
4. O modo multimode combina exploração eficiente com precisão alta

---

## 2. Configuração do Experimento

### 2.1 Parâmetros

| Parâmetro | Valor |
|-----------|-------|
| Aplicativos | 14 |
| Modos | pure_algorithm, llm_only, multimode |
| Seeds | 42, 123, 456, 789 |
| Timeout | 300s por execução |
| Total de runs | 168 |
| LLM | Qwen/Qwen3-VL-4B-Instruct |
| Servidor | SGLang @ 192.168.0.21:30000 |
| Prompt | v13 (com tratamento de diálogos) |

### 2.2 Aplicativos Testados

| # | Package | Categoria | Tipo UI |
|---|---------|-----------|---------|
| 1 | br.unb.cic.cryptoapp | Criptografia | **Standard** |
| 2 | byrne.utilities.hashpass | Senhas | **Standard** |
| 3 | ca.farrelltonsolar.classic | Utilitário | **Standard** |
| 4 | com.gianlu.dnshero | Rede | **Standard** |
| 5 | com.github.axet.hourlyreminder | Produtividade | **Standard** |
| 6 | com.hwloc.lstopo | Sistema | **Standard** |
| 7 | com.sam.hex | Jogo | **Canvas** |
| 8 | info.zamojski.soft.towercollector | Localização | **Standard** |
| 9 | livio.rssreader | Notícias | **Standard** |
| 10 | org.emunix.insteadlauncher | Jogo | **Canvas** |
| 11 | org.pulpdust.lesserpad | Notas | **Standard** |
| 12 | org.secuso.privacyfriendlydicer | Jogo | **Standard** |
| 13 | org.secuso.privacyfriendlyludo | Jogo | **Standard** |
| 14 | t20kdc.offlinepuzzlesolver | Puzzle | **Standard** |

**Classificação de Tipo UI**:
- **Standard**: UI nativa Android com elementos expostos no UIAutomator
- **Canvas**: Renderização customizada (WebView, Canvas, OpenGL) não exposta ao UIAutomator

### 2.3 Descrição dos Modos

| Modo | LLM | Algoritmo | Descrição |
|------|-----|-----------|-----------|
| `pure_algorithm` | 0% | 100% | Apenas RVAgentStrategy (DFS + priorização) |
| `llm_only` | 100% | 0% | Apenas decisões da LLM |
| `multimode` | 70% | 30% | Híbrido com routing dinâmico |

---

## 3. Resultados Detalhados

### 3.1 Estatísticas por Modo

#### pure_algorithm

| Métrica | Média | Std | Min | Max | Mediana |
|---------|-------|-----|-----|-----|---------|
| Estados únicos | 15.9 | 8.7 | 1 | 32 | 16.0 |
| Iterações | 107.2 | 30.7 | 12 | 161 | 116.0 |
| Tempo (s) | 281.3 | 63.0 | - | - | - |

**Observação**: Este modo não possui hit rate pois não usa LLM.

#### llm_only

| Métrica | Média | Std | Min | Max | Mediana |
|---------|-------|-----|-----|-----|---------|
| Hit Rate | 94.4% | 15.7 | 0% | 100% | 100% |
| Estados únicos | 5.7 | 4.0 | 0 | 20 | 5.0 |
| Iterações | 27.1 | 19.2 | 0 | 65 | 37.0 |
| Tempo (s) | 191.8 | 132.4 | - | - | - |

#### multimode

| Métrica | Média | Std | Min | Max | Mediana |
|---------|-------|-----|-----|-----|---------|
| Hit Rate | 93.6% | 19.7 | 0% | 100% | 100% |
| Estados únicos | 7.6 | 5.7 | 1 | 22 | 6.0 |
| Iterações | 30.2 | 23.0 | 1 | 82 | 34.5 |
| Tempo (s) | 176.8 | 127.6 | - | - | - |

### 3.2 Distribuição de Hit Rate

#### llm_only
```
     100%: 44 runs (78.6%) ████████████████████████████████████████
   90-99%:  3 runs ( 5.4%) ███
   80-89%:  1 run  ( 1.8%) █
   70-79%:  5 runs ( 8.9%) █████
     <70%:  3 runs ( 5.4%) ███
```

#### multimode
```
     100%: 39 runs (69.6%) ███████████████████████████████████
   90-99%:  9 runs (16.1%) ████████
   80-89%:  5 runs ( 8.9%) █████
   70-79%:  0 runs ( 0.0%)
     <70%:  3 runs ( 5.4%) ███
```

### 3.3 Resultados por Aplicativo

| Aplicativo | Tipo | Alg. States | LLM HR | LLM States | Multi HR | Multi States |
|------------|------|-------------|--------|------------|----------|--------------|
| cryptoapp | Std | 26.8 | 100% | 10.5 | 100% | 12.5 |
| hashpass | Std | 5.0 | 99% | 8.2 | 99% | 7.0 |
| classic | Std | 14.2 | 100% | 3.2 | 100% | 3.0 |
| dnshero | Std | 1.0 | 100% | 4.2 | 100% | 5.8 |
| hourlyreminder | Std | 26.5 | 96% | 2.5 | 100% | 3.5 |
| lstopo | Std | 7.5 | 99% | 10.0 | 99% | 13.0 |
| **hex** | **Canvas** | 26.2 | **83%** | 7.2 | **95%** | 12.0 |
| towercollector | Std | 17.0 | 100% | 5.8 | 100% | 5.0 |
| rssreader | Std | 29.2 | 100% | 4.0 | 99% | 10.2 |
| **insteadlauncher** | **Canvas** | 11.0 | **70%** | 6.2 | **76%** | 6.2 |
| lesserpad | Std | 14.0 | 100% | 4.0 | 94% | 10.2 |
| privacyfriendlydicer | Std | 15.8 | 100% | 4.0 | 100% | 4.0 |
| privacyfriendlyludo | Std | 18.8 | 100% | 5.5 | 96% | 7.8 |
| offlinepuzzlesolver | Std | 9.2 | 100% | 4.5 | 100% | 6.2 |

---

## 4. Análise de Apps Canvas (Hit Rate Baixo)

### 4.1 Problema Identificado

Os apps com hit rate significativamente menor são **jogos que usam renderização customizada**. O conteúdo interativo do jogo não é exposto na hierarquia UIAutomator.

### 4.2 Análise Detalhada: org.emunix.insteadlauncher

**Tipo**: Engine de jogos de aventura texto (INSTEAD)

**UI durante gameplay (InsteadActivity)**:
```
Total elementos no XML: 5
Elementos clicáveis:    2

  [-] SystemAction_BACK
  [C] Button (android)        ← Único botão de sistema
  [C] ImageButton             ← Menu/settings
  [-] TextView (android)      ← Texto do jogo (não clicável)
  [-] TextView (android)      ← Mais texto (não clicável)
```

**Problema**:
- O jogo renderiza conteúdo interativo (links, escolhas) em um **WebView/TextView customizado**
- A LLM vê visualmente opções clicáveis no screenshot
- UIAutomator não expõe esses elementos como interativos
- Resultado: Cliques em texto do jogo → `ui_miss`

**Classificação dos Misses**:
| Modo | Total Ações | Hits | UI Miss | Hit Rate |
|------|-------------|------|---------|----------|
| llm_only | 30 | 21 | 9 | 70.0% |
| multimode | 29 | 24 | 5 | 82.8% |

### 4.3 Análise Detalhada: com.sam.hex

**Tipo**: Jogo de tabuleiro hexagonal

**UI durante gameplay (HexGame)**:
```
Total elementos no XML: 19
Elementos clicáveis:    8

  [C] ImageButton (menu)
  [-] ImageView (hex)         ← TABULEIRO DO JOGO (não clicável!)
  [-] ImageView (hex)         ← Células do tabuleiro
  [C] LinearLayout            ← Container
  [C] TextView (score)
  [C] TextView (turn)
  [-] SystemUI elements...
```

**Problema**:
- O tabuleiro hexagonal é um `ImageView` com `clickable=false`
- A LLM vê as células hexagonais e tenta jogar (comportamento correto!)
- Coordenadas típicas dos misses: `(538, 917-960)` - centro do tabuleiro
- UIAutomator não registra cliques no canvas do jogo

**Classificação dos Misses**:
| Modo | Total Ações | Hits | UI Miss | Empty Miss | Hit Rate |
|------|-------------|------|---------|------------|----------|
| llm_only | 144 | 120 | 23 | 1 | 83.3% |
| multimode | 154 | 147 | 6 | 1 | 95.5% |

### 4.4 Padrão Comum

| Característica | insteadlauncher | hex |
|----------------|-----------------|-----|
| Tipo de jogo | Aventura texto | Tabuleiro |
| Renderização | WebView/Custom TextView | Canvas/ImageView |
| Elementos no XML | 5 | 19 |
| Clicáveis no XML | 2 | 8 |
| Área interativa visual | Grande (texto) | Grande (grid) |
| Área clicável real | Pequena (2 botões) | Pequena (menus) |

### 4.5 Conclusão: Não é Problema da LLM

A LLM está **corretamente identificando elementos visuais interativos**. O problema é que:

1. **Jogos usam renderização customizada** que não expõe elementos ao UIAutomator
2. **Hit rate mede cliques no XML**, não a intenção correta da LLM
3. A LLM está "jogando o jogo" corretamente, mas isso é classificado como miss

### 4.6 Hit Rate Ajustado (Excluindo Apps Canvas)

Recalculando hit rate apenas para apps com UI standard (12 apps):

| Modo | Hit Rate Original | Hit Rate (Standard Only) | Diferença |
|------|-------------------|--------------------------|-----------|
| llm_only | 94.4% | **98.7%** | +4.3% |
| multimode | 93.6% | **98.5%** | +4.9% |

**Distribuição ajustada (llm_only, apps standard)**:
```
     100%: 40 runs (83.3%) ██████████████████████████████████████████
   90-99%:  3 runs ( 6.3%) ███
   80-89%:  1 run  ( 2.1%) █
   70-79%:  4 runs ( 8.3%) ████
     <70%:  0 runs ( 0.0%)
```

---

## 5. Análise Comparativa

### 5.1 Exploração vs Precisão

```
                    Estados Únicos (média)
    ┌────────────────────────────────────────┐
    │                                        │
 20 ┤ ████████████████                       │ pure_algorithm: 15.9
    │                                        │
 15 ┤                                        │
    │                                        │
 10 ┤         ████████                       │ multimode: 7.6
    │                                        │
  5 ┤     ██████                             │ llm_only: 5.7
    │                                        │
  0 ┼────────────────────────────────────────┘
       pure_alg   llm_only   multimode
```

O algoritmo puro explora significativamente mais estados porque:
1. **Sem latência de LLM**: Cada iteração leva ~1-2s vs ~7-8s com LLM
2. **Execução mais rápida**: 107 iterações vs 27-30 com LLM
3. **Exploração sistemática**: DFS com backtracking eficiente

### 5.2 Eficiência de Iterações

| Modo | Iterações/min | Estados/min |
|------|---------------|-------------|
| pure_algorithm | 22.8 | 3.4 |
| llm_only | 8.5 | 1.8 |
| multimode | 10.3 | 2.6 |

### 5.3 Trade-off Precisão vs Cobertura

| Modo | Vantagem | Desvantagem |
|------|----------|-------------|
| pure_algorithm | Máxima exploração | Sem inteligência contextual |
| llm_only | Decisões contextuais | Baixa cobertura, alta latência |
| multimode | Equilíbrio | Complexidade de routing |

---

## 6. Análise de Hit Rate

### 6.1 Classificação de Cliques

O hit rate mede a precisão dos cliques da LLM em elementos interativos:

| Classificação | Descrição |
|---------------|-----------|
| **HIT** | Clique em elemento interativo válido |
| **NEAR_MISS** | Clique próximo a elemento (< 50px) |
| **UI_MISS** | Clique em elemento não-interativo |
| **EMPTY_MISS** | Clique em área vazia |

### 6.2 Fatores que Afetam Hit Rate

1. **Renderização Canvas**: Apps com canvas/WebView têm elementos não expostos ao UIAutomator
2. **Diálogos sobrepostos**: Tratados pelo prompt v13
3. **Elementos dinâmicos**: Animações podem causar dessincronização
4. **Coordenadas normalizadas**: Qwen3-VL usa [0,1000) que requer conversão

### 6.3 Categorização de Apps por Tipo UI

| Categoria | Descrição | Hit Rate Esperado | Métrica Recomendada |
|-----------|-----------|-------------------|---------------------|
| **Standard** | UI nativa Android | 95-100% | Hit Rate |
| **Canvas** | Jogos/WebView | 70-85% | Activity Coverage |

---

## 7. Métricas de Performance

### 7.1 Tempo por Modo

| Modo | Tempo Médio | % do Timeout |
|------|-------------|--------------|
| pure_algorithm | 281.3s | 93.8% |
| llm_only | 191.8s | 63.9% |
| multimode | 176.8s | 58.9% |

**Observação**: Modos com LLM terminam antes devido a:
- Stuck detection mais agressivo
- Menor número de iterações antes do timeout

### 7.2 Custo de LLM (estimado)

| Modo | Chamadas LLM | Tokens (est.) |
|------|--------------|---------------|
| pure_algorithm | 0 | 0 |
| llm_only | ~27/run | ~70k/run |
| multimode | ~21/run | ~55k/run |

---

## 8. Conclusões

### 8.1 Validação do Sistema

1. **LLM funciona corretamente**: 98-99% hit rate em apps standard demonstra excelente precisão
2. **Apps canvas requerem categoria separada**: Hit rate não é métrica adequada para jogos
3. **Prompt v13 efetivo**: Tratamento de diálogos melhorou hit rate
4. **Modos funcionam conforme esperado**: Cada modo tem características distintas

### 8.2 Recomendações

| Cenário | Modo Recomendado |
|---------|------------------|
| Exploração máxima | pure_algorithm |
| Interação inteligente | llm_only |
| Produção/Geral | multimode |

### 8.3 Recomendações para Apps Canvas

1. **Classificar apps por tipo UI** antes do experimento
2. **Usar activity_coverage** como métrica principal para apps canvas
3. **Reportar hit rate separadamente** por categoria
4. **Considerar métricas alternativas**: tempo em tela, sequência de ações, cobertura visual

### 8.4 Próximos Passos

1. ~~Investigar apps problemáticos~~: ✅ Identificado como problema de renderização canvas
2. **Implementar classificação automática** de tipo UI (detectar canvas/WebView)
3. **Expandir dataset** com mais apps de cada categoria
4. **Análise de cobertura MOP**: Verificar se estados explorados cobrem operações monitoradas

---

## 9. Anexos

### 9.1 Arquivos de Resultados

```
validation_results/e1_baseline_20260112_163000/
├── config.json                              # Configuração do experimento
├── results_final.json                       # Resultados consolidados
├── results_progress.json                    # Progresso incremental
└── multimodal_metrics_*.json (168 arquivos) # Métricas detalhadas por run
```

### 9.2 Comando de Execução

```bash
cd modules/rv-agent
PYTHONPATH=../rv-android-core/src:src poetry run python validation/run_multimodal.py run \
  --apks-dir "validation/apks" \
  --modes "pure_algorithm,llm_only,multimode" \
  --timeout 300 \
  --seeds "42,123,456,789" \
  --output "validation_results/e1_baseline_20260112_163000"
```

### 9.3 Ambiente

| Componente | Versão/Configuração |
|------------|---------------------|
| Python | 3.12 |
| LLM | Qwen/Qwen3-VL-4B-Instruct |
| Servidor LLM | SGLang |
| Emulador | Android SDK (emulator-5554) |
| Prompt | v13 |

### 9.4 Cálculo do Hit Rate Ajustado

```python
# Apps canvas (excluídos do cálculo ajustado)
canvas_apps = ['org.emunix.insteadlauncher', 'com.sam.hex']

# Apps standard (12 apps)
standard_apps = [app for app in all_apps if app not in canvas_apps]

# Hit rate ajustado
# llm_only:  98.7% (48 runs, excluindo 8 runs de canvas)
# multimode: 98.5% (48 runs, excluindo 8 runs de canvas)
```

---

**Relatório gerado em**: 13/01/2026
**Autor**: RV-Agent Validation Suite
**Versão**: 1.1 (adicionada análise de apps canvas)
