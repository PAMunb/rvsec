# gh69 — o tratamento de coringas é completo? Veredito medido

**Data**: 2026-08-21 · **Issue**: #69 · **Change**: `openspec/changes/gh69-generic-subtype-target-matching/`
**Natureza**: análise. Nada foi implementado, nenhum artefato OpenSpec foi editado, nenhum emulador foi tocado.
**Método**: seis linhas de medição independentes, cada uma re-derivando os números do corpus, do bytecode ou
do código, com o comando à vista.

---

## 1. O veredito, em três frases

No eixo estrito dos coringas — import com asterisco, owner por subtipo `+`, nome de método com coringa — a
change **não é meia-boca**: as três capacidades têm requisito, tarefa e teste, a decisão A2 está correta
(verificada por desmontagem do bytecode do Soot, não por javadoc), e o corpus não contém nenhum dos casos
perigosos que se poderia temer.

Mas o produto que a change promete reparar — o sinal estático do conjunto `generic_new` — **satura no eixo
transitivo e sobrevive no eixo direto**. O `reachesTarget` colapsa sobre `reachable` (84–94% dos métodos) e
vira a métrica trivial "o método é alcançável"; o `directlyReachesTarget` sai de 0,0–0,3% para 2–12% e é o
único dos dois que continua separando métodos.

E a mitigação que a change registra para isso — delegar a filtragem de owners quase-universais para a change
downstream — **está empiricamente refutada**: remover 34 dos 67 pares não move o `reachesTarget` em nenhum
APK médio ou grande.

**Recomendação: implementar, com o escopo reafirmado sobre o `directlyReachesTarget`** — ver §7.

---

## 2. O que foi medido, e como

| # | Eixo | Instrumento |
|---|---|---|
| 1 | Saturação em APK real | `dexdump -d` sobre 8 APKs (0,2–75 MB; 205.519 métodos, 827.443 call sites), hierarquia parseada do `android.jar`, fecho reverso com bracket LB/UB |
| 2 | Lacunas (a) e (b) | Sonda de AST compilada contra o `mop-extractor.jar` da árvore; gramática `aspectj.jj`; leitura do GATOR |
| 3 | Lacunas de restrição e parâmetro | Parser AST-lite por evento sobre os 73 `.mop` dos três conjuntos; 3 APKs para o efeito da poda |
| 4 | A2 e coringas de nome | `javap -p -c` sobre `FastHierarchy`/`SootClass` do Soot 4.7.1; sondas `Class.forName` sobre o `android.jar` |
| 5 | Artefatos da change | Leitura integral dos 5 artefatos + rastreabilidade + `openspec validate --strict` |
| 6 | Corpus | Parser próprio validado à mão contra 4 specs e cruzado com regex independente; extrator real rodado sob JDK 21 |

**Calibração do pipeline de medição.** O eixo direto foi validado contra o `directlyReachesTarget` real
gravado nos `*.apk.json` do conjunto `jca`: bateu em 7 dos 8 APKs, com `cryptoapp` exato (21 = 21). As
frações "direto" deste documento são medida, não estimativa. O eixo de subtipo tem ≤0,15% de call sites com
hierarquia incompleta.

---

## 3. O que a change entrega — e entrega bem

**As três capacidades coringa fecham fim a fim.** Cada uma tem requisito (INV-ANA-40/41/42), tarefa e teste,
com cardinalidade fixada *a priori* (67/66) em vez de "o que a implementação emitir", e com o caso
`List <: Iterable` isolado como o único que distingue A2 de A1.

**A2 está correta, e agora tem lastro de bytecode.** Desmontando `FastHierarchy.canStoreType` do Soot 4.7.1:

- classe→interface: cobre, via `getAllImplementersOfInterface` ou `canStoreClassClassic`;
- **interface→interface: cobre**, via `getAllSubinterfaces(parent).contains(child)` — é exatamente a
  propriedade que refuta A1, e o ADR 0004 estava certo;
- `parent` phantom ou não resolvido: **não lança**; `checkLevel` passa porque phantoms ficam em `BODIES`;
- primitivos e arrays: retornam `false` sem exceção, e são irrelevantes aqui (o lado esquerdo é sempre
  `RefType`, vindo de `getDeclaringClass().getType()`).

**O corpus não contém nenhum dos casos perigosos:**

| risco temido | ocorrências no corpus |
|---|---|
| `+` combinado com `*` nu (todo método de toda subclasse) | **0** — os dois `*` nus são `Iterator.*`, owner exato, sem `+` |
| coringa no meio ou início do nome (`*Foo`, `a*b`) | **0** — todo coringa é sufixo |
| owner com coringa (`java.util.*` como owner, `*Stream`) | **0** |
| tipo array, primitivo ou parametrizado como owner | **0** |
| ambiguidade de import-asterisco | **0 real**; 1 latente e inerte (`Proxy` em `java.lang.reflect` × `java.net`, numa spec que não o usa) |

Os 23 owners existem no `android.jar` (conferido em android-30 e android-34). A decisão de **não** semear
`java.lang` está correta e não custa nada ao `generic_new`: as sete specs com owner de `java.lang` declaram
`import java.lang.*;` explicitamente.

`openspec validate gh69-generic-subtype-target-matching --strict` passa; os quatro artefatos de planejamento
estão completos.

---

## 4. O que a medição derruba

### 4.1 O número-título compara grandezas diferentes

O "120 (jca) contra 67 (generic_new)" mistura duas convenções: o 120 conta **assinaturas** e **inclui**
construtores; o 67 conta **pares (owner, método)** e **exclui** construtores. Sob convenção única:

| convenção | `jca` | `generic_new` |
|---|---|---|
| assinaturas (a que produz o 120) | 120 | **72** |
| pares (owner, método) | 68 | **69** |
| pares sem construtor | 59 | 67 |

E há um agravante — §4.2. Contando só o que resolve hoje, o `jca` tem **57 pares vivos**; o `generic_new`
reparado teria **67**. O conjunto genérico produziria **mais** alvos vivos que a régua congelada, não metade.

Número correlato que os artefatos não declaram: apenas **54** dos 67 pares carregam `+`. É esse 54 — não 67
nem 71 — o número de alvos que entra no caminho `canStoreType`. A RISK-005 diz "limitado por 67".

### 4.2 Onze alvos mortos no conjunto congelado `jca`

O extrator já emite construtores: `jca` produz **18 linhas** com `method=new`, que colapsam em **11 pares
distintos** de 68 — `SecureRandom.new`, `IvParameterSpec.new`, `SecretKeySpec.new`, `PBEKeySpec.new`,
`CipherInputStream.new`, `CipherOutputStream.new`, `GCMParameterSpec.new`, `PBEParameterSpec.new`,
`DHGenParameterSpec.new`, `KeyPair.new`, `HMACParameterSpec.new`.

O casamento é igualdade de string (`TargetResolver.java:53`) e `SootMethod.getName()` de construtor é
`<init>`. **Essas 11 chaves não casam com nada.** O scan de bytecode não recupera: `targetKeys` é derivado do
`Set<SootMethod>` já resolvido (`RvsecAnalysisClient.java:583-585`), então chave morta no resolver é chave
ausente no scan.

Consequência: a régua de medição publicada **nunca contou call site de construtor** — inclusive
`new SecretKeySpec(...)` e `new IvParameterSpec(...)`, que são centrais no mau uso de JCA. Nenhum artefato da
gh69 registra isso.

O reparo é ~6-8 linhas em um arquivo do extrator, sem nenhuma mudança no GATOR (o `SignatureFileTargetSource`
já aceita `<init>`; sua regex `([^(]+)` sempre esteve pronta). **Barato de implementar, caro de aprovar** —
move `reachesTarget` no conjunto congelado e exige re-baseline de `test_reachability_parity.py:156` e de
`BaselineComparisonIT`. É change própria, não da gh69. Mas a justificativa registrada para excluí-lo ("sem
mapeamento new→`<init>`") apresenta como limitação técnica o que é, de fato, decisão de congelamento.

### 4.3 A saturação: medida, e o sinal se parte em dois

Oito APKs, denominador alinhado ao conjunto de classes que o `apk.json` enumera:

| sinal | `jca` (medido, real) | `generic_new` (medido, reparado) |
|---|---|---|
| `directlyReachesTarget` | 0,0 – 0,3% | **2 – 12%** |
| `reachesTarget` | 11 – 47% | **84 – 94%** (limite inferior rigoroso) |

O limite inferior do `reachesTarget` **ultrapassa a própria fração `reachable`** da âncora em 4 dos 8 APKs
(mupen 93,8% > 82,4%; rcx 91,7% > 86,9%; flym 87,5% > 85,3%; quicknote 87,2% > 79,5%). O gargalo deixa de ser
o alvo e passa a ser o conjunto alcançável — isto é, `reachesTarget` vira `reachable` com outro nome.

Em escala bruta: **34.411 de 827.443 call sites (4,16%) casam com algum dos 67 pares**, contra 225 (0,027%)
para o `jca` — **153× mais**.

### 4.4 A RISK-004 erra os exemplos, não tem número, e sua mitigação não funciona

**Erra os exemplos.** `Object+` são 169 call sites em 827.443 — **0,02%**, um dos pares mais raros do corpus;
`Object+.notifyAll` marca **zero** métodos em toda a amostra. `Comparable+.compareTo` é moderado (0,31%).
`Iterable+` é largo por *um* dos seus dois métodos (`iterator` 1,84%; `listIterator` marca zero).

Os vetores reais, na ordem medida: `Collection+.add*` (2,50%), `CharSequence+.equals` (2,10%), a família
`Iterator` (1,88% × 4), `Iterable+.iterator` (1,84%), `Collection+.iterator` (1,68%), `Closeable+.close`
(1,12%). Nenhum dos três primeiros está nomeado na RISK-004.

**Não tem número.** Grep por `saturat|near-true|quasi-universal` em toda a change dá 14 ocorrências e
**nenhuma carrega um valor medido**: "a huge fraction", "almost everywhere", "saturates near-true". Note a
assimetria — o falso-*negativo* do `RandomStringPassword` foi medido a 74/17/57 sobre 3 APKs, mas o
falso-*positivo* que a change **introduz** não foi medido em APK nenhum.

**A mitigação está refutada.** Descartar os 34 pares da família coleções/iterador/CharSequence **não move o
`reachesTarget`**: quicknote 1752→1752, geometerplus 1358→1358, rcx 2514→2513, flym 2247→2245, mupen
2342→2340. Só os APKs minúsculos reagem. O resíduo de I/O (`InputStream+`, `OutputStream+`, `Reader+`,
`Writer+`, `Closeable+`) sozinho já está espalhado o bastante para reproduzir a saturação. **Filtrar owners —
a solução que a RISK-004 delega para downstream — não conserta o `reachesTarget`.** No máximo conserta o
`directlyReachesTarget`, que não precisa de conserto.

### 4.5 O consumidor quebra no mesmo commit

`reachesTarget` tem três consumidores, e a saturação atinge cada um de um jeito:

1. **Ranking do rv-agent** (`scorers.py:111-113`): três níveis — direto > transitivo > nenhum. Degrada com
   elegância: o nível direto continua discriminando.
2. **`StateMopDensityScorer`** (`scorers.py:242`): densidade = widgets marcados / totais. Com saturação vira
   ≈1,0 em toda tela — escalar constante, sinal zero. Está desligado por padrão.
3. **`cov_reaches_target` = `mop_method_coverage`** (`result_processor.py:487`,
   `coverage.py:438`): `called_target_methods / total_target_methods`. É **variável dependente do
   experimento**. Com o denominador saturado, converge para `method_coverage` — a métrica passa a duplicar
   uma que já existe e **para de distinguir ferramentas**.
4. **`aperv-tool`**, já em produção: `sa_methods_reaches_mop` é usado como covariável de tamanho
   (`static_artifact.py:13-17`) e degenera para `total_methods`; o veredito `hot`/`cold`
   (`static_artifact.py:288-296`) classifica praticamente tudo como `hot`.

O item 4 é o que a RISK-004 subestima ao chamar de "downstream concern" — e o próprio `design.md:78-86` já
diz isso, mas em nota de rodapé.

### 4.6 A lacuna das restrições: os artefatos escolheram o exemplo errado

A fronteira de escopo (d) diz que `&& args(...)`, `&& target(...)` e `&& condition(...)` são descartados —
"40 das 88 linhas `call(`". Medido por **evento** (a unidade certa; restrições atravessam linhas), são
**55 de 58 eventos, 95%**. Mas a extensão não é o que importa:

- **`args()` recupera precisão zero.** Dos 58 eventos com `call(`, apenas **2** têm `args()` que estreita
  tipo, e nenhum dos dois altera o conjunto de `SootMethod` alvo. O exemplo que a delta-spec usa —
  `call(* Set+.add(..)) && args(CharSequence)` — é justamente o caso que rende nada, porque
  `Collection+.add*` de outra spec já cobre o mesmo par sem restrição nenhuma. **Recomendo trocar esse
  exemplo**: ele sugere um ganho que não existe.
- **O `target()`-de-tipo é onde está a precisão**: 22 das 57 ocorrências nomeiam um tipo (8 positivas, 14
  negadas), e é a única classe de restrição aplicável na camada onde o casamento acontece —
  `resolveInScene:53` e o scan (`:590`) já têm o tipo do receptor em mãos.
- **Mas o ganho colapsa na união**, porque `reachesTarget` é booleano por método, não por spec. Sobrevivem
  exatamente **duas** podas: `CharSequence+.equals`/`hashCode` (que a spec restringe com `!target(String)`)
  e a parte não-`java.io` do `Closeable+.close`.
- Essas duas valem **11% a 41%** da semente direta:

| APK | métodos da app | com (d) aberta | com poda `target()` | delta |
|---|---|---|---|---|
| `com.pindroid_69` | 3.353 | 153 (4,6%) | 119 (3,5%) | −22% |
| `lesserpad_42` | 708 | 37 (5,2%) | 22 (3,1%) | −41% |
| `moneytracker_38` | 7.869 | 171 (2,2%) | 152 (1,9%) | −11% |

Nos 3 APKs, **100% dos call sites de `equals`/`hashCode` sobre um `CharSequence` têm receptor
`java.lang.String`** — zero `StringBuilder`/`StringBuffer`. O par `(CharSequence+, equals)` que a change vai
criar é **100% falso positivo** nesses APKs, e o `!target(String)` que a própria spec escreve o eliminaria
por inteiro.

### 4.7 A lacuna dos parâmetros não é o que se pensava

`getParams` **já resolve FQN** pela tabela de imports (`UsedJcaMethodsVisitor.java:84-85`). O que quebra é o
descarte do import-asterisco (`:38-40`) — que a gh69 já conserta. O benefício em `getParams` sai de graça,
uma linha, no ponto de inserção que já existe.

E é irrelevante para o `generic_new` de qualquer modo: **63% dos pares (42/67) usam `(..)`**, sem assinatura;
dos 37% que têm, ~5 discriminam overloads que quase não ocorrem em APK Android. A lacuna só importa no `jca`,
onde o estilo se inverte (43 de 70 pares com assinatura explícita) — exatamente onde o design já a alocou.

**Armadilha a registrar**: `(..)` produz `params=[".."]` de tamanho 1. Se alguém ligar `STRICT` em alvo MOP
sem a degradação por coringa que `SignatureFileTargetSource:87-88` já implementa, `paramsMatch` rejeita tudo
e **41 dos 67 pares viram zero alvos** — e o scan não os recupera, porque deriva dos alvos já resolvidos.

### 4.8 As lacunas (a) e (b), reavaliadas

**(a) `staticinitialization`** — as três specs afetadas (`Collection_HashCode`,
`Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission`) têm o `staticinitialization` como
**único evento**. São reflexivas puras sobre a classe carregada; não observam chamada nenhuma, e não há
evento alternativo que pudesse dar alvos. As três ficam em zero, e é a única causa.

Não é inexprimível: o owner **está** na AST, num nó já visitável (`IDPointCut`, com
`visit(IDPointCut, T)` já presente em `VoidVisitorAdapter.java:232`), e mapearia para `<clinit>`. Mas custa
uma política de casamento nova (`SUBTYPE_CLINIT`), enumeração de subtipos em vez de casamento por nome, e uma
decisão de produto sobre o que `directlyReachesTarget` significa quando **não existe chamador** — o scan é
estruturalmente cego a isso (`stmt.containsInvokeExpr()`). Ordem de 150–250 linhas + IT. **A exclusão é
defensável; a justificativa escrita, não.**

**(b) construtores** — ver §4.2. Barato, mas com custo de aprovação no conjunto congelado.

---

## 5. Defeitos novos encontrados no caminho

| # | Achado | Onde | Severidade |
|---|---|---|---|
| 1 | `forceResolve(…, HIERARCHY)` do D2 + `cls.getMethods()` sem guarda ⇒ `RuntimeException`. `getMethods()` faz `checkLevel(SIGNATURES)`, `Scene.doneResolving()` é `true` no pack `wjtp` e `ignore_resolving_levels` não é setado. Candidato realista: `ServerSocket` num APK sem sockets. **Crash, não falso-negativo.** Correção: resolver em `SIGNATURES`, ou guardar o laço. | INV-ANA-43 × `TargetResolver.java:48-50` | **Alta** |
| 2 | 11 dos 68 pares do `jca` são `(classe, "new")` e não resolvem — a régua congelada nunca contou construtor | `TargetResolver.java:53` | **Alta** (fora da gh69) |
| 3 | "`canStoreType` é O(1) amortizado" é **falso** quando `parent` é interface — e 10 dos 16 owners com `+` são interfaces. `Comparable` (245 subtipos) e `Closeable` (154) caem em `canStoreClassClassic`; os demais fazem varredura linear sobre implementers | ADR 0004; `risk-register.md:237` | Média |
| 4 | `sort -u` sob locale pt_BR funde `Map+.put` com `Map+.put*` → devolve 66 em vez de 67. O gate de cardinalidade da tarefa 1.4 falharia pelo motivo errado. Exige `LC_ALL=C` ou comparação exata em Java | teste da tarefa 1.4 | Média |
| 5 | `force_android_jar` aponta para `platforms/android-N/**data**/android.jar`, que **não existe** em nenhuma plataforma instalada. Só não quebra porque o `-cp` é explícito | `Configs.java:250` | Baixa hoje |
| 6 | `Closeable+` não alcança `AutoCloseable` (o `+` desce, não sobe) — falso-negativo estático fiel ao AspectJ mas não documentado | fronteira de escopo | Baixa |
| 7 | Alvos cujo método **não existe no owner declarado**: `Iterable+.listIterator`, `Collection+.pop`/`push`. Legal em AspectJ e funcional sob A2, mas some silenciosamente se o owner perder o `+` | `ListIterator_Set.mop:19`, `Map_UnsafeIterator.mop:47-48` | Baixa |
| 8 | Coringa não-sufixo cai em `equals` **silenciosamente** — um futuro `*Listener` viraria literal e daria zero alvos sem aviso | D4 | Baixa |
| 9 | `jca/SecretKeySpecSpec.mop`, evento `c1`: um `)` a mais no `condition(...)`. O javamop tolera; qualquer parser por profundidade de parênteses atravessa o `{` do corpo | corpus congelado | Baixa |
| 10 | Os 4 documentos-evidência citados como base normativa estão **não versionados**. Um clone limpo não verifica nenhum número da change | tarefa 5.7 (fase 5) | Média |
| 11 | `nameMatches`-primeiro também para alvos exatos pessimiza o JCA, onde `equals(fqn)` é o filtro seletivo | `design.md` §API Design | Baixa |
| 12 | Necessidade do `canStoreType` no 2º ponto não demonstrada: o `Set<SootMethod>` resolvido já enumera as chaves que o scan encontra | `design.md` D-Flow item 5 | Baixa |

Correção de premissa, para o próximo leitor: a fronteira de escopo tem **quatro** lacunas rotuladas
`(a) (b) (d) (c)` — nessa ordem no arquivo. As lacunas "(e)" e "(f)" que circulam em prompts de retomada
**não existem** nos artefatos: (e) é Non-Goal do design e (f) é a RISK-004.

---

## 6. A releitura que a medição autoriza

O `jca` e o `generic_new` são **complementares nos eixos, não redundantes**:

| | `jca` | `generic_new` |
|---|---|---|
| API | rara, explícita | ubíqua, estrutural |
| `directlyReachesTarget` | 0,0–0,3% — denominador minúsculo, às vezes 0 ou 1 método; **métrica ruidosa** | 2–12% — **denominador utilizável** |
| `reachesTarget` | 11–47% — **discrimina** | 84–94% — **degenera** |

O `jca` tem um sinal transitivo útil e um sinal direto estatisticamente inútil. O `generic_new` tem
exatamente o oposto. Isso não é defeito da gh69: é propriedade das duas famílias de API. Mas significa que a
frase "a change repara o sinal estático do generic" precisa de qualificador — **ela repara o sinal
`directlyReachesTarget`**, e no mesmo movimento torna `reachesTarget` degenerado para esse conjunto.

---

## 7. Recomendação

**Implementar a gh69.** O defeito de 0 alvos é real, o reparo é correto, as três capacidades coringa estão
completas e testáveis, A2 está verificada no bytecode, e o resultado entrega um `directlyReachesTarget`
utilizável onde hoje não há sinal nenhum. Isso não é meia-boca.

Mas com quatro ajustes antes ou junto:

1. **Reescrever a RISK-004** com os números medidos, com os owners certos (`Collection+.add*`,
   `CharSequence+.equals`, família `Iterator`, `Closeable+.close`), e com a constatação de que **sua própria
   mitigação está refutada** — filtrar owners não move o transitivo.
2. **Declarar explicitamente que o sinal entregue para o `generic_new` é o `directlyReachesTarget`**, e que
   `reachesTarget` degenera. Isso muda o texto da proposal, não o código.
3. **Decidir o que fazer com o `aperv-tool` no mesmo commit** — o `hot`/`cold` colapsa. É código em produção,
   não filtro futuro. Ou a gh69 ganha uma tarefa, ou nasce uma change irmã que entra junto.
4. **Corrigir os números que não batem**: 54 (não 67) alvos de subtipo; a comparação 120×67 sob convenção
   única; o exemplo de `args()` que rende zero; e o `LC_ALL=C` no gate de cardinalidade.

E abrir, separadamente:

- **Os 11 alvos `new` mortos no `jca`** (§4.2) — com re-baseline dos dois gates de paridade. É defeito da
  régua publicada, e a gh69 não é o lugar de consertá-lo.
- **A poda por `target()`-de-tipo** (§4.6), escopada aos dois pares que sobrevivem à união
  (`CharSequence+.equals`/`hashCode` e `Closeable+.close`). Vale 11–41% da semente direta — que é justamente
  o sinal que sobrevive.
- **O achado #1 da §5** (`forceResolve` em `HIERARCHY` derrubando `resolveInScene`) precisa entrar na gh69,
  não numa change futura: ele é criado pela própria tarefa 2.x da change.

**O que não fazer**: gastar escopo em (a) `staticinitialization` (3 specs reflexivas, 150–250 linhas,
política de casamento nova), em `args()` (2 casos, ganho zero) ou em resolução de parâmetros para FQN (63%
dos pares não têm assinatura). São as três exclusões defensáveis — só as justificativas escritas precisam
mudar.
