# RSAKeyGenParameterSpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `RSAKeyGenParameterSpecSpec-keysize-and-exponent.txt` | introduced | — | c1:RSAKEYGENPARAMETERSPEC-CONSTR-00, c1:RSAKEYGENPARAMETERSPEC-KEYSIZE-00 |
| `RSAKeyGenParameterSpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `RSAKeyGenParameterSpecSpec-keysize-and-exponent.txt` (A) `new RSAKeyGenParameterSpec(512, 3) -> params`
- `RSAKeyGenParameterSpecSpec.txt` (A) `new RSAKeyGenParameterSpec(2048, 65537) -> params`

## Envelopes

- `RSAKeyGenParameterSpecSpec-keysize-and-exponent.txt` (B) `spec=RSAKeyGenParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=RSAKEYGENPARAMETERSPEC-CONSTR-00 ev=c1 obj=RSAKeyGenParameterSpec val='3' exp='65537' msg='the rsa public exponent is not the one the rule admits'`
- `RSAKeyGenParameterSpecSpec-keysize-and-exponent.txt` (B) `spec=RSAKeyGenParameterSpecSpec,ev=c1,type=InvalidKeySize,msg=v=1 code=RSAKEYGENPARAMETERSPEC-KEYSIZE-00 ev=c1 obj=RSAKeyGenParameterSpec val='512' exp='[1024, 2048, 4096]' msg='the rsa key size is not one the rule admits'`
