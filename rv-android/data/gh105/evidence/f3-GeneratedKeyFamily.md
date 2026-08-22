# Tarefas 5.6 e 5.7 — a família `generated*key`, e a aridade que a plataforma torna quase muda

**Data**: 2026-08-22 · **Lote**: B3, o quarto do Grupo 5 · **Commit**: um só
**Cláusulas**: ledger #5, #15, #16 (5.6) · #34, #35, #8 (5.7)
**Arquivos editados**: oito `.mop`, quatro registros de dados, uma suíte, oito traces novas
**Resultado em uma linha**: as seis cláusulas são **fiadas**, três outras que o oráculo enuncia
ao lado delas são **registradas vacuous**, e a medição que mais mudou o quadro diz que a JCA já
recusa o programa que a aridade da #5 existe para acusar.

---

## 1. O que as tarefas pediram, e o que a árvore respondeu

O enunciado da 5.6 lista quatro produtores. **Dois deles não existem como a tarefa os nomeia**, e
a árvore ganha do enunciado:

| o enunciado diz | a árvore diz |
|---|---|
| produtor `SecretKeyFactory` | **não há `SecretKeyFactorySpec.mop`**. O conjunto tem 24 arquivos e nenhum é esse. A regra existe no oráculo (`SecretKeyFactory.cryptsl:47`) e a 4.10 já registrara a ausência |
| produtor `KeyPairGenerator` | produz `generatedKeypair[kp, alg]`, **predicado diferente**, que a #5/#15/#16 não leem. A escrita dele já está no ponto de aceitação desde a 4.14 e é um beco sem leitor |
| produtores reais de `GENERATED_KEY` | **três**: `KeyGeneratorSpec:179`, `SecretKeySpecSpec:153`, `KeyStoreSpec:128` — todos em aridade 1 |
| leitores reais de `GENERATED_KEY` | **dois**, e o segundo é fácil de esquecer: `CipherSpec:118` e `SecretKeySpec:79` |

O enunciado da 5.6 também diz "zero new events", e isso se cumpriu: o `CipherSpec` continua em
**17 de 17** (INV-INS-145).

---

## 2. A medição que reenquadrou a #5

Antes de escrever qualquer leitura, um programa Java solto pôs cada ponta contra a outra
(achado 73). O que ele mediu sobre a aridade da #5 não estava previsto em tarefa nenhuma.

**A JCA recusa, ela própria, toda chave cujo algoritmo difere do do Cipher.** Temurin 21:

| composição | resultado |
|---|---|
| chave AES → `Cipher("AES/CBC/PKCS5Padding")` | **aceita** |
| chave HmacSHA256 → `Cipher("AES/CBC/PKCS5Padding")` | `InvalidKeyException: Wrong algorithm: AES or Rijndael required` |
| chave DESede → `Cipher("AES/CBC/PKCS5Padding")` | `InvalidKeyException: Wrong algorithm: AES or Rijndael required` |
| chave RSA privada → `Cipher("AES/CBC/PKCS5Padding")` | `InvalidKeyException: No installed provider supports this key` |
| chave AES → `Cipher("DESede/CBC/PKCS5Padding")` | `InvalidKeyException: Wrong algorithm: DESede or TripleDES required` |
| chave AES → `Cipher("RSA/ECB/PKCS1Padding")` | `InvalidKeyException: No installed provider supports this key` |
| `Cipher.getInstance("AES_128/CBC/PKCS5Padding")` | `NoSuchAlgorithmException` — o `part(0)` que a regra admite e nenhum provedor tem |

Duas consequências, e as duas decidiram desenho:

1. **O ramo VIOLATED da leitura em aridade 2 não tem caminho de execução que a plataforma
   permita completar.** A advice do `i2` é `before`, então a leitura roda e o relatório sai — na
   chamada que em seguida lança. O que a segunda posição compra é o **ramo SATISFIED**: uma chave
   AES responde ao Cipher AES e só a ele, e o limite de alcance continua distinguível do defeito.
   Isso é o oposto de "a aridade acha defeitos novos", e está aqui escrito em vez de suposto.
2. **O curinga `_` do `KeyStore` fica indistinguível do algoritmo concreto.** A regra escreve
   `generatedKey[key, _]` (`KeyStore.cryptsl:97`) e o `PredicateStore` não tem curinga. A única
   execução em que as duas leituras discordariam é uma que a JCA recusa. Então o sítio escreve
   `key.getAlgorithm()`, a diverg��ncia fica registrada, e o conjunto não paga uma mudança no
   substrato compartilhado por um único sítio (decisão 61 do pesquisador, 2026-08-22).

Uma terceira medição, sobre o mesmo `KeyStore`: **`getKey` devolve um objeto novo**, não o que
`setKeyEntry` recebeu — no PKCS12, um `javax.crypto.spec.SecretKeySpec` fresco sobre o mesmo
material. Um store keyado por identidade **não carrega predicado através de um key store**. É
por isso que a escrita do `KeyStoreSpec` tem de existir: a origem do que sai é estabelecida ali
ou em lugar nenhum.

As outras três cadeias compõem sem surpresa: `new KeyPair(kp.getPublic(), kp.getPrivate())` roda
e preserva identidade (os dois acessores devolvem o mesmo objeto em toda chamada, e o construtor
guarda as metades sem copiar); `initSign(priv)`/`initVerify(pub)` assinam e verificam; e
`mac.doFinal(data)` seguido de `cipher.doFinal(data)` sobre o **mesmo array** roda até o fim,
que é o mac-then-encrypt que a #8 proíbe.

---

## 3. A aridade sobe dos dois lados, e o segundo leitor quase passou despercebido

`validate` compara a **tupla de valores** (achado 35): uma escrita em aridade 2 lida por um
`validate` em aridade 1 devolve `VIOLATED` — evidência positiva de defeito — e não
`NOT_OBSERVED`. Cinco sítios sobem juntos, no mesmo commit:

| sítio | antes | agora | o valor da segunda posição |
|---|---|---|---|
| `KeyGeneratorSpec.@match` | 1 | 2 | o `alg` de `getInstance`, estagiado por `gk1` |
| `SecretKeySpecSpec.@match` | 1 | 2 | o `keyAlgorithm` do construtor, estagiado por `c1`/`c2` |
| `KeyStoreSpec.@match` | 1 | 2 | `key.getAlgorithm()` — a regra escreve `_` |
| `CipherSpec.i2` (leitura) | 1 | 2 | `CipherTransformationUtil.alg(c.getAlgorithm())` |
| `SecretKeySpec.e1` (leitura) | 1 | 2 | `secretKey.getAlgorithm()` |

**O `SecretKeySpec.e1` é o que quase passa.** Ele não traduz cláusula nenhuma — é a única ponte
de propagação do conjunto, e `SATISFIED` nele governa uma escrita em vez de uma acusação.
Deixado em aridade 1 ele passaria a receber VIOLATED para toda chave que o conjunto observa
sendo gerada, não estagiaria nada, e a ponte quebraria **em silêncio**: o sítio não reporta, e
a propagação quebrada só apareceria como acusação três especificações adiante (decisão 62).

Medido sobre os três produtores, o único par cujas grafias diferem é
`KeyGenerator.getInstance("BLOWFISH")`, cuja chave reporta `Blowfish` — e casa, porque as
posições de valor do store comparam `String` em minúsculas.

**A coluna `splitter` do grafo fica vazia e o splitter está aplicado.** O emissor detecta um
splitter pelo literal `.split(` no argumento, e este sítio chama `CipherTransformationUtil.alg`,
que é onde essa análise já vive, correta e testada, e que a utilidade api30 deliberadamente não
restata. Está registrado na coluna `reason` da linha.

---

## 4. As cláusulas fiadas, e as três registradas ao lado delas

| # | cláusula | sítios | disposição |
|---|---|---|---|
| 5 | `generatedKey[key, part(0,"/",transformation)]` | `CipherSpec.i2`, aridade 2 | **fiada** |
| 15 | `generatedPrivkey[consPriv]` | `KeyPairSpec.c1` | **fiada** — o arquivo não tinha sítio nenhum |
| 16 | `generatedPubkey[consPub]` | `KeyPairSpec.c1` | **fiada** |
| 34 | `generatedPrivkey[priv]` | `SignatureSpec.i1`, `i2` | **fiada** — dois sítios, um por sobrecarga |
| 35 | `generatedPubkey[pub]` | `SignatureSpec.i4` | **fiada** |
| 8 | `!macced[_, plainText]` | `CipherSpec.f5`, `f6`, `IvChainJunction.finalInput`, `finalRange` | **fiada**, quatro sítios |

E três que o oráculo enuncia ao lado e que **não ganham sítio**, cada uma por uma razão medida:

- **`macced[output1, inp]`** (`Mac.cryptsl:89`) — `inp` é um **`byte` primitivo**. Uma escrita o
  boxaria, o store é keyado por identidade, e nenhum `Cipher` recebe um `byte` como plainText:
  nenhuma leitura da cláusula consumidora poderia encontrar o que uma escrita ali registrou.
- **`generatedPubkey[key]` no KeyStore** (`KeyStore.cryptsl:101`) — `getKey` devolve `SecretKey`
  ou `PrivateKey`, **nunca** `PublicKey`; a metade pública de um certificado sai de
  `getCertificate`, chamada que esta especificação não observa.
- **`CipherSpec.f7`** para a #8 — liga um `ByteBuffer`, e nenhum sítio do conjunto pode marcar um
  sob este predicado (a regra do `Mac` não declara evento de `ByteBuffer`). Como `validateAbsent`
  nunca responde `NOT_OBSERVED`, a leitura ali só poderia responder `SATISFIED`: sítio sem
  caminho para acusação, que a decisão 19 apaga em vez de escrever.

O `SignatureSpec.i3` também não lê: liga um `Certificate`, e a api30 não enuncia cláusula sobre
ele. A assimetria é do oráculo e fica registrada.

---

## 5. Onde os sítios da #8 couberam, e por quê

O `CipherSpec` está em 17 de 17 eventos, e o evento 18 estoura `StackOverflowError` no parser do
enable-set em qualquer heap (INV-INS-145). O `f2` dele é `call(public byte[] Cipher.doFinal(..))`
e cobre **três** sobrecargas sem ligar argumento nenhum — inclusive `doFinal(byte[])`, que é como
praticamente todo programa cifra.

Então a cláusula se divide por construção, não por gosto: `f5` e `f6` a leem no próprio
`CipherSpec` porque já ligam o `plainText`, e as duas sobrecargas dominantes vão para dois
eventos novos do `IvChainJunction.mop` — o arquivo que existe exatamente para ligar argumento de
chamada do `Cipher` que o `CipherSpec` não tem espaço para ligar. O universo enumerado fica em
**215**: nenhum `.mop` novo, e o G-PARAM segue em 23 comparadas mais uma pulada.

Do lado produtor, o `MacSpec` tinha **zero sítios** de `MACED` e nem `@match` — a 4.9 apagara o
handler inteiro quando a contabilidade de estado aceitante saiu. Ele volta, agora com cláusula
para escrever. E os eventos que ligam o dado tiveram de ser criados: `update(..)` e a disjunção
de `doFinal` não ligavam argumento nenhum, que é o defeito do achado 74. Um evento por
sobrecarga, tipos por extenso (achado 79):

| evento | símbolo da regra | liga |
|---|---|---|
| `update` (estreitado) | `u1: update(inp)` | nada — a cláusula é vacuous |
| `updateBytes` | `u2`/`u4: update(pre_input)` | o array |
| `updateRange` | `u3: update(pre_input, offset, len)` | o array |
| `updateBuffer` | — | nada; a api30 não declara essa sobrecarga |
| `f1` (estreitado) | `f1: output1 = doFinal()` | nada |
| `f1Input` | `f2: output2 = doFinal(input)` | o array |

O `updateBuffer` existe por conservadorismo declarado: o pointcut agregado que ele substitui
casava `update(ByteBuffer)`, e apagá-lo estreitaria em silêncio o que o autômato observa — uma
mudança de alfabeto que cláusula nenhuma pede. A regra põe u1 a u4 numa alternação só, então o
split não move afirmação de ordenação nenhuma.

---

## 6. O que o harness mediu

122 traces (114 antes; oito novas), pré-imagem contra a árvore:

| classe | antes | agora |
|---|---|---|
| unchanged | 71 | **69** |
| moved | 25 | **26** |
| introduced | 8 | **17** |
| removed | 10 | **10** |

As **nove `introduced` novas**, uma a uma:

| trace | código | é defeito? |
|---|---|---|
| `CipherSpec-keygen-key-mismatch.txt` *(nova)* | `CIPHER-CONSTR-00` | **sim** — chave HmacSHA256 num Cipher AES. É o ramo que a aridade 2 abre, e é o programa que a JCA recusa |
| `MacSpec-mac-then-encrypt.txt` *(nova)* | `IVCHAINJUNCTION-CONSTR-06` | **sim** — mac-then-encrypt sobre o mesmo array |
| `MacSpec-update-then-encrypt.txt` *(nova)* | `IVCHAINJUNCTION-CONSTR-06` | **sim** — o mesmo, escrito de forma incremental |
| `SignatureSpec.txt` | `SIGNATURE-NOBS-00` | **limite de alcance, honesto**: o programa é `s.initSign(null)` |
| `SignatureSpec-ecdsa.txt` | `SIGNATURE-NOBS-00` | idem |
| `SignatureSpec-initsign-after-sign.txt` | `SIGNATURE-NOBS-00` | idem |
| `KeyPairSpec.txt` | `KEYPAIR-NOBS-01` | idem — `new KeyPair(null, null)` |
| `KeyPairSpec-public-cipher.txt` | `KEYPAIR-NOBS-01` | **limite de alcance**: as metades vêm de linhas `bind`, que o harness executa sem despachar |
| `KeyPairSpec-private-cipher.txt` | `KEYPAIR-NOBS-01` | idem |

**As seis últimas são o limite de alcance dizendo o próprio nome**, e é para isso que o código
`NOBS` existe separado do `CONSTR` (INV-INS-143). As traces novas são a outra metade da medição
e separam os veredictos: `SignatureSpec-generated-privkey.txt` e `-generated-pubkey.txt`, onde a
chave tem origem observada, e `KeyPairSpec-observed-halves.txt`, onde as duas metades têm, ficam
**silenciosas quanto às cláusulas novas** — só carregam o `KEYPAIR-ORDER-00` que a 4.13 mediu e
a 7.1 possui. E `CipherSpec-keygen-key.txt` e `-keystore-key.txt`, as duas cadeias de #5 que o
corpus nunca observara nas duas pontas, ficam **inteiramente silenciosas**.

As traces das cadeias que se fecham não são editadas para calar as que acusam: uma trace é
artefato de medição, e as três de `Signature` que passam `null` descrevem um programa a que
nenhum gerador deu chave — o relatório é correto sobre o programa que a trace nomeia.

---

## 7. Duas propriedades do instrumento, medidas nesta passagem

**O harness devolve um envelope por despacho, não um por relatório.** `TraceRunner.envelope`
percorre o conjunto de erros e devolve **o primeiro** cuja spec casa, então um evento que emite
dois códigos aparece com um só. Medido em vez de suposto: um despacho de `KeyPairSpec.c1` sobre
`new KeyPair(null, null)` produz **2** relatórios (`KEYPAIR-NOBS-00` e `KEYPAIR-NOBS-01`), e o
harness mostra um. Não afeta a classificação — `accused` é um piso, não uma contagem (achado 14)
—, mas a coluna de envelope sub-reporta evento multi-código. Registrado, não reparado: mudar o
resolvente no meio de uma medição é mudança de instrumento.

**Um `bytes` na trace aloca um array novo a cada ocorrência.** Uma trace que escrevesse `bytes`
nas duas pontas da #8 nomearia dois objetos diferentes, e um store keyado por identidade
responderia `SATISFIED` no Cipher: a trace passaria descrevendo um programa que não existe.
`bind pt = bytes(16)` nomeia um array só, e é o que as duas traces de mac-then-encrypt usam.

**Um evento com `returning(boolean)` exige que a chamada seja executada.** `s.verify(bytes)` sem
`-> x` faz o harness passar `null` para um parâmetro primitivo e a linha cai em `unresolved`.
A trace do `-generated-pubkey` para no `update`, e `g1 i4 update` é um prefixo que o `ere`
aceita, então nenhum relatório de ordenação substitui a cauda que falta.

---

## 8. Contabilidade

| medida | antes | agora |
|---|---|---|
| eventos: `CipherSpec` / `IvChainJunction` / `MacSpec` | 17 / 5 / 8 | **17** / 7 / 12 |
| linhas no `codes.csv` | 88 | **102** (14 novos; nenhum renumerado) |
| sítios no `predicate_graph.csv` | 53 | **65** |
| `read:body` / `read-absent:body` | 23 / 1 | **28 / 5** |
| `write:acceptance` / `write:body` | 23 / 5 | **26 / 5** |
| `negate:body` / `read:condition-guard` | 1 / 0 | **1 / 0** |
| hunks no `divergence_record.csv` | 280 | **284** (45 novos, 41 `stale` com as razões absorvidas) |
| linhas no `gate_allowlist.csv` | 12 | **14** |
| traces do corpus | 114 | **122** |
| achados dos gates (G-PRED2) | 4 | **4** — os mesmos quatro, nenhum deste lote |
| `gh104_gates`: G-2a | 9 hits / 3 falhas | **11 hits / 3 falhas** (as duas novas allow-listadas) |
| `gh104_gates`: G-2b' | 16, todas allow-listadas | **18**, todas allow-listadas |
| baseline (`gate_baseline.json`) | — | **inalterada**; nenhuma linha `repaired` |
| asserções nas quatro suítes | 94 | **94** (6 + 2 + 16 + 70) |
| universo enumerado (`.mop`) | 215 | **215** — nenhum arquivo novo |

O `write:body` fica em 5 e o `read:condition-guard` em 0, e essas duas são a afirmação que este
lote mais precisa fazer: ele acrescenta sete escritas e treze leituras e **não põe nenhuma delas
fora do ponto de aceitação nem dentro de uma guarda**.

---

## 9. O que fica para depois

- **As duas linhas `MacSpec.mop/match/MACED`** do grafo são indistinguíveis em toda coluna que o
  emissor calcula. Carregam texto **idêntico** de propósito, para que uma troca entre elas num
  `--emit` futuro seja um no-op (achado 81).
- **O `MacSpec` não tem linha no `order_alphabet_map.csv`** — é uma das treze pendentes da 7.1 —
  então o G-ORDER pula o arquivo nas duas direções e **não checou** o `ere` novo. Está dito aqui
  em vez de escondido; quando a 7.1 mapear o arquivo, os seis símbolos deste lote precisam de
  linha.
- **A `SIGNATURE-CONSTR-*` não tem programa que a dispare hoje**: nada no api30 retira
  `generatedPrivkey` ou `generatedPubkey`, então `validate` só pode responder `SATISFIED` ou
  `NOT_OBSERVED` para eles. Os ramos ficam escritos pela razão que os irmãos deles registram —
  um predicado ganha um `negate` no dia em que alguma cláusula NEGATES for fiada a ele, e uma
  leitura que tivesse dobrado VIOLATED em NOT_OBSERVED passaria a reportar uma retirada como um
  limite de alcance.
