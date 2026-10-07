# smk119 — relatório da corrida de 07/10/2026

Smoke da change `gh119-rvsec-occ-emulator-memory` (design D10). O objetivo era medir, sob
exploração real, quanto a linha `RVSEC-OCC` escreve, se alguma linha se perde entre o
coletor e o arquivo capturado e onde as linhas caem na linha do tempo da exploração.

## Resumo

- As cinco tarefas completaram, e todo `.logcat` tem linhas `RVSEC-OCC`.
- Não houve perda medida. As 1 005 linhas `RVSEC` das cinco corridas têm, cada uma, a
  sua `RVSEC-OCC` com `n=1`, e nenhuma `n=1` ficou sem a sua `RVSEC`. Nenhuma linha
  `RVSEC-OCC` saiu fora do formato de nove campos.
- O volume é pequeno. São de 0,59 a 3,28 linhas `RVSEC-OCC` por segundo em média, com
  pico de 25 a 56 por segundo, e elas são de 2,3 % a 16,1 % das linhas capturadas. O pico
  de todas as linhas capturadas ficou entre 1 031 e 1 322 por segundo, contra 6 673 no E6.
- O contador mostra repetições que a linha `RVSEC` sozinha não mostra. No maskan.chat e no
  bitbanana, uma identidade do `CipherSpec` em `PrfAesCmac.compute` chega a `n` = 265 e 277,
  com uma única linha `RVSEC` por processo.

## Como a corrida foi feita

A corrida usou o AVD `RVSec` do host, ligado e desligado pelo `rv-platform`, com o braço
`aperv:mop_off_llm_off`, 600 s, uma repetição e captura diagnóstica ligada. Ninguém mexeu
no emulador à mão.

Foram dois passos.

1. **Instrumentação a partir dos originais.** O `rv-experiment` gerou os monitores do
   `jca_android` (47 especificações) e instrumentou com `dexlib2` os cinco originais de
   `apks/`. O jar `rvsec-logger-logcat-0.9.5-SNAPSHOT.jar` foi instalado pelo reator às
   12:35 e copiado para `results/lib_tmp/`. O DEX de cada um dos cinco APKs instrumentados
   contém a string `RVSEC-OCC`.
2. **Execução com os artefatos estáticos do E6.** O braço `mop_off_llm_off` precisa do
   `.apk.json` de cada APK, porque mantém o documento MOP e zera os pesos (INV-APV-29); uma
   tarefa sem ele falha ao armar o braço. Por decisão do pesquisador, não se rodou o GATOR.
   Os cinco `.apk.json` vieram do E6, de
   `/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2/`
   (de 02/09/2026), e foram copiados ao lado dos APKs instrumentados, com o sha256 em
   `results/instrumented_apks/e6_apk_json.sha256`. O comando foi:

   ```bash
   uv run rv-experiment run --tools aperv:mop_off_llm_off --apks-dir experimento-smk119/results/instrumented_apks --specification-set jca_android --instrumentation-variant dexlib2 --skip-monitors --skip-instrument --skip-static --timeouts 600 --repetitions 1 --logcat-diagnostics --no-window --name smk119 --output-dir experimento-smk119/results
   ```

   As tarefas rodaram das 13:24 às 14:19.

A primeira tentativa, com `--skip-static` e sem os `.apk.json`, instrumentou os APKs mas
teve todas as tarefas abortadas ao armar o braço. Ela fica em `tentativa1_sem_static/`,
fora do git, e não entra em nenhum número deste relatório.

A medição é a do `scripts/measure_occ.py`, cuja saída completa está em
`results/measure_occ.json`.

## Resultados por corrida

### Volume

| APK | Linhas `RVSEC-OCC` | Média/s | Pico/s (janela de 1 s) | Fração das linhas capturadas | `RVSEC-COV` | Pico de todas as linhas/s |
|---|---|---|---|---|---|---|
| maskan.chat_90 | 1 949 | 3,28 | 56 | 16,1 % (1 949 / 12 109) | 9 231 | 1 031 |
| bitbanana_79 | 539 | 1,14 | 38 | 3,7 % (539 / 14 609) | 13 050 | 1 187 |
| deku_83 | 324 | 0,59 | 55 | 2,7 % (324 / 12 110) | 10 276 | 1 183 |
| passportreader_22 | 677 | 1,14 | 48 | 3,8 % (677 / 17 649) | 15 734 | 1 191 |
| habdroid_589 | 803 | 1,35 | 25 | 2,3 % (803 / 34 244) | 31 823 | 1 322 |

A média é calculada no intervalo entre a primeira e a última linha `RVSEC-OCC`, de 473 a
595 s. Com o prefixo do logcat, uma linha `RVSEC-OCC` ocupa de 185 a 225 bytes em média.
O maior volume, no maskan.chat, soma 392 KB em 600 s.

### Contador `n`

| APK | Identidades distintas | `n` máximo | Identidade com o maior `n` |
|---|---|---|---|
| maskan.chat_90 | 31 | 265 | `CipherSpec`, `PrfAesCmac.compute` (`PrfAesCmac.java:103`), `CIPHER-ORDER-03`, `f2` |
| bitbanana_79 | 33 | 277 | a mesma identidade do maskan.chat (Tink) |
| deku_83 | 25 | 16 | `CipherSpec`, `PrfAesCmac.compute` (`PrfAesCmac.java:98`), `CIPHER-ORDER-03`, `f2` |
| passportreader_22 | 40 | 61 | `IvParameterSpecSpec`, `zzbbe.zzb` (play-services-ads), `IVPARAMETERSPEC-NOBS-00`, `c1` |
| habdroid_589 | 35 | 69 | `MessageDigestSpec`, `okio.ByteString.digest$okio` (`ByteString.kt:82`), `MESSAGEDIGEST-ALG-02`, `g4` |

O último `n` de cada identidade é um limite inferior. Ocorrências depois da última linha
escrita são contadas em memória e não chegam ao log.

### Pareamento `RVSEC` × `RVSEC-OCC n=1` (perda)

| APK | Linhas `RVSEC` | Linhas `n=1` | Pares | `RVSEC` sem `n=1` | `n=1` sem `RVSEC` | Linhas fora do formato | Processos do app |
|---|---|---|---|---|---|---|---|
| maskan.chat_90 | 136 | 136 | 136 | 0 | 0 | 0 | 5 |
| bitbanana_79 | 99 | 99 | 99 | 0 | 0 | 0 | 4 |
| deku_83 | 153 | 153 | 153 | 0 | 0 | 0 | 7 |
| passportreader_22 | 305 | 305 | 305 | 0 | 0 | 0 | 8 |
| habdroid_589 | 312 | 312 | 312 | 0 | 0 | 0 | 17 |

Há mais linhas `RVSEC` do que identidades distintas porque o app reiniciou durante a
exploração; a última coluna conta os processos distintos que escreveram essas linhas. Cada
processo novo começa com o coletor vazio e escreve de novo a `RVSEC` e a `RVSEC-OCC` com
`n=1` de cada identidade que atinge. Por isso o pareamento é feito por contagem em cada
chave, não por identidade única.

### Posição na linha do tempo

| APK | Antes do primeiro passo | Num passo | Depois do último passo | Sem alinhamento | Passos com alguma `RVSEC-OCC` |
|---|---|---|---|---|---|
| maskan.chat_90 | 105 (5,4 %) | 1 844 | 0 | 0 | 98 de 683 (14,3 %) |
| bitbanana_79 | 47 (8,7 %) | 492 | 0 | 0 | 38 de 771 (4,9 %) |
| deku_83 | 39 (12,0 %) | 285 | 0 | 0 | 6 de 1 261 (0,5 %) |
| passportreader_22 | 65 (9,6 %) | 612 | 0 | 0 | 57 de 841 (6,8 %) |
| habdroid_589 | 13 (1,6 %) | 790 | 0 | 0 | 70 de 640 (10,9 %) |

As linhas antes do primeiro passo são da inicialização do app, antes do primeiro heartbeat
`ApeRvHb`. Todas as outras caem num passo da exploração.

## Condições e limites

- **A comparação com o E6 é aproximada.** A corrida usou o AVD do host, com 4096 MB de RAM,
  8192 MB de partição de dados e 2 núcleos. O AVD do container do E6 tem 1536 MB, 800 MB e
  4 núcleos. A pressão sobre o buffer do logcat e a velocidade da exploração não são as
  mesmas, então os 1 031 a 1 322 por segundo daqui, ao lado dos 6 673 do E6, indicam folga
  e não medem a mesma condição.
- **A correção de memória e partição não foi exercitada.** Ela muda o AVD do container, e o
  AVD do host já roda com 4096 MB / 8192 MB. O efeito dela só aparece na primeira campanha
  com uma imagem refeita.
- **Os artefatos estáticos vêm do E6.** Os `.apk.json` são da análise do E6, não de uma
  análise destes APKs re-instrumentados. O código do app é o mesmo. O braço zera os pesos de
  MOP, e o volume da linha de ocorrência depende do código que a exploração executa.
- **São cinco APKs com uma repetição cada.** Eles foram escolhidos por terem mais linhas
  `RVSEC` no E6, o que os põe entre os que mais escrevem. A corrida mede o fluxo
  `RVSEC-OCC`; não estima nenhuma quantidade do estudo.
