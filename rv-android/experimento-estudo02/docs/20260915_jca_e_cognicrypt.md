# `jca` do artigo, valores do `jca_android` e CogniCrypt — números do relatório executivo

Gerado por `experimento-estudo02/scripts/jca_e_cognicrypt.py`. Os mecanismos estão explicados nas seções 7 e 8 de `20260915_relatorio_executivo.md`; aqui estão só as contagens.

## 1. `jca`: as acusações publicadas do artigo, por mecanismo

Arquivo: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv` (somente leitura). 97018 linhas, **28930 maus usos por execução**, em 113 apps.

### Por tipo de erro combinado dentro do mau uso

| tipos | maus usos |
|---|---|
| InvalidSequenceOfMethodCalls | 15879 |
| InvalidSequenceOfMethodCalls+UnsafeAlgorithm | 7606 |
| InvalidSequenceOfMethodCalls+UnsafeProtocol | 4507 |
| InvalidKeyStoreType+InvalidSequenceOfMethodCalls | 927 |
| InvalidKeySize+InvalidSequenceOfMethodCalls | 7 |
| UnsafeAlgorithm | 3 |
| UnsafeProtocol | 1 |

### Por grupo

| group | maus usos | % |
|---|---|---|
| A | 12358 | 42.7 |
| B | 9000 | 31.1 |
| C | 4145 | 14.3 |
| D | 2705 | 9.4 |
| resto | 722 | 2.5 |

### Por mecanismo

| group | bucket | maus usos |
|---|---|---|
| A | SSLContext "TLS" fora da lista | 4385 |
| A | SSLContext só ORDER (getInstance("TLS")) | 3967 |
| A | KeyStore só ORDER | 2771 |
| A | KeyStore AndroidKeyStore | 927 |
| A | TrustManagerFactory X509 | 308 |
| B | algoritmo vazio ("found .") | 4545 |
| B | SecureRandomSpec só ORDER | 4455 |
| C | CipherSpec só ORDER | 4145 |
| D | MD5/SHA-1 | 2705 |
| resto | KeyPairSpec só ORDER | 258 |
| resto | MacSpec só ORDER | 166 |
| resto | MessageDigestSpec só ORDER | 91 |
| resto | CipherSpec: expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} | 89 |
| resto | SSLContext "SSL" | 77 |
| resto | SignatureSpec só ORDER | 26 |
| resto | SignatureSpec: expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384wit | 8 |
| resto | KeyPairGeneratorSpec: invalid key size for algorithm RSA. | 5 |
| resto | KeyPairGeneratorSpec: invalid key size for algorithm DSA. | 2 |

### Em quantos apps

- `jca`: 113 de 163 apps com alguma acusação; `jca_android` (bruto da `estudo02`): 91 de 163.
- Nos 162 apps em comum: nos dois 90; só no `jca` 22; só no `jca_android` 1.
- Apps do `jca` só com acusações dos grupos A e B: 54; com algo em C, D ou resto: 59.

### Algoritmo vazio por spec

| spec | maus usos |
|---|---|
| MacSpec | 31 |
| MessageDigestSpec | 75 |
| SSLContextSpec | 46 |
| SignatureSpec | 99 |
| TrustManagerFactorySpec | 4294 |

### Trechos com mais maus usos só de ORDER

| spec | class | method | maus usos |
|---|---|---|---|
| SSLContextSpec | okhttp3.internal.platform.Platform | newSSLContext | 3764 |
| SecureRandomSpec | kotlin.uuid.UuidKt__UuidJVMKt | secureRandomBytes | 1948 |
| SecureRandomSpec | kotlin.uuid.UuidKt__UuidJVMKt | secureRandomUuid | 780 |
| KeyStoreSpec | androidx.security.crypto.MasterKeys | keyExists | 689 |
| SecureRandomSpec | com.google.crypto.tink.subtle.Random | randBytes | 626 |
| CipherSpec | com.google.crypto.tink.integration.android.AndroidKeystoreAesGcm | encryptInternal | 625 |
| CipherSpec | com.google.crypto.tink.integration.android.AndroidKeystoreAesGcm | decryptInternal | 625 |
| KeyStoreSpec | com.google.crypto.tink.integration.android.AndroidKeystoreKmsClient$Builder | <init> | 624 |
| CipherSpec | com.google.crypto.tink.subtle.PrfAesCmac | generateSubKeys | 539 |
| CipherSpec | com.google.crypto.tink.subtle.PrfAesCmac | compute | 443 |
| CipherSpec | com.google.crypto.tink.subtle.AesSiv | encryptDeterministically | 442 |
| CipherSpec | com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce | encrypt | 241 |
| SecureRandomSpec | com.google.android.gms.measurement.internal.zzgi | zzi | 213 |
| KeyStoreSpec | okhttp3.tls.internal.TlsUtil | newEmptyKeyStore | 198 |
| SSLContextSpec | okhttp3.internal.platform.AndroidPlatform | getSSLContext | 197 |
| MacSpec | io.ktor.network.tls.HashesKt | P_hash | 163 |
| KeyPairSpec | io.ktor.network.tls.TLSClientHandshakeKt | generateECKeys | 162 |
| CipherSpec | com.google.crypto.tink.aead.internal.InsecureNonceAesGcmJce | decrypt | 103 |
| KeyStoreSpec | com.darkrockstudios.app.securecamera.security.SecurityLevelDetector | getKeyStore | 99 |
| KeyStoreSpec | com.google.crypto.tink.integration.android.AndroidKeystore | getAndroidKeyStore | 99 |

## 2. `jca_android`: acusações de valor na `estudo02`

Linhas ALG/PROTO/KEYSIZE: **19448**; com valor vazio: **0**; do `TrustManagerFactorySpec`: **0**.

| spec | val | linhas |
|---|---|---|
| MessageDigestSpec | MD5 | 8866 |
| MessageDigestSpec | SHA-1 | 5860 |
| CipherSpec | AES/ECB/NoPadding | 2675 |
| RSAKeyGenParameterSpecSpec | 3072 | 1095 |
| MessageDigestSpec | SHA1 | 503 |
| SecretKeyFactorySpec | PBEWITHSHAAND256BITAES-CBC-BC | 227 |
| SSLContextSpec | SSL | 96 |
| CipherSpec | RSA/ECB/OAEPWithSHA1AndMGF1Padding | 92 |
| AlgorithmParametersSpec | GCM | 17 |
| MacSpec | HmacSHA1 | 6 |
| SecretKeySpecSpec | RAW | 6 |
| MessageDigestSpec | SHA | 3 |
| SecretKeyFactorySpec | PBKDF2WithHmacSHA1 | 1 |
| SignatureSpec | NONEWITHRSA | 1 |

## 3. CogniCrypt 5.0.1 sobre o corpus

Arquivos de relatório: 197; apps da campanha com relatório: **144 de 163**; apps com algum achado: 82.

Achados: **1708**; `RequiredPredicateError`: **758** (44.4 %); desses, `SSLContext` + `TrustManagerFactory`: 652 (86.0 %); em classes do okhttp: 619 (81.7 %).

### Por tipo de erro

| tipo | achados |
|---|---|
| RequiredPredicateError | 758 |
| TypestateError | 323 |
| ConstraintError | 243 |
| IncompleteOperationError | 204 |
| ImpreciseValueExtractionError | 180 |

### `RequiredPredicateError` por regra

| regra | achados |
|---|---|
| javax.net.ssl.SSLContext | 520 |
| javax.net.ssl.TrustManagerFactory | 132 |
| javax.crypto.Cipher | 23 |
| javax.crypto.spec.SecretKeySpec | 18 |
| javax.crypto.Mac | 15 |
| java.security.KeyFactory | 13 |
| javax.crypto.spec.IvParameterSpec | 8 |
| javax.crypto.KeyAgreement | 7 |
| javax.net.ssl.KeyManagerFactory | 6 |
| javax.crypto.spec.GCMParameterSpec | 4 |
| javax.crypto.SecretKeyFactory | 4 |
| java.security.KeyPair | 2 |
| java.security.AlgorithmParameters | 2 |
| java.security.cert.PKIXParameters | 1 |
| java.security.spec.X509EncodedKeySpec | 1 |
| java.security.KeyPairGenerator | 1 |
| javax.crypto.spec.PBEKeySpec | 1 |

### `RequiredPredicateError` por método

| ViolatedRule | Class | Method | achados |
|---|---|---|---|
| javax.net.ssl.SSLContext | okhttp3.internal.platform.Platform | <okhttp3.internal.platform.Platform: javax.net.ssl.SSLSocketFactory newSslSocketFactory(javax.net.ssl.X509TrustManager)> | 360 |
| javax.net.ssl.SSLContext | okhttp3.internal.platform.ConscryptPlatform | <okhttp3.internal.platform.ConscryptPlatform: javax.net.ssl.SSLSocketFactory newSslSocketFactory(javax.net.ssl.X509TrustManager)> | 63 |
| javax.net.ssl.TrustManagerFactory | okhttp3.internal.platform.Platform | <okhttp3.internal.platform.Platform: javax.net.ssl.X509TrustManager platformTrustManager()> | 54 |
| javax.net.ssl.SSLContext | okhttp3.OkHttpClient | <okhttp3.OkHttpClient: javax.net.ssl.SSLSocketFactory newSslSocketFactory(javax.net.ssl.X509TrustManager)> | 33 |
| javax.net.ssl.SSLContext | okhttp3.tls.HandshakeCertificates | <okhttp3.tls.HandshakeCertificates: javax.net.ssl.SSLContext sslContext()> | 32 |
| javax.net.ssl.TrustManagerFactory | okhttp3.internal.platform.BouncyCastlePlatform | <okhttp3.internal.platform.BouncyCastlePlatform: javax.net.ssl.X509TrustManager platformTrustManager()> | 21 |
| javax.net.ssl.TrustManagerFactory | okhttp3.internal.platform.OpenJSSEPlatform | <okhttp3.internal.platform.OpenJSSEPlatform: javax.net.ssl.X509TrustManager platformTrustManager()> | 21 |
| javax.net.ssl.TrustManagerFactory | okhttp3.internal.platform.ConscryptPlatform | <okhttp3.internal.platform.ConscryptPlatform: javax.net.ssl.X509TrustManager platformTrustManager()> | 21 |
| javax.crypto.Mac | com.google.crypto.tink.subtle.Hkdf | <com.google.crypto.tink.subtle.Hkdf: byte[] computeHkdf(java.lang.String,byte[],byte[],byte[],int)> | 6 |
| javax.net.ssl.KeyManagerFactory | okhttp3.tls.internal.TlsUtil | <okhttp3.tls.internal.TlsUtil: javax.net.ssl.X509KeyManager newKeyManager(java.lang.String,okhttp3.tls.HeldCertificate,java.security.cert.X509Certificate[])> | 6 |
| javax.net.ssl.TrustManagerFactory | okhttp3.tls.internal.TlsUtil | <okhttp3.tls.internal.TlsUtil: javax.net.ssl.X509TrustManager newTrustManager(java.lang.String,java.util.List,java.util.List)> | 5 |
| javax.crypto.KeyAgreement | com.google.crypto.tink.subtle.EllipticCurves | <com.google.crypto.tink.subtle.EllipticCurves: byte[] computeSharedSecret(java.security.interfaces.ECPrivateKey,java.security.spec.ECPoint)> | 4 |

### `RequiredPredicateError` por mensagem

| mensagem | achados |
|---|---|
| First parameter was not properly generated as generatedKeyManagers | 181 |
| Second parameter was not properly generated as generatedTrustManagers | 181 |
| Third parameter was not properly generated as randomized | 158 |
| First parameter was not properly generated as generatedKeyStore | 139 |
| First parameter was not properly generated as preparedKeyMaterial | 19 |
| Second parameter was not properly generated as generatedKey | 18 |
| First parameter was not properly generated as speccedKey | 17 |
| First parameter was not properly generated as generatedKey | 15 |
| First parameter was not properly generated as randomized | 8 |
| First parameter was not properly generated as generatedPubkey | 6 |
| Second parameter was not properly generated as randomized | 5 |
| Third parameter was not properly generated as preparedGCM | 3 |
