# Reanálise independente das acusações da estudo02 (`NOBS` e demais códigos)

Data: 15/09/2026. Campanha `experimento-estudo02`, conjunto `jca_android`, tecelão dexlib2, 163 APKs.
Substitui, para qualquer uso, a primeira passagem de 14/09 (`20260914_adjudicacao_nobs.md`), que
passa a valer só como registro das hipóteses daquele dia.

Anexos em `docs/adjudicacao_nobs/reanalise_20260915/`: `my_verdicts_all.csv` (veredito por sítio
`NOBS`), `nonnobs_keys.csv` (os maus usos sustentados por outro código), `full_partition_keys.csv`
(a partição final dos 27 068 maus usos), `readers/` (folha de specs e relatórios das leituras) e
`scripts/`. A varredura do gancho pulado (seção 7) é `experimento-estudo02/scripts/branch_target_hooks.py`;
o resultado está em `branch_target_hooks.csv` (um ponto por linha), `branch_target_hooks_totals.csv`
(denominador por APK) e `branch_target_hooks_covered_runs.csv`.

---

## 1. Resposta curta

- **Dos 27 068 maus usos por execução, 6 278 (23,2 %) são sustentados pelas regras** — em 50 dos 91
  APKs com alguma acusação. A primeira passagem dizia 7 872 (29,1 %) porque contou como sustentados,
  sem conferir, todos os maus usos que traziam um código diferente de `NOBS`.
- **Relevantes para segurança são 1 572 (5,8 %), em 14 APKs**: os `NOBS` que são mau uso real (trust
  manager que aceita tudo, chave ou IV fixos, salt fixo, semente fixa) mais as violações de valor que
  protegem algo de fato ou são discutíveis.
- **A maior massa (17 409, 64,3 %) é caminho correto que o monitor não consegue ver**, e quase todo
  mecanismo está previsto nos comentários dos próprios `.mop`. Dois métodos do okhttp respondem por
  43,5 % dela; oito métodos de biblioteca, por 73 %.
- **A fração sustentada é estreita entre ferramentas (0,220–0,253) e orçamentos (0,238 / 0,229 /
  0,230)**. Não há motivo para esperar inversão no ranking de ferramentas; só o reajuste do modelo
  com o desfecho restrito diz isso com número.
- **Tecelão**: o disparo duplo de `getInstance(String)` é comportamento registrado cujo efeito nas
  acusações não estava registrado (25,5 % das linhas; 654 maus usos são só isso); o `getEncoded()`
  com dono subtipo é lacuna real, não documentada, que decide 47 a 94 maus usos; e há um terceiro
  achado, novo e medido aqui: **o gancho `before` é pulado quando a chamada é alvo de desvio**, em
  424 dos 7 838 ganchos `before` inseridos no corpus (5,4 %), quase todos em bibliotecas. Nesta
  campanha ele fabrica 13 maus usos e esconde poucos relatos que se consigam enxergar.

## 2. Método

**Censo, não amostra, a partir das fontes primárias.** Refeito do zero sobre
`data/results/estudo02_consolidado/errors.csv`: 62 533 linhas `NOBS`, 515 pontos `(apk, classe,
método, spec, código)`, 181 sítios `(classe, método, spec, código)`, 99 métodos; 27 068 maus usos
por execução `(apk, ferramenta, rep, orçamento, classe, método, spec)`. Números idênticos aos da
primeira passagem.

**Leitura independente.** Seis leituras de sítios, uma da folha de specs (o que cada um dos 22
códigos `NOBS` lê, todo produtor, suas guardas, o grafo de cascata), uma do disparo duplo, uma do
`getEncoded` e uma dos 6 765 maus usos com código diferente de `NOBS`, que a primeira passagem não
tinha conferido. As leituras receberam os sítios sem os vereditos de 14/09. Tudo que decide volume
foi reconferido por mim na fonte: `.mop`, regra CrySL fixada (`rvsec-cognicrypt/CrySL-Rules/`),
código do app ou da biblioteca na versão embarcada, e bytecode do APK instrumentado.

**Categorias por sítio `NOBS`.**

| categoria | quando |
|---|---|
| mau uso real | o programa faz o que o requisito protege |
| caminho correto invisível | origem correta que o monitor não tem como ver (cópia, array novo, `null` = padrão do sistema, IV lido do texto cifrado, bytes de keyset) |
| decisão da regra | a regra CrySL acusa de propósito, e o `.mop` a transcreve fielmente |
| produtor ausente | origem correta e observável que o conjunto não credita |
| lacuna do tecelão | o produtor existe e não foi inserido no APK |
| artefato do tecelão | o `NOBS` só existe por causa do disparo duplo |

**Projeção por mau uso.** Um mau uso com algum código de valor (`ALG`, `KEYSIZE`, `CONSTR`,
`PROTO`, `FORB`) é classificado pelo código de valor; um só com `NOBS`, pela categoria mais grave dos
seus sítios; um só com `ORDER-00`, pelo mecanismo do `ORDER`. A violação de ordem do disparo duplo é
reconhecida por regra independente dos vereditos: `ORDER-00` de `TrustManagerFactorySpec`,
`KeyManagerFactorySpec` ou `SecureRandomSpec` cujo gatilho (`ORDER-00` no evento `g2`) aparece no
mesmo mau uso, em outro método da mesma execução e spec, ou no mesmo sítio em outras execuções.

## 3. O que a primeira passagem afirmou e o que ficou

| afirmação de 14/09 | situação | número certo |
|---|---|---|
| 27 068 maus usos, 181 sítios, 99 métodos | confirmada | — |
| 7 872 (29,1 %) sustentados | **corrigida** | 6 278 (23,2 %) pelas regras; 1 572 (5,8 %) relevantes |
| 6 765 sustentados por outro código | **corrigida** | 6 710 são desse lado; só 5 169 são violação genuína pela regra |
| 17 409 caminhos corretos invisíveis | confirmada | 17 409 |
| 1 107 maus usos reais (`NOBS`) | confirmada | 1 109 |
| 1 186 defeitos da cadeia (spec ou tecelão) | **corrigida** | 552 produtor ausente + 537 decisão da regra + 94 lacuna do `getEncoded` + 3 artefato |
| 601 só violação de ordem do disparo duplo | **corrigida** | 654 (o gatilho às vezes está em outro método) |
| disparo duplo é defeito do tecelão | **corrigida** (já em 14/09, seção 7) | comportamento registrado; o efeito nas acusações não estava |
| `getEncoded` com dono subtipo não tecido | confirmada, causa achada | 1 559 chamadas sem advice, 117 APKs; decide 47–94 maus usos |
| `KeyStore.getEntry` é lacuna de spec | **refutada** | a regra só credita `getKey`; é decisão da regra |
| bytes de `SecureRandom` como chave é lacuna | **refutada** | decisão registrada (`SecretKeySpecSpec.mop:79-91`) |
| `Cipher.init(int, Key)` do aegis foi tecido | **refutada em parte** | tecido, mas o gancho não roda no caminho que chega por desvio (seção 7) |
| a fração sustentada é igual entre ferramentas | confirmada | 0,220–0,253 |

## 4. Lado `NOBS`: o que decide cada mau uso

| status | maus usos |
|---|---:|
| caminho correto invisível | 17 409 |
| mau uso real | 1 109 |
| produtor ausente no conjunto | 552 |
| decisão da regra | 537 |
| lacuna do tecelão (`getEncoded`) | 94 |
| artefato do disparo duplo (ktor `Nonce`) | 3 |

**Onde estão os 17 409.** okhttp `Platform.platformTrustManager` 3 881 e `newSslSocketFactory` 3 688
(43,5 %); com tink `AesSiv.encryptDeterministically` 1 792, `AndroidKeystoreAesGcm.decryptInternal`
1 254, os dois métodos GCM do ktor (≈1 100), tink `PrfAesCmac.<init>` 546 e
`InsecureNonceAesGcmJce.<init>` 447, oito métodos fazem 73 %. Mecanismos, todos conferidos na fonte:

- `null` com sentido de padrão do sistema, lido como não observado por decisão registrada
  (`TrustManagerFactorySpec.mop:102-112`, `SSLContextSpec.mop:176-208`);
- array novo em volta do trust manager da fábrica (`arrayOf(trustManager)`, okhttp 4.12.0
  `Platform.kt:165-169`; previsto em `SSLContextSpec.mop:199-202`): o predicado foi gravado no array
  devolvido por `getTrustManagers()`, e o array passado ao `init` é outro;
- bytes de chave do tink copiados do protobuf do keyset;
- IV lido do texto cifrado ao decifrar;
- IV ou nonce derivado por construção (IV sintético do AES-SIV, nonce de registro TLS, nonce de
  segmento).

**Os maus usos reais (10 APKs, 1 109).**

| APK | método | o que faz | alcance | maus usos |
|---|---|---|---|---:|
| myexpenses (LVL embarcado) | `AESObfuscator.<init>` | salt literal, IV estático | sempre | 396 |
| redreader | `General.parseConfig` | chave = SHA-256 do certificado de assinatura + pacote, IV zero | sempre | 297 |
| passportreader (gms ads) | `zzbbe.zzb` | chave = 16 bytes de um Base64 literal com XOR 0x44 | ofuscação | 99 |
| dsub2000 | `RESTMusicService.<init>` | trust-all construído sempre | usado só com "allow insecure" por servidor (padrão desligado) | 99 |
| metadataremover | `MainViewModel.<clinit>` | `SecureRandom("75rgu86gr59ht86".bytes)` | sem efeito prático no Android ≥ 7 | 99 |
| feeder | `jsonfeed.trustAllCerts` | trust-all e qualquer hostname | **ligado por padrão** no cliente singleton (`FeederApplication.kt:117-123`) | 98 |
| mtgfam | `MarketPriceFetcher` | string de recurso como chave AES, IV = chave | sempre | 15 |
| treehouses, passnotes, matedroid | — | KDF caseiro 1000 × SHA-256 (4); trust-all em build DEBUG + opção, e o APK do corpus é DEBUG (1); trust-all atrás de opção do usuário (1) | — | 6 |

**Decisões da regra (537).** Duas famílias:
1. *Bytes aleatórios usados como chave* — feeder `AesCbcWithIntegrity.generateKey`, photok
   `KeyGen.generateVaultMasterKey`, freeotp `MasterKey.<init>`, tink `Hkdf.computeHkdf`: a regra exige
   material preparado, não aleatório; registrado em `SecretKeySpecSpec.mop:79-91`.
2. *Chave do AndroidKeyStore obtida por `getEntry(...).secretKey`* — tokn, deku (`lib_smsmms`),
   trafficlight, networksurvey (`CryptoManager.kt:39-40`). A regra fixada só garante
   `generatedKey[key, _]` sobre o retorno de `getKey` (`KeyStore.crysl:45,60`); `getEntry` não produz
   chave nenhuma na regra. A transcrição é fiel. Na primeira reanálise o networksurvey tinha ficado
   como produtor ausente e os outros três como decisão; foi harmonizado (5 maus usos).

**Produtor ausente (552).** ktor TLS: `ECPublicKeySpec` não produz chave especificada nem no
conjunto nem no oráculo, e a cascata desce para `KeyAgreement` e para o `SecretKeySpec` do segredo.

**Divergências de veredito com a primeira passagem, fora das acima.**
- photok `derivePasswordKeyEncryptionKey` e `PasswordVaultProtectionHandler.create`: lacuna do
  `getEncoded` (seção 6.3), não produtor ausente.
- ktor `NonceKt$nonceGeneratorJob$1` `SECURERANDOM-NOBS-00` (3): artefato do disparo duplo — o `@fail`
  do `SecureRandomSpec` descarta os arrays aguardando `RANDOMIZED`.
- treehouses `Encryptor.encrypt`: IV = bytes 16..31 do mesmo digest da senha que dá a chave, com salt
  aleatório. Classifiquei como mau uso (1 mau uso); fronteira.
- bitbanana `encodePbkdf2`: salt `"BitBanana" + nextInt()`. Classifiquei como correto invisível (a
  aleatoriedade passa por int/String); fronteira; os mesmos 2 maus usos continuam sustentados por
  5 000 iterações e PBKDF2-SHA1.

## 5. Lado não-`NOBS`: os 6 710 que a primeira passagem não conferiu

| status | maus usos | o que é |
|---|---:|---|
| genuíno pela regra, sem relevância de segurança | 4 706 | MD5/SHA-1 para nome de cache, impressão digital ou hash exigido por protocolo; AES/ECB como primitiva do CMAC; RSA 3072 na tabela estática do BouncyCastle; HMAC-SHA1 em HOTP/TOTP; rótulo `"RAW"`; `getDefault` de diagnóstico; GCM fora da lista de `AlgorithmParameters` |
| objeto criado sem evento de criação | 956 | `KeyPair` de `generateKeyPair()` 267 (decisão registrada, `KeyPairSpec.mop:154-188`); DRBG do spongycastle via `SecureRandom(Spi, Provider)` 495; `Digest` subclasse no kmp-tor 149; `clone` do guava 28; `AlgorithmParameters` de `Cipher.getParameters()` 17 |
| reuso legal recusado pela regra | 572 | novo `init` depois de `doFinal`: ciphers em ThreadLocal do tink, cipher estático do gms, PRF `P_hash` do TLS no ktor, HKDF do tink (registrado em `CipherSpec.mop:414-418`; igual em `Mac.crysl:41`, `Cipher.crysl:85`) |
| genuíno, discutível | 379 | LVL 1 024 iterações + algoritmo PBE; bitbanana 5 000 iterações + PBKDF2-SHA1; flyve RSA/OAEP-SHA1; DSub `md5(senha+salt)` do protocolo Subsonic |
| genuíno, relevante | 84 | Fossify padrão/PIN gravado como SHA-1 sem salt (9); nextcloudcookbook `SSLContext.getInstance("SSL")` no caminho trust-all (75) |
| gancho pulado por desvio | 13 | seção 7 |

Todo `ORDER-00` de `MessageDigest`, `Mac` ou `Cipher` que divide o sítio com um código de valor é
cascata dele (100 % de sobreposição): um `getInstance` recusado deixa o autômato num estado que não
admite o evento seguinte. Esses `ORDER-00` não contam como evidência independente.

## 6. Partição final e os dois achados do tecelão já conhecidos

### 6.1 Partição dos 27 068 maus usos

| grupo | maus usos | % |
|---|---:|---:|
| **sustentado pelas regras** (mau uso real `NOBS` + genuíno pela regra) | **6 278** | **23,2** |
| dos quais relevantes para segurança (mau uso real + genuíno relevante + discutível) | 1 572 | 5,8 |
| caminho correto invisível | 17 409 | 64,3 |
| objeto sem evento de criação | 956 | 3,5 |
| só violação de ordem do disparo duplo | 654 | 2,4 |
| reuso legal recusado pela regra | 572 | 2,1 |
| produtor ausente | 552 | 2,0 |
| decisão da regra (`NOBS`) | 537 | 2,0 |
| lacuna do `getEncoded` | 94 | 0,3 |
| gancho pulado por desvio / artefato `NOBS` do disparo duplo | 13 / 3 | 0,1 |

Fração sustentada por ferramenta: ape 0,221, ares 0,236, droidbot bfs_greedy 0,225, bfs_naive
0,241, dfs_greedy 0,220, dfs_naive 0,238, droidmate 0,233, fastbot 0,232, humanoid 0,242, monkey
0,221, qtesting 0,253. Por orçamento: 0,238 / 0,229 / 0,230 (60 / 180 / 300 s).

Composição das 139 916 linhas: `NOBS` 62 533 (44,7 %); violação de ordem do disparo duplo 35 694
(25,5 %); `ORDER-00` em cascata de falha de valor no mesmo mau uso 16 429 (11,7 %); o restante 25 260
(`ALG` 18 257, `ORDER` 5 561, `KEYSIZE` 1 095, `CONSTR` 245, `PROTO` 96, `FORB` 6). Uma linha é um
relato distinto por processo e sítio, não uma chamada: o `ErrorCollector` deduplica por
`(spec, erro, classe, método, local, código, evento)` (`rvsec-logger-logcat/.../ErrorCollector.java:26,51`).

### 6.2 Disparo duplo de `getInstance(String)`

Confirmado no bytecode da campanha (wrappers de `app.eduroam.geteduroam_2685` e
`app.plugbrain.android_154`): `TrustManagerFactory` `g1,g2`; `KeyManagerFactory` `g1,g3,g2`;
`SecureRandom` `g1,g2,g5,g4`. Causa: `args(alg, *)` sem tipo casa sempre
(`PointcutMatcher.java:268-271`) e o wrapper recebe todo advice, só contando a incompatibilidade de
aridade (`WrapperEmitter.java:301-313`). **Registrado** como invariante em
`openspec/specs/instrumentation/spec.md:351` (requisito em `:2530-2559`, que cita este disparo em
`:2534`); `advicesExcludedByArity` = 10 em 164 das 170 linhas por APK.

**Não registrado**: a consequência no autômato. `g2` chega a um estado que não o declara, sai
`ORDER-00` e o monitor reinicia; todo evento seguinte do objeto também dá `ORDER-00`. No
`SecureRandomSpec` o `@fail` descarta os arrays de `nextBytes`/`generateSeed` e o `RANDOMIZED` se
perde. Os comentários do `.mop` assumem a aridade do AspectJ (`SecureRandomSpec.mop:139-140,154-157`).
Efeito: 35 694 linhas (25,5 %) e 654 maus usos sem nada além disso. **A seção 4 do veredito
("quatro linhas por uso" = verbosidade do conjunto) está errada para essas três specs**: três das
quatro linhas são este artefato. O veredito comitado não foi alterado.

### 6.3 `getEncoded()` com dono subtipo do framework

Varredura completa, 163 de 163 APKs: com dono `java.security.Key`, 2 847 chamadas, todas desviadas
para `MonitorWrappers.java_security_Key_getEncoded`; com dono subtipo do framework, 1 559 chamadas e
**nenhuma** tecida (`PublicKey` 865, `SecretKey` 363, `PrivateKey` 237, `ECPublicKey` 38,
`SecretKeySpec` 23, `ECPrivateKey` 18, `PBEKey` 15), em 117 APKs; 90 sítios em código de app de 39
APKs.

Cadeia causal lida no código: advice `after` em chamada que não é construtor só existe por wrapper
(`DexWeaver.java:501-514`); `WrapperEmitter.expandCallTarget` (`:437-445`) consulta
`AndroidClassIndex.methods` (`:115-126`), que só devolve métodos declarados, e `SecretKey` não declara
`getEncoded` — nenhum wrapper, descarte silencioso em `WrapperEmitter.java:291`, sem contador; o
wrapper de `Key` é chaveado pelo dono exato (`DexWeaver.java:137-178,270-281`) e só ganha apelido
para subtipos do próprio APK (`InheritanceResolver.java:79-96`). O matcher casa
(`PointcutMatcher.java:322-347`). Nada disso está em `openspec/specs/instrumentation/spec.md`, que
só tem um cenário de matcher (`:1688-1692`), e nenhum teste cobre subtipo do framework que não
declara o método.

Direção: `PREPARED_KEY_MATERIAL` nunca é retirado, então a lacuna só pode criar `NOBS` falso, nunca
esconder um `VIOLATED`. Efeito pequeno porque o produtor só grava quando a origem da chave já foi
creditada (`KeySpec.mop:78-84`, `SecretKeySpec.mop:122-126`): no photok, o `create` (47 maus usos) é
decidido pela lacuna com certeza — salt novo de `SecureRandom`, `generateSecret` creditado, único elo
quebrado o `getEncoded` sem advice (`classes11.dex`, 0x0034) —; o `derive` (outros 47) também carrega
`PBEKEYSPEC-NOBS-01` do caminho de desbloqueio, com salt lido do armazenamento. **47 certos, no máximo
94.**

## 7. Achado novo: gancho `before` pulado quando a chamada é alvo de desvio

### 7.1 O mecanismo

O tecelão insere o advice `before` como instruções imediatamente antes da chamada casada
(`InstructionInjector.insertBefore`, `dex-mutator/.../InstructionInjector.java:80-87`, que chama
`insertAll` em `:457-463`, isto é, `MutableMethodImplementation.addInstruction(i, ins)`). No dexlib2
um rótulo pertence à posição da instrução original, e a instrução inserida antes dela ganha uma
posição nova; um desvio que tinha a chamada como alvo continua apontando para a chamada e passa por
cima do gancho. O próprio injetor depende desse comportamento para a guarda de `if(...)`: o rótulo de
salto é criado sobre a posição da instrução seguinte ao bloco, e a documentação diz que ele acompanha
a instrução quando algo é inserido antes (`InstructionInjector.java:167-180`). Para o `before`, esse
mesmo comportamento tira o gancho do caminho do desvio.

Conferido no bytecode do APK da campanha, `com.beemdevelopment.aegis_81.apk`,
`CryptoUtils.createCipher`:

```
000b: if-eqz v5, 0024                        // nonce == null → vai direto para o init
...
001a: invoke-static CipherSpec_i2Event       // gancho do ramo com nonce
001d: invoke-virtual Cipher.init(I, Key, AlgorithmParameterSpec)
0020: goto 0027
0021: invoke-static CipherSpec_i2Event       // só roda por queda, nunca é alcançado
0024: invoke-virtual Cipher.init(I, Key)     // alvo do desvio
```

Não é decisão registrada: nada em `openspec/specs/instrumentation/spec.md` (a única menção a rótulos
é a preservação na cópia do `RegisterShifter`, `:1362-1366`), no `architecture.md` e no `CLAUDE.md`
do tecelão, nem em `docs/20260827_achados_instrumentador_dexlib2.md`; `InstructionInjectorTest` não
tem caso com desvio. A primeira passagem olhou este mesmo método e concluiu que o `init` "foi tecido"
(`20260914_adjudicacao_nobs.md`, seção 3): foi, mas só num dos dois caminhos.

O mesmo mecanismo explica o `__LOC` de eventos `before` que cita a linha da instrução anterior: a
tabela de linhas também fica presa à posição original, e a instrução inserida herda a entrada
anterior (no dump acima, `0x0021` fica sob `0x0020 line=68`, e a chamada em `0x0024` é a linha 69).

### 7.2 Tamanho no corpus

Varredura de todos os 163 APKs instrumentados (`scripts/branch_target_hooks.py`: `dexdump` por dex,
fora do pacote `mop/`; conta cada sequência de eventos `before` do monitor imediatamente seguida da
chamada casada cujo endereço é alvo de `if-*`, `goto*` ou `switch` no mesmo método; nenhum advice
`before` do conjunto tem guarda `if(...)`, então não há salto legítimo para descontar):

| medida | valor |
|---|---:|
| ganchos `before` inseridos em linha | 7 838 |
| ganchos com a chamada como alvo de desvio | **424 (5,4 %)** |
| APKs com pelo menos um | 39 de 163 |
| sítios distintos (classe, método, chamada) | 94 |
| em código do próprio app (prefixo do pacote) | 7 pontos, 5 APKs |
| em bibliotecas embarcadas | 417 pontos; BouncyCastle 330 em 14 APKs, conscrypt 20, Apache POI/XML Security 13, netty 11, jsch 9 |

Por evento: `SecureRandom.nextBytes` 170, `Signature.initSign(PrivateKey)` 74, `Cipher.init` 68
(40 com o evento de junção de IV junto), `KeyGenerator.init(int, SecureRandom)` 26,
`Signature.initVerify` 26, `KeyManagerFactory.init` 20, `Signature.update` 16, `KeyStore.load` 10,
`SecureRandom.nextInt` 7, `TrustManagerFactory.init` 4, outros 3 (`Signature.initSign(PrivateKey, SecureRandom)` 2, `Mac.init` 1). Os 170 de `nextBytes` são quase
todos os `random` dos campos de curva do BouncyCastle (`SecP256R1Field.random` e irmãos): laço
`do { nextBytes } while`, em que o desvio de volta pula o gancho a partir da segunda volta.

### 7.3 Efeito nesta campanha

Direção: o corpo do evento que não roda não lê origem de chave, algoritmo nem tamanho, então **os
relatos daquele ponto se perdem** (falso negativo); e o autômato do objeto fica sem o evento, então
**os eventos seguintes dão `ORDER-00`** (falso positivo).

- **Falsos positivos medidos: 13 maus usos** (0,05 % dos 27 068): aegis `CryptoUtils.encrypt`
  `CIPHER-ORDER-00` em `doFinal` (6), etesync conscrypt `OpenSSLX509Certificate.verifyInternal`
  `SIGNATURE-ORDER-00` (5), droid_scep BouncyCastle `JcaContentSignerBuilder` (2).
- **Falsos negativos visíveis**: a cobertura da campanha (`coverage.csv`) só registra métodos do
  app. Dos 7 pontos em código de app, só o do aegis executou: em 6 execuções de 300 s (droidbot e
  humanoid). Ali o caminho sem nonce perdeu o `CIPHER-NOBS-00` do `init` (a chave não tem produtor);
  em 4 dessas 6 execuções o mau uso `(createCipher, CipherSpec)` some por inteiro, nas outras 2 ele
  aparece pelo caminho com nonce. Os 417 pontos de biblioteca não têm como ser medidos com os dados
  da campanha.

É um defeito do tecelão, sem registro, de alcance moderado no corpus (1 em cada 19 ganchos `before`)
e de efeito desprezível nas acusações desta campanha.

## 8. Outros achados, de menor peso

Conferidos:
- **`getEntry` e `setEntry` do `KeyStoreSpec` nunca são tecidos.** O `TypeResolver` resolve o nome
  importado `KeyStore.ProtectionParameter` como pacote, `Ljava/security/KeyStore/ProtectionParameter;`,
  em vez de `KeyStore$ProtectionParameter` (`TypeResolver.java:87-103`, `resolveFqn` `:110-117`); no
  networksurvey a chamada `KeyStore.getEntry` não tem evento antes dela. São os dois únicos pointcuts
  do conjunto que nomeiam tipo aninhado (`KeyStoreSpec.mop:7-8,107,111`). Efeito nesta campanha:
  nenhum — não há código `KEYSTORE-*` em `errors.csv`, e o `ere` aceita `gk1` sem `ge1`
  (`KeyStoreSpec.mop:124`). Um `store` depois de `setEntry` daria `ORDER-00`.
- **Linhas perdidas no logcat**: códigos emitidos incondicionalmente pelo mesmo corpo de evento
  diferem em ±1–2 por sítio (okhttp `platformTrustManager` 7 910 `g2` contra 7 908 `gtm1`; em 3
  execuções a linha `g2` sumiu). É perda de registro, não do monitor.

Relatados pelas leituras e não reconferidos um a um:
- `SSLCONTEXT-NOBS-01` não separa trust manager que aceita tudo de trust manager próprio que delega
  ao sistema; o alvo principal da regra cai sob o código de limite de alcance.
- O cliente TLS do ktor 1.6.0 (beatgame, retrowars) não verifica hostname; o pareamento do paperwork
  usa `addInsecureHost` do okhttp-tls. Nenhuma spec mede isso.
- `KeyAgreementSpec.conforms` não se recupera depois de uma leitura acusadora; toda ECDH com par
  remoto desce em cascata para `SecretKeySpec`/`Cipher` `NOBS`. Um `CONSTR` de tamanho de tag ou um
  `ALG` vira `NOBS` adiante (e aí o `NOBS` não é limite de alcance).
- Oráculo: a lista de tamanhos RSA admite 1 024 e recusa 3 072; RSA/ECB admite OAEP-MD5 e recusa
  OAEP-SHA1; a lista de `AlgorithmParameters` não tem "GCM"; HMAC-SHA1 recusado apesar de exigido
  pelas RFC 4226/6238.
- `OpenSSLRandom.engineSetSeed(byte[])` do Conscrypt não faz nada; toda leitura de
  `randomized[seed]` em `setSeed`/`SecureRandom(byte[])` mede uma chamada sem efeito no Android.

## 9. O que não está verificado

- A classificação por mau uso dos 956 "objeto sem evento de criação" e dos 572 "reuso legal" foi
  feita por spec e classe (`scripts/nonnobs_project.py`); os sítios foram lidos, mas não reconferi
  cada um dos 6 710.
- A divisão exata do photok entre `create` e `derive` (47 certos, até 94).
- Os falsos negativos do gancho pulado em código de biblioteca: a cobertura não registra métodos de
  biblioteca.
- A separação entre código de app e biblioteca da seção 7 usa o prefixo do nome do pacote do APK;
  bibliotecas do mesmo autor com outro prefixo (deku `libsignal_doubleratchet`) caem em biblioteca.
- O modelo estatístico não foi reajustado com o desfecho restrito.
