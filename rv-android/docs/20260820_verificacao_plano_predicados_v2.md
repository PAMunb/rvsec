# Verificação do plano de fiação de predicados — segunda passada

**Objeto:** `docs/20260820_plano_fiacao_predicados.md` (1.082 linhas, corrigido pela primeira
auditoria) e `docs/20260820_auditoria_plano_predicados.md` (a própria primeira auditoria).
**Mandato:** `docs/20260820_handoff_verificacao_plano_predicados_v2.md` — auditar a auditoria,
fechar os itens abertos do §7 e verificar a coerência do plano corrigido.
**Método:** 8 agentes paralelos, cada um reexecutando as medições contra a fonte (specs, código
gerado, oráculo CrySL, dataset publicado) — nunca contra o texto. Evidência bruta preservada em
`audit/20260820_verificacao_plano_predicados_v2/agent{A..I}/` (relatórios, scripts, specs do
piloto).

| campo | valor |
|---|---|
| data | 2026-08-20 |
| ponto de medição | reator `rvsec` em `bd61abea` (confirmado; sem deriva desde `d27c48e9`) |
| frentes | A medições · B estrutural/genericidade · C gerador/OOM · D parâmetros · E venn D1 · F decisão §3.1-bis · H coerência · I piloto do IV |
| alegações reexaminadas | 58 |
| `SUSTENTADO` | 43 |
| `REFINADO` | 9 |
| `REVERTIDO` (da 1ª auditoria) | 4 |
| `AINDA ABERTO` | 2 (R4 em dispositivo; tecelagem ponta a ponta do idioma `Object`) |
| itens do §7 do handoff fechados | 7 de 9 (os 2 restantes são decisões do pesquisador ou exigem dispositivo) |

**Balanço em uma frase:** nenhum achado invalida o plano — as reversões atingem a **primeira
auditoria**, não o plano; depois das emendas `[auditado-v2]`, o plano está mais forte do que
antes da segunda passada, e o D4 agora tem um piloto **executado**, não recomendado.

---

## 1. Auditar a auditoria — vereditos por alegação

### 1.1 Medições numéricas (agente A)

| alegação da 1ª auditoria | veredito | evidência |
|---|---|---|
| enum `Property` = 25 valores | SUSTENTADO | contagem direta em `Property.java` |
| distribuição set/validate/remove (49/27/9; 21/4/8 valores) | SUSTENTADO | grep reproduzido valor a valor |
| 18 valores sem consumidor, 35 sítios | SUSTENTADO | 21−3=18; 49−(9+3+2)=35, valor a valor |
| zero sítios: só `MACED` e `GENERATED_CIPHER` | SUSTENTADO | `GENERATED_TRUST_MANAGERS` tem o sítio `TrustManagerFactorySpec.mop:101` |
| censo 134 = 23+27+49+9+25+1 | SUSTENTADO | soma exata; 42/7 é partição dos 49 `setProperty` (corpo/`@match`) |
| sem deriva `d27c48e9` ↔ `bd61abea` | SUSTENTADO | `git grep` nas duas revisões + diff: idêntico |
| oráculo: 33 regras, 54 ENSURES, 36 REQUIRES, 2 NEGATES, 32 predicados | SUSTENTADO | dois métodos de contagem independentes concordam |
| aridades 59 unárias / 29 binárias / 2 quaternárias; `generatedKey` aridade 4 | **REVERTIDO** | ver §2.1 |
| 19 conectáveis / 35 pares / 44 arestas | REFINADO | ver §2.4 |
| 2 NEGATES; ≤1 dos 9 `remove()` corresponde | SUSTENTADO | `SecretKey:30 after d` (sem evento `destroy` em spec alguma) e `PBEKeySpec after cP` ↔ `PBEKeySpecSpec.mop:74` |

### 1.2 Analisador estrutural e genericidade (agente B)

| alegação | veredito | evidência |
|---|---|---|
| órfãos 17/9 (`jca_android`), 18/10 (`jca`), 0 (`bug_predicate`) | SUSTENTADO | analisador reconstruído (`agentB/analyze_mop.py`), mesmos specs/eventos |
| validate 27 todos `condition`; setProperty 42/7; remove 8 `@fail` + 1 corpo | SUSTENTADO | idem; a contagem ingênua de `validate(` dá 31 — o helper privado `validate(int)` de `KeyPairGeneratorSpec` exige o discriminador `validate(Property` |
| `bug_predicate`: validate 56 = 33 condition + 23 fora | SUSTENTADO | 23 = 18 corpo de evento + 5 corpo de helper |
| `generic`: 1 órfão (`FSM246.mop`, `event_2`) | SUSTENTADO | exatamente 1 |
| `generic_new`: 17 specs sem `fsm`/`ere` | SUSTENTADO | 17 event-only, somando 27 eventos (bate com os "27 falsos positivos" do plano) |
| 11 dup-param + colisão `FSM358.mop:4,6` | SUSTENTADO | mesmos 11 arquivos, todos em `generic` |
| seis lacunas da §8-bis | SUSTENTADO | e há uma **sétima** — ver §3 |

### 1.3 Gerador (agente C)

| alegação | veredito | evidência |
|---|---|---|
| `n·(2ⁿ−1)` exato em n=14/16/17/18; sem `fail` ≈ 2 ms | SUSTENTADO | driver reconstruído (`agentC/Drive.java`); igualdade exata nas 4 linhas |
| OOM é do pipeline (toString + StreamGobbler), não do `FSMCoenables` | **REVERTIDO** em parte | ver §2.2 |
| "passar `-Xmx` destrava o CipherSpec" | **REVERTIDO** | ver §2.2 |
| R5 (falha mascarada, `waitFor` sem timeout, stderr concatenado) | SUSTENTADO **e agravado** | reproduzido ao vivo: OOM no filho vira `Logic Engine Error: null` com **exit 0**; um único byte no stderr do filho (a linha `Picked up JAVA_TOOL_OPTIONS`) quebra o parse do XML porque `executeProgram` concatena stderr após o stdout |

### 1.4 Colapso de parâmetro (agente D)

| alegação | veredito | evidência |
|---|---|---|
| `byte[]`/`int[]` apagam a lista inteira; `Object[]`/`Object`/`String` preservam | SUSTENTADO | matriz refeita; controle `SafeSyncMap` preserva os 3 |
| `char[]` colapsa (a 1ª auditoria só inferiu) | SUSTENTADO — **agora medido** | colapsa igual; atinge o `PBEKeySpec` |
| a falha é silenciosa (rc=0) | SUSTENTADO e agravado | até parse error duro de pointcut sai com rc=0 — o rc do javamop é inútil como gate |
| contorno via `Object` = indexação por identidade genuína | SUSTENTADO | `CachedWeakReference` + comparações `==`; arrays não sobrescrevem `hashCode` — sem armadilha. Refinamento de idioma: o overload tem de ser fixado na assinatura do `call(...)`, porque `args(b)` com `Object` casa qualquer argumento (inclusive autoboxing) |
| causa raiz | **FECHADO** (era item aberto) | ver §4.1 |

### 1.5 Venn do D1 (agente E)

| alegação | veredito | evidência |
|---|---|---|
| linha-base `454/423/112/342/311` dígito a dígito | SUSTENTADO | pandas puro seguindo `rq1_rv_cc.py:45-143` |
| allow-lists sozinhas movem zero células | SUSTENTADO | 342/311 inalterado, literal e com alias |
| leitura agressiva = 299/322, "não há folga além de 299" | **REVERTIDO** | ver §2.3 |
| risco editorial vem do E5, não das allow-lists | REFINADO | ver §2.3 |
| órfãos sustentam 70,4% da categoria ISoMC | SUSTENTADO | 49.817 reproduzido dígito a dígito; 314 de 454 chaves do venn em specs portadoras |

### 1.6 Decisão §3.1-bis (agente F)

| item | veredito | evidência |
|---|---|---|
| superfície pública da classe antiga completa | SUSTENTADO | única omissão: `instance()` (trivial — todo sítio passa por ele); nenhuma spec de conjunto algum chama nada fora da lista |
| `hasEnsuredPredicate`/`isInAcceptingState` com zero sítios em `.mop` | SUSTENTADO | só `rvsec-agent/src/test/.../Assertions.java` + 17 testes bench01; `SecureRandomTest.java:19` é o único sítio externo de `reset()` |
| specs que chamam `ExecutionContext`: 23/23/23/0/0 | SUSTENTADO | por arquivo, nos 5 conjuntos |
| classe nova oferece tudo que F0 pede sem tocar a antiga | SUSTENTADO | ressalva estrutural: `condition(...)` compila para guarda booleana — os três valores só são consumíveis no **corpo** do evento, exatamente o que F2 já planeja |
| 4 sítios de `remove(Property)` 1-arg no `jca` | SUSTENTADO | `KeyManagerFactorySpec.mop:91`, `MacSpec.mop:87`, `TrustManagerFactorySpec.mop:87-88` |
| G-PRED precisa ser reformulado | SUSTENTADO e **dimensionado** | ver §4.2 |
| gate de disciplina de import factível | SUSTENTADO | ver §4.3 |
| caminho absoluto no `main()` do defsuses | **FECHADO** — confirmado com atribuição corrigida | ver §4.4 |

### 1.7 Coerência do plano corrigido (agente H)

O plano **já incorpora** a decisão §3.1-bis em F0, R1, D3 e D4 — a premissa do handoff ("o plano
ainda não incorpora") estava parcialmente desatualizada. Sobraram **8 problemas**, todos emendados
com a marca `[auditado-v2]`:

1. §4.4 ainda concluía com a formulação superseded "uma implementação de store por conjunto".
2. §7.4 dizia "store **corrigido**" — sob a decisão, nada é corrigido; o mecanismo A é a classe nova.
3. §5 (três valores) não dizia o custo (27 sítios + envelope) nem onde a decisão o confina.
4. §7.4 apresentava a `IvChainSpec(…byte[] iv…)` sem aviso de que essa assinatura não compila (§7.5).
5. §4.2 declarava a clonagem "não é critério de escolha" sem apontar que o critério real existe (§7.5).
6. §7.2 condicionava F0 só à §7.4, ignorando que o piloto (D4) decide e o precede.
7. Faltava o risco do mapeamento de alfabeto do G-ORDER — entrou como **R7**.
8. F5 citava `conformance_record.csv` como irmão do `predicate_graph.csv`; o irmão é `constraint_table.csv`.

Varredura de resíduo numérico: **limpa** (nenhuma ocorrência viva de 24 valores, 19 arestas,
17/33, 255/354 fora do rótulo "estimativa anterior", Mac/Key como piloto decisor).

### 1.8 Piloto da cadeia do IV (agente I)

Executado — ver §5.

---

## 2. Reversões da primeira auditoria — qual e por quê

A auditoria anterior é documento vivo; estas quatro correções incidem sobre **ela** (o plano já
carrega as versões corrigidas via `[auditado-v2]`).

### 2.1 Aridades: 59/31/0, máximo 2 — não 59/29/2

As "2 quaternárias" (`Cipher.cryptsl:174,178`) contavam as vírgulas **internas** do splitter
`part(0,"/",transformation)`, que é **um** parâmetro CrySL. Estruturalmente: 59 unárias, 31
binárias, aridade máxima 2. A linha "`generatedKey` chega a aridade 4 — CONFIRMADO" da auditoria
não se sustenta: as seis cláusulas `generatedKey[...]` do api30 são todas binárias. A conclusão
substantiva ("31 das 90 cláusulas precisam de aridade ≥ 2") sobrevive intacta.

### 2.2 O bloqueio do gerador em n=18 não é OOM — e 17 nunca foi bloqueio

Pipeline real medido (`rvj.Main` → filho `logicrepository.Main`):

- **`CipherSpec` real (17 eventos) gera em toda configuração** — inclusive `-Xmx1g` no pai **e**
  no filho (~53 s). O "teto de 17" nunca bloqueou a viabilidade; o re-orçamento 17→14 **não é
  necessário** para viabilidade.
- **n=18: o modo dominante é `StackOverflowError` no processo PAI**, no regex de
  `EnableSet.parseSets` (`EnableSet.java:66-116`), com **qualquer** heap (1g/2g/24g/default). O
  filho completa com exit 0 em ~30 s já com `-Xmx2g`. `-Xss` já está no máximo aceito pela JVM
  (rejeita `-Xss1025m`+). **n=18 não é destravável por flag nenhuma** — só com patch em
  `parseSets` ou supressão dos coenables de `fail`.
- O OOM verídico existe apenas no **filho** com heap < ~2 GB (`-Xmx1g` → "Java heap space") — e é
  sempre mascarado: o pai imprime `Logic Engine Error: null` e sai com **exit 0**, sem monitor.

A frase da auditoria "o estouro é do pipeline completo, não do cálculo" estava certa; a hipótese
"`toString()` + `StreamGobbler`, e `-Xmx` destrava" estava errada nos dois lados.

### 2.3 O venn do D1: 300/322 no cenário estreito — e 299 não era teto

- O cenário "api30 + alias, descartando a chave inteira" dá **300/322**, não 299/322. Off-by-one
  diagnosticado: a chave do `MacSpec` (31 eventos `UnsafeAlgorithm` com valor observado **vazio**)
  não pode cair, porque valor vazio não é admitido por `matches()` — sob a própria modelagem da
  auditoria.
- **"Não há folga além de 299" está revertido.** Estendendo o mesmo silenciamento às categorias
  `UnsafeProtocol` (`SSLContext` admite TLS/SSL — 8.751 eventos) e `InvalidKeyStoreType`
  (`AndroidKeyStore` admitido — 2.005) — exatamente os dois casos do apêndice
  `rv-only-examples.tex` que o próprio plano declara que "deixam de ser violações" — o resultado é
  **255/355**, recuperando quase exatamente a estimativa original do plano (~255/~354). A
  auditoria estreitou a categoria a `UnsafeAlgorithm` sem declarar.
- A atribuição "o risco vem do E5, não das allow-lists" fica **parcialmente invertida**: nas 53
  chaves do cenário 300/322, o reparo de allow-list **como escrito no `jca_android`** derruba
  sozinho o report e a acusação de ordem acoplada (a guarda co-emite os dois); o E5 sozinho não
  derruba nenhuma delas. O E5 tem, sim, o alcance maior (E5-máx: 247/339; tudo combinado:
  160/383). A conclusão prática sai **reforçada**: a manchete publicada está exposta pelos dois
  lados, e o caminho 1 do D1 ("não tocar nas specs") continua não a protegendo.

### 2.4 "35 pares" é a unidade quase certa — o rótulo exato é outro

20 predicados exigidos, 1 sem produtor (`preparedEC`) ⇒ 19 conectáveis ✓; 44 arestas
produtora→consumidora ✓. Mas 35 é a contagem de **cláusulas `REQUIRES` conectáveis** (36 − 1);
como pares **distintos** (predicado, regra-consumidora) são **34**, porque `Mac.cryptsl` exige
`encrypted` em duas cláusulas. F3 = 35 itens continua correto — cada cláusula é uma fiação
distinta — só o rótulo muda.

---

## 3. A sétima lacuna de genericidade (e duas menores)

**S1 — órfão reverso e evento duplicado (a sétima lacuna).** `jca/GCMParameterSpecSpec.mop`
declara `event c1` **duas vezes** (linhas 23 e 34) e o `ere : c1 | c2` (linha 48) referencia um
`c2` **nunca declarado**; idêntico em `jca_android_bug_predicate` (23/34/48); `jca_android` já
está corrigido. São os únicos 2 casos nos 214 `.mop`. O gate de órfão precisa checar também a
direção `usados − declarados` e tratar o alfabeto declarado como multiconjunto — e registrar que
o congelado diverge do alvo aqui.

**S2 — sombreamento de nome da API.** Helpers privados chamados `validate` (`KeyPairGeneratorSpec`
nos 3 conjuntos jca; `generic_new/TreeMap_Comparable.mop:21,30,41`) e 10 chamadas `.remove(` de
coleções em `generic`/`generic_new`: gate que casa por nome de método erra; o discriminador
obrigatório é `(Property`.

**S3 — handlers via alias.** 5 specs por conjunto jca usam `@match1` via `alias match1 = <estado>`
(ex.: `jca_android/CipherSpec.mop:222`); gate com nomes fixos `{@match, @fail}` erra a partição
42/7 se não resolver aliases.

Fato adicional útil: **zero** das 214 specs tem hoje parâmetro primitivo/array — o colapso da
§7.5 é prospectivo (aconteceria na F3); o G-PARAM protege o futuro, não conserta o presente.

---

## 4. Itens abertos do §7 do handoff — estado final

| item | estado | resultado |
|---|---|---|
| `char[]` como parâmetro | **FECHADO** | colapsa, medido (§1.4) |
| causa raiz do colapso | **FECHADO** | §4.1 abaixo |
| onde nasce o OOM | **FECHADO** | §2.2 — e a conclusão prática mudou |
| piloto da cadeia do IV | **FECHADO** | executado; §5 |
| reformulação do G-PRED | **FECHADO** (dimensionado) | §4.2 |
| gate de disciplina de import | **FECHADO** (esboçado) | §4.3 |
| caminho absoluto no defsuses | **FECHADO** | §4.4 |
| R4 — `equals` das chaves concretas | AINDA ABERTO | exige dispositivo; nada mudou |
| D1–D4 | do pesquisador | números prontos (§2.3, §5, plano D1–D4) |

### 4.1 Causa raiz do colapso de parâmetro — localizada, com correção possível

Assimetria de gramática + catch silencioso, **duplicada nos dois tradutores**:

- `javamop/src/main/javacc/javamop/parser/main_parser/javamop.jj:1456` — `SimpleTypePattern()`
  (parâmetros de **spec**) aceita só `<IDENTIFIER>|get|set` na cabeça do tipo;
  `javamop.jj:1470` — `TypePattern()` (parâmetros de **evento**) aceita as keywords primitivas.
  Por isso os eventos preservam `byte[]` e a spec não.
- `javamop/.../parser/JavaParserAdapter.java:320-327` — `convertParameters()` faz
  `catch (Exception e) { /*e.printStackTrace();*/ return null; }` → lista nula → `T()`.
- Espelho exato no rv-monitor: `RVMonitorParser.jj:876` + `rvj/JavaParserAdapter.java:233-240`
  (lá o stack trace é impresso, mas ainda gera monitor global com rc=0).

**Correção barata existe, mas exige patch DUPLO** (javamop **e** rv-monitor — só o javamop não
basta, porque o rv-monitor re-parseia o `.rvm` e colapsa de novo): um ramo
`("byte"|…|"char") ("[" "]")+` em ambos os `SimpleTypePattern()` (primitivo só com array, pois
primitivo nu não fatia) e trocar `return null` por relançar. `Object[]` já passa de ponta a
ponta — o bloqueio é puramente léxico. Há precedente de patch local (o descritor JSON do javamop).
**Isso muda o enquadramento do D4: a limitação é de toolchain reparável, não semântica** — mas o
patch é decisão do pesquisador; o contorno `Object` funciona sem ele.

### 4.2 Reformulação do G-PRED — média, não uma linha

Hoje `gh104_gates.py::predicate_divergences` (l.1014-1051, fiação 1454-1468) compara por arquivo
a sequência de linhas com `ExecutionContext` contra a semente congelada do `jca`; o pytest de
INV-INS-128 exige adicionalmente o censo exato (134 linhas, 23 specs). Na migração, tudo falha
nos 23 arquivos. Dimensionamento: manter G-PRED como cadeado do `jca`; **aposentá-lo para
`jca_android` e substituí-lo por G-PRED2 + `predicate_graph.csv`** (F5). Dano colateral a orçar
junto: `accept_requires` (l.1189-1191) decide o G-2 grepando `ExecutionContext` (falsos
vermelhos), a regex `PREDICATE_CALL` (l.514-517) é cega para a classe nova e para aridade N, o
pytest precisa ser reescrito, e a política do `divergence_record`/INV-INS-118 para as ~134 linhas
reescritas precisa ser decidida.

### 4.3 Gate de disciplina de import — factível, com predicado mais forte

Não existe wildcard `br.unb.cic.mop.*` em conjunto algum, mas o predicado por `import` não pega
uso fully-qualified. O predicado recomendado:

```bash
grep -rlw 'ExecutionContext' rvsec/rvsec-mop/src/main/resources/jca_android --include='*.mop' | wc -l   # deve ser 0
```

### 4.4 O caminho absoluto do defsuses — confirmado, atribuição corrigida

A alegação do plano se confirma na substância, com o arquivo errado: o `main()` com caminho
absoluto está em **`rvsec/rvsec-mop-defsuses/.../DefsUsesGraph.java:65-66`**, não em
`MOPSpecDefsUses.java` (modelo de dados, sem `main`). Agravantes: `listFiles()` sem recursão
(l.23) → zero `.mop` → diagrama vazio; e o caminho usa o alias `/pedro/...`, que não resolve na
JVM → `listFiles()` devolve null → NPE engolido. A recomendação de aposentar o módulo sai
reforçada.

---

## 5. O piloto da cadeia do IV — executado, e a recomendação do D4

O agente I executou o piloto (specs e drivers em `audit/.../agentI/`), injetando eventos pelos
despachantes estáticos do monitor gerado (o contrato do `TraceRunner`), sem emulador e sem tocar
nas specs de produção.

**Constatação prévia:** duas specs separadas compartilhando o `byte[]` não têm canal algum no
JavaMOP (mapas e monitores próprios, zero referências cruzadas) — "specs se comunicando" **é** o
`ExecutionContext`, ou seja, mecanismo A. O mecanismo B real é **uma spec de junção por cadeia**.

**Resultados:**

1. **B funciona no caso difícil.** `IvChainFsmSpec(Object iv, IvParameterSpec spec, Cipher c)`
   com o contorno `Object`: lista sobrevive no `.rvm`, fatiamento real por identidade, e com dois
   `byte[]` no mesmo processo o veredito é exato — o traço bom dá 1 MATCH e zero FAIL; o ruim dá
   FAIL em `mk` (`REQUIRES randomized`) **e** em `use` (`REQUIRES preparedIV`), na instância
   certa, com bindings certos; consumidor sem cadeia observada: silêncio.
2. **B ingênuo acusa o caso bom** (achado novo): com `use` como evento criador, a instância
   parcial `(spec, c)` não enxerga `gen`/`mk` e falha — falso positivo no traço correto. Regra:
   **consumidor nunca é `creation`**. O silêncio resultante no cenário consumidor-só é a lógica
   de três valores da §5 implementada estruturalmente — argumento novo a favor de B.
3. **Joins produto-cruzado acontecem mesmo sem creation no consumidor** (achado novo): sem o laço
   benigno para instâncias desconexas, o `iv` randomizado de **outra** cadeia gera FAIL espúrio.
   Laço benigno é obrigatório.
4. **§7.5 reproduzido na cadeia real**: `byte[] iv` declarado → lista inteira apagada, rc=0,
   monitor global. G-PARAM indispensável.
5. **De graça no caminho B**: `WeakReference` + `TerminatedMonitorCleaner` +
   `AbstractSynchronizedMonitor` — os três defeitos do §4.3 do plano (referências fortes, sem
   expurgo, sem sincronização) não existem nesse caminho. Custo do gerador trivial: 3 eventos,
   k=3 (o k=4 do esboço é desnecessário), coenable 21 contra 2,2 M do `CipherSpec`.

**Recomendação D4 (fundamentada, para o pesquisador decidir):** o híbrido da §7.6, agora com
evidência executada — B para cadeias co-observáveis, **inclusive a família `byte[]` via idioma
`Object`**, condicionado a quatro regras de design gateáveis: (a) consumidor nunca é `creation`;
(b) laço benigno para joins desconexos; (c) estado para handlers via campos do monitor
(parâmetros de spec não são visíveis em `@match`/`@fail`); (d) G-PARAM. Mecanismo A (classe nova
da F0) para posições de valor, arestas sem cadeia co-observável e o que mais sobrar.

**Não testado (limites honestos):** tecelagem ajc/dexlib2 de ponta a ponta do binding
`Object`↔`byte[]` no `.aj`; coexistência com `CipherSpec` no mesmo joinpoint (dedup de relato);
memória em escala dos joins desconexos (O(#gen × #use) monitores calados); re-embrulho por getter
(§4.2 — neutro entre A e B); integração com `ErrorCollector`/envelope gh104.

---

## 6. Emendas aplicadas ao plano (marca `[auditado-v2]`)

| # | seção | emenda |
|---|---|---|
| 1 | §2.1 | rótulo da unidade: 35 = cláusulas `REQUIRES` conectáveis (34 pares distintos) |
| 2 | §2.2 E2 | aridades 59/31/0, máx. 2; removida a alegação "generatedKey aridade 4" |
| 3 | §4.2 | a assimetria real entre A e B é a §7.5, não a clonagem |
| 4 | §4.4 | conclusão alinhada à decisão §3.1-bis (classes novas, antigas intocadas) |
| 5 | §5 | custo dos três valores + confinamento pela F0 + nota do `condition()` booleano |
| 6 | §7.2 F0 | condicionamento reescrito: o piloto (D4) precede o dimensionamento de F0 |
| 7 | §7.2 F0 | dimensionamento da reformulação do G-PRED (médio; colaterais nomeados) |
| 8 | §7.3 | consequência 1 reescrita: 17 gera com 1 GB; n=18 é teto duro do parser do pai |
| 9 | §7.4 | título e mecanismo A: "store novo", não "store corrigido"; aviso na `IvChainSpec` |
| 10 | §7.5 | `char[]` medido; causa raiz com arquivo:linha; patch duplo possível; rc inútil como gate; idioma do overload |
| 11 | §7.6/D4 | piloto executado, resultados e as quatro regras de design |
| 12 | §8 | atribuição do caminho absoluto: `DefsUsesGraph.java:65-66` |
| 13 | §8-bis | sétima lacuna (órfão reverso) + S2/S3 + "G-PARAM é prospectivo" |
| 14 | R1 | predicado do gate de import com `-w` (pega uso fully-qualified) |
| 15 | R2 | reescrito: sem alavanca de flag para n=18; 17 nunca foi bloqueio |
| 16 | R5 | confirmação ao vivo + o byte de stderr que quebra o parse |
| 17 | R7 | novo risco: mapeamento de alfabeto do G-ORDER |
| 18 | D1 | tabela e atribuição reescritas: 300/322 estreito, 255/355 defensável, exposição pelos dois lados |
| 19 | F5 | `predicate_graph.csv` como irmão do `constraint_table.csv` |

---

## 7. O que permanece aberto para a change

1. **R4** — `equals` das chaves concretas do Android: exige dispositivo (via `rv-experiment`/
   `rv-platform`, nunca emulador manual).
2. **Tecelagem ponta a ponta do idioma `Object`** — o piloto validou até o monitor; falta o `.aj`
   tecido num APK real (cabe no experimento de validação conjunto, `experimento-gh104/`).
3. **Decisões do pesquisador**: D1 (com 300/322–255/355), D2 (escopo), D3, D4 (com o piloto
   executado), o patch duplo da §4.1, a entrada do R7 e a política do `divergence_record` na
   reformulação do G-PRED.
