# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 31/74, o Grupo 4 passou da metade)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `ba219f1a`
**Progresso**: 31 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.6 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v9.md` (checkpoint 30/74).

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
Duas dessas passagens já fecharam elos que o plano tinha roteado para o Grupo 5 — a 4.4+4.5
fiaram o #12, a 4.5+4.6 fiaram o #24 —, o que virou a consequência recorrente do grupo.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três; as treze foram levadas em opções com recomendação **e medição**, e
as treze recomendações foram ratificadas. Faça o mesmo — e leve **medição** junto com a opção,
não só argumento. Se a medição disser que duas opções são indistinguíveis, diga isso: é o que faz
a escolha ser preservação literal em vez de mudança comportamental disfarçada. E se a medição
**mata** uma opção (foi o caso da terceira opção da 4.6), apresente a opção morta assim mesmo,
com o número que a matou: é o que separa uma escolha de um gosto.

**Formule a pergunta sobre o sítio certo.** Na 4.5 a primeira versão da pergunta soou como
"descartar eventos" quando o que estava em jogo era a linha de escrita dentro do corpo, e o
pesquisador parou a tarefa para pedir explicação. Nomeie o que muda (a chamada `ensure`, o
evento, o estado do autômato) antes de oferecer opções, e diga explicitamente o que **não** muda.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente (design, Constraints).
Ele aparece legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado
inteiro (INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando
acertar, **diga que acertou e por que não conta**.

**Vocabulário.** Neste projeto "especificação" é o objeto formal (`.mop`/`.rvm`, autômato
paramétrico, monitor tecido), avaliado pela eficácia empírica em achar defeitos no sentido de
Legunsen et al. (ASE'16), de quem o artigo do próprio grupo é continuação. A seção 3 do
`WORKFLOW.md` cita literatura de *spec-driven development* assistido por IA, onde "spec" é o
documento de requisitos que precede a geração de código — **não é o sentido em uso aqui**.

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

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as cinco evidências
que já existem, porque são as cinco formas que uma passagem de arquivo pode ter:

| evidência | a forma |
|---|---|
| `data/gh105/evidence/f2-CipherSpec.md` (4.1/4.2) | a que move tudo |
| `data/gh105/evidence/f2-reach-probe.md` (4.3) | a que vai ao dispositivo |
| `data/gh105/evidence/f2-IvParameterSpec.md` (4.4) | a que não move sítio nenhum |
| `data/gh105/evidence/f2-SecureRandomSpec.md` (4.5) | a que fecha e abre janelas F2 |
| `data/gh105/evidence/f2-PBEKeySpecSpec.md` (4.6) | a que fecha uma cláusula sem ter sido mandada |

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
app sob teste. A 4.4, a 4.5 e a 4.6 já se apoiaram nessa tolerância — se a decisão mudar, os
sítios mudam junto.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 + 4.2, um commit atômico (`d71c8e64`)

`CipherSpec` é o primeiro arquivo migrado, e o mais difícil: 17/17 eventos (headroom zero),
3 leituras, 12 escritas, 1 chamada de estado de aceitação. A tricotomia de origem de chave do
`i2` sai de `condition(...)` para o corpo como **um** sítio composto com veredito de três valores
(`CIPHER-CONSTR-00` para `VIOLATED`, `CIPHER-NOBS-00` para `NOT_OBSERVED`); onze escritas de
`ENCRYPTED` sobem para os **dois** pontos de aceitação; a décima segunda, `WRAPPED_KEY`, foi
apagada. A 4.2 acrescentou a família `NOBS` ao `codes.csv` e uma quinta propriedade ao
`gh104_message_gate.py`.

### 4.3 — a sonda de alcance, commit `4881b557`

**Veredito: a change NÃO está bloqueada. O Grupo 5 está liberado. O weaver não é pré-requisito.**

Três camadas: L1 (`dexdump` sobre o APK instrumentado) ✅ `PredicateStore` em `classes7.dex`,
14 sítios de `Cipher.init` → 14 invocações de `CipherSpec_i2Event`; L2 (`RVSEC-COV` no logcat) ✅;
L3 (`errors.csv`) ✅ **3 linhas `code=CIPHER-NOBS-00 ev=i2`**. Duas execuções: `ape` 60 s deu L1
verde e L2 vermelho — **sonda inconclusiva, que é leitura diferente de change bloqueada**;
`aperv:sata_mop` 300 s alcançou. Evidência: `data/gh105/evidence/f2-reach-probe.md`; artefatos em
`data/gh105/evidence/reach-probe/` (`results/` é ignorado pelo git).

### 4.4 — `IvParameterSpec`, commit `a9d8f2bd` — a passagem que não move sítio nenhum

Primeira passagem em que **o censo de colocação não se mexe**: a 3.3 já tinha trazido as duas
leituras para o corpo, e `preparedIV[this]` não tem qualificação `after L`, então a escrita já
estava no `@match`. Quatro códigos onde havia dois, porque **um código nomeia um sítio, não uma
cláusula** (o `codes.csv` é chaveado por evento e linha).

### 4.5 — `SecureRandomSpec`, commit `a7e97294` — a passagem que fecha e abre janelas

O arquivo com mais menções ao substrato velho (9), o que fecha a cadeia do IV, e o primeiro em que
uma **relocação de escrita tem delta comportamental**. `alias match2 = end`, com os corpos
preparando o objeto em campos do monitor e o handler escrevendo depois da transição. Duas decisões
ratificadas: `next1`/`next3` ficam no corpo com razão registrada (a 5.5 as nomeia); a escrita do
`ints` é apagada com o evento preservado (precedente `WRAPPED_KEY`).

### 4.6 — `PBEKeySpecSpec`, commit `ba219f1a` — a passagem que fecha uma cláusula sem ter sido mandada

Censo de colocação parado outra vez (a 3.5 já tinha trazido as duas leituras do `c1` para o corpo),
e quatro coisas que o censo não vê: substrato, veredito de três valores nas duas leituras, aridade
2 na escrita (`speccedKey[this, keylength]`), e a **espécie da remoção** — o `remove:body` virou
`negate:body`. O `@match` inteiro sumiu (só carregava escrituração) e o campo `spec` com ele.

**O achado da tarefa**: com o `next2` no store novo desde a 4.5, `randomized[salt]` agora responde
`SATISFIED` na trace que randomiza o salt. O elo **#24 do ledger está fiado de ponta a ponta** por
duas passagens de arquivo que nunca foram sobre a cadeia — e a **5.4 herda a mesma consequência
que a 5.1 herdou do #12**: não pode acrescentar um segundo acusador para a mesma cláusula.

Evidência: **`data/gh105/evidence/f2-PBEKeySpecSpec.md`**.

---

## Decisões ratificadas pelo pesquisador

### Na 4.1

1. **As escritas de `ENSURES` aterrissam em handler de estado**, não no corpo com razão
   registrada. O custo que o plano atribuía a essa forma — "vence o último par" — **foi medido e
   não existe**: o despachante recomputa a categoria de estado depois de *todo* evento.
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

9. **`next1`/`next3` ficam no corpo com razão registrada.** O INV-INS-134 admite escrita fora da
   aceitação com razão registrada, e a 5.5 resolve a cláusula com o hub inteiro à frente.
10. **A escrita do `ints` é apagada, o evento fica.** Precedente `CipherSpec.wkb1` exato.

### Na 4.6 (2026-08-21)

11. **A tradução do `remove()` do `clearPassword` vem da 6.5 para a 4.6.** A escrita que ela
    retira troca de substrato nesta passagem; separar as duas deixaria `speccedKey` garantida num
    store e retirada do outro, com a retirada virando no-op no intervalo — uma janela F2 aberta
    dentro de um arquivo só. Medido o outro desfecho: 2 menções residuais, achado INV-INS-130
    sobrevivendo na baseline sem regressão (a chave é `[set, file, subject]`), e a **4.15 passando
    a depender da 6.5**. A 6.5 continua com o outro entregável dela (o `unclosable` do `SecretKey`).
    Delta semântico registrado e sem observador: `negate` **lembra** a retirada (`VIOLATED` depois)
    onde `remove` esquecia (`NOT_OBSERVED`); **zero leitores de `SPECCED_KEY` nos cinco conjuntos**.
12. **A escrita de `speccedKey` fica no corpo do `c1` com razão registrada.** A api30 qualifica a
    cláusula com `after c1` e o arquivo é `ere`: `alias` só existe na gramática do plugin FSM, e o
    plugin ERE emite exatamente um alias — `match`, sobre os estados de aceitação, que aqui é o
    estado **depois do `c2`**, onde a regra NEGA a predicate. A opção literal (`fsm` +
    `alias match1 = <pós-c1>`) foi **medida e recusada**: torna o estado aceitante, e o arquivo
    passa a aceitar `c1` sozinho, que a ORDER da api30 recusa (`('c1',)` → False no DFA do próprio
    gate) — quinta divergência G-ORDER num arquivo verde. Do outro lado: **nenhum programa
    construtível faz a transição do `c1` falhar** para o objeto que ele liga, então corpo e
    pós-`c1` coincidem em toda trace. Terceira opção registrada para quem voltar ao assunto: `fsm`
    com **categoria nomeada que não é alias `match`** (`alias specced` + `@specced`) põe a escrita
    depois da transição sem mexer no conjunto aceitante, ao custo de reescrever o autômato e
    alargar o `_ACCEPTANCE_HANDLERS` do gate.
13. **A leitura sem cláusula também é de três valores.** A leitura de `randomized[password]` não
    está atrás de cláusula alguma da api30 (a 3.5 mediu e preservou a acusação sem reparo), mas
    ganha `PBEKEYSPEC-NOBS-00` ao lado do `CONSTR-01`: acusa as mesmas construções com a mesma
    mensagem, e a mensagem que ela já emitia era a do terceiro valor.

---

## Achados que valem mais que as tarefas

### Continuam valendo

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — `g3` leva a um estado cujas únicas saídas são
   outros `getInstance`. Está no `fsm`, então o G-ACC não o vê e nenhuma tarefa dos Grupos 3-6 o
   alcança. **Registrado, não reparado. Vale tarefa própria.**
2. **A guarda do `g2`** em `TrustManagerFactorySpec`, `SignatureSpec` e `SSLContextSpec` carrega a
   mesma supressão que o `g1` perdeu na fusão. Registrado na 3.6, não reparado.
3. **`s3` não tem laços `u* -> s3`.** Defeito pré-existente. Grupo 6 / 7.1.
4. **Três traces do corpus nomeavam um programa que não compila** (`c.init(1, null)` é ambíguo).
   **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila.**
5. **O dispositivo confirmou o que só o harness tinha mostrado** (4.3): em `CipherUtil.java:54`
   sai `CIPHER-ALG-01 val='DES'` — a acusação que a guarda do `i2` suprimia inteira.
6. **Precisão sobre o que é evidência de quê**: o run da 4.3 também emitiu dois
   `SECRETKEYSPEC-CONSTR-00`, mas esses leem o substrato **velho** (migração é a 4.10).
7. **A aresta #12 do ledger já está fiada por mecanismo A** (4.4 + 4.5). **Consequência que a 5.1
   tem de resolver**: ou estreita o junction à cláusula guardada #9, ou move #12 para o junction e
   tira os acusadores das duas leituras.
8. **`IVPARAMETERSPEC-CONSTR-00`/`-01`, `SECURERANDOM-CONSTR-00` e agora `PBEKEYSPEC-CONSTR-01`
   não têm caminho de execução.** `VIOLATED` na aridade 1 sem posições de valor só vem de
   `negate`, e as duas cláusulas `NEGATES` da api30 não retiram `randomized`. Escrevem-se assim
   mesmo porque o INV-INS-133 exige códigos distintos para a leitura falha e a não observada.
9. **Uma passagem de arquivo pode não mover nada e ainda assim mudar o que o conjunto acusa**
   (4.4 e 4.6). Se você olhar só o censo, conclui que a tarefa não fez nada.
10. **A regra de colocação e o reparo de linguagem podem ser a mesma edição, e só o gate mostra**
    (4.5, o `alias match2 = end` que fechou o `Ends*`). **Antes de aliasar um estado novo, confira
    o que o G-ORDER passa a aceitar.**
11. **A janela F2 tem dois lados, e migrar um produtor abre janelas nos consumidores.** As duas
    `introduced` vivas são `PBEParameterSpecSpec-randomised` (fecha na 4.7) e `SecretKeySpecSpec`
    (fecha na 4.10).
12. **Um consumidor que ainda lê em `condition(...)` converte o elo quebrado em silêncio, não em
    relato.** O `GCMParameterSpecSpec` é o caso vivo; quando a 4.8 mover a leitura para o corpo, a
    janela vai aparecer como relato. **Não leia "inalterado" como "sem consequência" num arquivo
    que ainda tem guarda.**
13. **A identidade do evento acusador pode provar o que a contagem não prova** (4.5, `setSeed2`).
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos.** Leia os
    envelopes em `<scratch>/{a,b}/work/outcomes.json` e nos relatórios por especificação, não só a
    coluna `class`.
15. **O primeiro `SATISFIED` da change apareceu sem tarefa que o pedisse** (4.5, metade do #33).

### Novos, da 4.6

16. **Uma janela F2 pode abrir e fechar sem nunca aparecer na coluna `class`.** A 4.5 fez o
    `PBEKeySpecSpec` acusar o salt (`CONSTR-02`) numa trace que randomiza o salt — porque o
    produtor tinha mudado de store e o consumidor não. O harness classificou `moved` nos dois
    momentos, porque o arquivo já acusava por outro motivo. **Só o envelope mostrou**, e a
    diferença entre as duas execuções do harness (`git diff` no relatório por especificação) é o
    instrumento mais barato para ver isso.
17. **O `ere` não tem como nomear o estado que segue um evento.** `alias` é construto do plugin
    FSM (`rv-monitor/rv-monitor/src/main/javacc/.../logicpluginshells/{fsm,tfsm}/parser/FSMParser.jj`);
    o plugin ERE emite exatamente um alias, `match`, sobre os estados de aceitação
    (`rv-monitor/plugins_logicrepository/ere/.../FSM.java:85`). Nenhum dos 64 arquivos `ere` do
    universo tem alias. **Uma cláusula `ENSURES ... after L` num arquivo `ere` não tem ponto de
    aceitação endereçável** — ou o autômato vira `fsm`, ou a escrita fica no corpo com razão.
18. **`alias` no plugin FSM define categoria nomeada qualquer, não só aceitação.** `JavaFSM.java`
    gera uma propriedade `<nome> condition` para todo alias, e o handler `@<nome>` roda quando ela
    vale. O G-ORDER só lê aliases `match…` para derivar o conjunto aceitante. Isso abre uma forma
    de handler de estado sem mexer na linguagem aceita — usada por ninguém ainda.
19. **Dá para medir o que a ORDER da api30 aceita direto no gate**, sem raciocinar: `read_rule` +
    `expand_aggregates` + `parse_expression` + `nfa_of_expression` + `determinize(nfa, alfabeto)`
    + `accepts(dfa, palavra)`. Foi assim que a opção `alias match1` da 4.6 morreu com número.
20. **A sonda de contagem precisa chamar todos os dispatchers que a chamada resolve.** No lado A
    (pré-imagem) o `c1` tem guarda positiva e não relata nada: quem acusa são os `err*`. Uma sonda
    que chama só o `c1` mede 0 e mente. Chame todo `<Spec>_*Event` da aridade certa.
21. **O `gate_baseline_report.md` em HEAD estava dois checkpoints atrasado.** O JSON estava
    corrente; só o relatório legível não tinha sido reescrito desde a 4.3. Foi regenerado na 4.6.
    **Rode `gh105_gate_baseline.py --write` sempre que um achado for reparado**, não só quando um
    sítio muda de chave — o `--write` preserva `retired`.

### Três defeitos de pipeline, fora do escopo desta change — **relatório escrito, decisão pendente**

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). Resumo:

| # | Defeito | Já conhecido? | Impacto medido |
|---|---|---|---|
| D1 | O caminho de experimento não fornece `ANDROID_SDK_HOME`, e `lib/gator/gator:64` lê a variável com subscrito nu | **Sim**, desde a gh91 | **Total**: `coverage.csv` sem uma linha, `called_methods: 0` |
| D2 | A análise estática mira `resources/jca` mesmo sob `--specification-set jca_android` | **Sim**, bloqueador **B4** do `experimento-gh104/CONTEXTO.md:147` | **Zero neste corpus** — os conjuntos diferem em **um** par (`MessageDigest.reset`) |
| D3 | O INV-EXP-16 não é aplicado: um APK sem `.apk.json` é executado assim mesmo | **Não** — achado da 4.3 | É o multiplicador: converte a falha do D1 em run silenciosamente degradado |

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.** Mas **D2 interage com
o Grupo 5**: as junction specs nascem só no `jca_android`, então cada uma aumenta o delta — e
aumenta exatamente na campanha que vai medir se a gh105 funcionou.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21 após a 4.6)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **8** | 0 |
| leituras em corpo | 0 | **10** | todas |
| escritas em corpo de evento | 42 | **27** | 0 sem razão registrada |
| escritas no ponto de aceitação | 7 | **11** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **21** | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **19** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **86** | — |
| achados dos gates estruturais | — | **77** (G-PRED2 26, INV-INS-130 19, INV-INS-133 8, INV-INS-134 24) | 0 |
| traces do corpus | 63 | **82** | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 82 traces contra `backup/gh105-preimage/jca_android`: **58 inalteradas,
17 movidas, 2 introduzidas, 5 removidas** (cumulativas contra a pré-imagem; os mesmos quatro
números da 4.5 — veja o achado 16 antes de ler isso como "nada mudou"). As duas `introduced` são
`PBEParameterSpecSpec-randomised` (fecha na 4.7) e `SecretKeySpecSpec` (fecha na 4.10).

G-ORDER, as quatro divergências (inalteradas; endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2`), `SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.7-4.14 são pré-change e estão desatualizados**: o Grupo 3 moveu
leituras para o corpo ao fundir gêmeos. Esta tabela saiu do `predicate_graph.csv` em 2026-08-21,
depois da 4.6. Reconfira com `--emit` antes de citar qualquer número numa evidência.

| arquivo | `read:condition` | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove` | tarefa |
|---|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 0 | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 0 | 1 | 2 | 3 | 0 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 0 | 2 | 1 | 0 | 0 | 1 (`negate`) | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 1 | 1 | 0 | 1 | 1 | 0 | **4.7** |
| `GCMParameterSpecSpec.mop` | 2 | 0 | 0 | 1 | 1 | 0 | 4.8 |
| `MacSpec.mop` | 2 | 0 | 2 | 0 | 1 | 1 | 4.9 |
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

## Próximo passo: 4.7 — `PBEParameterSpecSpec`

### O que a tarefa diz, e o que o arquivo diz

`tasks.md`: *"`PBEParameterSpecSpec` (3 reads / 1 write / 1 call); the 3-arg `c2` read gains its
accuser here (`randomized[salt]`)"*. **O censo está desatualizado** — a 3.6 fundiu o `c3` no `c1`.
O estado medido é **1 leitura em `condition(...)` (no `c2`), 1 leitura em corpo (no `c1`), 1
escrita no ponto de aceitação, 1 escrituração**, com **5 menções ao substrato velho**.

A regra api30 (`PBEParameterSpec.cryptsl`) é curta: `EVENTS c1: PBEParameterSpec(salt,
iterationCount)` e o `c2` de três argumentos; `ORDER Cons`; `CONSTRAINTS` sobre o
`iterationCount`; `REQUIRES randomized[salt]`; `ENSURES preparedPBE[this]` — **sem qualificação
`after L`**, então o ponto de aceitação é o estado de aceitação e a escrita já está no `@match`.

Pontos que a 4.7 tem de resolver:

* **É a primeira passagem do Grupo 4 que tira uma leitura de `condition(...)`** desde a 4.1. A do
  `c2` é a última guarda de leitura de predicate fora do `GCMParameterSpecSpec`, do `MacSpec`, do
  `RandomStringPassword` e do `SecretKeySpec`. Tirá-la **muda a transição**: hoje a guarda falsa
  suprime o evento. Meça o delta com o harness e com a sonda de contagem, como a 3.6 fez.
* **A janela F2 desta cadeia fecha aqui.** `PBEParameterSpecSpec-randomised` é uma das duas
  verdicts `introduced` vivas: a 4.5 moveu o `next2` para o store novo e este arquivo ainda lê o
  velho. Depois da 4.7 a trace volta a ficar silenciosa. **Diga na evidência que fechou, e mostre
  o envelope** — a coluna `class` pode não mudar (achado 16).
* **`preparedPBE` é uma das nove predicates `ENSURES`-only** (design, dead-ends): tem produtor no
  conjunto e nenhum leitor, então a escrita fica com **registro de omissão deliberada**
  (INV-INS-137), não com leitor fabricado. O G-PRED2 do arquivo só fecha quando esse registro
  existir — decida se é aqui ou na 5.10 e diga qual.
* **O elo #25 do ledger** (`PBEParameterSpec randomized[salt]`, tarefa 5.4) é o irmão do #24 que a
  4.6 acabou de fiar. Depois de mover a leitura do `c2` para o corpo, **meça se o #25 também fica
  fiado de ponta a ponta** — se ficar, a 5.4 recebe dois elos já resolvidos e vira uma tarefa de
  registro.

### Depois da 4.7

4.8 a 4.14 são um passo por arquivo, paralelizáveis por subagente. A 4.15 fecha o grupo (gates de
colocação verdes, baselines aposentadas pelo bloco `retired`) e a 4.16 roda `/rv-test-run
tests/parity`. Só então o Grupo 5, que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.6)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação. **E se o arquivo for
   `ere`, a resposta pode ser "não existe ponto endereçável"** (achado 17).
2. **Medir o mecanismo no artefato antes de escrever a edição** quando a decisão depender dele.
   A 4.1 leu o monitor gerado; a 4.3 mediu o corpus de runs; a 4.4 mediu que `PREPARED_IV` não tem
   leitor vivo; a 4.5 mediu que nenhuma especificação viva lê `RANDOMIZED` sobre um `int`; a 4.6
   mediu a gramática dos dois plugins e rodou o DFA do próprio gate.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string.
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. As linhas se deslocam quando o comentário cresce — reconfira **todos** os
   `file_line` do arquivo, não só os novos.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa mexer no autômato, **atualize a nota da linha**.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade em vez de assumir. **Fora da janela, meça o
   lado satisfaz de verdade**: foi assim que a 4.6 descobriu o #24 fiado. Se as traces já
   existirem de uma tarefa do Grupo 3, não as reescreva.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason` à mão nas linhas novas.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo
   ("This hunk absorbs the reason of the retired `<digest>`: …"), com a coluna `task` acumulando.
   O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
9. Rodar o harness diferencial (background, ~15 min). Ler os **envelopes** e o `git diff` do
   relatório por especificação, não só a coluna `class`.
10. Conferir e reescrever a baseline (`--write`); ela preserva `retired`.
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também.**
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md`.
13. Rodar as quatro suítes. Commitar (stage por caminho explícito). Marcar o checkbox.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)
- Gramáticas: `rv-monitor/rv-monitor/src/main/javacc/.../logicpluginshells/fsm/parser/FSMParser.jj`
  (o `alias`), `rv-monitor/plugins_logicrepository/ere/.../FSM.java:85` (o alias único do ERE),
  `rv-monitor/rv-monitor/src/main/java/.../logicpluginshells/fsm/JavaFSM.java:160` (alias → categoria)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: 7.6**)
- `scripts/gh104_gates.py`, `gh104_divergence_record.py`, `gh104_diff_harness.py`,
  `gh104_message_gate.py`
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (82 traces)
- `data/gh105/evidence/`: `f1-group-three-the-seventeen.md`, `f2-CipherSpec.md`,
  `f2-reach-probe.md`, `f2-IvParameterSpec.md`, `f2-SecureRandomSpec.md`,
  **`f2-PBEKeySpecSpec.md`**, `reach-probe/`, `f1-IvParameterSpec-report-count.md`,
  `f1-PBEParameterSpecSpec-report-count.md`, `f1-SecretKeySpecSpec-unreachable-constraint.md`,
  `f1-PBEKeySpecSpec-fusion.md`, `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

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

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android

# o que a ORDER da api30 aceita, medido no próprio gate (foi o que decidiu a 4.6)
uv run python -c "
import sys; sys.path.insert(0,'scripts')
from pathlib import Path
import gh105_order_gate as g
r = g.read_rule(Path('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/PBEKeySpec.cryptsl'))
d = g.determinize(g.nfa_of_expression(g.expand_aggregates(g.parse_expression(r.order), r.aggregates)), ('c1','cP'))
print([(w, g.accepts(d, w)) for w in [(), ('c1',), ('c1','cP')]])
"

# gate de mensagens (a quinta propriedade da 4.2 vive aqui)
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# baseline (comparar; --write depois de reparar qualquer achado — preserva `retired`)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS --write

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~15 min) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON (inclusive o "scratch") fica no TOPO da saída
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android --b $SPECS/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f2

# sonda de contagem sobre o ErrorCollector inteiro (a receita está na evidência da 4.6)
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
javac -cp "$CP" -d <dir> Probe.java && java -cp "<dir>:$CP" Probe b <scratch>/b/work/classes/classes

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

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda. Corpo que acusa por conta
   própria → absorve. Corpo que só religa campo → funde.
2. **E o critério de qual absorção é a regra**, não o formato do autômato.
3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
   `TraceRunner.envelope()` devolve o primeiro erro do `Set` por chamada de dispatcher.
4. **Um órfão pode suprimir o achado, não só somar ruído.** Medido na 3.2, na 3.6, na 4.1 e em
   produção na 4.3.
5. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` resolve para
   `PKIX` (`alias_table.csv:2`).
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
    de chave. O `--write` preserva `retired`. (O relatório legível ficou dois checkpoints atrás
    exatamente por isso.)
16. **O `ere` suporta `*`, `+`, `|` e agrupamento.** Mas laço não avança o autômato.
17. **O corpo do evento roda antes do `handleEvent`**, e o handler de estado dispara a cada evento
    cujo `nextstate` cai no estado — inclusive laços.
18. **Um handler de ponto de aceitação precisa se chamar `@match<N>`** —
    `_ACCEPTANCE_HANDLERS = ^@match\d*$` no `gh105_predicate_graph.py`. Mas o gerador aceita
    **qualquer** nome de alias como categoria (achado 18); o gate é que só reconhece `match…`.
19. **`PredicateStore.validateAbsent` é name-only** (`:339`): ignora as posições de valor.
20. **`c.init(1, null)` não compila** (ambíguo).
21. **Quando escritas viram handler compartilhado, N sítios viram 1 linha no grafo.**
22. **Os censos de `tasks.md` para o Grupo 4 estão desatualizados.** Use a tabela deste documento.
23. **`ANDROID_SDK_HOME` precisa estar exportado** para qualquer run no host.
24. **Nem toda ferramenta alcança o `Cipher.init` do `cryptoapp`.** `aperv:sata_mop` 300 s alcança
    de forma confiável, `ape` 60 s é estocástico, `monkey` não chega lá em 600 s.
25. **`results/` é ignorado pelo git.** Evidência de dispositivo tem que ser copiada para
    `data/gh105/evidence/` para sobreviver.
26. **O `lib_tmp/` da raiz é velho e não é o que a instrumentação usa.**
27. **Uma sonda com uma pergunta binária não é auditável.** As três camadas da 4.3 são o que
    permitiu ler o primeiro run como "inconclusivo" em vez de "bloqueado".
28. **`gh105_gate_baseline.py` e `gh105_predicate_graph.py` saem com código 1 quando há achados**,
    o que é correto — mas quebra um encadeamento `cmd && diff && echo OK`. Rode em comandos
    separados.
29. **Um código pode ser escrito sabendo que nada o executa**, desde que a razão esteja registrada.
    Já são sete, em três razões distintas.
30. **Ao medir com `grep` sobre os cinco conjuntos, diga onde os acertos caíram.** O conjunto
    reprovado vai aparecer; filtrar em silêncio produz afirmação falsa.
31. **Quando as traces do par já existem de uma tarefa do Grupo 3, não as reescreva.**
32. **O gate do INV-INS-130 conta menções em comentário e string, não só em código.**
33. **`alias match<N> = <estado>` tem efeito no G-ORDER, não só na colocação.** **Rode o G-ORDER
    antes e depois, sempre** — e antes de declarar um alias novo, **rode o DFA da ORDER** para
    saber o que a regra aceita (o comando está na seção de comandos).
34. **O `carry_judgments` do grafo casa linhas por `(file, event, predicate, kind, ordinal)`.**
    Preencha `clause` na ordem em que as chamadas aparecem no corpo, e não reordene depois.
35. **`condition(...)` é compilado para dentro do `Prop_N_event_X` do monitor gerado**, não para o
    dispatcher `<Spec>_<evento>Event`. Por isso a sonda de contagem e o harness respeitam a guarda.
36. **Migrar um produtor tem efeito em todo consumidor não migrado.** Antes de mover uma escrita de
    `RANDOMIZED`/`GENERATED_*`, liste quem lê aquele `Property` e diga qual tarefa fecha cada
    janela aberta. **E ao migrar um consumidor, meça se a janela que ele fecha era visível** —
    a do `PBEKeySpecSpec` não era (achado 16).
37. **A sonda de contagem tem de chamar todos os dispatchers da aridade certa**, não só o
    sobrevivente da fusão: no lado A quem acusa são os `err*` (achado 20).
38. **O `ErrorCollector` tem `reset()`** — dá para medir várias construções num processo só.

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 4.7.
Leia primeiro docs/handoff/20260821_gh105_apply_prompt_v10.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/ e as cinco evidências do Grupo 4 em
data/gh105/evidence/ (f2-CipherSpec.md, f2-reach-probe.md, f2-IvParameterSpec.md,
f2-SecureRandomSpec.md, f2-PBEKeySpecSpec.md), e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão. A sonda de alcance já
respondeu: a change não está bloqueada e o Grupo 5 está liberado. Os censos por arquivo do
Grupo 4 em tasks.md estão desatualizados — use a tabela do handoff. A 4.7 é a primeira
passagem desde a 4.1 que tira uma leitura de dentro de condition(...), o que muda a
transição, e é onde fecha a janela F2 da trace PBEParameterSpecSpec-randomised; meça se o
elo #25 do ledger fica fiado de ponta a ponta como o #24 ficou na 4.6, porque isso é
consequência para a 5.4. Traga as decisões de projeto ao pesquisador antes de editar, com
medição junto — e se a medição matar uma opção, mostre a opção morta com o número.
```
