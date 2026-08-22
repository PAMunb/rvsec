# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 38/74, a 4.14 herda três dívidas)

**Data**: 2026-08-22 · **Branch**: `modules` · **Último commit**: `bd25a3aa`
**Progresso**: 38 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.13 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v16.md` (checkpoint 37/74).

> **A 4.13 fechou os quatro arquivos só de escrita da batelada A e deixou três dívidas nomeadas
> para a 4.14.** A que a 4.12 abriu (a janela contra `KeyGeneratorSpec.mop:80` e
> `KeyStoreSpec.mop:83`, testemunhada pela trace `SecretKeySpec-keygen-iv.txt`, hoje classificada
> `introduced` e que **tem de sair de `introduced`** quando a 4.14 migrar os dois produtores); o
> registro do `generatedKeypair` que a 4.13 roteou para a 5.10; e o `KeyPairGeneratorSpec.mop:111`,
> que é o último dos onze sítios de beco sem saída que o `design.md` conta. Leia a seção
> "Próximo passo" antes de abrir qualquer arquivo.

---

## O que estamos fazendo

Aplicando a change **gh105-predicate-wiring** (GitHub issue #105) pelo workflow OpenSpec.
A change fia as predicates CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) no conjunto `jca_android`,
que não as fiava: das 19 predicates conectáveis contra as 33 regras api30, o conjunto realizava
3 elos; as leituras de predicate viviam dentro de `condition(...)`, onde uma guarda falsa
suprime a transição e converte "origem de chave não modelada" num `InvalidSequenceOfMethodCalls`
errado; e os acusadores órfãos sustentavam no máximo 39.682 eventos = 56,1 % daquela categoria
publicada (teto medido sobre a campanha `jca`, não atribuição causal).

O gh104 fez o handler `@fail` falar. Esta change faz ele parar de disparar quando não deve.
O Grupo 3 fechou essa segunda metade para os 17 acusadores órfãos; a 4.3 provou que o mecanismo
chega ao dispositivo e liberou o Grupo 5; o Grupo 4 está migrando o conjunto arquivo por arquivo.
**Sete** dessas passagens fecharam elos ou janelas que o plano tinha roteado para depois, **duas**
reverteram a instrução que a própria tarefa carregava, e **duas** repararam o instrumento no
caminho.

---

## Regras de trabalho (não negociáveis)

**Siga `docs/WORKFLOW.md` rigorosamente.** Artefato OpenSpec **nunca** se edita com `Write`/`Edit`
direto — invoque a skill (`openspec-update-change`) pela ferramenta `Skill`. Ela **pede
confirmação antes de escrever cada artefato**, e isso não é formalidade: foi por ela que a sessão
do `946aad17` descobriu que o reparo tinha *dois* sítios, que a 4.10 descobriu que a 5.6 não
listava o quinto produtor, que a 4.11 emendou a regra de `propagation` do `spec.md` em vez de
dobrá-la em torno de um arquivo, que a 4.12 descobriu que uma frase do `spec.md` tinha acabado de
virar falsa, e que a 4.13 descobriu que o censo escrito na **própria tarefa** estava errado.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final. **Stage por caminho explícito, nunca `git add -A`**
— a árvore tem muita modificação pré-existente não relacionada (gh69, docs, experimentos, e onze
`data/gh104/evidence/harness/selftest*.md` modificados que **não são seus**).

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três, a 4.8 quatro, a 4.9 três mais duas, a 4.10 duas, a 4.11
duas, a 4.12 três, a 4.13 **cinco**; as trinta e nove foram levadas em opções com recomendação
**e medição**, e as trinta e nove recomendações foram ratificadas. Faça o mesmo — e leve
**medição** junto com a opção, não só argumento. Se a medição disser que duas opções são
indistinguíveis, diga isso *e diga onde elas deixam de ser* (foi o que decidiu a #36).

**O pesquisador contesta, e às vezes ele tem razão.** Na 4.11 a pergunta sobre a trace da rota
`int` voltou como *"como assim um parâmetro declarado Object não consegue receber Integer???"*.
Não era limitação legítima do harness, era defeito. Quando o pesquisador duvidar de uma limitação
que você aceitou, **meça a limitação** antes de defendê-la. A 4.13 aplicou isso sozinha: o
harness "não conseguia" produzir um `KeyPair`, e a limitação era um defeito de três linhas.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda antes de oferecer opções, e diga
explicitamente o que **não** muda. A 4.13 abriu com um parágrafo do que a passagem move
independentemente de qualquer decisão, uma tabela dos pontos de aceitação lidos do monitor
gerado, e uma tabela de medições — as cinco decisões saíram em duas rodadas.

**Diga o custo por inteiro.** A 4.11 removeu um falso-negativo e introduziu um falso-positivo. A
4.12 fechou uma cadeia e abriu uma janela, e mediu que a janela não custa relato nenhum. A 4.13
manteve duas escritas fora do ponto de aceitação e **declarou o que isso custa**: depois de um
segundo `c1`, sequência que regra e autômato ambos rejeitam, a escrita no corpo marca uma chave
que o autômato não aceitou.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente. Ele aparece
legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado inteiro
(INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando acertar,
**diga que acertou e por que não conta** (a 4.13 fez isso na varredura dos cinco `Property`).

**Vocabulário.** Neste projeto "especificação" é o objeto formal (`.mop`/`.rvm`, autômato
paramétrico, monitor tecido), avaliado pela eficácia empírica em achar defeitos no sentido de
Legunsen et al. (ASE'16). A seção 3 do `WORKFLOW.md` cita literatura de *spec-driven development*
assistido por IA, onde "spec" é o documento de requisitos que precede a geração de código —
**não é o sentido em uso aqui**.

---

## Artefatos da change (leitura obrigatória)

Em `openspec/changes/gh105-predicate-wiring/`:

| Arquivo | O que contém |
|---|---|
| `proposal.md` | o porquê, o escopo, o que é BREAKING |
| `design.md` | D-1 a D-14, o **ledger de 36 cláusulas**, o censo dos 17 órfãos |
| `specs/instrumentation/spec.md` | INV-INS-130 a INV-INS-148, Data Contracts, cenários WHEN/THEN |
| `tasks.md` | as 74 tarefas, com o comentário HTML de despacho no topo |

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
openspec instructions apply --change gh105-predicate-wiring --json
openspec validate gh105-predicate-wiring          # note: `validate` NÃO aceita --change
```

**A regra do `spec.md` que a 4.14 usa é o INV-INS-134**: uma escrita fica no ponto de aceitação,
ou carrega uma razão registrada no `predicate_graph.csv`. A 4.13 usou as duas metades no mesmo
commit — cinco escritas ao ponto de aceitação e duas no corpo com razão —, então há precedente
literal para as duas saídas.

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as doze evidências
que já existem, porque são as doze formas que uma passagem de arquivo pode ter:

| evidência | a forma |
|---|---|
| `data/gh105/evidence/f2-CipherSpec.md` (4.1/4.2) | a que move tudo |
| `data/gh105/evidence/f2-reach-probe.md` (4.3) | a que vai ao dispositivo |
| `data/gh105/evidence/f2-IvParameterSpec.md` (4.4) | a que não move sítio nenhum |
| `data/gh105/evidence/f2-SecureRandomSpec.md` (4.5) | a que fecha e abre janelas F2 |
| `data/gh105/evidence/f2-PBEKeySpecSpec.md` (4.6) | a que fecha uma cláusula sem ter sido mandada |
| `data/gh105/evidence/f2-PBEParameterSpecSpec.md` (4.7) | a que descobre um sítio que não acusava nada |
| `data/gh105/evidence/f2-GCMParameterSpecSpec.md` (4.8) | a que descobre uma especificação inteira muda |
| `data/gh105/evidence/f2-MacSpec.md` (4.9) | a que APAGA sítios em vez de movê-los |
| `data/gh105/evidence/f2-SecretKeySpecSpec.md` (4.10) | a que fecha janelas que o harness não enxerga |
| `data/gh105/evidence/f2-RandomStringPassword.md` (4.11) | a que apaga porque a ESCRITA é insustentável, e repara o instrumento |
| `data/gh105/evidence/f2-SecretKeySpec.md` (4.12) | a que mede a janela que ela mesma abre |
| **`data/gh105/evidence/f2-write-only-batch-a.md`** (4.13) | **a de quatro arquivos de uma vez, sem leitura nenhuma — onde a pergunta vira "quem lê a escrita?"** |

E duas que não são passagem de arquivo e sim **achado sobre o instrumento**:

| `data/gh105/evidence/f1-order-gate-precedence.md` | o G-ORDER lia a gramática ao contrário |
| (dentro da evidência da 4.8, seção "O gate que leu a especificação da forma antiga") | o G-CONF lia a cláusula só na guarda |

---

## O que foi feito

### Grupo 1 — substrato (rvsec-core) — 6/6, commit `b55a61a2`

`PredicateVerdict`, `PredicateStore` (chave de identidade fraca com `ReferenceQueue`, posições
`String`/`int`/`Integer` sem distinguir caixa, aridade N, `ensure/validate(Property, Object
bound, Object... values)`, `negate`, `validateAbsent`, `reset`), 19 testes JUnit, reset do
substrato no `TraceRunner.replay()`, `ExecutionContext.java` byte-idêntico em `FROZEN_PATHS`,
`Property` append-only.

**Decisão ainda a confirmar com o pesquisador**: `bound == null` é tolerado (no-op /
`NOT_OBSERVED` / `SATISFIED`) em vez de lançar, porque uma NPE dentro de advice tecido derruba a
app sob teste. A 4.4 a 4.13 já se apoiaram nessa tolerância.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 a 4.12: ver os handoffs v12 a v16

Em uma linha cada: **4.1+4.2** `CipherSpec`, o arquivo mais difícil (17/17 eventos, headroom
zero), `d71c8e64`; **4.3** a sonda de alcance em três camadas — *a change NÃO está bloqueada, o
Grupo 5 está liberado*, `4881b557`; **4.4** `IvParameterSpec`, `a9d8f2bd`; **4.5**
`SecureRandomSpec`, `a7e97294`; **4.6** `PBEKeySpecSpec`, `ba219f1a`; **4.7**
`PBEParameterSpecSpec`, `d64f3a40`; **4.8** `GCMParameterSpecSpec`, `5222a5d9`; **4.9** `MacSpec`,
`e86bd270` (apaga quatro sítios, o arquivo sai do grafo); **4.10** `SecretKeySpecSpec`,
`28cfa722`; **4.11** `RandomStringPassword`, `5f64c8de` (apaga os quatro sítios e repara o
`fitsPointcut`); **4.12** `SecretKeySpec`, `fbd861c6` (a última guarda; INV-INS-133 vai a zero, e
a janela que ela abre é medida em zero relatos); e a sessão de verificação `946aad17`, em que o
parser do G-ORDER foi desmascarado sem reparo.

### 4.13 — as quatro só de escrita, commit `bd25a3aa`

Evidência: **`data/gh105/evidence/f2-write-only-batch-a.md`** (301 linhas).
Arquivos: `SignatureSpec`, `MessageDigestSpec`, `SSLContextSpec`, `KeyPairSpec`.

Primeira passagem **sem nenhuma leitura**, o que troca a pergunta: não "o que este sítio acusa?"
(nada, escrita não acusa) mas "**quem lê esta escrita, e em que store?**".

**Nove dos onze sítios são becos sem saída, não sete.** O "sete" da tarefa era o número do
`design.md` para *sete predicados sobre onze sítios* em cinco arquivos, colado por engano nos onze
sítios da própria 4.13. Medido: nenhuma regra do api30 exige `signed`, `verified`, `digested`,
`generatedSSLContext` ou `generatedSSLEngine`; nenhum `.mop` de nenhum conjunto lê as cinco
`Property`; a única ocorrência que não é escrita é um driver de auditoria de 2026-08-08 que o
INV-INS-147 já lista como não mantido. Os nove levam registro de omissão. O `tasks.md` foi
corrigido pela skill.

Os outros dois, `KeyPairSpec.gpu`/`gpr`, têm leitor vivo (`CipherSpec.i2`, store novo desde a 4.1).

A tabela que decidiu a passagem (sonda sobre o `ErrorCollector` inteiro, **um processo por
configuração** — o conjunto de monitores é estático e `ExecutionContext.reset()` não o toca):

| configuração | pré-imagem | partida | corpo | `@match` | migrada real |
|---|---|---|---|---|---|
| A `new KeyPair` → `getPublic` → `Cipher.init` | 0 | 1 | **0** | **0** | **0** |
| A2 par do `KeyPairGenerator` → `getPublic` → `Cipher.init` | 1 | 2 | **1** | **2** | **1** |
| B `new KeyPair` → `getPrivate` → `Cipher.init` | 0 | 1 | **0** | **0** | **0** |
| C controle: chave sem origem observada | 0 | 1 | 1 | 1 | **1** |
| D controle: produtor já no store novo (4.10) | 0 | 0 | 0 | 0 | **0** |

**Cinco decisões ratificadas** (ver "Decisões", #35 a #39).

---

## Decisões ratificadas pelo pesquisador

**As decisões 1 a 25 estão no handoff v13, as 26 a 29 no v14, as 30 e 31 no v15 e as 32 a 34 no
v16** — leia-as lá. As mais citadas: **2** (escrita sem cláusula é apagada, não registrada),
**7** (mudança comportamental sem medição que a decida não entra em migração de substrato),
**11** (a retirada vai com a escrita que ela desfaz), **13** (a leitura sem cláusula também é de
três valores), **16** (o registro de omissão deliberada vem para a passagem do arquivo), **19**
(código sem caminho de execução é apagado quando mover criaria outro), **21** (o `@fail`
inalcançável é registrado, não reparado), **28** (a escrita move store e não move aridade), **31**
(o reparo do `fitsPointcut` entra na 4.11), **32** (a leitura do `SecretKeySpec.e1` fica,
governando a escrita), **34** (a confusão `RANDOMIZED` × `preparedKeyMaterial` continua
registrada).

### Na 4.13 (2026-08-22)

35. **As duas escritas do `KeyPairSpec` ficam no corpo do evento, com razão registrada** — não no
    ponto de aceitação, que é o padrão do INV-INS-134. O que decidiu foi a configuração A2: o
    `ere` é `c1 (gpu | gpr)*` e a regra api30 ordena `co?, (pu*, pr*)*`, com o construtor
    **opcional**, então um par vindo de `KeyPairGenerator.generateKeyPair()` nunca passou por uma
    chamada monitorada e `gpu` sai do estado 0 direto para `fail` (linha `{2, 1, 2}`). Uma escrita
    no ponto de aceitação deixaria esse programa com **2 relatos em vez de 1** — o
    `CIPHER-NOBS-00` que a passagem existe para tirar continuaria lá, na rota comum. O reparo do
    autômato é da **7.1** (o `KeyPairSpec` é ORDER-unmapped, o G-ORDER o pula e não checaria a
    mudança), e a divergência já está registrada em `conformance_record.csv` como
    measured-not-repaired, com **668 linhas do corpus em 8 aplicativos** (gh104 8.12(f)). Quando a
    7.1 entrar, as duas escritas vão para `@match`. **Custo declarado**: depois de um segundo
    `c1` — sequência que regra e autômato ambos rejeitam — a escrita no corpo marca uma chave que
    o autômato não aceitou.
36. **O `gpr` passa a escrever `GENERATED_PRIVATE_KEY`**, como a cláusula `generatedPrivkey[retPriv]
    after pr` nomeia, tomando a primeira metade da tarefa **6.1**. Reparado junto com a mudança de
    store e não adiado, porque o argumento que manteve a confusão #32 apenas registrada não vale
    aqui: medido, renomear fecha exatamente a mesma cadeia (o `CipherSpec.i2` lê os três
    predicados de origem como uma disjunção, coluna B = 0 nas duas formas). O que o nome da
    semente custa é a jusante, e a **5.7 roda antes da 6.1**: medido no store, uma chave privada
    marcada como pública responde `NOT_OBSERVED` a `initSign(priv)` — relato sobre programa
    conforme — e `SATISFIED` a `generatedPubkey`. Bônus medido: a única propriedade só-de-leitura
    do conjunto fecha (`[G-PRED2] repaired jca_android/CipherSpec.mop i2/GENERATED_PRIVATE_KEY`).
37. **O `v1`/`v2` do `SignatureSpec` passa a escrever o `byte[]` que `verified[sign]` nomeia**, no
    lugar do booleano devolvido. Sem custo medido (ninguém lê `verified`), e o que decidiu foi a
    medição do que a forma da semente é: `ensure(VERIFIED, true)` num store chaveado por
    identidade marca o `Boolean.TRUE` cacheado do JVM inteiro, e `validate` contra qualquer outro
    `true` do programa responde `SATISFIED`.
38. **O `generatedKeypair[this, _] after co` não ganha escrita fabricada.** A cláusula existe
    (`KeyPair.cryptsl:39`) e o `KeyPairSpec.c1` não tem sítio. O predicado não é exigido por regra
    nenhuma, seu outro produtor é `KeyPairGeneratorSpec.mop:111` (4.14), e **uma cláusula sem
    sítio não tem linha no `predicate_graph.csv`** porque o inventário é de sítios. O registro
    pertence à **5.10**, e a 4.13 escreveu a medição no texto dela em vez de duplicar.
39. **O reparo do `TraceRunner.produce()` entra na 4.13** (a forma da decisão 31). Ver
    "Achados", 47.

---

## Achados que valem mais que as tarefas

**Os achados 1 a 32 estão no v13, os 33 a 36 no v14, os 37 a 40 no v15 e os 41 a 46 no v16.**
Os mais operacionais:

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — registrado, não reparado; a família tem cinco membros.
4. **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila** — e que não lança.
8. **Códigos sem caminho de execução**: **quinze** depois da 4.13 (ver o achado 48).
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos**, e o veredito é **piso, não contagem**.
17. **Um evento inteiro pode não acusar nada, e o censo não mostra** — e, desde a 4.8, uma especificação inteira também.
29. **A mudez pode ser da especificação, não do evento.** Leia a tabela de transição no monitor gerado.
35. **`PredicateStore.validate` compara a tupla de valores.** Aridade divergente devolve `VIOLATED`, não `NOT_OBSERVED`.
38. **O `PredicateStore` não é simétrico entre vínculo e valor.** O vínculo é identidade fraca; as posições de valor normalizam `String` e `Integer` para texto.
40. **O `TraceRunnerTest` está VERMELHO no HEAD, e já estava.** 2 falhas de 6 (`everyTraceLineResolvesToAnAdvice` e `theFrozenSetAccusesALegitimateGetTrustManagers…`) — **não são regressão sua**, e não as repare dentro da gh105 sem levar ao pesquisador.
41. **Uma janela F2 pode não custar relato nenhum, e só a medição diz qual é o caso.**
42. **A tabela de transição decide onde a escrita vai, e às vezes as duas rotas coincidem.** Custa um `awk`.
43. **Um handler não vê parâmetro de evento.** Toda escrita no ponto de aceitação sobre um valor que só o evento conhece precisa de um campo de estágio, limpo ao ser consumido.
44. **`getEncoded()` devolve um clone novo a cada chamada.**
46. **Uma linha `unchanged` do harness pode ser exatamente a que mede o ganho.** Diga contra o que ela é `unchanged`.

### Novos, da 4.13

47. **Antes de aceitar uma limitação do instrumento, meça a sua LARGURA, não só a sua existência.**
    O `TraceRunner` não produzia `KeyPair`: `KeyPairGenerator.getInstance("RSA")` devolve
    `java.security.KeyPairGenerator$Delegate`, **não-pública**, e `setAccessible(true)` sobre o
    `generateKeyPair()` dela lança `InaccessibleObjectException` (*module java.base does not
    "opens java.security" to unnamed module*). O vínculo virava `null` **em silêncio**, porque
    linhas `bind` nunca entram em `unresolved`. Varri as catorze fábricas que o corpus usa e o
    defeito alcança **uma só**, e só nos dois métodos que o delegate sobrescreve — o
    `MessageDigest$Delegate` e o `Signature$Delegate` também não são públicos e **não** são
    afetados, porque não sobrescrevem os métodos que o corpus chama. O reparo (`onPublicOwner`,
    reprocurar a assinatura no supertipo público) muda **zero das 97 traces commitadas**.
    Corolário: uma limitação medida em largura vira um reparo de três linhas; medida só em
    existência, vira uma seção de "o instrumento não consegue".
48. **Uma escrita pode ser relocada para cima de um evento que nunca dispara, e isso é correto.**
    O `engine` do `SSLContextSpec` declara `call(public void SSLContext.createSSLEngine(..))` onde
    a API devolve `SSLEngine`, e os dois weavers casam o tipo de retorno exatamente — o advice é
    gerado e nunca dispara. O harness mostra isso dos **dois** lados (`SSLContextSpec.txt —
    ctx.createSSLEngine()` em *Lines no pointcut resolved*). Já está registrado como
    measured-not-repaired pelo gh104 8.7. A escrita foi relocada como a cláusula pede e continua
    sem caminho de execução: a forma da decisão 21.
49. **Um número escrito na tarefa pode estar errado, e o `design.md` é quem decide.** A 4.13 leu
    "sete dos onze" na sua própria tarefa e mediu nove. O sete era o número do design para *sete
    predicados sobre onze sítios* em **cinco** arquivos. Isto é o achado 60 do v16 na direção
    inversa: lá o handoff discordava do artefato; aqui **a tarefa discordava do design**, e o
    design ganhou. **Recontar o censo da tarefa contra a fonte é parte da passagem, não zelo.**
50. **Quatro arquivos numa passagem só é mais barato que quatro passagens.** Os quatro
    compartilham a mesma pergunta ("quem lê a escrita?"), a mesma resposta para nove sítios, um
    único harness (~13 min) e um único `git diff --stat` da evidência. O que **não** compartilham
    é a decisão: o `KeyPairSpec` sozinho gerou três das cinco. Agrupe pela pergunta, não pelo
    número de arquivos.
51. **`ExecutionContext.reset()` não zera o conjunto de monitores.** Uma sonda que roda várias
    configurações num processo só vaza estado de autômato entre elas — a primeira versão da sonda
    da 4.13 media 6 relatos numa configuração que sozinha mede 1. **Um processo por
    configuração.** (Isto refina o aprendizado 38, que só falava dos stores e do `ErrorCollector`.)
52. **O harness pode casar um pointcut a mais quando um argumento é `null`.** `c.init(1, null)`
    casa `CipherSpec.i1` (`init(int, Certificate,..)`) *e* `i2`, porque `fitsPointcut` aceita
    `null` para qualquer tipo não-primitivo; `i1` leva o autômato a `s2` e o `i2` seguinte cai em
    `fail`, e o resultado é um `CIPHER-ORDER-00` que o programa não tem. Foi assim que o vínculo
    nulo do achado 47 se disfarçou de defeito de ordenação. **Se uma trace der ORDER onde você
    esperava CONSTR, desconfie de um vínculo nulo antes de desconfiar do autômato.**

### Três defeitos de pipeline, fora do escopo desta change — relatório escrito, decisão pendente

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). D1: o caminho de experimento não fornece `ANDROID_SDK_HOME` e o
GATOR morre. D2: a análise estática mira `resources/jca` mesmo sob `--specification-set
jca_android` — **interage com o Grupo 5**. D3: o INV-EXP-16 não é aplicado.

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.**

Há ainda o **RISK-013 da gh69** (`openspec/changes/gh69-generic-subtype-target-matching/risk-register.md:565`),
que é sobre o `RandomStringPassword.mop` e é defeito de *análise estática*, não de runtime.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-22, depois da 4.13)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **0** ✅ | 0 |
| leituras em corpo | 0 | **14** | todas |
| escritas em corpo de evento (grafo) | 42 | **13** | 0 sem razão registrada |
| escritas no ponto de aceitação (grafo) | 7 | **17** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **11** | 0 |
| `remove()` em `@fail` | 8 | 7 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 + o registro `unclosable` da 6.5 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **9** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| linhas no `predicate_graph.csv` | — | **63** | — |
| linhas com `disposition=omission` | 0 | **6** | — |
| achados dos gates estruturais | 71 (na 4.8) | **30** (G-PRED2 13, INV-INS-130 9, INV-INS-134 8) | 0 |
| hunks no `divergence_record.csv` | — | **240**, todos registrados | — |
| traces do corpus | 63 | **100**, todas commitadas | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 100 traces contra `backup/gh105-preimage/jca_android`: **65 inalteradas, 19
movidas, 10 introduzidas, 6 removidas** (cumulativas contra a pré-imagem). Das 10 `introduced`,
**nove são reparos deliberados e uma é janela** — a `SecretKeySpec-keygen-iv`, que a 4.14 fecha.

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

`gh104_gates.py` sobre o monitor gerado: `G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 ·
G-ERE 0 · G-CONF 0 · **G-PRED 14**`. O G-PRED sobe por construção — conta os sítios de predicate
da semente que um arquivo migrado não tem mais, **um por arquivo migrado** — e é o espelho do
INV-INS-130 descendo. Estava em 10 na 4.12 porque dez arquivos estavam migrados; agora catorze.

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas são pré-change e estão desatualizados** (a 4.13 provou isso do
jeito caro — ver o achado 49). Esta tabela saiu do `predicate_graph.csv` em 2026-08-22, depois da
4.13. Reconfira com `--emit` antes de citar qualquer número numa evidência.

| arquivo | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove`/`negate` | tarefa |
|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 1 | 2 | 3 | 0 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 2 | 1 | 0 | 0 | 1 (`negate`) | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 2 | 0 | 1 | 0 | 0 | ✅ 4.7 |
| `GCMParameterSpecSpec.mop` | 2 | 0 | 1 | 0 | 0 | ✅ 4.8 |
| ~~`MacSpec.mop`~~ | — | — | — | — | — | ✅ 4.9 (**saiu do grafo**) |
| `SecretKeySpecSpec.mop` | 1 | 0 | 1 | 0 | 0 | ✅ 4.10 |
| ~~`RandomStringPassword.mop`~~ | — | — | — | — | — | ✅ 4.11 (**saiu do grafo**) |
| `SecretKeySpec.mop` | 1 | 0 | 1 | 0 | 0 | ✅ 4.12 |
| `SignatureSpec.mop` | 0 | 0 | 2 | 0 | 0 | ✅ 4.13 |
| `MessageDigestSpec.mop` | 0 | 0 | 1 | 0 | 0 | ✅ 4.13 |
| `SSLContextSpec.mop` | 0 | 0 | 2 | 0 | 0 | ✅ 4.13 |
| `KeyPairSpec.mop` | 0 | **2** (razão registrada) | 0 | 0 | 0 | ✅ 4.13 |
| **`KeyStoreSpec.mop`** | 0 | **2** | 0 | 2 | 2 | **4.14** |
| **`KeyManagerFactorySpec.mop`** | 0 | **2** | 0 | 2 | 1 | **4.14** |
| **`TrustManagerFactorySpec.mop`** | 0 | **2** | 0 | 2 | 2 | **4.14** |
| **`KeyGeneratorSpec.mop`** | 0 | **1** | 0 | 2 | 1 | **4.14** |
| **`KeyPairGeneratorSpec.mop`** | 0 | **1** | 0 | 1 | 1 | **4.14** |
| **`DHGenParameterSpecSpec.mop`** | 0 | 0 | **1** | 1 | 0 | **4.14** |
| **`HMACParameterSpecSpec.mop`** | 0 | 0 | **1** | 1 | 0 | **4.14** |

Reproduzir:

```bash
python3 -c "
import csv,collections
rows=list(csv.DictReader(open('data/jca_android/predicate_graph.csv')))
per=collections.defaultdict(collections.Counter)
for r in rows: per[r['file']][r['verdict']]+=1
for f in sorted(per): print(f, dict(per[f]))
"
```

---

## Próximo passo: 4.14 — a batelada B, e três dívidas que ela salda

Sete arquivos, **10 escritas / 11 chamadas de estado de aceitação**. O formato é o da 4.13 (a
pergunta é "quem lê a escrita?"), mas com três diferenças que mudam o peso.

### 1. A janela que a 4.12 abriu fecha aqui, e a prova é uma linha do harness

A 4.12 abriu uma janela contra **`KeyGeneratorSpec.mop:80`** e **`KeyStoreSpec.mop:83`**, os dois
produtores de `GENERATED_KEY` que continuam no store velho. A trace
`data/gh104/traces/SecretKeySpec-keygen-iv.txt` é a testemunha e está classificada `introduced`
hoje. **Quando a 4.14 migrar esses dois, essa linha tem de sair de `introduced`** — a evidência
da 4.14 deve mostrar isso, porque é a prova de que a janela era janela e não regressão. A coluna
"guardada pós-4.14" da tabela da 4.12 já mediu o que deve acontecer: a linha A vai a 0.

### 2. Os `remove()` em `@fail` NÃO são desta tarefa

A tarefa é explícita: *"Their `@fail` removals are NOT touched here — 6.4 owns all eight"*. São
sete hoje (a 4.9 levou o oitavo com as escritas que ele desfazia). **Mas** o critério da 4.6 e da
4.9 é que a retirada viaja com a escrita que ela desfaz (decisão 11) — se num destes sete
arquivos a escrita que o `remove()` desfaz for migrada aqui, a retirada tem de vir junto, e a
6.4 fica com menos. **Meça arquivo por arquivo e leve ao pesquisador se algum caso aparecer.**

### 3. `KeyPairGeneratorSpec.mop:111` é o último beco sem saída do design

O `generatedKeypair` é o sétimo dos sete predicados de beco sem saída que o `design.md` conta, e
`KeyPairGeneratorSpec.mop:111` é o seu sítio. Depois dele, os onze sítios da lista do design estão
todos dispostos. A 4.13 já mediu que o predicado não é exigido por regra nenhuma e roteou o
registro da metade `after co` (a do `KeyPairSpec.c1`, sem sítio) para a **5.10** — não duplique.

### O que conferir em cada arquivo antes de editar

- **`KeyStoreSpec.mop`** (2 escritas, 2 bookkeeping, 2 remove) — um dos dois produtores da janela
  da 4.12. **Atenção**: o gh104 8.12(a) registrou que este arquivo declara `ks` e vincula `k` em
  todo evento, o que dá **um monitor único para o processo inteiro** — leia esse registro em
  `conformance_record.csv` antes de raciocinar sobre o que a escrita marca.
- **`KeyGeneratorSpec.mop`** (1 escrita, 2 bookkeeping, 1 remove) — o outro produtor da janela.
- **`TrustManagerFactorySpec.mop`** (2, 2, 2) — **tem divergência G-ORDER aberta** (`g1 i1 gtm`),
  que é da 7.1, e o gh104 8.7 registrou que o `gtm1` vincula `k` e não `mf`, caindo na fatia vazia
  e transmitindo para todo monitor vivo. Diga isso na evidência.
- **`KeyManagerFactorySpec.mop`** (2, 2, 1) — a cláusula `generatedKeyStore[keyStore]` é o ledger
  #14, que a **5.9** fia; aqui só o produtor.
- **`KeyPairGeneratorSpec.mop`** (1, 1, 1) — ver acima.
- **`DHGenParameterSpecSpec.mop`** e **`HMACParameterSpecSpec.mop`** (0 corpo, 1 aceitação, 1
  bookkeeping cada) — as duas únicas da batelada cuja escrita **já está** no ponto de aceitação.
  A passagem delas é só store + bookkeeping. Diga isso em vez de deixar parecer que moveu algo.

### Depois da 4.14

A 4.15 fecha o grupo (gates de colocação verdes, baselines aposentadas pelo bloco `retired`) e a
4.16 roda `/rv-test-run tests/parity`. Só então o Grupo 5, que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.13)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20), que às
   vezes é o mesmo que o `@match` (achado 42). **E confira a aridade da cláusula contra a aridade
   da `Property`.** **Se não houver regra**, diga isso e diga o que o arquivo então é.
   **E reconte o censo que a tarefa afirma** (achado 49).
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   **Um processo por configuração** (achado 51). Se o corpus não tiver trace do sítio, **escreva a
   trace e meça a semente — antes da edição** (aprendizado 47). E **audite a sonda**: um controle
   que sabidamente acusa e um que sabidamente não, no mesmo carregador, e liste os dispatchers que
   ela encontrou. **Quando a passagem tiver mais de uma disposição possível, simule a
   alternativa** em linha entre os dispatchers reais (aprendizado 51) — e, depois de editar,
   **confira a simulação contra a árvore de verdade** (aprendizado 57).
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string (a 4.13 teve de apagar uma frase de comentário da semente por isso).
   **E não ponha comentário entre o `ere`/`fsm` e o primeiro `@`** (aprendizado 43); se o
   comentário for sobre o handler, ponha-o **antes** do `ere`.
   **Apague o campo que o bookkeeping órfã**, com as suas atribuições — precedente da 4.1
   (`Cipher cipher`) e da 4.13 (`Signature signature`, `MessageDigest md`, `KeyPair keyPair`).
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. **Preserve a ordem do arquivo** (aprendizado 44). Um sítio só de escrita
   não ganha código nenhum — mas as linhas existentes **mudam de `file_line`** quando a edição
   move linhas: relocate-as no lugar, sem reordenar.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato, as linhas ficam como estão
   — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade. **Confira que a trace replica inteira**
   (`unresolved: []`) antes de commitá-la, nos dois lados **e** contra o snapshot congelado
   (aprendizado 52). Uma trace pode ligar o valor devolvido (`k.getEncoded() -> enc`, aprendizado
   58) e usar `bind` para construir objetos sem disparar nada.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas — e **reconferir o
   round-trip depois de preencher** (aprendizado 34).
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo, com
   a coluna `task` acumulando. O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
   **Anexe as linhas novas no fim, na ordem do arquivo `.mop`, e não reordene o resto**
   (aprendizado 44). **Chaveie por `(file, hunk)`, nunca só por `hunk`** (aprendizado 45).
   Convenção de `kind`: bloco de comentário → `placement`; o sítio e o import → `predicate-store`;
   troca de valor ou de predicado escrito → `behavioural`.
   **Para mapear stale → novo**, recompute os hunks contra `git show HEAD:<path>` e case por
   sobreposição de linhas: é o que a 4.13 fez, e resolveu inclusive os hunks só de adição.
   Confira com `git diff --numstat` que o arquivo cresceu e não foi reescrito.
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class` — **e lembrar que é piso, não contagem**,
   e que um `unchanged` pode ser exatamente a linha que mede o ganho (achado 46).
   **`git diff --stat data/gh105/evidence/harness/` é a medida mais forte de "não mexi em mais
   nada"**: na 4.11, na 4.12 e na 4.13 só um relatório dos 23 mudou (aprendizado 53).
10. Conferir e reescrever a baseline (`--write`); ela preserva `retired`. Ela imprime uma linha
    `repaired` por achado que saiu — cole essas linhas na evidência.
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também.** São
    **três** censos e eles não estão juntos: o do conjunto (`counts["write"]`,
    `accepting-state`, `read_placement`), o do grafo (`read:body`, `write:body`,
    `write:acceptance`, `bookkeeping`) e o do gate de colocação (`len(guards)`, hoje **0**).
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md` (ou `f2-<lote>.md` se a passagem
    cobrir vários arquivos, como a 4.13).
13. Rodar as quatro suítes. **Apagar `data/gh104/traces/output/`** (achado 59). Commitar (stage
    por caminho explícito). Marcar o checkbox pela skill, junto com qualquer correção de texto que
    a passagem tenha descoberto nos artefatos.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java` (o envelope está em
  `getExpecting()`; os acessores são `getType()`/`getSpec()`, **não** `getErrorType()`)
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (`getErrors()` devolve um
  `Set`; `reset()` existe, e **não** zera o conjunto de monitores — achado 51)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (a gramática das traces;
  `fitsPointcut` reparado pela 4.11, `produce`/`onPublicOwner` pela 4.13) e `TraceRunnerTest.java`
  (**2 falhas pré-existentes no HEAD — achado 40**)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)
- Gramáticas: `rv-monitor/.../fsm/parser/FSMParser.jj` (o `alias`),
  `rv-monitor/plugins_logicrepository/ere/.../FSM.java:85` (o alias único do ERE),
  `rv-monitor/.../fsm/JavaFSM.java:160` (alias → categoria),
  e **`javamop/.../main_parser/RVParser.java:379`** (`propertyHandler` — o que exige o `@`)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: 7.6**)
- `scripts/gh104_gates.py` (**`_list_guarding` em `:783`**; a extração da fórmula em `:316-321`),
  `gh104_mop_lint.py`, `gh104_divergence_record.py`, `gh104_diff_harness.py`,
  `gh104_message_gate.py`
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`, **`conformance_record.csv`** (73 linhas — o catálogo
  measured-not-repaired do gh104; **leia-o antes de "descobrir" uma divergência**),
  `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (**100, todas commitadas**), `data/gh104/baseline.md` (o corpus publicado)
- `results/gh101_group8_jca_frozen_control/monitors/` (o snapshot contra o qual o
  `TraceRunnerTest` replica — uma trace nova tem de resolver **aqui também**)
- `data/gh105/evidence/`: as doze evidências de passagem, `f1-group-three-the-seventeen.md`,
  `f1-order-gate-precedence.md`, `reach-probe/`, `f1-*-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`
— para a 4.14, leia `KeyStore.cryptsl`, `KeyGenerator.cryptsl`, `TrustManagerFactory.cryptsl`,
`KeyManagerFactory.cryptsl`, `KeyPairGenerator.cryptsl`, `DHGenParameterSpec.cryptsl` e
`HMACParameterSpec.cryptsl` **antes** de abrir os `.mop`.

**Gramática do CrySL (somente leitura)**:
`/home/pedro/tmp/CryptSL/de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext`
— o `ORDER` está em :99-134. **É a fonte que decide qualquer dúvida de precedência.**

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 94 passando, ~80 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit
# achados por gate, de um golpe (hoje: G-PRED2 13 · INV-INS-130 9 · INV-INS-134 8):
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android 2>&1 \
    | grep -oE "\[INV-INS-[0-9]+\]|\[G-[A-Z0-9']+\]" | sort | uniq -c

# lint e gate de mensagens do gh104 (os dois quebram com facilidade numa migração)
uv run python scripts/gh104_mop_lint.py $SPECS/jca_android
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# gerar o monitor a partir do conjunto editado (~75 s) — é o teste de gramática mais barato
uv run rv-monitor-generator generate --specs-dir $SPECS/jca_android --output <dir>

# os gates estruturais sobre um monitor já gerado (use o scratch do harness: os três gates
# derivados do diretório do conjunto pulam se o monitor não estiver nesse layout)
M=$(ls -dt ~/tmp-gh104/gh104-harness-* | head -1)/b/monitors/MultiSpec_1RuntimeMonitor.java
uv run python scripts/gh104_gates.py --monitor $M \
    --allowlist data/jca_android/gate_allowlist.csv \
    --crysl /home/pedro/.../MetaCrySL/generated/api30 \
    --alias data/jca_android/alias_table.csv \
    --constraint-table data/jca_android/constraint_table.csv
# hoje: G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 14

# ler a tabela de transição de uma especificação no monitor gerado (achado 42)
awk '/^class <Spec>Monitor /,/^}/' $M | grep -E "transition_|Category_"

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android
# ATENÇÃO: para uma regra cujo ORDER tem `,` e `|` no mesmo nível de parênteses (só a Cipher),
# `parse_expression` responde sob o parse ERRADO. Reparo na 7.1.

# baseline (comparar; --write depois de reparar qualquer achado — preserva `retired`)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS --write

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~13 min) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON (inclusive o "scratch") fica no TOPO da saída
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android --b $SPECS/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f2
# e depois, a medida mais forte de "não mexi em mais nada":
git diff --stat -- data/gh105/evidence/harness/
# ATENÇÃO: o TraceRunner deixa um data/gh104/traces/output/ de sucata — apague antes de commitar

# replicar UMA trace nova antes de commitá-la (os dois lados + o snapshot congelado)
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
TC=$RVSEC_HOME/rvsec/rvsec-mop/target/test-classes
java -cp "$TC:$CP" br.unb.cic.mop.harness.TraceRunner <monitorDir> <tracesDir> <workDir> <out.json>
#   monitorDir: <scratch>/{a,b}/monitors  e  results/gh101_group8_jca_frozen_control/monitors
# se editar o TraceRunner: mvn -o -q test-compile -pl rvsec/rvsec-mop -DskipMopAgent -DskipTests

# sonda de contagem sobre o ErrorCollector inteiro (receita completa na evidência da 4.13, que
# tem UM PROCESSO POR CONFIGURAÇÃO e os modos "árvore que você não tem" + os dois controles)
javac -nowarn -cp "$CP" -d <dir> Probe.java
java -cp "<dir>:$CP:<scratch>/<lado>/work/classes/classes" Probe <árvore> <modo> <configuração>

# testes JUnit do lado Java (ATENÇÃO: TraceRunnerTest tem 2 falhas pré-existentes — achado 40)
cd $RVSEC_HOME
mvn -o test -pl rvsec/rvsec-mop -DskipMopAgent -Dtest=TraceRunnerTest

# build do reator Java (JDK 21 no prefixo; recurso serializado) — ~50 s
mvn clean install -DskipMopAgent -DskipTests
```

**Execução de dispositivo** (só a 8.5 ainda precisa; o rv-platform gerencia o emulador inteiro):

```bash
export RVSEC_HOME=/home/pedro/.../rvsec
export ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk
export ANDROID_SDK_HOME=$ANDROID_HOME     # obrigatório: sem ele o GATOR morre (defeito D1)
uv run rv-experiment run --tools aperv:sata_mop --timeouts 300 --repetitions 1 \
    --apks-dir ./apks_examples --specification-set jca_android \
    --instrumentation-variant dexlib2 --name <nome> --no-window
```

---

## Aprendizados que custaram tempo (não redescobrir)

**Os aprendizados 1 a 46 estão no v13, os 47 a 50 no v14, os 51 a 56 no v15 e os 57 a 60 no v16.**
Os que a 4.14 vai usar:

3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
13. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
14. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. **Stage por caminho explícito.**
17. **O corpo do evento roda antes do `handleEvent`**, e o handler de estado dispara a cada evento
    cujo `nextstate` cai no estado — inclusive laços.
27. **Uma sonda com uma pergunta binária não é auditável**, e **uma sonda que mede zero precisa de
    um controle que meça diferente de zero, no mesmo carregador**. Corolário: uma sonda em que
    **tudo** mede 1, controle inclusive, também não distingue nada.
32. **O gate do INV-INS-130 conta menções em comentário e string, não só em código.**
38. **O `ErrorCollector` tem `reset()`**, mas `getErrors()` devolve um `Set` chaveado por
    `ErrorSummary`: relatos idênticos se fundem. Resete entre configurações — e resete os **dois**
    stores também. **E veja o achado 51: isso ainda não basta.**
43. **Não ponha comentário entre a linha do `ere`/`fsm` e o primeiro `@handler`.**
44. **Não reordene `codes.csv` nem `divergence_record.csv`.**
45. **`git diff` sem `--cached` compara com o índice, não com o HEAD.**
47. **"Escreva a trace primeiro" quer dizer antes da EDIÇÃO.**
49. **Uma linha aposentada pode se dividir entre dois hunks novos.** Registre a absorção nos dois.
    (E um hunk novo pode absorver duas aposentadas — a 4.13 teve os dois casos.)
51. **Dá para medir a árvore que você não tem** — escreva os corpos candidatos em linha na sonda,
    entre os dispatchers reais da árvore de partida.
52. **Uma trace nova tem de resolver em TRÊS snapshots**, não dois.
53. **`git diff --stat -- data/gh105/evidence/harness/`** é a asserção mais barata e mais forte de
    que a passagem não mexeu em mais nada.
54. **Antes de aceitar uma limitação do instrumento, meça-a** — e meça a sua **largura**
    (achado 47).
56. **`String.valueOf(Object)` de um `byte[]` é `[B@<hash>`.** Não deduza semântica de JDK da
    documentação: chame.
57. **Confira a simulação contra a árvore de verdade depois de editar.** Custa um comando e audita
    o aprendizado 51 em vez de confiar nele.
58. **Uma trace pode ligar o valor devolvido por uma chamada de instância** (`k.getEncoded() ->
    enc`), e `bind x = <chamada>` constrói o objeto **sem disparar advice nenhum** — que é como se
    monta o cenário de uma trace sem poluí-la de eventos.
60. **Quando um número do handoff discordar de um artefato, o artefato ganha.** E quando a
    **tarefa** discordar do `design.md`, o design ganha (achado 49).
