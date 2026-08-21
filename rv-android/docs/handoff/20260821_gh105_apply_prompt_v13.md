# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 33/74, com a 4.9 medida e decidida)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `5222a5d9`
**Progresso**: 33 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.8 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v12.md` (checkpoint 32/74).

> **A 4.9 está a meio caminho, e o caminho já andado é o caro.** Toda a medição foi feita, as
> **três decisões de projeto já foram levadas ao pesquisador e ratificadas**, e as duas traces
> que o corpus não tinha já estão escritas em disco (**não commitadas, não rastreadas**). O que
> falta é atualizar dois artefatos OpenSpec, editar o `.mop` e rodar o ciclo. **Não re-meça: leia
> a seção "Próximo passo" e execute.**

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
**Quatro** dessas passagens já fecharam elos que o plano tinha roteado para o Grupo 5 — a 4.4+4.5
fiaram o #12, a 4.5+4.6 o #24, a 4.5+4.7 o #25, a 4.5+4.8 o #11 —, o que virou a consequência
recorrente do grupo: a 5.1 herdou um elo pronto e a **5.4 herdou três**.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

A `openspec-update-change` **pede confirmação antes de escrever cada artefato** — isso não é
formalidade: foi por ela que a sessão do `946aad17` descobriu que o reparo tinha *dois* sítios
(a tarefa e o invariante) e não um. **A 4.9 precisa dela antes de qualquer edição de código.**

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três, a 4.8 **quatro**, a 4.9 **três**; as vinte e três foram
levadas em opções com recomendação **e medição**, e as vinte e três recomendações foram
ratificadas. Faça o mesmo — e leve **medição** junto com a opção, não só argumento. Se a medição
disser que duas opções são indistinguíveis, diga isso. Se a medição **mata** uma opção (4.6)
apresente a opção morta assim mesmo, com o número que a matou. E se a medição só existe depois de
você **escrever o instrumento** (4.7) ou **as traces** (4.8, 4.9), escreva-os primeiro e diga que
são novos.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda (a chamada `ensure`, o evento, o
estado do autômato) antes de oferecer opções, e diga explicitamente o que **não** muda. A 4.8
abriu com um parágrafo "o que a tarefa move independentemente de qualquer decisão" e uma tabela
de seis medições com a fonte de cada uma; as três decisões saíram numa rodada só.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente. Ele aparece
legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado inteiro
(INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando acertar,
**diga que acertou e por que não conta**. A 4.8 e a 4.9 fizeram isso duas vezes — e na 4.9 o
conjunto reprovado foi a fonte mais informativa que existia sobre o defeito (ver achado 30).

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

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as sete evidências
que já existem, porque são as sete formas que uma passagem de arquivo pode ter:

| evidência | a forma |
|---|---|
| `data/gh105/evidence/f2-CipherSpec.md` (4.1/4.2) | a que move tudo |
| `data/gh105/evidence/f2-reach-probe.md` (4.3) | a que vai ao dispositivo |
| `data/gh105/evidence/f2-IvParameterSpec.md` (4.4) | a que não move sítio nenhum |
| `data/gh105/evidence/f2-SecureRandomSpec.md` (4.5) | a que fecha e abre janelas F2 |
| `data/gh105/evidence/f2-PBEKeySpecSpec.md` (4.6) | a que fecha uma cláusula sem ter sido mandada |
| `data/gh105/evidence/f2-PBEParameterSpecSpec.md` (4.7) | a que descobre um sítio que não acusava nada |
| **`data/gh105/evidence/f2-GCMParameterSpecSpec.md` (4.8)** | **a que descobre uma especificação inteira muda — e um gate lendo a forma pré-migração** |

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
app sob teste. A 4.4 a 4.8 já se apoiaram nessa tolerância — a 4.7 e a 4.8 explicitamente: o
`@match` chama `ensure(..., spec)` com `spec` nulo quando a construção quebrou uma cláusula, e é
a tolerância que faz disso um no-op. Se a decisão mudar, os sítios mudam junto.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 a 4.7: ver o handoff v12

Resumos completos em `docs/handoff/20260821_gh105_apply_prompt_v12.md` (seção "O que foi feito").
Em uma linha cada: **4.1+4.2** `CipherSpec`, o arquivo mais difícil (17/17 eventos, headroom
zero), commit `d71c8e64`; **4.3** a sonda de alcance em três camadas — *a change NÃO está
bloqueada, o Grupo 5 está liberado*, `4881b557`; **4.4** `IvParameterSpec`, a passagem que não
move sítio nenhum, `a9d8f2bd`; **4.5** `SecureRandomSpec`, a que fecha e abre janelas F2,
`a7e97294`; **4.6** `PBEKeySpecSpec`, a que fecha uma cláusula sem ter sido mandada, `ba219f1a`;
**4.7** `PBEParameterSpecSpec`, a que descobre um sítio mudo, `d64f3a40`; e a sessão de
verificação `946aad17`, em que o parser do G-ORDER foi desmascarado sem que nada fosse reparado.

### 4.8 — `GCMParameterSpecSpec`, commit `5222a5d9` — a passagem que acabou com uma especificação muda

Evidência: **`data/gh105/evidence/f2-GCMParameterSpecSpec.md`** (295 linhas).

A tarefa mandava tirar duas leituras de `randomized[src]` de `condition(...)`. O que ela achou
antes de editar qualquer coisa é maior: a 4.7 tinha descoberto que uma guarda cala um *evento*;
aqui **duas guardas e um `@fail` inalcançável calavam a especificação inteira**. Os dois eventos
abriam com `if (!(guarda)) return false;` antes do `handleEvent`, e o handler de ordenação não
socorre transição suprimida nenhuma porque não pode disparar: as duas linhas de transição são
`{1, 2, 2}` e o monitor é chaveado no objeto construído, então cada monitor vê **no máximo um
evento** e o estado 2 nunca é atingido.

Três leituras independentes da mesma mudez: **0 relatos em 8 construções** sobre o
`ErrorCollector` inteiro; **0 nas 6 traces** do corpus dos dois lados; **0 de 97.018 linhas** do
corpus publicado atribuídas a esta especificação (razão do hunk `4e26843171eb`, do gh104).

O corpus não podia separar decisão nenhuma aqui — as duas traces que nomeavam o arquivo conformam
por inteiro —, então **quatro traces de defeito foram escritas primeiro** e a semente medida com
elas.

Quatro decisões ratificadas (ver abaixo), sete códigos onde havia um, elo **#11** fiado de ponta a
ponta. Achados dos gates 74 → **71**.

---

## Decisões ratificadas pelo pesquisador

### Na 4.1

1. **As escritas de `ENSURES` aterrissam em handler de estado**, não no corpo com razão
   registrada. O custo que o plano atribuía a essa forma — "vence o último par" — **foi medido e
   não existe**.
2. **A escrita sem cláusula é apagada, não registrada como omissão** (`WRAPPED_KEY`).
   `Property.WRAPPED_KEY` fica no enum — INV-INS-132 é append-only.
3. **Aridade 2 com `null`** onde o pointcut não liga o texto claro.

### Na 4.3

4. **APK e driver**: `cryptoapp.apk` com `ape` 60 s primeiro, escalando para `aperv:sata_mop`
   300 s. O `monkey` foi **medido não alcançar** em 600 s.
5. **Veredito em três camadas**, com oráculo e desfecho próprios por camada.
6. **Build do reator rodado assim mesmo**, embora o jar instalado já bastasse.

### Na 4.4

7. **`NOT_OBSERVED` não prepara.** Medido antes de escolher: as duas alternativas são
   indistinguíveis — nenhuma especificação viva lê `PREPARED_IV`. Escolha: **preservação
   literal**. *Mudança comportamental sem medição que a decida não entra em migração de substrato.*
8. **O grafo descreve o artefato, não o plano.**

### Na 4.5

9. **`next1`/`next3` ficam no corpo com razão registrada.**
10. **A escrita do `ints` é apagada, o evento fica.** Precedente `CipherSpec.wkb1` exato.

### Na 4.6 (2026-08-21)

11. **A tradução do `remove()` do `clearPassword` vem da 6.5 para a 4.6.**
12. **A escrita de `speccedKey` fica no corpo do `c1` com razão registrada** — `ere` não sabe
    nomear o estado que segue um evento; a opção literal foi medida e recusada com o DFA do gate.
13. **A leitura sem cláusula também é de três valores.**

### Na 4.7 (2026-08-21)

14. **O relato composto do `c1` decompõe por cláusula.** Delta medido: **uma** construção do
    corpus muda de contagem (`-lowiter`, 1 → 2 relatos).
15. **A guarda do `c2` sai inteira, com a checagem de CONSTRAINTS junto.** Terceira opção
    registrada e não tomada: tirar a contagem da guarda e deixá-la governar só a escrita, sem
    relato.
16. **O `preparedPBE` recebe o registro de omissão deliberada aqui, não na 5.10.** É a **primeira
    `disposition` preenchida** nas linhas do grafo.

### Na sessão de verificação (2026-08-21)

17. **O achado do parser do G-ORDER é registrado agora e reparado na 7.1**, não no Grupo 4.
18. **O registro entra em dois artefatos, não em um** (a tarefa 7.1 *e* o INV-INS-138).

### Na 4.8 (2026-08-21)

19. **Os três conjuntos de faixa do `c2` são APAGADOS, não movidos.**
    `offset >= 0 && len >= 0 && src.length >= offset + len` não traduz cláusula nenhuma (a api30
    tem uma só cláusula CONSTRAINTS, sobre `tLen`) e é **falso-inalcançável** onde estava: o
    contrato documentado do construtor (`GCMParameterSpec.java:102-105`) lança
    `IllegalArgumentException` exatamente no complemento, e um advice `after ... returning` só
    roda no retorno normal — medido nas três construções, todas lançam. **A trace que separaria
    apagar de mover não pode ser escrita, porque o programa não pode ser escrito.** Mover teria
    criado dois códigos sem caminho de execução, numa **quarta** razão.
20. **A checagem de `tLen` sai da guarda junto com a leitura, com código em cada evento.**
    Mantê-la deixaria a leitura recém-movida atrás de uma segunda guarda que suprime a mesma
    transição (o argumento da decisão 15). Delta medido: as duas traces `-badtaglen` vão de 0 para
    1 relato — e vale para **todo** `tagLen` fora do conjunto, não só no corpus.
21. **O `@fail` inalcançável é registrado, não reparado** — o tratamento que o achado 1 deu ao
    sumidouro `unsafeAlg`. Vale tarefa própria: **todo `@fail` de especificação só-construtor
    deste conjunto está na mesma posição**.
22. **O reparo do `_list_guarding` (G-CONF) acontece dentro da 4.8.** O ramo irmão da mesma função
    já tinha sido corrigido pelo mesmo motivo na 3.4. Medido: `jca_android` G-CONF 2 → 0 falhas;
    as quatro suítes vão a 94/94; o `jca` congelado não muda veredito nenhum.

### Na 4.9 (2026-08-21) — **ratificadas, ainda NÃO implementadas**

23. **As duas escritas de `GENERATED_MAC` (`f1`, `f2`) são APAGADAS, e o `remove` do `@fail` vem
    junto.** Medido: `GENERATED_MAC` é escrito em três dos cinco conjuntos e **lido em nenhum** —
    nem no reprovado, que lê `MACED`, outra `Property`. E não traduz a cláusula: a api30 declara
    `macced[output1, inp]`, `[output1, pre_input]`, `[output2, input]` — **aridade 2** — e
    `GENERATED_MAC` guarda só a saída. Precedentes: `WRAPPED_KEY` (decisão 2) e o `ints` (decisão
    10). O produtor de verdade é o elo **#8**, roteado para a **5.7** com a aridade certa no ponto
    de aceitação; migrar a escrita daria à 5.7 um **segundo** produtor para o mesmo elo. O
    `remove(GENERATED_MAC)` acompanha pelo precedente da decisão 11 (a retirada vai com a escrita
    que ela desfaz) — **a 6.4 passa a ter 7 remoções em vez de 8**.
24. **As duas leituras de `GENERATED_KEY` em `i1`/`i2` são APAGADAS.** O `tasks.md` as chama de
    *propagation* e manda registrá-las assim no grafo; a medição discorda do rótulo. No
    `RandomStringPassword` (4.11) uma leitura de propagação **alimenta uma escrita**; aqui
    `i1`/`i2` não escrevem nada — leem um predicado e descartam o veredito, exceto para suprimir a
    transição, e a regra Mac **não exige** `generatedKey` (REQUIRES são `preparedHMAC[params]` e
    os dois `!encrypted`). Apagar e mover-ao-corpo-sem-acusador são **comportamentalmente
    indistinguíveis**; a diferença é código morto e duas linhas de grafo. Os REQUIRES de verdade
    chegam a este mesmo arquivo na **5.2** e na **5.3**. **Esta decisão contradiz o texto da 4.9 —
    ver "Próximo passo".**
25. **O `@match` e o campo `mac` são apagados inteiros.** O handler só carregava
    `setObjectAsInAcceptingState(mac)` (INV-INS-147) e o campo só servia a ele — precedente literal
    da 4.6. A 5.7 recria o handler quando tiver o que escrever, e na aridade 2 sobre `output` e o
    dado, não sobre `mac`, então o campo não é o que ela precisa.

---

## Achados que valem mais que as tarefas

### Continuam valendo (1 a 26: ver o handoff v12 para o texto completo)

Os mais operacionais, repetidos aqui porque a 4.9 depende deles:

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — registrado, não reparado. **A 4.8 achou o
   segundo membro da família (o `@fail` inalcançável do GCM) e a 4.9 achou o terceiro (o `g3*` do
   Mac, ver achado 29).**
3. **`s3` não tem laços `u* -> s3`.** Defeito pré-existente. Grupo 6 / 7.1.
4. **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila** —
   e, desde a 4.8, **que não lança**.
8. **Códigos sem caminho de execução**: já eram nove em três razões; a 4.8 acrescentou
   `GCMPARAMETERSPEC-CONSTR-01` e `-03` (mesma razão: `VIOLATED` na aridade 1 sem posições de
   valor só vem de `negate`, e nenhuma cláusula da api30 retira `randomized`). **São onze.**
12. **Um consumidor que ainda lê em `condition(...)` converte o elo quebrado em silêncio, não em
    relato.** O `GCMParameterSpecSpec` era o caso vivo e fechou na 4.8. **Não resta nenhum.**
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos**, e o veredito
    é **piso, não contagem**. A 4.9 é a demonstração mais forte disso até agora (achado 28).
17. **Um evento inteiro pode não acusar nada, e o censo não mostra.** A 4.8 generalizou: **uma
    especificação inteira pode não acusar nada.**
18. **Quando o corpus não tem trace do sítio, escreva a trace primeiro e meça a semente.** Na 4.8
    as duas traces existentes conformavam por inteiro; na 4.9 nenhuma das quatro configurações
    interessantes existia.
19. **Duas opções indistinguíveis no corpus não são duas opções indistinguíveis.** **Diga sobre o
    que a sua medição é.** A 4.8 tem o caso mais forte já visto do lado "programa": a trace que
    separaria as opções da decisão 19 não pode existir.
20. **O `ere` sem qualificação `after L` põe a escrita no `@match` e pronto.** Confirmado pela 4.8.
21. **Um handler `@match` precisa de campo do monitor, e o campo é o que decide o no-op.**
24. **O parse de um gate é a única coisa que o gate não pode conferir sozinho.**
25. **Um invariante que exige o resultado sem exigir a leitura deixa passar erro de leitura.**
26. **Um teste pode fixar o defeito e ainda assim nomear o risco certo.**

### Novos, da 4.8

27. **Quando uma migração faz um gate reclamar, pergunte primeiro se o gate lê a forma
    pós-migração.** É a segunda vez nesta change (a primeira foi o achado 24, o parser do
    G-ORDER). O `_list_guarding` do G-CONF exigia `event.condition` e procurava a `Arrays.asList`
    só dentro da guarda, então reportava a mesma cláusula **duas vezes, de cada lado**:
    `CRYSL-NAO-IMPLEMENTADO` ("a cláusula da regra não alcança guarda nenhuma") e `MOP-SEM-BASE`
    ("`validLengths` guarda chamadas que cláusula nenhuma alcança"). O **ramo irmão da mesma
    função** já tinha sido corrigido para isso na 3.4, e o comentário dele diz por quê; o ramo de
    pertinência a conjunto ficou para trás porque nenhum arquivo migrado tinha tirado uma **lista**
    da guarda até a 4.8.
28. **Uma guarda que duplica um contrato `@throws` documentado é código morto, e o construtor é
    quem prova.** Um advice `after ... returning` não roda quando a construção lança. Antes de
    mover uma checagem de faixa para o corpo, rode a construção proibida e veja se ela chega ao
    advice.
29. **A mudez pode ser da especificação, não do evento.** O critério: se **todos** os eventos que
    podem acusar estão atrás de guarda **e** o `@fail` é inalcançável, a especificação não tem
    caminho de relato nenhum. O teste barato do `@fail`: leia a tabela de transição no monitor
    gerado e pergunte quantos eventos um monitor pode receber — uma especificação parametrizada
    pelo objeto construído recebe **um**.

### Novo, da 4.9 (medido, ainda não commitado)

30. **O conjunto reprovado pode ser a melhor documentação de um defeito — e ainda assim não ser
    semente.** `jca_android_bug_predicate/CipherSpec.mop:98` explica em uma linha por que
    `GENERATED_MAC` não traduz `macced`: *"MACED is the second place of CrySL's two-place
    macced[M, D]; GENERATED_MAC holds the …"*. Foi a fonte que fechou a decisão 23. Cite-o como
    registro, nunca copie dele.
31. **Um rótulo do `tasks.md` pode estar errado, e a medição é quem descobre.** A 4.9 chama
    `i1`/`i2` de *propagation*; propagação é ler um predicado **e escrever outro** (é o que o
    `RandomStringPassword.vo` faz). `i1`/`i2` não escrevem nada. **Antes de implementar um rótulo
    do plano, confira o que o sítio faz.**
32. **Uma guarda pode transformar um programa conforme num acusado.** Medido no `MacSpec`:
    algoritmo seguro + chave que nenhum gerador observado produziu ⇒ `MAC-ORDER-00`. A regra Mac
    não exige `generatedKey`, então o programa não quebra cláusula alguma; a guarda suprime o
    `init`, o `doFinal` chega num estado inadmissível, e o arquivo acusa **ordenação**. É o falso
    positivo espelho do achado 17: lá a guarda calava, aqui ela inventa.

### Três defeitos de pipeline, fora do escopo desta change — **relatório escrito, decisão pendente**

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). D1: o caminho de experimento não fornece `ANDROID_SDK_HOME` e o
GATOR morre (conhecido desde a gh91, impacto total). D2: a análise estática mira `resources/jca`
mesmo sob `--specification-set jca_android` (bloqueador B4 do `experimento-gh104/CONTEXTO.md:147`;
zero impacto neste corpus, mas **interage com o Grupo 5** — as junction specs nascem só no
`jca_android`). D3: o INV-EXP-16 não é aplicado, e um APK sem `.apk.json` roda assim mesmo (achado
da 4.3; é o multiplicador que converte D1 em run silenciosamente degradado).

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.**

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21, depois da 4.8)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **5** | 0 |
| leituras em corpo | 0 | **13** | todas |
| escritas em corpo de evento | 42 | **27** | 0 sem razão registrada |
| escritas no ponto de aceitação | 7 | **11** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **19** | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **17** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **84** | — |
| achados dos gates estruturais | — | **71** (G-PRED2 25, INV-INS-130 17, INV-INS-133 5, INV-INS-134 24) | 0 |
| traces do corpus | 63 | **91** (89 commitadas + 2 da 4.9 **não rastreadas**) | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 89 traces commitadas contra `backup/gh105-preimage/jca_android`: **60
inalteradas, 17 movidas, 7 introduzidas, 5 removidas** (cumulativas contra a pré-imagem). Das 7
`introduced`, quatro são da 4.8 (o reparo da mudez), duas do `c2` de 3 argumentos da 4.7, e uma é
o `SecretKeySpecSpec` — a **única janela F2 ainda aberta**, que fecha na 4.10.

Com as 91 (incluindo as duas da 4.9, ainda sem edição no `.mop`): **62 / 17 / 7 / 5**.

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.9-4.14 são pré-change e estão desatualizados.** Esta tabela
saiu do `predicate_graph.csv` em 2026-08-21, depois da 4.8. Reconfira com `--emit` antes de citar
qualquer número numa evidência.

| arquivo | `read:condition` | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove` | tarefa |
|---|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 0 | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 0 | 1 | 2 | 3 | 0 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 0 | 2 | 1 | 0 | 0 | 1 (`negate`) | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.7 |
| `GCMParameterSpecSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.8 |
| `MacSpec.mop` | 2 | 0 | 2 | 0 | 1 | 1 | **4.9** |
| `SecretKeySpecSpec.mop` | 0 | 1 | 0 | 1 | 1 | 0 | 4.10 |
| `RandomStringPassword.mop` | 2 | 0 | 2 | 0 | 0 | 0 | 4.11 |
| `SecretKeySpec.mop` | 1 | 0 | 1 | 0 | 0 | 0 | 4.12 |
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

## Próximo passo: 4.9 — `MacSpec` — **medida, decidida, não implementada**

### Ordem de execução (não invente outra)

**Passo 1 — os artefatos, pela skill, ANTES de qualquer código.** A decisão 24 contradiz o texto
da tarefa. Invoque `openspec-update-change` e leve **dois** sítios (o precedente do achado 18: só a
tarefa deixaria o contrato sem exigir o certo):

| artefato | o que muda |
|---|---|
| `tasks.md` **4.9** | as leituras de `i1`/`i2` **não** são *propagation* e **não** são registradas no grafo: são apagadas, porque não alimentam escrita nenhuma e a regra Mac não exige `generatedKey`. As duas escritas de `GENERATED_MAC` são apagadas (decisão 23) e o `remove` do `@fail` vem junto. O `@match` e o campo `mac` somem (decisão 25) |
| `tasks.md` **6.4** | passa de **8** para **7** remoções; `MacSpec.mop:99` sai da lista de sítios |
| `tasks.md` **6.5** | já registra que a 4.6 levou uma das nove; acrescentar que a 4.9 levou outra, pelo mesmo critério |
| `specs/instrumentation/spec.md` **INV-INS-142** (`:338-341`) | "The eight `@fail` removals" vira sete, com a razão |
| `specs/instrumentation/spec.md` `:335`, `:669-671` | a lista de leituras *propagation* nomeia `RandomStringPassword.vo/gb` e `SecretKeySpec.e1` — **`MacSpec.i1/i2` não estão lá**, então provavelmente nada muda; **confira e diga que conferiu** |

**Passo 2 — a edição do `.mop`.** Segue a receita por tarefa abaixo. O arquivo é
`$SPECS/jca_android/MacSpec.mop`. Depois das três decisões o arquivo **não nomeia predicate
nenhum**: sem leituras, sem escritas, sem `remove`, sem `@match`. O INV-INS-130 vai a zero para
ele e o `predicate_graph.csv` perde **6** linhas (84 → 78). Diga isso na evidência — é a primeira
passagem do grupo que **remove** um arquivo inteiro do grafo, e um leitor que olhar só o censo vai
achar que a tarefa não fez nada (achado 9, na forma mais extrema).

**Atenção:** o `i1`/`i2` mantêm o corpo (o relato `MAC-ALG-00`/`-01`), o `q(...)` e o
`ConscryptAliasTable`. O que sai é a `condition(...)`. E o `import br.unb.cic.mop.Property` só sai
se nada mais o usar — **confira**; o `ConscryptAliasTable` e o `ErrorType` ficam.

**Passo 3 — o resto do ciclo**: `codes.csv` (as linhas de `MacSpec` mudam de `file_line`!),
grafo `--emit`, `divergence_record.py --check` + registro dos hunks, harness, baseline `--write`,
censos do pytest, evidência, quatro suítes, commit, checkbox.

### O que já está medido (não repita — custou dois harness e duas sondas)

**As duas traces já estão escritas em disco e NÃO estão no git:**
`data/gh104/traces/MacSpec-unsafe-generated-key.txt` e `MacSpec-ungenerated-key.txt`.
Confira que existem (`ls data/gh104/traces/MacSpec*` deve dar 5) antes de tudo. Se sumiram, os
conteúdos estão descritos abaixo e nos comentários que elas mesmas carregam.

**A regra api30** (`MetaCrySL/generated/api30/Mac.cryptsl`):

```
ORDER        Gets, Inits, (Finals | (Updates+, Finals))            :67
CONSTRAINTS  macAlg in {…12 valores…}; offset < len;
             length(output1) > outOffset;                          :71-75
REQUIRES     preparedHMAC[params];                                 :80
             !encrypted[output1, _];  !encrypted[output2, _];       :82-84
ENSURES      macced[output1, inp]; macced[output1, pre_input];
             macced[output2, input];                                :89-93
```

`generatedKey` **não aparece**. Os três REQUIRES são os elos **#21** (5.2), **#22** e **#23**
(5.3); o ENSURES é o elo **#8** (5.7).

**A contagem sobre o `ErrorCollector` inteiro** (sonda `MacProbe`, os dois lados do scratch,
resultados idênticos porque o `MacSpec.mop` é byte-idêntico na pré-imagem e no HEAD):

| configuração | hoje | previsto depois da 4.9 |
|---|---|---|
| algoritmo seguro + chave gerada | 0 | 0 |
| algoritmo seguro + **chave não gerada** | **1 — `MAC-ORDER-00` @f1** | **0** — falso positivo removido |
| **algoritmo inseguro** + chave gerada | 3 — `MAC-ORDER-00` @i1, **`MAC-ALG-00` @i1**, `MAC-ORDER-00` @f1 | 3, iguais |
| **algoritmo inseguro + chave não gerada** | **1 — `MAC-ORDER-00` @f1** | **2 — `MAC-ALG-00` @i1 + `MAC-ORDER-00`** |

Linha 2 é o achado 32: um programa que não quebra cláusula alguma é acusado de ordenação.
Linha 4 é o achado 17 na forma acusatória: o defeito real (algoritmo inseguro) é invisível e o que
sai é a mesma acusação errada. **As duas linhas são reparos, e nenhuma aparecia no corpus antes
das duas traces.**

**O harness escondeu o principal.** Na linha 3 ele mostrou **um** envelope (`MAC-ORDER-00 ev=i1`)
onde a sonda contou **três** — a mesma chamada de dispatcher emite o relato do corpo e o da
transição, e `TraceRunner.envelope()` devolve o primeiro do `Set`. **Não conclua "MAC-ALG-00 não
dispara" a partir do relatório do harness.** (achado 14 / aprendizado 3.)

**Confirme o previsto com a sonda depois de editar** — a previsão da linha 4 depende de o `g3*`
do `ere` continuar sem levar a lugar nenhum, e isso não foi medido do lado editado.

### O `g3*` que não leva a lugar nenhum — registrar, não reparar

`ere : (g3* g1 | g3* g2) (i1 | i2) ((f1 | f2) | (update* (f1 | f2)))`. Com um algoritmo inseguro
**só** o `g3` dispara, e `g3*` exige um `g1`/`g2` depois — que nunca vem. Então **todo** uso de
algoritmo inseguro termina em `MAC-ORDER-00`, independentemente do resto. É o terceiro membro da
família do achado 1 (o sumidouro `unsafeAlg` do `CipherSpec`) e o segundo do achado 2 (a guarda do
`g2`). **Não é da 4.9**: é do autômato, e a 4.9 não move símbolo — o `MacSpec` é um dos treze
ainda ausentes do `order_alphabet_map.csv`, que a 7.1 possui, então o G-ORDER o pula. Registre na
evidência e nomeie como candidato à mesma tarefa que o achado 1 e o 21 da 4.8 pedem.

### Depois da 4.9

4.10 a 4.14 são um passo por arquivo, paralelizáveis por subagente. A **4.10 (`SecretKeySpecSpec`)
fecha a última janela F2 aberta**. A 4.15 fecha o grupo (gates de colocação verdes, baselines
aposentadas pelo bloco `retired`) e a 4.16 roda `/rv-test-run tests/parity`. Só então o Grupo 5,
que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.8)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20). **E confira
   a aridade da cláusula contra a aridade da `Property`** — foi isso que decidiu a 4.9.
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   Se o corpus não tiver trace do sítio, **escreva a trace e meça a semente** (achado 18). E
   **audite a sonda**: rode um controle que sabidamente acusa no mesmo carregador de classes, e
   liste os dispatchers que ela encontrou. Zero só é evidência se o controle não for zero.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string. **E não ponha comentário entre o `ere` e o primeiro `@`** (aprendizado 43).
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. As linhas se deslocam quando o comentário cresce — reconfira **todos** os
   `file_line` do arquivo, não só os novos. **Preserve a ordem do arquivo**: agrupado por
   especificação, e dentro dela por `file_line` (aprendizado 44).
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato, as linhas ficam como estão
   — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade. **Fora da janela, meça o lado satisfaz de
   verdade** (a 4.8 mediu: as duas construções conformes ficam mudas dos dois lados, que é como se
   parece uma cadeia fechada). Se as traces já existirem de uma tarefa do Grupo 3, não as
   reescreva.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo
   ("This hunk absorbs the reason of the retired `<digest>`: …"), com a coluna `task` acumulando.
   O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`. **Anexe as linhas novas no
   fim, na ordem do arquivo `.mop`, e não reordene o resto** (aprendizado 44). **Chaveie por
   `(file, hunk)`, nunca só por `hunk`** (aprendizado 45).
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class` — **e lembrar que é piso, não contagem**.
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
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)
- Gramáticas: `rv-monitor/rv-monitor/src/main/javacc/.../logicpluginshells/fsm/parser/FSMParser.jj`
  (o `alias`), `rv-monitor/plugins_logicrepository/ere/.../FSM.java:85` (o alias único do ERE),
  `rv-monitor/rv-monitor/src/main/java/.../logicpluginshells/fsm/JavaFSM.java:160` (alias → categoria)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: 7.6**)
- `scripts/gh104_gates.py` (**`_list_guarding` em `:783`, reparado pela 4.8**; a extração da
  fórmula em `:316-321`), `gh104_mop_lint.py`, `gh104_divergence_record.py`,
  `gh104_diff_harness.py`, `gh104_message_gate.py`
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (**89 commitadas + as 2 da 4.9 não rastreadas**)
- `data/gh105/evidence/`: `f1-group-three-the-seventeen.md`, `f2-CipherSpec.md`,
  `f2-reach-probe.md`, `f2-IvParameterSpec.md`, `f2-SecureRandomSpec.md`, `f2-PBEKeySpecSpec.md`,
  `f2-PBEParameterSpecSpec.md`, **`f2-GCMParameterSpecSpec.md`**, `f1-order-gate-precedence.md`,
  `reach-probe/`, `f1-IvParameterSpec-report-count.md`, `f1-PBEParameterSpecSpec-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
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

# sonda de contagem sobre o ErrorCollector inteiro (as receitas completas estão nas evidências
# da 4.7 e da 4.8; a da 4.9 chama KeyGeneratorSpec_g1Event/gk1Event antes do Mac)
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
javac -nowarn -cp "$CP" -d <dir> Probe.java
java -cp "<dir>:$CP" Probe <rótulo> <scratch>/<lado>/work/classes/classes

# build do reator Java (JDK 21 no prefixo; recurso serializado) — ~50 s
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
mvn -o test -pl rvsec-core,rvsec-mop -DskipMopAgent
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

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda.
2. **E o critério de qual absorção é a regra**, não o formato do autômato.
3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
   `TraceRunner.envelope()` devolve o primeiro erro do `Set` por chamada de dispatcher. **A 4.9 é
   o caso mais forte: 1 envelope contra 3 relatos.**
4. **Um órfão pode suprimir o achado, não só somar ruído.** **E uma guarda pode suprimir o evento
   inteiro (4.7), a especificação inteira (4.8), ou inventar um falso positivo (4.9).**
5. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` → `PKIX`.
6. **O digest de hunk é do conteúdo.** Terminar o `.mop` antes de sincronizar `codes.csv`.
7. **`openspec validate` não aceita `--change`** — a sintaxe é `openspec validate <nome>`.
8. **`csv.writer` escreve `\r\n` por padrão.** `divergence_record.csv` **é** CRLF (preserve);
   `gate_allowlist.csv`, `predicate_graph.csv` e `codes.csv` são LF (`lineterminator="\n"`).
9. **Dois hunks com as mesmas linhas mudadas colidem num digest** — mas o registro é chaveado por
   `(file, hunk)`. O hunk do import (`c9fe4844152e`) é literalmente o mesmo em todo arquivo migrado.
10. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30`. Congelado; o leitor pula com motivo.
11. **`TraceRunnerTest` tem 2 falhas pré-existentes.** Verificado com `git stash`. Não é regressão.
12. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (mtime do
    `lib/gator/rvsec-analysis-client.jar`). É o tripwire funcionando.
13. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
14. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. A árvore tem **muita** modificação
    pré-existente não relacionada — **stage por caminho explícito**, nunca `git add -A`.
15. **A baseline precisa ser reescrita quando um achado é reparado**, não só quando um sítio muda
    de chave. O `--write` preserva `retired`. **Mas o G-ORDER é chaveado por
    `(conjunto, arquivo, "order")` e não guarda testemunha.**
16. **O `ere` suporta `*`, `+`, `|` e agrupamento.** Mas laço não avança o autômato.
17. **O corpo do evento roda antes do `handleEvent`**, e o handler de estado dispara a cada evento
    cujo `nextstate` cai no estado — inclusive laços.
18. **Um handler de ponto de aceitação precisa se chamar `@match<N>`** —
    `_ACCEPTANCE_HANDLERS = ^@match\d*$` no `gh105_predicate_graph.py`.
19. **`PredicateStore.validateAbsent` é name-only** (`:339`): ignora as posições de valor.
20. **`c.init(1, null)` não compila** (ambíguo).
21. **Quando escritas viram handler compartilhado, N sítios viram 1 linha no grafo.**
22. **Os censos de `tasks.md` para o Grupo 4 estão desatualizados.** Use a tabela deste documento.
23. **`ANDROID_SDK_HOME` precisa estar exportado** para qualquer run no host.
24. **Nem toda ferramenta alcança o `Cipher.init` do `cryptoapp`.** `aperv:sata_mop` 300 s alcança
    de forma confiável, `ape` 60 s é estocástico, `monkey` não chega lá em 600 s.
25. **`results/` é ignorado pelo git.** Evidência de dispositivo tem que ser copiada.
26. **O `lib_tmp/` da raiz é velho e não é o que a instrumentação usa.**
27. **Uma sonda com uma pergunta binária não é auditável.** As três camadas da 4.3 são o que
    permitiu ler o primeiro run como "inconclusivo". **E uma sonda que mede zero precisa de um
    controle que meça diferente de zero, no mesmo carregador** (4.8).
28. **`gh105_gate_baseline.py` e `gh105_predicate_graph.py` saem com código 1 quando há achados.**
    Comandos separados.
29. **Um código pode ser escrito sabendo que nada o executa**, desde que a razão esteja registrada.
    **Já são onze**, em três razões distintas.
30. **Ao medir com `grep` sobre os cinco conjuntos, diga onde os acertos caíram.**
31. **Quando as traces do par já existem de uma tarefa do Grupo 3, não as reescreva.**
32. **O gate do INV-INS-130 conta menções em comentário e string, não só em código.**
33. **`alias match<N> = <estado>` tem efeito no G-ORDER, não só na colocação.** **Rode o G-ORDER
    antes e depois, sempre.**
34. **O `carry_judgments` do grafo casa linhas por `(file, event, predicate, kind, ordinal)`.**
35. **`condition(...)` é compilado para dentro do `Prop_N_event_X` do monitor gerado**, e vira
    `if (!(guarda)) return false;` **antes** do `handleEvent`.
36. **Migrar um produtor tem efeito em todo consumidor não migrado.** **E ao migrar um consumidor,
    meça se a janela que ele fecha era visível.**
37. **A sonda de contagem tem de chamar todos os dispatchers da aridade certa.**
38. **O `ErrorCollector` tem `reset()`** — dá para medir várias construções num processo só.
    **Mas `getErrors()` devolve um `Set` chaveado por `ErrorSummary`: relatos idênticos se
    fundem.** Se duas construções da mesma sonda podem gerar o mesmo envelope, resete entre elas.
39. **O `ErrorDescription` carrega o envelope em `getExpecting()`**, não em `toString()`.
40. **Uma trace precisa de objetos ligados em silêncio** (`bind x = new ...`) quando o construtor
    dispararia eventos de outra especificação no envelope desta.
41. **O `ORDER` do CrySL tem a vírgula como operador MAIS FRACO** (`CrySL.xtext:103-120`). O
    `gh105_order_gate.py` lê ao contrário. **Reparo na 7.1; até lá, não use `parse_expression`
    para responder pergunta sobre a `ORDER` da `Cipher`.**
42. **`difference_witness` é simétrico.** Para saber **quem** aceita, chame `accepts` nos dois.

### Novos, da 4.8

43. **Não ponha comentário entre a linha do `ere` e o primeiro `@handler`.** `parse_mop`
    (`gh104_gates.py:316-321`) toma como fórmula tudo entre `ere :` e a próxima linha que começa
    com `@` ou `alias`, então um bloco de comentário ali vira `undeclared-symbol` **por palavra**
    — 67 achados de uma vez. Ponha o comentário **acima** do `ere` (é onde ele costuma pertencer,
    já que fala do autômato) ou dentro do corpo do handler. **Registrado e não reparado**: o
    conserto é de uma linha no linter e pertence a quem for dono daquele script.
44. **Não reordene `codes.csv` nem `divergence_record.csv`.** Nenhum dos dois está ordenado: o
    `codes.csv` é agrupado por especificação e, dentro dela, por `file_line`; o
    `divergence_record.csv` **anexa** as linhas da gh105 no fim, com a coluna `task` acumulando
    (`8.1;4.8`). Um `sort` produz um diff de 150 linhas que esconde a mudança real.
45. **`git diff` sem `--cached` compara com o índice, não com o HEAD.** Se você já deu `git add`
    numa versão anterior, o `--stat` mente sobre o tamanho da mudança. `git reset` antes de medir.
46. **O `gh104_message_gate.py` compara os literais inteiros da mensagem com os da guarda.** Se o
    conjunto admitido vive num campo do monitor (`validLengths`), soletrar os números na mensagem
    afirma literais que a guarda não carrega. A forma que o conjunto já usa é a do
    `KeyPairGeneratorSpec`: **nomear a regra** (`exp='a tag length api30 GCMParameterSpec.cryptsl
    admits'`), com o valor observado em `val='...'`, que é runtime e o gate não vê.
