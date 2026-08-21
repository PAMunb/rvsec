# Handoff gh69 — o que descobrimos antes de você começar

**Data**: 2026-08-21 · **Sessão de origem**: `bug-analise-estatica`
**Destino**: a sessão que vai implementar `openspec/changes/gh69-generic-subtype-target-matching/`
**Natureza**: material de referência; nenhum artefato da gh69 foi alterado por esta sessão
**Issue**: #69 (`type:feature`, `track:full-sdd`)

---

## 0. Por que este documento existe

A gh69 está escrita e nunca foi executada: **0 de 26 tarefas**, último toque em 2026-07-09.
Investigando outro assunto (o acoplamento experimento ↔ análise estática), esta sessão mediu o
extrator e encontrou **uma contradição interna nos artefatos da gh69** — duas tarefas dela se
reprovam mutuamente — e **um caso que ela não previu**, no conjunto `jca`, que ela declara como
inalterado.

Nada disso invalida a gh69. O diagnóstico dela está certo e a solução é a certa. O que muda são
**dois critérios de aceite** e **uma decisão de política de casamento** que, se não for tomada, faz
o reparo piorar a medição em vez de melhorá-la.

Tudo abaixo foi medido nesta máquina em 2026-08-21, com o `mop-extractor.jar` construído em
`2026-08-21 08:48`. Os comandos estão na §5.

---

## 1. O que a gh69 é (resumo de uma linha)

Ensinar o extrator e o matcher a lidar com o estilo `generic_new`: **imports com asterisco**
(`import java.util.*;`), **owners por subtipo** (`call(* Collection+.addAll(..))`) e **nomes de
método com coringa** (`add*`). Hoje o pipeline carrega **0 alvos** contra `generic_new` e reporta
`reachesTarget=false` para todo método de todo APK.

---

## 2. O que medimos — os números de partida

Rodando `JavamopFacade.listUsedMethods()` diretamente sobre cada diretório:

| conjunto | assinaturas | pares `(classe, método)` | classes-owner | specs |
|---|---|---|---|---|
| `jca` | **120** | **68** | **22** | 23 |
| `jca_android` | **119** | **67** | **22** | 23 |
| `generic` | 296 | — | — | — |
| `generic_new` | **0** | 0 | 0 | 27 |

Confirmado independentemente nos logs reais do GATOR:

```
[MopSpecsTargetSource] Loaded 120 MOP signatures from .../resources/jca          (probe_run_b.log:238)
[MopSpecsTargetSource] Loaded 119 MOP signatures from .../resources/jca_android  (gator_jca_android.log:103)
```

**Repare em "22 owners para 23 specs".** Uma spec inteira do `jca` não contribui alvo nenhum.

> **Atualização de 2026-08-21 — isto agora é RISK-013, nível High, na gh69.**
> A gh69 passou a saber: o achado deixou de ser *scope boundary (c)* do RISK-010, onde herdava o
> efeito **"Tolerable"**, e virou risco próprio em
> `openspec/changes/gh69-generic-subtype-target-matching/risk-register.md`. O que sustenta o nível:
> o descarte é **silencioso** (`UsedJcaMethodsVisitor:70-77` não tem `else` nem log), é
> **estrutural e repetível** para qualquer spec futura com owner não importado, e cai sobre a
> **régua congelada** — todo `cov_reaches_target` já publicado a partir do `jca` foi calculado sobre
> **22 das 23** specs. Medição nova que delimita o dano: em todas as campanhas da árvore aparecem
> 16 specs distintas no `errors.csv` e `RandomStringPasswordSpec` **não é uma delas** — nenhuma
> contagem de violação publicada está errada; o que está errado é o denominador de alcance.
> A gh69 quita a *silêncio* (task 1.3(b) loga o owner descartado, task 1.5 assere que continua
> logado); o reparo da *medição* segue diferido para a task 5.6.

---

## 3. O achado: `java.lang` não é implícito para o visitor

### 3.1 O mecanismo

`rvsec/rvsec-mop-extractor/src/main/java/br/unb/cic/mop/extractor/visitor/UsedJcaMethodsVisitor.java`:

```java
// :38-40   imports com asterisco são descartados
if (n.isAsterisk()) return;
// :41-43   os demais entram num mapa com chave = NOME SIMPLES, valor = FQN
imports.put(clazz.substring(clazz.lastIndexOf('.') + 1), clazz);
// :70-77   um pointcut só vira alvo se o owner estiver nesse mapa
String clazzName = p.getSignature().getOwner().toString();
if (imports.containsKey(clazzName)) { ... }   // sem else, sem log
```

### 3.2 A spec afetada

`rvsec/rvsec-mop/src/main/resources/jca/RandomStringPassword.mop` (e a sua gêmea em `jca_android`)
declara dois eventos:

```java
event vo after(Object obj) returning(String s):
   call(public static String String.valueOf(Object)) && args(obj) && ...      // :12
event gb after(String s) returning(char[] chars):
   call(public char[] String.toCharArray()) && target(s) && ...               // :19
```

E importa `java.util.stream.IntStream` mais três pacotes `br.unb.cic.mop.*` — **nunca
`java.lang.String`**, porque em Java isso é implícito. O visitor não sabe disso, e os dois pointcuts
desaparecem em silêncio.

**Resultado: `RandomStringPasswordSpec` contribui zero alvos estáticos, nos dois conjuntos, em toda
campanha já rodada — `jca` inclusive.** O aspecto tecido **inclui** os dois pointcuts
(`jca/MultiSpec_1MonitorAspect.aj:874,879`): o monitor acusa em runtime, e o denominador de alcance
não sabe que existe alvo ali.

### 3.3 A causa **não** é o asterisco

Isto importa porque o `tasks.md:1.2` da gh69 trata os dois como o mesmo problema. Não são:

* Os 23 `.mop` do `jca` **usam** `import br.unb.cic.mop.eh.*`, e mesmo assim **todos** os 22 owners
  resolvidos vêm de import explícito. Perda por asterisco no `jca`: **zero**.
* O único owner perdido é `String`, que não está importado de forma alguma.
* O asterisco é, isso sim, o que colapsa `generic_new`: 27 specs, 89 pointcuts `call(...)`,
  **89 perdidos (100%)**, porque todos os owners vêm de `import java.util.*` / `java.io.*` /
  `java.net.*` / `java.lang.*`. É exatamente o diagnóstico da gh69, e está correto.

---

## 4. A contradição dentro da gh69

O `tasks.md:1.2` **já manda o reparo**:

> *"stop discarding `isAsterisk()` imports — register wildcard-import packages... **seed `java.lang`
> by default** as defense-in-depth (Java imports it implicitly, so a future spec may omit it; note:
> every current `generic_new` spec with a `java.lang` owner DOES carry an explicit
> `import java.lang.*;` — verified 2026-07-09 — so today's owners already resolve via wildcard
> registration alone)"*

O parêntese é verdadeiro **para `generic_new`**. Ninguém olhou o `jca`. E o `jca` tem exatamente o
caso que a semente existe para cobrir.

Com `java.lang` semeado:

| | hoje | depois da 1.2 |
|---|---|---|
| `jca` — assinaturas | 120 | **122** |
| `jca_android` — assinaturas | 119 | **121** |
| `jca` — pares | 68 | **70** |
| `jca_android` — pares | 67 | **69** |
| owners | 22 | **23** |

E a `tasks.md:1.5` diz:

> *"Unit test: parse the 23 `jca` specs → **assert 120 targets**, all `includeSubtypes=false` and
> `nameIsPattern=false` (INV-ANA-40 JCA half / INV-ANA-41)"*

O mesmo 120 está fixado em `design.md:56` e `design.md:222`.

**A tarefa 1.5 reprova a tarefa 1.2.** Um dos dois artefatos está errado, e isso precisa ser
decidido **antes** de escrever código, não descoberto quando o teste falhar.

---

## 5. O que o INV-ANA-35 realmente bloqueia — medido, não suposto

A leitura ingênua diz que o comportamento do visitor está congelado:

> `openspec/specs/analysis/spec.md:367` — **INV-ANA-35**: *"`MopSpecsTargetSource.load()` MUST
> produce a `Set<TargetMethod>` whose cardinality and `(className, methodName)` pairs equal those
> produced by the historical `loadMopSignatures()` on the same `mopDir`. For `cryptoapp.mop`, this
> set has exactly 16 entries (gh57 baseline `b2e04a26`)."*

Fomos verificar o que isso **de facto** exerce. É mais frouxo do que parece:

1. **O `MopSpecsParityTest` é tautológico.** Ele compara `MopSpecsTargetSource.load()` com
   `JavamopFacade.listUsedMethods()` sobre o mesmo diretório — os dois chamam o mesmo visitor.
   Sobrevive a qualquer mudança nele. O próprio Javadoc admite o escopo
   (`MopSpecsParityTest.java:31-35`): *"The 'exactly 16 entries on cryptoapp.mop' half of INV-ANA-35
   is exercised by the end-to-end `gator` smoke in task 1.9... This unit test verifies the
   load-bearing parity invariant on a **portable subset**: CipherSpec + MessageDigestSpec."*
2. **Os fixtures desse teste não têm `String`.** `test-specs/` contém só `CipherSpec.mop` e
   `MessageDigestSpec.mop` (owners: `MessageDigest`, `Cipher`); medido: 24 assinaturas, 9 pares,
   2 owners, zero ocorrências de `String.`.
3. **Não existe diretório `cryptoapp.mop` na árvore.** A metade dos "16 entries" nunca é asseverada
   diretamente. A `gh60/tasks.md:34` admite: *"The fixture-level invariant (16 entries on
   cryptoapp.mop) is **implicit** in those passing tests"* — os do `BaselineComparisonIT`, que medem
   `directlyReachesMop`/`reachesMop` sobre o `cryptoapp.apk`.
4. **O `cryptoapp.apk` tem 0 call sites de `String.valueOf`/`toCharArray` no próprio pacote**
   (medido com androguard). Logo semear `java.lang` **não muda** o `BaselineComparisonIT`.

**Conclusão: o reparo não quebra nada que hoje é verificado.** O que quebra é o `assert 120` que a
própria gh69 escreveu.

---

## 6. O risco que **de facto** existe: LENIENT sobre-casa

Este é o número que deve governar a decisão.

`MopSpecsTargetSource.java:39` emite **todo** alvo com `TargetMethod.MatchPolicy.LENIENT`, e a
política está declarada em `openspec/specs/analysis/spec.md:418`: *"LENIENT (class+name only) for
`MopSpecsTargetSource` because AspectJ wildcards in `.mop` specs leave the full signature
semantically undefined"*. Ou seja: casa por `(classe, nome)`, **ignorando a assinatura**.

Medimos os call sites de `String.valueOf`/`toCharArray` dentro do próprio pacote da app, em 3 APKs
do corpus:

| assinatura | ocorrências | o aspecto tece? |
|---|---|---|
| `valueOf(int)` | 53 | **não** |
| `valueOf(Object)` | 14 | sim |
| `valueOf(long)` | 4 | **não** |
| `toCharArray()` | 3 | sim |

**17 de 74 (23%) são o que o monitor de facto dispara.** Os outros 57 são conversão de inteiro para
string em `toString`/log.

Amplitude: em 12 APKs amostrados de `data/apks/`, **8 têm pelo menos um call site** — de 0 a 52 por
app. O `String.valueOf` é onipresente.

**Se `String` for semeado com LENIENT, os 74 contam como alvo.** Isso não recupera um falso-negativo:
cria ~77% de falso-positivo. E como `reachesTarget` é transitivo, o erro se propaga para todos os
chamadores — no `probe_run_b.log`, 22 chamadores diretos propagaram para 124 métodos.

---

## 7. O que fazer na gh69 — proposta concreta

### 7.1 Antes de escrever código: acertar os artefatos

| Arquivo | Mudança |
|---|---|
| `tasks.md:1.5` | `assert 120 targets` → **122** (ou decidir não semear `java.lang`, e dizer isso na 1.2) |
| `design.md:56` | `extractor run asserts 27→N (24 specs with ≥1 target), 23→120` → **23→122** |
| `design.md:222` | `jca → 120, flags false` → **jca → 122** |
| `tasks.md:1.2` | corrigir o parêntese: a afirmação *"today's owners already resolve via wildcard registration alone"* vale para `generic_new`, **não** para `jca` — `RandomStringPassword.mop` usa `String` sem import nenhum e é o caso que a semente cobre |
| `tasks.md:1.4` | acrescentar o caso `jca`: hoje o teste sintético *"a spec with NO `java.lang` import still resolves an `Object+` owner"* é o que prova a semente; agora existe um caso **real** no `jca` para asseverar |

### 7.2 A decisão de política — três opções

O reparo do asterisco (o núcleo da gh69) é seguro e não tem esta questão: os owners de
`generic_new` são tipos de coleção, não `String`. A questão é **só** sobre semear `java.lang`.

| # | Opção | Efeito |
|---|---|---|
| **A** | Semear `java.lang` **e** emitir esses alvos com **`STRICT`** | Recupera os 17 verdadeiros sem os 57 falsos. Exige consertar `getParams()` (`UsedJcaMethodsVisitor.java:80-90`), que hoje devolve `"String"`/`"Object"` crus em vez de FQN — visível na coluna `parameters` do CSV. **Recomendada, se a §7.3 for aceita.** |
| **B** | Semear `java.lang` com LENIENT (o que a 1.2 diz hoje) | Ganha 2 alvos e ~77% de falso-positivo sobre eles. **Não recomendada.** |
| **C** | Não semear `java.lang`; registrar a perda como falso-negativo estático conhecido | Custo zero, mantém `jca`/`jca_android` em 120/119, e a `1.5` continua válida. Precedente no próprio design da gh69, que já documenta *"Scope boundary"* para `staticinitialization` e para os pointcuts `Owner.new(..)`. **Escolhida — com uma emenda de 2026-08-21**: "registrar" não pode ser só documentar. O owner descartado tem de ser **logado** (task 1.3(b)), senão o registro fica no papel e o pipeline continua mudo. É essa emenda que separa o risco aceito do risco invisível — ver RISK-013 |

### 7.3 Sobre o `jca` congelado

O `jca` é a régua das medições publicadas. Qualquer mudança na semente muda `reachesTarget` e
`directlyReachesTarget` em ~metade do corpus (8 de 12 APKs amostrados têm call site), e o efeito é
transitivo.

**Recomendação**: aplicar a semente **só ao `jca_android`** — que é o conjunto que carrega os
reparos de especificação — ou atrás de flag, deixando o `jca` intocado. Assim a `1.5` (`jca → 120`)
continua correta como está, e o ganho vai para o conjunto que ainda não tem medição publicada.

Se você escolher isto, a mudança nos artefatos da §7.1 vira: manter `120` para `jca` e acrescentar
uma linha para `jca_android → 121`.

---

## 8. Comandos para reproduzir

### 8.1 Contar alvos por conjunto

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
S=/tmp/gh69_scratch && mkdir -p $S
cat > $S/Count.java <<'EOF'
import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import java.util.*;
public class Count {
  public static void main(String[] a) throws Exception {
    JavamopFacade f = new JavamopFacade();
    for (String d : a) {
      Set<MopMethod> r = f.listUsedMethods(d, false);
      Set<String> pairs = new TreeSet<>(), owners = new TreeSet<>();
      for (MopMethod m : r) { pairs.add(m.getClassName()+"#"+m.getName()); owners.add(m.getClassName()); }
      System.out.println("RESULT " + d.substring(d.lastIndexOf('/')+1)
        + " signatures=" + r.size() + " pairs=" + pairs.size() + " owners=" + owners.size());
    }
  }
}
EOF
J=$PWD/rvsec/rvsec-mop-extractor/target/mop-extractor.jar
javac -cp $J -d $S $S/Count.java
java -cp $J:$S Count \
  $PWD/rvsec/rvsec-mop/src/main/resources/jca \
  $PWD/rvsec/rvsec-mop/src/main/resources/jca_android \
  $PWD/rvsec/rvsec-mop/src/main/resources/generic_new
# medido 2026-08-21:
#   jca          signatures=120 pairs=68 owners=22
#   jca_android  signatures=119 pairs=67 owners=22
#   generic_new  signatures=0   pairs=0  owners=0
```

Use **caminhos `/home/pedro/...`**, não o alias `/pedro/...` — a JVM não abre o alias.

### 8.2 Medir o impacto do LENIENT num APK

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
.venv/bin/python - <<'EOF'
import logging; logging.disable(logging.WARNING)
from androguard.misc import AnalyzeAPK
tot = {}
for f in ["data/apks/com.akop.bach_120.apk",
          "data/apks/com.andrew.apollo_2.apk",
          "data/apks/com.alienpants.leafpicrevived_24.apk"]:
    a, d, dx = AnalyzeAPK(f); pkg = a.get_package().replace(".", "/")
    for m in dx.get_methods():
        if pkg not in str(m.class_name): continue
        for _, c, _ in m.get_xref_to():
            if str(c.class_name) == "Ljava/lang/String;" and str(c.name) in ("valueOf", "toCharArray"):
                k = f"{c.name}{c.descriptor}"; tot[k] = tot.get(k, 0) + 1
for k, v in sorted(tot.items(), key=lambda x: -x[1]): print(f"{k:45s} x{v}")
EOF
# medido: valueOf(I) x53, valueOf(Object) x14, valueOf(J) x4, toCharArray x3
```

### 8.3 Confirmar que a baseline dos 16 não é afetada

```bash
# o BaselineComparisonIT roda sobre cryptoapp.apk; conte os call sites lá:
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
# (mesmo script de 8.2, com apks_examples/cryptoapp.apk)  -> medido: 0
```

---

## 9. Coisas que descobrimos e que NÃO são da gh69

Para você não gastar tempo com elas:

* **O `MopSpecsParityTest` é tautológico.** Se a gh69 quiser um gate de verdade sobre a cardinalidade
  do `jca`, precisa de um número literal — que é o que a `1.5` tenta fazer. O teste de paridade
  atual não protege nada.
* **`MopSpecsTargetSource.java:44-46` engole `MOPException`** devolvendo `Collections.emptySet()`,
  sem spec e sem teste. Um `.mop` malformado vira "zero alvos" em vez de erro. Adjacente ao tema da
  gh69, mas independente.
* **`mopDir` inexistente ou vazio devolve conjunto vazio em silêncio** — e isso **é contrato**,
  testado por `MopSpecsParityTest.emptyDirYieldsEmptySetWithoutThrowing`. Não mexer.
* **A análise estática mira `resources/jca` mesmo sob `--specification-set jca_android`** — defeito
  do orquestrador Python, não do extrator. Está em
  `docs/20260821_plano_correcao_analise_estatica.md` (D2). Se ele for reparado antes da gh69, o
  `generic_new` passa a ser efetivamente alcançável pelo caminho de experimento — hoje nem chega lá.

---

## 10. Referências

| Item | Caminho |
|---|---|
| Change | `openspec/changes/gh69-generic-subtype-target-matching/` (proposal, design, tasks, risk-register, specs) |
| Visitor | `rvsec/rvsec-mop-extractor/src/main/java/br/unb/cic/mop/extractor/visitor/UsedJcaMethodsVisitor.java:38-43,70-90` |
| Facade | `rvsec/rvsec-mop-extractor/src/main/java/br/unb/cic/mop/extractor/JavamopFacade.java:63-82` |
| Target source | `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/target/MopSpecsTargetSource.java:39,44-46` |
| Teste de paridade | `.../client/src/test/java/presto/android/gui/clients/target/MopSpecsParityTest.java:31-35,90-96` |
| Spec afetada | `rvsec/rvsec-mop/src/main/resources/jca/RandomStringPassword.mop:11-22` |
| Aspecto tecido | `rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879` |
| INV-ANA-35 / política LENIENT | `openspec/specs/analysis/spec.md:367,418` |
| Origem da baseline dos 16 | `openspec/changes/archive/2026-06-17-gh60-targets-core/tasks.md:31,34` |
| Diagnóstico original do `generic_new` | `docs/20260617_sa_generic_new.md`, `docs/20260611_sweep_generic_new_400.md` |
| Plano irmão (orquestrador) | `docs/20260821_plano_correcao_analise_estatica.md` |
