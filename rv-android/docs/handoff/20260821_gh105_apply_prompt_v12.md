# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 32/74, com o parser do G-ORDER desmascarado)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `946aad17`
**Progresso**: 32 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.7 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v11.md` (checkpoint 32/74).

> **A sessão anterior não fechou tarefa nenhuma.** Ela foi interrompida antes de editar a 4.8
> para verificar uma afirmação vinda de outra sessão, a afirmação se confirmou, e o achado foi
> registrado em evidência + dois artefatos OpenSpec. O ponto de retomada continua sendo a **4.8**.

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
**Três** dessas passagens já fecharam elos que o plano tinha roteado para o Grupo 5 — a 4.4+4.5
fiaram o #12, a 4.5+4.6 fiaram o #24, a 4.5+4.7 fiaram o #25 —, o que virou a consequência
recorrente do grupo: a 5.1 herdou um elo pronto e a **5.4 herdou dois**.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

A `openspec-update-change` **pede confirmação antes de escrever cada artefato** — isso não é
formalidade: foi por ela que a sessão anterior descobriu que o reparo tinha *dois* sítios
(a tarefa e o invariante) e não um.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 três, a 4.4
duas, a 4.5 duas, a 4.6 três, a 4.7 três; as dezesseis foram levadas em opções com recomendação
**e medição**, e as dezesseis recomendações foram ratificadas. Faça o mesmo — e leve **medição**
junto com a opção, não só argumento. Se a medição disser que duas opções são indistinguíveis,
diga isso. Se a medição **mata** uma opção (4.6) apresente a opção morta assim mesmo, com o
número que a matou. E se a medição só existe depois de você **escrever o instrumento** (4.7:
o corpus não tinha nenhuma trace do construtor de 3 argumentos), escreva o instrumento primeiro
e diga que ele é novo.

**Formule a pergunta sobre o sítio certo.** Nomeie o que muda (a chamada `ensure`, o evento, o
estado do autômato) antes de oferecer opções, e diga explicitamente o que **não** muda. Na 4.7
a pergunta abriu com um parágrafo "o que a tarefa move independentemente de qualquer decisão"
e uma tabela de cinco medições; as três decisões saíram numa rodada só.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente. Ele aparece
legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado inteiro
(INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando acertar,
**diga que acertou e por que não conta** (a 4.7 fez isso na medição de `PREPARED_PBE`).

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

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4** as seis evidências
que já existem, porque são as seis formas que uma passagem de arquivo pode ter:

| evidência | a forma |
|---|---|
| `data/gh105/evidence/f2-CipherSpec.md` (4.1/4.2) | a que move tudo |
| `data/gh105/evidence/f2-reach-probe.md` (4.3) | a que vai ao dispositivo |
| `data/gh105/evidence/f2-IvParameterSpec.md` (4.4) | a que não move sítio nenhum |
| `data/gh105/evidence/f2-SecureRandomSpec.md` (4.5) | a que fecha e abre janelas F2 |
| `data/gh105/evidence/f2-PBEKeySpecSpec.md` (4.6) | a que fecha uma cláusula sem ter sido mandada |
| `data/gh105/evidence/f2-PBEParameterSpecSpec.md` (4.7) | a que descobre um sítio que não acusava nada |

E uma sétima, que não é passagem de arquivo e sim **achado sobre o instrumento**:

| `data/gh105/evidence/f1-order-gate-precedence.md` | o gate lia a gramática ao contrário |

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
app sob teste. A 4.4, a 4.5, a 4.6 e a 4.7 já se apoiaram nessa tolerância — a 4.7 explicitamente:
o `@match` chama `ensure(PREPARED_PBE, spec)` com `spec` nulo quando a construção quebrou uma
cláusula, e é a tolerância que faz disso um no-op. Se a decisão mudar, os sítios mudam junto.

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

Censo de colocação parado outra vez, e quatro coisas que o censo não vê: substrato, veredito de
três valores nas duas leituras, aridade 2 na escrita (`speccedKey[this, keylength]`), e a
**espécie da remoção** — o `remove:body` virou `negate:body`. O `@match` inteiro sumiu (só
carregava escrituração) e o campo `spec` com ele. **O achado**: o elo #24 ficou fiado de ponta a
ponta por duas passagens que nunca foram sobre a cadeia.

### 4.7 — `PBEParameterSpecSpec`, commit `d64f3a40` — a passagem que descobre um sítio mudo

Evidência: **`data/gh105/evidence/f2-PBEParameterSpecSpec.md`** (240 linhas).

A tarefa era tirar a leitura do `c2` de dentro de `condition(...)` — a primeira desde a 4.1 a sair
porque a migração pediu. O que ela achou: **o construtor de três argumentos não acusava nada**.
Nem salt sem randomização, nem contagem abaixo do limite, nem as duas juntas. Medido no monitor
gerado do lado semente:

```java
final boolean Prop_1_event_c2(...) {
    if ( ! (iterationCount >= 10000 && <leitura>) ) { return false; }   // antes do handleEvent
    { spec = s; }
    int nextstate = this.handleEvent(1, Prop_1_transition_c2);
```

contra o `c1`, que roda o corpo e transita sempre. A guarda do `c2` era, **caractere por
caractere, a guarda que o `c1` carregava antes da fusão da 3.6** — ficou lá só porque o `c2` não
tinha gêmeo negado para acusar no lugar dela.

Três decisões ratificadas (ver abaixo). Seis códigos onde havia dois. A janela F2 desta cadeia
fechou (`-randomised.txt` saiu de `introduced` para `unchanged`) e o **elo #25 está fiado de ponta
a ponta**.

### Sessão de verificação, commit `946aad17` — **o gate lia a gramática do CrySL ao contrário**

Nenhuma tarefa fechou. Uma afirmação vinda de outra sessão foi levada à verificação, se confirmou
nas três fontes, e o achado está em **`data/gh105/evidence/f1-order-gate-precedence.md`** (238
linhas, com bloco de reprodução conferido rodando literalmente).

**A afirmação**: o `gh105_order_gate.py` lê o `ORDER` com precedência invertida.

**Confirmada em três sítios.**

1. A gramática. `/home/pedro/tmp/CryptSL/de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext`:
   `Order: Sequence` (:103), `Sequence: Alternative (',' Alternative)*` (:107, `SEQUENCE = ','`
   :112), `Alternative: Cardinality ('|' Cardinality)*` (:115). `Sequence` é a produção mais
   externa, logo a **vírgula é o operador mais fraco**: `a, b | c` é `a, (b | c)`.
2. O gate. `tokenize` (:136) descarta a vírgula (`if token != ","`, :152) e `parse_expression`
   (:160) documenta a própria gramática como `alt := cat ('|' cat)*` (:162) — concatenação mais
   forte. O parser está **certo para o `ere`** (que não tem vírgula) e errado só para a `ORDER`.
3. A suíte fixa o defeito. `tests/parity/test_gh105_predicate_gates.py:1344`,
   `test_the_order_grammar_is_read_with_alternation_weakest`, afirma que `a, b | c` é
   `(a, b) | c` — e o docstring dela raciocina sobre a regra `Cipher` e avisa que a precedência
   errada faria "o gate reportar uma divergência que é artefato do próprio parser". É o que
   estava acontecendo, com o sinal trocado.

**Raio de alcance: uma regra.** Das 33 regras da api30, cinco escrevem `,` e `|`; só a `Cipher`
os deixa **no mesmo nível de parênteses** (`Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+`).
As outras quatro parentetizam cada alternância e os dois parsers concordam nelas. O
`order_alphabet_map.csv` não tem vírgula em nenhuma das 120 células de `order_symbol`.

| sequência | CrySL | gate |
|---|---|---|
| `g1 i2 f2` — getInstance, init, doFinal | **aceita** | **rejeita** |
| `f2` — um `doFinal` sozinho | **rejeita** | **aceita** |

Em palavras de até 3 símbolos as duas linguagens discordam em **795** (715 só o gate aceita).

**Delta medido, trocando o parser por um fiel à gramática**: `passed=6 / findings=4 / skipped=13`
nos dois casos — **exatamente um achado muda, e inverte**:

| | hoje | com o parser fiel |
|---|---|---|
| `CipherSpec` | `` `f2` `` aceito pelo **ORDER api30** | `` `g1 i1 u1` `` aceito pela **especificação** |
| os outros três | — | inalterados |

**A divergência real que isso descobre é a oposta da registrada**: o `ere` do `CipherSpec` aceita
`getInstance → init → update` terminando sem `doFinal`, que a `ORDER` recusa. Um reparo guiado
pela testemunha de hoje teria afrouxado o autômato na direção errada.

**Nada foi reparado.** Decisão do pesquisador: **registrar agora, reparar na 7.1**. Dois artefatos
OpenSpec receberam o achado pela `openspec-update-change`:
- **`tasks.md` 7.1** — o reparo com o delta medido e o ponteiro para a evidência;
- **`spec.md` INV-INS-138** — a cláusula que exige ler o `ORDER` sob a precedência do CrySL. Ela
  **faltava**: o invariante exigia equivalência de DFA sob o mapa de alfabeto e não dizia nada
  sobre o parse. Era esse o buraco pelo qual o defeito passou.

A baseline **não** precisa de `--write`: `gate_baseline.json` chaveia o G-ORDER por
`(conjunto, arquivo, "order")` e não guarda testemunha. Duas linhas ficam obsoletas e a 7.1 as
atualiza: `data/jca_android/evidence/gate_baseline_report.md:68` e o parêntese em
`data/gh105/evidence/f2-CipherSpec.md:96`. Nenhuma decisão ratificada se apoia na testemunha `f2`
— foi conferido.

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

14. **O relato composto do `c1` decompõe por cláusula.** O INV-INS-133 só admite sítio composto
    para probes de *uma* cláusula (o caso vivo é a tricotomia do `CipherSpec.i2`); aqui são duas,
    de duas seções diferentes da regra — a contagem em CONSTRAINTS, o salt em REQUIRES. Com as
    duas metades quebradas não havia código consistente para arquivar o relato. Forma: a que a
    4.6 deu ao arquivo irmão. Delta medido: **uma** construção do corpus muda de contagem
    (`-lowiter`, 1 → 2 relatos).
15. **A guarda do `c2` sai inteira, com a checagem de CONSTRAINTS junto.** O INV-INS-133 permite
    que checagens de CONSTRAINTS fiquem como guarda; aqui não ficou, por duas medições. Deixá-la
    manteria a leitura recém-tirada da guarda **atrás de uma segunda guarda que suprime a mesma
    transição**, e deixaria o arquivo acusando `PBEParameterSpec(bytes, 1000)` e mudo sobre
    `PBEParameterSpec(bytes, 1000, params)`. No corpus de 82 traces as opções são
    **indistinguíveis**; a trace que as separa (`-threearg-lowiter.txt`) foi escrita nesta
    passagem e as separa por 1 relato contra 0. Terceira opção registrada e não tomada: tirar a
    contagem da guarda e deixá-la governar só a escrita, sem relato.
16. **O `preparedPBE` recebe o registro de omissão deliberada aqui, não na 5.10.** É onde o
    design já roteava os onze sítios `ENSURES`-only. Medido: `preparedPBE` aparece **uma única
    vez no oráculo api30 inteiro**, como o ENSURES desta própria regra; `PREPARED_PBE` é escrito
    em três dos cinco conjuntos (`jca`, `jca_android` e o **reprovado**, que o grep acerta e não
    conta) e **lido em nenhum**. É a **primeira `disposition` preenchida** nas linhas do grafo.

### Na sessão de verificação (2026-08-21)

17. **O achado do parser do G-ORDER é registrado agora e reparado na 7.1**, não no Grupo 4.
    Nenhum `.mop` é editado por causa dele; o reparo é do parser, do teste que o fixa e das duas
    linhas de registro que citam a testemunha artefato.
18. **O registro entra em dois artefatos, não em um.** Só a tarefa consertaria o caso e deixaria
    o contrato sem exigir o parse certo — nada impediria a regressão. O INV-INS-138 ganhou a
    cláusula.

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
   sai `CIPHER-ALG-01 val='DES'`.
6. **Precisão sobre o que é evidência de quê**: o run da 4.3 também emitiu dois
   `SECRETKEYSPEC-CONSTR-00`, mas esses leem o substrato **velho** (migração é a 4.10).
7. **A aresta #12 do ledger já está fiada por mecanismo A** (4.4 + 4.5). A 5.1 resolve.
8. **Códigos sem caminho de execução**: `IVPARAMETERSPEC-CONSTR-00`/`-01`, `SECURERANDOM-CONSTR-00`,
   `PBEKEYSPEC-CONSTR-01` e `PBEPARAMETERSPEC-CONSTR-01`/`-03`. `VIOLATED` na aridade 1 sem
   posições de valor só vem de `negate`, e nenhuma cláusula da api30 retira `randomized`.
   Escrevem-se assim mesmo porque o INV-INS-133 exige códigos distintos para a leitura falha e a
   não observada. **Já são nove, em três razões distintas.**
9. **Uma passagem de arquivo pode não mover nada e ainda assim mudar o que o conjunto acusa**
   (4.4 e 4.6). Se você olhar só o censo, conclui que a tarefa não fez nada.
10. **A regra de colocação e o reparo de linguagem podem ser a mesma edição, e só o gate mostra**
    (4.5, o `alias match2 = end`). **Antes de aliasar um estado novo, confira o que o G-ORDER passa
    a aceitar.**
11. **A janela F2 tem dois lados, e migrar um produtor abre janelas nos consumidores.** A do
    `PBEParameterSpecSpec` fechou na 4.7. **Resta uma viva: `SecretKeySpecSpec` (fecha na 4.10).**
12. **Um consumidor que ainda lê em `condition(...)` converte o elo quebrado em silêncio, não em
    relato.** O `GCMParameterSpecSpec` é o caso vivo; quando a 4.8 mover a leitura para o corpo, a
    janela vai aparecer como relato. **Não leia "inalterado" como "sem consequência" num arquivo
    que ainda tem guarda.**
13. **A identidade do evento acusador pode provar o que a contagem não prova** (4.5, `setSeed2`).
14. **O harness classifica pelo conjunto de eventos acusadores, não pelos códigos.** Leia os
    envelopes em `<scratch>/{a,b}/work/outcomes.json` e nos relatórios por especificação.
15. **O primeiro `SATISFIED` da change apareceu sem tarefa que o pedisse** (4.5, metade do #33).
16. **Uma janela F2 pode abrir e fechar sem nunca aparecer na coluna `class`** (4.6). A da 4.7
    apareceu — a diferença é se o arquivo já acusava por outro motivo naquela trace.
17. **Um evento inteiro pode não acusar nada, e o censo não mostra.** O `c2` do
    `PBEParameterSpecSpec` era uma alternativa completa do `ORDER` da regra, com leitura, escrita
    e transição — e zero relatos em qualquer configuração, porque a guarda `return false` levava
    tudo embora antes do `handleEvent`. **Um sítio que o grafo conta como `read:condition-guard`
    pode estar escondendo um evento mudo, não só uma leitura mal colocada.** Antes de migrar um
    arquivo, pergunte de cada evento com guarda: *o que ele acusa hoje, medido?*
18. **Quando o corpus não tem trace do sítio, escreva a trace primeiro e meça a semente.** O
    corpus tinha 0 de 82 traces do construtor de 3 argumentos. Sem escrever as três, a 4.7 teria
    "medido" a decisão como indistinguível e escolhido preservação literal — que era a resposta
    errada, porque o que estava sendo preservado era um silêncio total.
19. **Duas opções indistinguíveis no corpus não são duas opções indistinguíveis.** "Nenhuma trace
    separa as duas" é afirmação sobre o corpus, não sobre o programa. A 4.4 tinha o caso genuíno
    (nenhuma especificação viva lê `PREPARED_IV` — afirmação sobre os cinco conjuntos); a 4.7
    tinha o caso falso. **Diga sobre o que a sua medição é.**
20. **O `ere` sem qualificação `after L` põe a escrita no `@match` e pronto.** A 4.6 e a 4.7 são o
    par que mostra a regra inteira: `speccedKey[this, keylength] **after c1**` num `ere` não tem
    ponto endereçável (fica no corpo com razão), `preparedPBE[this]` sem qualificação tem
    (`@match`). **Leia a qualificação da cláusula antes de decidir onde a escrita vai.**
21. **Um handler `@match` precisa de campo do monitor, e o campo é o que decide o no-op.** O campo
    só é ligado no ramo conforme, então uma construção que quebrou cláusula chega ao handler com
    `null` e o `ensure` é no-op — o que preserva a semântica CrySL sem um `if` no handler. Depende
    da tolerância a `bound == null` do Grupo 1.
22. **A sonda de contagem em três colunas (semente / antes da tarefa / depois) é mais barata e
    mais informativa que duas.** A coluna do meio é a que prova de quem era o silêncio: na 4.7
    mostrou que o `c2` mudo era da guarda e não do substrato, e mostrou a janela F2 crua (salt
    randomizado acusado antes, mudo depois).
23. **O javadoc do `PBEParameterSpecSpec` diz `GCMParameterSpec`** (a semente também:
    `jca/PBEParameterSpecSpec.mop:11`). Não reparado: o recorder de divergência não tem `kind`
    para correção de documentação, e alargar a whitelist é colateral de outra tarefa.

### Novo, da sessão de verificação

24. **O parse de um gate é a única coisa que o gate não pode conferir sozinho.** Surpresa numa
    testemunha é evidência sobre o **leitor** antes de ser evidência sobre o **lido**. Este achado
    já tinha sido visto e explicado errado: o handoff v2 (`20260820_gh105_apply_prompt_v2.md:124`)
    registra "precedência do `|` no ORDER **da regra** deixa `doFinal` sozinho legal" — mecanismo
    certo, culpado errado. **Quando um gate disser algo surpreendente sobre a entrada dele,
    confira o parse contra a gramática da entrada antes de registrar a surpresa como fato.**
25. **Um invariante que exige o resultado sem exigir a leitura deixa passar erro de leitura.** O
    INV-INS-138 exigia equivalência de DFA sob o mapa de alfabeto e não dizia nada sobre como o
    `ORDER` é parseado. Foi por aí. **Ao escrever invariante de gate, exija também como a entrada
    é lida, não só o que é comparado.**
26. **Um teste pode fixar o defeito e ainda assim nomear o risco certo.** O
    `test_the_order_grammar_is_read_with_alternation_weakest` avisa no docstring que a precedência
    errada produziria "uma divergência que é artefato do próprio parser" — e afirma a precedência
    errada. **Um teste com raciocínio certo e asserção invertida é mais difícil de ver que um
    teste sem raciocínio nenhum.**

### Três defeitos de pipeline, fora do escopo desta change — **relatório escrito, decisão pendente**

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). Resumo:

| # | Defeito | Já conhecido? | Impacto medido |
|---|---|---|---|
| D1 | O caminho de experimento não fornece `ANDROID_SDK_HOME`, e `lib/gator/gator:64` lê a variável com subscrito nu | **Sim**, desde a gh91 | **Total**: `coverage.csv` sem uma linha, `called_methods: 0` |
| D2 | A análise estática mira `resources/jca` mesmo sob `--specification-set jca_android` | **Sim**, bloqueador **B4** do `experimento-gh104/CONTEXTO.md:147` | **Zero neste corpus** — os conjuntos diferem em **um** par (`MessageDigest.reset`) |
| D3 | O INV-EXP-16 não é aplicado: um APK sem `.apk.json` é executado assim mesmo | **Não** — achado da 4.3 | É o multiplicador: converte a falha do D1 em run silenciosamente degradado |

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.** Mas **D2 interage com
o Grupo 5**: as junction specs nascem só no `jca_android`, então cada uma aumenta o delta.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **7** | 0 |
| leituras em corpo | 0 | **11** | todas |
| escritas em corpo de evento | 42 | **27** | 0 sem razão registrada |
| escritas no ponto de aceitação | 7 | **11** | todas |
| chamadas de estado de aceitação (INV-INS-147) | 25 | **20** | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| `negate` traduzindo `NEGATES` | 0 | **1** | 1 |
| menções ao substrato velho (INV-INS-130) | 23 arquivos | **18** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **85** | — |
| achados dos gates estruturais | — | **74** (G-PRED2 25, INV-INS-130 18, INV-INS-133 7, INV-INS-134 24) | 0 |
| traces do corpus | 63 | **85** | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 85 traces contra `backup/gh105-preimage/jca_android`: **60 inalteradas,
17 movidas, 3 introduzidas, 5 removidas** (cumulativas contra a pré-imagem). As três `introduced`
são as duas do `c2` de 3 argumentos (o reparo da 4.7) e o `SecretKeySpecSpec`, que é a **única
janela F2 ainda aberta** e fecha na 4.10.

G-ORDER, as quatro divergências (endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2` — **testemunha artefato do parser; a real é `g1 i1 u1`, ver o achado 24**),
`SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.8-4.14 são pré-change e estão desatualizados**: o Grupo 3 moveu
leituras para o corpo ao fundir gêmeos. Esta tabela saiu do `predicate_graph.csv` em 2026-08-21,
depois da 4.7. Reconfira com `--emit` antes de citar qualquer número numa evidência.

| arquivo | `read:condition` | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove` | tarefa |
|---|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 0 | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 0 | 1 | 2 | 3 | 0 | 0 | ✅ 4.5 |
| `PBEKeySpecSpec.mop` | 0 | 2 | 1 | 0 | 0 | 1 (`negate`) | ✅ 4.6 |
| `PBEParameterSpecSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.7 |
| `GCMParameterSpecSpec.mop` | 2 | 0 | 0 | 1 | 1 | 0 | **4.8** |
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

## Próximo passo: 4.8 — `GCMParameterSpecSpec`

### O que a tarefa diz, e o que o arquivo diz

`tasks.md`: *"`GCMParameterSpecSpec` (2 reads / 1 write / 1 call); `c1`/`c2` gain their accusers
(`randomized[src]`)"*. O censo medido bate: **2 leituras em `condition(...)`, 1 escrita no ponto
de aceitação, 1 escrituração**.

O arquivo hoje (`$SPECS/jca_android/GCMParameterSpecSpec.mop`): dois construtores (`c1` de 2
argumentos, `c2` de 4), ambos com `condition(...)` que combina `validLengths.contains(tagLen)`
(CONSTRAINTS) com `ExecutionContext.instance().validate(Property.RANDOMIZED, src)` (a leitura de
predicate) — e o `c2` acrescenta três checagens de faixa. `ere : c1 | c2`. O `@match` escreve
`PREPARED_GCM` e chama `setObjectAsInAcceptingState` (a escrituração que o INV-INS-147 dispensa).

**Este é o arquivo do achado 12**, e o achado 17 da 4.7 acabou de dar a ele um irmão. As duas
leituras estão em guarda; a cadeia `randomized[src]` tem produtor no store novo desde a 4.5; então
**a janela F2 deste arquivo está aberta e é invisível**, porque a guarda converte o elo quebrado
em silêncio em vez de relato. Quando a 4.8 mover as leituras, a janela vira relato.

E note a forma da guarda do `c2`: é exatamente o padrão que a 4.7 encontrou — leitura de predicate
**e** checagens de CONSTRAINTS na mesma `condition(...)`, com `return false` antes do
`handleEvent`. A decisão 15 da 4.7 é o precedente direto; leia-a antes de propor a sua.

Pontos que a 4.8 tem de resolver, e a ordem em que a 4.7 sugere resolvê-los:

* **Meça o que cada evento acusa hoje, antes de editar** (achado 17). O `GCMParameterSpecSpec` é
  o candidato mais provável a um segundo evento mudo: duas leituras em guarda, e o arquivo é a
  **fixture negativa do G-ACC** na sua versão `jca` (`jca/GCMParameterSpecSpec.mop:23,34,48`
  carrega os dois defeitos de alfabeto). A versão `jca_android` foi reparada, mas confira o que
  o `c2` de segunda sobrecarga faz — há trace para ele
  (`GCMParameterSpecSpec-second-overload.txt`).
* **A sonda de contagem em três colunas** (semente / HEAD antes da sua edição / depois). A do
  meio é a que separa "a guarda calava" de "o substrato não tinha o produtor".
* **`preparedGCM` é elo #10 do ledger** (consumidor `Cipher`, tarefa 5.8) e a escrita deste
  arquivo é a produtora. Ela já está no ponto de aceitação; confira a qualificação da cláusula na
  api30 antes de assumir (achado 20).
* **`randomized[src]` é o elo #11** (tarefa 5.4 — a mesma que já herdou #24 e #25). Se a 4.8
  também o fiar de ponta a ponta, a 5.4 fica com **três** elos prontos e vira tarefa de registro.
  Meça e diga.
* **Registro de omissão**: se a escrita de `preparedGCM` tiver leitor no conjunto (o `CipherSpec`
  é o consumidor da regra), o G-PRED2 fecha por leitura, não por omissão. Confira antes de
  repetir o padrão da 4.7.
* **A 4.8 não depende do achado 24.** O `ORDER` do `GCMParameterSpec` não tem vírgula, então o
  parse do gate é o mesmo nos dois mundos. Rode o G-ORDER antes e depois como sempre
  (aprendizado 33) e espere as mesmas quatro divergências.

### Depois da 4.8

4.9 a 4.14 são um passo por arquivo, paralelizáveis por subagente. A 4.15 fecha o grupo (gates de
colocação verdes, baselines aposentadas pelo bloco `retired`) e a 4.16 roda `/rv-test-run
tests/parity`. Só então o Grupo 5, que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.7)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai — e
   se a cláusula tem `after L` ou não, decide **qual** ponto de aceitação (achado 20).
2. **Medir o que cada sítio acusa hoje**, com a sonda de contagem, **antes** de escrever a edição.
   Se o corpus não tiver trace do sítio, **escreva a trace e meça a semente** (achado 18).
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro. E **não escreva a
   palavra do substrato velho nem em comentário** — o gate do INV-INS-130 conta menções em
   comentário e string.
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. As linhas se deslocam quando o comentário cresce — reconfira **todos** os
   `file_line` do arquivo, não só os novos.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped`. Se a tarefa não mexer no autômato (4.7 não mexeu), as linhas
   ficam como estão — e diga isso na evidência.
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade. **Fora da janela, meça o lado satisfaz de
   verdade.** Se as traces já existirem de uma tarefa do Grupo 3, não as reescreva.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois). Preencher
   `clause`/`mechanism`/`reason`/`disposition` à mão nas linhas novas.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo
   ("This hunk absorbs the reason of the retired `<digest>`: …"), com a coluna `task` acumulando.
   O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
9. Rodar o harness diferencial (background, ~13 min). Ler os **envelopes** e o `git diff` do
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
- `data/gh104/traces/` (85 traces)
- `data/gh105/evidence/`: `f1-group-three-the-seventeen.md`, `f2-CipherSpec.md`,
  `f2-reach-probe.md`, `f2-IvParameterSpec.md`, `f2-SecureRandomSpec.md`, `f2-PBEKeySpecSpec.md`,
  `f2-PBEParameterSpecSpec.md`, **`f1-order-gate-precedence.md`**, `reach-probe/`,
  `f1-IvParameterSpec-report-count.md`, `f1-PBEParameterSpecSpec-report-count.md`,
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

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 94 passando, ~83 s
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
# ATENÇÃO: para uma regra cujo ORDER tem `,` e `|` no mesmo nível de parênteses (só a Cipher),
# este comando responde sob o parse ERRADO. Use o bloco de reprodução de
# data/gh105/evidence/f1-order-gate-precedence.md. Reparo na 7.1.

# gate de mensagens (a quinta propriedade da 4.2 vive aqui)
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

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

# sonda de contagem sobre o ErrorCollector inteiro (a receita completa está na evidência da 4.7)
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)
javac -nowarn -cp "$CP" -d <dir> Probe.java
java -cp "<dir>:$CP" Probe <rótulo> <scratch>/<lado>/work/classes/classes
# rode nos TRÊS lados: a (semente), b do scratch anterior (HEAD antes da sua edição), b do novo

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
   `TraceRunner.envelope()` devolve o primeiro erro do `Set` por chamada de dispatcher.
4. **Um órfão pode suprimir o achado, não só somar ruído.** Medido na 3.2, na 3.6, na 4.1 e em
   produção na 4.3. **E uma guarda pode suprimir o evento inteiro** (4.7).
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
    `(conjunto, arquivo, "order")` e não guarda testemunha** — mudar a testemunha não pede
    `--write`.
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
    permitiu ler o primeiro run como "inconclusivo" em vez de "bloqueado".
28. **`gh105_gate_baseline.py` e `gh105_predicate_graph.py` saem com código 1 quando há achados**,
    o que é correto — mas quebra um encadeamento `cmd && diff && echo OK`. Comandos separados.
29. **Um código pode ser escrito sabendo que nada o executa**, desde que a razão esteja registrada.
    **Já são nove**, em três razões distintas.
30. **Ao medir com `grep` sobre os cinco conjuntos, diga onde os acertos caíram.** O conjunto
    reprovado vai aparecer; filtrar em silêncio produz afirmação falsa.
31. **Quando as traces do par já existem de uma tarefa do Grupo 3, não as reescreva.**
32. **O gate do INV-INS-130 conta menções em comentário e string, não só em código.**
33. **`alias match<N> = <estado>` tem efeito no G-ORDER, não só na colocação.** **Rode o G-ORDER
    antes e depois, sempre.**
34. **O `carry_judgments` do grafo casa linhas por `(file, event, predicate, kind, ordinal)`.**
    Preencha `clause` na ordem em que as chamadas aparecem no corpo, e não reordene depois.
35. **`condition(...)` é compilado para dentro do `Prop_N_event_X` do monitor gerado**, não para o
    dispatcher `<Spec>_<evento>Event`, e vira `if (!(guarda)) return false;` **antes** do
    `handleEvent`. Por isso a sonda e o harness respeitam a guarda — e por isso um evento com
    guarda pode ser inteiramente mudo (4.7).
36. **Migrar um produtor tem efeito em todo consumidor não migrado.** Antes de mover uma escrita de
    `RANDOMIZED`/`GENERATED_*`, liste quem lê aquele `Property` e diga qual tarefa fecha cada
    janela aberta. **E ao migrar um consumidor, meça se a janela que ele fecha era visível.**
37. **A sonda de contagem tem de chamar todos os dispatchers da aridade certa**, não só o
    sobrevivente da fusão. No lado semente do `PBEParameterSpecSpec` são dois para a sobrecarga de
    2 argumentos (`c1` e o gêmeo `c3`) e um para a de 3.
38. **O `ErrorCollector` tem `reset()`** — dá para medir várias construções num processo só, e é o
    que faz a sonda de três colunas caber num comando.
39. **O `ErrorDescription` carrega o envelope em `getExpecting()`**, não em `toString()`; não
    existe `getExpectedValue()`.
40. **A trace de 3 argumentos precisa de um `AlgorithmParameterSpec` ligado em silêncio**:
    `bind params = new IvParameterSpec(bytes(16))` cria o objeto sem disparar os eventos do
    `IvParameterSpec`, que poriam relatos de outra especificação no envelope desta.
41. **O `ORDER` do CrySL tem a vírgula como operador MAIS FRACO** (`CrySL.xtext:103-120`), ao
    contrário da convenção de regex. O `gh105_order_gate.py` lê ao contrário e por isso a
    testemunha do `CipherSpec` é artefato dele. **Reparo na 7.1; até lá, não use
    `parse_expression` para responder pergunta sobre a `ORDER` da `Cipher`** — é a única regra da
    api30 em que os dois parses divergem. `data/gh105/evidence/f1-order-gate-precedence.md`.
42. **`difference_witness` é simétrico** — devolve a menor palavra em que os dois autômatos
    discordam, em qualquer direção. Para saber **quem** aceita, chame `accepts` nos dois.

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 4.8.
Leia primeiro docs/handoff/20260821_gh105_apply_prompt_v12.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/ e as evidências do Grupo 4 em data/gh105/evidence/
(f2-CipherSpec.md, f2-reach-probe.md, f2-IvParameterSpec.md, f2-SecureRandomSpec.md,
f2-PBEKeySpecSpec.md, f2-PBEParameterSpecSpec.md, e f1-order-gate-precedence.md), e siga
docs/WORKFLOW.md rigorosamente — invoque a skill openspec-apply-change, não escreva
artefatos à mão. A sonda de alcance já respondeu: a change não está bloqueada e o Grupo 5
está liberado. Os censos por arquivo do Grupo 4 em tasks.md estão desatualizados — use a
tabela do handoff. A 4.8 é o GCMParameterSpecSpec, o arquivo com as duas últimas leituras
em condition(...) de uma cadeia cujo produtor já migrou: meça o que cada evento acusa hoje
antes de editar, porque a 4.7 descobriu que uma guarda pode calar um evento inteiro e o
censo não mostra isso, e a guarda do c2 aqui tem exatamente a forma que a 4.7 encontrou
(leitura de predicate junto com checagens de CONSTRAINTS, com return false antes do
handleEvent) — leia a decisão 15 da 4.7 antes de propor a sua. Meça também se o elo #11 do
ledger fica fiado de ponta a ponta, porque a 5.4 já herdou o #24 e o #25 e não pode
acrescentar um segundo acusador para nenhum deles. Traga as decisões de projeto ao
pesquisador antes de editar, com medição junto — e diga sobre o que a sua medição é:
"nenhuma trace separa as duas opções" é afirmação sobre o corpus, não sobre o programa.
O achado 24 (o parser do G-ORDER lia a gramática do CrySL ao contrário) está registrado e
roteado para a 7.1 — não o repare na 4.8, e não se assuste com a testemunha `f2` do
CipherSpec no G-ORDER: ela é artefato do gate, não da regra.
```
