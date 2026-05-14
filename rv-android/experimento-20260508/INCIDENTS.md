# Incidentes — Experimento RV-Android (dispatch 2026-05-08 21:50 BRT)

Registro cronológico de tudo que saiu do esperado. Cada entrada: data/hora BRT, VM/container, sintoma, diagnóstico, ação, impacto.

## 2026-05-09 02:59 — m1-exp02 / exp_00 — OOM (exit 137)

- **Sintoma**: container morto há ~2h quando descoberto às ~04:55 BRT. `docker ps -a` mostrou `Exited (137) 2 hours ago`.
- **Estado no kill**: monkey rodando em `com.leekleak.trafficlight_25.apk`, coverage updates fluindo (Methods 21.92 %, MOP 25.93 %).
- **Diagnóstico**: exit 137 = SIGKILL, padrão de OOM killer. m1 é n2-standard-16 (64 GB RAM). 4 containers × 8 GB = 32 GB alocados → folga grande, então OOM provavelmente veio de spawn de docker-sibling (ARES/QTesting) que cresceu fora do limite de 8 GB do exp_00.
- **Ação**: às 04:55 BRT, `docker compose --env-file .env.m1 up -d exp_00` → retomado com auto-resume (132 tasks completadas estavam intactas em `tasks.json`).
- **Impacto**: ~5h de execução perdida só para exp_00. Auto-resume retomou de onde parou. Sem perda de dados em `tasks.json`. Container exp_00 ficou ~60 tasks atrás dos outros 3 da m1.

## 2026-05-09 ~05:52 — m1-exp02 / exp_01 — adb install hung

- **Sintoma**: descoberto às 09:14 BRT que exp_01 não progrediu desde 06:13 (3h). docker stats mostrava CPU 6 %, RAM 5.6 / 8 GB (vivo, sem progresso).
- **Estado**: log parou em `Installing APK: com.vishaltelangre.nerdcalci_371.apk on emulator-5554` (timestamp 05:52:01). adb install pendurou.
- **Diagnóstico**: `adb install` hangueou. O `rv-platform` não tem timeout para a etapa de instalação — só para a execução do tool. APK atravessado.
- **Ação**: `docker restart exp_01` às 09:14. Auto-resume tomou conta — a task incompleta (`com.vishaltelangre.nerdcalci_371.apk`) é retentada do início.
- **Impacto**: ~3h22 de execução perdida em exp_01 da m1. Sem perda de dados (a task pendurada nem chegou em `tasks.json`).

## 2026-05-09 ~10:00 (estimado) — m1-exp02 / exp_03 — OOM (exit 137)

- **Sintoma**: descoberto às 12:35 BRT, status "Exited (137) 2 hours ago".
- **Diagnóstico**: mesmo padrão do exp_00 m1 (provável docker-sibling).
- **Ação**: `docker compose up -d exp_03` às 12:35 → retomado.
- **Impacto**: ~2h de execução perdida.

## 2026-05-09 ~09:30 (estimado) — m2-exp02 / exp_02 — OOM (exit 137)

- **Sintoma**: descoberto às 12:35 BRT, status "Exited (137) 3 hours ago".
- **Diagnóstico**: m2 é n2-custom-16-32768 (32 GB RAM). 4 containers × 8 GB = 32 GB → **sem buffer para o OS**. Quando docker-sibling cresce, OOM killer mata o container que está consumindo mais.
- **Ação**: retomado às 12:35 BRT.
- **Impacto**: ~3h de execução perdida.

## 2026-05-09 ~11:48 — m3-exp02 / exp_00 — OOM (exit 137)

- **Sintoma**: descoberto às 12:35 BRT, status "Exited (137) 47 minutes ago".
- **Diagnóstico**: mesmo padrão. m3 também é 32 GB.
- **Ação**: retomado às 12:35 BRT.
- **Impacto**: ~47 min de execução perdida.

## 2026-05-10 ~01:11 — m1-exp02 / exp_00 — OOM (exit 137)

- **Sintoma**: descoberto às 01:42 BRT no loop horário, status "Exited (137) 31 minutes ago".
- **Diagnóstico**: 4º OOM da campanha. Mesmo padrão de docker-sibling crescendo além do limite de 8 GB.
- **Ação**: `EXP_TIMEOUT=180 docker compose --env-file .env.m1 up -d exp_00` às 01:42 BRT → retomado, auto-resume preserva tasks já feitas (T60 1617 + T180 ~135 da m1 inteira).
- **Impacto**: ~31 min de execução perdida em exp_00 da m1.

## 2026-05-10 ~10:53 — m3-exp02 / exp_00 — OOM (exit 137)

- **Sintoma**: descoberto às 11:01 BRT no loop horário, status "Exited (137) 8 minutes ago".
- **Diagnóstico**: 5º OOM da campanha. m3 (32 GB), 2º OOM nesta VM (1º foi às 11:48 BRT 09/05).
- **Ação**: `EXP_TIMEOUT=180 docker compose --env-file .env.m3 up -d exp_00` às 11:01 BRT → retomado.
- **Impacto**: ~8 min de execução perdida.

## 2026-05-10 ~12:08 — m2-exp02 / exp_02 — OOM (exit 137)

- **Sintoma**: descoberto às 13:06 BRT no loop horário, status "Exited (137) 58 minutes ago".
- **Diagnóstico**: 7º OOM da campanha. m2 (32 GB), 2º OOM nesta VM (1º foi às ~09:30 BRT 09/05).
- **Ação**: `EXP_TIMEOUT=180 docker compose --env-file .env.m2 up -d exp_02` às 13:06 BRT → retomado.
- **Impacto**: ~58 min de execução perdida.

## 2026-05-10 ~12:30 — m1-exp02 / exp_03 — OOM (exit 137)

- **Sintoma**: descoberto às 13:06 BRT no loop horário, status "Exited (137) 36 minutes ago".
- **Diagnóstico**: 6º OOM da campanha. m1 (64 GB), 1º OOM em exp_03 desta VM.
- **Ação**: `EXP_TIMEOUT=180 docker compose --env-file .env.m1 up -d exp_03` às 13:06 BRT → retomado.
- **Impacto**: ~36 min de execução perdida.

## 2026-05-11 ~06:28 — m1-exp02 / exp_00 — OOM (exit 137) — durante T300

- **Sintoma**: descoberto às 06:40 BRT no loop horário, status "Exited (137) 12 minutes ago".
- **Diagnóstico**: 8º OOM da campanha, 3º em m1/exp_00 (1º em 02:59 BRT 09/05, 2º em 12:30 BRT 10/05 em exp_03). Primeiro OOM em pass T300 (tasks de 5 min). m1 (64 GB) — provável crescimento do docker-sibling.
- **Ação**: `EXP_TIMEOUT=300 docker compose --env-file .env.m1 up -d exp_00` às 06:40 BRT → retomado.
- **Impacto**: ~12 min de execução T300 perdida.

## 2026-05-11 ~23:20 — m1-exp02 / exp_03 — OOM (exit 137) — durante T300

- **Sintoma**: descoberto às 00:20 BRT 12/05 no loop horário, status "Exited (137) About an hour ago".
- **Diagnóstico**: 9º OOM da campanha, 2º em m1/exp_03 (1º em 12:30 BRT 10/05). Segundo OOM em pass T300 (1º foi m1/exp_00 às ~06:28). Tarefa T300=329 quando matou.
- **Ação**: `EXP_TIMEOUT=300 docker compose --env-file .env.m1 up -d exp_03` às 00:20 BRT 12/05 → retomado.
- **Impacto**: ~1h de execução T300 perdida.

## 2026-05-12 ~00:30 — m2-exp02 / exp_02 — OOM (exit 137) — durante T300

- **Sintoma**: descoberto às 01:22 BRT 12/05 no loop horário, status "Exited (137) 52 minutes ago".
- **Diagnóstico**: 10º OOM da campanha, 2º em m2/exp_02 (1º em 12:08 BRT 10/05). T300=317 quando matou.
- **Ação**: `EXP_TIMEOUT=300 docker compose --env-file .env.m2 up -d exp_02` às 01:22 BRT 12/05 → retomado.
- **Impacto**: ~52 min de execução T300 perdida.

## 2026-05-12 ~06:49 — m1-exp02 / exp_02 — OOM (exit 137) — durante T300 final

- **Sintoma**: descoberto às 07:03 BRT 12/05, status "Exited (137) 14 minutes ago".
- **Diagnóstico**: 11º OOM da campanha. Tarefa T300=395 (1 task do cap 396). m1 (64 GB) — provável docker-sibling.
- **Ação**: `EXP_TIMEOUT=300 docker compose --env-file .env.m1 up -d exp_02` às 07:03 BRT → retomado.
- **Impacto**: ~14 min de execução T300 final perdida.

## 2026-05-12 ~00:45 — m3-exp02 / exp_02 — Exit 0 (FIM legítimo T300)

- **Sintoma**: descoberto às 01:22 BRT, status "Exited (0) 37 minutes ago", T300=396/396.
- **Diagnóstico**: completou T300 com 396/396 tasks (cap do batch 12-APK). FIM legítimo.
- **Ação**: nenhuma — aguardando demais containers m3 finalizarem.

## 2026-05-11 ~21:30 — m4-exp04 / exp_02 e exp_03 — Exit 0 (FIM legítimo T300)

- **Sintoma**: descoberto às 23:18 BRT 11/05, ambos em Exit 0 há ~50 min.
- **Diagnóstico**: terminaram T300 com 363/363 tasks cada (cap do batch 11-APK). FIM legítimo, não restart.
- **Ação**: nenhuma — aguardando exp_00/01 da m4 terminarem para script encerrar.
- **Impacto**: nenhum.

## 2026-05-09 12:35 — m2-exp02 / exp_01 e m4-exp04 / exp_02 e exp_03 — Exit 0 (saída limpa)

- **Sintoma**: 3 containers em Exit 0 esperando `docker wait` no script `run_experiment.sh`.
- **Diagnóstico**: cada um completou todas as tasks da passada `timeout=60` antes dos demais containers da mesma VM. O `rv-experiment` saiu naturalmente. O script `run_experiment.sh` está em `docker wait exp_00 exp_01 exp_02 exp_03` — bloqueia até **todos os 4** terminarem antes de avançar para `timeout=180`.
- **Ação**: nenhuma necessária. Vão ficar aguardando até os outros completarem o pass 60s.
- **Impacto**: nenhum (comportamento esperado do `docker wait`).

---

## Padrão geral

- **3 OOMs em 15h** (taxa ~1 OOM / 5h). Em 50h totais: ~10 OOMs esperados. Auto-resume mitiga, mas perde wall-clock.
- **VMs com 32 GB** (m2, m3, m4) mais vulneráveis: 4 × 8 GB de limite Docker = 32 GB total, sem folga para o OS.
- **adb install hang** (1 incidente até agora) — não previsível, indeterministico. Sem timeout no `rv-platform`. Watchdog seria útil mas user descartou.

## Mitigação possível (não aplicada agora)

1. **Reduzir limit RAM/container nas 32 GB VMs**: 4 × 6 GB = 24 GB → deixa 8 GB pro OS. Diminui paralelismo dentro do container (Java + emulator + ARES/QTesting + docker-sibling).
2. **Aumentar tipo das VMs m2/m3/m4** para n2-standard-16 (64 GB), espelhando m1.
3. **Watchdog automático** que detecta containers parados (output de log estático) e dá `docker restart`.

Por agora: monitor manual + auto-resume.
