# Experimento RV-Android — Comparação de 11 Ferramentas com Verificação Runtime de JCA

Este documento descreve o experimento de comparação que vamos executar em GCP a partir do dataset `APKS_FINAL_JCA_DEXLIB` (190 APKs F-Droid pré-instrumentados com dexlib2 + estática JCA). Ele replica o desenho do paper ASE2024 ("A Comparison of 10 Android Test Case Generation Tools to Identify API Misuses via Runtime Verification") com a infraestrutura modular do RV-Android.

Quem precisa executar o experimento lê este arquivo do início ao fim. Ele é a fonte da verdade para o que rodar, com qual configuração, em qual hardware, e o que fazer se algo der errado.

---

## ⚠ Regra de operação — VMs no GCP

**NUNCA deletar uma VM do projeto `research-318211` sem ordem expressa do usuário.** Vale para `gcloud compute instances delete`, comandos equivalentes na console web, ou qualquer scripting que termine numa deleção. Parar (`stop`) está OK quando justificado para economizar custo; deletar não.

A regra aplica também a qualquer ação destrutiva sobre o projeto: remover discos persistentes, deletar buckets GCS, apagar imagens customizadas, alterar firewall rules em modo destrutivo. Em dúvida, perguntar antes.

**NÃO iniciar o experimento real sem aprovação expressa.** Setup das VMs, rebuild de imagens, smoke tests podem ser disparados quando claramente solicitados. O `docker compose up -d` que dispara o experimento de 3-4 dias só roda depois do "ok, pode rodar" do usuário.

---

## 1. Objetivo

Medir, para cada uma das 11 ferramentas de exploração automática de UI Android, três coisas distintas em 190 APKs reais:

1. **Cobertura de código** (métodos e activities executadas)
2. **Cobertura de operações monitoradas** (frações de métodos JCA alcançados em runtime)
3. **Violações detectadas** das especificações JCA (`SSLContextSpec`, `SecureRandomSpec`, `TrustManagerFactorySpec`, `KeyStoreSpec`, `MessageDigestSpec`)

A hipótese a testar: ferramentas que usam algum tipo de modelo (DroidBot, APE, DroidMate, Fastbot, ARES, QTesting, Humanoid) ou priorização (variantes "greedy") superam exploração puramente aleatória (Monkey) em pelo menos uma dessas três métricas, e parte das diferenças entre elas só aparece em janelas de tempo maiores.

---

## 2. As 11 ferramentas (e por que essas)

São as mesmas do paper, mantendo identidade de implementação para que a comparação seja válida. Os nomes seguem o DSL do `rv-tools` (`tool` ou `tool:variant`):

| # | Identificador | Tipo de exploração |
|---|---|---|
| 1 | `monkey` | Pseudoaleatória (linha de base) |
| 2 | `droidbot:dfs_greedy` | Modelo + busca em profundidade priorizando estados não vistos |
| 3 | `droidbot:bfs_greedy` | Modelo + busca em largura priorizando estados não vistos |
| 4 | `droidbot:dfs_naive` | Modelo + DFS sem priorização |
| 5 | `droidbot:bfs_naive` | Modelo + BFS sem priorização |
| 6 | `ape` | Modelo abstrato refinado por árvore de decisão |
| 7 | `droidmate` | Modelo priorizando estados pouco explorados |
| 8 | `humanoid` | Rede neural treinada em traces humanos |
| 9 | `ares` | Reinforcement learning sobre policy do DroidBot |
| 10 | `fastbot` | Multi-agente com componente RL |
| 11 | `qtesting` | RL híbrido com mecanismo de curiosidade |

DroidBot aparece em 4 variantes porque a literatura (e o próprio README do módulo `rv-tools/droidbot`) reconhece que a *policy* dominam o resultado — comparar só uma seria caricatura. As outras 6 ferramentas têm 1 variante por escolha de design (não há discriminação útil entre sub-policies expostas).

A string que vai para `RV_TOOLS`:

```
monkey,droidbot:dfs_greedy,droidbot:bfs_greedy,droidbot:dfs_naive,droidbot:bfs_naive,ape,droidmate,humanoid,ares,fastbot,qtesting
```

---

## 3. Os 190 APKs (e por que esses)

O dataset começa em 400 APKs vindos dos PRs mais recentes do F-Droid (planilha `PLANILHA_dexlib2.csv`) e chega a 190 depois de quatro filtros sequenciais. Cada filtro tem motivo concreto:

```
400  APKs (top F-Droid PRs)
 │
 │  ── 20 perdidos: análise estática (Soot/GATOR) falhou por timeout, OOM,
 │     ou bug do callgraph. Sem estática não há ground truth de reachability.
 ▼
380  com sa_status=complete
 │
 │  ── 154 sem JCA alcançável (sa_reaches_mop=false). São apps que simplesmente
 │     não usam criptografia — a comparação seria sem sinal.
 ▼
226  com sa_reaches_mop=true
 │
 │  ── 2 cuja instrumentação dexlib2 falhou (bytecode incompatível):
 │     io.github.chrisimx.scanbridge_2001004.apk e it.fast4x.riplay_74.apk.
 ▼
224  instrumentados com sucesso (estes são os que existem em disco em
 │   /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_dexlib2/)
 │
 │  ── 9 com min_sdk > 30. A AVD do experimento é API 30 (Android 11);
 │     Android é forward-only, então min_sdk=31+ não consegue iniciar.
 │
 │  ── 25 ARM-only (nenhum binário x86_64). O NDK Translation do AVD
 │     google_apis x86_64 traduz ARM em runtime, mas a tradução tem
 │     comportamento não-determinístico em alguns paths e queremos isolar
 │     o efeito da ferramenta de exploração, não da tradução de bytecode.
 ▼
190  APKs FINAIS  (em /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/)
```

A lista completa dos 34 excluídos com motivo está em `data/validation_filters/validation_excluded.txt`.

---

## 4. Parâmetros do experimento

| Parâmetro | Valor | Razão |
|---|---|---|
| Ferramentas | 11 (acima) | Mesma escolha do paper para comparabilidade |
| Timeouts por task | **60 s, 180 s, 300 s** | O paper usa também 120 s; o nosso desenho dispensa por compactação. As 3 janelas mostram (i) "que ferramenta gera evento rápido", (ii) regime intermediário, (iii) regime estabilizado. |
| Repetições | **3** | Variância das ferramentas estocásticas (Monkey, ARES, Fastbot, QTesting) é grande no curto prazo; 3 reps é o mínimo aceitável |
| APKs | 190 | Filtrado dos 224 instrumentados (§3) |
| Specification set | `jca` | O dataset foi instrumentado para JCA |
| Variante de instrumentação | `dexlib2` | É como os APKs já estão; não vamos re-instrumentar |
| Pre-processing | **pular tudo** | APKs já instrumentados (`--skip-monitors --skip-instrument --skip-static`) |

**Total de tasks: 11 × 3 × 3 × 190 = 18 810**.

A duração média de uma task é `timeout + ~90 s` de overhead (boot único da AVD reusado + instalação do APK + extração de cobertura + cleanup). Distribuídas igualmente entre os três timeouts, isso dá:

> tempo_médio_task = (60+180+300)/3 + 90 ≈ **270 s**

---

## 5. Hardware e tempo de execução

A infraestrutura é o projeto GCP `research-318211`, zona `us-central1-a`, 4 VMs `n2-standard-16` (16 vCPU, 64 GB RAM, 200 GB disco, Intel Cascade Lake com nested virtualization habilitada). KVM funciona dentro das VMs, o que é pré-requisito para o emulador Android rodar com aceleração — sem KVM o experimento se torna ~10× mais lento e inviável.

As VMs serão entregues cruas (apenas o OS Debian 12). Toda a configuração — Docker, pull da imagem, dataset, scripts — fica conosco.

Cada container do RV-Android usa 4 vCPU e 8 GB RAM. **4 containers por VM × 4 VMs = 16 containers paralelos**. RAM consumida por VM: 4 × 8 = 32 GB. Cabe nas 4 VMs (m1: 64 GB com folga; m2/m3/m4: 32 GB sem buffer pro OS, monitorar OOM no smoke).

Com 16 containers e tempo médio de 270 s/task:

> wall-clock ≈ 18 810 / 16 × 270 s ≈ **88 h ≈ 3,7 dias**

---

## 6. Execução em três fases

As 4 VMs do projeto são `m1-exp02`, `m2-exp02`, `m3-exp02`, `m4-exp02` (zona `us-central1-a`). O fluxo:

1. Configurar uma VM (`m1-exp02`) — §6.1
2. Smoke test nela com a imagem que vamos usar — §6.2
3. Replicar setup canônico nas outras 3 — §6.3
4. Disparar experimento completo (só depois do "ok" do usuário) — §6.4
5. Monitorar e consolidar — §6.5

Esta seção foi consolidada após o smoke validar. As §§6.1-6.2 abaixo são o procedimento **canônico** (não rascunho) — o mesmo que vamos rodar nas outras VMs.

### 6.1 Configurar uma VM (procedimento canônico)

Tudo é executado da máquina local, fazendo SSH na VM via `gcloud`. Estes comandos são idempotentes — rodá-los duas vezes não quebra nada.

**Acessar a VM**

```bash
gcloud compute ssh m1-exp02 --zone=us-central1-a --project=research-318211
```

**Dentro da VM, instalar Docker** (Debian 12, repositório oficial Docker)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Permitir que o usuário rode Docker e acesse KVM sem sudo**

```bash
sudo usermod -aG docker,kvm "$USER"
```

A mudança só vale no próximo login. Saia e entre de novo via `gcloud compute ssh` antes de seguir.

**Verificar pré-requisitos**

```bash
docker run --rm hello-world          # docker funcional
ls -la /dev/kvm                      # acessível (grupo kvm)
egrep -c '(vmx|svm)' /proc/cpuinfo   # >0 (32 esperado em n2-standard-16)
free -h && nproc && df -h /          # 16 vCPU, 62 GB RAM, ~190 GB livres
```

**Pull das imagens** (~6 GB de rvandroid + ~3-4 GB de ares + qtesting)

```bash
docker pull phtcosta/rvandroid:0.8.0
docker pull phtcosta/ares:latest        # ARES roda como Docker sibling
docker pull phtcosta/qtesting:latest    # QTesting idem
docker pull phtcosta/humanoid:1.0       # serviço auxiliar para a tool humanoid
```

Por que três imagens auxiliares: ARES e QTesting **não rodam dentro do container rvandroid** — cada execução cria um sibling container via `docker.sock` (ver `modules/rv-tools/src/rv_tools/builtin/{ares,qtesting}/tool.py`). Fastbot e APE rodam como `app_process` dentro do emulador (não precisam imagem extra). Humanoid é um servidor TCP rodando em sua própria imagem; o tool `humanoid` do `rv-tools` apenas faz requests HTTP a ele.

**Sincronizar dataset e arquivos do experimento da máquina local**

Da máquina local, com a VM rodando:

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# 1) Dataset (~3.8 GB) — cabe em ~10 min na conexão padrão
gcloud compute scp --recurse --zone=us-central1-a --project=research-318211 \
  /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB \
  m1-exp02:/home/pedro/

# 2) Arquivos do experimento (compose + filtros + scripts)
gcloud compute scp --recurse --zone=us-central1-a --project=research-318211 \
  experimento-20260508 \
  m1-exp02:/home/pedro/
```

Estado-alvo dentro da VM:

```
/home/pedro/
├── APKS_FINAL_JCA_DEXLIB/         # 190 APKs + 190 JSONs (3.8 GB, ro no compose)
└── experimento-20260508/
    ├── docker-compose.gcp.yml     # (a criar) define 4 containers para a VM
    ├── filters/                   # batches por container desta VM
    └── scripts/                   # entry points executados na VM
```

### 6.2 Smoke test (validado em `m1-exp02` 2026-05-08)

Smoke configurado: **2 APKs × 11 tools × 1 rep × 2 timeouts (60 s e 120 s) = 44 tasks** num único container, ~2 h 12 min. Exercita todos os 11 binários, e os dois timeouts validam que o pipeline lida com runs sequenciais que reusam o mesmo `RV_EXPERIMENT_NAME` (auto-resume cumulativo).

APKs escolhidos a partir do consolidado de validação (2026-05-07): `ch.famoser.mensa_60.apk` e `com.destructo.botox_43.apk` — ambos com MOP=100 % em ape e aperv:sata_mop, pequenos (~3 MB cada).

Resultado real:

| Métrica | Valor |
|---|---|
| Tasks | 42/44 COMPLETED, 2 ERROR |
| MOP médio | 72,3 % |
| Tools 100 % OK | 10/11 |
| Tool com ERROR | `monkey` 2/4 (cosmético — exit code != 0 quando o platform mata o processo no fim do timeout; cobertura é gravada antes do raise, então `summary.csv` tem os números) |

Issue conhecido descoberto e resolvido durante o smoke: a versão de `androguard` empacotada na imagem `0.8.0` original (`3.4.0a1`) não parseia o `resources.arsc` produzido por `aapt2` em apps com `targetSdk ≥ 33`, falhando com `ResParserError: res1 must be zero!`. O `droidbot` (que usa `androguard.APK.get_app_name()`) crashava em todos os 190 APKs. Solução: rebuild da imagem `phtcosta/rvandroid_tools:0.8.0` com `androguard>=4.1.3` no pip global (env do droidbot) — mantendo `3.4.0a1` no uv venv (que `rv-android-core` usa, mas em paths que não acionam o parser). 1 sed no `docker/tools/Dockerfile` corrige o import path do droidbot (`androguard.core.bytecodes.apk` → `androguard.core.apk`). A imagem `0.8.0` no Docker Hub agora carrega esse fix; nenhum hot-patch runtime é necessário.

Compose validado em `experimento-20260508/docker-compose.smoke.yml`; script orquestrador em `experimento-20260508/scripts/run_smoke.sh` (faz duas passadas sequenciais com `RV_TIMEOUTS=60` e `RV_TIMEOUTS=120`).

### 6.3 Replicar nas outras 3 VMs

`m2-exp02`, `m3-exp02`, `m4-exp02` recebem o mesmo procedimento da §6.1. Em paralelo, da máquina local:

```bash
for VM in m2-exp02 m3-exp02 m4-exp02; do
    gcloud compute ssh "$VM" --zone=us-central1-a --project=research-318211 --command='
        # Docker install (idêntico ao §6.1)
        sudo apt-get update -q
        ...
        sudo usermod -aG docker,kvm $USER
    ' &
done
wait
# pull das 4 imagens em cada VM, depois scp dataset+experimento
```

Os comandos completos estão no script `scripts/setup_remaining_vms.sh` (a criar antes de rodar; espelho do que fizemos em `m1-exp02`). Validação por VM ao fim: `docker run --rm phtcosta/rvandroid:0.8.0 echo ok` retorna OK.

### 6.4 Início do experimento completo

O experimento usa os 190 APKs particionados em 16 batches round-robin (≈12 APKs/batch). Cada VM roda 4 batches simultâneos.

Decisão arquitetural: **3 runs sequenciais por timeout**, não um único run multi-timeout. O CLI 0.8.0 (Click) só aceita `--timeout int`, e o `RV_TIMEOUTS` envvar é mapeado para `--timeout` (também int). Multi-timeout via `--config experiment.json` exige sobrescrever o entrypoint canônico, o que descartamos para alinhar com o padrão dos exemplos (`rvsec-02`, `aperv-comparacao`). O preço é 3 boots de AVD por container ao longo do experimento (~135 s extras), irrelevante na escala de 88 h.

Cada passada usa `RV_TIMEOUTS=60`, depois `=180`, depois `=300`, mesmo `RV_EXPERIMENT_NAME` por container. Auto-resume via `tasks.json` acumula combos `(apk, tool, variant, rep, timeout)` sem duplicar — re-executar `docker compose up -d` recupera o estado, mesmo entre passadas e entre falhas.

**Serviço humanoid compartilhado por VM** (padrão do `rvsec-02`): um único `rv-humanoid:50405` no compose, cada container `exp_NN` referencia via `RV_HUMANOID_URL=rv-humanoid:50405` (DNS do compose). Sem healthcheck; `depends_on` espera só o start.

**Esqueleto do compose** (espelho de `docker-compose.smoke.yml`, multiplicado para 4 containers):

```yaml
services:
  humanoid:
    image: phtcosta/humanoid:1.0
    container_name: rv-humanoid
    ports: ["50405:50405"]

  exp_00:
    image: phtcosta/rvandroid:0.8.0
    container_name: exp_00
    depends_on: [humanoid]
    devices: [/dev/kvm:/dev/kvm]
    deploy:
      resources:
        limits: { cpus: "4", memory: "8g" }
    environment:
      RV_EXPERIMENT_NAME: exp_00
      RV_TOOLS: "monkey,droidbot:dfs_greedy,droidbot:bfs_greedy,droidbot:dfs_naive,droidbot:bfs_naive,ape,droidmate,humanoid,ares,fastbot,qtesting"
      RV_TIMEOUTS: "${EXP_TIMEOUT:-60}"
      RV_REPETITIONS: "3"
      RV_NO_WINDOW: "true"
      RV_SPEC_SET: "jca"
      RV_INSTRUMENTATION_VARIANT: "dexlib2"
      RV_APKS_DIR: "/opt/rvsec/rv-android/apks"
      RV_APKS_FILTER: "/opt/rvsec/rv-android/filters/batch_00.txt"
      RV_SKIP_MONITORS: "true"
      RV_SKIP_INSTRUMENT: "true"
      RV_SKIP_STATIC_ANALYSIS: "true"
      RV_HUMANOID_URL: "rv-humanoid:50405"
      RV_DELAY: "0"
    volumes:
      - /home/pedro/APKS_FINAL_JCA_DEXLIB:/opt/rvsec/rv-android/apks:ro
      - ./filters:/opt/rvsec/rv-android/filters:ro
      - ./results/exp_00:/opt/rvsec/rv-android/results
      - /var/run/docker.sock:/var/run/docker.sock

  exp_01:  # idem com RV_DELAY: "30", RV_APKS_FILTER batch_01, container_name: exp_01
  exp_02:  # ...                          60                  batch_02            exp_02
  exp_03:  # ...                          90                  batch_03            exp_03
```

Cada VM define seus 4 batches e roda os mesmos 4 containers. Os 16 batches dos 190 APKs são distribuídos entre as 4 VMs (4-4-4-4).

**Mapeamento batch → VM** (o `docker-compose.gcp.yml` lê `BATCH_0..BATCH_3` do `.env.<vm>`):

| VM | Arquivo `.env` | Batches que recebe |
|---|---|---|
| m1-exp02 | `.env.m1` | `batch_00..03` |
| m2-exp02 | `.env.m2` | `batch_04..07` |
| m3-exp02 | `.env.m3` | `batch_08..11` |
| m4-exp04 | `.env.m4` | `batch_12..15` |

**Disparo (em cada VM, depois do "ok" do usuário)** via `scripts/run_experiment.sh` que orquestra 3 passadas sequenciais:

```bash
cd /home/pedro/experimento-20260508
nohup ./scripts/run_experiment.sh m<N> > experiment.log 2>&1 < /dev/null &
# m<N> = m1, m2, m3 ou m4 conforme a VM
```

O script roda `EXP_TIMEOUT=60`, depois `=180`, depois `=300`, sempre com `--env-file .env.m<N>`. Mesmo `RV_EXPERIMENT_NAME` por container ao longo das 3 passadas — `tasks.json` acumula combos `(apk, tool, variant, rep, timeout)` sem duplicar. Se a VM cair ou um container morrer, basta re-rodar o script: o auto-resume ignora combinações já completas.

Sem watchdog: tasks travadas correm até o timeout configurado pelo `rv-experiment` e a próxima task começa.

### 6.5 Monitoramento e consolidação

Sem solução robusta agora. Durante a execução, scripts pequenos vão ser copiados para cada VM e executados via `gcloud compute ssh` quando a gente quiser olhar o estado. A coleta final é `rsync` puxando `results/exp_NN/` de cada VM para `experimento-20260508/results/vm<N>/`, depois um `consolidate_experiment.py` (a criar) que une summary.csv, errors.csv e tasks.json num CSV único com `(apk, tool, variant, rep, timeout, cov_method, cov_act, cov_rv_method, errors_total, status, duration_s)`. A discussão fina sobre painel de monitoramento fica para depois do experimento começar a rodar.

### 6.6 Incidentes operacionais

Falhas durante a execução (OOM, hangs do adb, kills do kernel) são registradas em `INCIDENTS.md` desta mesma pasta. Cada entrada contém data/hora, container afetado, sintoma, diagnóstico, ação tomada e impacto. Padrões observados:

- **OOM kills (exit 137)** nas VMs com 32 GB (m2/m3/m4): 4 × 8 GB de limite Docker = 32 GB total, sem buffer para o OS. Quando o ARES ou QTesting spawna seu sibling container, picos transientes de RAM são fatais.
- **adb install hang**: ocasional, sem timeout no `rv-platform` — container fica vivo consumindo recursos mas sem progresso. Recovery manual via `docker restart`.

Em todos os casos o auto-resume via `tasks.json` evita perda de dados — só perdemos wall-clock até a detecção e o restart.

---

## 7. Estrutura desta pasta

```
experimento-20260508/
├── README.md                        ← este arquivo
├── INCIDENTS.md                     ← histórico cronológico de falhas durante a execução
├── docker-compose.smoke.yml         ← smoke validado em m1
├── docker-compose.minismoke.yml     ← mini-smoke (1 APK + 1 tool) para sanity em VM nova
├── docker-compose.gcp.yml           ← experimento real (4 containers + humanoid)
├── .env.m1  .env.m2  .env.m3  .env.m4   ← mapeamento BATCH_0..3 por VM
├── filters/
│   ├── experiment_apks.txt          ← lista canônica dos 190 APKs
│   ├── batch_00.txt … batch_15.txt  ← 16 batches round-robin (auditados, 0 dup, cov 100 %)
│   ├── smoke_batch.txt              ← 2 APKs do smoke
│   └── minismoke_batch.txt          ← 1 APK do mini-smoke
├── scripts/
│   ├── preflight.sh                 ← (legado do smoke; não usado pela imagem 0.8.0 atual)
│   ├── run_smoke.sh                 ← orquestra 60 s + 120 s para o smoke
│   └── run_experiment.sh            ← orquestra 60 s + 180 s + 300 s para o experimento real
└── results/
    ├── smoke/                       ← saída do smoke 2026-05-08 em m1
    ├── exp_00/  exp_01/  exp_02/  exp_03/   ← criados em runtime; um por container/VM
    ├── vm1/  vm2/  vm3/  vm4/       ← rsync futuro pra consolidação local (a criar)
    └── consolidated/                ← saída agregada do consolidate_experiment.py (a criar)
```

---

## 8. Validação prévia (2026-05-07)

Para confirmar que o pipeline funciona ponta a ponta antes do experimento principal, rodamos um smoke local com 10 containers, 2 ferramentas (`ape` e `aperv:sata_mop`), 3 reps, timeout 300 s sobre os 190 APKs. O resultado:

- 1 134 de 1 140 tasks completaram (taxa de falha 0,53%)
- A imagem `phtcosta/rvandroid:0.8.0` boota a AVD em 45 s e instala APKs sem incidente
- O pipeline emite eventos RVSEC corretamente — 68 067 eventos de violação, 218 mensagens únicas, 76 APKs com pelo menos uma violação
- Top specs detectadas: `SSLContextSpec` (~11 700), `SecureRandomSpec` (~11 300), `TrustManagerFactorySpec` (~7 800), `KeyStoreSpec` (~3 160) — perfil idêntico nas duas ferramentas
- Auto-resume via `tasks.json` funciona: containers exited limpos

A comparação `ape × aperv:sata_mop` em 300 s deu Wilcoxon p > 0,05 em todas as métricas — as duas tools são estatisticamente indistinguíveis nessa janela. Isso reforça a importância de incluir 60 s e 180 s no experimento principal: parte da diferença entre ferramentas só aparece em regimes de tempo onde uma ainda não chegou no caminho que a outra já cobriu.

Os 169 APKs que dispararam JCA em 300 s (de 190) classificaríamos como "fáceis"; os outros 21 dependem de exploração mais agressiva ou caminhos de UI específicos. No experimento principal mantemos os 190 — algumas das ferramentas que não rodaram no smoke (Fastbot com RL, Humanoid com modelo neural) tipicamente alcançam caminhos de UI diferentes, e excluí-los já agora viesa a comparação.

Detalhes em `data/results/validation_consolidated.csv` e `docs/20260507_validacao_dataset_pre_experimento.md`.

---

## 9. Decisões pendentes

Antes de gerar os artefatos e disparar:

- **Quais 2 APKs para o smoke** (§6.2)? Sugestão: `byrne.utilities.hashpass_2.apk` (pequeno, sem rede, dispara JCA básico) e `org.cis_india.wsreader_145.apk` (médio, validado no smoke 2026-05-07 com 7 violações).
- **ARES e QTesting na imagem 0.8.0**: o `rvsec-02/PROBLEMS.md` documenta freezes pós-timeout dessas duas tools no `phtcosta/rvandroid:0.0.1`. A versão 0.8.0 pode ter regredido ou mantido esse comportamento. Decisão atual: deixar rodar até o timeout, confiando que o `rv-experiment` mata o container/processo no fim. Se o smoke mostrar zombies persistentes, reavaliamos.

Decisões já fechadas (registradas para histórico): sizing 4 vCPU + 16 GB, 4 containers/VM, humanoid compartilhado por VM, particionamento round-robin, sem watchdog, monitoramento ad-hoc via ssh, persistência via rsync ao fim do experimento.

---

## 10. Referências

| Arquivo | Conteúdo |
|---|---|
| `docs/20260507_validacao_dataset_pre_experimento.md` | Plano e resultados do smoke que fechou os 190 APKs |
| `docs/20260503_modernizacao.md` | Justificativa da AVD API 30 x86_64 |
| `docs/rv_android_architecture.md` | Visão arquitetural do RV-Android |
| `openspec/specs/experiment/spec.md` | Especificação formal do `rv-experiment` |
| `modules/rv-experiment/CLAUDE.md` | Mapa env vars → flags do CLI |
| `modules/rv-tools/src/rv_tools/builtin/<tool>/` | Implementação e variantes de cada uma das 11 ferramentas |
| `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-02/` | Workspace do experimento anterior; recipe de batches/monitor/watchdog vale herdar |
| `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase2024/main.pdf` | Paper de referência |
| `data/results/validation_consolidated.csv` | Saída por-APK do smoke 2026-05-07 |
| `data/validation_filters/validation_apks.txt` | Lista dos 190 APKs |
| `data/validation_filters/validation_excluded.txt` | Lista dos 34 excluídos com motivo |
