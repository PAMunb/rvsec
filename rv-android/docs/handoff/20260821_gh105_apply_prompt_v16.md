# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 37/74, o Grupo 4 vira só escritas)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `fbd861c6`
**Progresso**: 37 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.12 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v15.md` (checkpoint 36/74).

> **O conjunto não tem mais nenhuma leitura em `condition(...)`.** A 4.12 tirou a última e o
> INV-INS-133 foi a zero. O que resta do Grupo 4 são as **4.13 e 4.14, só escritas** — 21 escritas
> e 17 chamadas de estado de aceitação em onze arquivos, nenhum deles com leitura. Isso muda a
> forma da passagem: sem leitura, a pergunta "o que este sítio acusa hoje?" quase sempre responde
> *nada*, e o que decide a passagem passa a ser **quem lê a escrita** e **em que store**. Leia a
> seção "Próximo passo" antes de abrir qualquer arquivo: a 4.14 tem uma dívida nominal
> (a janela que a 4.12 abriu) e a 4.13 tem sete sítios que não têm leitor nenhum.

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
**Seis** dessas passagens fecharam elos ou janelas que o plano tinha roteado para depois, e
**duas** reverteram a instrução que a própria tarefa carregava.

---

## Regras de trabalho (não negociáveis)

**Siga `docs/WORKFLOW.md` rigorosamente.** Artefato OpenSpec **nunca** se edita com `Write`/`Edit`
direto — invoque a skill (`openspec-update-change`) pela ferramenta `Skill`. Ela **pede
confirmação antes de escrever cada artefato**, e isso não é formalidade: foi por ela que a sessão
do `946aad17` descobriu que o reparo tinha *dois* sítios, que a 4.10 descobriu que a 5.6 não
listava o quinto produtor, que a 4.11 emendou a regra de `propagation` do `spec.md` em vez de
dobrá-la em torno de um arquivo, e que a 4.12 descobriu que uma frase do `spec.md` — «`e1` *guards*
a propagation write» — tinha acabado de virar falsa pela própria passagem.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final. **Stage por caminho explícito, nunca `git add -A`**
— a árvore tem muita modificação pré-existente não relacionada (gh69, docs, experimentos).

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três, a 4.8 quatro, a 4.9 três mais duas, a 4.10 duas, a 4.11
duas, a 4.12 três; as trinta e quatro foram levadas em opções com recomendação **e medição**, e as
trinta e quatro recomendações foram ratificadas. Faça o mesmo — e leve **medição** junto com a
opção, não só argumento. Se a medição disser que duas opções são indistinguíveis, diga isso. Se a
medição **mata** uma opção, apresente a opção morta assim mesmo, com o número que a matou (na 4.11
foi a gramática do JavaMOP que matou uma; na 4.12 foi um falso-negativo medido).

**O pesquisador contesta, e às vezes ele tem razão.** Na 4.11 a pergunta sobre a trace da rota
`int` voltou como *"como assim um parâmetro declarado Object não consegue receber Integer???"*.
Não era limitação legítima do harness, era defeito — e a investigação que a contestação forçou
virou reparo medido. Quando o pesquisador duvidar de uma limitação que você aceitou, **meça a
limitação** antes de defendê-la.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda (a chamada `ensure`, o evento, o
estado do autômato) antes de oferecer opções, e diga explicitamente o que **não** muda. A 4.8, a
4.10, a 4.11 e a 4.12 abriram com um parágrafo do que a tarefa move independentemente de qualquer
decisão e uma tabela de medições com a fonte de cada uma; as decisões saíram numa rodada só.

**Diga o custo por inteiro.** A 4.11 removeu um falso-negativo e **introduziu um falso-positivo**
sobre um programa honesto. A 4.12 fechou uma cadeia e **abriu uma janela**, e mediu que a janela
não custa relato nenhum em vez de afirmar que era pequena. Uma passagem que só conta o que
melhorou não é evidência.

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

**As duas regras do `spec.md` que o Grupo 4 usa** foram emendadas pelas duas últimas passagens.
A de `propagation` tem duas condições desde a 4.11 (alimenta uma escrita **e** a escrita carrega o
predicado através) e ganhou na 4.12 a medição que a sustenta no único sítio que a cumpre. E a
INV-INS-134 é a que decide as 4.13/4.14 inteiras: **uma escrita fica no ponto de aceitação, ou
carrega uma razão registrada no `predicate_graph.csv`**.

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as onze evidências
que já existem, porque são as onze formas que uma passagem de arquivo pode ter:

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
| `data/gh105/evidence/f2-RandomStringPassword.md` (4.11) | a que apaga porque a ESCRITA é insustentável, e repara o instrumento no caminho |
| **`data/gh105/evidence/f2-SecretKeySpec.md` (4.12)** | **a que mede a janela que ela mesma abre, e descobre que a janela não custa nada** |

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
app sob teste. A 4.4 a 4.12 já se apoiaram nessa tolerância.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 a 4.11: ver os handoffs v12, v13, v14 e v15

Em uma linha cada: **4.1+4.2** `CipherSpec`, o arquivo mais difícil (17/17 eventos, headroom
zero), `d71c8e64`; **4.3** a sonda de alcance em três camadas — *a change NÃO está bloqueada, o
Grupo 5 está liberado*, `4881b557`; **4.4** `IvParameterSpec`, `a9d8f2bd`; **4.5**
`SecureRandomSpec`, `a7e97294`; **4.6** `PBEKeySpecSpec`, `ba219f1a`; **4.7**
`PBEParameterSpecSpec`, `d64f3a40`; **4.8** `GCMParameterSpecSpec`, `5222a5d9`; **4.9** `MacSpec`,
`e86bd270` (apaga quatro sítios, o arquivo sai do grafo); **4.10** `SecretKeySpecSpec`,
`28cfa722` (fecha duas janelas invisíveis, aridade fica em 1 de propósito); **4.11**
`RandomStringPassword`, `5f64c8de` (apaga os quatro sítios e repara o `fitsPointcut`); e a sessão
de verificação `946aad17`, em que o parser do G-ORDER foi desmascarado sem reparo.

### 4.12 — `SecretKeySpec`, commit `fbd861c6` — a última guarda, e a janela medida

Evidência: **`data/gh105/evidence/f2-SecretKeySpec.md`** (256 linhas).

Com ela o **INV-INS-133 vai a zero**: o conjunto não tem mais leitura em `condition(...)`.

A regra `api30/SecretKey.cryptsl` enuncia `ENSURES preparedKeyMaterial[keyMaterial] after ge` e
**nenhuma seção `REQUIRES`**, então a leitura de `generatedKey` não traduz cláusula e não pode
acusar. Três disposições possíveis, todas medidas sobre o `ErrorCollector` inteiro, em seis
árvores — três reais e três escritas **em linha entre os dispatchers da árvore de partida**
(aprendizado 51), e a simulação foi depois conferida contra a árvore migrada de verdade,
configuração por configuração:

| configuração | pré-imagem | partida | **guardada** | sem guarda | apagada | guardada pós-4.14 | migrada real |
|---|---|---|---|---|---|---|---|
| A `KeyGenerator` → `getEncoded` → `IvParameterSpec` | 0 | 1 | **1** | 0 | 1 | **0** | 1 |
| B randomizado → `SecretKeySpec` → `getEncoded` → `IvParameterSpec` | 0 | 1 | **0** | 0 | 1 | 0 | 0 |
| C controle: `byte[]` sem origem | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| D controle: `SecretKeySpec` hard-coded | 4 | 2 | **2** | **1** | 2 | 2 | 2 |
| E a trace commitada, sem consumidor | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

A linha D matou a opção "sem guarda", que era a tradução literal da regra: sem a leitura, a
encodificação de uma chave hard-coded é entregue como randomizada e o IV construído com ela deixa
de ser acusado. A linha B é o que a passagem compra. E a linha A é a janela contra
`KeyGeneratorSpec.mop:80` e `KeyStoreSpec.mop:83`, que **não custa relato nenhum**, porque a
escrita que a leitura passa a suprimir ia para um store que nenhum leitor de `randomized` usa
desde a 4.4.

Três decisões ratificadas: a leitura fica governando a escrita; o `NEGATES generatedKey[this,_]
after d` sem sítio é registrado (a 6.5 é dona do registro, e recebeu a medição); a confusão #32
continua registrada e não reparada (5.10 + 6.1).

---

## Decisões ratificadas pelo pesquisador

**As decisões 1 a 25 estão no handoff v13, as 26 a 29 no v14 e as 30 e 31 no v15** — leia-as lá.
As mais citadas: **2** (escrita sem cláusula é apagada, não registrada), **7** (mudança
comportamental sem medição que a decida não entra em migração de substrato), **11** (a retirada
vai com a escrita que ela desfaz), **13** (a leitura sem cláusula também é de três valores),
**16** (o registro de omissão deliberada vem para a passagem do arquivo), **19** (código sem
caminho de execução é apagado quando mover criaria outro), **21** (o `@fail` inalcançável é
registrado, não reparado), **28** (a escrita move store e não move aridade), **30** (os quatro
sítios do `RandomStringPassword` são apagados), **31** (o reparo do `fitsPointcut` entra na 4.11).

### Na 4.12 (2026-08-21)

32. **A leitura do `SecretKeySpec.e1` fica, governando a escrita**, e não é apagada com a escrita
    virando incondicional — que seria a tradução literal de um `ENSURES` sem `REQUIRES`. O que
    decidiu foi a configuração D: sem a guarda, um falso-negativo medido sobre um programa
    desonesto. A leitura é registrada como `propagation`, sem acusador, de três valores no store —
    e é o único sítio do conjunto em que os três vereditos colapsam em dois, porque ela governa
    uma escrita em vez de um relato.
33. **O `NEGATES generatedKey[this,_] after d` é registrado, não inventado.** Medido: `destroy()`
    lança `DestroyFailedException` nas duas implementações de `SecretKey` que o conjunto enxerga —
    a `SecretKeySpec` e a que o `KeyGenerator.generateKey()` devolve, que é a mesma classe —,
    então um advice `after ... returning` sobre ela não teria caminho de execução nem se o evento
    existisse. **O registro pertence à 6.5**, que o design D-3 já roteia como `unclosable`; a 4.12
    escreveu a medição no texto da 6.5 em vez de duplicar o registro.
34. **A confusão `RANDOMIZED` × `preparedKeyMaterial` continua registrada e não reparada.** É a
    cláusula #32 do ledger, a mesma que a 4.10 registrou do lado da leitura. Renomear só aqui
    reabriria a cadeia que a passagem fecha — medido: a coluna B voltaria de 0 para 1.

---

## Achados que valem mais que as tarefas

**Os achados 1 a 32 estão no handoff v13, os 33 a 36 no v14 e os 37 a 40 no v15.** Os mais
operacionais:

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
38. **O `PredicateStore` não é simétrico entre vínculo e valor.** O vínculo é identidade fraca; as
    posições de valor normalizam `String` e `Integer` para texto.
40. **O `TraceRunnerTest` está VERMELHO no HEAD, e já estava.** 2 falhas de 6, pertencentes à porta
    de tipo de retorno do `bdc027a6` e à 8.5 do gh104 — **não são regressão sua**, e não as repare
    dentro da gh105 sem levar ao pesquisador.

### Novos, da 4.12

41. **Uma janela F2 pode não custar relato nenhum, e só a medição diz qual é o caso.** A 4.12
    abriu uma janela contra dois produtores e mediu **1 relato antes, 1 depois**: a escrita que a
    leitura passou a suprimir já ia para um store que ninguém lê desde a 4.4. O corolário é
    operacional — **quando abrir uma janela, meça se ela é observável antes de descrevê-la como
    custo**, e diga qual das duas coisas ela é. O contrário também vale: a coluna "pós-4.14"
    mostra a linha indo a 0, então a janela é real, apenas invisível hoje.
42. **A tabela de transição decide onde a escrita vai, e às vezes as duas rotas coincidem.**
    O INV-INS-134 admite o `@match` **ou** os estados de um `after L`. No `SecretKeySpec` a
    cláusula tem `after ge` e o `ere` é `e1*`: a linha de transição é `{0, 1}` e a categoria é
    `nextstate == 0`, então os estados depois de `ge` e os de aceitação são o mesmo estado único.
    **Leia a linha de transição do monitor gerado antes de argumentar sobre a colocação** — custa
    um `awk` e fecha a discussão.
43. **Um handler não vê parâmetro de evento.** Toda escrita no ponto de aceitação sobre um valor
    que só o evento conhece precisa de um campo de estágio, limpo ao ser consumido — a forma do
    `SecureRandomSpec.next2` (4.5) e agora do `SecretKeySpec.e1`. Se não limpar, um evento cuja
    leitura falhou reescreve a marcação do anterior.
44. **`getEncoded()` devolve um clone novo a cada chamada.** Medido, não deduzido. Consequência:
    nenhum store chaveado por identidade enxerga o material através da cópia, e uma cadeia
    "chave → bytes" **precisa** de um sítio de propagação — não é conveniência.
45. **A migração estreita o casamento também sobre objetos com `equals` de valor.** O
    `javax.crypto.spec.SecretKeySpec` sobrescreve `equals` comparando algoritmo e bytes, e o store
    velho era um `HashSet`. Duas chaves distintas com o mesmo material compartilhavam
    `generatedKey` e não compartilham mais. Aqui o estreitamento é defensável (um predicado sobre
    uma chave não deve grudar noutra), mas **é uma mudança silenciosa que todo arquivo migrado
    herda** — confira, quando o objeto vinculado for de uma classe com `equals` de valor.
46. **Uma linha `unchanged` do harness pode ser exatamente a que mede o ganho.** A trace
    `SecretKeySpec-encoded-iv` é muda na pré-imagem e muda na árvore migrada, e acusava só na
    árvore de partida — que o harness não contém. **Não conclua "não mudou nada" de um
    `unchanged`**: diga contra o que ele é `unchanged`.

### Três defeitos de pipeline, fora do escopo desta change — relatório escrito, decisão pendente

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). D1: o caminho de experimento não fornece `ANDROID_SDK_HOME` e o
GATOR morre. D2: a análise estática mira `resources/jca` mesmo sob `--specification-set
jca_android` — **interage com o Grupo 5**. D3: o INV-EXP-16 não é aplicado.

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.**

Há ainda o **RISK-013 da gh69** (`openspec/changes/gh69-generic-subtype-target-matching/risk-register.md:565`),
que é sobre o `RandomStringPassword.mop` e é defeito de *análise estática*, não de runtime.
Referencie um do outro, não os funda.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21, depois da 4.12)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **0** ✅ | 0 |
| leituras em corpo | 0 | **14** | todas |
| escritas em corpo de evento | 42 | **22** | 0 sem razão registrada |
| escritas no ponto de aceitação | 7 | **12** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **17** | 0 |
| `remove()` em `@fail` | 8 | 7 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 + o registro `unclosable` da 6.5 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **13** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **73** | — |
| achados dos gates estruturais | 71 (na 4.8) | **55** (G-PRED2 23, INV-INS-130 13, INV-INS-134 19) | 0 |
| hunks no `divergence_record.csv` | — | **212**, todos registrados | — |
| traces do corpus | 63 | **97**, todas commitadas | — |
| asserções nas quatro suítes | — | **94** | — |

> **Correção ao v15**: a linha do `negate` dizia alvo "2 (falta `SecretKey: generatedKey after d`)".
> Está errado, e o `design.md` D-3 é a fonte: a segunda cláusula **não** ganha sítio, ela ganha um
> registro `unclosable` na tarefa 6.5. O alvo é 1 mais o registro.

Harness sobre as 97 traces contra `backup/gh105-preimage/jca_android`: **62 inalteradas, 19
movidas, 10 introduzidas, 6 removidas** (cumulativas contra a pré-imagem). Das 10 `introduced`,
**nove são reparos deliberados e uma é janela** — a `SecretKeySpec-keygen-iv`, que a 4.14 fecha.

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.13-4.14 são pré-change e estão desatualizados.** Esta tabela
saiu do `predicate_graph.csv` em 2026-08-21, depois da 4.12. Reconfira com `--emit` antes de citar
qualquer número numa evidência.

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
| **`SignatureSpec.mop`** | 0 | **4** | 0 | 1 | 0 | **4.13** |
| **`MessageDigestSpec.mop`** | 0 | **3** | 0 | 2 | 0 | **4.13** |
| **`SSLContextSpec.mop`** | 0 | **2** | 0 | 2 | 0 | **4.13** |
| **`KeyPairSpec.mop`** | 0 | **2** | 0 | 1 | 0 | **4.13** |
| `KeyStoreSpec.mop` | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyManagerFactorySpec.mop` | 0 | 2 | 0 | 2 | 1 | 4.14 |
| `TrustManagerFactorySpec.mop` | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyGeneratorSpec.mop` | 0 | 1 | 0 | 2 | 1 | 4.14 |
| `KeyPairGeneratorSpec.mop` | 0 | 1 | 0 | 1 | 1 | 4.14 |
| `DHGenParameterSpecSpec.mop` | 0 | 0 | 1 | 1 | 0 | 4.14 |
| `HMACParameterSpecSpec.mop` | 0 | 0 | 1 | 1 | 0 | 4.14 |

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

## Próximo passo: 4.13 — quatro arquivos **só de escritas**

### O que muda de forma na passagem

Nenhum destes quatro arquivos tem leitura. Isso tira do jogo a pergunta que guiou as 4.1 a 4.12
("o que este sítio acusa hoje?") — a resposta é *nada*, porque uma escrita não acusa. **O que
decide a passagem passa a ser outra pergunta: quem lê esta escrita, e em que store?** Três casos,
e a tarefa já diz que sete dos onze sítios caem no terceiro:

1. **Tem leitor no conjunto, já migrado** → mover a escrita fecha uma cadeia. Meça o antes e o
   depois com a sonda, como a 4.12 fez com a coluna B.
2. **Tem leitor no conjunto, ainda no store velho** → mover abre uma janela F2. **Meça se ela é
   observável** (achado 41): pode custar zero, e dizer "custa zero" é diferente de dizer
   "é pequena".
3. **Não tem leitor nenhum** — o `ENSURES` é um beco sem saída do oráculo. A tarefa 4.13 diz que
   **sete dos onze** sítios estão aqui, e que cada um leva um **registro de omissão deliberada**
   (INV-INS-137) pelo leitor ausente. **Nenhuma leitura é fabricada para nenhum deles.** O
   precedente literal é o `preparedPBE` da 4.7, a única linha do grafo com `disposition=omission`
   até hoje — leia essa linha antes de escrever as suas.

### O que ainda é igual

O ponto de aceitação continua sendo decidido pelo par (cláusula tem `after L`?, o que o `ere`/`fsm`
nomeia) — e o achado 42 diz para **ler a tabela de transição do monitor gerado** antes de
argumentar. Se a escrita ficar fora do ponto de aceitação, ela precisa da **razão registrada** no
`predicate_graph.csv` (INV-INS-134). E as chamadas de estado de aceitação (`setObjectAsInAcceptingState`
e a irmã) saem sem substituto: o store novo não as oferece e o conjunto nunca as leu de volta
(INV-INS-147) — são 6 delas nestes quatro arquivos, e o número global vai de 17 para 11.

### Os quatro arquivos, e o que conferir em cada um antes de editar

- **`SignatureSpec.mop`** — 4 escritas, 1 bookkeeping. É o arquivo com mais escritas do que resta.
  Confira `api30/Signature.cryptsl`: quais dos quatro sítios traduzem `ENSURES` e quais não
  traduzem nada. A regra tem um `i2` com `SecureRandom` no pointcut (`SignatureSpec_i2Event`),
  então há chance de elo com o `SecureRandomSpec`, que já está no store novo.
- **`MessageDigestSpec.mop`** — 3 escritas, 2 bookkeeping. Lembre do achado 29: a mudez pode ser
  da especificação. E o `reset` deste arquivo é um advice `before`, que é justamente o que o
  `TraceRunner` replica pelos dispatchers estáticos e não pelos wrappers.
- **`SSLContextSpec.mop`** — 2 escritas, 2 bookkeeping. **Este arquivo tem uma divergência
  G-ORDER aberta** (`g1 Init se1 se1`), que é da 7.1 e **não** desta passagem — diga isso na
  evidência em vez de deixar o leitor achar que a passagem a ignorou.
- **`KeyPairSpec.mop`** — 2 escritas, 1 bookkeeping. Confira se o consumidor é o
  `KeyPairGeneratorSpec` (`GENERATED_KEY_PAIR`), que só migra na 4.14 — se for, é o caso 2 e a
  janela tem de ser medida.

### E a dívida que a 4.14 herda, por escrito

A 4.12 abriu uma janela contra **`KeyGeneratorSpec.mop:80`** e **`KeyStoreSpec.mop:83`**, os dois
produtores de `GENERATED_KEY` que continuam no store velho. A trace
`data/gh104/traces/SecretKeySpec-keygen-iv.txt` é a testemunha, e ela está classificada
`introduced` no harness hoje. **Quando a 4.14 migrar esses dois, essa linha tem de sair de
`introduced`** — e a evidência da 4.14 deve mostrar isso, porque é a prova de que a janela era
janela e não regressão. A coluna "guardada pós-4.14" da tabela da 4.12 já mediu o que deve
acontecer: a linha A vai a 0.

### Depois da 4.13 e da 4.14

A 4.15 fecha o grupo (gates de colocação verdes, baselines aposentadas pelo bloco `retired`) e a
4.16 roda `/rv-test-run tests/parity`. Só então o Grupo 5, que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.12)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20), que às
   vezes é o mesmo que o `@match` (achado 42). **E confira a aridade da cláusula contra a aridade
   da `Property`.** **Se não houver regra**, diga isso e diga o que o arquivo então é.
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   Se o corpus não tiver trace do sítio, **escreva a trace e meça a semente — antes da edição**
   (achado 18 + 34 + aprendizado 47). E **audite a sonda**: rode um controle que sabidamente acusa
   no mesmo carregador de classes, e liste os dispatchers que ela encontrou.
   **E, quando a passagem tiver mais de uma disposição possível, simule a alternativa** em linha
   entre os dispatchers reais (aprendizado 51) — e, depois de editar, **confira a simulação contra
   a árvore de verdade**, que é o que a 4.12 fez e o que audita o próprio método.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string. **E não ponha comentário entre o `ere`/`fsm` e o primeiro `@`**
   (aprendizado 43); se o comentário for sobre o handler, ponha-o **antes** do `ere`.
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. **Preserve a ordem do arquivo** (aprendizado 44). Um sítio só de escrita
   não ganha código nenhum.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato, as linhas ficam como estão
   — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade. **Fora da janela, meça o lado satisfaz de
   verdade.** **Confira que a trace replica inteira** (`unresolved: []`) antes de commitá-la, nos
   dois lados **e** contra o snapshot congelado (aprendizado 52). Uma trace pode ligar o valor
   devolvido: `k.getEncoded() -> enc` funciona, e foi assim que a 4.12 observou a cadeia inteira.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas — e **reconferir o
   round-trip depois de preencher** (aprendizado 34).
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo, com
   a coluna `task` acumulando. O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
   **Anexe as linhas novas no fim, na ordem do arquivo `.mop`, e não reordene o resto**
   (aprendizado 44). **Chaveie por `(file, hunk)`, nunca só por `hunk`** (aprendizado 45).
   Convenção de `kind`: bloco de comentário → `placement`; o sítio e o import → `predicate-store`.
   Confira com `git diff --numstat` que o arquivo cresceu e não foi reescrito.
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class` — **e lembrar que é piso, não contagem**,
   e que um `unchanged` pode ser exatamente a linha que mede o ganho (achado 46).
   **`git diff --stat data/gh105/evidence/harness/` é a medida mais forte de "não mexi em mais
   nada"**: na 4.11 e na 4.12 só um relatório dos 23 mudou (aprendizado 53).
10. Conferir e reescrever a baseline (`--write`); ela preserva `retired`. Ela imprime uma linha
    `repaired` por achado que saiu — cole essas linhas na evidência.
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também.** São
    **três** censos e eles não estão juntos: o do conjunto (`read_placement`, `accepting-state`), o
    do grafo (`read:body`, `write:body`, `write:acceptance`, `bookkeeping`) e o do gate de
    colocação (`len(guards)`, que agora é **0** e deve continuar sendo).
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md`.
13. Rodar as quatro suítes. Commitar (stage por caminho explícito). Marcar o checkbox pela skill.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java` (o envelope está em
  `getExpecting()`, não em `toString()`)
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (`getErrors()` devolve um
  `Set`; `reset()` existe)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (a gramática das traces;
  `fitsPointcut` reparado pela 4.11) e `TraceRunnerTest.java` (**2 falhas pré-existentes no
  HEAD — achado 40**)
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
  `constraint_table.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (**97, todas commitadas**), `data/gh104/baseline.md` (o corpus publicado)
- `results/gh101_group8_jca_frozen_control/monitors/` (o snapshot contra o qual o
  `TraceRunnerTest` replica — uma trace nova tem de resolver **aqui também**)
- `data/gh105/evidence/`: as onze evidências de passagem, `f1-group-three-the-seventeen.md`,
  `f1-order-gate-precedence.md`, `reach-probe/`, `f1-*-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`
— para a 4.13, leia `Signature.cryptsl`, `MessageDigest.cryptsl`, `SSLContext.cryptsl` e
`KeyPair.cryptsl` **antes** de abrir os `.mop`.

**Gramática do CrySL (somente leitura)**:
`/home/pedro/tmp/CryptSL/de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext`
— o `ORDER` está em :99-134. **É a fonte que decide qualquer dúvida de precedência.**

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 94 passando, ~90 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI (--json dá as contagens por gate)
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit
# achados por gate, de um golpe:
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android 2>&1 \
    | grep -oE "\[INV-INS-[0-9]+\]|\[G-[A-Z0-9']+\]" | sort | uniq -c

# lint e gate de mensagens do gh104 (os dois quebram com facilidade numa migração)
uv run python scripts/gh104_mop_lint.py $SPECS/jca_android
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# gerar o monitor a partir do conjunto editado (~80 s) — é o teste de gramática mais barato
uv run rv-monitor-generator generate --specs-dir $SPECS/jca_android --output <dir>

# os gates estruturais sobre um monitor já gerado (G-ERE, G-6', G-CONF)
M=$(ls -dt ~/tmp-gh104/gh104-harness-* | head -1)/b/monitors/MultiSpec_1RuntimeMonitor.java
uv run python scripts/gh104_gates.py --monitor $M \
    --allowlist data/jca_android/gate_allowlist.csv \
    --crysl /home/pedro/.../MetaCrySL/generated/api30 \
    --alias data/jca_android/alias_table.csv \
    --constraint-table data/jca_android/constraint_table.csv
# hoje: G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 10

# ler a tabela de transição de uma especificação no monitor gerado (achado 42)
awk '/^class <Spec>Monitor /,/^}/' $M | grep -n "transition_\|Category_"

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

# sonda de contagem sobre o ErrorCollector inteiro (receitas completas nas evidências 4.7-4.12;
# a da 4.12 tem os dois modos "árvore que você não tem" e o controle que mede diferente de zero)
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

**Os aprendizados 1 a 46 estão no handoff v13, os 47 a 50 no v14 e os 51 a 56 no v15.** Os que a
4.13 vai usar:

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
    stores também.
43. **Não ponha comentário entre a linha do `ere`/`fsm` e o primeiro `@handler`.**
44. **Não reordene `codes.csv` nem `divergence_record.csv`.**
45. **`git diff` sem `--cached` compara com o índice, não com o HEAD.**
47. **"Escreva a trace primeiro" quer dizer antes da EDIÇÃO.**
49. **Uma linha aposentada pode se dividir entre dois hunks novos.** Registre a absorção nos dois.
51. **Dá para medir a árvore que você não tem** — escreva os corpos candidatos em linha na sonda,
    entre os dispatchers reais da árvore de partida.
52. **Uma trace nova tem de resolver em TRÊS snapshots**, não dois.
53. **`git diff --stat -- data/gh105/evidence/harness/`** é a asserção mais barata e mais forte de
    que a passagem não mexeu em mais nada.
54. **Antes de aceitar uma limitação do instrumento, meça-a.**
55. **Uma opção pode ser morta pela gramática do gerador, e isso é uma medição.**
56. **`String.valueOf(Object)` de um `byte[]` é `[B@<hash>`.** Não deduza semântica de JDK da
    documentação: chame.

### Novos, da 4.12

57. **Confira a simulação contra a árvore de verdade depois de editar.** A 4.12 escreveu três
    colunas simuladas antes da edição e, depois, rodou a mesma sonda contra a árvore migrada real:
    bateu configuração por configuração. Isso audita o aprendizado 51 em vez de confiar nele, e
    custa um comando.
58. **Uma trace pode ligar o valor devolvido por uma chamada de instância**: `k.getEncoded() -> enc`
    resolve pelo `produce()` do `TraceRunner` e foi o que permitiu observar a cadeia inteira numa
    trace só. A gramática documentada no cabeçalho do `TraceRunner` não mostra essa forma; ela
    funciona.
59. **O `TraceRunner` deixa sucata dentro do repositório.** Uma réplica escreve
    `data/gh104/traces/output/summary.csv`, que aparece como não-rastreado no `git status`. Apague
    antes de montar o stage, ou você a commita junto.
60. **A tarefa pode estar certa e o handoff errado.** O v15 dizia que o alvo do `negate` era 2; o
    `design.md` D-3 e a tarefa 6.5 dizem que a segunda cláusula `NEGATES` ganha um registro
    `unclosable`, não um sítio. **Quando um número do handoff discordar de um artefato, o artefato
    ganha** — e corrija o handoff.
