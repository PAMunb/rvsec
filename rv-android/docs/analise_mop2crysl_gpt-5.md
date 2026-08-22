# Revisão externa do componente de conformidade MOP↔CrySL

## 1. Veredito

**Prosseguir somente com emendas estruturais e em duas etapas.** O comparador é um instrumento útil, mas o plano ainda não sustenta os números globais de geração nem uma alegação de “conformidade” da regra inteira: M2 mede linguagem de ordem, não `IncompleteOperationError`, e eventos AspectJ sobrepostos tornam falso o pressuposto de um símbolo por chamada (`docs/20260821_conformidade_mop_crysl.md:895-900`; `docs/20260821_auditoria_conformidade_mop_crysl.md:112-186`). O primeiro produto deve ser um comparador vertical, versionado e conservador; `crysl2mop` deve ser um segundo marco, aprovado apenas depois de um piloto reproduzível. A arquitetura comum pode permanecer, mas não os dois compromissos de produto no mesmo MVP (`docs/20260821_conformidade_mop_crysl.md:52-56,1089-1094`).

## 2. Método

Revisão iniciada no `HEAD 0290caf56d6f9a75149b374a5b9e000182aed2cc` e aprofundada no `HEAD e9bfb0d70e706566145ff8479ee0fc3eb0f61bb1` (transcrições: `git rev-parse HEAD`). A mudança durante a revisão é evidência direta de que o snapshot se move; as recontagens finais abaixo pertencem a `e9bfb0d7`. Três subagentes rederivaram independentemente D1–D2, D3–D5 e D4–D6–D8; a síntese e D7 foram feitas pelo revisor principal. Foram lidos o plano, validações, auditoria, gramáticas, corpora, CSVs, código dos substratos e arnês. Foram repetidos os censos centrais, 214 parses, o leitor CrySL isolado, o pipeline Cipher, um exemplo terminal e uma mutação de handler. Não houve implementação nem alteração de artefato sob revisão; todos os produtos de execução ficaram sob `/tmp`. O servidor `sequential-thinking` **não estava disponível**: a enumeração das ferramentas retornou `[]` para `/sequential|thinking/i`; portanto D7 e a síntese usaram análise explícita convencional.

## 3. Achados por dimensão

### D1 — factual e numérica

- **CONFIRMED — HIGH:** a tabela de geração não é evidência de corpus. Ela anuncia `152/167`, `22/22`, `7/22`, `11/22`, `16/55`, `47/55`, `87/92`, `67,6%`, `9%` (`docs/20260821_conformidade_mop_crysl.md:742-749`), mas o próprio texto limita execução a três regras (`:750-766`). Além disso, `92-87=5`, não quatro lacunas; `16+47>55`; e 67,6%+9% deixa 23,4% sem categoria. Até existir arnês integral, esses valores são **UNVERIFIED estimates**.
- **CONFIRMED — HIGH:** a decomposição M4 correta no próprio plano é `26+28+19+19=92` (`docs/20260821_conformidade_mop_crysl.md:404-413`); a formulação recomendada apaga os 28 de fiação (`:471-473`).
- **CONFIRMED — HIGH:** `Property` tem 26 constantes, não 24: enumeração em `../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java:7-68`. Apenas quatro blocos de Javadoc estão visíveis (`:3-6,11-23,25-36,56-68`), refutando “cada constante”.
- **CONFIRMED — HIGH, REEXECUTED:** contagem direta das cláusulas terminadas em `;`, por seção e por regra, deu M3 `all=62`, `paired=55` e M4 `all=92`, `paired=73`, com `REQUIRES=36`, `ENSURES=54`, `NEGATES=2`. Transcript: `/tmp/d1d2_recount.out`; SHA-256 do transcript `2e3a22113d719c44da77588b65f256bd1748a3e68fc5745345df4623d0488257`. A matriz M3 impressa fecha em 55 (11+3+4+7+30) (`docs/20260821_conformidade_mop_crysl.md:316-347`).
- **CONFIRMED — HIGH:** o “teto do oráculo” documentado como três regras/nove cláusulas (`docs/20260821_conformidade_mop_crysl.md:321-335`) é apenas um subconjunto. A auditoria rederivou 95→62 cláusulas e 16 regras afetadas (`docs/20260821_auditoria_conformidade_mop_crysl.md:305-320`); o plano não publica o inventário completo, portanto a contagem ampla fica **UNVERIFIED nesta revisão**, embora a crítica ao subdimensionamento seja confirmada.
- **REFUTED — HIGH, REEXECUTED:** `generic=93/118` (`docs/20260821_conformidade_mop_crysl.md:1162-1168`) está errado. Recontagem dos cabeçalhos deu 118 specs, buckets `{1:21,2:40,3:30,4:17,5:6,6:4}` e **97 multiparâmetro**. Transcript e hash: `/tmp/d1d2_recount.out`, acima. A recontagem coincide com `docs/20260821_auditoria_conformidade_mop_crysl.md:235-241`.

### D2 — coerência interna

- **CONFIRMED — HIGH, REEXECUTED:** “um `CrySLModelReader` por regra” (`docs/20260821_conformidade_mop_crysl.md:1105-1107`) é incompatível com “31 regras que carregam” (`:310-314`). Com cinco normalizações e reader novo dentro do loop, o resultado foi **30/33**; falharam `AlgorithmParameters`, `DigestOutputStream` e `Signature`. Transcript `/tmp/isolated_read.out`, SHA-256 `1303d1fd775a7f1a65e1c06d2a2974b1d570d8facbbd336a19f0c19516204b65`. Probe separado confirmou `Signature`: fresh FAIL → após GCM no mesmo reader OK → fresh FAIL; o arnês V6 reutiliza reader em `docs/handoff/20260821_arnes_validacoes/v6/LiftCrysl.java:19,28-37`.
- **CONFIRMED — HIGH:** §12 especifica quatro substituições (`docs/20260821_conformidade_mop_crysl.md:1099-1103`) enquanto a correção validada exige cinco (`docs/20260821_auditoria_conformidade_mop_crysl.md:101-110`).
- **CONFIRMED — HIGH, REEXECUTED:** a testemunha `g1 i1 f1` é contradita pelo pipeline real. Em `/tmp/mop-review-cipher.JJd9ag`, JavaMOP→RV-Monitor→ajc→JSE produziu `[EV] g1`, `[EV] i2`, `[EV] f1`, `[FAIL]`, `[EV] f2`, `[FAIL]`; o controle `g1,i2,u1,f2` produziu `[MATCH]`. Isso reproduz `docs/20260821_auditoria_conformidade_mop_crysl.md:112-172`.
- **REFUTED — HIGH, NOVO:** a testemunha substituta `g1 i1 wkb1 f2` proposta pela auditoria (`docs/20260821_auditoria_conformidade_mop_crysl.md:176-181`) não é concretamente realizável na JCA. `/tmp/WrapFinalProbe.java` executou os dois modos: em `ENCRYPT_MODE`, `wrap` lançou `IllegalStateException: Cipher not initialized for wrapping keys`; em `WRAP_MODE`, `wrap` passou e `doFinal` lançou `IllegalStateException: Cipher not initialized for encryption/decryption`. Logo **INCOMPARÁVEL está demonstrado apenas para as linguagens abstratas**, não para traços JCA concretos. O lado regra\MOP continua sustentado pela reinicialização; o lado MOP\regra precisa de outra testemunha realizável ou deve ser rebaixado a UNVERIFIED operacionalmente.
- **CONFIRMED — MEDIUM:** V10 diz construção experimental restaurada, mas o plano fala como se os módulos ainda estivessem no reator (`docs/20260821_conformidade_mop_crysl.md:1055-1063`; `docs/20260821_auditoria_conformidade_mop_crysl.md:278-284`).

### D3 — arquitetura

- **CONFIRMED — HIGH:** um DFA sobre rótulos não basta. Uma chamada pode produzir uma sequência ordenada de eventos (`f1;f2`), logo M2 precisa de uma camada explícita **join point → palavra de eventos**, incluindo guardas e ordem de advice; o modelo atual contém apenas `Map<Label,Set<Signature>>` (`docs/20260821_conformidade_mop_crysl.md:1124-1136`) e já falhou nesse caso (`docs/20260821_auditoria_conformidade_mop_crysl.md:118-172`).
- **CONFIRMED — HIGH:** testemunha abstrata e traço realizável são objetos distintos. Além do co-disparo, o estado da API restringe sequências: `wrap;doFinal` aparece no FSM como caminho aceito (`../rvsec/rvsec-mop/src/main/resources/jca_android/CipherSpec.mop:259-289`) mas é proibido em qualquer modo legal do `Cipher` pelo probe `/tmp/WrapFinalProbe.java`. O comparador deve rotular testemunhas como `ABSTRACT` até concretização/execução; “falso positivo/negativo real” exige trace realizável.
- **CONFIRMED — MEDIUM:** JSON entre processos é justificável como isolamento e evidência (`docs/20260821_conformidade_mop_crysl.md:1113-1122`), mas três módulos mais processos separados excedem P1 se o primeiro marco for só comparação. Começar por dois extratores CLI + esquema JSON versionado + comparador puro; só adicionar `lower` depois do piloto. P1 exige complexidade mínima (`CLAUDE.md:111-114`).
- **CONFIRMED — MEDIUM:** serializar apenas DFA mínimo perde a relação com agregados, rótulos originais e pontos `after`. O plano reconhece que a fachada perde agregados (`docs/20260821_conformidade_mop_crysl.md:789-799`) e pede procedência por item (`:1124-1136`); o JSON deve preservar NFA/AST ou mapa de origem além do DFA.
- **REFUTED — MEDIUM:** “conflito Guava implica processos” é forte demais. O conflito existe (`docs/20260821_conformidade_mop_crysl.md:1113-1117`), mas processos são uma escolha, não consequência lógica; shading ou classloaders isolados continuam alternativas. O isolamento por processo ganha por simplicidade operacional somente se o esquema for pequeno e estável.
- **REFUTED — MEDIUM, REEXECUTED:** minha primeira leitura de que Guava 33.5 contaminaria hoje o filho MOP estava errada. O `effective-pom` herda a propriedade, mas o classpath resolvido do filho equivalente tem 28 jars e não contém Guava nem Soot; `SpecExtractor.parse` passou 214/214 nesse classpath. A afirmação de V10 de Guava “nos dois filhos” (`docs/20260821_conformidade_mop_crysl.md:1055-1061`) confunde `dependencyManagement` com dependência resolvida. O pin no pai é risco futuro/complexidade desnecessária, não falha atual.
- **CONFIRMED — HIGH:** `Set<Constraint>` e `Set<PredicateRef>` podem colapsar cláusulas repetidas e suas proveniências (`docs/20260821_conformidade_mop_crysl.md:1127-1136`). Usar lista/multiset com ID estável; só deduplicar numa visão derivada.
- **CONFIRMED — HIGH:** o gate descrito compara apenas ORDER (`docs/20260821_conformidade_mop_crysl.md:1182-1186`), portanto não pode detectar por si só `@match` sem `@fail`, embora o texto alegue isso (`:1188-1191`). O gate deve recomputar M1–M4, invariantes de handlers e um smoke observacional.

### D4 — validade metodológica

- **CONFIRMED — HIGH:** a unidade principal deve ser um quarteto versionado `(R_java,R_android,S_java,S_android)`, nunca um par implícito. O próprio plano define divergência vertical/horizontal (`docs/20260821_conformidade_mop_crysl.md:65-85`), mas compara allow-lists com oráculos diferentes sem rotular o eixo; a auditoria localiza `9/11` versus `7/11` (`docs/20260821_auditoria_conformidade_mop_crysl.md:339`).
- **CONFIRMED — HIGH:** M2 é necessário, mas insuficiente para “conformidade”. O resultado deve chamar-se `ORDER-conformance`; conformidade global só pode ser `PASS` se M1–M4, handlers e obrigações de término estiverem cobertos, caso contrário `UNKNOWN/OUT_OF_SCOPE`. O próprio plano mostra que `@match` sem `@fail` pode nunca acusar (`docs/20260821_conformidade_mop_crysl.md:1188-1191`).
- **CONFIRMED — HIGH, REEXECUTED:** dois monitores sintéticos tinham eventos, ERE `a+`, constraints, predicates e tabelas M2-eff idênticos; a única diferença era o corpo de `@fail`. Para o mesmo traço `append; reverse`, o primeiro imprimiu `DETECTED_BY_LOUD`, o segundo apenas `PROGRAM_DONE`. Ambos passaram JavaMOP→RV-Monitor→ajc. Assim M1–M4 certificam como iguais monitores de eficácia oposta. É necessário um M5 observacional `trace → diagnósticos + efeitos no PredicateStore`, ou o nome deve ser “conformidade estrutural”. Artefatos: `/tmp/mop-review-handler`; separação entre fórmula e handlers na AST: `../javamop/src/main/java/javamop/parser/ast/mopspec/PropertyAndHandlers.java:30-49`.
- **CONFIRMED — HIGH:** falta testar a **comutatividade do quadrado**. Duas comparações verticais não demonstram que a mudança `S_java→S_android` corresponde intencionalmente à mudança `R_java→R_android`; o diagrama e os dois eixos estão em `docs/20260821_conformidade_mop_crysl.md:65-85`. Acrescentar delta horizontal pareado com proveniência/rationale.
- **CONFIRMED — HIGH:** `Unknown` é correto, mas precisa estar no denominador. Separar `SUPPORTED_PASS`, `SUPPORTED_FAIL`, `UNKNOWN_TOOL`, `UNOBSERVABLE_RUNTIME`, `ORACLE_DEFECT` e `OUT_OF_SCOPE`; nunca remover recusas do denominador. A motivação já aparece em `docs/20260821_conformidade_mop_crysl.md:449-465,1139-1144`.
- **CONFIRMED — HIGH:** M2-eff assume correção do gerador e estabilidade do layout Java. O próprio plano exige fallback porque aceitação nem sempre está materializada (`docs/20260821_conformidade_mop_crysl.md:231-243,1103-1105`); `RVM_eventNames` nem sempre existe (`docs/20260821_auditoria_conformidade_mop_crysl.md:344`). Trate M2-eff como teste diferencial contra M2-decl, não como fonte privilegiada silenciosa.
- **REFUTED — HIGH:** N1 não é lei geral demonstrada. O plano a generaliza para “qualquer spec paramétrica” (`docs/20260821_conformidade_mop_crysl.md:269-282`), mas V8 é uma sonda e apenas KeyGenerator muda entre cinco casos (`:245-263`). N1 deve ser hipótese de semântica de fatia, habilitada por formalismo e validada contra corpus.

### D5 — viabilidade e risco

- **CONFIRMED — HIGH:** parsing não é validação: o handoff registra id duplicado e símbolo inexistente que atravessam parser, gerador e compilador (`docs/handoff/20260821_prompt_revisao_externa_conformidade.md:372-376`). Apesar disso, o contrato de viabilidade do parser foi **REEXECUTED**: os cinco diretórios somaram 214 specs e deram `TOTAL=214 OK=214 FAIL=0`; transcript terminal `/tmp/mop-review-parse214.sdO8ib`. O saneamento AST (ids únicos; alfabeto usado ⊆ declarado; eventos observáveis) é gate separado e anterior a qualquer métrica.
- **CONFIRMED — HIGH:** o passo menos validado é geração integral, não dependências: apenas três specs passaram ponta a ponta (`docs/20260821_conformidade_mop_crysl.md:750-766,1211-1215`). Um piloto estratificado deve incluir ERE/FSM, agregados, guardas, co-disparo, predicados N-ários e regra com erro de oráculo.
- **CONFIRMED — MEDIUM:** `ExecutionContext` é de fato unário (`Map<Property,Set<Object>>`, `setProperty`, `validate`) (`../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java:17-21,80-97`). A aridade N não é limite arquitetural: `PredicateStore` já armazena tuplas e leituras trivaloradas (`../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java:24-35,67-79,231-253`). Logo o substrato é parâmetro de alvo, não limite do componente.
- **CONFIRMED — HIGH, REEXECUTED:** V6 não exercita a decisão “reader por regra”: instancia um reader antes do loop e o reutiliza (`docs/handoff/20260821_arnes_validacoes/v6/LiftCrysl.java:19,28-37`). A execução isolada deu 30/33 e o probe fresh/reused/fresh reproduziu o vazamento; logo V6 não valida a arquitetura proposta.
- **CONFIRMED — MEDIUM:** os três módulos não incluem um orquestrador dos processos (`docs/20260821_conformidade_mop_crysl.md:1080-1093`). É preciso especificar CLI, códigos de saída, arquivos temporários e falha parcial; esses comportamentos não “caem” da decomposição Maven.

### D6 — contribuição científica

- **CONFIRMED — HIGH:** “há um tradutor” não basta; o plano o admite (`docs/20260821_conformidade_mop_crysl.md:909-925`). A contribuição defensável é: uma taxonomia operacional de perdas entre especificação estática e monitorável, com corpus pareado, testemunhas mínimas e recusas explícitas.
- **CONFIRMED — HIGH:** o baseline deve incluir (a) tradução humana publicada, (b) scripts/gates existentes e (c) geração direta. Sem precisão/recall por classe de cláusula, custo humano e validação por traços, a “mapa do que não traduz” parece inventário local, não resultado generalizável.
- **CONFIRMED — HIGH:** critérios de morte: números não reproduzíveis de §10; oráculo Android defeituoso; ausência de hold-out; e avaliação somente nas mesmas regras que inspiraram políticas. A alegada citação do TSE não aparece no cofre verificado (`docs/20260821_auditoria_conformidade_mop_crysl.md:286-303`) e deve virar paráfrase com fonte correta.

### D7 — alternativas

1. **Recomendação: comparador vertical + compilador opcional.** Dois front-ends produzem um IR semântico versionado; um checker calcula inclusão nas duas direções e testemunhas; um back-end MOP é fase posterior. Custo: manter esquema e dois extratores. Ganho: não mistura validação científica com produto gerador e mantém reutilização real (`docs/20260821_conformidade_mop_crysl.md:1089-1094`).
2. **Conformidade por construção (`R_android→S_android`).** Gerar MOP no build e manter somente exceções tipadas. É elegante para o corpus Android, mas não elimina o comparador: o compilador e o oráculo podem errar, e divergências deliberadas/humanas precisam de differential checking. Migração: três regras piloto, depois estratos, depois corpus.
3. **Testes diferenciais/property-based.** Gerar palavras curtas e chamadas concretas para comparar CrySL, MOP declarado e monitor gerado. Custo: concretização JCA e explosão de estados. Ganho: detecta co-disparo, guards e bugs do gerador que equivalência abstrata perde. Deve complementar, não substituir, inclusão de linguagens.
4. **Refinement checking.** Modelar `S⊆R` e `R⊆S` separadamente em biblioteca de autômatos; é exatamente a lattice “mais estrita/mais permissiva/incomparável”, com testemunhas. Bisimulação é forte e dependente de estrutura; equivalência de linguagem é a relação observacional correta para ORDER. Simulation pode ser otimização/prova suficiente, não o veredito sem completude.
5. **SMT/teorema.** Útil apenas para M3/M4 com aritmética e predicados; caro e desnecessário para regex finita. Não recomendado no MVP.
6. **Inferir CrySL de traços.** Mede comportamento observado, não obrigação normativa; não responde conformidade e sofre incompletude de cobertura. Serve como gerador de contraexemplos, não como arquitetura central.

### D8 — adversarial

- **CONFIRMED — HIGH, REEXECUTED:** contraexemplo real: dois eventos no mesmo join point (`doFinal()`→`f1;f2`) tornam errada uma testemunha aceita pelo modelo atual. Pipeline e saída estão registrados em `/tmp/mop-review-cipher.JJd9ag`; a evidência anterior está em `docs/20260821_auditoria_conformidade_mop_crysl.md:118-172`.
- **CONFIRMED — HIGH:** contraexemplo sintético mínimo para o parser: declarar `c1` duas vezes e usar `c2` no ERE produz sucesso espúrio; a ocorrência real é `GCMParameterSpecSpec.mop`, descrita no handoff (`docs/handoff/20260821_prompt_revisao_externa_conformidade.md:372-376`).
- **CONFIRMED — HIGH, REEXECUTED:** uma spec com ordem aceita mas handler silencioso recebe M1–M4 idênticos e não acusa; o par Loud/Silent em `/tmp/mop-review-handler` demonstrou isso ponta a ponta. Os propagadores atuais com `@match` sem `@fail` também estão documentados (`docs/20260821_conformidade_mop_crysl.md:239-243,1188-1191`).
- **CONFIRMED — MEDIUM:** amanhã, uma spec multi-parâmetro cujo ORDER intercala dois objetos será recusada (`docs/20260821_conformidade_mop_crysl.md:1155-1180`). A recusa é correta para CrySL clássico, mas invalida alegação de tradutor JavaMOP geral; o escopo deve dizer “JCA mono-slice”.

## 4. Revisão da auditoria existente

Concordo com A1–A14 em substância, com duas exceções materiais. A4 refuta corretamente a testemunha original, mas sua substituta é **REFUTED como traço concreto**: `wrap` e `doFinal` exigem modos mutuamente incompatíveis no mesmo `Cipher` (transcript `/tmp/WrapFinalProbe.java`). A auditoria preserva incomparabilidade abstrata, não operacional. A14 demonstra convincentemente que três regras não definem o teto, mas a tabela 95→62/16 precisa ser publicada como artefato reproduzível antes de virar número do artigo (`docs/20260821_auditoria_conformidade_mop_crysl.md:305-320`).

A auditoria perdeu o defeito arquitetural mais importante: o IR não representa que uma chamada concreta pode gerar uma **palavra** de eventos, embora seu próprio A4 prove isso; `events: Map<Label,Set<Signature>>` presume relação conjuntista (`docs/20260821_conformidade_mop_crysl.md:1124-1136`). Também não transforma a cegueira a término em regra de composição do veredito global.

## 5. Dez alegações estruturais

1. Comparação como produto: **aceita para a pesquisa; separar o gerador como marco/produto** (`docs/20260821_conformidade_mop_crysl.md:28-56`).
2. Equivalência de linguagem: **correta para ORDER**, calculada por duas inclusões; refinement é a apresentação acionável. Bisimulação não é necessária.
3. Precedência: **confirmada**; Xtext faz `|` mais forte que `,` (`audit/20260808_validacao_jca_android/fase0/upstream_CrySL_e92f5607.xtext:103-133`), Rascal faz o inverso (`../../MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-69`). “Exatamente uma de 33” foi rederivado por um subagente por análise de profundidade, mas o transcript detalhado não foi depositado; fica **UNVERIFIED para reprodução externa**.
4. M2-eff: **válida como observação diferencial, não oráculo único** (`docs/20260821_conformidade_mop_crysl.md:211-243`).
5. N1: **não demonstrada como lei geral** (`:245-282`).
6. `IncompleteOperationError`: a alegação “sem contraparte MOP” é **REFUTED por execução**. O fork declara `endObject`, `endProgram` e `endThread` (`../javamop/src/main/javacc/javamop/parser/main_parser/javamop.jj:356-358`). O exemplo `FileClose`, cuja ERE exige `close+ endProg` (`../javamop/examples/EndProgram/FileClose/FileClose.mop:16-23`), passou por JavaMOP→RV-Monitor→ajc e denunciou exatamente dois writers não fechados em `/tmp/mop-review-endprogram.BFIDCU`. A equivalência de `endObject` com o ciclo de vida CrySL permanece **UNVERIFIED**; investigar antes de classificar a obrigação como inexprimível.
7. Fronteira mono-parâmetro: **recusa principiada para JCA; gap expressivo para JavaMOP geral** (`:1155-1180`).
8. JSON/processos: **boa escolha pragmática, condicionada a IR sem perda e schema versionado** (`:1113-1136`).
9. Substrato: **parâmetro real; aridade 2 não é teto do design**, pois `PredicateStore` é N-ário (`../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java:24-35,231-253`).
10. Ciência: **defensável somente como estudo de fronteiras/monitorabilidade com avaliação externa e reproduzível**, não como automação local (`docs/20260821_conformidade_mop_crysl.md:909-925`).

## 6. Riscos ranqueados e testes baratos

1. **Veredito semanticamente falso por co-disparo/handlers/guardas.** Teste barato: extractor de join points + cinco probes concretos, incluindo Cipher e mutação `@fail {}`.
2. **Classpath experimental errado.** Teste: parse 214/214 dentro do classpath efetivo do filho MOP e reader novo por regra no filho CrySL.
3. **Oráculo contaminado.** Teste: diff cláusula-a-cláusula versionado `R_java→R_android`, nunca contagem agregada.
4. **Geração superestimada.** Teste: piloto estratificado de 8–10 regras com gate completo e artefatos publicados.
5. **M2-eff frágil a versão.** Teste: differential M2-decl/M2-eff em todos os 23 monitores e duas versões do gerador.
6. **Denominador móvel.** Teste: manifest com hashes dos quatro artefatos e categorias exhaustivas.
7. **Contribuição local demais.** Teste: hold-out de regras e um segundo corpus/DSL ou replicação externa.

## 7. Recomendações em ordem de retorno

**Mecânicas:** corrigir números e cruzamentos A1–A14; publicar censos e comandos; carimbar commits; mudar quatro→cinco substituições; executar a testemunha substituta; tornar saneamento AST um gate; renomear resultados para `M1..M4` específicos, sem `PASS global`; versionar JSON e preservar relação join point→sequência de eventos; mover o pin de Guava para cada filho; executar V6 com reader/resource set novos por arquivo; trocar conjuntos de cláusulas por listas com IDs.

**Decisões humanas:** aprovar primeiro apenas o comparador vertical; decidir se término entra num M5 ou torna o global `UNKNOWN`; escolher `api30` corrigido ou dupla referência como oráculo; exigir hold-out e baseline antes de alegação científica; só então autorizar `crysl2mop`. O nome `mop2crysl` deve ser abandonado: ele codifica o produto rejeitado, enquanto o plano recomenda “conformidade” (`docs/20260821_conformidade_mop_crysl.md:1152-1153`).

## 8. Transcrições essenciais reproduzidas

### 8.1 Corpus JavaMOP

Com classpath produzido por `mvn -o -q dependency:build-classpath`, cada `.mop` dos cinco diretórios foi processado isoladamente por:

```text
java -cp "$CPM" javamop.JavaMOPMain -merge -d "$out" "$spec"
TOTAL=214 OK=214 FAIL=0
```

Saída: `/tmp/mop-review-parse214.sdO8ib`. Isso confirma capacidade sintática, não integridade semântica.

### 8.2 Censos e precedência

```text
GENERIC total=118 buckets={1:21,2:40,3:30,4:17,5:6,6:4} multi=97
PROPERTY count=26
PAIRING paired=22 unpaired=11
M3 all=62 paired=55
M4 all=92 paired=73 kinds={REQUIRES:36, ENSURES:54, NEGATES:2}
PRECEDENCE affected=1
PRECEDENCE_RULE Cipher: Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+
```

Script `/tmp/d1d2_recount.py` (SHA-256 `7b00c6099f05ae7f2d101789c01ffda76183016b270bbdb4f2a8f4b6af1247a9`); output `/tmp/d1d2_recount.out` (SHA-256 registrado na D1). O scanner extraiu ORDER, acompanhou profundidade de parênteses e marcou coexistência de `,` e `|` no mesmo nível.

### 8.3 Leitor CrySL isolado

Após cinco normalizações, `CrySLModelReader` novo por arquivo:

```text
FAIL AlgorithmParameters.crysl
FAIL DigestOutputStream.crysl
FAIL Signature.crysl
SUMMARY ok=30 fail=3 total=33
```

Comandos e saída estão em `/tmp/IsolatedRead.java`, `/tmp/normalize_api30.py` e `/tmp/isolated_read.out`. Um probe adicional produziu `fresh Signature FAIL; reused after GCM OK; fresh again FAIL`, confirmando vazamento de `OBJECTS`.

### 8.4 Cipher e término

Cipher B:

```text
[EV] g1
[EV] i2
[EV] f1
>>> [FAIL] ev=f1
[EV] f2
>>> [FAIL] ev=f2
```

Cipher C inverteu a emissão para `f2`/`f1`, mas ainda terminou em FAIL. No exemplo terminal, cinco writers, dois não fechados, produziram cinco mensagens `Program has ended` e duas mensagens `You should close the file you wrote.`. Ambos foram gerados, tecidos e executados em JSE; nenhum emulador foi usado.

### 8.5 Realizabilidade da testemunha substituta

```text
mode=1 (ENCRYPT_MODE)
wrap=IllegalStateException: Cipher not initialized for wrapping keys
doFinal=OK
mode=3 (WRAP_MODE)
wrap=OK
doFinal=IllegalStateException: Cipher not initialized for encryption/decryption
```

Comando: `javac -d /tmp /tmp/WrapFinalProbe.java && java -cp /tmp WrapFinalProbe`. Isso não refuta a inclusão abstrata calculada sobre símbolos; refuta chamar sua testemunha de “realizável” e impede inferir falsos negativos concretos sem uma camada de realizabilidade.

## 9. Não verificado

- V1–V10 completos não foram todos repetidos; foram repetidos V6 na condição arquitetural correta, parser 214/214, Cipher A/B/C, evento terminal, mutação de handler e censos centrais.
- 95→62 cláusulas/16 regras: ainda depende do censo da auditoria; a parte 62 do alvo foi recontada, a parte 95/origem não.
- Adequação de `endObject` à semântica exata de `IncompleteOperationError`: evento terminal global foi executado; equivalência por objeto não.
- Existência de outra testemunha **concretamente realizável** para o lado MOP\CrySL do Cipher: a substituta publicada foi refutada; não foi encontrada outra nesta revisão.
- Publicabilidade em TSE/ICSE/ASE: julgamento editorial não verificável; a seção D6 enumera condições necessárias, não garante aceitação.
- Comportamento em APK/emulador: não executado e nenhum emulador foi iniciado, conforme proibição do projeto (`CLAUDE.md:101-105`).
