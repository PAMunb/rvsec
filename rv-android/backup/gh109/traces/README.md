# Traces retiradas por gh109 task 7.3 (checkpoint 2)

As duas do `PKIXParametersSpec` não replicavam. `new PKIXParameters(ks)` sobre um PKCS12 vazio
lança `InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty`; o
`instantiate` do arnês devolve `null`, e o dispatcher gerado, que indexa o monitor pelo objeto,
levanta `NullPointerException` dentro da árvore de indexação. As duas mediam como limpas.

- `PKIXParametersSpec-unloaded-keystore.txt` é substituída por
  `PKIXParametersSpec-unobserved-truststore.txt`, que faz a mesma pergunta com o `truststore` da
  plataforma e de fato desenha `PKIXPARAMETERS-NOBS-00`.
- `PKIXParametersSpec.txt` pedia a metade conforme, que **não é exprimível**: precisa de um
  keystore que ao mesmo tempo tenha entrada confiável (ou o construtor lança) e tenha sido
  observado sendo carregado (ou `KeyStoreSpec` não escreve `generatedKeyStore`), e a notação não
  dá as duas coisas — uma linha sem binding nunca chega à plataforma, logo nunca carrega nada.
  A razão está registrada em `PKIXBuilderParametersSpec-unobserved-truststore.txt`.
