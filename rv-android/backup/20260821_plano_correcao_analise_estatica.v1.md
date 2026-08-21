# Plano de correção — acoplamento experimento ↔ análise estática

**Data**: 2026-08-21 · **Sessão**: `bug-analise-estatica`
**Natureza**: Fase 0 do `docs/WORKFLOW.md` — material de referência, não artefato OpenSpec
**Origem**: `docs/20260821_relatorio_analise_estatica_defeitos.md` (relatório de ideação da sessão gh105)
**Supersede**: `docs/20260821_verificacao_relatorio_analise_estatica.md` — aquele documento contém
achados que a verificação empírica posterior **refutou**; use este.
**Status**: nada implementado, nenhuma issue aberta, nenhuma change criada. A gh105 não foi tocada.

---

## 0. O que este documento é

O relatório de origem catalogou três defeitos (D1, D2, D3). Esta sessão verificou cada alegação
**contra o código, contra as specs e contra artefatos reais** — e não só por leitura. O resultado:

* os três defeitos **se sustentam**, com uma correção importante sobre o alcance do D3;
* apareceram **cinco defeitos novos** que a leitura anterior não tinha, quatro deles no
  `lib/gator/gator` e um em violação direta de invariante publicado;
* e **onze alegações foram refutadas** — em sua maioria por serem comportamento **especificado**.
  A §4 registra cada uma, com a citação que a mata, para que ninguém as rederive.

O critério de admissão deste documento: nenhum item entra sem (a) citação `arquivo:linha`, e
(b) verificação contra `openspec/specs/*/spec.md` respondendo "isto é comportamento especificado?".
Onde houve medição, o comando está na §7.

---

## 1. Inventário verificado

Ordem por gravidade dentro de cada bloco. "Especificado?" responde se existe texto normativo que
mande ou proíba o comportamento — é a coluna que separa defeito de desenho.

### 1.1 Confirmados no orquestrador Python

| # | Defeito | Onde | Especificado? |
|---|---|---|---|
| **D1** | `get_tool_command()` monta 9 flags fixos e nunca emite `--sdk`; o `gator` lê `ANDROID_SDK_HOME` com subscrito nu | `rv-static-analysis/config.py:336-406` + `lib/gator/gator:62-64` | não previsto |
| **D2** | `get_static_analysis_config()` não passa `mop_dir`; o default fixa o literal `jca` mesmo sob `--specification-set jca_android`/`generic`/`custom` | `rv-experiment/config.py:949-958` + `rv-static-analysis/config.py:199-208` | **viola** `experiment/spec.md:67` (decisão 7) |
| **D3** | a lista filtrada pelo INV-EXP-16 chega a `_create_platform_config` e o parâmetro **nunca é lido**; a seleção real é reglobada do diretório | `rv-experiment/execution_controller.py:221,260-262` | **viola** cenário `experiment/spec.md:244` |
| **P1** | `validate_on_init=False` no único construtor de produção — postura de *dry-run* num run real | `rv-experiment/config.py:956` | não previsto; **diverge** de `docs/architecture/static-analysis.md:85,171` |
| **P2** | geração de monitores: `reset_folder()` apaga a pasta **antes** de gerar, a falha vira `warning`, e a instrumentação segue sobre diretório vazio | `rv-monitor-generator/runtime_verification_generator.py:143` + `rv-experiment/pre_processor.py:157-159` | `reset_folder` e o `return False` **são** especificados; **prosseguir com `False` não é** — não existe INV-EXP equivalente ao -08 para monitores |
| **P3** | o CLI descarta o retorno de `execute_with_config()` e imprime `✅ Experiment completed successfully!` incondicionalmente; `sys.exit(1)` só no `except` | `rv-experiment/__main__.py:747-749` | lacuna: `experiment/spec.md:276-278` **manda** `run()` devolver `False`, e esse valor não tem leitor |

**Sobre o D2 — o texto normativo que o mata**, e que o relatório de origem não usou:

> `openspec/specs/experiment/spec.md:67`, decisão 7 — *"**Specification set isolation.** Each
> experiment uses exactly one specification set... **Specification sets are never mixed within a
> single experiment.**"*

Um run `jca_android` gera monitores de `jca_android` e mede alcançabilidade contra `jca`. Isso é
mistura. Note que a frase seguinte da decisão 7 fala só de geração de monitores — o acoplamento com
a análise estática nunca foi escrito, e é essa a lacuna que o D2 expõe.

**Sobre o D3 — alcance corrigido.** O defeito é **latente**. Reproduzi com as classes de produção
reais (`ExperimentConfig`, `PreProcessor.get_instrumented_apks`,
`ExecutionController._create_platform_config`, `Platform._discover_apks`):

| Cenário | `get_instrumented_apks()` | Platform instala | Diverge |
|---|---|---|---|
| A — 3 APKs, todos com `.apk.json` | a, b, c | a, b, c | não |
| **B — 3 APKs, 2 com `.apk.json`** | **a, b** | **a, b, c** | **SIM** |
| C — 3 APKs, nenhum com `.apk.json` | a, b, c (originais) | a, b, c | não |
| D — `instrumented_apks/` não existe | a, b, c | a, b, c | não |
| B + `--apks-filter` com os três | a, b | a, b, c | SIM |

Divergência exige **falha parcial de análise estática**: `instrumented_apks/` não-vazio, pelo menos
um APK sem `.apk.json` e pelo menos um com. As campanhas **nunca** alcançam isso —
`experimento-gh104/docker-compose.yml:164-167` liga os três skips e monta o corpus já instrumentado
`:ro`, então `instrumented_apks/` não é criado no run de execução e o fluxo cai sempre no cenário D.
Frequência real até hoje: **zero**. Vira observável no modo one-shot (sem `--skip-static`) sobre
corpus grande onde o GATOR falhe em algum APK.

O `--apks-filter` **não** cobre o caso: ele é a lista do corpus, não a lista pós-INV-EXP-16 — o
cenário "B + filtro com os três" ainda diverge. O `preflight.py:165-172` do
`experimento-comp162-ajc` já cita o INV-EXP-16 nominalmente para exigir diretório novo: hoje o
defeito é compensado à mão.

### 1.2 Confirmados no `lib/gator/gator`

O arquivo **é editável nesta change**. Evidência:

* `rvsec/rvsec-android/rvsec-gator/pom.xml:82-89` copia para `rv-android/lib/gator/` **só**
  `${final.jar.name}.jar` — um único `<include>`. O script `gator` não existe no reator.
* `lib/gator/.gitignore` tem duas linhas, ambas jars. O `gator` é rastreado.
* `git log --follow lib/gator/gator`: **duas changes já o editaram à mão** — `912269e4` (gh9,
  `--jvm-memory`) e `1086ebaf` (gh51, `-cgAlgorithm`).

| # | Defeito | Linha | Especificado? |
|---|---|---|---|
| **G1** | `sdk_path = os.environ['ANDROID_SDK_HOME']` — subscrito nu, `KeyError` | `:64` | não previsto (é o D1 visto do outro lado) |
| **G2** | `call(cmd, timeout=...)` com retorno **descartado** — o exit code da JVM é engolido e o `gator` sai 0 | `:111` | não previsto; **muda o que é acusado** se corrigido |
| **G3** | o timeout externo (`Command`) e o `--timeout` interno recebem **o mesmo** `analysis_timeout`; o externo começa antes e mata primeiro → `remove_temp_dirs()` nunca roda e o ramo `TimeoutExpired` do gator é código morto | `:112-113`, `:119` vs `static_analysis.py:279` + `config.py:357` | não previsto |
| **G4** | `<sdk>/tools/bin/sdkmanager` é layout legado do SDK Tools 26.x; funciona no Docker só porque `docker/android/Dockerfile:53-56` fabrica o symlink | `:95` | não previsto |
| **G5** | `parse_known_args()` repassa flags desconhecidas à JVM — é o que faz `--sdkpath` falhar em silêncio | `:254` + `:104` | não previsto |

**Consequência de G2 que importa para o desenho do reparo**: o cheque `cmd_result.code != 0` de
`static_analysis.py:369` **nunca dispara** para falhas da JVM. `OutOfMemoryError`,
`RuntimeException("Unknown option")` e `-Xmx` inválido chegam ao Python como sucesso. A única rede
que resta é a pós-condição "o JSON apareceu?" (`static_analysis.py:287-290`).

### 1.3 Confirmado na árvore Java — violação de invariante

| # | Defeito | Onde | Especificado? |
|---|---|---|---|
| **J1** | o sentinela `"complete": true` é emitido ao fim de **toda** chamada bem-sucedida de `write()`, inclusive a escrita pré-WTG — logo um run que estourou o timeout durante o WTG deixa em disco um artefato marcado como completo | `JsonReportWriter.java:111` + `RvsecAnalysisClient.java:165-170` | **viola INV-ANA-31** |

> `openspec/specs/analysis/spec.md:363` — **INV-ANA-31**: *"The JSON output of a successful
> (non-truncated) GATOR run MUST end with the literal field `"complete": true`...
> **Truncated outputs MUST NOT contain this field.**"*
>
> `spec.md:406`: *"a timeout or crash after any section produces a parseable partial file
> (**no sentinel emitted** — `complete` is absent or implicitly `false`)"*

**Prova em artefato real.** Cinco APKs do `SA_RERUN_gh91_wtg` com `timed_out: true` e
`returncode: 206` (7200 s) no `_progress/`:

| APK | `complete` | `reachability` | `transitions` |
|---|---|---|---|
| `app.pachli_50` | **true** | 6453 | 0 |
| `ch.rmy.android.http_shortcuts` | **true** | 7016 | 0 |
| `it.niedermann.owncloud.notes` | **true** | 1318 | 0 |
| `org.glpi.inventory.agent` | **true** | 179 | 0 |
| `com.github.livingwithhippos.unchained` | **true** | 2 | 0 |

O comentário em `RvsecAnalysisClient.java:157-163` afirma o contrário — *"the pre-WTG write does
NOT emit the sentinel... with NO sentinel"* — e está errado.

**Há consumidor real**: `aperv-tool/tools/aperv/derive_mop_artifact.py:248-252` levanta
`DerivationError` quando o sentinela falta. Um run estourado **passa** pelo portão que existe para
rejeitá-lo. O `scripts/gh91_campaign.py:133-147` já compensa exigindo sentinela **e**
`timed_out == False` do `_progress`; o pipeline `rv-platform` não compensa.

**Delimitação honesta**: o denominador de cobertura (`reachability`) está **íntegro** nos cinco — é
escrito antes do WTG. O que se perde é `transitions`/`windows`. Não há inflação de cobertura.

### 1.4 Fora desta change por decisão sua, não minha

| # | Item | Estado |
|---|---|---|
| **N9** | `UsedJcaMethodsVisitor` descarta pointcut cujo owner não está em import explícito; `RandomStringPassword.mop` contribui **zero** alvos em `jca` e `jca_android`, em toda campanha já rodada | **vai para a gh69** — ver `docs/20260821_handoff_gh69_coringas.md` |

---

## 2. Alegações refutadas — não rederivar

Onze itens que apresentei como defeitos e que a verificação matou. A maioria por serem
**comportamento especificado**. Registro a citação que decide cada um.

| Alegação | Veredito |
|---|---|
| "um APK não instrumentado entra na execução parecendo saudável" (originais copiados ganham `.apk.json`) | **especificado.** INV-EXP-08 (`experiment/spec.md:193`) manda copiar para que *"The experiment MUST NOT abort"*; a nota de `:209` declara o resultado pretendido: *"experiment runs on originals with 0% coverage"*. Resta só imprecisão de documentação: a **rota** descrita em `pre_processor.py:448-450` e `spec.md:209` não é a que o código percorre |
| "o cache da análise estática não tem chave de proveniência" | **especificado.** INV-ANA-11 (`analysis/spec.md:345`) *manda* o cache por existência de arquivo. E o gatilho que aleguei é impossível: `output_dir` é sempre por-run (`__main__.py:1255,1280,1289`) e o resume desliga a análise uma camada acima. `scripts/static_analysis_sweep.py:442-453` já contorna, citando o invariante |
| "`complete`/`timed_out` produzidos e nunca consumidos; cobertura sai inflada" | **falso.** `timed_out` não é chave do JSON (é campo Pydantic em memória, lido em 5+ lugares); `complete:false` é inescrevível; 0 artefatos truncados em 11.697; e `reachability` sobrevive ao timeout. O defeito real é o **J1**, que é o inverso |
| "o checksum do resume não cobre `specification_set`" | **especificado.** INV-PLT-12 + cenário `platform/spec.md:427` definem o escopo como o `PlatformConfig`, que não tem — nem pode ter (`extra="forbid"`) — esse campo. E `platform/spec.md:355`: divergência de checksum *"logs a warning but execution continues"* |
| "`coverage.py` zera métricas no retorno antecipado" | **especificado com precisão.** INV-ANA-25 (`analysis/spec.md:360`) descreve exatamente esse comportamento, inclusive a parte de contar erros antes. O código cita o invariante em `:734-740` |
| "`_percentage()` devolve 0.0 para total==0, confundindo indefinido com zero" | **especificado.** INV-PLT-15 e INV-PLT-16 exigem justamente zero nesse caso |
| "`post_processing_completed: True` é literal, sem gate" | **especificado + deliberado.** Contrato em `experiment/spec.md:125,154`; e INV-EXP-02 **proíbe** o PostProcessor ler resultados, que é o dado que um gate exigiria. O comentário em `post_processor.py:177-181` explica |
| "a sonda de API levels `["33","29","28","27","26"]` está errada" | **especificado.** `docs/architecture/static-analysis.md:171,176` documenta os níveis literais sob NFR07 |
| "`mopDir` vazio devolve conjunto vazio em silêncio" | **especificado por teste.** `MopSpecsParityTest.emptyDirYieldsEmptySetWithoutThrowing` + dois casos em `MopSignatureLoaderTest`. Diretório *inexistente* é deliberado (guarda explícita); `MOPException` engolida em `MopSpecsTargetSource:44-46` é a única parte sem cobertura |
| "`if not success` sobre `InstrumentationResults` é defeito" | **comportamento especificado** (INV-EXP-08/15/16). O ramo é código morto de facto, mas nenhuma spec exige aquele ERROR. Cosmético |
| "o `rv-platform` desiste da análise estática em silêncio" | **especificado.** INV-PLT-05 (`platform/spec.md:164`): *"it MUST return `True` and log a warning"*. O warning é emitido um nível abaixo (`static_analysis_parser.py:220`). Resta cosmético: o `else` de `static_analysis.py:150` é inalcançável e o log diz `"Static analysis completed"` com dado vazio |

**Lição de método, registrada de propósito**: das minhas primeiras onze alegações, sete morreram por
eu não ter perguntado "existe invariante que mande isto?" antes de chamar de defeito. Essa checagem
é obrigatória para qualquer achado novo neste sistema.

---

## 3. Ordem de execução

A ordem não é por custo. É pela observabilidade que cada passo destrava para o seguinte.

| | Passo | Por que nesta posição |
|---|---|---|
| 1 | **P3** — o CLI consome o booleano e sai ≠ 0 | Uma linha. Enquanto o CLI declarar sucesso incondicional, **nenhuma barreira nova é observável de fora** e nenhum teste de aceitação pode usar código de saída |
| 2 | **G2** — o `gator` propaga o exit code da JVM | Sem isto, o cheque `code != 0` do Python continua cego e qualquer barreira a jusante herda a cegueira. **Muda o que é acusado** — precisa da sua decisão (§5) |
| 3 | **D3** — a lista filtrada passa a valer | A barreira. De pé, converte qualquer falha futura da análise (não só D1) em recusa |
| 4 | **P2** — falha de geração de monitores deixa de ser `warning` | Mesmo padrão do D3, um estágio antes; hoje `out/monitors/` pode ficar vazio e o run anuncia sucesso |
| 5 | **D1 + G1** — a raiz do SDK chega ao GATOR | Reparo puro. Ver §4 sobre cobertura das duas opções |
| 6 | **D2** — o `mop_dir` deriva do `specification_set` | O de maior alcance conceitual; entra com o registro do `mop_dir` efetivo na saída |
| 7 | **J1** — o sentinela só na escrita pós-WTG | Violação de invariante com prova; independente dos demais |
| — | **P1, G3, G4, G5** | reparo puro, entram em qualquer ponto |

---

## 4. Desenho dos reparos que têm escolha

### D1 — duas camadas, não competem

| Opção | Cobertura | Custo |
|---|---|---|
| **A — fallback em `lib/gator/gator:62-64`** | **10 portas de entrada**: `rv-experiment`, `rv-platform`, `rv-static-analysis` standalone, `sa_parallel.py`, os dois `static_analysis_sweep*.py`, `gh91_sa_rerun.py`, `filter_apks_static_analysis.py`, `gh51_smoke_test.py`, shell manual | 3 linhas, **zero** testes tocados (a forma do argv não muda) |
| **B — emitir `--sdk` em `get_tool_command()`** | **5 portas** (as que passam por lá) | ~6 asserções de argv a atualizar |

Fazer **as duas**. A opção A é a rede de segurança e a única que cobre os chamadores que montam o
argv por conta própria. A opção B fecha uma incoerência arquitetural real: hoje o config Python lê
`ANDROID_HOME`, deriva `android_platforms_dir` e `android_jar` — e **descarta tudo**, deixando o
`gator` recalcular seu próprio `android.jar` a partir de outra variável, não validada.

**Duas armadilhas registradas:**

1. O flag é **`--sdk`** (`lib/gator/gator:195`, `dest='sdkpath'`). **Não existe `--sdkpath`** — e
   como `:254` usa `parse_known_args()`, passá-lo não dá erro: o token vai para a JVM e o `KeyError`
   dispara igual. Verificado por execução. O nome errado está em
   `openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/design.md:143`, `.../tasks.md:69`
   e `docs/20260730_verificacao_consistencia_gh91.md:617` — **corrigir os três**.
2. Emitir `--sdk` incondicionalmente quebra quem tem só `ANDROID_SDK_HOME` exportado, que é o que a
   documentação vem mandando desde julho. Emitir **apenas quando a raiz for resolvível** custa o
   mesmo e não regride ninguém.

### D2 — o mapeamento e a régua declarada

Reusar o mapa de `get_monitor_generation_config()` (`rv-experiment/config.py:695-719`), que já
despacha `jca`/`jca_android`/`generic`/`custom` corretamente e levanta `ConfigurationError` no
default. Extrair para um método único e chamá-lo dos dois lados.

**Não** remover o default `jca` de `rv-static-analysis/config.py:199-208` sem antes resolver o P1:
com `validate_on_init=False`, um `mop_dir` ausente ou inválido chega ao GATOR, que responde com zero
alvos em silêncio (contrato testado — ver §2) e escreve um JSON estruturalmente válido com todo
`reachesTarget` em `false`, indistinguível de "o app não toca criptografia".

**Registrar a régua na saída**: coluna `mop_dir` (ou `spec_set`) no `summary.csv`. Isto é seguro —
`aperv-tool/analysis/loader.py:93-105` declara os payloads mas com a ressalva explícita
*"A campaign writing extra columns keeps them; the join is not restricted"*. Não há contrato
congelado a quebrar. As colunas que o `aperv-tool` consome — `cov_reachable`, `cov_reaches_target`,
`cov_directly_reaches_target` — são exatamente o raio de dano do D2.

### D3 — a barreira já existe, falta ligá-la

O parâmetro `apks` já chega em `_create_platform_config` (`execution_controller.py:221`) e nunca é
lido. E o `PlatformConfig` já tem `apks_filter_file`, com recusa dura implementada:

```python
# modules/rv-platform/src/rv_platform/platform.py:356-365
if self.config.apks_filter_file:
    allowed = set(Path(self.config.apks_filter_file).read_text().strip().splitlines())
    apk_files = [f for f in apk_files if f.name in allowed]
    if not apk_files:
        raise ValueError(f"No APKs match filter: {self.config.apks_filter_file}")
```

Alimentar esse filtro com a lista filtrada faz o INV-EXP-16 valer e traz o erro duro de graça.
**Ressalva**: `--apks-filter` é flag do usuário — a composição correta é **interseção**, nunca
sobrescrita.

**O teste que falta existe no papel**: `openspec/changes/archive/2026-04-16-gh49-fix-instrumentation-pipeline/design.md:46`
nomeia `test_execution_only_with_sa_data`. Grep no repo: **zero ocorrências**. E
`modules/rv-experiment/tests/experiment/test_execution_controller.py:193-205`,
`test_config_uses_instrumented_apks_when_available`, **mascara** o defeito: patcha `os.listdir` para
`["test.apk"]` — o critério defeituoso — e a única asserção é `assert config is not None`.

### J1 — o sentinela

Emitir `"complete": true` **só** na escrita pós-WTG (parâmetro `emitSentinel` no `write()`, ou
marcar a pré-WTG distintamente), e corrigir o comentário de `RvsecAnalysisClient.java:157-163`, que
hoje descreve o comportamento oposto ao do código.

---

## 5. Decisões que precisam de você

1. **G2 muda o que é acusado.** Propagar o exit code da JVM faz runs que hoje terminam "com sucesso"
   passarem a falhar duro. Entra nesta change, ou vira change própria com corrida de calibração?
2. **D3 recusa o run inteiro ou só o APK afetado?** Num corpus de 162, um GATOR que estoura em três
   não deveria matar a campanha — mas "seguir com 159" precisa aparecer em artefato, senão o `n`
   muda em silêncio. Precedente em casa: `aperv-tool/tools/aperv/tool.py:1195-1216` (gh96) escolheu
   **falhar a task**, com justificativa escrita.
3. **O `mop_dir` efetivo vira coluna do `summary.csv`?** Tecnicamente barato e sem leitor congelado
   (§4). É mudança de header.
4. **P1: ligar o `validate_on_init`?** Está desligado desde 2025-06-11, commit `cd8167fb`, cuja
   mensagem inteira é `refactoring`. É a razão de o pré-voo inteiro não existir no caminho de
   produção, e desliga a guarda Pydantic do INV-ANA-33. Ligá-lo é mudança de comportamento
   observável — configurações que hoje passam podem falhar cedo.
5. **Reabrir o bloqueador B4 da gh104?** A decisão registrada em `experimento-gh104/CONTEXTO.md:147`
   continua correta para o desenho atual (reuso dos `.apk.json` da `comp162`). A pergunta é se ela
   deve deixar de ser necessária antes de a campanha rodar.
6. **Antes ou depois de a gh105 aterrissar?** Menos urgente do que o relatório de origem sugeria: o
   crescimento do delta pelas junction specs é **hipótese**, não aritmética (sob LENIENT, uma
   junction só aumenta o delta se nomear um método ainda ausente nas classes já cobertas).

---

## 6. Módulos afetados

| Módulo | Arquivos |
|---|---|
| `rv-experiment` | `__main__.py` (P3), `config.py` (D2, P1), `pre_processor.py` (P2), `execution_controller.py` (D3) |
| `rv-static-analysis` | `config.py` (D1-B, D2), `analysis/static/static_analysis.py` (G3, timeouts) |
| `rv-platform` | `platform.py` (D3, filtro), `components/static_analysis.py` (cosmético) |
| `lib/gator/gator` | `:62-64` (G1), `:111` (G2), `:95` (G4), `:254` (G5) — **editável, com precedente** |
| árvore Java (reator `rvsec`) | `JsonReportWriter.java:111`, `RvsecAnalysisClient.java:157-170` (J1) |
| OpenSpec | `specs/experiment/spec.md` (INV-EXP-16 passa a valer; corrigir a nota de `:209`; decisão 7 ganha o acoplamento com a análise), `specs/analysis/spec.md` (INV-ANA-31 ganha teste) |
| Docs | `docs/architecture/static-analysis.md` §3, §4 (o argv literal de `:85`), §7 (`:143`, `:171` NFR05), cenários `:319-331`, *variability guides* `:259`/`:315`, `:380`; e as três correções de `--sdkpath` |

**Trilha sugerida: Fast-Forward SDD.** Precedente direto: a **gh102**
(`openspec/changes/archive/2026-08-16-gh102-artifact-scoped-parse`, commit `bd10fb0f`) tratou um
defeito da mesma família — assinatura observável idêntica (`coverage.csv` só com cabeçalho,
`cov_*=0`, logcat cheio de `RVSEC-COV`) — como `track:ff-sdd`, com `corpus_evidence.md` e
`verify_corpus.py` como anexos. Esse é o molde do artefato. **A issue #102 continua aberta no
GitHub apesar de arquivada** — vale fechá-la ao abrir a nova.

Consequência de método: a assinatura "`coverage.csv` só com cabeçalho" já tem **pelo menos três
causas distintas** conhecidas (a da gh102, o D1, e o descarte não contado de
`coverage.py:655-674`). Um diagnóstico futuro não pode assumir a causa.

---

## 7. Como reproduzir

### D3 — a divergência do cenário B

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
# script que instancia as classes de produção reais e tabula os 5 cenários
.venv/bin/python /tmp/claude-1000/<sessão>/scratchpad/inv16_probe.py
# esperado: divergência SÓ no cenário B (e em B com --apks-filter contendo os três)
```

### D1 — a precedência real dos argumentos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator
env -u ANDROID_SDK_HOME python3 ./gator a --sdkpath /tmp/fake -p x.apk --out /tmp/o.json
#   -> KeyError: 'ANDROID_SDK_HOME'   (o argumento foi engolido por parse_known_args)
env -u ANDROID_SDK_HOME python3 ./gator a --sdk /tmp/fake -p x.apk --out /tmp/o.json
#   -> passa de :64 e morre adiante por outro motivo
```

### J1 — o sentinela que mente

```bash
python3 - <<'EOF'
import json, glob, os
D = "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
for p in glob.glob(os.path.join(D, "_progress", "*.json")):
    d = json.load(open(p))
    if not d.get("timed_out"): continue
    name = os.path.basename(p)[:-5]
    hits = [h for h in glob.glob(os.path.join(D, "**", name), recursive=True) if "_progress" not in h]
    if hits:
        a = json.load(open(hits[0]))
        print(name, "complete=", a.get("complete"), "reach=", len(a.get("reachability", [])),
              "trans=", len(a.get("transitions", [])))
EOF
# esperado: 5 APKs, todos complete=True com trans=0
```

### Contagem de alvos por conjunto

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
# usa o fat-jar do extrator; ver docs/20260821_handoff_gh69_coringas.md §5 para o Count.java
java -cp rvsec/rvsec-mop-extractor/target/mop-extractor.jar:<scratch> Count \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca_android
# medido 2026-08-21: jca 120 assinaturas / 68 pares / 22 owners
#                    jca_android 119 / 67 / 22
```

---

## 8. Pendências documentais (reparo puro, sem decisão)

| Item | Onde |
|---|---|
| `--sdkpath` → `--sdk` | `openspec/changes/archive/2026-07-31-gh91-.../design.md:143`, `.../tasks.md:69`, `docs/20260730_verificacao_consistencia_gh91.md:617` |
| "linha 267" → linha 182 | `docs/20260821_relatorio_analise_estatica_defeitos.md` §2.4 |
| logs das duas sondas não commitados (vivem em `/tmp`) | copiar `probe_run.log` e `probe_run_b.log` para `data/gh105/evidence/reach-probe/` |
| *"end at `validateInputs()`"* — a última linha `RVSEC-COV` é `setupHmacUI()` | `data/gh105/evidence/f2-reach-probe.md` |
| a rota descrita não é a que o código percorre | `pre_processor.py:448-450` e `openspec/specs/experiment/spec.md:209` |
| o comentário afirma o oposto do código | `RvsecAnalysisClient.java:157-163` |
| contagens 70/69 → 120/119 assinaturas (68/67 pares) | `docs/20260821_relatorio_analise_estatica_defeitos.md` §3.3 |
| issue #102 aberta apesar de arquivada | GitHub |

---

## 9. Referências

* `docs/20260821_relatorio_analise_estatica_defeitos.md` — relatório de origem (D1/D2/D3).
* `docs/20260821_handoff_gh69_coringas.md` — o N9 e o que fazer na gh69.
* `docs/architecture/static-analysis.md` — arquitetura do subsistema; ver §9 do documento
  superseded sobre a fronteira que ele escolheu e o que fica desatualizado após os reparos.
* `openspec/changes/archive/2026-08-16-gh102-artifact-scoped-parse/` — precedente de trilha,
  de artefato e de assinatura observável.
* `data/gh105/evidence/f2-reach-probe.md` e `data/gh105/evidence/reach-probe/` — evidência das
  sondas; auditada e byte-idêntica aos originais em `results/`.
