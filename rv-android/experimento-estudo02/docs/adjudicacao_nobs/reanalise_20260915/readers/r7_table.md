| spec | code | class.method | category | security_relevant | runkeys (lines/apks) | evidence file:line | confidence |
|---|---|---|---|---|---|---|---|
| AlgorithmParametersSpec | ALG-00 | EncryptedKey.decrypt | GENUINE_PER_RULE | no | 17 (17/1) | EncryptedKey.java:54 | high |
| AlgorithmParametersSpec | ORDER-00 | EncryptedKey.<init> | UNOBSERVED_CREATION |  | 17 (17/1) | EncryptedKey.java:32 | high |
| CipherSpec | ALG-01 | PrfAesCmac.generateSubKeys | GENUINE_PER_RULE | no | 546 (1180/7) | PrfAesCmac.java:110 | high |
| CipherSpec | ALG-01 | PrfAesCmac.compute | GENUINE_PER_RULE | no | 448 (967/7) | PrfAesCmac.java:69 | high |
| CipherSpec | ALG-01 | PrfAesCmac.compute | GENUINE_PER_RULE | no | 99 (264/1) | PrfAesCmac.java:106 | high |
| CipherSpec | ALG-01 | PrfAesCmac.generateSubKeys | GENUINE_PER_RULE | no | 99 (264/1) | PrfAesCmac.java:155 | high |
| CipherSpec | ALG-01 | CryptoUtil.encrypt | GENUINE_PER_RULE | debatable | 80 (92/1) | CryptoUtil.java:83 | high |
| CipherSpec | CONSTR-00 | EncryptedKey.encrypt | GENUINE_PER_RULE | no | 17 (17/1) | EncryptedKey.java:42 | high |
| CipherSpec | ORDER-00 | PrfAesCmac.generateSubKeys | CASCADE_OF_VALUE_FAILURE |  | 546 (2360/7) | PrfAesCmac.java:110 | high |
| CipherSpec | ORDER-00 | PrfAesCmac.compute | CASCADE_OF_VALUE_FAILURE |  | 448 (2901/7) | PrfAesCmac.java:69 | high |
| CipherSpec | ORDER-00 | InsecureNonceAesGcmJce.encrypt | LEGAL_REUSE_REJECTED |  | 112 (242/4) | InsecureNonceAesGcmJce.java:93 | high |
| CipherSpec | ORDER-00 | PrfAesCmac.compute | CASCADE_OF_VALUE_FAILURE |  | 99 (792/1) | PrfAesCmac.java:106 | high |
| CipherSpec | ORDER-00 | PrfAesCmac.generateSubKeys | CASCADE_OF_VALUE_FAILURE |  | 99 (528/1) | PrfAesCmac.java:155 | high |
| CipherSpec | ORDER-00 | zzbbe.zzb | LEGAL_REUSE_REJECTED |  | 98 (486/1) | com.google.android.gms:play-services-ads@@25.3.0:10 | high |
| CipherSpec | ORDER-00 | InsecureNonceAesGcmJce.decrypt | LEGAL_REUSE_REJECTED |  | 86 (276/4) | InsecureNonceAesGcmJce.java:136 | high |
| CipherSpec | ORDER-00 | CryptoUtil.encrypt | CASCADE_OF_VALUE_FAILURE |  | 80 (184/1) | CryptoUtil.java:83 | high |
| CipherSpec | ORDER-00 | AesSiv.encryptInternal | LEGAL_REUSE_REJECTED |  | 57 (124/1) | AesSiv.java:191 | high |
| CipherSpec | ORDER-00 | CryptoUtils.encrypt | CASCADE_OF_VALUE_FAILURE |  | 6 (6/1) | CryptoUtils.java:78 | high |
| CipherSpec | ORDER-00 | AesGcmJce.encrypt | LEGAL_REUSE_REJECTED |  | 1 (2/1) | AesGcmJce.java:73 | high |
| KeyPairSpec | ORDER-00 | TLSClientHandshakeKt.generateECKeys | UNOBSERVED_CREATION |  | 185 (685/4) | TLSClientHandshake.kt:525 | high |
| KeyPairSpec | ORDER-00 | CryptoUtil.generateKeyPair | UNOBSERVED_CREATION |  | 80 (184/1) | CryptoUtil.java:65 | high |
| KeyPairSpec | ORDER-00 | BaseSSHKeyGen.generateKey | UNOBSERVED_CREATION |  | 1 (2/1) | BaseSSHKeyGen.kt:115 | high |
| KeyPairSpec | ORDER-00 | ScepClient.CertReq | UNOBSERVED_CREATION |  | 1 (4/1) | ScepClient.java:135 | high |
| MacSpec | ALG-00 | TOTP.hmac_sha | GENUINE_PER_RULE | no | 3 (3/1) | TOTP.java:46 | high |
| MacSpec | ALG-00 | HOTP.getHash | GENUINE_PER_RULE | no | 2 (2/1) | HOTP.java:41 | high |
| MacSpec | ALG-00 | HOTP.hmac_sha1 | GENUINE_PER_RULE | no | 1 (1/1) | HOTP.java:32 | high |
| MacSpec | ORDER-00 | HashesKt.P_hash | LEGAL_REUSE_REJECTED |  | 184 (1596/4) | Hashes.kt:31 | high |
| MacSpec | ORDER-00 | Hkdf.computeHkdf | LEGAL_REUSE_REJECTED |  | 34 (170/1) | Hkdf.java:65 | high |
| MacSpec | ORDER-00 | TOTP.hmac_sha | CASCADE_OF_VALUE_FAILURE |  | 3 (6/1) | TOTP.java:46 | high |
| MacSpec | ORDER-00 | HOTP.getHash | CASCADE_OF_VALUE_FAILURE |  | 2 (4/1) | HOTP.java:41 | high |
| MacSpec | ORDER-00 | HOTP.hmac_sha1 | CASCADE_OF_VALUE_FAILURE |  | 1 (2/1) | HOTP.java:32 | high |
| MessageDigestSpec | ALG-00 | ByteString.digest$okio | GENUINE_PER_RULE | no | 699 (1504/13) | ByteString.kt:83 | high |
| MessageDigestSpec | ALG-00 | CommonUtils.hash | GENUINE_PER_RULE | no | 297 (702/3) | CommonUtils.java:169 | high |
| MessageDigestSpec | ALG-00 | zzf.zzG | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads-api@@25.3.0:2 | high |
| MessageDigestSpec | ALG-00 | zzf.zzj | GENUINE_PER_RULE | no | 99 (490/1) | com.google.android.gms:play-services-ads-api@@25.3.0:6 | high |
| MessageDigestSpec | ALG-00 | zzazv.zze | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads@@25.3.0:5 | high |
| MessageDigestSpec | ALG-00 | AccessPointsAdapterData.calculateChildType | GENUINE_PER_RULE | no | 99 (180/1) | AccessPointsAdapterData.kt:68 | high |
| MessageDigestSpec | ALG-00 | HashUtils.digest | GENUINE_PER_RULE | no | 98 (162/1) | HashUtils.kt:18 | high |
| MessageDigestSpec | ALG-00 | AeSimpleSHA1.SHA1 | GENUINE_PER_RULE | no | 98 (172/1) | AeSimpleSHA1.java:16 | high |
| MessageDigestSpec | ALG-00 | Schedule$Item.hashCode | GENUINE_PER_RULE | no | 86 (117/1) | Schedule.java:1152 | high |
| MessageDigestSpec | ALG-00 | GettersKt.getChecksum | GENUINE_PER_RULE | no | 64 (156/1) | Getters.kt:135 | high |
| MessageDigestSpec | ALG-00 | GraphWrapper.calculateGraphType | GENUINE_PER_RULE | no | 54 (107/1) | GraphWrapper.kt:168 | high |
| MessageDigestSpec | ALG-00 | PatternLockUtils.patternToSha1 | GENUINE_PER_RULE | yes | 5 (5/1) | PatternLockUtils.java:91 | high |
| MessageDigestSpec | ALG-00 | PinTab.getHashedPin | GENUINE_PER_RULE | yes | 4 (4/1) | PinTab.kt:135 | high |
| MessageDigestSpec | ALG-00 | ExtensionFunctionsKt.getCurrentSignatures | GENUINE_PER_RULE | no | 1 (1/1) | ExtensionFunctions.kt:298 | high |
| MessageDigestSpec | ALG-00 | DigestImpl.plusAssign-impl | GENUINE_PER_RULE | no | 1 (1/1) | CryptoJvm.kt:51 | high |
| MessageDigestSpec | ALG-01 | zzgi.zzh | GENUINE_PER_RULE | no | 212 (551/3) | com.google.android.gms:play-services-measurement-impl@@23.2.0:29 | high |
| MessageDigestSpec | ALG-01 | AndroidUtilsLight.getPackageCertificateHashBytes | GENUINE_PER_RULE | no | 198 (257/2) | com.google.android.gms:play-services-basement@@18.9.0:4 | high |
| MessageDigestSpec | ALG-01 | StringUtils.calculateStringHash | GENUINE_PER_RULE | no | 101 (125/2) | StringUtils.java:132 | high |
| MessageDigestSpec | ALG-01 | zzop.zza | GENUINE_PER_RULE | no | 99 (164/1) | com.google.android.gms:play-services-measurement-impl@@22.1.0:176 | high |
| MessageDigestSpec | ALG-01 | Util.md5Hex | GENUINE_PER_RULE | debatable | 99 (282/1) | Util.java:1007 | high |
| MessageDigestSpec | ALG-01 | APKParser.getCertificateFingerprint | GENUINE_PER_RULE | no | 73 (106/1) | APKParser.java:124 | high |
| MessageDigestSpec | ALG-01 | General.sha1 | GENUINE_PER_RULE | no | 69 (86/1) | General.kt:540 | high |
| MessageDigestSpec | ALG-01 | DiskCache.getCacheFile | GENUINE_PER_RULE | no | 55 (56/1) | DiskCache.kt:63 | high |
| MessageDigestSpec | ALG-01 | HashUtils$Companion$getHashPrefixAndSuffix$2.invokeSuspend | GENUINE_PER_RULE | no | 48 (63/1) | HashUtils.kt:34 | high |
| MessageDigestSpec | ALG-01 | Helper.getFingerprint | GENUINE_PER_RULE | no | 43 (47/1) | Helper.java:3308 | high |
| MessageDigestSpec | ALG-01 | FileBasedConfig.hash | GENUINE_PER_RULE | no | 5 (5/1) | FileBasedConfig.java:208 | high |
| MessageDigestSpec | ALG-01 | ByteString.digest$jvm | GENUINE_PER_RULE | no | 3 (3/1) | ByteString.kt:103 | high |
| MessageDigestSpec | ALG-01 | MiscUtilsKt.getMd5 | GENUINE_PER_RULE | no | 1 (1/1) | MiscUtils.kt:71 | high |
| MessageDigestSpec | ALG-02 | ByteString.digest$okio | GENUINE_PER_RULE | no | 698 (1503/13) | ByteString.kt:82 | high |
| MessageDigestSpec | ALG-02 | CommonUtils.hash | GENUINE_PER_RULE | no | 297 (702/3) | CommonUtils.java:159 | high |
| MessageDigestSpec | ALG-02 | AndroidUtilsLight.zza | GENUINE_PER_RULE | no | 198 (257/2) | com.google.android.gms:play-services-basement@@18.9.0:1 | high |
| MessageDigestSpec | ALG-02 | zzpp.zzQ | GENUINE_PER_RULE | no | 113 (306/2) | com.google.android.gms:play-services-measurement-impl@@23.2.0:1 | high |
| MessageDigestSpec | ALG-02 | StringUtils.calculateStringHash | GENUINE_PER_RULE | no | 101 (125/2) | StringUtils.java:127 | high |
| MessageDigestSpec | ALG-02 | zzf.zzG | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads-api@@25.3.0:1 | high |
| MessageDigestSpec | ALG-02 | zzf.zzj | GENUINE_PER_RULE | no | 99 (245/1) | com.google.android.gms:play-services-ads-api@@25.3.0:5 | high |
| MessageDigestSpec | ALG-02 | zzazu.run | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads@@25.3.0:1 | high |
| MessageDigestSpec | ALG-02 | zzop.zzu | GENUINE_PER_RULE | no | 99 (164/1) | com.google.android.gms:play-services-measurement-impl@@22.1.0:492 | high |
| MessageDigestSpec | ALG-02 | zzpp.zzO | GENUINE_PER_RULE | no | 99 (245/1) | com.google.android.gms:play-services-measurement-impl@@23.0.0:1 | high |
| MessageDigestSpec | ALG-02 | AccessPointsAdapterData.calculateChildType | GENUINE_PER_RULE | no | 99 (180/1) | AccessPointsAdapterData.kt:67 | high |
| MessageDigestSpec | ALG-02 | Util.md5Hex | GENUINE_PER_RULE | debatable | 99 (282/1) | Util.java:1006 | high |
| MessageDigestSpec | ALG-02 | HashUtils.digest | GENUINE_PER_RULE | no | 98 (162/1) | HashUtils.kt:15 | high |
| MessageDigestSpec | ALG-02 | AeSimpleSHA1.SHA1 | GENUINE_PER_RULE | no | 98 (172/1) | AeSimpleSHA1.java:14 | high |
| MessageDigestSpec | ALG-02 | Schedule$Item.hashCode | GENUINE_PER_RULE | no | 86 (117/1) | Schedule.java:1151 | high |
| MessageDigestSpec | ALG-02 | APKParser.getCertificateFingerprint | GENUINE_PER_RULE | no | 73 (106/1) | APKParser.java:122 | high |
| MessageDigestSpec | ALG-02 | General.sha1 | GENUINE_PER_RULE | no | 69 (86/1) | General.kt:536 | high |
| MessageDigestSpec | ALG-02 | GettersKt.getChecksum | GENUINE_PER_RULE | no | 64 (156/1) | Getters.kt:130 | high |
| MessageDigestSpec | ALG-02 | DiskCache.getCacheFile | GENUINE_PER_RULE | no | 55 (56/1) | DiskCache.kt:62 | high |
| MessageDigestSpec | ALG-02 | GraphWrapper.calculateGraphType | GENUINE_PER_RULE | no | 53 (106/1) | GraphWrapper.kt:167 | high |
| MessageDigestSpec | ALG-02 | AppModuleKt.appModule$lambda$0$3 | GENUINE_PER_RULE | no | 48 (63/1) | AppModule.kt:32 | high |
| MessageDigestSpec | ALG-02 | Helper.getFingerprint | GENUINE_PER_RULE | no | 43 (47/1) | Helper.java:3307 | high |
| MessageDigestSpec | ALG-02 | PatternLockUtils.patternToSha1 | GENUINE_PER_RULE | yes | 5 (5/1) | PatternLockUtils.java:90 | high |
| MessageDigestSpec | ALG-02 | Constants.newMessageDigest | GENUINE_PER_RULE | no | 5 (5/1) | Constants.java:501 | high |
| MessageDigestSpec | ALG-02 | PinTab.getHashedPin | GENUINE_PER_RULE | yes | 4 (4/1) | PinTab.kt:134 | high |
| MessageDigestSpec | ALG-02 | ByteString.digest$jvm | GENUINE_PER_RULE | no | 3 (3/1) | ByteString.kt:103 | high |
| MessageDigestSpec | ALG-02 | ExtensionFunctionsKt.getCurrentSignatures | GENUINE_PER_RULE | no | 1 (1/1) | ExtensionFunctions.kt:297 | high |
| MessageDigestSpec | ALG-02 | CryptoKt__CryptoJvmKt.Digest | GENUINE_PER_RULE | no | 1 (1/1) | CryptoJvm.kt:47 | high |
| MessageDigestSpec | ALG-02 | MiscUtilsKt.getMd5 | GENUINE_PER_RULE | no | 1 (1/1) | MiscUtils.kt:71 | high |
| MessageDigestSpec | ALG-03 | ByteString.digest$okio | GENUINE_PER_RULE | no | 699 (1504/13) | ByteString.kt:84 | high |
| MessageDigestSpec | ALG-03 | CommonUtils.hash | GENUINE_PER_RULE | no | 297 (702/3) | CommonUtils.java:171 | high |
| MessageDigestSpec | ALG-03 | zzf.zzG | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads-api@@25.3.0:3 | high |
| MessageDigestSpec | ALG-03 | zzf.zzj | GENUINE_PER_RULE | no | 99 (245/1) | com.google.android.gms:play-services-ads-api@@25.3.0:8 | high |
| MessageDigestSpec | ALG-03 | zzazv.zze | GENUINE_PER_RULE | no | 99 (244/1) | com.google.android.gms:play-services-ads@@25.3.0:6 | high |
| MessageDigestSpec | ALG-03 | AccessPointsAdapterData.calculateChildType | GENUINE_PER_RULE | no | 99 (180/1) | AccessPointsAdapterData.kt:72 | high |
| MessageDigestSpec | ALG-03 | HashUtils.digest | GENUINE_PER_RULE | no | 98 (162/1) | HashUtils.kt:19 | high |
| MessageDigestSpec | ALG-03 | AeSimpleSHA1.SHA1 | GENUINE_PER_RULE | no | 98 (172/1) | AeSimpleSHA1.java:17 | high |
| MessageDigestSpec | ALG-03 | Schedule$Item.hashCode | GENUINE_PER_RULE | no | 86 (117/1) | Schedule.java:1153 | high |
| MessageDigestSpec | ALG-03 | GettersKt.getChecksum | GENUINE_PER_RULE | no | 62 (121/1) | Getters.kt:138 | high |
| MessageDigestSpec | ALG-03 | GraphWrapper.calculateGraphType | GENUINE_PER_RULE | no | 54 (107/1) | GraphWrapper.kt:172 | high |
| MessageDigestSpec | ALG-03 | PatternLockUtils.patternToSha1 | GENUINE_PER_RULE | yes | 5 (5/1) | PatternLockUtils.java:93 | high |
| MessageDigestSpec | ALG-03 | PinTab.getHashedPin | GENUINE_PER_RULE | yes | 4 (4/1) | PinTab.kt:136 | high |
| MessageDigestSpec | ALG-03 | ExtensionFunctionsKt.getCurrentSignatures | GENUINE_PER_RULE | no | 1 (1/1) | ExtensionFunctions.kt:299 | high |
| MessageDigestSpec | ALG-03 | DigestImpl.build-impl | GENUINE_PER_RULE | no | 1 (1/1) | CryptoJvm.kt:58 | high |
| MessageDigestSpec | ORDER-00 | ByteString.digest$okio | CASCADE_OF_VALUE_FAILURE |  | 699 (3010/13) | ByteString.kt:83 | high |
| MessageDigestSpec | ORDER-00 | CommonUtils.hash | CASCADE_OF_VALUE_FAILURE |  | 297 (1404/3) | CommonUtils.java:169 | high |
| MessageDigestSpec | ORDER-00 | zzgi.zzh | CASCADE_OF_VALUE_FAILURE |  | 212 (551/3) | com.google.android.gms:play-services-measurement-impl@@23.2.0:29 | high |
| MessageDigestSpec | ORDER-00 | AndroidUtilsLight.getPackageCertificateHashBytes | CASCADE_OF_VALUE_FAILURE |  | 198 (257/2) | com.google.android.gms:play-services-basement@@18.9.0:4 | high |
| MessageDigestSpec | ORDER-00 | StringUtils.calculateStringHash | CASCADE_OF_VALUE_FAILURE |  | 101 (125/2) | StringUtils.java:132 | high |
| MessageDigestSpec | ORDER-00 | zzf.zzG | CASCADE_OF_VALUE_FAILURE |  | 99 (488/1) | com.google.android.gms:play-services-ads-api@@25.3.0:2 | high |
| MessageDigestSpec | ORDER-00 | zzf.zzj | CASCADE_OF_VALUE_FAILURE |  | 99 (735/1) | com.google.android.gms:play-services-ads-api@@25.3.0:6 | high |
| MessageDigestSpec | ORDER-00 | zzazv.zze | CASCADE_OF_VALUE_FAILURE |  | 99 (488/1) | com.google.android.gms:play-services-ads@@25.3.0:5 | high |
| MessageDigestSpec | ORDER-00 | zzop.zza | CASCADE_OF_VALUE_FAILURE |  | 99 (164/1) | com.google.android.gms:play-services-measurement-impl@@22.1.0:176 | high |
| MessageDigestSpec | ORDER-00 | AccessPointsAdapterData.calculateChildType | CASCADE_OF_VALUE_FAILURE |  | 99 (360/1) | AccessPointsAdapterData.kt:68 | high |
| MessageDigestSpec | ORDER-00 | Util.md5Hex | CASCADE_OF_VALUE_FAILURE |  | 99 (282/1) | Util.java:1007 | high |
| MessageDigestSpec | ORDER-00 | HashUtils.digest | CASCADE_OF_VALUE_FAILURE |  | 98 (324/1) | HashUtils.kt:18 | high |
| MessageDigestSpec | ORDER-00 | AeSimpleSHA1.SHA1 | CASCADE_OF_VALUE_FAILURE |  | 98 (344/1) | AeSimpleSHA1.java:16 | high |
| MessageDigestSpec | ORDER-00 | Schedule$Item.hashCode | CASCADE_OF_VALUE_FAILURE |  | 86 (234/1) | Schedule.java:1152 | high |
| MessageDigestSpec | ORDER-00 | FileID$Companion.createFID | UNOBSERVED_CREATION |  | 75 (87/1) | FileID.kt:59 | high |
| MessageDigestSpec | ORDER-00 | FileID$Companion.createFID$lambda$0 | UNOBSERVED_CREATION |  | 74 (169/1) | FileID.kt:57 | high |
| MessageDigestSpec | ORDER-00 | APKParser.getCertificateFingerprint | CASCADE_OF_VALUE_FAILURE |  | 73 (106/1) | APKParser.java:124 | high |
| MessageDigestSpec | ORDER-00 | General.sha1 | CASCADE_OF_VALUE_FAILURE |  | 69 (86/1) | General.kt:540 | high |
| MessageDigestSpec | ORDER-00 | GettersKt.getChecksum | CASCADE_OF_VALUE_FAILURE |  | 64 (277/1) | Getters.kt:135 | high |
| MessageDigestSpec | ORDER-00 | DiskCache.getCacheFile | CASCADE_OF_VALUE_FAILURE |  | 55 (56/1) | DiskCache.kt:63 | high |
| MessageDigestSpec | ORDER-00 | GraphWrapper.calculateGraphType | CASCADE_OF_VALUE_FAILURE |  | 54 (214/1) | GraphWrapper.kt:168 | high |
| MessageDigestSpec | ORDER-00 | HashUtils$Companion$getHashPrefixAndSuffix$2.invokeSuspend | CASCADE_OF_VALUE_FAILURE |  | 48 (63/1) | HashUtils.kt:34 | high |
| MessageDigestSpec | ORDER-00 | Helper.getFingerprint | CASCADE_OF_VALUE_FAILURE |  | 43 (47/1) | Helper.java:3308 | high |
| MessageDigestSpec | ORDER-00 | MessageDigestHashFunction$MessageDigestHasher.hash | UNOBSERVED_CREATION |  | 14 (16/1) | MessageDigestHashFunction.java:167 | high |
| MessageDigestSpec | ORDER-00 | MessageDigestHashFunction$MessageDigestHasher.update | UNOBSERVED_CREATION |  | 14 (16/1) | MessageDigestHashFunction.java:149 | high |
| MessageDigestSpec | ORDER-00 | PatternLockUtils.patternToSha1 | CASCADE_OF_VALUE_FAILURE |  | 5 (10/1) | PatternLockUtils.java:91 | high |
| MessageDigestSpec | ORDER-00 | FileBasedConfig.hash | CASCADE_OF_VALUE_FAILURE |  | 5 (5/1) | FileBasedConfig.java:208 | high |
| MessageDigestSpec | ORDER-00 | PinTab.getHashedPin | CASCADE_OF_VALUE_FAILURE |  | 4 (8/1) | PinTab.kt:135 | high |
| MessageDigestSpec | ORDER-00 | ByteString.digest$jvm | CASCADE_OF_VALUE_FAILURE |  | 3 (3/1) | ByteString.kt:103 | high |
| MessageDigestSpec | ORDER-00 | ExtensionFunctionsKt.getCurrentSignatures | CASCADE_OF_VALUE_FAILURE |  | 1 (2/1) | ExtensionFunctions.kt:298 | high |
| MessageDigestSpec | ORDER-00 | DigestImpl.build-impl | CASCADE_OF_VALUE_FAILURE |  | 1 (1/1) | CryptoJvm.kt:58 | high |
| MessageDigestSpec | ORDER-00 | DigestImpl.plusAssign-impl | CASCADE_OF_VALUE_FAILURE |  | 1 (1/1) | CryptoJvm.kt:51 | high |
| MessageDigestSpec | ORDER-00 | MiscUtilsKt.getMd5 | CASCADE_OF_VALUE_FAILURE |  | 1 (1/1) | MiscUtils.kt:71 | high |
| PBEKeySpecSpec | PBEKEYSPEC-CONSTR-00 | AESObfuscator.<init> | GENUINE_PER_RULE | debatable | 99 (227/1) | AESObfuscator.java:59 | high |
| PBEKeySpecSpec | PBEKEYSPEC-CONSTR-00 | UtilFunctions.encodePbkdf2 | GENUINE_PER_RULE | debatable | 1 (1/1) | UtilFunctions.java:93 | high |
| RSAKeyGenParameterSpecSpec | RSAKEYGENPARAMETERSPEC-KEYSIZE-00 | CompositeIndex.<clinit> | GENUINE_PER_RULE | no | 97 (1095/1) | Unknown Source:358 | high |
| SSLContextSpec | FORB-00 | CustomCertService.<clinit> | GENUINE_PER_RULE | no | 5 (6/1) | CustomCertService.kt:65 | high |
| SSLContextSpec | ORDER-00 | CustomCertService.<clinit> | CASCADE_OF_VALUE_FAILURE |  | 5 (6/1) | CustomCertService.kt:65 | high |
| SSLContextSpec | PROTO-00 | OkHttpClientProvider.configureTrustAllCertificates | GENUINE_PER_RULE | yes | 75 (96/1) | OkHttpClientProvider.kt:74 | high |
| SecretKeyFactorySpec | ALG-00 | AESObfuscator.<init> | GENUINE_PER_RULE | debatable | 99 (227/1) | AESObfuscator.java:57 | high |
| SecretKeyFactorySpec | ALG-00 | UtilFunctions.encodePbkdf2 | GENUINE_PER_RULE | debatable | 1 (1/1) | UtilFunctions.java:94 | high |
| SecretKeySpecSpec | SECRETKEYSPEC-ALG-00 | TOTP.hmac_sha | GENUINE_PER_RULE | no | 3 (3/1) | TOTP.java:46 | high |
| SecretKeySpecSpec | SECRETKEYSPEC-ALG-00 | HOTP.getHash | GENUINE_PER_RULE | no | 2 (2/1) | HOTP.java:32 | high |
| SecretKeySpecSpec | SECRETKEYSPEC-ALG-00 | HOTP.hmac_sha1 | GENUINE_PER_RULE | no | 1 (1/1) | HOTP.java:32 | high |
| SecureRandomSpec | ORDER-00 | NonceKt$nonceGeneratorJob$1.invokeSuspend | ARTIFACT_OTHER |  | 102 (3324/2) | Nonce.kt:81 | high |
| SecureRandomSpec | ORDER-00 | BasicEntropySourceProvider$1.getEntropy | UNOBSERVED_CREATION |  | 99 (244/1) | BasicEntropySourceProvider.java:53 | high |
| SecureRandomSpec | ORDER-00 | DRBG.createBaseRandom | UNOBSERVED_CREATION |  | 99 (488/1) | DRBG.java:128 | high |
| SecureRandomSpec | ORDER-00 | DRBG$HybridSecureRandom.<init> | UNOBSERVED_CREATION |  | 99 (244/1) | DRBG.java:233 | high |
| SecureRandomSpec | ORDER-00 | DRBG$HybridSecureRandom$SignallingEntropySource.getEntropy | UNOBSERVED_CREATION |  | 99 (244/1) | DRBG.java:294 | high |
| SecureRandomSpec | ORDER-00 | DRBG$HybridSecureRandom$SignallingEntropySource$EntropyGatherer.run | UNOBSERVED_CREATION |  | 99 (244/1) | DRBG.java:326 | high |
| SecureRandomSpec | ORDER-00 | Encryptor.encrypt | ARTIFACT_OTHER |  | 1 (1/1) | Encryptor.kt:65 | high |
| SignatureSpec | ALG-03 | JcaContentVerifierProviderBuilder.createRawSig | GENUINE_PER_RULE | no | 1 (1/1) | Unknown Source:13 | high |
| SignatureSpec | ORDER-00 | OpenSSLX509Certificate.verifyInternal | ARTIFACT_OTHER |  | 5 (12/1) | OpenSSLX509Certificate.java:402 | high |
| SignatureSpec | ORDER-00 | SignatureUpdatingOutputStream.write | ARTIFACT_OTHER |  | 1 (2/1) | Unknown Source:8 | high |
| SignatureSpec | ORDER-00 | JcaContentSignerBuilder$1.getSignature | ARTIFACT_OTHER |  | 1 (1/1) | Unknown Source:7 | high |