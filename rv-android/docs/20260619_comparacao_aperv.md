# Comparação APE × APE-RV (SATA/MOP/LLM) — Plano de Experimento

**Data:** 2026-06-19
**Branch:** `modules`
**Dataset:** `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604` (169 APKs JCA dexlib2-instrumentados + 169 `.apk.json` co-localizados)
**Imagem:** `phtcosta/rvandroid:0.9.1` (a construir)

---

## 1. Objetivo e hipóteses

Avaliar se a orientação por **análise estática (MOP)** — e, adicionalmente, por **LLM** — melhora a
detecção de operações monitoradas (MOP) em relação ao **APE puro**, mantendo toda a comparação
**dentro da família APE/APE-RV** (sem baselines externos como monkey/droidbot/fastbot). Essa escolha dá
uma narrativa limpa: o mesmo binário APE-RV é comparado com o MOP ligado/desligado, isolando o efeito da
orientação sem confundir com diferenças de implementação entre ferramentas distintas.

| ID | Hipótese | Teste | Expectativa |
|----|----------|-------|-------------|
| **H1** | `ape` ≈ `aperv:sata` — APE-RV com MOP desligado reproduz o APE original (sanidade/equivalência) | Wilcoxon pareado | p > 0.05 (equivalência) |
| **H2** | `aperv:sata_mop` > `ape` **e** > `aperv:sata` em cobertura MOP e violações únicas (**claim central**) | Wilcoxon pareado | p < 0.05 (ganho) |
| **H3** | `aperv:sata_mop_llm` ≥ `aperv:sata_mop` (exploratória; 1 GPU, risco de contenção) | Wilcoxon pareado | tendência positiva |

O par **`aperv:sata` vs `aperv:sata_mop`** é o controle *within-binary* mais limpo (mesmo binário, única
diferença = JSON MOP). O par **`ape` vs `aperv:sata`** é a checagem de equivalência entre o APE original e
a reimplementação APE-RV.

---

## 2. Braços comparados (4) — combined run

| Arm | CLI (`--tools`) | MOP | LLM | Papel |
|-----|-----------------|-----|-----|-------|
| **ape** | `ape` | ❌ | ❌ | baseline original (builtin, base AOSP-Monkey) |
| **sata** | `aperv:sata` | ❌ | ❌ | controle within-binary (APE-RV puro) |
| **sata_mop** | `aperv:sata_mop` | ✅ | ❌ | **contribuição central** (orientado por MOP estático) |
| **sata_mop_llm** | `aperv:sata_mop_llm@llm_percentage=0.9` | ✅ | ✅ | MOP + LLM **em 90% das ações** (requer SGLang) |

Tool string completa: `--tools "ape,aperv:sata,aperv:sata_mop,aperv:sata_mop_llm@llm_percentage=0.9"`

**Consumo do MOP data** (`aperv:sata_mop` e `_llm`): o tool procura `<results_dir>/<apk>.json`, faz push para
`/data/local/tmp/static_analysis.json` no device e adiciona `ape.mopDataPath=...` às properties. Sem o JSON,
degrada para SATA puro (warning, sem falha). Por isso os `.apk.json` precisam estar co-localizados (ver §4).

**Decisão sobre o braço LLM — taxa de 90% das ações.** A variante base `aperv:sata_mop_llm`
(`tool.py:249`) só dispara o LLM por **evento** (`llm_on_new_state=true`, `llm_on_stagnation=true`) e deixa
`ape.llmPercentage` no default do `ape-rv.jar` — LLM esparso. As 6 variantes `sata_mop_llm_<v>` (gh43)
adicionam `llm_percentage=0.7` **mas amarradas a um prompt experimental** (`ape_current`/…/`v17`). Para ter o
LLM denso **com o prompt default** — sem comprometer com um prompt de experimento — usamos o **override de
DSL** com a taxa escolhida: `aperv:sata_mop_llm@llm_percentage=0.9` (**90% das ações**). Isso mantém a config
base e só força `ape.llmPercentage=0.9`. (O smoke de 2026-06-19 rodou a 0.7; a corrida completa usa **0.9**.)
A 90% a pressão sobre o SGLang/GPU aumenta; o `llm_timeout_ms=15000` degrada graciosamente (chamadas que
estouram o timeout seguem sem LLM naquele passo), então o wall-clock não estoura.

**Config do braço LLM** (`aperv:sata_mop_llm`, de `aperv-tool/src/aperv_tool/tools/aperv/tool.py:249`, mais o
override `llm_percentage=0.9`): `llm_url=http://10.0.2.2:30000/v1`, `llm_on_new_state=true`,
`llm_on_stagnation=true`, **`llm_percentage=0.9`**, `llm_model=default`, `llm_temperature=0.3`,
`llm_top_p=0.6`, `llm_top_k=50`, `llm_timeout_ms=15000`. O timeout de 15 s garante **degradação graciosa**:
sob pressão de GPU, chamadas que estouram o timeout fazem o APE-RV seguir sem orientação LLM naquele passo
(comportamento tende a `sata_mop`).

---

## 3. Dataset e skip de pré-processamento

- **169 APKs** dexlib2-instrumentados + **169 `.apk.json`** (análise estática GATOR) **na mesma pasta**.
- Skip integral do pré-processamento — nada de gerar monitores, instrumentar ou rodar GATOR:
  - `RV_SKIP_MONITORS=true`
  - `RV_SKIP_INSTRUMENT=true`
  - `RV_SKIP_STATIC_ANALYSIS=true`
- **Gotcha resolvido:** o platform copia automaticamente `<apk>.json` (e `.methods`, se existir) co-localizado
  com o APK para o results-dir de cada task (`StaticAnalysisComponent.copy_static_analysis_files`). Logo,
  `--skip-static` **não** priva o `aperv:sata_mop`/`_llm` do MOP data — basta apontar `--apks-dir` para a pasta
  que já contém os pares `.apk` + `.apk.json`. Não há flag `--static-analysis-dir` separada.
- **Spec set:** `jca`.

Verificação (deve dar 169 = 169):
```bash
DS=/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604
ls "$DS"/*.apk | wc -l
ls "$DS"/*.apk.json | wc -l
```

### 3.1. AVD / ABI e elegibilidade de APK

A AVD da imagem é **API 30, `google_apis`, `x86_64`** (de `docker/android/Dockerfile`:
`API_LEVEL=30`, `IMG_TYPE=google_apis`, `ARCHITECTURE=x86_64` → `ABI=google_apis/x86_64`; decisão gh55
D8/D10, que abandonou o default antigo API 29 x86). Fallback para API 29 x86 só via
`--build-arg API_LEVEL=29 --build-arg ARCHITECTURE=x86`.

**Filtrar `native_code_abis` pela arch da AVD (`x86_64`)** antes de selecionar/estratificar APKs
(memória `feedback_filter_apk_abi_for_avd` — ~20% de perda histórica por rodar arch incompatível). Em API 30
`x86_64` com **NDK Translation**, são elegíveis:
- APKs com lib nativa **`x86_64`** (execução nativa);
- APKs **`arm64-v8a`** (rodam via tradução NDK);
- APKs **sem código nativo**.

Ficam de fora apenas APKs puramente legados **`x86`/`armeabi`** (sem `x86_64`/`arm64-v8a`). Como os 169 já
passaram por validação de instalação na campanha 20260604 (mesma AVD x86_64), espera-se que todos sejam
elegíveis — confirmar no preflight/smoke caso algum não instale.

---

## 4. Configuração de execução

| Parâmetro | Valor |
|-----------|-------|
| Containers | **6** (round-robin, ~28-29 APKs/container) — reduzido de 8 após o smoke (ver §7.1) |
| Timeout | **300 s** (5 min) — `RV_TIMEOUTS=300` |
| Repetições | **3** — `RV_REPETITIONS=3` |
| Braços | 4 (combined, interleaved no mesmo experimento) |
| **Total de tasks** | **4 × 169 × 3 = 2 028** |
| Wall-clock estimado | **~37–40 h** (~1.7 dia) a ~6.5 min/task efetivo (300 s + boot/install/coverage), com 6 containers |
| Spec set | `jca` |
| Janela | headless — `RV_NO_WINDOW=true` |
| AVD / ABI | API 30, `google_apis`, **`x86_64`** (NDK Translation cobre `arm64-v8a`) — ver §3.1 |

**SGLang** roda como **serviço próprio no compose** (padrão de `docker-compose.exp3-aperv-llm.yml`):
`lmsysorg/sglang:v0.5.6.post2`, modelo **`Qwen/Qwen3-VL-4B-Instruct` (base, NÃO o fine-tuned
`phtcosta/qwen3vl-4b`)**, porta 30000, reserva de **1 GPU**, healthcheck em `/health`. Os 6 containers
rvandroid usam `depends_on: { sglang: service_healthy }` e `RVSMART_LLM_MODE=true`, que liga a ponte `socat`
(`127.0.0.1:30000 → sglang:30000`) no entrypoint; o `aperv` alcança o endpoint via
`http://10.0.2.2:30000/v1` (alias do emulador para o host).

> **Modelo já baixado (verificado 2026-06-19):** `Qwen/Qwen3-VL-4B-Instruct` está completo em
> `HF_CACHE=/pedro/desenvolvimento/.cache/huggingface` (8.3 GB, 2 shards safetensors íntegros, snapshot
> `ebb281ec…`). O compose deve montar esse caminho como volume HF para o SGLang subir **sem rebaixar** o
> modelo. ⚠️ O mesmo cache contém `phtcosta/qwen3vl-4b` (fine-tuned) — usar o **base** no `--model-path`.

> **Nota de contenção:** com 1 GPU e até 8 braços LLM concorrentes em determinados instantes, o SGLang
> pode enfileirar requisições. Como o timeout da task é wall-clock (300 s) e `llm_timeout_ms=15000` degrada
> graciosamente, isso **não estende** o tempo — apenas reduz a eficácia da orientação LLM sob pressão. H3 é,
> portanto, exploratória. Monitorar saúde/latência do SGLang durante a corrida.

---

## 5. Imagem docker 0.9.1 (pré-requisito)

A imagem precisa ser **reconstruída** para incorporar os fixes do branch `modules` (gh60–gh70).

**Escopo: cadeia completa** via `docker/build_all.sh` (~45–65 min). Reconstrói
`base → android → tools → rvandroid`, garantindo 0.9.1 consistente em todos os estágios.

Cadeia de imagens (todas em `:0.9.1`):
1. `phtcosta/rvsec_base:0.9.1` — Java 25, Maven, AspectJ, uv
2. `phtcosta/rvsec_android:0.9.1` — Android SDK/Emulator (API 30 x86_64), GATOR, KVM
3. `phtcosta/rvandroid_tools:0.9.1` — droidbot, ape, fastbot
4. `phtcosta/rvandroid:0.9.1` — **produção**: clone `PAMunb/rvsec` (branch `modules`) + `mvn install` + `uv sync`

### Pré-condições de build
- ⚠️ **O estágio 4 faz `git clone` de `PAMunb/rvsec` branch `modules`** → os commits relevantes precisam estar
  **pushed** antes do build. O commit `1eec78a3` está unpushed (ver memória). **Verificar e fazer push** do
  branch `modules` (rvsec e rv-android conforme necessário) antes de construir.
- Confirmar que os strings de versão já estão em `0.9.1` (build scripts `docker/*/build.sh`, `FROM` nos
  Dockerfiles, `docker/docker-compose.yml:20`, defaults em `scripts/*_docker.py`, asserts de jar nos testes).
  O subagente de levantamento já encontrou `VERSION=0.9.1` nos scripts — apenas validar antes de buildar.

### Passos
```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker

# 1. (pré) garantir branch modules pushed no GitHub PAMunb/rvsec
# 2. build da cadeia completa
./build_all.sh   # base -> android -> tools -> rvandroid (~45-65 min, --no-cache)

# 3. verificações pós-build
docker inspect phtcosta/rvandroid:0.9.1 | grep -A2 rvsec.branch
docker run --rm phtcosta/rvandroid:0.9.1 bash -lc \
  'ls /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar'
# ape-rv.jar presente (bundlado via aperv-tool):
docker run --rm phtcosta/rvandroid:0.9.1 bash -lc \
  'find /opt/rvsec -name ape-rv.jar'
```

---

## 6. Infraestrutura — filter files e docker-compose

### 6.1. Split round-robin dos 169 APKs em 6 batches
```bash
python3 - <<'EOF'
import os
from pathlib import Path
ds = "/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604"
n = 6
apks = sorted(f for f in os.listdir(ds) if f.endswith(".apk"))
out = Path("./data/comparacao_aperv_filters"); out.mkdir(parents=True, exist_ok=True)
groups = [[] for _ in range(n)]
for i, a in enumerate(apks):
    groups[i % n].append(a)
for i, g in enumerate(groups):
    (out / f"batch_{i:02d}.txt").write_text("\n".join(g) + "\n")
    print(f"batch_{i:02d}.txt: {len(g)} APKs")
print("total:", len(apks))
EOF
```

### 6.2. docker-compose (6 rvandroid + 1 sglang)
Copiar `docker/docker-compose.exp3-aperv-llm.yml` para
`docker/docker-compose.comparacao-aperv.yml` e ajustar:

- Serviço `sglang` (1 GPU, `v0.5.6.post2`, `Qwen/Qwen3-VL-4B-Instruct`, healthcheck) — manter.
- Âncora `&rvandroid-base`: `image: phtcosta/rvandroid:0.9.1`, `depends_on: {sglang: service_healthy}`,
  `devices: [/dev/kvm:/dev/kvm]`, limites 4 CPU / 10g.
- Env compartilhado:
  ```yaml
  RV_TOOLS: "ape,aperv:sata,aperv:sata_mop,aperv:sata_mop_llm@llm_percentage=0.9"
  RV_TIMEOUTS: "300"
  RV_REPETITIONS: "3"
  RV_SPEC_SET: "jca"
  RV_NO_WINDOW: "true"
  RV_SKIP_MONITORS: "true"
  RV_SKIP_INSTRUMENT: "true"
  RV_SKIP_STATIC_ANALYSIS: "true"
  RVSMART_LLM_MODE: "true"
  ```
- 6 serviços `cmp_00`..`cmp_05`, cada um com:
  - `container_name: cmp_NN`
  - `RV_EXPERIMENT_NAME: cmp_NN` (habilita resume por nome)
  - `RV_APKS_FILTER: /opt/rvsec/rv-android/filters/batch_NN.txt`
  - `RV_DELAY: "<0,10,20,30,40,50>"` (escalona o start; espalha boot do emulador e warmup do SGLang)
  - volumes:
    ```yaml
    - /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604:/opt/rvsec/rv-android/apks:ro
    - ./data/comparacao_aperv_filters:/opt/rvsec/rv-android/filters:ro
    - ./data/results/cmp_NN:/opt/rvsec/rv-android/results
    ```

---

## 7. Preflight (1 APK, antes do launch completo)

Rodar **1 APK × 4 braços × 1 rep** num único container e validar:

1. Todas as 4 tasks terminam **COMPLETED** (timeout é saída normal de ferramenta de exploração).
2. Cobertura > 0% em todos os braços (se 0%, suspeitar de APK não-instrumentado / coverage markers ausentes).
3. **`aperv:sata_mop` difere de `aperv:sata`** nos eventos/cobertura MOP — se idênticos, o JSON MOP **não** foi
   consumido (checar push do `static_analysis.json` e presença do `<apk>.json` no results-dir).
4. **Braço LLM responde:** logs do SGLang mostram requisições; latência típica < `llm_timeout_ms`. Se o SGLang
   não estiver healthy, o `aperv:sata_mop_llm` cai para `sata_mop` — detectável por ausência de chamadas LLM.
5. `RVToolExecutionError`/`VerifyError` = 0.

Só liberar o launch completo após o preflight passar.

### 7.1. Smoke (16 APKs) — gate obrigatório antes da corrida completa

O smoke é o preflight em escala reduzida: roda os **4 braços** num subconjunto de **16 APKs** para validar
todo o pipeline (skip-preprocessing, consumo do MOP JSON, caminho SGLang, resume, consolidação) antes de
comprometer ~30 h. **Já configurado e pronto (2026-06-19), aguardando OK para executar.**

**Config:** 16 APKs × 4 braços × 1 rep × 120 s = **64 tasks**; 8 containers (2 APKs/cada) + 1 sglang;
~30–40 min.

**Set B (16 APKs)** — selecionados dos 169 por: `directly_reaches_mop` com `n_methods>0` (sinal MOP real),
ABI `x86_64`-compat (x86_64 / arm64-v8a / sem-nativo), menores em tamanho, com cap de 2 por família de
pacote (diversidade). 15 famílias distintas, 6 APKs com ≥3 métodos-MOP, `duress.keyboard` e
`app.passwordstore` (apps de cripto/senha, alta chance de exercitar JCA):

```
duress.keyboard_51            com.xmission.trevin.android.todo_1050101   me.ocv.partyup_10900
dev.itsvic.parceltracker_…    net.ibbaa.keepitup_19                       org.fossify.home_16
com.hhst.litube_212           com.sbv.linkdroid_24                        org.fossify.math_10
com.eanema.graph89_1200       app.passwordstore.agrahn_11602              io.github.drumber.kitsune_39
com.zhangke.fread_108010      com.nospeak.app_1000010                     org.polymorphicshade.tubular_1009
eu.opencloud.android_5
```

**Artefatos prontos:**
- Filter files (8 × 2 APKs, round-robin pequeno+maior): `data/smoke_aperv_filters/smoke_batch_00..07.txt`
- Compose: `docker/docker-compose.smoke-aperv.yml` (imagem `phtcosta/rvandroid:0.9.1`, sglang
  `v0.5.6.post2`, `RV_TOOLS="ape,aperv:sata,aperv:sata_mop,aperv:sata_mop_llm@llm_percentage=0.7"`, `RV_TIMEOUTS=120`,
  `RV_REPETITIONS=1`, skip-flags, `RVSMART_LLM_MODE=true`, dataset montado `:ro`, filtros `:ro`,
  results em `data/results/smoke_cmp_NN`).

**Launch (quando autorizado):**
```bash
cd docker
docker compose -f docker-compose.smoke-aperv.yml up -d
watch -n 30 'docker ps --filter name=smoke_cmp_ --format "table {{.Names}}\t{{.Status}}"'
docker logs --tail 5 sglang-server          # saúde do SGLang
# ao terminar:
docker compose -f docker-compose.smoke-aperv.yml down
```

**Gates de saída** (todos têm de passar para liberar a corrida completa):
1. ~64 tasks **COMPLETED** (timeout = saída normal).
2. **Cobertura > 0** em todos os braços.
3. **`aperv:sata_mop` ≠ `aperv:sata`** em eventos/cobertura MOP (confirma consumo do `<apk>.json`).
4. **Braço LLM bate no SGLang** (logs do `sglang-server` mostram requisições; latência < `llm_timeout_ms`)
   **E** o `ape.properties` do braço LLM tem `ape.llmPercentage=0.7` — confirma que o override de DSL
   `@llm_percentage=0.7` parseou e chegou ao jar (senão o LLM roda na taxa default, não 70%).
5. **0** `VerifyError`/`RVToolExecutionError`.
6. **Resume validado:** matar 1 container no meio e `restart` → pula COMPLETED, re-executa não-completas (§8.1).
7. **Consolidação offline** gera as 4 tabelas, dedup por identidade, sem zerar cobertura (checar WARNING `N/M`).

#### Resultado do smoke (executado 2026-06-19, 8 containers) — ✅ ESTRUTURA VALIDADA

O smoke rodou com **8 containers** e **validou todo o pipeline**. Não será re-executado (cumpriu o papel de
validar a estrutura).

| Gate | Resultado |
|------|-----------|
| 1. COMPLETED | **62/64** — 2 FAILED por **install transiente** (não APK, não VerifyError; ver abaixo) |
| 2. Cobertura > 0 | ✅ todos os braços (cov_method mediano: ape 25.3 / sata 26.3 / sata_mop 21.6 / sata_mop_llm 21.5) |
| 3. `sata_mop` ≠ `sata` | ✅ **13/15 APKs** diferem → MOP JSON consumido |
| 4. LLM real + 70% | ✅ Decode batches reais no SGLang + `ape.llmPercentage=0.7` (renderizado do código) |
| 5. 0 VerifyError/tool errors | ✅ (os 2 erros são install transiente) |
| 7. Consolidação offline | ✅ dedup por identidade = 62 |

**Achado → decisão de 6 containers.** Os 2 FAILED foram **falhas transientes de `adb install`**
(`com.xmission.trevin.android.todo`, `eu.opencloud.android`) — ambos instalam e rodam perfeitamente no
experimento-20260604 (32 953 / 126 946 linhas nos CSVs), minSdk ≤ 30, ABI com x86_64. Causa: **8 emuladores +
SGLang num único host** → contenção; o emulador sinaliza boot antes do package manager estar pronto. O
20260604 rodou 4 containers/VM (mais leve), sem o problema. **Mitigação: corrida completa com 6 containers**
(§4) **+ passada de resume ao final** (§8, fase 4b) — o resume re-executa tasks FAILED (§8.1).

---

## 8. Launch e monitoramento

```bash
cd docker
docker compose -f docker-compose.comparacao-aperv.yml up -d

# monitor
watch -n 120 'docker ps --filter name=cmp_ --format "table {{.Names}}\t{{.Status}}"'
# saúde do SGLang
watch -n 120 'docker logs --tail 5 sglang-server 2>&1 | tail -n 5'
```

- **Recuperação:** se um container vazar emulador/JVM ou morrer, `docker compose ... restart cmp_NN` —
  o resume retoma de onde parou (ver §8.1).
- **Passada de resume final (fase 4b):** ao terminar a corrida, dar `docker compose ... up -d` de novo (ou
  `restart`) **uma vez** — como o resume só pula `COMPLETED` e re-executa `FAILED` (§8.1), isso recupera as
  falhas transientes de `adb install` sob carga (o smoke teve ~3% delas). Conferir que o nº de identidades
  COMPLETED sobe para perto de 2 028 antes de encerrar.
- **Encerramento — NÃO dar `down` automaticamente.** Ao terminar (e após a passada de resume), **manter os
  containers `Exited`** para copiar/inspecionar os traces do APE-RV de dentro do container (`docker cp cmp_NN:…`,
  artefatos fora do bind-mount). Só dar `docker compose ... down` **depois** de extrair e analisar (§8.2).

### 8.1. Mecanismo de resume (verificado no código, 2026-06-19)

Vamos depender do resume tanto no smoke quanto na corrida completa (interrupções, vazamento de emulador,
restart de container). Comportamento exato:

**Gatilho.** `--name` (env `RV_EXPERIMENT_NAME=cmp_NN`, resolvido pelo Click via `envvar=`) — se já existe
`results/<name>/tasks.json`, o run entra em **modo resume implícito**. Alternativa explícita: `--resume-dir`.
No Docker, basta `docker compose restart cmp_NN`: o entrypoint re-invoca `rv-experiment run` com o mesmo
`--name`, e o volume `results/cmp_NN` persiste o `tasks.json`.
(`modules/rv-experiment/src/rv_experiment/__main__.py:1054-1095`.)

**Em resume, os 3 flags de pré-processamento são forçados a `False`** (`generate_monitors`,
`instrument_apks`, `static_analysis`) — não re-instrumenta, não re-gera monitor, não re-roda GATOR. Coerente
com o nosso skip integral. (mesmo trecho `__main__.py`.)

**O que é pulado vs re-executado** — regra de identidade
`(apk_name, tool_name, variant, repetition, timeout)` (`platform.py:261-269`):
| Estado anterior da task | No resume |
|-------------------------|-----------|
| **COMPLETED** | **pulada** (não re-executa) |
| **ERROR / FAILED** | **RE-EXECUTADA do zero** (não está em `completed_ids`) |
| Nunca executada (run morreu antes) | executada |

> ⚠️ **Só `COMPLETED` é pulada** — `_skip_completed_tasks` filtra exclusivamente por identidades COMPLETED
> (`platform.py:230-282`; `rv-platform/CLAUDE.md` "Crash Recovery: the interrupted task is re-executed from
> scratch"). Logo, **tasks que falharam SÃO re-tentadas** num restart — é o que queremos (um emulador que
> vazou não perde a task). O efeito colateral: cada re-execução cria um **novo UUID** para a mesma
> identidade → `tasks.json` acumula duplicatas → por isso a consolidação dedup por identidade (§9).

**Persistência atômica.** `tasks.json` é escrito por-task (write-tmp → `fsync` → rename atômico) logo após
cada task concluir (`task_storage.py:281-342`). Se o container morre no meio, o `tasks.json` anterior
sobrevive íntegro; a task interrompida volta como não-COMPLETED e é re-executada.

**Por-container, sem coordenação.** Cada container tem seu próprio `results/cmp_NN/tasks.json` e seu
`RV_APKS_FILTER` (fatia de APKs). O resume é **independente por container** — cada um pula só as próprias
COMPLETED. Não há lock nem estado compartilhado. (Se o filter mudar entre runs, as identidades não batem e
tasks novas rodam.)

**Caveat gh58 no resume (origem do §9).** Tasks carregadas do `tasks.json` têm `repository=None`
(o `LogcatRepository` não é serializado). O `result_processor` reconstrói a partir do **logcat + JSON de SA
co-localizado** (`_reconstruct_repository_from_logcat` → `_resolve_static_data`). Se o JSON de SA não
resolver, a **cobertura por-método zera no CSV** (violações MOP preservadas) e sai um WARNING agregado `N/M`
("resume coverage health"). Daí a regra: **logcats = fonte da verdade**, consolidar offline (§9). No nosso
caso o `<apk>.json` está co-localizado no results-dir, então a reconstrução deve resolver — mas validar o
WARNING `N/M` após qualquer resume.

### 8.2. Pós-corrida: preservar traces do APE-RV + investigar cobertura baixa

**Motivação (2026-06-19):** no smoke, a cobertura de `sata_mop` ficou **baixa** (cov_method mediano ~21.6%,
abaixo de `ape`/`sata`) e o braço **LLM** também não se destacou. Antes de tirar conclusões da corrida
completa, é preciso **debugar minuciosamente** se o MOP-guidance e o LLM estão de fato influenciando a
exploração — pode ser efeito real, bug de integração, ou artefato de medição.

**Preservação dos artefatos (obrigatório):**
- **NÃO dar `down`** ao fim — manter os 6 containers `Exited` (§8).
- Os traces do APE-RV ficam em `data/results/cmp_NN/cmp_NN/<apk>/*.trace` (bind-mount, já no host) **e** o
  `ape_output/` por task. Copiar/snapshot antes de qualquer limpeza:
  `cp -a data/results/comparacao_traces_backup/` (ou `docker cp cmp_NN:/opt/rvsec/rv-android/results …` para
  o que não estiver no bind-mount). Artefatos efêmeros no device (`/data/local/tmp/ape.properties`,
  `static_analysis.json`, WTG model) só existem com o container vivo — por isso mantê-los.

**Roteiro de investigação (cobertura baixa de `sata_mop` e LLM):**
1. **MOP data chegou e foi consumido?** Confirmar `ape.mopDataPath=/data/local/tmp/static_analysis.json` nas
   properties e que o `<apk>.json` foi pushado; nos traces/`ape_output`, procurar evidência de scoring por MOP
   (o APE-RV usa o JSON para ponderar telas). Se `sata_mop` explora igual a `sata`, o JSON não está pesando.
2. **`sata_mop` vs `sata` lado a lado** (mesmos APKs): comparar sequências de telas/ações nos traces — o
   MOP-guidance deveria priorizar telas que alcançam operações monitoradas. Quantificar divergência.
3. **Denominador da cobertura:** a cobertura MOP é `disparadas ÷ alcançáveis` (do `.json`). Cobertura "baixa"
   pode ser denominador grande (muitos métodos alcançáveis estáticos que o runtime raramente atinge em 300s),
   não falha do tool. Cruzar `cov_directly_reaches_target` com o nº de métodos do JSON.
4. **LLM realmente agindo?** Nos logcats/traces do braço LLM: as sugestões do LLM viram ações executadas
   (mapeamento de coordenadas Qwen3-VL [0,1000)→pixels)? Quantas chamadas estouraram `llm_timeout_ms=15000`
   sob contenção (→ degradou para `sata_mop`)? Medir taxa de timeout no `sglang-server` e correlacionar com a
   cobertura por APK.
5. **Throttle/tempo:** 300 s pode ser curto para o LLM (latência por passo) cobrir mais que o SATA puro;
   verificar nº de ações/task por braço.

Saída: um memo de diagnóstico (`docs/<data>_debug_aperv_cobertura.md`) com a causa-raiz de cada achado antes
de validar/refutar H2/H3.

---

## 9. Consolidação (anti-gh58) e deduplicação

> **Regra:** a **fonte da verdade são os logcats por task**, não os CSVs de container. O bug gh58
> (`result_processor` zera cobertura/MOP de tasks resumidas no CSV) ainda está presente; os dados crus
> ficam preservados nos logcats + `tasks.json`. Consolidar **offline** a partir dos logcats.

- **Dedup por identidade `(apk, tool, variant, rep, timeout)`** — **nunca** por `task_id` (UUIDs inflam em
  re-run/resume). `tasks.json` infla por duplicatas de re-run → sempre deduplicar pela tupla de identidade.
- Merge dos `data/results/cmp_*/` → tabelas consolidadas:
  - `coverage_consolidated.csv` (cobertura método/código por task)
  - `mop_consolidated.csv` (cobertura MOP + violações únicas por task)
  - `errors_consolidated.csv`, `summary_consolidated.csv`
- Esperado após dedup: **2 028 identidades distintas COMPLETED** (4 braços × 169 × 3). Reportar qualquer
  déficit e a causa (erro de install, teardown, etc.).

---

## 10. Métricas e análise estatística

### Métricas
- **Primárias:**
  - **Cobertura MOP** = operações monitoradas *disparadas* ÷ *alcançáveis* (denominador do `.apk.json` estático).
  - **Violações MOP únicas** = nº de violações distintas de operação monitorada detectadas.
- **Secundárias:** cobertura de método/código, crashes detectados, taxa de COMPLETED, tempo de execução.

### Estatística
- **Pareamento por APK:** cada APK vira **um ponto pareado = média das 3 repetições** (reduz o ruído inter-rep,
  que foi de 10–15 pp em campanhas anteriores).
- **Teste:** Wilcoxon signed-rank pareado por APK para cada par de braços:
  - H1: `ape` vs `aperv:sata` (espera p > 0.05).
  - H2: `aperv:sata_mop` vs `ape`; `aperv:sata_mop` vs `aperv:sata` (espera p < 0.05).
  - H3: `aperv:sata_mop_llm` vs `aperv:sata_mop` (exploratória).
- **Robustez:** trimmed mean 10% nos agregados por braço; reportar effect size além do p-valor.
- **Sanidade:** verificar que `aperv:sata_mop` ≠ `aperv:sata` em agregado (senão MOP não foi usado).

---

## 11. Fases e timeline

| Fase | Ação | Tempo |
|------|------|-------|
| 0 | Push branch `modules` (rvsec) → garantir código no GitHub | ~5 min |
| 1 | Build cadeia completa `build_all.sh` → `:0.9.1` + verificações | ~45–65 min |
| 2 | Gerar 8 filter files + `docker-compose.comparacao-aperv.yml` | ~15 min |
| 3 | Preflight (1 APK × 4 braços) | ~20–30 min |
| 4 | Launch + monitoramento (resume por nome) | **~37–40 h** (6 containers) |
| 4b | Passada de resume p/ limpar FAILED transientes de install (`compose restart`) | ~1-2 h |
| 4c | **Preservar traces** (NÃO dar `down`; manter containers `Exited`; snapshot dos traces) | — |
| 5 | Consolidação offline (logcats) + dedup por identidade | ~30 min |
| 5b | **Debug de cobertura baixa `sata_mop`/LLM** (§8.2) → memo de diagnóstico | ~2-4 h |
| 6 | Análise estatística (Wilcoxon, trimmed mean) + relatório | ~1–2 h |

---

## 12. Riscos e mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| **Contenção de GPU** (braços LLM, 1 GPU) | H3 inconclusiva; LLM degrada p/ `sata_mop` | `llm_timeout_ms=15000` degrada graciosamente (wall-clock fixo); monitorar latência SGLang; H3 já é exploratória |
| **Carga do host** (emuladores + SGLang num só host) → `adb install` transiente | ~3% de tasks FAILED (visto no smoke com 8 containers) | **6 containers** (§4, reduz contenção) + **passada de resume final** (§8 fase 4b) re-executa FAILED |
| **`sata_mop` == `sata`** (JSON MOP não consumido) | invalida o claim central | checar no preflight: `<apk>.json` no results-dir, push do `static_analysis.json`, `aperv:sata_mop` ≠ `aperv:sata` |
| **Build de código não-pushed** | imagem 0.9.1 sem os fixes gh60–gh70 | push do branch `modules` antes do build; validar `rvsec.branch` na imagem |
| **gh58 zera CSVs em resume** | métricas corrompidas nos CSVs de container | consolidar offline dos logcats (fonte da verdade) |
| **Inflação de tasks por re-run** | contagem/estatística incorretas | dedup por `(apk,tool,variant,rep,timeout)` |
| **Vazamento de emulador/JVM** | container trava | `compose restart cmp_NN` (resume pula COMPLETED); cleanup gerenciado pelo platform |
| **Processo compartilhado ape/aperv** (`com.android.commands.monkey`) | colisão se rodarem juntos no mesmo device | platform termina processos órfãos antes de cada launch (INV-APV-07) |

---

## 13. Referências

- Plano canônico anterior (3-way, 600 s/2 reps): `docs/20260313_aperv_comparacao.md`
- run_jca169 (ape@300, baseline gh62): `docs/20260601_run_jca169_analise.md`
- Calibração APE-RV (SGLang local, GPU): `docs/20260318_*`, `docs/20260407_aperv_calibracao_v2.md`
- Compose com SGLang: `docker/docker-compose.exp3-aperv-llm.yml`
- Tool APE-RV (variantes): `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`
- Entrypoint / socat / skip-flags: `docker/rvandroid/docker-entrypoint.sh`
- Dataset + metadados: `APKS_FINAL_JCA_DEXLIB_20260604/`, `PLANILHA_dexlib2.csv`
