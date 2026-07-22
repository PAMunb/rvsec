# Pré-plano — Correção do resume + geração de planilhas (coverage zerada)

**Data**: 2026-06-10
**Tipo**: Documento de Fase 0 (ideação / análise técnica) — **NÃO é artefato OpenSpec**.
Entrada para Track Selection + `/opsx:explore` (ver `docs/WORKFLOW.md §1`). Decisões aqui
são insumo, não compromisso; o design final é da fase de Design da change.
**Status**: Fases 1-3 concluídas em 2026-06-13. Issue **#65** aberta (refs #58); change
`openspec/changes/gh65-resume-static-data-resolution/` criada e válida (proposal + delta specs
`platform`/`analysis` + design + tasks); **ADR 0003** (`docs/adr/0003-resume-results-dir-derived-from-logcat.md`)
revisita parcialmente o ADR 0002. Próximo passo do workflow SDD: Fase 4 (Implement) via `/opsx:apply`.

---

## 0. Adendo da Fase 1 (Explore) — 2026-06-13

A Fase 1 (Explore) confirmou a causa-raiz ponta a ponta no código e validou empiricamente nos
resultados das 4 VMs em `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS_experimento-20260604`.
Esta seção registra as **decisões travadas**, **correções** ao diagnóstico original (seções 2-8, de
2026-06-10) e um **achado novo**. **Onde as seções abaixo divergirem deste adendo, vale o adendo.**

### 0.1 Decisões travadas (insumo para a proposal/design)

| # | Decisão | Escolha |
|---|---------|---------|
| **D1-approach** | Como o resume obtém `results_dir` | **Opção A** — derivar de `os.path.dirname(task.result.logcat_file)`. Sem mudar o schema do `tasks.json`. |
| **Fallback (Q2)** | Fallback para `coverage_metrics` serializado | **Auditável + accounting** — quando o reparse falhar (logcat/JSON genuinamente ausentes), cair para o `coverage_metrics` serializado **com log auditável + contador** de tasks afetadas. Reconcilia INV-PLT-16 como "sem fallback *silencioso*", não "sem fallback". |
| **Early-return** | Erros zerados no summary (achado novo, §0.4) | **Corrigir** — contar `total_errors`/`unique_errors` **antes** do early-return em `coverage.py:593`. |
| **Sweep (Q4)** | Sweep de confirmação pré-Design | **Não** — causa determinística + dados já consolidados offline (cov_method 29,43%, C1-C4 PASS). |

### 0.2 Causa-raiz ÚNICA, TRÊS sintomas (não dois)

```
resume → Task.from_dict() → __init__ → results_dir="" , app=None
   └─ _resolve_static_data: read_static_analysis_files("", apk, None)
        → os.path.join("", "<apk>.json") = "<apk>.json"  (path RELATIVO, NÃO None)
        → os.path.isfile("<apk>.json") = False
        → retorna StaticAnalysisData VAZIO  (sem exceção, sem TypeError)
   └─ repository.classes vazio
        └─ CoverageMetricsRepository.calculate_metrics()  (coverage.py:593):
             if not self.classes: return CoverageMetrics()   ← EARLY RETURN, tudo zerado
               ├─ summary.csv: cov_*            = 0   (documentado)
               ├─ summary.csv: mop_errors_*     = 0   (ACHADO NOVO §0.4 — não estava no doc)
               └─ coverage.csv: linhas          = 0   (documentado)
   errors.csv SOBREVIVE: _write_task_error_data usa repository.get_errors() direto,
   sem passar por calculate_metrics() → 4285 linhas reconstruídas do logcat.
```

**A Opção A corrige os três sintomas de uma vez**: com `static_data` não-vazio, `repository.classes`
é populado → sem early return → cobertura e erros calculados corretamente.

### 0.3 Correção do mecanismo: dados vazios, NÃO `TypeError` engolido

O doc original (§3.2-3.4) afirma `results_dir=None` → `os.path.join(None,…)` → `TypeError` capturado
pelo `except` → retorna `None`. **Isso está incorreto para o caminho real.** `Task.__init__`
(`task.py:559`) define o default como **`""` (string vazia)**, e `from_dict` chama `__init__`. Logo:

- `getattr(task, "results_dir", None)` retorna `""` (o atributo existe).
- `read_static_analysis_files("", apk, None)` → `os.path.join("", "<apk>.json")` = `"<apk>.json"`
  (path **relativo**), não `TypeError`.
- `parse_file` (`static_analysis_parser.py:205`): `if not file_path or not os.path.isfile(file_path)`
  → arquivo relativo inexistente → retorna **`StaticAnalysisData` VAZIO**, sem exceção.
- `code_package=None` **não** quebra o parser: o filtro `if package and package not in normalized`
  (`_parse_classes`, linha 360) curto-circuita quando `package` é falsy (não filtra).

**Consequência prática**: `_resolve_static_data` **não lança** — retorna dados vazios. O warning que o
doc supõe ("Failed to re-parse…") **não dispara**; o único sinal é o `warning("Analysis file not
found: <apk>.json")` do parser, com path relativo. O sintoma é **ainda mais silencioso** que o doc diz.
Isso muda o **teste de regressão** (D3): ele deve exercitar o caminho de dados-vazios (logcat presente,
`results_dir` vazio), não simular `TypeError`.

### 0.4 ACHADO NOVO: o summary também zera os agregados de erro no resume

O summary lê `mop_errors_total`/`mop_errors_unique` de `repository.calculate_metrics().to_dict()`
(`result_processor.py:585-586`), e `calculate_metrics` faz **early return** com `CoverageMetrics()`
zerado quando `self.classes` está vazio (`coverage.py:593-597`) — **antes** da contagem de erros na
linha 623 (`metrics.total_errors = len(self.errors)`). Portanto, no resume, o summary zera **tanto a
cobertura quanto os agregados de erro**, embora o errors.csv (que usa `get_errors()` direto) esteja
correto.

Evidência (m2/exp_00, in-container vs offline regen):

| | linhas | `cov_method > 0` | `mop_errors_total > 0` |
|---|------:|----------------:|----------------------:|
| **in-container** `summary.csv` | 1055 | **4** | **2** |
| **regen** `summary_regen.csv` | 1089 | 1074 | **501** |

O early-return conflaciona "sem cobertura" com "sem erros" — os erros são independentes da SA. **Fix
travado**: mover a contagem de `total_errors`/`unique_errors` para **antes** do `if not self.classes`,
para que os agregados de erro sobrevivam mesmo no caso degradado legítimo (logcat presente, JSON
genuinamente ausente, ex. `--skip-static`). Entra nesta change como parte de D1, com teste de
regressão dedicado (erros > 0 com `static_data` vazio).

> **D5 é uma violação código-vs-spec, não só um bug.** A invariante **INV-ANA-25**
> (`openspec/specs/analysis/spec.md:351`) afirma textualmente que, com `static_data=None`,
> `calculate_metrics().to_dict()` zera a cobertura mas **"Only `total_errors` and `unique_errors`
> remain accurate."** O early-return em `coverage.py:593` **contradiz a própria spec**: zera também
> os erros. Logo o fix de D5 (contar erros antes do early-return) **não altera INV-ANA-25** — faz o
> código **passar a conformar** com a invariante já escrita. INV-ANA-25 entra em §7 como invariante a
> verificar (não a emendar).

### 0.5 Opção A validada empiricamente (à prova de container)

**Identidade de runtime** (`task.py:722-730`): `initialize()` faz `self.results_dir =
os.path.join(base_results_dir, apk_name)` e `logcat_file = os.path.join(self.results_dir,
base_name + ".logcat")`. Logo, em runtime, vale exatamente:

```
task.results_dir == os.path.dirname(task.result.logcat_file)
```

A Opção A não "aproxima" — **reconstrói o valor exato** que `results_dir` tinha em runtime. E
`logcat_file` herda a relatividade de `base_results_dir` (relativo no container → portável; absoluto
fora → resolve na mesma máquina), tornando o fix robusto dentro e fora do container.

Validação nos dados reais das 4 VMs:

| Verificação | Resultado |
|---|---|
| Dirs por-APK sem `.json` co-localizado (m1/m2/m3/m4 = 44/44/41/40 = 169) | **0 faltando** |
| `errors.csv` (m2/exp_00) — erros sobreviveram ao resume | 4285 linhas (logcat resolve) |
| Simulação do resume: `dirname(logcat_file)` acha logcat **+** JSON | **1299/1299 tasks; 0 logcat ausente, 0 json ausente** |

O JSON de SA está **sempre co-localizado** com os `.logcat` no dir por-APK
(`<apkdir>/<apk_name>.json`). Como o path do logcat é o único comprovadamente resolúvel no resume (os
4285 erros foram reconstruídos a partir dele), derivar o dir do JSON dele garante que o JSON também é
encontrado — para 100% das tasks.

### 0.6 D2 (cov_class no offline regen) já resolvido

O commit `b2bc5aa9` ("offline result consolidation pipeline with real cov_class") **já**: (a) grava
`class_cov` real no slot `cov_class` (`regenerate_container.py:222`) e (b) versionou
`scripts/regenerate_results/` (antes untracked). A questão Q3 do doc está **resolvida**. Resta apenas:
`scripts/regenerate_results/verify.py` C3 **não checa** `cov_class` (linha ~169 só cobre
cov_act/cov_method/cov_reaches_target) e tem comentário stale (linha 166: "cov_class duplicates
cov_method"). Decisão: incluir o ajuste do `verify.py` C3 nesta change.

### 0.7 Respostas às questões abertas da §8

1. **D1 Opção A vs B** → **Opção A** (derivar do logcat). Mínima, sem mudar schema, validada em §0.5.
2. **Reabilitar fallback para `coverage_metrics`** → **Sim, auditável + accounting** (§0.1).
3. **D2/offline regen nesta change** → já feito em `b2bc5aa9`; resta só o `verify.py` C3 (§0.6).
4. **Sweep de confirmação** → **Não** (causa determinística; dados consolidados). Validação documental
   em §0.4-0.5 cobre a evidência que o sweep buscaria.
5. **Por que T=300 também zerou** → **Confirmado e refinado**: zera toda task **não executada ao vivo
   no run que gerou o CSV**. `_process_results` usa `task_storage.get_completed_tasks()`, que retorna o
   objeto vivo (com `results_dir`) só para tasks da sessão corrente; tasks de sessões anteriores vêm de
   `load()→from_dict` (`results_dir=""`). Como o run final de consolidação pula ~tudo
   (`_skip_completed_tasks`), 100% das linhas — inclusive T=300 — passam pelo caminho quebrado. Um run
   fresco single-pass **não** exibe o bug (por isso os testes do gh58 passaram).

---

## 1. O que queremos mudar e por quê

Durante o `experimento-20260604` (re-run JCA, 169 APKs, 4 VMs), as planilhas consolidadas
**geradas dentro do container** (`summary.csv`/`coverage.csv`) saíram com **cobertura zerada**
para praticamente todas as tasks vindas de resume. O experimento usa resume de forma **intensiva**
(3 passes T=60/180/300 + múltiplos mop-ups por OOM/preempção), então isso é a norma, não exceção.

O bug **já tinha sido endereçado** pela change **gh58** (arquivada 2026-05-14,
`openspec/changes/archive/2026-05-14-gh58-result-processor-static-data/`), que está **presente no
código e na imagem `rvandroid:0.9.0`** usada no experimento. Mesmo assim o defeito **persistiu**.
Esta change quer: (a) corrigir de verdade o resume no `result_processor.py`, (b) fechar o teste que
deixou o gap passar, (c) portar o fix gêmeo para a ferramenta offline `scripts/regenerate_results/`
(chore que o gh58 adiou e nunca foi feito), e (d) sincronizar docs/invariantes.

**Importante (sem urgência de dados):** os dados do 20260604 **não se perderam**. Foram consolidados
offline com sucesso (`experimento-20260604/scripts/consolidate_offline.sh`, verify C1–C4 PASS,
cov_method médio 29,43%). Esta change é para **as próximas campanhas produzirem CSV correto por
construção**, não um resgate. Relaciona-se a FR10 (consolidação), FR12 (métricas de cobertura),
NFR03 (reprodutibilidade) e NFR08 (durabilidade de resume).

---

## 2. Sintoma observado (evidência)

`summary.csv` in-container de `m2/results/exp_00/exp_00/` (1055 linhas, schema gh58 de 12 colunas):

| timeout | linhas | linhas com `cov_method > 0` |
|---------|-------:|----------------------------:|
| 60      | 363    | **0** |
| 180     | 354    | 4 |
| 300     | 338    | **0** |
| **Σ**   | 1055   | **4** |

Ou seja: cobertura praticamente toda zerada, **inclusive no T=300** (o último passe, supostamente
"vivo"). O schema é o do gh58 (`cov_class, cov_reaches_target, ...`), confirmando que a imagem
**tem** o gh58 — o defeito é de *runtime/precondição*, não de versão.

Contraste: o **offline regen** (mesmos logcats + JSONs de SA externos) produz cobertura correta
(cov_method médio 29,43%; 16 729 linhas; verify C1–C4 PASS).

---

## 3. Causa-raiz (confirmada ponta a ponta)

> **Correção da Fase 1 (§0.3):** o mecanismo descrito abaixo como `TypeError` engolido está incorreto.
> O caminho real passa `results_dir=""` (não `None`), gerando path relativo inexistente que retorna
> `StaticAnalysisData` **vazio sem exceção**. O resultado (cobertura zerada) é o mesmo, mas o mecanismo
> — e portanto o teste de regressão — difere. Vale o §0.3.

### 3.1 O gh58 corrigiu o *mecanismo*, mas a *precondição* falha no resume real

O gh58 fez o `result_processor._reconstruct_repository_from_logcat` reparsear o JSON de SA
on-demand via `_resolve_static_data(task)`
(`modules/rv-platform/src/rv_platform/components/result_processor.py:152`):

```python
results_dir  = getattr(task, "results_dir", None)
apk_name     = task.config.apk_name
code_package = task.app.code_package if getattr(task, "app", None) else None
static_data  = static_analysis_parser.read_static_analysis_files(results_dir, apk_name, code_package)
```

### 3.2 `results_dir` e `app` NÃO são serializados → ambos vazios no resume

`Task.to_dict()` serializa **apenas** `id`, `config`, `result`
(`modules/rv-android-core/src/rv_android_core/domain/task.py:846-857`):

```python
return {"id": self.id, "config": self.config.to_dict(), "result": self.result.to_dict()}
```

`results_dir` (`task.py:559`, default `""`) e `app` (`task.py:558`, default `None`) são **campos
runtime-only**. `Task.from_dict()` (`task.py:860`) reconstrói só `config` + `result`. Confirmado no
`tasks.json` real: as chaves de cada task são só `['id', 'config', 'result']`.

Logo, no resume: `results_dir = None` (ou `""`) e `code_package = None`. A chamada vira
`read_static_analysis_files(None, apk, None)`. E `read_static_analysis_files`
(`modules/rv-static-analysis/.../static_analysis_parser.py:253`) monta o path assim
(linha 272):

```python
file_path = os.path.join(results_dir, apk + constants.EXTENSION_STATIC_ANALYSIS)  # results_dir/<apk>.json
```

`os.path.join(None, ...)` → **`TypeError`** → capturado pelo `except Exception` em
`_resolve_static_data` → `warning` silencioso → retorna `None` → `LogcatRepository` sem denominadores
→ **cobertura por método zera** para toda task de resume.

### 3.3 Reprodução empírica

Com um dir real do 20260604 (`.../exp_00/exp_00/app.passwordstore.agrahn_11602.apk/`):

```
read_static_analysis_files(<apkdir>, apk, None)  ->  221 classes, 724 métodos   ✅
read_static_analysis_files(None,     apk, None)  ->  TypeError                   ❌ (o caso do resume)
```

O JSON existe em `<apkdir>/<apk>.json`. O path correto que o parser precisa é **o dir por-APK**, que
é exatamente `os.path.dirname(task.result.logcat_file)` — e o `logcat_file` **É serializado**
(`result.logcat_file = results/exp_00/<apk>/<apk>__1__60__monkey.logcat`).

### 3.4 Por que os testes do gh58 não pegaram

O fixture `_make_gh58_task`
(`modules/rv-platform/tests/components/test_result_processor.py:540-569`) **seta manualmente**
`task.results_dir = str(results_dir)` (linha 549) e `task.app = mock_app` (linha 566). Ou seja, os
testes do gh58 **nunca exercitam o resume real** (onde ambos vêm vazios de `from_dict`). Eles
validam o mecanismo de reparse com a precondição já satisfeita — passam em verde, mas mascaram o gap.

### 3.5 O dado NÃO se perdeu (existe em DOIS lugares)

1. **`task.result.coverage_metrics`** está serializado no `tasks.json` e tem os valores **corretos
   do runtime**: 1040/1055 tasks COMPLETED com `method_coverage > 0` (ex.: `method_coverage=18,92`,
   `activities_coverage=22,73`, `methods_mop_reachable_coverage=19,25` num T=60). Porém é um conjunto
   **parcial** (tem `method_coverage`, `activities_coverage`, `methods_mop_reachable_coverage`,
   `total_errors`, `total_method_calls`; **não** tem `class_coverage` nem a quebra de reachability).
2. **Os `.logcat` + JSONs de SA** permitem reconstrução completa (é o que o offline regen faz).

**Ironia central:** o gh58 **removeu** o fallback de 3 níveis que usava `coverage_metrics`
(INV-PLT-16, "no silent fallback to stale serialized metrics") e o trocou por um reparse que falha no
resume real. Resultado: a `summary.csv` zera mesmo com o valor correto deserializado ao lado. O
`coverage_metrics` não é "stale" — foi computado ao vivo quando a task rodou.

---

## 4. Defeitos identificados (consolidados)

> **Atualizado pela Fase 1 (§0).** Mecanismo de D1 corrigido (dados vazios, não `TypeError` — §0.3);
> D1 ampliado para erros (§0.4); D2 resolvido no commit `b2bc5aa9` (§0.6).

| # | Defeito | Local | Severidade |
|---|---------|-------|-----------|
| **D1** | Resume zera cobertura **e agregados de erro do summary**: `_resolve_static_data` recebe `results_dir=""` (não serializado) → `read_static_analysis_files("", apk, None)` monta path relativo inexistente → retorna `StaticAnalysisData` **vazio** (sem exceção) → `repository.classes` vazio → `calculate_metrics()` faz **early return** zerado | `result_processor.py:152-176` + `task.py:846-857` + `coverage.py:593` | **Alta** (corrompe cobertura E `mop_errors_*` de todos os CSV in-container de campanhas com resume) |
| **D2** | ~~Slot `cov_class` grava `method_cov`~~ — **RESOLVIDO** no commit `b2bc5aa9` (offline regen grava `class_cov` real; script versionado). Resta só `verify.py` C3 não checar `cov_class` (§0.6) | `scripts/regenerate_results/verify.py` (C3) | Baixa (ajuste residual) |
| **D3** | Testes do gh58 não cobrem o resume real (fixture seta `results_dir`/`app`). O novo teste deve exercitar **dados vazios** (logcat presente, `results_dir=""`), não simular `TypeError` (§0.3) | `test_result_processor.py:540-569` | Média (deixou D1 passar) |
| **D4** | Docs desatualizadas: `rv-platform/CLAUDE.md` descreve comportamento pré-gh58 ("writes a single summary row using `coverage_metrics`" — confirmado stale); `experimento-20260604/CLAUDE.md` gotcha #7 trata o bug como "a corrigir numa change própria" | docs | Baixa |
| **D5** | `calculate_metrics` conflaciona "sem cobertura" com "sem erros": o early-return (`coverage.py:593`) ocorre **antes** da contagem de erros (linha 623), zerando `total_errors`/`unique_errors` mesmo quando os erros existem no repository (§0.4) | `coverage.py:593-624` | Média (subcausa de D1; fix: contar erros antes do early-return) |

---

## 5. Direções de correção (a decidir no Design — não fechado)

### Fix D1 — restaurar a resolução de `results_dir` no resume
- **Opção A (preferida, P1):** em `_resolve_static_data`, quando `results_dir` estiver vazio/None,
  derivá-lo de `os.path.dirname(task.result.logcat_file)`. Usa dado **já serializado**, sem mudar
  schema do `tasks.json`. Tratar `code_package=None` (o parser tolera; o offline regen passa `""` e
  funciona — o JSON já vem filtrado pelo GATOR).
- **Opção B (mais robusta, escopo maior):** serializar `results_dir` (string curta) no `Task.to_dict`.
  Diferente do que o ADR 0002 rejeitou (serializar o `StaticAnalysisData` inteiro, MBs/task); um path
  é barato. Resolve não só cobertura mas qualquer consumidor futuro de `results_dir` no resume.
  Atenção: paths absolutos do container (`/rvandroid/...`) não existem fora do container → preferir
  path relativo (como o `logcat_file` já é) ou re-derivar do base na carga.
- **Opção C (rede de segurança):** quando logcat/JSON faltarem, cair para o `coverage_metrics`
  serializado (parcial) **com log auditável**, em vez de zerar. Tensão com a filosofia do gh58
  (INV-PLT-16, "no silent fallback"); pode ser reconciliada como "fallback auditável, não silencioso".
- **Trocar o `warning` silencioso por falha contabilizada:** ao menos contar/expor quantas tasks
  zeraram por static_data ausente, para o defeito nunca mais passar despercebido.

### Fix D2 — portar o fix de `cov_class` para o offline regen
- Manter `called_classes` (set de `call["class_name"]`) e usar
  `total_classes = metrics_dict["total_classes"]` (mesmo denominador do summary) →
  `cov_class = len(called_classes)/total_classes*100`. Já validado o caminho: o summary usa
  `class_coverage = called_classes/total_classes` (`rv_android_core/domain/coverage.py:427`).
- **Atualização (§0.6):** o fix de `cov_class` no offline regen **já foi feito** no commit `b2bc5aa9`
  (grava `class_cov` real, `regenerate_container.py:222`) e os scripts **já estão versionados** (o
  chore que o gh58 adiou — não é mais "untracked"). Resta apenas o resíduo: `verify.py` C3 não checa
  `cov_class` (comentário stale na linha 166). Esse ajuste do `verify.py` entra nesta change.

### Fix D3 — teste de integração de resume real
- Construir a task via `Task.from_dict(task.to_dict())` (ida-e-volta de serialização), com o JSON de
  SA co-localizado no dir por-APK e o `logcat_file` apontando para lá, e asseverar `cov_method>0`.
  É o teste que faltou: exercita a precondição vazia que o fixture do gh58 burlava.

### Fix D4 — sincronizar docs
- Atualizar `rv-platform/CLAUDE.md` (seção "MOP Violation Reconstruction") para o comportamento
  pós-correção; remover/atualizar o gotcha #7 do `experimento-20260604/CLAUDE.md`; revisitar
  INV-PLT-15/16/17 nos specs (`openspec/specs/platform/spec.md`, `analysis/spec.md`).

---

## 6. Escopo afetado

> **Atualização da Fase 1 (§0):** Opção A escolhida → `task.py` **não** é tocado (sem mudança de
> schema). Adicionado `coverage.py` ao escopo (fix do early-return, D5).

**Código (framework):**
- `modules/rv-platform/src/rv_platform/components/result_processor.py` — `_resolve_static_data`
  (derivar `results_dir` de `os.path.dirname(task.result.logcat_file)`; Opção A) + accounting/fallback
  auditável quando o reparse falhar.
- `modules/rv-android-core/src/rv_android_core/domain/coverage.py` — `calculate_metrics`: contar
  `total_errors`/`unique_errors` **antes** do early-return `if not self.classes` (D5, §0.4).
- `modules/rv-android-core/src/rv_android_core/domain/task.py` — **não tocado** (Opção A dispensa
  serializar `results_dir`).
- `modules/rv-platform/tests/components/test_result_processor.py` — novo teste de resume real;
  rever `_make_gh58_task`.
- `modules/rv-platform/tests/execution/test_resume*.py` — cobertura de integração.

**Tooling offline (script no repo, fora de `modules/`):**
- `scripts/regenerate_results/regenerate_container.py` — fix `cov_class` **já aplicado** em `b2bc5aa9`
  (linha 222); sem ação pendente.
- `scripts/regenerate_results/verify.py` — passar a checar `cov_class` no C3 (hoje pulado por ser
  não-confiável; comentário stale na linha 166). **Único item pendente do tooling offline.**
- `scripts/regenerate_results/` **já versionado** em `b2bc5aa9` (não é mais untracked).

**Não toca:** `parse_logcat_file` / `rv-coverage` (API estável); `rv-experiment`; `tasks.json`
schema (a menos da Opção B); instrumentação; pipeline de execução.

**Consumidores das planilhas:** as colunas não mudam de nome; `cov_class` na `coverage.csv` passa a
ser **confiável** (hoje aliasa `cov_method`). Análises que já usavam `summary.cov_class` seguem
corretas; quem evitava `coverage.cov_class` pode passar a usá-la.

---

## 7. Track sugerido e invariantes

- **Track:** Full SDD (`rv-sdd`). Toca código de framework, tem **decisão de design real** (como o
  resume obtém `results_dir`: derivar do logcat vs serializar; reabilitar ou não o fallback de
  `coverage_metrics`), e cruza ≥2 módulos potenciais. Justifica ADR (revisão/superseção parcial do
  **ADR 0002**) e provavelmente `/rv-risk` (mexe em contrato de dados de experimento).
- **Invariantes a revisitar:** INV-PLT-15 (resume obtém static_data — precisa de precondição de
  `results_dir`), INV-PLT-16 (remoção do fallback — reconsiderar fallback auditável), INV-PLT-17
  (`cov_class = class_coverage` — estender ao tooling offline). **INV-ANA-25** (a verificar, não
  emendar): o fix de D5 faz `calculate_metrics().to_dict()` cumprir a garantia já escrita de que
  `total_errors`/`unique_errors` permanecem acurados quando `static_data` está ausente (§0.4) — hoje o
  early-return a viola.
- **GitHub:** abrir issue nova `PAMunb/rvsec#N` ("result_processor resume ainda zera cobertura:
  results_dir/app não serializados") referenciando #58. Diretório `gh<N>-resume-static-data-resolution`.

---

## 8. Questões abertas para a ideação

> **RESPONDIDAS na Fase 1 — ver §0.7.** Resumo: (1) Opção A; (2) fallback auditável + accounting;
> (3) D2 já feito, resta `verify.py` C3; (4) sem sweep; (5) T=300 zerou pelo run de consolidação que
> pula tudo. As questões abaixo ficam como registro do estado em 2026-06-10.

1. **D1 — Opção A (derivar do logcat) vs B (serializar `results_dir`)?** A é mínima; B é mais robusta
   mas mexe no schema do `tasks.json` e precisa lidar com paths absolutos do container.
2. **Reabilitar o fallback para `coverage_metrics` serializado** (auditável) quando o reparse não for
   possível? Reconcilia com INV-PLT-16 ou o supera?
3. **D2/offline regen entra nesta change** (unifica + versiona `scripts/regenerate_results/`) ou vira
   chore separado?
4. **Confirmar D1 em outros tools/timeouts**: o sample foi m2/exp_00. Vale um sweep rápido nas 4 VMs
   para quantificar a fração zerada por container antes do Design (provavelmente ~100%).
5. **Por que o T=300 (passe "vivo") também zerou?** Hipótese: a geração final do `summary.csv` roda
   sobre TODAS as tasks via `get_completed_tasks()` (todas `repository=None`, todas pelo caminho de
   resume), não só as do passe corrente. Confirmar no `platform._process_results`.

---

## 9. Referências

- Change anterior: `openspec/changes/archive/2026-05-14-gh58-result-processor-static-data/`
  (proposal, design, specs, tasks).
- `docs/adr/0002-resume-path-static-data-reparse.md` — decisão do reparse on-demand (a revisitar).
- `docs/20260514_regenerar_planilhas.md` — design do pipeline offline.
- Invariantes: `openspec/specs/platform/spec.md` (INV-PLT-15/16/17), `analysis/spec.md` (INV-ANA-25).
- Evidência do sintoma: `experimento-20260604/RELATORIO.md §6.6`, `CLAUDE.md` gotcha #7.
- Pipeline de consolidação usado: `experimento-20260604/scripts/consolidate_offline.sh`.
- Código: `result_processor.py:152` (`_resolve_static_data`), `task.py:846` (`to_dict`),
  `static_analysis_parser.py:272` (montagem do path), `coverage.py:593` (early-return) / `:623`
  (contagem de erros, D5), `regenerate_container.py:222` (slot cov_class, fix b2bc5aa9),
  `test_result_processor.py:540` (fixture que mascarou o bug).
```
