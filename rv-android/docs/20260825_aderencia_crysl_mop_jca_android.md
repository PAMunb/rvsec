# Aderência CrySL→MOP do conjunto `jca_android` — o que está coberto, o que não está, e o que era antes

**Data**: 2026-08-25 · **Árvore auditada**: rvsec `HEAD = 14dd8093` · **Change**: gh105 (grupos 10 e 11 abertos por esta análise)

**Oráculo (D-16, pesquisador, 2026-08-25)**: o oráculo único do conjunto, para **todas** as dimensões — valores, ORDER, alfabeto de eventos e predicados — são as **49 regras CrySL validadas por especialistas** em `RVSec-replication-package/tools/rules/`, pinadas por sha256 (`d7bcc019…`, recomputado nesta auditoria e conferido). O MetaCrySL (`generated/api30/`) **não tem mais papel de oráculo em dimensão nenhuma**: o D-16 supersede o escopo "values only" do D-15. Como os registros e autômatos da árvore atual foram derivados sob o contrato antigo (valores→expert desde o D-15; protocolo→api30), este relatório mede a aderência **contra o expert** e marca explicitamente cada ponto em que o estado atual é herança da âncora api30 e aguarda re-adjudicação (tarefas do grupo 11 da gh105).

Método: seis auditorias independentes (25/08) + dois levantamentos exaustivos (80 cláusulas de valor; ledger de predicados, ORDER, alfabeto e o estado do seed), todos contra fontes primárias — regras, `.mop` atuais, `.mop` do seed congelado, registros de `data/jca_android/`, monitor gerado. Nenhuma análise de outro modelo foi lida.

---

## 1. Sumário executivo — os números de cobertura

| Dimensão | Cobertura medida | Estado sob o D-16 |
|---|---|---|
| **Regras** (49 expert) | **21 com spec pareada**; 28 sem spec (lacuna idêntica no seed — nada abriu nem fechou) | válido — a lacuna é decisão "no new accusation classes", mantida |
| **Valores** (80 cláusulas das 21 regras pareadas) | **30 comparadas literalmente** (22 IGUAL + 6 das 14 em Java + 2 mais-permissivas registradas); **42 deferidas com registro** + 8 acoplamentos do Cipher fora da Util | válido — os valores já respondem ao expert desde o D-15 |
| **Predicados** (ledger derivado: 36 cláusulas) | **21 fiadas** (produtor+consumidor+acusador+códigos) + 14 registradas com medição + 1 unclosable | **pendente de re-derivação (11.1)** — o ledger veio das api30; deltas expert já verificados: 5 cláusulas voltam/abrem |
| **ORDER/alfabeto** | 132/140 símbolos cobertos (**94,3%**); 8 divergências mantidas com registro; 2 skips declarados | **pendente de re-ancoragem (11.2/11.6)** — o mapa aponta símbolos api30; caso já nomeado: construtor do KeyPair |
| **Teste ácido** | MD5, SHA-1, HmacMD5, MD5withRSA, AES/ECB, DES, RC4, Blowfish, ChaCha20 **acusados** em todas | válido — conferido no texto, no monitor gerado e na CLI gh106 (M4: 0 polaridades invertidas) |

**O construto honesto para o artigo**: o instrumento cobre *as cláusulas que o `jca` publicado já checava, com os valores expert corretos, mais a fiação de predicados* — não "as 49 regras". O denominador de valores é 30/80 nas 21 regras pareadas (62,5% das 48 com custo de detecção real — ver correção 2 no rodapé); as 42 deferidas e as 28 regras sem spec estão enumeradas abaixo, cada uma com o que fica mudo.

---

## 2. Cobertura por regra: as 49 regras expert

### 2.1 As 21 pareadas

Cipher, CipherInputStream, CipherOutputStream, DHGenParameterSpec, GCMParameterSpec, HMACParameterSpec, IvParameterSpec, KeyGenerator, KeyManagerFactory, KeyPair, KeyPairGenerator, KeyStore, Mac, MessageDigest, PBEKeySpec, PBEParameterSpec, SSLContext, SecretKeySpec, SecureRandom, Signature, TrustManagerFactory — cada uma com seu `.mop` homônimo. Os 3 `.mop` restantes não pareiam com regra: `SecretKeySpec.mop` (propagador — serve de fato ao ENSURES `preparedKeyMaterial` de `SecretKey.crysl:17`, sem linha própria no conformance_record), `RandomStringPassword.mop` (ponte heurística, hoje sem efeito — negativo registrado) e `IvChainJunction.mop` (junção da cadeia de IV, só predicados).

### 2.2 As 28 sem spec — o que fica de fora, por relevância

**Confirmado: o seed `jca` tinha exatamente os mesmos 23 arquivos.** Nenhuma das 28 lacunas foi aberta ou fechada pelo `jca_android` — e mantê-las é a decisão "no new accusation classes" (classe nova = taxa de FP não medida no corpus).

| Relevância | Regra | O que detectaria |
|---|---|---|
| **ALTA** | `SecretKeyFactory.crysl:22-25` | a rota canônica de PBE/derivação de senha: acusaria `PBKDF2WithHmacSHA1`, `PBEWithMD5AndDES`, `PBEWithSHA1AndDESede`. **A lacuna mais cara do conjunto.** |
| **ALTA** | `KeyAgreement.crysl:40-41` | `{DH, DiffieHellman, ECDH}` + `noCallTo[generateSecret(String)]` — derivar chave simétrica direto do segredo DH sem KDF, misuse real de E2E. |
| **ALTA** | `ECGenParameterSpec.crysl:14-22` | curvas fracas (`secp192r1`, `prime192v1`, `secp160*`) — é como apps escolhem a curva; complementa o `keysize==256` do KeyPairGenerator. |
| MÉDIA | `RSAKeyGenParameterSpec.crysl:15-16` | rota `initialize(RSAKeyGenParameterSpec)` que hoje escapa da checagem de keysize (nota: o expert admite 1024!). |
| MÉDIA | `OAEPParameterSpec.crysl:18-19` / `MGF1ParameterSpec.crysl:14` | OAEP/MGF1 configurados com SHA-1/MD5. |
| MÉDIA | `SSLEngine.crysl:18-43` / `SSLParameters.crysl:20-45` | `setEnabledProtocols({"TLSv1"})` e cipher suites fracas (uso direto incomum em apps). |
| MÉDIA-BAIXA | `AlgorithmParameters.crysl:28-31` | 8 aliases Conscrypt registrados sem spec. |
| BAIXA | `KeyFactory`, `AlgorithmParameterGenerator`, `DHParameterSpec`, `DSAParameterSpec`, `DSAGenParameterSpec`, `DigestInputStream`, `DigestOutputStream`, `CertificateFactory`, `PasswordAuthentication` | pouca capacidade de acusação por valor, classes raras em apps, ou cláusulas de origem estática (senha) inobserváveis em RV dinâmico. |
| BAIXA (sem CONSTRAINTS) | `Key`, `SecretKey`, `ECParameterSpec`, `CertPathTrustManagerParameters`, `KeyStoreBuilderParameters`, `PKIXBuilderParameters`, `PKIXParameters`, `TrustAnchor`, `X509EncodedKeySpec` | nenhuma cláusula de valor a perder; predicados dessas regras entram no delta 11.1. |
| NULA | `Cookie.crysl` | `javax.servlet.http.Cookie` não existe no Android. |

Duas notas: `DigestInputStream`/`DigestOutputStream` carregam FORBIDDEN (`on(boolean)`) que o G-FORB declara fora de escopo por não haver `.mop`; e das 28, **9 nem têm bloco CONSTRAINTS** (11 das 49, mas `HMACParameterSpec` e `KeyPair` são pareadas) — a perda concentra-se nas 7 primeiras linhas da tabela.

---

## 3. Dimensão de valores: as 80 cláusulas, uma a uma

Fonte: `constraint_table.csv` (80 linhas = 42 CRYSL-NAO-IMPLEMENTADO + 22 IGUAL + 14 NAO-DERIVADO + 2 MOP-MAIS-PERMISSIVO — recontado e conferido). Atenção de leitura: a coluna `mop_line` da tabela cita **o seed congelado** (é sobre ele que o G-CONF reproduz a tabela, `agree 66 / disagree 0` — adjudicação 9.19(a)); as âncoras do conjunto atual abaixo foram verificadas arquivo a arquivo.

### 3.1 As 22 IGUAL — transcritas e ativas

Todas as listas/testes seguintes são transcrição literal da cláusula expert, comparadas hoje por **uma** regra de normalização (case-insensitive + `alias_table.csv` via `ConscryptAliasTable`; no Cipher via `CipherTransformationNormalizer`, que resolve alias e dobra caixa antes de delegar aos valores congelados):

| Spec | Cláusula expert | Onde checa hoje (jca_android) |
|---|---|---|
| MessageDigest | `algorithm in {SHA-256, SHA-384, SHA-512}` (:37) | lista `:33`; acusa em g4/updates/d2 (ALG-00/01/02) |
| Signature | os 7 `SHA{256,384,512}with{RSA,ECDSA,DSA}` (:48) | lista `:42-43`; acusa nos 4 inits (ALG-00..03) |
| Mac | os 9 (`HmacSHA256/384/512`, `HmacPBESHA1`, `PBEWithHmacSHA1/224/256/384/512`) (:44) | lista `:31-34` |
| SecureRandom | os 6 (`SHA1PRNG`, `Windows-PRNG`, `NativePRNG*`, `PKCS11`) (:42) | lista `:40-41` (5 inertes no Android — mantidos, *no narrowing*) |
| KeyGenerator | `{AES, HmacSHA256/384/512}` (:29) | lista `:42`; acusa em gk1 |
| KeyPairGenerator | `{RSA, EC, DSA, DiffieHellman, DH}` (:28) + keysizes RSA `{4096,3072,2048}`, DSA/DH `{2048}`, EC `{256}` (:29-32) | lista `:38`, switch `:45-56` (KEYSIZE-00) — `EC`, `DiffieHellman` e `3072` restaurados pelo D-15 |
| KeyStore | `type in {JCEKS, JKS, DKS, PKCS11, PKCS12}` (:52) | lista `:48-49` + 4 platform-values citados (`AndroidKeyStore`, `AndroidCAStore`, `BKS`, `BouncyCastle`) |
| SSLContext | `protocol in {TLSv1.2, TLSv1.3}` (:29) | lista `:43` + platform-value `TLS` (Conscrypt `:81`); **`SSL` deliberadamente acusado** |
| TrustManagerFactory / KeyManagerFactory | `{PKIX, SunX509}` (:25/:28) | listas `:38`; `X509` silencia por alias (`X509→PKIX`, Conscrypt `:90`) |
| SecretKeySpecSpec | `keyAlgorithm in {AES, HmacSHA256/384/512}` (:18) | lista `:38-39` — **restaurada** pelo D-15 (a api30 a tinha deletado) |
| GCMParameterSpec | `tagLen in {96,104,112,120,128}` (:18) | lista `:22`; acusa (CONSTR-00/02) — no seed era guarda silenciosa |
| PBEKeySpec / PBEParameterSpec | `iterationCount >= 10000` (:24/:17) | `:111-113` / `:56-58` e `:105-107` — acusam |
| SecretKeySpecSpec | `length[keyMaterial] >= offset+len` (:19) | `:167-169` (ramo inalcançável na prática — a plataforma lança antes; declarado) |
| IvParameterSpec | `length >= offset+len`, `offset >= 0` (:17-18) | guarda da escrita `:115` |
| DHGenParameterSpec | `exponentSize < primeSize` (:15) | `condition()` `:21-24` — **filtro, não acusador**: violação é silêncio (herdado; risco anotado) |

Ressalva de registro: `GCMParameterSpec.crysl:19-20` (bounds) constam IGUAL na tabela, mas o **atual** os removeu (task 8.1 — caminho inexecutável medido: a plataforma lança `IllegalArgumentException` antes do advice). Custo de detecção nulo; o veredito da tabela responde pelo seed.

### 3.2 As 14 NAO-DERIVADO — checadas em Java, fora do derivador

NAO-DERIVADO **não** significa "não checada": significa que a cláusula vive em fluxo de controle Java (`CipherTransformationUtil`, mapeada à mão), fora do alcance do derivador mecânico do G-CONF. São as 14 cláusulas de acoplamento do **Cipher** (`Cipher.crysl:88-118`). Estado real, uma a uma:

**Implementadas (6)**: modos AES `{CBC, CCM, GCM, PCBC, CTR, CTS, CFB, OFB}` (:97); modos RSA `{"", ECB}` (:101); pad RSA sem modo (:106); paddings RSA/ECB incl. os OAEP (:107-110); paddings AES/CBC-PCBC `{PKCS5Padding, ISO10126Padding}` (:112); paddings AES/stream+GCM+CCM `{NoPadding}` (:113) — todas em `CipherTransformationUtil.java:32-68`, consumidas via `CipherTransformationNormalizer`.

**Não implementadas (8)**, sendo 4 delas *mais estritas* e não silenciosas: as implicações por tipo de chave (:88-96 — `instanceOf[key,…] => alg in {…}`; nota: a família `PBEWithHmacSHA*AndAES_*` que o expert admite fica **acusada** — a Util só admite AES/RSA, mais restritiva, documentado no Normalizer `:44-45`); os acoplamentos valor↔evento (:115-118 — `noCallTo/callTo[IV]`, `noCallTo[AADUpdate]`; o espírito do IV é parcialmente servido pelos predicados da IvChainJunction, mas não como estas cláusulas).

### 3.3 As 2 MOP-MAIS-PERMISSIVO — variantes do próprio congelado

- **Mac**: 17 entradas contra 9 do expert; 6 dobram por alias, mas `PBEWITHHMACSHA` e `PBEWITHHMACSHA-256` não dobram para nada — inertes (nenhum provider as resolve), mantidas porque remover entrada que não muda veredito é edição não validada.
- **SecretKeySpecSpec**: 6 variantes `HMAC[-/]SHA*` num serviço sem linhas de alias — mesmas condições.

### 3.4 As 42 CRYSL-NAO-IMPLEMENTADO — o silêncio declarado, em 4 famílias

Todas com registro `deferred-constant` citando o texto **expert** (nunca a reconstrução api30, provadamente mutilada), e todas com o mesmo antes/depois: **o seed nunca as checou; o atual continua exatamente tão silencioso**. A promoção é a task 2.14, condicionada ao harness dimensionar as acusações.

1. **Proteção de senha — 9 cláusulas** (`neverTypeOf`×5, `notHardCoded`×4, em KeyStore/KMF/PBEKeySpec/SecretKeySpec): estruturalmente inadequadas a RV dinâmico puro — `neverTypeOf` pergunta pelo tipo estático da variável-fonte (o call site já fixa `char[]`); `notHardCoded` é propriedade da origem no código-fonte (domínio de análise estática/taint). **Fica mudo**: senha hardcoded e senha vivendo em `String`. É a família que justifica a frase da auditoria: "nenhuma proteção sobre material de senha sobrevive à cadeia".
2. **Janelas de buffer — 31 cláusulas** (`length/offset/len` em CipherStreams ×6, Cipher ×10, Mac ×4, MessageDigest ×6, Signature ×3, GCM `len>0`, IvParameterSpec `len>0`): custo de detecção ≈ zero — nos construtores a plataforma lança antes do advice (medido em 3 casos); nas janelas de update a JCA valida índices. **Fica mudo**: erro de índice, não misuse criptográfico. (Os dois `len>0` estão aqui porque ambos os conjuntos testam `len>=0` — desvio de um símbolo, sem acusação em caso algum.)
3. **`encmode in {1,2,3,4}`** (Cipher :121) — 1 cláusula; `Cipher.init` rejeita opmode inválido sozinho.
4. **Keysize AES do KeyGenerator** (`AES => keysize in {128,192,256}`, :30) — 1 cláusula; o caso nomeado da regra *no-new-accusation-classes*.

9 + 31 + 1 + 1 = 42 ✓.

---

## 4. Dimensão de predicados: o ledger e os deltas do D-16

### 4.1 Estado atual (ledger derivado sob a âncora antiga): 21 + 14 + 1 = 36

**As 21 fiadas** — cada uma com leitura em corpo de evento (nunca `condition()`), três valores (VIOLATED ≠ NOT_OBSERVED, códigos CONSTR/NOBS distintos), produtor no ponto de aceitação e acusador em `codes.csv`:

| Cláusula | Consumidor | Produtor |
|---|---|---|
| Cipher `generatedKey[key, alg]` | CipherSpec.i2 `:166` (leitura composta das 3 origens) | KeyGenerator `:215`, KeyStore `:193/:195`, SecretKeySpecSpec `:237`, KeyPair `:117/:137` |
| Cipher `randomized[ranGen]` | IvChainJunction `:247-295` (4 overloads) | hub SecureRandom `:320/:330/:334` |
| Cipher `!macced[_, plainText]` | CipherSpec f5/f6 + IvChainJunction (validateAbsent) | Mac `:379/:383` (@match) |
| Cipher `…=> preparedIV/preparedGCM[params]` | IvChainJunction `:160/:194` (guarda no corpo) | IvParameterSpec `:138`, GCM `:164` (@match) |
| GCM/Iv/PBEKeySpec/PBEParam `randomized[salt/iv/src]` | corpos dos construtores | hub SecureRandom |
| KeyGenerator `randomized[ranGen]` | 3 inits novos `:121-153` | hub |
| KMF/TMF `generatedKeyStore` | inits `:123/:126` | KeyStore `:189` (@match após Loads) |
| KeyPair `generatedPrivkey/Pubkey[cons*]` | c1 `:77/:86` | gpr/gpu `:137/:117` |
| Mac `!encrypted[output1,_]` | f2 `:316` (validateAbsent) | CipherSpec `:434/:442` |
| SSLContext `generatedKeyManager/TrustManager` | init `:199/:208` | gkm1/gtm1 `:149/:179` |
| SecretKeySpec `preparedKeyMaterial` | SecretKeySpecSpec c1/c2 `:110/:172` | propagador SecretKey `:125` |
| SecureRandom `randomized[seed]` (autocadeia) | c2 `:95`, setSeed2 `:171` | @match1 `:320` + genSeed/nextBytes |
| Signature `generatedPrivkey/Pubkey` | i1/i2/i4 `:146-194` | KeyPair, KeyStore |

**As 14 registradas com medição**: 10 `unmonitored-*` (uma das pontas sem `.mop` — AlgorithmParameters ×3, CertPathTMP, Cipher `preparedAlg`, KPG `preparedDSA/RSA`, PKIX ×2, SecretKeyFactory `speccedKey`), 2 `unreachable-composition` (#17 KPG `preparedDH` — a JCA recusa `DHGenParameterSpec` em `initialize`, medido; #21 Mac `preparedHMAC` — a classe produtora não existe no android-30), 2 `vacuous` (#23 Mac `!encrypted[output2,_]` — array alocado fresco; **#30 SSLContext `randomized[sr]` — cai com o D-16**, ver 4.2). **1 `unclosable`**: `preparedEC` (nenhuma regra **pareada** o garante — `ECGenParameterSpec:25` e `ECParameterSpec:17` o garantem, e ambas estão entre as 28 sem spec). O único NEGATES real do conjunto (`PBEKeySpec` `speccedKey` after `clearPassword`) está traduzido como o único `negate` do store.

### 4.2 O que o oráculo expert muda — deltas verificados na fonte (25/08), ordenados pela 11.1/11.5

| Delta | Cláusula expert | Consequência |
|---|---|---|
| **Volta** | `Mac.crysl:54` `generatedKey[key,_]` | a leitura que a 4.9 deletou ("a api30 não declara") **retorna** — no corpo do init, três valores, códigos próprios (11.5a) |
| **Abre** | `SSLContext.crysl:18` `i1: init(km, tm, random)` + `:34` `randomized[random]` | o expert **liga** `random` no init — o `vacuous` do #30 era artefato api30 e cai; a fiação abre (11.5b) |
| **Abre (registro)** | `TrustManagerFactory.crysl:29` `generatedManagerFactoryParameters[params]` | produtores sem `.mop` → disposição esperada `unmonitored-producer`, derivada sob o expert (11.5c) |
| **Abre (registro)** | `SecureRandom.crysl:46` `randomized[lSeed]`; `:52` `randomized[randInt] after nI` | `long`/`Integer` boxam fresco — limite de plataforma, derivado não assumido (11.5d) |
| **Reabre** | `KeyPair.crysl:27` `generatedKeypair[this,_] after Con` | ENSURES que a api30 fazia opcional; pareamento no ledger novo |
| **Nomenclatura** | `SSLContext.crysl:32` `generatedKeyManagers[km]` (plural) | resolver o pareamento no ledger, não no código |

O ledger completo sob o expert (varredura das 49 regras, não só das 33) é a tarefa 11.1 — os números "36/21/14/1" acima descrevem a derivação histórica e **vão mudar**.

---

## 5. Dimensão ORDER e alfabeto

### 5.1 Estado atual

- **Alfabeto**: 140 símbolos-base nas regras pareadas; **132 cobertos (94,3%)**. Os 8 sem evento: `Cipher.iv` (a própria regra não o ordena; a cláusula `callTo(iv)` está deferida), os 3 `Entries` do KeyStore (`scE/skE1/skE2` — fora do ORDER da própria regra; registro ordenado pela 10.5g), `SecureRandom.ne` (`next(int)` é `protected`), `SecretKey.d` (`destroy()` lança nas duas implementações — INV-INS-137), e os 2 construtores de 1 argumento dos CipherStreams (`protected` no android-30). **Nenhum dos 8 é alcançável por programa monitorado ou ordenado pela regra** — a cobertura efetiva do observável é 100%.
- **Eventos extras sem símbolo** (16 `order-unmapped`, todos com classificação): os gêmeos/acusadores absorvidos pela gh105 (g3/g4, FORB do PBEKeySpec e do getDefault), `CipherOutputStream.fl` (flush fora do alfabeto da regra — caminho flush-only registrado, FN), `Mac.updateBuffer` (overload Android).
- **8 divergências de ordenação mantidas de propósito** (allowlist, cada uma com razão e testemunha): CipherInputStream (`c1` protected — excesso do lado da regra), CipherOutputStream (flush-only), Cipher (`g1 i1 u1` — update sem final, nada no corpus), KeyGenerator (`g1 g1 gk` — folga do seed publicado), KeyStore (`g1 l1 g1 l1` — o `+` externo do seed), SSLContext (segundo `createSSLEngine`), SecretKeySpec (`d` — lado da regra), SecureRandom (`c1 c1`). **Eram nove**: a do KeyPair foi **reparada** na 9.11 e a testemunha do KeyStore substituída na 9.16 (o README ainda diz "nine" — correção ordenada pela 10.3).
- **2 skips declarados** do G-ORDER: IvChainJunction e RandomStringPassword (sem regra — prosa no cabeçalho do mapa, nunca linha de dados).

### 5.2 O que o D-16 muda aqui

O `order_alphabet_map.csv` re-ancora nos símbolos e linhas do **expert** (11.2) e o G-ORDER passa a comparar contra o ORDER expert (11.3). O diff KeyStore expert×api30 feito em 25/08 mostra que a estrutura sobrevive (só mudam rótulos de agregados), então a maioria re-ancora mecanicamente — mas o caso já nomeado onde os oráculos divergem de verdade é o **KeyPair**: o expert ordena `Con, (GetPubl | GetPriv)*` com construtor **obrigatório**, e o autômato atual é `(c1 | epsilon)` (reparo 9.11, medido: construtor obrigatório acusava todo par saído de `generateKeyPair()` — 668 linhas, 8 apps, porque a plataforma constrói o par internamente). Sob o D-16 essa escolha deixa de ser "obediência à api30" e vira **registro de divergência contra a regra expert, adjudicado por você** (11.6). A varredura completa dos 21 ORDERs contra o expert é o resto da 11.6.

---

## 6. As specs originais (`jca` Java): como era, e o que ganhamos

### 6.1 O antes, em números (medidos no seed congelado, base `7e7acb69`)

| O que | Medida |
|---|---|
| Substrato de predicados | 134 linhas `ExecutionContext` (23 import, 27 validate, 49 setProperty, 9 remove, 25 accepting-state, 1 comentário) |
| Leituras de predicado | **27, todas em `condition()`** — guarda falsa suprime a transição e fabrica `InvalidSequenceOfMethodCalls`; mecanismo provado no monitor gerado (`return false` antes de `handleEvent`) |
| Escritas | 49; **42 fora do ponto de aceitação** (marcavam predicado até em sequência rejeitada); `GENERATED_PRIVATE_KEY`: **zero escritas** — a leitura correspondente do Cipher era insatisfazível |
| Cláusulas com alguma fiação | das 36, **8 tinham leitura** (todas defeituosas por posição) e 6 tinham escrita sem leitor; **22 não existiam de nenhum lado** |
| `remove()` | 9; **8 em `@fail`** — semântica ("desfazer o predicado quando o autômato falha") que nenhuma geração CrySL tem |
| Acusadores órfãos | **17 em 9 specs** (fora do `ere`, linha all-fail): relatório dobrado ou, no caso medido do TMF, **supressão do achado real** (2 ORDER espúrios, 0 acusação de algoritmo) |
| Idiomas de comparação | **11 em 3 famílias**: `contains()` case-sensitive em 8 specs, `toUpperCase()` em 3 — a mesma string era misuse numa spec e não noutra |
| Specs mortas/inertes | `Signature.s1/s2` (assinaturas erradas — o ramo de assinatura **nunca teceu**), `TMF.gtm1` (3 defeitos + propriedade errada `GENERATED_KEY_MANAGERS`), `SSLContext.engine` (retorno `void`), `GCMParameterSpec` **inteiro** (dois eventos com o mesmo nome + `ere` referindo evento inexistente + tudo em `condition()`: **zero relatórios possíveis**), `SSLContext.getDefault()` proibido pelos dois lados e silencioso, FORBIDDEN do PBEKeySpec acusado como ORDER |
| Defeito de semântica | `KeyPairSpec:38` escrevia a chave **privada** sob `GENERATED_PUBLIC_KEY`; `SecretKeySpec` conflava `randomized` com material de chave (bytes hardcoded passavam por aleatórios rio abaixo) |
| Custo no publicado | os 17 órfãos sustentavam **até 39.682 eventos = 56,1%** do `InvalidSequenceOfMethodCalls` (teto medido, não atribuição causal); caso âncora: `SecureRandom.next2` ausente do estado `end` = 12.400 eventos espúrios |

Importante para o antes/depois: **as listas de valores do seed eram as do expert** (transcritas corretamente — é o que o G-CONF confirma com `agree 66 / disagree 0`); o que falhava no seed era o *resto do instrumento*: posição das leituras, autômatos, idiomas de comparação, acusadores órfãos, specs mortas.

### 6.2 O que ganhamos, transição por transição

| Eixo | seed `jca` (Java) | `jca_android` hoje |
|---|---|---|
| Valores | expert, mas 11 idiomas inconsistentes | expert + **uma** normalização auditável (175 aliases = fonte Conscrypt, teste de igualdade código↔CSV) |
| Predicados | 8/36 lidas (mal), 22 inexistentes | 21/36 fiadas com três valores e códigos; 14 registradas com medição; grafo fechado e gateado |
| Autômatos | 17 órfãos, 5 specs mortas/inertes | órfãos fundidos/absorvidos; specs ressuscitadas (Signature assina, TMF produz, GCM acusa, getDefault FORB) |
| Relatórios | 50 sítios, 1 comentado, envelopes autocontraditórios, 72,93% `unknown` | **115 sítios ↔ 115 códigos** (bijeção gateada), envelope v=1, NOBS separado de violação |
| Semântica | privada-como-pública; `randomized` conflado; `remove()` em `@fail` | corrigidos; único `negate` = único NEGATES real |
| Custo novo | — | 42 deferências declaradas; NOBS sem análogo anterior; 4 populações × 3 semânticas de `UnsafeAlgorithm` (toda comparação nomeia o oráculo); e, sob o D-16, o passivo de re-ancoragem do protocolo (grupo 11) |

**Conclusão**: melhorou em todos os eixos que importam — e o D-16 fecha a última inconsistência de fundamento: o instrumento passa a responder, em todas as dimensões, à única fonte com validação de especialista.

---

## 7. O que deve constar no artigo (denominadores e limites)

1. **Oráculo**: as 49 regras expert pinadas (sha256), únicas — com os warts transcritos e declarados: `CCM` (só na cópia do replication package), `OAEPWithMD5` sem variante OAEP-SHA-1, sem `SHA-224`, sem `SHA1/SHA224withECDSA`; e a divergência do upstream atual (que dropou `CBC/PCBC` — o pin evita re-ancoragem acidental, e `AES/CBC` segue admitido aqui).
2. **Denominador de valores**: 30/80 cláusulas comparadas literalmente nas 21 regras pareadas; 42 deferidas (senha = domínio de análise estática; buffers = custo ~zero; acoplamentos por tipo de chave do Cipher; keysize AES) — *não* "as 49 regras".
3. **Denominador de regras**: 21/49 com spec; as 3 lacunas caras nomeadas (SecretKeyFactory, KeyAgreement, ECGenParameterSpec).
4. **Predicados**: 21 fiadas / 14 registradas / 1 unclosable sob a derivação histórica; re-derivação expert em curso (grupo 11) com 5 deltas já verificados.
5. **NOBS não é violação**; a junção conta como acusador próprio; comparações entre `jca`, arquivado, pré-D-15 e atual nomeiam o oráculo de cada contagem.
6. **Envelope de plataforma**: API 30 / Conscrypt `android11-release`; Bouncy Castle embarcado fora do oráculo de aliases; camada platform-value fechada (5 entradas citadas; `SSL` deliberadamente acusado).

## 8. Pendências abertas por esta análise (nos artefatos da gh105)

- **Grupo 10** (auditoria interna de 25/08): 4 linhas G-2a; escopo do G-PRED no CLI; refresh de README (112→115, "nine"→8), predicate_graph, divergence/conformance; comentários estale em 7 specs; imports do GCM; registro-sem-reparo dos 4 achados comportamentais adiados; re-execução da medição 8.4; **10.10** = reparo do splitter `generatedKey` do CipherSpec (classe de FP: grafias de alias/compostas — o store já dobra caixa), decisão sua.
- **Grupo 11 (D-16)**: re-derivação do ledger (11.1) e do mapa de alfabeto (11.2) contra o expert; gates no oráculo único (11.3); registros single-oracle com adenda de supersessão (11.4); fiações que voltam/abrem (11.5 — Mac `generatedKey`, SSLContext `randomized[random]`, TMF `params`, SecureRandom `lSeed`); ORDER re-adjudicado (11.6 — KeyPair nomeado); verificação (11.7).

Nada disso foi implementado: os artefatos da change ordenam; a execução aguarda sua decisão por tarefa nos blocos comportamentais.

---

## 9. Correções aplicadas em 2026-08-25 (segunda passagem)

Três números desta análise foram refeitos por enumeração direta sobre as fontes e corrigidos acima.
Registrados aqui para que uma leitura de versão anterior não fique órfã:

1. **9 das 28** regras sem spec não têm `CONSTRAINTS` — não 11. As outras duas sem `CONSTRAINTS`
   (`HMACParameterSpec`, `KeyPair`) são pareadas, então não pertencem às 28. O texto corrido
   contradizia a própria tabela da §2.2, que já listava 9.
2. As 14 cláusulas `NAO-DERIVADO` do `Cipher` estão **6 implementadas / 8 não** — não 7/7. Conferido
   linha a linha em `Cipher.crysl:88-118` contra `CipherTransformationUtil.java:32-68`: implementadas
   são `:97`, `:101`, `:106`, `:107`, `:112`, `:113`. Das 8 restantes, quatro (`:90`, `:94`, `:98`,
   `:103`) não são silêncio e sim **excesso de restrição** — a Util colapsa as implicações em
   `alg ∈ {AES, RSA}`, então a família `PBEWithHmacSHA*AndAES_*` fica acusada; e quatro são silêncio
   de fato (`:88`, `:115`, `:116`, `:118`). Em consequência, o denominador de valores comparados é
   **30/80** e não 38/80.
3. `preparedEC` é insaciável porque nenhuma regra **pareada** o garante, não porque nenhuma regra o
   garanta.

A versão narrativa e completa desta análise, com a taxonomia dos motivos de tradução parcial e o
inventário do que é exclusivamente Android, está em
[`20260825_dossie_jca_android.md`](20260825_dossie_jca_android.md).
