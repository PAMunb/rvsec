# Ferramentas Recentes de Teste Android: Análise e Aplicabilidade ao rvagent/rvsmart

**Data**: 2026-03-13
**Contexto**: Pesquisa de artigos e ferramentas publicados entre 2022-2025 para identificar
técnicas que possam melhorar o rvagent (agente Python LLM-driven, Qwen3-VL, DFS+MOP) e o
rvsmart (agente Java via app_process, ~14 evt/s, DFS 4-tier, 10 scorers).

---

## 1. Ferramentas Baseadas em LLM

### 1.1 GPTDroid — "Make LLM a Testing Expert"
- **Ano/Venue**: ICSE 2024 | arXiv:2310.15780
- **Ideia central**: Modela o teste de GUI como um diálogo Q&A onde o LLM simula um testador humano. Inovação principal: **functionality-aware memory prompting** — o LLM mantém uma memória crescente das funcionalidades já testadas ao longo da sessão, não apenas o estado atual.
- **Exploração**: LLM-guided step-by-step; sem backtracking explícito.
- **LLM**: GPT-3.5/GPT-4. Output em linguagem natural mapeado a widgets via rede de matching.
- **Estado**: XML view hierarchy convertido a linguagem natural.
- **Resultados**: +32% activity coverage vs melhor baseline em 93 apps do Google Play. +31% mais bugs. 53 bugs novos, 35 confirmados/corrigidos.
- **GitHub**: https://github.com/testinging6/GPTDroid
- **Aplicabilidade rvagent**: O padrão de **memória funcional acumulativa** é diretamente aplicável. Atualmente o rvagent mantém estado de exploração (telas visitadas, path buffer) mas não uma descrição semântica de "o que já foi testado". Adicionar um resumo de funcionalidades ao prompt do LLM durante detecção de plateau poderia reduzir exploração redundante.

### 1.2 DroidBot-GPT
- **Ano/Venue**: 2023 | arXiv:2304.07061
- **Ideia central**: Wrapper mínimo de LLM sobre DroidBot — baseline do paradigma LLM-por-passo.
- **Exploração**: LLM puro por passo, sem memória, sem backtracking.
- **LLM**: ChatGPT (GPT-3.5/4). Uma chamada por passo.
- **Resultados**: 39.39% task completion em 33 tarefas/17 apps.
- **GitHub**: https://github.com/MobileLLM/DroidBot-GPT
- **Aplicabilidade**: Baseline superado pelo rvagent. Referência de arquitetura limpa.

### 1.3 AutoDroid (MobiCom 2024)
- **Ano/Venue**: MobiCom 2024 | arXiv:2308.15272 | Microsoft Research
- **Ideia central**: Combina exploração dinâmica prévia (offline) para construir uma **UI memory por app** com execução guiada por LLM usando essa memória. Multi-granularity query optimization reduz custo.
- **Exploração**: Duas fases — pré-exploração DroidBot + execução LLM-guided com memória.
- **LLM**: GPT-4, GPT-3.5, Vicuna. HTML-style text do GUI hierarchy + memória app-específica.
- **Resultados**: 90.9% action accuracy, 71.3% task completion (158 tarefas, 13 apps). +36.4% vs GPT-4 baseline.
- **GitHub**: https://github.com/MobileLLM/AutoDroid
- **Aplicabilidade rvagent**: O padrão offline→online de construção de memória por widget durante a fase de exploração é complementar ao WTG estático já usado pelo rvagent. Síntese de "tarefas simuladas" a partir do WTG durante a análise estática para pré-popular o contexto do LLM.

### 1.4 AutoDroid-V2 (MobiSys 2025)
- **Ano/Venue**: MobiSys 2025 | arXiv:2412.18116
- **Ideia central**: Converte automação de UI em **geração de código UIAutomator** — em vez de decidir ação por ação, o SLM gera um script multi-passo para a tarefa inteira. Reduz N chamadas LLM para ~1 por tarefa.
- **LLM**: Small Language Models (SLMs) via llama.cpp. Poucos parâmetros, on-device.
- **Resultados**: +10.5–51.7% task completion vs baselines. Tokens: -43.5x (input), -5.8x (output). Latência: -5.7–13.4x.
- **Aplicabilidade rvsmart**: O rvsmart executa como agente Java no emulador. A ideia de gerar um script de ações em batch para uma subtarefa (em vez de decidir widget a widget) é diretamente aplicável — geração de sequências via LLM executada a 14 evt/s pelo rvsmart.

### 1.5 DroidAgent (ICST 2024)
- **Ano/Venue**: ICST 2024 | arXiv:2311.08649 | KAIST
- **Ideia central**: Primeira ferramenta a **definir seus próprios objetivos de teste** autonomamente. Um agente Planner gera intenções funcionais relevantes para o app; um agente Actor executa cada intenção.
- **LLM**: GPT-4 (Planner + Actor + completion detector).
- **Resultados**: 61% activity coverage vs 51% SOTA em 15 apps. 317/374 tarefas criadas autonomamente avaliadas como realistas.
- **GitHub**: https://github.com/coinse/droidagent
- **Aplicabilidade rvagent**: A **geração autônoma de intenções funcionais** é uma ideia forte. O rvagent poderia usar o WTG estático para gerar intenções app-específicas (ex: "alcançar Activity X via caminho Y") e rastrear quais foram satisfeitas, adicionando uma camada semântica de objetivos acima da exploração DFS.

### 1.6 AppAgent / AppAgent v2 (CHI 2025)
- **Ano/Venue**: CHI 2025 | arXiv:2312.13771 (Tencent QQG Y-Lab) | v2: arXiv:2408.11824
- **Ideia central**: Fase de exploração constrói **knowledge base por app** documentando o que cada elemento UI faz; fase de deployment usa RAG sobre essa base para execução eficiente.
- **LLM**: GPT-4V/4o (multimodal). Screenshots + descrições de elementos.
- **GitHub**: https://github.com/TencentQQGYLab/AppAgent
- **Aplicabilidade rvagent**: O padrão **RAG sobre documentação de UI por app** é altamente aplicável. rvagent poderia manter uma base de conhecimento leve por app (construída na primeira exploração), reduzindo queries redundantes ao LLM para os mesmos tipos de widget.

### 1.7 Mobile-Agent v1/v2/v3 (NeurIPS 2024)
- **Ano/Venue**: v1: arXiv:2401.16158 | v2: NeurIPS 2024, arXiv:2406.01014 | v3: arXiv:2508.15144 | Alibaba
- **Ideia central v2**: **Colaboração multi-agente** com separação clara de planejamento e execução. Planning Agent mantém notas de progresso e decide direção macro; Execution Agent cuida de interações na tela atual.
- **LLM**: GPT-4V. v1 adiciona OCR externo + detecção de ícones para compensar localização imprecisa do GPT-4V.
- **GitHub**: https://github.com/X-PLUG/MobileAgent
- **Aplicabilidade rvagent**: A **separação Planning Agent / Execution Agent** do v2 é diretamente relevante à arquitetura LangGraph do rvagent. Um nó dedicado de planejamento (raciocina sobre qual área do app explorar a nível de Activity/feature) separado do nó de execução (decisões por widget) melhoraria coerência em sessões longas.

### 1.8 LLMDroid (FSE 2025)
- **Ano/Venue**: FSE 2025 | ACM Software Engineering
- **Ideia central**: Framework **wrapper que envolve ferramentas existentes** (DroidBot, Humanoid, Fastbot) com orientação LLM ativada apenas quando o crescimento de cobertura estagna. O LLM resume páginas exploradas e sugere novas direções de exploração.
- **LLM**: GPT-4o ótimo ($4.77/hr); alternativa econômica obtém 78% do desempenho a $0.18/hr.
- **Resultados**: +26.16% code coverage, +29.31% activity coverage em 14 apps top.
- **GitHub**: https://github.com/LLMDroid-2024/LLMDroid
- **Aplicabilidade rvagent/rvsmart**: **O paper mais diretamente aplicável**. O plateau detector do rvagent já detecta estagnação. O insight do LLMDroid — usar LLM apenas quando travado, não em cada passo — é uma otimização explícita de custo/qualidade. Para rvsmart (Java, 14 evt/s), sugere um híbrido: DFS 4-tier a velocidade máxima normalmente, chamada LLM única ao detectar plateau.

### 1.9 VisionDroid (arXiv 2024)
- **Ano/Venue**: 2024 | arXiv:2407.03037
- **Ideia central**: Primeira abordagem vision-only para detectar **bugs funcionais não-crash**. MLLM raciocina sobre sequências de screenshots, segmentadas em unidades logicamente coesas, para detectar anomalias visuais.
- **Resultados**: +8–230% recall, +27–43% precision vs melhor baseline. 29 bugs novos no Google Play, 19 confirmados.
- **GitHub**: https://github.com/testtestA6/VisionDroid
- **Aplicabilidade rvagent**: O **detector de bugs visual** que segmenta histórico de exploração em unidades funcionais e as avalia com MLLM é um padrão de oracle complementar ao MOP. rvagent poderia adicionar detecção visual de bugs funcionais além das violações MOP.

### 1.10 LLM-Explorer (MobiCom 2025)
- **Ano/Venue**: MobiCom 2025 | arXiv:2505.10593
- **Ideia central**: **Inversão do paradigma LLM-por-passo**. LLM é usado apenas para construir/manter um grafo de conhecimento da app (raramente), não para gerar ações individuais. Seleção de ação usa sistema rule-based leve sobre o grafo.
- **Resultados**: **Maior cobertura** entre todos os 5 baselines testados em 20 apps. **148x menor custo** que SOTA LLM-por-passo.
- **Aplicabilidade rvagent/rvsmart**: **Insight arquitetural fundamental**. Usar LLM apenas para construção de conhecimento (raramente) e heurística local rápida para seleção de ação (sempre) reduz dramaticamente custo mantendo cobertura. Para rvsmart, eliminaria quase todas as chamadas LLM mantendo o benefício: construir grafo de widget-functions na exploração inicial, depois usar para guiar o DFS a 14 evt/s sem LLM.

### 1.11 TreeMind (arXiv 2025)
- **Ano/Venue**: 2025 | arXiv:2509.22431
- **Ideia central**: Combina LLM com **Monte Carlo Tree Search (MCTS)** para reprodução de bugs. Dois agentes LLM especializados: Expander (gera top-k ações candidatas como nós filhos) e Simulator (estima probabilidade de cada ação levar ao objetivo).
- **Resultados**: 63.44% bug reproduction rate vs 45.16% (ReActDroid), 40.86% (ReBL), 34.41% (AdbGPT).
- **Aplicabilidade rvagent**: O padrão **MCTS + LLM Expander/Simulator** é aplicável às decisões de backtracking do rvagent. Substituir a heurística DFS por MCTS leve onde o LLM fornece score de "probabilidade de este caminho alcançar novo MOP coverage" como função de simulação.

### 1.12 VLM-Fuzz (EMSE 2025)
- **Ano/Venue**: EMSE 2025 | arXiv:2504.11675
- **Ideia central**: DFS recursivo híbrido com **alocação de budget por componente** baseada no AndroidManifest. Testa cada componente da app separadamente; tempo de budget por componente proporcional ao número de elementos UI interativos.
- **Resultados**: +9.0% class coverage, +3.7% method coverage, +2.1% line coverage vs APE. 208 unique crashes em 24 apps.
- **Aplicabilidade rvsmart/rvagent**: A **alocação de budget por componente** com base em AndroidManifest é uma melhoria concreta e implementável. O DFS 4-tier do rvsmart atualmente não diferencia alocação de tempo entre Activities. Alocar mais tempo de teste para Activities com mais widgets interativos (mensurável a partir do WTG + análise estática) melhora eficiência de cobertura.

### 1.13 AUITestAgent (arXiv 2024)
- **Ano/Venue**: 2024 | arXiv:2407.09018 | Fudan + Meituan
- **Ideia central**: Primeira ferramenta de teste GUI em linguagem natural que **automatiza execução e verificação** a partir de requisitos. Dado requisito (ex: "Verificar que login falha com senha errada"), gera interações UI E verifica o resultado.
- **Resultados**: 94% verification accuracy. 4 bugs funcionais novos em produção Meituan.
- **GitHub**: https://github.com/bz-lab/AUITestAgent
- **Aplicabilidade rvagent**: O padrão de **verificação automatizada a partir de requisitos em linguagem natural** é aplicável a specs MOP. rvagent poderia aceitar descrições das specs MOP e derivar automaticamente interações de teste que exercitem o caminho de código relevante.

### 1.14 Aurora (ICSE 2025)
- **Ano/Venue**: ICSE 2025 | arXiv:2505.09894
- **Ideia central**: Classificador multimodal de telas em **21 categorias** (login, home, settings, advertisement, etc.) com estratégias de navegação adaptadas por tipo. Aborda o problema de ferramentas ficarem travadas em tipos específicos de tela.
- **Resultados**: +19.6% coverage vs APE/Monkey/VET em 17 apps proprietárias.
- **Aplicabilidade rvagent/rvsmart**: O **classificador de 21 tipos de tela** é diretamente aplicável. rvagent poderia classificar cada nova tela (via Qwen3-VL com few-shot prompting) e aplicar priorização MOP diferenciada por tipo. Telas de login devem usar credenciais armazenadas; diálogos devem ser descartados; formulários devem ser preenchidos com dados significativos.

---

## 2. Ferramentas Baseadas em VLM/Multimodal

### 2.1 OmniParser (Microsoft, arXiv 2024)
- **Ano/Venue**: 2024 | arXiv:2408.00203 | Microsoft Research
- **Ideia central**: Parser de tela pure-vision — converte screenshots em representações estruturadas de UI sem XML/HTML. Dois modelos especializados: detector de ícones YOLO fine-tuned + modelo de descrição funcional. Produz bounding boxes com IDs numéricos e descrições texto/ícone.
- **Grounding**: O overlay de IDs numéricos na screenshot permite que o VLM refira elementos por ID ("clicar elemento 7") em vez de coordenadas.
- **GitHub**: microsoft/OmniParser (HuggingFace + GitHub)
- **Aplicabilidade rvagent**: A abordagem de **numeric ID overlay** é diretamente aplicável. Pré-processar cada screenshot com OmniParser: detectar elementos, sobrepor caixas numeradas, pedir ao Qwen3-VL para raciocinar usando IDs em vez de coordenadas. Isso desacopla raciocínio de precisão de coordenadas e reduz carga espacial do VLM.

### 2.2 UGround (ICLR 2025 Oral)
- **Ano/Venue**: ICLR 2025 Oral | arXiv:2410.05243
- **Ideia central**: Modelo universal de visual grounding treinado no maior dataset de grounding de GUI (10M elementos, 1.3M screenshots). Habilita agentes GUI pure-vision que igualam ou superam agentes com input XML adicional.
- **Grounding**: Saída em coordenadas normalizadas [0, 1000) — idêntico ao Qwen2-VL/Qwen3-VL.
- **GitHub**: https://github.com/OSU-NLP-Group/UGround
- **Aplicabilidade rvagent**: UGround-V1 (7B, variante Qwen2-VL) poderia ser usado como **módulo de grounding especializado** ao lado do Qwen3-VL. Mesmo sistema de coordenadas [0,1000) = zero friction de integração. Setup dois modelos: Qwen3-VL para planejamento/raciocínio, UGround para localização de precisão.

### 2.3 SeeClick (ACL 2024)
- **Ano/Venue**: ACL 2024 | arXiv:2401.10935
- **Ideia central**: Fine-tuning de GUI grounding em cima do Qwen-VL via LoRA. Identifica que capacidade de grounding (mapear instrução a localização de clique precisa) é o gargalo para todas as tarefas downstream de agente GUI.
- **Dataset**: ScreenSpot benchmark para avaliar grounding.
- **GitHub**: https://github.com/njucckevin/SeeClick
- **Aplicabilidade rvagent**: O **ScreenSpot benchmark** é diretamente útil para avaliar precisão de coordenadas do rvagent. A receita de fine-tuning LoRA no Qwen-VL é aplicável ao Qwen3-VL para melhorar o hit rate além dos 84.2% atuais.

### 2.4 GUI-Actor (NeurIPS 2025, Microsoft)
- **Ano/Venue**: NeurIPS 2025 | arXiv:2506.03143 | Microsoft
- **Ideia central**: Substitui geração de coordenadas por texto por uma **action attention head** baseada em atenção. O problema fundamental: VLMs treinados para geração de linguagem, não regressão espacial — pedir "x=342, y=619" introduz perda de precisão. GUI-Actor produz heatmaps de atenção sobre patches visuais.
- **Resultados**: GUI-Actor-7B: 44.6 no ScreenSpot-Pro vs UI-TARS-72B: 38.1. SOTA em múltiplos benchmarks com menos parâmetros.
- **GitHub**: https://github.com/microsoft/GUI-Actor
- **Aplicabilidade rvagent**: O padrão de **grounding verifier** — verificar output de coordenadas do Qwen3-VL contra bounding boxes de elementos detectados (via OmniParser ou UIAutomator). Se o ponto predito cair fora de qualquer elemento conhecido, ajustar para o centro do elemento mais próximo.

### 2.5 UI-TARS (ByteDance, 2025)
- **Ano/Venue**: 2025 | arXiv:2501.12326 | ByteDance
- **Ideia central**: Agente GUI nativo end-to-end que unifica percepção, grounding, raciocínio, memória e ação em um único modelo. Treinado em dados massivos de interação GUI (não via prompt engineering).
- **Grounding**: Screenshots apenas (sem XML). Vocabulário de ações mobile-específico: `long_press`, `open_app`, `press_home`, `press_back`, `scroll`, `input_text`, `tap`.
- **Resultados**: AndroidWorld 46.6 vs GPT-4o 34.5. SOTA em 10+ benchmarks. Variantes: 2B, 7B, 72B.
- **GitHub**: https://github.com/bytedance/UI-TARS
- **Aplicabilidade rvagent**: O **vocabulário de ações mobile-específico** é diretamente aplicável ao espaço de ações do rvagent. A distinção entre `long_press`, `press_back` e variantes já existe no rvagent; o aprendizado é que tipos de ação granulares melhoram precisão em mobile.

### 2.6 Ferret-UI / Ferret-UI 2 (Apple, 2024)
- **Ano/Venue**: 2024 | arXiv:2404.05719 / v2: arXiv:2410.18967 | Apple
- **Ideia central**: VLM especificamente projetado para UI mobile com referring, grounding e reasoning. Inovação: processamento "any resolution" — divide screenshots verticalmente longas em 2 sub-imagens por aspect ratio, codifica separadamente, depois mescla. Captura elementos pequenos (ícones, texto) que o patching ViT padrão perde.
- **GitHub**: https://github.com/apple/ml-ferret
- **Aplicabilidade rvagent**: A abordagem de **split por aspect ratio** é diretamente aplicável ao prompting do Qwen3-VL. Em vez de enviar a screenshot inteira, dividir telas Android verticalmente longas em metades superior/inferior e enviar cada uma com contexto. Melhora precisão para elementos pequenos em listas longas scrolláveis.

### 2.7 MobileVLM — Xiaomi (EMNLP 2024)
- **Ano/Venue**: EMNLP 2024 | arXiv:2409.14818 | Xiaomi
- **Ideia central**: VLM com 4 tarefas de pre-training mobile-específicas para entendimento intra-UI e **inter-UI** (transições entre telas). Dataset Mobile3M: 3 milhões de páginas UI formando um grafo de transição dirigido.
- **Resultados**: +34.18% vs Qwen-VL-Max em tarefas de self-navigation; +14.34% em ScreenQA.
- **GitHub**: https://github.com/XiaoMi/mobilevlm
- **Aplicabilidade rvagent**: O **entendimento inter-UI** (pré-treinamento em grafos de transição) aborda diretamente a deduplicação semântica de estados no rvagent. Um modelo treinado em grafos de transição reconhece "esta tela é equivalente àquela anterior apesar das diferenças visuais" — identidade de estado semântico, não apenas similaridade de pixels.

---

## 3. Ferramentas Baseadas em RL/ML

### 3.1 MobileRL (arXiv 2025) — ESTADO DA ARTE
- **Ano/Venue**: 2025 | arXiv:2509.18119 | THUDM
- **Algoritmo**: GRPO (Group Relative Policy Optimization) + ADAGRPO (variante difficulty-adaptive); online RL fine-tuning de VLMs
- **Estado**: Screenshot VLM + XML — modalidade idêntica ao rvagent's Qwen3-VL
- **Recompensa**: Task success + shortest-path adjustment (penaliza sequências desnecessariamente longas)
- **Resultados**: MobileRL-9B: 80.2% no AndroidWorld, 53.6% no AndroidLab; supera UI-TARS-1.5 (72B) por +16% com modelo 8x menor
- **GitHub**: https://github.com/THUDM/MobileRL
- **Aplicabilidade rvagent**: **SOTA 2025 para agentes mobile baseados em VLM**. Fine-tuning GRPO em trajetórias do rvagent com sinal de recompensa MOP-trigger é o caminho de melhoria de maior upside para o rvagent. O difficulty-adaptive replay (tarefas fáceis mantidas no buffer de treinamento para prevenir forgetting) é aplicável ao currículo de APKs do rvagent por complexidade.

### 3.2 Hawkeye — Change-Targeted DRL (ByteDance, ICSE-SEIP 2024)
- **Ano/Venue**: ICSE-SEIP 2024 | arXiv:2309.01519 | ByteDance
- **Algoritmo**: DRL treinado em dados históricos de exploração GUI; mapeia eventos GUI a funções de código alvo
- **Recompensa**: Targeted — quão efetivamente eventos GUI executam funções de código modificadas/alvo
- **Resultados**: Supera Fastbot2 e ARES em targeted testing; deployado em CI do ByteDance
- **Aplicabilidade rvagent/rvsmart**: **Mais relevante para a tese**. Recompensa MOP-targeted = recompensa quando uma operação monitorada dispara a partir do estado atual. Hawkeye valida o conceito: recompensa RL direcionada supera significativamente recompensa de coverage-only quando existe objetivo específico (no nosso caso: triggers MOP).

### 3.3 DQT — Deep Q-Network com Graph Embedding (ICSE 2024)
- **Ano/Venue**: ICSE 2024 | ACM
- **Algoritmo**: DQN customizado com encoder GNN para representação de estado e ação
- **Estado**: Graph Neural Network embedding da hierarquia de widgets — preserva informação estrutural e semântica, habilita comparação baseada em similaridade entre apps
- **Recompensa**: Curiosity reward dinâmico fine-grained atualizado em runtime; compartilhado entre estados via similaridade de grafo
- **Resultados**: Supera SOTA em 30 apps open-source; especialmente forte em apps grandes/complexas. 21 bugs confirmados por desenvolvedores.
- **GitHub**: https://github.com/Yuanhong-Lan/DQT
- **Aplicabilidade rvagent/rvsmart**: **Cross-state knowledge sharing** é a ideia mais promissora: se clicar em um botão "Login" no app A disparou um MOP, a mesma ação no app B deveria receber score alto sem reaprendizagem. GNN-based state embedding é mais rico que hash de string para detecção de duplicatas.

### 3.4 DinoDroid — Cross-App Transfer Learning (TOSEM 2024)
- **Ano/Venue**: TOSEM 2024 | arXiv:2210.06307
- **Algoritmo**: DQN pré-treinado em corpus de apps Android; fine-tune por nova app
- **Estado**: Conteúdo de widgets (texto, labels, resource IDs) como features neurais
- **Resultados**: Supera ferramentas existentes em 64 apps Android open-source; efetivo imediatamente sem warm-up
- **Aplicabilidade rvsmart**: Pré-treinar em corpus dos 19 APKs já testados fornece um "head start" para novos APKs. Texto de widgets como features mapeia diretamente para o scorer de widgets existente do rvsmart — adicionar uma camada de embedding semântico seria uma melhoria tratável.

### 3.5 Fastbot2 — Modelo Probabilístico + RL (ByteDance, ASE 2022)
- **Ano/Venue**: ASE 2022 | ByteDance
- **Algoritmo**: Modelo probabilístico acumulando transições evento-activity entre runs + exploração RL-guided; herda throughput de 12 ações/segundo do Monkey
- **Estado**: Activity-level model (coarse); probabilidades de transição evento→activity persistem entre runs de CI
- **Resultados**: Supera Monkey, APE e Stoat em apps industriais com bilhões de usuários. 50.8% dos bugs confirmados por desenvolvedores foram primeiro reportados pelo Fastbot2.
- **GitHub**: https://github.com/bytedance/Fastbot_Android
- **Aplicabilidade rvsmart**: **Modelo probabilístico persistente entre sessões** é o enhancement RL mais prático para o rvsmart. Após cada run, salvar um JSON pequeno: `{state_hash → {action → mop_trigger_probability}}`. Próximo run começa com esse prior. Baixo custo de engenharia, alto impacto em cobertura.

### 3.6 TimeMachine — State Snapshot Restoration (ICSE 2020)
- **Ano/Venue**: ICSE 2020
- **Algoritmo**: Restauração de estado baseada em snapshots de emulador com heurística "most progressive state"
- **Estado**: Widget hierarchy tree hash; corpus de snapshots rastreia todos os estados descobertos com metadados
- **Resultados**: ~900 métodos adicionais cobertos e 1.5x mais crashes vs baseline
- **GitHub**: https://github.com/DroidTest/TimeMachine
- **Aplicabilidade rvagent/rvsmart**: A **fila de prioridade global de estados "most progressive"** é uma formulação limpa do que o plateau detector do rvagent já faz parcialmente. Insight do TimeMachine: quando travado, não reiniciar do zero — saltar para o estado globalmente mais promissor conhecido (não apenas o pai local). Para rvagent, manter fila global de estados parcialmente explorados durante a sessão inteira.

### 3.7 UCB Scoring (DroidbotX / APE)
- **Conceito**: `score_ucb(s,a) = Q(s,a) + C * sqrt(ln(visits(s)) / visits(s,a))`. Ações nunca tentadas em um estado recebem bônus grande; ações frequentes são penalizadas a menos que o Q-value justifique.
- **Aplicabilidade rvsmart**: O **formula UCB como 11° scorer do rvsmart** é a melhoria mais simples e imediata. Zero infraestrutura ML necessária — apenas contadores. DroidbotX valida: UCB converge mais rápido que epsilon-greedy em espaços de estado moderados.

---

## 4. Técnicas de Coverage-Guided e Especificação

### 4.1 ComboDroid (ICSE 2020)
- **Ano/Venue**: ICSE 2020
- **Ideia central**: Identifica via análise de call-graph estático "gateway events" — interações UI que levam a regiões de código alvo. Exploração prioriza esses caminhos de gateway.
- **Resultados**: +13% method coverage vs DroidBot em 20 apps
- **GitHub**: https://github.com/skull591/ComboDroid
- **Aplicabilidade**: **Extremamente relevante**. O GATOR WTG + call-graph já fornece esses dados no rvsec. Pré-computar o caminho UI para cada Activity contendo uma operação MOP e injetá-lo como prefixo de navegação de alta prioridade. Resolve diretamente o problema "login → settings → crypto".

### 4.2 Talos — Backward Slicing from Security APIs (CCS 2019)
- **Ano/Venue**: CCS 2019
- **Ideia central**: Backward slicing a partir de chamadas de API sensíveis (permissões, crypto) para identificar entry points UI. Geração de testes forward então cobre esses entry points.
- **Resultados**: Dispara 78% das APIs de segurança alvo vs 31% para teste aleatório
- **Aplicabilidade**: Esta é a **ferramenta mais diretamente aplicável para MOP coverage**. Backward slice a partir de cada método monitorado (`Cipher.init`, `MessageDigest.digest`, etc.) pelo call graph até o entry point UI. Então rvagent/rvsmart priorizam esses entry points.

### 4.3 TimeMachine (ICSE 2020) — Snapshot para Caminhos Profundos
- **Aplicabilidade**: Tomar **snapshots MOP-checkpoint**. Se uma operação MOP está atrás de login flow, snapshot o estado pós-login. Quando MOP coverage estagna, restaurar o checkpoint mais próximo. Abordagem mais forte para operações MOP em caminhos profundos/indiretos.

### 4.4 Q-Testing — Curiosity Reward (ISSTA 2020)
- **Aplicabilidade**: Recompensa de curiosidade/novelidade (prediction error em feature space) é aplicável ao reward propagation do rvagent. Memory set para deduplicação de estados visitados é alternativa leve ao hashing completo da widget tree.

---

## 5. Análise por Dimensão de Melhoria

### 5.1 Exploração: Além do DFS

| Abordagem | Ferramenta | Resultado vs DFS | Esforço Impl. |
|-----------|-----------|-----------------|--------------|
| MCTS + LLM Expander/Simulator | TreeMind | +40% bug repro | Alto |
| UCT scoring (MCTS sem rollouts) | OAT, DroidbotX | +15-25% cobertura | Baixo |
| Persistent probabilistic model | Fastbot2 | +20-30% cobertura | Baixo |
| Global progressive-state queue | TimeMachine | +40% método | Médio |
| Component budget allocation | VLM-Fuzz | +9% class | Médio |

**Recomendação**: UCT scoring como 11° scorer do rvsmart (baixo esforço) + component budget allocation via AndroidManifest (médio esforço, alto impacto direto).

### 5.2 Integração LLM: Custo vs Qualidade

| Abordagem | Ferramenta | Redução de custo | Impacto cobertura |
|-----------|-----------|-----------------|------------------|
| LLM apenas em plateau | LLMDroid | -70% chamadas | +26% cobertura |
| Knowledge graph (LLM raramente) | LLM-Explorer | -148x custo | +15% cobertura |
| LLM para geração de scripts batch | AutoDroid-V2 | -43.5x tokens | comparável |
| Planning/Execution split | Mobile-Agent v2 | moderado | +15% coerência |

**Recomendação**: Para rvagent, manter LLM ativo mas adicionar "fast path" sem LLM para ações de alta confiança. Para rvsmart, implementar híbrido LLM-em-plateau (já existe parcialmente).

### 5.3 Representação de Estado e Deduplicação

| Técnica | Ferramenta | Velocidade | Precisão |
|---------|-----------|-----------|---------|
| APE 4-attr abstraction | APE | O(1) | Alta (produção) |
| pHash/dHash | genérico | O(1) | Média (pixel) |
| GNN embedding | DQT | O(n) | Muito alta |
| Screen type classification | Aurora | O(1) inferência | Semântica |
| VLM description embedding | genérico | Lento | Semântica |

**Recomendação**: Dois níveis — APE 4-attr para fast-path (O(1)), screen type classifier para semantic dedup quando APE falha.

### 5.4 Grounding de Coordenadas Qwen3-VL

| Técnica | Ferramenta | Hit rate esperado |
|---------|-----------|-----------------|
| Atual (raw screenshot) | rvagent | 84.2% |
| OmniParser numeric IDs | OmniParser | ~90%+ |
| Grounding verifier (snap to nearest) | GUI-Actor | ~92%+ |
| UGround como módulo especializado | UGround | ~95%+ |
| LoRA fine-tuning em dados mobile | SeeClick | ~92%+ |

**Recomendação**: OmniParser numeric ID overlay (baixo esforço, alta utilidade) + grounding verifier snap-to-nearest (médio esforço).

### 5.5 MOP Coverage Específica

**Top 3 técnicas para maximizar MOP triggers:**

1. **ComboDroid/Talos — backward slicing estático** (Esforço: Médio, Impacto: Alto)
   - Usar output do GATOR já disponível para computar caminho UI → Activity com MOP
   - Injetar como prefixo de navegação obrigatório no início de cada sessão

2. **LLM prompt com alvos MOP explícitos** (Esforço: Baixo, Impacto: Médio-Alto)
   - Incluir lista de operações MOP ainda não acionadas no prompt do LLM
   - "Destas operações ainda não disparadas: [lista]. Qual elemento na tela atual provavelmente leva a uma delas?"

3. **Snapshot pós-autenticação** (Esforço: Médio, Impacto: Alto para apps com login)
   - TimeMachine-style: ao detectar login bem-sucedido, salvar snapshot
   - Ao detectar estagnação de MOP coverage, restaurar snapshot pós-login

---

## 6. Recomendações Priorizadas para rvagent

### Tier 1 — Alta Prioridade, Baixo Esforço (1-3 dias)

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 1 | Incluir lista de MOP targets não disparados no prompt LLM | GPTDroid, XBOT/LLMDroid | +15-25% MOP coverage |
| 2 | Screen refinement: overlay de bounding boxes antes do Qwen3-VL | LELANTE, OmniParser | +5-10% hit rate coordenadas |
| 3 | Functionality-aware memory no prompt do plateau detector | GPTDroid, LLMDroid | -30% exploração redundante |
| 4 | Grounding verifier: snap coordenada ao elemento mais próximo se fora de bounds | GUI-Actor | +8% hit rate |

### Tier 2 — Média Prioridade, Médio Esforço (1-2 semanas)

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 5 | Screen type classifier (21 categorias) com estratégia adaptada por tipo | Aurora | +20% cobertura em apps com login |
| 6 | Component budget allocation via AndroidManifest | VLM-Fuzz | +9% cobertura global |
| 7 | Planning Agent / Execution Agent split no LangGraph | Mobile-Agent v2 | +15% coerência sessões longas |
| 8 | Snapshot MOP-checkpoint pós-autenticação | TimeMachine | Alto para apps com login obrigatório |
| 9 | Prefixos de navegação pré-computados (backward slicing GATOR) | ComboDroid, Talos | +20-30% MOP triggers em caminhos profundos |

### Tier 3 — Longo Prazo, Alto Esforço (1-4 semanas)

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 10 | MCTS backtracking com LLM Simulator score | TreeMind | +40% em reprodução dirigida |
| 11 | Persistent session knowledge base (RAG sobre widgets por app) | AppAgent v2 | +25% em runs consecutivas |
| 12 | RL fine-tuning GRPO com MOP-trigger reward | MobileRL | Highest upside long-term |
| 13 | OmniParser como módulo de grounding alternativo | OmniParser | +90% hit rate |

---

## 7. Recomendações Priorizadas para rvsmart

### Tier 1 — Alta Prioridade, Baixo Esforço (1-3 dias)

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 1 | UCB como 11° scorer: `Q(s,a) + C*sqrt(ln(N(s))/N(s,a))` | DroidbotX, APE | +15% cobertura, converge mais rápido |
| 2 | APE 4-attribute state abstraction para dedup mais robusto | APE | -20% estados duplicados |

### Tier 2 — Média Prioridade, Médio Esforço

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 3 | Component budget allocation (tempo por Activity ∝ widgets interativos) | VLM-Fuzz | +9-15% cobertura de Activities menos visitadas |
| 4 | Persistent probabilistic model entre sessões | Fastbot2 | +20% cobertura em runs consecutivas |
| 5 | LLM em plateau: geração de sequência batch vs decisão passo-a-passo | AutoDroid-V2 | -80% chamadas LLM |

### Tier 3 — Longo Prazo

| # | Melhoria | Fonte | Impacto Esperado |
|---|----------|-------|-----------------|
| 6 | Cross-app knowledge sharing via GNN embeddings | DQT, DinoDroid | Warm start para novos APKs |
| 7 | Knowledge graph sem LLM por passo | LLM-Explorer | -148x custo LLM |

---

## 8. Gaps de Pesquisa — Contribuições Originais Potenciais

1. **MOP-targeted RL reward**: Nenhum paper usa reward específico para triggers de operações monitoradas. Hawkeye valida o conceito para funções alvo; aplicar a specs MOP é contribuição original.

2. **Integração runtime verification + LLM testing**: A combinação de JavaMOP instrumentation + LLM-driven exploration para maximizar MOP coverage é única. Nenhuma ferramenta encontrada faz isso.

3. **Static → dynamic pathway**: Usar backward slicing do call-graph estático para gerar prefixos de navegação dinâmica para operações monitoradas específicas é uma contribuição arquitetural nova.

4. **Benchmark MOP-coverage**: Não existe benchmark público para cobertura de operações monitoradas em Android testing. Criação seria contribuição para a comunidade.

---

## 9. Referências Selecionadas (por relevância)

### Altamente Recomendadas para Leitura
- LLMDroid (FSE 2025) — https://dl.acm.org/doi/10.1145/3715763
- LLM-Explorer (MobiCom 2025) — https://arxiv.org/abs/2505.10593
- VLM-Fuzz (EMSE 2025) — https://arxiv.org/abs/2504.11675
- TreeMind (arXiv 2025) — https://arxiv.org/abs/2509.22431
- MobileRL (arXiv 2025) — https://arxiv.org/abs/2509.18119
- Aurora (ICSE 2025) — https://arxiv.org/abs/2505.09894
- GPTDroid (ICSE 2024) — https://dl.acm.org/doi/abs/10.1145/3597503.3639180
- DQT (ICSE 2024) — https://dl.acm.org/doi/10.1145/3597503.3623344
- Hawkeye (ICSE-SEIP 2024) — https://dl.acm.org/doi/10.1145/3639477.3639749
- GUI-Actor (NeurIPS 2025) — https://arxiv.org/abs/2506.03143
- OmniParser (arXiv 2024) — https://arxiv.org/abs/2408.00203
- UGround (ICLR 2025) — https://arxiv.org/abs/2410.05243

### Para Contexto e Baseline
- GPTDroid GitHub: https://github.com/testinging6/GPTDroid
- DQT GitHub: https://github.com/Yuanhong-Lan/DQT
- AutoDroid GitHub: https://github.com/MobileLLM/AutoDroid
- DroidAgent GitHub: https://github.com/coinse/droidagent
- AppAgent GitHub: https://github.com/TencentQQGYLab/AppAgent
- MobileRL GitHub: https://github.com/THUDM/MobileRL
- UI-TARS GitHub: https://github.com/bytedance/UI-TARS
- Fastbot2 GitHub: https://github.com/bytedance/Fastbot_Android
- TimeMachine GitHub: https://github.com/DroidTest/TimeMachine
- OmniParser: microsoft/OmniParser (HuggingFace)
- GUI-Actor GitHub: https://github.com/microsoft/GUI-Actor
- UGround GitHub: https://github.com/OSU-NLP-Group/UGround

---

*Pesquisa realizada em 2026-03-13. Baseada em 6 agentes de pesquisa paralelos cobrindo: LLM-based tools (17 ferramentas), VLM/multimodal (18 ferramentas), RL/ML exploration (15 ferramentas), coverage-guided/spec-based (15 ferramentas), state abstraction/widget strategies (18 ferramentas), surveys/benchmarks (17 ferramentas).*

---

## 10. Técnicas Fundacionais e Estratégias de Widget

### 10.1 APE — Adaptive Probabilistic Exploration (ICSE 2019)
- **Técnica**: CEGAR (Counter-Example Guided Abstraction Refinement) aplicado a modelos de estado de GUI — coarsens e refina dinamicamente a abstração baseado em feedback de runtime.
- **Estado**: Equivalência por action-set (não por pixel/hash) — estados que produzem as mesmas ações são mesclados.
- **Resultados**: Supera todos os baselines em 15 apps do Google Play em cobertura e crashes únicos.
- **GitHub**: https://github.com/tianxiaogu/ape
- **Aplicabilidade rvagent/rvsmart**: Inspiração para deduplicação dinâmica de estados — o DFS do rvagent poderia adotar CEGAR-inspired coarsening para tratar "mesma tela, scroll diferente" como estados equivalentes sem lógica de hash hardcoded.

### 10.2 VET — Identifying and Avoiding UI Exploration Tarpits (FSE 2021) — Distinguished Paper
- **Técnica**: Análise de traces para detectar padrões tarpit (ex: logout screens, confirmation loops infinitos).
- **Problema**: Ferramentas ficam presas em padrões específicos (ex: clicar logout → impossível re-logar). VET identifica que um único padrão pode consumir **até 98.6% do budget de teste**.
- **Implementação**: Fase 1 — rodar ferramenta, gravar traces; Fase 2 — identificar padrões recorrentes de bloqueio; Fase 3 — bloquear ou recuperar desses triggers em runs subsequentes.
- **Aplicabilidade rvagent/rvsmart**: Tratamento formal do que o BACK-exemption do rvsmart cobre parcialmente. A análise offline de traces + bloqueio online de padrões é diretamente aplicável. O cenário de login wall é o exemplo canônico.

### 10.3 QTypist — Context-Aware LLM Text Input Generation (ICSE 2023)
- **Técnica**: Extrai contexto do widget (placeholder, tipo de campo, labels próximas, nome do app) → prompt estruturado para LLM → gera input semanticamente válido.
- **Resultados**: **87% passing rate** — 93% de melhoria sobre melhor baseline; +42% activities, +52% páginas, +122% bugs revelados.
- **arXiv**: 2212.04732
- **Aplicabilidade rvagent/rvsmart**: **Gap de maior impacto em ambas as ferramentas**. rvagent pode usar o contexto visual do Qwen3-VL para inferir semântica do campo. Para rvsmart (Java): extrair `resource-id` + `hint` + `contentDescription` + `inputType` → dicionário de categorias semânticas (email, nome, cidade, data, telefone).

### 10.4 Guardian — Runtime Framework for LLM-Based UI Exploration (ISSTA 2024)
- **Técnica**: Restringe espaço de ações do LLM em runtime + detecta quando nova informação invalida planejamento anterior → restaura estado + replaneja.
- **Resultados**: Avaliado em FestiVal: 58 tarefas de 23 apps populares; supera baselines LLM-only.
- **GitHub**: https://github.com/PKU-ASE-RISE/Guardian
- **Aplicabilidade rvagent**: O nó de validação do rvagent é uma versão mais grosseira do invalidation detection do Guardian. O padrão de **action space constraining** — "dizer ao LLM apenas sobre o subconjunto válido de ações" — é diretamente aplicável para reduzir ações alucinadas.

### 10.5 InputBlaster — LLM para Inputs de Texto Incomuns (2023)
- **Técnica**: Geração de inputs semanticamente inesperados mas sintaticamente válidos (emoji em campos numéricos, RTL text, etc.).
- **Resultados**: **78% bug detection rate, 136% acima do melhor baseline**. Detectou 37 crashes anteriormente não encontrados.
- **arXiv**: 2310.15657
- **Aplicabilidade rvagent**: Complementa QTypist — enquanto QTypist gera inputs semanticamente corretos para cobrir funcionalidade, InputBlaster gera inputs de boundary para encontrar crashes.

### 10.6 Delm — Deep Link-Enhanced Monkey (2024)
- **Técnica**: Usa Android deep links para injetar testing em activities difíceis de alcançar (protegidas por auth, states específicos).
- **Resultados**: **+27.2% activity coverage, +21.13% method coverage, +23.81% crash detection** vs Monkey.
- **arXiv**: 2404.19307
- **Aplicabilidade rvagent/rvsmart**: Deep links como bypass de auth para Activities que contêm MOPs. Se o AndroidManifest expõe deep links para Activities com operações monitoradas, usá-los como entry points privilegiados.

### 10.7 ProMal — Precise WTG via Tribrid Analysis (ICSE 2022)
- **Técnica**: Combina análise estática + dinâmica + ML para resolver ambiguidades de transição que nenhuma abordagem sozinha resolve.
- **Aplicabilidade rvagent/rvsmart**: rv-static-analysis usa GATOR (estático apenas). A abordagem tribrid — adicionar ML disambiguation à base estática existente — melhoraria precisão do WTG, especialmente para navegação gerada dinamicamente (WebViews, Fragment transactions).

### 10.8 Recomendações de Geração de Texto por Tipo de Campo

Para rvagent (Qwen3-VL): sub-prompt com contexto do campo:
> "This Android app is [app name]. The highlighted field is labeled [label] and accepts [type]. Generate a realistic, valid input."

Para rvsmart (Java, sem LLM no loop): dicionário tipado por categoria inferida do `inputType` + resource-id pattern:

| inputType | Estratégia |
|-----------|-----------|
| textEmailAddress | `testuser@example.com` |
| textPassword | `Test123!` (min complexity) |
| phone | formato local válido |
| number | valor numérico plausível |
| date | data futura/passada conforme semântica |
| text genérico | inferir de resource-id (search → termo do domínio do app) |

---

## 11. Benchmarks e Avaliação (2024-2025)

### 11.1 AndroidWorld (Google Research, 2024)
- **Venue**: arXiv:2405.14573
- **Escopo**: 116 tarefas programáticas em 20 apps reais do Android com variação dinâmica de parâmetros.
- **Resultado chave**: Melhor agente baseline atinge apenas **30.6% task completion** — gap severo vs performance humana.
- **GitHub**: https://github.com/google-research/android_world
- **Relevância**: Benchmark de referência para agentes LLM mobile. Resultados do rvagent podem ser comparados diretamente.

### 11.2 SPA-Bench (ICLR 2025 Spotlight)
- **Venue**: arXiv:2410.15164
- **Escopo**: 10+ agentes avaliados em ambiente Android interativo. 7 métricas cobrindo task completion e resource consumption.
- **Bottlenecks identificados**: (a) UI interpretation, (b) action grounding, (c) memory retention, (d) execution cost.
- **Relevância**: Valida empiricamente que memory retention para tarefas longas e grounding são os principais gargalos — exatamente as dimensões abordadas pelas seções 5.3 e 5.4 deste documento.

### 11.3 LlamaTouch (ACM UIST 2024)
- **Venue**: arXiv:2404.16054
- **Escopo**: 496 tarefas, 4 agentes mobile integrados. Introduz multi-level fuzzy matching para avaliação mais justa.
- **Finding chave**: Avaliação por exact-match subestima significativamente performance de agentes — fuzzy matching é necessário para avaliação realista.

### 11.4 A3: Android Agent Arena (2025)
- **Venue**: arXiv:2501.01149
- **Escopo**: 100 tarefas em 20 apps dinâmicas do Google Play (não apps estáticas offline).
- **Inovação**: "Essential-state procedural evaluation" usando MLLMs como reward models para verificação progressiva — mais robusto que avaliação single-shot.

### 11.5 Síntese: Open Problems (Consenso 2024-2025)

| Problema | Impacto no rvagent | Soluções discutidas neste doc |
|----------|-------------------|-------------------------------|
| Coverage ceiling (~50% activity) | Plateau frequente | Seções 5.1, 6.Tier2 |
| UI grounding e action localization | 84.2% hit rate atual | Seção 5.4, OmniParser, GUI-Actor |
| Long-horizon task completion | Sessões > 30min degradam | Mobile-Agent v2, AppAgent RAG |
| Meaningful text input generation | Formulários bloqueiam exploração | QTypist, InputBlaster (Seção 10.3/10.5) |
| Benchmark reliability | Comparação com literatura difícil | AndroidWorld como referência |

### 11.6 Promising Directions (Consenso da Comunidade)

1. **Hybrid LLM + Traditional Exploration**: LLM para decisões semânticas (o que testar), DFS tradicional para coverage exaustivo — exatamente a arquitetura do rvagent.
2. **Specialized UI Grounding Models**: SeeClick, GUI-Actor, UGround superam MLLMs gerais em grounding. ClickAgent (Samsung): separar raciocínio (MLLM) de localização (modelo especializado).
3. **Dynamic Benchmarks with Programmatic Rewards**: Direção do AndroidWorld + A3 — avaliação sem anotação humana.
4. **Change-Targeted and Intent-Driven Testing**: Hawkeye, DroidAgent, GPTDroid mostram que testing direcionado supera exploração não-direcionada — diretamente alinhado com MOP-targeted de rvagent/rvsmart.
5. **Bug Reproduction from Reports**: Linha AdbGPT → BugRepro → TreeMind: +81% → +155% em 2 anos. MCTS + LLM é o estado da arte atual.
