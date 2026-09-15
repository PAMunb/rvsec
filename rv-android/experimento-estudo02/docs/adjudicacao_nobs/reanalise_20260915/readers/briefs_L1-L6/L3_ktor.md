# Batch L3_ktor: NOBS sites to read

## io.ktor.network.tls.TLSConfigBuilderKt.findTrustManager
- NOBS lines: 227; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 227, source lines {'TLSConfigBuilder.kt:159': np.int64(219), 'TLSConfigBuilder.kt:153': np.int64(8)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## io.ktor.network.tls.TLSClientHandshakeKt.generateECKeys
- NOBS lines: 228; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **KEYFACTORY-NOBS-01** (spec `KeyFactorySpec`, event `genPublic`), lines 228, source lines {'TLSClientHandshake.kt:523': np.int64(139), 'TLSClientHandshake.kt:522': np.int64(80), 'TLSClientHandshake.kt:496': np.int64(9)}
  - expects: a key spec this instrumentation observed being built from key material
  - msg: no construction of the key spec was observed
  - observed val(s): ['EC']

## io.ktor.network.tls.TLSClientHandshake.generatePreSecret
- NOBS lines: 228; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **KEYAGREEMENT-NOBS-08** (spec `KeyAgreementSpec`, event `dophase`), lines 228, source lines {'TLSClientHandshake.kt:363': np.int64(139), 'TLSClientHandshake.kt:362': np.int64(80), 'TLSClientHandshake.kt:338': np.int64(9)}
  - expects: a public key this instrumentation observed being generated
  - msg: no generation of the public key given to doPhase was observed
  - observed val(s): ['ECDH']

## io.ktor.network.tls.TLSClientHandshake.handleServerDone
- NOBS lines: 228; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 228, source lines {'TLSClientHandshake.kt:340': np.int64(139), 'TLSClientHandshake.kt:339': np.int64(80), 'TLSClientHandshake.kt:316': np.int64(9)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## io.ktor.network.tls.HashesKt.P_hash
- NOBS lines: 456; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 456, source lines {'Hashes.kt:26': np.int64(219), 'Hashes.kt:31': np.int64(219), 'Hashes.kt:23': np.int64(6), 'Hashes.kt:28': np.int64(6)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSHA256', 'HmacSHA384']

## io.ktor.network.tls.KeysKt.masterSecret
- NOBS lines: 228; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 228, source lines {'Keys.kt:69': np.int64(228)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## io.ktor.network.tls.KeysKt.clientKey
- NOBS lines: 228; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **SECRETKEYSPEC-NOBS-01** (spec `SecretKeySpecSpec`, event `c2`), lines 228, source lines {'Keys.kt:37': np.int64(228)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## io.ktor.network.tls.cipher.GCMCipherKt.gcmEncryptCipher
- NOBS lines: 684; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 228, source lines {'GCMCipher.kt:74': np.int64(228)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 228, source lines {'GCMCipher.kt:73': np.int64(228)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 228, source lines {'GCMCipher.kt:74': np.int64(228)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## io.ktor.network.tls.KeysKt.serverKey
- NOBS lines: 225; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **SECRETKEYSPEC-NOBS-01** (spec `SecretKeySpecSpec`, event `c2`), lines 225, source lines {'Keys.kt:30': np.int64(225)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], int, int, String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## io.ktor.network.tls.cipher.GCMCipherKt.gcmDecryptCipher
- NOBS lines: 675; APKs (4): com.mateusrodcosta.apps.vidyamusic_2200.apk, com.sapuseven.untis_29198884.apk, com.serwylo.beatgame_35.apk, com.serwylo.retrowars_70.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 225, source lines {'GCMCipher.kt:107': np.int64(225)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 225, source lines {'GCMCipher.kt:105': np.int64(225)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 225, source lines {'GCMCipher.kt:107': np.int64(225)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## io.ktor.util.NonceKt$nonceGeneratorJob$1.invokeSuspend
- NOBS lines: 9; APKs (1): com.serwylo.retrowars_70.apk
- **SECURERANDOM-NOBS-00** (spec `SecureRandomSpec`, event `setSeed2`), lines 9, source lines {'Nonce.kt:43': np.int64(3), 'Nonce.kt:63': np.int64(3), 'Nonce.kt:66': np.int64(3)}
  - expects: a randomized byte[]
  - msg: setSeed() expects a byte array observed to come from a randomized source
  - observed val(s): ['']
