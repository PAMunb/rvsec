Resumo Executivo
As três abordagens mais promissoras identificadas são:
Agente LLM ReAct com Ferramentas – Um agente sequencial que intercala raciocínio e ações (“Reason+Act”), usando chamadas de função (tools) para interagir com o app Android via UIAutomator. Esse paradigma, ilustrado por Rivera (2025)
medium.com
medium.com
, permite que o modelo gere raciocínio passo-a-passo e selecione ações (cliques, inputs etc) dinamicamente, reagindo ao estado atual da tela. É nativamente implementável em Python (e.g. com LangChain), reutiliza rv-uiautomator e rv-llm e funciona de forma síncrona. Espera-se adaptação robusta a mudanças na interface e maior cobertura de teste que prompt estático.
Agente Orientado a Planejamento de Tarefas (DroidAgent) – Inspirado em Yoon et al. (2023)
arxiv.org
, esse agente define metas de teste em alto nível e tenta realizá-las interagindo com o app. Usa múltiplas instâncias LLM com memória de curto e longo prazo para planejar e executar cada tarefa de forma contínua. Embora complexa, essa abordagem auto-orientada alcançou 61% de cobertura de atividades (vs. 51% de técnicas convencionais)
arxiv.org
, mostrando maior autonomia na geração de cenários de teste.
Agente Multimodal Visão-Linguagem – Utiliza modelos de visão-linguagem (e.g. Qwen-2.5-VL ou MobileVLM) para interpretar a interface visualmente. Por exemplo, técnicas como VETL
arxiv.org
aplicam LVLM para entender o contexto visual e gerar entradas de texto/contexto para exploração, aumentando em ~25% as ações únicas descobertas em sites web. O trabalho GUI-Actor
arxiv.org
demonstra como um VLM treinado especialmente pode localizar zonas de ação sem coordenadas explícitas. Essa abordagem pode detectar erros visuais (layout, bugs gráficos) que agentes puramente textuais não veriam, e integrar rv-screen-parser para fornecer screenshots ao LLM.
Abordagens Detalhadas
Abordagem 1: Agente ReAct com Ferramentas
Descrição técnica: O agente opera em loop síncrono: extrai o estado atual (hierarquia UI/screenshot), envia ao modelo com raciocínio encadeado e recebe de volta um JSON de ação via chamadas de função (tools). Ferramentas possíveis: clicar em elementos, inserir texto, tirar screenshot, acessar rv-screen-parser para parse. Esse fluxo “pensar-ação-observar” (ReAct) é similar à arquitetura demonstrada por Rivero (2025)
medium.com
, permitindo ao LLM gerar automaticamente debugging de contexto e decidir qual ferramenta usar a cada passo. O agente mantém o histórico recente e possivelmente resumos, ajustando a entrada ao contexto limitado dos modelos locais.
Compatibilidade com restrições:
Execução Python: ✅ (exemplo LangChain/LangGraph em Python)
Sem servidores externos: ✅ (usa modelos locais via rv-llm)
Janela de contexto limitada: ⚠️ (gestão de memória/resumo necessária)
Execução síncrona: ✅ (loop simples)
Dispositivo único: ✅
Reuso de módulos RV: ✅ (usa rv-llm, rv-uiautomator, rv-screen-parser)
Esforço de implementação: Moderado. Requer implementar novas subclasses de AbstractTool para ações de UI, orquestrar o loop do agente e lidar com parsing de JSON nos prompts. Há exemplos em TypeScript/Py (p.ex. implementação de “TestTools” em
medium.com
medium.com
) mas adaptar para Python deve levar semanas de desenvolvimento.
Benefícios vs. ferramenta atual: Oferece testes auto-adaptativos, menos frágeis a mudanças de UI. Pode operar com instruções em linguagem natural e gerar relatórios dinâmicos. Em comparação à engenharia de prompt pura, permite descoberta reativa: o agente ajusta a estratégia no teste em tempo real. Espera-se maior cobertura de fluxo (edge cases) e capacidade de “auto-correção” diante de falhas, graças ao raciocínio intermediário, conforme evidenciado no loop proposto por Rivero
medium.com
.
Avaliação (0–10): Viabilidade ~8 (complexidade moderada), Potencial de melhoria ~7 (bom ganho frente a prompts fixos), Maturidade ~5 (conceito emergente, pouco no open source).
Abordagem 2: Agente Planejador de Tarefas com Memória (DroidAgent)
Descrição técnica: Baseado no trabalho de Yoon et al. (2023)
arxiv.org
, esse agente usa múltiplas fases e memórias: um planejador (Planner) gera metas de teste em linguagem natural, um executor (Actor) tenta cumprir cada meta interagindo passo a passo com o app, e um observador/refletor (Observer/Reflector) atualiza a memória de longo prazo com resumos do que foi aprendido. A arquitetura completa emprega LLMs diferenciados (por ex. GPT-4 como crítico de tarefas) e vetores de memória (“widget retriever”)
ar5iv.labs.arxiv.org
ar5iv.labs.arxiv.org
. O agente é capaz de “lembrar” de widgets anteriores, resumir resultados e planejar de forma hierárquica. Em testes, o DroidAgent gerou centenas de tarefas realistas (85% relevantes) e superou baselines de cobertura
arxiv.org
.
Compatibilidade com restrições:
Execução Python: ⚠️ (conceptualmente sim, mas reimplementação de módulos complexo)
Sem servidores externos: ❌ (originalmente usava GPT-4/GPT-3.5 e ChromaDB)
Janela de contexto limitada: ❌ (depende de extensiva memória e LLM grande)
Execução síncrona: ⚠️ (fluxo recursivo, multi-turn complexo)
Dispositivo único: ✅ (foco em um app de cada vez)
Reuso de módulos RV: ✅ (pode usar rv-screen-parser para memória, rv-llm para LLM)
Esforço de implementação: Alto. Requer desenvolver ou adaptar componentes de memória (repositório de tarefas, base de conhecimento) e possivelmente treinar/fine-tunar modelos de visão-ação (difícil sem acesso a GPT-4). A complexidade arquitetural (múltiplos agentes internos e ciclos de reflexão) torna essa abordagem custosa em tempo.
Benefícios vs. ferramenta atual: Muito maior autonomia e cobertura de testes sem intervenção humana. O agente planeja e executa cenários completos, registrando-os em NL e código de teste. Em teoria, gera casos de uso significativos automaticamente. Comparado a prompts simples, ele direciona o teste a metas de negócio/usuário e itera sobre resultados, potencialmente detectando falhas lógicas que abordagens reativas não acham. Em Yoon et al. ele alcançou 61% de cobertura (vs 51% Humanoid)
arxiv.org
.
Avaliação (0–10): Viabilidade ~4 (muito desafiador sob restrições), Potencial de melhoria ~9 (poderoso se implementado), Maturidade ~3 (pesquisa acadêmica, poucos implementations práticos).
Abordagem 3: Agente Multimodal Visão-Linguagem
Descrição técnica: Integra modelos vision-language para interpretação direta da interface. Usa capturas de tela ou entrada da câmera e envia ao LLM multimodal (ex. Qwen-2.5VL, MobileVLM) junto com prompts. Por exemplo, VETL
arxiv.org
emprega LVLM para gerar textos de entrada contextualizados e Q&A visual, guiando uma estratégia de exploração por curiosidade. A pesquisa GUI-Actor
arxiv.org
demonstra como usar Qwen-VL para apontar regiões da tela (“grounding”) sem produzir coordenadas textuais: um token especial <ACTOR> “alinha” visualmente com elementos de interesse. Esses avanços permitem ao agente entender layouts e relacionamentos espaciais. Na prática, usar rv-screen-parser para estruturar elementos e sumarizá-los em texto ainda é essencial, mas o modelo multimodal pode confirmar escolhas via análise de imagem (ex: “qual botão parece ser ‘Enviar’?”).
Compatibilidade com restrições:
Execução Python: ✅ (ex. PyTorch, OpenCV, já há libs para visão)
Sem servidores externos: ✅ (Qwen-2.5VL roda localmente com Ollama)
Janela de contexto limitada: ⚠️ (cada imagem/prompt consome tokens, mas janela visual ajuda)
Execução síncrona: ✅ (chamadas sequenciais ao modelo multimodal)
Dispositivo único: ✅
Reuso de módulos RV: ✅ (aproveita rv-screen-parser para hierarquia e visão)
Esforço de implementação: Moderado. Envolve incorporar a inferência do modelo de visão (via rv-llm) e possivelmente ajustar prompts para tarefas visuais (análise de screenshot, descrição de elementos). Ferramentas auxiliares (detecção OCR, reconhecimento de componentes) podem ser reutilizadas do sistema, mas é preciso construir o pipeline de pré-processamento de imagem. Ainda assim, como o modelo faz boa parte do trabalho visual, não é tão custoso quanto aprender parâmetros.
Benefícios vs. ferramenta atual: Captura informações que testes baseados só em DOM/hierarquia não veem – por exemplo, elementos desenhados sem atributos textuais, erros de layout, mudanças de tema. Models como MobileVLM
arxiv.org
são treinados para “entender” relacionamentos visuais e textuais de UIs. Isso pode aumentar a robustez do agente: em vez de depender apenas de IDs/XPath, o modelo multimodal identifica elementos pelos seus conteúdos visuais. Em VETL, a componente visual permitiu criar entradas de texto válidas e explorar contextos dinâmicos, descobrindo ~25% mais ações relevantes
arxiv.org
. No RV-Android, essa abordagem pode complementar o parsing tradicional, melhorando a localização de ações críticas na tela.
Avaliação (0–10): Viabilidade ~7 (modelos VLM já disponíveis), Potencial de melhoria ~6 (bom ganho em análise de UI), Maturidade ~5 (campo novo, em rápida evolução).
Implementação Recomendada
Paradigma escolhido: Um agente ReAct com ferramentas, combinado com memória incremental. Essa abordagem cumpre as restrições de forma nativa e traz ganhos claros de adaptabilidade. Em vez de reimplementar o sofisticado pipeline de DroidAgent, recomendamos focar no fluxo de raciocínio e ação iterativo, estendendo-o progressivamente com simples memórias/sumarização. Arquitetura de integração: Implementar uma nova classe de ferramenta (AbstractTool) que orquestra o agente: por exemplo, um método rv_llm_tool que chama o modelo com prompts e recebe JSON. Outras ferramentas concretas incluem “click element” (usando rv-uiautomator), “input text” e “capturar estado UI” (com rv-screen-parser gerando JSON ou mesmo screenshot). O ciclo do agente faz:
Obter contexto: usar rv-screen-parser para extrair a árvore UI/texto ou tirar screenshot. Incluir esse estado no prompt (talvez textualizar JSON curto).
LLM call: via rv-llm, passando prompt com a missão do agente e instruções sistemáticas. O prompt incorpora instruções de teste (ex: “Execute um teste de login”) e o contexto UI.
Parse de Ação: o LLM retorna, em formato JSON definido, a próxima ação (ex: {"tool": "click", "selector": "..."}]).
Executar: Ferramenta correspondente executa a ação no dispositivo via UIAutomator. Obter feedback (novo estado ou resultado).
Repetir: Adicionar feedback ao histórico do prompt, possivelmente sumarizar cada X ciclos para manter contexto curto (técnica de memória). Voltar ao passo 1 até conclusão.
Esse agente básico já reutiliza rv-llm (chamadas LLM locais), rv-uiautomator (execução UI) e rv-screen-parser (memória de tela). Como framework de agentes, pode se basear em estruturas do LangChain em Python (não requer o LangGraph completo). Ferramentas adicionais podem ser registradas no ToolRegistry. A orquestração geral permanece síncrona, evitando a complexidade assíncrona. Roadmap de desenvolvimento sugerido:
Protótipo de Ferramentas: Crie ferramentas básicas herdeiras de AbstractTool: “get_screenshot” (ou estado textual), “perform_click”, “input_text”, “wait” etc. Teste-as isoladamente via UIAutomator.
Loop de Agente: Implemente a rotina principal que chama rv-llm com o prompt atual e executa a ação retornada. Verifique o JSON do LLM e mapeie para chamadas de ferramenta.
Gerenciamento de Contexto: Adicione um método de sumarização periódica (como usar o próprio LLM para resumir os últimos N passos) para não extrapolar a janela de contexto
arxiv.org
.
Visão (opcional): Integre Qwen-VL via rv-llm para, quando necessário, passar capturas de tela ao modelo (coletar screenshot e converter em base64/texto). Isso pode ser usado para validar automaticamente a ação escolhida.
Cobertura Estática e Eventos: Conectar o agente ao RV-Platform para obter insights estáticos (p.ex. fluxo de atividades) pode orientar as metas do agente. Use esses dados no prompt inicial ou como ferramentas adicionais de consulta.
Teste e Iteração: Avalie com aplicativos de benchmark (ex.: Themis) e compare cobertura/bugs encontrados contra ferramentas existentes (DroidBot, RV-Tools). Ajuste os prompts e o sistema de memória de acordo com os resultados.
Com esse plano, o agente proporcionará uma automação muito mais inteligente que prompts fixos, permanecendo compatível com a arquitetura modular do RV-Android e com os modelos locais disponíveis.
Referências
Yoon et al. Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing (2023)
arxiv.org
.
Wang et al. Leveraging Large Vision-Language Model For Better Automatic Web GUI Testing (2024)
arxiv.org
.
Wu et al. GUI-Actor: Coordinate-Free Visual Grounding for GUI Agents (2025)
arxiv.org
.
Wu et al. MobileVLM: A Vision-Language Model for Better Intra- and Inter-UI Understanding (2024)
arxiv.org
.
Feng et al. Breaking Single-Tester Limits: Multi-Agent LLMs for Multi-User Feature Testing (MAdroid) (2025)
arxiv.org
.
Liu et al. Temac: Multi-Agent Collaboration for Automated Web GUI Testing (2025)
arxiv.org
.
Citações

How I built an AI agent for end to end mobile app QA automation | by Ricardo Rivero | Jul, 2025 | Medium

https://medium.com/@ricrivero3/how-i-built-an-ai-agent-for-end-to-end-mobile-app-qa-automation-934b211fc9ae

How I built an AI agent for end to end mobile app QA automation | by Ricardo Rivero | Jul, 2025 | Medium

https://medium.com/@ricrivero3/how-i-built-an-ai-agent-for-end-to-end-mobile-app-qa-automation-934b211fc9ae

[2311.08649] Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing

https://arxiv.org/abs/2311.08649

[2311.08649] Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing

https://arxiv.org/abs/2311.08649

Leveraging Large Vision-Language Model For Better Automatic Web GUI Testing

https://arxiv.org/html/2410.12157v1

GUI-Actor: Coordinate-Free Visual Grounding for GUI Agents

https://arxiv.org/html/2506.03143v1

How I built an AI agent for end to end mobile app QA automation | by Ricardo Rivero | Jul, 2025 | Medium

https://medium.com/@ricrivero3/how-i-built-an-ai-agent-for-end-to-end-mobile-app-qa-automation-934b211fc9ae

How I built an AI agent for end to end mobile app QA automation | by Ricardo Rivero | Jul, 2025 | Medium

https://medium.com/@ricrivero3/how-i-built-an-ai-agent-for-end-to-end-mobile-app-qa-automation-934b211fc9ae

[2311.08649] Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing

https://ar5iv.labs.arxiv.org/html/2311.08649

[2311.08649] Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing

https://ar5iv.labs.arxiv.org/html/2311.08649

[2311.08649] Autonomous Large Language Model Agents Enabling Intent-Driven Mobile GUI Testing

https://arxiv.org/abs/2311.08649

[2409.14818] MobileVLM: A Vision-Language Model for Better Intra- and Inter-UI Understanding

https://arxiv.org/abs/2409.14818

Recursively Summarizing Enables Long-Term Dialogue Memory in Large Language Models

https://arxiv.org/html/2308.15022v4

Breaking Single-Tester Limits: Multi-Agent LLMs for Multi-User Feature Testing

https://arxiv.org/html/2506.17539v2

[2506.00520] Temac: Multi-Agent Collaboration for Automated Web GUI Testing

https://arxiv.org/abs/2506.00520