# Tarefa 9.10 — a única spec de valor que não normalizava, nos dois sentidos

**Data**: 2026-08-25 · **Decisão**: GO nas duas metades (pesquisador, 25/08)
**Par**: `A = pós-9.15` · `B = A + 9.10` · `~/tmp-gh104/g9b/pair-910.json`
**Java**: `rvsec-core/.../jca/util/CipherTransformationNormalizer.java` (nova) · reator buildado

## O que estava errado

Das doze especificações que carregam valor, onze comparam por `ConscryptAliasTable.matches`, que
dobra caixa e resolve alias. O `CipherSpec` chamava a **congelada**
`CipherTransformationUtil.isValid`, que compara cru:

| defeito | linha |
|---|---|
| `alg(t).equals("AES")` sensível a caixa | `:44` |
| `modes.contains(mode(t))` sensível a caixa | `:45` |
| só o padding chama `toUpperCase()` | `:46` |
| lista CBC `[PKCS5PADDING, ISO10126PADDING, PKCS5PADDING]` — duplicata, sem PKCS7 | `:35` |
| ramo RSA admite só `""` e `"ECB"` como modo | `:64-65` |

## O normalizador, e o que ele deliberadamente **não** muda

`CipherTransformationNormalizer` resolve o alias Conscrypt pinado, dobra caixa, e **então** compara
— exatamente o mecanismo que a D-15 já ratificou para as outras onze. As cláusulas de valor são as
da congelada, reproduzidas: **a decisão foi alias e caixa, não valores.**

Medido na classe nova, sobre o classpath do reator recém-buildado:

| transformação | `isValid` antigo | `isValid` novo | `mode()` novo | canônico |
|---|---|---|---|---|
| `AES/CBC/PKCS5Padding` | true | true | `CBC` | — |
| `AES/CBC/PKCS7Padding` | **false** | **true** | `CBC` | `AES/CBC/PKCS5Padding` |
| `aes/cbc/pkcs5padding` | **false** | **true** | `CBC` | — |
| `AES/cbc/PKCS5Padding` | **false** | **true** | `CBC` | — |
| `RSA/None/PKCS1Padding` | **false** | **true** | `ECB` | `RSA/ECB/PKCS1Padding` |
| **`AES/ECB/PKCS5Padding`** | false | **false** | `ECB` | — |
| `DES/CBC/PKCS5Padding` | false | false | `CBC` | — |
| `PBEWithHmacSHA1AndAES_128` | false | false | **`CBC`** (era `''`) | `AES_128/CBC/PKCS5PADDING` |

As quatro grafias que a tarefa nomeia viram `true`. **`AES/ECB/PKCS5Padding` continua `false`** — a
D-15 não reabre, e isso é medição e não promessa.

Dois desvios conhecidos contra o expert ficam **de pé**, cada um seria decisão de valor própria, e
estão escritos no javadoc da classe:

1. `Cipher.crysl:89-92` admite oito algoritmos `PBEWithHmacSHA*AndAES_*`; nem a congelada nem a
   nova os implementam, então continuam acusados.
2. Para AES com `CCM/GCM/CTR/CTS/CFB/OFB` o expert admite só `NoPadding`, e esta lista também
   admite o padding vazio. É inerte: uma transformação de duas partes (`"AES/GCM"`) não é um nome
   que o JCA resolva.

## A segunda exposição vai na direção contrária

O `IvChainJunction` **não chama `isValid`** — a tarefa dizia que chamava, e é falso. Ele chama só o
parser `mode()` (`:136`) e já dobrava caixa nos dois testes. O defeito dele é outro: extrai o modo
da transformação **não resolvida**. A última linha da tabela acima é a prova —
`PBEWithHmacSHA1AndAES_128` dava `mode() == ''` e **furava as cláusulas de IV e GCM em silêncio**.
Resolvido o alias antes do parse, dá `CBC`, e as cláusulas passam a valer.

Isso **acrescenta** acusação: é falso negativo fechando, onde a metade do `isValid` é falso positivo
saindo. As duas metades foram aprovadas juntas.

## Como os dois arquivos nomeiam a classe

O import é **liso e qualificado no sítio**, não `import static`. A congelada continua importada
estaticamente; as duas classes declaram métodos de mesmo nome, e um segundo `static-*` tornaria todo
`mode(...)` e `isValid(...)` do monitor fundido **ambíguo** — o monitor não compilaria. É a mesma
disciplina que as tasks 11.3/11.9 registraram para a congelada, aplicada à nova.

E há linhas dos dois tipos no `CipherSpec` de propósito: o `alg(...)` da leitura de
`generatedKey` (`:159`) **continua na congelada**. Dobrar o algoritmo ali mudaria uma comparação de
tupla de predicado contra produtores que escrevem o valor sem dobrar
(`KeyGeneratorSpec:215`, `KeyStoreSpec:193`, `SecretKeySpecSpec:237`) — o que seria mudança de
comportamento que a 9.10 não foi aprovada para fazer.

## O medido

```
pair-910: 172 traces  {"unchanged": 169, "moved": 3}
```

| trace | A | B |
|---|---|---|
| `CipherSpec-lowercase.txt` | `f1:ORDER-00`, **`i2:CIPHER-ALG-01`**, `i2:NOBS-00`, **`i2:ORDER-00`** | `f1:ORDER-00`, `i2:NOBS-00` |
| `CipherSpec-pkcs7-alias.txt` | `f1:ORDER-00`, `i2:CIPHER-ALG-01`, `i2:NOBS-00`, **`i2:ORDER-00`** | `f1:ORDER-00`, `i2:CIPHER-ALG-01`, `i2:NOBS-00` |
| `CipherSpec-rsa-none.txt` | `f1:ORDER-00`, `i2:CIPHER-ALG-01`, `i2:NOBS-00`, **`i2:ORDER-00`** | `f1:ORDER-00`, `i2:CIPHER-ALG-01`, `i2:NOBS-00` |

Os três perdem o `ORDER-00`: a guarda dos eventos `g1`/`g2`/`g3` lê o argumento `transformation`
que o trace nomeia, o normalizador o admite, e o cipher deixa de entrar pelo ramo inseguro.

### O `CIPHER-ALG-01` que sobra em dois dos três é limite do arnês, não do reparo

Só o `lowercase` perde também o `ALG-01`, e a diferença diz exatamente qual é o limite. Esse
código vem de um sítio no **corpo** do `i2`, que lê `c.getAlgorithm()` **do objeto real** e não do
argumento do trace. O TraceRunner tenta a chamada de verdade e, quando a plataforma não tem o
nome, cai para "qualquer instância do tipo":

- `aes/cbc/pkcs5padding` **resolve** no JSE (o JCA é insensível a caixa), então `getAlgorithm()`
  devolve a grafia do trace e a guarda migrada a aceita — o `ALG-01` some.
- `AES/CBC/PKCS7Padding` e `RSA/None/PKCS1Padding` **não resolvem** no JSE — são registrações do
  Conscrypt, que é a plataforma do Android e não a deste JVM. O objeto é o do fallback, e
  `getAlgorithm()` responde outra coisa que nenhum reparo de grafia poderia salvar.

Ou seja: o arnês **subestima** a 9.10 nesses dois traces, e subestima por rodar num JVM que não é
a plataforma. A prova de que a metade do corpo também se move é a tabela da classe acima, medida
diretamente sobre o classpath do reator, onde `isValid` recebe a string e responde `true`. Isso
está declarado aqui em vez de escondido atrás do `moved`.
