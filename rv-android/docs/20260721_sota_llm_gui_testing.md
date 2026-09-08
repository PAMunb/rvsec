# SOTA verificado: teste de GUI Android guiado por LLM/VLM (2023–2026)

**rev. 2 de 2026-07-29** — acrescenta duas famílias que a rev. 1 não cobria: (i) **teste dirigido a alvo** (§7, novo: GoalExplorer, Guardian, ADGE, Mole, Agent+P, GAPS) — a família tecnicamente mais próxima do que o APE-RV faz; (ii) **desenho de prompt com fonte primária** (§8, novo: prompts literais do Guardian lidos no paper *e* no código do artefato, mais tabela comparativa de 7 ferramentas). A rev. 1 organizava todo o SOTA no eixo "quando chamar o LLM para escolher a ação", o que subrepresentava regimes em que a latência não é o problema — corrigido em §7/§8. Duas correções de citação em §5.

**Data**: 2026-07-21
**Método**: deep-research multi-agente (5 ângulos de busca × 20 fontes × 100 afirmações extraídas → 25 verificadas adversarialmente por 3 votos independentes cada: **24 confirmadas, 1 refutada**). Complementa e atualiza a survey interna `docs/20260313_comparacao_tools_recentes.md`.
**Uso (decisão do usuário, 2026-07-29): este documento é fonte de IDEIAS para melhorar o APE-RV — não fonte de comparadores.** Nenhuma ferramenta aqui entra no experimento; o conjunto de comparação é o do `ase-journal` sem acréscimos (ver `docs/20260729_contexto_pesquisa_e3.md` §6-bis). Cada melhoria adotada deve citar a seção correspondente daqui, ser implementada e ter o efeito medido.

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
- **Formato de ação dominante**: template restrito **índice-do-widget + tipo-de-ação** (AutoDroid fill-in-the-blank; HybridMonkey igual). **Nenhuma ferramenta verificada emite coordenadas cruas** — confirma a conclusão da survey interna (`20260322_aperv_tuning.md`) de que a abordagem de coordenadas do APE-RV é sem precedentes e é a fonte estrutural do no-match. **rev. 2**: agora com 7 ferramentas verificadas em fonte primária (§8.5) — o DroidAgent **apaga `bounds` do JSON de propósito**, o GPTDroid colapsa coordenada para `upper`/`lower`, e o VisionDroid usa `bounds` só para *desenhar* as caixas numeradas. O APE-RV está sozinho nesse desenho.
- **Custo do multimodal**: no benchmark DailyDroid (75 tasks, GPT-4o/o4-mini), adicionar screenshot ao texto da UI-tree rende só +4–5,7% de sucesso por **25–26× o custo** — texto-apenas é o default custo-efetivo. (⚠️ **rev. 2** — a rev. 1 concluía daqui que "um prompt textual índice-numerado pode dispensar a imagem, cortando prefill". Isso está **descartado**: seleção por lista foi decidida como fora do escopo (§6, item 2), e os dados internos mostram que aterrar visualmente rende o dobro de copiar da lista. O achado aproveitável é outro e continua válido: **o prefill da imagem domina o custo** — atacá-lo é questão de resolução/qualidade do screenshot, não de trocar o espaço de ação.)
- **Grounding sem coordenadas em VLMs**: GUI-Actor (NeurIPS 2025) substitui geração de string de coordenada por action head de atenção; GUI-Actor-7B supera UI-TARS-72B em ScreenSpot-Pro (44,6 vs 38,1) — modelo pequeno com mecanismo de grounding melhor vence modelo 10× maior gerando coordenada. **⚠️ rev. 2: inviável no nosso stack** — exige hidden states que nem SGLang nem vLLM expõem, e não há backbone Qwen3-VL (§6).
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
| **Guardian** | **ISSTA 2024** (peer-reviewed) | Runtime que *restringe* o LLM: espaço de ações refinado por subtração + replanejamento passo a passo. Zero análise estática | **A referência de desenho de prompt** — ver §8. Prompts literais disponíveis no artefato |
| **GAPS** | arXiv 2511.23213 (v1 nov/2025, v3 jul/2026; **preprint, não revisado**) | Travessia reversa de call graph (Androguard/smali, CHA sob demanda) → plano de interação GUI executável; LLM como fallback | Concorrente direto no eixo "estático guia dinâmico" — ver §7 |

Status de peer-review: Guardian (ISSTA'24), HybridMonkey (ASE'26), LLMDroid (FSE'25), LLM-Explorer (MobiCom'25), AutoDroid (MobiCom'24), GUI-Actor (NeurIPS'25) revisados; CovAgent/EpiDroid/PropGen/UI-TARS-2/GAPS são preprints com benchmarks auto-reportados, sem replicação independente. Todos os resultados de cobertura são self-benchmarks em datasets curados.

## 5. Confirmações/correções à survey interna (20260313)

- Venues/anos confirmados para GPTDroid (Q&A sobre view-hierarchy→texto, +32% activity), AutoDroid (MobiCom'24, HTML simplificado + índice), LLM-Explorer (MobiCom'25), LLMDroid (FSE'25), QTypist (cloze fill-in-blank, +52% coverage), GUI-Actor (NeurIPS'25).
- **Correção**: GPTDroid **não** é stateless — o prompt codifica contexto estático da página + contexto dinâmico do processo iterativo (memória funcional). A survey interna já apontava isso; confirmado na fonte.
- **Correção de terceiros**: não descrever PropGen como SoM-based (refutado).
- CovAgent corrobora o "teto de ~30% de activity coverage" das tools SOTA em apps industriais (estudo de Akinotcho et al., 103 apps).
- **rev. 2 — correções de citação**: **GoalExplorer é ASE 2019** (Lai & Rubin, pp. 115–127), não ISSTA/TOSEM. **Guardian é ISSTA 2024** (Ran et al., pp. 958–970, DOI `10.1145/3650212.3680334`).
- **rev. 2 — viés de enquadramento da rev. 1**: o documento organizava o SOTA inteiro no eixo "quando chamar o LLM para escolher a próxima ação", o que naturaliza always-LLM/selective-routing e subrepresenta regimes em que o LLM **não escolhe ação nenhuma** (LLM-Explorer: só funde estados abstratos, ação é sorteada; EpiDroid: sumarização + replay; QTypist/InputBlaster: só geram texto de entrada; PropGen: gera specs offline). O §6 herdava o viés — 5 de 6 itens eram sobre routing/sampling. Corrigido em §7/§8.

## 6. Playbook verificado para o APE-RV (síntese)

1. **APE continua primário; LLM dispara só em plateau/estagnação** — 5 ferramentas independentes confirmam que este é o único regime em que LLM ganha do algorítmico no mesmo orçamento de tempo. (→ eixo routing da calibração: `llm_percentage` baixo, `llm_on_stagnation`.)
2. **Escolha por índice numerado é o consenso da literatura, e a rev. 1 descartou a opção cedo demais.** A justificativa original: as tools SOTA tratam o dump da hierarquia como verdade completa; o aperv usa VLM multimodal justamente para tocar elementos dinâmicos que **não aparecem** no dump do UIAutomator (saída por coordenada + tap off-tree `llm_tap`), e restringir a escolha ao dump eliminaria esse diferencial. **rev. 2 — a justificativa mistura dois problemas distintos, mas a ressalva do dump é REAL e não se resolve numerando.** Precisão necessária: as caixas numeradas do VisionDroid são desenhadas a partir dos `bounds` **do próprio dump** — numerar muda o *formato de referência* aos mesmos elementos, não o *alcance*. Qualquer esquema `index-N` sobre uma lista derivada do dump exclui, por construção, exatamente os elementos off-dump que motivam o `llm_tap`. E o Guardian, a referência de §8, é **text-only sobre `dump_hierarchy()`** — ele nunca teve o problema de alcance que temos.

**⚠️ CORREÇÃO (2026-07-29) — Set-of-Mark visual está VETADO para modelos deste porte.** Uma redação anterior desta seção recomendava o desenho do VisionDroid (screenshot com caixas numeradas). Cinco fontes independentes mostram que overlay de marcas **quebra** justamente modelos pequenos e grounding-tuned: `[WEB]` arXiv 2509.11548 leva **Qwen2-VL-7B de 47,56 → 28,38 (−19 pp)** com mark-grid — e é o único modelo grounding-tuned da tabela, da mesma família do nosso; MobiBench mostra SoM+a11y perdendo para Raw+a11y nos três tamanhos, com o gap **crescendo** conforme o modelo encolhe; Contrastive Region Guidance (2403.02325) mede −16,2% em LLaVA-13B e conclui que *"SoM does not transfer well to open-source VLMs"*; SoM-LLaVA (2404.16375) diagnostica a capacidade ausente — o modelo lê a tag e reconhece o objeto mas **não associa tag↔objeto**; OSWorld mede GPT-4o caindo pela metade (11,21 → 4,59). **Se quisermos índices, eles vão em texto, nunca em pixels.**

**⚠️ GUI-Actor também está inviável no nosso stack.** `[WEB]` Ele consome os hidden states do token `<actor>`; a mantenedora registra na issue #17 que *"vLLM doesn't support returning hidden states out-of-the-box"*, e a issue #22 (SGLang) segue aberta sem plano. Não há backbone Qwen3-VL, e a variante de backbone congelado rende 22,9 vs 40,7 no ScreenSpot-Pro.

**⚠️ DECISÃO DO USUÁRIO (2026-07-29) — seleção por lista está DESCARTADA e não será re-tentada.** Uma versão anterior do rv-android já implementou exatamente isso: o LLM escolhendo apenas de uma lista de opções montada pelo sistema. O código está preservado como histórico em `backup/rv-llm/src/rv_llm/` e `backup/rvandroid/llm/`, fora do sistema atual. A abordagem foi abandonada; não voltaremos a ela. **Portanto `select_index(N)` sai do espaço de desenho**, e com ele qualquer variante "índice sobre lista derivada do dump".

Isso é coerente com o que os próprios dados dizem (relatório `20260724` §12-bis.9): entre as emissões que **copiam** um centro da lista impressa no v13, o rendimento é **14,89%**; entre as que **aterram visualmente** (3–15 px de um centro), é **31,61%** — o dobro. A lista leva o modelo a contêineres (`ScrollView`, `ViewPager`, `View` genérico, cujo centro é espaço morto); olhar a tela o leva a botões. **Empurrar o modelo para a lista pioraria a decisão.**

O que sobrevive desta seção, então, não é o formato de saída — é o resto do desenho do Guardian, que é **ortogonal ao espaço de ação** e onde estão os ganhos reais (§8.3, §8.4): impedir `click` em `EditText`, separar "onde" de "o que digitar" em duas chamadas, e sobretudo **restringir por subtração em vez de por instrução**. E a curadoria da lista continua valendo como melhoria de *prompt* — hoje ela entrega poluição de contêineres sem entregar o sinal MOP que deveria justificá-la (`[DM]/[M]` ~98% vazio).

**MEDIDO (2026-07-29, teste T7 — ver §12-bis do relatório `20260724`).** O rendimento do tap off-tree foi medido contra um contrafactual pareado (os `no_match`, que devolvem o turno ao algoritmo **no mesmo passo, na mesma tela, pelo mesmo gatilho**):

| grupo | n | `new_state` | `activity_changed` | ação sem efeito |
|---|---|---|---|---|
| `matched` (LLM escolhe alvo do dump) | 26.466 | **17,1%** | 9,4% | 45,6% |
| **`llm_tap`** (tap off-tree por coordenada) | 4.606 | **7,4%** | **1,7%** | **65,7%** |
| `no_match` → algoritmo (contrafactual) | 6.644 | **16,3%** | 9,0% | 39,6% |
| algorítmico puro | 83.934 | 9,3% | 8,2% | 46,9% |

**Duas leituras, e é essencial não confundi-las:**
1. **A escolha de alvo pelo LLM tem valor real** — `matched` 17,1% contra 9,3% do algoritmo puro (36,1% vs 27,6% no modo new-state). Isso valida o uso do LLM como seletor.
2. **A codificação como coordenada crua com execução off-tree não se paga** — 7,4% contra 16,3% do contrafactual, ICs disjuntos, pior em 28/31 APKs (p=4,6e-6), yield plano por distância, e perdendo **justamente em telas de dump pobre** (0–2 widgets: 9,1% vs 14,6%). O gradiente de "sem efeito" é invertido (84% perto do widget vs ~50% longe), assinatura de erro de mira, não de descoberta. E o braço com 48% mais `llm_tap` (A9/v17) rende **menos** — a taxa de `llm_tap` é **métrica de erro de aterrissagem, não de alcance**.

Consequência para o playbook: a premissa do plano de calibração §1 ("saída por coordenada é inegociável porque o `llm_tap` é o diferencial") **não é sustentada por este corpus**. O alcance a elemento dinâmico permanece como **requisito de projeto** (decisão do usuário, 2026-07-29) — mas o mecanismo atual não o entrega, e precisa de intenção declarada + verificação pós-toque + aprendizado com o fracasso, nenhum dos quais existe hoje. Ver §12-bis.6 do relatório.

**Ação imediata identificada, sem rebuild**: 43,6% dos `llm_tap` estão a <150 px de um widget e renderiam ~3× mais se snapados (16,1–18,3% como `matched CLICK` vs 5,1–6,5% como tap cru). `ape.llmSnapTolerancePx` já está exposto (`Config.java:223`) e mapeado (`tool.py:161`).
3. **Memória local mínima, stateless-friendly** — tentativas falhas do plateau atual, não trace global. Compatível com o requisito 4B/16GB. (→ variante history-aware compacta.)
4. **Cache de decisões de escape reutilizado (p≈0,8)** — corta chamadas repetidas ao LLM no mesmo estado. (→ candidato futuro; muda o jar.)
5. **Sampling**: partir da recomendação vendor (0,7/0,8/20) e do temperature=0,25 do AutoDroid como pontos do sweep; a literatura não responde — medir in-house. (→ eixo sampling.)
6. **Gatilho de estagnação**: growth-rate de cobertura (LLMDroid) vs similaridade perceptual (HybridMonkey) — nenhum estudo compara; **o sinal MOP do APE-RV pode definir um gatilho RV-específico inédito**. (→ hipótese H6, rodada futura.)
7. **rev. 2 — restrição por subtração, não por instrução** (§8.4): banir `(ação, estado)` removendo a ação do espaço apresentado, em vez de contar ao modelo o que ele já fez. O paper do Guardian mede o custo da alternativa: 36% de violação mesmo com instrução explícita — e um modelo 4B viola mais. Ablação: −28,5% de SR sem esse mecanismo, e transplantá-lo para um baseline dobra o resultado (+100%).
8. **rev. 2 — `EditText` não deve oferecer `click`** (§8.3): remover `click` do widget e oferecer só `text`; gerar o conteúdo numa **segunda** chamada. Ataca diretamente o colapso `type_text ≈ 0` medido em todos os braços da calibração (§8 do relatório `20260724`).
9. **rev. 2 — resposta inválida deve virar ação legal** (§8.2): índice fora do intervalo → `back()`, não exceção nem descarte de turno. Contraste com o APE-RV atual, em que `no_match` devolve o turno ao algoritmo (o que tem a vantagem colateral de preservar o fallback de alto rendimento — ver *fallback starvation*).

## 7. Teste dirigido a alvo (*directed / targeted GUI testing*) — trabalho relacionado

> **Escopo (decisão do usuário, 2026-07-29): esta família entra como TRABALHO RELACIONADO, não como comparação.** Não haverá contraste experimental com GAPS, GoalExplorer ou congêneres. O que segue é levantamento para situar a literatura e para redação de related work — não é baseline nem alvo a bater.

Ausente da rev. 1. É a linhagem que traduz um **alvo estático** (activity, método, statement) em **guia dinâmico**, e é onde o APE-RV de fato compete — não no eixo "cobertura genérica".

| Trabalho | Venue | Alvo | Como vira decisão | LLM? |
|---|---|---|---|---|
| **AFLGo** / **Hawkeye** | CCS'17 / CCS'18 | statement / função (binário) | *distância ao alvo* como fitness do fuzzer | não |
| **GoalExplorer** | **ASE 2019** | activity, chamada de API, statement | **pathfinding na Screen Transition Graph** → script replayável | não |
| **Mole** | TSE 2024 | — | — | — |
| **Guardian** | **ISSTA 2024** | objetivo em linguagem natural | LLM escolhe 1 ação/passo sobre espaço **refinado por subtração**; replanejamento a cada passo | sim (central) |
| **ADGE** | ICST 2025 | — | — | — |
| **Agent+P** | 2025 (arXiv) | — | planejamento simbólico guiando agente de UI | sim |
| **GAPS** | arXiv 2511.23213 (preprint) | método arbitrário | travessia **reversa** de call graph → plano de interação GUI executável | sim (fallback) |

**Observação factual sobre a família, que vale registrar: todos param em "o alvo foi alcançado"; nenhum verifica uma propriedade.** O GAPS confirma o hit com hook Frida ("o método executou"); o GoalExplorer, com o disparo do alvo. A distância entre isso e "a propriedade `CipherSpec` foi violada com estes parâmetros neste caminho" é o oráculo de RV — e nenhum trabalho desta família o tem.

⚠️ **Isto é um fato sobre a literatura, não uma decisão de posicionamento.** As questões de pesquisa do estudo E3 (APE-RV) **não existem ainda** — confirmado em disco: sem capítulo na tese, sem RQ no ledger (só um Requirement-placeholder em `openspec/specs/estudo-ape-guiado/spec.md`), sem menção no PRD. Uma redação anterior desta seção sugeria um "reposicionamento da contribuição da tese"; **foi retirada** por ser invenção deste documento, não achado. Ver `docs/20260729_contexto_pesquisa_e3.md`.

### 7.1 GAPS — leitura crítica (o trabalho tecnicamente mais próximo)

*Detalhado porque é o mais recente e o mais próximo em mecanismo; e porque números incorretos dele circulavam internamente. **Não é comparação** — ver a nota de escopo da §7.*

**Números corretos, e eles não são os que circulam.** Os **88,24%** frequentemente citados são **reconstrução estática de caminho** ("a ferramenta produziu ao menos um caminho contendo o alvo"), comparados contra FlowDroid 58,81% e DroidReach 9,48%. O número **dinâmico** — o único comparável a APE/Guardian — é **56,93%** (v3). E os valores mudaram muito entre versões:

| | v1 (nov/2025) | v3 (jul/2026) |
|---|---|---|
| GAPS dinâmico | 57,44% | **56,93%** |
| **Guardian** (baseline LLM) | 17,12% | **34,00%** |
| APE | 12,82% | 11,12% |
| GoalExplorer | 9,69% | 4,75% |

A vantagem sobre o melhor baseline é **1,67×**, não 7×. **Se citar, use a v3 e separe sempre o número estático do dinâmico.**

**A ablação inverte a narrativa do título.** GAPS **sem** o componente LLM (o "PHIL", fallback agêntico limitado a 1 invocação por Activity) alcança **23,24%** — **abaixo** do Guardian (34%), que é LLM puro sem análise estática nenhuma. Mais da metade do resultado vem do LLM. O trabalho se chama "via Static Path Reconstruction" mas o resultado é majoritariamente híbrido. **GAPS não é evidência de que "estático sem LLM vence LLM"; é evidência a favor de arquitetura híbrida.**

**O que é sólido**: alvos = 50 métodos **aleatórios, fixos, idênticos entre todas as ferramentas e execuções** (bom desenho, refuta a suspeita de alvos escolhidos pelo método); métrica dinâmica rigorosa (instrumentação `AndroLog` por método / hooks Frida — "o método executou", não "chegou na tela").

**O que é frágil**: **AndroTest é o benchmark de 2015** (apps de 2012–2014: sem login, sem rede, sem permissões de runtime, sem Compose), e usam 56 dos 68 apps sem justificar quais 12 saíram; **o APE é usado como baseline de tarefa dirigida sendo que o APE não aceita alvos** (nenhuma flag reportada); GoalExplorer com build quebrado admitido pelos autores; **zero análise de precisão estática** (88,24% de recall, nada sobre falsos positivos — e a CHA sob demanda é sobre-aproximada: mediana da cadeia = **2 chamadas**, quase trivial); ambiguidade não resolvida sobre o orçamento do GAPS (3:15 por app ou por alvo?); sem seção de threats to validity, sem estatística inferencial; **artefato 404**; modelo citado como "GPT-5.4" sem versão nem data. Hawkeye/AFLGo/directed fuzzing **não são mencionados** no related work.

**Nota sobre Compose**: o GAPS declara verbatim que *"Jetpack Compose ... remains an open research problem"* — útil como citação de related work para atestar que a limitação é reconhecida na literatura, não uma idiossincrasia deste projeto. Independentemente disso, o corpus **deste** projeto é contemporâneo (219 apps, 64,8% com Compose) e o custo da cegueira do substrato estático é mensurável nele — ver `docs/20260729_contexto_pesquisa_e3.md` §5. Se isso vira sub-questão do E3 é decisão em aberto.

## 8. Desenho de prompt: o Guardian como referência (fonte primária: paper + código do artefato)

O Guardian é a referência mais útil da literatura para o nosso problema porque sua tese é: **não confie na obediência do modelo; mova a restrição para o harness.** Ele levou o GPT-3.5 de 6,9% (DroidBot-GPT) a **48,3%** de success rate no mesmo modelo — 7× de ganho vindo puramente do runtime.

**Ressalva de artefato**: o código publicado (`PKU-ASE-RISE/Guardian`, Apache-2.0) é uma refatoração incompleta — a reflexão via LLM (`llm_reflection`) está comentada e `restore_state`/`block_failed_action` são stubs. **Os prompts, esses, são literais e confiáveis.**

### 8.1 Como o Guardian representa a GUI

Texto puro, **nunca screenshot** (o modelo é text-only). Pipeline: `dump_hierarchy()` → filtro `isInteractable` (só `clickable`/`scrollable`/`EditText` visível) → filtro de pacote → **`setActualClickable`** (quando um wrapper clicável tem >2 filhos, o clicável é *rebaixado* para os filhos, concatenando `resource-id`/`content-desc` do pai — resolve listas em que só o container é clicável) → **`rewriteDescription`** (widget clicável sem texto herda o texto do 1º descendente que tenha).

Renderização de cada item: `a View ({descrição}) to {ação}`, onde a descrição junta só o que existe: `accessibility information: …`, `resource_id {último segmento}`, `text: …`.

**Atributos que nunca chegam ao LLM**: `class`, `bounds`/coordenadas, `package`, `checked`, `enabled`, e a estrutura de árvore. A lista é **plana**. Itens que renderizariam `"a View () to click"` (descrição vazia) são **descartados** — o modelo nunca vê widget anônimo.

### 8.2 O formato de saída — descrito para registro, **NÃO transferível para o APE-RV**

> **Leia primeiro**: a seleção por índice sobre lista está **descartada por decisão do usuário** (2026-07-29) — já foi implementada e abandonada numa versão anterior do rv-android (`backup/rv-llm/`, `backup/rvandroid/llm/`). E os dados internos apontam na mesma direção: copiar da lista rende metade de aterrar visualmente (§6, item 2). O que segue documenta o desenho do Guardian **para referência de literatura**, não como recomendação.

**`index-N` sobre pares (widget, ação). Nunca coordenada.** Três consequências de desenho que valem separadamente:

1. **A unidade enumerada é o par (widget, ação), não o widget.** Um widget clicável e scrollável aparece **duas vezes**: `... to click` e `... to swipe`. **O tipo da ação é escolhido implicitamente pelo índice** — não existe um campo "ação" separado que o modelo possa colapsar.
2. **A coordenada é calculada pelo runtime**, do centro do `bounds`. O LLM nunca vê nem produz um pixel.
3. **Parsing por regex com validação de domínio**: itera sobre as ocorrências de `index-`, aceita a primeira cujo inteiro caia em `range(len(events))`; se nada válido → **`back()`**. O fallback é uma **ação legal**, não uma exceção.

### 8.3 Os quatro mecanismos que atacam o colapso de política

1. **Não existe campo "ação" para colapsar** (item 1 acima). Um esquema `{action: "click"|"type_text", x, y}` tem prior fortíssimo em `click`, porque `click` é o token mais provável naquele slot. O Guardian **remove o slot**.
2. **`fixTextEdit`: em `EditText`, a ação `click` é literalmente removida e substituída por `text`.** O modelo é *impedido* de clicar numa caixa de texto.
3. **"Onde" e "o que digitar" são chamadas separadas.** Pedir localização e conteúdo na mesma resposta penaliza `type_text` (resposta mais longa, mais formatos para errar) e enviesa para a ação de saída curta.
4. **Empurrão de política explícito**: todo widget scrollável recebe a string fixa `accessibility information: scroll to see more options(very useful!)`. Grosseiro, mas é precedente honesto de desenviesar uma ação específica sem tocar no modelo.

### 8.4 Restrição por subtração, não por instrução

O histórico do Guardian **age removendo ações do espaço**, não adicionando contexto ao prompt. No artefato publicado, o histórico **não entra no prompt de forma alguma** — existe só como `bannedEvents`. O paper mede o custo da alternativa: o DroidBot-GPT, instruído explicitamente a não repetir, **repete em 36% das ações**. Camadas: anti-repetição por `(ação, estado)`; anti-loop por **Jaccard > 0,8** sobre hashes de widgets (ignorando `text`); anti-saída do app; escape de deadlock (se sobrar <2 ações, limpa todos os bloqueios da tela).

**Ablações do paper — as duas contribuições são separáveis, grandes e *portáveis*:** sem refinamento do espaço de ações −28,5% SR; sem replanejamento −32,1%; e transplantadas para o baseline, `Refine-Droidbot` 6,9→13,8 (+100%) e `Replan-Droidbot` 6,9→19,0 (+175%).

**Onde o Guardian falha é onde nós somos fortes**: 56,7% das falhas residuais vêm de ícone/`ImageButton` sem informação de acessibilidade — o modelo não tem como saber o que é. **Temos a modalidade que faltava a ele**, e os dados internos confirmam que a usamos bem: aterrar visualmente rende 31,61% contra 14,89% de copiar da lista (§6, item 2). ⚠️ Uma redação anterior propunha aqui o desenho do VisionDroid (set-of-mark + lista numerada, saída `index-N`); **isso está duplamente vetado** — o SoM quebra modelos pequenos (§6) e a seleção por lista foi descartada por decisão do usuário, já tendo sido implementada e abandonada antes (`backup/rv-llm/`). O caminho aberto para o APE-RV é **manter a saída visual e atacar a repetição e a curadoria do contexto**, não trocar o espaço de ação.

### 8.5 Tabela comparativa: representação da GUI × formato de saída (7 ferramentas, fonte primária)

| Ferramenta | Representação da GUI | Formato de saída | CoT / few-shot | Modelo · chamadas |
|---|---|---|---|---|
| **Guardian** (ISSTA'24) | Lista plana numerada, só interativos; sem class/bounds/árvore; atributos filtrados por relevância via LLM | **`index-N`**, regex + validação de intervalo; `index-none` → `back()` | Paper pede "first think"; código não. Sem few-shot, sem JSON, sem tool-call | GPT-3.5, T=0,2 · **3–4 calls/passo** |
| **DroidBot-GPT** | Lista NL numerada; texto cortado em 20 chars | **Inteiro puro**; parse falha → **ação aleatória** | Nenhum (CoT suprimido) | GPT-3.5 · 1 call/passo |
| **AutoDroid** (MobiCom'24) | **HTML simplificado**, 5 tags; merge de folhas (625→339 tokens) | **JSON com índice**; `id=-1` = fim | CoT zero-shot dentro do JSON | GPT-3.5/4, Vicuna-7B FT · 1 call/passo |
| **LLMDroid** (FSE'25) | HTML simplificado; mantém class + resource-id; ≤100 tags, corte em 7.000 chars | **JSON id + código numérico de ação** | Sem CoT, T=0 | GPT-4o · **0 calls no caminho crítico** |
| **DroidAgent** (ICST'24) | JSON aninhado; **bounds e class deletados explicitamente**; cap 15.000 chars | **Function calling** com `enum` de IDs legais por tela | CoT em chamada separada | GPT-4 + GPT-3.5-16k · ~3 calls/ação, **$18/app** |
| **VisionDroid** (TSE'25) | **Screenshot com set-of-mark**: caixas coloridas por tipo de ação, numeradas | `([Widget ID] + [Action] + [Widget text])` — divergência ID×texto dispara re-pergunta | **Few-shot por recuperação** + CoT | `gpt-4-vision-preview` · ~1 call/passo |
| **GPTDroid** (ICSE'24) | **Prosa em linguagem natural** por template; coordenada reduzida a `upper`/`lower` | NL com template inline | Pseudo-CoT | GPT-3.5 · 1 call/passo |

**Duas observações transversais:**

- **Nenhuma das sete pede coordenada ao LLM.** O APE-RV, pedindo `[0,1000)` normalizado, está sozinho nesse desenho.
  **⚠️ CORREÇÃO (2026-07-29) — os "84,2% de hit rate" citados aqui na rev. 2 foram RETIRADOS: o número não é verificável.** O documento-fonte, `docs/20260107_rvagent_validacao_multimodal.md`, **não existe no repositório e o git não tem registro de ele jamais ter sido adicionado ou removido em nenhuma branch** — é citação fantasma, propagada por 9 arquivos incluindo o `CLAUDE.md`. Pior: o número é descrito de três formas mutuamente incompatíveis — "hit rate da conversão `[0,1000)`" (`CLAUDE.md:162`), "taxa de interação efetiva, **maior** que o benchmark porque produção usa seleção UIAutomator, **explicitamente não comparável**" (`VISION.md:976`), e "hit rate na denormalização, um teto de ~16% de perdas" (a redação que eu mesmo escrevi aqui). E a `VISION.md` §13.2 afirma que sob seleção o hit rate "aproxima-se de 100%", o que torna 84,2% inconsistente com a própria explicação que ela oferece.
  **O número medido e rastreável é outro: 57,7% de hit rate** — Qwen3-VL-4B, SGLang bf16, modo `visual_only` (nenhuma coordenada no prompt), 468 screenshots / 28 APKs / 812 elementos / 3 reps = 2.847 testes, hit = ≤50 px do centro do bounds do UIAutomator (`docs/vision/017_full_benchmark_results.md`, `018_benchmark_methodology.md`). Trajetória: 3,6% (antes da denormalização) → ~50% (com a convenção `[0,1000)`) → 67,1% (preliminar, 150 ss) → **57,7%** (completo).
  Cuidado ao pesquisar: há pelo menos quatro "84,2%" **não relacionados** no repositório (tool call rate de `RelativeLayout` em `docs/vision/011`, progresso de execução em `experimento-20260706/MONITORAMENTO.md`, e a fração de taps perto de widget sem efeito em `20260724` §12-bis.2 — esta última é medição legítima desta campanha e nada tem a ver com grounding).
- **Só o DroidAgent usa tool-calling de verdade**; os outros seis parseiam texto (regex ou `json.loads`). Dado o tool-calling híbrido problemático do SGLang com Qwen3-VL (que colapsa em `(0,0)` em ~58% das respostas do caminho nativo, ver relatório `20260724` §6.1), **a lição transferível é sair do tool-calling nativo para um formato textual extraível por regex — não necessariamente `index-N`**, que está descartado. Um `click(x=…, y=…)` em texto puro, com reparo, capturaria o mesmo benefício de parsing sem tocar no espaço de ação.

**Ressalvas de disponibilidade** (relevantes para citação): GPTDroid não tem código utilizável (repo desativado por ToS); LLMDroid não tem preprint e o ACM DL bloqueia (fatos vieram do repo); o repo do VisionDroid é um stub de demo cujo `prompt.py` é text-only e **não corresponde** ao pipeline multimodal do paper.

## 9. Questões abertas (da verificação adversarial)

1. Calibração de sampling para diversidade de exploração vs validade de ação — lacuna real; explorável e publicável.
2. Transferência dos ganhos de selective-routing para VLM 4B on-prem — não testada; o papel "knowledge-maintenance-only" (LLM-Explorer) é o mais 4B-friendly.
3. Gatilho ótimo de estagnação/tarpit — nenhuma comparação publicada; sinal MOP como gatilho é inédito.
4. LLM-guidance melhora detecção de violações RV além do que o ganho de cobertura prevê? — sem baseline publicado; `cov_mop`/`mop_unique` do APE-RV podem ser a primeira medição.
5. **rev. 2 — toda a evidência de §8 vem de modelos text-only sobre o dump.** Nenhum trabalho publicado mede o desenho que de fato usamos: VLM pequeno, saída por coordenada, com alvo podendo estar fora do dump. A pergunta em aberto **não** é mais "índice vs coordenada" (descartada, §6 item 2) — é **como reduzir a repetição e curar o contexto mantendo a saída visual**, para o que não há precedente publicado.
6. **rev. 2 — custo do substrato estático na era Compose.** A literatura reconhece a limitação (o GAPS a declara "open research problem") mas não a mede em corpus contemporâneo. Os dados para medi-la existem aqui (`docs/20260708_investigacao_formas_guiar_mop.md`): 38,8% do corpus é Compose puro, 53,5% dos APKs produzem zero `windows`, 71,8% sem widget MOP utilizável — enquanto a riqueza do dump em **runtime** não difere entre Compose e View (p=0,971). Se isso vira sub-questão do E3 é decisão do autor.
7. **rev. 2 — LLM assíncrono / fora do caminho crítico em teste de GUI: não existe.** A literatura de especulação e latency-hiding em agentes LLM é ativa (PASTE, IdleSpec, Speculative Actions, MobileExplorer), mas **nenhuma** foi aplicada a teste de GUI. É a lacuna que ataca diretamente a causa raiz medida do gap do APE-RV.
9. **rev. 2 — repetição de ação inefetiva é O modo de falha da área, e a correção é determinística.** `[WEB]` VeriGUI / "Don't Act Blindly" (arXiv 2604.05477, ACL 2026): *"agents observe an unchanged screen yet generate another action… tend to repeat the exact same ineffective action"* — **72,3% de todas as falhas** em 1.265 execuções. LLMDroid (FSE'25): **69,75% das ações recomendadas por LLM não levaram a página nova**. "Tarpit escaping" (ASE 2026, arXiv 2604.06763): teste aleatório desperdiça ~metade do tempo em tarpits (pior caso 85,2%); detector por **perceptual hash + Hamming, θ=0,95, k=8**, deliberadamente **sem usar a view tree**; **+44,1% de cobertura de linha sobre o Monkey**. Reflexion (2303.11366): o gatilho original é **determinístico** (`>3 ciclos com mesma ação`), não uma pergunta ao modelo.
10. **rev. 2 — NUNCA perguntar ao modelo se a ação funcionou.** `[WEB]` MobiBench (2512.12634v3): *"self-reflection consistently degraded performance across all models"*; precisão de detecção de erro **52,94%** (moeda). "How Mobile World Model Guides GUI Agents?" (2605.10347): feedback pós-ação eleva Gemini-3-Flash 50,57→66,59, mas **Qwen3-VL-8B tem ganho mínimo e às vezes degrada**; entropia de ação 0,15 — o modelo não diversifica nem quando informado da falha. Self-Reflection via RL (2607.02490): **Qwen2.5-VL-3B com 77,3% de taxa de repetição**, e a reflexão *piorou* a acurácia multi-turno (4,5% vs 6,0%). **Implicação de desenho: separar detecção (determinística, no harness) de resposta (mecânica, por subtração do espaço de ações).** Nosso modelo é 4B — estaria no pior lado dessas curvas.
11. **rev. 2 — o Compose expõe acessibilidade em runtime (AOSP).** Converte a árvore *unmerged* em `AccessibilityNodeInfo`, classe padrão `android.view.View`, `resource-id` vazio sem `testTagsAsResourceId`. Isso explica por que apps Compose têm dump de runtime equivalente ao View-based (medido: p=0,971, ver §8.6). A lacuna real é estreita: `Canvas` de 1 argumento e `Layout` custom com desenho direto geram **zero nós**. ⚠️ Detalhe testável: o Compose usa `boundsInScreen()` para os bounds do `AccessibilityNodeInfo` e `positionInRoot()` para o hit-testing — **fontes de coordenada diferentes**, logo um tap dentro dos bounds reportados pode errar. Mecanismo plausível para parte dos `matched` inertes.
12. **rev. 2 — serviço de acessibilidade persistente no emulador** `[WEB]` recupera filhos de WebView (o Chromium só constrói os nós quando há um a11y service ativo) e força a semântica do Flutter. Custo ~zero, encolhe o conjunto off-dump antes de qualquer modelagem.
8. **rev. 2 — destilação LLM→política barata para exploração GUI: não existe.** Nenhum trabalho usa o LLM offline para produzir uma heurística/scorer que rode em runtime sem chamada.

## 10. Fontes (deduplicadas; qualidade primária salvo indicação)

**rev. 2 — teste dirigido a alvo e desenho de prompt (fonte primária):**

- **Guardian** (ISSTA 2024, pp. 958–970): https://dl.acm.org/doi/10.1145/3650212.3680334 · PDF https://dezhi-ran.com/publication/issta24-guardian/issta24-guardian.pdf · **artefato** https://github.com/PKU-ASE-RISE/Guardian (Apache-2.0; prompts literais confiáveis, reflexão/restauração **não implementadas**)
- **GAPS**: https://arxiv.org/abs/2511.23213 (preprint; **citar v3**, jul/2026 — v1 e v3 divergem materialmente; artefato 404)
- **GoalExplorer** (ASE 2019, pp. 115–127): https://dl.acm.org/doi/10.1109/ASE.2019.00021 · apêndice https://resess.github.io/PaperAppendices/GoalExplorer/
- **Hawkeye** (CCS 2018): https://dx.doi.org/10.1145/3243734.3243849 · **ADGE** (ICST 2025): https://ieeexplore.ieee.org/document/10989023/ · **Agent+P**: https://arxiv.org/abs/2510.06042
- **DroidBot-GPT**: https://github.com/MobileLLM/DroidBot-GPT · **DroidAgent** (ICST'24): https://github.com/coinse/droidagent · **VisionDroid**: https://arxiv.org/abs/2407.03037 · **GPTDroid**: https://arxiv.org/abs/2310.15780

**rev. 1:**

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
