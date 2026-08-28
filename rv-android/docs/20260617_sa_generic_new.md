# Plano: subtype/wildcard-aware target matching no GATOR (specs generic_new)

**Data:** 2026-06-17
**Tipo:** ideação Phase-0 (alimenta `/opsx:new` — change `gh<N>-generic-subtype-target-matching`)
**Origem:** blocker descoberto no sweep generic400 (parado em 49/400). Investigação completa em
`docs/20260611_sweep_generic_new_400.md` §10–§11. Este doc é o **plano do fix**; o sweep/dataset
é consumo posterior (fronteira de escopo, ver §7).

---

## 1. Problema (uma frase)

Os specs `generic_new` declaram alvos por **hierarquia de tipos** (`call(* Collection+.add*(..))`),
mas o pipeline de matching de targets do GATOR casa por **FQN exato** e foi escrito para o estilo
JCA (imports explícitos + classe.método exatos). Resultado: **0 alvos carregados** →
`reachesTarget=false` em todo método de todo APK → análise estática inútil para o experimento
generic.

Sintoma no log (todo APK): `[MopSpecsTargetSource] Loaded 0 MOP signatures from .../generic_new`
→ `MOP methods resolved: 0` → `reachesTarget: 0`. A reachability em si funciona (28k+ métodos);
só o conjunto-alvo vem vazio.

## 2. Objetivo

Tornar o matching **subtype/wildcard-aware** para que `reachesTarget` e `directlyReachesTarget`
fiquem **corretos** nos specs com `+`. Um método `a()` passa de `reachesTarget=false` para `true`
quando chama (direta ou indiretamente) um método cuja classe declarante **é-subtipo-de** a classe
declarada no spec (ex.: chamar `ArrayList.add` casa `Collection+.add*`).

**Escopo:** apenas o *matching* (extractor + matcher) + rebuild + testes. **Schema de saída
INTACTO** (ver §6). Sweep e definição do dataset são change posterior.

## 3. Decisões já tomadas (autoritativas — não relitigar no Phase 1/2)

| # | Decisão | Status | Justificativa |
|---|---------|--------|---------------|
| **A** | Matching = **A2** (`canStoreType` no momento do match), NÃO pré-expandir (A1) | ✅ decidido por spike | §4 |
| **B** | **Schema de saída NÃO muda** (sem per-spec, sem `targetSummary`) | ✅ descartada | §6 |
| **C** | Change cobre só matching+rebuild; sweep/dataset depois | ✅ | §7 |

### 3.A — Por que A2 e não A1 (evidência do spike, 2026-06-13)

Spike throwaway (`out/spike_subtype_hierarchy/`) num APK pequeno, Soot Android scene (Soot 4.7.1
do fat jar do gator):
- **A1 (pré-expandir via `getImplementersOf`) é incompleto e errado:** `getImplementersOf(Collection)`
  retornou só 3 classes (as presentes no Scene daquele app) e **não inclui sub-interfaces** —
  `getImplementersOf(Iterable)` NÃO continha `java.util.List`. O call site real do app era
  `iterator <- java.util.List` (declarante = a interface `List`). A1 erraria esse caso.
- **A2 (`FastHierarchy.canStoreType`) funciona em tipos de biblioteca:** `ArrayList<:Collection`,
  `HashMap<:Map`, `String<:CharSequence` → todos `true`.
- **Conclusão:** A2 é correto por construção (só pergunta sobre classes que aparecem no call site,
  que são sempre resolvidas) e cobre interface→interface. A1 descartado.

### 3.B — Por que o schema não muda (per-spec vive no runtime)

O relatório de coverage usa o `reachesTarget` **agregado** como denominador
(`result_processor.py:402-435`: `mop_coverage = called_target_methods / total_target_methods`).
A atribuição **por-spec** (qual `.mop` violou) **já existe no runtime**: cada handler `.mop` loga
`RVSEC ... ::: <NomeDoSpec> <mensagem>` no logcat (ex.: `Collection_UnsynchronizedAddAll The source
collection of addAll() has been modified.`), que o `rv-coverage` parseia para `errors.csv`. Logo a
estática só precisa do booleano agregado correto — sem per-spec, sem `targetSummary`, sem carregar
proveniência do `.mop` no extractor. **Schema intacto = zero risco** nos dois únicos consumidores
do JSON (parser Python `static_analysis_parser.py` + ape `MopData.java`, ambos tolerantes/atrás de
fronteira única). Detalhe da análise de risco em `docs/20260611_...` §11.

## 4. As 3 capacidades novas (o que o generic_new usa e o JCA não)

Verificado no AST do parser JavaMOP e na grammar. Sobre 89 pointcuts `call(...)` nos 27 `.mop`:

| Capacidade | Exemplo | Hoje | Quantos |
|------------|---------|------|---------|
| (1) Import **wildcard** | `import java.io.*;` | visitor ignora `isAsterisk()` | 26/27 arquivos |
| (2) Dono por **subtipo `+`** | `call(* Closeable+.close())` | match por FQN exato | 71/89 pointcuts |
| (3) Nome de método **wildcard** | `call(* Collection+.add*(..))` | match por nome exato | vários (`add*`,`remove*`,`retain*`) |

Notas de representação (confirmadas no código):
- O `+` é **concatenado à string** do tipo na grammar (`aspectj.jj:2073/2333`: `id.str += "+"`).
  Logo o dono de `Closeable+` chega como a string literal `"Closeable+"`.
- O retorno wildcard (`*`) vira `BaseTypePattern("*")` e **já é ignorado** (o extractor não usa o
  tipo de retorno) → inócuo, sem trabalho.

## 5. Desenho do fix (dois componentes, dois JARs)

```
 .mop (generic_new)                              Soot Scene (do APK)
      │                                                │
      ▼  COMPONENTE 1                                  │
 ┌────────────────────────────────────┐               │
 │ UsedJcaMethodsVisitor               │ ← (1) import wildcard
 │ (rvsec-mop-extractor)               │ ← (2) tirar '+', marcar includeSubtypes
 │                                     │ ← (3) preservar nome-padrão (add*)
 └──────────────┬──────────────────────┘
                │ MopMethod{className, name, params, +includeSubtypes, +nameIsPattern}
                ▼
 ┌────────────────────────────────────┐
 │ MopSpecsTargetSource                │ → TargetMethod{..., includeSubtypes, namePattern}
 └──────────────┬──────────────────────┘
                ▼  COMPONENTE 2
 ┌──────────────────────────────────────────────────────────────┐
 │ predicado de match: equals(FQN)  →                            │
 │   nameMatches(padrão) && canStoreType(classeNoUso, superTipo)  │
 │ aplicado em DOIS pontos:                                       │
 │   • TargetResolver.resolveInScene   (semeia o BFS reverso do CG)│
 │   • findDirectTargetCallersByBytecodeScan (scan direto)        │
 └──────────────────────────────────────────────────────────────┘
```

### Componente 1 — Extractor (`rvsec-mop-extractor`)

Arquivo: `src/main/java/br/unb/cic/mop/extractor/visitor/UsedJcaMethodsVisitor.java`
- `visit(ImportDeclaration)` (hoje `if (n.isAsterisk()) return;`): registrar os **pacotes**
  wildcard (`java.io`, `java.util`, `java.lang`, ...).
- `visit(MethodPointCut)` (hoje `clazzName = owner.toString(); if (imports.containsKey(clazzName))`):
  (a) **tirar o sufixo `+`** do dono e marcar `includeSubtypes=true`; (b) resolver nome simples→FQN —
  primeiro `imports` explícitos, senão tentar `Class.forName(pkg + "." + simple)` sobre os pacotes
  wildcard (são todos do JDK → resolvem no runtime do extractor); (c) preservar nome de método com
  wildcard (`add*`) como **padrão**, não literal.
- `model/MopMethod.java`: novos campos `includeSubtypes` e `nameIsPattern` (hoje só
  className/name/params/signature).

### Componente 2 — Matcher (`rvsec-gator`, módulos `commons` + `client`)

- `commons/.../target/TargetMethod.java`: carregar `includeSubtypes` (flag) + `nameIsPattern`.
  Propagar de `MopMethod` → `TargetMethod` em `MopSpecsTargetSource.load()`.
- `client/.../target/TargetResolver.resolveInScene` (hoje
  `t.getClassName().equals(fqn) && t.getMethodName().equals(name)`): quando `includeSubtypes`,
  trocar o `equals(className)` por `canStoreType(method.getDeclaringClass().getType(), superType)`
  e o `equals(methodName)` por casamento de padrão. Constrói o `Set<SootMethod>` (inclui os métodos
  concretos de subtipos presentes no Scene — ex.: `ArrayList.add`). O BFS reverso do
  `ReachabilityEngine` segue inalterado a partir desse set.
- `client/.../RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` (linha ~574, hoje casa
  `declaringClass.getName()+"#"+name` contra um Set de chaves exatas): no call site, a classe
  declarante pode ser **interface** (`java.util.List`); então o scan precisa testar
  `canStoreType(ref.getDeclaringClass().getType(), superType) && nameMatches` **contra os
  super-tipos-alvo** (não contra chaves de métodos pré-resolvidos). Idem `findDirectTargetCallers`
  (CG-based, linha ~447) que usa `targetMethods.contains(target)` — funciona pois o set resolvido já
  contém os métodos concretos dos subtipos.
- API Soot disponível (Soot 4.7.1 `org.soot-oss`): `Scene.v().getOrMakeFastHierarchy().canStoreType(sub, sup)`
  e `Scene.v().getActiveHierarchy()`. **Hoje não usadas no gator** (integração net-new — validado §14).
- **Resolução do super-tipo-alvo no Scene (R-5, obrigatório — ponto de maior risco):** `canStoreType`
  só responde se **ambos** os tipos estão no Scene. O spike (§14, item 4) reproduziu o modo-de-falha
  `ByteArrayInputStream <: Closeable : one side NOT in Scene`. No matcher, o tipo do call site sempre
  está carregado, mas o **super-tipo declarado no spec** (ex.: `java.io.Closeable`) pode não estar.
  Antes de construir a `FastHierarchy`, **forçar a resolução de cada owner-alvo** no Scene
  (`Scene.v().forceResolve(fqn, SootClass.HIERARCHY)`), e quando um lado ainda faltar, **degradar
  para `equals` exato + log** (sem falso-negativo silencioso). A correção é decidida no ADR; o IT de
  1 APK (§10) deve exercer `canStoreType` **dentro da scene real do `RvsecAnalysisClient`**, não numa
  scene standalone, antes de liberar o sweep.

**Caminho JCA preservado:** specs JCA têm import explícito + classe.método exatos e `includeSubtypes=false`
→ o predicado cai no `equals` exato de hoje. Sem mudança de comportamento.

## 6. Schema de saída — INTACTO

Nenhuma chave nova, nenhuma renomeada. `reachability[].methods[].{reachable,reachesTarget,
directlyReachesTarget}` continuam idênticos em forma; só ficam **mais corretos** (mais métodos
`true` nos specs com `+`). Consequência esperada e aceita: o denominador do coverage generic cresce
(specs como `Iterable+.iterator()` são quase onipresentes). Não se compara número-a-número com JCA
(experimentos distintos — confirmado pelo usuário).

## 7. Fronteira de escopo

```
ESTA change (gh<N>-generic-subtype-target-matching)        change SEPARADA (depois)
  • extractor: carregar alvos generic_new                    • rodar sweep generic400 (400 APKs)
  • matcher A2: subtype/wildcard-aware                        • consolidar CSV, filtrar dataset
  • rebuild 2 JARs + testes; schema intacto                  • plano já em docs/20260611_...
```

## 8. Invariantes / testes a preservar

- **INV-ANA-35** (`MopSpecsParityTest`): a carga de specs JCA (CipherSpec, MessageDigestSpec) deve
  permanecer byte-a-byte igual. Specs JCA não têm `+`/wildcard → caminho exato intacto.
- **INV-ANA-33** (mop_dir × targets_file mutex) inalterado.
- **BUG-INV-ANA-19** (complemento bytecode-scan) preservado; o scan ganha o predicado de subtipo.
- Novos testes:
  - Extractor: parsear um `.mop` generic_new e assertar N>0 alvos com `includeSubtypes=true` e
    nome-padrão (ex.: `add*`); JCA continua N exato.
  - Matcher: unit de `canStoreType` cobrindo classe→interface e interface→interface
    (`List <: Iterable`).
  - IT de 1 APK: `reachesTarget>0` contra generic_new (hoje 0). **Executar `canStoreType` DENTRO da
    scene real do `RvsecAnalysisClient`** (não standalone) p/ cobrir o risco R-5 (§5/§14) — confirmar
    que os super-tipos-alvo (`Closeable`, `Collection`, ...) resolvem no Scene de produção.

## 9. Rebuild

**Ordem em 2 passos OBRIGATÓRIA (R-12):** o `rvsec-mop-extractor` é dependência **compile-scope** do
gator `client` (`client/pom.xml:40-43`) → suas classes ficam **embutidas** no
`rvsec-analysis-client.jar`. Rebuildar só o extractor atualiza `lib/mop-extractor/mop-extractor.jar`,
mas **NÃO** refresca a cópia dentro do `rvsec-analysis-client.jar`. Logo:

```bash
# Passo 1 — extractor: publica no ~/.m2 + copia mop-extractor.jar p/ rv-android/lib/mop-extractor/
cd <workspace>/rvsec/rvsec/rvsec-mop-extractor
mvn clean install -DskipTests

# Passo 2 — gator: re-empacota o fat jar do client (pega o novo extractor do .m2) e copia as 2 JARs
cd <workspace>/rvsec/rvsec/rvsec-android/rvsec-gator
mvn clean install -DskipTests -pl sootandroid,client -am
```

- **Path corrigido (R-12a):** o gator está em `…/rvsec/rvsec/rvsec-android/rvsec-gator` (`rvsec`
  **duplicado** no workspace); de `rv-android` é `../rvsec/rvsec-android/rvsec-gator`.
- **Copy automático:** `rvsec-gator-parent/pom.xml:71-95` (maven-resources, fase `install`) copia
  `rvsec-gator.jar` + `rvsec-analysis-client.jar` p/ `rv-android/lib/gator/`; o extractor tem copy
  próprio p/ `rv-android/lib/mop-extractor/`. Precisa chegar à fase **`install`** (não `package`).
- **Seguro:** o fix de arity do `FlowgraphRebuilder` (WTG) está no **source**
  (`FlowgraphRebuilder.java:212-225,647-660`) — incluir `sootandroid` no `-pl` mantém o fix no
  `rvsec-gator.jar`; rebuild não o perde.
- **Pré-requisito:** deps siblings (`javamop`, `jcommander`, `rvsec-apk`) já resolvíveis no `.m2`;
  se `javamop` mudou, `install` primeiro.

## 10. Verificação (pós-implementação)

1. `/rv-verify` + `/opsx:verify` (testes/lint/parity).
2. Re-rodar o spike/IT: `reachesTarget>0` num APK generic.
3. Re-lançar o **Estágio A** do sweep (doc 20260611) num subconjunto pequeno (5–10 APKs) e conferir
   no log `Loaded N>0 MOP signatures` e `reachesTarget>0`.
4. Só então liberar o sweep completo dos 400 (change separada).

## 11. Mapeamento OpenSpec (Full SDD — toca tooling de análise estática, decisão de design)

| Fase | Skill | Produto |
|------|-------|---------|
| 1. Explore | (feito neste doc + `/opsx:explore`) | entendimento, A2, B-descartada |
| 2. Propose | `/opsx:new` → `/opsx:continue` ×2 | `proposal.md` + delta `specs/analysis/spec.md` |
| 3. Design | `/opsx:continue` ×2 → `/rv-doc-adr` | `design.md` (ADR: A2 canStoreType vs A1) + `tasks.md` |
| 4. Implement | `/opsx:apply` + `/rv-test-add` | extractor + matcher + testes |
| 5. Verify | `/rv-verify` + `/opsx:verify` | parity OK, IT reachesTarget>0 |
| 6. Archive | `/opsx:archive` | specs sincronizadas |

ADR candidato: "Subtype matching via FastHierarchy.canStoreType (não pré-expansão)".

## 12. Riscos / unknowns

- **Super-tipo-alvo ausente do Scene (R-5 — maior risco, mitigado):** `canStoreType` não responde se
  um lado não está carregado (`one side NOT in Scene` no spike). Mitigação no design: `forceResolve`
  do owner-alvo + degradação para `equals`+log. Validar no IT na scene real (§5, §8, §14).
- **Custo do `canStoreType` no scan:** o scan já itera todos os invokes; o check de hierarquia é
  O(1) amortizado no `FastHierarchy`. Risco baixo; medir no IT.
- **`Class.forName` no extractor p/ resolver wildcard imports:** funciona p/ classes JDK
  (todas as do generic_new). Se algum `.mop` referenciar classe não-JDK via wildcard, o resolve
  falha → logar e seguir (degradação graciosa). Confirmar que não há caso assim nos 27 specs.
- **Specs quase-universais** (`Iterable+`, `Object+`): inflam `reachesTarget` — esperado e aceito
  (§6). Sem impacto no schema.

## 13. Status

- 2026-06-17: plano escrito; decisões A/B/C fechadas; spike concluído. **Aguardando abrir a change
  com `/opsx:new`.** Sweep generic400 permanece parado em 49/400 até o fix entrar.
- 2026-06-17: **validação rigorosa concluída** (§14). Veredito: artefatos sólidos (as 3 decisões
  A2/B-descartada/C resistiram à refutação).
- 2026-06-17: **correções incorporadas** — R-5 (resolução do super-tipo no Scene + IT na scene real)
  em §5/§8/§12; R-12 (ordem de rebuild extractor→gator) e R-12a (path corrigido) em §9; R-13 (nota de
  supersession da Decisão B) aplicada em `20260611_...` §11. **Plano pronto para `/opsx:new`**
  (change `gh<N>-generic-subtype-target-matching`, Full SDD). Sweep generic400 segue parado em
  49/400 até o fix entrar.
- 2026-08-28: **implementado** na change `gh69-generic-subtype-target-matching`. O extractor passou a
  registrar imports com asterisco, a tirar o `+` do dono, a preservar o padrão de nome e a mapear
  `Owner.new(..)` para `<init>` (D9); o matcher A2 entrou nos dois pontos de casamento via
  `TargetMatching.canStoreType`; e o BFS reverso passou a ser semeado com o conjunto direto, o que
  torna `reachesTarget ⊇ directlyReachesTarget` derivado e não apenas afirmado (INV-ANA-64, D8).
  Medido em `cryptoapp.apk` sob spark: `generic_new` sai de 0 para 72 assinaturas carregadas, 21 donos
  resolvidos e **0 degradações**, com `directlyReachesTarget` em 13/106 (12,3%) contra 0,0% antes.
- 2026-08-28: **duas correções que este plano não previa**, ambas medidas e registradas na change.
  (a) A mitigação da D2 estava invertida: guardar a degradação em `isPhantom()` derruba **todo** dono
  declarado dos dois conjuntos, porque sob `-force-android-jar` as classes `java.*`/`javax.*` são lidas
  do `android.jar` da plataforma com hierarquia completa e correta **e** marcadas phantom assim mesmo
  (522 de 575 no Scene do `cryptoapp`). O critério certo é conteúdo de hierarquia, não a flag.
  (b) Os ITs rodavam com `-withCHA`, ou seja, mediam um call graph que a produção não usa — o mesmo
  defeito do incidente gh60 §D12, que consertou o script de gate e nunca chegou aos ITs. Com spark, as
  duas linhas de base do `cryptoapp` passam a descrever a mesma corrida (55/33/23).
- 2026-08-28: sweep generic400 **continua parado por decisão de escopo**, não por falta do fix: rodá-lo
  é uma change própria, e o corpus migrou do conjunto de 400 APKs para o `rvsec-dataset`.

---

## 14. Validação rigorosa (2026-06-17)

Revisão cética e adversarial dos claims deste doc e de `20260611_...` §10–§11, **antes** de abrir a
change. Cada item foi verificado de forma independente contra o código/binário real (não só lido):
extractor **executado** nos dois dirs, spike **re-rodado**, gator/ape/python **grep+leitura** com
`arquivo:linha`. Legenda: **PASS** confirma o claim; **RESSALVA** confirma mas com gap/correção a
incorporar; **FAIL** refuta.

### Grupo 1 — Diagnóstico do blocker

| # | Item | Veredito | Evidência |
|---|------|----------|-----------|
| 1 | extractor carrega 0 do generic_new e N>0 do jca | **PASS** | Executado `mop-extractor.jar -t METHODS_PARAMS`: `generic_new` → CSV só com header (**0 métodos**); `jca` → **120 métodos** (`java.security.KeyPair.getPrivate`, ...). `MopSpecsTargetSource.load()` mapeia `MopMethod`→`TargetMethod` (commons), confirmado. |
| 2 | causa no `UsedJcaMethodsVisitor` | **PASS** | `UsedJcaMethodsVisitor.java:38-39` `if (n.isAsterisk()) return;` (dropa wildcard); `:72` `if (imports.containsKey(clazzName))` exige import explícito e casa owner exato. `JavamopFacade.listUsedMethods` só agrega `getMethods()`. Grammar: `aspectj.jj:2073` e `:2333` fazem `id.str += "+"` → owner chega como `"Collection+"` (confirma o dobro-bloqueio: mapa vazio **e** sufixo `+`). |
| 3 | 26/27 wildcard; 71/89 com `+` | **PASS** (recontado) | **27/27** têm import wildcard; exatamente **26 têm SÓ wildcard** (Collection_HashCode.mop também tem 1 import explícito) → casa "26/27 só wildcard". **89** pointcuts `call(...)`, **71** com owner `+` (Collection×20, Map×11, Reader×6, InputStream×5, ServerSocket×4, ...). Números exatos. |

### Grupo 2 — Decisão A2 (a mais crítica)

| # | Item | Veredito | Evidência |
|---|------|----------|-----------|
| 4 | re-rodar spike: getImplementersOf incompleto; canStoreType em lib; call site usa interface | **PASS** (reproduzido) | Re-rodado `run_spike.sh`. `getImplementersOf(Iterable)`=4 e **NÃO inclui `java.util.List`** (List aparece só como interface separada, level=2); `Collection`=3. `canStoreType` true: `ArrayList<:Collection`, `HashMap<:Map`, `String<:CharSequence`. Call site real: `iterator <- java.util.List` (declarante = **interface**). A1 erraria; A2 acerta. |
| 5 | **contestar o spike**: scene standalone × scene de produção do GATOR | **RESSALVA** | O spike usa o **mesmo Soot 4.7.1** do fat jar de produção (`soot/` entries=2889 no `rvsec-gator.jar`) → paridade de **API** está de pé. **MAS** roda numa scene **standalone** (`HierarchyProbe`), não na scene whole-program do `RvsecAnalysisClient`. E o próprio spike expõe o modo-de-falha do `canStoreType`: **`ByteArrayInputStream <: Closeable : one side NOT in Scene`** — quando um dos tipos não está carregado, `canStoreType` **não responde**. No matcher A2 o tipo do call site sempre está no Scene, mas o **super-tipo-alvo** (ex.: `java.io.Closeable`) **pode não estar**. **GAP do plano:** §5 não especifica garantir que o super-tipo-alvo seja resolvido no Scene de produção antes do `canStoreType`. **Correção (→ design/ADR):** `forceResolve(fqn, HIERARCHY)` (ou equivalente) de cada owner-alvo + degradação para `equals` exato com log quando um lado faltar; e **validar `canStoreType` DENTRO da scene do `RvsecAnalysisClient`** no IT de 1 APK (§10/§8) antes do sweep completo. Em produção o risco é **menor** (android.jar + whole-program carregam mais classes), mas não nulo. |
| 6 | dois pontos de match contra o super-tipo (não chaves pré-resolvidas) | **PASS** | Hoje ambos exatos: `TargetResolver.resolveInScene` (`equals(className)&&equals(name)`, TargetResolver.java:53) e `findDirectTargetCallersByBytecodeScan` (chave `declaringClass#name`, RvsecAnalysisClient.java:585; `findDirectTargetCallers` CG-based usa `targetMethods.contains`, ~:455). O desenho de testar `canStoreType(classeNoCallSite, superTipo)` nos dois pontos é correto p/ call sites tipados por interface. Sub-caveat de Scene cai no R-5. |

### Grupo 3 — Decisão B (schema intacto)

| # | Item | Veredito | Evidência |
|---|------|----------|-----------|
| 7 | só DOIS consumidores do JSON | **PASS** | Produção: (1) `static_analysis_parser.py` (fronteira única, `_JK` cruza com `JsonSchema.Keys`, INV-ANA-32); (2) ape `MopData.java` (parser tolerante `opt*`: `optBoolean("reachesTarget",false)`:276, etc.; `MopData.load()` é o único `new JSONObject` sobre o JSON; 6 consumidores leem o POJO tipado). **Procurado terceiro**: nenhum em produção. ~6 scripts offline (`scripts/static_analysis_sweep*.py`, `check_*`, `gh51_smoke_test.py`) leem chaves cruas — mas como B mantém **schema intacto**, **zero quebra**. |
| 8 | coverage usa reachesTarget agregado; per-spec vem do runtime | **PASS** | `result_processor.py:402-406` denominador `total_target_methods = len(repository.get_target_methods())`; `:433-437` `mop_coverage = called_target_methods / total_target_methods` — **agregado, sem per-spec**. Runtime: handlers `.mop` logam `Log.v("RVSEC", __LOC + " ::: <SpecName> <msg>")` (Collection_UnsynchronizedAddAll.mop:38 e outros); `logcat_parser.py:211` extrai o spec (`message_text.split(" ")[0]`); `result_processor.py:490/561` grava coluna `spec` em `errors.csv`. |
| 9 | `targetMethods` é nível-componente (lifecycle), não as APIs monitoradas | **PASS** | `RvsecAnalysisClient.writeComponentEntry:1524-1542` e `writeProviderEntry:1567-1585` populam `targetMethods` iterando `sc.getMethods()` filtrando por `lifecycleMethodNames` + `reachesTarget` → assinaturas de lifecycle do próprio componente (`<MainActivity: void onCreate(Bundle)>`). Hint de navegação, **não** APIs monitoradas. Não reusar o nome. |

### Grupo 4 — Invariantes, parity e rebuild

| # | Item | Veredito | Evidência |
|---|------|----------|-----------|
| 10 | INV-ANA-35 / `MopSpecsParityTest`: JCA sem `+` → exato preservado | **PASS** | `MopSpecsParityTest.java` exercita CipherSpec+MessageDigestSpec; assert byte-a-byte `MopSpecsTargetSource.load()` × `JavamopFacade.listUsedMethods` (cardinalidade + pares `(className,methodName)`). Grep nos 21 `.mop` JCA: **0 owners com `+`**, **0 nome-de-método wildcard**. (Nuance: `+` aparece em JCA só na **posição de parâmetro** — `getInstance(String, Object+)`, CipherSpec.mop:40 — que vive em `getParams`, não no owner → não afeta o caminho exato.) Fix só dispara em owner `+`/wildcard → JCA inalterado. |
| 11 | arity fix do FlowgraphRebuilder no SOURCE | **PASS** | `FlowgraphRebuilder.java:212-225` (`processFlowAtCall`) e `:647-660` (`removeFlowAtCall`): guarda `availableActuals = (ie instanceof InstanceInvokeExpr)? argCount+1 : argCount; if (num_param > availableActuals) return;`. Comentário explica o crash SPARK cgDelegation. Rebuild **não perde** o fix. |
| 12 | comandos de rebuild dos 2 JARs + install copia p/ lib/gator | **RESSALVA** | **(a)** Copy confirmado: `rvsec-gator-parent/pom.xml:71-95` maven-resources `copy-resources` **na fase `install`** → `${main.basedir}/rv-android/lib/gator` (jars atuais `jun 13 11:40`, batem com `target/`). Módulos: dir `sootandroid`→`rvsec-gator.jar`, dir `client`→`rvsec-analysis-client.jar` (fat). **Correção de path**: o gator está em `…/rvsec/rvsec/rvsec-android/rvsec-gator` (rvsec **duplicado**); de `rv-android` é `../rvsec/rvsec-android/rvsec-gator` — o `cd rvsec/rvsec-android/rvsec-gator` do §9 está errado. **(b)** **ACOPLAMENTO CRÍTICO**: o extractor é dependência **compile-scope** do `client` (`client/pom.xml:40-43`) → fica **embutido** no `rvsec-analysis-client.jar` (17 entries `br/unb/cic/mop/*` confirmados no jar). ⇒ rebuild do extractor exige **ordem em 2 passos**: (1) `mvn install` do `rvsec-mop-extractor` (publica no `.m2` + copia `mop-extractor.jar`); (2) **só então** rebuild do gator `client` p/ re-empacotar. O §9 não torna a ordem explícita → **adicionar ao `tasks.md`**. |

### Grupo 5 — Coerência dos artefatos

| # | Item | Veredito | Evidência |
|---|------|----------|-----------|
| 13 | coerência interna do doc + mapeamento OpenSpec | **RESSALVA** (menor) | Referências `arquivo:linha` do 20260617 conferem (desvios de ±2-3 linhas, todas confirmadas: `result_processor.py:402-435`✓, scan `~574`✓, `~447`✓, `FlowgraphRebuilder:212-223/647-657`✓≈225/660, `1524/1567`✓, `aspectj.jj:2073/2333`✓). **Inconsistência cruzada**: `20260611_...` §11 ainda apresenta o `targetSummary` per-spec como **design vivo** (com exemplo jsonc + "PONTO AINDA EM ABERTO G1×G2"), enquanto este doc §3.B **fecha B como descartada** (schema intacto). **Correção de doc**: anotar em 20260611 §11 "SUPERSEDED por 20260617 §3.B — B descartada, schema intacto" p/ não reabrir. |
| 14 | `Class.forName` cobre todas as classes dos 27 `.mop` (todas JDK?) | **PASS** | Owners distintos: CharSequence, Closeable, Collection, Collections, Comparable, InputStream, Iterable, Iterator, ListIterator, Long, Map, Object, OutputStream, Queue, Reader, ServerSocket, Set, TreeMap, URLDecoder, URLEncoder, Writer — **todos JDK** (`java.lang`/`util`/`io`/`net`). **Nenhum owner não-JDK** → `Class.forName` resolve no runtime do extractor. (Nota impl.: o resolve precisa iterar os **pacotes wildcard do arquivo**; conferir que cada owner tem seu pacote entre os wildcards do `.mop` — ex.: `ServerSocket` exige `java.net.*` no arquivo.) |

### Veredito final

**Artefatos prontos para `/opsx:new` APÓS incorporar 4 correções** (nenhuma invalida as decisões
A2/B/C — todas resistiram à refutação):

1. **R-5 (design/ADR, importante):** especificar a **resolução do super-tipo-alvo no Scene de
   produção** antes do `canStoreType` (`forceResolve` HIERARCHY + degradação-com-log se ausente) e
   **validar `canStoreType` na scene real do `RvsecAnalysisClient`** no IT de 1 APK antes do sweep.
   É o ponto de maior risco (o spike standalone não cobre a config de scene de produção).
2. **R-12 (tasks):** registrar a **ordem de rebuild em 2 passos** (extractor `install` → gator
   `client` rebuild), pois o extractor é embutido no `rvsec-analysis-client.jar`.
3. **R-12a (doc):** corrigir o path do comando gator no §9 (`../rvsec/rvsec-android/rvsec-gator`).
4. **R-13 (doc):** anotar supersession em `20260611_...` §11 (B descartada).

Tudo o mais: **PASS**. Diagnóstico do blocker, decisão A2, schema-intacto (B), parity JCA, fix de
arity no source e cobertura JDK do `Class.forName` confirmados empírica e estaticamente.

## 15. Validação adversarial dos artefatos da change `gh69-generic-subtype-target-matching` (2026-06-17)

Revisão **adversarial dos artefatos OpenSpec** (proposal/spec-delta/design/tasks/risk-register/ADR),
**antes** de `/opsx:apply`. Diferente da §14 (que validou o *plano*), esta seção valida os *artefatos
da change* — cada referência `arquivo:linha`, cada invariante, cada claim de traceability foi
re-verificado de forma independente contra o código real (grep+leitura+`javap`+spike) e contra os
demais artefatos. Legenda: **PASS** / **RESSALVA** (confirma com gap a corrigir) / **FAIL**.

### Grupo 1 — Sanidade e completude OpenSpec
- **Item 1 — PASS.** `openspec validate "gh69-generic-subtype-target-matching"` → *valid*;
  `openspec status` → **4/4** (proposal, design, specs, tasks).
- **Item 2 — PASS.** Track **Full SDD** (rv-sdd) coerente com `docs/WORKFLOW.md`: artefatos de Phase 2
  (proposal + spec-delta) e Phase 3 (design + tasks + **ADR 0004** + **risk-register**) presentes. ADR
  justificado (decisão arquitetural A2 vs A1); risk-register justificado (multi-módulo + dep externa
  Soot + acoplamento de build). `.openspec.yaml` presente.

### Grupo 2 — Traceability e coerência cruzada
- **Item 3 — PASS.** Cadeia sem claim órfão. Os 5 invariantes novos (INV-ANA-40..44) estão **definidos**
  na spec-delta (§Invariants), **mapeados** em `design.md` (tabela Spec→Impl→Test: 40→extractor,
  41→`MopSpecsTargetSource.load`, 42→`TargetMatching`+2 pontos, 43→`forceResolveTargets`+degrade,
  44→key-set diff) e **cobertos por task** (40→1.1-1.6, 41→2.1-2.2, 42→2.3/2.4/3.1/3.2, 43→2.3/2.4,
  44→4.4). Nenhum invariante citado sem definição; INV-ANA-15/17/18/19/33/35 são referências a
  invariantes pré-existentes (corretamente tratados como contexto, não redefinidos).
- **Item 4 — PASS.** Os **8 acceptance criteria** da issue #69 estão todos cobertos:
  (1) extractor N>0 → tasks 1.2-1.5 + cenários "Extractor loads…"/"Wildcard method name…";
  (2) A2 `canStoreType` interface→interface nos 2 pontos → tasks 3.1/3.2 + cenários "Subtype match"/
  "Interface-typed call site"/"Predicate applied at both match points";
  (3) `forceResolve` HIERARCHY + degrade equals+log → task 2.3 + cenário "force-resolved…graceful
  degradation" + INV-ANA-43;
  (4) schema intacto → task 4.4 + cenário "Output schema unchanged" + INV-ANA-44;
  (5) parity JCA byte-a-byte → task 3.3 + cenário "JCA exact path" + INV-ANA-35;
  (6) 2 JARs na ordem → tasks 4.1/4.2 + RISK-003;
  (7) IT 1 APK `reachesTarget>0` na scene real → task 4.3 + RISK-001;
  (8) testes novos (extractor + unit `canStoreType`) → tasks 1.4/1.5/2.4.
- **Item 5 — PASS.** RISK-001 vira gate explícito em **task 4.3** ("0 degrade warnings", IT na scene
  real do `RvsecAnalysisClient`); RISK-003 vira gates em **tasks 4.1→4.2** (ordem) + **4.5** (canary
  pós-rebuild N>0). INV-ANA-43 cobre formalmente a degradação sem falso-negativo silencioso.

### Grupo 3 — Numeração de invariantes
- **Item 6 — PASS (recontado do zero).** Maior INV-ANA em uso fora de gh69: **39** (gh60 usa 30-38,
  gh66 usa 39; gh57 usa 20-25; specs sincronizados vão até 25; archive até 25). **INV-ANA-40..44 estão
  livres** — sem colisão com gh57/gh60/gh65/gh66 in-flight nem com `openspec/specs`/`archive`.

### Grupo 4 — ADDED vs MODIFIED + dependência gh60
- **Item 7(a) — PASS.** `## ADDED Requirements` é a operação correta: a change **acrescenta** um
  requirement novo ("Subtype/Wildcard-Aware Target Matching") à capability `analysis`; não reescreve
  texto de um requirement já sincronizado. `proposal.md` enquadra como *Modified Capability* `analysis`
  — consistente (modifica a capability adicionando-lhe um requirement).
- **Item 7(b)/(c) — RESSALVA (gap de sync-ordering, não bloqueia apply).** Verificado:
  `openspec/specs/analysis/spec.md` **não contém** INV-ANA-33/35 nem `TargetResolver/TargetMethod/
  MatchPolicy` (grep vazio) — gh60 está **OPEN e não-sincronizado**. A spec-delta do gh69 **referencia**
  INV-ANA-33/35 e "builds on `TargetMethod`/`MatchPolicy`/`TargetResolver`". Logo, se gh69 for
  arquivado/sincronizado **antes** de gh60, o `analysis/spec.md` resultante terá **referências
  pendentes** (INV-ANA-33/35 inexistentes). **Nenhum artefato do gh69 documenta a ordem obrigatória
  gh60→gh69**, e o risk-register não tem entrada para isso. *Correção proposta:* (i) anotar em
  `proposal.md §Impact` que **gh60 DEVE ser sincronizado/arquivado antes de gh69**; (ii) opcionalmente
  uma RISK-008 (sync-ordering) no register. Coerente com o caveat de batch-archive já registrado para
  gh50/52/53 (a ordem importa). Não afeta `/opsx:apply` (só morde na Phase 6 — archive/sync).

### Grupo 5 — Grounding no código real
- **Item 8 — PASS.** `rvsec` duplicado confirmado: gator em
  `…/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/{commons,client,sootandroid}` e extractor em
  `…/rvsec/rvsec/rvsec-mop-extractor` (caminhos **absolutos** existem). `generic_new` = 27 `.mop`,
  `jca` = 23 `.mop`.
- **Item 9 — PASS (refs exatas).** Verificado contra o código atual:
  - Extractor `UsedJcaMethodsVisitor.java`: `if (n.isAsterisk()) { return; }` (**linha 38-39**) e gate
    `if (imports.containsKey(clazzName)) {` (**linha 72**) — verbatim. `visit(MethodPointCut)` (70-78)
    não tira `+` nem trata `add*` hoje.
  - `model/MopMethod.java`: hoje só `className/name/parameters/signature` (linhas 10-13), **sem**
    `includeSubtypes/nameIsPattern`. *(Nota cosmética: o campo chama-se `parameters`/`name`, não
    `params`/`methodName`; os artefatos usam `name` de forma consistente — sem impacto.)*
  - `commons/.../target/TargetMethod.java`: `className/methodName/params/signature/policy`, todos
    `final` (linhas 29-33), 1 construtor, **sem** flags novas.
  - `client/.../target/MopSpecsTargetSource.load()`: mapeia `MopMethod→TargetMethod` campo-a-campo
    (linhas 34-39, `MatchPolicy.LENIENT` fixo) — não propaga flags (ainda inexistentes).
  - `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` em **linha 574 exata**: constrói
    `targetKeys` no formato `declaringClass#method` (583-586) e casa por `Set.contains` (629) —
    confirma o claim "chaves pré-resolvidas". `findDirectTargetCallers` em **linha 447 exata** (CG-based,
    consome o set resolvido).
  - `TargetResolver.resolveInScene`: `equals(className) && equals(methodName)` (**linha 53**).
  - Soot `canStoreType`/`getActiveHierarchy`/`getOrMakeFastHierarchy`/`FastHierarchy`/`forceResolve`:
    **0 ocorrências** em commons/client — integração net-new confirmada.
- **Item 10 — PASS (`javap` em `soot-4.7.1.jar`).** `FastHierarchy.canStoreType(soot.Type, soot.Type)`;
  `Scene.getOrMakeFastHierarchy()→FastHierarchy`; `Scene.forceResolve(String,int)→SootClass`;
  `SootClass.HIERARCHY/SIGNATURES/BODIES` presentes. Versão **4.7.1** confirmada via property
  `soot.version` no pom avô `…/workspace-rv/rvsec/pom.xml:38` (`org.soot-oss`), resolvida por
  `help:evaluate`. *(As assinaturas usadas em `design.md §API` batem exatamente.)*
- **Item 11 — PASS.** `client/pom.xml:40-43` declara `br.unb.cic:rvsec-mop-extractor` como dependência
  **compile-scope** (sem `<scope>`). Cópia dos JARs para `rv-android/lib/gator/` herdada do pom-pai
  gator (`rvsec-gator/pom.xml:71-93`, `maven-resources-plugin`, fase **install**); extractor copia para
  `rv-android/lib/mop-extractor/` (`rvsec-mop-extractor/pom.xml:59-83`). Ordem D6 (extractor `install`
  → gator rebuild) e `sootandroid` no `-pl` (preserva arity guard) confirmados como necessários.

  **RESSALVA 5a (path nas tasks — corrigir antes do apply).** As tasks **1.6, 2.5, 4.1, 4.2** usam
  `cd rvsec/rvsec/rvsec-mop-extractor` / `cd rvsec/rvsec/rvsec-android/rvsec-gator` — caminhos
  **relativos sem `../`**. A partir do diretório-raiz do projeto (`…/rvsec/rv-android`, onde
  `/opsx:apply` roda), esses paths **não existem** (`[ -d rvsec/rvsec/… ] → NO`); só resolveriam se o
  CWD fosse `workspace-rv/`. O correto é `cd ../rvsec/rvsec-mop-extractor` e
  `cd ../rvsec/rvsec-android/rvsec-gator` (confirmado: `[ -d ../rvsec/rvsec-android/rvsec-gator ] → YES`).
  A própria §14/R-12a deste doc já havia fixado o path com `../`, mas o `tasks.md` reintroduziu a forma
  sem prefixo → **todos os comandos mvn das tasks falhariam como escritos**.

  **RESSALVA 5b (linha errada em proposal — cosmética).** `proposal.md:79` cita o arity guard em
  `FlowgraphRebuilder.java:212-225,647-660`. O primeiro guard está em **212-225** (correto); o segundo
  está em **704-717**, **não** em 647-660. O guard existe e está correto; só a faixa de linha citada
  está errada (propagar a correção para qualquer outro doc que repita 647-660).

### Grupo 6 — Fidelidade às decisões + escopo
- **Item 12 — PASS.** ADR 0004 bate com `design.md` D1/D2; status **Accepted** apropriado (decisão
  fechada por spike antes de código). Evidência do spike citada **fielmente** vs
  `out/spike_subtype_hierarchy/spike_result.txt`: `getImplementersOf(Iterable)` = 4 implementers
  `[ArrayList, AbstractList, AbstractCollection, TextUtils$SimpleStringSplitter]` (List **ausente**) ✓;
  call site real `iterator <- java.util.List` ✓; `String <: CharSequence : canStoreType=true` ✓;
  `ByteArrayInputStream <: Closeable : one side NOT in Scene` ✓. *(Observação de baixa severidade: o
  spike **não** roda `canStoreType(List, Iterable)` diretamente — exigiria ambos no Scene; o ADR infere
  esse caso a partir de `String<:CharSequence` e o cenário 4 da spec o trata como asserção do
  `TargetMatchingTest`. É a justificativa exata de INV-ANA-43/`forceResolve` — internamente coerente.)*
- **Item 13 — PASS.** Schema-intacto (decisão B / INV-ANA-44) consistente em TODOS os artefatos
  (proposal, spec, design D3, RISK-007, cenário "Output schema unchanged"). Nenhum lugar propõe chave
  nova/per-spec/`targetSummary` (D3 rejeita explicitamente a variante aditiva).
- **Item 14 — PASS.** Escopo C respeitado: o sweep/dataset dos 400 APKs fica fora (design §Non-Goals;
  tasks **4.5/5.2** dizem explicitamente "do NOT launch the full 400-APK sweep"). Nenhuma task/spec
  vaza dataset para dentro da change.
- **Item 15 — PASS.** Checkbox no formato `- [ ] X.Y`; comandos são **mvn/JUnit** (Java), não skills
  Python `/rv-*` inaplicáveis; `/rv-code-reviewer` (agnóstico) mantido em 5.3 e `/opsx:verify` em 5.4.

### Observação adicional (baixa severidade, para o implementador)
- `design.md §API` especifica `matches(SootMethodRef callSite, …)`, mas dos 2 pontos de match um itera
  `SootMethod` (`TargetResolver.resolveInScene`) e outro `SootMethodRef` (bytecode scan). O helper
  precisará de adaptação/overload (`m.makeRef()` ou passar declaringClass/name). Detalhe de
  implementação, não defeito de spec — anotar na task 2.3.

### Veredito

**Artefatos quase prontos — corrigir 3 RESSALVAS antes do `/opsx:apply` (todas baratas; nenhuma altera
o design A2/B/C nem a numeração de invariantes):**

1. **(bloqueia execução das tasks) RESSALVA 5a** — corrigir os `cd` em `tasks.md` 1.6/2.5/4.1/4.2 para
   `../rvsec/rvsec-mop-extractor` e `../rvsec/rvsec-android/rvsec-gator` (ou caminhos absolutos). Como
   estão, falham a partir da raiz do projeto.
2. **(morde na Phase 6) RESSALVA 7(b)/(c)** — documentar a ordem obrigatória **gh60 sync/archive →
   gh69** em `proposal.md §Impact` (e, opcional, RISK-008 no register), evitando referências pendentes
   a INV-ANA-33/35 no `analysis/spec.md` sincronizado.
3. **(cosmética) RESSALVA 5b** — corrigir a faixa de linha do segundo arity guard em `proposal.md:79`
   (`647-660` → `704-717`).

Tudo o mais: **PASS** — diagnóstico, traceability completa (8/8 ACs), numeração 40-44 livre, decisão A2
fiel ao spike, schema-intacto, parity JCA, API Soot 4.7.1 exata, acoplamento de build e ordem de rebuild
corretos. Após as 3 correções, **os artefatos ficam prontos para `/opsx:apply`**.

### Correções aplicadas (2026-06-17)

Todas as 3 RESSALVAS + a observação ao implementador foram corrigidas; `openspec validate` segue *valid*
(4/4):

1. **RESSALVA 5a (RESOLVIDA)** — `tasks.md` 1.6/2.5/4.1/4.2: `cd rvsec/rvsec/…` → `cd ../rvsec/…`
   (relativo à raiz `rvsec/rv-android`); nota explicando o `rvsec` duplicado adicionada à task 1.6.
   Confirmado: `grep 'cd rvsec/rvsec' tasks.md` → vazio.
2. **RESSALVA 7(b)/(c) (RESOLVIDA)** — `proposal.md §Impact`: adicionada a **ordem obrigatória gh60→gh69**
   (sync/archive) com referência a RISK-008; **RISK-008** criado no `risk-register.md` (Low; sumário
   7→8, Low 3→4; indicador `grep INV-ANA-33/35 analysis/spec.md` não-vazio antes do sync; checklist +
   change log atualizados).
3. **RESSALVA 5b (RESOLVIDA)** — `proposal.md:79`: arity guard `647-660` → `704-717`. Confirmado:
   `grep 647-660` na change → vazio.
4. **Observação ao implementador (INCORPORADA)** — task 2.3: nota sobre `SootMethodRef` (bytecode scan)
   vs `SootMethod` (`resolveInScene`) — expor `matches(...)` para os dois pontos (overload / `makeRef()`).

**Veredito final: artefatos prontos para `/opsx:apply`.**
