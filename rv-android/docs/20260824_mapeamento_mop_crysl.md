# O mapeamento JavaMOP ↔ CrySL, nas duas direções

**Data:** 24 de agosto de 2026
**Carimbo:** `rvsec @ 5fbe8173` (branch `modules`) · `rvsec-cognicrypt @ f2f4d3b0` (oráculo) · `MetaCrySL @ fb1ecaba` (só controle histórico). **Todos os números deste documento são do commit `5fbe8173`, lidos via `git show`/`git archive`, salvo indicação explícita** — o worktree diverge do HEAD nesta janela (a gh105 readapta 13 `.mop` de `jca_android` + `codes.csv`), e números de disco e de commit não coincidem.
**Método:** cinco leituras independentes por subagentes (matriz CrySL→MOP; matriz MOP→CrySL; componentes/parsers/writers; consistência da change; re-medição sem MetaCrySL), seguidas de uma verificação adversarial que re-executou as medições por rota própria e refutou contra a fonte. As erratas da verificação já estão aplicadas aqui.
**Escopo:** este documento serve à change `gh106-mop-crysl-conformance`. Por decisão do pesquisador (24/08/2026), a gh106 faz **tradução mecânica e literal** entre os formalismos, contra as regras CrySL Java originais do upstream (`rvsec-cognicrypt/CrySL-Rules`, 49 regras). Onde a spec `jca_android` diverge da regra, o componente **acusa a divergência**; a adjudicação entre *adaptação Android deliberada* e *infidelidade* é responsabilidade do corpus e do seu registro (`data/jca_android/divergence_record.csv`, trabalho da linhagem gh104/gh105) — não do tradutor, e não desta change.

---

## 1. O veredito, primeiro

**A conversão é cientificamente válida — com perdas conhecidas, enumeradas e medidas.** O mapeamento **não é 100 % e não precisa ser**: cada construção dos dois formalismos tem estatuto declarado (`BIJETIVO` · `SOBRE-APROXIMA` · `SUB-APROXIMA` · `HEURÍSTICO` · `NÃO MAPEIA`), as construções sem imagem têm raiz identificada (formalismo, substrato dinâmico×estático, ou ferramenta) e direção de erro declarada, e as perdas estão redigidas como ameaças à validade (§5). Perda registrada não é bloqueio; perda não registrada seria o defeito.

Os denominadores do veredito:

- **Direção CrySL→MOP (§3):** de **42** construções sintáticas com ocorrência no corpus upstream, **35 (83 %) mapeiam com estatuto bijetivo** — 24 diretamente no autômato/pointcut e 11 via código Java no handler ou na guarda (fiéis em semântica, invisíveis a métricas estruturais) — 2 são heurísticas, 1 sobre-aproxima e **4 não mapeiam**, todas errando na direção do silêncio (falso negativo), nunca do alarme falso.
- **Direção MOP→CrySL (§4):** de **36** construções com ocorrência, **16 são bijetivas** — e concentram o grosso do volume (eventos, pointcuts, autômato, os quatro verbos de predicado do substrato novo) — 3 sobre-aproximam, 2 sub-aproximam, 9 são heurísticas e 6 não mapeiam, das quais **3 com perda nula** (envelope de relatório).
- Sobre- e sub-aproximação erram em direções opostas e **não podem ser somadas** num único percentual.

## 2. As medições da virada de oráculo

Regras de contagem declaradas antes de cada número; reproduzidas por **duas implementações independentes** (a do medidor e a do verificador adversarial), ambas calibradas contra os totais publicados na Fase 0 antes de qualquer número inédito.

### 2.1 Parse do upstream, sem normalização

Regra: um `CrySLModelReader` novo por regra (CrySLParser 4.0.6), modo `jdk`, nenhuma substituição léxica. **47 de 49 regras parseiam**; 215 linhas de assinatura de evento resolvidas. As duas falhas:

| Regra | Erro | Causa |
|---|---|---|
| `OAEPParameterSpec.crysl` | `:8: mismatched input 'alg' expecting RULE_ID` | `OBJECTS` declara `java.lang.String alg;` — `alg` é palavra reservada da gramática 4.x |
| `SSLEngine.crysl` | `:12: Couldn't resolve reference to Event 'cp1'` | bug do upstream: o evento declarado na linha 11 chama-se `ep1`; a linha 12 escreve `EnableProtocol := cp1;` |

A normalização léxica (as cinco substituições do `api30`) fica **sem objeto**: o upstream carrega sem nenhuma.

### 2.2 Pareamento por tipo declarado — 22 de 24

O pareamento por nome de arquivo é ambíguo (`SecretKeySpec.mop` casaria `SecretKey.crysl` **e** `SecretKeySpec.crysl`, ambas existem) e está proibido. A regra: lado CrySL = FQN da linha `SPEC`; lado MOP = tipo do parâmetro da declaração da spec; para as duas specs sem parâmetro, o tipo declarante do pointcut. **22 das 24 specs de `jca_android` pareiam; as duas sem par são `IvChainJunction` (junção, não traduz regra) e `RandomStringPassword` (`String` não tem regra).**

| Arquivo `.mop` | Spec declarada | Tipo declarado | Regra `.crysl` |
|---|---|---|---|
| CipherInputStreamSpec.mop | CipherInputStreamSpec | CipherInputStream *(pointcut)* | CipherInputStream.crysl |
| CipherOutputStreamSpec.mop | CipherOutputStreamSpec | CipherOutputStream *(pointcut)* | CipherOutputStream.crysl |
| CipherSpec.mop | CipherSpec | Cipher | Cipher.crysl |
| DHGenParameterSpecSpec.mop | DHGenParameterSpecSpec | DHGenParameterSpec | DHGenParameterSpec.crysl |
| GCMParameterSpecSpec.mop | GCMParameterSpecSpec | GCMParameterSpec | GCMParameterSpec.crysl |
| HMACParameterSpecSpec.mop | HMACParameterSpecSpec | HMACParameterSpec | HMACParameterSpec.crysl |
| IvChainJunction.mop | IvChainJunctionSpec | Cipher | **SKIP** (junção) |
| IvParameterSpec.mop | IvParameterSpecSpec | IvParameterSpec | IvParameterSpec.crysl |
| KeyGeneratorSpec.mop | KeyGeneratorSpec | KeyGenerator | KeyGenerator.crysl |
| KeyManagerFactorySpec.mop | KeyManagerFactorySpec | KeyManagerFactory | KeyManagerFactory.crysl |
| KeyPairGeneratorSpec.mop | KeyPairGeneratorSpec | KeyPairGenerator | KeyPairGenerator.crysl |
| KeyPairSpec.mop | KeyPairSpec | KeyPair | KeyPair.crysl |
| KeyStoreSpec.mop | KeyStoreSpec | KeyStore | KeyStore.crysl |
| MacSpec.mop | MacSpec | Mac | Mac.crysl |
| MessageDigestSpec.mop | MessageDigestSpec | MessageDigest | MessageDigest.crysl |
| PBEKeySpecSpec.mop | PBEKeySpecSpec | PBEKeySpec | PBEKeySpec.crysl |
| PBEParameterSpecSpec.mop | PBEParameterSpecSpec | PBEParameterSpec | PBEParameterSpec.crysl |
| RandomStringPassword.mop | RandomStringPasswordSpec | String | **SKIP** (sem regra) |
| SSLContextSpec.mop | SSLContextSpec | SSLContext | SSLContext.crysl |
| SecretKeySpec.mop | SecretKeySpec | SecretKey | SecretKey.crysl |
| SecretKeySpecSpec.mop | SecretKeySpecSpec | SecretKeySpec | SecretKeySpec.crysl |
| SecureRandomSpec.mop | SecureRandomSpec | SecureRandom | SecureRandom.crysl |
| SignatureSpec.mop | SignatureSpec | Signature | Signature.crysl |
| TrustManagerFactorySpec.mop | TrustManagerFactorySpec | TrustManagerFactory | TrustManagerFactory.crysl |

### 2.3 Denominadores de M3 e M4

**M3 (regra R1):** uma cláusula por `;` dentro de `CONSTRAINTS`, comentários removidos, `&&` não separado.

```
upstream, 49 regras       : 119
upstream, as 22 pareadas  :  80   <- denominador novo de M3
api30,    33 regras       :  62
api30,    as 22 pareadas  :  55   <- denominador antigo
```

Doze das 22 regras pareadas perdem cláusulas na geração `api30` (25 cláusulas ao todo; nenhuma regra ganha): CipherInputStream 3→1 · CipherOutputStream 3→1 · DHGenParameterSpec 1→0 · GCMParameterSpec 4→1 · IvParameterSpec 3→0 · KeyManagerFactory 3→2 · KeyStore 5→4 · Mac 5→3 · MessageDigest 7→3 · PBEKeySpec 3→2 · SecretKeySpec 3→1 · Signature 4→1. O numerador de M3 **tem de ser remedido**: cláusulas que o `api30` apagou podem estar implementadas no `.mop` e hoje figurar como `MOP-SEM-BASE` (as 4 linhas do `constraint_table.csv` são candidatas).

**M4 (cláusulas de `ENSURES`/`REQUIRES`/`NEGATES`, mesma mecânica):** o denominador novo é **135** (76 ENSURES + 57 REQUIRES + 2 NEGATES nas 49 regras; 84 nas 22 pareadas; 51 nas 27 sem `.mop`), com sensibilidade 132 se as 2 regras que não parseiam ficarem fora — decisão da change, precedente do `api30` (o 92 conta as 33, incluindo 3 que não parseiam) diz que entram. **A estimativa "perto de 119" do handoff estava errada: 119 é o total de M3 do upstream, não de M4.** O contador foi calibrado reproduzindo o 92 (= 54+36+2) do `api30` antes de publicar o 135, e o 135 foi confirmado por rota independente (a soma por seção da matriz do §3 dá 76/57/2, medida por outro autor e outra rota).

**Regras upstream sem par `.mop`: 27** (contra 11 no `api30` — o débito de cobertura quase triplica): AlgorithmParameterGenerator, AlgorithmParameters, CertPathTrustManagerParameters, CertificateFactory, Cookie, DHParameterSpec, DSAGenParameterSpec, DSAParameterSpec, DigestInputStream, DigestOutputStream, ECGenParameterSpec, ECParameterSpec, Key, KeyAgreement, KeyFactory, KeyStoreBuilderParameters, MGF1ParameterSpec, OAEPParameterSpec, PKIXBuilderParameters, PKIXParameters, PasswordAuthentication, RSAKeyGenParameterSpec, SSLEngine, SSLParameters, SecretKeyFactory, TrustAnchor, X509EncodedKeySpec.

### 2.4 A P1 refeita sobre o upstream

`V3Fresh` (leitor novo por regra), 49 regras upstream, modo `jdk` × modo `android` com o `android.jar` da API 30: **215 linhas de assinatura resolvida nos dois modos, `diff` vazio** — o `android.jar` não muda uma única linha resolvida, como no `api30`. Conferência contra o `android.jar` (`ApiCheck`, 4.750 classes): `215 = 175 exata + 29 só-aridade + 5 classe-ausente + 6 método-ausente`. Classe-ausente: `javax.servlet.http.Cookie` ×2, `java.security.spec.DSAGenParameterSpec` ×2 (só API ≥ 35), `javax.xml.crypto.dsig.spec.HMACParameterSpec` ×1. Os 6 método-ausente são todos a limitação declarada do conferidor (não segue herança). `Unknown{UnresolvedSignature}` contra o `android.jar` fica **mais** importante com o oráculo único: é o único lugar onde o Android entra na conta do componente.

## 3. A matriz CrySL → MOP

Corpus: as 49 regras upstream (1.632 linhas), lidas na íntegra. Regras de contagem: **occ** = ocorrências textuais (cláusulas reunidas por `;`, comentários excluídos, `&&` não separa); **reg** = regras com ≥ 1 ocorrência; contagens de `in {` restritas à seção `CONSTRAINTS` (96 no corpus inteiro; os 13 de `REQUIRES` pertencem à linha 33). Presença de seção: SPEC/OBJECTS/EVENTS/ORDER/ENSURES 49/49 · CONSTRAINTS 38/49 · REQUIRES 30/49 · FORBIDDEN 4/49 · NEGATES 2/49.

Estatutos: **B** = bijetivo · **B/cód** = bijetivo via código Java no handler/guarda (fora do autômato — invisível a métricas estruturais) · **SOBRE** · **HEU** = heurístico · **NM** = não mapeia.

| # | Seção | Construção | occ | reg | Exemplo | Estatuto | Motivo |
|---|---|---|---:|---:|---|---|---|
| 1 | SPEC | `SPEC <FQN>` | 49 | 49 | AlgorithmParameterGenerator.crysl:1 | **B** | vira o tipo do parâmetro da spec MOP (regra do §2.2); a fronteira do parâmetro único não morde: 0 das 24 specs declaram tupla |
| 2 | OBJECTS | declaração tipada (assinatura de evento) | 233 | 49 | AlgorithmParameterGenerator.crysl:4 | **B** | tipos vão direto para `call(...)`/`args(...)` |
| 3 | OBJECTS | mesmo objeto em vários eventos (correlação) | — | 49 | Cipher.crysl:26–27 × :69 | **HEU** | JavaMOP fatia só sobre o parâmetro da spec; a correlação dos demais objetos passa pelo `PredicateStore` chaveado por identidade — aproximação |
| 4 | OBJECTS | tipo genérico | 1 | 1 | PKIXBuilderParameters.crysl:6 | **SOBRE** | *erasure* no pointcut casa qualquer `Set` |
| 5 | OBJECTS | arrays / primitivos / classes internas | 49+61+6 | 26/25/2 | KeyStore.crysl:10 | **B** | exprimíveis em assinatura AspectJ |
| 6 | EVENTS | evento rotulado com parâmetros | 218 | 49 | AlgorithmParameterGenerator.crysl:11 | **B** | `event l before/after(...): call(...) && args(...)` |
| 7 | EVENTS | evento construtor | 43 | 30 | CertPathTrustManagerParameters.crysl:7 | **B** | `call(Type.new(...))` |
| 8 | EVENTS | retorno `x = m(...)` | 38 | 20 | AlgorithmParameterGenerator.crysl:21 | **B** | `after(...) returning (T x)` |
| 9 | EVENTS | wildcard `_` em parâmetro | 28 | 19 | AlgorithmParameterGenerator.crysl:12 | **B** | `*`/`..` no pointcut |
| 10 | EVENTS | agregado `Ev := a \| b` | 121 | 48 | AlgorithmParameterGenerator.crysl:13 | **B** | expansão 1:N sobre disjunção; ressalva: o alfabeto resultante não é disjunto (perda transversal T1, §5) |
| 11 | EVENTS | rótulo com `this` | 0 | 0 | — | — | não ocorre no corpus (os 38 `this` estão todos em ENSURES/NEGATES) |
| 12–17 | ORDER | `,` 59/28 · `\|` 15/11 · `*` 10/9 · `+` 21/9 · `?` 8/8 · `()` 26/12 | — | — | CertificateFactory.crysl:24 | **B** | operadores regulares do `ere`; `?` expande em `(x \| ε)`; determinização obrigatória por correção (*no-op* no corpus atual) |
| 18 | ORDER | **semântica de aceitação** (operação incompleta) | — | 28 | CipherInputStream.crysl:23 | **NM** | JavaMOP tem `@fail`/`@match` e nenhum evento de fim de traço — perda P1 |
| 19 | CONSTRAINTS | pertinência `x in {...}` | 83 | 27 | AlgorithmParameterGenerator.crysl:28 | **B/cód** | igualdade de valor em runtime no handler; nota: onde o `jca_android` injeta `ConscryptAliasTable.matches()`, a allow-list idêntica em texto é mais permissiva — é **divergência a acusar** pelo tradutor literal, adjudicada no corpus (§0) |
| 20 | CONSTRAINTS | comparação aritmética | 51 | 16 | PBEKeySpec.crysl:24 | **B/cód** | compila para `condition(...)`; a guarda mora a montante das tabelas (T2, §5) |
| 21 | CONSTRAINTS | partes de string `alg/mode/pad(...)` | 11+10+5 | 1 | Cipher.crysl:88,:97,:103 | **B/cód** | split da transformation em código auxiliar; só `Cipher.crysl` |
| 22 | CONSTRAINTS | implicação `=>` | 26 | 6 | Cipher.crysl:88 | **B/cód** | `if` no handler; acoplamento CONSTRAINTS↔ORDER quando o consequente é `callTo`/`noCallTo` |
| 23 | CONSTRAINTS | conjunção `&&` (6 occ/1 reg) / disjunção `\|\|` (3 occ em 1 cláusula/1 reg) | 6/3 | 1/1 | Cipher.crysl:106; :88 | **B/cód** | operadores booleanos de Java |
| 24 | CONSTRAINTS | `instanceOf[x, T]` | 4 | 1 | Cipher.crysl:88 | **B** | `instanceof` em runtime é exato — o monitor dinâmico supera o estático aqui |
| 25 | CONSTRAINTS | `neverTypeOf[x, T]` | 7 | 5 | KeyManagerFactory.crysl:26 | **NM** | propriedade do tipo estático da origem — perda P2 |
| 26 | CONSTRAINTS | `notHardCoded[x]` | 4 | 4 | KeyManagerFactory.crysl:27 | **NM** | constância literal é propriedade do código-fonte — perda P3 |
| 27 | CONSTRAINTS | `noCallTo[Ev]` | 4 | 2 | Cipher.crysl:94 | **B/cód** | é *safety*: a ocorrência do símbolo proibido é observável; os argumentos são símbolos do ORDER, não expressões de valor |
| 28 | CONSTRAINTS | `callTo[Ev]` | 1 | 1 | Cipher.crysl:116 | **NM** | obrigação (*liveness*): exige detectar ausência futura — perda P4; o evento `IV` nem aparece no ORDER, existe só para o predicado |
| 29 | CONSTRAINTS | `length[x]` | 16 | 11 | Cipher.crysl:122 | **B/cód** | `x.length` em runtime |
| 30 | CONSTRAINTS | `elements(x) in {...}` | 10 | 2 | SSLEngine.crysl:18 | **B/cód** | laço sobre o array no handler |
| 31 | CONSTRAINTS | notação `1^2048` | 4 | 2 | DHParameterSpec.crysl:17 | **B/cód** | comparação de `BigInteger` mapeia; a cláusula upstream em si é suspeita (achado U4, §7) |
| 32 | REQUIRES | cláusulas REQUIRES (total; inclui as linhas 33–34) | 57 | 30 | AlgorithmParameterGenerator.crysl:32 | **B** | leitura no `PredicateStore` |
| 33 | REQUIRES | condicional `constraint => pred[...]` | 13 | 4 | AlgorithmParameters.crysl:35 | **B/cód** | guarda + leitura no store |
| 34 | REQUIRES | negado `!pred[...]` | 3 | 2 | Cipher.crysl:137 | **B** | ausência no store |
| 35 | REQUIRES | wildcard `_` | 6 | 4 | KeyFactory.crysl:27 | **B** | posição ignorada na consulta |
| 36 | REQUIRES | `alg(...)` como argumento | 2 | 1 | Cipher.crysl:134 | **B/cód** | o split da linha 21 aplicado ao argumento |
| 37 | ENSURES | predicado com `after Ev` | 33 | 17 | AlgorithmParameterGenerator.crysl:35 | **B** | `put` no handler do evento — posicionamento determinado pela cláusula; dois mecanismos de realização: alias de estado (`ere` gera só um alias `match` — parcial) ou corpo do handler (geral) |
| 38 | ENSURES | predicado **sem** `after` | 43 | 35 | CertificateFactory.crysl:31 | **HEU** | a semântica default obriga o tradutor a escolher o evento de ancoragem — é exatamente a fiação da gh105 |
| 39 | ENSURES/NEGATES | `this` como argumento | 36+2 | 35+2 | AlgorithmParameters.crysl:43 | **B** | o parâmetro da spec |
| 40 | ENSURES | wildcard `_` | 5 | 5 | KeyPair.crysl:27 | **B** | posição livre no store |
| 41 | NEGATES | predicado `after Ev` | 2 | 2 | PBEKeySpec.crysl:35 | **B** | remoção no store ancorada no handler |
| 42 | FORBIDDEN | com alternativa `=> Ev` | 3 | 2 | PBEKeySpec.crysl:10 | **B** | pointcut na assinatura proibida + acusação imediata; a alternativa é diagnóstico |
| 43 | FORBIDDEN | sem alternativa | 2 | 2 | DigestInputStream.crysl:11 | **B** | idem |

**Somatório (42 construções com ocorrência; a linha 11 tem occ 0):** BIJETIVO **24** · BIJETIVO via código **11** · SOBRE-APROXIMA **1** · HEURÍSTICO **2** · NÃO MAPEIA **4**. As 4 sem imagem somam 12 ocorrências textuais (7 `neverTypeOf` + 4 `notHardCoded` + 1 `callTo`) mais o alcance estrutural da linha 18, que não tem occ pontual: as **28 regras** com sequência no ORDER têm todo prefixo próprio vivo indetectável.

## 4. A matriz MOP → CrySL

Corpora: 24 specs de `jca_android` + 23 de `jca`, lidas na íntegra. Regra de contagem: casamentos de expressão regular sobre o fonte com comentários removidos; pares `jca_android / jca`; **números do commit `5fbe8173`**. Quadro: 134/134 eventos · `after` 109/116 · `before` 25/18 · `returning` 71/81 · `call(` 140/144 · `args(` 94/90 · `target(` 77/65 · `condition(` 31/64 · `ere` 19/18 · `fsm` 5/5 · `alias` 9/5 · `@fail` 21/21 · `@match*` 25/21 · `__RESET` 20/20 · `addError` 112/50 · verbos do substrato novo: `ensure` 31, `validate` 33, `validateAbsent` 5, `negate` 1.

| # | Construção JavaMOP | Occ (and./jca) | Exemplo (@5fbe8173) | Estatuto | Motivo / imagem CrySL |
|---|---|---|---|---|---|
| 1 | declaração de spec, 1 parâmetro | 22/21 | jca_android/CipherSpec.mop:28 | **B** | `SPEC <FQN>` + `OBJECTS`; pareamento pelo tipo do parâmetro |
| 2 | declaração 0 parâmetros (monitor global) | 2/2 | CipherInputStreamSpec.mop:10 | **HEU** | pareia pelo tipo do pointcut; monitor global não é typestate por objeto — streams intercalados podem falhar um autômato que cada objeto satisfaz |
| 3 | declaração N≥2 parâmetros | 0/0 | — | **NM** | `SPEC` do CrySL é unário; custo zero neste corpus (no `generic`: 93/118) |
| 4 | `package`/`import` (resolução de FQN) | 177/137 | CipherSpec.mop:3-15 | **B** | determina FQNs; exige classpath, mas é determinístico |
| 5 | classe-constraint externa (`import static`) | 1/1 | CipherSpec.mop:16-17,:66 | **HEU** | transcreve a CONSTRAINTS composta numa classe Java (@5fbe8173, `Api30CipherTransformationUtil`); auditável só lendo a classe |
| 6 | helper de relatório `q(String)` | 13/0 arqs | KeyGeneratorSpec.mop | **NM** (perda nula) | envelope de relatório (gh104); não traduz cláusula |
| 7 | helper de constraint `validate(int)` | 1/1 | KeyPairGeneratorSpec.mop | **HEU** | transcreve `alg in {..} => keysize in {..}`; extração exige reconhecer o idioma |
| 8 | campos de monitor (staging p/ handler) | ~30/~25 | MacSpec.mop | **HEU** | mecânica do acceptance point (imagem: `ENSURES … after L`); o campo em si não tem seção CrySL |
| 9 | `event … before/after [returning]` | 134/134 | KeyGeneratorSpec.mop | **B** no rótulo | `EVENTS`; o tempo do advice não tem imagem (T4, §5): `after` é after-finally e roda em chamada que lança |
| 10 | pointcut `call(assinatura)` | 140/144 | IvParameterSpec.mop | **B** | evento CrySL = chamada nomeada; zero `execution`/`within`/`cflow`/`this(` nos dois corpora |
| 11 | `target(v)` | 77/65 | SignatureSpec.mop | **B** | o objeto do `SPEC` |
| 12 | `args(v…)` | 94/90 | PBEKeySpecSpec.mop | **B** | os parâmetros do evento |
| 13 | `..` (agregação de sobrecargas) | 18/18 | CipherSpec.mop (`init(int, Key,..)`) | **SOBRE** | um símbolo MOP ↦ N eventos da regra; a expansão 1:N é declarável, mas a distinção da regra se apaga |
| 14 | `*` em `args` | 12/3 | IvChainJunction.mop | **B** | é o `_` do CrySL |
| 15 | `Tipo+` (subtipo) | 3/3 | CipherSpec.mop (`Object+`) | **HEU** | corresponde ao `_` de `getInstance(alg, _)`; a correspondência é política, não dedução |
| 16 | disjunção `call() \|\| call()` num evento | 6/10 | KeyManagerFactorySpec.mop | **SOBRE** | funde `i1`/`i2` da regra num símbolo; a discriminação volta por tipo em runtime — e `null` não tem tipo |
| 17 | `condition(…)` transcrevendo CONSTRAINTS | 28/~25 | KeyGeneratorSpec.mop; DHGenParameterSpecSpec.mop | **SUB** | o conteúdo é a cláusula; a **posição** não: a guarda compila para `if (!(cond)) return false;` antes da transição (`RawMonitor.java:135-142`) — violação vira silêncio ou acusação de ordem errada (T2, §5) |
| 18 | `condition(…)` com leitura de predicado | 0/~20 | jca/GCMParameterSpecSpec.mop | **SUB** | a imagem certa é `REQUIRES`, mas REQUIRES falho não é falha de typestate; o `jca_android` moveu todas para o corpo — no `jca` congelado a supressão está viva |
| 19 | `condition(…)` sobre estado do monitor | 2/3 | KeyGeneratorSpec.mop; MessageDigestSpec.mop | **NM** | guarda com memória entre eventos é inexprimível na regra |
| 20 | gêmeo negado / acusador fora do autômato | 0/~15 ev. | jca/IvParameterSpec.mop:42-56 | **HEU** (defeito conhecido) | a mesma cláusula lida pelo avesso; o efeito colateral produz acusações de ordem sem contraparte na regra — removido no `jca_android` |
| 21 | `addError(ErrorDescription(...))` | 112/50 | CipherSpec.mop | **HEU** | a taxonomia `ErrorType` ↔ classe de erro CrySL é convenção (`codes.csv`); um código nomeia um sítio, não uma cláusula |
| 22 | `PredicateStore.ensure(...)` | 31/0 | IvParameterSpec.mop | **B** | `ENSURES` na aridade da regra; `@match` = estado aceitante, `@matchN` = `after L` |
| 23 | `PredicateStore.validate(...)` (3-valorado) | 33/0 | IvParameterSpec.mop | **B** (n:1 nos códigos) | `REQUIRES`; VIOLATED × NOT_OBSERVED é refinamento sem contraparte — perda de granularidade, não de correção |
| 24 | `validateAbsent(...)` | 5/0 | CipherSpec.mop | **B** | o `!pred[…]` |
| 25 | `negate(...)` | 1/0 | PBEKeySpecSpec.mop | **B** | a única NEGATES real do conjunto |
| 26 | substrato A (`ExecutionContext.setProperty/validate/remove`) | 0/49+27+9 | jca/CipherSpec.mop | **HEU** | mapeia ENSURES/REQUIRES/NEGATES em aridade 1 chaveado por `equals`, onde a regra tem aridade 2 e o substrato novo usa identidade; o extrator precisa ler os dois dialetos — a literatura publicada mora no `jca` |
| 27 | `remove` dentro de `@fail` (withdraw-on-fail) | 0/6 sítios | jca/KeyGeneratorSpec.mop | **NM** | semântica sem geração CrySL (INV-INS-142); apagada no `jca_android` |
| 28 | `set/unsetObjectAsInAcceptingState` | 0/25+6 | jca/CipherSpec.mop | **NM** | bookkeeping sem leitor (INV-INS-147) |
| 29 | `ere : …` | 19/18 | SignatureSpec.mop | **B** | `ORDER` como linguagem regular; determinização obrigatória por correção |
| 30 | `fsm : …` (estados nomeados) | 5/5 | CipherSpec.mop | **B** | idem; estados-pia extras são divergência de instância, não do formalismo |
| 31 | `alias matchN = estado` | 9/5 | CipherSpec.mop | **B** | traduz `ENSURES … after L`; limitação real: `ere` gera um só alias `match` — o `speccedKey after c1` de PBEKeySpec ficou no corpo do evento, com a razão registrada (SUB pontual) |
| 32 | absorção de acusadores no autômato (Kleene) | 4 arqs | PBEKeySpecSpec.mop; SecureRandomSpec.mop | **HEU** | o símbolo absorvido não é evento do ORDER da regra; a comparação exige apagá-lo declaradamente (`ORDER-unmapped`) |
| 33 | handler `@fail` | 21/21 | CipherInputStreamSpec.mop | **B** parcial | violação de ordem = TypestateError; não cobre fim de vida (P1) |
| 34 | handlers `@match`/`@matchN` | 25/21 | SecureRandomSpec.mop | **B** | estado aceitante / acceptance points |
| 35 | `__RESET` | 20/20 | CipherInputStreamSpec.mop | **NM** | CrySL não tem "re-armar após a violação"; `__RESET` ↦ `this.reset()` no gerador. Os 2 `@fail` sem `__RESET`: `KeyPairGeneratorSpec`, nos dois conjuntos |
| 36 | `__LOC`/`__EVENTNAME` | 112+112/50+0 | CipherInputStreamSpec.mop | **NM** (perda nula) | localização/nome no relatório |

**Somatório (36 construções com ocorrência):** BIJETIVO **16** · SOBRE-APROXIMA **3** (13, 16, e a igualdade injetada por alias — ver nota) · SUB-APROXIMA **2** (17, 18) · HEURÍSTICO **9** · NÃO MAPEIA **6** (das quais 3 com perda nula: 6, 36, e 35 — este só importa para re-observação pós-violação).

**Nota sobre a igualdade injetada:** @`5fbe8173`, a `ConscryptAliasTable` tem **158 entradas em `ROWS`** (= as 158 linhas de dados de `data/jca_android/alias_table.csv` — classe e CSV concordam), com `matches/canonical` invocado em 38 sítios de 10 arquivos. Uma allow-list textualmente idêntica à regra é, com a tabela, mais permissiva que ela — um extrator literal diria "conforme". Para o tradutor mecânico da gh106, isso é **divergência a acusar**; a adjudicação é do corpus (§0). *(No worktree em que a gh105 trabalha, a tabela já está em 169 entradas — qualquer número publicado precisa dizer o commit.)*

## 5. As perdas — e a redação para *Threats to Validity*

Perdas por direção do erro. Sobre- e sub-aproximações erram em direções opostas e não se somam.

**P1 — Fim de vida do objeto (`IncompleteOperationError`).** Raiz: formalismo — JavaMOP tem `@fail` (transição inválida) e `@match` (aceitação) e nenhum evento de fim de traço; um prefixo próprio vivo de palavra aceita nunca dispara nada. Alcance: estruturalmente, as 28/49 regras com sequência no ORDER; dinamicamente, medido por execução em 24/08/2026 — as duas specs de *stream* calam sobre o traço que os próprios autores rotulam `# violating branch`, nos dois conjuntos, com controles negativos provando os monitores vivos. Direção: **sub-aproximação** (falso negativo). Solução: não há no monitor dinâmico puro; um gancho de fim de vida seria mudança comportamental, fora desta linha. *Redação sugerida:* "Our runtime monitors cannot express CrySL's `IncompleteOperationError`: JavaMOP raises verdicts on invalid transitions or acceptance, never at end-of-trace. Objects abandoned mid-protocol — the canonical misuse the static analyser flags — are invisible to the dynamic monitor by construction. This loss affects all 28 rules whose ORDER prescribes a sequence, errs exclusively toward silence (false negatives), and was confirmed empirically: both stream specifications remain silent on the authors' own violating trace while negative controls prove the monitors live."

**P2 — `neverTypeOf[x, T]`** (7 occ, 5 regras). Raiz: substrato dinâmico×estático — propriedade do tipo estático da origem; na fronteira da chamada o valor já é `char[]`. Direção: sub-aproximação (nunca acusa). Sem tradução fiel; a checagem pertence à análise estática. *Redação:* "CrySL's `neverTypeOf` constrains the static type of a value's origin (e.g., passwords must never originate from `String`). At the call boundary observed by a runtime monitor the value has already been converted; the property is unobservable dynamically. The 7 occurrences across 5 rules are declared untranslatable and err toward silence."

**P3 — `notHardCoded[x]`** (4 occ, 4 regras). Raiz: substrato — constância literal é propriedade do código-fonte. Direção: sub-aproximação. Mesma redação de P2, mutatis mutandis.

**P4 — `callTo[Ev]`** (1 occ, `Cipher.crysl:116`). Raiz: formalismo — obrigação de chamada futura é *liveness* sem fim de traço, mesma raiz de P1. A assimetria importa: **`noCallTo` (4 occ) mapeia**, porque proibição é *safety*. *Redação:* "Of CrySL's two call-predicates, `noCallTo` (a safety property — the forbidden call is observable when it happens) translates faithfully; `callTo` (a liveness obligation — the required call's absence is only decidable at end-of-trace) does not, for the same reason as `IncompleteOperationError`. One occurrence in the corpus."

**P5 — dialeto do `jca` congelado.** O `jca` usa três idiomas sem imagem CrySL que o `jca_android` já não usa: *withdraw-on-fail* (`remove` em `@fail`, 6 sítios em 4 specs), *accepting-state bookkeeping* (25+6 sítios) e o *gêmeo negado* (acusador fora do autômato, ~15 eventos). Na leitura do `jca` congelado o tradutor declara divergência, não traduz. Direção: mista, declarada caso a caso.

**Ressalvas transversais (não são perdas de tradução, mas erram em direção conhecida se ignoradas):**

- **T1 — O alfabeto não é disjunto.** Uma chamada pode casar dois pointcuts e emitir duas letras (conferido: o pointcut de `use` contém a assinatura exata de `useRandomSpec` no `IvChainJunction`). Consequência para o componente: `Map<Label, Set<Signature>>` está proibido; o objeto de comparação é o morfismo inverso `h⁻¹(L)`.
- **T2 — A guarda mora a montante das tabelas.** `condition(...)` compila para `if (!(cond)) return false;` antes da transição (`RawMonitor.java:135-142`, conferido no gerador): o autômato efetivo é `⟨tabelas, guardas, ordem de fusão de advice⟩` e nenhuma métrica estrutural o vê inteiro. Para o tradutor: `condition` ≠ `CONSTRAINTS` em posição.
- **T3 — Parâmetro múltiplo.** CrySL nomeia um tipo em `SPEC`; JavaMOP fatia sobre tupla. Custo **zero** no corpus do componente (0 de 24, medido); 93 de 118 no `generic`.
- **T4 — Tempo do advice.** CrySL não distingue `before`/`after`, e o `after` do AspectJ é after-finally (roda em chamada que lança). Nota de método; sem solução.
- **T5 — Ancoragem de `ENSURES` sem `after`** (43 occ, 35 regras): a semântica default obriga o tradutor a escolher o evento do `put` — heurística declarável, e exatamente o trabalho de fiação da gh105.

## 6. Componentes e adapters — perguntas 5 e 6

**Estamos usando os componentes certos? Sim.** Confirmado na fonte: `SpecExtractor.parse(File)` lê `.mop` (`javamop/src/main/java/javamop/parser/SpecExtractor.java:23-36`; não chama `MOPNameSpace.init()` — a armadilha nº 2 é real); `MOPSpecFile` tem construtor público e `DumpVisitor` (1.670 linhas, com `RVDumpVisitor` como precedente de extensão) re-emite — a rota `SpecModel → MOPSpecFile → DumpVisitor`, nunca texto à mão, está sustentada pela API. `CrySLModelReader.readRule(File)` lê `.crysl` (leitor novo por regra, obrigatório). As **sete armadilhas do parser** do plano §7 estão todas carregadas pela change (`spec.md:104`, G01 1.3(a)–(g)) e todas conferidas na fonte javamop.

**Mas a fachada `CrySLRule` não basta sozinha.** Verificado por `javap` no jar 4.0.6: a fachada não expõe (i) nomes de evento CrySL (`TransitionEdge.getLabel()` devolve `Collection<CrySLMethod>`, que constrói assinaturas, não rótulos), (ii) agregados (já compilados em arestas), (iii) posição `arquivo:linha` (nenhum método de posição em `crysl.rule.*`). Os três só saem pela rota EMF (`CrySLStandaloneSetup` → `XtextResourceSet` → `ClasspathTypeProvider`; posições via `NodeModelUtils`), que **não aparece em nenhum artefato da change** (grep: único hit é a menção "(Xtext/EMF)" em `design.md:10`). Três sítios da change dependem dela sem dizê-lo: G02 2.5 (`resource.getErrors()`), G02 2.6 ("automaton over the rule's event names, preserve aggregate names" — que também conflita com `design.md:229`/INV-CONF-03, "over Signature, not Label") e `spec.md:79` (procedência `file:line` por item, sem mecanismo declarado em lado nenhum — no lado MOP a saída é a varredura de texto paralela do plano §11.3, porque `getBeginLine()` devolve 0/1). **A reescrita da Fase 4 precisa ou descer G02 2.6 para assinaturas, ou declarar a rota EMF como via de relatório.**

**A arquitetura de adapters está certa? Sim.** O padrão "converter cada modelo nativo para o canônico e emitir pelo writer existente" está escrito (`design.md:274` "Never StringBuilder", `spec.md:330`, G11 11.1) e realizado pela decomposição por tecnologia (`-core`/`-mop`/`-crysl`, D-16 fixando que o `-core` não conhece parser nenhum). Observação de forma: o princípio do writer não tem decisão D-xx numerada própria.

**`crysl.lower` (emitir `.crysl`) continua fora de escopo — e o argumento ficou mais forte com a virada.** O `CrySLSemanticSequencer` existe e está ligado no runtime module, mas o projeto CrySL não tem formatter (zero classes; saída em uma linha), e os dois consumidores concebíveis de `.crysl` gerado morreram: o corpus gerado à la `api30` saiu com o MetaCrySL, e regras adaptadas legíveis para humanos não são produto da gh106 (tradução mecânica; §0). A direção MOP→CrySL precisa só do **modelo**. Manter D-14/non-goal.

## 7. Achados colaterais — registrar, não corrigir

**No corpus upstream** (bugs do próprio upstream; a tradução fiel os propagaria — "parseou" não é oráculo):

- **U1** — `SSLEngine.crysl:11-12`: evento declarado `ep1`, agregado escrito `EnableProtocol := cp1;` — não parseia.
- **U2** — `OAEPParameterSpec.crysl:8`: objeto chamado `alg`, palavra reservada da gramática 4.x — não parseia.
- **U3** — `KeyAgreement.crysl:17,30-31`: `GenSecretBuffer := gs1 | g2;` onde `g2` é `getInstance(algorithm, _)` — quase certamente typo por `gs2` (que fica órfão). Parseia; o agregado está semanticamente errado.
- **U4** — `DHParameterSpec.crysl:17-18` e `DSAParameterSpec.crysl:16-17`: `p >= 1^2048` — se `^` é potência, a cláusula é vácua (`1^2048 = 1`); a intenção evidente era módulo de 2048 bits.
- **U5** — `KeyAgreement.crysl:34,37,41`: `GenSecret` definido e ausente do ORDER; `gs3` só existe como alvo de `noCallTo` — mesmo padrão do `IV` de `Cipher.crysl`.

**No corpus MOP** (@`5fbe8173`):

- **Nome de arquivo ≠ nome de spec em 5 arquivos** (não 1): `jca_android/IvParameterSpec.mop` e `jca/IvParameterSpec.mop` → `IvParameterSpecSpec`; `jca_android/IvChainJunction.mop` → `IvChainJunctionSpec`; `jca_android/RandomStringPassword.mop` e `jca/RandomStringPassword.mop` → `RandomStringPasswordSpec`. Ferramenta que derive o nome da spec do arquivo erra silenciosamente nos 5. Classe vizinha: `SecretKeySpec.mop` declara `SecretKeySpec(SecretKey …)` — só o tipo do parâmetro desambigua.
- **Cabeçalhos errados:** `PBEParameterSpecSpec.mop` intitula-se "GCMParameterSpec" nos dois conjuntos; `jca/TrustManagerFactorySpec.mop` intitula-se "KeyManagerFactory".
- **Defeitos do `jca` congelado, conferidos na fonte:** `GCMParameterSpecSpec` com dois eventos `c1` e `ere : c1 | c2` de `c2` fantasma; `SecretKeySpecSpec` com parêntese desbalanceado (52×53); `SignatureSpec` com tipos de retorno errados nos pointcuts de `sign` (pointcut sem casamento possível; corrigido no `jca_android`); `KeyPairSpec` com campo sombreando o parâmetro da spec e `gpr` escrevendo `GENERATED_PUBLIC_KEY` para a chave privada (reparado no `jca_android`); `KeyGeneratorSpec` com `Key` sem import.
- **O cenário dos dois substratos da change cita idioma inexistente:** `spec.md:113-114` e G01 1.12 afirmam `Property.MACED` de aridade 1 em `jca/MacSpec.mop` — o arquivo @`5fbe8173` não contém `MACED` (escreve `GENERATED_MAC`); o idioma citado existe em `jca_android_bug_predicate/MacSpec.mop:40`. Corrigir na Fase 4.
- `MultiSpec_1MonitorAspect.aj` (71 KB, gerado) está no diretório de specs do `jca` **no disco**, ignorado pelo git (`rvsec-mop/.gitignore`) e ausente da árvore @`5fbe8173` — censos por git nunca o veem; censos por disco sim.

## 8. NÃO-VERIFICADO (consolidado das seis passagens)

| Item | Motivo |
|---|---|
| `generic` 93/118 multi-parâmetro | decidido na adjudicação externa §1.1; não re-medido nesta rodada |
| "9 de 11 allow-lists idênticas são mais permissivas" | pertencia à frente de adaptações Android, retirada do escopo da gh106 pelo pesquisador; o mecanismo (`matches()` + tabela) foi conferido, a fração não |
| Execução do arnês gh104 (streams calam no traço violador) | medição de 24/08 aceita; não re-executada |
| Determinização como *no-op* nas 47 regras upstream | só medida no `api30`; vira medição nova (G03 3.10 retargetada) |
| Diff jdk×android e `ApiCheck` 175/29/5/6 da §2.4 | medidos uma vez (subagente F); o verificador re-executou só o modo `jdk` |
| `BaseMonitor.java` e a topologia completa "antes do `handleEvent`" | conferido só `RawMonitor.java:135-142` — suficiente para "guarda antecede transição" |
| HEADs de `rvsec-cognicrypt`/`MetaCrySL` na emissão do handoff | o handoff só carimba o `rvsec`; os três foram carimbados hoje |
| Se as 2 regras que não parseiam entram no denominador de M4 (135 × 132) | decisão da change; o precedente do `api30` diz que entram |
| Os nomes "21 regras pareadas" (README do dado) × "22 pares" (change) | ambos textuais; 55 cláusulas são compatíveis com os dois (três pareadas têm 0 cláusulas); a regra de conversão precisa ser declarada na Fase 4 |
| Células das matrizes fora das amostras adversariais (OBJECTS 233; construtores 43/30; retornos 38/20; wildcard EVENTS 28/19; arrays) | amostra de 17+16 células sem nenhuma falha; as demais não recontadas |
