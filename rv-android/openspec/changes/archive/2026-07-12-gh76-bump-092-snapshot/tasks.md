<!-- Change pequena: grupos independentes (arquivos disjuntos). Grupo 1 primeiro (validar diff
     do plugin isolado); grupos 2-5 paralelizáveis; grupo 6 (Verificação) por último. -->

## 1. POMs do reator (via plugin)

- [x] 1.1 Da raiz `rvsec/`: `mvn versions:set -DnewVersion=0.9.2-SNAPSHOT -DgenerateBackupPoms=true`
- [x] 1.2 `git diff --stat` — confirmar que só os 45 POMs do reator mudaram (zero em `backup/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup)

## 2. rv-android/pom.xml (explícito, comentado no reator)

- [x] 2.1 `rv-android/pom.xml`: `<parent><version>` (l.10) + `<version>` do módulo → `0.9.2-SNAPSHOT`

## 3. Scripts runtime (mantêm `-SNAPSHOT`)

- [x] 3.1 `configure.sh:13` `RV_MONITOR_VERSION` → `0.9.2-SNAPSHOT`
- [x] 3.2 `rvsec/config.sh:13` `RV_MONITOR_VERSION` → `0.9.2-SNAPSHOT`
- [x] 3.3 `rv-android/scripts/run_phase5_validators.sh:80` `validator-0.9.2-SNAPSHOT.jar`

## 4. Docker chain (tag `0.9.1` → `0.9.2`)

- [x] 4.1 Build scripts: `build_docker_image.sh:12`; `docker/{base,android,tools,rvandroid}/build.sh:5` (+comentário l.15); `docker/rvandroid_dev/build.sh:3`
- [x] 4.2 Dockerfile `FROM`: `docker/{android,tools,rvandroid,rvandroid_dev}/Dockerfile:1`
- [x] 4.3 Run helpers: `docker/base/run.sh:3`, `docker/android/run.sh:3`, `docker/tools/run.sh:17` (+comentário l.47), `docker/rvandroid/run.sh:3`
- [x] 4.4 Compose canônico: `docker/docker-compose.yml:20`; `docker/docker-compose.dexlib2-validation.template.yml:34,55` (+comentários l.6,21)

## 5. Defaults Python de imagem

- [x] 5.1 `rv-android/scripts/baseline_docker.py:252-253` → `0.9.2`
- [x] 5.2 `rv-android/scripts/preprocess_docker.py:271-272` → `0.9.2`
- [x] 5.3 `rv-android/scripts/calibration_orchestrator.py:584-585` → `0.9.2`
- [x] 5.4 `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:202` → `0.9.2`

## 6. Testes (asserts + green)

- [x] 6.1 `modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` → `*-0.9.2-SNAPSHOT.jar`
- [x] 6.2 `modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:536-538,546-548,580-582,594-596` → `*-0.9.2-SNAPSHOT.jar`
- [x] 6.3 `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed

## 7. Verificação

- [x] 7.1 `mvn versions:commit` (remover `*.versionsBackup`)
- [x] 7.2 `mvn -o -q -DskipTests validate` (da raiz) → EXIT=0
- [x] 7.3 `git grep -n "0.9.1-SNAPSHOT"` e `git grep -n ":0.9.1"` → residual só nas exceções esperadas (`backup/`, `experimento-20260706/`, `experimento-20260604/`, `experimento-20260508/`, `para05/`, `data/`, `*.md`)
- [x] 7.4 Confirmar `experimento-20260706/` e históricos intactos em `0.9.1`
- [x] 7.5 Verificar todos os acceptance criteria do `plan.md`
</content>
