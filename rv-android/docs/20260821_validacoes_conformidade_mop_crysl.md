# Validações V1–V10 do componente de conformidade MOP–CrySL

**Data:** 21 de agosto de 2026
**Escopo:** execução das validações que o handoff
`docs/handoff/20260821_conformidade_mop_crysl_prompt.md` deixou abertas
**Documento-mãe:** `docs/20260821_conformidade_mop_crysl.md`
**Arnês:** `docs/handoff/20260821_arnes_validacoes/`
**Estado:** as dez fecharam. Nenhuma linha de código de produção escrita; nenhum artefato OpenSpec
criado; nenhuma issue aberta.

O handoff pedia que o plano deixasse de ter hipótese não testada antes de virar change. Este
documento é a medição. Onde uma conclusão do documento-mãe se confirmou, está dito em uma linha;
onde mudou, a correção vem com a evidência que a produziu.

---

## Sumário

| | O que testava | Veredito |
|---|---|---|
| **V1** | `MOPSpecFile` montado à mão atravessa o `DumpVisitor` | ✅ passa |
| **V2** | gerar uma spec inteira ponta a ponta e medir contra o gabarito | ✅ passa — **é a validação central** |
| **V3** | `CrySLParser` com o `android.jar` da API 30 | ⚠️ a via é impossível; **impacto medido = zero**, e há desenho alternativo barato |
| **V4** | determinizar o `StateMachineGraph` e refazer os vereditos do §5.2 | ✅ vereditos confirmados |
| **V5** | preservar os nomes de agregado | ✅ passa, e entrega mais do que se pedia |
| **V6** | a costura JSON com os dois classpaths reais | ✅ passa — **mas o controle não foi rodado (R5): um processo também funciona**, ver abaixo |
| **V7** | o `.mop` gerado atravessa o pipeline inteiro | ✅ passa — e responde a pergunta aberta do §13 |
| **V8** | a semântica de fatiamento paramétrico | ✅ N1 confirmado por execução **nas specs sonda**; corrige o mecanismo do §4.1. **Ressalva de 22/08/2026 (R5): não generaliza** — 5 das 23 specs do corpus compilam para monitor global (sem `MapOfMonitor`) e nelas N1 é falsa |
| **V9** | dois achados de subagente | ✅ ambos confirmados, **ambos com alcance menor do que o relatado** |
| **V10** | o módulo mínimo compila no reator | ✅ passa — **precisado em 22/08/2026 (R5)**: o Guava 33.5.0-jre aparece num filho só (`-crysl`); o `-mop` não tem Guava no classpath resolvido. E a saída Scala 3 do §11.5 não existe: o `dependencyManagement` da raiz vence o *nearest-wins* e rebaixa para 2.11.12 |

**Nenhuma validação falseou o desenho.** Uma (V3) falseou a *via* proposta e ficou com desenho
alternativo definido e medido.

---

## O que mudou no documento-mãe

Seis correções e sete achados novos. Estão listados aqui porque mudam o que a proposta deve dizer.

### Correções

1. **§13 — "se N1 cair, dois dos três vereditos de equivalência voltam a *mais permissiva*".**
   Cai **um só**, o `KeyGeneratorSpec`. `MessageDigestSpec` e `SignatureSpec` são equivalentes com ou
   sem N1, porque a ERE de cada uma já traz um único evento criador na cabeça. Isso reduz o que V8
   decidia. *(V4)*

2. **§4.1 — "`g1` e `g4` co-disparam na mesma chamada; uma chamada produz a palavra `g4 g1`".**
   Errado nas duas metades. **Exatamente um dos dois dispara por chamada**, porque o corpo de `g1`
   escreve o campo que a guarda de `g4` lê, e o advice de `g1` roda inteiro antes. E se
   co-disparassem a ordem seria `g1 g4` — ordem de declaração —, que a ERE `(g4* g1 | …)`
   rejeitaria. **A conclusão do §4.1 continua de pé, por razão mais forte.** *(V8c)*

3. **§9 — `Signature.cryptsl:51` "não carrega".** Carrega ou não **conforme quais outras regras foram
   lidas antes**, no mesmo leitor. Ver o achado novo sobre vazamento de escopo. *(V4)*

4. **§9 — o `AIOOBE` do `CipherTransformationUtil` é "alcançável de `condition(...)` de
   `CipherSpec.g1/g2/g3`".** Verdade do grafo de chamadas, falso da entrada: `Cipher.getInstance`
   rejeita toda transformação com barra final antes de retornar, e todo sítio de `isValid` recebe
   uma transformação que já sobreviveu ao `getInstance`. Defeito **latente**, não crash vivo. *(V9b)*

5. **§13 — a não-determinação do `CrySLParser` vem do `HashSet` do classpath.** O `HashSet` é
   irrelevante: quem decide é a delegação *parent-first* do `URLClassLoader`. A instabilidade real é
   outra, e maior — o *resource set* do Xtext acumula escopo entre arquivos. *(V3, V4)*

6. **§8 — "uma camada de normalização de 4 substituições leva 20→30".** São **cinco** substituições
   e levam a **31/33**: falta `length(…)` → `length[…]`. *(V3)*

### Achados novos

1. **O escopo de `OBJECTS` vaza entre regras lidas pelo mesmo `CrySLModelReader`.** `Signature.crysl`
   usa `offset` e `len` sem declará-los; sozinho ele **falha**, depois de `GCMParameterSpec.crysl`
   (que declara os dois) ele **carrega**. O significado de uma regra depende da companhia. *(V4)*

2. **Três regras `api30` perderam a seção `CONSTRAINTS` inteira** em relação à regra CrySL original —
   `DHGenParameterSpec` (1 cláusula), `DSAGenParameterSpec` (5), `IvParameterSpec` (3). A perda
   acontece no template base do MetaCrySL, não na geração. O denominador de M3 já é uma perda. *(V2)*

3. **Duas regras `api30` especificam classes que não existem na plataforma Android.**
   `java.security.spec.DSAGenParameterSpec` só aparece na API 35;
   `javax.xml.crypto.dsig.spec.HMACParameterSpec` não existe em nenhum nível (o pacote
   `javax.xml.crypto` inteiro está ausente). E `jca_android/HMACParameterSpecSpec.mop` monitora
   exatamente essa classe: é uma das 23 specs do conjunto, **morta por construção**. *(V3)*

4. **O §10.3 está incompleto — falta a política de acoplamento `ENSURES` ↔ `CONSTRAINTS`.**
   O corpus humano escreve `boolean conforms = true; … if (conforms) { spec = s; }`: o predicado
   não vale para uma construção que quebrou uma cláusula. O gerador precisa dessa política, e ela
   não está nomeada. *(V2)*

5. **O pipeline inteiro é cego para os dois defeitos de sintaxe do `jca` congelado.** `.mop` →
   `.rvm` → monitor Java → **compila com 0 erros**. O `c2` inexistente do `ere` desaparece do
   alfabeto sem aviso. *(V7)*

6. **`getStatesForMethods` resolve por método, não por nome de agregado.** O conjunto de nós só fica
   vazio quando **nenhum** método do agregado aparece no `ORDER` — mais raro do que o relatado, e
   ausente do corpus. *(V9a)*

7. **O `AIOOBE` do `CipherTransformationUtil` é mais largo que o relatado**: `alg("/")` também lança,
   e as três utilitárias caem juntas porque todas delegam o parsing à mesma classe. *(V9b)*

---

## V1 — `MOPSpecFile` do zero pelo `DumpVisitor` ✅

Montado à mão: pacote, quatro imports, um campo, um `creation event` com `args()` e `condition()`,
`ere`, `@fail` e `@match`. Dump e reparse com semântica preservada — `creation=true`,
`condition=[exponentSize < primeSize]`, `handlers=[fail, match]`.

Três coisas que a decisão de escrita ganha:

- **O emissor não constrói AST de AspectJ.** O construtor de `EventDefinition` recebe o pointcut
  como *string* e o parseia sozinho. Idem blocos Java, via `new JavaMOPParser(is).Block()`, e
  declarações de campo via `ClassOrInterfaceBodyDeclaration(false)`.
- **Armadilha**: `ClassOrInterfaceBody(boolean)` **não** consome chaves. Passar `{ T x; }` produz um
  *initializer estático* com uma variável local, não um campo — e reparseia calado.
- A não-idempotência é cosmética, como §11.1 já dizia.

**Consequência**: §12 se mantém, mas por razão mais fraca — o que exige os tipos do `javamop` é o
`MOPSpecFile`/`EventDefinition`, não o pointcut.

---

## V2 — gerar uma spec inteira ponta a ponta ✅ **a validação central**

Gerador em `v2/Gen.java`, família *parameter-spec* (eventos que são construtores do tipo da `SPEC`).
Emite pelo `MOPSpecFile` + `DumpVisitor`, nunca por concatenação de texto. Três specs geradas de
`api30`: `DHGenParameterSpec`, `GCMParameterSpec`, `PBEParameterSpec`. Todas reparseiam e atravessam
o pipeline.

### As quatro métricas, gerado × gabarito humano `jca_android`

| | DHGenParameterSpecSpec | GCMParameterSpecSpec | PBEParameterSpecSpec |
|---|---|---|---|
| **M1** eventos | 1/1 — id e assinatura idênticos | 2/2 idênticos | 2/2 idênticos |
| **M2** ordem | `c1` × `c1` — equivalentes | `(c1\|c2)` × `c1\|c2` — equivalentes | equivalentes |
| **M3** constraints | 0 no oráculo, 1 no humano | 1/1, mesmo idioma | 1/1, mesmo idioma |
| **M4** predicados | 1/1 `ensures` | 1 `requires` + 1 `ensures` | idem |

**M1 5/5 · M2 3/3 · M4 5/5 · M3 2/2 sobre o que o oráculo pede.**

### As divergências, uma a uma

**A cláusula que falta no `DHGenParameterSpecSpec` não é do gerador.** O `api30` não tem `CONSTRAINTS`
para essa regra; a regra CrySL original tem `exponentSize < primeSize`, e o `.mop` humano a
implementa. Três regras perdem a seção inteira entre a original e o template base do MetaCrySL:

| regra | cláusulas na regra original | no `api30` |
|---|---|---|
| `DHGenParameterSpec` | 1 — `exponentSize < primeSize` | 0 |
| `DSAGenParameterSpec` | 5 — `primePLen`, `subPrimeQLen`, 3 implicações | 0 |
| `IvParameterSpec` | 3 — `length[iv] >= offset+len`, `offset >= 0`, `len > 0` | 0 |

Isso acrescenta um **terceiro tipo de teto** aos dois do §6: o teto do *oráculo*. Um `.mop` humano
fiel à regra original aparece como `MOP-SEM-BASE` quando medido contra o `api30`.

**O substrato é a única divergência de M4, e é uma escolha que o gerador tem de receber.**
O gerado emite `ExecutionContext.setProperty/validate` — binário, um código por leitura. O humano de
`GCM` e `PBE` já migrou para `PredicateStore.ensure/validate` — três-valorado, **dois** códigos por
leitura (`VIOLATED` e `NOT_OBSERVED`). Mesma aresta do grafo, expressividade diferente. Não é
dedutível da regra: tem de ser parâmetro.

**O §10.3 está incompleto.** A primeira versão do gerador gravava o predicado sempre; o humano
condiciona a atribuição do campo a `conforms`. O humano está certo — um objeto que violou a cláusula
não pode carregar `preparedGCM`. Corrigido na segunda passada e é o padrão certo.

**Um defeito do gerador, corrigido**: não coletava os tipos usados nos pointcuts, então o
`PBEParameterSpecSpec` saía sem `import java.security.spec.AlgorithmParameterSpec` — parseava e não
compilaria.

**O que não é divergência**: nome de parâmetro (`tLen` × `tagLen`), literal inline × campo
`validLengths`, `creation event` × `event`, parentização redundante do `ere`. E os três conjuntos que
o humano **deletou** de `GCM` (`offset>=0 && len>=0 && src.length>=offset+len`) porque não traduzem
cláusula alguma e o construtor já os garante — o gerador não os emite por construção.

**Veredito**: os percentuais do §10 deixam de ser previsão para estas três specs. Onde o gerado
diverge do humano, a causa é nomeável em todos os casos.

---

## V3 — `CrySLParser` com o `android.jar` da API 30 ⚠️

### A via proposta é impossível, e por razão de princípio

O bytecode de `CrySLModelReaderClassPath.getClassPath()` devolve
`HashSet(javaRuntimeClassPath ∪ virtualClassPath)` — o classpath virtual **nunca substitui**, só
soma. E o `CrySLModelReader` constrói `new URLClassLoader(urls)` com **pai padrão**, então a
resolução passa por delegação *parent-first* e a JDK vence qualquer nome que ela tenha.

Duas sondas decidem:

| sonda | sem `android.jar` | com `android.jar` no classpath virtual |
|---|---|---|
| `android.util.Base64.encodeToString` (só Android) | não resolve | **resolve** |
| `java.util.HexFormat.formatHex` (JDK 17, ausente da API 30) | resolve | **resolve na mesma** |

A via (b) do handoff — "JVM cujo classpath de aplicação contenha só o `android.jar`" — **também não
funciona**: `java.base` não vem do `java.class.path`, vem da camada de módulos, e nem
`new URLClassLoader(urls, null)` a remove. Restringir a leitura à API 30 exigiria substituir o
`ClasspathTypeProvider`.

### O impacto medido é zero

Os 31 arquivos que carregam produzem **129 linhas de assinatura resolvida idênticas** com e sem o
`android.jar` — `diff` = 0.

### O desenho alternativo, e ele é barato

Em vez de forkar o CrySL: **validar a posteriori** cada assinatura resolvida contra o `android.jar`.
Medido em 155 eventos:

| | n |
|---|---:|
| assinatura exata na API 30 | 131 |
| casa só por aridade (apagamento de genéricos, `AnyType`) | 19 |
| limitação do conferidor (`SecretKey.destroy/getEncoded`, herdados) | 2 |
| **classe ausente da API 30** | **3** |

As três: `java.security.spec.DSAGenParameterSpec` (×2) e `javax.xml.crypto.dsig.spec.HMACParameterSpec`.
Nenhuma existe na API 30 — a primeira só na 35, a segunda em nenhum nível verificado (26, 30, 33, 35).
E `jca_android/HMACParameterSpecSpec.mop` monitora essa segunda: uma das 23 specs do conjunto,
**morta por construção** no Android. É outro ângulo sobre o "0/1 parâmetro ligado" do §9.

### A normalização léxica tem cinco substituições

`FORBIDDEN:`→`FORBIDDEN`, `;;`→`;`, `alg`→`algName`,
`neverTypeOf/noCallTo/callTo/notHardCoded(…)`→`[…]`, e **`length(…)`→`length[…]`**. Com as cinco,
**31/33** carregam. As duas residuais são as conhecidas: `AlgorithmParameters:47` e
`DigestOutputStream:20`.

---

## V4 — determinizar o `StateMachineGraph` ✅

**A NFA de Glushkov é real e nenhuma regra do corpus a exibe.** A sintética `ORDER con, a?, a`
produz mesmo duas arestas `append` do mesmo nó. Varridas as 31 regras `api30` que carregam:
**31 determinísticas, 0 não-determinísticas**. A determinização é obrigatória por correção geral e é
*no-op* neste corpus. `wrapUpCreation()` precisa mesmo ser chamado à mão.

### Os cinco vereditos, agora sobre o autômato que o parser entrega

| Spec | §5.2 dizia | sem N1 | com N1 |
|---|---|---|---|
| `MessageDigestSpec` | EQUIVALENTES | **EQUIVALENTES** | EQUIVALENTES |
| `SignatureSpec` | EQUIVALENTES | **EQUIVALENTES** | EQUIVALENTES |
| `KeyGeneratorSpec` | EQUIVALENTES | MOP mais permissiva — `g1 g1 gk1` | **EQUIVALENTES** |
| `SecureRandomSpec` | MOP mais permissiva | MOP mais permissiva — `c1 c1` | **MOP mais permissiva** — `SecureRandom(); generateSeed(int); setSeed(byte[])`, testemunha idêntica à do §5.2 |
| `CipherSpec` | INCOMPARÁVEIS | **INCOMPARÁVEIS** | INCOMPARÁVEIS — testemunhas **idênticas** às do §5.2: `g1 i2 doFinal()` e `g1 i2 i2 doFinal(byte[])` |

O motor é `m2/Aut.java` + `m2/M2.java`: parser de ERE, parser do bloco `fsm`, subconjunto,
reetiquetagem pelo mapa de alfabeto, filtro N1, e equivalência por busca no produto com testemunha
mínima nas duas direções. Os mapas estão em `maps/*.map`.

**Confirma o §9 sobre o `order_alphabet_map.csv`**: `CipherSpec.f2` mapeia mesmo `{f1,f2,f4}` — o
pointcut é `public byte[] Cipher.doFinal(..)` e as sobrecargas que devolvem `byte[]` são
`doFinal()`, `doFinal(byte[])` e `doFinal(byte[],int,int)`. É daí que sai a testemunha
`g1 i2 doFinal()`.

---

## V5 — preservar os nomes de agregado ✅

As ~10 linhas previstas no §10.2 funcionam fora do jar publicado:

```java
Injector inj = new CrySLStandaloneSetup().createInjectorAndDoEMFRegistration();
XtextResourceSet rs = inj.getInstance(XtextResourceSet.class);
URL[] cp = CrySLModelReaderClassPath.JAVA_CLASS_PATH.getClassPath();
rs.setClasspathURIContext(new URLClassLoader(cp));
new ClasspathTypeProvider(new URLClassLoader(cp), rs, null, null);
Domainmodel dm = (Domainmodel) rs.getResource(URI.createFileURI(path), true).getContents().get(0);
```

- **33/33 arquivos entregam AST** — inclusive os 2 que a fachada rejeita por erro de validação.
  A via AST é estritamente mais permissiva, o que é bom para relatório.
- Recuperados **167 nomes de evento** e **61 agregados** com membros, em 23 das 33 regras. Exemplo
  `Cipher`: `Gets:=g1|g2`, `IWOIV:=i1|i2|i3|i8`, `IWIV:=i4|i5|i6|i7`, `Inits:=IWOIV|IWIV`,
  `updates:=u1..u5`, `FINWOU:=f2|f4|f5|f6|f7`, `DOFINALS:=FINWOU|f1|f3`.
- **A procedência `arquivo:linha` sai junto**, por `NodeModelUtils`, e o texto cru do `ORDER`
  também. §11.3 previa e está confirmado.

A leitura pela AST foi fundida no leitor CrySL — é o que o componente faria.

---

## V6 — a costura JSON com os dois classpaths reais ✅

Três processos, nenhum compartilhando JVM: `LiftCrysl` (classpath do `CrySLParser`, Guava 33.5),
`LiftMop` (classpath do `javamop`), e o núcleo `M2` (só Gson). 33 regras e 23 specs serializadas; o
núcleo compara sem tocar em nenhuma das duas tecnologias — **é o que produziu a tabela do V4**.

Nada de essencial se perde. O autômato sai como `{start, accepting, edges[]}` com arestas rotuladas
por conjunto de assinaturas, mais um `deterministic` calculado no leitor. Os eventos MOP saem com
`id`, `pos`, `creation`, pointcut cru, `condition` e as assinaturas de `call(...)` extraídas do AST
de AspectJ. A `ORDER` sai como `{formalism, text}`.

**Ressalva medida**: o texto do `fsm` traz junto as linhas `alias matchN = estado`, e o `ere` chega
com espaçamento cru. Não é perda — é trabalho de parser no núcleo, já escrito.

> **O controle desta validação não foi rodado — corrigido em 22/08/2026 (R5).** V6 mostrou que três
> processos **funcionam**; nunca testou se **um** falha. E não falha: um módulo único que declare
> `javamop` + `CrySLParser`, com `<guava.version>33.5.0-jre</guava.version>` no pom-pai, roda
> `SpecExtractor.parse` e `CrySLModelReader.readRule` na mesma JVM, `EXIT=0`. Com o pin herdado de
> 19.0 a sonda compila limpa e morre em `new CrySLModelReader()` com
> `NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()` — logo o conflito é real, mas é do
> `dependencyManagement` da raiz, não do `javamop` (que não puxa Guava nem Soot).
>
> E o "nada de essencial se perde" tem custo a declarar: como a `ORDER` sai como `{formalism, text}`,
> **o núcleo precisa do seu próprio parser de `ere`/`fsm`** — a duplicação que o §3 do plano diz que o
> componente existe para acabar; a numeração de estados do DFA no fio não é fixada por nada; e um erro
> de leitura dentro do *lift* vira código de saída em vez de item `Unknown` tipado.

---

## V7 — o `.mop` gerado atravessa o pipeline inteiro ✅

`javamop -merge` → 3 `.rvm` + `MultiSpec_1MonitorAspect.aj`; `rv-monitor -merge -d` →
`MultiSpec_1RuntimeMonitor.java` com `static final int Prop_1_transition_c1[] = {1, 2, 2};`.
**O monitor gerado compila**: `javac` contra `rvsec-core` + `rv-monitor-rt` + `rvsec-logger-csv`,
**0 erros, 7 classes**. (`ErrorCollector` mora no `rvsec-logger-csv`, não no `-core`.)

### A pergunta aberta do §13 sobre as duas specs com defeito de sintaxe em `jca` — respondida

O conjunto `jca` congelado atravessa o pipeline **em silêncio**: 23/23 `.rvm`, monitor gerado, e
**compila com 0 erros (63 classes)**. Para `jca/GCMParameterSpecSpec.mop` — dois eventos com id `c1`,
`ere : c1 | c2` citando um `c2` que não existe — o monitor sai assim:

```java
static final int Prop_1_transition_c1[] = {1, 2, 2};;
static final String[] RVM_eventNames = {"c1", "c1"};;
...
int nextstate = this.handleEvent(0, Prop_1_transition_c1);   // primeiro c1
int nextstate = this.handleEvent(1, Prop_1_transition_c1);   // segundo c1, MESMA tabela
```

O `c2` do `ere` **desaparece do alfabeto sem uma linha de aviso**, e não existe
`Prop_1_transition_c2`. Nem "parseou", nem "gerou monitor", nem "compilou" é oráculo de sanidade. O
checador de vinte linhas sobre a AST — ids únicos, alfabeto da fórmula ⊆ ids — é o único que pega.

---

## V8 — a semântica de fatiamento paramétrico ✅

Tudo na JSE com `ajc` 1.9.25.1 e `rv-monitor-rt`. **Nenhum emulador envolvido.**

**Um monitor por objeto.** Spec sonda com `creation event g` (`getInstance`), `event gk`
(`generateKey`, `target(k)`) e `ere : g gk` — ERE que **rejeita** duas criações. Programa com dois
`getInstance` seguidos de dois `generateKey`:

```
[EV] g   monitor=2007328737 kg=340870931
[EV] g   monitor=1830908236 kg=1936628443     <- monitor DIFERENTE
[EV] gk  monitor=2007328737 kg=340870931   → [MATCH]
[EV] gk  monitor=1830908236 kg=1936628443  → [MATCH]
```

Dois objetos, dois monitores, cada um com exatamente um evento criador. **Zero `@fail`.** Se o
monitor fosse global, o segundo `g` teria levado ao estado de falha. **N1 vale.**

**Dois eventos no mesmo join point co-disparam.** Spec com `g` e `h` sobre o *mesmo* pointcut,
`ere : g h gk`, um único `getInstance`: os dois disparam, **na ordem de declaração, no mesmo monitor,
com a mesma ligação**.

**Correção ao §4.1.** Réplica exata da forma do `MessageDigestSpec` — guarda de `g1` no argumento,
guarda de `g4` no campo `currentAlgorithmInstance`, `g1` declarado antes:

```
=== algoritmo seguro (SHA-256) ===
[EV] g1 monitor=396180261 alg=SHA-256 campoAntes=''    → [MATCH]     (só g1)
=== algoritmo inseguro (MD5) ===
[EV] g4 monitor=835648992 alg=MD5     campoAntes=''    → [FAIL ]     (só g4)
```

A razão é a ordem: a `condition` compila para `if (!(guarda)) return false;` **dentro** do método do
evento, e o advice de `g1` roda inteiro — guarda **e corpo** — antes de a guarda de `g4` ser
avaliada. Como o corpo de `g1` escreve `currentAlgorithmInstance = alg`, a guarda de `g4`
(`!matches(campo)`) fica falsa. **Exatamente um dos dois dispara por chamada**; a palavra é `g1` ou
`g4`, nunca `g1 g4` nem `g4 g1`.

A conclusão do §4.1 continua de pé por razão mais forte: a testemunha `g1 g1` morre por N1, e o par
`g1/g4` é mutuamente exclusivo por construção da guarda.

---

## V9 — os dois achados de subagente ✅ ambos confirmados, ambos com alcance menor

### `CrySLModelReader.getStatesForMethods`

Duas regras sintéticas decidem:

| regra | resultado |
|---|---|
| `digested[out] after Gets`, `Gets` no `ORDER` | `NOS=2` |
| `digested[out] after Fora`, `Fora := d2`, `d2` **fora** do `ORDER` | **`eventos=1 NOS=0`** |

O predicado vale em estado nenhum, a regra carrega **sem erro e sem aviso**.

**Precisão a mais**: a resolução é **por método, não por nome de agregado**. `Sozinho := g1` com
`ORDER Gets, d1` (onde `Gets := g1|g2`) resolve normalmente. O conjunto só fica vazio quando
**nenhum** método do agregado aparece no `ORDER`.

**Alcance no corpus: zero.** As 19 cláusulas `after` das 33 regras `api30` citam, todas, símbolo
presente no `ORDER`. É risco a detectar e reportar, não defeito vivo.

### `CipherTransformationUtil.mode("AES/")`

Confirmado por execução, e mais largo do que o relatado: `mode("AES/")`, `mode("AES//")`,
`mode("RSA/")` lançam `ArrayIndexOutOfBoundsException`, `alg("/")` também, e as três utilitárias
caem juntas porque todas delegam o parsing à mesma classe.

**Mas o caminho pela JCA está fechado.** `Cipher.getInstance` rejeita todas as formas com barra
final antes de retornar — `NoSuchAlgorithmException: Invalid transformation format`. Todo sítio de
`isValid` nas specs recebe uma transformação que já sobreviveu ao `getInstance`, seja por
`args(transformation)` num `after … returning`, seja por `c.getAlgorithm()` sobre um `Cipher`
obtido. **Defeito latente**, não crash vivo: vale a guarda de duas linhas, não vale conserto de
emergência.

---

## V10 — o módulo mínimo compila no reator ✅

Quatro `pom.xml` do §12 com uma classe vazia em cada, montados em `rvsec/rvsec-crysl/` e adicionados
a `rvsec/pom.xml`. `BUILD SUCCESS` nos quatro.

- **Guava: a sobrescrita funciona como §11.5 previa.** `<guava.version>33.5.0-jre</guava.version>` no
  pom-pai do componente → propriedade efetiva `33.5.0-jre`, e a árvore mostra
  `com.google.guava:guava:jar:33.5.0-jre:compile` nos dois filhos de tecnologia. O
  `dependencyManagement` da raiz é *property-driven*, então a herança segue junto.
- **`slf4j-simple` excluído**: sobra só `org.slf4j:slf4j-api:2.0.17`.
- **Scala**: `rvsec-crysl-mop` recebe `scala-library:2.11.12` transitivamente por
  `javamop → rv-monitor → ptltl`, como previsto, e não atrapalha — o módulo é Java 21. O
  *nearest-wins* de §11.5 não foi exercitado porque não declarei Scala 3; segue opção do §11.4.
- **`main.basedir` resolve.** O `directory-maven-plugin` roda em `initialize` no módulo novo.
  (`mvn help:evaluate` devolve `null` para essa propriedade **em qualquer módulo**, inclusive no
  `rvsec-agent` que a usa — é artefato de o `help:evaluate` não rodar o ciclo de vida.)
  **Ressalva**: resolve para o alias `/pedro/...`, que não abre na JVM.
- **A árvore foi restaurada**: `rvsec/pom.xml` sem diff, `rvsec/rvsec-crysl/` removido. O esqueleto
  medido ficou em `docs/handoff/20260821_arnes_validacoes/v10/`.

---

## A questão do parâmetro múltiplo

JavaMOP é paramétrico sobre uma **tupla**; CrySL nomeia **um** tipo em `SPEC` e não tem autômato
conjunto sobre um par de objetos. A resposta de CrySL para relação entre dois objetos é **predicado**
(`ENSURES generatedKey[key, algName]`), não ordem conjunta — é a mesma aridade-2 do §5.4 vista pelo
outro lado.

| Conjunto | specs | com mais de um parâmetro |
|---|---:|---|
| `jca` | 23 | **0** |
| `jca_android` | 23 | **0** (todas com 0 ou 1) |
| `generic_new` | 27 | 4 |
| `generic` | 118 | **93** — 39 com 2, 28 com 3, 18 com 4, 7 com 5, 1 com 6 |

- Na direção **CrySL → MOP** (o gerador) o problema **não existe**: `SPEC` nomeia um tipo, logo a
  spec gerada tem sempre um parâmetro. É até propriedade boa — o gerador não consegue cometer o
  defeito das 6 de 21 specs com fatiamento quebrado.
- Na direção **MOP → CrySL** e no **comparador**, uma spec de *k*>1 parâmetros não tem imagem em
  CrySL quando a `ORDER` de fato intercala eventos sobre objetos diferentes. A saída certa é
  **recusa tipada** — `Unknown{MultiSlicedOrder, params:[…]}` — nunca achatamento silencioso.
- **Custo medido da restrição no corpus do componente: zero (0/23).** É fronteira de escopo
  declarada, não dívida. Vira dívida real no dia em que apontarem o comparador para o `generic`,
  onde são 93 de 118 — e aí a recusa tipada é o que impede o relatório de mentir.

---

## O que a proposta tem de dizer, além do que o §13 já pedia

1. **Declarar o teto do oráculo**, além dos dois tetos do §6. Três regras `api30` perderam
   `CONSTRAINTS` que a regra CrySL original tem; medir contra o `api30` acusa como `MOP-SEM-BASE`
   uma spec fiel à regra de origem.
2. **Declarar a política de substrato** como parâmetro do gerador — `ExecutionContext` (binário) ou
   `PredicateStore` (três-valorado). Não é dedutível da regra e muda o número de códigos emitidos.
3. **Acrescentar ao §10.3 a política de acoplamento `ENSURES` ↔ `CONSTRAINTS`**: o predicado não
   vale para uma construção que quebrou uma cláusula.
4. **Declarar a fronteira do parâmetro único** com o custo medido (0/23 no corpus, 93/118 no
   `generic`) e a recusa tipada como saída.
5. **Ler cada regra CrySL num leitor novo**, ou declarar a ordem de leitura — o escopo de `OBJECTS`
   vaza entre regras no mesmo `CrySLModelReader`.
6. **Validar a posteriori contra o `android.jar`** em vez de tentar fixar o classpath do parser.

---

## Consertos que a medição confirmou e que valem independentemente

Em ordem de retorno, e todos baratos:

1. **Checador de sanidade de `.mop`** — ids únicos e alfabeto da fórmula ⊆ ids. Vinte linhas sobre a
   AST. V7 mostra que é o **único** ponto do pipeline inteiro capaz de pegar essa classe.
2. **`PrettyPrinter.rsc:49,139`** no MetaCrySL — duas linhas, e as cinco substituições léxicas
   medidas em V3 dizem exatamente quais.
3. **Precedência invertida** em `scripts/gh105_order_gate.py:136-200` e em
   `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70`. O parser de `ORDER` de `v2/Gen.java` já traz
   a precedência correta e serve de referência.
4. **Guarda de duas linhas** em `CipherTransformationUtil.alg/mode/pad` — latente, não urgente.
5. **Restaurar as `CONSTRAINTS`** dos três templates base do MetaCrySL. São ~9 cláusulas normativas
   apagadas do oráculo, e o efeito é sobre o denominador de M3, não sobre uma spec só.
