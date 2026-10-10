# experimento-smk124 — verificação do carimbo Compose (gh124)

## Propósito

A change `gh124-compose-stamp-f0-material` (issue #124) corrige dois pontos em que o carimbo
Compose da gh121 (`mop.RvsecStamp.composeHandler`) nomeava uma classe de biblioteca em vez do
handler do app:

- **passo do nó:** quando a lambda da ação não tem `this$0`, o helper lê `f$0` e o trata como o
  nó clicável só se ele for um `androidx.compose.foundation.AbstractClickableNode` (forma do D8
  na foundation ≥ 1.9);
- **etapa Material:** um handler `androidx.compose.material*` com exatamente um campo
  `kotlin.jvm.functions.Function*` é lido uma vez; o valor só é carimbado se a classe dele
  estiver fora de `androidx.` (o `onCheckedChange` do app por trás do `Checkbox`).

Este diretório reúne o que verifica a mudança fora dos testes JVM do `monitor-builder`:

- **equivalência** (tarefa 4.4): o jar novo e o jar anterior à change produzem DEX do app
  idênticos e os mesmos `weaveCounts` no saucenao; só o DEX do monitor muda, e só em
  `mop.RvsecStamp`;
- **smoke no dispositivo** (tarefas 5.1–5.5): três apps Compose rodados pelo APE-RV com a guia
  MOP, com a análise das linhas `RVSEC-BIND` contra a tabela `handlers` do artefato MOP.

Os resultados estão em `RELATORIO.md`.

## Conteúdo

| Caminho | O que é |
|---|---|
| `baseline/SHA256` | sha256 do `instr-cli.jar` anterior à change (`8880e47f…`) |
| `baseline/instr-cli.jar` | esse jar, referência da equivalência; fora do git |
| `scripts/instrument.py` | instrumenta APKs no host por `DexlibInstrumentation`, com `--stamp-handlers` e os monitores `jca_android` do smk121 |
| `scripts/analyze.py` | análise de um APK do smoke: `RVSEC-BIND` por origem, classes do app contra `handlers`, formas da gh124, `stampHits`, decisões `src=MOP`, crashes e `VerifyError` |
| `filters/<apk>.txt` | filtro de APK de cada container |
| `docker-compose.yml` | um container por APK, braço `aperv:mopd_on_llm_off`, 300 s, 1 rep, `restart: "no"` |
| `RELATORIO.md` | jars, testes, equivalência e smoke |

Fora do git (`.gitignore`): `baseline/instr-cli.jar`, `equiv/` (logs de build e de testes,
saídas do `dexcmp.py`, cópia do jar novo), `apks/` (APKs originais e instrumentados) e
`results/` (saídas das execuções, criadas pelo container como root).

## Pré-condições

- `ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk`, com `build-tools/35.0.1`
  (`dexdump`) e `platforms/android-30`.
- O `instr-cli.jar` da change em `modules/rv-instrumentation-dexlib2/lib/` (build do reator
  `rvsec` com JDK 21: `mvn clean install -o -DskipMopAgent -DskipTests`).
- Os monitores `jca_android` de `experimento-smk121/results/monitors`.
- Os APKs originais em `apks/src/` (links físicos para os de `rvsec-dataset/head_apks`), cada
  um com o seu `.apk.json` do e6-corpus ao lado do APK instrumentado (os braços MOP o exigem).
- A imagem `phtcosta/rvandroid:0.9.5`. Nenhum emulador é iniciado ou parado à mão: o
  `rv-platform` cuida disso dentro de cada container.

## Comandos

Todos rodam a partir da raiz do `rv-android/`.

**Equivalência (4.4).** Instrumentar o saucenao com os dois jars e comparar os DEX:

```bash
uv run python experimento-smk124/scripts/instrument.py experimento-smk124/baseline/instr-cli.jar \
  experimento-smk124/equiv/baseline experimento-smk124/equiv/src/com.luk.saucenao_27.apk
uv run python experimento-smk124/scripts/instrument.py modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
  experimento-smk124/equiv/new experimento-smk124/equiv/src/com.luk.saucenao_27.apk
ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk python3 experimento-smk121/scripts/dexcmp.py \
  --work-dir experimento-smk124/equiv/tmp \
  base=experimento-smk124/equiv/baseline/instrumented/com.luk.saucenao_27.apk \
  new=experimento-smk124/equiv/new/instrumented/com.luk.saucenao_27.apk
```

O `instr-cli` do wrapper não define `-Xmx`; não rode mais de uma ou duas instrumentações em
paralelo.

**Smoke (5.1–5.5).** Instrumentar os três APKs, pôr o `.apk.json` de cada um ao lado do
instrumentado e subir os containers:

```bash
uv run python experimento-smk124/scripts/instrument.py modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
  experimento-smk124/apks experimento-smk124/apks/src/*.apk
E03MINI_IMAGE=phtcosta/rvandroid:0.9.5 docker compose -f experimento-smk124/docker-compose.yml up -d
```

Depois de cada tarefa, analisar o APK:

```
analyze.py <task_dir> <apk_name> <mop.json> <instrumented.apk> <work_dir>
```

`<task_dir>` é o diretório da tarefa em `results/<container>/<container>/<apk>/` (`.logcat` e
`.trace.ndjson.gz`); `<mop.json>` é o artefato MOP derivado da execução. Os arquivos de
`results/` pertencem ao root; uma cópia legível do `.mop.json` sai por um container descartável:

```bash
docker run --rm --entrypoint cat -v <dir>:/d:ro phtcosta/rvandroid:0.9.5 /d/<arquivo>
```

O `analyze.py` reutiliza `dexidx.py` de `data/e03mini_a2/sweep_stamp/` para os fatos estáticos
do DEX. O logcat grava só a classe final do carimbo, de modo que a atribuição de uma classe à
etapa Material é inferência a partir desses fatos, não observação.
