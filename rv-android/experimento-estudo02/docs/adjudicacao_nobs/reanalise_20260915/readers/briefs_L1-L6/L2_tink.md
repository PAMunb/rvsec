# Batch L2_tink: NOBS sites to read

## com.google.crypto.tink.integration.android.AndroidKeystoreAesGcm.decryptInternal
- NOBS lines: 2536; APKs (8): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.celzero.bravedns_619.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk, org.openhab.habdroid_589.apk
- **GCMPARAMETERSPEC-NOBS-01** (spec `GCMParameterSpecSpec`, event `c2`), lines 1268, source lines {'AndroidKeystoreAesGcm.java:113': np.int64(1055), 'AndroidKeystoreAesGcm.java:110': np.int64(213)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 1268, source lines {'AndroidKeystoreAesGcm.java:116': np.int64(1055), 'AndroidKeystoreAesGcm.java:113': np.int64(213)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## com.google.crypto.tink.subtle.PrfAesCmac.<init>
- NOBS lines: 1180; APKs (7): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk, org.openhab.habdroid_589.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 1180, source lines {'PrfAesCmac.java:57': np.int64(966), 'PrfAesCmac.java:50': np.int64(214)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.PrfAesCmac.generateSubKeys
- NOBS lines: 1180; APKs (7): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk, org.openhab.habdroid_589.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 1180, source lines {'PrfAesCmac.java:110': np.int64(966), 'PrfAesCmac.java:103': np.int64(214)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce.<init>
- NOBS lines: 966; APKs (6): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 966, source lines {'InsecureNonceAesGcmJce.java:66': np.int64(966)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.PrfAesCmac.compute
- NOBS lines: 967; APKs (7): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk, org.openhab.habdroid_589.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 967, source lines {'PrfAesCmac.java:69': np.int64(966), 'PrfAesCmac.java:62': np.int64(1)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesSiv.encryptDeterministically
- NOBS lines: 3865; APKs (7): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, com.tk.quicksearch_65.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk, org.openhab.habdroid_589.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 966, source lines {'AesSiv.java:119': np.int64(965), 'AesSiv.java:109': np.int64(1)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-00** (spec `IvChainJunctionSpec`, event `use`), lines 966, source lines {'AesSiv.java:119': np.int64(965), 'AesSiv.java:109': np.int64(1)}
  - expects: an IvParameterSpec built over an observed randomized iv
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/CTR/NoPadding']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 966, source lines {'AesSiv.java:119': np.int64(965), 'AesSiv.java:109': np.int64(1)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 967, source lines {'AesSiv.java:119': np.int64(966), 'AesSiv.java:109': np.int64(1)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce.encrypt
- NOBS lines: 357; APKs (5): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 357, source lines {'InsecureNonceAesGcmJce.java:93': np.int64(357)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce.getParams
- NOBS lines: 463; APKs (5): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk
- **GCMPARAMETERSPEC-NOBS-01** (spec `GCMParameterSpecSpec`, event `c2`), lines 463, source lines {'InsecureNonceAesGcmJce.java:159': np.int64(463)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']

## com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce.decrypt
- NOBS lines: 926; APKs (5): app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, com.afkanerd.deku_83.apk, dev.dettmer.simplenotes_41.apk, org.css_apps_m3.password_manager_16.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 463, source lines {'InsecureNonceAesGcmJce.java:136': np.int64(463)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 463, source lines {'InsecureNonceAesGcmJce.java:136': np.int64(463)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## com.google.crypto.tink.subtle.AesSiv.decryptDeterministically
- NOBS lines: 204; APKs (1): app.maskan.chat_90.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 68, source lines {'AesSiv.java:143': np.int64(68)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 68, source lines {'AesSiv.java:143': np.int64(68)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 68, source lines {'AesSiv.java:143': np.int64(68)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.integration.android.AndroidKeystore$AeadImpl.decrypt
- NOBS lines: 528; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **GCMPARAMETERSPEC-NOBS-01** (spec `GCMParameterSpecSpec`, event `c2`), lines 264, source lines {'AndroidKeystore.java:175': np.int64(264)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 264, source lines {'AndroidKeystore.java:178': np.int64(264)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## com.google.crypto.tink.prf.internal.PrfAesCmac.<init>
- NOBS lines: 264; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 264, source lines {'PrfAesCmac.java:76': np.int64(264)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.prf.internal.PrfAesCmac.generateSubKeys
- NOBS lines: 264; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 264, source lines {'PrfAesCmac.java:155': np.int64(264)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.aead.internal.AesGcmJceUtil.getSecretKey
- NOBS lines: 264; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 264, source lines {'AesGcmJceUtil.java:57': np.int64(264)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.prf.internal.PrfAesCmac.compute
- NOBS lines: 264; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 264, source lines {'PrfAesCmac.java:106': np.int64(264)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesSiv.encryptInternal
- NOBS lines: 1056; APKs (1): com.hegocre.nextcloudpasswords_38.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 264, source lines {'AesSiv.java:191': np.int64(264)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-00** (spec `IvChainJunctionSpec`, event `use`), lines 264, source lines {'AesSiv.java:191': np.int64(264)}
  - expects: an IvParameterSpec built over an observed randomized iv
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/CTR/NoPadding']
- **IVPARAMETERSPEC-NOBS-00** (spec `IvParameterSpecSpec`, event `c1`), lines 264, source lines {'AesSiv.java:191': np.int64(264)}
  - expects: a randomized byte[]
  - msg: no randomized source of the iv given to IvParameterSpec(byte[]) was observed
  - observed val(s): ['']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 264, source lines {'AesSiv.java:191': np.int64(264)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesGcmJce.<init>
- NOBS lines: 214; APKs (1): org.openhab.habdroid_589.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 214, source lines {'AesGcmJce.java:54': np.int64(214)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesGcmJce.encrypt
- NOBS lines: 1; APKs (1): org.openhab.habdroid_589.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 1, source lines {'AesGcmJce.java:73': np.int64(1)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']

## com.google.crypto.tink.subtle.Hkdf.computeHkdf
- NOBS lines: 136; APKs (1): org.css_apps_m3.password_manager_16.apk
- **MAC-NOBS-00** (spec `MacSpec`, event `i1`), lines 68, source lines {'Hkdf.java:59': np.int64(34), 'Hkdf.java:65': np.int64(34)}
  - expects: a key observed coming from a key generator, a key store or a key specification
  - msg: the key given to Mac.init was not observed coming from a key generator, a key store or a key specification
  - observed val(s): ['HmacSha256']
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 68, source lines {'Hkdf.java:59': np.int64(34), 'Hkdf.java:65': np.int64(34)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesGcmHkdfStreaming.deriveKeySpec
- NOBS lines: 34; APKs (1): org.css_apps_m3.password_manager_16.apk
- **SECRETKEYSPEC-NOBS-00** (spec `SecretKeySpecSpec`, event `c1`), lines 34, source lines {'AesGcmHkdfStreaming.java:192': np.int64(34)}
  - expects: prepared key material
  - msg: the keyMaterial given to SecretKeySpec(byte[], String) was not observed to have been prepared by a Key.getEncoded()
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesGcmHkdfStreaming.paramsForSegment
- NOBS lines: 34; APKs (1): org.css_apps_m3.password_manager_16.apk
- **GCMPARAMETERSPEC-NOBS-00** (spec `GCMParameterSpecSpec`, event `c1`), lines 34, source lines {'AesGcmHkdfStreaming.java:183': np.int64(34)}
  - expects: a randomized byte[]
  - msg: the IV material was not observed to come from a randomized source
  - observed val(s): ['']

## com.google.crypto.tink.subtle.AesGcmHkdfStreaming$AesGcmHkdfStreamEncrypter.encryptSegment
- NOBS lines: 68; APKs (1): org.css_apps_m3.password_manager_16.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 34, source lines {'AesGcmHkdfStreaming.java:234': np.int64(34)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 34, source lines {'AesGcmHkdfStreaming.java:234': np.int64(34)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']

## com.google.crypto.tink.subtle.AesGcmHkdfStreaming$AesGcmHkdfStreamDecrypter.decryptSegment
- NOBS lines: 28; APKs (1): org.css_apps_m3.password_manager_16.apk
- **CIPHER-NOBS-00** (spec `CipherSpec`, event `i2`), lines 14, source lines {'AesGcmHkdfStreaming.java:299': np.int64(14)}
  - expects: a key produced by one of the generators the rule names
  - msg: no generator of the key given to Cipher.init was observed
  - observed val(s): ['']
- **IVCHAINJUNCTION-NOBS-01** (spec `IvChainJunctionSpec`, event `use`), lines 14, source lines {'AesGcmHkdfStreaming.java:299': np.int64(14)}
  - expects: a GCMParameterSpec built over an observed randomized source
  - msg: no preparation of the AlgorithmParameterSpec given to Cipher.init was observed
  - observed val(s): ['AES/GCM/NoPadding']
