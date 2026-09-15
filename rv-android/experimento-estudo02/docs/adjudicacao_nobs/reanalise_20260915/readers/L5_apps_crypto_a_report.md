# Batch L5_apps_crypto_a — NOBS site re-reading (app-level crypto)

Read-only investigation. Sources read: the nine app repos under `rvsec-dataset/repos/<apk>/`, the `jca_android` `.mop` files that ran (`CipherSpec`, `IvParameterSpec`, `SecretKeySpecSpec`, `SecretKeySpec`, `KeySpec`, `SecretKeyFactorySpec`, `PBEKeySpecSpec`, `KeyStoreSpec`, `KeyGeneratorSpec`, `GCMParameterSpecSpec`, `IvChainJunction`, `SecureRandomSpec`, `codes.csv`), `PredicateStore.java`, the dexlib2 instrumenter sources (`PointcutMatcher.java`, `WrapperEmitter.java`, `DexWeaver.java`, `TypeResolver.java`), and the **instrumented** APK bytecode (dexdump of `classes*.dex` extracted into `scratchpad/r5/dex/`). For deku, the bundled library `com.github.smswithoutborders:lib_smsmms_android:73432ef` (app `build.gradle:153`) has no local source; I fetched the GitHub archive at that commit into `scratchpad/r5/lib_smsmms_src/` and cross-checked it against the bytecode. For passportreader (`com.google.android.gms.internal.ads.zzbbe`, play-services-ads 25.3.0, obfuscated) only bytecode was read.

Abbreviations: `GK` = `Property.GENERATED_KEY`; `PKM` = `PREPARED_KEY_MATERIAL`; `RND` = `RANDOMIZED`; `SK` = `SPECCED_KEY`. Spec paths are relative to `rvsec/rvsec-mop/src/main/resources/jca_android/`. Dexdump excerpts are in `scratchpad/r5/*.txt`.

---

## (a) Site table

| class.method | spec | code | category | root (if cascade) | library+version or app | evidence file:line | conf. | one-line reason |
|---|---|---|---|---|---|---|---|---|
| gms...zzbbe.zzb | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | **MISUSE** | — | play-services-ads 25.3.0 (passportreader) | zzbbz.zza bytecode 0x0078-0x009d; zzbbe.zzb 0x0021-0x0028 | high | key = 16 bytes of a base64 string literal XOR 0x44, hard-coded in the library |
| gms...zzbbe.zzb | IvParameterSpecSpec | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | play-services-ads 25.3.0 | zzbbe.zzb 0x000b-0x001b, 0x0032-0x0037 | high | IV = first 16 bytes of the base64-decoded input (ciphertext prefix), DECRYPT_MODE |
| gms...zzbbe.zzb | CipherSpec | CIPHER-NOBS-00 | MISUSE (cascade) | zzbbe.zzb SECRETKEYSPEC-NOBS-00 | play-services-ads 25.3.0 | zzbbe.zzb 0x003e-0x0041 | high | c1 refused the hard-coded key, so GK was never written for it |
| redreader General.parseConfig | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | **MISUSE** | — | app | General.kt:543-550, :638-639, :701; AndroidCommon.kt:108-121 | high | key = SHA-256(signing-cert DER ‖ packageName) — derived from public app identity, never via getEncoded |
| redreader General.parseConfig | IvParameterSpecSpec | IVPARAMETERSPEC-NOBS-00 | **MISUSE** | — | app | General.kt:702; bytecode 0x001c-0x0023 | high | `IvParameterSpec(ByteArray(16))` — all-zero constant IV |
| redreader General.parseConfig | CipherSpec | CIPHER-NOBS-00 | MISUSE (cascade) | parseConfig SECRETKEYSPEC-NOBS-00 | app | General.kt:699-703 | high | key SecretKeySpec refused → no GK |
| myexpenses AESObfuscator.<init> | PBEKeySpecSpec | PBEKEYSPEC-NOBS-01 | **MISUSE** | — | app (vendored Google LVL `PlayLicensingOrig`) | AESObfuscator.java:59; LicenceModule.kt:60-83 | high | salt = 20-byte literal `byteArrayOf(-1,-124,...)`; also iterationCount 1024 |
| myexpenses AESObfuscator.<init> | SecretKeyFactorySpec | SECRETKEYFACTORY-NOBS-00 | MISUSE (cascade) | AESObfuscator.<init> PBEKEYSPEC-NOBS-01 | app | AESObfuscator.java:60; PBEKeySpecSpec.mop:121-161 | high | c1 did not conform (salt NOBS + iterations<10000) → SK never written |
| myexpenses AESObfuscator.<init> | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | MISUSE (cascade) | AESObfuscator.<init> PBEKEYSPEC-NOBS-01 | app | AESObfuscator.java:61; bytecode 0x0032 | high | no GK for `tmp` → PKM impossible; **independently** the `SecretKey.getEncoded()` call carries no advice (see Anomaly 2) |
| myexpenses AESObfuscator.<init> | IvParameterSpecSpec | IVPARAMETERSPEC-NOBS-00 | **MISUSE** | — | app | AESObfuscator.java:42-43, :63, :65 | high | 16-byte static literal `IV` (fill-array-data in `<clinit>`) |
| myexpenses AESObfuscator.<init> | IvChainJunctionSpec | IVCHAINJUNCTION-NOBS-00 | MISUSE (cascade) | AESObfuscator.<init> IVPARAMETERSPEC-NOBS-00 | app | AESObfuscator.java:63; IvParameterSpec.mop:77-79, :152-154 | high | CBC + ENCRYPT_MODE; PREPARED_IV not written because c1 refused the literal |
| myexpenses AESObfuscator.<init> | CipherSpec | CIPHER-NOBS-00 | MISUSE (cascade) | AESObfuscator.<init> PBEKEYSPEC-NOBS-01 | app | AESObfuscator.java:63, :65 | high | `secret` SecretKeySpec refused → no GK |
| trafficlight CryptoManager.decrypt | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | CryptoManager.kt:22-26, :61; KeyStoreSpec.mop:106-108, :114-122, :199-205 | high | AndroidKeyStore key via `getEntry()…getSecretKey()`; only `getKey` (gk1) writes GK |
| trafficlight CryptoManager.decrypt | GCMParameterSpecSpec | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | CryptoManager.kt:56-57, :61 | high | IV = `combined.sliceArray(0 until 12)` of the stored Base64 blob |
| trafficlight CryptoManager.decrypt | IvChainJunctionSpec | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE (cascade) | CryptoManager.decrypt GCMPARAMETERSPEC-NOBS-00 | app | GCMParameterSpecSpec.mop:77-84, :179-181 | high | PREPARED_GCM not written because c1 refused |
| tokn KeystoreManager.encrypt | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | KeystoreManager.kt:53-55, :72-89 | high | `getOrCreateKey()` always returns `getEntry(...).secretKey`, even right after `generateKey()` |
| tokn KeystoreManager.decrypt | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | KeystoreManager.kt:66-68, :88 | high | same key route as encrypt |
| tokn KeystoreManager.decrypt | GCMParameterSpecSpec | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | KeystoreManager.kt:63-64, :68 | high | IV = `combined.copyOfRange(0, 12)` of the Base64 string read from SharedPreferences |
| tokn KeystoreManager.decrypt | IvChainJunctionSpec | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE (cascade) | KeystoreManager.decrypt GCMPARAMETERSPEC-NOBS-00 | app | GCMParameterSpecSpec.mop:77-84 | high | PREPARED_GCM not written |
| metadataremover MainViewModel.<clinit> | SecureRandomSpec | SECURERANDOM-NOBS-01 | **MISUSE** | — | app | MainViewModel.kt:46; bytecode 0x001a-0x002e | high | `SecureRandom("75rgu86gr59ht86".toByteArray())` — literal seed, default path |
| deku Cryptography.encryptWithKeyStore | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | — | lib_smsmms_android @73432ef | Cryptography.kt:70-78; bytecode 0x0020-0x0044 | high | AndroidKeyStore key via `getEntry()…getSecretKey()` |
| deku Cryptography.decryptWithKeyStore | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | — | lib_smsmms_android @73432ef | Cryptography.kt:100-109 | high | same key route |
| deku Cryptography.decryptWithKeyStore | GCMParameterSpecSpec | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | lib_smsmms_android @73432ef | Cryptography.kt:95-96, :108 | high | IV = `data.copyOfRange(0, 12)` of the stored ciphertext |
| deku Cryptography.decryptWithKeyStore | IvChainJunctionSpec | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE (cascade) | decryptWithKeyStore GCMPARAMETERSPEC-NOBS-00 | lib_smsmms_android @73432ef | GCMParameterSpecSpec.mop:77-84 | high | PREPARED_GCM not written |
| photok KeyGen.generateVaultMasterKey | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE (rule-level; see note) | — | app | KeyGen.kt:30-32; bytecode 0x000e-0x001e; SecretKeySpecSpec.mop:79-91 | medium (category) / high (provenance) | 32 bytes from an observed `SecureRandom.nextBytes` (RND written) but c1 reads PKM, which only `getEncoded()` produces — refusal by construction, recorded decision 2026-08-22 |
| photok KeyGen.derivePasswordKeyEncryptionKey | PBEKeySpecSpec | PBEKEYSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | — | app | KeyGen.kt:43; PasswordVaultProtectionHandler.kt:60-62 (unlock) | high | fires only on the unlock path: salt = `Base64.decode(params.salt)` read from storage (create/migrate pass a fresh `SecureRandom` salt → SATISFIED) |
| photok KeyGen.derivePasswordKeyEncryptionKey | SecretKeyFactorySpec | SECRETKEYFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE (cascade) | KeyGen.derive… PBEKEYSPEC-NOBS-01 | app | KeyGen.kt:44; SecretKeyFactorySpec.mop:96-106 | high | SK not written for the unlock-path PBEKeySpec |
| photok KeyGen.derivePasswordKeyEncryptionKey | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | **SPEC_DEFECT** (create path) / cascade LEGIT_UNOBSERVABLE (unlock path) | create: none (root); unlock: PBEKEYSPEC-NOBS-01 | app | KeyGen.kt:44-46; bytecode classes11.dex 0x0034-0x003f | high | on create GK *is* written for the factory key, but the `invoke-interface javax/crypto/SecretKey.getEncoded()` carries **no advice and no wrapper redirect** in the instrumented APK, so PKM is never written |
| photok PasswordVaultProtectionHandler.create | CipherSpec | CIPHER-NOBS-00 | SPEC_DEFECT (cascade) | KeyGen.derive… SECRETKEYSPEC-NOBS-00 (getEncoded not woven) | app | PasswordVaultProtectionHandler.kt:95-104; bytecode 0x00a2 | high | salt and IV are fresh `SecureRandom` bytes here; the only broken link is the unwoven `getEncoded()` bridge; fires in 47/47 create runs |
| photok PasswordVaultProtectionHandler.unlock | CipherSpec | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE (cascade) | KeyGen.derive… PBEKEYSPEC-NOBS-01 (stored salt) | app | PasswordVaultProtectionHandler.kt:60-70 | high | stored salt breaks the chain first; the unwoven `getEncoded()` would break it anyway (second, independent break) |
| photok PasswordVaultProtectionHandler.unlock | IvParameterSpecSpec | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | PasswordVaultProtectionHandler.kt:69-70; generated at :80 | high | IV = `Base64.decode(params.iv)` read from stored params (it was `SecureRandom` bytes at create) |
| photok PasswordVaultProtectionHandler.unlock | SecretKeySpecSpec | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | PasswordVaultProtectionHandler.kt:73-74 | high | key material = `cipher.doFinal(protection.wrappedVMK)` — decrypted from storage, not a `getEncoded()` |
| dsub2000 KeyStoreUtil.decrypt | IvParameterSpecSpec | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | — | app | KeyStoreUtil.java:121-127, :135; produced at :91-94 | high | IV bytes `System.arraycopy`'d out of the Base64 blob; originally `cipher.getIV()` of the AndroidKeyStore cipher |

Cascade roots are all inside the same method as their cascade unless a different method is named.

---

## (b) Per-method provenance notes

### 1. `com.google.android.gms.internal.ads.zzbbe.zzb([B, String)` — passportreader (play-services-ads 25.3.0, obfuscated)

No source. Bytecode (`scratchpad/r5/passport_zzbbe.txt`, `passport_classes4.dump`). The class is the ads SDK's AES helper: `zzc()` lazily builds one static `Cipher.getInstance("AES/CBC/PKCS5Padding")` (woven via `MonitorWrappers.javax_crypto_Cipher_getInstance`). `zzb(key, base64)` is decrypt, `zza(key, plain)` is encrypt.

- Key bytes (`v5`, first parameter): the only caller that supplies a key is `zzbbz` — `zzbbz.zzf` holds the `zzbbe` and `zzbbz.zzg` the key. `zzbbz.zza(Context,…)` builds `zzg` as:
  ```
  |0078: const-string v2, "GpeoZNfYB0xbX4XrY9tptE+P6lGr6tGbtd6Fg+9sjdQ="
  |007a: invoke-static {v2, v12}, zzazp.zzb(String,Z)[B        ; base64 decode → 32 bytes
  |0081: if-ne v3, v4 (length must be 32)
  |0087: ByteBuffer.wrap(v2, 4, 16) ; |008b: new-array v4, 16 ; |008d: get(v4)
  |0093..009c: v4[i] ^= 0x44 for i in 0..15
  |009d: iput-object v4, v0, zzbbz.zzg:[B
  ```
  So the key is a **16-byte literal** (bytes 4..19 of a base64 constant, XOR 0x44), then `zzbbz.zza` 0x00d0-0x00d4 and `zzbbz.zzu` 0x00ab-0x00bc pass `zzg` to `zzbbe.zzb`. Inside `zzb`: `|0025: SecretKeySpec.<init>(v5, "AES")` followed by `|0028: SecretKeySpecSpec_c1Event` (woven). `c1` reads PKM (SecretKeySpecSpec.mop:110) — a literal never had `getEncoded()` → NOT_OBSERVED → **SECRETKEYSPEC-NOBS-00, MISUSE** (hard-coded key). It is the library's obfuscation of its cached dynamite dex, reachable by default whenever the ads SDK initialises its task context (`zzbbz.zza` is entered from `zzbbz` init; the string `"1762298034389"` next to it is the module version).
- IV: `zzb` 0x000b-0x001e splits the decoded input: `ByteBuffer.put(decoded).flip(); get(v6 /*16 bytes*/); get(v0 /*rest*/)` then `|0034: IvParameterSpec.<init>(v6)` + `|0037: IvParameterSpecSpec_c1Event`. The IV is the ciphertext prefix → `RND` never written → **IVPARAMETERSPEC-NOBS-00, LEGIT_UNOBSERVABLE**. `init(2 /*DECRYPT*/, key, ivspec)` at 0x0041 — `IvChainJunction.use` requires `encmode == 1` for the IV clause (IvChainJunction.mop:156-158), so no junction report here, consistent with the batch.
- `CIPHER-NOBS-00` at `|003e: CipherSpec_i2Event(2, v1, v2)`: `CipherSpec.i2` reads GK on the SecretKeySpec (CipherSpec.mop:199-202); `SecretKeySpecSpec.@match` writes GK only when `conforms` (SecretKeySpecSpec.mop:121-124, :255-258) → cascade of the key MISUSE.
- Source lines `…@@25.3.0:9/:10` are R8's synthetic line table (positions: line=9 at 0x0021, line=10 at 0x002e); they match the recorded lines.

### 2. `org.quantumbadger.redreader.common.General.parseConfig` (General.kt:696-711)

```kotlin
696 private fun parseConfig(b1: ByteArray, b2: ByteArray, action: (String, String) -> Unit) {
698     val cipher = Cipher.getInstance("AES/CBC/PKCS5PADDING")
699-703 cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(b1, "AES"), IvParameterSpec(ByteArray(16)))
704     val dis = DataInputStream(ByteArrayInputStream(cipher.doFinal(b2)))
```
Caller `initAppConfig` (General.kt:626-645): for each config blob `buf` from `ConfigProviders.read`, `appIds(context).forEach { id -> parseConfig(id, buf) … }`. `appIds` (General.kt:543-550): for each `ids` entry, `SHA-256(it ‖ packageName)`; `ids` = the app's signing certificates' DER (`AndroidCommon.kt:117-120`: `pInfo.signatures.map { CertificateFactory…generateCertificate(...).encoded }`). So **b1 = SHA-256(signing cert DER ‖ package name)**: a key deterministically derived from public app identity, produced by `MessageDigest.digest()` (no `getEncoded()`, no generator). → SECRETKEYSPEC-NOBS-00 **MISUSE** (derived-from-public-data key); the Cipher NOBS is its cascade. IV = `ByteArray(16)` → 16 zero bytes → **MISUSE** (`IvParameterSpecSpec.c1` reads `RND`, IvParameterSpec.mop:68). Bytecode (`redreader_General.txt`) confirms all three advices woven at 0x0015, 0x0023, 0x002c. Reachable by default (app config load); every exception is swallowed (`catch(_: Exception) {}`), so a wrong id just fails silently.

### 3. `com.google.android.vending.licensing.AESObfuscator.<init>` — myexpenses (vendored module `PlayLicensingOrig`, `settings.gradle:31`, `myExpenses/build.gradle:187`)

```java
40  KEYGEN_ALGORITHM = "PBEWITHSHAAND256BITAES-CBC-BC";
42  private static final byte[] IV = { 16, 74, 71, -80, 32, 101, -47, 72, 117, -14, 0, -29, 70, 65, -12, 74 };
57  SecretKeyFactory factory = SecretKeyFactory.getInstance(KEYGEN_ALGORITHM);
59  KeySpec keySpec = new PBEKeySpec((applicationId + deviceId).toCharArray(), salt, 1024, 256);
60  SecretKey tmp = factory.generateSecret(keySpec);
61  SecretKey secret = new SecretKeySpec(tmp.getEncoded(), "AES");
63  mEncryptor.init(Cipher.ENCRYPT_MODE, secret, new IvParameterSpec(IV));
65  mDecryptor.init(Cipher.DECRYPT_MODE, secret, new IvParameterSpec(IV));
```
Constructor call: `LicenceModule.kt:57-83` — `AESObfuscator(byteArrayOf(-1,-124,-4,-59,…,-25) /*20 literal bytes*/, application.packageName, deviceId)` with `deviceId = Settings.Secure.ANDROID_ID` (`LicenceModule.kt:42-43`). Dagger `@Singleton @Provides` → runs on the default path.

Chain, with the woven bytecode (`myexpenses_AESObfuscator.txt`):
1. `|0026 PBEKeySpec.<init>(chars, v9=salt, 1024, 256)` → `|0029 PBEKeySpecSpec_c1Event`. `c1` (PBEKeySpecSpec.mop:117-162): `iterationCount < 10000` → CONSTR-00 and `conforms=false`; `validate(RND, salt)` on the literal → NOT_OBSERVED → **PBEKEYSPEC-NOBS-01, MISUSE (hard-coded salt)**. `SK` is not ensured (:159-161).
2. `|002c MonitorWrappers.javax_crypto_SecretKeyFactory_generateSecret` → `gen` (SecretKeyFactorySpec.mop:92-110): `validateAny(SK, keySpec)` → NOT_OBSERVED → **SECRETKEYFACTORY-NOBS-00** (val `'PBEWITHSHAAND256BITAES-CBC-BC'` = `canonical()` of the alias, matches the observed val); GK not written for `tmp`. Cascade.
3. `|0032 invoke-interface Ljavax/crypto/SecretKey;.getEncoded:()[B` → `|0035 move-result-object` → `|0038 SecretKeySpec.<init>` → `|003b SecretKeySpecSpec_c1Event`. **There is no advice on the `getEncoded` call** (no `SecretKeySpec_e1Event`, no `KeySpec_ge1Event`, no `MonitorWrappers` redirect). Even if there were, `e1`/`ge1` stage only when GK is SATISFIED for the key (SecretKeySpec.mop:122-126; KeySpec.mop:78-84), which step 2 prevented. → **SECRETKEYSPEC-NOBS-00**, cascade of step 1 (the weaving gap is masked here; see Anomaly 2).
4. `|004a IvParameterSpec.<init>(IV)` → `|004d IvParameterSpecSpec_c1Event`: `RND` never written for the `<clinit>` literal (`|0004 fill-array-data`) → **IVPARAMETERSPEC-NOBS-00, MISUSE**; `spec` stays null so `@match` writes no PREPARED_IV (IvParameterSpec.mop:77-79, :152-154). Same at 0x0066-0x0069 for the decryptor (hence 454 = 2 × 227 lines).
5. `|0051 IvChainJunctionSpec_useEvent(1, ivspec, cipher)`: mode CBC, encmode 1 → `validate(PREPARED_IV, params)` → **IVCHAINJUNCTION-NOBS-00**, cascade of 4 (only the :63 ENCRYPT site, consistent with `lines 227`).
6. `|0054 / |0070 CipherSpec_i2Event`: GK on `secret` absent → **CIPHER-NOBS-00**, cascade of 1-3.

Not in this batch but expected from the same code: PBEKEYSPEC-CONSTR-00 (1024 iterations), SECRETKEYFACTORY-ALG-00 (`PBEWITHSHAAND256BITAES-CBC-BC` is not in `safeAlgorithms`, SecretKeyFactorySpec.mop:40-46).

### 4. `com.leekleak.trafficlight.database.CryptoManager.decrypt` (CryptoManager.kt:55-63)

```kotlin
18 private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
22 private fun getSecretKey(alias) = keyCache[alias]
23     ?: (keyStore.getEntry(alias, null) as? KeyStore.SecretKeyEntry)?.secretKey?.also { keyCache[alias] = it }
25     ?: createKey(alias)          // KeyGenerator.getInstance("AES","AndroidKeyStore") … generateKey()
56 val combined = Base64.decode(encryptedData, NO_WRAP)
57 val iv = combined.sliceArray(0 until 12)
61 cipher.init(Cipher.DECRYPT_MODE, getSecretKey(KEY_ALIAS), GCMParameterSpec(128, iv))
```
- Key. Two routes. (i) `createKey` → `KeyGenerator` g2 (`MonitorWrappers.javax_crypto_KeyGenerator_getInstance_1`, bytecode 0x0019) → `init(AlgorithmParameterSpec)` (`KeyGeneratorSpec_initEvent`, 0x003f) → `generateKey` (wrapper, 0x0045) → `gk1` → `@match` writes GK(key, "AES") (KeyGeneratorSpec.mop:213-227) → `CipherSpec.i2` SATISFIED. This route runs only in the process that first creates the alias. (ii) `getEntry(alias, null) … .secretKey` — every later process start. `KeyStoreSpec.ge1` is a `before` event that stages nothing (KeyStoreSpec.mop:106-108); only `gk1` (`getKey(String,char[])`) stages `generatedKey` and `@match` writes GK (:114-122, :199-205). The `.mop` comments record that the oracle ensures `generatedKey[key,_]` only over `getKey`'s return (:135-141, :180-184). In the bytecode, the `getEntry` call (`getSecretKey` 0x0012) carries **no advice at all** (Anomaly 1), and `SecretKeyEntry.getSecretKey()` (0x0020) has no pointcut in the set. → the key is a correct Android-Keystore key that reaches `Cipher.init` with no producer: **LEGIT_UNOBSERVABLE** ("key from keystore"). Note for the researcher: both `KeyStore.getEntry` and `KeyStore$SecretKeyEntry.getSecretKey()` are JCA calls in woven code, so a producer over that route *could* be written; whether that is wanted is a set-vs-oracle decision, not an implementation slip.
- IV: `combined.sliceArray(0 until 12)` — the first 12 bytes of the stored Base64 blob, written by `encrypt` from `cipher.iv` of an AndroidKeyStore GCM cipher (:50-52). `GCMParameterSpecSpec.c1` reads `RND` (GCMParameterSpecSpec.mop:71) → **GCMPARAMETERSPEC-NOBS-00, LEGIT_UNOBSERVABLE**; `spec` not bound → no PREPARED_GCM (:82-84, :179-181) → `IvChainJunction.use` GCM clause (IvChainJunction.mop:191-203) → **IVCHAINJUNCTION-NOBS-01**, cascade.
- Bytecode of `decrypt`: `GCMParameterSpecSpec_c1Event` 0x0041, `IvChainJunctionSpec_useEvent` 0x0046, `CipherSpec_i2Event` 0x0049 — all woven.

### 5. `me.diamondforge.tokn.security.KeystoreManager.encrypt` (:52-60) / `.decrypt` (:62-70)

```kotlin
72 private fun getOrCreateKey(): SecretKey {
73     if (!keystore.containsAlias(KEY_ALIAS)) { … KeyGenerator.getInstance("AES", "AndroidKeyStore") … keyGen.generateKey() }
88     return (keystore.getEntry(KEY_ALIAS, null) as KeyStore.SecretKeyEntry).secretKey
```
Unlike trafficlight, the freshly generated key is discarded and the entry is always re-read through `getEntry` (:88), so **every** `Cipher.init` in `encrypt`/`decrypt` sees a key with no producer → **CIPHER-NOBS-00, LEGIT_UNOBSERVABLE** on both. Bytecode (`tokn_KeystoreManager.txt`): `getOrCreateKey` 0x0056 `KeyStore.getEntry` with no advice; 0x0061 `SecretKeyEntry.getSecretKey`. The contrast inside the same class: the biometric route uses `keystore.getKey(...)` (:111, :150), which **is** redirected (`MonitorWrappers.java_security_KeyStore_getKey`, 0x0028 / 0x006b) → `gk1` → GK — so `biometricDecryptCipher` is not in this batch, as expected.
- `decrypt` IV: `Base64.decode(encoded)` from SharedPreferences (`getDatabasePassphrase` :29-31), `iv = combined.copyOfRange(0, GCM_IV_LENGTH)` (:63-64); produced at encrypt time by `cipher.iv` (:56). → **GCMPARAMETERSPEC-NOBS-00 LEGIT_UNOBSERVABLE**, **IVCHAINJUNCTION-NOBS-01** cascade. Woven: `GCMParameterSpecSpec_c1Event` 0x0032, `useEvent` 0x0037, `i2Event` 0x003a.
- Counts (137 encrypt vs 909 decrypt) fit: `encrypt` runs only when no passphrase is stored yet (:30-34), `decrypt` on every later start.

### 6. `rocks.poopjournal.metadataremover.viewmodel.MainViewModel.<clinit>` (MainViewModel.kt:45-49)

```kotlin
46 val random = SecureRandom("75rgu86gr59ht86".toByteArray(Charsets.UTF_8))
```
Bytecode: `|001a const-string "75rgu86gr59ht86"` → `getBytes` → `|002b SecureRandom.<init>([B)` → `|002e SecureRandomSpec_c2Event(bytes, sr)`. `c2` reads `RND` on the seed (SecureRandomSpec.mop:95-108); a string literal was never marked → **SECURERANDOM-NOBS-01, MISUSE** (constant seed), reachable by default (companion-object init; `random` is used for output file names, :143, :172). Practical note: on Android ≥ 7 `SecureRandom(byte[])` supplements rather than replaces the OS seed, and the generator is not used for key material here, so the security impact is nil; the rule's clause (`randomized[seed]`) is still violated by a literal.

### 7. `com.afkanerd.smswithoutborders_libsmsmms.data.Cryptography.encryptWithKeyStore` (:65-80) / `.decryptWithKeyStore` (:94-111) — deku, library `lib_smsmms_android@73432ef`

Source (fetched; line numbers match the dex `positions` table: 66/67/70/71/74/75/77/78/79 and 95-110):
```kotlin
70  val keyStore = KeyStore.getInstance("AndroidKeyStore"); 71 keyStore.load(null)
73-75 val key: SecretKey = (keyStore.getEntry(keystoreAlias, null) as KeyStore.SecretKeyEntry).secretKey
77-78 Cipher.getInstance("AES/GCM/NoPadding").init(Cipher.ENCRYPT_MODE, key)        // encrypt
95-97 val iv = data.copyOfRange(0, 12); val data = data.copyOfRange(12, data.size)      // decrypt
108-109 cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
```
Same shape as tokn: the key is always re-read via `getEntry` (even right after `createAndStoreSecretKey`, :66-67), so **CIPHER-NOBS-00 LEGIT_UNOBSERVABLE** on both methods. Bytecode (`deku_Cryptography.txt`): `KeyStoreSpec_loadEvent` woven (0x001a/0x001d), `getEntry` at 0x0020/0x0023 with no advice, `CipherSpec_i2Event` at 0x0041/0x0051. The GCM IV is the 12-byte prefix of the stored ciphertext (`settingsGetDbPassword`) → **GCMPARAMETERSPEC-NOBS-00 LEGIT_UNOBSERVABLE** (c1Event 0x004a), **IVCHAINJUNCTION-NOBS-01** cascade (useEvent 0x004e). Counts 169 (encrypt: first run only, when no stored password) vs 645 (decrypt) fit `getDatabasePassword` (:114-129).

### 8. photok — `KeyGen` and `PasswordVaultProtectionHandler`

```kotlin
KeyGen.kt
29 fun generateVaultMasterKey(): SecretKey { val keyBytes = ByteArray(32); SecureRandom().nextBytes(keyBytes); return SecretKeySpec(keyBytes, "AES") }
42 val factory = SecretKeyFactory.getInstance(kdf.value)            // "PBKDF2WithHmacSHA256"
43 val spec = PBEKeySpec(password.toCharArray(), salt, kdfIterations, keySize)
44 val keyBytes = factory.generateSecret(spec).encoded
46 return SecretKeySpec(keyBytes, "AES")
PasswordVaultProtectionHandler.kt
60-66 (unlock)  kek = derive(password, salt = Base64.decode(params.salt), kdf, iterations, keySize)
68-71 (unlock)  Cipher.getInstance(params.algorithm.value).init(DECRYPT_MODE, kek, IvParameterSpec(Base64.decode(params.iv)))
73-74 (unlock)  vmkBytes = cipher.doFinal(protection.wrappedVMK); return SecretKeySpec(vmkBytes, "AES")
79-80 (create)  salt / iv = ByteArray(16).also { SecureRandom().nextBytes(it) }
95-104 (create) kek = derive(password, salt, PBKDF2WithHmacSHA256, 100_000, 256); cipher.init(ENCRYPT_MODE, kek, IvParameterSpec(iv))
107 (create)    wrappedVmk = cipher.doFinal(vmk.encoded)
```
- **generateVaultMasterKey SECRETKEYSPEC-NOBS-00**: bytecode 0x000e `SecureRandomSpec_c1Event`, 0x0011 `SecureRandomSpec_next2Event`, 0x0014 `nextBytes`, 0x001e `SecretKeySpecSpec_c1Event`. So `RND` *is* written for `keyBytes` (SecureRandomSpec.mop:289-294, :392-401). But `c1` reads `PKM` (SecretKeySpecSpec.mop:110), and the file states that `PKM` "is ENSURED by `Key.getEncoded()` and `SecretKey.getEncoded()` and by nothing else in the whole oracle, so the idiom … fill a byte[] from an observed SecureRandom and construct a SecretKeySpec from it — does not satisfy the clause" (:79-91, researcher decision 2026-08-22). Origin is correct and observed; the refusal is by construction of the rule as transcribed. I file it as LEGIT_UNOBSERVABLE (no producer of `PKM` can exist for these bytes) and flag it: if the expert `SecretKeySpec.crysl` REQUIRES is actually `randomized[keyMaterial] || preparedKeyMaterial[keyMaterial]`, this becomes SPEC_DEFECT — I could not open the `.crysl` (see (d)).
- **derive… PBEKEYSPEC-NOBS-01**: the salt is a parameter. Callers: `unlock` passes `Base64.decode(params.salt)` (stored) → `RND` NOT_OBSERVED → NOBS, **LEGIT_UNOBSERVABLE**; `create` (:79) and `migrate` (:142) pass fresh `SecureRandom().nextBytes` salts — woven (`create` bytecode 0x0012/0x0015 `SecureRandomSpec_c1Event`/`next2Event`) → SATISFIED, no report. `kdfIterations` = 100 000 on every path (≥ 10 000). The 51-run count is the unlock population.
- **derive… SECRETKEYFACTORY-NOBS-00**: `gen` reads `validateAny(SK, keySpec)` (SecretKeyFactorySpec.mop:96); `SK` is ensured by `PBEKeySpecSpec.c1` only when `conforms` (:159-161) → absent on the unlock path → cascade. On the create path `SK(spec, 256)` is written, `gen` answers SATISFIED and writes GK(key, "PBKDF2WithHmacSHA256") (:107-109).
- **derive… SECRETKEYSPEC-NOBS-00** (KeyGen.kt:46): bytecode classes11.dex:
  ```
  |0030: invoke-static  MonitorWrappers.javax_crypto_SecretKeyFactory_generateSecret(...)   ; woven
  |0034: invoke-interface {v2}, Ljavax/crypto/SecretKey;.getEncoded:()[B                   ; NO advice, NO wrapper
  |0037: move-result-object v2
  |003c: invoke-direct SecretKeySpec.<init>(v2, "AES")  → |003f: SecretKeySpecSpec_c1Event
  ```
  The `PKM` bridge is `SecretKeySpec.e1` (`SecretKey+.getEncoded()`, SecretKeySpec.mop:119-127, `@match` :143-148) and `KeySpec.ge1` (`Key+.getEncoded()`, KeySpec.mop:75-85, :103-108). Neither was woven at this site: there is no `MultiSpec_1RuntimeMonitor.SecretKeySpec_e1Event`/`KeySpec_ge1Event` call and no redirect to `mop/MonitorWrappers`. Declared owner of the invoke: **`javax/crypto/SecretKey`** (`invoke-interface`). The monitor dex (classes21.dex) does contain both event methods and a wrapper `MonitorWrappers.java_security_Key_getEncoded` (which internally calls `Key.getEncoded` then `KeySpec_ge1Event`), but no app site invokes that wrapper (full scan of the 10 `getEncoded()` sites in the APK: 4 × `javax/crypto/SecretKey`, 2 × `java/security/PublicKey`, 1 × `Certificate`, 1 × `AlgorithmParameters` (that one is advised), 1 × `Key` — the last is the wrapper's own body). On the create path GK exists for the factory key, so a woven `e1` would have staged and `@match` would have written `PKM` → SATISFIED. → **SPEC_DEFECT (advice not woven), confirmed in bytecode**. On the unlock path the same site is additionally a cascade of the stored salt.
- **create CIPHER-NOBS-00** (PVPH.kt:104): bytecode 0x0099 `IvParameterSpecSpec_c1Event` on the fresh IV (SATISFIED → PREPARED_IV written; no IV report, consistent), 0x009f `useEvent`, 0x00a2 `CipherSpec_i2Event(1, kek, cipher)`. `kek` is the `SecretKeySpec` from KeyGen.kt:46, refused at c1 → no GK → CIPHER-NOBS-00 in 47/47 create runs. Cascade of the unwoven `getEncoded()` → **SPEC_DEFECT**. Nothing else on this path is unobservable: salt, IV and VMK bytes are all fresh `SecureRandom` output observed by the monitor.
- **unlock CIPHER-NOBS-00 / IVPARAMETERSPEC-NOBS-00 / SECRETKEYSPEC-NOBS-00**: bytecode 0x0042 and 0x0078 `Base64.decode` (salt, iv), 0x0081-0x0084 `IvParameterSpec`+`c1Event`, 0x008d `i2Event`, 0x0099 `doFinal` wrapper, 0x00a1-0x00a4 `SecretKeySpec`+`c1Event`. IV and salt come from the stored `VaultProtectionParams` (originally `SecureRandom` at :79-80, :142-143); the VMK bytes are the decrypted `wrappedVMK`. All three are **LEGIT_UNOBSERVABLE** (storage / decryption), the Cipher one as a cascade of the salt (root KeyGen.kt:43) with the unwoven `getEncoded()` as a second, independent break. `DECRYPT_MODE` → no `IvChainJunction` IV read, consistent with the batch.

### 9. `github.paroj.dsub2000.util.KeyStoreUtil.decrypt` (KeyStoreUtil.java:115-148)

```java
118 final Key key = getKey();                          // KeyStore("AndroidKeyStore").load(null).getKey(alias, null)
121 byte[] decodedBytes = Base64.decode(encryptedString, NO_WRAP);
122 int ivLength = decodedBytes[0];
126-127 byte[] ivBytes = new byte[ivLength]; System.arraycopy(decodedBytes, 1, ivBytes, 0, ivLength);
134 Cipher cipher = Cipher.getInstance("AES/CBC/PKCS7Padding", "AndroidKeyStoreBCWorkaround");
135 IvParameterSpec ivParamSpec = new IvParameterSpec(ivBytes);
136 cipher.init(Cipher.DECRYPT_MODE, key, ivParamSpec);
```
The IV was produced by the AndroidKeyStore cipher at encrypt time (`cipher.getIV()`, :91-94) and stored with the ciphertext; on decrypt it is a fresh `new byte[]` filled by `System.arraycopy` → no `RND` → **IVPARAMETERSPEC-NOBS-00, LEGIT_UNOBSERVABLE**. Bytecode: `IvParameterSpecSpec_c1Event` 0x002f, `useEvent` 0x0032 (encmode 2 → no IV read), `i2Event` 0x0035. The key route goes through `getKey` — redirected to `MonitorWrappers.java_security_KeyStore_getKey` (0x0014) → `gk1` → GK → no CIPHER-NOBS here, which is exactly what the batch shows. Callers: `Util.java:209,380`, `UserUtil.java:276`, `RESTMusicService.java:1981`, `EditPasswordPreference.java:41` — default path when a password was stored encrypted.

---

## (c) Anomalies

1. **`KeyStoreSpec.ge1` (`KeyStore.getEntry(String, ProtectionParameter)`) is never woven.** At all five `getEntry` call sites in this batch (trafficlight `getSecretKey` 0x0012, tokn `getOrCreateKey` 0x0056, deku `encryptWithKeyStore` 0x0020 and `decryptWithKeyStore` 0x0023) the invoke carries no `KeyStoreSpec_ge1Event`, although `load` right before it does carry `KeyStoreSpec_loadEvent` and the monitor dex defines `KeyStoreSpec_ge1Event`/`se1Event`. Cause (read, not run): the pointcut spells the parameter as `ProtectionParameter`, imported as `java.security.KeyStore.ProtectionParameter` (KeyStoreSpec.mop:7-8, :107, :111); `TypeResolver.toDescriptor` (TypeResolver.java:87-107) turns any dotted name into `L…/KeyStore/ProtectionParameter;` with no `$` handling, so it never equals the DEX descriptor `Ljava/security/KeyStore$ProtectionParameter;` and `PointcutMatcher` finds no match. Consequences: `se1` is dead too; the `(ge1 gk1)` alternative of the `ere` (KeyStoreSpec.mop:124) can never be exercised; no NOBS verdict in this batch changes (ge1 stages nothing anyway), but any ORDER claim about `getEntry`/`setEntry` is untested.

2. **The `preparedKeyMaterial` bridge (`SecretKeySpec.e1`, `KeySpec.ge1`) never fires for application code under dexlib2 instrumentation.** Facts read in the instrumented APKs: `mop.MonitorWrappers` defines exactly one `getEncoded` wrapper, `java_security_Key_getEncoded` (photok classes21.dex, myexpenses classes31.dex); every app call site with declared owner `javax/crypto/SecretKey` (photok: 4 sites incl. KeyGen.kt:44 and PVPH.kt:107; myexpenses: 3 sites incl. AESObfuscator.java:61) or `java/security/PublicKey` (4 sites) is left as a plain `invoke-interface` with no event call after it. Mechanism (read in the instrumenter): wrapper substitution is a map lookup keyed by the exact `MethodReference` (`DexWeaver.findWrapperReplacement`, DexWeaver.java:270-280); subtype keys are added only for **APK-internal** subtypes of the wrapper's parent (`expandWrapperReplacementsForApk`, DexWeaver.java:178-231: `inheritance.subtypesOf(...)` over the APK class graph), so a platform interface such as `javax.crypto.SecretKey` never obtains a key. Whether the `SecretKey+.getEncoded()` pointcut produced no wrapper of its own because `AndroidClassIndex.methods("javax.crypto.SecretKey","getEncoded")` finds no declaration on `SecretKey` (WrapperEmitter.java:437-445) is my inference, not verified by running the emitter. This contradicts the reasoning recorded in SecretKeySpec.mop:102-118 and KeySpec.mop:40-49, which measured `T+` owner matching in `PointcutMatcher` (PointcutMatcher.java:322-345 — correct for inline advices) but not the wrapper-substitution path an `after … returning` advice on a non-constructor call actually takes. Effect on the corpus: every `new SecretKeySpec(key.getEncoded(), alg)` — the exact idiom SecretKeySpecSpec.mop:81-84 names as "the one that does" satisfy the clause — draws SECRETKEYSPEC-NOBS-00 and a downstream CIPHER-NOBS-00, regardless of how the key was made. photok's `create` (47/47 runs) is the clean witness: everything upstream of `getEncoded()` was credited. The ajc variant was not checked.

3. **Line-count arithmetic**: myexpenses codes present at both `:63` and `:65` show 454 = 2 × 227, and the ENCRYPT-only `IVCHAINJUNCTION-NOBS-00` shows 227 — consistent with the `ErrorCollector` dedup per `(spec, code, event, class, method, location)` and one report per run per site. photok's derive site (51) vs create (47) vs unlock (51) cannot be split by path from counts alone for the same reason.

4. passportreader `zzbbe`: the constructor `zzbbe.<init>(SecureRandom)` discards its argument (bytecode: only `Object.<init>`), and the encrypt path `zza` calls `Cipher.init(1, key, (SecureRandom) null)` (0x0013-0x001a, with `IvChainJunctionSpec_useRandomKeyEvent(null, …)` woven) — a `null` SecureRandom must answer NOT_OBSERVED at IvChainJunction.mop:248 (`validate` on null, PredicateStore.java:343-345). Not in this batch; recorded for whoever holds IVCHAINJUNCTION-NOBS-02.

5. redreader `initAppConfig` calls `parseConfig` once per signing certificate per config record and swallows every exception; each attempt constructs a new `SecretKeySpec`, `IvParameterSpec` and `Cipher`, so one config load can emit several identical reports per site (deduped to one line per run).

6. In `SecretKeySpec.e1`/`KeySpec.ge1` the guard `validate(GK, key, key.getAlgorithm())` compares the key's own algorithm string with what `SecretKeyFactorySpec.gen` wrote (`canonical("SecretKeyFactory", alg)`). For BC's PBKDF2 keys `getAlgorithm()` returns the factory name (`PBKDF2WithHmacSHA256`), so the pair would match; for myexpenses' `PBEWITHSHAAND256BITAES-CBC-BC` I did not verify what `BCPBEKey.getAlgorithm()` returns — moot there because `gen` refused, but worth a probe once Anomaly 2 is fixed.

---

## (d) What I could not verify

- The expert `.crysl` files themselves (`SecretKeySpec.crysl`, `KeyStore.crysl`): not found under `rvsec/rvsec/rvsec-crysl`, `rvsec-mop`, `rv-android/tools` or `openspec` (bounded searches). Every oracle statement above is taken from the `.mop` transcriptions and their comments (e.g. SecretKeySpecSpec.mop:73-91, KeyStoreSpec.mop:135-141, :180-193). The photok `generateVaultMasterKey` category hinges on the exact REQUIRES clause.
- Which branch of trafficlight `getSecretKey` ran in a given task (fresh keystore → `createKey` → SATISFIED; existing alias → `getEntry` → NOBS). 800 decrypt lines say the `getEntry` branch dominated; I did not read the per-task logs.
- The ajc-instrumented variant of the same apps (whether `SecretKey.getEncoded()` is advised there).
- The WrapperEmitter inference in Anomaly 2 (why no `javax_crypto_SecretKey_getEncoded` wrapper exists) — read from source, not reproduced by running the emitter.
- `BCPBEKey.getAlgorithm()` for `PBEWITHSHAAND256BITAES-CBC-BC` (Anomaly 6).
- passportreader: the `zzbbz.zzu`/`zzbdl.zzc` callers pass the same `zzg` key; I did not enumerate every `zzbbz` entry point, only the three `zzbbe.zzb` call sites and the single `zzg` writer (the `iput-object` at `zzbbz.zza` 0x009d is the only write in classes4.dex).
