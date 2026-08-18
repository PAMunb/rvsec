# gh104 — brief do pivô para Android (consolidado de 4 levantamentos)

## Decisão do pesquisador (2026-08-18)
1. Foco em Android. Conjunto sucessor = **`jca_android_v2`**, DIRETÓRIO NOVO.
2. Base = cópia dos `.mop` do **`jca` Java congelado** (NÃO do `jca_android`, que está quebrado).
3. **Sem `REQUIRES`/predicados**: nada de `ExecutionContext` (validate/setProperty/remove).
4. MetaCrySL fica **intocado**; as regras já geradas em `generated/api30/` são o oráculo.
5. Allow-lists das `.mop` := listas das `CONSTRAINTS` das regras api30, **literais**.
6. Fase 4 (weaver arity) entra em **modo contador, sem filtro**.
7. Fase 9 (predicados) cortada. Fase 8 encurtada (decidir depois).

## Números que justificam o pivô (ase-journal, `docs/20260806_owasp_cwe_mapping_report.md`)
Tier publicável com evidência de fonte primária: **11.409 eventos / 84 misuses (18,5% de 454)**.

| spec / ErrorType / valor observado | eventos | apps | misuses |
|---|---|---|---|
| `SSLContextSpec / UnsafeProtocol / TLS` | 8.648 | 60 | 65 |
| `KeyStoreSpec / InvalidKeyStoreType / AndroidKeyStore` | 2.005 | 11 | 12 |
| `TrustManagerFactorySpec / UnsafeAlgorithm / X509` | 643 | 3 | 5 |
| `CipherSpec / UnsafeAlgorithm / RSA/ECB/OAEPWithSHA1AndMGF1Padding` | 109 | 1 | 1 |
| `SignatureSpec / UnsafeAlgorithm / SHA256WITHRSA` | 4 | 1 | 1 |

Contexto fixado em **API 30 / Android 11**, Conscrypt branch `android11-release`
(`dataset.tex:5`; `mapping_report.md:622-648`).

## O que a troca de allow-list resolve sozinha
- `AndroidKeyStore`: api30 `KeyStore` = {AndroidKeyStore, PKCS12, BKS, BouncyCastle, AndroidCAStore} -> resolve os 2.005.
- `"TLS"`: api30 `SSLContext` = {Default, TLSv1.2, TLSv1.1, SSL, TLSv1, TLS, TLSv1.3} -> resolve os 8.648.

## O que a troca literal NAO resolve (exige regra de normalização declarada)
- `X509` (643 ev): é **alias Conscrypt de PKIX** (`OpenSSLProvider.java:101-107`), não algoritmo.
  api30 `TrustManagerFactory` = {PKIX} apenas. Sem tabela de alias, os 643 permanecem.
- `SHA256WITHRSA` (4 ev): api30 tem `SHA256withRSA`. Só caixa.
- `OAEPWithSHA1AndMGF1Padding` (109 ev): api30 tem `OAEPwithSHA-1andMGF1Padding`. Caixa + hífen.
- Aliases `SHA1`/`SHA`/`SHA256` (Conscrypt `OpenSSLProvider.java:131-132,140`) fragmentam
  **2.340 eventos / 22 misuses** em três grafias.
- Comparação é case-sensitive em 6 specs (`Mac`, `Signature`, `SecureRandom`, `KeyGenerator`,
  `TrustManagerFactory`, `KeyManagerFactory`) e `.toUpperCase()` em 3 (`MessageDigest`,
  `SSLContext`, `SecretKeySpec`).

=> **Regra proposta**: comparação case-insensitive + tabela de alias declarada, derivada do
Conscrypt `android11-release` com ponteiro por entrada, registrada por spec. Sem isso a
transcrição literal deixa ~3.000 eventos sem efeito.

## Conformidade atual `.mop` (jca) x api30 — 74 constantes comparadas
| veredicto | qtd |
|---|---|
| CRYSL-NAO-IMPLEMENTADO (regra declara, mop ignora) | 30 |
| IGUAL | 14 |
| MOP-SEM-BASE (mop testa o que a regra não declara) | 13 |
| MOP-MAIS-PERMISSIVO | 7 |
| DIVERGENTE | 7 |
| MOP-MAIS-RESTRITIVO | 3 |

Consequências diretas da transcrição literal:
- `SecretKeySpecSpec`: a allow-list de algoritmos é MOP-SEM-BASE (a regra nada declara sobre
  `alg`) -> **a lista some**.
- `CipherSpec`: hoje aceita só AES/RSA (via `CipherTransformationUtil.java`, NÃO no `.mop`);
  api30 aceita 8 algoritmos. A lista do Cipher vive em Java -> ou reescreve a classe ou move
  a lista para o `.mop`. **Decisão pendente.**
- `KeyPairGeneratorSpec`: api30 = {DSA, DH, RSA}; `EC` só aparece na implicação de keySize
  (`alg in {"EC"} => keySize in {256}`), sem estar na lista de algoritmos. Ramo morto.
  **Decisão pendente** (chave EC no AndroidKeyStore é caso comum).
- `SecureRandom`, `KeyManagerFactory`, `TrustManagerFactory`: api30 é mais restritivo e está
  certo (Windows-PRNG/NativePRNG/PKCS11/SunX509 não existem no Android).

## Remoção dos predicados — alcance medido no `jca`
24 eventos tocam predicado:
- **13** usam predicado só como GUARDA no `condition` -> remover é **ganho** (hoje silenciam a spec).
- **11** ACUSAM com base em predicado -> perda de detecção:
  - perda total (6): `IvParameterSpec c3/c4`, `PBEKeySpecSpec err2/err3`, `SecureRandomSpec setSeed3`, `GCMParameterSpecSpec:33`
  - perda parcial (2): `PBEParameterSpecSpec c3`, `SecretKeySpecSpec c3` (a metade allow-list sobrevive)
  - procedência de chave entre specs (3): `CipherSpec i2`, `MacSpec i1/i2` (`GENERATED_KEY`)
- Somem 9 sítios `remove(Property)` (contra apenas **2 `NEGATES`** em toda a api30).
- **Duas specs deixam de existir** (propagadores puros): `RandomStringPassword.mop`,
  `SecretKeySpec.mop`. Conjunto novo nasce com **21 specs**.
- Nota do ase-journal: chaves de `AndroidKeyStore`/Tink/`KeyGenParameterSpec` nunca carregam
  `GENERATED_KEY` (11.620 ev / 80 misuses / 25 apps) — ou seja, as 3 detecções de procedência
  perdidas já não funcionavam em Android.

## Defeitos estruturais prováveis (Fase 8 encurtada) — confirmados contra CrySL
1. `GCMParameterSpecSpec:33` evento nomeado `c1` deveria ser `c2` (a regra declara `c1` e `c2`;
   `c2` não existe no monitor gerado). 1 token.
2. `SecretKeySpecSpec:27-30` parêntese sobrando no `condition`.
3. `MessageDigestSpec:73` evento `reset` de corpo vazio, sem cláusula CrySL -> morto.
4. `KeyPairGeneratorSpec:26` `String algorithm` não inicializado.
5. Pointcuts mortos: `SignatureSpec:99,:106`, `SSLContextSpec:64` (tipo de retorno).
6. `KeyPairGeneratorSpec:71-72` ramo inalcançável.
7. **NOVOS** (achados agora): `KeyGeneratorSpec:47` e `MessageDigestSpec:55` testam
   `contains(currentAlgorithmInstance)` em vez de `contains(alg)` — o argumento recém-recebido
   nunca é avaliado.

## Correção do gate G-2 (Fase 6)
Os "18 eventos órfãos" NÃO são defeito: 17 dos 18 são a codificação correta de
`CONSTRAINTS`/`REQUIRES`/`FORBIDDEN` do CrySL (que por definição não entram no `ORDER`).
Único órfão real: `MessageDigestSpec:73 reset`.
=> G-2 precisa da regra CrySL como entrada. Gate novo e seguro a acrescentar:
**todo símbolo citado no `ere` tem declaração de evento** (pega o GCM, zero falso positivo).

## Mensagens que mentem — confirmadas contra a regra
- `PBEKeySpecSpec:50` diz ">= 1000", guarda testa `10000`; api30 `PBEKeySpec` = `>= 10000`.
- `PBEParameterSpecSpec:50` idem.
- `MessageDigestSpec:58,70,92` listam 3 entradas, a lista real tem 6.
- `CipherSpec:61,76` citam transformações que não refletem o `CipherTransformationUtil`.

## Geração do MetaCrySL (só para registro; não se altera nada)
Java 8 + `rascal-0.19.6.jar`, a partir da raiz do MetaCrySL, config
`samples/jca/android/config/Android30.config`. Nível de API é convenção de diretório +
lista de tiers no `.config`; refinement só sabe ADICIONAR (não há `remove`).

---

# DECISÕES FECHADAS (2026-08-18) — vinculantes para a reescrita da change

## D-a. `ErrorType` ganha os tipos corretos
Criar os tipos que faltam para que a spec identifique o erro corretamente e a mensagem seja
útil para o desenvolvedor que vai corrigir. `RequiredPredicate` NÃO entra (predicados saem).
`ForbiddenMethod` ENTRA — `FORBIDDEN` do CrySL não é predicado; é o que
`PBEKeySpecSpec f1/f2` codificam, e hoje eles reportam `InvalidSequenceOfMethodCalls`,
que é o tipo errado. Corrigir também os `ErrorType` errados já catalogados:
`PBEParameterSpecSpec:49` (`UnsafeAlgorithm` -> `UnsatisfiedConstraint`),
`PBEKeySpecSpec:24,30` (`InvalidSequenceOfMethodCalls` -> `ForbiddenMethod`).

## D-b. A allow-list do Cipher permanece em Java
Não migra para o `.mop`. Consequência: o conjunto novo precisa de uma **classe própria** —
`CipherTransformationUtil` é do `jca` congelado e `AndroidCipherTransformationUtil` é do
`jca_android`; nenhuma das duas pode ser alterada. Criar classe nova em
`rvsec-core/.../jca/util/` com as listas transcritas das CONSTRAINTS de
`generated/api30/Cipher.cryptsl`. O gate de conformidade de allow-list lê essa classe Java
para o Cipher e os `.mop` para as demais specs.

## D-c. `EC` entra na allow-list do `KeyPairGenerator`, com divergência registrada
Evidência: `samples/jca/android/11plus/KeyPairGenerator.ref:2` escreve
`define algorithm = {"EC"};` (comando que liga um buraco `${algorithm}`), mas
`samples/jca/base/KeyPairGenerator.cryptsl:27` escreve a lista como LITERAL
(`alg in {"DH","DSA","RSA"}`) em vez de `alg in ${algorithm}` — logo o `define` é
descartado em silêncio. Prova de que é defeito de modelagem e não intenção: a mesma tier
`11plus` usa o mesmo idioma em `KeyGenerator.ref` e funciona, porque
`base/KeyGenerator.cryptsl:27` tem o buraco. Só três specs base fixam literal
(`KeyManagerFactory`, `KeyPairGenerator`, `TrustManagerFactory`) e apenas o
`KeyPairGenerator` tem `.ref` Android tentando estendê-la.
Como as CONSTRAINTS do CrySL são conjuntivas, o api30 gerado hoje REJEITA `EC` e deixa a
cláusula `alg in {"EC"} => keySize in {256}` inalcançável.
Decisão: a allow-list do `jca_android_v2` inclui `EC` (keySize 256). Uma entrada no registro
de divergência do conjunto nomeia o defeito do MetaCrySL e diz que o conserto de raiz é
`alg in ${algorithm}` na spec base — não executado aqui por decisão de não alterar MetaCrySL.
Justificativa: transcrição literal fabricaria a mesma classe de `spec-artefact` que esta
change existe para eliminar (EC é o algoritmo recomendado pelo Android para AndroidKeyStore).

## D-d. As 11 fichas `tasks/*.md` são atualizadas e entram no commit
`tasks/E5-predicates.md` é DELETADO (grupo cortado). As demais são reescritas em coerência
com o `tasks.md` renumerado.

## Renomeação
`jca_v2` -> `jca_android_v2` em toda a change (142 ocorrências, 16 arquivos).
