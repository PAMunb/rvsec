# Fase 0 — Inventário e Pareamento spec `.mop` ↔ regra `.cryptsl` (api30)

**Data:** 2026-08-08 · rvsec HEAD `1dd1f4c5` (branch `modules`) · MetaCrySL HEAD `fb1ecaba` (branch `master`)

Fontes:
- Specs: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/` (23 `.mop`, todas `package mop;`)
- Regras: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/` (33 `.cryptsl`)

Método de pareamento: a classe-alvo de cada spec foi extraída dos pointcuts/eventos (chamadas `call(... Classe.metodo(...))` e tipo do parâmetro da spec), e casada com a linha `SPEC <FQCN>` de cada `.cryptsl`. O pareamento é por **conteúdo** (classe-alvo = FQCN do SPEC); a coluna "Base" indica quando o nome do arquivo, sozinho, teria induzido a erro. "Nº eventos" = contagem de declarações `event`/`creation event` no `.mop`.

## Tabela de pareamento (23 specs)

| Spec `.mop` (nome da spec declarada) | Classe-alvo (dos eventos) | Nº eventos | Regra `.cryptsl` pareada (SPEC) | Base do pareamento | Ambiguidade / observação |
|---|---|---|---|---|---|
| CipherInputStreamSpec.mop (`CipherInputStreamSpec`) | `javax.crypto.CipherInputStream` | 4 | CipherInputStream.cryptsl (`javax.crypto.CipherInputStream`) | nome + conteúdo | — |
| CipherOutputStreamSpec.mop (`CipherOutputStreamSpec`) | `javax.crypto.CipherOutputStream` | 5 | CipherOutputStream.cryptsl (`javax.crypto.CipherOutputStream`) | nome + conteúdo | — |
| CipherSpec.mop (`CipherSpec`) | `javax.crypto.Cipher` | 14 | Cipher.cryptsl (`javax.crypto.Cipher`) | nome + conteúdo | maior spec do conjunto (16,8 KB) |
| DHGenParameterSpecSpec.mop (`DHGenParameterSpecSpec`) | `javax.crypto.spec.DHGenParameterSpec` | 1 | DHGenParameterSpec.cryptsl (`javax.crypto.spec.DHGenParameterSpec`) | nome + conteúdo | byte-idêntica à versão `jca` |
| GCMParameterSpecSpec.mop (`GCMParameterSpecSpec`) | `javax.crypto.spec.GCMParameterSpec` | 2 | GCMParameterSpec.cryptsl (`javax.crypto.spec.GCMParameterSpec`) | nome + conteúdo | byte-idêntica à versão `jca` |
| HMACParameterSpecSpec.mop (`HMACParameterSpecSpec`) | `javax.xml.crypto.dsig.spec.HMACParameterSpec` | 1 | HMACParameterSpec.cryptsl (`javax.xml.crypto.dsig.spec.HMACParameterSpec`) | conteúdo (FQCN confere) | byte-idêntica à versão `jca`; única classe fora de `java.security`/`javax.crypto`/`javax.net.ssl` |
| IvParameterSpec.mop (`IvParameterSpecSpec`) | `javax.crypto.spec.IvParameterSpec` | 4 | IvParameterSpec.cryptsl (`javax.crypto.spec.IvParameterSpec`) | conteúdo | nome do arquivo sem sufixo `Spec` do padrão; nome da spec declarada difere do arquivo |
| KeyGeneratorSpec.mop (`KeyGeneratorSpec`) | `javax.crypto.KeyGenerator` | 9 | KeyGenerator.cryptsl (`javax.crypto.KeyGenerator`) | nome + conteúdo | — |
| KeyManagerFactorySpec.mop (`KeyManagerFactorySpec`) | `javax.net.ssl.KeyManagerFactory` | 6 | KeyManagerFactory.cryptsl (`javax.net.ssl.KeyManagerFactory`) | nome + conteúdo | — |
| KeyPairGeneratorSpec.mop (`KeyPairGeneratorSpec`) | `java.security.KeyPairGenerator` | 9 | KeyPairGenerator.cryptsl (`java.security.KeyPairGenerator`) | nome + conteúdo | — |
| KeyPairSpec.mop (`KeyPairSpec`) | `java.security.KeyPair` | 3 | KeyPair.cryptsl (`java.security.KeyPair`) | conteúdo | candidata trivial; confirmado que o alvo é KeyPair (getPrivate/getPublic), não KeyPairGenerator |
| KeyStoreSpec.mop (`KeyStoreSpec`) | `java.security.KeyStore` | 7 | KeyStore.cryptsl (`java.security.KeyStore`) | nome + conteúdo | — |
| MacSpec.mop (`MacSpec`) | `javax.crypto.Mac` | 11 | Mac.cryptsl (`javax.crypto.Mac`) | nome + conteúdo | — |
| MessageDigestSpec.mop (`MessageDigestSpec`) | `java.security.MessageDigest` | 8 | MessageDigest.cryptsl (`java.security.MessageDigest`) | nome + conteúdo | — |
| PBEKeySpecSpec.mop (`PBEKeySpecSpec`) | `javax.crypto.spec.PBEKeySpec` | 7 | PBEKeySpec.cryptsl (`javax.crypto.spec.PBEKeySpec`) | nome + conteúdo | — |
| PBEParameterSpecSpec.mop (`PBEParameterSpecSpec`) | `javax.crypto.spec.PBEParameterSpec` | 3 | PBEParameterSpec.cryptsl (`javax.crypto.spec.PBEParameterSpec`) | nome + conteúdo | — |
| RandomStringPassword.mop (`RandomStringPasswordSpec`) | `java.lang.String` (`String.valueOf`, `String.toCharArray`) | 2 | **NENHUMA** | conteúdo | **sem regra CrySL** — spec auxiliar de propagação da propriedade `RANDOMIZED` (taint de senhas via String); confirmado que nenhuma das 33 regras tem SPEC java.lang.String |
| SSLContextSpec.mop (`SSLContextSpec`) | `javax.net.ssl.SSLContext` | 5 | SSLContext.cryptsl (`javax.net.ssl.SSLContext`) | nome + conteúdo | — |
| SecretKeySpec.mop (`SecretKeySpec`) | `javax.crypto.SecretKey` (getEncoded, destroy) | 2 | **SecretKey.cryptsl** (`javax.crypto.SecretKey`) | **conteúdo** (nome engana) | **ambiguidade resolvida**: apesar do nome do arquivo/spec, os dois eventos apontam para `javax.crypto.SecretKey`, não para `javax.crypto.spec.SecretKeySpec`; o próprio Javadoc da spec cita SecretKey.crysl |
| SecretKeySpecSpec.mop (`SecretKeySpecSpec`) | `javax.crypto.spec.SecretKeySpec` | 4 | SecretKeySpec.cryptsl (`javax.crypto.spec.SecretKeySpec`) | nome + conteúdo | par da ambiguidade acima; eventos são construtores de `SecretKeySpec` |
| SecureRandomSpec.mop (`SecureRandomSpec`) | `java.security.SecureRandom` | 15 | SecureRandom.cryptsl (`java.security.SecureRandom`) | nome + conteúdo | maior alfabeto de eventos do conjunto |
| SignatureSpec.mop (`SignatureSpec`) | `java.security.Signature` | 12 | Signature.cryptsl (`java.security.Signature`) | nome + conteúdo | — |
| TrustManagerFactorySpec.mop (`TrustManagerFactorySpec`) | `javax.net.ssl.TrustManagerFactory` | 6 | TrustManagerFactory.cryptsl (`javax.net.ssl.TrustManagerFactory`) | nome + conteúdo | — |

**Resumo:** 22 specs pareadas com 22 regras distintas de api30; 1 spec (`RandomStringPassword.mop`) sem regra CrySL correspondente. Nenhuma regra foi pareada com duas specs; nenhuma spec pareou com duas regras.

## Regras `.cryptsl` de api30 SEM spec `.mop` correspondente (11)

Confirmado por diferença de conjuntos (33 regras − 22 pareadas):

1. AlgorithmParameters.cryptsl (`java.security.AlgorithmParameters`)
2. CertPathTrustManagerParameters.cryptsl (`javax.net.ssl.CertPathTrustManagerParameters`)
3. DSAGenParameterSpec.cryptsl (`java.security.spec.DSAGenParameterSpec`)
4. DigestInputStream.cryptsl (`java.security.DigestInputStream`)
5. DigestOutputStream.cryptsl (`java.security.DigestOutputStream`)
6. Key.cryptsl (`java.security.Key`)
7. KeyStoreBuilderParameters.cryptsl (`javax.net.ssl.KeyStoreBuilderParameters`)
8. PKIXBuilderParameters.cryptsl (`java.security.cert.PKIXBuilderParameters`)
9. PKIXParameters.cryptsl (`java.security.cert.PKIXParameters`)
10. RSAKeyGenParameterSpec.cryptsl (`java.security.spec.RSAKeyGenParameterSpec`)
11. SecretKeyFactory.cryptsl (`javax.crypto.SecretKeyFactory`)

Nota sobre `Key.cryptsl`: a regra alveja a interface `java.security.Key`; specs como MacSpec e KeyStoreSpec **referenciam** `java.security.Key` em assinaturas de eventos, mas nenhuma spec tem `Key` como classe-alvo — a regra permanece sem spec.

## Specs sem regra (1)

- `RandomStringPassword.mop` — auxiliar de propagação de `Property.RANDOMIZED` entre `String.valueOf(Object)` e `String.toCharArray()`; não corresponde a nenhuma classe coberta pelas regras de api30.

## Observações de inventário

- Todas as 23 specs declaram `package mop;` e são ASCII puro; nenhuma spec duplicada dentro de `jca_android`.
- Convenção de nome irregular em dois arquivos: `IvParameterSpec.mop` (spec `IvParameterSpecSpec`) e `RandomStringPassword.mop` (spec `RandomStringPasswordSpec`) — o nome declarado da spec difere do nome do arquivo. Em `SecretKeySpec.mop` o nome declarado (`SecretKeySpec`) coincide com o arquivo, mas **não** com a classe monitorada (`SecretKey`).
- 4 das 23 specs são byte-idênticas às homônimas do conjunto congelado `jca` (DHGenParameterSpecSpec, GCMParameterSpecSpec, HMACParameterSpecSpec, RandomStringPassword); as outras 19 divergem — coerente com o papel de `jca_android` como portador das correções.
