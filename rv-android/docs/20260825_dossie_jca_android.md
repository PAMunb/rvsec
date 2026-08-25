# Dossiê `jca_android` — as regras CrySL, o conjunto publicado e o sucessor

**Data**: 2026-08-25 · **Árvore auditada**: rvsec `HEAD = 14dd8093` · **Change**: gh105 (grupos 10 e 11 abertos)
**Oráculo único (D-16)**: as 49 regras expert de `RVSec-replication-package/tools/rules/`, pinadas por sha256 `d7bcc019…`
**Plataforma**: API 30 · Conscrypt `android11-release`

Versão publicada (mesmo conteúdo, formatação de leitura): <https://claude.ai/code/artifact/052cbc53-ed87-4dca-8cbf-1140d662e893>

Este documento compara três coisas — o que as regras CrySL validadas por especialistas exigem, o que
o conjunto `jca` publicado realmente executava, e o que o sucessor `jca_android` passou a medir — e
isola, ao final, tudo o que existe unicamente porque o alvo é Android. Toda contagem citada foi
obtida por enumeração sobre as fontes primárias, não copiada de documento anterior.

**Os números de capa**

| | |
|---|---|
| Regras expert com `.mop` pareado | **21 de 49** — a mesma lacuna do seed |
| Cláusulas de valor checadas literalmente | **30 de 80** — 62,5% das que têm custo de detecção |
| Símbolos do alfabeto cobertos | **132 de 140** — os 8 restantes são inalcançáveis |
| Sítios de relatório vivos | **50 → 115**, do seed ao sucessor |
| Leituras de predicado dentro de `condition()` | **27 → 0** |
| Idiomas de comparação de string | **11 → 1** |

---

## I. Três artefatos e dois eixos de comparação

Quase todo mal-entendido sobre estes números nasce de confundir artefatos de naturezas diferentes.
Vale fixar o vocabulário antes de qualquer contagem.

### A regra CrySL: o que deveria ser verdade

Uma regra `.crysl` é a especificação de uso correto de **uma** classe da JCA, escrita na linguagem do
CogniCrypt e validada por especialistas em criptografia. São 49 delas na cópia pinada. Cada regra
afirma até seis coisas distintas, e a distinção importa porque cada bloco se perde de um jeito
diferente:

| Bloco | O que afirma | Exemplo real |
|---|---|---|
| `EVENTS` | quais chamadas são observáveis e como se agrupam em símbolos | `g1: getInstance(algorithm)` → `Get := g1 \| g2` |
| `ORDER` | a expressão regular sobre os símbolos que define a sequência legal | `Get, Init, DoPhase, GenSecretBuffer` |
| `CONSTRAINTS` | os **valores** admitidos em cada posição | `stdName in {"secp256r1", …}` |
| `REQUIRES` | o que precisa chegar pronto de outro objeto (predicado consumido) | `generatedPrivkey[privKey]` |
| `ENSURES` | o que este objeto entrega aos outros (predicado produzido) | `generatedKey[key, algorithm]` |
| `FORBIDDEN` / `NEGATES` | chamada proibida / predicado revogado | `noCallTo[gs3]`; `speccedKey` após `clearPassword` |

Apenas 4 das 49 regras declaram `FORBIDDEN` (`DigestInputStream`, `DigestOutputStream`,
`PBEKeySpec`, `SSLContext`) e apenas 2 declaram `NEGATES` (`PBEKeySpec`, `SecretKey`). O instrumento
traduz exatamente um `negate` — o do `PBEKeySpec`; o outro é inalcançável no Android, porque
`destroy()` lança.

### A spec `.mop`: o que efetivamente roda

Uma spec `.mop` é um autômato JavaMOP com *pointcuts* AspectJ — **escrita à mão, não gerada da
regra**. É ela que é tecida no APK, observa as chamadas e emite os relatórios. A relação entre uma
regra e uma spec é de tradução manual, e é aí que mora tudo o que este dossiê mede: uma regra pode
estar impecável e a spec que a traduz não executar nada.

### Os quatro conjuntos

| Conjunto | `.mop` | Papel |
|---|---:|---|
| `jca` (congelado) | 23 | O conjunto Java original, congelado byte a byte em `7e7acb69`. É contra ele que os números publicados respondem. |
| `jca_android` (ativo) | 24 | O sucessor. Semeado byte a byte do `jca` e alvejado na API 30. É onde os reparos entram. |
| `jca_android_bug_predicate` (reprovado) | 23 | Derivado por atacado contra as regras `api30`. A auditoria de 08/08 reprovou 22 dos 23 arquivos. Arquivado sem entrada de mapeamento: **nada o seleciona**. |
| `generic` | — | Fora do escopo (uso geral de API). |

### O pareamento não é um-para-um

| | Quantidade | O que é |
|---|---:|---|
| Regras **com** `.mop` homônimo | **21** | o pareamento real |
| Regras **sem** `.mop` | **28** | a lacuna herdada do seed |
| `.mop` **sem** regra | **3** | `SecretKeySpec.mop` (propagador — serve de fato ao `ENSURES preparedKeyMaterial` de `SecretKey.crysl:17`, sem linha própria no registro), `RandomStringPassword.mop` (ponte heurística, hoje sem efeito), `IvChainJunction.mop` (junção da cadeia de IV, criada pela gh105) |

O congelado tem 23 = 21 pareados + 2 sem regra; o sucessor tem 24 porque a `IvChainJunction` entrou.

### Os dois eixos, e a história do oráculo

- **Eixo de conformidade** — `jca_android` contra as 49 regras expert. Responde "o instrumento faz o
  que a especialidade diz que deve fazer?".
- **Eixo de sucessão** — `jca_android` contra o `jca` congelado. Responde "o que mudou em relação ao
  instrumento cujos números foram publicados?".

O oráculo do primeiro eixo mudou duas vezes:

| Âncora | Vigência | O que ancorava | Por que caiu |
|---|---|---|---|
| `MetaCrySL/generated/api30/` | até 24/08 | tudo | As regras `api30` são refinadas de arquivos `.ref` derivados de **registros de provider**. Um `in {…}` assim responde "o que a plataforma oferece", nunca "o que é seguro usar". Com a sintaxe intacta e o conjunto trocado, a regra se inverte em silêncio: o `Api30CipherTransformationUtil` admitia **`AES/ECB/PKCS5Padding`**. |
| D-15 — expert *para valores* | 24/08 → 25/08 | só cláusulas de valor | Escopo estreito demais: deixava protocolo e predicados respondendo a uma fonte já sabidamente derivada de registro de provider. |
| **D-16 — oráculo único** | desde 25/08 | **todas** as dimensões | Vigente. A `api30` não tem mais papel de oráculo em dimensão nenhuma; é citada apenas dentro de adendos de supersessão. |

**Por que o oráculo é uma cópia com hash, e não um branch.** Existem três cópias locais das 49
regras. O checkout upstream do CogniCrypt e o `rvsec-cognicrypt/CrySL-Rules` são byte-idênticos; a
cópia do *replication package* — a pinada — difere em exatamente um valor: acrescenta `"CCM"` aos
modos AES. Enquanto isso, o `master` upstream **hoje** andou no sentido oposto e removeu `CBC` e
`PCBC`. Reancorar num branch vivo passaria a acusar `AES/CBC/PKCS5Padding` — a transformação mais
comum do corpus — por decisão de ninguém, numa execução que ninguém pediu.

---

## II. A cobertura: 21 regras de 49

### Quatro perdas, não uma

Dizer que 28 regras "não são checadas" subestima o efeito. Uma regra sem `.mop` custa quatro coisas,
e duas delas **vazam para specs que existem**:

1. **As acusações próprias.** Os `CONSTRAINTS` e o `ORDER` da regra nunca são avaliados.
2. **O `REQUIRES` não é consumido.** Quem produz o predicado rio acima continua produzindo — para
   ninguém. A escrita fica órfã.
3. **O `ENSURES` não é produzido.** Todo `.mop` que consome esse predicado passa a ler
   `NOT_OBSERVED`. Uma checagem existente *degrada*.
4. **A cadeia se rompe.** É o efeito composto — e é o que separa uma lacuna cara de uma irrelevante.

O terceiro item merece cuidado: o conjunto **não acusa o que não observou**. `NOT_OBSERVED` tem
código próprio (`*-NOBS-*`) e é separado de `VIOLATED` em toda leitura fiada. Isso é qualidade, não
defeito — mas significa que uma lacuna de spec produz cegueira *declarada*, não falso positivo.

### A lacuna é idêntica à do seed — e isso é decisão

Conferido por enumeração: o `jca` congelado tem 23 arquivos cobrindo **exatamente as mesmas 21
regras**. O `jca_android` acrescentou apenas o `IvChainJunction.mop`, que não é classe nova.
Nenhuma das 28 lacunas foi aberta ou fechada. Duas razões sustentam a decisão:

- **Comparabilidade.** Se o sucessor tivesse ganhado um `SecretKeyFactorySpec.mop`, qualquer
  comparação antes/depois misturaria "o instrumento melhorou" com "o instrumento passou a olhar para
  o que nem olhava". A diferença de contagem viraria ininterpretável.
- **Taxa de falso positivo não medida.** Uma classe de acusação nova carrega uma taxa de FP que
  nunca foi medida naquele corpus. A regra tem nome — *no new accusation classes* — e o caso medido
  é o `keysize` AES do `KeyGenerator`, deliberadamente deferido.

### As 28 sem spec, por relevância

| Relevância | Regra | O que deixaria de escapar |
|---|---|---|
| **ALTA** | `SecretKeyFactory` | a rota canônica de PBE — `PBKDF2WithHmacSHA1`, `PBEWithMD5AndDES`, `PBEWithSHA1AndDESede` |
| **ALTA** | `KeyAgreement` | `{DH, DiffieHellman, ECDH}` + `noCallTo[generateSecret(String)]` — chave simétrica direto do segredo DH, sem KDF |
| **ALTA** | `ECGenParameterSpec` | curvas fracas — `secp192r1`, `prime192v1`, `secp160*` |
| MÉDIA | `RSAKeyGenParameterSpec` | a rota `initialize(RSAKeyGenParameterSpec)` que escapa da checagem de keysize (o expert admite 1024 aqui) |
| MÉDIA | `OAEPParameterSpec`, `MGF1ParameterSpec` | OAEP/MGF1 configurados com SHA-1 ou MD5 |
| MÉDIA | `SSLEngine`, `SSLParameters` | `setEnabledProtocols({"TLSv1"})` e cipher suites fracas |
| MÉDIA-BAIXA | `AlgorithmParameters` | 8 aliases Conscrypt registrados sem spec |
| BAIXA | `KeyFactory`, `AlgorithmParameterGenerator`, `DHParameterSpec`, `DSAParameterSpec`, `DSAGenParameterSpec`, `DigestInputStream`, `DigestOutputStream`, `CertificateFactory`, `PasswordAuthentication` | pouca capacidade de acusação por valor, classes raras em app, ou cláusulas de origem estática |
| BAIXA (sem `CONSTRAINTS`) | `Key`, `SecretKey`, `ECParameterSpec`, `CertPathTrustManagerParameters`, `KeyStoreBuilderParameters`, `PKIXBuilderParameters`, `PKIXParameters`, `TrustAnchor`, `X509EncodedKeySpec` | nenhuma cláusula de valor a perder — só predicados |
| NULA | `Cookie` | `javax.servlet.http.Cookie` não existe no Android |

> **Correção (i) ao relatório de 25/08.** O texto corrido daquele relatório diz "das 28, 11 nem têm
> bloco `CONSTRAINTS`", contradizendo a própria tabela. A enumeração das 49 dá **11 sem
> `CONSTRAINTS` no total**, mas duas delas — `HMACParameterSpec` e `KeyPair` — **são pareadas**.
> Entre as 28 sem spec, são **9**.

---

## III. As três lacunas caras, com o texto da regra na mão

### SecretKeyFactory — a rota canônica de senha para chave

```
CONSTRAINTS
  algorithm in {"PBKDF2WithHmacSHA512", …, "PBEWithHmacSHA512AndAES_256"};  // 13 entradas, :22-25
REQUIRES  speccedKey[keySpec, _];                                           // :28
ENSURES   generatedKey[key, algorithm];                                     // :31
```

É *o* caminho pelo qual um app Android transforma senha em chave. A lista é branca, e
**`PBKDF2WithHmacSHA1` não está nela** — nem `PBEWithMD5AndDES`, nem `PBEWithSHA1AndDESede`. São os
três misuses de PBE mais comuns em app real, e nenhum é acusado hoje.

A perda composta é dupla:

- **Rio abaixo**: `ENSURES generatedKey[key, algorithm]` é o mesmo predicado que `CipherSpec` e
  `MacSpec` consomem. Uma chave derivada por PBKDF2 e passada ao `Cipher.init` chega sem produtor: a
  leitura composta do `CipherSpec.i2` responde `NOT_OBSERVED`. A rota PBE **cega o Cipher**, não só
  o SecretKeyFactory.
- **Rio acima**: os produtores de `speccedKey` são `PBEKeySpec:32`, `SecretKeySpec:26` e
  `X509EncodedKeySpec:17`; os consumidores, `KeyFactory:27` e `SecretKeyFactory:28` — **nenhum dos
  dois pareado**. O `PBEKeySpecSpec.mop` existe, checa `iterationCount >= 10000` e acusa
  corretamente, mas o predicado que ele entrega não tem leitor monitorado. O elo "este keyspec foi
  de fato usado para derivar uma chave" está morto nas duas pontas.

### KeyAgreement — o misuse de ponta-a-ponta

```
CONSTRAINTS
  algorithm in {"DH", "DiffieHellman", "ECDH"};   // :40
  noCallTo[gs3];                                  // :41   gs3 = generateSecret(String)
REQUIRES
  randomized[random]; generatedPrivkey[privKey]; generatedPubkey[pubKey];
  algorithm in {"DiffieHellman","DH"} => preparedDH[params];
  algorithm in {"ECDH"}               => preparedEC[params];
```

O `noCallTo[gs3]` é a cláusula interessante e é fácil deixar passar. `generateSecret(String alg)`
devolve uma `SecretKey` derivada **direto** do segredo Diffie-Hellman bruto, sem KDF. O segredo DH
não é uniformemente distribuído; usá-lo como chave AES é o erro clássico do protocolo E2E caseiro. A
regra proíbe a chamada por completo — e uma proibição pontual é a espécie mais barata de
instrumentar: basta o evento existir.

O `REQUIRES` liga a `KeyAgreement` a quatro predicados que o conjunto **já produz**. O grafo tem as
pontas; falta o consumidor.

### ECGenParameterSpec — as curvas fracas, e a cadeia que não fecha

```
CONSTRAINTS
  stdName in {brainpoolP224r1 … P512r1, secp224r1, secp256r1,
              secp384r1, secp521r1, + OIDs e aliases NIST};   // :14-22
ENSURES
  preparedEC[this];                                            // :25
```

Lista branca de curvas de 224 bits para cima. Tudo fora dela viola — `secp192r1`, `prime192v1`,
`secp160k1` — e é assim que app escolhe curva na prática.

O efeito de segunda ordem é o mais caro. Quem toca `preparedEC` nas 49 regras:

```
PRODUTORES (ENSURES)                 PREDICADO          CONSUMIDORES (REQUIRES)
ECGenParameterSpec:25  ──╮                          ╭──  KeyPairGenerator:38   (.mop existe)
   sem .mop             ├──►  preparedEC  ──────────┤
ECParameterSpec:17     ──╯     unclosable           ╰──  KeyAgreement:48       (sem .mop)
   sem .mop
```

O `KeyPairGeneratorSpec.mop` **existe** e lê `algorithm in {"EC"} => preparedEC[params]`. Nenhum
produtor pareado pode satisfazê-la — por construção. É por isso que `preparedEC` aparece no ledger
como a **única cláusula `unclosable`** do conjunto: não é anomalia isolada, é a sombra desta lacuna.

O efeito concreto:

```java
KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
kpg.initialize(new ECGenParameterSpec("secp192r1"));   // curva fraca
```

**Silêncio duplo.** A curva não é acusada (sem spec) *e* o predicado que denunciaria "os parâmetros
EC não vieram de fonte validada" é estruturalmente insatisfazível. Fechar essa lacuna fecha as duas
coisas de uma vez — é o melhor custo/benefício das 28.

> **Correção (iii).** O relatório de 25/08 descreve `preparedEC` como "nenhuma regra o garante". O
> correto é *nenhuma regra **pareada** o garante*: duas regras o garantem, e ambas estão entre as 28.

---

## IV. Valores: as 80 cláusulas, e o que fica mudo de propósito

O denominador honesto não são as 49 regras — são as **80 cláusulas de `CONSTRAINTS` das 21 regras
pareadas**. Cobrar do instrumento cláusulas de classes que ele deliberadamente não monitora seria
contar duas vezes a mesma lacuna.

| Verdito | Nº | O que significa |
|---|---:|---|
| `IGUAL` | 22 | transcritas literalmente e ativas |
| `NAO-DERIVADO` | 14 | vivem em código Java, fora do derivador — **6** implementadas |
| `MOP-MAIS-PERMISSIVO` | 2 | variantes de grafia do próprio congelado |
| `CRYSL-NAO-IMPLEMENTADO` | 42 | silêncio declarado, com registro |

Somando o que é **de fato comparado contra a cláusula expert**: 22 + 2 + 6 = **30 das 80**.

### As 42 deferidas cabem em quatro famílias — e nenhuma é "não deu tempo"

| Nº | Família | Por que fica mudo | O que se perde |
|---:|---|---|---|
| 9 | **Proteção de senha** (`neverTypeOf`×5, `notHardCoded`×4) | Estruturalmente incompatíveis com RV dinâmico. `neverTypeOf` pergunta pelo **tipo estático** da variável de origem — no *call site* já é `char[]`, a informação foi apagada. `notHardCoded` é propriedade da **origem no código-fonte**: domínio de taint/análise estática. | senha hardcoded; senha vivendo em `String` |
| 31 | **Janelas de buffer** (`length`/`offset`/`len`) | Custo de detecção ≈ zero: nos construtores a plataforma lança `IllegalArgumentException` **antes do advice tecer** (medido em 3 casos), e nos `update` a própria JCA valida índices. | erro de índice — não misuse criptográfico |
| 1 | `encmode in {1,2,3,4}` | O `Cipher.init` rejeita opmode inválido sozinho. | nada observável |
| 1 | `AES => keysize in {128,192,256}` | Seria classe de acusação **nova**: FP não medido no corpus. Caso nomeado da regra *no new accusation classes*. | chave AES de tamanho não padrão |

9 + 31 + 1 + 1 = 42. A aritmética fecha por enumeração, nunca por asserção.

### "NÃO-DERIVADO" não quer dizer "não checado"

O rótulo marca uma cláusula que **saiu da lista declarativa e virou fluxo de controle Java** (o
`CipherTransformationUtil`), portanto fora do alcance do derivador mecânico do portão G-CONF. São as
14 cláusulas de acoplamento do `Cipher`. Conferido linha a linha em `Cipher.crysl:88-118` contra
`CipherTransformationUtil.java:32-68`:

| Linha | Cláusula | Estado |
|---|---|---|
| `:97` | AES ⇒ modos `{CBC, CCM, GCM, PCBC, CTR, CTS, CFB, OFB}` | implementada |
| `:101` | RSA ⇒ modos `{"", ECB}` | implementada |
| `:106` | RSA sem modo ⇒ *padding* vazio | implementada |
| `:107` | RSA/ECB ⇒ paddings, incluindo os OAEP | implementada |
| `:112` | AES/CBC-PCBC ⇒ `{PKCS5Padding, ISO10126Padding}` | implementada |
| `:113` | AES stream + GCM + CCM ⇒ `{NoPadding}` | implementada |
| `:90 :94 :98 :103` | as quatro implicações que admitem a família `PBEWithHmacSHA*AndAES_*` | **mais estrita** — a utilitária colapsa tudo em `alg ∈ {AES, RSA}`, então a família PBE fica acusada (documentado no `Normalizer`) |
| `:88` | `instanceOf[key, PublicKey…] \|\| encmode in {3,4} ⇒ alg in {RSA}` | não checada — exige o tipo da chave no ponto do valor |
| `:115 :116 :118` | `noCallTo[IWOIV]`, `callTo[IV]`, `noCallTo[AADUpdate]` | não checada — acoplamento valor↔evento |

**6 implementadas, 4 mais estritas, 4 não checadas.**

> **Correção (ii) ao relatório de 25/08.** Aquele relatório dá as 14 como "7 implementadas / 7 não"
> e, no sumário, conta as 14 inteiras dentro de "38 cláusulas ativas". A conferência linha a linha dá
> **6 implementadas**, e o total de cláusulas efetivamente comparadas contra o texto expert é
> **30 de 80**, não 38. É o denominador que deve ir para o artigo.

---

## V. Predicados: o mecanismo que o seed errava

Esta é a dimensão onde a diferença entre `jca` e `jca_android` deixa de ser quantitativa. Não é que o
seed lesse poucos predicados: é que **ler no lugar errado transforma um defeito de predicado num
defeito de ordem**.

### O mecanismo, provado no monitor gerado

No JavaMOP, o bloco `condition()` decide se a transição acontece. Um `condition()` falso **suprime a
transição** — o monitor não avança de estado. Está provado no monitor gerado: um `return false` antes
do `handleEvent`.

A consequência é a inversão do diagnóstico. Uma leitura de predicado dentro de `condition()` não
reporta "predicado violado": ela **fabrica um `InvalidSequenceOfMethodCalls`**. O defeito de
predicado sai disfarçado de defeito de ordem. Foi exatamente o que mascarou o `MAC-ALG-00` sob o
`MAC-ORDER-00` no seed.

| Substrato | `jca` (seed) | `jca_android` | O que a diferença significa |
|---|---:|---:|---|
| menções a `ExecutionContext` | 134 | 0 | substrato trocado pelo `PredicateStore` (91 menções), com chave por identidade em vez de igualdade |
| leituras `…validate(` | 27 | 33 | no seed, todas em `condition()`; hoje, todas em corpo de evento |
| leituras dentro de `condition()` | 27 | **0** | as 3 ocorrências restantes de `condition(…validate(` no sucessor são o helper local `validate(int keySize)` do `KeyPairGeneratorSpec` — checagem de valor, não leitura de predicado |
| escritas `setProperty(` | 49 | 0 | substituídas por 31 `ensure(` — todas no **ponto de aceitação**; no seed, 42 das 49 marcavam predicado até em sequência rejeitada |
| `.remove(` | 9 | 0 | 8 das 9 estavam em `@fail` — semântica que nenhuma geração CrySL possui |
| `negate(` | — | 1 | o único `NEGATES` alcançável das 49 regras |
| bookkeeping de estado de aceitação | 25 | 0 | a aceitação passou a ser a posição da escrita |

Contagens obtidas por `grep` direto sobre os dois diretórios de specs.

### O ledger: 21 fiadas, 14 registradas, 1 insaciável

Das 36 cláusulas de predicado do ledger derivado, **21 estão fiadas** — cada uma com leitura em
corpo de evento, três valores (`SATISFIED` / `VIOLATED` / `NOT_OBSERVED`, com códigos `CONSTR` e
`NOBS` distintos), produtor no ponto de aceitação e acusador registrado em `codes.csv`. As demais:

- **14 registradas com medição** — 10 `unmonitored-*` (uma das pontas sem `.mop`), 2
  `unreachable-composition` (a JCA recusa `DHGenParameterSpec` em `initialize`; a classe produtora de
  `preparedHMAC` não existe na API 30), 2 `vacuous`.
- **1 `unclosable`** — `preparedEC`, pelo mecanismo da §III.

O registro de sítios (`predicate_graph.csv`, 70 linhas) confirma a disciplina: 44 sítios em corpo de
evento contra 26 em `@match`; 33 leituras `read:body`, 5 `read-absent:body`, 26 escritas
`write:acceptance`, 5 `write:body`, 1 `negate:body`. Nenhuma leitura em `condition()`.

**Por que isso é mais forte que a igualdade byte a byte.** Até a gh105, o teste de que o sucessor
"preservava" o seed era comparar os arquivos. A igualdade byte a byte só sabe dizer que as linhas não
se moveram — não que *cada leitura tem produtor e cada escrita tem leitor*.

---

## VI. ORDER e alfabeto: 94,3% de superfície, 100% do observável

O denominador são os símbolos declarados nos `EVENTS` das 21 regras pareadas: **140**. O numerador,
os que têm evento correspondente no `.mop`: **132**. Mas 94,3% é o número de superfície:

| Símbolo descoberto | Por que não custa detecção |
|---|---|
| `Cipher.iv` | a **própria regra** não o coloca no `ORDER`; a cláusula `callTo(iv)` está entre as deferidas |
| `KeyStore` ×3 (`scE`, `skE1`, `skE2`) | idem — fora do `ORDER` da própria regra |
| `SecureRandom.ne` | `next(int)` é `protected` — programa monitorado não chama |
| `SecretKey.d` | `destroy()` lança nas duas implementações do android-30 *(só Android)* |
| construtores 1-arg dos CipherStreams ×2 | `protected` no android-30 *(só Android)* |

Nenhum dos 8 é alcançável por app nem ordenado pela regra. A cobertura do **observável** é 100%.

Há ainda **8 divergências de ordenação mantidas de propósito**, cada uma na *allowlist* com razão e
testemunha: `CipherInputStream` (`c1` protected — excesso do lado da regra), `CipherOutputStream`
(caminho *flush-only*), `Cipher` (`g1 i1 u1`: update sem final, nada no corpus), `KeyGenerator`,
`KeyStore`, `SSLContext`, `SecretKeySpec` e `SecureRandom`. **Eram nove**: a do `KeyPair` foi
reparada e a testemunha do `KeyStore`, substituída.

**O caso `KeyPair`, que o D-16 reabre.** A regra expert ordena `Con, (GetPubl | GetPriv)*` —
construtor **obrigatório**. O autômato atual é `(c1 | epsilon)`, reparado sob medição: com o
construtor obrigatório, *todo* par saído de `generateKeyPair()` era acusado — 668 linhas, 8 apps —
porque a plataforma constrói o par internamente e o app nunca chama `c1`. Sob o D-16 essa escolha
deixa de ser "obediência à âncora `api30`" e passa a ser **registro de divergência contra a regra
expert**, a ser adjudicado explicitamente.

---

## VII. `jca` → `jca_android`: o que aconteceu com cada arquivo

O sucessor foi semeado **byte a byte** do congelado. Tudo o que os difere é reparo, fiação ou camada
Android — nada é reescrita de conveniência.

| | `jca` | `jca_android` |
|---|---:|---:|
| Arquivos | 23 | 24 (só acréscimo: `IvChainJunction.mop`) |
| Linhas | 1.912 | 4.839 (+153%) |
| Sítios de relatório vivos | 50 | 115 (e `codes.csv` tem 115 linhas: bijeção) |
| Idiomas de comparação | 11 | 1 (`ConscryptAliasTable`, citada 51 vezes) |

### Arquivo por arquivo

| Spec | `jca` | `jca_android` | Δ | O que carregou o crescimento |
|---|---:|---:|---:|---|
| `CipherSpec` | 218 | 447 | +229 | leitura composta de `generatedKey` das 3 origens; `randomized`; `!macced`; normalizador; envelopes |
| `MacSpec` | 94 | 388 | +294 | `!encrypted`, fusão de gêmeos, ressurreição dos acusadores de algoritmo |
| `SecureRandomSpec` | 174 | 338 | +164 | o *hub* de `randomized`; autocadeia de `seed`; `next2` devolvido ao estado `end` |
| `SSLContextSpec` | 93 | 294 | +201 | `generatedKeyManager`/`TrustManager`; `getDefault()` como FORBIDDEN de fato; `engine` com retorno correto |
| `SignatureSpec` | 138 | 294 | +156 | assinaturas de `sign()` corrigidas — o ramo de assinatura **nunca teceu** no seed; 11 sítios novos |
| `SecretKeySpecSpec` | 70 | 240 | +170 | lista de algoritmos **restaurada** (a âncora `api30` a havia deletado); `preparedKeyMaterial` |
| `TrustManagerFactorySpec` | 97 | 231 | +134 | 3 defeitos no `gtm1` e a propriedade errada (`GENERATED_KEY_MANAGERS`) corrigidos |
| `KeyGeneratorSpec` | 82 | 219 | +137 | 3 `init` novos lendo `randomized`; 8 sítios novos |
| `KeyPairGeneratorSpec` | 118 | 214 | +96 | `keysize` por switch; `EC`, `DiffieHellman` e `3072` restaurados pelo D-15 |
| `PBEKeySpecSpec` | 86 | 204 | +118 | os dois FORBIDDEN deixam de ser acusados como ORDER; o único `negate` |
| `KeyManagerFactorySpec` | 98 | 206 | +108 | `generatedKeyStore` lido no `init`, com produtor em `@match` |
| `KeyStoreSpec` | 87 | 199 | +112 | parametrização por instância; 4 *platform-values* citados |
| `MessageDigestSpec` | 119 | 171 | +52 | o `g4` comentado desde sempre foi **revivido** com medição de harness |
| `KeyPairSpec` | 52 | 170 | +118 | corrige o defeito de semântica: `:38` escrevia a chave **privada** sob `GENERATED_PUBLIC_KEY` |
| `GCMParameterSpecSpec` | 59 | 167 | +108 | ressuscitada por inteiro |
| `PBEParameterSpecSpec` | 63 | 155 | +92 | `iterationCount` passa a acusar; `randomized[salt]` |
| `IvChainJunction` | — | 141 | novo | a junção da cadeia de IV: 14 sítios, sozinha |
| `IvParameterSpec` | 69 | 141 | +72 | construtores fundidos; `randomized[iv]` |
| `SecretKeySpec` (propagador) | 34 | 130 | +96 | deixa de conflar `randomized` com material de chave |
| `RandomStringPassword` | 29 | 76 | +47 | ponte heurística; hoje sem efeito, com negativo registrado |
| `CipherOutputStreamSpec` | 28 | 48 | +20 | substrato + envelope |
| `CipherInputStreamSpec` | 28 | 46 | +18 | substrato + envelope |
| `DHGenParameterSpecSpec` | 39 | 39 | 0 | **só** substrato e envelope |
| `HMACParameterSpecSpec` | 37 | 37 | 0 | idem |

### As duas specs que só trocaram de substrato

O diff completo do `DHGenParameterSpecSpec` tem três hunks e ilustra em miniatura o que a migração
fez em toda parte:

```diff
- import br.unb.cic.mop.ExecutionContext;
+ import br.unb.cic.mop.PredicateStore;

- ErrorCollector…addError(new ErrorDescription(…, "DHGenParameterSpecSpec", "" + __LOC));
+ ErrorCollector…addError(new ErrorDescription(…, "DHGenParameterSpecSpec", "" + __LOC,
+     "v=1 code=DHGENPARAMETERSPEC-ORDER-00 ev=" + __EVENTNAME + " obj=… msg='…'"));

- ExecutionContext.instance().setProperty(Property.PREPARED_DH, spec);
- ExecutionContext.instance().setObjectAsInAcceptingState(spec);
+ PredicateStore.instance().ensure(Property.PREPARED_DH, spec);
```

Três coisas de uma vez: o substrato troca, o relatório ganha envelope estruturado com código próprio,
e a marcação paralela de "estado de aceitação" desaparece porque a escrita *passa a ficar* no ponto
de aceitação.

### As cinco specs mortas do seed

Não "imperfeitas": **mortas**. Cada uma emitia zero relatórios possíveis.

| Spec | O defeito | Consequência no publicado |
|---|---|---|
| `Signature.s1/s2` | assinaturas de método erradas | o ramo de assinatura **nunca teceu** |
| `GCMParameterSpec` (inteira) | dois eventos com o mesmo nome + `ere` referindo evento inexistente + tudo em `condition()` | **zero relatórios possíveis** em toda a campanha |
| `TMF.gtm1` | 3 defeitos + propriedade errada | 2 ORDER espúrios e **0 acusação de algoritmo** — o achado real foi suprimido |
| `SSLContext.engine` | retorno declarado `void` | evento inerte |
| `SSLContext.getDefault()` | proibido pelos dois lados e silencioso | FORBIDDEN sem acusador |

### Os 17 acusadores órfãos

Sítios de relatório fora da `ere`, na linha *all-fail*, em 9 specs. Sustentavam **até 39.682 eventos
= 56,1%** de todo o `InvalidSequenceOfMethodCalls` publicado (teto medido, não atribuição causal). O
caso âncora é o `SecureRandom.next2`, ausente do estado `end`: **12.400 eventos espúrios** sozinho. E,
no `TrustManagerFactory`, o efeito foi supressão do achado verdadeiro.

> **O achado que reorganiza a narrativa da tese.** As listas de valores do seed **já estavam certas**:
> o portão de conformidade reproduz a tabela do congelado com `agree 66 / disagree 0`. O que falhava
> era o *resto do instrumento* — posição das leituras, autômatos, idiomas de comparação, acusadores
> órfãos, specs mortas, semântica de predicado. A tese não é "melhoramos as regras". É: **as regras
> estavam certas e o instrumento não as executava**.

---

## VIII. O que existe unicamente porque o alvo é Android

O `jca` congelado não menciona Android nem Conscrypt em nenhum dos seus 23 arquivos — nem uma vez. O
`jca_android` menciona em **20 dos 24**. Tudo nesta seção é camada de plataforma: não corrige defeito
do seed e não responde a nenhuma regra CrySL.

### 1 — A tabela de aliases do Conscrypt (175 linhas)

A JCA do Android é implementada pelo Conscrypt, cujo `OpenSSLProvider` registra centenas de
`Alg.Alias`. Um app que pede `"SHA256/ECDSA"` recebe exatamente o mesmo que quem pede
`"SHA256withECDSA"` — e uma lista branca literal do expert acusaria o primeiro e absolveria o segundo.

| Serviço | Linhas | Serviço | Linhas |
|---|---:|---|---:|
| `Signature` | 61 | `AlgorithmParameters` | 8 |
| `Cipher` | 34 | `KeyPairGenerator` | 5 |
| `Mac` | 24 | `KeyFactory` | 5 |
| `KeyGenerator` | 23 | `TrustManagerFactory` | 1 |
| `MessageDigest` | 12 | `SecretKeyFactory` · `CertificateFactory` | 2 |

Cada linha cita a linha exata do `OpenSSLProvider.java` de onde saiu. A tabela **não é lida em tempo
de execução** — um monitor tecido num APK não tem contrato de sistema de arquivos com este
repositório —, então `ConscryptAliasTable` carrega as linhas como código e um teste assere a
igualdade linha a linha com o CSV.

Efeito colateral valioso: essa mesma chamada substituiu os **11 idiomas de comparação** do seed
(`contains()` sensível a caixa em 8 specs, `toUpperCase()` em 3), sob os quais a mesma string era
misuse numa spec e não em outra. A camada Android pagou uma dívida de coerência que era Java.

### 2 — Os *platform-values* (conjunto fechado, 5 entradas)

Um valor que a regra expert omite e cuja rejeição acusaria uma prática que **a própria plataforma
recomenda**. Cada entrada exige citação de fonte primária; candidato sem citação é descartado e
continua acusado.

| Valor | Spec | Por quê |
|---|---|---|
| `TLS` | `SSLContextSpec` | é o nome que o Android documenta para obter o melhor protocolo disponível. Sozinho, resolve um bloco de **8.648 eventos / 60 apps / 65 misuses** do corpus publicado. |
| `AndroidKeyStore` | `KeyStoreSpec` | o keystore respaldado por hardware — recomendação central da plataforma |
| `AndroidCAStore` | `KeyStoreSpec` | a âncora de confiança do sistema |
| `BKS` | `KeyStoreSpec` | o formato do Bouncy Castle embarcado |
| `BouncyCastle` | `KeyStoreSpec` | idem |

### 3 — `SSL` é deliberadamente acusado

No Conscrypt, `SSLContext.SSL` e `SSLContext.TLS` apontam para a **mesma classe de implementação**
(`OpenSSLProvider.java:80-81`) — comportamentalmente, pedir `"SSL"` não é pior. Mas o registro é
feito por um `put`, não por um `Alg.Alias`: não é equivalência declarada, é coincidência de
implementação. Logo não ganha linha na tabela de aliases, não ganha *platform-value*, e **continua
acusado** — porque pedir `"SSL"` a um provider é precisamente o misuse sobre o qual a regra fala.
São 103 eventos do corpus que voltaram a ser acusados.

Pelo mesmo raciocínio, `X509` *não* precisa de *platform-value*: existe uma `Alg.Alias` genuína
mapeando-o para `PKIX` (`OpenSSLProvider.java:90`), que é entrada expert. Ele silencia pela tabela,
não por exceção.

### 4 — A regra do não-estreitamento

Valores que o expert lista e que o Android **não oferece** — `SunX509`, `NativePRNG*`,
`Windows-PRNG`, `PKCS11`, `JKS`, `JCEKS`, `DKS` — **permanecem nas listas**. São inertes (nenhum app
consegue obtê-los, então nenhum veredito depende deles), e remover entrada de uma lista validada por
especialistas porque a plataforma local não a tem é exatamente o estreitamento não validado que o
D-15 existe para desfazer. Essa decisão **reverteu três estreitamentos** que a âncora `api30` havia
tomado.

### 5 — Os limites de plataforma medidos no android-30

| Limite | Efeito no instrumento |
|---|---|
| `SecretKey.destroy()` lança nas duas implementações | símbolo `d` descoberto; o `NEGATES` de `SecretKey` é inalcançável |
| construtores 1-arg dos CipherStreams são `protected` | 2 símbolos descobertos, mais a divergência de ORDER do `CipherInputStream` |
| `SecureRandom.next(int)` é `protected` | símbolo `ne` descoberto |
| `javax.xml.crypto.dsig.spec` não existe no Android | `preparedHMAC` classificado `unreachable-composition` |
| a JCA recusa `DHGenParameterSpec` em `KeyPairGenerator.initialize` | `preparedDH` classificado `unreachable-composition` |
| cache de `Integer` da JVM | afeta a identidade das posições inteiras no store — motivo de `randomized[randInt]` ser registro e não fiação |
| a plataforma declara **dois** `getInstance` de dois argumentos | *pointcuts* escritos com `Object+` em `Mac`, `Signature`, `KeyPairGenerator` e `SSLContext` |
| `Mac.updateBuffer` — overload exclusivo do Android | evento extra sem símbolo na regra, classificado `order-unmapped` |
| `javax.servlet.http.Cookie` não existe | a regra `Cookie.crysl` tem relevância **nula** no alvo |

### 6 — A âncora `api30`: a alteração Android que precisou ser desfeita

A mais instrutiva de todas, porque foi uma tentativa de "adaptar ao Android" que quase inverteu o
instrumento. O MetaCrySL gera regras por *tier* de API a partir de arquivos `.ref`, e esses `.ref`
foram derivados de **registros de provider**. Uma cláusula `algorithm in {…}` refinada assim responde
à pergunta "o que a plataforma oferece" — e é transcrita para um lugar cuja pergunta é "o que é
seguro usar". A sintaxe fica idêntica e o sentido inverte.

O que a âncora `api30` chegou a admitir: **MD5**, **SHA-1** e **`AES/ECB/PKCS5Padding`**. E a mesma
cadeia tinha deletado por completo a lista de algoritmos do `SecretKeySpec`.

A medição de aceitação da reancoragem é o teste de duas pontas, replicado sobre o corpus publicado
(97.018 linhas de erro, 26.251 com rótulo de valor):

| Spec | Valor acusado | Eventos | Veredito hoje |
|---|---|---:|---|
| `SSLContextSpec` | `TLS` | 8.648 | silencia (platform-value) |
| `MessageDigestSpec` | `MD5` | 3.552 | **acusa** (voltou) |
| `KeyStoreSpec` | `AndroidKeyStore` | 2.005 | silencia (platform-value) |
| `MessageDigestSpec` | `SHA-1` | 1.915 | **acusa** (voltou) |
| `TrustManagerFactorySpec` | `X509` | 643 | silencia (alias genuíno) |
| `MessageDigestSpec` | `SHA1` | 424 | **acusa** (voltou) |
| `CipherSpec` | `RSA/ECB/OAEPWithSHA1AndMGF1Padding` | 109 | acusa |
| `SSLContextSpec` | `SSL` | 103 | **acusa** (decisão explícita) |
| `SignatureSpec` | `SHA256WITHRSA` | 4 | silencia (só dobra de caixa) |
| `SignatureSpec` | `NONEwithRSA` | 4 | **acusa** (voltou) |

Ao todo, **5.892 linhas** de `MessageDigest`, as 103 de `SSL` e as 4 de `NONEwithRSA` voltam a ser
acusadas — todas eram silenciosas sob a âncora `api30`. Do outro lado, os 8.648 `TLS`, 2.005
`AndroidKeyStore`, 643 `X509` e 4 `SHA256WITHRSA` continuam silenciosos, como devem.

### 7 — As verrugas do oráculo, transcritas em vez de corrigidas

- `MessageDigest.crysl` omite **SHA-224**, que o Conscrypt registra. A entrada **não** é adicionada:
  o teste do *platform-value* é se a rejeição acusaria uma prática recomendada, e o Android recomenda
  SHA-256 para cima.
- `Signature.crysl` omite `SHA224withECDSA` (verruga) e `SHA1withECDSA` (omissão deliberada e
  correta — SHA-1 é quebrado).
- A cópia pinada acrescenta `CCM` aos modos AES, coisa que o upstream nunca teve. Mantido.
- `Cipher.crysl` admite `OAEPWithMD5AndMGF1Padding` e **nenhuma** variante OAEP-SHA-1 — errado dos
  dois lados por qualquer leitura moderna. Transcrito literalmente, com a verruga nomeada.

### 8 — O envelope de execução

API 30, Conscrypt `android11-release`, Bouncy Castle embarcado **fora** do oráculo de aliases (limite
declarado da tabela). E um teto que é do gerador, não do Android, mas condiciona toda spec futura: o
`CipherSpec` está em **exatamente 17 eventos**, com zero folga — dezoito levantam `StackOverflowError`
no parser de *enable-set* do processo pai, em qualquer heap. O conjunto inteiro gera em ~78 s, com
pico de 4,5–5,4 GB, produzindo um monitor determinístico de 17.087 linhas.

---

## IX. Por que a tradução é parcial: oito motivos, e só três são reversíveis

"O `.mop` não traduz a regra inteira" é uma frase que junta coisas incompatíveis. Há decisões que uma
reunião pode reverter e há impossibilidades que nenhuma decisão alcança.

### Motivos que são decisão (reversíveis)

| Nº | Motivo | O que explica | Cláusulas |
|---:|---|---|---|
| 1 | **Comparabilidade da medição** | Classe de acusação nova carrega taxa de FP **não medida** no corpus. Introduzi-la junto com os reparos contaminaria a medição dos reparos. É a regra *no new accusation classes*. | as 28 regras sem spec + o `keysize` AES |
| 2 | **Fidelidade acima da opinião** | As verrugas do oráculo são transcritas **como estão**. Corrigir em particular uma regra validada por especialistas é o modo de falha que o D-15 existe para desfazer. | 4 verrugas nomeadas |
| 3 | **Escolha da utilitária do `Cipher`** | As implicações que admitem a família PBE foram colapsadas numa regra incondicional `alg ∈ {AES, RSA}` — mais estrita que o expert. | 4 |

### Motivos que não revertem com decisão

| Nº | Motivo | O mecanismo | Cláusulas |
|---:|---|---|---|
| 4 | **O paradigma não alcança** | `neverTypeOf` pergunta pelo **tipo estático** da variável de origem — no *call site* a informação já foi apagada. `notHardCoded` pergunta pela **origem no código-fonte**. São perguntas de análise estática e taint. | 9 (senha) |
| 5 | **Custo de detecção nulo** | Nos construtores, a plataforma lança antes do advice tecer — medido em 3 casos. Nas janelas de `update`, a JCA valida os índices sozinha. | 32 (31 buffers + `encmode`) |
| 6 | **A plataforma não tem o evento** *(só Android)* | O símbolo existe na regra e não existe no aparelho: construtores `protected`, `destroy()` que lança, `javax.xml.crypto` ausente, `DHGenParameterSpec` recusado pelo `initialize`. | 4 símbolos + 2 predicados + 1 regra |
| 7 | **Teto do gerador** | O `CipherSpec` está em exatamente 17 eventos, com zero folga. Os acoplamentos `callTo[IV]` e `noCallTo[AADUpdate]` precisariam de eventos que não cabem. | 3 |
| 8 | **A outra ponta não existe** | Consequência aritmética do motivo 1: uma cláusula de predicado cuja regra produtora ou consumidora está entre as 28 sem spec não tem como ser fiada. | 10 `unmonitored-*` + 1 `unclosable` |

**A leitura que isso permite.** Das 50 cláusulas de valor que o conjunto não compara, **32 não custam
detecção nenhuma** (motivo 5) e **9 são impossíveis no paradigma** (motivo 4). Sobram **9 cláusulas**
em que a ausência é decisão revogável e tem valor de detecção: o `keysize` AES, o acoplamento `:88` e
os três de IV/AAD do `Cipher`, mais as quatro que a utilitária torna estritas demais. Esse é o passivo
real de tradução — não "42 cláusulas não implementadas".

---

## X. Aderência e o saldo

### Nível de aderência dentro do que foi traduzido

A pergunta certa não é "quantas das 49" — é **quão fiéis são as 21 que traduzimos**.

| Dimensão | Denominador | Aderente | Nível, lido corretamente |
|---|---:|---:|---|
| **Valores** | 80 cláusulas | 30 | 37,5% nominal — **62,5%** entre as 48 que têm custo de detecção real |
| **Predicados** | 36 cláusulas | 21 | 58% nominal — **100% das fiáveis**; as 15 restantes têm impossibilidade medida, uma a uma |
| **Alfabeto** | 140 símbolos | 132 | 94,3% de superfície — **100% do observável** |
| **ORDER** | 21 autômatos | 13 | 8 divergências, todas declaradas com razão e testemunha |
| **Relatórios** | 115 sítios | 115 | bijeção sítio↔código, verificada por portão |

### O mesmo cálculo, contra o Java original

| Eixo | seed `jca` (Java) | `jca_android` hoje |
|---|---|---|
| **Valores** | expert e corretos, mas comparados por 11 idiomas inconsistentes | expert + **uma** normalização auditável (175 aliases da fonte Conscrypt, com teste de igualdade código↔CSV) |
| **Predicados** | **0 de 36** corretamente fiadas — 8 lidas, todas defeituosas por posição; 6 escritas sem leitor; 22 inexistentes | 21 fiadas com três valores e códigos próprios; 14 registradas com medição; 1 `unclosable`; grafo fechado e gateado |
| **Autômatos** | 17 acusadores órfãos; 5 specs mortas ou inertes | órfãos fundidos ou absorvidos; specs ressuscitadas |
| **Relatórios** | 50 sítios, 1 comentado, envelopes autocontraditórios, 72,93% `unknown` | **115 sítios ↔ 115 códigos**, envelope `v=1`, `NOBS` separado de violação |
| **Semântica** | chave privada gravada como pública; `randomized` conflado com material de chave; `remove()` em `@fail` | corrigidos; o único `negate` corresponde ao único `NEGATES` alcançável |
| **Custo novo** | — | 42 deferências declaradas; `NOBS` sem análogo anterior; toda comparação obrigada a nomear seu oráculo; e o passivo de reancoragem do protocolo, ainda aberto |

### Os denominadores que devem constar no artigo

1. **Oráculo**: as 49 regras expert pinadas por sha256, únicas — com as verrugas transcritas e
   declaradas.
2. **Valores**: **30/80** cláusulas comparadas literalmente nas 21 regras pareadas; 42 deferidas em 4
   famílias, mais 8 acoplamentos do `Cipher`. *Não* "as 49 regras".
3. **Regras**: **21/49** com spec; as 3 lacunas caras nomeadas.
4. **Predicados**: 21 fiadas / 14 registradas / 1 `unclosable`, sob a derivação histórica; a
   re-derivação expert está em curso e vai mover esses números.
5. **`NOBS` não é violação.** A junção conta como acusador próprio. Comparações entre `jca`, o
   arquivado, o pré-D-15 e o atual precisam nomear o oráculo de cada contagem.
6. **Envelope**: API 30, Conscrypt `android11-release`, Bouncy Castle fora do oráculo de aliases,
   camada de *platform-value* fechada em 5 entradas, `SSL` deliberadamente acusado.

**Conclusão.** O instrumento melhorou em todos os eixos que importam, e por um motivo que a
comparação com o CrySL torna preciso: as regras já diziam a coisa certa e a tradução para monitor é
que não as executava. A camada exclusivamente Android — aliases, *platform-values*, limites medidos —
não afrouxou o instrumento; ela removeu de vez a única fonte que o afrouxava, a âncora derivada de
registro de provider, e pagou junto uma dívida de coerência que era do lado Java.

---

## XI. O que continua aberto

Nada abaixo foi implementado. Os artefatos da change ordenam; a execução aguarda decisão por tarefa
nos blocos que mexem no que é acusado.

### Grupo 10 — auditoria interna de 25/08

- Quatro linhas do portão G-2a sem cobertura; escopo do G-PRED no CLI.
- *Refresh* de registros: o `README` ainda diz **112** sítios (são 115) e ainda fala em "nove"
  divergências de ORDER (são 8); `predicate_graph`, `divergence_record` e `conformance_record` idem.
- Comentários obsoletos em 7 specs; imports faltantes no `GCMParameterSpecSpec`; re-execução da
  medição diferencial.
- **10.10** *(decisão)* — reparo do *splitter* de `generatedKey` no `CipherSpec`. A classe de falso
  positivo exposta é **grafia de alias/composta** (o store já dobra a caixa, então o cenário
  "aes vs AES" está refutado): `Cipher.getInstance("AES_128/CBC/PKCS5Padding")` com chave de
  `KeyGenerator("AES")` forma a tupla `("aes_128")` contra `("aes")` do produtor → `VIOLATED` → um
  `CIPHER-CONSTR-00` falso que o envelope apresenta como evidência positiva de misuse.

### Grupo 11 — o oráculo único (D-16)

| Tarefa | O que faz | Natureza |
|---|---|---|
| **11.1** | re-derivar o ledger de predicados varrendo `REQUIRES`/`ENSURES`/`NEGATES` das 49 regras expert, com tabela de delta contra o ledger `api30` | registro |
| **11.2** | re-derivar o mapa de alfabeto contra os `EVENTS`/`ORDER` expert das 21 pareadas | registro |
| **11.3** | apontar todos os portões ao oráculo único; nenhum caminho de código `api30` sobrevive | portões |
| **11.4** | registros de oráculo único, com adendo de supersessão em cada linha derivada sob a âncora antiga | registro |
| **11.5** | as fiações que voltam ou abrem — `Mac generatedKey`, `SSLContext randomized[random]`, `TMF params`, `SecureRandom lSeed` | **decisão por cláusula** |
| **11.6** | ORDER re-adjudicado contra o expert; o `KeyPair` é o caso nomeado | **decisão por spec** |
| **11.7** | verificação do grupo — nenhuma tarefa fecha por código de saída de portão | verificação |

**Os cinco deltas já verificados na fonte**

| Delta | Cláusula expert | Consequência |
|---|---|---|
| volta | `Mac.crysl:54` `generatedKey[key,_]` | a leitura deletada porque "a `api30` não declara a cláusula" **retorna** — no corpo do `init`, três valores, códigos próprios |
| abre | `SSLContext.crysl:18,34` — `i1` liga `random` | o `vacuous` registrado era artefato da `api30` e cai junto com o comentário na spec |
| registro | `TrustManagerFactory.crysl:29` | produtores sem `.mop` → disposição esperada `unmonitored-producer`, a ser *derivada* e não assumida |
| registro | `SecureRandom.crysl:46,52` | `long`/`Integer` boxam fresco — limite de plataforma, derivado e não assumido |
| reabre | `KeyPair.crysl:27` | `ENSURES` que a `api30` fazia opcional; pareamento a resolver no ledger novo |

Há ainda um caso de **nomenclatura** a resolver no ledger e não no código: `SSLContext.crysl:32`
nomeia `generatedKeyManagers[km]` no plural, enquanto a leitura fiada consome a propriedade no
singular.

### Quais `.mop` são tocados, afinal

Das dezoito tarefas abertas dos dois grupos, **quatro** mexem em arquivo de especificação de um jeito
que muda o que é acusado — e todas exigem decisão explícita antes de qualquer edição:

| Tarefa | Arquivo | O que muda no que é acusado |
|---|---|---|
| **10.10** | `CipherSpec.mop:166-167` | *remove FP* — o *splitter* da tupla `GENERATED_KEY` passa pelo normalizador. Duas perguntas precisam de resposta do *harness* antes: se `alg("AES_128/CBC/…")` devolve `AES_128`, ainda diverge do produtor `AES`; e se algum programa afetado é acusado **só** pelo CONSTR falso, o reparo cria silêncio novo. |
| **11.5a** | `MacSpec.mop` | *acusa mais* — a leitura de `generatedKey` volta ao corpo do `init`, com códigos CONSTR/NOBS próprios. |
| **11.5b** | `SSLContextSpec.mop` | *acusa mais* — o evento `init` ganha o *binding* de `random` e a leitura correspondente; o comentário `vacuous` sai junto. |
| **11.6** | `KeyPairSpec.mop` | *depende* — se o autômato `(c1 \| epsilon)` for mantido, **nenhuma edição**, só registro de divergência contra a regra expert. Se a decisão for obedecer ao ORDER expert, o construtor volta a ser obrigatório e as 668 linhas de acusação medidas voltam com ele. |

Fora dessas quatro: **11.1, 11.2, 11.3, 11.4 e 11.7 não tocam em `.mop` nenhum** — são derivação,
portões e registros. Do grupo 10, a **10.6** reescreve comentários obsoletos em 7 specs (prosa, zero
comportamento, com prova `unchanged`) e a **10.7** acrescenta dois `import` ao `GCMParameterSpecSpec`.
O resto do grupo 10 é registro.

**Ordem obrigatória:** 11.1 → 11.2 → 11.3 → 11.4 → 11.5/11.6 → 11.7. Os instrumentos precisam apontar
para as regras expert *antes* que qualquer registro alegue conformidade a elas. As tarefas 8.8 e 8.9
dependem deste grupo.

---

## Fontes primárias e correções

**Fontes.** As 49 regras de `RVSec-replication-package/tools/rules/` (sha256 `d7bcc019…`, recomputado
e conferido); os 23 `.mop` de `jca/` e os 24 de `jca_android/`, lidos e contados diretamente; os cinco
registros de `data/jca_android/` (`constraint_table` 80 linhas, `conformance_record` 116,
`divergence_record` 335, `order_alphabet_map` 208, `predicate_graph` 70) e as evidências de aceitação
do D-15. Toda contagem citada foi obtida por enumeração sobre esses arquivos.

**Três correções ao relatório `docs/20260825_aderencia_crysl_mop_jca_android.md`:**

1. **9 das 28** regras sem spec não têm `CONSTRAINTS` — não 11; as outras duas (`HMACParameterSpec`,
   `KeyPair`) são pareadas.
2. As 14 cláusulas `NAO-DERIVADO` do `Cipher` estão **6 implementadas**, não 7 — o que põe o total de
   cláusulas de valor efetivamente comparadas em **30 de 80**, e não 38.
3. `preparedEC` é insaciável porque nenhuma regra **pareada** o garante — duas regras o garantem
   (`ECGenParameterSpec:25`, `ECParameterSpec:17`), e ambas estão entre as 28 sem spec.
