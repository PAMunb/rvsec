# Debug — cobertura baixa de `sata_mop`/LLM na comparação APE × APE-RV

**Data:** 2026-06-19 (atualizado 2026-06-21)
**Experimento:** `docs/20260619_comparacao_aperv.md` (corrida `comparacao-aperv`, 6 containers `cmp_00..05`, 2028 tasks)
**Status:** corrida **COMPLETA** — 2028/2028 tasks distintas COMPLETED (21 FAILED transientes recuperadas
no resume final, 0 falhas genuínas). Análise pareada concluída (Achado 3). Roteiro: plano §8.2/§10.

## Motivação

No smoke (16 APKs, 1 rep, 120s), a cobertura de método mediana saiu **invertida** do esperado:
`ape 25.3 / sata 26.3 / sata_mop 21.6 / sata_mop_llm 21.5`. Ligar o MOP-guidance (e o LLM)
**baixou** a cobertura em vez de subir — o oposto da hipótese central H2. Antes de validar/refutar
H2/H3 na corrida completa, é preciso achar a causa-raiz: bug de integração, artefato de medição, ou
efeito real.

Este memo registra os achados conforme cada item do roteiro §8.2 é investigado.

---

## Achado 1 — Latência da LLM e timeouts (roteiro §8.2 item 4)

**Hipótese testada:** o braço `aperv:sata_mop_llm` cobriria menos porque chamadas LLM estourariam
o `llm_timeout_ms=15000` sob contenção de GPU (1 GPU, 6 containers) e degradariam para `sata_mop` —
fazendo o braço LLM se comportar como o MOP puro, sem ganho e com tempo gasto à toa.

**Resultado: hipótese de timeout DESCARTADA.**

Fonte da verdade: a telemetria por chamada nos traces do APE-RV
(`<apk>__<rep>__300__aperv:sata_mop_llm.trace`), linha:

```
[APE-LLM-TEL] variant=ape_current call=N mode=new-state action=click qwen=(x,y) pixel=(x,y)
              result=matched ... tokens_in=1212 tokens_out=25 time_ms=1530
```

`time_ms` é a latência ponta-a-ponta da chamada (inclui a ponte `socat` 127.0.0.1:30000 → sglang).

### Distribuição (snapshot 2026-06-19 20:13, corrida ~29% — 71 traces, 7.640 chamadas LLM)

| Métrica | Valor |
|---------|-------|
| mín | 577 ms |
| **mediana** | **1.144 ms** |
| média | 1.264 ms |
| p90 | 1.895 ms |
| p95 | 2.090 ms |
| p99 | 2.724 ms |
| **máx** | 9.321 ms (1 outlier) |
| **timeouts (≥15.000 ms)** | **0 (0,00 %)** |
| ≥8.000 ms | 2 (0,03 %) |
| ≥5.000 ms | 8 (0,10 %) |

Tokens: `tokens_in` mediano 1.360 (imagem + prompt; system prompt em prefix-cache), `tokens_out`
mediano 26 (resposta curta = uma ação/coordenada). Chamadas LLM por task: **mediana 121** (mín 10,
máx 216) — LLM denso e atuante, coerente com `@llm_percentage=0.9`.

### Interpretação

- **A LLM não é gargalo e não degrada por timeout.** Latência dominante ~1,1 s, p95 ~2,1 s — muito
  abaixo do `llm_timeout_ms=15000`. Em 7.640 chamadas, **nenhuma** estourou o timeout; apenas 2
  passaram de 8 s.
- **Sem contenção de GPU efetiva.** Pela interleave dos 4 braços por APK, raramente há 2+ braços LLM
  batendo no SGLang ao mesmo tempo (`#running-req` ≤ 1, `#queue-req` 0 nos logs do `sglang-server`).
  O risco de contenção previsto para H3 não se materializou nesta janela.
- **As ações da LLM estão sendo aplicadas** (`result=matched`, mapeamento Qwen3-VL
  `qwen=(x,y)→pixel=(x,y)`), não ignoradas.

### Consequência para o diagnóstico

A causa da cobertura baixa do braço LLM **não** é "chamadas estourando 15 s e caindo para
`sata_mop`". A investigação deve focar nos demais itens do §8.2:

- **item 2** — `sata_mop` vs `sata` lado a lado: o MOP-guidance prioriza telas que alcançam operações
  monitoradas, mas isso cobre **menos método no geral**? (efeito real, não bug)
- **item 3** — denominador da cobertura MOP (métodos alcançáveis estáticos raramente atingidos em 300 s).
- **item 4 (resto)** — as ações sugeridas pela LLM, embora aplicadas, exploram **menos** que o SATA
  puro? (o LLM pode estar "clicando bem" mas repetindo telas, enquanto o SATA cobre mais por força bruta).
- **item 5** — nº de ações/task por braço: mesmo a ~1,1 s/chamada, 121 chamadas ≈ 140 s só em LLM
  dentro dos 300 s — o braço LLM executa **menos ações totais** que o SATA puro no mesmo tempo. Esta é
  agora a hipótese principal para o braço LLM (custo de oportunidade do tempo, não timeout).

### Reprodução

```bash
python3 - <<'PY'
import glob, statistics as st, re
times=[]; timeouts=0
for f in glob.glob("data/results/cmp_*/cmp_*/*/*aperv:sata_mop_llm*.trace"):
    for m in re.finditer(r'\[APE-LLM-TEL\].*?time_ms=(\d+)', open(f,errors='ignore').read()):
        ms=int(m.group(1)); times.append(ms); timeouts+=ms>=15000
print(f"n={len(times)} median={st.median(times):.0f} p95={sorted(times)[int(len(times)*0.95)]} max={max(times)} timeouts={timeouts}")
PY
```

---

## Achado 2 — Proporção de ações LLM e custo de oportunidade (roteiro §8.2 itens 4–5)

**Pergunta:** com `@llm_percentage=0.9`, a LLM de fato decide ~90% das ações? E qual o efeito disso
sobre o volume de exploração?

**Resultado: a taxa de 90% está funcionando (mediana 87,5% quando a LLM está ativa), mas o custo de
latência por ação corta o volume de exploração em ~2,3×, e 2 apps nem acionaram a LLM.**

Fonte: traces do braço LLM. Total de ações = steps SATA (`SATA begin step [N]`); ações LLM =
linhas `[APE-LLM-TEL]`. Snapshot 2026-06-19 20:13 (71 tasks, 10.940 steps, 7.640 chamadas LLM).

### Proporção

| Grupo | Tasks | Ações/task (mediana) | Proporção LLM |
|-------|-------|----------------------|---------------|
| **LLM ativa** | 65/71 | **142** | **87,5 %** (mediana; p10 46 %, p90 93 %) |
| **LLM = 0** (fallback SATA puro) | 6/71 | **325** | 0 % |

Gatilho da chamada (`mode=`): `random` (rolagem do `llmPercentage=0.9`) **6.912 (90,5 %)** —
confirma a taxa de 90 %; `new-state` 727; `stagnation` 1.

O gap 90 % → 87,5 % é **`no_match`**: das 7.640 chamadas, **1.184 (15,5 %)** retornaram coordenada
que não casou com nenhum widget (`result=no_match`) → a ação da LLM é descartada e cai no SATA
naquele passo. Tipos de ação: click 7.228, type_text 397, back 15.

### Custo de oportunidade do tempo (mecanismo provável da cobertura baixa do braço LLM)

- Task com LLM ativa: **~142 ações** em 300 s.
- Mesmo orçamento em SATA puro (tasks LLM=0, e o braço `aperv:sata`): **~325 ações**.
- ⇒ **~2,3× menos ações** no braço LLM. ~142 chamadas × ~1,1 s ≈ 156 s só em LLM dentro dos 300 s,
  mais o overhead de screenshot/parse por passo.

A LLM troca **~2,3× menos ações por ações "mais inteligentes"**. Se as ações inteligentes não
compensam o volume perdido, a cobertura cai. **Esta é a hipótese principal para a cobertura baixa do
braço LLM** (§8.2 item 5) — não timeout (Achado 1), não falta de acionamento (a LLM age em 87,5 % das
ações).

### Anomalia — 2 apps com 0 chamadas LLM

`bim.app_1500` e `app.notesr_59` (todas as 3 reps cada = 6 tasks) rodaram como **SATA puro**, sem
nenhuma chamada LLM, apesar de serem o braço LLM. Não é timeout (Achado 1 mostra 0 timeouts).

**Causa confirmada: `FLAG_SECURE`.** Esses apps marcam a janela como segura (`WindowManager.LayoutParams.FLAG_SECURE`),
o que bloqueia a captura de screenshot. Sem imagem, o caminho multimodal do APE-RV não tem o que enviar
ao Qwen3-VL e **degrada para SATA puro** (0 chamadas LLM). É degradação graciosa correta, não bug.

Implicação para a análise: tasks com `FLAG_SECURE` no braço LLM são, na prática, **SATA puro** e devem
ser **tratadas à parte** (ou excluídas) ao comparar `sata_mop_llm` vs `sata_mop` — senão diluem o efeito
do LLM com pontos que não tiveram LLM. Marcar essas identidades na consolidação (§9).

### Reprodução

```bash
python3 - <<'PY'
import glob, re, statistics as st
from collections import Counter
modes=Counter(); res=Counter(); active=[]; zero=[]
for f in glob.glob("data/results/cmp_*/cmp_*/*/*aperv:sata_mop_llm*.trace"):
    d=open(f,errors='ignore').read()
    steps=len(re.findall(r'SATA begin step \[', d))
    tel=re.findall(r'\[APE-LLM-TEL\][^\n]*', d)
    for t in tel:
        modes[re.search(r'mode=(\S+)',t).group(1)]+=1
        res[re.search(r'result=(\S+)',t).group(1)]+=1
    if steps: (zero if not tel else active).append((steps,len(tel)))
print("modes",dict(modes)); print("result",dict(res))
print("LLM-ativas",len(active),"steps_med",st.median([s for s,_ in active]),
      "ratio_med",st.median([c/s for s,c in active]))
print("LLM=0",len(zero),"steps_med",st.median([s for s,_ in zero]) if zero else 0)
PY
```

---

## Achado 3 — Resultado final pareado por APK (Wilcoxon) — H1✓ / H2✗ / H3✗ (§10)

**Pergunta:** com a corrida completa (169 APKs × 3 reps × 4 braços = 2028 tasks), o MOP-guidance
(H2) e o LLM (H3) melhoram a detecção MOP em relação ao APE puro?

**Resultado: H1 confirmada (equivalência), H2 NÃO confirmada (MOP-guidance sem ganho significativo),
H3 refutada (LLM piora significativamente).**

Método (§10): cada APK = 1 ponto pareado = **média das 3 repetições**; Wilcoxon signed-rank pareado
por APK, two-sided, n=169. Fontes: `data/results/comparacao_consolidado/` (gerado por
`scripts/consolida_comparacao_aperv.py`). Coberturas + `mop_unique` (=`total_errors`) do `tasks.json`;
`mop_total` (eventos brutos `RVSEC`) dos logcats.

### Resumo por tool (média sobre as 169 médias-por-APK)

| tool | cov_método | cov_ativ | cov_MOP | mop_único | mop_total |
|------|-----------:|---------:|--------:|----------:|----------:|
| ape | 39.36 | 67.33 | 43.02 | 3.74 | 8.31 |
| aperv:sata | 39.62 | 67.83 | 43.65 | 3.80 | 8.98 |
| aperv:sata_mop | 39.70 | 67.22 | 43.38 | 3.87 | **13.41** |
| aperv:sata_mop_llm | 34.52 | 61.85 | 38.59 | 3.55 | 5.45 |

### Wilcoxon pareado por APK (mediana A/B, vitórias A>B/A<B, p two-sided)

| Hip. | A vs B | métrica | med A / B | A>B / A<B | p | veredito |
|------|--------|---------|-----------|-----------|---|----------|
| H1 | ape vs sata | cov_MOP | 39.9 / 39.5 | 53/57 | 0.295 | ns ✓ equivalência |
| H1 | ape vs sata | mop_único | 2.0 / 2.3 | 16/29 | 0.307 | ns |
| H1 | ape vs sata | cov_método | 34.1 / 34.7 | 64/68 | 0.332 | ns |
| H2 | sata_mop vs ape | cov_MOP | 40.7 / 39.9 | 58/55 | 0.793 | **ns ✗** |
| H2 | sata_mop vs ape | mop_único | 2.0 / 2.0 | 29/16 | 0.093 | ns (tendência) |
| H2 | sata_mop vs sata | cov_MOP | 40.7 / 39.5 | 53/50 | 0.502 | **ns ✗** |
| H2 | sata_mop vs sata | mop_total | 3.3 / 4.0 | 38/59 | 0.139 | ns |
| H3 | llm vs sata_mop | cov_MOP | 32.9 / 40.7 | 22/106 | <0.001 | **sig ✗ (pior)** |
| H3 | llm vs sata_mop | cov_método | 28.9 / 35.4 | 26/124 | <0.001 | **sig (pior)** |
| H3 | llm vs sata_mop | mop_único | 2.0 / 2.0 | 18/43 | 0.002 | **sig (pior)** |
| H3 | llm vs sata_mop | mop_total | 3.0 / 3.3 | 18/88 | <0.001 | **sig (pior)** |

### Interpretação

- **H1 ✓ (equivalência):** `ape` ≈ `aperv:sata` em todas as métricas (p 0.12–0.33). A reimplementação
  APE-RV reproduz o APE original — sanidade do within-binary OK.
- **H2 ✗ (claim central falha):** o MOP-guidance **não melhora** cobertura nem violações únicas de
  forma significativa, nem contra `ape` nem contra `sata` (todos p>0.05). O `sata_mop` **re-dispara**
  mais eventos (`mop_total` 13.4 vs 9.0), mas isso **não vira mais cobertura única nem mais violações
  distintas** — coerente com o denominador grande (§8.2 item 3): re-exercitar as mesmas operações
  monitoradas não amplia o conjunto alcançado. Único sopro de sinal: `mop_único` vs `ape` (29×16,
  p=0.093) — tendência, não significância.
- **H3 ✗ (LLM piora):** adicionar LLM **reduz significativamente** tudo (cov_MOP −7.8pp na mediana,
  106 de 128 APKs com diferença pioram, p<0.001). Causa-raiz nos Achados 1 e 2: a latência (~1,1 s/ação,
  0 timeouts) **não** é o problema; o problema é o **custo de oportunidade** — ~142 ações/task (LLM) vs
  ~325 (SATA puro), ~2,3× menos exploração em 300 s.

### Implicação para a narrativa do paper

O ganho do MOP-guidance (H2) **não aparece** nestas métricas/condições (300 s, dataset JCA-169). Antes
de concluir "MOP-guidance não ajuda", investigar (§8.2 itens 2–3) se o efeito existe numa métrica mais
fina (ex.: *tempo até a primeira violação*, ordem de exploração de telas que alcançam MOP) que a
cobertura agregada em 300 s mascara. Para o LLM (H3), o caminho é orçamento de tempo maior ou reduzir
o custo por ação (taxa < 0.9, ou só em estagnação) — não latência.

### Artefatos

- `data/results/comparacao_consolidado/{per_task,per_apk_paired,per_tool_summary,wilcoxon}.csv`
- `scripts/consolida_comparacao_aperv.py` (reprodutível)
