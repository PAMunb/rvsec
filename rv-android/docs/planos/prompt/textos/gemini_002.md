

# **O Estado da Arte em Otimização de Large Language Models: Uma Análise Técnica de Prompts e Inferência**

### **Resumo Executivo**

O desempenho de um Large Language Model (LLM) na vanguarda da tecnologia é uma função da sinergia entre duas disciplinas críticas e inter-relacionadas: a engenharia de prompt e a otimização de inferência. A engenharia de prompt evoluiu de uma prática intuitiva para um campo técnico, com a ascensão de frameworks de raciocínio sofisticados, como o Tree-of-Thought (ToT) e o Self-Consistency, que aprimoram a acurácia do modelo ao emular estratégias cognitivas humanas de resolução de problemas. Paralelamente, a otimização de inferência transformou o desempenho de execução, utilizando abordagens como a quantização e o speculative decoding para mitigar os gargalos computacionais inerentes aos modelos de grande escala.

A otimização de ponta não reside em uma única técnica, mas na orquestração inteligente de ambas as áreas. A adoção de prompts complexos, embora melhore a qualidade das respostas, pode aumentar a latência e o custo. Em contrapartida, as otimizações de nível de sistema, como a compressão do modelo e a aceleração algorítmica, tornam o uso dessas técnicas avançadas de prompt economicamente viável e tecnicamente escalável. O presente relatório detalha o estado da arte em ambas as esferas, analisando os trade-offs, as interconexões e os benchmarks empíricos. O sucesso na aplicação desses modelos reside na calibração fina das estratégias para cada caso de uso, equilibrando de forma ideal a precisão com a eficiência.

### **Introdução: O Paradigma da Otimização em LLMs**

A rápida adoção de Large Language Models (LLMs) em diversas aplicações, da automação de tarefas ao suporte à decisão, tem evidenciado um desafio fundamental: seu alto custo computacional e latência. A pesquisa no "estado da arte" em otimização de LLMs é impulsionada pela necessidade de tornar a inferência de modelos mais rápida, eficiente e acessível para o uso em escala real.1 Esta otimização é um esforço multifacetado que se baseia em dois pilares: a engenharia de prompt, que manipula a entrada para guiar o comportamento do modelo, e a otimização de inferência, que aprimora o processo de execução no nível do sistema.

Para avaliar o sucesso das estratégias de otimização, é crucial definir as métricas de desempenho. A performance de um LLM pode ser medida tanto em termos de **qualidade** quanto de **eficiência**. A qualidade da saída abrange acurácia, coerência, e relevância, frequentemente avaliada por benchmarks padronizados como MMLU, GSM8K e HumanEval.3 A eficiência, por sua vez, é quantificada por métricas como a

**latência**, o **throughput** e o **custo**. A latência de inferência é tipicamente dividida em duas componentes principais: o **Tempo para a Primeira Token (TTFT)**, que mede a responsividade inicial do modelo e é diretamente influenciada pelo comprimento do prompt de entrada, e o **Tempo por Token de Saída (TPOT)**, que mede a velocidade de geração de tokens subsequentes.4 O throughput é medido em tokens por segundo (TPS) ou requests por segundo (RPS) e indica a capacidade do sistema de processar múltiplas solicitações simultaneamente.5 Por fim, o custo é um fator crítico, diretamente ligado ao consumo de tokens e aos recursos de hardware.6

Apesar do rápido avanço, a área de engenharia de prompt ainda sofre com uma terminologia fragmentada e uma compreensão ontológica inconsistente, um desafio que artigos de pesquisa recentes buscam endereçar através da criação de taxonomias unificadas de técnicas.7 Este relatório busca preencher essa lacuna, fornecendo uma análise estruturada das técnicas de ponta em ambas as disciplinas e explorando a complexa relação entre elas.

### **Seção I: A Vanguarda da Engenharia de Prompt para Raciocínio Complexo**

As técnicas de engenharia de prompt evoluíram significativamente, passando de instruções simples para a formulação de prompts que funcionam como verdadeiros frameworks de raciocínio. A abordagem mais avançada não se limita a pedir uma resposta, mas a instruir o modelo sobre como "pensar" para chegar a essa resposta.

#### **1.1. Técnicas de Decomposição e Raciocínio Deliberado**

**Tree-of-Thought (ToT)**

O Tree-of-Thought (ToT) é um framework avançado que generaliza a técnica do Chain-of-Thought (CoT) ao permitir que o LLM explore múltiplos caminhos de raciocínio de forma estruturada, semelhante a um algoritmo de busca em árvore.9 Essa abordagem simula as estratégias de resolução de problemas da cognição humana, permitindo que o modelo realize um "lookahead" e retroceda (

*backtrack*) quando um caminho de solução se mostra inviável.9

O mecanismo do ToT opera em duas etapas principais. Primeiro, um prompt de "proposição" é utilizado para gerar possíveis soluções parciais. Em seguida, um prompt de "avaliação" orienta o modelo a avaliar o progresso através de cada uma dessas soluções intermediárias, combinando-se com algoritmos de busca tradicionais, como o BFS (*Breadth-First Search*) ou o DFS (*Depth-First Search*), para uma exploração sistemática.9 A pesquisa demonstra que o ToT supera significativamente outras técnicas de prompt em tarefas que exigem planejamento e raciocínio multi-etapa, como o "Jogo do 24" e quebra-cabeças. Em um benchmark de quebra-cabeças, o ToT alcançou uma taxa de sucesso de 20%, em contraste com a taxa de 1% do CoT.9 A técnica também se mostra eficaz em tarefas de escrita criativa.9

**Self-Consistency**

A técnica do Self-Consistency foi proposta como uma estratégia para aprimorar o desempenho do Chain-of-Thought (CoT) ao substituir a decodificação gananciosa (*naive greedy decoding*) por um processo de agregação.12 A ideia central é que um problema de raciocínio complexo pode ter múltiplos caminhos de pensamento válidos, todos levando à mesma resposta correta.14 Para aproveitar essa propriedade, o modelo é instruído a gerar um conjunto diversificado de caminhos de raciocínio para uma única consulta. A resposta final é então selecionada com base em uma verificação de consistência ou por um sistema de votação de maioria entre os diferentes resultados gerados.12

Essa abordagem aumenta a acurácia em tarefas de raciocínio aritmético e senso comum.12 Ao usar a agregação, a técnica se torna mais robusta contra erros individuais ou vieses que possam surgir em uma única cadeia de raciocínio, resultando em uma resposta mais confiável.16 O Self-Consistency é uma técnica não supervisionada que não requer anotação humana adicional ou ajuste fino do modelo.17 A pesquisa também indica que os benefícios de desempenho aumentam com a escala do modelo.17 Os casos de uso práticos da técnica incluem análise de risco financeiro, diagnóstico médico e otimização de algoritmos quânticos.14

**Least-to-Most (LtM)**

O Least-to-Most (LtM) é um método que aumenta a capacidade de resolução de problemas dos LLMs ao decompor tarefas complexas em uma série de subproblemas mais simples.18 A característica distintiva do LtM é que os subproblemas são resolvidos sequencialmente, e a solução de cada um é adicionada como contexto de entrada para o subproblema seguinte.19 O processo é dividido em duas fases: na fase de decomposição, o prompt guia o modelo para listar os subproblemas; na fase de resolução, o modelo soluciona cada subproblema um a um, encadeando as respostas para construir a solução final.18

A progressão do CoT para o Self-Consistency, ToT e LtM ilustra a evolução da engenharia de prompt de uma "instrução de raciocínio" para uma "arquitetura de raciocínio". Enquanto o CoT oferece uma única linha de pensamento, que pode ser frágil e levar a um único caminho incorreto, o Self-Consistency resolve isso com redundância e agregação. O ToT, por sua vez, aprofunda a estratégia com uma busca ativa por múltiplos caminhos de solução. O LtM foca na quebra explícita de subproblemas para que a resposta de um seja o input para o próximo, criando uma dependência sequencial mais forte que a de um simples CoT. O avanço demonstra um movimento em direção a prompts que incentivam a autocorreção e a autoavaliação, tornando os modelos mais robustos e menos suscetíveis a alucinações em tarefas críticas.

#### **1.2. Otimização Estrutural e de Conteúdo do Prompt**

A estrutura e o conteúdo do prompt são fatores cruciais para a performance do modelo. A pesquisa demonstra um trade-off fundamental entre expressividade e eficiência. Prompts excessivamente longos e verbosos podem introduzir ruído e instruções conflitantes, prejudicando a performance do LLM e aumentando os custos e a latência.21 O custo de API e o tempo de processamento escalam diretamente com o número de tokens de entrada.6

Para otimizar essa relação, a pesquisa sugere técnicas de **compressão de prompt**.6 A

**destilação de informação** é uma técnica que condensa textos longos em resumos concisos, mantendo a mensagem central.6 O

**design estruturado** utiliza tags simbólicas (\<goal\>, \<context\>, \<format\>) e listas para criar prompts modulares e bem organizados, melhorando a legibilidade e a precisão das saídas.24 Finalmente, a

**extração de palavras-chave** é um método eficaz para tarefas de recuperação de informação.6

Estudos comparativos mostram que sistemas de otimização de prompt baseados em IA podem produzir prompts de melhor desempenho em uma fração do tempo (10 minutos) se comparado ao trabalho manual (20 horas), o que indica que a otimização automatizada é o novo paradigma de ponta.21

Um prompt ideal para acurácia é frequentemente o pior em termos de eficiência e custo. Prompts complexos para raciocínio (como os de ToT ou Self-Consistency), embora melhorem a qualidade, tendem a ser mais longos, aumentando a latência e o custo de inferência. A otimização de prompts, portanto, não é apenas uma questão de economia, mas de qualidade. A arte de engenharia de prompts de alto nível reside em condensar a verbosidade para manter a estrutura e o contexto, transformando a disciplina da intuição em uma ciência da otimização estrutural.

**Tabela 1: Comparativo de Técnicas de Prompting Avançadas**

| Característica | Tree-of-Thought (ToT) | Self-Consistency | Least-to-Most (LtM) |
| :---- | :---- | :---- | :---- |
| **Complexidade** | Alta. Requer múltiplos prompts e algoritmos de busca. | Moderada. Requer múltiplas execuções e uma estratégia de votação. | Moderada a Alta. Requer decomposição explícita do problema. |
| **Custo Computacional** | Alto. Múltiplas chamadas ao modelo (proporcional ao número de caminhos explorados). | Alto. Múltiplas chamadas ao modelo (geralmente fixo). | Moderado a Alto. Depende do número de subproblemas. |
| **Principal Vantagem** | Acurácia superior em tarefas que exigem planejamento e lookahead. | Aumento significativo da acurácia em tarefas de raciocínio. | Maior acurácia em problemas complexos decomponíveis. |
| **Limitações** | Intensivo em recursos. Não é eficiente para tarefas simples. | Custo computacional elevado. Menos eficaz para tarefas com múltiplas respostas válidas. | Pode ser ineficiente se a decomposição for mal definida. |
| **Casos de Uso Ideais** | Resolução de quebra-cabeças, escrita criativa, raciocínio matemático complexo. | Problemas de lógica e aritmética, análise financeira, diagnóstico médico. | Planejamento de projetos, roteiros de viagem, análise de dados. |

### **Seção II: Otimização de Inferência: A Eficiência no Nível do Sistema**

A otimização da inferência foca em como o modelo é executado no hardware, visando melhorar a velocidade, o throughput e a eficiência de custo.

#### **2.1. Métodos de Compressão de Modelo**

**Quantização**

A quantização é a técnica de reduzir a precisão numérica dos parâmetros de um modelo (pesos e ativações) de 32 ou 16-bit para 8 ou 4-bit.2 O principal benefício é a significativa redução no uso de memória e um aumento na velocidade de inferência.28

As abordagens mais recentes se concentram em minimizar a perda de acurácia, que é o principal trade-off da quantização.31

* **GPTQ (Generalized Post-Training Quantization):** Um método de quantização pós-treinamento que utiliza informações de segunda ordem para comprimir o modelo.32 Ele oferece flexibilidade nos níveis de quantização, de 8-bit a 2-bit.32  
* **AWQ (Activation-Aware Weight Quantization):** Esta abordagem "sensível à ativação" protege os pesos mais importantes para a acurácia, observando os padrões de ativação do modelo. A pesquisa indica que o AWQ frequentemente supera o GPTQ e pode até se aproximar da performance de modelos de precisão total em alguns benchmarks.32  
* **OmniQuant:** Uma técnica de quantização calibrada que visa minimizar a perda de informação durante o processo de conversão.35

A análise de trade-offs de qualidade em modelos quantizados demonstra que a perda de acurácia é mais severa em modelos menores e em tarefas de raciocínio complexo, como código e matemática.26 A pesquisa também mostra que a perda de qualidade pode ser mitigada mantendo as ativações em precisão mais alta (por exemplo, 16-bit) enquanto se quantiza os pesos para 4-bit.26

**Destilação de Conhecimento (Knowledge Distillation)**

A destilação de conhecimento é o processo de transferir a expertise de um modelo maior e mais lento ("professor") para um modelo menor e mais rápido ("aluno"), permitindo que o modelo menor mantenha uma alta performance com menos parâmetros.36

Um estudo de caso notável no domínio biomédico ilustra o potencial dessa técnica.38 Através da destilação de dados de alta qualidade de uma vasta biblioteca de resumos do PubMed, um modelo menor (Llama3-70B) foi capaz de superar um modelo maior (GPT-4) em tarefas de resposta a perguntas, apesar do GPT-4 possuir um número de parâmetros várias vezes maior. Este exemplo demonstra que a qualidade do conjunto de dados de treinamento pode ser um fator mais crítico para a performance do que o tamanho do modelo em si, permitindo que a destilação de conhecimento crie modelos de domínio menores e mais eficientes.38

#### **2.2. Otimizações Algorítmicas e de Hardware**

**Speculative Decoding (SD)**

O speculative decoding é uma técnica que acelera a inferência do LLM ao quebrar o gargalo sequencial da geração token-a-token.39 A abordagem utiliza um modelo menor e mais rápido ("modelo rascunho") para gerar vários tokens preliminares de uma só vez, que são então verificados em paralelo por um modelo maior e mais preciso.40 Se os tokens do rascunho forem aceitos, o processo avança rapidamente; se forem rejeitados, o modelo principal gera os tokens corretos.40

O SD pode reduzir a latência de resposta em 30-40% e o uso de recursos computacionais pela metade, sem comprometer a qualidade do output.40 A pesquisa mais recente foca em inovações como a verificação baseada em árvore (

*tree-based verification*) para processar múltiplos tokens de forma mais eficiente.41 No entanto, um desafio emergente é a ineficácia do SD com arquiteturas

*Mixture-of-Experts* (MoE).42 O speculative decoding funciona porque a verificação paralela não aumenta a sobrecarga de busca de pesos em modelos densos. Em um modelo MoE, no entanto, cada token ativa um subconjunto de "experts," e a verificação de múltiplos tokens pode levar a um aumento de 2-3x no movimento de dados para buscar todos os especialistas ativados, tornando a técnica contraproducente.42 Este fenômeno demonstra que a eficácia de uma otimização de inferência depende criticamente da arquitetura do modelo.

**Paralelismo de Modelo (Tensor vs. Pipeline)**

Para modelos que não cabem em uma única GPU, o paralelismo é uma estratégia essencial.43 O

**paralelismo de tensor** divide as camadas do modelo horizontalmente, exigindo alta comunicação entre as GPUs.43 É eficaz na fase de decodificação, mas sofre com uma sobrecarga substancial na fase de

*prefill* (processamento do prompt de entrada).44 O

**paralelismo de pipeline**, por outro lado, divide o modelo verticalmente (camadas) em diferentes GPUs.43 Embora reduza a comunicação de dados de

*tensors*, é mais lento na fase de decodificação devido à micro-batching e ao carregamento repetitivo de pesos.44

A análise desses mecanismos revela que não existe uma solução única que se adapte a todas as cargas de trabalho. O melhor desempenho é geralmente alcançado através de uma combinação de ambas as abordagens, calibrada para as características da tarefa.43

A pesquisa aponta uma tensão entre as otimizações no nível do modelo e as otimizações no nível do sistema. As otimizações de modelo (quantização, destilação) modificam o modelo para torná-lo mais leve, enquanto as otimizações de sistema (SD, paralelismo) alteram a forma como o modelo é executado. Essas abordagens não são mutuamente exclusivas, mas sim complementares. Uma estratégia de ponta combina um modelo otimizado (destilado e quantizado) servido com técnicas de aceleração algorítmica e paralelismo.

**Tabela 2: Comparativo Técnico de Abordagens de Quantização**

| Característica | GPTQ | AWQ | Outras Abordagens |
| :---- | :---- | :---- | :---- |
| **Impacto na Acurácia** | Desempenho geralmente inferior a AWQ, pode sofrer de overfitting. | Mantém a acurácia próxima ao modelo de precisão total, especialmente para LLMs ajustados. | Variável. Modelos menores sofrem perdas mais severas (até 92% em tarefas de código).26 |
| **Velocidade de Inferência** | Oferece ganhos de velocidade e é compatível com a maioria das GPUs. | Acelera a geração de tokens e reduz o uso de memória da GPU.32 | Depende do método. Geralmente, maior compressão resulta em mais velocidade. |
| **Vantagens Principais** | Flexibilidade e suporte a uma ampla gama de níveis de bit.32 | Protege os pesos mais importantes com base nas ativações, resultando em maior acurácia.27 | Abordagens como o *SmoothQuant* focam na calibração de ativações para reduzir erros.27 |
| **Limitações** | Pode apresentar variações de output e desempenho em diferentes GPUs.43 | Pode ser menos eficaz em modelos que não foram ajustados com instruções.32 | Trade-off significativo entre acurácia e eficiência, especialmente para tarefas de raciocínio complexo.26 |
| **Hardware Recomendado** | GPUs de consumo (ex: RTX 3090\) são suficientes para execução.33 | Integrado em frameworks como NVIDIA TensorRT-LLM e vLLM para GPU.32 | Depende do método e do modelo. Hardware avançado (GPU/TPU) é necessário.28 |

### **Seção III: Análise de Trade-offs, Benchmarks e Casos de Uso**

A otimização de LLMs é uma busca por um equilíbrio ideal. O uso de prompts que geram mais tokens (como o CoT ou o ToT) melhora a acurácia, mas aumenta o custo de inferência, trocando recursos computacionais por desempenho.46 Essa tensão entre a otimização de prompt (visando a qualidade) e a otimização de inferência (visando a eficiência) é fundamental para a aplicação prática dos modelos.

#### **3.1. Análise de Benchmarks de Qualidade e Performance**

Benchmarks públicos, como o MLPerf Inference v4.0, fornecem dados padronizados para comparar modelos e frameworks em condições controladas.48 O MLPerf v4.0 incluiu o modelo Llama 2 70B, fornecendo métricas de referência para latência. Para o cenário de inferência interativa, as latências de referência são de

**TTFT \<= 450 ms** e **TPOT \<= 40 ms**.50

A pesquisa demonstra que o comprimento do prompt de entrada é um dos fatores mais influentes no TTFT. Um prompt mais longo requer mais processamento na fase de *prefill* antes que o primeiro token possa ser gerado.4

**Tabela 3: Métricas de Desempenho de Inferência de Referência (Llama 2 70B no MLPerf)**

| Métrica | Cenário Interativo | Descrição |
| :---- | :---- | :---- |
| **TTFT** | \<= 450 ms | Tempo para o modelo começar a responder. A latência de entrada. |
| **TPOT** | \<= 40 ms | Tempo médio para gerar cada token subsequente. A latência de saída. |
| **Latência Total** | TTFT \+ (TPOT x tokens de saída) | Tempo total desde o envio da requisição até a conclusão da resposta. |
| **Throughput** | Não detalhado no snippet 49 | Capacidade do sistema em processar tokens ou requisições por segundo. |

#### **3.2. A Interconexão entre Prompting e Inferência**

O relacionamento entre a engenharia de prompt e a otimização de inferência é complexo e não-linear. As otimizações de inferência movem a "fronteira de Pareto" do desempenho, permitindo um maior desempenho (em latência/throughput) e/ou um menor custo para um dado nível de qualidade. A decisão sobre a combinação ideal de técnicas depende do caso de uso. Para uma aplicação de chatbot, um baixo TTFT é crucial para a experiência do usuário, justificando a preferência por prompts concisos e quantização agressiva.5 Em contraste, um sistema de diagnóstico médico exige precisão absoluta, tornando o custo de um prompt Self-Consistency e de um modelo de precisão total aceitável.

### **Conclusões e Recomendações Estratégicas**

A otimização do "estado da arte" em LLMs é uma disciplina unificada, na qual a engenharia de prompt atua no nível da "lógica" do modelo (o que ele pensa), enquanto a otimização de inferência opera no nível da "execução" (como ele computa). As descobertas apresentadas indicam que a abordagem mais eficaz é a holística, que considera a pilha tecnológica completa, do prompt ao hardware.

#### **Recomendações Práticas**

1. **Definir o Caso de Uso:** A escolha de técnicas deve ser orientada por um trade-off explícito entre qualidade e eficiência. A otimização não é um objetivo único, mas uma calibração para as necessidades específicas da aplicação.  
2. **Adotar Otimização Automatizada de Prompts:** Utilizar ferramentas que geram e otimizam prompts automaticamente para garantir a clareza e a precisão sem a verbosidade manual.21  
3. **Implementar uma Estratégia "Full-Stack":** A combinação de otimizações de modelo (quantização AWQ para acurácia equilibrada, destilação de conhecimento para modelos de domínio) e otimizações de sistema (speculative decoding, paralelismo híbrido) é a via para atingir o desempenho ideal.

#### **Desafios em Aberto e Direções Futuras**

A pesquisa na área aponta para vários desafios em aberto. A falta de padronização na terminologia de prompt é uma barreira que impede a reprodutibilidade de resultados.7 A superação dos desafios do speculative decoding para arquiteturas MoE é um foco de pesquisa atual.42 Finalmente, a direção mais promissora é o desenvolvimento de frameworks integrados, onde a complexidade e os requisitos de um prompt de entrada informam dinamicamente a estratégia de otimização de inferência ideal a ser utilizada, criando um sistema de auto-otimização adaptativo.

#### **Referências citadas**

1. Otimização de Inferência em LLMs na CPU: Análise do Cenário Atual | Anais da Escola Regional de Alto Desempenho de São Paulo (ERAD-SP) \- SOL-SBC, acessado em agosto 28, 2025, [https://sol.sbc.org.br/index.php/eradsp/article/view/36423](https://sol.sbc.org.br/index.php/eradsp/article/view/36423)  
2. LLM Inference Optimization Techniques: A Comprehensive Analysis | by Sahin Ahmed, Data Scientist | Medium, acessado em agosto 28, 2025, [https://medium.com/@sahin.samia/llm-inference-optimization-techniques-a-comprehensive-analysis-1c434e85ba7c](https://medium.com/@sahin.samia/llm-inference-optimization-techniques-a-comprehensive-analysis-1c434e85ba7c)  
3. LLM Benchmarks: Overview, Limits and Model Comparison \- Vellum AI, acessado em agosto 28, 2025, [https://www.vellum.ai/blog/llm-benchmarks-overview-limits-and-model-comparison](https://www.vellum.ai/blog/llm-benchmarks-overview-limits-and-model-comparison)  
4. A Guide to LLM Inference Performance Monitoring | Symbl.ai, acessado em agosto 28, 2025, [https://symbl.ai/developers/blog/a-guide-to-llm-inference-performance-monitoring/](https://symbl.ai/developers/blog/a-guide-to-llm-inference-performance-monitoring/)  
5. Key metrics for LLM inference \- BentoML, acessado em agosto 28, 2025, [https://bentoml.com/llm/inference-optimization/llm-inference-metrics](https://bentoml.com/llm/inference-optimization/llm-inference-metrics)  
6. Prompt Compression in Large Language Models (LLMs): Making ..., acessado em agosto 28, 2025, [https://medium.com/@sahin.samia/prompt-compression-in-large-language-models-llms-making-every-token-count-078a2d1c7e03](https://medium.com/@sahin.samia/prompt-compression-in-large-language-models-llms-making-every-token-count-078a2d1c7e03)  
7. \[2406.06608\] The Prompt Report: A Systematic Survey of Prompt Engineering Techniques, acessado em agosto 28, 2025, [https://arxiv.org/abs/2406.06608](https://arxiv.org/abs/2406.06608)  
8. A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications \- arXiv, acessado em agosto 28, 2025, [https://arxiv.org/abs/2402.07927](https://arxiv.org/abs/2402.07927)  
9. Tree of Thoughts (ToT): Enhancing Problem-Solving in LLMs \- Learn Prompting, acessado em agosto 28, 2025, [https://learnprompting.org/docs/advanced/decomposition/tree\_of\_thoughts](https://learnprompting.org/docs/advanced/decomposition/tree_of_thoughts)  
10. What is Tree Of Thoughts Prompting? | IBM, acessado em agosto 28, 2025, [https://www.ibm.com/think/topics/tree-of-thoughts](https://www.ibm.com/think/topics/tree-of-thoughts)  
11. Tree of Thoughts (ToT) | Prompt Engineering Guide, acessado em agosto 28, 2025, [https://www.promptingguide.ai/techniques/tot](https://www.promptingguide.ai/techniques/tot)  
12. Self-Consistency | Prompt Engineering Guide, acessado em agosto 28, 2025, [https://www.promptingguide.ai/techniques/consistency](https://www.promptingguide.ai/techniques/consistency)  
13. Self-Consistency Improves Chain of Thought Reasoning in Language Models \- arXiv, acessado em agosto 28, 2025, [https://arxiv.org/abs/2203.11171](https://arxiv.org/abs/2203.11171)  
14. What is Self-Consistency Prompting? \- Digital Adoption, acessado em agosto 28, 2025, [https://www.digital-adoption.com/self-consistency-prompting/](https://www.digital-adoption.com/self-consistency-prompting/)  
15. Self-Consistency and Universal Self-Consistency Prompting \- PromptHub, acessado em agosto 28, 2025, [https://www.prompthub.us/blog/self-consistency-and-universal-self-consistency-prompting](https://www.prompthub.us/blog/self-consistency-and-universal-self-consistency-prompting)  
16. Advanced Prompt Engineering — Self-Consistency, Tree-of-Thoughts, RAG | by Sulbha Jain, acessado em agosto 28, 2025, [https://medium.com/@sulbha.jindal/advanced-prompt-engineering-self-consistency-tree-of-thoughts-rag-17a2d2c8fb79](https://medium.com/@sulbha.jindal/advanced-prompt-engineering-self-consistency-tree-of-thoughts-rag-17a2d2c8fb79)  
17. Prompt Engineering for Large Language Models: A Systematic Review and Future Directions \- ResearchGate, acessado em agosto 28, 2025, [https://www.researchgate.net/publication/392015598\_Prompt\_Engineering\_for\_Large\_Language\_Models\_A\_Systematic\_Review\_and\_Future\_Directions](https://www.researchgate.net/publication/392015598_Prompt_Engineering_for_Large_Language_Models_A_Systematic_Review_and_Future_Directions)  
18. Least-to-Most Prompting Guide \- PromptHub, acessado em agosto 28, 2025, [https://www.prompthub.us/blog/least-to-most-prompting-guide](https://www.prompthub.us/blog/least-to-most-prompting-guide)  
19. Least-to-Most Prompting, acessado em agosto 28, 2025, [https://learnprompting.org/docs/intermediate/least\_to\_most](https://learnprompting.org/docs/intermediate/least_to_most)  
20. learnprompting.org, acessado em agosto 28, 2025, [https://learnprompting.org/docs/intermediate/least\_to\_most\#:\~:text=Definition%3A%20Least%2Dto%2DMost,as%20input%20for%20the%20next.](https://learnprompting.org/docs/intermediate/least_to_most#:~:text=Definition%3A%20Least%2Dto%2DMost,as%20input%20for%20the%20next.)  
21. Prompt Engineering em 2025: 6 Mitos que Estão Errados Segundo 1500 Estudos \- RDD10+, acessado em agosto 28, 2025, [https://www.robertodiasduarte.com.br/prompt-engineering-em-2025-6-mitos-que-estao-errados-segundo-1500-estudos/](https://www.robertodiasduarte.com.br/prompt-engineering-em-2025-6-mitos-que-estao-errados-segundo-1500-estudos/)  
22. How to Optimize Token Efficiency When Prompting \- Portkey, acessado em agosto 28, 2025, [https://portkey.ai/blog/optimize-token-efficiency-in-prompts](https://portkey.ai/blog/optimize-token-efficiency-in-prompts)  
23. Savings in Your AI Prompts: How We Reduced Token Usage by Up to 10% \- Requesty, acessado em agosto 28, 2025, [https://www.requesty.ai/blog/savings-in-your-ai-prompts-how-we-reduced-token-usage-by-up-to-10](https://www.requesty.ai/blog/savings-in-your-ai-prompts-how-we-reduced-token-usage-by-up-to-10)  
24. Engenharia de Prompts Avançada: Controle e Precisão \- RDD10+ \- Roberto Dias Duarte, acessado em agosto 28, 2025, [https://www.robertodiasduarte.com.br/engenharia-de-prompts-avancada-controle-e-precisao/](https://www.robertodiasduarte.com.br/engenharia-de-prompts-avancada-controle-e-precisao/)  
25. Use nosso melhorador de prompts para otimizar seus prompts \- Anthropic API, acessado em agosto 28, 2025, [https://docs.anthropic.com/pt/docs/build-with-claude/prompt-engineering/prompt-improver](https://docs.anthropic.com/pt/docs/build-with-claude/prompt-engineering/prompt-improver)  
26. The Newbie's Handbook on LLM Quantization and Model Compression \- GoPenAI, acessado em agosto 28, 2025, [https://blog.gopenai.com/the-newbies-handbook-on-llm-quantization-and-model-compression-b0e649c709de](https://blog.gopenai.com/the-newbies-handbook-on-llm-quantization-and-model-compression-b0e649c709de)  
27. Optimizing LLMs for Performance and Accuracy with Post-Training Quantization, acessado em agosto 28, 2025, [https://developer.nvidia.com/blog/optimizing-llms-for-performance-and-accuracy-with-post-training-quantization/](https://developer.nvidia.com/blog/optimizing-llms-for-performance-and-accuracy-with-post-training-quantization/)  
28. Práticas recomendadas para otimizar a inferência de modelos de linguagem grandes com GPUs no Google Kubernetes Engine (GKE), acessado em agosto 28, 2025, [https://cloud.google.com/kubernetes-engine/docs/best-practices/machine-learning/inference/llm-optimization?hl=pt-br](https://cloud.google.com/kubernetes-engine/docs/best-practices/machine-learning/inference/llm-optimization?hl=pt-br)  
29. LLM Inference Optimization: Speed, Scale, and Savings \- Ghost, acessado em agosto 28, 2025, [https://latitude-blog.ghost.io/blog/llm-inference-optimization-speed-scale-and-savings/](https://latitude-blog.ghost.io/blog/llm-inference-optimization-speed-scale-and-savings/)  
30. LLM Inference Optimization: Challenges, benefits (+ checklist) \- Tredence, acessado em agosto 28, 2025, [https://www.tredence.com/blog/llm-inference-optimization](https://www.tredence.com/blog/llm-inference-optimization)  
31. Systematic Characterization of LLM Quantization: A Performance, Energy, and Quality Perspective \- arXiv, acessado em agosto 28, 2025, [https://arxiv.org/html/2508.16712v1](https://arxiv.org/html/2508.16712v1)  
32. Which Quantization Method Is Best for You?: GGUF, GPTQ, or AWQ \- E2E Cloud, acessado em agosto 28, 2025, [https://www.e2enetworks.com/blog/which-quantization-method-is-best-for-you-gguf-gptq-or-awq](https://www.e2enetworks.com/blog/which-quantization-method-is-best-for-you-gguf-gptq-or-awq)  
33. Why LLM Benchmarks Can Be Misleading \- AWQ vs. GPTQ \- bitbasti, acessado em agosto 28, 2025, [https://bitbasti.com/blog/why-you-should-not-trust-benchmarks](https://bitbasti.com/blog/why-you-should-not-trust-benchmarks)  
34. Combining and Quantizing LLMs for Enhanced Performance \- inovex GmbH, acessado em agosto 28, 2025, [https://www.inovex.de/de/blog/combining-and-quantizing-llms-for-enhanced-performance/](https://www.inovex.de/de/blog/combining-and-quantizing-llms-for-enhanced-performance/)  
35. Zhen-Dong/Awesome-Quantization-Papers: List of papers related to neural network quantization in recent AI conferences and journals. \- GitHub, acessado em agosto 28, 2025, [https://github.com/Zhen-Dong/Awesome-Quantization-Papers](https://github.com/Zhen-Dong/Awesome-Quantization-Papers)  
36. LLM Model Pruning and Knowledge Distillation with NVIDIA NeMo Framework, acessado em agosto 28, 2025, [https://developer.nvidia.com/blog/llm-model-pruning-and-knowledge-distillation-with-nvidia-nemo-framework/](https://developer.nvidia.com/blog/llm-model-pruning-and-knowledge-distillation-with-nvidia-nemo-framework/)  
37. Awesome Knowledge Distillation of LLM Papers \- GitHub, acessado em agosto 28, 2025, [https://github.com/Tebmer/Awesome-Knowledge-Distillation-of-LLMs](https://github.com/Tebmer/Awesome-Knowledge-Distillation-of-LLMs)  
38. Knowledge Hierarchy Guided Biological-Medical Dataset Distillation ..., acessado em agosto 28, 2025, [https://arxiv.org/abs/2501.15108](https://arxiv.org/abs/2501.15108)  
39. feifeibear/LLMSpeculativeSampling: Fast inference from large lauguage models via speculative decoding \- GitHub, acessado em agosto 28, 2025, [https://github.com/feifeibear/LLMSpeculativeSampling](https://github.com/feifeibear/LLMSpeculativeSampling)  
40. Speculative Decoding: A Guide With Implementation Examples ..., acessado em agosto 28, 2025, [https://www.datacamp.com/tutorial/speculative-decoding](https://www.datacamp.com/tutorial/speculative-decoding)  
41. Speculative Decoding and Beyond: An In-Depth Review of Techniques \- arXiv, acessado em agosto 28, 2025, [https://arxiv.org/html/2502.19732v1](https://arxiv.org/html/2502.19732v1)  
42. Utility-Driven Speculative Decoding for Mixture-of-Experts \- ResearchGate, acessado em agosto 28, 2025, [https://www.researchgate.net/publication/393065833\_Utility-Driven\_Speculative\_Decoding\_for\_Mixture-of-Experts](https://www.researchgate.net/publication/393065833_Utility-Driven_Speculative_Decoding_for_Mixture-of-Experts)  
43. Tensor Parallel LLM Inferencing. As models increase in size, it becomes… | by Sneha Ghantasala | Thomson Reuters Labs | Medium, acessado em agosto 28, 2025, [https://medium.com/tr-labs-ml-engineering-blog/tensor-parallel-llm-inferencing-09138daf0ba7](https://medium.com/tr-labs-ml-engineering-blog/tensor-parallel-llm-inferencing-09138daf0ba7)  
44. 1 Introduction \- arXiv, acessado em agosto 28, 2025, [https://arxiv.org/html/2503.06433v1](https://arxiv.org/html/2503.06433v1)  
45. Inferência llm \- Dataconomy PT, acessado em agosto 28, 2025, [https://pt.dataconomy.com/2025/05/07/inferencia-llm/](https://pt.dataconomy.com/2025/05/07/inferencia-llm/)  
46. Inference-Time Compute Scaling Methods to Improve Reasoning Models, acessado em agosto 28, 2025, [https://sebastianraschka.com/blog/2025/state-of-llm-reasoning-and-inference-scaling.html](https://sebastianraschka.com/blog/2025/state-of-llm-reasoning-and-inference-scaling.html)  
47. Prompt Optimization in Large Language Models \- MDPI, acessado em agosto 28, 2025, [https://www.mdpi.com/2227-7390/12/6/929](https://www.mdpi.com/2227-7390/12/6/929)  
48. LLM performance benchmarks | LLM Inference Handbook \- BentoML, acessado em agosto 28, 2025, [https://bentoml.com/llm/inference-optimization/llm-performance-benchmarks](https://bentoml.com/llm/inference-optimization/llm-performance-benchmarks)  
49. New MLPerf Inference Benchmark Results Highlight The Rapid ..., acessado em agosto 28, 2025, [https://mlcommons.org/2024/03/mlperf-inference-v4/](https://mlcommons.org/2024/03/mlperf-inference-v4/)  
50. Benchmark MLPerf Inference: Datacenter | MLCommons V3.1, acessado em agosto 28, 2025, [https://mlcommons.org/benchmarks/inference-datacenter/](https://mlcommons.org/benchmarks/inference-datacenter/)  
51. Llama 2 70B: An MLPerf Inference Benchmark for Large Language Models \- MLCommons, acessado em agosto 28, 2025, [https://mlcommons.org/2024/03/mlperf-llama2-70b/](https://mlcommons.org/2024/03/mlperf-llama2-70b/)