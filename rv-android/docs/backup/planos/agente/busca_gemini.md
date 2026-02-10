

# **Relatório de Pesquisa: Agentes LLM para Teste Automatizado Android no Contexto do Sistema RV-Android**

## **1\. Resumo Executivo**

Este relatório técnico e estratégico detalha uma análise aprofundada sobre a aplicação de agentes LLM (Large Language Model) para teste automatizado em aplicações Android, com um foco particular nas restrições e oportunidades intrínsecas à arquitetura do sistema RV-Android. A pesquisa, baseada em uma revisão abrangente da literatura técnica e acadêmica recente, bem como em uma avaliação de frameworks e paradigmas agênticos, identifica o caminho mais viável e promissor para o desenvolvimento de uma nova ferramenta de teste inteligente.

A principal conclusão é que a mera aplicação de *prompt engineering* para orientar modelos de linguagem atingiu suas limitações para tarefas de teste complexas e não determinísticas. O futuro da automação de QA (Quality Assurance) reside na adoção de um modelo agêntico, onde o LLM atua como um motor de raciocínio, e não apenas como um gerador de texto.

Nesse contexto, identificamos três abordagens estratégicas que se destacam pela sua compatibilidade e potencial de alavancar o ecossistema RV-Android:

1. **Adoção de um Modelo Agêntico Híbrido ReAct-LangGraph:** Esta abordagem utiliza o paradigma Reason \+ Act (ReAct) para interligar raciocínio, execução de ações e observação do estado da UI em um ciclo contínuo. A implementação deste ciclo em um framework de grafo como LangGraph permite a criação de fluxos de trabalho estaduais (stateful) e a inclusão de lógicas complexas de ramificação e repetição, superando a natureza linear e rígida dos *prompts* tradicionais. Esta sinergia é a fundação técnica mais robusta para a nova ferramenta.  
2. **Desenvolvimento de uma Arquitetura de Memória e Contexto Multi-nível:** As janelas de contexto limitadas dos modelos locais (como Gemma e Qwen) representam um desafio crítico. A solução viável não se restringe a uma única técnica, mas a um sistema híbrido de memória. Este sistema combina a técnica de "janela deslizante" com a sumarização inteligente do histórico de interações (ConversationSummaryBufferMemory) e a persistência de fatos críticos em "blocos de memória". Este modelo evita a "amnésia digital" do agente e mantém a coerência em testes de longa duração.  
3. **Integração Distribuída de Visão-Linguagem para Percepção de UI:** O uso de modelos multimodais como Qwen 2.5VL não deve ser para a execução direta de ações, o que geraria um *overhead* computacional proibitivo. Em vez disso, o modelo vision deve atuar como uma camada de percepção (screen understanding), que enriquece a representação textual da UI. O rv-screen-parser aprimorado geraria uma descrição semântica da tela (e.g., "Há um botão de login nas coordenadas ") que, por sua vez, seria consumida por um LLM menor e mais ágil para o raciocínio e a tomada de decisão. Essa arquitetura distribuída maximiza a eficiência e o potencial dos módulos existentes.

A recomendação estratégica e imediata para o desenvolvimento é a implementação de um *Tool-using Agent* orquestrado por um framework de grafo como LangGraph. Este modelo se alinha perfeitamente com a interface AbstractTool e o ToolRegistry já existentes, garantindo a reutilização máxima dos componentes do sistema. A implementação deve seguir um roteiro de desenvolvimento em três fases, começando com uma prova de conceito do ciclo ReAct e evoluindo para a incorporação de sistemas de memória e mecanismos robustos de recuperação de falhas.

## **2\. Análise do Estado da Arte em Agentes LLM para Teste de Software**

### **2.1. Paradigmas Agênticos Aplicáveis**

A transição da automação de testes baseada em *scripts* rígidos para a automação impulsionada por agentes de IA representa uma mudança fundamental no paradigma de QA. Em vez de seguir um conjunto predefinido de instruções, um agente LLM opera em um ciclo dinâmico de percepção, raciocínio e ação. Essa abordagem permite que o sistema adapte seu comportamento a condições de teste imprevistas, como pop-ups, mudanças de UI ou atrasos de carregamento.

#### **ReAct (Reasoning and Acting)**

O paradigma ReAct é uma das arquiteturas mais influentes para o desenvolvimento de agentes que utilizam ferramentas.1 Ele se baseia na interconexão de três elementos fundamentais em um

*loop* contínuo:

* **Thought (Pensamento):** O agente LLM analisa o estado atual do sistema, o histórico de interações e a meta do teste para gerar uma justificação para a próxima ação. Este passo de raciocínio interno é o que distingue o ReAct da mera execução de comandos.  
* **Action (Ação):** Com base no Thought, o agente seleciona e invoca uma ferramenta externa, como uma API de clique ou um comando para capturar a tela. No contexto do RV-Android, o rv-uiautomator e o rv-llm são candidatos perfeitos para essa camada de ação.  
* **Observation (Observação):** O agente processa o resultado da Action. A "observação" pode ser o sucesso de um clique, uma nova captura de tela, ou uma mensagem de erro. Essa nova informação é realimentada no loop, servindo de base para o próximo Thought.

Para a automação de UI, o modelo ReAct é a evolução natural do *prompt engineering*. Ele mimetiza o fluxo de trabalho de um testador humano: "Observar a tela, pensar no próximo passo, realizar uma ação, e observar a mudança resultante".1 A implementação deste paradigma é totalmente compatível com a arquitetura

RV-Android, que já possui as ferramentas para percepção (rv-screen-parser) e ação (rv-uiautomator). A nova ferramenta agêntica (AbstractTool) atuaria como o orquestrador desse ciclo.

#### **Agentes Tool-using**

O conceito de Tool-using agents é a fundação para a aplicação do ReAct no mundo real. Ele capacita o LLM a interagir com o ambiente externo de forma estruturada. Em vez de simplesmente gerar um texto para o usuário, o LLM pode emitir uma "chamada de função" que o sistema executa. O framework RV-Android com sua interface AbstractTool e seu ToolRegistry já implementa esse padrão de forma nativa.3

A transição para um agente LLM que consome essas ferramentas é, portanto, direta e eficiente. A nova ferramenta de teste não precisaria reinventar a roda, mas apenas se conectar ao ToolRegistry existente. O LLM receberia um conjunto de descrições das ferramentas disponíveis e seus parâmetros (por exemplo, click(x: int, y: int)), e seria capaz de selecionar a ferramenta apropriada e gerar os argumentos corretos para realizar a tarefa. A aplicação deste padrão no teste de UI é particularmente poderosa, pois a natureza granular das ações (click, input, scroll) se alinha perfeitamente com as funcionalidades de frameworks como UIAutomator.2

#### **Planejamento Hierárquico e Sistemas Multi-agentes**

Embora a literatura discuta amplamente os sistemas multi-agentes e a colaboração entre eles (como em CrewAI e AutoGen) para tarefas complexas como a geração de relatórios 4, a restrição de "foco em teste de um dispositivo por vez" do

RV-Android limita a aplicação direta desse paradigma. O *overhead* de orquestração e a comunicação entre múltiplos agentes independentes podem ser desnecessários e incompatíveis com a natureza síncrona do sistema.

No entanto, o conceito de **planejamento hierárquico** é altamente aplicável. Uma única entidade agêntica pode receber uma tarefa de alto nível (e.g., "validar o fluxo de compra de um produto"), e então decompor essa tarefa em sub-objetivos menores (e.g., "encontrar o campo de busca", "digitar o nome do produto", "clicar no botão 'adicionar ao carrinho'"). O agente principal agiria como um "planejador", delegando a execução de cada sub-tarefa a si mesmo, mas em um ciclo de Thought-Action-Observation. Essa abordagem permite a automação de fluxos de teste complexos sem a necessidade de uma arquitetura multi-agente distribuída, otimizando o sistema para o ambiente de dispositivo único.6

### **2.2. Frameworks de Agentes LLM em Python**

A escolha do framework de desenvolvimento é crucial para garantir a viabilidade técnica da solução. A arquitetura RV-Android, sendo modular e baseada em Python, requer uma ferramenta que se integre de forma fluida com seus componentes existentes.

* **LangChain:** É o framework mais popular e maduro para a criação de aplicações com LLMs.4 Sua arquitetura modular, que inclui  
  Agents, Tools, Chains, e sistemas de memória, oferece um conjunto de blocos de construção essenciais para o projeto. A vasta comunidade e a documentação extensa tornam-no um excelente ponto de partida. Ele fornece os modelos e a sintaxe para implementar o paradigma ReAct de forma eficiente.  
* **LangGraph:** Sendo uma extensão de LangChain, o LangGraph é projetado especificamente para a construção de fluxos de trabalho stateful e cíclicos.7 Ele representa o fluxo de execução como um grafo, onde os nós são passos (  
  LLM, Tool, Human-in-the-loop) e as arestas são transições condicionais. Essa estrutura é particularmente adequada para o teste de UI, onde o agente pode precisar voltar para um estado anterior ou repetir uma ação com base em uma nova observação. A capacidade de checkpointing do LangGraph para persistir o estado do grafo é um recurso vital para a recuperação de falhas, uma preocupação central em sistemas de teste não determinísticos.8  
* **CrewAI:** Focado na orquestração de equipes de agentes com papéis e objetivos bem definidos.4 Cada agente tem um  
  role, um goal, uma backstory e um conjunto de tools. Embora seja uma abordagem limpa e intuitiva para fluxos de trabalho complexos que se beneficiam da colaboração (como a geração de conteúdo), sua filosofia pode ser um excesso para o RV-Android. A comunicação e coordenação entre agentes introduziriam uma camada de abstração desnecessária e um potencial *overhead* de latência, o que colide com a restrição de um sistema de dispositivo único e a natureza síncrona da arquitetura atual.8

### **2.3. Estudos de Caso e Pesquisa Acadêmica Recente (2023-2024)**

A literatura recente valida a tendência de usar agentes LLM para QA, oferecendo modelos e inspirações para a implementação.

* AutoDroid 34:  
  Este sistema de automação de tarefas para Android demonstra a viabilidade de usar LLMs para guiar interações com a UI. O AutoDroid utiliza uma "representação HTML simplificada" da UI, que é alimentada ao LLM para que este determine a próxima ação. A similaridade dessa abordagem com o uso do rv-screen-parser para gerar uma representação da tela é notável e valida a estratégia central do projeto RV-Android: a representação textual do estado visual é um *input* poderoso para o raciocínio do agente.  
* Test-Agent 29:  
  O framework Test-Agent é um exemplo promissor de automação de teste multimodal. Ele não depende de *scripts* pré-escritos, mas sim da análise de capturas de tela e da estrutura da UI para gerar ações. O documento descreve como o framework utiliza tecnologias de visão computacional e o poder de modelos de linguagem para entender instruções em linguagem natural e traduzi-las em ações de teste. A principal conclusão é que essa abordagem reduz drasticamente o tempo de desenvolvimento, diminui a necessidade de habilidades técnicas especializadas e oferece uma versatilidade *cross-platform* superior a ferramentas tradicionais como Appium e Espresso. Isso confirma que a visão por trás da nova ferramenta para o RV-Android está alinhada com as pesquisas de ponta na área.  
* **Outros Estudos:** A pesquisa acadêmica em 2023-2024 mostra a aplicação de agentes LLM em diversas tarefas de software, como detecção de vulnerabilidades (GPTLens), análise estática de código (ICAA), e *fuzzing* de sistemas (WhiteFox).10 Isso indica que a integração de LLMs não se limita a tarefas de conversação, mas está se tornando um componente central para a automação de QA em um sentido mais amplo. A capacidade de um agente de interagir com ferramentas e analisar o ambiente é uma das chaves para essa revolução.11

## **3\. Análise de Compatibilidade e Viabilidade Arquitetural para RV-Android**

A viabilidade de qualquer abordagem agêntica para o sistema RV-Android depende de uma análise rigorosa de sua compatibilidade com as restrições e oportunidades da arquitetura existente. O sistema é modular e baseado em Python, utiliza modelos locais (como Gemma e Qwen) e opera em um fluxo síncrono. Além disso, a nova ferramenta deve herdar da classe AbstractTool e reutilizar os módulos rv-\* existentes. A análise a seguir confronta as abordagens encontradas com esses critérios críticos.

O desafio mais complexo é reconciliar a capacidade de análise visual dos modelos multimodais (Qwen 2.5VL) com o custo computacional e a latência de execução em um ambiente de hardware limitado. A solução não reside na utilização do VLM para cada passo de raciocínio, mas em uma arquitetura distribuída. O VLM atua como uma "camada de percepção" para o rv-screen-parser, traduzindo a UI visual em uma representação textual rica e semântica. Essa representação otimizada é, então, passada para um LLM de raciocínio menor e mais rápido (rv-llm), que pode tomar decisões de ação sem precisar processar a imagem inteira novamente. Esta divisão de tarefas minimiza o *overhead* e maximiza o potencial de cada modelo.

A Tabela 1 sintetiza a avaliação de compatibilidade e viabilidade das principais abordagens e frameworks.

| Abordagem / Framework | Compatibilidade com Restrições RV-Android | Esforço de Implementação (0-10) | Potencial de Melhoria (0-10) | Maturidade (0-10) |
| :---- | :---- | :---- | :---- | :---- |
| **Paradigma ReAct** | ✅ Totalmente compatível com o modelo síncrono. A interface AbstractTool é um encaixe perfeito. | 3 | 9 | 9 |
| **Framework LangGraph** | ✅ Implementável em Python. Suporta stateful e ciclos. A feature de checkpointing é vital para recuperação. | 4 | 9 | 7 |
| **Framework CrewAI** | ❌ O modelo de multi-agentes é incompatível com o foco em "single-device". | 8 | 5 | 7 |
| **Gerenciamento de Contexto (Sumarização)** | ✅ Essencial e fácil de integrar via um novo chain ou memory no rv-llm. | 2 | 8 | 8 |
| **VLMs para Percepção Distribuída** | ⚠️ Viável se a latência for gerenciada. Requer aprimoramento do rv-screen-parser. | 6 | 10 | 7 |

### **3.1. Viabilidade de Implementação**

A viabilidade técnica de um novo agente LLM é alta, dada a arquitetura modular e baseada em Python do RV-Android. A interface AbstractTool e o ToolRegistry já oferecem o padrão de tool-using necessário.3 O principal desafio é o design da nova ferramenta (

rv-agent) que atue como o orquestrador do ciclo ReAct. O LangGraph é a escolha mais inteligente, pois permite a criação de um fluxo de trabalho em grafo, onde os nós podem ser os módulos rv-\* e as transições podem ser condicionais, dependendo da observação do LLM.

A complexidade de implementação é moderada (esforço 4/10 para LangGraph), pois se baseia na reutilização de componentes existentes em vez de exigir a criação de uma nova arquitetura do zero. A maior parte do esforço seria investida no *prompt engineering* para o LLM (rv-llm), na adaptação do rv-screen-parser para a análise multimodal, e na implementação da lógica de estado e recuperação de falhas.

### **3.2. Análise de Desempenho e Overhead**

A principal preocupação de desempenho reside na inferência do modelo multimodal Qwen 2.5VL.12 Embora o modelo seja robusto, seu tamanho pode introduzir latência significativa em dispositivos com recursos limitados. A estratégia de usar o VLM como uma camada de percepção distribuída é uma solução para este problema, pois o

rv-llm só precisa processar uma descrição de texto otimizada, e não a imagem completa a cada passo do raciocínio. O overhead de frameworks como LangGraph é baixo em comparação com frameworks de multi-agentes como CrewAI. A latência de *loop* será dominada pelo tempo de inferência do LLM e pela captura e processamento da tela, não pelo framework de orquestração em si.

### **3.3. Análise de Oportunidades**

A arquitetura do RV-Android oferece oportunidades únicas para a aplicação de agentes LLM. O rv-llm já é um ponto de integração central, e o rv-screen-parser e o rv-uiautomator são as ferramentas ideais para percepção e ação. A maior oportunidade reside em aprimorar o rv-screen-parser para não apenas capturar a estrutura da UI (via XML) mas também para gerar uma descrição semântica da tela, aproveitando as capacidades de screen understanding de modelos como o Qwen 2.5VL.13 Isso capacitaria o agente a tomar decisões mais inteligentes, como entender que um ícone de lupa representa a função de busca ou que um campo de texto pede um e-mail. Esta sinergia direta entre os módulos existentes e a nova abordagem agêntica é a chave para a vantagem competitiva do sistema.

## **4\. Técnicas de Otimização e Padrões de Implementação Inovadores**

A construção de um agente LLM robusto para teste de UI requer a incorporação de técnicas avançadas que superem as limitações inerentes aos modelos e à natureza do problema. Três áreas de otimização são críticas: gerenciamento de contexto, orquestração de ferramentas e integração de modelos de visão.

### **4.1. Estratégias de Gerenciamento de Contexto**

A limitação da janela de contexto dos modelos locais (Gemma, Qwen) é um desafio fundamental para testes de longa duração, levando à "amnésia digital" onde o agente esquece interações passadas.14 A solução mais eficaz é uma arquitetura de memória híbrida que combine diferentes níveis de armazenamento e recuperação de informações.

* **Janela Deslizante com Sumarização:** Uma técnica básica é o uso de uma "janela deslizante" que mantém apenas as k interações mais recentes.14 No entanto, isso pode fazer com que informações críticas sejam descartadas. Uma abordagem superior utiliza a  
  **sumarização inteligente**. O agente LLM, com um chain específico para esta tarefa, periodicamente resume o histórico de conversação mais antigo em um único texto, liberando espaço na janela de contexto para interações mais recentes. Frameworks como LangChain e LangGraph oferecem componentes prontos para essa tarefa, como o ConversationSummaryBufferMemory.14 Essa técnica mantém a coerência e permite que o agente lide com sequências de teste mais longas.  
* **Blocos de Memória Persistente:** O conceito de "blocos de memória" (MemGPT) oferece uma abstração para a persistência de estado do agente que é independente da janela de contexto.15 Fatos críticos sobre a aplicação ou o teste (e.g., "o login do usuário é  
  teste@email.com" ou "o objetivo é comprar um produto") podem ser armazenados em um MemoryBlock externo. O agente pode então, de forma controlada, acessar ou "re-escrever" este bloco conforme necessário, garantindo que informações vitais não sejam perdidas. Essa abordagem é ideal para o sistema RV-Android, permitindo que o agente mantenha o conhecimento de fatos persistentes sem poluir a janela de contexto com informações estáticas.

### **4.2. Padrões de Orquestração de Ferramentas**

A orquestração de ferramentas em um agente LLM não se resume a uma chamada simples de função, mas deve incluir mecanismos robustos para seleção dinâmica, manipulação de erros e recuperação de falhas.6

* **Seleção Dinâmica de Ferramentas:** O agente deve ser capaz de escolher a ferramenta mais adequada a partir de um conjunto de opções com base em seu Thought.3 A arquitetura  
  ToolRegistry já oferece a base para isso, e a implementação deve garantir que o *prompt* do LLM inclua descrições claras e precisas de cada AbstractTool disponível.  
* **Recuperação de Falhas (Error Handling):** Falhas em sistemas de agentes são frequentes e não determinísticas, podendo ser causadas por alucinações do modelo, *timeouts* de ferramentas, ou mudanças inesperadas na UI.9 Um sistema agêntico robusto deve ter estratégias de recuperação integradas:  
  1. **Retry and Backoff:** Para falhas transientes (e.g., um problema de rede), o sistema deve tentar a ação novamente com um atraso exponencial crescente.17  
  2. **State Persistence and Checkpointing:** O LangGraph oferece a capacidade de salvar o estado do fluxo de trabalho após cada passo bem-sucedido. Em caso de falha crítica, o agente pode reiniciar a partir do último checkpoint válido, evitando a necessidade de começar o teste do zero.9  
  3. **Handoff to Human-in-the-Loop:** Quando o agente encontra um estado que não consegue resolver (e.g., uma tela de erro não mapeada), ele deve ser capaz de "escalar" o problema para um testador humano, fornecendo todo o contexto da falha para facilitar a intervenção.17

### **4.3. Integração de Modelos de Visão e Linguagem**

A capacidade de um agente de "ver" a tela é um pré-requisito para o teste de UI. A integração de VLMs no RV-Android deve focar em uma arquitetura de percepção distribuída que otimiza o uso de recursos.

* **Técnicas de Screen Understanding:** O rv-screen-parser atual fornece a estrutura XML da UI. Um aprimoramento seria a sua capacidade de utilizar um VLM (Qwen 2.5VL) para gerar uma descrição textual rica e contextualizada da tela. Essa descrição incluiria informações como:  
  * Identificação de elementos interativos (buttons, text fields) e não interativos (icons, images).13  
  * Extração de texto via OCR e sua associação a elementos visuais.  
  * Compreensão da semântica da UI (e.g., o que é um ícone de "carrinho de compras").18  
* **Previsão de Coordenadas (Coordinate Prediction):** A capacidade de um VLM de prever a localização espacial de elementos na tela é crucial para que o agente possa comandar o rv-uiautomator a clicar em pontos específicos.18 A pesquisa acadêmica indica que essa é uma área de estudo ativa. O  
  rv-screen-parser aprimorado poderia não apenas descrever a tela, mas também fornecer uma lista de elementos com suas respectivas coordenadas e descrições, permitindo que o LLM de raciocínio (o rv-llm) apenas selecione a ação e as coordenadas apropriadas. Isso divide a carga computacional, reservando o VLM para a percepção visual complexa e o LLM para o raciocínio e a tomada de decisão ágil.19

## **5\. Recomendação de Abordagem e Roteiro de Implementação**

Com base na análise técnica e na avaliação de viabilidade, a abordagem mais promissora para o sistema RV-Android é um modelo de agente híbrido que alavanca as fortalezas da arquitetura modular existente.

### **5.1. Paradigma Agêntico Recomendado**

A recomendação é a adoção de um **Único Agente com Execução ReAct Hierárquica via LangGraph**. Esta abordagem se justifica pela sua compatibilidade com as restrições do sistema e pela sua capacidade de superar as limitações do *prompt engineering* tradicional. Ela permite um controle refinado sobre o fluxo de trabalho, suporta lógicas de teste cíclicas e oferece um caminho claro para a implementação de recuperação de falhas, essenciais para a confiabilidade em ambientes de teste não determinísticos.

### **5.2. Arquitetura de Integração com RV-Android**

A nova ferramenta de teste, denominada rv-agent, seria implementada como um novo módulo em Python que herda da classe AbstractTool. Sua arquitetura de integração seguiria um fluxo de trabalho em grafo orquestrado pelo LangGraph, reutilizando os módulos rv-\* como ferramentas dedicadas.

* **Componentes do rv-agent:**  
  * **Orquestrador (LangGraph):** O motor central que gerencia o estado do loop ReAct, incluindo o histórico, a meta do teste e a lógica de transição entre os nós.  
  * **Nós de Ferramenta (AbstractTool):** O rv-screen-parser e o rv-uiautomator seriam expostos como ferramentas do LangGraph.  
  * **Nó de Raciocínio (rv-llm):** O rv-llm seria o nó responsável por gerar o Thought e a Action com base na observação e na meta atual.  
  * **Sistema de Memória:** Um componente de memória híbrida que armazena o histórico sumarizado e os "blocos de memória" persistentes.  
* **Fluxo de Trabalho de Exemplo:**  
  1. O usuário envia uma tarefa ao sistema (e.g., "Comprar um produto"). O sistema aciona o rv-agent.  
  2. O rv-agent inicia um LangGraph com a meta do teste.  
  3. O LangGraph chama o rv-screen-parser, que usa o Qwen 2.5VL para analisar a tela e gerar uma descrição semântica rica.  
  4. O rv-llm recebe a descrição da tela e a meta. Ele gera um Thought ("A tela inicial tem um campo de busca.") e uma Action (call\_tool('input', 'search\_field', 'produto')).  
  5. O LangGraph executa a ação via o rv-uiautomator.  
  6. O rv-uiautomator retorna a Observation (e.g., "Ação de input bem-sucedida.").  
  7. O LangGraph alimenta a Observation de volta para o rv-llm para o próximo passo de raciocínio, e o ciclo se repete até que a meta seja alcançada ou uma falha seja detectada.

### **5.3. Roteiro de Desenvolvimento Sugerido**

A implementação deve ser dividida em fases incrementais para validar a arquitetura e garantir a funcionalidade em cada etapa.

* **Fase 1: Prova de Conceito do Ciclo ReAct (30 dias)**  
  * **Objetivo:** Demonstrar que o ciclo Thought-Action-Observation funciona e pode ser orquestrado pelo LangGraph.  
  * **Atividades:**  
    * Criação de um protótipo rv-agent que herda de AbstractTool.  
    * Integração dos módulos rv-screen-parser e rv-uiautomator como Tools em um fluxo LangGraph.  
    * Desenvolvimento de um *prompt* inicial no rv-llm para guiar a navegação em uma UI de teste simples e estática.  
    * Validação da execução síncrona do loop.  
* **Fase 2: Implementação da Arquitetura de Memória e Visão (60 dias)**  
  * **Objetivo:** Adicionar a inteligência de contexto e a percepção aprimorada.  
  * **Atividades:**  
    * Desenvolvimento de um componente de memória híbrida para o rv-llm que utilize sumarização para o histórico e "blocos de memória" para fatos.  
    * Aprimoramento do rv-screen-parser para utilizar o Qwen 2.5VL para gerar uma descrição textual detalhada da tela e suas coordenadas, em vez de apenas o XML.  
    * Testes de desempenho para avaliar a latência da inferência do Qwen e otimização do fluxo de dados entre os modelos.  
* **Fase 3: Robustez e Recuperação de Falhas (60 dias)**  
  * **Objetivo:** Aumentar a confiabilidade do agente para testes de longa duração em cenários não determinísticos.  
  * **Atividades:**  
    * Integração do checkpointing do LangGraph para persistência de estado.  
    * Implementação de uma lógica de error recovery no rv-agent, que possa re-planejar o próximo passo ou acionar lógicas de *retry* com *backoff* em caso de falha de uma ferramenta.  
    * Desenvolvimento de mecanismos de detecção de alucinações ou de estados de erro irrecuperáveis, com a opção de fallback para intervenção humana, se necessário.

## **6\. Referências (Anexo)**

* 4  
  [https://code-b.dev/blog/python-frameworks-ai-agent](https://code-b.dev/blog/python-frameworks-ai-agent)  
* 5  
  [https://github.com/kaushikb11/awesome-llm-agents](https://github.com/kaushikb11/awesome-llm-agents)  
* 20  
  [https://medium.com/@erickzanetti/automated-testing-with-jest-and-react-testing-library-a-complete-guide-272a06c94301](https://medium.com/@erickzanetti/automated-testing-with-jest-and-react-testing-library-a-complete-guide-272a06c94301)  
* 21  
  [https://legacy.reactjs.org/docs/testing.html](https://legacy.reactjs.org/docs/testing.html)  
* 7  
  [https://www.zenml.io/blog/langgraph-vs-crewai](https://www.zenml.io/blog/langgraph-vs-crewai)  
* 8  
  [https://www.truefoundry.com/blog/crewai-vs-langgraph](https://www.truefoundry.com/blog/crewai-vs-langgraph)  
* 10  
  [https://arxiv.org/html/2404.04834v4](https://arxiv.org/html/2404.04834v4)  
* 11  
  [https://www.researchgate.net/publication/387670287\_The\_Potential\_of\_LLMs\_in\_Automating\_Software\_Testing\_From\_Generation\_to\_Reporting](https://www.researchgate.net/publication/387670287_The_Potential_of_LLMs_in_Automating_Software_Testing_From_Generation_to_Reporting)  
* 22  
  [https://ai.meta.com/research/publications/augmented-language-models-a-survey/](https://ai.meta.com/research/publications/augmented-language-models-a-survey/)  
* 23  
  [https://openreview.net/forum?id=pV1xV2RK6I](https://openreview.net/forum?id=pV1xV2RK6I)  
* 24  
  [https://github.com/jingyi0000/VLM\_survey](https://github.com/jingyi0000/VLM_survey)  
* 12  
  [https://arxiv.org/html/2504.09724v3](https://arxiv.org/html/2504.09724v3)  
* 15  
  [https://www.letta.com/blog/memory-blocks](https://www.letta.com/blog/memory-blocks)  
* 14  
  [https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345](https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345)  
* 25  
  [https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/cs-enable-ai-generated-summary](https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/cs-enable-ai-generated-summary)  
* 26  
  [https://www.supportlogic.com/supportlogic-summarization-agent/](https://www.supportlogic.com/supportlogic-summarization-agent/)  
* 27  
  [https://ai.google.dev/gemini-api/docs/long-context](https://ai.google.dev/gemini-api/docs/long-context)  
* 28  
  [https://developer.nvidia.com/blog/scaling-to-millions-of-tokens-with-efficient-long-context-llm-training/](https://developer.nvidia.com/blog/scaling-to-millions-of-tokens-with-efficient-long-context-llm-training/)  
* 3  
  [https://arxiv.org/html/2503.10071v1](https://arxiv.org/html/2503.10071v1)  
* 1  
  [https://python.langchain.com/docs/tutorials/agents/](https://python.langchain.com/docs/tutorials/agents/)  
* 16  
  [https://www.scoutos.com/blog/llm-orchestration-key-tactics-and-tools](https://www.scoutos.com/blog/llm-orchestration-key-tactics-and-tools)  
* 6  
  [https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)  
* 17  
  [https://www.newline.co/@zaoyang/5-recovery-strategies-for-multi-agent-llm-failures--673fe4c4](https://www.newline.co/@zaoyang/5-recovery-strategies-for-multi-agent-llm-failures--673fe4c4)  
* 9  
  [https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development)  
* 29  
  [http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf](http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf)  
* 30  
  [https://github.com/X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent)  
* 13  
  [https://research.google/blog/screenai-a-visual-language-model-for-ui-and-visually-situated-language-understanding/](https://research.google/blog/screenai-a-visual-language-model-for-ui-and-visually-situated-language-understanding/)  
* 31  
  [https://machinelearning.apple.com/research/screen-relationships](https://machinelearning.apple.com/research/screen-relationships)  
* 18  
  [https://arxiv.org/html/2502.14638v1](https://arxiv.org/html/2502.14638v1)  
* 19  
  [https://arxiv.org/html/2405.17247v1](https://arxiv.org/html/2405.17247v1)  
* 32  
  [https://www.headspin.io/blog/6-popular-test-automation-tools-for-react-native-apps](https://www.headspin.io/blog/6-popular-test-automation-tools-for-react-native-apps)  
* 33  
  [https://reactnative.dev/docs/testing-overview](https://reactnative.dev/docs/testing-overview)  
* 34  
  [https://arxiv.org/html/2308.15272v4](https://arxiv.org/html/2308.15272v4)  
* 2  
  [https://huggingface.co/blog/Kseniase/action](https://huggingface.co/blog/Kseniase/action)  
* 14  
  [https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345](https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345)  
* 8  
  [https://www.truefoundry.com/blog/crewai-vs-langgraph](https://www.truefoundry.com/blog/crewai-vs-langgraph)  
* 29  
  [http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf](http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf)  
* 30  
  [https://github.com/X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent)  
* 14  
  [https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345](https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345)

#### **Referências citadas**

1. Build an Agent | 🦜️ LangChain, acessado em agosto 29, 2025, [https://python.langchain.com/docs/tutorials/agents/](https://python.langchain.com/docs/tutorials/agents/)  
2. \#13: Action\! How AI Agents Execute Tasks with UI and API Tools \- Hugging Face, acessado em agosto 29, 2025, [https://huggingface.co/blog/Kseniase/action](https://huggingface.co/blog/Kseniase/action)  
3. Advanced Tool Learning and Selection System (ATLASS): A Closed-Loop Framework Using LLM \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2503.10071v1](https://arxiv.org/html/2503.10071v1)  
4. Top 10 Python Frameworks for AI Agents ( Ranked) in 2025 \- Code B, acessado em agosto 29, 2025, [https://code-b.dev/blog/python-frameworks-ai-agent](https://code-b.dev/blog/python-frameworks-ai-agent)  
5. A curated list of awesome LLM agents frameworks. \- GitHub, acessado em agosto 29, 2025, [https://github.com/kaushikb11/awesome-llm-agents](https://github.com/kaushikb11/awesome-llm-agents)  
6. AI Agent Orchestration Patterns \- Azure Architecture Center | Microsoft Learn, acessado em agosto 29, 2025, [https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)  
7. LangGraph vs CrewAI: Let's Learn About the Differences \- ZenML Blog, acessado em agosto 29, 2025, [https://www.zenml.io/blog/langgraph-vs-crewai](https://www.zenml.io/blog/langgraph-vs-crewai)  
8. Crewai vs LangGraph: Know The Differences \- TrueFoundry, acessado em agosto 29, 2025, [https://www.truefoundry.com/blog/crewai-vs-langgraph](https://www.truefoundry.com/blog/crewai-vs-langgraph)  
9. Error Recovery and Fallback Strategies in AI Agent Development \- GoCodeo, acessado em agosto 29, 2025, [https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development)  
10. LLM-Based Multi-Agent Systems for Software Engineering: Literature Review, Vision and the Road Ahead \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2404.04834v4](https://arxiv.org/html/2404.04834v4)  
11. (PDF) The Potential of LLMs in Automating Software Testing: From Generation to Reporting, acessado em agosto 29, 2025, [https://www.researchgate.net/publication/387670287\_The\_Potential\_of\_LLMs\_in\_Automating\_Software\_Testing\_From\_Generation\_to\_Reporting](https://www.researchgate.net/publication/387670287_The_Potential_of_LLMs_in_Automating_Software_Testing_From_Generation_to_Reporting)  
12. A Survey on Efficient Vision-Language Models \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2504.09724v3](https://arxiv.org/html/2504.09724v3)  
13. ScreenAI: A visual language model for UI and visually-situated language understanding, acessado em agosto 29, 2025, [https://research.google/blog/screenai-a-visual-language-model-for-ui-and-visually-situated-language-understanding/](https://research.google/blog/screenai-a-visual-language-model-for-ui-and-visually-situated-language-understanding/)  
14. The Ultimate Guide to LLM Memory: From Context Windows to ..., acessado em agosto 29, 2025, [https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345](https://medium.com/@sonitanishk2003/the-ultimate-guide-to-llm-memory-from-context-windows-to-advanced-agent-memory-systems-3ec106d2a345)  
15. Memory Blocks: The Key to Agentic Context Management \- Letta, acessado em agosto 29, 2025, [https://www.letta.com/blog/memory-blocks](https://www.letta.com/blog/memory-blocks)  
16. LLM Orchestration: Key Tactics and Tools \- Scout, acessado em agosto 29, 2025, [https://www.scoutos.com/blog/llm-orchestration-key-tactics-and-tools](https://www.scoutos.com/blog/llm-orchestration-key-tactics-and-tools)  
17. 5 Recovery Strategies for Multi-Agent LLM Failures \- Newline.co, acessado em agosto 29, 2025, [https://www.newline.co/@zaoyang/5-recovery-strategies-for-multi-agent-llm-failures--673fe4c4](https://www.newline.co/@zaoyang/5-recovery-strategies-for-multi-agent-llm-failures--673fe4c4)  
18. Navig: Natural Language-guided Analysis with Vision Language Models for Image Geo-localization \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2502.14638v1](https://arxiv.org/html/2502.14638v1)  
19. An Introduction to Vision-Language Modeling \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2405.17247v1](https://arxiv.org/html/2405.17247v1)  
20. Automated Testing with Jest and React Testing Library: A Complete Guide | by Erick Zanetti, acessado em agosto 29, 2025, [https://medium.com/@erickzanetti/automated-testing-with-jest-and-react-testing-library-a-complete-guide-272a06c94301](https://medium.com/@erickzanetti/automated-testing-with-jest-and-react-testing-library-a-complete-guide-272a06c94301)  
21. Testing Overview \- React, acessado em agosto 29, 2025, [https://legacy.reactjs.org/docs/testing.html](https://legacy.reactjs.org/docs/testing.html)  
22. Augmented Language Models: a Survey | Research \- AI at Meta, acessado em agosto 29, 2025, [https://ai.meta.com/research/publications/augmented-language-models-a-survey/](https://ai.meta.com/research/publications/augmented-language-models-a-survey/)  
23. ToolQA: A Dataset for LLM Question Answering with External Tools \- OpenReview, acessado em agosto 29, 2025, [https://openreview.net/forum?id=pV1xV2RK6I](https://openreview.net/forum?id=pV1xV2RK6I)  
24. jingyi0000/VLM\_survey: Collection of AWESOME vision-language models for vision tasks \- GitHub, acessado em agosto 29, 2025, [https://github.com/jingyi0000/VLM\_survey](https://github.com/jingyi0000/VLM_survey)  
25. Set up auto-summarization for conversations in Dynamics 365 Customer Service, acessado em agosto 29, 2025, [https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/cs-enable-ai-generated-summary](https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/cs-enable-ai-generated-summary)  
26. Summarization Agent | SupportLogic, acessado em agosto 29, 2025, [https://www.supportlogic.com/supportlogic-summarization-agent/](https://www.supportlogic.com/supportlogic-summarization-agent/)  
27. Long context | Gemini API | Google AI for Developers, acessado em agosto 29, 2025, [https://ai.google.dev/gemini-api/docs/long-context](https://ai.google.dev/gemini-api/docs/long-context)  
28. Scaling to Millions of Tokens with Efficient Long-Context LLM Training \- NVIDIA Developer, acessado em agosto 29, 2025, [https://developer.nvidia.com/blog/scaling-to-millions-of-tokens-with-efficient-long-context-llm-training/](https://developer.nvidia.com/blog/scaling-to-millions-of-tokens-with-efficient-long-context-llm-training/)  
29. Test-Agent: A Multimodal App Automation Testing ... \- Yangyang Li, acessado em agosto 29, 2025, [http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf](http://www.liyangyang.com/wp-content/uploads/2024/12/DTPI24-Agent-YangyangLi.pdf)  
30. X-PLUG/MobileAgent: Mobile-Agent: The Powerful GUI ... \- GitHub, acessado em agosto 29, 2025, [https://github.com/X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent)  
31. Understanding Screen Relationships from Screenshots of Smartphone Applications, acessado em agosto 29, 2025, [https://machinelearning.apple.com/research/screen-relationships](https://machinelearning.apple.com/research/screen-relationships)  
32. 6 Automation Tools & Frameworks for React Native App Testing \- HeadSpin, acessado em agosto 29, 2025, [https://www.headspin.io/blog/6-popular-test-automation-tools-for-react-native-apps](https://www.headspin.io/blog/6-popular-test-automation-tools-for-react-native-apps)  
33. Testing \- React Native, acessado em agosto 29, 2025, [https://reactnative.dev/docs/testing-overview](https://reactnative.dev/docs/testing-overview)  
34. AutoDroid: LLM-powered Task Automation in Android \- arXiv, acessado em agosto 29, 2025, [https://arxiv.org/html/2308.15272v4](https://arxiv.org/html/2308.15272v4)