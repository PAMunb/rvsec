# Plano: calibração da configuração LLM do APE-RV (prompts × sampling × routing)

**Data**: 2026-07-21 (rev. 2 — pós-validação em 3 eixos: SOTA, código Java `ape@d90c1f4`, lado Python; cada eixo auditado por verificador adversarial independente)
**Status**: Proposta (aguardando review)
**Objetivo**: escolher a configuração LLM (prompt, temperature, top_p, top_k, routing) do experimento final, num subset de 30–50 APKs representativo do dataset de 181, de modo que o braço `aperv` LLM seja **pelo menos não-inferior ao `ape` builtin em coberturas e superior em violações MOP encontradas** (`mop_unique`, APKs-com-violação).
**Fontes de evidência**: diagnóstico llm-gap (§2), SOTA verificado `docs/20260721_sota_llm_gui_testing.md`, survey interna `docs/20260313_comparacao_tools_recentes.md`, espaço de parâmetros `docs/20260316_aperv_llm.md`, superfície de config do jar (§4), prior-art de calibração (gh9, 20260318, 20260407, `rvsec-calibracao` — §12), metodologia do loop `docs/20260721_metodologia_calibracao_loop.md`.

---

## 1. Contexto e restrições

- **Prompt stateless**: modelo pequeno (Qwen3-VL-4B) em GPU 16GB via SGLang — sem conversa multi-turno; qualquer "memória" tem que ser injetada compacta no prompt de cada chamada.
- **Execução local** (máquina com GPU), template derivado de `experimento-20260721/`, adaptado para multi-arm interleaved (§6): todos os braços usam o mesmo modelo servido, então rodam interleaved num único experimento; SGLang extraído para compose compartilhado (um só `sglang-server`, provado por `[APE-LLM-CONFIG-ACK] server_model=` em cada task).
- **Dataset**: `APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181` (181 APKs dexlib2+JCA com `.apk.json` co-localizado); skips de pré-processamento ligados.
- **Dependência de modelo (H7)**: o cmp_llm_20260721 (base×v2, img 0.9.3 com tap-fix) decide o MODELO antes; a calibração roda com o vencedor. Se for necessário paralelizar, rodar com o base e re-checar o delta de modelo depois.
- **Saída por coordenada é inegociável**: a visão multimodal de elementos fora do dump do UIAutomator (`llm_tap`) é o diferencial do aperv. Nenhuma hipótese propõe prompt por índice/lista numerada.

## 2. Evidência que molda o desenho (diagnóstico llm-gap, 2026-07-21)

1. **O gap do braço LLM vs sem-LLM é ~100% custo de oportunidade** (Hipótese A): 175 vs 273 ações/300s (1,56×), ~96s do wall-clock bloqueados em inferência (93 chamadas × ~1,03s). Contrafactual pela curva widget@300→widget@600: com o mesmo nº de ações o gap fecha inteiro.
2. **Por ação, o LLM não é pior** — cobre ~46% mais por ação. O problema é volume, não qualidade da decisão.
3. **23,2% das chamadas são desperdício puro** (16,5% no_match + 6,7% falha de parse) na gramática antiga. ⚠️ **Semântica mudou no `ape@d90c1f4`**: erro de grounding (coordenada in-bounds longe de widget) agora vira `llm_tap` off-tree, não `no_match`; `no_match` restante ≈ rejeição de política (boundary y<5%/y>94%, degenerate (0,0), type_text sem campo, back-fail, tela sem ações) (`LlmRouter.mapToModelAction:555-678`). Toda análise sobre traces antigos (cmpm_base) usa a taxonomia antiga e precisa de mapeamento explícito (§5-0.2).
4. **Paradoxo v2**: modelo tunado decide melhor (match 62→80%) e cobre menos (−2,62pp) — sugerindo que fidelidade ≠ cobertura e que exploração estocástica tem valor. ⚠️ Corrida confundida (tap no-op); revalidar no cmp_llm_20260721.

O SOTA externo (5 ferramentas, 3 peer-reviewed) converge: **selective routing** — explorador algorítmico primário, LLM só em estagnação — é o único regime publicado em que LLM ganha do algorítmico no mesmo orçamento (SOTA doc §1, §6.1). LLMDroid e HybridMonkey usam gatilho de **estagnação apenas** (sem gatilho por estado novo).

## 3. Hipóteses (todas nomeadas; cada braço testa combinações delas)

| # | Hipótese | Predição testável | Braços |
|---|---|---|---|
| **H1** | **Routing/orçamento de chamadas**: reduzir a frequência de chamadas devolve throughput e fecha o gap. Semântica verificada (`LlmRouter.java:205-234`): `llm_percentage` governa **só** o gatilho aleatório; new-state e estagnação são gatilhos independentes. New-state dispara ~1×/estado novo (~27–55 chamadas/300s, doc 20260316 §3.1) — **não é regime de poucas chamadas**; o regime SOTA canônico é estagnação-ONLY. Estagnação dispara **uma única vez** (igualdade) em `graphStableRestartThreshold/2`, e o threshold é **compartilhado com o restart do SATA** (`StatefulAgent.java:1047`) — não retunar na Fase A | ações/task ↑ monotônico A1→A2→A4→A3; cov_mop de A2/A3 > A1 | A2, A3, A4 vs A1 |
| **H2** | **Latência por chamada**: prompt mais curto reduz time_ms → mais ações. ⚠️ Recalibrada: `compact_v1` só encurta o system text (o corpo user cai no default = ape_current, `ApePromptBuilder:139-159`); a escada real de comprimento é `visual_only` < `ape_current` ≤ `v13` < `v17`. Além disso o prefill da **imagem** domina o custo (screenshot ≈ 25–26× tokens por +4–5,7% sucesso, SOTA §2) — largar a imagem está fora de questão (off-dump), então o efeito esperado de texto é **pequeno**; H2 é caracterização de mecanismo, não lever primário. TEL só reporta tokens_in total (sem separação imagem/texto) | time_ms e tokens_in: A8 < A2 < A9; cov ∝ ações se H1 domina | A8, A9 vs A2 |
| **H3** | **Temperatura = controle de exploração, não acurácia**: temp>0 recupera exploração estocástica (paradoxo v2); temp=0 (config do cmp_llm) pode ser exatamente errada. Lacuna publicável (SOTA §3: zero estudos de sampling para exploração GUI). Desenho desconfundido: braço temp-only (A6) isola temperatura; A5 testa o bundle vendor (0,7/0,8/20); A7 testa temp=0,25 (único ponto com precedente publicado, AutoDroid) | cov_mop/mop_unique: A6/A7 > A2; taxa de traces idênticos entre reps < que em temp 0 (alvo <30%) | A5, A6, A7 vs A2 |
| **H4** | **Desperdício de chamadas**: endurecer formato de saída (parse-null 6,7%→~0; modo de falha típico de modelo pequeno, SOTA §3) e calibrar snapping — **mantendo saída por coordenada**. Alvos concretos no jar: tolerância euclidiana `max(50, min(w,h)/2)` hardcoded (`LlmRouter.java:653`) e bandas de boundary 5%/94% hardcoded (`:572`) → expor como properties na Fase B (viram knobs sem-rebuild dali em diante) | no_match+null ↓ forte; llm_tap preservado; ganho de cov além do previsto pelo throughput | B1 vs vencedor-A |
| **H5** | **Valor por chamada (MOP-targeted)** — *re-escopada*: o jar **não tem** estado runtime de "operação monitorada já disparada" (só reachability estática `[DM]/[M]` do `.apk.json`; canal plataforma→tool é rejeitado por decisão de projeto). Proxy disponível hoje: **widgets `[DM]/[M]` com `visitedCount==0`** ("MOP-reaching ainda não tentados") — injetável no prompt sem plumbing novo | mop_unique ↑ com cov_method ~constante | B2 vs B1 |
| **H6** | **Memória de platô** — *re-escopada*: histórico genérico (últimas 5 ações + visit counts) **já é injetado** em todas as variantes principais (`ApePromptBuilder:75-82,338,643,667,752`) — "adicionar histórico" está morto. O que falta é o padrão HybridMonkey: **tentativas de escape falhas dentro do platô atual** + cache de decisões de escape reutilizado com p≈0,8 (SOTA §2/§6.4) | ações repetidas no mesmo estado ↓; cov_act ↑ | B3 vs B1 |
| **H7** | **Modelo**: base vs v2 (decidida pelo cmp_llm_20260721, fora deste plano) | — | dependência externa |
| **H8** | **Gatilho RV-específico** (futuro, contribuição inédita — SOTA §6.6/§7.3): disparar o LLM em **platô de cov_mop**, não de cobertura genérica. Exige mudança no jar; candidata à Fase B/C ou paper seguinte. (No SOTA doc esse conceito aparece rotulado "H6" — a numeração daqui prevalece) | — | fase B+ |

**Prior pré-registrado** (SOTA §1/§6.1): o vencedor será um braço de poucas chamadas (A2/A3), não A1 (p=0,7).

Critério global de sucesso: existe config LLM com **cov_method/cov_act/cov_mop não-inferiores ao `ape` builtin (margem SESOI −2,0pp) e mop_unique/APKs-com-violação superiores** (testes unilaterais pré-registrados, §8–§9), no subset — com confirmação final no 181 completo (guarda anti-overfit de subset, §12).

## 4. O que dá para variar sem rebuild do jar (superfície de config)

Verificado em `ape@d90c1f4` (`Config.java:194-206`) e no aperv-tool:

- **Sem rebuild**: `llm_temperature` (0.3), `llm_top_p` (0.6), `llm_top_k` (50), `llm_model`, `llm_timeout_ms` (15000), `llm_percentage` (0.02, clamp [0,1]), `llm_on_new_state` (true), `llm_on_stagnation` (true), `llm_prompt_variant` (`ape_current`; 6 variantes embutidas: `ape_current`, `ape_reasoning`, `compact_v1`, `v13`, `v17`, `visual_only`), `llm_url`. SglangClient envia temperature/top_p/top_k/max_tokens no corpo da request (`SglangClient.java:120-124`).
- **Exige mudança no repo `ape` + rebuild** (rodada B): texto de prompt novo, `max_tokens` (hardcoded 1024, `LlmRouter.java:105`), tolerância de snapping e bandas de boundary (hardcoded, §3-H4), gatilho de estagnação desacoplado do restart (H8).
- **⚠️ Braços = variantes NOMEADAS, nunca `@override`**: a identidade de task é `(apk, tool, variant, rep, timeout)` (`platform.py:308-316`) e o sufixo `@` é descartado antes (`__main__.py:207`) — dois braços que diferem só por override **colidem e o segundo é silenciosamente pulado no resume**. Cada braço da calibração é um dict novo em `get_variants()` (nomes tool-agnostic `cal_*`).
- **Regra INV-APV-14 estendida**: o guard atual cobre só as 18 chaves de exploração (`test_aperv_tool.py:565-574`); `_LLM_FLAGS` **omite `llm_percentage` e `llm_prompt_variant`** (`tool.py:261-270`) — criar guard `LLM_ARM_KEYS` exigindo todas as chaves LLM explícitas em cada braço `cal_*`. Auditoria por task: `[APE-LLM-CONFIG]` no `.trace` + `[APE-LLM-CONFIG-ACK] server_model=`.
- Telemetria por chamada (emissores verificados em `LlmRouter.java:125-137, 377-380, 488-512, 708-723`): `[APE-LLM-TEL]` (result matched/llm_tap/no_match, reason, qwen vs pixel, nearest_dist, tokens, time_ms, mode) só em **sucesso**; falhas em `[APE-LLM-ERROR]` (image/timeout/http/connection/parse/internal) **sem time_ms**, e falha de screenshot não emite ERROR (só counter) — o proxy "% wall-clock em inferência" **subconta** falhas (viés documentado; corrigir na Fase B se relevante). Parser: `experimento-20260721/scripts/analyze_cmpv2_llm.py`.

## 5. Fase 0 — offline, custo zero de GPU (pré-requisito de tudo)

**0.1 Seleção do subset (40 APKs, alvo 30–50).** Fonte: `data/results/cmpma_consolidado/per_apk_paired.csv`. Método:
- Estratificar os 181 por quantis de `ape__cov_mop` (5 estratos, incluindo cov_mop=0), amostragem proporcional; otimização gulosa com trocas: |média_subset − média_full| ≤1,0pp em `ape__cov_mop` (35,10), na média pooled dos 5 braços (~35,8) e secundariamente em `ape__cov_method`/`ape__cov_act`/`ape__mop_unique`; KS não-significativo em cov_mop (sd=24,4 exige casar distribuição).
- Fração com `mop_unique>0` ≈ 70% (espelha os 70,7% do full).
- **Estratificação LLM-relevante adicional**: balancear também por proxy de "quanto o LLM atua" no APK (nº de chamadas LLM e taxa de `llm_tap` por APK extraídos dos traces do cmpm_base) — representatividade para o `ape` não garante representatividade para os braços LLM.
- **Guarda anti-overfit** (lição 20260407: vencedor no subset-30 regrediu −0,93pp no full-169): reportar robustez do ranking em reamostragens leave-10-out do subset; decisão final sempre confirmada no 181 (§12).
- `app.michaelwuensch.bitbanana_79` (único FLAG_SECURE): incluir como estrato de controle.
- Validar presença de `.apk`+`.apk.json` e gerar `filters/`.

**0.2 Decomposição causal dos no-matches.** Classificar ~200 chamadas `no_match`/`null` dos traces do `cmpm_base` em (a) parse/formato, (b) denormalização, (c) grounding, (d) política — usando `qwen=`, `pixel=`, `reason`, `nearest_dist`. ⚠️ Esses traces são da **gramática antiga**; mapear para a taxonomia d90c1f4 (grounding→`llm_tap`; `no_match`→boundary/degenerate/policy) antes de dimensionar H4. O resultado calibra: (a) instruções de formato; (b)/(c) tolerância de snapping (valor default atual: `max(50, min(w,h)/2)` px) — sempre mantendo coordenadas.

**0.3 Extração dos baselines do subset** a partir do cmpma (referência histórica; âncoras re-rodam no experimento).

**0.4 Análise de poder (feita, 2026-07-21, de `per_apk_paired.csv`).** sd das diferenças pareadas de cov_mop entre braços: 5,3–9,6pp (mediana 7,2). **MDE (α=,05 bilateral, poder 80%) ≈ 3,3pp com n=40** — maior que as diferenças reais observadas entre braços razoáveis (0,15–2,8pp). `mop_unique`: MDE ≈ 0,7 violações com n=40. Consequências vinculantes: (i) Fases A/B **selecionam por ranking de efeito + proxies mecanísticos, nunca por p-valor**; (ii) Fase C usa testes **unilaterais** pré-registrados e n maior (§8); (iii) "APKs-com-violação" (binária por APK, teste de McNemar) entra como métrica com poder potencialmente melhor quando o LLM acha violações onde o ape não acha.

## 6. Fase A — Rodada de screening sem rebuild (`cala`)

Um único experimento multi-arm interleaved: **1 SGLang compartilhado** (compose próprio) + 8 containers, cada container com `RV_TOOLS` multi-tool listando os 11 braços (Cartesiano APK×braço×rep no mesmo emulador — padrão cmpma, mínimo confound). A ordem de execução dentro do container é determinística `apk→tool→rep` (`platform.py:227-235`), com a ordem de braços fixada por `RV_TOOLS` — **rotacionar a ordem dos braços entre os 8 containers** para balancear efeito de ordem. 40 APKs, **2 reps**, timeout 300s, `RV_LOGCAT_DIAGNOSTICS` off.

| Braço | Config (todas as chaves LLM explícitas; demais = A1) | Testa |
|---|---|---|
| **ANC1** | `ape` builtin | âncora principal (meta: bater) |
| **ANC2** | `aperv:sata_mop_act_frontier` | melhor não-LLM (teto algorítmico) |
| **A1** | `v13`, p=0.7, temp=0, top_p=0.6, top_k=50, ns=true, stag=true | controle LLM = config do cmp_llm_20260721 |
| **A2** | p=**0.3** | H1 (menos chamadas aleatórias) |
| **A3** | **estagnação-ONLY**: ns=**false**, stag=true, p=**0** | H1 extremo — regime SOTA canônico (LLMDroid/HybridMonkey) |
| **A4** | **new-state+estagnação**: ns=true, stag=true, p=**0** | H1 híbrido (~27–55 chamadas/300s via new-state) |
| **A5** | p=0.3, **temp=0.7, top_p=0.8, top_k=20** (bundle vendor Qwen) | H3 (bundle) |
| **A6** | p=0.3, **temp=0.7** (top_p=0.6, top_k=50) | H3 (temperatura isolada; A6 vs A5 isola top_p/top_k) |
| **A7** | p=0.3, **temp=0.25** (top_p=0.6, top_k=50) | H3 (ponto AutoDroid, único com precedente publicado) |
| **A8** | p=0.3, temp=0, **`visual_only`** | H2 (extremo curto real — sem widget list) |
| **A9** | p=0.3, temp=0, **`v17`** | H2 (extremo longo) / prompt alternativo |

(`compact_v1` foi descartado como braço: corpo user idêntico ao `ape_current` — contraste de comprimento fraco.)

Custo: 11 braços × 40 APKs × 2 reps = **880 tasks** ≈ 880×(300s+~80s)/8 ≈ **11,6h** (uma noite longa). Smoke gate antes (4 APKs × braços extremos A1/A3/A8, 90s, 1 rep, multi-tool): COMPLETED, cobertura>0, `[APE-LLM-CONFIG]` de cada braço ecoa exatamente o dict da variante, `server_model` correto, identidades distintas no tasks.json (11 braços), 0 VerifyError.

**Decisão (gates em ordem; screening SELECIONA, nunca conclui — §5-0.4):**
1. *Gate proxy (eliminação)*: parse-fail alto, latência média ≥2× a mediana entre braços, ou ações/task < A1 sem ganho de cov → eliminado.
2. *Ranking de outcome*: média aparada 10% + bootstrap pareado por APK (B≥10.000, seed fixa) das diferenças vs ANC1/ANC2 em cov_mop, mop_unique, cov_method, cov_act; Friedman+Holm só como sanidade descritiva.
3. *Checagem mecanística*: o ganho observado de cada braço bate com o previsto por proxies (Δações/task × +46%/ação)? Divergência grande = mecanismo não entendido → investigar antes de promover.
4. *H3 específico*: taxa de traces idênticos entre reps (alvo <30% nos braços temp>0).
Levar **2–3 configs** para a rodada B (não 1 — a ordenação A→B pode escolher ótimo local se H4 interagir com routing).

## 7. Fase B — Rodada com novas variantes de prompt (`calb`, exige mudanças no repo `ape`)

Mudanças no `ape` (workflow próprio daquele repo; commits pushed antes do build — o Dockerfile clona o branch default). Todas mantêm **saída por coordenada**. **Bundle único de rebuild** — além dos itens de experimento, expor como properties tudo que hoje é hardcoded, para que TODA iteração posterior (Fase C, loop autônomo) seja sem-rebuild:
1. **Robustez de formato + snapping** (H4): endurecer instruções de saída/tool-schema (parse-null→~0) e tolerância de snapping configurável (`ape.llmSnapTolerancePx`? — valor calibrado pelos dados do §5-0.2), bandas de boundary configuráveis; preservar `llm_tap` off-tree.
2. **Prompt MOP-targeted via proxy** (H5): injetar os widgets `[DM]/[M]` com `visitedCount==0` e pedir o elemento que leva a um deles.
3. **Memória de platô** (H6): tentativas de escape falhas no platô atual (+ opcional cache de escape p≈0,8, padrão HybridMonkey).
4. `ape.llmMaxTokens` + mapping no aperv-tool (1 linha em `APERV_PROPERTY_MAPPING`); opcional: time_ms nos caminhos de falha e ERROR na falha de screenshot (fecha o viés de medição do §4); opcional: gatilho de estagnação LLM desacoplado do restart (pré-requisito do H8).

Braços: ANC1, ANC2, 2–3 sobreviventes-A (controle na imagem nova), **B1** = melhor-A + formato/snapping (H4), **B2** = B1 + MOP-targets (H5), **B3** = B1 + memória de platô (H6). 7–8 braços × 40 × 2 = 560–640 tasks ≈ **7,5–8,5h**.

## 8. Fase C — Confirmação (`calc`)

Melhor config global vs ANC1 vs ANC2, **3 reps**, **n=80–100 APKs** (mesmo método de seleção do §5-0.1, supersete do subset-40; MDE cai para ≈2,1–2,3pp, compatível com o SESOI de 2,0pp) — 3 braços × 90 × 3 ≈ 810 tasks ≈ **11h**. Hipóteses pré-registradas NESTE doc antes da rodada; testes **unilaterais** (só interessa ser melhor). Desfechos possíveis: **GO** (critério do §3 atingido), **NO-GO** (inferior com poder adequado), **INCONCLUSIVE** (CI cruza o SESOI) — reportar qual for, com a partição throughput×qualidade atualizada. Se GO, a config vai para o experimento final no 181 completo (confirmação definitiva, guarda anti-overfit).

## 9. Métricas e análise

- **Primária confirmatória (Fase C)**: `cov_mop` (não-inferioridade, margem 2,0pp) **e** `mop_unique` (superioridade) — conjunção pré-registrada; APKs-com-violação (McNemar) co-primária de suporte; `cov_method`, `cov_act`, `mop_total` secundárias. Consolidação sempre dos logcats (`consolidate_compare.py`, anti-gh58), contagem por identidade dedup.
- **Proxies (.trace, por braço)**: ações/task (`SATA begin step`), chamadas LLM, time_ms médio, tokens_in/out (total; sem split imagem/texto), % matched/llm_tap/no_match(+reason)/null, distribuição de `mode`, % wall-clock em inferência (viés: subconta falhas, §4). Parser: `analyze_cmpv2_llm.py`.
- **Exploração**: taxa de traces idênticos entre reps; activities distintas visitadas.
- **Estatística**: pareado por APK (média das reps); média aparada 10% como sumário; bootstrap pareado por APK B≥10.000 (seed fixa) para CIs; rank-biserial como effect size; Friedman+Holm descritivo entre braços (script novo — não existe hoje para multi-arm; `cmpm_paired_stats.py` é 2-arm hardcoded). Ferramentas estatísticas reutilizadas de `rvsec-calibracao/scripts/{stats_utils,power_analysis}.py`.

## 10. Riscos e gotchas

- **Contenção de GPU**: braços com taxa de chamada diferente compartilham 1 SGLang; interleaving por APK + rotação de ordem entre containers equaliza a contenção média; registrar time_ms como covariável.
- **Confound de imagem**: âncoras e braços LLM na MESMA imagem/máquina/experimento; números históricos do cmpma só como sanidade. Na Fase B, âncoras e sobreviventes-A re-rodam na imagem nova (ponte entre imagens).
- **Resume/identidade**: braços = variantes nomeadas (§4); smoke verifica 11 identidades distintas no tasks.json.
- **Paradoxo v2 confundido**: não usar números do cmpm_v2 como evidência; H3 é o teste limpo.
- **Dependência de orçamento**: o veredito vale para timeout 300s — a 300s a penalidade dominante é latência/throughput; em orçamentos longos (≥1h) a literatura mostra platô dos LLM-drivens e crescimento contínuo dos algorítmicos (SOTA §1). Não generalizar o resultado para outros budgets sem re-teste.
- **Overfit de subset**: lição 20260407 (−0,93pp no full); mitigações §5-0.1 (leave-10-out) e §8/§12 (confirmação no 181).
- **Nunca**: gerenciar emulador na mão; mudar config de experimento em curso; tocar no repo `ape` a partir de sessão rv-android (mudanças da Fase B são do workflow daquele repo); usar `@override` para distinguir braços.

## 11. Cronograma-resumo

| Etapa | Duração | Pré-requisito |
|---|---|---|
| Fase 0 (subset + no-match + poder + scripts) | ~1 dia, offline | consolidados existentes |
| cmp_llm_20260721 (modelo, H7) | já planejado, à parte | imagem 0.9.3 pronta |
| Fase A (`cala`, 880 tasks) | ~12h + smoke | Fase 0 + modelo decidido + variantes `cal_*` |
| Fase B (`calb`, 560–640 tasks) | ~8h + rebuild imagem | mudanças no `ape` + Fase A |
| Fase C (`calc`, ~810 tasks) | ~11h | Fase B |

## 12. Decisão Optuna (prior art auditado)

Quatro gerações de calibração numérica via Optuna/TPE no projeto (gh9 executada; 20260318 v1 executada parcial; 20260407 v2 post-mortem; `rvsec-calibracao` v4 pronta e nunca rodada) produziram o mesmo padrão: **melhor trial estatisticamente empatado com bons defaults**, e no caso v1 o vencedor do subset-30 **regrediu no full-169**. A própria v4 documenta que TPE não resolve categóricos em ~44 trials e auto-estima P(GO)≈10–15%. O problema LLM é dominado por knobs **categóricos/estruturais** (prompt, regime de routing) + um mecanismo de throughput — exatamente onde braços-hipótese com estatística pareada funcionam e busca cega não.

**Decisão**: o desenho por estágios (este plano) é o instrumento principal — Optuna **não** substitui nem envelopa as fases. Reservar Optuna como **micro-refinamento opcional e encaixotado** após a Fase B: ≤6 dimensões contínuas (temperature, top_p, top_k, opcionalmente percentage) em torno do braço vencedor, warm-start no vencedor, Sobol→TPE, ~15–20 trials × 20 APKs × 2 reps (~15h), objetivo = média aparada da diferença pareada de cov_mop vs ANC1. Saída do Optuna é **candidata, nunca conclusão** — passa obrigatoriamente pela Fase C. Reaproveitar de `rvsec-calibracao`: `stats_utils.py`/`power_analysis.py` (já na §9) e, se o micro-loop rodar, o trio coordinator/job-queue/worker em modo local (SQLite + 1 Postgres).

A metodologia completa do pipeline e do loop autônomo de calibração (contratos entrada→saída por passo, verificador independente por iteração, divisão de changes entre repos): `docs/20260721_metodologia_calibracao_loop.md`.
