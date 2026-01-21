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

## 12. Análise Técnica: Fluxo Completo de Ações

### 12.1 Visão Geral do Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLUXO DE AÇÕES NO RV-AGENT                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. VISITOR (rv-screen-parser)                                              │
│     enhanced_visitor.py                                                     │
│     ┌─────────────────────────────────────────────┐                         │
│     │  ItemAction(                                │                         │
│     │    id=123,                                  │                         │
│     │    event=WidgetEventType.SCROLL,            │  ← Tipo de evento       │
│     │    coordinates=(540, 960),                  │  ← Ponto de click       │
│     │    target_view={                            │                         │
│     │      'class': 'SeekBar',                    │                         │
│     │      'swipe_start': (300, 960),  ← AQUI!   │  ← Não é extraído!      │
│     │      'swipe_end': (780, 960)     ← AQUI!   │                         │
│     │    }                                        │                         │
│     │  )                                          │                         │
│     └─────────────────────────────────────────────┘                         │
│                            │                                                │
│                            ▼                                                │
│  2. STRATEGY (rv-agent)                                                     │
│     rvagent_strategy.py → algorithm_node.py                                 │
│     ┌─────────────────────────────────────────────┐                         │
│     │  action = {                                 │                         │
│     │    "action_type": "SCROLL",                 │                         │
│     │    "x": 540,                                │                         │
│     │    "y": 960,                                │                         │
│     │    "source": "algorithm"                    │                         │
│     │    # NÃO TEM: swipe_start, swipe_end !!!   │  ← PROBLEMA!            │
│     │  }                                          │                         │
│     └─────────────────────────────────────────────┘                         │
│                            │                                                │
│                            ▼                                                │
│  3. EXECUTOR (rv-agent)                                                     │
│     tool_executor.py                                                        │
│     ┌─────────────────────────────────────────────┐                         │
│     │  _execute_scroll(action):                   │                         │
│     │    swipe_start = action.get("swipe_start")  │  ← None!               │
│     │    swipe_end = action.get("swipe_end")      │  ← None!               │
│     │    if swipe_start and swipe_end:            │                         │
│     │      device.swipe(...)  # Não executa       │                         │
│     │    else:                                    │                         │
│     │      device.scroll("down")  # Fallback!    │  ← Não funciona!        │
│     └─────────────────────────────────────────────┘                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Mapeamento de Tipos de Evento

| WidgetEventType | action_type | Executor Method | Comportamento |
|-----------------|-------------|-----------------|---------------|
| `CLICK` | "click" | `_execute_click()` | ✅ Funciona |
| `LONG_CLICK` | "long_click" | `_execute_long_click()` | ✅ Funciona |
| `TEXT_CHANGE` | "set_text" | `_execute_type_text()` | ✅ Funciona |
| `SCROLL` | "scroll" | `_execute_scroll()` | ⚠️ Fallback direcional |
| `DRAG` | "swipe" | `_execute_swipe()` | ❌ Usa scroll direcional! |
| `GESTURE` | "swipe" | `_execute_swipe()` | ❌ Usa scroll direcional! |
| `BACK` | "key_event" | `_execute_back()` | ✅ Funciona |

### 12.3 Problema Central: Perda de Dados no Pipeline

**O `algorithm_node.py` não extrai `swipe_start`/`swipe_end` do `target_view`!**

Código atual (linha 159-166):
```python
action = {
    "action_type": action_type,
    "x": x,
    "y": y,
    "text": text_value,
    "source": "algorithm",
    "id": item_action.id
    # FALTA: swipe_start, swipe_end, direction, etc.
}
```

### 12.4 Análise por Componente

#### CheckBox (46% coverage - BAIXO)

| Fator | Status | Impacto |
|-------|--------|---------|
| Handler existe | ✅ `visit_checkbox()` | OK |
| prioritize_check | ✅ True | OK |
| Gera ação CLICK | ✅ | OK |
| Coordenadas | ✅ | OK |

**Investigação necessária:**
- Checkboxes podem estar ocultos (scroll)
- Checkboxes podem estar em diálogos não acessados
- Estado `checked=true` pode não gerar ação de toggle em alguns visitors

#### SeekBar (0% coverage - CRÍTICO)

| Fator | Status | Impacto |
|-------|--------|---------|
| Handler existe | ✅ `visit_slider()` | OK |
| Tipo de evento | ❌ `SCROLL` | PROBLEMA |
| Coordenadas swipe | ❌ Em `target_view` | NÃO EXTRAÍDO |
| Executor | ❌ Fallback direcional | NÃO FUNCIONA |

**Correção:** Usar `DRAG` com coordenadas explícitas + extrair no algorithm_node.

#### RadioGroup (0% coverage - CRÍTICO)

| Fator | Status | Impacto |
|-------|--------|---------|
| Handler existe | ✅ `visit_radio_group()` | OK |
| Lógica | ⚠️ Condicional | PARCIAL |
| RadioButton | ❓ | VERIFICAR |

**Investigação:** O RadioButton pode não estar sendo reconhecido como clicável.

#### Chip (0% coverage)

| Fator | Status | Impacto |
|-------|--------|---------|
| Handler | ❌ Não mapeado | PROBLEMA |
| Fallback | ⚠️ `visit_leaf_node()` | PARCIAL |
| clickable | ❓ | VERIFICAR |

**Correção:** Adicionar ao `widget_handler_mapping`.

### 12.5 Confusão Semântica: SCROLL vs SWIPE vs DRAG

| Conceito | Semântica Esperada | Implementação Atual | Status |
|----------|-------------------|---------------------|--------|
| **SCROLL** | Rolagem de lista (direção) | `device.scroll(direction)` | ✅ OK |
| **SWIPE** | Gesto de deslizar (direção) | `device.scroll(direction)` | ⚠️ Redundante |
| **DRAG** | Movimento de A→B (coordenadas) | `device.scroll(direction)` | ❌ ERRADO |

**Solução proposta:**
- `SCROLL` → Rolagem de containers (direção)
- `DRAG` → Movimento preciso (coordenadas start→end)
- `SWIPE` → Alias para `SCROLL` (manter compatibilidade)

### 12.6 Correções Necessárias (Ordenadas por Impacto)

#### Correção 1: algorithm_node.py - Extrair dados de swipe

```python
# Após linha 165
# Extrair dados de swipe do target_view se disponível
if item_action.target_view:
    if "swipe_start" in item_action.target_view:
        action["swipe_start"] = item_action.target_view["swipe_start"]
    if "swipe_end" in item_action.target_view:
        action["swipe_end"] = item_action.target_view["swipe_end"]
    if "direction" in item_action.target_view:
        action["direction"] = item_action.target_view["direction"]
```

#### Correção 2: visit_slider() - Gerar coordenadas de swipe

```python
def visit_slider(self, node: Node) -> None:
    bounds = node.bounds
    if bounds and len(bounds) == 2:
        x1, y1 = bounds[0]
        x2, y2 = bounds[1]
        center_y = (y1 + y2) // 2
        width = x2 - x1

        positions = [0, 25, 50, 75, 100]
        for pos in positions:
            target_x = x1 + int(width * (pos / 100))
            start_x = (x1 + x2) // 2  # Sempre do centro

            action = ItemAction(
                id=self.counter.increment(),
                text=f"DRAG_SLIDER to {pos}%",
                event=WidgetEventType.DRAG,  # Usar DRAG, não SCROLL
                target_view={
                    **node.data,
                    'swipe_start': (start_x, center_y),
                    'swipe_end': (target_x, center_y),
                },
                coordinates=(start_x, center_y),
            )
```

#### Correção 3: tool_executor.py - Handler para DRAG

```python
elif action_type == "DRAG":
    result = self._execute_drag(action)

def _execute_drag(self, action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute coordinate-based drag action (for SeekBar, sliders, etc.)."""
    swipe_start = action.get("swipe_start")
    swipe_end = action.get("swipe_end")

    if not swipe_start or not swipe_end:
        return {"success": False, "error": "DRAG requires swipe_start and swipe_end"}

    start_x, start_y = swipe_start
    end_x, end_y = swipe_end
    self.device.swipe(start_x, start_y, end_x, end_y)
    self.logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    return {"success": True}
```

#### Correção 4: Adicionar Chip ao mapping

```python
# model.py
widget_handler_mapping = {
    ...
    "com.google.android.material.chip.Chip": "visit_button",
    "Chip": "visit_button",
}
```

### 12.7 Impacto Esperado das Correções

| Correção | Elementos | APKs Afetados | Melhoria UI Coverage |
|----------|-----------|---------------|----------------------|
| SeekBar (DRAG) | 78 | 7 | +5-10% nos APKs afetados |
| algorithm_node (extração) | Todos | Todos | Correção de base |
| RadioGroup | 24 | 2 | +5-8% em diceware... |
| Chip | 4 | 1 | +1% |
| **TOTAL** | 106+ | 10+ | **37.2% → ~45%** |

---

## 13. Arquivos Modificados

| Arquivo | Módulo | Mudança | Status |
|---------|--------|---------|--------|
| `algorithm_node.py` | rv-agent | Extrair swipe_start/swipe_end do target_view | ✅ FEITO |
| `tool_executor.py` | rv-agent | Adicionar handler para DRAG | ✅ FEITO |
| `model.py` | rv-screen-parser | Mapear DRAG → "drag" (era "swipe") | ✅ FEITO |
| `default_visitor.py` | rv-screen-parser | Usar DRAG para SeekBar com coordenadas | ✅ FEITO |
| `enhanced_visitor.py` | rv-screen-parser | Usar DRAG para SeekBar com coordenadas | ✅ FEITO |
| `model.py` | rv-screen-parser | Adicionar Chip ao widget_handler_mapping | ✅ FEITO |
| `abstract_visitor.py` | rv-screen-parser | Adicionar Chip a ALWAYS_CLICKABLE_TYPES | ✅ FEITO |

---

## 14. Correções Aplicadas (2026-01-18)

### 14.1 Resumo das Correções

| Correção | Descrição | Impacto |
|----------|-----------|---------|
| **algorithm_node.py** | Extrai `swipe_start`, `swipe_end`, `direction` do `target_view` | SeekBar, ViewPager, scroll |
| **tool_executor.py** | Novo handler `_execute_drag()` para ações com coordenadas | SeekBar funcionando |
| **model.py** | `DRAG` mapeia para "drag" (não "swipe") | Semântica clara |
| **visit_slider()** | Usa `WidgetEventType.DRAG` com coordenadas calculadas | 78 elementos SeekBar |
| **ALWAYS_CLICKABLE_TYPES** | Adicionado `Chip` e classe completa | 4 elementos Chip |
| **widget_handler_mapping** | Chip tratado como button | 4 elementos Chip |

### 14.2 Backup

Arquivos originais salvos em: `backup/20260118_action_fixes/`

### 14.3 Próximos Passos

1. **Executar testes unitários** para validar as correções
2. **Rodar mini-calibração** com 3-5 APKs afetados para verificar melhoria
3. **Comparar métricas** antes/depois

---

## 15. Validação das Correções (2026-01-18 15:00)

### 15.1 Teste Rápido: dicewarepasswordgenerator

| Métrica | Antes | Depois | Mudança |
|---------|-------|--------|---------|
| UI Coverage | 17.8% | **33.3%** | **+87%** |
| Method Coverage | 48.1% | **76.5%** | **+59%** |
| States Discovered | 8 | 5 | -37% |
| Iterations | 32 | 35 | +9% |

### 15.2 Cobertura por Componente (dicewarepasswordgenerator)

| Componente | Antes | Depois | Status |
|------------|-------|--------|--------|
| **SeekBar** | 0% | **50%** | ✅ CORRIGIDO |
| **RadioButton** | N/A | **100%** | ✅ CORRIGIDO |
| RadioGroup | 0% | 0% | ⚪ Container (esperado) |
| CheckBox | 50% | **100%** | ✅ |
| Button | 66.7% | **100%** | ✅ |
| ImageButton | 100% | **100%** | ✅ |
| ScrollView | 100% | **50%** | ⚠️ |

**Nota:** RadioGroup mostra 0% porque é um container - o importante é que os RadioButton filhos estão sendo clicados (100%).

---

## 16. Análise Completa de Componentes Android (2026-01-18 16:00)

### 16.1 Componentes Agora Suportados

#### Standard Android Widgets (android.widget.*)

| Componente | Handler | Status |
|------------|---------|--------|
| Button | `visit_button` | ✅ |
| EditText | `visit_edit_text` | ✅ |
| TextView | `visit_text_view` | ✅ |
| CheckBox | `visit_checkbox` | ✅ |
| CheckedTextView | `visit_checked_text` | ✅ |
| ImageButton | `visit_image_button` | ✅ |
| ImageView | `visit_image` | ✅ |
| ToggleButton | `visit_toggle_button` | ✅ |
| Switch | `visit_switch` | ✅ |
| RadioButton | `visit_radio_button` | ✅ |
| RadioGroup | `visit_radio_group` | ✅ CORRIGIDO |
| SeekBar | `visit_slider` | ✅ CORRIGIDO |
| **RatingBar** | `visit_slider` | ✅ NOVO |
| **AutoCompleteTextView** | `visit_edit_text` | ✅ NOVO |
| **MultiAutoCompleteTextView** | `visit_edit_text` | ✅ NOVO |
| Spinner | `visit_spinner` | ✅ |

#### AndroidX AppCompat Widgets (androidx.appcompat.widget.*)

| Componente | Handler | Status |
|------------|---------|--------|
| AppCompatButton | `visit_button` | ✅ NOVO |
| AppCompatEditText | `visit_edit_text` | ✅ NOVO |
| AppCompatTextView | `visit_text_view` | ✅ NOVO |
| AppCompatCheckBox | `visit_checkbox` | ✅ NOVO |
| AppCompatImageButton | `visit_image_button` | ✅ NOVO |
| AppCompatImageView | `visit_image` | ✅ NOVO |
| AppCompatRadioButton | `visit_radio_button` | ✅ NOVO |
| AppCompatSeekBar | `visit_slider` | ✅ NOVO |
| SwitchCompat | `visit_switch` | ✅ NOVO |
| AppCompatToggleButton | `visit_toggle_button` | ✅ NOVO |
| AppCompatCheckedTextView | `visit_checked_text` | ✅ NOVO |
| AppCompatSpinner | `visit_spinner` | ✅ NOVO |

#### Material Design Components (com.google.android.material.*)

| Componente | Handler | Status |
|------------|---------|--------|
| Chip | `visit_button` | ✅ CORRIGIDO |
| ChipGroup | container (children) | ✅ NOVO |
| MaterialButton | `visit_button` | ✅ NOVO |
| TextInputEditText | `visit_edit_text` | ✅ NOVO |
| SwitchMaterial | `visit_switch` | ✅ NOVO |
| MaterialCheckBox | `visit_checkbox` | ✅ NOVO |
| MaterialRadioButton | `visit_radio_button` | ✅ NOVO |
| Slider | `visit_slider` | ✅ NOVO |
| RangeSlider | `visit_slider` | ✅ NOVO |
| FloatingActionButton | `visit_button` | ✅ NOVO |
| ExtendedFloatingActionButton | `visit_button` | ✅ NOVO |

### 16.2 Elementos Sempre Clicáveis (ALWAYS_CLICKABLE_TYPES)

| Categoria | Componentes |
|-----------|-------------|
| **Tabs** | ActionBar$Tab, Tab, TabLayout, TabView |
| **Navigation** | NavigationBarView, BottomNavigationItemView, NavigationRailView |
| **Menus** | ActionMenuItemView, MenuItemView, OverflowMenuButton |
| **Material Design** | Chip, TabItem, TabLayout$TabView, BottomNavigationItemView, NavigationBarItemView, FloatingActionButton |
| **AndroidX** | ActionMenuView, ActionMenuItemView |

### 16.3 Containers com Tratamento Especial

| Container | Comportamento |
|-----------|---------------|
| Spinner | `visit_spinner()` - trata como dropdown |
| AppCompatSpinner | `visit_spinner()` - trata como dropdown |
| RadioGroup | `visit_radio_group()` - itera filhos RadioButton |
| ChipGroup | Itera filhos Chip individualmente |

---

## 17. Resumo das Correções Completas

### 17.1 Arquivos Modificados

| Arquivo | Módulo | Mudanças |
|---------|--------|----------|
| `algorithm_node.py` | rv-agent | Extrai swipe_start/swipe_end/direction do target_view |
| `tool_executor.py` | rv-agent | Novo handler `_execute_drag()` |
| `model.py` | rv-screen-parser | +25 mapeamentos de widgets (AndroidX, Material) |
| `model.py` | rv-screen-parser | DRAG → "drag", ChipGroup como container |
| `default_visitor.py` | rv-screen-parser | `visit_radio_group()` com coordenadas |
| `enhanced_visitor.py` | rv-screen-parser | `visit_radio_group()` com coordenadas |
| `abstract_visitor.py` | rv-screen-parser | +13 elementos em ALWAYS_CLICKABLE_TYPES |

### 17.2 Impacto Estimado

| Correção | Componentes | Impacto |
|----------|-------------|---------|
| SeekBar (DRAG) | 78 | +10% UI Coverage em 7 APKs |
| RadioGroup (coordenadas) | 24 | +8% UI Coverage em 2 APKs |
| Chip | 4+ | +1% |
| AndroidX/Material mappings | Variável | Suporte a apps modernos |
| ALWAYS_CLICKABLE_TYPES | Variável | Melhor navegação em tabs/menus |

### 17.3 Próximos Passos

1. ✅ Correções implementadas
2. ✅ Teste rápido validou correções (dicewarepasswordgenerator)
3. ⏳ Executar mini-calibração com 5-10 APKs para validação estatística
4. ⏳ Comparar métricas com baseline (37.2% → esperado >45%)
5. ⏳ Atualizar documentação de componentes suportados

---

## 18. Correções Adicionais (2026-01-18 18:00)

### 18.1 Stuck Detection Dinâmico

**Problema Identificado**: Threshold fixo de 8 iterações causava BACK prematuro em telas complexas.

**Arquivos Modificados**:
- `rv_agent.py` - Novos parâmetros configuráveis
- `learn_node.py` - Lógica de threshold dinâmico

**Implementação**:
```python
# rv_agent.py
self.BASE_STUCK_THRESHOLD = 8      # Mínimo para telas simples
self.STUCK_THRESHOLD_FACTOR = 1.5  # Multiplicador (calibrável)

# learn_node.py
def _get_dynamic_stuck_threshold(agent, state) -> int:
    base = getattr(agent, 'BASE_STUCK_THRESHOLD', 8)
    factor = getattr(agent, 'STUCK_THRESHOLD_FACTOR', 1.5)
    num_elements = len(state.get("available_actions", []))
    return max(base, int(num_elements * factor))
```

**Tabela de Impacto**:

| Elementos | Factor=1.5 | Factor=2.0 |
|-----------|------------|------------|
| 5 | 8 (min) | 10 |
| 10 | 15 | 20 |
| 20 | 30 | 40 |
| 30 | 45 | 60 |

### 18.2 ComponentPriorityScorer Expandido

**Problema Identificado**: Apenas 11 componentes tinham prioridade configurada. Tabs e muitos componentes AndroidX/Material não tinham prioridade.

**Arquivo Modificado**: `scorers.py`

**HIGH_PRIORITY (50.0) - 19 componentes**:

| Categoria | Componentes |
|-----------|-------------|
| Buttons | Button, ImageButton, MaterialButton, FloatingActionButton, ExtendedFloatingActionButton |
| Form Inputs | EditText, AutoCompleteTextView, MultiAutoCompleteTextView, TextInputEditText |
| Dropdowns | Spinner, AppCompatSpinner |
| Navigation | DrawerLayout, Tab, TabLayout, TabView, ActionBar$Tab, TabItem |
| Bottom/Side Nav | BottomNavigationItemView, NavigationBarItemView, NavigationBarView, NavigationRailView |
| Menus | ActionMenuItemView, MenuItemView, OverflowMenuButton |
| Chips | Chip |

**MEDIUM_PRIORITY (40.0) - 16 componentes**:

| Categoria | Componentes |
|-----------|-------------|
| Toggles | CheckBox, MaterialCheckBox, AppCompatCheckBox, Switch, SwitchCompat, SwitchMaterial, ToggleButton, AppCompatToggleButton |
| Radio | RadioButton, MaterialRadioButton, AppCompatRadioButton |
| Sliders | SeekBar, AppCompatSeekBar, Slider, RangeSlider, RatingBar |
| Content | ViewPager, RecyclerView, CheckedTextView, AppCompatCheckedTextView |

**Total**: 35 componentes com prioridade (antes eram 11)

### 18.3 Resumo das Correções da Sessão

| # | Correção | Arquivo | Impacto |
|---|----------|---------|---------|
| 1 | Stuck Detection Dinâmico | rv_agent.py, learn_node.py | Menos BACK prematuro |
| 2 | Tabs com alta prioridade | scorers.py | Melhor exploração de abas |
| 3 | 35 componentes priorizados | scorers.py | Cobertura de AndroidX/Material |

### 18.4 GradualDecayScorer (Substitui UntestedScorer)

**Problema Identificado**: O sistema binário do UntestedScorer causava "cliff effect" - elementos perdiam 79% do score após a primeira visita (260 → 55), levando a abandono prematuro de elementos parcialmente testados.

**Arquivo Modificado**: `scorers.py`

**Antes (UntestedScorer - REMOVIDO)**:
```python
class UntestedScorer(Scorer):
    UNTESTED_SCORE = 200.0

    def score(self, action, context):
        if is_untested:
            return 200.0  # Binário: 200 ou 0
        return 0.0
```

**Depois (GradualDecayScorer)**:
```python
class GradualDecayScorer(Scorer):
    BASE_SCORE = 200.0
    DECAY_RATE = 0.7  # 70% retention per visit
    MIN_VISITS_FOR_ZERO = 5

    def score(self, action, context):
        visit_count = context.ui_coverage.get_element_test_count(element_id)
        if visit_count >= MIN_VISITS_FOR_ZERO:
            return 0.0
        return BASE_SCORE * (DECAY_RATE ** visit_count)
```

**Tabela de Decay (DECAY_RATE=0.7)**:

| Visitas | Score | % do Original | Comportamento |
|---------|-------|---------------|---------------|
| 0 | 200.0 | 100% | Nunca testado - máxima prioridade |
| 1 | 140.0 | 70% | Testado 1x - ainda alta prioridade |
| 2 | 98.0 | 49% | Testado 2x - prioridade moderada |
| 3 | 68.6 | 34% | Testado 3x - prioridade menor |
| 4 | 48.0 | 24% | Testado 4x - baixa prioridade |
| 5+ | 0.0 | 0% | Bem testado - sem bonus |

**Benefícios**:
1. Transição suave de prioridade em vez de queda abrupta
2. Elementos são revisitados mais vezes antes de serem "abandonados"
3. Melhor cobertura em elementos que requerem múltiplas interações
4. DECAY_RATE configurável para ajuste fino

### 18.5 Remoção de Código Legado

**Aliases removidos** (seguindo regras de implementação):
- `UntestedScorer = GradualDecayScorer` - REMOVIDO
- `DropdownScorer = ComponentPriorityScorer` - REMOVIDO

**Arquivos atualizados**:
- `scorers.py` - Classe GradualDecayScorer, aliases removidos
- `__init__.py` - Exporta GradualDecayScorer
- `rvagent_strategy.py` - Usa GradualDecayScorer diretamente

### 18.6 Experimento de Validação

**Status**: Em execução (mini_calibration_fixes)
- APKs: 5
- Seeds: 2 (42, 123)
- Timeout: 300s
- Total: 10 runs

**Nota**: Este experimento usa código ANTES das correções desta sessão. As novas correções (Seções 18.1-18.5) serão validadas no próximo experimento.

### 18.7 Resumo de Todas as Correções da Sessão

| # | Correção | Arquivo | Impacto |
|---|----------|---------|---------|
| 1 | Stuck Detection Dinâmico | rv_agent.py, learn_node.py | Menos BACK prematuro |
| 2 | Tabs com alta prioridade | scorers.py | Melhor exploração de abas |
| 3 | 35 componentes priorizados | scorers.py | Cobertura de AndroidX/Material |
| 4 | **GradualDecayScorer** | scorers.py | Transição suave de prioridade |
| 5 | Remoção de código legado | scorers.py, __init__.py | Código limpo |

---

*Relatório gerado em 2026-01-18 13:31 | Análise profunda: 2026-01-18 15:45 | Análise código: 2026-01-18 16:30 | Correções aplicadas: 2026-01-18 14:30 | Análise completa de componentes: 2026-01-18 17:00 | Correções adicionais: 2026-01-18 18:00 | GradualDecayScorer: 2026-01-18 19:00*
