# Change Plan: Bump 0.9.1-SNAPSHOT → 0.9.2-SNAPSHOT

**Date**: 2026-07-12
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#76](https://github.com/PAMunb/rvsec/issues/76)
**PRD Reference**: N/A (chore de release/manutenção; sem alteração de comportamento)
**Domains**: instrumentation (asserts de teste), build/infra (POMs do reator + Docker chain)

## 1. Context

Subir a versão do projeto de `0.9.1-SNAPSHOT` → `0.9.2-SNAPSHOT` nos POMs ativos do reator
Maven e as tags de imagem Docker `0.9.1` → `0.9.2`, além dos scripts de runtime/build ativos.
POMs mantêm o sufixo `-SNAPSHOT`; imagens Docker usam a forma release (sem `-SNAPSHOT`).

A mudança é **mecânica, sem decisões de design** (Quick Path — WORKFLOW.md §3): substituição
de string de versão em POMs (via `versions-maven-plugin`), scripts, Dockerfiles, compose,
defaults Python e asserts de teste. O mapeamento completo (Phase 0) está em
`docs/20260712_plano_bump_0.9.2-SNAPSHOT.md`.

Diferença vs. o bump anterior (0.9.0→0.9.1): os órfãos `rvsec-gesda`/`rvsec-reachability`
foram movidos para `backup/` — a árvore ativa está **uniformemente** em `0.9.1-SNAPSHOT`, então
não há tratamento especial de "deixar em versão antiga" além dos históricos.

## 2. Scope

**Incluído (ativo):**
- **Grupo A — POMs do reator (via plugin):** `mvn versions:set` da raiz alcança 45 POMs.
- **Grupo B — `rv-android/pom.xml` (explícito):** comentado no reator (`pom.xml:73`), não é
  alcançado pelo plugin — edição manual de `<version>` + `<parent><version>`.
- **Grupo C — Scripts runtime:** 3 arquivos (caminhos de JAR Maven, mantêm `-SNAPSHOT`).
- **Grupo D — Docker chain:** build scripts, Dockerfile `FROM`, run helpers, compose canônico
  (tag `0.9.1` → `0.9.2`, sem `-SNAPSHOT`).
- **Grupo E — Defaults Python de imagem:** 4 arquivos.
- **Grupo F — Testes:** asserts de nome de jar (2 arquivos) + rodar suítes green.

**Excluído (NÃO tocar — decisão confirmada 2026-07-12):**
- `experimento-20260706/` (pinado em `0.9.1`, experimento ativo em curso).
- `backup/*` (4 POMs em `0.9.0-SNAPSHOT` — gesda/reachability).
- Históricos: `experimento-20260604/`, `experimento-20260508/`, `para05/`, `data/`, docs `*.md`.
- Reatores de versão própria: crylogger (`0.3.0`), docker/mop (`1.2.8`), rv-monitor
  docs/installer (`1.4-SNAPSHOT`), teste-sootup (`0.6.0`).
- `rvsmart/dependency-reduced-pom.xml` (gerado pelo shade — regenerado no build, não editar).

## 3. File Inventory

### Grupo A — POMs do reator (via `versions-maven-plugin`)

Da raiz `rvsec/`:
```bash
mvn versions:set -DnewVersion=0.9.2-SNAPSHOT -DgenerateBackupPoms=true
```
Alcança 45 POMs: raiz `rvsec-parent`; `rv-monitor` (+rt, logicrepository, 10 plugins, rv-monitor);
`javamop`; `mop-maven-plugin`; `rvsec` (+rvsec-mop, -mop-extractor, -mop-defsuses, -core,
-logger-csv, -agent, -android); `rvsec-android` (+rvsec-apk, -logger-logcat, rvsec-gator
+commons/sootandroid/client, rvsmart, -frame-computer, -instrumentation-dexlib2 +10 filhos).

| File | Action | Detail |
|------|--------|--------|
| 45 POMs do reator | `versions:set` | `0.9.1-SNAPSHOT` → `0.9.2-SNAPSHOT` (via plugin) |

### Grupo B — rv-android/pom.xml (explícito)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/pom.xml` | Edit | `<parent><version>` (linha 10) + `<version>` do módulo → `0.9.2-SNAPSHOT` |

### Grupo C — Scripts runtime (JAR paths, mantêm `-SNAPSHOT`)

| File | Action | Detail |
|------|--------|--------|
| `configure.sh` | Edit | l.13 `RV_MONITOR_VERSION=0.9.1-SNAPSHOT` → `0.9.2-SNAPSHOT` |
| `rvsec/config.sh` | Edit | l.13 `RV_MONITOR_VERSION=0.9.1-SNAPSHOT` → `0.9.2-SNAPSHOT` |
| `rv-android/scripts/run_phase5_validators.sh` | Edit | l.80 `validator-0.9.1-SNAPSHOT.jar` → `validator-0.9.2-SNAPSHOT.jar` |

### Grupo D — Docker chain (tag `0.9.1` → `0.9.2`, sem `-SNAPSHOT`)

| File | Action | Detail |
|------|--------|--------|
| `build_docker_image.sh` | Edit | l.12 `IMAGE_TAG="0.9.1"` |
| `rv-android/docker/base/build.sh` | Edit | l.5 `VERSION=0.9.1` (+comentário l.15) |
| `rv-android/docker/android/build.sh` | Edit | l.5 `VERSION=0.9.1` (+comentário l.15) |
| `rv-android/docker/tools/build.sh` | Edit | l.5 `VERSION=0.9.1` (+comentário l.15) |
| `rv-android/docker/rvandroid/build.sh` | Edit | l.5 `VERSION=0.9.1` (+comentário l.15) |
| `rv-android/docker/rvandroid_dev/build.sh` | Edit | l.3 `VERSION=0.9.1` |
| `rv-android/docker/android/Dockerfile` | Edit | l.1 `FROM phtcosta/rvsec_base:0.9.1` |
| `rv-android/docker/tools/Dockerfile` | Edit | l.1 `FROM phtcosta/rvsec_android:0.9.1` |
| `rv-android/docker/rvandroid/Dockerfile` | Edit | l.1 `FROM phtcosta/rvandroid_tools:0.9.1` |
| `rv-android/docker/rvandroid_dev/Dockerfile` | Edit | l.1 `FROM phtcosta/rvandroid_tools:0.9.1` |
| `rv-android/docker/base/run.sh` | Edit | l.3 `rvsec_base:0.9.1` |
| `rv-android/docker/android/run.sh` | Edit | l.3 `rvsec_android:0.9.1` |
| `rv-android/docker/tools/run.sh` | Edit | l.17 `rvandroid_tools:0.9.1` (+comentário l.47) |
| `rv-android/docker/rvandroid/run.sh` | Edit | l.3 `rvandroid:0.9.1` |
| `rv-android/docker/docker-compose.yml` | Edit | l.20 `phtcosta/rvandroid:0.9.1` (entrypoint canônico) |
| `rv-android/docker/docker-compose.dexlib2-validation.template.yml` | Edit | l.34,55 `image:` (+comentários l.6,21) |

### Grupo E — Defaults Python de imagem

| File | Action | Detail |
|------|--------|--------|
| `rv-android/scripts/baseline_docker.py` | Edit | l.252-253 `default="phtcosta/rvandroid:0.9.1"` + help |
| `rv-android/scripts/preprocess_docker.py` | Edit | l.271-272 `default=...:0.9.1` + help |
| `rv-android/scripts/calibration_orchestrator.py` | Edit | l.584-585 `default=...:0.9.1` + help |
| `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py` | Edit | l.202 `default="phtcosta/rvandroid:0.9.1"` |

### Grupo F — Testes (asserts, mantêm `-SNAPSHOT`)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py` | Edit | l.97-99 → `*-0.9.2-SNAPSHOT.jar` (rv-monitor-rt, rvsec-core, rvsec-logger-logcat) |
| `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py` | Edit | l.536-538,546-548,580-582,594-596 → `*-0.9.2-SNAPSHOT.jar` |

## 4. Execution Order

Todos os grupos são independentes entre si (arquivos disjuntos) e podem rodar em paralelo.
Sequência sugerida para verificação limpa:

1. **Grupo A** (`versions:set`) — depois validar `git diff --stat` que só os 45 POMs do reator
   mudaram (zero em `backup/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup).
2. **Grupo B** (rv-android/pom.xml) — manual.
3. **Grupos C, D, E** — edições de string independentes (paralelizáveis).
4. **Grupo F** — asserts + rodar suítes.
5. **Verificação final** (`versions:commit`, grep residual, `mvn validate`, pytest).

Change pequena (~25 arquivos ativos + 45 POMs via 1 comando) — **não requer subagentes**
(WORKFLOW.md §5: subagentes só para 20+ arquivos com edição manual independente; aqui o grosso
é 1 comando de plugin).

## 5. Acceptance Criteria

- [ ] 46 POMs ativos em `0.9.2-SNAPSHOT` (45 via plugin + `rv-android/pom.xml`); `git diff --stat`
      confirma zero mudança em `backup/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup
- [ ] Scripts runtime (Grupo C): 3 arquivos em `0.9.2-SNAPSHOT`
- [ ] Docker chain (Grupo D): 16 arquivos em `0.9.2` (build scripts, Dockerfile FROM, run helpers, compose canônico)
- [ ] Defaults Python (Grupo E): 4 arquivos em `0.9.2`
- [ ] Asserts de teste (Grupo F) em `*-0.9.2-SNAPSHOT.jar`
- [ ] `experimento-20260706/` e históricos **intactos** em `0.9.1`
- [ ] `mvn -o -q -DskipTests validate` (da raiz) → EXIT=0
- [ ] Pytest green: `test_instrumenter.py` + `test_dexlib_instrumentation.py` com `--import-mode=importlib -o "addopts="` → 0 failed
- [ ] `git grep "0.9.1-SNAPSHOT"` e `git grep ":0.9.1"` → residual apenas nas exceções esperadas
      (`backup/`, `experimento-20260706/`, `experimento-20260604/`, `experimento-20260508/`, `para05/`, `data/`, `*.md`)
- [ ] `mvn versions:commit` executado (sem `*.versionsBackup` restantes)
</content>
