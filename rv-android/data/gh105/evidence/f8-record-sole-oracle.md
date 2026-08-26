# Tarefa 11.4 — os registros e o texto das specs param de nomear o catálogo retirado

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: reancoragem de registro, com censo
**Oráculo único**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Insumo retirado**: `MetaCrySL/generated/api30/` — sem papel de oráculo em nenhuma dimensão

## 1. O que a tarefa fez

Três superfícies do conjunto sucessor citavam a api30 como autoridade: os registros de
`data/jca_android/`, os comentários dos `.mop` e as strings emitidas. A tarefa fecha as duas
primeiras e deixa a terceira para a 11.8, de propósito — o portão fica vermelho enquanto ela
existir, que é o que prova a 11.8 completa quando fechar.

| entrega | onde |
|---|---|
| instrumento de conformidade cláusula a cláusula | `scripts/gh105_expert_conformance.py` |
| portão de grep do grupo | `scripts/gh105_sole_oracle_gate.py` |
| registro de conformidade re-ancorado numa coluna `rule` só | `data/jca_android/conformance_record.csv` |
| censo dos dois catálogos | `data/jca_android/conformance_record_delta.csv` |
| adendos D-16 no registro de divergências | `data/jca_android/divergence_record.csv` |
| declaração de oráculo único | `data/jca_android/README.md` |
| linhas G-ORDER re-justificadas contra a ORDER expert | `data/jca_android/gate_allowlist.csv` |
| grafo de predicados re-citado | `data/jca_android/predicate_graph.csv` |
| varredura dos comentários das 20 specs | `rvsec-mop/src/main/resources/jca_android/*.mop` |

## 2. O censo: 98 cláusulas, e três que estão invertidas

`gh105_expert_conformance.py --emit delta` pareia os dois catálogos cláusula a cláusula, em quatro
estágios (forma exata → objetos renomeados → valores diferentes → ambos), cada estágio só fazendo
par quando ele é unívoco nos dois sentidos. O que os estágios recusam vai para `PAIRING_OVERRIDES`
com a razão escrita. **Nenhum veredito é decidido pelo instrumento**: o que se re-deriva é a
âncora.

| disposição | cláusulas |
|---|---:|
| par (idêntica, renomeada, valores diferentes, split, merged) | **35** |
| retirada (só a api30 tinha) | **17** |
| restaurada (só o oráculo tem) | **43** |
| **invertida** | **3** |
| total | **98** |

As três invertidas são a terceira dimensão em que a api30 se mostrou defeituosa, depois dos
valores (D-15) e da fiação (D-16):

| api30 | oráculo |
|---|---|
| `Cipher.cryptsl:131` `length(pre_ciphertext) <= pre_ciphertext_off` | `Cipher.crysl:123` `length[preCipherText] >= preCipherTextOffset` |
| `Cipher.cryptsl:133` `length(plainText) <= plain_off + len` | `Cipher.crysl:127` `length[plainText] >= plainTextOffset + plainTextLen` |
| `Cipher.cryptsl:135` `length(cipherText) <= ciphertext_off` | `Cipher.crysl:128` `length[cipherText] >= cipherTextOffset` |

São satisfeitas exatamente onde o oráculo é violado. Que isto é defeito da cadeia geradora e não
dialeto se lê na quarta cláusula da mesma família: a `Cipher.cryptsl:129` **não** está invertida.
Um dialeto que trocasse o sentido da comparação trocaria nas quatro.

## 3. `conformance_record.csv`: 116 → 108 linhas, uma coluna `rule`

O registro nomeava duas regras por especificação. Passa a nomear uma, a expert, e a citação da
api30 sobrevive dentro do adendo de supersessão de cada linha derivada contra ela.

- **dezesseis** linhas passam a `withdrawn` — a cláusula que as ancorava não existe no oráculo;
- **dez** somem por fusão: diferiam a mesma constante duas vezes, sob duas autoridades;
- **duas** entram, `IvParameterSpec.crysl:17` e `:18`, como `transcription`, porque o guarda do
  `c2` já as implementa e o registro nunca as teve — a regra gerada não declarava CONSTRAINTS
  alguma para `IvParameterSpec`.

O `--check` reprova três coisas, e cada uma é um jeito diferente de o registro voltar a ter dois
oráculos: coluna `rule` nomeando um `.cryptsl`; linha citando o catálogo retirado sem adendo; e
censo aberto — cláusula do oráculo sem linha que a ancore, ou retirada ancorada por um número de
linhas diferente de um.

## 4. `gate_allowlist.csv`: quatro linhas re-chaveadas, uma fecha

As testemunhas do G-ORDER estavam escritas nos símbolos do catálogo retirado, então quatro linhas
deixavam de casar sem que nada no conjunto tivesse mudado:

| espec | testemunha | era |
|---|---|---|
| `CipherOutputStreamSpec` | `c1 cl1` | `c2 c` |
| `KeyGeneratorSpec` | `g1 g1 gk1` | `g1 g1 gk` |
| `SSLContextSpec` | `g1 i1 se1 se1` | `g1 Init se1 se1` |
| `SecretKeySpec` | `d1` | `d` |

Uma quinta **fecha**: a linha do `CipherInputStreamSpec` perdoava `c1 r1 c`, uma testemunha cujo
símbolo `c` vinha do construtor de um argumento que só a api30 declarava. Contra o oráculo o
`CipherInputStreamSpec` passa, e a linha deixa de ser uma decisão de perdoar coisa nenhuma.

**G-ORDER hoje: 13 passadas / 2 falhas / 7 perdoadas**, e as sete são o número que o
`tests/parity/test_gh105_predicate_gates.py` afirma. As duas falhas são da 11.6 — `KeyPairSpec`
(sequência vazia) e `MacSpec` (`g1 i1 f1`).

## 5. A varredura dos comentários: 20 specs, e sete frases que caíram

A D-17 escrita como regra: *uma frase que a substituição torna falsa não move o veredito, mas move
a premissa — e é a premissa que uma tarefa posterior reusa.* Foi o que fez a varredura valer. As
frases abaixo tinham conclusão de pé e razão de outra classe; nenhuma delas mudou o que o conjunto
acusa.

| spec | a frase que caiu | o que o oráculo diz |
|---|---|---|
| `IvParameterSpec` | "a regra não declara CONSTRAINTS alguma" | declara três (`:17-19`); o guarda do `c2` implementa duas |
| `GCMParameterSpecSpec` | os três conjuntos de faixa "não traduzem cláusula" | traduzem `GCMParameterSpec.crysl:19-21` |
| `SSLContextSpec` | `randomized[sr]` "vacuosa, não liga `sr` em evento algum" | `i1: init(km, tm, random)` liga — abrir é **11.5(b)** |
| `PBEKeySpecSpec` (×2) | "sua única cláusula de CONSTRAINTS é `neverTypeOf(...)`" | são duas, com `notHardCoded[password]` (`:25-26`) |
| `KeyPairSpec` | "ORDER responde à api30 e valores à expert" | a convenção acabou com a D-16; a `KeyPair.crysl:20` ordena o construtor obrigatório — **11.6** |
| `CipherSpec` | "a regra do `Mac` não declara evento de `ByteBuffer`" | declara (`u4`); o que não faz é garantir `macced` sobre um |
| `CipherSpec` | `w: wrap(wrappedKey)` "não é nomeado em ENSURES alguma" | a `:78` declara `wkb1` e a `:148` garante `wrappedKey[...]` — **11.5(e)** |
| `SecretKeySpecSpec` | "a única cláusula de CONSTRAINTS da regra" | são três |
| `SecureRandomSpec` | "garante `randomized` sobre três objetos" | cinco (`:49-53`); duas são da 11.5 |

As três últimas specs da varredura entraram nesta passagem e trouxeram mais três:

- **`MacSpec.i1`/`i2`** diziam que o guarda de `generatedKey` apagado pela 4.9 "não traduz cláusula
  alguma". A `Mac.crysl:54` REQUIRES `generatedKey[key,_]` — quarta cláusula de REQUIRES, que a
  regra gerada não tinha — e a linha 39 do `predicate_ledger.csv` a dispõe `wireable` com os dois
  lados especificados no conjunto. **A deleção não se reverte aqui**: restaurar a leitura é a
  **11.5(a)**, que anda com par de arnês e decisão por cláusula. O que muda é a razão escrita.
- **`MacSpec.updateBuffer`** dizia que `update(ByteBuffer)` é sobrecarga que a regra não declara. A
  `Mac.crysl:30` declara `u4: update(preInputByteBuffer)` e a `:31` o põe dentro de `Update`. O que
  a regra continua não fazendo é garantir `macced` sobre um `ByteBuffer` — a mesma leitura que o
  `CipherSpec.f7` carrega na ponta consumidora. O mapa de alfabeto o mantém `order-unmapped` de
  propósito (11.2): mapear muda a linguagem comparada, e isso é 11.5/11.6.
- **`SignatureSpec.v1`/`v2`** diziam traduzir `verified[sign]`, cláusula de uma casa e sem `after
  L`. A `Signature.crysl:61` diz `verified[verified, sign] after Verify`. **Nenhuma das duas
  diferenças move o sítio**: a escrita fica em uma casa porque nenhuma das 49 regras exige
  `verified`, e o `after Verify` chega ao mesmo `@match`, porque `v1` e `v2` param no estado 4, que
  a categoria de match contém. A linha 68 do `predicate_graph.csv` ganhou a cauda da segunda
  diferença — o adendo D-16 registrava só a aridade.

Duas frases se corrigiram sem que a substituição as tivesse tornado falsas, e ficam anotadas como
tal: o `MacSpec.f1Input` dizia que a regra põe `f1` e `f2` no mesmo `FinalWU` (a
`Mac.crysl:36-37` não põe, e é daí que sai a falha `g1 i1 f1`), e o comentário do `ere` do
`MacSpec` dizia que o G-ORDER não reportava divergência ali (reporta uma, desde a reancoragem
da 11.2).

### A medição do `HMACParameterSpec`, refeita

A razão da disposição `unreachable-composition` da cláusula `preparedHMAC[params]` corria sobre os
**doze** nomes da lista retirada. O oráculo nomeia **nove**, e oito deles estavam entre os doze —
`HmacPBESHA1` nunca fora medido. Refeita sobre os nove da `Mac.crysl:44`, em Temurin 21:

```
HmacSHA256 / HmacSHA384 / HmacSHA512      -> InvalidAlgorithmParameterException: HMAC does not use parameters
HmacPBESHA1                               -> InvalidAlgorithmParameterException: PBEParameterSpec type required
PBEWithHmacSHA1 / 224 / 256 / 384 / 512   -> InvalidAlgorithmParameterException: PBEParameterSpec type required
```

`HmacPBESHA1` exige uma `PBEKey` antes de olhar para o parâmetro, então a medição usou uma
implementação mínima de `javax.crypto.interfaces.PBEKey`; com uma `SecretKeySpec` ela para antes,
em `InvalidKeyException: Missing password`. **Todos os nove resolvem**, o que é a única diferença
contra a medição antiga — a lista retirada nomeava `PBEwithHmacSHA`, que nenhum provedor tem. A
conclusão é a que era: nenhum `Mac` que a regra admite aceita um `HMACParameterSpec`, e a
disposição fica onde estava (tarefa 11.9(b) a re-cita).

## 6. A curva do portão

`gh105_sole_oracle_gate.py` lê as três superfícies e conta o que pulou, para que uma corrida que
parou de olhar não se confunda com uma que não achou nada. Oito registros são isentos por
declaração, com a razão escrita; seis deles são saída dos instrumentos das 11.1/11.2/11.4, cujo
`--check` reproduz o arquivo e pega edição à mão.

| momento | achados |
|---|---:|
| abertura da tarefa | **231** |
| depois dos registros e das duas primeiras levas de comentários | 45 |
| depois do `MacSpec` (26 comentários + 1 resumo de hunk) | 18 |
| depois do `SignatureSpec` (12 comentários) | 6 |
| depois do `KeyPairGeneratorSpec` (1 comentário) | **5** |

Os cinco que restam são as mensagens da **11.8** — `GCMPARAMETERSPEC-CONSTR-00` e `-02`,
`PBEKEYSPEC-FORB-00` e `-01`, `SSLCONTEXT-FORB-00`. O portão fica vermelho até lá de propósito.

Duas linhas citam o catálogo pelo nome de um `kind` do `divergence_record.csv` (`api30-omits`, no
`SignatureSpec` e no `KeyPairGeneratorSpec`). O `kind` é chave de registro e não se renomeia: as
frases passam a dizer isso, e é a decisão que a linha carrega.

## 7. Efeitos colaterais que a passagem teve de tratar

- **Âncoras do `codes.csv`**: 17 códigos mudaram de linha (4 no `MacSpec`, 13 nas outras), porque
  qualquer linha inserida acima de um sítio de report as move. O `code-anchor` do portão de
  mensagem acusa e **diz a linha certa**; o `reanchor_codes.py` consome isso direto.
- **Re-chaveamento de hunks**: 16 linhas do `divergence_record.csv` re-chaveadas, por posição
  contra o `HEAD` do git, porque editar comentário re-chaveia o hunk e muda o resumo junto quando a
  edição toca a primeira linha dele.
- **Um hunk que se partiu**: o bloco de comentário do `MacSpec.i2` cresceu o bastante para que o
  `difflib`, a `n=0`, passasse a casar como inalterado o `}` que fecha o corpo do `i1`. Uma corrida
  virou duas, e o registro ganha a linha `b41d2fa9eab5`. **É janela do differ, não divergência
  nova**: nenhuma linha de programa mudou com ela, e a razão da linha diz isso. O `rekey2.py`
  recusa contagens diferentes de propósito, então o pareamento com deslocamento foi feito por um
  segundo instrumento que imprime o alinhamento antes de aplicá-lo.

## 8. Dívida herdada da 11.3, paga

`scripts/gh104_baseline.py:1912` emitia, em voz presente, *"This is what makes
`MetaCrySL/generated/api30/*.cryptsl` **the** oracle and not one option among several"*. Passa ao
pretérito, diz que a D-16 retirou o catálogo, e diz que o conjunto sucessor responde à cópia
expert. O `data/gh104/baseline.md` foi regerado: **só essa linha muda**, e o `baseline.json` fica
byte a byte o mesmo — que é o que o `test_baseline_reproduces_byte_identical` afirma.

As outras duas menções do mesmo arquivo (`:775`, `:1769`) descrevem contra o que a medição de
agosto foi feita, em contexto passado, e são exatas como história.

## 9. Observações que a passagem encontrou e **não** reparou

1. **`constraint_table.csv`, `IvParameterSpec.crysl:19` (`len > 0`)**: a linha 40 diz
   `CRYSL-NAO-IMPLEMENTADO` com âncora vazia. O `c2` do conjunto congelado **implementa** a
   cláusula, e mais permissivamente — `len >= 0` onde a regra pede `len > 0`
   (`jca/IvParameterSpec.mop:30`). O veredito certo é `MOP-MAIS-PERMISSIVO` com âncora. Mexer nele
   move um número que o G-CONF reproduz sobre o controle congelado, o que é medição e não texto:
   fora do escopo da 11.4.
2. **A âncora `.mop` do `constraint_table.csv` foi verificada e está certa** — o registro do
   handoff que a dava por estagnada estava errado. As 24 âncoras que apontam para o conjunto
   resolvem contra o **seed `jca`**, que é o conjunto de que a tabela é oráculo
   (`gh104_gates.py:1868-1872`); contra o `jca_android` 15 delas caem em comentário ou cabeçalho,
   e é essa leitura que produz o falso positivo. Nada a reparar.
3. **`MacSpec`, três CONSTRAINTS de janela não implementadas**: a `Mac.crysl:46-48`
   (`length[preInput] >= offset + len`, `offset >= 0`, `len > 0`) não tem sítio no `.mop`. Já
   consta como `CRYSL-NAO-IMPLEMENTADO` nas linhas 58-60 do `constraint_table.csv`, e o comentário
   do `updateRange` passa a dizer isso em vez de deixar entender que a regra nada diz da janela.
   Fechá-las é classe de acusação nova, que a D-16 mantém fora desta mudança.
4. **`MacSpec.f1`, um parágrafo estagnado**: o bloco acima do `f1` dizia que o evento "funde `f1` e
   `f2` sob uma disjunção de pointcut", coisa que deixou de ser verdade quando o `f1Input` se
   separou. Não é efeito da substituição — é anterior a ela — mas o parágrafo estava sendo
   reescrito, então a frase passou a descrever o estado atual (P4).

## 10. Bateria, ao fechar a tarefa

```
gh105_sole_oracle_gate      exit=1  ← as cinco mensagens da 11.8
gh105_expert_conformance    exit=0     gh104_divergence_record   exit=0
gh105_expert_ledger         exit=0     gh104_message_gate        exit=0
gh105_expert_alphabet       exit=0     gh104_mop_lint            exit=0
gh105_predicate_graph       exit=0     gh104_gates               exit=0
gh105_spec_gates            exit=0     gh105_order_gate          exit=1  ← as duas da 11.6
```

O `gh104_gates` correu sobre monitor gerado nesta árvore, com `--crysl` na cópia expert: nove
portões, `ok=true`, `skipped` vazio, G-PRED em `superseded`.

**Paridade: 185 passed / 3 failed** — a linha de base, com as mesmas três falhas pré-existentes de
outras frentes (`test_baseline_not_older_than_jar`, `test_repo_is_clean`,
`test_real_gator_json_parses_with_complete_true`). Sem quarta falha.
