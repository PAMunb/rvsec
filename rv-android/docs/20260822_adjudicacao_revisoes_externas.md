# Adjudicação das revisões externas — componente de conformidade MOP–CrySL

**Data:** 22 de agosto de 2026
**HEAD no início da adjudicação:** `c12f4689`
**Objeto:** as três revisões externas em `docs/analise_mop2crysl_{gemini3,gpt-5,opus5}.md`, confrontadas com a fonte primária
**Artefatos corrigidos a partir daqui:** `docs/20260821_conformidade_mop_crysl.md` (o plano), `docs/20260821_auditoria_conformidade_mop_crysl.md` (a auditoria de consistência), `docs/handoff/20260821_arnes_validacoes/NOTAS-BRUTAS.md`

Três modelos receberam o mesmo prompt de revisão adversarial (`docs/handoff/20260821_prompt_revisao_externa_conformidade.md`) e devolveram relatórios independentes. Este documento **não** adota as recomendações deles. Ele arbitra: cada claim foi remedida por oito verificadores contra a fonte primária — corpora no disco, código do JavaMOP, `CrySLParser 4.0.6` executado, monitores regerados e tecidos com `ajc`, e o fonte do paper do TSE 2023 — e só o que sobreviveu entra nos artefatos.

A arbitragem valeu a pena por uma razão concreta: **das claims em que dois revisores concordavam entre si e contra o plano, duas estavam erradas** e teriam piorado o documento se adotadas.

---

## 1. As refutadas — o que **não** se deve corrigir

Esta seção existe para que a próxima rodada não reintroduza estas "correções". Cada linha traz a medição que a derruba.

### 1.1 `generic` não tem 97 specs multi-parâmetro. O plano está certo com 93.

Gemini e GPT-5 recontaram **97** e classificaram o **93** do plano como `REFUTED — HIGH`, com buckets `{1:21, 2:40, 3:30, 4:17, 5:6, 6:4}`. Os dois contaram o **texto do cabeçalho** da spec.

Parse real das 118 specs com `javamop.parser.SpecExtractor`, lendo `spec.getParameters().size()`:

```
TOTAL specs=118 fail=0 buckets={1:25, 2:39, 3:28, 4:18, 5:7, 6:1} multi=93
```

Os buckets da AST reproduzem **literalmente** a linha `:1167` do plano ("39 com dois, 28 com três, 18 com quatro, 7 com cinco, 1 com seis"). O plano usa a regra da AST e usa-a corretamente; o que falta é **declarar a regra**.

**E a diferença é um defeito, não um detalhe.** `MOPParameters.add` (`javamop/.../ast/mopspec/MOPParameters.java:41-51`) descarta silenciosamente parâmetro cujo **nome** já existe — `getParam` (`:84-94`) compara só o nome, ignorando o tipo — e não há diagnóstico em lugar nenhum, ao contrário de evento duplicado, que é detectado e renomeado (`JavaMOPSpec.java:100-135`). Onze specs do `generic` perdem declarações: `FSM119` (6→4), `FSM123` (2→1), `FSM133`, `FSM140`, `FSM197`, `FSM206`, `FSM209` (6→4), `FSM224`, `FSM45`, `FSM60`, `FSM69`.

O dano vai além da contagem. Gerado o monitor de `FSM123` pelo pipeline real (saída "FSM123.rvm is generated", zero avisos):

```
entrada :  FSM123(InetAddress i, InetSocketAddress i) { event event_1 after(InetSocketAddress i): ... }
gerado  :  FSM123(InetAddress i)  com os três eventos ligando InetSocketAddress i
```

**O tipo sobrevivente na tupla de indexação é o do primeiro declarado, e pode não ser o que os eventos ligam.** Adotar "97" teria trocado um número certo por um errado *e* apagado esta classe de defeito.

### 1.2 A citação do TSE 2023 existe. O achado A13 da auditoria cai.

A auditoria afirmou que a frase *"the CrySL and JavaMOP specification languages are similar"* *"não contém essa frase nem nada próximo"* no paper; o gemini seguiu-a e recomendou "remover as aspas da citação".

`rvsec-paper/main.tex:811-814`:

```
First, these \csl \specs were validated by \crypto
experts. Second, the \csl
and JavaMOP \spec languages are similar. Third, the \cc development team provide a test suite ...
```

É a **segunda das três *main reasons***; a auditoria citou a primeira e parou. A frase está nas duas edições do paper (o draft de 2022 escreve *"there are similarities between the CrySL and JavaMOP specification languages"*). E `macros.tex:132` define `\nrules`=22 com `main.tex:824-825` dizendo *"In total, we write 22 JavaMOP \specs"* — logo o "22" do §10.6 também está certo.

**A causa do erro é metodológica e vale mais que o erro.** A auditoria consultou `ase-journal/docs/notes/@torres-tse-2023.md`, um cofre **indexado por uso**: cada entrada é `## Use: <arquivo:linha>`, doze excertos escolhidos porque sustentam doze afirmações. Ausência ali nunca foi evidência de ausência no paper. O mesmo método pode ter contaminado outros achados da mesma auditoria.

Detalhe adicional que o cofre resolve: `rvsec-paper/main.pdf` tem 12 páginas e é o **draft pré-aceitação de 2022**; o `main.tex` é que corresponde à edição publicada. Quem for verificar citação deve ler o `.tex`, não o PDF da árvore.

### 1.3 A objeção aritmética ao §6 testa uma estrutura que o texto não afirma.

Auditoria (A6) e gemini: a formulação do §6 perde a parcela de 28, porque `26 + 19 + 19 = 64 ≠ 92`.

O §6 (`:469-474`) enuncia um **encaixe**, não uma partição: `92 ⊃ 73 ⊃ 54 ⊃ 26`, com `73 − 54 = 19` e `92 − 73 = 19`. As duas contas fecham e nada no §6 contradiz o §5.4.

**Mas o defeito é real, e a evidência dele é melhor que a objeção.** O antecedente natural de "as 19 restantes", vindo logo depois de "26 estão implementadas — 48 % do exprimível", é o **54**, cujo resto é 28. Três leitores independentes leram exatamente assim: a auditoria, o gemini, e um subagente do opus5 que não conhecia nenhum dos dois. O §6 afirma da própria formulação que é *"a única versão que um revisor não pode ler errado"* — afirmação empiricamente falsificada três vezes.

**Reparo adotado:** escrever a parcela de 28 por extenso e retirar a auto-afirmação. Não "consertar" a aritmética.

### 1.4 Outras refutações menores

| Claim | Quem | Medição |
|---|---|---|
| "26 de 34 sítios de `ENSURES` sem leitor" | opus5 | São **23 de 34** (16 *properties*). A assinatura 26/34 não existe em nenhum dos 14 commits recentes; a própria lista da revisão soma 16. |
| "só o `CipherSpec` tem par subsumido não guardado, nos dois conjuntos" | opus5 | Vale para `jca_android`. No `jca` há mais três pares no `PBEKeySpecSpec` (`err1`/`err2`/`err3`, guardas não mutuamente exclusivas) — ver §3.1. |
| "a lista de seis specs com fatiamento quebrado do §9 está errada nas duas direções" | opus5 | Os seis números batem **exatamente** contra o código gerado. `CipherInputStreamSpec`/`CipherOutputStreamSpec` são declaradas **sem parâmetro**, logo fora do escopo "21 specs parametrizadas" (23 − 2 = 21 fecha). |
| "nenhum modo de leitura produz 31" | opus5 | O leitor partilhado em ordem alfabética produz 31, e é de lá que o número do plano veio. |
| "o discriminante é o comentário `RVMRef_x was suppressed`" | opus5 | O comentário aparece **21 vezes**, uma por spec paramétrica, inclusive nas que indexam. O discriminante é a ausência de `MapOfMonitor`. |
| "o conflito de Guava não existe" | opus5 | Existe — por outro mecanismo (§2.5). O que cai é a cadeia causal do plano e a necessidade de três processos. |
| "o pareamento é 21 de 23" | opus5 | São **22 de 23**. `IvParameterSpec.mop` pareia normalmente; só o nome do arquivo é irregular. A única sem regra é `RandomStringPassword.mop`. |
| "o 97 do §10 é órfão total" | auditoria | Não é: `56 target(<param>) + 41 returning(… <param>)` = 97 sítios de ligação de parâmetro. O que falta é declarar o denominador. |

---

## 2. As confirmadas — o que entra nos artefatos

### 2.1 São 30 regras que carregam, não 31 — e o plano cita um número produzido pela via que ele mesmo condena

O §12 decide "um `CrySLModelReader` **por regra**". Medido com `CrySLParser 4.0.6` (resultados idênticos em JDK 17, 21 e 25):

```
leitor novo por regra          ok=30/33   falham AlgorithmParameters, DigestOutputStream, Signature
leitor partilhado, alfabético  ok=31/33
leitor partilhado, inverso     ok=29/33
40 ordens aleatórias           {29:3, 30:15, 31:22}    falhas: DigestOutputStream 40, AlgorithmParameters 40, Key 15, Signature 6
leitor novo, 10 ordens         10 × ok=30              (invariante)
```

**Sob a decisão do §12 o número é 30.** As três frases derivadas herdam o erro: §8 ("as 31 regras que carregam produzem 129 linhas de assinatura idênticas com e sem `android.jar`" — as 129 precisam de remedição), §10.2/V4 ("31 determinísticas"), §12 ("*no-op* nas 31 regras de hoje").

**O vazamento de escopo corre nos dois sentidos** — a auditoria viu só o resgate. Quem conserta o `Signature` num leitor partilhado são exatamente `GCMParameterSpec`, `IvParameterSpec` e `Mac`, as três únicas regras que declaram **ambos** `int offset;` e `int len;` em `OBJECTS`. E na direção contrária, `SecretKey.crysl` lido antes de `Key.crysl` **quebra** o `Key.crysl` (`Couldn't resolve reference to JvmExecutable 'getEncoded'`), que sozinho carrega. O escopo esconde defeito *e* cria defeito.

Isso derruba a "CORREÇÃO a §9" registrada em `NOTAS-BRUTAS.md` (*"o parser 4.0.6 aceita `offset`/`len` não declarados e infere os tipos"*): não infere nada — herdou a declaração de outra regra.

**A via AST EMF entrega 33/33 e isso é vazio.** `getResource(…, true)` devolve a árvore com recuperação de erro; ninguém validou. Chamando `IResourceValidator` explicitamente, sobram **30** — e esse 30 coincide com a fachada de leitor novo em *todos* os degraus da escada. Pior, usar os três recusados é ativamente perigoso:

| regra | consequência |
|---|---|
| `Signature` | `NullPointerException` em `resolveEventsToCryslMethods` **e** em `buildSMG` |
| `DigestOutputStream` | `NullPointerException` em `CrySLReaderUtils.toCrySLMethod(forbidden)` |
| `AlgorithmParameters` | **trunca em silêncio**: `alg in {"BLOWFISH"} => preparedIV[params];` vira `algName in {"BLOWFISH"}` — a implicação e o predicado somem sem sinal, e a regra passa a *exigir* que o algoritmo seja BLOWFISH |

O que a via AST ganha: os agregados (a fachada os descarta; a AST os entrega em 23/33 com procedência) e o `ORDER` compilado (`StateMachineGraphBuilder.buildSMG` é `public static`, 32/33). O que ela perde de verdade: a árvore `ISLConstraint` de `CONSTRAINTS` e a montagem de `CrySLPredicate` — métodos privados de `CrySLModelReader`, que só expõe `readRule`.

### 2.2 A escada léxica do §8 mistura duas configurações

Medido degrau a degrau, com leitor novo por regra:

| degrau | §8 diz | medido (novo) | medido (partilhado/alfa) |
|---|---:|---:|---:|
| cru | 20 | **20** | 20 |
| `+FORBIDDEN:` | — | **22** | 22 |
| `+;;` | 22 | **22** | 22 |
| `+alg→algName` | — | **24** | 25 |
| `+colchetes` sem `length(` | 30 | **27** | 28 |
| `+length(…)→length[…]` | 31 | **30** | 31 |

`length(` move **27→30**, nunca 30→31. O degrau "30" do §8, rotulado *sem* `length`, mede 27. E as residuais são **três**, não duas — a terceira é o `Signature:51,59,65`, que só desaparecia por vazamento de escopo.

As três foram confrontadas com a regra oficial em `rvsec-cognicrypt/CrySL-Rules/`, e as três são defeitos reais do **gerador MetaCrySL**, nenhum alcançável por substituição léxica: `AlgorithmParameters:47` põe uma implicação com predicado dentro de `CONSTRAINTS` (o oficial põe em `REQUIRES`, e o próprio arquivo já tem a forma certa três linhas abaixo); `DigestOutputStream:20` declara `FORBIDDEN on(java.lang.String)` quando `javap` dá `public void on(boolean)`; `Signature` omite `int offset;` e `int len;` de `OBJECTS`, que o oficial declara.

**E "6 arquivos" são 4.** `neverTypeOf` ocorre em `KeyManagerFactory`, `KeyStore`, `PBEKeySpec`; `noCallTo` e `callTo` só no `Cipher`; `notHardCoded` tem **zero** ocorrências no `api30`. O 6 é a união com o grupo `length(` (`Cipher`, `SecretKeySpec`, `Mac`) — número certo, atribuído ao conjunto errado.

### 2.3 O alfabeto não é disjunto, e uma chamada emite uma palavra

Este é o achado que atinge o modelo canônico do §12. O §5.2 já o registra como normalização N4 (*"`doFinal(..)` também casa `doFinal()`; os eventos MOP não são disjuntos"*), mas o `events : Map<Label, Set<Signature>>` do §12 não tem onde guardá-lo.

Varredura dos 46 `.mop` (254 eventos), com interseção de aridade e tipo de retorno: **10 pares sobrepostos em `jca_android`, 26 no `jca`**. Dos que **não** são separados por guarda complementar:

- `CipherSpec` `f1` × `f2`, nos dois conjuntos, sem `condition` nenhuma. Tecido com `ajc` e executado em JSE, `getInstance("AES/GCM/NoPadding"); init(ENCRYPT,k); doFinal()` produz **dois** relatórios de um único *join point* — `CIPHER-ORDER-00 ev=f1` e `ev=f2`. O tecelão despachou `f1` primeiro; `f1` vai a *fail*, `__RESET` leva a 0, e `f2` de 0 também é *fail*. **A palavra é `f1 f2` e as duas letras acusam.**
- `jca/PBEKeySpecSpec` `err1` × `err2` × `err3` — as três têm `condition`, e as três condições não são mutuamente exclusivas. Um único `new PBEKeySpec(pw, salt, 500, 128)` produz **seis relatórios**: três `UnsatisfiedConstraint` e três `InvalidSequenceOfMethodCalls` (os três eventos estão declarados e ausentes do `ere : c1 c2`, logo têm linha de transição toda-`fail`). Uma chamada, três letras.

**A fusão de advices é um subconjunto do problema, não o problema.** O gerador funde apenas pointcuts de texto **idêntico** — `MultiSpec_1MonitorAspect.aj:314` mostra `g1` e `g3` no mesmo corpo. Sobreposições *semânticas* (`doFinal()` ⊂ `doFinal(..)`) saem como advices separados e o tecelão dispara os dois no mesmo *join point* assim mesmo. Contagem: `jca_android` 112 advices, 8 fundidos, 7 specs; `jca` 115, 17 fundidos, 13 specs.

Ressalva que importa para a normalização: `KeyGeneratorSpec:44/:60` e `MessageDigestSpec:44/:65` **não** são complementares sintaticamente — `g1` lê o argumento, `g3`/`g4` lê o campo `currentAlgorithmInstance`. Só são exclusivos porque o corpo de `g1` escreve o campo antes de `g3` ser despachado, dentro do mesmo advice fundido. **A separação depende da ordem de despacho, não da guarda.**

### 2.4 M2-eff não mede o que o §5.1 diz que mede

A `condition(...)` compila para dentro do método de evento, **antes** de qualquer transição:

```java
// MultiSpec_1RuntimeMonitor.java:4663
final boolean Prop_1_event_g1(String alg, KeyGenerator k) {
    if ( ! (ConscryptAliasTable.matches("KeyGenerator", alg, safeAlgorithms)) ) { return false; }
    { keyGenerator = k; currentAlgorithmInstance = alg; }
    int nextstate = this.handleEvent(0, Prop_1_transition_g1);     // a tabela vem depois
```

`Prop_1_transition_g1 = {2,5,2,5,5,5}` não carrega vestígio da guarda. Executado com `ajc` em JSE, `KeyGenerator.getInstance(alg); generateKey()` — **ordem correta pela regra** — dá:

```
DES →  KEYGENERATOR-ALG-00 (ev=gk1)  +  InvalidSequenceOfMethodCalls KEYGENERATOR-ORDER-00 (ev=gk1)
AES →  nenhum relatório
```

Uma acusação de **ordem** contra um programa que não viola ordem. Mecanismo: `g1` reprova a guarda e não transita, `g3` transita `0 → 0`, e `gk1` sai de 0, onde `Prop_1_transition_gk1[0] = 5` = *fail*.

**Agravante que o plano não registra:** o monitor é criado **antes** de a guarda ser avaliada (`// FindOrCreateEntry` em `KeyGeneratorSpec_g1Event`), então uma guarda reprovada deixa um monitor vivo no estado 0 e o evento seguinte é julgado dali.

**Consequência:** o autômato efetivo é `⟨tabelas, guardas, ordem de fusão de advice⟩`, e o M2-eff lê só a primeira componente. M2-decl também não vê a guarda (ela não aparece no `ere`). O §5.1 não pode continuar dizendo que M2-eff responde *"o monitor que rodou aceita a mesma linguagem que a regra?"*.

### 2.5 O conflito de Guava é real, a cadeia causal é falsa, e a JVM única funciona

O §12 justifica três processos assim: *"`CrySLParser` traz Guava 33.5.0-jre e Guice 7, enquanto `javamop` vive num reator que pina Guava 19.0 por causa do Soot"*.

Medido com `mvn -o dependency:tree`: **`javamop` não puxa Guava e não puxa Soot.** E o Soot 4.7.1 não declara Guava — ela chega por `heros:1.2.4 → guava:999.0.0-HEAD-jre-SNAPSHOT`, um *placeholder*; o único módulo do reator que usa Soot (`rvsec-gator`) já sobrescreve para 27.1-jre. Nada liga o valor `19.0` ao Soot.

O mecanismo real é outro: o `dependencyManagement` da **raiz** (`rvsec/pom.xml:41,158-160`) impõe Guava 19.0 a qualquer descendente, inclusive a um que só dependa do `CrySLParser` — `guava:jar:19.0:compile (version managed from 33.5.0-jre)`. Sonda executada com o pin herdado:

```
javac limpo; parse do .mop OK sob Guava 19
new CrySLModelReader() → NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()  (Guice 7 → Guava ≥31)
```

Isso **confirma** a metade do plano que diz "falharia em runtime, não em compilação". Mas acrescentando **uma linha** ao `<properties>` do pom-pai do componente (`<guava.version>33.5.0-jre</guava.version>`), um módulo único roda os dois parsers na mesma JVM:

```
== Guava carregado: guava-33.5.0-jre.jar
== parse .mop  : spec=MessageDigestSpec eventos=8 props=1
== ler regra   : rule=java.security.MessageDigest eventos=9 objects=10 · ORDER=9 transições
OK: os dois parsers rodaram na mesma JVM.   EXIT=0
```

O `javamop` é **indiferente** ao Guava (parseou sob 19.0 e sob 33.5.0-jre) porque não o toca. **Três processos e a costura JSON deixam de ser consequência e viram escolha** — defensável por inspecionabilidade e isolamento, mas é isso que o plano tem de argumentar.

Correção correlata: o V10 afirma Guava 33.5.0-jre "nos dois filhos". A sobrescrita funciona, mas o efeito aparece em **um** — o `-crysl`. O `-mop` não tem Guava nenhum no classpath resolvido.

### 2.6 O §11.5 está preso entre duas medições

- **O `ptltl` é 2.11** — `PTLTLHelpers.class` com *major version* 50, `ScalaSignature`, `$$anonfun$`.
- **Sobrescrever `scala.version` contamina o classpath inteiro e mata o `ptltl`.** Com `2.13.14`, `PTLTL.mkFSM("(*) a")` por reflexão dá `NoClassDefFoundError: scala/Serializable` (a classe existe no jar 2.11.12 e não existe no 2.13.14); sob 2.11.12 a mesma chamada funciona.
- **O *nearest-wins* alegado como "verificado na árvore" não pode ocorrer.** Com `scala3-library_3:3.3.4` declarado direto e sem tocar na propriedade, a árvore dá `scala-library:jar:2.11.12 (version managed from 2.13.14)` — o gerenciamento da raiz vence e **rebaixa**. O Scala 3 rodaria sobre uma `scala-library` 2.11.12 sem `ArraySeq`.

Logo: ou sobrescreve e quebra o `ptltl` que o próprio §11.5 proíbe excluir, ou não sobrescreve e o Scala 3 não resolve. Nuance medida que abre a saída: **nenhuma das 23 specs usa `ptltl`** (19 usam `ere`, 5 usam `fsm`), então a proibição de excluí-lo não é sustentada pelo corpus atual — mas isso não resgata a sobrescrita, porque a contaminação é global.

### 2.7 N1 não é lei geral

O §5.2 declara N1 (*"no máximo um evento criador por monitor"*) como regra *geral*, válida "para qualquer spec paramétrica". Censo do `MultiSpec_1RuntimeMonitor.java` regerado, idêntico nos dois conjuntos: **5 de 23 não constroem `MapOfMonitor`** — `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`, `KeyStoreSpec`, `RandomStringPassword`. Elas compilam para `Tuple2<Set, Monitor>`: **um monitor para o programa inteiro**, e o despachante confirma (`matchedEntry = KeyStoreSpec__Map`). Nelas a palavra `g1 g1` é realizável.

As três aplicações concretas de N1 no plano continuam válidas — `KeyGenerator`, `SecureRandom` e `Cipher` indexam integralmente. O que cai é a generalização.

Corolário para o critério de apagamento do §5.2 (*"…ou se nenhuma palavra realizável contém `e` junto com outros símbolos"*): o segundo disjunto quantifica sobre programas Java e não é decidível do `.mop`. É exatamente ele que torna N1 correta para o `KeyGeneratorSpec` e incorreta para o `KeyStoreSpec`, e os dois casos são **textualmente indistinguíveis**. O substituto decidível é a árvore de indexação do monitor gerado — que o M2-eff já lê.

### 2.8 Os números do §5.4/§7/§9 estão presos a um commit anterior

Contagem de sítios em `jca_android/*.mop`, varridos **todos os 25 commits** que tocam o diretório:

| commit | `ExecutionContext` | `PredicateStore` | arquivos migrados |
|---|---:|---:|---:|
| `d64f3a40` | 64 | 21 | 5 de 23 |
| **HEAD `c12f4689`** | **47** | **26** | **7 de 23** |
| árvore de trabalho | 45 | 28 | 8 de 23 |

A assinatura `64/21/5` ocorre em **exatamente um** commit. Corroboração independente: `predicate_graph.csv` tinha 85 linhas de dados em `d64f3a40` e tem **73** hoje (`86 → 85 → 79 → 78 → 74` linhas totais). O §7:513 diz "41 `condition(`"; hoje são **36**. E a linha de teto `74,0 % / 58,7 %` foi calculada para 5 arquivos migrados.

**A classificação FIEL/PROJETADO/CONFLADO/AUSENTE do §5.4 não é derivável de artefato nenhum.** `gh105_predicate_graph.py` (1845 linhas) nunca lê um `.cryptsl` — as três ocorrências de `crysl` estão em prosa de comentário — e o próprio docstring diz que carrega *"the committed `predicate_graph.csv` for the judgment columns **no analyzer can re-derive**"* (`:34-35`, repetido em `:1028-1030`). As colunas de julgamento são semeadas por humano e propagadas por `carry_judgments()`. Isso precisa estar escrito onde o número é publicado.

### 2.9 O teto do oráculo é maior que o §5.3 diz, e tem três modos

Regra de contagem declarada (**R1**): uma cláusula por `;` dentro de `CONSTRAINTS`, comentários removidos, conjunções `&&` **não** contadas à parte.

| corpus | escopo | R1 |
|---|---|---:|
| upstream `CrySL-Rules` | 49 regras | 119 |
| upstream | as 33 do `api30` | **95** |
| upstream | as 22 com `.mop` | 80 |
| `samples/jca/base` | 33 | 42 |
| `api30` | 33 | **62** |
| `api30` | as 22 com `.mop` | **55** ← o denominador do §5.3 |

`95 → 62` é **−33 líquido** em 16 regras (34 deleções contra 1 acréscimo). Sob outras regras de contagem: separar `&&` dá 101/71; separar os lados de `=>` dá 117/87. O "116" que uma das revisões relatou não reproduz sob nenhuma delas.

O "~9 cláusulas em 3 regras" do §5.3 está **correto para o que afirma** — `DHGenParameterSpec` 1 + `DSAGenParameterSpec` 5 + `IvParameterSpec` 3, as três regras cuja seção `CONSTRAINTS` inteira desapareceu — mas é subconjunto: o teto real é −33 sobre 33 regras (−25 sobre as 22 com `.mop`), em 17 regras.

E o teto tem **três modos**, dos quais o plano só descreve o primeiro:

1. **deleção** — o `api30` perde a cláusula → uma spec fiel à origem aparece como `MOP-SEM-BASE`. Já tratado, e o censo já aplica o rótulo certo (`IvParameterSpec.mop:35-37`, `DHGenParameterSpecSpec.mop:24`).
2. **corrupção de operador** — `api30/Cipher.cryptsl:131,133,135` escrevem `length(x) <= off` onde o upstream (`CrySL-Rules/Cipher.crysl:123,127,128`) escreve `>=`. Não é perda: as quatro cláusulas sobrevivem, três com o sentido invertido.
3. **substituição de predicado** — a tríade `length[x] >= off+len; off >= 0; len > 0` foi trocada por `len > off`, um predicado sobre dois inteiros que nada diz sobre o array (`base/{CipherInputStream,CipherOutputStream,DigestInputStream,DigestOutputStream,MessageDigest,Mac}`), e em `base/{IvParameterSpec,GCMParameterSpec,Signature}` simplesmente sumiu.

Os modos (2) e (3) erram na **direção oposta** ao (1): fariam uma tradução fiel à origem aparecer como infidelidade. **Hoje têm zero ocorrências** — a família `length` no `api30` são exatamente 6 cláusulas, das quais 5 estão `CRYSL-NAO-IMPLEMENTADO` e a única implementada (`SecretKeySpec.cryptsl:29`, `>=`, correta) é justamente a correta no oráculo (`SecretKeySpecSpec.mop:101`). É risco latente, não realizado — e é por isso que o "quarto eixo" proposto pelo opus5 **não** é um eixo novo: o plano já tem o teto do oráculo como terceiro eixo, com a consequência de sinal já nomeada. O que falta é registrar os três modos.

Tudo isso nasce no **template**, não no gerador: `MetaCrySL/samples/jca/base/Cipher.cryptsl:79-82` já traz as quatro cláusulas como o `api30` as tem. Regerar não corrige.

### 2.10 O arnês do gh104 é o maior precursor do componente e não está no §3

| artefato | tamanho |
|---|---|
| `rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` | **1255 l.** |
| `…/harness/TraceRunnerTest.java` | 243 l. |
| `rv-android/scripts/gh104_diff_harness.py` | 489 l. |
| `data/gh104/traces/` | **94 traços versionados** |
| `data/gh104/evidence/harness/` | **162 arquivos** (7 grupos × 23 specs + resumo) |

Ele replica um traço de chamadas por um **snapshot de monitor gerado**, com gramática própria (`bind`, `->`), resolve cada chamada contra os pointcuts do próprio snapshot lidos do descritor `MultiSpec_1MonitorAspect.json` — para que os dois lados não precisem partilhar alfabeto — e dá a cada traço um *class loader* novo, porque o monitor guarda as tabelas de indexação em campos `static`. Tem `Outcome.unresolved`, que distingue "não acusado" de "não replicado".

O `TraceRunner.java:36-42` enuncia a tese:

> *It exists because a structural gate measures the artefact and not its behaviour. gh100's wrapper merge removed twelve silently discarded wrappers … and the count that was reported as success (`wrappersGenerated 96 -> 84`) was blind to it; gh101's automaton repairs removed eighteen all-`fail` rows and moved the accusation to the next call, and no gate that counts rows could see that either.*

O §3 inventaria seis artefatos e "~10.400 linhas em 18 scripts `gh10*.py`" (confirmado: 18 arquivos, 10410 linhas). O `gh104_diff_harness.py` está dentro do agregado, mas no *bucket* "14 dos 18 parseiam `.mop` por regex" — do qual ele não faz parte. O `TraceRunner.java` está fora de qualquer contagem.

**E o §13:1240 é falso na primeira sentença.** Os monitores do gh104 foram gerados **das specs do corpus** (`rv-monitor-generator generate --specs-dir …/jca` e `…/jca_android`); o auto-teste replica 63 traços sobre o `jca`; há evidência por spec para o `jca_android` em sete grupos de 23 arquivos. Sobrevive apenas a última cláusula: "sobre APK real, não".

Custo de promovê-lo a oráculo do M2, medido: roda em JSE (precisa de JDK, não JRE) e **não** precisa de programa de apoio por tipo JCA — `instantiate()`/`produce()` constroem por reflexão a partir do nome escrito no traço. Falta (a) um enumerador de palavras curtas, (b) o mapa inverso evento → chamada **com argumentos concretos** — a peça cara, porque a escolha do argumento é semântica —, (c) o emissor de arquivo de traço e (d) trocar o classificador diferencial por veredito absoluto. Os 94 traços são testemunhas autoradas (1 a 9 por spec), corpus de regressão, não oráculo.

### 2.11 A aritmética do §10, e a proveniência que falta

| número | veredito |
|---|---|
| `152/167` (91 %) | percentual correto; o texto nomeia **12** dos **15** não resolvidos |
| `22/22` | fecha trivialmente |
| `7/22` + `11/22` | **não fecha em leitura nenhuma** — disjunto dá 18 (sobram 4 nunca citadas), aninhado sobram 11; e o "gêmeo negado (10/22)" não corresponde a nenhum dos dois |
| `16/55` + `47/55` | **63 > 55**; e nenhum dos dois se reconcilia com a partição do §5.3 (11+3+4+7+30, presentes = 25) |
| `87/92` + "4 lacunas" | `92 − 87 = 5`. O 87 é o número vivo (94,565 % → "94,6 %"), mas `:876` diz "reduzido de 19 para 4", consistente com 88. Falta nomear a quinta lacuna |
| `67,6 %` + `9 %` | soma 76,6 %; os 23,4 % não têm nome nem destino, e "linhas do arquivo" nunca declara de quais arquivos |

**O achado que subordina os seis:** `grep -rl` por `152/167`, `16/55` e `67,6` em toda a árvore `rv-android` devolve o próprio plano, a auditoria e as análises externas — **não** o registro de validações que o §10 cita como fonte, nem CSV, nem script. Não há artefato contra o qual recalcular. A tabela do §10 é estimativa, e tem de ser rotulada como tal.

Contraste que isola o problema: a decomposição do §5.4 fecha exatamente (`26 + 28 + 19 + 19 = 92`) e o vetor `26/54/73/92` é coerente com ela. É o §10 que se solta.

### 2.12 A fronteira do parâmetro único deixa de ter custo zero durante a janela do componente

`openspec/changes/gh105-predicate-wiring/tasks.md` está em **36 de 74**. A tarefa **5.1**, aberta, cria `IvChainJunction.mop` (`SecureRandom → byte[] → IvParameterSpec → Cipher`), e a delta-spec é explícita (`specs/instrumentation/spec.md:740`): *"the wiring SHALL use a junction specification: **one multi-parameter JavaMOP specification per chain**"*. É a primeira spec multi-parâmetro do `jca_android` **por definição de mecanismo**, é a primeira das onze tarefas do Grupo 5, e as 5.4/5.9 preveem mais junções.

A tarefa **6.6**, também aberta, manda *"make the wider pointcut disjoint"* no par `f1`/`f2` do `CipherSpec`. Verificado no `fsm` (`:244-289`): `s2` não tem transição `f1`. Tornar `f2` disjunto faz o `doFinal()` nu disparar só `f1`, que em `s2` não transita — o monitor **rejeita**, e a direção `MOP \ regra` fica sem testemunha. Colateral: o §9 registra como reparo pendente que "`CipherSpec.f2` deveria mapear `{f1,f2,f4}`"; depois da 6.6, `{f2,f4}` passa a ser a resposta certa.

Também abertas e sobre o que o §9 mede: **5.3** (cria as duas primeiras leituras negadas do corpus — hoje `validateAbsent` tem **zero** *call sites* e o `MacSpec` não tem um único sítio `Property.`), **4.15** (hoje ainda há 17 sítios de `ObjectAsInAcceptingState` em 11 arquivos), **6.1–6.4** (a 6.4 apaga os 7 `remove()` em `@fail` — medido: exatamente 7).

### 2.13 O falso positivo do `GENERATED_KEY` é real e está subdimensionado

`ExecutionContext` e `PredicateStore` são armazéns disjuntos — o javadoc do segundo diz que *"exists **beside** `ExecutionContext` rather than replacing it because that class is frozen"*. `CipherSpec.mop:118-120` é uma leitura composta de três sondas no substrato novo:

| sonda | escritores do mesmo `Property` |
|---|---|
| `:118` `GENERATED_KEY` | 1 novo (`SecretKeySpecSpec.mop:153`) + **2 velhos** (`KeyGeneratorSpec.mop:80`, `KeyStoreSpec.mop:83`) |
| `:119` `GENERATED_PUBLIC_KEY` | **2 velhos, zero novos** (`KeyPairSpec.mop:32,:38`) |
| `:120` `GENERATED_PRIVATE_KEY` | **nenhum, em lugar nenhum** |

A única forma de responder `SATISFIED` hoje é uma chave construída à mão via `new SecretKeySpec(...)`. Ressalva de qualificação: o código separa deliberadamente `CIPHER-NOBS-00` de `CIPHER-CONSTR-00`, e `CipherSpec.mop:110-114` antecipa a leitura (*"NOT_OBSERVED says only that no producer of this key was ever observed, which on Android is as often a reach limit of the instrumentation as it is a misuse"*). Não é falso positivo de **violação**; é um report da família *not observed* disparado por uma causa que não é limite de alcance — é substrato errado. O Grupo 5 (5.5, 5.6) é quem fecha.

Irmã confirmada: `PBEKeySpecSpec.mop:108` valida `RANDOMIZED` sobre um `char[]`, e os seis escritores de `RANDOMIZED` ligam `int`, `SecureRandom` e `byte[]` — **nenhum `char[]`**. Como o `PredicateStore` é chaveado por identidade, não há nem coincidência de valor possível: o veredito é permanentemente `NOT_OBSERVED`.

### 2.14 O TSE 2023 já publicou a manchete que o §10.6 elege

`main.tex:1953` abre a subseção **"Inherent Limitation of RVSec"**, e `:1970-1974` traz um `tcolorbox`:

> *Main reason for RVSec's false negatives: It is hard to write RV specs to check if a variable was initialized to a hard-coded string constant.*

O `main.tex:2825` justifica a tradução tecnicamente (*"the rules are defined as EREs over method call sequences and JavaMOP has native support for ERE"*), e `:1471-1480` já aponta as specs faltantes para classes JCA pouco usadas como trabalho futuro.

O que **sobra de novo**, e é o que o §10.6 deveria elevar: as palavras `neverTypeOf`, `notHardCoded` como categoria, `IncompleteOperationError` e *monitorabilidade* não aparecem em nenhum `.tex` do paper; o TSE dá uma observação **qualitativa sobre um caso**, e o plano propõe uma **medida por corpus, por seção do CrySL, com `Unknown` contável** — diferente em espécie. E o achado sobre `IncompleteOperationError` é inteiramente novo e, notavelmente, limita o próprio comparador M2.

O título está cortado (`main.tex:87`: *Runtime Verification of Crypto APIs: **An Empirical Study***). E a alegação de lacuna é ampla demais: *tracematches* (Allan et al., OOPSLA 2005) compila padrão regular sobre traço **com variáveis livres** em monitores AspectJ, e PQL (Martin, Livshits & Lam, OOPSLA 2005) é uma linguagem com backends estático e dinâmico. O CogniCrypt já está em `references.bib:754` do próprio paper do grupo — mas o compilador CrySL → análise estática é descrito no **CrySL, ECOOP 2018**, não no ASE 2017; citar o paper certo.

---

## 3. Defeitos novos, descobertos pela verificação

Nenhuma das três revisões os tem. Vão para o §9 do plano.

| Onde | O quê | Consequência |
|---|---|---|
| `javamop/.../ast/mopspec/MOPParameters.java:41-51,84-94` | `add` descarta parâmetro cujo **nome** já existe; `getParam` compara só o nome, ignorando o tipo; sem log, sem exceção | 11 specs do `generic` perdem declarações, e o tipo sobrevivente na tupla de indexação pode não ser o que os eventos ligam (`FSM123` medido). Evento duplicado é detectado; parâmetro duplicado, não. |
| `jca_android/MacSpec.mop:143-147` e `jca/MacSpec.mop` | O evento `f2` declara `target(m)` sem `m` nas formais; `ajc` trata `m` como **nome de tipo** (`[warning] no match for this type name: m [Xlint:invalidAbsoluteTypeName]`) | O pointcut **nunca casa**. Como `f2` está no `ere`, todo programa que fecha um `Mac` com `doFinal(byte[],int)` é acusado de `MAC-ORDER-00`. É `MacSpec` 7/8, ausente da lista do §9. |
| `MetaCrySL/samples/jca/base/Cipher.cryptsl:79` | Usa `pre_plain_off + len`, mas `len` é ligado pelos `doFinal`; quem liga o comprimento do `update` é `pre_len` (declarado, ligado em `u3`/`u4`, usado por cláusula nenhuma) | A cláusula relaciona um buffer do `update` com um comprimento do `doFinal`. O upstream distinguia `prePlainTextLen` de `plainTextLen`. Imune a regeração. |
| `crysl.parsing.CrySLModelReader` | O vazamento de `OBJECTS` corre nos **dois** sentidos: `SecretKey.crysl` lido antes de `Key.crysl` quebra o `Key.crysl`, que sozinho carrega | O conjunto que carrega não é função do corpus: 29 a 31 conforme a ordem. Determinismo — e não denominador — é a razão certa para "um leitor por regra". |
| via AST EMF (`v5/V5.java`, `v6/LiftCrysl.java`) | Nenhum dos dois consulta `resource.getErrors()` nem `IResourceValidator` | `AlgorithmParameters` é lido com a implicação e o predicado **apagados em silêncio**, e a regra passa a exigir que o algoritmo seja BLOWFISH. |
| monitor gerado, `Prop_1_event_*` | O monitor é criado (`FindOrCreateEntry`) **antes** de a guarda ser avaliada | Uma `condition` reprovada deixa um monitor vivo no estado 0, e o evento seguinte é julgado dali. |
| `KeyPairSpec.mop:38` (efeito) | `GENERATED_PRIVATE_KEY` é **read-only** no conjunto: uma leitura (`CipherSpec.mop:120`), zero escritas em qualquer substrato | Consequência direta do defeito já registrado no §9 (o `gpr` grava sob a `Property` da pública). A tarefa 6.1 o conserta. |

---

## 4. O que continua sem verificação

Nenhum destes vira correção; todos vão para a lista do §13.

- **"12 de 23 specs absorvem uso incorreto"** (§2, §13) × "16 de 23" (gemini). Ninguém remediu nesta rodada.
- **`152/167` eventos que resolvem para assinatura única** × 155/167 (opus5). Exige resolver os 167 contra o `android.jar` da API 30; esta rodada mediu a aritmética, não a resolução.
- **"28 das 55 cláusulas mudam de veredito conforme a relação de igualdade"** (§10.3). O opus5 defende 35 e declara não ter derivado 28; ninguém arbitrou.
- **As 129 linhas de assinatura idênticas com e sem `android.jar`** (§8) — foram medidas com o leitor partilhado; precisam de remedição sob leitor novo.
- **`SSLContextSpec` e `TrustManagerFactorySpec`**, as outras duas falhas do gate, seguem sem análise.
- **Comportamento sobre APK real.** Tudo o que esta rodada executou foi JSE, com `ajc` e `rv-monitor-rt`. Nenhum emulador foi iniciado.

---

## 5. Decisões que ficam com o pesquisador

A premissa factual de cada uma foi medida; a escolha não é minha.

| # | Decisão | O que a medição já fixou |
|---|---|---|
| J1 | Um módulo e uma JVM, ou três processos com costura JSON | A JVM única funciona com uma linha de `<guava.version>`. A justificativa atual do §12 é falsa e sai de qualquer forma; se os três processos ficarem, o argumento passa a ser inspecionabilidade e isolamento. |
| J2 | Trocar a forma armazenada do `order` por autômato simbólico guardado sobre assinaturas, com `events` **ordenado** | 10 pares sobrepostos em `jca_android` e 26 no `jca`; `doFinal()` emite `f1 f2` e as duas letras acusam; a guarda mora a montante das tabelas. Sem isto, `CipherSpec`, `KeyGeneratorSpec` e `PBEKeySpecSpec` não têm veredito com significado. |
| J3 | Acrescentar M0 — vitalidade do monitor (indexa? tem sítio de acusação alcançável? o pointcut resolve?) | 5 specs globais, `MacSpec.f2` que nunca casa, `PBEKeySpecSpec:108` permanentemente `NOT_OBSERVED`. As três perguntas são decidíveis de artefatos que o desenho já produz. |
| J4 | Inventariar o arnês do gh104, ou promovê-lo a oráculo do M2 | O motor de replay, o isolamento por palavra e a distinção "não acusado × não replicado" já existem e estão testados; falta o enumerador e o mapa evento → chamada com argumentos. |
| J5 | Comparar contra dois oráculos (`api30` e `CrySL-Rules`) | Não é eixo novo — o teto do oráculo já é o terceiro eixo. O custo do pareamento é baixo (22/23, lendo `@see` e não o nome do arquivo); o custo real é a sintaxe. Os modos (2) e (3) têm zero ocorrências hoje. |
| J6 | Retargetar a moldura científica | A manchete escolhida está publicada em quadro destacado no TSE 2023 do próprio grupo. Sobrevivem a qualidade do oráculo e o resultado metodológico de que equivalência de `ORDER` é estritamente mais fraca que conformidade. |
| J7 | Java 21 em tudo, sem sobrescrever `scala.version` | A alternativa Scala 3 é incompatível com o `ptltl`, e o *nearest-wins* que a sustentava não ocorre. Nenhuma spec do corpus usa `ptltl`. |
