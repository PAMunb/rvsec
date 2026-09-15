# Dossiê G6 — código criptográfico de aplicativo

Grupo G6: 16 métodos, 29 sítios, 7 APKs (bitbanana, deku, aegis, networksurvey, mtgfam, trafficlight,
feeder). Todas as fontes são do próprio app no HEAD do dataset, exceto o deku, cuja classe
`Cryptography` vem da dependência jitpack `com.github.smswithoutborders:lib_smsmms_android:73432ef`
(fonte baixada do GitHub nesse commit para `src/lib_smsmms_android-73432ef/`; as linhas 78, 108 e
109 dos registros caem exatamente nas chamadas monitoradas). Caminhos de app são relativos ao
diretório `repos/`; `.mop` relativos a `rvsec-mop/src/main/resources/`.

## Tabela de veredictos

| id | método | código | categoria | mecanismo | raiz |
|---|---|---|---|---|---|
| 18 | bitbanana `UtilFunctions.encodePbkdf2` | PBEKEYSPEC-NOBS-01 | MISUSE (média) | low_entropy_salt | — |
| 18 | bitbanana `UtilFunctions.encodePbkdf2` | SECRETKEYFACTORY-NOBS-00 | MISUSE (média) | low_entropy_salt | PBEKEYSPEC-NOBS-01 |
| 21 | deku `Cryptography.decryptWithKeyStore` | CIPHER-NOBS-00 | SPEC_DEFECT | keystore_getentry_route_not_credited | — |
| 21 | deku `Cryptography.decryptWithKeyStore` | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 21 | deku `Cryptography.decryptWithKeyStore` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | GCMPARAMETERSPEC-NOBS-00 |
| 22 | deku `Cryptography.encryptWithKeyStore` | CIPHER-NOBS-00 | SPEC_DEFECT | keystore_getentry_route_not_credited | — |
| 23 | aegis `CryptoUtils.createCipher` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_non_jca_kdf | SECRETKEYSPEC-NOBS-01 @ deriveKey |
| 23 | aegis `CryptoUtils.createCipher` | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 23 | aegis `CryptoUtils.createCipher` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | GCMPARAMETERSPEC-NOBS-00 |
| 24 | aegis `CryptoUtils.deriveKey` | SECRETKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | key_from_non_jca_kdf | — |
| 25 | aegis `HOTP.getHash` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_user_provisioned_secret | — |
| 25 | aegis `HOTP.getHash` | MAC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_user_provisioned_secret | SECRETKEYSPEC-NOBS-00 |
| 26 | networksurvey `CryptoManager.decrypt` | CIPHER-NOBS-00 | SPEC_DEFECT | keystore_getentry_route_not_credited | — |
| 26 | networksurvey `CryptoManager.decrypt` | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 26 | networksurvey `CryptoManager.decrypt` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | GCMPARAMETERSPEC-NOBS-00 |
| 27 | networksurvey `CryptoManager.encrypt` | CIPHER-NOBS-00 | SPEC_DEFECT | keystore_getentry_route_not_credited | — |
| 29 | mtgfam `MarketPriceFetcher.decrypt` | CIPHER-NOBS-00 | MISUSE | hardcoded_key | SECRETKEYSPEC-NOBS-00 @ $1.fetch |
| 30 | mtgfam `MarketPriceFetcher$1.fetch` | SECRETKEYSPEC-NOBS-00 | MISUSE | hardcoded_key | — |
| 30 | mtgfam `MarketPriceFetcher$1.fetch` | IVPARAMETERSPEC-NOBS-00 | MISUSE | iv_equals_hardcoded_key | — |
| 34 | trafficlight `CryptoManager.decrypt` | CIPHER-NOBS-00 | SPEC_DEFECT | keystore_getentry_route_not_credited | — |
| 34 | trafficlight `CryptoManager.decrypt` | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 34 | trafficlight `CryptoManager.decrypt` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | GCMPARAMETERSPEC-NOBS-00 |
| 36 | feeder `AesCbcWithIntegrity.decodeKey` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_storage | — |
| 36 | feeder `AesCbcWithIntegrity.decodeKey` | SECRETKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | key_from_storage | — |
| 37 | feeder `AesCbcWithIntegrity.decrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_storage | SECRETKEYSPEC-NOBS-01 @ decodeKey |
| 37 | feeder `AesCbcWithIntegrity.decrypt` | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 38 | feeder `AesCbcWithIntegrity.encrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_storage | SECRETKEYSPEC-NOBS-01 @ decodeKey |
| 39 | feeder `AesCbcWithIntegrity.generateKey` | SECRETKEYSPEC-NOBS-00 | SPEC_DEFECT | random_bytes_not_credited_as_key_material | — |
| 40 | feeder `AesCbcWithIntegrity.generateMac` | MAC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_storage | SECRETKEYSPEC-NOBS-00 @ decodeKey |

Contagem: MISUSE 5, SPEC_DEFECT 6, LEGIT_UNOBSERVABLE 18, UNDETERMINED 0.

## Leituras dos .mop que importam aqui

- `CipherSpec.i2` (`CipherSpec.mop:168-233`) lê `GENERATED_KEY[key, alg]` (família e letra),
  `GENERATED_PUBLIC_KEY` e `GENERATED_PRIVATE_KEY`; CIPHER-NOBS-00 em :232. Produtores de
  `GENERATED_KEY`: `KeyGeneratorSpec.mop:223` (no `@match`, só após sequência aceita),
  `SecretKeySpecSpec.mop:256` (só se a construção conformou), `SecretKeyFactorySpec.mop:108` (só se
  o KeySpec tinha `SPECCED_KEY`) e `:122`, `KeyStoreSpec.mop:200` (só a chave de `gk1`, isto é,
  `KeyStore.getKey`).
- `GCMParameterSpecSpec.c1` (`:71-79`) e `IvParameterSpec.c1` (`:68-75`) leem `RANDOMIZED` sobre o
  array; produtor único: `SecureRandomSpec.mop:384,394,398`. `PREPARED_GCM` só é escrito
  (`GCMParameterSpecSpec.mop:180`) se `c1` conformou (`:82-84`), daí a cascata para
  `IvChainJunction.mop:194-201` (IVCHAINJUNCTION-NOBS-01).
- `SecretKeySpecSpec.c1`/`c2` (`:110-118`, `:176-184`) leem `PREPARED_KEY_MATERIAL`, produzido só
  por `getEncoded()` de uma chave já creditada (`SecretKeySpec.mop:119-146`, `KeySpec.mop:75-106`)
  e por `KeyAgreementSpec.mop:298,315`.
- `MacSpec.i1` (`:179-186`) lê `validateAny(GENERATED_KEY, key)`.
- `PBEKeySpecSpec.c1` (`:148-156`) lê `RANDOMIZED` sobre o salt e só escreve `SPECCED_KEY` (`:160`)
  se também `iterationCount >= 10000`; `SecretKeyFactorySpec.gen` (`:96-105`) lê esse `SPECCED_KEY`.

---

## 18 — bitbanana `UtilFunctions.encodePbkdf2`

```java
// UtilFunctions.java:53
hash = encodePbkdf2(data.toCharArray(), getAppSalt().getBytes(), RefConstants.NUM_HASH_ITERATIONS, 32);
// UtilFunctions.java:70-73
String salt = "";
String decrypted = PrefsUtil.getEncryptedPrefs().getString(PrefsUtil.RANDOM_SOURCE, "");
salt = "BitBanana" + decrypted;
// UtilFunctions.java:83-85  (createRandomSource)
int randomNumber = random.nextInt();
PrefsUtil.editEncryptedPrefs().putString(PrefsUtil.RANDOM_SOURCE, String.valueOf(randomNumber)).commit();
// UtilFunctions.java:93-95
PBEKeySpec spec = new PBEKeySpec(password, salt, iterations, bytes * 8);
SecretKeyFactory skf = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
return skf.generateSecret(spec).getEncoded();
```

Rastro do salt: `getAppSalt()` → `"BitBanana" + <decimal de um int de SecureRandom.nextInt()>`
guardado nas EncryptedSharedPreferences → `String.getBytes()`. O array nasce de uma recodificação de
texto, portanto nunca carregaria `RANDOMIZED`; mas o ponto não é só alcance: o valor tem prefixo fixo
e apenas 32 bits de entropia (2^32 salts possíveis, colisão a 50% perto de 65 mil instalações),
contra os ≥128 bits de NIST SP 800-132, e se a leitura das preferências lançar exceção o salt vira a
constante `"BitBanana"`. O uso é o hash do PIN/senha de bloqueio do app, com 5000 iterações
(PBEKEYSPEC-CONSTR-00 dispara no mesmo sítio).

- **PBEKEYSPEC-NOBS-01 → MISUSE (média)**, `low_entropy_salt`. A dúvida está no critério: se bastar
  "salt único por instalação", o sítio seria LEGIT_UNOBSERVABLE (valor lido de armazenamento). Como o
  salt tem estrutura previsível e entropia bem abaixo do mínimo normativo, classifico como uso
  indevido fraco.
- **SECRETKEYFACTORY-NOBS-00 → MISUSE (média)**, cascata de PBEKEYSPEC-NOBS-01 (o KeySpec da linha 93
  não recebeu `SPECCED_KEY`; as 5000 iterações também teriam bloqueado a escrita).

## 21, 22 — deku `Cryptography.decryptWithKeyStore` / `encryptWithKeyStore` (lib_smsmms_android@73432ef)

```kotlin
// Cryptography.kt:70-79 (encrypt)
val keyStore: KeyStore = KeyStore.getInstance("AndroidKeyStore")
keyStore.load(null)
val keyEntry: KeyStore.SecretKeyEntry = keyStore.getEntry(keystoreAlias, null) as KeyStore.SecretKeyEntry
val key: SecretKey = keyEntry.secretKey
val cipher: Cipher = Cipher.getInstance("AES/GCM/NoPadding")
cipher.init(Cipher.ENCRYPT_MODE, key)
return cipher.iv + cipher.doFinal(data)
// Cryptography.kt:95-109 (decrypt)
val iv = data.copyOfRange(0, ivSize)
...
val spec = GCMParameterSpec(128, iv)
cipher.init(Cipher.DECRYPT_MODE, key, spec)
```

Rastro da chave: gerada uma vez por `KeyGenerator.getInstance("AES","AndroidKeyStore")` com
`KeyGenParameterSpec` (:34-52), mas o retorno de `generateKey()` é descartado; toda cifragem e
decifragem relê a chave com `getEntry(...).secretKey`. `KeyStoreSpec` observa `getEntry` (evento
`ge1`, `KeyStoreSpec.mop:106-108`) e não encena nada; só `gk1` (`getKey`, :114-122) chega à escrita
de `GENERATED_KEY` (:200); nenhum .mop observa `KeyStore.SecretKeyEntry.getSecretKey()`. A chamada
está em código tecido e o objeto seria credenciável exatamente como a rota `getKey` já é.
Rastro do IV: 12 primeiros bytes do blob que `getDatabasePassword` (:114-128) guardou nas
configurações, produzido na cifragem por `cipher.iv` (IV gerado pelo provedor Keystore, que exige
`setRandomizedEncryptionRequired(true)`).

- **CIPHER-NOBS-00 (21 e 22) → SPEC_DEFECT (alta)**, `keystore_getentry_route_not_credited`.
- **GCMPARAMETERSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (alta)**, `iv_from_ciphertext`.
- **IVCHAINJUNCTION-NOBS-01 → LEGIT_UNOBSERVABLE (alta)**, cascata da anterior.

## 23, 24 — aegis `CryptoUtils.createCipher` / `deriveKey`

```java
// CryptoUtils.java:36-38
byte[] keyBytes = SCrypt.generate(input, params.getSalt(), params.getN(), params.getR(), params.getP(), CRYPTO_AEAD_KEY_SIZE);
return new SecretKeySpec(keyBytes, 0, keyBytes.length, "AES");
// CryptoUtils.java:65-67
if (nonce != null) {
    AlgorithmParameterSpec spec = new GCMParameterSpec(CRYPTO_AEAD_TAG_SIZE * 8, nonce);
    cipher.init(opmode, key, spec);
```

Rastro da chave em `deriveKey`: `KeyDerivationTask.java:25-34` gera salt de 32 bytes com
`SecureRandom.nextBytes` (`CryptoUtils.java:113-122`) e chama scrypt (N=2^15, r=8, p=1) da cópia de
BouncyCastle embutida em `com.beemdevelopment.aegis.crypto.bc.SCrypt` — código de app, fora da JCA,
sem nenhuma API que a spec possa observar produzindo `PREPARED_KEY_MATERIAL`.
- **SECRETKEYSPEC-NOBS-01 (24) → LEGIT_UNOBSERVABLE (alta)**, `key_from_non_jca_kdf`.

Rastro da chave em `createCipher:66`: nas duas execuções que chegaram lá (droidbot bfs e dfs, rep 2),
`deriveKey:38` aparece antes (258 s → 284 s; 241 s → 283 s): é o desbloqueio pelo slot de senha
(`PasswordSlotDecryptTask.java:51,82` → `Slot.createDecryptCipher` :89-91). As demais rotas até esse
init também são legítimas (chave mestra decifrada; chave do Keystore por `getKey`, que seria
creditada; importadores com PBKDF2). O nonce é `_encryptedMasterKeyParams.getNonce()`, que veio do
`cipher.getIV()` gravado na cifragem do slot (`CryptoUtils.java:75-83`, `Slot.java:67-76`) ou do
JSON do cofre (`Slot.java:128-129`).
- **CIPHER-NOBS-00 (23) → LEGIT_UNOBSERVABLE (alta)**, cascata de SECRETKEYSPEC-NOBS-01 @ deriveKey.
- **GCMPARAMETERSPEC-NOBS-00 (23) → LEGIT_UNOBSERVABLE (alta)**, `iv_from_ciphertext`.
- **IVCHAINJUNCTION-NOBS-01 (23) → LEGIT_UNOBSERVABLE (alta)**, cascata.

Observações: o `__LOC` :66 cobre o init da linha 67 (o jar do dex2jar não trouxe tabela de linhas;
o método tem um único `init` de três argumentos). À parte, e fora dos sítios do grupo: o
`cipher.init(opmode, key)` de :69 não deixou nenhuma linha `i2` nas 6 execuções em que `doFinal`
(:78) disparou CIPHER-ORDER-00 — como a chave ali é a mesma derivada, esperaria-se CIPHER-NOBS-00;
vale checar se esse `init(int, Key)` foi tecido.

## 25 — aegis `HOTP.getHash`

```java
// HOTP.java:32, 41-42
SecretKeySpec key = new SecretKeySpec(secret, "RAW");
Mac mac = Mac.getInstance(algo);
mac.init(key);
```

Rastro: `HotpInfo.getOtp` (:33-37) / `TOTP` → `OtpInfo.getSecret()`, preenchido pelo segredo
Base32/Hex que o usuário digitou (`EditEntryActivity.java:748`), de um QR `otpauth://`
(`GoogleAuthInfo.java:58,166`) ou de um importador. É o segredo compartilhado provisionado pelo
serviço, não gerável pelo app.
- **SECRETKEYSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (alta)**, `key_from_user_provisioned_secret`
  (SECRETKEYSPEC-ALG-00 por `"RAW"` também dispara).
- **MAC-NOBS-00 → LEGIT_UNOBSERVABLE (alta)**, cascata; `HmacSHA1` é imposição do RFC 4226/6238.

## 26, 27 — networksurvey `CryptoManager.decrypt` / `encrypt`

```kotlin
// CryptoManager.kt:38-41
val existingKey = keyStore.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry
return existingKey?.secretKey ?: createKey()
// :74  cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
// :104-109
val iv = Base64.decode(parts[0], Base64.NO_WRAP)
val spec = GCMParameterSpec(GCM_TAG_LENGTH, iv)
cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), spec)
```

Mesma forma do deku. Na primeira chamada do processo sem chave, `createKey()` usa
`KeyGenerator.getInstance("AES","AndroidKeyStore")` + `init(KeyGenParameterSpec)` + `generateKey()`,
que `KeyGeneratorSpec` credita (`g2 init gk1`, :223); com a chave existente a rota é `getEntry`, não
creditada. IV do decrypt: Base64 da parte `iv` da string guardada, que `encrypt` produziu de
`cipher.iv`.
- **CIPHER-NOBS-00 (26, 27) → SPEC_DEFECT (alta)**, `keystore_getentry_route_not_credited`.
- **GCMPARAMETERSPEC-NOBS-00 (26) → LEGIT_UNOBSERVABLE (alta)**, `iv_from_ciphertext`.
- **IVCHAINJUNCTION-NOBS-01 (26) → LEGIT_UNOBSERVABLE (alta)**, cascata.

## 29, 30 — mtgfam `MarketPriceFetcher$1.fetch` / `MarketPriceFetcher.decrypt`

```java
// MarketPriceFetcher.java:125-131
SecretKey sk = new SecretKeySpec(context.getString(R.string.key_lastLegalityUpdate).substring(0, 16).getBytes(StandardCharsets.UTF_8), "AES");
IvParameterSpec iv = new IvParameterSpec(sk.getEncoded());
String a = "AES/CBC/PKCS5Padding";
token = api.getAccessToken(
        MarketPriceFetcher.decrypt(a, "j9mxAigDGtwUdJscE38NUh6CKK2EpiPCG/pDURUxAeC8+6btP2GvRQf0In29Wn3T", sk, iv), ...
// MarketPriceFetcher.java:473-474
Cipher cipher = Cipher.getInstance(algorithm);
cipher.init(Cipher.DECRYPT_MODE, key, iv);
```

`res/values/strings-pref-keys.xml:22`: `key_lastLegalityUpdate` = `lastLegalityUpdate`. A chave AES é
a constante `"lastLegalityUpda"`, o IV é a própria chave, e os textos cifrados são literais: é
ofuscação de credenciais da API TCGPlayer embarcadas no APK, recuperáveis por qualquer um.
- **SECRETKEYSPEC-NOBS-00 (30) → MISUSE (alta)**, `hardcoded_key`.
- **IVPARAMETERSPEC-NOBS-00 (30) → MISUSE (alta)**, `iv_equals_hardcoded_key` (IV fixo = chave).
- **CIPHER-NOBS-00 (29) → MISUSE (alta)**, cascata de SECRETKEYSPEC-NOBS-00 @ `$1.fetch`.

## 34 — trafficlight `CryptoManager.decrypt`

```kotlin
// CryptoManager.kt:22-25
return keyCache[alias] ?: (keyStore.getEntry(alias, null) as? KeyStore.SecretKeyEntry)?.secretKey?.also {
    keyCache[alias] = it
} ?: createKey(alias)
// :56-61
val combined = Base64.decode(encryptedData, Base64.NO_WRAP)
val iv = combined.sliceArray(0 until 12)
cipher.init(Cipher.DECRYPT_MODE, getSecretKey(KEY_ALIAS), GCMParameterSpec(128, iv))
```

Chave do Android Keystore: criada por `KeyGenerator` AndroidKeyStore (creditada, e mantida em
`keyCache` com a mesma identidade) ou relida por `getEntry` (não creditada). Os dados confirmam a
divisão: CIPHER-NOBS-00 tem 204 linhas contra 298 de GCMPARAMETERSPEC-NOBS-00 no mesmo sítio — nos
processos em que a chave foi gerada, o `i2` foi satisfeito. IV: 12 primeiros bytes do Base64
armazenado, gravado por `encrypt` (:47-52) a partir de `cipher.iv`.
- **CIPHER-NOBS-00 → SPEC_DEFECT (alta)**, `keystore_getentry_route_not_credited`.
- **GCMPARAMETERSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (alta)**, `iv_from_ciphertext`.
- **IVCHAINJUNCTION-NOBS-01 → LEGIT_UNOBSERVABLE (alta)**, cascata.

## 36–40 — feeder `AesCbcWithIntegrity`

```kotlin
// AesCbcWithIntegrity.kt:122-130 (generateKey)
val keyGen = KeyGenerator.getInstance(CIPHER)
keyGen.init(AES_KEY_LENGTH_BITS)
val confidentialityKey = keyGen.generateKey()
val integrityKeyBytes = randomBytes(HMAC_KEY_LENGTH_BITS / 8) // SecureRandom().nextBytes
val integrityKey: SecretKey = SecretKeySpec(integrityKeyBytes, HMAC_ALGORITHM)
// :88-98 (decodeKey)
val confidentialityKey = Base64.decode(keysArr[0], BASE64_FLAGS)
val integrityKey = Base64.decode(keysArr[1], BASE64_FLAGS)
SecretKeys(SecretKeySpec(confidentialityKey, 0, confidentialityKey.size, CIPHER),
           SecretKeySpec(integrityKey, HMAC_ALGORITHM))
// :287-292 (encrypt)  var iv = generateIv(); ... init(ENCRYPT_MODE, secretKeys.confidentialityKey, IvParameterSpec(iv))
// :363-366 (decrypt)  init(DECRYPT_MODE, secretKeys.confidentialityKey, IvParameterSpec(civ.iv))
// :394-395 (generateMac) sha256HMAC.init(integrityKey)
```

Rastro: `SyncRemoteStore.kt:108-116` cria o remoto padrão com
`secretKey = AesCbcWithIntegrity.generateKey().toString()` — Base64 de `getEncoded()` das duas chaves
— e grava no banco Room; ou a string chega pelo link/QR de adesão à cadeia de sincronização.
`SyncRestClient.kt:68,104,149` sempre usa `decodeKey(syncRemote.secretKey)`. A codificação Base64 e o
armazenamento quebram a identidade (o `getEncoded()` creditado em `toString()` gera um array que é
imediatamente codificado). Na execução ape rep 1 a sequência é: `generateKey:130` (33 s) →
`decodeKey:97/98`, `encrypt:289`, `generateMac:395` (151 s) → `decrypt:366/363` (155 s); e de novo
`decodeKey` (263 s) → `generateMac`, `decrypt` (268 s). O IV do `decrypt` é Base64 do campo `iv` de
`"iv:mac:ciphertext"` vindo do servidor (:494-500), autenticado pelo HMAC antes do uso; o IV do
`encrypt` é de `SecureRandom` e não é acusado.

- **SECRETKEYSPEC-NOBS-00 / -01 (36) → LEGIT_UNOBSERVABLE (alta)**, `key_from_storage`.
- **CIPHER-NOBS-00 (37, 38) → LEGIT_UNOBSERVABLE (alta)**, cascata de SECRETKEYSPEC-NOBS-01 @ decodeKey.
- **IVPARAMETERSPEC-NOBS-00 (37) → LEGIT_UNOBSERVABLE (alta)**, `iv_from_ciphertext`.
- **MAC-NOBS-00 (40) → LEGIT_UNOBSERVABLE (alta)**, cascata de SECRETKEYSPEC-NOBS-00 @ decodeKey
  (a chave HMAC de `generateKey` não chega a `Mac.init` nas execuções).
- **SECRETKEYSPEC-NOBS-00 (39, generateKey:130) → SPEC_DEFECT (alta)**,
  `random_bytes_not_credited_as_key_material`. 32 bytes de `SecureRandom.nextBytes` (observados;
  `SecureRandomSpec.mop:392-399` escreve `RANDOMIZED`) são material correto para HMAC-SHA256, mas
  `SecretKeySpecSpec.mop:110-118` só aceita `PREPARED_KEY_MATERIAL`, produzido apenas por
  `getEncoded()` de chave creditada e por `KeyAgreement`. É fiel ao oráculo e está registrado como
  decisão do pesquisador (`SecretKeySpecSpec.mop:77-95`); na taxonomia do censo conta como
  SPEC_DEFECT porque a proveniência é correta e observável. É o sítio de maior volume do grupo
  (108 linhas, 99 execuções só-NOBS, todas as ferramentas).

## Padrões

1. **Rota `KeyStore.getEntry(...).getSecretKey()` sem crédito** (4 métodos, 3 apps: deku,
   networksurvey, trafficlight). Idioma Android padrão e correto; `KeyStoreSpec` só credita
   `getKey`. Um produtor sobre `KeyStore.SecretKeyEntry.getSecretKey()` (ou uma escrita encenada em
   `ge1`) eliminaria todos.
2. **IV/nonce GCM relido do texto cifrado** (4 métodos): cascata GCMPARAMETERSPEC-NOBS-00 →
   IVCHAINJUNCTION-NOBS-01 em toda decifragem GCM, porque o IV de cifragem é gerado dentro do
   provedor Keystore/Conscrypt e sai por `getIV()`.
3. **Material de chave recodificado ou vindo de fora da JCA** (aegis scrypt, segredo OTP, feeder
   Base64 no banco): legítimo e inobservável.
4. **Bytes de `SecureRandom` como material de `SecretKeySpec`** (feeder generateKey): acusado por
   decisão de oráculo.
5. O único uso indevido claro é o mtgfam (chave e IV constantes); o bitbanana é um salt fraco, não
   ausente.
