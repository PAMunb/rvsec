# Tarefa 11.7 — a verificação do grupo 11, item por item

**Data**: 2026-08-26 · **Monitor**: `~/tmp-gh104/verif11/monitors/` (gerado nesta tarefa a partir de
`rvsec/rvsec-mop/src/main/resources/jca_android`, 24 especificações) · **Controle congelado**:
`~/tmp-gh104/verif11/jca/` (gerado nesta tarefa, para a §7)
**Oráculo único (D-16)**: `RVSec-replication-package/tools/rules/` — 49 regras, sha256 `d7bcc019…`

Espelho da 9.18 e da 10.11, com a mesma regra: **nada aqui fecha por código de saída** (R5/R6).
Cada exigência da 11.7 tem abaixo o artefato que a responde. Onde a exigência pedia uma garantia que
ainda não existia — o `--check` do ledger, que a §5 mede — ela foi feita nesta tarefa e não herdada,
e **achou um defeito na primeira execução**.

---

## 1. Os portões sobre os insumos reancorados

`gh104_gates.py` sobre o monitor gerado nesta tarefa, com `--crysl` no oráculo único:

```
ok = true      skipped = []
```

| portão | falhas | hits | perdoados | observação |
|---|---:|---:|---:|---|
| G-2 | 0 | 0 | 0 | 0 órfãos crus |
| G-2a | 0 | 12 | 12 | as oito antigas mais as quatro da 10.1 |
| G-2b' | 0 | 19 | 19 | |
| G-2c | 0 | 2 | 2 | |
| G-2d | 0 | 3 | 3 | |
| G-6' | 0 | 0 | 0 | |
| G-ERE | 0 | 0 | 0 | |
| G-CONF | 0 | 0 | 0 | **80 cláusulas anotadas**, oráculo de valor = cópia expert fixada |
| G-PRED | 0 | — | — | **`superseded`**, com o sucessor nomeado por escrito |

`skipped` vazio importa tanto quanto o `ok`: insumo ausente não é aprovação. O `superseded` do
G-PRED é o terceiro estado da 10.2 — não é skip, e skip reprova.

Os portões que rodam fora dessa CLI, sobre a mesma árvore:

| portão | veredito |
|---|---|
| `gh104_mop_lint.py` | `ok: true`, `counts: {}` |
| `gh104_message_gate.py` | `ok: true`, `counts: {}` — inclui o `code-anchor`, que a 11.6 moveu sete vezes |
| G-SIG | 418 checados, **0 falhas**, 7 perdoados, 7 pulados declaradamente, 16 notas |
| G-FORB | 9 checados, **0 falhas**, 6 perdoados, 8 pulados |
| G-BIND | 854 checados, **0 falhas**, 30 perdoados, 22 pulados |
| **G-ORDER** | **15 passadas, 0 falhas**, 7 perdoadas, 2 puladas declaradamente |
| `gh105_expert_ledger.py --check` | exit 0 |
| `gh105_expert_alphabet.py --check` | exit 0 |
| `gh105_expert_conformance.py --check` | exit 0 |
| `gh104_divergence_record.py --check` | exit 0 |
| `gh105_predicate_graph.py --sets all` | 0 falhando, 0 perdoadas, 21 informativas |

Duas contagens que **mudaram por substituição de oráculo e não por regressão**, ambas já registradas
na 11.3 (`f8-instruments-sole-oracle.md §2.3`): o G-FORB caía de 18/12 para 9/6 porque o catálogo
retirado declarava `FORBIDDEN` que o expert não declara; e o G-ORDER passou de 14 comparadas para 15
porque as duas divergências da 11.6 fecharam. **Nenhuma das duas perdeu veredito.**

Os dois pulos do G-ORDER continuam sendo os dois arquivos sem regra no catálogo
(`IvChainJunction`, `RandomStringPassword`), declarados e contados.

**Uma leitura que só o artefato dá**: as três cláusulas `FORBIDDEN` do conjunto vivo
(`PBEKeySpecSpec.f1`, `.f2`, `SSLContextSpec.getDefault`) aparecem entre as **checadas**, não entre
as perdoadas — os seis perdões do G-FORB são todos do `jca` congelado e do arquivado. É a 11.8
funcionando lida pelo lado do portão, e não pelo lado do texto que ela editou.

## 2. O portão de grep da 11.4, em zero

```
G-ORACLE: 30 file(s) read, 0 finding(s) (0), 10 skipped
```

Nenhum artefato de `data/jca_android/`, nenhum comentário de `.mop` e **nenhuma mensagem emitida**
nomeia a api30 como autoridade fora de adendo de supersessão. Os dez pulos são declarados, um a um,
com a razão de cada.

**Um deles foi conferido e não bate com a sua própria razão** — é a §5.

## 3. A aritmética do ledger, fechada por enumeração

Contada da linha, nunca afirmada como literal:

| seção | linhas | disposições |
|---|---:|---|
| REQUIRES | 57 | `wireable` **24** · `unmonitored-consumer` 21 · `unmonitored-producer` 9 · `vacuous` **2** · `unreachable-composition` 1 |
| ENSURES | 76 | `unmonitored-producer-side` 31 · `producible` 28 · `unread` 13 · `unmonitored-consumer-side` 4 |
| NEGATES | 2 | `unmonitored-consumer-side` 1 · `unmonitored-producer-side` 1 |
| **total** | **135** | |

`57 + 76 + 2 = 135`, e dentro de REQUIRES `24 + 21 + 9 + 2 + 1 = 57`. Fecha.

### O que se moveu, e por qual tarefa — medido nos commits, não lembrado

A 11.7 pede que a aritmética esteja **imóvel pela 11.9**. Está, e a medida é o ledger em cada
commit que o tocou:

| commit | tarefa | `wireable` | `vacuous` | `unreach.-comp.` | `unmon.-producer` |
|---|---|---:|---:|---:|---:|
| `1325b7b1` | 11.1 (derivação) | 25 | 1 | 2 | 8 |
| `01156622` | **11.9** | 25 | 1 | **1** | **9** |
| `bca7baaa` | **11.5(d)** | **24** | **2** | 1 | 9 |
| `HEAD` | depois da 11.6 | 24 | 2 | 1 | 9 |

Lê-se linha a linha:

- **A 11.9 não moveu contagem alguma da partição.** Ela trocou uma linha de balde dentro do lado
  *registrado* — a cláusula #34 do `KeyPairGenerator`, de `unreachable-composition` para
  `unmonitored-producer` — e `wireable` ficou em 25. É exatamente o que a D-17 pedia: renomear a
  disposição sem mover o que está fiado.
- **A 11.5(d) moveu de propósito**, com decisão por cláusula: `randomized[lSeed]` sai de `wireable`
  para `vacuous`, porque o oráculo não tem produtor de `randomized` em tipo que um `long` possa
  carregar. Está escrito em três lugares — `predicate_ledger.md`, o `VACUITY_OVERRIDES` do
  instrumento e o comentário ao lado do `setSeed1`.
- **A 11.6 não moveu nada no ledger**, o que é o esperado: ela é tarefa de ORDER, e ORDER não é
  cláusula de predicado.

O censo da 11.9(c)(d) reproduz: **11 cláusulas / 10 predicados** exigidos e não observáveis;
**18 cláusulas / 12 predicados** garantidos e não legíveis.

## 4. Reprodução dos registros derivados, arquivo por arquivo

Round-trip é o que separa "derivado" de "escrito à mão uma vez":

| arquivo | como se reproduz | resultado |
|---|---|---|
| `predicate_ledger.csv` | `--emit ledger --out` + `cmp` | **byte a byte idêntico** |
| `predicate_ledger_delta.csv` | `--emit delta --out` + `cmp` | idêntico **depois do reparo da §5** |
| `order_alphabet_map_expert.csv` | `--check` (compara bytes) | exit 0 |
| `order_alphabet_map_delta.csv` | `--check` (compara bytes) | exit 0 |
| `predicate_graph.csv` | `--emit` + `git diff` | vazio |
| `conformance_record.csv` / `_delta.csv` | `gh105_expert_conformance.py --check` | exit 0 |

Terminadores de linha, **medidos** e não lembrados — o handoff anterior os tinha ao contrário para
um deles:

| CRLF | LF |
|---|---|
| `conformance_record.csv`, `divergence_record.csv`, `gate_allowlist.csv`, `constraint_table.csv` | `predicate_graph.csv`, `predicate_ledger.csv`, `predicate_ledger_delta.csv`, `order_alphabet_map_expert.csv`, `order_alphabet_map_delta.csv`, `conformance_record_delta.csv`, `alias_table.csv`, **`codes.csv`** |

## 5. A isenção que se apoiava numa garantia inexistente — e o defeito que ela escondia

O `gh105_sole_oracle_gate.py` isenta seis registros do seu grep, e a razão coletiva que escreve é
esta: *"each instrument's `--check` reproduces its file and fails if it does not — so exempting them
here moves the guarantee to a sharper gate rather than dropping it"*.

**Era verdade do instrumento de alfabeto e não era do ledger.** Medido: o `--check` do
`gh105_expert_ledger.py` tinha uma linha só de asserção — `sum(counts.values()) != total` — que
afirma que a aritmética fecha e **nada** sobre o arquivo commitado ser o que o instrumento emite.
Um `predicate_ledger.csv` reescrito à mão passava pelos dois portões.

O `--check` foi apertado nesta tarefa para reproduzir os dois arquivos que o instrumento deriva,
como o de alfabeto já fazia. **Na primeira execução ele reprovou**:

```
data/jca_android/predicate_ledger_delta.csv: committed file is not what --emit writes
```

O delta estava **desatualizado de uma linha** desde a 11.5(d): aquela tarefa moveu a disposição de
`SecureRandom randomized` de `wireable` para `vacuous` e re-emitiu o ledger, **e não o delta**. A
linha que faltava é exatamente a que registra esse movimento:

```
REQUIRES,SecureRandom,randomized,1,no,no,changed,vacuous,wireable,SecureRandom.crysl:46,SecureRandom.cryptsl:66,disposition wireable -> vacuous
```

O delta foi re-emitido e o `--check` sai 0. É o achado que justifica a §5 existir: a aritmética
fechava, o grep estava limpo, e o registro que conta o que o oráculo mudou tinha um buraco de uma
linha que nenhum portão via.

## 6. Pares de arnês, um por tarefa que moveu acusação

| tarefa | o que moveu | par | veredito |
|---|---|---|---|
| 11.5(a) | `Mac generatedKey[key,_]` fiado no corpo do `init` | `f8a-MacSpec.md` | 2 `moved`, 2 `introduced`, 7 `unchanged` |
| 11.5(b) | `SSLContext randomized[random]` ganha binding e leitura | `f8b-SSLContextSpec.md` | 8 `moved`, 1 `introduced`, 3 `unchanged` |
| 11.5(e1) | a cadeia `generatedCipher` fiada nas duas pontas | `f8e-CipherInputStreamSpec.md` | 3 `introduced`, 1 `unchanged` |
| | | `f8e-CipherOutputStreamSpec.md` | 2 `introduced`, 1 `unchanged` |
| **11.6** | o `ere` do `MacSpec` (`Update+`) | `f8f-MacSpec.md` | 3 `moved`, 11 `unchanged` |
| **11.6** | o `ere` do `KeyPairSpec` (construtor obrigatório) | `f8g-KeyPairSpec.md` | 3 `introduced`, 3 `unchanged` |
| | | `f8g-SignatureSpec.md` | 2 `introduced`, 10 `unchanged` |
| 11.8 | as cinco mensagens reancoradas | `f8-GCMParameterSpecSpec.md` | **6 `unchanged`** |
| | | `f8-PBEKeySpecSpec.md` | **7 `unchanged`** |
| | | `f8-SSLContextSpec.md` | **12 `unchanged`** |
| 11.5(c)(d)(e2), 11.9 | registro: nenhum sítio, nenhuma acusação | — | não se deve par |

As três provas `unchanged` da 11.8 são a exigência literal da 11.7, e são o que a própria 11.8
mandava provar em vez de argumentar: reancorar o texto de uma mensagem **parece** mudar o que é
acusado, e não muda, porque a comparação do arnês é sobre `(evento, código)`.

A 11.6 é a única tarefa do grupo cujos dois pares medem **coisas de sinais opostos**: o `MacSpec`
acrescenta relatório a traces que já acusavam (`moved`), o `KeyPairSpec` acrescenta relatório a
traces que não acusavam nada (`introduced`). As duas são acusação nova, e as duas foram decididas.

## 7. Um defeito de registro que esta verificação achou e **não** reparou

O handoff desta linha entregou à 11.7 a suspeita de que a linha 40 do `constraint_table.csv` está
errada, e a suspeita **procede em substância e não no reparo**. Os três oráculos:

1. **A regra**: `IvParameterSpec.crysl:19` diz `len > 0`.
2. **O `.mop`**: o seed `jca/IvParameterSpec.mop:36`, dentro da `condition(...)` do `c2`, diz
   `len >= 0`. A cláusula **alcança um guarda**, mais permissivamente.
3. **O registro**: `CRYSL-NAO-IMPLEMENTADO`, cuja definição no vocabulário do instrumento é
   *"the clause reaches no guard of the specification"* — literalmente falsa aqui.

Mas o reparo que o handoff propunha — trocar o veredito para `MOP-MAIS-PERMISSIVO` com âncora
`IvParameterSpec.mop:30` — **foi medido e reprova o portão**. G-CONF sobre o `jca` congelado, com o
monitor gerado nesta tarefa:

```
hoje    oracle_rows 80   agree 66   disagree 0   not-derived 14   unrecorded 0   failures 0
mutante oracle_rows 80   agree 65   disagree 1   not-derived 14   unrecorded 0   failures 1
        oracle-mismatch IvParameterSpecSpec IvParameterSpec.crysl:19
        derived=CRYSL-NAO-IMPLEMENTADO  recorded=MOP-MAIS-PERMISSIVO
```

A razão está no instrumento e é estrutural, não um descuido: `MOP-MAIS-PERMISSIVO` sai de
`_compare()`, que compara **listas de valores** canonicalizadas pela tabela de aliases — as duas
linhas que hoje o carregam são listas de algoritmo (`Mac.crysl:44`, `SecretKeySpec.crysl:18`). Para
cláusula numérica o instrumento diz de si mesmo, em comentário: *"A numeric bound is implemented
when some guard states the same relation; the record calls that IGUAL and nothing finer."* Ele
procura o literal `>0` no texto do guarda, acha `>=0`, e não tem célula para "mesma variável,
relação mais fraca".

**Portanto o reparo certo é de instrumento e não de linha**, e ele move um número que o
`docs/20260821_conformidade_mop_crysl.md` reproduz sobre o controle congelado (a razão de
implementadas/comparáveis do §13). Isso é decisão do pesquisador, sobre a árvore congelada, fora do
que a 11.7 pode fechar sozinha. **Fica registrado aqui, medido dos dois lados, e nada foi editado.**

## 8. O registro de divergências, e a paridade

```
gh104_divergence_record.py --check  ->  exit 0
305 hunk(s), all recorded; 26 narrative entr(ies)
```

A trajetória, contra os `306 hunks / 26 narrativas` da 10.11, em três medidas: **306 → 308** com as
tarefas 11.2 a 11.5 (a 11.5(e) inseriu dois hunks no `CipherSpec` que são janela do differ e não
divergência, e a linha nova de cada um diz isso) e **308 → 305** com a 11.6. Os três que saíram são
do `KeyPairSpec`: desfazer a divergência da 9.11 fez o `ere` sair do diff seed→sucessor e os
vizinhos se fundirem, com as razões das linhas absorvidas nas que as absorveram. É o único movimento
de hunk do grupo que é *fechamento* e não janela do differ. As narrativas não se moveram em nenhuma
das duas etapas: nenhuma tarefa do grupo 11 acrescentou linha sem hunk.

Linhas com etiqueta de tarefa do grupo, contadas: 11.1 → 1, 11.2 → 23, 11.3 → 2, 11.4 → 4,
11.5 → 38, **11.6 → 6**, 11.8 → 5, 11.9 → 1. Todas chaveadas; o `--check` reprova as duas direções.

Paridade, contrato de CI, com `RVSEC_HOME`, `ANDROID_HOME` e `ANDROID_SDK_HOME` setados:

```
3 failed, 185 passed in 422.97s
```

As três são as mesmas de sempre e nenhuma é desta change: `test_baseline_not_older_than_jar`,
`test_repo_is_clean` e `test_real_gator_json_parses_with_complete_true`. **Nenhuma quarta.** O
número de passados não subiu, e não devia: a 11.6 **removeu** um símbolo de teste
(`OPEN_ORDER_DIVERGENCES`) e uma função auxiliar sem remover asserção — as três funções que os liam
continuam lá, afirmando o estado novo.

## 9. Nenhuma tarefa fechou por código de saída

Por R5/R6, e vale nomear onde isso teve consequência nesta passagem, porque teve três vezes:

1. **A §5** existe porque a razão escrita da isenção foi lida contra o que o instrumento faz, e não
   contra o seu exit code. O `--check` saía 0, e saía 0 sem provar o que a isenção dizia que ele
   provava. O defeito do delta estava atrás disso.
2. **A §7** existe porque o reparo proposto foi *medido* antes de ser aplicado. Aplicado às cegas,
   teria deixado o G-CONF vermelho sobre o controle congelado.
3. **A restauração do `updateBuffer`** (11.6 §1) entrou na tarefa como "ganho de fidelidade só de
   registro, sem par de arnês" e a medição mostrou que ela é premissa do reparo do `ere`: com o
   evento apagado, o `+` seria satisfeito por movimento epsilon e a testemunha sobreviveria intacta.
   O portão teria saído verde na conta de passadas e errado na razão.
