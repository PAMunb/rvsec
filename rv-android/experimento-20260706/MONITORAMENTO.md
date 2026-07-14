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
- **2026-07-08 19:52 (local)** — **formato-padrão da tabela (v2.1)**: **uma tabela curta
  por VM** (`### mN`, granularidade por container `exp_00..03` + linha `total`) SEGUIDA de
  uma **tabela-resumo geral** (1 linha por VM + `TOTAL`). Motivo: a tabela única de 22 linhas
  (v2) quebrava em visualizadores que truncam tabelas altas (markdown válido, limitação do
  viewer). Colunas por container: `docker` + `timeout 60·180·300` (feito por passada, sempre
  nas 3 posições — passada não iniciada = `0`). `rv_status.py` exporta por container
  `by_timeout` (e `by_rep`, no JSON mas não renderizado) reduzidos a `{ok,err,done}` (lidos do
  `tasks.json` no host, sem `docker exec`). Consistência por container: `p60+p180+p300 = feito`.
  Documentado no `README.md`. `rv_status.py` redeployado nas 4 VMs.
- **2026-07-06 14:13–14:14 (local)** — run disparado nas 4 VMs (nohup). Passada
  TIMEOUT=60s iniciada; `run_experiment.sh` ALIVE e `exp_00..03` up em todas.
  Pids: m1=112698, m2=6958, m3=6482, m4=6535. (= 17:13–17:14 UTC na VM.)
- **2026-07-06 21:00–21:30 (local)** — m3/m4 ficaram com SSH inacessível por 3
  ciclos seguidos (20:00, 20:35, 21:00), porta 22 totalmente fechada mesmo com
  as instâncias `RUNNING` no `gcloud compute instances list` (m1/m2 respondiam
  normalmente na porta 22 no mesmo teste). Usuário reiniciou `m3-exp02` e
  `m4-exp02` manualmente via console web do gcloud (~21:29 UTC / 00:29 UTC na
  VM). Reboot confirmado (uptime ~1 min), porta 22 voltou a responder,
  containers antigos (`exp_00..03`, `rv-humanoid`, criados 17:14 UTC)
  apareceram `Exited` (mortos pelo reboot), `run_experiment.sh` não estava
  mais vivo em nenhuma das duas. Resume manual autorizado explicitamente pelo
  usuário: relançado `nohup ./scripts/run_experiment.sh {m3,m4} >> run.log 2>&1 &`
  (mesmo padrão do AUTO-RESUME do `health_check.py`) em cada VM. Confirmado
  às ~21:33 (local): `exp_00..03` + `rv-humanoid` `Up` em ambas. Resume idempotente
  via `tasks.json` — progresso anterior preservado, sem perda de dados.
  Causa-raiz do SSH_FALHOU não identificada (rede/subnet `10.128.15.x`
  diferente de m1/m2, ou falha de rede da própria VM) — não investigada a
  fundo, ação foi reset+resume, não diagnóstico completo.
- **2026-07-06 21:37–22:20 (local)** — containers individuais mortos por
  **OOM (`OOMKilled: true`, exit 137)** dentro do próprio limite de memória do
  container (10g, `docker-compose.gcp.yml`), não falta de RAM do host (m1
  tinha 23GB livres). Mortes: m1/`exp_01` (~19:01 local), m1/`exp_02`
  (~20:49 local), m1/`exp_00` (~21:37 local) — restou só `exp_03` vivo (~25%
  da capacidade); m2/`exp_00` (~21:39 local) — 3/4 vivos. Como
  `run_experiment.sh` continuava ALIVE (só bloqueado em
  `docker wait exp_00 exp_01 exp_02 exp_03`, esperando os 4 saírem antes de
  avançar de passada), o AUTO-RESUME do `health_check.py` não detectou nem
  agiu — esse cenário (container individual morto com o processo pai vivo)
  não é coberto pela lógica de auto-resume atual. Usuário autorizou
  explicitamente restart pontual: `docker start exp_00 exp_01 exp_02` em m1 e
  `docker start exp_00` em m2 (~22:1x local). Confirmado: os 4 containers
  voltaram `Up` e estáveis (>40s sem recair) em ambas as VMs. `docker start`
  não interfere no `docker wait` já em andamento no processo pai (que só
  observa a saída já registrada dos containers originais) — os containers
  reiniciados voltam a consultar o `tasks.json` compartilhado e pulam
  identidades já `COMPLETED`, mesmo mecanismo idempotente do resume de
  processo inteiro. Risco residual: se o limite de 10g for insuficiente para
  o restante do run, o mesmo padrão de OOM deve se repetir — não foi feita
  nenhuma alteração de `mem_limit` (mudança de config do experimento, exige
  autorização à parte).

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

## Correção ao diagnóstico — não é só boot-storm inicial (2026-07-06 16:00–19:03 local)

O diagnóstico acima ("zero falhas novas depois da janela de arranque") estava
**incompleto** — baseado só na primeira meia-hora do run. Com mais dados
(ciclo 16:00, ~700 tasks concluídas nas 4 VMs), confirmei via `tasks.json` que
`EmulatorError` continua ocorrendo **esporadicamente ao longo de todo o run**,
não só no arranque. Exemplo: `com.phpbg.easysync_25.apk` no `exp_02` da m2 —
30 tentativas (10 tools × 3 reps) entre 14:15 e 15:27, **27 COMPLETED / 3
ERROR** (monkey rep1 às 14:15 — arranque; `ares` rep1 às 15:11 e `fastbot`
rep3 às 15:21 — **1h e 1h10 depois do arranque**, sem relação com cold-start).
Mesmo padrão em outras APKs (`de.grobox.liberario_131.apk` na m3 falhou 3x
entre 15:34–15:44, mais de 1h20 após o arranque).

**Interpretação revisada:** existe uma taxa de fundo baixa e aparentemente
estável de falhas transitórias de boot/instalação de emulador (~3-7% por
janela), não limitada ao arranque simultâneo dos 16 containers. Cada
ocorrência é isolada — não vi nenhum caso de uma APK falhando em todas as
tools/reps (a maioria das identidades tem 27-29 de 30 tentativas OK); a
tendência global de fail rate está **caindo**, não crescendo (24% em 14:27 →
7.3% em 15:00 → 5.1% acumulado em 16:00, com taxa marginal do intervalo
15:00→16:00 em ~3.5%). Ou seja: não é uma regressão nem problema crescente,
mas também não é "só arranque" como eu tinha concluído antes — é ruído de
infraestrutura (contenção KVM/CPU/RAM com 4 emuladores paralelos por VM)
distribuído ao longo do run, dentro de faixa aceitável e sem sinal de piora.
Continua sem exigir ação: mesma decisão de tratar via mop-up manual (tarefa
#8) antes da consolidação.

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

## Ciclo 2026-07-06 16:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 3.4% | 174 | 14 | 0 | 5356 | ~135.9h | — |
| m2 | RUNNING | 3.3% | 173 | 10 | 0 | 5361 | ~139.7h | — |
| m3 | RUNNING | 3.4% | 175 | 9 | 0 | 5261 | ~136.4h | — |
| m4 | RUNNING | 3.6% | 182 | 5 | 0 | 4961 | ~126.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:11, install/adb:3
- m1: 48 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:7, install/adb:3
- m2: 48 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:6, install/adb:3
- m3: 47 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:3, install/adb:2
- m4: 44 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 17:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 5.4% | 278 | 19 | 0 | 5247 | ~101.9h | — |
| m2 | RUNNING | 5.2% | 268 | 22 | 0 | 5254 | ~104.5h | — |
| m3 | RUNNING | 5.3% | 275 | 15 | 0 | 5155 | ~102.6h | — |
| m4 | RUNNING | 5.7% | 286 | 9 | 0 | 4853 | ~94.9h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:11, install/adb:8
- m1: 44 APK(s) com 0 task (esperam mop-up)
- m2: erros → install/adb:11, emulator/boot:9, timeout:2
- m2: 44 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:7, install/adb:7, timeout:1
- m3: 43 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:4, emulator/boot:4, timeout:1
- m4: 40 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 18:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 7.2% | 381 | 21 | 0 | 5142 | ~86.6h | — |
| m2 | RUNNING | 7.0% | 366 | 22 | 0 | 5156 | ~90.0h | — |
| m3 | RUNNING | 6.9% | 355 | 22 | 0 | 5068 | ~91.0h | — |
| m4 | RUNNING | 7.8% | 385 | 16 | 0 | 4747 | ~80.2h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:12, install/adb:9
- m1: 1 APK(s) só-falha → com.flxrs.dankchat_40038.apk
- m1: 40 APK(s) com 0 task (esperam mop-up)
- m2: erros → install/adb:11, emulator/boot:9, timeout:2
- m2: 43 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:12, emulator/boot:7, timeout:3
- m3: 43 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:9, emulator/boot:6, timeout:1
- m4: 38 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 19:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 8.8% | 467 | 23 | 0 | 5054 | ~80.3h | — |
| m2 | RUNNING | 8.9% | 462 | 29 | 0 | 5053 | ~80.1h | — |
| m3 | RUNNING | 7.8% | 398 | 27 | 0 | 5020 | ~92.0h | — |
| m4 | RUNNING | 9.9% | 488 | 21 | 0 | 4639 | ~71.0h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:14, install/adb:9
- m1: 40 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:15, install/adb:12, timeout:2
- m2: 40 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:15, emulator/boot:7, timeout:5
- m3: 39 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:11, emulator/boot:9, timeout:1
- m4: 36 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 20:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 10.4% | 548 | 28 | 0 | 4968 | ~75.6h | — |
| m2 | RUNNING | 10.6% | 551 | 36 | 0 | 4957 | ~74.1h | — |
| m3 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |
| m4 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:14, install/adb:12, timeout:2
- m1: 37 APK(s) com 0 task (esperam mop-up)
- m1: container exp_01 docker=exited (ok=118 fail=4)
- m2: erros → emulator/boot:20, install/adb:14, timeout:2
- m2: 36 APK(s) com 0 task (esperam mop-up)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ssh timeout (sem ação)

## Ciclo 2026-07-06 20:35:46 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 11.3% | 592 | 35 | 0 | 4917 | ~73.4h | — |
| m2 | RUNNING | 11.6% | 607 | 38 | 0 | 4899 | ~71.1h | — |
| m3 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |
| m4 | RUNNING | 12.6% | 619 | 29 | 0 | 4500 | ~65.3h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:19, install/adb:14, timeout:2
- m1: 34 APK(s) com 0 task (esperam mop-up)
- m1: container exp_01 docker=exited (ok=118 fail=4)
- m2: erros → emulator/boot:20, install/adb:16, timeout:2
- m2: 36 APK(s) com 0 task (esperam mop-up)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → install/adb:13, emulator/boot:13, timeout:3
- m4: 32 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 21:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 11.8% | 621 | 35 | 0 | 4888 | ~72.8h | — |
| m2 | RUNNING | 12.3% | 645 | 39 | 0 | 4860 | ~69.4h | — |
| m3 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |
| m4 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:19, install/adb:14, timeout:2
- m1: 34 APK(s) com 0 task (esperam mop-up)
- m1: container exp_01 docker=exited (ok=118 fail=4)
- m1: container exp_02 docker=exited (ok=159 fail=16)
- m2: erros → emulator/boot:21, install/adb:16, timeout:2
- m2: 32 APK(s) com 0 task (esperam mop-up)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-06 21:41:52 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 12.5% | 659 | 35 | 0 | 4850 | ~73.1h | — |
| m2 | RUNNING | 13.0% | 682 | 40 | 0 | 4822 | ~69.9h | — |
| m3 | RUNNING | 12.3% | 641 | 29 | 0 | 4775 | ~74.6h | — |
| m4 | RUNNING | 14.2% | 707 | 26 | 0 | 4415 | ~63.0h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:19, install/adb:14, timeout:2
- m1: 33 APK(s) com 0 task (esperam mop-up)
- m1: container exp_00 docker=exited (ok=189 fail=9)
- m1: container exp_01 docker=exited (ok=118 fail=4)
- m1: container exp_02 docker=exited (ok=159 fail=16)
- m2: erros → emulator/boot:21, install/adb:16, timeout:3
- m2: 32 APK(s) com 0 task (esperam mop-up)
- m2: container exp_00 docker=exited (ok=171 fail=9)
- m3: erros → install/adb:15, emulator/boot:8, timeout:6
- m3: 32 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:13, emulator/boot:11, timeout:2
- m4: 28 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 22:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 12.7% | 668 | 35 | 0 | 4841 | ~74.2h | — |
| m2 | RUNNING | 13.5% | 708 | 40 | 0 | 4796 | ~69.1h | — |
| m3 | RUNNING | 12.5% | 670 | 10 | 0 | 4765 | ~75.5h | — |
| m4 | RUNNING | 14.4% | 737 | 6 | 0 | 4405 | ~63.9h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:19, install/adb:14, timeout:2
- m1: 33 APK(s) com 0 task (esperam mop-up)
- m1: container exp_00 docker=exited (ok=189 fail=9)
- m1: container exp_01 docker=exited (ok=118 fail=4)
- m1: container exp_02 docker=exited (ok=159 fail=16)
- m2: erros → emulator/boot:21, install/adb:16, timeout:3
- m2: 32 APK(s) com 0 task (esperam mop-up)
- m2: container exp_00 docker=exited (ok=171 fail=9)
- m3: erros → emulator/boot:5, install/adb:5
- m3: 31 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:5, install/adb:1
- m4: 28 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 22:14:02 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 12.8% | 680 | 29 | 0 | 4835 | ~75.0h | — |
| m2 | RUNNING | 13.8% | 728 | 38 | 0 | 4778 | ~68.6h | — |
| m3 | RUNNING | 12.9% | 694 | 10 | 0 | 4741 | ~74.1h | — |
| m4 | RUNNING | 14.9% | 760 | 8 | 0 | 4380 | ~62.7h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:16, install/adb:11, timeout:2
- m1: 33 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:20, install/adb:16, timeout:2
- m2: 31 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:5, install/adb:5
- m3: 31 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:5, install/adb:3
- m4: 28 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-06 23:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 14.0% | 752 | 23 | 0 | 4769 | ~72.4h | — |
| m2 | RUNNING | 14.9% | 790 | 38 | 0 | 4716 | ~67.0h | — |
| m3 | RUNNING | 14.5% | 773 | 16 | 0 | 4656 | ~69.5h | — |
| m4 | RUNNING | 16.6% | 840 | 13 | 0 | 4295 | ~59.3h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:18, install/adb:5
- m1: 30 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:19, install/adb:18, timeout:1
- m2: 30 APK(s) com 0 task (esperam mop-up)
- m2: container exp_03 docker=exited (ok=186 fail=12)
- m3: erros → install/adb:11, emulator/boot:5
- m3: 29 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:8, install/adb:5
- m4: 24 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-07 00:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 15.7% | 834 | 35 | 0 | 4675 | ~68.7h | — |
| m2 | RUNNING | 16.3% | 861 | 44 | 0 | 4639 | ~65.5h | — |
| m3 | RUNNING | 16.3% | 868 | 20 | 0 | 4557 | ~65.5h | — |
| m4 | RUNNING | 18.7% | 942 | 21 | 0 | 4185 | ~55.5h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:30, install/adb:5
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → install/adb:22, emulator/boot:21, timeout:1
- m2: 27 APK(s) com 0 task (esperam mop-up)
- m2: container exp_02 docker=exited (ok=222 fail=17)
- m2: container exp_03 docker=exited (ok=186 fail=12)
- m3: erros → install/adb:14, emulator/boot:6
- m3: 27 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m4: erros → install/adb:11, emulator/boot:10
- m4: 20 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-07 01:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 16.8% | 891 | 38 | 0 | 4615 | ~68.4h | — |
| m2 | RUNNING | 17.4% | 916 | 47 | 0 | 4581 | ~65.5h | — |
| m3 | RUNNING | 17.9% | 947 | 26 | 0 | 4472 | ~63.3h | — |
| m4 | RUNNING | 20.8% | 1046 | 27 | 0 | 4075 | ~52.3h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:30, install/adb:8
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:24, install/adb:22, timeout:1
- m2: 25 APK(s) com 0 task (esperam mop-up)
- m2: container exp_02 docker=exited (ok=222 fail=17)
- m2: container exp_03 docker=exited (ok=186 fail=12)
- m3: erros → install/adb:16, emulator/boot:10
- m3: 24 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m4: erros → install/adb:16, emulator/boot:11
- m4: 1 APK(s) só-falha → ua.acclorite.book_story_14.apk
- m4: 16 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-07 02:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 17.8% | 946 | 43 | 0 | 4555 | ~68.0h | — |
| m2 | RUNNING | 18.4% | 971 | 49 | 0 | 4524 | ~65.5h | — |
| m3 | RUNNING | 19.4% | 1026 | 32 | 0 | 4387 | ~61.2h | — |
| m4 | RUNNING | 22.9% | 1149 | 32 | 0 | 3967 | ~49.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:33, install/adb:10
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:25, install/adb:23, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m2: container exp_02 docker=exited (ok=222 fail=17)
- m2: container exp_03 docker=exited (ok=186 fail=12)
- m3: erros → install/adb:17, emulator/boot:15
- m3: 21 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m4: erros → install/adb:19, emulator/boot:13
- m4: 15 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-07 03:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 19.0% | 1001 | 51 | 0 | 4492 | ~67.3h | — |
| m2 | RUNNING | 19.4% | 1017 | 61 | 0 | 4466 | ~65.3h | — |
| m3 | RUNNING | 21.0% | 1106 | 37 | 0 | 4302 | ~59.4h | — |
| m4 | RUNNING | 24.9% | 1243 | 38 | 0 | 3867 | ~47.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:38, install/adb:13
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:35, install/adb:25, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:20, emulator/boot:17
- m3: 18 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m4: erros → install/adb:24, emulator/boot:14
- m4: 12 APK(s) com 0 task (esperam mop-up)
- m4: container exp_01 docker=exited (ok=306 fail=9)

## Ciclo 2026-07-07 04:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 20.0% | 1059 | 52 | 0 | 4433 | ~66.9h | — |
| m2 | RUNNING | 20.5% | 1075 | 63 | 0 | 4406 | ~64.9h | — |
| m3 | RUNNING | 22.4% | 1185 | 37 | 0 | 4223 | ~58.0h | — |
| m4 | RUNNING | 26.6% | 1322 | 45 | 0 | 3781 | ~46.4h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:39, install/adb:13
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:35, install/adb:27, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:20, emulator/boot:17
- m3: 16 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m3: container exp_02 docker=exited (ok=319 fail=10)
- m4: erros → install/adb:27, emulator/boot:18
- m4: 9 APK(s) com 0 task (esperam mop-up)
- m4: container exp_01 docker=exited (ok=306 fail=9)

## Ciclo 2026-07-07 05:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 21.1% | 1109 | 61 | 0 | 4374 | ~66.4h | — |
| m2 | RUNNING | 21.6% | 1128 | 71 | 0 | 4345 | ~64.4h | — |
| m3 | RUNNING | 23.5% | 1242 | 38 | 0 | 4165 | ~57.8h | — |
| m4 | RUNNING | 28.0% | 1395 | 47 | 0 | 3706 | ~45.7h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:46, install/adb:15
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:42, install/adb:28, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:21, emulator/boot:17
- m3: 14 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=212 fail=4)
- m3: container exp_02 docker=exited (ok=319 fail=10)
- m4: erros → install/adb:28, emulator/boot:19
- m4: 6 APK(s) com 0 task (esperam mop-up)
- m4: container exp_01 docker=exited (ok=306 fail=9)
- m4: container exp_02 docker=exited (ok=360 fail=9)

## Ciclo 2026-07-07 06:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 22.1% | 1165 | 63 | 0 | 4316 | ~66.0h | — |
| m2 | RUNNING | 22.7% | 1184 | 74 | 0 | 4286 | ~63.9h | — |
| m3 | RUNNING | 24.7% | 1318 | 29 | 0 | 4098 | ~57.1h | — |
| m4 | RUNNING | 29.3% | 1468 | 39 | 0 | 3641 | ~45.4h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:46, install/adb:17
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:43, install/adb:30, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:16, emulator/boot:13
- m3: 13 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:22, emulator/boot:17
- m4: 4 APK(s) com 0 task (esperam mop-up)

## Ciclo 2026-07-07 07:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 22.9% | 1199 | 69 | 0 | 4276 | ~66.7h | — |
| m2 | RUNNING | 23.7% | 1236 | 79 | 0 | 4229 | ~63.6h | — |
| m3 | RUNNING | 26.6% | 1415 | 35 | 0 | 3995 | ~54.5h | — |
| m4 | RUNNING | 31.2% | 1561 | 44 | 0 | 3543 | ~43.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:51, install/adb:18
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m1: container exp_01 docker=exited (ok=244 fail=13)
- m2: erros → emulator/boot:46, install/adb:32, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:19, emulator/boot:16
- m3: 10 APK(s) com 0 task (esperam mop-up)
- m4: erros → install/adb:26, emulator/boot:18
- m4: 2 APK(s) com 0 task (esperam mop-up)
- m4: container exp_00 docker=exited (ok=413 fail=16)
- m4: container exp_03 docker=exited (ok=410 fail=19)

## Ciclo 2026-07-07 08:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 23.6% | 1241 | 70 | 0 | 4233 | ~67.1h | — |
| m2 | RUNNING | 24.8% | 1293 | 84 | 0 | 4167 | ~62.9h | — |
| m3 | RUNNING | 27.9% | 1483 | 37 | 0 | 3925 | ~53.6h | — |
| m4 | RUNNING | 32.3% | 1616 | 46 | 0 | 3486 | ~43.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:51, install/adb:19
- m1: 28 APK(s) com 0 task (esperam mop-up)
- m1: container exp_01 docker=exited (ok=244 fail=13)
- m2: erros → emulator/boot:50, install/adb:33, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:21, emulator/boot:16
- m3: 8 APK(s) com 0 task (esperam mop-up)
- m3: container exp_01 docker=exited (ok=251 fail=6)
- m3: container exp_03 docker=exited (ok=412 fail=17)
- m4: erros → install/adb:27, emulator/boot:19
- m4: 1 APK(s) com 0 task (esperam mop-up)
- m4: container exp_00 docker=exited (ok=413 fail=16)
- m4: container exp_02 docker=exited (ok=421 fail=8)
- m4: container exp_03 docker=exited (ok=410 fail=19)

## Ciclo 2026-07-07 08:59:53 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |
| m2 | RUNNING | 25.9% | 1351 | 84 | 0 | 4109 | ~62.4h | — |
| m3 | RUNNING | 28.7% | 1526 | 36 | 0 | 3883 | ~54.2h | — |
| m4 | RUNNING | 32.9% | 1646 | 47 | 0 | 3455 | ~44.5h | — |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: erros → emulator/boot:50, install/adb:33, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:21, emulator/boot:15
- m3: 7 APK(s) com 0 task (esperam mop-up)
- m3: container exp_03 docker=exited (ok=412 fail=17)
- m4: erros → install/adb:26, emulator/boot:21
- m4: container exp_00 docker=exited (ok=413 fail=16)
- m4: container exp_03 docker=exited (ok=410 fail=19)

## Ciclo 2026-07-07 09:00:02 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | SSH_FALHOU | 0.0% | ? | ? | ? | ? | — | — |
| m2 | RUNNING | 25.9% | 1351 | 84 | 0 | 4109 | ~62.4h | — |
| m3 | RUNNING | 28.7% | 1526 | 36 | 0 | 3883 | ~54.2h | — |
| m4 | RUNNING | 32.9% | 1646 | 47 | 0 | 3455 | ~44.5h | — |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: erros → emulator/boot:50, install/adb:33, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → install/adb:21, emulator/boot:15
- m3: 7 APK(s) com 0 task (esperam mop-up)
- m3: container exp_03 docker=exited (ok=412 fail=17)
- m4: erros → install/adb:26, emulator/boot:21
- m4: container exp_00 docker=exited (ok=413 fail=16)
- m4: container exp_03 docker=exited (ok=410 fail=19)

## Evento 2026-07-07 ~09:00-09:08 (local) — OOM m3/m4 + reboot+resume m1

- **m3/m4 OOM restart (09:00 local, autorização permanente)**: reiniciados `docker start` — m3/exp_00 (137), m3/exp_01 (137), m4/exp_02 (137). Todos `Up` em seguida. Containers Exited(0) na varredura (m3/exp_03, m4/exp_00, m4/exp_03) NÃO reiniciados: conclusão limpa da passada 60s (run_experiment.sh vivo, relançado na próxima passada).
- **m1 reboot + resume (09:04-09:08 local, autorizado pelo usuário)**: SSH port 22 sem resposta (banner timeout) em `gcloud ssh` e ssh puro, instância `RUNNING`. Reset via `gcloud compute instances reset m1-exp02` às 09:04:55 local (12:04:55 UTC). SSH voltou ~09:05; `uptime` confirmou `up 0 min`; containers `Exited(255)` (daemon-killed no boot). Resume: `nohup ./scripts/run_experiment.sh m1` (PID 1730). 4/4 exp + rv-humanoid `Up` às 09:07:55 local.

## Ciclo 2026-07-07 10:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 25.8% | 1362 | 68 | 0 | 4114 | ~65.5h | — |
| m2 | RUNNING | 26.9% | 1398 | 96 | 0 | 4050 | ~61.7h | — |
| m3 | RUNNING | 29.6% | 1584 | 27 | 0 | 3834 | ~54.2h | — |
| m4 | RUNNING | 33.5% | 1678 | 48 | 0 | 3422 | ~45.1h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:48, install/adb:20
- m1: 26 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:61, install/adb:34, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:16, install/adb:11
- m3: 5 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=461 fail=1)
- m3: container exp_03 docker=exited (ok=412 fail=17)
- m4: erros → emulator/boot:26, install/adb:22

## Ciclo 2026-07-07 10:06:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 26.0% | 1371 | 69 | 0 | 4104 | ~65.2h | — |
| m2 | RUNNING | 27.0% | 1403 | 96 | 0 | 4045 | ~61.7h | — |
| m3 | RUNNING | 29.7% | 1590 | 28 | 0 | 3827 | ~54.1h | — |
| m4 | RUNNING | 33.6% | 1681 | 49 | 0 | 3418 | ~45.2h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:48, install/adb:21
- m1: 26 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:61, install/adb:34, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:16, install/adb:12
- m3: 5 APK(s) com 0 task (esperam mop-up)
- m3: container exp_03 docker=exited (ok=412 fail=17)
- m4: erros → emulator/boot:27, install/adb:22

## Ciclo 2026-07-07 11:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 27.8% | 1463 | 77 | 0 | 4004 | ~61.8h | — |
| m2 | RUNNING | 28.0% | 1454 | 97 | 0 | 3993 | ~61.2h | — |
| m3 | RUNNING | 30.6% | 1631 | 38 | 0 | 3776 | ~53.8h | — |
| m4 | RUNNING | 34.7% | 1736 | 52 | 0 | 3360 | ~44.7h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:52, install/adb:25
- m1: 22 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:61, install/adb:35, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:26, install/adb:12
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:27, install/adb:25

## Ciclo 2026-07-07 11:02:47 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 27.9% | 1468 | 77 | 0 | 3999 | ~61.6h | — |
| m2 | RUNNING | 28.0% | 1456 | 98 | 0 | 3990 | ~61.1h | — |
| m3 | RUNNING | 30.7% | 1633 | 38 | 0 | 3774 | ~53.8h | — |
| m4 | RUNNING | 34.8% | 1739 | 52 | 0 | 3357 | ~44.6h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:52, install/adb:25
- m1: 22 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:61, install/adb:36, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:26, install/adb:12
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:27, install/adb:25

## Ciclo 2026-07-07 11:59:34 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 29.8% | 1567 | 84 | 0 | 3893 | ~58.4h | — |
| m2 | RUNNING | 29.0% | 1501 | 109 | 0 | 3934 | ~60.5h | — |
| m3 | RUNNING | 31.7% | 1686 | 40 | 0 | 3719 | ~53.4h | — |
| m4 | RUNNING | 35.9% | 1790 | 57 | 0 | 3301 | ~44.3h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:52, install/adb:32
- m1: 19 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:71, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:26, install/adb:14
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:29, install/adb:28

## Ciclo 2026-07-07 12:00:01 (local)

| VM | estado | % | ok | fail | active | remaining | ETA | ação |
|----|--------|---|----|------|--------|-----------|-----|------|
| m1 | RUNNING | 29.8% | 1567 | 84 | 0 | 3893 | ~58.4h | — |
| m2 | RUNNING | 29.0% | 1501 | 109 | 0 | 3934 | ~60.5h | — |
| m3 | RUNNING | 31.7% | 1686 | 40 | 0 | 3719 | ~53.4h | — |
| m4 | RUNNING | 35.9% | 1791 | 57 | 0 | 3300 | ~44.2h | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:52, install/adb:32
- m1: 19 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:71, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:26, install/adb:14
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:29, install/adb:28

## Ciclo 2026-07-07 12:23:32 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.609 | 88 | 1.697 | 5.544 | 30,6 % | — |
| m2 | RUNNING | 1.522 | 109 | 1.631 | 5.544 | 29,4 % | — |
| m3 | RUNNING | 1.708 | 40 | 1.748 | 5.445 | 32,1 % | — |
| m4 | RUNNING | 1.807 | 66 | 1.873 | 5.148 | 36,4 % | — |
| **Total** | — | **6.646** | **303** | **6.949** | **21.681** | **32,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:53, install/adb:35
- m1: 18 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:71, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:26, install/adb:14
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:38, install/adb:28

## Ciclo 2026-07-07 13:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.670 | 94 | 1.764 | 5.544 | 31,8 % | — |
| m2 | RUNNING | 1.554 | 109 | 1.663 | 5.544 | 30,0 % | — |
| m3 | RUNNING | 1.743 | 42 | 1.785 | 5.445 | 32,8 % | — |
| m4 | RUNNING | 1.841 | 69 | 1.910 | 5.148 | 37,1 % | — |
| **Total** | — | **6.808** | **314** | **7.122** | **21.681** | **32,8 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:57, install/adb:37
- m1: 15 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:71, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:27, install/adb:15
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:38, install/adb:31

## Ciclo 2026-07-07 13:04:38 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.677 | 94 | 1.771 | 5.544 | 31,9 % | — |
| m2 | RUNNING | 1.558 | 109 | 1.667 | 5.544 | 30,1 % | — |
| m3 | RUNNING | 1.745 | 45 | 1.790 | 5.445 | 32,9 % | — |
| m4 | RUNNING | 1.845 | 69 | 1.914 | 5.148 | 37,2 % | — |
| **Total** | — | **6.825** | **317** | **7.142** | **21.681** | **32,9 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:57, install/adb:37
- m1: 15 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:71, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:30, install/adb:15
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:38, install/adb:31

## Ciclo 2026-07-07 14:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.775 | 98 | 1.873 | 5.544 | 33,8 % | — |
| m2 | RUNNING | 1.597 | 115 | 1.712 | 5.544 | 30,9 % | — |
| m3 | RUNNING | 1.794 | 51 | 1.845 | 5.445 | 33,9 % | — |
| m4 | RUNNING | 1.899 | 70 | 1.969 | 5.148 | 38,2 % | — |
| **Total** | — | **7.065** | **334** | **7.399** | **21.681** | **34,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:58, install/adb:40
- m1: 13 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:75, install/adb:39, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m2: container exp_00 docker=exited (ok=429 fail=25)
- m3: erros → emulator/boot:34, install/adb:17
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:38, install/adb:32

## Ciclo 2026-07-07 14:01:46 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.778 | 98 | 1.876 | 5.544 | 33,8 % | — |
| m2 | RUNNING | 1.597 | 116 | 1.713 | 5.544 | 30,9 % | — |
| m3 | RUNNING | 1.796 | 51 | 1.847 | 5.445 | 33,9 % | — |
| m4 | RUNNING | 1.900 | 70 | 1.970 | 5.148 | 38,3 % | — |
| **Total** | — | **7.071** | **335** | **7.406** | **21.681** | **34,2 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:58, install/adb:40
- m1: 12 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:76, install/adb:39, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:34, install/adb:17
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:38, install/adb:32

## Ciclo 2026-07-07 14:58:54 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.877 | 101 | 1.978 | 5.544 | 35,7 % | — |
| m2 | RUNNING | 1.639 | 116 | 1.755 | 5.544 | 31,7 % | — |
| m3 | RUNNING | 1.850 | 51 | 1.901 | 5.445 | 34,9 % | — |
| m4 | RUNNING | 1.949 | 78 | 2.027 | 5.148 | 39,4 % | — |
| **Total** | — | **7.315** | **346** | **7.661** | **21.681** | **35,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:59, install/adb:42
- m1: 10 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:78, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:34, install/adb:17
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:46, install/adb:32

## Ciclo 2026-07-07 15:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.879 | 101 | 1.980 | 5.544 | 35,7 % | — |
| m2 | RUNNING | 1.640 | 116 | 1.756 | 5.544 | 31,7 % | — |
| m3 | RUNNING | 1.850 | 51 | 1.901 | 5.445 | 34,9 % | — |
| m4 | RUNNING | 1.950 | 78 | 2.028 | 5.148 | 39,4 % | — |
| **Total** | — | **7.319** | **346** | **7.665** | **21.681** | **35,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:59, install/adb:42
- m1: 10 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:78, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:34, install/adb:17
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:46, install/adb:32

## Ciclo 2026-07-07 15:55:53 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.959 | 107 | 2.066 | 5.544 | 37,3 % | — |
| m2 | RUNNING | 1.661 | 117 | 1.778 | 5.544 | 32,1 % | — |
| m3 | RUNNING | 1.898 | 63 | 1.961 | 5.445 | 36,0 % | — |
| m4 | RUNNING | 2.003 | 80 | 2.083 | 5.148 | 40,5 % | — |
| **Total** | — | **7.521** | **367** | **7.888** | **21.681** | **36,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:63, install/adb:44
- m1: 6 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:79, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:44, install/adb:19
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:46, install/adb:34

## Ciclo 2026-07-07 16:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 1.965 | 106 | 2.071 | 5.544 | 37,4 % | — |
| m2 | RUNNING | 1.665 | 117 | 1.782 | 5.544 | 32,1 % | — |
| m3 | RUNNING | 1.901 | 63 | 1.964 | 5.445 | 36,1 % | — |
| m4 | RUNNING | 2.007 | 80 | 2.087 | 5.148 | 40,5 % | — |
| **Total** | — | **7.538** | **366** | **7.904** | **21.681** | **36,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:62, install/adb:44
- m1: 6 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:79, install/adb:37, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:44, install/adb:19
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:46, install/adb:34

## Diagnóstico 2026-07-07 ~16:00 (local) — por que m2 está atrás (e por que NÃO rebootar)

**Pergunta:** m2 parece estranha, bem atrás — não seria caso de rebootar a VM?

**Método (o jeito CERTO de diagnosticar — não inferir progresso pelo rótulo da passada):**
`rv_status.py --json` → `by_timeout` (COMPLETED/ERROR por 60/180/300) + `done` total + `zero_task_apks`; `docker stats` (CPU/MEM); `docker logs --tail` (coverage ao vivo); cruzar nome de APK zero-task com o log (`docker logs <c> | grep <apk>`).

**Números reais (16:00 local):**

| VM | done total | 60s (ok+err) | 180s (ok+err) | fail | zero-task |
|----|-----------:|-------------:|--------------:|-----:|----------:|
| m1 | 2.080 | 1.580 | 500 | 104 | 6 |
| **m2** | **1.788** | **1.051** | 737 | **119** | **23** |
| m3 | 1.971 | 1.653 | 318 | 63 | 4 |
| m4 | 2.093 | 1.716 | 377 | 80 | 0 |

**Conclusão (corrigida — a 1ª análise estava errada):**
- m2 está genuinamente ATRÁS (menor `done` total: 1.788), NÃO adiantada. A 1ª leitura ("m2 terminou a 60s e faz trabalho lento na 180s") foi FALSA: o `by_timeout` mostra só 1.051 na passada 60s vs 1.580-1.716 das outras. m2 está na 180s **com a 60s incompleta** — o `run_experiment.sh` avançou de passada (05:32) sem terminar a 60s (corte por OOM na madrugada). **Estar numa passada mais adiantada ≠ mais progresso.**
- Causa real do atraso: (1) maior carga de falha (119 fail, 79 emulator/boot — mais que todas) → throughput menor (62 tasks/h); (2) absorveu a pior janela de OOM da madrugada e **nunca foi rebootada** (as outras 3 foram, reganharam terreno); (3) ainda mói os APKs iniciais, não chegou nos ~23 do fim da lista.
- Os 23 zero-task de m2 são **pendentes/não-alcançados** (confirmado: `com.kin.easynotes`, `com.kylecorry.trail_sense`, `com.learntube.app` não aparecem no log — sem tentativa de install), NÃO uninstalláveis. Serão processados conforme m2 avança + no mop-up final.
- m2 NÃO está travada: `docker stats` = CPU 92-414% nos 4 containers; logs ao vivo = exp_01 coletando coverage a 58%.

**Decisão: NÃO rebootar.** Reboot não conserta taxa de falha do batch (intrínseca ao APK/AVD) e perde trabalho em voo. Buracos são preenchidos pelo mop-up (re-roda run_experiment.sh). Reboot só se o usuário quiser estado limpo (upside fraco: emulador fresco após 28h uptime; custo certo: perde in-flight).

## Ciclo 2026-07-07 16:52:33 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.050 | 99 | 2.149 | 5.544 | 38,8 % | — |
| m2 | RUNNING | 1.694 | 118 | 1.812 | 5.544 | 32,7 % | — |
| m3 | RUNNING | 1.947 | 67 | 2.014 | 5.445 | 37,0 % | — |
| m4 | RUNNING | 2.050 | 92 | 2.142 | 5.148 | 41,6 % | — |
| **Total** | — | **7.741** | **376** | **8.117** | **21.681** | **37,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:59, install/adb:40
- m1: 4 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:83, install/adb:34, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:44, install/adb:23
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:57, install/adb:35

**Ações (16:51 local):** varredura SSH detectou 2 containers OOM (Exit 137) → restart imediato: m1/exp_01 (morto ~16:46 UTC) e m2/exp_03 (morto ~16:14 UTC). Ambos `docker start` OK, OOMKilled=false Status=running. run_experiment.sh vivo nas 4 VMs. Todos os containers Up (4/4 exp + humanoid) nas 4 VMs após restart.

## Ciclo 2026-07-07 17:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.061 | 97 | 2.158 | 5.544 | 38,9 % | — |
| m2 | RUNNING | 1.701 | 118 | 1.819 | 5.544 | 32,8 % | — |
| m3 | RUNNING | 1.953 | 67 | 2.020 | 5.445 | 37,1 % | — |
| m4 | RUNNING | 2.057 | 93 | 2.150 | 5.148 | 41,8 % | — |
| **Total** | — | **7.772** | **375** | **8.147** | **21.681** | **37,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:58, install/adb:39
- m1: 4 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:82, install/adb:35, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:44, install/adb:23
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:57, install/adb:36

## Ciclo 2026-07-07 17:51:05 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.131 | 88 | 2.219 | 5.544 | 40,0 % | — |
| m2 | RUNNING | 1.740 | 116 | 1.856 | 5.544 | 33,5 % | — |
| m3 | RUNNING | 1.993 | 77 | 2.070 | 5.445 | 38,0 % | — |
| m4 | RUNNING | 2.107 | 94 | 2.201 | 5.148 | 42,8 % | — |
| **Total** | — | **7.971** | **375** | **8.346** | **21.681** | **38,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:34
- m1: 2 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:83, install/adb:32, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:54, install/adb:23
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:58, install/adb:36

**Ações (17:50 local):** varredura SSH detectou 1 container OOM (Exit 137): m1/exp_03 (morto ~20:01 UTC / 17:01 local) → restart imediato, `docker start` OK, OOMKilled=false Status=running. Demais containers Up nas 4 VMs; run_experiment.sh vivo nas 4. m1: 2º container distinto a OOMar no ciclo anterior (exp_01 às 16:46) — sem recorrência do MESMO container.

## Ciclo 2026-07-07 18:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.143 | 88 | 2.231 | 5.544 | 40,2 % | — |
| m2 | RUNNING | 1.748 | 115 | 1.863 | 5.544 | 33,6 % | — |
| m3 | RUNNING | 2.001 | 78 | 2.079 | 5.445 | 38,2 % | — |
| m4 | RUNNING | 2.115 | 94 | 2.209 | 5.148 | 42,9 % | — |
| **Total** | — | **8.007** | **375** | **8.382** | **21.681** | **38,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:34
- m1: 2 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:83, install/adb:31, timeout:1
- m2: 23 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:54, install/adb:24
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:58, install/adb:36

## Ciclo 2026-07-07 18:48:58 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.208 | 83 | 2.291 | 5.544 | 41,3 % | — |
| m2 | RUNNING | 1.790 | 121 | 1.911 | 5.544 | 34,5 % | — |
| m3 | RUNNING | 2.045 | 80 | 2.125 | 5.445 | 39,0 % | — |
| m4 | RUNNING | 2.156 | 103 | 2.259 | 5.148 | 43,9 % | — |
| **Total** | — | **8.199** | **387** | **8.586** | **21.681** | **39,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:53, install/adb:28, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:88, install/adb:32, timeout:1
- m2: 22 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:54, install/adb:26
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:67, install/adb:36

**Ações (18:48 local):** varredura SSH detectou 1 container OOM (Exit 137): m1/exp_03 (morto ~21:28 UTC / 18:28 local) → restart imediato OK (OOMKilled=false, running). **ATENÇÃO: m1/exp_03 OOMou 2 ciclos seguidos (17:01 e 18:28 local).** Ainda abaixo do gatilho de 3+ consecutivos, mas é reincidência do MESMO container — vigiar no próximo ciclo; se repetir será sinalizado com ênfase. Demais containers Up nas 4 VMs; run_experiment.sh vivo nas 4.

## Ciclo 2026-07-07 19:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.219 | 81 | 2.300 | 5.544 | 41,5 % | — |
| m2 | RUNNING | 1.801 | 122 | 1.923 | 5.544 | 34,7 % | — |
| m3 | RUNNING | 2.055 | 80 | 2.135 | 5.445 | 39,2 % | — |
| m4 | RUNNING | 2.165 | 104 | 2.269 | 5.148 | 44,1 % | — |
| **Total** | — | **8.240** | **387** | **8.627** | **21.681** | **39,8 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:51, install/adb:28, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m1: container exp_00 docker=exited (ok=580 fail=13)
- m1: container exp_02 docker=exited (ok=566 fail=33)
- m2: erros → emulator/boot:88, install/adb:33, timeout:1
- m2: 22 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:54, install/adb:26
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:68, install/adb:36

## Ciclo 2026-07-07 19:46:56 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.240 | 71 | 2.311 | 5.544 | 41,7 % | — |
| m2 | RUNNING | 1.843 | 124 | 1.967 | 5.544 | 35,5 % | — |
| m3 | RUNNING | 2.087 | 84 | 2.171 | 5.445 | 39,9 % | — |
| m4 | RUNNING | 2.210 | 105 | 2.315 | 5.148 | 45,0 % | — |
| **Total** | — | **8.380** | **384** | **8.764** | **21.681** | **40,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:51, install/adb:18, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:89, install/adb:34, timeout:1
- m2: 22 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:57, install/adb:27
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:68, install/adb:37

**Ações (19:46 local):** varredura SSH detectou 1 container OOM (Exit 137): m3/exp_00 (morto ~22:09 UTC / 19:09 local) → restart imediato OK (OOMKilled=false, running). m1 recriou todos os 5 containers ~19:03 local (Up 43 min) — transição normal de passada via docker-compose (o cron das 19:00 pegou exp_00/exp_02 exited no meio da transição). m1/exp_03 NÃO reincidiu (Up 43 min, saudável) — encerra a vigilância de 2 ciclos. Demais containers Up nas 4 VMs; run_experiment.sh vivo nas 4.

## Ciclo 2026-07-07 20:00:02 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.249 | 73 | 2.322 | 5.544 | 41,9 % | — |
| m2 | RUNNING | 1.855 | 126 | 1.981 | 5.544 | 35,7 % | — |
| m3 | RUNNING | 2.095 | 86 | 2.181 | 5.445 | 40,1 % | — |
| m4 | RUNNING | 2.222 | 105 | 2.327 | 5.148 | 45,2 % | — |
| **Total** | — | **8.421** | **390** | **8.811** | **21.681** | **40,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:17, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:91, install/adb:34, timeout:1
- m2: 22 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:59, install/adb:27
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:68, install/adb:37

## Ciclo 2026-07-07 20:44:40 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.292 | 73 | 2.365 | 5.544 | 42,7 % | — |
| m2 | RUNNING | 1.890 | 136 | 2.026 | 5.544 | 36,5 % | — |
| m3 | RUNNING | 2.132 | 87 | 2.219 | 5.445 | 40,8 % | — |
| m4 | RUNNING | 2.261 | 111 | 2.372 | 5.148 | 46,1 % | — |
| **Total** | — | **8.575** | **407** | **8.982** | **21.681** | **41,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:17, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:97, install/adb:38, timeout:1
- m2: 21 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:60, install/adb:27
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:70, install/adb:41

**Ações (20:44 local):** varredura SSH — nenhuma anomalia. 4/4 exp + humanoid Up nas 4 VMs; run_experiment.sh vivo nas 4. Nenhum OOM neste ciclo (1º ciclo sem restart desde ~16:00). m3/exp_00 (restartado 19:09) saudável Up 57 min.

## Ciclo 2026-07-07 21:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.307 | 73 | 2.380 | 5.544 | 42,9 % | — |
| m2 | RUNNING | 1.903 | 136 | 2.039 | 5.544 | 36,8 % | — |
| m3 | RUNNING | 2.146 | 88 | 2.234 | 5.445 | 41,0 % | — |
| m4 | RUNNING | 2.273 | 113 | 2.386 | 5.148 | 46,3 % | — |
| **Total** | — | **8.629** | **410** | **9.039** | **21.681** | **41,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:17, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:97, install/adb:38, timeout:1
- m2: 21 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:60, install/adb:28
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:72, install/adb:41

## Ciclo 2026-07-07 21:42:37 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.346 | 76 | 2.422 | 5.544 | 43,7 % | — |
| m2 | RUNNING | 1.938 | 141 | 2.079 | 5.544 | 37,5 % | — |
| m3 | RUNNING | 2.184 | 92 | 2.276 | 5.445 | 41,8 % | — |
| m4 | RUNNING | 2.309 | 121 | 2.430 | 5.148 | 47,2 % | — |
| **Total** | — | **8.777** | **430** | **9.207** | **21.681** | **42,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:57, install/adb:17, timeout:2
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:100, install/adb:40, timeout:1
- m2: 21 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:62, install/adb:30
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:77, install/adb:44

**Ações (21:42 local):** varredura SSH — nenhuma anomalia. 4/4 exp + humanoid Up nas 4 VMs; run_experiment.sh vivo nas 4. Nenhum OOM (2º ciclo limpo consecutivo). m1 saudável Up 3h (passada iniciada ~18:42).

## Ciclo 2026-07-07 22:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.361 | 81 | 2.442 | 5.544 | 44,0 % | — |
| m2 | RUNNING | 1.954 | 141 | 2.095 | 5.544 | 37,8 % | — |
| m3 | RUNNING | 2.199 | 95 | 2.294 | 5.445 | 42,1 % | — |
| m4 | RUNNING | 2.325 | 121 | 2.446 | 5.148 | 47,5 % | — |
| **Total** | — | **8.839** | **438** | **9.277** | **21.681** | **42,8 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:60, install/adb:18, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:100, install/adb:40, timeout:1
- m2: 21 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:64, install/adb:31
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:77, install/adb:44

## Ciclo 2026-07-07 22:49:21 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.406 | 85 | 2.491 | 5.544 | 44,9 % | — |
| m2 | RUNNING | 1.995 | 144 | 2.139 | 5.544 | 38,6 % | — |
| m3 | RUNNING | 2.216 | 103 | 2.319 | 5.445 | 42,6 % | — |
| m4 | RUNNING | 2.360 | 123 | 2.483 | 5.148 | 48,2 % | — |
| **Total** | — | **8.977** | **455** | **9.432** | **21.681** | **43,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:63, install/adb:19, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:103, install/adb:40, timeout:1
- m2: 20 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:67, install/adb:35, timeout:1
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:77, install/adb:46

**Ações (22:40 local) — INCIDENTE: m3 E m4 travadas simultaneamente.** Varredura SSH deu banner timeout na porta 22 em m3 (34.45.199.111) e m4 (136.65.192.165), persistente em 2 retentativas; ambas RUNNING no `gcloud instances list`. Diagnóstico = VMs travadas (SSH hang). **Reboot imediato das duas** (`gcloud compute instances reset m3/m4-exp02`, ~01:43/01:44 UTC). SSH voltou em ~90s (uptime "up 1 min"). Resume `run_experiment.sh` nas duas → docker-compose recriou os 5 containers (4 exp + humanoid). Confirmado: m3 5/5 Up + run vivo; m4 5/5 Up + run vivo. m1/m2 permaneceram saudáveis durante o incidente. **Nota:** 2 VMs travando ao mesmo tempo é atípico (as anteriores foram isoladas); os containers Exited(255) esperados pós-reboot foram recriados pelo resume. Sem perda de progresso (tasks.json idempotente).

## Ciclo 2026-07-07 23:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.416 | 85 | 2.501 | 5.544 | 45,1 % | — |
| m2 | RUNNING | 2.000 | 150 | 2.150 | 5.544 | 38,8 % | — |
| m3 | RUNNING | 2.228 | 94 | 2.322 | 5.445 | 42,6 % | — |
| m4 | RUNNING | 2.371 | 112 | 2.483 | 5.148 | 48,2 % | — |
| **Total** | — | **9.015** | **441** | **9.456** | **21.681** | **43,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:63, install/adb:19, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:109, install/adb:40, timeout:1
- m2: 1 APK(s) só-falha → com.vermont.possin_8.apk
- m2: 19 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:65, install/adb:28, timeout:1
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=599 fail=12)
- m4: erros → emulator/boot:74, install/adb:38
- m4: container exp_01 docker=exited (ok=602 fail=16)
- m4: container exp_02 docker=exited (ok=600 fail=22)

## Ciclo 2026-07-07 23:46:57 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.457 | 87 | 2.544 | 5.544 | 45,9 % | — |
| m2 | RUNNING | 2.040 | 154 | 2.194 | 5.544 | 39,6 % | — |
| m3 | RUNNING | 2.260 | 85 | 2.345 | 5.445 | 43,1 % | — |
| m4 | RUNNING | 2.398 | 85 | 2.483 | 5.148 | 48,2 % | — |
| **Total** | — | **9.155** | **411** | **9.566** | **21.681** | **44,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:63, install/adb:21, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:112, install/adb:41, timeout:1
- m2: 19 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:61, install/adb:23, timeout:1
- m3: 4 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:64, install/adb:21

**Ações (23:46 local):** m3 com 3 containers OOM pós-reboot (Exit 137: exp_00 ~22:50, exp_02 ~23:02, exp_03 ~23:25 local) → `docker start exp_00 exp_02 exp_03` OK (todos OOMKilled=false running). run_experiment.sh vivo em m3. **VIGILÂNCIA m3/m4 pós-reboot duplo ENCERRADA: nenhuma das duas RETRAVOU** (SSH normal, VM saudável) — o risco de infra do reboot simultâneo NÃO recorreu; os eventos de m3 foram OOM de container (esperado na retomada de carga pós-reboot), não hang de VM. m4 saudável 5/5 Up 17min (transição de passada). m1/m2 ok. Todas 4/4 exp + humanoid Up após ações.

## Ciclo 2026-07-08 00:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.466 | 90 | 2.556 | 5.544 | 46,1 % | — |
| m2 | RUNNING | 2.051 | 154 | 2.205 | 5.544 | 39,8 % | — |
| m3 | RUNNING | 2.267 | 84 | 2.351 | 5.445 | 43,2 % | — |
| m4 | RUNNING | 2.403 | 80 | 2.483 | 5.148 | 48,2 % | — |
| **Total** | — | **9.187** | **408** | **9.595** | **21.681** | **44,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:66, install/adb:21, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:112, install/adb:41, timeout:1
- m2: 19 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:60, install/adb:23, timeout:1
- m3: 3 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=609 fail=27)
- m3: container exp_03 docker=exited (ok=578 fail=21)
- m4: erros → emulator/boot:64, install/adb:16

## Ciclo 2026-07-08 00:45:41 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.502 | 99 | 2.601 | 5.544 | 46,9 % | — |
| m2 | RUNNING | 2.088 | 161 | 2.249 | 5.544 | 40,6 % | — |
| m3 | RUNNING | 2.289 | 85 | 2.374 | 5.445 | 43,6 % | — |
| m4 | RUNNING | 2.426 | 61 | 2.487 | 5.148 | 48,3 % | — |
| **Total** | — | **9.305** | **406** | **9.711** | **21.681** | **44,8 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:75, install/adb:21, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:115, install/adb:45, timeout:1
- m2: 18 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:60, install/adb:24, timeout:1
- m3: 3 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:60, install/adb:1

**Ações (00:44 local) + DIAGNÓSTICO de OOM recorrente em m3.** Os MESMOS 3 containers de m3 (exp_00/exp_02/exp_03) reincidiram Exit 137 — morreram ~23:53 local (~7min após o restart das 23:46) e ficaram **~48min parados** até este ciclo (o cron NÃO reinicia container individual). Restart em bloco OK (3/3 running). **2º ciclo consecutivo com a mesma trinca OOMando.**
- **Causa (snapshot `free -g` + `docker stats` em m3):** a VM tem **31 GiB físicos**, mas o compose dá `mem_limit: 10g × 4 containers = 40 GiB` — **oversubscrição de ~1,3×**. Quando ≥3 emuladores de m3 dão pico simultâneo (exp_01 sozinho estava em 8,46 GiB/84%), a soma estoura os 31 GiB e o OOM-killer do kernel mata containers (Exit 137). m4 é idêntica (31 GiB, mesma oversubscrição) — a diferença é só o TIMING dos APKs do batch de m3 (08-11) picando juntos agora; não é VM quebrada nem hang (SSH normal, VM saudável).
- **Impacto:** perda de throughput em m3 (containers parados até ~1h entre checagens manuais), NÃO perda de dado (tasks.json idempotente). m3 segue avançando (43,6%).
- **Lacuna operacional:** o self-heal de container OOM depende da minha checagem horária; entre ciclos um container pode ficar morto até ~1h. Recomendação a levar ao usuário (NÃO agir sem autorização — é infra/automação): um cron leve de container-restart (`docker start $(docker ps -aq -f status=exited -f label=...)` a cada ~10min) fecharia a lacuna SEM tocar em config de experimento (mem/timeouts/tools/dataset). Alternativa (mudança de config, exige autorização): reduzir mem_limit para caber 4× em 31 GiB.

## Ciclo 2026-07-08 01:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.515 | 99 | 2.614 | 5.544 | 47,2 % | — |
| m2 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m3 | RUNNING | 2.300 | 83 | 2.383 | 5.445 | 43,8 % | — |
| m4 | RUNNING | 2.440 | 61 | 2.501 | 5.148 | 48,6 % | — |
| **Total** | — | **7.255** | **243** | **7.498** | **16.137** | **46,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:75, install/adb:21, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:58, install/adb:24, timeout:1
- m3: 2 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=610 fail=26)
- m3: container exp_03 docker=exited (ok=579 fail=20)
- m4: erros → emulator/boot:60, install/adb:1

## Ciclo 2026-07-08 01:48:36 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.540 | 100 | 2.640 | 5.544 | 47,6 % | — |
| m2 | RUNNING | 2.102 | 161 | 2.263 | 5.544 | 40,8 % | — |
| m3 | RUNNING | 2.322 | 84 | 2.406 | 5.445 | 44,2 % | — |
| m4 | RUNNING | 2.479 | 72 | 2.551 | 5.148 | 49,6 % | — |
| **Total** | — | **9.443** | **417** | **9.860** | **21.681** | **45,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:75, install/adb:22, timeout:3
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m2: erros → emulator/boot:115, install/adb:45, timeout:1
- m2: 18 APK(s) com 0 task (esperam mop-up)
- m2: container exp_01 docker=exited (ok=588 fail=45)
- m3: erros → emulator/boot:58, install/adb:25, timeout:1
- m3: 2 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=610 fail=26)
- m4: erros → emulator/boot:69, install/adb:3

**Ações (01:43 local) — ciclo pesado: 1 reboot + 2 restarts + escalação m3.**
- **m1 TRAVOU** (SSH banner timeout, RUNNING no gcloud, persistente em 2 tentativas) → reboot imediato (`reset m1-exp02`, ~04:45 UTC), SSH voltou (up 0 min), resume run_experiment.sh, 5/5 containers Up + run vivo. 2º reboot de m1 travada hoje (1º às 09:04).
- **m2 SSH_FALHOU no cron das 01:00 foi BLIP transitório** — recuperou sozinha (SSH ok na varredura, 4/4 Up). Mas m2/exp_01 OOMou (isolado) → restart OK, running.
- **m3/exp_00+exp_02+exp_03: 3º CICLO CONSECUTIVO OOMando (gatilho de ênfase).** Pior: neste ciclo re-OOMaram em ~16-60s após o restart (churn) — o exp_01 sozinho segura 8,4 GiB e, quando os 3 sobem juntos, estouram os 31 GiB. No 2º restart deste ciclo sobreviveram 40s (4/4 Up) → o churn é INTERMITENTE, ligado ao pico simultâneo do exp_01.
- **CONCLUSÃO:** o self-heal por restart manual funciona só parcialmente em m3 e deixa a trinca parada até ~1h entre checagens. m3 drena throughput (44,2% vs m4 49,6%). PRECISA de decisão do usuário: (1) cron leve de container-restart a cada ~10min (sem tocar config de experimento) — recomendado; ou (2) reduzir mem_limit p/ caber 4× em 31 GiB (mudança de config). Todas 4 VMs 4/4 exp + humanoid Up ao fim do ciclo.

## Ciclo 2026-07-08 02:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.549 | 92 | 2.641 | 5.544 | 47,6 % | — |
| m2 | RUNNING | 2.110 | 163 | 2.273 | 5.544 | 41,0 % | — |
| m3 | RUNNING | 2.328 | 84 | 2.412 | 5.445 | 44,3 % | — |
| m4 | RUNNING | 2.490 | 72 | 2.562 | 5.148 | 49,8 % | — |
| **Total** | — | **9.477** | **411** | **9.888** | **21.681** | **45,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:72, install/adb:19, timeout:1
- m1: 1 APK(s) com 0 task (esperam mop-up)
- m1: container exp_00 docker=exited (ok=663 fail=17)
- m1: container exp_03 docker=exited (ok=660 fail=22)
- m2: erros → emulator/boot:115, install/adb:47, timeout:1
- m2: 1 APK(s) só-falha → com.kin.easynotes_14.apk
- m2: 16 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:25, timeout:1
- m3: 2 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=610 fail=26)
- m3: container exp_03 docker=exited (ok=579 fail=20)
- m4: erros → emulator/boot:69, install/adb:3

## Ciclo 2026-07-08 02:50:10 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.582 | 84 | 2.666 | 5.544 | 48,1 % | — |
| m2 | RUNNING | 2.150 | 159 | 2.309 | 5.544 | 41,6 % | — |
| m3 | RUNNING | 2.353 | 84 | 2.437 | 5.445 | 44,8 % | — |
| m4 | RUNNING | 2.538 | 72 | 2.610 | 5.148 | 50,7 % | — |
| **Total** | — | **9.623** | **399** | **10.022** | **21.681** | **46,2 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:73, install/adb:10, timeout:1
- m2: erros → emulator/boot:113, install/adb:45, timeout:1
- m2: 16 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:25, timeout:1
- m3: 1 APK(s) com 0 task (esperam mop-up)
- m4: erros → emulator/boot:69, install/adb:3

**Ações (02:48 local) — oversubscrição agora SISTÊMICA (m1 + m3).** m1 exibiu o MESMO padrão de m3: trinca exp_00/exp_02/exp_03 OOMada (~50min parada), exp_01 de pé (memory hog). m3 idem. Restart 1x de cada trinca → ambas sobreviveram 30s (4/4 Up). m2/m4 saudáveis (4/4). Marco: 10.022/21.681 = 46,2% (>10k). **A decisão sobre o container-restart cron (opção 1) fica MAIS urgente: o padrão não é exclusivo de m3 — atinge qualquer VM cujo batch pique junto. Sem a automação, 2 VMs ficaram com 3 containers ociosos ~50min neste ciclo.** Decisão do usuário ainda pendente; sigo com self-heal manual.

## Ciclo 2026-07-08 03:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.587 | 83 | 2.670 | 5.544 | 48,2 % | — |
| m2 | RUNNING | 2.157 | 158 | 2.315 | 5.544 | 41,8 % | — |
| m3 | RUNNING | 2.358 | 84 | 2.442 | 5.445 | 44,8 % | — |
| m4 | RUNNING | 2.548 | 72 | 2.620 | 5.148 | 50,9 % | — |
| **Total** | — | **9.650** | **397** | **10.047** | **21.681** | **46,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:73, install/adb:9, timeout:1
- m1: container exp_00 docker=exited (ok=663 fail=17)
- m1: container exp_03 docker=exited (ok=661 fail=21)
- m2: erros → emulator/boot:113, install/adb:44, timeout:1
- m2: 16 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:25, timeout:1
- m3: 1 APK(s) com 0 task (esperam mop-up)
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=610 fail=26)
- m3: container exp_03 docker=exited (ok=579 fail=20)
- m4: erros → emulator/boot:69, install/adb:3

## Ciclo 2026-07-08 03:49:48 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.608 | 79 | 2.687 | 5.544 | 48,5 % | — |
| m2 | RUNNING | 2.199 | 158 | 2.357 | 5.544 | 42,5 % | — |
| m3 | RUNNING | 2.380 | 87 | 2.467 | 5.445 | 45,3 % | — |
| m4 | RUNNING | 2.588 | 84 | 2.672 | 5.148 | 51,9 % | — |
| **Total** | — | **9.775** | **408** | **10.183** | **21.681** | **47,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:69, install/adb:9, timeout:1
- m2: erros → emulator/boot:115, install/adb:42, timeout:1
- m2: 15 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:61, install/adb:25, timeout:1
- m4: erros → emulator/boot:78, install/adb:6

**Ações (03:47 local):** m1 e m3 com trinca OOMada ~50min (padrão recorrente) → restart 1x cada. m3 4/4 direto. Em m1, ao subir a trinca o exp_01 (antigo hog) foi expulso e OOMou (churn rotativo) → restart do exp_01 → m1 4/4 estabilizou. m2/m4 saudáveis. Decisão do cron de container-restart AINDA pendente; padrão custa ~50min/hora de 3 containers ociosos em m1 e m3 (por isso m1 48,5% e m3 45,3% atrás de m4 51,9%).

## Ciclo 2026-07-08 04:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.611 | 76 | 2.687 | 5.544 | 48,5 % | — |
| m2 | RUNNING | 2.208 | 158 | 2.366 | 5.544 | 42,7 % | — |
| m3 | RUNNING | 2.385 | 87 | 2.472 | 5.445 | 45,4 % | — |
| m4 | RUNNING | 2.598 | 85 | 2.683 | 5.148 | 52,1 % | — |
| **Total** | — | **9.802** | **406** | **10.208** | **21.681** | **47,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:66, install/adb:9, timeout:1
- m1: container exp_00 docker=exited (ok=664 fail=16)
- m1: container exp_01 docker=exited (ok=623 fail=19)
- m1: container exp_03 docker=exited (ok=661 fail=21)
- m2: erros → emulator/boot:115, install/adb:42, timeout:1
- m2: 15 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:61, install/adb:25, timeout:1
- m3: container exp_00 docker=exited (ok=600 fail=11)
- m3: container exp_02 docker=exited (ok=610 fail=26)
- m3: container exp_03 docker=exited (ok=579 fail=20)
- m4: erros → emulator/boot:78, install/adb:7

## Ciclo 2026-07-08 04:48:51 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.623 | 64 | 2.687 | 5.544 | 48,5 % | — |
| m2 | RUNNING | 2.249 | 166 | 2.415 | 5.544 | 43,6 % | — |
| m3 | RUNNING | 2.394 | 87 | 2.481 | 5.445 | 45,6 % | — |
| m4 | RUNNING | 2.645 | 88 | 2.733 | 5.148 | 53,1 % | — |
| **Total** | — | **9.911** | **405** | **10.316** | **21.681** | **47,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:54, install/adb:10
- m2: erros → emulator/boot:120, install/adb:45, timeout:1
- m2: 12 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:61, install/adb:25, timeout:1
- m4: erros → emulator/boot:78, install/adb:10

**Ações (04:47 local):** m3 trinca OOMada ~54min → restart; exp_01 expulso ao subir (churn rotativo) → restart do exp_01 → m3 4/4. m1 recuperou-se sozinha via transição de passada (5/5 Up 42min). m2/m4 saudáveis. Decisão do cron de container-restart ainda pendente. m4 lidera (53,1%), m2 fechando gap (43,6%).

## Ciclo 2026-07-08 05:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.633 | 62 | 2.695 | 5.544 | 48,6 % | — |
| m2 | RUNNING | 2.260 | 166 | 2.426 | 5.544 | 43,8 % | — |
| m3 | RUNNING | 2.396 | 85 | 2.481 | 5.445 | 45,6 % | — |
| m4 | RUNNING | 2.658 | 89 | 2.747 | 5.148 | 53,4 % | — |
| **Total** | — | **9.947** | **402** | **10.349** | **21.681** | **47,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:52, install/adb:10
- m2: erros → emulator/boot:120, install/adb:45, timeout:1
- m2: 12 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:59, install/adb:25, timeout:1
- m4: erros → emulator/boot:78, install/adb:11

## Ciclo 2026-07-08 05:46:41 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.673 | 72 | 2.745 | 5.544 | 49,5 % | — |
| m2 | RUNNING | 2.303 | 167 | 2.470 | 5.544 | 44,6 % | — |
| m3 | RUNNING | 2.419 | 67 | 2.486 | 5.445 | 45,7 % | — |
| m4 | RUNNING | 2.698 | 98 | 2.796 | 5.148 | 54,3 % | — |
| **Total** | — | **10.093** | **404** | **10.497** | **21.681** | **48,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:59, install/adb:13
- m2: erros → emulator/boot:120, install/adb:46, timeout:1
- m2: 12 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:15, timeout:1
- m4: erros → emulator/boot:86, install/adb:12

**Ações (05:46 local):** varredura SSH — nenhuma anomalia. 4/4 exp + humanoid Up nas 4 VMs; run vivo nas 4. Nenhum OOM neste ciclo. m3 estável desde o restart das 04:48 (Up 53min) — a trinca sobreviveu a hora inteira desta vez (janela de pico dos batches passou). Decisão do cron ainda pendente.

## Ciclo 2026-07-08 06:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.685 | 73 | 2.758 | 5.544 | 49,7 % | — |
| m2 | RUNNING | 2.313 | 170 | 2.483 | 5.544 | 44,8 % | — |
| m3 | RUNNING | 2.429 | 61 | 2.490 | 5.445 | 45,7 % | — |
| m4 | RUNNING | 2.711 | 98 | 2.809 | 5.148 | 54,6 % | — |
| **Total** | — | **10.138** | **402** | **10.540** | **21.681** | **48,6 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:60, install/adb:13
- m2: erros → emulator/boot:123, install/adb:46, timeout:1
- m2: 11 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:50, install/adb:10, timeout:1
- m4: erros → emulator/boot:86, install/adb:12

## Ciclo 2026-07-08 06:44:44 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.729 | 74 | 2.803 | 5.544 | 50,6 % | — |
| m2 | RUNNING | 2.349 | 177 | 2.526 | 5.544 | 45,6 % | — |
| m3 | RUNNING | 2.469 | 60 | 2.529 | 5.445 | 46,4 % | — |
| m4 | RUNNING | 2.754 | 98 | 2.852 | 5.148 | 55,4 % | — |
| **Total** | — | **10.301** | **409** | **10.710** | **21.681** | **49,4 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:60, install/adb:14
- m2: erros → emulator/boot:129, install/adb:47, timeout:1
- m2: 9 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:9
- m4: erros → emulator/boot:86, install/adb:12

**Ações (06:44 local):** varredura SSH — nenhuma anomalia. 4/4 exp + humanoid Up nas 4 VMs; run vivo nas 4. Nenhum OOM (2º ciclo limpo consecutivo). m1 Up 3h, m3 Up 2h — trincas estáveis. Total 49,4% (perto da metade). Decisão do cron ainda pendente (padrão OOM quieto há 2 ciclos).

## Ciclo 2026-07-08 07:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.744 | 75 | 2.819 | 5.544 | 50,8 % | — |
| m2 | RUNNING | 2.361 | 180 | 2.541 | 5.544 | 45,8 % | — |
| m3 | RUNNING | 2.484 | 62 | 2.546 | 5.445 | 46,8 % | — |
| m4 | RUNNING | 2.768 | 99 | 2.867 | 5.148 | 55,7 % | — |
| **Total** | — | **10.357** | **416** | **10.773** | **21.681** | **49,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:60, install/adb:15
- m2: erros → emulator/boot:132, install/adb:47, timeout:1
- m2: 1 APK(s) só-falha → com.orgzlyrevived_284.apk
- m2: 8 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:11
- m4: erros → emulator/boot:86, install/adb:13

## Ciclo 2026-07-08 07:42:42 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.784 | 78 | 2.862 | 5.544 | 51,6 % | — |
| m2 | RUNNING | 2.400 | 181 | 2.581 | 5.544 | 46,6 % | — |
| m3 | RUNNING | 2.523 | 66 | 2.589 | 5.445 | 47,5 % | — |
| m4 | RUNNING | 2.806 | 103 | 2.909 | 5.148 | 56,5 % | — |
| **Total** | — | **10.513** | **428** | **10.941** | **21.681** | **50,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:63, install/adb:15
- m2: erros → emulator/boot:132, install/adb:48, timeout:1
- m2: 8 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:54, install/adb:12
- m4: erros → emulator/boot:90, install/adb:13

**Ações (07:42 local):** varredura SSH — nenhuma anomalia. 4/4 exp + humanoid Up nas 4 VMs; run vivo. Nenhum OOM (3º ciclo limpo consecutivo). **MARCO: Total 50,5% — metade do experimento concluída.** Trincas estáveis (m1 Up 4h, m3 Up 3h). Decisão do cron pendente (OOM quieto há 3 ciclos).

## Ciclo 2026-07-08 08:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.797 | 83 | 2.880 | 5.544 | 51,9 % | — |
| m2 | RUNNING | 2.416 | 181 | 2.597 | 5.544 | 46,8 % | — |
| m3 | RUNNING | 2.536 | 72 | 2.608 | 5.445 | 47,9 % | — |
| m4 | RUNNING | 2.819 | 108 | 2.927 | 5.148 | 56,9 % | — |
| **Total** | — | **10.568** | **444** | **11.012** | **21.681** | **50,8 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:68, install/adb:15
- m2: erros → emulator/boot:132, install/adb:48, timeout:1
- m2: 8 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:14
- m4: erros → emulator/boot:94, install/adb:14

## Ciclo 2026-07-08 08:40:44 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.834 | 86 | 2.920 | 5.544 | 52,7 % | — |
| m2 | RUNNING | 2.449 | 185 | 2.634 | 5.544 | 47,5 % | — |
| m3 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m4 | RUNNING | 2.859 | 110 | 2.969 | 5.148 | 57,7 % | — |
| **Total** | — | **8.142** | **381** | **8.523** | **16.236** | **52,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:70, install/adb:16
- m2: erros → emulator/boot:135, install/adb:49, timeout:1
- m2: 7 APK(s) com 0 task (esperam mop-up)
- m3: SSH inacessível — ssh timeout (sem ação)
- m4: erros → emulator/boot:94, install/adb:16

**Ações (08:40 local):** minha varredura SSH inicial (08:40) alcançou as 4 VMs OK (4/4 Up, sem OOM — seria 4º ciclo limpo). Mas ao rodar o health_check logo depois, m3 ficou inacessível (SSH_FALHOU na tabela acima). Retentativa + gcloud confirmaram: m3 RUNNING no gcloud mas SSH banner timeout persistente → VM TRAVADA. **Reboot imediato** (`reset m3-exp02`, ~11:46 UTC), SSH voltou (up 0 min), resume run_experiment.sh, 5/5 containers Up + run vivo. m1/m2/m4 saudáveis (4/4). 5º reboot de VM travada nas últimas ~24h (m3 é a mais afetada por hang). A tabela 08:40 mostra m3 com "?" por causa do timeout no momento do health_check — o `done` real de m3 (~2.6k) foi preservado (tasks.json).

## Ciclo 2026-07-08 09:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.852 | 87 | 2.939 | 5.544 | 53,0 % | — |
| m2 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m3 | RUNNING | 2.574 | 70 | 2.644 | 5.445 | 48,6 % | — |
| m4 | RUNNING | 2.876 | 110 | 2.986 | 5.148 | 58,0 % | — |
| **Total** | — | **8.302** | **267** | **8.569** | **16.137** | **53,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:70, install/adb:17
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:58, install/adb:12
- m3: container exp_00 docker=exited (ok=647 fail=12)
- m3: container exp_02 docker=exited (ok=651 fail=21)
- m3: container exp_03 docker=exited (ok=625 fail=12)
- m4: erros → emulator/boot:94, install/adb:16
- m4: container exp_01 docker=exited (ok=728 fail=16)

## Ciclo 2026-07-08 09:46:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.894 | 92 | 2.986 | 5.544 | 53,9 % | — |
| m2 | RUNNING | 2.460 | 190 | 2.650 | 5.544 | 47,8 % | — |
| m3 | RUNNING | 2.586 | 58 | 2.644 | 5.445 | 48,6 % | — |
| m4 | RUNNING | 2.908 | 112 | 3.020 | 5.148 | 58,7 % | — |
| **Total** | — | **10.848** | **452** | **11.300** | **21.681** | **52,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:72, install/adb:20
- m2: erros → emulator/boot:138, install/adb:51, timeout:1
- m2: 5 APK(s) com 0 task (esperam mop-up)
- m2: container exp_00 docker=exited (ok=650 fail=46)
- m3: erros → emulator/boot:52, install/adb:6
- m4: erros → emulator/boot:95, install/adb:17

**Ações (09:45 local):** m4/exp_01 OOM isolado (~08:57) → restart OK. m2/exp_00 OOMou durante o health_check (~09:45, isolado) → restart OK. m2 SSH_FALHOU no cron 09:00 foi BLIP (recuperou sozinha, 4/4). **m3 estável pós-reboot** (5/5 Up 38min — NÃO retravou; vigilância encerrada; a trinca-exited do cron 09:00 era só a retomada de carga pós-reboot). m1 saudável (4/4 Up 6h). Todas 4/4 exp + humanoid Up ao fim. Total 52,1%. Decisão do cron pendente.

## Ciclo 2026-07-08 09:57:28 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.905 | 93 | 2.998 | 5.544 | 54,1 % | — |
| m2 | RUNNING | 2.469 | 189 | 2.658 | 5.544 | 47,9 % | — |
| m3 | RUNNING | 2.593 | 53 | 2.646 | 5.445 | 48,6 % | — |
| m4 | RUNNING | 2.915 | 115 | 3.030 | 5.148 | 58,9 % | — |
| **Total** | — | **10.882** | **450** | **11.332** | **21.681** | **52,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:73, install/adb:20
- m2: erros → emulator/boot:137, install/adb:51, timeout:1
- m2: 5 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:50, install/adb:3
- m4: erros → emulator/boot:99, install/adb:16

**Ações (09:57 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, nenhum container Exited/OOM, run vivo em todas. Ciclo LIMPO (sem restart/reboot). Containers recém-recuperados seguem estáveis (m2/exp_00 Up 10min, m4/exp_01 Up 11min). m3 estável pós-reboot 08:44 (Up 50min). Total 52,3%. Decisão do cron de container-restart segue pendente.

## Ciclo 2026-07-08 10:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.907 | 94 | 3.001 | 5.544 | 54,1 % | — |
| m2 | RUNNING | 2.471 | 189 | 2.660 | 5.544 | 48,0 % | — |
| m3 | RUNNING | 2.595 | 53 | 2.648 | 5.445 | 48,6 % | — |
| m4 | RUNNING | 2.916 | 116 | 3.032 | 5.148 | 58,9 % | — |
| **Total** | — | **10.889** | **452** | **11.341** | **21.681** | **52,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:73, install/adb:21
- m2: erros → emulator/boot:137, install/adb:51, timeout:1
- m2: 5 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:2
- m4: erros → emulator/boot:100, install/adb:16

## Ciclo 2026-07-08 10:55:36 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.954 | 104 | 3.058 | 5.544 | 55,2 % | — |
| m2 | RUNNING | 2.511 | 188 | 2.699 | 5.544 | 48,7 % | — |
| m3 | RUNNING | 2.644 | 55 | 2.699 | 5.445 | 49,6 % | — |
| m4 | RUNNING | 2.961 | 115 | 3.076 | 5.148 | 59,8 % | — |
| **Total** | — | **11.070** | **462** | **11.532** | **21.681** | **53,2 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:80, install/adb:24
- m2: erros → emulator/boot:138, install/adb:49, timeout:1
- m2: 4 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:4
- m4: erros → emulator/boot:100, install/adb:15

**Ações (10:55 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, nenhum container Exited/OOM, run vivo em todas. Ciclo LIMPO (sem restart/reboot). m2/exp_00 Up ~1h, m4/exp_01 Up ~1h (estáveis desde restarts anteriores). m3 estável pós-reboot (Up 2h). m2 avançou +41 (recuperou fôlego). Total 53,2%. Decisão do cron pendente.

## Ciclo 2026-07-08 11:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 2.958 | 104 | 3.062 | 5.544 | 55,2 % | — |
| m2 | RUNNING | 2.513 | 188 | 2.701 | 5.544 | 48,7 % | — |
| m3 | RUNNING | 2.648 | 55 | 2.703 | 5.445 | 49,6 % | — |
| m4 | RUNNING | 2.965 | 115 | 3.080 | 5.148 | 59,8 % | — |
| **Total** | — | **11.084** | **462** | **11.546** | **21.681** | **53,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:80, install/adb:24
- m2: erros → emulator/boot:138, install/adb:49, timeout:1
- m2: 4 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:51, install/adb:4
- m4: erros → emulator/boot:100, install/adb:15

## Marco 2026-07-08 ~11:10 (local) — Cron de container-restart instalado (opção 1, autorizado)

Usuário autorizou o cron leve de container-restart. Instalado nas 4 VMs (validado no m3 primeiro, depois m1/m2/m4):
- Script `~/experimento-20260706/scripts/restart_exited.sh`: para cada `exp_00..03`, se `docker inspect .State.Status == exited`, dá `docker start` (com run vivo, exited = OOM a recuperar). Loga timestamp em `logs/restart_cron.out`.
- Crontab (usuário `pedro`, em cada VM): `*/10 * * * * cd ~/experimento-20260706 && bash scripts/restart_exited.sh >> logs/restart_cron.out 2>&1`.
- Verificação final: cron_lines=1, script executável, cron daemon UP nas 4 VMs.
- NÃO tocou docker-compose/mem_limit/timeouts/tools/dataset (só automatiza o `docker start` manual). Reduz janela de ociosidade pós-OOM de ~1h → ~10min.
- NOTA: o cron do health_check roda na MÁQUINA LOCAL (não nas VMs); este novo cron é independente e roda DENTRO de cada VM. A varredura SSH manual a cada ciclo continua como rede de segurança adicional.

## Ciclo 2026-07-08 11:58:49 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.012 | 109 | 3.121 | 5.544 | 56,3 % | — |
| m2 | RUNNING | 2.555 | 186 | 2.741 | 5.544 | 49,4 % | — |
| m3 | RUNNING | 2.697 | 63 | 2.760 | 5.445 | 50,7 % | — |
| m4 | RUNNING | 3.016 | 124 | 3.140 | 5.148 | 61,0 % | — |
| **Total** | — | **11.280** | **482** | **11.762** | **21.681** | **54,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:82, install/adb:27
- m2: erros → emulator/boot:140, install/adb:44, timeout:2
- m2: 3 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:57, install/adb:6
- m4: erros → emulator/boot:105, install/adb:19

**Ações (11:58 local):** m3/exp_01 OOM (Exit 137, ~11:54) → `docker start` imediato (Up 3s; cron de 10min ainda não havia disparado). m2 SSH_FALHOU na varredura → gcloud confirmou RUNNING + retentativa recuperou (4/4 Up, run vivo) = BLIP, não hang, sem reboot. m1 (Up 8h) e m4 (Up 12h) saudáveis. Log do cron restart_exited vazio nas 4 (primeiro OOM pós-install foi pego por mim antes do tick). Total 54,3% (+216 na hora). m2 avançou +40 (segue recuperando).

## Ciclo 2026-07-08 12:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.012 | 109 | 3.121 | 5.544 | 56,3 % | — |
| m2 | RUNNING | 2.558 | 187 | 2.745 | 5.544 | 49,5 % | — |
| m3 | RUNNING | 2.699 | 63 | 2.762 | 5.445 | 50,7 % | — |
| m4 | RUNNING | 3.018 | 124 | 3.142 | 5.148 | 61,0 % | — |
| **Total** | — | **11.287** | **483** | **11.770** | **21.681** | **54,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:82, install/adb:27
- m2: erros → emulator/boot:141, install/adb:44, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:57, install/adb:6
- m4: erros → emulator/boot:105, install/adb:19

## Ciclo 2026-07-08 13:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.063 | 116 | 3.179 | 5.544 | 57,3 % | — |
| m2 | RUNNING | 2.561 | 188 | 2.749 | 5.544 | 49,6 % | — |
| m3 | RUNNING | 2.744 | 66 | 2.810 | 5.445 | 51,6 % | — |
| m4 | RUNNING | 3.063 | 128 | 3.191 | 5.148 | 62,0 % | — |
| **Total** | — | **11.431** | **498** | **11.929** | **21.681** | **55,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:89, install/adb:27
- m2: erros → emulator/boot:142, install/adb:44, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:8
- m4: erros → emulator/boot:105, install/adb:23

## Ciclo 2026-07-08 13:02:34 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.065 | 116 | 3.181 | 5.544 | 57,4 % | — |
| m2 | RUNNING | 2.564 | 185 | 2.749 | 5.544 | 49,6 % | — |
| m3 | RUNNING | 2.747 | 66 | 2.813 | 5.445 | 51,7 % | — |
| m4 | RUNNING | 3.065 | 128 | 3.193 | 5.148 | 62,0 % | — |
| **Total** | — | **11.441** | **495** | **11.936** | **21.681** | **55,1 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:89, install/adb:27
- m2: erros → emulator/boot:139, install/adb:44, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:58, install/adb:8
- m4: erros → emulator/boot:105, install/adb:23

**Ações (13:02 local):** **m2 TRAVADA** (SSH banner timeout persistente na varredura + retentativa; gcloud RUNNING) → reboot `reset m2-exp02` (~15:56 UTC), SSH voltou (up 0 min), resume run_experiment.sh m2 → 5/5 Up 3min + run vivo. tasks.json garante idempotência (nada reprocessado). 6º reboot de VM travada nas ~24h. **Cron de restart PROVOU funcionar:** m4/exp_02 OOMou e o cron o reiniciou sozinho às 15:20:01 UTC (12:20 local, Up 36min na varredura) — primeira auto-recuperação sem minha intervenção. m1 (Up 9h) e m3 (Up 4h) saudáveis. Total 55,1% (+174 na hora).

## Ciclo 2026-07-08 14:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m2 | RUNNING | 2.656 | 155 | 2.811 | 5.544 | 50,7 % | — |
| m3 | RUNNING | 2.800 | 74 | 2.874 | 5.445 | 52,8 % | — |
| m4 | RUNNING | 3.111 | 129 | 3.240 | 5.148 | 62,9 % | — |
| **Total** | — | **8.567** | **358** | **8.925** | **16.137** | **55,3 %** | — |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: erros → emulator/boot:131, install/adb:23, timeout:1
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:64, install/adb:10
- m4: erros → emulator/boot:107, install/adb:22

## Ciclo 2026-07-08 14:04:51 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.097 | 117 | 3.214 | 5.544 | 58,0 % | — |
| m2 | RUNNING | 2.660 | 155 | 2.815 | 5.544 | 50,8 % | — |
| m3 | RUNNING | 2.801 | 74 | 2.875 | 5.445 | 52,8 % | — |
| m4 | RUNNING | 3.112 | 129 | 3.241 | 5.148 | 63,0 % | — |
| **Total** | — | **11.670** | **475** | **12.145** | **21.681** | **56,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:89, install/adb:28
- m2: erros → emulator/boot:131, install/adb:23, timeout:1
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:64, install/adb:10
- m4: erros → emulator/boot:107, install/adb:22

**Ações (14:04 local):** **m1 TRAVADA** (SSH banner timeout persistente na varredura + retentativa; gcloud RUNNING) → reboot `reset m1-exp02` (~17:01 UTC), SSH voltou (up 0 min), resume run_experiment.sh m1 → 5/5 Up 2min + run vivo. 7º reboot de VM travada nas ~24h. m2 recuperou bem do reboot anterior (12:57): 4/4 Up ~1h, +66 na hora (agora 50,8%). m3 (Up 5h) e m4 (Up 15h) saudáveis. Cron de restart sem novos OOMs (log ainda mostra só o 12:20 do m4). Total 56,0% (+209 na hora). VIGILÂNCIA m1 no próximo ciclo (recém-rebootado).

## Ciclo 2026-07-08 14:20:02 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.097 | 117 | 3.214 | 5.544 | 58,0 % | — |
| m2 | RUNNING | 2.686 | 156 | 2.842 | 5.544 | 51,3 % | — |
| m3 | RUNNING | 2.815 | 75 | 2.890 | 5.445 | 53,1 % | — |
| m4 | RUNNING | 3.127 | 129 | 3.256 | 5.148 | 63,2 % | — |
| **Total** | — | **11.725** | **477** | **12.202** | **21.681** | **56,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:90, install/adb:27
- m2: erros → emulator/boot:131, install/adb:24, timeout:1
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:65, install/adb:10
- m4: erros → emulator/boot:107, install/adb:22

## Ciclo 2026-07-08 15:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.109 | 105 | 3.214 | 5.544 | 58,0 % | — |
| m2 | RUNNING | 2.754 | 158 | 2.912 | 5.544 | 52,5 % | — |
| m3 | RUNNING | 2.850 | 80 | 2.930 | 5.445 | 53,8 % | — |
| m4 | RUNNING | 3.163 | 130 | 3.293 | 5.148 | 64,0 % | — |
| **Total** | — | **11.876** | **473** | **12.349** | **21.681** | **57,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:88, install/adb:17
- m2: erros → emulator/boot:132, install/adb:25, timeout:1
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:68, install/adb:12
- m4: erros → emulator/boot:108, install/adb:22

## Ciclo 2026-07-08 15:02:58 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.110 | 104 | 3.214 | 5.544 | 58,0 % | — |
| m2 | RUNNING | 2.759 | 159 | 2.918 | 5.544 | 52,6 % | — |
| m3 | RUNNING | 2.853 | 80 | 2.933 | 5.445 | 53,9 % | — |
| m4 | RUNNING | 3.166 | 130 | 3.296 | 5.148 | 64,0 % | — |
| **Total** | — | **11.888** | **473** | **12.361** | **21.681** | **57,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:17
- m2: erros → emulator/boot:132, install/adb:26, timeout:1
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:68, install/adb:12
- m4: erros → emulator/boot:108, install/adb:22

**Ações (15:02 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual). **m1 confirmado estável** pós-reboot (Up 48min, não retravou); vigilância m1 encerrada. **Cron de restart auto-recuperou m1/exp_01 às 17:10:02 UTC (14:10 local)** — 2ª auto-recuperação do cron (1ª foi m4/exp_02 às 12:20). m2 (Up 2h), m3 (Up 6h), m4 (Up 16h) saudáveis. Total 57,0% (+12 no delta curto vs cron 15:00; ~+216/h no ritmo). O cron está absorvendo os OOMs isolados — nenhum container ficou ocioso entre ciclos.

## Ciclo 2026-07-08 15:45:11 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.135 | 84 | 3.219 | 5.544 | 58,1 % | — |
| m2 | RUNNING | 2.830 | 164 | 2.994 | 5.544 | 54,0 % | — |
| m3 | RUNNING | 2.891 | 80 | 2.971 | 5.445 | 54,6 % | — |
| m4 | RUNNING | 3.198 | 132 | 3.330 | 5.148 | 64,7 % | — |
| **Total** | — | **12.054** | **460** | **12.514** | **21.681** | **57,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:82, install/adb:2
- m2: erros → emulator/boot:134, install/adb:28, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:68, install/adb:12
- m4: erros → emulator/boot:107, install/adb:24, timeout:1

**Ações (15:45 local):** varredura SSH ativa — m1/m2/m3 saudáveis (5/5 exp+humanoid Up, run vivo). **m4 TRAVADA** (SSH banner timeout persistente na varredura + retentativa; gcloud RUNNING) → reboot `reset m4-exp02` (~18:42 UTC), SSH voltou em 20s (up 0 min), resume run_experiment.sh m4 → 5/5 Up 2min + run vivo. **8º reboot de VM travada nas ~24h** (m4 vinha com Up 16h — o mais longo, condizente com hang acumulado). Cron de restart sem novos OOMs (log ainda mostra só o 17:10 do m1/exp_01 + 12:20 do m4). Total 57,7% (+153 vs 15:02). VIGILÂNCIA m4 no próximo ciclo (recém-rebootada).

## Ciclo 2026-07-08 16:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.149 | 84 | 3.233 | 5.544 | 58,3 % | — |
| m2 | RUNNING | 2.855 | 167 | 3.022 | 5.544 | 54,5 % | — |
| m3 | RUNNING | 2.904 | 81 | 2.985 | 5.445 | 54,8 % | — |
| m4 | RUNNING | 3.201 | 129 | 3.330 | 5.148 | 64,7 % | — |
| **Total** | — | **12.109** | **461** | **12.570** | **21.681** | **58,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:81, install/adb:3
- m2: erros → emulator/boot:136, install/adb:29, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:69, install/adb:12
- m4: erros → emulator/boot:104, install/adb:24, timeout:1

## Ciclo 2026-07-08 16:43:37 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.186 | 93 | 3.279 | 5.544 | 59,1 % | — |
| m2 | RUNNING | 2.929 | 171 | 3.100 | 5.544 | 55,9 % | — |
| m3 | RUNNING | 2.939 | 86 | 3.025 | 5.445 | 55,6 % | — |
| m4 | RUNNING | 3.210 | 120 | 3.330 | 5.148 | 64,7 % | — |
| **Total** | — | **12.264** | **470** | **12.734** | **21.681** | **58,7 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:88, install/adb:5
- m2: erros → emulator/boot:136, install/adb:33, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:74, install/adb:12
- m4: erros → emulator/boot:96, install/adb:23, timeout:1

**Ações (16:43 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual). **m4 confirmada estável pós-reboot** (Up 46min, não retravou); vigilância m4 encerrada. Cron do m4 auto-recuperou exp_01 às 18:50:01 UTC (15:50 local) — 3ª auto-recuperação do cron; m1/exp_01 segue no log (17:10). **Diagnóstico m4** (total "flat" em 3.330 por 3 leituras): NÃO está travada — `rv_status by_timeout` mostra passada 60s completa (1716/1716 done) + passada 180s em andamento (1499 COMPLETED / 115 ERROR sendo retentados) + passada 300s não iniciada; `docker stats` confirma trabalho intenso (CPU 238-409% nos 4 containers, mem 3,6-5,3 GiB). O total distinto não subiu porque o resume estava reprocessando erros da passada 180s (err→ok, mesma identidade). zero_task=[] em m4. m1 (Up 2h), m2 (Up 4h), m3 (Up 8h) saudáveis. Total 58,7% (+220 vs 15:45; ~+220/h no ritmo).

## Ciclo 2026-07-08 17:00:02 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.201 | 96 | 3.297 | 5.544 | 59,5 % | — |
| m2 | RUNNING | 2.957 | 172 | 3.129 | 5.544 | 56,4 % | — |
| m3 | RUNNING | 2.952 | 89 | 3.041 | 5.445 | 55,8 % | — |
| m4 | RUNNING | 3.215 | 115 | 3.330 | 5.148 | 64,7 % | — |
| **Total** | — | **12.325** | **472** | **12.797** | **21.681** | **59,0 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:90, install/adb:6
- m2: erros → emulator/boot:136, install/adb:34, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 2 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:76, install/adb:13
- m4: erros → emulator/boot:96, install/adb:18, timeout:1

## Ciclo 2026-07-08 17:43:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.240 | 99 | 3.339 | 5.544 | 60,2 % | — |
| m2 | RUNNING | 3.031 | 175 | 3.206 | 5.544 | 57,8 % | — |
| m3 | RUNNING | 2.991 | 91 | 3.082 | 5.445 | 56,6 % | — |
| m4 | RUNNING | 3.241 | 109 | 3.350 | 5.148 | 65,1 % | — |
| **Total** | — | **12.503** | **474** | **12.977** | **21.681** | **59,9 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:91, install/adb:8
- m2: erros → emulator/boot:136, install/adb:37, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 1 APK(s) com 0 task (esperam mop-up)
- m3: erros → emulator/boot:76, install/adb:15
- m4: erros → emulator/boot:100, install/adb:8, timeout:1

**Ações (17:43 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual, sem containers exited). **m4 saiu do "flat"**: 3.330→3.350 (+20 distintas) — resume terminou de retentar erros da passada 180s e voltou a processar tasks novas; confirmação de que o diagnóstico do ciclo anterior estava certo (não era travamento). **m2 zero-task caiu de 2 para 1 APK** (progresso no mop-up natural). Uptimes: m1 3h, m2 5h, m3 9h, m4 2h — sem novos OOMs (cron log inalterado: 17:10 m1 + 18:50 m4). Total 59,9% (+243 vs 16:43; ~+243/h). Cruzando 60% em breve. Nenhuma intervenção necessária.

## Ciclo 2026-07-08 18:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.256 | 99 | 3.355 | 5.544 | 60,5 % | — |
| m2 | RUNNING | 3.057 | 175 | 3.232 | 5.544 | 58,3 % | — |
| m3 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m4 | RUNNING | 3.259 | 104 | 3.363 | 5.148 | 65,3 % | — |
| **Total** | — | **9.572** | **378** | **9.950** | **16.236** | **61,3 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:91, install/adb:8
- m2: erros → emulator/boot:136, install/adb:37, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m2: 1 APK(s) com 0 task (esperam mop-up)
- m3: SSH inacessível — ssh timeout (sem ação)
- m4: erros → emulator/boot:99, install/adb:5

## Ciclo 2026-07-08 18:40:47 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.294 | 103 | 3.397 | 5.544 | 61,3 % | — |
| m2 | RUNNING | 3.122 | 173 | 3.295 | 5.544 | 59,4 % | — |
| m3 | RUNNING | 3.012 | 92 | 3.104 | 5.445 | 57,0 % | — |
| m4 | RUNNING | 3.295 | 104 | 3.399 | 5.148 | 66,0 % | — |
| **Total** | — | **12.723** | **472** | **13.195** | **21.681** | **60,9 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:92, install/adb:11
- m2: erros → emulator/boot:136, install/adb:35, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:76, install/adb:16
- m4: erros → emulator/boot:98, install/adb:6

**Ações (18:40 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual). **m3 confirmada saudável** (Up 10h, run vivo): o `SSH_FALHOU` do cron das 18:00 foi **blip transiente de SSH** (recuperou sozinho na varredura seguinte — nenhum reboot foi necessário; comportamento esperado por protocolo). **Cron do m2 auto-recuperou exp_01 às 21:00:01 UTC (18:00 local)** — 4ª auto-recuperação do cron (exp_01 agora Up 40min). m2 zero-task agora ZERADO (só resta o só-falha keypass_1442). Uptimes: m1 4h, m2 6h, m3 10h, m4 3h. Total **60,9%** (+218 vs 17:43; ~+218/h). Cruzamos os 60%. Nenhuma intervenção manual.

## Ciclo 2026-07-08 19:00:01 (local)

| VM | estado | Executadas (ok) | Com erro | Total feito | Previsto | % do previsto | ação |
|----|--------|----------------:|---------:|------------:|---------:|--------------:|------|
| m1 | RUNNING | 3.310 | 108 | 3.418 | 5.544 | 61,7 % | — |
| m2 | RUNNING | 3.151 | 173 | 3.324 | 5.544 | 60,0 % | — |
| m3 | SSH_FALHOU | ? | ? | ? | ? | ? | — |
| m4 | RUNNING | 3.308 | 102 | 3.410 | 5.148 | 66,2 % | — |
| **Total** | — | **9.769** | **383** | **10.152** | **16.236** | **62,5 %** | — |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:12
- m2: erros → emulator/boot:134, install/adb:37, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → emulator/boot:96, install/adb:6

## Ciclo 2026-07-08 19:12:25 (local)

| VM | container | docker | passadas 60·180·300 | reps (feito) | ok | err | feito | alvo | % |
|----|-----------|--------|---------------------|--------------|----:|----:|------:|-----:|--:|
| m1 | exp_00 | Up | 462·405 | 289·289·289 | 840 | 27 | 867 | 1.386 | 62,6 % |
| m1 | exp_01 | Up | 462·365 | 276·276·275 | 803 | 24 | 827 | 1.386 | 59,7 % |
| m1 | exp_02 | Up | 462·411 | 291·291·291 | 841 | 32 | 873 | 1.386 | 63,0 % |
| m1 | exp_03 | Up | 462·401 | 288·288·287 | 836 | 27 | 863 | 1.386 | 62,3 % |
| **m1 subtotal** | — | — | — | — | **3.320** | **110** | **3.430** | **5.544** | **61,9 %** |
| m2 | exp_00 | Up | 444·404 | 283·283·282 | 812 | 36 | 848 | 1.386 | 61,2 % |
| m2 | exp_01 | Up | 457·424 | 295·293·293 | 849 | 32 | 881 | 1.386 | 63,6 % |
| m2 | exp_02 | Up | 392·439 | 278·277·276 | 773 | 58 | 831 | 1.386 | 60,0 % |
| m2 | exp_03 | Up | 351·431 | 261·261·260 | 736 | 46 | 782 | 1.386 | 56,4 % |
| **m2 subtotal** | — | — | — | — | **3.170** | **172** | **3.342** | **5.544** | **60,3 %** |
| m3 | exp_00 | Up | 462·329 | 264·264·263 | 770 | 21 | 791 | 1.386 | 57,1 % |
| m3 | exp_01 | Up | 462·311 | 258·258·257 | 747 | 26 | 773 | 1.386 | 55,8 % |
| m3 | exp_02 | Up | 462·336 | 266·266·266 | 763 | 35 | 798 | 1.386 | 57,6 % |
| m3 | exp_03 | Up | 429·336 | 255·255·255 | 748 | 17 | 765 | 1.287 | 59,4 % |
| **m3 subtotal** | — | — | — | — | **3.028** | **99** | **3.127** | **5.445** | **57,4 %** |
| m4 | exp_00 | Up | 429·429 | 286·286·286 | 825 | 33 | 858 | 1.287 | 66,7 % |
| m4 | exp_01 | Up | 429·420 | 283·283·283 | 833 | 16 | 849 | 1.287 | 66,0 % |
| m4 | exp_02 | Up | 429·421 | 284·283·283 | 827 | 23 | 850 | 1.287 | 66,0 % |
| m4 | exp_03 | Up | 429·429 | 286·286·286 | 828 | 30 | 858 | 1.287 | 66,7 % |
| **m4 subtotal** | — | — | — | — | **3.313** | **102** | **3.415** | **5.148** | **66,3 %** |
| **TOTAL GERAL** | — | — | — | — | **12.831** | **483** | **13.314** | **21.681** | **61,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:98, install/adb:12
- m2: erros → emulator/boot:133, install/adb:37, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:81, install/adb:18
- m4: erros → emulator/boot:95, install/adb:7

**Ações (19:12 local):** ciclo com **reboot do m3** + estreia do formato v2 da tabela. Durante o deploy do `rv_status.py` atualizado, o SCP para **m3 deu connect-timeout persistente (2 tentativas), gcloud RUNNING** → VM travada → `reset m3-exp02` (~22:09 UTC); SSH voltou em 20s, `rv_status.py` deployado, resume do run_experiment.sh → 5/5 Up. **9º reboot de VM travada** nas ~24h (m3 já havia dado blip às 18:00; desta vez travou de verdade). **Churn pós-reboot** (esperado): ao subir a trinca, exp_00/exp_02 haviam OOMado (Exit 137) → `docker start`; isso expulsou exp_03 → `docker start` do 4º (1x). Resultado: 5/5 Up, `free -g` folgado (6 usado). `rv_status.py` redeployado nas 4 VMs; `health_check.py` (local) com o novo montador. Total 61,4% (13.320/21.681). Formato v2 registrado no README + Marco.

## Ciclo 2026-07-08 19:38:48 (local)

| VM | container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | exp_00 | Up | 462·412·0 | 846 | 28 | 874 | 1.386 | 63,1 % |
| m1 | exp_01 | Up | 462·371·0 | 808 | 25 | 833 | 1.386 | 60,1 % |
| m1 | exp_02 | Up | 462·417·0 | 847 | 32 | 879 | 1.386 | 63,4 % |
| m1 | exp_03 | Up | 462·407·0 | 842 | 27 | 869 | 1.386 | 62,7 % |
| **m1** | — | — | — | **3.343** | **112** | **3.455** | **5.544** | **62,3 %** |
| m2 | exp_00 | Up | 451·404·0 | 822 | 33 | 855 | 1.386 | 61,7 % |
| m2 | exp_01 | Up | 462·424·0 | 856 | 30 | 886 | 1.386 | 63,9 % |
| m2 | exp_02 | Up | 404·439·0 | 785 | 58 | 843 | 1.386 | 60,8 % |
| m2 | exp_03 | Up | 363·431·0 | 747 | 47 | 794 | 1.386 | 57,3 % |
| **m2** | — | — | — | **3.210** | **168** | **3.378** | **5.544** | **60,9 %** |
| m3 | exp_00 | Up | 462·329·0 | 770 | 21 | 791 | 1.386 | 57,1 % |
| m3 | exp_01 | Up | 462·311·0 | 749 | 24 | 773 | 1.386 | 55,8 % |
| m3 | exp_02 | Up | 462·336·0 | 764 | 34 | 798 | 1.386 | 57,6 % |
| m3 | exp_03 | Up | 429·336·0 | 748 | 17 | 765 | 1.287 | 59,4 % |
| **m3** | — | — | — | **3.031** | **96** | **3.127** | **5.445** | **57,4 %** |
| m4 | exp_00 | Up | 429·429·0 | 826 | 32 | 858 | 1.287 | 66,7 % |
| m4 | exp_01 | Up | 429·426·0 | 839 | 16 | 855 | 1.287 | 66,4 % |
| m4 | exp_02 | Up | 429·428·0 | 833 | 24 | 857 | 1.287 | 66,6 % |
| m4 | exp_03 | Up | 429·429·0 | 830 | 28 | 858 | 1.287 | 66,7 % |
| **m4** | — | — | — | **3.328** | **100** | **3.428** | **5.148** | **66,6 %** |
| **TOTAL** | — | — | — | **12.912** | **476** | **13.388** | **21.681** | **61,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:99, install/adb:13
- m2: erros → emulator/boot:131, install/adb:35, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:77, install/adb:19
- m4: erros → emulator/boot:93, install/adb:7

**Ações (19:38 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual). Primeiro ciclo real no **formato v2-final** (sem reps, coluna `timeout`, sem sufixos subtotal/geral). **Cron de restart absorveu 3 OOMs** desde o ciclo anterior: m2/exp_00 (21:50 UTC), m3/exp_02 (22:20 UTC), m4/exp_03 (21:50 UTC) — todos Up automaticamente (5ª/6ª/7ª auto-recuperações do cron). m3 estável pós-reboot 19:09 (Up 14min, run vivo). Uptimes: m1 5h, m2 misto (7h + restarts recentes), m3 14min, m4 4h. Total **61,7%** (+74 vs 19:12). Nenhuma intervenção manual necessária.

## Ciclo 2026-07-08 19:56:09 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·416·0 | 850 | 28 | 878 | 1.386 | 63,3 % |
| exp_01 | Up | 462·375·0 | 812 | 25 | 837 | 1.386 | 60,4 % |
| exp_02 | Up | 462·421·0 | 851 | 32 | 883 | 1.386 | 63,7 % |
| exp_03 | Up | 462·411·0 | 846 | 27 | 873 | 1.386 | 63,0 % |
| **total** | — | 1.848·1.623·0 | **3.359** | **112** | **3.471** | **5.544** | **62,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 459·404·0 | 830 | 33 | 863 | 1.386 | 62,3 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 411·439·0 | 792 | 58 | 850 | 1.386 | 61,3 % |
| exp_03 | Up | 371·431·0 | 753 | 49 | 802 | 1.386 | 57,9 % |
| **total** | — | 1.703·1.698·0 | **3.234** | **167** | **3.401** | **5.544** | **61,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·329·0 | 772 | 19 | 791 | 1.386 | 57,1 % |
| exp_01 | Up | 462·311·0 | 751 | 22 | 773 | 1.386 | 55,8 % |
| exp_02 | Up | 462·336·0 | 764 | 34 | 798 | 1.386 | 57,6 % |
| exp_03 | Up | 429·336·0 | 750 | 15 | 765 | 1.287 | 59,4 % |
| **total** | — | 1.815·1.312·0 | **3.037** | **90** | **3.127** | **5.445** | **57,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 827 | 31 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 842 | 16 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 834 | 24 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 832 | 26 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.335** | **97** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.623·0 | 3.359 | 112 | 3.471 | 5.544 | 62,6 % |
| m2 | RUNNING | 1.703·1.698·0 | 3.234 | 167 | 3.401 | 5.544 | 61,3 % |
| m3 | RUNNING | 1.815·1.312·0 | 3.037 | 90 | 3.127 | 5.445 | 57,4 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.335 | 97 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **12.965** | **466** | **13.431** | **21.681** | **61,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:99, install/adb:13
- m2: erros → emulator/boot:131, install/adb:34, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:73, install/adb:17
- m4: erros → emulator/boot:90, install/adb:7

**Ações (19:56 local):** ciclo real no layout v2.1 (4 tabelas por VM + resumo geral). 4/4 exp + humanoid Up nas 4 VMs, run vivo. m4 exp_01 tinha OOMado no preview 19:51 → `docker start` (agora Up). m4 completou as passadas 60s **e** 180s (1.716·1.716) — vai iniciar a passada 300s; por isso trava em 66,7% (2/3 do alvo). m3 ainda com a 180s mais atrás (1.312) pós-reboot 19:09. Total 61,9% (13.431/21.681). A partir daqui os wakeups do monitor passam a disparar em hora cheia (20:00, 21:00, ...).

## Ciclo 2026-07-08 20:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·417·0 | 851 | 28 | 879 | 1.386 | 63,4 % |
| exp_01 | Up | 462·376·0 | 813 | 25 | 838 | 1.386 | 60,5 % |
| exp_02 | Up | 462·422·0 | 852 | 32 | 884 | 1.386 | 63,8 % |
| exp_03 | Up | 462·412·0 | 847 | 27 | 874 | 1.386 | 63,1 % |
| **total** | — | 1.848·1.627·0 | **3.363** | **112** | **3.475** | **5.544** | **62,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 460·404·0 | 831 | 33 | 864 | 1.386 | 62,3 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 413·439·0 | 794 | 58 | 852 | 1.386 | 61,5 % |
| exp_03 | Up | 372·431·0 | 754 | 49 | 803 | 1.386 | 57,9 % |
| **total** | — | 1.707·1.698·0 | **3.238** | **167** | **3.405** | **5.544** | **61,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·329·0 | 773 | 18 | 791 | 1.386 | 57,1 % |
| exp_01 | Up | 462·311·0 | 751 | 22 | 773 | 1.386 | 55,8 % |
| exp_02 | Up | 462·336·0 | 764 | 34 | 798 | 1.386 | 57,6 % |
| exp_03 | Up | 429·336·0 | 751 | 14 | 765 | 1.287 | 59,4 % |
| **total** | — | 1.815·1.312·0 | **3.039** | **88** | **3.127** | **5.445** | **57,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 827 | 31 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 843 | 15 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 835 | 23 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 832 | 26 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.337** | **95** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.627·0 | 3.363 | 112 | 3.475 | 5.544 | 62,7 % |
| m2 | RUNNING | 1.707·1.698·0 | 3.238 | 167 | 3.405 | 5.544 | 61,4 % |
| m3 | RUNNING | 1.815·1.312·0 | 3.039 | 88 | 3.127 | 5.445 | 57,4 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.337 | 95 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **12.977** | **462** | **13.439** | **21.681** | **62,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:99, install/adb:13
- m2: erros → emulator/boot:131, install/adb:34, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:73, install/adb:15
- m4: erros → emulator/boot:88, install/adb:7

## Ciclo 2026-07-08 20:04:12 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·418·0 | 852 | 28 | 880 | 1.386 | 63,5 % |
| exp_01 | Up | 462·377·0 | 814 | 25 | 839 | 1.386 | 60,5 % |
| exp_02 | Up | 462·423·0 | 853 | 32 | 885 | 1.386 | 63,9 % |
| exp_03 | Up | 462·413·0 | 848 | 27 | 875 | 1.386 | 63,1 % |
| **total** | — | 1.848·1.631·0 | **3.367** | **112** | **3.479** | **5.544** | **62,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 833 | 33 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 414·439·0 | 795 | 58 | 853 | 1.386 | 61,5 % |
| exp_03 | Up | 374·431·0 | 756 | 49 | 805 | 1.386 | 58,1 % |
| **total** | — | 1.712·1.698·0 | **3.243** | **167** | **3.410** | **5.544** | **61,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·329·0 | 774 | 17 | 791 | 1.386 | 57,1 % |
| exp_01 | Up | 462·311·0 | 751 | 22 | 773 | 1.386 | 55,8 % |
| exp_02 | Up | 462·336·0 | 764 | 34 | 798 | 1.386 | 57,6 % |
| exp_03 | Up | 429·336·0 | 751 | 14 | 765 | 1.287 | 59,4 % |
| **total** | — | 1.815·1.312·0 | **3.040** | **87** | **3.127** | **5.445** | **57,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 827 | 31 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 843 | 15 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 836 | 22 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 832 | 26 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.338** | **94** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.631·0 | 3.367 | 112 | 3.479 | 5.544 | 62,8 % |
| m2 | RUNNING | 1.712·1.698·0 | 3.243 | 167 | 3.410 | 5.544 | 61,5 % |
| m3 | RUNNING | 1.815·1.312·0 | 3.040 | 87 | 3.127 | 5.445 | 57,4 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.338 | 94 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **12.988** | **460** | **13.448** | **21.681** | **62,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:99, install/adb:13
- m2: erros → emulator/boot:131, install/adb:34, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:74, install/adb:13
- m4: erros → emulator/boot:87, install/adb:7

**Ações (20:04 local):** varredura SSH ativa — **m2 exp_01 estava Exited(137)** (OOM ~20:01) → `docker start` (agora Up, sem churn). Demais 3/3 exp + humanoid Up nas 4 VMs, run vivo em todas. m3 estável pós-reboot 19:09 (Up 39min). Cron de restart ativo (log mostra restarts recentes m2/exp_01 22:50 UTC, m3/exp_02 22:20, m4/exp_02 22:50 — todos absorvidos). m4 firme na passada 300s (1.716·1.716·0). Total ~62,0% (13.431-13.439/21.681; leve oscilação pelo resume do m2 exp_01). Cadência de wakeup alinhada à hora cheia (este ciclo às 20:00/20:04; próximo 21:00).

## Ciclo 2026-07-08 21:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·433·0 | 864 | 31 | 895 | 1.386 | 64,6 % |
| exp_01 | Up | 462·390·0 | 827 | 25 | 852 | 1.386 | 61,5 % |
| exp_02 | Up | 462·437·0 | 864 | 35 | 899 | 1.386 | 64,9 % |
| exp_03 | Up | 462·429·0 | 862 | 29 | 891 | 1.386 | 64,3 % |
| **total** | — | 1.848·1.689·0 | **3.417** | **120** | **3.537** | **5.544** | **63,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 835 | 31 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 440·439·0 | 820 | 59 | 879 | 1.386 | 63,4 % |
| exp_03 | Up | 400·431·0 | 778 | 53 | 831 | 1.386 | 60,0 % |
| **total** | — | 1.764·1.698·0 | **3.292** | **170** | **3.462** | **5.544** | **62,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·336·0 | 784 | 14 | 798 | 1.386 | 57,6 % |
| exp_01 | Up | 462·318·0 | 760 | 20 | 780 | 1.386 | 56,3 % |
| exp_02 | Up | 462·336·0 | 767 | 31 | 798 | 1.386 | 57,6 % |
| exp_03 | Up | 429·347·0 | 764 | 12 | 776 | 1.287 | 60,3 % |
| **total** | — | 1.815·1.337·0 | **3.075** | **77** | **3.152** | **5.445** | **57,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 829 | 29 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 848 | 10 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 840 | 18 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 835 | 23 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.352** | **80** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.689·0 | 3.417 | 120 | 3.537 | 5.544 | 63,8 % |
| m2 | RUNNING | 1.764·1.698·0 | 3.292 | 170 | 3.462 | 5.544 | 62,4 % |
| m3 | RUNNING | 1.815·1.337·0 | 3.075 | 77 | 3.152 | 5.445 | 57,9 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.352 | 80 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **13.136** | **447** | **13.583** | **21.681** | **62,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:104, install/adb:16
- m2: erros → emulator/boot:133, install/adb:35, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:72, install/adb:5
- m4: erros → emulator/boot:74, install/adb:6

## Ciclo 2026-07-08 21:02:43 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·433·0 | 864 | 31 | 895 | 1.386 | 64,6 % |
| exp_01 | Up | 462·390·0 | 827 | 25 | 852 | 1.386 | 61,5 % |
| exp_02 | Up | 462·437·0 | 864 | 35 | 899 | 1.386 | 64,9 % |
| exp_03 | Up | 462·430·0 | 862 | 30 | 892 | 1.386 | 64,4 % |
| **total** | — | 1.848·1.690·0 | **3.417** | **121** | **3.538** | **5.544** | **63,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 835 | 31 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 441·439·0 | 821 | 59 | 880 | 1.386 | 63,5 % |
| exp_03 | Up | 402·431·0 | 780 | 53 | 833 | 1.386 | 60,1 % |
| **total** | — | 1.767·1.698·0 | **3.295** | **170** | **3.465** | **5.544** | **62,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·336·0 | 784 | 14 | 798 | 1.386 | 57,6 % |
| exp_01 | Up | 462·319·0 | 761 | 20 | 781 | 1.386 | 56,3 % |
| exp_02 | Up | 462·336·0 | 767 | 31 | 798 | 1.386 | 57,6 % |
| exp_03 | Up | 429·348·0 | 765 | 12 | 777 | 1.287 | 60,4 % |
| **total** | — | 1.815·1.339·0 | **3.077** | **77** | **3.154** | **5.445** | **57,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 829 | 29 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 848 | 10 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 840 | 18 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 835 | 23 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.352** | **80** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.690·0 | 3.417 | 121 | 3.538 | 5.544 | 63,8 % |
| m2 | RUNNING | 1.767·1.698·0 | 3.295 | 170 | 3.465 | 5.544 | 62,5 % |
| m3 | RUNNING | 1.815·1.339·0 | 3.077 | 77 | 3.154 | 5.445 | 57,9 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.352 | 80 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **13.141** | **448** | **13.589** | **21.681** | **62,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:105, install/adb:16
- m2: erros → emulator/boot:133, install/adb:35, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:72, install/adb:5
- m4: erros → emulator/boot:74, install/adb:6

**Ações (21:02 local):** varredura SSH ativa — 4/4 exp + humanoid Up nas 4 VMs, run vivo em todas. Ciclo LIMPO (sem restart/reboot manual). Cron de restart absorveu OOMs isolados: m2/exp_01 às 00:00 UTC (21:00 local), m4/exp_01 às 23:50 UTC (20:50) — todos Up automaticamente. Uptimes: m1 7h, m2 8h (+ restarts recentes), m3 2h (pós-reboot 19:09), m4 5h (+ restarts). m4 firme na passada 300s (1.716·1.716·0). m3 progredindo na 180s (1.337). Total **62,6%** (13.583/21.681; +152 vs 20:04). Nenhuma intervenção manual necessária.

## Ciclo 2026-07-08 21:17:58 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·437·0 | 868 | 31 | 899 | 1.386 | 64,9 % |
| exp_01 | Up | 462·394·0 | 831 | 25 | 856 | 1.386 | 61,8 % |
| exp_02 | Up | 462·440·0 | 867 | 35 | 902 | 1.386 | 65,1 % |
| exp_03 | Up | 462·433·0 | 865 | 30 | 895 | 1.386 | 64,6 % |
| **total** | — | 1.848·1.704·0 | **3.431** | **121** | **3.552** | **5.544** | **64,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 836 | 30 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 448·439·0 | 826 | 61 | 887 | 1.386 | 64,0 % |
| exp_03 | Up | 408·431·0 | 785 | 54 | 839 | 1.386 | 60,5 % |
| **total** | — | 1.780·1.698·0 | **3.306** | **172** | **3.478** | **5.544** | **62,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·340·0 | 788 | 14 | 802 | 1.386 | 57,9 % |
| exp_01 | Up | 462·323·0 | 764 | 21 | 785 | 1.386 | 56,6 % |
| exp_02 | Up | 462·339·0 | 771 | 30 | 801 | 1.386 | 57,8 % |
| exp_03 | Up | 429·351·0 | 768 | 12 | 780 | 1.287 | 60,6 % |
| **total** | — | 1.815·1.353·0 | **3.091** | **77** | **3.168** | **5.445** | **58,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·0 | 830 | 28 | 858 | 1.287 | 66,7 % |
| exp_01 | Up | 429·429·0 | 849 | 9 | 858 | 1.287 | 66,7 % |
| exp_02 | Up | 429·429·0 | 842 | 16 | 858 | 1.287 | 66,7 % |
| exp_03 | Up | 429·429·0 | 837 | 21 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.716·1.716·0 | **3.358** | **74** | **3.432** | **5.148** | **66,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.704·0 | 3.431 | 121 | 3.552 | 5.544 | 64,1 % |
| m2 | RUNNING | 1.780·1.698·0 | 3.306 | 172 | 3.478 | 5.544 | 62,7 % |
| m3 | RUNNING | 1.815·1.353·0 | 3.091 | 77 | 3.168 | 5.445 | 58,2 % |
| m4 | RUNNING | 1.716·1.716·0 | 3.358 | 74 | 3.432 | 5.148 | 66,7 % |
| **TOTAL** | — | — | **13.186** | **444** | **13.630** | **21.681** | **62,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:105, install/adb:16
- m2: erros → emulator/boot:132, install/adb:38, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:72, install/adb:5
- m4: erros → emulator/boot:70, install/adb:4

**Ações (21:17 local):** varredura SSH ativa nas 4 VMs. m2/exp_01 estava `Exited(137)` (OOM, ~2 min antes) → `docker start exp_01` manual imediato, voltou Up 2s. Demais: m1 4/4 Up 7h (limpo), m3 4/4 Up 2h (limpo, pós-reboot 19:09), m4 4/4 Up (churn benigno, uptimes 7–57min, todos Up). Run vivo (4 procs) em TODAS as 4 VMs. Cron de restart absorvendo OOMs (m2/exp_01 00:10 UTC, m4/exp_02 00:10 UTC). Total **62,9%** (13.630/21.681; +47 vs 21:02). m4 firme na 300s (1.716·1.716·0). m3 na 180s (1.353). 1 restart manual (m2/exp_01).

## Marco 2026-07-08 ~21:25 (local) — m4 "travada" era transição lenta 180s→300s

**Sintoma (percebido pelo usuário):** m4 com 4 containers idênticos (429·429·0, feito 858/ctr, 66,7%) e `feito` total travado em 3.432 por >1h (20:04→21:17).

**Investigação dentro dos containers:**
- CPU ~380–395% nos 4 (trabalhando), mem 19/31 GiB, load 41.
- `RV_TIMEOUTS=180` nos 4 → ainda na passada 180s (NÃO 300s).
- `by_timeout`: 60s=1711+5, 180s=1648+68 (=1716, **100% completa**), **300s ausente** (0 tasks).
- run_experiment.sh (pid 1666) bloqueado em `docker wait exp_00..03` — só avança para 300s quando os 4 saírem.
- Nenhum marcador `passada TIMEOUT=300s` no run.log → 300s nunca iniciou.

**Causa raiz:** a passada 180s estava completa, mas a transição exige que os **4 containers saiam ~simultaneamente** (`docker wait`). Sob churn de OOM (containers re-executando 180s já feito e sendo mortos/reiniciados), levou ~1h para os 4 saírem juntos. **Não era travamento permanente** — resolveu sozinha às ~21:24: `docker wait` retornou → `compose down` → `compose up` com `RV_TIMEOUTS=300`. Passada 300s agora rodando (4 containers Up, `docker wait` re-armado).

**RISCO SISTÊMICO IDENTIFICADO (requer autorização p/ corrigir):** `restart_exited.sh` reinicia QUALQUER container `exited`, sem distinguir exit 0 (fim limpo de passada) de exit 137 (OOM). Na transição de passada, isso reinicia containers que saíram limpos para avançar → briga com o `docker wait` e prolonga a transição. Provável contribuinte do atraso de ~1h. m1/m2/m3 baterão na mesma transição 180→300. **Correção proposta:** cron só reiniciar containers com ExitCode==137. NÃO aplicado (mudança de script = precisa de autorização).

**CORREÇÃO APLICADA (~21:28 local, autorizada pelo usuário):** `restart_exited.sh` atualizado nas 4 VMs para reiniciar SOMENTE containers com `ExitCode==137` (OOM), nunca exit 0 (fim limpo de passada). Versão canônica agora no repo (`experimento-20260706/scripts/restart_exited.sh`) com comentário explicando o livelock. scp + chmod +x OK em m1/m2/m3/m4; crontab `*/10` inalterado (mesmo path). Isso elimina a briga do cron com a transição de passada — m1/m2/m3 devem avançar 180s→300s sem o atraso de ~1h visto na m4.

## Ciclo 2026-07-08 21:37:11 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·442·0 | 872 | 32 | 904 | 1.386 | 65,2 % |
| exp_01 | Up | 462·399·0 | 834 | 27 | 861 | 1.386 | 62,1 % |
| exp_02 | Up | 462·445·0 | 872 | 35 | 907 | 1.386 | 65,4 % |
| exp_03 | Up | 462·437·0 | 869 | 30 | 899 | 1.386 | 64,9 % |
| **total** | — | 1.848·1.723·0 | **3.447** | **124** | **3.571** | **5.544** | **64,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 838 | 28 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 457·439·0 | 835 | 61 | 896 | 1.386 | 64,6 % |
| exp_03 | Up | 417·431·0 | 794 | 54 | 848 | 1.386 | 61,2 % |
| **total** | — | 1.798·1.698·0 | **3.326** | **170** | **3.496** | **5.544** | **63,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·344·0 | 792 | 14 | 806 | 1.386 | 58,2 % |
| exp_01 | Up | 462·328·0 | 769 | 21 | 790 | 1.386 | 57,0 % |
| exp_02 | Up | 462·344·0 | 776 | 30 | 806 | 1.386 | 58,2 % |
| exp_03 | Up | 429·356·0 | 773 | 12 | 785 | 1.287 | 61,0 % |
| **total** | — | 1.815·1.372·0 | **3.110** | **77** | **3.187** | **5.445** | **58,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·2 | 831 | 29 | 860 | 1.287 | 66,8 % |
| exp_01 | Up | 429·429·3 | 850 | 11 | 861 | 1.287 | 66,9 % |
| exp_02 | Up | 429·429·3 | 842 | 19 | 861 | 1.287 | 66,9 % |
| exp_03 | Up | 429·429·3 | 837 | 24 | 861 | 1.287 | 66,9 % |
| **total** | — | 1.716·1.716·11 | **3.360** | **83** | **3.443** | **5.148** | **66,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.723·0 | 3.447 | 124 | 3.571 | 5.544 | 64,4 % |
| m2 | RUNNING | 1.798·1.698·0 | 3.326 | 170 | 3.496 | 5.544 | 63,1 % |
| m3 | RUNNING | 1.815·1.372·0 | 3.110 | 77 | 3.187 | 5.445 | 58,5 % |
| m4 | RUNNING | 1.716·1.716·11 | 3.360 | 83 | 3.443 | 5.148 | 66,9 % |
| **TOTAL** | — | — | **13.243** | **454** | **13.697** | **21.681** | **63,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:17
- m2: erros → emulator/boot:130, install/adb:38, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:72, install/adb:5
- m4: erros → emulator/boot:78, install/adb:5

**Ações (21:37 local):** varredura SSH ativa nas 4 VMs. m2/exp_01 estava `Exited(137)` (OOM, ~54s antes) → `docker start exp_01` manual imediato, voltou Up 2s. Demais: m1 4/4 Up 7h (limpo), m3 4/4 Up 2h (limpo, pós-reboot 19:09), m4 4/4 Up 10min (transição 180→300 concluída). Run vivo (4 procs) em TODAS as 4 VMs. Cron corrigido confirmado funcionando (m2 log 00:30 UTC = novo formato "OOM exit 137"). **m4 entrou na passada 300s** (1.716·1.716·11) — transição limpa, sem o atraso de ~1h da m4 anterior. Total **63,2%** (13.697/21.681; +67 vs 21:17). Deltas: m1 +19, m2 +18, m3 +19, m4 +11. 1 restart manual (m2/exp_01).

## Ciclo 2026-07-08 22:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·447·0 | 877 | 32 | 909 | 1.386 | 65,6 % |
| exp_01 | Up | 462·399·0 | 834 | 27 | 861 | 1.386 | 62,1 % |
| exp_02 | Up | 462·450·0 | 877 | 35 | 912 | 1.386 | 65,8 % |
| exp_03 | Up | 462·442·0 | 874 | 30 | 904 | 1.386 | 65,2 % |
| **total** | — | 1.848·1.738·0 | **3.462** | **124** | **3.586** | **5.544** | **64,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 840 | 61 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 428·431·0 | 805 | 54 | 859 | 1.386 | 62,0 % |
| **total** | — | 1.814·1.698·0 | **3.343** | **169** | **3.512** | **5.544** | **63,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·350·0 | 798 | 14 | 812 | 1.386 | 58,6 % |
| exp_01 | Up | 462·334·0 | 774 | 22 | 796 | 1.386 | 57,4 % |
| exp_02 | Up | 462·349·0 | 781 | 30 | 811 | 1.386 | 58,5 % |
| exp_03 | Up | 429·361·0 | 778 | 12 | 790 | 1.287 | 61,4 % |
| **total** | — | 1.815·1.394·0 | **3.131** | **78** | **3.209** | **5.445** | **58,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·6 | 834 | 30 | 864 | 1.287 | 67,1 % |
| exp_01 | Up | 429·429·6 | 853 | 11 | 864 | 1.287 | 67,1 % |
| exp_02 | Up | 429·429·7 | 846 | 19 | 865 | 1.287 | 67,2 % |
| exp_03 | Up | 429·429·8 | 840 | 26 | 866 | 1.287 | 67,3 % |
| **total** | — | 1.716·1.716·27 | **3.373** | **86** | **3.459** | **5.148** | **67,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.738·0 | 3.462 | 124 | 3.586 | 5.544 | 64,7 % |
| m2 | RUNNING | 1.814·1.698·0 | 3.343 | 169 | 3.512 | 5.544 | 63,3 % |
| m3 | RUNNING | 1.815·1.394·0 | 3.131 | 78 | 3.209 | 5.445 | 58,9 % |
| m4 | RUNNING | 1.716·1.716·27 | 3.373 | 86 | 3.459 | 5.148 | 67,2 % |
| **TOTAL** | — | — | **13.309** | **457** | **13.766** | **21.681** | **63,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:17
- m2: erros → emulator/boot:129, install/adb:38, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:73, install/adb:5
- m4: erros → emulator/boot:79, install/adb:7

## Ciclo 2026-07-08 22:03:32 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·448·0 | 878 | 32 | 910 | 1.386 | 65,7 % |
| exp_01 | Up | 462·399·0 | 834 | 27 | 861 | 1.386 | 62,1 % |
| exp_02 | Up | 462·451·0 | 878 | 35 | 913 | 1.386 | 65,9 % |
| exp_03 | Up | 462·443·0 | 875 | 30 | 905 | 1.386 | 65,3 % |
| **total** | — | 1.848·1.741·0 | **3.465** | **124** | **3.589** | **5.544** | **64,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 841 | 60 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 430·431·0 | 806 | 55 | 861 | 1.386 | 62,1 % |
| **total** | — | 1.816·1.698·0 | **3.345** | **169** | **3.514** | **5.544** | **63,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·350·0 | 798 | 14 | 812 | 1.386 | 58,6 % |
| exp_01 | Up | 462·335·0 | 775 | 22 | 797 | 1.386 | 57,5 % |
| exp_02 | Up | 462·350·0 | 782 | 30 | 812 | 1.386 | 58,6 % |
| exp_03 | Up | 429·365·0 | 779 | 15 | 794 | 1.287 | 61,7 % |
| **total** | — | 1.815·1.400·0 | **3.134** | **81** | **3.215** | **5.445** | **59,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·7 | 835 | 30 | 865 | 1.287 | 67,2 % |
| exp_01 | Up | 429·429·7 | 854 | 11 | 865 | 1.287 | 67,2 % |
| exp_02 | Up | 429·429·7 | 846 | 19 | 865 | 1.287 | 67,2 % |
| exp_03 | Up | 429·429·9 | 841 | 26 | 867 | 1.287 | 67,4 % |
| **total** | — | 1.716·1.716·30 | **3.376** | **86** | **3.462** | **5.148** | **67,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.741·0 | 3.465 | 124 | 3.589 | 5.544 | 64,7 % |
| m2 | RUNNING | 1.816·1.698·0 | 3.345 | 169 | 3.514 | 5.544 | 63,4 % |
| m3 | RUNNING | 1.815·1.400·0 | 3.134 | 81 | 3.215 | 5.445 | 59,0 % |
| m4 | RUNNING | 1.716·1.716·30 | 3.376 | 86 | 3.462 | 5.148 | 67,2 % |
| **TOTAL** | — | — | **13.320** | **460** | **13.780** | **21.681** | **63,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:17
- m2: erros → emulator/boot:129, install/adb:38, timeout:2
- m2: 1 APK(s) só-falha → com.yogeshpaliyal.keypass_1442.apk
- m3: erros → emulator/boot:73, install/adb:8
- m4: erros → emulator/boot:79, install/adb:7

**Ações (22:03 local):** varredura SSH ativa nas 4 VMs — ciclo LIMPO, 4/4 exp + humanoid Up em todas, run vivo (4 procs). NENHUM restart manual. Cron corrigido absorveu OOMs isolados: m1/exp_01 00:50 UTC + m2/exp_02 01:00 UTC (novo formato "OOM exit 137"). m2 com 3 containers Up 3min (churn benigno, todos Up). m4 firme na passada 300s (1.716·1.716·30, subindo devagar do teto — normal, tasks 300s demoram). m1/m2/m3 ainda na 180s. Total **63,6%** (13.780/21.681; +83 vs 21:37). Deltas: m1 +18, m2 +18, m3 +28, m4 +19.

## Ciclo 2026-07-08 23:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 890 | 34 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·399·0 | 838 | 23 | 861 | 1.386 | 62,1 % |
| exp_02 | Up | 462·462·0 | 889 | 35 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·456·0 | 888 | 30 | 918 | 1.386 | 66,2 % |
| **total** | — | 1.848·1.779·0 | **3.505** | **122** | **3.627** | **5.544** | **65,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 850 | 51 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 442·431·0 | 815 | 58 | 873 | 1.386 | 63,0 % |
| **total** | — | 1.828·1.698·0 | **3.363** | **163** | **3.526** | **5.544** | **63,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·366·0 | 810 | 18 | 828 | 1.386 | 59,7 % |
| exp_01 | Up | 462·349·0 | 788 | 23 | 811 | 1.386 | 58,5 % |
| exp_02 | Up | 462·364·0 | 795 | 31 | 826 | 1.386 | 59,6 % |
| exp_03 | Up | 429·378·0 | 791 | 16 | 807 | 1.287 | 62,7 % |
| **total** | — | 1.815·1.457·0 | **3.184** | **88** | **3.272** | **5.445** | **60,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·16 | 844 | 30 | 874 | 1.287 | 67,9 % |
| exp_01 | Up | 429·429·16 | 863 | 11 | 874 | 1.287 | 67,9 % |
| exp_02 | Up | 429·429·20 | 859 | 19 | 878 | 1.287 | 68,2 % |
| exp_03 | Up | 429·429·19 | 850 | 27 | 877 | 1.287 | 68,1 % |
| **total** | — | 1.716·1.716·71 | **3.416** | **87** | **3.503** | **5.148** | **68,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.779·0 | 3.505 | 122 | 3.627 | 5.544 | 65,4 % |
| m2 | RUNNING | 1.828·1.698·0 | 3.363 | 163 | 3.526 | 5.544 | 63,6 % |
| m3 | RUNNING | 1.815·1.457·0 | 3.184 | 88 | 3.272 | 5.445 | 60,1 % |
| m4 | RUNNING | 1.716·1.716·71 | 3.416 | 87 | 3.503 | 5.148 | 68,0 % |
| **TOTAL** | — | — | **13.468** | **460** | **13.928** | **21.681** | **64,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:15
- m2: erros → emulator/boot:129, install/adb:29, timeout:5
- m3: erros → emulator/boot:77, install/adb:11
- m4: erros → emulator/boot:79, install/adb:8

## Ciclo 2026-07-08 23:03:33 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 890 | 34 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·399·0 | 839 | 22 | 861 | 1.386 | 62,1 % |
| exp_02 | Up | 462·462·0 | 889 | 35 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·457·0 | 889 | 30 | 919 | 1.386 | 66,3 % |
| **total** | — | 1.848·1.780·0 | **3.507** | **121** | **3.628** | **5.544** | **65,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 851 | 50 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 443·431·0 | 816 | 58 | 874 | 1.386 | 63,1 % |
| **total** | — | 1.829·1.698·0 | **3.365** | **162** | **3.527** | **5.544** | **63,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·367·0 | 811 | 18 | 829 | 1.386 | 59,8 % |
| exp_01 | Up | 462·350·0 | 789 | 23 | 812 | 1.386 | 58,6 % |
| exp_02 | Up | 462·365·0 | 795 | 32 | 827 | 1.386 | 59,7 % |
| exp_03 | Up | 429·379·0 | 792 | 16 | 808 | 1.287 | 62,8 % |
| **total** | — | 1.815·1.461·0 | **3.187** | **89** | **3.276** | **5.445** | **60,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·16 | 844 | 30 | 874 | 1.287 | 67,9 % |
| exp_01 | Up | 429·429·17 | 864 | 11 | 875 | 1.287 | 68,0 % |
| exp_02 | Up | 429·429·21 | 860 | 19 | 879 | 1.287 | 68,3 % |
| exp_03 | Up | 429·429·19 | 850 | 27 | 877 | 1.287 | 68,1 % |
| **total** | — | 1.716·1.716·73 | **3.418** | **87** | **3.505** | **5.148** | **68,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.780·0 | 3.507 | 121 | 3.628 | 5.544 | 65,4 % |
| m2 | RUNNING | 1.829·1.698·0 | 3.365 | 162 | 3.527 | 5.544 | 63,6 % |
| m3 | RUNNING | 1.815·1.461·0 | 3.187 | 89 | 3.276 | 5.445 | 60,2 % |
| m4 | RUNNING | 1.716·1.716·73 | 3.418 | 87 | 3.505 | 5.148 | 68,1 % |
| **TOTAL** | — | — | **13.477** | **459** | **13.936** | **21.681** | **64,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:106, install/adb:15
- m2: erros → emulator/boot:128, install/adb:29, timeout:5
- m3: erros → emulator/boot:78, install/adb:11
- m4: erros → emulator/boot:79, install/adb:8

**Ações (23:03 local):** varredura SSH ativa nas 4 VMs — ciclo LIMPO, 4/4 exp + humanoid Up em todas, run vivo (4 procs). NENHUM restart manual. Cron corrigido absorveu OOMs: m1/exp_02 + m2/exp_01 às 02:00 UTC (novo formato "OOM exit 137"). m1/m2 com containers Up 3min (churn benigno, todos Up). m4 subindo na 300s (1.716·1.716·73, 68,1%). m1 quase fechando a 180s (2 containers em 462·462, slot 180=1.780). m3 avançando na 180s (1.461). Total **64,3%** (13.936/21.681; +156 vs 22:03). Deltas: m1 +39, m2 +13, m3 +61, m4 +43.

## Marco 2026-07-08 ~23:17-23:21 (local) — m2 travada (banner timeout) → reboot + resume

**Gatilho:** task de background "resume m2" (disparada fora do ciclo horário) falhou com exit 255 ("resume m2 disparado" + `client_loop: send disconnect: Broken pipe`). Investigação inicial (23:13) mostrou m2 SAUDÁVEL via SSH: 4/4 exp + humanoid Up, 1 run_experiment.sh real (pid 1704, sem duplicata — o `count=4` era inflação do grep casando wrapper+comando).
**Escalada:** ~60s depois, SSH da m2 passou a dar `Connection timed out during banner exchange`. Protocolo aplicado: gcloud confirmou `m2-exp02 RUNNING`; 3 tentativas SSH consecutivas (ConnectTimeout 20/25/40, ServerAliveInterval) em ~90s → TODAS banner timeout. Diagnóstico: sshd não responde ao handshake = travamento real (pressão de memória severa / VM hung), não blip.
**Ação:** `gcloud compute instances reset m2-exp02` às 23:17:52. SSH voltou em ~20s (uptime "up 0 min"). Resume `nohup ./scripts/run_experiment.sh m2` às ~23:19. Verificação 23:21: 5/5 (4 exp + humanoid) Up 2min, **run_procs=1** (sem duplicata). m2 recuperada.
**Nota:** reboot #10 do experimento. run_experiment.sh idempotente via tasks.json → resume não reprocessa. Sem perda de dados (tasks completas já persistidas).

## Ciclo 2026-07-08 23:33:07 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 892 | 32 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·404·0 | 845 | 21 | 866 | 1.386 | 62,5 % |
| exp_02 | Up | 462·462·0 | 890 | 34 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.790·0 | **3.521** | **117** | **3.638** | **5.544** | **65,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 856 | 45 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 448·431·0 | 826 | 53 | 879 | 1.386 | 63,4 % |
| **total** | — | 1.834·1.698·0 | **3.380** | **152** | **3.532** | **5.544** | **63,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·374·0 | 818 | 18 | 836 | 1.386 | 60,3 % |
| exp_01 | Up | 462·357·0 | 796 | 23 | 819 | 1.386 | 59,1 % |
| exp_02 | Up | 462·372·0 | 801 | 33 | 834 | 1.386 | 60,2 % |
| exp_03 | Up | 429·387·0 | 800 | 16 | 816 | 1.287 | 63,4 % |
| **total** | — | 1.815·1.490·0 | **3.215** | **90** | **3.305** | **5.445** | **60,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·21 | 849 | 30 | 879 | 1.287 | 68,3 % |
| exp_01 | Up | 429·429·21 | 868 | 11 | 879 | 1.287 | 68,3 % |
| exp_02 | Up | 429·429·26 | 865 | 19 | 884 | 1.287 | 68,7 % |
| exp_03 | Up | 429·429·24 | 855 | 27 | 882 | 1.287 | 68,5 % |
| **total** | — | 1.716·1.716·92 | **3.437** | **87** | **3.524** | **5.148** | **68,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.790·0 | 3.521 | 117 | 3.638 | 5.544 | 65,6 % |
| m2 | RUNNING | 1.834·1.698·0 | 3.380 | 152 | 3.532 | 5.544 | 63,7 % |
| m3 | RUNNING | 1.815·1.490·0 | 3.215 | 90 | 3.305 | 5.445 | 60,7 % |
| m4 | RUNNING | 1.716·1.716·92 | 3.437 | 87 | 3.524 | 5.148 | 68,5 % |
| **TOTAL** | — | — | **13.553** | **446** | **13.999** | **21.681** | **64,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:99, install/adb:18
- m2: erros → emulator/boot:125, install/adb:25, timeout:2
- m3: erros → emulator/boot:79, install/adb:11
- m4: erros → emulator/boot:79, install/adb:8

**Ações (23:33 local):** varredura SSH ativa nas 4 VMs. **m2/exp_02** OOM (Exited 137, 25s) → `docker start exp_02` manual imediato (recuperado). Cron absorveu outros OOMs: m1/exp_03 + m2/exp_01 às 02:30 UTC (formato "OOM exit 137"). m3 (4/4 Up 4h) e m4 (4/4 Up 2h) ciclos limpos. **`run_procs=2` investigado e BENIGNO**: pgrep casa o processo real (`/bin/bash ./scripts/run_experiment.sh`) + o wrapper `bash -c … nohup … disown` que o lançou e ficou pendurado — 1 campanha real por VM, sem duplicata (padrão uniforme nas 4). m2 confirmada recomposta pós-reboot #10 (progredindo). Total **64,6%** (13.999/21.681; +63 vs 23:03). Deltas: m1 +10, m2 +5, m3 +29, m4 +19. Ordem: m4 68,5% > m1 65,6% > m2 63,7% > m3 60,7%.

## Ciclo 2026-07-09 00:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 895 | 29 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·411·0 | 851 | 22 | 873 | 1.386 | 63,0 % |
| exp_02 | Up | 462·462·0 | 891 | 33 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.797·0 | **3.531** | **114** | **3.645** | **5.544** | **65,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 857 | 44 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 448·431·0 | 833 | 46 | 879 | 1.386 | 63,4 % |
| **total** | — | 1.834·1.698·0 | **3.388** | **144** | **3.532** | **5.544** | **63,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·382·0 | 824 | 20 | 844 | 1.386 | 60,9 % |
| exp_01 | Up | 462·363·0 | 802 | 23 | 825 | 1.386 | 59,5 % |
| exp_02 | Up | 462·379·0 | 808 | 33 | 841 | 1.386 | 60,7 % |
| exp_03 | Up | 429·394·0 | 807 | 16 | 823 | 1.287 | 63,9 % |
| **total** | — | 1.815·1.518·0 | **3.241** | **92** | **3.333** | **5.445** | **61,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·25 | 853 | 30 | 883 | 1.287 | 68,6 % |
| exp_01 | Up | 429·429·26 | 873 | 11 | 884 | 1.287 | 68,7 % |
| exp_02 | Up | 429·429·30 | 869 | 19 | 888 | 1.287 | 69,0 % |
| exp_03 | Up | 429·429·28 | 859 | 27 | 886 | 1.287 | 68,8 % |
| **total** | — | 1.716·1.716·109 | **3.454** | **87** | **3.541** | **5.148** | **68,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.797·0 | 3.531 | 114 | 3.645 | 5.544 | 65,7 % |
| m2 | RUNNING | 1.834·1.698·0 | 3.388 | 144 | 3.532 | 5.544 | 63,7 % |
| m3 | RUNNING | 1.815·1.518·0 | 3.241 | 92 | 3.333 | 5.445 | 61,2 % |
| m4 | RUNNING | 1.716·1.716·109 | 3.454 | 87 | 3.541 | 5.148 | 68,8 % |
| **TOTAL** | — | — | **13.614** | **437** | **14.051** | **21.681** | **64,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:18
- m2: erros → emulator/boot:124, install/adb:19, timeout:1
- m3: erros → emulator/boot:79, install/adb:13
- m4: erros → emulator/boot:79, install/adb:8

## Ciclo 2026-07-09 00:02:52 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 895 | 29 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·412·0 | 852 | 22 | 874 | 1.386 | 63,1 % |
| exp_02 | Up | 462·462·0 | 892 | 32 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.798·0 | **3.533** | **113** | **3.646** | **5.544** | **65,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 857 | 44 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 450·431·0 | 835 | 46 | 881 | 1.386 | 63,6 % |
| **total** | — | 1.836·1.698·0 | **3.390** | **144** | **3.534** | **5.544** | **63,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·383·0 | 825 | 20 | 845 | 1.386 | 61,0 % |
| exp_01 | Up | 462·364·0 | 802 | 24 | 826 | 1.386 | 59,6 % |
| exp_02 | Up | 462·379·0 | 808 | 33 | 841 | 1.386 | 60,7 % |
| exp_03 | Up | 429·394·0 | 807 | 16 | 823 | 1.287 | 63,9 % |
| **total** | — | 1.815·1.520·0 | **3.242** | **93** | **3.335** | **5.445** | **61,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·26 | 854 | 30 | 884 | 1.287 | 68,7 % |
| exp_01 | Up | 429·429·26 | 873 | 11 | 884 | 1.287 | 68,7 % |
| exp_02 | Up | 429·429·30 | 869 | 19 | 888 | 1.287 | 69,0 % |
| exp_03 | Up | 429·429·30 | 860 | 28 | 888 | 1.287 | 69,0 % |
| **total** | — | 1.716·1.716·112 | **3.456** | **88** | **3.544** | **5.148** | **68,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.798·0 | 3.533 | 113 | 3.646 | 5.544 | 65,8 % |
| m2 | RUNNING | 1.836·1.698·0 | 3.390 | 144 | 3.534 | 5.544 | 63,7 % |
| m3 | RUNNING | 1.815·1.520·0 | 3.242 | 93 | 3.335 | 5.445 | 61,2 % |
| m4 | RUNNING | 1.716·1.716·112 | 3.456 | 88 | 3.544 | 5.148 | 68,8 % |
| **TOTAL** | — | — | **13.621** | **438** | **14.059** | **21.681** | **64,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:95, install/adb:18
- m2: erros → emulator/boot:124, install/adb:19, timeout:1
- m3: erros → emulator/boot:80, install/adb:13
- m4: erros → emulator/boot:79, install/adb:9

**Ações (00:02 local):** varredura SSH ativa nas 4 VMs — ciclo LIMPO, 16/16 exp + 4 humanoid Up. NENHUM restart manual. Cron absorveu OOMs: m1/exp_03 (02:30 UTC) + m2/exp_02 (03:00 UTC, trinca da m2 recomposta Up 2min) — formato "OOM exit 137". m3 (Up 5h) e m4 (Up 3h) sem intervenção. `run_procs=2` benigno (real+wrapper) confirmado nas 4. m4 na 300s (112, 68,8%, subindo do teto ~66,7% — normal). m1 fechou a 180s (1.798, quase completa). m3 subindo bem na 180s (1.520). Total **64,8%** (14.059/21.681; +60 vs 23:33). Deltas: m1 +8, m2 +2, m3 +30, m4 +20. Ordem: m4 68,8% > m1 65,8% > m2 63,7% > m3 61,2%.

## Ciclo 2026-07-09 01:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 902 | 22 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·425·0 | 865 | 22 | 887 | 1.386 | 64,0 % |
| exp_02 | Up | 462·462·0 | 897 | 27 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 899 | 25 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.811·0 | **3.563** | **96** | **3.659** | **5.544** | **66,0 %** |

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·400·0 | 836 | 26 | 862 | 1.386 | 62,2 % |
| exp_01 | Up | 462·378·0 | 814 | 26 | 840 | 1.386 | 60,6 % |
| exp_02 | Up | 462·393·0 | 822 | 33 | 855 | 1.386 | 61,7 % |
| exp_03 | Up | 429·409·0 | 820 | 18 | 838 | 1.287 | 65,1 % |
| **total** | — | 1.815·1.580·0 | **3.292** | **103** | **3.395** | **5.445** | **62,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·36 | 862 | 32 | 894 | 1.287 | 69,5 % |
| exp_01 | Up | 429·429·37 | 881 | 14 | 895 | 1.287 | 69,5 % |
| exp_02 | Up | 429·429·41 | 877 | 22 | 899 | 1.287 | 69,9 % |
| exp_03 | Up | 429·429·42 | 868 | 32 | 900 | 1.287 | 69,9 % |
| **total** | — | 1.716·1.716·156 | **3.488** | **100** | **3.588** | **5.148** | **69,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.811·0 | 3.563 | 96 | 3.659 | 5.544 | 66,0 % |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | RUNNING | 1.815·1.580·0 | 3.292 | 103 | 3.395 | 5.445 | 62,4 % |
| m4 | RUNNING | 1.716·1.716·156 | 3.488 | 100 | 3.588 | 5.148 | 69,7 % |
| **TOTAL** | — | — | **10.343** | **299** | **10.642** | **16.137** | **65,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:91, install/adb:5
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:87, install/adb:16
- m4: erros → emulator/boot:90, install/adb:10

## Ciclo 2026-07-09 01:10:00 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 902 | 22 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·427·0 | 867 | 22 | 889 | 1.386 | 64,1 % |
| exp_02 | Up | 462·462·0 | 898 | 26 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 899 | 25 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.813·0 | **3.566** | **95** | **3.661** | **5.544** | **66,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 839 | 27 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 859 | 27 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 857 | 44 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 461·431·0 | 845 | 47 | 892 | 1.386 | 64,4 % |
| **total** | — | 1.847·1.698·0 | **3.400** | **145** | **3.545** | **5.544** | **63,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·403·0 | 838 | 27 | 865 | 1.386 | 62,4 % |
| exp_01 | Up | 462·380·0 | 816 | 26 | 842 | 1.386 | 60,8 % |
| exp_02 | Up | 462·395·0 | 824 | 33 | 857 | 1.386 | 61,8 % |
| exp_03 | Up | 429·411·0 | 822 | 18 | 840 | 1.287 | 65,3 % |
| **total** | — | 1.815·1.589·0 | **3.300** | **104** | **3.404** | **5.445** | **62,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·37 | 863 | 32 | 895 | 1.287 | 69,5 % |
| exp_01 | Up | 429·429·38 | 882 | 14 | 896 | 1.287 | 69,6 % |
| exp_02 | Up | 429·429·42 | 878 | 22 | 900 | 1.287 | 69,9 % |
| exp_03 | Up | 429·429·43 | 869 | 32 | 901 | 1.287 | 70,0 % |
| **total** | — | 1.716·1.716·160 | **3.492** | **100** | **3.592** | **5.148** | **69,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.813·0 | 3.566 | 95 | 3.661 | 5.544 | 66,0 % |
| m2 | RUNNING | 1.847·1.698·0 | 3.400 | 145 | 3.545 | 5.544 | 63,9 % |
| m3 | RUNNING | 1.815·1.589·0 | 3.300 | 104 | 3.404 | 5.445 | 62,5 % |
| m4 | RUNNING | 1.716·1.716·160 | 3.492 | 100 | 3.592 | 5.148 | 69,8 % |
| **TOTAL** | — | — | **13.758** | **444** | **14.202** | **21.681** | **65,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:93, install/adb:2
- m2: erros → emulator/boot:124, install/adb:20, timeout:1
- m3: erros → emulator/boot:87, install/adb:17
- m4: erros → emulator/boot:90, install/adb:10

**Ações (01:10 local):** ciclo do cron 01:00 registrou **m2 SSH_FALHOU** (alvo caiu p/ 16.137). Varredura ativa: m1/m3/m4 OK (m1/exp_03 OOM Exited-137 → `docker start` manual, recuperado). m2 = **banner timeout em 3 tentativas consecutivas** (ConnectTimeout 20/25/40, ServerAliveInterval 5), RUNNING no gcloud → travamento real → **reboot #11** (`gcloud compute instances reset m2-exp02` 01:06:24). SSH voltou em ~30s (uptime 0 min). Resume `nohup run_experiment.sh m2` 01:07; verificação: 5/5 Up + **run_reais=1** (sem duplicata). Total **65,5%** (14.202/21.681; +143 vs 00:02). Deltas: m1 +15, m2 +11, m3 +69, m4 +48. Ordem: m4 69,8% > m1 66,0% > m2 63,9% > m3 62,5%.

## Marco 2026-07-09 ~01:03-01:08 (local) — m2 travada de novo (banner timeout) → reboot #11 + resume

**Gatilho:** ciclo do cron local 01:00 marcou `m2: SSH_FALHOU` (health_check pulou a VM; alvo do resumo caiu p/ 16.137 = 3 VMs). Ao retomar o ciclo horário 01:03, m2 deu banner timeout na 1ª tentativa SSH.
**Escalada:** protocolo VM-travada — gcloud confirmou `m2-exp02 RUNNING`; 3 tentativas SSH (ConnectTimeout 20→25→40, ServerAliveInterval 5) TODAS `Connection timed out during banner exchange`. sshd não responde ao handshake = travamento real (pressão de memória, VM hung), padrão idêntico ao reboot #10 (~2h antes).
**Ação:** `gcloud compute instances reset m2-exp02 --zone us-central1-f` às 01:06:24. SSH voltou em ~30s (uptime "up 0 min"). Resume `nohup ./scripts/run_experiment.sh m2` ~01:07. Verificação: 5/5 (4 exp + humanoid) Up 2min, **run_reais=1** (pgrep `/bin/bash ./scripts/run_experiment.sh m2` = 1, sem duplicata).
**Nota:** reboot #11. **m2 travou DUAS vezes em ~2h (23:17 e 01:06)** — é a VM mais instável do conjunto (também a de maior err: 145). Resume idempotente via tasks.json, sem perda de dados. Padrão recorrente de banner-timeout na m2 a vigiar nos próximos ciclos.

## Ciclo 2026-07-09 02:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·441·0 | 878 | 25 | 903 | 1.386 | 65,2 % |
| exp_02 | Up | 462·462·0 | 901 | 23 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 901 | 23 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.827·0 | **3.584** | **91** | **3.675** | **5.544** | **66,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 840 | 26 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 861 | 25 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 858 | 43 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 462·431·0 | 851 | 42 | 893 | 1.386 | 64,4 % |
| **total** | — | 1.848·1.698·0 | **3.410** | **136** | **3.546** | **5.544** | **64,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·415·0 | 849 | 28 | 877 | 1.386 | 63,3 % |
| exp_01 | Up | 462·391·0 | 827 | 26 | 853 | 1.386 | 61,5 % |
| exp_02 | Up | 462·408·0 | 834 | 36 | 870 | 1.386 | 62,8 % |
| exp_03 | Up | 429·424·0 | 833 | 20 | 853 | 1.287 | 66,3 % |
| **total** | — | 1.815·1.638·0 | **3.343** | **110** | **3.453** | **5.445** | **63,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·46 | 871 | 33 | 904 | 1.287 | 70,2 % |
| exp_01 | Up | 429·429·46 | 890 | 14 | 904 | 1.287 | 70,2 % |
| exp_02 | Up | 429·429·50 | 886 | 22 | 908 | 1.287 | 70,6 % |
| exp_03 | Up | 429·429·51 | 877 | 32 | 909 | 1.287 | 70,6 % |
| **total** | — | 1.716·1.716·193 | **3.524** | **101** | **3.625** | **5.148** | **70,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.827·0 | 3.584 | 91 | 3.675 | 5.544 | 66,3 % |
| m2 | RUNNING | 1.848·1.698·0 | 3.410 | 136 | 3.546 | 5.544 | 64,0 % |
| m3 | RUNNING | 1.815·1.638·0 | 3.343 | 110 | 3.453 | 5.445 | 63,4 % |
| m4 | RUNNING | 1.716·1.716·193 | 3.524 | 101 | 3.625 | 5.148 | 70,4 % |
| **TOTAL** | — | — | **13.861** | **438** | **14.299** | **21.681** | **66,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:88, install/adb:3
- m2: erros → emulator/boot:116, install/adb:19, timeout:1
- m3: erros → emulator/boot:90, install/adb:20
- m4: erros → emulator/boot:90, install/adb:11

## Ciclo 2026-07-09 02:04:21 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·442·0 | 879 | 25 | 904 | 1.386 | 65,2 % |
| exp_02 | Up | 462·462·0 | 901 | 23 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 901 | 23 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.828·0 | **3.585** | **91** | **3.676** | **5.544** | **66,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·404·0 | 840 | 26 | 866 | 1.386 | 62,5 % |
| exp_01 | Up | 462·424·0 | 862 | 24 | 886 | 1.386 | 63,9 % |
| exp_02 | Up | 462·439·0 | 858 | 43 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 462·431·0 | 851 | 42 | 893 | 1.386 | 64,4 % |
| **total** | — | 1.848·1.698·0 | **3.411** | **135** | **3.546** | **5.544** | **64,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·416·0 | 850 | 28 | 878 | 1.386 | 63,3 % |
| exp_01 | Up | 462·392·0 | 828 | 26 | 854 | 1.386 | 61,6 % |
| exp_02 | Up | 462·409·0 | 835 | 36 | 871 | 1.386 | 62,8 % |
| exp_03 | Up | 429·425·0 | 834 | 20 | 854 | 1.287 | 66,4 % |
| **total** | — | 1.815·1.642·0 | **3.347** | **110** | **3.457** | **5.445** | **63,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·47 | 872 | 33 | 905 | 1.287 | 70,3 % |
| exp_01 | Up | 429·429·47 | 891 | 14 | 905 | 1.287 | 70,3 % |
| exp_02 | Up | 429·429·51 | 887 | 22 | 909 | 1.287 | 70,6 % |
| exp_03 | Up | 429·429·52 | 878 | 32 | 910 | 1.287 | 70,7 % |
| **total** | — | 1.716·1.716·197 | **3.528** | **101** | **3.629** | **5.148** | **70,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.828·0 | 3.585 | 91 | 3.676 | 5.544 | 66,3 % |
| m2 | RUNNING | 1.848·1.698·0 | 3.411 | 135 | 3.546 | 5.544 | 64,0 % |
| m3 | RUNNING | 1.815·1.642·0 | 3.347 | 110 | 3.457 | 5.445 | 63,5 % |
| m4 | RUNNING | 1.716·1.716·197 | 3.528 | 101 | 3.629 | 5.148 | 70,5 % |
| **TOTAL** | — | — | **13.871** | **437** | **14.308** | **21.681** | **66,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:88, install/adb:3
- m2: erros → emulator/boot:115, install/adb:19, timeout:1
- m3: erros → emulator/boot:90, install/adb:20
- m4: erros → emulator/boot:90, install/adb:11

**Ações (02:04 local):** ciclo do cron 02:00 OK (m2 sobreviveu, sem SSH_FALHOU). Varredura ativa: 16/16 exp + 4 humanoid Up. NENHUM restart manual (cron absorveu OOMs isolados). **m2 diagnosticada** (slot 180=1.698 estático há 4 ciclos): NÃO é deadlock — `free` mostra 10g usados/20g disponíveis, `RV_TIMEOUTS=180` nos 4 containers (passada correta), logs com emuladores bootando ao vivo (02:03). A estagnação da 180s é efeito dos 2 reboots (23:17+01:06): cada reboot custa ~30min de re-boot dos 4 emuladores + skip de tasks via tasks.json. m2 lenta-mas-viva. m3/m4 limpas (Up 7h/5h). Total **66,0%** (14.308/21.681; +106 vs 01:10). Deltas: m1 +15, m2 +1, m3 +53, m4 +37. Ordem: m4 70,5% > m1 66,3% > m3 63,5% > m2 64,0% (m3 ultrapassou m2). m2 é a lanterna efetiva por instabilidade.

## Ciclo 2026-07-09 03:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 908 | 16 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·457·0 | 892 | 27 | 919 | 1.386 | 66,3 % |
| exp_02 | Up | 462·462·0 | 903 | 21 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 903 | 21 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.843·0 | **3.606** | **85** | **3.691** | **5.544** | **66,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·407·0 | 846 | 23 | 869 | 1.386 | 62,7 % |
| exp_01 | Up | 462·426·0 | 867 | 21 | 888 | 1.386 | 64,1 % |
| exp_02 | Up | 462·439·0 | 863 | 38 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 462·431·0 | 860 | 33 | 893 | 1.386 | 64,4 % |
| **total** | — | 1.848·1.703·0 | **3.436** | **115** | **3.551** | **5.544** | **64,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·425·0 | 859 | 28 | 887 | 1.386 | 64,0 % |
| exp_01 | Up | 462·402·0 | 836 | 28 | 864 | 1.386 | 62,3 % |
| exp_02 | Up | 462·418·0 | 843 | 37 | 880 | 1.386 | 63,5 % |
| exp_03 | Up | 429·429·0 | 838 | 20 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.674·0 | **3.376** | **113** | **3.489** | **5.445** | **64,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·56 | 881 | 33 | 914 | 1.287 | 71,0 % |
| exp_01 | Up | 429·429·56 | 900 | 14 | 914 | 1.287 | 71,0 % |
| exp_02 | Up | 429·429·60 | 896 | 22 | 918 | 1.287 | 71,3 % |
| exp_03 | Up | 429·429·61 | 887 | 32 | 919 | 1.287 | 71,4 % |
| **total** | — | 1.716·1.716·233 | **3.564** | **101** | **3.665** | **5.148** | **71,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.843·0 | 3.606 | 85 | 3.691 | 5.544 | 66,6 % |
| m2 | RUNNING | 1.848·1.703·0 | 3.436 | 115 | 3.551 | 5.544 | 64,1 % |
| m3 | RUNNING | 1.815·1.674·0 | 3.376 | 113 | 3.489 | 5.445 | 64,1 % |
| m4 | RUNNING | 1.716·1.716·233 | 3.564 | 101 | 3.665 | 5.148 | 71,2 % |
| **TOTAL** | — | — | **13.982** | **414** | **14.396** | **21.681** | **66,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:80, install/adb:5
- m2: erros → emulator/boot:100, install/adb:14, timeout:1
- m3: erros → emulator/boot:93, install/adb:20
- m4: erros → emulator/boot:90, install/adb:11

## Ciclo 2026-07-09 03:02:57 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 908 | 16 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·457·0 | 892 | 27 | 919 | 1.386 | 66,3 % |
| exp_02 | Up | 462·462·0 | 903 | 21 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 903 | 21 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.843·0 | **3.606** | **85** | **3.691** | **5.544** | **66,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·407·0 | 846 | 23 | 869 | 1.386 | 62,7 % |
| exp_01 | Up | 462·427·0 | 868 | 21 | 889 | 1.386 | 64,1 % |
| exp_02 | Up | 462·439·0 | 864 | 37 | 901 | 1.386 | 65,0 % |
| exp_03 | Up | 462·431·0 | 860 | 33 | 893 | 1.386 | 64,4 % |
| **total** | — | 1.848·1.704·0 | **3.438** | **114** | **3.552** | **5.544** | **64,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·426·0 | 860 | 28 | 888 | 1.386 | 64,1 % |
| exp_01 | Up | 462·402·0 | 836 | 28 | 864 | 1.386 | 62,3 % |
| exp_02 | Up | 462·418·0 | 843 | 37 | 880 | 1.386 | 63,5 % |
| exp_03 | Up | 429·429·0 | 838 | 20 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.675·0 | **3.377** | **113** | **3.490** | **5.445** | **64,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·56 | 881 | 33 | 914 | 1.287 | 71,0 % |
| exp_01 | Up | 429·429·56 | 900 | 14 | 914 | 1.287 | 71,0 % |
| exp_02 | Up | 429·429·61 | 897 | 22 | 919 | 1.287 | 71,4 % |
| exp_03 | Up | 429·429·61 | 887 | 32 | 919 | 1.287 | 71,4 % |
| **total** | — | 1.716·1.716·234 | **3.565** | **101** | **3.666** | **5.148** | **71,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.843·0 | 3.606 | 85 | 3.691 | 5.544 | 66,6 % |
| m2 | RUNNING | 1.848·1.704·0 | 3.438 | 114 | 3.552 | 5.544 | 64,1 % |
| m3 | RUNNING | 1.815·1.675·0 | 3.377 | 113 | 3.490 | 5.445 | 64,1 % |
| m4 | RUNNING | 1.716·1.716·234 | 3.565 | 101 | 3.666 | 5.148 | 71,2 % |
| **TOTAL** | — | — | **13.986** | **413** | **14.399** | **21.681** | **66,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:80, install/adb:5
- m2: erros → emulator/boot:100, install/adb:13, timeout:1
- m3: erros → emulator/boot:93, install/adb:20
- m4: erros → emulator/boot:90, install/adb:11

**Ações (03:02 local):** ciclo do cron 03:00 OK (m2 RUNNING, sem SSH_FALHOU). Varredura ativa: 16/16 exp + 4 humanoid Up. NENHUM restart manual (cron absorveu OOMs: m1/exp_00, m3/exp_03). **m2 estabilizada**: Up 2h sem novo reboot, slot 180s VOLTOU a subir (1.698→1.704, +6) confirmando o diagnóstico "lenta-mas-viva". m4 (Up 6h) na 300s (234, 71,2%). m1 quase fechando a 180s (1.843). Total **66,4%** (14.399/21.681; +91 vs 02:04). Deltas: m1 +15, m2 +6, m3 +33, m4 +37. Ordem: m4 71,2% > m1 66,6% > m2 = m3 64,1%. m2 recuperando o ritmo; err da m2 caindo (135→114).

## Ciclo 2026-07-09 04:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·7 | 912 | 19 | 931 | 1.386 | 67,2 % |
| exp_01 | Up | 462·462·8 | 902 | 30 | 932 | 1.386 | 67,2 % |
| exp_02 | Up | 462·462·7 | 908 | 23 | 931 | 1.386 | 67,2 % |
| exp_03 | Up | 462·462·7 | 910 | 21 | 931 | 1.386 | 67,2 % |
| **total** | — | 1.848·1.848·29 | **3.632** | **93** | **3.725** | **5.544** | **67,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·421·0 | 860 | 23 | 883 | 1.386 | 63,7 % |
| exp_01 | Up | 462·441·0 | 879 | 24 | 903 | 1.386 | 65,2 % |
| exp_02 | Up | 462·443·0 | 872 | 33 | 905 | 1.386 | 65,3 % |
| exp_03 | Up | 462·439·0 | 870 | 31 | 901 | 1.386 | 65,0 % |
| **total** | — | 1.848·1.744·0 | **3.481** | **111** | **3.592** | **5.544** | **64,8 %** |

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·66 | 891 | 33 | 924 | 1.287 | 71,8 % |
| exp_01 | Up | 429·429·66 | 910 | 14 | 924 | 1.287 | 71,8 % |
| exp_02 | Up | 429·429·71 | 904 | 25 | 929 | 1.287 | 72,2 % |
| exp_03 | Up | 429·429·72 | 895 | 35 | 930 | 1.287 | 72,3 % |
| **total** | — | 1.716·1.716·275 | **3.600** | **107** | **3.707** | **5.148** | **72,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·29 | 3.632 | 93 | 3.725 | 5.544 | 67,2 % |
| m2 | RUNNING | 1.848·1.744·0 | 3.481 | 111 | 3.592 | 5.544 | 64,8 % |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·275 | 3.600 | 107 | 3.707 | 5.148 | 72,0 % |
| **TOTAL** | — | — | **10.713** | **311** | **11.024** | **16.236** | **67,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:6
- m2: erros → emulator/boot:101, install/adb:10
- m3: SSH inacessível — ssh timeout (sem ação)
- m4: erros → emulator/boot:96, install/adb:11

## Ciclo 2026-07-09 04:06:58 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·8 | 913 | 19 | 932 | 1.386 | 67,2 % |
| exp_01 | Up | 462·462·9 | 903 | 30 | 933 | 1.386 | 67,3 % |
| exp_02 | Up | 462·462·8 | 909 | 23 | 932 | 1.386 | 67,2 % |
| exp_03 | Up | 462·462·8 | 911 | 21 | 932 | 1.386 | 67,2 % |
| **total** | — | 1.848·1.848·33 | **3.636** | **93** | **3.729** | **5.544** | **67,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·422·0 | 861 | 23 | 884 | 1.386 | 63,8 % |
| exp_01 | Up | 462·443·0 | 881 | 24 | 905 | 1.386 | 65,3 % |
| exp_02 | Up | 462·445·0 | 873 | 34 | 907 | 1.386 | 65,4 % |
| exp_03 | Up | 462·441·0 | 872 | 31 | 903 | 1.386 | 65,2 % |
| **total** | — | 1.848·1.751·0 | **3.487** | **112** | **3.599** | **5.544** | **64,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·438·0 | 869 | 31 | 900 | 1.386 | 64,9 % |
| exp_01 | Up | 462·414·0 | 847 | 29 | 876 | 1.386 | 63,2 % |
| exp_02 | Up | 462·432·0 | 853 | 41 | 894 | 1.386 | 64,5 % |
| exp_03 | Up | 429·429·0 | 843 | 15 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.713·0 | **3.412** | **116** | **3.528** | **5.445** | **64,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·68 | 891 | 35 | 926 | 1.287 | 72,0 % |
| exp_01 | Up | 429·429·67 | 910 | 15 | 925 | 1.287 | 71,9 % |
| exp_02 | Up | 429·429·72 | 905 | 25 | 930 | 1.287 | 72,3 % |
| exp_03 | Up | 429·429·73 | 896 | 35 | 931 | 1.287 | 72,3 % |
| **total** | — | 1.716·1.716·280 | **3.602** | **110** | **3.712** | **5.148** | **72,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·33 | 3.636 | 93 | 3.729 | 5.544 | 67,3 % |
| m2 | RUNNING | 1.848·1.751·0 | 3.487 | 112 | 3.599 | 5.544 | 64,9 % |
| m3 | RUNNING | 1.815·1.713·0 | 3.412 | 116 | 3.528 | 5.445 | 64,8 % |
| m4 | RUNNING | 1.716·1.716·280 | 3.602 | 110 | 3.712 | 5.148 | 72,1 % |
| **TOTAL** | — | — | **14.137** | **431** | **14.568** | **21.681** | **67,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:6
- m2: erros → emulator/boot:101, install/adb:11
- m3: erros → emulator/boot:100, install/adb:16
- m4: erros → emulator/boot:99, install/adb:11

**Ações (04:06 local):** ⚠️ **m3 travada** (banner timeout) — provavelmente travou o cron das 04:00 (entrada ausente no cron.out). Varredura: m1/m2/m4 OK. m3 = banner timeout em 3 tentativas (ConnectTimeout 20/25/40), RUNNING no gcloud → **reboot #12** (`reset m3-exp02` 04:04:56). SSH voltou em ~20s → resume 04:06 → **5/5 Up, run_reais=1** (sem duplicata). m1 fez **transição limpa 180→300** (slot 180=1.848 completo, 300=33; o "Up 38min" dos 4 containers era o compose down/up da transição, NÃO reboot — confirma que o fix do cron eliminou o travamento de transição). m2 estável (Up 3h, +47). m4 (Up 7h) na 300s (280, 72,1%). Total **67,2%** (14.568/21.681; +169 vs 03:02). Deltas: m1 +38, m2 +47, m3 +38, m4 +46. Ordem: m4 72,1% > m1 67,3% > m2 64,9% ≈ m3 64,8%.

## Marco 2026-07-09 ~04:02-04:07 (local) — m3 travada (banner timeout) → reboot #12 + resume

**Gatilho:** ciclo do cron local 04:00 NÃO registrou entrada no cron.out (health_check provavelmente travou no SSH da m3). Varredura horária 04:02: m3 banner timeout na 1ª tentativa.
**Escalada:** protocolo VM-travada — gcloud `m3-exp02 RUNNING`; 3 tentativas SSH (ConnectTimeout 20→25→40, ServerAliveInterval 5) TODAS `Connection timed out during banner exchange`. Travamento real (pressão de memória/VM hung), mesmo padrão dos reboots #10/#11 da m2.
**Ação:** `gcloud compute instances reset m3-exp02 --zone us-central1-f` às 04:04:56. SSH voltou em ~20s (uptime 0 min). Resume `nohup ./scripts/run_experiment.sh m3` 04:06. Verificação: 5/5 (4 exp + humanoid) Up 55s, **run_reais=1** (sem duplicata).
**Nota:** reboot #12. Agora a instabilidade de banner-timeout atingiu TAMBÉM a m3 (antes só a m2) — é um padrão de infra do cluster (oversubscrição de memória 40g vs 31g), não específico de uma VM. m3 estava saudável até 03:02 (Up 8h). Resume idempotente via tasks.json, sem perda de dados. Vigiar recorrência nas 4 VMs.

## Ciclo 2026-07-09 05:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·17 | 922 | 19 | 941 | 1.386 | 67,9 % |
| exp_01 | Up | 462·462·18 | 911 | 31 | 942 | 1.386 | 68,0 % |
| exp_02 | Up | 462·462·17 | 918 | 23 | 941 | 1.386 | 67,9 % |
| exp_03 | Up | 462·462·17 | 919 | 22 | 941 | 1.386 | 67,9 % |
| **total** | — | 1.848·1.848·69 | **3.670** | **95** | **3.765** | **5.544** | **67,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·436·0 | 872 | 26 | 898 | 1.386 | 64,8 % |
| exp_01 | Up | 462·455·0 | 893 | 24 | 917 | 1.386 | 66,2 % |
| exp_02 | Up | 462·458·0 | 886 | 34 | 920 | 1.386 | 66,4 % |
| exp_03 | Up | 462·454·0 | 884 | 32 | 916 | 1.386 | 66,1 % |
| **total** | — | 1.848·1.803·0 | **3.535** | **116** | **3.651** | **5.544** | **65,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·438·0 | 870 | 30 | 900 | 1.386 | 64,9 % |
| exp_01 | Up | 462·414·0 | 848 | 28 | 876 | 1.386 | 63,2 % |
| exp_02 | Up | 462·432·0 | 853 | 41 | 894 | 1.386 | 64,5 % |
| exp_03 | Up | 429·429·0 | 843 | 15 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.713·0 | **3.414** | **114** | **3.528** | **5.445** | **64,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·78 | 899 | 37 | 936 | 1.287 | 72,7 % |
| exp_01 | Up | 429·429·77 | 918 | 17 | 935 | 1.287 | 72,6 % |
| exp_02 | Up | 429·429·81 | 913 | 26 | 939 | 1.287 | 73,0 % |
| exp_03 | Up | 429·429·84 | 906 | 36 | 942 | 1.287 | 73,2 % |
| **total** | — | 1.716·1.716·320 | **3.636** | **116** | **3.752** | **5.148** | **72,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·69 | 3.670 | 95 | 3.765 | 5.544 | 67,9 % |
| m2 | RUNNING | 1.848·1.803·0 | 3.535 | 116 | 3.651 | 5.544 | 65,9 % |
| m3 | RUNNING | 1.815·1.713·0 | 3.414 | 114 | 3.528 | 5.445 | 64,8 % |
| m4 | RUNNING | 1.716·1.716·320 | 3.636 | 116 | 3.752 | 5.148 | 72,9 % |
| **TOTAL** | — | — | **14.255** | **441** | **14.696** | **21.681** | **67,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:8
- m2: erros → emulator/boot:103, install/adb:13
- m3: erros → emulator/boot:98, install/adb:16
- m4: erros → emulator/boot:102, install/adb:14

## Ciclo 2026-07-09 05:02:44 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·17 | 922 | 19 | 941 | 1.386 | 67,9 % |
| exp_01 | Up | 462·462·19 | 912 | 31 | 943 | 1.386 | 68,0 % |
| exp_02 | Up | 462·462·17 | 918 | 23 | 941 | 1.386 | 67,9 % |
| exp_03 | Up | 462·462·18 | 920 | 22 | 942 | 1.386 | 68,0 % |
| **total** | — | 1.848·1.848·71 | **3.672** | **95** | **3.767** | **5.544** | **67,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·437·0 | 873 | 26 | 899 | 1.386 | 64,9 % |
| exp_01 | Up | 462·456·0 | 894 | 24 | 918 | 1.386 | 66,2 % |
| exp_02 | Up | 462·458·0 | 886 | 34 | 920 | 1.386 | 66,4 % |
| exp_03 | Up | 462·455·0 | 885 | 32 | 917 | 1.386 | 66,2 % |
| **total** | — | 1.848·1.806·0 | **3.538** | **116** | **3.654** | **5.544** | **65,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·438·0 | 871 | 29 | 900 | 1.386 | 64,9 % |
| exp_01 | Up | 462·414·0 | 848 | 28 | 876 | 1.386 | 63,2 % |
| exp_02 | Up | 462·432·0 | 853 | 41 | 894 | 1.386 | 64,5 % |
| exp_03 | Up | 429·429·0 | 843 | 15 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.713·0 | **3.415** | **113** | **3.528** | **5.445** | **64,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·78 | 899 | 37 | 936 | 1.287 | 72,7 % |
| exp_01 | Up | 429·429·77 | 918 | 17 | 935 | 1.287 | 72,6 % |
| exp_02 | Up | 429·429·81 | 913 | 26 | 939 | 1.287 | 73,0 % |
| exp_03 | Up | 429·429·84 | 906 | 36 | 942 | 1.287 | 73,2 % |
| **total** | — | 1.716·1.716·320 | **3.636** | **116** | **3.752** | **5.148** | **72,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·71 | 3.672 | 95 | 3.767 | 5.544 | 67,9 % |
| m2 | RUNNING | 1.848·1.806·0 | 3.538 | 116 | 3.654 | 5.544 | 65,9 % |
| m3 | RUNNING | 1.815·1.713·0 | 3.415 | 113 | 3.528 | 5.445 | 64,8 % |
| m4 | RUNNING | 1.716·1.716·320 | 3.636 | 116 | 3.752 | 5.148 | 72,9 % |
| **TOTAL** | — | — | **14.261** | **440** | **14.701** | **21.681** | **67,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:8
- m2: erros → emulator/boot:103, install/adb:13
- m3: erros → emulator/boot:97, install/adb:16
- m4: erros → emulator/boot:102, install/adb:14

**Ações (05:02 local):** ciclo do cron 05:00 OK (4 RUNNING; o 04:00 tinha pego m3 SSH_FALHOU = o reboot #12). Varredura ativa: 16/16 exp + 4 humanoid Up. NENHUM restart manual (cron absorveu OOMs isolados). m1 subindo bem na 300s (71). m4 na 300s (320, 72,9%). m2 estável (Up 4h, +55). **m3 feito estático (3.528, +0)**: esperado — reboot #12 às 04:04, gastou a última hora re-bootando 4 emuladores + skip via tasks.json (slot 180=1.713 igual); Up 32min, deve retomar a 180s no próximo ciclo (mesmo padrão da m2 pós-reboot). Total **67,8%** (14.701/21.681; +133 vs 04:06). Deltas: m1 +38, m2 +55, m3 +0, m4 +40. Ordem: m4 72,9% > m1 67,9% > m2 65,9% > m3 64,8%.

## Ciclo 2026-07-09 06:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·27 | 931 | 20 | 951 | 1.386 | 68,6 % |
| exp_01 | Up | 462·462·29 | 921 | 32 | 953 | 1.386 | 68,8 % |
| exp_02 | Up | 462·462·27 | 927 | 24 | 951 | 1.386 | 68,6 % |
| exp_03 | Up | 462·462·28 | 929 | 23 | 952 | 1.386 | 68,7 % |
| **total** | — | 1.848·1.848·111 | **3.708** | **99** | **3.807** | **5.544** | **68,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·451·0 | 887 | 26 | 913 | 1.386 | 65,9 % |
| exp_01 | Up | 462·462·0 | 900 | 24 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 891 | 33 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 892 | 32 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.837·0 | **3.570** | **115** | **3.685** | **5.544** | **66,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·438·0 | 881 | 19 | 900 | 1.386 | 64,9 % |
| exp_01 | Up | 462·418·0 | 857 | 23 | 880 | 1.386 | 63,5 % |
| exp_02 | Up | 462·432·0 | 853 | 41 | 894 | 1.386 | 64,5 % |
| exp_03 | Up | 429·429·0 | 847 | 11 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.717·0 | **3.438** | **94** | **3.532** | **5.445** | **64,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·87 | 908 | 37 | 945 | 1.287 | 73,4 % |
| exp_01 | Up | 429·429·86 | 927 | 17 | 944 | 1.287 | 73,3 % |
| exp_02 | Up | 429·429·91 | 923 | 26 | 949 | 1.287 | 73,7 % |
| exp_03 | Up | 429·429·94 | 916 | 36 | 952 | 1.287 | 74,0 % |
| **total** | — | 1.716·1.716·358 | **3.674** | **116** | **3.790** | **5.148** | **73,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·111 | 3.708 | 99 | 3.807 | 5.544 | 68,7 % |
| m2 | RUNNING | 1.848·1.837·0 | 3.570 | 115 | 3.685 | 5.544 | 66,5 % |
| m3 | RUNNING | 1.815·1.717·0 | 3.438 | 94 | 3.532 | 5.445 | 64,9 % |
| m4 | RUNNING | 1.716·1.716·358 | 3.674 | 116 | 3.790 | 5.148 | 73,6 % |
| **TOTAL** | — | — | **14.390** | **424** | **14.814** | **21.681** | **68,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:12
- m2: erros → emulator/boot:103, install/adb:12
- m3: erros → emulator/boot:84, install/adb:10
- m4: erros → emulator/boot:102, install/adb:14

## Ciclo 2026-07-09 06:01:44 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·28 | 932 | 20 | 952 | 1.386 | 68,7 % |
| exp_01 | Up | 462·462·29 | 921 | 32 | 953 | 1.386 | 68,8 % |
| exp_02 | Up | 462·462·28 | 928 | 24 | 952 | 1.386 | 68,7 % |
| exp_03 | Up | 462·462·28 | 929 | 23 | 952 | 1.386 | 68,7 % |
| **total** | — | 1.848·1.848·113 | **3.710** | **99** | **3.809** | **5.544** | **68,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·451·0 | 887 | 26 | 913 | 1.386 | 65,9 % |
| exp_01 | Up | 462·462·0 | 900 | 24 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 891 | 33 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 892 | 32 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.837·0 | **3.570** | **115** | **3.685** | **5.544** | **66,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·438·0 | 881 | 19 | 900 | 1.386 | 64,9 % |
| exp_01 | Up | 462·419·0 | 858 | 23 | 881 | 1.386 | 63,6 % |
| exp_02 | Up | 462·432·0 | 853 | 41 | 894 | 1.386 | 64,5 % |
| exp_03 | Up | 429·429·0 | 847 | 11 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.718·0 | **3.439** | **94** | **3.533** | **5.445** | **64,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·88 | 909 | 37 | 946 | 1.287 | 73,5 % |
| exp_01 | Up | 429·429·87 | 928 | 17 | 945 | 1.287 | 73,4 % |
| exp_02 | Up | 429·429·91 | 923 | 26 | 949 | 1.287 | 73,7 % |
| exp_03 | Up | 429·429·94 | 916 | 36 | 952 | 1.287 | 74,0 % |
| **total** | — | 1.716·1.716·360 | **3.676** | **116** | **3.792** | **5.148** | **73,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·113 | 3.710 | 99 | 3.809 | 5.544 | 68,7 % |
| m2 | RUNNING | 1.848·1.837·0 | 3.570 | 115 | 3.685 | 5.544 | 66,5 % |
| m3 | RUNNING | 1.815·1.718·0 | 3.439 | 94 | 3.533 | 5.445 | 64,9 % |
| m4 | RUNNING | 1.716·1.716·360 | 3.676 | 116 | 3.792 | 5.148 | 73,7 % |
| **TOTAL** | — | — | **14.395** | **424** | **14.819** | **21.681** | **68,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:87, install/adb:12
- m2: erros → emulator/boot:103, install/adb:12
- m3: erros → emulator/boot:84, install/adb:10
- m4: erros → emulator/boot:102, install/adb:14

**Ações (06:01 local):** ciclo do cron 06:00 OK (4 RUNNING). Varredura ativa: 16/16 exp + 4 humanoid Up. NENHUM restart manual (cron absorveu OOMs isolados na m2/m3). **m3 confirmou recuperação** pós-reboot #12: feito voltou a subir (3.528→3.533, +5) e slot 180s avançou (1.713→1.718), err caiu (113→94) — validando a previsão do ciclo anterior. m1 subindo na 300s (113). m4 (Up 9h) na 300s (360, 73,7%). m2 estável (+31). Total **68,4%** (14.819/21.681; +118 vs 05:02). Deltas: m1 +42, m2 +31, m3 +5, m4 +40. Ordem: m4 73,7% > m1 68,7% > m2 66,5% > m3 64,9%.

## Ciclo 2026-07-09 07:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·39 | 940 | 23 | 963 | 1.386 | 69,5 % |
| exp_01 | Up | 462·462·40 | 930 | 34 | 964 | 1.386 | 69,6 % |
| exp_02 | Up | 462·462·39 | 936 | 27 | 963 | 1.386 | 69,5 % |
| exp_03 | Up | 462·462·39 | 937 | 26 | 963 | 1.386 | 69,5 % |
| **total** | — | 1.848·1.848·157 | **3.743** | **110** | **3.853** | **5.544** | **69,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 897 | 27 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| exp_03 | exit | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.848·0 | **3.589** | **107** | **3.696** | **5.544** | **66,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·448·0 | 893 | 17 | 910 | 1.386 | 65,7 % |
| exp_01 | Up | 462·434·0 | 870 | 26 | 896 | 1.386 | 64,6 % |
| exp_02 | Up | 462·442·0 | 865 | 39 | 904 | 1.386 | 65,2 % |
| exp_03 | Up | 429·429·0 | 849 | 9 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.753·0 | **3.477** | **91** | **3.568** | **5.445** | **65,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·98 | 918 | 38 | 956 | 1.287 | 74,3 % |
| exp_01 | Up | 429·429·97 | 937 | 18 | 955 | 1.287 | 74,2 % |
| exp_02 | Up | 429·429·102 | 931 | 29 | 960 | 1.287 | 74,6 % |
| exp_03 | Up | 429·429·106 | 924 | 40 | 964 | 1.287 | 74,9 % |
| **total** | — | 1.716·1.716·403 | **3.710** | **125** | **3.835** | **5.148** | **74,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·157 | 3.743 | 110 | 3.853 | 5.544 | 69,5 % |
| m2 | RUNNING | 1.848·1.848·0 | 3.589 | 107 | 3.696 | 5.544 | 66,7 % |
| m3 | RUNNING | 1.815·1.753·0 | 3.477 | 91 | 3.568 | 5.445 | 65,5 % |
| m4 | RUNNING | 1.716·1.716·403 | 3.710 | 125 | 3.835 | 5.148 | 74,5 % |
| **TOTAL** | — | — | **14.519** | **433** | **14.952** | **21.681** | **69,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:14
- m2: erros → emulator/boot:104, install/adb:3
- m2: container exp_03 docker=exited (ok=894 fail=30)
- m3: erros → emulator/boot:87, install/adb:4
- m4: erros → emulator/boot:107, install/adb:18

## Ciclo 2026-07-09 07:02:55 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·40 | 941 | 23 | 964 | 1.386 | 69,6 % |
| exp_01 | Up | 462·462·40 | 930 | 34 | 964 | 1.386 | 69,6 % |
| exp_02 | Up | 462·462·40 | 937 | 27 | 964 | 1.386 | 69,6 % |
| exp_03 | Up | 462·462·40 | 938 | 26 | 964 | 1.386 | 69,6 % |
| **total** | — | 1.848·1.848·160 | **3.746** | **110** | **3.856** | **5.544** | **69,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 897 | 27 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 894 | 30 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.848·0 | **3.589** | **107** | **3.696** | **5.544** | **66,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·449·0 | 894 | 17 | 911 | 1.386 | 65,7 % |
| exp_01 | Up | 462·435·0 | 871 | 26 | 897 | 1.386 | 64,7 % |
| exp_02 | Up | 462·443·0 | 866 | 39 | 905 | 1.386 | 65,3 % |
| exp_03 | Up | 429·429·0 | 849 | 9 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.756·0 | **3.480** | **91** | **3.571** | **5.445** | **65,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·98 | 918 | 38 | 956 | 1.287 | 74,3 % |
| exp_01 | Up | 429·429·97 | 937 | 18 | 955 | 1.287 | 74,2 % |
| exp_02 | Up | 429·429·102 | 931 | 29 | 960 | 1.287 | 74,6 % |
| exp_03 | Up | 429·429·107 | 925 | 40 | 965 | 1.287 | 75,0 % |
| **total** | — | 1.716·1.716·404 | **3.711** | **125** | **3.836** | **5.148** | **74,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·160 | 3.746 | 110 | 3.856 | 5.544 | 69,6 % |
| m2 | RUNNING | 1.848·1.848·0 | 3.589 | 107 | 3.696 | 5.544 | 66,7 % |
| m3 | RUNNING | 1.815·1.756·0 | 3.480 | 91 | 3.571 | 5.445 | 65,6 % |
| m4 | RUNNING | 1.716·1.716·404 | 3.711 | 125 | 3.836 | 5.148 | 74,5 % |
| **TOTAL** | — | — | **14.526** | **433** | **14.959** | **21.681** | **69,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:14
- m2: erros → emulator/boot:104, install/adb:3
- m3: erros → emulator/boot:87, install/adb:4
- m4: erros → emulator/boot:107, install/adb:18

**Ações (07:02 local):** ciclo do cron 07:00 OK (4 RUNNING). Varredura ativa: **m2/exp_03 OOM (Exited 137, 2min) → `docker start` manual imediato** (recuperado); demais 15 exp + 4 humanoid Up. **m2 fechou a passada 180s** (1.848 completa, prestes a entrar na 300s). m1 subindo na 300s (160). m4 (Up 10h) na 300s (404, 74,5%). m3 progredindo firme na 180s (1.756, err baixo 91). Total **69,0%** (14.959/21.681; +140 vs 06:01). Deltas: m1 +47, m2 +11, m3 +38, m4 +44. Ordem: m4 74,5% > m1 69,6% > m2 66,7% > m3 65,6%. Cluster estável, sem banner-timeout neste ciclo.

## Ciclo 2026-07-09 08:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·50 | 951 | 23 | 974 | 1.386 | 70,3 % |
| exp_01 | Up | 462·462·50 | 940 | 34 | 974 | 1.386 | 70,3 % |
| exp_02 | Up | 462·462·51 | 947 | 28 | 975 | 1.386 | 70,3 % |
| exp_03 | Up | 462·462·49 | 947 | 26 | 973 | 1.386 | 70,2 % |
| **total** | — | 1.848·1.848·200 | **3.785** | **111** | **3.896** | **5.544** | **70,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·0 | 899 | 25 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 907 | 17 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 895 | 29 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 897 | 27 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.848·0 | **3.598** | **98** | **3.696** | **5.544** | **66,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 906 | 18 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·449·0 | 885 | 26 | 911 | 1.386 | 65,7 % |
| exp_02 | Up | 462·458·0 | 881 | 39 | 920 | 1.386 | 66,4 % |
| exp_03 | Up | 429·429·0 | 853 | 5 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.798·0 | **3.525** | **88** | **3.613** | **5.445** | **66,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·110 | 927 | 41 | 968 | 1.287 | 75,2 % |
| exp_01 | Up | 429·429·108 | 945 | 21 | 966 | 1.287 | 75,1 % |
| exp_02 | Up | 429·429·113 | 942 | 29 | 971 | 1.287 | 75,4 % |
| exp_03 | Up | 429·429·118 | 935 | 41 | 976 | 1.287 | 75,8 % |
| **total** | — | 1.716·1.716·449 | **3.749** | **132** | **3.881** | **5.148** | **75,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·200 | 3.785 | 111 | 3.896 | 5.544 | 70,3 % |
| m2 | RUNNING | 1.848·1.848·0 | 3.598 | 98 | 3.696 | 5.544 | 66,7 % |
| m3 | RUNNING | 1.815·1.798·0 | 3.525 | 88 | 3.613 | 5.445 | 66,4 % |
| m4 | RUNNING | 1.716·1.716·449 | 3.749 | 132 | 3.881 | 5.148 | 75,4 % |
| **TOTAL** | — | — | **14.657** | **429** | **15.086** | **21.681** | **69,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:15
- m2: erros → emulator/boot:95, install/adb:3
- m2: container exp_00 docker=exited (ok=899 fail=25)
- m3: erros → emulator/boot:82, install/adb:5, timeout:1
- m4: erros → emulator/boot:112, install/adb:20

## Ciclo 2026-07-09 08:06:44 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·51 | 952 | 23 | 975 | 1.386 | 70,3 % |
| exp_01 | Up | 462·462·51 | 941 | 34 | 975 | 1.386 | 70,3 % |
| exp_02 | Up | 462·462·52 | 948 | 28 | 976 | 1.386 | 70,4 % |
| exp_03 | Up | 462·462·50 | 948 | 26 | 974 | 1.386 | 70,3 % |
| **total** | — | 1.848·1.848·204 | **3.789** | **111** | **3.900** | **5.544** | **70,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 899 | 25 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 907 | 17 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 895 | 29 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 462·462·0 | 897 | 27 | 924 | 1.386 | 66,7 % |
| **total** | — | 1.848·1.848·0 | **3.598** | **98** | **3.696** | **5.544** | **66,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 906 | 18 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·450·0 | 886 | 26 | 912 | 1.386 | 65,8 % |
| exp_02 | Up | 462·459·0 | 882 | 39 | 921 | 1.386 | 66,5 % |
| exp_03 | Up | 429·429·0 | 853 | 5 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.800·0 | **3.527** | **88** | **3.615** | **5.445** | **66,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·111 | 928 | 41 | 969 | 1.287 | 75,3 % |
| exp_01 | Up | 429·429·110 | 947 | 21 | 968 | 1.287 | 75,2 % |
| exp_02 | Up | 429·429·114 | 943 | 29 | 972 | 1.287 | 75,5 % |
| exp_03 | Up | 429·429·119 | 936 | 41 | 977 | 1.287 | 75,9 % |
| **total** | — | 1.716·1.716·454 | **3.754** | **132** | **3.886** | **5.148** | **75,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·204 | 3.789 | 111 | 3.900 | 5.544 | 70,3 % |
| m2 | RUNNING | 1.848·1.848·0 | 3.598 | 98 | 3.696 | 5.544 | 66,7 % |
| m3 | RUNNING | 1.815·1.800·0 | 3.527 | 88 | 3.615 | 5.445 | 66,4 % |
| m4 | RUNNING | 1.716·1.716·454 | 3.754 | 132 | 3.886 | 5.148 | 75,5 % |
| **TOTAL** | — | — | **14.668** | **429** | **15.097** | **21.681** | **69,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:15
- m2: erros → emulator/boot:95, install/adb:3
- m3: erros → emulator/boot:82, install/adb:5, timeout:1
- m4: erros → emulator/boot:112, install/adb:20

**Ações (08:06 local):** ciclo do cron 08:00 OK (4 RUNNING). Varredura: **m2 com 2 containers OOM** (exp_00 + exp_01, Exited 137) → `docker start exp_00 exp_01` manual; m3 recompôs 2 (cron); m1/m4 limpas (Up 5h/11h). **m2 presa na transição 180→300** (feito estático 3.696 = 66,7% há ~1h): DIAGNOSTICADO — run vivo (pid 1696) em `docker wait exp_00 exp_01 exp_02 exp_03`, marcador `passada TIMEOUT=180s` às 04:31 sem marcador 300s; as tasks 180s estão completas (1.848) mas o docker wait só retorna quando os 4 saem exit 0, e exp_00/exp_01 OOMavam (137) antes de completar o skip-loop → barreira aberta. free 15g disponíveis (não é pressão agora). Reiniciei os 2; SEM ação destrutiva — aguardar os 4 alinharem exit 0. Total **69,6%** (15.097/21.681; +138 vs 07:02). Deltas: m1 +44, m2 +0, m3 +44, m4 +50. Ordem: m4 75,5% > m1 70,3% > m2 66,7% > m3 66,4%. ⚠️ m3 (180=1.800) baterá na MESMA barreira em breve — vigiar.

## Marco 2026-07-09 ~08:02-08:07 (local) — m2 barreira de transição 180→300 (docker wait + OOM)

**Mecanismo:** run_experiment.sh avança de passada via `docker wait exp_00 exp_01 exp_02 exp_03`, que só retorna quando os 4 containers saem com exit 0. No fim da passada 180s da m2, as 1.848 tasks já estavam COMPLETAS, mas 2 containers (exp_00/exp_01) morriam por OOM (exit 137) durante o skip-loop (re-iteração das tasks já feitas, com boot de emulador) em vez de sair limpo (exit 0). Resultado: a barreira nunca fechava → feito congelado em 3.696 (66,7%) por ~1h, slot 300s=0.
**Confirmação:** pid 1696 (run) vivo; filho `docker wait exp_00 exp_01 exp_02 exp_03`; run.log com `passada TIMEOUT=180s (04:31:24)` e SEM `passada TIMEOUT=300s`. free -g: 15 usados / 15 disponíveis.
**Ação:** `docker start exp_00 exp_01` (os OOM). O cron de restart (137-only) também absorve. NADA destrutivo — a passada 300s inicia sozinha quando os 4 saírem exit 0. Dados 60s+180s da m2 estão íntegros (3.696 salvos).
**Nota:** é o ponto vulnerável da oversubscrição de memória — a transição de passada exige os 4 emuladores bootados/saindo simultaneamente. NÃO confundir com deadlock de código (run está correto em docker wait). VIGIAR: se m2 seguir em 3.696 por 2h+, reportar com ênfase. m3/m1/m4 passam pela mesma barreira ao fim de cada passada.

## Ciclo 2026-07-09 09:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·59 | 960 | 23 | 983 | 1.386 | 70,9 % |
| exp_01 | Up | 462·462·59 | 949 | 34 | 983 | 1.386 | 70,9 % |
| exp_02 | Up | 462·462·63 | 959 | 28 | 987 | 1.386 | 71,2 % |
| exp_03 | Up | 462·462·59 | 957 | 26 | 983 | 1.386 | 70,9 % |
| **total** | — | 1.848·1.848·240 | **3.825** | **111** | **3.936** | **5.544** | **71,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·7 | 903 | 28 | 931 | 1.386 | 67,2 % |
| exp_01 | Up | 462·462·7 | 912 | 19 | 931 | 1.386 | 67,2 % |
| exp_02 | Up | 462·462·7 | 900 | 31 | 931 | 1.386 | 67,2 % |
| exp_03 | Up | 462·462·7 | 902 | 29 | 931 | 1.386 | 67,2 % |
| **total** | — | 1.848·1.848·28 | **3.617** | **107** | **3.724** | **5.544** | **67,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 908 | 16 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 898 | 26 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 886 | 38 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 429·429·0 | 855 | 3 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.815·0 | **3.547** | **83** | **3.630** | **5.445** | **66,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·120 | 937 | 41 | 978 | 1.287 | 76,0 % |
| exp_01 | Up | 429·429·118 | 955 | 21 | 976 | 1.287 | 75,8 % |
| exp_02 | Up | 429·429·124 | 952 | 30 | 982 | 1.287 | 76,3 % |
| exp_03 | Up | 429·429·129 | 945 | 42 | 987 | 1.287 | 76,7 % |
| **total** | — | 1.716·1.716·491 | **3.789** | **134** | **3.923** | **5.148** | **76,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·240 | 3.825 | 111 | 3.936 | 5.544 | 71,0 % |
| m2 | RUNNING | 1.848·1.848·28 | 3.617 | 107 | 3.724 | 5.544 | 67,2 % |
| m3 | RUNNING | 1.815·1.815·0 | 3.547 | 83 | 3.630 | 5.445 | 66,7 % |
| m4 | RUNNING | 1.716·1.716·491 | 3.789 | 134 | 3.923 | 5.148 | 76,2 % |
| **TOTAL** | — | — | **14.778** | **435** | **15.213** | **21.681** | **70,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:15
- m2: erros → emulator/boot:103, install/adb:4
- m3: erros → emulator/boot:78, install/adb:5
- m4: erros → emulator/boot:112, install/adb:22

## Ciclo 2026-07-09 09:02:50 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·60 | 961 | 23 | 984 | 1.386 | 71,0 % |
| exp_01 | Up | 462·462·60 | 950 | 34 | 984 | 1.386 | 71,0 % |
| exp_02 | Up | 462·462·63 | 959 | 28 | 987 | 1.386 | 71,2 % |
| exp_03 | Up | 462·462·59 | 957 | 26 | 983 | 1.386 | 70,9 % |
| **total** | — | 1.848·1.848·242 | **3.827** | **111** | **3.938** | **5.544** | **71,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·7 | 903 | 28 | 931 | 1.386 | 67,2 % |
| exp_01 | Up | 462·462·8 | 913 | 19 | 932 | 1.386 | 67,2 % |
| exp_02 | Up | 462·462·7 | 900 | 31 | 931 | 1.386 | 67,2 % |
| exp_03 | Up | 462·462·7 | 902 | 29 | 931 | 1.386 | 67,2 % |
| **total** | — | 1.848·1.848·29 | **3.618** | **107** | **3.725** | **5.544** | **67,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 908 | 16 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 898 | 26 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 886 | 38 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 429·429·0 | 855 | 3 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.815·0 | **3.547** | **83** | **3.630** | **5.445** | **66,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·120 | 937 | 41 | 978 | 1.287 | 76,0 % |
| exp_01 | Up | 429·429·119 | 956 | 21 | 977 | 1.287 | 75,9 % |
| exp_02 | Up | 429·429·124 | 952 | 30 | 982 | 1.287 | 76,3 % |
| exp_03 | Up | 429·429·129 | 945 | 42 | 987 | 1.287 | 76,7 % |
| **total** | — | 1.716·1.716·492 | **3.790** | **134** | **3.924** | **5.148** | **76,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·242 | 3.827 | 111 | 3.938 | 5.544 | 71,0 % |
| m2 | RUNNING | 1.848·1.848·29 | 3.618 | 107 | 3.725 | 5.544 | 67,2 % |
| m3 | RUNNING | 1.815·1.815·0 | 3.547 | 83 | 3.630 | 5.445 | 66,7 % |
| m4 | RUNNING | 1.716·1.716·492 | 3.790 | 134 | 3.924 | 5.148 | 76,2 % |
| **TOTAL** | — | — | **14.782** | **435** | **15.217** | **21.681** | **70,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:96, install/adb:15
- m2: erros → emulator/boot:103, install/adb:4
- m3: erros → emulator/boot:78, install/adb:5
- m4: erros → emulator/boot:112, install/adb:22

**Ações (09:02 local):** ciclo do cron 09:00 OK (4 RUNNING). Varredura: 16/16 exp + 4 humanoid Up, NENHUM container OOM parado (cron reiniciou os da m3). **m2 ROMPEU a barreira 180→300** — entrou na 300s (slot 300=29, feito 3.696→3.725), confirmando o diagnóstico do ciclo anterior (bastou manter os OOM reiniciados). **m3 agora na MESMA barreira** (1.815·1.815·0, 180s completa, 300s=0; exp_00/01/03 recém-reiniciados pelo cron, todos Up, err baixo 83) — vai romper como a m2. m1 (300=242) e m4 (300=492, 76,2%) subindo firme na 300s. Total **70,2%** (15.217/21.681; +120 vs 08:06). Deltas: m1 +38, m2 +29, m3 +15, m4 +38. Ordem: m4 76,2% > m1 71,0% > m2 67,2% > m3 66,7%. Cluster saudável, sem banner-timeout neste ciclo.

## Ciclo 2026-07-09 10:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·70 | 968 | 26 | 994 | 1.386 | 71,7 % |
| exp_01 | Up | 462·462·70 | 957 | 37 | 994 | 1.386 | 71,7 % |
| exp_02 | Up | 462·462·74 | 968 | 30 | 998 | 1.386 | 72,0 % |
| exp_03 | Up | 462·462·70 | 965 | 29 | 994 | 1.386 | 71,7 % |
| **total** | — | 1.848·1.848·284 | **3.858** | **122** | **3.980** | **5.544** | **71,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·17 | 912 | 29 | 941 | 1.386 | 67,9 % |
| exp_01 | Up | 462·462·17 | 922 | 19 | 941 | 1.386 | 67,9 % |
| exp_02 | Up | 462·462·18 | 911 | 31 | 942 | 1.386 | 68,0 % |
| exp_03 | Up | 462·462·16 | 911 | 29 | 940 | 1.386 | 67,8 % |
| **total** | — | 1.848·1.848·68 | **3.656** | **108** | **3.764** | **5.544** | **67,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 911 | 13 | 924 | 1.386 | 66,7 % |
| exp_01 | exit | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 886 | 38 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 429·429·0 | 856 | 2 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.815·0 | **3.557** | **73** | **3.630** | **5.445** | **66,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·129 | 946 | 41 | 987 | 1.287 | 76,7 % |
| exp_01 | Up | 429·429·128 | 965 | 21 | 986 | 1.287 | 76,6 % |
| exp_02 | Up | 429·429·135 | 960 | 33 | 993 | 1.287 | 77,2 % |
| exp_03 | Up | 429·429·140 | 954 | 44 | 998 | 1.287 | 77,5 % |
| **total** | — | 1.716·1.716·532 | **3.825** | **139** | **3.964** | **5.148** | **77,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·284 | 3.858 | 122 | 3.980 | 5.544 | 71,8 % |
| m2 | RUNNING | 1.848·1.848·68 | 3.656 | 108 | 3.764 | 5.544 | 67,9 % |
| m3 | RUNNING | 1.815·1.815·0 | 3.557 | 73 | 3.630 | 5.445 | 66,7 % |
| m4 | RUNNING | 1.716·1.716·532 | 3.825 | 139 | 3.964 | 5.148 | 77,0 % |
| **TOTAL** | — | — | **14.896** | **442** | **15.338** | **21.681** | **70,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:15
- m2: erros → emulator/boot:103, install/adb:5
- m3: erros → emulator/boot:70, install/adb:3
- m3: container exp_01 docker=exited (ok=904 fail=20)
- m4: erros → emulator/boot:117, install/adb:22

## Ciclo 2026-07-09 10:03:06 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·70 | 968 | 26 | 994 | 1.386 | 71,7 % |
| exp_01 | Up | 462·462·71 | 958 | 37 | 995 | 1.386 | 71,8 % |
| exp_02 | Up | 462·462·74 | 968 | 30 | 998 | 1.386 | 72,0 % |
| exp_03 | Up | 462·462·70 | 965 | 29 | 994 | 1.386 | 71,7 % |
| **total** | — | 1.848·1.848·285 | **3.859** | **122** | **3.981** | **5.544** | **71,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·17 | 912 | 29 | 941 | 1.386 | 67,9 % |
| exp_01 | Up | 462·462·17 | 922 | 19 | 941 | 1.386 | 67,9 % |
| exp_02 | Up | 462·462·19 | 912 | 31 | 943 | 1.386 | 68,0 % |
| exp_03 | Up | 462·462·17 | 912 | 29 | 941 | 1.386 | 67,9 % |
| **total** | — | 1.848·1.848·70 | **3.658** | **108** | **3.766** | **5.544** | **67,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·0 | 911 | 13 | 924 | 1.386 | 66,7 % |
| exp_01 | Up | 462·462·0 | 904 | 20 | 924 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·0 | 886 | 38 | 924 | 1.386 | 66,7 % |
| exp_03 | Up | 429·429·0 | 856 | 2 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.815·0 | **3.557** | **73** | **3.630** | **5.445** | **66,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·130 | 947 | 41 | 988 | 1.287 | 76,8 % |
| exp_01 | Up | 429·429·128 | 965 | 21 | 986 | 1.287 | 76,6 % |
| exp_02 | Up | 429·429·135 | 960 | 33 | 993 | 1.287 | 77,2 % |
| exp_03 | Up | 429·429·140 | 954 | 44 | 998 | 1.287 | 77,5 % |
| **total** | — | 1.716·1.716·533 | **3.826** | **139** | **3.965** | **5.148** | **77,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·285 | 3.859 | 122 | 3.981 | 5.544 | 71,8 % |
| m2 | RUNNING | 1.848·1.848·70 | 3.658 | 108 | 3.766 | 5.544 | 67,9 % |
| m3 | RUNNING | 1.815·1.815·0 | 3.557 | 73 | 3.630 | 5.445 | 66,7 % |
| m4 | RUNNING | 1.716·1.716·533 | 3.826 | 139 | 3.965 | 5.148 | 77,0 % |
| **TOTAL** | — | — | **14.900** | **442** | **15.342** | **21.681** | **70,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:15
- m2: erros → emulator/boot:103, install/adb:5
- m3: erros → emulator/boot:70, install/adb:3
- m4: erros → emulator/boot:117, install/adb:22

**Ações (10:03 local):** ciclo do cron 10:00 OK (4 RUNNING). Varredura: **m3 com 2 containers OOM** (exp_01 + exp_02, Exited 137) → `docker start exp_01 exp_02` manual (é o churn da barreira 180→300). m1/m2/m4 limpas (Up 7h/2h/13h). **m3 ainda na barreira** (1.815·1.815·0, feito 3.630 estático há ~1h — mesmo tempo que a m2 levou para romper; err baixo 73). Reiniciei os OOM, SEM ação destrutiva — deve romper no próximo ciclo. m2 avança bem na 300s (70). m1(300=285) e m4(300=533, 77,0%) firmes. Total **70,8%** (15.342/21.681; +125 vs 09:02). Deltas: m1 +43, m2 +41, m3 +0, m4 +41. Ordem: m4 77,0% > m1 71,8% > m2 67,9% > m3 66,7%. ⚠️ Se m3 seguir em 3.630 no ciclo 11:00 (2h de barreira), reportar com ênfase.

## Ciclo 2026-07-09 10:16:37 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·73 | 971 | 26 | 997 | 1.386 | 71,9 % |
| exp_01 | Up | 462·462·73 | 960 | 37 | 997 | 1.386 | 71,9 % |
| exp_02 | Up | 462·462·77 | 970 | 31 | 1.001 | 1.386 | 72,2 % |
| exp_03 | Up | 462·462·72 | 967 | 29 | 996 | 1.386 | 71,9 % |
| **total** | — | 1.848·1.848·295 | **3.868** | **123** | **3.991** | **5.544** | **72,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·20 | 915 | 29 | 944 | 1.386 | 68,1 % |
| exp_01 | Up | 462·462·19 | 924 | 19 | 943 | 1.386 | 68,0 % |
| exp_02 | Up | 462·462·21 | 914 | 31 | 945 | 1.386 | 68,2 % |
| exp_03 | Up | 462·462·19 | 914 | 29 | 943 | 1.386 | 68,0 % |
| **total** | — | 1.848·1.848·79 | **3.667** | **108** | **3.775** | **5.544** | **68,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·2 | 912 | 14 | 926 | 1.386 | 66,8 % |
| exp_01 | Up | 462·462·1 | 905 | 20 | 925 | 1.386 | 66,7 % |
| exp_02 | Up | 462·462·1 | 886 | 39 | 925 | 1.386 | 66,7 % |
| exp_03 | Up | 429·429·0 | 856 | 2 | 858 | 1.287 | 66,7 % |
| **total** | — | 1.815·1.815·4 | **3.559** | **75** | **3.634** | **5.445** | **66,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·133 | 949 | 42 | 991 | 1.287 | 77,0 % |
| exp_01 | Up | 429·429·131 | 968 | 21 | 989 | 1.287 | 76,8 % |
| exp_02 | Up | 429·429·138 | 963 | 33 | 996 | 1.287 | 77,4 % |
| exp_03 | Up | 429·429·142 | 956 | 44 | 1.000 | 1.287 | 77,7 % |
| **total** | — | 1.716·1.716·544 | **3.836** | **140** | **3.976** | **5.148** | **77,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·295 | 3.868 | 123 | 3.991 | 5.544 | 72,0 % |
| m2 | RUNNING | 1.848·1.848·79 | 3.667 | 108 | 3.775 | 5.544 | 68,1 % |
| m3 | RUNNING | 1.815·1.815·4 | 3.559 | 75 | 3.634 | 5.445 | 66,7 % |
| m4 | RUNNING | 1.716·1.716·544 | 3.836 | 140 | 3.976 | 5.148 | 77,2 % |
| **TOTAL** | — | — | **14.930** | **446** | **15.376** | **21.681** | **70,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:16
- m2: erros → emulator/boot:103, install/adb:5
- m3: erros → emulator/boot:73, install/adb:2
- m4: erros → emulator/boot:118, install/adb:22

**Ações (10:16 local):** Retomada do loop pós-reboot da máquina LOCAL do usuário. Cron local do health_check sobreviveu (rodou ininterrupto até 10:00). Varredura SSH ativa nas 4 VMs: todas RUNNING, 5/5 containers Up (m1 7h, m2 2h, m3 5min, m4 13h), run_procs=2 em todas (real+wrapper, normal). **m3 rompeu a barreira 180→300** (slot 300 0→4; containers "Up 5min" = re-iteração concluída, entrou na passada final) — resolveu sozinha como a m2, sem ação destrutiva. cron OOM ativo nas 4 (últimos restarts: m1 exp_00, m2 exp_02, m3 exp_03, m4 exp_02). Nenhuma ação corretiva necessária. Total 15.376/21.681 = 70,9% (+34 vs 10:03). Ordem: m4 77,2% > m1 72,0% > m2 68,1% > m3 66,7%. Reboots acumulados: 12.

## Ciclo 2026-07-09 11:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·80 | 978 | 26 | 1.004 | 1.386 | 72,4 % |
| exp_01 | Up | 462·462·80 | 967 | 37 | 1.004 | 1.386 | 72,4 % |
| exp_02 | Up | 462·462·84 | 977 | 31 | 1.008 | 1.386 | 72,7 % |
| exp_03 | Up | 462·462·82 | 977 | 29 | 1.006 | 1.386 | 72,6 % |
| **total** | — | 1.848·1.848·326 | **3.899** | **123** | **4.022** | **5.544** | **72,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·27 | 922 | 29 | 951 | 1.386 | 68,6 % |
| exp_01 | Up | 462·462·26 | 931 | 19 | 950 | 1.386 | 68,5 % |
| exp_02 | Up | 462·462·29 | 921 | 32 | 953 | 1.386 | 68,8 % |
| exp_03 | Up | 462·462·26 | 921 | 29 | 950 | 1.386 | 68,5 % |
| **total** | — | 1.848·1.848·108 | **3.695** | **109** | **3.804** | **5.544** | **68,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·10 | 918 | 16 | 934 | 1.386 | 67,4 % |
| exp_01 | Up | 462·462·10 | 911 | 23 | 934 | 1.386 | 67,4 % |
| exp_02 | Up | 462·462·9 | 892 | 41 | 933 | 1.386 | 67,3 % |
| exp_03 | Up | 429·429·9 | 862 | 5 | 867 | 1.287 | 67,4 % |
| **total** | — | 1.815·1.815·38 | **3.583** | **85** | **3.668** | **5.445** | **67,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·141 | 955 | 44 | 999 | 1.287 | 77,6 % |
| exp_01 | Up | 429·429·140 | 974 | 24 | 998 | 1.287 | 77,5 % |
| exp_02 | Up | 429·429·145 | 970 | 33 | 1.003 | 1.287 | 77,9 % |
| exp_03 | Up | 429·429·150 | 963 | 45 | 1.008 | 1.287 | 78,3 % |
| **total** | — | 1.716·1.716·576 | **3.862** | **146** | **4.008** | **5.148** | **77,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·326 | 3.899 | 123 | 4.022 | 5.544 | 72,5 % |
| m2 | RUNNING | 1.848·1.848·108 | 3.695 | 109 | 3.804 | 5.544 | 68,6 % |
| m3 | RUNNING | 1.815·1.815·38 | 3.583 | 85 | 3.668 | 5.445 | 67,4 % |
| m4 | RUNNING | 1.716·1.716·576 | 3.862 | 146 | 4.008 | 5.148 | 77,9 % |
| **TOTAL** | — | — | **15.039** | **463** | **15.502** | **21.681** | **71,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:16
- m2: erros → emulator/boot:103, install/adb:6
- m3: erros → emulator/boot:80, install/adb:5
- m4: erros → emulator/boot:121, install/adb:25

## Ciclo 2026-07-09 11:02:52 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·80 | 978 | 26 | 1.004 | 1.386 | 72,4 % |
| exp_01 | Up | 462·462·81 | 968 | 37 | 1.005 | 1.386 | 72,5 % |
| exp_02 | Up | 462·462·84 | 977 | 31 | 1.008 | 1.386 | 72,7 % |
| exp_03 | Up | 462·462·82 | 977 | 29 | 1.006 | 1.386 | 72,6 % |
| **total** | — | 1.848·1.848·327 | **3.900** | **123** | **4.023** | **5.544** | **72,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·27 | 922 | 29 | 951 | 1.386 | 68,6 % |
| exp_01 | Up | 462·462·27 | 932 | 19 | 951 | 1.386 | 68,6 % |
| exp_02 | Up | 462·462·29 | 921 | 32 | 953 | 1.386 | 68,8 % |
| exp_03 | Up | 462·462·27 | 922 | 29 | 951 | 1.386 | 68,6 % |
| **total** | — | 1.848·1.848·110 | **3.697** | **109** | **3.806** | **5.544** | **68,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·10 | 918 | 16 | 934 | 1.386 | 67,4 % |
| exp_01 | Up | 462·462·10 | 911 | 23 | 934 | 1.386 | 67,4 % |
| exp_02 | Up | 462·462·10 | 893 | 41 | 934 | 1.386 | 67,4 % |
| exp_03 | Up | 429·429·9 | 862 | 5 | 867 | 1.287 | 67,4 % |
| **total** | — | 1.815·1.815·39 | **3.584** | **85** | **3.669** | **5.445** | **67,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·141 | 955 | 44 | 999 | 1.287 | 77,6 % |
| exp_01 | Up | 429·429·141 | 975 | 24 | 999 | 1.287 | 77,6 % |
| exp_02 | Up | 429·429·145 | 970 | 33 | 1.003 | 1.287 | 77,9 % |
| exp_03 | Up | 429·429·151 | 964 | 45 | 1.009 | 1.287 | 78,4 % |
| **total** | — | 1.716·1.716·578 | **3.864** | **146** | **4.010** | **5.148** | **77,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·327 | 3.900 | 123 | 4.023 | 5.544 | 72,6 % |
| m2 | RUNNING | 1.848·1.848·110 | 3.697 | 109 | 3.806 | 5.544 | 68,7 % |
| m3 | RUNNING | 1.815·1.815·39 | 3.584 | 85 | 3.669 | 5.445 | 67,4 % |
| m4 | RUNNING | 1.716·1.716·578 | 3.864 | 146 | 4.010 | 5.148 | 77,9 % |
| **TOTAL** | — | — | **15.045** | **463** | **15.508** | **21.681** | **71,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:16
- m2: erros → emulator/boot:103, install/adb:6
- m3: erros → emulator/boot:80, install/adb:5
- m4: erros → emulator/boot:121, install/adb:25

**Ações (11:02 local):** Ciclo de rotina, sem incidentes. Cron local ativo (11:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up (m1 8h, m2 3h, m3 51min, m4 14h), run_procs=2 em todas. m3 estável há 51min na passada final (sem OOM churn recente), recuperou-se bem pós-barreira (300: 4→39). Nenhuma ação corretiva. Total 15.508/21.681 = 71,5% (+132 vs 10:16). Todas na passada 300s subindo. Ordem: m4 77,9% > m1 72,6% > m2 68,7% > m3 67,4%. Reboots acumulados: 12.

## Ciclo 2026-07-09 12:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·89 | 987 | 26 | 1.013 | 1.386 | 73,1 % |
| exp_01 | Up | 462·462·90 | 977 | 37 | 1.014 | 1.386 | 73,2 % |
| exp_02 | Up | 462·462·95 | 988 | 31 | 1.019 | 1.386 | 73,5 % |
| exp_03 | Up | 462·462·91 | 986 | 29 | 1.015 | 1.386 | 73,2 % |
| **total** | — | 1.848·1.848·365 | **3.938** | **123** | **4.061** | **5.544** | **73,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·37 | 931 | 30 | 961 | 1.386 | 69,3 % |
| exp_01 | Up | 462·462·38 | 939 | 23 | 962 | 1.386 | 69,4 % |
| exp_02 | Up | 462·462·40 | 930 | 34 | 964 | 1.386 | 69,6 % |
| exp_03 | Up | 462·462·37 | 929 | 32 | 961 | 1.386 | 69,3 % |
| **total** | — | 1.848·1.848·152 | **3.729** | **119** | **3.848** | **5.544** | **69,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·20 | 928 | 16 | 944 | 1.386 | 68,1 % |
| exp_01 | Up | 462·462·20 | 920 | 24 | 944 | 1.386 | 68,1 % |
| exp_02 | Up | 462·462·19 | 902 | 41 | 943 | 1.386 | 68,0 % |
| exp_03 | Up | 429·429·18 | 871 | 5 | 876 | 1.287 | 68,1 % |
| **total** | — | 1.815·1.815·77 | **3.621** | **86** | **3.707** | **5.445** | **68,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·150 | 964 | 44 | 1.008 | 1.287 | 78,3 % |
| exp_01 | Up | 429·429·151 | 984 | 25 | 1.009 | 1.287 | 78,4 % |
| exp_02 | Up | 429·429·155 | 979 | 34 | 1.013 | 1.287 | 78,7 % |
| exp_03 | Up | 429·429·160 | 973 | 45 | 1.018 | 1.287 | 79,1 % |
| **total** | — | 1.716·1.716·616 | **3.900** | **148** | **4.048** | **5.148** | **78,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·365 | 3.938 | 123 | 4.061 | 5.544 | 73,3 % |
| m2 | RUNNING | 1.848·1.848·152 | 3.729 | 119 | 3.848 | 5.544 | 69,4 % |
| m3 | RUNNING | 1.815·1.815·77 | 3.621 | 86 | 3.707 | 5.445 | 68,1 % |
| m4 | RUNNING | 1.716·1.716·616 | 3.900 | 148 | 4.048 | 5.148 | 78,6 % |
| **TOTAL** | — | — | **15.188** | **476** | **15.664** | **21.681** | **72,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:16
- m2: erros → emulator/boot:112, install/adb:7
- m3: erros → emulator/boot:80, install/adb:6
- m4: erros → emulator/boot:121, install/adb:27

## Ciclo 2026-07-09 12:02:38 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·89 | 987 | 26 | 1.013 | 1.386 | 73,1 % |
| exp_01 | Up | 462·462·90 | 977 | 37 | 1.014 | 1.386 | 73,2 % |
| exp_02 | Up | 462·462·96 | 989 | 31 | 1.020 | 1.386 | 73,6 % |
| exp_03 | Up | 462·462·92 | 987 | 29 | 1.016 | 1.386 | 73,3 % |
| **total** | — | 1.848·1.848·367 | **3.940** | **123** | **4.063** | **5.544** | **73,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·37 | 931 | 30 | 961 | 1.386 | 69,3 % |
| exp_01 | Up | 462·462·39 | 940 | 23 | 963 | 1.386 | 69,5 % |
| exp_02 | Up | 462·462·40 | 930 | 34 | 964 | 1.386 | 69,6 % |
| exp_03 | Up | 462·462·37 | 929 | 32 | 961 | 1.386 | 69,3 % |
| **total** | — | 1.848·1.848·153 | **3.730** | **119** | **3.849** | **5.544** | **69,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·20 | 928 | 16 | 944 | 1.386 | 68,1 % |
| exp_01 | Up | 462·462·21 | 921 | 24 | 945 | 1.386 | 68,2 % |
| exp_02 | Up | 462·462·19 | 902 | 41 | 943 | 1.386 | 68,0 % |
| exp_03 | Up | 429·429·19 | 872 | 5 | 877 | 1.287 | 68,1 % |
| **total** | — | 1.815·1.815·79 | **3.623** | **86** | **3.709** | **5.445** | **68,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·151 | 965 | 44 | 1.009 | 1.287 | 78,4 % |
| exp_01 | Up | 429·429·151 | 984 | 25 | 1.009 | 1.287 | 78,4 % |
| exp_02 | Up | 429·429·156 | 980 | 34 | 1.014 | 1.287 | 78,8 % |
| exp_03 | Up | 429·429·160 | 973 | 45 | 1.018 | 1.287 | 79,1 % |
| **total** | — | 1.716·1.716·618 | **3.902** | **148** | **4.050** | **5.148** | **78,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·367 | 3.940 | 123 | 4.063 | 5.544 | 73,3 % |
| m2 | RUNNING | 1.848·1.848·153 | 3.730 | 119 | 3.849 | 5.544 | 69,4 % |
| m3 | RUNNING | 1.815·1.815·79 | 3.623 | 86 | 3.709 | 5.445 | 68,1 % |
| m4 | RUNNING | 1.716·1.716·618 | 3.902 | 148 | 4.050 | 5.148 | 78,7 % |
| **TOTAL** | — | — | **15.195** | **476** | **15.671** | **21.681** | **72,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:107, install/adb:16
- m2: erros → emulator/boot:112, install/adb:7
- m3: erros → emulator/boot:80, install/adb:6
- m4: erros → emulator/boot:121, install/adb:27

**Ações (12:02 local):** Ciclo de rotina, sem incidentes. Cron local ativo (12:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up (m1 9h, m2 4h, m3 2h, m4 15h), run_procs=2 em todas. Sem OOM churn recente. Nenhuma ação corretiva. Total 15.671/21.681 = 72,3% (+163 vs 11:02). Todas na passada 300s subindo consistente. Ordem: m4 78,7% > m1 73,3% > m2 69,4% > m3 68,1%. Reboots acumulados: 12.

## Ciclo 2026-07-09 13:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·98 | 996 | 26 | 1.022 | 1.386 | 73,7 % |
| exp_01 | Up | 462·462·98 | 985 | 37 | 1.022 | 1.386 | 73,7 % |
| exp_02 | Up | 462·462·106 | 996 | 34 | 1.030 | 1.386 | 74,3 % |
| exp_03 | Up | 462·462·103 | 994 | 33 | 1.027 | 1.386 | 74,1 % |
| **total** | — | 1.848·1.848·405 | **3.971** | **130** | **4.101** | **5.544** | **74,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·47 | 941 | 30 | 971 | 1.386 | 70,1 % |
| exp_01 | Up | 462·462·52 | 951 | 25 | 976 | 1.386 | 70,4 % |
| exp_02 | Up | 462·462·49 | 939 | 34 | 973 | 1.386 | 70,2 % |
| exp_03 | Up | 462·462·46 | 938 | 32 | 970 | 1.386 | 70,0 % |
| **total** | — | 1.848·1.848·194 | **3.769** | **121** | **3.890** | **5.544** | **70,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·30 | 937 | 17 | 954 | 1.386 | 68,8 % |
| exp_01 | Up | 462·462·30 | 930 | 24 | 954 | 1.386 | 68,8 % |
| exp_02 | Up | 462·462·31 | 914 | 41 | 955 | 1.386 | 68,9 % |
| exp_03 | Up | 429·429·30 | 880 | 8 | 888 | 1.287 | 69,0 % |
| **total** | — | 1.815·1.815·121 | **3.661** | **90** | **3.751** | **5.445** | **68,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·160 | 974 | 44 | 1.018 | 1.287 | 79,1 % |
| exp_01 | Up | 429·429·160 | 993 | 25 | 1.018 | 1.287 | 79,1 % |
| exp_02 | Up | 429·429·165 | 989 | 34 | 1.023 | 1.287 | 79,5 % |
| exp_03 | Up | 429·429·171 | 981 | 48 | 1.029 | 1.287 | 80,0 % |
| **total** | — | 1.716·1.716·656 | **3.937** | **151** | **4.088** | **5.148** | **79,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·405 | 3.971 | 130 | 4.101 | 5.544 | 74,0 % |
| m2 | RUNNING | 1.848·1.848·194 | 3.769 | 121 | 3.890 | 5.544 | 70,2 % |
| m3 | RUNNING | 1.815·1.815·121 | 3.661 | 90 | 3.751 | 5.445 | 68,9 % |
| m4 | RUNNING | 1.716·1.716·656 | 3.937 | 151 | 4.088 | 5.148 | 79,4 % |
| **TOTAL** | — | — | **15.338** | **492** | **15.830** | **21.681** | **73,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:113, install/adb:17
- m2: erros → emulator/boot:112, install/adb:9
- m3: erros → emulator/boot:80, install/adb:10
- m4: erros → emulator/boot:124, install/adb:27

## Ciclo 2026-07-09 13:02:56 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·98 | 996 | 26 | 1.022 | 1.386 | 73,7 % |
| exp_01 | Up | 462·462·98 | 985 | 37 | 1.022 | 1.386 | 73,7 % |
| exp_02 | Up | 462·462·106 | 996 | 34 | 1.030 | 1.386 | 74,3 % |
| exp_03 | Up | 462·462·103 | 994 | 33 | 1.027 | 1.386 | 74,1 % |
| **total** | — | 1.848·1.848·405 | **3.971** | **130** | **4.101** | **5.544** | **74,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·47 | 941 | 30 | 971 | 1.386 | 70,1 % |
| exp_01 | Up | 462·462·53 | 952 | 25 | 977 | 1.386 | 70,5 % |
| exp_02 | Up | 462·462·50 | 940 | 34 | 974 | 1.386 | 70,3 % |
| exp_03 | Up | 462·462·47 | 939 | 32 | 971 | 1.386 | 70,1 % |
| **total** | — | 1.848·1.848·197 | **3.772** | **121** | **3.893** | **5.544** | **70,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·30 | 937 | 17 | 954 | 1.386 | 68,8 % |
| exp_01 | Up | 462·462·31 | 931 | 24 | 955 | 1.386 | 68,9 % |
| exp_02 | Up | 462·462·31 | 914 | 41 | 955 | 1.386 | 68,9 % |
| exp_03 | Up | 429·429·31 | 881 | 8 | 889 | 1.287 | 69,1 % |
| **total** | — | 1.815·1.815·123 | **3.663** | **90** | **3.753** | **5.445** | **68,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·160 | 974 | 44 | 1.018 | 1.287 | 79,1 % |
| exp_01 | Up | 429·429·161 | 994 | 25 | 1.019 | 1.287 | 79,2 % |
| exp_02 | Up | 429·429·166 | 989 | 35 | 1.024 | 1.287 | 79,6 % |
| exp_03 | Up | 429·429·172 | 982 | 48 | 1.030 | 1.287 | 80,0 % |
| **total** | — | 1.716·1.716·659 | **3.939** | **152** | **4.091** | **5.148** | **79,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·405 | 3.971 | 130 | 4.101 | 5.544 | 74,0 % |
| m2 | RUNNING | 1.848·1.848·197 | 3.772 | 121 | 3.893 | 5.544 | 70,2 % |
| m3 | RUNNING | 1.815·1.815·123 | 3.663 | 90 | 3.753 | 5.445 | 68,9 % |
| m4 | RUNNING | 1.716·1.716·659 | 3.939 | 152 | 4.091 | 5.148 | 79,5 % |
| **TOTAL** | — | — | **15.345** | **493** | **15.838** | **21.681** | **73,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:113, install/adb:17
- m2: erros → emulator/boot:112, install/adb:9
- m3: erros → emulator/boot:80, install/adb:10
- m4: erros → emulator/boot:125, install/adb:27

**Ações (13:02 local):** Ciclo de rotina, sem incidentes pendentes. Cron local ativo (13:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up (m1 10h/exp_01 2min, m2 5h, m3 3h, m4 16h), run_procs=2 em todas. m1 exp_01 auto-reiniciado pelo cron OOM (137) há 2min — já Up, nenhuma ação manual necessária. Total 15.838/21.681 = 73,1% (+167 vs 12:02). Todas na passada 300s subindo consistente; m4 exp_03 cruzou 80%. Ordem: m4 79,5% > m1 74,0% > m2 70,2% > m3 68,9%. Reboots acumulados: 12.

## Ciclo 2026-07-09 14:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·109 | 1.005 | 28 | 1.033 | 1.386 | 74,5 % |
| exp_01 | Up | 462·462·103 | 989 | 38 | 1.027 | 1.386 | 74,1 % |
| exp_02 | Up | 462·462·116 | 1.006 | 34 | 1.040 | 1.386 | 75,0 % |
| exp_03 | Up | 462·462·112 | 1.003 | 33 | 1.036 | 1.386 | 74,7 % |
| **total** | — | 1.848·1.848·440 | **4.003** | **133** | **4.136** | **5.544** | **74,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·56 | 950 | 30 | 980 | 1.386 | 70,7 % |
| exp_01 | Up | 462·462·62 | 961 | 25 | 986 | 1.386 | 71,1 % |
| exp_02 | Up | 462·462·60 | 949 | 35 | 984 | 1.386 | 71,0 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·235 | **3.808** | **123** | **3.931** | **5.544** | **70,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·41 | 946 | 19 | 965 | 1.386 | 69,6 % |
| exp_01 | Up | 462·462·41 | 938 | 27 | 965 | 1.386 | 69,6 % |
| exp_02 | Up | 462·462·43 | 922 | 45 | 967 | 1.386 | 69,8 % |
| exp_03 | Up | 429·429·41 | 888 | 11 | 899 | 1.287 | 69,9 % |
| **total** | — | 1.815·1.815·166 | **3.694** | **102** | **3.796** | **5.445** | **69,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·172 | 982 | 48 | 1.030 | 1.287 | 80,0 % |
| exp_01 | Up | 429·429·171 | 1.001 | 28 | 1.029 | 1.287 | 80,0 % |
| exp_02 | Up | 429·429·176 | 997 | 37 | 1.034 | 1.287 | 80,3 % |
| exp_03 | Up | 429·429·181 | 991 | 48 | 1.039 | 1.287 | 80,7 % |
| **total** | — | 1.716·1.716·700 | **3.971** | **161** | **4.132** | **5.148** | **80,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·440 | 4.003 | 133 | 4.136 | 5.544 | 74,6 % |
| m2 | RUNNING | 1.848·1.848·235 | 3.808 | 123 | 3.931 | 5.544 | 70,9 % |
| m3 | RUNNING | 1.815·1.815·166 | 3.694 | 102 | 3.796 | 5.445 | 69,7 % |
| m4 | RUNNING | 1.716·1.716·700 | 3.971 | 161 | 4.132 | 5.148 | 80,3 % |
| **TOTAL** | — | — | **15.476** | **519** | **15.995** | **21.681** | **73,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:15
- m2: erros → emulator/boot:112, install/adb:11
- m3: erros → emulator/boot:91, install/adb:11
- m4: erros → emulator/boot:132, install/adb:29

## Ciclo 2026-07-09 14:02:45 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·109 | 1.005 | 28 | 1.033 | 1.386 | 74,5 % |
| exp_01 | Up | 462·462·103 | 989 | 38 | 1.027 | 1.386 | 74,1 % |
| exp_02 | Up | 462·462·116 | 1.006 | 34 | 1.040 | 1.386 | 75,0 % |
| exp_03 | Up | 462·462·113 | 1.004 | 33 | 1.037 | 1.386 | 74,8 % |
| **total** | — | 1.848·1.848·441 | **4.004** | **133** | **4.137** | **5.544** | **74,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·57 | 951 | 30 | 981 | 1.386 | 70,8 % |
| exp_01 | Up | 462·462·62 | 961 | 25 | 986 | 1.386 | 71,1 % |
| exp_02 | Up | 462·462·60 | 949 | 35 | 984 | 1.386 | 71,0 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·236 | **3.809** | **123** | **3.932** | **5.544** | **70,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·41 | 946 | 19 | 965 | 1.386 | 69,6 % |
| exp_01 | Up | 462·462·41 | 938 | 27 | 965 | 1.386 | 69,6 % |
| exp_02 | Up | 462·462·43 | 922 | 45 | 967 | 1.386 | 69,8 % |
| exp_03 | Up | 429·429·42 | 889 | 11 | 900 | 1.287 | 69,9 % |
| **total** | — | 1.815·1.815·167 | **3.695** | **102** | **3.797** | **5.445** | **69,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·173 | 983 | 48 | 1.031 | 1.287 | 80,1 % |
| exp_01 | Up | 429·429·171 | 1.001 | 28 | 1.029 | 1.287 | 80,0 % |
| exp_02 | Up | 429·429·176 | 997 | 37 | 1.034 | 1.287 | 80,3 % |
| exp_03 | Up | 429·429·181 | 991 | 48 | 1.039 | 1.287 | 80,7 % |
| **total** | — | 1.716·1.716·701 | **3.972** | **161** | **4.133** | **5.148** | **80,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·441 | 4.004 | 133 | 4.137 | 5.544 | 74,6 % |
| m2 | RUNNING | 1.848·1.848·236 | 3.809 | 123 | 3.932 | 5.544 | 70,9 % |
| m3 | RUNNING | 1.815·1.815·167 | 3.695 | 102 | 3.797 | 5.445 | 69,7 % |
| m4 | RUNNING | 1.716·1.716·701 | 3.972 | 161 | 4.133 | 5.148 | 80,3 % |
| **TOTAL** | — | — | **15.480** | **519** | **15.999** | **21.681** | **73,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:15
- m2: erros → emulator/boot:112, install/adb:11
- m3: erros → emulator/boot:91, install/adb:11
- m4: erros → emulator/boot:132, install/adb:29

**Ações (14:02 local):** Ciclo de rotina, sem incidentes. Cron local ativo (14:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up (m1 11h/exp_01 ~1h, m2 6h, m3 4h, m4 17h), run_procs=2 em todas. Sem OOM churn recente. Nenhuma ação corretiva. Total 15.999/21.681 = 73,8% (+161 vs 13:02). Todas na passada 300s subindo consistente; m4 inteira cruzou 80%. Ordem: m4 80,3% > m1 74,6% > m2 70,9% > m3 69,7%. Reboots acumulados: 12.

## Ciclo 2026-07-09 15:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·118 | 1.014 | 28 | 1.042 | 1.386 | 75,2 % |
| exp_01 | Up | 462·462·112 | 998 | 38 | 1.036 | 1.386 | 74,7 % |
| exp_02 | Up | 462·462·125 | 1.015 | 34 | 1.049 | 1.386 | 75,7 % |
| exp_03 | Up | 462·462·122 | 1.013 | 33 | 1.046 | 1.386 | 75,5 % |
| **total** | — | 1.848·1.848·477 | **4.040** | **133** | **4.173** | **5.544** | **75,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·69 | 959 | 34 | 993 | 1.386 | 71,6 % |
| exp_01 | Up | 462·462·74 | 968 | 30 | 998 | 1.386 | 72,0 % |
| exp_02 | Up | 462·462·70 | 956 | 38 | 994 | 1.386 | 71,7 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·270 | **3.831** | **135** | **3.966** | **5.544** | **71,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·50 | 955 | 19 | 974 | 1.386 | 70,3 % |
| exp_01 | Up | 462·462·53 | 948 | 29 | 977 | 1.386 | 70,5 % |
| exp_02 | Up | 462·462·53 | 932 | 45 | 977 | 1.386 | 70,5 % |
| exp_03 | Up | 429·429·51 | 898 | 11 | 909 | 1.287 | 70,6 % |
| **total** | — | 1.815·1.815·207 | **3.733** | **104** | **3.837** | **5.445** | **70,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·182 | 992 | 48 | 1.040 | 1.287 | 80,8 % |
| exp_01 | Up | 429·429·181 | 1.011 | 28 | 1.039 | 1.287 | 80,7 % |
| exp_02 | Up | 429·429·185 | 1.006 | 37 | 1.043 | 1.287 | 81,0 % |
| exp_03 | Up | 429·429·191 | 1.001 | 48 | 1.049 | 1.287 | 81,5 % |
| **total** | — | 1.716·1.716·739 | **4.010** | **161** | **4.171** | **5.148** | **81,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·477 | 4.040 | 133 | 4.173 | 5.544 | 75,3 % |
| m2 | RUNNING | 1.848·1.848·270 | 3.831 | 135 | 3.966 | 5.544 | 71,5 % |
| m3 | RUNNING | 1.815·1.815·207 | 3.733 | 104 | 3.837 | 5.445 | 70,5 % |
| m4 | RUNNING | 1.716·1.716·739 | 4.010 | 161 | 4.171 | 5.148 | 81,0 % |
| **TOTAL** | — | — | **15.614** | **533** | **16.147** | **21.681** | **74,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:15
- m2: erros → emulator/boot:121, install/adb:14
- m3: erros → emulator/boot:91, install/adb:13
- m4: erros → emulator/boot:132, install/adb:29

## Ciclo 2026-07-09 15:02:48 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·119 | 1.015 | 28 | 1.043 | 1.386 | 75,3 % |
| exp_01 | Up | 462·462·112 | 998 | 38 | 1.036 | 1.386 | 74,7 % |
| exp_02 | Up | 462·462·126 | 1.016 | 34 | 1.050 | 1.386 | 75,8 % |
| exp_03 | Up | 462·462·122 | 1.013 | 33 | 1.046 | 1.386 | 75,5 % |
| **total** | — | 1.848·1.848·479 | **4.042** | **133** | **4.175** | **5.544** | **75,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·69 | 959 | 34 | 993 | 1.386 | 71,6 % |
| exp_01 | Up | 462·462·75 | 969 | 30 | 999 | 1.386 | 72,1 % |
| exp_02 | Up | 462·462·71 | 957 | 38 | 995 | 1.386 | 71,8 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·272 | **3.833** | **135** | **3.968** | **5.544** | **71,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·51 | 956 | 19 | 975 | 1.386 | 70,3 % |
| exp_01 | Up | 462·462·54 | 949 | 29 | 978 | 1.386 | 70,6 % |
| exp_02 | Up | 462·462·53 | 932 | 45 | 977 | 1.386 | 70,5 % |
| exp_03 | Up | 429·429·51 | 898 | 11 | 909 | 1.287 | 70,6 % |
| **total** | — | 1.815·1.815·209 | **3.735** | **104** | **3.839** | **5.445** | **70,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·182 | 992 | 48 | 1.040 | 1.287 | 80,8 % |
| exp_01 | Up | 429·429·181 | 1.011 | 28 | 1.039 | 1.287 | 80,7 % |
| exp_02 | Up | 429·429·186 | 1.007 | 37 | 1.044 | 1.287 | 81,1 % |
| exp_03 | Up | 429·429·192 | 1.002 | 48 | 1.050 | 1.287 | 81,6 % |
| **total** | — | 1.716·1.716·741 | **4.012** | **161** | **4.173** | **5.148** | **81,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·479 | 4.042 | 133 | 4.175 | 5.544 | 75,3 % |
| m2 | RUNNING | 1.848·1.848·272 | 3.833 | 135 | 3.968 | 5.544 | 71,6 % |
| m3 | RUNNING | 1.815·1.815·209 | 3.735 | 104 | 3.839 | 5.445 | 70,5 % |
| m4 | RUNNING | 1.716·1.716·741 | 4.012 | 161 | 4.173 | 5.148 | 81,1 % |
| **TOTAL** | — | — | **15.622** | **533** | **16.155** | **21.681** | **74,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:15
- m2: erros → emulator/boot:121, install/adb:14
- m3: erros → emulator/boot:91, install/adb:13
- m4: erros → emulator/boot:132, install/adb:29

**Ações (15:02 local):** Ciclo de rotina, sem incidentes. Cron local ativo (15:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up (m1 12h/exp_01 2h, m2 7h, m3 5h, m4 18h), run_procs=2 em todas. Sem OOM churn recente. Nenhuma ação corretiva. Total 16.155/21.681 = 74,5% (+156 vs 14:02). Todas na passada 300s subindo consistente; m4 >81%. Ordem: m4 81,1% > m1 75,3% > m2 71,6% > m3 70,5%. Reboots acumulados: 12.

## Ciclo 2026-07-09 16:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·125 | 1.021 | 28 | 1.049 | 1.386 | 75,7 % |
| exp_01 | Up | 462·462·118 | 1.004 | 38 | 1.042 | 1.386 | 75,2 % |
| exp_02 | Up | 462·462·126 | 1.018 | 32 | 1.050 | 1.386 | 75,8 % |
| exp_03 | Up | 462·462·128 | 1.019 | 33 | 1.052 | 1.386 | 75,9 % |
| **total** | — | 1.848·1.848·497 | **4.062** | **131** | **4.193** | **5.544** | **75,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·79 | 969 | 34 | 1.003 | 1.386 | 72,4 % |
| exp_01 | Up | 462·462·84 | 978 | 30 | 1.008 | 1.386 | 72,7 % |
| exp_02 | Up | 462·462·80 | 966 | 38 | 1.004 | 1.386 | 72,4 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·300 | **3.861** | **135** | **3.996** | **5.544** | **72,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·60 | 965 | 19 | 984 | 1.386 | 71,0 % |
| exp_01 | Up | 462·462·64 | 958 | 30 | 988 | 1.386 | 71,3 % |
| exp_02 | Up | 462·462·62 | 941 | 45 | 986 | 1.386 | 71,1 % |
| exp_03 | Up | 429·429·61 | 908 | 11 | 919 | 1.287 | 71,4 % |
| **total** | — | 1.815·1.815·247 | **3.772** | **105** | **3.877** | **5.445** | **71,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·190 | 1.000 | 48 | 1.048 | 1.287 | 81,4 % |
| exp_01 | Up | 429·429·189 | 1.019 | 28 | 1.047 | 1.287 | 81,4 % |
| exp_02 | Up | 429·429·194 | 1.014 | 38 | 1.052 | 1.287 | 81,7 % |
| exp_03 | Up | 429·429·200 | 1.008 | 50 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·773 | **4.041** | **164** | **4.205** | **5.148** | **81,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·497 | 4.062 | 131 | 4.193 | 5.544 | 75,6 % |
| m2 | RUNNING | 1.848·1.848·300 | 3.861 | 135 | 3.996 | 5.544 | 72,1 % |
| m3 | RUNNING | 1.815·1.815·247 | 3.772 | 105 | 3.877 | 5.445 | 71,2 % |
| m4 | RUNNING | 1.716·1.716·773 | 4.041 | 164 | 4.205 | 5.148 | 81,7 % |
| **TOTAL** | — | — | **15.736** | **535** | **16.271** | **21.681** | **75,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:119, install/adb:12
- m2: erros → emulator/boot:121, install/adb:14
- m3: erros → emulator/boot:91, install/adb:14
- m4: erros → emulator/boot:134, install/adb:30

## Ciclo 2026-07-09 16:02:58 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·125 | 1.021 | 28 | 1.049 | 1.386 | 75,7 % |
| exp_01 | Up | 462·462·118 | 1.004 | 38 | 1.042 | 1.386 | 75,2 % |
| exp_02 | Up | 462·462·126 | 1.018 | 32 | 1.050 | 1.386 | 75,8 % |
| exp_03 | Up | 462·462·128 | 1.019 | 33 | 1.052 | 1.386 | 75,9 % |
| **total** | — | 1.848·1.848·497 | **4.062** | **131** | **4.193** | **5.544** | **75,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·79 | 969 | 34 | 1.003 | 1.386 | 72,4 % |
| exp_01 | Up | 462·462·85 | 979 | 30 | 1.009 | 1.386 | 72,8 % |
| exp_02 | Up | 462·462·81 | 967 | 38 | 1.005 | 1.386 | 72,5 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·302 | **3.863** | **135** | **3.998** | **5.544** | **72,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·61 | 966 | 19 | 985 | 1.386 | 71,1 % |
| exp_01 | Up | 462·462·64 | 958 | 30 | 988 | 1.386 | 71,3 % |
| exp_02 | Up | 462·462·63 | 942 | 45 | 987 | 1.386 | 71,2 % |
| exp_03 | Up | 429·429·61 | 908 | 11 | 919 | 1.287 | 71,4 % |
| **total** | — | 1.815·1.815·249 | **3.774** | **105** | **3.879** | **5.445** | **71,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·190 | 1.000 | 48 | 1.048 | 1.287 | 81,4 % |
| exp_01 | Up | 429·429·189 | 1.019 | 28 | 1.047 | 1.287 | 81,4 % |
| exp_02 | Up | 429·429·194 | 1.014 | 38 | 1.052 | 1.287 | 81,7 % |
| exp_03 | Up | 429·429·200 | 1.008 | 50 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·773 | **4.041** | **164** | **4.205** | **5.148** | **81,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·497 | 4.062 | 131 | 4.193 | 5.544 | 75,6 % |
| m2 | RUNNING | 1.848·1.848·302 | 3.863 | 135 | 3.998 | 5.544 | 72,1 % |
| m3 | RUNNING | 1.815·1.815·249 | 3.774 | 105 | 3.879 | 5.445 | 71,2 % |
| m4 | RUNNING | 1.716·1.716·773 | 4.041 | 164 | 4.205 | 5.148 | 81,7 % |
| **TOTAL** | — | — | **15.740** | **535** | **16.275** | **21.681** | **75,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:119, install/adb:12
- m2: erros → emulator/boot:121, install/adb:14
- m3: erros → emulator/boot:91, install/adb:14
- m4: erros → emulator/boot:134, install/adb:30

**Ações (16:02 local):** Ciclo de rotina, sem incidentes pendentes. Cron local ativo (16:00 registrado). Varredura SSH: 4 VMs RUNNING, 5/5 containers Up. Dois containers auto-reiniciados pelo cron OOM (137) e já Up: m1 exp_02 (32min) e m4 exp_03 (2min) — nenhuma ação manual necessária. Total 16.275/21.681 = 75,1% (+120 vs 15:02; delta menor por causa do churn OOM em m1/m4). Todas na passada 300s subindo; m4 >82%. Ordem: m4 81,7% > m1 75,6% > m2 72,1% > m3 71,2%. Reboots acumulados: 12.

## Ciclo 2026-07-09 16:19:30 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·128 | 1.024 | 28 | 1.052 | 1.386 | 75,9 % |
| exp_01 | Up | 462·462·121 | 1.007 | 38 | 1.045 | 1.386 | 75,4 % |
| exp_02 | Up | 462·462·126 | 1.020 | 30 | 1.050 | 1.386 | 75,8 % |
| exp_03 | Up | 462·462·131 | 1.022 | 33 | 1.055 | 1.386 | 76,1 % |
| **total** | — | 1.848·1.848·506 | **4.073** | **129** | **4.202** | **5.544** | **75,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·82 | 972 | 34 | 1.006 | 1.386 | 72,6 % |
| exp_01 | Up | 462·462·87 | 981 | 30 | 1.011 | 1.386 | 72,9 % |
| exp_02 | Up | 462·462·83 | 969 | 38 | 1.007 | 1.386 | 72,7 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·309 | **3.870** | **135** | **4.005** | **5.544** | **72,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·63 | 968 | 19 | 987 | 1.386 | 71,2 % |
| exp_01 | Up | 462·462·68 | 960 | 32 | 992 | 1.386 | 71,6 % |
| exp_02 | Up | 462·462·65 | 944 | 45 | 989 | 1.386 | 71,4 % |
| exp_03 | Up | 429·429·64 | 911 | 11 | 922 | 1.287 | 71,6 % |
| **total** | — | 1.815·1.815·260 | **3.783** | **107** | **3.890** | **5.445** | **71,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·193 | 1.003 | 48 | 1.051 | 1.287 | 81,7 % |
| exp_01 | Up | 429·429·192 | 1.022 | 28 | 1.050 | 1.287 | 81,6 % |
| exp_02 | Up | 429·429·197 | 1.017 | 38 | 1.055 | 1.287 | 82,0 % |
| exp_03 | Up | 429·429·200 | 1.009 | 49 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·782 | **4.051** | **163** | **4.214** | **5.148** | **81,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·506 | 4.073 | 129 | 4.202 | 5.544 | 75,8 % |
| m2 | RUNNING | 1.848·1.848·309 | 3.870 | 135 | 4.005 | 5.544 | 72,2 % |
| m3 | RUNNING | 1.815·1.815·260 | 3.783 | 107 | 3.890 | 5.445 | 71,4 % |
| m4 | RUNNING | 1.716·1.716·782 | 4.051 | 163 | 4.214 | 5.148 | 81,9 % |
| **TOTAL** | — | — | **15.777** | **534** | **16.311** | **21.681** | **75,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:11
- m2: erros → emulator/boot:121, install/adb:14
- m3: erros → emulator/boot:93, install/adb:14
- m4: erros → emulator/boot:134, install/adb:29

**Ações (16:19 local):** Retomada de sessão + ciclo de rotina, sem incidentes. Cron local ativo (16:00 registrado). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up em cada, run_procs=2 (real+wrapper, normal). Cron OOM da VM reiniciou m1 exp_02 (15:30 local) e m4 exp_03 (16:00 local) — ambos Up, nenhuma ação manual. Sem SSH_FALHOU na última hora (últimos reboots: #11 m2 01:00, #12 m3 04:00, já recuperados; m2/m3 estáveis Up 8h/6h). Total 16.311/21.681 = 75,2% (+36 vs 16:02 — ciclo curto de 17min). Todas na passada 300s subindo; m4 82%. Ordem: m4 81,9% > m1 75,8% > m2 72,2% > m3 71,4%. Reboots acumulados: 12.

## Ciclo 2026-07-09 17:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·136 | 1.029 | 31 | 1.060 | 1.386 | 76,5 % |
| exp_01 | Up | 462·462·127 | 1.013 | 38 | 1.051 | 1.386 | 75,8 % |
| exp_02 | Up | 462·462·132 | 1.026 | 30 | 1.056 | 1.386 | 76,2 % |
| exp_03 | Up | 462·462·138 | 1.027 | 35 | 1.062 | 1.386 | 76,6 % |
| **total** | — | 1.848·1.848·533 | **4.095** | **134** | **4.229** | **5.544** | **76,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·90 | 978 | 36 | 1.014 | 1.386 | 73,2 % |
| exp_01 | Up | 462·462·94 | 988 | 30 | 1.018 | 1.386 | 73,4 % |
| exp_02 | Up | 462·462·90 | 976 | 38 | 1.014 | 1.386 | 73,2 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·331 | **3.890** | **137** | **4.027** | **5.544** | **72,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·71 | 973 | 22 | 995 | 1.386 | 71,8 % |
| exp_01 | Up | 462·462·75 | 966 | 33 | 999 | 1.386 | 72,1 % |
| exp_02 | Up | 462·462·74 | 950 | 48 | 998 | 1.386 | 72,0 % |
| exp_03 | Up | 429·429·71 | 915 | 14 | 929 | 1.287 | 72,2 % |
| **total** | — | 1.815·1.815·291 | **3.804** | **117** | **3.921** | **5.445** | **72,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·202 | 1.008 | 52 | 1.060 | 1.287 | 82,4 % |
| exp_01 | Up | 429·429·200 | 1.028 | 30 | 1.058 | 1.287 | 82,2 % |
| exp_02 | Up | 429·429·205 | 1.022 | 41 | 1.063 | 1.287 | 82,6 % |
| exp_03 | Up | 429·429·200 | 1.014 | 44 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·807 | **4.072** | **167** | **4.239** | **5.148** | **82,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·533 | 4.095 | 134 | 4.229 | 5.544 | 76,3 % |
| m2 | RUNNING | 1.848·1.848·331 | 3.890 | 137 | 4.027 | 5.544 | 72,6 % |
| m3 | RUNNING | 1.815·1.815·291 | 3.804 | 117 | 3.921 | 5.445 | 72,0 % |
| m4 | RUNNING | 1.716·1.716·807 | 4.072 | 167 | 4.239 | 5.148 | 82,3 % |
| **TOTAL** | — | — | **15.861** | **555** | **16.416** | **21.681** | **75,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:11
- m2: erros → emulator/boot:121, install/adb:16
- m3: erros → emulator/boot:103, install/adb:14
- m4: erros → emulator/boot:141, install/adb:26

## Ciclo 2026-07-09 17:03:43 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·136 | 1.029 | 31 | 1.060 | 1.386 | 76,5 % |
| exp_01 | Up | 462·462·128 | 1.014 | 38 | 1.052 | 1.386 | 75,9 % |
| exp_02 | Up | 462·462·133 | 1.026 | 31 | 1.057 | 1.386 | 76,3 % |
| exp_03 | Up | 462·462·139 | 1.028 | 35 | 1.063 | 1.386 | 76,7 % |
| **total** | — | 1.848·1.848·536 | **4.097** | **135** | **4.232** | **5.544** | **76,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·91 | 979 | 36 | 1.015 | 1.386 | 73,2 % |
| exp_01 | Up | 462·462·94 | 988 | 30 | 1.018 | 1.386 | 73,4 % |
| exp_02 | Up | 462·462·90 | 976 | 38 | 1.014 | 1.386 | 73,2 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·332 | **3.891** | **137** | **4.028** | **5.544** | **72,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·71 | 973 | 22 | 995 | 1.386 | 71,8 % |
| exp_01 | Up | 462·462·76 | 967 | 33 | 1.000 | 1.386 | 72,2 % |
| exp_02 | Up | 462·462·74 | 950 | 48 | 998 | 1.386 | 72,0 % |
| exp_03 | Up | 429·429·72 | 916 | 14 | 930 | 1.287 | 72,3 % |
| **total** | — | 1.815·1.815·293 | **3.806** | **117** | **3.923** | **5.445** | **72,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·203 | 1.009 | 52 | 1.061 | 1.287 | 82,4 % |
| exp_01 | Up | 429·429·200 | 1.028 | 30 | 1.058 | 1.287 | 82,2 % |
| exp_02 | Up | 429·429·206 | 1.023 | 41 | 1.064 | 1.287 | 82,7 % |
| exp_03 | Up | 429·429·200 | 1.015 | 43 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·809 | **4.075** | **166** | **4.241** | **5.148** | **82,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·536 | 4.097 | 135 | 4.232 | 5.544 | 76,3 % |
| m2 | RUNNING | 1.848·1.848·332 | 3.891 | 137 | 4.028 | 5.544 | 72,7 % |
| m3 | RUNNING | 1.815·1.815·293 | 3.806 | 117 | 3.923 | 5.445 | 72,0 % |
| m4 | RUNNING | 1.716·1.716·809 | 4.075 | 166 | 4.241 | 5.148 | 82,4 % |
| **TOTAL** | — | — | **15.869** | **555** | **16.424** | **21.681** | **75,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:124, install/adb:11
- m2: erros → emulator/boot:121, install/adb:16
- m3: erros → emulator/boot:103, install/adb:14
- m4: erros → emulator/boot:140, install/adb:26

**Ações (17:03 local):** Ciclo de rotina, sem incidentes. Cron local ativo (17:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up em cada, run_procs=2 (real+wrapper, normal). Sem SSH_FALHOU, sem OOM pendente — cron OOM da VM cobrindo. Nenhuma ação manual. Total 16.424/21.681 = 75,8% (+113 vs 16:19). Todas na passada 300s subindo; m4 82,4%. Ordem: m4 82,4% > m1 76,3% > m2 72,7% > m3 72,0%. Reboots acumulados: 12.

## Ciclo 2026-07-09 18:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·145 | 1.038 | 31 | 1.069 | 1.386 | 77,1 % |
| exp_01 | Up | 462·462·138 | 1.021 | 41 | 1.062 | 1.386 | 76,6 % |
| exp_02 | Up | 462·462·143 | 1.034 | 33 | 1.067 | 1.386 | 77,0 % |
| exp_03 | Up | 462·462·149 | 1.038 | 35 | 1.073 | 1.386 | 77,4 % |
| **total** | — | 1.848·1.848·575 | **4.131** | **140** | **4.271** | **5.544** | **77,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·103 | 987 | 40 | 1.027 | 1.386 | 74,1 % |
| exp_01 | Up | 462·462·104 | 995 | 33 | 1.028 | 1.386 | 74,2 % |
| exp_02 | Up | 462·462·100 | 985 | 39 | 1.024 | 1.386 | 73,9 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·364 | **3.915** | **145** | **4.060** | **5.544** | **73,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·82 | 982 | 24 | 1.006 | 1.386 | 72,6 % |
| exp_01 | Up | 462·462·86 | 977 | 33 | 1.010 | 1.386 | 72,9 % |
| exp_02 | Up | 462·462·84 | 960 | 48 | 1.008 | 1.386 | 72,7 % |
| exp_03 | Up | 429·429·81 | 925 | 14 | 939 | 1.287 | 73,0 % |
| **total** | — | 1.815·1.815·333 | **3.844** | **119** | **3.963** | **5.445** | **72,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·213 | 1.018 | 53 | 1.071 | 1.287 | 83,2 % |
| exp_01 | Up | 429·429·209 | 1.036 | 31 | 1.067 | 1.287 | 82,9 % |
| exp_02 | Up | 429·429·215 | 1.032 | 41 | 1.073 | 1.287 | 83,4 % |
| exp_03 | Up | 429·429·200 | 1.020 | 38 | 1.058 | 1.287 | 82,2 % |
| **total** | — | 1.716·1.716·837 | **4.106** | **163** | **4.269** | **5.148** | **82,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·575 | 4.131 | 140 | 4.271 | 5.544 | 77,0 % |
| m2 | RUNNING | 1.848·1.848·364 | 3.915 | 145 | 4.060 | 5.544 | 73,2 % |
| m3 | RUNNING | 1.815·1.815·333 | 3.844 | 119 | 3.963 | 5.445 | 72,8 % |
| m4 | RUNNING | 1.716·1.716·837 | 4.106 | 163 | 4.269 | 5.148 | 82,9 % |
| **TOTAL** | — | — | **15.996** | **567** | **16.563** | **21.681** | **76,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:129, install/adb:11
- m2: erros → emulator/boot:127, install/adb:18
- m3: erros → emulator/boot:103, install/adb:16
- m4: erros → emulator/boot:141, install/adb:22

## Ciclo 2026-07-09 18:03:45 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·146 | 1.039 | 31 | 1.070 | 1.386 | 77,2 % |
| exp_01 | Up | 462·462·139 | 1.022 | 41 | 1.063 | 1.386 | 76,7 % |
| exp_02 | Up | 462·462·143 | 1.034 | 33 | 1.067 | 1.386 | 77,0 % |
| exp_03 | Up | 462·462·150 | 1.039 | 35 | 1.074 | 1.386 | 77,5 % |
| **total** | — | 1.848·1.848·578 | **4.134** | **140** | **4.274** | **5.544** | **77,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·103 | 987 | 40 | 1.027 | 1.386 | 74,1 % |
| exp_01 | Up | 462·462·105 | 996 | 33 | 1.029 | 1.386 | 74,2 % |
| exp_02 | Up | 462·462·101 | 985 | 40 | 1.025 | 1.386 | 74,0 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·366 | **3.916** | **146** | **4.062** | **5.544** | **73,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·83 | 983 | 24 | 1.007 | 1.386 | 72,7 % |
| exp_01 | Up | 462·462·86 | 977 | 33 | 1.010 | 1.386 | 72,9 % |
| exp_02 | Up | 462·462·84 | 960 | 48 | 1.008 | 1.386 | 72,7 % |
| exp_03 | Up | 429·429·82 | 926 | 14 | 940 | 1.287 | 73,0 % |
| **total** | — | 1.815·1.815·335 | **3.846** | **119** | **3.965** | **5.445** | **72,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·213 | 1.018 | 53 | 1.071 | 1.287 | 83,2 % |
| exp_01 | Up | 429·429·210 | 1.037 | 31 | 1.068 | 1.287 | 83,0 % |
| exp_02 | Up | 429·429·216 | 1.033 | 41 | 1.074 | 1.287 | 83,4 % |
| exp_03 | Up | 429·429·201 | 1.020 | 39 | 1.059 | 1.287 | 82,3 % |
| **total** | — | 1.716·1.716·840 | **4.108** | **164** | **4.272** | **5.148** | **83,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·578 | 4.134 | 140 | 4.274 | 5.544 | 77,1 % |
| m2 | RUNNING | 1.848·1.848·366 | 3.916 | 146 | 4.062 | 5.544 | 73,3 % |
| m3 | RUNNING | 1.815·1.815·335 | 3.846 | 119 | 3.965 | 5.445 | 72,8 % |
| m4 | RUNNING | 1.716·1.716·840 | 4.108 | 164 | 4.272 | 5.148 | 83,0 % |
| **TOTAL** | — | — | **16.004** | **569** | **16.573** | **21.681** | **76,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:129, install/adb:11
- m2: erros → emulator/boot:128, install/adb:18
- m3: erros → emulator/boot:103, install/adb:16
- m4: erros → emulator/boot:142, install/adb:22

**Ações (18:03 local):** Ciclo de rotina, sem incidentes. Cron local ativo (18:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up em cada, run_procs=2 (normal). Sem SSH_FALHOU, sem OOM pendente — cron OOM da VM cobrindo. Nenhuma ação manual. Total 16.573/21.681 = 76,4% (+149 vs 17:03). Todas na passada 300s subindo; m4 83,0%. Ordem: m4 83,0% > m1 77,1% > m2 73,3% > m3 72,8%. Reboots acumulados: 12.

## Ciclo 2026-07-09 19:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.048 | 31 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.031 | 41 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.043 | 33 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.047 | 35 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.169** | **140** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·112 | 996 | 40 | 1.036 | 1.386 | 74,7 % |
| exp_01 | Up | 462·462·114 | 1.005 | 33 | 1.038 | 1.386 | 74,9 % |
| exp_02 | Up | 462·462·112 | 994 | 42 | 1.036 | 1.386 | 74,7 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·395 | **3.943** | **148** | **4.091** | **5.544** | **73,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·93 | 992 | 25 | 1.017 | 1.386 | 73,4 % |
| exp_01 | Up | 462·462·96 | 987 | 33 | 1.020 | 1.386 | 73,6 % |
| exp_02 | Up | 462·462·93 | 969 | 48 | 1.017 | 1.386 | 73,4 % |
| exp_03 | Up | 429·429·91 | 935 | 14 | 949 | 1.287 | 73,7 % |
| **total** | — | 1.815·1.815·373 | **3.883** | **120** | **4.003** | **5.445** | **73,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·223 | 1.027 | 54 | 1.081 | 1.287 | 84,0 % |
| exp_01 | Up | 429·429·220 | 1.046 | 32 | 1.078 | 1.287 | 83,8 % |
| exp_02 | Up | 429·429·225 | 1.041 | 42 | 1.083 | 1.287 | 84,1 % |
| exp_03 | Up | 429·429·212 | 1.031 | 39 | 1.070 | 1.287 | 83,1 % |
| **total** | — | 1.716·1.716·880 | **4.145** | **167** | **4.312** | **5.148** | **83,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.169 | 140 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·395 | 3.943 | 148 | 4.091 | 5.544 | 73,8 % |
| m3 | RUNNING | 1.815·1.815·373 | 3.883 | 120 | 4.003 | 5.445 | 73,5 % |
| m4 | RUNNING | 1.716·1.716·880 | 4.145 | 167 | 4.312 | 5.148 | 83,8 % |
| **TOTAL** | — | — | **16.140** | **575** | **16.715** | **21.681** | **77,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:129, install/adb:11
- m2: erros → emulator/boot:129, install/adb:19
- m3: erros → emulator/boot:103, install/adb:17
- m4: erros → emulator/boot:142, install/adb:25

## Ciclo 2026-07-09 19:07:28 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.048 | 31 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.031 | 41 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.043 | 33 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.047 | 35 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.169** | **140** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·113 | 997 | 40 | 1.037 | 1.386 | 74,8 % |
| exp_01 | Up | 462·462·115 | 1.006 | 33 | 1.039 | 1.386 | 75,0 % |
| exp_02 | Up | 462·462·113 | 995 | 42 | 1.037 | 1.386 | 74,8 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·398 | **3.946** | **148** | **4.094** | **5.544** | **73,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·94 | 993 | 25 | 1.018 | 1.386 | 73,4 % |
| exp_01 | Up | 462·462·97 | 988 | 33 | 1.021 | 1.386 | 73,7 % |
| exp_02 | Up | 462·462·94 | 970 | 48 | 1.018 | 1.386 | 73,4 % |
| exp_03 | Up | 429·429·92 | 936 | 14 | 950 | 1.287 | 73,8 % |
| **total** | — | 1.815·1.815·377 | **3.887** | **120** | **4.007** | **5.445** | **73,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·224 | 1.028 | 54 | 1.082 | 1.287 | 84,1 % |
| exp_01 | Up | 429·429·221 | 1.047 | 32 | 1.079 | 1.287 | 83,8 % |
| exp_02 | Up | 429·429·227 | 1.042 | 43 | 1.085 | 1.287 | 84,3 % |
| exp_03 | Up | 429·429·213 | 1.032 | 39 | 1.071 | 1.287 | 83,2 % |
| **total** | — | 1.716·1.716·885 | **4.149** | **168** | **4.317** | **5.148** | **83,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.169 | 140 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·398 | 3.946 | 148 | 4.094 | 5.544 | 73,8 % |
| m3 | RUNNING | 1.815·1.815·377 | 3.887 | 120 | 4.007 | 5.445 | 73,6 % |
| m4 | RUNNING | 1.716·1.716·885 | 4.149 | 168 | 4.317 | 5.148 | 83,9 % |
| **TOTAL** | — | — | **16.151** | **576** | **16.727** | **21.681** | **77,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:129, install/adb:11
- m2: erros → emulator/boot:129, install/adb:19
- m3: erros → emulator/boot:103, install/adb:17
- m4: erros → emulator/boot:142, install/adb:26

**Ações (19:07 local):** ⚠️ INCIDENTE — m1 banner-timeout (primeiro da m1; padrão de cluster agora atingiu as 3 VMs m1/m2/m3). Cron local ativo (19:00 pegou m1:RUNNING 78% — travou logo após). Varredura SSH: m2/m3/m4 RUNNING 5/5 Up; m1 SSH_FALHOU. Confirmado m1 RUNNING no gcloud + 3 retentativas SSH (ConnectTimeout 20→30→40) todas banner-timeout → m1 travada de verdade → **reboot #13** (gcloud reset m1-exp02 22:06 UTC). SSH voltou em ~20s (up 0 min). Containers Exited(255) + run morto pós-reboot → RESUME disparado → confirmado 5/5 Up + run_reais=1 (19:07 local). Dados íntegros (resume idempotente). Total 16.727/21.681 = 77,2% (+154 vs 18:03). Ordem: m4 83,9% > m1 77,7% > m2 73,8% > m3 73,6%. Reboots acumulados: **13**.

## Marco — reboot #13 (m1 banner-timeout) 2026-07-09 ~22:06 UTC / 19:06 local
Primeiro banner-timeout da m1. Sequência de cluster completa: m2 (#10 23:17, #11 01:06), m3 (#12 04:04), agora m1 (#13). VM RUNNING no gcloud, sshd sem responder ao handshake sob pressão de memória. Tratamento padrão: reset → SSH volta ~20s → RESUME → 5/5 Up + run vivo. Sem perda de dados. m4 permanece a única VM nunca rebootada (Up ~22h).

## Ciclo 2026-07-09 20:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.050 | 29 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.033 | 39 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.043 | 33 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.048 | 34 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.174** | **135** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·122 | 1.006 | 40 | 1.046 | 1.386 | 75,5 % |
| exp_01 | Up | 462·462·124 | 1.015 | 33 | 1.048 | 1.386 | 75,6 % |
| exp_02 | Up | 462·462·121 | 1.003 | 42 | 1.045 | 1.386 | 75,4 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·424 | **3.972** | **148** | **4.120** | **5.544** | **74,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·104 | 999 | 29 | 1.028 | 1.386 | 74,2 % |
| exp_01 | Up | 462·462·107 | 995 | 36 | 1.031 | 1.386 | 74,4 % |
| exp_02 | Up | 462·462·104 | 977 | 51 | 1.028 | 1.386 | 74,2 % |
| exp_03 | Up | 429·429·102 | 943 | 17 | 960 | 1.287 | 74,6 % |
| **total** | — | 1.815·1.815·417 | **3.914** | **133** | **4.047** | **5.445** | **74,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·236 | 1.035 | 59 | 1.094 | 1.287 | 85,0 % |
| exp_01 | Up | 429·429·229 | 1.055 | 32 | 1.087 | 1.287 | 84,5 % |
| exp_02 | Up | 429·429·238 | 1.051 | 45 | 1.096 | 1.287 | 85,2 % |
| exp_03 | Up | 429·429·221 | 1.040 | 39 | 1.079 | 1.287 | 83,8 % |
| **total** | — | 1.716·1.716·924 | **4.181** | **175** | **4.356** | **5.148** | **84,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.174 | 135 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·424 | 3.972 | 148 | 4.120 | 5.544 | 74,3 % |
| m3 | RUNNING | 1.815·1.815·417 | 3.914 | 133 | 4.047 | 5.445 | 74,3 % |
| m4 | RUNNING | 1.716·1.716·924 | 4.181 | 175 | 4.356 | 5.148 | 84,6 % |
| **TOTAL** | — | — | **16.241** | **591** | **16.832** | **21.681** | **77,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:122, install/adb:13
- m2: erros → emulator/boot:129, install/adb:19
- m3: erros → emulator/boot:115, install/adb:18
- m4: erros → emulator/boot:147, install/adb:28

## Ciclo 2026-07-09 20:02:34 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.050 | 29 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.033 | 39 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.043 | 33 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.049 | 33 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.175** | **134** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·122 | 1.006 | 40 | 1.046 | 1.386 | 75,5 % |
| exp_01 | Up | 462·462·124 | 1.015 | 33 | 1.048 | 1.386 | 75,6 % |
| exp_02 | Up | 462·462·122 | 1.004 | 42 | 1.046 | 1.386 | 75,5 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·425 | **3.973** | **148** | **4.121** | **5.544** | **74,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·104 | 999 | 29 | 1.028 | 1.386 | 74,2 % |
| exp_01 | Up | 462·462·107 | 995 | 36 | 1.031 | 1.386 | 74,4 % |
| exp_02 | Up | 462·462·105 | 978 | 51 | 1.029 | 1.386 | 74,2 % |
| exp_03 | Up | 429·429·102 | 943 | 17 | 960 | 1.287 | 74,6 % |
| **total** | — | 1.815·1.815·418 | **3.915** | **133** | **4.048** | **5.445** | **74,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·236 | 1.035 | 59 | 1.094 | 1.287 | 85,0 % |
| exp_01 | Up | 429·429·230 | 1.056 | 32 | 1.088 | 1.287 | 84,5 % |
| exp_02 | Up | 429·429·238 | 1.051 | 45 | 1.096 | 1.287 | 85,2 % |
| exp_03 | Up | 429·429·221 | 1.040 | 39 | 1.079 | 1.287 | 83,8 % |
| **total** | — | 1.716·1.716·925 | **4.182** | **175** | **4.357** | **5.148** | **84,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.175 | 134 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·425 | 3.973 | 148 | 4.121 | 5.544 | 74,3 % |
| m3 | RUNNING | 1.815·1.815·418 | 3.915 | 133 | 4.048 | 5.445 | 74,3 % |
| m4 | RUNNING | 1.716·1.716·925 | 4.182 | 175 | 4.357 | 5.148 | 84,6 % |
| **TOTAL** | — | — | **16.245** | **590** | **16.835** | **21.681** | **77,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:121, install/adb:13
- m2: erros → emulator/boot:129, install/adb:19
- m3: erros → emulator/boot:115, install/adb:18
- m4: erros → emulator/boot:147, install/adb:28

**Ações (20:02 local):** Ciclo de rotina, sem incidentes. Cron local ativo (20:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up em cada, run_procs=2 (normal). m1 estável pós-reboot #13 (Up 31min; cron OOM já cobriu 1 restart de exp_02 — normal). Sem SSH_FALHOU. Nenhuma ação manual. Total 16.835/21.681 = 77,6% (+108 vs 19:07). m1 quase flat (custo do reboot 19:06, ~7min parada+resume); m2/m3/m4 subindo bem. Ordem: m4 84,6% > m1 77,7% > m2 74,3% ≈ m3 74,3%. Reboots acumulados: 13.

## Ciclo 2026-07-09 21:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.052 | 27 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.037 | 35 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.044 | 32 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.050 | 32 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.183** | **126** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·131 | 1.015 | 40 | 1.055 | 1.386 | 76,1 % |
| exp_01 | Up | 462·462·135 | 1.023 | 36 | 1.059 | 1.386 | 76,4 % |
| exp_02 | Up | 462·462·131 | 1.013 | 42 | 1.055 | 1.386 | 76,1 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·454 | **3.999** | **151** | **4.150** | **5.544** | **74,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·113 | 1.007 | 30 | 1.037 | 1.386 | 74,8 % |
| exp_01 | Up | 462·462·116 | 1.004 | 36 | 1.040 | 1.386 | 75,0 % |
| exp_02 | Up | 462·462·114 | 987 | 51 | 1.038 | 1.386 | 74,9 % |
| exp_03 | Up | 429·429·113 | 953 | 18 | 971 | 1.287 | 75,4 % |
| **total** | — | 1.815·1.815·456 | **3.951** | **135** | **4.086** | **5.445** | **75,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·246 | 1.045 | 59 | 1.104 | 1.287 | 85,8 % |
| exp_01 | Up | 429·429·239 | 1.063 | 34 | 1.097 | 1.287 | 85,2 % |
| exp_02 | Up | 429·429·247 | 1.060 | 45 | 1.105 | 1.287 | 85,9 % |
| exp_03 | Up | 429·429·230 | 1.049 | 39 | 1.088 | 1.287 | 84,5 % |
| **total** | — | 1.716·1.716·962 | **4.217** | **177** | **4.394** | **5.148** | **85,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.183 | 126 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·454 | 3.999 | 151 | 4.150 | 5.544 | 74,9 % |
| m3 | RUNNING | 1.815·1.815·456 | 3.951 | 135 | 4.086 | 5.445 | 75,0 % |
| m4 | RUNNING | 1.716·1.716·962 | 4.217 | 177 | 4.394 | 5.148 | 85,4 % |
| **TOTAL** | — | — | **16.350** | **589** | **16.939** | **21.681** | **78,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:118, install/adb:8
- m2: erros → emulator/boot:132, install/adb:19
- m3: erros → emulator/boot:115, install/adb:20
- m4: erros → emulator/boot:149, install/adb:28

## Ciclo 2026-07-09 21:02:33 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.052 | 27 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.037 | 35 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.044 | 32 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.051 | 31 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.184** | **125** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·132 | 1.016 | 40 | 1.056 | 1.386 | 76,2 % |
| exp_01 | Up | 462·462·135 | 1.023 | 36 | 1.059 | 1.386 | 76,4 % |
| exp_02 | Up | 462·462·131 | 1.013 | 42 | 1.055 | 1.386 | 76,1 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·455 | **4.000** | **151** | **4.151** | **5.544** | **74,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·113 | 1.007 | 30 | 1.037 | 1.386 | 74,8 % |
| exp_01 | Up | 462·462·116 | 1.004 | 36 | 1.040 | 1.386 | 75,0 % |
| exp_02 | Up | 462·462·114 | 987 | 51 | 1.038 | 1.386 | 74,9 % |
| exp_03 | Up | 429·429·115 | 954 | 19 | 973 | 1.287 | 75,6 % |
| **total** | — | 1.815·1.815·458 | **3.952** | **136** | **4.088** | **5.445** | **75,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·246 | 1.045 | 59 | 1.104 | 1.287 | 85,8 % |
| exp_01 | Up | 429·429·240 | 1.064 | 34 | 1.098 | 1.287 | 85,3 % |
| exp_02 | Up | 429·429·247 | 1.060 | 45 | 1.105 | 1.287 | 85,9 % |
| exp_03 | Up | 429·429·230 | 1.049 | 39 | 1.088 | 1.287 | 84,5 % |
| **total** | — | 1.716·1.716·963 | **4.218** | **177** | **4.395** | **5.148** | **85,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.184 | 125 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·455 | 4.000 | 151 | 4.151 | 5.544 | 74,9 % |
| m3 | RUNNING | 1.815·1.815·458 | 3.952 | 136 | 4.088 | 5.445 | 75,1 % |
| m4 | RUNNING | 1.716·1.716·963 | 4.218 | 177 | 4.395 | 5.148 | 85,4 % |
| **TOTAL** | — | — | **16.354** | **589** | **16.943** | **21.681** | **78,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:117, install/adb:8
- m2: erros → emulator/boot:132, install/adb:19
- m3: erros → emulator/boot:115, install/adb:21
- m4: erros → emulator/boot:149, install/adb:28

**Ações (21:02 local):** Ciclo de rotina. Cron local ativo (21:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up em cada, run_procs=2 (normal). Cron OOM cobriu restarts recentes (m1 exp_00/exp_02, m3 exp_00, todos Up). Sem SSH_FALHOU. Nenhuma ação manual. Total 16.943/21.681 = 78,1% (+108 vs 20:02). ⚠️ m1 FLAT há 2 ciclos (done=4.309 desde 19:07; 300-pass feito=613 parado). DIAGNÓSTICO ATIVO: m1 está VIVO e trabalhando (logs: Monkey ativo, boot emulador, coverage 9%); flat = taxa de churn de OOM pós-reboot #13 (boot storm dos 4 containers juntos → OOMs repetidos → skip-loop refeito → throughput ~zero). Não é barreira (mid-pass 554/1848 COMPLETED no 300), não é deadlock. Memória m1 já recuperou (19 GB disponíveis) → deve retomar. VIGIAR próximo ciclo; escalar só se persistir. m2/m3/m4 subindo bem. Ordem: m4 85,4% > m1 77,7% > m3 75,1% > m2 74,9%. Reboots acumulados: 13.

**Ações (21:10 local):** ⚠️ AÇÃO CORRETIVA — m1 flat há 2h (done=4.309 desde 19:07, sem avanço líquido) apesar de "vivo": decisão do usuário de rebootar+resumir em vez de esperar o churn de OOM estabilizar. **reboot #14** (gcloud reset m1-exp02 00:08 UTC / 21:08 local). SSH voltou ~20s (up 0 min). Containers Exited(255) + run morto → RESUME → confirmado 5/5 Up + run_reais=1 (21:10 local). Dados íntegros (resume idempotente; done=4.309 preservado). Reboots acumulados: **14**. Lição: churn de OOM pós-reboot pode manter uma VM efetivamente parada (throughput ~0) por 2h+ mesmo com processos vivos — reboot+resume limpa o estado e é preferível a esperar quando o avanço líquido é zero por 2 ciclos.

## Ciclo 2026-07-09 22:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.052 | 27 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.037 | 35 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.044 | 32 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.054 | 28 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.187** | **122** | **4.309** | **5.544** | **77,7 %** |

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·113 | 1.011 | 26 | 1.037 | 1.386 | 74,8 % |
| exp_01 | Up | 462·462·127 | 1.014 | 37 | 1.051 | 1.386 | 75,8 % |
| exp_02 | Up | 462·462·124 | 997 | 51 | 1.048 | 1.386 | 75,6 % |
| exp_03 | Up | 429·429·124 | 963 | 19 | 982 | 1.287 | 76,3 % |
| **total** | — | 1.815·1.815·488 | **3.985** | **133** | **4.118** | **5.445** | **75,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·257 | 1.056 | 59 | 1.115 | 1.287 | 86,6 % |
| exp_01 | Up | 429·429·249 | 1.072 | 35 | 1.107 | 1.287 | 86,0 % |
| exp_02 | Up | 429·429·257 | 1.070 | 45 | 1.115 | 1.287 | 86,6 % |
| exp_03 | Up | 429·429·242 | 1.058 | 42 | 1.100 | 1.287 | 85,5 % |
| **total** | — | 1.716·1.716·1.005 | **4.256** | **181** | **4.437** | **5.148** | **86,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.187 | 122 | 4.309 | 5.544 | 77,7 % |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | RUNNING | 1.815·1.815·488 | 3.985 | 133 | 4.118 | 5.445 | 75,6 % |
| m4 | RUNNING | 1.716·1.716·1.005 | 4.256 | 181 | 4.437 | 5.148 | 86,2 % |
| **TOTAL** | — | — | **12.428** | **436** | **12.864** | **16.137** | **79,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:116, install/adb:6
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:115, install/adb:18
- m4: erros → emulator/boot:152, install/adb:29

## Ciclo 2026-07-09 22:07:30 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.052 | 27 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.037 | 35 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.045 | 31 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.055 | 27 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.189** | **120** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.022 | 43 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.032 | 36 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.020 | 45 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 948 | 33 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.022** | **157** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·113 | 1.012 | 25 | 1.037 | 1.386 | 74,8 % |
| exp_01 | Up | 462·462·127 | 1.014 | 37 | 1.051 | 1.386 | 75,8 % |
| exp_02 | Up | 462·462·124 | 997 | 51 | 1.048 | 1.386 | 75,6 % |
| exp_03 | Up | 429·429·125 | 964 | 19 | 983 | 1.287 | 76,4 % |
| **total** | — | 1.815·1.815·489 | **3.987** | **132** | **4.119** | **5.445** | **75,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·257 | 1.056 | 59 | 1.115 | 1.287 | 86,6 % |
| exp_01 | Up | 429·429·249 | 1.072 | 35 | 1.107 | 1.287 | 86,0 % |
| exp_02 | Up | 429·429·257 | 1.070 | 45 | 1.115 | 1.287 | 86,6 % |
| exp_03 | Up | 429·429·243 | 1.059 | 42 | 1.101 | 1.287 | 85,5 % |
| **total** | — | 1.716·1.716·1.006 | **4.257** | **181** | **4.438** | **5.148** | **86,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.189 | 120 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.022 | 157 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·489 | 3.987 | 132 | 4.119 | 5.445 | 75,6 % |
| m4 | RUNNING | 1.716·1.716·1.006 | 4.257 | 181 | 4.438 | 5.148 | 86,2 % |
| **TOTAL** | — | — | **16.455** | **590** | **17.045** | **21.681** | **78,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:115, install/adb:5
- m2: erros → emulator/boot:138, install/adb:19
- m3: erros → emulator/boot:115, install/adb:17
- m4: erros → emulator/boot:151, install/adb:30

**Ações (22:07 local):** ⚠️ DOIS INCIDENTES. (1) m2 banner-timeout (cron pegou m2:SSH_FALHOU 22:00) → RUNNING no gcloud + 3 retentativas SSH (20→30→40) banner-timeout → **reboot #15** (01:06 UTC / 22:06 local) → SSH ~20s → Exited(255)+run morto → RESUME → 5/5 Up + run_reais=1. (2) m1 exp_00 Exited(137) → docker start (5/5 Up). Cron OOM cobrindo m3/m4 (restarts normais). Total 17.045/21.681 = 78,6% (+102 vs 21:02).

**DIAGNÓSTICO m1 (raiz do "flat" — CORRIGE a hipótese de churn):** m1 ainda done=4.309 pós-reboot #14. CAUSA REAL: containers m1 estão em RV_TIMEOUTS=180, NÃO 300. Cada reboot reinicia run_experiment.sh desde a passada 60 → precisa RE-CAMINHAR os skip-loops de 60 e 180 (re-boot emuladores + re-tentar tasks ERROR) antes de re-alcançar a 300. done fica flat porque a passada 300 (554 COMPLETED) não avança até a m1 re-chegar nela. Logs = trabalho real (exp_02 coverage 40%/MOP 36%, exp_03 parsing static, MOP violations reconstruídas) → está re-tentando os ~54 erros da 180. IMPLICAÇÃO: reboot NÃO acelera m1 — reseta o ponteiro de passada e adiciona custo de re-caminhada (~30-60min). Dados íntegros (idempotente). NÃO rebootar de novo por flat — só se run morto/VM travada. m1 volta a subir done ao re-alcançar a 300. Reboots acumulados: **15**. Ordem: m4 86,2% > m1 77,7% > m3 75,6% > m2 75,4%.

## Ciclo 2026-07-09 23:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.054 | 25 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.038 | 34 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.045 | 31 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.057 | 25 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.194** | **115** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.022 | 43 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.033 | 35 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.021 | 44 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 949 | 32 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.025** | **154** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·119 | 1.019 | 24 | 1.043 | 1.386 | 75,3 % |
| exp_01 | Up | 462·462·137 | 1.022 | 39 | 1.061 | 1.386 | 76,6 % |
| exp_02 | Up | 462·462·135 | 1.005 | 54 | 1.059 | 1.386 | 76,4 % |
| exp_03 | Up | 429·429·135 | 971 | 22 | 993 | 1.287 | 77,2 % |
| **total** | — | 1.815·1.815·526 | **4.017** | **139** | **4.156** | **5.445** | **76,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·268 | 1.064 | 62 | 1.126 | 1.287 | 87,5 % |
| exp_01 | Up | 429·429·249 | 1.075 | 32 | 1.107 | 1.287 | 86,0 % |
| exp_02 | Up | 429·429·267 | 1.077 | 48 | 1.125 | 1.287 | 87,4 % |
| exp_03 | Up | 429·429·252 | 1.067 | 43 | 1.110 | 1.287 | 86,2 % |
| **total** | — | 1.716·1.716·1.036 | **4.283** | **185** | **4.468** | **5.148** | **86,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.194 | 115 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.025 | 154 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·526 | 4.017 | 139 | 4.156 | 5.445 | 76,3 % |
| m4 | RUNNING | 1.716·1.716·1.036 | 4.283 | 185 | 4.468 | 5.148 | 86,8 % |
| **TOTAL** | — | — | **16.519** | **593** | **17.112** | **21.681** | **78,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:110, install/adb:5
- m2: erros → emulator/boot:134, install/adb:20
- m3: erros → emulator/boot:121, install/adb:18
- m4: erros → emulator/boot:157, install/adb:28

## Ciclo 2026-07-09 23:02:40 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.054 | 25 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·148 | 1.039 | 33 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·152 | 1.045 | 31 | 1.076 | 1.386 | 77,6 % |
| exp_03 | Up | 462·462·158 | 1.057 | 25 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·613 | **4.195** | **114** | **4.309** | **5.544** | **77,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.022 | 43 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.034 | 34 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.021 | 44 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 949 | 32 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.026** | **153** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·119 | 1.019 | 24 | 1.043 | 1.386 | 75,3 % |
| exp_01 | Up | 462·462·137 | 1.022 | 39 | 1.061 | 1.386 | 76,6 % |
| exp_02 | Up | 462·462·135 | 1.005 | 54 | 1.059 | 1.386 | 76,4 % |
| exp_03 | Up | 429·429·135 | 971 | 22 | 993 | 1.287 | 77,2 % |
| **total** | — | 1.815·1.815·526 | **4.017** | **139** | **4.156** | **5.445** | **76,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·268 | 1.064 | 62 | 1.126 | 1.287 | 87,5 % |
| exp_01 | Up | 429·429·249 | 1.076 | 31 | 1.107 | 1.287 | 86,0 % |
| exp_02 | Up | 429·429·268 | 1.078 | 48 | 1.126 | 1.287 | 87,5 % |
| exp_03 | Up | 429·429·253 | 1.068 | 43 | 1.111 | 1.287 | 86,3 % |
| **total** | — | 1.716·1.716·1.038 | **4.286** | **184** | **4.470** | **5.148** | **86,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·613 | 4.195 | 114 | 4.309 | 5.544 | 77,7 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.026 | 153 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·526 | 4.017 | 139 | 4.156 | 5.445 | 76,3 % |
| m4 | RUNNING | 1.716·1.716·1.038 | 4.286 | 184 | 4.470 | 5.148 | 86,8 % |
| **TOTAL** | — | — | **16.524** | **590** | **17.114** | **21.681** | **78,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:108, install/adb:6
- m2: erros → emulator/boot:133, install/adb:20
- m3: erros → emulator/boot:121, install/adb:18
- m4: erros → emulator/boot:156, install/adb:28

**Ações (23:02 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (23:00 registrado, m2 recuperada). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 containers Up, run_procs=2. Cron OOM cobrindo restarts (normais). Nenhuma ação manual. Total 17.114/21.681 = 78,9% (+69 vs 22:07 — puxado por m3 +37 e m4 +32). m1 e m2 FLAT (done 4.309/4.179): confirmado que AMBOS re-caminham a passada 180 (RV_TIMEOUTS=180 nos 4 containers de cada) pós-reboots #14/#15. m1 já ~2h na re-caminhada — lenta por churn de OOM (re-tenta ~54 erros da 180 a até 180s cada + re-boots de emulador). VIVO e trabalhando; NÃO rebootar (lição 22:07). Se m1 NÃO alcançar a passada 300 até o próximo ciclo, investigar se o churn de OOM está IMPEDINDO a passada 180 de completar (barreira-like: containers OOMam antes de sair exit 0) — nesse caso a ação é só docker start + aguardar, nunca reboot. Ordem: m4 86,8% > m1 77,7% > m3 76,3% > m2 75,4%. Reboots acumulados: 15.

## Ciclo 2026-07-10 00:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.055 | 24 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·149 | 1.040 | 33 | 1.073 | 1.386 | 77,4 % |
| exp_02 | Up | 462·462·153 | 1.048 | 29 | 1.077 | 1.386 | 77,7 % |
| exp_03 | Up | 462·462·158 | 1.060 | 22 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·615 | **4.203** | **108** | **4.311** | **5.544** | **77,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.025 | 40 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.037 | 31 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.023 | 42 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 951 | 30 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.036** | **143** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·128 | 1.028 | 24 | 1.052 | 1.386 | 75,9 % |
| exp_01 | Up | 462·462·148 | 1.031 | 41 | 1.072 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·146 | 1.014 | 56 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 429·429·146 | 981 | 23 | 1.004 | 1.287 | 78,0 % |
| **total** | — | 1.815·1.815·568 | **4.054** | **144** | **4.198** | **5.445** | **77,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·279 | 1.074 | 63 | 1.137 | 1.287 | 88,3 % |
| exp_01 | Up | 429·429·253 | 1.082 | 29 | 1.111 | 1.287 | 86,3 % |
| exp_02 | Up | 429·429·277 | 1.087 | 48 | 1.135 | 1.287 | 88,2 % |
| exp_03 | Up | 429·429·262 | 1.077 | 43 | 1.120 | 1.287 | 87,0 % |
| **total** | — | 1.716·1.716·1.071 | **4.320** | **183** | **4.503** | **5.148** | **87,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·615 | 4.203 | 108 | 4.311 | 5.544 | 77,8 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.036 | 143 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·568 | 4.054 | 144 | 4.198 | 5.445 | 77,1 % |
| m4 | RUNNING | 1.716·1.716·1.071 | 4.320 | 183 | 4.503 | 5.148 | 87,5 % |
| **TOTAL** | — | — | **16.613** | **578** | **17.191** | **21.681** | **79,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:104, install/adb:4
- m2: erros → emulator/boot:127, install/adb:16
- m3: erros → emulator/boot:121, install/adb:23
- m4: erros → emulator/boot:156, install/adb:27

## Ciclo 2026-07-10 00:02:44 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·155 | 1.055 | 24 | 1.079 | 1.386 | 77,8 % |
| exp_01 | Up | 462·462·149 | 1.040 | 33 | 1.073 | 1.386 | 77,4 % |
| exp_02 | Up | 462·462·153 | 1.048 | 29 | 1.077 | 1.386 | 77,7 % |
| exp_03 | Up | 462·462·158 | 1.060 | 22 | 1.082 | 1.386 | 78,1 % |
| **total** | — | 1.848·1.848·615 | **4.203** | **108** | **4.311** | **5.544** | **77,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.026 | 39 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.037 | 31 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.023 | 42 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 951 | 30 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.037** | **142** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·128 | 1.028 | 24 | 1.052 | 1.386 | 75,9 % |
| exp_01 | Up | 462·462·149 | 1.032 | 41 | 1.073 | 1.386 | 77,4 % |
| exp_02 | Up | 462·462·146 | 1.014 | 56 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 429·429·146 | 981 | 23 | 1.004 | 1.287 | 78,0 % |
| **total** | — | 1.815·1.815·569 | **4.055** | **144** | **4.199** | **5.445** | **77,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·279 | 1.074 | 63 | 1.137 | 1.287 | 88,3 % |
| exp_01 | Up | 429·429·253 | 1.082 | 29 | 1.111 | 1.287 | 86,3 % |
| exp_02 | Up | 429·429·277 | 1.087 | 48 | 1.135 | 1.287 | 88,2 % |
| exp_03 | Up | 429·429·262 | 1.077 | 43 | 1.120 | 1.287 | 87,0 % |
| **total** | — | 1.716·1.716·1.071 | **4.320** | **183** | **4.503** | **5.148** | **87,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·615 | 4.203 | 108 | 4.311 | 5.544 | 77,8 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.037 | 142 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·569 | 4.055 | 144 | 4.199 | 5.445 | 77,1 % |
| m4 | RUNNING | 1.716·1.716·1.071 | 4.320 | 183 | 4.503 | 5.148 | 87,5 % |
| **TOTAL** | — | — | **16.615** | **577** | **17.192** | **21.681** | **79,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:104, install/adb:4
- m2: erros → emulator/boot:126, install/adb:16
- m3: erros → emulator/boot:121, install/adb:23
- m4: erros → emulator/boot:156, install/adb:27

**Ações (00:02 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (00:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1 (run real; wrapper do resume já saiu — normal). Nenhuma ação manual. Total 17.192/21.681 = 79,3% (+78 vs 23:02; m3 +43, m4 +33). ✅ m1 RE-ALCANÇOU a passada 300 (RV_TIMEOUTS=300 nos 4 containers) — re-caminhada pós-reboots #14/#15 concluída; done 4.309→4.311 (300-pass 613→615), deve acelerar agora. m2 ainda na 180 (rebootou mais tarde #15 22:06 — re-caminhada em curso, esperado). Cluster saudável. Ordem: m4 87,5% > m1 77,8% > m3 77,1% > m2 75,4%. Reboots acumulados: 15.

## Ciclo 2026-07-10 01:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·163 | 1.064 | 23 | 1.087 | 1.386 | 78,4 % |
| exp_01 | Up | 462·462·159 | 1.050 | 33 | 1.083 | 1.386 | 78,1 % |
| exp_02 | Up | 462·462·162 | 1.057 | 29 | 1.086 | 1.386 | 78,4 % |
| exp_03 | Up | 462·462·164 | 1.067 | 21 | 1.088 | 1.386 | 78,5 % |
| **total** | — | 1.848·1.848·648 | **4.238** | **106** | **4.344** | **5.544** | **78,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.030 | 35 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.039 | 29 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.024 | 41 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 953 | 28 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.046** | **133** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·138 | 1.036 | 26 | 1.062 | 1.386 | 76,6 % |
| exp_01 | Up | 462·462·160 | 1.043 | 41 | 1.084 | 1.386 | 78,2 % |
| exp_02 | Up | 462·462·155 | 1.023 | 56 | 1.079 | 1.386 | 77,8 % |
| exp_03 | Up | 429·429·156 | 990 | 24 | 1.014 | 1.287 | 78,8 % |
| **total** | — | 1.815·1.815·609 | **4.092** | **147** | **4.239** | **5.445** | **77,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·288 | 1.083 | 63 | 1.146 | 1.287 | 89,0 % |
| exp_01 | Up | 429·429·266 | 1.093 | 31 | 1.124 | 1.287 | 87,3 % |
| exp_02 | Up | 429·429·287 | 1.096 | 49 | 1.145 | 1.287 | 89,0 % |
| exp_03 | Up | 429·429·274 | 1.086 | 46 | 1.132 | 1.287 | 88,0 % |
| **total** | — | 1.716·1.716·1.115 | **4.358** | **189** | **4.547** | **5.148** | **88,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·648 | 4.238 | 106 | 4.344 | 5.544 | 78,4 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.046 | 133 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·609 | 4.092 | 147 | 4.239 | 5.445 | 77,9 % |
| m4 | RUNNING | 1.716·1.716·1.115 | 4.358 | 189 | 4.547 | 5.148 | 88,3 % |
| **TOTAL** | — | — | **16.734** | **575** | **17.309** | **21.681** | **79,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:102, install/adb:4
- m2: erros → emulator/boot:112, install/adb:21
- m3: erros → emulator/boot:123, install/adb:24
- m4: erros → emulator/boot:161, install/adb:28

## Ciclo 2026-07-10 01:01:51 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·163 | 1.064 | 23 | 1.087 | 1.386 | 78,4 % |
| exp_01 | Up | 462·462·159 | 1.050 | 33 | 1.083 | 1.386 | 78,1 % |
| exp_02 | Up | 462·462·163 | 1.058 | 29 | 1.087 | 1.386 | 78,4 % |
| exp_03 | Up | 462·462·165 | 1.068 | 21 | 1.089 | 1.386 | 78,6 % |
| **total** | — | 1.848·1.848·650 | **4.240** | **106** | **4.346** | **5.544** | **78,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·141 | 1.030 | 35 | 1.065 | 1.386 | 76,8 % |
| exp_01 | Up | 462·462·144 | 1.040 | 28 | 1.068 | 1.386 | 77,1 % |
| exp_02 | Up | 462·462·141 | 1.024 | 41 | 1.065 | 1.386 | 76,8 % |
| exp_03 | Up | 462·462·57 | 953 | 28 | 981 | 1.386 | 70,8 % |
| **total** | — | 1.848·1.848·483 | **4.047** | **132** | **4.179** | **5.544** | **75,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·139 | 1.037 | 26 | 1.063 | 1.386 | 76,7 % |
| exp_01 | Up | 462·462·160 | 1.043 | 41 | 1.084 | 1.386 | 78,2 % |
| exp_02 | Up | 462·462·156 | 1.024 | 56 | 1.080 | 1.386 | 77,9 % |
| exp_03 | Up | 429·429·156 | 990 | 24 | 1.014 | 1.287 | 78,8 % |
| **total** | — | 1.815·1.815·611 | **4.094** | **147** | **4.241** | **5.445** | **77,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·288 | 1.083 | 63 | 1.146 | 1.287 | 89,0 % |
| exp_01 | Up | 429·429·266 | 1.093 | 31 | 1.124 | 1.287 | 87,3 % |
| exp_02 | Up | 429·429·288 | 1.097 | 49 | 1.146 | 1.287 | 89,0 % |
| exp_03 | Up | 429·429·274 | 1.086 | 46 | 1.132 | 1.287 | 88,0 % |
| **total** | — | 1.716·1.716·1.116 | **4.359** | **189** | **4.548** | **5.148** | **88,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·650 | 4.240 | 106 | 4.346 | 5.544 | 78,4 % |
| m2 | RUNNING | 1.848·1.848·483 | 4.047 | 132 | 4.179 | 5.544 | 75,4 % |
| m3 | RUNNING | 1.815·1.815·611 | 4.094 | 147 | 4.241 | 5.445 | 77,9 % |
| m4 | RUNNING | 1.716·1.716·1.116 | 4.359 | 189 | 4.548 | 5.148 | 88,3 % |
| **TOTAL** | — | — | **16.740** | **574** | **17.314** | **21.681** | **79,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:102, install/adb:4
- m2: erros → emulator/boot:112, install/adb:20
- m3: erros → emulator/boot:123, install/adb:24
- m4: erros → emulator/boot:161, install/adb:28

**Ações (01:01 local):** Ciclo de rotina, sem incidentes. Cron local ativo (01:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1 (normal). Nenhuma ação manual. ✅ m1 E m2 AMBOS na passada 300 (RV_TIMEOUTS=300) — re-caminhadas pós-reboots #14/#15 concluídas. m1 voltou a avançar (done 4.311→4.346, 300-pass 615→650); m2 re-alcançou a 300 (done ainda 4.179, vai subir). Total 17.314/21.681 = 79,9% (+122 vs 00:02 — melhor delta em horas: m4 +45, m3 +42, m1 +35). Cluster saudável e acelerando. Ordem: m4 88,3% > m1 78,4% > m3 77,9% > m2 75,4%. Reboots acumulados: 15.

## Ciclo 2026-07-10 02:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·173 | 1.072 | 25 | 1.097 | 1.386 | 79,1 % |
| exp_01 | Up | 462·462·170 | 1.058 | 36 | 1.094 | 1.386 | 78,9 % |
| exp_02 | Up | 462·462·174 | 1.066 | 32 | 1.098 | 1.386 | 79,2 % |
| exp_03 | Up | 462·462·176 | 1.076 | 24 | 1.100 | 1.386 | 79,4 % |
| **total** | — | 1.848·1.848·693 | **4.272** | **117** | **4.389** | **5.544** | **79,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·143 | 1.036 | 31 | 1.067 | 1.386 | 77,0 % |
| exp_01 | Up | 462·462·147 | 1.044 | 27 | 1.071 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·66 | 963 | 27 | 990 | 1.386 | 71,4 % |
| **total** | — | 1.848·1.848·502 | **4.074** | **124** | **4.198** | **5.544** | **75,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·148 | 1.046 | 26 | 1.072 | 1.386 | 77,3 % |
| exp_01 | Up | 462·462·170 | 1.051 | 43 | 1.094 | 1.386 | 78,9 % |
| exp_02 | Up | 462·462·164 | 1.032 | 56 | 1.088 | 1.386 | 78,5 % |
| exp_03 | Up | 429·429·164 | 998 | 24 | 1.022 | 1.287 | 79,4 % |
| **total** | — | 1.815·1.815·646 | **4.127** | **149** | **4.276** | **5.445** | **78,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·301 | 1.091 | 68 | 1.159 | 1.287 | 90,1 % |
| exp_01 | Up | 429·429·275 | 1.101 | 32 | 1.133 | 1.287 | 88,0 % |
| exp_02 | Up | 429·429·297 | 1.106 | 49 | 1.155 | 1.287 | 89,7 % |
| exp_03 | Up | 429·429·284 | 1.096 | 46 | 1.142 | 1.287 | 88,7 % |
| **total** | — | 1.716·1.716·1.157 | **4.394** | **195** | **4.589** | **5.148** | **89,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·693 | 4.272 | 117 | 4.389 | 5.544 | 79,2 % |
| m2 | RUNNING | 1.848·1.848·502 | 4.074 | 124 | 4.198 | 5.544 | 75,7 % |
| m3 | RUNNING | 1.815·1.815·646 | 4.127 | 149 | 4.276 | 5.445 | 78,5 % |
| m4 | RUNNING | 1.716·1.716·1.157 | 4.394 | 195 | 4.589 | 5.148 | 89,1 % |
| **TOTAL** | — | — | **16.867** | **585** | **17.452** | **21.681** | **80,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:112, install/adb:5
- m2: erros → emulator/boot:111, install/adb:13
- m3: erros → emulator/boot:125, install/adb:24
- m4: erros → emulator/boot:164, install/adb:31

## Ciclo 2026-07-10 02:01:34 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·173 | 1.072 | 25 | 1.097 | 1.386 | 79,1 % |
| exp_01 | Up | 462·462·171 | 1.059 | 36 | 1.095 | 1.386 | 79,0 % |
| exp_02 | Up | 462·462·174 | 1.066 | 32 | 1.098 | 1.386 | 79,2 % |
| exp_03 | Up | 462·462·176 | 1.076 | 24 | 1.100 | 1.386 | 79,4 % |
| **total** | — | 1.848·1.848·694 | **4.273** | **117** | **4.390** | **5.544** | **79,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·144 | 1.037 | 31 | 1.068 | 1.386 | 77,1 % |
| exp_01 | Up | 462·462·147 | 1.044 | 27 | 1.071 | 1.386 | 77,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·66 | 963 | 27 | 990 | 1.386 | 71,4 % |
| **total** | — | 1.848·1.848·503 | **4.075** | **124** | **4.199** | **5.544** | **75,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·148 | 1.046 | 26 | 1.072 | 1.386 | 77,3 % |
| exp_01 | Up | 462·462·170 | 1.051 | 43 | 1.094 | 1.386 | 78,9 % |
| exp_02 | Up | 462·462·165 | 1.033 | 56 | 1.089 | 1.386 | 78,6 % |
| exp_03 | Up | 429·429·165 | 999 | 24 | 1.023 | 1.287 | 79,5 % |
| **total** | — | 1.815·1.815·648 | **4.129** | **149** | **4.278** | **5.445** | **78,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·301 | 1.091 | 68 | 1.159 | 1.287 | 90,1 % |
| exp_01 | Up | 429·429·276 | 1.102 | 32 | 1.134 | 1.287 | 88,1 % |
| exp_02 | Up | 429·429·298 | 1.106 | 50 | 1.156 | 1.287 | 89,8 % |
| exp_03 | Up | 429·429·284 | 1.096 | 46 | 1.142 | 1.287 | 88,7 % |
| **total** | — | 1.716·1.716·1.159 | **4.395** | **196** | **4.591** | **5.148** | **89,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·694 | 4.273 | 117 | 4.390 | 5.544 | 79,2 % |
| m2 | RUNNING | 1.848·1.848·503 | 4.075 | 124 | 4.199 | 5.544 | 75,7 % |
| m3 | RUNNING | 1.815·1.815·648 | 4.129 | 149 | 4.278 | 5.445 | 78,6 % |
| m4 | RUNNING | 1.716·1.716·1.159 | 4.395 | 196 | 4.591 | 5.148 | 89,2 % |
| **TOTAL** | — | — | **16.872** | **586** | **17.458** | **21.681** | **80,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:112, install/adb:5
- m2: erros → emulator/boot:111, install/adb:13
- m3: erros → emulator/boot:125, install/adb:24
- m4: erros → emulator/boot:165, install/adb:31

**Ações (02:01 local):** Ciclo de rotina, sem incidentes. Cron local ativo (02:00 registrado, 4 VMs RUNNING subindo). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1, containers estáveis (sem OOM recente). Nenhuma ação manual. Total 17.458/21.681 = 80,5% (+144 vs 01:01 — todas avançando: m1 +44, m4 +43, m3 +37, m2 +20). ✅ m2 voltou a subir (300-pass 483→503, done 4.179→4.199) — re-caminhada totalmente absorvida. Cluster saudável e em ritmo bom. Ordem: m4 89,2% > m1 79,2% > m3 78,6% > m2 75,7%. Reboots acumulados: 15.

## Ciclo 2026-07-10 03:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·184 | 1.083 | 25 | 1.108 | 1.386 | 79,9 % |
| exp_01 | Up | 462·462·180 | 1.068 | 36 | 1.104 | 1.386 | 79,7 % |
| exp_02 | Up | 462·462·183 | 1.075 | 32 | 1.107 | 1.386 | 79,9 % |
| exp_03 | Up | 462·462·186 | 1.086 | 24 | 1.110 | 1.386 | 80,1 % |
| **total** | — | 1.848·1.848·733 | **4.312** | **117** | **4.429** | **5.544** | **79,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·153 | 1.046 | 31 | 1.077 | 1.386 | 77,7 % |
| exp_01 | Up | 462·462·157 | 1.054 | 27 | 1.081 | 1.386 | 78,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·79 | 973 | 30 | 1.003 | 1.386 | 72,4 % |
| **total** | — | 1.848·1.848·535 | **4.104** | **127** | **4.231** | **5.544** | **76,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·156 | 1.054 | 26 | 1.080 | 1.386 | 77,9 % |
| exp_01 | Up | 462·462·177 | 1.058 | 43 | 1.101 | 1.386 | 79,4 % |
| exp_02 | Up | 462·462·165 | 1.034 | 55 | 1.089 | 1.386 | 78,6 % |
| exp_03 | Up | 429·429·174 | 1.006 | 26 | 1.032 | 1.287 | 80,2 % |
| **total** | — | 1.815·1.815·672 | **4.152** | **150** | **4.302** | **5.445** | **79,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·311 | 1.101 | 68 | 1.169 | 1.287 | 90,8 % |
| exp_01 | Up | 429·429·285 | 1.111 | 32 | 1.143 | 1.287 | 88,8 % |
| exp_02 | Up | 429·429·309 | 1.114 | 53 | 1.167 | 1.287 | 90,7 % |
| exp_03 | Up | 429·429·294 | 1.105 | 47 | 1.152 | 1.287 | 89,5 % |
| **total** | — | 1.716·1.716·1.199 | **4.431** | **200** | **4.631** | **5.148** | **90,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·733 | 4.312 | 117 | 4.429 | 5.544 | 79,9 % |
| m2 | RUNNING | 1.848·1.848·535 | 4.104 | 127 | 4.231 | 5.544 | 76,3 % |
| m3 | RUNNING | 1.815·1.815·672 | 4.152 | 150 | 4.302 | 5.445 | 79,0 % |
| m4 | RUNNING | 1.716·1.716·1.199 | 4.431 | 200 | 4.631 | 5.148 | 90,0 % |
| **TOTAL** | — | — | **16.999** | **594** | **17.593** | **21.681** | **81,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:112, install/adb:5
- m2: erros → emulator/boot:114, install/adb:13
- m3: erros → emulator/boot:126, install/adb:24
- m4: erros → emulator/boot:166, install/adb:34

## Ciclo 2026-07-10 03:01:37 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·185 | 1.084 | 25 | 1.109 | 1.386 | 80,0 % |
| exp_01 | Up | 462·462·180 | 1.068 | 36 | 1.104 | 1.386 | 79,7 % |
| exp_02 | Up | 462·462·184 | 1.076 | 32 | 1.108 | 1.386 | 79,9 % |
| exp_03 | Up | 462·462·186 | 1.086 | 24 | 1.110 | 1.386 | 80,1 % |
| **total** | — | 1.848·1.848·735 | **4.314** | **117** | **4.431** | **5.544** | **79,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·153 | 1.046 | 31 | 1.077 | 1.386 | 77,7 % |
| exp_01 | Up | 462·462·157 | 1.054 | 27 | 1.081 | 1.386 | 78,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·80 | 974 | 30 | 1.004 | 1.386 | 72,4 % |
| **total** | — | 1.848·1.848·536 | **4.105** | **127** | **4.232** | **5.544** | **76,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·156 | 1.054 | 26 | 1.080 | 1.386 | 77,9 % |
| exp_01 | Up | 462·462·178 | 1.059 | 43 | 1.102 | 1.386 | 79,5 % |
| exp_02 | Up | 462·462·165 | 1.034 | 55 | 1.089 | 1.386 | 78,6 % |
| exp_03 | Up | 429·429·174 | 1.006 | 26 | 1.032 | 1.287 | 80,2 % |
| **total** | — | 1.815·1.815·673 | **4.153** | **150** | **4.303** | **5.445** | **79,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·311 | 1.101 | 68 | 1.169 | 1.287 | 90,8 % |
| exp_01 | Up | 429·429·285 | 1.111 | 32 | 1.143 | 1.287 | 88,8 % |
| exp_02 | Up | 429·429·310 | 1.115 | 53 | 1.168 | 1.287 | 90,8 % |
| exp_03 | Up | 429·429·294 | 1.105 | 47 | 1.152 | 1.287 | 89,5 % |
| **total** | — | 1.716·1.716·1.200 | **4.432** | **200** | **4.632** | **5.148** | **90,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·735 | 4.314 | 117 | 4.431 | 5.544 | 79,9 % |
| m2 | RUNNING | 1.848·1.848·536 | 4.105 | 127 | 4.232 | 5.544 | 76,3 % |
| m3 | RUNNING | 1.815·1.815·673 | 4.153 | 150 | 4.303 | 5.445 | 79,0 % |
| m4 | RUNNING | 1.716·1.716·1.200 | 4.432 | 200 | 4.632 | 5.148 | 90,0 % |
| **TOTAL** | — | — | **17.004** | **594** | **17.598** | **21.681** | **81,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:112, install/adb:5
- m2: erros → emulator/boot:114, install/adb:13
- m3: erros → emulator/boot:126, install/adb:24
- m4: erros → emulator/boot:166, install/adb:34

**Ações (03:01 local):** Ciclo de rotina, sem incidentes. Cron local ativo (03:00 registrado, 4 VMs RUNNING subindo). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1, containers MUITO estáveis (m1/m2 Up 4h/3h sem OOM, m4 Up 30h). Nenhuma ação manual. Total 17.598/21.681 = 81,2% (+140 vs 02:01 — m4 +41, m1 +41, m2 +33, m3 +25). m4 atingiu 90,0%. Cluster totalmente saudável, ritmo estável ~+140/h. Ordem: m4 90,0% > m1 79,9% > m3 79,0% > m2 76,3%. Reboots acumulados: 15.

## Ciclo 2026-07-10 04:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·194 | 1.093 | 25 | 1.118 | 1.386 | 80,7 % |
| exp_01 | Up | 462·462·190 | 1.078 | 36 | 1.114 | 1.386 | 80,4 % |
| exp_02 | Up | 462·462·194 | 1.085 | 33 | 1.118 | 1.386 | 80,7 % |
| exp_03 | Up | 462·462·199 | 1.095 | 28 | 1.123 | 1.386 | 81,0 % |
| **total** | — | 1.848·1.848·777 | **4.351** | **122** | **4.473** | **5.544** | **80,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·163 | 1.056 | 31 | 1.087 | 1.386 | 78,4 % |
| exp_01 | Up | 462·462·168 | 1.062 | 30 | 1.092 | 1.386 | 78,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·89 | 983 | 30 | 1.013 | 1.386 | 73,1 % |
| **total** | — | 1.848·1.848·566 | **4.132** | **130** | **4.262** | **5.544** | **76,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·167 | 1.063 | 28 | 1.091 | 1.386 | 78,7 % |
| exp_01 | Up | 462·462·187 | 1.068 | 43 | 1.111 | 1.386 | 80,2 % |
| exp_02 | Up | 462·462·173 | 1.041 | 56 | 1.097 | 1.386 | 79,1 % |
| exp_03 | Up | 429·429·185 | 1.016 | 27 | 1.043 | 1.287 | 81,0 % |
| **total** | — | 1.815·1.815·712 | **4.188** | **154** | **4.342** | **5.445** | **79,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·319 | 1.109 | 68 | 1.177 | 1.287 | 91,5 % |
| exp_01 | Up | 429·429·294 | 1.119 | 33 | 1.152 | 1.287 | 89,5 % |
| exp_02 | Up | 429·429·318 | 1.122 | 54 | 1.176 | 1.287 | 91,4 % |
| exp_03 | Up | 429·429·303 | 1.112 | 49 | 1.161 | 1.287 | 90,2 % |
| **total** | — | 1.716·1.716·1.234 | **4.462** | **204** | **4.666** | **5.148** | **90,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·777 | 4.351 | 122 | 4.473 | 5.544 | 80,7 % |
| m2 | RUNNING | 1.848·1.848·566 | 4.132 | 130 | 4.262 | 5.544 | 76,9 % |
| m3 | RUNNING | 1.815·1.815·712 | 4.188 | 154 | 4.342 | 5.445 | 79,7 % |
| m4 | RUNNING | 1.716·1.716·1.234 | 4.462 | 204 | 4.666 | 5.148 | 90,6 % |
| **TOTAL** | — | — | **17.133** | **610** | **17.743** | **21.681** | **81,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:113, install/adb:9
- m2: erros → emulator/boot:117, install/adb:13
- m3: erros → emulator/boot:131, install/adb:23
- m4: erros → emulator/boot:169, install/adb:35

## Ciclo 2026-07-10 04:01:44 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·194 | 1.093 | 25 | 1.118 | 1.386 | 80,7 % |
| exp_01 | Up | 462·462·190 | 1.078 | 36 | 1.114 | 1.386 | 80,4 % |
| exp_02 | Up | 462·462·194 | 1.085 | 33 | 1.118 | 1.386 | 80,7 % |
| exp_03 | Up | 462·462·199 | 1.095 | 28 | 1.123 | 1.386 | 81,0 % |
| **total** | — | 1.848·1.848·777 | **4.351** | **122** | **4.473** | **5.544** | **80,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·163 | 1.056 | 31 | 1.087 | 1.386 | 78,4 % |
| exp_01 | Up | 462·462·168 | 1.062 | 30 | 1.092 | 1.386 | 78,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·89 | 983 | 30 | 1.013 | 1.386 | 73,1 % |
| **total** | — | 1.848·1.848·566 | **4.132** | **130** | **4.262** | **5.544** | **76,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·168 | 1.063 | 29 | 1.092 | 1.386 | 78,8 % |
| exp_01 | Up | 462·462·187 | 1.068 | 43 | 1.111 | 1.386 | 80,2 % |
| exp_02 | Up | 462·462·174 | 1.042 | 56 | 1.098 | 1.386 | 79,2 % |
| exp_03 | Up | 429·429·185 | 1.016 | 27 | 1.043 | 1.287 | 81,0 % |
| **total** | — | 1.815·1.815·714 | **4.189** | **155** | **4.344** | **5.445** | **79,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·319 | 1.109 | 68 | 1.177 | 1.287 | 91,5 % |
| exp_01 | Up | 429·429·294 | 1.119 | 33 | 1.152 | 1.287 | 89,5 % |
| exp_02 | Up | 429·429·318 | 1.122 | 54 | 1.176 | 1.287 | 91,4 % |
| exp_03 | Up | 429·429·303 | 1.112 | 49 | 1.161 | 1.287 | 90,2 % |
| **total** | — | 1.716·1.716·1.234 | **4.462** | **204** | **4.666** | **5.148** | **90,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·777 | 4.351 | 122 | 4.473 | 5.544 | 80,7 % |
| m2 | RUNNING | 1.848·1.848·566 | 4.132 | 130 | 4.262 | 5.544 | 76,9 % |
| m3 | RUNNING | 1.815·1.815·714 | 4.189 | 155 | 4.344 | 5.445 | 79,8 % |
| m4 | RUNNING | 1.716·1.716·1.234 | 4.462 | 204 | 4.666 | 5.148 | 90,6 % |
| **TOTAL** | — | — | **17.134** | **611** | **17.745** | **21.681** | **81,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:113, install/adb:9
- m2: erros → emulator/boot:117, install/adb:13
- m3: erros → emulator/boot:132, install/adb:23
- m4: erros → emulator/boot:169, install/adb:35

**Ações (04:01 local):** Ciclo de rotina, sem incidentes. Cron local ativo (04:00 registrado, 4 VMs RUNNING subindo). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1, containers muito estáveis (m1 Up 5h, m2 Up 4h sem OOM, m4 Up 31h). Nenhuma ação manual. Total 17.745/21.681 = 81,8% (+147 vs 03:01 — m1 +42, m3 +41, m4 +34, m2 +30). Cluster totalmente saudável, ritmo estável ~+140-147/h. Ordem: m4 90,6% > m1 80,7% > m3 79,8% > m2 76,9%. Reboots acumulados: 15.

## Ciclo 2026-07-10 05:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·206 | 1.102 | 28 | 1.130 | 1.386 | 81,5 % |
| exp_01 | Up | 462·462·201 | 1.086 | 39 | 1.125 | 1.386 | 81,2 % |
| exp_02 | Up | 462·462·205 | 1.093 | 36 | 1.129 | 1.386 | 81,5 % |
| exp_03 | Up | 462·462·209 | 1.103 | 30 | 1.133 | 1.386 | 81,7 % |
| **total** | — | 1.848·1.848·821 | **4.384** | **133** | **4.517** | **5.544** | **81,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·173 | 1.063 | 34 | 1.097 | 1.386 | 79,1 % |
| exp_01 | Up | 462·462·178 | 1.072 | 30 | 1.102 | 1.386 | 79,5 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·99 | 993 | 30 | 1.023 | 1.386 | 73,8 % |
| **total** | — | 1.848·1.848·596 | **4.159** | **133** | **4.292** | **5.544** | **77,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·178 | 1.072 | 30 | 1.102 | 1.386 | 79,5 % |
| exp_01 | Up | 462·462·196 | 1.077 | 43 | 1.120 | 1.386 | 80,8 % |
| exp_02 | Up | 462·462·184 | 1.051 | 57 | 1.108 | 1.386 | 79,9 % |
| exp_03 | Up | 429·429·195 | 1.025 | 28 | 1.053 | 1.287 | 81,8 % |
| **total** | — | 1.815·1.815·753 | **4.225** | **158** | **4.383** | **5.445** | **80,5 %** |

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·821 | 4.384 | 133 | 4.517 | 5.544 | 81,5 % |
| m2 | RUNNING | 1.848·1.848·596 | 4.159 | 133 | 4.292 | 5.544 | 77,4 % |
| m3 | RUNNING | 1.815·1.815·753 | 4.225 | 158 | 4.383 | 5.445 | 80,5 % |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **12.768** | **424** | **13.192** | **16.533** | **79,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:10
- m2: erros → emulator/boot:120, install/adb:13
- m3: erros → emulator/boot:132, install/adb:26
- m4: SSH inacessível — ssh timeout (sem ação)

## Ciclo 2026-07-10 05:05:32 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·207 | 1.103 | 28 | 1.131 | 1.386 | 81,6 % |
| exp_01 | Up | 462·462·201 | 1.086 | 39 | 1.125 | 1.386 | 81,2 % |
| exp_02 | Up | 462·462·206 | 1.094 | 36 | 1.130 | 1.386 | 81,5 % |
| exp_03 | Up | 462·462·209 | 1.103 | 30 | 1.133 | 1.386 | 81,7 % |
| **total** | — | 1.848·1.848·823 | **4.386** | **133** | **4.519** | **5.544** | **81,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·174 | 1.064 | 34 | 1.098 | 1.386 | 79,2 % |
| exp_01 | Up | 462·462·179 | 1.073 | 30 | 1.103 | 1.386 | 79,6 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·101 | 993 | 32 | 1.025 | 1.386 | 74,0 % |
| **total** | — | 1.848·1.848·600 | **4.161** | **135** | **4.296** | **5.544** | **77,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·179 | 1.073 | 30 | 1.103 | 1.386 | 79,6 % |
| exp_01 | Up | 462·462·197 | 1.078 | 43 | 1.121 | 1.386 | 80,9 % |
| exp_02 | Up | 462·462·185 | 1.052 | 57 | 1.109 | 1.386 | 80,0 % |
| exp_03 | Up | 429·429·196 | 1.026 | 28 | 1.054 | 1.287 | 81,9 % |
| **total** | — | 1.815·1.815·757 | **4.229** | **158** | **4.387** | **5.445** | **80,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.113 | 68 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.122 | 35 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.126 | 54 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.116 | 49 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.477** | **206** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·823 | 4.386 | 133 | 4.519 | 5.544 | 81,5 % |
| m2 | RUNNING | 1.848·1.848·600 | 4.161 | 135 | 4.296 | 5.544 | 77,5 % |
| m3 | RUNNING | 1.815·1.815·757 | 4.229 | 158 | 4.387 | 5.445 | 80,6 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.477 | 206 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.253** | **632** | **17.885** | **21.681** | **82,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:10
- m2: erros → emulator/boot:122, install/adb:13
- m3: erros → emulator/boot:132, install/adb:26
- m4: erros → emulator/boot:170, install/adb:36

**Ações (05:05 local):** ⚠️ INCIDENTE — m4 banner-timeout (PRIMEIRO da m4; entrada 05:00 do cron.out AUSENTE = cron travou no SSH da m4 morta). m4 era a mais saudável (Up 31h, líder 90,6%) → padrão de cluster agora atingiu AS 4 VMs. Varredura SSH: m1/m2/m3 RUNNING 5/5 Up; m4 SSH_FALHOU. Confirmado m4 RUNNING no gcloud + 3 retentativas SSH (20→30→40) banner-timeout → m4 travada de verdade → **reboot #16** (08:04 UTC / 05:04 local). SSH ~20s (up 0 min). Exited(255)+run morto → RESUME → 5/5 Up + run_reais=1 (05:05 local). Dados íntegros (done m4 4.666→4.683). Total 17.885/21.681 = 82,5% (+140 vs 04:01). NOTA: 1º health_check pegou m4 durante reboot (SSH_FALHOU/parcial); 2º (05:05) correto. Ordem: m4 91,0% > m1 81,5% > m3 80,6% > m2 77,5%. Reboots acumulados: **16**.

## Marco — reboot #16 (m4 banner-timeout) 2026-07-10 ~08:04 UTC / 05:04 local
PRIMEIRO banner-timeout da m4, que era a única VM nunca rebootada (Up 31h). Confirma que o banner-timeout sob pressão de memória é padrão de CLUSTER, não de VM específica — todas as 4 já passaram por ele. Tratamento padrão (reset→SSH~20s→RESUME→5/5 Up + run vivo), dados íntegros. m4 vai re-caminhar 60→180→300 pós-reboot (flat esperado ~1-3h), mas por ser a líder (91%) o impacto é menor.

## Ciclo 2026-07-10 06:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·215 | 1.111 | 28 | 1.139 | 1.386 | 82,2 % |
| exp_01 | Up | 462·462·210 | 1.095 | 39 | 1.134 | 1.386 | 81,8 % |
| exp_02 | Up | 462·462·215 | 1.102 | 37 | 1.139 | 1.386 | 82,2 % |
| exp_03 | Up | 462·462·219 | 1.112 | 31 | 1.143 | 1.386 | 82,5 % |
| **total** | — | 1.848·1.848·859 | **4.420** | **135** | **4.555** | **5.544** | **82,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·184 | 1.074 | 34 | 1.108 | 1.386 | 79,9 % |
| exp_01 | Up | 462·462·188 | 1.081 | 31 | 1.112 | 1.386 | 80,2 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·110 | 1.001 | 33 | 1.034 | 1.386 | 74,6 % |
| **total** | — | 1.848·1.848·628 | **4.187** | **137** | **4.324** | **5.544** | **78,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·188 | 1.081 | 31 | 1.112 | 1.386 | 80,2 % |
| exp_01 | Up | 462·462·208 | 1.085 | 47 | 1.132 | 1.386 | 81,7 % |
| exp_02 | Up | 462·462·193 | 1.060 | 57 | 1.117 | 1.386 | 80,6 % |
| exp_03 | Up | 429·429·201 | 1.029 | 30 | 1.059 | 1.287 | 82,3 % |
| **total** | — | 1.815·1.815·790 | **4.255** | **165** | **4.420** | **5.445** | **81,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.114 | 67 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.126 | 31 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.126 | 54 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.120 | 45 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.486** | **197** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·859 | 4.420 | 135 | 4.555 | 5.544 | 82,2 % |
| m2 | RUNNING | 1.848·1.848·628 | 4.187 | 137 | 4.324 | 5.544 | 78,0 % |
| m3 | RUNNING | 1.815·1.815·790 | 4.255 | 165 | 4.420 | 5.445 | 81,2 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.486 | 197 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.348** | **634** | **17.982** | **21.681** | **82,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:12
- m2: erros → emulator/boot:124, install/adb:13
- m3: erros → emulator/boot:137, install/adb:28
- m4: erros → emulator/boot:162, install/adb:35

## Ciclo 2026-07-10 06:02:52 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·216 | 1.112 | 28 | 1.140 | 1.386 | 82,3 % |
| exp_01 | Up | 462·462·210 | 1.095 | 39 | 1.134 | 1.386 | 81,8 % |
| exp_02 | Up | 462·462·216 | 1.103 | 37 | 1.140 | 1.386 | 82,3 % |
| exp_03 | Up | 462·462·219 | 1.112 | 31 | 1.143 | 1.386 | 82,5 % |
| **total** | — | 1.848·1.848·861 | **4.422** | **135** | **4.557** | **5.544** | **82,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·184 | 1.074 | 34 | 1.108 | 1.386 | 79,9 % |
| exp_01 | Up | 462·462·189 | 1.082 | 31 | 1.113 | 1.386 | 80,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·111 | 1.002 | 33 | 1.035 | 1.386 | 74,7 % |
| **total** | — | 1.848·1.848·630 | **4.189** | **137** | **4.326** | **5.544** | **78,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·188 | 1.081 | 31 | 1.112 | 1.386 | 80,2 % |
| exp_01 | Up | 462·462·209 | 1.086 | 47 | 1.133 | 1.386 | 81,7 % |
| exp_02 | Up | 462·462·193 | 1.060 | 57 | 1.117 | 1.386 | 80,6 % |
| exp_03 | Up | 429·429·201 | 1.030 | 29 | 1.059 | 1.287 | 82,3 % |
| **total** | — | 1.815·1.815·791 | **4.257** | **164** | **4.421** | **5.445** | **81,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.114 | 67 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.126 | 31 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.126 | 54 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.120 | 45 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.486** | **197** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·861 | 4.422 | 135 | 4.557 | 5.544 | 82,2 % |
| m2 | RUNNING | 1.848·1.848·630 | 4.189 | 137 | 4.326 | 5.544 | 78,0 % |
| m3 | RUNNING | 1.815·1.815·791 | 4.257 | 164 | 4.421 | 5.445 | 81,2 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.486 | 197 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.354** | **633** | **17.987** | **21.681** | **83,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:12
- m2: erros → emulator/boot:124, install/adb:13
- m3: erros → emulator/boot:137, install/adb:27
- m4: erros → emulator/boot:162, install/adb:35

**Ações (06:02 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (06:00 registrado, 4 VMs RUNNING; 05:00 apareceu tarde com m4:SSH_FALHOU, cron completou após reboot). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1. Nenhuma ação manual. Total 17.987/21.681 = 83,0% (+102 vs 05:05). m4 FLAT (done 4.683) = re-caminhando a passada 180 (RV_TIMEOUTS=180 confirmado) pós-reboot #16 — esperado, NÃO rebootar. m1/m2/m3 avançando bem (m1 +38, m3 +34, m2 +30). Ordem: m4 91,0% > m1 82,2% > m3 81,2% > m2 78,0%. Reboots acumulados: 16.

## Ciclo 2026-07-10 07:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·225 | 1.120 | 29 | 1.149 | 1.386 | 82,9 % |
| exp_01 | Up | 462·462·219 | 1.104 | 39 | 1.143 | 1.386 | 82,5 % |
| exp_02 | Up | 462·462·225 | 1.112 | 37 | 1.149 | 1.386 | 82,9 % |
| exp_03 | Up | 462·462·230 | 1.123 | 31 | 1.154 | 1.386 | 83,3 % |
| **total** | — | 1.848·1.848·899 | **4.459** | **136** | **4.595** | **5.544** | **82,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·193 | 1.083 | 34 | 1.117 | 1.386 | 80,6 % |
| exp_01 | Up | 462·462·200 | 1.091 | 33 | 1.124 | 1.386 | 81,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·121 | 1.011 | 34 | 1.045 | 1.386 | 75,4 % |
| **total** | — | 1.848·1.848·660 | **4.216** | **140** | **4.356** | **5.544** | **78,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·199 | 1.090 | 33 | 1.123 | 1.386 | 81,0 % |
| exp_01 | Up | 462·462·211 | 1.091 | 44 | 1.135 | 1.386 | 81,9 % |
| exp_02 | Up | 462·462·205 | 1.068 | 61 | 1.129 | 1.386 | 81,5 % |
| exp_03 | Up | 429·429·201 | 1.034 | 25 | 1.059 | 1.287 | 82,3 % |
| **total** | — | 1.815·1.815·816 | **4.283** | **163** | **4.446** | **5.445** | **81,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.117 | 64 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.126 | 31 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.129 | 51 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.124 | 41 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.496** | **187** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·899 | 4.459 | 136 | 4.595 | 5.544 | 82,9 % |
| m2 | RUNNING | 1.848·1.848·660 | 4.216 | 140 | 4.356 | 5.544 | 78,6 % |
| m3 | RUNNING | 1.815·1.815·816 | 4.283 | 163 | 4.446 | 5.445 | 81,7 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.496 | 187 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.454** | **626** | **18.080** | **21.681** | **83,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:13
- m2: erros → emulator/boot:125, install/adb:15
- m3: erros → emulator/boot:140, install/adb:23
- m4: erros → emulator/boot:154, install/adb:33

## Ciclo 2026-07-10 07:01:40 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·225 | 1.120 | 29 | 1.149 | 1.386 | 82,9 % |
| exp_01 | Up | 462·462·219 | 1.104 | 39 | 1.143 | 1.386 | 82,5 % |
| exp_02 | Up | 462·462·225 | 1.112 | 37 | 1.149 | 1.386 | 82,9 % |
| exp_03 | Up | 462·462·230 | 1.123 | 31 | 1.154 | 1.386 | 83,3 % |
| **total** | — | 1.848·1.848·899 | **4.459** | **136** | **4.595** | **5.544** | **82,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·194 | 1.084 | 34 | 1.118 | 1.386 | 80,7 % |
| exp_01 | Up | 462·462·201 | 1.091 | 34 | 1.125 | 1.386 | 81,2 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·121 | 1.011 | 34 | 1.045 | 1.386 | 75,4 % |
| **total** | — | 1.848·1.848·662 | **4.217** | **141** | **4.358** | **5.544** | **78,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·199 | 1.090 | 33 | 1.123 | 1.386 | 81,0 % |
| exp_01 | Up | 462·462·211 | 1.092 | 43 | 1.135 | 1.386 | 81,9 % |
| exp_02 | Up | 462·462·205 | 1.068 | 61 | 1.129 | 1.386 | 81,5 % |
| exp_03 | Up | 429·429·201 | 1.034 | 25 | 1.059 | 1.287 | 82,3 % |
| **total** | — | 1.815·1.815·816 | **4.284** | **162** | **4.446** | **5.445** | **81,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.117 | 64 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.126 | 31 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.129 | 51 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.124 | 41 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.496** | **187** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·899 | 4.459 | 136 | 4.595 | 5.544 | 82,9 % |
| m2 | RUNNING | 1.848·1.848·662 | 4.217 | 141 | 4.358 | 5.544 | 78,6 % |
| m3 | RUNNING | 1.815·1.815·816 | 4.284 | 162 | 4.446 | 5.445 | 81,7 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.496 | 187 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.456** | **626** | **18.082** | **21.681** | **83,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:123, install/adb:13
- m2: erros → emulator/boot:126, install/adb:15
- m3: erros → emulator/boot:140, install/adb:22
- m4: erros → emulator/boot:154, install/adb:33

**Ações (07:01 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (07:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1. Nenhuma ação manual. Total 18.082/21.681 = 83,4% (+95 vs 06:02). m4 ainda FLAT (done 4.683) re-caminhando a passada 180 (~2h pós-reboot #16) — esperado, NÃO rebootar. m1/m2/m3 avançando (m1 +38, m3 +25, m2 +32). Ordem: m4 91,0% > m1 82,9% > m3 81,7% > m2 78,6%. Reboots acumulados: 16.

## Ciclo 2026-07-10 08:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·234 | 1.126 | 32 | 1.158 | 1.386 | 83,5 % |
| exp_01 | Up | 462·462·227 | 1.112 | 39 | 1.151 | 1.386 | 83,0 % |
| exp_02 | Up | 462·462·228 | 1.115 | 37 | 1.152 | 1.386 | 83,1 % |
| exp_03 | Up | 462·462·240 | 1.130 | 34 | 1.164 | 1.386 | 84,0 % |
| **total** | — | 1.848·1.848·929 | **4.483** | **142** | **4.625** | **5.544** | **83,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·203 | 1.091 | 36 | 1.127 | 1.386 | 81,3 % |
| exp_01 | Up | 462·462·210 | 1.100 | 34 | 1.134 | 1.386 | 81,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·130 | 1.020 | 34 | 1.054 | 1.386 | 76,0 % |
| **total** | — | 1.848·1.848·689 | **4.242** | **143** | **4.385** | **5.544** | **79,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·210 | 1.098 | 36 | 1.134 | 1.386 | 81,8 % |
| exp_01 | Up | 462·462·211 | 1.097 | 38 | 1.135 | 1.386 | 81,9 % |
| exp_02 | Up | 462·462·214 | 1.077 | 61 | 1.138 | 1.386 | 82,1 % |
| exp_03 | Up | 429·429·203 | 1.040 | 21 | 1.061 | 1.287 | 82,4 % |
| **total** | — | 1.815·1.815·838 | **4.312** | **156** | **4.468** | **5.445** | **82,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.119 | 62 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.129 | 28 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.130 | 50 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.125 | 40 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.503** | **180** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·929 | 4.483 | 142 | 4.625 | 5.544 | 83,4 % |
| m2 | RUNNING | 1.848·1.848·689 | 4.242 | 143 | 4.385 | 5.544 | 79,1 % |
| m3 | RUNNING | 1.815·1.815·838 | 4.312 | 156 | 4.468 | 5.445 | 82,1 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.503 | 180 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.540** | **621** | **18.161** | **21.681** | **83,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:128, install/adb:14
- m2: erros → emulator/boot:128, install/adb:15
- m3: erros → emulator/boot:142, install/adb:14
- m4: erros → emulator/boot:149, install/adb:31

## Ciclo 2026-07-10 08:01:46 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·234 | 1.126 | 32 | 1.158 | 1.386 | 83,5 % |
| exp_01 | Up | 462·462·227 | 1.112 | 39 | 1.151 | 1.386 | 83,0 % |
| exp_02 | Up | 462·462·228 | 1.115 | 37 | 1.152 | 1.386 | 83,1 % |
| exp_03 | Up | 462·462·240 | 1.130 | 34 | 1.164 | 1.386 | 84,0 % |
| **total** | — | 1.848·1.848·929 | **4.483** | **142** | **4.625** | **5.544** | **83,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·204 | 1.092 | 36 | 1.128 | 1.386 | 81,4 % |
| exp_01 | Up | 462·462·210 | 1.100 | 34 | 1.134 | 1.386 | 81,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·131 | 1.021 | 34 | 1.055 | 1.386 | 76,1 % |
| **total** | — | 1.848·1.848·691 | **4.244** | **143** | **4.387** | **5.544** | **79,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·210 | 1.098 | 36 | 1.134 | 1.386 | 81,8 % |
| exp_01 | Up | 462·462·211 | 1.097 | 38 | 1.135 | 1.386 | 81,9 % |
| exp_02 | Up | 462·462·214 | 1.077 | 61 | 1.138 | 1.386 | 82,1 % |
| exp_03 | Up | 429·429·204 | 1.041 | 21 | 1.062 | 1.287 | 82,5 % |
| **total** | — | 1.815·1.815·839 | **4.313** | **156** | **4.469** | **5.445** | **82,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.119 | 62 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.129 | 28 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.130 | 50 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.125 | 40 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.503** | **180** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·929 | 4.483 | 142 | 4.625 | 5.544 | 83,4 % |
| m2 | RUNNING | 1.848·1.848·691 | 4.244 | 143 | 4.387 | 5.544 | 79,1 % |
| m3 | RUNNING | 1.815·1.815·839 | 4.313 | 156 | 4.469 | 5.445 | 82,1 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.503 | 180 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.543** | **621** | **18.164** | **21.681** | **83,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:128, install/adb:14
- m2: erros → emulator/boot:128, install/adb:15
- m3: erros → emulator/boot:142, install/adb:14
- m4: erros → emulator/boot:149, install/adb:31

**Ações (08:01 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (08:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1. Nenhuma ação manual. ✅ m4 RE-ALCANÇOU a passada 300 (RV_TIMEOUTS=300 nos 4 containers) — re-caminhada pós-reboot #16 concluída em ~3h (como esperado); done 4.683, começa a subir agora. Total 18.164/21.681 = 83,8% (+82 vs 07:01; m1 +30, m2 +29, m3 +23). Ritmo volta a acelerar com m4 de novo na 300. Ordem: m4 91,0% > m1 83,4% > m3 82,1% > m2 79,1%. Reboots acumulados: 16.

## Ciclo 2026-07-10 09:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·244 | 1.136 | 32 | 1.168 | 1.386 | 84,3 % |
| exp_01 | Up | 462·462·238 | 1.120 | 42 | 1.162 | 1.386 | 83,8 % |
| exp_02 | Up | 462·462·230 | 1.120 | 34 | 1.154 | 1.386 | 83,3 % |
| exp_03 | Up | 462·462·250 | 1.139 | 35 | 1.174 | 1.386 | 84,7 % |
| **total** | — | 1.848·1.848·962 | **4.515** | **143** | **4.658** | **5.544** | **84,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·214 | 1.102 | 36 | 1.138 | 1.386 | 82,1 % |
| exp_01 | Up | 462·462·220 | 1.110 | 34 | 1.144 | 1.386 | 82,5 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·141 | 1.029 | 36 | 1.065 | 1.386 | 76,8 % |
| **total** | — | 1.848·1.848·721 | **4.272** | **145** | **4.417** | **5.544** | **79,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·219 | 1.107 | 36 | 1.143 | 1.386 | 82,5 % |
| exp_01 | Up | 462·462·217 | 1.104 | 37 | 1.141 | 1.386 | 82,3 % |
| exp_02 | Up | 462·462·224 | 1.087 | 61 | 1.148 | 1.386 | 82,8 % |
| exp_03 | Up | 429·429·213 | 1.050 | 21 | 1.071 | 1.287 | 83,2 % |
| **total** | — | 1.815·1.815·873 | **4.348** | **155** | **4.503** | **5.445** | **82,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.123 | 58 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.132 | 25 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.133 | 47 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.128 | 37 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.516** | **167** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·962 | 4.515 | 143 | 4.658 | 5.544 | 84,0 % |
| m2 | RUNNING | 1.848·1.848·721 | 4.272 | 145 | 4.417 | 5.544 | 79,7 % |
| m3 | RUNNING | 1.815·1.815·873 | 4.348 | 155 | 4.503 | 5.445 | 82,7 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.516 | 167 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.651** | **610** | **18.261** | **21.681** | **84,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:130, install/adb:13
- m2: erros → emulator/boot:130, install/adb:15
- m3: erros → emulator/boot:143, install/adb:12
- m4: erros → emulator/boot:148, install/adb:19

## Ciclo 2026-07-10 09:01:47 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·244 | 1.136 | 32 | 1.168 | 1.386 | 84,3 % |
| exp_01 | Up | 462·462·239 | 1.121 | 42 | 1.163 | 1.386 | 83,9 % |
| exp_02 | Up | 462·462·230 | 1.120 | 34 | 1.154 | 1.386 | 83,3 % |
| exp_03 | Up | 462·462·251 | 1.140 | 35 | 1.175 | 1.386 | 84,8 % |
| **total** | — | 1.848·1.848·964 | **4.517** | **143** | **4.660** | **5.544** | **84,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·215 | 1.103 | 36 | 1.139 | 1.386 | 82,2 % |
| exp_01 | Up | 462·462·220 | 1.110 | 34 | 1.144 | 1.386 | 82,5 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·141 | 1.029 | 36 | 1.065 | 1.386 | 76,8 % |
| **total** | — | 1.848·1.848·722 | **4.273** | **145** | **4.418** | **5.544** | **79,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·220 | 1.108 | 36 | 1.144 | 1.386 | 82,5 % |
| exp_01 | Up | 462·462·218 | 1.105 | 37 | 1.142 | 1.386 | 82,4 % |
| exp_02 | Up | 462·462·224 | 1.087 | 61 | 1.148 | 1.386 | 82,8 % |
| exp_03 | Up | 429·429·213 | 1.050 | 21 | 1.071 | 1.287 | 83,2 % |
| **total** | — | 1.815·1.815·875 | **4.350** | **155** | **4.505** | **5.445** | **82,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.123 | 58 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·299 | 1.132 | 25 | 1.157 | 1.287 | 89,9 % |
| exp_02 | Up | 429·429·322 | 1.133 | 47 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·307 | 1.128 | 37 | 1.165 | 1.287 | 90,5 % |
| **total** | — | 1.716·1.716·1.251 | **4.516** | **167** | **4.683** | **5.148** | **91,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·964 | 4.517 | 143 | 4.660 | 5.544 | 84,1 % |
| m2 | RUNNING | 1.848·1.848·722 | 4.273 | 145 | 4.418 | 5.544 | 79,7 % |
| m3 | RUNNING | 1.815·1.815·875 | 4.350 | 155 | 4.505 | 5.445 | 82,7 % |
| m4 | RUNNING | 1.716·1.716·1.251 | 4.516 | 167 | 4.683 | 5.148 | 91,0 % |
| **TOTAL** | — | — | **17.656** | **610** | **18.266** | **21.681** | **84,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:130, install/adb:13
- m2: erros → emulator/boot:130, install/adb:15
- m3: erros → emulator/boot:143, install/adb:12
- m4: erros → emulator/boot:148, install/adb:19

**Ações (09:01 local):** Ciclo de rotina, sem novos incidentes. Cron local ativo (09:00 registrado, 4 VMs RUNNING). Varredura SSH ATIVA: 4 VMs RUNNING, 5/5 Up, run_procs=1. Nenhuma ação manual. Total 18.266/21.681 = 84,2% (+102 vs 08:01; m1 +35, m3 +36, m2 +31). m4 done flat (4.683) MAS confirmado VIVO e trabalhando via docker logs (4 containers ativos na passada 300, Monkey 300s, coverage subindo). DIAGNÓSTICO: é a CAUDA PESADA da passada 300 de m4 — 300-pass COMPLETED=1132/1716 (~66%), restam ~584 tasks de 300s (5min cada) + re-tentativa de ~119 erros, memória apertada (11 GB livre) → throughput líquido baixo mas real. NÃO é barreira nem stuck, NÃO rebootar. m4 vai moer a cauda devagar; as outras 3 carregam o progresso. Ordem: m4 91,0% > m1 84,1% > m3 82,7% > m2 79,7%. Reboots acumulados: 16.

## Ciclo 2026-07-10 10:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·254 | 1.146 | 32 | 1.178 | 1.386 | 85,0 % |
| exp_01 | Up | 462·462·248 | 1.130 | 42 | 1.172 | 1.386 | 84,6 % |
| exp_02 | Up | 462·462·244 | 1.132 | 36 | 1.168 | 1.386 | 84,3 % |
| exp_03 | Up | 462·462·261 | 1.150 | 35 | 1.185 | 1.386 | 85,5 % |
| **total** | — | 1.848·1.848·1.007 | **4.558** | **145** | **4.703** | **5.544** | **84,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·224 | 1.112 | 36 | 1.148 | 1.386 | 82,8 % |
| exp_01 | Up | 462·462·229 | 1.119 | 34 | 1.153 | 1.386 | 83,2 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·150 | 1.038 | 36 | 1.074 | 1.386 | 77,5 % |
| **total** | — | 1.848·1.848·749 | **4.300** | **145** | **4.445** | **5.544** | **80,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·229 | 1.116 | 37 | 1.153 | 1.386 | 83,2 % |
| exp_01 | Up | 462·462·226 | 1.113 | 37 | 1.150 | 1.386 | 83,0 % |
| exp_02 | Up | 462·462·235 | 1.094 | 65 | 1.159 | 1.386 | 83,6 % |
| exp_03 | Up | 429·429·223 | 1.059 | 22 | 1.081 | 1.287 | 84,0 % |
| **total** | — | 1.815·1.815·913 | **4.382** | **161** | **4.543** | **5.445** | **83,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.130 | 51 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·306 | 1.141 | 23 | 1.164 | 1.287 | 90,4 % |
| exp_02 | Up | 429·429·322 | 1.138 | 42 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·316 | 1.136 | 38 | 1.174 | 1.287 | 91,2 % |
| **total** | — | 1.716·1.716·1.267 | **4.545** | **154** | **4.699** | **5.148** | **91,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.007 | 4.558 | 145 | 4.703 | 5.544 | 84,8 % |
| m2 | RUNNING | 1.848·1.848·749 | 4.300 | 145 | 4.445 | 5.544 | 80,2 % |
| m3 | RUNNING | 1.815·1.815·913 | 4.382 | 161 | 4.543 | 5.445 | 83,4 % |
| m4 | RUNNING | 1.716·1.716·1.267 | 4.545 | 154 | 4.699 | 5.148 | 91,3 % |
| **TOTAL** | — | — | **17.785** | **605** | **18.390** | **21.681** | **84,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:131, install/adb:14
- m2: erros → emulator/boot:130, install/adb:15
- m3: erros → emulator/boot:146, install/adb:15
- m4: erros → emulator/boot:149, install/adb:5

## Ciclo 2026-07-10 10:01:43 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·254 | 1.146 | 32 | 1.178 | 1.386 | 85,0 % |
| exp_01 | Up | 462·462·248 | 1.130 | 42 | 1.172 | 1.386 | 84,6 % |
| exp_02 | Up | 462·462·244 | 1.132 | 36 | 1.168 | 1.386 | 84,3 % |
| exp_03 | Up | 462·462·261 | 1.150 | 35 | 1.185 | 1.386 | 85,5 % |
| **total** | — | 1.848·1.848·1.007 | **4.558** | **145** | **4.703** | **5.544** | **84,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·224 | 1.112 | 36 | 1.148 | 1.386 | 82,8 % |
| exp_01 | Up | 462·462·230 | 1.120 | 34 | 1.154 | 1.386 | 83,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·150 | 1.038 | 36 | 1.074 | 1.386 | 77,5 % |
| **total** | — | 1.848·1.848·750 | **4.301** | **145** | **4.446** | **5.544** | **80,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·230 | 1.117 | 37 | 1.154 | 1.386 | 83,3 % |
| exp_01 | Up | 462·462·227 | 1.114 | 37 | 1.151 | 1.386 | 83,0 % |
| exp_02 | Up | 462·462·236 | 1.095 | 65 | 1.160 | 1.386 | 83,7 % |
| exp_03 | Up | 429·429·224 | 1.060 | 22 | 1.082 | 1.287 | 84,1 % |
| **total** | — | 1.815·1.815·917 | **4.386** | **161** | **4.547** | **5.445** | **83,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.130 | 51 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·306 | 1.141 | 23 | 1.164 | 1.287 | 90,4 % |
| exp_02 | Up | 429·429·322 | 1.138 | 42 | 1.180 | 1.287 | 91,7 % |
| exp_03 | Up | 429·429·316 | 1.136 | 38 | 1.174 | 1.287 | 91,2 % |
| **total** | — | 1.716·1.716·1.267 | **4.545** | **154** | **4.699** | **5.148** | **91,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.007 | 4.558 | 145 | 4.703 | 5.544 | 84,8 % |
| m2 | RUNNING | 1.848·1.848·750 | 4.301 | 145 | 4.446 | 5.544 | 80,2 % |
| m3 | RUNNING | 1.815·1.815·917 | 4.386 | 161 | 4.547 | 5.445 | 83,5 % |
| m4 | RUNNING | 1.716·1.716·1.267 | 4.545 | 154 | 4.699 | 5.148 | 91,3 % |
| **TOTAL** | — | — | **17.790** | **605** | **18.395** | **21.681** | **84,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:131, install/adb:14
- m2: erros → emulator/boot:130, install/adb:15
- m3: erros → emulator/boot:146, install/adb:15
- m4: erros → emulator/boot:149, install/adb:5

**Ações (10:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: m1/m2/m4 RUNNING 5/5 Up; m3 SSH_FALHOU na 1ª tentativa → BLIP TRANSITÓRIO sob carga altíssima (load average 109.90!), NÃO travamento: recuperou na retentativa (ConnectTimeout 30), uptime "up 1 day" (não rebootou), 5/5 Up + run vivo. SEM reboot — blip de SSH não é VM travada (distinção: retry com timeout maior resolve). Nenhuma ação destrutiva. Total 18.390/21.681 = 84,8% (+124 vs 09:01; m1 +43, m3 +38, m2 +27, m4 +16). ✅ m4 saiu do flat (done 4.683→4.699, moendo a cauda 300 como diagnosticado). Ordem: m4 91,3% > m1 84,8% > m3 83,4% > m2 80,2%. Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 10:08:04 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·255 | 1.147 | 32 | 1.179 | 1.386 | 85,1 % |
| exp_01 | Up | 462·462·249 | 1.131 | 42 | 1.173 | 1.386 | 84,6 % |
| exp_02 | Up | 462·462·246 | 1.134 | 36 | 1.170 | 1.386 | 84,4 % |
| exp_03 | Up | 462·462·262 | 1.151 | 35 | 1.186 | 1.386 | 85,6 % |
| **total** | — | 1.848·1.848·1.012 | **4.563** | **145** | **4.708** | **5.544** | **84,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·225 | 1.113 | 36 | 1.149 | 1.386 | 82,9 % |
| exp_01 | Up | 462·462·231 | 1.121 | 34 | 1.155 | 1.386 | 83,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·151 | 1.039 | 36 | 1.075 | 1.386 | 77,6 % |
| **total** | — | 1.848·1.848·753 | **4.304** | **145** | **4.449** | **5.544** | **80,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·231 | 1.118 | 37 | 1.155 | 1.386 | 83,3 % |
| exp_01 | Up | 462·462·228 | 1.115 | 37 | 1.152 | 1.386 | 83,1 % |
| exp_02 | Up | 462·462·237 | 1.096 | 65 | 1.161 | 1.386 | 83,8 % |
| exp_03 | Up | 429·429·224 | 1.060 | 22 | 1.082 | 1.287 | 84,1 % |
| **total** | — | 1.815·1.815·920 | **4.389** | **161** | **4.550** | **5.445** | **83,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·323 | 1.130 | 51 | 1.181 | 1.287 | 91,8 % |
| exp_01 | Up | 429·429·307 | 1.142 | 23 | 1.165 | 1.287 | 90,5 % |
| exp_02 | Up | 429·429·323 | 1.140 | 41 | 1.181 | 1.287 | 91,8 % |
| exp_03 | Up | 429·429·317 | 1.137 | 38 | 1.175 | 1.287 | 91,3 % |
| **total** | — | 1.716·1.716·1.270 | **4.549** | **153** | **4.702** | **5.148** | **91,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.012 | 4.563 | 145 | 4.708 | 5.544 | 84,9 % |
| m2 | RUNNING | 1.848·1.848·753 | 4.304 | 145 | 4.449 | 5.544 | 80,2 % |
| m3 | RUNNING | 1.815·1.815·920 | 4.389 | 161 | 4.550 | 5.445 | 83,6 % |
| m4 | RUNNING | 1.716·1.716·1.270 | 4.549 | 153 | 4.702 | 5.148 | 91,3 % |
| **TOTAL** | — | — | **17.805** | **604** | **18.409** | **21.681** | **84,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:131, install/adb:14
- m2: erros → emulator/boot:130, install/adb:15
- m3: erros → emulator/boot:146, install/adb:15
- m4: erros → emulator/boot:148, install/adb:5

**Ações (10:08 local):** Retomada do loop em nova sessão. Cron local ativo (0 * * * * health_check). Varredura SSH ativa: m1 5/5 Up (run_procs 2, exp_02 recém-restartado OOM pelo cron 10:40 — normal), m2 5/5 Up (run_procs 2), m4 5/5 Up (run_procs 2, uptime 5:03 = reboot #16 de 05:04 já contabilizado). m3 SSH banner-timeout na 1ª tentativa (ConnectTimeout 20) → BLIP TRANSITÓRIO sob carga altíssima (load average 69.46), recuperou na retentativa ConnectTimeout=30, uptime "up 1 day 6:02" (NÃO rebootou), 5/5 Up + run vivo → SEM reboot (distinção blip×travada aplicada). gcloud: 4/4 RUNNING. Nenhuma ação destrutiva, nenhum restart manual necessário (cron OOM cobrindo). Total 18.409/21.681 = 84,9% (+14 vs 10:01). Ordem: m4 91,3% > m1 84,9% > m3 83,6% > m2 80,2%. m4 na cauda pesada 300 (feito ~flat, throughput baixo — esperado). Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 11:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·263 | 1.155 | 32 | 1.187 | 1.386 | 85,6 % |
| exp_01 | Up | 462·462·260 | 1.142 | 42 | 1.184 | 1.386 | 85,4 % |
| exp_02 | Up | 462·462·254 | 1.142 | 36 | 1.178 | 1.386 | 85,0 % |
| exp_03 | Up | 462·462·272 | 1.159 | 37 | 1.196 | 1.386 | 86,3 % |
| **total** | — | 1.848·1.848·1.049 | **4.598** | **147** | **4.745** | **5.544** | **85,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·236 | 1.121 | 39 | 1.160 | 1.386 | 83,7 % |
| exp_01 | Up | 462·462·241 | 1.128 | 37 | 1.165 | 1.386 | 84,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·160 | 1.048 | 36 | 1.084 | 1.386 | 78,2 % |
| **total** | — | 1.848·1.848·783 | **4.328** | **151** | **4.479** | **5.544** | **80,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·240 | 1.124 | 40 | 1.164 | 1.386 | 84,0 % |
| exp_01 | Up | 462·462·229 | 1.116 | 37 | 1.153 | 1.386 | 83,2 % |
| exp_02 | Up | 462·462·244 | 1.103 | 65 | 1.168 | 1.386 | 84,3 % |
| exp_03 | Up | 429·429·235 | 1.067 | 26 | 1.093 | 1.287 | 84,9 % |
| **total** | — | 1.815·1.815·948 | **4.410** | **168** | **4.578** | **5.445** | **84,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·333 | 1.138 | 53 | 1.191 | 1.287 | 92,5 % |
| exp_01 | Up | 429·429·315 | 1.150 | 23 | 1.173 | 1.287 | 91,1 % |
| exp_02 | Up | 429·429·333 | 1.147 | 44 | 1.191 | 1.287 | 92,5 % |
| exp_03 | Up | 429·429·328 | 1.148 | 38 | 1.186 | 1.287 | 92,2 % |
| **total** | — | 1.716·1.716·1.309 | **4.583** | **158** | **4.741** | **5.148** | **92,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.049 | 4.598 | 147 | 4.745 | 5.544 | 85,6 % |
| m2 | RUNNING | 1.848·1.848·783 | 4.328 | 151 | 4.479 | 5.544 | 80,8 % |
| m3 | RUNNING | 1.815·1.815·948 | 4.410 | 168 | 4.578 | 5.445 | 84,1 % |
| m4 | RUNNING | 1.716·1.716·1.309 | 4.583 | 158 | 4.741 | 5.148 | 92,1 % |
| **TOTAL** | — | — | **17.919** | **624** | **18.543** | **21.681** | **85,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:133, install/adb:14
- m2: erros → emulator/boot:136, install/adb:15
- m3: erros → emulator/boot:151, install/adb:17
- m4: erros → emulator/boot:152, install/adb:6

## Ciclo 2026-07-10 11:01:36 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·263 | 1.155 | 32 | 1.187 | 1.386 | 85,6 % |
| exp_01 | Up | 462·462·260 | 1.142 | 42 | 1.184 | 1.386 | 85,4 % |
| exp_02 | Up | 462·462·255 | 1.143 | 36 | 1.179 | 1.386 | 85,1 % |
| exp_03 | Up | 462·462·272 | 1.159 | 37 | 1.196 | 1.386 | 86,3 % |
| **total** | — | 1.848·1.848·1.050 | **4.599** | **147** | **4.746** | **5.544** | **85,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·236 | 1.121 | 39 | 1.160 | 1.386 | 83,7 % |
| exp_01 | Up | 462·462·241 | 1.128 | 37 | 1.165 | 1.386 | 84,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·160 | 1.048 | 36 | 1.084 | 1.386 | 78,2 % |
| **total** | — | 1.848·1.848·783 | **4.328** | **151** | **4.479** | **5.544** | **80,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·241 | 1.125 | 40 | 1.165 | 1.386 | 84,1 % |
| exp_01 | Up | 462·462·229 | 1.116 | 37 | 1.153 | 1.386 | 83,2 % |
| exp_02 | Up | 462·462·245 | 1.104 | 65 | 1.169 | 1.386 | 84,3 % |
| exp_03 | Up | 429·429·235 | 1.067 | 26 | 1.093 | 1.287 | 84,9 % |
| **total** | — | 1.815·1.815·950 | **4.412** | **168** | **4.580** | **5.445** | **84,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·333 | 1.138 | 53 | 1.191 | 1.287 | 92,5 % |
| exp_01 | Up | 429·429·315 | 1.150 | 23 | 1.173 | 1.287 | 91,1 % |
| exp_02 | Up | 429·429·333 | 1.147 | 44 | 1.191 | 1.287 | 92,5 % |
| exp_03 | Up | 429·429·328 | 1.148 | 38 | 1.186 | 1.287 | 92,2 % |
| **total** | — | 1.716·1.716·1.309 | **4.583** | **158** | **4.741** | **5.148** | **92,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.050 | 4.599 | 147 | 4.746 | 5.544 | 85,6 % |
| m2 | RUNNING | 1.848·1.848·783 | 4.328 | 151 | 4.479 | 5.544 | 80,8 % |
| m3 | RUNNING | 1.815·1.815·950 | 4.412 | 168 | 4.580 | 5.445 | 84,1 % |
| m4 | RUNNING | 1.716·1.716·1.309 | 4.583 | 158 | 4.741 | 5.148 | 92,1 % |
| **TOTAL** | — | — | **17.922** | **624** | **18.546** | **21.681** | **85,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:133, install/adb:14
- m2: erros → emulator/boot:136, install/adb:15
- m3: erros → emulator/boot:151, install/adb:17
- m4: erros → emulator/boot:152, install/adb:6

**Ações (11:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: as 4 VMs responderam na 1ª tentativa, 5/5 Up, run_procs=2, cron OOM funcionando (m1 exp_02 up 3h / m3 exp_01 up 31min — restarts OOM normais). Sem SSH_FALHOU no cron.out 11:00. Nenhuma ação manual necessária. Total 18.546/21.681 = 85,5% (+137 vs 10:08). Deltas: m4 +39 (4.741), m1 +38 (4.746), m2 +30 (4.479), m3 +30 (4.580). ✅ m4 saiu do flat, moendo a cauda 300 (300=1.309, +42). Ordem: m4 92,1% > m1 85,6% > m3 84,1% > m2 80,8%. Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 12:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.163 | 35 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·270 | 1.149 | 45 | 1.194 | 1.386 | 86,1 % |
| exp_02 | Up | 462·462·266 | 1.151 | 39 | 1.190 | 1.386 | 85,9 % |
| exp_03 | Up | 462·462·283 | 1.168 | 39 | 1.207 | 1.386 | 87,1 % |
| **total** | — | 1.848·1.848·1.093 | **4.631** | **158** | **4.789** | **5.544** | **86,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·245 | 1.130 | 39 | 1.169 | 1.386 | 84,3 % |
| exp_01 | Up | 462·462·250 | 1.137 | 37 | 1.174 | 1.386 | 84,7 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·171 | 1.056 | 39 | 1.095 | 1.386 | 79,0 % |
| **total** | — | 1.848·1.848·812 | **4.354** | **154** | **4.508** | **5.544** | **81,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·250 | 1.134 | 40 | 1.174 | 1.386 | 84,7 % |
| exp_01 | Up | 462·462·236 | 1.121 | 39 | 1.160 | 1.386 | 83,7 % |
| exp_02 | Up | 462·462·254 | 1.113 | 65 | 1.178 | 1.386 | 85,0 % |
| exp_03 | Up | 429·429·244 | 1.076 | 26 | 1.102 | 1.287 | 85,6 % |
| **total** | — | 1.815·1.815·984 | **4.444** | **170** | **4.614** | **5.445** | **84,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·343 | 1.148 | 53 | 1.201 | 1.287 | 93,3 % |
| exp_01 | Up | 429·429·325 | 1.160 | 23 | 1.183 | 1.287 | 91,9 % |
| exp_02 | Up | 429·429·343 | 1.157 | 44 | 1.201 | 1.287 | 93,3 % |
| exp_03 | Up | 429·429·338 | 1.156 | 40 | 1.196 | 1.287 | 92,9 % |
| **total** | — | 1.716·1.716·1.349 | **4.621** | **160** | **4.781** | **5.148** | **92,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.093 | 4.631 | 158 | 4.789 | 5.544 | 86,4 % |
| m2 | RUNNING | 1.848·1.848·812 | 4.354 | 154 | 4.508 | 5.544 | 81,3 % |
| m3 | RUNNING | 1.815·1.815·984 | 4.444 | 170 | 4.614 | 5.445 | 84,7 % |
| m4 | RUNNING | 1.716·1.716·1.349 | 4.621 | 160 | 4.781 | 5.148 | 92,9 % |
| **TOTAL** | — | — | **18.050** | **642** | **18.692** | **21.681** | **86,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:139, install/adb:19
- m2: erros → emulator/boot:139, install/adb:15
- m3: erros → emulator/boot:152, install/adb:18
- m4: erros → emulator/boot:154, install/adb:6

## Ciclo 2026-07-10 12:01:42 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·275 | 1.164 | 35 | 1.199 | 1.386 | 86,5 % |
| exp_01 | Up | 462·462·270 | 1.149 | 45 | 1.194 | 1.386 | 86,1 % |
| exp_02 | Up | 462·462·266 | 1.151 | 39 | 1.190 | 1.386 | 85,9 % |
| exp_03 | Up | 462·462·283 | 1.168 | 39 | 1.207 | 1.386 | 87,1 % |
| **total** | — | 1.848·1.848·1.094 | **4.632** | **158** | **4.790** | **5.544** | **86,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·246 | 1.131 | 39 | 1.170 | 1.386 | 84,4 % |
| exp_01 | Up | 462·462·250 | 1.137 | 37 | 1.174 | 1.386 | 84,7 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·171 | 1.056 | 39 | 1.095 | 1.386 | 79,0 % |
| **total** | — | 1.848·1.848·813 | **4.355** | **154** | **4.509** | **5.544** | **81,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·250 | 1.134 | 40 | 1.174 | 1.386 | 84,7 % |
| exp_01 | Up | 462·462·237 | 1.122 | 39 | 1.161 | 1.386 | 83,8 % |
| exp_02 | Up | 462·462·254 | 1.113 | 65 | 1.178 | 1.386 | 85,0 % |
| exp_03 | Up | 429·429·245 | 1.077 | 26 | 1.103 | 1.287 | 85,7 % |
| **total** | — | 1.815·1.815·986 | **4.446** | **170** | **4.616** | **5.445** | **84,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·344 | 1.149 | 53 | 1.202 | 1.287 | 93,4 % |
| exp_01 | Up | 429·429·325 | 1.160 | 23 | 1.183 | 1.287 | 91,9 % |
| exp_02 | Up | 429·429·343 | 1.157 | 44 | 1.201 | 1.287 | 93,3 % |
| exp_03 | Up | 429·429·338 | 1.156 | 40 | 1.196 | 1.287 | 92,9 % |
| **total** | — | 1.716·1.716·1.350 | **4.622** | **160** | **4.782** | **5.148** | **92,9 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.094 | 4.632 | 158 | 4.790 | 5.544 | 86,4 % |
| m2 | RUNNING | 1.848·1.848·813 | 4.355 | 154 | 4.509 | 5.544 | 81,3 % |
| m3 | RUNNING | 1.815·1.815·986 | 4.446 | 170 | 4.616 | 5.445 | 84,8 % |
| m4 | RUNNING | 1.716·1.716·1.350 | 4.622 | 160 | 4.782 | 5.148 | 92,9 % |
| **TOTAL** | — | — | **18.055** | **642** | **18.697** | **21.681** | **86,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:139, install/adb:19
- m2: erros → emulator/boot:139, install/adb:15
- m3: erros → emulator/boot:152, install/adb:18
- m4: erros → emulator/boot:154, install/adb:6

**Ações (12:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: as 4 VMs responderam na 1ª tentativa, 5/5 Up, run_procs=2, cron OOM funcionando (restarts normais m1/m3). Sem SSH_FALHOU no cron.out 12:00. Nenhuma ação manual necessária. Total 18.697/21.681 = 86,2% (+151 vs 11:01). Deltas: m3 +36 (4.616), m4 +41 (4.782), m1 +44 (4.790), m2 +30 (4.509). As 4 avançando bem na passada 300 (m4 300=1.350, +41). Ordem: m4 92,9% > m1 86,4% > m3 84,8% > m2 81,3%. Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 13:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·280 | 1.169 | 35 | 1.204 | 1.386 | 86,9 % |
| exp_01 | Up | 462·462·276 | 1.155 | 45 | 1.200 | 1.386 | 86,6 % |
| exp_02 | Up | 462·462·272 | 1.156 | 40 | 1.196 | 1.386 | 86,3 % |
| exp_03 | Up | 462·462·289 | 1.174 | 39 | 1.213 | 1.386 | 87,5 % |
| **total** | — | 1.848·1.848·1.117 | **4.654** | **159** | **4.813** | **5.544** | **86,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·255 | 1.140 | 39 | 1.179 | 1.386 | 85,1 % |
| exp_01 | Up | 462·462·262 | 1.147 | 39 | 1.186 | 1.386 | 85,6 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·182 | 1.065 | 41 | 1.106 | 1.386 | 79,8 % |
| **total** | — | 1.848·1.848·845 | **4.383** | **158** | **4.541** | **5.544** | **81,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·260 | 1.143 | 41 | 1.184 | 1.386 | 85,4 % |
| exp_01 | Up | 462·462·246 | 1.130 | 40 | 1.170 | 1.386 | 84,4 % |
| exp_02 | Up | 462·462·263 | 1.122 | 65 | 1.187 | 1.386 | 85,6 % |
| exp_03 | Up | 429·429·255 | 1.086 | 27 | 1.113 | 1.287 | 86,5 % |
| **total** | — | 1.815·1.815·1.024 | **4.481** | **173** | **4.654** | **5.445** | **85,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·353 | 1.158 | 53 | 1.211 | 1.287 | 94,1 % |
| exp_01 | Up | 429·429·336 | 1.168 | 26 | 1.194 | 1.287 | 92,8 % |
| exp_02 | Up | 429·429·353 | 1.166 | 45 | 1.211 | 1.287 | 94,1 % |
| exp_03 | Up | 429·429·349 | 1.166 | 41 | 1.207 | 1.287 | 93,8 % |
| **total** | — | 1.716·1.716·1.391 | **4.658** | **165** | **4.823** | **5.148** | **93,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.117 | 4.654 | 159 | 4.813 | 5.544 | 86,8 % |
| m2 | RUNNING | 1.848·1.848·845 | 4.383 | 158 | 4.541 | 5.544 | 81,9 % |
| m3 | RUNNING | 1.815·1.815·1.024 | 4.481 | 173 | 4.654 | 5.445 | 85,5 % |
| m4 | RUNNING | 1.716·1.716·1.391 | 4.658 | 165 | 4.823 | 5.148 | 93,7 % |
| **TOTAL** | — | — | **18.176** | **655** | **18.831** | **21.681** | **86,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:139, install/adb:19
- m3: erros → emulator/boot:152, install/adb:21
- m4: erros → emulator/boot:157, install/adb:8

## Ciclo 2026-07-10 13:01:42 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·281 | 1.170 | 35 | 1.205 | 1.386 | 86,9 % |
| exp_01 | Up | 462·462·277 | 1.156 | 45 | 1.201 | 1.386 | 86,7 % |
| exp_02 | Up | 462·462·273 | 1.157 | 40 | 1.197 | 1.386 | 86,4 % |
| exp_03 | Up | 462·462·290 | 1.175 | 39 | 1.214 | 1.386 | 87,6 % |
| **total** | — | 1.848·1.848·1.121 | **4.658** | **159** | **4.817** | **5.544** | **86,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·255 | 1.140 | 39 | 1.179 | 1.386 | 85,1 % |
| exp_01 | Up | 462·462·262 | 1.147 | 39 | 1.186 | 1.386 | 85,6 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·183 | 1.066 | 41 | 1.107 | 1.386 | 79,9 % |
| **total** | — | 1.848·1.848·846 | **4.384** | **158** | **4.542** | **5.544** | **81,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·261 | 1.144 | 41 | 1.185 | 1.386 | 85,5 % |
| exp_01 | Up | 462·462·247 | 1.131 | 40 | 1.171 | 1.386 | 84,5 % |
| exp_02 | Up | 462·462·263 | 1.122 | 65 | 1.187 | 1.386 | 85,6 % |
| exp_03 | Up | 429·429·255 | 1.086 | 27 | 1.113 | 1.287 | 86,5 % |
| **total** | — | 1.815·1.815·1.026 | **4.483** | **173** | **4.656** | **5.445** | **85,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·353 | 1.158 | 53 | 1.211 | 1.287 | 94,1 % |
| exp_01 | Up | 429·429·337 | 1.169 | 26 | 1.195 | 1.287 | 92,9 % |
| exp_02 | Up | 429·429·353 | 1.166 | 45 | 1.211 | 1.287 | 94,1 % |
| exp_03 | Up | 429·429·349 | 1.166 | 41 | 1.207 | 1.287 | 93,8 % |
| **total** | — | 1.716·1.716·1.392 | **4.659** | **165** | **4.824** | **5.148** | **93,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.121 | 4.658 | 159 | 4.817 | 5.544 | 86,9 % |
| m2 | RUNNING | 1.848·1.848·846 | 4.384 | 158 | 4.542 | 5.544 | 81,9 % |
| m3 | RUNNING | 1.815·1.815·1.026 | 4.483 | 173 | 4.656 | 5.445 | 85,5 % |
| m4 | RUNNING | 1.716·1.716·1.392 | 4.659 | 165 | 4.824 | 5.148 | 93,7 % |
| **TOTAL** | — | — | **18.184** | **655** | **18.839** | **21.681** | **86,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:139, install/adb:19
- m3: erros → emulator/boot:152, install/adb:21
- m4: erros → emulator/boot:157, install/adb:8

**Ações (13:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: as 4 VMs responderam na 1ª tentativa, 5/5 Up, run_procs=2, cron OOM funcionando. m1 com pico de memória recente (load 15-min=146) mas 1-min já em 29 e SSH OK — spike se recuperando, sem blip, sem ação. Sem SSH_FALHOU no cron.out 13:00. Nenhuma ação manual necessária. Total 18.839/21.681 = 86,9% (+142 vs 12:01). Deltas: m1 +27 (4.817), m2 +33 (4.542), m3 +40 (4.656), m4 +42 (4.824). As 4 na passada 300, m4 quase em 94% (300=1.392, +42). Ordem: m4 93,7% > m1 86,9% > m3 85,5% > m2 81,9%. Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 14:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.171 | 35 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·279 | 1.158 | 45 | 1.203 | 1.386 | 86,8 % |
| exp_02 | Up | 462·462·275 | 1.159 | 40 | 1.199 | 1.386 | 86,5 % |
| exp_03 | Up | 462·462·292 | 1.177 | 39 | 1.216 | 1.386 | 87,7 % |
| **total** | — | 1.848·1.848·1.128 | **4.665** | **159** | **4.824** | **5.544** | **87,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·267 | 1.148 | 43 | 1.191 | 1.386 | 85,9 % |
| exp_01 | Up | 462·462·272 | 1.155 | 41 | 1.196 | 1.386 | 86,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·194 | 1.077 | 41 | 1.118 | 1.386 | 80,7 % |
| **total** | — | 1.848·1.848·879 | **4.411** | **164** | **4.575** | **5.544** | **82,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·272 | 1.152 | 44 | 1.196 | 1.386 | 86,3 % |
| exp_01 | Up | 462·462·255 | 1.139 | 40 | 1.179 | 1.386 | 85,1 % |
| exp_02 | Up | 462·462·274 | 1.130 | 68 | 1.198 | 1.386 | 86,4 % |
| exp_03 | Up | 429·429·266 | 1.094 | 30 | 1.124 | 1.287 | 87,3 % |
| **total** | — | 1.815·1.815·1.067 | **4.515** | **182** | **4.697** | **5.445** | **86,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·363 | 1.168 | 53 | 1.221 | 1.287 | 94,9 % |
| exp_01 | Up | 429·429·347 | 1.179 | 26 | 1.205 | 1.287 | 93,6 % |
| exp_02 | Up | 429·429·367 | 1.176 | 49 | 1.225 | 1.287 | 95,2 % |
| exp_03 | Up | 429·429·359 | 1.175 | 42 | 1.217 | 1.287 | 94,6 % |
| **total** | — | 1.716·1.716·1.436 | **4.698** | **170** | **4.868** | **5.148** | **94,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.128 | 4.665 | 159 | 4.824 | 5.544 | 87,0 % |
| m2 | RUNNING | 1.848·1.848·879 | 4.411 | 164 | 4.575 | 5.544 | 82,5 % |
| m3 | RUNNING | 1.815·1.815·1.067 | 4.515 | 182 | 4.697 | 5.445 | 86,3 % |
| m4 | RUNNING | 1.716·1.716·1.436 | 4.698 | 170 | 4.868 | 5.148 | 94,6 % |
| **TOTAL** | — | — | **18.289** | **675** | **18.964** | **21.681** | **87,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:144, install/adb:20
- m3: erros → emulator/boot:159, install/adb:23
- m4: erros → emulator/boot:160, install/adb:10

## Ciclo 2026-07-10 14:01:35 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.171 | 35 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·279 | 1.158 | 45 | 1.203 | 1.386 | 86,8 % |
| exp_02 | Up | 462·462·275 | 1.159 | 40 | 1.199 | 1.386 | 86,5 % |
| exp_03 | Up | 462·462·292 | 1.177 | 39 | 1.216 | 1.386 | 87,7 % |
| **total** | — | 1.848·1.848·1.128 | **4.665** | **159** | **4.824** | **5.544** | **87,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·268 | 1.149 | 43 | 1.192 | 1.386 | 86,0 % |
| exp_01 | Up | 462·462·272 | 1.155 | 41 | 1.196 | 1.386 | 86,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·194 | 1.077 | 41 | 1.118 | 1.386 | 80,7 % |
| **total** | — | 1.848·1.848·880 | **4.412** | **164** | **4.576** | **5.544** | **82,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·272 | 1.152 | 44 | 1.196 | 1.386 | 86,3 % |
| exp_01 | Up | 462·462·256 | 1.140 | 40 | 1.180 | 1.386 | 85,1 % |
| exp_02 | Up | 462·462·274 | 1.130 | 68 | 1.198 | 1.386 | 86,4 % |
| exp_03 | Up | 429·429·267 | 1.094 | 31 | 1.125 | 1.287 | 87,4 % |
| **total** | — | 1.815·1.815·1.069 | **4.516** | **183** | **4.699** | **5.445** | **86,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·364 | 1.168 | 54 | 1.222 | 1.287 | 94,9 % |
| exp_01 | Up | 429·429·348 | 1.180 | 26 | 1.206 | 1.287 | 93,7 % |
| exp_02 | Up | 429·429·367 | 1.176 | 49 | 1.225 | 1.287 | 95,2 % |
| exp_03 | Up | 429·429·359 | 1.175 | 42 | 1.217 | 1.287 | 94,6 % |
| **total** | — | 1.716·1.716·1.438 | **4.699** | **171** | **4.870** | **5.148** | **94,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.128 | 4.665 | 159 | 4.824 | 5.544 | 87,0 % |
| m2 | RUNNING | 1.848·1.848·880 | 4.412 | 164 | 4.576 | 5.544 | 82,5 % |
| m3 | RUNNING | 1.815·1.815·1.069 | 4.516 | 183 | 4.699 | 5.445 | 86,3 % |
| m4 | RUNNING | 1.716·1.716·1.438 | 4.699 | 171 | 4.870 | 5.148 | 94,6 % |
| **TOTAL** | — | — | **18.292** | **677** | **18.969** | **21.681** | **87,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:144, install/adb:20
- m3: erros → emulator/boot:160, install/adb:23
- m4: erros → emulator/boot:161, install/adb:10

**Ações (14:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: as 4 VMs na 1ª tentativa, 5/5 Up, run_procs=2, cron OOM funcionando (m1 exp_00 recém-restartado 17:00 UTC, up 1min; pico load 15-min=161 já caindo). Sem SSH_FALHOU no cron.out 14:00. Nenhuma ação manual necessária. Total 18.969/21.681 = 87,5% (+130 vs 13:01). Deltas: m1 +7 (4.824, exp_00 acabou de reiniciar OOM → throughput temporariamente menor), m2 +34 (4.576), m3 +43 (4.699), m4 +46 (4.870). m4 já em 94,6% (300=1.438). Ordem: m4 94,6% > m1 87,0% > m3 86,3% > m2 82,5%. Reboots acumulados: 16 (nenhum novo).

## Ciclo 2026-07-10 15:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.174 | 32 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·289 | 1.168 | 45 | 1.213 | 1.386 | 87,5 % |
| exp_02 | Up | 462·462·285 | 1.169 | 40 | 1.209 | 1.386 | 87,2 % |
| exp_03 | Up | 462·462·303 | 1.185 | 42 | 1.227 | 1.386 | 88,5 % |
| **total** | — | 1.848·1.848·1.159 | **4.696** | **159** | **4.855** | **5.544** | **87,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·278 | 1.158 | 44 | 1.202 | 1.386 | 86,7 % |
| exp_01 | Up | 462·462·282 | 1.165 | 41 | 1.206 | 1.386 | 87,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·199 | 1.082 | 41 | 1.123 | 1.386 | 81,0 % |
| **total** | — | 1.848·1.848·905 | **4.436** | **165** | **4.601** | **5.544** | **83,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.154 | 44 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.141 | 40 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.522** | **183** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·374 | 1.176 | 56 | 1.232 | 1.287 | 95,7 % |
| exp_01 | Up | 429·429·358 | 1.189 | 27 | 1.216 | 1.287 | 94,5 % |
| exp_02 | Up | 429·429·376 | 1.185 | 49 | 1.234 | 1.287 | 95,9 % |
| exp_03 | Up | 429·429·371 | 1.184 | 45 | 1.229 | 1.287 | 95,5 % |
| **total** | — | 1.716·1.716·1.479 | **4.734** | **177** | **4.911** | **5.148** | **95,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.159 | 4.696 | 159 | 4.855 | 5.544 | 87,6 % |
| m2 | RUNNING | 1.848·1.848·905 | 4.436 | 165 | 4.601 | 5.544 | 83,0 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.522 | 183 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.479 | 4.734 | 177 | 4.911 | 5.148 | 95,4 % |
| **TOTAL** | — | — | **18.388** | **684** | **19.072** | **21.681** | **88,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:143, install/adb:22
- m3: erros → emulator/boot:160, install/adb:23
- m4: erros → emulator/boot:165, install/adb:12

## Ciclo 2026-07-10 15:01:42 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.174 | 32 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·289 | 1.168 | 45 | 1.213 | 1.386 | 87,5 % |
| exp_02 | Up | 462·462·285 | 1.169 | 40 | 1.209 | 1.386 | 87,2 % |
| exp_03 | Up | 462·462·303 | 1.185 | 42 | 1.227 | 1.386 | 88,5 % |
| **total** | — | 1.848·1.848·1.159 | **4.696** | **159** | **4.855** | **5.544** | **87,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·278 | 1.158 | 44 | 1.202 | 1.386 | 86,7 % |
| exp_01 | Up | 462·462·282 | 1.165 | 41 | 1.206 | 1.386 | 87,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·199 | 1.082 | 41 | 1.123 | 1.386 | 81,0 % |
| **total** | — | 1.848·1.848·905 | **4.436** | **165** | **4.601** | **5.544** | **83,0 %** |

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·375 | 1.177 | 56 | 1.233 | 1.287 | 95,8 % |
| exp_01 | Up | 429·429·359 | 1.190 | 27 | 1.217 | 1.287 | 94,6 % |
| exp_02 | Up | 429·429·377 | 1.186 | 49 | 1.235 | 1.287 | 96,0 % |
| exp_03 | Up | 429·429·371 | 1.184 | 45 | 1.229 | 1.287 | 95,5 % |
| **total** | — | 1.716·1.716·1.482 | **4.737** | **177** | **4.914** | **5.148** | **95,5 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.159 | 4.696 | 159 | 4.855 | 5.544 | 87,6 % |
| m2 | RUNNING | 1.848·1.848·905 | 4.436 | 165 | 4.601 | 5.544 | 83,0 % |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.482 | 4.737 | 177 | 4.914 | 5.148 | 95,5 % |
| **TOTAL** | — | — | **13.869** | **501** | **14.370** | **16.236** | **88,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:140, install/adb:19
- m2: erros → emulator/boot:143, install/adb:22
- m3: SSH inacessível — ssh timeout (sem ação)
- m4: erros → emulator/boot:165, install/adb:12

## Ciclo 2026-07-10 15:12:28 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.175 | 31 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·290 | 1.169 | 45 | 1.214 | 1.386 | 87,6 % |
| exp_02 | Up | 462·462·287 | 1.171 | 40 | 1.211 | 1.386 | 87,4 % |
| exp_03 | Up | 462·462·305 | 1.187 | 42 | 1.229 | 1.386 | 88,7 % |
| **total** | — | 1.848·1.848·1.164 | **4.702** | **158** | **4.860** | **5.544** | **87,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·280 | 1.160 | 44 | 1.204 | 1.386 | 86,9 % |
| exp_01 | Up | 462·462·284 | 1.167 | 41 | 1.208 | 1.386 | 87,2 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·199 | 1.082 | 41 | 1.123 | 1.386 | 81,0 % |
| **total** | — | 1.848·1.848·909 | **4.440** | **165** | **4.605** | **5.544** | **83,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.154 | 44 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.141 | 40 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.522** | **183** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·376 | 1.178 | 56 | 1.234 | 1.287 | 95,9 % |
| exp_01 | Up | 429·429·360 | 1.191 | 27 | 1.218 | 1.287 | 94,6 % |
| exp_02 | Up | 429·429·378 | 1.187 | 49 | 1.236 | 1.287 | 96,0 % |
| exp_03 | Up | 429·429·373 | 1.186 | 45 | 1.231 | 1.287 | 95,6 % |
| **total** | — | 1.716·1.716·1.487 | **4.742** | **177** | **4.919** | **5.148** | **95,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.164 | 4.702 | 158 | 4.860 | 5.544 | 87,7 % |
| m2 | RUNNING | 1.848·1.848·909 | 4.440 | 165 | 4.605 | 5.544 | 83,1 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.522 | 183 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.487 | 4.742 | 177 | 4.919 | 5.148 | 95,6 % |
| **TOTAL** | — | — | **18.406** | **683** | **19.089** | **21.681** | **88,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:141, install/adb:17
- m2: erros → emulator/boot:143, install/adb:22
- m3: erros → emulator/boot:160, install/adb:23
- m4: erros → emulator/boot:165, install/adb:12

**Ações (15:12 local):** ⚠️ REBOOT #17 (m3). Sequência: varredura SSH 15:01 mostrou m3 viva mas com pico de load 15-min=242 (pressão de memória severa). O health_check das 15:01:42 registrou m3:SSH_FALHOU(0%). Retentativas seguintes (ConnectTimeout 30/40/50 + poll de ~5min, ~7 tentativas totais) TODAS banner-timeout, gcloud=RUNNING → travamento confirmado por pressão de memória (NÃO blip — o teste blip×travada deu travada: não recuperou nas retentativas). Ação: `gcloud compute instances reset m3-exp02`. m3 voltou em ~1min (up 0min, load 0.29), Docker subiu (5 containers), run_experiment resumido via nohup/disown (exit 124 do timeout do SSH, esperado); confirmado 5/5 Up + run_procs=2 (PID 1852 real). Dados íntegros (tasks.json idempotente: m3 done 4.699→4.705, NÃO perdeu). NOTA custo-reboot: m3 re-caminha 60→180→300, done pode ficar ~flat 1-3h. m1/m2/m4 saudáveis, sem ação. Ciclo 15:01:42 (m3=0%) SUPERSEDED por este 15:12:28 limpo. Total 19.089/21.681 = 88,0% (+120 vs 14:01). Deltas: m1 +36 (4.860), m2 +29 (4.605), m3 +6 (4.705, pós-reboot), m4 +49 (4.919, 95,6%). Ordem: m4 95,6% > m1 87,7% > m3 86,4% > m2 83,1%. Reboots acumulados: 17.

## Ciclo 2026-07-10 16:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·287 | 1.180 | 31 | 1.211 | 1.386 | 87,4 % |
| exp_01 | Up | 462·462·300 | 1.176 | 48 | 1.224 | 1.386 | 88,3 % |
| exp_02 | Up | 462·462·294 | 1.178 | 40 | 1.218 | 1.386 | 87,9 % |
| exp_03 | Up | 462·462·315 | 1.197 | 42 | 1.239 | 1.386 | 89,4 % |
| **total** | — | 1.848·1.848·1.196 | **4.731** | **161** | **4.892** | **5.544** | **88,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·288 | 1.168 | 44 | 1.212 | 1.386 | 87,4 % |
| exp_01 | Up | 462·462·292 | 1.174 | 42 | 1.216 | 1.386 | 87,7 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·200 | 1.087 | 37 | 1.124 | 1.386 | 81,1 % |
| **total** | — | 1.848·1.848·926 | **4.460** | **162** | **4.622** | **5.544** | **83,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.158 | 40 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.143 | 38 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.528** | **177** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·383 | 1.185 | 56 | 1.241 | 1.287 | 96,4 % |
| exp_01 | Up | 429·429·368 | 1.196 | 30 | 1.226 | 1.287 | 95,3 % |
| exp_02 | Up | 429·429·384 | 1.192 | 50 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·379 | 1.192 | 45 | 1.237 | 1.287 | 96,1 % |
| **total** | — | 1.716·1.716·1.514 | **4.765** | **181** | **4.946** | **5.148** | **96,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.196 | 4.731 | 161 | 4.892 | 5.544 | 88,2 % |
| m2 | RUNNING | 1.848·1.848·926 | 4.460 | 162 | 4.622 | 5.544 | 83,4 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.528 | 177 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.514 | 4.765 | 181 | 4.946 | 5.148 | 96,1 % |
| **TOTAL** | — | — | **18.484** | **681** | **19.165** | **21.681** | **88,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:145, install/adb:16
- m2: erros → emulator/boot:143, install/adb:19
- m3: erros → emulator/boot:155, install/adb:22
- m4: erros → emulator/boot:168, install/adb:13

## Ciclo 2026-07-10 16:01:51 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·287 | 1.180 | 31 | 1.211 | 1.386 | 87,4 % |
| exp_01 | Up | 462·462·300 | 1.176 | 48 | 1.224 | 1.386 | 88,3 % |
| exp_02 | Up | 462·462·295 | 1.179 | 40 | 1.219 | 1.386 | 88,0 % |
| exp_03 | Up | 462·462·316 | 1.198 | 42 | 1.240 | 1.386 | 89,5 % |
| **total** | — | 1.848·1.848·1.198 | **4.733** | **161** | **4.894** | **5.544** | **88,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·288 | 1.168 | 44 | 1.212 | 1.386 | 87,4 % |
| exp_01 | Up | 462·462·293 | 1.175 | 42 | 1.217 | 1.386 | 87,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·200 | 1.087 | 37 | 1.124 | 1.386 | 81,1 % |
| **total** | — | 1.848·1.848·927 | **4.461** | **162** | **4.623** | **5.544** | **83,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.158 | 40 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.143 | 38 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.528** | **177** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·383 | 1.185 | 56 | 1.241 | 1.287 | 96,4 % |
| exp_01 | Up | 429·429·368 | 1.196 | 30 | 1.226 | 1.287 | 95,3 % |
| exp_02 | Up | 429·429·384 | 1.192 | 50 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·379 | 1.192 | 45 | 1.237 | 1.287 | 96,1 % |
| **total** | — | 1.716·1.716·1.514 | **4.765** | **181** | **4.946** | **5.148** | **96,1 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.198 | 4.733 | 161 | 4.894 | 5.544 | 88,3 % |
| m2 | RUNNING | 1.848·1.848·927 | 4.461 | 162 | 4.623 | 5.544 | 83,4 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.528 | 177 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.514 | 4.765 | 181 | 4.946 | 5.148 | 96,1 % |
| **TOTAL** | — | — | **18.487** | **681** | **19.168** | **21.681** | **88,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:145, install/adb:16
- m2: erros → emulator/boot:143, install/adb:19
- m3: erros → emulator/boot:155, install/adb:22
- m4: erros → emulator/boot:168, install/adb:13

**Ações (16:01 local):** Ciclo de rotina. Cron local ativo. Varredura SSH: as 4 VMs na 1ª tentativa, 5/5 Up, run_procs=2, cron OOM funcionando. m3 recuperada do reboot #17 (up 51min, containers up 34min, rodando bem). Sem SSH_FALHOU no cron.out 16:00. Nenhuma ação manual necessária. Total 19.168/21.681 = 88,4% (+79 vs 15:12, intervalo 49min + m3 flat). Deltas: m1 +34 (4.894), m2 +18 (4.623), m3 +0 (4.705, FLAT pós-reboot re-caminhando 60→180→300, esperado por 1-3h), m4 +27 (4.946, 96,1%). Ordem: m4 96,1% > m1 88,3% > m3 86,4% > m2 83,4%. Reboots acumulados: 17 (nenhum novo).

## Ciclo 2026-07-10 16:15:07 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·289 | 1.182 | 31 | 1.213 | 1.386 | 87,5 % |
| exp_01 | Up | 462·462·302 | 1.178 | 48 | 1.226 | 1.386 | 88,5 % |
| exp_02 | Up | 462·462·297 | 1.181 | 40 | 1.221 | 1.386 | 88,1 % |
| exp_03 | Up | 462·462·318 | 1.200 | 42 | 1.242 | 1.386 | 89,6 % |
| **total** | — | 1.848·1.848·1.206 | **4.741** | **161** | **4.902** | **5.544** | **88,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·290 | 1.170 | 44 | 1.214 | 1.386 | 87,6 % |
| exp_01 | Up | 462·462·295 | 1.177 | 42 | 1.219 | 1.386 | 88,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·203 | 1.089 | 38 | 1.127 | 1.386 | 81,3 % |
| **total** | — | 1.848·1.848·934 | **4.467** | **163** | **4.630** | **5.544** | **83,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.158 | 40 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.143 | 38 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.528** | **177** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·385 | 1.187 | 56 | 1.243 | 1.287 | 96,6 % |
| exp_01 | Up | 429·429·370 | 1.198 | 30 | 1.228 | 1.287 | 95,4 % |
| exp_02 | Up | 429·429·384 | 1.192 | 50 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·381 | 1.194 | 45 | 1.239 | 1.287 | 96,3 % |
| **total** | — | 1.716·1.716·1.520 | **4.771** | **181** | **4.952** | **5.148** | **96,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.206 | 4.741 | 161 | 4.902 | 5.544 | 88,4 % |
| m2 | RUNNING | 1.848·1.848·934 | 4.467 | 163 | 4.630 | 5.544 | 83,5 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.528 | 177 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.520 | 4.771 | 181 | 4.952 | 5.148 | 96,2 % |
| **TOTAL** | — | — | **18.507** | **682** | **19.189** | **21.681** | **88,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:145, install/adb:16
- m2: erros → emulator/boot:144, install/adb:19
- m3: erros → emulator/boot:155, install/adb:22
- m4: erros → emulator/boot:168, install/adb:13

**Ações (16:15 local):** Ciclo de rotina. Cron local ativo. Varredura SSH (sequencial, todas na 1ª tentativa): m1/m2/m4 5/5 Up run_procs=2; m3 exp_00 Exited(137) 4min → `docker start exp_00` IMEDIATO → 5/5 Up. m3 up 1:04 (pós-reboot #17), re-caminhando 60→180→300 → done FLAT esperado até ~18:12. m4 load 15-min=35 (cauda 300, exp_02 recém-restartado pelo cron OOM). Cron OOM das VMs funcionando (m1 17:00, m2 17:30, m3 19:10, m4 19:00 UTC). Total 19.189/21.681 = 88,5% (+21 vs 16:01). Deltas: m1 +8 (4.902), m2 +7 (4.630), m3 +0 (4.705, FLAT re-caminhada esperada), m4 +6 (4.952, 96,2%). Ordem: m4 96,2% > m1 88,4% > m3 86,4% > m2 83,5%. Reboots acumulados: 17 (nenhum novo). Faltam ~2.492 tasks.

## Ciclo 2026-07-10 17:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·296 | 1.189 | 31 | 1.220 | 1.386 | 88,0 % |
| exp_01 | Up | 462·462·313 | 1.187 | 50 | 1.237 | 1.386 | 89,2 % |
| exp_02 | Up | 462·462·306 | 1.187 | 43 | 1.230 | 1.386 | 88,7 % |
| exp_03 | Up | 462·462·325 | 1.207 | 42 | 1.249 | 1.386 | 90,1 % |
| **total** | — | 1.848·1.848·1.240 | **4.770** | **166** | **4.936** | **5.544** | **89,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·298 | 1.177 | 45 | 1.222 | 1.386 | 88,2 % |
| exp_01 | Up | 462·462·304 | 1.183 | 45 | 1.228 | 1.386 | 88,6 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·210 | 1.096 | 38 | 1.134 | 1.386 | 81,8 % |
| **total** | — | 1.848·1.848·958 | **4.487** | **167** | **4.654** | **5.544** | **83,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.159 | 39 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.145 | 36 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.531** | **174** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·393 | 1.194 | 57 | 1.251 | 1.287 | 97,2 % |
| exp_01 | Up | 429·429·377 | 1.205 | 30 | 1.235 | 1.287 | 96,0 % |
| exp_02 | Up | 429·429·384 | 1.193 | 49 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·389 | 1.202 | 45 | 1.247 | 1.287 | 96,9 % |
| **total** | — | 1.716·1.716·1.543 | **4.794** | **181** | **4.975** | **5.148** | **96,6 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.240 | 4.770 | 166 | 4.936 | 5.544 | 89,0 % |
| m2 | RUNNING | 1.848·1.848·958 | 4.487 | 167 | 4.654 | 5.544 | 83,9 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.531 | 174 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.543 | 4.794 | 181 | 4.975 | 5.148 | 96,6 % |
| **TOTAL** | — | — | **18.582** | **688** | **19.270** | **21.681** | **88,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:148, install/adb:18
- m2: erros → emulator/boot:148, install/adb:19
- m3: erros → emulator/boot:152, install/adb:22
- m4: erros → emulator/boot:168, install/adb:13

## Ciclo 2026-07-10 17:03:49 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·297 | 1.190 | 31 | 1.221 | 1.386 | 88,1 % |
| exp_01 | Up | 462·462·313 | 1.187 | 50 | 1.237 | 1.386 | 89,2 % |
| exp_02 | Up | 462·462·306 | 1.187 | 43 | 1.230 | 1.386 | 88,7 % |
| exp_03 | Up | 462·462·326 | 1.208 | 42 | 1.250 | 1.386 | 90,2 % |
| **total** | — | 1.848·1.848·1.242 | **4.772** | **166** | **4.938** | **5.544** | **89,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·299 | 1.177 | 46 | 1.223 | 1.386 | 88,2 % |
| exp_01 | Up | 462·462·305 | 1.184 | 45 | 1.229 | 1.386 | 88,7 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·210 | 1.096 | 38 | 1.134 | 1.386 | 81,8 % |
| **total** | — | 1.848·1.848·960 | **4.488** | **168** | **4.656** | **5.544** | **84,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.159 | 39 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.145 | 36 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.095 | 31 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.531** | **174** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·394 | 1.195 | 57 | 1.252 | 1.287 | 97,3 % |
| exp_01 | Up | 429·429·378 | 1.206 | 30 | 1.236 | 1.287 | 96,0 % |
| exp_02 | Up | 429·429·384 | 1.193 | 49 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·390 | 1.203 | 45 | 1.248 | 1.287 | 97,0 % |
| **total** | — | 1.716·1.716·1.546 | **4.797** | **181** | **4.978** | **5.148** | **96,7 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.242 | 4.772 | 166 | 4.938 | 5.544 | 89,1 % |
| m2 | RUNNING | 1.848·1.848·960 | 4.488 | 168 | 4.656 | 5.544 | 84,0 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.531 | 174 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.546 | 4.797 | 181 | 4.978 | 5.148 | 96,7 % |
| **TOTAL** | — | — | **18.588** | **689** | **19.277** | **21.681** | **88,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:148, install/adb:18
- m2: erros → emulator/boot:149, install/adb:19
- m3: erros → emulator/boot:152, install/adb:22
- m4: erros → emulator/boot:168, install/adb:13

**Ações (17:03 local):** Ciclo de rotina. Cron local ativo. Varredura SSH (sequencial, todas na 1ª tentativa): m1/m2/m4 5/5 Up run_procs=2; m3 exp_00 Exited(137) ~1min (churn recorrente neste container) → `docker start exp_00` IMEDIATO → 5/5 Up. m3 up 1:53 (pós-reboot #17), ainda re-caminhando → done FLAT esperado até ~18:12. m4 load 15-min=30 (cauda 300). Cron OOM das VMs funcionando (m1 17:00, m3 20:00, m4 19:00 UTC). Total 19.277/21.681 = 88,9% (+88 vs 16:15). Deltas: m1 +36 (4.938), m2 +26 (4.656), m3 +0 (4.705, FLAT re-caminhada esperada), m4 +26 (4.978, 96,7%). Ordem: m4 96,7% > m1 89,1% > m3 86,4% > m2 84,0%. Reboots acumulados: 17 (nenhum novo). Faltam ~2.404 tasks.

## Ciclo 2026-07-10 18:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·309 | 1.198 | 35 | 1.233 | 1.386 | 89,0 % |
| exp_01 | Up | 462·462·322 | 1.196 | 50 | 1.246 | 1.386 | 89,9 % |
| exp_02 | Up | 462·462·316 | 1.196 | 44 | 1.240 | 1.386 | 89,5 % |
| exp_03 | Up | 462·462·337 | 1.216 | 45 | 1.261 | 1.386 | 91,0 % |
| **total** | — | 1.848·1.848·1.284 | **4.806** | **174** | **4.980** | **5.544** | **89,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·308 | 1.185 | 47 | 1.232 | 1.386 | 88,9 % |
| exp_01 | Up | 462·462·314 | 1.193 | 45 | 1.238 | 1.386 | 89,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·220 | 1.105 | 39 | 1.144 | 1.386 | 82,5 % |
| **total** | — | 1.848·1.848·988 | **4.514** | **170** | **4.684** | **5.544** | **84,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.160 | 38 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.146 | 35 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.096 | 30 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.534** | **171** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·404 | 1.202 | 60 | 1.262 | 1.287 | 98,1 % |
| exp_01 | Up | 429·429·387 | 1.215 | 30 | 1.245 | 1.287 | 96,7 % |
| exp_02 | Up | 429·429·384 | 1.196 | 46 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·400 | 1.211 | 47 | 1.258 | 1.287 | 97,7 % |
| **total** | — | 1.716·1.716·1.575 | **4.824** | **183** | **5.007** | **5.148** | **97,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.284 | 4.806 | 174 | 4.980 | 5.544 | 89,8 % |
| m2 | RUNNING | 1.848·1.848·988 | 4.514 | 170 | 4.684 | 5.544 | 84,5 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.534 | 171 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.575 | 4.824 | 183 | 5.007 | 5.148 | 97,3 % |
| **TOTAL** | — | — | **18.678** | **698** | **19.376** | **21.681** | **89,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:154, install/adb:20
- m2: erros → emulator/boot:150, install/adb:20
- m3: erros → emulator/boot:150, install/adb:21
- m4: erros → emulator/boot:171, install/adb:12

## Ciclo 2026-07-10 18:03:36 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·309 | 1.198 | 35 | 1.233 | 1.386 | 89,0 % |
| exp_01 | Up | 462·462·322 | 1.196 | 50 | 1.246 | 1.386 | 89,9 % |
| exp_02 | Up | 462·462·317 | 1.197 | 44 | 1.241 | 1.386 | 89,5 % |
| exp_03 | Up | 462·462·337 | 1.216 | 45 | 1.261 | 1.386 | 91,0 % |
| **total** | — | 1.848·1.848·1.285 | **4.807** | **174** | **4.981** | **5.544** | **89,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·309 | 1.186 | 47 | 1.233 | 1.386 | 89,0 % |
| exp_01 | Up | 462·462·314 | 1.193 | 45 | 1.238 | 1.386 | 89,3 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·221 | 1.106 | 39 | 1.145 | 1.386 | 82,6 % |
| **total** | — | 1.848·1.848·990 | **4.516** | **170** | **4.686** | **5.544** | **84,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.160 | 38 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·257 | 1.146 | 35 | 1.181 | 1.386 | 85,2 % |
| exp_02 | Up | 462·462·276 | 1.132 | 68 | 1.200 | 1.386 | 86,6 % |
| exp_03 | Up | 429·429·268 | 1.096 | 30 | 1.126 | 1.287 | 87,5 % |
| **total** | — | 1.815·1.815·1.075 | **4.534** | **171** | **4.705** | **5.445** | **86,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·405 | 1.203 | 60 | 1.263 | 1.287 | 98,1 % |
| exp_01 | Up | 429·429·387 | 1.215 | 30 | 1.245 | 1.287 | 96,7 % |
| exp_02 | Up | 429·429·384 | 1.196 | 46 | 1.242 | 1.287 | 96,5 % |
| exp_03 | Up | 429·429·401 | 1.212 | 47 | 1.259 | 1.287 | 97,8 % |
| **total** | — | 1.716·1.716·1.577 | **4.826** | **183** | **5.009** | **5.148** | **97,3 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.285 | 4.807 | 174 | 4.981 | 5.544 | 89,8 % |
| m2 | RUNNING | 1.848·1.848·990 | 4.516 | 170 | 4.686 | 5.544 | 84,5 % |
| m3 | RUNNING | 1.815·1.815·1.075 | 4.534 | 171 | 4.705 | 5.445 | 86,4 % |
| m4 | RUNNING | 1.716·1.716·1.577 | 4.826 | 183 | 5.009 | 5.148 | 97,3 % |
| **TOTAL** | — | — | **18.683** | **698** | **19.381** | **21.681** | **89,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:154, install/adb:20
- m2: erros → emulator/boot:150, install/adb:20
- m3: erros → emulator/boot:150, install/adb:21
- m4: erros → emulator/boot:171, install/adb:12

**Ações (18:03 local):** Ciclo de rotina, SEM ação manual. Cron local ativo. Varredura SSH (sequencial, todas na 1ª tentativa): as 4 VMs 5/5 Up, run_procs=2, nenhum container Exited. m3 up 2:53 (pós-reboot #17), containers recriados há 54min — re-caminhando, done ainda FLAT (esperado até ~18:12). Cron OOM das VMs funcionando. Total 19.381/21.681 = 89,4% (+104 vs 17:03). Deltas: m1 +43 (4.981), m2 +30 (4.686), m3 +0 (4.705, FLAT re-caminhada — deve retomar ~18:12; VIGIAR no próximo ciclo), m4 +31 (5.009, 97,3%). Ordem: m4 97,3% > m1 89,8% > m3 86,4% > m2 84,5%. Reboots acumulados: 17. Faltam ~2.300 tasks.

## Ciclo 2026-07-10 19:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·319 | 1.207 | 36 | 1.243 | 1.386 | 89,7 % |
| exp_01 | Up | 462·462·333 | 1.204 | 53 | 1.257 | 1.386 | 90,7 % |
| exp_02 | Up | 462·462·327 | 1.206 | 45 | 1.251 | 1.386 | 90,3 % |
| exp_03 | Up | 462·462·348 | 1.226 | 46 | 1.272 | 1.386 | 91,8 % |
| **total** | — | 1.848·1.848·1.327 | **4.843** | **180** | **5.023** | **5.544** | **90,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·319 | 1.195 | 48 | 1.243 | 1.386 | 89,7 % |
| exp_01 | Up | 462·462·324 | 1.203 | 45 | 1.248 | 1.386 | 90,0 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·230 | 1.115 | 39 | 1.154 | 1.386 | 83,3 % |
| **total** | — | 1.848·1.848·1.019 | **4.544** | **171** | **4.715** | **5.544** | **85,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.166 | 32 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·263 | 1.153 | 34 | 1.187 | 1.386 | 85,6 % |
| exp_02 | Up | 462·462·277 | 1.136 | 65 | 1.201 | 1.386 | 86,7 % |
| exp_03 | Up | 429·429·269 | 1.101 | 26 | 1.127 | 1.287 | 87,6 % |
| **total** | — | 1.815·1.815·1.083 | **4.556** | **157** | **4.713** | **5.445** | **86,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·413 | 1.211 | 60 | 1.271 | 1.287 | 98,8 % |
| exp_01 | Up | 429·429·396 | 1.224 | 30 | 1.254 | 1.287 | 97,4 % |
| exp_02 | Up | 429·429·392 | 1.204 | 46 | 1.250 | 1.287 | 97,1 % |
| exp_03 | Up | 429·429·410 | 1.220 | 48 | 1.268 | 1.287 | 98,5 % |
| **total** | — | 1.716·1.716·1.611 | **4.859** | **184** | **5.043** | **5.148** | **98,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.327 | 4.843 | 180 | 5.023 | 5.544 | 90,6 % |
| m2 | RUNNING | 1.848·1.848·1.019 | 4.544 | 171 | 4.715 | 5.544 | 85,0 % |
| m3 | RUNNING | 1.815·1.815·1.083 | 4.556 | 157 | 4.713 | 5.445 | 86,6 % |
| m4 | RUNNING | 1.716·1.716·1.611 | 4.859 | 184 | 5.043 | 5.148 | 98,0 % |
| **TOTAL** | — | — | **18.802** | **692** | **19.494** | **21.681** | **89,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:157, install/adb:23
- m2: erros → emulator/boot:150, install/adb:21
- m3: erros → emulator/boot:147, install/adb:10
- m4: erros → emulator/boot:171, install/adb:13

## Ciclo 2026-07-10 19:03:47 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·320 | 1.208 | 36 | 1.244 | 1.386 | 89,8 % |
| exp_01 | Up | 462·462·334 | 1.205 | 53 | 1.258 | 1.386 | 90,8 % |
| exp_02 | Up | 462·462·327 | 1.206 | 45 | 1.251 | 1.386 | 90,3 % |
| exp_03 | Up | 462·462·348 | 1.226 | 46 | 1.272 | 1.386 | 91,8 % |
| **total** | — | 1.848·1.848·1.329 | **4.845** | **180** | **5.025** | **5.544** | **90,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·319 | 1.195 | 48 | 1.243 | 1.386 | 89,7 % |
| exp_01 | Up | 462·462·325 | 1.204 | 45 | 1.249 | 1.386 | 90,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·231 | 1.116 | 39 | 1.155 | 1.386 | 83,3 % |
| **total** | — | 1.848·1.848·1.021 | **4.546** | **171** | **4.717** | **5.544** | **85,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·274 | 1.167 | 31 | 1.198 | 1.386 | 86,4 % |
| exp_01 | Up | 462·462·263 | 1.153 | 34 | 1.187 | 1.386 | 85,6 % |
| exp_02 | Up | 462·462·278 | 1.137 | 65 | 1.202 | 1.386 | 86,7 % |
| exp_03 | Up | 429·429·269 | 1.101 | 26 | 1.127 | 1.287 | 87,6 % |
| **total** | — | 1.815·1.815·1.084 | **4.558** | **156** | **4.714** | **5.445** | **86,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·414 | 1.212 | 60 | 1.272 | 1.287 | 98,8 % |
| exp_01 | Up | 429·429·397 | 1.224 | 31 | 1.255 | 1.287 | 97,5 % |
| exp_02 | Up | 429·429·392 | 1.204 | 46 | 1.250 | 1.287 | 97,1 % |
| exp_03 | Up | 429·429·411 | 1.221 | 48 | 1.269 | 1.287 | 98,6 % |
| **total** | — | 1.716·1.716·1.614 | **4.861** | **185** | **5.046** | **5.148** | **98,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.329 | 4.845 | 180 | 5.025 | 5.544 | 90,6 % |
| m2 | RUNNING | 1.848·1.848·1.021 | 4.546 | 171 | 4.717 | 5.544 | 85,1 % |
| m3 | RUNNING | 1.815·1.815·1.084 | 4.558 | 156 | 4.714 | 5.445 | 86,6 % |
| m4 | RUNNING | 1.716·1.716·1.614 | 4.861 | 185 | 5.046 | 5.148 | 98,0 % |
| **TOTAL** | — | — | **18.810** | **692** | **19.502** | **21.681** | **89,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:157, install/adb:23
- m2: erros → emulator/boot:150, install/adb:21
- m3: erros → emulator/boot:147, install/adb:9
- m4: erros → emulator/boot:172, install/adb:13

**Ações (19:03 local):** Ciclo de rotina, SEM ação manual. Cron local ativo. Varredura SSH (sequencial, todas na 1ª tentativa): as 4 VMs 5/5 Up, run_procs=2, nenhum container Exited. m3 SAIU do FLAT (re-caminhada pós-reboot #17 concluída, agora progredindo — cron 86%→87%). Cron OOM das VMs funcionando. Total 19.502/21.681 = 89,9% (+121 vs 18:03). Deltas: m1 +44 (5.025), m2 +31 (4.717), m3 +9 (4.714, RETOMOU), m4 +37 (5.046, 98,0%). Ordem: m4 98,0% > m1 90,6% > m3 86,6% > m2 85,1%. m4 quase completa (98%, cauda 300 final). Reboots acumulados: 17 (nenhum novo). Faltam ~2.179 tasks.

## Ciclo 2026-07-10 20:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·329 | 1.217 | 36 | 1.253 | 1.386 | 90,4 % |
| exp_01 | Up | 462·462·341 | 1.211 | 54 | 1.265 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·338 | 1.214 | 48 | 1.262 | 1.386 | 91,1 % |
| exp_03 | Up | 462·462·357 | 1.235 | 46 | 1.281 | 1.386 | 92,4 % |
| **total** | — | 1.848·1.848·1.365 | **4.877** | **184** | **5.061** | **5.544** | **91,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·329 | 1.204 | 49 | 1.253 | 1.386 | 90,4 % |
| exp_01 | Up | 462·462·334 | 1.211 | 47 | 1.258 | 1.386 | 90,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·242 | 1.124 | 42 | 1.166 | 1.386 | 84,1 % |
| **total** | — | 1.848·1.848·1.051 | **4.570** | **177** | **4.747** | **5.544** | **85,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·281 | 1.174 | 31 | 1.205 | 1.386 | 86,9 % |
| exp_01 | Up | 462·462·275 | 1.161 | 38 | 1.199 | 1.386 | 86,5 % |
| exp_02 | Up | 462·462·287 | 1.146 | 65 | 1.211 | 1.386 | 87,4 % |
| exp_03 | Up | 429·429·278 | 1.110 | 26 | 1.136 | 1.287 | 88,3 % |
| **total** | — | 1.815·1.815·1.121 | **4.591** | **160** | **4.751** | **5.445** | **87,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·423 | 1.221 | 60 | 1.281 | 1.287 | 99,5 % |
| exp_01 | Up | 429·429·406 | 1.231 | 33 | 1.264 | 1.287 | 98,2 % |
| exp_02 | Up | 429·429·403 | 1.212 | 49 | 1.261 | 1.287 | 98,0 % |
| exp_03 | Up | 429·429·420 | 1.229 | 49 | 1.278 | 1.287 | 99,3 % |
| **total** | — | 1.716·1.716·1.652 | **4.893** | **191** | **5.084** | **5.148** | **98,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.365 | 4.877 | 184 | 5.061 | 5.544 | 91,3 % |
| m2 | RUNNING | 1.848·1.848·1.051 | 4.570 | 177 | 4.747 | 5.544 | 85,6 % |
| m3 | RUNNING | 1.815·1.815·1.121 | 4.591 | 160 | 4.751 | 5.445 | 87,3 % |
| m4 | RUNNING | 1.716·1.716·1.652 | 4.893 | 191 | 5.084 | 5.148 | 98,8 % |
| **TOTAL** | — | — | **18.931** | **712** | **19.643** | **21.681** | **90,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:160, install/adb:24
- m2: erros → emulator/boot:155, install/adb:22
- m3: erros → emulator/boot:151, install/adb:9
- m4: erros → emulator/boot:177, install/adb:14

## Ciclo 2026-07-10 20:03:35 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·329 | 1.217 | 36 | 1.253 | 1.386 | 90,4 % |
| exp_01 | Up | 462·462·341 | 1.211 | 54 | 1.265 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·338 | 1.214 | 48 | 1.262 | 1.386 | 91,1 % |
| exp_03 | Up | 462·462·358 | 1.236 | 46 | 1.282 | 1.386 | 92,5 % |
| **total** | — | 1.848·1.848·1.366 | **4.878** | **184** | **5.062** | **5.544** | **91,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·331 | 1.205 | 50 | 1.255 | 1.386 | 90,5 % |
| exp_01 | Up | 462·462·335 | 1.212 | 47 | 1.259 | 1.386 | 90,8 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·242 | 1.124 | 42 | 1.166 | 1.386 | 84,1 % |
| **total** | — | 1.848·1.848·1.054 | **4.572** | **178** | **4.750** | **5.544** | **85,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·282 | 1.175 | 31 | 1.206 | 1.386 | 87,0 % |
| exp_01 | Up | 462·462·275 | 1.161 | 38 | 1.199 | 1.386 | 86,5 % |
| exp_02 | Up | 462·462·287 | 1.146 | 65 | 1.211 | 1.386 | 87,4 % |
| exp_03 | Up | 429·429·279 | 1.111 | 26 | 1.137 | 1.287 | 88,3 % |
| **total** | — | 1.815·1.815·1.123 | **4.593** | **160** | **4.753** | **5.445** | **87,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·423 | 1.221 | 60 | 1.281 | 1.287 | 99,5 % |
| exp_01 | Up | 429·429·407 | 1.232 | 33 | 1.265 | 1.287 | 98,3 % |
| exp_02 | Up | 429·429·403 | 1.212 | 49 | 1.261 | 1.287 | 98,0 % |
| exp_03 | Up | 429·429·421 | 1.230 | 49 | 1.279 | 1.287 | 99,4 % |
| **total** | — | 1.716·1.716·1.654 | **4.895** | **191** | **5.086** | **5.148** | **98,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.366 | 4.878 | 184 | 5.062 | 5.544 | 91,3 % |
| m2 | RUNNING | 1.848·1.848·1.054 | 4.572 | 178 | 4.750 | 5.544 | 85,7 % |
| m3 | RUNNING | 1.815·1.815·1.123 | 4.593 | 160 | 4.753 | 5.445 | 87,3 % |
| m4 | RUNNING | 1.716·1.716·1.654 | 4.895 | 191 | 5.086 | 5.148 | 98,8 % |
| **TOTAL** | — | — | **18.938** | **713** | **19.651** | **21.681** | **90,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:160, install/adb:24
- m2: erros → emulator/boot:156, install/adb:22
- m3: erros → emulator/boot:151, install/adb:9
- m4: erros → emulator/boot:177, install/adb:14

**Ações (20:03 local):** Ciclo de rotina, SEM ação manual. Cron local ativo. Varredura SSH (sequencial, todas na 1ª tentativa): as 4 VMs 5/5 Up, run_procs=2, nenhum container Exited (m1/exp_01 auto-restartado pelo cron 22:50 UTC, já Up 13min). Cron OOM das VMs funcionando. Total 19.651/21.681 = 90,6% (+149 vs 19:03) — cruzou 90%. Deltas: m1 +37 (5.062), m2 +33 (4.750), m3 +39 (4.753), m4 +40 (5.086, 98,8%). Ordem: m4 98,8% > m1 91,3% > m3 87,3% > m2 85,7% (m3 ultrapassou m2). m4 quase completa (98,8%). Reboots acumulados: 17 (nenhum novo). Faltam ~2.030 tasks.

## Ciclo 2026-07-10 21:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·340 | 1.225 | 39 | 1.264 | 1.386 | 91,2 % |
| exp_01 | Up | 462·462·341 | 1.212 | 53 | 1.265 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·349 | 1.225 | 48 | 1.273 | 1.386 | 91,8 % |
| exp_03 | Up | 462·462·369 | 1.244 | 49 | 1.293 | 1.386 | 93,3 % |
| **total** | — | 1.848·1.848·1.399 | **4.906** | **189** | **5.095** | **5.544** | **91,9 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·341 | 1.213 | 52 | 1.265 | 1.386 | 91,3 % |
| exp_01 | Up | 462·462·344 | 1.221 | 47 | 1.268 | 1.386 | 91,5 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·252 | 1.134 | 42 | 1.176 | 1.386 | 84,8 % |
| **total** | — | 1.848·1.848·1.083 | **4.599** | **180** | **4.779** | **5.544** | **86,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·291 | 1.184 | 31 | 1.215 | 1.386 | 87,7 % |
| exp_01 | Up | 462·462·284 | 1.170 | 38 | 1.208 | 1.386 | 87,2 % |
| exp_02 | Up | 462·462·296 | 1.155 | 65 | 1.220 | 1.386 | 88,0 % |
| exp_03 | Up | 429·429·288 | 1.120 | 26 | 1.146 | 1.287 | 89,0 % |
| **total** | — | 1.815·1.815·1.159 | **4.629** | **160** | **4.789** | **5.445** | **88,0 %** |

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.399 | 4.906 | 189 | 5.095 | 5.544 | 91,9 % |
| m2 | RUNNING | 1.848·1.848·1.083 | 4.599 | 180 | 4.779 | 5.544 | 86,2 % |
| m3 | RUNNING | 1.815·1.815·1.159 | 4.629 | 160 | 4.789 | 5.445 | 88,0 % |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **14.134** | **529** | **14.663** | **16.533** | **88,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:165, install/adb:24
- m2: erros → emulator/boot:158, install/adb:22
- m3: erros → emulator/boot:151, install/adb:9
- m4: SSH inacessível — ssh timeout (sem ação)

## Ciclo 2026-07-10 21:10:41 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·342 | 1.227 | 39 | 1.266 | 1.386 | 91,3 % |
| exp_01 | Up | 462·462·341 | 1.213 | 52 | 1.265 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·351 | 1.227 | 48 | 1.275 | 1.386 | 92,0 % |
| exp_03 | Up | 462·462·371 | 1.246 | 49 | 1.295 | 1.386 | 93,4 % |
| **total** | — | 1.848·1.848·1.405 | **4.913** | **188** | **5.101** | **5.544** | **92,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·342 | 1.214 | 52 | 1.266 | 1.386 | 91,3 % |
| exp_01 | Up | 462·462·346 | 1.223 | 47 | 1.270 | 1.386 | 91,6 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·253 | 1.135 | 42 | 1.177 | 1.386 | 84,9 % |
| **total** | — | 1.848·1.848·1.087 | **4.603** | **180** | **4.783** | **5.544** | **86,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·293 | 1.186 | 31 | 1.217 | 1.386 | 87,8 % |
| exp_01 | Up | 462·462·286 | 1.172 | 38 | 1.210 | 1.386 | 87,3 % |
| exp_02 | Up | 462·462·300 | 1.156 | 68 | 1.224 | 1.386 | 88,3 % |
| exp_03 | Up | 429·429·289 | 1.121 | 26 | 1.147 | 1.287 | 89,1 % |
| **total** | — | 1.815·1.815·1.168 | **4.635** | **163** | **4.798** | **5.445** | **88,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.226 | 61 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.237 | 33 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.217 | 49 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.234 | 49 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.914** | **192** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.405 | 4.913 | 188 | 5.101 | 5.544 | 92,0 % |
| m2 | RUNNING | 1.848·1.848·1.087 | 4.603 | 180 | 4.783 | 5.544 | 86,3 % |
| m3 | RUNNING | 1.815·1.815·1.168 | 4.635 | 163 | 4.798 | 5.445 | 88,1 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.914 | 192 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.065** | **723** | **19.788** | **21.681** | **91,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:164, install/adb:24
- m2: erros → emulator/boot:158, install/adb:22
- m3: erros → emulator/boot:154, install/adb:9
- m4: erros → emulator/boot:177, install/adb:15

**Ações (21:03→21:10 local):** m4 TRAVADA (SSH_FALHOU no cron 21:00; banner timeout persistente em 8 tentativas: ConnectTimeout 20/30/40/50 + poll 4×; gcloud=RUNNING) → travamento confirmado → **reboot #18** (gcloud compute instances reset m4-exp02). SSH voltou em ~5min (up 0min), Docker subiu (containers Exited 255 esperado), RESUME disparado (exit 124 normal) → confirmado 5/5 Up + run_procs=2. m1/m2/m3 saudáveis 5/5 Up run_procs=2 na 1ª tentativa. Total 19.788/21.681 = 91,3% (+137 vs 20:03). Deltas: m1 +39 (5.101), m2 +33 (4.783), m3 +45 (4.798), m4 +20 (5.106, 99,2% — dados íntegros pós-reboot; exp_00 100,0%). Ordem: m4 99,2% > m1 92,0% > m3 88,1% > m2 86,3%. **ATENÇÃO próximo ciclo:** m4 agora re-caminhando 60→180→300 pós-reboot #18 → done FLAT esperado por 1-3h (~até 23:10); NÃO rebootar por isso. Reboots acumulados: 18. Faltam ~1.893 tasks.

## Ciclo 2026-07-10 21:49:20 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·348 | 1.233 | 39 | 1.272 | 1.386 | 91,8 % |
| exp_01 | Up | 462·462·341 | 1.216 | 49 | 1.265 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·357 | 1.233 | 48 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·377 | 1.252 | 49 | 1.301 | 1.386 | 93,9 % |
| **total** | — | 1.848·1.848·1.423 | **4.934** | **185** | **5.119** | **5.544** | **92,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·348 | 1.220 | 52 | 1.272 | 1.386 | 91,8 % |
| exp_01 | Up | 462·462·352 | 1.229 | 47 | 1.276 | 1.386 | 92,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·260 | 1.142 | 42 | 1.184 | 1.386 | 85,4 % |
| **total** | — | 1.848·1.848·1.106 | **4.622** | **180** | **4.802** | **5.544** | **86,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·300 | 1.190 | 34 | 1.224 | 1.386 | 88,3 % |
| exp_01 | Up | 462·462·292 | 1.178 | 38 | 1.216 | 1.386 | 87,7 % |
| exp_02 | Up | 462·462·307 | 1.162 | 69 | 1.231 | 1.386 | 88,8 % |
| exp_03 | Up | 429·429·296 | 1.128 | 26 | 1.154 | 1.287 | 89,7 % |
| **total** | — | 1.815·1.815·1.195 | **4.658** | **167** | **4.825** | **5.445** | **88,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.227 | 60 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.237 | 33 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.218 | 48 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.234 | 49 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.916** | **190** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.423 | 4.934 | 185 | 5.119 | 5.544 | 92,3 % |
| m2 | RUNNING | 1.848·1.848·1.106 | 4.622 | 180 | 4.802 | 5.544 | 86,6 % |
| m3 | RUNNING | 1.815·1.815·1.195 | 4.658 | 167 | 4.825 | 5.445 | 88,6 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.916 | 190 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.130** | **722** | **19.852** | **21.681** | **91,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:163, install/adb:22
- m2: erros → emulator/boot:158, install/adb:22
- m3: erros → emulator/boot:156, install/adb:11
- m4: erros → emulator/boot:173, install/adb:17

**Ações (21:49 local):** Varredura SSH: 4 VMs vivas, run_procs=2 em todas. **(a)** m4 exp_01 Exited(137)/OOM (3s atrás; cron da VM já havia restartado 00:40 UTC, re-OOMou) → `docker start exp_01` → 5/5 Up. **(b)** m2 exp_02 diagnosticado HUNG: último log 01:57 UTC (~23h atrás), congelado em "Installing com.sakethh.linkora_50.apk"; container "Up" mas processo morto → cron OOM (exit-137-only) NÃO cobre → explica os 77,2% (146/passada-300) parados 2+ ciclos → `docker restart exp_02` (idempotente; entrypoint reiniciou "waiting 60s") → destravado. Total 19.852/21.681 = **91,6%** (+64 vs 21:10). Deltas: m1 +18 (5.119, 92,3%), m2 +19 (4.802, 86,6% — exp_02 agora deve subir), m3 +27 (4.825, 88,6%), m4 +0 (5.106, 99,2% — FLAT esperado, re-caminhando pós-reboot #18 até ~23:10; NÃO rebootar). Ordem: m4 > m1 > m3 > m2. Reboots acumulados: 18. Faltam ~1.829 tasks.

## Ciclo 2026-07-10 22:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·350 | 1.235 | 39 | 1.274 | 1.386 | 91,9 % |
| exp_01 | Up | 462·462·342 | 1.218 | 48 | 1.266 | 1.386 | 91,3 % |
| exp_02 | Up | 462·462·359 | 1.235 | 48 | 1.283 | 1.386 | 92,6 % |
| exp_03 | Up | 462·462·378 | 1.253 | 49 | 1.302 | 1.386 | 93,9 % |
| **total** | — | 1.848·1.848·1.429 | **4.941** | **184** | **5.125** | **5.544** | **92,4 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·350 | 1.222 | 52 | 1.274 | 1.386 | 91,9 % |
| exp_01 | Up | 462·462·353 | 1.230 | 47 | 1.277 | 1.386 | 92,1 % |
| exp_02 | Up | 462·462·146 | 1.031 | 39 | 1.070 | 1.386 | 77,2 % |
| exp_03 | Up | 462·462·261 | 1.143 | 42 | 1.185 | 1.386 | 85,5 % |
| **total** | — | 1.848·1.848·1.110 | **4.626** | **180** | **4.806** | **5.544** | **86,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·302 | 1.192 | 34 | 1.226 | 1.386 | 88,5 % |
| exp_01 | Up | 462·462·294 | 1.180 | 38 | 1.218 | 1.386 | 87,9 % |
| exp_02 | Up | 462·462·309 | 1.164 | 69 | 1.233 | 1.386 | 89,0 % |
| exp_03 | Up | 429·429·298 | 1.129 | 27 | 1.156 | 1.287 | 89,8 % |
| **total** | — | 1.815·1.815·1.203 | **4.665** | **168** | **4.833** | **5.445** | **88,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.228 | 59 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.237 | 33 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.218 | 48 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.234 | 49 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.917** | **189** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.429 | 4.941 | 184 | 5.125 | 5.544 | 92,4 % |
| m2 | RUNNING | 1.848·1.848·1.110 | 4.626 | 180 | 4.806 | 5.544 | 86,7 % |
| m3 | RUNNING | 1.815·1.815·1.203 | 4.665 | 168 | 4.833 | 5.445 | 88,8 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.917 | 189 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.149** | **721** | **19.870** | **21.681** | **91,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:163, install/adb:21
- m2: erros → emulator/boot:157, install/adb:23
- m3: erros → emulator/boot:157, install/adb:11
- m4: erros → emulator/boot:173, install/adb:16

## Ciclo 2026-07-10 22:54:42 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·359 | 1.244 | 39 | 1.283 | 1.386 | 92,6 % |
| exp_01 | Up | 462·462·350 | 1.226 | 48 | 1.274 | 1.386 | 91,9 % |
| exp_02 | Up | 462·462·369 | 1.242 | 51 | 1.293 | 1.386 | 93,3 % |
| exp_03 | Up | 462·462·388 | 1.262 | 50 | 1.312 | 1.386 | 94,7 % |
| **total** | — | 1.848·1.848·1.466 | **4.974** | **188** | **5.162** | **5.544** | **93,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·359 | 1.230 | 53 | 1.283 | 1.386 | 92,6 % |
| exp_01 | Up | 462·462·362 | 1.239 | 47 | 1.286 | 1.386 | 92,8 % |
| exp_02 | Up | 462·462·149 | 1.035 | 38 | 1.073 | 1.386 | 77,4 % |
| exp_03 | Up | 462·462·272 | 1.151 | 45 | 1.196 | 1.386 | 86,3 % |
| **total** | — | 1.848·1.848·1.142 | **4.655** | **183** | **4.838** | **5.544** | **87,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·311 | 1.201 | 34 | 1.235 | 1.386 | 89,1 % |
| exp_01 | Up | 462·462·303 | 1.186 | 41 | 1.227 | 1.386 | 88,5 % |
| exp_02 | Up | 462·462·318 | 1.171 | 71 | 1.242 | 1.386 | 89,6 % |
| exp_03 | Up | 429·429·308 | 1.137 | 29 | 1.166 | 1.287 | 90,6 % |
| **total** | — | 1.815·1.815·1.240 | **4.695** | **175** | **4.870** | **5.445** | **89,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.229 | 58 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.238 | 32 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.222 | 44 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.234 | 49 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.923** | **183** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.466 | 4.974 | 188 | 5.162 | 5.544 | 93,1 % |
| m2 | RUNNING | 1.848·1.848·1.142 | 4.655 | 183 | 4.838 | 5.544 | 87,3 % |
| m3 | RUNNING | 1.815·1.815·1.240 | 4.695 | 175 | 4.870 | 5.445 | 89,4 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.923 | 183 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.247** | **729** | **19.976** | **21.681** | **92,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:166, install/adb:22
- m2: erros → emulator/boot:161, install/adb:22
- m3: erros → emulator/boot:163, install/adb:12
- m4: erros → emulator/boot:168, install/adb:15

**Ações (22:54 local):** Ciclo de rotina, SEM ação manual. Cron local ativo; cron 22:00 recuperou m4 (RUNNING 99%, pós-reboot #18). Varredura SSH: 4 VMs saudáveis 5/5 Up, run_procs=2, nenhum container Exited. **m2 exp_02 CONFIRMADO destravado** ("Up About an hour" — restart 21:49 funcionou; contribuiu +36 no total da m2). m4 load 41 (boot-storm da re-caminhada, normal). Total 19.976/21.681 = **92,1%** (+124 vs 21:49). Deltas: m1 +43 (5.162, 93,1%), m2 +36 (4.838, 87,3%), m3 +45 (4.870, 89,4%), m4 +0 (5.106, 99,2% — FLAT esperado, re-caminhando pós-reboot #18 até ~23:10; NÃO rebootar). Ordem: m4 > m1 > m3 > m2. Reboots acumulados: 18. Faltam ~1.705 tasks.

## Ciclo 2026-07-10 23:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·360 | 1.245 | 39 | 1.284 | 1.386 | 92,6 % |
| exp_01 | Up | 462·462·351 | 1.227 | 48 | 1.275 | 1.386 | 92,0 % |
| exp_02 | Up | 462·462·370 | 1.243 | 51 | 1.294 | 1.386 | 93,4 % |
| exp_03 | Up | 462·462·389 | 1.263 | 50 | 1.313 | 1.386 | 94,7 % |
| **total** | — | 1.848·1.848·1.470 | **4.978** | **188** | **5.166** | **5.544** | **93,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·360 | 1.231 | 53 | 1.284 | 1.386 | 92,6 % |
| exp_01 | Up | 462·462·364 | 1.240 | 48 | 1.288 | 1.386 | 92,9 % |
| exp_02 | Up | 462·462·150 | 1.036 | 38 | 1.074 | 1.386 | 77,5 % |
| exp_03 | Up | 462·462·273 | 1.151 | 46 | 1.197 | 1.386 | 86,4 % |
| **total** | — | 1.848·1.848·1.147 | **4.658** | **185** | **4.843** | **5.544** | **87,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·312 | 1.202 | 34 | 1.236 | 1.386 | 89,2 % |
| exp_01 | Up | 462·462·304 | 1.187 | 41 | 1.228 | 1.386 | 88,6 % |
| exp_02 | Up | 462·462·319 | 1.172 | 71 | 1.243 | 1.386 | 89,7 % |
| exp_03 | Up | 429·429·309 | 1.138 | 29 | 1.167 | 1.287 | 90,7 % |
| **total** | — | 1.815·1.815·1.244 | **4.699** | **175** | **4.874** | **5.445** | **89,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.230 | 57 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.238 | 32 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.222 | 44 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.234 | 49 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.924** | **182** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.470 | 4.978 | 188 | 5.166 | 5.544 | 93,2 % |
| m2 | RUNNING | 1.848·1.848·1.147 | 4.658 | 185 | 4.843 | 5.544 | 87,4 % |
| m3 | RUNNING | 1.815·1.815·1.244 | 4.699 | 175 | 4.874 | 5.445 | 89,5 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.924 | 182 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.259** | **730** | **19.989** | **21.681** | **92,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:166, install/adb:22
- m2: erros → emulator/boot:162, install/adb:23
- m3: erros → emulator/boot:163, install/adb:12
- m4: erros → emulator/boot:167, install/adb:15

## Ciclo 2026-07-10 23:58:36 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·370 | 1.252 | 42 | 1.294 | 1.386 | 93,4 % |
| exp_01 | Up | 462·462·361 | 1.237 | 48 | 1.285 | 1.386 | 92,7 % |
| exp_02 | Up | 462·462·381 | 1.254 | 51 | 1.305 | 1.386 | 94,2 % |
| exp_03 | Up | 462·462·401 | 1.271 | 54 | 1.325 | 1.386 | 95,6 % |
| **total** | — | 1.848·1.848·1.513 | **5.014** | **195** | **5.209** | **5.544** | **94,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·371 | 1.239 | 56 | 1.295 | 1.386 | 93,4 % |
| exp_01 | Up | 462·462·376 | 1.249 | 51 | 1.300 | 1.386 | 93,8 % |
| exp_02 | Up | 462·462·161 | 1.047 | 38 | 1.085 | 1.386 | 78,3 % |
| exp_03 | Up | 462·462·283 | 1.161 | 46 | 1.207 | 1.386 | 87,1 % |
| **total** | — | 1.848·1.848·1.191 | **4.696** | **191** | **4.887** | **5.544** | **88,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·321 | 1.211 | 34 | 1.245 | 1.386 | 89,8 % |
| exp_01 | Up | 462·462·313 | 1.196 | 41 | 1.237 | 1.386 | 89,2 % |
| exp_02 | Up | 462·462·335 | 1.185 | 74 | 1.259 | 1.386 | 90,8 % |
| exp_03 | Up | 429·429·318 | 1.147 | 29 | 1.176 | 1.287 | 91,4 % |
| **total** | — | 1.815·1.815·1.287 | **4.739** | **178** | **4.917** | **5.445** | **90,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.231 | 56 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.240 | 30 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.223 | 43 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.236 | 47 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.930** | **176** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.513 | 5.014 | 195 | 5.209 | 5.544 | 94,0 % |
| m2 | RUNNING | 1.848·1.848·1.191 | 4.696 | 191 | 4.887 | 5.544 | 88,1 % |
| m3 | RUNNING | 1.815·1.815·1.287 | 4.739 | 178 | 4.917 | 5.445 | 90,3 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.930 | 176 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.379** | **740** | **20.119** | **21.681** | **92,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:172, install/adb:23
- m2: erros → emulator/boot:166, install/adb:25
- m3: erros → emulator/boot:166, install/adb:12
- m4: erros → emulator/boot:160, install/adb:16

**Ações (23:58 local):** Ciclo de rotina, SEM ação manual. Cron local ativo; cron 23:00 saudável nas 4 VMs. Varredura SSH: 4 VMs 5/5 Up, run_procs=2, nenhum container Exited. m4 (up 2:49, pós-reboot #18) containers "Up ~1h" = re-caminhando passadas 60→180→300 (done FLAT esperado; só ~42 tasks restam, finaliza ao reencontrar a 300). Total 20.119/21.681 = **92,8%** (+143 vs 22:54) — cruzou 20k. Deltas: m1 +47 (5.209, 94,0%), m2 +49 (4.887, 88,1%), m3 +47 (4.917, 90,3% — cruzou 90%), m4 +0 (5.106, 99,2% — FLAT esperado, re-caminhada). Ordem: m4 > m1 > m3 > m2. Reboots acumulados: 18. Faltam ~1.562 tasks.

## Ciclo 2026-07-11 00:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·370 | 1.252 | 42 | 1.294 | 1.386 | 93,4 % |
| exp_01 | Up | 462·462·361 | 1.237 | 48 | 1.285 | 1.386 | 92,7 % |
| exp_02 | Up | 462·462·381 | 1.254 | 51 | 1.305 | 1.386 | 94,2 % |
| exp_03 | Up | 462·462·401 | 1.271 | 54 | 1.325 | 1.386 | 95,6 % |
| **total** | — | 1.848·1.848·1.513 | **5.014** | **195** | **5.209** | **5.544** | **94,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·371 | 1.239 | 56 | 1.295 | 1.386 | 93,4 % |
| exp_01 | Up | 462·462·376 | 1.249 | 51 | 1.300 | 1.386 | 93,8 % |
| exp_02 | Up | 462·462·161 | 1.047 | 38 | 1.085 | 1.386 | 78,3 % |
| exp_03 | Up | 462·462·283 | 1.161 | 46 | 1.207 | 1.386 | 87,1 % |
| **total** | — | 1.848·1.848·1.191 | **4.696** | **191** | **4.887** | **5.544** | **88,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·321 | 1.211 | 34 | 1.245 | 1.386 | 89,8 % |
| exp_01 | Up | 462·462·314 | 1.197 | 41 | 1.238 | 1.386 | 89,3 % |
| exp_02 | Up | 462·462·335 | 1.185 | 74 | 1.259 | 1.386 | 90,8 % |
| exp_03 | Up | 429·429·318 | 1.147 | 29 | 1.176 | 1.287 | 91,4 % |
| **total** | — | 1.815·1.815·1.288 | **4.740** | **178** | **4.918** | **5.445** | **90,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.231 | 56 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.240 | 30 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.223 | 43 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.236 | 47 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.930** | **176** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.513 | 5.014 | 195 | 5.209 | 5.544 | 94,0 % |
| m2 | RUNNING | 1.848·1.848·1.191 | 4.696 | 191 | 4.887 | 5.544 | 88,1 % |
| m3 | RUNNING | 1.815·1.815·1.288 | 4.740 | 178 | 4.918 | 5.445 | 90,3 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.930 | 176 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.380** | **740** | **20.120** | **21.681** | **92,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:172, install/adb:23
- m2: erros → emulator/boot:166, install/adb:25
- m3: erros → emulator/boot:166, install/adb:12
- m4: erros → emulator/boot:160, install/adb:16

**Correção/investigação m4 (00:05 local, resposta a "precisa de reboot?"):** Investigado a fundo — **m4 NÃO precisa de reboot, está VIVA na cauda da passada 300.** DESCOBERTA DE FUSO: os logs dos containers estão em **UTC−3**, mas o host da VM roda em **UTC** → offset de 3h. Relógio VM = 03:04 UTC; último log de cada container m4 = 00:04 (UTC−3) = **~1s de idade**. Todos os 4 containers logando em tempo real: exp_01 Coverage 3.99%→4.03% (ferramenta ativa), exp_03 coverage processing, exp_00/exp_02 booting emulador. done flat (5.106) porque restam só **42 tasks na passada 300** + **136 ERROS pass-300 sendo re-tentados** (retries consomem tempo mas re-erram → não incrementam done). Cauda pesada esperada + retries de erro, NÃO hang. Reboot seria o PIOR movimento (re-caminha 60→180→300, perde a cauda). LIÇÃO PERMANENTE: ao ler docker logs de qualquer VM, LEMBRAR que container=UTC−3 e host=UTC (3h de offset) — NÃO confundir log "3h atrás" com hung; comparar com `date` DENTRO do mesmo SSH. Os 136 erros pass-300 da m4 são candidatos ao resíduo não-recuperável (FASE 2 retry): se não virarem COMPLETED após retries, documentar e reportar.

## Ciclo 2026-07-11 00:07:30 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·371 | 1.253 | 42 | 1.295 | 1.386 | 93,4 % |
| exp_01 | Up | 462·462·362 | 1.238 | 48 | 1.286 | 1.386 | 92,8 % |
| exp_02 | Up | 462·462·384 | 1.256 | 52 | 1.308 | 1.386 | 94,4 % |
| exp_03 | Up | 462·462·402 | 1.272 | 54 | 1.326 | 1.386 | 95,7 % |
| **total** | — | 1.848·1.848·1.519 | **5.019** | **196** | **5.215** | **5.544** | **94,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·373 | 1.241 | 56 | 1.297 | 1.386 | 93,6 % |
| exp_01 | Up | 462·462·378 | 1.251 | 51 | 1.302 | 1.386 | 93,9 % |
| exp_02 | Up | 462·462·162 | 1.048 | 38 | 1.086 | 1.386 | 78,4 % |
| exp_03 | Up | 462·462·284 | 1.162 | 46 | 1.208 | 1.386 | 87,2 % |
| **total** | — | 1.848·1.848·1.197 | **4.702** | **191** | **4.893** | **5.544** | **88,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·323 | 1.213 | 34 | 1.247 | 1.386 | 90,0 % |
| exp_01 | Up | 462·462·315 | 1.198 | 41 | 1.239 | 1.386 | 89,4 % |
| exp_02 | Up | 462·462·336 | 1.186 | 74 | 1.260 | 1.386 | 90,9 % |
| exp_03 | Up | 429·429·319 | 1.148 | 29 | 1.177 | 1.287 | 91,5 % |
| **total** | — | 1.815·1.815·1.293 | **4.745** | **178** | **4.923** | **5.445** | **90,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.231 | 56 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.240 | 30 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.223 | 43 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.236 | 47 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.930** | **176** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.519 | 5.019 | 196 | 5.215 | 5.544 | 94,1 % |
| m2 | RUNNING | 1.848·1.848·1.197 | 4.702 | 191 | 4.893 | 5.544 | 88,3 % |
| m3 | RUNNING | 1.815·1.815·1.293 | 4.745 | 178 | 4.923 | 5.445 | 90,4 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.930 | 176 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.396** | **741** | **20.137** | **21.681** | **92,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:172, install/adb:24
- m2: erros → emulator/boot:166, install/adb:25
- m3: erros → emulator/boot:166, install/adb:12
- m4: erros → emulator/boot:161, install/adb:15

## Ciclo 2026-07-11 00:26:26 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·375 | 1.256 | 43 | 1.299 | 1.386 | 93,7 % |
| exp_01 | Up | 462·462·366 | 1.239 | 51 | 1.290 | 1.386 | 93,1 % |
| exp_02 | Up | 462·462·387 | 1.259 | 52 | 1.311 | 1.386 | 94,6 % |
| exp_03 | Up | 462·462·405 | 1.275 | 54 | 1.329 | 1.386 | 95,9 % |
| **total** | — | 1.848·1.848·1.533 | **5.029** | **200** | **5.229** | **5.544** | **94,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·376 | 1.244 | 56 | 1.300 | 1.386 | 93,8 % |
| exp_01 | Up | 462·462·381 | 1.254 | 51 | 1.305 | 1.386 | 94,2 % |
| exp_02 | Up | 462·462·166 | 1.051 | 39 | 1.090 | 1.386 | 78,6 % |
| exp_03 | Up | 462·462·287 | 1.165 | 46 | 1.211 | 1.386 | 87,4 % |
| **total** | — | 1.848·1.848·1.210 | **4.714** | **192** | **4.906** | **5.544** | **88,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·326 | 1.216 | 34 | 1.250 | 1.386 | 90,2 % |
| exp_01 | Up | 462·462·318 | 1.201 | 41 | 1.242 | 1.386 | 89,6 % |
| exp_02 | Up | 462·462·340 | 1.189 | 75 | 1.264 | 1.386 | 91,2 % |
| exp_03 | Up | 429·429·322 | 1.151 | 29 | 1.180 | 1.287 | 91,7 % |
| **total** | — | 1.815·1.815·1.306 | **4.757** | **179** | **4.936** | **5.445** | **90,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.232 | 55 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·412 | 1.241 | 29 | 1.270 | 1.287 | 98,7 % |
| exp_02 | Up | 429·429·408 | 1.223 | 43 | 1.266 | 1.287 | 98,4 % |
| exp_03 | Up | 429·429·425 | 1.238 | 45 | 1.283 | 1.287 | 99,7 % |
| **total** | — | 1.716·1.716·1.674 | **4.934** | **172** | **5.106** | **5.148** | **99,2 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.533 | 5.029 | 200 | 5.229 | 5.544 | 94,3 % |
| m2 | RUNNING | 1.848·1.848·1.210 | 4.714 | 192 | 4.906 | 5.544 | 88,5 % |
| m3 | RUNNING | 1.815·1.815·1.306 | 4.757 | 179 | 4.936 | 5.445 | 90,7 % |
| m4 | RUNNING | 1.716·1.716·1.674 | 4.934 | 172 | 5.106 | 5.148 | 99,2 % |
| **TOTAL** | — | — | **19.434** | **743** | **20.177** | **21.681** | **93,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:25
- m2: erros → emulator/boot:167, install/adb:25
- m3: erros → emulator/boot:166, install/adb:13
- m4: erros → emulator/boot:162, install/adb:10

**Ações (00:26 local):** Varredura SSH ativa nas 4 VMs — todas VIVAS, 5/5 containers Up cada, `pgrep=2` (real+wrapper) em todas, nenhum SSH_FALHOU. OOM restarts no restart_cron.out são antigos/tratados pelo cron */10 (m1 exp_01 22:50, m2 exp_03 17:30, m3 exp_03 20:00, m4 exp_01 01:30 UTC). m4 uptime `up 3:17` = reboot #18 já conhecido (não novo), recuperou e voltou à cauda p300. Deltas 00:07→00:26 (19min): m1 +14 · m2 +13 · m3 +13 · m4 +0 · TOTAL +40 (20.137→20.177 = 93,1%). Delta-anomalia m4 = cauda-viva já investigada (42 tasks + 172 retries p300), NÃO stall → sem reboot. m2 exp_02 seguindo lento (78,6%) mas subindo, sem hang. Nenhuma ação corretiva necessária. Próximo wakeup: 01:00 local.

## Ciclo 2026-07-11 01:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·382 | 1.262 | 44 | 1.306 | 1.386 | 94,2 % |
| exp_01 | Up | 462·462·372 | 1.245 | 51 | 1.296 | 1.386 | 93,5 % |
| exp_02 | Up | 462·462·392 | 1.264 | 52 | 1.316 | 1.386 | 94,9 % |
| exp_03 | Up | 462·462·410 | 1.280 | 54 | 1.334 | 1.386 | 96,2 % |
| **total** | — | 1.848·1.848·1.556 | **5.051** | **201** | **5.252** | **5.544** | **94,7 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·381 | 1.249 | 56 | 1.305 | 1.386 | 94,2 % |
| exp_01 | Up | 462·462·386 | 1.259 | 51 | 1.310 | 1.386 | 94,5 % |
| exp_02 | Up | 462·462·172 | 1.054 | 42 | 1.096 | 1.386 | 79,1 % |
| exp_03 | Up | 462·462·293 | 1.170 | 47 | 1.217 | 1.386 | 87,8 % |
| **total** | — | 1.848·1.848·1.232 | **4.732** | **196** | **4.928** | **5.544** | **88,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·335 | 1.220 | 39 | 1.259 | 1.386 | 90,8 % |
| exp_01 | Up | 462·462·323 | 1.206 | 41 | 1.247 | 1.386 | 90,0 % |
| exp_02 | Up | 462·462·345 | 1.194 | 75 | 1.269 | 1.386 | 91,6 % |
| exp_03 | Up | 429·429·328 | 1.157 | 29 | 1.186 | 1.287 | 92,2 % |
| **total** | — | 1.815·1.815·1.331 | **4.777** | **184** | **4.961** | **5.445** | **91,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·416 | 1.246 | 28 | 1.274 | 1.287 | 99,0 % |
| exp_02 | Up | 429·429·411 | 1.227 | 42 | 1.269 | 1.287 | 98,6 % |
| exp_03 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.685 | **4.949** | **168** | **5.117** | **5.148** | **99,4 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.556 | 5.051 | 201 | 5.252 | 5.544 | 94,7 % |
| m2 | RUNNING | 1.848·1.848·1.232 | 4.732 | 196 | 4.928 | 5.544 | 88,9 % |
| m3 | RUNNING | 1.815·1.815·1.331 | 4.777 | 184 | 4.961 | 5.445 | 91,1 % |
| m4 | RUNNING | 1.716·1.716·1.685 | 4.949 | 168 | 5.117 | 5.148 | 99,4 % |
| **TOTAL** | — | — | **19.509** | **749** | **20.258** | **21.681** | **93,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:26
- m2: erros → emulator/boot:169, install/adb:27
- m3: erros → emulator/boot:169, install/adb:15
- m4: erros → emulator/boot:161, install/adb:7

**Decisão FASE 2 / retry (00:40 local, autorização do usuário):** NÃO iniciar retry enquanto a run da VM estiver viva. Deixar `run_experiment.sh <vm>` TERMINAR por completo (sair natural, pgrep=0 sem reboot/OOM). Retry só APÓS a VM inteira esgotar a FASE 1, e **UMA VM POR VEZ** (sem mop-up paralelo entre VMs). Quando a 1ª VM concluir, PARAR e REPORTAR antes de disparar retry (decidir formato: por-container sequencial — alivia oversubscrição de memória, root cause dos boot errors — vs re-disparo VM-level). Contexto técnico: `feito`=ok+err (100% = tudo terminal, NÃO tudo COMPLETED); resume re-roda ERROR pois `_skip_completed_tasks` pula só COMPLETED (confirmado empiricamente: m4 exp_00 err 56→55 entre 00:07-00:26). Para VMs no teto de feito, monitorar Δok (não Δfeito).

## Ciclo 2026-07-11 02:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·386 | 1.266 | 44 | 1.310 | 1.386 | 94,5 % |
| exp_01 | Up | 462·462·376 | 1.249 | 51 | 1.300 | 1.386 | 93,8 % |
| exp_02 | Up | 462·462·398 | 1.268 | 54 | 1.322 | 1.386 | 95,4 % |
| exp_03 | Up | 462·462·414 | 1.284 | 54 | 1.338 | 1.386 | 96,5 % |
| **total** | — | 1.848·1.848·1.574 | **5.067** | **203** | **5.270** | **5.544** | **95,1 %** |

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·426 | 1.256 | 28 | 1.284 | 1.287 | 99,8 % |
| exp_02 | Up | 429·429·422 | 1.238 | 42 | 1.280 | 1.287 | 99,5 % |
| exp_03 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.706 | **4.970** | **168** | **5.138** | **5.148** | **99,8 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.574 | 5.067 | 203 | 5.270 | 5.544 | 95,1 % |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.706 | 4.970 | 168 | 5.138 | 5.148 | 99,8 % |
| **TOTAL** | — | — | **10.037** | **371** | **10.408** | **10.692** | **97,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:177, install/adb:26
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: SSH inacessível — ssh timeout (sem ação)
- m4: erros → emulator/boot:165, install/adb:3

## Ciclo 2026-07-11 03:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·352 | 1.236 | 40 | 1.276 | 1.386 | 92,1 % |
| exp_01 | Up | 462·462·337 | 1.218 | 43 | 1.261 | 1.386 | 91,0 % |
| exp_02 | Up | 462·462·365 | 1.209 | 80 | 1.289 | 1.386 | 93,0 % |
| exp_03 | Up | 429·429·348 | 1.174 | 32 | 1.206 | 1.287 | 93,7 % |
| **total** | — | 1.815·1.815·1.402 | **4.837** | **195** | **5.032** | **5.445** | **92,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | RUNNING | 1.815·1.815·1.402 | 4.837 | 195 | 5.032 | 5.445 | 92,4 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.979 | 169 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **9.816** | **364** | **10.180** | **10.593** | **96,1 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: erros → emulator/boot:176, install/adb:18, timeout:1
- m4: erros → emulator/boot:164, install/adb:5
- m4: container exp_00 docker=gone (ok=1234 fail=53)
- m4: container exp_01 docker=gone (ok=1259 fail=28)
- m4: container exp_02 docker=gone (ok=1243 fail=44)
- m4: container exp_03 docker=gone (ok=1243 fail=44)

## Ciclo 2026-07-11 04:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.979 | 169 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → emulator/boot:164, install/adb:5
- m4: container exp_00 docker=gone (ok=1234 fail=53)
- m4: container exp_01 docker=gone (ok=1259 fail=28)
- m4: container exp_02 docker=gone (ok=1243 fail=44)
- m4: container exp_03 docker=gone (ok=1243 fail=44)

## Ciclo 2026-07-11 05:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.979 | 169 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → emulator/boot:164, install/adb:5
- m4: container exp_00 docker=gone (ok=1234 fail=53)
- m4: container exp_01 docker=gone (ok=1259 fail=28)
- m4: container exp_02 docker=gone (ok=1243 fail=44)
- m4: container exp_03 docker=gone (ok=1243 fail=44)

## Ciclo 2026-07-11 06:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.979 | 169 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → emulator/boot:164, install/adb:5
- m4: container exp_00 docker=gone (ok=1234 fail=53)
- m4: container exp_01 docker=gone (ok=1259 fail=28)
- m4: container exp_02 docker=gone (ok=1243 fail=44)
- m4: container exp_03 docker=gone (ok=1243 fail=44)

## Ciclo 2026-07-11 07:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.979 | 169 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **4.979** | **169** | **5.148** | **5.148** | **100,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ssh timeout (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: erros → emulator/boot:164, install/adb:5
- m4: container exp_00 docker=gone (ok=1234 fail=53)
- m4: container exp_01 docker=gone (ok=1259 fail=28)
- m4: container exp_02 docker=gone (ok=1243 fail=44)
- m4: container exp_03 docker=gone (ok=1243 fail=44)

## Ciclo 2026-07-11 07:13:31 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.288 | 43 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.279 | 55 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.303 | 59 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.321 | 59 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.191** | **216** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.296 | 50 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.108 | 45 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.197 | 50 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.879** | **204** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.271 | 43 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.242 | 42 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.209 | 36 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.965** | **204** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.234 | 53 | 1.287 | 1.287 | 100,0 % |
| exp_01 | exit | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.244 | 43 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.980** | **168** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.191 | 216 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.879 | 204 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.965 | 204 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.980 | 168 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.015** | **792** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:185, install/adb:29, timeout:2
- m2: erros → emulator/boot:182, install/adb:22
- m3: erros → emulator/boot:187, install/adb:16, timeout:1
- m4: erros → emulator/boot:163, install/adb:5
- m4: container exp_01 docker=exited (ok=1259 fail=28)

## INCIDENTE — monitoramento parado + recuperação (07:14 local 2026-07-11)

**FALHA DE MONITORAMENTO:** a cadeia de wakeup quebrou após ~00:40; m1/m2/m3 travaram (SSH connect-timeout, gcloud RUNNING) por volta das **04:00** e ficaram ~3h sem intervenção. O cron local registrou `SSH_FALHOU(0%)` para m1/m2/m3 nos ciclos 04:00/05:00/06:00 mas o cron só LOGA — quem age (reboot) é o wakeup, que não disparou. Detectado só às 07:04 por cobrança do usuário.

**RECUPERAÇÃO (07:05-07:14):**
- m4 havia **CONCLUÍDO a FASE 1** às 05:38:49 (run saiu limpa, `compose down`). Disparado **retry FASE 2 VM-level** (`run_experiment.sh m4`): 5 containers Up, re-caminhando p60 para varrer os 168 ERROR (skip COMPLETED). Estado real via rv_status direto: done 5148/5148, ok 4980, err 168.
- m1/m2/m3: confirmado travamento (2× connect-timeout ConnectTimeout=40, gcloud RUNNING) → **reboot** (`gcloud compute instances reset`, um por vez). Voltaram em ~1min, Docker OK, **resume disparado** em cada. pgrep=2 + 5 containers Up nas 3. Re-caminham desde p60 (idempotente).
- Sem perda de dados: tasks.json em bind-mount host sobrevive a reboot (confirmado m4 = 5148 done intacto).

**Estado pós-recuperação (07:13): TOTAL 20.807/21.681 = 96,0%** (ok 20.015, err 792). m1 97,5% · m2 91,7% · m3 94,9% · m4 100% (feito). Reboots VM acumulados: 21 (+3 neste incidente).

**LIÇÃO:** o wakeff horário É o mecanismo de ação; se a sessão terminar sem reagendar, o experimento fica cego. SEMPRE reagendar ao fim de cada ciclo. FASE 2 (retry VM-level) roda assim que os containers de uma VM terminam — NÃO é "uma VM por vez com pausa" (isso era só sobre a decisão de subir por-container, já descartada).

## Ciclo 2026-07-11 08:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.289 | 42 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.280 | 54 | 1.334 | 1.386 | 96,2 % |
| exp_02 | exit | 462·462·438 | 1.303 | 59 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.321 | 59 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.193** | **214** | **5.407** | **5.544** | **97,5 %** |

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.271 | 43 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.242 | 42 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | exit | 429·429·387 | 1.209 | 36 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.965** | **204** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.236 | 51 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.244 | 43 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.984** | **164** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.193 | 214 | 5.407 | 5.544 | 97,5 % |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.965 | 204 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.984 | 164 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **15.142** | **582** | **15.724** | **16.137** | **97,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:182, install/adb:30, timeout:2
- m1: container exp_02 docker=exited (ok=1303 fail=59)
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:185, install/adb:18, timeout:1
- m3: container exp_03 docker=exited (ok=1209 fail=36)
- m4: erros → emulator/boot:158, install/adb:6

## Ciclo 2026-07-11 08:07:18 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.289 | 42 | 1.331 | 1.386 | 96,0 % |
| exp_01 | exit | 462·462·410 | 1.280 | 54 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.303 | 59 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.321 | 59 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.193** | **214** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.296 | 50 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.108 | 45 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.197 | 50 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.879** | **204** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.271 | 43 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.242 | 42 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.209 | 36 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.965** | **204** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.236 | 51 | 1.287 | 1.287 | 100,0 % |
| exp_01 | exit | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.244 | 43 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.985** | **163** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.193 | 214 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.879 | 204 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.965 | 204 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.985 | 163 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.022** | **785** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:183, install/adb:29, timeout:2
- m1: container exp_01 docker=exited (ok=1280 fail=54)
- m2: erros → emulator/boot:182, install/adb:22
- m3: erros → emulator/boot:185, install/adb:18, timeout:1
- m4: erros → emulator/boot:157, install/adb:6
- m4: container exp_00 docker=exited (ok=1236 fail=51)
- m4: container exp_01 docker=exited (ok=1259 fail=28)

**Ações (08:07 local):** Ciclo pós-incidente. cron.out mostrou m2 SSH_FALHOU 05/06/07/08h — m2 **re-travou** após reboot 07:07 (aguentou ~53min, banner-exchange timeout = pressão de memória). Confirmado (2× ConnectTimeout=40 + gcloud RUNNING) → **reboot m2** (reset #22) + resume OK (up 0min, Docker OK, run disparado). OOM restarts: m1 exp_02, m3 exp_03, m4 exp_02 (docker start, Exited 137). m1/m3 up ~54min (reboots 07:10 ok), m4 up 10:55 (não rebootada). Δok 07:14→08:07: m1 +2 · m2 +0 · m3 +0 · m4 +5 (retry convertendo err 168→163). Baixo por churn de recuperação (m2 hung+reboot, m1/m3 re-walk p60/180). TOTAL 20.807 feito / ok 20.022 / err 785 / 96,0%. OOMs novos no health_check (m1 exp_01, m4 exp_00/01) deixados p/ cron */10. VIGIAR m2: se re-travar 3ª vez, é OOM-churn crônico daquela VM (candidata a atenção especial). Próximo wakeup 09:00.

## Ciclo 2026-07-11 09:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.290 | 41 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.284 | 50 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.304 | 58 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.321 | 59 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.199** | **208** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.296 | 50 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.110 | 43 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.200 | 47 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.884** | **199** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.271 | 43 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.243 | 41 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.210 | 35 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.967** | **202** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.236 | 51 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.987** | **161** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.199 | 208 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.884 | 199 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.967 | 202 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.987 | 161 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.037** | **770** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:179, install/adb:27, timeout:2
- m2: erros → emulator/boot:180, install/adb:19
- m3: erros → emulator/boot:184, install/adb:17, timeout:1
- m4: erros → emulator/boot:155, install/adb:6

## Ciclo 2026-07-11 09:02:35 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.290 | 41 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.284 | 50 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.304 | 58 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.321 | 59 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.199** | **208** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.296 | 50 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.110 | 43 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.200 | 47 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.884** | **199** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.271 | 43 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.243 | 41 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.210 | 35 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.967** | **202** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.236 | 51 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.987** | **161** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.199 | 208 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.884 | 199 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.967 | 202 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.987 | 161 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.037** | **770** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:180, install/adb:26, timeout:2
- m2: erros → emulator/boot:181, install/adb:18
- m3: erros → emulator/boot:183, install/adb:18, timeout:1
- m4: erros → emulator/boot:155, install/adb:6

**Ações (09:02 local):** Ciclo limpo — 4 VMs saudáveis, sem SSH_FALHOU, sem Exited(137), pgrep=2 em todas, cron.out 09:00 = 4× RUNNING. m2 NÃO re-travou (reboot 08:05 segurou; up 55min). m1/m3 up ~1:52 (reboots 07:10), m4 up 11:53 (retry rodando). Nenhuma intervenção. Δok 08:07→09:02: m1 +6 · m2 +5 · m3 +2 · m4 +2 · TOTAL +15 (err 785→770). Fase mop-up: feito no teto, retries convertendo err→completed. Completude real (só COMPLETED) 20.037/21.681 = 92,4% (faltam 770 err + 874 pendentes, maioria dos pendentes em m2 exp_02=233 que re-walk ainda não alcançou). Próximo wakeup 10:00.

## Ciclo 2026-07-11 10:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.291 | 40 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.284 | 50 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.305 | 57 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.323 | 57 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.203** | **204** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.296 | 50 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.111 | 42 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.201 | 46 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.886** | **197** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.272 | 42 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.243 | 41 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.212 | 33 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.970** | **199** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.262 | 25 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.992** | **156** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.203 | 204 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.886 | 197 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.970 | 199 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.992 | 156 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.051** | **756** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:180, install/adb:22, timeout:2
- m2: erros → emulator/boot:178, install/adb:19
- m3: erros → emulator/boot:180, install/adb:18, timeout:1
- m4: erros → emulator/boot:148, install/adb:8

## Ciclo 2026-07-11 10:02:35 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·407 | 1.291 | 40 | 1.331 | 1.386 | 96,0 % |
| exp_01 | Up | 462·462·410 | 1.284 | 50 | 1.334 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·438 | 1.305 | 57 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.323 | 57 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.711 | **5.203** | **204** | **5.407** | **5.544** | **97,5 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.278 | 59 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.297 | 49 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.111 | 42 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.201 | 46 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.887** | **196** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.272 | 42 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·360 | 1.243 | 41 | 1.284 | 1.386 | 92,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.212 | 33 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.539 | **4.970** | **199** | **5.169** | **5.445** | **94,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.262 | 25 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.992** | **156** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.711 | 5.203 | 204 | 5.407 | 5.544 | 97,5 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.887 | 196 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.539 | 4.970 | 199 | 5.169 | 5.445 | 94,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.992 | 156 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.052** | **755** | **20.807** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:180, install/adb:22, timeout:2
- m2: erros → emulator/boot:177, install/adb:19
- m3: erros → emulator/boot:180, install/adb:18, timeout:1
- m4: erros → emulator/boot:148, install/adb:8

**Ações (10:02 local):** Ciclo limpo (4 VMs RUNNING, sem SSH_FALHOU/OOM pendente, pgrep=2, cron 10:00 4× OK). m2 estável (não re-travou). Δok 09:02→10:02: m1 +4 · m2 +3 · m3 +3 · m4 +5 · TOTAL +15 (err 770→755). **DIAGNÓSTICO feito-flat (3 ciclos):** investigado m2 exp_02 (maior bolso pendente, 233). RV_TIMEOUTS=180 em todos os 4 containers da m2 → ainda na PASSADA 180, não chegou à 300 (onde estão os pendentes). run.log: reboot 08:05→re-walk p60 (11:06 UTC)→p180 (11:19 UTC), ~1h45 na p180 re-rodando erros que re-falham no boot do emulador (exp_02 log ativo "Waiting for emulator to boot" — oversubscrição). feito flat = pendentes p300 não alcançados; só erros convertem. RISCO A VIGIAR: se m2 rebootar antes de chegar à p300, walk reinicia na p60 → possível livelock (pendentes nunca tentados). Não é o caso agora (m2 up 1:55 progredindo). Sem ação cabível (não mexer em config/mem, não gerenciar emulador no container). Completude real (ok) 20.052/21.681 = 92,5%. Próximo wakeup 11:00.

## Ciclo 2026-07-11 11:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·409 | 1.295 | 38 | 1.333 | 1.386 | 96,2 % |
| exp_01 | Up | 462·462·413 | 1.288 | 49 | 1.337 | 1.386 | 96,5 % |
| exp_02 | Up | 462·462·438 | 1.308 | 54 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.329 | 51 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.716 | **5.220** | **192** | **5.412** | **5.544** | **97,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.279 | 58 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.299 | 47 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.113 | 40 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.202 | 45 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.893** | **190** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.276 | 38 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·367 | 1.249 | 42 | 1.291 | 1.386 | 93,1 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·387 | 1.213 | 32 | 1.245 | 1.287 | 96,7 % |
| **total** | — | 1.815·1.815·1.546 | **4.981** | **195** | **5.176** | **5.445** | **95,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.262 | 25 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.994** | **154** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.716 | 5.220 | 192 | 5.412 | 5.544 | 97,6 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.893 | 190 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.546 | 4.981 | 195 | 5.176 | 5.445 | 95,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.994 | 154 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.088** | **731** | **20.819** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:15, timeout:2
- m2: erros → emulator/boot:173, install/adb:17
- m3: erros → emulator/boot:182, install/adb:12, timeout:1
- m4: erros → emulator/boot:148, install/adb:6

## Ciclo 2026-07-11 11:03:37 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·409 | 1.295 | 38 | 1.333 | 1.386 | 96,2 % |
| exp_01 | Up | 462·462·414 | 1.289 | 49 | 1.338 | 1.386 | 96,5 % |
| exp_02 | Up | 462·462·438 | 1.308 | 54 | 1.362 | 1.386 | 98,3 % |
| exp_03 | Up | 462·462·456 | 1.329 | 51 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.717 | **5.221** | **192** | **5.413** | **5.544** | **97,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.279 | 58 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.299 | 47 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·229 | 1.113 | 40 | 1.153 | 1.386 | 83,2 % |
| exp_03 | Up | 462·462·323 | 1.202 | 45 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.387 | **4.893** | **190** | **5.083** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·390 | 1.276 | 38 | 1.314 | 1.386 | 94,8 % |
| exp_01 | Up | 462·462·368 | 1.250 | 42 | 1.292 | 1.386 | 93,2 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·388 | 1.214 | 32 | 1.246 | 1.287 | 96,8 % |
| **total** | — | 1.815·1.815·1.548 | **4.983** | **195** | **5.178** | **5.445** | **95,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.262 | 25 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.994** | **154** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.717 | 5.221 | 192 | 5.413 | 5.544 | 97,6 % |
| m2 | RUNNING | 1.848·1.848·1.387 | 4.893 | 190 | 5.083 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.548 | 4.983 | 195 | 5.178 | 5.445 | 95,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.994 | 154 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.091** | **731** | **20.822** | **21.681** | **96,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:176, install/adb:14, timeout:2
- m2: erros → emulator/boot:174, install/adb:16
- m3: erros → emulator/boot:182, install/adb:12, timeout:1
- m4: erros → emulator/boot:148, install/adb:6

**Ações (11:03 local):** Ciclo limpo — 4 VMs RUNNING, sem SSH_FALHOU/OOM pendente, pgrep=2, cron 11:00 4× OK. CONFIRMAÇÃO do diagnóstico 10:02: **as 4 VMs agora em RV_TIMEOUTS=300** (m2 alcançou a p300, containers up 23min). feito voltou a subir (m1 +6, m3 +9 = pendentes sendo tentados). Δok 10:02→11:03: m1 +18 · m2 +6 · m3 +13 · m4 +2 · TOTAL +39 (dobro do ritmo anterior; err 755→731). Completude real (ok) 20.091/21.681 = 92,7% (faltam 731 err + 858 pendentes). m2 sem re-travar (up 2:56). Sem intervenção. Próximo wakeup 12:00.

## Ciclo 2026-07-11 12:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·419 | 1.304 | 39 | 1.343 | 1.386 | 96,9 % |
| exp_01 | Up | 462·462·423 | 1.298 | 49 | 1.347 | 1.386 | 97,2 % |
| exp_02 | Up | 462·462·442 | 1.315 | 51 | 1.366 | 1.386 | 98,6 % |
| exp_03 | Up | 462·462·456 | 1.333 | 47 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.740 | **5.250** | **186** | **5.436** | **5.544** | **98,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.281 | 56 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.300 | 46 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·230 | 1.117 | 37 | 1.154 | 1.386 | 83,3 % |
| exp_03 | Up | 462·462·323 | 1.205 | 42 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.388 | **4.903** | **181** | **5.084** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·400 | 1.283 | 41 | 1.324 | 1.386 | 95,5 % |
| exp_01 | Up | 462·462·377 | 1.259 | 42 | 1.301 | 1.386 | 93,9 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·399 | 1.223 | 34 | 1.257 | 1.287 | 97,7 % |
| **total** | — | 1.815·1.815·1.578 | **5.008** | **200** | **5.208** | **5.445** | **95,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.997** | **151** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.740 | 5.250 | 186 | 5.436 | 5.544 | 98,1 % |
| m2 | RUNNING | 1.848·1.848·1.388 | 4.903 | 181 | 5.084 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.578 | 5.008 | 200 | 5.208 | 5.445 | 95,6 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.997 | 151 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.158** | **718** | **20.876** | **21.681** | **96,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:10, timeout:1
- m2: erros → emulator/boot:167, install/adb:14
- m3: erros → emulator/boot:187, install/adb:12, timeout:1
- m4: erros → emulator/boot:145, install/adb:6

## Ciclo 2026-07-11 12:02:30 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·420 | 1.305 | 39 | 1.344 | 1.386 | 97,0 % |
| exp_01 | Up | 462·462·423 | 1.298 | 49 | 1.347 | 1.386 | 97,2 % |
| exp_02 | Up | 462·462·443 | 1.316 | 51 | 1.367 | 1.386 | 98,6 % |
| exp_03 | Up | 462·462·456 | 1.333 | 47 | 1.380 | 1.386 | 99,6 % |
| **total** | — | 1.848·1.848·1.742 | **5.252** | **186** | **5.438** | **5.544** | **98,1 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.281 | 56 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.300 | 46 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·231 | 1.118 | 37 | 1.155 | 1.386 | 83,3 % |
| exp_03 | Up | 462·462·323 | 1.205 | 42 | 1.247 | 1.386 | 90,0 % |
| **total** | — | 1.848·1.848·1.389 | **4.904** | **181** | **5.085** | **5.544** | **91,7 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·401 | 1.284 | 41 | 1.325 | 1.386 | 95,6 % |
| exp_01 | Up | 462·462·377 | 1.259 | 42 | 1.301 | 1.386 | 93,9 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·399 | 1.223 | 34 | 1.257 | 1.287 | 97,7 % |
| **total** | — | 1.815·1.815·1.579 | **5.009** | **200** | **5.209** | **5.445** | **95,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.237 | 50 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.997** | **151** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.742 | 5.252 | 186 | 5.438 | 5.544 | 98,1 % |
| m2 | RUNNING | 1.848·1.848·1.389 | 4.904 | 181 | 5.085 | 5.544 | 91,7 % |
| m3 | RUNNING | 1.815·1.815·1.579 | 5.009 | 200 | 5.209 | 5.445 | 95,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.997 | 151 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.162** | **718** | **20.880** | **21.681** | **96,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:10, timeout:1
- m2: erros → emulator/boot:167, install/adb:14
- m3: erros → emulator/boot:187, install/adb:12, timeout:1
- m4: erros → emulator/boot:144, install/adb:7

**Ações (12:02 local):** Ciclo limpo — 4 VMs RUNNING na p300, sem SSH_FALHOU/OOM pendente, pgrep=2, cron 12:00 4× OK. Δok 11:03→12:02: m1 +31 · m2 +11 · m3 +26 · m4 +3 · TOTAL +71 (melhor ritmo; err 731→718). Aceleração sustentada (+15→+39→+71) com as 4 na p300. m2 exp_02 destravou os pendentes (feito 1.153→1.155, p300 229→231). Completude real (ok) 20.162/21.681 = 93,0% (faltam 718 err + 801 pendentes). m2 sem re-travar (up 3:55). Sem intervenção. Próximo wakeup 13:00.

## Ciclo 2026-07-11 12:48:48 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·428 | 1.312 | 40 | 1.352 | 1.386 | 97,5 % |
| exp_01 | Up | 462·462·432 | 1.304 | 52 | 1.356 | 1.386 | 97,8 % |
| exp_02 | Up | 462·462·451 | 1.323 | 52 | 1.375 | 1.386 | 99,2 % |
| exp_03 | Up | 462·462·460 | 1.340 | 44 | 1.384 | 1.386 | 99,9 % |
| **total** | — | 1.848·1.848·1.771 | **5.279** | **188** | **5.467** | **5.544** | **98,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·413 | 1.284 | 53 | 1.337 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·422 | 1.304 | 42 | 1.346 | 1.386 | 97,1 % |
| exp_02 | Up | 462·462·240 | 1.123 | 41 | 1.164 | 1.386 | 84,0 % |
| exp_03 | Up | 462·462·328 | 1.211 | 41 | 1.252 | 1.386 | 90,3 % |
| **total** | — | 1.848·1.848·1.403 | **4.922** | **177** | **5.099** | **5.544** | **92,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·408 | 1.291 | 41 | 1.332 | 1.386 | 96,1 % |
| exp_01 | Up | 462·462·385 | 1.267 | 42 | 1.309 | 1.386 | 94,4 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·407 | 1.231 | 34 | 1.265 | 1.287 | 98,3 % |
| **total** | — | 1.815·1.815·1.602 | **5.032** | **200** | **5.232** | **5.445** | **96,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.238 | 49 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.998** | **150** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.771 | 5.279 | 188 | 5.467 | 5.544 | 98,6 % |
| m2 | RUNNING | 1.848·1.848·1.403 | 4.922 | 177 | 5.099 | 5.544 | 92,0 % |
| m3 | RUNNING | 1.815·1.815·1.602 | 5.032 | 200 | 5.232 | 5.445 | 96,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.998 | 150 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.231** | **715** | **20.946** | **21.681** | **96,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:177, install/adb:11
- m2: erros → emulator/boot:168, install/adb:9
- m3: erros → emulator/boot:187, install/adb:12, timeout:1
- m4: erros → emulator/boot:142, install/adb:8
- m4: container exp_00 docker=gone (ok=1238 fail=49)
- m4: container exp_01 docker=gone (ok=1264 fail=23)
- m4: container exp_02 docker=gone (ok=1248 fail=39)
- m4: container exp_03 docker=gone (ok=1248 fail=39)

**Ações (12:49 local):**
- Varredura SSH: m1/m2/m3 saudáveis (5/5 Up, passada p300, pgrep real=1 + wrapper, load ativo 6-24). Nenhum SSH_FALHOU nos últimos 4 ciclos do cron.
- **m4 concluiu FASE 2** (2º walk): `=== experimento concluído 2026-07-11 15:11:10 UTC ===` (12:11 local), concluido=2, compose down limpo, VM ociosa (load 0.00, remaining=0, err=150). **Disparado retry VM-level FASE 2** às 12:49 (PID 783762 `/bin/bash ./scripts/run_experiment.sh m4` confirmado). Re-roda os 150 ERROR (pula COMPLETED).
- **Caracterização da cauda (achado)**: 704 dos 715 err (98,5%) são da tool `monkey` — m1=185, m2=176, m3=193, m4=150. As outras 10 tools estão ~100% COMPLETED em m4 (468 cada). Monkey falha ~30-40% (categoria emulator/boot), resíduo determinístico que re-falha a cada walk (m4: 151→150 no walk anterior). Só 11 err não-monkey em todo o experimento. A cauda de completude é essencialmente monkey.
- Δok desde 12:02: TOTAL +69 (m1 +27, m2 +18, m3 +23, m4 +1). ok real 20.162→20.231 (93,3%).
- Reagendado wakeup para 13:00 (próxima hora cheia).

## Ciclo 2026-07-11 13:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.313 | 43 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.325 | 52 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.286** | **191** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·414 | 1.285 | 53 | 1.338 | 1.386 | 96,5 % |
| exp_01 | Up | 462·462·423 | 1.305 | 42 | 1.347 | 1.386 | 97,2 % |
| exp_02 | Up | 462·462·242 | 1.125 | 41 | 1.166 | 1.386 | 84,1 % |
| exp_03 | Up | 462·462·330 | 1.213 | 41 | 1.254 | 1.386 | 90,5 % |
| **total** | — | 1.848·1.848·1.409 | **4.928** | **177** | **5.105** | **5.544** | **92,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·410 | 1.293 | 41 | 1.334 | 1.386 | 96,2 % |
| exp_01 | Up | 462·462·387 | 1.269 | 42 | 1.311 | 1.386 | 94,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·409 | 1.233 | 34 | 1.267 | 1.287 | 98,4 % |
| **total** | — | 1.815·1.815·1.608 | **5.038** | **200** | **5.238** | **5.445** | **96,2 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.238 | 49 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.998** | **150** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.286 | 191 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.409 | 4.928 | 177 | 5.105 | 5.544 | 92,1 % |
| m3 | RUNNING | 1.815·1.815·1.608 | 5.038 | 200 | 5.238 | 5.445 | 96,2 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.998 | 150 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.250** | **718** | **20.968** | **21.681** | **96,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:179, install/adb:12
- m2: erros → emulator/boot:168, install/adb:9
- m3: erros → emulator/boot:187, install/adb:12, timeout:1
- m4: erros → emulator/boot:142, install/adb:8

## Ciclo 2026-07-11 13:10:34 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.313 | 43 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.325 | 52 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.286** | **191** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·415 | 1.286 | 53 | 1.339 | 1.386 | 96,6 % |
| exp_01 | Up | 462·462·425 | 1.307 | 42 | 1.349 | 1.386 | 97,3 % |
| exp_02 | Up | 462·462·245 | 1.127 | 42 | 1.169 | 1.386 | 84,3 % |
| exp_03 | Up | 462·462·333 | 1.213 | 44 | 1.257 | 1.386 | 90,7 % |
| **total** | — | 1.848·1.848·1.418 | **4.933** | **181** | **5.114** | **5.544** | **92,2 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·412 | 1.295 | 41 | 1.336 | 1.386 | 96,4 % |
| exp_01 | Up | 462·462·389 | 1.271 | 42 | 1.313 | 1.386 | 94,7 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·411 | 1.234 | 35 | 1.269 | 1.287 | 98,6 % |
| **total** | — | 1.815·1.815·1.614 | **5.043** | **201** | **5.244** | **5.445** | **96,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.238 | 49 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **4.998** | **150** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.286 | 191 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.418 | 4.933 | 181 | 5.114 | 5.544 | 92,2 % |
| m3 | RUNNING | 1.815·1.815·1.614 | 5.043 | 201 | 5.244 | 5.445 | 96,3 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 4.998 | 150 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.260** | **723** | **20.983** | **21.681** | **96,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:179, install/adb:12
- m2: erros → emulator/boot:171, install/adb:10
- m3: erros → emulator/boot:187, install/adb:13, timeout:1
- m4: erros → emulator/boot:142, install/adb:8

**Ações (13:10 local — ciclo 13:00 atrasado, rodado manualmente):**
- **m4**: a pedido do usuário, dado **reboot da VM** (`gcloud compute instances reset m4-exp02`) às 12:57 e **relançado o walk** (PID 1754). Dados preservados (done=5148/ok=4998/err=150 idêntico). Após o boot, churn de OOM na p60 (4 emuladores subindo juntos > 31 GiB): exp_00/01/02/03 ciclaram Exit 137 e foram restartados (docker start); memória normalizou (11-14 GiB usado). **POLÍTICA ALTERADA: auto-retry FASE 2 da m4 SUSPENSO — NÃO re-disparar ao término deste walk até discutir com o usuário.**
- **m1: VM TRAVADA** — SSH banner timeout em 5 tentativas (ConnectTimeout 20 e 40), gcloud RUNNING (padrão do incidente overnight, load estava ~25). **Reset da VM** (`m1-exp02`) às 13:06 + **walk resumido** (PID 1750). Dados preservados e levemente à frente (ok 5279→5286, remaining 77→67). 5/5 containers Up.
- m2/m3 saudáveis (5/5 Up, p300, load 8-25 ativo).
- Números 13:10: TOTAL done 20.981 (96,8%), ok 20.258 (93,4%), err 723, remaining 700. Δok desde 12:50: +27 (m1 +7, m2 +10, m3 +10, m4 +0 re-walking p60).
- Cauda continua monkey (704+ dos 723 err). m1/m4 recém-rebootadas voltam à p60 → ~2h para realcançar a p300 (livelock a monitorar).

## Ciclo 2026-07-11 14:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.313 | 43 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.326 | 51 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.287** | **190** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·423 | 1.294 | 53 | 1.347 | 1.386 | 97,2 % |
| exp_01 | Up | 462·462·435 | 1.314 | 45 | 1.359 | 1.386 | 98,1 % |
| exp_02 | Up | 462·462·253 | 1.135 | 42 | 1.177 | 1.386 | 84,9 % |
| exp_03 | Up | 462·462·342 | 1.221 | 45 | 1.266 | 1.386 | 91,3 % |
| **total** | — | 1.848·1.848·1.453 | **4.964** | **185** | **5.149** | **5.544** | **92,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·399 | 1.277 | 46 | 1.323 | 1.386 | 95,5 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·419 | 1.242 | 35 | 1.277 | 1.287 | 99,2 % |
| **total** | — | 1.815·1.815·1.638 | **5.063** | **205** | **5.268** | **5.445** | **96,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.240 | 47 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.250 | 37 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.002** | **146** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.287 | 190 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.453 | 4.964 | 185 | 5.149 | 5.544 | 92,9 % |
| m3 | RUNNING | 1.815·1.815·1.638 | 5.063 | 205 | 5.268 | 5.445 | 96,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.002 | 146 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.316** | **726** | **21.042** | **21.681** | **97,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:178, install/adb:12
- m2: erros → emulator/boot:173, install/adb:12
- m3: erros → emulator/boot:190, install/adb:14, timeout:1
- m4: erros → emulator/boot:135, install/adb:11

## Ciclo 2026-07-11 14:03:06 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.313 | 43 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.326 | 51 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.287** | **190** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·424 | 1.295 | 53 | 1.348 | 1.386 | 97,3 % |
| exp_01 | Up | 462·462·435 | 1.314 | 45 | 1.359 | 1.386 | 98,1 % |
| exp_02 | Up | 462·462·253 | 1.135 | 42 | 1.177 | 1.386 | 84,9 % |
| exp_03 | Up | 462·462·343 | 1.222 | 45 | 1.267 | 1.386 | 91,4 % |
| **total** | — | 1.848·1.848·1.455 | **4.966** | **185** | **5.151** | **5.544** | **92,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·399 | 1.277 | 46 | 1.323 | 1.386 | 95,5 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·420 | 1.243 | 35 | 1.278 | 1.287 | 99,3 % |
| **total** | — | 1.815·1.815·1.639 | **5.064** | **205** | **5.269** | **5.445** | **96,8 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.240 | 47 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.251 | 36 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.003** | **145** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.287 | 190 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.455 | 4.966 | 185 | 5.151 | 5.544 | 92,9 % |
| m3 | RUNNING | 1.815·1.815·1.639 | 5.064 | 205 | 5.269 | 5.445 | 96,8 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.003 | 145 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.320** | **725** | **21.045** | **21.681** | **97,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:178, install/adb:12
- m2: erros → emulator/boot:173, install/adb:12
- m3: erros → emulator/boot:190, install/adb:14, timeout:1
- m4: erros → emulator/boot:134, install/adb:11

**Ações (14:03 local):**
- 4/4 VMs vivas (cron 14:00 todas RUNNING; nenhum SSH_FALHOU).
- **m1 e m4 SEM livelock**: ambas avançaram p60→**p180** após o reboot (RV_TIMEOUTS=180), caminhando normalmente pela passada. Chegam à p300 em ~1h.
- **m4 convertendo erros pós-reboot: err 150→146** (+4 ok, agora ok=5002). Evidência de que parte do resíduo monkey era OOM-transitório (recuperável por reboot limpo), não puramente determinístico. Ainda na p180 — mais conversão esperada ao chegar à p300.
- m1: exp_01 Exited(137)/OOM → `docker start` (restaurado). Load moderado 8-11.
- m2/m3 saudáveis na p300 (5/5 Up), progredindo bem: Δok m2 +33, m3 +22.
- Números 14:03: TOTAL done 21.044 (97,1%), ok 20.318 (93,7%), err 726, remaining 637. Δok desde 13:10: +60 (m1 +1 [p180 re-validação], m2 +33, m3 +22, m4 +4).
- m4 auto-retry segue SUSPENSO (aguardando discussão).

## Ciclo 2026-07-11 15:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.314 | 42 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.328 | 49 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.290** | **187** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·435 | 1.303 | 56 | 1.359 | 1.386 | 98,1 % |
| exp_01 | Up | 462·462·444 | 1.323 | 45 | 1.368 | 1.386 | 98,7 % |
| exp_02 | Up | 462·462·262 | 1.144 | 42 | 1.186 | 1.386 | 85,6 % |
| exp_03 | Up | 462·462·352 | 1.231 | 45 | 1.276 | 1.386 | 92,1 % |
| **total** | — | 1.848·1.848·1.493 | **5.001** | **188** | **5.189** | **5.544** | **93,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·409 | 1.287 | 46 | 1.333 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.658 | **5.083** | **205** | **5.288** | **5.445** | **97,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.241 | 46 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.265 | 22 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.250 | 37 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.008** | **140** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.290 | 187 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.493 | 5.001 | 188 | 5.189 | 5.544 | 93,6 % |
| m3 | RUNNING | 1.815·1.815·1.658 | 5.083 | 205 | 5.288 | 5.445 | 97,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.008 | 140 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.382** | **720** | **21.102** | **21.681** | **97,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:174, install/adb:13
- m2: erros → emulator/boot:176, install/adb:12
- m3: erros → emulator/boot:190, install/adb:14, timeout:1
- m4: erros → emulator/boot:130, install/adb:10

## Ciclo 2026-07-11 15:02:59 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.314 | 42 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.328 | 49 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.290** | **187** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·435 | 1.303 | 56 | 1.359 | 1.386 | 98,1 % |
| exp_01 | Up | 462·462·445 | 1.324 | 45 | 1.369 | 1.386 | 98,8 % |
| exp_02 | Up | 462·462·263 | 1.145 | 42 | 1.187 | 1.386 | 85,6 % |
| exp_03 | Up | 462·462·352 | 1.231 | 45 | 1.276 | 1.386 | 92,1 % |
| **total** | — | 1.848·1.848·1.495 | **5.003** | **188** | **5.191** | **5.544** | **93,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·409 | 1.287 | 46 | 1.333 | 1.386 | 96,2 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.658 | **5.083** | **205** | **5.288** | **5.445** | **97,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.241 | 46 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.265 | 22 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.250 | 37 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.009** | **139** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.290 | 187 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.495 | 5.003 | 188 | 5.191 | 5.544 | 93,6 % |
| m3 | RUNNING | 1.815·1.815·1.658 | 5.083 | 205 | 5.288 | 5.445 | 97,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.009 | 139 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.385** | **719** | **21.104** | **21.681** | **97,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:174, install/adb:13
- m2: erros → emulator/boot:176, install/adb:12
- m3: erros → emulator/boot:189, install/adb:15, timeout:1
- m4: erros → emulator/boot:129, install/adb:10

**Ações (15:03 local):**
- 4/4 VMs vivas (cron 15:00 todas RUNNING; nenhum SSH_FALHOU). **Todas as 4 agora na p300.**
- ✅ **m1 e m4 completaram o walk pós-reboot sem livelock**: ambas chegaram p60→p180→**p300** (m1 uptime 1:53, m4 2:03). Os pendentes p300 voltam a progredir.
- 🔬 **m4 continua convertendo erros pós-reboot: err 146→140** (trajetória 150→146→140 desde o reboot das 12:57 → **10 erros recuperados**). Confirma componente OOM-transitório significativo no resíduo monkey; reboot limpo recupera. ok m4 = 5.008/5.148 (97,3%).
- m2/m3 saudáveis na p300; m3 exp_03 teve OOM e já reergueu (Up 2 min). Sem ação manual necessária.
- Números 15:02: TOTAL done 21.104 (97,3%), ok 20.384 (94,0%), err 720, remaining 577. Δok desde 14:03: +66 (m1 +3, m2 +38, m3 +19, m4 +6). **Cruzou 94% ok.**
- m4 auto-retry segue SUSPENSO (aguardando discussão).

## Ciclo 2026-07-11 16:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.316 | 40 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.329 | 48 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.293** | **184** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·445 | 1.313 | 56 | 1.369 | 1.386 | 98,8 % |
| exp_01 | Up | 462·462·456 | 1.333 | 47 | 1.380 | 1.386 | 99,6 % |
| exp_02 | Up | 462·462·273 | 1.152 | 45 | 1.197 | 1.386 | 86,4 % |
| exp_03 | Up | 462·462·364 | 1.240 | 48 | 1.288 | 1.386 | 92,9 % |
| **total** | — | 1.848·1.848·1.538 | **5.038** | **196** | **5.234** | **5.544** | **94,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·419 | 1.297 | 46 | 1.343 | 1.386 | 96,9 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.668 | **5.094** | **204** | **5.298** | **5.445** | **97,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.266 | 21 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.251 | 36 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.014** | **134** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.293 | 184 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.538 | 5.038 | 196 | 5.234 | 5.544 | 94,4 % |
| m3 | RUNNING | 1.815·1.815·1.668 | 5.094 | 204 | 5.298 | 5.445 | 97,3 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.014 | 134 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.439** | **718** | **21.157** | **21.681** | **97,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:176, install/adb:8
- m2: erros → emulator/boot:180, install/adb:16
- m3: erros → emulator/boot:187, install/adb:16, timeout:1
- m4: erros → emulator/boot:127, install/adb:7

## Ciclo 2026-07-11 16:02:59 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.316 | 40 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·434 | 1.306 | 52 | 1.358 | 1.386 | 98,0 % |
| exp_02 | Up | 462·462·453 | 1.329 | 48 | 1.377 | 1.386 | 99,4 % |
| exp_03 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.781 | **5.293** | **184** | **5.477** | **5.544** | **98,8 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·445 | 1.313 | 56 | 1.369 | 1.386 | 98,8 % |
| exp_01 | Up | 462·462·456 | 1.333 | 47 | 1.380 | 1.386 | 99,6 % |
| exp_02 | Up | 462·462·274 | 1.153 | 45 | 1.198 | 1.386 | 86,4 % |
| exp_03 | Up | 462·462·365 | 1.240 | 49 | 1.289 | 1.386 | 93,0 % |
| **total** | — | 1.848·1.848·1.540 | **5.039** | **197** | **5.236** | **5.544** | **94,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·419 | 1.297 | 46 | 1.343 | 1.386 | 96,9 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.668 | **5.094** | **204** | **5.298** | **5.445** | **97,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.266 | 21 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.251 | 36 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.014** | **134** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.781 | 5.293 | 184 | 5.477 | 5.544 | 98,8 % |
| m2 | RUNNING | 1.848·1.848·1.540 | 5.039 | 197 | 5.236 | 5.544 | 94,4 % |
| m3 | RUNNING | 1.815·1.815·1.668 | 5.094 | 204 | 5.298 | 5.445 | 97,3 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.014 | 134 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.440** | **719** | **21.159** | **21.681** | **97,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:177, install/adb:7
- m2: erros → emulator/boot:181, install/adb:16
- m3: erros → emulator/boot:187, install/adb:16, timeout:1
- m4: erros → emulator/boot:128, install/adb:6

**Ações (16:03 local):**
- 4/4 VMs vivas (cron 16:00 todas RUNNING; nenhum SSH_FALHOU). Todas na p300.
- Nenhuma anomalia manual: m4 exp_01/exp_03 e m3 exp_03 tiveram OOM e o cron já reergueu (todos Up). Loads altos (m1=36, m2=23) mas trabalhando.
- m4 (3º walk, ainda rodando, concluido=2) segue convertendo: err 140→**134** (trajetória pós-reboot 150→146→140→134 = **16 recuperados**). ok m4 = 5.014/5.148.
- m2 puxando na p300 (Δok +36); m3 +11; m1 +3.
- Números 16:02: TOTAL done 21.159 (97,6%), ok 20.440 (94,3%), err 719, remaining 522. Δok desde 15:02: +56.
- m4 auto-retry segue SUSPENSO. Plano de mop-up de baixa concorrência (menos containers) discutido com o usuário — aguardando m4 terminar para extrair o conjunto-falha.

## Ciclo 2026-07-11 17:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·441 | 1.325 | 40 | 1.365 | 1.386 | 98,5 % |
| exp_01 | Up | 462·462·442 | 1.314 | 52 | 1.366 | 1.386 | 98,6 % |
| exp_02 | Up | 462·462·461 | 1.338 | 47 | 1.385 | 1.386 | 99,9 % |
| exp_03 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.806 | **5.320** | **182** | **5.502** | **5.544** | **99,2 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·453 | 1.320 | 57 | 1.377 | 1.386 | 99,4 % |
| exp_01 | Up | 462·462·462 | 1.338 | 48 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·282 | 1.160 | 46 | 1.206 | 1.386 | 87,0 % |
| exp_03 | Up | 462·462·374 | 1.247 | 51 | 1.298 | 1.386 | 93,7 % |
| **total** | — | 1.848·1.848·1.571 | **5.065** | **202** | **5.267** | **5.544** | **95,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·428 | 1.306 | 46 | 1.352 | 1.386 | 97,5 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.677 | **5.105** | **202** | **5.307** | **5.445** | **97,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.268 | 19 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.018** | **130** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.806 | 5.320 | 182 | 5.502 | 5.544 | 99,2 % |
| m2 | RUNNING | 1.848·1.848·1.571 | 5.065 | 202 | 5.267 | 5.544 | 95,0 % |
| m3 | RUNNING | 1.815·1.815·1.677 | 5.105 | 202 | 5.307 | 5.445 | 97,5 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.018 | 130 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.508** | **716** | **21.224** | **21.681** | **97,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:7
- m2: erros → emulator/boot:181, install/adb:21
- m3: erros → emulator/boot:186, install/adb:15, timeout:1
- m4: erros → emulator/boot:122, install/adb:8

## Ciclo 2026-07-11 17:03:00 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·441 | 1.325 | 40 | 1.365 | 1.386 | 98,5 % |
| exp_01 | Up | 462·462·442 | 1.314 | 52 | 1.366 | 1.386 | 98,6 % |
| exp_02 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.807 | **5.321** | **182** | **5.503** | **5.544** | **99,3 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·454 | 1.321 | 57 | 1.378 | 1.386 | 99,4 % |
| exp_01 | Up | 462·462·462 | 1.338 | 48 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·283 | 1.161 | 46 | 1.207 | 1.386 | 87,1 % |
| exp_03 | Up | 462·462·374 | 1.247 | 51 | 1.298 | 1.386 | 93,7 % |
| **total** | — | 1.848·1.848·1.573 | **5.067** | **202** | **5.269** | **5.544** | **95,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·430 | 1.307 | 47 | 1.354 | 1.386 | 97,7 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.679 | **5.106** | **203** | **5.309** | **5.445** | **97,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.242 | 45 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.268 | 19 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.018** | **130** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.807 | 5.321 | 182 | 5.503 | 5.544 | 99,3 % |
| m2 | RUNNING | 1.848·1.848·1.573 | 5.067 | 202 | 5.269 | 5.544 | 95,0 % |
| m3 | RUNNING | 1.815·1.815·1.679 | 5.106 | 203 | 5.309 | 5.445 | 97,5 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.018 | 130 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.512** | **717** | **21.229** | **21.681** | **97,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:175, install/adb:7
- m2: erros → emulator/boot:181, install/adb:21
- m3: erros → emulator/boot:187, install/adb:15, timeout:1
- m4: erros → emulator/boot:122, install/adb:8

**Ações (17:03 local):**
- 4/4 VMs vivas (cron 17:00 todas RUNNING; nenhum SSH_FALHOU). Todas na p300.
- Nenhuma anomalia manual: restarts pontuais (m1 exp_03, m2 exp_01, m3 exp_03) cobertos pelo cron. Loads m4=30, m2=24.
- m1 acelerando na p300: ok +28, remaining 67→41 (perto do teto).
- m4 (3º walk, ainda rodando, concluido=2) segue convertendo: err 134→**130** (trajetória pós-reboot 150→146→140→134→130 = **20 recuperados**). ok m4 = 5.018/5.148.
- Números 17:02: TOTAL done 21.229 (97,9%), ok 20.512 (94,6%), err 717, remaining 452. Δok desde 16:02: +72 (m1 +28, m2 +28, m3 +12, m4 +4).
- m4 auto-retry SUSPENSO; plano de mop-up de baixa concorrência aguardando término da m4.

## Ciclo 2026-07-11 18:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·452 | 1.335 | 41 | 1.376 | 1.386 | 99,3 % |
| exp_01 | Up | 462·462·451 | 1.323 | 52 | 1.375 | 1.386 | 99,2 % |
| exp_02 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.827 | **5.341** | **182** | **5.523** | **5.544** | **99,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.329 | 57 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·294 | 1.170 | 48 | 1.218 | 1.386 | 87,9 % |
| exp_03 | Up | 462·462·383 | 1.256 | 51 | 1.307 | 1.386 | 94,3 % |
| **total** | — | 1.848·1.848·1.601 | **5.094** | **203** | **5.297** | **5.544** | **95,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·441 | 1.315 | 50 | 1.365 | 1.386 | 98,5 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.690 | **5.114** | **206** | **5.320** | **5.445** | **97,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.270 | 17 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.021** | **127** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.827 | 5.341 | 182 | 5.523 | 5.544 | 99,6 % |
| m2 | RUNNING | 1.848·1.848·1.601 | 5.094 | 203 | 5.297 | 5.544 | 95,5 % |
| m3 | RUNNING | 1.815·1.815·1.690 | 5.114 | 206 | 5.320 | 5.445 | 97,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.021 | 127 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.570** | **718** | **21.288** | **21.681** | **98,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:173, install/adb:9
- m2: erros → emulator/boot:180, install/adb:23
- m3: erros → emulator/boot:190, install/adb:15, timeout:1
- m4: erros → emulator/boot:119, install/adb:8

## Ciclo 2026-07-11 18:02:56 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·452 | 1.335 | 41 | 1.376 | 1.386 | 99,3 % |
| exp_01 | Up | 462·462·452 | 1.324 | 52 | 1.376 | 1.386 | 99,3 % |
| exp_02 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.828 | **5.342** | **182** | **5.524** | **5.544** | **99,6 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.329 | 57 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·294 | 1.170 | 48 | 1.218 | 1.386 | 87,9 % |
| exp_03 | Up | 462·462·384 | 1.257 | 51 | 1.308 | 1.386 | 94,4 % |
| **total** | — | 1.848·1.848·1.602 | **5.096** | **202** | **5.298** | **5.544** | **95,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·442 | 1.316 | 50 | 1.366 | 1.386 | 98,6 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.691 | **5.115** | **206** | **5.321** | **5.445** | **97,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.270 | 17 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.021** | **127** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.828 | 5.342 | 182 | 5.524 | 5.544 | 99,6 % |
| m2 | RUNNING | 1.848·1.848·1.602 | 5.096 | 202 | 5.298 | 5.544 | 95,6 % |
| m3 | RUNNING | 1.815·1.815·1.691 | 5.115 | 206 | 5.321 | 5.445 | 97,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.021 | 127 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.574** | **717** | **21.291** | **21.681** | **98,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:173, install/adb:9
- m2: erros → emulator/boot:179, install/adb:23
- m3: erros → emulator/boot:191, install/adb:14, timeout:1
- m4: erros → emulator/boot:119, install/adb:8

**Ações (18:03 local):**
- 4/4 VMs vivas (cron 18:00 todas RUNNING; nenhum SSH_FALHOU). Todas na p300.
- Nenhuma anomalia manual: restarts pontuais (m1 exp_02, m2 exp_00, m3 exp_03, m4 exp_00) cobertos pelo cron. Loads 22-27.
- m1 no teto de feito: remaining 41→20 (+21 ok). Deve fechar o 1º walk em breve → então entra em retry FASE 2 (política normal p/ m1).
- m4 (3º walk, ainda rodando, concluido=2) converte: err 130→**127** (trajetória pós-reboot 150→127 = **23 recuperados**; p300 ERROR agora 101, p180 26). ok m4 = 5.021/5.148.
- Números 18:02: TOTAL done 21.290 (98,2%), ok 20.573 (94,9%), err 717, remaining 391. Δok desde 17:02: +61 (m1 +21, m2 +28, m3 +9, m4 +3). **Perto de 95% ok.**
- m4 auto-retry SUSPENSO; mop-up de baixa concorrência aguardando término da m4.

## Ciclo 2026-07-11 19:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·461 | 1.333 | 52 | 1.385 | 1.386 | 99,9 % |
| exp_02 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.847 | **5.361** | **182** | **5.543** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.330 | 56 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·306 | 1.178 | 52 | 1.230 | 1.386 | 88,7 % |
| exp_03 | Up | 462·462·393 | 1.266 | 51 | 1.317 | 1.386 | 95,0 % |
| **total** | — | 1.848·1.848·1.623 | **5.119** | **200** | **5.319** | **5.544** | **95,9 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·451 | 1.325 | 50 | 1.375 | 1.386 | 99,2 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.700 | **5.124** | **206** | **5.330** | **5.445** | **97,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.847 | 5.361 | 182 | 5.543 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.623 | 5.119 | 200 | 5.319 | 5.544 | 95,9 % |
| m3 | RUNNING | 1.815·1.815·1.700 | 5.124 | 206 | 5.330 | 5.445 | 97,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.627** | **713** | **21.340** | **21.681** | **98,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:173, install/adb:9
- m2: erros → emulator/boot:179, install/adb:21
- m3: erros → emulator/boot:191, install/adb:14, timeout:1
- m4: erros → emulator/boot:118, install/adb:7

## Ciclo 2026-07-11 19:02:57 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·461 | 1.333 | 52 | 1.385 | 1.386 | 99,9 % |
| exp_02 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.847 | **5.361** | **182** | **5.543** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.330 | 56 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·307 | 1.179 | 52 | 1.231 | 1.386 | 88,8 % |
| exp_03 | Up | 462·462·393 | 1.266 | 51 | 1.317 | 1.386 | 95,0 % |
| **total** | — | 1.848·1.848·1.624 | **5.121** | **199** | **5.320** | **5.544** | **96,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·452 | 1.326 | 50 | 1.376 | 1.386 | 99,3 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.255 | 32 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.701 | **5.125** | **206** | **5.331** | **5.445** | **97,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.847 | 5.361 | 182 | 5.543 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.624 | 5.121 | 199 | 5.320 | 5.544 | 96,0 % |
| m3 | RUNNING | 1.815·1.815·1.701 | 5.125 | 206 | 5.331 | 5.445 | 97,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.630** | **712** | **21.342** | **21.681** | **98,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:174, install/adb:8
- m2: erros → emulator/boot:179, install/adb:20
- m3: erros → emulator/boot:191, install/adb:14, timeout:1
- m4: erros → emulator/boot:118, install/adb:7

**Ações (19:03 local):**
- 4/4 VMs vivas (cron 19:00 todas RUNNING; nenhum SSH_FALHOU). Todas na p300.
- Nenhuma anomalia manual: restarts pontuais (m1 exp_00, m3 exp_03, m4 exp_01) cobertos pelo cron. m4 load alto (40) mas trabalhando.
- **m1 remaining=1** — prestes a fechar o 1º walk (concluido=0→deve virar 1). Ao terminar, retry FASE 2 normal (m1≠m4) → re-roda os 182 err (137 na p300, ainda não retentados). VIGIAR término no próximo ciclo.
- m4 (3º walk, ainda rodando) converte: err 127→**125** (trajetória pós-reboot 150→125 = **25 recuperados**). ok m4 = 5.023/5.148.
- Números 19:02: TOTAL done 21.341 (98,4%), ok 20.629 (**95,1%**), err 712, remaining 340. Δok desde 18:02: +56 (m1 +19, m2 +25, m3 +10, m4 +2). **Cruzou 95% ok.**
- m4 auto-retry SUSPENSO; mop-up aguardando término da m4.

## Ciclo 2026-07-11 20:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.335 | 51 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.365** | **179** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.331 | 55 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·317 | 1.187 | 54 | 1.241 | 1.386 | 89,5 % |
| exp_03 | Up | 462·462·404 | 1.274 | 54 | 1.328 | 1.386 | 95,8 % |
| **total** | — | 1.848·1.848·1.645 | **5.138** | **203** | **5.341** | **5.544** | **96,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.257 | 30 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.137** | **204** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.365 | 179 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.645 | 5.138 | 203 | 5.341 | 5.544 | 96,3 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.137 | 204 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.663** | **711** | **21.374** | **21.681** | **98,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:173, install/adb:6
- m2: erros → emulator/boot:182, install/adb:21
- m3: erros → emulator/boot:189, install/adb:14, timeout:1
- m4: erros → emulator/boot:119, install/adb:6
- m4: container exp_00 docker=gone (ok=1243 fail=44)
- m4: container exp_01 docker=gone (ok=1272 fail=15)
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-11 21:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.335 | 51 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.370** | **174** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.331 | 55 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.347 | 39 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·329 | 1.197 | 56 | 1.253 | 1.386 | 90,4 % |
| exp_03 | Up | 462·462·415 | 1.284 | 55 | 1.339 | 1.386 | 96,6 % |
| **total** | — | 1.848·1.848·1.668 | **5.159** | **205** | **5.364** | **5.544** | **96,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.257 | 30 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.137** | **204** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.370 | 174 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.668 | 5.159 | 205 | 5.364 | 5.544 | 96,8 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.137 | 204 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.689** | **708** | **21.397** | **21.681** | **98,7 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:167, install/adb:6, timeout:1
- m2: erros → emulator/boot:181, install/adb:24
- m3: erros → emulator/boot:190, install/adb:13, timeout:1
- m4: erros → emulator/boot:119, install/adb:6
- m4: container exp_00 docker=gone (ok=1243 fail=44)
- m4: container exp_01 docker=gone (ok=1272 fail=15)
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-11 22:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.373** | **171** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.331 | 55 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·339 | 1.205 | 58 | 1.263 | 1.386 | 91,1 % |
| exp_03 | Up | 462·462·424 | 1.293 | 55 | 1.348 | 1.386 | 97,3 % |
| **total** | — | 1.848·1.848·1.687 | **5.177** | **206** | **5.383** | **5.544** | **97,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.338 | 48 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.257 | 30 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.139** | **202** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.373 | 171 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.687 | 5.177 | 206 | 5.383 | 5.544 | 97,1 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.139 | 202 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.712** | **704** | **21.416** | **21.681** | **98,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:166, install/adb:4, timeout:1
- m2: erros → emulator/boot:180, install/adb:26
- m3: erros → emulator/boot:190, install/adb:11, timeout:1
- m4: erros → emulator/boot:119, install/adb:6
- m4: container exp_00 docker=gone (ok=1243 fail=44)
- m4: container exp_01 docker=gone (ok=1272 fail=15)
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-11 22:26:46 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.373** | **171** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.332 | 54 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·343 | 1.209 | 58 | 1.267 | 1.386 | 91,4 % |
| exp_03 | Up | 462·462·430 | 1.297 | 57 | 1.354 | 1.386 | 97,7 % |
| **total** | — | 1.848·1.848·1.697 | **5.186** | **207** | **5.393** | **5.544** | **97,3 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.338 | 48 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.140** | **201** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.373 | 171 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.697 | 5.186 | 207 | 5.393 | 5.544 | 97,3 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.140 | 201 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.722** | **704** | **21.426** | **21.681** | **98,8 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:166, install/adb:4, timeout:1
- m1: container exp_00 docker=gone (ok=1346 fail=40)
- m1: container exp_01 docker=gone (ok=1336 fail=50)
- m1: container exp_02 docker=gone (ok=1343 fail=43)
- m1: container exp_03 docker=gone (ok=1348 fail=38)
- m2: erros → emulator/boot:179, install/adb:28
- m2: container exp_01 docker=exited (ok=1348 fail=38)
- m3: erros → emulator/boot:187, install/adb:13, timeout:1
- m4: erros → emulator/boot:119, install/adb:6
- m4: container exp_00 docker=gone (ok=1243 fail=44)
- m4: container exp_01 docker=gone (ok=1272 fail=15)
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

**Ações (22:28 local — ciclo 20:00 estendido pela análise da m4):**
- NOTA: o ciclo levou ~2h20 de tempo real (análise do conjunto-falha da m4 com o usuário). Números finais coletados às 22:28.
- **m4 TERMINOU o 3º walk** (concluido=3, ociosa, auto-retry SUSPENSO). Resíduo final = **125 err, 100% monkey** (p180=26, p300=99). Pré-reboot 150 → 125 (25 recuperados).
- **ANÁLISE DO CONJUNTO-FALHA DA m4 (extraído do tasks.json, dedup por identidade):** 125 identidades ERROR em **48 APKs distintos** (de 52 no batch). Distribuição de slots falhos por APK (de 9 monkey): 1/9=13 APKs, 2/9=10, 3/9=13, 4/9=8, 5/9=3, 6/9=1. **NENHUM APK falha 7-9/9** (máx 6/9). Todo APK que falha ainda passa ≥3 dos 9 runs → assinatura de **falha OOM-transitória, NÃO crash determinístico**. Não há núcleo determinístico detectável; os 125 são recuperáveis com alívio de memória (mop-up de baixa concorrência). CONCLUSÃO PENDENTE DE DECISÃO DO USUÁRIO.
- **m1 TERMINOU o 1º walk** (concluido=1) e ficou ociosa → **retry FASE 2 disparado** às 22:28 (PID 805085; m1≠m4, política normal). Re-roda os 171 err.
- m2: exp_01 Exited(137) → restart. Rodando. Δok +47 (2h).
- m3: rodando, mas LENTA neste janela (Δok +3, remaining 104 estável) → VIGIAR próximo ciclo.
- Números 22:28: TOTAL done 21.427 (98,8%), ok 20.723 (**95,6%**), err 704, remaining 254. Δok desde 20:02: +58.

**Ações (22:40 local):**
- **m3 REBOOTADA** (`reset m3-exp02`) a pedido + walk relançado (PID 1748); dados preservados (ok=5140/err=201/rem=104). Volta à p60 → ~2h p/ p300. Reboots acumulados: 25.
- **MOP-UP DA m4 INICIADO** (autorizado): 2 containers × 16 GiB, driver `scripts/run_mopup.sh m4` (PID 356536), compose `docker-compose.mopup.yml` (mem 16g). 2 ondas (exp_00+01, depois exp_02+03) × 3 passadas (60/180/300); reusa results/exp_NN → resume pula COMPLETED, re-roda só os 125 ERROR monkey. Baseline: ok=5023/err=125. Log: `mopup_m4.log`. Objetivo: recuperar o resíduo OOM-transitório (análise: 48 APKs, máx 6/9, sem núcleo determinístico).
- m1 retry FASE 2 rodando (err 171); m2 rodando (err 207, rem 146); m3 pós-reboot re-walking.
- Números 22:40: ok 20.728 (95,6%), err 703, remaining 250.

## Ciclo 2026-07-11 22:53:57 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.373** | **171** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·348 | 1.214 | 58 | 1.272 | 1.386 | 91,8 % |
| exp_03 | Up | 462·462·434 | 1.301 | 57 | 1.358 | 1.386 | 98,0 % |
| **total** | — | 1.848·1.848·1.706 | **5.196** | **206** | **5.402** | **5.544** | **97,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.141** | **200** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.373 | 171 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.706 | 5.196 | 206 | 5.402 | 5.544 | 97,4 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.141 | 200 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.733** | **702** | **21.435** | **21.681** | **98,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:167, install/adb:3, timeout:1
- m2: erros → emulator/boot:178, install/adb:28
- m3: erros → emulator/boot:186, install/adb:13, timeout:1
- m4: erros → emulator/boot:118, install/adb:7
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

**Ações (22:53 local):** ok real 20.733/21.681 = 95,63 % (err 702, rem 246; Δok +5 desde 22:40). Nenhuma intervenção necessária — todos os containers esperados Up. m1: retry FASE 2 rodando (p180), 5/5 Up. m2: p300, 5/5 Up (restarts OOM cron esperados exp_00/exp_01). m3: pós-reboot 22:31 re-walking (p180), 5/5 Up. m4: mop-up onda 1 ATIVA (exp_00+exp_01, 2×16 GiB, passada p180 recém-recriada; log 22:53:39 local vs host 22:53:41 = vivo); exp_02/exp_03 "gone" é esperado na onda 1 (não é anomalia). Cauda ~700 err ainda 100 % monkey/emulator-boot (m1:167, m2:178, m3:186, m4:118), OOM-transitória. Reboots acumulados: 25. Reagendado wakeup 23:00.

## Ciclo 2026-07-11 23:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.373** | **171** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·349 | 1.215 | 58 | 1.273 | 1.386 | 91,8 % |
| exp_03 | Up | 462·462·435 | 1.302 | 57 | 1.359 | 1.386 | 98,1 % |
| **total** | — | 1.848·1.848·1.708 | **5.198** | **206** | **5.404** | **5.544** | **97,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.142** | **199** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.373 | 171 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.708 | 5.198 | 206 | 5.404 | 5.544 | 97,5 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.142 | 199 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.736** | **701** | **21.437** | **21.681** | **98,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:167, install/adb:3, timeout:1
- m2: erros → emulator/boot:178, install/adb:28
- m3: erros → emulator/boot:185, install/adb:13, timeout:1
- m4: erros → emulator/boot:118, install/adb:7
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-11 23:05:11 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.373** | **171** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·349 | 1.215 | 58 | 1.273 | 1.386 | 91,8 % |
| exp_03 | Up | 462·462·436 | 1.303 | 57 | 1.360 | 1.386 | 98,1 % |
| **total** | — | 1.848·1.848·1.709 | **5.199** | **206** | **5.405** | **5.544** | **97,5 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.301 | 41 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.142** | **199** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.243 | 44 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.272 | 15 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.023** | **125** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.373 | 171 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.709 | 5.199 | 206 | 5.405 | 5.544 | 97,5 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.142 | 199 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.023 | 125 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.737** | **701** | **21.438** | **21.681** | **98,9 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:167, install/adb:3, timeout:1
- m2: erros → emulator/boot:178, install/adb:28
- m3: erros → emulator/boot:184, install/adb:14, timeout:1
- m4: erros → emulator/boot:117, install/adb:8
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

**Ações (23:05 local):** ok real 20.737/21.681 = 95,65 % (err 701, rem 243; Δok +4 desde 22:53). Nenhuma intervenção — todos os containers esperados Up. m1: retry FASE 2 (p180), 5/5 Up. m2: p300, 5/5 Up (Δok +3; restarts OOM cron esperados). m3: re-walking pós-reboot (p180), 5/5 Up. m4: mop-up onda 1 ainda em curso (exp_00+exp_01, p180; log 23:05:00 vs host 23:05:02 = vivo); err=125 inalterado é esperado — onda 1 não fechou passada ainda; exp_02/exp_03 "gone" esperado. Cauda ~700 err 100 % monkey/emulator-boot. Reboots acumulados: 25. Reagendado wakeup 00:00.

## Ciclo 2026-07-12 00:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.376** | **168** | **5.544** | **5.544** | **100,0 %** |

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.303 | 39 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.243 | 83 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.147** | **194** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.244 | 43 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.273 | 14 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.025** | **123** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.376 | 168 | 5.544 | 5.544 | 100,0 % |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.147 | 194 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.025 | 123 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **15.548** | **485** | **16.033** | **16.137** | **99,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:163, install/adb:4, timeout:1
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: erros → emulator/boot:180, install/adb:13, timeout:1
- m4: erros → emulator/boot:116, install/adb:7
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-12 01:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.376** | **168** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | exit | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.303 | 39 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.342 | 44 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.245 | 81 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.149** | **192** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.275 | 12 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.256 | 31 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.028** | **120** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.376 | 168 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.149 | 192 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.028 | 120 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.767** | **687** | **21.454** | **21.681** | **99,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:164, install/adb:3, timeout:1
- m2: erros → emulator/boot:181, install/adb:26
- m2: container exp_00 docker=exited (ok=1333 fail=53)
- m2: container exp_01 docker=exited (ok=1348 fail=38)
- m2: container exp_02 docker=exited (ok=1223 fail=58)
- m2: container exp_03 docker=exited (ok=1310 fail=58)
- m3: erros → emulator/boot:175, install/adb:16, timeout:1
- m4: erros → emulator/boot:113, install/adb:7
- m4: container exp_02 docker=gone (ok=1256 fail=31)
- m4: container exp_03 docker=gone (ok=1252 fail=35)

## Ciclo 2026-07-12 02:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.378** | **166** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | exit | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·418 | 1.307 | 35 | 1.342 | 1.386 | 96,8 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.247 | 79 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.711 | **5.157** | **184** | **5.341** | **5.445** | **98,1 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.275 | 12 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.257 | 30 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.029** | **119** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.378 | 166 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.711 | 5.157 | 184 | 5.341 | 5.445 | 98,1 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.029 | 119 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.778** | **676** | **21.454** | **21.681** | **99,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:159, install/adb:7
- m2: erros → emulator/boot:181, install/adb:26
- m2: container exp_00 docker=exited (ok=1333 fail=53)
- m2: container exp_01 docker=exited (ok=1348 fail=38)
- m2: container exp_02 docker=exited (ok=1223 fail=58)
- m2: container exp_03 docker=exited (ok=1310 fail=58)
- m3: erros → emulator/boot:172, install/adb:11, timeout:1
- m4: erros → emulator/boot:112, install/adb:6, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)

## Ciclo 2026-07-12 03:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.383** | **161** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | exit | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·425 | 1.314 | 35 | 1.349 | 1.386 | 97,3 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·404 | 1.253 | 75 | 1.328 | 1.386 | 95,8 % |
| exp_03 | Up | 429·429·429 | 1.261 | 26 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.720 | **5.171** | **179** | **5.350** | **5.445** | **98,3 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.276 | 11 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.257 | 30 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.030** | **118** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.383 | 161 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.720 | 5.171 | 179 | 5.350 | 5.445 | 98,3 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.030 | 118 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.798** | **665** | **21.463** | **21.681** | **99,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:148, install/adb:12, timeout:1
- m2: erros → emulator/boot:181, install/adb:26
- m2: container exp_00 docker=exited (ok=1333 fail=53)
- m2: container exp_01 docker=exited (ok=1348 fail=38)
- m2: container exp_02 docker=exited (ok=1223 fail=58)
- m2: container exp_03 docker=exited (ok=1310 fail=58)
- m3: erros → emulator/boot:172, install/adb:7
- m4: erros → emulator/boot:110, install/adb:7, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)

## Ciclo 2026-07-12 03:37:42 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.384** | **160** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·432 | 1.318 | 38 | 1.356 | 1.386 | 97,8 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·410 | 1.259 | 75 | 1.334 | 1.386 | 96,2 % |
| exp_03 | Up | 429·429·429 | 1.261 | 26 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.733 | **5.181** | **182** | **5.363** | **5.445** | **98,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.032** | **116** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.384 | 160 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.733 | 5.181 | 182 | 5.363 | 5.445 | 98,5 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.032 | 116 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.811** | **665** | **21.476** | **21.681** | **99,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:149, install/adb:10, timeout:1
- m1: container exp_00 docker=gone (ok=1349 fail=37)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m1: container exp_02 docker=gone (ok=1345 fail=41)
- m1: container exp_03 docker=gone (ok=1349 fail=37)
- m2: erros → emulator/boot:181, install/adb:26
- m3: erros → emulator/boot:173, install/adb:9
- m4: erros → emulator/boot:107, install/adb:8, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)

**Ações (03:37 local):** ok real 20.811/21.681 = 95,99 % (err 665, rem 205; Δok +74 desde 23:05, gap de ~4,5h com sessão ociosa). AÇÕES: (1) **m2 estava TRAVADA** — SSH "banner exchange timeout" 4× com VM RUNNING no gcloud (thrashing/OOM); RESET m2-exp02 (~00:04), mas a VM voltou com containers Exited e o cron NÃO resume → ficou ~3h ociosa até resume manual às 03:36 (dados preservados via bind-mount: ok 5199→5214, rem 139→123). (2) **m1**: retry FASE 2 fechou 2 walks (err 171→160, "concluído" 03:11 local), residual OOM-transitório → copiei run_mopup.sh + docker-compose.mopup.yml da m4 (não existiam na m1) e disparei **MOP-UP m1** (onda 1 exp_00+exp_01 ativa). (3) **m4 mop-up**: onda 1 CONCLUÍDA (exp_00 exit=0 limpo), **onda 2 (exp_02+exp_03) rodando**; err 125→116. (4) m3: rodando, err 199→182. Cauda ~665 err ainda 100 % monkey/emulator-boot. Reboots acumulados: 26. LIÇÃO: cron só loga; VM resetada precisa de resume ATIVO — não deixar turno terminar sem confirmar resume. Reagendado wakeup 04:00.

## Ciclo 2026-07-12 04:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.384** | **160** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·436 | 1.322 | 38 | 1.360 | 1.386 | 98,1 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·414 | 1.263 | 75 | 1.338 | 1.386 | 96,5 % |
| exp_03 | Up | 429·429·429 | 1.261 | 26 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.741 | **5.189** | **182** | **5.371** | **5.445** | **98,6 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.032** | **116** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.384 | 160 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.741 | 5.189 | 182 | 5.371 | 5.445 | 98,6 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.032 | 116 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.819** | **665** | **21.484** | **21.681** | **99,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:150, install/adb:9, timeout:1
- m1: container exp_02 docker=gone (ok=1345 fail=41)
- m1: container exp_03 docker=gone (ok=1349 fail=37)
- m2: erros → emulator/boot:179, install/adb:28
- m3: erros → emulator/boot:173, install/adb:9
- m4: erros → emulator/boot:107, install/adb:8, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)

## Ciclo 2026-07-12 04:04:10 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.384** | **160** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.333 | 53 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.223 | 58 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.214** | **207** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·436 | 1.322 | 38 | 1.360 | 1.386 | 98,1 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·415 | 1.264 | 75 | 1.339 | 1.386 | 96,6 % |
| exp_03 | Up | 429·429·429 | 1.261 | 26 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.742 | **5.190** | **182** | **5.372** | **5.445** | **98,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.032** | **116** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.384 | 160 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.214 | 207 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.742 | 5.190 | 182 | 5.372 | 5.445 | 98,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.032 | 116 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.820** | **665** | **21.485** | **21.681** | **99,1 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:150, install/adb:9, timeout:1
- m1: container exp_02 docker=gone (ok=1345 fail=41)
- m1: container exp_03 docker=gone (ok=1349 fail=37)
- m2: erros → emulator/boot:179, install/adb:28
- m3: erros → emulator/boot:173, install/adb:9
- m4: erros → emulator/boot:107, install/adb:8, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)
- m4: container exp_01 docker=gone (ok=1277 fail=10)

**Ações (04:04 local):** ok real 20.820/21.681 = 96,03 % (err 665, rem 196; Δok +9 desde 03:37). Estados: m1 MOP-UP onda 1 (exp_00+exp_01 Up; exp_02/03 "gone" esperado). m2 viva pós-resume, re-walking p180 (5/5 Up) — VM que travou segue OK. m3 chegou à **p300** (rem 104→74, err 182). m4 MOP-UP onda 2 (exp_02+exp_03 Up p300; exp_00 exit=0 onda1). AÇÃO: **removido stray exp_01 na m4** — cron restart_exited.sh havia ressuscitado exp_01 (onda 1) durante a onda 2 → 3 emuladores, memória 24g/31g usados só 6g livre = quebra da concorrência-2 do mop-up e risco de reacender OOM. `docker stop` deu exit=137 (cron reiniciaria) → `docker rm exp_01` para não ressuscitar (results no bind-mount host preservados; compose down final do mop-up lida com ausência). Pós-remoção: memória 10g/31g usados, 20g livre, concorrência-2 restaurada. NOVO APRENDIZADO: cron pode ressuscitar container de onda MOP-UP já encerrada → após parar stray, REMOVER (rm), não só stop. Cauda ~665 err 100 % monkey/emulator-boot. Reboots: 26. Reagendado wakeup 05:00.

## Ciclo 2026-07-12 05:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.385** | **159** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.334 | 52 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.224 | 57 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.218** | **203** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·447 | 1.331 | 40 | 1.371 | 1.386 | 98,9 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·424 | 1.273 | 75 | 1.348 | 1.386 | 97,3 % |
| exp_03 | Up | 429·429·429 | 1.263 | 24 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.762 | **5.210** | **182** | **5.392** | **5.445** | **99,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.032** | **116** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.385 | 159 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.218 | 203 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.762 | 5.210 | 182 | 5.392 | 5.445 | 99,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.032 | 116 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.845** | **660** | **21.505** | **21.681** | **99,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:151, install/adb:7, timeout:1
- m1: container exp_02 docker=gone (ok=1345 fail=41)
- m1: container exp_03 docker=gone (ok=1349 fail=37)
- m2: erros → emulator/boot:179, install/adb:24
- m3: erros → emulator/boot:170, install/adb:12
- m4: erros → emulator/boot:110, install/adb:5, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)
- m4: container exp_01 docker=gone (ok=1277 fail=10)

## Ciclo 2026-07-12 05:02:25 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.385** | **159** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.334 | 52 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.224 | 57 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.310 | 58 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.218** | **203** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·448 | 1.332 | 40 | 1.372 | 1.386 | 99,0 % |
| exp_01 | Up | 462·462·462 | 1.343 | 43 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·424 | 1.273 | 75 | 1.348 | 1.386 | 97,3 % |
| exp_03 | Up | 429·429·429 | 1.263 | 24 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.763 | **5.211** | **182** | **5.393** | **5.445** | **99,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.252 | 35 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.032** | **116** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.385 | 159 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.218 | 203 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.763 | 5.211 | 182 | 5.393 | 5.445 | 99,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.032 | 116 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.846** | **660** | **21.506** | **21.681** | **99,2 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:151, install/adb:7, timeout:1
- m1: container exp_02 docker=gone (ok=1345 fail=41)
- m1: container exp_03 docker=gone (ok=1349 fail=37)
- m2: erros → emulator/boot:179, install/adb:24
- m3: erros → emulator/boot:170, install/adb:12
- m4: erros → emulator/boot:110, install/adb:5, timeout:1
- m4: container exp_00 docker=exited (ok=1245 fail=42)
- m4: container exp_01 docker=gone (ok=1277 fail=10)

**Ações (05:02 local):** ok real 20.846/21.681 = 96,15 % (err 660, rem 175; Δok +26 desde 04:04). Nenhuma intervenção — todos os containers esperados Up, sem strays (remoção do exp_01 na m4 se manteve). m1: MOP-UP onda 1 na ÚLTIMA passada (p300, desde 04:10 local; exp_00/01 Up). m2: viva, re-walking p180 (5/5 Up; err 207→203). m3: p300 avançando bem (rem 74→53, feito 99,0 %; ponta da cauda). m4: MOP-UP onda 2 na ÚLTIMA passada (p300; exp_02/03 Up, exp_01 removido). Cauda ~660 err 100 % monkey/emulator-boot. Reboots: 26. A VIGIAR no próx. ciclo: (1) "MOPUP m4 concluido" → medir recuperação de err; (2) m4 depois pode precisar de retry FASE 2 se residual persistir; (3) m3 conclusão do walk p300. Reagendado wakeup 06:00.

## Ciclo 2026-07-12 06:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | exit | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.387** | **157** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.334 | 52 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.225 | 56 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.311 | 57 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.220** | **201** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·459 | 1.343 | 40 | 1.383 | 1.386 | 99,8 % |
| exp_01 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·435 | 1.281 | 78 | 1.359 | 1.386 | 98,1 % |
| exp_03 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.785 | **5.232** | **183** | **5.415** | **5.445** | **99,4 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.033** | **115** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.387 | 157 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.220 | 201 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.785 | 5.232 | 183 | 5.415 | 5.445 | 99,4 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.033 | 115 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.872** | **656** | **21.528** | **21.681** | **99,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:150, install/adb:5, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_03 docker=exited (ok=1349 fail=37)
- m2: erros → emulator/boot:178, install/adb:23
- m3: erros → emulator/boot:173, install/adb:10
- m4: erros → emulator/boot:110, install/adb:4, timeout:1
- m4: container exp_00 docker=gone (ok=1245 fail=42)
- m4: container exp_01 docker=gone (ok=1277 fail=10)
- m4: container exp_02 docker=gone (ok=1258 fail=29)
- m4: container exp_03 docker=gone (ok=1253 fail=34)

## Ciclo 2026-07-12 06:04:29 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | exit | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.387** | **157** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.334 | 52 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.225 | 56 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.311 | 57 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.220** | **201** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·460 | 1.344 | 40 | 1.384 | 1.386 | 99,9 % |
| exp_01 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·436 | 1.282 | 78 | 1.360 | 1.386 | 98,1 % |
| exp_03 | Up | 429·429·429 | 1.264 | 23 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.787 | **5.234** | **183** | **5.417** | **5.445** | **99,5 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.245 | 42 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.033** | **115** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.387 | 157 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.220 | 201 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.787 | 5.234 | 183 | 5.417 | 5.445 | 99,5 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.033 | 115 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.874** | **656** | **21.530** | **21.681** | **99,3 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:150, install/adb:5, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m1: container exp_03 docker=exited (ok=1349 fail=37)
- m2: erros → emulator/boot:178, install/adb:23
- m3: erros → emulator/boot:173, install/adb:10
- m4: erros → emulator/boot:110, install/adb:4, timeout:1

**Ações (06:04 local):** ok real 20.874/21.681 = 96,28 % (err 656, rem 151; Δok +28 desde 05:02). AÇÕES: (1) **m1 estava TRAVADA** (banner-exchange timeout 2×, RUNNING no gcloud, load avg **93.96**); voltou na 3ª tentativa (ConnectTimeout 60). Causa: mop-up avançou p/ **onda 2** (exp_02+exp_03) e o cron **ressuscitou stray exp_01** (onda 1) → 3 emuladores → OOM matou exp_03 (Exit 137) + thrash. NÃO resetei (VM respondeu). **Removido stray exp_01** (stop+rm) → onda 2 segue com 2 containers; o mop-up recria exp_03 na passada p180. (2) **m4 mop-up CONCLUÍDO** (05:24 local): recuperação modesta err 125→115 (−10; residual 24@p180 + 91@p300, tudo monkey/OOM). m4 idle → disparado **retry FASE 2** (4/4 Up, procs=3). (3) m2 chegou à p300 (5/5 Up). (4) m3 rem 53→30, feito 99,5 % (quase fechando). Cauda ~656 err 100 % monkey/emulator-boot. Reboots: 26. APRENDIZADO: mop-up recupera pouco (−10) quando residual é tail-p300 duro; após 2ª tentativa (retry FASE 2 m4) sem ganho → documentar residual. A VIGIAR: m1 stray na transição de onda (recorrente — cron ressuscita a cada 10min); m3 fim do walk; m4 ganho do retry FASE 2. Reagendado wakeup 07:00.

## Ciclo 2026-07-12 07:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.388** | **156** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.337 | 49 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.227 | 54 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.312 | 56 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.226** | **195** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.347 | 39 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·447 | 1.292 | 79 | 1.371 | 1.386 | 98,9 % |
| exp_03 | Up | 429·429·429 | 1.266 | 21 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.800 | **5.249** | **181** | **5.430** | **5.445** | **99,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.034** | **114** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.388 | 156 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.226 | 195 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.800 | 5.249 | 181 | 5.430 | 5.445 | 99,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.034 | 114 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.897** | **646** | **21.543** | **21.681** | **99,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:149, install/adb:5, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m2: erros → emulator/boot:173, install/adb:22
- m3: erros → emulator/boot:171, install/adb:10
- m4: erros → emulator/boot:111, install/adb:3

## Ciclo 2026-07-12 07:03:09 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.388** | **156** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.337 | 49 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.227 | 54 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.312 | 56 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.226** | **195** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.347 | 39 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.344 | 42 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·447 | 1.292 | 79 | 1.371 | 1.386 | 98,9 % |
| exp_03 | Up | 429·429·429 | 1.266 | 21 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.800 | **5.249** | **181** | **5.430** | **5.445** | **99,7 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.258 | 29 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.034** | **114** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.388 | 156 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.226 | 195 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.800 | 5.249 | 181 | 5.430 | 5.445 | 99,7 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.034 | 114 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.897** | **646** | **21.543** | **21.681** | **99,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:148, install/adb:6, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m2: erros → emulator/boot:173, install/adb:22
- m3: erros → emulator/boot:171, install/adb:10
- m4: erros → emulator/boot:110, install/adb:4

**Ações (07:03 local):** ok real 20.897/21.681 = 96,38 % (err 646, rem 138; Δok +23 desde 06:04). Nenhuma intervenção — **sem strays na m1 este ciclo** (exp_00 Exited-143 limpo, exp_01 removido segue gone; onda 2 exp_02+exp_03 na última passada p300). m2 p300 (5/5 Up, err 201→195). m3 quase fechando: rem 30→**15**, feito 99,7 %. m4 retry FASE 2 na p300 recuperando marginalmente (err 115→114) — confirma tail-p300 duro (após esta passada, se residual estável, DOCUMENTAR). Cauda ~646 err 100 % monkey/emulator-boot. Reboots: 26. A VIGIAR: fim das ondas/walks (m1 mop-up onda 2, m3, m4 retry) → medir residual final e decidir documentação. Reagendado wakeup 08:00.

## Ciclo 2026-07-12 08:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.388** | **156** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.337 | 49 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.234 | 47 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.317 | 51 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.238** | **183** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.349 | 37 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·458 | 1.303 | 79 | 1.382 | 1.386 | 99,7 % |
| exp_03 | Up | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.811 | **5.265** | **176** | **5.441** | **5.445** | **99,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.035** | **113** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.388 | 156 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.238 | 183 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.811 | 5.265 | 176 | 5.441 | 5.445 | 99,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.035 | 113 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.926** | **628** | **21.554** | **21.681** | **99,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:152, install/adb:3, timeout:1
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m2: erros → emulator/boot:174, install/adb:9
- m3: erros → emulator/boot:161, install/adb:15
- m4: erros → emulator/boot:107, install/adb:6

## Ciclo 2026-07-12 08:03:34 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·462 | 1.345 | 41 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.388** | **156** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.337 | 49 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·357 | 1.235 | 46 | 1.281 | 1.386 | 92,4 % |
| exp_03 | Up | 462·462·444 | 1.318 | 50 | 1.368 | 1.386 | 98,7 % |
| **total** | — | 1.848·1.848·1.725 | **5.240** | **181** | **5.421** | **5.544** | **97,8 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·459 | 1.304 | 79 | 1.383 | 1.386 | 99,8 % |
| exp_03 | Up | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.812 | **5.267** | **175** | **5.442** | **5.445** | **99,9 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.246 | 41 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.277 | 10 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.259 | 28 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.253 | 34 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.035** | **113** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.388 | 156 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.725 | 5.240 | 181 | 5.421 | 5.544 | 97,8 % |
| m3 | RUNNING | 1.815·1.815·1.812 | 5.267 | 175 | 5.442 | 5.445 | 99,9 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.035 | 113 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.930** | **625** | **21.555** | **21.681** | **99,4 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:152, install/adb:3, timeout:1
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m1: container exp_02 docker=exited (ok=1345 fail=41)
- m2: erros → emulator/boot:173, install/adb:8
- m3: erros → emulator/boot:161, install/adb:14
- m4: erros → emulator/boot:107, install/adb:6

**Ações (08:03 local):** ok real 20.930/21.681 = 96,54 % (err 625, rem 127; Δok +32 desde 07:03 — melhor Δ da série). Nenhuma intervenção necessária. m1: MOP-UP onda 2 na última passada p300 (exp_03 rodando sozinho, vivo boot 45s; exp_02 deu OOM Exit-137 mas memória abundante 5g/31g usados 22g livre → deixado fechar; se cron reativar exp_02 ≤2 containers=OK, só remover se virar 3; exp_00 Exited-143 e exp_01 gone limpos). m2: p300 recuperando BEM (err 195→181, −14; rem 123 mas convertendo). m3: **rem 4, feito 99,9 %** — deve fechar o walk no próximo ciclo (aí retry FASE 2 se residual só-ERROR). m4: retry FASE 2 marginal (err 114→113); tail-p300 duro confirmado. Cauda ~625 err 100 % monkey/emulator-boot. Reboots: 26. A VIGIAR: m3 conclusão iminente; "MOPUP m1 concluido"; ganho final m4/m2. Reagendado wakeup 09:00.

## Ciclo 2026-07-12 09:00:02 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.351 | 35 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·366 | 1.242 | 48 | 1.290 | 1.386 | 93,1 % |
| exp_03 | Up | 462·462·452 | 1.327 | 49 | 1.376 | 1.386 | 99,3 % |
| **total** | — | 1.848·1.848·1.742 | **5.259** | **179** | **5.438** | **5.544** | **98,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.307 | 79 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.275** | **170** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.039** | **109** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.742 | 5.259 | 179 | 5.438 | 5.544 | 98,1 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.275 | 170 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.039 | 109 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.962** | **613** | **21.575** | **21.681** | **99,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:152, install/adb:2, timeout:1
- m1: container exp_00 docker=gone (ok=1352 fail=34)
- m1: container exp_01 docker=gone (ok=1341 fail=45)
- m1: container exp_02 docker=gone (ok=1346 fail=40)
- m1: container exp_03 docker=gone (ok=1350 fail=36)
- m2: erros → emulator/boot:172, install/adb:7
- m3: erros → emulator/boot:157, install/adb:13
- m4: erros → emulator/boot:106, install/adb:3

## Ciclo 2026-07-12 09:05:07 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.339 | 47 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.351 | 35 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·366 | 1.242 | 48 | 1.290 | 1.386 | 93,1 % |
| exp_03 | Up | 462·462·452 | 1.327 | 49 | 1.376 | 1.386 | 99,3 % |
| **total** | — | 1.848·1.848·1.742 | **5.259** | **179** | **5.438** | **5.544** | **98,1 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.307 | 79 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.275** | **170** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| exp_01 | Up | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | Up | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | Up | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.039** | **109** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.742 | 5.259 | 179 | 5.438 | 5.544 | 98,1 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.275 | 170 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.039 | 109 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.962** | **613** | **21.575** | **21.681** | **99,5 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:152, install/adb:2, timeout:1
- m2: erros → emulator/boot:172, install/adb:7
- m3: erros → emulator/boot:157, install/adb:13
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_02 docker=gone (ok=1307 fail=79)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:107, install/adb:2

**Ações (09:05 local):** ok real 20.962/21.681 = 96,68 % (err 613, rem 106; Δok +32 desde 08:03). AÇÃO: **m1 mop-up CONCLUÍDO** (08:30 local; recuperação total do mop-up modesta 160→155, −5; residual 155 = 6@p60+36@p180+113@p300, tail-p300 duro). m1 idle → disparado **retry FASE 2 final** (4/4 Up, procs=3) — se ganho <5, próximo passo é documentar residual. Demais: m2 p300 recuperando (rem 123→106, err 179; feito 98,1 %). m3 rem 0 (walk ainda rodando p300, convertendo ERROR; err 175→170). m4 retry FASE 2 recuperando (err 113→109). Cauda ~613 err 100 % monkey/emulator-boot. Reboots: 26. Δok série: 07:03=20.897 · 08:03=20.930 · 09:05=20.962 (+32/ciclo consistente). A VIGIAR: ganho do retry m1; conclusão dos walks m3/m4/m2 → decisão documentar vs. nova recuperação. Reagendado wakeup 10:00.

## Ciclo 2026-07-12 09:45:14 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.351 | 35 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·373 | 1.249 | 48 | 1.297 | 1.386 | 93,6 % |
| exp_03 | Up | 462·462·460 | 1.334 | 50 | 1.384 | 1.386 | 99,9 % |
| **total** | — | 1.848·1.848·1.757 | **5.274** | **179** | **5.453** | **5.544** | **98,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.307 | 79 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.275** | **170** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.040** | **108** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.757 | 5.274 | 179 | 5.453 | 5.544 | 98,4 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.275 | 170 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.040 | 108 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.978** | **612** | **21.590** | **21.681** | **99,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:152, install/adb:2, timeout:1
- m2: erros → emulator/boot:172, install/adb:7
- m3: erros → emulator/boot:157, install/adb:13
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_02 docker=gone (ok=1307 fail=79)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:105, install/adb:3
- m4: container exp_00 docker=gone (ok=1248 fail=39)
- m4: container exp_01 docker=gone (ok=1278 fail=9)
- m4: container exp_02 docker=gone (ok=1260 fail=27)
- m4: container exp_03 docker=gone (ok=1254 fail=33)

**Ações (09:45 local):** m1 rodando retry Fase 2 (p180, 4/4 Up) — sem intervenção. m2 rodando walk p300 (exp_02 373/462, rem 91) — convertendo, sem intervenção. m3 e m4 com walk FECHADO (procs=0), residual só-ERROR. **Análise de causa-raiz do residual (a pedido):** o residual NÃO é OOM genérico espalhado — é 100% `monkey` (m4: 108/108; m3: 168/170), com as 10 demais tools 468/468 COMPLETED em TODOS os timeouts. Erros monotônicos no timeout (m4: 0@60·24@180·84@300; m3: 3@60·49@180·118@300). Logcat de um caso (paint@300) mostra app rodando normal (stream RVSEC-COV) e corte no meio SEM crash/ANR/OOM no log → kill externo mid-run (container/host OOM). m4 JÁ passou por mop-up 2-cont (concluido 08:24) + retry (109→108, ganho 1) → **lever 2-container esgotado** (2×16g=32g ainda >31 GiB, oversubscreve). **Retry cego suspenso em m3/m4 nesta passada** — decisão de lever (1-container serial vs documentar) levada ao usuário. Nenhum stray; free ~28-30g livres em m3/m4.

**Ações (09:55 local) — residual documentado (decisão do usuário):** residual é sistemático `monkey × timeout-longo` (OOM-kill mid-run), NÃO transitório. 4 VMs uniformes: ~99% dos ~612 net-ERROR são monkey; 10 demais tools ~100% COMPLETED; monotônico no timeout (60«180«300). Lever 2-container esgotado (m4 109→108; 2×16g=32g>31 GiB oversubscreve). Determinísticos: com.yogeshpaliyal.deepr (m2), inc.flide.vi8 (m3) falham todas as 9 identidades monkey. Doc: docs/residual/RESIDUAL_MONKEY.md + residual_m{1..4}.csv. **m3/m4 NÃO serão mais iterados** (ociosos, residual = limitação conhecida). m1/m2 seguem walk até fechar. Sem stray; free ~28-30g m3/m4.

## Ciclo 2026-07-12 10:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | Up | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.351 | 35 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·375 | 1.251 | 48 | 1.299 | 1.386 | 93,7 % |
| exp_03 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.761 | **5.278** | **179** | **5.457** | **5.544** | **98,4 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.307 | 79 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.275** | **170** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.040** | **108** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.761 | 5.278 | 179 | 5.457 | 5.544 | 98,4 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.275 | 170 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.040 | 108 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **20.982** | **612** | **21.594** | **21.681** | **99,6 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:150, install/adb:4, timeout:1
- m2: erros → emulator/boot:173, install/adb:6
- m3: erros → emulator/boot:157, install/adb:13
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_02 docker=gone (ok=1307 fail=79)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:105, install/adb:3
- m4: container exp_00 docker=gone (ok=1248 fail=39)
- m4: container exp_01 docker=gone (ok=1278 fail=9)
- m4: container exp_02 docker=gone (ok=1260 fail=27)
- m4: container exp_03 docker=gone (ok=1254 fail=33)

## Ciclo 2026-07-12 11:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 462·462·462 | 1.340 | 46 | 1.386 | 1.386 | 100,0 % |
| exp_01 | Up | 462·462·462 | 1.351 | 35 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·385 | 1.261 | 48 | 1.309 | 1.386 | 94,4 % |
| exp_03 | Up | 462·462·462 | 1.336 | 50 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.771 | **5.288** | **179** | **5.467** | **5.544** | **98,6 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·462 | 1.308 | 78 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.276** | **169** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | Up | 429·429·429 | 1.248 | 39 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.040** | **108** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | RUNNING | 1.848·1.848·1.771 | 5.288 | 179 | 5.467 | 5.544 | 98,6 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.276 | 169 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.040 | 108 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **15.604** | **456** | **16.060** | **16.137** | **99,5 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: erros → emulator/boot:172, install/adb:7
- m3: erros → emulator/boot:157, install/adb:12
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:105, install/adb:3
- m4: container exp_01 docker=gone (ok=1278 fail=9)
- m4: container exp_02 docker=gone (ok=1260 fail=27)
- m4: container exp_03 docker=gone (ok=1254 fail=33)

## Ciclo 2026-07-12 12:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 13:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ssh timeout (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 14:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·402 | 1.323 | 3 | 1.326 | 1.386 | 95,7 % |
| exp_03 | Up | 462·462·471 | 1.391 | 4 | 1.395 | 1.386 | 100,6 % |
| **total** | — | 1.848·1.848·1.797 | **5.486** | **7** | **5.493** | **5.544** | **99,1 %** |

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | RUNNING | 1.848·1.848·1.797 | 5.486 | 7 | 5.493 | 5.544 | 99,1 % |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **5.486** | **7** | **5.493** | **5.544** | **99,1 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: erros → emulator/boot:6, install/adb:1
- m2: container exp_00 docker=gone (ok=1386 fail=0)
- m2: container exp_01 docker=gone (ok=1386 fail=0)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 15:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·412 | 1.333 | 3 | 1.336 | 1.386 | 96,4 % |
| exp_03 | Up | 462·462·480 | 1.400 | 4 | 1.404 | 1.386 | 101,3 % |
| **total** | — | 1.848·1.848·1.816 | **5.505** | **7** | **5.512** | **5.544** | **99,4 %** |

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | RUNNING | 1.848·1.848·1.816 | 5.505 | 7 | 5.512 | 5.544 | 99,4 % |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **5.505** | **7** | **5.512** | **5.544** | **99,4 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: erros → emulator/boot:6, install/adb:1
- m2: container exp_00 docker=gone (ok=1386 fail=0)
- m2: container exp_01 docker=gone (ok=1386 fail=0)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 16:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_02 | Up | 462·462·422 | 1.343 | 3 | 1.346 | 1.386 | 97,1 % |
| exp_03 | Up | 462·462·490 | 1.410 | 4 | 1.414 | 1.386 | 102,0 % |
| **total** | — | 1.848·1.848·1.836 | **5.525** | **7** | **5.532** | **5.544** | **99,8 %** |

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | RUNNING | 1.848·1.848·1.836 | 5.525 | 7 | 5.532 | 5.544 | 99,8 % |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **5.525** | **7** | **5.532** | **5.544** | **99,8 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: erros → emulator/boot:6, install/adb:1
- m2: container exp_00 docker=gone (ok=1386 fail=0)
- m2: container exp_01 docker=gone (ok=1386 fail=0)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 17:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | exit | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·429 | 1.350 | 3 | 1.353 | 1.386 | 97,6 % |
| exp_03 | gone | 462·462·495 | 1.416 | 3 | 1.419 | 1.386 | 102,4 % |
| **total** | — | 1.848·1.848·1.848 | **5.538** | **6** | **5.544** | **5.544** | **100,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.309 | 77 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.277** | **168** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.039** | **109** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.848 | 5.538 | 6 | 5.544 | 5.544 | 100,0 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.277 | 168 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.039 | 109 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **21.243** | **438** | **21.681** | **21.681** | **100,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:149, install/adb:4, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=exited (ok=1341 fail=45)
- m1: container exp_02 docker=exited (ok=1346 fail=40)
- m1: container exp_03 docker=exited (ok=1350 fail=36)
- m2: erros → emulator/boot:6
- m2: container exp_00 docker=gone (ok=1386 fail=0)
- m2: container exp_01 docker=gone (ok=1386 fail=0)
- m2: container exp_02 docker=gone (ok=1350 fail=3)
- m2: container exp_03 docker=gone (ok=1416 fail=3)
- m3: erros → emulator/boot:157, install/adb:11
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_02 docker=gone (ok=1309 fail=77)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:106, install/adb:3
- m4: container exp_00 docker=gone (ok=1247 fail=40)
- m4: container exp_01 docker=gone (ok=1278 fail=9)
- m4: container exp_02 docker=gone (ok=1260 fail=27)
- m4: container exp_03 docker=gone (ok=1254 fail=33)

## Ciclo 2026-07-12 18:00:01 (local)

### m1
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | exit | 462·462·462 | 1.352 | 34 | 1.386 | 1.386 | 100,0 % |
| exp_01 | exit | 462·462·462 | 1.341 | 45 | 1.386 | 1.386 | 100,0 % |
| exp_02 | exit | 462·462·462 | 1.346 | 40 | 1.386 | 1.386 | 100,0 % |
| exp_03 | exit | 462·462·462 | 1.350 | 36 | 1.386 | 1.386 | 100,0 % |
| **total** | — | 1.848·1.848·1.848 | **5.389** | **155** | **5.544** | **5.544** | **100,0 %** |

### m2
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.386 | 0 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·429 | 1.350 | 3 | 1.353 | 1.386 | 97,6 % |
| exp_03 | gone | 462·462·495 | 1.416 | 3 | 1.419 | 1.386 | 102,4 % |
| **total** | — | 1.848·1.848·1.848 | **5.538** | **6** | **5.544** | **5.544** | **100,0 %** |

### m3
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 462·462·462 | 1.353 | 33 | 1.386 | 1.386 | 100,0 % |
| exp_01 | gone | 462·462·462 | 1.348 | 38 | 1.386 | 1.386 | 100,0 % |
| exp_02 | gone | 462·462·462 | 1.309 | 77 | 1.386 | 1.386 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.267 | 20 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.815·1.815·1.815 | **5.277** | **168** | **5.445** | **5.445** | **100,0 %** |

### m4
| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|
| exp_00 | gone | 429·429·429 | 1.247 | 40 | 1.287 | 1.287 | 100,0 % |
| exp_01 | gone | 429·429·429 | 1.278 | 9 | 1.287 | 1.287 | 100,0 % |
| exp_02 | gone | 429·429·429 | 1.260 | 27 | 1.287 | 1.287 | 100,0 % |
| exp_03 | gone | 429·429·429 | 1.254 | 33 | 1.287 | 1.287 | 100,0 % |
| **total** | — | 1.716·1.716·1.716 | **5.039** | **109** | **5.148** | **5.148** | **100,0 %** |

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | RUNNING | 1.848·1.848·1.848 | 5.389 | 155 | 5.544 | 5.544 | 100,0 % |
| m2 | RUNNING | 1.848·1.848·1.848 | 5.538 | 6 | 5.544 | 5.544 | 100,0 % |
| m3 | RUNNING | 1.815·1.815·1.815 | 5.277 | 168 | 5.445 | 5.445 | 100,0 % |
| m4 | RUNNING | 1.716·1.716·1.716 | 5.039 | 109 | 5.148 | 5.148 | 100,0 % |
| **TOTAL** | — | — | **21.243** | **438** | **21.681** | **21.681** | **100,0 %** |

**Problemas / eventos:**
- m1: erros → emulator/boot:149, install/adb:4, timeout:2
- m1: container exp_00 docker=exited (ok=1352 fail=34)
- m1: container exp_01 docker=exited (ok=1341 fail=45)
- m1: container exp_02 docker=exited (ok=1346 fail=40)
- m1: container exp_03 docker=exited (ok=1350 fail=36)
- m2: erros → emulator/boot:6
- m2: container exp_00 docker=gone (ok=1386 fail=0)
- m2: container exp_01 docker=gone (ok=1386 fail=0)
- m2: container exp_02 docker=gone (ok=1350 fail=3)
- m2: container exp_03 docker=gone (ok=1416 fail=3)
- m3: erros → emulator/boot:157, install/adb:11
- m3: container exp_00 docker=gone (ok=1353 fail=33)
- m3: container exp_01 docker=gone (ok=1348 fail=38)
- m3: container exp_02 docker=gone (ok=1309 fail=77)
- m3: container exp_03 docker=gone (ok=1267 fail=20)
- m4: erros → emulator/boot:106, install/adb:3
- m4: container exp_00 docker=gone (ok=1247 fail=40)
- m4: container exp_01 docker=gone (ok=1278 fail=9)
- m4: container exp_02 docker=gone (ok=1260 fail=27)
- m4: container exp_03 docker=gone (ok=1254 fail=33)

---

**Validação pós-campanha (2026-07-12, sessão local):** (1) **Cross-check remoto×local FECHOU com diff 0** nas 4 VMs (m1=5.544, m2=5.544, m3=5.445, m4=5.148; total 21.681). Nota operacional: m1/m3/m4 mudaram de IP externo ao religar (efêmero GCP) — IPs reconferidos via `gcloud compute instances list`. VMs deixadas RUNNING para o usuário parar. (2) **Métrica real por RVSEC-COV**: dos 21.681 logcats >0 B, **21.446 (98,92%) têm RVSEC-COV** e **235 (1,08%) não têm** (88–117 B, só cabeçalhos de stream = app nunca subiu). (3) **Causa-raiz dos 235 fechada**: 189 = `qtesting × no_launchable_activity` — determinístico, 21 APKs (9/9 execuções) cujo manifest declara MAIN/LAUNCHER só em `activity-alias` → `aapt dump badging` sem `launchable-activity` → qtesting lança `Intent { cmp=<pkg>/noactivityname }` → Error type 3 em loop; match 1:1 entre o conjunto qtesting-falho e o conjunto sem-launchable dos 219 APKs; contraprova: mesmos APKs saudáveis nas outras 10 tools. Os outros 46 = infra transitória (adb/emulador indisponível na janela: ares/appium timeout, droidbot `device not found`, droidmate `handleTargetAbsence`, 1 qtesting `waiting for device`). (4) **Docs**: `docs/residual/NOCOV_LOGCATS.md` + `docs/residual/nocov_235.csv` (lista completa com classe de motivo). qtesting cobre efetivamente 198/219 APKs (threat to validity para o artigo). (5) smoke NÃO veio na cópia local (gate do consolidate não bloqueia); STATIC_DIR com 219 .apk.json confirmado. Consolidação AGUARDA autorização.

## Ciclo 2026-07-12 19:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 20:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 21:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 22:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-12 23:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 00:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 01:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 02:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 03:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 04:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 05:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 06:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 07:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 08:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 09:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 10:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 11:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 12:00:02 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m2: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m3: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)
- m4: SSH inacessível — ERROR: (gcloud.compute.ssh) [/usr/bin/ssh] exited with return code [255]. (sem ação)

## Ciclo 2026-07-13 13:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 14:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 15:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 16:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 17:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 18:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 19:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 20:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 21:00:02 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 22:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-13 23:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 00:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 01:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 02:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 03:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 04:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 05:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 06:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 07:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 08:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 09:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 10:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 11:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)

## Ciclo 2026-07-14 12:00:01 (local)

### m1
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m2
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m3
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### m4
_estado: SSH_FALHOU — sem dados de container neste ciclo._

### Resumo geral
| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|
| m1 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m2 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m3 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| m4 | SSH_FALHOU | — | ? | ? | ? | ? | ? |
| **TOTAL** | — | — | **0** | **0** | **0** | **0** | **0,0 %** |

**Problemas / eventos:**
- m1: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m1-exp02' was not found (sem ação)
- m2: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m2-exp02' was not found (sem ação)
- m3: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m3-exp02' was not found (sem ação)
- m4: SSH inacessível —  - The resource 'projects/research-318211/zones/us-central1-f/instances/m4-exp02' was not found (sem ação)
