# Batch L5_apps_crypto_a: NOBS sites to read

## com.google.android.gms.internal.ads.zzbbe.zzb
- NOBS lines: 730; APKs (1): com.tananaev.passportreader_22.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 243, source lines {'com.google.android.gms:play-services-ads@@25.3.0:10': np.int64(243)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 243, source lines {'com.google.android.gms:play-services-ads@@25.3.0:10': np.int64(243)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 244, source lines {'com.google.android.gms:play-services-ads@@25.3.0:9': np.int64(244)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## org.quantumbadger.redreader.common.General.parseConfig
- NOBS lines: 462; APKs (1): org.quantumbadger.redreader_117.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 154, source lines {'General.kt:699': np.int64(154)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 154, source lines {'General.kt:702': np.int64(154)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 154, source lines {'General.kt:701': np.int64(154)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.android.vending.licensing.AESObfuscator.<init>
- NOBS lines: 1816; APKs (1): org.totschnig.myexpenses_858.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 454, source lines {'AESObfuscator.java:63': np.int64(227), 'AESObfuscator.java:65': np.int64(227)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-00** (spec `IvChainJunctionSpec`, event `use`), lines 227, source lines {'AESObfuscator.java:63': np.int64(227)}
  - expects: an IvParameterSpec built over an observed randomized iv
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/CBC/PKCS5Padding']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 454, source lines {'AESObfuscator.java:63': np.int64(227), 'AESObfuscator.java:65': np.int64(227)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 227, source lines {'AESObfuscator.java:59': np.int64(227)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 227, source lines {'AESObfuscator.java:60': np.int64(227)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBEWITHSHAAND256BITAES-CBC-BC']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 227, source lines {'AESObfuscator.java:61': np.int64(227)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.leekleak.trafficlight.database.CryptoManager.decrypt
- NOBS lines: 800; APKs (1): com.leekleak.trafficlight_38.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 204, source lines {'CryptoManager.kt:61': np.int64(204)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 298, source lines {'CryptoManager.kt:61': np.int64(298)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 298, source lines {'CryptoManager.kt:61': np.int64(298)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## me.diamondforge.tokn.security.KeystoreManager.encrypt
- NOBS lines: 137; APKs (1): me.diamondforge.tokn_19.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 137, source lines {'KeystoreManager.kt:55': np.int64(137)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## me.diamondforge.tokn.security.KeystoreManager.decrypt
- NOBS lines: 909; APKs (1): me.diamondforge.tokn_19.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 303, source lines {'KeystoreManager.kt:68': np.int64(303)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 303, source lines {'KeystoreManager.kt:68': np.int64(303)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 303, source lines {'KeystoreManager.kt:68': np.int64(303)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## rocks.poopjournal.metadataremover.viewmodel.MainViewModel.<clinit>
- NOBS lines: 264; APKs (1): rocks.poopjournal.metadataremover_20020.apk
- **SECURERANDOM-NOBS-01** (spec `SecureRandomSpec`, event `c2`), lines 264, source lines {'MainViewModel.kt:46': np.int64(264)}
  - expects: a randomized byte[]
  - msg: the constructor expects a byte array observed to come from a randomized source
  - observed val(s): ['']

## com.afkanerd.smswithoutborders_libsmsmms.data.Cryptography.encryptWithKeyStore
- NOBS lines: 169; APKs (1): com.afkanerd.deku_83.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 169, source lines {'Cryptography.kt:78': np.int64(169)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.afkanerd.smswithoutborders_libsmsmms.data.Cryptography.decryptWithKeyStore
- NOBS lines: 645; APKs (1): com.afkanerd.deku_83.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 215, source lines {'Cryptography.kt:109': np.int64(215)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 215, source lines {'Cryptography.kt:108': np.int64(215)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 215, source lines {'Cryptography.kt:109': np.int64(215)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## dev.leonlatsch.photok.encryption.domain.crypto.KeyGen.generateVaultMasterKey
- NOBS lines: 47; APKs (1): dev.leonlatsch.photok_62.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 47, source lines {'KeyGen.kt:32': np.int64(47)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## dev.leonlatsch.photok.encryption.domain.crypto.KeyGen.derivePasswordKeyEncryptionKey
- NOBS lines: 153; APKs (1): dev.leonlatsch.photok_62.apk
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 51, source lines {'KeyGen.kt:43': np.int64(51)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 51, source lines {'KeyGen.kt:44': np.int64(51)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBKDF2WithHmacSHA256']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 51, source lines {'KeyGen.kt:46': np.int64(51)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## dev.leonlatsch.photok.encryption.domain.handlers.PasswordVaultProtectionHandler.create
- NOBS lines: 47; APKs (1): dev.leonlatsch.photok_62.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 47, source lines {'PasswordVaultProtectionHandler.kt:104': np.int64(47)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## dev.leonlatsch.photok.encryption.domain.handlers.PasswordVaultProtectionHandler.unlock
- NOBS lines: 153; APKs (1): dev.leonlatsch.photok_62.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 51, source lines {'PasswordVaultProtectionHandler.kt:70': np.int64(51)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 51, source lines {'PasswordVaultProtectionHandler.kt:70': np.int64(51)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 51, source lines {'PasswordVaultProtectionHandler.kt:74': np.int64(51)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## github.paroj.dsub2000.util.KeyStoreUtil.decrypt
- NOBS lines: 285; APKs (1): github.paroj.dsub2000_217.apk
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 285, source lines {'KeyStoreUtil.java:135': np.int64(285)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
