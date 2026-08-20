# MessageDigestSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 6

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MessageDigestSpec-guard-on-field.txt` | unchanged | MessageDigestSpec.update | MessageDigestSpec.update |
| `MessageDigestSpec-md5-only.txt` | unchanged | — | — |
| `MessageDigestSpec-md5.txt` | unchanged | — | — |
| `MessageDigestSpec-reset.txt` | removed | MessageDigestSpec.reset | — |
| `MessageDigestSpec-sha1.txt` | unchanged | — | — |
| `MessageDigestSpec.txt` | unchanged | — | — |

## Self-contradicting envelopes

- `MessageDigestSpec-guard-on-field.txt` — a: self-contradicting envelope -- val ∈ exp: observed 'sha-256' is listed in ['md5', 'sha-1', 'sha-224', 'sha-256', 'sha-384', 'sha-512']
- `MessageDigestSpec-guard-on-field.txt` — b: self-contradicting envelope -- val ∈ exp: observed 'sha-256' is listed in ['md5', 'sha-1', 'sha-224', 'sha-256', 'sha-384', 'sha-512']

## Lines no pointcut resolved

- `MessageDigestSpec-reset.txt` — `md.reset()`

## Envelopes

- `MessageDigestSpec-guard-on-field.txt` (A) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=v=1 code=MESSAGEDIGEST-ALG-00 ev=update obj=MessageDigest val='SHA-256' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found SHA-256'`
- `MessageDigestSpec-guard-on-field.txt` (B) `spec=MessageDigestSpec,ev=update,type=UnsafeAlgorithm,msg=v=1 code=MESSAGEDIGEST-ALG-00 ev=update obj=MessageDigest val='SHA-256' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found SHA-256'`
- `MessageDigestSpec-reset.txt` (A) `spec=MessageDigestSpec,ev=reset,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MESSAGEDIGEST-ORDER-00 ev=reset obj=MessageDigest val='' exp='' msg='the observed call sequence is not one MessageDigestSpec accepts'`
