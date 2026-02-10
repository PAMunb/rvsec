# Relatório E3 Baseline - RV-Agent Validation

**Data da Análise**: 15/01/2026
**Data da Execução**: 14-15/01/2026
**Status**: Execução completa

---

## Resumo Executivo

Este relatório apresenta os resultados do experimento E3 Baseline, que compara três modos de exploração do RV-Agent:

| Modo | Descrição |
|------|-----------|
| `pure_algorithm` | Exploração puramente algorítmica (DFS + MOP priority) |
| `llm_only` | Exploração guiada exclusivamente por LLM (Qwen3-VL) |
| `multimode` | Modo híbrido (70% LLM / 30% algoritmo) |

### Resultados Principais

| Métrica | pure_algorithm | multimode | llm_only |
|---------|----------------|-----------|----------|
| Apps completos | 34 | 33 | 32 |
| Taxa de sucesso | 69% | 67% | 65% |
| Iterações (média) | 93.2 | 41.2 | 36.0 |
| Method coverage (média) | 34.9% | 31.6% | 27.7% |
| Activities descobertas | 3.5 | 3.3 | 3.2 |

**Conclusão Principal**: O modo `pure_algorithm` apresentou a melhor cobertura média (34.9%), seguido por `multimode` (31.6%) e `llm_only` (27.7%). Isso se deve principalmente ao maior número de iterações do modo algorítmico (93 vs ~40).

---

## 1. Configuração do Experimento

### 1.1 Parâmetros

| Parâmetro | Valor |
|-----------|-------|
| APKs testados | 49 |
| Modos | 3 (pure_algorithm, llm_only, multimode) |
| Seeds | 1 (42) |
| Timeout por run | 300 segundos |
| Total de runs | 147 |
| LLM Model | Qwen/Qwen3-VL-4B-Instruct |
| LLM Server | SGLang @ http://192.168.0.36:30000/v1 |
| LLM Temperature | 0.001 |
| Estratégia | rvagent (DFS + MOP priority) |

### 1.2 Ambiente

- **Dispositivo**: Android Emulator (emulator-5554)
- **Android SDK**: API 29 (Android 10)
- **APKs**: Instrumentados com especificações genéricas (MOP)
- **Análise estática**: GESDA, GATOR (WTG), REACH

---

## 2. Resultados Detalhados por Modo

### 2.1 Pure Algorithm

**Status**: 34/49 runs completos (69%)

| Métrica | Média | Mediana | Min | Max | Std Dev |
|---------|-------|---------|-----|-----|---------|
| Iterações | 93.2 | 96.0 | 24 | 132 | 24.3 |
| Method Coverage | 34.9% | 30.1% | 1.9% | 81.8% | 21.8% |
| Activities | 3.5 | 3.0 | 1 | 7 | 1.8 |


### 2.2 LLM Only

**Status**: 32/49 runs completos (65%)

| Métrica | Média | Mediana | Min | Max | Std Dev |
|---------|-------|---------|-----|-----|---------|
| Iterações | 36.0 | 36.5 | 1 | 64 | 11.8 |
| Method Coverage | 27.7% | 21.2% | 1.4% | 81.8% | 19.3% |
| Activities | 3.2 | 3.0 | 1 | 6 | 1.3 |

**Métricas LLM**:
- Total de cliques LLM: 1095
- Hits (cliques válidos): 1068
- Hit rate global: 97.5%


### 2.3 Multimode (Híbrido)

**Status**: 33/49 runs completos (67%)

| Métrica | Média | Mediana | Min | Max | Std Dev |
|---------|-------|---------|-----|-----|---------|
| Iterações | 41.2 | 43.0 | 1 | 73 | 18.7 |
| Method Coverage | 31.6% | 24.8% | 4.3% | 86.2% | 20.7% |
| Activities | 3.3 | 3.0 | 1 | 6 | 1.4 |

**Métricas LLM**:
- Total de cliques LLM: 906
- Hits (cliques válidos): 882
- Hit rate global: 97.4%


---

## 3. Ranking de Apps por Method Coverage

### 3.1 Pure Algorithm

| # | App | Coverage | Iterações | Activities |
|---|-----|----------|-----------|------------|
| 1 | net.xvello.salasana | 81.8% | 78 | 4 |
| 2 | github.vatsal.easyweatherdemo | 81.2% | 68 | 2 |
| 3 | com.example.openpass | 80.0% | 123 | 5 |
| 4 | t20kdc.offlinepuzzlesolver | 62.9% | 83 | 6 |
| 5 | com.freezingwind.animereleasenotifier | 60.0% | 123 | 2 |
| 6 | com.github.axet.binauralbeats | 56.8% | 131 | 2 |
| 7 | com.allansimon.verbisteandroid | 55.2% | 84 | 4 |
| 8 | max.music_cyclon | 51.7% | 132 | 2 |
| 9 | biz.gyrus.yaab | 50.6% | 100 | 5 |
| 10 | jackpal.androidterm | 45.7% | 101 | 4 |

### 3.2 Multimode

| # | App | Coverage | Iterações | Activities |
|---|-----|----------|-----------|------------|
| 1 | com.allansimon.verbisteandroid | 86.2% | 49 | 4 |
| 2 | com.freezingwind.animereleasenotifier | 66.2% | 70 | 4 |
| 3 | t20kdc.offlinepuzzlesolver | 65.2% | 68 | 6 |
| 4 | com.example.openpass | 62.9% | 49 | 6 |
| 5 | com.github.axet.binauralbeats | 62.6% | 67 | 4 |
| 6 | github.vatsal.easyweatherdemo | 56.2% | 39 | 2 |
| 7 | net.xvello.salasana | 45.5% | 1 | 2 |
| 8 | jackpal.androidterm | 44.1% | 46 | 4 |
| 9 | com.example.root.analyticaltranslator | 43.8% | 54 | 3 |
| 10 | max.music_cyclon | 43.3% | 5 | 1 |

### 3.3 Llm Only

| # | App | Coverage | Iterações | Activities |
|---|-----|----------|-----------|------------|
| 1 | net.xvello.salasana | 81.8% | 41 | 4 |
| 2 | com.allansimon.verbisteandroid | 72.4% | 36 | 3 |
| 3 | com.github.axet.binauralbeats | 57.7% | 36 | 2 |
| 4 | com.freezingwind.animereleasenotifier | 49.2% | 1 | 1 |
| 5 | t20kdc.offlinepuzzlesolver | 48.3% | 25 | 4 |
| 6 | com.example.root.analyticaltranslator | 43.8% | 39 | 3 |
| 7 | biz.gyrus.yaab | 41.1% | 39 | 4 |
| 8 | jackpal.androidterm | 38.8% | 35 | 2 |
| 9 | org.emergent.android.weave | 37.9% | 46 | 5 |
| 10 | org.pyload.android.client | 37.4% | 45 | 5 |

---

## 4. Comparação Direta Entre Modos

**Apps com todos os modos completos**: 31

### 4.1 Modo com Melhor Coverage por App

| Modo | Apps onde foi melhor | Percentual |
|------|---------------------|------------|
| pure_algorithm | 20 | 65% |
| multimode | 14 | 45% |
| llm_only | 6 | 19% |

### 4.2 Diferença Média de Coverage

| Comparação | Diferença Média |
|------------|-----------------|
| pure_algorithm vs multimode | +3.1% |
| pure_algorithm vs llm_only | +6.5% |
| multimode vs llm_only | +3.5% |

---

## 5. Apps que Falharam

**Total de apps com falhas**: 18

| App | Modos que falharam |
|-----|--------------------|
| com.fairphone.mycontacts | llm_only, multimode, pure_algorithm |
| com.gbeatty.arxiv | llm_only, multimode, pure_algorithm |
| com.gianlu | llm_only, multimode, pure_algorithm |
| com.grarak.kerneladiutor | llm_only, multimode, pure_algorithm |
| com.jonbanjo | llm_only, multimode, pure_algorithm |
| com.lzx.lock | llm_only, multimode, pure_algorithm |
| com.orpheusdroid.screenrecorder | llm_only, multimode, pure_algorithm |
| community.fairphone.clock | llm_only, multimode, pure_algorithm |
| github.vatsal.easyweatherdemo | llm_only |
| io.github.tjg1 | llm_only, multimode, pure_algorithm |
| is.zi | llm_only, multimode, pure_algorithm |
| net.etuldan.sparss | llm_only, multimode, pure_algorithm |
| net.momodalo.app | llm_only, multimode, pure_algorithm |
| org.dyndns.warenix.web2pdf | llm_only |
| org.exarhteam.iitc_mobile | multimode |
| org.fitchfamily.android | llm_only, multimode, pure_algorithm |
| org.ntpsync.service | llm_only, multimode, pure_algorithm |
| org.secuso.privacyfriendlydicegame | llm_only, multimode, pure_algorithm |

**Apps que falharam em TODOS os modos**: 15

Possíveis causas:
- Apps que requerem permissões especiais não concedidas
- Apps que crasham imediatamente ao iniciar
- Apps incompatíveis com o emulador (x86)
- Apps que requerem configuração inicial complexa

---

## 6. Erros MOP Detectados

**Total de erros detectados**: 31
**Erros únicos**: 31
**Apps com erros**: 7

| App | Total de Erros |
|-----|----------------|
| com.github.axet.binauralbeats | 12 |
| max.music_cyclon | 6 |
| com.mareksebera.simpledilbert | 3 |
| net.xvello.salasana | 3 |
| org.emergent.android.weave | 3 |
| org.exarhteam.iitc_mobile | 2 |
| de.kaffeemitkoffein.imagepipe | 2 |

**Nota**: Os erros MOP são violações de especificações detectadas pelo runtime verification. A baixa quantidade de erros indica que a maioria dos apps segue as especificações corretamente.

---

## 7. Análise de Correlação

### 7.1 Iterações vs Coverage

- **pure_algorithm**: r = 0.206
- **multimode**: r = 0.227

**Interpretação**: Correlação fraca (r ≈ 0.2) entre iterações e coverage, indicando que mais iterações não garantem necessariamente maior cobertura. A qualidade das ações (exploração inteligente) é mais importante que a quantidade.

---

## 8. Conclusões e Recomendações

### 8.1 Principais Descobertas

1. **Pure algorithm supera LLM em cobertura**: O modo algorítmico alcançou 34.9% de cobertura média, vs 31.6% (multimode) e 27.7% (llm_only).

2. **LLM realiza menos iterações**: Os modos LLM completaram ~40 iterações vs ~93 do algoritmo, devido à latência do modelo (~3-4s por ação vs <1s do algoritmo).

3. **Hit rate excelente (97.5%)**: O LLM (Qwen3-VL) acertou 97.5% dos cliques (1068/1095 em llm_only, 882/906 em multimode). A validação visual está funcionando corretamente.

4. **Falhas consistentes**: 12 apps falharam em todos os modos, indicando problemas de compatibilidade ou configuração.

5. **Poucos erros MOP**: Apenas 31 erros detectados em 7 apps, sugerindo que a maioria dos apps segue as especificações.

### 8.2 Problemas Identificados

1. **Iterações insuficientes nos modos LLM**: Com timeout de 300s, LLM faz ~40 iterações vs ~93 do algoritmo. A latência do modelo (~3-4s) limita a exploração. Considerar:
   - Aumentar timeout para 600s
   - Usar modelo mais rápido (vLLM quantizado)
   - Pré-processar screenshots para reduzir tokens

2. **18 apps com falhas**: Revisar manualmente os apps que falharam para identificar padrões. Possíveis causas:
   - Apps que requerem permissões especiais
   - Apps incompatíveis com emulador x86
   - Apps que crasham imediatamente

3. **Cobertura MOP zerada**: Os arquivos `.methods` reportam `total_mop_methods=0` para a maioria dos apps. Verificar se as especificações genéricas estão corretamente mapeadas.

### 8.3 Próximos Passos

1. [ ] Analisar logs dos apps que falharam para identificar padrões
2. [ ] Executar experimento com timeout maior (600s) para equalizar iterações
3. [ ] Executar com múltiplas seeds (42, 123, 456) para validação estatística
4. [ ] Comparar com baseline de ferramentas tradicionais (Monkey: 19.8%, Humanoid: 26.8%)
5. [ ] Investigar cobertura MOP zerada nos arquivos `.methods`
6. [ ] Testar com especificações JCA (criptografia) para apps de segurança

---

## Apêndice A: Dados Completos por App

<details>
<summary>Clique para expandir tabela completa</summary>

| App | Mode | Iterations | Coverage | Activities |
|-----|------|------------|----------|------------|
| biz.gyrus.yaab | pure_algorithm | 100 | 50.6% | 5 |
| biz.gyrus.yaab | multimode | 43 | 36.1% | 2 |
| biz.gyrus.yaab | llm_only | 39 | 41.1% | 4 |
| com.aidinhut.simpletextcrypt | pure_algorithm | 65 | 12.2% | 2 |
| com.aidinhut.simpletextcrypt | multimode | 51 | 24.5% | 4 |
| com.aidinhut.simpletextcrypt | llm_only | 40 | 12.2% | 5 |
| com.allansimon.verbisteandroid | pure_algorithm | 84 | 55.2% | 4 |
| com.allansimon.verbisteandroid | multimode | 49 | 86.2% | 4 |
| com.allansimon.verbisteandroid | llm_only | 36 | 72.4% | 3 |
| com.example.openpass | pure_algorithm | 123 | 80.0% | 5 |
| com.example.openpass | multimode | 49 | 62.9% | 6 |
| com.example.openpass | llm_only | 54 | 35.7% | 5 |
| com.example.root.analyticaltranslator | pure_algorithm | 70 | 43.8% | 2 |
| com.example.root.analyticaltranslator | multimode | 54 | 43.8% | 3 |
| com.example.root.analyticaltranslator | llm_only | 39 | 43.8% | 3 |
| com.fairphone.mycontacts | pure_algorithm | 0 | 0.0% | 0 |
| com.fairphone.mycontacts | multimode | 0 | 0.0% | 0 |
| com.fairphone.mycontacts | llm_only | 0 | 0.0% | 0 |
| com.freezingwind.animereleasenotifier | pure_algorithm | 123 | 60.0% | 2 |
| com.freezingwind.animereleasenotifier | multimode | 70 | 66.2% | 4 |
| com.freezingwind.animereleasenotifier | llm_only | 1 | 49.2% | 1 |
| com.gbeatty.arxiv | pure_algorithm | 0 | 6.9% | 0 |
| com.gbeatty.arxiv | multimode | 0 | 6.9% | 0 |
| com.gbeatty.arxiv | llm_only | 0 | 6.9% | 0 |
| com.gianlu | pure_algorithm | 0 | 0.0% | 0 |
| com.gianlu | multimode | 0 | 0.0% | 0 |
| com.gianlu | llm_only | 0 | 0.0% | 0 |
| com.github.axet.binauralbeats | pure_algorithm | 131 | 56.8% | 2 |
| com.github.axet.binauralbeats | multimode | 67 | 62.6% | 4 |
| com.github.axet.binauralbeats | llm_only | 36 | 57.7% | 2 |
| com.googlecode.networklog | pure_algorithm | 89 | 25.0% | 3 |
| com.googlecode.networklog | multimode | 59 | 24.8% | 4 |
| com.googlecode.networklog | llm_only | 28 | 23.5% | 2 |
| com.grarak.kerneladiutor | pure_algorithm | 0 | 0.0% | 0 |
| com.grarak.kerneladiutor | multimode | 0 | 0.0% | 0 |
| com.grarak.kerneladiutor | llm_only | 0 | 0.0% | 0 |
| com.jonbanjo | pure_algorithm | 0 | 0.0% | 0 |
| com.jonbanjo | multimode | 0 | 0.0% | 0 |
| com.jonbanjo | llm_only | 0 | 0.0% | 0 |
| com.linuxcounter.lico_update_003 | pure_algorithm | 70 | 28.9% | 3 |
| com.linuxcounter.lico_update_003 | multimode | 45 | 28.9% | 4 |
| com.linuxcounter.lico_update_003 | llm_only | 37 | 6.7% | 3 |
| com.lzx.lock | pure_algorithm | 0 | 0.0% | 0 |
| com.lzx.lock | multimode | 0 | 0.0% | 0 |
| com.lzx.lock | llm_only | 0 | 0.0% | 0 |
| com.mareksebera.simpledilbert | pure_algorithm | 103 | 30.0% | 3 |
| com.mareksebera.simpledilbert | multimode | 33 | 24.8% | 4 |
| com.mareksebera.simpledilbert | llm_only | 36 | 20.4% | 2 |
| com.orpheusdroid.screenrecorder | pure_algorithm | 0 | 2.4% | 0 |
| com.orpheusdroid.screenrecorder | multimode | 0 | 2.4% | 0 |
| com.orpheusdroid.screenrecorder | llm_only | 0 | 2.4% | 0 |
| com.pindroid | pure_algorithm | 76 | 8.9% | 2 |
| com.pindroid | multimode | 38 | 8.9% | 3 |
| com.pindroid | llm_only | 41 | 10.6% | 3 |
| com.sam.hex | pure_algorithm | 115 | 34.3% | 7 |
| com.sam.hex | multimode | 23 | 19.8% | 4 |
| com.sam.hex | llm_only | 37 | 19.8% | 3 |
| com.soumikshah.investmenttracker | pure_algorithm | 103 | 16.6% | 4 |
| com.soumikshah.investmenttracker | multimode | 38 | 8.7% | 2 |
| com.soumikshah.investmenttracker | llm_only | 35 | 8.7% | 2 |
| com.tobiaskuban.android.monthcalendarwidgetfoss | pure_algorithm | 81 | 11.4% | 3 |
| com.tobiaskuban.android.monthcalendarwidgetfoss | multimode | 45 | 11.4% | 3 |
| com.tobiaskuban.android.monthcalendarwidgetfoss | llm_only | 34 | 8.9% | 3 |
| com.zzzmode.appopsx | pure_algorithm | 126 | 23.6% | 6 |
| com.zzzmode.appopsx | multimode | 40 | 12.0% | 2 |
| com.zzzmode.appopsx | llm_only | 47 | 16.5% | 4 |
| community.fairphone.clock | pure_algorithm | 0 | 0.0% | 0 |
| community.fairphone.clock | multimode | 0 | 0.0% | 0 |
| community.fairphone.clock | llm_only | 0 | 0.0% | 0 |
| de.kaffeemitkoffein.imagepipe | pure_algorithm | 98 | 33.8% | 2 |
| de.kaffeemitkoffein.imagepipe | multimode | 4 | 22.0% | 2 |
| de.kaffeemitkoffein.imagepipe | llm_only | 8 | 21.8% | 2 |
| de.srlabs.gsmmap | pure_algorithm | 80 | 5.8% | 1 |
| de.srlabs.gsmmap | multimode | 47 | 6.5% | 3 |
| de.srlabs.gsmmap | llm_only | 30 | 6.5% | 3 |
| fm.libre.droid | pure_algorithm | 68 | 17.2% | 2 |
| fm.libre.droid | multimode | 42 | 17.2% | 3 |
| fm.libre.droid | llm_only | 37 | 17.2% | 3 |
| github.vatsal.easyweatherdemo | pure_algorithm | 68 | 81.2% | 2 |
| github.vatsal.easyweatherdemo | multimode | 39 | 56.2% | 2 |
| github.vatsal.easyweatherdemo | llm_only | 0 | 43.8% | 1 |
| in.blogspot.anselmbros.torchie | pure_algorithm | 118 | 19.5% | 4 |
| in.blogspot.anselmbros.torchie | multimode | 39 | 10.3% | 3 |
| in.blogspot.anselmbros.torchie | llm_only | 36 | 10.3% | 2 |
| io.github.tjg1 | pure_algorithm | 0 | 0.0% | 0 |
| io.github.tjg1 | multimode | 0 | 0.0% | 0 |
| io.github.tjg1 | llm_only | 0 | 0.0% | 0 |
| is.zi | pure_algorithm | 0 | 0.0% | 0 |
| is.zi | multimode | 0 | 0.0% | 0 |
| is.zi | llm_only | 0 | 0.0% | 0 |
| jackpal.androidterm | pure_algorithm | 101 | 45.7% | 4 |
| jackpal.androidterm | multimode | 46 | 44.1% | 4 |
| jackpal.androidterm | llm_only | 35 | 38.8% | 2 |
| max.music_cyclon | pure_algorithm | 132 | 51.7% | 2 |
| max.music_cyclon | multimode | 5 | 43.3% | 1 |
| max.music_cyclon | llm_only | 34 | 24.2% | 2 |
| me.kuehle.carreport | pure_algorithm | 123 | 21.7% | 7 |
| me.kuehle.carreport | multimode | 35 | 17.8% | 5 |
| me.kuehle.carreport | llm_only | 41 | 18.5% | 5 |
| net.etuldan.sparss | pure_algorithm | 0 | 0.0% | 0 |
| net.etuldan.sparss | multimode | 0 | 0.0% | 0 |
| net.etuldan.sparss | llm_only | 0 | 0.0% | 0 |
| net.jjc1138.android.scrobbler | pure_algorithm | 91 | 30.3% | 2 |
| net.jjc1138.android.scrobbler | multimode | 24 | 36.8% | 3 |
| net.jjc1138.android.scrobbler | llm_only | 15 | 36.8% | 2 |
| net.momodalo.app | pure_algorithm | 0 | 0.0% | 0 |
| net.momodalo.app | multimode | 0 | 0.0% | 0 |
| net.momodalo.app | llm_only | 0 | 0.0% | 0 |
| net.xvello.salasana | pure_algorithm | 78 | 81.8% | 4 |
| net.xvello.salasana | multimode | 1 | 45.5% | 2 |
| net.xvello.salasana | llm_only | 41 | 81.8% | 4 |
| nl.patrickkostjens.kandroid | pure_algorithm | 112 | 1.9% | 1 |
| nl.patrickkostjens.kandroid | multimode | 73 | 4.3% | 1 |
| nl.patrickkostjens.kandroid | llm_only | 64 | 1.4% | 1 |
| nz.gen.geek_central.ObjViewer | pure_algorithm | 24 | 16.4% | 2 |
| nz.gen.geek_central.ObjViewer | multimode | 33 | 18.2% | 3 |
| nz.gen.geek_central.ObjViewer | llm_only | 34 | 14.5% | 3 |
| org.dyndns.warenix.web2pdf | pure_algorithm | 76 | 17.1% | 3 |
| org.dyndns.warenix.web2pdf | multimode | 1 | 11.7% | 1 |
| org.dyndns.warenix.web2pdf | llm_only | 0 | 11.7% | 1 |
| org.emergent.android.weave | pure_algorithm | 98 | 39.3% | 5 |
| org.emergent.android.weave | multimode | 47 | 35.3% | 3 |
| org.emergent.android.weave | llm_only | 46 | 37.9% | 5 |
| org.exarhteam.iitc_mobile | pure_algorithm | 56 | 19.9% | 4 |
| org.exarhteam.iitc_mobile | multimode | 0 | 15.5% | 1 |
| org.exarhteam.iitc_mobile | llm_only | 36 | 19.0% | 4 |
| org.fitchfamily.android | pure_algorithm | 0 | 0.0% | 0 |
| org.fitchfamily.android | multimode | 0 | 0.0% | 0 |
| org.fitchfamily.android | llm_only | 0 | 0.0% | 0 |
| org.gmote.client.android | pure_algorithm | 109 | 20.4% | 3 |
| org.gmote.client.android | multimode | 58 | 21.0% | 6 |
| org.gmote.client.android | llm_only | 43 | 20.7% | 6 |
| org.ntpsync.service | pure_algorithm | 0 | 0.0% | 0 |
| org.ntpsync.service | multimode | 0 | 0.0% | 0 |
| org.ntpsync.service | llm_only | 0 | 0.0% | 0 |
| org.pyload.android.client | pure_algorithm | 101 | 43.9% | 7 |
| org.pyload.android.client | multimode | 43 | 37.4% | 5 |
| org.pyload.android.client | llm_only | 45 | 37.4% | 5 |
| org.secuso.privacyfriendlydicegame | pure_algorithm | 0 | 0.0% | 0 |
| org.secuso.privacyfriendlydicegame | multimode | 0 | 0.0% | 0 |
| org.secuso.privacyfriendlydicegame | llm_only | 0 | 0.0% | 0 |
| t20kdc.offlinepuzzlesolver | pure_algorithm | 83 | 62.9% | 6 |
| t20kdc.offlinepuzzlesolver | multimode | 68 | 65.2% | 6 |
| t20kdc.offlinepuzzlesolver | llm_only | 25 | 48.3% | 4 |
| uk.ac.swansea.eduroamcat | pure_algorithm | 94 | 39.7% | 6 |
| uk.ac.swansea.eduroamcat | multimode | 52 | 27.8% | 4 |
| uk.ac.swansea.eduroamcat | llm_only | 41 | 23.1% | 3 |

</details>

---

*Relatório gerado automaticamente pelo RV-Agent Validation Framework*