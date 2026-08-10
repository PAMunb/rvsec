# Protocolo científico para validar as especificações `jca_android`

## Prompt mestre

Você atuará como orquestrador de uma auditoria formal, adversarial e reproduzível das 23 especificações JavaMOP do conjunto `jca_android`. O objetivo principal é determinar, para cada especificação e para o conjunto completo, se a tradução preserva a semântica das regras CrySL originais. Seu objetivo não é encontrar argumentos favoráveis à tradução: é tentar falsificar sua fidelidade.

A ausência de contraexemplos em testes finitos não constitui prova quando uma verificação algorítmica é possível. Consenso entre agentes não constitui prova. Um score alto não abre o portão de qualidade. A decisão `APROVADA` somente é permitida quando nenhuma diferença semanticamente relevante permanece sem classificação e todas as evidências mandatórias são reproduzíveis.

### 1. Escopo, oráculos e fontes obrigatórias

Inspecione diretamente, sem confiar apenas neste prompt:

- arquitetura e pipeline: `docs/architecture/rv-android.md`;
- change OpenSpec GH101 completa: `openspec/changes/gh101-jca-spec-conformance/`, incluindo `proposal.md`, `design.md`, os deltas em `specs/` e `tasks.md`;
- change GH100 e seus artefatos, localizando-os no repositório antes de citar qualquer correção;
- specs sob auditoria: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`;
- regras CrySL read-only: `$WS/MetaCrySL/generated/api30/` e, quando necessário para explicar a derivação, o projeto `$WS/MetaCrySL/`;
- skill baseline: `.claude/skills/rv-analyze-spec/SKILL.md` e seus `reference/` e `scripts/`;
- histórico: `$WS/ase-journal/dataset/results/errors.csv`;
- API efetiva: o `android.jar` da API 30 realmente usado;
- código e binários efetivos de JavaMOP, RV-Monitor, pointcut engine, AJC/dexlib2, `ExecutionContext`, `Property`, gerador, instrumentador e parser de logcat;
- registros e scripts produzidos por GH101: conformance record, predicate inventory, deliberate omissions, divergence record, freeze check, write/read guard e transition check. Localize-os; não presuma seus caminhos nem sua correção.

As regras CrySL são o oráculo normativo e não devem ser alteradas para fazer a tradução passar. A change GH101 é uma hipótese de implementação e um conjunto de requisitos verificáveis, não um segundo oráculo. Itens marcados `[x]` em `tasks.md` continuam sendo alegações até que sua evidência seja reproduzida. Itens `[ ]`, em particular a validação empírica dependente de GH100 e as verificações finais, são lacunas abertas até execução bem-sucedida.

Não implemente funcionalidades de produção. Trabalhe em modo read-only por padrão e só altere os arquivos explicitamente previstos/autorizados pela change ou pelo pesquisador: artefatos de auditoria, specs `.mop` e a skill `/rv-analyze-spec`. Testes, fixtures ou scripts novos exigem que já estejam previstos ou aprovação explícita. Não modifique CrySL nem o conjunto congelado `jca`. Antes de qualquer edição, entregue o diagnóstico e o patch proposto; não misture descoberta e reparo na mesma rodada de evidência.

### 2. Uso de Sequential Thinking sem expor raciocínio privado

Use o MCP Sequential Thinking no início, antes de cada spec, na resolução de divergências e antes do parecer global. Use-o para decompor hipóteses, dependências, ameaças à validade e próximos experimentos. Não publique chain-of-thought. Publique somente um log científico conciso contendo: questão, hipótese, teste discriminante, evidência, resultado, incerteza e próxima decisão.

Se o MCP não estiver disponível, registre a indisponibilidade e aplique explicitamente a mesma decomposição em etapas. A indisponibilidade da ferramenta não autoriza reduzir o rigor.

### 3. Princípios metodológicos não negociáveis

1. Congele primeiro, analise depois. Toda conclusão deve identificar a versão exata dos artefatos.
2. Separe `PROVADO`, `MEDIDO`, `OBSERVADO_EM_ARTEFATO`, `INFERIDO` e `NÃO_VERIFICADO`.
3. Toda alegação material deve ser triangulada por pelo menos dois ângulos que possam realmente discordar. Para propriedades da toolchain, um deles deve ser executável.
4. Prefira código de produção, harness sobre classes reais, artefato gerado e execução end-to-end a modelos/reimplementações.
5. Procure o menor contraexemplo, não somente testemunhas favoráveis.
6. Ausência de firing não significa aceitação: diferencie evento não alcançado, pointcut não casado, `condition(false)`, emissão perdida, monitor não chamado e trace aceito.
7. Use `INCONCLUSIVA` quando faltar evidência. Nunca converta desconhecido em sucesso ou segurança.
8. Não permita compensação: um defeito crítico em uma dimensão não pode ser cancelado por pontuação alta em outra.
9. Não atribua causalidade a GH100, GH101 ou a uma spec apenas por correlação no `errors.csv`.
10. Preserve distinções entre disponibilidade Android, recomendação criptográfica e fidelidade à regra. Uma queda no número de violações não demonstra melhoria.

### 4. Fase 0 — pré-registro e congelamento do corpus

Antes dos pareceres, crie um manifesto reproduzível:

- commits de `rv-android`, `rvsec`, MetaCrySL, JavaMOP e RV-Monitor;
- estado exato e relação de dependência de GH100 e GH101;
- SHA-256 de todas as `.mop`, `.cryptsl`, `android.jar`, jars da toolchain, `errors.csv` e scripts de auditoria;
- Java, Maven, Android API/SDK, memória, limites JVM, sistema e comandos;
- inventário programático das 23 `.mop` e pareamento com a regra CrySL;
- specs sem regra correspondente, regras sem spec correspondente e ambiguidades de nome;
- baseline dos registros GH101 e status real das tarefas abertas;
- diretório scratch por execução. Nunca rode JavaMOP sobre a árvore de specs, pois ele escreve `.rvm` ao lado da fonte.

Defina previamente:

- perguntas de pesquisa;
- unidade de análise: cláusula, evento, spec, trace, site instrumentado, APK e conjunto;
- critérios `PASS/FAIL/INCONCLUSIVE` de cada teste;
- severidade e impacto esperado em falso positivo, falso negativo, diagnóstico e reprodutibilidade;
- política de repetição, seeds e tratamento de flaky tests;
- conjunto de artefatos que constituirá o pacote de replicação.

Não altere critérios depois de observar resultados sem registrar a alteração como desvio do pré-registro.

### 5. Modelo semântico comum

Antes de comparar arquivos, defina formalmente o que significa equivalência neste estudo.

Considere traces finitos de chamadas observáveis contendo, quando aplicável: identidade do receptor, assinatura resolvida, argumentos, retorno, exceção, localização e ordem. Explicite:

- qual objeto parametriza e indexa cada monitor;
- identidade versus `equals`, aliasing, múltiplas instâncias, interleaving, reuso e descarte/GC;
- eventos `before`, `after`, `after returning` e `after throwing`;
- início, aceitação, violação e término de trace;
- efeitos e escopo de `REQUIRES`, `ENSURES`, `NEGATES` e `CONSTRAINTS`;
- diferença entre evento rejeitado, evento suprimido e evento não observado.

Construa uma função/relação de abstração `α` entre chamada Java real, evento CrySL e evento MOP. Para fusões, registre a relação muitos-para-um, o predicado discriminante (`instanceof`, retorno, aridade etc.), o agregado CrySL e o perfil de binding preservado.

Avalie separadamente:

1. equivalência da linguagem de `ORDER`;
2. equivalência de captura dos eventos;
3. equivalência de bindings e predicados;
4. equivalência das constraints;
5. equivalência paramétrica/ciclo de vida;
6. equivalência diagnóstica;
7. equivalência observacional no pipeline Android.

É proibido declarar equivalência global quando apenas o `ORDER` foi validado.

### 6. Matriz normativa cláusula a cláusula

Para cada spec, produza uma linha para cada `OBJECT`, evento, agregado, expressão de `ORDER`, `REQUIRES`, `ENSURES`, `NEGATES` e `CONSTRAINT`:

| Claim ID | seção/cláusula CrySL | argumentos/eventos | tradução MOP | artefato efetivo | status | evidência | impacto FP/FN | incerteza |
|---|---|---|---|---|---|---|---|---|

Estados permitidos:

- `FIDELIDADE_DEMONSTRADA`;
- `DIVERGÊNCIA_EQUIVALENTE_COMPROVADA`;
- `LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA`;
- `OMITIDA`;
- `INCORRETA`;
- `INCONCLUSIVA`.

Uma fusão sintática não é defeito por si só; um `_` CrySL é argumento anônimo. Entretanto, toda fusão deve preservar linguagem, agregado, binding profile, corpo, efeitos laterais e diagnóstico, ou demonstrar formalmente a discriminação que recupera essas diferenças. Uma limitação conhecida ou registrada por GH101 continua bloqueante para a alegação de aderência total, salvo decisão explícita do pesquisador que reduza formalmente o escopo do oráculo.

### 7. Perfil de binding e grafo de predicados

Crie o perfil completo por evento CrySL:

| evento CrySL | assinatura/agregado | argumento/posição/tipo | `_`? | cláusulas dependentes | binding no pointcut | disponível no body/handler | objeto da propriedade | escopo |
|---|---|---|---|---|---|---|---|---|

Verifique:

- argumentos requeridos não ligados ou ligados na posição/objeto errado;
- fusões incompatíveis entre aridades;
- primitivas versus referências e boxing/cache;
- retorno e `returning(...)`;
- indisponibilidade de `thisJoinPoint` no event body;
- `condition(...)` que torna cláusula inalcançável;
- `remove(Property)` global versus `remove(Property, object)` por instância;
- identidade do `ExecutionContext` contra a identidade usada pelo índice JavaMOP;
- writer/reader de toda `Property`, constantes erradas, writers sem reader, readers sem producer e edges que atravessam specs;
- propriedades sobre projeções: prove quando um argumento anônimo torna uma projeção fiel e registre resíduos;
- isolamento entre duas instâncias iguais por `equals`, mas distintas por identidade.

Reproduza e tente falsificar os invariantes GH101 sobre predicate inventory, deliberate omissions, write/read guard e identity store. Não aceite a simples presença desses arquivos.

### 8. Equivalência formal da propriedade

Para cada spec:

1. Normalize o `ORDER` CrySL em um autômato de referência independente.
2. Extraia o autômato efetivo do monitor gerado, e não apenas da sintaxe `.mop`.
3. Aplique `α` quando houver eventos fundidos ou divididos.
4. Verifique algoritmicamente as duas inclusões:
   - `L(CrySL) ⊆ α(L(MOP))`;
   - `α(L(MOP)) ⊆ L(CrySL)`.
5. Se alguma inclusão falhar, produza o menor trace separador e a caminhada estado a estado.
6. Verifique estado inicial, estados aceitantes, `fail`, transições ausentes, alternativas, repetição, `epsilon`, prefixos incompletos e fim de trace.
7. Detecte evento declarado com linha de transição toda `fail`, evento não colocado, evento duplicado e chamadas legítimas que mudam o estado indevidamente.
8. Quando útil, reescreva a linguagem em ERE/FSM/LTL. Não conte como evidência independente duas notações que reescrevem para o mesmo backend; use a segunda formalização para detectar erros de modelagem.

Faça revisão adversarial específica das decisões GH101 D-S9 a D-S14: reparo dos eventos all-`fail`, resíduo que pode deslocar a acusação para a chamada seguinte, remoção de `MessageDigest.reset`, orçamento de `Cipher`, transcrição de `!macced[_, plainText]`, edges deliberadamente abertos e constraints registradas como fora de escopo.

### 9. Captura real de eventos e orçamento

Para cada pointcut, obtenha do `android.jar` real:

- `Esperado`: membros modelados pela regra;
- `Capturado`: membros casados pelo matcher de produção;
- `Vizinhos`: membros semelhantes que não devem casar.

Exija:

- `Esperado ⊆ Capturado`;
- `Capturado ∩ Vizinhos = ∅`;
- interseção entre eventos MOP vazia, salvo sobreposição deliberada com prova semântica;
- nenhum membro esperado disparando zero ou mais de um evento;
- aridade, tipo de retorno, overloads, `Object+`, subtipo `T+`, primitivas, `..`, prefix glob e exceções corretos;
- concordância entre `PointcutBudget`, `.aj` gerado e comportamento do matcher/weaver real;
- comparação AJC versus dexlib2 quando ambos são caminhos do experimento.

Use o `PointcutBudget` da skill sobre classes de produção, não uma reimplementação. Inclua os pointcuts atuais e os candidatos na mesma matriz.

Conte os eventos e verifique o custo com o backend real. Para specs com `@fail`, registre `n × (2^n − 1)`, resultado do `CoenableProbe`, tempo e RSS da geração completa. O teto prático vigente é 17 eventos; qualquer spec acima dele falha. Reproduza a restrição e não copie os números de GH101 sem medição. Dê atenção especial às specs mais próximas do teto, mas não pule as menores.

### 10. Triangulação dos artefatos gerados e do weaving

Valide a cadeia completa:

```text
.mop → .rvm + MonitorAspect.aj/descriptor → RuntimeMonitor.java
     → advice/monitorCall → DEX tecido → execução → RVSEC/RVSEC-COV
     → parser/serialização → errors.csv
```

Em cada etapa, verifique cardinalidade, ordem, argumentos, binding, `before/after/returning`, localização e tratamento de erro. Em particular:

- `condition(false)` gera supressão silenciosa, não transição;
- `(..)` inclui aridade zero;
- múltiplos pointcuts podem causar double-fire;
- múltiplos `monitorCall` de um advice devem ser preservados, na ordem correta;
- nenhum parse/pointcut desconhecido pode ser aceito em modo fail-open;
- wrappers não podem colidir nem perder corpo/variável;
- transições implícitas para `fail` devem coincidir com o modelo;
- `__LOC` deve sobreviver e ser passado explicitamente a helpers;
- o DEX final deve conter cada invoke esperado, confirmado por inspeção independente do emissor;
- pressão de registradores, retorno descartado, exceção e chamadas inlined não podem suprimir evento;
- APK deve instalar, abrir e executar os sites instrumentados;
- reconstrução/resume a partir de logcat deve preservar cobertura e violações.

Use GH100 como conjunto de hipóteses de falha do weaver e GH101 como conjunto de hipóteses de correção das specs/predicados. Execute uma matriz versionada `{antes,depois GH100} × {antes,depois GH101}` quando os commits forem materialmente reproduzíveis. Mantenha as entradas, APK, seed, driver, orçamento e ambiente constantes. Se algum braço não puder ser construído, classifique-o como `INCONCLUSIVO` e explique.

### 11. Testes derivados, diferenciais e de mutação

Gere sistematicamente por spec:

- testemunha positiva mínima para cada alternativa/caminho e estado aceitante;
- negativo mínimo para cada transição proibida e constraint;
- zero/uma/múltiplas repetições e prefixos incompletos;
- todos os overloads relevantes, valores-limite e `null` quando válido;
- eventos conformes e violadores derivados da mesma chamada CrySL;
- `condition(true/false)` e garantia de que erro específico não vem acompanhado de `@fail` espúrio;
- duas instâncias intercaladas, aliasing, reuso e objetos iguais/distintos;
- producer/consumer na ordem certa/errada, objeto certo/errado, propriedade presente/ausente e `NEGATES`;
- retorno normal e exceção;
- replay no oráculo formal e no monitor MOP, comparando decisão, categoria e primeiro ponto de violação;
- execução instrumentada AJC e dexlib2, comparando multiplicidade/ordem de `RVSEC-COV` e `RVSEC`.

Faça mutation testing da spec e da tradução: remova/inverta transição, amplie/restrinja pointcut, remova binding, troque overload/tipo/retorno, inverta constraint, altere propriedade/objeto/escopo, force `condition(false)`, duplique evento e troque alias. Todo mutante semanticamente não equivalente deve ser morto. Mutante sobrevivente torna a adequação da suite `INCONCLUSIVA`; mutation score não substitui prova de equivalência.

Para cada requisito CrySL, construa pelo menos um par de traces distinguíveis que difira somente naquele requisito, quando isso for expressível. Se nenhum teste puder observar a diferença, registre uma ameaça de observabilidade.

### 12. Diagnóstico e histórico experimental

Audite todos os handlers `@fail`, `@match` e caminhos específicos. Uma mensagem suficiente deve permitir atribuir a ocorrência sem expor material criptográfico sensível:

- categoria específica e ID da regra/cláusula;
- spec e hash/versão;
- evento observado e conjunto/operação esperada;
- estado anterior/novo ou prefixo mínimo;
- `__LOC`;
- identidade pseudonimizada do monitor/objeto e bindings relevantes;
- esperado/observado apenas quando seguro;
- chave estável de deduplicação.

Gate diagnóstico: nenhum `unknown`; toda violação reproduzível e atribuível a cláusula, evento, estado e localização; nenhum erro específico acompanhado de sequência inválida espúria.

Ao analisar `errors.csv`:

- congele hash e schema e valide registros malformados/nulos;
- relate separadamente linhas, `unique_msg`, APKs e sites; não misture unidades;
- controle pseudorreplicação por tool, repetição e timeout;
- estratifique por spec, categoria, APK, classe, método e configuração;
- trate o histórico como gerador de hipóteses, pois é anterior às mudanças e pode conter perdas de emissão;
- não atribua uma linha a um dos eventos all-`fail` sem replay/site/evento que sustente a causalidade;
- use replay pareado para classificar deltas como correção, FP, FN, instrumentação, serialização ou inconclusivo;
- não use redução bruta de erros como evidência de correção.

### 13. Sinergia com a análise estática

Construa uma tabela por cláusula:

| regra/cláusula | fato estático possível | binding/predicate | evento/estado dinâmico | diagnóstico | terceiro estado/limitação |
|---|---|---|---|---|---|

Verifique que as duas análises compartilham a mesma identidade de regra/cláusula, interpretação de `_`, agregados e semântica de `REQUIRES/ENSURES/NEGATES`. Um trace aceito pelo oráculo CrySL não pode ser rejeitado pelo MOP. Um contraexemplo estático deve possuir uma testemunha dinâmica possível se o caminho executar. `unknown`, não alcançado e não observável são terceiros estados, nunca “seguro”.

O desbloqueio da análise estática exige 100% das cláusulas mapeadas ou limitações formalmente delimitadas e aceitas pelo pesquisador, sem contradições abertas. Registre que a seleção nominal `jca_android` realmente resolve para o diretório correto e não cai silenciosamente em `jca`/`custom`.

### 14. Organização multiagente adversarial

Use pelo menos três subagentes em contextos independentes. Eles não devem ler os pareceres uns dos outros antes de entregar a primeira rodada. Todos recebem o manifesto congelado e preenchem o mesmo esquema de claims.

#### Agente Alfa — conformidade CrySL e lógica formal

- matriz normativa completa;
- função `α` e binding profile;
- duas inclusões de linguagem e contraexemplos mínimos;
- constraints e grafo `REQUIRES/ENSURES/NEGATES`;
- busca ativa de falsos positivos e negativos sem depender do pipeline.

#### Agente Beta — red team da toolchain e Android

- orçamento/coenables;
- matcher contra API real, cobertura/disjunção/leakage;
- `.rvm`, `.aj`, descriptor e RuntimeMonitor;
- cardinalidade/ordem de advice e `monitorCall`;
- inspeção independente do DEX e execução AJC/dexlib2;
- hipóteses GH100/GH101, suppressions, fail-open e observabilidade ponta a ponta.

#### Agente Gama — diagnóstico, experimento e análise estática

- handlers e suficiência das mensagens;
- análise estatística correta de `errors.csv`;
- replay pareado e atribuição causal;
- sinergia estático/dinâmico;
- proveniência, validade interna/externa e ameaças.

Cada claim deve conter: ID, spec/cláusula, posição (`PASS/FAIL/INCONCLUSIVE`), tipo da alegação, evidência primária com comando/arquivo:linha/hash, resultado, contraevidência, ameaça à validade, impacto FP/FN, severidade e confiança calibrada.

### 15. LLM-as-a-Judge e rodada de refutação

O juiz recebe os relatórios anonimizados e os artefatos primários. Ele sintetiza evidência; não funciona como oráculo formal e não decide por maioria.

Produza a matriz:

| Claim ID | Alfa | Beta | Gama | evidência conflitante | teste discriminante | resolução | incerteza residual |
|---|---|---|---|---|---|---|---|

Regras do juiz:

- um contraexemplo reproduzível não pode ser descartado por consenso;
- alegação baseada apenas em leitura/modelo não fecha claim de toolchain;
- quando os agentes medem coisas diferentes, formule e execute teste discriminante;
- prioridade típica: execução/harness real → artefato gerado → código/API → tradução manual → opinião; ajuste somente com justificativa;
- `INCONCLUSIVE` nunca vira aprovação;
- divergência deve ser classificada como equivalente comprovada, limitação inevitável documentada, defeito ou inconclusiva;
- score é apenas descritivo, nunca arredondado para 100 e nunca abre o gate.

Calcule também a pontuação de aderência solicitada, de 0 a 100%, com subpontuações separadas para linguagem formal, captura, bindings/cláusulas, predicados/composição, toolchain Android, diagnóstico e reprodutibilidade. Publique pesos e denominadores antes de pontuar; itens `INCONCLUSIVE` permanecem fora do denominador e impedem chamar o score de completo. Não use média entre agentes: pontue claims resolvidos pelo juiz. Rotule claramente: `score descritivo ≠ probabilidade de correção ≠ veredito`. Apenas 100% com todos os gates satisfeitos pode acompanhar `READY`; obter 100% aritmeticamente não força `READY`.

Depois da síntese, faça uma segunda rodada com um revisor adversarial independente cuja única tarefa seja refutar o parecer do juiz, procurando claims sem evidência, contradições entre matriz e anexos, counterexamples ignorados e ameaças à validade. O juiz só emite decisão final após responder a cada objeção.

### 16. Gates obrigatórios

Avalie pelo menos:

- `G0 Proveniência`: corpus/versionamento/hashes completos;
- `G1 Inventário`: 23/23 specs e pareamento CrySL sem lacunas;
- `G2 Gerabilidade`: ≤17 eventos, geração limpa, tempo/RSS, sem erro/warning relevante;
- `G3 Linguagem`: duas inclusões demonstradas ou contraexemplo classificado;
- `G4 Cláusulas/bindings`: 100% rastreados e observáveis no objeto correto;
- `G5 Pointcuts`: cobertura completa, leakage zero e double-fire zero não justificado;
- `G6 Artefatos/weaving`: cardinalidade, ordem, bindings e DEX confirmados ponta a ponta;
- `G7 Predicados/composição`: store, writer/reader/negates/remove e interobjetos corretos;
- `G8 Testes`: corpus discriminante sem FP/FN e mutantes relevantes mortos;
- `G9 Diagnóstico`: nenhuma mensagem `unknown`, atribuição e deduplicação suficientes;
- `G10 Android`: equivalência observacional AJC/dexlib2/logcat/resume no escopo testado;
- `G11 GH100/GH101`: requisitos reproduzidos; tarefas abertas não ocultadas; confundimento delimitado;
- `G12 Estática`: mapeamento completo e nenhuma contradição estático/dinâmico;
- `G13 Revisão`: nenhum achado crítico/major aberto após refutação independente.

Veredito por spec: `APROVADA`, `REPROVADA` ou `INCONCLUSIVA`.

`READY` para o conjunto é uma conjunção, não uma média: todas as 23 specs `APROVADA`, todos os gates `PASS`, nenhuma cláusula `OMITIDA`, `INCORRETA` ou `INCONCLUSIVA`, nenhum contraexemplo aberto e evidência reproduzível. Uma divergência conscientemente aceita pelo pesquisador exige alteração explícita do escopo científico; não pode ser silenciosamente chamada de 100% aderente. Se uma única spec não passar, o conjunto não desbloqueia a análise estática.

### 17. Entregáveis

Crie uma árvore versionada de auditoria com:

1. manifesto e pré-registro;
2. relatório individual das 23 specs;
3. matrizes CrySL→MOP e binding profiles;
4. `α`, autômatos, resultados das inclusões e contraexemplos;
5. matrizes de pointcuts/API;
6. `.rvm`, `.aj`, descriptor e RuntimeMonitor usados, ou hashes/paths imutáveis;
7. inspeção DEX e traces `RVSEC/RVSEC-COV`;
8. suites, fixtures, resultados e mutation report;
9. análise histórica com unidades estatísticas explícitas;
10. matriz de conflitos e parecer do juiz;
11. rodada de refutação e respostas;
12. matriz final de gates;
13. relatório global com riscos e ameaças à validade;
14. pacote de replicação com comandos exatos.

O relatório deve distinguir fatos medidos de inferências, citar `arquivo:linha`, registrar comandos e outputs e permitir reprodução por outro pesquisador.

### 18. Evolução controlada da `/rv-analyze-spec`

Não edite a skill durante a primeira auditoria. Registre cada nova dimensão candidata com caso mínimo, generalidade, evidência, risco e anti-padrão. Valide-a em pelo menos duas specs, salvo fenômeno justificadamente singular. Depois proponha patch separado, revisão independente e regressão das regras existentes.

Inclua no mínimo:

- **Dimensão 6 — Diagnóstico e mensagens de erro**: perguntas, campos mínimos, privacidade, `__LOC`, estado/evento, deduplicação e gates;
- **Dimensão 7 — Sinergia com análise estática e invariantes**: mapeamento de cláusulas, terceiro estado e gate de desbloqueio;
- **Dimensão 8 — Fidelidade ponta a ponta do weaving/emissão**;
- **Dimensão 9 — Semântica paramétrica e ciclo de vida do monitor**;
- **Dimensão 10 — Verificação diferencial e mutation testing**;
- **Dimensão 11 — Proveniência e reprodutibilidade**;
- **Dimensão 12 — Composição entre specs e grafo de predicados**;
- **Dimensão 13 — Exceções, supressões e eventos incompletos**;
- **Dimensão 14 — Validade Android/API-level e equivalência AJC/dexlib2**;
- **Dimensão 15 — Grau de certeza e dívida de verificação**.

Cada dimensão deve especificar entradas, procedimento, evidência esperada, `PASS/FAIL/INCONCLUSIVE`, ameaças e exemplos regressivos. Separe regras normativas de medições empíricas versionadas. Atualize changelog/versão e nunca incorpore uma “lição” baseada apenas em opinião do juiz.

### 19. Ordem de execução

1. Leia todas as fontes e congele o corpus.
2. Faça o pré-registro e defina a semântica comum.
3. Execute um piloto em uma spec complexa e uma simples para validar o protocolo, sem mudar os gates.
4. Audite as 23 specs, uma por vez, com três pareceres independentes.
5. Execute verificações do conjunto: composição de predicados, geração `-merge`, descriptor, weaving, Android e análise histórica.
6. Faça julgamento, teste discriminante dos conflitos e rodada de refutação.
7. Emita vereditos individuais e global.
8. Somente depois proponha correções e evolução da skill em patches separados.

Comece agora pelo Sequential Thinking e pela Fase 0. Não emita parecer de aderência antes de produzir o manifesto, a definição de equivalência e os critérios pré-registrados.
