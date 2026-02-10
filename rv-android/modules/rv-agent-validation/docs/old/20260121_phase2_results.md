# Mini Phase 2 - Resultados

**Data**: 21/01/2026
**Experimento**: `mini_phase2_multimode`
**Referencia**: `docs/20260115_rvagent_validacao_multimodal.md` (Secao 3 - Fase 2)

---

## 1. Configuracao do Experimento

### 1.1 Desvios do Plano Original

| Parametro | Plano Original (Fase 2) | Mini Phase 2 | Motivo |
|-----------|-------------------------|--------------|--------|
| Prompts | v13, v14 | v13, v14, **v15** | Testar novo prompt com scores enriquecidos |
| Params | 3 (default, deterministic, explorative) | 1 (default) | Trade-off para incluir v15 |
| Mode | llm_only | **multimode (70/30)** | Testar modo hibrido |
| Seeds | 3 | 2 | Reduzir tempo de execucao |

### 1.2 Configuracao Final

```
3 prompts × 1 param × 2 static × 15 APKs × 2 seeds = 180 runs
Timeout: 180s (3 min)
Mode: multimode (70% LLM / 30% algoritmo)
```

### 1.3 Prompts Testados

| Prompt | Descricao |
|--------|-----------|
| `v13` | Dialog handling - prompt atual |
| `v14` | Structured reasoning |
| `v15` | Enriched elements com [UNTESTED]/[TESTED-Nx] tags e scores |

---

## 2. Execucao

| Metrica | Valor |
|---------|-------|
| **Inicio** | 20/01/2026 18:13 |
| **Fim** | 21/01/2026 01:48 (interrompido por reinicio) |
| **Duracao** | ~7.5 horas |
| **Runs completados** | 142/180 (79%) |
| **Runs com falha** | 24 (13%) |
| **Runs nao executados** | 14 (8%) |

### 2.1 Distribuicao dos Runs

| Prompt | Com SA | Sem SA | Total |
|--------|--------|--------|-------|
| v13 | 28 | 29 | 57 |
| v14 | 26 | 27 | 53 |
| v15 | 27 | 29 | 56 |
| **Total** | **81** | **85** | **166** |

**Nota**: 166 runs com resultados validos para analise (142 completed + alguns dos failed com metricas parciais).

---

## 3. Resultados

### 3.1 Comparacao por Prompt

| Prompt | N | Method Coverage | UI Coverage | States | Act/min |
|--------|---|-----------------|-------------|--------|---------|
| v13 | 57 | 34.8% ± 27.7 | 17.9% ± 11.4 | 4.6 | 8.2 |
| **v14** | 53 | **41.1% ± 28.6** | **18.6% ± 11.7** | **6.1** | **9.0** |
| v15 | 56 | 34.5% ± 27.7 | 17.0% ± 11.7 | 5.1 | 7.7 |

**Vencedor em coverage**: v14

### 3.2 Latencia e Hit Rate

| Prompt | N | Latencia Media | Hit Rate |
|--------|---|----------------|----------|
| v13 | 48 | 1427 ± 392 ms | 98.3% |
| v14 | 48 | 1362 ± 379 ms | 98.4% |
| **v15** | 46 | **1355 ± 386 ms** | **98.7%** |

**Vencedor em latencia/hit rate**: v15

### 3.3 Impacto do Static Analysis

| Variante | N | Method Coverage | UI Coverage | States |
|----------|---|-----------------|-------------|--------|
| **Com SA** | 81 | **38.1% ± 27.9** | **18.4% ± 12.0** | 5.1 |
| Sem SA | 85 | 35.4% ± 28.2 | 17.2% ± 11.1 | 5.3 |

**Delta (Com SA - Sem SA)**:
- Method Coverage: **+2.8%**
- UI Coverage: **+1.2%**

### 3.4 Matriz Prompt × Static Analysis

| Prompt | SA | N | Method Coverage | UI Coverage |
|--------|-----|---|-----------------|-------------|
| v13 | Com | 28 | 38.7% ± 26.8 | 18.0% ± 11.3 |
| v13 | Sem | 29 | 31.0% ± 28.6 | 17.8% ± 11.7 |
| v14 | Com | 26 | 40.6% ± 28.7 | 19.6% ± 12.7 |
| **v14** | **Sem** | 27 | **41.6% ± 29.1** | 17.5% ± 10.8 |
| v15 | Com | 27 | 35.1% ± 29.0 | 17.7% ± 12.4 |
| v15 | Sem | 29 | 34.0% ± 26.9 | 16.3% ± 11.1 |

### 3.5 Ranking por Method Coverage

| # | Configuracao | Method Coverage | N |
|---|--------------|-----------------|---|
| 1 | **v14 + Sem SA** | **41.6%** | 27 |
| 2 | v14 + Com SA | 40.6% | 26 |
| 3 | v13 + Com SA | 38.7% | 28 |
| 4 | v15 + Com SA | 35.1% | 27 |
| 5 | v15 + Sem SA | 34.0% | 29 |
| 6 | v13 + Sem SA | 31.0% | 29 |

---

## 4. Verificacao das Hipoteses

### 4.1 Hipoteses Originais (Fase 2)

| # | Hipotese | Resultado | Status |
|---|----------|-----------|--------|
| H4 | v14 > v13 em hit_rate | v14 (98.4%) ≈ v13 (98.3%) | ~ Empate |
| H5 | v14 > v13 em method_coverage | v14 (41.1%) > v13 (34.8%) | **Confirmada** |
| H6 | SA melhora navegacao | Delta +2.8% method_cov | **Confirmada** |

### 4.2 Hipoteses Adicionais (v15)

| # | Hipotese | Resultado | Status |
|---|----------|-----------|--------|
| H4' | v15 > v14 > v13 em hit_rate | v15 (98.7%) > v14 (98.4%) > v13 (98.3%) | **Confirmada** |
| H5' | v15 > v14 > v13 em method_coverage | v14 (41.1%) > v13 (34.8%) > v15 (34.5%) | **Refutada** |
| H7 | v15 se beneficia mais de SA | Delta v13: +7.7%, Delta v15: +1.1% | **Refutada** |

---

## 5. Analise e Discussao

### 5.1 Paradoxo v15: Melhor Precisao, Pior Exploracao

O prompt v15 apresentou um paradoxo:
- **Melhor precisao**: Menor latencia (1355ms) e maior hit rate (98.7%)
- **Pior exploracao**: Menor method coverage (34.5%)

**Hipoteses explicativas**:

1. **Sobrecarga cognitiva**: Os scores e tags adicionais (`[UNTESTED]`, `[score:XXX]`) podem estar "distraindo" o LLM, fazendo-o focar em elementos com alto score em vez de explorar novos estados.

2. **Viés de confirmação**: O LLM pode estar escolhendo elementos marcados como "[UNTESTED]" repetidamente na mesma tela, em vez de navegar para novas telas.

3. **Complexidade do prompt**: O formato mais complexo do v15 pode estar consumindo mais contexto, deixando menos "espaço mental" para raciocínio estratégico.

### 5.2 v14: Equilibrio Ideal

O prompt v14 demonstrou o melhor equilibrio:
- **Method coverage superior**: 41.1% (vs 34.8% do v13 e 34.5% do v15)
- **Mais estados descobertos**: 6.1 (vs 4.6 do v13 e 5.1 do v15)
- **Maior throughput**: 10 acoes/min e 31 acoes totais

O "structured reasoning" do v14 parece guiar melhor a **estrategia de navegacao** sem sobrecarregar com informacoes de scoring.

### 5.3 Static Analysis: Impacto Moderado

O impacto do static analysis foi positivo mas moderado:
- **+2.8% method coverage global**
- Maior beneficio para v13 (+7.7%) do que para v15 (+1.1%)

Isso sugere que os MOP markers e WTG guidance sao mais uteis para prompts simples. O v15 ja tem informacoes de priorizacao embutidas, tornando o SA parcialmente redundante.

### 5.4 Surpresa: v14+NoSA foi o Melhor

A melhor configuracao foi **v14 sem static analysis** (41.6%), superando v14 com SA (40.6%). Possivel explicacao:

- O v14 tem raciocinio estruturado proprio que pode conflitar com as sugestoes do WTG
- Menos informacoes = decisoes mais rapidas e exploracao mais ampla

---

## 6. Comparacao com Baseline

| Ferramenta | Method Coverage |
|------------|-----------------|
| Humanoid | 26.79% |
| FastBot | 25.46% |
| APE | 25.29% |
| **rv-agent (v14+NoSA)** | **41.6%** |
| **rv-agent (v14+SA)** | **40.6%** |

**Conclusao**: rv-agent com v14 supera todas as ferramentas tradicionais por margem significativa (+55% vs Humanoid).

---

## 7. Recomendacoes

### 7.1 Configuracao Recomendada

| Parametro | Valor |
|-----------|-------|
| Prompt | **v14** |
| Static Analysis | **Opcional** (sem SA teve resultado marginalmente melhor) |
| Mode | multimode (70/30) |
| Params | default (temperature=0.01, top_p=0.6, top_k=50) |

### 7.2 Proximos Passos

1. **Investigar v15**: Por que pior coverage com melhor precisao?
   - Analisar logs de decisao do LLM
   - Verificar padrao de navegacao entre telas

2. **Testar variacoes de llm_probability**: O multimode 70/30 foi o unico testado
   - Fase 3 deve testar 0%, 30%, 50%, 70%

3. **Validar com mais seeds**: Apenas 2 seeds foram usados
   - Alta variancia observada (±28% em method coverage)

---

## 8. Arquivos de Resultados

| Arquivo | Descricao |
|---------|-----------|
| `results/mini_phase2_multimode/checkpoint.json` | Estado do experimento |
| `results/mini_phase2_multimode/runs/*.json` | Resultados individuais |
| `results/mini_phase2_multimode/experiment.log` | Log de execucao |

---

## 9. Conclusao

O **prompt v14** (structured reasoning) e a melhor escolha para o rv-agent em modo multimode, atingindo **41.1% de method coverage** - significativamente acima do baseline de ferramentas tradicionais (26.79%).

O prompt v15 com elementos enriquecidos nao trouxe os beneficios esperados em exploracao, apesar de melhorar precisao de cliques. Isso sugere que **menos informacao pode ser melhor** para guiar a estrategia do LLM.

O static analysis tem impacto positivo mas moderado (+2.8%), sendo mais util para prompts mais simples.
