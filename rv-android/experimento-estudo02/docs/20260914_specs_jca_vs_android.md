# Maus usos por spec: `jca` (artigo) × `jca_android` (estudo02)

162 APKs em comum; fora da comparação: com.shatteredpixel.shatteredpixeldungeon_896.apk, info.dvkr.screenstream_44000.apk.

| spec | linhas jca | linhas android | Σ por run jca | Σ por run android | pontos jca | pontos android | APKs jca | APKs android |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SSLContextSpec | 26312 | 26962 | 8475 | 4638 | 125 | 69 | 62 | 61 |
| TrustManagerFactorySpec | 18029 | 37735 | 4602 | 4798 | 70 | 71 | 64 | 63 |
| SecureRandomSpec | 12222 | 5921 | 4356 | 799 | 52 | 11 | 42 | 6 |
| CipherSpec | 10923 | 18099 | 4234 | 3396 | 72 | 67 | 21 | 25 |
| KeyStoreSpec | 10660 | 0 | 3698 | 0 | 52 | 0 | 22 | 0 |
| MessageDigestSpec | 16183 | 25166 | 2871 | 3650 | 55 | 61 | 38 | 34 |
| KeyPairSpec | 668 | 875 | 258 | 267 | 8 | 7 | 8 | 7 |
| MacSpec | 837 | 2316 | 197 | 225 | 8 | 9 | 7 | 8 |
| SignatureSpec | 990 | 251 | 133 | 108 | 9 | 6 | 4 | 3 |
| KeyPairGeneratorSpec | 16 | 0 | 7 | 0 | 2 | 0 | 2 | 0 |
| AlgorithmParametersSpec | 0 | 34 | 0 | 34 | 0 | 2 | 0 | 1 |
| IvParameterSpecSpec | 0 | 2493 | 0 | 1029 | 0 | 17 | 0 | 16 |
| IvChainJunctionSpec | 0 | 4774 | 0 | 2111 | 0 | 39 | 0 | 19 |
| GCMParameterSpecSpec | 0 | 3302 | 0 | 1450 | 0 | 28 | 0 | 17 |
| KeyAgreementSpec | 0 | 228 | 0 | 184 | 0 | 4 | 0 | 4 |
| PBEKeySpecSpec | 0 | 549 | 0 | 175 | 0 | 6 | 0 | 6 |
| KeyManagerFactorySpec | 0 | 3012 | 0 | 323 | 0 | 5 | 0 | 5 |
| KeyFactorySpec | 0 | 321 | 0 | 265 | 0 | 6 | 0 | 6 |
| SecretKeySpecSpec | 0 | 6142 | 0 | 3263 | 0 | 59 | 0 | 22 |
| SecretKeyFactorySpec | 0 | 548 | 0 | 175 | 0 | 6 | 0 | 6 |
| RSAKeyGenParameterSpecSpec | 0 | 1095 | 0 | 97 | 0 | 1 | 0 | 1 |
| X509EncodedKeySpecSpec | 0 | 93 | 0 | 81 | 0 | 2 | 0 | 2 |
| **total** | 96840 | 139916 | 28831 | 27068 | 453 | 476 | | |

Sem a spec na chave — distintos (class, method) por run, somados: jca 28809, android 21934.

## Pontos (apk, class, method)

jca 449, android 373, em ambos 273; só no jca 176; só no android 100.

### Só o `jca` acusa, por spec que acusava

| specs | pontos | APKs |
|---|---:|---:|
| SSLContextSpec | 58 | 57 |
| KeyStoreSpec | 50 | 22 |
| SecureRandomSpec | 44 | 40 |
| CipherSpec | 12 | 12 |
| MessageDigestSpec | 6 | 4 |
| SignatureSpec | 4 | 2 |
| KeyPairSpec | 1 | 1 |
| TrustManagerFactorySpec | 1 | 1 |

### Só o `jca_android` acusa, por spec que acusa

| specs | pontos | APKs |
|---|---:|---:|
| SecretKeySpecSpec | 38 | 16 |
| MessageDigestSpec | 12 | 9 |
| CipherSpec,GCMParameterSpecSpec,IvChainJunctionSpec | 10 | 6 |
| GCMParameterSpecSpec | 6 | 5 |
| KeyManagerFactorySpec | 5 | 5 |
| PBEKeySpecSpec,SecretKeyFactorySpec | 4 | 4 |
| CipherSpec | 4 | 4 |
| KeyAgreementSpec | 4 | 4 |
| SecureRandomSpec | 3 | 3 |
| SSLContextSpec | 2 | 2 |
| TrustManagerFactorySpec | 2 | 2 |
| KeyFactorySpec,X509EncodedKeySpecSpec | 2 | 2 |
| CipherSpec,IvParameterSpecSpec | 1 | 1 |
| CipherSpec,IvChainJunctionSpec,IvParameterSpecSpec,PBEKeySpecSpec,SecretKeyFactorySpec,SecretKeySpecSpec | 1 | 1 |
| CipherSpec,IvParameterSpecSpec,SecretKeySpecSpec | 1 | 1 |
| IvParameterSpecSpec,SecretKeySpecSpec | 1 | 1 |
| MacSpec | 1 | 1 |
| PBEKeySpecSpec,SecretKeyFactorySpec,SecretKeySpecSpec | 1 | 1 |
| RSAKeyGenParameterSpecSpec | 1 | 1 |
| SignatureSpec | 1 | 1 |

