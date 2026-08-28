# Sweep estático (reachability-only) nos 400 APKs — specs GENERIC_NEW — plano de execução

**Data:** 2026-06-11
**Objetivo:** computar a **reachability** e o **reachesTarget** de cada um dos **400 APKs
originais** contra o spec set **`generic_new`** (NÃO jca), para **definir o dataset do
experimento generic** — quais APKs alcançam os targets genéricos entram no experimento
(análogo ao JCA, onde 380→226 `reaches_mop`). Foco **apenas em reachability**: `--skip-wtg`
(não precisamos de `windows[]`/`transitions[]`).

> Tarefa NOVA e independente da JCA (essa segue em `out/sweep_20260604_wtg_spark/`).
> Outro spec set, outros 400 APKs, output próprio: `out/sweep_generic400/`.

## 1. Ponto de partida

| Item | Valor |
|------|-------|
| Script base | `scripts/static_analysis_sweep.py` (resume + classificação por completude + CSV) |
| Script adaptado | `scripts/static_analysis_sweep_generic.py` (expõe `--mop-dir`) |
| Launch Estágio A | `scripts/run_sweep_generic400_stageA.sh` (paths fixados + corrigidos) |
| 400 APKs originais | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` |
| Specs GENERIC_NEW (mopDir) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new` (27 `.mop`) |
| RVSEC_HOME | `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec` |
| ANDROID_HOME | `/home/pedro/desenvolvimento/aplicativos/android/sdk` |
| Output NOVO | `out/sweep_generic400/` |
| `_progress/<apk>.json` | stem **sem** `.apk` (ex.: `app.dumdum_14.json`); JSON do GATOR em `out/sweep_generic400/<package>/<apk>.apk.json` |

Com `--skip-wtg`, a WTG nem é construída → rápido, sem timeouts de WTG; `transitions[]`
fica `[]` (esperado, não usamos). `reachability` é gravada write-first, então mesmo
timeout/kill na reachability preserva o JSON.

## 2. Decisões tomadas (2026-06-11)

1. **mopDir = generic_new (obrigatório):** o sweep base não expõe `mop_dir` e o config
   faz **default para `jca`**. Sem `--mop-dir`, roda JCA por engano. Por isso a adaptação
   (§3) e o launch script fixam `--mop-dir .../generic_new`. **Sempre conferir no comando
   GATOR que aparece `mopDir=.../generic_new`** (verificado em §4).
2. **SPARK na reachability:** `--cg-algorithm spark` (default) — um único call graph na
   Scene alimenta o `ReachabilityEngine`. Manter o default.
3. **Sem WTG / sem Estágio B:** reachability-only (`--skip-wtg`). Não há WTG para "colher"
   com mais tempo. A escada é só **A (bulk)** → **C (memória↑)** para os patológicos de
   reachability.
4. **Sem `--planilha`:** a PLANILHA de cross-validation é JCA/androguard-específica; as
   colunas não fazem sentido no generic. Não usar.
5. **Não rebuildar o gator:** a `lib/gator/*.jar` atual tem um fix de arity não-commitado
   no `FlowgraphRebuilder`, mas ele só afeta o caminho `cgDelegation=true` da **WTG**.
   **Com `--skip-wtg` é irrelevante** — a JAR atual serve, nada a commitar para este sweep.

## 3. Adaptação do script (feita e verificada)

`scripts/static_analysis_sweep.py` → `scripts/static_analysis_sweep_generic.py`. Diff é
**exatamente** duas adições (nada mais):

1. Novo argumento (junto a `--rvsec-root`):
   ```python
   parser.add_argument("--mop-dir", type=str, default=None,
                       help="JavaMOP specs directory (mopDir). Overrides the jca default. "
                            "Mutex with targets_file (INV-ANA-33).")
   ```
2. Propagação em `build_config_kwargs(...)`, antes do `return kwargs`:
   ```python
   if getattr(args, "mop_dir", None):
       kwargs["mop_dir"] = args.mop_dir
   ```

`RVStaticAnalysisConfig` já aceita `mop_dir` (mutex com `targets_file`, INV-ANA-33) e o
propaga como `-clientParam mopDir=<path>`. Passar **só** `--mop-dir`.

## 4. Verificações pré-execução (2026-06-11)

Todas concluídas antes de qualquer run:

- **Path dos specs corrigido:** o prompt original tinha inconsistência — a tabela usa
  `.../rvsec/rvsec-mop/...` (correto, existe) mas os exemplos de comando usavam
  `.../rvsec/rvsec-android/rvsec-mop/...` (**não existe**). Os scripts usam o path correto.
- **Diff mínimo:** `diff` confirma só as 2 adições; `py_compile` OK; `--help` mostra `--mop-dir`.
- **Comando GATOR renderizado** (via `config.get_tool_command("analysis", ...)`):
  ```
  ... -client RvsecAnalysisClient \
      -clientParam mopDir=.../rvsec-mop/src/main/resources/generic_new \
      -cgAlgorithm spark --timeout 900 --jvm-memory 12G -clientParam skipWtg=true
  ```
  `mopDir=generic_new` ✅ · `skipWtg=true` ✅ · `spark` ✅ · **sem `jca`** ✅.
- **Prova de que a flag importa:** sem `--mop-dir`, o mesmo render cai em
  `mopDir=.../resources/jca` (default silencioso) — confirma a necessidade da adaptação.
- **Dry-run** (`--dry-run --limit 5`): "Found 400 APK(s)", "To process: 5".
- **Inventário:** 400 APKs · 27 `.mop` · gator jars presentes · launch script `bash -n` OK.
- **Nota:** o dry-run criou o scaffold `out/sweep_generic400/{_logs,_progress,_backup}` com
  **0 entries** — inócuo; o sweep resume limpo e processa os 400.

## 5. Escada de execução

Todos os estágios escrevem no MESMO `out/sweep_generic400/` (consolidação por resume).

### Estágio A — bulk (todos os 400)
```bash
scripts/run_sweep_generic400_stageA.sh
# equivale a:
uv run python scripts/static_analysis_sweep_generic.py \
    --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs \
    --output ./out/sweep_generic400 \
    --mop-dir /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new \
    --skip-wtg --cg-algorithm spark \
    --timeout 900 --workers 8 --jvm-memory 12g
```
Rodar em background; o script grava `out/sweep_generic400/sweep.pid`. Parar com
`kill -INT $(cat out/sweep_generic400/sweep.pid)`. Reachability-only fecha rápido na
maioria; só poucos patológicos precisam de memória (Estágio C).

### Estágio C — escalonamento de memória (só os que falharam/partial)
Referência empírica do skip-wtg nos 169 (mesmo protocolo): a maioria fecha com 8w/900s/12g;
**~4 "FixpointSolver"** precisaram de **2w/3600s/60g**; **1 OOM** (`com.infomaniak.meet`,
118MB/6dex) precisou de **1w/3600s/100g**. Esperar proporção parecida nos 400.

1. Montar symlink dir só com falhos/partial (status != complete OU reachability vazia):
   ```bash
   python3 - <<'PY'
   import json, glob, os
   OUT="out/sweep_generic400"; src="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs"
   rows=[json.load(open(f)) for f in glob.glob(f"{OUT}/_progress/*.json")]
   pend=[r["apk_name"] for r in rows
         if r.get("status")!="complete" or int(r.get("methods_total") or 0)==0]
   d=f"{OUT}/_stageC_apks"; os.makedirs(d,exist_ok=True)
   for f in os.listdir(d): os.unlink(os.path.join(d,f))
   for n in pend:
       s=os.path.join(src,n)
       if os.path.exists(s): os.symlink(s, os.path.join(d,n))
   print(f"pendentes p/ Estágio C: {len(pend)} -> {d}")
   PY
   ```
2. Re-rodar com 60g (`--retry-statuses` cobrindo `failed_no_json`, que NÃO está no retry default):
   ```bash
   uv run python scripts/static_analysis_sweep_generic.py \
       --apks-dir out/sweep_generic400/_stageC_apks --output ./out/sweep_generic400 \
       --mop-dir /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new \
       --skip-wtg --cg-algorithm spark \
       --retry-statuses "complete,failed_no_json,failed_timeout_no_json,partial_empty_reachability,partial_reachability_only,unparseable" \
       --timeout 3600 --workers 2 --jvm-memory 60g
   ```
3. Se ainda sobrar OOM, rebuildar o symlink dir dos remanescentes e rodar `--workers 1 --jvm-memory 100g`.

## 6. Resume (se parar no meio)

O script resume sozinho pelo `out/sweep_generic400/_progress/*.json`. Re-rodar o MESMO
comando do Estágio A continua de onde parou (pula os `complete`). Para FORÇAR
reprocessamento de status que o resume normalmente pula (ex.: escalonar memória), usar o
**symlink-subset + `--retry-statuses`** como no Estágio C — evita refazer os já-resolvidos.

## 7. Monitoramento (snapshot com timestamp)
```bash
python3 - <<'PY'
import json, glob, collections
OUT="out/sweep_generic400"
rows=[json.load(open(f)) for f in glob.glob(f"{OUT}/_progress/*.json")]
st=collections.Counter(r.get("status") for r in rows)
reach=sum(1 for r in rows if int(r.get("methods_total") or 0)>0)
tgt=sum(1 for r in rows if int(r.get("methods_reach_mop") or 0)>0)
print(f"completados: {len(rows)}/400 | status={dict(st)}")
print(f"  com reachability: {reach} | reachesTarget>0 (generic): {tgt}")
PY
```
Também: `tail -f out/sweep_generic400/_logs/*.log` e `out/sweep_generic400/progress.csv`.

## 8. Critério de sucesso / saída

- **400/400 processados**, 0 (ou pouquíssimos, com motivo) `failed_*` após o Estágio C.
- Cada APK com JSON íntegro: `reachability` populada, `complete:true`, `transitions:[]`
  (esperado com skip-wtg).
- `reaches/directlyReachesTarget` calculado contra **generic_new** → base para **filtrar o
  dataset do experimento** (APKs que alcançam os targets genéricos).
- Consolidar `out/sweep_generic400/progress.csv` e listar os APKs com `reachesTarget>0`.

## 9. Notas / gotchas

- **mopDir default é jca** — sem `--mop-dir`, o sweep roda JCA por engano. Conferir sempre.
- **NÃO usar `--planilha`** (cross-validation é JCA/androguard).
- **`mop_dir` e `targets_file` são mutex** (INV-ANA-33) — passar só `--mop-dir`.
- **Não tocar** em `out/sweep_20260604_wtg_spark/` nem `out/sweep_20260604/` (JCA, outra tarefa).
- **Não rebuildar o gator** — JAR atual serve; com `--skip-wtg` o fix de arity é irrelevante.
- rv-platform gerencia emulador — aqui não há emulador (análise estática pura).

## 10. Execução real e resultado

> A preencher após rodar. Registrar: data/hora, wall-clock do Estágio A, balanço de
> status (complete / partial / failed_*), nº com `reachability`, nº com `reachesTarget>0`
> (generic), patológicos resolvidos no Estágio C (memória usada), e a lista final de APKs
> que entram no dataset do experimento generic.

**Status em 2026-06-11:** tudo pronto e verificado (§3, §4).

**Estágio A LANÇADO 18:25 → HALTADO 18:50 (BLOCKER).** Background via `nohup`. Confirmado
em runtime: `mopDir=.../generic_new` ✅, `skipWtg=true` ✅, reachability OK (28k+ métodos).
**MAS:** `reachesTarget=0` em TODOS os 49 APKs processados. Parado em 49/400 (42 reachability,
0 reachesTarget) para não queimar horas de SPARK gerando dataset inútil.

### BLOCKER: extractor de MOP não suporta o estilo dos specs generic_new

Log por-APK: `[MopSpecsTargetSource] Loaded 0 MOP signatures from .../generic_new` →
`MOP methods resolved: 0` → `reachesTarget: 0`. **Causa-raiz no código** (`rvsec-mop-extractor`,
`visitor/UsedJcaMethodsVisitor.java`):

- `visit(ImportDeclaration)`: `if (n.isAsterisk()) return;` → **ignora imports wildcard**.
- `visit(MethodPointCut)`: só extrai se `imports.containsKey(clazzName)` → **exige a classe
  como import EXPLÍCITO** e casa o owner por nome exato.

O extractor foi escrito para o estilo **JCA**: imports explícitos
(`import javax.net.ssl.KeyManagerFactory;`) + pointcuts com classe.método explícitos
(`call(... KeyManagerFactory.getInstance(String))`). O **generic_new** usa outro estilo:
- **26/27** `.mop` têm SÓ imports wildcard (`java.io.*`, `java.util.*`, `java.lang.*`, ...).
- pointcuts com **subtipo `+`** e wildcard de retorno: `call(* Closeable+.close())`,
  `call(boolean Collection+.addAll(..))`, `call(Set Map+.keySet())`, `call(* ServerSocket+.accept(..))`.

Resultado: `imports` fica sem `Closeable`/`Collection`/`Map`/etc. → 0 métodos extraídos →
`reachesTarget=0` para todo APK. **A reachability em si está correta** (write-first), mas é
inútil sem os targets — e como os targets são resolvidos DENTRO do mesmo run do GATOR, o
output atual NÃO é reaproveitável: qualquer correção exige re-rodar o GATOR.

### Investigação mais profunda (2026-06-11): o problema é ARQUITETURAL, não só de parsing

Tracei toda a cadeia de matching de targets no gator client:

- **`TargetResolver.resolveInScene`** (`client/.../target/TargetResolver.java`): casa target↔Soot
  por **FQN exato** — `t.getClassName().equals(cls.getName()) && t.getMethodName().equals(name)`.
- **`findDirectTargetCallersByBytecodeScan`** (`RvsecAnalysisClient.java:574`): a chave do scan é
  `declaringClass.getName()+"#"+methodName` dos SootMethods **resolvidos** — também FQN exato,
  sem hierarquia.
- **`ReachabilityEngine`**: roda BFS no CG a partir do `Set<SootMethod> targets` resolvido. Tudo
  depende da resolução exata.

**Implicação:** os specs generic_new miram **supertipos com `+`** (`Collection+.add*`, `Map+.keySet`,
`Closeable+.close`, `ServerSocket+.accept`). Mesmo que o target `java.util.Collection.addAll` fosse
resolvido, um call site em `ArrayList.addAll` / `List.add` **não casa** (FQN ≠). O pipeline inteiro
(extractor → resolver → bytecode scan) é **exact-FQN, NÃO subtype-aware**.

**Quantificação** (89 pointcuts `call(...)` nos 27 `.mop`):
- **71/89 (80%) usam subtipo `+`** → exigem match por hierarquia (`Collection+`×20, `Map+`×11,
  `Reader+`×6, `InputStream+`×5, `ServerSocket+`×4, ...).
- 18/89 "exatos" — e parte são construtores (`ServerSocket.new`, `TreeMap.new`) + `Long.parseLong`.

Ou seja: **80% do generic_new é inalcançável sem matching por hierarquia de tipos** — uma adição
de feature à camada de reachability/target do gator, não um parse-fix pequeno. Preserva-se
INV-ANA-35 (LENIENT por className,methodName) e `MopSpecsParityTest` no caminho JCA.

**Opções reformuladas (a decidir com o usuário):**
1. **Subtype-aware matching (fix correto e completo):** tornar `TargetResolver` + bytecode-scan
   hierarchy-aware (expandir cada classe-alvo aos subtipos/implementadores via Soot
   `FastHierarchy`/`getActiveHierarchy`, ou testar `isSubtype` no scan) **+** corrigir o
   extractor para imports wildcard/`+`/retorno-wildcard. Único caminho que cobre os 80% `+`.
   Mexe no gator client + extractor → rebuild de 2 JARs; tem invariantes/testes a preservar.
   → Candidato a mudança via OpenSpec (toca tooling de análise estática, decisão de design).
2. **`--targets-file` só com o subset exato:** cobre apenas os ~18 pointcuts sem `+` (e nem os
   construtores). **Deixa 80% de fora silenciosamente** — dataset generic incompleto. Não
   recomendado como solução, serve no máximo de smoke parcial.
3. **Re-escrever os specs generic_new sem `+`** enumerando classes concretas: inviável (subtipos
   ilimitados em código de app).

Sweep parado em 49/400; nada reprocessado. Decisão pendente sobre o caminho 1 (provável via
OpenSpec) antes de re-lançar.

### Investigação do fix (2026-06-13): onde mexer, em quê e tamanho

Tracei o AST do parser JavaMOP, a grammar, a API do Soot e os testes. O fix tem **dois
componentes** em **dois módulos** (2 JARs a rebuildar).

**Como os specs genéricos são representados no AST** (verificado no código):
- `MethodPointCut.getSignature()` → `MethodPattern` (estende `FieldPattern`): `getOwner()` é um
  `TypePattern` cujo `getOp()`/`toString()` carrega a **string literal** do dono.
- O `+` de subtipo é **concatenado à string** na grammar (`aspectj.jj:2073/2333`: `id.str += "+"`).
  Logo o dono de `call(* Closeable+.close())` é a string `"Closeable+"` — `+` grudado.
- Retorno wildcard (`*`) vira `BaseTypePattern("*")` e **já é ignorado** (o extractor não usa o
  tipo de retorno) → inócuo.
- **3ª dimensão de wildcard:** nome de método com `*` (`Collection+.add*`, `remove*`, `retain*`).
  O extractor guarda o memberName literal `"add*"` → o matcher exato nunca casa.

Resumo: os specs genéricos exigem **3 capacidades novas** que o JCA nunca precisou —
(1) dono por **subtipo** (`+`), (2) dono via **import wildcard** (`java.io.*`), (3) **nome de
método com wildcard** (`add*`). O JCA usa import explícito + classe.método exatos, então segue
o caminho atual **inalterado** (preserva INV-ANA-35 / `MopSpecsParityTest`, que só exercita
CipherSpec+MessageDigestSpec — sem `+`/wildcards).

**Componente 1 — Extractor (`rvsec-mop-extractor`, `visitor/UsedJcaMethodsVisitor.java`)**
- `visit(ImportDeclaration)`: parar de descartar `isAsterisk()`; registrar os **pacotes**
  wildcard (`java.io`, `java.util`, `java.lang`, ...).
- `visit(MethodPointCut)`: (a) tirar o sufixo `+` do dono e marcar `includeSubtypes=true`;
  (b) resolver nome simples→FQN: primeiro `imports` explícitos, senão tentar
  `Class.forName(pkg+"."+simple)` sobre os pacotes wildcard (são todos classes do JDK →
  resolve em runtime do extractor); (c) preservar wildcard de nome de método (`add*`) como
  padrão, não literal.
- `model/MopMethod`: ganhar flags `includeSubtypes` e `methodNameIsPattern` (hoje só carrega
  className/name/params/signature).

**Componente 2 — Matching de reachability (`rvsec-gator/client` + `commons`)**
- `commons/.../target/TargetMethod`: novo `MatchPolicy.SUBTYPE` (ou flag `includeSubtypes`) +
  suporte a nome-padrão. Propagar de `MopMethod` → `TargetMethod` em `MopSpecsTargetSource`.
- `client/.../target/TargetResolver.resolveInScene`: quando `includeSubtypes`, expandir a
  classe-alvo aos **subtipos** no Scene via Soot `Scene.v().getActiveHierarchy()`
  (`getSubclassesOf` p/ classes, `getImplementersOf`/`getAllImplementersOfInterface` p/
  interfaces) — Soot é `org.soot-oss` 4.x, a API existe; e casar nome de método por padrão.
- `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` (e `findDirectTargetCallers`):
  hoje a chave é `declaringClass#method` dos SootMethods já resolvidos. Se o resolver expandir
  aos subtipos, as chaves já incluem `ArrayList#add` etc. → o scan passa a casar. (Alternativa:
  testar `fastHierarchy.canStoreType` no scan, mas reusar a expansão do resolver é mais simples.)

**Tamanho/risco estimado:** ~2 arquivos no extractor + ~3 no gator client/commons; +1 flag em 2
modelos; testes novos (parity generic + um IT de 1 APK). Rebuild de `rvsec-mop-extractor` e das
2 JARs do gator (`lib/gator/*.jar`). Risco baixo p/ JCA (caminho exato preservado); risco médio
na semântica da expansão.

**⚠️ Subtleza semântica a decidir (não é bug):** alguns specs genéricos miram interfaces
**universais** — `Object+` (`Object_MonitorOwner`), `Comparable+`, `Iterable+`, `CharSequence+`.
Expandir `Object+` casa **toda** classe do app → `reachesTarget` vira trivialmente verdadeiro
para quase todo APK. É o que o spec literalmente diz, mas pode tornar o filtro do dataset
inútil p/ esses specs. Opções a alinhar no design: (i) aceitar como está; (ii) reportar
reachesTarget **por-spec** (não agregado) p/ excluir os universais do critério de dataset;
(iii) excluir specs `Object+`/`Comparable+` do conjunto de filtragem. Decisão de experimento →
pergunta ao usuário no `/opsx:explore`.

**Conclusão:** o caminho 1 é uma feature bem-delimitada (subtype/wildcard-aware target matching),
não um patch. Recomendo formalizar via **OpenSpec** (`gh<N>-generic-subtype-target-matching`):
`/opsx:explore` → `/opsx:new` (proposal+specs) → design (ADR p/ a decisão de hierarquia + a
subtleza dos universais) → implement → rebuild 2 JARs → re-lançar Estágio A.

> **Plano do fix (separado):** `docs/20260617_sa_generic_new.md` — change
> `gh<N>-generic-subtype-target-matching` (extractor + matcher A2, schema intacto). Este doc
> (sweep/dataset) é o consumo posterior. Decisões A=A2, B=descartada, C=escopo lá consolidadas.

### Spike A1 vs A2 (2026-06-13) — DECIDIDO: A2 (canStoreType no match)

Probe throwaway (`out/spike_subtype_hierarchy/`) num APK pequeno (`com.mine.autoshine`),
Soot Android scene (Soot 4.7.1 do fat jar do gator). Resultado:
- **(2) `getImplementersOf` (mecanismo do A1) é incompleto:** `Collection`→3 implementers,
  `Iterable`→4 — e crucialmente **não inclui sub-interfaces** (`java.util.List` ausente do
  implementers de `Iterable`). Só retorna o que está no Scene daquele app.
- **(3) `FastHierarchy.canStoreType` (mecanismo do A2) funciona em tipos de biblioteca:**
  `ArrayList<:Collection`=true, `HashMap<:Map`=true, `String<:CharSequence`=true.
- **(4) call site real do app:** `iterator <- java.util.List` — a classe declarante é a
  **interface** `List`. A1 (chave `List#iterator` não existe no conjunto expandido de
  `Iterable+`) **erra**; A2 (`canStoreType(List, Iterable)`=true) **acerta**.

**Decisão A = A2:** trocar o predicado de match, em `TargetResolver.resolveInScene` (semear o
BFS reverso do CG) e em `findDirectTargetCallersByBytecodeScan`, de `equals(FQN)` para
`nomeMatchPadrão && canStoreType(classeNoCallSite, superTipoAlvo)`. Custo de hierarquia é
marginal (o scan já itera todos os invokes). A1 fica descartado (incompleto + erra
interface-typed call sites).

### Decisão B (schema por-spec) — análise de risco + desenho (2026-06-13)

> **⚠️ SUPERSEDED por `docs/20260617_sa_generic_new.md` §3.B (validado 2026-06-17 §14):**
> **Decisão B = DESCARTADA — o schema de saída NÃO muda.** Não haverá `targetSummary` nem
> per-spec no estático: a atribuição por-spec vive no **runtime** (handler `.mop` loga
> `RVSEC ... ::: <SpecName>` → `logcat_parser.py` → coluna `spec` em `errors.csv`), e o coverage
> usa o `reachesTarget` **agregado** como denominador (`result_processor.py:402-435`). O desenho
> `targetSummary`/G1×G2 abaixo fica **registrado como histórico** — não implementar. Ler esta seção
> apenas pela análise de risco aditivo×destrutivo (que continua válida e fundamenta manter o schema
> intacto = risco-zero nos dois consumidores).

**Esclarecimento:** o rename `reachesMop → reachesTarget` JÁ foi feito (gh60). `reachesTarget`
é o campo atual e estabelecido — não há nada a renomear. A mudança da Decisão B é **aditiva**.

**Quem consome o `static_analysis.json` — só DOIS pontos fora dos domain objects:**
1. **Python** — `rv-static-analysis/.../parser/static/static_analysis_parser.py`: fronteira
   ÚNICA. Mapeia chaves cruas (`reachesTarget`, `directlyReachesTarget`, `methods`, `signature`,
   `reachable`, ...) → domain objects. Todo o resto (rv-agent, rv-coverage, rv-platform,
   rv-screen-parser) consome **domain object** (`StaticAnalysisData`), NÃO o JSON cru.
2. **Java (ape)** — `ape/.../utils/MopData.java`: parser **tolerante** — usa `opt*` em tudo
   (`optBoolean("reachesTarget", false)`, `optJSONArray("methods")`, `optJSONObject("components")`).

**Matriz de risco (a chave do medo do usuário):**

| Tipo de mudança | Python parser | ape `MopData` | Risco |
|---|---|---|---|
| **ADITIVA** (mantém campos atuais, adiciona novos) | inalterado (só muda se quiser surfar o novo dado → 1 arquivo) | ignora chaves novas (opt*) → 0 quebra | **~nulo** |
| **DESTRUTIVA** (renomeia/remove `reachesTarget`) | quebra (`Keys` map) | `optBoolean` retorna `false` **silenciosamente** → quebra SEM erro | **alto + silencioso** ⚠️ |

Conclusão: o medo é válido **só para mudança destrutiva** (e seria pior — o ape quebra sem
erro, com priorização MOP toda zerada). **Aditivo é risco-zero nos dois consumidores.** Os 60+
arquivos que o grep cuspiu são quase todos `backup/`, `tests/`, ou consumidores de domain object.

**Campo `targetMethods` já existente ≠ o que queremos:** ele vive no nível **componente**
(`writeComponentEntry`/`writeProviderEntry` em `RvsecAnalysisClient.java:1524,1567`) e contém as
**assinaturas dos métodos de lifecycle do próprio componente que alcançam target** (ex.:
`<MainActivity: void onCreate(Bundle)>`) — hint de navegação p/ o ape, NÃO as APIs monitoradas.
Não reutilizar esse nome/semântica.

**Desenho proposto (aditivo) — `targetSummary` por-spec no topo do JSON:**
```jsonc
{
  "complete": true,
  "reachability": [ ... ],          // inalterado (mantém reachesTarget agregado)
  "windows": [ ... ],
  "targetSummary": {                // NOVO, aditivo, ignorado pelo ape (opt*)
    "Collection_UnsynchronizedAddAll": { "reaches": 12, "directlyReaches": 3 },
    "Iterable_iterator":               { "reaches": 480, "directlyReaches": 220 }, // quase-universal salta à vista
    "Object_MonitorOwner":             { "reaches": 0,  "directlyReaches": 0 }
  }
}
```
Vantagens: responde direto "este APK alcança quais specs e quão intensamente" (filtro do
dataset por-spec); **expõe** os quase-universais (decidir exclusão com dado na mão, sem
adivinhar a priori); puramente aditivo.

**Dependência:** o conteúdo por nome-de-spec só existe se o extractor **carregar a proveniência**
(de qual `.mop` cada alvo veio). Hoje `JavamopFacade` lê arquivo-por-arquivo e descarta o nome.
A mudança do extractor (já necessária p/ subtipo/wildcard) ganha de brinde: anexar `specName` a
cada `MopMethod`.

**Custo (decisão de implementação, não agora):** reachability por-spec muda o BFS reverso —
hoje 1 passada do conjunto-união; por-spec vira N passadas (uma por spec/alvo) ou 1 passada
multi-label (marca cada método com o conjunto de specs cujo reverse-set o inclui). Para o resumo
G1 (só contagens) dá p/ fazer barato. Detalhe de ADR.

**PONTO AINDA EM ABERTO (a discutir):** granularidade —
- **G1 (resumo por-spec, por-APK):** o `targetSummary` acima. Suficiente p/ definir o dataset.
- **G2 (por-método, por-spec):** cada método em `reachability[].methods[]` ganha
  `reachesTargets: [specName, ...]`. Rico p/ guiar o ape em runtime, porém mais caro.

Decisão A (A2) e o desenho do extractor NÃO dependem de fechar G1×G2. Decidir antes de fechar
o design/specs da change.
