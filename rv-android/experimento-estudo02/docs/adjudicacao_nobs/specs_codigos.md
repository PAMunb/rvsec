# Folha de referência por código NOBS — conjunto `jca_android` (grupo A0)

Caminhos abreviados usados abaixo:

- `mop/` = `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/`
- `store` = `…/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`
- `crysl/` = `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/RVSec-replication-package/tools/rules/`
- `gh99` = `…/rv-android/results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java`
- `matcher` = `…/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java`

Todas as linhas de `.mop` foram lidas nos arquivos atuais; os `file_line` de `codes.csv` conferem com o
`addError` de cada código.

---

## 0. Semântica comum (vale para todas as seções)

### 0.1 O que o store responde

- `validate(p, obj, vals…)`: `NOT_OBSERVED` se `obj == null` (`store:343-345`) ou se não há entrada
  `(identidade de obj, p)` (`store:347-349`) ou se a entrada tem conjunto de tuplas vazio (`store:356-357`);
  `VIOLATED` se foi negada ou se há tuplas mas nenhuma igual (`store:353-361`). Logo, **NOBS = nenhum
  `ensure(p, <este objeto>)` jamais executou**; um `ensure` com valores diferentes dá `VIOLATED`
  (código `CONSTR`), não NOBS.
- `validateAny(p, obj)`: `SATISFIED` com qualquer tupla (`store:395-412`).
- `ensure` com `bound == null` é no-op (`store:292-294`): um campo `spec`/`sr` não vinculado não credita nada.
- Chave por identidade (`store:222-251`): cópia (`clone`, `Arrays.copyOf*`, `System.arraycopy` para array
  novo, `ByteBuffer`, Base64/hex ida-e-volta) não herda predicado.

### 0.2 Ordem de execução no monitor gerado (JavaMOP/RV-Monitor)

Confirmado no monitor `gh99` (gerador idêntico; **o conjunto de specs de onde ele foi gerado é
anterior e diferente** — usa `ExecutionContext`, `TrustManagerFactorySpec.gtm1` com
`TrustManager[][]` e `setProperty(GENERATED_KEY_MANAGERS)`, lista de algoritmos só `PKIX` — portanto só
serve para a semântica do gerador, não para o conteúdo):

1. `condition(...)` falsa compila para `return false` **antes** do corpo e da transição
   (`gh99:8833-8837`, `:8854-8858`).
2. O corpo do evento executa **antes** da transição e independentemente do estado (`gh99:8896-8911`,
   `:8914-8927`), inclusive em monitor recém-criado no estado 0.
3. Todo evento faz *FindOrCreate*: sem monitor para o objeto, cria um no estado inicial
   (`gh99:16420-16432`, `:16453-16482`) — não há `creation event` no conjunto (só citado em comentário,
   `KeyPairSpec.mop:181-187`).
4. Depois da transição, o despachante chama `@fail` e em seguida `@match*` conforme a categoria do
   **novo** estado (`gh99:262-279`, `:16434-16440`). `__RESET` volta ao estado 0.

Consequências usadas abaixo: (a) um `ensure` **no corpo** do evento é incondicional em relação ao
autômato; (b) um `ensure` **em `@match`** exige que a sequência observada naquele objeto chegue ao estado
de aceitação — o que falha quando o nascimento do objeto não foi observado (monitor em `start`); (c) o
próprio conjunto registra as mesmas medições sobre o gerador atual (`SecureRandomSpec.mop:56-58`,
`KeyPairSpec.mop:112-114`, `SSLContextSpec.mop:88-92`, `CipherSpec.mop:76-78`).

### 0.3 Casamento de pointcut no weaver dexlib2

- Dono do método: **igualdade exata** com o `definingClass` do `invoke` quando o pointcut não usa `T+`
  (`matcher:316-343`); com `T+`, subtipos (`matcher:333-341`). Só `SecretKey+.getEncoded()`
  (`SecretKeySpec.mop:120`) e `Key+.getEncoded()` (`KeySpec.mop:76`) usam `+`. Assim
  `Random r = new SecureRandom(); r.nextBytes(b)` (dono `java/util/Random`) ou um receptor tipado como
  subclasse de `SecureRandom` **não** casam `SecureRandom.nextBytes(byte[])`.
- `after … returning` não executa se a chamada lança (e o dexlib2 também pula `after` simples, ver
  BRIEFING).
- Exclusões do aspecto e framework não observado: ver BRIEFING.

---

## 1. Índice de produtores por Property (referenciado pelas seções)

### P-RANDOMIZED — `SecureRandomSpec.mop`

| Onde | Evento / pointcut | Objeto | Gate |
|---|---|---|---|
| `@match1` `:383-385` | ao entrar no estado `init` (alias `:365`) vindo de `c1` `new SecureRandom()` `:67-70`, `c2` `new SecureRandom(byte[])` `:95-108`, `g1` `getInstance(String)` `:113-118`, `g2` `getInstance(String, ..)` com `args(alg,*)` `:122-127`, `g3` `getInstance Strong()` `:130-133` | o próprio `SecureRandom` (`sr`) | automático na criação observada; `g1`/`g2` só com algoritmo ∈ {SHA1PRNG, Windows-PRNG, NativePRNG, NativePRNGBlocking, NativePRNGNonBlocking, PKCS11} via `ConscryptAliasTable` (`:40-41`, `:116`, `:125`). `g4`/`g5` (algoritmo rejeitado) ficam em `start` e não vinculam `sr` (`:145-169`, `:336-337`) → **nenhum crédito**. `c2` credita mesmo com semente NOBS (sem gate). |
| `@match2` `:392-401` | `genSeed` `byte[] generateSeed(int)` `:247-251` (after returning) | array retornado | estado novo ∈ `end` (alias `:368`), isto é, só a partir de `init`/`end` (`:339-361`) |
| `@match2` `:392-401` | `next2` **before** `void SecureRandom.nextBytes(byte[])` `:289-294` | o array argumento | idem; se o monitor do `SecureRandom` está em `start` (criação não observada: framework, pacote excluído, `g4/g5`), a transição vai a `fail`, `@fail` descarta o staged (`:370-376`) e emite `SECURERANDOM-ORDER-00` **no mesmo local** do `nextBytes`. Dono exato `SecureRandom` (§0.3). |

Não produzem: `nextInt`/`ints` (`:253-311`), `setSeed` (`:200-239`), `java.util.Random`,
`ThreadLocalRandom`, `Cipher.getIV()`, `Cipher.getParameters()`, qualquer cópia.

### P-GENERATED_KEY (valores = algoritmo)

| Onde | Evento | Objeto / valores | Gate |
|---|---|---|---|
| `KeyGeneratorSpec.mop:213-228` `@match` | `gk1` `SecretKey KeyGenerator.generateKey()` `:164-173` | chave; `canonical("KeyGenerator", alg de getInstance)` | aceitação do `ere` `(g3* g1+ | g3* g2+) ((init|initRandom*) gk1 | gk1)` `:175`: exige `getInstance` observado com algoritmo ∈ {AES, HmacSHA256/384/512 e grafias} (`:42`, `:62`, `:69`); **um** `generateKey` por gerador; `init` no máximo uma vez. `KEYGENERATOR-NOBS-00..02` **não** bloqueiam. |
| `KeyStoreSpec.mop:194-206` `@match` | `gk1` `Key KeyStore.getKey(String, char[])` `:114-122` | chave; `key.getAlgorithm()` (+ `GENERATED_PRIVATE_KEY` se `PrivateKey`, `:201-203`) | aceitação do `ere` `(g2* (g1|g3) load (((ge1 gk1)|gk1)|(se1 store))*)+` `:124`: `getInstance` observado com tipo ∈ {JCEKS, JKS, DKS, PKCS11, PKCS12, AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle} (`:48-49`), `load(..)` observado, sem `getEntry` não seguido de `getKey`, sem `setEntry` sem `store`. |
| `SecretKeySpecSpec.mop:255-258` `@match` | `c1` `new SecretKeySpec(byte[], String)` `:97-125`; `c2` `new SecretKeySpec(byte[], int, int, String)` `:159-191` | o `SecretKeySpec`; o algoritmo do construtor (também escreve `SPECCED_KEY`, `:257`) | `spec` só é vinculado se algoritmo ∈ {AES, HMACSHA256/384/512 e grafias} **e** `validate(PREPARED_KEY_MATERIAL, keyMaterial) == SATISFIED` (`:105-124`, `:166-190`) |
| `SecretKeyFactorySpec.mop:92-110` corpo | `gen` `SecretKey generateSecret(KeySpec)` | chave; `canonical(alg de get)` (`:64`) | só se `validateAny(SPECCED_KEY, keySpec) == SATISFIED` (`:95-109`); corpo, logo independe do autômato; se `get` não foi observado, `algorithm == null` → leitores com valor respondem `VIOLATED` |
| `SecretKeyFactorySpec.mop:119-123` corpo | `translate` `translateKey(SecretKey)` | chave; algoritmo | incondicional |

Não produzem: `KeyStore.getEntry(...)` + `SecretKeyEntry.getSecretKey()`/`PrivateKeyEntry.getPrivateKey()`,
`Cipher.unwrap`, `KeyAgreement.generateSecret(String)` (proibido), chaves criadas no framework
(`KeyGenerator` chamado dentro de lib excluída), `KeyPairGenerator` (produz via P-PUB/PRIV).

### P-GENERATED_PUBLIC_KEY / P-GENERATED_PRIVATE_KEY

| Onde | Evento | Objeto | Gate |
|---|---|---|---|
| `KeyPairSpec.mop:123-127` corpo | `gpu` `PublicKey KeyPair.getPublic()` | chave pública retornada | **incondicional** (corpo; o `ere` `c1 (gpu|gpr)*` `:189` rejeita pares vindos de `generateKeyPair()`, mas o `ensure` já ocorreu, `:106-119`) |
| `KeyPairSpec.mop:143-147` corpo | `gpr` `PrivateKey KeyPair.getPrivate()` | chave privada retornada | incondicional |
| `KeyFactorySpec.mop:101-119` corpo | `genPublic` `PublicKey generatePublic(KeySpec)` | chave retornada | só se `validateAny(SPECCED_KEY, keySpec) == SATISFIED` (`:104-118`) |
| `KeyFactorySpec.mop:75-93` corpo | `genPrivate` `PrivateKey generatePrivate(KeySpec)` | chave retornada | idem (`:78-92`) |
| `KeyStoreSpec.mop:201-203` `@match` | `gk1` | `PrivateKey` retornada por `getKey` | aceitação do `ere` (ver P-GENERATED_KEY) |

Nenhum produtor de chave pública além de `getPublic` e `generatePublic`: `Certificate.getPublicKey()`,
`KeyStore.getCertificate(alias).getPublicKey()` e decodificação interna de BouncyCastle/Tink nunca
creditam. `KeyStore.crysl:62` (`generatedPubkey[key]`) não tem sítio, de propósito (`KeyStoreSpec.mop:190-193`).

### P-PREPARED_KEY_MATERIAL

| Onde | Evento | Objeto | Gate |
|---|---|---|---|
| `SecretKeySpec.mop:143-148` `@match` | `e1` `byte[] SecretKey+.getEncoded()` `:119-127` | array retornado | só se `validate(GENERATED_KEY, key, key.getAlgorithm()) == SATISFIED` (`:122-126`). `ere e1*` `:141`, aceita sempre. |
| `KeySpec.mop:103-108` `@match` | `ge1` `byte[] Key+.getEncoded()` `:75-85` | array retornado | só se a chave tem `GENERATED_KEY` com o próprio algoritmo **ou** `GENERATED_PUBLIC_KEY` **ou** `GENERATED_PRIVATE_KEY` (`:78-84`) |
| `KeyAgreementSpec.mop:294-300` corpo | `gs1` `byte[] generateSecret()` | array retornado | `if (conforms)`: o campo fica `false` por `KEYAGREEMENT-ALG-00` (`:84-88`), qualquer `CONSTR/NOBS-00..08` (`:106-273`) ou `FORB-00` (`:337-343`); `@fail` o repõe em `true` (`:381-386`) |
| `KeyAgreementSpec.mop:311-317` corpo | `gs2` `int generateSecret(byte[], int)` | array argumento | idem |

Não produzem: `SecureRandom.nextBytes` (é `RANDOMIZED`, predicado distinto; `SecretKeySpecSpec.mop:79-91`),
`MessageDigest.digest`, `Mac.doFinal`, HKDF, bytes de armazenamento/rede/constante, cópias de um array
creditado (`Arrays.copyOf(key.getEncoded(), 16)`).

### P-SPECCED_KEY

| Onde | Evento | Objeto / valores | Gate |
|---|---|---|---|
| `PBEKeySpecSpec.mop:159-161` corpo | `c1` `new PBEKeySpec(char[], byte[], int, int)` `:117-162` | o spec; `keyLength` | `iterationCount >= 10000` (`:121-125`) **e** `validate(RANDOMIZED, salt) == SATISFIED` (`:148-158`). Construtores `PBEKeySpec(char[])` e `(char[], byte[], int)` (`f1`/`f2`, `:48-60`) nunca escrevem. `clearPassword()` nega (`:183-187`) → leitor dá `VIOLATED`. |
| `SecretKeySpecSpec.mop:257` `@match` | `c1`/`c2` | o `SecretKeySpec` (aridade 1) | mesmo gate de P-GENERATED_KEY (algoritmo + material preparado) |
| `X509EncodedKeySpecSpec.mop:82-84` `@match` | `c1` `new X509EncodedKeySpec(byte[])` `:40-55` | o spec | `spec` só vinculado se `validate(PREPARED_KEY_MATERIAL, encodedKey) == SATISFIED` (`:43-54`) |

Sem produtor no conjunto (nem no oráculo): `PKCS8EncodedKeySpec`, `RSAPublicKeySpec`, `RSAPrivateKeySpec`,
`ECPublicKeySpec`, `ECPrivateKeySpec`, `DHPublicKeySpec`, `DESedeKeySpec`, `DESKeySpec`.

### P-GENERATED_KEY_STORE — `KeyStoreSpec.mop:195-198` `@match`

Objeto: o `KeyStore` alvo de `load(..)` (`:96-100`). Gate: chegar à aceitação por `g1|g3` (tipo na lista,
`:59-63`, `:90-94`) seguido de `load`. Tipo fora da lista (`g2`, `:65-69`) ou `getInstance` não observado
(`KeyStore.getInstance(File, …)`, criação no framework/pacote excluído) → `load` vai a `fail`
(`KEYSTORE-ORDER-00`) e nada é escrito. Uma vez escrito, persiste mesmo que o monitor falhe depois.

### P-GENERATED_TRUST_MANAGER (array) — `TrustManagerFactorySpec.mop:215-219` corpo

`gtm1` `after returning TrustManager[] getTrustManagers()` com `target(mf)`: `ensure` sobre o array
retornado, **incondicional** (corpo; §0.2). Não depende de `TRUSTMANAGERFACTORY-NOBS-00/01`, `-ALG-00`
nem de `-ORDER-00` (um segundo `getTrustManagers()` gera ORDER e ainda assim marca o novo array). O
`ensure` em `@match1` `:254-259` marca a **fábrica**, não o array, e não tem leitor.

### P-GENERATED_KEY_MANAGERS (array) — `KeyManagerFactorySpec.mop:173-177` corpo

Idêntico: `gkm1` `after returning KeyManager[] getKeyManagers()`, incondicional. `@match1` `:218-223`
marca a fábrica, sem leitor.

### P-PREPARED_IV — `IvParameterSpec.mop:152-154` `@match`

Objeto: o `IvParameterSpec`. `spec` só vinculado se `validate(RANDOMIZED, iv) == SATISFIED` em `c1`
(`:65-80`) ou, em `c2`, `SATISFIED` e `len > 0` e limites válidos (`:114-133`). `ere c1 | c2` sempre
aceita.

### P-PREPARED_GCM — `GCMParameterSpecSpec.mop:179-181` `@match`

Objeto: o `GCMParameterSpec`. `spec` só vinculado se `tagLen ∈ {96,104,112,120,128}` **e**
`validate(RANDOMIZED, src) == SATISFIED` (`:62-85`, `:116-139`).

---

## 2. Seções por código

### SSLCONTEXT-NOBS-00

1. **Emissor.** `SSLContextSpec.mop:214-217` `event init after(KeyManager[] kms, TrustManager[] tms,
   SecureRandom random, SSLContext ctx)`: `call(public void SSLContext.init(KeyManager[], TrustManager[],
   SecureRandom)) && args(kms, tms, random) && target(ctx)`. Leitura `:222`
   `validate(GENERATED_KEY_MANAGERS, kms)` (objeto = **1º argumento**, sem valores); NOBS em `:227-230`.
   Sem condição; roda em qualquer estado do autômato; `null` é lido de propósito (`:204-208`).
2. **Produtor.** P-GENERATED_KEY_MANAGERS (`KeyManagerFactorySpec.mop:173-177`), incondicional.
3. **Proveniência aceitável.** `kmf.getKeyManagers()` chamado em código tecido e **o mesmo array**
   passado a `init`. **Nunca satisfaz:** `init(null, …)` (cliente TLS sem certificado de cliente — o caso
   comum; `LEGIT_UNOBSERVABLE`/decisão do pesquisador), array reconstruído (`arrayOf(km)`,
   `new KeyManager[]{…}`), cópia, `KeyManager` próprio, array obtido dentro do framework ou de pacote
   excluído.
4. **Cascata.** Nenhuma aresta de entrada vinda de códigos NOBS: `KEYMANAGERFACTORY-NOBS-00/01`,
   `-ALG-00` e `-ORDER-00` **não** suprimem o `ensure` do array.
5. **CrySL.** `crysl/SSLContext.crysl:32` `generatedKeyManagers[km]`, produtor
   `crysl/KeyManagerFactory.crysl:36`. Equivalente; o conjunto não isenta `null` e o oráculo também não.

### SSLCONTEXT-NOBS-01

1. **Emissor.** Mesmo evento `init` (`SSLContextSpec.mop:214-217`). Leitura `:231`
   `validate(GENERATED_TRUST_MANAGER, tms)` (objeto = **2º argumento**); NOBS em `:236-239`.
2. **Produtor.** P-GENERATED_TRUST_MANAGER (`TrustManagerFactorySpec.mop:215-219`), incondicional.
3. **Proveniência aceitável.** `tmf.getTrustManagers()` em código tecido, mesmo array direto em `init`.
   **Nunca satisfaz:** `init(km, null, …)` (trust store padrão), `arrayOf(x509TrustManager)` /
   `new TrustManager[]{tm}` (padrão do okhttp e de wrappers de *pinning*: o `X509TrustManager` pode vir de
   `getTrustManagers()[0]`, mas o array novo não carrega nada), gerenciador de confiança próprio (inclusive
   *trust-all*: aqui NOBS não distingue MISUSE de LEGIT — é preciso ler o `TrustManager`), array vindo de
   framework.
4. **Cascata.** **Não há** aresta `TRUSTMANAGERFACTORY-NOBS-00 → SSLCONTEXT-NOBS-01`: uma fábrica cujo
   `init((KeyStore) null)` foi NOBS ainda marca o array em `gtm1`. A única raiz é o array não ser o
   retornado por um `getTrustManagers()` observado.
5. **CrySL.** `crysl/SSLContext.crysl:33` / `crysl/TrustManagerFactory.crysl:33`. Equivalente (a
   constante do conjunto é `GENERATED_TRUST_MANAGER`, singular, escrita sobre o array; `Property.java`
   documenta).

### SSLCONTEXT-NOBS-02

1. **Emissor.** Mesmo evento `init`. Leitura `SSLContextSpec.mop:240` `validate(RANDOMIZED, random)`
   (objeto = **3º argumento**); NOBS em `:245-248`. `null` lido de propósito (`:176-185`).
2. **Produtor.** P-RANDOMIZED, linha `@match1` (`SecureRandomSpec.mop:383-385`) sobre o próprio gerador.
3. **Proveniência aceitável.** `new SecureRandom()`, `new SecureRandom(seed)`,
   `SecureRandom.getInstance(alg∈lista[, prov])` ou `getInstanceStrong()` executados em código tecido, e
   esse objeto passado a `init`. **Nunca satisfaz:** `init(km, tm, null)` (o idioma documentado para o
   gerador da plataforma; comentário do próprio arquivo diz que todo o corpus cai aqui), `SecureRandom`
   criado dentro de lib excluída/framework, `getInstance` com algoritmo fora da lista.
4. **Cascata.** `SECURERANDOM-ALG-00/01` (sobre o mesmo objeto) → sem `RANDOMIZED` → este NOBS.
   `SECURERANDOM-NOBS-00/01` não cascateiam (`c2` e `setSeed2` não bloqueiam `@match1`).
5. **CrySL.** `crysl/SSLContext.crysl:34` `randomized[random]`, produtor `crysl/SecureRandom.crysl:49`.
   Equivalente; a leitura de `null` é decisão registrada, não estreitamento.

### TRUSTMANAGERFACTORY-NOBS-00

1. **Emissor.** `TrustManagerFactorySpec.mop:118-121` `event init before(Object arg, TrustManagerFactory mf)`:
   `(call(void TrustManagerFactory.init(KeyStore)) || call(void TrustManagerFactory.init(ManagerFactoryParameters)))
   && args(arg) && target(mf)`. Ramo `if (arg == null || arg instanceof KeyStore)` `:146`, leitura `:147`
   `validate(GENERATED_KEY_STORE, arg)`; NOBS `:152-155`. Um `ManagerFactoryParameters` vai ao ramo
   `:161` (código `-NOBS-01`, fora deste censo).
2. **Produtor.** P-GENERATED_KEY_STORE (`KeyStoreSpec.mop:195-198`, `@match` após `g1|g3 load`).
3. **Proveniência aceitável.** `KeyStore.getInstance(tipo∈lista[, prov])` + `ks.load(…)` (qualquer
   sobrecarga, inclusive `load(null)`/`load(null, null)`) em código tecido, depois `tmf.init(ks)`. Cobre
   `AndroidCAStore`, `BKS`/`getDefaultType()`, `PKCS12`, e o padrão de *pinning*
   `load(null, null)` + `setCertificateEntry` (o `ensure` já ocorreu no `load`).
   **Nunca satisfaz:** `tmf.init((KeyStore) null)` (trust store padrão — `LEGIT_UNOBSERVABLE` por
   construção; `:102-112`), `KeyStore` criado/carregado no framework ou em pacote excluído,
   `KeyStore.getInstance(File, …)`, tipo fora da lista.
4. **Cascata.** Entrada: `KEYSTORE-ORDER-00` no `load` do mesmo objeto (nascimento não observado ou tipo
   rejeitado). Saída: **nenhuma** para `SSLCONTEXT-NOBS-01` (ver P-GENERATED_TRUST_MANAGER).
5. **CrySL.** `crysl/TrustManagerFactory.crysl:28` / `crysl/KeyStore.crysl:59`. Equivalente; a lista de
   tipos do conjunto é **mais larga** (tipos Android, `KeyStoreSpec.mop:43-49`).

### KEYMANAGERFACTORY-NOBS-00

1. **Emissor.** `KeyManagerFactorySpec.mop:113-116` `event init before(Object arg, KeyManagerFactory k)`:
   `(call(void init(KeyStore, char[])) || call(void init(ManagerFactoryParameters))) && args(arg, ..) &&
   target(k)`. Ramo `arg == null || arg instanceof KeyStore` `:121`, leitura `:122`
   `validate(GENERATED_KEY_STORE, arg)`; NOBS `:127-130`. Um `init((ManagerFactoryParameters) null)` também
   cai aqui (`:101-104`).
2. **Produtor.** P-GENERATED_KEY_STORE.
3. **Proveniência aceitável.** Idem à seção anterior (`getInstance` + `load` observados). **Nunca
   satisfaz:** `kmf.init(null, null)`, `KeyStore` de framework/pacote excluído (p.ex. obtido de
   `KeyChain`), tipo fora da lista. Na JVM, `init` com store não carregado lança (`:92-94`), então um
   store não-nulo que chega aqui foi carregado em algum lugar — NOBS indica nascimento/carga não
   observados.
4. **Cascata.** Entrada: `KEYSTORE-ORDER-00`. Saída: nenhuma para `SSLCONTEXT-NOBS-00`.
5. **CrySL.** `crysl/KeyManagerFactory.crysl:31`. Equivalente.

### CIPHER-NOBS-00

1. **Emissor.** `CipherSpec.mop:168-171` `event i2 before(int mode, Key key, Cipher c)`:
   `call(void Cipher.init(int, Key, ..)) && args(mode, key, ..) && target(c)` — todas as sobrecargas com
   `Key` e **todos os modos** (encrypt, decrypt, wrap, unwrap). Leitura composta `:199-225`:
   `validate(GENERATED_KEY, key, keyAlgorithm(c.getAlgorithm()))` e `validate(GENERATED_KEY, key,
   alg(c.getAlgorithm()))`, `validate(GENERATED_PUBLIC_KEY, key)`, `validate(GENERATED_PRIVATE_KEY, key)`.
   NOBS (`:230-233`) só quando **as quatro** respondem `NOT_OBSERVED` (qualquer `VIOLATED` vira
   `CIPHER-CONSTR-00`). `init(int, Certificate, …)` é `i1` e não lê chave.
2. **Produtores.** P-GENERATED_KEY (KeyGenerator, KeyStore, SecretKeySpec, SecretKeyFactory
   `gen`/`translate`) e P-GENERATED_PUBLIC_KEY / P-GENERATED_PRIVATE_KEY (KeyPair `gpu`/`gpr`, KeyFactory,
   KeyStore).
3. **Proveniências aceitáveis.**
   - `KeyGenerator.getInstance(alg∈lista[, prov]) [init] generateKey()` → `c.init(mode, key, …)`
     (inclusive `"AndroidKeyStore"` como provedor), uma chave por gerador.
   - `KeyStore.getInstance(tipo) → load(…) → [getEntry] getKey(alias, pw)` → `init`.
   - `new SecretKeySpec(bytes, alg∈lista)` com `bytes` = o array devolvido por `k.getEncoded()` de chave
     creditada, ou por `KeyAgreement.generateSecret()` conforme.
   - `SecretKeyFactory.generateSecret(pbeKeySpec)` com `PBEKeySpec` conforme (sal de `nextBytes`
     observado, ≥ 10 000 iterações) → `init` direto (PBE) ou re-embrulho via `getEncoded()` + `SecretKeySpec`.
   - `kpg.generateKeyPair().getPublic()/getPrivate()` → `init` (RSA/OAEP).
   - `KeyFactory.generatePublic/Private(X509EncodedKeySpec(bytes creditados))`.

   **Nunca satisfaz:** chave AES/HMAC com bytes de armazenamento, rede, keyset (Tink `AesGcmJce`,
   `AesCtrJceCipher` etc. fazem `new SecretKeySpec(keyValue, …)`), constante/`String.getBytes()`, hash de
   senha (`MessageDigest.digest`), HKDF/`Mac.doFinal`, `SecureRandom.nextBytes` direto (é `RANDOMIZED`,
   não `PREPARED_KEY_MATERIAL`), cópia (`Arrays.copyOf(k.getEncoded(), 16)`); chave de
   `KeyStore.getEntry(...)` → `SecretKeyEntry.getSecretKey()` / `PrivateKeyEntry.getPrivateKey()`
   (idioma dominante do AndroidKeyStore); `getCertificate(alias).getPublicKey()` e
   `Certificate.getPublicKey()`; chave de `Cipher.unwrap`; `SecretKeySpec` com algoritmo fora da lista
   (`"HmacSHA1"`, `"DESede"`, `"ChaCha20"`, uma transformação completa como `"AES/CBC/PKCS5Padding"`);
   segundo `generateKey()` do mesmo `KeyGenerator`; `KeyStore` cujo `getInstance`/`load` não foi observado
   ou cuja sequência quebrou (dois `getEntry` seguidos, `setEntry` sem `store`) antes do `getKey`;
   chave pública de `KeyFactory` com spec não creditado (`RSAPublicKeySpec`, `X509EncodedKeySpec` de bytes
   externos).
4. **Cascata (entradas).** `SECRETKEYSPEC-NOBS-00/01` (e `-ALG-00/01`) → sem `GENERATED_KEY` no spec;
   `SECRETKEYFACTORY-NOBS-00` (e `-CONSTR-00`) → sem `GENERATED_KEY` na chave derivada;
   `KEYFACTORY-NOBS-00/01` → sem PUB/PRIV; `KEYSTORE-ORDER-00` e `KEYGENERATOR-ORDER-00` (ou algoritmo
   rejeitado em `KeyGenerator`) → sem `GENERATED_KEY`. **Não** cascateiam: `KEYGENERATOR-NOBS-00..02`,
   `KEYPAIR-NOBS-00/01`, `KEYPAIR-ORDER-00`. Saída: `CIPHER-NOBS-00` não bloqueia nenhum `ensure` da
   `CipherSpec` (`initialisedCipher = c` incondicional, `:238`; `@match3` `CipherSpec.mop` fim do arquivo).
5. **CrySL.** `crysl/Cipher.crysl:134` exige só `generatedKey[key, alg(transformation)]`; o conjunto é
   **mais largo** (aceita também `generatedPubkey`/`generatedPrivkey`). Os caminhos "nunca" acima também
   não são creditados pelo oráculo (nenhuma regra dos 49 garante predicado para entry getters,
   `getPublicKey`, `unwrap`) — produtor ausente no conjunto **e** no oráculo.

### SECRETKEYSPEC-NOBS-00

1. **Emissor.** `SecretKeySpecSpec.mop:97-99` `event c1 after(byte[] keyMaterial, String keyAlgorithm)
   returning(SecretKeySpec secretKeySpec)`: `call(SecretKeySpec.new(byte[], String))`. Leitura `:110`
   `validate(PREPARED_KEY_MATERIAL, keyMaterial)` (objeto = **1º argumento**); NOBS `:116-120`. A leitura
   ocorre mesmo com algoritmo rejeitado (`:105-109` só zera `conforms`).
2. **Produtores.** P-PREPARED_KEY_MATERIAL: `SecretKeySpec.mop:143-148`, `KeySpec.mop:103-108` (ambos com
   gate de origem da chave) e `KeyAgreementSpec.mop:294-317` (gate `conforms`).
3. **Proveniências aceitáveis.** `new SecretKeySpec(k.getEncoded(), alg)` onde `k` tem origem creditada
   (KeyGenerator, KeyStore.getKey, SecretKeySpec conforme, SecretKeyFactory com spec conforme,
   KeyPair.getPublic/getPrivate, KeyFactory com spec conforme) **e** o algoritmo gravado bate com
   `k.getAlgorithm()` (senão `VIOLATED` silencioso no gate e nada é marcado); `new SecretKeySpec(ka.generateSecret(), alg)`
   com `KeyAgreement` conforme. **Nunca satisfaz:** bytes de `SecureRandom.nextBytes` (idioma comum de
   geração de chave — o oráculo exige `preparedKeyMaterial`, não `randomized`; `:79-91`), Base64/hex de
   armazenamento ou rede, keyset Tink, `MessageDigest.digest(senha)`, saída de HKDF/`Mac`,
   `Arrays.copyOf*` do `getEncoded()`, `generateSecret()` de `KeyAgreement` com qualquer NOBS/CONSTR
   (chave pública do par vinda de fora), `getEncoded()` de chave de origem não observada (entry getter,
   `unwrap`, framework).
4. **Cascata (entradas).** Via gate de origem (`KeySpec.mop:78-84`, `SecretKeySpec.mop:122-126`): todas as
   raízes de `CIPHER-NOBS-00` sobre a chave cujo `getEncoded()` foi lido — em especial
   `SECRETKEYFACTORY-NOBS-00` (derivação PBKDF2 com sal não creditado: cadeia
   `PBEKEYSPEC-NOBS-01 → SECRETKEYFACTORY-NOBS-00 → SECRETKEYSPEC-NOBS-00 → CIPHER-NOBS-00`) e
   `SECRETKEYSPEC-NOBS-00` anterior (re-embrulho de material já recusado). Via `conforms`:
   `KEYAGREEMENT-NOBS-00..08`, `-CONSTR-00..08`, `-ALG-00`, `-FORB-00`. Saídas: `CIPHER-NOBS-00`,
   `MAC-NOBS-00/01`, `SECRETKEYFACTORY-NOBS-00`, `KEYFACTORY-NOBS-00/01` (spec não recebe
   `GENERATED_KEY` nem `SPECCED_KEY`).
5. **CrySL.** `crysl/SecretKeySpec.crysl:23`; produtores `crysl/SecretKey.crysl:17`, `crysl/Key.crysl:14`,
   `crysl/KeyAgreement.crysl:51`. **Mais estreito que o oráculo:** `Key.crysl`/`SecretKey.crysl` não têm
   REQUIRES, mas o conjunto só marca o `getEncoded()` de chave com origem observada (divergência
   `MOP-MAIS-RESTRITIVO` registrada em `KeySpec.mop:66` e `SecretKeySpec.mop:61-67`) e compara o valor de
   algoritmo gravado com `getAlgorithm()`. Fonte potencial de SPEC_DEFECT quando a chave vem de uma
   origem correta porém não creditada.

### SECRETKEYSPEC-NOBS-01

1. **Emissor.** `SecretKeySpecSpec.mop:159-161` `event c2 after(byte[] keyMaterial, int offset, int len,
   String keyAlgorithm) returning(SecretKeySpec)`: `call(SecretKeySpec.new(byte[], int, int, String))`.
   Leitura `:176`, NOBS `:182-186`. Objeto = o **array inteiro** (o recorte `offset/len` não importa para a
   identidade).
2. **Produtores.** Iguais a `SECRETKEYSPEC-NOBS-00`.
3. **Proveniências.** Iguais; o caso típico é fatiar um buffer maior: `new SecretKeySpec(buf, 0, 16, "AES")`
   satisfaz se `buf` for **o mesmo** array de `getEncoded()`/`generateSecret()` creditado; nunca satisfaz
   se `buf` for `MessageDigest.digest(...)`, saída de HKDF, bytes decodificados ou lidos.
4. **Cascata.** Idem `-NOBS-00`.
5. **CrySL.** Idem (`crysl/SecretKeySpec.crysl:11,23`).

### IVCHAINJUNCTION-NOBS-00

1. **Emissor.** `IvChainJunction.mop:138-141` `event use before(int encmode, AlgorithmParameterSpec params,
   Cipher c)`: `call(void Cipher.init(int, Key, AlgorithmParameterSpec, ..)) && args(encmode, *, params, ..)
   && target(c)` (sobrecargas i4/i6; **não** `init(…, AlgorithmParameters, …)`). Condição no corpo
   `:155-159`: `encmode == 1` (ENCRYPT_MODE) **e** `mode(c.getAlgorithm())` normalizado ∈ {CBC, CTS, CTR,
   CFB, PCBC, OFB}. Leitura `:160` `validate(PREPARED_IV, params)`; NOBS `:165-168`.
2. **Produtor.** P-PREPARED_IV (`IvParameterSpec.mop:152-154`), gate `RANDOMIZED` do `iv`.
3. **Proveniência aceitável.** `sr.nextBytes(iv)` (ou `iv = sr.generateSeed(n)`) com `sr` de nascimento
   observado e dono `SecureRandom` → `new IvParameterSpec(iv)` (ou `(iv, off, len>0)`) → **o mesmo spec**
   em `c.init(ENCRYPT_MODE, key, spec)`. **Nunca satisfaz:** IV zero/constante (`new byte[16]`, bytes
   fixos — MISUSE típico), IV derivado da chave/senha, IV de `Arrays.copyOfRange` de um buffer aleatório,
   `c.getParameters().getParameterSpec(IvParameterSpec.class)` ou `new IvParameterSpec(c.getIV())`
   (objetos do framework), `GCMParameterSpec` passado em modo CBC, `SecureRandom` de nascimento não
   observado. Decriptação **não** é lida (encmode ≠ 1).
4. **Cascata.** `IVPARAMETERSPEC-NOBS-00/01` (e `-CONSTR-00/01/02`) sobre o spec passado → este NOBS
   (duplo relato registrado em `IvChainJunction.mop:127-137`); por trás, as raízes de P-RANDOMIZED
   (`SECURERANDOM-ORDER-00` no `nextBytes`, `SECURERANDOM-ALG-00/01`).
5. **CrySL.** `crysl/Cipher.crysl:138` (`encmode == 1`), `crysl/IvParameterSpec.crysl:22,25`. Equivalente.

### IVCHAINJUNCTION-NOBS-01

1. **Emissor.** Mesmo evento `use`. Condição `:191-193`: modo normalizado == `GCM`, **sem** restrição de
   `encmode` (decriptação também é lida). Leitura `:194` `validate(PREPARED_GCM, params)`; NOBS `:199-202`.
2. **Produtor.** P-PREPARED_GCM (`GCMParameterSpecSpec.mop:179-181`), gate tamanho de tag + `RANDOMIZED`.
3. **Proveniência aceitável.** `sr.nextBytes(nonce)` → `new GCMParameterSpec(128, nonce)` (ou
   `(128, nonce, off, len)`) → mesmo objeto em `c.init(mode, key, spec)`. **Nunca satisfaz:** toda
   decriptação GCM que lê o nonce do texto cifrado (`new GCMParameterSpec(128, ct, 0, 12)`) — o oráculo
   exige o predicado também ali, então é NOBS por construção (`LEGIT_UNOBSERVABLE`); `new
   GCMParameterSpec(128, c.getIV())`; **`IvParameterSpec` usado com GCM** (Conscrypt aceita; aqui sempre NOBS
   mesmo se o IV foi aleatório, pois o spec tem `PREPARED_IV`, não `PREPARED_GCM`); nonce fatiado/copiado;
   tag fora da lista.
4. **Cascata.** `GCMPARAMETERSPEC-NOBS-00/01` e `-CONSTR-00..03` sobre o spec → este NOBS; por trás,
   raízes de P-RANDOMIZED.
5. **CrySL.** `crysl/Cipher.crysl:139` (sem `encmode`), `crysl/GCMParameterSpec.crysl:24,27`. Equivalente
   (leitura literal do oráculo).

### IVPARAMETERSPEC-NOBS-00

1. **Emissor.** `IvParameterSpec.mop:65-67` `event c1 after(byte[] iv) returning(IvParameterSpec s)`:
   `call(IvParameterSpec.new(byte[]))`. Leitura `:68` `validate(RANDOMIZED, iv)` (1º argumento); NOBS
   `:73-76`. Lido em **qualquer** uso (encrypt e decrypt; o construtor não sabe o modo).
2. **Produtor.** P-RANDOMIZED, `@match2` (`SecureRandomSpec.mop:392-401`) sobre arrays de `nextBytes` /
   `generateSeed`.
3. **Proveniência aceitável.** `SecureRandom` criado em código tecido (c1/c2/g1/g2/g3), `sr.nextBytes(iv)`
   com dono estático `SecureRandom`, depois `new IvParameterSpec(iv)` com o **mesmo** array; ou
   `iv = sr.generateSeed(n)`. **Nunca satisfaz:** IV lido do texto cifrado/armazenamento na decriptação
   (`LEGIT_UNOBSERVABLE`), `c.getIV()` (cópia do framework), IV constante/zero/derivado (MISUSE),
   `Arrays.copyOfRange(random, 0, 16)` (cópia), `Random`/`ThreadLocalRandom`, `Random r = new
   SecureRandom(); r.nextBytes(iv)` (dono `java/util/Random`, §0.3), `SecureRandom` criado no framework
   ou em pacote excluído (o `nextBytes` gera `SECURERANDOM-ORDER-00` e não marca), bytes de
   `getEncoded()` de uma chave.
4. **Cascata.** Entradas: `SECURERANDOM-ALG-00/01` e o `SECURERANDOM-ORDER-00` do `nextBytes` que
   preencheu o array. `SECURERANDOM-NOBS-00/01` não cascateiam. Saída: `IVCHAINJUNCTION-NOBS-00` (e a
   leitura de `AlgorithmParametersSpec`).
5. **CrySL.** `crysl/IvParameterSpec.crysl:22`, `crysl/SecureRandom.crysl:51`. Equivalente no predicado;
   **mais estreito na tecelagem** (dono exato de `nextBytes`; ver §3).

### GCMPARAMETERSPEC-NOBS-00

1. **Emissor.** `GCMParameterSpecSpec.mop:62-64` `event c1 after(int tagLen, byte[] src)
   returning(GCMParameterSpec s)`: `call(GCMParameterSpec.new(int, byte[]))`. Leitura `:71`
   `validate(RANDOMIZED, src)` (2º argumento); NOBS `:77-81`. Independe do tamanho da tag.
2. **Produtor.** P-RANDOMIZED `@match2`.
3. **Proveniências.** Iguais a `IVPARAMETERSPEC-NOBS-00` com `src` no lugar de `iv`. O caso "nunca"
   dominante é a decriptação que reconstrói o spec a partir do nonce armazenado junto do texto cifrado,
   e o `new GCMParameterSpec(128, cipher.getIV())`.
4. **Cascata.** Entradas iguais às de `IVPARAMETERSPEC-NOBS-00`. Saída: `IVCHAINJUNCTION-NOBS-01`.
5. **CrySL.** `crysl/GCMParameterSpec.crysl:24`. Equivalente.

### GCMPARAMETERSPEC-NOBS-01

1. **Emissor.** `GCMParameterSpecSpec.mop:116-118` `event c2 after(int tagLen, byte[] src, int offset, int
   len) returning(GCMParameterSpec s)`. Leitura `:125`, NOBS `:131-135`. Objeto = o array inteiro.
2. **Produtor.** P-RANDOMIZED `@match2`.
3. **Proveniências.** Satisfaz se `src` é o array preenchido por `nextBytes` observado (com recorte);
   nunca satisfaz o padrão `new GCMParameterSpec(128, data, 0, 12)` em que `data` é o texto cifrado
   recebido (decriptação) ou um buffer montado por concatenação.
4. **Cascata.** Idem `-NOBS-00`.
5. **CrySL.** `crysl/GCMParameterSpec.crysl:11,24`. Equivalente.

### MAC-NOBS-00

1. **Emissor.** `MacSpec.mop:171-174` `event i1 before(java.security.Key key, Mac m)`:
   `call(void Mac.init(java.security.Key)) && args(key) && target(m)`. Leitura `:179`
   `validateAny(GENERATED_KEY, key)` (valor anônimo); NOBS `:184-187`. Só `GENERATED_KEY` conta
   (chaves assimétricas não).
2. **Produtores.** P-GENERATED_KEY (KeyGenerator, KeyStore, SecretKeySpec conforme, SecretKeyFactory
   `gen`/`translate`). O `algorithm == null` de uma `SecretKeyFactory` não observada **satisfaz** aqui
   (`validateAny`).
3. **Proveniências aceitáveis.** `KeyGenerator.getInstance("HmacSHA256"[, "AndroidKeyStore"]).generateKey()`;
   `KeyStore.getKey`; `new SecretKeySpec(k.getEncoded(), "HmacSHA256|384|512")` com `k` creditada;
   `SecretKeyFactory.generateSecret(pbeKeySpec conforme)`. **Nunca satisfaz:** HMAC com chave de bytes
   externos/constantes (inclusive licenças/assinaturas de API), `SecretKeySpec(bytes, "HmacSHA1")` ou
   `"HMAC"` (Tink) — algoritmo fora da lista impede o `ensure` mesmo com material preparado; HKDF
   (`Mac.init(new SecretKeySpec(salt, …))` com sal constante/zero); chave vinda de `getEntry`;
   `SecretKeySpec` sobre `nextBytes`.
4. **Cascata.** Entradas: `SECRETKEYSPEC-NOBS-00/01` (+`-ALG-00/01`), `SECRETKEYFACTORY-NOBS-00`,
   `KEYSTORE-ORDER-00`, `KEYGENERATOR-ORDER-00`/algoritmo rejeitado.
5. **CrySL.** `crysl/Mac.crysl:54` `generatedKey[key,_]`. Equivalente.

### KEYFACTORY-NOBS-01

1. **Emissor.** `KeyFactorySpec.mop:101-103` `event genPublic after(KeySpec keySpec, KeyFactory f)
   returning(PublicKey publicKey)`: `call(PublicKey KeyFactory.generatePublic(KeySpec)) && args(keySpec)
   && target(f)`. Leitura `:105` `validateAny(SPECCED_KEY, keySpec)`; NOBS `:111-115` e `conforms = false`
   → **não** escreve `GENERATED_PUBLIC_KEY` (`:116-118`).
2. **Produtores.** P-SPECCED_KEY: `X509EncodedKeySpecSpec.mop:82-84` (o único realista para chave pública),
   `SecretKeySpecSpec.mop:257`, `PBEKeySpecSpec.mop:160`.
3. **Proveniência aceitável.** `new X509EncodedKeySpec(pub.getEncoded())` onde `pub` já é creditada
   (`KeyPair.getPublic()` ou outra `generatePublic` creditada) → `generatePublic`: basicamente só uma ida e
   volta dentro do mesmo processo. **Nunca satisfaz:** chave pública recebida de fora — Base64 de
   licença/servidor (p.ex. verificação de compra do Google Play: `generatePublic(new
   X509EncodedKeySpec(Base64.decode(chave)))`), certificado/pin, par remoto de ECDH — e todo spec sem
   produtor: `RSAPublicKeySpec`, `ECPublicKeySpec` (Tink `EllipticCurves`), `DHPublicKeySpec`.
4. **Cascata.** Entrada: `X509ENCODEDKEYSPEC-NOBS-00` (e `-CONSTR-00`) sobre o mesmo spec. Saídas:
   `SIGNATURE-NOBS-02`, `KEYAGREEMENT-NOBS-08`, `CIPHER-NOBS-00` (chave pública em `Cipher.init`),
   `KEYPAIR-NOBS-01`, `TrustAnchorSpec`, e `X509ENCODEDKEYSPEC-NOBS-00` de uma re-codificação
   (`KeySpec.mop:78-84`).
5. **CrySL.** `crysl/KeyFactory.crysl:27`; `speccedKey` só é garantido por `PBEKeySpec`, `SecretKeySpec`,
   `X509EncodedKeySpec` nos 49. Equivalente ao oráculo; os specs sem regra são produtor ausente no conjunto
   e no oráculo.

### PBEKEYSPEC-NOBS-01

1. **Emissor.** `PBEKeySpecSpec.mop:117-119` `event c1 after(char[] password, byte[] salt, int
   iterationCount, int keyLength) returning(PBEKeySpec s)`. Leitura `:148` `validate(RANDOMIZED, salt)`
   (2º argumento); NOBS `:154-158`, zera `conforms` → sem `SPECCED_KEY` (`:159-161`).
2. **Produtor.** P-RANDOMIZED `@match2`.
3. **Proveniência aceitável.** `sr.nextBytes(salt)` (sr de nascimento observado) → `new PBEKeySpec(pw, salt,
   iter, len)` com o mesmo array. **Nunca satisfaz:** sal lido junto do texto cifrado/perfil na
   re-derivação (login, decriptação — `LEGIT_UNOBSERVABLE`), sal constante ou derivado do usuário/pacote
   (MISUSE), sal Base64-decodificado, cópia.
4. **Cascata.** Entradas: raízes de P-RANDOMIZED. Saída: `SECRETKEYFACTORY-NOBS-00` (e daí
   `CIPHER-NOBS-00`/`MAC-NOBS-00`/`SECRETKEYSPEC-NOBS-00`).
5. **CrySL.** `crysl/PBEKeySpec.crysl:29`. Equivalente.

### SECRETKEYFACTORY-NOBS-00

1. **Emissor.** `SecretKeyFactorySpec.mop:92-94` `event gen after(KeySpec keySpec, SecretKeyFactory f)
   returning(SecretKey key)`: `call(SecretKey SecretKeyFactory.generateSecret(KeySpec)) && args(keySpec) &&
   target(f)`. Leitura `:96` `validateAny(SPECCED_KEY, keySpec)`; NOBS `:102-106`; sem `ensure`
   (`:107-109`).
2. **Produtores.** P-SPECCED_KEY (PBEKeySpec conforme, SecretKeySpec conforme, X509EncodedKeySpec conforme).
3. **Proveniência aceitável.** `new PBEKeySpec(pw, salt∈RANDOMIZED, iter ≥ 10000, len)` → `generateSecret`
   sem `clearPassword()` antes. **Nunca satisfaz:** sal não creditado (ver seção anterior), iterações
   < 10 000 (`PBEKEYSPEC-CONSTR-00` também zera `conforms`), construtores `PBEKeySpec(char[])` /
   `(char[], byte[], int)` (`PBEKEYSPEC-FORB-00/01`, nunca escrevem), `DESedeKeySpec`/`DESKeySpec` (sem
   spec), `SecretKeySpec` não conforme.
4. **Cascata.** Entradas: `PBEKEYSPEC-NOBS-01`, `PBEKEYSPEC-CONSTR-00/02`, `PBEKEYSPEC-FORB-00/01`,
   `SECRETKEYSPEC-NOBS-00/01`, `X509ENCODEDKEYSPEC-NOBS-00`. Saídas: `CIPHER-NOBS-00`, `MAC-NOBS-00/01`,
   `SECRETKEYSPEC-NOBS-00/01` e `X509ENCODEDKEYSPEC-NOBS-00` sobre `getEncoded()` da chave derivada.
5. **CrySL.** `crysl/SecretKeyFactory.crysl:28`. Equivalente. (O `ensure` do conjunto não verifica a lista de
   algoritmos — mais largo, irrelevante para NOBS.)

### KEYAGREEMENT-NOBS-08

1. **Emissor.** `KeyAgreementSpec.mop:259-261` `event dophase after(Key pubKey, boolean lastPhase,
   KeyAgreement ka)`: `call(Key KeyAgreement.doPhase(Key, boolean)) && args(pubKey, lastPhase) &&
   target(ka)`. Leitura `:262` `validate(GENERATED_PUBLIC_KEY, pubKey)`; NOBS `:268-272`, `conforms = false`.
2. **Produtores.** P-GENERATED_PUBLIC_KEY (`KeyPairSpec.gpu`, `KeyFactorySpec.genPublic`).
3. **Proveniência aceitável.** Chave pública do par obtida por `KeyPair.getPublic()` em código tecido
   (teste local/par gerado no mesmo processo) ou por `generatePublic(X509EncodedKeySpec(bytes creditados))`.
   **Nunca satisfaz:** a chave pública do **outro** participante recebida pela rede/armazenamento — o uso
   normal de ECDH/DH —, `ECPublicKeySpec`/`DHPublicKeySpec`, decodificação por BouncyCastle/Tink sem passar
   pela API `KeyFactory`.
4. **Cascata.** Entradas: `KEYFACTORY-NOBS-01` ← `X509ENCODEDKEYSPEC-NOBS-00`. Saída: `conforms = false` →
   `generateSecret()` não marca → `SECRETKEYSPEC-NOBS-00/01`, `X509ENCODEDKEYSPEC-NOBS-00`.
   Ressalva: se o `KeyAgreement` nasceu fora do código tecido, cada evento cai em `fail` e `@fail` repõe
   `conforms = true` (`:381-386`), então `gs1` marca o segredo mesmo com NOBS — falso negativo, não NOBS.
5. **CrySL.** `crysl/KeyAgreement.crysl:46`. Equivalente.

### SIGNATURE-NOBS-02

1. **Emissor.** `SignatureSpec.mop:184-187` `event i4 before(PublicKey key, Signature s)`:
   `call(void Signature.initVerify(PublicKey)) && args(key) && target(s)`. Leitura `:192`
   `validate(GENERATED_PUBLIC_KEY, key)`; NOBS `:197-200`. `initVerify(Certificate)` (`i3`, `:174-182`)
   não lê nada.
2. **Produtores.** P-GENERATED_PUBLIC_KEY.
3. **Proveniência aceitável.** `kp.getPublic()` ou `generatePublic(X509EncodedKeySpec(bytes creditados))`.
   **Nunca satisfaz:** verificação com chave pública embutida/recebida (Base64 → `X509EncodedKeySpec` →
   `generatePublic`, p.ex. `Security.verifyPurchase` do Play Billing), `cert.getPublicKey()`,
   `ks.getCertificate(alias).getPublicKey()` (AndroidKeyStore), `RSAPublicKeySpec`.
4. **Cascata.** Entradas: `KEYFACTORY-NOBS-01` ← `X509ENCODEDKEYSPEC-NOBS-00`.
5. **CrySL.** `crysl/Signature.crysl:55`. Equivalente; o oráculo também não credita `Certificate.getPublicKey()`
   (nem trata `initVerify(cert)`).

### X509ENCODEDKEYSPEC-NOBS-00

1. **Emissor.** `X509EncodedKeySpecSpec.mop:40-42` `event c1 after(byte[] encodedKey)
   returning(X509EncodedKeySpec s)`: `call(X509EncodedKeySpec.new(byte[]))`. Leitura `:43`
   `validate(PREPARED_KEY_MATERIAL, encodedKey)`; NOBS `:48-51`; `spec` não vinculado → sem `SPECCED_KEY`.
2. **Produtores.** P-PREPARED_KEY_MATERIAL.
3. **Proveniência aceitável.** `new X509EncodedKeySpec(pub.getEncoded())` com `pub` creditada.
   **Nunca satisfaz:** bytes Base64/PEM de chave pública embutida, baixada, lida de preferência ou de
   certificado; `cert.getPublicKey().getEncoded()` (origem não creditada → gate de `KeySpec.mop:78-84`).
4. **Cascata.** Entradas: raízes da chave cujo `getEncoded()` foi lido (`KEYFACTORY-NOBS-01`, ...),
   `KEYAGREEMENT-*` via `conforms` (improvável). Saídas: `KEYFACTORY-NOBS-00/01` →
   `SIGNATURE-NOBS-02`/`KEYAGREEMENT-NOBS-08`/`CIPHER-NOBS-00`.
5. **CrySL.** `crysl/X509EncodedKeySpec.crysl:14`. Equivalente ao oráculo quanto ao predicado; **mais
   estreito** pelo gate de origem em `Key.getEncoded()` (ver `SECRETKEYSPEC-NOBS-00`, item 5).

### SECURERANDOM-NOBS-00

1. **Emissor.** `SecureRandomSpec.mop:226-229` `event setSeed2 after(byte[] seed, SecureRandom r)`:
   `call(void SecureRandom.setSeed(byte[])) && args(seed) && target(r)`. Leitura `:230`
   `validate(RANDOMIZED, seed)`; NOBS `:235-238`. `setSeed(long)` (`setSeed1`, `:200-202`) não lê nada.
2. **Produtor.** P-RANDOMIZED `@match2` (arrays de `generateSeed`/`nextBytes` de **outro** — ou do mesmo —
   `SecureRandom` observado).
3. **Proveniência aceitável.** `sr.setSeed(sr2.generateSeed(n))` ou semente preenchida por `nextBytes`
   observado. **Nunca satisfaz:** semente de `String.getBytes()`, identificador do dispositivo, tempo
   serializado, constante — candidatos a MISUSE se o gerador for determinístico; no Android (Conscrypt
   `OpenSSLRandom`) a semente complementa o estado, o que pesa na avaliação da gravidade, não no rótulo
   NOBS.
4. **Cascata.** Entradas: raízes de P-RANDOMIZED. Saída: **nenhuma** (`setSeed2` não bloqueia `@match1`
   nem `@match2`).
5. **CrySL.** `crysl/SecureRandom.crysl:45`. Equivalente.

### SECURERANDOM-NOBS-01

1. **Emissor.** `SecureRandomSpec.mop:95-97` `event c2 after(byte[] seed) returning(SecureRandom r)`:
   `call(SecureRandom.new(byte[]))`. Leitura `:99`; NOBS `:104-107`.
2. **Produtor.** P-RANDOMIZED `@match2`.
3. **Proveniências.** Iguais a `SECURERANDOM-NOBS-00` (`new SecureRandom(sr.generateSeed(32))` satisfaz;
   semente literal/derivada não).
4. **Cascata.** Saída: nenhuma — o gerador ainda recebe `RANDOMIZED` em `@match1` (`c2 -> init`, `:332`).
5. **CrySL.** `crysl/SecureRandom.crysl:15,45`. Equivalente.

---

## 3. Padrões corretos que o conjunto nunca credita

Derivados dos produtores do §1 (nenhum `ensure` existe para eles). Coluna "natureza" indica se a
proveniência é inobservável por construção (dado externo, `null`, framework) ou observável em princípio
(há uma chamada de API em código tecido que o conjunto não credita — candidato a SPEC_DEFECT).

| Padrão | Códigos afetados | Natureza | Base |
|---|---|---|---|
| `SSLContext.init(null, …)`, `init(…, null, …)`, `init(…, …, null)` | SSLCONTEXT-NOBS-00/01/02 | `null` = padrão da plataforma; leitura por decisão | `SSLContextSpec.mop:176-185, 204-208`; `store:343-345` |
| `TrustManager[]`/`KeyManager[]` montado à mão (`arrayOf(tm)`) | SSLCONTEXT-NOBS-00/01 | cópia/array novo; o elemento pode ter vindo de fábrica observada | P-GENERATED_TRUST_MANAGER |
| `TrustManagerFactory.init((KeyStore) null)`, `KeyManagerFactory.init(null, null)` | TRUSTMANAGERFACTORY-NOBS-00, KEYMANAGERFACTORY-NOBS-00 | `null` = padrão | `TrustManagerFactorySpec.mop:102-112` |
| `KeyStore` de nascimento não observado (`getInstance(File,…)`, framework, pacote excluído) | TMF/KMF-NOBS-00, CIPHER/MAC-NOBS-00 | framework/weaver | `KeyStoreSpec.mop:124` |
| `KeyStore.getEntry(...)` → `getSecretKey()`/`getPrivateKey()`; `getCertificate(a).getPublicKey()` | CIPHER-NOBS-00, MAC-NOBS-00, SIGNATURE-NOBS-00..02, SECRETKEYSPEC-NOBS-* (via `getEncoded`) | **observável**; produtor ausente no conjunto e no oráculo | `KeyStoreSpec.mop:106-122`; `crysl/KeyStore.crysl:58-62` |
| `Certificate.getPublicKey()` | SIGNATURE-NOBS-02, KEYAGREEMENT-NOBS-08, CIPHER-NOBS-00, X509ENCODEDKEYSPEC-NOBS-00 | observável; produtor ausente (conjunto e oráculo) | P-GENERATED_PUBLIC_KEY |
| Chave pública/privada decodificada de bytes externos (`X509EncodedKeySpec`/`PKCS8EncodedKeySpec` de Base64) | X509ENCODEDKEYSPEC-NOBS-00 → KEYFACTORY-NOBS-00/01 → SIGNATURE-NOBS-02 / KEYAGREEMENT-NOBS-08 / CIPHER-NOBS-00 | dado externo | `X509EncodedKeySpecSpec.mop:43`; sem spec para PKCS8 |
| `RSAPublicKeySpec`, `ECPublicKeySpec`, `DHPublicKeySpec`, `DESedeKeySpec`, `PKCS8EncodedKeySpec` como `KeySpec` | KEYFACTORY-NOBS-00/01, SECRETKEYFACTORY-NOBS-00 | observável; produtor ausente (conjunto e oráculo) | P-SPECCED_KEY |
| Chave simétrica de bytes armazenados, keyset (Tink), rede, constante | SECRETKEYSPEC-NOBS-*, CIPHER-NOBS-00, MAC-NOBS-00 | dado externo (ou MISUSE se constante) | P-PREPARED_KEY_MATERIAL |
| Chave simétrica de `SecureRandom.nextBytes(k)` → `new SecretKeySpec(k, "AES")` | SECRETKEYSPEC-NOBS-*, CIPHER/MAC-NOBS-00 | observável; o **oráculo** exige `preparedKeyMaterial`, não `randomized` (literal) | `SecretKeySpecSpec.mop:79-91`; `crysl/SecretKeySpec.crysl:23` |
| Material derivado por `MessageDigest.digest`, HKDF/`Mac.doFinal`, ou `KeyAgreement.generateSecret()` pós-processado | SECRETKEYSPEC-NOBS-*, CIPHER/MAC-NOBS-00 | observável; nenhuma regra garante predicado para essas saídas | P-PREPARED_KEY_MATERIAL |
| `getEncoded()` de chave com origem não creditada (entry getter, `unwrap`, `getPublicKey`, framework) | SECRETKEYSPEC-NOBS-*, X509ENCODEDKEYSPEC-NOBS-00 | observável; **conjunto mais estreito que o oráculo** | `KeySpec.mop:66, 78-84`; `SecretKeySpec.mop:122-126`; `crysl/Key.crysl:14`, `crysl/SecretKey.crysl:17` |
| Qualquer cópia (`Arrays.copyOf*`, `clone`, `arraycopy`, `ByteBuffer`, Base64 ida e volta) de IV/nonce/sal/chave | todos os de array | identidade perdida | `store:222-251` |
| IV/nonce/sal lido do texto cifrado ou do armazenamento (decriptação, re-derivação) | IVPARAMETERSPEC-NOBS-00, GCMPARAMETERSPEC-NOBS-00/01, IVCHAINJUNCTION-NOBS-01, PBEKEYSPEC-NOBS-01 → SECRETKEYFACTORY-NOBS-00 | dado externo | P-RANDOMIZED |
| Decriptação GCM (sempre lida) | IVCHAINJUNCTION-NOBS-01 | leitura literal de `Cipher.crysl:139` | `IvChainJunction.mop:179-194` |
| `IvParameterSpec` usado com transformação GCM | IVCHAINJUNCTION-NOBS-01 | observável; spec não tem `PREPARED_GCM` | `IvChainJunction.mop:194` |
| `Cipher.getIV()`, `Cipher.getParameters().getParameterSpec(...)` | IVPARAMETERSPEC-NOBS-00, GCMPARAMETERSPEC-NOBS-00, IVCHAINJUNCTION-NOBS-00/01 | objeto do framework | nenhum produtor |
| `Random r = new SecureRandom(); r.nextBytes(b)`; receptor tipado como subclasse de `SecureRandom` | IVPARAMETERSPEC/GCMPARAMETERSPEC/PBEKEYSPEC/SECURERANDOM-NOBS-* | observável; **dono exato do pointcut** | `SecureRandomSpec.mop:289-294`; `matcher:343` |
| `SecureRandom` criado no framework ou pacote excluído, ou por `getInstance` com algoritmo fora da lista; `nextBytes` sobre ele | idem + SSLCONTEXT-NOBS-02 | framework/weaver (ALG: constraint do oráculo) | `SecureRandomSpec.mop:336-339, 370-376` |
| Segundo `generateKey()` no mesmo `KeyGenerator`; `KeyGenerator` com algoritmo fora da lista | CIPHER-NOBS-00, MAC-NOBS-00 | ORDER/constraint do oráculo | `KeyGeneratorSpec.mop:175, 186-196` |
| `PBEKeySpec` com < 10 000 iterações ou construtor proibido | SECRETKEYFACTORY-NOBS-00 | constraint/FORBIDDEN do oráculo | `PBEKeySpecSpec.mop:121-125, 48-60` |
| `SecretKeySpec` com algoritmo fora da lista (`HmacSHA1`, `DESede`, `ChaCha20`, `HMAC`, transformação completa) | CIPHER-NOBS-00, MAC-NOBS-00 (o próprio spec acusa ALG, não NOBS) | constraint do oráculo | `SecretKeySpecSpec.mop:38-39, 105-109, 121-124` |

---

## 4. Arestas de cascata

Notação: `A ⇒ B` = o código `A` (ou o estado que o acompanha) impede o `ensure` que a leitura `B` exige.
"gate" = linha que condiciona o `ensure`.

### 4.1 Arestas que existem

```
SECURERANDOM-ALG-00/01 (g4/g5: sr não vinculado, fica em start)        gate SecureRandomSpec.mop:336-337, 383-385
SECURERANDOM-ORDER-00 no nextBytes/generateSeed (nascimento não visto) gate :370-376, 392-401
   ⇒ SSLCONTEXT-NOBS-02 (só ALG)
   ⇒ IVPARAMETERSPEC-NOBS-00/01 ⇒ IVCHAINJUNCTION-NOBS-00               gate IvParameterSpec.mop:77-79, 130-132, 152-154
   ⇒ GCMPARAMETERSPEC-NOBS-00/01 ⇒ IVCHAINJUNCTION-NOBS-01              gate GCMParameterSpecSpec.mop:82-84, 136-138, 179-181
   ⇒ PBEKEYSPEC-NOBS-01 ⇒ SECRETKEYFACTORY-NOBS-00                      gate PBEKeySpecSpec.mop:159-161
   ⇒ SECURERANDOM-NOBS-00/01

PBEKEYSPEC-CONSTR-00/02, PBEKEYSPEC-FORB-00/01 ⇒ SECRETKEYFACTORY-NOBS-00
IVPARAMETERSPEC-CONSTR-00/01/02 ⇒ IVCHAINJUNCTION-NOBS-00
GCMPARAMETERSPEC-CONSTR-00..03  ⇒ IVCHAINJUNCTION-NOBS-01

SECRETKEYFACTORY-NOBS-00 (e -CONSTR-00)                                 gate SecretKeyFactorySpec.mop:107-109
   ⇒ CIPHER-NOBS-00, MAC-NOBS-00/01
   ⇒ (getEncoded sem ponte, KeySpec.mop:78-84 / SecretKeySpec.mop:122-126)
        SECRETKEYSPEC-NOBS-00/01, X509ENCODEDKEYSPEC-NOBS-00

SECRETKEYSPEC-NOBS-00/01 (e -ALG-00/01, -CONSTR-*)                      gate SecretKeySpecSpec.mop:121-124, 187-190, 255-258
   ⇒ CIPHER-NOBS-00, MAC-NOBS-00/01
   ⇒ SECRETKEYFACTORY-NOBS-00, KEYFACTORY-NOBS-00/01 (sem SPECCED_KEY)
   ⇒ SECRETKEYSPEC-NOBS-00/01 seguinte (re-embrulho do getEncoded)

X509ENCODEDKEYSPEC-NOBS-00 (e -CONSTR-00)                               gate X509EncodedKeySpecSpec.mop:52-54, 82-84
   ⇒ KEYFACTORY-NOBS-00/01                                              gate KeyFactorySpec.mop:90-92, 116-118
        ⇒ SIGNATURE-NOBS-00/01/02, KEYAGREEMENT-NOBS-00/01/03/06/08, CIPHER-NOBS-00, KEYPAIR-NOBS-00/01
        ⇒ X509ENCODEDKEYSPEC-NOBS-00 / SECRETKEYSPEC-NOBS-* (getEncoded sem ponte)

KEYAGREEMENT-NOBS-00..08, -CONSTR-00..08, -ALG-00, -FORB-00 (antes do gs) gate KeyAgreementSpec.mop:297, 314
   ⇒ SECRETKEYSPEC-NOBS-00/01, X509ENCODEDKEYSPEC-NOBS-00

KEYSTORE-ORDER-00 / tipo fora da lista (g2)                             gate KeyStoreSpec.mop:124, 194-206
   ⇒ TRUSTMANAGERFACTORY-NOBS-00, KEYMANAGERFACTORY-NOBS-00 (sem GENERATED_KEY_STORE)
   ⇒ CIPHER-NOBS-00, MAC-NOBS-00, SIGNATURE-NOBS-00/01 (chave de getKey sem crédito)

KEYGENERATOR-ORDER-00 / algoritmo fora da lista                         gate KeyGeneratorSpec.mop:175, 213-228
   ⇒ CIPHER-NOBS-00, MAC-NOBS-00, e via getEncoded SECRETKEYSPEC-NOBS-*
```

### 4.2 Arestas que **não** existem (verificadas)

- `TRUSTMANAGERFACTORY-NOBS-00/01`, `-ALG-00`, `-ORDER-00` ⇏ `SSLCONTEXT-NOBS-01`: o array é marcado no
  corpo de `gtm1` (`TrustManagerFactorySpec.mop:215-219`), que roda antes da transição e em qualquer
  estado (§0.2). Idem `KEYMANAGERFACTORY-*` ⇏ `SSLCONTEXT-NOBS-00` (`KeyManagerFactorySpec.mop:173-177`).
  Um `SSLCONTEXT-NOBS-00/01` tem sempre raiz **no próprio argumento** (`null`, array novo, cópia,
  framework).
- `SECURERANDOM-NOBS-00/01` ⇏ nada (`SecureRandomSpec.mop:95-108, 226-239`; `@match1` incondicional).
- `KEYGENERATOR-NOBS-00..02` ⇏ `CIPHER/MAC-NOBS-00` (`@match` sem `conforms`, `KeyGeneratorSpec.mop:213-228`).
- `KEYPAIR-NOBS-00/01`, `KEYPAIR-ORDER-00` ⇏ `SIGNATURE/KEYAGREEMENT/CIPHER-NOBS` (`gpu`/`gpr` no corpo,
  `KeyPairSpec.mop:123-147`).
- `CIPHER-NOBS-00` ⇏ `CipherInputStream/CipherOutputStream` (`initialisedCipher` staged sem gate,
  `CipherSpec.mop:238`).
- `IVCHAINJUNCTION-NOBS-*` e `SSLCONTEXT-NOBS-*` são folhas: nenhum `ensure` depende deles.

### 4.3 Sinais diagnósticos para os dossiês

- `SECURERANDOM-ORDER-00` na mesma linha de um `nextBytes` = o array daquele IV/sal/nonce nunca foi marcado
  (nascimento do `SecureRandom` não observado); a raiz é weaver/framework, não o IV.
- Um `KEYSTORE-ORDER-00` no mesmo objeto antes de `tmf.init(ks)`/`getKey` explica TMF/KMF/CIPHER-NOBS.
- `PBEKEYSPEC-NOBS-01` + `SECRETKEYFACTORY-NOBS-00` + `SECRETKEYSPEC-NOBS-00` + `CIPHER-NOBS-00` no mesmo
  método é **uma** proveniência (o sal), não quatro.
- Chave pública externa gera a trinca `X509ENCODEDKEYSPEC-NOBS-00` → `KEYFACTORY-NOBS-01` →
  `SIGNATURE-NOBS-02`/`KEYAGREEMENT-NOBS-08`, com raiz na primeira.
