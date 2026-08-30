# ECGenParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `ECGenParameterSpecSpec-weak-curve.txt` | introduced | — | c1:ECGENPARAMETERSPEC-ALG-00 |
| `ECGenParameterSpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `ECGenParameterSpecSpec-weak-curve.txt` (A) `new ECGenParameterSpec("secp192r1") -> curve`
- `ECGenParameterSpecSpec.txt` (A) `new ECGenParameterSpec("secp256r1") -> curve`

## Envelopes

- `ECGenParameterSpecSpec-weak-curve.txt` (B) `spec=ECGenParameterSpecSpec,ev=c1,type=UnsafeAlgorithm,msg=v=1 code=ECGENPARAMETERSPEC-ALG-00 ev=c1 obj=ECGenParameterSpec val='secp192r1' exp='brainpoolP224r1,1.3.36.3.3.2.8.1.1.5,brainpoolP256r1,1.3.36.3.3.2.8.1.1.7,brainpoolP320r1,1.3.36.3.3.2.8.1.1.9,brainpoolP384r1,1.3.36.3.3.2.8.1.1.11,brainpoolP512r1,1.3.36.3.3.2.8.1.1.13,secp224r1,NIST P-224,1.3.132.0.33,secp256r1,NIST P-256,X9.62 prime256v1,1.2.840.10045.3.1.7,secp384r1,NIST P-384,1.3.132.0.34,secp521r1,NIST P-521,1.3.132.0.35' msg='the elliptic curve standard name is not one the rule admits'`
