# experimento-smk121 — verificação do carimbo de handler (gh121)

## Propósito

A change `gh121-instr-handler-stamp` (issue #121) faz o app instrumentado gravar, nos
extras do `AccessibilityNodeInfo` de cada nó clicável, a classe do handler ligado a ele
(`rvsec.click`, `rvsec.longClick`), e registrar cada mudança no logcat sob a tag
`RVSEC-BIND`. Este diretório reúne o que verifica isso fora dos testes unitários:

- **offline**, a diferença entre DEX instrumentados com e sem a opção
  (`scripts/dexcmp.py`, `scripts/dexnorm.py`): com a opção desligada, a saída é idêntica
  byte a byte à do instrumentador anterior à change (design D13); com ela ligada, toda
  diferença é uma reescrita de setter ou uma inserção de `composeNode`;
- **no dispositivo**, que um cliente `UiAutomation` de fato recebe os extras (design D14):
  `probe/StampProbe.java` lê a árvore como o APE-RV lê, navega um nível, e
  `scripts/check_delivery.py` compara o que ele leu com as linhas `RVSEC-BIND` do logcat.

## Conteúdo

| Caminho | O que é |
|---|---|
| `ref/instr-cli-pre-gh121.jar` | o `instr-cli.jar` anterior à change, referência da identidade byte a byte (D13); fora do git |
| `scripts/dexnorm.py` | normaliza a saída de `dexdump -d` e imprime o md5 do texto normalizado e os contadores do carimbo |
| `scripts/dexcmp.py` | compara os `classes*.dex` de APKs: md5 bruto, `method_ids` e md5 normalizado |
| `probe/StampProbe.java`, `probe/build_probe.sh` | a sonda que roda sob `app_process` e o script que a compila em `probe/probe.jar` |
| `scripts/run_probe.py` | registra a ferramenta `stampprobe` no `ToolRegistry` e chama o `rv-platform` |
| `scripts/check_delivery.py` | pareia os nós das capturas da sonda com as linhas `RVSEC-BIND` e decide |
| `tests/` | testes de `dexnorm.py` e de `check_delivery.py` sobre textos sintéticos |

## Pré-condições

- `ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk`, com
  `build-tools/35.0.1` (`d8`, `dexdump`), `platforms/android-30` e `platforms/android-36`.
- JDK 21 em `$HOME/.sdkman/candidates/java/21.0.12-tem` (o `build_probe.sh` o usa quando
  `JAVA_HOME` não está definido).
- O novo `instr-cli.jar` construído (grupo 8 da change) e o reator `rvsec` instalado.
- `RVSEC_HOME` definido, para a geração de monitores do 9.0.
- A sonda construída uma vez, antes do 9.5:

  ```bash
  experimento-smk121/probe/build_probe.sh
  ```

- Nenhum emulador é iniciado ou parado à mão: o `rv-platform` cuida disso no 9.4 e no 9.5.

## Comandos (grupo 9 do `tasks.md`)

Todos rodam a partir da raiz do `rv-android/`.

**9.0 — insumos das verificações offline.** Criar em `experimento-smk121/apks/` os links
(nunca cópias) para os quatro APKs originais — `com.beemdevelopment.aegis_81.apk`,
`dev.itsvic.parceltracker_10501000.apk`, `systems.sieber.droid_scep_7.apk` (em
`rvsec-dataset/jca_android/apks/`) e `apks_examples/cryptoapp.apk` — e rodar só o
pré-processamento, sem o carimbo:

```bash
uv run rv-experiment run --tools ape --apks-dir experimento-smk121/apks \
  --specification-set jca_android --instrumentation-variant dexlib2 \
  --skip-static --skip-execution --name smk121-pre --output-dir experimento-smk121/results/pre
```

Daí saem o descritor `jca_android` e os fontes dos monitores (`results/pre/monitors/`) e
os jars de runtime (`results/pre/lib_tmp/`), que os passos 9.1–9.3 reutilizam.

**9.1–9.3 — verificações offline.** Chamam `instr-cli instrument` diretamente, com o
descritor, os monitores e os jars de runtime do 9.0, e sempre com o `android.jar` e o
`d8` fixados explicitamente:

```bash
java -jar <instr-cli.jar> instrument ... \
  --android-jar $ANDROID_HOME/platforms/android-36/android.jar \
  --d8 $ANDROID_HOME/build-tools/35.0.1/d8
```

- 9.1: `parceltracker` instrumentado com `ref/instr-cli-pre-gh121.jar` e com o jar novo
  sem a opção (e sem `RVSEC_STAMP_HANDLERS`); todo `classes*.dex` deve sair idêntico
  (md5 bruto). Depois, um APK com `--stamp-handlers` e o seguinte sem a opção no mesmo
  `--monitor-src-dir`/`--work-dir`: o DEX de monitores do segundo não tem `Lmop/RvsecStamp`.
- 9.2: `aegis` com e sem a opção, comparado pelo md5 normalizado.
- 9.3: `cryptoapp` com `RVSEC_STAMP_HANDLERS=true` sem a opção (há chaves `stamp*` em
  `weaveCounts`) e com `--no-stamp-handlers` (não há).

A comparação usa um diretório de trabalho dado na linha de comando, para os DEX
temporários (nunca ao lado do script nem em `/tmp`):

```bash
python3 experimento-smk121/scripts/dexcmp.py --work-dir experimento-smk121/results/dexwork \
  off=<apk instrumentado A> on=<apk instrumentado B>
```

Com dois rótulos, a saída termina com uma linha `cmp` por DEX (`raw=same|diff`,
`norm=same|diff`); cada linha por DEX traz os contadores `stamp_static`,
`setter_virtual`, `compose_inserted`, `setter_super` e `insns_lines`.

**9.4 — execução no dispositivo pelo pipeline**, em segundo plano:

```bash
uv run rv-experiment run --tools ape --apks-dir experimento-smk121/apks \
  --specification-set jca_android --instrumentation-variant dexlib2 --stamp-handlers \
  --skip-static --timeouts 120 --repetitions 1 --logcat-diagnostics --no-window \
  --name smk121 --output-dir experimento-smk121/results
```

**9.5 — entrega ao cliente `UiAutomation`**, em segundo plano, sobre os APKs carimbados
do 9.4:

```bash
uv run python experimento-smk121/scripts/run_probe.py run --tools stampprobe \
  --apks-dir experimento-smk121/results/instrumented_apks \
  --results-dir experimento-smk121/results/probe --timeouts 60 --repetitions 1 --no-window
uv run python experimento-smk121/scripts/check_delivery.py experimento-smk121/results/probe
```

O `run_probe.py` repassa seus argumentos ao `rv-platform`; a ferramenta `stampprobe` é a
única cliente `UiAutomation` da tarefa (nenhum APE roda junto). O `check_delivery.py`
sai com 0 quando nenhum nó pareado diverge e há ao menos um nó View e um nó Compose
pareados no conjunto; sai com 1 caso contrário. As regras de pareamento estão na
docstring do script.

## Formato da captura da sonda

A sonda escreve em stdout, separado por tabulações, uma linha `APP` e uma captura por
passo:

```
APP   <pacote>  <atividade>
STEP  <índice>  <hora>  <pacote em primeiro plano>  <ação>  <classe>  <view-id>  <bounds>
NODE  <classe>  <view-id>  <bounds>  <rvsec.click>  <rvsec.longClick>
```

`<ação>` é `start` (primeira tela), `click` (o nó clicado da primeira tela) ou `missing`
(o nó não foi encontrado na tela em que a sonda estava; nada foi clicado). Valores
ausentes são `-`. A hora é o relógio do dispositivo no formato do `threadtime` do logcat
(`MM-dd HH:mm:ss.SSS`), tomada depois da leitura da árvore, porque o Compose escreve suas
linhas `RVSEC-BIND` durante essa leitura. Os bounds seguem `Rect.toShortString()`.

## Onde ficam os resultados

Tudo vai para `experimento-smk121/results/`:

- `results/pre/` — pré-processamento do 9.0;
- `results/dexwork/` — DEX temporários do `dexcmp.py` (apagados a cada uso);
- `results/` (raiz) — a execução do 9.4, inclusive `instrumented_apks/`;
- `results/probe/<apk>/` — a execução do 9.5: para cada tarefa, o `.logcat`, o `.trace`
  (stderr da sonda) e o `.probe.txt` (as capturas), lado a lado.

O relatório dos resultados vai para `RELATORIO.md` (tarefa 9.6).

`results/` e `ref/` ficam fora do git (ver `.gitignore`), assim como os `.class` e o
`probe.jar` gerados pelo `build_probe.sh`.

## Testes

```bash
uv run pytest experimento-smk121/tests --import-mode=importlib -o "addopts="
```
