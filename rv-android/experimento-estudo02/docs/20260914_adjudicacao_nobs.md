# Adjudicação das acusações `NOBS` da estudo02 e os defeitos que ela expôs

> **Superada por `20260915_reanalise_acusacoes.md`** (reanálise independente de 15/09, que confere
> também os códigos que não são `NOBS`). Os números e classificações abaixo não devem ser usados.

Data: 14/09/2026. Campanha `experimento-estudo02`, conjunto `jca_android` (47 `.mop`, commit
`a599be6b`, byte-idênticos ao que está hoje em `rvsec-mop/src/main/resources/jca_android/`),
tecelão dexlib2, 163 APKs, 16 137 identidades.

Anexos, em `docs/adjudicacao_nobs/`: `vereditos.csv` (os 181 sítios, com evidência
`arquivo:linha`, versão da biblioteca e confiança), `metodos.csv` (os 99 métodos), `dossie_G1.md` a
`dossie_G7.md` (a leitura sítio a sítio), `specs_codigos.md` (o que cada um dos 22 códigos lê, quem
produz o predicado e as arestas de cascata). Projeção reproduzível:
`uv run python experimento-estudo02/scripts/adjudicacao_nobs.py`.

---

## 1. Resposta curta

- **Dos 27 068 maus usos por execução da campanha, 7 872 (29,1 %) têm sustentação**: 6 765 por um
  código que não é `NOBS` (não adjudicados aqui) e 1 107 por um `NOBS` que aponta mau uso real.
  **Os outros 19 196 (70,9 %) não apontam mau uso**: 17 409 são caminhos corretos que o monitor não
  consegue ver, 1 186 são defeitos da cadeia de monitoramento (spec ou tecelão) e 601 são só
  violações de ordem fabricadas pelo tecelão.
- **Dois defeitos do tecelão dexlib2**, confirmados no bytecode dos APKs da campanha:
  (a) `getInstance(String)` dispara os eventos `g1` e `g2` ao mesmo tempo, o que fabrica 35 631
  linhas `ORDER-00` em `TrustManagerFactorySpec`, `KeyManagerFactorySpec` e `SecureRandomSpec`;
  (b) nenhuma chamada `getEncoded()` com dono `SecretKey`, `PublicKey` ou `PrivateKey` foi tecida
  (385 + 1 170 chamadas no corpus), então a ponte `preparedKeyMaterial` só existe quando o dono
  declarado é exatamente `java.security.Key`.
- **Três lacunas de spec** geram acusações falsas: `KeyStore.getEntry(...).getSecretKey()` não
  credita a chave, `ECPublicKeySpec` não tem produtor, e bytes de `SecureRandom` não contam como
  material de chave (decisão registrada, igual à regra CrySL).
- **24 sítios são mau uso real** em 13 métodos de 12 APKs: 5 trust managers que aceitam qualquer
  certificado, chaves e IVs fixos (mtgfam, redreader, LVL do myexpenses, gms ads), salt fixo, semente
  fixa, KDF fraco.
- **A fração sustentada é a mesma em todas as ferramentas (28,2 %–30,3 %) e orçamentos
  (28,9 %–29,2 %)**. A comparação entre ferramentas não deve mudar de sinal; o que muda é o volume e
  o número de zeros (36 dos 91 APKs com acusação ficam sem nenhuma sustentada), e o modelo precisa
  ser reajustado para dizer isso com número.

## 2. O que é um `NOBS` e por que ele não é, sozinho, uma acusação

Uma spec do `jca_android` lê um `REQUIRES` da regra CrySL com
`PredicateStore.instance().validate(Property.X, objeto, ...)`
(`rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java:342-362`). A resposta tem três
valores. `NOT_OBSERVED` — e o código `…-NOBS-nn` — sai quando o objeto é `null` (`:343-345`) ou
quando nenhum `ensure` foi gravado para **aquele objeto**, por identidade (`System.identityHashCode`,
`:162-213`). Uma cópia do array, um array novo em volta do mesmo elemento, bytes lidos do disco ou um
objeto nascido dentro do framework chegam sem predicado, por mais correta que seja a origem.

O próprio `.mop` diz isso (`IvParameterSpec.mop:46-51`): `NOT_OBSERVED` "no Android é tão
frequentemente um limite de alcance da instrumentação quanto um mau uso". O veredito da campanha
registrou que 15 032 dos 27 068 maus usos por execução (55,5 %) só tinham `NOBS` e deixou a
adjudicação para depois. Este documento é essa adjudicação.

## 3. Método

**Censo, não amostra.** As 62 533 linhas `NOBS` caem em 515 pontos `(apk, classe, método, spec,
código)` e em **181 sítios** `(classe, método, spec, código)`, que são **99 métodos**. As bibliotecas
se repetem entre APKs (`okhttp3.internal.platform.Platform.platformTrustManager` está em 54 APKs), então
ler 99 métodos cobre tudo.

**Três oráculos por sítio.** Para cada sítio: (1) o `.mop` — qual evento emite o código, qual
propriedade lê, sobre qual objeto; (2) quem produz a propriedade e sob que guarda (a folha
`specs_codigos.md`), conferida contra a semântica do monitor gerado (corpo do evento antes da
transição, `@match`/`@fail` depois); (3) o código no ponto da chamada — fonte do app em
`rvsec-dataset/repos/<apk>/`, fonte da biblioteca na versão embarcada (baixada do Maven Central e
confirmada pela linha `__LOC` gravada em `errors.csv`), ou bytecode do APK quando não havia fonte
(gms ads, deku, flyve, droid_scep, passportreader; marcado em `vereditos.csv`).

**Quatro categorias.**

| categoria | quando |
|---|---|
| `MISUSE` | o programa faz o que o requisito protege: chave, IV, salt ou semente fixos ou derivados de dado público; trust manager que aceita tudo |
| `LEGIT_UNOBSERVABLE` | a origem é correta e o monitor não tem como vê-la: IV lido do texto cifrado, chave vinda de keyset ou de armazenamento, `null` que significa "padrão do sistema", objeto do framework, identidade perdida numa cópia, IV derivado por construção do protocolo |
| `SPEC_DEFECT` | a origem é correta **e observável** (uma chamada de API em código tecido a produz), mas a cadeia de monitoramento não a credita: produtor ausente no conjunto, advice não tecido, produtor desfeito pelo tecelão |
| `UNDETERMINED` | não foi possível estabelecer a origem (nenhum sítio ficou nesta categoria) |

Cascata não é categoria: um `CIPHER-NOBS-00` que só existe porque o `SecretKeySpec` anterior não
foi creditado herda a categoria da raiz, registrada na coluna `root`.

**Leitura em paralelo, conferência central.** Oito leituras independentes (uma da folha de specs,
sete de sítios) escreveram dossiês; os vereditos que decidem volume foram reconferidos na fonte por
mim: o `arrayOf(trustManager)` do okhttp 4.12.0 (`Platform.kt:165-169`) contra
`SSLContextSpec.mop:231` e `TrustManagerFactorySpec.mop:218`; o IV lido do texto cifrado em
`AndroidKeystoreAesGcm.java:113-116` (tink-android 1.8.0); o `ge1` vazio em `KeyStoreSpec.mop:106-108`;
os dois defeitos do tecelão no bytecode (seção 5). Uma suspeita de um dossiê caiu na conferência:
o `Cipher.init(int, Key)` do aegis **foi** tecido (`CipherSpec_i2Event` antes do `invoke-virtual`
em `CryptoUtils.createCipher`), e por isso não aparece abaixo.

**Harmonização.** Duas leituras classificaram o mesmo fenômeno de formas diferentes e foram
alinhadas numa regra única: IV ou nonce derivado por construção do protocolo — o IV sintético do
AES-SIV (RFC 5297), o nonce de registro do TLS no ktor (RFC 5288), o nonce de segmento do
`AesGcmHkdfStreaming` do tink, e o IV do treehouses derivado do mesmo digest com salt aleatório novo a
cada cifragem — é `LEGIT_UNOBSERVABLE` (`derived_iv_by_construction`), porque nenhuma chamada de API
produz esse valor para o monitor creditar. As quatro mudanças estão anotadas na coluna `notes`.

## 4. Resultado do censo

### 4.1 Sítios, pontos e linhas

| categoria | sítios | pontos | linhas |
|---|---:|---:|---:|
| `LEGIT_UNOBSERVABLE` | 139 | 464 | 56 810 |
| `MISUSE` | 24 | 24 | 3 591 |
| `SPEC_DEFECT` | 18 | 27 | 2 132 |
| **total** | **181** | **515** | **62 533** |

### 4.2 Maus usos por execução, pelo que os sustenta

A chave é a do artigo, `(apk, ferramenta, rep, orçamento, classe, método, spec)`. Um mau uso é
"decidido por `NOBS`" quando nenhum dos seus códigos é outra coisa além de `NOBS` e da violação de
ordem fabricada pelo duplo casamento (5.1). Com vários `NOBS` na mesma chave, vale a categoria mais
grave.

| status | maus usos por execução | % |
|---|---:|---:|
| sustentado por outro código (não adjudicado aqui) | 6 765 | 25,0 |
| decidido por `NOBS`: `MISUSE` | 1 107 | 4,1 |
| decidido por `NOBS`: `SPEC_DEFECT` | 1 186 | 4,4 |
| decidido por `NOBS`: `LEGIT_UNOBSERVABLE` | 17 409 | 64,3 |
| só `ORDER` do duplo casamento | 601 | 2,2 |
| **total** | **27 068** | 100 |

O número é maior que os 15 032 "só `NOBS`" do veredito porque 4 670 maus usos que tinham `NOBS` mais
um `ORDER-00` do `TrustManagerFactorySpec`/`KeyManagerFactorySpec` passam a ser decididos pelo
`NOBS` depois que o `ORDER-00` se revela artefato.

**Confiança** dos 19 702 decididos por `NOBS`: alta 18 677 (94,8 %), média 1 023, baixa 2.

**Por biblioteca** (decididos por `NOBS`):

| origem | `LEGIT_UNOBSERVABLE` | `MISUSE` | `SPEC_DEFECT` | total |
|---|---:|---:|---:|---:|
| okhttp | 8 161 | 0 | 0 | 8 161 |
| tink | 5 500 | 0 | 34 | 5 534 |
| ktor | 1 835 | 0 | 555 | 2 390 |
| apps e outras bibliotecas | 1 913 | 1 107 | 597 | 3 617 |

**Por ferramenta**, a fração sustentada (outro código ou `MISUSE`) vai de 0,282 (`monkey`) a 0,303
(`qtesting`); por orçamento, 0,292 / 0,289 / 0,292 em 60 / 180 / 300 s.

### 4.3 Onde estão os caminhos corretos que o monitor não vê

| mecanismo | o que acontece | onde pesa |
|---|---|---|
| `null` com significado de padrão | `SSLContext.init(null, tms, null)` (sem certificado cliente, gerador padrão), `TrustManagerFactory.init((KeyStore) null)` (loja de CAs do sistema); o `.mop` lê `null` como `NOT_OBSERVED` por decisão (`SSLContextSpec.mop:176-208`) | okhttp em 52–54 APKs, conscrypt, apps |
| identidade perdida em array novo | `init(null, arrayOf(tm), null)`: o predicado foi gravado no array devolvido por `getTrustManagers()`, o elemento é o mesmo, o array não | okhttp em todas as versões 3.14.9–5.4.0 |
| chave vinda de keyset ou armazenamento | tink lê o keyset de SharedPreferences, decifra com a master key do Android Keystore e copia os bytes (`toByteArray`, `copyOfRange`) | EncryptedSharedPreferences em 9 APKs |
| IV lido do texto cifrado | toda decifração GCM/CBC gera `GCMPARAMETERSPEC-NOBS` e, em cascata, `IVCHAINJUNCTION-NOBS-01`; inclui o autoteste do tink, que cifra e decifra 10 bytes a cada carga da master key | tink, apps |
| derivado por construção | IV do SIV, nonce TLS, nonce de segmento, PRF do TLS | tink, ktor |
| cascata | a leitura seguinte na cadeia herda a raiz | todas |

### 4.4 Os 24 sítios de mau uso real

| APK | método | o que faz | alcance |
|---|---|---|---|
| feeder (`com.nononsenseapps.feeder`) | `jsonfeed.OkHttpBuilderExtensionsKt.trustAllCerts` | trust manager vazio e hostname verifier que devolve `true` | **padrão**: o cliente HTTP singleton do app usa (`FeederApplication.kt:117-123`) |
| dsub2000 | `RESTMusicService.<init>` | `SSLContext` trust-all criado em todo construtor | instalado só com "allow insecure" por servidor |
| passnotes | `webdav.HttpClientFactory.createHttpClient` | trust-all | build DEBUG e opção "ignorar SSL" |
| matedroid | `TeslamateApiFactory.configureInsecureTls` | trust-all | opção "aceitar certificados inválidos" |
| nextcloudcookbook | `OkHttpClientProvider.configureTrustAllCertificates` | trust-all e qualquer hostname | opção "permitir autoassinados" |
| mtgfam | `MarketPriceFetcher$1.fetch`, `.decrypt` | chave AES = string de recurso `"lastLegalityUpda"`, IV = a própria chave; decifra credenciais de API embutidas | sempre |
| redreader | `General.parseConfig` | chave = SHA-256 de dados públicos (certificado de assinatura + pacote), IV de zeros | sempre (ofuscação de configuração) |
| myexpenses (LVL vendorizado) | `AESObfuscator.<init>` | salt de 20 bytes literais, senha = pacote + ANDROID_ID, IV `static final` | sempre |
| passportreader (gms ads 25.3.0 embarcado) | `com.google.android.gms.internal.ads.zzbbe.zzb` | chave AES-128 fatiada de um Base64 literal com XOR 68; decifra um `.jar` embutido | ofuscação de código (bytecode) |
| metadataremover | `MainViewModel.<clinit>` | `new SecureRandom("75rgu86gr59ht86".getBytes())` | latente: o Conscrypt não troca a entropia pela semente |
| treehouses | `ssh.Encryptor.encrypt` | KDF caseiro, 1000 × SHA-256 (herdado do ConnectBot) | ao cifrar chave SSH |
| bitbanana | `UtilFunctions.encodePbkdf2` | salt = `"BitBanana"` + `nextInt()` (32 bits), `"BitBanana"` puro se a leitura falhar | **fronteira** (confiança média) |

Contando só os decididos por `NOBS`, esses sítios somam 1 107 maus usos por execução, dos quais 396
do `AESObfuscator` e 297 do redreader.

## 5. Defeitos da cadeia de monitoramento

### 5.1 Tecelão: `getInstance(String)` dispara `g1` e `g2`

`TrustManagerFactorySpec.mop:82-91`, `KeyManagerFactorySpec.mop:50-59` e `SecureRandomSpec.mop:113-127`
têm dois eventos para a mesma fábrica: `g1` sobre `getInstance(String)` e `g2` sobre
`getInstance(String, ..) && args(alg, *)`. Em AspectJ o `args(alg, *)` exige dois argumentos e `g2`
não casa com a sobrecarga de um. No dexlib2 um `args(...)` sem tipo concreto é inerte
(`PointcutMatcher.java:269-270`, "an always-match collector"), e o `(String, ..)` do `call` aceita
zero argumentos a mais (`:361-366`). **Os dois eventos são emitidos**, confirmado no wrapper do APK
da campanha (`app.eduroam.geteduroam_2685.apk`):

```
mop.MonitorWrappers.javax_net_ssl_TrustManagerFactory_getInstance:(Ljava/lang/String;)
  invoke-static  TrustManagerFactory.getInstance(String)
  invoke-static  MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g1Event
  invoke-static  MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g2Event
```

O autômato aceita `g1`, recebe `g2`, falha e reinicia; o `init` e o `getTrustManagers` seguintes
falham também. Por isso `TrustManagerFactorySpec` tem 9 593 / 9 592 / 9 591 linhas `ORDER-00` em `g2`
/ `init` / `gtm1`, praticamente iguais.

| spec | linhas `ORDER-00` atribuídas | maus usos com o artefato | só com o artefato |
|---|---:|---:|---:|
| `TrustManagerFactorySpec` | 28 715 | 4 745 | 203 |
| `KeyManagerFactorySpec` | 2 734 | 323 | 198 |
| `SecureRandomSpec` | 4 182 | 203 | 200 |

No `SecureRandomSpec` o dano não para no `ORDER`: o `@fail` descarta os arrays aguardando
`RANDOMIZED`, e o ktor 1.6.0 (`Nonce.kt:106`, `SecureRandom.getInstance("SHA1PRNG")`) ganha um
`SECURERANDOM-NOBS-00` falso. A atribuição do `SecureRandomSpec` conta todo `ORDER-00` das chaves que
têm `ORDER-00` em `g2`, inclusive os eventos seguintes do mesmo objeto; 200 das 203 chaves só têm
`ORDER-00`.

**Consequência para o veredito**: a frase "`TrustManagerFactorySpec` emite quatro linhas por uso" e a
leitura de que o salto de eventos mede verbosidade do conjunto (veredito, seção 4) estão erradas para
essas três specs: a maior parte das linhas é artefato do tecelão. O mesmo par `g1`/`g2` existe no
`jca` e o APK instrumentado do artigo emite o mesmo duplo casamento; como o `jca` saiu de uso, isso só
importa onde o veredito compara as duas campanhas.

### 5.2 Tecelão: `getEncoded()` com dono subtipo não é tecido

`KeySpec.mop:76` (`call(public byte[] Key+.getEncoded())`) e `SecretKeySpec.mop:120`
(`call(public byte[] SecretKey+.getEncoded())`) são os dois únicos pointcuts do conjunto com `+` no
dono, e são os que gravam `PREPARED_KEY_MATERIAL` — a ponte que o próprio `CipherSpec.mop` indica como
o caminho conforme do PBE (`getEncoded()` → `new SecretKeySpec(bytes, "AES")`). Varredura de todas as
chamadas `getEncoded()[B` fora do pacote `mop/` nos 163 APKs da campanha (`dexdump`):

| dono declarado na chamada | chamadas | tecidas |
|---|---:|---:|
| `java.security.Key` | 2 847 | 2 847 (via `MonitorWrappers.java_security_Key_getEncoded`) |
| `javax.crypto.SecretKey` | 363 | **0** |
| `javax.crypto.spec.SecretKeySpec` | 22 | **0** |
| `java.security.PublicKey` | 862 | **0** |
| `java.security.PrivateKey` | 237 | **0** |
| `ECPublicKey`, `ECPrivateKey`, `PBEKey` | 71 | **0** |

O comentário de `SecretKeySpec.mop:103-118` afirma que o `T+` no dono foi medido e funciona; nos
APKs da campanha ele não funcionou em nenhum caso, e o `Key+` só casou o dono exato. **A causa não
foi diagnosticada** (descritor, resolução de tipo ou matcher). No censo, o efeito direto é pequeno —
photok, 94 maus usos decididos, com o `KeyGen.derivePasswordKeyEncryptionKey` confirmado no bytecode
(`invoke-interface SecretKey.getEncoded` sem evento depois) —, mas o predicado inteiro fica sem
produtor em código Kotlin/Java comum, e cada `SecretKeySpec` construído a partir de uma chave
derivada vira `NOBS`.

### 5.3 Spec: produtores ausentes

| lacuna | onde (`.mop`) | sítios | maus usos decididos |
|---|---|---:|---:|
| `KeyStore.getEntry(alias, null)` → `SecretKeyEntry.getSecretKey()`: o `ge1` tem corpo vazio; só `gk1`/`getKey` grava `GENERATED_KEY` | `KeyStoreSpec.mop:106-108`, `:114-122` | 7 (deku, networksurvey, trafficlight, tokn) | 340 |
| `ECPublicKeySpec` não produz `SPECCED_KEY` (só `X509EncodedKeySpec`, `SecretKeySpec`, `PBEKeySpec`); cascata em `KeyAgreement` e no `SecretKeySpec` do segredo | `KeyFactorySpec.mop:101-119`, `KeyAgreementSpec.mop:294-299` | 3 (ktor TLS) | 552 |
| HKDF: salt e PRK não contam como material de chave | `SecretKeySpecSpec.mop:79-91` | 2 (tink `Hkdf`) | 34 |

A folha de specs lista outras chamadas observáveis sem produtor que não apareceram no censo:
`Certificate.getPublicKey()`, `Cipher.getIV()`/`getParameters()`/`unwrap`, `RSAPublicKeySpec`,
`PKCS8EncodedKeySpec`, `DESedeKeySpec`.

### 5.4 Spec: decisão registrada que acusa uso correto

Bytes de `SecureRandom.nextBytes` usados como chave (`new SecretKeySpec(random32, "HmacSHA256")`) são
`RANDOMIZED`, não `PREPARED_KEY_MATERIAL`, e o `SecretKeySpecSpec` recusa. É leitura fiel da regra
CrySL e está registrada em `SecretKeySpecSpec.mop:77-95`. Acusa feeder `AesCbcWithIntegrity.generateKey`,
photok `KeyGen.generateVaultMasterKey` e freeotp `MasterKey.<init>`: 3 sítios, 163 maus usos.

### 5.5 Outros achados da leitura

Verificados:
- `SecureRandomSpec.mop:290`: `nextBytes` casa só com dono exato `SecureRandom`; `Random r = new
  SecureRandom(); r.nextBytes(b)` não grava `RANDOMIZED`.
- `KeyAgreementSpec.mop:381-386`: o `@fail` volta `conforms = true`; um `KeyAgreement` criado fora do
  código tecido tem o segredo marcado como preparado mesmo com leituras `NOBS` (falso negativo).

Relatados pelos dossiês e não reconferidos:
- `SecretKeyFactory` com `get` não observado grava `GENERATED_KEY` com algoritmo `null`, e o
  `CipherSpec` responde `VIOLATED` em vez de `NOBS` (`specs_codigos.md`).
- `__LOC` do evento `init` do `TrustManagerFactory` sai na linha do `getInstance` em alguns apps
  (`CertUtils.kt:22`, `MemorizingTrustManager.java:310/282`).
- Fraquezas de segurança fora do que o monitor cobra: o cliente TLS do ktor 1.6.0 (beatgame,
  retrowars) não verifica hostname (não há `verifyHostnameInCertificate` no 1.6.0, há no 3.x); o
  droid_scep aceita qualquer CA com fingerprint vazio (`OptimisticCertificateVerifier.verify` devolve
  `true`) e usa MD5 no outro caso; o pareamento do paperwork (`PairingRunner.kt:139-152`) aceita
  qualquer certificado do host antes de conferir o fingerprint.
- O `SSLCONTEXT-NOBS-01` não separa trust manager que aceita tudo de trust manager próprio que valida:
  os 5 `MISUSE` e os 5 que delegam ao sistema (etesync, ownCloud, openCloud, openHAB, MTM) têm a mesma
  forma na chamada.

## 6. O que fazer com estes resultados

### 6.1 Usar os dados da estudo02 sem rodar de novo

Nada do que foi encontrado exige reexecução para ser medido: toda linha de `errors.csv` tem
`spec`, `code`, `event` e o sítio, e o censo cobre todos os `NOBS`. O caminho é reanálise:

1. **Desfecho sustentado.** Recontar `mop_unique4` por execução só com as chaves "sustentadas por
   outro código" ou "decididas por `NOBS` como `MISUSE`" (7 872) e reajustar o modelo NB2 como
   sensibilidade (s7), ao lado do desfecho original. A fração sustentada é igual entre ferramentas,
   então a expectativa é que os IRRs entre ferramentas fiquem parecidos; o que o reajuste precisa
   mostrar é o efeito dos zeros (36 dos 91 APKs com acusação ficam sem nenhuma sustentada) e do
   orçamento.
2. **Declarar no dossiê**: o desfecho de eventos (`mop_total`) de `TrustManagerFactorySpec`,
   `KeyManagerFactorySpec` e `SecureRandomSpec` está inflado pelo duplo casamento; o desfecho de
   maus usos únicos tem 70,9 % de acusações sem sustentação; os 6 765 sustentados por outro código
   não foram adjudicados.
3. **Corrigir o veredito** onde ele atribui o salto de eventos à verbosidade (5.1) e onde diz que os
   `NOBS` não foram adjudicados.

**Nível de confiança da reanálise.** A classificação dos `NOBS` é de confiança alta em 94,8 % dos
maus usos que ela decide, e as massas maiores (okhttp e tink, 13 695 maus usos) foram reconferidas na
fonte. O duplo casamento e o `getEncoded` não tecido estão confirmados no bytecode da campanha. O que
não tem confiança nenhuma ainda é a parte **não adjudicada**: 6 765 maus usos sustentados por códigos
`ALG`, `CONSTR`, `ORDER` de outras specs — se houver artefatos parecidos lá, a fração sustentada cai.

### 6.2 Corrigir para o próximo experimento

| # | correção | onde | efeito medido nesta campanha | observação |
|---|---|---|---|---|
| C1 | `args(...)` sem tipo deve impor a aridade, como no AspectJ | `rvsec-instrumentation-dexlib2`, `PointcutMatcher.matchArgs` | 35 631 linhas `ORDER-00`; 5 271 maus usos contaminados, 601 inteiramente fabricados; `RANDOMIZED` perdido em `SecureRandom.getInstance(String)` | vale para todos os conjuntos; alternativa só no `.mop`: trocar `getInstance(String, ..)` pelas duas sobrecargas explícitas nas três specs |
| C2 | diagnosticar e corrigir `T+` no dono (`Key+`, `SecretKey+`) | tecelão (descritor, `TypeResolver` ou `InheritanceResolver`) | 1 555 chamadas `getEncoded` sem advice; 94 maus usos no censo | sem C2, `PREPARED_KEY_MATERIAL` quase não tem produtor |
| C3 | produtor para `KeyStore.getEntry` → `SecretKeyEntry.getSecretKey()` | `KeyStoreSpec.mop` | 340 maus usos, idioma Android comum | classe de acusação muda (memória "Mudanças que alteram o que é acusado") |
| C4 | produtores para `ECPublicKeySpec` (e `RSAPublicKeySpec`, `PKCS8EncodedKeySpec`) | spec nova ou `KeyFactorySpec.mop` | 552 maus usos (ktor) | spec nova move os pinos (memória "Tirar ou pôr um .mop") |
| C5 | decidir o tratamento de `null` nos `init` do TLS | `SSLContextSpec.mop:176-208`, `TrustManagerFactorySpec.mop:102-112` | maior massa isolada (okhttp) | decisão de desenho, não defeito |
| C6 | decidir se o predicado de trust manager vale para o elemento, não só para o array | `TrustManagerFactorySpec.mop:218`, `SSLContextSpec.mop:231` | todo `SSLCONTEXT-NOBS-01` do okhttp | decisão de desenho |
| C7 | não ler `randomized` no IV em `DECRYPT_MODE` | `IvChainJunction.mop`, `GCMParameterSpecSpec.mop`, `IvParameterSpec.mop` | toda decifração | a regra CrySL lê; seria divergência registrada |
| C8 | separar `NOBS` das acusações no consolidador (desfecho com e sem `NOBS`) | `consolidate_compare.py` | — | não depende de tecelão nem de spec |

C1, C2 e C8 não mudam o que é mau uso: tiram artefatos e perdas de medição. C3 e C4 removem
acusações falsas mas mudam o conjunto. C5 a C7 são decisões de desenho, que mudam o que o conjunto
diz e pedem registro de divergência contra o oráculo. Qualquer mudança em `.mop` exige reinstrumentar
o corpus (8 h 09 min na instrumentação da `jca_android`, `FUNIL.md`).

## 7. Correções feitas no fim da sessão (14/09) — ler antes das seções 1, 5 e 6

Este documento foi escrito antes de duas verificações. Elas corrigem o enquadramento e **a análise
inteira será refeita de forma independente** antes de qualquer uso.

**7.1 O duplo casamento de `getInstance(String)` não é defeito novo.** O comportamento é conhecido,
medido e deixado em aberto de propósito: `WrapperEmitter.java` agrupa todos os advices de uma
chamada concreta num único wrapper e **não filtra** por aridade de `args()`; conta os incompatíveis
em `advicesExcludedByArity` (`instrument_results.json`). Está escrito como invariante em
`openspec/specs/instrumentation/spec.md:351` (INV-INS-122): "Measuring rather than filtering is
deliberate: a filter would change what every campaign reports". O que este documento acrescenta é o
**tamanho do efeito na estudo02** (seção 5.1), não a descoberta do mecanismo. A descrição "defeito
do tecelão" nas seções 1, 5.1 e 6.2 deve ser lida como "comportamento registrado (INV-INS-122) cujo
efeito não tinha sido medido nas acusações".

**7.2 Causa do `getEncoded()` não tecido (lida no código, não reproduzida em execução).**
1. Advice `after` numa chamada que não é construtor só é aplicado por wrapper; a via inline é pulada
   (`DexWeaver.java`, comentário INV-INS-66, contador `plansSkippedAliasing`).
2. `WrapperEmitter.expandCallTarget` procura sobrecargas com `AndroidClassIndex.methods(classe, nome)`,
   que devolve só métodos **declarados** na classe (`AndroidClassIndex.java:115-126`).
   `javax.crypto.SecretKey` não declara `getEncoded()` — herda de `java.security.Key` (`javap` no
   `android.jar` 37) —, então `SecretKey+.getEncoded()` não gera wrapper nenhum.
3. `Key+.getEncoded()` gera wrapper com dono `Key`. O registro de apelidos para subtipos
   (`DexWeaver.expandWrapperReplacementsForApk`) usa `InheritanceResolver.subtypesOf`, que percorre
   só classes do APK; `SecretKey`, `PublicKey` e `PrivateKey` são interfaces do framework e não
   ganham apelido. A chamada com esses donos não é substituída e fica sem advice.

**7.3 Leitura dos números da seção 1.** "70,9 % não apontam mau uso" não quer dizer que os monitores
erraram: `NOBS` é, por desenho do `.mop`, um relato de "não consegui confirmar a origem", distinto de
`VIOLATED`. O que a seção 4 mede é quanto da métrica "maus usos únicos" (que conta `NOBS` como mau
uso) é feita desse relato. Os 17 409 concentram-se em poucos pontos de código repetidos por
APK × ferramenta × repetição × orçamento: dois métodos do okhttp somam 7 569 (43 %).
