# Batch L6_apps_crypto_b: NOBS sites to read

## com.gelakinetic.mtgfam.helpers.tcgp.MarketPriceFetcher$1.fetch
- NOBS lines: 10; APKs (1): com.gelakinetic.mtgfam_99.apk
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 5, source lines {'MarketPriceFetcher.java:126': np.int64(5)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 5, source lines {'MarketPriceFetcher.java:125': np.int64(5)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.gelakinetic.mtgfam.helpers.tcgp.MarketPriceFetcher.decrypt
- NOBS lines: 5; APKs (1): com.gelakinetic.mtgfam_99.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 5, source lines {'MarketPriceFetcher.java:474': np.int64(5)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## org.spongycastle.jcajce.provider.asymmetric.x509.X509CertificateObject.checkSignature
- NOBS lines: 233; APKs (1): com.tananaev.passportreader_22.apk
- **SIGNATURE-NOBS-02** (spec `SignatureSpec`, event `i4`), lines 233, source lines {'X509CertificateObject.java:805': np.int64(233)}
  - expects: a public key produced by one of the generators the rule names
  - msg: no generator of the public key given to initVerify was observed
  - observed val(s): ['SHA256WITHRSA']

## io.treehouses.remote.ssh.Encryptor.encrypt
- NOBS lines: 4; APKs (1): io.treehouses.remote_6098.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 1, source lines {'Encryptor.kt:81': np.int64(1)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-00** (spec `IvChainJunctionSpec`, event `use`), lines 1, source lines {'Encryptor.kt:81': np.int64(1)}
  - expects: an IvParameterSpec built over an observed randomized iv
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/CBC/PKCS5Padding']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 1, source lines {'Encryptor.kt:84': np.int64(1)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 1, source lines {'Encryptor.kt:83': np.int64(1)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## org.fedorahosted.freeotp.encryptor.MasterKey.<init>
- NOBS lines: 17; APKs (1): org.fedorahosted.freeotp_48.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 17, source lines {'MasterKey.java:43': np.int64(17)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## org.fedorahosted.freeotp.encryptor.MasterKey.decrypt
- NOBS lines: 34; APKs (1): org.fedorahosted.freeotp_48.apk
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 17, source lines {'MasterKey.java:72': np.int64(17)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 17, source lines {'MasterKey.java:64': np.int64(17)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBKDF2withHmacSHA512']

## org.fedorahosted.freeotp.encryptor.EncryptedKey.decrypt
- NOBS lines: 51; APKs (1): org.fedorahosted.freeotp_48.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 34, source lines {'EncryptedKey.java:51': np.int64(17), 'EncryptedKey.java:57': np.int64(17)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 17, source lines {'EncryptedKey.java:59': np.int64(17)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## ua.com.radiokot.photoprism.features.ext.key.activation.logic.ParseEnteredKeyUseCase.getIssuerPublicKey$lambda$0
- NOBS lines: 2; APKs (1): ua.com.radiokot.photoprism_67.apk
- **KEYFACTORY-NOBS-01** (spec `KeyFactorySpec`, event `genPublic`), lines 1, source lines {'ParseEnteredKeyUseCase.kt:96': np.int64(1)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['RSA']
- **X509ENCODEDKEYSPEC-NOBS-00** (spec `X509EncodedKeySpecSpec`, event `c1`), lines 1, source lines {'ParseEnteredKeyUseCase.kt:97': np.int64(1)}
  - expects: key material the monitor observed being prepared
  - msg: no preparation of the encoded key material was observed
  - observed val(s): ['']

## app.michaelwuensch.bitbanana.util.UtilFunctions.encodePbkdf2
- NOBS lines: 2; APKs (1): app.michaelwuensch.bitbanana_79.apk
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 1, source lines {'UtilFunctions.java:93': np.int64(1)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 1, source lines {'UtilFunctions.java:95': np.int64(1)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBKDF2WithHmacSHA1']

## com.nononsenseapps.feeder.crypto.AesCbcWithIntegrity.generateKey
- NOBS lines: 108; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 108, source lines {'AesCbcWithIntegrity.kt:130': np.int64(108)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.nononsenseapps.feeder.crypto.AesCbcWithIntegrity.decodeKey
- NOBS lines: 4; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 2, source lines {'AesCbcWithIntegrity.kt:98': np.int64(2)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-01** (spec `SecretKeySpecSpec`, event `c2`), lines 2, source lines {'AesCbcWithIntegrity.kt:97': np.int64(2)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.nononsenseapps.feeder.crypto.AesCbcWithIntegrity.encrypt
- NOBS lines: 1; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 1, source lines {'AesCbcWithIntegrity.kt:289': np.int64(1)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.nononsenseapps.feeder.crypto.AesCbcWithIntegrity.generateMac
- NOBS lines: 2; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 2, source lines {'AesCbcWithIntegrity.kt:395': np.int64(2)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSHA256']

## com.nononsenseapps.feeder.crypto.AesCbcWithIntegrity.decrypt
- NOBS lines: 4; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 2, source lines {'AesCbcWithIntegrity.kt:363': np.int64(2)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 2, source lines {'AesCbcWithIntegrity.kt:366': np.int64(2)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']

## com.craxiom.networksurvey.util.CryptoManager.encrypt
- NOBS lines: 3; APKs (1): com.craxiom.networksurvey_114.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 3, source lines {'CryptoManager.kt:74': np.int64(3)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.craxiom.networksurvey.util.CryptoManager.decrypt
- NOBS lines: 6; APKs (1): com.craxiom.networksurvey_114.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 2, source lines {'CryptoManager.kt:109': np.int64(2)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 2, source lines {'CryptoManager.kt:108': np.int64(2)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 2, source lines {'CryptoManager.kt:109': np.int64(2)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## dev.whyoleg.cryptography.providers.jdk.algorithms.JdkPbkdf2SecretDerivation.deriveSecretToByteArrayBlocking
- NOBS lines: 2; APKs (1): com.darkrockstudios.app.securecamera_31.apk
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 1, source lines {'JdkPbkdf2.kt:40': np.int64(1)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 1, source lines {'JdkPbkdf2.kt:46': np.int64(1)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBKDF2WithHmacSHA256']

## se.arctosoft.vault.encryption.Encryption.getDirHash
- NOBS lines: 47; APKs (1): se.arctosoft.vault_41.apk
- **PBEKEYSPEC-NOBS-01** (spec `PBEKeySpecSpec`, event `c1`), lines 24, source lines {'Encryption.java:689': np.int64(24)}
  - expects: a randomized byte[]
  - msg: the second argument was not observed to come from a randomized source
  - observed val(s): ['']
- **SECRETKEYFACTORY-NOBS-00** (spec `SecretKeyFactorySpec`, event `gen`), lines 23, source lines {'Encryption.java:690': np.int64(23)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['PBKDF2withHmacSHA512']

## org.bouncycastle.operator.jcajce.JcaContentVerifierProviderBuilder$1.get
- NOBS lines: 1; APKs (1): systems.sieber.droid_scep_7.apk
- **SIGNATURE-NOBS-02** (spec `SignatureSpec`, event `i4`), lines 1, source lines {'Unknown Source:46': np.int64(1)}
  - expects: a public key produced by one of the generators the rule names
  - msg: no generator of the public key given to initVerify was observed
  - observed val(s): ['SHA256WITHRSA']

## org.bouncycastle.operator.jcajce.JcaContentVerifierProviderBuilder.createRawSig
- NOBS lines: 1; APKs (1): systems.sieber.droid_scep_7.apk
- **SIGNATURE-NOBS-02** (spec `SignatureSpec`, event `i4`), lines 1, source lines {'Unknown Source:13': np.int64(1)}
  - expects: a public key produced by one of the generators the rule names
  - msg: no generator of the public key given to initVerify was observed
  - observed val(s): ['NONEWITHRSA']

## org.cry.otp.HOTP.hmac_sha1
- NOBS lines: 2; APKs (1): org.cry.otp_31.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 1, source lines {'HOTP.java:32': np.int64(1)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSHA1']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 1, source lines {'HOTP.java:32': np.int64(1)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## org.cry.otp.TOTP.hmac_sha
- NOBS lines: 6; APKs (1): org.cry.otp_31.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 3, source lines {'TOTP.java:46': np.int64(3)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSHA1']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 3, source lines {'TOTP.java:46': np.int64(3)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.beemdevelopment.aegis.crypto.otp.HOTP.getHash
- NOBS lines: 4; APKs (1): com.beemdevelopment.aegis_81.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 2, source lines {'HOTP.java:41': np.int64(2)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSHA1']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 2, source lines {'HOTP.java:32': np.int64(2)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.beemdevelopment.aegis.crypto.CryptoUtils.deriveKey
- NOBS lines: 6; APKs (1): com.beemdevelopment.aegis_81.apk
- **SECRETKEYSPEC-NOBS-01** (spec `SecretKeySpecSpec`, event `c2`), lines 6, source lines {'CryptoUtils.java:38': np.int64(6)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.beemdevelopment.aegis.crypto.CryptoUtils.createCipher
- NOBS lines: 6; APKs (1): com.beemdevelopment.aegis_81.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 2, source lines {'CryptoUtils.java:66': np.int64(2)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 2, source lines {'CryptoUtils.java:66': np.int64(2)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 2, source lines {'CryptoUtils.java:66': np.int64(2)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## org.flyve.inventory.CryptoUtil.stringToPublicKey
- NOBS lines: 184; APKs (1): org.glpi.inventory.agent_39469.apk
- **KEYFACTORY-NOBS-01** (spec `KeyFactorySpec`, event `genPublic`), lines 92, source lines {'CryptoUtil.java:110': np.int64(92)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['RSA']
- **X509ENCODEDKEYSPEC-NOBS-00** (spec `X509EncodedKeySpecSpec`, event `c1`), lines 92, source lines {'CryptoUtil.java:108': np.int64(92)}
  - expects: key material the monitor observed being prepared
  - msg: no preparation of the encoded key material was observed
  - observed val(s): ['']

## org.flyve.inventory.CryptoUtil.encrypt
- NOBS lines: 92; APKs (1): org.glpi.inventory.agent_39469.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 92, source lines {'CryptoUtil.java:83': np.int64(92)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
