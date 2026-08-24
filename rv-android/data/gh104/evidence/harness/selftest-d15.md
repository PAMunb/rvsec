# d15 — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 28

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `d15-CipherSpec-aes-ecb-nopadding.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-CipherSpec-aes-ecb-pkcs5.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-CipherSpec-arc4.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-CipherSpec-blowfish-ecb.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-CipherSpec-chacha20.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-CipherSpec-desede-cbc.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `d15-KeyGeneratorSpec-arc4.txt` | unchanged | gk1:?, init:? | gk1:?, init:? |
| `d15-KeyGeneratorSpec-desede.txt` | unchanged | gk1:?, init:? | gk1:?, init:? |
| `d15-KeyGeneratorSpec-hmacmd5.txt` | unchanged | gk1:?, init:? | gk1:?, init:? |
| `d15-KeyManagerFactorySpec-sunx509.txt` | unchanged | init:?, init:? | init:?, init:? |
| `d15-KeyPairGeneratorSpec-diffiehellman.txt` | unchanged | — | — |
| `d15-KeyPairGeneratorSpec-rsa-3072.txt` | unchanged | — | — |
| `d15-KeyStoreSpec-jks.txt` | unchanged | — | — |
| `d15-KeyStoreSpec-pkcs12.txt` | unchanged | — | — |
| `d15-MacSpec-hmacpbesha1.txt` | unchanged | update:? | update:? |
| `d15-MessageDigestSpec-md5.txt` | moved | update:?, update:? | g4:?, update:? |
| `d15-MessageDigestSpec-sha1-alias.txt` | moved | update:?, update:? | g4:?, update:? |
| `d15-MessageDigestSpec-sha1.txt` | moved | update:?, update:? | g4:?, update:? |
| `d15-SSLContextSpec-ssl.txt` | unchanged | init:?, init:? | init:?, init:? |
| `d15-SSLContextSpec-tlsv1.txt` | unchanged | init:?, init:? | init:?, init:? |
| `d15-SecretKeySpecSpec-aes.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |
| `d15-SecretKeySpecSpec-hmacsha256.txt` | unchanged | c3:?, c3:? | c3:?, c3:? |
| `d15-SecureRandomSpec-nativeprng.txt` | unchanged | — | — |
| `d15-SecureRandomSpec-windowsprng.txt` | unchanged | — | — |
| `d15-SignatureSpec-md5withrsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `d15-SignatureSpec-nonewithrsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `d15-SignatureSpec-sha1withdsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `d15-TrustManagerFactorySpec-sunx509.txt` | unchanged | init:?, init:? | init:?, init:? |

## Lines no pointcut resolved

- `d15-SignatureSpec-md5withrsa.txt` — `s.sign() -> out`
- `d15-SignatureSpec-md5withrsa.txt` — `s.sign() -> out`
- `d15-SignatureSpec-nonewithrsa.txt` — `s.sign() -> out`
- `d15-SignatureSpec-nonewithrsa.txt` — `s.sign() -> out`
- `d15-SignatureSpec-sha1withdsa.txt` — `s.sign() -> out`
- `d15-SignatureSpec-sha1withdsa.txt` — `s.sign() -> out`

## Envelopes

- `d15-CipherSpec-aes-ecb-nopadding.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/NoPadding.`
- `d15-CipherSpec-aes-ecb-nopadding.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-aes-ecb-nopadding.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/NoPadding.`
- `d15-CipherSpec-aes-ecb-nopadding.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-aes-ecb-pkcs5.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `d15-CipherSpec-aes-ecb-pkcs5.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-aes-ecb-pkcs5.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `d15-CipherSpec-aes-ecb-pkcs5.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-arc4.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found ARC4.`
- `d15-CipherSpec-arc4.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-arc4.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found ARC4.`
- `d15-CipherSpec-arc4.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-blowfish-ecb.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found BLOWFISH/ECB/NoPadding.`
- `d15-CipherSpec-blowfish-ecb.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-blowfish-ecb.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found BLOWFISH/ECB/NoPadding.`
- `d15-CipherSpec-blowfish-ecb.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-chacha20.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found ChaCha20.`
- `d15-CipherSpec-chacha20.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-chacha20.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found ChaCha20.`
- `d15-CipherSpec-chacha20.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-desede-cbc.txt` (A) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found DESede/CBC/PKCS5Padding.`
- `d15-CipherSpec-desede-cbc.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-CipherSpec-desede-cbc.txt` (B) `spec=CipherSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found DESede/CBC/PKCS5Padding.`
- `d15-CipherSpec-desede-cbc.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-arc4.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-arc4.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyGeneratorSpec-arc4.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-arc4.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyGeneratorSpec-desede.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-desede.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyGeneratorSpec-desede.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-desede.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyGeneratorSpec-hmacmd5.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-hmacmd5.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyGeneratorSpec-hmacmd5.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyGeneratorSpec-hmacmd5.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found .`
- `d15-KeyManagerFactorySpec-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `d15-KeyManagerFactorySpec-sunx509.txt` (A) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-KeyManagerFactorySpec-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg= expecting one of PKIX,SunX509 but found .`
- `d15-KeyManagerFactorySpec-sunx509.txt` (B) `spec=KeyManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-md5.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `d15-MessageDigestSpec-md5.txt` (A) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-md5.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.`
- `d15-MessageDigestSpec-md5.txt` (B) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-sha1-alias.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA1.`
- `d15-MessageDigestSpec-sha1-alias.txt` (A) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-sha1-alias.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA1.`
- `d15-MessageDigestSpec-sha1-alias.txt` (B) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-sha1.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1.`
- `d15-MessageDigestSpec-sha1.txt` (A) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-MessageDigestSpec-sha1.txt` (B) `spec=MessageDigestSpec,ev=g4,type=UnsafeAlgorithm,msg=expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1.`
- `d15-MessageDigestSpec-sha1.txt` (B) `spec=MessageDigestSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SSLContextSpec-ssl.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `d15-SSLContextSpec-ssl.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SSLContextSpec-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `d15-SSLContextSpec-ssl.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SSLContextSpec-tlsv1.txt` (A) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `d15-SSLContextSpec-tlsv1.txt` (A) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SSLContextSpec-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=UnsafeProtocol,msg=expecting one of {TLSv1.2, TLSv1.3} but found .`
- `d15-SSLContextSpec-tlsv1.txt` (B) `spec=SSLContextSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SecretKeySpecSpec-aes.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `d15-SecretKeySpecSpec-aes.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SecretKeySpecSpec-aes.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `d15-SecretKeySpecSpec-aes.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SecretKeySpecSpec-hmacsha256.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `d15-SecretKeySpecSpec-hmacsha256.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SecretKeySpecSpec-hmacsha256.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg= Using either an invalid algorithm or keyMaterial.length is not randomized.`
- `d15-SecretKeySpecSpec-hmacsha256.txt` (B) `spec=SecretKeySpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-md5withrsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-md5withrsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found MD5withRSA.`
- `d15-SignatureSpec-md5withrsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-md5withrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found MD5withRSA.`
- `d15-SignatureSpec-nonewithrsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-nonewithrsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found NONEwithRSA.`
- `d15-SignatureSpec-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found NONEwithRSA.`
- `d15-SignatureSpec-sha1withdsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-sha1withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA1withDSA.`
- `d15-SignatureSpec-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-SignatureSpec-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA1withDSA.`
- `d15-TrustManagerFactorySpec-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `d15-TrustManagerFactorySpec-sunx509.txt` (A) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `d15-TrustManagerFactorySpec-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=UnsafeAlgorithm,msg=expecting one of PKIX,SunX509 but found .`
- `d15-TrustManagerFactorySpec-sunx509.txt` (B) `spec=TrustManagerFactorySpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
