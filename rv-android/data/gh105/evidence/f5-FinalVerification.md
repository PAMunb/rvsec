# Tarefas 8.6 e 8.7 — a sequência final do esquema rv-sdd

**Data**: 2026-08-23 (8.6) e 2026-08-24 (8.7) · **Base**: `519f2ff8` (fim da 7.5) → `c21b5808`
A sequência que o esquema fixa: **lint-fix → verify → suíte de paridade → code-reviewer.**
As secções 1 a 5 são a 8.6; da 6 em diante é a 8.7.

---

## 1. O escopo, recontado antes de ser executado

A tarefa diz *"tudo que a change tocou desde a 7.5"*. Recontado:

```
git diff --name-only 519f2ff8..HEAD  →  16 .md, 4 .logcat, 1 .json
```

**Zero arquivos de código.** Os três commits do Grupo 8 até aqui são evidência, logcats e o
`tasks.md`. Se o escopo fosse lido ao pé da letra, a 8.6 não teria o que limpar.

Lido pelo espírito — *a change acaba com o seu código limpo* —, há o que limpar, e num lugar que
a 7.5 tinha deliberadamente deixado de fora. A 7.5 cobriu **todo `scripts/gh10*.py` menos três**
(`gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`), porque a tarefa 2.12
já os cobriria. Medido hoje, não cobria:

| ferramenta | sobre os 14 da 7.5 | sobre os 3 excluídos |
|---|---|---|
| `black --check` | limpo | **3 de 3 reformatariam** |
| `isort --check-only` | limpo | **1 arquivo fora de ordem** |
| `flake8` fora de `E501` | **0** | **2** |
| `autoflake` | nenhuma mudança | nenhuma mudança |

Os três foram editados depois da 2.12 — o `gh105_order_gate.py` no `012f9dbe`, dois commits
antes da 7.5 —, e é aí que a limpeza se desfez.

**E não eram só eles.** O `/rv-verify` apanhou o que este recontar tinha deixado passar: os
**quatro arquivos de teste** que a change escreveu ou reescreveu (`test_gh101_specset_gates.py`,
`test_gh104_specset_gates.py`, `test_gh104_structural_gates.py`,
`test_gh105_predicate_gates.py`) também estavam fora do `black`, e o
`test_gh105_predicate_gates.py` carregava um **`import json` morto** — a única falha real de
lint no escopo inteiro. Um teste é código da change tanto quanto um portão.

## 2. O que a 8.6 mudou

`autoflake` → `isort` → `black`, na ordem que a skill fixa, sobre os três arquivos:

```
3 arquivos, 54 hunks, +242 / -73 linhas    (3.167 → 3.336 linhas)
```

Mais dois resíduos que as três ferramentas não alcançam, tirados à mão:

1. **`gh105_order_gate.py`, `parse_cat()`** declarava `nonlocal position` e **nunca atribui** a
   variável — só a lê, indiretamente, através de `parse_postfix()` e `peek()`, que têm as suas
   próprias declarações. É o mesmo defeito que o lote B10 achou em `gh104_gates.py:481`, e a
   terceira vez nesta change que um `nonlocal` de leitura aparece: vale como padrão, não como
   caso.
2. **`gh105_predicate_graph.py`** terminava com linha em branco (`W391`), que o `black` fechou.

E os quatro arquivos de teste, na mesma ordem de ferramentas:

```
4 arquivos, +226 / -73 linhas    (o `import json` morto sai com o autoflake)
```

Resíduo fora de `E501` ao fim: **0**, nos 17 scripts e nos 4 testes. As passagens de
`black --check` e `isort --check-only` sobre `scripts/gh10*.py` e sobre os quatro testes saem
limpas.

## 3. A prova de que a reformatação não mudou nada

Item 26 da receita: a suíte verde não prova que um formatador não mexeu em nada. As cinco saídas
dos três portões foram capturadas **antes** e **depois** e comparadas:

| saída | resultado |
|---|---|
| `gh105_predicate_graph --sets all --json` (215 arquivos) | **idêntica** |
| `gh105_order_gate --sets all --json` (215 arquivos) | **idêntica** |
| `gh105_param_gate --sets jca_android --monitors <24 .rvm>` | **idêntica** |
| `gh105_predicate_graph --sets jca_android` (texto) | **idêntica** |
| `gh105_order_gate --sets jca_android` (texto) | **idêntica** |

`diff -r` sobre os dois diretórios: sem diferença.

E as quatro suítes, depois da reformatação dos próprios arquivos de teste:
**`6 + 2 + 16 + 67 = 91 passed`**, em 85 s. Os mesmos 91 de antes.

## 4. Uma medida que fica registrada e não foi executada

Os três arquivos têm **18 itens sem docstring**, contra **0** nos catorze da 7.5. Os dezoito são
fechos de uma linha dentro de funções já documentadas — `peek`, `key`, `total`, `universe`,
`read`, `skipped` — e as cinco funções do descendente recursivo (`parse_seq`, `parse_alt`,
`parse_cat`, `parse_postfix`, `parse_atom`), cuja função-mãe já documenta a gramática inteira e
o `ParseError` que levantam.

**Não foram escritas**, e a razão é P1: uma docstring sobre `def key(row): return ...` é cerimônia
que o próximo leitor pula. A medição fica aqui para que a diferença entre 0 e 18 seja uma escolha
registrada e não um esquecimento.

## 5. A suíte de paridade

```
uv run pytest tests/parity --import-mode=importlib -o "addopts="
→ 3 failed, 149 passed em 238 s
```

**Os três que falham são anteriores a esta change e estão fora do seu escopo.** Nenhum dos cinco
arquivos de teste envolvidos menciona `gh105`, e os três caminhos que causam as falhas estão
limpos na árvore ou pertencem a outro lote:

| teste | causa medida | de quem é |
|---|---|---|
| `test_baseline_freshness::test_baseline_not_older_than_jar` | os jars do gator são de **2026-08-23 01:58** e a baseline `cryptoapp.apk.json` é de **2026-05-29**: o jar foi reconstruído sem regenerar a baseline | build do reator anterior a esta sessão; a própria mensagem manda regenerar por gh60 11.8 |
| `test_no_legacy_mop::test_repo_is_clean` | seis ocorrências do token `reachesMop` em `modules/aperv-tool/` | o `aperv-tool` está modificado na árvore por outro lote |
| `test_sentinel_emission::test_real_gator_json_parses_with_complete_true` | `StaticAnalysisParser.parse_file()` recebe 1 argumento e o teste passa 2 | `bd10fb0f fix(analysis): o artefato define o próprio escopo, e o parser para de refiltrá-lo` tirou o parâmetro `package` e o teste da gh60 não acompanhou |

**Uma armadilha de ambiente, medida**: sem `ANDROID_SDK_HOME` exportado, sete testes **erram**
(não falham) com `KeyError: 'ANDROID_SDK_HOME'` levantado de dentro do `lib/gator/gator`, e um
oitavo falha por arrasto. Com a variável, os oito passam. É a mesma classe de armadilha do
`RVSEC_HOME` que a 8.2 registra: um portão que não corre não é um portão verde.

**Nenhuma das três falhas foi reparada aqui**, e isso é decisão de escopo: a terceira é um reparo
de uma linha noutra change, e corrigi-la dentro do commit de verificação final da gh105 misturaria
duas coisas que o próximo leitor precisa separar. As três estão relatadas ao pesquisador.


---

# Tarefa 8.7 — a revisão de código

## 6. O veredicto, e a regra que a revisão ensinou

O `/rv-code-reviewer` correu sobre o que a change escreveu e saiu com **REQUEST CHANGES**: três
achados críticos (C1, C2, C3), dez avisos (W1–W10) e um punhado de sugestões 🟢.

**Cada achado foi reproduzido antes de ser aceito ou recusado**, e a reprodução não foi cerimónia:
dois dos três críticos **só aparecem fora da raiz do repositório**, então um leitor que confiasse
na suíte verde da raiz teria recusado ambos. E um deles veio com um reparo proposto que a própria
medição derrubou — o que vale como regra e está registrado como aprendizado:

> **A revisão pode estar certa no diagnóstico e errada no reparo.** O C3 chegou com o reparo
> "inverta as duas escritas". O teste concorrente que a decisão mandou escrever mediu **18
> vazamentos com as escritas já invertidas**. O defeito não era ordem de escrita — era leitura
> não atómica de dois campos, que nenhuma ordem de escrita conserta. **Escreva o teste antes de
> acreditar no reparo.**

## 7. Os três críticos, medidos e reparados

Todos em `caa48643`.

| # | o que a revisão disse | o que a medição mostrou | reparo |
|---|---|---|---|
| **C1** | os caminhos de dado dos portões são relativos | de qualquer `cwd` que não a raiz, **três portões saíam 0 tendo comparado 0 de 24**, e a razão do pulo culpava a especificação em vez do CSV inexistente | caminhos ancorados em `Path(__file__).resolve().parents[1]`; o mapa ausente diz o próprio nome; um conjunto que a árvore não tem vira pulo com razão em vez de sumir; **os três portões saem 2 quando não compararam nada**; o `--emit` recusa reescrever o registro de julgamento sem o conjunto migrado, que antes o truncava para o cabeçalho |
| **C2** | o teste fixa o mapa e deixa o allow-list no default | `test_inv_ins_138_gorder` ficava **vermelho fora da raiz**: da raiz 91, de `/tmp` **67** | `_order_run` fixa os dois caminhos |
| **C3** | `PredicateStore` escreve duas verdades em dois campos | um leitor que amostra `negated` e depois `tuples` cai num par que nunca existiu — sem tuplas e não negado — que o `validate` lê como `NOT_OBSERVED`, **a única direção que suprime acusação**. Inverter as escritas **não** resolve: 18 vazamentos medidos com elas já invertidas | os dois factos passam a viver num `State` imutável atrás de uma `AtomicReference`; `ensure` troca por compare-and-set, `negate` por uma escrita só, e **toda leitura é um instantâneo**. `rvsec-core`: **72 testes, zero falhas** (`PredicateStoreTest` de 19 para 20) |

**Prova de inércia nos três**: as cinco saídas dos portões são idênticas byte a byte antes e
depois, e o `verify_all` continua em 6+2+16+67.

## 8. O W1 — a testemunha do allow-list

Também em `caa48643`, e ratificado junto com o W7 ("fazer as duas agora").

O allow-list do G-ORDER casava por `(conjunto, especificação)` e **ignorava a testemunha**: uma
linha escrita para um contraexemplo perdoava qualquer outro da mesma especificação — **nove das
vinte e duas comparadas ficavam sem guarda**. O `gate_allowlist.csv` ganhou a coluna `witness`,
preenchida nas nove linhas **a partir da própria saída do portão** e nunca transcrita à mão;
`read_allowlist` devolve 4-tuplas e recusa linha sem testemunha; `_is_allowed` compara a
testemunha nas duas larguras.

Conferido nos dois sentidos: com as testemunhas certas o veredicto não se move (cinco saídas
idênticas byte a byte), e trocando uma delas o `CipherSpec` volta a acusar — **13 / 1 / 8 / 2,
exit 1**.

## 9. O W7 — os caminhos vermelhos que nenhum teste exercitava

O revisor mediu que `_is_allowed`, `read_allowlist`, `OrderRun` e o `main()` do
`gh105_order_gate.py` **não eram chamados por teste nenhum**, e que dois invariantes não tinham
fixture negativa. A ausência foi medida, não presumida: `grep "condition(" tests/parity/fixtures`
não devolvia nada e nenhuma fixture nomeava `ExecutionContext`.

O problema é sempre o mesmo, e vale escrever uma vez: **o portão está verde e o verde não prova
nada.** G-ORDER reporta zero achados desde a 7.6; INV-INS-133 está em zero desde a 4.12;
INV-INS-130 desde a 4.14. Um portão reescrito para devolver `[]` incondicionalmente **satisfaria
todas as asserções que a suíte fazia sobre os três**. O que faltava era mostrar que ainda sabem
ficar vermelhos.

### Os seis testes que entram

| teste | o que fixa | como falha se o portão parar de olhar |
|---|---|---|
| `test_the_placement_gate_reports_a_read_left_in_a_guard` | INV-INS-133 sobre `GuardedReadSpec.mop` | trocando a guarda de `site_kind == "condition"` por `False`: **vermelho** |
| `test_the_import_gate_reports_the_old_substrate_in_code_and_in_prose` | INV-INS-130 sobre `LegacySubstrateSpec.mop`, **as duas contagens** (3 menções, 2 em código, 1 em prosa) | cegando o `_EXECUTION_CONTEXT`: **vermelho** |
| `test_the_order_gate_accuses_when_the_allow_list_stops_covering_the_witness` | o caminho vermelho do G-ORDER: **13 / 1 / 8 / 2**, testemunha `g1 i1 u1`, acusada pela especificação | fazendo `_is_allowed` ignorar a testemunha: **vermelho** |
| `test_an_allow_list_row_allows_nothing_without_both_a_reason_and_a_witness` | `read_allowlist` no leitor **e** na corrida: 9 linhas admitidas; com `reason` ou `witness` em branco, **8**, e o `CipherSpec` volta a acusar | tirando as duas guardas do leitor: **vermelho** |
| `test_the_allow_list_has_two_widths_and_the_witness_is_in_both` | `_is_allowed`: `(conjunto, spec)` e `(conjunto, *)`, a palavra vazia como testemunha real, e que **não há largura por evento** | idem: **vermelho** |
| `test_the_order_gate_exits_one_when_it_accuses_and_two_when_it_compared_nothing` | os três veredictos do `main()` — **0**, **1** e o **2** do C1 | fazendo `main()` devolver sempre 0: **vermelho** |

**Cada uma das cinco mutações foi aplicada, corrida e revertida**, e os `scripts/` voltaram byte a
byte ao que eram. Um teste novo que não sabe ficar vermelho é decoração.

### As duas fixtures negativas

Vivem em `tests/parity/fixtures/gh105/`, ao lado das quatro do INV-INS-136, e seguem a mesma
disciplina que o README delas já enunciava: **uma fixture carrega um defeito e nenhum outro**,
porque uma que tropeçasse em dois portões não diria qual dos dois ainda funciona.

* **`GuardedReadSpec.mop`** — a ponta consumidora da cadeia de IV com o `validate` dentro de
  `condition(...)`. O substrato é o `PredicateStore` do conjunto (então o portão de import fica
  calado) e a única escrita está no ponto de aceitação (então o INV-INS-134 também). Medido:
  **uma** achado, `INV-INS-133 / consume/PREPARED_IV`. O teste ainda compara com a
  `ConformingJunction.mop` ao lado, onde a mesma leitura no corpo é a colocação certa — é a
  diferença de `site_kind`, e não a operação, que faz o achado.
* **`LegacySubstrateSpec.mop`** — nomeia `ExecutionContext` nas três formas que a fronteira de
  palavra do `grep -rlw` existe para apanhar, nenhuma delas subcadeia das outras: a linha de
  import, uma chamada qualificada por inteiro e uma menção num comentário. A única escrita está
  no ponto de aceitação e o arquivo não declara leitura, então o portão de colocação não tem o
  que dizer. Medido: **3 menções, 2 em código e 1 em prosa** — que é por que o portão reporta as
  duas contagens separadas e não uma só.

### O resultado

```
uv run pytest tests/parity/test_gh105_predicate_gates.py  →  73 passed em 5,5 s   (era 67)
as quatro suítes juntas                                   →  97 passed em 86 s    (era 91)
```

`black`, `isort` e `flake8` fora de `E501` limpos sobre tudo que a gh105 é dona. As quatro saídas
dos portões, idênticas byte a byte antes e depois — o `divergence_record.csv` não é lido por
portão nenhum, e a prova é a comparação e não o argumento.

## 10. O que a revisão levantou e foi registrado, não reparado

A disposição aqui não é preguiça de escopo: é a **decisão 7** da change, que mantém mudança
comportamental fora dela sem medição própria. O que segue é o que fica escrito para quem vier.

### O W2, que ganhou a sua linha no registro

**É o único dos não-reparados que exigia mais que prosa**, e a razão é que ele *é* uma divergência
do conjunto sucessor contra a semente — pertence ao `divergence_record.csv`, não a um comentário.

Medido bloco a bloco, contando chaves e não linhas: **20 dos 21 blocos `@fail` do `jca_android`
terminam em `__RESET`**, e `KeyPairGeneratorSpec.mop:158` é a exceção. Sem o reset o monitor fica
na categoria de falha depois da primeira sequência rejeitada, e todo evento seguinte da mesma
ligação re-dispara `KEYPAIRGENERATOR-ORDER-00`: **uma sequência errada é reportada como muitas.**

O bloco **foi editado por esta change** — o `kp = null;` (hunk `ee86d177e08f`, tarefas 7.5 e 4.14)
substituiu um `ExecutionContext.instance().remove(...)` — e não acrescentou o reset; além disso
limpa `kp` e deixa o campo irmão `algorithm` posto, de modo que o campo que o handler do ponto de
aceitação encena e o campo que `validate(keySize)` lê se limpam em horários diferentes. O irmão
`KeyGeneratorSpec.mop:163-169` faz as duas coisas, o que torna isto uma assimetria e não um estilo
da casa.

**Disposição**: uma linha `behavioural` sem chave de hunk — narrativa, porque é uma afirmação
sobre o conjunto e não sobre um diff. O registro passa a **288 linhas** (282 hunks + **6**
narrativas), `check()` em exit 0, zero `stale`. O arquivo é CRLF e a linha foi **apendida**, não
reescrita: as 288 linhas anteriores são byte a byte as mesmas — um `csv.writer` com
`lineterminator="\n"` reescreveria o arquivo inteiro, e reescreveu, na primeira tentativa.

### Os outros, que ficam em prosa

| # | o que é | por que não se repara aqui |
|---|---|---|
| **W3** | G-PRED2 filtra por `read`/`read-absent`/`write` e **não olha sítios `negate`**. No grafo vivo: 33 read + 5 read-absent + 31 write + **1 negate**, e essa linha (`PBEKeySpecSpec.c2`, `SPECCED_KEY`) tem `disposition` e `reason` vazios — escapa ao contrato de fecho. `remove` escaparia igual | alarga o contrato de um portão; é mudança de escopo do fecho, não reparo |
| **W5** | ORDER malformado **parseia como epsilon em vez de levantar**: `parse_cat` devolve `("eps",)` quando não acha itens, então `a||b` vira `a|ε|b` e `a,` vira `a·ε`. Uma barra dupla **muda a linguagem comparada** em vez de produzir um pulo | muda veredicto de portão sobre entrada que a árvore hoje não tem |
| **W6** | um `order_symbol` em branco **apaga um evento independentemente da disposição** (`if row.disposition == "order-unmapped" or not row.order_symbol:`). O CSV de hoje não tem linha assim | código que falha aberto, não verde falso vivo |
| **W9 (P4)** | a cronologia nos artefatos: duas docstrings de teste com **334 e 275 linhas** escritas tarefa a tarefa, **29 linhas de cronologia** nos `.mop` e **52 referências `task N.M`** que ficam penduradas quando o `tasks.md` arquivar; e `test_the_derived_set_carries_exactly_the_seventeen_orphan_accusers`, que afirma `found == {}` com um nome que descreve o estado anterior à migração | **a razão é valiosa (P2); é a cronologia que o P4 proíbe** — separar uma da outra é trabalho de edição sobre 52 sítios e merece a sua própria passagem |
| **W10** | comentários que esta change deixou obsoletos: `IvChainJunction.mop:282` diz *"the five events this file declares"* e o arquivo declara **sete**; `TrustManagerFactorySpec.mop:7` tem `import javax.net.ssl.KeyManager;` morto desde o reparo do `gtm1`; `test_gh105_predicate_gates.py:1944` ainda afirma *"no junction specification exists yet; these are Group 5's"* e o Grupo 5 aterrou | reparo de uma linha cada, mas toca `.mop` do conjunto: entra na próxima passagem que já os abra |
*(Os números de linha acima foram reconferidos na árvore de hoje e não transcritos da revisão: o `:1806` era `:1801` e o do teste era `:1873` antes de a 8.7 lhe acrescentar seis testes. O censo do W3 também, sobre as 70 linhas do grafo vivo: 33 read + 5 read-absent + 31 write + 1 negate, e a linha `negate` é `PBEKeySpecSpec.c2 / SPECCED_KEY` com `disposition` e `reason` vazios.)*

| **🟢** | código morto verificado (`_row_key`, `Finding.key`, `ParamFinding.key`, `Site.snippet`, `MapRow.symbol_kind`, `Rule.name`/`Rule.events`, guardas inalcançáveis de `parse_atom`), um `if` sempre falso em `gh105_predicate_graph.py:1806`, `"jca_android"` como literal em 3 lugares onde `TARGET_SET` existe, `compare()` do param gate contando cabeçalho gerado ilegível como **passou**, e `RandomStringPassword.mop` **inteiramente inerte** mas ainda tecendo dois join points quentíssimos do Android | o último não é sugestão de estilo: é **decisão de NFR06 explícita**, e por isso não se herda de passagem |

### Um achado de lint que não é da gh105

`black --check` sobre o glob que o roteiro usa (`scripts/gh10*.py tests/parity/test_gh10*.py`)
reporta **um** arquivo a reformatar: `tests/parity/test_gh104_baseline.py`, cometido em
`110fc714` pela **gh104** e não tocado por esta change nem pela árvore. A mudança que o `black`
26.1.0 quer é a de formatação de `assert ... , mensagem`, que é do formatador e não do arquivo.
**Não foi reparado**: pôr um arquivo da gh104 dentro do commit de verificação final da gh105
misturaria duas coisas que o próximo leitor precisa separar — a mesma razão da terceira falha da
§5. Tudo que a gh105 **é dona** está limpo nas três ferramentas.
