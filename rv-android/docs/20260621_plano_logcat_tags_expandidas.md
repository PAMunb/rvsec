# Plano — Expansão de tags do logcat (crashes, VerifyError, ANR)

**Data:** 2026-06-21
**Branch:** `modules`
**Status:** Planejamento (Fase 0 / ideação) — **nada implementado**
**Escopo:** captura + parsing de eventos diagnósticos de execução do app no logcat, além das 2 tags atuais.

---

## 1. Objetivo

Hoje o pipeline trata **2 tags** do logcat (`RVSEC`, `RVSEC-COV`). Queremos avaliar a viabilidade — e mapear
o impacto no parser — de tratar **outras tags** para capturar eventos/erros de execução do app: **crashes**
(exceções não tratadas), **VerifyError de carga** e **ANR/morte de processo**. O fim é entender *o que
aconteceu com o app* durante a exploração, hoje invisível.

Este documento é a saída da investigação. As decisões de escopo já foram tomadas (§4). A implementação segue
o workflow OpenSpec (§8) numa etapa posterior.

---

## 2. Estado atual (confirmado no código)

### 2.1. As 2 tags
`modules/rv-android-core/src/rv_android_core/util/logging/constants.py:21-22`
```python
TAG_RVSEC     = "RVSEC"       # violação de propriedade  -> RvErrorLog
TAG_RVSEC_COV = "RVSEC-COV"   # chamada de método (cobertura) -> RvCoverageLog
```

### 2.2. O comando de captura — o ponto que destrava tudo
`modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py:176-187`
```
adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V
```
O flag **`-s` é um filtro silenciador**: tudo que não for `RVSEC`/`RVSEC-COV` é descartado **na origem**.
**Conclusão:** crashes/exceções/VerifyError **não chegam ao arquivo de logcat hoje** — não é limitação do
parser, é da captura. Qualquer expansão **começa** por alterar este comando (`default_tags` em
`logcat_manager.py:61-64`).

### 2.3. O parser é estritamente linha-a-linha e sem estado
`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py:83`
```python
def parse_logcat_line(line) -> Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]:
    # 1 linha -> no máximo 1 registro; dispatch por igualdade de tag (==)
```
- Regex threadtime (`logcat_parser.py:130`): `MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message`.
- `CoverageTracker` (rv-coverage) chama isso por linha numa **thread de fundo** durante a execução.
- `CoverageAnalyzer`/`parse_logcat_file` reprocessa offline.
- A tupla `(RvErrorLog, RvCoverageLog)` é a única forma de saída — **não escala** para N tipos de evento.

### 2.4. Fluxo de dados
captura (`logcat_manager`) → arquivo `.logcat` → `parse_logcat_line` (tracker em tempo real / analyzer offline)
→ `LogcatRepository` (rv-android-core `domain/coverage.py`) → CSVs (`result_processor.py`: `coverage.csv`,
`errors.csv`).

### 2.5. Tratamento de crash hoje: **inexistente**
Nenhum código toca `VerifyError`, `FATAL`, `AndroidRuntime`, ANR. Só há tratamento de erro de I/O e de
parsing malformado (warning + None).

---

## 3. Evidência empírica — corrida de hoje (`docs/20260619_comparacao_aperv.md`)

Varredura nos **2.028 logcats** de `data/results/cmp_0*/` (4 braços × 169 APKs × 3 reps, 300 s):

| Observação | Resultado |
|---|---|
| Tags distintas presentes | **somente `RVSEC` e `RVSEC-COV`** (amostra: 12.755 COV + 5 RVSEC num arquivo) |
| `AndroidRuntime` "encontrado" | **21 arquivos — falso positivo**: substring de assinatura (`boolean isAndroidRuntime()`) |
| `FATAL EXCEPTION` / `VerifyError` / `ANR in` / `System.err` | **0 arquivos** (filtrados pelo `-s`) |
| `--------- beginning of crash` | **178/2.028 (8,8%)** — buffer de crash **aberto**, mas conteúdo filtrado: linhas seguintes são RVSEC-COV |
| Linhas que não casam o regex | apenas separadores `--------- beginning of {main,system,kernel,crash}` → parser já as ignora (None) |

**Leitura:** o separador `beginning of crash` em ~9% dos runs indica que **atividade de crash existe e está
sendo descartada hoje**. Estamos cegos a ela — e ela é um *confounder* silencioso de cobertura (um APK
instrumentado que morre cedo aparece como "ferramenta de baixa cobertura").

> Caveat metodológico: o separador sozinho não prova um crash *deste* app (o buffer de crash é do device).
> Mas é sinal suficiente de que vale capturar o conteúdo para desambiguar.

---

## 4. Decisões tomadas (2026-06-21)

| Eixo | Decisão |
|------|---------|
| **Escopo de tags** | **Crashes** (`AndroidRuntime:E`) + **VerifyError load-time** (`art`/`dalvikvm:E`) + **ANR/morte de processo** (`ActivityManager:W`). **Fora de escopo:** `System.err:W` (verboso, baixo valor). |
| **Captura adb** | Alterar o filtro `-s` **sim, mas opt-in/flag**, com default **preservando** o comportamento atual; validar que RVSEC/COV não muda. |
| **Saída** | **Novo CSV dedicado** (`app_events.csv` / `crashes.csv`); **não** mexer no schema de `coverage.csv`/`errors.csv` (consumidos por scripts de consolidação e Wilcoxon). |

---

## 5. Tags-alvo e o que capturam

| Tag (prioridade adb) | Captura | Multi-linha | Valor |
|---|---|---|---|
| `AndroidRuntime:E` | `FATAL EXCEPTION` — exceção não tratada = crash; inclui `Caused by: java.lang.VerifyError` (runtime) | **Sim** (stack trace) | Alto — explica morte do app |
| `art:E` (+ `dalvikvm:E` legado) | rejeição de verificação de classe na carga: `Verification error`, `Rejecting class ...` (VerifyError load-time) | às vezes | Alto — substitui o grep offline da comparação **dexlib2×ajc** |
| `ActivityManager:W` | `ANR in <pkg>`, `Force finishing activity`, `Process ... has died` | parcial | Médio — explica stalls / baixa cobertura |

**Por que VerifyError aparece em 2 lugares:**
- **Load-time:** ART rejeita a classe → tag `art`/`dalvikvm`.
- **Run-time:** `java.lang.VerifyError` lançado → `FATAL EXCEPTION` sob `AndroidRuntime` (`Caused by:`).
Ambos relevantes para validar a corretude da instrumentação (critérios de sucesso dos experimentos contam
VerifyError = 0).

---

## 6. Impacto no parser (ordenado por dificuldade)

### 6.1. Registros multi-linha — **a maior mudança**
RVSEC/COV são de 1 linha. Um crash é **1 header + N linhas** de stack trace (`\tat ...`, `Caused by:`,
`... N more`), **todas com a mesma tag** `AndroidRuntime` e **mesmo pid/tid**. Cada frame casa o regex
threadtime (tag=`AndroidRuntime`, message=`\tat ...`) — então não é problema de regex, é de **montagem**.
O parser sem estado atual emite 1 registro por linha e **não consegue agregar** o trace.

**Implicação:** é preciso um **acumulador com estado** que agrupe linhas consecutivas da mesma `(tag, pid,
tid)` num único evento, fechando o registro quando a tag/pid muda ou surge uma linha não-continuação. Isso
**quebra o contrato de função pura** de `parse_logcat_line`.

### 6.2. Assinatura do dispatcher — **DECIDIDO: opção B**
`(Optional[RvErrorLog], Optional[RvCoverageLog])` não comporta um 3º tipo sem virar tupla-monstro (anti-P1).
Decisão: **(B)** manter `parse_logcat_line` intacta (2-tupla) e introduzir um **objeto-parser com estado**
separado (`DiagnosticEventParser`) para os eventos diagnósticos — que precisam de estado de qualquer forma.

**Por quê B** (blast-radius medido — §11.1): a opção A (refatorar para `RvLogEvent` único) tocaria **6
call-sites de produção + 7 asserts de teste** e quebraria a API pública; a opção B é **aditiva** (0 mudança
no caminho quente RVSEC/COV, 0 teste reescrito), e o caminho RVSEC/COV (1 linha → 1 registro, imutável) é
ortogonal ao diagnóstico (multi-linha, com estado). Risco baixo onde importa.

> ⚠️ Rejeitar explicitamente a sugestão de transformar `parse_logcat_line` numa 3-tupla
> `(error, coverage, diagnostic)` — isso é a opção A disfarçada e contraria a decisão B.

**Onde o estado vive:** o `CoverageTracker._track_coverage` (`tracker.py:281-325`) lê o arquivo por linha
(`readlines()` + tail loop, thread daemon) e `_process_line` (`tracker.py:361-425`) é **sem estado** hoje. O
novo parser **não** entra ali como estado solto; é um objeto `DiagnosticEventParser` com `feed_line(line) ->
Optional[RvDiagnosticEvent]` (buffer interno por `(tag,pid,tid)`) + `flush()` no fim. Tanto o tracker quanto
`parse_logcat_file` (`logcat_parser.py:71`) instanciam um e alimentam cada linha; ao fechar um evento,
chamam `repository.register_diagnostic_event(...)`. Assim a **reconstrução no resume**
(`_reconstruct_repository_from_logcat` → `parse_logcat_file`, §8.1 gh58) também recupera os diagnósticos.

### 6.3. Novos modelos de domínio — **DECIDIDO: `RvDiagnosticEvent` unificado**
Um único modelo em `rv-android-core/domain/log.py`, seguindo o padrão de `RvErrorLog`/`RvCoverageLog`
(`@validated_model`, `to_dict`/`from_dict`, `computed_field unique_msg`):

```python
@validated_model(["category", "class_full_name", "method", "message"])
class RvDiagnosticEvent(BaseValidatedModel):
    category: str            # "crash" | "verify_error" | "anr"
    class_full_name: str     # exception class OU classe rejeitada OU pacote (ANR)
    method: str              # 1º frame do app, quando houver
    message: str             # 1ª linha legível (FATAL EXCEPTION / Rejecting class / ANR in)
    source: str = ""         # file:line do 1º frame do app, quando extraível
    process: str = ""        # pacote do app afetado (do "Process:"/"ANR in") — atribuição §6.8
    pid: str = ""
    tid: str = ""
    fatal: bool = False
    stack_head: str = ""     # 1º frame (resumo p/ CSV)
    n_frames: int = 0        # nº de frames no trace
    original_msg: str = ""   # bloco multi-linha completo preservado
    time_occurred: datetime = Field(default_factory=datetime.now)
    time_since_task_start: int = 0
```
Modelo único > 3 modelos: adicionar uma categoria é um valor de enum, não uma classe nova (P1).

### 6.4. Repositório (`LogcatRepository`) — isolamento **confirmado no código**
`calculate_metrics()` (`coverage.py:578-650`) itera **só** `self.classes`; `total_errors`/`unique_errors`
contam **só** `self.errors`/`self.unique_errors`; `get_method_calls` itera **só** `self.classes`. Uma coleção
nova `self.diagnostic_events: List[RvDiagnosticEvent]` + `register_diagnostic_event()` + `get_diagnostic_events()`
fica **automaticamente isolada** — nenhum cálculo de cobertura/MOP nem `total_errors` a enxerga.

### 6.5. Saída CSV (`result_processor.py`) — **DECIDIDO: stack_head no CSV, trace completo no logcat**
Novo writer `app_events.csv` no mesmo padrão de `_generate_errors_csv` (`result_processor.py:467-502`).
Colunas: `apk, rep, timeout, tool, time, category, exception_class, method, source, message, process, pid,
fatal, n_frames, stack_head`. **O trace multi-linha completo NÃO vai para o CSV** (escaping/volume) — fica no
`.logcat` (fonte da verdade) e em `original_msg` na reconstrução. **Schemas de `coverage.csv`/`errors.csv`
intactos.**

### 6.6. Performance / volume
Mais tags = mais linhas na thread do tracker durante execução. Crashes são raros/burst; ANR é esporádico;
`art:E` pode ser ruidoso em alguns apps. **Evitar catch-all `*:E`** (volume e perda de foco). Filtro por tags
nomeadas mantém o custo controlado.

### 6.7. Robustez e compat retroativa
- Separadores `--------- beginning of crash` continuam não casando o regex → ignorados (ok).
- **Logcats antigos** só têm RVSEC* → continuam parseando idêntico; eventos de crash só existirão em **runs
  novos** (a captura mudou). Reprocessar dados antigos **não** recupera crashes (não foram capturados).

### 6.8. Atribuição ao app-alvo — **DECIDIDO: pelo bloco, não por PID vivo**
Investigado (§11.3): o `LogcatComponent` **não** tem `app.package_name` no momento de iniciar a captura (o
`task.app` é setado depois), e `adb logcat --pid=<pid>` não é prático mid-stream (a captura já está rodando).
**Decisão: não plumbar PID vivo.** Atribuir o evento ao app pela própria carga do bloco:
- Crash `AndroidRuntime`: a 2ª linha traz `Process: <pacote>, PID: <n>` → extrair `process`/`pid` daí.
- ANR `ActivityManager`: `ANR in <pacote>` → extrair `process`.
- VerifyError `art`/`dalvikvm`: extrair a classe rejeitada; correlação com o app por prefixo de pacote.

Ruído de outros processos do device fica **filtrável offline** por `process` (match com o pacote do APK da
task). Captura em prioridade de erro (`:E`/`:W`) já mantém o volume baixo sem precisar do `--pid`.

---

## 7. Arquitetura proposta (decisões fechadas)

1. **Captura opt-in** via flag `RV_LOGCAT_DIAGNOSTICS` (default `false` = comportamento atual). Quando `true`,
   acrescenta `AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` ao filtro existente. Plumbing (§11.3):
   `constants.py` (`ENV_LOGCAT_DIAGNOSTICS`) → Click `@option(envvar=...)` em `rv-experiment/__main__.py` →
   `ExperimentConfig` → `PlatformConfig` → `LogcatComponent.__init__(enable_diagnostics)` →
   `start_capture(tags=default_tags + diagnostic_tags)`. **O parâmetro `tags` já existe** em
   `LogcatManager.start_capture` (`logcat_manager.py:129`) — hoje o `LogcatComponent` simplesmente não o passa.
   Gate de regressão: com a flag `false`, o comando adb e os logcats têm de ser **byte-idênticos** ao baseline.
2. **`DiagnosticEventParser` com estado** (opção B, §6.2): `feed_line()`/`flush()`, buffer por `(tag,pid,tid)`,
   alimentado pelo tracker e por `parse_logcat_file`. `parse_logcat_line` (RVSEC/COV) **inalterada**.
3. **`RvDiagnosticEvent`** em `domain/log.py` + `diagnostic_events`/`register_diagnostic_event`/
   `get_diagnostic_events` no `LogcatRepository` (§6.3/§6.4), isolados das métricas.
4. **Writer `app_events.csv`** novo no `result_processor` (§6.5); CSVs existentes inalterados.
5. **Tags emitidas pelo app são fixas** (`Log.v("RVSEC", ...)` em `rvsec-logger-logcat/.../ErrorCollector.java`)
   — só a captura no device muda; nada no APK instrumentado.
6. **Testes**: fixtures de logcat com crash/VerifyError/ANR (formatos canônicos §11.4, mais reais de um run de
   validação com a flag ligada); golden tests garantindo RVSEC/COV idêntico ao baseline.

---

## 8. Próximos passos (workflow OpenSpec)

Multi-módulo (`rv-android-core` captura+modelos, `rv-coverage` parser, `rv-platform` result_processor) **com
decisões de design** (captura opt-in, parser com estado) → **Full SDD** (`rv-sdd`). O blast-radius e as
decisões já estão fechados (§6, §12), então o `/opsx:explore` é confirmatório, não exploratório.

1. `/opsx:explore` (confirmar os call-sites de §11.1) + `/rv-impact-analyzer`.
2. `/opsx:new` → proposal + delta spec no domínio **analysis** (`openspec/specs/analysis/spec.md`,
   FR04-FR06/FR12-FR13) e tocando **core** (modelos/captura).
3. `/opsx:continue` design + `/rv-doc-adr` (registrar a decisão B: parser com estado separado vs união) +
   `/rv-risk` (mudança de captura afeta experimentos).
4. `/opsx:apply` → `/rv-verify` → `/opsx:verify` → `/opsx:archive`.

**Ordem de implementação sugerida** (cada passo verificável isolado):
1. `RvDiagnosticEvent` + coleção/métodos no `LogcatRepository` (puro core, testável sem device).
2. `DiagnosticEventParser` (`feed_line`/`flush`) + fixtures dos formatos canônicos (§11.4).
3. Integração no `parse_logcat_file` + `CoverageTracker` (gate: RVSEC/COV golden idêntico).
4. Writer `app_events.csv` no `result_processor` (+ sobreviver à reconstrução de resume).
5. Flag `RV_LOGCAT_DIAGNOSTICS` ponta-a-ponta (gate: flag `false` ⇒ adb byte-idêntico).
6. Run de validação curto com a flag ligada num APK que crasha (ver §3: 8,8% abrem buffer de crash).

### 8.1. Critérios de validação/aceitação (gates)

Formato WHEN/THEN com valores concretos. Cada critério é um gate de merge; agrupados por objetivo.

**G1 — Não-regressão / não-interferência (o gate mais forte; protege os baselines)**
- **AC1.1** WHEN a flag `RV_LOGCAT_DIAGNOSTICS` está `false` THEN o comando `adb logcat` emitido é
  **byte-idêntico** ao baseline (`-v threadtime -s RVSEC:V RVSEC-COV:V`) AND o `.logcat` resultante é idêntico.
- **AC1.2** WHEN re-parseamos os 2.028 logcats de `data/results/cmp_0*/` (pré-feature) THEN `coverage.csv`,
  `errors.csv` e `summary.csv` saem **idênticos** ao baseline (cobertura/MOP/`total_errors`/`unique_errors`
  inalterados) — diff zero.
- **AC1.3** THEN a assinatura de `parse_logcat_line` permanece `Tuple[Optional[RvErrorLog],
  Optional[RvCoverageLog]]` (D1) AND os 7 asserts de teste existentes (§11.1) passam **sem reescrita**.
- **AC1.4** THEN `/rv-verify` (testes + lint + type) passa em `rv-android-core`, `rv-coverage`, `rv-platform`.

**G2 — Captura opt-in (D5, D7)**
- **AC2.1** WHEN `RV_LOGCAT_DIAGNOSTICS=true` THEN o comando adb contém `AndroidRuntime:E art:E dalvikvm:E
  ActivityManager:W` **além** de `RVSEC:V RVSEC-COV:V` (RVSEC/COV preservados).
- **AC2.2** WHEN a var de ambiente é setada no nível do experimento THEN ela chega ao `LogcatManager`
  (ponta-a-ponta: `constants.py` → Click `envvar=` → `ExperimentConfig` → `PlatformConfig` →
  `LogcatComponent` → `start_capture(tags=...)`), comprovado por teste de integração.

**G3 — Parsing correto e multi-linha (D1, D2)**
- **AC3.1** WHEN o logcat tem um bloco `AndroidRuntime` FATAL (header + N× `\tat` + `Caused by:` + `... N more`)
  THEN o parser emite **1** `RvDiagnosticEvent` `category="crash"` com `exception_class`, `method` (1º frame do
  app), `source` (`File:linha`), `fatal=true`, `n_frames=N`, `stack_head` = 1º frame, `original_msg` = bloco
  completo.
- **AC3.2** WHEN aparece `art`/`dalvikvm` com `Rejecting class`/`Verification error` THEN emite 1 evento
  `category="verify_error"` com a classe rejeitada.
- **AC3.3** WHEN aparece `ActivityManager: ANR in <pkg>` (ou `... has died`) THEN emite 1 evento
  `category="anr"` com `process=<pkg>`.
- **AC3.4** WHEN a linha seguinte muda `(tag,pid,tid)` ou não é continuação THEN o evento anterior **fecha**;
  AND no EOF o `flush()` emite o último evento bufferizado (nada se perde).
- **AC3.5** WHEN há `RVSEC-COV: <... boolean isAndroidRuntime()>` THEN **nenhum** evento de crash é gerado
  (casa o **campo tag**, não substring) — regressão do falso positivo de §3.
- **AC3.6** WHEN a linha é separador (`--------- beginning of crash`) ou não casa o regex threadtime THEN é
  ignorada sem erro.

**G4 — Isolamento de métricas (D4)**
- **AC4.1** GIVEN um logcat com violações RVSEC **e** crashes WHEN `calculate_metrics()` roda THEN
  `total_errors`/`unique_errors` contam **só** as violações RVSEC AND cobertura método/MOP é idêntica à de um
  logcat sem os crashes (eventos diagnósticos não entram em nenhuma métrica).

**G5 — Saída CSV (D3) e resume (gh58)**
- **AC5.1** WHEN há eventos diagnósticos THEN `app_events.csv` é gerado com header
  `apk,rep,timeout,tool,time,category,exception_class,method,source,message,process,pid,fatal,n_frames,stack_head`
  AND 1 linha por evento AND o trace completo **não** está no CSV (só `stack_head`).
- **AC5.2** THEN os headers de `coverage.csv`/`errors.csv` são **byte-idênticos** ao baseline (schema intacto).
- **AC5.3** WHEN uma task é reconstruída no resume (`_reconstruct_repository_from_logcat` → `parse_logcat_file`)
  THEN os eventos diagnósticos do `.logcat` reaparecem em `app_events.csv` (sobrevivem ao resume).

**G6 — Atribuição ao app (D6)**
- **AC6.1** WHEN um crash traz `Process: <pkg>, PID: <n>` (ou ANR `in <pkg>`) THEN `process`/`pid` do evento são
  preenchidos a partir do bloco AND um filtro offline por `process == <pacote do APK da task>` separa os eventos
  do app dos de outros processos.

**G7 — Validação ponta-a-ponta (run real, §8 passo 6)**

> **Fixture canônico = `cryptoapp` (bug intencional no option menu).** `examples/cryptoapp/app/src/main/java/
> br/unb/cic/cryptoapp/MainActivity.java:50` — o listener do item de menu *Message Digest* faz
> `new Intent(null, MessageDigestActivity.class)` (Context `null`) → `ComponentName.<init>` chama
> `null.getPackageName()` → **`NullPointerException`** → **`FATAL EXCEPTION: main`** sob `AndroidRuntime:E`,
> no clique do item. Crash determinístico, atribuível (`Process: br.unb.cic.cryptoapp`), reachável abrindo o
> overflow menu e tocando *Message Digest*. Hoje (filtro `-s RVSEC*`) esse crash é descartado — o app só
> "some" e a cobertura cai sem registro do porquê (caso real do confounder de §3).

- **AC7.1** WHEN rodamos um run curto com `RV_LOGCAT_DIAGNOSTICS=true` no `cryptoapp` e o explorador toca o
  item de menu *Message Digest* THEN `app_events.csv` contém ≥1 evento `category="crash"`,
  `exception_class="java.lang.NullPointerException"`, `process="br.unb.cic.cryptoapp"`, `fatal=true`,
  `stack_head` apontando `MainActivity$1.onMenuItemClick(MainActivity.java:50)` AND o `.logcat` contém o bloco
  `AndroidRuntime` bruto correspondente.
- **AC7.2** THEN a cobertura/MOP dos braços que **não** crasham é estatisticamente indistinguível de um run com
  a flag `false` (confirma que a captura aditiva não perturba a métrica primária — base da decisão D9).
- **AC7.3** (diagnóstico, não-bloqueante) THEN medir se `art`/`dalvikvm` emitiram em `W` em vez de `E`; se sim,
  registrar para incluir `art:W` (ver Riscos §9).

**Definição de pronto (DoD):** G1–G6 verdes em CI (`/rv-verify` + `/opsx:verify`) + G7 executado e relatado.
G1 é **bloqueante absoluto** — qualquer desvio de não-interferência reprova o merge.

---

## 9. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| **Mudança de captura afeta experimentos** (memória `feedback_never_change_experiment_config`) | baseline de futuras corridas muda | opt-in/flag, default = atual, gate de regressão RVSEC/COV idêntico |
| **Volume** em runs longos com tags ruidosas | arquivo grande, thread do tracker mais pesada | tags nomeadas (sem `*:E`); medir overhead num run de validação |
| **Estado no parser** introduz bug no caminho quente RVSEC/COV | corrompe cobertura/violações | opção B: `parse_logcat_line` intacta; parser diagnóstico separado; golden test RVSEC/COV |
| **Poluir métricas** com eventos diagnósticos | cobertura/MOP/`total_errors` inflados | coleção separada; isolamento **confirmado** (§6.4) — métricas só leem `self.classes`/`self.errors` |
| **Falso positivo de tag** (substring tipo `isAndroidRuntime`) | contagem errada | casar **campo tag** do threadtime, não substring na linha (visto na evidência §3) |
| **`art`/`dalvikvm` emitem em W além de E** | VerifyError load-time perdido se só `:E` | validar prioridade no run de validação; ajustar para `art:W` se preciso |

---

## 10. Decisões fechadas (2026-06-21)

| # | Questão | Decisão | Base |
|---|---------|---------|------|
| D1 | Dispatcher: união vs parser separado | **Parser separado com estado (opção B)** — `parse_logcat_line` intacta | blast-radius §11.1 (6+7 call-sites em A vs 0 em B) |
| D2 | Modelo de domínio | **`RvDiagnosticEvent` único** com `category` enum | §6.3; P1 (enum > 3 classes) |
| D3 | Granularidade do CSV | **`stack_head` no `app_events.csv`; trace completo só no `.logcat`** | §6.5; evita escaping/volume |
| D4 | Isolamento de métricas | **Coleção separada `diagnostic_events`** — não toca cobertura/MOP/`total_errors` | confirmado §6.4/§11.2 |
| D5 | Flag de captura | **`RV_LOGCAT_DIAGNOSTICS`** (default `false`), plumbing via Click `envvar=` | §11.3 |
| D6 | Atribuição ao app | **Pelo bloco (`Process:`/`ANR in`), não por `--pid` vivo** | §11.3 (componente não tem pacote no start) |
| D7 | Lista de tags | **`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W`** | escopo §4 + prior art §11.5 |
| D8 | Tombstones nativos (`DEBUG:F`/`libc:F`, SIGSEGV) | **Fora do v1** (nem captura nem parser). Reabrir só com gatilho de dados | conceitual + evidência de ABI §11.6 |
| D9 | Flag no compose dos experimentos | **Default OFF no baseline; opt-in por campanha** (env explícito, não na âncora compartilhada) | memória `feedback_never_change_experiment_config` + §11.7 |

### D8 — por que tombstones nativos ficam fora do v1
1. **Conceitual (o mais forte):** a instrumentação que validamos é **DEX/Java** (dexlib2/ajc); ela **não toca
   `.so` nativo**. Um SIGSEGV nativo é bug pré-existente do app, **ortogonal** às nossas perguntas (VerifyError,
   corretude de instrumentação, crash como confounder de cobertura). Crash induzido por instrumentação é
   sempre Java (`VerifyError`/exceção), nunca tombstone nativo.
2. **Evidência de ABI (§11.6):** dos 169 APKs, **0** são `arm64-v8a`-only — não há o cenário de tradução ARM
   com risco elevado de SIGSEGV. 144/169 têm libs nativas **mas com `x86_64`** (execução nativa, sem tradução);
   25 não têm nativo (SIGSEGV impossível).
3. **Custo/payoff:** tombstone tem formato próprio (`*** ***`, `signal 11`, `backtrace: #00 pc <addr> <lib>`),
   exigiria um ramo de parser distinto do stack Java — payoff baixo no v1.
4. **Gatilho de reabertura (data-driven, não palpite):** no run de validação (§8 passo 6), se houver APK com
   **cobertura colapsando + `--------- beginning of crash` + sem FATAL Java capturado**, é provável crash
   nativo → aí sim adicionar `libc:F DEBUG:F` (captura) + ramo tombstone (parser). Adição barata sobre o
   framework já pronto: +1 valor de `category` (`native_crash`) e um parser de backtrace.

### D9 — por que default OFF, opt-in por campanha
- Duas famílias de experimento: **(A) validação de instrumentação** (dexlib2×ajc — onde VerifyError/crash *é*
  o ponto; `check_crashes.py` existe exatamente p/ isso) e **(B) comparação de ferramentas** (APE/APE-RV
  cobertura/MOP, como a corrida de hoje — crash é confounder a medir, mas comparabilidade do baseline importa).
- Memória `feedback_never_change_experiment_config`: **nunca** mudar baseline sem autorização. Com o gate
  "byte-idêntico quando `false`", **default OFF é a verdadeira não-mudança** — seguro de decidir agora.
- **Nuance que de-risca ligar:** a captura é **aditiva** e as métricas leem só RVSEC/COV (§6.4) → ligar
  diagnostics **não altera** cobertura/MOP nem quebra comparação pareada nas métricas primárias. A ressalva
  conservadora é só reprodutibilidade byte-a-byte e volume (desprezível).
- **Mecânica do opt-in:** expor `RV_LOGCAT_DIAGNOSTICS` como **linha de env explícita por serviço/campanha** no
  compose, **não** embutir na âncora `&rvandroid-base` compartilhada — ligar tem de ser ato deliberado.
  Recomendação por família: **A → ligar** (decisão do usuário por campanha); **B → manter OFF** salvo interesse
  explícito em quantificar crashes como confounder.

---

## 11. Investigação profunda (2026-06-21) — evidências

### 11.1. Blast-radius do parser (decisão D1)
Call-sites de `parse_logcat_line`/`parse_logcat_file`/`stream_logcat_entries` (11 no total):
- **Produção (6):** `tracker.py:370` (`_process_line`), `logcat_parser.py:71` (loop do `parse_logcat_file`),
  `analyzer.py:378` (usa só `.errors`), `coverage.py:140` (`CoverageComponent._parse_existing_logcat`, resume),
  `task.py:688,698` (`Task.logcat_repository_from_file`), `result_processor.py:287`
  (`_reconstruct_repository_from_logcat`).
- **Testes (2 arquivos, 7 asserts):** `test_logcat_parser.py` (6), `test_tracker.py` (1).
- **API pública:** `rv_coverage/__init__.py` e `parser/__init__.py` exportam `parse_logcat_line`/`parse_logcat_file`.
- **Tracker:** `_track_coverage` (`tracker.py:281-325`) = thread daemon, `readlines()` + tail loop; `_process_line`
  (`361-425`) é stateless → o estado multi-linha vai no `DiagnosticEventParser`, não no tracker.
⇒ Opção A custaria 6 call-sites + 7 asserts + quebra de API; **B é aditivo (0)**. Decisão D1 = B.

### 11.2. Isolamento de métricas (decisão D4)
`coverage.py`: `calculate_metrics()` (578-650) itera só `self.classes`; `total_errors=len(self.errors)`,
`unique_errors=len(self.unique_errors)` (597-598); `get_method_calls` só `self.classes`; `get_errors` só
`self.errors`. Nenhum caminho varre coleções arbitrárias ⇒ `diagnostic_events` nasce isolada.
Reconstrução de resume: `result_processor.py:259-301` → `parse_logcat_file` re-registra a partir do logcat;
o `DiagnosticEventParser` plugado ali faz os diagnósticos sobreviverem ao resume (caveat gh58).

### 11.3. Plumbing da flag e atribuição (decisões D5, D6)
- `LogcatManager.start_capture(output_file, tags=None, clear_buffer=None)` (`logcat_manager.py:126-147`) **já
  aceita `tags`**; o `LogcatComponent` (`logcat.py:128-131`) não passa → usa `default_tags`. Basta o componente
  passar `default_tags + diagnostic_tags`.
- Caminho RV_*: `constants.py` (declara `ENV_*`) → `rv-experiment/__main__.py` Click `@option(envvar=ENV_*)` →
  `ExperimentConfig` → `PlatformConfig` → componente. Adicionar `ENV_LOGCAT_DIAGNOSTICS` segue esse padrão.
- PID vivo: `LogcatComponent` não tem `task.app` no start; `adb logcat --pid` não serve mid-stream ⇒ atribuir
  pelo bloco (`Process: <pkg>`/`ANR in <pkg>`). App-side fixo: `Log.v("RVSEC", ...)` em `ErrorCollector.java`.

### 11.4. Formatos canônicos (sem amostra real capturada — filtro `-s` exclui)
Nenhum logcat do repo contém crashes (todos filtrados). Formatos-alvo para os fixtures:
- **Crash:** `… E AndroidRuntime: FATAL EXCEPTION: main` / `… E AndroidRuntime: Process: <pkg>, PID: <n>` /
  `… E AndroidRuntime: <exc>: <msg>` / N× `… E AndroidRuntime: \tat <classe>.<método>(<File>:<linha>)` /
  `… E AndroidRuntime: Caused by: java.lang.VerifyError: …` / `… E AndroidRuntime: \t… N more`.
  → agrupar por `(tag,pid,tid)`; fechar quando muda `(tag,pid,tid)` ou aparece linha não-continuação.
- **VerifyError load-time:** `… E art: Verification error …` / `… E art: Rejecting class <classe> …` (1-2 linhas).
- **ANR:** `… E ActivityManager: ANR in <pkg>` / `Reason: …` / `… I ActivityManager: Force finishing activity …`
  ou `… I ActivityManager: Process <pkg> (pid N) has died`.

### 11.5. Prior art no repo (valida tags e abordagem)
- `modules/rv-tools/src/rv_tools/builtin/qtesting/src/main.py:77` — filtro histórico:
  `AndroidRuntime:E CrashAnrDetector:D ActivityManager:E SQLiteDatabase:E WindowManager:E ActivityThread:E
  Parcel:E *:F *:S`. Confirma o padrão de captura de crash/ANR no projeto.
- `out/forensic_ajc_zero/check_crashes.py` — já faz forense **offline** de `FATAL EXCEPTION`, `VerifyError`,
  `NoSuchMethodError`, `ClassNotFoundException`. A captura estruturada substitui esse grep manual.

### 11.6. ABI nativa do dataset (decisão D8)
Cruzamento dos 169 APKs de `APKS_FINAL_JCA_DEXLIB_20260604` com `PLANILHA_dexlib2.csv` (col `native_code_abis`),
169/169 casados por `package_name`:

| Categoria | APKs | Implicação p/ crash nativo |
|---|---|---|
| Com código nativo, contém `x86_64` | **144** | roda **nativamente** no AVD x86_64 (sem tradução) |
| Só `arm64-v8a` (tradução ARM, risco↑ SIGSEGV) | **0** | cenário de risco **ausente** |
| Sem código nativo | **25** | SIGSEGV **impossível** |

Distribuição: 129 `arm64-v8a;armeabi-v7a;x86;x86_64`, 25 sem-nativo, 7 `x86_64`, 4 `arm64-v8a;x86_64`,
3 `arm64-v8a;armeabi-v7a;x86_64`, 1 multi-ABI. ⇒ a premissa "tombstone relevante p/ ARM-translation" **não
vale aqui**; combinada com o argumento conceitual (instrumentação é DEX/Java), justifica D8 = fora do v1.

### 11.7. Famílias de campanha (decisão D9)
- **(A) Validação de instrumentação** (dexlib2×ajc): VerifyError/crash é o objeto de estudo → diagnostics
  agrega muito; recomendado ligar (decisão do usuário por campanha).
- **(B) Comparação de ferramentas** (APE/APE-RV cobertura/MOP, ex. `docs/20260619_comparacao_aperv.md`): crash
  é confounder; manter OFF salvo interesse explícito. Como a captura é aditiva (§6.4), ligar **não** invalida a
  comparação pareada das métricas primárias — só afeta reprodutibilidade byte-a-byte.

---

## 12. Referências
- Captura: `modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py:61,126-147,176-187`
- Parser: `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py:83,120-145`
- Modelos: `modules/rv-android-core/src/rv_android_core/domain/log.py`; `domain/coverage.py` (`LogcatRepository`)
- CSV: `modules/rv-platform/src/rv_platform/components/result_processor.py`
- Evidência empírica: `data/results/cmp_0*/` (corrida de `docs/20260619_comparacao_aperv.md`)
