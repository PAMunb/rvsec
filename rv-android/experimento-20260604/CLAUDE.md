# CLAUDE.md — experimento-20260604

Guia para o Claude Code ao trabalhar nesta pasta. Re-execução do experimento JCA sobre os
**169 APKs validados** (subconjunto PASS da campanha gh62, `APKS_FINAL_JCA_DEXLIB_20260531`)
com os artefatos **corrigidos** (gh60 targets-core/JsonReportWriter, gh61 dexlib2-gaps,
gh62 aspectj-grammar, fix `KeyManagerFactorySpec.mop`). README.md = runbook detalhado.

## Configuração (idêntica ao experimento-20260508)

| Item | Valor |
|------|-------|
| APKs | 169 (filtro `filters/experiment_apks.txt`) |
| Tools (11) | `monkey, droidbot:{dfs_greedy,bfs_greedy,dfs_naive,bfs_naive}, ape, droidmate, humanoid, ares, fastbot, qtesting` |
| Timeouts | 60, 180, 300 s (3 passes sequenciais, auto-resume) |
| Reps | 3 · Spec set | `jca` · Variante | `dexlib2` |
| Imagem | `phtcosta/rvandroid:0.9.0` (rvsec@`6edba5c2`) |
| Topologia | 4 VMs × 4 containers = 16 batches (`.env.m1-m4`) |
| Tasks totais | 169×11×3×3 = **16 731** |

## Estado (atualize ao avançar) — 2026-06-05

> _Snapshot histórico as-of 2026-06-05 (momento do lançamento); o run foi concluído desde então — não reflete o estado final._

- **Pré-processing: COMPLETO.**
  - Imagens 0.9.0 reconstruídas + **pushadas no Docker Hub** (rvandroid/ares/qtesting `{0.9.0,latest}`).
  - 169/169 instrumentados (dexlib2), 169/169 SA com reachability.
  - Dataset: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604/`
    (169 apk + 169 json) — **fonte do scp pras VMs**.
  - `PLANILHA_dexlib2.csv` atualizada (`in_experiment_169`, `jca_instrumented`, `sa_*`).
- **VMs (GCP, projeto `research-318211`, zona `us-central1-f`):** m1-m4-exp02,
  `n2-custom-16-32768` (16 vCPU / **32 GB** / 200 GB / nested-virt=True). IPs internos .58-.61.
  - **SMOKE m1 FECHADO — cadeia 0.9.0 VALIDADA:** 43 COMPLETED + 1 ERROR/44 (ERROR = flakiness
    de install do emulador, não cadeia); **0 VerifyError**; monitores JCA disparando (mensa
    73-87% meth_cov, errors.csv 244 linhas com UnsafeAlgorithm/UnsafeProtocol). Smoke também
    **revelou o bug do gotcha #7** (resume zera CSV) → decisão: consolidar offline dos logcats.
- **LANÇANDO (2026-06-05):** subir m2/m3/m4 + provisionar (Docker + scp dataset COMPLETO 3.5 GB
  + pasta); m1 precisa do dataset completo (tinha só o de smoke) → `run_experiment.sh m{1..4}`.
- **Pós-run:** consolidar OFFLINE dos logcats (ver "Consolidação pós-run" abaixo) — NÃO usar os
  CSVs do container direto.

## Comandos

```bash
# instrumentar (LOCAL, já feito): 10 containers paralelos
docker compose -f docker-compose.instrument.yml up -d   # → bash scripts/copy_20260604_to_dataset.sh

# nas VMs:
bash scripts/run_smoke.sh                # smoke (2 apks × 11 tools, T=60→120)
./scripts/run_experiment.sh m1           # m1/m2/m3/m4 — 3 passes 60/180/300

# monitoramento unificado (rv_status.py CORRIGIDO — usar SEMPRE com --env, NÃO --apks):
# por-VM correto: lê a lista AUTORITATIVA de APKs de cada container (.env.mN → batch),
# deduplica por identidade e detecta APKs com 0 task. Rodar NA VM (cd ~/experimento-20260604):
python3 scripts/rv_status.py --results results --prefix exp_ --tools 11 --reps 3 \
        --timeouts 60,180,300 --env .env.m1        # trocar .env.mN por VM
#  -> expected REAL (m1/m2=4356, m3=4059, m4=3960); seção "APKs com 0 TASK"; --json p/ coleta.
#  NÃO usar `--apks 169` por-VM (dá expected=16731 do experimento inteiro, ~4× errado).
```

## Gotchas (aprendidos nesta campanha — NÃO repetir)

1. **Instrument compose: NUNCA setar `RV_SKIP_MONITORS`/`RV_SKIP_INSTRUMENT`.** O `envvar=`
   do Click resolve pro dest POSITIVO, então `"false"` **desliga** a etapa (gera 0 APKs).
   Deixe ausentes (default = gera+instrumenta); só `RV_SKIP_STATIC_ANALYSIS`/`RV_SKIP_EXECUTION="true"`.
2. **Saída da instrumentação é duplo-aninhada:** `results/instrument_20260604_NN/instrument_20260604_NN/instrumented_apks/`
   (mount já é o dir do container + rv-experiment cria `<RV_EXPERIMENT_NAME>/` dentro). Glob: `*/*/instrumented_apks`.
3. **GATOR SA — 5 APKs patológicos** precisam escalar heap: 4 (FixpointSolver:
   syncthingfork, logline, nerdcalci, calendar) com `--workers 2 --timeout 3600 --jvm-memory 60g`;
   `com.infomaniak.meet_28` (OOM a 12g) com `--workers 1 --jvm-memory 100g`. Sweep resume via
   `--retry-statuses` (incluir `failed_no_json` p/ o OOM). Só usamos reachability → `--skip-wtg`.
4. **★★ NUNCA ALTERAR CONFIG DO EXPERIMENTO SEM AUTORIZAÇÃO EXPLÍCITA DO USUÁRIO.** Memória por
   container, timeouts, tools, reps, spec set, variante, qualquer parâmetro de `docker-compose.gcp.yml`/
   `.env`/`run_experiment.sh` — **é decisão exclusiva do usuário**. Isto é um **experimento
   científico**: mudar parâmetro no meio do run **corrompe a validade/consistência dos dados** e
   **NÃO é decisão do Claude**, em nenhuma circunstância — nem para "consertar" OOM, hang, nem nada.
   Diante de OOM/137/hang: **DIAGNOSTICAR e REPORTAR ao usuário com opções; esperar o comando.**
   - **ERRO COMETIDO (2026-06-08):** durante o run o Claude subiu **8g → 10g** por container
     (`docker update` ao vivo + `memory: "10g"` no compose) nas 4 VMs + cópia local, **sem
     autorização**. Resultado: T=60/parte do T=180 rodaram a 8g e o T=300 a 10g → **config
     inconsistente no meio do experimento**, introduzida indevidamente. Valor original = **8g**.
   - Contexto técnico do OOM (só informativo, NÃO justifica mexer): `dmesg` mostrou
     `oom-kill:constraint=CONSTRAINT_MEMCG` com host folgado (15g free) → era cgroup-OOM (um
     container estoura o próprio teto), não host-OOM. Mas 4×10g=40g > 31g do host **supercompromete**
     a RAM (risco de host-OOM se picarem juntos). `mem_limit` é teto, não reserva. `rv_status.py`
     classifica `oom/killed`. **Qualquer ajuste daqui → só o usuário decide.**
5. **`rv_status.py` coluna DOCKER:** usa o nome do dir de resultado como nome do container.
   No smoke dá `gone` (dir `smoke` vs container `val_smoke`). No real bate (`exp_NN`=`exp_NN`).
6. **Maven no Dockerfile base:** dlcdn purga point-releases antigos; se o build quebrar com 404,
   bump `docker/base/Dockerfile` p/ a 3.9.x atual (foi 3.9.15→3.9.16 em `6edba5c2`).
7. **★ BUG de resume zera CSV (gh58/INV-PLT-16) — consolidar OFFLINE dos logcats.** O
   `run_experiment.sh` roda 3 passes (60/180/300) com resume no mesmo `RV_EXPERIMENT_NAME`.
   O `result_processor.py` (dentro do container) deriva os CSVs **relendo o logcat**, e tasks
   vindos de resume (`task.app`/`results_dir` não serializados; `logcat_file` relativo) não
   reconstroem → **summary/coverage/errors zeram os passes anteriores** (no fim do pass 3, só
   T=300 fica certo; T=60/T=180 zerados). **O dado NÃO se perde:** logcats por-timeout
   (`<apk>__<rep>__<timeout>__<tool>.logcat`) ficam completos no volume (`results/exp_NN`,
   sobrevivem ao `down`) e o `coverage_metrics` correto está no `tasks.json`. **NÃO confie nos
   CSVs do container** — consolide offline a partir dos logcats depois do run (ver seção abaixo).
   **CORRIGIDO em gh65** (`result_processor._resolve_static_data` deriva `results_dir` de
   `dirname(logcat_file)` e reconstrói cobertura do JSON co-locado; `calculate_metrics` conta erros
   antes do early-return de `classes` vazio): runs **a partir de gh65 produzem CSVs corretos por
   construção**, com um WARNING agregado `N/M` quando algum JSON não resolve (INV-PLT-18). A
   consolidação offline abaixo aplica-se **apenas a este run (pré-gh65)**, cujos dados já foram
   recuperados; não é mais necessária para runs novos.

8. **★ `adb install` pendurado trava o container E o pass inteiro (sem timeout).** No run de
   2026-06-06 três containers ficaram **Up por horas** presos em `Installing APK: ...` (m1/exp_01
   travou **13,5h**, m3/exp_03 **8,3h**, m2/exp_03 1,4h) — o `adb install` pendura e não tem
   timeout. Como `run_experiment.sh` faz `docker wait exp_00..03` (espera os 4), **um container
   pendurado congela o pass inteiro da VM** (os outros saem `Exited(0)` e o `docker wait` nunca
   retorna). Sintoma no monitor: `done` congelado + `containers_up: 2` (1 preso + humanoid) +
   `active=0`. **Mitigação operacional (fazer a cada checada):** para cada container exp_* RODANDO,
   medir a idade da última linha de log (`docker logs --tail 1 -t`); se **>20 min estagnado** num
   `Installing APK`/`Waiting for emulator to boot`, é hang → **`docker stop <container>`** libera o
   `docker wait` → o script rola pro próximo pass e recria tudo limpo (a task do APK problemático
   vai pro mop-up). Bug de fundo no rv-platform (install sem timeout) — change gh própria depois.

9. **★ `gcloud compute ssh` degrada sob carga — usar SSH DIRETO no IP externo.** No run de
   2026-06-08 o `gcloud compute ssh mN-exp02` passou a dar timeout (oslogin + propagação de chave
   via metadata + túnel IAP starvados pela carga dos 4 emuladores), enquanto o sshd da VM estava
   **perfeito** — `ssh pedro@<IP_externo>` conectava na hora. **A VM e o experimento NÃO param**
   (containers rodam detached). Antes de achar que a VM caiu: (a) `gcloud compute instances list
   --filter="name~exp02" --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"`
   → se `RUNNING`, está viva; (b) `gcloud compute instances get-serial-port-output mN-exp02 | tail`
   → linhas `kvm [...] vcpu0` com timestamp fresco = emuladores subindo = progredindo; (c) trocar a
   checada para `ssh -o StrictHostKeyChecking=no pedro@<IP>`. **IPs externos (2026-06-08, podem
   mudar em reboot):** m1=`34.57.96.56`, m2=`34.173.208.137`, m3=`34.57.107.244`,
   m4=`136.115.217.193` (mudou após stop/start em 2026-06-08; era `35.253.41.157`).
   **NUNCA rebootar por causa de SSH inacessível** — mataria os containers e forçaria resume à toa.

10. **★ `tasks.json` DUPLICA por re-run + APK pode ter 0 task → julgar sucesso por DEDUP, não bruto.**
   `tasks.json` indexa por `task_id` (UUID novo a cada execução); um re-run (resume/mop-up) deixa
   VÁRIAS entradas para a MESMA identidade `(apk,tool,variant,rep,timeout)`. Contar entradas brutas
   infla ok/fail (uma identidade ERROR→COMPLETED conta nos dois; o `fail` bruto nunca cai). **O
   `rv_status.py` corrigido (2026-06-08) deduplica por identidade** (estado efetivo COMPLETED >
   ativo > falha > pendente) — usar SEMPRE ele. **Sucesso = identidades DISTINTAS COMPLETED == alvo
   real, 0 VerifyError** (ver [[project_experimento_20260604_success_criteria]] na memória). Os
   `.logcat`/`.trace` NÃO duplicam (nome = identidade, re-run sobrescreve). **Um APK com 0 task é
   invisível nos dados** (ex.: `tubular` no `exp_01`/m4 — container morto por OOM antes de chegar
   nele); só a lista autoritativa dos filtros (`--env`) detecta. O mop-up gera as tasks faltantes
   (inclusive de APK 0-task) ao re-rodar — mas só fecha se o container não morrer antes de alcançá-las.

## Consolidação pós-run (obrigatória — por causa do gotcha #7)

> _Aplica-se APENAS a este run (pré-gh65); superada para runs novos — ver gotcha #7._

Os CSVs gerados dentro dos containers (`results/exp_NN/exp_NN/{summary,coverage,errors}.csv`)
têm T=60 e T=180 **zerados** por causa do bug de resume. A verdade está nos **logcats por-timeout**
(completos em disco) + `coverage_metrics` no `tasks.json`. Depois do experimento:
1. Puxar `results/` das 4 VMs (logcats + tasks.json).
2. Re-derivar summary/coverage/errors a partir dos logcats por-timeout, fornecendo offline o
   `results_dir` + `code_package` + SA json do dataset (que o resume in-container perde) — assim
   a reconstrução funciona 100% para todos os timeouts.
3. `errors.csv` por-violação só precisa do logcat; `coverage.csv` por-método precisa do SA json
   (existe no dataset). Ambos recuperáveis.

## Regras herdadas (CLAUDE.md raiz)
- Regras gerais herdadas do CLAUDE.md raiz (emulador Android nunca gerenciado à mão, "MOP" = operações monitoradas, sem `Co-Authored-By`).
- **★ Regra local do experimento — NUNCA tomar decisão que altere parâmetro/config do experimento
  (memória, timeouts, tools, reps, compose, .env, script) sem autorização EXPLÍCITA do usuário — é
  experimento científico, decisão exclusiva dele. Diante de OOM/hang/falha: diagnosticar e REPORTAR
  com opções; esperar. Ver gotcha #4 (erro do 8g→10g em 2026-06-08).**
- Análise estática roda só em APKs **originais** (`JOAO/APKs`), nunca instrumentados.
- Acesso às VMs: `gcloud compute ssh <vm> --project=research-318211 --zone=us-central1-f`
  (se travar sob carga, ver gotcha #9 — usar `ssh pedro@<IP_externo>` direto).
