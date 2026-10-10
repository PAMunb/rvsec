# gh125 — evidências do apply (10/10/2026)

Change `gh125-static-json-compact` (#125). Todas as medições abaixo foram feitas nesta sessão, no host; os documentos E6 foram lidos sem alteração em `rvsec-study03-replication-package/data/raw/e6-static-analysis/final/`.

## 1. Baseline (tarefas 0.1, 0.2)

Jars de `lib/gator/` copiados para `baseline/` antes de qualquer build:

| jar | sha256 |
|---|---|
| `rvsec-analysis-client.jar` (baseline) | `6f9fa9863b32c4422a8912aafafe7d580015e561c0a4f99b87542473b76c88b4` |
| `rvsec-gator.jar` (baseline) | `134f628f6eac8eee6162b47301d1665cfbb57927e496ec8888c9d0a2d37e8361` |
| `rvsec-analysis-client.jar` (gh125) | `e65eb662093b30a0017bceda5d44126b0b15344c1d30e5d7bb82259a700d5ca7` |
| `rvsec-gator.jar` (gh125) | `024ccdfb77f90afeaaa69de018c3b57aacee180cb5d3c538f819f959533cf2c7` |

`rv-static-analysis analyze --apk apks_examples/cryptoapp.apk` com os jars da baseline: `baseline/cryptoapp.apk.json`, 80 638 B, sha256 `b6e6fc67…`. Uma segunda execução (`baseline-rerun/`) deu o mesmo sha256.

## 2. GATOR no cryptoapp com o jar da gh125 (tarefa 4.5)

| documento | bytes | sha256 |
|---|---|---|
| `baseline/` (jar antigo) | 80 638 | `b6e6fc67…` |
| `full/` (`--full-output`) | 80 638 | `4e5c485b…` |
| `full-rerun/` (`--full-output`, execução isolada) | 80 638 | `4e5c485b…` |
| `compact/` (padrão) | 51 258 | `3fc518d0…` |
| `converted/` (`rv-static-analysis compact full/…`) | 51 258 | `3fc518d0…` |

**(a) full × baseline (INV-ANA-86).** O documento é idêntico byte a byte da primeira até a última posição antes de `"transitions"` (68 750 bytes). Em `transitions`, as 35 arestas são as mesmas, com os mesmos ids de nó, mas em outra ordem (`compare_docs.py`: todos os demais membros iguais; `transitions` igual como multiconjunto). Cada jar é determinístico consigo mesmo: duas execuções do jar antigo dão `b6e6fc67…` e duas do jar novo dão `4e5c485b…`. A ordem de `transitions` sai da iteração sobre as arestas do WTG, que depende de identity hash. Isso é o mesmo fenômeno que INV-ANA-79 trata ao comparar ids de nó por conteúdo, e o design D4 admite essa comparação. O código do modo full não toca nessa seção.

**(b) compacto × conversor (INV-ANA-87).** Idênticos byte a byte.

**(c) Forma do compacto.** Nenhum caractere de quebra de linha; membros na ordem `package, mainActivity, codePackage, codePackageSource, class_defs_under_key, distancePairs, distanceTargets, components, reachability, windows, transitions, complete`; `distancePairs = {"weighedMax": 3, "k": 3}`. O log registra `[RvsecAnalysisClient] Output mode: compact` / `full`. A linha de comando só contém `-clientParam fullOutput=true` na execução com `--full-output`.

## 3. Equivalência para os consumidores (tarefas 4.1, 4.2, 4.4)

O `*.mop.json` grava em `source.digest` o sha256 do arquivo de onde foi derivado. Como full e compacto têm bytes diferentes, esse campo necessariamente difere. Por isso, as comparações abaixo passam a mesma proveniência a `derive()` dos dois lados e comparam todo o resto byte a byte.

| documento | derive (full × compacto) | `StaticAnalysisData` | métodos |
|---|---|---|---|
| fixture `cryptoapp.apk.json` | idêntico (teste no aperv-tool) | igual (teste no rv-static-analysis) | — |
| `org.wikipedia_50595` | idêntico, 796 336 B | igual | 39 950 |
| `at.techbee.jtx_216000015` (sem `complete`) | idêntico, 470 017 B | igual | 22 934 |
| `com.apps.adrcotfas.goodtime_348` | idêntico, 106 803 B | igual | 10 036 |
| `org.fossify.calendar_20` | idêntico, 789 139 B | igual | 5 161 |
| `com.js.nowakelock_87` (sem WTG, sem `complete`) | idêntico, 69 080 B | igual | 6 625 |

Script: `check_equivalence.py` (leitura em streaming; nenhum documento passa por `json.load`). Logs em `e6/<apk>.check.log`.

`summary.csv` e `coverage.csv` saem idênticos byte a byte a partir do documento full e do compacto: `test_csv_identical_from_full_and_compact_documents` (rv-platform).

## 4. Conversor nos documentos E6 (tarefas 4.2, 4.3)

| documento | entrada | saída | saída/entrada | tempo | pico RSS |
|---|---|---|---|---|---|
| `eu.darken.sdmse_10705000` (sozinho) | 9 335 267 701 | 54 621 271 | 0,59 % | 3 min 06 s | 674 MiB |
| `org.wikipedia_50595` | 2 159 952 697 | 22 919 681 | 1,06 % | 44 s | 300 MiB |
| `at.techbee.jtx_216000015` | 2 017 546 684 | 11 342 811 | 0,56 % | 41 s | 158 MiB |
| `org.fossify.calendar_20` | 406 431 973 | 268 908 835 | 66,2 % | 15 s | 1 956 MiB |
| `com.apps.adrcotfas.goodtime_348` | 161 122 499 | 3 707 929 | 2,30 % | 3,9 s | 88 MiB |
| `com.js.nowakelock_87` | 47 757 158 | 2 222 733 | 4,65 % | 2,7 s | 79 MiB |

Os cinco documentos menores foram convertidos em paralelo; o sdmse rodou sozinho. Os tamanhos de saída do sdmse, da wikipedia, do jtx e do goodtime batem com a medição do planejamento: 54,6, 22,9, 11,3 e 3,6 MB. O calendar continua grande por causa da seção `windows`, que está fora do escopo da change. Por isso ele também tem o maior pico de memória: o conversor guarda o documento reduzido inteiro (design D6).

## 5. Testes

- GATOR, a partir da raiz do reator com JDK 21: `mvn -o install -DskipMopAgent -pl rvsec/rvsec-android/rvsec-gator/client -am` passa com os testes de unidade (client: 256, 0 falhas, 0 pulados), e `mvn -o verify -DskipITs=false -pl …/client` passa com 33 ITs. O comando do hand-off, `-pl rvsec/rvsec-android/rvsec-gator -am`, constrói só o pom agregador: termina em 0,8 s sem rodar nenhum teste.
- rv-static-analysis: 244 passados.
- Paridade (`test_json_keys.py` + `test_distance_pair_constants.py`): 5 passados.
- aperv-tool: 760 passados e 25 pulados antes do teste da 4.1. O resultado final está na seção 6 de `tasks.md`.
