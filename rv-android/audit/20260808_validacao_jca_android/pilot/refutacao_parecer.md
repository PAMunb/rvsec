# REFUTAÇÃO — revisão adversarial do parecer do juiz (rodada-piloto)

Revisor adversarial independente · 2026-08-08. Alvo: `pilot/juiz_sintese.md` e
`pilot/juiz_claims_resolvidos.csv`. Não re-audito as specs; audito o parecer. Todas as
verificações executáveis foram re-executadas em scratchpad próprio (subdiretório
`refutacao/`), lendo os artefatos gerados pelos agentes em `{alfa,beta,gama}/` sem tocá-los.

## 0. O que foi re-verificado com sucesso (base que NÃO consegui refutar)

Antes das objeções, registro o que resistiu à tentativa de refutação — isso delimita o
alcance das objeções abaixo:

1. **Re-soma integral do score** a partir do CSV: 65 resolvidos (32 PASS, 33 FAIL),
   7 INCONCLUSIVE, denominadores por dimensão exatamente como na tabela
   (`juiz_sintese.md:162-171`): 20×4/7 + 20 + 15×3/9 + 15×8/13 + 15×9/15 + 10×1/12 + 5×2/4
   = **57,99 ≈ 58,0**. Aritmética e regra de denominador do pré-registro §6 corretas;
   rótulo "INCOMPLETO" aplicado como exigido.
2. **Caminhada independente dos 5 contraexemplos** sobre as tabelas do artefato
   (`beta/gen_cipher/out/CipherSpecRuntimeMonitor.java:405-418`, re-parseadas por script
   próprio): `G I I`→@fail, `G I U U`→@fail, `G I W Fw` e `G I Fw W`→estado 4 aceitante,
   `G I W U`→estado 2 sem @fail; cascata pós-`__RESET` (`u1[0]=f1[0]=f2[0]=wkb1[0]=5`) e
   `g3[0]=0`/`init2[0]=5` confirmados. Tabelas de Beta e Gama byte-idênticas (diff vazio).
   Lado CrySL conferido no oráculo (`MetaCrySL/generated/api30/Cipher.cryptsl:116-117`:
   `Inits+`, `updates+`, `w+ |(...)+` exclusivos). **ALFA-CIP-01/02/03/06/22 e os G3-FAIL
   estão corretamente resolvidos.**
3. **Citações estruturais do juiz (§0.5)**, todas conferidas no fonte: 3-arg →`"unknown"`
   (`ErrorDescription.java:35-37`); `validate` binário sem casa de algoritmo
   (`ExecutionContext.java:118-120`); dois `event c1` + `ere : c1 | c2` no `.mop` do GCM;
   `{1,2,2}` na linha 93 dos dois artefatos; `return false` antes de `handleEvent` e corpo
   antes de `handleEvent` em `Prop_1_event_init2` (`:495-506`); wrapper testa flags ignorando
   o retorno (`:917-924`); `import java.util.*` na linha 8; literal `jca` e probe sem `"30"`
   (`rv_static_analysis/config.py:186-207`); `get_static_analysis_config` sem
   `mop_dir`/`targets_file` nos kwargs (`rv_experiment/config.py:928-950`); dedupe exclui
   `expecting` (javadoc do próprio `ErrorDescription.java:131-135`); mensagem
   `AES/PCBC/ISO10126Padding` × `MODES` sem PCBC para AES
   (`CipherSpec.mop:55-56`, `AndroidCipherTransformationUtil.java:94`); escrita
   `GENERATED_KEY` sem algoritmo (`KeyGeneratorSpec.mop:113-114`); ENSURES do api30 só com
   os 3 `encrypted` (`Cipher.cryptsl:187-194`); `divergence_record.csv` linha `be31fad07d4a`
   existente e registrando o `condition(...)`.
4. **Conferência (e) do mandato**: a premissa "72 resolvidos vs 70 declarados (34+19+17)"
   é **falsa**. Os CSVs dos agentes contêm 34+20+18 = **72** claims e o juiz resolveu os 72
   em bijeção exata (diff de IDs vazio nos dois sentidos). Não há claim de agente não
   resolvido nem claim inventado pelo juiz.
5. **INCONCLUSIVE→PASS com teste novo** (conferência (d)): ALFA-GCM-01 e ALFA-GCM-08 têm
   evidência executável nova (artefatos gerados nesta rodada, verificados por mim), como o
   pré-registro exige. Não são conversões por consenso.

Consequência: **nenhuma objeção abaixo alcança os vereditos REPROVADA/REPROVADA**, que se
apoiam em FAILs re-verificados independentemente. As objeções atingem resoluções PASS
individuais, classificações de severidade e a leitura do score.

## 1. Objeções

### REF-01 — ALFA-CIP-17/18: "sem registro algum" é factualmente falso; o registro existe em `tasks.md` 4.11
- **Alvo**: `juiz_claims_resolvidos.csv:20` (ALFA-CIP-17, "OMITIDA (critica; sem registro
  algum)", evidência "ausente de data/gh101"), `:21` (ALFA-CIP-18, "comentario no spec sem
  registro formal"); matriz #14 (`juiz_sintese.md:66`), que descarta a citação de Gama
  ("tarefa 4.11") como "comentário no spec".
- **Tipo**: contraevidência ignorada / evidência insuficiente na resolução.
- **Fundamento**: `openspec/changes/gh101-jca-spec-conformance/tasks.md:117` — tarefa 4.11,
  marcada `[x]`: *"Record as out of scope, with the reason, the clauses the fusion also
  destroyed and this change does not restore: `noCallTo(IWOIV)` and `callTo(iv)` in the
  `Cipher` rule…"*, incluindo a nota de recuperabilidade (o mesmo `instanceof` do init-3).
  Isso não é comentário de spec: é registro deliberado de omissão, com razão, no ledger da
  change. Gama apontou a tarefa (`gama_sinergia.md:57`) e o juiz a conflacionou com o
  comentário do `.mop`. O critério pré-registrado (§4, `pre_registro.md:56-57`) define major
  como "OMITIDA **sem registro de omissão deliberada**" — o registro existe para c2 E c3.
- **Gravidade**: muda a **classificação** de dois claims (c2 deixa de ser "sem registro
  algum"; c3 deixa de ser "sem registro formal"), e a severidade de c2 passa a depender
  apenas do FN realizável (defensável como crítica por essa via, mas o fundamento escrito
  está errado). **Não muda** as resoluções FAIL nem o G4 FAIL (omissão registrada continua
  bloqueando aderência total — `modelo_semantico.md:98-99` — e c4/c5–c8/14a permanecem).
  Ironia registrável: o próprio juiz recomenda (ajuste 5, `juiz_sintese.md:240-244`) que
  "procurei registro e não achei" seja passo obrigatório **com localização exata pesquisada**
  — e a sua resolução pesquisou só `data/gh101/`, não o ledger da change.
- **Teste que resolveria**: busca padronizada de registro em `data/gh101/` + `openspec/
  changes/gh101-*/` (tasks/design/proposal) antes de qualquer rótulo "sem registro".

### REF-02 — ALFA-GCM-05: PASS "COMPROVADA" com evidência "INFERIDO" viola o pré-registro
- **Alvo**: `juiz_claims_resolvidos.csv:32` — resolução PASS, classificação
  "DIVERGENCIA_EQUIVALENTE_COMPROVADA **(INFERIDO da API)**".
- **Tipo**: violação de pré-registro / contradição interna do rótulo.
- **Fundamento**: o rótulo normativo exige equivalência **comprovada**
  (`modelo_semantico.md:94-99`: "demonstrar formalmente a discriminação"); a linha de
  decisão Binding/cláusula do pré-registro (`pre_registro.md:41`) dá INCONCLUSIVE quando a
  determinação exige execução não realizada. A equivalência (ctor lança
  `IllegalArgumentException` exatamente nos casos das condições extras, tornando-as
  sempre-verdadeiras sob `after returning`) depende do comportamento do construtor no
  android-30 **em execução**, que ninguém executou — a pendência do próprio juiz o admite
  ("comportamento do ctor nao verificado contra android-30 em execucao"). Harness JVM sem
  emulador bastava (mesma classe de teste que o juiz propõe em D-piloto-2 para casos
  análogos).
- **Gravidade**: resolução deveria ser INCONCLUSIVE (ou o rótulo rebaixado a divergência
  não comprovada). Score: bindings 15×3/9=5,0 → 15×2/8=**3,75** (total ≈56,7). Não muda
  vereditos.
- **Teste**: harness JVM chamando os dois ctors com casos-limite (offset/len inválidos,
  tLen negativo) contra o android-30 congelado.

### REF-03 — BETA-SET-03: PASS por leitura em claim de toolchain contradiz a regra que o próprio parecer enuncia
- **Alvo**: `juiz_claims_resolvidos.csv:53` (PASS, "escopo codigo"); matriz #17
  (`juiz_sintese.md:69`).
- **Tipo**: contradição interna / evidência insuficiente.
- **Fundamento**: o preâmbulo do parecer declara "alegação só de leitura não fecha claim de
  toolchain" (`juiz_sintese.md:4-5`). BETA-SET-03 é fechado PASS na dimensão toolchain com
  evidência exclusivamente de leitura de código (`MonitorInvokeBuilder.java:69-78` etc.) e
  com o nível DEX explicitamente NÃO_VERIFICADO ("evidencia V0/V2 da gh100 segue alegacao
  de terceiro"). O re-escopo ("no escopo código") é divulgado, mas converte em PASS pleno de
  denominador um fenômeno cuja metade decisiva (o que é tecido de fato) está INCONCLUSIVE.
- **Gravidade**: PASS→INCONCLUSIVE deslocaria toolchain 9,0 → 15×8/14≈**8,57**. Qualifica
  G-toolchain; não muda vereditos. Alternativa mínima: manter PASS mas retirar a aparente
  simetria com os demais "fato medido" da dimensão (rotulá-lo como escopo-reduzido no CSV,
  campo `resolucao`, não só na pendência).
- **Teste**: weave dexlib2 de APK sintético + baksmali diff (G6), já previsto.

### REF-04 — Assimetria 14a × 14b: mesmo tipo de dependência semântica externa, resoluções opostas
- **Alvo**: `juiz_claims_resolvidos.csv:16` (ALFA-CIP-14a FAIL, INCORRETA major) vs `:17`
  (ALFA-CIP-14b FAIL→INCONCLUSIVE); justificativa em `juiz_sintese.md:112` e §2.3 (:120-126).
- **Tipo**: inconsistência de critério (potencial violação do pré-registro §3).
- **Fundamento**: 14b foi rebaixado a INCONCLUSIVE porque o **impacto** depende de semântica
  externa não testada (resolução case-insensitive do JCA). 14a depende igualmente de
  semântica externa não testada — `part()` do CogniCrypt sobre componente ausente — que o
  próprio juiz declara "não verificada" na mesma linha. A diferenciação oferecida (a
  convenção `''` está nos literais do próprio oráculo: RSA c13 e ChaCha20 listam `''`) é um
  argumento real, mas prova apenas que `''` é um valor possível de `part(1)`, não que
  componente **ausente** avalia a `''` — exatamente a lacuna que mantém 14b aberto.
- **Gravidade**: 14a FAIL→INCONCLUSIVE é defensável pelo mesmo padrão aplicado a 14b;
  bindings iria a 15×3/8=5,625 (com REF-02 junto: 15×2/7≈4,29). Não muda G4 (as omissões
  restantes sustentam o FAIL). Alternativa: manter 14a FAIL e **re-elevar 14b a FAIL**
  (a divergência textual é fato nos dois) — qualquer das duas restaura a consistência;
  o parecer atual não escolhe nenhuma.
- **Teste**: o próprio D-piloto-2 (teste de `part()` sobre componente ausente + folding×JCA)
  — que o juiz já propõe; a objeção é ao par de resoluções emitido **antes** do teste.

### REF-05 — ALFA-CIP-15/16: severidade "minor" atribuída por mitigação INFERIDA, contra a letra do pré-registro
- **Alvo**: `juiz_claims_resolvidos.csv:18-19` (c4 encmode e c5–c8 comprimentos, "OMITIDA
  (minor)").
- **Tipo**: violação de pré-registro (severidade).
- **Fundamento**: `pre_registro.md:56-57` — OMITIDA sem registro de omissão deliberada é
  **major**. c4 e c5–c8 não constam de `data/gh101/` nem da tarefa 4.11 (verifiquei: 4.11
  registra só `noCallTo`/`callTo`/`neverTypeOf`). O rebaixamento a minor apoia-se em
  mitigação pela API (`InvalidParameterException`) que a própria resolução marca como
  "INFERIDA - confirmar em harness". Severidade importa: G13 exige nenhum major aberto.
- **Gravidade**: reclassificação minor→major de 2 claims; sem efeito no score (seguem FAIL)
  nem nos vereditos-piloto; efeito real é a contabilidade de pendências para G13.
- **Teste**: harness JVM: `cipher.init(7, key)` e os 4 casos de comprimento, observando se a
  exceção da plataforma cobre o FN alegado.

### REF-06 — Score: atribuição claim→dimensão ex post e mistura spec×conjunto tornam o 58,0 sensível a escolhas não pré-registradas
- **Alvo**: `juiz_sintese.md:156-178` e coluna `dimensao_score` do CSV.
- **Tipo**: erro/fragilidade de score (qualificação, não aritmética — a soma confere).
- **Fundamento**: (i) o pré-registro fixa pesos e regra de denominador, mas **não** a
  atribuição de cada claim a uma dimensão — feita pelo juiz na resolução; fenômenos únicos
  entram como FAIL em até 3 dimensões (supressão do GCM: bindings ALFA-GCM-03, predicados
  ALFA-GCM-04/GAMA-GCM-03, diagnóstico BETA-GCM-04) enquanto a metade FAIL de BETA-GCM-02
  ("FAIL(texto)") foi re-alojada em GAMA-GCM-01 (toolchain), mantendo BETA-GCM-02 como PASS
  puro em linguagem — decisão coerente, mas com efeito direto de +1 PASS em linguagem que
  não passou por regra pré-registrada; (ii) 12 claims SET-wide (BETA-SET-*, GAMA-SET-*)
  entram no denominador de um score apresentado como "do piloto (2 specs)". O juiz declara
  a limitação (i) de fenômenos ((`juiz_sintese.md:175-178`)), mas não a (ii) nem a
  discricionariedade da atribuição.
- **Gravidade**: só qualifica: o número 58,0 está aritmeticamente certo e rotulado como
  descritivo/incompleto/sem gate; a objeção é que variações razoáveis de atribuição o movem
  ~±2 pontos (com REF-02/03/04: ≈56–57), o que deve ser dito na rodada das 23.
- **Teste**: o próprio ajuste 6 do juiz (ID de fenômeno) + pré-registrar a regra de
  atribuição claim→dimensão e o tratamento de claims de conjunto antes da rodada das 23.

### REF-07 — GAMA-CIP-07: rebaixamento FAIL→INCONCLUSIVE fundado em raciocínio não executado (assimetria de padrão probatório) — MENOR
- **Alvo**: `juiz_claims_resolvidos.csv:62`; `juiz_sintese.md:113`.
- **Tipo**: evidência insuficiente (na direção oposta à usual).
- **Fundamento**: o juiz exige teste novo para subir INCONCLUSIVE→PASS, mas desce FAIL→
  INCONCLUSIVE com um argumento de leitura não executado ("transformation com `\n` não
  sobrevive ao `getInstance`" — plausível, pois o evento é `after returning`, mas nenhum
  harness o demonstrou; provedores exóticos e outras strings serializadas não foram
  descartados por medição). Atenuante: o próprio Gama rotulou o claim INFERIDO, e
  INCONCLUSIVE é o estado pré-registrado para "não determinável por leitura + execução".
- **Gravidade**: menor — direção favorável à spec (retira um FAIL do denominador de
  diagnóstico: 0,83 vs 0,77); vereditos intactos (G9 já FAIL por outros cinco claims).
- **Teste**: harness de serialização com string controlada contendo `\n` (já proposto).

### REF-08 — BETA-CIP-10 / "captura 20/20": ameaça de FP realizável (A1) fica sem estado normativo — MENOR
- **Alvo**: `juiz_claims_resolvidos.csv:45`; manchete "captura 20,0/20" e G5 PASS
  (`juiz_sintese.md:165,195`).
- **Tipo**: contraexemplo potencial não adjudicado / lacuna de cobertura declarada.
- **Fundamento**: BETA-CIP-10 documenta FP condicional (creation em todo evento: `init`
  sem `getInstance` observado → monitor nasce em 0 → fail imediato). Resolvido PASS
  ("mecanismo observado") com o FP relegado a pendência; ele não aparece em nenhuma
  categoria do §3 nem há claim INCONCLUSIVE que o carregue. Além disso, a dimensão 5 do
  modelo semântico (paramétrica/ciclo de vida — `modelo_semantico.md:83`) não tem **nenhum**
  claim nem gate no piloto, e a declaração de escopo (`juiz_sintese.md:181-186`) só exclui
  G6/G8/G10 — a lacuna não é declarada. A conclusão §6 "o piloto validou o protocolo no
  essencial" não registra que uma das sete equivalências obrigatórias não produziu claims.
- **Gravidade**: menor para os vereditos (REPROVADA não depende disso); relevante para a
  alegação de validação do protocolo. Sem efeito aritmético (captura ficaria 4/4=20,0).
- **Teste**: claim próprio de ciclo de vida por spec na rodada das 23 (interleaving,
  identidade, creation) + declarar a dimensão 5 no escopo de cada rodada.

### REF-09 — §2.2 incompleto: resoluções que normalizaram posições qualificadas não estão na tabela de mudanças — MENOR
- **Alvo**: `juiz_sintese.md:104-115`.
- **Tipo**: rastreabilidade.
- **Fundamento**: diff mecânico posição-do-agente × resolução (feito por script): além dos
  listados, mudaram sem constar de §2.2: BETA-GCM-02 `FAIL(texto)/PASS(linguagem)`→PASS
  (a metade FAIL migrou para GAMA-GCM-01 — divulgado só na matriz #3), BETA-SET-03
  `PASS(codigo)/NAO_VERIFICADO(DEX)`→PASS, BETA-SET-05 `PASS(sem efeito no piloto)`→PASS,
  BETA-CIP-10 `PASS-com-ameaca`→PASS.
- **Gravidade**: menor; nenhum contraexemplo descartado (confirmo), mas a promessa de
  resolução claim a claim rastreável fica incompleta exatamente nos casos de re-escopo.

### REF-10 — Completude do produto BFS do GCM não argumentada no registro — MENOR
- **Alvo**: G3 PASS do GCM (`juiz_sintese.md:204`), apoiado em "no separating trace up to
  length 12" (`alfa_automata_output.txt:56`).
- **Tipo**: evidência com justificativa ausente (não incorreta).
- **Fundamento**: `alfa_automata_check.py:192` poda por estados visitados do produto, logo
  a busca é de fato completa quando o diâmetro do produto < 12 — verdadeiro para autômatos
  deste tamanho —, mas nenhum documento afirma nem calcula isso; o registro publicado diz
  apenas "até comprimento 12", que, lido literalmente, é verificação limitada
  ("verificação algorítmica" do pré-registro §3 pede decisão, não busca truncada).
- **Gravidade**: menor (o PASS é correto; o registro é que está incompleto).
- **Teste**: imprimir |estados do produto| e diâmetro no output do script na rodada das 23.

### REF-11 — "Duas rotas de geração independentes" superestima a independência — MENOR
- **Alvo**: `juiz_sintese.md:14-19` (§0.1) e matriz #3.
- **Tipo**: retórica de consenso.
- **Fundamento**: Beta e Gama usaram os mesmos jars, a mesma spec e o mesmo modo `-merge`;
  a identidade dos artefatos é consequência do determinismo do gerador (que o próprio Beta
  mediu por hash entre modos), não replicação independente. A evidência decisiva para H-GCM
  é o conteúdo do artefato (uma geração bastaria); a duplicação não acrescenta força e o
  texto a apresenta como acréscimo de confiança.
- **Gravidade**: menor; nenhuma resolução depende só disso.

### REF-12 — Triangulação G10 cobre android-37.0 (host), não o android-36 efetivo do Docker — MENOR
- **Alvo**: BETA-CIP-04/BETA-SET-05 e as frases "insensível ao G10" (matriz #12, G5 PASS).
- **Tipo**: ameaça à validade não tratada.
- **Fundamento**: o manifesto registra que a variante dexlib2 resolve `android-37.0` no
  host e `android-36` **no Docker** (`fase0/manifesto.md:54-58`, anomalia 3). Beta comparou
  30×37.0; ninguém comparou 36. A interpolação (API monotônica ⇒ 30⊆36⊆37) é plausível e
  provavelmente verdadeira para estas classes, mas é inferência, e o parecer repete
  "insensível ao G10" sem a ressalva do alvo Docker.
- **Gravidade**: menor; se 36 divergisse (improvável), afetaria G5 fora do host.
- **Teste**: rodar a mesma mesa contra `android-36/android.jar` do container.

### REF-13 — Coluna `classificacao` do CSV não normalizada aos seis estados da matriz normativa — MENOR
- **Alvo**: `juiz_claims_resolvidos.csv` (ex.: linhas 34 "registro", 35 "resolvido",
  36-39 "fato medido", 42 "presenca de __LOC fiel", 53 "escopo codigo", 73 "n/a").
- **Tipo**: desvio de esquema.
- **Fundamento**: `modelo_semantico.md:92-95` fixa os seis estados da matriz. Rótulos
  livres impedem agregação mecânica na rodada das 23 e o fechamento dos gates G11–G13 por
  contagem de estados.
- **Gravidade**: menor; nenhum juízo individual errado por causa disso.

## 2. Resumo

### Objeções capazes de mudar veredito
**Nenhuma.** Os dois REPROVADA sobrevivem a todas as objeções: os FAILs estruturantes
(G3 do Cipher, supressão de CONSTRAINT/REQUIRES, omissões, diagnóstico) foram re-executados
ou re-verificados independentemente nesta refutação e estão corretos. Também não há caso de
INCONCLUSIVE convertido em PASS sem teste novo, nem uso de consenso como prova em resolução
alguma (REF-11 é retórica, não fundamento).

### Objeções que mudam resolução ou classificação de claims (5)
- REF-01 (ALFA-CIP-17/18: registro de omissão existe em `tasks.md:117` — evidência da
  resolução factualmente errada; classificação muda, FAIL permanece);
- REF-02 (ALFA-GCM-05: PASS→INCONCLUSIVE pelo pré-registro);
- REF-03 (BETA-SET-03: PASS por leitura contradiz regra do próprio parecer);
- REF-04 (14a×14b: aplicar o mesmo critério aos dois — uma das duas resoluções está errada);
- REF-05 (ALFA-CIP-15/16: minor→major pela letra do pré-registro §4).

### Objeções de score
- Re-soma **confirma 58,0** (57,99; denominadores e pesos corretos; rótulos obrigatórios
  presentes). REF-02/03/04 deslocariam para ≈56,3–56,9 e elevariam os INCONCLUSIVE de 7
  para 9–10; REF-06 registra a sensibilidade da atribuição claim→dimensão e a mistura de
  claims de conjunto num score "de 2 specs". Nada disso abre ou fecha gate (o score não
  abre gate por pré-registro).

### Objeções menores
REF-07 a REF-13 (assimetria probatória no rebaixamento de GAMA-CIP-07; ameaça A1 e dimensão
5 sem estado nem declaração de lacuna; §2.2 incompleto; completude do BFS não argumentada;
retórica de independência; android-36 não triangulado; esquema de classificação livre).

### Nota sobre a conferência (e)
A discrepância "70 declarados × 72 resolvidos" sugerida no mandato desta refutação **não
existe**: 34+20+18 = 72 nos CSVs dos agentes, bijeção exata com o CSV do juiz.
