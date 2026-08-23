# F3 — a chamada que valia por dois eventos, e a tarefa que já estava feita

**Lote B7** · tarefas **6.3**, **6.6** e **6.7** · um commit · 2026-08-22

Este lote encerra o Grupo 6. Traz um reparo de uma linha e uma tarefa que se verifica em vez de se
executar — e as duas descobertas vieram do mesmo lugar: **recontar o enunciado antes de o
executar**. A 6.3 acusava dois defeitos que a árvore já não tem, e a 6.6 acusava um que a árvore
tem, mas cujo efeito o corpus não era capaz de mostrar.

---

## 1. A 6.3: as duas metades já estavam reparadas, por passagens anteriores à tarefa

A tarefa enuncia dois defeitos em `SignatureSpec.mop`: `verified` marcado no `boolean` em vez de
no `byte[]`, e pointcuts de `sign()` declarando `public byte`. **Nenhum dos dois está na árvore**,
e cada um saiu por um commit que a tarefa não nomeia.

**A metade dos pointcuts** saiu em `bc5e3e09` — `fix(jca_android): seis reparos estruturais
provados` —, da gh104, portanto antes desta change existir. O diff é literal:

```
-         call(public byte Signature.sign()) &&
+         call(public byte[] Signature.sign()) &&
-         call(public byte Signature.sign(byte[], int, int)) &&
+         call(public int Signature.sign(byte[], int, int)) &&
```

**A metade do `verified`** saiu em `bd25a3aa` — a passagem de arquivo do Grupo 4 que migrou as
quatro especificações só de escrita. O `predicate_graph.csv` já credita a autoria por escrito, na
linha `SignatureSpec.mop,match,...,VERIFIED`: *"the clause names the signature the call was given
and the seed wrote the boolean it returned … (researcher decision, task 4.13)"*. É o critério da
decisão 11 pela terceira vez neste grupo: **cada reparo saiu com a passagem que migrou a escrita
que ele retira**, que é a mesma forma que a 6.4 e a 6.5 já tinham.

**Verificado por medição, não por leitura** (a 6.4 fixou este padrão):

| o que se verifica | como | resultado |
|---|---|---|
| nenhum pointcut com tipo de retorno errado | `grep -rn "public byte [^[]"` nos 24 `.mop` de `jca_android` | **0** |
| `verified` marca o `byte[]` | `SignatureSpec.mop:242` e `:250` | `stagedVerified = sign;` nos dois |
| o `boolean` não é lido em lugar nenhum | o `returning(boolean signed)` de `:238` e `:246` | `signed` não aparece em nenhum corpo |
| a linha do grafo diz o mesmo | `predicate_graph.csv` | `position_types=byte[]`, `disposition=omission` |

**Onde o defeito sobrevive** — e é a mesma correção de enunciado que a 6.4 recebeu: as âncoras que
a tarefa nomeia resolvem no conjunto **congelado** `jca` (`jca/SignatureSpec.mop:99,106`) e no
arquivado `jca_android_bug_predicate` (`:120,127`), não na árvore. Vale registar a consequência,
porque ninguém a tinha escrito: no `jca`, `call(public byte Signature.sign())` não casa chamada
nenhuma — `Signature.sign()` devolve `byte[]` —, portanto **`s1` e `s2` são produtores
inexistentes** naquele conjunto (achado 95). O `jca` está congelado contra as medições publicadas
e esta change não lhe toca; o registo fica aqui.

---

## 2. A 6.6: uma chamada, duas transições — e a regra já dizia qual era de quem

`CipherSpec.f1` é `call(public byte[] Cipher.doFinal())` e `f2` era `call(public byte[]
Cipher.doFinal(..))`. Em AspectJ, `(..)` casa também a lista vazia, portanto **um único
`c.doFinal()` disparava os dois eventos**.

O que decide a forma do reparo não é o gosto: é o `order_alphabet_map.csv`, que **já atribuía** o
comportamento pretendido a cada evento —

| linha | evento do `.mop` | símbolo da regra | regra |
|---|---|---|---|
| `:115` | `f1` | `f1` | `Cipher.cryptsl:93` — `cipherText = doFinal()` |
| `:116` | `f2` | `f2` | `:95` — `cipherText = doFinal(plainText)` |
| `:117` | `f2` | `f4` | `:99` — `cipherText = doFinal(plainText, plain_off, len)` |

— e cuja nota dizia, desde que foi escrita, *"covers **both** of the rule's returning overloads"*.
Eram duas na nota e três no pointcut. O reparo é `doFinal(byte[], ..)`: casa as duas sobrecargas
`byte[]`-retornantes que têm argumento e deixa a sem argumento para o `f1`. Cobertura preservada,
disjunção obtida, **zero símbolo gasto** — 17 eventos antes e 17 depois, o que importa porque
dividir o `f2` em dois eventos continua indisponível (INV-INS-145, `n=18` estoura o parser do
enable-set em qualquer heap).

### 2.1 O que a medição mostrou, e o que ela precisou de uma sonda para mostrar

Medido com o harness sobre o corpus existente (a = árvore, b = candidata, 128 traces): **128
inalteradas**. Inclusive a única trace do corpus com `doFinal()` sem argumento,
`CipherSpec-update-chain.txt` — e a razão é instrutiva. Nela a chamada vem depois de um `update`,
logo o monitor está em `s3`, e `s3` tem transição para os dois: `f1 -> end` e `f2 -> end`. Como o
`f1` corre primeiro (medido, não presumido — o `b_events` da trace não acusa nada), o percurso é
`s3 -> end -> end`, aceite nos dois passos. **O defeito era silencioso em todo o corpus.**

Onde ele é audível é no caminho **sem** `update`, que o corpus não cobria: de `s2` só sai `f2`, e o
`f1` não tem transição nenhuma. A sonda foi escrita para isso e **corrida primeiro contra o
controle**, que é o que a torna uma sonda e não uma afirmação:

| | eventos acusadores | envelopes |
|---|---|---|
| árvore (antes) | `i2`, `f1`, `f2` | `CIPHER-NOBS-00` + `CIPHER-ORDER-00` **duas vezes** |
| candidata (depois) | `i2`, `f1` | `CIPHER-NOBS-00` + `CIPHER-ORDER-00` **uma vez** |

A segunda `CIPHER-ORDER-00` vinha do estado inicial em que o próprio `__RESET` do `f1` deixara o
monitor. **A sequência continua acusada dos dois lados, e está certo que continue**: a `ORDER` do
api30 é `Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+` com `FINWOU := f2 | f4 | f5 | f6 |
f7`, que **exclui** o `f1` da regra — um `doFinal()` logo depois do `init` está fora da ordem, e o
`fsm` diz isso fielmente ao deixar o `f1` fora do `s2`. O que o reparo troca é **duas acusações por
uma**, não uma acusação por nenhuma.

A sonda entrou no corpus como `data/gh104/traces/CipherSpec-nofinal-arg.txt` (decisão do
pesquisador, 2026-08-22): sem ela, o único reparo do lote não tem no repositório nada que o
reverifique. O precedente é o B5, que levou o corpus de 126 a 128 pela mesma razão. Medido antes
de a acrescentar: **nenhuma asserção das quatro suítes conta arquivos de trace** — o piso
`len(specs) >= 23` do censo do leitor conta `.mop`, e o parágrafo do B5 em
`test_gh105_predicate_gates.py` regista por escrito que o corpus não é contado (achado 72,
satisfeito por medição).

### 2.2 O reparo destrava uma coisa que o arquivo vizinho registava como impossível

`IvChainJunction.mop` existe, entre outras coisas, para carregar os dois sítios de
`!macced[_, plainText]` (cláusula #8 do ledger) que `CipherSpec` não conseguia carregar, e o motivo
estava escrito lá: *"its `f2` is declared `call(public byte[] Cipher.doFinal(..))` … binding no
argument, and **narrowing it would drop `doFinal()` out of the automaton**"*.

As duas metades da frase foram medidas contra a árvore e a regra:

- A segunda é imprecisa. O estreitamento não tira `doFinal()` do autómato — o `f1` continua a
  cobri-lo em `s3`. Tira-o do **`s2`**, que é uma transição que a `ORDER` nunca concedeu.
- A primeira **deixa de valer com o reparo**. As duas sobrecargas que restam ao `f2` partilham um
  `byte[]` na primeira posição, portanto `args(plainText, ..)` passaria a ligá-lo — com o wildcard
  depois do tipo discriminante, que é onde o próprio `IvChainJunction.mop` diz que o wildcard é
  seguro.

Decisão do pesquisador (2026-08-22): **corrigir o comentário e adiar a mudança.** Mover as duas
leituras é mudança comportamental — aposentaria `IVCHAINJUNCTION-CONSTR-06` e `-07` e trocaria
qual especificação relata um mau uso que nenhuma das colocações deixa de relatar — e este lote não
a mede. Os dois comentários (`CipherSpec.mop`, bloco do `f5`; `IvChainJunction.mop`, bloco da
cláusula #8) passam a dizer que a colocação é **escolha e não impossibilidade**.

---

## 3. A 6.7: a contabilidade das outras duas

| registo | o que mudou |
|---|---|
| `codes.csv` | reancorado por script inteiro: **5 de 112** linhas mudaram, todas por deslocamento dos meus comentários — `CIPHER-CONSTR-01` `:272→:293`, `CIPHER-CONSTR-02` `:284→:305`, `CIPHER-ORDER-00` `:355→:376`, `IVCHAINJUNCTION-CONSTR-06` `:337→:342`, `-07` `:347→:352`. **Zero deriva pré-existente** — o B6 tinha reancorado tudo. |
| `divergence_record.csv` | **278 hunks, todos registados, zero `stale`**, 283 linhas antes e depois. Três hunks re-chavearam e três saíram, um para um: `465872e781b7` (novo, `automaton`, 6.6) absorve `91c25b291fdb`; `f535aef55279` absorve `95a6e30dc89e`; `f44aff070792` absorve `a42232d095f8`. Anexados no fim, não reordenados. |
| `predicate_graph.csv` | **não muda**: nem `f1` nem `f2` tem linha (encenam num campo, a escrita está no `@match1`). Round-trip conferido — cópia, `--emit`, `diff`: **idêntico**, 70 linhas, 0 achados. |
| `order_alphabet_map.csv` | só a nota da linha `:116`, reescrita para nomear o pointcut novo. **Nenhum símbolo se move**, nenhum evento entra — que é o que impede o gate de pular a especificação inteira (`gh105_order_gate.py:799`). |
| `gate_baseline.json` | **não muda.** G-ORDER continua `6 passed / 4 failed / 14 skipped` com os mesmos quatro achados, `CipherSpec f2` incluído: ele é sobre a `ORDER` contra o `fsm`, e este lote não toca no `fsm`. A 7.1 continua dona dele. |
| censos | os dois parágrafos por lote escritos, os dois dizendo que **nada se moveu** e por quê (regra 16: se um número não se moveu, escreva isso também). |

**O `IvChainJunction.mop` não gera hunk** por não existir no `jca`: a sua linha no registo é
`new-file`, e a edição de um comentário dentro dele não a altera.

---

## 4. Estado do conjunto depois deste lote

**Harness contra a pré-imagem, 129 traces**: **60 unchanged · 31 moved · 31 introduced · 7
removed**. O `moved` sobe de 30 para 31 e a trace que o move é a nova — nenhuma das 128 anteriores
mudou de classe. `git diff --stat -- data/gh105/evidence/harness/` dá **um** arquivo,
`f2-CipherSpec.md`, com a trace nova; `unresolved` continua em **seis linhas, quatro arquivos**,
todas pré-existentes.

**`verify_all.sh`**: as quatro suítes verdes — **94 asserções** (6 + 2 + 16 + 70) —, `mop-lint`,
`message-gate`, `graph-all`, `graph-android`, `divergence` e `baseline` a zero. Os dois códigos 1
são os vereditos esperados: `order-gate` (as quatro divergências) e `gh104-gates`, com
`G-2 0 · G-2a 11 · G-2b' 18 · G-2c 2 · G-2d 3 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23` —
**idênticos desde o B4**.

---

## 5. O que fica para o Grupo 7

1. **A ligação do `plainText` no `CipherSpec.f2`** passou de impossível a disponível, e a decisão
   de não a exercer está registada nos dois comentários e aqui. Quem a medir aposenta dois
   acusadores; quem não a medir não deve mexer.
2. **A 7.1 herda o `CipherSpec` inteiro**: a divergência G-ORDER do `f2`, o reparo do parser de
   precedência da `ORDER` (`f1-order-gate-precedence.md`) e a `f1` fora do `s2` são o mesmo
   assunto, e este lote deixou o `fsm` intacto de propósito.
3. **Cobertura de trace medida e não fechada**: nenhuma trace do corpus alcança `v1`/`v2` de
   `SignatureSpec` — logo, nem a escrita de `VERIFIED` — nem `f5`/`f6` de `CipherSpec`, logo nem
   `CIPHER-CONSTR-01` nem `-02`. São quatro acusadores sem trace que os exercite.
4. **A âncora que ninguém confere continua sem portão** (matéria que o B6 deixou): este lote
   moveu cinco linhas do `codes.csv` e só as apanhou porque reancorou o arquivo inteiro por
   script. Um portão de dez linhas fecha isto.
