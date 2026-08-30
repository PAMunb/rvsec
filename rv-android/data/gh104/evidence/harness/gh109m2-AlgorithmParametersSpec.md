# AlgorithmParametersSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `AlgorithmParametersSpec-dh-alias-unobserved.txt` | introduced | — | init:ALGORITHMPARAMETERS-NOBS-01 |
| `AlgorithmParametersSpec-dh-alias.txt` | unchanged | — | — |
| `AlgorithmParametersSpec-unlisted.txt` | introduced | — | get:ALGORITHMPARAMETERS-ALG-00 |

## Lines no pointcut resolved

- `AlgorithmParametersSpec-dh-alias-unobserved.txt` (A) `AlgorithmParameters.getInstance("dh") -> ap`
- `AlgorithmParametersSpec-dh-alias-unobserved.txt` (A) `ap.init(params)`
- `AlgorithmParametersSpec-dh-alias.txt` (A) `AlgorithmParameters.getInstance("dh") -> ap`
- `AlgorithmParametersSpec-dh-alias.txt` (A) `new DHParameterSpec(bits(2048), bits(2048)) -> params`
- `AlgorithmParametersSpec-dh-alias.txt` (A) `ap.init(params)`
- `AlgorithmParametersSpec-unlisted.txt` (A) `AlgorithmParameters.getInstance("Blowfish") -> ap`

## Envelopes

- `AlgorithmParametersSpec-dh-alias-unobserved.txt` (B) `spec=AlgorithmParametersSpec,ev=init,type=UnsatisfiedConstraint,msg=v=1 code=ALGORITHMPARAMETERS-NOBS-01 ev=init obj=AlgorithmParameters val='dh' exp='preparedDH' msg='no preparation of the parameter spec was observed'`
- `AlgorithmParametersSpec-unlisted.txt` (B) `spec=AlgorithmParametersSpec,ev=get,type=UnsafeAlgorithm,msg=v=1 code=ALGORITHMPARAMETERS-ALG-00 ev=get obj=AlgorithmParameters val='Blowfish' exp='AES,DiffieHellman,DH,OAEP,PBEWithHmacSHA224AndAES_128,PBEWithHmacSHA256AndAES_128,PBEWithHmacSHA384AndAES_128,PBEWithHmacSHA512AndAES_128,PBEWithHmacSHA224AndAES_256,PBEWithHmacSHA256AndAES_256,PBEWithHmacSHA384AndAES_256,PBEWithHmacSHA512AndAES_256' msg='expecting one of AES,DiffieHellman,DH,OAEP,PBEWithHmacSHA224AndAES_128,PBEWithHmacSHA256AndAES_128,PBEWithHmacSHA384AndAES_128,PBEWithHmacSHA512AndAES_128,PBEWithHmacSHA224AndAES_256,PBEWithHmacSHA256AndAES_256,PBEWithHmacSHA384AndAES_256,PBEWithHmacSHA512AndAES_256 but found Blowfish'`
