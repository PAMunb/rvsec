# SOTA verificado: teste de GUI Android guiado por LLM/VLM (2023–2026)

**Data**: 2026-07-21
**Método**: deep-research multi-agente (5 ângulos de busca × 20 fontes × 100 afirmações extraídas → 25 verificadas adversarialmente por 3 votos independentes cada: **24 confirmadas, 1 refutada**). Complementa e atualiza a survey interna `docs/20260313_comparacao_tools_recentes.md`.
**Uso**: fonte de evidência para o plano de calibração LLM do APE-RV (`docs/20260721_plano_calibracao_llm.md`) — cada melhoria proposta ao aperv deve citar a seção correspondente daqui, ser executada e ter o efeito medido.

---

## 1. Conclusão central: o SOTA 2025–2026 convergiu para *selective LLM routing*

A evidência mais forte e consistente (5 ferramentas independentes, 3 delas peer-reviewed) é que **manter um explorador algorítmico como loop primário de eventos e invocar o LLM apenas em estagnação/tarpit/alvos não alcançados** vence tanto os baselines puramente algorítmicos quanto as ferramentas always-LLM:

| Ferramenta (venue) | Padrão de routing | Resultado verificado |
|---|---|---|
| **LLMDroid** (FSE 2025, peer-reviewed) | Exploração autônoma da tool base (DroidBot/Humanoid/Fastbot2); transição para "LLM Guidance" **só quando o crescimento de cobertura desacelera** | +26,16% de cobertura média sobre as 3 tools base, em 14 apps top do Google Play |
| **HybridMonkey / HybridDroidbot** (ASE 2026, peer-reviewed) | Random exploration; LLM (GPT-4o) invocado **só quando detecta UI tarpit** (k=8 estados consecutivos com similaridade perceptual pHash > 0,95) | Cobertura cresce sustentadamente em runs de 3h enquanto GPTDroid/LLMDroid platôam em ~60min; custo $0,19/rodada vs $9,21 do GPTDroid (~1.425 queries) |
| **LLM-Explorer** (MobiCom 2025, peer-reviewed) | Inversão total: LLM **só para manutenção de conhecimento** (fusão de estados abstratos + grafo de interação); a escolha da ação por passo é **sem LLM** (sorteio entre ações abstratas não exploradas) | Maior cobertura média de activity (64,58% vs DroidAgent 60,1%) em 20 apps/2h; custo $0,11/app vs $16,31 do DroidAgent (148×) |
| **CovAgent** (2026, preprint) | Fuzzer algorítmico (APE/Fastbot) permanece explorador primário; agente LLM (Claude Sonnet 3.7) atua **só nas activities que o fuzzer não alcançou**, via scripts Frida (code-as-action) | CovAgent-APE 49,5% activity coverage vs APE puro 17,7% em runs de 60min (obs.: motivação declarada dos autores é alcançabilidade de GUI, não latência; dataset exclui apps fáceis, o que deflaciona baselines) |
| **EpiDroid** (2026, preprint) | "Sparse calling": LLM nunca por ação — só para sumarização semântica de clusters de páginas e recomposição/replay | +10–28% method coverage sobre Fastbot/LLM-Explorer/LLMDroid |

### Por que always-LLM perde: latência custa eventos

Evidência direta e quantificada de ferramentas LLM **perdendo** de exploradores algorítmicos:

- Tempos por passo verificados: **Monkey 0,79s vs LLM-Explorer 5,19s vs DroidAgent 19,10s**.
- Monkey* (random widget-aware) atinge 24,8% de branch coverage superando testers LLM-driven em orçamentos de 3h (paper do HybridMonkey).
- GPTDroid/LLMDroid platôam em ~60 min em runs de 3h (caveat: os autores do estudo de tarpit notam que o platô pode ser amplificado além dos orçamentos originais dos baselines — a *direção* do efeito é robusta, as magnitudes exatas não).
- Ressalva de atribuição: o baixo throughput do LLM-Explorer (227 eventos/30min vs 499 do Fastbot) é **parcialmente** overhead do harness DroidBot (UTG), não só inferência.

**Convergência com o diagnóstico interno**: a partição do gap dos nossos `cmp*` (relatório llm-gap, 2026-07-21) atribuiu ~100% do déficit do braço LLM à Hipótese A (menos ações por latência: 175 vs 273 ações/300s), com qualidade por ação igual ou melhor. O SOTA externo chega à mesma conclusão por caminho independente.

## 2. Representação de estado e formato de ação: consenso confirmado

- **Representação dominante em tools de texto**: lista textual **numerada/ID'd** de widgets visíveis (derivada de accessibility/XML, com filtragem de oclusão). AutoDroid: HTML simplificado com só 5 tags (`<button> <checkbox> <scroller> <input> <p>`), ID = ordem na GUI tree, elementos invisíveis podados, equivalentes fundidos.
- **Formato de ação dominante**: template restrito **índice-do-widget + tipo-de-ação** (AutoDroid fill-in-the-blank; HybridMonkey igual). **Nenhuma ferramenta verificada emite coordenadas cruas** — confirma a conclusão da survey interna (`20260322_aperv_tuning.md`) de que a abordagem de coordenadas do APE-RV é sem precedentes e é a fonte estrutural do no-match.
- **Custo do multimodal**: no benchmark DailyDroid (75 tasks, GPT-4o/o4-mini), adicionar screenshot ao texto da UI-tree rende só +4–5,7% de sucesso por **25–26× o custo** — texto-apenas é o default custo-efetivo. (Relevante para nós: um prompt textual índice-numerado pode dispensar a imagem em parte das chamadas, cortando latência de prefill multimodal.)
- **Grounding sem coordenadas em VLMs**: GUI-Actor (NeurIPS 2025) substitui geração de string de coordenada por action head de atenção; GUI-Actor-7B supera UI-TARS-72B em ScreenSpot-Pro (44,6 vs 38,1) — modelo pequeno com mecanismo de grounding melhor vence modelo 10× maior gerando coordenada.
- **Memória**: deliberadamente **local e mínima** no SOTA de teste — HybridMonkey exclui o trace global e mantém só o histórico de tentativas falhas *dentro do tarpit atual* + cache persistente de escapes por estado, reutilizado com p=0,8 em vez de re-consultar o LLM. GPTDroid é o contraponto (memória funcional acumulativa), mas é always-LLM e perde em orçamentos longos. Para prompt stateless (nosso caso), o padrão HybridMonkey é o compatível.

## 3. Sampling e modelos pequenos: lacunas genuínas da literatura (= nossas contribuições possíveis)

- **NENHUMA das 24 afirmações verificadas reporta calibração de temperature/top_p/top_k para exploração de GUI.** As duas únicas menções a sampling em todo o corpus: AutoDroid fixa **temperature=0,25** ("creativity sem randomness excessiva", sem estudo); surveys de 2024 confirmam zero estudos sistemáticos. **Calibrar sampling para exploração é lacuna publicável.**
- **Recomendação oficial do vendor** (repo QwenLM/Qwen3-VL): para modelos **Instruct** (inclui o 4B): **temperature=0,7, top_p=0,8, top_k=20**; para Thinking: 0,6/0,95/20. Nota: nossos defaults atuais no jar (0,3/0,6/50) e o temperature=0 do cmp_llm_20260721 **divergem ambos** da recomendação do vendor — o sweep precisa incluir o ponto vendor.
- **Nenhuma ferramenta verificada valida modelo ~4B on-prem.** Todas usam APIs GPT-3.5/4/4o/5-mini/Claude. Datapoints mais próximos: LLM-Explorer com Vicuna-13B AWQ 4-bit numa RTX 3090 teve quedas *leves* de cobertura (modo de falha: formatos incorretos, IDs inválidos) — sugerindo que papel de **manutenção de conhecimento** é o mais amigável a modelo pequeno; LLMDroid com modelo barato atinge 78% do ótimo a $0,18/h. Qwen3-VL-4B (out/2025, FP8 disponível) é viável em GPU 16GB, com cookbook oficial de Mobile Agent — mas eficácia no papel de tarpit-escape é **não testada** na literatura.
- **Detecção de violações RV**: nenhuma fonte verificada mede rendimento de violação de propriedade (nosso `mop_unique`) sob exploração LLM-guiada. PropGen (2026, preprint) é o vizinho mais próximo — LLM **gera** propriedades (25 bugs novos), mas não é spec-checking. **cov_mop não tem baseline publicado** — contribuição direta do APE-RV.

## 4. Ferramentas novas (não cobertas pela survey interna 20260313)

| Ferramenta | Ano/venue | O que é | Relevância p/ APE-RV |
|---|---|---|---|
| **HybridMonkey / HybridDroidbot** | ASE 2026 (peer-reviewed) | Random/model-based + LLM só em tarpit (pHash θ=0,95, k=8); cache de escapes reutilizado p=0,8 | **O mais próximo do nosso desenho-alvo.** Gatilho de estagnação + cache = padrão a adaptar no routing do APE-RV |
| **CovAgent** | 2026 preprint | LLM escreve scripts Frida para alcançar activities que o fuzzer não atinge (code-as-action) | Braço APE: CovAgent-APE 49,5% vs APE 17,7% — mas invasivo (Frida) e API proprietária |
| **EpiDroid** | 2026 preprint | Plugin black-box de sparse-calling sobre Fastbot etc.; Semantic-UTG por cluster + recomposição/replay | Arquitetura plugin (não muda a tool base) — análogo ao nosso substrate MOP |
| **PropGen** | 2026 preprint | Exploração guiada por funcionalidade + LLM sintetiza propriedades (GPT-5.2, ~$14,86/app) | RV-adjacente (geração de spec). **NÃO é Set-of-Marks** — afirmação refutada na verificação (1-2); representação é textual |
| **UI-TARS-2** | set/2025 tech report | Sucessor do UI-TARS; AndroidWorld 73,3 | Referência de teto para agentes end-to-end; não é ferramenta de teste |

Status de peer-review: HybridMonkey (ASE'26), LLMDroid (FSE'25), LLM-Explorer (MobiCom'25), AutoDroid (MobiCom'24), GUI-Actor (NeurIPS'25) revisados; CovAgent/EpiDroid/PropGen/UI-TARS-2 são preprints com benchmarks auto-reportados, sem replicação independente. Todos os resultados de cobertura são self-benchmarks em datasets curados.

## 5. Confirmações/correções à survey interna (20260313)

- Venues/anos confirmados para GPTDroid (Q&A sobre view-hierarchy→texto, +32% activity), AutoDroid (MobiCom'24, HTML simplificado + índice), LLM-Explorer (MobiCom'25), LLMDroid (FSE'25), QTypist (cloze fill-in-blank, +52% coverage), GUI-Actor (NeurIPS'25).
- **Correção**: GPTDroid **não** é stateless — o prompt codifica contexto estático da página + contexto dinâmico do processo iterativo (memória funcional). A survey interna já apontava isso; confirmado na fonte.
- **Correção de terceiros**: não descrever PropGen como SoM-based (refutado).
- CovAgent corrobora o "teto de ~30% de activity coverage" das tools SOTA em apps industriais (estudo de Akinotcho et al., 103 apps).

## 6. Playbook verificado para o APE-RV (síntese)

1. **APE continua primário; LLM dispara só em plateau/estagnação** — 5 ferramentas independentes confirmam que este é o único regime em que LLM ganha do algorítmico no mesmo orçamento de tempo. (→ eixo routing da calibração: `llm_percentage` baixo, `llm_on_stagnation`.)
2. **Escolha por índice numerado é o consenso da literatura, mas foi deliberadamente descartada no APE-RV**: as tools SOTA tratam o dump da hierarquia como verdade completa; o aperv usa VLM multimodal justamente para tocar elementos dinâmicos que **não aparecem** no dump do UIAutomator (saída por coordenada + tap off-tree `llm_tap`). Restringir a escolha ao dump eliminaria esse diferencial. O desperdício de no-match/parse é atacado por robustez de formato e snapping, mantendo coordenadas (plano de calibração, H4).
3. **Memória local mínima, stateless-friendly** — tentativas falhas do plateau atual, não trace global. Compatível com o requisito 4B/16GB. (→ variante history-aware compacta.)
4. **Cache de decisões de escape reutilizado (p≈0,8)** — corta chamadas repetidas ao LLM no mesmo estado. (→ candidato futuro; muda o jar.)
5. **Sampling**: partir da recomendação vendor (0,7/0,8/20) e do temperature=0,25 do AutoDroid como pontos do sweep; a literatura não responde — medir in-house. (→ eixo sampling.)
6. **Gatilho de estagnação**: growth-rate de cobertura (LLMDroid) vs similaridade perceptual (HybridMonkey) — nenhum estudo compara; **o sinal MOP do APE-RV pode definir um gatilho RV-específico inédito**. (→ hipótese H6, rodada futura.)

## 7. Questões abertas (da verificação adversarial)

1. Calibração de sampling para diversidade de exploração vs validade de ação — lacuna real; explorável e publicável.
2. Transferência dos ganhos de selective-routing para VLM 4B on-prem — não testada; o papel "knowledge-maintenance-only" (LLM-Explorer) é o mais 4B-friendly.
3. Gatilho ótimo de estagnação/tarpit — nenhuma comparação publicada; sinal MOP como gatilho é inédito.
4. LLM-guidance melhora detecção de violações RV além do que o ganho de cobertura prevê? — sem baseline publicado; `cov_mop`/`mop_unique` do APE-RV podem ser a primeira medição.

## 8. Fontes (20, deduplicadas; qualidade primária salvo indicação)

- LLMDroid: https://dl.acm.org/doi/pdf/10.1145/3715763 (FSE 2025) + repo https://github.com/LLMDroid-2024/LLMDroid
- HybridMonkey/HybridDroidbot (tarpit escaping): https://arxiv.org/abs/2604.06763 (ASE 2026)
- LLM-Explorer: https://arxiv.org/pdf/2505.10593 / https://dl.acm.org/doi/10.1145/3680207.3723494 (MobiCom 2025)
- CovAgent: https://arxiv.org/pdf/2601.21253
- EpiDroid: https://arxiv.org/pdf/2604.01522
- PropGen: https://arxiv.org/html/2604.13463
- UI-TARS-2: https://arxiv.org/abs/2509.02544
- GUI-Actor: https://arxiv.org/abs/2506.03143 (NeurIPS 2025)
- AutoDroid: https://dl.acm.org/doi/10.1145/3636534.3649379 (MobiCom 2024)
- GPTDroid (TSE 2024 / ICSE 2024): via https://www.semanticscholar.org/paper/f43b8a87a96f8abc2467b90538b643a6061416e9
- Survey TMLR "LLM-Powered GUI Agents in Phone Automation": https://arxiv.org/html/2504.19838v2 + lista companion https://github.com/PhoneLLM/Awesome-LLM-Powered-Phone-GUI-Agents (secundárias)
- Survey "Software Testing with LLMs" (102 estudos): idem Semantic Scholar
- Custo texto vs multimodal (DailyDroid): https://arxiv.org/pdf/2604.17817
- Qwen3-VL oficial (sampling recomendado, 4B/FP8, SGLang, Mobile-Agent cookbook): https://github.com/QwenLM/Qwen3-VL
- Demais: https://arxiv.org/html/2411.18279v12 (secundária)
