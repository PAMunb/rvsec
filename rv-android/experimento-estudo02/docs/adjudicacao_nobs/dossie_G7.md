# Dossiê G7 — código criptográfico dos próprios apps

37 sítios, 19 métodos, 11 apps. Fontes em `rvsec-dataset/repos/<apk>/` (HEAD do build); a
biblioteca `org.flyve.inventory` vem só como AAR local e foi lida em bytecode. Specs lidas em
`rvsec-mop/src/main/resources/jca_android/`.

## Tabela de veredictos

| id | método | código | categoria | mecanismo | raiz |
|---|---|---|---|---|---|
| 47 | photok `KeyGen.derivePasswordKeyEncryptionKey` | PBEKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | salt_from_storage | — |
| 47 | 〃 | SECRETKEYFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ KeyGen |
| 47 | 〃 | SECRETKEYSPEC-NOBS-00 | **SPEC_DEFECT** | getencoded_producer_not_woven | — |
| 48 | photok `KeyGen.generateVaultMasterKey` | SECRETKEYSPEC-NOBS-00 | **SPEC_DEFECT** | randomized_not_accepted_as_key_material | — |
| 49 | photok `PasswordVaultProtectionHandler.create` | CIPHER-NOBS-00 | **SPEC_DEFECT** | cascade | SECRETKEYSPEC-NOBS-00 @ KeyGen |
| 50 | photok `PasswordVaultProtectionHandler.unlock` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ KeyGen |
| 50 | 〃 | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_storage | — |
| 50 | 〃 | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_unwrap | — |
| 55 | dsub2000 `KeyStoreUtil.decrypt` | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 56 | treehouses `ssh.Encryptor.encrypt` | SECRETKEYSPEC-NOBS-00 | **MISUSE** | adhoc_weak_password_kdf | — |
| 56 | 〃 | IVPARAMETERSPEC-NOBS-00 | **MISUSE** | iv_derived_from_password_kdf | SECRETKEYSPEC @ Encryptor |
| 56 | 〃 | IVCHAINJUNCTION-NOBS-00 | **MISUSE** | cascade | IVPARAMETERSPEC @ Encryptor |
| 56 | 〃 | CIPHER-NOBS-00 | **MISUSE** | cascade | SECRETKEYSPEC @ Encryptor |
| 57 | tokn `KeystoreManager.decrypt` | CIPHER-NOBS-00 | **SPEC_DEFECT** | keystore_entry_route_no_producer | — |
| 57 | 〃 | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 57 | 〃 | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC @ decrypt |
| 58 | tokn `KeystoreManager.encrypt` | CIPHER-NOBS-00 | **SPEC_DEFECT** | keystore_entry_route_no_producer | — |
| 62 | cry.otp `HOTP.hmac_sha1` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_user_shared_secret | — |
| 62 | 〃 | MAC-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC @ HOTP |
| 63 | cry.otp `TOTP.hmac_sha` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_user_shared_secret | — |
| 63 | 〃 | MAC-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC @ TOTP |
| 64 | freeotp `EncryptedKey.decrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ MasterKey.decrypt |
| 64 | 〃 | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_unwrap | — |
| 65 | freeotp `MasterKey.<init>` | SECRETKEYSPEC-NOBS-00 | **SPEC_DEFECT** | randomized_not_accepted_as_key_material | — |
| 66 | freeotp `MasterKey.decrypt` | PBEKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | copy_loses_identity | — |
| 66 | 〃 | SECRETKEYFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ MasterKey.decrypt |
| 67 | flyve `CryptoUtil.encrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | X509ENCODEDKEYSPEC @ stringToPublicKey |
| 68 | flyve `CryptoUtil.stringToPublicKey` | X509ENCODEDKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | copy_loses_identity | — |
| 68 | 〃 | KEYFACTORY-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | X509ENCODEDKEYSPEC @ stringToPublicKey |
| 71 | redreader `General.parseConfig` | SECRETKEYSPEC-NOBS-00 | **MISUSE** | key_derived_from_public_data | — |
| 71 | 〃 | IVPARAMETERSPEC-NOBS-00 | **MISUSE** | constant_zero_iv | — |
| 71 | 〃 | CIPHER-NOBS-00 | **MISUSE** | cascade | SECRETKEYSPEC @ parseConfig |
| 73 | metadataremover `MainViewModel.<clinit>` | SECURERANDOM-NOBS-01 | **MISUSE** | hardcoded_seed | — |
| 74 | vault `Encryption.getDirHash` | PBEKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | salt_from_storage | — |
| 74 | 〃 | SECRETKEYFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | PBEKEYSPEC-NOBS-01 @ getDirHash |
| 75 | photoprism `ParseEnteredKeyUseCase.getIssuerPublicKey$lambda$0` | X509ENCODEDKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | embedded_public_key | — |
| 75 | 〃 | KEYFACTORY-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | X509ENCODEDKEYSPEC @ getIssuerPublicKey |

Contagem: LEGIT_UNOBSERVABLE 23 · MISUSE 8 · SPEC_DEFECT 6 · UNDETERMINED 0.

## O que as leituras pedem (resumo das specs)

- `SecretKeySpecSpec.c1` (`SecretKeySpecSpec.mop:110-119`) valida `PREPARED_KEY_MATERIAL` sobre o
  `byte[]`. Esse predicado só é escrito por `SecretKeySpec.mop:145` (`SecretKey+.getEncoded()`),
  `KeySpec.mop:105` (`Key+.getEncoded()`) e `KeyAgreementSpec.mop:298,315`. Bytes de SecureRandom
  **não** servem, e o próprio `.mop` documenta isso (`:79-91`).
- `PBEKeySpecSpec.c1` (`:148-157`), `IvParameterSpec.c1` (`:65-76`), `GCMParameterSpecSpec.c1`
  (`:62-84`) e `SecureRandomSpec.c2` (`:95-107`) validam `RANDOMIZED` sobre o array. Os únicos
  produtores são `SecureRandomSpec.mop:384,394,398` (`nextBytes`/`generateSeed`).
- `CipherSpec.i2` (`:199-233`) e `MacSpec.i1` (`:171-187`) leem `GENERATED_KEY` (e, no Cipher,
  pub/priv). Os produtores são `KeyGeneratorSpec:223`, `KeyStoreSpec:200` (só `getKey`),
  `SecretKeyFactorySpec:108,122` e `SecretKeySpecSpec:256`, todos só no ramo conforme.
- `SecretKeyFactorySpec.gen` e `KeyFactorySpec.genPublic` leem `SPECCED_KEY` com `validateAny`;
  quem escreve são `PBEKeySpecSpec:160`, `SecretKeySpecSpec:257` e `X509EncodedKeySpecSpec:83`, todos
  condicionados ao próprio SATISFIED.
- `SECURERANDOM-NOBS-01` é o construtor `new SecureRandom(byte[] seed)`: lê `RANDOMIZED` **sobre a
  semente**, não sobre o gerador.

## Achado sistemático: `SecretKey.getEncoded()` não é tecido

No APK instrumentado do photok (`APKS_INSTRUMENTED_jca_android_dexlib2/dev.leonlatsch.photok_62.apk`,
convertido para `g7jars/photok_instr.jar`), a chamada em `KeyGen.derivePasswordKeyEncryptionKey`
continua crua:

```
74: invokestatic  MonitorWrappers.javax_crypto_SecretKeyFactory_generateSecret(...)
77: invokeinterface javax/crypto/SecretKey.getEncoded:()[B      <- sem advice
98: invokestatic  MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event(...)
```

`SecretKeySpec_e1Event` existe no monitor, mas nenhuma classe do app o chama. O mesmo acontece em
`PasswordVaultProtectionHandler.create` (`vmk.encoded`), no vault (`Encryption.getDirHash`) e no
freeotp (`MasterKey.<init>`). No vault, o único ponto que chama `KeySpec_ge1Event` é
`com.google.crypto.tink.subtle.PrfHmacJce`, onde o owner do invoke é literalmente
`java/security/Key`. Conclusão: o weaver dexlib2 só aplica `Key+.getEncoded()` e
`SecretKey+.getEncoded()` quando o owner declarado é o próprio `java.security.Key`. A afirmação do
comentário em `SecretKeySpec.mop:103-118` (o `T+` casaria receptores `SecretKey`/`SecretKeySpec`)
não se confirma no APK da campanha. O efeito é que a ponte `getEncoded → PREPARED_KEY_MATERIAL`
praticamente nunca dispara em código compilado com tipo estático `SecretKey`, `PrivateKey` ou
`PublicKey`, e isso deve afetar outros grupos.

---

## photok — `KeyGen` (47, 48) e `PasswordVaultProtectionHandler` (49, 50)

```kotlin
// KeyGen.kt:29-47
fun generateVaultMasterKey(): SecretKey {
    val keyBytes = ByteArray(32)
    SecureRandom().nextBytes(keyBytes)
    return SecretKeySpec(keyBytes, "AES")                       // :32
}
fun derivePasswordKeyEncryptionKey(password, salt, kdf, kdfIterations, keySize): SecretKey {
    val factory = SecretKeyFactory.getInstance(kdf.value)        // PBKDF2WithHmacSHA256
    val spec = PBEKeySpec(password.toCharArray(), salt, kdfIterations, keySize)   // :43
    val keyBytes = factory.generateSecret(spec).encoded          // :44
    return SecretKeySpec(keyBytes, "AES")                        // :46
}
// PasswordVaultProtectionHandler.kt
// unlock: salt = Base64.decode(params.salt) (:62); iv = Base64.decode(params.iv) (:69)
//         init(DECRYPT_MODE, kek, IvParameterSpec(iv)) (:70); SecretKeySpec(cipher.doFinal(wrappedVMK)) (:74)
// create: salt/iv = ByteArray(..).also { SecureRandom().nextBytes(it) } (:79-80), 100 000 iterações
//         init(ENCRYPT_MODE, kek, IvParameterSpec(iv)) (:104)
```

**Como separar os caminhos.** Em cada uma das 47 runs, a ordem das linhas é: `KeyGen.kt:32` →
`KeyGen.kt:46` → `:104` → `KeyGen.kt:43` → `:44` → `:70` → `:74`. Ou seja, o create emite `:46` e
`:104` **sem** emitir `:43` nem `:44`: o salt aleatório do create é observado (assim como o IV do
create, já que não há IVPARAMETERSPEC-NOBS em `:104`), e a cadeia só quebra no `.encoded`. A chave
PBKDF2 do Android 11 tem `getAlgorithm() = "PBKDF2WithHmacSHA256"` (`aosp-bc-android11/PBEPBKDF2.java:458`,
`BCPBEKey.java:61-63`), que casaria com o `ensure`. O que falta é o evento, que não foi tecido (achado
sistemático acima). `:43` e `:44` só aparecem no unlock seguinte, com salt lido do armazenamento.

- **PBEKEYSPEC-NOBS-01 (:43)**: LEGIT_UNOBSERVABLE, `salt_from_storage`. Salt Base64 do
  `VaultProtection` persistido, originalmente de `SecureRandom`.
- **SECRETKEYFACTORY-NOBS-00 (:44)**: LEGIT_UNOBSERVABLE, cascata de `:43`.
- **SECRETKEYSPEC-NOBS-00 (:46)**: SPEC_DEFECT, `getencoded_producer_not_woven`. É um defeito do
  weaver, não do texto da spec. As 4 linhas extras (de 51) vêm de um segundo processo, só com
  unlock, e são cascata do salt.
- **SECRETKEYSPEC-NOBS-00 (:32)**: SPEC_DEFECT, `randomized_not_accepted_as_key_material`. São 256 bits
  de `SecureRandom`, sem problema de segurança. A spec recusa por decisão documentada.
- **CIPHER-NOBS-00 (create :104)**: SPEC_DEFECT por cascata de `:46`.
- **CIPHER-NOBS-00 (unlock :70)**: LEGIT_UNOBSERVABLE por cascata de `:43`.
- **IVPARAMETERSPEC-NOBS-00 (unlock :70)**: LEGIT_UNOBSERVABLE, `iv_from_storage`.
- **SECRETKEYSPEC-NOBS-00 (unlock :74)**: LEGIT_UNOBSERVABLE, `key_from_unwrap`. É a VMK decifrada.

## dsub2000 — `KeyStoreUtil.decrypt` (55)

```java
byte[] decodedBytes = Base64.decode(encryptedString, Base64.NO_WRAP);   // :121
byte[] ivBytes = new byte[ivLength];
System.arraycopy(decodedBytes, 1, ivBytes, 0, ivLength);               // :127
IvParameterSpec ivParamSpec = new IvParameterSpec(ivBytes);            // :135
cipher.init(Cipher.DECRYPT_MODE, key, ivParamSpec);
```

No `encrypt` (`:85,91-94`), o IV é gerado pelo provider do AndroidKeyStore e gravado no prefixo do
blob. **IVPARAMETERSPEC-NOBS-00**: LEGIT_UNOBSERVABLE, `iv_from_ciphertext`. A chave vem de
`KeyStore.getKey` e é creditada.

## treehouses — `ssh.Encryptor.encrypt` (56)

```kotlin
SecureRandom.getInstance("SHA1PRNG").nextBytes(salt)          // :65 (salt de 8 bytes, PubKeyUtils.kt:44)
pw = computePw(iterations, pw, salt, shaDigest)               // 1000 × SHA-256(pw||salt), PubKeyUtils.kt:47
System.arraycopy(pw, 0, key, 0, 16)                            // :75
System.arraycopy(pw, 16, iv, 0, 16)                            // :76
cipher.init(ENCRYPT_MODE, SecretKeySpec(key, "AES"), IvParameterSpec(iv))   // :81-84
```

O código (herdado do ConnectBot) cifra a chave SSH privada com a senha do usuário. A chave depende de
um segredo, mas é derivada por um KDF caseiro de 1000 iterações de SHA-256, abaixo do mínimo de
10 000 que a própria regra PBEKeySpec exige. O IV é a outra metade do mesmo digest.

- **SECRETKEYSPEC-NOBS-00 (:83)**: MISUSE, `adhoc_weak_password_kdf`, confiança média.
- **IVPARAMETERSPEC-NOBS-00 (:84)**: MISUSE, `iv_derived_from_password_kdf`, confiança baixa. Como o
  salt é novo a cada cifragem, o IV é único e imprevisível sem a senha. O dano concreto é o do KDF,
  por isso a raiz aponta para a chave.
- **IVCHAINJUNCTION-NOBS-00 (:81)**: MISUSE por cascata do IV.
- **CIPHER-NOBS-00 (:81)**: MISUSE por cascata da chave.

## tokn — `KeystoreManager.encrypt/decrypt` (57, 58)

```kotlin
private fun getOrCreateKey(): SecretKey {
    if (!keystore.containsAlias(KEY_ALIAS)) { ...; keyGen.generateKey() }          // retorno descartado
    return (keystore.getEntry(KEY_ALIAS, null) as KeyStore.SecretKeyEntry).secretKey   // :88
}
// encrypt: cipher.init(ENCRYPT_MODE, key) (:55); iv = cipher.iv
// decrypt: iv = combined.copyOfRange(0, 12) (:64); init(DECRYPT_MODE, key, GCMParameterSpec(128, iv)) (:68)
```

A chave é uma AES-256 do AndroidKeyStore. `KeyStoreSpec.ge1` (`:106-108`) observa `getEntry` mas não
liga nada, e só `gk1` (`getKey`, `:114-122`) marca a chave que sai. A rota
`getEntry → SecretKeyEntry.getSecretKey()` não tem produtor, embora seja uma chamada tecida.

- **CIPHER-NOBS-00 (:55, :68)**: SPEC_DEFECT, `keystore_entry_route_no_producer`.
- **GCMPARAMETERSPEC-NOBS-00 (:68)**: LEGIT_UNOBSERVABLE, `iv_from_ciphertext`.
- **IVCHAINJUNCTION-NOBS-01 (:68)**: LEGIT_UNOBSERVABLE por cascata (sem `PREPARED_GCM`).

## cry.otp — `HOTP.hmac_sha1` (62) e `TOTP.hmac_sha` (63)

```java
SecretKeySpec macKey = new SecretKeySpec(keyBytes, "RAW");   // HOTP.java:32 / TOTP.java:46
hmacSha1.init(macKey);
```

`keyBytes` é o segredo OTP em hex digitado pelo usuário em `ProfileSetup` (`:72,137,153,219`), lido
do banco (`Profiles.java:203`) e passado por `Home.java:77,101`. É o segredo compartilhado do
protocolo (RFC 4226/6238).

- **SECRETKEYSPEC-NOBS-00**: LEGIT_UNOBSERVABLE, `key_from_user_shared_secret`. O algoritmo "RAW" também
  tira o `conforms`.
- **MAC-NOBS-00**: LEGIT_UNOBSERVABLE por cascata.

## freeotp — `MasterKey` (65, 66) e `EncryptedKey.decrypt` (64)

```java
// MasterKey.java
byte[] raw = new byte[pwd.getEncoded().length];
new SecureRandom().nextBytes(raw);
SecretKey key = new SecretKeySpec(raw, "AES");                          // :43
mSalt = spec.getSalt();                                                 // :48  (clone)
return decrypt(new PBEKeySpec(pwd.toCharArray(), mSalt, mIterations, mSalt.length * 8));  // :72
// EncryptedKey.java
cipher.init(Cipher.ENCRYPT_MODE, key);                                  // :51
cipher.init(Cipher.DECRYPT_MODE, key, ap);                              // :57
return new SecretKeySpec(cipher.doFinal(mCipherText), mToken);          // :59
```

`TokenPersistence.provision` (`:87,96`) chama `MasterKey.generate(password)` e logo depois
`mk.decrypt(password)`, sobre o mesmo objeto em memória. Como `PBEKeySpec.getSalt()` devolve
`salt.clone()`, `mSalt` já não é o array marcado. No `restore` (`:153-160`), o `MasterKey` é
desserializado pelo Gson. As linhas saem no mesmo segundo que `MasterKey.<init>:43`, o que aponta
para o provision.

- **SECRETKEYSPEC-NOBS-00 (MasterKey:43)**: SPEC_DEFECT, `randomized_not_accepted_as_key_material`.
- **PBEKEYSPEC-NOBS-01 (MasterKey:72)**: LEGIT_UNOBSERVABLE, `copy_loses_identity` (e armazenamento, no restore).
- **SECRETKEYFACTORY-NOBS-00 (MasterKey:64)**: LEGIT_UNOBSERVABLE por cascata.
- **CIPHER-NOBS-00 (EncryptedKey:51, :57)**: LEGIT_UNOBSERVABLE por cascata de MasterKey:72. Mesmo com
  o salt observado, `GENERATED_KEY(pwd, PBKDF2withHmacSHA512)` contra uma Cipher AES daria
  CIPHER-CONSTR-00, como já ocorre em `EncryptedKey.encrypt:42`.
- **SECRETKEYSPEC-NOBS-00 (EncryptedKey:59)**: LEGIT_UNOBSERVABLE, `key_from_unwrap`.

## flyve inventory — `CryptoUtil` (67, 68), em bytecode

Não há fonte: a biblioteca vem como `app/libs/inventory-release-v1.6.1.aar`, lida em
`inventory-release-v1.6.1/classes.jar`. As LineNumberTable conferem com o `__LOC`: 83 é o `init`,
108 o `X509EncodedKeySpec` e 110 o `generatePublic`.

```
OperatingSystem.getSSHKey: map = CryptoUtil.generateKeyPair()      // RSA-2048 novo; Base64(publicKey.getEncoded())
                           CryptoUtil.encrypt("Test message...", map.get("publicKey"))
CryptoUtil.stringToPublicKey: keyBytes = Base64.decode(s, 0)       // 107
                              spec = new X509EncodedKeySpec(keyBytes)        // 108
                              KeyFactory.getInstance("RSA").generatePublic(spec)  // 110
```

- **X509ENCODEDKEYSPEC-NOBS-00**: LEGIT_UNOBSERVABLE, `copy_loses_identity`. A ida e volta pelo Base64
  gera outro array, e a chave é pública.
- **KEYFACTORY-NOBS-01** e **CIPHER-NOBS-00 (:83)**: LEGIT_UNOBSERVABLE por cascata.

## redreader — `General.parseConfig` (71)

```kotlin
private fun appIds(context) = ... ids.map { SHA-256(signingCert || packageName) }   // General.kt:543-550
fun initAppConfig(...) { ConfigProviders.read { ... parseConfig(id, buf) { k, v -> GlobalConfig.<k> = v } } }
// PrefsUtility.java:182: ConfigProviders.register(() -> "IJuC7OVo2SgR0QVvEZXr913LYMKU4r7p...")
cipher.init(DECRYPT_MODE, SecretKeySpec(b1, "AES"), IvParameterSpec(ByteArray(16)))   // :699-702
```

A chave é o hash do certificado de assinatura (público) com o nome do pacote. O IV é zero e o texto
cifrado é um literal no fonte. O objetivo é ofuscação e anti-fork (só o build assinado oficialmente
lê o `appId`), mas não há sigilo criptográfico: a chave não é segredo e o IV é constante.

- **SECRETKEYSPEC-NOBS-00 (:701)**: MISUSE, `key_derived_from_public_data`.
- **IVPARAMETERSPEC-NOBS-00 (:702)**: MISUSE, `constant_zero_iv`.
- **CIPHER-NOBS-00 (:699)**: MISUSE por cascata da chave.

## metadataremover — `MainViewModel.<clinit>` (73)

```kotlin
companion object {
    val random = SecureRandom("75rgu86gr59ht86".toByteArray(Charsets.UTF_8))   // :46
}
// uso: random.nextLong(System.currentTimeMillis()) (:143); nomes de arquivo aleatórios (:167-175)
```

SECURERANDOM-NOBS-01 é `SecureRandomSpec.c2` (`:95-107`), que lê `RANDOMIZED` sobre a **semente**
passada ao construtor. Aqui a semente é um literal. **MISUSE**, `hardcoded_seed`, confiança média.
O efeito é latente no Android: `new SecureRandom(byte[])` usa o provider padrão (Conscrypt
`OpenSSLRandom`), cujo `engineSetSeed` não substitui a entropia do sistema, e o gerador só produz
nomes de arquivo.

## vault — `Encryption.getDirHash` (74)

```java
KeySpec keySpec = new PBEKeySpec(password, salt, 120_000, KEY_LENGTH + 8);   // :689
SecretKey secretKey = secretKeyFactory.generateSecret(keySpec);              // :690
// Settings.getDirHashForKey: salt = Arrays.copyOfRange(prefs bytes, ...)    // Settings.java:246-248
// PasswordFragment: se nulo, salt = generateSecureSalt(16) (getInstanceStrong + nextBytes) // :113-114
```

O desbloqueio lê o salt das SharedPreferences, e o `copyOfRange` gera ainda outra cópia. O caminho de
criação está tecido (`g3` via `MonitorWrappers`, `next2`) e deveria compor. As linhas não separam os
dois caminhos, mas a recorrência por run (duas ocorrências em várias runs) é do desbloqueio.

- **PBEKEYSPEC-NOBS-01**: LEGIT_UNOBSERVABLE, `salt_from_storage`, confiança média.
- **SECRETKEYFACTORY-NOBS-00**: LEGIT_UNOBSERVABLE por cascata.

## photoprism — `ParseEnteredKeyUseCase.getIssuerPublicKey$lambda$0` (75)

```kotlin
KeyFactory.getInstance("RSA")
    .generatePublic(X509EncodedKeySpec(Base64Variants.PEM.decode(ISSUER_PUB.trimIndent())))   // :95-99
```

É a chave pública fixada do emissor de licenças, usada para verificar a assinatura JWT. Chave pública
embutida não é segredo, e nenhuma API a produz.

- **X509ENCODEDKEYSPEC-NOBS-00**: LEGIT_UNOBSERVABLE, `embedded_public_key`.
- **KEYFACTORY-NOBS-01**: LEGIT_UNOBSERVABLE por cascata.
