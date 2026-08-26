# Tarefa 11.2 — o mapa de alfabeto re-derivado contra o oráculo único

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: derivação pura, nada se move
**Oráculo**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Instrumento**: `scripts/gh105_expert_alphabet.py` · **Saídas**:
`data/jca_android/order_alphabet_map_expert.csv` e `order_alphabet_map_delta.csv`

## 1. O que foi derivado, e por que não pelo nome

O `order_alphabet_map.csv` associa evento de `.mop` a símbolo de `ORDER`, uma linha por
associação, e cada uma das suas 138 linhas nomeia um símbolo e uma linha da api30. A associação em
si é **julgamento humano** — a INV-INS-138 proíbe inferi-la — e esta tarefa não a re-decide. O que
ela re-deriva é a **âncora**: dado que o `SecureRandomSpec.setSeed1` é o `setSeed(long)` da regra,
que símbolo é esse na regra expert, em que linha, dentro de que agregado.

O pareamento é **por assinatura e nunca por nome**, e isso não é preciosismo: os dois catálogos
permutam nomes sobre as mesmas chamadas.

| chamada | api30 | expert |
|---|---|---|
| `initialize(int)` | `i3` | `i1` |
| `initialize(int, _)` | `i4` | `i2` |
| `initialize(AlgorithmParameterSpec)` | `i1` | `i3` |
| `initialize(AlgorithmParameterSpec, _)` | `i2` | `i4` |

Essa é a permutação de quatro vias do `KeyPairGenerator`, e a do `Signature` troca `u1` com `u2`.
Uma reancoragem por nome pareceria mecânica e estaria errada exatamente onde importa: mandaria o
`init1` do `.mop`, que é `initialize(int)`, para o `i3` expert, que é `initialize(params)`.

A chave de assinatura é o método mais o tipo resolvido de cada argumento, com `*` onde a regra não
diz — um `_` do CrySL e um argumento que a regra deixou fora de OBJECTS são a mesma coisa, e as
duas ocorrem: a `Cipher.cryptsl` escreve `u2: update(pre_plaintext, pre_plain_off, _)` e a
`Signature.cryptsl` não declara `offset` nem `len` em OBJECTS. A aridade nunca é curinga. Um par
só se faz quando é **unívoco** nos dois sentidos; o resto sai como não pareado e vira linha do
delta, porque os casos ambíguos não são quase-acertos — são os lugares onde uma das duas regras
declara a mesma chamada duas vezes.

## 2. Os números

```
order_alphabet_map.csv         138 linhas, 22 especificações pareadas, 2 skips declarados
order_alphabet_map_expert.csv  137 linhas, as mesmas 22, os mesmos 2 skips
order_alphabet_map_delta.csv   152 linhas
```

| classe | linhas | o que é |
|---|---|---|
| `same-name` | 85 | a regra expert nomeia a mesma chamada pelo mesmo símbolo |
| `renamed` | 33 | mesma chamada, mesmo agrupamento, símbolo diferente |
| `order-unmapped` | 16 | a linha apaga o evento das duas linguagens (INV-INS-138) |
| `duplicate-settled` | 3 | duplicata da api30 resolvida por nome, com a razão escrita |
| `withdrawn-duplicate` | 1 | a linha existia só para reclamar uma duplicata da api30 |
| `uncovered-expert-symbol` | 8 | a regra expert declara e nenhum evento do conjunto observa |
| `withdrawn-api30-symbol` | 6 | a api30 declarava e a regra expert não |

**São 22 especificações pareadas, não 21.** A tarefa 11.2 escreve "the 21 paired specifications";
a enumeração sobre o catálogo dá 22, e as 22 estão nomeadas no delta. As duas fora são as de sempre
(`IvChainJunction`, `RandomStringPassword`), que continuam skip declarado em prosa e sem linha de
dado — o catálogo expert não enuncia regra para nenhuma das duas, que é a mesma razão que a api30
dava, agora dita contra o oráculo certo.

## 3. Onde os alfabetos realmente diferem

A tarefa manda listar isso em vez de presumir zero. São seis famílias, todas verificadas contra o
texto das duas regras.

**`Mac` — a regra api30 declarava duas chamadas duas vezes.** `g1` e `g2` transcrevem o mesmo
`getInstance(macAlg)`, e `u2` e `u4` o mesmo `update(pre_input)`; o defeito está na fonte dela
também (`MetaCrySL samples/jca/base/Mac.cryptsl:17-18,26,28`). O expert escreve
`g2: getInstance(algorithm, _)` (`:20`) e `u4: update(preInputByteBuffer)` (`:30`) — duas chamadas
de verdade. Consequência de registro: a linha `MacSpec.updateBytes -> u4`, que existia só para que
nenhum símbolo da regra ficasse sem dono, é **retirada** (é a única linha a menos das 138).

**`Mac` — o ORDER separa o que a api30 fundia.** api30: `Gets, Inits, (Finals | (Updates+, Finals))`,
com `Finals` nos dois ramos. Expert: `Get, Init, (FinalWU | (Update+, Final))`, com
`FinalWU := f2` (o `doFinal(byte[])` de um tiro) apartado de `FinalWOU := f1 | f3`. A regra expert
**não aceita** `getInstance; init; doFinal()` — um MAC sobre nada — e a api30 aceitava.

**`SecureRandom` — `nextInt` existe.** A api30 nomeava `ne: next(numB)`, o `next(int)` protegido, e
nenhum evento `nextInt`. O expert declara `nI: randInt = nextInt()` (`:32`) e
`nIR: randIntInRange = nextInt(range)` (`:33`), ambos dentro de `Next` (`:34`), que o ORDER alcança
por `End`. E o ORDER muda de forma: `Ins, Seeds?, Ends*` vira `Ins, (Seed?, End*)*`.

**`Cipher` — a família `updateAAD`.** O expert declara `ua1`, `ua2`, `ua3` e o agregado
`AADUpdate`, e põe `AADUpdate*` no ORDER; a api30 não tem nenhum dos quatro. Nenhum evento do
`CipherSpec` observa `updateAAD`, então os três entram como símbolo do lado da regra sem cobertura
— a mesma classe dos setters do `KeyStore`, que a 10.5(g) registrou.

**`CipherInputStream` / `CipherOutputStream` — o construtor de um argumento sai.** A api30 declarava
`c1: CipherInputStream(is)` e o nomeava dentro de `Constructs`; o expert declara só o construtor de
dois argumentos. O `.mop` já apontava só para o de dois (o de um é `protected` no android-30 e
nenhum sítio de aplicação o alcança), então o que era estreitamento deliberado do pointcut virou o
próprio alfabeto.

**`KeyPair` — o construtor é obrigatório.** api30: `co?, (pu*, pr*)*`. Expert: `Con, (GetPubl |
GetPriv)*`. É o caso que a D-16 já nomeia, e a §6 mostra o que ele faz ao portão.

**`KeyStore` — os três setters saem.** `scE`, `skE1` e `skE2` eram declarados pela api30 e nomeados
por nenhum ORDER (nem o dela); o expert não os declara. O cabeçalho do mapa api30 já dizia isso
desde a 10.5(g), como consequência da D-16; agora é linha de tabela e não parágrafo.

## 4. Três apagamentos que perdem o chão — e ficam onde estão

Três linhas `order-unmapped` foram escritas porque a **api30** não nomeava a chamada. O catálogo
expert nomeia as três:

| linha | chamada | símbolo expert |
|---|---|---|
| `MacSpec.updateBuffer` | `update(ByteBuffer)` | `u4` (`Mac.crysl:30`), dentro de `Update` |
| `SecureRandomSpec.next1` | `nextInt(int)` | `nIR` (`SecureRandom.crysl:33`), dentro de `Next` |
| `SecureRandomSpec.next3` | `nextInt()` | `nI` (`SecureRandom.crysl:32`), dentro de `Next` |

**As três mantêm a disposição `order-unmapped` no mapa expert, de propósito.** Mapear qualquer uma
muda a linguagem contra a qual o autômato é comparado, e isso é mudança de comportamento: entra por
11.5/11.6, com par de arnês e decisão do pesquisador por cláusula. O que a 11.2 faz é registrar —
e a razão de cada uma das três linhas foi reescrita para dizer exatamente isso, em vez de continuar
afirmando que a chamada não existe na regra.

## 5. As razões que foram reescritas

Vinte razões do arquivo afirmavam algo sobre a api30 — uma linha dela, um símbolo dela, ou uma
verruga que só ela tinha. Contra o oráculo único essas afirmações são **falsas**, e registro cuja
razão contradiz a própria âncora é pior do que registro sem razão. As vinte foram reescritas contra
o texto expert e vivem em `REASON_OVERRIDES`, no script, cada uma conferida em 26/08; as outras 63
razões sobreviveram literalmente, porque valem nos dois catálogos. O `--check` reprova um override
escrito e não aplicado, pela mesma lógica: prosa que ninguém lê mais, ao lado de prosa conferida.

Duas delas são o exemplo do que a reescrita compra. A razão de `CipherOutputStreamSpec.w1 -> w2`
carregava um aviso — a regra api30 declarava o parâmetro `byte[]` sob um objeto chamado
literalmente `byte`, e ler o `w2` dela como a sobrecarga inteira era risco vivo. O expert tipa as
duas posições (`int specifiedByte`, `byte[] data`) e o risco sumiu; a razão diz isso em vez de
repetir um cuidado que não se aplica mais. E a de `SSLContextSpec.init` passa a dizer por que o
`i1: init(km, tm, random)` expert importa: ele **liga** a terceira posição como
`java.security.SecureRandom`, que é o que dá sujeito à cláusula `randomized[random]` (`:34`) e
aposenta a disposição `vacuous` da cláusula #30 do ledger — o delta que a D-16 nomeia.

## 6. O que o G-ORDER diz sob o par expert (medida, não previsão)

O portão ainda lê a api30 por padrão; apontá-lo é a 11.3. Mas a medida com os dois insumos trocados
é barata e é o que diz o que a 11.3 e a 11.5/11.6 vão encontrar:

```
python3 scripts/gh105_order_gate.py --sets jca_android \
  --rules  RVSec-replication-package/tools/rules \
  --map    data/jca_android/order_alphabet_map_expert.csv

G-ORDER: 13 passed, 6 failed, 3 allow-listed, 2 skipped of 24 specifications
```

Contra `14 passed, 0 failed, 8 allow-listed, 2 skipped` sob a api30. As seis falhas se separam em
duas classes, e a diferença entre elas é toda a informação:

**Quatro são a mesma divergência com outro nome.** O `gate_allowlist.csv` chaveia a linha pelo texto
da testemunha, e a testemunha é escrita em símbolos da regra:

| especificação | testemunha api30 | testemunha expert |
|---|---|---|
| `CipherOutputStreamSpec` | `c2 c` | `c1 cl1` |
| `KeyGeneratorSpec` | `g1 g1 gk` | `g1 g1 gk1` |
| `SSLContextSpec` | `g1 Init se1 se1` | `g1 i1 se1 se1` |
| `SecretKeySpec` | `d` | `d1` |

Nenhuma delas é divergência nova: é a linha do allowlist que precisa ser rechaveada quando os
instrumentos virarem, o que é serviço da 11.3/11.4.

**Duas são divergências que a api30 não enxergava**, e as duas já estão previstas pela D-16:

- `KeyPairSpec`, testemunha **`a sequência vazia`**: o ORDER expert exige o construtor (`Con, …`) e
  o autômato da especificação aceita o vazio, porque a 9.11 escreveu `(c1 | epsilon)` sobre 668
  linhas de corpus medidas — a plataforma constrói o par internamente e a aplicação nunca chama o
  construtor. É exatamente o caso que a D-16 manda tratar como **divergência registrada contra a
  regra expert, adjudicada pelo pesquisador**, e não como obediência.
- `MacSpec`, testemunha **`g1 i1 f1`**: `getInstance; init; doFinal()` — um MAC sobre nada. O ORDER
  expert recusa (o `f1` só entra por `Final`, depois de `Update+`) e o da api30 aceitava, porque
  fundia os dois ramos em `Finals`. Divergência nova, comportamental, sem decisão tomada.

**Uma allow-list deixa de ser necessária.** O `CipherInputStreamSpec` passa a **passar**: a
testemunha `c1 r1 c` que a linha perdoava vinha do construtor de um argumento que só a api30
declarava. Sob o oráculo único não há o que perdoar.

Um detalhe do instrumento que a 11.3 herda: as mensagens do portão dizem "the api30 ORDER"
literalmente, em texto fixo. Sob o oráculo único isso passa a ser mentira de rótulo.

## 7. O que esta tarefa não fez

Não apontou instrumento nenhum (11.3), não mexeu em `conformance_record.csv` nem em
`gate_allowlist.csv` (11.4), não reparou nenhuma das duas divergências novas nem os três
apagamentos sem chão (11.5/11.6), e não tocou em uma linha de especificação. O
`order_alphabet_map.csv` continua sendo o mapa que o portão lê, com o cabeçalho apontando para o
sucessor. Rodando hoje, `gh105_order_gate.py --sets jca_android` continua saindo 0 com
`14 passed, 0 failed, 8 allow-listed`.
