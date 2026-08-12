# Registro de execução — prontidão do Estudo 03 (Fases A e B)

Registro narrativo da execução do plano `20260810_plano_prontidao_estudo03.md`, escrito
durante a corrida de 2026-08-11/12. O plano diz o que fazer; este documento diz o que
aconteceu quando se fez, incluindo o que o plano não previu e as conclusões que tiveram de ser
retiradas.

Ele não substitui nem edita o plano. Quatro defeitos foram medidos aqui, três deles em
código de produção; todos estão descritos com `arquivo:linha`, porque handoff, relatório e
aritmética não são verificação.

**Corte deste documento: 2026-08-12 15:10. As duas fases estão encerradas e suas seções são
definitivas, e a validação em emulador dos 162 (P7) foi executada e fechou 162/162 (§3.2).** A Fase A entregou 25/30 e **reprovou** no Gate A; a Fase B entregou **162/163**
e a entrega está consolidada em `APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`,
**o diretório do experimento final** (§3). O que continua aberto são decisões, não medições, e
está na §4.

---

## 1. Fase A — análise estática dos 30 com WTG

**Executada de 2026-08-11 10:56:43 a 2026-08-12 04:59:34, 18,05 h de relógio.** Duas rodadas,
a primeira a 32 g/3600 s com 3 concorrentes, a segunda a 120 g/7200 s serial.

**Resultado: 25/30 completos, 5 truncados. O Gate A REPROVOU, e só na asserção 3.2.**

```
3.1 cardinality                            PASS  (30 JSONs, 30 esperados)
3.2 completeness (sentinela + sem timeout)  FAIL  (5)
3.3a key applied (classes)                 PASS
3.3b key applied (Filter package:)         PASS
3.4 right APK (manifest package)           PASS
3.5 MOP surface preserved (HARD STOP)      PASS
3.7 wtg_status: ok 25 · truncated 5 · unclassified 0
```

Tudo aquilo para que a Fase A existia funcionou: a chave `Mneut` foi aplicada nos 30, o APK
certo foi analisado, e a superfície MOP sobreviveu no HARD STOP — inclusive nos 5 truncados,
porque a seção `reachability` é escrita antes do WTG. O ganho de integridade aparece na 3.6:
`org.wikipedia` saiu de **78 para 7987** classes sob a chave correta, `app.pachli` de 2466 para
6453, `com.jerboa` de 140 para 3171, `swati4star.createpdf` de 35 para 529.

### 1.1 A quarta edição salvou 17% do corpus

Os 5 APKs que falharam deixaram em disco JSONs que **se declaram completos sobre grafos
vazios** — um deles com 12,5 MB, indistinguível de legítimo por tamanho:

| APK superseded (rodada 1) | tamanho | sentinela | transições |
|---|---|---|---|
| `ch.rmy.android.http_shortcuts_1104060001` | 12,5 MB | `complete: true` | 0 |
| `it.niedermann.owncloud.notes_340000090` | 2,2 MB | `complete: true` | 0 |
| `com.darkrockstudios.app.securecamera_31` | 2,1 MB | `complete: true` | 0 |
| `org.glpi.inventory.agent_39469` | 0,3 MB | `complete: true` | 0 |
| `com.github.livingwithhippos.unchained_60` | 0,04 MB | `complete: true` | 0 |

Sob o predicado antigo `has_sentinel`, os cinco entrariam no corpus como prontos. O predicado
novo `is_complete` (`scripts/gh91_campaign.py:126`), que exige sentinela **e**
`timed_out is False`, rejeitou os cinco e os promoveu à rodada 2. Verificado em produção sobre
o arquivo real do `org.glpi`: `has_sentinel → True`, `is_complete → False`.

**Por que o sentinela não basta, no fonte.** `JsonReportWriter.write()` emite o sentinela
**incondicionalmente**, como último campo de toda escrita
(`.../clients/json/JsonReportWriter.java:111`) — não há parâmetro que distinga escrita parcial
de final. E o `RvsecAnalysisClient` chama esse mesmo `write()` **duas vezes**: antes do WTG,
com `wtg = null` (`:167-169`, e o writer então emite `transitions: []`), e de novo depois do
WTG, sobrescrevendo. As duas escritas levam o sentinela.

O comentário do próprio cliente (`:155-163`) declara o contrário — que *"the pre-WTG write does
NOT emit the sentinel"* e que um timeout no WTG deixaria o arquivo *"with NO sentinel"* —, e o
comentário do writer registra o contrato ADR-6, segundo o qual é a **ausência** do sentinela que
marca a amostra como incompleta. **A implementação não faz o que os dois comentários dizem.**
Medido: 5/5 dos truncados da Fase A e 79/79 dos da Phase-7 têm o sentinela.

O `skipWtg=true` da rodada anterior escondia isso porque o cliente retornava logo após a
escrita pré-WTG (`:180-184`) — ali aquele arquivo *era* o final legítimo, e sentinela e
completude coincidiam por acidente do fluxo.

**O tamanho real disto.** A `reachability` é escrita antes do WTG e fica íntegra; o WTG falta de
todo modo. A única coisa que se perde é **saber, olhando só o JSON, se o grafo está vazio por
timeout ou por natureza** — e o `_progress` da corrida responde isso, que é exatamente o que o
`is_complete` passou a consultar. Não há dado corrompido nem análise errada: há um campo que
não carrega a informação que seria conveniente ele carregar. Conserto seria pequeno (um
`boolean partial` no `write()`, ou emitir o sentinela só na segunda chamada), mas é
`rvsec-gator` e não foi feito.

### 1.2 Defeito: o WTG do GATOR trava para sempre quando um worker morre

**As 5 falhas não são fome de recurso.** Os APKs queimaram o teto exato do timeout em toda
rodada — 1800 s a 12 g, 3604 s a 32 g, 7205 s a 120 g — com RSS de 26 GiB contra `-Xmx120G`.
Quadruplicar memória e dobrar tempo não moveu nenhum deles.

A causa, verificada no fonte (código upstream do GATOR, Ohio State 2018, não do rvsec):

- `CFGWorker.run()`
  (`rvsec-gator/sootandroid/src/main/java/presto/android/gui/wtg/parallel/CFGWorker.java:33-42`)
  chama `doTask()` **sem try/catch**. Se `doTask()` lança, a thread morre na linha 34 e a linha
  38, `scheduler.workerPool.put(this)`, nunca executa — o worker não volta ao pool.
- `CFGScheduler.schedule()` (`CFGScheduler.java:66-72`) espera com
  `while (workerPool.size() != Configs.workerNum) Thread.sleep(500)`. Com um worker a menos,
  esse contador nunca mais é atingido. Espera infinita. `Configs.workerNum = 16`
  (`Configs.java:108`).

A exceção observada é `ArrayIndexOutOfBoundsException` em
`ConstantAnalysis.intConstantPropagationAtCall` (`ConstantAnalysis.java:1633`), via
`AbstractInvokeExpr.getArg` do Soot.

**Evidência:** a exceção aparece em **4 dos 30 logs, e os 4 estão entre os 5 que falharam;
zero entre os 25 que passaram**. O `app.pachli` perdeu 14 dos 16 workers. O quinto,
`ch.rmy.android.http_shortcuts`, não tem a exceção e travou por motivo ainda não identificado.

**Consequência prática:** uma terceira rodada não resolveria — o defeito é determinístico e
independe de orçamento. Ao ver um APK estourar timeout dentro do WTG, procurar
`ArrayIndexOutOfBoundsException` no log **antes** de subir orçamento; subir só resolve o caso
genuíno de recurso, que foi o que resgatou `binaryeye` (timeout na Phase-7 → 499 transições) e
`createpdf`, e na rodada 2 `securecamera`, `jerboa` e `wikipedia`.

Corrigir o gator é decisão do pesquisador, e não foi feita: seria um try/catch em
`CFGWorker.run()` com `finally` devolvendo o worker, mas diverge do upstream. Registrado sem
issue, por decisão de 2026-08-12.

### 1.3 `/tmp` é tmpfs — o vazamento de temp dir come RAM, não disco

`findmnt /tmp` → **tmpfs de 62 GiB, em RAM**. O GATOR decodifica cada APK com apktool em
`$TMPDIR/gator-*` (`lib/gator/pygator/unpacker.py:19`, via `tempfile.mkdtemp`) e, no timeout,
`sys.exit(-50)` (`lib/gator/gator:113`) pula o `remove_temp_dirs()` (`:119`).

O plano previu o vazamento mas assumiu que `/tmp` fosse disco. Como o portão de budget
(`gh91_campaign.py:504`) lê `MemAvailable` **uma única vez, no lançamento**, temp dirs vazados
em tmpfs encolhem a RAM durante a corrida sem que nada reclame. Mitigado exportando `TMPDIR`
para `/pedro` antes de lançar; `_gator_env()` (`gh91_sa_rerun.py:333`) herda `os.environ`, então
propaga aos filhos sem mudança de código.

**Medido:** 10 temp dirs vazaram (exatamente os 10 timeouts), **670 MB, todos em disco**;
`/tmp` terminou com zero `gator-*`.

### 1.4 Decisão em aberto

O Gate A não fecha com os 5 truncados, e o portão é coerente ao reprovar — o comentário da 3.7
(`scripts/gh91_gate.py:219-221`) declara que um `truncated` sempre vem acompanhado de falha na
3.2. As saídas visíveis: corpus de 25; ou 30 com `wtg_status = truncated` documentado como
exceção; ou corrigir o `CFGWorker`. **Não decidido.**

---

## 2. Fase B — instrumentação dos 163

O plano orçava **~27 h seriais** (163 × ~600 s), porque `instrument_apks`
(`modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:225`)
é um `for` puro, uma JVM por APK, e o lado Java (`BatchRunner.java:120`) é
`.forEach(apk -> results.add(runPipeline(cfg, apk)))`, também sequencial. Não existe flag
`--jobs` no `rv-experiment`.

**Decisão: paralelizar por sharding de processo** — N processos `rv-experiment`, cada um com
sua fatia do `--apks-filter` e seu próprio `--output-dir`. Escolhida por cima da alternativa
(pool dentro do `instrument_apks`) porque não toca no código que vai tecer o corpus definitivo,
e porque o isolamento necessário vem de graça, pela razão da §2.1.

### 2.1 Duas colisões de estado global que o sharding tem de respeitar

**Primeira, resolvida de graça.** `working_dir = Path(self.output_dir)`
(`modules/rv-experiment/src/rv_experiment/config.py:857`) — o work dir **é** o `--output-dir`.
Dentro do CLI Java os nomes de scratch são planos e compartilhados:
`workDir.resolve("woven_" + ed.entryName)` (`BatchRunner.java:308`) e
`workDir.resolve("monitor-build")` (`:356`). Todo APK escreve `woven_classes.dex` no mesmo
caminho. Serialmente é inofensivo; **em paralelo, duas JVMs sobrescrevem o DEX tecido uma da
outra e o resultado é um APK assinado com o código de outro app, sem erro nenhum.** Dar a cada
fatia seu próprio `--output-dir` elimina isso.

**Segunda, que exigiu mudar a sequência.** O `monitors/` também é escrito **durante** a
tecelagem: `WrapperEmitter.generate(descriptor, wrapperOutDir, androidIndex)` com
`wrapperOutDir = cfg.monitorSrcDir()` (`BatchRunner.java:195-199`) emite
`mop/MonitorWrappers.java` lá dentro. Logo, cada fatia precisa de uma **cópia real** do
diretório de monitores, nunca de um symlink compartilhado.

### 2.2 Defeito: a geração de monitores não é paralelizável

**Descoberto ao rodar o piloto com 5 fatias concorrentes, cada uma com
`--generate-monitors`.** As cinco produziram conjuntos de monitores **diferentes entre si**:
só uma saiu com `MultiSpec_1RuntimeMonitor.java`; as outras quatro, não.

Causa, no fonte
(`modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:218-222`),
com o comentário já presente no código:

```python
# Critical workaround: JavaMOP's -d option has incomplete behavior
# It moves generated .aj files but leaves .rvm files in source directory
utils.move_files_by_extension(EXTENSION_RVM, self.config.mop_specs_dir, output_dir)
```

O JavaMOP deixa os `.rvm` **no diretório de specs compartilhado**
(`rvsec/rvsec-mop/src/main/resources/jca`) e o gerador os **move** de lá para o seu próprio
`output_dir`. N geradores concorrentes roubam os `.rvm` uns dos outros. O `_execute_rvmonitor`
(`:272`) então morre com `[Error] Target file, .../monitors/*.rvm, doesn't exist!`.

**A falha não aborta.** O `ErrorHandler` captura e o pipeline segue para a instrumentação com
monitores faltando — um lote desacompanhado teria tecido 163 APKs sem monitor e reportado
sucesso.

As 23 specs `.mop` congeladas **não foram danificadas** (`git status` limpo, nenhum `.rvm`
deixado para trás). O piloto corrompido foi descartado; evidência em
`backup/e3-piloto-monitor-race-20260812/`.

**Contorno adotado**, sem tocar em código: (1) gerar monitores **uma vez, sozinho**, com
`--generate-monitors --skip-instrument`; (2) copiar `monitors/` para cada fatia; (3) rodar as
fatias com `--skip-monitors`. Além de evitar o defeito, isso garante por construção que todo o
corpus é tecido com monitores **byte-idênticos** — verificado: o master do piloto e o do lote
dos 163 deram o mesmo `sha256` `fb4b0a95…`, o que também mostra que a geração é determinística
quando roda sozinha. Custo: **73 s**.

O runner do lote carrega um gate duro: se não houver `*RuntimeMonitor.java` no master, aborta
sem lançar nada.

### 2.3 Piloto de 10 — aprovado na metade que ele pode provar

**10/10 com `success: True` e `phase: signed`**, zero falha rebaixada. É o critério do plano
(passo 10) para a combinação inédita `rvsec-core` revertido + weaver reparado, na parte que o
`--skip-execution` alcança. A outra metade (instala, lança, `RVSEC-COV` no logcat, nenhum
`VerifyError`) continua pendente e exige corrida com emulador, como o plano já declarava.

Dois alarmes levantados e **descartados com medição**:

- **Encolhimento dos APKs.** `dankchat` 91,5 → 28,9 MiB e `feeder.play` 129,4 → 67,5 MiB.
  Comparando os zips entrada a entrada: **zero entradas ausentes**, e o conteúdo
  *descomprimido* **cresceu** (92→98 e 151→157 MiB). É recompressão. O que importa para
  instalabilidade foi preservado: `resources.arsc` e todas as `lib/*.so` seguem **STORED**.
- **Dois APKs com `matchesApplied = 0`.** Ver §2.4 — o contador estava sendo lido errado.

**Consumo medido, que dimensionou o lote:** **1,0–2,1 GiB de RSS por JVM** e ~160–400 s por
APK, contra os ~600 s que o plano projetava da campanha de junho. `/tmp` e `TMPDIR` ficaram
vazios: o scratch da instrumentação vai todo para o `--work-dir`, então a armadilha de tmpfs da
§1.3 **não se aplica aqui**.

Lote lançado com **N=8**, 163 APKs em 8 fatias balanceadas por tamanho (round-robin sobre os
APKs ordenados do maior para o menor), 20–21 APKs por fatia.

### 2.4 Correção: `matchesApplied` não conta sítios MOP tecidos

Durante a análise do piloto, três conclusões foram afirmadas e depois **retiradas**. A causa
comum foi inferir de números agregados em vez de abrir o fonte. Ficam registradas porque a
métrica errada reapareceria na medição de superfície MOP dos 163.

**Retirada 1 — "estes APKs têm `reachesTarget = 0`".** Falso, e por bug no script de medição:
`reachability` é uma **lista** de classes e `reachesTarget` é campo **por método**, dentro de
`methods`; o filtro procurava por classe, num dict, e caía para `[]` silenciosamente. Medido
corretamente, **os 10 têm `reachesTarget > 0`** e o funil do `rvsec-dataset` está coerente.

**Retirada 2 — "`directlyReachesTarget` subconta gravemente".** Enquadramento errado. Ele não
deveria bater com sítios tecidos: `isAppClass` (`RvsecAnalysisClient.java:277-280`) exige
`className.startsWith(filterPackage)`, então **toda a seção `reachability` só enxerga o pacote
do app**, enquanto o weaver percorre o DEX inteiro. No `com.nononsenseapps.feeder.play_4025` a
SA vê **6** classes e o weaver **48.872**. São universos diferentes, não métrica quebrada.

**Retirada 3 — "`lstopo` e `giggity` tecem zero sítios e não contribuem para cobertura MOP".**
Falso. `DexWeaver.java` tem dois caminhos de tecelagem:

- **`wrappersSubstituted`** (`:395-403`): `findWrapperReplacement(ins)` **substitui o `invoke`
  do sítio monitorado** por uma chamada a `mop.MonitorWrappers`. É o mecanismo principal de
  instrumentação JCA.
- **`matchesApplied`** (`:553`, mais `:357`): planos de advice aplicados inline (`applyPlan`)
  **mais** as entregas de `staticinitialization(T+)`
  (`staticInitSynthesized + staticInitPrepended`, ver o comentário do record em `:1000-1007`).
  Caminho diferente.

Com o contador certo, `lstopo` e `giggity` têm **12 substituições cada**. O diff de `invoke`
entre APK original e instrumentado confirma instrução por instrução:
`mop.MonitorWrappers.java_security_MessageDigest_{getInstance, digest, update}` injetados nos
dois. **Um APK pode ter `matchesApplied = 0` e estar corretamente instrumentado.**

Ao medir superfície MOP instrumentada do corpus, somar `wrappersSubstituted`, e não comparar
nenhum dos dois com a análise estática sem declarar qual universo cada lado enxerga.

### 2.5 Lote dos 163 — encerrado, **162/163**

**Executado de 2026-08-12 08:07 a 12:00, 3 h 53 min de relógio, `rc=0`.** Oito fatias
concorrentes, ~1,4 min/APK efetivo. O plano orçava **~27 h seriais**: o sharding devolveu a
fase em **1/7 do tempo**, sem alterar uma linha do instrumentador.

| fatia | entregue | | fatia | entregue |
|---|---|---|---|---|
| s0 | 21/21 | | s4 | 20/20 |
| s1 | 21/21 | | s5 | 20/20 |
| s2 | **20/21** | | s6 | 20/20 |
| s3 | 20/20 | | s7 | 20/20 |

**Cardinalidade conferida antes do merge:** 162 presentes, **zero duplicados entre fatias**,
zero inesperados, e a única ausência é o `info.dvkr.screenstream_44000.apk` na s2. Toda outra
fatia entregou exatamente o que sua lista pedia.

**Qualidade dos 162 tecidos:**

| medida | valor |
|---|---|
| `success` + `phase: signed` | **162/163** registros |
| `advices` | **115 em todos** — o mesmo conjunto `jca` validado no piloto |
| `wrappersSubstituted` | mín **12** · p25 **98** · mediana **170** · p75 **299** · máx **3045** · **soma 46.926** |
| APKs com zero sítios tecidos | **0** |
| `constructorInlineApplied` | 6079, em 160 APKs |
| `plansSkipped` (genérico) | **0** |

O piso de 12 é o mesmo observado em `lstopo`/`giggity` no piloto — **nenhum APK do corpus sai
sem instrumentação MOP.**

**Entrega consolidada** em `E3_jca_dexlib2_163/instrumented_apks/`: os 162 APKs (3,8 GB, cópia
real — as oito fatias ficam intactas como proveniência), o `instrument_results.json` fundido
com os **163** registros (162 sucessos **mais o registro da falha**, que não se perde no
merge), e um `SHA256SUMS` com as 162 linhas.

#### Falha única: `info.dvkr.screenstream_44000.apk`

```
phase=uncaught, weaveCounts={}
uncaught error: Exception occurred while writing code_item for method
  Landroidx/core/view/WindowInsetsCompat$Impl20;->setTypeBoundingRectsMap([[Landroid/graphics/Rect;)V
```

**Decisão do pesquisador em 2026-08-12: o corpus fecha com 162.** O APK não entra. O que segue
é o diagnóstico completo, registrado em detalhe porque a causa é estrutural e vai reaparecer.

**Reprocessamento isolado: reproduz.** Rodado sozinho, com o mesmo `monitors_master` e preflight
próprio (`retry1/`), falhou de novo com **mensagem idêntica, mesmo método, mesma fase**, em
347,5 s contra 400,2 s da primeira vez — só variação de tempo. **A falha é determinística, não
transitória.**

##### A causa: o APK bateu no teto de 64K referências de método do formato DEX

Os intermediários do reprocessamento ficaram em disco e permitiram localizar onde a escrita
parou. O laço percorre os DEX em **ordem lexicográfica** e escreveu 21 dos 29 antes de morrer:

- `woven_classes28.dex` existe mas está **inválido**: 8.067.641 bytes com **cabeçalho zerado**
  (`magic` de 8 bytes nulos, `file_size = 0`, `class_defs = 0`). O `DexWriter` escreve o header
  por último e nunca chegou lá.
- Os oito seguintes na ordem (`classes29`, `classes3`–`classes9`) **não chegaram a ser
  tentados** — a exceção abortou o laço inteiro.
- `Landroidx/core/view/WindowInsetsCompat$Impl20;` vive exatamente em `classes28.dex`.

E o `classes28.dex` **original** já chega ao teto:

| | |
|---|---|
| `method_ids` usados | **65.521** |
| limite do formato DEX | **65.536** |
| **folga** | **15 referências** |

A tecelagem precisa injetar referências aos métodos de `mop.MonitorWrappers` (são **84**
wrappers gerados) mais a sonda de cobertura. **Não cabem em 15 slots.** A comparação com os
demais DEX do mesmo APK fecha o argumento: quase todos saíram com `orig + 1` referência, o
`classes16` com `+4`. E o próprio `classes.dex` deste APK está na borda — **65.352 usados, 184
de folga** — e passou raspando, saindo com 65.353.

**Isto não é defeito do weaver nem da tecelagem JCA.** É limitação estrutural do formato: um
APK cujo DEX já está no teto de 64K não admite instrumentação sem ser reparticionado. Explica
todas as observações: o determinismo, a indiferença a mais memória e mais tempo, e a falha
ocorrer no momento da **escrita**, não da análise. Remediar exigiria reparticionar o DEX antes
de tecer — o projeto tem um `MultidexMerger`, mas a falha acontece **antes** dele, na escrita
por DEX.

**Risco residual para o corpus:** 1 em 163 nesta rodada. Qualquer APK com um DEX próximo de
65.536 falha do mesmo modo, e a margem é o que decide — 184 de folga sobreviveu, 15 não. Vale
como verificação barata em corpora futuros: ler `method_ids` (offset 88 do header DEX) de cada
DEX antes de instrumentar.

##### Dois defeitos de diagnóstico que este caso expôs

**1. O relatório do instrumentador não preserva a causa da falha.** O registro completo do APK
é uma linha de mensagem e nada mais:

```json
{ "apkName": "info.dvkr.screenstream_44000.apk", "success": false,
  "message": "uncaught error: Exception occurred while writing code_item for method
              Landroidx/core/view/WindowInsetsCompat$Impl20;->setTypeBoundingRectsMap([[Landroid/graphics/Rect;)V",
  "phase": "uncaught", "weaveCounts": {} }
```

Por construção: `BatchRunner.java:381-382` faz
`catch (RuntimeException ex) { return failed(apk, "uncaught error: " + ex.getMessage(), "uncaught"); }`
— guarda **apenas `ex.getMessage()`**, descartando o *stack trace* e a **causa encadeada**; e
`failed(...)` (`:386-388`) ainda substitui os contadores por `Map.of()`, apagando o que já fora
medido. A exceção vem de `com.android.tools.smali.dexlib2.writer.DexWriter`, que embrulha a
original em `new ExceptionWithContext(ex, "Exception occurred while writing code_item for
method %s", …)`; e `ExceptionWithContext` **não sobrescreve `getMessage()`** (verificado com
`javap`: a classe só expõe `printStackTrace`, `getContext`, `addContext`). Logo a causa real
está em `getCause()`, **que ninguém lê**. `--log-level=TRACE` não ajuda — foi rodado, e a saída
é idêntica, porque o `catch` descarta antes de qualquer log. Todo o diagnóstico acima teve de
ser reconstruído a partir dos intermediários em disco.

**2. O `instr-cli` sai com `exit 0` quando falha.** O próprio registro diz
`success=false, phase=uncaught`, e o processo retorna zero:

```
--- exit 0 after 347.5s ---
instr-cli result: PerApkResult[... success=false, phase=uncaught ...]
```

**O código de saída não é confiável para detectar falha por APK.** Quem interceptou foi a
checagem de existência do arquivo no wrapper Python (`instr-cli reported success but ... was
not created`). Um consumidor que confie no exit code engole a falha em silêncio. O sítio onde o
exit code é definido não foi inspecionado, então fica registrado como observação medida, não
como defeito caracterizado.

#### Dois contadores de aliasing, lidos no fonte

- **`plansSkippedAliasing` — 1832 em 139 dos 162 APKs.** **Não é defeito.** É recusa deliberada e
  documentada (INV-INS-66, `DexWeaver.java:481-512`): advice **AFTER** cujo `invoke` não é
  estático e portanto não pode ser roteado por wrapper — tipicamente chamada virtual ou de
  interface. Emitir o hook inline ali leria registradores de argumento que o `move-result*` já
  sobrescreveu, produzindo **`VerifyError` em todo sítio desses**. O weaver prefere não
  instrumentar a gerar APK quebrado; advice **BEFORE** não é afetado. Vale registrar como
  propriedade do corpus: são eventos AFTER monitorados que ficam sem instrumentação, por
  desenho — **3,9%** ante os 46.926 sítios tecidos.
- **`wrappersAliasedToSubtype` — 16.740 em 27 APKs.** É **ganho, não perda**:
  `DexWeaver.java:222-228` registra o wrapper da classe-pai também para os **subtipos** dela,
  de forma idempotente, capturando chamadas cujo tipo estático é o subtipo. É crescimento da
  tabela de substituição, não contagem de sítios tecidos.
- **Resíduos de um dígito**, todos declarados aqui para que ninguém os descubra depois como
  surpresa: `plansSkippedHighRegister` **3** em 2 APKs; `plansSkippedUnresolvedBinding` **1**
  em 1 APK; `coverageSpillFailed` **1**, em `swati4star.createpdf_110.apk`. Deste último o
  sítio de incremento não foi localizado no fonte, então **a semântica não está
  caracterizada** — é sonda de cobertura, não monitor MOP. Pendente.

---

## 3. O diretório do experimento final

**`RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`**

É **este** o diretório a ser usado no experimento final do Estudo 03. Montado em 2026-08-12 por
decisão do pesquisador, segue a nomenclatura e o layout dos diretórios irmãos
(`APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected163`): tudo plano, `<nome>.apk` e
`<nome>.apk.json` lado a lado — que é como `pre_processor.py:459` procura a análise estática
(`app_path + EXTENSION_STATIC_ANALYSIS`, INV-EXP-16) — mais um `selected162.txt` com a lista.

| conteúdo | origem |
|---|---|
| **162 APKs instrumentados** | `E3_jca_dexlib2_163/instrumented_apks/` (Fase B, §2.5) |
| **30 `.apk.json`** | `SA_RERUN_gh91_wtg/` — a rodada da Fase A, chave `Mneut` + WTG (§1) |
| **132 `.apk.json`** | `rvsec-dataset/static_analysis/` — Phase-7, que já tinham chave do manifesto e WTG e por isso não foram reanalisados |
| `selected162.txt` | a lista, no mesmo formato do `selected163.txt` |

4,3 GB. Conferido: pareamento **1:1** entre `.apk` e `.apk.json`, `selected162.txt` idêntico ao
conjunto de arquivos, e sha256 dos APKs batendo com o `SHA256SUMS` da entrega da Fase B.

A aritmética fecha exatamente: os 163 do funil são **30 + 133**, com os 30 do `30_apks.csv`
contidos nos 163; o APK excluído (`info.dvkr.screenstream_44000.apk`, §2.5) pertence ao grupo
dos 133, então dele saem **132** JSON e o total é **30 + 132 = 162**.

### 3.1 Achado ao montar: 40 dos 162 carregam WTG truncado, não vazio

Aplicando aos 162 a mesma classificação que a Fase A estabeleceu — cruzar `transitions` com o
`timed_out` do `_progress`, porque o sentinela sozinho não distingue os dois casos:

| estado do WTG | quantos |
|---|---|
| povoado | **121** |
| **vazio por truncamento** | **40** |
| genuinamente vazio | 1 |
| indeterminado | 0 |

Dos 40 truncados, **5 são os da Fase A** (§1.1, já conhecidos e declarados no Gate A) e **35
vêm da Phase-7** — descobertos agora, ao aplicar pela primeira vez o predicado `is_complete`
sobre aquelas saídas. Os `_progress` correspondentes estão em `rvsec-dataset-sa/_progress/` e
todos os 35 têm `timed_out: true`; nenhum ficou indeterminado.

**Consequência a considerar antes do experimento:** o braço guiado do E3 consome o artefato MOP
derivado, e esse artefato precisa do WTG (`wtgEdges`). **Um quarto do corpus entregaria grafo
vazio.** O número em si é o que importa aqui — não o mecanismo, que é o mesmo da §1.1 e de
tamanho modesto: os 35 da Phase-7 têm sentinela como qualquer outro, então a distinção entre
"vazio por timeout" e "vazio por natureza" só sai do `_progress`, e por isso ninguém a tinha
feito antes. Fica registrado porque afeta a interpretação de qualquer medida de cobertura
guiada, e porque o número não estava disponível antes desta montagem.

### 3.2 Validação em execução dos 162 — a P7 fecha

**Executada em 2026-08-12, das 14:19 às 15:10, 49 min de relógio, 18,1 s por APK.** Emulador
`RVSec` (API 30, x86_64) subiu **uma vez** pelo comando canônico da imagem Docker
(`scripts/run_emulator.sh`, com `-writable-system -wipe-data`) e caiu uma vez no fim. A regra
PERMANENTE do `CLAUDE.md` continua valendo: o pesquisador autorizou o emulador **para esta
validação e só para ela**, e o texto da regra não foi alterado.

Driver: `scripts/e3_validate_emulator.py` — serial, resume por CSV append-only, um logcat
gzipado por APK. Para cada um: instala com `adb install -r -g`, lança a activity principal,
espera 15 s, captura `adb logcat -d`, classifica, desinstala.

**As quatro metades do critério do piloto (§2.3), todas provadas:**

| | |
|---|---|
| instalou | **162/162** |
| lançou | **162/162** |
| `RVSEC-COV` ≥ 2 no pacote do app | **162/162** |
| `VerifyError` | **0** |

Também zero `FATAL EXCEPTION`, zero `ANR in`, zero `Error type 3` e zero `force-stop`, somados
os 162 logcats.

| linhas `RVSEC-COV` | mín | p25 | mediana | p75 | máx | soma |
|---|---:|---:|---:|---:|---:|---:|
| do código do app | **4** | 116 | 425 | 786 | 3493 | 91.446 |
| totais | 11 | — | 1068 | — | 7255 | 220.027 |

O piso é 4, em `com.smartpack.packagemanager_79`; apenas 2 APKs ficam abaixo de 10. O
`net.gaast.giggity_769`, um dos dois que no piloto apareciam com `matchesApplied = 0` e cujo
mérito só se vê em `wrappersSubstituted` (§2.4), emite 80 linhas, todas do próprio pacote — o
piso de 12 sítios tecidos funciona **em execução**, não só no relatório.

**Isto é validação de boot, não de exploração.** Prova que o APK instrumentado sobe e emite
evento monitorado; não diz nada sobre a instrumentação sobreviver a interação prolongada.

#### O critério mede contra o universo do artefato, e ler isso não pede chave

O critério é `RVSEC-COV` **do código do app**, o mesmo universo que a análise estática usa como
denominador de 100% de cobertura. Esse universo é a `reachability` do `.apk.json`, carregada
como está: o GATOR foi invocado com `-clientParam codePackage=<chave>` e descartou tudo fora
dela **antes de escrever**, então o artefato já chega escopado (INV-ANA-59). Uma linha
`RVSEC-COV` é do app quando sua classe **pertence** a esse conjunto.

**A chave é assunto de produção, e o consumo não a pergunta** (INV-ANA-61). A Fase A precisou
escolhê-la — foi por isso que passou `codePackage=Mneut` (§1) —, mas quem lê o artefato não
pode reabrir a questão: só poderia discordar do produtor. A gh102 mediu o preço de reabri-la.
Como `App.code_package` devolve o `applicationId` declarado desde a gh98 (`553ae54a`), e
`io.keepalive.android.debug` não é prefixo de `io.keepalive.android.MainActivity`, o refiltro do
`StaticAnalysisParser` **zerava 75 dos 162** — as mesmas 75 que carregam sufixo de build.
Nenhuma passaria o critério de admissibilidade, e a `comp162` fecharia em **n=87**. O
`corpus_evidence.md` da change mede o que estava em jogo: **110.692 → 215.430 classes** e
**536.178 → 1.058.685 métodos**.

Esta validação reproduziu o número por outro caminho: somando `sa_classes` dos 162 dá
**215.430**, idêntico ao "depois" da gh102.

**Consequência para quem consumir esta saída:** o `validation.csv` traz `sa_classes` (tamanho do
universo do artefato) e `cov_app` (linhas cuja classe pertence a ele). Nenhuma chave de pacote é
lida em lugar nenhum do driver.

#### Sete denominadores degenerados — a P12 ganha nomes

O universo do artefato tem mediana de 671 classes, mas **7 dos 162 ficam abaixo de 50**, e em
três deles a `reachability` contém **apenas activities**:

| APK | `sa_classes` | `transitions` | o que a `reachability` tem |
|---|---:|---:|---|
| `br.com.colman.petals_3040000` | **1** | 12 | só `br.com.colman.petals.MainActivity` |
| `com.github.livingwithhippos.unchained_60` | 2 | 0 | truncado da Fase A (§1.1) |
| `com.nononsenseapps.feeder.play_4025` | 6 | 47 | as 6 activities, nada mais |
| `com.tananaev.passportreader_22` | 18 | 32 | |
| `com.github.cvzi.screenshottile_148` | 21 | 86 | as 21 activities |
| `org.cry.otp_31` | 23 | 255 | |
| `com.hwloc.lstopo_80283` | 37 | 48 | |

**Só um dos sete se explica pelo que já era conhecido.** O `unchained_60` é truncado da Fase A.
Os outros seis têm `transitions` povoadas, então não é truncamento; e não é sufixo, porque a
gh102 é sobre o consumo e estes números são o que o produtor escreveu.

Isto é exatamente o que a gh102 declara fora de escopo — *"an artefact produced with a wrong key
still yields a wrong denominator"* — e o que a P12 registrava como dúvida. Agora tem nome e
número. O `com.nononsenseapps.feeder.play_4025` já aparecia na §2.4 com "a SA vê 6 classes e o
weaver 48.872", ali enquadrado como universos diferentes; com o denominador exposto, 6 classes
para um app inteiro é outra coisa.

**A autoridade para fechar isso não está no artefato**: é a linha
`Filtered N classes (libraries/generated) using package: <chave>` que o cliente imprime no log
da corrida (`RvsecAnalysisClient.java:105-107`). Para os 30 da Fase A os logs estão em
`SA_RERUN_gh91_wtg/logs/`; para os 132 da Phase-7, em `rvsec-dataset-sa/logs/`. **Não conferido
aqui.**

Nada disto afeta o veredito desta validação — os 7 passam com folga sobre o limiar de 2 —, mas
afeta qualquer proporção de cobertura calculada sobre eles.

#### Como a Fase A escolheu a chave, do lado da produção

Escolher a chave **é** decisão real quando se roda uma análise, e a Fase A teve de tomá-la: o
`rv-static-analysis` não aceita chave arbitrária — a dele é `App(apk).code_package`, o
`applicationId` declarado ou a eleição do `PackageDetector` —, então a gh91 chamou o GATOR
direto para poder passar `-clientParam codePackage=<Mneut>` (`gh91_sa_rerun.py:266,321`), com o
`Mneut` lido verbatim do `30_apks.csv`. Isso vale para os 30; os 132 da Phase-7 vieram como
estavam.

Onde a curadoria deste corpus está escrita, **fora deste repositório**:

| artefato | onde |
|---|---|
| o funil, com `manifest_package` e `detected_package` por APK | `rvsec-dataset/docs/dataset.csv` |
| por que 37 dos 219 saíram (`filtered_pkgdet_scope`) — o `funnel_stage` do `30_apks.csv` | `rvsec-dataset/docs/20260714_package-scope-final-dataset.md` |
| o sufixo de build como artefato do nosso `assembleDebug`, e os arms medidos | `ase-journal/docs/20260730_relatorio_remocao_package_detector.md` |
| a chave congelada dos 30 | `rv-android/30_apks.csv`, coluna `Mneut` |

**Sufixo de build nos 162:** 75 têm, 87 não — `.debug` 61, `.dev` 7, `.beta` 4, `.current` 1,
`.BETA` 1, `.qa.debug` 1. Os quatro últimos estão fora da lista que aparece no `30_apks.csv`
(`.debug`/`.dev`/`.current`). Isso não é problema **desta** leitura, que não usa chave; é o que
determina quais APKs a gh102 recuperou.

#### Armadilha do driver, medida aqui: o `ResolverActivity`

19 dos 162 não expõem `launchable-activity` no `aapt dump badging` porque declaram
`MAIN`/`LAUNCHER` só em `<activity-alias>` — a causa dos 189 logcats perdidos da campanha de
julho (`experimento-20260706/docs/residual/NOCOV_LOGCATS.md`). Perguntar ao PackageManager do
device (`adb shell cmd package resolve-activity --brief -c LAUNCHER <pkg>`) resolve, porque ele
enxerga o alias: 17 APKs lançaram assim, entre eles `org.fossify.notes_13`, cuja activity real
é `…activities.SplashActivity.Green`.

**Mas o resolve-activity tem seu próprio buraco.** Quando o app declara mais de uma activity
LAUNCHER, o PackageManager devolve `android/com.android.internal.app.ResolverActivity` — o
seletor do sistema. Lançar isso abre o chooser, não o app, e o logcat sai com zero cobertura
por motivo nenhum do APK. Aconteceu com `com.gaurav.avnc_51` e `org.wikipedia_50595`, que
foram reportados `nocov` na primeira passada; com o guarda que rejeita componente fora do
pacote alvo e cai para `monkey -p`, os dois passam (1089 e 5239 linhas). **São os únicos dois
não-`pass` da corrida, e ambos eram defeito do driver.**

---

## 4. Pendências abertas

Nenhuma destas foi decidida. Estão aqui para não se perderem entre sessões.

| # | pendência | onde |
|---|---|---|
| P1 | **O Gate A não fecha com os 5 truncados.** Corpus de 25; ou 30 com `wtg_status = truncated` documentado como exceção; ou corrigir o `CFGWorker`. Uma terceira rodada não resolve — o defeito é determinístico. | §1.2, §1.4 |
| P2 | **Corrigir ou não o `CFGWorker` do gator.** Seria try/catch com `finally` devolvendo o worker ao pool, mas diverge do upstream. Sem issue aberta, por decisão de 2026-08-12. | §1.2 |
| P3 | **`ch.rmy.android.http_shortcuts` travou sem a exceção do `ConstantAnalysis`.** Causa não identificada. | §1.2 |
| ~~P4~~ | ~~Destino do `info.dvkr.screenstream_44000.apk`.~~ **Decidido pelo pesquisador em 2026-08-12: o corpus fecha com 162**, com a causa documentada em detalhe. O reprocessamento isolado foi feito e reproduziu a falha; a causa é o teto de 64K referências do DEX, estrutural, não remediável sem reparticionar. | §2.5 |
| P5 | **`instr-cli` retorna `exit 0` com `success=false`.** Sítio do exit code não inspecionado; só a checagem de existência no wrapper Python detecta. | §2.5 |
| P11 | **35 JSON da Phase-7 carregam WTG truncado** e se declaram completos pelo sentinela (§3.1). Um quarto do corpus final entregaria grafo vazio ao braço guiado. | §3.1 |
| P10 | **O relatório do instrumentador não preserva a causa das falhas** (`BatchRunner.java:381-382` descarta trace e `getCause()`; `failed()` zera os contadores). Qualquer `RuntimeException` vira uma linha sem diagnóstico. | §2.5 |
| P6 | **`coverageSpillFailed` sem semântica caracterizada.** 1 ocorrência. | §2.5 |
| ~~P7~~ | ~~Metade do critério do piloto continua não provada.~~ **Feita** em 2026-08-12, 49 min: **162/162** instalam, lançam e emitem ≥ 2 linhas `RVSEC-COV` do pacote do app, com **zero `VerifyError`**, zero `FATAL EXCEPTION`, zero ANR. É validação de boot, não de exploração. | §3.2 |
| P12 | **Sete artefatos têm denominador degenerado, e só um se explica.** `sa_classes` < 50 em 7 dos 162 — `petals` com **1** classe, `feeder.play` com 6, `screenshottile` com 21, e nesses três a `reachability` só tem activities. Um é truncado da Fase A; os outros seis têm `transitions` povoadas, então não é truncamento, e não é o defeito da gh102, que é de consumo. A autoridade é a linha `Filtered N classes … using package:` dos logs da corrida (`RvsecAnalysisClient.java:105-107`), **não conferida**. Afeta qualquer proporção de cobertura sobre esses APKs; não afeta o veredito da §3.2. | §3.2 |
| ~~P8~~ | ~~Merge das 8 fatias.~~ **Feito** em 2026-08-12 12:07: cardinalidade conferida antes de fundir (162, zero duplicados), APKs copiados, `instrument_results.json` fundido com os 163 registros, `SHA256SUMS` gerado. | §2.5 |
| ~~P9~~ | ~~Reescrever a §2.5 com os números finais.~~ **Feito.** | §2.5 |

Duas observações que não são pendências, mas condicionam quem for usar esta entrega:

- **A entrega é de 162 APKs, não 163, e isso é decisão fechada, não pendência.** Qualquer
  contagem, denominador ou proporção calculada sobre o corpus instrumentado tem de declarar
  isso, e não herdar o 163 do `apks_163.txt`. O APK excluído é o
  `info.dvkr.screenstream_44000.apk`, pela causa estrutural descrita na §2.5.
- **O corpus está instrumentado e validado em execução** (§3.2): os 162 instalam, lançam e
  emitem cobertura, sem nenhum `VerifyError`. O que **não** está provado é comportamento sob
  exploração prolongada — a validação é de boot.
- **Ler o artefato não pede chave de pacote** (INV-ANA-59/61, gh102). A `reachability` já vem
  escopada pelo produtor e **é** o denominador. Refiltrá-la por `applicationId` zerava 75 dos
  162 — os que carregam sufixo de build — e teria fechado a `comp162` em n=87. Escolher a chave
  é decisão de quem **roda** a análise, e a Fase A a tomou explicitamente (§1, §3.2).

---

## 5. Índice dos artefatos desta execução

| artefato | caminho |
|---|---|
| Saída da Fase A | `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg/` — 30 JSONs, `REGISTRO.md`, `logs/`, `_progress/`, `_superseded/r1/` |
| Predicado novo + gate | `rv-android/scripts/gh91_campaign.py:126`, `gh91_gate.py` (3.2 forte, 3.7) |
| Testes do predicado | `rv-android/tests/parity/test_gh91_completeness.py` (9 casos) |
| Commit da Fase A | `1679a0e3` |
| Preflight da Fase B | `rv-android/scripts/e3_preflight_instrument.py` |
| Piloto (válido) | `RV_ANDROID_NOVO_DATASET/E3_piloto10/` — `monitors_master/`, `s0..s4/` |
| Piloto corrompido (evidência do defeito da §2.2) | `rv-android/backup/e3-piloto-monitor-race-20260812/` |
| Lote dos 163 — fatias e proveniência | `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/` — `monitors_master/`, `s0..s7/` + `s*.log`/`s*.preflight`, `PROVENIENCIA.md` |
| **Entrega consolidada da Fase B** | `E3_jca_dexlib2_163/instrumented_apks/` — **162 APKs** (3,8 GB), `instrument_results.json` (163 registros), `SHA256SUMS` |
| **► DIRETÓRIO DO EXPERIMENTO FINAL** | `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/` — 162 `.apk` + 162 `.apk.json` co-locados + `selected162.txt` (§3) |
| Driver da validação em emulador | `rv-android/scripts/e3_validate_emulator.py` — serial, resume por CSV, `--reclassify` recomputa o critério offline sobre os logcats gravados |
| **Saída da validação (P7)** | `RV_ANDROID_NOVO_DATASET/E3_VALIDACAO_EMULADOR_162/` — `validation.csv` (162 linhas), `logcats/*.logcat.gz` (evidência integral por APK), `run.log`, `validation_criterio_antigo.csv` |
| Curadoria da chave de pacote (produção) | `rvsec-dataset/docs/dataset.csv` (o funil) · `rvsec-dataset/docs/20260714_package-scope-final-dataset.md` (o corte dos 37) · `ase-journal/docs/20260730_relatorio_remocao_package_detector.md` (o sufixo como artefato do nosso build) |
| O refiltro removido do consumo | `openspec/changes/gh102-artifact-scoped-parse/` — `proposal.md`, `corpus_evidence.md`, `corpus_verification.csv` (162 linhas, antes/depois) |
| Evidência do diagnóstico do DEX 64K | `rv-android/backup/e3-screenstream-dex64k-20260812/` e `E3_jca_dexlib2_163/retry1/` (os `woven_*.dex` que provam o ponto de parada) |
