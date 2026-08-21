# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 36/74, a 4.12 tem duas janelas)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `5f64c8de`
**Progresso**: 36 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.11 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v14.md` (checkpoint 35/74).

> **A 4.12 também não começa editando.** O `SecretKeySpec.e1` é a última leitura em
> `condition(...)` do conjunto, e migrá-la **fecha uma cadeia e abre outra**: o produtor de
> `GENERATED_KEY` que já está no store novo é o `SecretKeySpecSpec` (4.10), mas os outros dois —
> `KeyGeneratorSpec.mop:80` e `KeyStoreSpec.mop:83` — só migram na 4.14. Isso é uma janela F2
> nova, e ela **não aparece em nenhum dos dois lados do harness** (achado 34). Meça as duas
> configurações na árvore de partida antes de tocar no arquivo. A seção "Próximo passo" tem a
> ordem exata.

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
**Seis** dessas passagens já fecharam elos ou janelas que o plano tinha roteado para depois, e
**duas** reverteram a instrução que a própria tarefa carregava.

---

## Regras de trabalho (não negociáveis)

**Siga `docs/WORKFLOW.md` rigorosamente.** Artefato OpenSpec **nunca** se edita com `Write`/`Edit`
direto — invoque a skill (`openspec-update-change`) pela ferramenta `Skill`. Ela **pede
confirmação antes de escrever cada artefato**, e isso não é formalidade: foi por ela que a sessão
do `946aad17` descobriu que o reparo tinha *dois* sítios, foi por ela que a 4.10 descobriu que a
5.6 não listava o quinto produtor, e foi por ela que a 4.11 emendou a regra de `propagation` do
`spec.md` em vez de dobrá-la em torno de um arquivo.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final. **Stage por caminho explícito, nunca `git add -A`**
— a árvore tem muita modificação pré-existente não relacionada (gh69, docs, experimentos).

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três, a 4.8 quatro, a 4.9 três mais duas, a 4.10 duas, a 4.11
duas; as trinta e uma foram levadas em opções com recomendação **e medição**, e as trinta e uma
recomendações foram ratificadas. Faça o mesmo — e leve **medição** junto com a opção, não só
argumento. Se a medição disser que duas opções são indistinguíveis, diga isso. Se a medição
**mata** uma opção, apresente a opção morta assim mesmo, com o número que a matou (na 4.11 foi a
gramática do JavaMOP que matou uma). E se a medição só existe depois de você **escrever o
instrumento** ou **as traces**, escreva-os primeiro e diga que são novos.

**O pesquisador contesta, e às vezes ele tem razão.** Na 4.11 a pergunta sobre a trace da rota
`int` voltou como *"como assim um parâmetro declarado Object não consegue receber Integer???"*.
Não era limitação legítima do harness, era defeito — e a investigação que a contestação forçou
virou reparo medido. Quando o pesquisador duvidar de uma limitação que você aceitou, **meça a
limitação** antes de defendê-la.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda (a chamada `ensure`, o evento, o
estado do autômato) antes de oferecer opções, e diga explicitamente o que **não** muda. A 4.8, a
4.10 e a 4.11 abriram com um parágrafo do que a tarefa move independentemente de qualquer decisão
e uma tabela de medições com a fonte de cada uma; as decisões saíram numa rodada só.

**Diga o custo por inteiro.** A 4.11 removeu um falso-negativo e **introduziu um falso-positivo**
sobre um programa honesto, e a evidência diz isso em tantas palavras, com as três coisas que
limitam o custo — duas delas medidas. Uma passagem que só conta o que melhorou não é evidência.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente. Ele aparece
legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado inteiro
(INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando acertar,
**diga que acertou e por que não conta**.

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

**A regra de `propagation` do `spec.md` foi emendada pela 4.11 e é o que a 4.12 vai usar.** Ela
tinha uma condição e agora tem duas: uma leitura que não traduz cláusula é `propagation` quando
**alimenta uma escrita** *e* essa escrita **carrega o predicado através**. O `SecretKeySpec.e1` é
o único sítio do conjunto que cumpre as duas, e o `spec.md` já diz por quê — leia isso antes de
abrir a 4.12.

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as dez evidências
que já existem, porque são as dez formas que uma passagem de arquivo pode ter:

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
| **`data/gh105/evidence/f2-RandomStringPassword.md` (4.11)** | **a que apaga porque a ESCRITA é insustentável, e que repara o instrumento no caminho** |

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
app sob teste. A 4.4 a 4.10 já se apoiaram nessa tolerância.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 a 4.10: ver os handoffs v12, v13 e v14

Em uma linha cada: **4.1+4.2** `CipherSpec`, o arquivo mais difícil (17/17 eventos, headroom
zero), `d71c8e64`; **4.3** a sonda de alcance em três camadas — *a change NÃO está bloqueada, o
Grupo 5 está liberado*, `4881b557`; **4.4** `IvParameterSpec`, `a9d8f2bd`; **4.5**
`SecureRandomSpec`, `a7e97294`; **4.6** `PBEKeySpecSpec`, `ba219f1a`; **4.7**
`PBEParameterSpecSpec`, `d64f3a40`; **4.8** `GCMParameterSpecSpec`, `5222a5d9`; **4.9** `MacSpec`,
`e86bd270` (apaga quatro sítios, o arquivo sai do grafo); **4.10** `SecretKeySpecSpec`,
`28cfa722` (fecha duas janelas invisíveis, e a aridade fica em 1 de propósito); e a sessão de
verificação `946aad17`, em que o parser do G-ORDER foi desmascarado sem reparo.

### 4.11 — `RandomStringPassword`, commit `5f64c8de` — a ponte que carregava a coisa errada

Evidência: **`data/gh105/evidence/f2-RandomStringPassword.md`** (297 linhas).

Segunda passagem a **reverter a instrução da própria tarefa**, e a segunda a tirar um arquivo
inteiro do `predicate_graph.csv` — por motivo diferente do `MacSpec`. As leituras do `MacSpec`
saíram por não alimentarem escrita; estas alimentam, e saem porque **a escrita é que é
insustentável**.

O arquivo é o único encanamento de dataflow do conjunto: existe para levar `randomized` por
`Object → String → char[]`, porque `PBEKeySpecSpec.c1` é a única leitura desse predicado sobre um
`char[]` e nada mais no conjunto produz um. Medido antes da edição, sobre os três tipos de fonte
que o conjunto consegue lhe entregar:

| fonte | `String.valueOf(Object)` devolve | carrega aleatoriedade? |
|---|---|---|
| `byte[]` (`nextBytes`, `generateSeed`) | `[B@726f3b58` — a string de identidade | **não** |
| o próprio `SecureRandom` | `SecureRandom` — uma constante | **não** |
| `Integer` (`nextInt`) | os próprios dígitos | **sim**, e é o que morre no store novo |

E o que decide o `Integer`: o `PredicateStore` chaveia o **vínculo** por identidade, então a caixa
da escrita e a caixa da leitura só são o mesmo objeto dentro do cache do `Integer` (−128..127) —
onde, para `nextInt(int)`, o valor marcado é o **argumento-limite**, não o resultado. Os dois
tipos que propagam não carregam aleatoriedade e o que carrega não propaga.

Medido em três árvores, `ErrorCollector` inteiro:

| configuração | pré-imagem | árvore de partida | migração fiel (corpos simulados) |
|---|---|---|---|
| rota `byte[]` → `PBEKeySpec` | **0 — silenciosa** | 1 — `PBEKEYSPEC-NOBS-00` | **0 — silenciosa de novo** |
| rota `Integer` fora do cache | 0 | 1 | 1 |
| rota `Integer` dentro do cache | 0 | 1 | 0 |
| controle: senha hard-coded | 0 | 1 | 1 |

A linha 1 da pré-imagem é o achado: um `PBEKeySpec` cuja senha é o `char[]` de `[B@6ae40994` —
onze caracteres de endereço de heap — é aceito como randomizado e não tira relato nenhum. Falso
negativo, vivo na semente congelada, e a migração fiel o restauraria.

O custo está dito por inteiro: a leitura de senha do `PBEKeySpecSpec.c1` nunca mais pode ser
satisfeita. Três coisas o limitam, duas medidas: (a) em relação à árvore nada muda, porque a ponte
já estava inerte; (b) em relação à migração fiel só a linha do `byte[]` difere; (c) a acusação não
tem cláusula por trás — a api30 exige `randomized[salt]` e o que diz da senha é
`neverTypeOf(password, java.lang.String)`.

**A passagem também reparou o instrumento** (ver decisão 31 e achado 39).

---

## Decisões ratificadas pelo pesquisador

**As decisões 1 a 25 estão no handoff v13 e as 26 a 29 no v14** — leia-as lá. As mais citadas:
**2** (escrita sem cláusula é apagada, não registrada), **7** (mudança comportamental sem medição
que a decida não entra em migração de substrato), **11** (a retirada vai com a escrita que ela
desfaz), **13** (a leitura sem cláusula também é de três valores), **16** (o registro de omissão
deliberada vem para a passagem do arquivo), **19** (código sem caminho de execução é apagado
quando mover criaria outro), **21** (o `@fail` inalcançável é registrado, não reparado), **28**
(a escrita move store e não move aridade).

### Na 4.11 (2026-08-21)

30. **Os quatro sítios do `RandomStringPassword` são APAGADOS, não migrados** — revertendo a
    instrução da tarefa, que mandava registrar as duas leituras como `propagation`. Registrar o
    par poria o nome do conjunto numa afirmação que a conversão não sustenta. A opção do meio —
    migrar com porta de tipo na escrita (`obj instanceof Number || obj instanceof CharSequence`),
    que mata os dois falsos-negativos — foi recusada por inventar uma condição que regra nenhuma
    enuncia, dentro de uma migração de substrato, para alimentar melhor uma leitura que também
    não tem cláusula.
31. **O reparo do `TraceRunner.fitsPointcut` entra na própria 4.11**, com teste novo, em vez de
    virar tarefa 7.x. O pesquisador escolheu isso depois de a investigação mostrar que o guard não
    protegia nada (ver achado 39). O harness é instrumento, não conjunto: o reparo não muda
    especificação nenhuma.

**Não foi decisão, foi a gramática**: apagar o `@match` vazio, como a 4.6 e a 4.9 fizeram, não
compila — `RVParser.propertyHandler` exige `"@"` depois do `ere`, e a geração falha com
`ParseException: Encountered "<EOF>"`. O handler vazio fica.

---

## Achados que valem mais que as tarefas

**Os achados 1 a 32 estão no handoff v13 e os 33 a 36 no v14.** Os mais operacionais:

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — registrado, não reparado; a família já tem cinco
   membros.
4. **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila** —
   e que não lança.
8. **Códigos sem caminho de execução**: catorze depois da 4.10.
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos**, e o veredito
    é **piso, não contagem**.
17. **Um evento inteiro pode não acusar nada, e o censo não mostra** — e, desde a 4.8, uma
    especificação inteira também.
29. **A mudez pode ser da especificação, não do evento.** Leia a tabela de transição no monitor
    gerado e pergunte quantos eventos um monitor pode receber.
32/33. **Uma guarda pode transformar um programa conforme num acusado — e também pode MASCARAR a
    acusação que o autômato faria.** Nenhum dos dois aparece num censo de colocação.
34. **Nenhum dos dois lados do harness contém uma janela F2.** A janela só existe nas árvores
    intermediárias por onde a migração passa.
35. **`PredicateStore.validate` compara a tupla de valores.** Aridade divergente devolve
    `VIOLATED`, não `NOT_OBSERVED`.
36. **O corpus publicado é anterior ao envelope v=1**; as linhas dele são mudas, então renumerar
    um código não custa nada fora da árvore.

### Novos, da 4.11

37. **Uma escrita de propagação pode ser insustentável sem que nada no arquivo o mostre.** A
    regra do `spec.md` dizia que uma leitura sem cláusula é `propagation` se **alimenta uma
    escrita**; faltava a segunda condição, que a escrita **carregue o predicado através**. O teste
    é barato e ninguém o tinha feito: chame a conversão de verdade, com cada tipo de fonte que os
    produtores do conjunto realmente emitem, e compare o que sai com o que o predicado afirma.
    `String.valueOf(SecureRandom)` devolve a constante `"SecureRandom"`; nenhum documento do
    projeto tinha isso escrito.
38. **O `PredicateStore` não é simétrico entre vínculo e valor.** O **vínculo** é identidade fraca
    (`BoundKey`, `System.identityHashCode`), então um `Integer` só casa dentro do cache; as
    **posições de valor** normalizam `String` e `Integer` para texto, então casam por conteúdo. O
    store velho (`ExecutionContext`) era um `HashSet` e usava `equals` para tudo. Isso significa
    que **a migração estreita silenciosamente o casamento de predicados sobre primitivos boxados**,
    e o único sítio afetado era esta ponte. Medido:

    ```
    store novo, mesmo array                    -> SATISFIED
    store novo, Integer igual fora do cache    -> NOT_OBSERVED
    store novo, Integer igual dentro do cache  -> SATISFIED
    store novo, String igual mas distinta      -> NOT_OBSERVED
    store velho, Integer igual fora do cache   -> true
    store velho, String igual mas distinta     -> true
    ```
39. **O `fitsPointcut` do `TraceRunner` recusava um `Integer` contra QUALQUER tipo de referência
    declarado**, antes da linha que de fato testa atribuibilidade. A justificativa da docstring —
    separar `initialize(int)` de `initialize(AlgorithmParameterSpec)` — já era decidida pela linha
    de baixo. A regra larga só mudava resultado onde o tipo declarado aceita um `Integer`
    (`Object`, `Number`, `Integer`, `Comparable`, `Serializable`), e das **112 advices** do
    conjunto **exatamente uma** declara um assim: o `String.valueOf(Object)` desta ponte. Medida a
    inércia antes de remover: **0 mudanças de resultado sobre as 92 traces nos dois lados**.
40. **O `TraceRunnerTest` está VERMELHO no HEAD, e já estava.** 2 falhas de 6:
    `everyTraceLineResolvesToAnAdvice` (8 linhas não resolvidas contra o snapshot congelado:
    `s.sign()` ×5, `ctx.createSSLEngine()`, `tmf.getTrustManagers()`, e as duas NPE do
    `KeyPairGeneratorSpec-sticky-fail`) e
    `theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect`. Verificado replicando o
    corpus com o `TraceRunner` do HEAD: idêntico. **Pertencem à porta de tipo de retorno do
    `bdc027a6` e à 8.5 do gh104, não a esta change** — não confunda com regressão sua, e não as
    repare dentro da gh105 sem levar ao pesquisador.

### Três defeitos de pipeline, fora do escopo desta change — relatório escrito, decisão pendente

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). D1: o caminho de experimento não fornece `ANDROID_SDK_HOME` e o
GATOR morre. D2: a análise estática mira `resources/jca` mesmo sob `--specification-set
jca_android` — **interage com o Grupo 5**. D3: o INV-EXP-16 não é aplicado.

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.**

Há ainda o **RISK-013 da gh69** (`openspec/changes/gh69-generic-subtype-target-matching/risk-register.md:565`),
que é sobre o **mesmo arquivo** e não é a mesma coisa: lá o defeito é de *análise estática* — o
`RandomStringPassword.mop` nomeia o owner `String` sem importar, contribui zero alvos estáticos e
o denominador de todo `cov_reaches_target` publicado saiu sobre 22 de 23 specs. O que a 4.11 mediu
é de *runtime*. Referencie um do outro, não os funda.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21, depois da 4.11)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **1** | 0 |
| leituras em corpo | 0 | **13** | todas |
| escritas em corpo de evento | 42 | **23** | 0 sem razão registrada |
| escritas no ponto de aceitação | 7 | **11** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **17** | 0 |
| `remove()` em `@fail` | 8 | 7 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 2 (falta `SecretKey: generatedKey after d`) |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **14** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **73** | — |
| achados dos gates estruturais | 71 (na 4.8) | **58** (G-PRED2 23, INV-INS-130 14, INV-INS-133 1, INV-INS-134 20) | 0 |
| hunks no `divergence_record.csv` | — | **206**, todos registrados | — |
| traces do corpus | 63 | **94**, todas commitadas | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 94 traces contra `backup/gh105-preimage/jca_android`: **61 inalteradas, 18
movidas, 9 introduzidas, 6 removidas** (cumulativas contra a pré-imagem). As 9 `introduced` são
reparos deliberados (quatro da 4.8, duas da 4.7, uma da 4.9, duas da 4.11).

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.12-4.14 são pré-change e estão desatualizados.** Esta tabela
saiu do `predicate_graph.csv` em 2026-08-21, depois da 4.11. Reconfira com `--emit` antes de citar
qualquer número numa evidência.

| arquivo | `read:condition` | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove`/`negate` | tarefa |
|---|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 0 | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 0 | 1 | 2 | 3 | 0 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 0 | 2 | 1 | 0 | 0 | 1 (`negate`) | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.7 |
| `GCMParameterSpecSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.8 |
| ~~`MacSpec.mop`~~ | — | — | — | — | — | — | ✅ 4.9 (**saiu do grafo**) |
| `SecretKeySpecSpec.mop` | 0 | 1 | 0 | 1 | 0 | 0 | ✅ 4.10 |
| ~~`RandomStringPassword.mop`~~ | — | — | — | — | — | — | ✅ 4.11 (**saiu do grafo**) |
| **`SecretKeySpec.mop`** | **1** | 0 | **1** | 0 | 0 | 0 | **4.12** |
| `SignatureSpec.mop` | 0 | 0 | 4 | 0 | 1 | 0 | 4.13 |
| `MessageDigestSpec.mop` | 0 | 0 | 3 | 0 | 2 | 0 | 4.13 |
| `SSLContextSpec.mop` | 0 | 0 | 2 | 0 | 2 | 0 | 4.13 |
| `KeyPairSpec.mop` | 0 | 0 | 2 | 0 | 1 | 0 | 4.13 |
| `KeyStoreSpec.mop` | 0 | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyManagerFactorySpec.mop` | 0 | 0 | 2 | 0 | 2 | 1 | 4.14 |
| `TrustManagerFactorySpec.mop` | 0 | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyGeneratorSpec.mop` | 0 | 0 | 1 | 0 | 2 | 1 | 4.14 |
| `KeyPairGeneratorSpec.mop` | 0 | 0 | 1 | 0 | 1 | 1 | 4.14 |
| `DHGenParameterSpecSpec.mop` | 0 | 0 | 0 | 1 | 1 | 0 | 4.14 |
| `HMACParameterSpecSpec.mop` | 0 | 0 | 0 | 1 | 1 | 0 | 4.14 |

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

## Próximo passo: 4.12 — `SecretKeySpec` — **MEÇA AS DUAS JANELAS ANTES DE EDITAR**

### O que este arquivo é

```java
SecretKeySpecSpec(SecretKey secretKey) {              // arquivo: SecretKeySpec.mop
   event e1 after(SecretKey secretKey) returning(byte[] key):
      call(public byte[] SecretKey.getEncoded()) && target(secretKey) &&
      condition(ExecutionContext.instance().validate(Property.GENERATED_KEY, secretKey)) {
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, key);
   }
   ere : e1*
   @match {
     // __RESET;
   }
}
```

**A última leitura em `condition(...)` do conjunto.** Depois dela o INV-INS-133 vai a **0** e o
INV-INS-130 a **13**.

### A regra existe, e diz mais do que a tarefa supõe

`api30/SecretKey.cryptsl` — **leia antes de tudo**:

```
EVENTS     d: destroy();   ge: keyMaterial = getEncoded();
ORDER      ge*, d?
ENSURES    preparedKeyMaterial[keyMaterial] after ge;
NEGATES    generatedKey[this, _] after d;
```

Três coisas caem daí, e nenhuma está no texto da 4.12:

1. **A escrita deveria ser `preparedKeyMaterial`, não `RANDOMIZED`.** É a mesma confusão do ledger
   **#32** que a leitura do `SecretKeySpecSpec.c1` carrega, desfeita na 5.10 junto com a 6.1.
   Registre aqui, não repare (precedente literal: a 4.10 fez exatamente isso).
2. **A cláusula tem `after ge`**, então há ponto de aceitação a considerar (achado 20). O `ere` é
   `e1*`, e o alias único do ERE é `match` sobre os estados de aceitação — confira o que isso
   nomeia aqui antes de decidir onde a escrita fica.
3. **O `NEGATES generatedKey[this,_] after d` não tem sítio nenhum**, e é a **segunda** das duas
   cláusulas `NEGATES` do oráculo (INV-INS-142); a primeira, `speccedKey after cP`, a 4.6 fez. O
   arquivo não declara evento para `destroy()`. Isso é uma decisão a levar ao pesquisador: criar o
   evento e o `negate`, ou registrar a omissão (INV-INS-137).

### A janela F2, que é o motivo de medir antes

A leitura do `e1` é de `GENERATED_KEY`. Quem escreve `GENERATED_KEY` hoje:

| produtor | store | tarefa |
|---|---|---|
| `SecretKeySpecSpec.mop:153` | **novo** (`PredicateStore`) | ✅ 4.10 |
| `KeyGeneratorSpec.mop:80` | **velho** (`ExecutionContext`) | 4.14 |
| `KeyStoreSpec.mop:83` | **velho** (`ExecutionContext`) | 4.14 |

Migrar a leitura **fecha** a cadeia `SecretKeySpecSpec → SecretKeySpec` e **abre** uma janela
contra os outros dois até a 4.14. Além disso a leitura governa uma escrita, então a janela se
propaga: uma chave gerada por `KeyGenerator` deixa de marcar `RANDOMIZED` sobre os bytes que ela
devolve, e quem lê `RANDOMIZED` sobre `byte[]` são sete sítios.

**Meça as três configurações na árvore de partida, com sonda sobre o `ErrorCollector` inteiro,
antes de editar** (achado 34 + aprendizado 47):

1. `KeyGenerator.generateKey()` → `key.getEncoded()` → um consumidor de `randomized` sobre
   `byte[]` (o `IvParameterSpec.c1` é o mais barato). Quanto acusa hoje? E depois?
2. `new SecretKeySpec(km,"AES")` → `key.getEncoded()` → o mesmo consumidor. Esta é a que **fecha**.
3. O controle: um `byte[]` de origem nenhuma no mesmo consumidor (tem de medir diferente de zero —
   aprendizado 27).

E veja se o corpus tem trace disso: `data/gh104/traces/SecretKeySpec.txt` existe, mas confira o
que ele exercita. Se não exercitar a cadeia, **escreva a trace antes da edição**.

### As decisões que dá para antecipar

- **A leitura vira de três valores sem acusador?** Decisão 13 diz que sim. Confirme, e diga o que
  acontece com `NOT_OBSERVED` quando a leitura **governa uma escrita** — o corpo vira
  `if (verdict == SATISFIED) { escreve }`, e `NOT_OBSERVED` e `VIOLATED` se comportam igual.
- **Onde fica a escrita**, dado o `after ge` e o `ere : e1*`.
- **O `NEGATES` sem sítio**: criar ou registrar a omissão.
- **A confusão `RANDOMIZED` × `preparedKeyMaterial`**: registrar (ledger #32, 5.10+6.1), não
  reparar. Isto é quase certo, mas formule.
- **O `@match` com o `// __RESET;` comentado**: é bookkeeping? O censo diz 0 bookkeeping para este
  arquivo. Se o handler ficar sem nada, lembre da 4.11 — **a gramática exige um handler**, então
  ele fica vazio, não some.

### Depois da 4.12

4.13 e 4.14 (só escritas). A 4.15 fecha o grupo (gates de colocação verdes, baselines aposentadas
pelo bloco `retired`) e a 4.16 roda `/rv-test-run tests/parity`. Só então o Grupo 5, que a 4.3
liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.11)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20). **E confira
   a aridade da cláusula contra a aridade da `Property`.** **Se não houver regra**, diga isso e
   diga o que o arquivo então é.
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   Se o corpus não tiver trace do sítio, **escreva a trace e meça a semente — antes da edição**
   (achado 18 + 34 + aprendizado 47). E **audite a sonda**: rode um controle que sabidamente acusa
   no mesmo carregador de classes, e liste os dispatchers que ela encontrou.
   **E, quando a passagem tiver mais de uma disposição possível, simule a alternativa** — a 4.11
   comparou três árvores tendo só duas, rodando os corpos migrados em linha entre os dispatchers
   da árvore de partida (aprendizado 51).
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string. **E não ponha comentário entre o `ere` e o primeiro `@`** (aprendizado 43).
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. **Preserve a ordem do arquivo** (aprendizado 44).
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato, as linhas ficam como estão
   — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade. **Fora da janela, meça o lado satisfaz de
   verdade.** **Confira que a trace replica inteira** (`unresolved: []`) antes de commitá-la, nos
   dois lados **e** contra o snapshot congelado, porque o `TraceRunnerTest` replica contra ele
   (aprendizado 52).
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas — e **reconferir o
   round-trip depois de preencher** (aprendizado 34).
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo, com
   a coluna `task` acumulando. O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
   **Anexe as linhas novas no fim, na ordem do arquivo `.mop`, e não reordene o resto**
   (aprendizado 44). **Chaveie por `(file, hunk)`, nunca só por `hunk`** (aprendizado 45).
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class` — **e lembrar que é piso, não contagem**.
   **`git diff --stat data/gh105/evidence/harness/` é a medida mais forte de "não mexi em mais
   nada"**: na 4.11 só um relatório dos 23 mudou (aprendizado 53).
10. Conferir e reescrever a baseline (`--write`); ela preserva `retired`.
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também.** São
    **três** censos e eles não estão juntos: o do conjunto (`read_placement["condition"]`,
    `accepting-state`), o do grafo (`read:condition-guard`, `read:body`, `bookkeeping`) e o do
    gate de colocação (`len(guards)`).
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md`.
13. Rodar as quatro suítes. Commitar (stage por caminho explícito). Marcar o checkbox.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (`getErrors()` devolve um
  `Set`; `reset()` existe)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (a gramática das traces;
  **`fitsPointcut` reparado pela 4.11**) e `TraceRunnerTest.java` (**2 falhas pré-existentes no
  HEAD — achado 40**)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)
- Gramáticas: `rv-monitor/rv-monitor/src/main/javacc/.../logicpluginshells/fsm/parser/FSMParser.jj`
  (o `alias`), `rv-monitor/plugins_logicrepository/ere/.../FSM.java:85` (o alias único do ERE),
  `rv-monitor/rv-monitor/src/main/java/.../logicpluginshells/fsm/JavaFSM.java:160` (alias → categoria),
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
  `constraint_table.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (**94, todas commitadas**), `data/gh104/baseline.md` (o corpus publicado)
- `results/gh101_group8_jca_frozen_control/monitors/` (o snapshot contra o qual o
  `TraceRunnerTest` replica — uma trace nova tem de resolver **aqui também**)
- `data/gh105/evidence/`: as dez evidências de passagem, `f1-group-three-the-seventeen.md`,
  `f1-order-gate-precedence.md`, `reach-probe/`, `f1-*-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`
— para a 4.12, **`SecretKey.cryptsl` existe e tem ENSURES e NEGATES**.

**Gramática do CrySL (somente leitura)**:
`/home/pedro/tmp/CryptSL/de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext`
— o `ORDER` está em :99-134. **É a fonte que decide qualquer dúvida de precedência.**

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 94 passando, ~100 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI (--json dá as contagens por gate)
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit

# lint e gate de mensagens do gh104 (os dois quebram com facilidade numa migração)
uv run python scripts/gh104_mop_lint.py $SPECS/jca_android
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# os gates estruturais sobre um monitor já gerado (G-ERE, G-6', G-CONF)
M=$(ls -dt ~/tmp-gh104/gh104-harness-* | head -1)/b/monitors/MultiSpec_1RuntimeMonitor.java
uv run python scripts/gh104_gates.py --monitor $M \
    --allowlist data/jca_android/gate_allowlist.csv \
    --crysl /home/pedro/.../MetaCrySL/generated/api30 \
    --alias data/jca_android/alias_table.csv \
    --constraint-table data/jca_android/constraint_table.csv

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android
# ATENÇÃO: para uma regra cujo ORDER tem `,` e `|` no mesmo nível de parênteses (só a Cipher),
# `parse_expression` responde sob o parse ERRADO. Use o bloco de reprodução de
# data/gh105/evidence/f1-order-gate-precedence.md. Reparo na 7.1.

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

# replicar UMA trace nova antes de commitá-la (os dois lados + o snapshot congelado)
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
TC=$RVSEC_HOME/rvsec/rvsec-mop/target/test-classes
java -cp "$TC:$CP" br.unb.cic.mop.harness.TraceRunner <monitorDir> <tracesDir> <workDir> <out.json>
#   monitorDir: <scratch>/{a,b}/monitors  e  results/gh101_group8_jca_frozen_control/monitors

# sonda de contagem sobre o ErrorCollector inteiro (receitas completas nas evidências 4.7-4.11)
javac -nowarn -cp "$CP" -d <dir> Probe.java
java -cp "<dir>:$CP:<scratch>/<lado>/work/classes/classes" Probe <rótulo>

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

**Os aprendizados 1 a 46 estão no handoff v13 e os 47 a 50 no v14.** Os que a 4.12 vai usar:

3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
13. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
14. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. **Stage por caminho explícito.**
17. **O corpo do evento roda antes do `handleEvent`**, e o handler de estado dispara a cada evento
    cujo `nextstate` cai no estado — inclusive laços.
27. **Uma sonda com uma pergunta binária não é auditável**, e **uma sonda que mede zero precisa de
    um controle que meça diferente de zero, no mesmo carregador**. Corolário da 4.11: uma sonda em
    que **tudo** mede 1, controle inclusive, também não distingue nada — arranje a configuração
    que mede 0.
32. **O gate do INV-INS-130 conta menções em comentário e string, não só em código.**
35. **`condition(...)` é compilado para dentro do `Prop_N_event_X`** e vira
    `if (!(guarda)) return false;` **antes** do `handleEvent`.
37. **A sonda de contagem tem de chamar todos os dispatchers da aridade certa.**
38. **O `ErrorCollector` tem `reset()`**, mas `getErrors()` devolve um `Set` chaveado por
    `ErrorSummary`: relatos idênticos se fundem. Resete entre configurações.
39. **O `ErrorDescription` carrega o envelope em `getExpecting()`**, não em `toString()`.
40. **Uma trace precisa de objetos ligados em silêncio** (`bind x = new ...`) quando o construtor
    dispararia eventos de outra especificação no envelope desta.
43. **Não ponha comentário entre a linha do `ere` e o primeiro `@handler`.**
44. **Não reordene `codes.csv` nem `divergence_record.csv`.**
45. **`git diff` sem `--cached` compara com o índice, não com o HEAD.**
47. **"Escreva a trace primeiro" quer dizer antes da EDIÇÃO.**
49. **Uma linha aposentada pode se dividir entre dois hunks novos.** Registre a absorção nos dois.

### Novos, da 4.11

51. **Dá para medir a árvore que você não tem.** Para comparar "o que a migração fiel faria" com
    "o que a deleção faz", sem editar nem gerar duas vezes: escreva os corpos migrados em linha na
    sonda (`validate` → `if SATISFIED then ensure`, no store novo) **entre os dispatchers reais da
    árvore de partida**. Tudo o mais no encadeamento continua sendo o código da árvore. Foi assim
    que a 4.11 pôs três colunas numa tabela tendo duas árvores.
52. **Uma trace nova tem de resolver em TRÊS snapshots**, não dois: os lados `a` e `b` do harness
    **e** o controle congelado `results/gh101_group8_jca_frozen_control/monitors`, porque é contra
    ele que o `everyTraceLineResolvesToAnAdvice` replica. Uma trace que só resolve nos dois
    primeiros deixa a suíte JUnit pior.
53. **`git diff --stat -- data/gh105/evidence/harness/`** é a asserção mais barata e mais forte de
    que a passagem não mexeu em mais nada: se só o relatório do arquivo da tarefa mudou, acabou a
    discussão. Ponha o resultado na evidência.
54. **Antes de aceitar uma limitação do instrumento, meça-a.** O guard do `fitsPointcut` parecia
    defensável e tinha docstring explicando por quê. Bastaram duas medições — quantos pointcuts do
    conjunto declaram um tipo que aceita `Integer` (um, de 112) e quantos resultados o guard muda
    sobre o corpus (zero, nos dois lados) — para virar reparo de três linhas.
55. **Uma opção pode ser morta pela gramática do gerador, e isso é uma medição.** Copie o conjunto
    para um scratch, aplique a variante, rode `uv run rv-monitor-generator generate --specs-dir
    <dir> --output <dir>` e leia o `exit`. Custa ~40 s e fecha a discussão com um `ParseException`
    em vez de um argumento.
56. **`String.valueOf(Object)` de um `byte[]` é `[B@<hash>`, e de um `SecureRandom` é a constante
    `"SecureRandom"`.** Não deduza semântica de JDK da documentação: chame.
