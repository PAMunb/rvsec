# Tarefa 11.8 — as cinco mensagens emitidas deixam de citar o catálogo retirado

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: rótulo, medido contra veredito
**Oráculo único**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Par de arnês**: 173 traços, **173 `unchanged`**

## 1. O que a tarefa fez

Cinco strings entregues ao `ErrorDescription` nomeavam a api30 como a autoridade da acusação.
Isto é texto que **sai do repositório**: é o que uma pessoa lê num relatório de violação, e sob a
D-16 citava um oráculo que não existe mais.

| código | sítio | era | é |
|---|---|---|---|
| `GCMPARAMETERSPEC-CONSTR-00` | `GCMParameterSpecSpec.mop`, `c1` | `exp='a tag length api30 GCMParameterSpec.cryptsl admits'` | `exp='a tag length the expert GCMParameterSpec.crysl admits'` |
| `GCMPARAMETERSPEC-CONSTR-02` | idem, `c2` | idem | idem |
| `PBEKEYSPEC-FORB-00` | `PBEKeySpecSpec.mop`, `f1` | `msg='… is forbidden by api30 PBEKeySpec.cryptsl'` | `msg='… is forbidden by the expert PBEKeySpec.crysl'` |
| `PBEKEYSPEC-FORB-01` | idem, `f2` | idem | idem |
| `SSLCONTEXT-FORB-00` | `SSLContextSpec.mop`, `getDefault` | `msg='… is forbidden by api30 SSLContext.cryptsl'` | `msg='… is forbidden by the expert SSLContext.crysl'` |

A sexta desta família foi reparada pela **10.6** (`KEYPAIRGENERATOR-KEYSIZE-00`), que chegou só
àquela porque trabalhou sobre os achados de uma validação interna e não sobre uma varredura. Esta
tarefa varreu as strings de report do conjunto, que é o método que o `gh105_sole_oracle_gate.py`
executa: **as cinco eram todas as que restavam, e depois delas o portão dá 0 achados**.

## 2. A âncora por linha ficou no comentário, e não na string

A tarefa pedia que cada mensagem fosse reancorada na cláusula que implementa, **citada por
linha**. A primeira passada escreveu a linha dentro do envelope — `GCMParameterSpec.crysl:18`,
`PBEKeySpec.crysl:10`, `:11`, `SSLContext.crysl:11` — e o `gh104_message_gate.py` reprovou as
cinco, com razão:

```
literal-mismatch GCMParameterSpecSpec.mop:65   the message says 18 and the guard uses no literal
literal-mismatch GCMParameterSpecSpec.mop:112  the message says 18 and the guard uses no literal
literal-mismatch PBEKeySpecSpec.mop:44         the message says 10 and the guard uses no literal
literal-mismatch PBEKeySpecSpec.mop:51         the message says 11 and the guard uses no literal
literal-mismatch SSLContextSpec.mop:125        the message says 11 and the guard uses no literal
```

O portão lê **numeral em mensagem como literal de valor** e o compara com os do guarda — é a
checagem que impede uma mensagem de dizer que esperava `{96,104,112,128}` quando o guarda testa
outra coisa. Um número de linha no envelope é indistinguível disso: para o portão, e para quem lê
o relatório, `crysl:18` parece uma afirmação sobre o argumento.

Então a linha da cláusula foi para o **comentário ao lado do sítio**, que é onde um mantenedor a
lê, e a string nomeia a regra. Isso está escrito nos três arquivos, com a razão, para que a
próxima passagem não a devolva ao envelope. O `.mop` ganha a citação exata:
`GCMParameterSpec.crysl:18` (e a REQUIRES `:24`, que já tinha sítio), `PBEKeySpec.crysl:10` e
`:11`, `SSLContext.crysl:11`.

Consequência prevista pela própria tarefa e paga: **20 âncoras do `codes.csv` andaram** (7 no
`GCMParameterSpecSpec`, 6 no `PBEKeySpecSpec`, 7 no `SSLContextSpec`), porque linha acrescentada
acima de um sítio de report move todas as que vêm depois. O `code-anchor` do portão de mensagem
acusa e **diz a linha certa de cada código**.

## 3. É rótulo e não veredito, e o par prova

As três cláusulas dizem a mesma coisa nos dois catálogos, e isto foi verificado no texto e não
assumido:

| cláusula | oráculo | catálogo retirado |
|---|---|---|
| comprimento da tag | `GCMParameterSpec.crysl:18` `tagLen in {96, 104, 112, 120, 128}` | `GCMParameterSpec.cryptsl:29` `tLen in {128, 120, 96, 112, 104}` |
| construtores proibidos | `PBEKeySpec.crysl:10,11` `PBEKeySpec(char[])`, `PBEKeySpec(char[],byte[],int)` | `PBEKeySpec.cryptsl:16,18`, os mesmos dois |
| `getDefault()` proibido | `SSLContext.crysl:11` | `SSLContext.cryptsl:18` |

Nenhum programa muda de classe, e o par de arnês mede isso em vez de afirmá-lo:

```
gh104_diff_harness.py --a <snapshot pré-11.8> --b <conjunto vivo> --traces data/gh104/traces
  traces: 173      counts: {"unchanged": 173}
```

Os cinco códigos são **exercitados** pelo corpus, o que é o que faz o par valer alguma coisa — um
`unchanged` sobre traços que não acionam a mensagem não mediria nada:

| traço | evento:código |
|---|---|
| `GCMParameterSpecSpec-badtaglen.txt` | `c1:GCMPARAMETERSPEC-CONSTR-00` |
| `GCMParameterSpecSpec-second-overload-badtaglen.txt` | `c2:GCMPARAMETERSPEC-CONSTR-02` |
| `PBEKeySpecSpec-forbidden.txt`, `-forbidden-then-clear.txt` | `f1:PBEKEYSPEC-FORB-00` |
| `PBEKeySpecSpec-forbidden3.txt` | `f2:PBEKEYSPEC-FORB-01` |
| `SSLContextSpec-getdefault.txt`, `-getdefault-engine.txt` | `getDefault:SSLCONTEXT-FORB-00` |

Relatórios commitados: `data/gh105/evidence/harness/f8-GCMParameterSpecSpec.md`,
`f8-PBEKeySpecSpec.md`, `f8-SSLContextSpec.md` — os três em que uma mensagem mudou. Os outros 21
relatórios da varredura não são commitados: dizem o mesmo que o agregado `173 unchanged`, e o que
prova que nada mais se moveu é o agregado, não vinte e um arquivos idênticos em conteúdo.

**Um par que lesse outra coisa seria esta tarefa errando**, não a medição surpreendendo: quereria
dizer que uma mensagem foi reancorada numa cláusula que o conjunto não implementa, e a edição
sairia.

## 4. Registro

As cinco linhas do `divergence_record.csv` que carregam os hunks editados foram re-chaveadas (a
edição de mensagem re-chaveia o hunk) e ganharam a coluna `task` com `11.8` e a cauda que diz o
que a string dizia, o que passa a dizer, qual cláusula implementa e onde está o par. Nenhuma linha
nova: as edições não acrescentaram nem removeram hunk.

## 5. Bateria, ao fechar a tarefa

```
gh105_sole_oracle_gate      exit=0  ← 0 achados; é o que prova a 11.8 completa
gh104_message_gate          exit=0     gh105_expert_ledger        exit=0
gh104_mop_lint              exit=0     gh105_expert_alphabet      exit=0
gh104_divergence_record     exit=0     gh105_expert_conformance   exit=0
gh105_predicate_graph       exit=0     gh105_spec_gates           exit=0
gh105_order_gate            exit=1  ← as duas da 11.6
```

**Paridade: 185 passed / 3 failed** — a linha de base, com as mesmas três falhas pré-existentes de
outras frentes. Sem quarta falha.

## 6. O que fica dito para quem vier depois

O portão do grupo agora dá **zero**. Ele continua sendo a prova de que a 11.8 fechou, e é por isso
que ele lê as três superfícies e não duas: escrito como "nenhum comentário `.mop`", ele passaria
por cima destas cinco strings, porque texto entregue ao `ErrorDescription` não é comentário.
