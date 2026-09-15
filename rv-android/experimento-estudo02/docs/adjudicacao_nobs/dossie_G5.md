# Dossiê G5 — TLS do ktor, bouncycastle/spongycastle, gms ads, LVL AESObfuscator, whyoleg PBKDF2

Grupo G5, 17 métodos, 29 sites. Caminhos de biblioteca relativos a `$SP/src/`, de app relativos ao
diretório `repos/`, de `.mop` relativos a `rvsec-mop/src/main/resources/jca_android/`.

## Veredictos

| id | classe.método | código | categoria | mecanismo | raiz |
|---|---|---|---|---|---|
| 0 | bc JcaContentVerifierProviderBuilder.createRawSig | SIGNATURE-NOBS-02 | LEGIT_UNOBSERVABLE | pubkey_from_certificate | — |
| 1 | bc JcaContentVerifierProviderBuilder$1.get | SIGNATURE-NOBS-02 | LEGIT_UNOBSERVABLE | pubkey_from_certificate | — |
| 2 | ktor HashesKt.P_hash | MAC-NOBS-00 | LEGIT_UNOBSERVABLE | tls_prf_derived_key | SECRETKEYSPEC-NOBS-00 @ KeysKt.masterSecret (1 de 4 PRFs cai em SPEC_DEFECT) |
| 3 | ktor KeysKt.clientKey | SECRETKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | tls_prf_derived_key | — |
| 4 | ktor KeysKt.masterSecret | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | tls_prf_derived_key | — |
| 5 | ktor KeysKt.serverKey | SECRETKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | tls_prf_derived_key | — |
| 6 | ktor TLSClientHandshake.generatePreSecret | KEYAGREEMENT-NOBS-08 | SPEC_DEFECT | cascade | KEYFACTORY-NOBS-01 @ generateECKeys |
| 7 | ktor TLSClientHandshake.handleServerDone | SECRETKEYSPEC-NOBS-00 | SPEC_DEFECT | cascade | KEYFACTORY-NOBS-01 @ generateECKeys |
| 8 | ktor TLSClientHandshakeKt.generateECKeys | KEYFACTORY-NOBS-01 | SPEC_DEFECT | producer_missing_in_specset | — |
| 9 | ktor TLSConfigBuilderKt.findTrustManager | TRUSTMANAGERFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore | — |
| 10 | ktor GCMCipherKt.gcmDecryptCipher | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-01 @ KeysKt.serverKey |
| 10 | ktor GCMCipherKt.gcmDecryptCipher | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_record_and_key_block | — |
| 10 | ktor GCMCipherKt.gcmDecryptCipher | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-00 @ gcmDecryptCipher |
| 11 | ktor GCMCipherKt.gcmEncryptCipher | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-01 @ KeysKt.clientKey |
| 11 | ktor GCMCipherKt.gcmEncryptCipher | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | tls_deterministic_nonce | — |
| 11 | ktor GCMCipherKt.gcmEncryptCipher | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-00 @ gcmEncryptCipher |
| 12 | ktor NonceKt$nonceGeneratorJob$1.invokeSuspend | SECURERANDOM-NOBS-00 | SPEC_DEFECT | producer_reset_by_g1_g2_double_match | SECURERANDOM-ORDER-00 @ NonceKt.getInstanceOrNull |
| 31 | gms ads zzbbe.zzb | SECRETKEYSPEC-NOBS-00 | **MISUSE** | hardcoded_key | — |
| 31 | gms ads zzbbe.zzb | CIPHER-NOBS-00 | **MISUSE** | cascade | SECRETKEYSPEC-NOBS-00 @ zzbbe.zzb |
| 31 | gms ads zzbbe.zzb | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 32 | LVL AESObfuscator.&lt;init&gt; | PBEKEYSPEC-NOBS-01 | **MISUSE** | hardcoded_salt | — |
| 32 | LVL AESObfuscator.&lt;init&gt; | SECRETKEYFACTORY-NOBS-00 | **MISUSE** | cascade | PBEKEYSPEC-NOBS-01 @ AESObfuscator.&lt;init&gt; |
| 32 | LVL AESObfuscator.&lt;init&gt; | SECRETKEYSPEC-NOBS-00 | **MISUSE** | cascade | PBEKEYSPEC-NOBS-01 @ AESObfuscator.&lt;init&gt; |
| 32 | LVL AESObfuscator.&lt;init&gt; | CIPHER-NOBS-00 | **MISUSE** | cascade | PBEKEYSPEC-NOBS-01 @ AESObfuscator.&lt;init&gt; |
| 32 | LVL AESObfuscator.&lt;init&gt; | IVPARAMETERSPEC-NOBS-00 | **MISUSE** | hardcoded_iv | — |
| 32 | LVL AESObfuscator.&lt;init&gt; | IVCHAINJUNCTION-NOBS-00 | **MISUSE** | cascade | IVPARAMETERSPEC-NOBS-00 @ AESObfuscator.&lt;init&gt; |
| 51 | whyoleg JdkPbkdf2SecretDerivation.deriveSecretToByteArrayBlocking | PBEKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | salt_loaded_from_storage | — |
| 51 | whyoleg JdkPbkdf2SecretDerivation.deriveSecretToByteArrayBlocking | SECRETKEYFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ deriveSecretToByteArrayBlocking |
| 72 | spongycastle X509CertificateObject.checkSignature | SIGNATURE-NOBS-02 | LEGIT_UNOBSERVABLE | pubkey_from_certificate | — |

Totais: MISUSE 8 · LEGIT_UNOBSERVABLE 17 · SPEC_DEFECT 4 · UNDETERMINED 0.

---

## 1. TLS do ktor (ids 2–11)

Quatro apps: vidyamusic (ktor 3.5.0), untis (3.1.3), beatgame e retrowars (1.6.0). As linhas do
`__LOC` batem com os fontes de cada versão (por exemplo `TLSClientHandshake.kt:338` no 1.6.0, `:362`
no 3.1.3, `:363` no 3.5.0, todas `doPhase`). `Keys.kt` e `cipher/GCMCipher.kt` são idênticos nas três
versões (diff vazio). Única discrepância: beatgame registra `Hashes.kt:23/:28`, uma linha abaixo de
`:24/:29` que o fonte 1.6.0 tem e que retrowars registra; é o mesmo `P_hash`.

A cadeia do handshake ECDHE (1.6.0; 3.x igual com deslocamento de linhas):

```kotlin
// TLSClientHandshake.kt:487-499 (1.6.0)
val clientKeys = KeyPairGenerator.getInstance("EC")!!.run { initialize(ECGenParameterSpec(curve.name)); generateKeyPair()!! }
val publicKey = clientKeys.public as ECPublicKey
val factory = KeyFactory.getInstance("EC")!!
val serverPublic = factory.generatePublic(ECPublicKeySpec(serverPoint, publicKey.params!!))!!   // :496
// TLSClientHandshake.kt:335-340
ECDHE -> KeyAgreement.getInstance("ECDH")!!.run {
    init(encryptionInfo.clientPrivate)
    doPhase(encryptionInfo.serverPublic, true)                                                   // :338
    generateSecret()!! }
// TLSClientHandshake.kt:315-319
masterSecret = masterSecret(SecretKeySpec(preSecret, serverHello.cipherSuite.hash.macName), clientSeed, serverHello.serverSeed) // :316
```

### id 8 — KEYFACTORY-NOBS-01 · SPEC_DEFECT (raiz)

`KeyFactorySpec.genPublic` (`KeyFactorySpec.mop:101-119`) lê `validateAny(SPECCED_KEY, keySpec)`. Os
produtores de `SPECCED_KEY` são só `X509EncodedKeySpecSpec.mop:83`, `SecretKeySpecSpec.mop:257` e
`PBEKeySpecSpec.mop:160`. O `ECPublicKeySpec` é construído em código tecido (`:496`) a partir do ponto
EC do `ServerKeyExchange`, que o cliente autentica com `Signature.verify` sobre randoms e parâmetros
(`:261-274`). Não há `.mop` para `ECPublicKeySpec` no conjunto; o `X509EncodedKeySpec`, que embrulha
bytes de rede do mesmo jeito, é creditado incondicionalmente. Uso correto de ECDHE, falta de produtor.

### id 6 — KEYAGREEMENT-NOBS-08 · SPEC_DEFECT (cascata)

`KeyAgreementSpec.dophase` (`:259-272`) lê `GENERATED_PUBLIC_KEY` do `serverPublic`, que `genPublic`
só grava se o spec for creditado. Raiz: id 8. `init1` sobre `clientKeys.private` não acusa nas mesmas
execuções, então o único elo quebrado é a chave do servidor.

### id 7 — SECRETKEYSPEC-NOBS-00 @ handleServerDone · SPEC_DEFECT (cascata)

`preSecret` é o próprio array devolvido por `generateSecret()` (mesma identidade). `KeyAgreementSpec.gs1`
(`:294-299`) só grava `PREPARED_KEY_MATERIAL` se `conforms` (campo, `:61`), que o `dophase` derrubou.
Raiz: id 8. Corrigido o produtor, a cadeia fecharia.

### id 4 — SECRETKEYSPEC-NOBS-00 @ masterSecret · LEGIT_UNOBSERVABLE

```kotlin
// Keys.kt:65-72
internal fun masterSecret(preMasterSecret: SecretKey, clientRandom: ByteArray, serverRandom: ByteArray): SecretKeySpec =
    SecretKeySpec(PRF(preMasterSecret, MASTER_SECRET_LABEL, clientRandom + serverRandom, 48), preMasterSecret.algorithm)
// Hashes.kt:36
    return result.copyOf(requiredLength)
```

O material é a saída do PRF do TLS 1.2 (RFC 5246 §8.1): um array novo de `copyOf` sobre
concatenações de `Mac.doFinal`. Os únicos produtores de `PREPARED_KEY_MATERIAL` são `getEncoded()` de
chave de origem observada (`SecretKeySpec.mop`, `KeySpec.mop`) e `KeyAgreement.generateSecret`
(`KeyAgreementSpec.mop:294-316`). Mesmo com o id 8 corrigido este site continuaria acusando: é o
limite de uma derivação de chave (KDF) feita à mão, não um defeito do caminho.

### ids 3 e 5 — SECRETKEYSPEC-NOBS-01 @ clientKey/serverKey · LEGIT_UNOBSERVABLE

```kotlin
// Keys.kt:37-42 (serverKey em :30-35, offset + keyStrength)
internal fun ByteArray.clientKey(suite: CipherSuite): SecretKeySpec = SecretKeySpec(this, 2 * suite.macStrengthInBytes, suite.keyStrengthInBytes, suite.jdkCipherName.substringBefore("/"))
// TLSClientHandshake.kt:40-50 — this = keyMaterial(masterSecret, serverSeed + clientSeed, ...) = PRF(masterSecret, "key expansion", ...)
```

O `this` é o key_block derivado pelo PRF a partir do master secret. Mesma razão do id 4.

### ids 10 e 11 — CIPHER-NOBS-00 · LEGIT_UNOBSERVABLE (cascata)

`val key = keyMaterial.clientKey(suite)` (`GCMCipher.kt:67`) / `serverKey` (`:98`). O `SecretKeySpec`
não ganhou `GENERATED_KEY` porque sua leitura deu NOT_OBSERVED (`SecretKeySpecSpec.mop:187-190`).
Raiz: ids 3/5.

### ids 10 e 11 — GCMPARAMETERSPEC-NOBS-00 · LEGIT_UNOBSERVABLE

```kotlin
// GCMCipher.kt:67-74 (cifrar)
val key = keyMaterial.clientKey(suite)
val fixedIv = keyMaterial.clientIV(suite)          // copyOfRange do key_block
val iv = fixedIv.copyOf(suite.ivLength)
iv.set(suite.fixedIvLength, recordIv)              // recordIv = outputCounter (GCMCipher.kt:25-26)
val gcmSpec = GCMParameterSpec(suite.cipherTagSizeInBytes * 8, iv)   // :73
cipher.init(Cipher.ENCRYPT_MODE, key, gcmSpec)                       // :74
// GCMCipher.kt:39-51, 98-105 (decifrar): recordIv = packet.readLong() — nonce_explicit lido do registro
```

Nonce de 12 bytes = fixed IV de 4 bytes do key_block ‖ 8 bytes. Na cifragem os 8 bytes são o contador
de registros `outputCounter`, que incrementa a cada registro (`:34`) sob uma chave de sessão nova a cada
handshake: único, que é o que o GCM exige (RFC 5288 §3). Na decifração vêm do registro recebido. A
leitura `RANDOMIZED` (`GCMParameterSpecSpec.mop:62-84`) não admite um nonce determinístico e único; não
há reuso nem previsibilidade explorável. Não é mau uso.

### ids 10 e 11 — IVCHAINJUNCTION-NOBS-01 · LEGIT_UNOBSERVABLE (cascata)

`IvChainJunction.use` (`:138-141`, leitura GCM em `:192-202`) pede `PREPARED_GCM`, gravado só por
`GCMParameterSpecSpec.@match` (`:179-181`) quando o `c1` conformou. Raiz: o GCMPARAMETERSPEC do mesmo
método.

### id 2 — MAC-NOBS-00 @ P_hash · LEGIT_UNOBSERVABLE (caminho dominante)

```kotlin
// Hashes.kt:22-31 (1.6.0)
while (result.size < requiredLength) {
    mac.reset(); mac.init(secretKey); mac.update(A); A = mac.doFinal()   // :24
    mac.reset(); mac.init(secretKey); mac.update(A); mac.update(seed)    // :29
```

`MacSpec.i1` (`:171-187`) lê `validateAny(GENERATED_KEY, key)`. Por handshake há quatro PRFs: um com o
`SecretKeySpec(preSecret)` (raiz id 8, SPEC_DEFECT) e três com o `masterSecret` (`keyMaterial`,
`finished`, `serverFinished`; raiz id 4, LEGIT). As linhas deduplicadas do CSV não separam os dois
caminhos. Classifiquei pelo dominante, que é também o que continuaria acusando depois de corrigir o
produtor; confiança média.

### id 9 — TRUSTMANAGERFACTORY-NOBS-00 · LEGIT_UNOBSERVABLE

```kotlin
// TLSConfigBuilder.kt:151-157 (1.6.0); :157-163 no 3.x
val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())!!
factory.init(null as KeyStore?)
```

`null` = repositório de CAs do sistema; `PredicateStore.validate` responde NOT_OBSERVED para `null`
(`PredicateStore.java:343-345`). Fora desta leitura: o cliente TLS do ktor 1.6.0 (beatgame, retrowars)
não verifica hostname. Não existe `verifyHostnameInCertificate` no 1.6.0; no 3.x existe
(`TLSClientHandshake.kt:260-262`). É uma fraqueza real dessa versão, mas não é o que o NOBS-00 cobra.

## 2. ktor Nonce (id 12) — SECURERANDOM-NOBS-00 · SPEC_DEFECT (defeito do weaver exposto pelo `.mop`)

```kotlin
// ktor-utils-jvm 1.6.0, Nonce.kt
val secureInstance = lookupSecureRandom()                      // :37 → getInstanceOrNull("NativePRNGNonBlocking") falha no Android → SecureRandom.getInstance("SHA1PRNG") :106
val weakRandom = SecureRandom.getInstance(SHA1PRNG)            // :38
weakRandom.setSeed(secureInstance.generateSeed(secureBytes.size))   // :43
secureInstance.nextBytes(secureBytes)                          // :48
weakRandom.setSeed(secureInstance.generateSeed(secureBytes.size))   // :63
weakRandom.setSeed(secureBytes)                                // :66
```

As três sementes vêm de um `SecureRandom` observado (`generateSeed` e `nextBytes`), então a
proveniência é correta. Por que não carregam `RANDOMIZED`: o monitor do `secureInstance` foi a fail
logo no `getInstance`. As linhas de retrowars mostram `SECURERANDOM-ORDER-00 ev=g2 @ Nonce.kt:106`,
depois `ev=genSeed @ :43/:63` e `ev=next2 @ :48`. O `@fail` (`SecureRandomSpec.mop:370-377`) zera
`stagedGeneratedSeed` e `stagedNextBytes` antes que o `@match2` (`:392-401`) grave `RANDOMIZED`.

Mecanismo: `g1` é `call(getInstance(String)) && args(alg)` e `g2` é
`call(getInstance(String, ..)) && args(alg, *)` (`:113-127`). Em AspectJ, `args(alg, *)` exige aridade
2. No weaver dexlib2, um `args(...)` sem tipo concreto é um coletor que sempre casa
(`PointcutMatcher.java:268-271`, `ArgsPC.java:49-56`), e o `..` final aceita zero argumentos. Assim,
`getInstance(String)` dispara `g1` (start→init) e em seguida `g2` (init→fail). Contraprova: dankchat
(ktor 3.5.0) obtém o gerador forte por `getInstanceStrong` (`g3`) e não acusa NOBS no mesmo
`setSeed(generateSeed(...))`. O mesmo par `g2` com `args(alg, *)` existe em
`TrustManagerFactorySpec.mop:87-90` (explica o TRUSTMANAGERFACTORY-ORDER-00 ev=g2 dos quatro apps
ktor) e em `KeyManagerFactorySpec.mop:56-57`.

## 3. Play Services Ads 25.3.0, `zzbbe.zzb` (id 31) — apenas bytecode

```text
// zzbbz (inicialização), bytecode do APK passportreader
ldc "GpeoZNfYB0xbX4XrY9tptE+P6lGr6tGbtd6Fg+9sjdQ="  → zzazp.zzb = android.util.Base64.decode
ByteBuffer.wrap(bytes, 4, 16).get(new byte[16]); for i<16: b[i] ^= 68   → putfield zzg
... zzf.zzb(zzg, "<blob Base64 embutido>") → escreve <cacheDir>/1762298034389.jar
// zzbbe.zzb(byte[] key, String data)
decoded = Base64.decode(data); iv = decoded[0..16); ct = decoded[16..)
new SecretKeySpec(key, "AES")                 // bc@65-75   (linha 9)
cipher.init(2, keySpec, new IvParameterSpec(iv))  // bc@89-107 (linha 10)
```

Os dois chamadores de `zzbbe.zzb` (`zzbbz` e `zzbdl.zzc`) passam `zzbbz.zzg()`.

- **SECRETKEYSPEC-NOBS-00 · MISUSE (hardcoded_key)**: a chave AES-128 é uma constante embutida
  desofuscada por XOR. O uso é decifrar código embutido do próprio SDK (ofuscação), então o impacto
  prático é baixo, mas a chave é constante.
- **CIPHER-NOBS-00 · MISUSE (cascata)**: raiz o site acima.
- **IVPARAMETERSPEC-NOBS-00 · LEGIT_UNOBSERVABLE (iv_from_ciphertext)**: o IV são os 16 primeiros bytes
  do texto cifrado; a cifragem (`zza`) usa `init(1, key, null)` e antepõe `getIV()`. O blob é constante,
  então o IV também é, mas a escolha dele foi do lado cifrador, fora do app.

## 4. LVL `AESObfuscator` vendorizado em myexpenses (id 32) — MISUSE em todos os 6 códigos

```java
// PlayLicensingOrig/src/com/google/android/vending/licensing/AESObfuscator.java
private static final byte[] IV = { 16, 74, 71, -80, 32, 101, -47, 72, 117, -14, 0, -29, 70, 65, -12, 74 }; // :42-43
SecretKeyFactory factory = SecretKeyFactory.getInstance(KEYGEN_ALGORITHM);                                  // :57
KeySpec keySpec = new PBEKeySpec((applicationId + deviceId).toCharArray(), salt, 1024, 256);                 // :59
SecretKey tmp = factory.generateSecret(keySpec);                                                            // :60
SecretKey secret = new SecretKeySpec(tmp.getEncoded(), "AES");                                              // :61
mEncryptor.init(Cipher.ENCRYPT_MODE, secret, new IvParameterSpec(IV));                                      // :63
mDecryptor.init(Cipher.DECRYPT_MODE, secret, new IvParameterSpec(IV));                                      // :65
```

```kotlin
// myExpenses/.../di/LicenceModule.kt:57-83 e :39-43
AESObfuscator(byteArrayOf(-1, -124, -4, -59, -52, 1, -97, -32, 38, 59, 64, 13, 45, -104, -3, -92, -56, -49, 65, -25),
              application.packageName, deviceId)   // deviceId = Settings.Secure.ANDROID_ID
```

- **PBEKEYSPEC-NOBS-01 · hardcoded_salt**: sal de 20 bytes literais, igual em toda instalação; a senha
  é `packageName + ANDROID_ID`, nada secreta; 1024 iterações (PBEKEYSPEC-CONSTR-00 na mesma linha).
- **SECRETKEYFACTORY-NOBS-00, SECRETKEYSPEC-NOBS-00, CIPHER-NOBS-00 · cascata**: raiz o PBEKeySpec. O
  `c1` não grava `SPECCED_KEY` (`PBEKeySpecSpec.mop:158-161`), `gen` não grava `GENERATED_KEY`
  (`SecretKeyFactorySpec.mop:106-109`), `getEncoded` não vira `PREPARED_KEY_MATERIAL`
  (`SecretKeySpec.mop:119-148`, `KeySpec.mop:75-108`) e a chave do `Cipher.init` fica sem origem.
- **IVPARAMETERSPEC-NOBS-00 · hardcoded_iv**: `static final byte[] IV` em AES/CBC, nos dois `init`
  (`:63` e `:65`).
- **IVCHAINJUNCTION-NOBS-00 · cascata**: raiz o IvParameterSpec; `IvParameterSpec.@match` (`:152-154`)
  não grava `PREPARED_IV`.

Quem tiver o APK e o ANDROID_ID (legível por qualquer app do mesmo assinante, e não secreto) reconstrói
a chave que protege o estado de licença em `SharedPreferences`.

## 5. whyoleg cryptography 0.6.0 em securecamera (id 51) — LEGIT_UNOBSERVABLE

```kotlin
// cryptography-provider-jdk-jvm-0.6.0/jvmMain/algorithms/JdkPbkdf2.kt:39-47
override fun deriveSecretToByteArrayBlocking(input: ByteArray): ByteArray {
    val spec = PBEKeySpec(input.decodeToString(throwOnInvalidSequence = true).toCharArray(), salt, iterations, outputSizeBits) // :40
    return factory.use { it.generateSecret(spec).encoded }                                                                    // :46
}
// app: security/schemes/HardwareBackedEncryptionScheme.kt:69-73 (e :143-147, SoftwareEncryptionScheme.kt:104-109)
salt = hashedPin.salt.toByteArray()
// security/pin/PinCrypto.kt:21,32 — val salt = CryptographyRandom.nextBytes(16); HashedPin(..., salt.base64EncodeUrlSafe())
```

- **PBEKEYSPEC-NOBS-01 · salt_loaded_from_storage**: o sal é aleatório por instalação, gerado no
  cadastro do PIN, persistido como string Base64 e re-encodado em um `byte[]` novo a cada derivação.
  Identidade perdida por construção. Detalhe lateral: o mesmo sal serve ao hash Argon2 do PIN e ao
  PBKDF2.
- **SECRETKEYFACTORY-NOBS-00 · cascata**: raiz o PBEKeySpec do mesmo método.

## 6. Verificação de assinatura com chave de certificado (ids 0, 1, 72) — LEGIT_UNOBSERVABLE

`SignatureSpec.i4` (`:184-200`) lê `GENERATED_PUBLIC_KEY`. Os produtores são só `KeyPair.getPublic`
(`KeyPairSpec.mop:123-126`) e `KeyFactory.generatePublic` creditado (`KeyFactorySpec.mop:101-119`).
Nenhuma spec, nem a regra CrySL, credita uma chave extraída de certificado. Seria errado creditá-la sem
condição, porque o que a torna confiável é a validação da cadeia, não a origem do objeto.

**droid_scep (bcpkix 1.79 via jscep 3.0.1; APK sem linhas, "Unknown Source")**. O bytecode de
`JcaContentVerifierProviderBuilder$1.get` confirma:

```java
// bcpkix-jdk18on-1.79 .../JcaContentVerifierProviderBuilder.java:99-108
sig = helper.createSignature(algorithm);
sig.initVerify(certificate.getPublicKey());                          // $1.get  (id 1)
Signature rawSig = createRawSig(algorithm, certificate.getPublicKey()); // → :272 rawSig.initVerify(publicKey) (id 0)
```

Os chamadores no jscep são `Client.verifyRA` (`:301`, certificado da CA), `Client.isSelfSigned`
(`:644`) e `SignedDataUtils.isSignedBy` (`:71`). Todos passam um `X509Certificate`, vindo do servidor
SCEP ou autoassinado pelo app sobre um `KeyPair` gerado; neste caso o certificado reconvertido devolve
outro objeto `PublicKey`. Fora desta leitura: `ScepClient.java:111-112` aceita qualquer CA
(`OptimisticCertificateVerifier`) quando o fingerprint está vazio e usa MD5 quando não está. Confiança
média, porque o chamador exato não foi fixado.

**passportreader (spongycastle prov 1.58.0.0)**.

```java
// X509CertificateObject.java:791-809
X509SignatureUtil.setSignatureParameters(signature, params);   // :805 (linha registrada)
signature.initVerify(key);                                     // :807
```

O `__LOC` diz `:805`; o bytecode tem um único `initVerify(PublicKey)` no método, então o site é
inequívoco. O app faz `Security.insertProviderAt(BouncyCastleProvider(), 1)` (`MainApplication.kt:25`),
e daí `CertificateFactory`/`CertPathValidator` do processo resolvem para o spongycastle. No validador
PKIX a chave é `trust.getCAPublicKey()` (`PKIXCertPathValidatorSpi.java:232`) ou `cert.getPublicKey()`
(`CertPathValidatorUtilities.java:1226`). O próprio `getPublicKey` usa
`BouncyCastleProvider.getPublicKey(SubjectPublicKeyInfo)` (`X509CertificateObject.java:530-540`), sem
`KeyFactory` JCA. A validação PKIX do próprio app (`MainActivity.kt:339-383`) só roda depois de ler um
passaporte por NFC, o que é improvável nas execuções. Em qualquer caminho a chave sai de um
certificado. Confiança média.

## Padrões transversais

1. **Duplo casamento `g1`/`g2` no dexlib2.** `call(X.getInstance(String, ..)) && args(alg, *)` casa
   `getInstance(String)`, porque o matcher não impõe aridade a um `args` sem tipo. O monitor vai a fail
   no segundo evento e descarta o que ia gravar. Afeta `SecureRandomSpec`, `TrustManagerFactorySpec` e
   `KeyManagerFactorySpec`; qualquer `RANDOMIZED` derivado de um `SecureRandom.getInstance("X")`
   observado se perde.
2. **KDF escrita à mão.** O PRF do TLS e, em geral, saídas de HMAC nunca carregam
   `preparedKeyMaterial`, então toda a pilha de registros do TLS do ktor acusa por construção.
3. **Nonce determinístico de protocolo.** A exigência `randomized` do GCM/IV não distingue um nonce
   único por contador (TLS) de um IV fixo. Aqui ele é único; no AESObfuscator, fixo.
4. **Chave pública de certificado** nunca satisfaz `generatedPubkey` (bc, spongycastle).
