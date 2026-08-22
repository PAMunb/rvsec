# Validações V1–V10 — resultados brutos (sessão 2026-08-21)

## V1 — MOPSpecFile do zero pelo DumpVisitor  ✅ PASSA
Arnês: `v1/V1.java` (mínimo) e `v1/V1c.java` (completo).
- Montado à mão: pacote, 4 imports, 1 campo, 1 `creation event` com `args()`+`condition()`,
  `ere`, `@fail` e `@match`. Dump 1/1, reparse 1/1, semântica preservada
  (`creation=true`, `condition=[exponentSize < primeSize]`, `handlers=[fail, match]`).
- **O emissor não constrói AST de AspectJ**: o construtor de `EventDefinition` recebe o pointcut
  como *string* e o parseia sozinho (`parsePointCut`). Idem blocos Java — `new JavaMOPParser(is).Block()`.
- Corpos e declarações saem de re-parse de texto: `Block()` para `@fail`/`@match` e corpo de evento;
  `ClassOrInterfaceBodyDeclaration(false)` para campos.
- **Armadilha**: `ClassOrInterfaceBody(boolean)` **não** consome chaves. Passar `{ T x; }` produz um
  *initializer estático* contendo uma variável local, não um campo — e reparseia calado.
- Não-idempotência é cosmética: `ere: ` (dump 1) vs `ere:  ` + linha em branco (dump 2).
- Defeitos de formatação do `DumpVisitor` (cosméticos): `)returning(`, `:call(`, `){` sem espaço.

**Consequência**: §12 mantém-se — o emissor mora ao lado do leitor, mas por razão mais fraca do que
§11.1 supunha: o que exige os tipos do `javamop` é o `MOPSpecFile`/`EventDefinition`, não o pointcut.

## V9 — dois achados de subagente
### V9a `CipherTransformationUtil.mode("AES/")` — **defeito CONFIRMADO, alcance REFUTADO**
- Execução (`v9/V9b.java`): `mode("AES/")`, `mode("AES//")`, `mode("RSA/")` lançam
  `ArrayIndexOutOfBoundsException: Index 1 out of bounds for length 1`.
- **Mais largo que o relatado**: `alg("/")` também lança (`Index 0 out of bounds for length 0`), e as
  três utilitárias caem juntas — `CipherTransformationUtil.isValid`, `Api30CipherTransformationUtil.isValid`
  (que delega o parsing à primeira) e, por herança do mesmo parsing, a arquivada.
- **Mas o caminho pela JCA está fechado** (`v9/V9c.java`): `Cipher.getInstance` rejeita todas as
  formas com barra final *antes* de retornar — `NoSuchAlgorithmException: Invalid transformation format`.
  Todo sítio de `isValid` nas specs (`jca` e `jca_android`) recebe uma transformação que já
  sobreviveu ao `getInstance`, seja por `args(transformation)` num `after … returning`, seja por
  `c.getAlgorithm()` sobre um `Cipher` obtido. Logo o AIOOBE é **latente**, não um crash vivo.
- Veredito: vale a guarda de duas linhas; não vale conserto de emergência. §9 deve ser corrigido —
  "alcançável de `isValid`" é verdade do grafo de chamadas e falso da entrada.

## V3 — CrySLParser com o android.jar da API 30  ⚠️ FALSEIA A VIA, MAS SEM IMPACTO MEDIDO
Arnês: `v3/V3.java`, `v3/ApiCheck.java`; corpus normalizado em `api30_norm/`.
- **A normalização léxica tem 5 substituições, não 4**: `FORBIDDEN:`→`FORBIDDEN`, `;;`→`;`,
  `alg`→`algName`, `neverTypeOf/noCallTo/callTo/notHardCoded (…)`→`[…]`, e **`length(…)`→`length[…]`**.
  Com as cinco: **31/33** parseiam (§8 media 30/33).
- As residuais são **três** (corrigido em 22/08/2026, R5): `AlgorithmParameters:47` (predicado dentro
  de `CONSTRAINTS`), `DigestOutputStream:20` (`on(java.lang.String)` inexistente) e `Signature:51`
  (`offset`/`len` fora de `OBJECTS`) — a terceira só sumia por vazamento de escopo, ver abaixo.
- **CORREÇÃO a §9 — ~~o parser infere os tipos~~. REFUTADA em 22/08/2026 (R5).** O parser **não
  infere nada**: `Signature.crysl` carregou porque `GCMParameterSpec`, `IvParameterSpec` ou `Mac` —
  as três únicas regras do corpus que declaram **ambos** `int offset;` e `int len;` — foram lidas
  antes no mesmo leitor e vazaram as declarações. Com leitor novo por regra, `Signature` **falha**, e
  `Signature.cryptsl:51` é defeito real da regra (o CrySL oficial declara os dois em `OBJECTS`).
  Consequência: as residuais são **três**, não duas, e o corpus carrega **30/33**, não 31/33.
- **O classpath virtual é estritamente aditivo.** `getClassPath()` (bytecode) devolve
  `HashSet(javaRuntimeClassPath ∪ virtualClassPath)`; e a resolução passa por delegação
  parent-first, então a JDK vence qualquer nome que ela tenha.
  - Sonda A: `android.util.Base64.encodeToString` — **não** resolve sem o jar, **resolve** com ele.
  - Sonda B: `java.util.HexFormat.formatHex` (JDK 17, ausente do android.jar da API 30) — **resolve
    nos dois modos**. Mirar a API 30 é impossível pelo construtor virtual.
  - A via (b) do handoff — "JVM cujo classpath de aplicação contenha só o android.jar" — **também
    não funciona**, e por razão de princípio: `java.base` não vem do `java.class.path`, vem da camada
    de módulos, e o `URLClassLoader` do provedor de tipos delega ao pai.
  - A não-determinação do `HashSet` é irrelevante: quem decide é a delegação, não a ordem.
- **Impacto medido: zero.** Os 31 arquivos produzem 129 linhas de assinatura resolvida **idênticas**
  com e sem o android.jar (`diff` = 0).
- **Desenho alternativo, barato**: em vez de forkar o CrySL, validar *a posteriori* cada assinatura
  resolvida contra o `android.jar`. Medido em 155 eventos: 131 casam assinatura exata, 19 casam só
  por aridade (apagamento de genéricos e `AnyType` — benignos), 2 são limitação do conferidor
  (`SecretKey.destroy/getEncoded`, herdados de `Destroyable`/`Key`), e **3 são reais**:
  - **ACHADO NOVO** `java.security.spec.DSAGenParameterSpec` **não existe na API 30** (aparece só na 35).
  - **ACHADO NOVO** `javax.xml.crypto.dsig.spec.HMACParameterSpec` **não existe em nenhum nível**
    de API Android verificado (26, 30, 33, 35) — o pacote `javax.xml.crypto` inteiro está ausente.
    E `jca_android/HMACParameterSpecSpec.mop` monitora exatamente essa classe: é uma das 23 specs do
    conjunto, **morta por construção** no Android. Explica de outro ângulo o "0/1 parâmetro ligado"
    do §9.

## V4 — determinizar o `StateMachineGraph` e refazer os vereditos do §5.2  ✅ VEREDITOS CONFIRMADOS
Arnês: `v4/Dump.java`, `v4/ScanND.java`, núcleo `m2/Aut.java` + `m2/M2.java`, mapas em `maps/*.map`.

**A NFA de Glushkov é real, e nenhuma regra do corpus a exibe.**
- Sintética `ORDER con, a?, a` → duas arestas `append` do nó 0 para 1 e 2. Confirmado.
  Idem `con, (a,t)|(a,a)`.
- **Varredura das 31 regras `api30` que carregam: 31 determinísticas, 0 não-determinísticas.**
  A determinização é obrigatória por correção geral e é *no-op* neste corpus.
- `wrapUpCreation()` precisa mesmo ser chamado à mão: `getHopsToAccepting()` do nó inicial é
  `2147483647` antes e o valor certo depois. Confirmado em 5 regras.

**Os quatro vereditos, agora sobre o autômato que o parser entrega:**

| Spec | §5.2 dizia | V4 mediu (sem N1) | V4 mediu (com N1) |
|---|---|---|---|
| `MessageDigestSpec` | EQUIVALENTES | **EQUIVALENTES** | EQUIVALENTES |
| `SignatureSpec` | EQUIVALENTES | **EQUIVALENTES** | EQUIVALENTES |
| `KeyGeneratorSpec` | EQUIVALENTES | MOP mais permissiva (`g1 g1 gk1`) | **EQUIVALENTES** |
| `SecureRandomSpec` | MOP mais permissiva | MOP mais permissiva (`c1 c1`) | **MOP mais permissiva** — testemunha idêntica à do §5.2: `SecureRandom(); generateSeed(int); setSeed(byte[])` |
| `CipherSpec` | INCOMPARÁVEIS | **INCOMPARÁVEIS** | INCOMPARÁVEIS — testemunhas **idênticas** às do §5.2: `g1 i2 doFinal()` e `g1 i2 i2 doFinal(byte[])` |

**CORREÇÃO a §13**: "se N1 cair, **dois** dos três vereditos de equivalência voltam a *mais
permissiva*" está errado — cai **um só**, o `KeyGeneratorSpec`. `MessageDigestSpec` e `SignatureSpec`
são equivalentes com ou sem N1, porque as suas ERE já trazem um único evento criador na cabeça
(`(g4* g1 | g4* g2 | g4* g3)` e `(g1|g2)`), enquanto a do `KeyGeneratorSpec` traz `g1+`.
Isso **reduz o que V8 decide**: V8 decide o veredito de uma spec, não de duas.

**Confirmação do §9 sobre o `order_alphabet_map.csv`**: `CipherSpec.f2` mapeia mesmo `{f1,f2,f4}` —
o pointcut é `public byte[] Cipher.doFinal(..)`, e as sobrecargas que devolvem `byte[]` são
`doFinal()`, `doFinal(byte[])` e `doFinal(byte[],int,int)`. Foi assim que a testemunha
`g1 i2 doFinal()` saiu.

## V6 — a costura JSON com os dois classpaths reais  ✅ PASSA
Três processos, nenhum compartilhando JVM: `v6/LiftCrysl.java` (classpath do `CrySLParser` com
Guava 33.5), `v6/LiftMop.java` (classpath do `javamop`), `m2/M2.java` (núcleo, só Gson).
- `LiftCrysl`: 33 regras → `crysl.json` (2 com `error`, as duas conhecidas).
- `LiftMop`: 23 specs → `mop.json`.
- O núcleo compara sem tocar em nenhuma das duas tecnologias. **É o que produziu a tabela do V4.**
- **Nada de essencial se perde na serialização**: o autômato sai como `{start, accepting, edges[]}`
  com as arestas rotuladas por conjunto de assinaturas, mais um campo `deterministic` calculado no
  leitor; os eventos MOP saem com `id`, `pos`, `creation`, pointcut cru, `condition` e as assinaturas
  de `call(...)` extraídas do AST de AspectJ; a `ORDER` sai como `{formalism, text}` e o bloco `fsm`
  chega inteiro, com as linhas `alias matchN = estado`.
- **Ressalva medida**: o texto do `fsm` inclui os `alias`, então o núcleo tem de parseá-los; e o
  `ere` chega com espaçamento cru. Nenhum dos dois é perda — é trabalho de parser no núcleo, que já
  está escrito (`M2.fsm`, `Aut.ere`).

## V5 — preservar os nomes de agregado  ✅ PASSA, e melhor do que o previsto
Arnês: `v5/V5.java`, depois fundido em `v6/LiftCrysl.java`.
As ~10 linhas previstas em §10.2 funcionam fora do jar publicado:
`CrySLStandaloneSetup().createInjectorAndDoEMFRegistration()` → `XtextResourceSet` →
`setClasspathURIContext(new URLClassLoader(cp))` → `new ClasspathTypeProvider(...)` →
`rs.getResource(URI, true)` → `Domainmodel`.
- **33/33 arquivos entregam AST** — inclusive os 2 que a fachada `CrySLParser` rejeita por erro de
  validação. A via AST é estritamente mais permissiva, o que é bom para relatório.
- Recuperados: **167 nomes de evento** e **61 agregados** com membros, em 23 das 33 regras.
  Exemplo `Cipher`: `Gets:=g1|g2`, `IWOIV:=i1|i2|i3|i8`, `IWIV:=i4|i5|i6|i7`, `Inits:=IWOIV|IWIV`,
  `updates:=u1..u5`, `FINWOU:=f2|f4|f5|f6|f7`, `DOFINALS:=FINWOU|f1|f3`.
- **A procedência `arquivo:linha` sai junto**, por `NodeModelUtils.getNode(e).getStartLine()`, e o
  texto cru do `ORDER` também. §11.3 previa isso e está confirmado.

## V7 — o `.mop` gerado atravessa o pipeline inteiro  ✅ PASSA
- `javamop -merge` sobre os 3 gerados → 3 `.rvm` + `MultiSpec_1MonitorAspect.aj`.
- `rv-monitor -merge -d` → `MultiSpec_1RuntimeMonitor.java` com
  `static final int Prop_1_transition_c1[] = {1, 2, 2};` e `Prop_1_transition_c2[]` idem.
- **O monitor gerado compila**: `javac` contra `rvsec-core` + `rv-monitor-rt` + `rvsec-logger-csv`,
  **0 erros, 7 classes**. (`ErrorCollector` mora no `rvsec-logger-csv`, não no `-core`.)

### A pergunta aberta do §13 sobre as duas specs com defeito de sintaxe em `jca` — **RESPONDIDA**
O conjunto `jca` congelado, com os dois defeitos, atravessa o pipeline inteiro **em silêncio**:
23/23 `.rvm`, monitor gerado, e **compila com 0 erros (63 classes)**.
Para `jca/GCMParameterSpecSpec.mop` (dois eventos com id `c1`, `ere : c1 | c2` citando um `c2` que
não existe) o monitor sai assim:
```java
static final int Prop_1_transition_c1[] = {1, 2, 2};;
static final String[] RVM_eventNames = {"c1", "c1"};;
...
int nextstate = this.handleEvent(0, Prop_1_transition_c1);   // primeiro evento c1
int nextstate = this.handleEvent(1, Prop_1_transition_c1);   // segundo evento c1, MESMA tabela
```
O `c2` do `ere` **desaparece do alfabeto sem uma linha de aviso** e não existe
`Prop_1_transition_c2`. Conclusão: nem "parseou" nem "gerou monitor" nem "compilou" é oráculo de
sanidade. O checador de vinte linhas sobre a AST (ids únicos + alfabeto ⊆ ids) é o único que pega.

## V8 — a semântica de fatiamento paramétrico  ✅ N1 CONFIRMADO POR EXECUÇÃO
Tudo na JSE com `ajc` 1.9.25.1 + `rv-monitor-rt` — nenhum emulador envolvido.

**V8a · um monitor por objeto.** Spec sonda `SliceProbeSpec(KeyGenerator k)` com
`creation event g` (`getInstance`), `event gk` (`generateKey`, `target(k)`) e `ere : g gk` — uma ERE
que **rejeita** duas criações. Programa com dois `getInstance` seguidos de dois `generateKey`:
```
[EV] g   monitor=2007328737 kg=340870931
[EV] g   monitor=1830908236 kg=1936628443     <- monitor DIFERENTE
[EV] gk  monitor=2007328737 kg=340870931
[MATCH] monitor=2007328737
[EV] gk  monitor=1830908236 kg=1936628443
[MATCH] monitor=1830908236
```
Dois objetos, dois monitores, cada um vendo exatamente um evento criador. **Zero `@fail`.** Se o
monitor fosse global, o segundo `g` teria levado ao estado de falha. **N1 vale.**

**V8b · dois eventos no mesmo join point co-disparam.** Spec com `g` e `h` sobre o *mesmo* pointcut,
`ere : g h gk`. Um único `getInstance`:
```
[EV] g  monitor=2007328737 kg=340870931
[EV] h  monitor=2007328737 kg=340870931       <- MESMO monitor, mesma ligação
[EV] gk monitor=2007328737 kg=340870931
[MATCH]
```
Confirma o mecanismo: uma chamada concreta emite **todos** os eventos cujo pointcut e guarda casam,
**na ordem de declaração**, no mesmo monitor.

**V8c · CORREÇÃO ao §4.1 — `g1` e `g4` NÃO co-disparam.** Réplica exata da forma do
`MessageDigestSpec` (guarda de `g1` no argumento, guarda de `g4` no campo
`currentAlgorithmInstance`, `g1` declarado antes):
```
=== algoritmo seguro (SHA-256) ===
[EV] g1 monitor=396180261 alg=SHA-256 campoAntes=''      <- so g1
[MATCH]
=== algoritmo inseguro (MD5) ===
[EV] g4 monitor=835648992 alg=MD5 campoAntes=''          <- so g4
[FAIL ]
```
A razão é a ordem: a `condition` compila para `if (!(guarda)) return false;` **dentro** do método do
evento, e o advice de `g1` roda inteiro — guarda **e corpo** — antes de a guarda de `g4` ser
avaliada. Como o corpo de `g1` escreve `currentAlgorithmInstance = alg`, a guarda de `g4`
(`!matches(campo)`) fica **falsa** e `g4` não dispara. Simetricamente, se `g1` recusa, o campo não
muda e só `g4` dispara.
- **Exatamente um dos dois dispara por chamada.** A palavra é `g1` ou `g4`, nunca `g1 g4` nem `g4 g1`.
- §4.1 diz "`g1` e `g4` co-disparam na mesma chamada... uma chamada concreta produz a palavra
  `g4 g1`". Isso está **errado nas duas metades** — não co-disparam, e se co-disparassem a ordem
  seria `g1 g4` (ordem de declaração), que a ERE `(g4* g1 | ...)` **rejeitaria**.
- **A conclusão do §4.1 continua de pé, por razão mais forte**: a testemunha `g1 g1` morre por N1
  (V8a) e o par `g1/g4` é mutuamente exclusivo por construção da guarda (V8c). O veredito
  EQUIVALENTES do `MessageDigestSpec` está confirmado independentemente em V4.

## A pergunta do parâmetro múltiplo — medida
JavaMOP é paramétrico sobre uma **tupla**; CrySL nomeia **um** tipo em `SPEC` e não tem autômato
conjunto sobre um par de objetos. A resposta de CrySL para relação entre dois objetos é **predicado**
(`ENSURES generatedKey[key, algName]`), não ordem conjunta — é a mesma aridade-2 do §5.4 vista pelo
outro lado.

| Conjunto | specs | com >1 parâmetro |
|---|---:|---|
| `jca_android` | 23 | **0** (todas 0 ou 1) |
| `jca` | 23 | **0** |
| `generic_new` | 27 | 4 (2 com dois, 2 com três) |
| `generic` | 118 | **93** (39 com 2, 28 com 3, 18 com 4, 7 com 5, 1 com 6) |

- Na direção **CrySL → MOP** (o gerador) o problema **não existe**: `SPEC` nomeia um tipo, logo a
  spec gerada tem sempre um parâmetro. É até uma propriedade boa — o gerador não consegue cometer o
  defeito das 6 de 21 specs com fatiamento quebrado.
- Na direção **MOP → CrySL** e no **comparador**, uma spec de k>1 parâmetros não tem imagem em CrySL
  quando a `ORDER` de fato intercala eventos sobre objetos diferentes. A saída certa é **recusa
  tipada** (`Unknown{MultiSlicedOrder, params:[...]}`), nunca achatamento silencioso.
- **Custo medido da restrição no corpus do componente: zero (0/23).** É fronteira de escopo
  declarada, não dívida. Vira dívida real no dia em que apontarem o comparador para o `generic`,
  onde são 93 de 118 — e aí a recusa tipada é o que impede o relatório de mentir.

## V2 — gerar uma spec inteira ponta a ponta  ✅ A VALIDAÇÃO CENTRAL PASSA
Gerador em `v2/Gen.java` (família *parameter-spec*: eventos que são construtores do tipo da `SPEC`).
Emite pelo `MOPSpecFile` + `DumpVisitor`, nunca por concatenação de texto. Três specs geradas de
`api30`, todas reparseiam e atravessam o pipeline (V7).

### As quatro métricas, gerado × gabarito humano `jca_android`

| | DHGenParameterSpecSpec | GCMParameterSpecSpec | PBEParameterSpecSpec |
|---|---|---|---|
| **M1** eventos | 1/1 — id e assinatura idênticos | 2/2 idênticos | 2/2 idênticos |
| **M2** ordem | `c1` × `c1` — **equivalentes** | `(c1\|c2)` × `c1\|c2` — **equivalentes** | idem — **equivalentes** |
| **M3** constraints | 0 no oráculo, **1 no humano** (ver abaixo) | 1/1, mesmo idioma (corpo, não guarda) | 1/1, mesmo idioma |
| **M4** predicados | 1/1 `ensures` | 1 `requires` + 1 `ensures`, **substrato diferente** | idem |

**Total: M1 5/5, M2 3/3, M4 5/5.** M3 é 2/2 sobre o que o oráculo pede.

### As divergências, e o que cada uma significa

1. **ACHADO NOVO — o oráculo `api30` perdeu cláusulas que a regra CrySL original tem.**
   `DHGenParameterSpec.cryptsl` **não tem seção `CONSTRAINTS`**; a regra original
   (`Crypto-API-Rules/.../DHGenParameterSpec.crysl`) tem `exponentSize < primeSize`, e o `.mop`
   humano a implementa. A perda acontece no **template base** (`MetaCrySL/samples/jca/base/`), não
   na geração. São **três regras** afetadas, ~9 cláusulas normativas apagadas:
   | regra | cláusulas na original | no `api30` |
   |---|---|---|
   | `DHGenParameterSpec` | 1 (`exponentSize < primeSize`) | 0 |
   | `DSAGenParameterSpec` | 5 (`primePLen`, `subPrimeQLen` e 3 implicações) | 0 |
   | `IvParameterSpec` | 3 (`length[iv] >= offset+len`, `offset >= 0`, `len > 0`) | 0 |
   Consequência para o §6: o denominador de M3 (62 cláusulas nas 33 regras `api30`) **já é uma
   perda** em relação ao oráculo CrySL. E um `.mop` humano fiel à regra original aparece como
   `MOP-SEM-BASE` quando medido contra o `api30`. Isso é um teto do *oráculo*, um terceiro tipo além
   dos dois do §6.

2. **Substrato — a única divergência de M4, e ela é uma escolha que o gerador tem de receber.**
   O gerado emite `ExecutionContext.setProperty/validate` (binário, um código por leitura); o humano
   de `GCM` e `PBE` já migrou para `PredicateStore.ensure/validate` (três-valorado, **dois** códigos
   por leitura: `VIOLATED` e `NOT_OBSERVED`). Mesma aresta do grafo, expressividade diferente.
   O gerador precisa de um parâmetro de substrato — não é dedutível da regra.

3. **CORREÇÃO ao §10.3 — falta uma política, e o corpus humano já a tem.**
   O humano escreve `boolean conforms = true; … if (conforms) { spec = s; }`: o `ENSURES` **não vale**
   para uma construção que quebrou uma `CONSTRAINTS` ou um `REQUIRES`. A primeira versão do gerador
   gravava o predicado sempre. **O humano está certo** e o §10.3 não nomeia essa política.
   Corrigido no gerador (segunda passada) e é o padrão certo.

4. **Defeito do gerador, corrigido**: não coletava os tipos usados nos pointcuts, então o
   `PBEParameterSpecSpec` gerado saía sem `import java.security.spec.AlgorithmParameterSpec` —
   parseia e não compilaria. Uma linha de correção.

5. **Diferenças que não são divergência**: nome de parâmetro (`tLen` × `tagLen`), literal inline ×
   campo `validLengths`, `creation event` × `event`, parentização redundante do `ere`, e os três
   conjuntos que o humano **deletou** de `GCM` (`offset>=0 && len>=0 && src.length>=offset+len`)
   porque não traduzem cláusula alguma e o construtor já os garante — o gerador não os emite por
   construção, e coincide com o humano.

**Veredito**: os percentuais do §10 deixam de ser previsão para estas três specs. O gerador
reproduz o gabarito humano nas quatro camadas onde o oráculo tem o que dizer; onde diverge, a causa
é nomeável em todos os casos, e em um deles (o §10.3 incompleto) a divergência apontou um defeito no
gerador, não no humano.

## V9a — `getStatesForMethods` com `after <Agregado>`  ✅ DEFEITO CONFIRMADO, ausente do corpus
Arnês: `v9/V9a.java` com duas regras sintéticas.
- Regra sadia (`digested[out] after Gets`, `Gets` no `ORDER`): `NOS=2`.
- Regra doente (`digested[out] after Fora`, `Fora := d2`, e `d2` **não** aparece no `ORDER`):
  **`eventos=1 NOS=0`** — o predicado vale em estado nenhum, a regra carrega sem erro e sem aviso.
- **Precisão a mais que o relato do subagente**: a resolução é **por método, não por nome de
  agregado**. `Sozinho := g1` com `ORDER Gets, d1` (onde `Gets := g1|g2`) resolve normalmente,
  porque o método de `g1` está no autômato. O conjunto só fica vazio quando **nenhum** método do
  agregado aparece no `ORDER`.
- **Alcance no corpus: zero.** As 19 cláusulas `after` das 33 regras `api30` citam, todas, símbolo
  presente no `ORDER`. É risco a detectar e reportar, não defeito vivo.

## ACHADO NOVO — o escopo de `OBJECTS` vaza entre regras no mesmo `CrySLModelReader`
Descoberto ao rodar V4 e reproduzido em três configurações:
| leitura | `Signature.crysl` |
|---|---|
| sozinho, leitor novo | **FALHA** — `Couldn't resolve reference to Object 'offset'` / `'len'` (linhas 51, 59, 65) |
| depois de `MessageDigest.crysl`, mesmo leitor | **FALHA** |
| depois de `GCMParameterSpec.crysl`, mesmo leitor | **CARREGA** |
| diretório inteiro em ordem alfabética | **CARREGA** (3/3 execuções) |

`GCMParameterSpec.crysl` declara `int offset;` e `int len;` em `OBJECTS`, e esses nomes passam a
resolver dentro de `Signature.crysl`, que os usa sem declarar. **O significado de uma regra depende
de quais outras foram lidas antes, no mesmo leitor.** Consequências:
- O leitor do componente tem de ler cada regra num `CrySLModelReader` novo, ou declarar a
  ordem de leitura como parte da configuração — e nesse caso `Signature` não carrega.
- **Isto refina a "não-determinação" do §13**: o `HashSet` do classpath é irrelevante (V3); a
  instabilidade real é o *resource set* do Xtext acumulando escopo entre arquivos.
- E é o que explica o §9: `Signature.cryptsl:51` **não** é uma regra que "não carrega" — é uma regra
  que carrega ou não conforme a companhia.
- **Ampliado em 22/08/2026 (R5): o vazamento corre nos dois sentidos.** `SecretKey.crysl` lido antes
  de `Key.crysl` **quebra** o `Key.crysl`, que sozinho carrega. Sobre 40 ordens aleatórias com leitor
  partilhado o total é `{29:3, 30:15, 31:22}`; com leitor novo é 30, invariante. O conjunto que
  carrega não é função do corpus — e é por isso que "um leitor por regra" se justifica por
  **determinismo**, não por denominador.

## V10 — o módulo mínimo compila no reator  ✅ PASSA
Quatro `pom.xml` do §12 (`rvsec-crysl` pai + `-core`, `-mop`, `-crysl`), uma classe vazia em cada,
montados em `rvsec/rvsec-crysl/` e adicionados a `rvsec/pom.xml`.
```
RVSec CrySL conformance ............................ SUCCESS
RVSec CrySL conformance :: core .................... SUCCESS
RVSec CrySL conformance :: mop ..................... SUCCESS
RVSec CrySL conformance :: crysl ................... SUCCESS
BUILD SUCCESS
```
- **Guava: a sobrescrita funciona como §11.5 previa.** `<guava.version>33.5.0-jre</guava.version>`
  no pom-pai do componente → `guava.version` efetiva = `33.5.0-jre`, e a árvore mostra
  `com.google.guava:guava:jar:33.5.0-jre:compile` nos dois filhos de tecnologia. O
  `dependencyManagement` da raiz é *property-driven*, então a herança segue junto.
- **`slf4j-simple` excluído**: sobra só `org.slf4j:slf4j-api:2.0.17`.
- **Scala**: `rvsec-crysl-mop` recebe `org.scala-lang:scala-library:2.11.12` transitivamente por
  `javamop → rv-monitor → ptltl`, como previsto, e **não atrapalha** — o módulo é Java 21. A
  resolução *nearest-wins* de §11.5 não foi exercitada porque não declarei Scala 3 (V10 usa Java em
  tudo); segue sendo opção do §11.4, não obrigação.
- **`main.basedir` resolve.** O `directory-maven-plugin` roda em `initialize` no módulo novo e
  imprime `main.basedir=/pedro/desenvolvimento/workspaces/wor…`. (`mvn help:evaluate` devolve `null`
  para ele **em qualquer módulo**, inclusive no `rvsec-agent` que o usa — é artefato de o
  `help:evaluate` não rodar o ciclo de vida, não falha da propriedade.)
  **Ressalva**: resolve para o alias `/pedro/...`, que não abre na JVM. Qualquer uso de
  `main.basedir` para entregar caminho a um processo Java herda esse alias.
- **A árvore do usuário foi restaurada**: `rvsec/pom.xml` sem diff, `rvsec/rvsec-crysl/` removido.
  O esqueleto medido ficou em `v10/rvsec-crysl/`.
