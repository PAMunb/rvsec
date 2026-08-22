# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 39/74, o Grupo 4 chega ao fim das migrações)

**Data**: 2026-08-22 · **Branch**: `modules` · **Último commit**: `1fa22acb`
**Progresso**: 39 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.14 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260822_gh105_apply_prompt_v17.md` (checkpoint 38/74).

> **A 4.14 migrou os sete últimos arquivos e levou três contadores a zero**: as chamadas de
> estado de aceitação (INV-INS-147, 11 → 0), as menções ao substrato velho (INV-INS-130,
> 9 arquivos → 0) e os `remove()` em `@fail` (7 → 0). **Não há mais nenhum arquivo do conjunto
> `jca_android` para migrar.** O que resta da 4.x são a 4.15 (gates de colocação e baselines) e
> a 4.16 (`/rv-test-run tests/parity`) — duas tarefas de conferência, não de edição. Leia a
> seção "Próximo passo" antes de abrir qualquer arquivo.

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
chega ao dispositivo e liberou o Grupo 5; o Grupo 4 migrou o conjunto arquivo por arquivo e
**terminou**. **Oito** dessas passagens fecharam elos ou janelas que o plano tinha roteado para
depois, **três** reverteram a instrução que a própria tarefa carregava, e **duas** repararam o
instrumento no caminho.

---

## Regras de trabalho (não negociáveis)

**Siga `docs/WORKFLOW.md` rigorosamente.** Artefato OpenSpec **nunca** se edita com `Write`/`Edit`
direto — invoque a skill (`openspec-update-change`) pela ferramenta `Skill`. Ela **pede
confirmação antes de escrever cada artefato**, e isso não é formalidade: foi por ela que a sessão
do `946aad17` descobriu que o reparo tinha *dois* sítios, que a 4.10 descobriu que a 5.6 não
listava o quinto produtor, que a 4.11 emendou a regra de `propagation` do `spec.md` em vez de
dobrá-la em torno de um arquivo, que a 4.12 descobriu que uma frase do `spec.md` tinha acabado de
virar falsa, que a 4.13 descobriu que o censo escrito na **própria tarefa** estava errado, e que
a 4.14 emendou o INV-INS-142 e transformou a 6.4 em tarefa de verificação.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final. **Stage por caminho explícito, nunca `git add -A`**
— a árvore tem muita modificação pré-existente não relacionada (gh69, docs, experimentos, e onze
`data/gh104/evidence/harness/selftest*.md` modificados que **não são seus**).

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três, a 4.8 quatro, a 4.9 três mais duas, a 4.10 duas, a 4.11
duas, a 4.12 três, a 4.13 cinco, a 4.14 **seis** (em duas rodadas); as quarenta e cinco foram
levadas em opções com recomendação **e medição**, e as quarenta e cinco recomendações foram
ratificadas. Faça o mesmo — e leve **medição** junto com a opção, não só argumento. Se a medição
disser que duas opções são indistinguíveis, diga isso *e diga onde elas deixam de ser*.

**O pesquisador contesta, e às vezes ele tem razão.** Na 4.11 a pergunta sobre a trace da rota
`int` voltou como *"como assim um parâmetro declarado Object não consegue receber Integer???"*.
Não era limitação legítima do harness, era defeito. Quando o pesquisador duvidar de uma limitação
que você aceitou, **meça a limitação** antes de defendê-la. A 4.13 e a 4.14 aplicaram isso
sozinhas: na 4.13 o harness "não conseguia" produzir um `KeyPair` e a limitação era um defeito de
três linhas; na 4.14 ele "não conseguia" tirar uma chave real de um `KeyStore`, e a limitação era
a gramática das traces, não a plataforma.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda antes de oferecer opções, e diga
explicitamente o que **não** muda. A 4.14 abriu com a tabela dos pontos de aceitação lidos do
monitor gerado, a tabela de quem lê cada escrita, e a tabela da sonda — as seis decisões saíram
em duas rodadas, quatro na primeira e duas na segunda.

**Diga o custo por inteiro.** A 4.11 removeu um falso-negativo e introduziu um falso-positivo. A
4.12 fechou uma cadeia e abriu uma janela, e mediu que a janela não custa relato nenhum. A 4.13
manteve duas escritas fora do ponto de aceitação e declarou o que isso custa. A 4.14 manteve
outras duas e declarou o mesmo: depois de um `gkm`/`gtm` — chamada que a *regra* aceita e o
*autômato* recusa — a escrita no corpo marca um objeto que o autômato não aceitou.

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

E, além dos artefatos, **as treze evidências de passagem** — que são as treze formas que uma
passagem pode ter:

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
| `data/gh105/evidence/f2-write-only-batch-a.md` (4.13) | a de quatro arquivos, sem leitura nenhuma |
| **`data/gh105/evidence/f2-write-only-batch-b.md`** (4.14) | **a de sete arquivos que zera três contadores e paga a dívida de uma passagem anterior** |

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
app sob teste. A 4.4 a 4.14 já se apoiaram nessa tolerância.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 a 4.13: ver os handoffs v12 a v17

Em uma linha cada: **4.1+4.2** `CipherSpec`, o arquivo mais difícil (17/17 eventos, headroom
zero), `d71c8e64`; **4.3** a sonda de alcance em três camadas — *a change NÃO está bloqueada, o
Grupo 5 está liberado*, `4881b557`; **4.4** `IvParameterSpec`, `a9d8f2bd`; **4.5**
`SecureRandomSpec`, `a7e97294`; **4.6** `PBEKeySpecSpec`, `ba219f1a`; **4.7**
`PBEParameterSpecSpec`, `d64f3a40`; **4.8** `GCMParameterSpecSpec`, `5222a5d9`; **4.9** `MacSpec`,
`e86bd270` (apaga quatro sítios, o arquivo sai do grafo); **4.10** `SecretKeySpecSpec`,
`28cfa722`; **4.11** `RandomStringPassword`, `5f64c8de` (apaga os quatro sítios e repara o
`fitsPointcut`); **4.12** `SecretKeySpec`, `fbd861c6` (a última guarda; INV-INS-133 vai a zero);
**4.13** as quatro só de escrita, `bd25a3aa`; e a sessão de verificação `946aad17`, em que o
parser do G-ORDER foi desmascarado sem reparo.

### 4.14 — as sete da batelada B, commit `1fa22acb`

Evidência: **`data/gh105/evidence/f2-write-only-batch-b.md`** (246 linhas).
Arquivos: `KeyStoreSpec`, `KeyGeneratorSpec`, `KeyManagerFactorySpec`, `TrustManagerFactorySpec`,
`KeyPairGeneratorSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec` — mais os dois imports
pendurados de `CipherInputStreamSpec` e `CipherOutputStreamSpec`.

Como a 4.13, nenhuma leitura nos arquivos; ao contrário da 4.13, quase toda escrita tem leitor.
Oito das dez escritas ao ponto de aceitação; duas no corpo com razão registrada. **A janela que a
4.12 abriu fechou nos dois produtores.**

A tabela que decidiu a passagem (sonda sobre o `ErrorCollector` inteiro, **um processo por
configuração**):

| configuração | partida | corpo | `@match` |
|---|---|---|---|
| **A** `KeyGenerator.generateKey` → `getEncoded` → `IvParameterSpec` | 1 | **0** | **0** |
| **A2** A mais um segundo `generateKey()` (regra e autômato rejeitam) | 2 | **1** | **2** |
| **B** `KeyStore.getKey` → `getEncoded` → `IvParameterSpec` | 1 | **0** | **0** |
| **C** controle: chave sem origem observada | 1 | 1 | 1 |
| **D** controle: produtor já no store novo (4.10) | 0 | 0 | 0 |
| **F** `KeyManagerFactory` — o que a 5.9 vai ler em `[kms]` | `NOT_OBSERVED` | `SATISFIED` | **`NOT_OBSERVED`** |

**Seis decisões ratificadas** (ver "Decisões", #40 a #45).

---

## Decisões ratificadas pelo pesquisador

**As decisões 1 a 25 estão no handoff v13, as 26 a 29 no v14, as 30 e 31 no v15, as 32 a 34 no
v16 e as 35 a 39 no v17** — leia-as lá. As mais citadas: **2** (escrita sem cláusula é apagada,
não registrada), **7** (mudança comportamental sem medição que a decida não entra em migração de
substrato), **11** (a retirada vai com a escrita que ela desfaz), **13** (a leitura sem cláusula
também é de três valores), **16** (o registro de omissão deliberada vem para a passagem do
arquivo), **19** (código sem caminho de execução é apagado quando mover criaria outro), **21** (o
`@fail` inalcançável é registrado, não reparado), **28** (a escrita move store e não move
aridade), **35** (a escrita fica no corpo quando o ponto de aceitação é inalcançável na rota
comum), **36** (o `gpr` passa a escrever o predicado que a cláusula nomeia).

### Na 4.14 (2026-08-22)

40. **As sete remoções em `@fail` saem na 4.14, não na 6.4.** O critério é o da decisão 11 — a
    retirada viaja com a escrita que ela desfaz — que a 4.6 e a 4.9 já usaram, e três medições o
    decidiram em vez do precedente sozinho: o `PredicateStore` **não oferece remoção nenhuma**
    (o INV-INS-131 lhe proíbe o `remove(Property)` cego ao objeto que o store velho tinha), então
    elas não podem migrar; deixadas, viram no-ops sobre um store que nada escreve, porque o
    INV-INS-133 está em zero e os dois leitores de `GENERATED_KEY` estão no `PredicateStore` —
    **nenhum leitor de predicado sobrou no substrato velho em `jca_android`** —, o que é código
    morto (P3); e o INV-INS-130 exige zero menções a `ExecutionContext`, conferido com `-w`, de
    modo que deixá-las manteria sete arquivos fora do zero e impediria a 4.15 de fechar antes da
    6.4. **A 6.4 e o INV-INS-142 foram emendados pela skill**: a 6.4 vira tarefa de verificação,
    a forma que a 6.5 já tem para a 4.6 e a 4.9.
41. **Oito escritas ao ponto de aceitação, duas no corpo com razão registrada.** As duas são
    `KeyManagerFactorySpec.gkm1` e `TrustManagerFactorySpec.gtm1`, cujas linhas de transição
    (`{3,3,0,3}` e `{3,0,3,3}`) saem do estado de aceitação para o `start`: ali a escrita no
    `@match` não é pior, ela **não acontece** — coluna F. Nas outras oito o padrão do INV-INS-134
    é mantido, e a linha **A2** é a razão: o ponto de aceitação é alcançável na rota comum, e o
    único programa que as duas colocações separam é um que a regra rejeita. **Custo declarado**:
    depois de um `gkm`/`gtm`, chamada que a regra aceita e o autômato recusa, a escrita no corpo
    marca um objeto que o autômato não aceitou. As duas vão para o `@match` quando a 7.1 entrar.
42. **O `gtm1` passa a escrever `GENERATED_TRUST_MANAGER`**, que é o que
    `generatedTrustManager[tms]` nomeia, no lugar do `GENERATED_KEY_MANAGERS` da regra vizinha
    (o javadoc do arquivo carregava a mesma cópia e foi corrigido junto). Forma da decisão 36. A
    5.9 roda **antes** da 6.2, então mediria o ledger #29 contra um produtor sabidamente errado.
    Custo medido: zero por dois motivos independentes — nada no conjunto lê as duas Property, e
    **o advice não tem caminho de execução nenhum**: o pointcut declara `getTrustManagers()`
    devolvendo `KeyManager[]` onde a API devolve `TrustManager[]`, e o harness mostra
    `tmf.getTrustManagers()` sem pointcut resolvido. É o gh104 8.7, já no
    `conformance_record.csv`, e a 6.2 é dona.
43. **Os dois imports pendurados de `CipherInputStreamSpec` e `CipherOutputStreamSpec` saem
    aqui.** Uma menção cada, no import, com zero usos. Nenhuma tarefa do Grupo 4 os cobria e a
    4.15 exige o INV-INS-130 verde; apagar import morto não pode mudar comportamento, e com eles
    o invariante chega a **zero no conjunto inteiro**.
44. **Três registros de omissão, por sítio**: o `generatedKeypair` do `KeyPairGeneratorSpec.gen`
    e as duas metades `[this] after Init` de `generatedKeyManager` e `generatedTrustManager`, que
    o oráculo ensura sobre a fábrica e que regra nenhuma pede ali. Os irmãos `[kms]`/`[tms]` têm
    leitor marcado para a 5.9 e não levam registro. O inventário é de **sítios**, e por isso o
    registro é por sítio ainda que o predicado ganhe consumidor.
45. **A divergência de ordenação do `KeyManagerFactorySpec` é alimentada à 7.1**, e não reparada
    aqui nem duplicada no catálogo do gh104. Ver "Achados", 53.

---

## Achados que valem mais que as tarefas

**Os achados 1 a 32 estão no v13, os 33 a 36 no v14, os 37 a 40 no v15, os 41 a 46 no v16 e os
47 a 52 no v17.** Os mais operacionais:

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — registrado, não reparado; a família tem cinco membros.
4. **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila** — e que não lança.
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos**, e o veredito é **piso, não contagem**.
17. **Um evento inteiro pode não acusar nada, e o censo não mostra** — e, desde a 4.8, uma especificação inteira também.
29. **A mudez pode ser da especificação, não do evento.** Leia a tabela de transição no monitor gerado.
35. **`PredicateStore.validate` compara a tupla de valores.** Aridade divergente devolve `VIOLATED`, não `NOT_OBSERVED`.
38. **O `PredicateStore` não é simétrico entre vínculo e valor.** O vínculo é identidade fraca; as posições de valor normalizam `String` e `Integer` para texto.
40. **O `TraceRunnerTest` está VERMELHO no HEAD, e já estava.** 2 falhas de 6 — **não são regressão sua**, e não as repare dentro da gh105 sem levar ao pesquisador.
41. **Uma janela F2 pode não custar relato nenhum, e só a medição diz qual é o caso.**
42. **A tabela de transição decide onde a escrita vai, e às vezes as duas rotas coincidem.** Custa um `awk`. Na 4.14 coincidiram **três vezes**, nas três cláusulas com `after L`.
43. **Um handler não vê parâmetro de evento.** Toda escrita no ponto de aceitação sobre um valor que só o evento conhece precisa de um campo de estágio, limpo ao ser consumido.
46. **Uma linha `unchanged` do harness pode ser exatamente a que mede o ganho.** Diga contra o que ela é `unchanged`.
47. **Antes de aceitar uma limitação do instrumento, meça a sua LARGURA, não só a sua existência.**
48. **Uma escrita pode ser relocada para cima de um evento que nunca dispara, e isso é correto.**
51. **`ExecutionContext.reset()` não zera o conjunto de monitores.** Um processo por configuração.
52. **O harness pode casar um pointcut a mais quando um argumento é `null`.**

### Novos, da 4.14

53. **Um gate que pula um arquivo declaradamente não é um gate verde sobre ele, e a diferença
    esconde defeito.** `g1 init gkm1` é **aceito** pelo ORDER api30 (`Gets, Init, gkm?`) e
    **rejeitado** pelo `fsm` do `KeyManagerFactorySpec`, cuja linha `gkm1 {3,3,0,3}` sai do
    estado de aceitação (2) para o `start` (0). É o espelho exato da divergência `g1 i1 gtm` que
    o G-ORDER já relata contra o `TrustManagerFactorySpec` — e o gate não a vê porque o arquivo
    não tem linhas no `order_alphabet_map.csv` e sai `skipped … G-ORDER never infers one`. Li o
    `conformance_record.csv` antes de chamá-la de nova: as três linhas do arquivo são sobre a
    allow-list, a constante `neverTypeOf` diferida e o reparo guard-on-field da 8.16. **Quando
    uma medição sua depender de um gate, confira se o gate roda sobre aquele arquivo.**
54. **Uma linha do harness sem `->` despacha os advices e NÃO executa a chamada.** Foi isso, e
    não a plataforma, que impediu a trace do `KeyStore` de produzir uma chave: `ks.load(null)`
    nunca inicializava o store, então `setKeyEntry` lançava e `produce()` engolia a exceção
    (`catch (Exception ignored)`), deixando o vínculo `null` em silêncio — o achado 47 de novo,
    em outro sítio. O padrão que funciona é fazer a chamada de efeito por uma linha `bind` e o
    despacho por uma linha simples, ainda que isso faça a mesma chamada aparecer duas vezes.
    **Medido antes de aceitar**: `PKCS12` e `JCEKS` aceitam `SecretKey` por `setKeyEntry` e
    devolvem um `javax.crypto.spec.SecretKeySpec` real; `JKS` recusa (`Cannot store
    non-PrivateKeys`); `BKS` e `AndroidKeyStore` não existem fora do Android.
55. **A mesma tabela pode decidir ao contrário em duas passagens seguidas, e isso não é
    inconsistência.** A linha A2 da 4.13 mandou a escrita para o corpo; a linha A2 da 4.14
    manteve-a no ponto de aceitação. A diferença é onde o ponto de aceitação está: lá ele era
    inalcançável na **rota comum**, aqui é alcançável, e o programa que as colocações separam é
    um que a regra rejeita — onde o relato a mais é verdadeiro pela semântica CrySL. **Pergunte
    sempre se a rota que a colocação prejudica é conforme ou não.**
56. **Um teste de fixture pode passar por vacuidade quando a árvore melhora.** O
    `test_the_placement_gate_accepts_a_write_that_records_why_it_stays` adicionava uma razão a
    uma linha `write:body` e exigia um achado a menos; depois da 4.14 todas as linhas já têm
    razão e ele comparava zero com zero. Reparado para **tirar** a razão e devolvê-la, que mede a
    direção nos dois sentidos. **Quando um contador chega a zero, releia os testes que o
    subtraem.**
57. **O `codes.csv` tem uma âncora vencida que não é sua.** `GCMPARAMETERSPEC-ORDER-00` aponta
    para `GCMParameterSpecSpec.mop:136`, que é comentário; o `addError` está em `:142`. Está
    assim no `HEAD` e o arquivo não foi tocado pela 4.14. **A 7.2 é dona.** Confira as âncoras
    que você mover, uma a uma, contra a árvore — é um laço de cinco linhas em Python.

### Três defeitos de pipeline, fora do escopo desta change — relatório escrito, decisão pendente

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). D1: o caminho de experimento não fornece `ANDROID_SDK_HOME` e o
GATOR morre. D2: a análise estática mira `resources/jca` mesmo sob `--specification-set
jca_android` — **interage com o Grupo 5**. D3: o INV-EXP-16 não é aplicado.

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.**

Há ainda o **RISK-013 da gh69** (`openspec/changes/gh69-generic-subtype-target-matching/risk-register.md:565`),
que é sobre o `RandomStringPassword.mop` e é defeito de *análise estática*, não de runtime.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-22, depois da 4.14)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **0** ✅ | 0 |
| leituras em corpo | 0 | **14** | todas |
| escritas em corpo de evento (grafo) | 42 | **7** | 0 sem razão registrada ✅ |
| escritas no ponto de aceitação (grafo) | 7 | **23** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **0** ✅ | 0 |
| `remove()` em `@fail` | 8 | **0** ✅ | 0 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **0** ✅ | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 + o registro `unclosable` da 6.5 |
| divergências de ordenação (G-ORDER) | 4 | 4 (+1 invisível, achado 53) | 0 |
| linhas no `predicate_graph.csv` | — | **45** | — |
| linhas com `disposition=omission` | 0 | **9** | — |
| achados dos gates estruturais | 71 (na 4.8) | **10** (todos G-PRED2) | 0 |
| hunks no `divergence_record.csv` | — | **277**, todos registrados | — |
| traces do corpus | 63 | **101**, todas commitadas | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 101 traces contra `backup/gh105-preimage/jca_android`: **67 inalteradas, 19
movidas, 9 introduzidas, 6 removidas** (cumulativas contra a pré-imagem). **As 9 `introduced` são
todas reparos deliberados — não há janela aberta.**

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`). **Mais a quinta, que o gate não vê: `KeyManagerFactorySpec`
(`g1 init gkm1`) — achado 53.**

`gh104_gates.py` sobre o monitor gerado: `G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 ·
G-ERE 0 · G-CONF 0 · **G-PRED 23**`. O G-PRED chegou a 23 — um por arquivo do conjunto — que é o
espelho do INV-INS-130 chegando a zero: **todos os 23 arquivos estão migrados**.

---

## Censo por arquivo — o **estado real**

Saiu do `predicate_graph.csv` em 2026-08-22, depois da 4.14. Reconfira com `--emit` antes de
citar qualquer número numa evidência.

| arquivo | `read:body` | `write:body` | `write:acceptance` | `negate` | tarefa |
|---|---|---|---|---|---|
| `CipherSpec.mop` | 3 | 0 | 2 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 2 | 0 | 1 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 1 | 2 | 3 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 2 | 1 | 0 | 1 | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 2 | 0 | 1 | 0 | ✅ 4.7 |
| `GCMParameterSpecSpec.mop` | 2 | 0 | 1 | 0 | ✅ 4.8 |
| `SecretKeySpecSpec.mop` | 1 | 0 | 1 | 0 | ✅ 4.10 |
| `SecretKeySpec.mop` | 1 | 0 | 1 | 0 | ✅ 4.12 |
| `SignatureSpec.mop` | 0 | 0 | 2 | 0 | ✅ 4.13 |
| `MessageDigestSpec.mop` | 0 | 0 | 1 | 0 | ✅ 4.13 |
| `SSLContextSpec.mop` | 0 | 0 | 2 | 0 | ✅ 4.13 |
| `KeyPairSpec.mop` | 0 | 2 (razão) | 0 | 0 | ✅ 4.13 |
| `KeyStoreSpec.mop` | 0 | 0 | 2 | 0 | ✅ 4.14 |
| `KeyGeneratorSpec.mop` | 0 | 0 | 1 | 0 | ✅ 4.14 |
| `KeyManagerFactorySpec.mop` | 0 | 1 (razão) | 1 | 0 | ✅ 4.14 |
| `TrustManagerFactorySpec.mop` | 0 | 1 (razão) | 1 | 0 | ✅ 4.14 |
| `KeyPairGeneratorSpec.mop` | 0 | 0 | 1 | 0 | ✅ 4.14 |
| `DHGenParameterSpecSpec.mop` | 0 | 0 | 1 | 0 | ✅ 4.14 |
| `HMACParameterSpecSpec.mop` | 0 | 0 | 1 | 0 | ✅ 4.14 |
| ~~`MacSpec.mop`~~ · ~~`RandomStringPassword.mop`~~ | — | — | — | — | saíram do grafo (4.9, 4.11) |

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

## Próximo passo: 4.15 e 4.16 — duas tarefas de conferência, não de edição

**A 4.15 provavelmente já está satisfeita.** Ela pede: zero leituras em `condition` (INV-INS-133
— **já em 0 desde a 4.12**), `test_inv_ins_134_write_placement` verde (**já verde**: as sete
escritas em corpo carregam razão registrada), disciplina de import verde (INV-INS-130 — **já em
0 desde a 4.14**), zero `set/unsetObjectAsInAcceptingState` (INV-INS-147 — **já em 0 desde a
4.14**), e par de traces commitado por leitura movida. **Não presuma**: rode os gates, confira
item por item, e o que a tarefa pedir de "baselines aposentadas pelo bloco `retired`" pode
exigir um `--write` com a chamada a `retire()`. Se tudo estiver satisfeito, a 4.15 fecha com a
evidência dizendo **contra o que** cada item foi conferido — e diga qual tarefa levou cada
número a zero, porque nenhum deles foi a 4.15.

Atenção a uma coisa que a 4.15 pode revelar: as **dez linhas G-PRED2** que restam são todas
escritas cujo consumidor é do Grupo 5 (`ENCRYPTED`×2, `PREPARED_DH`, `PREPARED_GCM`,
`PREPARED_HMAC`, `PREPARED_IV`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_STORE`, `SPECCED_KEY`,
`GENERATED_TRUST_MANAGER`). Elas estão na baseline e **devem** estar; a 5.11 é a varredura que
as fecha. Não as trate como achado novo.

A **4.16** roda `/rv-test-run tests/parity` (gh104 + gh105 juntos), que é mais amplo que as
quatro suítes de gates que você vem rodando.

**Só então o Grupo 5**, que a 4.3 liberou. A ordem dele é topológica pelo ledger, e a 5.1 é a
cadeia piloto. Repare que a 5.9 herda três produtores desta passagem e que o
`data/gh105/evidence/f2-write-only-batch-b.md` já mediu, para ela, o que cada um escreve e onde.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.14)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20), que às
   vezes é o mesmo que o `@match` (achado 42). **E confira a aridade da cláusula contra a aridade
   da `Property`.** **Se não houver regra**, diga isso e diga o que o arquivo então é.
   **E reconte o censo que a tarefa afirma** (achado 49).
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   **Um processo por configuração** (achado 51). Se o corpus não tiver trace do sítio, **escreva a
   trace e meça a semente — antes da edição** (aprendizado 47). E **audite a sonda**: um controle
   que sabidamente acusa e um que sabidamente não, no mesmo carregador. **Quando a passagem tiver
   mais de uma disposição possível, simule a alternativa** em linha entre os dispatchers reais
   (aprendizado 51) — e, depois de editar, **confira a simulação contra a árvore de verdade**.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string. **E não ponha comentário entre o `ere`/`fsm` e o primeiro `@`**
   (aprendizado 43). **Apague o campo que o bookkeeping órfã**, com as suas atribuições —
   precedente da 4.1, da 4.13 e da 4.14 (cinco campos de uma vez).
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. **Preserve a ordem do arquivo.** As linhas existentes **mudam de
   `file_line`** quando a edição move linhas: relocate-as no lugar, sem reordenar — e confira
   cada âncora contra a árvore num laço (achado 57).
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato, as linhas ficam como estão
   — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. **Confira que a trace replica inteira**
   (`unresolved: []`) antes de commitá-la, nos dois lados **e** contra o snapshot congelado
   (aprendizado 52). Uma trace pode ligar o valor devolvido (`k.getEncoded() -> enc`) e usar
   `bind` para construir objetos sem disparar nada — e **`bind` é também como se executa uma
   chamada de efeito que o monitor não deve ver** (aprendizado 54).
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas — e **reconferir o
   round-trip depois de preencher**.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo, com
   a coluna `task` acumulando. O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
   **Anexe as linhas novas no fim, na ordem do arquivo `.mop`, e não reordene o resto.**
   **Chaveie por `(file, hunk)`, nunca só por `hunk`.** Convenção de `kind`: bloco de comentário →
   `placement`; o sítio e o import → `predicate-store`; troca de valor ou de predicado escrito →
   `behavioural`; o `@fail` que perde uma remoção → `predicate-removal`.
   **Para mapear stale → novo**, recompute os hunks contra `git show HEAD:<path>` e case por
   sobreposição de linhas: o script está no histórico desta sessão e da 4.13.
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class`. **`git diff --stat
   data/gh105/evidence/harness/` é a medida mais forte de "não mexi em mais nada"**: na 4.11, na
   4.12, na 4.13 e na 4.14 no máximo dois relatórios dos 23 mudaram.
10. Conferir e reescrever a baseline (`--write`); ela preserva `retired`. Ela imprime uma linha
    `repaired` por achado que saiu — cole essas linhas na evidência. **Uma linha `NEW` pode ser um
    achado re-chaveado e não um novo**: a 4.14 teve duas, e a evidência diz qual velha chave cada
    uma substitui.
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também.** São
    **três** censos e eles não estão juntos: o do conjunto, o do grafo e o do gate de colocação.
    **E releia os testes de fixture que subtraem de um contador que chegou a zero** (achado 56).
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md` (ou `f2-<lote>.md`).
13. Rodar as quatro suítes. **Apagar `data/gh104/traces/output/`**. Commitar (stage por caminho
    explícito). Marcar o checkbox **pela skill**, junto com qualquer correção de texto que a
    passagem tenha descoberto nos artefatos.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java` (os acessores são
  `getType()`/`getSpec()`/`getExpecting()`, **não** `getErrorType()`/`getMessage()`)
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (`getErrors()` devolve um
  `Set`; `reset()` existe, e **não** zera o conjunto de monitores — achado 51)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (a gramática das traces;
  `fitsPointcut` reparado pela 4.11, `produce`/`onPublicOwner` pela 4.13) e `TraceRunnerTest.java`
  (**2 falhas pré-existentes no HEAD — achado 40**)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← **os 23 estão migrados**
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)
- Gramáticas: `rv-monitor/.../fsm/parser/FSMParser.jj`, `.../ere/.../FSM.java:85`,
  `.../fsm/JavaFSM.java:160`, **`javamop/.../main_parser/RVParser.java:379`**

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: 7.6**)
- `scripts/gh104_gates.py`, `gh104_mop_lint.py`, `gh104_divergence_record.py`,
  `gh104_diff_harness.py`, `gh104_message_gate.py`
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`, **`conformance_record.csv`** (73 linhas — **leia-o antes de "descobrir"
  uma divergência**), `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (**101, todas commitadas**), `data/gh104/baseline.md`
- `results/gh101_group8_jca_frozen_control/monitors/` (o snapshot congelado)
- `data/gh105/evidence/`: as treze evidências de passagem, `f1-group-three-the-seventeen.md`,
  `f1-order-gate-precedence.md`, `reach-probe/`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

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
# achados por gate, de um golpe (hoje: G-PRED2 10, e nada mais):
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android 2>&1 \
    | grep -oE "\[INV-INS-[0-9]+\]|\[G-[A-Z0-9']+\]" | sort | uniq -c

# lint e gate de mensagens do gh104
uv run python scripts/gh104_mop_lint.py $SPECS/jca_android
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# gerar o monitor a partir do conjunto editado (~75 s) — é o teste de gramática mais barato
uv run rv-monitor-generator generate --specs-dir $SPECS/jca_android --output <dir>

# os gates estruturais sobre um monitor já gerado (use o scratch do harness)
M=$(ls -dt ~/tmp-gh104/gh104-harness-* | head -1)/b/monitors/MultiSpec_1RuntimeMonitor.java
uv run python scripts/gh104_gates.py --monitor $M \
    --allowlist data/jca_android/gate_allowlist.csv \
    --crysl /home/pedro/.../MetaCrySL/generated/api30 \
    --alias data/jca_android/alias_table.csv \
    --constraint-table data/jca_android/constraint_table.csv
# hoje: G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23

# ler a tabela de transição de uma especificação no monitor gerado (achado 42)
awk '/^class <Spec>Monitor /,/^}/' $M | grep -E "transition_|Category_"

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer — a quinta é
# invisível ao gate, achado 53)
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

# sonda de contagem sobre o ErrorCollector inteiro (receita completa nas evidências da 4.13 e da
# 4.14, com UM PROCESSO POR CONFIGURAÇÃO e os dois controles)
javac -nowarn -cp "$CP:<scratch>/b/work/classes/classes" -d <dir> Probe.java
java -cp "<dir>:$CP:<scratch>/b/work/classes/classes" Probe <modo> <configuração>

# testes JUnit do lado Java (ATENÇÃO: TraceRunnerTest tem 2 falhas pré-existentes — achado 40)
cd $RVSEC_HOME && mvn -o test -pl rvsec/rvsec-mop -DskipMopAgent -Dtest=TraceRunnerTest

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
Os que a 4.15 e o Grupo 5 vão usar:

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
    `ErrorSummary`: relatos idênticos se fundem. **E veja o achado 51: isso ainda não basta.**
43. **Não ponha comentário entre a linha do `ere`/`fsm` e o primeiro `@handler`.**
44. **Não reordene `codes.csv` nem `divergence_record.csv`.**
45. **`git diff` sem `--cached` compara com o índice, não com o HEAD.**
47. **"Escreva a trace primeiro" quer dizer antes da EDIÇÃO.**
49. **Uma linha aposentada pode se dividir entre dois hunks novos** — e um hunk novo pode absorver
    **três** aposentadas, que foi o caso do `TrustManagerFactorySpec` na 4.14. Registre em todos.
51. **Dá para medir a árvore que você não tem** — escreva os corpos candidatos em linha na sonda,
    entre os dispatchers reais da árvore de partida.
52. **Uma trace nova tem de resolver em TRÊS snapshots**, não dois.
53. **`git diff --stat -- data/gh105/evidence/harness/`** é a asserção mais barata e mais forte de
    que a passagem não mexeu em mais nada.
54. **Antes de aceitar uma limitação do instrumento, meça-a** — e meça a sua **largura**.
56. **`String.valueOf(Object)` de um `byte[]` é `[B@<hash>`.** Não deduza semântica de JDK da
    documentação: chame.
57. **Confira a simulação contra a árvore de verdade depois de editar.**
58. **Uma trace pode ligar o valor devolvido por uma chamada de instância** (`k.getEncoded() ->
    enc`), e `bind x = <chamada>` constrói o objeto **sem disparar advice nenhum**.
60. **Quando um número do handoff discordar de um artefato, o artefato ganha.** E quando a
    **tarefa** discordar do `design.md`, o design ganha.
