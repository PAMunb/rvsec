# Handoff — implementar a gh102 e destravar a `comp162`

Sessão nova. Este documento é o estado completo; não presuma nada além dele sem verificar no
código ou nos artefatos.

---

## 1. O objetivo

**Implementar a change `gh102-artifact-scoped-parse`** (issue #102) — que tira o pacote do caminho
de consumo do artefato de análise estática — e, com a correção dentro da imagem, **rodar a campanha
`comp162`** que hoje está bloqueada por esse defeito.

A `comp162` **não é o experimento final do Estudo 03**. É um ensaio: ver como a instrumentação nova
se comporta na grade que a `cmp163` já exercitou, antes que o experimento final dependa dela. O
plano dela é `docs/20260812_comp162.md`; o handoff operacional original, ainda válido do Passo 4 em
diante, é `docs/20260812_comp162_handoff_prompt.md`.

**O andaime da campanha está pronto e verificado. O que falta é a correção de código, e depois
operar.**

---

## 2. O defeito, e por que ele bloqueia a campanha

O `StaticAnalysisParser` re-filtra por pacote um `.apk.json` que o GATOR **já entregou escopado**.
O GATOR é invocado com `-clientParam codePackage=<chave>` e registra o que removeu
(`[RvsecAnalysisClient] Filtered 4431 classes (libraries/generated) using package: ...`). O membro
`reachability` que ele escreve **é o 100 % da cobertura** — o denominador inteiro. Um segundo filtro
sobre essa lista não pode acrescentar informação; só pode tirar.

Desde a gh98 (`553ae54a`) o `App.code_package` devolve o applicationId declarado. Em app construído
com `applicationIdSuffix`, `io.keepalive.android.debug` não está contido em
`io.keepalive.android.MainActivity`, e o filtro esvazia o universo. **75 dos 162 APKs do corpus
medem cobertura 0,00 em todos os braços** e seriam excluídos pelo critério C5 — a campanha fecharia
em n=87.

Os dois sítios do pacote têm destinos diferentes, e essa distinção é o miolo do design:

| Sítio | Papel | Evidência |
|---|---|---|
| `static_analysis_parser.py:361` (classes) | **no-op** quando a chave está certa | 0 de 215.430 classes dos 162 JSONs caem fora da chave do produtor (`startsWith`) |
| `static_analysis_parser.py:428` (windows ACTIVITY) | **carrega peso real** | 125 dos 162 têm activity de framework nas `windows`, que o GATOR não escopa |

A regra que substitui o segundo filtro sai do próprio artefato: **uma ACTIVITY é do app se e somente
se a classe dela está em `reachability`**. Concorda com a decisão por chave em **162/162**, sobre
1.526 activities, zero divergência.

---

## 3. O que já foi feito (não refazer)

### 3.1 Da campanha `comp162`

1. **Push conferido** — `origin/modules` continha `c1d28365` (guarda INV-APV-60).
2. **Imagem construída** — `phtcosta/rvandroid:0.9.3-comp162`,
   `sha256:2c406490cac4b7572486aabdc89fdee63681f37a87adcb1fcdf82f74628f843d`, com o commit
   `45a6e74d` dentro. As tags `0.9.3` e `latest` seguem intactas em `b2904fdfc3dd`.
   **Esta imagem carrega o parser defeituoso** — vai precisar de rebuild.
3. **Manifesto fechado** com o ID da imagem: `corpus_basis = selected162:3bbc5fa9…`,
   **1458 identidades previstas**.
4. **Filtros re-verificados** (`make_filters.py --check`): `[21,20,21,20,20,20,20,20]` = 162.
5. **Jar sob teste conferido**: `a7eddf5a776ce20f7299911d7d9acb3a0f1342cdc1512b3e28aa00488e582a94`
   — o mesmo da `cmp163` e da perna B da gh97.
6. **Corpus conferido**: sha256 `3bbc5fa9…`, 162 `.apk` + 162 `.apk.json` + a lista.
7. **Dois smokes rodados**, e é aqui que mora a armadilha operacional — ver §6.2.

### 3.2 Da change `gh102`

8. **Issue #102 criada** em `PAMunb/rvsec`, com `type:bug`, `track:ff-sdd`, `domain:analysis`,
   `priority:high`, e as medições no corpo.
9. **Change `gh102-artifact-scoped-parse` completa** — 4/4 artefatos, `openspec validate` passa.
   Schema `rv-sdd` (FF SDD: módulo único com implicação de spec).
10. **Card do board NÃO movido** — o token do `gh` não tem escopo `project` (mesma pendência que
    sobrou da gh97). Para resolver: `gh auth refresh -s read:project`, que é interativo — peça ao
    pesquisador rodar com `! gh auth refresh -s read:project`.

---

## 4. Próximos passos, em ordem

### Passo 1 — implementar a change

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Invocar a skill pela ferramenta `Skill`: **`openspec-apply-change`** com
`gh102-artifact-scoped-parse`. **Não** escrever os artefatos nem editar código fora do fluxo — o
`CLAUDE.md` torna as skills OpenSpec obrigatórias para qualquer coisa sob `modules/**`.

O `tasks.md` tem 6 grupos. Os grupos 2 e 3 são independentes entre si e podem ir em paralelo depois
do 1. O grupo 2 é o único grande o bastante para justificar subagente: são **77 chamadas de teste**
no `rv-static-analysis` que passam pacote (mais 2 no `rv-platform` e 4 no `rv-agent`).

**Contrato de CI, sempre**: `pytest --import-mode=importlib -o "addopts="`.

### Passo 2 — verificar e sincronizar

- `openspec-verify-change` antes de arquivar.
- Task 5.6: `openspec-sync-specs` para levar o delta ao `openspec/specs/analysis/spec.md` —
  entram INV-ANA-59/60/61, sai o INV-ANA-03, e o INV-ANA-58 fica restrito ao caminho de produção.

### Passo 3 — commitar e **empurrar**

O `docker/rvandroid/Dockerfile` faz `git clone --branch ${RVSEC_BRANCH}` de
`https://github.com/PAMunb/rvsec.git`. **Ele clona o remoto, não copia a árvore local.** Sem push, a
imagem sai sem a correção.

Hoje o `HEAD` local (`c9d973bb`) já está **1 commit à frente** de `origin/modules`. Depois de
commitar a gh102, empurrar tudo. Confirmar antes do rebuild:

```bash
git fetch origin modules && git branch -r --contains $(git rev-parse HEAD)
```

**Commits: o pesquisador é o autor único — nunca adicionar `Co-Authored-By` nem qualquer trailer de
coautoria. Não commitar nem empurrar sem pedido explícito.**

### Passo 4 — rebuild da imagem (task 6.1)

```bash
docker build --no-cache --build-arg RVSEC_BRANCH=modules \
  -t phtcosta/rvandroid:0.9.3-comp162 docker/rvandroid
```

- **`--no-cache` não é opcional**: o `RUN git clone` é uma camada como outra qualquer.
- **Não usar `docker/rvandroid/build.sh`** — ele marca `0.9.3` e `latest`, que são a identidade da
  imagem da perna A do E3 e não podem ser sobrescritas.
- Levou ~25 min da última vez. Rodar em background e **não ficar em laço de espera** (§6.1).
- Depois: refazer o Passo 2 do handoff da campanha — `make_manifest.py --image-id ...`, porque o ID
  da imagem muda.

### Passo 5 — smoke, e os sete portões (task 6.2)

**Antes de subir, limpar `results_smoke/`** — senão o resume pula as identidades já `COMPLETED` e o
smoke não roda de verdade. Ver §6.2.

```bash
cd experimento-comp162
docker compose -f docker-compose.smoke.yml up -d      # 2 apps, 1 rep, 120 s, 6 identidades
uv run python scripts/smoke_gates.py                  # o criterio e o script, nao o `up -d`
```

Os dois APKs do smoke (`io.keepalive.android_133`, `de.markusfisch.android.binaryeye_174`) são
**justamente builds com `applicationIdSuffix`**, então eles exercitam a correção: com o parser
defeituoso os portões 2 e 5 reprovam com cobertura 0.

Só depois de **7/7 PASS**: `docker compose -f docker-compose.smoke.yml down`.

### Passo 6 — a campanha, e daí em diante

Do **Passo 4 do `docs/20260812_comp162_handoff_prompt.md`** em diante, sem alteração: `docker
compose up -d`, ~19 h, passada de resume, `consolidate.py` → `analise.py` → `compare_cmp163.py`, e o
relatório no molde de `docs/20260807_resultados_cmp163.md`.

Uma coisa a acrescentar ao relatório (task 6.3): **medições posteriores a esta correção não são
comparáveis à `cmp163` nas aplicações afetadas**, e o porquê está na §7.3 daqui.

---

## 5. Workflow — seguir rigorosamente

- **`CLAUDE.md` da raiz e do `rv-android` mandam.** Ler antes de agir. `docs/WORKFLOW.md` é a
  referência do processo.
- **Skills OpenSpec são obrigatórias** para tudo sob `modules/**` — invocar pela ferramenta `Skill`,
  nunca escrever os artefatos à mão.
- **NUNCA gerenciar emulador à mão.** Nada de `emulator`, `adb emu kill`, start/stop. O
  `rv-platform` cuida do ciclo inteiro. Regra permanente, sem exceção.
- **Commits**: autor único, sem trailer de coautoria. `refs #102` durante, `closes #102` no final.
- **P1–P4**: simplicidade; documentação narrativa que explica o *porquê*; sem retrocompatibilidade
  (código morto é apagado, com backup em `backup/`); comentários do estado atual.
- **Português com acentuação correta** em toda documentação.
- **Skill de apoio**: `rv-experiment-compare` documenta o ciclo de 4 fases da campanha e os gotchas
  de campo.

---

## 6. Operação

### 6.1 NÃO criar monitoramento automático

**Instrução explícita do pesquisador.** Nada de cron, `/loop`, `Monitor` persistente, `watch` em
background, ou laço de polling.

Consultar o estado **sob demanda** (`bash scripts/monitor.sh`). Para esperar algo pontual terminar
(o `docker build`, o `consolidate.py`), usar um comando em background que **sai sozinho quando a
condição é satisfeita** — uma notificação, não um fluxo. Padrão que funcionou:

```bash
while [ -n "$(docker ps -q --filter name=comp162smoke)" ]; do sleep 20; done; echo PRONTO
```

Nunca fabricar nem antecipar o resultado de algo que ainda está rodando.

### 6.2 `results_smoke/` precisa ser limpo antes de cada smoke

O resume **pula identidade `COMPLETED`**. Se `results_smoke/` tiver a corrida anterior, o `up -d`
sobe, não executa nada e sai — e os portões avaliam dados velhos.

**Estado atual: `results_smoke/` contém a segunda corrida de smoke, feita com o `PackageDetector`
ligado — configuração que foi revertida e é proibida (§7.1).** Aqueles números não valem. Limpar
antes de rodar de novo:

```bash
docker compose -f docker-compose.smoke.yml down
mkdir -p ../backup/comp162-smoke-detector-20260812
mv results_smoke/* ../backup/comp162-smoke-detector-20260812/
mkdir -p results_smoke/comp162smoke_00 results_smoke/comp162smoke_01
```

`results/` (a campanha) está **vazio** — nunca rodou.

---

## 7. Aprendizados — não re-aprender

### 7.1 O `PackageDetector` está fora, e isso é decisão do pesquisador

**Não usar `RV_PACKAGE_DETECTOR`, não ligar `--package-detector`, não propor nenhum dos dois.** Foi
dito de forma enfática e repetida. Eu tinha proposto isso como conserto e estava errado por duas
razões:

- Ele é heurística (prefixo comum, frequência, game engine, Jaro-Winkler; 88,9 % de resolução em 40
  APKs) e **discorda da chave do produtor em 30 de 30** linhas auditadas de `30_apks.csv`.
- Quando elege chave **mais longa**, trunca o denominador **em silêncio**.

Os composes foram revertidos: hoje **não há** `RV_PACKAGE_DETECTOR` em nenhum dos dois, e ambos
passam `docker compose config`.

### 7.2 `reachability` é o 100 % da cobertura

No `.apk.json`, `reachability` é a **lista completa de métodos** detectados com o pacote passado na
análise estática. **Não é o subconjunto alcançável.** O nome ficou assim porque as entradas carregam
*flags* da análise de alcançabilidade (`reachable`, `reachesTarget`, `directlyReachesTarget`).
**Não renomear** — decisão explícita do pesquisador. Ler o nome como "só o alcançável" foi o que
levou ao defeito em primeiro lugar.

### 7.3 Cinco APKs da `cmp163` foram medidos com denominador truncado

A `cmp163` rodou na imagem `0.9.3-rearch`, onde `code_package` invocava o detector
incondicionalmente. Onde ele elegeu chave mais longa:

| APK | chave do produtor | chave do detector | classes | activities | o que a `cmp163` publicou |
|---|---|---|---:|---:|---|
| `org.wikipedia_50595` | `org.wikipedia` | `org.wikipedia.diff` | 7987 → **78** | 73 → **1** | `cov_act=0` → **excluído por C5** |
| `app.pachli_50` | `app.pachli` | `app.pachli.core` | 6453 → **2466** | 27 → **0** | `cov_act=0` → **excluído por C5** |
| `com.jerboa_87` | `com.jerboa` | `com.jerboa.MainActivity` | 3171 → **140** | 1 → 1 | `cov_method=56,89` · `cov_act=100` |
| `swati4star.createpdf_110` | `swati4star.createpdf` | `…createpdf.activity` | 529 → **35** | 10 → 10 | `cov_method=27,03` |
| `net.osmtracker_73` | `net.osmtracker` | `…osmtracker.activity` | 232 → **140** | 19 → 19 | `cov_method=33,84` |

As duas exclusões por "cobertura zero" são **artefato da chave**, não propriedade das aplicações. Os
outros três entraram nas estatísticas publicadas com denominador truncado. **Re-ler a `cmp163` não
faz parte da gh102** — está registrado na proposal como fora de escopo, e é decisão do pesquisador.

### 7.4 Onde mora a proveniência da análise estática

- `rvsec-dataset-sa/logs/*.log` — 348 logs, os 132 APKs herdados da Phase-7.
- `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/logs/*.log` — 30 logs, a re-análise da Fase A.
- A chave está em `[RvsecAnalysisClient] Filter package:` ou em `codePackage=` — **este último
  aparece na linha ~200**, dentro do argv do java. Ler só o cabeçalho do arquivo **não** encontra:
  foi assim que 65 APKs pareceram "sem proveniência" numa primeira passada errada. Lendo o arquivo
  inteiro, a recuperação é **162/162**.
- `rv-android/30_apks.csv` tem a coluna **`Mneut`** — o pacote curado à mão para os 30 da Fase A,
  usado verbatim como `-clientParam codePackage=` (`scripts/gh91_sa_rerun.py:266`). É
  `manifest_package` menos o sufixo de build.

### 7.5 A regra determinística que reproduz a chave

"Maior prefixo pontuado do applicationId que casa com alguma classe" reproduz o `codePackage`
registrado em **162/162**. Serve para auditoria offline — **não** é o conserto, e não deve virar
código: o conserto é não perguntar o pacote.

### 7.6 Operacionais da campanha

- **Contar por IDENTIDADE** `(apk, tool, variant, rep, timeout)`, nunca por registro — o resume
  acrescenta em vez de sobrescrever. E **nunca** `grep '"state": "COMPLETED"' tasks.json`: conta em
  dobro por causa de `state_transitions`.
- **Atraso aparente não é travamento.** O `tasks.json` só é gravado quando a task fecha, então a
  seguinte já está em voo e invisível. Atraso normal chega a ~2 ciclos (~12 min a 300 s).
- **Não dar `down` antes de extrair os traços** — artefatos são efêmeros no device.
- **`consolidate.py` demora minutos** (~1458 logcats, ~7,5 GB). Rodar em background.
- **O reparo só toca container que NÃO está rodando** — o `cycle.sh` já respeita isso.
- **Com a guarda INV-APV-60 na imagem, zero reparos é o esperado.** Se o `repair.py` achar trabalho,
  isso é informação, não rotina.
- **Ciclo medido no smoke**: 178 s para orçamento de 120 s → sobrecarga ~58 s/run → **358 s/run a
  300 s** → 18,8 h no lote de 21 APKs. A referência da `cmp163` no mesmo host era 370 s/run.
- **`/tmp` é tmpfs de 62 GiB em RAM nesta máquina.** Exportar `TMPDIR` para `/pedro` em qualquer
  corrida de GATOR.

---

## 8. Arquivos

### Da change

| Caminho | Papel |
|---|---|
| `openspec/changes/gh102-artifact-scoped-parse/proposal.md` | O porquê, o BREAKING, a capability modificada |
| `openspec/changes/gh102-artifact-scoped-parse/specs/analysis/spec.md` | INV-ANA-59/60/61; INV-ANA-03 em REMOVED; INV-ANA-58 restrito à produção |
| `openspec/changes/gh102-artifact-scoped-parse/design.md` | D1–D4, mapeamento spec→impl→teste, riscos |
| `openspec/changes/gh102-artifact-scoped-parse/tasks.md` | 6 grupos, com dicas de despacho de subagente |

### Do código a mexer

| Caminho | O quê |
|---|---|
| `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py` | `_parse_classes:361`, `_parse_windows:428`, `parse_file`, `read_static_analysis_files` e os dois wrappers de módulo |
| `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py:439` | chamador |
| `modules/rv-platform/src/rv_platform/components/static_analysis.py:133` | chamador |
| `modules/rv-platform/src/rv_platform/components/result_processor.py:270` | chamador (caminho de reconstrução no resume) |
| `modules/rv-static-analysis/src/rv_static_analysis/config.py:397` | **NÃO tocar** — o produtor continua passando `codePackage=` |

### Da campanha

| Caminho | Papel |
|---|---|
| `docs/20260812_comp162.md` | O plano da campanha |
| `docs/20260812_comp162_handoff_prompt.md` | O handoff operacional original (Passo 4 em diante ainda vale) |
| `experimento-comp162/README.md` | O desenho e o procedimento |
| `experimento-comp162/scripts/smoke_gates.py` | Os sete portões; sai 1 em FAIL |
| `experimento-comp162/scripts/admissibility.py` | A regra de admissibilidade, num lugar só |
| `experimento-comp162/scripts/monitor.sh` · `cycle.sh` | Progresso; monitor→reparo→resume |
| `experimento-comp162/scripts/consolidate.py` · `analise.py` · `compare_cmp163.py` | A cadeia de análise |
| `data/results/cmp163_consolidado/` | Os CSVs da campanha de referência |
| `backup/comp162-smoke-reprovado-20260812/` | O primeiro smoke, o que expôs o defeito |

### Dataset

`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`
— 162 `.apk` + 162 `.apk.json` co-locados + `selected162.txt`, 4,3 GB, sha256 `3bbc5fa9…`.

---

## 9. Estado do git

Branch `modules`. `HEAD` = `c9d973bb` ("feat(e3): validar os 162 em emulador e fechar a P7"),
**1 commit à frente de `origin/modules`** e ainda não empurrado.

Untracked: `experimento-comp162/`, `docs/20260812_comp162.md`,
`openspec/changes/gh102-artifact-scoped-parse/`, e este handoff. O `.gitignore` recebeu as entradas
de `results/` e `results_smoke/` da campanha.

Modificado e **revertido ao original**: os dois composes de `experimento-comp162/` — o
`RV_PACKAGE_DETECTOR` que eu tinha acrescentado saiu, e ambos passam `docker compose config`.

Nada da gh102 foi commitado. Não commitar nem empurrar sem pedido explícito do pesquisador.
