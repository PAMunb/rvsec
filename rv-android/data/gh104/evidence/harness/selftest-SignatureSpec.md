# SignatureSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 12

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-d15-md5withrsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `SignatureSpec-d15-nonewithrsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `SignatureSpec-d15-sha1withdsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-generated-privkey.txt` | unchanged | gpr:? | gpr:? |
| `SignatureSpec-generated-pubkey.txt` | unchanged | gpu:? | gpu:? |
| `SignatureSpec-guard-on-field.txt` | unchanged | i1:?, i1:? | i1:?, i1:? |
| `SignatureSpec-initsign-after-sign.txt` | unchanged | i1:? | i1:? |
| `SignatureSpec-sha512withdsa-no-init.txt` | unchanged | g3:? | g3:? |
| `SignatureSpec-sha512withdsa.txt` | unchanged | g3:?, i1:? | g3:?, i1:? |
| `SignatureSpec-sign-unobserved.txt` | unchanged | — | — |
| `SignatureSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SignatureSpec-d15-md5withrsa.txt` — `s.sign() -> out`
- `SignatureSpec-d15-md5withrsa.txt` — `s.sign() -> out`
- `SignatureSpec-d15-nonewithrsa.txt` — `s.sign() -> out`
- `SignatureSpec-d15-nonewithrsa.txt` — `s.sign() -> out`
- `SignatureSpec-d15-sha1withdsa.txt` — `s.sign() -> out`
- `SignatureSpec-d15-sha1withdsa.txt` — `s.sign() -> out`
- `SignatureSpec-ecdsa.txt` — `s.sign() -> out`
- `SignatureSpec-ecdsa.txt` — `s.sign() -> out`
- `SignatureSpec-generated-privkey.txt` — `s.sign() -> out`
- `SignatureSpec-generated-privkey.txt` — `s.sign() -> out`
- `SignatureSpec-initsign-after-sign.txt` — `s.sign() -> out`
- `SignatureSpec-initsign-after-sign.txt` — `s.sign() -> out`
- `SignatureSpec-sha512withdsa.txt` — `s.sign() -> out`
- `SignatureSpec-sha512withdsa.txt` — `s.sign() -> out`
- `SignatureSpec-sign-unobserved.txt` — `s.sign() -> out`
- `SignatureSpec-sign-unobserved.txt` — `s.sign() -> out`
- `SignatureSpec.txt` — `s.sign() -> out`
- `SignatureSpec.txt` — `s.sign() -> out`

## Envelopes

- `SignatureSpec-d15-md5withrsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-md5withrsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found MD5withRSA.`
- `SignatureSpec-d15-md5withrsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-md5withrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found MD5withRSA.`
- `SignatureSpec-d15-nonewithrsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-nonewithrsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found NONEwithRSA.`
- `SignatureSpec-d15-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found NONEwithRSA.`
- `SignatureSpec-d15-sha1withdsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-sha1withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA1withDSA.`
- `SignatureSpec-d15-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-d15-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA1withDSA.`
- `SignatureSpec-generated-privkey.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-generated-privkey.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-generated-pubkey.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-generated-pubkey.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found .`
- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found .`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-initsign-after-sign.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-initsign-after-sign.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-sha512withdsa-no-init.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-sha512withdsa-no-init.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA512withDSA.`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA512withDSA.`
