# Resultados da Fase 1: Static Impact + Investigacao WTG

**Data:** 2026-01-20
**Experimento:** phase1_static_impact
**Status:** CONCLUIDO (360 runs) + CORRECOES WTG APLICADAS

---

## 1. Resumo Executivo

### 1.1 Experimento phase1_static_impact

| Metrica | Valor |
|---------|-------|
| Total de runs | 360 |
| Runs completados | 360 (100%) |
| Runs com falha | 0 |
| Estrategias testadas | 4 (rvagent, dfs, bfs, greedy) |
| Variantes Static Analysis | 2 (SA, NoSA) |
| APKs testados | 15 |
| Repeticoes por config | 3 |
| Timeout por run | 180s |
| Tempo total | ~19h |

### 1.2 Descoberta Critica

**O WTG (Window Transition Graph) NAO estava funcionando durante este experimento.**

A diferenca entre runs COM e SEM analise estatica foi **praticamente nula (~0.5%)**, indicando que MopScorer e WtgScorer nao estavam contribuindo para a priorizacao.

---

## 2. Resultados: Com vs Sem Analise Estatica

### 2.1 Metricas por Configuracao

| Config | Method Cov | Activity Cov | UI Cov | States | Actions | MOP Cov | Runs |
|--------|------------|--------------|--------|--------|---------|---------|------|
| rvagent_SA | 52.8% | 64.1% | 34.9% | 9.0 | 59.1 | 0.0% | 45 |
| rvagent_NoSA | 53.0% | 63.8% | 38.4% | 8.7 | 58.2 | 0.0% | 45 |
| dfs_SA | 48.7% | 62.7% | 30.3% | 6.4 | 77.3 | 0.0% | 45 |
| dfs_NoSA | 48.4% | 62.2% | 34.2% | 6.2 | 78.6 | 0.0% | 45 |
| bfs_SA | 48.5% | 62.2% | 30.4% | 6.2 | 77.3 | 0.0% | 45 |
| bfs_NoSA | 48.7% | 62.7% | 33.9% | 6.4 | 76.2 | 0.0% | 45 |
| greedy_SA | 49.8% | 63.1% | 30.4% | 7.3 | 75.4 | 0.0% | 45 |
| greedy_NoSA | 49.7% | 63.1% | 34.5% | 7.2 | 75.2 | 0.0% | 45 |

### 2.2 Comparacao: SA vs NoSA (Method Coverage)

| Estrategia | SA | NoSA | Delta | Delta% |
|------------|-----|------|-------|--------|
| rvagent | 52.8% | 53.0% | -0.3% | -0.5% |
| dfs | 48.7% | 48.4% | +0.3% | +0.7% |
| bfs | 48.5% | 48.7% | -0.2% | -0.4% |
| greedy | 49.8% | 49.7% | +0.1% | +0.2% |

**Conclusao:** Diferenca praticamente nula confirma que WTG nao estava funcionando.

### 2.3 Observacao sobre UI Coverage

**UI Coverage foi MENOR com SA ativado** (media ~31% vs ~35% sem SA).

Isso eh contra-intuitivo e pode indicar que o codigo de inicializacao do WTG estava causando algum overhead ou interferencia, mesmo sem funcionar corretamente.

---

## 3. Distribuicao de Acoes por Tipo de Elemento

### 3.1 Todos os Tipos (ordenados por cobertura)

| Tipo | Total | Testados | Cobertura | Interacoes |
|------|-------|----------|-----------|------------|
| GridView | 24 | 0 | 0.0% | 0 |
| RadioGroup | 13 | 0 | 0.0% | 0 |
| RelativeLayout | 24 | 0 | 0.0% | 0 |
| CheckBox | 990 | 144 | 14.5% | 640 |
| View | 319 | 51 | 16.0% | 132 |
| EditText | 1538 | 276 | 17.9% | 740 |
| TextView | 11822 | 2336 | 19.8% | 4549 |
| FrameLayout | 423 | 105 | 24.8% | 155 |
| Switch | 494 | 136 | 27.5% | 194 |
| SystemAction_BACK | 360 | 104 | 28.9% | 227 |
| LinearLayout | 2833 | 835 | 29.5% | 1296 |
| CheckedTextView | 704 | 216 | 30.7% | 234 |
| ImageView | 2968 | 956 | 32.2% | 2075 |
| TableLayout | 24 | 10 | 41.7% | 10 |
| LinearLayoutCompat | 294 | 147 | 50.0% | 193 |
| ScrollView | 82 | 41 | 50.0% | 41 |
| ImageButton | 848 | 489 | 57.7% | 2019 |
| Button | 2021 | 1238 | 61.3% | 5120 |
| RecyclerView | 81 | 53 | 65.4% | 140 |
| ActionBar$Tab | 172 | 118 | 68.6% | 302 |
| Spinner | 193 | 143 | 74.1% | 603 |
| ToggleButton | 8 | 6 | 75.0% | 6 |
| WebView | 11 | 9 | 81.8% | 21 |
| SeekBar | 180 | 166 | 92.2% | 723 |
| ViewPager | 234 | 217 | 92.7% | 1048 |
| scrollable | 95 | 95 | 100.0% | 108 |
| RadioButton | 21 | 21 | 100.0% | 21 |

### 3.2 Tipos com Baixa Cobertura (< 20%)

| Tipo | Cobertura | Testados/Total | Interacoes | Verificar Scorer? |
|------|-----------|----------------|------------|-------------------|
| GridView | 0.0% | 0/24 | 0 | NAO (nao clicavel) |
| RadioGroup | 0.0% | 0/13 | 0 | NAO (container) |
| RelativeLayout | 0.0% | 0/24 | 0 | NAO (container) |
| **CheckBox** | 14.5% | 144/990 | 640 | **SIM** (MEDIUM 40.0) |
| View | 16.0% | 51/319 | 132 | NAO (generico) |
| **EditText** | 17.9% | 276/1538 | 740 | **SIM** (HIGH 50.0) |
| TextView | 19.8% | 2336/11822 | 4549 | NAO (maioria labels) |

### 3.3 Analise dos Scorers

**CheckBox (14.5% cobertura):**
- Score atual: MEDIUM_PRIORITY = 40.0
- Interacoes: 640 (significativo)
- **Acao:** Considerar aumentar para HIGH_PRIORITY

**EditText (17.9% cobertura):**
- Score atual: HIGH_PRIORITY = 50.0
- Interacoes: 740 (significativo)
- **Acao:** Score ja eh alto, problema pode ser outro (e.g., falta de texto para digitar)

---

## 4. Investigacao e Correcoes WTG

### 4.1 Problemas Identificados

| # | Problema | Arquivo | Impacto |
|---|----------|---------|---------|
| 1 | `get_window()` fazia busca exata por nome | `rv-android-core/domain/window.py` | Window nunca encontrado |
| 2 | Set nao suporta slicing (`windows[:5]`) | `rv-screen-parser/visitor/abstract_visitor.py` | Excecao silenciosa |
| 3 | `_find_action_by_widget_id` nao encontrava acoes | `rv-agent/services/transition_manager.py` | WTG match sempre falhava |

### 4.2 Root Cause Analysis

**Problema 1: Nome de activity relativo vs absoluto**

```
Runtime: '.tutorial.TutorialActivity' (relativo)
WTG:     'com.reddyetwo.hashmypass.app.tutorial.TutorialActivity' (absoluto)
```

O metodo `get_window()` fazia busca exata e nunca encontrava.

**Problema 2: Set vs List**

```python
# ANTES (erro - set nao suporta slicing)
available = [w.name for w in static_info.windows.windows[:5]]

# Log de erro capturado:
# [WTG_DEBUG] Exception in window lookup: 'set' object is not subscriptable
```

**Problema 3: widget_id nao era setado nas acoes**

O `_find_action_by_widget_id` nao encontrava match porque as acoes nao tinham `widget_id` setado durante o parsing.

### 4.3 Correcoes Aplicadas

**Correcao 1: `get_window()` com matching parcial**

```python
def get_window(self, window_name: str) -> Optional[Window]:
    # Strategy 1: Exact match
    result = next((w for w in self.windows if w.name == window_name), None)
    if result:
        return result

    # Strategy 2: Relative name match (e.g., ".TutorialActivity")
    if window_name.startswith('.'):
        result = next((w for w in self.windows if w.name.endswith(window_name)), None)
        if result:
            return result

    # Strategy 3: Match by activity class name (last part)
    class_name = window_name.split('.')[-1] if '.' in window_name else window_name
    if class_name:
        result = next((w for w in self.windows if w.name.endswith(class_name)), None)
        if result:
            return result

    return None
```

**Correcao 2: Set to list conversion**

```python
available = [w.name for w in list(static_info.windows.windows)[:5]]
```

**Correcao 3: Matching via `events_by_id`**

Usando abordagem do rvsmart para encontrar acoes pelo widget_id.

### 4.4 Validacao das Correcoes

**Logs ANTES:**
```
[WTG_DEBUG] Window NOT found for activity '.tutorial.TutorialActivity'
[WTG_DEBUG] WTG match NOT found: widget_id=2131755143, widget_name=next_button
```

**Logs DEPOIS:**
```
[WTG_DEBUG] Window found: id=860, name=com.reddyetwo.hashmypass.app.tutorial.TutorialActivity
[WTG_DEBUG] WTG match found via events_by_id: widget_id=2131755143, action_id=6
```

---

## 5. Comparacao com Experimento Anterior (phase1_algorithms)

### 5.1 Experimento phase1_algorithms (18-19/01)

Este experimento anterior (180 runs) **nao tinha variantes de static analysis** - todos runs eram efetivamente sem SA funcionando.

| Estrategia | phase1_algorithms | phase1_static_impact (NoSA) |
|------------|-------------------|------------------------------|
| rvagent | 54.6% | 53.0% |
| dfs | 49.3% | 48.4% |
| bfs | 49.2% | 48.7% |
| greedy | 49.9% | 49.7% |

**Conclusao:** Resultados consistentes entre os dois experimentos.

---

## 6. Observacoes sobre MOP Coverage

**MOP coverage = 0% em todos os runs.**

Isso ocorre porque os arquivos `.methods` nao contem dados de MOP (total_reaches_mop = 0, total_directly_reaches_mop = 0).

**Acao necessaria:** Regenerar arquivos .methods com dados de MOP para que MopScorer funcione.

---

## 7. Proximos Passos

### 7.1 Imediatos

1. [ ] Regenerar arquivos .methods com dados MOP
2. [ ] Re-executar Fase 1 com WTG corrigido
3. [ ] Comparar resultados antes/depois das correcoes

### 7.2 Scorers a Verificar

1. **CheckBox:** Aumentar de MEDIUM (40.0) para HIGH (50.0)?
2. **EditText:** Investigar por que cobertura eh baixa apesar de score alto

### 7.3 Remover Logs de Debug

Apos validacao completa, remover todos os logs com prefixo `[WTG_DEBUG]` de:
- `rv-screen-parser/visitor/abstract_visitor.py`
- `rv-agent/services/transition_manager.py`
- `rv-agent/strategies/rvagent_strategy/ranking/scorers.py`

---

## 8. Arquivos Modificados

| Arquivo | Tipo | Status |
|---------|------|--------|
| `rv-android-core/domain/window.py` | FIX | Aplicado |
| `rv-screen-parser/visitor/abstract_visitor.py` | FIX + DEBUG | Aplicado |
| `rv-agent/services/transition_manager.py` | FIX + DEBUG | Aplicado |
| `rv-agent/strategies/rvagent_strategy/ranking/scorers.py` | DEBUG | Aplicado |

---

*Documento gerado em 2026-01-20*
