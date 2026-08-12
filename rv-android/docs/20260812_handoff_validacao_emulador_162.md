# Handoff — validar em emulador os 162 APKs instrumentados

> **Este arquivo é o prompt de retomada.** Aponte para ele no início da nova sessão.
> Não edite este arquivo para reportar progresso — progresso se reporta na conversa.

---

## 0. Sua tarefa nesta sessão

**Validar em emulador os 162 APKs instrumentados do Estudo 03.** Nada além disso.

Para cada APK, em série:

1. instalar no emulador;
2. lançar a *main activity*;
3. ler o logcat e decidir: **2 ou mais linhas `RVSEC-COV`** = passou;
4. registrar erro/crash se houver;
5. desinstalar;
6. próximo APK.

Emulador sobe **uma vez** no início e é derrubado **uma vez** no fim.

Isto é a pendência **P7** do registro de execução: a metade do critério do piloto que o
`--skip-execution` não pôde provar. Hoje o corpus está **instrumentado, não validado em
execução** — nenhum dos 162 foi instalado ou lançado.

---

## 1. LEIA ISTO ANTES DE TUDO — a regra do emulador

O `CLAUDE.md` do módulo contém uma regra marcada como **PERMANENTE**:

> **NEVER start, stop, or manage Android emulators manually.** […] This applies to ALL
> contexts: E2E validation, experiments, testing, debugging — no exceptions. Do NOT run
> `emulator` commands, `adb emu kill`, or any emulator-related shell commands.

**O pesquisador autorizou explicitamente, em 2026-08-12, subir o emulador para esta tarefa**,
inclusive indicando usar o mesmo comando da imagem Docker. A autorização é **para esta
validação e só para ela**; a regra continua valendo em todo o resto.

Duas consequências práticas:

- Não invente um caminho novo. Use o comando canônico da §4.1 ou a API do
  `rv_android_core.util.android.android.Android`, que é o mesmo código que o rv-platform usa.
- Se em algum momento a tarefa puder ser feita por `rv-experiment run` / `rv-platform run`,
  prefira. Não foi possível aqui porque `--skip-execution` pula a Fase 2 inteira do
  `ExperimentController` (`:189-197`), que é onde o emulador vive, e uma corrida *com* execução
  arrastaria ferramentas de teste que não queremos nesta validação.

O texto do `CLAUDE.md` **não foi alterado**. Se o pesquisador quiser registrar a exceção lá,
é decisão dele.

---

## 2. Contexto em cinco linhas

A tese tem três estudos. **E3** customiza o APE para guiar exploração por operações monitoradas
(MOP). **Defesa no fim de setembro de 2026; hoje é 2026-08-12; o experimento ainda não rodou.**

Esta linha de trabalho é **prontidão** — deixar os artefatos prontos. Não cobre a execução do
experimento, seus parâmetros, nem a escrita da tese.

O corpus a validar está pronto e é este:

```
/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/
```

162 `<nome>.apk` + 162 `<nome>.apk.json` co-locados + `selected162.txt`. 4,3 GB.

---

## 3. O que já foi feito (2026-08-11/12)

Tudo está narrado em **`rv-android/docs/20260812_registro_execucao_prontidao_e3.md`** — leia-o
antes de agir. Resumo:

**Fase A — análise estática dos 30 com WTG.** 18,05 h, 25/30 completos. **Gate A REPROVOU**, só
na asserção 3.2. Descobriu-se que o WTG do GATOR trava para sempre quando um `CFGWorker` morre
por exceção (`CFGWorker.java:33-42` + `CFGScheduler.java:66-72`) — determinístico, indiferente a
memória e tempo.

**Fase B — instrumentação.** **162/163** em 3 h 53 min, com 8 fatias paralelas (o plano orçava
27 h seriais). O APK excluído é `info.dvkr.screenstream_44000.apk`: o `classes28.dex` dele já
tem 65.521 dos 65.536 `method_ids` que o formato DEX permite, e a tecelagem não cabe em 15
slots. Decisão do pesquisador: **fecha com 162**.

**Diretório final montado** e verificado (pareamento 1:1, lista, sha256 contra o manifesto da
Fase B).

Commits: `1679a0e3` (scripts da Fase A), `1f4e7f00`, `f27fcf49`, `c5ac22db`, `a44ad8b6` (docs).

---

## 4. O protocolo — o que existe e é reusável

**Não escreva do zero antes de olhar isto.** Boa parte já existe.

### 4.1 Subir o emulador — o comando da imagem Docker

`rv-android/scripts/run_emulator.sh`, com os flags já comentados um a um no arquivo:

```sh
emulator @RVSec -writable-system -wipe-data -no-boot-anim -noaudio \
         -no-snapshot-save -delay-adb -no-window
```

O AVD é **`RVSec`** — é o único provisionado nesta máquina (`ls ~/.android/avd/`), e é o default
de `rv_platform/components/emulator.py:120`.

> **Divergência real, que você tem de resolver conscientemente.** A API do rv-platform
> (`Android.start_emulator`, `modules/rv-android-core/src/rv_android_core/util/android/android.py:135-150`)
> usa um conjunto **diferente** de flags: `-read-only -no-cache` em vez de
> `-writable-system -wipe-data`, mais `-port`. O `-read-only` existe para permitir múltiplas
> instâncias do mesmo AVD; o `-writable-system` existe porque o GATOR empurra hooks. Como aqui
> é **uma** instância e **não** há GATOR, os dois caminhos servem. O pesquisador pediu o comando
> da imagem Docker — então use o `run_emulator.sh`, mas **declare no relatório qual foi usado**,
> porque isso muda o estado do device entre execuções (`-wipe-data` zera; `-read-only` não).

Esperar o boot: `Android._wait_for_boot(device_name)` (`android.py:225`) já implementa a espera
correta, com `RV_EMULATOR_BOOT_TIMEOUT` (default 300 s) e `RV_ADB_CMD_TIMEOUT` (default 30 s).

Derrubar no fim: `Android.kill_emulator(avd_name, device_name)` (`android.py:160`) — faz
`adb emu kill -s <device>` sem matar o servidor adb.

### 4.2 Instalar / desinstalar

`Android.install_apk` (`:409`), `Android.install_with_permissions` (`:386`),
`Android.grant_permissions` (`:496`), `Android.uninstall_apk` (`:479`).

Precedente direto e reusável: **`rv-android/scripts/validate_ajc_apks_install.py`** — já faz
`adb install -r -g` → registra exit code + stderr → `adb uninstall` → próximo, **em série, com
resume por CSV**. Foi escrito para a variante `ajc`, mas o laço, o cache por APK e o resume são
exatamente o que esta tarefa precisa. Leia antes de escrever qualquer coisa.

### 4.3 Lançar a main activity — e a armadilha conhecida

O padrão usado no projeto (`modules/rv-tools/src/rv_tools/builtin/qtesting/src/main.py:22-49`):

```sh
aapt dump badging <apk> | grep package          # → nome do pacote
aapt dump badging <apk> | grep launchable        # → launchable-activity
adb shell am start -S -n <pkg>/<activity>
```

> **ARMADILHA MEDIDA, com causa-raiz fechada.** Na campanha de julho, **21 APKs** de 219
> declaram `MAIN`/`LAUNCHER` apenas em `<activity-alias>`. Nesses, o `aapt dump badging` **não
> emite `launchable-activity`**, o qtesting lançava `Intent { cmp=<pkg>/noactivityname }` e caía
> em `Error type 3` — resultando em logcat **sem `RVSEC-COV`** por falha de lançamento, não por
> falha de instrumentação. Documentado em
> `experimento-20260706/docs/residual/NOCOV_LOGCATS.md` e no `nocov_235.csv`.
>
> **Trate isto explicitamente.** Se não houver `launchable-activity`, caia para
> `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1`, ou leia o
> `<activity-alias>` do manifest. E **classifique o resultado**: "não lançou por falta de
> launchable" é diferente de "lançou e não cobriu". Se você não separar isso, vai reportar
> falha de instrumentação onde não há.

### 4.4 Ler o logcat

Limpar antes de cada APK: `EmulatorManager.clear_logcat`
(`modules/rv-android-core/src/rv_android_core/util/android/emulator_manager.py:152`) ou
`adb -s <device> logcat -c`. Capturar depois com `adb logcat -d`.

**Critério desta sessão: 2 ou mais linhas `RVSEC-COV`.** É o marcador que a instrumentação de
cobertura emite a cada entrada de método instrumentado.

> **Segunda armadilha medida.** Há casos com `RVSEC-COV` presente mas **apenas de infraestrutura
> de injeção de dependência** (`dagger.hilt.*`), com zero eventos do namespace do próprio app —
> cobertura real nula apesar do marcador. Documentado em
> `experimento-20260706/docs/residual/ZEROCOV_STARDROID.md`. **Vale contar também quantas
> linhas `RVSEC-COV` casam com o pacote do app**, e registrar as duas contagens. O critério que
> o pesquisador pediu é 2+; a segunda contagem é informação adicional, não critério — não
> reprove ninguém por ela sem perguntar.

Erros/crash a detectar no logcat: `FATAL EXCEPTION`, `ANR in`, `VerifyError`,
`Error type 3`, `force-stop`.

### 4.5 Alternativa em Java, se preferir

`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/.../BootValidator.java` tem um
modo `capture` que dirige `adb install / monkey / logcat -d` sobre um diretório de APKs, e um
modo `analyze` que extrai sítios de `VerifyError`. Ele **deliberadamente não gerencia o ciclo do
emulador** (respeita a regra do `CLAUDE.md`). Pode ser reusado, mas é orientado a comparar
`ajc` × `dexlib2` — o que **não** é o caso aqui, então provavelmente o caminho Python é mais
direto.

---

## 5. Roteiro sugerido

1. **Ler** `docs/20260812_registro_execucao_prontidao_e3.md` (§3 é o diretório; §4 são as
   pendências) e `scripts/validate_ajc_apks_install.py`.
2. **Conferir o corpus**: 162 `.apk`, 162 `.apk.json`, `selected162.txt` com 162 linhas.
3. **Escrever o driver** — reusando o laço/resume do `validate_ajc_apks_install.py`. Requisitos
   não negociáveis: **serial**; **resume** (a corrida é longa e pode ser interrompida); estado
   em CSV/JSON por APK; e **classificação separada** de (a) falha de instalação, (b) falha de
   lançamento, (c) lançou mas `RVSEC-COV` < 2, (d) crash/erro, (e) passou.
4. **Gate barato**: rodar em **3 APKs** primeiro — um grande, um pequeno e, se der para
   identificar, um sem `launchable-activity`. Só depois soltar os 162.
5. **Subir o emulador uma vez**, rodar os 162 em série, **derrubar uma vez** no fim.
   Processo longo vai em **background rastreado pelo harness**, nunca `nohup`/`setsid`.
6. **Reportar na conversa**: quantos passaram, e a distribuição das falhas por classe.
7. **Atualizar** `docs/20260812_registro_execucao_prontidao_e3.md` (fechar a **P7**, com os
   números) e a memória do projeto, se houver aprendizado durável.

**Tempo:** 162 APKs em série, com install + launch + logcat + uninstall. Se cada um levar
30–60 s, são **1,5 a 3 h**. Meça nos 3 do gate barato e projete antes de soltar.

---

## 6. Arquivos relacionados

### Corpus e artefatos
| caminho | papel |
|---|---|
| `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/` | **o corpus a validar** — 162 APK + 162 JSON + `selected162.txt` |
| `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/` | origem: `monitors_master/`, fatias `s0..s7/`, `instrumented_apks/` com `instrument_results.json` e `SHA256SUMS` |
| `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg/` | saída da Fase A (30 JSON, `REGISTRO.md`, `logs/`, `_progress/`) |

### Código a reusar (ler, não reinventar)
| caminho | o que tem |
|---|---|
| `rv-android/scripts/run_emulator.sh` | **o comando do emulador da imagem Docker**, com os flags comentados |
| `rv-android/scripts/validate_ajc_apks_install.py` | laço serial install→uninstall com resume por CSV — o precedente mais próximo |
| `modules/rv-android-core/src/rv_android_core/util/android/android.py` | `start_emulator` `:120`, `kill_emulator` `:160`, `_wait_for_boot` `:225`, `install_apk` `:409`, `install_with_permissions` `:386`, `uninstall_apk` `:479`, `grant_permissions` `:496` |
| `modules/rv-android-core/src/rv_android_core/util/android/emulator_manager.py` | `clear_logcat` `:152` e preparo do device |
| `modules/rv-platform/src/rv_platform/components/emulator.py` | o componente sancionado; AVD default `RVSec` em `:120` |
| `modules/rv-tools/src/rv_tools/builtin/qtesting/src/main.py:22-49` | padrão `aapt dump badging` → `am start -S -n` |
| `rvsec/.../validator/.../BootValidator.java` | captura `adb install/monkey/logcat` + análise de `VerifyError` |

### Armadilhas já medidas (leia antes de interpretar resultado)
| caminho | o que evita |
|---|---|
| `experimento-20260706/docs/residual/NOCOV_LOGCATS.md` + `nocov_235.csv` | os 21 APKs sem `launchable-activity` (MAIN/LAUNCHER só em `activity-alias`) |
| `experimento-20260706/docs/residual/ZEROCOV_STARDROID.md` | `RVSEC-COV` presente mas só de `dagger.*` — cobertura real nula |
| `experimento-20260706/docs/residual/RESIDUAL_MONKEY.md` | corte de logcat por kill externo (OOM de host), sem crash no log |

### Documentos diretores
| caminho | papel |
|---|---|
| `rv-android/docs/20260812_registro_execucao_prontidao_e3.md` | **o registro da execução**; §3 o diretório, §3.1 os 40 WTG truncados, §4 as pendências |
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` | o plano; §8 é o índice de artefatos |
| `rv-android/docs/20260811_handoff_fase_a_analise_estatica.md` | handoff da Fase A (histórico) |

---

## 7. Comandos

```bash
# Raízes
RVA=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
W=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
C=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162
export RVSEC_HOME=$W/rvsec

# Conferir o corpus
ls $C/*.apk | wc -l      # 162
ls $C/*.apk.json | wc -l # 162
wc -l < $C/selected162.txt

# Emulador (comando da imagem Docker) — AUTORIZADO só para esta tarefa
cd $RVA && sh scripts/run_emulator.sh &
adb devices                      # esperar 'emulator-5554  device'
adb shell getprop sys.boot_completed   # '1' quando pronto

# Um APK, manualmente (para o gate barato)
APK=$C/<nome>.apk
aapt dump badging $APK | grep -E "^package|launchable-activity"
adb install -r -g $APK
adb logcat -c
adb shell am start -S -n <pkg>/<activity>
sleep 10
adb logcat -d > /tmp/x.logcat
grep -c "RVSEC-COV" /tmp/x.logcat
grep -cE "FATAL EXCEPTION|ANR in|VerifyError|Error type 3" /tmp/x.logcat
adb uninstall <pkg>

# Derrubar no fim
adb emu kill

# Testes (flags obrigatórias)
cd $RVA && uv run pytest --import-mode=importlib -o "addopts=" <caminho>
```

---

## 8. Aprendizados desta linha de trabalho — não repita

1. **Verificar o código antes de afirmar mecanismo.** Handoff, relatório e aritmética **não**
   são verificação. Nesta linha, três conclusões foram afirmadas e tiveram de ser retiradas,
   todas por inferir de números agregados em vez de abrir o fonte. Cite `arquivo:linha`.
2. **`matchesApplied` não conta sítios MOP tecidos** — quem conta é `wrappersSubstituted`
   (`DexWeaver.java:395-403`). Um APK pode ter `matchesApplied = 0` e estar corretamente
   instrumentado.
3. **O sentinela `complete: true` do GATOR não distingue WTG vazio de WTG morto por timeout.**
   A causa só está no `_progress`. Limitação modesta, não corrupção; decidido não corrigir.
4. **O relatório do instrumentador não preserva a causa das falhas** (`BatchRunner.java:381-382`
   descarta trace e `getCause()`; `failed()` zera os contadores). Diagnostique pelos
   intermediários do `--work-dir`.
5. **`/tmp` nesta máquina é tmpfs (62 GiB, em RAM).** Para GATOR, exportar `TMPDIR` para
   `/pedro`. **Para instrumentação não é gargalo** — o scratch vai para o `--work-dir`. Para
   logcat/emulador, medir antes de assumir.
6. **A geração de monitores não é paralelizável** (JavaMOP estagia `.rvm` no diretório de specs
   compartilhado). Irrelevante aqui, mas não a paralelize se voltar a gerar.
7. **Sharding por processo funciona e é barato** quando cada fatia tem seu `--output-dir`. Foi
   o que trocou 27 h por 3 h 53 min na Fase B.
8. **Gate barato antes de queimar a janela.** Um piloto de 10 pegou um defeito de concorrência
   que teria tecido 163 APKs sem monitor e reportado sucesso.
9. **Não sugerir atalhos que reaproveitem artefatos parciais.** Integridade acima de tempo.
10. **Perguntar antes de decidir o que é do pesquisador.**

---

## 9. Regras de trabalho — seguir rigorosamente

Além do `CLAUDE.md` da raiz (`rvsec/CLAUDE.md`) e do módulo (`rvsec/rv-android/CLAUDE.md`), que
são autoritativos:

- **Workflow**: `docs/WORKFLOW.md`. Para qualquer coisa rastreada em `openspec/changes/gh<N>-*/`,
  invocar as skills OpenSpec via a ferramenta `Skill`. **Nunca** criar ou reescrever artefato
  OpenSpec com `Write`/`Edit` direto. *(Esta validação não é uma change OpenSpec — é execução de
  pendência do plano. Não abra change para ela.)*
- **Emulador**: ver §1. Autorização pontual, para esta tarefa; a regra do `CLAUDE.md` continua
  valendo em todo o resto.
- **Não mexer no gator.** `rvsec-gator` só muda por erro grosseiro; melhorias vão por offline ou
  pelo consumidor. **Não reconstrua o reator** — o `mvn install` de raiz sobrescreve os jars em
  `lib/gator/` e quebra a proveniência já assinada.
- **Background**: processos longos em background rastreado pelo harness, nunca `nohup`/`setsid`.
- **Commits**: nunca adicionar `Co-Authored-By` nem qualquer trailer de coautoria.
- **Português**: sempre com acentuação correta, mesmo que o pesquisador escreva sem acentos.
- **Testes**: `uv run pytest --import-mode=importlib -o "addopts="` — sem essas flags a coleta
  quebra.
- **P1–P4** (simplicidade, documentação narrativa, sem retrocompatibilidade, comentários do
  estado atual) governam todo código, comentário e documento.
- **Não editar handoffs e prompts do pesquisador.** Progresso se reporta na conversa.
- **`experimento-cal` é histórico** — não editar nem adaptar.

---

## 10. O que NÃO fazer nesta sessão

- **Não reinstrumentar nada.** A Fase B está fechada em 162; o `screenstream` está excluído por
  decisão registrada.
- **Não rodar análise estática.** A Fase A está encerrada, com o Gate A reprovado e a decisão da
  P1 ainda pendente.
- **Não reconstruir o reator** (`mvn install`).
- **Não tentar consertar** o `CFGWorker` do gator, o sentinela, o relatório do `instr-cli` nem o
  limite de 64K do DEX — todos estão registrados como pendências, e nenhum é escopo desta
  sessão.
- Não expandir para a execução do experimento nem para a escrita da tese.
- Não criar branch. A branch é `modules`.
- Não gerenciar emulador fora do escopo desta validação.

---

## 11. Pendências abertas do registro (contexto, não tarefa)

`docs/20260812_registro_execucao_prontidao_e3.md` §4 lista P1–P11. As que importam saber:

- **P7 — é a sua tarefa.** Validar os 162 em execução.
- **P1** — o Gate A não fecha com os 5 truncados; decisão do pesquisador, não tomada.
- **P11** — 40 dos 162 `.apk.json` carregam WTG truncado (5 da Fase A, 35 da Phase-7). Afeta o
  braço guiado, que consome `wtgEdges`. **Não afeta esta validação**, que só olha `RVSEC-COV`.
