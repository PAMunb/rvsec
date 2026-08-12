# Registro de execução — prontidão do Estudo 03 (Fases A e B)

Registro narrativo da execução do plano `20260810_plano_prontidao_estudo03.md`, escrito
durante a corrida de 2026-08-11/12. O plano diz o que fazer; este documento diz o que
aconteceu quando se fez, incluindo o que o plano não previu e as conclusões que tiveram de ser
retiradas.

Ele não substitui nem edita o plano. Quatro defeitos foram medidos aqui, três deles em
código de produção; todos estão descritos com `arquivo:linha`, porque handoff, relatório e
aritmética não são verificação.

**Corte deste documento: 2026-08-12 11:47.** A Fase A está encerrada e suas seções são
definitivas. A Fase B está **em execução** — a §2.5 é parcial e precisa ser reescrita com os
números finais. As pendências abertas estão na §4.

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

### 2.5 Lote dos 163 — parcial em 2026-08-12 11:47

**Estado: 148/163 tecidos, 1 falha, 7 fatias ainda em voo.** Lançado às 08:07 com N=8; ritmo
efetivo de ~1,4 min/APK, contra as ~27 h seriais que o plano orçava. A cauda desacelera à
medida que fatias fecham e o paralelismo cai (a s4 fechou primeiro, 20/20).

*Esta seção é parcial e deve ser reescrita com os números finais quando o lote encerrar.*

**Qualidade dos 148 concluídos com sucesso:**

| medida | valor |
|---|---|
| `success` + `phase: signed` | 148/149 registros |
| `advices` | **115 em todos** — o mesmo conjunto `jca` validado no piloto |
| `wrappersSubstituted` | mín **12** · mediana **168** · máx **3045** · **soma 42.578** |
| APKs com zero sítios tecidos | **0** |
| `plansSkipped` (genérico) | 0 |
| `plansSkippedUnresolvedBinding` | 0 |

O piso de 12 é o mesmo observado em `lstopo`/`giggity` no piloto — nenhum APK do corpus sai
sem instrumentação MOP.

#### Falha única: `info.dvkr.screenstream_44000.apk`

```
phase=uncaught, weaveCounts={}
uncaught error: Exception occurred while writing code_item for method
  Landroidx/core/view/WindowInsetsCompat$Impl20;->setTypeBoundingRectsMap([[Landroid/graphics/Rect;)V
```

O dexlib2 falhou ao **serializar** o `code_item` de um método do `androidx.core` cujo parâmetro
é `[[Rect` (array de arrays). Morreu após 400,2 s, antes de produzir contador algum — não é
falha da tecelagem JCA, é o escritor de DEX. É 1 em 149 até aqui; se outros APKs exibirem a
mesma exceção do `WindowInsetsCompat`, deixa de ser caso isolado e vira padrão a tratar.

**Achado colateral, mais grave que a falha em si: o `instr-cli` saiu com `exit 0`.** O próprio
registro do CLI diz `success=false, phase=uncaught`, e ainda assim o processo retornou zero:

```
--- exit 0 after 400.2s ---
instr-cli result: PerApkResult[... success=false, phase=uncaught ...]
```

**O código de saída do `instr-cli` não é confiável para detectar falha por APK.** Quem
interceptou foi a checagem de existência do arquivo no wrapper Python (`instr-cli reported
success but ... was not created`). Um consumidor que confie no exit code engole a falha em
silêncio. O sítio onde o exit code é definido não foi inspecionado, então isto fica registrado
como observação medida, não como defeito caracterizado.

#### Dois contadores de aliasing, lidos no fonte

- **`plansSkippedAliasing` — 1609 em 127 APKs.** **Não é defeito.** É recusa deliberada e
  documentada (INV-INS-66, `DexWeaver.java:481-512`): advice **AFTER** cujo `invoke` não é
  estático e portanto não pode ser roteado por wrapper — tipicamente chamada virtual ou de
  interface. Emitir o hook inline ali leria registradores de argumento que o `move-result*` já
  sobrescreveu, produzindo **`VerifyError` em todo sítio desses**. O weaver prefere não
  instrumentar a gerar APK quebrado; advice **BEFORE** não é afetado. Vale registrar como
  propriedade do corpus: são eventos AFTER monitorados que ficam sem instrumentação, por
  desenho — cerca de 3,8% ante os 42.578 sítios tecidos.
- **`wrappersAliasedToSubtype` — 14.444 em 24 APKs.** É **ganho, não perda**:
  `DexWeaver.java:222-228` registra o wrapper da classe-pai também para os **subtipos** dela,
  de forma idempotente, capturando chamadas cujo tipo estático é o subtipo. É crescimento da
  tabela de substituição, não contagem de sítios tecidos.
- `coverageSpillFailed` — **1 ocorrência**, em `swati4star.createpdf_110.apk`. O sítio de
  incremento não foi localizado no fonte, então **a semântica não está caracterizada**. É sonda
  de cobertura, não monitor MOP. Pendente.

---

## 3. Pendências abertas

Nenhuma destas foi decidida. Estão aqui para não se perderem entre sessões.

| # | pendência | onde |
|---|---|---|
| P1 | **O Gate A não fecha com os 5 truncados.** Corpus de 25; ou 30 com `wtg_status = truncated` documentado como exceção; ou corrigir o `CFGWorker`. Uma terceira rodada não resolve — o defeito é determinístico. | §1.2, §1.4 |
| P2 | **Corrigir ou não o `CFGWorker` do gator.** Seria try/catch com `finally` devolvendo o worker ao pool, mas diverge do upstream. Sem issue aberta, por decisão de 2026-08-12. | §1.2 |
| P3 | **`ch.rmy.android.http_shortcuts` travou sem a exceção do `ConstantAnalysis`.** Causa não identificada. | §1.2 |
| P4 | **Destino do `info.dvkr.screenstream_44000.apk`**: reprocessar isolado, ou declarar 162 e documentar a exclusão. | §2.5 |
| P5 | **`instr-cli` retorna `exit 0` com `success=false`.** Sítio do exit code não inspecionado; só a checagem de existência no wrapper Python detecta. | §2.5 |
| P6 | **`coverageSpillFailed` sem semântica caracterizada.** 1 ocorrência. | §2.5 |
| P7 | **Metade do critério do piloto continua não provada**: instala, lança, `RVSEC-COV` no logcat, nenhum `VerifyError`. Exige corrida com emulador, que o plano não escreve. | §2.3 |
| P8 | **Merge das 8 fatias** num `instrumented_apks/` único com `instrument_results.json` fundido, conferindo a cardinalidade antes de fundir. | §2.5 |
| P9 | **Reescrever a §2.5 com os números finais** quando o lote encerrar. | §2.5 |

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
| Lote dos 163 | `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/` — `monitors_master/`, `s0..s7/`, `PROVENIENCIA.md` |
