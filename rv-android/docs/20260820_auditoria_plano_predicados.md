# Auditoria do plano de fiação de predicados

**Objeto:** `docs/20260820_plano_fiacao_predicados.md` (799 linhas, Fase 0).
**Método:** cada alegação foi reconferida contra a fonte — arquivo aberto na linha citada, medição
reexecutada, ou experimento novo quando o plano só tinha inferência. Onde o plano media por regex,
a medição foi refeita com um analisador estrutural.

| campo | valor |
|---|---|
| data da auditoria | 2026-08-20 |
| ponto de medição | reator `rvsec` em `bd61abea` |
| ponto de medição do plano | `d27c48e9`, 2026-08-20T10:49 |
| alegações verificadas | 47 |
| `CONFIRMADO` | 33 |
| `CORRIGIDO` | 10 |
| `REFUTADO` | 3 |
| `NÃO VERIFICÁVEL` | 1 |

---

## 0. O resultado que muda o plano

Três achados, em ordem de consequência.

**(1) `byte[]` não pode ser parâmetro de spec do JavaMOP, e a falha é silenciosa.** Declarar
`byte[]` (ou qualquer array de tipo primitivo) na lista de parâmetros de uma spec faz o JavaMOP
**apagar a lista inteira** — não só o parâmetro ofensor — e emitir um monitor global sem
parametrização alguma, com código de saída 0 e nenhum aviso. Isso derruba o mecanismo B como
padrão para a família `randomized[byte[]]`, que carrega **21 das 27 leituras vivas**, e invalida o
piloto proposto (`Mac`/`Key`) como decisor, porque ele é de tipos-objeto e passaria. Há contorno —
declarar `Object` — e ele funciona; mas precisa entrar no design e virar gate. Ver §4.

**(2) A alegação editorial do D1 está superestimada em cerca de 2×.** A linha-base publicada
(342 só-RV / 311 só-CC) foi reproduzida dígito a dígito. As allow-lists api30 sozinhas movem
**zero** células do venn. Sob a leitura mais agressiva possível — com resolução de alias e
descarte da chave inteira — o resultado é **299 / 322**, não os 255 / 354 alegados. Ver §7.

**(3) `@fail` não é "o gatilho" do custo do gerador — ele é o custo inteiro.** Medido: sem `fail`
entre as categorias, n=18 custa **2 ms** e 10 entradas; com ele, n=17 custa 11 s e 2.228.207
entradas. O teto de alfabeto é um artefato exclusivo do `@fail`. Ver §2.5.

---

## 1. Reconferência das medições (§5.1 do handoff)

**Deriva dos Grupos 8/9: nenhuma no que importa.** Os Grupos 8 e 9 tocaram 12 dos 23 arquivos
(mais `codes.csv`), mas a distribuição de predicados em `d27c48e9` é idêntica à de `bd61abea`,
valor por valor. O gate G-PRED sustentou. As contagens do plano continuam válidas.

| alegação | plano | medido | veredito |
|---|---:|---:|---|
| leituras `validate(Property` | 27 | 27 | CONFIRMADO |
| escritas `setProperty(Property` | 49 | 49 | CONFIRMADO |
| `remove(Property` | 9 | 9 | CONFIRMADO |
| linhas `ExecutionContext` nas `.mop` | 134 | 134 | CONFIRMADO |
| valores do enum `Property` | 24 | **25** | **CORRIGIDO** |
| valores lidos | 4 (`RANDOMIZED` 21, `GENERATED_KEY` 4, `GENERATED_PUBLIC_KEY` 1, `GENERATED_PRIVATE_KEY` 1) | idem | CONFIRMADO |
| valores escritos | 21, em 49 sítios | idem | CONFIRMADO |
| escritas sem consumidor | 17 valores, 33 sítios | **18 valores, 35 sítios** | **CORRIGIDO** |
| `GENERATED_PRIVATE_KEY` escrito | 0 vezes | 0 | CONFIRMADO |
| zero sítios no conjunto | `MACED`, `GENERATED_CIPHER`, `GENERATED_TRUST_MANAGERS` | só os dois primeiros | **CORRIGIDO** |
| acusadores órfãos `jca_android` | 17 em 9 specs | 17 em 9 | CONFIRMADO |
| acusadores órfãos `jca` | 18 em 10 specs | 18 em 10 | CONFIRMADO |
| acusadores órfãos `jca_android_bug_predicate` | 0 | 0 | CONFIRMADO |
| leituras dentro de `condition(...)` | 27 de 27 | 27 de 27 | CONFIRMADO |
| escritas em corpo vs `@match` | 42 / 7 | 42 / 7 | CONFIRMADO |
| arestas produtor→consumidor no oráculo | 19 | 19 predicados, **35 pares, 44 arestas** | **CORRIGIDO** |
| arestas realizadas | 3 (+1 quebrada) | 3 (+1) | CONFIRMADO |

### As quatro correções

**O enum tem 25 valores, não 24.** Contagem direta em `Property.java`.

**As escritas sem consumidor são 18 valores em 35 sítios, não 17 em 33.** A aritmética do plano
subtraiu os **4** valores lidos dos 21 escritos, mas `GENERATED_PRIVATE_KEY` nunca é escrito — ele
não pertence ao conjunto de onde se subtrai. O correto é 21 − 3 = 18 valores, e
49 − (9+3+2) = 35 sítios.

**`GENERATED_TRUST_MANAGERS` não tem zero sítios — tem um**, e é pior do que zero:
`TrustManagerFactorySpec.mop:101` chama `remove(Property.GENERATED_TRUST_MANAGERS)`, a sobrecarga
`@Deprecated` que apaga a property para o processo inteiro, sobre uma property que **ninguém
escreve**. Só `MACED` e `GENERATED_CIPHER` são de fato inertes.

**"19 arestas" é a unidade errada, e isso encolhe F3 pela metade no papel.** O oráculo tem 20
predicados que são exigidos por alguma regra; um deles (`preparedEC`) não tem produtor; logo **19
predicados são conectáveis**. Mas o trabalho de F3 não é por predicado: é por par
(predicado, regra-consumidora), e esses são **35**; contando regra-produtora → regra-consumidora
são **44**. O número 3 (+1) das arestas realizadas está na mesma unidade de 19 e é coerente — só
o rótulo "arestas" precisa virar "predicados conectáveis", e F3 precisa ser dimensionada em 35.

---

## 2. As alegações de semântica (§5.2)

### 2.1 Guarda `condition(...)` falsa não transita — CONFIRMADO

`MultiSpec_1RuntimeMonitor.java:3713`, literal:

```java
final boolean Prop_1_event_i2(int mode, Key key, Cipher c) {
    if ( ! (ExecutionContext.instance().validate(Property.GENERATED_KEY, key) || ...) ) {
        return false;
    }
```

O `return false` precede o corpo e o `handleEvent`. A guarda é emitida no **método do monitor**,
não no advice do aspecto, e o gerador usa a mesma forma para `before` e `after` — a diferença
entre os dois vive no `.aj`, que apenas escolhe o momento da chamada.

### 2.2 Evento fora do `fsm` recebe linha toda-`fail` — CONFIRMADO

`Prop_1_transition_reset[] = {4, 4, 4, 4, 4}` no `MessageDigestSpecMonitor`, e o índice 4 é de
fato a categoria de falha: `Category_fail = nextstate == 4` (`match = nextstate == 3`).

### 2.3 `nextBytes()` duas vezes é violação — CONFIRMADO, com o mapa de estados decodificado

```
Prop_1_transition_next1[] = {3, 1, 1, 3}
Prop_1_transition_next2[] = {3, 3, 1, 3}
Category_fail = nextstate == 3
```

Estados: 0 = `start`, 1 = `end`, 2 = `init` (`alias match1 = init`, e `Category_match1 == 2`),
3 = `fail`. Logo `next2` a partir de `end` vai para `fail`, enquanto `next1` faz laço. Confirmado
também na fonte: o bloco `end` de `SecureRandomSpec.mop` lista `genSeed, setSeed1, setSeed2,
next1, next3, ints` e **omite `next2`**. Contradiz `Ins, Seeds?, Ends*` da regra api30 (§3.3).

Bônus da mesma tabela: `c3`, `g4` e `setSeed3` têm linha `{3,3,3,3}` — os três órfãos da spec,
todos constantes em `fail`, exatamente como §2.2 prevê.

### 2.4 O rv-monitor indexa por identidade — CONFIRMADO

`CachedWeakReference.java:16` → `System.identityHashCode(ref)`;
`WeakRefHashTable.java:474` → `if (key == this.ref)`. `CachedWeakReference` sobrescreve
`hashCode()` e **não** sobrescreve `equals()`, de modo que a igualdade herdada de `Object` também
é identidade. As duas pontas concordam.

### 2.5 `n·(2ⁿ−1)`, o teto e o `@fail` — CONFIRMADO, com uma correção e um reforço

Medição reproduzida com driver direto sobre `FSMCoenables` (FSM de 6 estados, categoria `fail`
presente):

| n | entradas medidas (categoria `fail`) | `n·(2ⁿ−1)` | bate | tempo |
|---:|---:|---:|:--:|---:|
| 14 | 229.362 | 229.362 | sim | 1,3 s |
| 16 | 1.048.560 | 1.048.560 | sim | 6,6 s |
| 17 | 2.228.207 | 2.228.207 | sim | 11,0 s |
| 18 | 4.718.574 | 4.718.574 | sim | 23,7 s |

A fórmula é o valor **exato atingido**, nas quatro linhas. A categoria de casamento, no mesmo
autômato, produz 10 entradas.

**Reforço — `@fail` não é o gatilho, é o custo inteiro.** Retirando `fail` da lista de categorias
e mantendo tudo o mais:

| n | com `fail` | sem `fail` |
|---:|---:|---:|
| 14 | 229.362 entradas, 1,3 s | 10 entradas, 2 ms |
| 17 | 2.228.207 entradas, 11,0 s | 10 entradas, 2 ms |
| 18 | 4.718.574 entradas, 23,7 s | 10 entradas, 2 ms |

O mecanismo está em `FSMCoenables.computeCoenables`: o caminho é um `HashSet<Symbol>`, ou seja um
**subconjunto do alfabeto**, e o estado `fail` é absorvente com auto-laço em todos os símbolos —
então a busca reversa a partir dele enumera todos os 2ⁿ−1 subconjuntos não vazios, para cada um
dos n eventos. Nenhuma outra categoria tem essa forma.

**Correção — o `-Xmx2g` não estoura em n=18.** O plano afirma que com `-Xmx2g` o n=18 dá
`OutOfMemoryError` após 101 s. Aqui n=18 **gerou** sob `-Xmx2g`, em 23,7 s, com o resultado exato.
A diferença é de escopo: o driver computa e conta os coenables em memória; o pipeline real ainda
serializa o `toString()` (os 82,4 milhões de caracteres que o próprio plano mede) e o transporta
pelo `StreamGobbler` do processo pai. O OOM é do **pipeline completo**, não do `FSMCoenables`, e
a tabela do plano precisa dizer isso — senão a conclusão "passar `-Xmx` destrava o `CipherSpec`"
fica ancorada numa medição que não se reproduz.

O resto da alegação 5 confirma-se: `rv-monitor:34` e `LogicRepositoryConnector.java:151` passam
**apenas** `-Xss1g`; `grep -r '\-Xmx'` sobre `rv-monitor` e `javamop` não retorna nada; a heap
efetiva é o default ergonômico do HotSpot (nesta máquina, `MaxHeapSize = 32 GB` sobre 123 GB de
RAM — ¼, como o plano diz); e não existe limite hard-coded no caminho FSM.

### 2.6 `--noopt1` não ajuda — CONFIRMADO

`EnableSet.java:121-125`: `getEnable()` devolve `getFullEnable()` quando `Main.noopt1` — age no
consumo e, além de não baratear, **piora** (usa o enable cheio). E
`OptimizedCoenableSet.optimize()` lê `contents.get(event.getId())` direto, sem passar por
`getEnable()`, de modo que a flag nem alcança o simplificador. `EREPlugin.java:33,40` converte
para FSM e grava `logic = "fsm"`: `ere` paga o mesmo que `fsm`.

### 2.7 A falha de geração é mascarada — CONFIRMADO

`LogicRepositoryConnector.executeProgram` (:198-243): `child.waitFor()` em `:223` sem timeout;
`getExitValue()`/`exitValue()` não aparecem no arquivo; e
`output = outputGobbler.getText() + errorGobbler.getText()` concatena stderr ao stdout. Sem
`catch (OutOfMemoryError)`, sem watchdog, sem limite de tamanho.

---

## 3. O oráculo CrySL (§5.3)

### 3.1 A geração é a antiga — CONFIRMADO

`workspace-rv/CryptoAnalysis` está em `349073ff`, de 2026-07-25 (pré-3.0). As regras api30 usam a
sintaxe antiga: `FORBIDDEN:` com dois-pontos em 4 arquivos, `neverTypeOf(a, T);;`,
`length(x) >= y`.

### 3.2 As cinco diferenças

| ponto | veredito | evidência |
|---|---|---|
| casamento por **nome** apenas | CONFIRMADO | `CrySLPredicate.equals` compara só `predName` — não aridade, não negação, não parâmetros. `EnsuredCrySLPredicate.equals` delega a ele. |
| `REQUIRES` **monotônico** | CONFIRMADO | `ensuredPredicates` (`AnalysisSeedWithSpecification.java:72`) só recebe `add` (`:580`); não há remoção em lugar nenhum. |
| `NEGATES` **no-op** | CONFIRMADO | `getNegatedPredicates` não é referenciado em nenhum ponto do analisador. |
| `ENSURES` condicional **sobrescrito** | CONFIRMADO | `:246-251`: `satisfiesConstraintSytem = checkConstraintSystem();` e logo em seguida, se há guarda, `satisfiesConstraintSytem = !evaluatePredCond(...)` — **atribuição**, não conjunção. O `ArrayList temp` construído nas linhas do meio nunca é usado, o que é a assinatura do defeito. |
| valor não extraível **cala-se** | **CORRIGIDO** | ver abaixo |

**A correção.** `ImpreciseValueExtractionError` **existe** nesta geração e **é lançado** — em
`ConstraintSolver.java:174` e `:484`. O que é verdade é mais estreito e mais interessante: os dois
sítios estão no caminho de **CONSTRAINTS**, não no de predicados. Em `doPredsMatch`, quando
`expVals` sai vazio o laço não executa e `requiredPredicatesExist` permanece `true` — silêncio a
favor do programa, sem erro. A linha da tabela do plano deve dizer *"na comparação de valores de
predicado"*, não em geral.

### 3.3 O achado central sobre posições — CORRIGIDO

O plano enuncia: *"posição 0 = referência de objeto; posições ≥1 = valores comparados
textualmente"*. O código não faz nada por posição. `doPredsMatch` itera **de i = 0** e decide por
**tipo declarado**:

```java
private final static List<String> trackedTypes =
        Arrays.asList("java.lang.String", "int", "java.lang.Integer");
```

`isOfNonTrackableType(var)` → `continue`. Ou seja: uma posição é comparada por valor se, e somente
se, seu tipo no bloco `OBJECTS` for `String`, `int` ou `Integer`. Na prática a posição 0 costuma
ser um objeto e cai fora — daí a leitura do plano funcionar como regra de bolso. Mas ela erra em
casos que importam para esta change:

- `macced[_, plainText]` — posição 1 é `byte[]`, **pulada**. O `!macced` do `Cipher` não compara
  valor nenhum.
- `encrypted[cipherText, plainText]` — ambas `byte[]`, ambas puladas.

Para esses, `doPredsMatch` degenera em "existe algum predicado ensured com este nome", que é
exatamente o casamento por nome. A frase correta é **"comparação por valor apenas nas posições de
tipo `String`/`int`/`Integer`; todas as demais são puladas"**, e ela é mais forte, porque explica
por que o oráculo é tão frouxo justamente na família `byte[]`.

### 3.4 Contagens do oráculo

| alegação | plano | medido | veredito |
|---|---:|---:|---|
| regras api30 | 33 | 33 | CONFIRMADO |
| cláusulas `ENSURES` | 54 | 54 | CONFIRMADO |
| cláusulas `REQUIRES` | 36 | 36 | CONFIRMADO |
| predicados distintos | 32 | 32 | CONFIRMADO |
| aridade máxima (`generatedKey`) | 4 | 4 | CONFIRMADO |
| *"a maioria binários"* | — | **59 unários, 29 binários, 2 quaternários** | **REFUTADO** |
| `ORDER` do `SecureRandom` | `Ins, Seeds?, Ends*` | idem | CONFIRMADO |
| as 6 cláusulas `REQUIRES` do `Cipher` | as seis nomeadas | idem, literais | CONFIRMADO |

**A maioria é unária, não binária.** Dois terços das 90 cláusulas `ENSURES`+`REQUIRES` são de
aridade 1. O eixo E2 continua real — 31 cláusulas precisam de aridade ≥ 2, e o enum não as
suporta — mas a severidade está superestimada, e a frase precisa ser corrigida porque ela é usada
para justificar a aridade N da F0.

### 3.5 `NEGATES` e os nossos 9 `remove()` — CORRIGIDO, e o D3 precisa ser reescrito

O oráculo inteiro tem **duas** cláusulas `NEGATES`:

```
SecretKey.cryptsl:   generatedKey[this, _] after d;
PBEKeySpec.cryptsl:  speccedKey[this, _] after cP;
```

Nossos 9 `remove()` estão em `@fail` (8) e em corpo de evento (1). Deles, **no máximo um** —
`PBEKeySpecSpec.mop:74`, `remove(SPECCED_KEY, s)` — corresponde a uma cláusula `NEGATES`. Os
outros oito implementam *"desfazer o predicado quando o autômato falha"*, que **não existe em
nenhuma das duas gerações do CrySL**: não é `NEGATES` mal traduzido, é semântica inventada.

O D3 do plano pergunta *"retiramos por fidelidade ou mantemos como divergência alinhada à geração
nova?"*. A pergunta certa é outra: **oito dos nove `remove()` não têm contraparte no oráculo em
versão alguma**, e quatro deles usam a sobrecarga `@Deprecated` que apaga a property para todos os
objetos do processo. O plano acerta o número 4 dessa sobrecarga; erra ao enquadrar os 9 como
tradução de `NEGATES`.

---

## 4. A decisão de arquitetura (§5.4) — o achado que reordena o plano

### 4.1 `byte[]` como parâmetro de spec — REFUTADO, com falha silenciosa

O plano marca isto como *"precisa de teste de fumaça"*. O teste foi feito. Matriz, mesma spec de
3 eventos, variando só o tipo do parâmetro do meio:

| tipo declarado | lista de parâmetros no `.rvm` gerado |
|---|---|
| `byte[]` | `TByteArr()` — **vazia** |
| `int[]` | `TIntArr()` — **vazia** |
| `Object[]` | `TObjArr(SecureRandom r, Object[] b)` — preservada |
| `Object` | `TObj(SecureRandom r, Object b)` — preservada |
| `String` | `TString(SecureRandom r, String b)` — preservada |

Controle com o exemplo canônico: `SafeSyncMap(Map, Set+, Iterator)` → `.rvm` preserva os três.

**Um array de tipo primitivo na lista de parâmetros apaga a lista inteira**, não apenas o
parâmetro ofensor. O JavaMOP conclui com `rc=0` e a mensagem normal `"… .rvm is generated"`;
nenhum aviso, nenhum erro.

A consequência a jusante é total. Rodando o rv-monitor sobre os dois `.rvm`:

| spec | indexação gerada |
|---|---|
| `TObj` (parâmetro `Object`) | `CachedWeakReference wr_b = new CachedWeakReference(b)` — fatiamento real por objeto |
| `TByteArr` (parâmetro `byte[]`) | **zero** ocorrências de `CachedWeakReference` ou `IndexingTree` — um monitor global |

**Por que isto reordena o plano.** A cadeia do IV — o exemplo trabalhado do próprio §7.4 —
declara `IvChainSpec(SecureRandom r, byte[] iv, IvParameterSpec spec, Cipher c)`. Ela não compila
para o que o plano descreve: compila para um monitor único e global, que é precisamente o defeito
que o mecanismo B deveria curar. E a família atingida é a maior: `randomized` sobre `byte[]` são
**21 das 27 leituras vivas**, mais `char[]` no `PBEKeySpec`.

**O contorno existe e funciona.** Declarar `Object` e ligar no pointcut contra o argumento
`byte[]` preserva os parâmetros e produz indexação por identidade genuína — foi o caso `TObj`
acima, cujo pointcut é `call(void SecureRandom.nextBytes(byte[])) && args(b)` com `Object b`. Ou
seja: o mecanismo B **é** viável para a família `byte[]`, mas só através de um idioma de
declaração não óbvio que precisa estar escrito no design e travado por gate.

**Gate novo que a auditoria propõe — G-PARAM.** A lista de parâmetros da `.mop` tem de sobreviver
íntegra no `.rvm`. É uma comparação de duas linhas e pega uma classe de falha que hoje é
inteiramente muda.

### 4.2 O piloto `Mac`/`Key` não decide a questão — falha de projeto

O plano diz: *"o piloto que decide é o mais barato do grafo — `Mac`/`Key`, k=2"*. `Mac` e `Key`
são ambos tipos-objeto. O piloto passaria, o mecanismo B seria adotado como padrão, e a falha
apareceria depois, silenciosamente, em toda cadeia que tocasse `byte[]`.

**Recomendação: o piloto tem de ser a cadeia do IV, não `Mac`/`Key`** — é ela que exercita o caso
difícil. Se um segundo piloto barato for desejado, `Mac`/`Key` serve como controle positivo.

### 4.3 O evento de criação — CONFIRMADO empiricamente

O plano identifica corretamente o ponto difícil. No monitor gerado para `TObj`, o evento não
criador:

```java
public static final void TObj_useEvent(Object b) {
    ...
    if (TObj_activated) {
        ...
        TObjMonitor_Set node_b = TObj_b_Map.getNodeWithStrongRef(b);
        if (node_b != null) { matchedEntry = node_b; }
        if ((matchedEntry != null) ) { matchedEntry.event_use(b); }
    }
```

Sem monitor pré-existente, `matchedEntry` é `null` e **nada acontece**: nem criação, nem relato.
E `TObj_activated` só é ligado pelo evento criador — se o primeiro evento observado no processo
for o consumidor, a spec inteira fica inerte. O traço violador é exatamente esse. Nota lateral:
o cache de despacho compara com `b == TObj_b_Map_cachekey_b`, mais uma confirmação de identidade.

### 4.4 Genericidade do mecanismo B — CONFIRMADO e reforçado

O plano pergunta se as specs `generic` já usam multiparâmetro. Usam, em escala:

| aridade da spec | `generic` (118) | `generic_new` (27) | `jca_android` (23) |
|---:|---:|---:|---:|
| k=0 | 0 | 13 | 2 |
| k=1 | 21 | 8 | 21 |
| k=2 | 40 | 4 | 0 |
| k=3 | 30 | 2 | 0 |
| k=4 | 17 | 0 | 0 |
| k=5 | 6 | 0 | 0 |
| k=6 | 4 | 0 | 0 |

**82% de `generic` é multiparamétrico, até k=6.** O mecanismo B é neutro quanto ao domínio e já
está exercitado no próprio repositório muito além do k=4 que o plano propõe. Este é um argumento
a favor de B que o plano não usa e deveria.

### 4.5 Recomendação revista sobre o D4

O híbrido continua certo, mas **B não pode ser o padrão** como o plano recomenda. A partição é
determinada pelo tipo, não pela preferência:

- **Cadeias de tipos-objeto** (`KeyStore → KeyManagerFactory → SSLContext`, `KeyPair → Signature`,
  `Mac`/`Key`): mecanismo B, direto.
- **Cadeias que passam por `byte[]`/`char[]`** (toda a família `randomized`, `preparedIV`,
  `preparedGCM`, `preparedKeyMaterial` — a maioria das leituras vivas): mecanismo B **só** com o
  idioma `Object` e o gate G-PARAM, ou mecanismo A.
- **Posições de valor** (`alg`, `part(0,"/",transformation)`): sempre no corpo do evento, que é o
  que o oráculo faz de qualquer modo.

E a decisão continua não devendo ser tomada no papel — mas o piloto que a decide é a cadeia do IV.

---

## 5. A escada de verificação (§5.5)

**G-ORDER é decidível — CONFIRMADO.** A gramática Xtext de `Order`
(`CrySL.xtext:99-134`) é, na íntegra: `Sequence` (`,`), `Alternative` (`|`), `Cardinality`
(`*`, `+`, `?`), `Primary` (átomo de evento ou `( Order )`). Concatenação, união, fecho e
agrupamento — expressão regular pura, sem interseção, complemento, contagem ou retro-referência.
Os agregados de `EVENTS` (`Gets := g1 | g2`) também são regulares. Equivalência de AFD decide.

A dificuldade real do G-ORDER não é a decidibilidade e sim o **mapeamento de alfabeto** entre os
eventos do `ORDER` e os da `.mop` (que separa sobrecargas para poder ligar parâmetros, e portanto
não é uma bijeção). Isso precisa entrar no design como o trabalho que de fato é.

**C4 — CONFIRMADO literalmente.** `CogniCryptAndroidAnalysis.run()`:

```java
constructCallGraph();
//return runCryptoAnalysis();
return new ArrayList<>();
```

O ponto de entrada Android constrói o call graph e devolve lista vazia. O caminho JSE é obrigatório.

**A lógica de três valores — coerente, com um custo que o plano não contabiliza.** Ela é
consistente com o resto do documento e ataca a causa raiz certa. Mas muda a assinatura de
`validate()`, o que atinge **todos os 27 sítios de leitura** e o envelope da gh104 (um código novo
para "não observado"). Como o `jca` congelado chama o mesmo `ExecutionContext`, isso reforça o
R1: sem o store por conjunto de specs, esta mudança sozinha quebra o congelamento. A dependência
F0 → (três valores) → envelope precisa estar explícita no plano.

---

## 6. Consistência interna e lacunas de genericidade (§5.6, §3.3)

### 6.1 Consistência interna

- **§4.2 vs §7.4**: a emenda ficou coerente. A limitação da clonagem é de fato neutra entre os
  dois mecanismos, porque incide sobre o re-embrulho feito pela **aplicação**. Verificado: as
  cinco classes citadas clonam na entrada e na saída. O que **não** é neutro entre os mecanismos
  é o achado §4.1 desta auditoria — e o plano precisa dizer isso no mesmo lugar.
- **Fases F0–F5**: continuam coerentes. F3 precisa ser redimensionada de 19 para 35 itens.
- **R1–R5 / D1–D4**: cobrem o corpo, com duas ausências — não há risco registrado para a falha
  silenciosa de parâmetro (§4.1) nem para o mapeamento de alfabeto do G-ORDER (§5).
- **§8 (`rvsec-mop-defsuses`)**: os argumentos continuam válidos. Verificado:
  `PropertyExtractor` faz `properties.add(exp.getArguments().get(0)...)` e descarta o argumento 1;
  `explore(Expression)` despacha só `BinaryExpr` e `MethodCallExpr`, logo `!validate(...)`
  (`UnaryExpr`) é invisível; `javaparser-symbol-solver-core` está no `pom.xml:28` e não é usado em
  parte alguma do `src`; o módulo está no `<modules>` em `rvsec/pom.xml:27`. A recomendação de
  aposentar procede. *(A alegação sobre o caminho absoluto no `main()` não foi verificada.)*
- **Erro de citação**: o plano diz *"`data/jca_android/conformance_record.csv`, 60 linhas"* para a
  conformidade de CONSTRAINTS. São dois arquivos trocados: `conformance_record.csv` tem 74 linhas
  e trata de literais de allow-list; quem tem 60 linhas e compara CONSTRAINTS regra a regra é
  `constraint_table.csv`.
- **Citação abreviada**: o `SafeSyncMap.mop` transcrito no §7.4 omite a declaração de
  `asyncCreateIter`, que o `ere` usa. Não altera o argumento, mas a transcrição não é literal.

### 6.2 Lacunas de genericidade — o plano não cobre nenhuma delas

O universo real foi reconferido: 118 + 27 + 23 + 23 + 23 = **214 `.mop`**, como o handoff diz.

1. **Specs sem autômato algum.** `generic_new` tem **17 specs sem bloco `fsm`/`ere`** — são
   event-only, relatam direto no corpo do evento (ex.: `Closeable_MeaninglessClose`). Um gate de
   acusador órfão que pressuponha autômato emitiria **27 falsos positivos** ali. O plano não
   menciona a existência dessa forma de spec. **É a lacuna mais séria da lista.**
2. **`generic` não dá verde trivial.** Tem 1 órfão real (`FSM246.mop`, evento `event_2`). O gate
   precisa distinguir "órfão numa spec sem predicados" de "acusador órfão", ou reportar o achado
   como informativo.
3. **Degradação nos 11 arquivos que não compilam.** Confirmados os 11 com nome de parâmetro
   duplicado (`FSM119`, `FSM123`, `FSM133`, `FSM140`, `FSM197`, `FSM206`, `FSM209`, `FSM224`,
   `FSM45`, `FSM60`, `FSM69`) e a colisão de `import` em `FSM358.mop:4,6` (`Level` de
   `RVMLogging` e de `java.util.logging`). O plano não diz como os gates degradam. Contrato
   necessário: pular e **contar**, nunca falhar em silêncio nem estourar.
4. **G-ORDER sobre spec sem regra CrySL.** `generic/*` (118), `generic_new/*` (27) e
   `RandomStringPassword.mop` não têm contraparte. O gate tem de **pular declaradamente**, no
   padrão `skipped` do `gh104_gates.py`. O plano não diz isso.
5. **`predicate_graph.csv` sobre conjunto sem predicados.** Zero linhas tem de ser verde, não
   erro. O plano não garante.
6. **G-PARAM (novo).** Ver §4.1 — nenhum gate hoje detecta o colapso silencioso da lista de
   parâmetros.

---

## 7. O risco editorial D1 (§5.7) — CORRIGIDO

**A linha-base foi reproduzida dígito a dígito**: `RV=454, CC=423, both=112, só-RV=342,
só-CC=311`, com a mesma política de merge do `rq1_rv_cc.py` (chave
`apk × class × method × spec`, exclusão das regras None-mapeadas e ausentes).

Depois modelei o efeito das allow-lists api30, lidas do próprio `jca_android` e avaliadas com as
classes Java reais (`Api30CipherTransformationUtil.isValid`, `ConscryptAliasTable.matches`), não
por aproximação:

| cenário | só-RV | só-CC |
|---|---:|---:|
| publicado (`jca`) | 342 | 311 |
| api30, removendo só os eventos silenciados | **342** | **311** |
| api30 + alias, descartando a chave inteira (máximo) | **299** | **322** |
| *alegado pelo plano* | *~255* | *~354* |

**As allow-lists sozinhas movem zero células.** O filtro silencia 5.467 dos 15.444 eventos
`UnsafeAlgorithm`, mas a chave do venn é `(apk, class, method, spec)` e sobrevive enquanto
**qualquer** evento seu sobreviver — e quase toda chave carrega também um
`InvalidSequenceOfMethodCalls`. Ou seja: o venn é surdo à correção de allow-list.

**O efeito só aparece se as acusações de ordem acopladas caírem junto** — que é o descarte da
chave inteira, e é exatamente o reparo E5 dos acusadores órfãos, não a re-transcrição de
allow-list. Sob essa leitura máxima o resultado é **299 / 322**.

Dois controles que fecham o cálculo:

- **`CipherSpec` não contribui nada.** É o maior bloco de só-RV (69 de 342), mas seus 109 eventos
  `UnsafeAlgorithm` têm um único valor distinto — `RSA/ECB/OAEPWithSHA1AndMGF1Padding` — e as duas
  tabelas o **rejeitam**: `CipherTransformationUtil.isValid` e `Api30CipherTransformationUtil.isValid`
  devolvem `false` para ele. Zero mudanças de veredito. Os 69 são acusações de ordem.
- **A resolução de alias esgota o resto.** Sob a allow-list literal restavam 5 pares
  (spec, valor) ainda acusando — `MessageDigestSpec/SHA`, `MessageDigestSpec/SHA1`,
  `SignatureSpec/NONEWITHRSA`, `SignatureSpec/SHA256WITHRSA`, `TrustManagerFactorySpec/X509`.
  Todos os cinco casam sob `ConscryptAliasTable.matches`. Não há folga além de 299.

**Veredito.** A direção está certa e a manchete de fato cruza (299 < 322), mas a magnitude está
superestimada em cerca de 2× (−43 em vez de −87; +11 em vez de +43), e a margem final é de 23
achados, não de 99. Mais importante para a decisão do pesquisador: **o risco editorial não vem das
allow-lists, vem do reparo dos acusadores órfãos**. Isso muda qual dos três caminhos do D1 é o
mais barato — o caminho 1 ("não tocar nas specs para este artigo") deixa de proteger a manchete,
porque a gh104 já reparou um órfão e as duas changes vão reparar os outros 17.

*(O recálculo 255/354 do plano não está persistido em nenhum artefato da árvore; só existe como
asserção no documento. Os números desta auditoria são reproduzíveis.)*

---

## 8. Alegações não verificadas

| alegação | por quê |
|---|---|
| `equals` por valor das chaves concretas do Android (`OpenSSLRSAPublicKey`, `BCRSAPublicKey`) — R4 | as classes não estão nos fontes locais; exige teste em dispositivo, como o próprio plano diz |
| caminho absoluto no `main()` de `MOPSpecDefsUses` (§8) | não localizado no arquivo; as outras quatro alegações do §8 se confirmam |

---

## 9. O que fazer com este relatório

Correções já aplicadas ao plano: as quatro de §1, a de §2.5 (`-Xmx2g`), as três de §3
(extração imprecisa, posições por tipo, `NEGATES`), a de §3.4 (aridade), a de §6.1 (citação
trocada) e a de §7 (D1). Inserções novas: §4.1 (`byte[]`), §4.2 (piloto), §6.2 (genericidade) e o
gate G-PARAM.

O que fica para a change decidir, e que a auditoria não decide:

1. **O piloto do D4 passa a ser a cadeia do IV.** Ele é o caso difícil e o único que separa os
   dois mecanismos.
2. **F3 é redimensionada para 35 itens** (pares predicado × regra-consumidora).
3. **O D3 é reformulado**: a pergunta não é sobre `NEGATES`, é sobre oito `remove()` sem
   contraparte no oráculo.
4. **O D1 é reapresentado com 299/322 e a atribuição correta** — o risco é do reparo E5, não das
   allow-lists.
