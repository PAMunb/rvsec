# Monitoramento — experimento-20260706 (JCA, dataset novo 219 APKs)

Registro automático do progresso e dos **problemas/erros** das 4 VMs gcloud
(`m1..m4-exp02`, zona `us-central1-f`). Uma seção por ciclo, gerada de hora em
hora por `scripts/health_check.py` (cron local).

**Convenção de fuso:** horários de **verificação/ciclo/ação** são sempre no **horário
local (UTC−3)**. Horários de **erro/evento na VM** ficam em **UTC** (hora da própria VM).

## Desenho
- 219 APKs × 11 tools × 3 reps × 3 passes (timeouts 60/180/300s) = **21 681 tasks**.
- Spec set **jca**, variante **dexlib2**, APKs já instrumentados (skip instrument/monitors/static).
- Topologia: 4 VMs × 4 containers = 16 batches. Batch→VM: m1=00-03, m2=04-07, m3=08-11, m4=12-15.
- Alvos COMPLETED distintos por VM: **m1=5544, m2=5544, m3=5445, m4=5148**.
- Imagem `phtcosta/rvandroid:0.9.1` (+ humanoid:1.0, ares:latest, qtesting:latest).

## Como o monitor age
- Lê o progresso REAL por VM via `rv_status.py --json --env .env.mN` (dedup por
  identidade `(apk,tool,variant,rep,timeout)`).
- **AUTO-RESUME**: se o run já foi iniciado mas `run_experiment.sh` morreu e ainda
  faltam tasks, relança (resume idempotente via `tasks.json`). Teto de 12 resumes
  por VM; ao estourar, exige intervenção humana. NUNCA faz o disparo inicial.
- Erros/APKs só-falha/containers mortos são sempre **registrados** (não decididos).

## Marcos
- **2026-07-06 14:13–14:14 (local)** — run disparado nas 4 VMs (nohup). Passada
  TIMEOUT=60s iniciada; `run_experiment.sh` ALIVE e `exp_00..03` up em todas.
  Pids: m1=112698, m2=6958, m3=6482, m4=6535. (= 17:13–17:14 UTC na VM.)

## Diagnóstico — falhas `emulator/boot` no arranque (2026-07-06 14:27–14:34 local)

**Sintoma:** ciclo 14:27:48 reportou fail rate aparentemente alto (7/22 em m1,
5/20 em m2, 6/22 em m3, 3/22 em m4). Investigação manual (leitura direta dos
`tasks.json` de cada container nas 4 VMs) — não apenas o agregado do
`rv_status.py`.

**Causa raiz confirmada:** boot-storm de arranque, não regressão nem problema
sistêmico. Em **todo** container afetado, a falha é sempre a(s) primeira(s)
task(s)/repetição(ões) que aquele container tentou executar — sempre
`EmulatorError: Failed to start emulator RVSec` — dentro de uma janela de
~7 min logo após o `docker compose up` (ex.: `com.craxiom.networksurvey_114.apk`
monkey rep 1/2/3 no `exp_02` da m1, ERROR entre 14:15:02–14:21:52 local).
Depois dessa janela, **zero falhas novas** em qualquer container/VM — todas as
tasks seguintes (mesma APK com outras tools, e todas as APKs seguintes)
completaram normalmente. Explicação plausível: 16 containers × emulador
cold-boot simultâneo por VM gera contenção de KVM/CPU/RAM no arranque; uma vez
que o container consegue seu primeiro boot bem-sucedido, não volta a falhar.
O % parecia alto só por causa do denominador pequeno (~20-30 tasks concluídas
de 5544 esperadas por VM neste ponto do run).

**Verificação no código-fonte (rv-platform / rv-experiment) — NÃO especulação:**
1. **Não existe retry in-process.** `TaskExecutor.execute()`
   (`modules/rv-platform/src/rv_platform/execution/executor.py:181-270`) roda o
   pipeline de componentes **uma única vez** dentro de um `try/except`; ao
   capturar `EmulatorError` (levantada em
   `EmulatorComponent.start_emulator()`, `modules/rv-platform/src/rv_platform/components/emulator.py:98-155`,
   que também não tem retry — loga, embrulha e re-lança direto), marca
   `TaskState.ERROR`, limpa recursos e retorna `False`. Nenhum backoff, nenhuma
   nova tentativa, nenhuma distinção por tipo de erro.
   `Platform._execute_tasks()` (`modules/rv-platform/src/rv_platform/platform.py:313-412`)
   itera as tasks uma vez cada; se uma falha, segue para a **próxima task da
   fila**, nunca reagenda a mesma.
2. **Novas entradas para a mesma identidade só surgem ao RE-EXECUTAR o
   processo** (resume manual ou auto-resume do `health_check.py` quando
   `run_experiment.sh` morre) — nunca automaticamente dentro do mesmo processo.
   `Platform._generate_tasks()` (`platform.py:181-228`) gera uma `Task` nova
   (UUID novo) para cada combinação `(apk,tool,rep,timeout)` toda vez que
   `Platform.run()` roda; `Platform._skip_completed_tasks()` (`platform.py:239,
   261-276`) só pula identidades cujo estado efetivo é **COMPLETED** — não
   consulta FAILED/ERROR. Ou seja: se o processo for re-executado (resume),
   qualquer identidade que não esteja COMPLETED — incluindo as que deram ERROR
   — ganha uma task nova, e a entrada antiga de ERROR permanece no
   `tasks.json` ao lado da nova (é exatamente o padrão de "2 entradas para o
   mesmo rep" observado). Isso é o mecanismo de recuperação de crash, não um
   retry dedicado a falhas.
3. **Não existe mop-up automático dedicado a FAILED/ERROR.** Não há nenhuma
   ocorrência de lógica de "mop-up" em `rv-platform`/`rv-experiment` (grep
   vazio). O termo só existe como vocabulário no nosso `rv_status.py`
   (linhas 20, 156, 172, 468) para reportar APKs com **0 tasks** — sinalização
   para ação humana, não automação. Reagendar identidades FAILED só acontece
   como efeito colateral de um resume manual do processo inteiro (item 2), não
   por uma varredura dedicada a falhas.
4. **Dedup por identidade é lógica local do `rv_status.py`, não do
   rv-platform.** `effective_entry()` (`rv_status.py:152-165`) agrupa entradas
   brutas por identidade e prioriza `DONE_STATES` (`{"COMPLETED"}`) sobre
   `ACTIVE_STATES` e `FAIL_STATES` — logo uma identidade com um ERROR mais
   antigo seguido de um COMPLETED mais novo (via resume) é contabilizada como
   **ok**, nunca como ok+fail ao mesmo tempo. Confirmado: nenhuma identidade
   FAILED reportada nos ciclos acima já teve um COMPLETED subsequente — os
   fails são genuínos e ainda sem substituição.

**Consequência prática / decisão pendente:** como não há retry nem mop-up
automático para FAILED, essas ~21 identidades (uma por container-tool, todas
concentradas na janela de arranque das 4 VMs) **vão ficar permanentemente
FAILED** a menos que o processo do `run_experiment.sh` seja re-executado
(resume) — o que só acontece automaticamente hoje se o processo morrer
(`health_check.py` auto-resume), não por causa de falhas isoladas dentro de um
processo vivo. **Não foi tomada nenhuma ação de config/retry/resume manual**
(regra: nunca alterar config de experimento sem autorização explícita). Ficará
para decisão do usuário se: (a) aceitar essas ~21 identidades como FAILED
definitivo (rate desprezível: 21/21681 ≈ 0.1% do total do experimento), ou
(b) agendar um mop-up manual dedicado a identidades FAILED (não só APKs com 0
task) antes da consolidação final (`consolidate_offline.sh`).

**Resume é o mecanismo único de recuperação — dois gatilhos diferentes:**
- **Processo morre** (`run_experiment.sh` cai) → `health_check.py` já faz
  **auto-resume automático** (até 12x/VM), sem ação humana. É o cenário que o
  monitor já cobre sozinho hoje.
- **Processo vive, mas tasks isoladas deram FAILED** (caso do boot-storm acima)
  → **sem gatilho automático**, porque nada morreu. Só corrige quando alguém
  re-executa manualmente o `run_experiment.sh`/`rv-experiment run` pro mesmo
  nome de experimento — aí sim as identidades não-COMPLETED (incluindo as
  FAILED) ganham task nova e tentam de novo (mecanismo do item 2 acima).
- **Decisão tomada:** não disparar esse resume manual agora, no meio do run.
  Ele fica amarrado à **tarefa #8** (mop-up + resume manual antes de rodar
  `consolidate_offline.sh`), cobrindo ao mesmo tempo as FAILED do boot-storm e
  os "APKs com 0 task" já sinalizados nos ciclos.

---

## Ciclo 2026-07-06 14:15:12

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 0.0% | 0 | 0 | 0 | 0 | — | — |
| m2 | RUNNING | 0.0% | 0 | 0 | 0 | 0 | — | — |
| m3 | RUNNING | 0.0% | 0 | 0 | 0 | 0 | — | — |
| m4 | RUNNING | 0.0% | 0 | 0 | 0 | 0 | — | — |

_Sem problemas neste ciclo._

## Ciclo 2026-07-06 14:16:24

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 0.1% | 1 | 0 | 0 | 1385 | ~4211.8h | — |
| m2 | RUNNING | 0.1% | 1 | 0 | 0 | 1385 | ~4211.4h | — |
| m3 | RUNNING | 0.1% | 1 | 0 | 0 | 1385 | ~4211.8h | — |
| m4 | RUNNING | 0.1% | 1 | 0 | 0 | 1286 | ~3911.0h | — |

**Problemas / eventos:**
- m1: 13 APK(s) com 0 task (esperam mop-up)
- m2: 13 APK(s) com 0 task (esperam mop-up)
- m3: 13 APK(s) com 0 task (esperam mop-up)
- m4: 12 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 14:27:48 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 0.4% | 15 | 7 | 0 | 5522 | ~811.5h | — |
| m2 | RUNNING | 0.4% | 15 | 5 | 0 | 5524 | ~892.9h | — |
| m3 | RUNNING | 0.4% | 16 | 6 | 0 | 5423 | ~796.9h | — |
| m4 | RUNNING | 0.4% | 19 | 3 | 0 | 5126 | ~753.3h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:7
- m1: 52 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:5
- m2: 52 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:5, install/adb:1
- m3: 51 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:2, install/adb:1
- m4: 48 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 15:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 1.5% | 72 | 9 | 0 | 5463 | ~254.2h | — |
| m2 | RUNNING | 1.4% | 71 | 5 | 0 | 5468 | ~271.2h | — |
| m3 | RUNNING | 1.4% | 73 | 6 | 0 | 5366 | ~256.0h | — |
| m4 | RUNNING | 1.5% | 76 | 3 | 0 | 5069 | ~241.9h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:7, install/adb:2
- m1: 52 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:5
- m2: 52 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:5, install/adb:1
- m3: 51 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:2, install/adb:1
- m4: 48 APK(s) com 0 task (esperam mop-up)
