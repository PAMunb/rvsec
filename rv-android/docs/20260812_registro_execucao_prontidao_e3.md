# Registro de execução — prontidão do Estudo 03 (Fases A e B)

Registro narrativo da execução do plano `20260810_plano_prontidao_estudo03.md`, escrito
durante a corrida de 2026-08-11/12. O plano diz o que fazer; este documento diz o que
aconteceu quando se fez, incluindo o que o plano não previu e as conclusões que tiveram de ser
retiradas.

Ele não substitui nem edita o plano. Quatro defeitos foram medidos aqui, três deles em
código de produção; todos estão descritos com `arquivo:linha`, porque handoff, relatório e
aritmética não são verificação.

**Corte deste documento: 2026-08-12 12:10. As duas fases estão encerradas e suas seções são
definitivas.** A Fase A entregou 25/30 e **reprovou** no Gate A; a Fase B entregou **162/163**
e a entrega está consolidada. O que continua aberto são decisões, não medições, e está na §3.

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

## 3. Pendências abertas

Nenhuma destas foi decidida. Estão aqui para não se perderem entre sessões.

| # | pendência | onde |
|---|---|---|
| P1 | **O Gate A não fecha com os 5 truncados.** Corpus de 25; ou 30 com `wtg_status = truncated` documentado como exceção; ou corrigir o `CFGWorker`. Uma terceira rodada não resolve — o defeito é determinístico. | §1.2, §1.4 |
| P2 | **Corrigir ou não o `CFGWorker` do gator.** Seria try/catch com `finally` devolvendo o worker ao pool, mas diverge do upstream. Sem issue aberta, por decisão de 2026-08-12. | §1.2 |
| P3 | **`ch.rmy.android.http_shortcuts` travou sem a exceção do `ConstantAnalysis`.** Causa não identificada. | §1.2 |
| ~~P4~~ | ~~Destino do `info.dvkr.screenstream_44000.apk`.~~ **Decidido pelo pesquisador em 2026-08-12: o corpus fecha com 162**, com a causa documentada em detalhe. O reprocessamento isolado foi feito e reproduziu a falha; a causa é o teto de 64K referências do DEX, estrutural, não remediável sem reparticionar. | §2.5 |
| P5 | **`instr-cli` retorna `exit 0` com `success=false`.** Sítio do exit code não inspecionado; só a checagem de existência no wrapper Python detecta. | §2.5 |
| P10 | **O relatório do instrumentador não preserva a causa das falhas** (`BatchRunner.java:381-382` descarta trace e `getCause()`; `failed()` zera os contadores). Qualquer `RuntimeException` vira uma linha sem diagnóstico. | §2.5 |
| P6 | **`coverageSpillFailed` sem semântica caracterizada.** 1 ocorrência. | §2.5 |
| P7 | **Metade do critério do piloto continua não provada**: instala, lança, `RVSEC-COV` no logcat, nenhum `VerifyError`. Exige corrida com emulador, que o plano não escreve. | §2.3 |
| ~~P8~~ | ~~Merge das 8 fatias.~~ **Feito** em 2026-08-12 12:07: cardinalidade conferida antes de fundir (162, zero duplicados), APKs copiados, `instrument_results.json` fundido com os 163 registros, `SHA256SUMS` gerado. | §2.5 |
| ~~P9~~ | ~~Reescrever a §2.5 com os números finais.~~ **Feito.** | §2.5 |

Duas observações que não são pendências, mas condicionam quem for usar esta entrega:

- **A entrega é de 162 APKs, não 163, e isso é decisão fechada, não pendência.** Qualquer
  contagem, denominador ou proporção calculada sobre o corpus instrumentado tem de declarar
  isso, e não herdar o 163 do `apks_163.txt`. O APK excluído é o
  `info.dvkr.screenstream_44000.apk`, pela causa estrutural descrita na §2.5.
- **O corpus está instrumentado, não validado em execução.** A metade do critério do piloto que
  exige emulador (P7) continua não provada, e nenhum destes 162 APKs foi instalado ou lançado.

---

## 4. Índice dos artefatos desta execução

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
