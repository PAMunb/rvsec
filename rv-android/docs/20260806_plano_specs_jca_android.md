# Plano — adaptação das especificações JCA para Android (`jca_android`)

**Data:** 2026-08-06 (revisão 2)
**Estado:** planejamento. Nada implementado.
**Origem:** planejar a adaptação de `rvsec/rvsec-mop/src/main/resources/jca` para Android, à luz do dossiê OWASP/CWE (`ase-journal/docs/20260806_owasp_cwe_mapping_report.md`), das regras CrySL 3.1.5 (`/home/pedro/tmp/Crypto-API-Rules`), da tradução documentada na tese e do artigo em revisão.

> **Mudança em relação à revisão 1:** a rev. 1 recomendava *não* adotar o CrySL 3.1.5. Isso estava errado e foi corrigido. As regras CrySL são validadas por especialistas em segurança; o **julgamento criptográfico** delas se adota por padrão. O que precisa ser re-derivado é a **codificação Java SE** desse julgamento. A §6 foi reescrita sobre essa separação, agora quantificada.

---

## 1. O que a investigação achou

O dossiê CWE nasceu de um pedido do orientador — cruzar as violações com CWE/OWASP para ter noção de severidade. Ele não produziu severidade. Produziu uma **auditoria de validade das especificações**:

> De 454 misuses únicos, **2 classificam como fraquezas inequívocas**. Ambos são `KeyPairGeneratorSpec/InvalidKeySize`.

| classe | eventos | % | misuses únicos |
|---|---|---|---|
| `spec-artefact` | 36.097 | 37,2% | 223 |
| `instrumentation-artefact` | 35.368 | 36,5% | 128 |
| `context-dependent` | 25.546 | 26,3% | 101 |
| **`weakness`** | **7** | **0,0%** | **2** |

A pergunta original — criar um diretório irmão — está correta, mas cobre **uma de três camadas**.

### 1.1 Uma premissa a corrigir

O pedido menciona "senhas hardcoded". A semântica de `RandomStringPassword.mop` é **inversa**: ela não detecta credencial fixa, ela **propaga taint de aleatoriedade** através de `String.valueOf(Object)` e `String.toCharArray()`, para que uma senha legitimamente derivada de `SecureRandom` **não** seja acusada por `PBEKeySpecSpec.mop:38`. É infraestrutura do grafo de predicados, não detector.

**Nenhuma spec do conjunto `jca` detecta credencial hardcoded.** A tese registra isso como limitação inerente da RV (`tex/4_EstudoDeCaso.tex:171,405`) — sete de oito falsos negativos no CryptoBench vêm daí. É o caso legítimo de complementaridade com análise estática, não um bug. **O CrySL expressa isso** (`notHardCoded[password]`, `neverTypeOf[password, String]`) e o CogniCrypt achou 17 desses no corpus — ver §8.

---

## 2. As três camadas do problema

### Camada 1 — codificação de plataforma (Java SE → Android)

Corrigível dentro do `.mop`. **É o que o `jca_android` resolve.** 18 das 23 specs declaram procedência CrySL em cabeçalho `@see`.

| # | Spec | Defeito | Eventos |
|---|---|---|---|
| L1.1 | `KeyStoreSpec` | allow-list `{JCEKS,JKS,DKS,PKCS11,PKCS12}` (`:23`). No Android existem `AndroidKeyStore 18+`, `PKCS12 1+`, `BKS 1+`, `BouncyCastle 1+`, `AndroidCAStore 14+` — **dos cinco da lista, só `PKCS12` existe**. Sinal invertido vs. MASWE-0003. | 2.005 / 12 um |
| L1.2 | `SSLContextSpec` | exige `{TLSV1.2,TLSV1.3}` (`:23`). Duplamente errada: restritiva demais (`getInstance("TLS")` é o idioma da plataforma, API 1+) e **permissiva demais** — `getInstance("TLSv1.2")` não desabilita TLS 1.0/1.1, porque o conjunto habilitado vem dos defaults do socket (`TLSv1` *enabled* em 1+, `TLSv1.1` em 20+). | 8.648 / 65 um |
| L1.3 | `TrustManagerFactorySpec` / `KeyManagerFactorySpec` | allow-list `{PKIX, SunX509}`. **No Android só existe `PKIX \| 1+`**; `X509` é alias Conscrypt de `PKIX` (`OpenSSLProvider.java:101-107`). | 643 / 5 um |
| L1.4 | `SecureRandomSpec` | allow-list de 6 nomes; **só `SHA1PRNG` existe** no Android (Conscrypt registra um único serviço). | 0 hoje |
| L1.5 | `CipherTransformationUtil` | aceita `NoPadding` e `OAEPWithMD5AndMGF1Padding` (**inexistente no Android**), rejeita `OAEPWithSHA1AndMGF1Padding` (existe, API 10+) — inverte a ordem de força. Não conhece `PKCS7Padding` nem `RSA/NONE/*`. | 109 |
| L1.6 | 8 de 11 allow-lists | comparação **case-sensitive** via `List.contains` cru. Nomes de algoritmo são case-insensitive por especificação Oracle; a doc do Google escreve `HMACSHA256`, `AES/CBC/PKCS5PADDING`, `OAEPwithSHA-256andMGF1Padding`. | 4 provados |
| L1.7 | aliases | `MD5`/`SHA-1`/`SHA1`/`SHA` como quatro valores distintos numa spec que já normaliza case. Precisa de tabela de aliases. | 2.340 / 22 um |
| L1.8 | `androidx.security.crypto` | maior sítio isolado de violação de sequência do `KeyStoreSpec` (`MasterKeys.keyExists`). A biblioteca está **deprecada** desde 1.1.0 — sinalizar como deprecada é defensável; como tipo de keystore inválido, não. | 1.514 |

### Camada 2 — defeitos de autoria de spec, independentes de plataforma

Existem **igualmente no `jca`**, e serão copiados para o irmão se o fork for cego.

| # | Spec | Defeito | Sítio |
|---|---|---|---|
| L2.1 | `SecureRandomSpec` | `next2` (`nextBytes`) ausente do estado `end` → **`nextBytes()` duas vezes é violação** | `:155-162` |
| L2.2 | `KeyPairSpec` | exige `new KeyPair(pub,priv)` antes de `getPublic()`; chaves de `generateKeyPair()` vão direto para falha | transição `gpu` |
| L2.3 | `MessageDigestSpec` | `reset()` é evento mas está fora da `ere` → **sempre falha** | `:57-58` |
| L2.4 | `GCMParameterSpecSpec` | `c1` declarado duas vezes (`:23`,`:34`); a `ere` referencia um `c2` inexistente (`:48`) → **spec incapaz de emitir** | `:23,34,48` |
| L2.5 | `TrustManagerFactorySpec` | `gtm1` errado três vezes: retorno `KeyManager[]` para `getTrustManagers()` (nunca casa), binding `TrustManager[][]`, grava `GENERATED_KEY_MANAGERS` | `:62-66` |
| L2.6 | `KeyPairSpec` | `gpr` grava `GENERATED_PUBLIC_KEY`; **`GENERATED_PRIVATE_KEY` não é escrita por ninguém** → guarda `CipherSpec.mop:72` morta | `:35-39` |
| L2.7 | `MacSpec` | `f2` declara `target(m)` sem formal correspondente; propaga para o `.aj` de produção (`:454`) | `:76-81` |
| L2.8 | `SignatureSpec` | pointcuts mortos por tipo de retorno errado (`byte` para `sign()`) | `:99,106` |
| L2.9 | `KeyPairGeneratorSpec` | `switch` sobre `algorithm` sem inicializador → NPE no monitor | `:26,29` |
| L2.10 | `PBEKeySpecSpec` / `PBEParameterSpecSpec` | guarda `< 10000`, mensagem "at least 1000"; `ErrorType.UnsafeAlgorithm` para restrição de iteração | `:46-50` |
| L2.11 | `SecretKeySpecSpec` | parêntese excedente na `condition(` | `:27-30` |
| L2.12 | nomes | `IvParameterSpec.mop` declara `IvParameterSpecSpec`; `RandomStringPassword.mop` declara `RandomStringPasswordSpec` | `:17` / `:9` |

**E o mais grave: o grafo de predicados está majoritariamente desconectado.**

O CrySL expressa dependências entre objetos por `REQUIRES`/`ENSURES`. O JavaMOP não tem construto para isso, e a tradução emulou com um mapa global (`ExecutionContext` + `Property`) — decisão documentada em `rvsec-paper/rvsec.tex:40-43`, texto **100% comentado, nunca publicado**.

| Property | escreve | lê |
|---|---|---|
| `RANDOMIZED` | `SecureRandomSpec` (6 sítios), `SecretKeySpec`, `RandomStringPassword` | 6 specs |
| `GENERATED_KEY` | `KeyGeneratorSpec`, `KeyStoreSpec`, `SecretKeySpecSpec` | `CipherSpec.i2`, `MacSpec.i1/i2` |
| `GENERATED_PUBLIC_KEY` | `KeyPairSpec` (`:32` e, por engano, `:38`) | `CipherSpec` |
| `GENERATED_PRIVATE_KEY` | **ninguém** | `CipherSpec:72` — guarda morta |
| `PREPARED_IV`, `PREPARED_GCM`, `PREPARED_PBE`, `PREPARED_DH`, `PREPARED_HMAC` | 5 specs | **ninguém** |
| outras 9 (`ENCRYPTED`, `DIGESTED`, `SIGNED`, `SPECCED_KEY`, `GENERATED_KEY_STORE`, …) | várias | **ninguém** |

**14 das 23 Properties são escritas e nunca lidas.** O encadeamento `IvParameterSpec → Cipher.init(int, Key, AlgorithmParameterSpec)` e `GCMParameterSpec → Cipher.init(...)` — coração do `REQUIRES` do CrySL — é **decorativo**.

`SecureRandomSpec` é a raiz única de `RANDOMIZED` para seis specs, e é justamente a spec com o defeito L2.1. Se a raiz morre, seis specs entram em cascata de `UnsatisfiedConstraint`.

Consequência Android: chaves de `AndroidKeyStore`, `KeyGenParameterSpec` ou Tink **nunca carregam `GENERATED_KEY`** — os eventos `init` de `CipherSpec`/`MacSpec` não disparam e o monitor morre na chamada seguinte (11.620 eventos / 80 misuses / 25 apps).

### Camada 3 — infraestrutura, fora das specs

| # | Onde | Defeito |
|---|---|---|
| L3.1 | `DexWeaver.java:145-159` | colisão de wrappers: `put` last-writer-wins silencioso. Dois `after` advices que baixam para a mesma sobrecarga JDK → **só um dispara**. Censo: 7 assinaturas colidindo, 9 wrappers mortos. |
| L3.2 | `TrustManagerFactorySpec.mop:44-49` | `g3` declara `returning(...)` e nunca menciona o parâmetro monitorado `mf` — atribuição pode cair em instância de monitor diferente. Hipótese concorrente a L3.1 para os 8.843 eventos com algoritmo vazio. |
| L3.3 | `ErrorDescription.java:108-139` | `equals`/`hashCode` excluem `expecting` → dedup **não determinística**. |
| L3.4 | `rvsec-core/.../CipherTransformationUtil.java` | política de cifra em **Java hardcoded, compartilhada pelos dois spec sets**. Forkar `CipherSpec.mop` **não muda a política de cifra**. |
| L3.5 | `rvsec-logger-logcat/ErrorCollector.java:39` | `escapeSpecialCharacters()` desativado (chamada comentada) → `expecting` com vírgula quebra o CSV. |
| L3.6 | `rv-experiment/config.py:873-936` | **a análise estática ignora `--specification-set`**: `mop_dir` nunca chega ao GATOR, o default `.../resources/jca` prevalece sempre. Já é bug hoje. |
| L3.7 | `MOPGen.java:94-96` | filtro de limpeza morto (`toLowerCase().startsWith("MultiSpec")` nunca é verdadeiro). O `.aj` obsoleto persiste em `resources/jca/`, é **reingerido** pelo `agent-gen` e **empacotado no jar**. |
| L3.8 | descritor de hooks | `Signature.getInstance(String,Provider)`, `Mac.getInstance(String,Provider)` e `MessageDigest.clone()` não cobertos → falsos negativos. |
| L3.9 | `ViolationRecorder.java:38` | `new Exception().getStackTrace()` por violação; sob R8/ProGuard cai em fallback degradado. |

---

## 3. Verificado × hipótese

**Verificado contra fonte primária ou código:** toda a camada 1, toda a camada 2 exceto agregados, L3.3–L3.9, e a tabela I/P/R da §6.

**Não reproduzido:** L3.1 e os quatro defeitos de typestate vieram de análise de subagente. O dossiê os marca como *"o achado mais importante da sessão e o menos verificado"* e impõe **embargo de publicação** sobre as três alegações-manchete (59% / 73,7% / 2-de-454).

**Aberto (G0):** L3.1 e L3.2 são hipóteses concorrentes. Sob L3.1, `TrustManagerFactorySpec` é 100% falso positivo. Sob L3.2, os reports de `X509` são observações genuínas. **A classificação de ~35.368 eventos é provisória.**

---

## 4. Instrumentação — o que está de fato em uso

Verificado, e há uma divergência que precisa ser corrigida:

- **O default de código é `ajc`**, e **nunca foi exercido por nenhuma campanha real**. `experimento-gov/scripts/instrument_gov.py:70` traz o comentário literal: `"--instrumentation-variant dexlib2 "  # <-- CLI default is ajc; force dexlib2`.
- **Toda a instrumentação que produziu dados é `dexlib2`.** Os 219 APKs do artigo vêm de `experimento-20260706` (`README.md:12,28`; `docker-compose.gcp.yml:5,9,42`); os 163 são o estágio `funnel_stage=='selected'` sobre o mesmo corpus, não outra campanha. Os composes de todas as campanhas fixam `dexlib2`.
- **Armadilha de leitura:** vários `experiment_config.json` recentes gravam `"instrumentation_variant": "ajc"` — mas sempre junto de `"instrument_apks": false`. É o default inerte do Click sendo serializado, não a variante que produziu os binários. Único `ajc` genuíno: `preprocessing_v2`/`v3`, pré-gh52.
- **O artigo descreve dexlib2** e trata o pipeline dex2jar+ajc+d8 como abandonado (34,6% de sucesso, contra 97,3% do dexlib2).
- **Sítios a corrigir para o default refletir a prática:** o default do CLI, `PY/README.md:355`, `PY/modules/rv-experiment/README.md:266`.

Consequência para este plano: **toda decisão de spec deve ser validada no caminho dexlib2**, e o harness da §7 deve rodar nele. O caminho ajc só interessa como comparação histórica.

### 4.1 O que o weaver dexlib2 realmente suporta — e o que falha em silêncio

As 23 specs atuais usam **exclusivamente `call(...)`** — 116/116 pointcuts. Isso é sorte, não desenho, porque o suporte a pointcuts é bem mais estreito do que o descritor sugere. O JSON emitido pelo javamop grava a expressão AspectJ **verbatim, sem filtrar tipo** (`DescriptorWriter.java:114-117`); toda a restrição está no matcher.

| PCD | Estado no `DexWeaver` |
|---|---|
| `call(...)` | **completo** — owner exato ou subtipo (`T+`), glob de nome, retorno, aridade, bindings de `args`/`target`/`$return` (`PointcutMatcher.java:308-411`) |
| `staticinitialization(...)` | **completo**, inclusive sintetizando `<clinit>` quando não existe (`DexWeaver.java:331-340`) |
| `args`/`target`/`if`/`adviceexecution` | ok no contexto de `call` |
| `!within(...)` | parcial — só a forma negada, usada no `commonPointcut` |
| **`execution(...)`** | **stub.** `ExecutionPC` guarda o corpo como string opaca; o matcher faz `if (instructionIndex != 0) return empty; return Match.empty(ex)` (`PointcutMatcher.java:509-515`) — **ignora a assinatura**, casa a entrada de *todo* método e **não produz bindings**. Qualquer advice com argumento ligado morre em `UnresolvedBindingException` e é descartado com contador `plansSkippedUnresolvedBinding` (`DexWeaver.java:440-461`) |
| **`withincode`, `initialization`, `preinitialization`, `handler`, `cflow`, `cflowbelow`, `get`, `set`, `this`** | **ausentes, e falham em silêncio.** Caem no `default` do parser (`PointcutExpressionParser.java:142`) → `NamedRefPC` → **match-true** no matcher. O weaver tece como se a cláusula não existisse |
| `around` | único rejeitado alto (`UnsupportedOperationException`) |

**Isto é um risco de autoria, não só uma limitação.** A lista "out of scope" documentada em `rv-instrumentation-dexlib2/errors.py:28-37` descreve uma intenção que o parser **não faz cumprir**: escrever uma spec nova com `cflow(...)` ou `withincode(...)` produz instrumentação silenciosamente errada, sem erro nem aviso. Qualquer spec nova precisa ser validada pelo harness da §7 — revisão de código não pega isto.

**Regras que observam implementações do próprio app** (trust-all `TrustManager`, `HostnameVerifier`, WebView `onReceivedSslError`) são inviáveis hoje, por dois motivos:

1. `call(...)` não tem join point: `checkServerTrusted` e `onReceivedSslError` são invocados pela pilha SSL/WebView do framework, que nunca é instrumentada. **Não existe call site no app.**
2. `execution(...)` é o PCD certo e está quebrado.

A máquina de tecer corpo de método existe — `DexWeaver.java:341` itera todas as classes do APK, incluindo o código do app —, mas **o `CoverageWeaver` não é reutilizável**: é passe hardcoded, não recebe descritor nem matcher, e não importa nada do `pointcut-engine` (`CoverageWeaver.java:106-120`; `coverage-weaver/pom.xml:20`). O que é reutilizável é a camada baixa: `RegisterShifter.spillLowRegisters`, `InstructionInjector` e `InsertionPoint.METHOD_ENTRY`, hoje exercitados só pelo `StaticInitializationEmitter`.

Faltam três peças para viabilizar: (i) `ExecutionPC` com AST real de assinatura, com `T+` resolvido pelo `InheritanceResolver`; (ii) **binding de `this` e dos parâmetros aos registradores de entrada do método** — a peça de verdade; (iii) um `ExecutionEmitter` usando `METHOD_ENTRY`. (i) e (iii) são pequenas.

---

## 5. Fase 0 — reprodução (bloqueante)

Antes de escrever uma linha de `.mop`. Consertar uma allow-list que nunca é lida porque o wrapper morreu não conserta nada e mascara o defeito real.

- **F0.1** Reproduzir independentemente a colisão de wrappers (`DexWeaver.java:145-159`) — decidir entre L3.1 e L3.2.
- **F0.2** Reproduzir os quatro defeitos de typestate sobre o **monitor gerado**, não sobre o `.mop`.
- **F0.3** Recontar mecanicamente os ~50 sítios `addError`.
- **F0.4** *(fechado — §4.1)* `execution(...)` é stub e sete PCDs falham em silêncio. Deriva daqui uma tarefa nova: **F0.4' — gate de PCD**, um verificador que rejeite, na geração, qualquer spec que use PCD não implementado, em vez de tecer errado sem avisar.

---

## 6. O CrySL 3.1.5 — o que se adota e o que se re-deriva

Regras baixadas: tag `3.1.5-jca`, **2026-08-03**, sintaxe CrySL 4.0.2 (linha CryptoAnalysis 4.x), 51 regras JCA. A tradução original usou o repositório acessado em **2022-08-22**, sem commit fixado.

> **Decisão D3 tomada: o `jca_android` fica na `1.5.2-jca`, a mesma release do baseline CogniCrypt.** A análise I/P/R abaixo permanece como instrumento de referência — ela é o que identifica o que é codificação Java SE e o que é julgamento —, mas o **julgamento** adotado continua sendo o da 1.5.2. A migração para a 3.1.5 vira trabalho posterior, e quando ocorrer terá de ocorrer **nos dois lados** para o Venn não comparar releases diferentes. Consequência prática: RSA-2048 continua aceito, AES/CBC continua aceito, `PBEWithHmacSHA*` no `Mac` continua aceito.
>
> **O que muda mesmo assim** são as categorias **P** (codificação Java SE → Android) e os defeitos de autoria da camada 2. Essas duas frentes são independentes da release.

**Postura:** o julgamento criptográfico do CrySL é validado por especialistas e se adota por padrão. O que se examina é a codificação. Três categorias:

- **(I) Julgamento portável** — vale em qualquer plataforma. Adota-se como está.
- **(P) Codificação Java SE** — julgamento certo expresso por nomes/tipos que só existem na Oracle JRE. A lista se re-deriva para Android; o julgamento fica.
- **(R) Certo, mas não realizável** — a plataforma não oferece, ou só a partir de certo API level. Exige política explícita.

### 6.1 Veredito quantitativo (51 regras)

| Categoria | Nº | % |
|---|---|---|
| **I** — adota-se como está | **37** | 73% |
| **P** — re-derivar a lista | **8** | 16% |
| **R** — condicionar ao API level | **4** | 8% |
| Inaplicáveis (classe inexistente no Android) | **2** | 4% |

As 8 **P**: `SecureRandom`, `KeyStore`, `TrustManagerFactory`, `KeyManagerFactory`, `SSLContext`, `SSLEngine`, `SSLParameters`, `ECGenParameterSpec`.
As 4 **R**: `Cipher` (mista), `SecretKeyFactory` (26+), `Mac` (PBE-MAC 26–31 + `preparedHMAC` insatisfazível), `AlgorithmParameterGenerator` (`AES` só 1–8).
As 2 inaplicáveis: `Cookie` (`javax.servlet`), `HMACParameterSpec` (`javax.xml.crypto` — **o pacote não existe no Android**; e como `Mac.crysl` tem `REQUIRES preparedHMAC[params]`, esse predicado é insatisfazível lá).

**Leitura:** ~73% das regras atravessam sem tocar em nada. O dano concentra-se em duas frentes, ambas de *codificação*: (i) toda a superfície TLS/PKI enumera nomes Oracle — `SunX509` some, `JKS/JCEKS/DKS/PKCS11` somem, 8 das 12 cipher suites somem; (ii) a criptografia baseada em senha inteira exige API 26+, com os PBE-MACs removidos na API 32.

### 6.2 Fatos Android verificados que sustentam a re-derivação

Todos extraídos das tabelas "Supported algorithms" de `developer.android.com/reference` e do código do Conscrypt/AOSP-BouncyCastle:

| Área | Fato |
|---|---|
| KeyStore | `AndroidKeyStore 18+`, `PKCS12 1+`, `BKS 1+`, `BouncyCastle 1+`, `AndroidCAStore 14+`. **Sem JKS, JCEKS, DKS, PKCS11.** |
| TMF/KMF | **`PKIX \| 1+`, e só.** |
| SSLContext | `TLS 1+`, `SSL 10+`, `SSLv3 10-25`, `TLSv1 10+`, `TLSv1.1 16+`, `TLSv1.2 16+`, `TLSv1.3 29+` |
| SSLSocket (habilitados por default) | `TLSv1 1+`, `TLSv1.1 20+`, `TLSv1.2 20+`, `TLSv1.3 29+` — **`getInstance("TLSv1.2")` não desabilita 1.0/1.1** |
| Cipher AES | `CBC CFB CTR CTS ECB OFB \| 1+`; `GCM \| 10+`; `GCM-SIV \| 30+`; `AES_128`/`AES_256 \| 26+`. Conscrypt registra só `ECB CBC CTR GCM GCM-SIV`; CTS/OFB/CFB resolvem pelo **BouncyCastle do AOSP** |
| Cipher RSA | `ECB NONE \| NoPadding OAEPPadding PKCS1Padding \| 1+`; `OAEPwithSHA-1/256andMGF1Padding \| 10+`; `SHA-224/384/512 \| 23+`. **Nenhuma linha `OAEPwithMD5`** |
| SecretKeyFactory | `PBKDF2withHmacSHA1 \| 10+`; `PBKDF2withHmacSHA224/256/384/512 \| 26+`; `PBEwithHmacSHA*AndAES_* \| 26+` |
| Mac | `HmacSHA256/384/512 \| 1+`; `PBEwithHmacSHA1 \| 1+`; **`PBEwithHmacSHA224/256/384/512 \| 26-31`** (removidos depois) |
| Curvas EC (Conscrypt) | `secp224r1`, `prime256v1`/`secp256r1`, `secp384r1`, `secp521r1`. **Nenhuma brainpool** |
| GCM | classe `GCMParameterSpec` **19+**; Android 12 exige IV de **exatamente 12 bytes** |

### 6.3 Três correções factuais à revisão 1

1. **`AES/CTS` e `AES/OFB` não estão ausentes do Android** — estão ausentes do *Conscrypt*, mas resolvem via o BouncyCastle do AOSP, e a tabela oficial os lista como `1+`. A afirmação da rev. 1 de que "a regra reduz o AES a GCM e CTR" **não se sustenta como estava**. Sustenta-se por outro caminho: esses modos só existem por um provider cujo uso explícito o Google depreciou.
2. **`PBEWithHmacSHA*AndAES_*` existem** (API 26+), e o Conscrypt os aliasa literalmente para `AES_n/CBC/PKCS5PADDING`. Ou seja: **a CrySL bane CBC no allow-list de `mode` e o readmite pela porta dos fundos no allow-list de `alg`.** É defeito interno da regra, a corrigir independentemente de Android.
3. **A tensão TLS é dupla, não simples.** `getInstance("TLSv1.2")` fixa o máximo em 1.2 (portanto desabilita 1.3, como o dossiê apontou) **e** não remove 1.0/1.1 do conjunto habilitado. A regra é simultaneamente restritiva demais e permissiva demais — o que **fortalece** o argumento de que o predicado está no lugar errado.

### 6.4 Os cinco casos difíceis

**`Cipher` — CBC/PCBC banidos, `NoPadding` exigido.** A regra está certa no julgamento e a doc do Google está desatualizada; mas a codificação da regra também está errada. O BSI TR-02102-1 recomenda GCM/CCM/OCB e só admite CBC acompanhado de MAC, com ressalva explícita de padding oracle; o NIST mantém CBC como aceitável. Banir CBC *sem autenticação* é defensável e alinhado ao BSI; banir CBC *sempre* é mais duro que o NIST. A doc do Android se contradiz dentro da mesma página — a tabela recomenda "AES in either CBC or GCM mode" e o exemplo de código escreve `Cipher.getInstance("AES/CBC/PKCS5PADDING")` — e o Jetpack `security-crypto`, que era a via idiomática para AES-GCM, está **deprecado sem substituto**. Reformulação proposta: `mode in {"GCM","GCM-SIV","CTR"}`, que mantém o julgamento, elimina os modos que só existem via um provider depreciado e evita que a regra recomende implicitamente o BC. Fica pendente uma contradição entre duas fontes primárias do Google (a nota da Android 12 diz ter removido as implementações AES do BC; a tabela do `Cipher` continua listando `1+`) que **não se resolve sem executar em dispositivo** — item para o harness da §7.

**`KeyStore` — o que a regra realmente quer.** JKS deriva a chave de integridade de SHA-1 sobre a senha; JCEKS usa PBEWithMD5AndTripleDES. A CrySL **os inclui no allow-list**, o que só faz sentido se o objetivo for "tipos que o SunJCE oferece", não "tipos seguros". É o retrato da categoria P: a lista é inventário de provider, não julgamento. Reformulação: `type in {"AndroidKeyStore","PKCS12"}`, com `AndroidKeyStore` preferido — não é formato de arquivo, é container respaldado por hardware onde o material da chave nunca entra no processo. **`BKS` fica de fora**: usa a mesma família PBE/SHA-1 do JKS, e aceitá-lo seria propagar para o Android o erro que a lista Java SE já contém. Ressalva: o `ORDER Get, Load, …` exige `load(...)` antes de qualquer uso, e com `AndroidKeyStore` o idioma é `load(null)` — a constraint `notHardCoded[passwordIn]` sobre `null` é falso positivo em potencial.

**`SecureRandom` — a lista é toda nome de provider.** O julgamento é "não use PRNG não-criptográfico". Dos seis nomes só `SHA1PRNG` existe no Android, e o comentário no código do Conscrypt diz que ele só foi registrado *"because various documentation mentions that algorithm by name instead of just recommending calling `new SecureRandom()`"* — o nome é rótulo legado para o CSPRNG do BoringSSL, não SHA-1. **Verificado no `.crysl`: `new SecureRandom()` não passa por nenhuma restrição de algoritmo** (a constraint só vincula `getInstance`), então o idioma Android já é aceito. A regra precisa perder cinco dos seis nomes e ganhar: FORBIDDEN sobre `getInstance("SHA1PRNG","Crypto")` (lança `NoSuchProviderException` desde a API 28) e desencorajamento de `setSeed()` antes de `nextBytes()`.

**`SSLContext` — o predicado está no lugar errado.** Reformulação: aceitar `protocol in {"TLS","TLSv1.2","TLSv1.3"}` no `getInstance`, e **deslocar a exigência para onde o conjunto é de fato fixado** — `setEnabledProtocols` no `SSLSocket`/`SSLEngine`/`SSLParameters`, com `elements(protocols) ⊆ {"TLSv1.2","TLSv1.3"}`. Em CrySL: um `ENSURES generatedSSLContext[this]` que só é emitido quando o `REQUIRES restrictedProtocols[…]` do consumidor é satisfeito. O `FORBIDDEN getDefault()` fica.

**`PBEKeySpec` / `SecretKeyFactory` — tensão genuína.** `PBKDF2withHmacSHA1` existe desde a API 10; os SHA-2 só a partir da **26**. A CrySL bane exatamente o único universalmente disponível. A favor da regra: HMAC-SHA1 dentro do PBKDF2 não é vulnerabilidade prática — a resistência a colisão do SHA-1 é irrelevante num KDF baseado em HMAC, e o que protege é o `iterationCount`. Contra o banimento absoluto: num app com `minSdk 21` não há alternativa dentro da plataforma, e a "correção" empurraria para implementação própria ou dependência de terceiros — pior. Conciliação: (a) `iterationCount >= 10000` como **I** puro; (b) allow-list **dependente do manifesto** — `minSdk >= 26` ⇒ exigir SHA-2; `minSdk < 26` ⇒ `PBKDF2WithHmacSHA1` vira achado informativo de "limitação de plataforma", com exigência compensatória de `iterationCount` mais alto. Isto introduz um conceito novo no conjunto: **constraint condicionada ao `minSdk` do app**, que hoje nenhuma spec expressa.

### 6.5 O artefato que falta: a tabela de política

Hoje não existe, em nenhum repositório, documento que justifique um único valor de allow-list. A tese não traz tabela de mapeamento; a única descrição sistemática do mapeamento CrySL→JavaMOP está **100% comentada** em `rvsec-paper/rvsec.tex:28-166`. `FORBIDDEN` e `NEGATES` nunca são mencionados — nem para dizer que foram ignorados.

O `jca_android` nasce com esse artefato: **uma linha por constraint**, colunas

`spec | constraint (literal .crysl) | categoria I/P/R | valor jca 2022 | valor CrySL 3.1.5 | valor jca_android | fato Android + API mín. | fonte | CWE/MASWE`

Fontes admissíveis: tabelas "Supported algorithms" de `developer.android.com/reference`, código do Conscrypt/AOSP, NIST SP 800-131A Rev.2 / 800-38, BSI TR-02102-1, MASVS v2 / MASWE (com commit SHA — os IDs foram renumerados em julho de 2026), AOSP Severity Ratings, Google Play ASI. Sem fonte citada, a revisão vira opinião.

---

## 7. Fase 1 — o harness de conformidade (o oráculo que não existe)

Este é o entregável que separa o plano de "editar allow-lists".

A tradução de 2022 teve um oráculo: a suíte JUnit do CogniCrypt (31 classes, 200+ métodos), rodada em JSE por TDD (`tex/3_Implementacao.tex:151`). **Esse oráculo não existe para Android**, e é exatamente onde os defeitos moram — nenhum defeito da camada 2 é erro de allow-list, e vários só se manifestam **depois do weaving em DEX**.

**Proposta:** APK sintético de conformidade, com sítios de chamada rotulados (`espera-violação` / `espera-silêncio` / `espera-predicado-propagado`), instrumentado pelo pipeline **dexlib2 de produção** e executado via `rv-platform`, com as linhas `RVSEC` comparadas ao rótulo. Estimativa: 60–80 sítios. Custo: um APK, minutos.

Quatro propriedades:

1. **Distingue defeito de spec de defeito de instrumentação** — resolve a G0 empiricamente.
2. **Cobre a superfície Android real** (AndroidKeyStore, `KeyGenParameterSpec`, Conscrypt, aliases `X509`/`SHA1`/`PKCS7Padding`) que nenhuma suíte JSE alcança.
3. **Resolve empiricamente as contradições de documentação** — em particular se `AES/CTS` e `AES/OFB` de fato resolvem no Android 12+ (§6.4).
4. **Vira artefato de replicação publicável** — o artigo tem `\replication = \todo{replication URL}` (`packages.tex:19`) como bloqueador declarado, prometido em quatro sítios do texto.

Oráculo complementar barato: o `RuleCorrectnessTests` do CrySL 3.1.5, como checklist de revisão.

---

## 8. Impacto empírico medido — e é aqui que a expectativa precisa ser calibrada

Medi sobre o dataset do artigo (`ase-journal/dataset/`) o que adotar o CrySL 3.1.5 renderia. **O resultado é sóbrio e muda a justificativa do trabalho.**

**8.1 O baseline do CogniCrypt da campanha é a CrySL `1.5.2-jca` (2023-08-14).** Identificado por comparação byte a byte contra as tags do upstream:

| Item | Valor |
|---|---|
| Motor | `HeadlessAndroidScanner 5.0.1` = CryptoAnalysis 5.0.1 + boomerangPDS/idealPDS 4.3.2 + **CrySLParser 4.0.5**; jar de 2025-08-14 |
| Invocação | `runner.py:96-99` — `java -Xmx64g -Xss1024m -jar <jar> --apkFile <apk> --platformDirectory <sdk/platforms> --rulesDir <rules>` |
| Ruleset | `rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules`, 49 `.crysl`, byte-idêntico a `rvsec-cognicrypt/CrySL-Rules` |
| **Versão do ruleset** | **`1.5.2-jca`** — 48 de 49 arquivos byte-idênticos à tag; único desvio: `SSLEngine.crysl` |
| Contra a 3.1.5-jca | 36 idênticos, **13 divergem**, e a 3.1.5 tem 2 regras a mais (`PrivateKey`, `PublicKey`) |
| Regras inertes | **2 das 49 falham no parser do CrySL e são silenciosamente puladas** (`config.py:594`) |

As 13 divergentes: `Cipher`, `KeyPairGenerator`, `Mac`, `SecretKeySpec`, `SecretKey`, `Key`, `KeyPair`, `OAEPParameterSpec`, `RSAKeyGenParameterSpec`, `DSAGenParameterSpec`, `AlgorithmParameterGenerator`, `SSLEngine`, `SSLParameters`.

Semântica verificada direto no arquivo da campanha:
- `Cipher.crysl:97` — `alg in {"AES"} => mode in {"CBC","GCM","PCBC","CTR","CTS","CFB","OFB"}`; `:112` — `CBC/PCBC => pad in {"PKCS5Padding","ISO10126Padding"}`
- `KeyPairGenerator.crysl:29-31` — RSA `{4096,3072,2048}`, DSA `{2048}`, DH `{2048}`

O CBC saiu do upstream em **2024-04-24** (`5d9bc97 Remove CBC mode from all rules`).

**Leitura correta:** o baseline não é "regra frouxa" — é uma release **também validada por especialistas**, só que ~3 anos mais velha. A questão não é "CrySL sim ou não", é **qual release**, e a mesma escolha vale para os dois lados. Se o RV adotar a 3.1.5 e o baseline CC ficar na 1.5.2, o Venn passa a comparar releases diferentes do mesmo conjunto de regras — assimetria que precisa ser resolvida ou declarada.

**Argumento adicional para atualizar, independente de estritez:** `SSLEngine.crysl` e `OAEPParameterSpec.crysl` estão entre as 13 que a 3.1.5 alterou, e são regras hoje inertes por falha de parser. Atualizar pode recuperá-las.

### 8.1.1 O delta `1.5.2` → `3.1.5`, e por que ele se divide em duas metades

13 regras alteradas, 2 novas (`PrivateKey`, `PublicKey`), 10 commits entre 2023-03 e 2026-04.

**Metade A — endurecimento de política (BSI TR-02102-1).** É o que a D3 deixa de fora.

| Regra | `1.5.2` | `3.1.5` |
|---|---|---|
| `Cipher` | AES `{CBC,GCM,PCBC,CTR,CTS,CFB,OFB}`; CBC/PCBC com `PKCS5Padding`/`ISO10126Padding`; PBE-AES ⇒ `CBC` | AES `{GCM,CTR,CTS,CFB,OFB}`, só `NoPadding` (`5d9bc97`, 2024-04-24, *"Remove CBC mode from all rules"*) |
| `KeyPairGenerator` | RSA `{4096,3072,2048}`, DSA `{2048}`, DH `{2048}` | RSA `{4096,3072}`, DSA `{3072}`, DH `{3072}` |
| `RSAKeyGenParameterSpec` | `{1024,2048,4096}` | `{3072,4096}` |
| `DSAGenParameterSpec` | primeP `{1024,2048,3072}`, subQ `{160,224,256}` + implicações | primeP `{3072}`, subQ `{256}` |
| `SSLEngine` / `SSLParameters` | 12 suites TLS 1.2, incluindo `*_CBC_SHA256/384` | só as AEAD/GCM |
| `AlgorithmParameterGenerator` | `{DH,DiffieHellman,DSA}`, size `{2048,3072}` | + `AES`/`Camellia`/`Shacal2`/`ElGamal`; DH/DSA/ElGamal ⇒ `{3072}` |

**Metade B — correção de modelagem de predicado.** **Não é mudança de julgamento — é conserto de falso positivo**, da mesma natureza da nossa camada 2. Pode ser absorvida mantendo a política na `1.5.2`.

| Regra | Mudança | Relevância direta |
|---|---|---|
| `Cipher` | `generatedKey[key,_]` → `generatedKey ‖ generatedPubkey ‖ generatedPrivkey` | **é o mesmo defeito do nosso L2.6** — chave assimétrica não satisfazia o predicado |
| `Cipher` | `!macced[_, plainText]` → `!macced[this, plainText]` | binding de parâmetro; mesma família do L3.2 |
| `Cipher` | evento `getIV` e `callTo[IV]` removidos (`8e9099f`) | simplifica o `ORDER` |
| `Mac` | `ORDER Get, Init, (FinalWU \| (Update+, Final))` → `…)+` | permite **reutilizar** o `Mac`. Temos 806 eventos de `InvalidSequenceOfMethodCalls` no `MacSpec` classificados como artefato — candidato forte à mesma causa |
| `SecretKeySpec` | `preparedKeyMaterial` → `preparedKeyMaterial ‖ randomized` (`db186ff`, 2026-04-02) | fecha aresta do grafo |
| `Key`, `SecretKey` | ganham `REQUIRES` | idem |
| `KeyPair` | `noCallTo[Con] => generatedKeypair[this,_]` | **cobre o nosso L2.2** — chaves de `generateKeyPair()` sem construtor explícito |
| `PrivateKey`, `PublicKey` | regras novas (`a291d81`, 2023-12-07) | dariam produtor a `GENERATED_PRIVATE_KEY`, hoje escrita por ninguém (L2.6) |
| `OAEPParameterSpec` | remove `OBJECTS` morto | higiene |

> **Decisão tomada: não absorver nada da `3.1.5`, nem a metade A nem a metade B.** O `jca_android` fica 100% ancorado na `1.5.2`, a mesma release do baseline CogniCrypt, sem exceções. Os defeitos da camada 2 — inclusive L2.2 e L2.6, que a metade B também resolve — são corrigidos **por conta própria**, documentados como decisão nossa e não como importação do upstream.
>
> Vantagem desta escolha: a proveniência fica uniforme e auditável — *uma* release de referência (`1.5.2-jca`), *uma* lista de desvios deliberados nossos, e o Venn com o CogniCrypt permanece simétrico em política **e** em modelagem. A tabela acima permanece no plano como registro do que existe upstream, útil quando a migração de release for reavaliada.

**8.2 Os dois números decisivos são inobteníveis do dataset.** Nem o RV nem o CogniCrypt registram uso *aceito* — só violações. Censo completo: `AES/CBC/PKCS5Padding` tem **0 ocorrências em todo o dataset**; o único `CipherSpec/UnsafeAlgorithm` são 109 eventos de um app (`RSA/ECB/OAEPWithSHA1AndMGF1Padding`); os 7 eventos `InvalidKeySize` são RSA fora de {2048,3072,4096} e um DSA — nenhum é RSA-2048. Para saber quantos apps usam `AES/CBC/*` ou RSA-2048 seria preciso **uma varredura estática de constantes string nos argumentos de `Cipher.getInstance` e `KeyPairGenerator.initialize` sobre os 163 APKs instrumentados** — barato, sem re-executar a campanha. É o item de maior retorno imediato do plano inteiro.

**8.3 O delta medido sobre o Venn é quase nulo.** Dos 311 achados só-CogniCrypt, apenas **96** têm `ConstraintError` (a única região onde "spec mais frouxa que CrySL" faz sentido). Desses 96, **~91 vêm de constraints que a spec RVSec já tem exatamente iguais** — a diferença é cobertura de execução, não estritez. O delta real de estritez é **6 achados** (`Mac`/`HmacSHA1`) e **17** de `notHardCoded`/`neverTypeOf`, que são **capacidade ausente**, não constraint frouxa. Estimativa de ganho por endurecer constraints: **≈ 0–23 de 311**.

**8.4 Os detectores que já funcionam não são fonte de ganho.** SHA-1 já rende 2.340 eventos / 21 apps; MD5, 3.552 / 20 apps. `DES/3DES/RC4/Blowfish` **já são flagados** hoje (`isValid` só aceita AES e RSA) e têm **0 ocorrências** em 97.018 eventos.

**8.5 O ganho aterrissa em biblioteca de terceiros.** 87,1% dos só-CC e 81,3% dos só-CC-com-ConstraintError estão em código de biblioteca. Onde app-code pesa é `KeyStoreSpec` (32,7%) — e é `AndroidKeyStore`, ou seja, **falso positivo estrutural**, não ganho.

**8.6 A lacuna de maior retorno estrutural não é estritez, é spec ausente.** `javax.crypto.SecretKeyFactory` mapeia para `None` em `cc_rv_mapping.csv` — **não existe `SecretKeyFactorySpec.mop`**. Os achados relevantes (`PBKDF2withHmacSHA1` no FreeOTP, `DES` no ufirewall) nem entram no Venn. Criar essa spec independe da versão do CrySL.

> **Conclusão da §8:** adotar o CrySL 3.1.5 se justifica por **correção e defensabilidade** — as regras são validadas por especialistas, e hoje divergimos delas sem justificativa escrita —, **não por rendimento de detecção**. O rendimento vem de outro lugar: consertar a camada 2, criar as specs ausentes (`SecretKeyFactory`) e escrever as regras Android que o CrySL não tem.

---

## 9. Fase 2 — o conjunto `jca_android`

> **Estado em 2026-08-06 — o conjunto foi produzido por derivação, não por tradução.**
> A F2 foi executada na change `gh99-metacrysl-jca-android` ([#99](https://github.com/PAMunb/rvsec/issues/99)).
> Em vez de uma segunda tradução à mão — que repetiria a ameaça **W3** — as regras
> Android saem do **MetaCrySL**, a camada de meta-especificação sobre CrySL: 32 specs
> base mais uma cadeia ordenada de refinamentos por nível de API compõem, para o alvo
> **API 30**, 33 regras `.cryptsl` em `$WS/MetaCrySL/generated/api30/`. O conjunto
> `jca_android` tem **23 `.mop` e nenhum `.aj`** (a ressalva do §9.1 foi respeitada):
> 10 arquivos adaptados, cada divergência ancorada numa regra gerada, e 13 mantidos
> verbatim. Seis specs — `SSLContext`, `KeyStore`, `Mac`, `MessageDigest`,
> `KeyManagerFactory`, `TrustManagerFactory` — batem elemento a elemento com as
> tabelas da própria plataforma no API 30.
>
> Três resultados que corrigem previsões feitas aqui no §9.2:
>
> - O `KeyStoreSpec` derivado não é `{AndroidKeyStore, PKCS12}`, e sim os **cinco**
>   tipos que o Android publica no API 30, incluindo `BKS`, `BouncyCastle` e
>   `AndroidCAStore`. O `SSLContextSpec` não apenas passa a aceitar `"TLS"`: aceita
>   os **sete** protocolos disponíveis, e o `SSLv3` cai sozinho porque sua janela
>   `1025` fecha antes do 26.
> - **O viés inverte de direção, e não só no `SSLContext`.** O perfil `android`
>   modela disponibilidade, não recomendação: o `MessageDigest` derivado admite
>   `MD5` e `SHA-1`, e o `Signature` admite `MD5withRSA`. Onde o `jca` produzia
>   falsos positivos, o `jca_android` troca parte deles por **falsos negativos**.
>   Queda no número de violações medidas **não** é evidência de código melhor.
> - **L1.5 continua aberto.** O `CipherSpec.mop` não carrega allow-list — delega a
>   `isValid()` em `rvsec-core/.../CipherTransformationUtil.java`, código Java
>   compartilhado com o conjunto `jca`. Adaptar as transformações do Cipher para
>   Android exigiria mexer nesse código e invalidar tudo que já foi medido com o
>   `jca`, ou criar um utilitário paralelo. É a maior lacuna da derivação e o
>   primeiro alvo de uma change seguinte.
>
> Mapa de tiers, tabela de rastreabilidade, ameaças à validade e os seis defeitos
> das regras derivadas (adotados como estão, por decisão, e documentados):
> **`docs/20260806_metacrysl_tier_map.md`**.

### 9.1 Estrutura

Diretório irmão `rvsec/rvsec-mop/src/main/resources/jca_android`, **fork apenas dos `.mop`** — nunca do `.aj` (L3.7: um `cp -r` copiaria um resíduo obsoleto com o defeito L2.7 dentro).

### 9.2 O que muda, por origem

**Correções P (re-derivação Android)** — `KeyStoreSpec` → `{AndroidKeyStore, PKCS12}`; `SSLContextSpec` → aceitar `"TLS"` e deslocar o predicado para `setEnabledProtocols`; TMF/KMF → `{PKIX}` com resolução de alias; `SecureRandomSpec` → `{SHA1PRNG}` + FORBIDDEN do provider `Crypto`; `ECGenParameterSpec` → curvas do Conscrypt, sem brainpool; suites TLS → as 4 ECDHE-GCM + ChaCha20.

**Alinhamento à `1.5.2` onde divergimos sem querer** — a tradução de 2022 introduziu aliases e frouxidões que não estão no upstream (`MessageDigestSpec` aceita `SHA256`/`SHA384`/`SHA512`; `KeyGeneratorSpec`/`MacSpec`/`SecretKeySpecSpec` aceitam `HMAC-SHA256`, `HMAC/SHA256`; `MacSpec` aceita `PBEWITHHMACSHA`). Cada um precisa de veredito: é adaptação legítima a nomes de provider Android (fica) ou é frouxidão acidental (sai)?

**Desvios deliberados do upstream, a documentar e reportar** — três defeitos estão presentes **tanto na 1.5.2 quanto na 3.1.5**, e o `jca_android` deve se afastar deles com justificativa escrita:
- `Cipher.crysl:107-110` — a lista OAEP aceita `OAEPWithMD5AndMGF1Padding` e **omite** `OAEPWithSHA-1AndMGF1Padding`, que o JDK obriga toda implementação a suportar e o Android oferece desde a API 10. Inverte a ordem de força. (Não é defeito da nossa tradução — é fiel ao upstream.)
- `Cipher.crysl:107` — `NoPadding` e `PKCS1Padding` aceitos para RSA (RSA textbook e Bleichenbacher).
- `Cipher.crysl:140-141` — o `REQUIRES` de OAEP compara `mode(transformation)` com nomes de **padding**; nunca dispara.

**Constraints dependentes de API level — sem condicionamento (D5)** — `SecretKeyFactory` (SHA-2 só 26+; `PBKDF2withHmacSHA1` banido pela regra e é o único universal em 10–25), família PBE do `Cipher`/`Mac`, `TLSv1.3` (29+), `GCM` IV de 12 bytes (31+). **Decisão: a regra vale para todos, sem exceção por `minSdk`.** O contexto de plataforma fica na leitura qualitativa dos resultados.

> Registro do porquê: a spec não teria como condicionar sozinha. Um `.mop` roda dentro do app, sem `Context` e sem acesso ao manifesto; o único dado disponível é `android.os.Build.VERSION.SDK_INT`, que é o API level do **dispositivo** (fixo no emulador), não o `minSdk` do app. Condicionar exigiria pós-processamento ou variantes de conjunto — ambos descartados.

**Correções de camada 2** — L2.1 a L2.12 e a **reconexão do grafo de predicados**: fazer `Cipher.init(int, Key, AlgorithmParameterSpec)` consumir `PREPARED_IV`/`PREPARED_GCM`, corrigir `GENERATED_PRIVATE_KEY`, e fazer chaves de `AndroidKeyStore`/`KeyGenParameterSpec` carregarem `GENERATED_KEY`.

**Correções internas ao próprio CrySL 3.1.5**, a reportar upstream: o `REQUIRES` de OAEP compara `mode(transformation)` com nomes de *padding* (nunca dispara); `KeyAgreement.GenSecretBuffer` referencia `g2` (=`getInstance`) onde provavelmente queria `gs2`; e o readmissão de CBC via `PBEWithHmacSHA*AndAES_*` (§6.3).

### 9.3 Resolução de nomes de algoritmo — camada transversal

Hoje cada spec compara strings do seu jeito, e nove classes de defeito decorrem disso. Esta é a única peça do `jca_android` que **todas** as specs consomem, e por isso é a primeira a ser escrita.

**Os casos a cobrir:**

| # | Caso | Evidência |
|---|---|---|
| 1 | **Case** — nomes de algoritmo são case-insensitive por especificação Oracle | `SHA256WITHRSA` acusado contra `SHA256withRSA` (4 eventos) |
| 2 | **`toUpperCase()` sensível a locale** — 8 specs normalizam **sem `Locale.ROOT`** | em locale turco, `"pkix".toUpperCase()` → `"PKİX"` ≠ `"PKIX"`. Falso positivo silencioso e não reprodutível |
| 3 | **Aliases de provider** | `SHA1`/`SHA`→`SHA-1`; `SHA256`→`SHA-256`; `X509`→`PKIX`; `PKCS7Padding`→`PKCS5Padding`; `DIFFIEHELLMAN`→`DH` |
| 4 | **Alias de transformação inteira** | `PBEWithHmacSHA256AndAES_128` → `AES_128/CBC/PKCS5PADDING` (Conscrypt) |
| 5 | **OIDs como nome** | `1.2.840.10045.3.1.7` = `secp256r1` = `prime256v1`; JCA aceita `OID.<oid>` e `<oid>` |
| 6 | **Grafia não canônica** | `OAEPwithSHA-256andMGF1Padding` (doc do Google) vs `OAEPWithSHA-256AndMGF1Padding` |
| 7 | **Transformação sem modo/padding** | `Cipher.getInstance("AES")` — hoje `isValid` devolve `false` com mensagem confusa; o diagnóstico correto é **ECB implícito** |
| 8 | **Nome do provider** | case-**sensitive**, ao contrário do algoritmo; e as sobrecargas `(String,Provider)`/`(String,String)` não são hookadas (L3.8) |
| 9 | **Protocolos TLS** | `TLS`/`SSL`/`Default` → default da plataforma; `TLSv1.2` fixo |
| 10 | **Espaços e separadores** | espaço à direita, `AES_128/CBC/PKCS5Padding` |

**Desenho proposto: resolver pelo registro de providers, não por tabela.**

`Provider.getService(String type, String algorithm)` é, por javadoc, *"the **case insensitive** algorithm name (or alternate alias)"*, e `Service.getAlgorithm()` devolve o nome canônico. Um resolvedor que varre `Security.getProviders()` na ordem de preferência canoniza **exatamente como o `getInstance` do app canoniza** — no dispositivo em que o app roda, com os providers que o app de fato tem, incluindo os que ele mesmo registrou (SpongyCastle, BC empacotado). Nenhuma tabela nossa acompanharia isso.

Contrato:

```
canon(type, name) -> nome canônico do serviço, ou null se nenhum provider o oferece
canonTransformation(t) -> (alg, mode, pad) canônicos
   1. tenta resolver `t` inteira como serviço Cipher   (pega o caso 4)
   2. senão, parseia alg[/mode/pad] e resolve `alg`     (pega os casos 3, 5, 6)
   3. mode/pad ausentes => marca "default do provider"  (pega o caso 7)
```

Notas de implementação, todas relevantes:
- **Cache estático**, construído uma vez. O resolvedor está no caminho quente do monitor.
- **`Locale.ROOT` obrigatório** em qualquer `toUpperCase`/`toLowerCase` remanescente (caso 2).
- **Não resolver nome de provider** — é case-sensitive; comparar literal.
- `null` para nome desconhecido é informação útil, não erro: significa que nenhum provider do dispositivo oferece aquilo, e o `getInstance` do app teria lançado `NoSuchAlgorithmException`. Distinguir isso de "vazio" separa achado genuíno de artefato de instrumentação (L3.1/L3.2).
- **Onde mora:** é mecânica de plataforma, não política. Fica em `rvsec-core`, compartilhado. Isso não conflita com mover a *política* de cifra para dentro do `.mop` (§11, L3.4) — a divisão é: **política no `.mop`, resolução de nome no core**.
- **Efeito nas contagens:** consolida os 2.340 eventos de SHA-1 hoje fragmentados em três linhas (`SHA-1`/`SHA1`/`SHA`) numa só, e elimina os 643 eventos de `X509` ao resolvê-lo para `PKIX`. Ambos são **redução**.

### 9.4 Specs a criar

Ordenadas por retorno, à luz da §8:

1. **`SecretKeyFactorySpec`** — PBKDF2. Lacuna medida, independe da versão do CrySL. Regra CrySL existe.
2. **Verificação do argumento `provider`** — sinalizar `"BC"` e `"Crypto"`, exigir `"AndroidKeyStore"` quando o keystore da plataforma for usado. A doc do Google é normativa aqui. Baixo custo: é `call(...)` sobre `getInstance(String,String)`. A CrySL descarta esse argumento com wildcard.
3. **`KeyGenParameterSpec.Builder` / `KeyProtection.Builder`** (API 23+) — `blockModes in {"GCM"}`, `encryptionPaddings in {"NoPadding"}`, `digests in {SHA-2}`, `keySize in {256}`. Além de detectar configuração fraca, **é o que reconecta `GENERATED_KEY` para chaves do keystore da plataforma**.
4. **StrongBox / `KeyInfo.getSecurityLevel()`** — `setIsStrongBoxBacked` (28+); `isInsideSecureHardware()` deprecado em 31, "superseded by getSecurityLevel".
5. **`SSLParameters` / `SSLEngine`** — hoje perdemos toda a checagem de `setEnabledProtocols` e de cipher suites. É também o consumidor do predicado deslocado em §6.4.
6. **Trust-all `TrustManager` / `HostnameVerifier` / WebView `onReceivedSslError`** — CWE-295, campanha nº 1 da Google Play ASI. A doc do `WebViewClient` é literalmente normativa: *"the host application should always call `SslErrorHandler#cancel()` and never proceed past errors"*. **Bloqueado por trabalho no weaver** (§4.1): exige implementar `ExecutionPC` com assinatura real e, sobretudo, o binding de `this`/parâmetros aos registradores de entrada. Não é uma spec — é uma extensão do `pointcut-engine`, e deve ser orçada como tal.

Ficam **fora**, com justificativa: PKI (`PKIXParameters`, `CertificateFactory`, `TrustAnchor`), `Cookie` (servlet), digest streams, `HMACParameterSpec` (`javax.xml.crypto` inexistente no Android).

---

## 10. Fase 3 — encanamento de seleção

| Sítio | O que é hoje |
|---|---|
| `rv-experiment/config.py:671-693` | `if/elif` fechado: `jca`, `generic`, `custom` |
| `rv-experiment/constants.py:91-94` | `SPEC_SET_JCA/GENERIC/CUSTOM` |
| `rv-static-analysis/config.py:199-208` | default hardcoded `.../resources/jca` — **e nunca sobrescrito** (L3.6) |
| `scripts/validation/fase_a_preprocess.py:353` | `choices=["jca","generic"]` |
| `rvsec-agent/pom.xml:106` | `pathToMopFiles` fixo em `.../resources/jca` |
| 9 `docker-compose*.yml` | `RV_SPEC_SET: "jca"` |
| `openspec/specs/experiment/spec.md:87,142,183,502`; `instrumentation/spec.md:273,619` | INV-EXP-03(f), INV-INS-09 — **normativas: exige delta spec** |
| `tests/test_config_validation.py:94-119`, `test_config_jit.py:68-159` | fixam a allow-list |
| `grammar-tests/.../DemandCounter.java:44-54` | `enum Corpus { ASPECT, JCA, GENERIC, GENERIC_NEW }` |
| default do CLI + `README.md:355` + `rv-experiment/README.md:266` | documentam `ajc`, que **nenhuma campanha usou** (§4) |

Nota: `generic_new` **não é alcançável** pelo mapeamento atual — defeito já existente.

**Invariantes a documentar:**

- **Um spec set por APK, nunca dois.** `MultiSpec_<n>` vem de contagem de arquivos no `outputDir` (`JavaMOPMain.java:171-181`) e `DexWeaver.monitorOwnerFor` faz fallback literal para `"MultiSpec_1"` (`:938-945`).
- **O nome da spec é literal repetido em cada `addError`.** Se o `jca_android` mantiver os literais, os resultados dos dois sets ficam indistinguíveis a jusante. Recomendação: **carimbar o spec set na saída** (coluna nova no `ErrorCollector`) em vez de renomear as specs — preserva comparabilidade par a par.
- Corrigir L3.7 **antes** do fork.

---

## 11. Fase 4 — camada 3

- **L3.1/L3.2** — resolvida em F0; a correção (fundir advices que compartilham assinatura de callee, ou falhar ruidosamente) é consequência.
- **L3.4 — `CipherTransformationUtil`**: único caso em que a política vive em Java. Duas saídas: parametrizar por spec set, ou **mover a política para dentro do `.mop`** como as outras 22 specs já fazem. Recomendo a segunda — torna o `jca_android` autocontido e elimina uma assimetria sem razão.
- **L3.3** — incluir `expecting` em `equals`/`hashCode`. **Aumenta** contagens.
- **L3.5** — reativar o escape do CSV.
- **L3.8** — cobrir `(String,Provider)` e `MessageDigest.clone()`.
- **L3.6** — passar `mop_dir` ao GATOR. **Pré-requisito**: sem isso o funil de seleção continua medindo a superfície do `jca`.
- **Novo:** alinhar o default do CLI a `dexlib2` (§4).

---

## 12. Impacto no artigo e na tese

**12.1 O fato que destrava.** Se as specs mudarem e o experimento for re-executado, **todo número muda e o funil rebuilda desde 342 apps** — a alcançabilidade estática usa os métodos referenciados nas declarações de evento das specs, então mudar as specs muda quais apps entram no dataset.

Mas os cenários de correção A–D **não movem `\uniqueMisusesMOP` = 454**: todo sítio que emite erro de KeyStore/TLS/valor-vazio também emite `InvalidSequenceOfMethodCalls`, então a chave `(apk, class, method, spec)` não muda. Só cenários que removem specs inteiras o movem (454 → 323).

**12.2 O que muda sem re-run.** `discussion.tex:77` (Construct Validity) precisa nomear a herança Java SE das allow-lists como ameaça específica. `results-rq1.tex:73` cita a violação de `KeyStoreSpec` no biometric-unlock do `password_manager` como misuse genuíno — o único valor observado é `found AndroidKeyStore`; a alegação de complementaridade sobrevive, a caracterização como misuse não. E o artigo nunca menciona que **13 das 23 specs nunca disparam**, das quais só uma é explicada.

**12.3 Ameaça nova, da §8.1.** O baseline CogniCrypt usa ruleset de 2022-09-29 sem versão declarada, que aceita `AES/CBC/PKCS5Padding` e RSA-2048. Isso precisa ir para as ameaças **independentemente** do que decidirmos sobre as specs, porque afeta a interpretação do Venn como está publicado.

**12.4 A oportunidade.** Não há mapeamento prévio de propriedades de RV para CWE na literatura, e o MASTG tem buracos reais de cobertura Android (weak hashing sem teste Android; weak KDF/PBE sem teste em plataforma alguma; IV estático em `placeholder`; uso de keystore sem teste dedicado). Um spec set JavaMOP calibrado para Android e ancorado em MASWE/CWE **preenche lacuna do próprio OWASP**.

**12.5 Tese.** Declara escopo "Java **and Android**" desde a introdução (`tex/1_Introducao.tex:86`) e afirma que as mesmas specs alimentam os dois caminhos (`tex/3_Implementacao.tex:42`), **sem nenhuma menção a adaptação ou a provedores distintos**. Este plano preenche esse silêncio. As ameaças W3 (tradução manual sem prova de equivalência) e B10 (viés dos benchmarks) estão em ledger mas **ausentes** de `tex/4_EstudoDeCaso.tex:759-790`, e ganham aqui evidência concreta.

---

## 13. Sequenciamento

```
F0  reprodução (G0 + viabilidade execution())        ── bloqueante
 │
F1  APK de conformidade                              ── instrumento de F0; artefato de replicação
 │
 ├─ F1b varredura estática de constantes string      ── barata, responde §8.2 sem re-run
 │
 ├─ F4  camada 3 (core/weaver/logger)                ── L3.6 é pré-requisito de F3
 │
F2  jca_android (.mop + tabela de política I/P/R)
 │
F3  encanamento de seleção + deltas OpenSpec
 │
F5  specs novas (SecretKeyFactory, provider, KeyGenParameterSpec, SSLParameters)
 │
F6  execution() real no pointcut-engine              ── pré-requisito de F7
 │
F7  trust-all / hostname / WebView
```

`F0.4'` (gate de PCD) entra junto de F1 — é barato e evita que qualquer spec nova de F2/F5 seja tecida errada em silêncio.

---

## 14. Decisões pendentes

**Decididas:**

- **D1 — Destino do `jca`.** ✔ Corrigir também no lado Java. A camada 2 é corrigida nos dois conjuntos; só a camada 1 diverge. Consequência a registrar: a reprodução exata dos números publicados deixa de valer, e isso precisa constar no pacote de replicação.
- **D2 — Seleção.** ✔ `--specification-set custom` como protótipo durante F1/F2; promover a primeira classe quando as constraints estabilizarem.
- **D4 — Artigo.** ✔ Não tocar agora. Fechar as 4 changes OpenSpec abertas e submeter; a auditoria e o `jca_android` são trabalho seguinte. **Ressalva a registrar:** a §12 nova do dossiê aponta que `CWE-573` responde por 76,5% dos eventos que carregam CWE e é a única atribuição sem fonte publicada — se o mapeamento CWE for usado em qualquer texto, isso precisa ser dito.

- **D3 — Release do CrySL.** ✔ Manter os dois lados na `1.5.2-jca` (2023-08-14). A migração para a `3.1.5-jca` é trabalho posterior e, quando ocorrer, tem de ocorrer **nos dois lados** para o Venn não comparar releases diferentes.
- **D5 — Condicionamento por API level.** ✔ Não condicionar. Regra estrita para todos; o contexto de plataforma fica na leitura qualitativa. (E fica registrado que a spec não teria como condicionar sozinha — §9.2.)
- **D6 — Metade B do delta 3.1.5.** ✔ Não absorver. Ancoragem uniforme na `1.5.2`; os defeitos da camada 2 são corrigidos como decisão nossa, com proveniência própria.

**Consequências combinadas das seis decisões:**

1. O `jca_android` tem **uma** release de referência (`1.5.2-jca`) e **uma** lista de desvios deliberados nossos — proveniência auditável em uma linha.
2. O escopo do conjunto é: **codificação Android (camada 1) + defeitos de autoria (camada 2) + resolução de nomes (§9.3) + specs ausentes (§9.4)**. Nenhuma mudança de julgamento criptográfico.
3. O Venn com o CogniCrypt permanece simétrico em política e em modelagem — nenhuma ameaça nova de comparação assimétrica.
4. `RSA-2048`, `AES/CBC/PKCS5Padding` e `PBEWithHmacSHA*` no `Mac` **continuam aceitos**, por decisão explícita e não por omissão.
5. O artigo não é tocado; a auditoria e o conjunto são trabalho seguinte.
6. Prototipagem via `--specification-set custom`; promoção a primeira classe quando as constraints estabilizarem.

**Ainda em aberto (não são decisões de política):**

- Veredito caso a caso sobre os aliases que a tradução de 2022 acrescentou fora do upstream (§9.2) — adaptação legítima a nomes de provider Android, ou frouxidão acidental?
- Se os desvios deliberados do upstream (OAEP com MD5 e sem SHA-1; `NoPadding`/`PKCS1Padding` para RSA; o `REQUIRES` de OAEP que nunca dispara) entram já ou ficam para depois — são defeitos presentes nas duas releases, logo corrigi-los é desviar do upstream conscientemente.

---

## 15. Riscos e o que não fazer

- **Não forkar antes de F0.** Um `jca_android` construído sobre a hipótese errada da G0 conserta o que não estava quebrado.
- **Não copiar o `.aj`** (L3.7).
- **Não prometer ganho de detecção com o 3.1.5.** A §8 mede ≈ 0–23 de 311. A justificativa é correção e defensabilidade.
- **Não tentar detectar credencial hardcoded em runtime** (§1.1) — mas **registrar** que o CrySL a expressa e o CogniCrypt achou 17, porque isso é evidência de complementaridade, não lacuna nossa.
- **Não publicar as alegações-manchete da auditoria** (59% / 73,7% / 2-de-454) antes de F0.
- **Não confundir as duas causas:** ~36,5% dos eventos são atribuídos a artefato de instrumentação, que specs Android não corrigem. Só o harness de F1 separa.
- **Não usar `results/*/experiment_config.json` como fonte da variante de instrumentação** (§4) — vários gravam `ajc` inerte junto de `instrument_apks: false`.
- **Não escrever spec nova com PCD fora de `{call, staticinitialization, args, target, if, !within}`** antes do gate F0.4' (§4.1). Sete PCDs são aceitos pelo parser e viram match-true silencioso; a instrumentação sai errada sem erro nem aviso, e revisão de código não pega.

---

## Fontes

- `ase-journal/docs/20260806_owasp_cwe_mapping_report.md` (1.129 linhas) + `_dictionary.md` + `_mapping.csv`
- `ase-journal/dataset/` — `cc.csv` (1.353), `cc_rv_mapping.csv`, `results/errors.csv` (97.018), `dataset.csv`
- `rv-android/docs/20260601_jca_spec_bugs_relatorio.md` (parcialmente superado)
- `rvsec/rvsec-mop/src/main/resources/jca/*.mop` — 23 specs, 116 pointcuts, **todos `call(...)`**
- `rvsec/rvsec-core/`, `rvsec-logger-logcat/`, `rvsec-android/rvsec-instrumentation-dexlib2/`
- `/home/pedro/tmp/Crypto-API-Rules` — tag `3.1.5-jca`, 2026-08-03, 51 regras JCA
- `rvsec-cognicrypt/CrySL-Rules/` — ruleset da campanha, 2022-09-29, 49 regras
- `developer.android.com/reference` (tabelas "Supported algorithms"), Conscrypt `OpenSSLProvider.java`, AOSP BouncyCastle
- `doutorado-tese/tex/3_Implementacao.tex:141-268`, `tex/4_EstudoDeCaso.tex:65-70,759-790`; `rvsec-paper/rvsec.tex:28-166` (comentado)
- `ase-journal/` — `settings.tex`, `results-rq1..rq3.tex`, `discussion.tex`, `constants.tex`, `dexlib2-primer.tex`
