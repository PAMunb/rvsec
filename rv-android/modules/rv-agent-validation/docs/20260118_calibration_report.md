# Relatório de Calibração - RV-Agent (Pure Algorithm)

**Data:** 2026-01-18 (atualizado 15:45)
**Experimento:** calibration_24apks_20260117_185036
**Modo:** pure_algorithm (sem LLM)

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Total de runs | 120 |
| Runs válidos | 110 (91.7%) |
| Runs com crash | 10 (8.3%) |
| APKs testados | 22 (2 com crash) |
| Seeds por APK | 5 |
| Timeout | 300s |

### Métricas Gerais (runs válidos)

| Métrica | Média | Desvio Padrão | Mín | Máx |
|---------|-------|---------------|-----|-----|
| UI Coverage (geral) | 37.2% | 20.5% | 0% | 83.9% |
| **UI Coverage (interativos)** | **63.6%** | - | - | - |
| Elementos por run | 75.0 | 58.1 | 11 | 226 |
| Interações por run | 1315.7 | 825.7 | - | - |
| Ações/minuto | 20.4 | 5.6 | 0.1 | 26.9 |

**Nota Importante:** UI Coverage de elementos interativos (63.6%) exclui containers e labels não-clicáveis (TextView, View, FrameLayout, etc).

---

## 2. Distribuição de Elementos Testados

| Categoria | Quantidade | Percentual |
|-----------|------------|------------|
| **Untested** | 5348 | **59.4%** |
| Tested once | 2280 | 25.3% |
| Tested multiple | 671 | 7.5% |
| Well tested | 703 | 7.8% |
| **TOTAL** | 9002 | 100% |

### Análise da Alta Taxa de Untested

A taxa de 59.4% de elementos untested é alta, mas a análise por tipo revela:

1. **Muitos são containers/labels não-interativos:** TextView (4231), View (149), FrameLayout (173)
2. **Cobertura de elementos interativos é 63.6%** - valor aceitável
3. **Problemas reais:** SeekBar (0%), RadioGroup (0%), Chip (0%)

---

## 3. Cobertura por Tipo de Componente

| Tipo | Elementos | Interações | Ratio | Cobertura | Status |
|------|-----------|------------|-------|-----------|--------|
| TextView | 4231 | 2055 | 0.49 | 26.8% | ⚪ Label |
| Button | 937 | 2617 | 2.79 | **68.5%** | ✅ OK |
| LinearLayout | 835 | 824 | 0.99 | 52.0% | ⚪ Container |
| ImageView | 635 | 635 | 1.00 | 32.9% | ⚪ Decorativo |
| CheckBox | 470 | 269 | 0.57 | 46.0% | ⚠️ Baixo |
| CheckedTextView | 347 | 326 | 0.94 | **63.7%** | ✅ OK |
| EditText | 340 | 720 | 2.12 | **62.4%** | ✅ OK |
| ImageButton | 275 | 1028 | 3.74 | **90.5%** | ✅ Excelente |
| FrameLayout | 173 | 43 | 0.25 | 22.0% | ⚪ Container |
| View | 149 | 35 | 0.23 | 18.1% | ⚪ Container |
| SystemAction_BACK | 110 | 0 | 0.00 | 0.0% | ⚪ Sistema |
| Switch | 106 | 183 | 1.73 | **91.5%** | ✅ Excelente |
| **SeekBar** | 78 | 0 | 0.00 | **0.0%** | ❌ PROBLEMA |
| LinearLayoutCompat | 65 | 94 | 1.45 | 58.5% | ✅ OK |
| Spinner | 60 | 124 | 2.07 | **91.7%** | ✅ Excelente |
| ViewPager | 59 | 133 | 2.25 | 37.3% | ⚠️ Baixo |
| ActionBar$Tab | 40 | 16 | 0.40 | 37.5% | ⚠️ Baixo |
| ScrollView | 28 | 142 | 5.07 | **96.4%** | ✅ Excelente |
| **RadioGroup** | 24 | 0 | 0.00 | **0.0%** | ❌ PROBLEMA |
| WebView | 12 | 240 | 20.00 | 41.7% | ⚠️ Médio |
| RecyclerView | 10 | 7 | 0.70 | 70.0% | ✅ OK |
| GridView | 5 | 3 | 0.60 | 60.0% | ✅ OK |
| ListView | 5 | 5 | 1.00 | 60.0% | ✅ OK |
| **Chip** | 4 | 0 | 0.00 | **0.0%** | ❌ PROBLEMA |
| TableLayout | 2 | 0 | 0.00 | 0.0% | ⚪ Container |
| ToggleButton | 1 | 1 | 1.00 | 100.0% | ✅ OK |
| HorizontalScrollView | 1 | 0 | 0.00 | 0.0% | ⚪ Container |

### Legenda
- ✅ OK/Excelente: Cobertura adequada
- ⚠️ Baixo/Médio: Pode melhorar
- ❌ PROBLEMA: Requer correção
- ⚪ Container/Label: Não necessita interação direta

---

## 4. Problemas Críticos Identificados

### 4.1 SeekBar - 0% Cobertura (78 elementos)

**APKs afetados:**
| APK | Elementos SeekBar |
|-----|-------------------|
| yaab | 21 |
| simplenotes | 12 |
| offlinepuzzlesolver | 10 |
| dicewarepasswordgenerator | 10 |
| hourlyreminder | 10 |
| privacyfriendlydicer | 10 |
| darknessimmunity | 5 |

**Causa:** O algoritmo atual suporta apenas CLICK e SET_TEXT. SeekBar requer ação SWIPE/DRAG.

**Impacto:** 7 APKs afetados, alguns com cobertura baixa por causa disso (dicewarepasswordgenerator: 18.6%).

**Recomendação:** Implementar ação SWIPE para elementos SeekBar.

### 4.2 RadioGroup - 0% Cobertura (24 elementos)

**APKs afetados:**
| APK | Elementos RadioGroup |
|-----|---------------------|
| dicewarepasswordgenerator | 20 |
| moneytracker | 4 |

**Causa:** RadioGroup é um container. Os RadioButton filhos deveriam ser clicados.

**Impacto:** Afeta significativamente dicewarepasswordgenerator (18.6% cobertura).

**Recomendação:** Verificar se RadioButton está sendo reconhecido pelo parser. Se não, expandir os filhos do RadioGroup.

### 4.3 Chip - 0% Cobertura (4 elementos)

**Causa:** Componente Material Design pode não estar marcado como clickable no XML.

**Recomendação:** Adicionar Chip à lista de elementos sempre clicáveis no parser.

---

## 5. Resultados por APK

| APK | Runs | UI Coverage | Untested% | Problemas |
|-----|------|-------------|-----------|-----------|
| animereleasenotifier | 5 | **83.9%** | 16.1% | - |
| fhem | 5 | **62.9%** | 37.1% | ActionBar$Tab baixo |
| mover | 5 | **62.0%** | 38.0% | - |
| app | 5 | **55.3%** | 44.7% | - |
| openpass | 5 | **55.1%** | 44.9% | - |
| darknessimmunity | 5 | **53.2%** | 46.8% | SeekBar, WebView |
| passera | 5 | 49.4% | 50.6% | - |
| privacyfriendlyludo | 5 | 46.5% | 53.5% | - |
| moneytracker | 5 | 45.7% | 54.3% | RadioGroup |
| yaab | 5 | 42.9% | 57.1% | SeekBar (21) |
| privacyfriendlydicer | 5 | 41.5% | 58.5% | SeekBar |
| privacyfriendlyyahtzeedicer | 5 | 40.9% | 59.1% | - |
| hourlyreminder | 5 | 37.4% | 62.6% | SeekBar |
| offlinepuzzlesolver | 5 | 34.3% | 65.7% | SeekBar |
| salasana | 5 | 33.3% | 66.7% | - |
| verbisteandroid | 5 | 33.3% | 66.7% | - |
| minedmonero | 5 | 24.2% | 75.8% | Muitos TextViews |
| simplenotes | 5 | 23.5% | 76.5% | SeekBar (12) |
| dicewarepasswordgenerator | 5 | **18.6%** | 81.4% | **SeekBar + RadioGroup** |
| lucia | 5 | 18.2% | 81.8% | App simples |
| dnshero | 5 | 17.0% | 83.0% | Muitos elementos display |
| easyweatherdemo | 5 | 13.0% | 87.0% | Possível permissão |
| lesserpad | 5 | **0.0%** | - | **CRASH** |
| music_cyclon | 5 | **0.0%** | - | **CRASH** |

---

## 6. APKs com Baixa Cobertura - Análise

### 6.1 dicewarepasswordgenerator (18.6%) - MAIS AFETADO

- **Elementos:** 121
- **Problemas:** SeekBar (10) + RadioGroup (20) = 30 elementos não interagidos
- **Impacto:** 25% dos elementos são tipos não suportados
- **Ação:** Corrigir SeekBar e RadioGroup aumentaria cobertura significativamente

### 6.2 easyweatherdemo (13.0%)

- **Elementos:** 23 (poucos)
- **Untested:** 87%
- **Análise:** Tipos não interagidos: View (10)
- **Possível causa:** App pode requerer permissão de localização

### 6.3 dnshero (17.0%)

- **Elementos:** 127 (muitos)
- **Tipos não interagidos:** TextView (36), ImageView (17)
- **Análise:** Muitos elementos de exibição, poucos interativos

### 6.4 lucia (18.2%)

- **Elementos:** 11 (muito poucos)
- **Análise:** App muito simples com poucos elementos

---

## 7. Ratio Interação/Elemento

### Elementos Mais Interagidos (Alta Prioridade)

| Tipo | Ratio | Análise |
|------|-------|---------|
| WebView | 20.00x | Interação intensiva quando encontrado |
| ScrollView | 5.07x | Scroll funcionando bem |
| ImageButton | 3.74x | Alta prioridade correta |
| Button | 2.79x | Principal elemento interativo |
| ViewPager | 2.25x | Swipe funcionando |
| EditText | 2.12x | Faker preenchendo campos |
| Spinner | 2.07x | Dropdown funcionando |

### Elementos Menos Interagidos

| Tipo | Ratio | Análise |
|------|-------|---------|
| SeekBar | 0.00x | ❌ Não suportado |
| RadioGroup | 0.00x | ❌ Não suportado |
| Chip | 0.00x | ❌ Não reconhecido |
| View | 0.23x | ⚪ Container (esperado) |
| FrameLayout | 0.25x | ⚪ Container (esperado) |

---

## 8. Variabilidade por APK

| APK | CV (%) | Interpretação |
|-----|--------|---------------|
| dnshero | 38.8 | Alta variabilidade |
| simplenotes | 32.5 | Alta variabilidade |
| offlinepuzzlesolver | 27.0 | Alta variabilidade |
| yaab | 23.8 | Alta variabilidade |
| passera | 14.0 | Moderada |
| minedmonero | 14.0 | Moderada |
| moneytracker | 12.6 | Moderada |
| animereleasenotifier | 0.0 | Determinístico |
| easyweatherdemo | 0.0 | Determinístico |
| lucia | 0.0 | Determinístico |
| privacyfriendlydicer | 0.0 | Determinístico |
| salasana | 0.0 | Determinístico |
| verbisteandroid | 0.0 | Determinístico |

**CV = 0%** indica exploração determinística (sempre mesmo resultado).

---

## 9. Conclusões

### Pontos Positivos

| Aspecto | Valor | Status |
|---------|-------|--------|
| Taxa de sucesso | 91.7% | ✅ |
| Cobertura elementos interativos | 63.6% | ✅ |
| Button coverage | 68.5% | ✅ |
| ImageButton coverage | 90.5% | ✅ |
| Switch coverage | 91.5% | ✅ |
| Spinner coverage | 91.7% | ✅ |
| EditText coverage | 62.4% | ✅ |
| ScrollView coverage | 96.4% | ✅ |

### Problemas a Corrigir

| Problema | Impacto | Prioridade |
|----------|---------|------------|
| SeekBar não suportado | 78 elementos (7 APKs) | **ALTA** |
| RadioGroup não suportado | 24 elementos (2 APKs) | **ALTA** |
| Chip não reconhecido | 4 elementos | Média |
| APKs com crash | 2 APKs | Média |

### Métricas de Referência (Baseline)

| Métrica | Valor Atual | Meta Fase 1 |
|---------|-------------|-------------|
| UI Coverage (geral) | 37.2% | >40% |
| UI Coverage (interativos) | 63.6% | >70% |
| Elementos untested | 59.4% | <50% |
| Taxa de sucesso | 91.7% | >95% |

---

## 10. Recomendações

### Antes da Fase 1 (Prioridade Alta)

1. **Implementar suporte a SeekBar**
   - Adicionar ação SWIPE/DRAG
   - Impacto: +78 elementos testáveis

2. **Corrigir RadioGroup/RadioButton**
   - Verificar parser se reconhece RadioButton
   - Expandir filhos de RadioGroup se necessário
   - Impacto: +24 elementos testáveis

3. **Adicionar Chip como clicável**
   - Adicionar à lista de elementos sempre clicáveis
   - Impacto: +4 elementos testáveis

### Para o Experimento Principal

1. **Remover APKs com crash:** lesserpad, music_cyclon
2. **Total de APKs:** 22 (dos 24 originais)
3. **Manter timeout:** 300s
4. **Comparar com baseline:** UI Coverage > 37.2%

---

## 11. Configuração do Experimento

```json
{
    "experiment_name": "calibration_24apks",
    "apks": 24,
    "apks_valid": 22,
    "seeds": 5,
    "timeout_seconds": 300,
    "agent_mode": "pure_algorithm",
    "strategy": "rvagent",
    "static_analysis": false
}
```

---

*Relatório gerado em 2026-01-18 13:31 | Análise profunda: 2026-01-18 15:45*
