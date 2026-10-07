# smk119 — volume, perda e posição da linha `RVSEC-OCC`

Smoke da change `gh119-rvsec-occ-emulator-memory` (design D10). A change faz o coletor
do logcat escrever, além da linha `RVSEC` da primeira ocorrência de cada identidade,
uma linha `RVSEC-OCC` por ocorrência, com no máximo uma linha por identidade a cada
100 ms e um contador `n` que deixa visível o que o limite suprimiu. Os testes de
unidade dizem que a linha tem o formato certo; não dizem quanto ela custa nem se
chega inteira ao arquivo quando um app real é explorado. Este smoke mede isso em
cinco APKs:

1. linhas `RVSEC-OCC` por segundo: média ao longo da corrida e pico em janelas de 1 s;
2. o maior `n` por identidade e as identidades com maior `n`;
3. o pareamento: toda linha `RVSEC` precisa de uma `RVSEC-OCC` com `n=1` na mesma
   chave, e toda `n=1` precisa da sua `RVSEC`. Linha sem par, de qualquer lado, é
   perda medida;
4. o pico de todas as linhas capturadas por segundo, qualquer tag (no E6 foi 6 673);
5. a posição das linhas `RVSEC-OCC` na linha do tempo da exploração: antes do
   primeiro passo, num passo, depois do último ou sem alinhamento (logcat sem
   heartbeat `ApeRvHb`).

## Entradas

`apks/` tem links simbólicos (nunca cópias) para cinco originais de
`rvsec-dataset/jca_android/apks/`: `com.tananaev.passportreader_22`,
`app.michaelwuensch.bitbanana_79`, `com.afkanerd.deku_83`, `org.openhab.habdroid_589` e
`app.maskan.chat_90`. A geração de monitores e a instrumentação `dexlib2` partem desses
originais, então os APKs instrumentados carregam o coletor novo.

O braço é `aperv:mop_off_llm_off`. Ele não precisa de SGLang, mas precisa do artefato de
análise estática de cada APK: o braço sem MOP mantém o documento MOP e zera os pesos, para
que a navegação por WTG e por fronteira continue viva (INV-APV-29), e uma tarefa sem
`<apk>.apk.json` falha ao armar o braço. Em vez de rodar o GATOR, usam-se os `.apk.json`
do E6, de `/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2/`
(de 02/09/2026), copiados ao lado dos APKs instrumentados; o sha256 de cada um fica em
`results/instrumented_apks/e6_apk_json.sha256`. Esses artefatos vêm da análise do E6, não
de uma análise destes APKs re-instrumentados; o código do app é o mesmo.

O volume da linha de ocorrência depende do código que a exploração executa, não da
orientação por MOP.

## Pré-condições

- Os grupos 1 e 2 da gh119 estão feitos:
  - o `install` do reator (grupo 1) pôs o jar novo do `rvsec-logger-logcat` no
    repositório Maven local, que é de onde `mvn dependency:copy-dependencies` o lê;
  - o grupo 2 incluiu `RVSEC-OCC` na allowlist de captura do logcat. Sem isso o
    `adb logcat -s` descarta a tag no dispositivo e o arquivo sai sem nenhuma linha.
- `RVSEC_HOME` aponta para o reator (`echo $RVSEC_HOME`).
- O emulador do host está livre: nenhum outro experimento o usa. O `rv-platform`
  sobe e derruba o AVD `RVSec` sozinho; você não inicia, não para e não mexe no
  emulador à mão, nem com `emulator` nem com `adb emu`.

## Execução

A partir de `rv-android/`, em segundo plano, em dois passos.

1. Gerar os monitores e instrumentar os originais de `apks/` com `dexlib2` em
   `results/instrumented_apks/`. Cerca de 15 minutos para os cinco.
2. Copiar os cinco `.apk.json` do E6 para `results/instrumented_apks/`, registrar o
   sha256 deles e executar:

```bash
uv run rv-experiment run --tools aperv:mop_off_llm_off --apks-dir experimento-smk119/results/instrumented_apks --specification-set jca_android --instrumentation-variant dexlib2 --skip-monitors --skip-instrument --skip-static --timeouts 600 --repetitions 1 --logcat-diagnostics --no-window --name smk119 --output-dir experimento-smk119/results
```

O segundo passo leva cerca de 55 minutos: cinco tarefas de 600 s, mais instalação e
boot do emulador.

Ao terminar, confira que as cinco tarefas completaram e que todo `.logcat` tem linhas
`RVSEC-OCC`. Um arquivo sem nenhuma indica APK com o coletor antigo ou captura que não
admitiu a tag; nesse caso, pare e diagnostique antes de medir.

## Medição

```bash
uv run python experimento-smk119/scripts/measure_occ.py experimento-smk119/results
```

O script é offline e só lê as entradas. Percorre `results/` atrás de cada `.logcat` (e
do `.trace` irmão, de mesmo nome, quando existe), imprime uma tabela por corrida e
grava o detalhe em `experimento-smk119/results/measure_occ.json`. As colunas da
tabela:

| Coluna | Significado |
|---|---|
| `occ`, `mean/s`, `peak/s` | linhas `RVSEC-OCC`; média por segundo no intervalo entre a primeira e a última; pico em janelas de 1 s |
| `max n` | maior `n` visto, sobre todas as identidades |
| `paired`, `lostR`, `lostO` | pares `RVSEC` × `n=1`; `RVSEC` sem `n=1`; `n=1` sem `RVSEC` |
| `malf` | linhas `RVSEC-OCC` que não têm nove campos com `n` inteiro (contadas, nunca descartadas em silêncio) |
| `all pk/s` | pico de todas as linhas capturadas por segundo |
| `pre`, `step`, `post`, `unal` | posição das linhas `RVSEC-OCC` em relação aos heartbeats |

A chave do pareamento tem oito campos: os seis primeiros da linha `RVSEC` mais o `code`
e o `ev` do envelope `v=1 ` da mensagem, extraídos com a mesma regra do coletor
(`UNSPECIFIED` quando a mensagem não tem envelope). A posição usa o mesmo leitor de
heartbeat e a mesma regra (`place_on_timeline`) de `clock_logcat_join` e `step_bundle`.

Os testes do script rodam com:

```bash
uv run pytest experimento-smk119/tests --import-mode=importlib -o "addopts=" -q
```

## O que fica fora do git

`results/` (logcats, traces, APKs instrumentados, monitores, os `.apk.json` do E6 e o
`measure_occ.json`), `apks/` (links com caminho absoluto deste host) e
`tentativa1_sem_static/` ficam fora do git pelo `.gitignore` deste diretório.
Versionam-se o script, os testes, este README e o relatório da corrida.

O `measure_occ.py` grava o relatório sempre e sai com código 1 quando alguma linha
`RVSEC-OCC` ou `RVSEC` está malformada ou ilegível.

## Condições e limites

O smoke roda no AVD do host, com 4096 MB de RAM, 8192 MB de partição de dados e
2 núcleos. O AVD do container do E6 tinha 1536 MB, 800 MB e 4 núcleos. A pressão sobre
o buffer do logcat e a velocidade da exploração não são as mesmas, então qualquer
número posto ao lado do E6 é uma aproximação, não uma comparação exata.

A correção de memória e de partição do emulador, que também faz parte da gh119, não é
exercitada aqui. O que ela muda é o AVD do container, que sai de 1536 MB / 800 MB para
4096 MB / 8192 MB; o AVD do host já roda com esses valores, então esta corrida não mostra
o efeito dessa passagem.
