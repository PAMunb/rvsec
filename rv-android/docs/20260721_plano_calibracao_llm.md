# Plano: calibração da configuração LLM do APE-RV (prompts × sampling × routing)

**Data**: 2026-07-21
**Status**: Proposta (aguardando review)
**Objetivo**: escolher a configuração LLM (prompt, temperature, top_p, top_k, routing) do experimento final, num subset de 30–50 APKs representativo do dataset de 181, de modo que o braço `aperv` LLM seja **pelo menos melhor que o `ape` builtin em coberturas e, principalmente, em violações MOP encontradas** (`mop_unique`, APKs-com-violação).
**Fontes de evidência**: diagnóstico llm-gap (§2), SOTA verificado `docs/20260721_sota_llm_gui_testing.md`, survey interna `docs/20260313_comparacao_tools_recentes.md`, espaço de parâmetros `docs/20260316_aperv_llm.md`, superfície de config do jar (§4).

---

## 1. Contexto e restrições

- **Prompt stateless**: modelo pequeno (Qwen3-VL-4B) em GPU 16GB via SGLang — sem conversa multi-turno; qualquer "memória" tem que ser injetada compacta no prompt de cada chamada.
- **Execução local** (máquina com GPU), template `experimento-20260721/` (pasta autocontida, composes com paths relativos, 8 containers, SGLang único com healthcheck; braços LLM não coexistem com troca de modelo — mas aqui **todos os braços usam o mesmo modelo servido**, então rodam interleaved num único experimento, padrão cmpma).
- **Dataset**: `APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181` (181 APKs dexlib2+JCA com `.apk.json` co-localizado); skips de pré-processamento ligados.
- **Dependência de modelo (H7)**: o cmp_llm_20260721 (base×v2, img 0.9.3 com tap-fix) decide o MODELO antes; a calibração roda com o vencedor. Se for necessário paralelizar, rodar com o base e re-checar o delta de modelo depois.

## 2. Evidência que molda o desenho (diagnóstico llm-gap, 2026-07-21)

1. **O gap do braço LLM vs sem-LLM é ~100% custo de oportunidade** (Hipótese A): 175 vs 273 ações/300s (1,56×), ~96s do wall-clock bloqueados em inferência (93 chamadas × ~1,03s). Contrafactual pela curva widget@300→widget@600: com o mesmo nº de ações o gap fecha inteiro.
2. **Por ação, o LLM não é pior** — cobre ~46% mais por ação. A "efetividade da exploração" por ação está OK; o problema é volume.
3. **23,2% das chamadas são desperdício puro** (16,5% no_match + 6,7% falha de parse): pagam ~1s e caem no fallback SATA sem guidance.
4. **Paradoxo v2**: modelo tunado decide melhor (match 62→80%) e cobre menos (−2,62pp) — sugerindo que fidelidade ≠ cobertura e que exploração estocástica tem valor. ⚠️ Corrida confundida (tap no-op); revalidar no cmp_llm_20260721.

O SOTA externo (5 ferramentas, 3 peer-reviewed) converge: **selective routing** — explorador algorítmico primário, LLM só em estagnação — é o único regime publicado em que LLM ganha do algorítmico no mesmo orçamento (SOTA doc §1, §6).

## 3. Hipóteses (todas nomeadas; cada braço testa combinações delas)

| # | Hipótese | Predição testável | Braços que a testam |
|---|---|---|---|
| **H1** | **Routing/orçamento de chamadas**: reduzir a frequência de chamadas LLM (percentage menor; new-state/estagnação-only) devolve throughput de ações e fecha o gap vs sem-LLM | ações/task ↑ monotônico com percentage ↓; cov_mop do braço p0.1–p0.3 > p0.7 | A2, A3 vs A1 |
| **H2** | **Latência por chamada**: prompt mais curto (menos tokens de prefill/output) reduz time_ms/chamada → mais ações no mesmo wall-clock | tokens_in/time_ms menores em `compact_v1`; cov ∝ ações | A6, A7 vs A1 |
| **H3** | **Temperatura = controle de exploração, não acurácia**: temp>0 recupera a exploração estocástica perdida quando a decisão fica "boa demais" (paradoxo v2); temp=0 (config atual do cmp_llm) pode ser exatamente errada | cov_mop/mop_unique maiores em temp 0,7 que temp 0; taxa de traces idênticos entre reps < com temp 0 (alvo <30%, doc 20260316 §8.4) | A4, A5 vs A1/A2 |
| **H4** | **Desperdício de chamadas**: endurecer o formato de saída (parse-null 6,7%→~0) e tornar o snapping de coordenada mais tolerante reduz os 23,2% de chamadas desperdiçadas — **mantendo saída por coordenada**, porque a visão multimodal de elementos fora do dump do UIAutomator (`llm_tap`) é o diferencial do aperv e não é negociável | no_match+null ↓ forte; llm_tap preservado; ganho de cov além do previsto só pelo throughput | B1 vs vencedor-A |
| **H5** | **Valor por chamada (MOP-targeted)**: injetar no prompt a lista de operações monitoradas ainda não disparadas aumenta mop_unique além do que o ganho de cobertura prevê (lacuna sem baseline publicado — SOTA doc §3/§7.4) | mop_unique ↑ com cov_method ~constante | B2/B3 vs B1 |
| **H6** | **Histórico compacto stateless-friendly**: memória local mínima (últimas ações + falhas do plateau atual, padrão HybridMonkey) reduz revisita sem custo de VRAM | ações repetidas no mesmo estado ↓; cov_act ↑ | B3 vs B1 |
| **H7** | **Modelo**: base vs v2 (decidida pelo cmp_llm_20260721, fora deste plano) | — | dependência externa |

Critério global de sucesso da calibração: existe uma config LLM com **cov_method, cov_act, cov_mop ≥ `ape` builtin e mop_unique/APKs-com-violação > `ape`** (Wilcoxon pareado, p<0,05), no subset.

## 4. O que dá para variar sem rebuild do jar (superfície de config)

Tudo flui por `ape.properties`, gerado por variante no `aperv-tool` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`, `APERV_PROPERTY_MAPPING`), com override inline no compose (`aperv:sata_mop_llm_v13@llm_temperature=0`):

- **Sem rebuild**: `llm_temperature`, `llm_top_p`, `llm_top_k`, `llm_model`, `llm_timeout_ms`, `llm_percentage`, `llm_on_new_state`, `llm_on_stagnation`, `llm_prompt_variant` (seleção entre as **6 variantes embutidas**: `ape_current`, `ape_reasoning`, `compact_v1`, `v13`, `v17`, `visual_only`), `llm_url`.
- **Exige mudança no repo `ape` + rebuild da imagem** (rodada B): texto de prompt novo (7ª+ variante em `ApePromptBuilder.java`), `max_tokens` (hardcoded 1024 em `LlmRouter.java:105`).
- **Regra INV-APV-14**: todo braço define TODAS as chaves LLM explicitamente (nada cai em default do jar silenciosamente); auditar por `[APE-LLM-CONFIG]` no `.trace` de cada task e `[APE-LLM-CONFIG-ACK] server_model=` para o modelo servido.
- Telemetria por chamada já existente: `[APE-LLM-TEL]` (result matched/llm_tap/no_match, qwen vs pixel, tokens_in/out, time_ms, mode) + `[APE-RV] LLM Summary` — todas as métricas proxy vêm daí, via parser `experimento-20260721/scripts/analyze_cmpv2_llm.py` (já reescrito para a gramática d90c1f4).

## 5. Fase 0 — offline, custo zero de GPU (pré-requisito de tudo)

**0.1 Seleção do subset (40 APKs, alvo 30–50).** Fonte: `data/results/cmpma_consolidado/per_apk_paired.csv` (único consolidado com braço `ape` builtin + 4 braços aperv nos mesmos 181 APKs). Método:
- Estratificar os 181 por quantis de `ape__cov_mop` (5 estratos, incluindo o estrato cov_mop=0), amostragem proporcional.
- Otimização gulosa com trocas: minimizar simultaneamente |média_subset − média_full| em `ape__cov_mop` (alvo 35,10), na média pooled dos 5 braços (~35,8 — "cobertura média total") e, secundariamente, em `ape__cov_method`/`ape__cov_act`/`ape__mop_unique`; tolerância ±1,0 pp.
- Restrições: fração com `mop_unique>0` ≈ 70% (espelha os 71% do full — poder para a métrica principal); KS subset vs full não-significativo em cov_mop (casar distribuição, não só média — sd=24,3 exige isso).
- `app.michaelwuensch.bitbanana_79` (único FLAG_SECURE do selected181): **incluir e marcar como estrato de controle** (degradação LLM→SATA é comportamento, não bug), como no cmpm.
- Validar presença de `.apk`+`.apk.json` no dataset físico e gerar `filters/`.

**0.2 Decomposição causal dos no-matches (gate do 20260322).** Classificar ~200 chamadas `no_match`/`null` dos traces existentes do `cmpm_base` em (a) parse/formato, (b) denormalização, (c) grounding, (d) policy — já temos `qwen=(x,y)`, `pixel=(x,y)`, `reason`, `nearest_dist` no TEL. O resultado dimensiona a H4: (a) se ataca com instruções de formato/tool-schema; (b)/(c) com snapping mais tolerante — sempre mantendo coordenadas (a visão off-dump é o diferencial).

**0.3 Extração dos baselines do subset** a partir do cmpma (referência histórica; as âncoras re-rodam no experimento para comparação na mesma imagem/máquina).

## 6. Fase A — Rodada de screening sem rebuild (`cala`)

Um único experimento multi-arm interleaved (mesmo modelo servido, 1 SGLang), 8 containers, 40 APKs, **2 reps**, timeout 300s, `RV_LOGCAT_DIAGNOSTICS` off (comparação de tools; padrão da skill).

| Braço | Config (chaves explícitas por braço) | Testa |
|---|---|---|
| **ANC1** | `ape` builtin | âncora principal (meta: bater) |
| **ANC2** | `aperv:sata_mop_act_frontier` | melhor não-LLM conhecido (teto algorítmico) |
| **A1** | `v13`, p=0.7, temp=0, top_p=0.6, top_k=50 | controle LLM = config do cmp_llm_20260721 |
| **A2** | `v13`, **p=0.3**, temp=0 | H1 (menos chamadas) |
| **A3** | `v13`, **new-state+stagnation only** (percentage≈0, `llm_on_new_state`+`llm_on_stagnation` true) | H1 extremo (selective routing SOTA) |
| **A4** | `v13`, p=0.7, **temp=0.7, top_p=0.8, top_k=20** (vendor Qwen) | H3 |
| **A5** | `v13`, **p=0.3, temp=0.7/0.8/20** | H1×H3 (combinação candidata a vencedora) |
| **A6** | **`compact_v1`**, p=0.3, temp=0 | H2 |
| **A7** | **`v17`**, p=0.3, temp=0 | H2/prompt alternativo |

Custo: 9 braços × 40 APKs × 2 reps = **720 tasks** ≈ 720×(300s+~80s overhead)/8 containers ≈ **9,5h** (uma noite). Smoke gate antes (4 APKs × braços LLM extremos, 90s, 1 rep): COMPLETED, cobertura>0, `[APE-LLM-CONFIG]` ecoa a config do braço, `server_model` correto, 0 VerifyError.

**Decisão (gates em ordem):**
1. *Gate proxy (descartar, nunca declarar vencedor)*: braço com parse-fail alto, latência média ≥2× a mediana, ou ações/task < A1 sem ganho de cov → eliminado.
2. *Outcome*: Friedman + Holm entre braços LLM; Wilcoxon pareado de cada sobrevivente vs ANC1/ANC2 em cov_mop, mop_unique, cov_method, cov_act.
3. *H3 específico*: taxa de traces idênticos entre reps por braço (alvo <30%).
Levar 1–2 configs vencedoras para a rodada B.

## 7. Fase B — Rodada com novas variantes de prompt (`calb`, exige mudanças no repo `ape`)

Mudanças no `ape` (via workflow próprio daquele repo; commits pushed antes do build da imagem — o Dockerfile clona o branch default). Todas mantêm **saída por coordenada** — a capacidade de tocar elementos fora do dump do UIAutomator (`llm_tap`) é o diferencial do aperv e não pode ser restringida:
1. **Robustez de formato + snapping** (H4): endurecer instruções de saída/tool-schema para zerar o parse-null (6,7%) e calibrar o threshold de snapping do no_match (dados do §5-0.2), preservando o tap off-tree.
2. **Prompt MOP-targeted** (P5; H5): injetar as N operações monitoradas ainda não disparadas (o jar conhece `reachesTarget` do `.apk.json`) e pedir o elemento que leva a uma.
3. **Histórico compacto** (P4; H6): últimas 3–5 ações + contagem de visitas do estado atual (stateless-friendly, padrão memória-local HybridMonkey).
4. `max_tokens` configurável (`ape.llmMaxTokens`) + mapping no aperv-tool.

Braços: ANC1, ANC2, vencedor-A (controle), **B1** = vencedor-A + formato/snapping (H4), **B2** = B1 + MOP-targets, **B3** = B1 + histórico. 6 braços × 40 × 2 reps = 480 tasks ≈ **6,5h**.

## 8. Fase C — Confirmação (`calc`)

Melhor config global vs ANC1 vs ANC2, **3 reps**, 40 APKs (9 braços→3 braços, 360 tasks ≈ 5h), hipóteses pré-registradas neste doc. Critério de sucesso do §3. Se a config vencer, ela é a config do experimento final; se não vencer o `ape`, o resultado honesto é reportar o teto atual e as causas (com a partição throughput×qualidade atualizada).

## 9. Métricas e análise

- **Primárias (outcome)**: `cov_mop`, `mop_unique` (= `total_errors`), APKs-com-violação; **secundárias**: `cov_method`, `cov_act`, `mop_total`. Consolidação sempre dos logcats (`consolidate_compare.py`, anti-gh58), contagem por identidade dedup.
- **Proxies (.trace, por braço)**: ações/task (`SATA begin step`), chamadas LLM, time_ms médio, tokens_in/out, % matched/llm_tap/no_match/null, distribuição de `mode` (new-state/stagnation/random), % do wall-clock em inferência. Parser: `analyze_cmpv2_llm.py`.
- **Exploração**: taxa de traces idênticos entre reps (determinismo), nº de activities distintas visitadas.
- **Estatística**: pareado por APK (média das reps); Friedman+Holm entre braços; Wilcoxon vs âncoras; rank-biserial como effect size (`cmpm_paired_stats.py`).

## 10. Riscos e gotchas

- **Contenção de GPU**: 8 containers interleaved compartilham 1 SGLang; monitorar time_ms por braço — se a latência média subir muito acima da referência ~1,1s, os braços de percentage alto ficam penalizados de forma assimétrica. Mitigação: braços interleaved por APK (todo braço sofre a mesma contenção média) + registrar time_ms como covariável.
- **Confound de imagem**: âncoras e braços LLM na MESMA imagem/máquina/experimento; nunca comparar contra números históricos do cmpma como teste primário (só sanidade).
- **Resume**: identidade `(apk,tool,variant,rep,timeout)` — cada braço precisa ser uma variante nomeada distinta (ou override que entre na identidade); verificar no smoke que os 9 braços geram identidades distintas no tasks.json.
- **Paradoxo v2 confundido**: não usar números do cmpm_v2 como evidência; H3 é o teste limpo da hipótese exploração.
- **Nunca**: gerenciar emulador na mão; mudar config de experimento em curso sem autorização; tocar no repo `ape` a partir desta sessão (mudanças da fase B são do workflow daquele repo).

## 11. Cronograma-resumo

| Etapa | Duração | Pré-requisito |
|---|---|---|
| Fase 0 (subset + no-match + scripts) | ~1 dia, offline | consolidados existentes |
| cmp_llm_20260721 (modelo, H7) | já planejado, à parte | imagem 0.9.3 pronta |
| Fase A (`cala`, 720 tasks) | ~10h + smoke | Fase 0 + modelo decidido |
| Fase B (`calb`, 480 tasks) | ~7h + rebuild imagem | mudanças no `ape` + Fase A |
| Fase C (`calc`, 360 tasks) | ~5h | Fase B |
