# Tabela de alias — Conscrypt `android11-release` (API 30)

**Fonte**: `platform/external/conscrypt`, branch `android11-release`,
`common/src/main/java/org/conscrypt/OpenSSLProvider.java` (607 linhas), baixada de
android.googlesource.com. Cópia local: `scratchpad/OpenSSLProvider.java`.
Tabela completa em `scratchpad/alias_table_conscrypt_android11.csv`
(colunas: service, alias, canonical, openssl_provider_line, in_api30_allowlist).

## Números

| | |
|---|---|
| `Alg.Alias.*` no provider | **175** |
| em serviços para os quais temos spec | 158 |
| que casam uma entrada da allow-list api30 | **114** |

Por serviço (aliases relevantes, recontados do CSV): Signature 39, Mac 24, KeyGenerator 23,
MessageDigest 12, AlgorithmParameters 5, KeyPairGenerator 5, Cipher 4, TrustManagerFactory 1,
SecretKeyFactory 1 — soma **114**.

## Correções aos ponteiros do ase-journal (verificadas na fonte)

O `docs/20260806_owasp_cwe_mapping_report.md` erra duas citações; o CSV e o anexo acertam.

| afirmação | citado no report | real |
|---|---|---|
| `SHA1`/`SHA` -> `SHA-1` | §7.1.1 diz `:131-132,140` | **`:115-116`**. `:131-132` é `SHA-512`/`SHA512`; `:140` é `KeyGenerator.ARC4`, que nem alias é |
| `X509` -> `PKIX` | §7.2.2 diz `:101-107` | **`:89-90`** (como o CSV `RV-15` e o anexo já dizem). `:101-102` é `AlgorithmParameters` DESEDE/TDEA |

## Os cinco casos medidos

| valor observado | resolve por | ponteiro |
|---|---|---|
| `X509` (643 ev) | alias -> `PKIX` | `:90` |
| `SHA1`/`SHA` (424+1 ev) | alias -> `SHA-1` | `:115-116` |
| `SHA256WITHRSA` (4 ev) | caixa -> `SHA256withRSA` | não é alias |
| `OAEPWithSHA1AndMGF1Padding` (109 ev) | caixa + hífen -> `OAEPwithSHA-1andMGF1Padding` | não é alias |
| `TLS` (8.648 ev) | entra na lista api30 | não é alias |

## Achado: a `.mop` do `jca` já continha uma tabela de alias escrita à mão

`KeyGeneratorSpec`, `MacSpec` e `SecretKeySpecSpec` carregam entradas como `HMAC-SHA256`,
`HMAC/SHA256`, `HMAC-SHA384`, `PBEWITHHMACSHA-256` **dentro da allow-list**. Elas são alias
Conscrypt reais — `HMAC-SHA256`/`HMAC/SHA256` -> `HmacSHA256` em `:170-171`,
`PBEWITHHMACSHA256` -> `HmacSHA256` em `:481`. Ou seja: o autor da spec resolveu alias
misturando-os à lista de algoritmos permitidos. A tabela de alias substitui isso com uma
origem única, e a lista volta a ser só a do api30.

## Limite declarado: Conscrypt não é o único provider

O AndroidKeyStore vem do `AndroidKeyStoreProvider` e o BKS/BouncyCastle do provider Bouncy
Castle — **nenhum alias de `KeyStore` existe neste arquivo**. A allow-list do `KeyStore`
(`AndroidKeyStore`, `PKCS12`, `BKS`, `BouncyCastle`, `AndroidCAStore`) portanto não tem
cobertura de alias aqui, e isso fica registrado como limite, não como ausência de problema.

Dois fatos vizinhos que **não** são `Alg.Alias` e por isso não entram no CSV:

```
80: put("SSLContext.SSL", classOpenSSLContextImpl + defaultSSLContextSuffix);
81: put("SSLContext.TLS", classOpenSSLContextImpl + defaultSSLContextSuffix);
```
`SSLContext.SSL` e `SSLContext.TLS` apontam para a MESMA classe — equivalência de
comportamento, não alias registrado.

```
327: put("SecureRandom.SHA1PRNG", PREFIX + "OpenSSLRandom");
328: put("SecureRandom.SHA1PRNG ImplementedIn", "Software");
```
`SHA1PRNG` é o único serviço `SecureRandom` do provider — o que confirma a lista api30
`{SHA1PRNG}` e refuta as cinco entradas Oracle da `.mop` do `jca`.

## Formas de alias presentes

1. **Grafia sem hífen**: `SHA1`, `SHA256`, `SHA384`, `SHA512`, `SHA224`
2. **Separador alternativo**: `HMAC-SHA256`, `HMAC/SHA256`, `SHA256/RSA`, `SHA224/ECDSA`
3. **Sufixo `Encryption`**: `SHA256withRSAEncryption` -> `SHA256withRSA`
4. **`andMGF1`**: `SHA256withRSAandMGF1` -> `SHA256withRSA/PSS`
5. **OID puro e `OID.`**: `1.2.840.113549.1.1.11`, `OID.1.2.840.113549.1.1.11`
6. **OID composto**: `1.3.14.3.2.26with1.2.840.113549.1.1.1`
7. **Nome histórico**: `RC4` -> `ARC4`, `ARCFOUR` -> `ARC4`, `TDEA` -> `DESEDE`
8. **`PBEWITHHMACSHA<n>`** -> `HmacSHA<n>` (só em `Mac`)

As formas 5 e 6 são mais de metade das 114 e nenhuma spec de hoje as trata.

## Correção (verificada no CSV)

O número correto é **114**, não 115. A contagem anterior incluía
`Cipher.GCM -> AES/GCM/NoPadding` (`OpenSSLProvider.java:430`) por casamento espúrio: a
string `GCM` aparece na lista do `Cipher` como **modo de operação**, não como algoritmo, e o
alias aponta para uma transformação inteira. O CSV é a fonte: 158 linhas em serviços com
spec, das quais **114 com `in_api30_allowlist=yes`** e 44 com `no`.

## O caso `OAEPWithSHA1AndMGF1Padding` — não é alias, e o Conscrypt não o explica

Valor observado no dataset: `RSA/ECB/OAEPWithSHA1AndMGF1Padding` (218 ocorrências = 109 eventos
contados duas vezes, em `message` e `unique_msg`), **sem hífen** em `SHA1`.

- api30 (`Cipher.cryptsl`) declara `OAEPwithSHA-1andMGF1Padding` — com hífen.
- Conscrypt registra `RSA/ECB/OAEPWithSHA-1AndMGF1Padding` (`:338`) e o alias
  `RSA/None/OAEPWithSHA-1AndMGF1Padding` (`:339-340`) — ambos com hífen.
- **Nenhum registro da grafia sem hífen neste arquivo.**

O advice `CipherSpec.g1` é `after ... returning(Cipher c)`, logo só dispara quando a chamada
retorna: as 109 chamadas funcionaram. Portanto algum provider da plataforma aceita a grafia sem
hífen e **não é o Conscrypt** — o candidato é o Bouncy Castle empacotado pelo Android, fora
deste arquivo.

**Consequência**: este caso NÃO entra na tabela de alias (não há linha de provider para citar) e
NÃO justifica afrouxar a exigência de ponteiro da INV-INS-127. Entra no registro de divergência
com evidência **comportamental** declarada como tal, e identificar o provider que o resolve é
tarefa de execução.

Nota adjacente: `OAEPPadding` está na lista api30 e o Conscrypt o registra em `:336` apontando
para a mesma implementação SHA-1 — um app que use `RSA/ECB/OAEPPadding` passa sem divergência.
