# gh-tbd-gator-full-minified-horizon — evidências do apply (11/11/2026)

Change `gh-tbd-gator-full-minified-horizon` (sem issue), worktree `worktrees-gator/distmax`, branch `wip/gator-distmax` a partir de `99572bc0`. Todas as medições foram feitas nesta sessão, no host, com o JDK 21.0.12 no build e o `java` do host para o GATOR. Nenhuma execução em aparelho faz parte da change.

Configuração das análises dos grupos 0 e 5 (`scripts/run_gator.sh`, copiado de `experimento-gtpaths/` com `WT` apontando para esta worktree): specs `jca_android`, SPARK, `--cg-delegation true`, heap 12g, `RV_STRIP_BUILD_TYPE_SUFFIX=true`, `--force`. APKs: `apks_examples/cryptoapp.apk` e `org.musicbrainz.picard.barcodescanner_38.apk` do `e6-corpus` do replication package (leitura).

## 1. Jars

| | `rvsec-analysis-client.jar` | `rvsec-gator.jar` | árvore do gator |
|---|---|---|---|
| baseline (árvore principal, build de 02/11 15:15, bump 0.9.7) | `dfb17c3d…` | `740de467…` | `1f252fe0…` (= `b4f7dd67` = `HEAD`) |
| novo (tarefa 4.1) | `b4493670…` | `e104db86…` | `604d6117…` (árvore de trabalho, índice temporário) |

Hashes completos em `baseline/SHA256` e `new/SHA256`. Jars do Maven não são reprodutíveis byte a byte; a árvore identifica o código.

Build (4.1), da raiz do reator da worktree, `-o`, sem `-DskipTests`: BUILD SUCCESS, 311 testes unitários do client e 31 do sootandroid, mais os dos módulos do `-am`, todos verdes (`new/build-install.log`). As 4 linhas `Tests are skipped.` são do failsafe (testes de integração) do rv-monitor e do client, cujo pom tem `skipITs=true`; o segundo comando, `verify -DskipITs=false`, rodou as 33 ITs do client, verdes (`RvsecAnalysisClientIT` 14, `GenericSubtypeMatchingIT` 8, `BaselineComparisonIT` 11; `new/build-verify-its.log`).

## 2. Baseline (grupo 0)

Tempo de parede com o jar do baseline, 4 análises em paralelo: cryptoapp 43,5 s (compacto) e 43,4 s (completo); barcodescanner 262,3 s e 267,6 s. O documento completo do barcodescanner tem 32 pares em d = 10, como o design previa.

O fixture `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` não sai do `run_gator.sh`: ele é gerado pela receita do script do gate (`scripts/check_signature_file_subset.py`): `./gator` com as specs `jca`, SPARK padrão, sem `cgDelegation` e sem `codePackage`, modo completo. A tarefa 5.1 pedia comparar o documento novo do cryptoapp com o fixture, o que só faz sentido com a mesma receita; por isso `scripts/run_fixture_recipe.sh` reproduz essa receita. Com o jar do baseline ela dá o conteúdo do fixture atual (mesmos membros, mesma ordem, valores iguais; `transitions` com as mesmas 35 arestas em outra ordem). O código do gator não mudou desde o jar do fixture (`434e8614…`, de `ce820929`): depois disso só entraram poms e um teste.

## 3. Checagens de ponta a ponta (grupo 5)

Novas análises: 11 execuções em até 6 JVMs de 12g (72 GB). Com 6 em paralelo o barcodescanner levou 556–603 s; o cryptoapp, 40–44 s. Resultados por checagem em `new/checks/`.

**5.1 — modo completo sem espaços, mesmo conteúdo (INV-ANA-86).** Nenhum dos documentos novos tem `\n`. Comparados com o baseline por `scripts/check_docs.py same` (mesma lógica do `experimento-gh125/compare_docs.py`, mais a contagem de quebras de linha): mesmos membros na mesma ordem, cada membro igual depois do parse, `transitions` igual como multiconjunto.

| documento | antes (bytes, linhas) | depois (bytes) | proporção |
|---|---|---|---|
| cryptoapp, `jca_android` | 79 823, 2 678 | 50 794 | 63,6 % |
| barcodescanner, `jca_android` | 402 506, 11 159 | 279 021 | 69,3 % |
| cryptoapp, receita do fixture (`jca`) | 80 709, 2 718 | 51 260 | 63,5 % |

O documento novo da receita do fixture também tem o conteúdo do fixture atual.

**5.2 — compacto sem parâmetro (INV-ANA-101).** Mesmo tamanho que o baseline (50 784 e 278 526 bytes), conteúdo igual; `cmp` difere só porque `transitions` muda de ordem (identity hash).

**5.3 — `--dist-max 10`.** Nos dois modos e nos dois APKs, o documento é o sem parâmetro mais o membro `distMax: 10`, logo depois de `class_defs_under_key` (antes de `distancePairs` no compacto, de `distanceTargets` no completo).

**5.4 — horizonte 15 no barcodescanner, e o conversor.** Ordem dos membros: `…class_defs_under_key, distMax, distanceTargets…` no completo e `…class_defs_under_key, distMax, distancePairs, distanceTargets…` no compacto. Pares por distância no documento completo:

| d | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sem parâmetro | 5 | 14 | 10 | 20 | 16 | 22 | 28 | 31 | 34 | 29 | 32 | – | – | – | – | – |
| `distMax=15` | 5 | 14 | 10 | 20 | 16 | 22 | 28 | 31 | 34 | 29 | 32 | 22 | 13 | 21 | 25 | 14 |

Até d = 10 os pares são os mesmos; o horizonte 15 acrescenta 95 pares (d de 11 a 15) e leva os métodos com pares de 53 para 69 (de 5 alvos). `rv-static-analysis compact` sobre o completo com `distMax=15` sai com 0 e gera o mesmo conteúdo do compacto que o GATOR escreveu com `distMax=15` (279 195 bytes os dois; só a ordem de `transitions` difere, porque são duas execuções do GATOR). Duas conversões do mesmo arquivo são idênticas byte a byte.

**5.5 — horizonte inválido (INV-ANA-100).**
- `rv-static-analysis analyze --dist-max 0`, `ten` e `-1`, e `batch --dist-max 0`: status 2, mensagem do argparse nomeando `--dist-max` e o valor, em menos de 1 s, sem diretório de saída e sem GATOR (`new/invalid/cli.txt`).
- JVM do GATOR chamada direto (comando que o lançador monta, `scripts/run_invalid_jvm.sh`) com `distMax=0` e `distMax=ten`: status 1, `IllegalStateException: distMax must be an integer >= 1, got '0'` (e `'ten'`) lançada de `RvsecAnalysisClient.parseDistMax` no início do `run`, nenhum documento, ~28 s (o tempo de carregar o APK e montar o grafo de chamadas).
- O mesmo pelo lançador Python `lib/gator/gator` (o caminho que o `get_tool_command` usa): status **0**, a mesma exceção no log, nenhum documento. O lançador ignora o status da JVM em qualquer falha (`call(cmd, …)` sem checar o retorno; só o timeout vira `-50`). É comportamento anterior a esta change. Pelo `rv-static-analysis`, a ausência do documento já vira `StaticAnalysisException("GATOR did not produce output JSON…")`.

**5.6 — reaproveitamento por horizonte (INV-ANA-102),** numa cópia do documento completo novo do cryptoapp (sem `distMax`), `analyze` sem `--force` (`new/reuse/`):

| execução | tempo | resultado |
|---|---|---|
| sem horizonte | 0,5 s | "Analysis result already exists, skipping"; nenhum GATOR; arquivo intacto |
| `--dist-max 12` | 33,8 s | "Regenerating …: it was computed with distance horizon 10 and this run asks for horizon 12. …"; GATOR rodou; documento novo com `distMax: 12` |
| `--dist-max 12` de novo | 0,6 s | reaproveitado; nenhum GATOR |

## 4. Fixture e suítes (grupo 6)

O fixture do cryptoapp foi regenerado com o jar novo pela receita (é o `new/fixture-recipe/cryptoapp.apk.json`): sha256 `a978237d…6067d546`, 51 260 bytes, sem `\n`. As contagens do MANIFEST não mudam (16 classes, 106 métodos, 61 reachable, 39 reachesTarget, 23 directly, 5 janelas, 35 transições, 51 widgets, 4 com hint, 11 com texto, complete). `baselines/MANIFEST.json` recebeu a data e o sha do jar novo; a cópia do aperv-tool e o sha256 do seu README acompanham.

Um teste fixava o leiaute indentado do fixture completo: `tests/test_compact_equivalence.py::test_fixture_is_a_full_mode_document` procurava `'\n  "distanceTargets": ['`. Passou a reconhecer o modo pelo conteúdo (sem `distancePairs`, com `distanceTargets`, sem `\n`).

Suítes, com `--import-mode=importlib -o "addopts="`:
- `tests/parity` inteira, com `RVSEC_HOME` na worktree: 183 passaram, 28 pulados, 4 min 29 s. Os pulos são de entradas ausentes ao lado da worktree (o `RVSec-replication-package` com as regras do especialista, o checkout do `rvsec-dataset`, `results/gh51_e2e_test`, os resultados da comp162), não de GATOR. Os quatro gates que rodam o GATOR (`test_reachability_parity`, `test_baseline_freshness`, `test_sentinel_emission`, `test_signature_file_subset`) rodaram: 11 de 11.
- rv-static-analysis 307; rv-android-core 1 154; rv-tools 464; aperv-tool 878 passaram e 49 pulados (sem o tier de migração).

## 5. Checagens offline do aperv-tool (grupo 7)

**7.1 — código antigo × novo.** `scripts/check_port_7_1.py` carrega `pin/old_derive_mop_artifact.py` e `pin/old_tool.py` (de `git show 99572bc0:`) ao lado dos módulos novos (`pin/check_7_1.txt`):
- `derive()` antigo e novo no corte 3 serializam os mesmos bytes nos 5 documentos: o fixture anterior (`pin/cryptoapp.apk.json.99572bc0`), o fixture novo, o completo do barcodescanner da 5.1 e os compactos do E6 de `org.musicbrainz.picard.barcodescanner_38` e `com.password.monitor_102`;
- as 8 variantes de `get_variants()` têm os mesmos nomes, e o `_push_properties` antigo e o novo escrevem o mesmo `ape.properties` em cada uma, com e sem a linha do artefato. Nenhuma variante tem escada.

**7.2 — pareamento com o jar.** Tier de migração com `APE_REPO` no checkout do `ape`, em `master` = `a0fb5c16` antes e depois da execução (`migration/tier.log`): 48 passaram, 9 falharam. As duas falhas de `mop_weight_d1..d3` sumiram (a varredura do mapeamento passa, 4 de 4). As 9 são exatamente as registradas em 11/11 antes da change:
- 7 de `APE_FIXES`: o bloco do jar tem `ape.apeFixes` a mais (`test_the_full_cell_is_the_union_of_the_four_blocks`, 4 × `test_the_fixture_carries_the_contracts_features`, `test_each_cell_is_the_union_of_its_group_blocks`, `test_the_cell_sizes`);
- 1 `KeyError: 'ape.llmPercentageNoSubstrate'` (`test_types_and_defaults_are_read_not_guessed`);
- 1 tamanho do vocabulário, 123 ≠ 125 (`test_accepted_vocabulary_size`).

Nenhuma falha nova.

## 6. Remoção do `k` do ledger (design D15; tarefas 3.7–3.9, 7.3 e 7.4)

Decisão do Pedro em 11/11: as quatro variantes MOP (`mop`, `as_mop`, `as_mop_llm`, `mop_nolaunch`) deixam de declarar `mop_coin_ledger_max_interactions: 2`, e a moeda passa a rodar no padrão do jar. No jar da branch `gh-tbd-mop-defaults-f1` do `ape` (`a867e471`) esse padrão é 4, o valor F1 da calibração v6 (`KeyOwnership.java:232`); na `a0fb5c16` é 1 (`:224`). A branch avançou depois para `06cc844f` (archive e sincronização das specs): `git diff a867e471 06cc844f -- src CLAUDE.md pom.xml` é vazio, então as checagens abaixo valem para os dois SHAs.

**Suíte do aperv-tool (3.9),** sem o tier de migração: 878 passaram e 49 foram pulados, os mesmos números da 6.3.

**7.3 — código antigo × novo, refeita.** `scripts/check_port_7_1.py` agora imprime, por variante, as linhas que saíram e as que entraram, e aceita só a diferença esperada (`pin/check_7_3.txt`, `RESULT PASS`):
- `derive()` no corte 3: mesmos bytes nos 5 documentos da 7.1;
- `base`, `default`, `as` e `as_llm`: o mesmo `ape.properties`, com e sem a linha do artefato;
- `mop`, `as_mop`, `as_mop_llm` e `mop_nolaunch`: o arquivo novo é o antigo menos exatamente a linha `ape.mopCoinLedgerMaxInteractions=2`, sem linha nova e com a ordem das demais preservada. Com o artefato, `as_mop` fica com 3 linhas e `as_mop_llm` com 4.

**7.4 — pareamento com o jar F1.** O código da `a867e471` foi extraído com `git archive` para `ape-f1/` (fora do git; o checkout do `ape` continuou em `master` = `a0fb5c16`). Tier de migração com `APE_REPO=ape-f1/` (`migration/tier-f1.log`): 53 passaram e 9 falharam, de 62. O total sobe de 57 para 62 porque o `TestLedgerBudget` passou de 3 para 8 testes. As 9 falhas são as mesmas da 7.2, com os mesmos motivos (7 de `APE_FIXES`, 1 `KeyError: 'ape.llmPercentageNoSubstrate'`, 1 vocabulário 123 ≠ 125). Os 8 testes do `TestLedgerBudget` passam: o padrão do jar é `"4"`, nenhuma variante MOP declara a chave e nenhum fixture MOP a carrega em `params`.

**Checagem negativa.** O `TestLedgerBudget` sozinho contra o checkout do `ape` em `a0fb5c16` (`migration/ledger-a0fb5c16.log`): 1 falha e 7 aprovados. A falha é `test_the_jar_default_is_the_calibrated_budget`, com `'1' == '4'`. É o que separa os dois jars antes de qualquer aparelho: este `tool.py` com o jar da `a0fb5c16` rodaria a moeda com k = 1.

## 7. Verificação (grupo 9)

**9.1 — lint.** Os fixers (autoflake, isort, black) não mudaram nenhum dos 11 arquivos `src/` tocados. O flake8 não acusa nenhuma linha escrita pela change depois de quebrar 7 linhas acima de 88 colunas (`tool.py` e dois testes do aperv-tool) e reordenar o import do `tests/parity/test_distance_pair_constants.py`. Os outros 102 avisos do flake8 nesses arquivos, e o black/isort de `test_aperv_tool.py` e `test_static_analysis_parser.py`, são idênticos no HEAD.

**9.2 — verify.** O `/rv-verify` achou uma regressão: os 6 testes de `tests/integration/test_package_key_end_to_end.py` falhavam (passam no HEAD). O teste força `os.path.isfile` a devolver True, então o `.apk.json` de saída "existe" sem existir, e a `_recorded_dist_max` abria o arquivo sem proteção (`FileNotFoundError`). Correção: um arquivo que não abre é um topo ilegível (INV-ANA-102), devolve `None` e é regenerado; o `os.remove` tolera um arquivo que já sumiu; teste novo `test_document_that_cannot_be_opened_is_regenerated`. Depois da correção:
- `rv-android/tests` inteira (os gates da raiz, como o CI roda), com `RVSEC_HOME` na worktree: 233 passaram, 29 pulados (`new/root-gates.log`);
- rv-static-analysis 308 (307 + o teste novo); rv-android-core 1 154; rv-tools 464; aperv-tool 878 passaram e 49 pulados sem o tier (884 e 105 com o tier pulado por falta de `APE_REPO`; o número 104 escrito antes aqui era erro de transcrição, conferido em 11/11 rodando a suíte sem o teste da 7.5).

Avisos de métrica do verify (radon, HEAD → agora), não corrigidos: o MI do `aperv_tool/tools/aperv/tool.py` cai de 38,93 para 33,38, abaixo do limiar 38; `_parse_mop_weights` tem CC 12; `Android.set_ape_heap_growth_limit` tem 62 linhas; `rv_static_analysis/config.py` (478 → 502) e `rv_tools/builtin/ape/tool.py` (491 → 504) passam de 500 linhas. O destino de cada um está na 9.3.

**7.5 — a escada padrão do jar (achado S1 da 9.3).** Nenhuma célula declara `mop_weights`, então o artefato sai no corte 3 e o jar pesa os pares com a sua escada padrão. Uma escada padrão com mais de 3 níveis deixaria os níveis fundos sem par, e nada avisaria. O teste novo `TestDefaultLadder::test_the_jar_default_ladder_fits_the_default_cut` (`tests/migration/test_cells.py`) lê `ape.mopWeights` pelo `load_key_specs` e exige tipo `INT_LIST` e no máximo `DIST_WEIGHED_MAX` níveis:
- F1 (`ape-f1/`, `a867e471`): `194,146,97`, 3 níveis, passa;
- checkout do `ape` em `a0fb5c16`: `500,400,300`, 3 níveis, passa (`migration/default-ladder-7.5.log`).

O tier inteiro, refeito com o teste novo:
- contra o F1 (`migration/tier-f1-7.5.log`): 54 passaram e 9 falharam, de 63, com as mesmas 9 falhas da 7.4 (mesmos ids de teste);
- contra a `a0fb5c16` (`migration/tier-a0fb5c16-7.5.log`): 53 passaram e 10 falharam, ou seja, as 9 conhecidas mais `test_the_jar_default_is_the_calibrated_budget` (`'1' == '4'`), como na checagem negativa da 7.4.

A sessão `ape` confirmou que a escada padrão da `gh-tbd-mop-defaults-f1` fica em 3 níveis (`KeyOwnership.java:218`, sem diferença de `src` entre `a867e471` e `06cc844f`). O flake8 não acusa nenhuma das 42 linhas acrescentadas ao arquivo. Suítes dos quatro módulos depois da 7.5 e das ressalvas da 9.3 (`new/suites-9.3.log`): rv-static-analysis 308; aperv-tool 884 passaram e 106 pulados (o teste novo é pulado sem `APE_REPO`); rv-tools 464; rv-android-core 1 154.

**9.3 — revisão.** O `/rv-code-reviewer` levantou W1–W4, S1–S5 e Q1; a 9.2 somou o caso do arquivo que não abre (D14).

Corrigido no código e nos docs:
- W1: `docs/architecture/static-analysis.md` dizia que um topo ilegível é reaproveitado; agora diz que é regenerado;
- W2: `docs/architecture/rv-android.md` ainda citava o ledger 2;
- W3: `docs/architecture/ape-rv.md` dizia 67 entradas no mapeamento, e são 64;
- a contagem de testes do rv-static-analysis passou de 307 para 308;
- W4, na parte escrita pela change: `_execute_command` caiu de CC 9 para 6 com `_stale_reason` (CC 5), e o `_recorded_dist_max`, de aninhamento 5, ficou com CC 2 ao passar a leitura dos eventos para `_horizon_from_top` (CC 9). Sem mudança de comportamento: os 308 testes do rv-static-analysis passam.

Corrigido nos artefatos (segunda `/opsx:update`, com o "ok" do Pedro, `--strict` válido):
- S1 virou a 7.5;
- S2: o derive lê os dois modos sem distingui-los só no corte padrão 3;
- S3: a checagem de reuso custa uma leitura de até 64 KiB, o buffer do `ijson`;
- S5: a citação `:1195` virou `:1210`;
- Q1: o "app sob teste mantém o heap do AVD" é inferência da calibração v6 (o `design.md:944` dela), não medida; os cenários de aperv e tools deixaram de afirmá-lo com SHALL;
- D14: passa a cobrir o arquivo que não abre.

Para caber no limite de 500 caracteres que o `--strict` impõe a um requisito ADDED, a justificativa do heap ficou na D12, e os dois requisitos apontam para ela. A mesma afirmação sem ressalva estava em cinco lugares do código e dos docs desta change: `rv_android_core/constants.py`, a docstring de `Android.set_ape_heap_growth_limit`, `modules/rv-android-core/CLAUDE.md`, `modules/aperv-tool/CLAUDE.md` e o README do `ape` em rv-tools. Os cinco passaram a dizer "is expected to keep the AVD's heap (inferred from the mechanism, not measured)".

Recusados, com motivo:
- S4 (tirar o padrão `cut = DIST_WEIGHED_MAX` de `_cut_weighed`): o único chamador de produção (`derive_mop_artifact.py:1194`) passa o corte; o padrão só serve aos testes no corte 3. Não tem efeito.
- MI do `aperv_tool/tools/aperv/tool.py`, de 38,93 para 33,38, na faixa "Poor" (< 38), e CC 12 de `_parse_mop_weights` ("Moderate"): o arquivo cresceu de 1 450 para 1 584 linhas com o código portado da calibração v6 (D9: escada, corte, heap), e o MI do radon cai com o volume do arquivo inteiro. A função valida a escada da DSL na fronteira do sistema, como na calibração. Ficam registrados, sem refatoração nesta change.
- Os três avisos de tamanho do verify mediram LOC, mas os limiares do projeto (`rv-analyze-complexity/reference.md`, § Size Thresholds) contam SLOC do `radon raw`. Em SLOC, `rv_static_analysis/config.py` tem 342 (era 325) e `rv_tools/builtin/ape/tool.py` 239 (era 237), abaixo do limiar de revisão de 500. A `Android.set_ape_heap_growth_limit` tem 64 linhas, das quais 19 são docstring e 41 são código, abaixo do limite de 50 por função. Nenhum dos três chega ao limiar.
