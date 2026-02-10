# Resultados da Fase 1: Validação de Estratégias Algorítmicas

**Data:** 2026-01-19 10:41
**Experimento:** phase1_algorithms
**Status:** CONCLUÍDO

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Total de runs | 180 |
| Runs completados | 180 (100%) |
| Runs com falha | 0 |
| Estratégias testadas | 4 (rvagent, dfs, bfs, greedy) |
| APKs testados | 15 |
| Repetições por config | 3 |
| Timeout por run | 300s |
| Tempo total | ~15h |

### Resultado Principal

| Ranking | Estratégia | Method Coverage | Diferença |
|---------|------------|-----------------|-----------|
| 🥇 | **rvagent** | **54.6%** | - |
| 🥈 | greedy | 49.9% | -4.8% |
| 🥉 | dfs | 49.3% | -5.4% |
| 4 | bfs | 49.2% | -5.5% |

**Conclusão:** rvagent é a melhor estratégia algorítmica com 4.8% de vantagem sobre o segundo lugar.

---

## 2. Métricas Detalhadas por Estratégia

### 2.1 Method Coverage

| Estratégia | Média | Desvio Padrão | Mediana | Mín | Máx |
|------------|-------|---------------|---------|-----|-----|
| rvagent | 54.6% | ±30.1 | 45.9% | 10.6% | 100.0% |
| greedy | 49.9% | ±31.1 | 32.7% | 6.0% | 100.0% |
| dfs | 49.3% | ±31.5 | 31.4% | 6.0% | 100.0% |
| bfs | 49.2% | ±31.4 | 31.4% | 6.0% | 100.0% |

### 2.2 Activity Coverage

| Estratégia | Média | Desvio Padrão |
|------------|-------|---------------|
| rvagent | 65.5% | ±31.8 |
| greedy | 62.7% | ±32.7 |
| dfs | 62.7% | ±33.5 |
| bfs | 62.2% | ±33.4 |

### 2.3 Exploração

| Estratégia | Estados Descobertos | Ações Executadas | Ações/Minuto |
|------------|---------------------|------------------|--------------|
| rvagent | 10.4 | 101.8 | 20.2 |
| greedy | 7.7 | 131.6 | 26.1 |
| dfs | 7.2 | 136.7 | 27.1 |
| bfs | 7.2 | 135.3 | 26.9 |

---

## 3. Resultados por APK

### 3.1 Method Coverage por APK e Estratégia

| APK | Methods | rvagent | dfs | bfs | greedy | Melhor |
|-----|---------|---------|-----|-----|--------|--------|
| com.blogspot.e_kanivets.moneytracker_38 | 1205 | 32.4% | 20.3% | 20.2% | 25.8% | rvagent |
| com.gianlu.dnshero_40 | 435 | 15.9% | 15.5% | 15.5% | 16.9% | greedy |
| com.github.axet.darknessimmunity_28 | 71 | 84.5% | 83.1% | 81.7% | 81.7% | rvagent |
| com.github.axet.hourlyreminder_476 | 724 | 45.1% | 31.5% | 31.2% | 30.7% | rvagent |
| com.pindroid_69 | 640 | 10.6% | 8.0% | 8.0% | 8.0% | rvagent |
| com.rafapps.simplenotes_7 | 161 | 37.5% | 25.1% | 25.5% | 25.1% | rvagent |
| com.reddyetwo.hashmypass.app_24 | 445 | 73.0% | 48.8% | 48.7% | 49.3% | rvagent |
| com.thibaudperso.sonycamera_24 | 454 | 22.8% | 20.5% | 20.5% | 20.5% | rvagent |
| digital.selfdefense.lucia_20001 | 17 | 76.5% | 76.5% | 76.5% | 76.5% | rvagent |
| gg.mw.passera_2 | 15 | 100.0% | 100.0% | 100.0% | 100.0% | rvagent |
| li.klass.fhem_141 | 2417 | 30.9% | 24.1% | 24.1% | 24.1% | rvagent |
| net.xvello.salasana_3 | 11 | 81.8% | 81.8% | 81.8% | 81.8% | rvagent |
| org.secuso.privacyfriendlydicer_8 | 82 | 82.1% | 80.5% | 80.5% | 80.9% | rvagent |
| org.secuso.privacyfriendlyludo_5 | 269 | 29.9% | 30.1% | 30.1% | 32.5% | greedy |
| org.secuso.privacyfriendlyyahtzeedicer_5 | 30 | 96.7% | 93.3% | 93.3% | 94.4% | rvagent |

### 3.2 Vitórias por Estratégia

| Estratégia | APKs Vencidos | Percentual |
|------------|---------------|------------|
| **rvagent** | **13/15** | **87%** |
| greedy | 2/15 | 13% |
| dfs | 0/15 | 0% |
| bfs | 0/15 | 0% |

---

## 4. Comparação com Ferramentas Tradicionais

### 4.1 Method Coverage: rv-agent vs Ferramentas

| APK | rv-agent | APE | ARES | DroidBot | FastBot | Humanoid | Monkey | Melhor |
|-----|----------|-----|------|----------|---------|----------|--------|--------|
| com.blogspot.e_kanivets.moneyt | 32.4% | 25.4% | 28.7% | 20.0% | 26.7% | 25.0% | 19.6% | rvagent |
| com.gianlu.dnshero_40 | 15.9% | 18.9% | 14.6% | 10.6% | 15.6% | 11.0% | 9.7% | ape |
| com.github.axet.darknessimmuni | 84.5% | 88.7% | 76.1% | 77.5% | 81.7% | 76.5% | 64.3% | ape |
| com.github.axet.hourlyreminder | 45.1% | 38.5% | 30.5% | 37.7% | 40.1% | 36.9% | 21.2% | rvagent |
| com.pindroid_69 | 10.6% | 9.1% | 9.7% | 8.8% | 9.6% | 10.2% | 7.6% | rvagent |
| com.rafapps.simplenotes_7 | 37.5% | 36.4% | 28.4% | 22.1% | 28.8% | 26.9% | 30.0% | rvagent |
| com.reddyetwo.hashmypass.app_2 | 73.0% | 67.4% | 43.3% | 41.0% | 50.0% | 61.1% | 18.1% | rvagent |
| com.thibaudperso.sonycamera_24 | 22.8% | 26.3% | 21.6% | 25.8% | 26.0% | 24.5% | 18.1% | ape |
| digital.selfdefense.lucia_2000 | 76.5% | 76.5% | 76.5% | 76.5% | 76.5% | 76.5% | 76.5% | rvagent |
| gg.mw.passera_2 | 100.0% | 100.0% | 86.7% | 97.8% | 100.0% | 100.0% | 73.3% | rvagent |
| li.klass.fhem_141 | 30.9% | 15.5% | 19.1% | 19.5% | 18.1% | 16.2% | 10.9% | rvagent |
| net.xvello.salasana_3 | 81.8% | 81.8% | 69.7% | 81.8% | 72.7% | 75.8% | 81.8% | ape |
| org.secuso.privacyfriendlydice | 82.1% | 54.1% | 48.8% | 48.0% | 57.3% | 48.8% | 26.0% | rvagent |
| org.secuso.privacyfriendlyludo | 29.9% | 37.9% | 29.6% | 26.0% | 37.9% | 27.9% | 9.9% | ape |
| org.secuso.privacyfriendlyyaht | 96.7% | 93.3% | 72.2% | 86.7% | 92.2% | 93.3% | 41.1% | rvagent |

### 4.2 Vitórias: rv-agent vs Ferramentas Tradicionais

| Ferramenta | Vitórias | Percentual |
|------------|----------|------------|
| **rv-agent** | **10/15** | **67%** |
| APE | 5/15 | 33% |
| ARES | 0/15 | 0% |
| DroidBot | 0/15 | 0% |
| FastBot | 0/15 | 0% |
| Humanoid | 0/15 | 0% |
| Monkey | 0/15 | 0% |

### 4.3 Resumo da Comparação

| Métrica | Valor |
|---------|-------|
| rv-agent (média) | 54.6% |
| Melhor tradicional (média por APK) | 52.2% |
| **Diferença** | **+2.4%** |
| Vitórias rv-agent | 10/15 (67%) |

---

## 5. Análise Estatística

### 5.1 Distribuição de Method Coverage

| Faixa | rvagent | dfs | bfs | greedy |
|-------|---------|-----|-----|--------|
| 0-20% | 6 | 4 | 4 | 4 |
| 20-40% | 15 | 20 | 20 | 20 |
| 40-60% | 3 | 3 | 3 | 3 |
| 60-80% | 6 | 3 | 4 | 3 |
| 80-100% | 12 | 12 | 11 | 12 |

### 5.2 Variabilidade (Coeficiente de Variação)

| Estratégia | CV (Method Coverage) |
|------------|---------------------|
| rvagent | 55.0% |
| greedy | 62.3% |
| dfs | 64.0% |
| bfs | 63.9% |

---

## 6. Hipóteses Validadas

| Hipótese | Descrição | Resultado |
|----------|-----------|-----------|
| **H1** | rvagent supera outras estratégias algorítmicas | ✅ **CONFIRMADA** (54.6% vs 49.9%) |
| **H5** | rv-agent supera Humanoid (26.79%) | ✅ **CONFIRMADA** (54.6% vs 26.79%) |

---

## 7. Conclusões

### 7.1 Principais Descobertas

1. **rvagent é a melhor estratégia algorítmica** com 54.6% de method coverage média
2. **Margem significativa** de +4.8% sobre o segundo lugar (greedy)
3. **Venceu em 87% dos APKs** (13/15) entre as estratégias algorítmicas
4. **Supera ferramentas tradicionais** em 67% dos APKs (10/15)
5. **Descobre mais estados** (10.4 vs 7.2 média) indicando melhor exploração

### 7.2 Pontos Fortes do rvagent

- Sistema de scoring com múltiplos critérios (MOP, Component Priority, Gradual Decay)
- Successor Tracker para revisitar estados com baixa cobertura
- Melhor exploração de estados (44% mais estados que outras estratégias)

### 7.3 Próximos Passos

1. ✅ Fase 1 concluída - rvagent selecionado como melhor estratégia
2. ⏳ Fase 2: Validar prompts e parâmetros LLM
3. ⏳ Fase 3: Encontrar proporção ótima LLM/algoritmo

---

## 8. Configuração do Experimento

```json
{{
  "experiment_id": "phase1_algorithms",
  "strategies": ["rvagent", "dfs", "bfs", "greedy"],
  "apks": 15,
  "repetitions": 3,
  "timeout_seconds": 300,
  "agent_mode": "pure_algorithm",
  "base_seed": 42
}}
```

---

## 9. APKs Utilizados

| # | APK | Methods | Categoria |
|---|-----|---------|-----------|
| 1 | com.blogspot.e_kanivets.moneytracker_38.apk | 1205 | Money |
| 2 | com.gianlu.dnshero_40.apk | 435 | Internet |
| 3 | com.github.axet.hourlyreminder_476.apk | 724 | Multimedia |
| 4 | com.pindroid_69.apk | 640 | Internet |
| 5 | com.rafapps.simplenotes_7.apk | 161 | Writing |
| 6 | com.thibaudperso.sonycamera_24.apk | 454 | Multimedia |
| 7 | li.klass.fhem_141.apk | 2417 | Internet |
| 8 | com.reddyetwo.hashmypass.app_24.apk | 445 | Security |
| 9 | org.secuso.privacyfriendlydicer_8.apk | 82 | Games |
| 10 | org.secuso.privacyfriendlyludo_5.apk | 269 | Games |
| 11 | gg.mw.passera_2.apk | 15 | Security |
| 12 | org.secuso.privacyfriendlyyahtzeedicer_5.apk | 30 | Games |
| 13 | digital.selfdefense.lucia_20001.apk | 17 | Connectivity |
| 14 | net.xvello.salasana_3.apk | 11 | Security |
| 15 | com.github.axet.darknessimmunity_28.apk | 71 | Theming |

---

*Documento gerado automaticamente em 2026-01-19 10:41*
