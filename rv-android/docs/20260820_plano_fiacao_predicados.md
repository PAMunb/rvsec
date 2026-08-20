# Fiação correta dos predicados CrySL nas specs JavaMOP `jca_android`

**Documento de ideação (Fase 0 do `docs/WORKFLOW.md`).** Não é artefato OpenSpec. Serve de
material de referência para a issue e a change que serão criadas a partir dele.

| campo | valor |
|---|---|
| data | 2026-08-20 |
| conjunto alvo | `rvsec/rvsec-mop/src/main/resources/jca_android/` |
| oráculo | `MetaCrySL/generated/api30/*.cryptsl` (33 regras) |
| antecessora | gh104 (`openspec/changes/gh104-legible-violation-reports/`), decisão **D-11** |
| ponto de medição | reator `rvsec` em `bd61abea` (reancorado 2026-08-20; coleta original em `d27c48e9`) |
| auditoria | `docs/20260820_auditoria_plano_predicados.md` — 47 alegações, 33 confirmadas |
| verificação v2 | `docs/20260820_verificacao_plano_predicados_v2.md` — 58 alegações, 4 reversões da 1ª auditoria, piloto do D4 executado |

> **Estado da reconferência.** As medições foram tomadas com a gh104 ativa em outra sessão, em
> `d27c48e9`, e reconferidas em `bd61abea` depois de os Grupos 8 e 9 aterrissarem. Os Grupos 8/9
> tocaram 12 dos 23 arquivos, mas **a distribuição de predicados é idêntica valor a valor nos dois
> pontos** — o gate G-PRED sustentou, e as contagens abaixo estão reancoradas ao `HEAD` atual.
>
> A auditoria refez cada medição com analisador estrutural em vez de regex, reproduziu os
> experimentos do gerador e do venn, e corrigiu dez números e três afirmações de semântica. As
> correções já estão aplicadas neste documento; onde o texto foi alterado, ele traz a marca
> **[auditado]**. Os dois achados que reordenam o plano estão em §7.3 (o custo do `@fail`) e
> §7.4 (`byte[]` não pode ser parâmetro de spec).
>
> **[auditado-v2]** Uma segunda passada (8 agentes paralelos, 2026-08-20) auditou a auditoria:
> reverteu quatro vereditos dela (as aridades do oráculo, o "teto 299" do venn, a atribuição do
> OOM do gerador e a alegação de que `-Xmx` destrava o `CipherSpec`), fechou os itens abertos do
> handoff e **executou o piloto da cadeia do IV** (D4). Onde o texto foi alterado por ela, a marca
> é **[auditado-v2]**. Registro: `docs/20260820_verificacao_plano_predicados_v2.md`; evidência:
> `audit/20260820_verificacao_plano_predicados_v2/`.

---

## 1. Enquadramento: esta change já foi nomeada

A gh104 não adiou este trabalho por omissão; ela o delimitou e declarou explicitamente, em
`design.md` D-11:

> *"Wiring the predicates correctly is a change of its own. It is the right repair and it is not
> attempted here. Its prerequisite is the instrument this change builds: the differential harness,
> which can size what a predicate edit adds and removes trace by trace. Attempting it before that
> instrument exists is what gh101 did."*

A gh104 fez três coisas que tornam esta change possível e que não se repetem aqui:

1. **Preservou o maquinário** — 134 linhas de `ExecutionContext` carregadas byte a byte do `jca`
   congelado, com o gate G-PRED invertido para asseverar *preservação*.
2. **Construiu o instrumento** — `scripts/gh104_diff_harness.py` (replay de traços por dois
   snapshots de conjunto, com classificação `unchanged`/`moved`/`removed`/`introduced`),
   `scripts/gh104_gates.py` (G-2, G-2a, G-2b', G-2c, G-2d, G-6', G-ERE, G-CONF, G-PRED),
   `scripts/gh104_message_gate.py`, o `TraceRunner` em `rvsec-mop` (escopo de teste) e 30+ traços
   versionados em `data/gh104/traces/`.
3. **Deu voz ao `@fail`** — envelope `v=1 code=… ev=… obj=… val=… exp=… msg='…'`, a macro
   `__EVENTNAME` emitida pelo gerador, e `codes.csv` com 49 códigos de falha.

O ponto 3 é o que torna esta change urgente e não apenas desejável: **a gh104 fez o `@fail` falar,
e o que ele diz continua errado.** A seção 3 mostra por quê.

---

## 2. O que foi medido

### 2.1 O grafo de predicados está desconectado

Contra as 33 regras api30 há **19 predicados conectáveis** — predicados que alguma regra assegura
e alguma regra exige. A implementação realiza **três**.

**[auditado] A unidade importa, e o plano a errava.** "19" conta *predicados*, não arestas. O
trabalho de fiação é por cláusula consumidora, e essas são **35**; contando
regra-produtora → regra-consumidora são **44**. **[auditado-v2]** A unidade exata: 35 é a contagem
de cláusulas `REQUIRES` conectáveis (36 − 1 de `preparedEC`); como pares distintos
(predicado, regra-consumidora) são **34**, porque `Mac.cryptsl` exige `encrypted` em duas
cláusulas — e cada cláusula é uma fiação distinta, então F3 continua dimensionada em 35 itens.
Um vigésimo predicado exigido, `preparedEC`, não
tem produtor em regra alguma. O número 3 (+1) das arestas realizadas está na mesma unidade de 19 e
é coerente — mas **F3 tem de ser dimensionada em 35 itens, não 19**.

| | valor |
|---|---|
| valores do enum `Property` | **25** [auditado] |
| valores **escritos** (`setProperty`) | 21, em 49 sítios |
| valores **lidos** (`validate`) | **4**, em 27 sítios |
| escritas sem consumidor algum | **18 valores, 35 sítios** [auditado] |
| lido sem produtor algum | `GENERATED_PRIVATE_KEY` (`CipherSpec.mop:85`) |
| documentado no enum, zero sítios | `MACED`, `GENERATED_CIPHER` [auditado] |

**[auditado]** A aritmética anterior (17 valores / 33 sítios) subtraía os **4** valores lidos dos 21
escritos, mas `GENERATED_PRIVATE_KEY` nunca é escrito — não pertence ao conjunto de onde se
subtrai. O correto é 21 − 3 = 18 valores e 49 − (9+3+2) = 35 sítios.

**[auditado]** `GENERATED_TRUST_MANAGERS` não tem zero sítios: tem um, e é pior que zero.
`TrustManagerFactorySpec.mop:101` chama `remove(Property.GENERATED_TRUST_MANAGERS)` — a sobrecarga
`@Deprecated`, que apaga a property para todos os objetos do processo — sobre uma property que
**ninguém escreve**. Só `MACED` e `GENERATED_CIPHER` são de fato inertes.

As quatro leituras vivas são `RANDOMIZED` (21 sítios), `GENERATED_KEY` (4),
`GENERATED_PUBLIC_KEY` (1) e `GENERATED_PRIVATE_KEY` (1, insatisfazível).

Consequências nomeadas:

- **A família `PREPARED_*` inteira é morta.** `PREPARED_IV`, `PREPARED_GCM`, `PREPARED_DH`,
  `PREPARED_HMAC` e `PREPARED_PBE` são escritas e nunca lidas. As regras api30 pedem
  `preparedIV[params]` e `preparedGCM[params]` no `Cipher` e `preparedHMAC[params]` no `Mac`.
  Ou seja: a classe inteira de misuse de *parameter spec* — IV estático, GCM reutilizado — é
  **falso negativo por construção**. `IvParameterSpec` e `GCMParameterSpecSpec` são as duas
  specs mais fiéis do conjunto e suas arestas morrem no consumidor.
- **`CipherSpec` implementa 1 das 6 cláusulas `REQUIRES` da sua regra, e a implementa errado.**
  A regra api30 pede `generatedKey[key, part(0,"/",transformation)]`, `randomized[ranGen]`,
  `preparedAlg[param, part(0,"/",transformation)]`, `!macced[_, plainText]` e as duas
  condicionais de IV/GCM. A `.mop` lê apenas `GENERATED_KEY`, unário, e acrescenta dois
  disjuntos que a regra não tem — um deles insatisfazível.
- **Todo o ramo TLS é decorativo.** `SSLContextSpec` é o único consumidor de
  `generatedKeyManager`, `generatedTrustManager` e `randomized[sr]` no oráculo, e não tem um
  único `validate`. A cadeia `generatedKeyStore → generatedKeyManager/TrustManager →
  generatedSSLContext` soma 7 escritas e 0 leituras.

### 2.2 Cinco eixos de infidelidade, todos enumeráveis

**E1 — Identidade.** `ExecutionContext` guarda `Map<Property, Set<Object>>` com `HashSet`, ou
seja, `equals()/hashCode()`. O rv-monitor indexa monitores por identidade — verificado em
`rv-monitor/rv-monitor-rt/.../rt/ref/CachedWeakReference.java:16`
(`System.identityHashCode(ref)`) e `.../rt/tablebase/WeakRefHashTable.java:474` (`if (key == this.ref)`).
As duas estruturas de indexação do mesmo sistema discordam sobre o que é "o mesmo objeto".

**E2 — Aridade.** As regras api30 declaram 54 `ENSURES` e 36 `REQUIRES` sobre 32 predicados.
**[auditado-v2]** A distribuição real de aridades é **59 unárias e 31 binárias — aridade máxima
2**. (A primeira auditoria registrou "2 quaternárias" e "`generatedKey` chega a aridade 4"; a
segunda passada mostrou que era artefato de contar as vírgulas internas do splitter
`part(0,"/",transformation)` em `Cipher.cryptsl:174,178`, que é **um** parâmetro CrySL — as seis
cláusulas `generatedKey[...]` são todas binárias.) O eixo continua real: **31 das 90 cláusulas
precisam de aridade ≥ 2** (`generatedKey[key, alg]`, `macced[M, D]`, `encrypted[c, p]`), enquanto
o enum é unário. Mas um terço não é "a maioria", e a F0 não pode justificar a aridade N com uma
severidade que a medição não sustenta. O Javadoc de `Property.MACED` admite a limitação por escrito.

**E3 — Momento.** O CrySL só garante um `ENSURES` no estado de aceitação do `ORDER` (ou nos
estados do `after L`). **42 das 49 escritas** ocorrem em corpo de evento; apenas 7 em `@match`.

**E4 — Forma da guarda.** **27 de 27** leituras estão dentro de `condition(...)`. Nenhuma está
em corpo de evento.

**E5 — Acusadores órfãos.** 17 eventos declarados estão fora do bloco `fsm`/`ere`, em 9 specs.
Eram 18 em 10 specs no `jca` congelado que produziu o dataset publicado; a gh104 reparou um
(`MessageDigestSpec.reset`).

### 2.3 A cadeia causal, verificada no monitor gerado

Os eixos E4 e E5 não são estilo: eles determinam o que o relatório diz. A prova está no
artefato gerado (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`):

**E4 — a guarda suprime a transição.** A leitura de predicado compila para um `return` antecipado,
antes do corpo e antes de `handleEvent`:

```java
final boolean Prop_1_event_i2(int mode, Key key, Cipher c) {
    if ( ! (ExecutionContext.instance().validate(Property.GENERATED_KEY, key)
         || ExecutionContext.instance().validate(Property.GENERATED_PUBLIC_KEY, key)
         || ExecutionContext.instance().validate(Property.GENERATED_PRIVATE_KEY, key)) ) {
        return false;                       // ← nenhuma transição, nenhum relato
    }
```

Um `Cipher.init` com chave que o monitor não viu gerar **desaparece do autômato**. O monitor fica
em `s1`; o `doFinal` seguinte encontra `Prop_1_transition_f2[3] == 5`, que é o estado de falha, e
o relatório sai como `CIPHER-ORDER-00 InvalidSequenceOfMethodCalls` — *"a sequência de chamadas
não é aceita"*. O desenvolvedor procura uma chamada que esqueceu. Não há nenhuma. A verdade era
"não modelamos a origem desta chave".

**E5 — o órfão manda todo estado para falha.** O gerador dá ao evento fora do autômato uma linha
de transição constante no índice de falha:

```java
static final int Prop_1_transition_reset[] = {4, 4, 4, 4, 4};
```

Então o acusador órfão emite o seu relatório correto **e** derruba o monitor, produzindo um
segundo registro `InvalidSequenceOfMethodCalls` e um `__RESET`. Assinatura empírica no dataset
publicado: `TrustManagerFactorySpec` marca 9.015 `InvalidSequenceOfMethodCalls` contra 9.014
`UnsafeAlgorithm`; em `SSLContextSpec`, `newSslSocketFactory` aparece 6.835 vezes de cada lado.
A gh101 dimensionou o total: **49.817 eventos = 70,4% de toda a categoria
`InvalidSequenceOfMethodCalls` e 51,3% do dataset publicado**.

**E5 também produz falso positivo puro.** `SecureRandomSpec` tem `next2` (`nextBytes(byte[])`)
no estado `init` e não no `end`:

```java
static final int Prop_1_transition_next1[] = {3, 1, 1, 3};   // nextInt: laço em 1
static final int Prop_1_transition_next2[] = {3, 3, 1, 3};   // nextBytes: de 1 vai para 3 = fail
```

Chamar `nextBytes()` duas vezes no mesmo `SecureRandom` é uma violação. Isso contradiz
diretamente o `ORDER` da regra api30, que é `Ins, Seeds?, Ends*` — estrela de Kleene. Custo
medido: 12.400 eventos (12,78% do dataset), 100% `InvalidSequenceOfMethodCalls`, 99,98% em
bibliotecas, com os maiores emissores sendo geradores de nonce em laço
(`kotlin.uuid.UuidKt__UuidJVMKt.secureRandomBytes`, `io.ktor.util.NonceKt`,
`com.google.crypto.tink.subtle.Random.randBytes`).

### 2.4 A conclusão que os números impõem

Dos 97.018 eventos publicados: 72,93% dizem apenas `unknown`; mais 9,11% dizem `but found .`;
sobram 17,84% acionáveis, dos quais 82,9% estão em código de terceiros. O núcleo atribuível a
código de aplicativo são **26 achados distintos**, e parte deles é falso positivo conhecido.

O ponto que reorganiza o trabalho: **as anomalias de mensagem e a fiação quebrada de predicados
não são dois problemas.** São o mesmo. A gh104 deu voz ao `@fail`; esta change tem de fazer o
`@fail` parar de disparar quando não deve, e fazer o `REQUIRES` violado acusar a si próprio.

---

## 3. A semântica do oráculo

O CryptoAnalysis existe em duas gerações com semânticas diferentes. As regras
`MetaCrySL/generated/api30/*.cryptsl` usam a **sintaxe antiga** (`FORBIDDEN:` com dois-pontos,
`neverTypeOf(a, T);;` com parênteses, `length(x) >= y`), logo o oráculo é a geração antiga —
`workspace-rv/CryptoAnalysis`. Isso não é detalhe: cinco pontos mudam entre as gerações.

| ponto | geração antiga (nosso oráculo) | geração nova |
|---|---|---|
| casamento de predicado | por **nome** apenas (`CrySLPredicate.equals`) | nome + aridade + negação |
| `REQUIRES` | **monotônico por objeto** — "ensured uma vez, vale sempre" | *flow-sensitive*, por ponto de programa |
| `NEGATES` | **no-op** — nenhum ponto do código remove um predicado emitido | máscara de estado |
| `ENSURES` condicional (`A => p`) | o resultado de CONSTRAINTS é **sobrescrito** pela avaliação de `A` | conjunção normal |
| valor não extraível **na comparação de predicado** | **cala-se a favor do programa**, não acusa | emite `ImpreciseValueExtractionError` |

**[auditado] Correção da última linha.** `ImpreciseValueExtractionError` **existe e é lançado** na
geração antiga — `ConstraintSolver.java:174` e `:484`. O que é verdade é mais estreito: os dois
sítios estão no caminho de **CONSTRAINTS**, não no de predicados. Em `doPredsMatch`, quando a
extração devolve conjunto vazio o laço não executa e `requiredPredicatesExist` permanece `true` —
silêncio a favor do programa, sem erro. A distinção importa porque é sobre predicados que esta
change opera.

Três consequências diretas para o plano:

1. **A globalidade do nosso `ExecutionContext` é fiel, não defeituosa.** Sob a geração antiga o
   predicado é um fato sobre um objeto, monotônico e válido em todo o programa. Escopar o
   predicado por monitor seria introduzir uma infidelidade nova. **O defeito é a identidade, não
   a globalidade** — é uma distinção que o enunciado do problema convida a errar.
2. **[auditado] Oito dos 9 `remove()` não traduzem cláusula nenhuma — nem `NEGATES`.** O oráculo
   inteiro tem **duas** cláusulas `NEGATES` (`SecretKey.cryptsl: generatedKey[this,_] after d` e
   `PBEKeySpec.cryptsl: speccedKey[this,_] after cP`), e `NEGATES` é no-op na geração antiga
   (`getNegatedPredicates` não é referenciado em ponto algum do analisador). Dos nossos 9
   `remove()`, **oito estão em `@fail`** e implementam *"desfazer o predicado quando o autômato
   falha"* — semântica que **não existe em nenhuma das duas gerações do CrySL**. Apenas
   `PBEKeySpecSpec.mop:74` (`remove(SPECCED_KEY, s)`) corresponde a uma cláusula `NEGATES`. Quatro
   deles usam ainda a sobrecarga `@Deprecated remove(Property)`, que apaga a property **inteira,
   para todos os objetos do processo** — uma única sequência malformada de `Mac` apaga a marca de
   todos os MACs já computados. Isso reformula o D3: ver §10.
3. **Em runtime somos estritamente mais fortes na comparação de valores.** O CogniCrypt compara
   por igualdade de string/inteiro *case-insensitive*, com *splitters* (`alg()`, `part(0,"/",t)`),
   e desiste quando não consegue extrair. Nós sempre temos o valor. Isso produz divergências
   **a nosso favor** que precisam ser contabilizadas como tais, não tratadas como bug.

E o achado central para a tradução, verificado em
`CryptoAnalysis/.../analysis/AnalysisSeedWithSpecification.java:475-519` e `:564-573`:

> **[auditado] A comparação por valor é decidida pelo TIPO da posição, não pela posição.**
> `doPredsMatch` itera de `i = 0` e pula toda posição cujo tipo declarado no bloco `OBJECTS` não
> esteja em `trackedTypes = {java.lang.String, int, java.lang.Integer}`. As posições sobreviventes
> são comparadas por igualdade textual *case-insensitive*, com *splitters* (`alg()`,
> `part(0,"/",t)`). O vínculo com o objeto vem do *seed* de dataflow (Boomerang) que carrega o
> predicado, não de uma posição privilegiada.

Na prática a posição 0 costuma ser um objeto e cai fora, o que faz a regra de bolso
"posição 0 = objeto, ≥1 = valor" funcionar quase sempre. Ela erra justamente nos casos desta
change:

- `macced[_, plainText]` — posição 1 é `byte[]`, **pulada**. O `!macced` do `Cipher` não compara
  valor nenhum.
- `encrypted[cipherText, plainText]` — ambas `byte[]`, ambas puladas.

Para esses, `doPredsMatch` degenera em *"existe algum predicado ensured com este nome"*, que é
exatamente o casamento por nome da primeira linha da tabela. **O oráculo é mais frouxo justamente
na família `byte[]`** — e é essa mesma família que o §7.4 mostra ser a difícil para nós.

O modelo correto é híbrido: **identidade no vínculo com o objeto, igualdade de valor apenas nas
posições de tipo `String`/`int`/`Integer`.** Nossa estrutura de dados usa igualdade em todas as
posições e projeta tudo para aridade 1 — erra nas duas pontas ao mesmo tempo.

---

## 4. A pergunta central: estamos apontando para o objeto certo?

Não. E a resposta tem quatro camadas, das quais só a primeira é o `equals`.

### 4.1 Chave por valor onde deveria ser identidade

Levantamento por tipo, verificado em `android-30/android.jar` (`javap -p`) e no fonte AOSP:

| tipo | `equals` | risco |
|---|---|---|
| `SecretKeySpec` | **VALOR** — aceita qualquer `SecretKey`, compara algoritmo *case-insensitive* e `MessageDigest.isEqual` do material | **colisão falso-negativa**: duas chaves distintas com o mesmo material são indistinguíveis |
| `ByteBuffer` | **VALOR e `hashCode` MUTÁVEL** — depende de `position()`/`limit()` | entrada fica em balde errado após um `flip()`: inalcançável e ineliminável |
| `String`, `Integer`, `Boolean` | VALOR, com internação/cache canônico | **identidade também não protege** |
| `byte[]`, `char[]`, arrays | IDENTIDADE (estável mesmo com preenchimento in-place) | ok para colisão |
| `IvParameterSpec`, `GCMParameterSpec`, `PBEParameterSpec`, `PBEKeySpec`, `DHGenParameterSpec` | IDENTIDADE — nenhuma declara override | ok |
| `Cipher`, `Mac`, `MessageDigest`, `SecureRandom`, `KeyStore`, `SSLContext`, … | IDENTIDADE | ok para colisão; vazamento |
| `Key`/`PublicKey`/`PrivateKey` concretas (Conscrypt, BouncyCastle) | **provavelmente VALOR** (módulo + expoente) | **a confirmar em dispositivo** |

Exemplo literal, hoje, em `SecureRandomSpec.mop:126`:

```java
event next1 before(SecureRandom r, int randIntInRange):
  call(public int SecureRandom.nextInt(int)) && args(randIntInRange) && target(r) {
     ExecutionContext.instance().setProperty(Property.RANDOMIZED, randIntInRange);
  }
```

Três defeitos empilhados: marca o **argumento** (o limite), não o resultado; o `int` sofre
autoboxing para `Integer`, cujo `valueOf` mantém cache de −128 a 127, de modo que `nextInt(16)`
marca a **instância canônica da JVM** para o processo inteiro; e nenhuma regra pede
`randomized` sobre inteiro. O arquivo carrega um `//TODO ... eh RANDOMIZED ou eh o retorno do
nextInt ???` desde sempre. Esta é a demonstração literal da preocupação: aqui nem é "outro objeto
do mesmo tipo" — é uma constante inteira de qualquer lugar do programa.

### 4.2 A clonagem defensiva do JCA — o eixo que a identidade *piora*

Este é o achado que muda a estratégia. Toda classe de spec do JCA clona na entrada **e** na saída:

| classe | entrada | saída |
|---|---|---|
| `IvParameterSpec` | `new byte[len]` + `arraycopy` | `getIV()` → `iv.clone()` |
| `SecretKeySpec` | `this.key = key.clone()` | `getEncoded()` → `key.clone()` |
| `GCMParameterSpec` | `arraycopy` | `getIV()` → `clone()` |
| `PBEKeySpec` | `.clone()` | `getPassword()` → `clone()` |
| `PBEParameterSpec` | `salt.clone()` | `getSalt()` → `clone()` |

A propagação de `RANDOMIZED` por identidade **sobrevive à entrada** — `args(iv)` liga o array do
chamador, que é o mesmo que `nextBytes` encheu — mas **não sobrevive à saída**. O idioma que
funciona é apenas o direto:

```java
byte[] iv = new byte[16];
sr.nextBytes(iv);              // marca ESTE array
new IvParameterSpec(iv);       // lê ESTE array → satisfeito
```

E falha em qualquer re-embrulho que passe por um getter, ou em
`SecretKey.getEncoded()` → `new SecretKeySpec(raw, alg)`, que é idioma comum de rederivação de
chave. Nesses casos o clone já é outro objeto, e **a troca para identidade não muda nada**.

O fundo do problema é que `randomized[x]` sobre um `byte[]` é *taint tracking*. O CrySL o resolve
com dataflow estático (Boomerang segue o `arraycopy`); runtime por identidade não segue. **21 das
27 leituras vivas são desta forma.** Nenhuma escolha de `Set` acompanha um valor através de
`System.arraycopy`.

**Escopo desta limitação — importante para não a usar em excesso.** Ela vale para o re-embrulho
feito pela **aplicação**, entre o produtor e o consumidor. Ela **não** vale para o clone que a
classe do JCA faz internamente, porque `args(iv)` liga o array do chamador nas duas pontas. E,
por incidir sobre a aplicação e não sobre o mecanismo, ela é **idêntica** para o store e para as
specs de junção da seção 7.4 — portanto é uma limitação declarada do conjunto, não um critério
de escolha entre os dois mecanismos. **[auditado-v2]** Isso não significa que nada distinga os
dois mecanismos: a assimetria real entre A e B é outra — `byte[]` não pode ser parâmetro de spec
(§7.5) — e é ela, não a clonagem, que decide a partição do D4.

### 4.3 O store global sem dono

- **`reset()` nunca é chamado em produção.** Os únicos chamadores em toda a árvore são testes
  JUnit e o harness offline da auditoria. Numa execução de 60 s sob Monkey, o contexto acumula do
  primeiro evento instrumentado até a morte do processo, com referências fortes.
- **`acceptingState` é write-only em produção**: 18 escritas em `@match`, **zero** leituras fora
  de `rvsec-agent/src/test/.../Assertions.java`. É exclusivamente um vazamento — um `HashSet` que
  retém todo `Cipher`, `Key`, `KeyStore` e `SSLContext` que alguma vez completou uma sequência.
- **`hasEnsuredPredicate(obj)`** devolve `true` se o objeto tem *qualquer* property. Não tem
  fidelidade nenhuma ao CrySL, que só sabe formular perguntas sobre predicados nomeados. Zero
  usos em produção; deve sair.
- **Nada é sincronizado**, em nenhuma camada: `HashMap`/`HashSet` simples, `instance()` com
  lazy-init sem `volatile`, e o monitor gerado tem zero ocorrências de `synchronized`.
  Contraste: `mop.Coverage` do caminho dexlib2 foi explicitamente tornado thread-safe com
  `ConcurrentHashMap.newKeySet()` (INV-INS-60) — o mesmo cuidado nunca chegou aqui. Cripto no
  Android raramente roda na main thread.

### 4.4 O precedente: a correção de identidade já foi feita e revertida

Isto **não é território novo**. A gh101 rechaveou o store por identidade em `233df18a`; três dias
depois foi revertido em `e204e2a4`, e a mensagem do commit diz por quê:

> *"Study 03 runs on the frozen `jca` set, which never asked for that semantics and inherited it
> by riding along in the same tree … Measuring the study with a substrate the freeze gate never
> inspected — **it checks the `.mop` files, not the classes they call** — is not an option."*

O registro `data/gh101/README.md:254-284` quantifica: **8 das 27 leituras mudam de resposta sob
identidade, e a direção é uniforme — todas as oito reportam mais, não menos.** As outras 19 são
sobre `byte[]`/`char[]` e não se movem.

**A lição arquitetural, e é a mais importante deste documento: um substrato compartilhado não
pode ter duas semânticas.** Enquanto `ExecutionContext` for uma classe única servindo o `jca`
congelado e o `jca_android` em evolução, qualquer correção nele quebra o congelamento.
**[auditado-v2]** A saída decidida (pesquisador, 2026-08-20; ver F0) é mais estrita que "uma
implementação por conjunto de specs": **classes novas ao lado das antigas, usadas apenas pelas
specs `jca_android`, com as antigas marcadas `@Deprecated` e literalmente não editadas** — o
congelamento fica protegido por construção, não por vigilância. O precedente de seleção pelo
`import` da spec já existe na gh104 (`CipherTransformationUtil` para `jca`,
`Api30CipherTransformationUtil` para `jca_android`).

---

## 5. Como garantir que a tradução está correta

O usuário formulou a pergunta certa: JavaMOP é método formal e tudo depende da corretude das
specs. A resposta honesta começa por um limite.

**Não existe prova de equivalência entre uma regra CrySL e uma spec JavaMOP, e não pode existir.**
O CrySL é estático, *flow-sensitive*, com points-to sobre o programa inteiro incluindo
bibliotecas. O JavaMOP é dinâmico, sobre o traço observado, restrito ao que foi tecido. Os dois
formalismos não têm o mesmo domínio. Qualquer afirmação de "tradução fiel" que não declare isso
é falsa.

O que se pode construir é uma escada de verificação, cada degrau mecanizado, com o que fica de
fora declarado. Proponho cinco.

### C1 — Conformidade sintática, derivada da regra (gate estático)

Extrair mecanicamente de cada regra api30 as seções `OBJECTS`, `EVENTS`, `ORDER`, `CONSTRAINTS`,
`REQUIRES`, `ENSURES`, `NEGATES`, `FORBIDDEN`, e comparar com a `.mop`. A gh104 já faz isso para
`CONSTRAINTS` (**[auditado]** `data/jca_android/constraint_table.csv`, 60 linhas — o
`conformance_record.csv` tem 74 linhas e trata de literais de allow-list). Faltam dois gates novos:

- **G-ORDER** — a linguagem aceita pelo `fsm`/`ere` é equivalente à do `ORDER` da regra. Ambos
  são expressões regulares, então **isto é decidível**: construir os dois AFDs e testar
  equivalência. Este gate teria pego `SecureRandomSpec.next2` sozinho, porque `Ends*` é estrela
  de Kleene e o `end` não tem a transição.
  **[auditado] Confirmado na gramática**: `CrySL.xtext:99-134` define `Order` como `Sequence` (`,`),
  `Alternative` (`|`), `Cardinality` (`*`, `+`, `?`) e `Primary` (átomo ou `( Order )`) — regular
  puro, sem interseção, complemento, contagem ou retro-referência; os agregados de `EVENTS`
  (`Gets := g1 | g2`) também são regulares. **A dificuldade real do G-ORDER não é a decidibilidade
  e sim o mapeamento de alfabeto** entre os eventos do `ORDER` e os da `.mop`, que separa
  sobrecargas para poder ligar parâmetros e portanto não é uma bijeção. Isso é o trabalho de fato
  e precisa ser orçado como tal.
- **G-PRED2** — toda cláusula `ENSURES` tem exatamente um sítio de escrita, no evento que a regra
  nomeia; toda cláusula `REQUIRES` tem exatamente um sítio de leitura, nos eventos que ligam a
  variável; e toda leitura tem um acusador.

### C2 — Fechamento do grafo de predicados (gate estático)

Todo predicado **lido** tem ao menos um produtor no conjunto; todo predicado **escrito** sem
consumidor é sinalizado. Hoje: 4 lidos contra 21 escritos, 1 lido sem produtor. Predicado lido
sem produtor é falso positivo garantido; escrito sem consumidor é código morto. É a checagem que
o antigo módulo `rvsec-mop-defsuses` tentava fazer em 2023 — ver seção 8.

### C3 — Oráculo de traços (o instrumento da gh104)

Cada cláusula `ENSURES`/`REQUIRES` ganha um **par de traços**: um que a satisfaz (não deve
acusar) e um que a viola (deve acusar, no evento certo, com o código certo). O `TraceRunner`
compila e reproduz; o harness diferencial mede A contra B e classifica
`unchanged`/`moved`/`removed`/`introduced`. Isto é o que a gh101 não tinha, e é o que decide
questões que a estatística agregada não decide.

Demonstração desse ponto, feita durante esta análise: testei a hipótese dos acusadores órfãos
contra o `errors.csv`. A co-ocorrência tipada↔ordem é universal (100% em todas as specs) e a
igualdade estrita de contagem discrimina bem em `TrustManagerFactorySpec` (99,7%) e
`SSLContextSpec` (89,5%) contra `CipherSpec`/`MacSpec` (0%) — mas `KeyStoreSpec` dá 78,1% sem ter
órfão. **O CSV agregado não decide.** Um único traço pelo `TraceRunner` decide, e a tabela de
transição gerada decidiu (seção 2.3).

### C4 — Oráculo diferencial contra o CogniCrypt

Temos `workspace-rv/CryptoAnalysis` local e `ase-journal/dataset/cognicrypt/`. Divergências
**categóricas** — "o CogniCrypt nunca reporta X e nós reportamos X em N registros" — são
evidência forte de defeito nosso. Duas ressalvas: as divergências previstas da seção 3 (somos
mais fortes onde ele se cala) devem ser descontadas antes; e o ponto de entrada Android do
CryptoAnalysis tem `return runCryptoAnalysis()` comentado no checkout atual, então a análise
precisa ser rodada pelo caminho JSE.

### C5 — Testes unitários de misuso conhecido

`ase-journal/dataset/results/errors_unit_tests.csv` (298 eventos, 32 APKs) e
`categoria_unit_tests.csv` (134 achados categorizados) são ground truth controlado. Toda spec
corrigida tem de continuar acusando o misuso plantado e parar de acusar o uso correto. Dado
relevante: o conjunto controlado produz **43 eventos `UnsatisfiedConstraint`** contra **zero** em
16.137 tarefas de campo — é o oráculo que exercita justamente os caminhos de constraint que a
exploração de GUI nunca alcança.

### O que fica declaradamente fora de qualquer garantia

1. **Alcance da instrumentação.** Tecemos o dex do app; o CogniCrypt analisa app + bibliotecas.
   Se o **produtor** de um predicado está fora do alcance, o predicado nunca é escrito e todo
   consumidor dentro do alcance é acusado. 88% das violações do dataset estão em código de
   terceiros.
2. **Taint através de cópia de array** (seção 4.2).
3. **Semântica *flow-sensitive*** — adotamos a monotônica da geração antiga, por fidelidade ao
   oráculo, e isso deve ser declarado.

### E daí a regra de projeto que falta hoje

Da limitação 1 sai o princípio que a primeira tentativa não tinha e que precisa entrar no design:

> **Um `REQUIRES` só pode acusar quando o monitor tem evidência de que teria visto o `ENSURES`
> correspondente. Na ausência dessa evidência, o veredito correto é "não observado", não
> "violado".**

A lógica de predicado em runtime é de **três valores** — satisfeito / violado / não-observado — e
não booleana. O `validate()` atual devolve `boolean` e colapsa "violado" com "não observado".
Isso é uma mudança de tipo de retorno, não de fiação, e é provavelmente a causa raiz nº 1 do
dilúvio de falsos positivos. O terceiro valor tem de chegar ao envelope da gh104 com código
próprio, para que a análise a jusante possa separá-lo.

**[auditado-v2] O custo, e onde ele fica confinado.** Trocar o retorno de `validate()` atingiria,
num substrato compartilhado, todos os 27 sítios de leitura — inclusive os do `jca` congelado — e
foi por isso que a auditoria o listou como reforço do R1. A decisão de F0 (classes novas;
`ExecutionContext` intocado) confina a assinatura de três valores à classe nova: os 27 sítios do
`jca` não são atingidos **por construção**, e os 27 de `jca_android` são reescritos de qualquer
forma por F2/F3. Nota estrutural que reforça a F2: `condition(...)` compila para guarda booleana,
então os três valores só são consumíveis no **corpo** do evento. Ficam duas tarefas explícitas:
(i) a assinatura de três valores nasce na classe nova da F0, nunca na antiga; (ii) o código de
"não observado" entra em `codes.csv` e no envelope da gh104 na mesma tarefa que introduzir a
primeira leitura de três valores.

---

## 6. O que se aprende com a tentativa falha

O conjunto `jca_android_bug_predicate` foi reprovado 22/22 pela auditoria de 2026-08-08. Mas a
auditoria reprovou **cláusula por cláusula, em 14 gates**, e o veredito global é a conjunção. A
partição dos 106 hunks:

| balde | hunks | veredito da auditoria |
|---|---|---|
| **(a) reparos estruturais de autômato** | 51 | `HELD` / `PROVADO` / *"PASS claims filed"* |
| **(c) re-orçamento do alfabeto** (Cipher 17→14 via `instanceof`) | ~21 | `FID` com duas ressalvas nomeadas |
| **(b) fiação de predicados** | 42 | **G7 FAIL**, 19 de 22 specs; 2 defeitos críticos introduzidos |

Medição independente que confirma o valor do balde (a): contando eventos declarados fora do
autômato,

```
jca                        18 órfãos em 10 specs
jca_android (hoje)         17 órfãos em  9 specs
jca_android_bug_predicate   0 órfãos em  0 specs
```

**A tentativa resolveu 100% de um defeito estrutural que segue em produção e que custa até 70,4%
da categoria `InvalidSequenceOfMethodCalls`.** O nome do diretório está certo sobre a causa da
reprovação e enganoso sobre o conteúdo.

Ela também **acertou a regra** que o conjunto atual viola por inteiro. Medição das leituras:

| conjunto | leituras | em `condition()` | no corpo |
|---|---:|---:|---:|
| `jca` (congelado) | 27 | **27 (100%)** | 0 |
| `jca_android` (hoje) | 27 | **27 (100%)** | 0 |
| `jca_android_bug_predicate` | 56 | 33 | **23** |

Das 29 leituras novas da tentativa, 23 estão no corpo do evento, com helpers dedicados
(`reportUnrandomized`, `reportUnpreparedParams`, `reportMacedPlainText`) e o comentário
explicando o porquê. O que ela **não** fez foi retrofitar as 27 herdadas — e são exatamente essas
que produziram as críticas da auditoria.

### Regras acionáveis

1. **Predicado nunca entra em `condition(...)`.** Guarda falsa não transita; o evento sai do
   autômato e a chamada seguinte é acusada de ordem. Leitura de `REQUIRES` vai no **corpo**,
   reportando `UnsatisfiedConstraint`. `condition()` fica reservado a discriminar sobrecargas e
   ramos do `ORDER`. Isso reflete a ortogonalidade do próprio CrySL, onde `ORDER` e `REQUIRES`
   são seções distintas: violar um `REQUIRES` **não** muda o typestate.
2. **Nunca declarar um evento fora do `fsm`/`ere`.** O gerador lhe dá uma linha toda-`fail`.
   Todo acusador precisa de laço no autômato.
3. **Nunca adicionar leitura sem o produtor modelado no mesmo conjunto e na mesma tarefa.**
   `validate` de chave ausente devolve `false`, então leitor sem produtor acusa toda chamada
   conforme.
4. **Nunca consertar binding sem colocar o evento no autômato na mesma edição** — converte evento
   morto em acusador incondicional.
5. **Nunca mudar código Java compartilhado achando que o portão de congelamento cobre.** O gate
   do `jca` verifica `.mop`, não as classes que eles chamam.
6. **[auditado-v2] O alfabeto é recurso escasso — mas o teto real é 18, e é do parser, não da
   heap.** Ver seção 7.3: o custo é `n × (2ⁿ − 1)` exato, disparado pela presença de `@fail`;
   17 eventos geram até com `-Xmx1g`, e o bloqueio em 18 é `StackOverflowError` no
   `EnableSet.parseSets` do processo pai, insanável por flag. Gerar o monitor no pipeline real
   antes de aceitar o alfabeto continua valendo; concluir que 17 é um limite, não.
7. **"Reparar é caro" não implica "remover é barato"** — as duas afirmações precisam de medições
   distintas (é a própria D-11).

---

## 7. Plano proposto

### 7.1 Princípio de ordenação

Ordenar pelo **grafo de predicados em ordem topológica**, não por arquivo. O grafo tem raiz
(`randomized`, produzido por `SecureRandom`), meio (`generatedKey`, `speccedKey`, `prepared*`) e
folhas (consumidores em `Cipher`, `Mac`, `Signature`). Um defeito na raiz cascateia. Uma aresta
por vez, com o par de traços de C3 e o delta do harness registrado. Isso dá granularidade natural
e critério de parada por aresta.

### 7.2 Fases

**F0 — Substrato (pré-requisito de tudo).** Não reparar o `ExecutionContext`: **escrever classes
novas ao lado dele**, usadas apenas pelas specs `jca_android`, e marcar as antigas como
`@Deprecated` — sem removê-las e **sem alterá-las** — até que uma change futura faça as migrações.
*(Decisão do pesquisador, 2026-08-20; substitui a formulação anterior "uma implementação por
conjunto de specs".)*

A API nova precisa de: chave híbrida (identidade no vínculo com o objeto, valor nas posições de
tipo `String`/`int`/`Integer`, *case-insensitive*, com *splitters*), aridade N, retorno de **três
valores**, chaves fracas com expurgo, e thread-safety (`ConcurrentHashMap` + `newKeySet()`,
`instance()` com holder estático). `hasEnsuredPredicate` e a sobrecarga `remove(Property)`
**não são oferecidas** pela classe nova — o que é ausência, não remoção, e não quebra ninguém.

**Por que isto resolve o R1 por construção.** Se a classe antiga não é tocada, o congelamento do
`jca` não pode ser quebrado por acidente — nem pelo caminho que já falhou uma vez (`233df18a`,
revertido em `e204e2a4`), que era exatamente mudar a classe compartilhada achando que o gate do
`jca` cobria. E o custo é baixo porque o levantamento mostra que **`generic` e `generic_new` não
chamam `ExecutionContext` em spec alguma**: depois da migração de `jca_android`, os únicos
consumidores da classe antiga são o conjunto congelado e o arquivado, ambos read-only por
política. Não há adaptador, não há shim, e o P3 não é violado — a classe antiga continua **viva**,
servindo o `jca`, e `@Deprecated` é sinalização de intenção, não compatibilidade retroativa.

**Consequência a orçar:** o gate G-PRED da gh104 assevera preservação byte a byte do maquinário de
predicados. Quando `jca_android` passar a chamar outra classe, ele deixa de fazer sentido na forma
atual e **precisa ser reformulado** — provavelmente para asseverar a preservação sobre o `jca` e a
equivalência semântica sobre o `jca_android`. **[auditado-v2] Dimensionamento: médio, não uma
linha.** G-PRED continua como cadeado do `jca`; para `jca_android` ele é aposentado e substituído
por G-PRED2 + `predicate_graph.csv` (F5). Dano colateral fora do G-PRED, a orçar junto:
`accept_requires` (`gh104_gates.py:1189-1191`) decide o G-2 grepando `ExecutionContext` e daria
falsos vermelhos; a regex `PREDICATE_CALL` (`:514-517`) é cega para a classe nova e para aridade
N; o pytest de INV-INS-128 (censo de 134 linhas) precisa ser reescrito; e a política do
`divergence_record`/INV-INS-118 para as ~134 linhas reescritas precisa ser decidida.

**[auditado-v2] F0 é condicionado pela decisão das seções 7.4–7.6, que o piloto da cadeia do IV
decide (D4).** O piloto, portanto, precede o dimensionamento final de F0. Se as specs de junção —
com o idioma `Object` e o G-PARAM — cobrirem a maior parte do grafo, o store deixa de ser o
mecanismo principal e F0 encolhe para o que sobrar: posições de valor, arestas sem cadeia
observável e o retorno de três valores, que permanece necessário em qualquer partição (§5). F1
independe dessa decisão e pode andar em paralelo; F2 é afetada só na margem — uma leitura que F3
venha a substituir por spec de junção deixa de existir, mas movê-la antes para o corpo não é
trabalho perdido, porque o acusador e o código em `codes.csv` migram com ela.

**F1 — Autômatos (resgate do balde (a)).** Absorver os 17 acusadores órfãos. É a mudança de maior
retorno por unidade de risco: já foi feita, já foi examinada e aprovada, e o defeito está
quantificado. Cada absorção medida pelo harness. Atenção ao resíduo já registrado
(`FEN-PBK-RESIDUO` / gh101 D-S9): o prefixo Kleene resolve o `@fail` no evento violador mas não
absorve chamadas obrigatórias que o sucedam — `PBEKeySpec.cP` é o caso.

**F2 — Forma da guarda.** Mover as 27 leituras de `condition()` para o corpo, cada uma com o seu
acusador e o seu código em `codes.csv`. Hoje há 9 sítios `CONSTR`; faltam 8 leituras positivas
sem acusador algum (`CipherSpec.i2`, `GCMParameterSpecSpec.c1/c2`, `MacSpec.i1/i2`,
`RandomStringPassword.vo/gb`, `SecretKeySpec.e1`).

**F3 — Fiação, em ordem topológica.** Aresta por aresta, da raiz às folhas. Prioridade pelo custo
medido: `randomized` (hub, 21 leituras), depois `generatedKey` com a segunda posição,
depois a família `prepared*` que fecha `Cipher`. Cada aresta entra com produtor + consumidor +
acusador + par de traços na mesma tarefa. **[auditado] Dimensionamento: 35 itens** — pares
(predicado, regra-consumidora) — e não 19, que é a contagem de *predicados* conectáveis. Ver §2.1.
Note também que o hub `randomized` é justamente a família `byte[]` do §7.5: ele deve entrar
**depois** de o piloto da cadeia do IV ter decidido o mecanismo.

**F4 — Defeitos pontuais** que a análise localizou e que independem do resto:
`KeyPairSpec.mop:38` (chave privada gravada em `GENERATED_PUBLIC_KEY`);
`TrustManagerFactorySpec.mop:74-78` (property errada + pointcut com retorno `KeyManager[]` +
parâmetro `TrustManager[][]`); `SignatureSpec` (`verified` marcado no `boolean` em vez do
`byte[]`; pointcuts de `sign()` declarando `public byte`);
`SecretKeySpec.mop:26` (a conflação `preparedKeyMaterial ≡ RANDOMIZED`);
`SecureRandomSpec.next1/next3` (marca do argumento autoboxado);
`SecureRandomSpec` `end` sem `next2`.

**F5 — Registro e gates.** `predicate_graph.csv` como irmão do `constraint_table.csv`
**[auditado-v2]**; gates
G-ORDER, G-PRED2, G-ACC (todo acusador tem laço no autômato) e **[auditado] G-PARAM** (a lista de
parâmetros da `.mop` sobrevive íntegra no `.rvm` — §7.5) na suíte pytest existente. Todos os
quatro têm de satisfazer o contrato de genericidade da §8-bis: rodam sobre os 214 `.mop`, pulam
declaradamente o que não se aplica, e contam o que pularam.

### 7.3 O teto do gerador, medido — e por que ele não é 17

`CipherSpec` tem 17 eventos, e as cinco cláusulas `REQUIRES` ausentes exigem ligar `params`,
`param` e `ranGen`, o que os pointcuts atuais não fazem. Ligar exige separar sobrecargas, o que
gasta eventos. A gh101 registrou um "teto de 17" (INV-INS-115) e a gh104 o herdou como restrição
dura (`design.md:139`: *"no task may add a `Cipher` event without removing one"*).

**A restrição é real; o número não é uma constante.** Executando `FSMCoenables` diretamente:

| n | entradas medidas | `n·(2ⁿ−1)` | tempo |
|---:|---:|---:|---:|
| 14 | 229.362 | 229.362 | 3,0 s |
| 16 | 1.048.560 | 1.048.560 | 15,5 s |
| **17** | **2.228.207** | **2.228.207** | **36,2 s** |
| 18 | 4.718.574 | 4.718.574 | 88,9 s **[auditado-v2:** no driver isolado, 22,7 s sob `-Xmx2g` — a nota original "só com 24 GB" não se reproduz; ver consequência 1**]** |

Igualdade dígito a dígito: a fórmula é o valor **exato atingido**, não uma cota. Sobre a
`CipherSpec` real (17 eventos, 6 estados), a categoria `fail` produz 2.228.207 entradas contra
**354** da categoria `match1` — razão de 6.294×, e o `toString()` devolvido pelo subprocesso tem
82,4 milhões de caracteres.

**[auditado] `@fail` não é o gatilho do custo — é o custo inteiro.** Reexecutando o
`FSMCoenables` com e sem `fail` na lista de categorias, tudo o mais igual:

| n | com `fail` | sem `fail` |
|---:|---:|---:|
| 14 | 229.362 entradas, 1,3 s | 10 entradas, 2 ms |
| 17 | 2.228.207 entradas, 11,0 s | 10 entradas, 2 ms |
| 18 | 4.718.574 entradas, 23,7 s | 10 entradas, 2 ms |

Cinco ordens de grandeza. O mecanismo está em `FSMCoenables.computeCoenables`: o caminho é um
`HashSet<Symbol>`, ou seja um **subconjunto do alfabeto**, e `fail` é absorvente com auto-laço em
todos os símbolos — a busca reversa a partir dele enumera os 2ⁿ−1 subconjuntos não vazios para
cada um dos n eventos. Nenhuma outra categoria tem essa forma. **O teto de alfabeto é um artefato
exclusivo do `@fail`**, e isso amplia o leque de alavancas: além de `-Xmx` e do re-orçamento,
existe a pergunta — que esta change não precisa responder, mas deve registrar — de quanto do
`@fail` é indispensável em cada spec.

Três consequências que mudam o plano:

1. **[auditado-v2] O teto real: 17 nunca foi bloqueio, e 18 é teto duro do parser — não da heap.**
   A segunda passada mediu o **pipeline completo** (`rvj.Main` → filho `logicrepository.Main`; o
   javamop está fora deste caminho): o `CipherSpec` real de 17 eventos **gera em toda
   configuração**, inclusive com `-Xmx1g` no pai e no filho (~53 s) — o "teto de 17" nunca
   bloqueou a viabilidade, e **o re-orçamento 17→14 não é necessário para viabilidade**. Em n=18
   o modo dominante de falha **não é OOM**: é `StackOverflowError` no processo **pai**, no regex
   de `EnableSet.parseSets` (`EnableSet.java:66-116`), com qualquer heap (1g/2g/24g/default) — e
   `-Xss` já está no máximo que a JVM aceita. **n=18 não é destravável por flag nenhuma**; as
   únicas alavancas são patch em `parseSets` ou supressão dos coenables de `fail`. O OOM verídico
   existe apenas no **filho** com heap < ~2 GB — relevante porque o launcher **não passa `-Xmx`**
   (`LogicRepositoryConnector.java:149-156` e `rv-monitor/src/main/scripts/bin/rv-monitor:34`
   passam apenas `-Xss1g`), a heap efetiva é o default do HotSpot (¼ da RAM física) e portanto
   **varia por máquina**: numa máquina pequena o filho estoura e a falha é mascarada (ver R5 —
   reproduzido ao vivo). Busca exaustiva por limite hard-coded no caminho FSM: não existe. Toda
   tarefa que toque `Cipher` deve medir no pipeline real e registrar a heap. O re-orçamento do
   balde (c) (17→14 via `instanceof`) fica como alavanca de **desempenho/portabilidade**, não de
   viabilidade, com as suas duas ressalvas nomeadas — `instanceof` testa tipo dinâmico enquanto o
   overload é estático, e terceiro argumento `null` cai fora dos dois ramos.
2. **Não há chave de desligamento.** `--noopt1` age no *consumo* (`EnableSet.java:121-125`),
   dentro do gerador, depois de o subprocesso já ter gasto o tempo e a heap; e
   `OptimizedCoenableSet.optimize()` lê `contents` direto, sem passar por `getEnable()`. `ere`
   paga o mesmo que `fsm` (`EREPlugin` converte e não marca `"done"`). A única alavanca sobre o
   custo é o número de eventos, a presença de `@fail` e a heap.
3. **A falha é mascarada** — ver R5.

---

### 7.4 A decisão de arquitetura: store novo ou specs de junção? [auditado-v2]

Há dois mecanismos possíveis para ligar um predicado, e a escolha entre eles é **a** decisão de
projeto desta change.

**Mecanismo A — store novo (F0).** **[auditado-v2]** A classe nova da F0 — chave híbrida,
aridade N, três valores — chamada pelas specs `jca_android` no lugar do `ExecutionContext`, que
fica intocado. Vantagem: nenhuma spec nova, o alfabeto não é tocado. Desvantagem: a identidade é
responsabilidade nossa e discorda da que o JavaMOP usa para indexar monitores.

**Mecanismo B — specs de junção multiparamétricas.** Uma aresta de predicado CrySL **é** um elo
de parâmetro do JavaMOP: `ENSURES p[x]` no produtor e `REQUIRES p[x]` no consumidor significam
que existe uma chamada que entrega `x` de um ao outro, e essa chamada é exatamente o evento que
liga os dois parâmetros.

Isto é primeira classe no JavaMOP, e o repositório carrega o exemplo canônico —
`javamop/examples/agent/many/rvm/ere/SafeSyncMap.mop`:

```
SafeSyncMap(Map syncMap, Set+ mapSet, Iterator iter) {
   creation event sync  after() returning(Map syncMap) : call(* Collections.synchr*(..))
   event createSet      after(Map syncMap) returning(Set+ mapSet) : call(* Map+.keySet()) && target(syncMap)
   event syncCreateIter after(Set+ mapSet) returning(Iterator iter) : call(* Collection+.iterator()) && target(mapSet)
   event accessIter     before(Iterator iter) : call(* Iterator.*(..)) && target(iter)
   ere : sync createSet (asyncCreateIter | (syncCreateIter accessIter))
}
```

Três objetos de três classes diferentes, relacionados **transitivamente** por eventos que ligam
subconjuntos sobrepostos. O runtime tem maquinaria dedicada por aridade — `IndexingTree1.java`,
`IndexingTree2.java`, `IndexingTree3.java` — mais `AbstractPartitionedMonitorSet` para as
ligações parciais.

A cadeia do IV, hoje três predicados mortos, tem a mesma forma:

```
IvChainSpec(SecureRandom r, byte[] iv, IvParameterSpec spec, Cipher c)
   gen : SecureRandom.nextBytes(iv)            → liga (r, iv)
   mk  : new IvParameterSpec(iv)               → liga (iv, spec)
   use : Cipher.init(mode, key, spec)          → liga (spec, c)
```

**[auditado-v2] Atenção: como escrita, esta assinatura não compila para o que se descreve.**
`byte[]` na lista de parâmetros faz o JavaMOP apagar a lista inteira e emitir um monitor global,
em silêncio (§7.5). A forma viável declara `iv` como `Object` e o liga no pointcut contra o
argumento `byte[]`. A vantagem e o custo discutidos a seguir valem para essa forma — e é
exatamente por isso que o piloto do D4 é esta cadeia.

**Vantagem decisiva: a identidade passa a ser garantida pelo próprio mecanismo do JavaMOP** — o
mesmo `System.identityHashCode` + `==` do `CachedWeakReference`. Sem `equals`, sem vazamento
(referências fracas mais `TerminatedMonitorCleaner`), sem aridade projetada, e as duas estruturas
de indexação do sistema passam a concordar sobre o que é "o mesmo objeto". O custo é baixo:
*k*=4 dá `2⁴−1 = 15` entradas de *enable set* e `3⁴ = 81` por evento no simplificador, e com
n≈6 eventos o coenable é 378 contra os 2.228.207 do `CipherSpec`.

**Correção de um argumento que este documento fazia contra B.** Uma versão anterior afirmava que
a clonagem defensiva da seção 4.2 inviabilizava a cadeia. Não inviabiliza: o clone acontece
**dentro** da classe do JCA, e `args(iv)` liga o array **do chamador** nas duas pontas. A cadeia
só quebra se a aplicação refizer o array por um getter entre as duas chamadas — limitação
idêntica para o mecanismo A, portanto neutra na comparação.

**O que é genuinamente difícil em B**, e precisa ser resolvido no design:

1. **Evento de criação.** Se o traço observado começa no consumidor sem a cadeia anterior — que é
   exatamente o caso violador — nenhum monitor é criado e ninguém acusa. Acusar a ausência exige
   que o evento consumidor também seja criador, produzindo um monitor parcial que possa ser
   julgado. É o ponto onde uma tradução ingênua fica silenciosa.
2. **Coexistência com as specs-base.** `CipherSpec` já observa `init`; uma spec de junção que
   também o observe põe dois monitores no mesmo *joinpoint*. Semanticamente correto, mas exige
   disciplina para não relatar duas vezes.
3. **Volume.** **[auditado]** São **35 pares (predicado, regra-consumidora)** sobre 19 predicados
   conectáveis; agrupados por cadeia, algo como 8 a 12 specs de junção novas — cada uma pequena,
   mas é superfície nova a manter e a tecer.
4. **Posições de valor.** O `alg` de `generatedKey[key, alg]` não é objeto e não pode ser
   parâmetro; vai comparado no corpo do evento, que é o que o CrySL faz de qualquer modo.
5. **`byte[]` como parâmetro de spec — [auditado] O TESTE FOI FEITO E REPROVOU.** Ver §7.5. É o
   achado que reordena esta seção.

---

### 7.5 [auditado] `byte[]` não pode ser parâmetro de spec, e a falha é silenciosa

Matriz medida, mesma spec de três eventos, variando só o tipo do parâmetro do meio:

| tipo declarado na `.mop` | lista de parâmetros no `.rvm` gerado |
|---|---|
| `byte[]` | `TByteArr()` — **vazia** |
| `int[]` | `TIntArr()` — **vazia** |
| `Object[]` | `TObjArr(SecureRandom r, Object[] b)` — preservada |
| `Object` | `TObj(SecureRandom r, Object b)` — preservada |
| `String` | `TString(SecureRandom r, String b)` — preservada |

Controle com o exemplo canônico: `SafeSyncMap(Map, Set+, Iterator)` preserva os três.

**Um array de tipo primitivo apaga a lista de parâmetros inteira** — não apenas o parâmetro
ofensor. O JavaMOP conclui com `rc=0` e a mensagem normal `"… .rvm is generated"`: nenhum aviso,
nenhum erro, nenhum código de saída diferente.

A consequência a jusante é total. Rodando o rv-monitor sobre os dois `.rvm`:

| spec | indexação gerada |
|---|---|
| `TObj` (parâmetro `Object`) | `CachedWeakReference wr_b = new CachedWeakReference(b)` — fatiamento real por objeto |
| `TByteArr` (parâmetro `byte[]`) | **zero** `CachedWeakReference`, zero `IndexingTree` — um monitor global |

**Por que isto reordena a decisão.** A `IvChainSpec(SecureRandom r, byte[] iv, IvParameterSpec
spec, Cipher c)` desenhada acima não compila para o que esta seção descreve: compila para um
monitor único e global — exatamente o defeito que o mecanismo B deveria curar. E a família
atingida é a maior do conjunto: `randomized` sobre `byte[]` são **21 das 27 leituras vivas**, mais
`char[]` no `PBEKeySpec`.

**O contorno existe e funciona.** Declarar o parâmetro como `Object` e ligá-lo no pointcut contra
o argumento `byte[]` preserva a lista e produz indexação por identidade genuína — foi o caso
`TObj` acima, cujo pointcut é `call(void SecureRandom.nextBytes(byte[])) && args(b)` com
`Object b`. O mecanismo B **é** viável para a família `byte[]`, mas apenas através de um idioma de
declaração não óbvio, que precisa estar escrito no design e travado por gate.

**[auditado-v2] Segunda passada — `char[]`, a causa raiz e o silêncio.** `char[]` foi medido e
colapsa igual (atinge o `PBEKeySpec`). A causa raiz está localizada: assimetria de gramática +
catch silencioso, **duplicada nos dois tradutores** — `javamop.jj:1456` (`SimpleTypePattern()`,
parâmetros de spec, aceita só identificadores na cabeça do tipo, enquanto o `TypePattern()` dos
eventos em `:1470` aceita as keywords primitivas — por isso os eventos preservam `byte[]` e a
spec não) e `JavaParserAdapter.convertParameters()` (`javamop/.../JavaParserAdapter.java:320-327`,
`catch (Exception) { return null; }` com o `printStackTrace` comentado); espelho exato no
rv-monitor (`RVMonitorParser.jj:876` + `rvj/JavaParserAdapter.java:233-240`). **Correção barata
existe, mas exige patch duplo** — javamop **e** rv-monitor, porque o rv-monitor re-parseia o
`.rvm` e colapsa de novo: um ramo de primitivo-array em ambos os `SimpleTypePattern()` e relançar
a exceção. Há precedente de patch local (o descritor JSON do javamop); a decisão é do pesquisador
— o contorno `Object` funciona sem ele, mas o enquadramento muda: **a limitação é de toolchain
reparável, não semântica**. Dois refinamentos operacionais: o rc do javamop é inútil como gate
(até parse error duro de pointcut sai com rc=0 — o G-PARAM inspeciona o artefato, nunca o código
de saída); e o idioma `Object` exige **fixar o overload na assinatura do `call(...)`**, porque
`args(b)` com `Object` casa qualquer argumento, inclusive autoboxing.

**Gate novo — G-PARAM.** A lista de parâmetros da `.mop` tem de sobreviver íntegra no `.rvm`. É
uma comparação de duas linhas e pega uma classe de falha que hoje é inteiramente muda. Entra na
F5 junto com G-ORDER, G-PRED2 e G-ACC.

---

### 7.6 [auditado] Recomendação revista sobre o mecanismo

**Híbrido continua certo, mas B não pode ser o padrão.** A partição é determinada pelo tipo dos
objetos da cadeia, não por preferência:

- **Cadeias de tipos-objeto** — `KeyStore → KeyManagerFactory/TrustManagerFactory → SSLContext`,
  `KeyPair → Signature`, `Mac`/`Key`: mecanismo B, direto.
- **Cadeias que passam por `byte[]`/`char[]`** — toda a família `randomized`, mais `preparedIV`,
  `preparedGCM` e `preparedKeyMaterial`, que é a maioria das leituras vivas: mecanismo B **só** com
  o idioma `Object` e o gate G-PARAM, ou mecanismo A.
- **Posições de valor** (`alg`, `part(0,"/",transformation)`): sempre no corpo do evento — é o que
  o oráculo faz de qualquer modo, e §3 mostra que ele só compara `String`/`int`/`Integer`.

**O piloto passa a ser a cadeia do IV, não `Mac`/`Key`.** `Mac` e `Key` são ambos tipos-objeto: o
piloto passaria, B seria adotado como padrão, e a falha apareceria depois, em silêncio, em toda
cadeia que tocasse `byte[]`. **Um piloto que só sabe passar não decide nada.** A cadeia do IV é o
caso difícil e é a única que separa os dois mecanismos; `Mac`/`Key` serve como controle positivo.

**Duas notas de comparação.** A limitação 1 da seção 5 (alcance da instrumentação) é idêntica nos
dois mecanismos e não entra na comparação — assim como a clonagem defensiva da §4.2. O que **não**
é neutro é esta seção 7.5: ela é uma assimetria real entre A e B, e é a única que a auditoria
encontrou.

**Um argumento a favor de B que este documento não usava.** As specs `generic` já são
multiparamétricas em escala — 40 com *k*=2, 30 com *k*=3, 17 com *k*=4, 6 com *k*=5 e 4 com *k*=6,
ou 82% das 118. O mecanismo é neutro quanto ao domínio e está exercitado no próprio repositório
muito além do *k*=4 aqui proposto.

---

## 8. `rvsec-mop-defsuses`: aposentar, promovendo a ideia

O módulo parseia `.mop` com o parser real do JavaMOP e imprime `DEFINES`/`USES` de `Property` em
PlantUML. A saída de 2023 já mostrava `CipherSpec` usando `GENERATED_PRIVATE_KEY` sem produtor.
A ideia é exatamente o gate C2. O código, porém, não a serve:

- `PropertyExtractor` pega `getArguments().get(0)` — a `Property` — e **descarta o argumento 1**,
  que é o objeto, o cerne de toda esta análise.
- `explore(Expression)` só despacha `BinaryExpr` e `MethodCallExpr`; `!validate(...)` é
  `UnaryExpr` e cai fora. **Todas as leituras negadas são invisíveis** — justamente os acusadores.
- Não sabe nada do autômato, logo não vê os 17 órfãos.
- Sem tipos (o symbol-solver está no `pom.xml` e não é usado), sem aridade, sem espécie de sítio.
- **[auditado-v2]** o `main()` com caminho absoluto existe — em `DefsUsesGraph.java:65-66`, não
  em `MOPSpecDefsUses.java` (modelo de dados, sem `main`; por isso a primeira auditoria não o
  localizou) — apontando para a raiz de `resources` via o alias `/pedro/...`, que nem resolve na
  JVM; e como `listFiles()` não desce (l.23), encontraria zero arquivos de qualquer forma —
  diagrama vazio. Está no `<modules>` do reator, sem consumidor algum, e o histórico inteiro no
  git é bump de versão e chore de documentação.

O argumento decisivo é arquitetural. Há três pontos de observação — fonte `.mop`, monitor gerado,
traço executado — e a gh104 já instrumentou os dois mais fortes. A lição nº 9 do post-mortem
mostra por que o mais fraco engana: o weaver dexlib2 apagava a categoria inteira,
`UnsatisfiedConstraint` deu **0 em 97.018 eventos** contra **43** no grupo de controle AspectJ.
Um grafo de def/use no nível do fonte teria mostrado uma aresta saudável que não existe em
execução.

**Recomendação:** mover para `backup/`, tirar do `<modules>`, e produzir o grafo de predicados na
camada de gates em Python, com uma linha por sítio carregando o que o módulo descarta — espécie
do sítio (`condition`/corpo/`@match`/`@fail`), polaridade, aridade, expressão e tipo estático da
posição 0, *splitter* das posições ≥1, cláusula CrySL traduzida e veredito, e pertinência ao
autômato — medido também no monitor gerado e confirmado por par de traços. O diagrama sai do CSV
em Graphviz/Mermaid, com as arestas mortas em vermelho.

---

## 8-bis. [auditado] Genericidade: o que a camada de gates precisa suportar

Só `jca_android` é **alterado**, mas os gates têm de aceitar **qualquer** spec JavaMOP, inclusive
as que não têm predicado algum. O universo real é de **214 `.mop`**:

| conjunto | `.mop` | o que ele testa nos gates |
|---|---:|---|
| `generic` | 118 | maior conjunto, zero predicados, 82% multiparamétrico |
| `generic_new` | 27 | **17 delas não têm autômato nenhum** |
| `jca` | 23 | congelado |
| `jca_android` | 23 | o alvo |
| `jca_android_bug_predicate` | 23 | arquivado |

**[auditado-v2]** Sete lacunas, nenhuma coberta pelo texto original deste plano. Todas medidas.

1. **Specs sem `fsm`/`ere` algum — a mais séria.** `generic_new` tem **17 specs event-only**, que
   relatam direto no corpo do evento e não declaram autômato (ex.:
   `Closeable_MeaninglessClose`, `TreeMap_Comparable`, `URLEncoder_EncodeUTF8`). Para elas, "todo
   evento é órfão" é uma leitura sem sentido: um gate de acusador órfão que pressuponha autômato
   emitiria **27 falsos positivos**. O gate precisa reconhecer a forma event-only e pulá-la
   declaradamente.
2. **`generic` não dá verde trivial.** Tem 1 órfão real — `FSM246.mop`, evento `event_2`. O gate
   precisa distinguir "evento fora do autômato numa spec sem predicados" de "acusador órfão", ou
   classificar o achado como informativo em vez de falha.
3. **Degradação nos arquivos que não compilam.** Confirmados os **11** com nome de parâmetro
   duplicado (`FSM119`, `FSM123`, `FSM133`, `FSM140`, `FSM197`, `FSM206`, `FSM209`, `FSM224`,
   `FSM45`, `FSM60`, `FSM69`) e a colisão de `import` em `FSM358.mop:4,6` (`Level` vindo de
   `RVMLogging` e de `java.util.logging`). Contrato obrigatório: **pular e contar**, nunca falhar
   em silêncio nem estourar. O contador entra no relatório do gate.
4. **G-ORDER sobre spec sem regra CrySL.** `generic/*`, `generic_new/*` e `RandomStringPassword.mop`
   não têm contraparte no oráculo. O gate tem de **pular declaradamente**, no mesmo padrão
   `skipped` do `gh104_gates.py` — nunca dar verde por vacuidade nem vermelho por ausência.
5. **`predicate_graph.csv` sobre conjunto sem predicados.** Zero linhas é o resultado **correto** e
   tem de ser verde. O fechamento de grafo sobre `generic` é trivialmente satisfeito.
6. **G-PARAM (§7.5).** Nenhum gate hoje detecta o colapso silencioso da lista de parâmetros. Vale
   para os 214 arquivos, não só para o alvo. **[auditado-v2]** Fato de escopo: **zero** das 214
   specs tem hoje parâmetro primitivo/array — o G-PARAM protege o trabalho futuro da F3, não
   conserta algo presente.
7. **[auditado-v2] Órfão reverso e evento duplicado.** `jca/GCMParameterSpecSpec.mop` declara
   `event c1` duas vezes (`:23`, `:34`) e o `ere` (`:48`) referencia um `c2` nunca declarado —
   idêntico no arquivado (`jca_android_bug_predicate`, mesmas linhas); `jca_android` já está
   corrigido. São os únicos 2 casos nos 214. O gate de órfão tem de checar também a direção
   `usados − declarados` e tratar o alfabeto declarado como multiconjunto — e registrar que o
   congelado diverge do alvo aqui. Duas notas de contrato do mesmo levantamento: helpers privados
   sombreiam nomes da API (`validate(int)` em `KeyPairGeneratorSpec`, `.remove(` de coleções em
   `generic`/`generic_new` — o discriminador obrigatório é `(Property`); e 5 specs por conjunto
   jca usam handler `@match1` via `alias match1 = <estado>`, que o gate precisa resolver para não
   errar a partição 42/7.

---

## 9. Não-objetivos

- **A `jca` congelada.** Não é descongelada, não é reparada, não é medida de novo. É a linha-base
  publicada.
- **`jca_android_bug_predicate`.** Não é reparado nem estendido; é registro da auditoria. Hunks
  dele são **reimplementados sob evidência própria**, nunca replicados por serem dele.
- **MetaCrySL.** As regras api30 são oráculo de leitura. Defeito de regra vira linha de
  `divergence_record.csv`, nunca edição a montante. (Há pelo menos dois já registrados:
  `KeyPairGenerator.cryptsl:45/:53` e a lista de `Signature`.)
- **O weaver e a instrumentação.** Fora de escopo, apesar de a lição nº 9 mostrar que ele pode
  apagar a categoria inteira. Se o gate de alcance da seção C3 mostrar que `UnsatisfiedConstraint`
  continua em zero no caminho de produção, **esta change fica bloqueada** e o weaver vira
  pré-requisito.
- **Republicar números no artigo em curso.** Ver seção 10.

---

## 10. Riscos e decisões pendentes

### R1 — O substrato compartilhado (rebaixado para baixo pela decisão de F0)
Qualquer mudança em `ExecutionContext` atinge o `jca` congelado. Já aconteceu e já foi revertido.
**Mitigação decidida (2026-08-20): classes novas ao lado, antigas depreciadas e intocadas** — ver
F0. Com a classe antiga literalmente não editada, o risco deixa de ser de vigilância e passa a ser
de disciplina de import: basta que nenhuma spec `jca_android` **mencione** a classe antiga.
**[auditado-v2]** O predicado é `grep -rlw 'ExecutionContext' jca_android/ --include='*.mop'`
vazio — com `-w`, para pegar também uso fully-qualified (não existe import wildcard em conjunto
algum). O risco residual é o do gate G-PRED, que precisa ser reformulado (ver F0), não o do
congelamento.

### R2 — O teto do gerador (baixo para 17; duro em 18) [auditado-v2]
Rebaixado pela medição do pipeline real (§7.3): o `CipherSpec` de 17 eventos gera até com
`-Xmx1g` nos dois processos — 17 não é risco de viabilidade. O teto real está em n=18:
`StackOverflowError` no parser do pai (`EnableSet.parseSets`), insanável por `-Xmx`/`-Xss`; as
alavancas são patch em `parseSets` ou supressão dos coenables de `fail`. Passar `-Xmx` ao
subprocesso continua valendo como blindagem de **portabilidade** — em máquina com pouca RAM o
filho estoura com a heap default e a falha é mascarada (R5). Toda tarefa que toque `Cipher` gera
o monitor no pipeline real antes de aceitar o alfabeto, e **registra a heap usada** — sem isso o
resultado não é reproduzível entre máquinas.

### R3 — Alcance da instrumentação (alto, não mitigável nesta change)
Predicado cujo produtor está fora do alcance é falso positivo garantido. Daí o terceiro valor
"não observado" (seção 5). Precisa de medição em dispositivo antes de F3.

### R4 — Chaves concretas do Android (médio, barato de resolver)
Não consegui determinar se `OpenSSLRSAPublicKey`/`BCRSAPublicKey` sobrescrevem `equals` por
valor — as classes não estão nos fontes locais. **Teste de uma linha em dispositivo** resolve, e
o resultado muda o veredito de `GENERATED_KEY`/`GENERATED_PUBLIC_KEY`.

### R5 — Falha de geração mascarada (médio, operacional)
`LogicRepositoryConnector.java:198-243` faz `child.waitFor()` **sem timeout**, nunca consulta
`getExitValue()` e concatena stderr ao stdout. Um `OutOfMemoryError` na JVM-filha aparece como
`"Logic Engine Error: ..."` ou `"Wrong Logic Repository Output"`, e o rv-monitor pode travar
indefinidamente. Não há `catch (OutOfMemoryError)`, watchdog nem limite de tamanho de saída.
Se uma geração falhar de forma opaca durante a change, esta é a primeira hipótese.
**[auditado-v2]** Confirmado ao vivo na segunda passada: OOM no filho aparece como
`Logic Engine Error: null` com **exit 0** e nenhum monitor gerado. E um único byte no stderr do
filho (ex.: a linha `Picked up JAVA_TOOL_OPTIONS`) quebra o parse do XML, porque
`executeProgram` concatena stderr após o stdout.

### R6 — [auditado] Falhas silenciosas da cadeia de geração (alto, mitigável por gate)
O JavaMOP apaga a lista de parâmetros de uma spec que declare array de tipo primitivo, e conclui
com `rc=0` e a mensagem de sucesso (§7.5). O rv-monitor então emite um monitor global, sem
fatiamento — e nada na cadeia acusa. Somado ao R5 (a falha de geração mascarada pelo
`LogicRepositoryConnector`), o padrão é o mesmo: **esta cadeia de ferramentas erra em silêncio, e
o silêncio parece sucesso.** Mitigação: G-PARAM na F5, e a disciplina de inspecionar o artefato
gerado — não o código de saída — em toda tarefa que toque spec de junção.

### R7 — O mapeamento de alfabeto do G-ORDER (médio, de orçamento) [auditado-v2]
O G-ORDER é decidível — `ORDER` e `fsm`/`ere` são ambos regulares (§5/C1) — mas a equivalência de
AFDs pressupõe um alfabeto comum, e não há bijeção: a `.mop` separa sobrecargas para poder ligar
parâmetros (um evento do `ORDER` vira vários da spec), agrega e renomeia. O trabalho real do gate
é construir e manter esse mapeamento evento a evento, por spec, e um mapeamento errado produz
veredito errado nas duas direções — verde sobre um autômato que não é o da regra, ou vermelho
sobre uma spec fiel. Mitigação: o mapeamento é artefato versionado (arquivo irmão do
`predicate_graph.csv`), revisado junto com a spec que o usa; o gate reporta `skipped` quando o
mapeamento não existe, nunca infere por heurística (§8-bis, lacuna 4). Orçar o mapeamento como
tarefa própria da F5, não como detalhe de implementação do gate.

### D1 — O artigo (decisão do usuário)

**[auditado] Os números foram refeitos e o enquadramento muda.** A linha-base publicada foi
reproduzida dígito a dígito (`RV=454, CC=423, both=112, só-RV=342, só-CC=311`), com a mesma
política de merge do `rq1_rv_cc.py`. O efeito das allow-lists api30 foi então modelado com as
classes Java reais — `Api30CipherTransformationUtil.isValid` e `ConscryptAliasTable.matches` — e
não por aproximação:

| cenário | só-RV | só-CC |
|---|---:|---:|
| publicado (`jca`) | 342 | 311 |
| api30, removendo só os eventos silenciados | **342** | **311** |
| api30 + alias, descartando a chave inteira (`UnsafeAlgorithm`) | **300** | **322** |
| **[auditado-v2]** idem + `UnsafeProtocol` (TLS/SSL) e `InvalidKeyStoreType` (`AndroidKeyStore`) | **255** | **355** |
| reparo E5 sozinho, no máximo | *247* | *339* |
| tudo combinado (E5 + allow-lists + alias) | *160* | *383* |

**As allow-lists sozinhas movem zero células.** O filtro silencia 5.467 dos 15.444 eventos
`UnsafeAlgorithm`, mas a chave do venn é `(apk, class, method, spec)` e sobrevive enquanto
**qualquer** evento seu sobreviver — e quase toda chave carrega também um
`InvalidSequenceOfMethodCalls`. O venn é surdo à correção de allow-list.

**[auditado-v2]** O efeito só aparece se as acusações de ordem acopladas caírem junto — o
descarte da chave inteira. A segunda passada corrigiu dois pontos da primeira auditoria aqui:
(i) o cenário `UnsafeAlgorithm` dá **300/322**, não 299/322 — a chave do `MacSpec` (31 eventos
com valor observado vazio) não é admitida por `matches()` e sobrevive sob a própria modelagem;
(ii) **299 não era teto** — estender o mesmo silenciamento a `UnsafeProtocol` (TLS/SSL admitidos
pelo `SSLContext`) e `InvalidKeyStoreType` (`AndroidKeyStore`), exatamente os dois casos do
apêndice que este documento declara que "deixam de ser violações", dá **255/355**, quase a
estimativa original. E a atribuição é **dos dois lados**: nas 53 chaves do cenário 300/322, o
reparo de allow-list como escrito no `jca_android` derruba sozinho o report e a acusação de ordem
acoplada (a guarda co-emite os dois); o E5 sozinho não derruba nenhuma delas — mas tem o alcance
maior (E5-máx 247/339; tudo combinado 160/383).

Dois controles fecham o cálculo. **`CipherSpec` não contribui nada**: é o maior bloco de só-RV
(69 de 342), mas seus 109 eventos `UnsafeAlgorithm` têm um único valor distinto —
`RSA/ECB/OAEPWithSHA1AndMGF1Padding` — que **as duas** tabelas rejeitam; os 69 são acusações de
ordem. E **a resolução de alias esgota o resto**: dos 5 pares (spec, valor) que ainda acusavam sob
a allow-list literal (`MessageDigestSpec/SHA`, `/SHA1`, `SignatureSpec/NONEWITHRSA`,
`/SHA256WITHRSA`, `TrustManagerFactorySpec/X509`), os cinco caem — dois por fold
*case-insensitive* direto (`NONEWITHRSA`, `SHA256WITHRSA`) e três sob `ConscryptAliasTable`
**[auditado-v2]**.

**O que isso muda para a decisão.** **[auditado-v2]** A direção está certa e a manchete de fato
cruza em qualquer cenário; a margem varia de 22 achados (300/322) a 100 (255/355), conforme a
leitura que o pesquisador adotar. E o risco editorial vem **dos dois lados** — allow-lists e
reparo E5 —, o que derruba a proteção que o caminho 1 abaixo parecia oferecer: "não tocar nas
specs para este artigo" não preserva a manchete, porque a gh104 já reparou um órfão e as duas
changes vão reparar os outros 17 e re-transcrever as allow-lists. A escolha entre os três
caminhos tem de ser feita sabendo disso. Os dois casos ilustrativos do apêndice `rv-only-examples.tex` (OkHttp
`"TLS"`/`"X509"` e `MasterKeys`/`AndroidKeyStore`) deixam de ser violações. Três caminhos:

1. **Não tocar nas specs para este artigo**, mas parar de tratar o defeito de spec como nota de
   rodapé sobre o GCM — declarar que 13 de 23 specs não emitiram nada e que ≥5 não podem, e
   quantificar o *tier* api30 (84 misuses / 11.409 eventos / 18,5%) como ameaça declarada. É o
   caminho de menor risco: o número dito por nós é muito melhor que o mesmo número descoberto por
   um revisor com o pacote de replicação em mãos.
2. Publicar `jca_android` como **segunda era declarada**, exatamente como a gh104 prevê.
3. Transformar em contribuição: *"medimos quanto de um corpus de RV é artefato de especificação e
   o reduzimos de X para Y"* — o harness diferencial é o instrumento que quantifica. É um
   resultado forte, e é o que a evidência realmente suporta.

Há também correções que **não movem número nenhum** e podem ser feitas já: `background.tex:115-116`
descreve `reset` como evento benigno quando ele é acusador incondicional; `discussion.tex:77` diz
"reported upstream" sem artefato correspondente; e `rv-only-examples.tex:10-13` aponta para
`dataset/results/specs/jca/`, que não existe no pacote.

### D2 — Escopo da change (decisão do usuário)
F0+F1+F2 já é uma change grande, e é a que tem o melhor retorno por risco (substrato + autômatos
+ forma da guarda, tudo medido). F3 (a fiação propriamente dita) pode ser uma segunda change,
com F0 como pré-requisito. Minha recomendação é separar: a gh101 falhou por atacar 22 specs de
uma vez sem instrumento, e F3 sem F0 repete o erro.

### D3 — Os 9 `remove()` (decisão técnica, registrar) [auditado — reformulado]
A pergunta anterior — *"retirar `NEGATES` por fidelidade ou manter como divergência alinhada à
geração nova?"* — partia de uma premissa falsa. O oráculo tem **duas** cláusulas `NEGATES`, e
apenas **uma** das nossas nove remoções (`PBEKeySpecSpec.mop:74`) corresponde a alguma delas. As
outras **oito estão em `@fail`** e implementam "desfazer o predicado quando o autômato falha",
semântica que não existe em nenhuma das duas gerações do CrySL — não é `NEGATES` mal traduzido, é
invenção nossa.

A decisão real, portanto, é dupla:
1. **As oito remoções de `@fail`**: acoplam o typestate ao predicado, o que contradiz a
   ortogonalidade do CrySL (violar `ORDER` não desfaz um `ENSURES`) e a regra acionável nº 1 desta
   change. A recomendação é retirá-las, com o delta medido pelo harness.
2. **As quatro que usam a sobrecarga `@Deprecated remove(Property)`** saem de qualquer forma: elas
   apagam a property para todos os objetos do processo, e uma delas
   (`TrustManagerFactorySpec.mop:101`) apaga `GENERATED_TRUST_MANAGERS`, que ninguém escreve.

---

### D4 — O mecanismo de ligação (decisão de arquitetura, a maior da change) [auditado]
Store corrigido, specs de junção multiparamétricas, ou híbrido — seções 7.4 a 7.6. A recomendação
continua sendo **híbrida**, porque as specs de junção fazem a identidade ser garantida pelo
mecanismo do JavaMOP em vez de reimplementada por nós — e as 118 specs de `generic`, 82% delas
multiparamétricas até *k*=6, mostram que o mecanismo aguenta a escala.

Mas **as specs de junção não podem ser o padrão**, e a partição não é de gosto: `byte[]` e `char[]`
não podem ser parâmetro de spec (§7.5), e é neles que estão 21 das 27 leituras vivas. A regra é a
da §7.6 — B para cadeias de tipos-objeto; B com o idioma `Object` e G-PARAM, ou A, para as cadeias
que passam por array primitivo; corpo do evento para as posições de valor.

**Esta decisão continua não devendo ser tomada no papel, mas o piloto mudou:** é a **cadeia do IV**
(`SecureRandom → byte[] → IvParameterSpec → Cipher`), não `Mac`/`Key`. `Mac` e `Key` são ambos
tipos-objeto — o piloto passaria e não teria dito nada sobre o caso que decide. Ele serve como
controle positivo. Dela depende o tamanho de F0.

**[auditado-v2] O piloto foi executado na segunda passada** (evidência em
`audit/20260820_verificacao_plano_predicados_v2/agentI/`), sem tocar nas specs de produção, com
eventos injetados pelos despachantes estáticos do monitor gerado (o contrato do `TraceRunner`).
Resultados:

1. **B funciona no caso difícil.** `IvChainFsmSpec(Object iv, IvParameterSpec spec, Cipher c)`
   com o idioma `Object` produz fatiamento real por identidade e o veredito exato com dois
   `byte[]` no mesmo processo — o traço bom dá 1 MATCH e zero FAIL; o ruim falha em `mk`
   (`REQUIRES randomized`) **e** em `use` (`REQUIRES preparedIV`), na instância certa, com
   bindings certos.
2. **B ingênuo acusa o caso bom** (achado novo): com o consumidor como evento `creation`, a
   instância parcial não enxerga a cadeia e falha — falso positivo no traço correto. Regra de
   design: **consumidor nunca é `creation`**. O silêncio resultante no cenário consumidor-só é a
   lógica de três valores da §5 implementada estruturalmente — argumento novo a favor de B.
3. **Joins produto-cruzado exigem laço benigno para instâncias desconexas** (achado novo), senão
   o `iv` randomizado de *outra* cadeia gera FAIL espúrio.
4. Parâmetros de spec não são visíveis em `@match`/`@fail` — estado para handlers vai em campos
   do monitor.
5. **De graça no caminho B**: `WeakReference` + `TerminatedMonitorCleaner` +
   `AbstractSynchronizedMonitor` — os três defeitos do §4.3 não existem nele. Custo do gerador
   trivial: 3 eventos, k=3 (o k=4 do esboço é desnecessário), coenable 21 contra 2,2 M do
   `CipherSpec`.

Constatação prévia importante: duas specs separadas compartilhando o `byte[]` **não têm canal
algum** no JavaMOP (mapas e monitores próprios, zero referências cruzadas) — "specs se
comunicando" **é** o mecanismo A. Não testado: a tecelagem ajc/dexlib2 de ponta a ponta do
binding `Object`↔`byte[]`, a coexistência com `CipherSpec` no mesmo joinpoint (dedup de relato) e
a memória em escala dos joins desconexos. A recomendação segue a partição da §7.6, com as regras
1–4 acima como critérios de design gateáveis; a decisão final continua sendo do pesquisador.

## Anexo — evidência de primeira mão

Comandos reproduzíveis a partir de
`rvsec/rvsec-mop/src/main/resources/`:

```bash
# grafo de predicados: escritas vs leituras
grep -ho "setProperty(Property\.[A-Z_]*" jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
grep -ho "validate(Property\.[A-Z_]*"    jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn

# leituras sem produtor
grep -n "GENERATED_PRIVATE_KEY" jca_android/*.mop      # 1 leitura, 0 escritas
grep -n "MACED" jca_android/*.mop                      # nenhuma ocorrência
```

**[auditado]** Acusadores órfãos (eventos declarados fora do `fsm`/`ere`) e a partição das
escritas entre corpo de evento e `@match` foram recontados pela auditoria com um analisador
estrutural — que casa chaves e parênteses e neutraliza comentários e literais de string antes de
varrer, em vez de regex sobre o texto cru. Os três conjuntos `jca`, `jca_android` e
`jca_android_bug_predicate` foram medidos com o mesmo instrumento, e os números confirmaram-se
(17/9, 18/10, 0; 27 de 27 leituras em `condition`; 42/7 nas escritas). O analisador ainda **não é**
o gate: ele precisa migrar para a camada da seção 8, com o contrato de genericidade da seção 8-bis,
antes de virar critério de aceitação.

Evidência no monitor gerado
(`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`):
`Prop_1_event_i2` com o `return false` da guarda; `Prop_1_transition_reset[] = {4,4,4,4,4}`;
`Prop_1_transition_next2[] = {3,3,1,3}` contra `next1[] = {3,1,1,3}`.
