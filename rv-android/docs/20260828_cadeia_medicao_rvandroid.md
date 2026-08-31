# A cadeia de medição do RV-Android — análise ponta a ponta — 28-30/08/2026 (rev. 6)

**Papel deste documento**: material de referência da Fase 0 (`docs/WORKFLOW.md`), companheiro de
`docs/20260827_achados_instrumentador_dexlib2.md`. Aquele cobre o **tecelão de advice** — o que o
instrumento *acusa*. Este cobre a **cadeia de medição** — o que o instrumento *mede*: a chave de
escopo, a análise estática, a cobertura, o cruzamento e o relatório. Nenhum dos dois é artefato
OpenSpec.

**Por que existe.** A auditoria do tecelão de advice encontrou uma classe de defeito — resolução de
nome feita por transformação textual, falhando em silêncio. A pergunta natural foi se ela aparecia
em outros pontos do pipeline. Aparece, em mais lugares e com mais consequência.

**O que a rev. 6 faz.** A rev. 6 (30/08) é a primeira revisão escrita **de dentro da
implementação**: a change `gh111` foi aplicada, e esta revisão registra o que as corridas mediram —
não mais o que a leitura de código previa. Ela recolhe também o que duas verificações independentes
estabeleceram antes dela, a adjudicação das cinco revisões externas
(`docs/20260829_adjudicacao_revisoes_gh111.md`) e a verificação de consistência das dez dimensões
(`docs/20260830_verificacao_consistencia_gh111.md`). Cinco correções e quatro achados novos:

- **a correção C1 estreita-se à política padrão** — o D9 é observável hoje sob `--package-detector`,
  que é política viva; o que é verdade é que nenhuma corrida registrada jamais a ligou. Ver §15.7;
- **a sonda `D9Probe` é predição, não aceitação** — ela não muta a Scene, então editar a guarda muda
  a saída dela por zero. A aceitação virou corrida real, e rodou: **21 → 535**;
- **os denominadores crus não são os entregues** — 771/1.971/3.589 são crus; o cliente filtra as
  classes geradas antes de escrever, e os entregues são 762/1.952/3.578/535;
- **o vazamento das classes de recurso** (D9c, INV-ANA-71), que é por que os 550 do `screenshottile`
  saíram de cena;
- **o controle de invariância trocou** — o `app.pachli_50` não podia falhar;
- **três achados de entrega**: os invariantes dos deltas não chegam à spec base pelo motor de merge,
  quatro requisitos da base contradiziam a change, e a ordem de arquivamento `gh104` → `gh111` está
  com a porta fechada hoje.

As correções da rev. 6 estão marcadas **[rev. 6]**, e §15.7 é o seu balanço.

**O que a rev. 5 faz.** A rev. 5 (29/08) não acrescenta investigação: ela **submete a rev. 4 à
leitura do código que a change ia precisar de qualquer forma**, e o que a leitura devolveu contradiz
a rev. 4 em dois pontos e completa um terceiro. Quatro correções e um achado novo:

- **o D9 e o D2 são conjuntivos na via de produção, não independentes** — `App.code_package` devolve
  o manifesto verbatim por default (`app.py:146-147`), então a guarda reparada leria hoje o mesmo
  valor de sempre. Os números da sonda foram medidos com a chave já neutralizada, e os quatro
  artefatos colapsados vieram do rerun da gh91, que passava `codePackage=` à mão para o cliente. Ver
  §15.6;
- **o diagnóstico histórico do normalizador está invertido** — `docs/NOVO/06_normalizacao_inner_classes.md`
  atribui o `$` ao AspectJ; o `Coverage.aj:64` usa `Class.getName()`, que nunca insere `$` em
  fronteira de pacote. Ver §5.1;
- **o D3 mata o `SignatureNormalizer` inteiro**, não só duas chamadas: a classe tem exatamente um
  consumidor em todo `modules/*/src`. Ver §11, D3;
- **a §15.3 ganha a coluna que faltava**: os achados da §9 que não estão na change, não foram
  roteados e não foram retirados. Eram invisíveis na tabela;
- **achado novo — a procedência e o desvio de finalidade do `libPackages.txt`**. Ver §4.3 e §15.6.

As correções da rev. 5 estão marcadas **[rev. 5]**.

**O que a rev. 4 faz.** A rev. 4 (fim da tarde de 28/08) fecha a **investigação do D9**, que a
rev. 3 deixou como primeiro item do escopo. O mecanismo do colapso do denominador está determinado e
foi reproduzido ao vivo: **não é o Soot nem o multidex** — é um laço do próprio GATOR
(`AnalysisEntrypoint.java:111-126`) que rebaixa as classes do app a biblioteca porque compara contra
o pacote do **manifesto**. Ver §4.3 para o mecanismo, §15.5 para o balanço, e
`docs/20260828_d9_colapso_denominador.md` para o relatório completo. As correções que a rev. 4 faz
nas seções anteriores estão marcadas **[rev. 4]**.

**O que a rev. 3 faz.** A rev. 3 (tarde de 28/08) não acrescenta análise nova: ela **submete a rev. 2
à verificação no código e no corpus**, retira o que não sobreviveu, e **registra as decisões do
pesquisador** que fecham o recorte. Ver §15, que é o resumo executivo desta revisão e o lugar onde
o escopo da change está definido.

Três medições da rev. 2 foram **reproduzidas diretamente** sobre
`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`
e conferem byte a byte: **75/162** artefatos cujo manifesto não é prefixo de classe nenhuma;
distribuição do denominador **min 1 / mediana 671 / 6 APKs com ≤30 classes**; corrupção do
normalizador em **465 classes de 215.430, em 7 de 162 APKs**, com a mesma lista e as mesmas frações.
As medições da rev. 2 estão sólidas.

O que **não** sobreviveu foram afirmações sobre *comportamento* — não sobre números. Estão corrigidas
em linha, cada uma marcada **[rev. 3]**, e listadas em §15.1.

**O que a rev. 2 acrescentou.** A rev. 1 (manhã de 28/08) mapeou a cadeia a partir do código e do
acervo local. Aquela revisão acrescentou quatro coisas e corrigiu cinco:

- o **mapa verificado do fluxo do `rv-experiment`** ponta a ponta (§2), que faltava por inteiro;
- o **elo da chave de escopo** (§3), que a rev. 1 tratava em dois parágrafos e é o elo que decide se
  o denominador existe. É aqui que mora o defeito que **bloqueia rodar o pipeline ponta a ponta no
  corpus atual**: 75 de 162 APKs teriam denominador vazio;
- o **cruzamento com o corpus e as campanhas publicadas** (§6), com o impacto medido sobre o artigo;
- a **medição que a rev. 1 declarava pendente**, agora fechada (§5.1);
- duas medições que a rev. 1 não tinha: **quantos registros de runtime não casam com o denominador**
  (51,6% das assinaturas distintas, sobre 11,6 milhões de linhas) e uma **quarta causa de cobertura
  errada** — o colapso do denominador, que é o único dos quatro que **infla** um número que entrará no
  artigo (§4.3). *(A rev. 2 a atribuía ao carregamento do Soot; a **[rev. 4]** determinou que a causa
  é o rebaixamento feito pelo GATOR.)*;
- e a **granularidade da chave de junção** (§4.5): a cadeia opera em duas réguas ao mesmo tempo, o
  `CLAUDE.md` do `rv-static-analysis` afirma o contrário do que o código faz, e a gh69 é adjudicada
  contra isso.

Correções factuais à rev. 1, todas registradas em linha: os três APKs nomeados como testemunhas não
pertencem ao corpus do artigo; "0,00% em 18 execuções" é 9; a âncora do lstopo no filtro da campanha
aponta para outra versão do app; "package mismatch não se manifesta neste corpus" é verdadeiro pelo
motivo errado; e o teste do normalizador contra o acervo do artigo dá números diferentes dos do
acervo de calibração.

**Escopo de reparo.** O caminho ajc é **referência histórica, não alvo de reparo** (decisão do
pesquisador, 28/08). Ele é consultado aqui para saber como as coisas eram e para atribuir
divergências, nunca para ser corrigido. O alvo é dexlib2 + análise estática + os módulos Python.

**Enquadramento das decisões.** O artigo **não foi publicado**. A campanha será **refeita depois das
correções** (gh105, gh109, instrumentador, análise estática) e os números serão escritos a partir dela
(decisão do pesquisador, 28/08). Nada aqui é errata: os números atuais são a **linha de base de
verificação** dos reparos, e a lista de reparos é um **portão de campanha**, não uma fila de
prioridades — §6.4.

---

## 1. A cadeia, e os dois caminhos que ela tem

```
                         ┌──────────────────────────┐
   APK original ────────►│  CHAVE DE ESCOPO         │  ← o elo que a rev. 1 não isolava
        │                │  App.code_package        │
        │                └────────────┬─────────────┘
        │                             │ -clientParam codePackage=
        ├──► análise estática (GATOR/Soot) ──► <apk>.apk.json  ──┐
        │       filtro: className.startsWith(chave)              │  DENOMINADOR
        │                                                        │
        ├──► tecelão de advice   (dexlib2) ──► APK instrumentado │
        │        deny-list de bibliotecas, NÃO usa a chave       │
        │                                       │                │
        └──► tecelão de cobertura (dexlib2) ────┘                │
                    deny-list, NÃO usa a chave  │                │
                                                │                │
                                     execução no emulador        │
                                     (usa package_name, COM      │
                                      sufixo — e está certo)     │
                                                │                │
                                  logcat: RVSEC-COV + RVSEC      │
                                                │                │  NUMERADOR
                                         parser (Python)  ───────┤
                                                │                │
                                   ► CRUZAMENTO por string ◄─────┘
                                                │
                                   coverage.csv / summary.csv / results.json
```

Cada seta é uma oportunidade de as duas pontas discordarem sobre a grafia de um nome. A cadeia tem
contabilidade rigorosa em quase todo ponto — e **nenhuma** no cruzamento, que é o único ponto onde
as duas populações se encontram, **nem na chave**, que é o único ponto que decide se existe
população.

**A cadeia tem dois caminhos, e as campanhas publicadas usaram o segundo.**

| | via de produção (`rv-experiment`) | via das campanhas publicadas |
|---|---|---|
| quem escolhe a chave | `App.code_package` (`domain/app.py:130-150`) | um CSV congelado, `Mneut` (gh91) |
| quem invoca o GATOR | `StaticAnalyzer.analyze()` | `scripts/gh91_sa_rerun.py:344` |
| chave efetiva | package do manifesto, **verbatim** | package do manifesto **neutralizado** |
| exercitada na campanha do artigo? | **não** | sim |

As 16 configurações da campanha do artigo têm `generate_monitors`, `instrument_apks` e
`run_static_analysis` **todos `false`** (verificado em 16/16 `experiment_config.json` sob
`RV_ANDROID_NOVO_DATASET/RESULTS/m*/results/*/*/`). A via de produção do `rv-experiment` **nunca
rodou análise estática nas campanhas publicadas**. É por isso que o defeito da chave nunca apareceu:
ninguém pediu ao pipeline que o cometesse.

---

## 2. O fluxo do `rv-experiment`, ponta a ponta

Mapa verificado no código (não em documentação), com âncora para cada afirmação.

```
  CLI run() __main__.py:394-766
    ├ --config ────► ExperimentConfig.from_file (:692)   [as demais flags são IGNORADAS]
    └ DSL da CLI ──► _create_experiment_config_from_cli (:1147) ─ resume? (:1258-1299)
                                   ↓
  ExperimentController.run()  experiment_controller.py:137-223
    │ save_experiment_config → experiment_config.json (:167, :365-383)
    │
    ├ FASE 1  PreProcessor.process(gen, inst, static)   pre_processor.py:63-120
    │    1 _generate_monitors   (:122-180)  → <output>/monitors/     [reset_folder!]
    │    2 _instrument_apks     (:182-267)  → <output>/instrumented_apks/*.apk
    │    3 _run_static_analysis (:291-392)  → <output>/instrumented_apks/<nome>.apk.json
    │                                          roda sobre os APKs ORIGINAIS
    ├ FASE 2  _run_execution (:241-311) → ExecutionController → PlatformConfig
    │            └► Platform.run()  platform.py:128-205
    │                 _generate_tasks (:207-266)   APK × tool × rep × timeout
    │                 _skip_completed_tasks (:268-333)
    │                 _execute_tasks (:369-479) → TaskExecutor
    │                 _process_results (:624-655) → 6 artefatos
    └ FASE 3  PostProcessor.process()  post_processor.py:91-126
```

### 2.1 Entrada

`run` tem 26 flags (`__main__.py:394-594`). As que importam para esta análise:

| Flag | Default | Destino |
|---|---|---|
| `--apks-dir` | `./apks_examples/` | `ExperimentConfig.apks_dir` (`:1329`) |
| `--specification-set` | `jca` | `resolve_spec_set_dir` (`config.py:645-704`) |
| `--instrumentation-variant` | `ajc` | `pre_processor.py:214-220` |
| `--generate-monitors/--skip-monitors` | `True` | `pre_processor.py:102-105` |
| `--instrument-apks/--skip-instrument` | `True` | `:108-111` |
| `--static-analysis/--skip-static` | `True` | `:114-117` |
| `--package-detector/--no-package-detector` | tri-estado, resolve para `False` | `:1325` → `App(package_detector=…)` |
| `--apks-filter` | `None` | `config.get_apk_list` (`config.py:591-593`) |
| `--name` / `--resume-dir` | `None` | resume (`:1258-1299`) |

**Não existe nenhuma flag que forneça uma chave de escopo.** O único controle sobre a chave é o
booleano `package_detector` — "eleger heuristicamente ou não". Este é o buraco de §3.

Duas armadilhas verificadas na entrada:

- **modo `--config` ignora quase tudo**: `:690-695` pula todo o `_create_experiment_config_from_cli`,
  então `--instrumentation-variant`, `--package-detector`, `--analysis-timeout`, `--name` e
  `--resume-dir` não têm efeito; o arquivo é a autoridade.
- **as env vars de negação só funcionam dentro do Docker**: o `envvar=` do Click liga a variável à
  forma **positiva** da flag; só o entrypoint traduz (`docker/rvandroid/docker-entrypoint.sh:84-88`).
  Fora do container, `RV_SKIP_STATIC_ANALYSIS=true` faz o **oposto** da intenção.

### 2.2 Pré-processamento

**Monitores** (`pre_processor.py:122-180`): `RuntimeVerificationGenerator.generate_monitors` faz
`utils.reset_folder(output_dir)` (`runtime_verification_generator.py:146`) — apaga o diretório antes
de gerar. Falha vira `logger.warning`, nunca aborta (`:158-171`).

**Instrumentação** (`:182-267`): variante via `get_instrumenter(variant, cfg)`
(`rv-instrumentation/factory.py:8-27`). **Falha não aborta**: qualquer exceção cai em
`_copy_original_apks()` (`:269-289`), que copia os APKs **originais** para `instrumented_apks/`
preservando o basename — a jusante nada distingue um APK instrumentado de um original com o mesmo
nome (INV-EXP-08).

**Análise estática** (`:291-392`): roda sobre os **APKs originais** (`_get_target_apks_for_analysis`,
`:394-428`) e grava em `instrumented_apks/`, ao lado do APK instrumentado, porque é ali que o
rv-platform procura. O sítio único onde a chave nasce:

```python
app = App(app_path=apk_path, package_detector=self.config.package_detector)   # :347-350
analyzer = StaticAnalyzer(app=app, config=static_config, output_dir=apk_output_dir)
result = analyzer.analyze()                                                    # :357
```

**O que cada `--skip-*` realmente pula** (verificado, e há efeitos colaterais não óbvios):

| Flag | Efeito colateral verificado |
|---|---|
| `--skip-monitors` | `out/monitors` não é resetado nem repovoado; a instrumentação usa o que estiver lá |
| `--skip-instrument` | `instrumented_apks/` não é criado → `_get_target_apks_for_analysis` devolve `[]` (`:408-412`) → **a análise estática também não roda**, mesmo sem `--skip-static` |
| `--skip-static` | nenhum `.apk.json` é gerado → `get_instrumented_apks` exclui todo APK (`:459-467`) → **fallback para os APKs originais** (`:485-492`): o experimento roda sobre APKs **não instrumentados** |
| resume | os três são forçados a `False` (`__main__.py:1266-1270,1281-1287`) |

### 2.3 Execução

`ExecutionController.setup` recebe `apks` mas **não os repassa** — `_create_platform_config`
(`execution_controller.py:219-260`) não tem esse parâmetro. O `PlatformConfig` recebe apenas um
**diretório** (`:258-260`), e o `Platform` faz um glob novo de `*.apk` (`platform.py:335-367`).

**Consequência**: o filtro "só APKs com `.apk.json`" (`pre_processor.py:459-467`) serve **apenas**
para o teste de vazio e para decidir o fallback; ele **não seleciona** o que será executado. Um APK
sem análise estática que esteja em `instrumented_apks/` **será executado**, desde que ao menos um
outro APK tenha passado no filtro.

Tasks: produto cartesiano `APKs × tool_configs × repetitions × timeouts` (`platform.py:235-237`).
Identidade da task = `(apk_name, tool.name, tool.variant, repetition, timeout)` (`:312-320`) — o
`task_id` (UUID novo a cada run) não participa.

`TaskExecutor` (`execution/executor.py:181-270`) executa em três fases, **na ordem por tipo, não na
ordem de registro** (`:286-363`):

1. `StaticAnalysisComponent` (fora do emulador);
2. `CoverageComponent.execute` (inicializa o tracker, fora do emulador);
3. sessão do emulador (`:365-468`): `install → logcat start → mark_tool_start → coverage start →
   tool.execute`, com o `finally` **dentro** do `with`, para que a coleta rode com o device vivo.

### 2.4 Onde o `.apk.json` é lido — e o que acontece se estiver vazio

Nome: `<basename com .apk>` + `.json` (`constants.py:14`; `static_analysis.py:198-200`). Três pontos
de leitura:

1. **filtro de elegibilidade** (`pre_processor.py:459-467`) — que, como visto, não seleciona;
2. **fase 1 da task** (`components/static_analysis.py:67-98`): `copy_static_analysis_files` copia
   `.methods` e `.json` do `apks_dir` para o diretório da task; **o valor de retorno é descartado**
   (`:79`). `load_static_data` chama `read_static_analysis_files(results_dir, apk_name)` — **sem
   chave** (INV-ANA-61);
3. **reconstrução no resume** (`result_processor.py:245-325`), que re-parseia a partir do diretório
   do logcat.

**Um JSON de análise vazio passa como sucesso.** `StaticAnalysisData` é um modelo Pydantic sem
`__bool__`/`__len__`, então o teste `if static_data:` (`components/static_analysis.py:139`) é
**sempre verdadeiro**; o componente loga "Static analysis completed" e devolve `True`. O único
caminho que contabiliza o vazio é o do resume (`result_processor.py:314-322`), e ele atribui a causa
errada (JSON não resolvido, não denominador vazio).

### 2.5 Pós-processamento — as colunas exatas

| Artefato | Colunas | Observação |
|---|---|---|
| `coverage.csv` | 15: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target` (`result_processor.py:429-447`) | `cov_act`/`cov_method`/`cov_rv_method` são **progressivas**; as demais constantes na linha |
| `errors.csv` | 13, constante `ERRORS_CSV_COLUMNS` (`:47-61`) | `unique_msg` é **lido**, nunca reconstruído |
| `summary.csv` | 12: `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target, mop_errors_total, mop_errors_unique` (`:847-862`) | uma linha por task |
| `app_events.csv` | 15 (`:737-755`) | só o `stack_head` |
| `performance.csv` | 7 no caminho normal (`performance_processor.py:84-94`), **8 no fallback** (`result_processor.py:1150-1161`) | dois esquemas |
| `results.json` | hierarquia `apk → rep → timeout → tool` (`:957-975`) | |

**Nenhum publica um denominador. Nenhum publica procedência** (variante de instrumentação, conjunto
de specs, chave de escopo).

### 2.6 Resume e checksum

Identidade da task não inclui o checksum, e o checksum é calculado sobre o `PlatformConfig`
(`platform.py:167` → `task_storage.py:58-89`). Ficam **de fora**: `specification_set`,
`instrumentation_variant`, `custom_specs_dir`, `enable_quarantine`, `generate_monitors`,
`instrument_apks`, `run_static_analysis`, `analysis_timeout`. Trocar de conjunto de specs ou de
tecelão e retomar **não gera nem o aviso** — a divergência quando existe é logada em DEBUG
(`task_storage.py:947-953`) e o aviso ao usuário nunca bloqueia (`platform.py:293-304`).

Só `COMPLETED` é pulado; registros em `ERROR` re-executam, e o store **acrescenta** (chave =
`task.id`, novo a cada run), então após uma recuperação a mesma identidade tem dois registros.
Análise a jusante precisa contar por identidade, não por registro.

---

## 3. A chave de escopo — o elo que as campanhas contornaram à mão

### 3.1 O fato do corpus: os APKs são de debug

`rvsec-dataset` constrói os APKs a partir do fonte com `assembleDebug`, sempre e por decisão
registrada (`rvsec-dataset/src/rvsec_dataset/build/builder.py:154-160`: *"The debug assemble task.
Always the aggregate `assembleDebug`"*), e **não faz nenhuma tentativa de neutralizar o
`applicationIdSuffix`** — as duas únicas ocorrências do termo no repositório estão em código de
*medição*, não de build (`src/rvsec_dataset/pkgdet_validation/metrics.py:50,89-102`).

O `applicationIdSuffix` do Gradle acrescenta um segmento ao **applicationId** sem tocar no
**namespace das classes**. Censo sobre os artefatos reais:

| Divergência entre o package do manifesto e o do nome do arquivo | 20260706 (219) | FINAL_selected162 (162) |
|---|---:|---:|
| nenhuma | 108 | 87 |
| `.debug` | 72 | 60 |
| `.dev` | 9 | 7 |
| `.beta` | 4 | 4 |
| `.staging` | 2 | 0 |
| `.current` | 1 | 1 |
| `.BETA` (caixa alta) | 1 | 1 |
| `.qa.debug` (composto) | 1 | 1 |
| `.beta2` | 1 | 0 |
| `.trial` | 1 | 0 |
| `.debug.HEAD` | 1 | 0 |
| `vip` (**sem ponto**) | 1 | 0 |
| package inteiramente outro | 17 | 1 |
| **total divergente** | **111** | **75** |

Três casos que qualificam a ideia de "lista de sufixos", todos com âncora no fonte comitado sob
`rvsec-dataset/repos/`:

- **`com.learntube.app`** → manifesto `com.learntube.app.debug.HEAD`. O `build.gradle.kts:66` faz
  `applicationIdSuffix = ".debug.$normalizedWorkingBranch"` — **o sufixo é o nome do branch git no
  momento do build**. O espaço de sufixos é aberto por construção; nenhuma lista estática o enumera.
- **`de.saschahlusiak.freebloks`** → `de.saschahlusiak.freebloksvip`. Não é sufixo: é o
  `applicationId` de outro *product flavor* (`app/build.gradle.kts:31`), e nem sequer é um segmento
  pontilhado.
- **13 APKs distintos com o mesmo package**: os apps `info.metadude.*.schedule` (mais o
  `ch.digitale_gesellschaft.winterkongress.schedule`) são 13 entradas F-Droid apontando para **um
  repositório** com um flavor por conferência (`app/build.gradle:119`); `assembleDebug` produziu o
  mesmo flavor `congress` para todos, e os 13 manifestos dizem
  `info.metadude.android.congress.schedule.debug`. Qualquer indexação por `package` os funde.

### 3.2 O que o código faz com isso

`App.code_package` devolve `package_name` **verbatim** quando `package_detector` é falso, e o default
é falso (`domain/app.py:130-150`, `:62-68`). A recusa a normalizar é deliberada e está escrita:

> *"The declared value is returned verbatim: build-type suffix stripping and prefix repair are
> properties of a particular corpus and belong to whoever curates it."* — `domain/app.py:141-144`

A decisão é defensável. O problema é que **não há por onde o curador entregar a resposta**: o único
parâmetro é o booleano `package_detector`; nenhuma CLI aceita uma chave.

O valor atravessa até o Java sem alteração: `static_analysis.py:270-276` →
`rv-static-analysis/config.py:393-397` (`-clientParam codePackage=`) →
`RvsecAnalysisClient.java:90` (`filterPackage = codePackage != null ? codePackage : manifestPackage`)
→ `isAppClass` (`:278-286`):

```java
static boolean isAppClass(String className, String filterPackage) {
    if (!className.startsWith(filterPackage)) { return false; }
    ...
}
```

`startsWith` **cru, sem fronteira de ponto**. Duas consequências, em direções opostas:

- com a chave sufixada, `app.foo.bar.debug` não é prefixo de `app.foo.bar.X` → **zero classes**;
- com a chave certa, `com.foo` é prefixo de `com.foobar.X` → **classes de outro pacote entram**.

### 3.3 A medição: o que aconteceria hoje

Para cada artefato, testei se a chave é prefixo (com fronteira de ponto) de **100%** das classes de
`reachability` — o membro que o GATOR escreve *depois* de aplicar o filtro:

| diretório | n | manifesto cru cobre 100% | `Mneut` cobre 100% |
|---|---:|---:|---:|
| `APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162` | 162 | **87** | **162** |
| `..._experimento-20260706_selected163` | 163 | 87 | **163** |
| `..._experimento-20260706` | 219 | 99 | 179 |
| `..._experimento-20260706_selected181` | 181 | 83 | 147 |
| `APKS_INSTRUMENTED_jca_ajc_comp162ajc_staging` | 106 | 61 | **106** |
| `APKS_INSTRUMENTED_jca_ajc_comp162ajc_selected41` | 41 | 25 | **41** |

**Ressalva metodológica sobre este teste.** "`Mneut` cobre 100%" não é, sozinho, prova de que o
artefato foi escopado por `Mneut`: como `Mneut` é prefixo da chave sufixada, um artefato escopado
pelo sufixo (um **resíduo**) também passaria. O teste discriminante é outro — *existe alguma classe
sob o prefixo sufixado?* — e a resposta é categórica:

```
FINAL_selected162      : 75 com sufixo no manifesto,  0 com qualquer classe sob o prefixo sufixado
ajc_comp162ajc_staging : 45 com sufixo,               0
experimento-20260706   : 111 com sufixo,              0
```

**0 de 231.** Nenhum artefato do acervo foi escopado pela chave sufixada. Registro isto porque a nota
`experimento-comp162-ajc/analise_previa/20260813_checks_offline_75.md:82-101` atribui ao sufixo o
baixo casamento de alguns APKs (*"o GATOR foi escopado por ele"*, com `com.nononsenseapps.feeder.play`
casando 17 de 6.481 linhas) — a **atribuição é refutada pelos artefatos**: as 6 classes daquele
artefato são `com.nononsenseapps.feeder.ui.*`, não `…feeder.debug.*`. O baixo casamento é real; a
causa é outra, e está em §4.3.

**Rodar a análise estática de dentro do `rv-experiment` hoje, no corpus do artigo, produziria
denominador vazio em 75 de 162 APKs (46,3%).** E produziria em silêncio:

| ponto | o que acontece com denominador vazio |
|---|---|
| `RvsecAnalysisClient` | imprime `[RvsecAnalysisClient] Filtered N classes … using package: X` em stdout (`:267-268`) — ninguém lê |
| `StaticAnalyzer._run_analysis` | única pós-condição é "o arquivo existe" (`static_analysis.py:283-289`); `reachability: []` com `complete: true` passa |
| `result.success` | permanece `True` |
| `StaticAnalysisComponent` | `if static_data:` é sempre verdadeiro (`:139`) → "Static analysis completed" |
| `CoverageMetrics._percentage` | devolve `0.0` quando `total == 0` (`domain/coverage.py:446-449`) |
| `LogcatRepository.diagnose()` | tem a checagem `"Static totals shows zero methods"` (`coverage.py:925-927`) e **só é chamado em testes** |

Resultado: seis métricas em 0,00%, indistinguível de um app que não exercitou nada.

### 3.4 A regra que as campanhas usaram, e o que ela não cobre

A regra existe, está escrita e está **no repositório do artigo**, não neste:
`ase-journal/data-analysis/mneut_scope.py:69-102` (lido diretamente, não por relato):

```python
BUILD_TYPE_DENYLIST = frozenset({"debug","dev","beta","staging","qa","nightly",
                                 "alpha","snapshot","current","head","indev"})
MIN_SEGMENTS = 2

def neutralize(application_id):
    segments = application_id.split(".")
    while len(segments) > MIN_SEGMENTS and segments[-1].lower() in BUILD_TYPE_DENYLIST:
        segments.pop()
    return ".".join(segments)
```

Três propriedades load-bearing: comparação em minúsculas (é o que trata `.BETA`), aplicação repetida
(é o que trata `.qa.debug` e `.debug.HEAD`), e — no modo de produção — casamento com **fronteira de
ponto**, `classes_under(..., dot_boundary=True)` (`:150-157`), *"sem isso `...fucksgiven` casa o app
irmão `...fucksgivenwatch.*`"*. O GATOR **não** faz essa fronteira.

O `mneut_scope.py` traz também um portão, `keep(X)` (`:75-77,180-191`): `A(X) ≠ ∅` **e**
`|A(X) ∩ G|/|G| ≥ 0,90` **e** `|A(X) \ G| = 0`. **Esse portão precisa de um oráculo que o pipeline não
tem** — `G_final`, a região de código adjudicada à mão, multi-raiz, congelada em
`dataset/pkgdet_validation/ground_truth_sheet.csv` e pinada por sha256 (`check_pins()` aborta se
divergir). Ele não é portável como está. Calibração declarada no próprio módulo (`:91-94`):
`EXPECTED_KEEP = 164`, `EXPECTED_COLLAPSE = 33`.

**E a própria implementação canônica precisa carregar um modo de compatibilidade para reproduzir
medições feitas com prefixo cru** (`:24-40,150-157`): `dot_boundary=False` existe porque **2 das
1.044 linhas** do `arms.csv` congelado só reproduzem sob `startswith` sem fronteira —
`com.jerboa_87`, cuja chave era `com.jerboa.MainActivity` (um **nome de classe**, não de pacote, que
casa as próprias inner classes e lambdas), e `rocks.poopjournal.fucksgiven_14`, cuja chave casa o
pacote irmão `…fucksgivenwatch.*`. É a mesma falta de fronteira do `isAppClass` do GATOR, com duas
testemunhas nomeadas — e explica por que `com.jerboa` cai de 50,87% para 17,75% na medição da §5.2:
a chave antiga arrastava tudo que começasse com o nome da `MainActivity`.

**A regra de sufixo não é total.** Sobre os 219:

| | 219 |
|---|---:|
| manifesto já é a raiz do código | 99 |
| a denylist resolve | 80 |
| a denylist **não basta** | **40 (18,3%)** |

Os 40 são casos em que o namespace do código não deriva do applicationId por transformação de string
nenhuma: `de.grobox.liberario` → `de.grobox.transportr`; `org.liberty.android.freeotpplus` →
`org.fedorahosted.freeotp`; `io.github.quillpad` → `org.qosp.notes`; `com.learntube.app` →
`org.schabi.newpipe` (um fork do NewPipe); os 13 `metadude` → `nerd.tuxmobil.fahrplan.congress`;
e apps multi-módulo cuja raiz é **mais ampla** que o `Mneut` (`eu.pretix.pretixscan.droid` →
`eu.pretix`; `com.sjapps.jsonlist` → `com.sjapps`).

**São exatamente os casos para os quais o `package_detector` existia.** Com o detector fora da mesa,
eles precisam de resposta — e a resposta segura não é uma lista maior, é um portão que recuse
silêncio.

### 3.5 O que já foi decidido nesta linhagem, e o que sobrou

| Change | Data | O que fez | O que deixou |
|---|---|---|---|
| **gh91** `sa-rerun-manifest-key` | 31/07 | reanalisou 30 APKs invocando o GATOR direto, com `Mneut` lido verbatim de um CSV congelado (`scripts/gh91_sa_rerun.py:279,344`), *"never from a flag"* (`:634`) | o próprio texto diz que não passou por `rv-static-analysis` porque *"whose only source for that parameter is `App.code_package`"* |
| **gh98** `manifest-package-default` | 07/08 | fixou o manifesto verbatim como default; tarefa 7.2 chegou a testar um APK com sufixo de build-type, **asserindo que a chave passa verbatim** | delegou o strip a "quem cura o corpus", sem lhe dar um canal |
| **gh102** `artifact-scoped-parse` | 16/08 | removeu o segundo filtro do parser; mediu **"75 of 162 applications parse to zero classes"** | corrigiu o lado do consumo; o lado da produção continua igual |

Os 75 do gh102 são os mesmos 75 deste censo. Três changes cercaram o mesmo defeito e nenhuma fechou
a via de produção, porque cada uma tinha um recorte legítimo que não a incluía.

### 3.6 O artefato não registra a chave que o filtrou

`JsonReportWriter.java:84` grava `"package"` = `output.getAppPackageName()` — **o manifesto**, não a
`codePackage`. `ReachabilityEnricher.topLevelMetadata()` (`ReachabilityEnricher.java:92-105`)
devolveria `{manifestPackage, codePackage, mainActivity}` e **não tem chamador em produção**.

Isto deixou de ser risco teórico e virou fato medido: nos 162 artefatos do corpus do artigo, **zero
classes começam pelo package registrado em `package`**, e **162/162 começam pelo `Mneut`**. O campo
`package` do artefato é um registro do manifesto, **não** da chave que o produziu. Do lado Python,
`StaticAnalysisResult.code_package`/`code_package_source` existem exatamente para cobrir isso
(`static_analysis.py:234-235`) — e **nada os serializa**; são logados em INFO
(`:236-243`), e `LoggingManager.setup_file_logging` (`util/logging/manager.py:153-200`) **nunca é
chamado em produção**. A chave efetiva não chega ao disco em lugar nenhum.

### 3.7 O que a chave NÃO toca — a superfície de um reparo

Verificado, e é uma boa notícia: a chave tem **um** consumidor funcional.

| Componente | Usa a chave de pacote da app? |
|---|---|
| análise estática (GATOR) | **sim** — `static_analysis.py:277` é o sítio único |
| tecelão de advice dexlib2 | **não** — deny-list de bibliotecas (`PackageFilter.java:20-61`) |
| tecelão de cobertura dexlib2 | **não** — mesma deny-list |
| instrumentação ajc | **[rev. 3] sim, e a rev. 2 errou aqui** — `ajc_instrumentation.py:854-900` usa `code_package` como guarda anti-quarentena. O próprio código registra que a guarda está **inerte exatamente nos apps sufixados** (`:858-866`) e loga WARNING (`:872-885`). O tecelão de *cobertura* do ajc não usa a chave (`Coverage.aj:22-46`); o *instrumentador* usa |
| captura de logcat | **não** — filtra por tag (`logcat_manager.py:194-212`) |
| parsing do artefato | **não** — INV-ANA-61, desde a gh102 |
| cruzamento (`coverage.py`) | **não** — usa o que veio no artefato |
| **instalação / `am start` / `pm clear` / `-p` do monkey, APE, fastbot, rv-agent** | usam **`package_name`**, com sufixo — **e está certo**: é o id que o `PackageManager` conhece |

A separação `package_name` (device) × `code_package` (escopo) está limpa em 20+ sítios; nenhum
mistura os dois.

**[rev. 3] A afirmação "superfície de uma linha funcional" está retirada.** São dois consumidores
funcionais, não um — o argv do GATOR e a guarda anti-quarentena do ajc acima. E o custo real não é
de contagem de linhas, é de **aridade**: `package_detector` é uma política *escalar de run*,
propagada aos 8 sítios `App(` sob INV-EXP-34, enquanto uma chave curada por APK exigiria mapa,
loader, política de entrada ausente e semântica de resume. É por isso que a decisão registrada em
§15.2 **não** cria canal por-APK.

Alternativas ao "lista de sufixos", avaliadas contra o que o código já tem em mãos:

| Alternativa | Viabilidade |
|---|---|
| prefixo comum de `Scene.v().getApplicationClasses()` no Java | a informação já está de graça dentro de `extractClasses`; é a resposta que o produtor pode dar sobre si mesmo |
| package da `mainActivity` do manifesto (androguard `get_main_activity()`) | barata do lado Python, já usada em `scripts/validate_instrument_jca190.py:153`; **ressalva medida**: 19 de 162 APKs declaram MAIN só em `<activity-alias>` (`scripts/e3_validate_emulator.py:26-36`) |
| denylist de sufixos | resolve 162/162 no corpus do artigo, 179/219 no amplo |
| portão de não-vacuidade | **ortogonal e obrigatório** — nenhuma das três é total |

---

## 4. Elo por elo

### 4.1 Tecelão de cobertura (RVSEC-COV) — os defeitos do tecelão de advice NÃO propagam

Verificado: a sonda é injetada na **entrada** do método (`CoverageWeaver.java:189-190`, índices 0 e
1 do prólogo), e o lado ajc também é `before()` (`Coverage.aj:53`). Um método que lança registra
cobertura nos dois — o defeito de semântica `after`/`finally`
(`docs/20260827_divergencia_after_dexlib2_ajc.md`) não tem análogo aqui.

O `coverage-weaver` também não importa `TypeResolver`/`AndroidClassIndex`/`InheritanceResolver`
(`CoverageWeaver.java:3-17`, `SignatureFormatter.java:3-5`, `PackageFilter.java:3-4`). Faz a
conversão na direção **oposta** — descritor DEX → FQN, `SignatureFormatter.java:43-69` — e preserva
o `$` por omissão deliberada. O mangle textual não existe aqui.

Formato emitido: `<FQN: Retorno nome(p1,p2)>`, vírgula sem espaço, `$` para aninhamento real,
primitivos por extenso, arrays com `[]`.

**O que existe no lugar: divergências de escopo entre os dois tecelões**, todas na direção
"dexlib2 reporta mais":

| Divergência | ajc | dexlib2 | Âncora |
|---|---|---|---|
| construtores | não emite | emite `<init>` e `<clinit>` | `Coverage.aj:50,56` vs `CoverageWeaver.java:120-135` |
| `org.apache..*` | exclui tudo | só `commons/` e `geronimo/` | `Coverage.aj:37` vs `PackageFilter.java:36-37` |
| classe `Log` de topo | exclui (`within(*..Log)`) | só sufixo `$Log;` | `Coverage.aj:45` vs `PackageFilter.java:41-43` |
| `com.android..*`, `com.sun..*`, `jakarta..*`, `libcore..*`, `br.unb.cic.mop..*`, `Coverage+` | exclui | ausentes | `Coverage.aj:25-46` |
| `kotlinx` | não exclui | exclui | `PackageFilter.java:31` — a única na direção inversa |
| sintéticos | nascem depois do weave (dex2jar→ajc→d8) | já estão no DEX de entrada | — |
| prioridade do log | `Log.v` | `Log.i` | `Coverage.aj:156` vs `CoverageSourceEmitter.java:47` |

**Medição num par controlado** (um APK do acervo em que os dois emissores rodaram no mesmo processo,
separáveis pela prioridade): ajc 135 assinaturas distintas, dexlib2 378, interseção 132,
**recall 0,9778 contra portão de 0,99**, delta +243 contra orçamento de 1,35.

- **A única causa de perda de recall medida** é a grafia de classe aninhada em posição de
  **parâmetro**: o `Coverage.aj` monta declarante e retorno por reflexão (`$`) mas parâmetros por
  `toLongString()` (`.`) — `Coverage.aj:64-65` contra `:111-117`. Atribuição confirmada por
  prioridade do log: parâmetro com `$` → 26 linhas, **todas `I`** (dexlib2); parâmetro aninhado com
  `.` → 3 linhas, **todas `V`** (ajc). Disjunção total.
- **O teste consagra a premissa errada.** `SignatureFormatterTest.java:76-82` afirma que o `$` é
  mantido *"matching the AspectJ signature template"*. O AspectJ não emite `$` em parâmetro. Nenhum
  teste hoje pode detectar essa divergência.

**Consequência para o portão.** Com o ajc fora da mesa de reparo, o `CoverageValidator` exige recall
≥ 0,99 do dexlib2 contra um emissor que ninguém vai corrigir. O portão não mede qualidade do
dexlib2 — mede uma diferença permanente. Precisa ser redefinido, não perseguido.

Achado adicional: `CoverageValidator.java:51` usa a regex `(<[^>]+>)`, que **trunca em `<init>`** —
`<com.foo.Bar: void <init>()>` vira o token `<com.foo.Bar: void <init>`. As assinaturas de
construtor entram no conjunto do dexlib2 malformadas. (O sintoma é visível a olho nu em qualquer
logcat: um `grep -o "<[^>]*>"` sobre RVSEC-COV devolve `<com.hwloc.lstopo.ZoomView.ZoomView: void
<init>` cortado no mesmo ponto.)

**Um terceiro mecanismo de zero, independente destes dois.** O `PackageFilter` do coverage-weaver
exclui `Lcom/google/`, e `com.google.android.stardroid_1678` é um app do próprio Google: ele reporta
**0% em 99 de 99 execuções** com denominador correto (705 classes, `complete: true`) e zero
violações. Está documentado em `experimento-20260706/docs/residual/ZEROCOV_STARDROID.md` e o artigo
o exclui pelo funil (`\zeroCoverageExcl`). Registro isto porque "cobertura zero" tem hoje **três**
causas distintas — denominador vazio pela chave, chave inalcançável pelo normalizador, e escopo
legítimo do tecelão — e o pipeline não distingue nenhuma delas.

### 4.2 Evento de violação (RVSEC) — a assimetria

A tag é `RVSEC`, distinta de `RVSEC-COV`, e a linha tem **sete campos posicionais separados por
vírgula** (`ErrorSummary.java:177`, emitido em `ErrorCollector.java:53`):

```
spec , classQualifiedName , className , methodName , location , errorType , expecting
```

`__LOC` **não é resolvido em runtime**: é macro substituída na geração do monitor
(`BaseMonitor.java:501-502`, `Util.java:7-8`) por `ViolationRecorder.getLineOfCode()`, visível
literal no monitor gerado (`MultiSpec_1RuntimeMonitor.java:3848`, 112 ocorrências). Em execução ela
devolve o `StackTraceElement.toString()` do primeiro frame não-monitor
(`ViolationRecorder.java:53-60,99-116`) — `classeFQN.metodo(Arquivo.java:linha)`, ou a string literal
`"(Unknown)"` se a pilha filtrada ficar vazia.

**A violação sempre carrega grafia `$`**, porque vem de `StackTraceElement` — nome binário da JVM. O
trecho que truncaria no `$` está **comentado** em `ErrorSummary.java:96-103`. Confirmado em logcat
real (`results/aperv_precal_macro/trial_85/.../org.mosad.seil0.projectlaogai_6000.apk__1__600__aperv:sata_mop.logcat:507`):

```
V RVSEC : KeyStoreSpec,com.google.crypto.tink.integration.android.AndroidKeystoreKmsClient$Builder,
          AndroidKeystoreKmsClient$Builder,<init>,Unknown Source:1,InvalidSequenceOfMethodCalls,unknown
```

**E aqui está a assimetria que fecha a cadeia: o elo de violação NÃO cruza com a análise estática.**
Lado a lado, no mesmo arquivo:

```python
def register_method_call(...):        # coverage.py:640-674  — DOIS portões estáticos
    class_data = self.get_class(class_name)
    if not class_data: ...debug...; return
    if signature in class_data.methods: ...
    else: ...debug...

def register_rv_error(self, error_log):   # coverage.py:676-688  — NENHUM portão
    self.errors.append(error_log)
    self.unique_errors.add(error_log.unique_msg)
```

Duas instruções, sem `get_class`, sem teste de pertinência, sem reachability. E as violações são
contadas **antes** do early-return de classes vazias (`coverage.py:733-748`). O
`result_processor.py:632-638` declara isso como projeto: *"errors.csv: reconstructible from logcat /
coverage.csv: NOT reconstructible (needs static analysis class list)"*.

**Consequência**: os dois elos erram em direções contrárias:

| | cobertura | violação |
|---|---|---|
| filtro contra a estática | dois portões | nenhum |
| erro possível | **perde** o que é da app | **aceita** o que não é |
| visibilidade | `logger.debug` sem contador | nenhuma — entra na contagem |

O exemplo acima é exatamente isso: o APK da task é `org.mosad.seil0.projectlaogai`, um app de
horários escolares, e a violação acusada é de `com.google.crypto.tink…` — biblioteca. A linha vai
para `errors.csv` com `apk = org.mosad.seil0.projectlaogai_6000.apk` na coluna 0
(`result_processor.py:673`), sem que `class_full_name` seja comparado com o pacote em momento algum.

**A atribuição ao APK é posicional, por task, nunca por nome** — e a captura de logcat filtra **só
por tag**, não por pid nem por pacote (`logcat_manager.py:194-212`:
`adb logcat -v threadtime -s RVSEC:V RVSEC-COV:V APERV-HEARTBEAT:V`). Qualquer processo do
dispositivo que emita sob `RVSEC` tem suas violações gravadas no `.logcat` da task corrente. A
limpeza de buffer no início (`clear_buffer_on_start=True`) mitiga, não elimina.

**Um terceiro defeito neste elo**, de família diferente: o split classe/método é feito por **último
ponto** depois de remover o sufixo `(arquivo:linha)` — do lado Java (`ErrorDescription.java:128-146`)
e replicado do lado Python (`logcat_parser.py:52-97`). Quando o regex não casa, o fallback **copia o
frame inteiro nos três campos**. Real, com âncora
(`results/gh56-smoke6/net.ibbaa.keepitup_19.apk/…__1__300__ape.logcat:1448`): uma classe sintética
R8 (`SystemActivity$$ExternalSyntheticLambda7`) faz a posição-fonte entrar dentro do nome de classe
e de método — e a chave de identidade `(class, method, spec, code, event, message)`
(`log.py:157-160`) é montada sobre esses campos corrompidos. Há caso análogo com o campo 3 saindo
como literalmente `kt:83)`; esse não tem efeito prático porque o Python ignora o campo 3
(`logcat_parser.py:576` lê os campos 2 e 4).

### 4.3 Análise estática (GATOR) — o denominador

**O GATOR escreve corretamente.** `RvsecAnalysisClient.java:1325` grava `cls.getName()` do Soot. Nos
artefatos reais: `$` sempre em aninhamento genuíno; `.` sempre em fronteira de pacote. Assinatura
completa com tipos de parâmetro qualificados:

```
<com.hwloc.lstopo.ZoomView.ZoomView$ZoomViewListener: void onZoomStarted(float,float,float)>
<...TableListAdapter: void onBindViewHolder(android.support.v7.widget.RecyclerView$ViewHolder,int)>
```

**[rev. 5] De onde vem o `libPackages.txt`, e por que ele erra aqui.** O arquivo é upstream do
GATOR, herdado por cadeia de forks registrada em `sootandroid/README.md`: GATOR (Ohio State
University, 2014-2019, Rountev/Dacong Yan) → `limerick1718/Gator` (commit `4b2fb94d`) →
`phtcosta/Gator` (commit `b11acb7d`) → `rvsec-gator`. Entrou no commit `d94e33cc` *"starting
rvsec-gator"* (25/09/2024), o import inicial, e **`git log --follow` sobre ele devolve esse único
commit** — nunca foi aberto nem editado aqui. As duas cópias (`sootandroid/` e a que o script
realmente usa, `rv-android/lib/gator/`) são idênticas byte a byte (md5 `9296d262…`).

**Ele é opcional, e o default do GATOR são dois padrões**: `AnalysisEntrypoint.java:77-82` cai em
`android.support.*` + `com.google.android.gms.*` quando a lista está vazia. Os 2.170 só existem
porque `rv-android/lib/gator/gator:95` passa `-libraryPackageListFile` **incondicionalmente** — não
há flag para desligar, e o grep no `rv-android` inteiro devolve essa única linha.

**A finalidade original não era medir.** O GATOR é um analisador de GUI: o par aplicação/biblioteca
existe para escopar a varredura de `hier.appClasses` que o `FlowgraphRebuilder`, o `WTGHelper` e o
`GatorIntentAnalysis` fazem. Nesse papel, **falso positivo custa precisão**, não número — rebaixar
uma classe do app por engano tira um pouco de análise de GUI e ninguém publica isso. O conteúdo
confirma a finalidade: `butterknife.internal.*`, `dagger.shaded.*`, `com.bumptech.*`,
`com.squareup.*`, `io.reactivex.*`, `yuku.ambilwarna.*`, `aQute.libg.*` — nomes de pacote de
bibliotecas Android de terceiros, com subpacotes internos, vocabulário de meados dos anos 2010.

**O defeito é mudança de finalidade sem reautorização.** O `RvsecAnalysisClient` faz
`Scene.v().getApplicationClasses()` (`:270`) e usa o resultado como **denominador de uma métrica
publicada**. No papel novo o falso positivo deixou de custar precisão e passou a custar erro de
medição. E aí a lista, defensável no papel antigo, fica indefensável: `com.github.*` é o namespace
do JitPack, `io.github.*` é o do OSSRH para usuários do GitHub, `br.com.*` e `uk.org.*` são group
ids de domínio reverso. Como heurística de "isto veio de um repositório Maven" faz sentido; só que
são exatamente os namespaces que apps de código aberto usam **para si mesmos**. A lista confunde
"namespace onde bibliotecas são publicadas" com "namespace que é biblioteca". Some-se a isso 127
padrões de um segmento só (`c.*`, `a.a.*`, `domain.*`, `flow.*` — saída típica de ProGuard) contra
2.043 de dois.

**Duas notas mecânicas.** O casamento de `Configs.isLibraryClass` (`:176-186`) faz
`className.startsWith(pkg.substring(0, len-1))`, e como todo padrão termina em `.*` o ponto final é
preservado — a denylist **tem** fronteira de ponto. Dentro do mesmo laço, portanto, a lista casa com
fronteira e a guarda de `:119` casa com `startsWith` cru: a frouxa é a que protege. E
`Configs.processLibraryPkgFile` (`:188-204`) engole toda exceção num `catch (Exception e) {}` vazio
— se o arquivo sumir, a lista fica vazia, o default de dois padrões assume, e a análise segue sem
dizer nada, com denominador **inflado** em vez de colapsado. Mesma família de silêncio.

**O artefato tem sete chaves, invariantes em 381 artefatos**: `package`, `mainActivity`,
`components`, `reachability`, `windows`, `transitions`, `complete` — nesta ordem, zero variação.
`reachability` é 76–78% dos bytes e é o denominador. `complete: true` em 219/219, 162/162 e nos 30
`.pkgdet`; **nenhum artefato incompleto no corpus**. `transitions` vazio em **83/219 (37,9%)** — os
30 do gh91 por construção (`skipWtg=true`, `SA_RERUN_gh91/REGISTRO.md`), e os outros 53 sem causa
decidível pelos artefatos, porque WTG genuinamente vazio e exceção no `WTGBuilder` gravam a mesma
coisa. Os `.apk.json.pkgdet` (30, só no diretório de 219) são os **antecessores** preservados pelo
gh91.

**"Alcança MOP" transitivo é vácuo, e é o critério que o nome sugere.** Há três predicados por
método, escritos em `RvsecAnalysisClient.java:1349-1351` a partir de `ReachabilityEngine.run()`:
`reachable` (BFS para frente dos entry points), `reachesTarget` (BFS no grafo **reverso** a partir dos
alvos — transitivo) e `directlyReachesTarget` (call site direto, com varredura de bytecode
complementar por BUG-INV-ANA-19). Medido:

| critério | 219 | 162 |
|---|---:|---:|
| `reachesTarget ≥ 1` | **219/219 (100%)** | **162/162 (100%)** |
| `directlyReachesTarget ≥ 1` | **94/219 (42,9%)** | 75/162 (46,3%) |
| mediana do % de métodos com `reachesTarget` | 27,1% | 25,5% |
| soma de `directlyReachesTarget` no corpus | **469 métodos** | 398 |

O BFS reverso a partir de uma API JCA alcança quase todo o grafo: o critério é satisfeito por 100% do
corpus e por ~27% de **todos** os métodos. O critério com poder discriminante é
`directlyReachesTarget` — e **125 de 219 artefatos (57%) não têm um único call site direto** para API
monitorada. Isto importa para `cov_reaches_target` (coluna medida) e para qualquer leitura de "quanto do
que alcança MOP foi exercitado".

**Correção à rev. 1.** A rev. 1 dizia: *"Package mismatch não se manifesta neste corpus: 0 artefatos
com zero classes ou zero métodos"*. A medição está certa e a leitura estava errada. Não se manifesta
porque **a chave foi neutralizada à mão, fora do pipeline** (§3). Rodando de dentro do
`rv-experiment`, 75 de 162 artefatos teriam zero classes. O "0 artefatos com zero classes" é
evidência de que o contorno manual funcionou, não de que o problema não existe.

**Multi-package persiste, e o sintoma foi trocado por silêncio.** Cobertura > 100% é
estruturalmente impossível hoje, porque o numerador é interseção com o denominador
(`coverage.py:656-673`) — verifiquei: **0 de 21.681 linhas** de `summary_all.csv` passam de 100% em
qualquer das seis métricas. O sinal que denunciava o problema em 2025 desapareceu; o problema, não.

**O sintoma novo é a saturação, e ela já ocorreu.** No corpus do artigo:

| APK | classes no denominador | `cov_class` mediano | `cov_method` mediano |
|---|---:|---:|---:|
| `br.com.colman.petals_3040000` | **1** | **100,00** | 71,43 |
| `com.github.livingwithhippos.unchained_60` | **2** | **100,00** | 44,44 |
| `com.nononsenseapps.feeder.play_4025` | 6 | 16,67 | 16,52 |
| `com.tananaev.passportreader_22` | 18 | 61,11 | 44,16 |
| `com.github.cvzi.screenshottile_148` | 21 | 14,29 | 12,18 |
| `org.cry.otp_31` | 23 | 39,13 | 22,68 |
| *(mediana do corpus)* | **671** | | |

Seis APKs têm ≤30 classes, dezesseis têm ≤100, e a mediana é 671. Os dois primeiros publicam
`cov_class = 100,00%` sobre uma e duas classes. É o modo de falha espelhado do zero: um denominador
degenerado **infla** a métrica, e nada o sinaliza. `cov_class == 100%` ocorre em 186 linhas / 2 APKs;
`cov_act == 100%` em 6.540 linhas / 97 APKs.

#### A quarta causa: o denominador colapsa no rebaixamento do GATOR — não na chave, não no Soot

*[rev. 4] Mecanismo determinado e reproduzido ao vivo. O relatório completo é
`docs/20260828_d9_colapso_denominador.md`; esta subseção traz o essencial e a correção do que a
rev. 2 supunha.*

Esta é a causa que a rev. 1 não tinha. **A chave desses artefatos está correta**, e há log que prova:
`SA_RERUN_gh91/logs/br.com.colman.petals_3040000.apk.log:508-521`, verbatim —

```
[STAT] Processed classes: 3711
[STAT] Processed methods: 14991
[RvsecAnalysisClient] Code package: br.com.colman.petals
[RvsecAnalysisClient] Manifest package: br.com.colman.petals.debug
[RvsecAnalysisClient] Filter package: br.com.colman.petals      ← a chave está certa
[RvsecAnalysisClient] Filtered 3710 classes (libraries/generated) using package: br.com.colman.petals
[RvsecAnalysisClient] Application classes: 1
```

O APK define **36.800 classes em 18 arquivos DEX** (`class_defs_size` lido dos cabeçalhos), e **551
classes distintas sob `br.com.colman.*` foram executadas** numa única corrida de 300 s.

As classes que sobram nos artefatos colapsados são **exatamente os componentes declarados no
manifesto**: `petals` → 1 `MainActivity`; `unchained` → 2 activities; `feeder.play` → 6 activities;
`screenshottile` → 21 activities. Não é um subconjunto aleatório — e a rev. 4 explica por quê.

**E é uma propriedade da análise estática, não do tecelão nem da chave**: os mesmos quatro APKs
colapsam com **os mesmos números** nos artefatos dexlib2 e nos ajc:

| APK | classes (dexlib2/162) | classes (ajc/106) |
|---|---:|---:|
| `br.com.colman.petals_3040000` | 1 | 1 |
| `com.github.livingwithhippos.unchained_60` | 2 | 2 |
| `com.nononsenseapps.feeder.play_4025` | 6 | 6 |
| `com.github.cvzi.screenshottile_148` | 21 | 21 |

**[rev. 4] O mecanismo, determinado.** O Soot carrega **todas** as 36.800 classes dos 18 DEX e marca
**todas** como classes de aplicação. Quem colapsa o denominador é o próprio GATOR, no laço de
`AnalysisEntrypoint.java:111-126`, que roda antes do cliente:

```java
if (activityNames.contains(c.getName())) { ... setApplicationClass(); continue; }  // :112 resgate
if (c.getName().startsWith(appPkg))                                    continue;   // :119 A GUARDA
if (Configs.isLibraryClass(c.getName())) { ... c.setLibraryClass(); }              // :121 rebaixa
```

`appPkg` é o pacote do **manifesto** (`:87-94`, verbatim, sem neutralização): `br.com.colman.petals.debug`.
Nenhuma classe compilada do app começa com esse prefixo, a guarda de `:119` nunca dispara, e o padrão
`br.com.*` — presente em `lib/gator/libPackages.txt` — rebaixa **33.089** classes a biblioteca.
Sobram 3.711 classes de aplicação e **uma** sob o prefixo do app: a `MainActivity`, devolvida pelo
ramo de resgate de `:112`, que só conhece `<activity>`. É por isso que os sobreviventes são os
componentes do manifesto, e é por isso que os *receivers* e *services* do próprio app (por exemplo
`br.com.colman.petals.widgets.AddLastUseWidgetReciever`) **não** estão nos artefatos.

O colapso exige **duas** condições simultâneas: a guarda morta (sufixo de build-type no
`applicationId`) **e** o pacote de código do app sob um padrão de `libPackages.txt`. Sobre os 162,
essa conjunção seleciona exatamente os quatro colapsados, sem falso positivo nem falso negativo;
`app.pachli` é a testemunha do contrário (mesmo sufixo, guarda igualmente morta, mas não casa a
lista — e não colapsa).

**A mesma corrida tem duas chaves de escopo.** O `RvsecAnalysisClient` prefere o `codePackage`
(`RvsecAnalysisClient.java:86-90`); o `AnalysisEntrypoint`, que decide o que existe para o cliente
filtrar, usa o manifesto sem alternativa. É por isso que o contorno manual das campanhas — passar
`codePackage=` na linha de comando — **não podia** reparar isto: ele conserta o filtro do cliente e
não toca a guarda que já esvaziou a `Scene`.

**A hipótese multidex da rev. 2 está morta, e por razão mais forte do que a medição sugeria.**
`set_process_multiple_dex` **não existe no Soot 4.7.1** — a string `multiple_dex` não aparece em
nenhum dos 2.759 `.class` do pacote `soot/` do jar, e `soot.dexpler.DexFileProvider.acceptFile` é
literalmente `{ return true; }`. A ausência da chamada na árvore do `rvsec-gator` não é defeito: é
uma opção que não existe mais. A sonda confirma na prática (`app=36800`). **Corrige-se aqui a
observação da rev. 2 sobre os cinco usos de `Options.v()`**: ela é factualmente certa e não tem
consequência nenhuma.

**Achado lateral [rev. 4]:** os três `-exclude` de `Main.java:225-227` (`kotlin.`, `kotlinx.`,
`androidx.compose.`) são **inertes** — `soot.Scene.isExcluded` só faz prefixo quando o padrão termina
em `.*`. Diferencial medido no `petals`: 36.800 classes de aplicação com os padrões atuais, 12.842
com `.*`. Configuração morta, **registrada e não reparada** (mexer nela muda medição).

**Escala.** No corpus de 219, 9 artefatos têm ≤25 classes; e o funil do artigo classifica **33 apps**
como `denominator_collapse` (`ase-journal/data-analysis/stage_denominator_scope.py:26-38`). **[rev. 4]
São coisas diferentes, e a rev. 2 as confundia**: o funil é calculado *offline* sobre as classes
compiladas do APK (`mneut_scope.py:150-158`, a partir de `dex_classes.zip`) e o artefato do GATOR não
entra nessa conta — o funil mede a qualidade da *chave*, este defeito é da *classificação* posterior.
Medido sobre os 219 executados, a conjunção das duas condições com denominador não-vazio dá
**exatamente 4**, e todos os quatro estão `selected`: **petals, unchained, feeder.play e
screenshottile sobreviveram ao funil e estão nos 163 do artigo** (§6.2 explica por quê). Nenhum dos
55 excluídos volta por causa deste reparo.

### 4.4 O cruzamento — o único elo sem contabilidade

`LogcatRepository.register_method_call` (`coverage.py:640-674`) é o ponto único, e faz **igualdade
literal de string** em duas etapas, com dois descartes silenciosos:

```python
class_data = self.get_class(class_name)
if not class_data:
    self.logger.debug(f"Ignoring method call for unknown class: {class_name}")   # :660
    return
if signature in class_data.methods: ...
else:
    self.logger.debug(f"Ignoring method call not found in static analysis: ...")  # :672
```

Ambos em `DEBUG`, **nenhum incrementa contador algum** — e, como `setup_file_logging` nunca é chamado
em produção (`util/logging/manager.py:153-200`), nem o DEBUG existe em disco.

O `ParserDiagnostics` (`coverage.py:453-521`) tem 13 contadores e fecha uma aritmética séria
(INV-ANA-62: "registros registrados mais linhas contadas é igual a linhas lidas") — mas todos são de
**parsing**. Uma linha bem formada que vira `RvCoverageLog` e é descartada dois quadros de pilha
depois conta como *registro registrado*: fica do lado certo da aritmética e some sem rastro. **A
contabilidade fecha e a cobertura está errada.**

#### O número que ninguém conta, agora medido

Varredura de **22 APKs × todos os seus logcats = 11.598.621 linhas `RVSEC-COV`**, comparando cada
assinatura distinta contra o `signature` do denominador, por igualdade literal:

| | valor |
|---|---|
| assinaturas distintas lidas | 170.131 |
| **sem correspondente literal no denominador** | **87.761 (51,6%)** |
| taxa por APK | mín. **17,67%** · mediana **59,95%** · máx. **99,82%** |
| ponderada por linha executada | mediana **64,38%** |
| classes vistas no logcat ausentes de `reachability` | **21.422 de 45.365 (47,2%)** |
| assinaturas que a regex de produção não parseia | **0** em 11,6 milhões de linhas |

O formato nunca é o problema. O problema é de conjunto. E a decomposição separa duas causas
qualitativamente diferentes:

- **fora do escopo declarado — 82.064 (95%)**: classes de biblioteca que o tecelão instrumentou e que
  o denominador nunca conteve (`coil3.BitmapImage`, `app.cash.sqldelight…`,
  `com.amulyakhare.textdrawable…`). É *por desenho* — e significa que numerador e denominador vivem
  em universos diferentes: **mais da metade dos eventos observados jamais pode entrar em taxa de
  cobertura nenhuma**, e essa perda não aparece em contador algum;
- **dentro do escopo declarado — 4.212 (5%)**: o defeito puro, e a distribuição é **bimodal**. Nos
  APKs saudáveis a lacuna é de **1 ou 2 assinaturas**, sempre as mesmas — `<…BuildConfig: void
  <clinit>()>` e `<…R$styleable: void <clinit>()>`, que o `isAppClass` exclui de propósito
  (`RvsecAnalysisClient.java:283-285`) e que o instrumentador tece assim mesmo. Nos colapsados a
  lacuna é de três ordens de grandeza: **petals 1.908, unchained 1.348, screenshottile 936** —
  4.192 dos 4.212, ou **99,5%**, concentrados em três artefatos.

`com.github.cvzi.screenshottile_148` é o caso mais limpo do acervo: **zero** falhas por biblioteca e
**936** por lacuna do denominador — 84,5% de não-casamento com culpa inteiramente da análise
estática.

Um contador de "evento válido rejeitado pelo denominador", separado em *fora-de-escopo* ×
*dentro-do-escopo*, é a instrumentação mínima que falta. O segundo desses dois números é o que
distingue "o app não usou" de "a análise não viu".

#### O denominador que executou não é o denominador de hoje

Em 4 dos 22 APKs varridos, o `<apk>.apk.json` **co-locado no diretório de resultados** (o que
acompanhou a execução) difere do que está no diretório plano de artefatos:

| APK | taxa de não-casamento contra o co-locado | contra o atual | Δ |
|---|---:|---:|---:|
| `org.wikipedia_50595` | **93,17%** | **43,06%** | −50,1 pp |
| `app.pachli_50` | 89,40% | 82,56% | −6,8 pp |
| `ch.rmy.android.http_shortcuts` | 29,15% | 30,90% | +1,8 pp |
| `com.antony.muzei.pixiv` | 90,36% | 90,39% | +0,03 pp |

Em `org.wikipedia`, o denominador que acompanhou a execução tinha 1.139 classes / 4.890 métodos; o
atual tem 7.987 / 39.950 — a corrida original mediu cobertura contra um universo que ignorava 86%
dos métodos do app. Os dois arquivos são **indistinguíveis por inspeção** (§3.6).

Duas consequências práticas. Primeira: **preservar os `.apk.json` co-locados**, porque são a única
testemunha de contra qual denominador um número foi computado. Segunda: os CSVs consolidados de topo
(`RESULTS/summary_all.csv`) foram regenerados em 31/07 contra o diretório plano — os
`*_pre_gh91.csv` são a fotografia do denominador antigo, e a diferença entre os dois é exatamente a
medição da §5.2.

### 4.5 A granularidade — a régua é grossa de um lado e fina do outro

A hipótese de partida era: *"o analisador estático mapeia os métodos MOP até o nome, não usa a
assinatura completa, aceitando todas as sobrecargas; e a mesma coisa acontece com `__LOC`"*. **As
duas metades estão certas.** A conclusão que costuma acompanhá-las — "logo a cadeia inteira é
granular por nome" — **é falsa**, e é o achado desta seção.

| elo | granularidade real | âncora |
|---|---|---|
| semeadura do alvo MOP (GATOR) | **nome** | `TargetResolver.java:53-59` |
| scan de bytecode (complemento de `directlyReachesTarget`) | **nome** (`class#method`) | `RvsecAnalysisClient.java:583-586,624-626` |
| **denominador** | **assinatura completa** | `classes.py:435-441`, `coverage.py:275` |
| **numerador** (RVSEC-COV) | **assinatura completa** | `SignatureFormatter.java:27-40`, `logcat_parser.py:695-702` |
| violação (RVSEC / `__LOC`) | **nome**, e nem isso com garantia | `ViolationRecorder.java:53-60`, `ErrorDescription.java:128-146` |
| `coverage.csv` | publica `class`, `method` **e** `signature` | `result_processor.py:436-438` |
| `errors.csv` | publica `class`, `method`, **sem `signature`** | `result_processor.py:47-61` |

Verifiquei os quatro sítios decisivos na fonte:

```java
// MopSpecsTargetSource.java:34-39 — LENIENT hard-coded, para TODO alvo, sem condição
targets.add(new TargetMethod(m.getClassName(), m.getName(), m.getParameters(),
                             m.getSignature(), TargetMethod.MatchPolicy.LENIENT));

// TargetResolver.java:52-59 — compara FQN + nome; LENIENT aceita sem olhar parâmetro
if (!t.getClassName().equals(fqn) || !t.getMethodName().equals(name)) continue;
if (t.getPolicy() == TargetMethod.MatchPolicy.LENIENT) { resolved.add(method); break; }
```

```python
# classes.py:437  — a chave do denominador é a assinatura
self.methods[method.signature] = method
# classes.py:128-150 — Method.__eq__/__hash__ usam SÓ a assinatura
# coverage.py:665 — e o cruzamento testa a assinatura
if signature in class_data.methods:
```

`Method.name` sobrevive como campo e **nunca é chave em lugar nenhum**.

**Existe política estrita, e ela é inalcançável pelo caminho MOP.** `paramsMatch`
(`TargetResolver.java:71-84`) compara tipo a tipo, funciona, e não é atingível: `STRICT` só nasce de
`SignatureFileTargetSource`, escolhida por `targetsFile != null` (`RvsecAnalysisClient.java:118`), e o
`rv-static-analysis` nunca passa `-clientParam targetsFile=`. O contrato é declarado
(`TargetResolver.java:17-18`, INV-ANA-35) e testado (`MopSpecsParityTest.java:85`).

E o complemento por scan de bytecode — que é quem produz `directlyReachesTarget` — **é name-granular
por construção e irreparável**: o javadoc `:571-574` diz que `methodRef` sozinho não reconstrói a
assinatura Soot no sítio de chamada. Ligar STRICT amanhã não o alcançaria.

#### O quanto isso vale, medido

| conjunto | `.mop` | `Loaded N MOP signatures` | pares `(classe, método)` | colapso | pares `new` **mortos** |
|---|---:|---:|---:|---:|---:|
| `jca` | 23 | 120 | **68** | 1,765× | **11** |
| `jca_android` | 48 | 207 | **113** | 1,832× | **27** |
| `generic` | 118 | 296 | 284 | 1,042× | 46 |

*(O log real do GATOR corrobora: `Loaded 120 MOP signatures` seguido de `MOP methods resolved: 76` —
68 pares que se expandem em 76 `SootMethod` por sobrecarga,
`SA_RERUN_gh91/logs/br.com.colman.petals_3040000.apk.log:522-524`.)*

**Os pares `new` são mortos** porque `SootMethod.getName()` de construtor é `<init>` e o
`TargetResolver` compara strings. A régua publicada **nunca contou sítio de chamada de construtor** —
e `SecretKeySpec.new`, `IvParameterSpec.new`, `PBEKeySpec.new` são dos alvos JCA mais comuns em app
real. Isso é 11 de 68 no `jca`, o conjunto das campanhas publicadas.

**Inflação do LENIENT**, contra o `android.jar` API 30: `jca` 141 sobrecargas casadas pelo pointcut
contra 158 aceitas → **1,121×** (17 extras em 13 pares); `jca_android` **1,072×**. Casos concretos:
`KeyStore.getInstance` casa 1 de 5 e o LENIENT acrescenta quatro; `Signature.initVerify` casa 2 de 4.
E o inverso: `KeyStore.getEntry`/`setEntry` casam **0 de 1** — só o LENIENT salva o alvo. E o
contexto que importa: **em 90% dos pointcuts a spec escreveu a lista de tipos** (130 de 144 no `jca`,
207 de 221 no `jca_android`); só 9,7% e 6,3% usam `..`. O GATOR joga fora uma informação que a spec
deu.

**No denominador, as sobrecargas valem 7%.** Sobre os 162 artefatos do corpus do artigo:

| | por assinatura (o que o código faz) | por `(classe, nome)` | delta |
|---|---:|---:|---:|
| `total_methods` | **1.058.685** | 982.521 | **−7,19%** |
| `total_target_methods` | 308.881 | 286.611 | **−7,21%** |
| `total_direct_target_methods` | 398 | 393 | −1,26% |

70.466 pares `(classe, nome)` têm mais de uma assinatura (146.630 métodos, 13,85%); **158 de 162
APKs** têm ao menos um; e **5.691 pares são mistos em `reachesTarget`** — algumas sobrecargas `true`,
outras `false`. O denominador preserva essa distinção; a semeadura não a tem.

No numerador o efeito é menor e existe: sobre as 20.884.554 linhas de `coverage_all.csv`, 514.323
pares `(apk, signature)` distintos contra 487.471 `(apk, class, method)` — **5,22%**.

#### Na violação, a perda de sobrecarga é pequena; o que domina é outra coisa

`__LOC` é macro de geração, não runtime (`BaseMonitor.java:501-502`, `HandlerMethod.java:45`,
`RawMonitor.java:104-105`, `Util.java:7-8`), e o que ela vira devolve
`StackTraceElement.toString()` — a JVM não guarda assinatura ali. Censo dos **300 sítios**
`new ErrorDescription(...)` das duas famílias: o terceiro argumento é **sempre exatamente** `"" +
__LOC` (jca 50/50, jca_android 250/250); nenhuma spec usa `thisJoinPoint`. Nenhum dos sete campos da
linha `RVSEC` é assinatura.

Cruzando `errors_all.csv` (165.999 linhas) com os 162 artefatos, sobre 629 triplas
`(apk, classe, método)` distintas:

| | triplas | % |
|---|---:|---:|
| classe **ausente** do denominador estático | **392** | **62,3%** |
| APK fora dos 162 | 180 | 28,6% |
| resolvível, assinatura única | 54 | 8,6% |
| **resolvível, ambígua entre sobrecargas** | **3** | **0,5%** |
| classe presente, método ausente | 0 | 0,0% |

A ambiguidade de sobrecarga é **5,26% das resolvíveis**. O que domina é a assimetria da §4.2, agora
com número: **62,3% dos sítios de violação são de classes que sequer estão no denominador**.

#### Um defeito adicional, com consequência sobre número que entrará no artigo

`UsedJcaMethodsVisitor.java:70-77` descarta em silêncio o pointcut cujo owner não está no mapa de
imports — e `:38` (`if (n.isAsterisk()) return;`) tira do mapa todo import com `*`. Consequência
medida: `RandomStringPassword.mop` contribui **zero alvos**, e portanto **todo `cov_reaches_target`
já medido foi computado sobre 22 das 23 specs do `jca`** — e voltaria a ser, na campanha nova, se o
reparo não entrar antes.

#### A assimetria, em uma frase

*Coberturas são medidas com régua de assinatura, alcance é semeado com régua de nome, e violações não
são medidas contra régua nenhuma.*

O efeito líquido do LENIENT sobre a **percentagem** de `cov_reaches_target` é indeterminado sem
rerodar o GATOR — ele infla numerador e denominador. O efeito sobre a **validade** é claro: um método
da app que só alcança uma sobrecarga que a spec nunca teceria é contado como "alcança alvo". E
`directlyReachesTarget` é o mais sensível — 398 métodos em 162 APKs, onde um único falso positivo
move 0,25%.

#### O `CLAUDE.md` do `rv-static-analysis` afirma o contrário do que o código faz

`modules/rv-static-analysis/CLAUDE.md:27` diz: *"Method granularity is `(class, method)`. **Overloads
are not distinguished anywhere**, and no analysis should assume they are. […] **Do not build a
comparison, a gate or a denominator that keys on a full signature**: it cannot be honoured end to
end, **which is why the pipeline never tries**."*

As duas primeiras cláusulas (alvo MOP e violação) são verdadeiras. As três em negrito são falsas: o
denominador **já** indexa por assinatura, o cruzamento **já** testa por assinatura, e o pipeline
**funciona assim há campanhas**. Um leitor que siga a orientação literal construiria um denominador
7,19% menor que o do código.

E os números do mesmo parágrafo estão vencidos: `jca` = 120/68 confere; `jca_android` está escrito
como 119/67 e hoje é **207/113** — o conjunto foi de 23 para 48 `.mop` com as gh105/gh109. O
parágrafo se oferece como régua de sanidade ("use it to confirm which spec set was loaded") e a régua
erra em 74%.

#### A gh69 e esta assimetria — adjudicação

A gh69 (`openspec/changes/gh69-generic-subtype-target-matching/`, issue #69 **aberta**) trata de
**coringas na resolução de alvos**: import com asterisco, owner por subtipo (`Collection+.addAll(..)`)
e nome de método com padrão (`add*`). Defeito real: o conjunto `generic_new` resolve **0 alvos** hoje.

**Não foi abandonada — nunca foi iniciada**: 1 de 47 checkboxes, zero código
(`grep -rn "includeSubtypes\|nameIsPattern"` no `rvsec-mop-extractor/src` e no `rvsec-gator/` volta
vazio), 10 commits, todos `docs(gh69)`.

**A razão registrada para segurá-la venceu.** A `proposal.md:191-208` (21/08) argumenta que o produto
**ficaria inalcançável mesmo depois de pronto**, porque `rv-experiment`/`rv-platform` nunca setam
`mop_dir` e o `RVStaticAnalysisConfig` cai no default literal `resources/jca` — e aponta a issue #104,
task 10.0, como veículo. **Essa tarefa foi entregue**: `openspec/changes/gh104-legible-violation-reports/tasks.md:264`
está marcada `[x]` e o código está no lugar —
`modules/rv-experiment/src/rv_experiment/config.py:987` passa
`mop_dir=self.resolve_spec_set_dir(rvsec_root)`. Antes disso, uma campanha `--specification-set
jca_android` era **instrumentada com um conjunto e medida contra outro** (auditoria G12); hoje não é.

Sobra uma ressalva estreita: `resolve_spec_set_dir` (`config.py:645-704`) mapeia `jca`,
`jca_android`, `generic` e `custom`. **`generic_new` existe em disco e nenhum valor de
`--specification-set` o nomeia** — mas é selecionável por `--specification-set custom
--custom-specs-dir …/generic_new`, o que antes da 10.0 também não bastaria, porque o `mop_dir` não
chegava ao GATOR. O produto da gh69 é alcançável hoje; só não tem nome próprio.

O veredito de 21/08 (`docs/20260821_gh69_veredito_coringas.md:12-26`) recomenda **implementar**, com o
escopo reafirmado sobre o `directlyReachesTarget`, porque o `reachesTarget` do `generic_new` reparado
**satura em 84–94% dos métodos** e em 4 de 8 APKs ultrapassa a própria fração `reachable`. A
mitigação registrada na RISK-004 está **empiricamente refutada**: remover 34 dos 67 pares de owners
quase-universais não move o transitivo em APK médio nem grande.

**Isso converge com o que medi aqui por outro caminho**: no `jca`, `reachesTarget ≥ 1` vale em
219/219 e 162/162 artefatos (§4.3). Os dois documentos chegam à mesma conclusão independentemente —
o critério transitivo não discrimina, e é ele que a coluna publicada `cov_reaches_target` usa.

**A gh69 resolve as assimetrias desta seção? Quase nenhuma** — e a própria change diz que os eixos
são ortogonais (`design.md:215-226`, D7: *"`MatchPolicy` is a different, orthogonal axis: signature
strictness"*):

| assimetria medida aqui | a gh69 resolve? |
|---|---|
| semeadura por nome infla o alvo 1,07–1,12× | **não** — preserva INV-ANA-35 byte a byte |
| **11/68 pares mortos por `<init>` no `jca`** | **sim, incidentalmente** — o reparo `new`→`<init>` entrou na change (commit `218c3c4c`, fase 4b/D9); efeito medido no fixture: 21 → 23 |
| **owner não importado descartado em silêncio** | **sim** — task 1.3(b), log-and-skip (RISK-013) |
| denominador por assinatura × semeadura por nome | não — ortogonal |
| 62,3% das violações fora do denominador | não — ortogonal |
| `errors.csv` sem `signature` | não — ortogonal |
| scan de bytecode LENIENT | não — irreparável por construção |

**Recomendação desta análise.** Os dois itens marcados "sim" — o reparo `new`→`<init>` e o
log-and-skip do owner — atacam defeitos do conjunto **`jca`, em produção, que o artigo mediu**: 11
pares mortos e uma spec inteira contribuindo zero alvos, com todo `cov_reaches_target` medido
saindo de 22 das 23 specs. São baratos, independem do eixo coringa e valem sozinhos; não há razão
para segurá-los.

Quanto ao restante da gh69, **o argumento de bloqueio caiu com a entrega da task 10.0**. O que resta
contra fazê-la agora é escopo, não impedimento: o veredito de 21/08 mostra que o `reachesTarget` do
`generic_new` reparado satura em 84–94% e que a mitigação registrada na RISK-004 está refutada, e
pede quatro ajustes de artefato antes. Se ela entrar, entra com o escopo reafirmado sobre o
`directlyReachesTarget` — e com a decisão sobre o `hot`/`cold` do `aperv-tool`, que colapsa junto e é
código em produção, no mesmo commit.

### 4.6 Relatórios — o que o leitor consegue enxergar

Colunas exatas em §2.5. Três lacunas:

**Nenhum CSV publica um denominador.** O `to_dict()` tem os totais (`coverage.py:413-418`); a escrita
os descarta. **Nenhum artefato registra quantos registros de runtime não casaram.**

Dois contadores certos existem e param antes do disco:

- `ParserDiagnostics` — nunca serializado; `to_dict()` só é chamado em testes.
- `TaskResult.write_errors` (`task.py:353-356`) — criado com a justificativa explícita de que "uma
  task cujas violações se perderam é indistinguível de uma task que não teve nenhuma" (INV-PLT-32) —
  e **ausente do `to_dict()`** (`task.py:429-452`).

**Procedência não chega aos CSVs.** O tecelão está em `experiment_config.json`
(`instrumentation_variant`), mas nenhuma coluna de `coverage.csv`/`summary.csv`/`errors.csv` o
carrega. E o checksum de configuração cobre o `PlatformConfig`, que **não tem**
`instrumentation_variant` nem `specification_set` (§2.6). Quando CSVs de campanhas diferentes são
concatenados, a origem se perde.

**Caso patológico já materializado**: `results/gh105_smoke_85_ape/` — 62 linhas `RVSEC-COV` no
logcat, 9 violações, `summary.csv` com **0% nas seis métricas**, nenhum JSON estático co-localizado,
nenhum arquivo de log no diretório. Nada ali registra que o denominador estava ausente.

---

## 5. Os dois achados com testemunha numérica

Os outros três — o colapso do denominador no rebaixamento do GATOR (§4.3), a taxa de não-casamento
do cruzamento (§4.4) e a
granularidade dupla (§4.5) — estão nas suas seções. Os dois abaixo têm o que os outros não têm: um
antes-e-depois medido no próprio acervo.

### 5.1 A regressão do normalizador

`StaticAnalysisParser` aplica `SignatureNormalizer.normalize_class_name()` a **todo** className vindo
do GATOR (`static_analysis_parser.py:371`). O `CLAUDE.md` do módulo afirma que isso é *"a safety-net
no-op on well-formed output"*. **É o oposto**: como o GATOR já emite a forma binária correta, todo
`.` entre dois segmentos maiúsculos na saída dele é **fronteira de pacote** — e a heurística
(`signature_normalizer.py:246-312`, converte quando ambas as partes começam com maiúscula) está
sempre errada ali.

O lado de runtime **não é normalizado**: o `SignatureNormalizer` aparece só em
`static_analysis_parser.py` em todo `modules/*/src/`. O instrumentador emite o nome binário puro.
Resultado: denominador com `$`, numerador com `.`, cruzamento por igualdade literal.

**[rev. 5] O diagnóstico de 2025 está invertido, e isso muda a natureza do reparo.** O
`docs/NOVO/06_normalizacao_inner_classes.md` (§2.1, §4.3) atribui o `$` ao AspectJ: *"AspectJ
interpreta estruturas Pacote.Classe onde Pacote == Classe como se fossem inner classes"*. Verificado
na fonte: `Coverage.aj:64` monta o nome com `method.getDeclaringClass().getName()`, que é o **nome
binário da JVM** e nunca insere `$` em fronteira de pacote — idêntico nos três `Coverage.aj` gerados
que existem no acervo (`cli_experiment_20260514_134106_eeefed0a`, `gh56-smoke`,
`gh99_jca_android_monitors`). Quem produzia o `$` era o normalizador, do lado estático. A
consequência é que o D3 não é uma escolha entre normalizar de um lado ou dos dois: é **remover uma
transformação que quebra um acordo que já existia**.

**[rev. 5] E o normalizador nunca poderia ter reparado, nem por acidente.** Ele é aplicado ao
`class_name` e **não** à `signature`: `static_analysis_parser.py:390` guarda `signature=signature`
verbatim. Quando dispara, produz um registro internamente inconsistente —
`Method.class_name = …ZoomView$ZoomView` ao lado de `Method.signature = <…ZoomView.ZoomView: …>` — e
o cruzamento testa os dois (`coverage.py:658` a classe, `:665` a assinatura). É isto que explica os
~10 milhões de warnings que o doc de 2025 mediu *apesar* do normalizador: a classe casava e o método
não.

#### A medição pendente da rev. 1, agora fechada

A rev. 1 registrava: *"não existe run dexlib2 do lstopo no acervo, então a propagação daquele caso ao
tecelão de produção é inferida do mecanismo, não medida"*. **Existe, e a inferência estava certa.**

`RESULTS/m2/results/exp_00/exp_00/com.hwloc.lstopo_80283.apk/` — 99 logcats, campanha do artigo:

```
RVSEC-COV: 9.902 linhas, prioridade I = 9.902, V = 0        → dexlib2, sem dúvida
com.hwloc.lstopo.ZoomView.ZoomView  (ponto)  → 1.080 ocorrências
com.hwloc.lstopo.ZoomView$ZoomView  (cifrão) →     0 ocorrências, em 99 de 99 logcats
artefato GATOR co-locado: 42 ocorrências com ponto; as 5 com $ são o aninhamento genuíno
                          ZoomView$ZoomViewListener
```

Os dois produtores concordam byte a byte, sem normalização nenhuma. O normalizador de produção,
executado sobre os nomes reais, desfaz o acordo **e piora o caso que já estava certo**:

```
com.hwloc.lstopo.ZoomView.ZoomView                    -> com.hwloc.lstopo.ZoomView$ZoomView
com.hwloc.lstopo.ZoomView.ZoomView$ZoomViewListener   -> com.hwloc.lstopo.ZoomView$ZoomView$ZoomViewListener
```

A ressalva de escopo da rev. 1 pode ser removida.

#### A dose no acervo de calibração (era ajc)

Rodando o normalizador de produção sobre todo `className` de todo `reachability[]`:
**413 classes (1,09%) e 2.725 métodos (1,41%), em 9 de 195 APKs (4,6%)**, sobre 8.328 artefatos.
Os nove, com a fração corrompida:

| APK | classes | métodos | pacote capitalizado |
|---|---|---|---|
| `nz.gen.geek_central.ObjViewer_1` | **23/23 (100%)** | 78/78 | `…geek_central.ObjViewer` |
| `tranquvis.simplesmsremote_140` | **171/172 (99,4%)** | 724/730 | `…CommandManagement.Commands`, `…Adapters` |
| `com.orpheusdroid.sqliteviewer_1` | 17/56 (30,4%) | 81/303 | `…sqliteviewer.Adapter` |
| `io.github.x0b.rcx_220` | 161/554 (29,1%) | **1621/2795 (58,0%)** | `…RecyclerViewAdapters`, `…Services` |
| `org.woheller69.solxpect_29` | 26/115 (22,6%) | 101/562 | `…weather.ui.RecycleList` |
| `org.secuso.privacyfriendlyludo_5` | 6/75 (8,0%) | 27/380 | `…privacyfriendlyludo.Map` |
| `com.hwloc.lstopo_271` | 2/36 (5,6%) | 37/170 | `com.hwloc.lstopo.ZoomView` |
| `com.orpheusdroid.screenrecorder_33` | 1/111 (0,9%) | 5/590 | `…screenrecorder.DemoMode` |
| `fr.free.nrw.commons_1034` | 6/2155 (0,3%) | 51/9107 | `fr.free.nrw.commons.LocationPicker` |

**Dose-resposta**, que descarta coincidência: 100% das classes corrompidas → 0,00%; 99,4% → 0,00%;
5,6% → cobertura presente mas subestimada.

**Duas correções à rev. 1**: o "0,00% em **18** execuções" é **9** — `baseline_v2/summary.csv` tem 9
linhas por APK (3 tools × 3 reps × 1 timeout de 600 s), e o 18 veio de `summary.csv` e
`aggregated_summary.csv` serem byte-idênticos (md5 `8b179538…`) e terem sido contados como dois. O
fato — cobertura 0,00% apesar de execução real — permanece intacto. E a âncora
`experimento-20260706/filters/experiment_apks.txt:58` aponta para **`com.hwloc.lstopo_80283.apk`**,
não `_271`; é o mesmo app em outra versão, e também é afetado, então a conclusão sobrevive.

#### A dose no corpus do artigo (dexlib2)

Este conjunto é **diferente** e a corrupção é **muito mais branda**. Sobre os 162 artefatos do corpus
do artigo (215.430 classes), **7 APKs afetados, 465 classes**:

| APK | classes corrompidas | `cov_method` mediano medido |
|---|---:|---:|
| `com.afkanerd.deku_83` | 75/505 (**14,9%**) | 10,67 |
| `com.hwloc.lstopo_80283` | 2/37 (5,4%) | 19,78 |
| `com.tk.quicksearch_65` | 305/6059 (5,0%) | 9,46 |
| `de.luhmer.owncloudnewsreader_196` | 19/528 (3,6%) | 17,59 |
| `com.smartpack.packagemanager_79` | 14/390 (3,6%) | 15,59 |
| `com.gelakinetic.mtgfam_99` | 15/457 (3,3%) | 12,78 |
| `app.michaelwuensch.bitbanana_79` | 35/2147 (1,6%) | 5,64 |

Os sete estão nos 163 do artigo. **Nenhum zera** — o padrão dose-resposta prevê isso, e é o que se
mede. O viés é de subestimação, distribuído.

### 5.2 A chave de escopo — a leverage medida

O acervo tem um antes-e-depois limpo do efeito da chave: `RESULTS/summary_all_pre_gh91.csv` e
`RESULTS/summary_all.csv`, 21.681 linhas cada, mesmos logcats, mesma instrumentação, mesmas
execuções — **só a chave mudou**, em 30 APKs.

`cov_method` mediano mudou em **26 dos 219 APKs**:

| APK | pre-gh91 | pós | fator |
|---|---:|---:|---|
| `org.fossify.paint_7` | 5,07 | **35,57** | ×7,0 |
| `org.fossify.math_10` | 8,76 | **42,01** | ×4,8 |
| `org.fossify.musicplayer_14` | 9,40 | 26,07 | ×2,8 |
| `org.fossify.voicerecorder_18` | 6,70 | 22,16 | ×3,3 |
| `org.fossify.notes_13` | 5,01 | 17,19 | ×3,4 |
| `net.osmtracker_73` | 7,48 | 13,14 | ×1,8 |
| `org.fossify.calendar_20` | 6,97 | 12,92 | ×1,9 |
| `org.wikipedia_50595` | **0,00** | 0,89 | — |
| `com.jerboa_87` | 50,87 | **17,75** | ÷2,9 |
| `swati4star.createpdf_110` | 20,00 | **3,60** | ÷5,6 |

**A mediana global mal se moveu: 17,63 → 17,92.** O agregado esconde a redistribuição inteira — que é
exatamente por que o defeito sobreviveu.

E o caso de assinatura: `org.wikipedia_50595` era `cov_method = 0` **com** `mop_errors_total > 0`
antes do gh91, e deixou de ser depois. Esse par é o que §12 nomeia como "o sinal mais forte
disponível de que o cruzamento falhou". Ele não é hipótese: já ocorreu no corpus do artigo, e a
correção da chave o desfez.

---

## 6. O corpus, as campanhas e os números medidos

> **Enquadramento (decisão do pesquisador, 28/08).** **O artigo não foi publicado.** O plano é
> **rodar a campanha de novo depois das correções** — gh105, gh109, instrumentador, análise estática —
> e só então escrever os números. Isso muda o que esta seção decide, e a mudança é grande:
>
> - Os números de hoje **não são errata, são rascunho.** Não há o que anotar nem o que retratar; eles
>   serão substituídos.
> - O valor deles é outro, e continua alto: são a **linha de base contra a qual cada reparo será
>   verificado**, e são a evidência de que os defeitos existem. `org.fossify.paint` 5,07 → 35,57 na
>   troca de chave é a melhor testemunha disponível de que a chave importa.
> - A pergunta deixa de ser "quanto o viés custa ao que já foi dito" e passa a ser **"o que precisa
>   estar correto antes de a campanha rodar"** — porque tudo o que não estiver corrigido no dia da
>   campanha fica dentro dos números definitivos. Ver §6.4.
> - E abre uma possibilidade que não existia sob o enquadramento antigo: **o corpus pode voltar a
>   crescer.** Os 55 apps excluídos pelo portão de denominador saíram por limitação da ferramenta, não
>   do app. Ver §6.2.

### 6.1 As campanhas

| | `experimento-20260706` | `experimento-20260721` |
|---|---|---|
| objetivo | a campanha que sustenta o artigo | escolher o modelo de visão do braço LLM do APE-RV (base × v2) |
| APKs | **219** (`filters/experiment_apks.txt`) | **181** (subconjunto de 219) |
| tools | 11 (`monkey`, 4× `droidbot`, `ape`, `droidmate`, `humanoid`, `ares`, `fastbot`, `qtesting`) | 1 braço (`aperv:sata_mop_llm_v13`) × 2 modelos |
| reps × timeouts | 3 × {60, 180, 300} | 3 × {300} |
| spec set / variante | `jca` / **dexlib2** | `jca` / dexlib2 |
| grade | **21.681 tasks** | 543 por braço |
| quando | 06–12/07/2026 (4 VMs GCP × 4 containers); reprocessado 31/07 pós-gh91 | 21–22/07/2026, local |
| brutos | `RV_ANDROID_NOVO_DATASET/RESULTS/m1..m4` (64 GB, 21.681 `.logcat`) | `experimento-20260721/results/` |

**As 16 configurações têm `generate_monitors`/`instrument_apks`/`run_static_analysis` = `false`.** Os
APKs chegaram instrumentados e os `.apk.json` chegaram prontos.

Perdas já documentadas pela própria campanha, sem relação com estes defeitos: **235 logcats sem
`RVSEC-COV`** (1,08%), sendo 189 determinísticos — `qtesting` × 21 APKs cuja MAIN só existe em
`<activity-alias>` (`docs/residual/NOCOV_LOGCATS.md`, `nocov_235.csv`).

### 6.2 O artigo

`ase-journal/docs/prompt_validacao_rigorosa.md:240` fixa o vínculo: *"`experimento-20260706/` is the
experiment this paper reports"*. A base publicada é `dataset/results/summary.csv` — verifiquei:
**16.137 runs, 163 APKs distintos**, média global de `cov_method` = **21,881%**, que é o `21.88%` de
`results-rq2.tex:14`.

O funil é **219 → 164 → 163 → 162**, e cada degrau tem um critério distinto:

1. **219 → 164, escopo de denominador.** Mantém o APK sse `keep(Mneut)`: `|A∩G|/|G| ≥ 0,90` **e**
   `|A\G|/|A| = 0` (`mneut_scope.py:76-77,186`). **55 excluídos**: 33 `denominator_collapse`,
   21 `denominator_too_narrow`, 1 `denominator_foreign` (`stage_denominator_scope.py:26-38`).
2. **164 → 163, cobertura zero.** Um APK: `com.google.android.stardroid_1678`, razão
   `weaver_pkgfilter_zero` (`reduce_to_163.py`).
3. **163 → 162.** Um APK: `info.dvkr.screenstream_44000`, que estourou o teto de 64 K referências de
   método na reinstrumentação dexlib2 (`docs/20260812_registro_execucao_prontidao_e3.md:309-330`).

Ou seja: **o corpus do artigo foi estreitado até o conjunto em que a chave derivada do manifesto
funciona.** É defensável como decisão editorial e é um dado sobre a ferramenta: a limitação do
pipeline entrou na seleção do corpus.

**E aqui está o ganho que o enquadramento novo abre.** Os 55 apps saíram do escopo de denominador
**por limitação da ferramenta, não por propriedade do app**: 33 porque a chave derivada do manifesto
não nomeava classe nenhuma, 21 porque o escopo saía estreito demais. Com a chave reparada (D2),
**parte desses 55 volta a ser mensurável** — o corpus da campanha nova pode crescer de 163 na
direção de 219. **[rev. 4] O crédito é todo do D2**: o funil avalia a chave contra as classes
compiladas, e o D9 — que é defeito da classificação feita depois — não devolve nenhum dos 55
(§4.3, e `docs/20260828_d9_colapso_denominador.md` §5). Não é um detalhe de forma: é poder estatístico, e
é a diferença entre "excluímos 25% do corpus" e "medimos o corpus". Quanto exatamente volta é medível
antes de rodar a campanha, reprocessando os `.apk.json` com a chave reparada.

**E o portão tem um ponto cego que importa.** `keep(X)` avalia `A(X)` = as classes **do DEX** sob o
prefixo `X` (`mneut_scope.py:150-157`, sobre `dex_classes.zip`). Ele valida a **chave**, não o
**artefato produzido**. Um APK cuja chave está certa mas cuja análise carregou quase nada passa no
portão intacto — e é o que acontece: `br.com.colman.petals` (1 classe no artefato),
`com.github.livingwithhippos.unchained` (2), `com.nononsenseapps.feeder.play` (6) e
`com.github.cvzi.screenshottile` (21) **estão nos 163 do artigo**, e os dois primeiros publicam
`cov_class = 100,00%`. Um portão do pipeline precisa comparar o artefato com o DEX, não só a chave.

**Nota sobre os 181 e os 163.** Não são degraus de uma mesma cadeia: são dois cortes concorrentes dos
mesmos 219, de eras diferentes, e **não são aninhados** (`163 ∩ 181 = 147`). Isso importa ao comparar
`experimento-20260721` (181) com o artigo (163).

**Nota sobre os artefatos dos 162.** 28 dos 162 `.apk.json` diferem dos homônimos no diretório de
219 — são os do gh91, e a diferença é **só o WTG** (classes e métodos idênticos; `transitions` 0 →
populado, porque o diretório dos 162 usa os JSONs de `SA_RERUN_gh91_wtg/`, sem `skipWtg`).

**Claims que dependem de cobertura** (`cov_method`, `cov_directly_reaches_mop`): a média global de
21,88% e o pico de 33,06% do APE (`results-rq2.tex:10-14`, `conclusions.tex:5`, `abstract.tex:11`); a
queda do monkey de 24,37% para 22,91% (`:16-17`); as razões 3,1× e 2,7× (`:26-29`); os 21,41% de
`cov_reaches_mop` (`:30-32`); `\directCovNoSupport`=87 (`constants.tex:110`); o modelo NB de RQ2
(`:43-62`); e as 66 células de `tabs/coverage.tex` + `tabs/coverage_mop.tex`.

**Claims que dependem só de violações** — e por isso **não são afetadas**, pelo mecanismo da §4.2:
`\uniqueMisusesMOP`=454, `\totalViolations`=97.018, a RQ1 inteira (ganhos 60→300 s, baseline de
testes unitários, Venn RV×CogniCrypt 112/342/311), a RQ3 inteira (70,9% em 4 specs, `\appCodePct`,
OkHttp 175 / Tink 84), e o GLM NB de RQ1 — cuja covariável é `sa_methods_reaches_mop`, estático.

**Teto de viés sobre os números de hoje** (limite superior analítico: "todos os métodos com chave
inalcançável foram executados"):

| Métrica | valor atual | teto de subestimação | relativo |
|---|---:|---:|---:|
| `cov_method` média global | 21,88% | **≤ 0,333 pp** | ≤ 1,52% |
| `cov_class` média global | 31,06% | ≤ 0,229 pp | ≤ 0,74% |
| `cov_method` máx. (ape @300s) | 33,06% | ≤ 0,333 pp | ≤ 1,01% |

Sob o enquadramento antigo (números publicados) esta tabela decidia se valia reprocessar. **Sob o
enquadramento real — artigo não publicado, campanha nova planejada — ela decide outra coisa**: é a
previsão contra a qual o reparo será checado. Se o `cov_method` da campanha nova subir muito mais que
0,333 pp por esta causa, a diferença tem outra origem e precisa ser explicada. E note que este teto
cobre **apenas a corrupção do normalizador**; os outros três defeitos (chave, colapso do
denominador, granularidade) não estão nele, e o da chave já mostrou fatores de ×7 e ÷5,6 por APK.

**Um efeito é de direção conhecida e vale registrar antes**: corrigir o normalizador e a chave
**aumenta** a cobertura medida. O argumento de RQ2 é "a cobertura é baixa" — ele não deixa de valer,
mas os números novos serão maiores que os atuais, e a redação tem de sair da campanha nova, não da
atual. Já o colapso do denominador (§4.3) anda na direção oposta: corrigi-lo **derruba** os `cov_class` de
100,00% de `petals` e `unchained`, que hoje são artefatos de denominador degenerado — **[rev. 4]** o
denominador de classes desses quatro sai de 1 / 2 / 6 / 21 para 771 / 1.971 / 3.589 / 550.

O único ponto que cruza os dois lados é o modelo NB de RQ2, que regride *misuses únicos* (lado sadio)
contra `cov_method` (lado enviesado). Com o eixo X corrigido a associação pode mudar de magnitude; o
IRR atual é 1,0028 com p = 0,6629, e um erro de medição em X **atenua** — ou seja, o "não há
associação detectável" de hoje é conservador, e a campanha nova é quem responde de verdade.

### 6.3 Onde o dano já se materializou

Os três APKs nomeados na rev. 1 (`ObjViewer`, `simplesmsremote`, `lstopo_271`) **não estão no corpus
do artigo nem no das duas campanhas** — vivem no acervo local `rv-android/results/`, era ajc, das
campanhas de calibração do APE-RV. A rev. 1 os tratava como se fossem do corpus do artigo; não são.

Mas o dano existe, e está em `rv-android/data/results/_analysis/` (análise do experimento MadEvolve
de 169 APKs, abril/2026 — corpus descartado do artigo, mesmo mecanismo):

```
broken_apks.csv:5   nz.gen.geek_central.ObjViewer_1.apk,0.000,0.000,broken_identical_near_zero
broken_apks.csv:12  tranquvis.simplesmsremote_140.apk,0.000,0.000,broken_identical_near_zero
```

Os dois APKs que o normalizador zera foram **classificados como inertes e descartados** ("Métrica 4:
dataset curado — 132 APKs, sem os 37 inertes", `merge_decision.md`). Não são inertes: executaram 78 e
730 métodos. E `violations_per_apk.csv` mostra o padrão assimétrico num artefato já produzido:

```
nz.gen.geek_central.ObjViewer_1.apk,1,1,1,baseline,0,0,0
```

Cobertura 0,000/0,000 **e** 1 violação única registrada. A violação sobrevive porque não cruza com a
estática; a cobertura morre porque cruza por igualdade literal.

Duas outras exposições no acervo de calibração:

- `results/baseline_v2` (174 APKs, **ajc**, 3 tools, 600 s): 7 dos 9 afetados, teto de viés 1,80 pp,
  **2 zeros falsos**.
- `results/aperv_precal_macro` (calibração Optuna, 131 trials, 30 APKs): a função-objetivo é **100%
  cobertura** (`scripts/aperv_objective.py:76-80`), e 2 dos 30 APKs têm chave corrompida. O
  `trim_mean(0.1)` provavelmente protege o *ranking* de hiperparâmetros; o valor absoluto do score
  (38,99) não. Não foi recalculado.

E `experimento-20260721`: o viés é **idêntico e constante nos dois braços** (mesmos 181 APKs, mesmos
artefatos). O Wilcoxon é sobre diferenças pareadas por APK, então o Δ de −2,23 pp em `cov_method` e a
decisão do modelo **sobrevivem intactos**; só as médias absolutas sobem um pouco.

---

### 6.4 O que precisa estar correto antes da campanha nova

Como o artigo não foi publicado e a campanha será refeita, a lista de reparos deixa de ser uma fila de
prioridades e vira um **portão**: tudo o que não estiver corrigido no dia em que a campanha rodar fica
dentro dos números definitivos, e sai caro depois — refazer 21.681 execuções em 4 VMs custa dias.

**Precisa entrar antes (muda o que é medido):**

| item | por quê, em uma linha |
|---|---|
| **D2 — a chave de escopo** | sem ela o pipeline não roda ponta a ponta neste corpus: 75 de 162 com denominador vazio |
| **D3 — a normalização do denominador** | 7 APKs com chaves inalcançáveis; o único reparo de direção conhecida e medida |
| **D9 — o colapso do denominador** | 4 artefatos com 1–21 classes; é o que produz `cov_class = 100,00%`. **[rev. 4]** mecanismo determinado: a guarda de `AnalysisEntrypoint.java:119` usa o pacote do manifesto e o `libPackages.txt` rebaixa o resto |
| **D9a — os dois reparos do `<init>` e do owner mudo** | 11 de 68 pares do `jca` e **27 de 113 do `jca_android`** semeiam zero alvos hoje |
| **R1 — `getEntry`/`setEntry` nunca tecem sob dexlib2** | FN silencioso **e** `KEYSTORE-ORDER-00` falso em todo `load…store` real; contamina a contagem de violações, que é RQ1/RQ3 |
| **os reparos R2–R5 e as decisões D-1…D-* da gh109** | são o que faz as specs ficarem certas; a campanha mede o que elas acusam |

**Conjunto de specs: `jca_android`, saída da gh109** (decisão do pesquisador, 28/08; a change está em
59 de 66 tarefas, com as 7 pendentes em registros stale e portões de harness/lint/review). A task 10.0
da gh104, já entregue, garante que a análise estática mede o mesmo conjunto que instrumenta — sem ela
uma campanha `jca_android` seria medida contra o `jca`.

**O recorte é decisão da ideação, não deste documento.** O que está estabelecido é só o material de
entrada, e ele é de três procedências distintas — o que **não** implica três changes:

| material de Fase 0 | o que traz para o portão | estado registrado |
|---|---|---|
| `docs/20260827_relatorio_final_validacao_jca_android.md` | R1–R6 e as decisões D-1…D-*; é o que faz as specs `jca_android` ficarem certas, e o que a campanha vai acusar | o próprio cabeçalho diz que serve de entrada para "**uma possível** issue+change de correção", linhagem gh100–gh105–gh109 |
| **este documento** | chave de escopo, normalizador, colapso do denominador, contabilidade do cruzamento, procedência, os dois itens da gh69 | entrada de uma issue+change (decisão do pesquisador, 28/08) |
| `docs/20260827_divergencia_after_dexlib2_ajc.md` §6, opção (a) | `after()` puro disparando também quando a chamada casada lança | registrado como "**candidata** a change própria do módulo dexlib2", porque muda comportamento e exige harness diferencial |

~~Se isso vira uma change, duas ou três é pergunta de recorte, e está aberta.~~

**[rev. 3] O recorte foi decidido, e são changes já existentes na maior parte.** A tabela acima
sugeria que os três materiais virariam issues novas. A verificação mostra que **dois dos três já têm
casa**:

- **Os reparos de spec (`20260827_relatorio_final_validacao_jca_android.md`) já estão na gh109**, num
  grupo **G8** que está na árvore de trabalho e **não foi commitado** (`tasks/G8-second-wave.md`
  untracked; `tasks.md`, `proposal.md`, `design.md` e o delta de spec modificados). Isso torna o §10
  daquele relatório — que propunha abrir a issue #111 — desatualizado: a decisão D-25 dobrou a
  segunda onda para dentro da gh109. Mapeamento verificado: **R2 → 8.1**, **R3 → 8.2**, **R4 → 6.4**
  (bloqueada por decisão do pesquisador), **R5 → 8.8**, **D-1 → 8.4**, **D-2/D-3 → 8.3**,
  **D-4 → 8.5**, **D-5 → 8.6**, **D-7 → 8.7** — todas abertas. Nada foi aplicado no reator
  (verificado em disco: `KeyStoreSpec.mop:106-112`, `MacSpec.mop:40`, `SecretKeySpecSpec.mop`,
  `ErrorType.java:16`, `Property.java` seguem idênticos ao que o relatório descreve). **Não abrir
  change nova para specs**: o caminho é commitar o G8 e fechar a gh109.
  Três itens ficaram **sem casa** e precisam de decisão: **R6 opção (b)** (o javadoc falso do
  `AfterEmitter` e a refundação de `conformance_record.csv:116-120`) não virou tarefa em lugar nenhum;
  **D-6** (emenda da divergence row 40), **D-8** (template das 44 mensagens ORDER) e **D-9**
  (CertificateFactory case-insensitive) não são tarefa nem constam da tabela "not adopted".
- **O `after()` (`20260827_divergencia_after_dexlib2_ajc.md`, opção (a))** continua sendo change
  própria do módulo dexlib2, como já estava registrado. **R1** acompanha, pela mesma razão: a gh109
  recusa explicitamente o workaround na `.mop` (`proposal.md:21`, `design.md:197`) e o reparo raiz é o
  `TypeResolver`.
- **Este documento** é o único que gera change nova — e o escopo dela está em §15.3.

**Sobre a divergência `after()` (R6), a adjudicação já existe e é dupla**
(`docs/20260827_relatorio_final_validacao_jca_android.md:174-176`):

- **opção (b) — corrigir o que está escrito** (javadoc falso do `AfterEmitter`, e re-fundamentar por
  backend as razões das cláusulas de janela dos Digest streams em `conformance_record.csv:116-120`,
  que argumentam com `after ... returning` sobre eventos que são `after` **puro**). Isso é registro,
  e entra na change 1;
- **opção (a) — corrigir o instrumento**, compondo `insertAfter` com handler catch-all + rethrow via
  `installTryCatch` (maquinário que já existe e já é usado pelo `after() throwing`). Isso muda
  comportamento, exige o harness diferencial antes/depois, e por isso é a change 3 — **não porque
  seja opcional, mas porque não pode entrar de carona numa change de spec.**

**As duas são complementares, não alternativas** — (b) conserta o que está escrito, (a) conserta o
instrumento. A superfície de (a) é de **35 de 134 eventos no `jca` e 58 de 202 no `jca_android`**
(10 e 18 specs), e a divergência morde exatamente onde a chamada **pode lançar** — que, em specs de
criptografia, é o mau uso de parâmetro que a própria API rejeita: o acusador `len <= 0` do
`DigestInputStreamSpec:93` dispara sob ajc para um `read(b, 0, -1)` que lançou, e é silêncio sob
dexlib2. Rodar a campanha sem a (a) é uma escolha legítima, mas ela tem preço declarável: significa
adotar "normal completion only" como envelope de medição e registrar que essa classe de mau uso não é
acusada.

**Precisa entrar antes (não muda o medido, mas sem isso a campanha não é auditável):**

| item | por quê |
|---|---|
| **D1 — contabilidade do cruzamento** | é a testemunha de que os reparos funcionaram; sem ela a campanha nova é tão opaca quanto a atual |
| **D5 — procedência nos artefatos e nos CSVs** | `instrumentation_variant`, `specification_set`, `code_package`; foi a falta disso que tornou esta análise difícil |
| **D4 — serializar o que já se conta** | `ParserDiagnostics`, `write_errors`, `setup_file_logging` em produção |
| **D6 — contaminação do logcat entre tasks** | barato, e contamina dados enquanto são coletados |

**Pode ficar para depois:** D7 (fallback do split de frame — afeta a chave de identidade da violação,
mas o dano é localizado e reconstruível do logcat), D8 (portão do `CoverageValidator` — é sobre o
instrumento, não sobre a campanha), D10 (efeitos colaterais das flags — armadilhas de operação, não de
medição), D9b (o `CLAUDE.md`).

**Duas medições que valem fazer antes de rodar, e são baratas:**

1. **Quanto do corpus volta.** Reprocessar os `.apk.json` com a chave reparada e reavaliar o portão de
   denominador: dos 55 excluídos, quantos voltam? Decide se a campanha nova roda sobre 163 ou sobre
   algo maior, e isso muda o desenho da campanha (tempo de VM, número de containers).
2. **A previsão do reparo.** Reprocessar os logcats existentes com a chamada de
   `static_analysis_parser.py:371` removida, sem re-executar nada. Dá o delta real do normalizador
   contra o teto analítico de 0,333 pp, e é a validação mais barata de D3 que existe — os logcats já
   estão em disco.

---

## 7. A leitura histórica

Há prior art de outubro/2025, no repositório `rvsec-regerar-resultados`
(`docs/NOVO/06_normalizacao_inner_classes.md` e `07_pacotes.md`), sobre exatamente esta cadeia na era
**Soot + AspectJ**.

**A mudança de formato do log ocorreu antes da migração de pipeline**: commit `16ca70b2`, 20/02/2025,
*"changing to method signature in soot format"*. O formato antigo era `pkg.Classe:::metodo:::(params)`.
O ramo de fallback que o parser atual mantém (`logcat_parser.py:706-712`) é **código morto**: 0
ocorrências em 1.618.087 linhas reais; a única que o exercita é a fixture `rvsec_cov_golden.logcat:4`.

**As quatro lições, e o que foi feito com elas:**

| Lição | Estado |
|---|---|
| (a) busca bidirecional `$`↔`.` no casamento | **perdida** — nunca implementada, nem lá nem aqui |
| (b) exclusão dos APKs problemáticos | **perdida como recomendação, realizada por outra via** — o funil do artigo exclui 55 apps pelo portão do denominador |
| (c) detecção de package via componentes | **absorvida com melhoria** (`_is_in_namespace`, gh63; avaliação na gh67) — mas `default=False` desde a gh98, e a decisão do pesquisador é aposentá-la |
| (d) contagem e reporte de "método não encontrado" | **perdida** — era `print` por ocorrência mais um conjunto de mismatches; hoje é `logger.debug` sem contador |

O `SignatureNormalizer` é **idêntico por AST** ao histórico — nenhuma linha de correção — e mudou de
lado: no pipeline antigo era aplicado ao **logcat**, para casar com o `.methods`; aqui é aplicado ao
**denominador estático**, que já vinha correto. E `normalize_signature`/`normalize_parameter_list`, o
núcleo do reparo histórico, viraram **código morto**.

**A inversão é o ponto.** Nada disto é novo; o que mudou foi a visibilidade:

| | pipeline histórico | pipeline atual |
|---|---|---|
| quem erra | AspectJ (ferramenta externa) | **nosso normalizador Python** / **nossa chave** |
| sintoma | 4.662.882 warnings num APK, log 99,99% ruído, throughput −50% | `logger.debug`, zero contadores, 0,00% e 100,00% |
| detectabilidade | impossível não ver | impossível ver |

---

## 8. O padrão que atravessa tudo

O documento do tecelão de advice identificou dois fios; a cadeia inteira confirma os dois e
acrescenta um terceiro.

**Fio 1 — decidir por heurística onde há autoridade disponível.** O `TypeResolver` adivinha a
fronteira pacote/classe trocando ponto por barra, tendo o `android.jar` carregado. O
`SignatureNormalizer` adivinha a mesma fronteira por capitalização, tendo o próprio artefato do GATOR
— que já traz a resposta — na mão. E o `isAppClass` decide pertinência a um pacote por `startsWith`
cru, tendo a `Scene` do Soot inteira carregada, com os nomes de todas as classes da aplicação. É o
mesmo erro, em três lugares, em duas linguagens.

**Fio 2 — falha silenciosa como padrão.** Descritor mal formado devolve `null`; classe ausente devolve
lista vazia; advice que não casa some no agregado; registro que não cruza vira `logger.debug`; chave
que não casa nada devolve `complete: true` e 0,00%. Defensável para o que o instrumento não controla;
indefensável para o que é defeito nosso.

**Fio 3 — o instrumento mede tudo, menos a si mesmo.** O pipeline tem invariantes numeradas, portões
com limiar pré-registrado, aritmética de parser que fecha linha a linha, comparador diferencial
ajc×dexlib2 com F1 e kappa. E não tem **um único contador** para "quantos registros de runtime não
encontraram par na análise estática", nem **uma única checagem** de "o denominador está vazio". As
duas existem escritas — `ParserDiagnostics`, `LogcatRepository.diagnose()` — e param antes do disco ou
só são chamadas em testes.

---

## 9. Superfície afetada

| Componente | Papel na cadeia | Achados |
|---|---|---|
| `rv-android-core/domain/app.py` | **a chave** | só aceita um booleano; nenhum canal para a chave curada |
| `rv-experiment/pre_processor.py` | invoca a estática | `:347-353` é o sítio único; `--skip-instrument` desliga a estática por efeito colateral |
| `rvsec-gator` (Java) | gera o denominador | `startsWith` sem fronteira; artefato não registra a chave; `ReachabilityEnricher.topLevelMetadata()` sem chamador; **[rev. 4] `AnalysisEntrypoint.java:119` guarda o rebaixamento com o pacote do manifesto** — 4 artefatos colapsam para as `<activity>` do manifesto com a chave correta; os três `-exclude` de `Main.java:225-227` são inertes |
| `rv-static-analysis/static_analysis.py` | orquestra o GATOR | pós-condição só de existência de arquivo; registra a chave só em log não persistido |
| `rv-static-analysis/static_analysis_parser.py` | parseia o denominador | **aplica o normalizador ao lado certo pelo motivo errado** |
| `rvsec-gator/target/*` | semeia os alvos MOP | `LENIENT` hard-coded; `STRICT` inalcançável pelo caminho MOP; 11/68 pares mortos por `<init>` no `jca` |
| `rvsec-mop-extractor/UsedJcaMethodsVisitor` | extrai os alvos das specs | descarta em silêncio owner não importado — uma spec do `jca` contribui zero alvos |
| `rv-static-analysis/CLAUDE.md` | orientação de granularidade | três cláusulas afirmam o oposto do código; régua de sanidade do `jca_android` errada em 74% |
| `rv-android-core/signature_normalizer` | heurística de `$` | a regressão medida |
| `rv-platform/components/static_analysis.py` | carrega o artefato | `if static_data:` sempre verdadeiro; retorno de `copy_static_analysis_files` descartado |
| `rv-android-core/domain/coverage.py` | o cruzamento e as métricas | igualdade literal; dois descartes sem contador; `_percentage` devolve 0,0 em 0/0; `diagnose()` só em testes |
| `rv-coverage/logcat_parser` | numerador | ramo `:::` morto; diagnósticos nunca serializados |
| `dexlib2/coverage-weaver` | emite RVSEC-COV | escopo divergente do ajc; `<init>`; `PackageFilter` exclui `com.google` (3º mecanismo de zero) |
| `dexlib2/validator/CoverageValidator` | portão ajc×dexlib2 | portão insatisfazível; regex trunca `<init>` |
| `rvsec-core/ErrorSummary`, `ErrorDescription` | monta a linha de violação | split por último ponto; fallback copia o frame nos três campos |
| `rv-android-core/logcat_manager` | captura o logcat | filtra só por tag, não por pid/pacote |
| `rv-platform/result_processor` | relatórios | denominadores não publicados; sem procedência; dois esquemas de `performance.csv` |
| `rv-platform/platform.py` + `task_storage` | resume | checksum não cobre spec set nem variante |

---

## 10. Perguntas para a ideação

**Q1 — Quem responde a fronteira pacote/classe no cruzamento?** Opções: (i) nenhuma normalização, os
dois lados já concordam e qualquer transformação é dano — o que a medição do lstopo agora sustenta em
**dexlib2 e ajc**; (ii) busca bidirecional no cruzamento, a Opção B nunca implementada do prior art;
(iii) normalizar os **dois** lados com a mesma função. Recomendo (i) como reparo imediato — remover a
chamada em `static_analysis_parser.py:371` — e (ii) como rede permanente.

**Q2 — Quem responde qual pacote escopa a app, e por onde a resposta entra? [rev. 3] DECIDIDA — ver
§15.2.** O enquadramento da rev. 2 estava sobredimensionado, e a correção é do pesquisador: o
`rv-android` é **genérico**, para qualquer APK. O defeito não é da ferramenta — é do encontro entre a
ferramenta e **como nós construímos o dataset**. Um APK de loja tem `applicationId` igual ao
namespace das classes e nada disto aparece; o `rvsec-dataset` roda `assembleDebug` sempre, e o
`applicationIdSuffix` do Gradle acrescenta um segmento ao applicationId sem tocar no namespace. Logo
**"chave curada por APK" é a resposta errada**: a certa é manter o manifesto verbatim como regra e ter
uma **flag global de run** dizendo "este corpus é de debug, remova o sufixo". As sub-perguntas abaixo
ficam registradas porque a análise que levou até a decisão continua valendo.
Sub-perguntas, cada uma com resposta independente:
  - **Q2a — qual regra?** A denylist de 11 sufixos do `mneut_scope.py` resolve 162/162 no corpus do
    artigo e 179/219 no amplo. O prefixo comum das classes da aplicação, computado no Java onde a
    informação já está, resolve mais. O package da `mainActivity` resolve quase tudo com a ressalva
    de 19/162 `activity-alias`.
  - **Q2b — por onde entra?** Hoje não entra. Precisa de um canal — flag, coluna de CSV, ou campo de
    config — e a decisão de qual precede a de qual regra.
  - **Q2c — o `startsWith` do GATOR ganha fronteira de ponto?** O `mneut_scope.py` já concluiu que
    sim para produção. Mudar isso **muda medição**, então é decisão, não reparo.

**Q3 — O cruzamento e a chave passam a ter contabilidade?** Um contador `unmatched_calls`/
`unmatched_classes` no `ParserDiagnostics` — **separado em fora-de-escopo × dentro-do-escopo**, que é
a separação que distingue "o app não usou" de "a análise não viu" — exposto como colunas de
`summary.csv`, mais uma checagem de plausibilidade do denominador que **falhe alto**. Sem isso,
nenhum reparo desta cadeia é verificável, e nenhuma regra de chave é segura, porque nenhuma é total.

**Q3b — o que é um denominador implausível? [rev. 3] REENQUADRADA — não é pergunta própria, é o D9.**
A rev. 2 tratava isto como se houvesse uma decisão a tomar sobre a *definição* do denominador. Não
há: **a lista que o GATOR produz dentro do pacote informado É o 100% por definição**, e a análise de
reachability apenas complementa cada entrada dessa lista com três predicados. Quando o artefato traz
1 classe para um app de 36.800, o problema não é que o denominador seja "implausível" — é que a
análise classificou errado. Isso é o D9, e a pergunta certa é a Q3c. O que sobrevive desta entrada é
apenas o **sinal barato para detectar o caso**: comparar nº de classes em `reachability` contra
`class_defs_size` dos DEX sob o mesmo prefixo — útil como instrumento de investigação do D9 e como
portão de sanidade do D1, não como redefinição de denominador. (O portão do artigo não serve para
isso: valida a chave, não o artefato — §6.2.)

**Q3c — o colapso do denominador é reparo ou investigação? [rev. 4] RESPONDIDA: é reparo, e a
investigação está fechada.** O mecanismo foi determinado e reproduzido ao vivo sobre o caso mínimo
`br.com.colman.petals_3040000` — relatório em `docs/20260828_d9_colapso_denominador.md`, resumo em
§4.3. Não é o Soot: é a guarda de `AnalysisEntrypoint.java:119`, que rebaixa as classes do app a
biblioteca porque compara contra o pacote do manifesto. O reparo é de poucas linhas num sítio
(passar a consultar `Configs.getClientParamCode("codePackage=")`, com fallback ao manifesto), e a
sonda mede o efeito: 1 → 771 classes no `petals`, e invariância nos apps que não casam
`libPackages.txt`.

**Q3d — Em que granularidade a cadeia deve operar?** Hoje são duas ao mesmo tempo: alvo semeado por
nome, cobertura medida por assinatura, violação sem régua. As opções não são simétricas — ligar
STRICT na semeadura é possível no `resolveInScene` e **impossível** no scan de bytecode, que é quem
produz `directlyReachesTarget`. Antes de escolher, note que a spec **já escreve** a lista de tipos em
90% dos pointcuts: a informação existe e é descartada.

**Q4 — O que precisa estar correto antes de a campanha ser refeita?** O artigo não foi publicado e a
campanha será refeita depois das correções, então a pergunta não é sobre errata — é sobre portão. Ver
§6.4 e §11, D0. Duas sub-perguntas que a resposta arrasta: **o corpus continua sendo 163?** (parte dos
55 excluídos saiu por limitação da ferramenta e pode voltar) e **qual conjunto de specs a campanha
usa?** (se `jca_android`, os reparos das gh105/gh109 entram, e o `<init>` mata 27 de 113 pares lá).

**Q5 — O `package_detector` sai de vez?** A decisão do pesquisador é usar só o manifesto. Os 40 de
219 que nenhuma regra de string resolve são a conta dessa decisão: ou entram por outra via
(prefixo comum / mainActivity), ou saem do corpus, e a segunda opção precisa ser explícita.

**Q6 — O que substitui o portão do `CoverageValidator`?** Ele compara contra um emissor aposentado e é
insatisfazível por construção.

**Q7 — Procedência nos artefatos.** Sem `instrumentation_variant`, `specification_set` e
`code_package` nas colunas e no checksum, concatenar campanhas mistura populações.

**Q8 — A violação deve ser filtrada contra a análise estática? [rev. 3] RESPONDIDA: não, e a pergunta
sai da mesa (decisão do pesquisador, 28/08).** Hoje não é filtrada, por projeto declarado
(`result_processor.py:632-638`). Dois contraexemplos decidem, e ambos são cenários legítimos de uso:
**(a)** rodar um APK instrumentado **sem** análise estática — não há contra o que filtrar, e o
experimento tem de funcionar; **(b)** querer justamente **todas** as violações do APK, inclusive as
de bibliotecas que ele usa. Filtrar a violação pela chave destruiria os dois. A opção (iii) da rev. 2
— resolver a contaminação do logcat — também cai, porque o defeito não existe (ver D6).

Fica registrado, sem virar tarefa, que a assimetria da §4.2 é **real e medida** (62,3% dos sítios de
violação são de classes fora do denominador): ela é consequência do desenho, não defeito dele. Se um
dia se quiser distinguir os dois casos na leitura, o caminho é uma **coluna informativa** dizendo se
a classe acusada está no escopo — nunca um filtro.

---

## 11. Candidatos de recorte

**D0 — Os números atuais são rascunho; o alvo é a campanha nova.** O artigo **não foi publicado**, e o
plano é refazer a campanha depois das correções (gh105, gh109, instrumentador, análise estática) e só
então escrever os números. Portanto: **nada a anotar, nada a retratar, nada a reprocessar para
publicar**. O que os números de hoje valem é como **linha de base de verificação** — cada reparo deve
mostrar um delta na direção prevista contra eles. A lista do que precisa estar pronto antes de rodar
está em §6.4, e ela reordena tudo o que vem abaixo: sob este enquadramento, D1–D9a não são prioridades
concorrentes, são **pré-requisitos de uma mesma campanha**.

Duas exceções, que continuam sendo errata de verdade porque alimentaram decisões já tomadas:
`data/results/_analysis` descartou `ObjViewer` e `simplesmsremote` como "inertes" com base num zero
falso (`broken_apks.csv`), e a curadoria "132 APKs sem os 37 inertes" foi usada como robustez;
`results/aperv_precal_macro` otimizou hiperparâmetros contra uma função-objetivo 100% cobertura com
2 de 30 APKs corrompidos. `experimento-20260721` não precisa de nada — o viés é pareado e o Δ
sobrevive.

**D1 — Contabilidade do cruzamento e do denominador.** Contadores `unmatched_*` no
`ParserDiagnostics` + serialização + colunas em `summary.csv`; e uma checagem de não-vacuidade que
falhe alto quando o denominador é vazio ou implausivelmente pequeno. Sem mudança de comportamento de
medição. **Habilita verificar D2 e D3, e é o que torna qualquer regra de chave segura.**

**D2 — A chave de escopo na via de produção.** Um canal para a chave curada + a regra de
neutralização (a denylist já é norma escrita no `mneut_scope.py`) + registro da chave efetiva no
artefato ou num sidecar. É o que desbloqueia rodar o `rv-experiment` ponta a ponta no corpus atual.
Nota de projeto: o portão `keep(X)` do artigo **não é portável** — depende de um ground truth
adjudicado; o portão do pipeline tem de ser sem oráculo.

**D3 — Remover a normalização do denominador.** **[rev. 3] São duas chamadas, não uma** —
`static_analysis_parser.py:371` (classes) e `:455` (windows). Remover só a primeira deixa o
denominador de atividades normalizado **e** quebra o casamento window↔class de INV-ANA-60: um lado
passa a ter `$`, o outro não. É duas ou nenhuma. Quatro testes quebram, um deles estruturalmente
(`test_normalizer_is_noop_on_correct_json` faz monkeypatch do método). As duas chamadas removidas,
mais teste que fixa a decisão, mais a correção do `CLAUDE.md` que
afirma o contrário do que o código faz.

**[rev. 5] O D3 mata a classe inteira, não só duas chamadas.** `SignatureNormalizer` tem
**exatamente um consumidor** em todo `modules/*/src/` — o `static_analysis_parser.py`. Removidas as
duas chamadas, a classe fica morta, e o P3 manda deletar: `signature_normalizer.py`,
`test_signature_normalizer.py`, a INV-ANA-02 que a torna normativa, e as três alegações de docstring
(`:11`, `:24`, `:183`) que a descrevem como rede de segurança. Sem shim, sem wrapper, sem
`_unused`. Maior impacto e menor risco da lista. *Muda medição* — para
melhor, e a direção é conhecida e medida. Testemunha automatizável: `com.hwloc.lstopo_80283`, único
caso afetado que existe **em dexlib2, no corpus vivo, com 99 execuções**.

**D4 — Serializar o que já se conta.** `ParserDiagnostics.to_dict()` e `TaskResult.write_errors` no
`to_dict()`; `setup_file_logging` chamado em produção; `LogcatRepository.diagnose()` no caminho vivo.
Trabalho pequeno, remove quatro pontos cegos que já têm código escrito.

**[rev. 3] Ressalva sobre o `setup_file_logging`**: não é "religar o que existe". O método tem um
chamador (`manager.py:147`), mas ele está guardado por `if self.log_path:`, e `log_path` só é
atribuído *dentro do próprio* `setup_file_logging` — é um ciclo fechado. Pior: `configure_output`,
o único chamador, também não tem chamador de produção. O reparo é **criar** a chamada num entry
point. E acrescentar chave ao `TaskResult.to_dict()` mexe no formato do `tasks.json`, que o resume
lê — verificar o `from_dict` junto.

**D5 — Procedência nos artefatos. ~~Colunas e checksum.~~ [rev. 3] RETIRADO (decisão do
pesquisador, 28/08).** A proposta era levar `instrumentation_variant`, `specification_set` e
`code_package` para as colunas dos CSVs e para o escopo do checksum. Está retirada, e a verificação
mostra que **também seria inútil**: os dois primeiros campos são lidos *exclusivamente* dentro do
pré-processamento (`get_specs_directory()` só é chamado de `_generate_monitors`;
`instrumentation_variant` só de `_instrument_apks:214`), e o resume **força os três flags de
pré-processamento a `False`** (`__main__.py:1267-1269` e `1282-1284`, INV-EXP-13). Retomar com
`--specification-set jca_android` é inerte: o valor entra no objeto e ninguém o consome. Não há
dano de dados a prevenir. A procedência de run já existe, fora dos CSVs, em
`results/<id>/experiment_config.json`.

Sobrou daí **um achado menor e diferente**, registrado para não se perder: o checksum de resume
**nunca pode divergir**. `set_experiment_metadata` (`platform.py:171`) sobrescreve o valor armazenado
**antes** da comparação (`platform.py:178`), então `check_continuation_compatibility` devolve `True`
sempre e o WARNING de `platform.py:302` é inalcançável em produção. É um defeito de ordenação, de uma
linha. Fora do escopo desta change; anotado aqui para quem for mexer no resume.

**D6 — Contaminação do logcat entre tasks. ~~Filtrar por pid ou pacote.~~ [rev. 3] RETIRADO — o
defeito não existe.** A rev. 2 dizia que "a limpeza de buffer mitiga, não elimina". Verificado no
código: **elimina**, e nem é ela o mecanismo principal. Para uma linha `RVSEC` de outro app entrar no
`.logcat` de uma task seria preciso um segundo APK instrumentado instalado e com processo vivo no
mesmo device durante a captura. Quatro mecanismos independentes impedem isso, cada um suficiente
sozinho:

1. **um emulador por task**, criado e destruído dentro da própria task (`executor.py:388` +
   `emulator_manager.py:133-144`) — o device da task anterior não existe mais;
2. **estado de disco efêmero** — `-read-only` e `-no-snapshot-save` (`android.py:140,144`): mesmo sem
   uninstall, o app anterior não está instalado no device seguinte;
3. **um único install por sessão** (`executor.py:400-407`);
4. **`logcat -c`** no início da captura (`logcat_manager.py:184-191`), com `clean_logcat=True` em todo
   o código de produção.

O que a rev. 2 leu como risco é uma propriedade real do comando (`adb logcat` filtra só por tag) sem
o cenário que a tornaria explorável. A única via que restaria é um `kill_emulator` que falha em
silêncio (`android.py:184-190`) deixando o emulador antigo segurar a porta — patológico, não
rotineiro. Registrado como não-defeito.

**D7 — Fallback do split de frame.** Quando o regex de `(arquivo:linha)` não casa, o frame inteiro vai
para os três campos e entra na chave de identidade da violação. Afeta classes sintéticas do R8 — o
dano cresce com a otimização do APK.

**D8 — Redefinir o portão de cobertura. [rev. 3] FORA DESTA CHANGE.** Depende de Q6, e a
verificação mostra que **não bloqueia nada**: o `CoverageValidator` só roda por invocação manual — é
o subcomando `layer5` do `ValidationCli` (`ValidationCli.java:451-458`). Nem o CI nem o pipeline o
chamam. Redefinir o portão é housekeeping do módulo dexlib2, não pré-requisito de campanha. O bug da
regex que trunca `<init>` (`CoverageValidator.java:51`) é real e de uma linha, e mora no mesmo
arquivo sem uso. Registre-se também o enquadramento: o portão compara contra o **ajc**, que está fora
da mesa de reparo por decisão do pesquisador — ele mede uma diferença permanente entre dois tecelões
que divergem por desenho, não a qualidade do dexlib2.

**D9a — Os dois itens da gh69 que valem sozinhos, e que precisam entrar antes da campanha.** O reparo
`new`→`<init>` (**11 de 68 pares do `jca` e 27 de 113 do `jca_android`** semeiam zero alvos hoje, com
`SecretKeySpec.new`/`IvParameterSpec.new`/`PBEKeySpec.new` entre os mortos) e o log-and-skip do owner
não resolvido (hoje `RandomStringPassword.mop` contribui zero alvos em silêncio, e todo
`cov_reaches_target` medido saiu de 22 das 23 specs do `jca`). Ambos independem do eixo coringa e
mexem em coluna medida — logo são §6.4, não fila.

**[rev. 3] Correção de estado, e ela muda o recorte.** A rev. 2 dizia que a gh69 estava em "1 de 47
checkboxes, zero código". **Está errado.** No `HEAD` são 0 de 47; **na árvore de trabalho são 22 de
47**, com as fases 1, 2 e 3 implementadas e não commitadas no reator Java: `TargetMatching.java`
(novo), `TargetMethod` com `includeSubtypes`/`nameIsPattern`, `TargetResolver`,
`MopSpecsTargetSource`, `ReachabilityEngine`, `UsedJcaMethodsVisitor`, mais seis testes e os dois
`pom.xml`. **Os dois itens do D9a já estão escritos** — `UsedJcaMethodsVisitor.java:118-135` traz o
mapeamento `new`→`<init>` e o log-and-skip do owner não resolvido, este último com o comentário
nomeando o defeito ("*a spec could contribute zero targets forever without anything saying so*").
Falta a **verificação** (fase 4, 4b.4–4b.7 e fase 5), não a implementação.

**Consequência**: o D9a **sai desta change**. Ele se fecha commitando a gh69, não replicando o
reparo. Duplicá-lo aqui criaria duas fontes para o mesmo código.

Nota de estado: o bloqueio que a gh69 registrava — `mop_dir` nunca setado pelo `rv-experiment` —
**caiu**, porque a task 10.0 da gh104 foi entregue (`config.py:987`). O que resta contra fazer a
change inteira agora não é impedimento nem escopo de risco: é **falta de consumidor**. O
`generic_new` só é exercitado por uma campanha genérica que ainda não existe, e o sinal que ele
entrega satura (`reachesTarget` em 84–94%). Recomendação: reescopar a #69 — os dois reparos acima saem
dela e entram no portão da campanha; o eixo coringa fica para quando a campanha genérica for agendada,
e entra com os quatro ajustes que o veredito de 21/08 pede.

**D9b — Corrigir o `CLAUDE.md` do `rv-static-analysis`.** Três cláusulas afirmam o oposto do que o
código faz, e os números da régua de sanidade do `jca_android` erram em 74%. Documentação que induz
ao erro é pior que documentação ausente, e este parágrafo em particular instrui a **não** construir
exatamente o que já está construído.

**D9 — O colapso do denominador no rebaixamento do GATOR. [rev. 4] deixou de ser investigação e
virou reparo de escopo conhecido.** Quatro artefatos do corpus do artigo têm 1, 2, 6 e 21 classes
com a chave correta, e dois deles publicam `cov_class = 100,00%`. O mecanismo está determinado
(§4.3; relatório em `docs/20260828_d9_colapso_denominador.md`): a guarda de
`AnalysisEntrypoint.java:119` compara com o pacote do **manifesto**, e o que ela não protege o
`libPackages.txt` rebaixa a biblioteca. Reparo: consultar ali o `codePackage` do cliente, com
fallback ao manifesto. Um sítio, poucas linhas, no `rvsec-gator`. **Muda medição** — os quatro
denominadores saem de 1 / 2 / 6 / 21 para 771 / 1.971 / 3.589 / 550.

~~Independe de D2 e de D3: o D2 conserta a chave que o cliente usa para filtrar; o D9 conserta a
guarda que decide o que existe para filtrar.~~ **[rev. 5] Independem como sítios de código e são
conjuntivos como efeito.** A guarda reparada lê `codePackage`, e na via de produção `codePackage`
**é** o manifesto: `App.code_package` devolve `self.package_name` quando `package_detector` está
desligado (`app.py:146-147`), que é o default e é a decisão D-A. Logo, sem o D2 a guarda reparada lê
exatamente o valor de hoje e não muda nada. E sem o D9 o D2 também não conserta os quatro: o
`AnalysisEntrypoint` roda antes e já esvaziou a `Scene`, então o filtro do cliente, agora com a
chave certa, encontra 1 classe em vez de 771. **Só os dois juntos devolvem o denominador.** Ver
§15.6 para o que isso muda na verificação.

**D10 — Efeitos colaterais das flags de pré-processamento. [rev. 3] verificado, e encolheu para
três.** A rev. 2 listava quatro armadilhas; uma estava errada e outra tem dono.

1. **`--skip-instrument` mata a análise estática em silêncio — defeito real.**
   `_run_static_analysis` chama `_get_target_apks_for_analysis` (`pre_processor.py:318`), que lista
   `instrumented_apks/`. Sem instrumentação o diretório não existe → `[]` → `logger.warning("No APKs
   available for static analysis")` e retorna. Então `--skip-instrument --static-analysis` é um
   no-op, e o aviso **não nomeia a causa**. Agravante: o cabeçalho do próprio `process()`
   (`pre_processor.py:83-90`) afirma o oposto do que o código faz — *"Step 3: Run GATOR static
   analysis on original APKs (**NOT** instrumented)"* e que a estática está por último *"by
   convention"*, sem dependência do passo 2. Mesma família do D9b.
2. **A INV-EXP-16 não vale — e a rev. 2 descreveu o sintoma errado.** A rev. 2 dizia que
   `--skip-static` faz o experimento rodar sobre APKs **não instrumentados**. **Não faz.** O conjunto
   real de APKs vem de `execution_controller.py:258-260` + `platform.py:350-351`, que fazem glob de
   `out/instrumented_apks` — os instrumentados, que é o comportamento correto. O fallback de
   `pre_processor.py:484-492` é **cosmético**: emite `"No instrumented APKs found, using original
   APKs"`, factualmente falso, e a lista que produz não decide nada. O defeito real é outro e menor:
   a docstring de `pre_processor.py:433-436` afirma que APKs sem `.apk.json` são *"excluded from
   execution"*, o filtro loga a exclusão APK a APK (`:462-467`) — e nada os exclui. No caso misto
   fica pior: um APK sem análise estática entra na execução **com um warning dizendo que foi
   excluído**.
3. **Reuso silencioso de monitores.** Com `--skip-monitors`, o `reset_folder` (`runtime_verification_
   generator.py:143`) não roda, mas `config.py:810-812` e `:883` seguem apontando para
   `out/monitors` — então um diretório remanescente de **outro `specification_set`** é consumido sem
   verificação nem log. (A queda para `_copy_original_apks()` quando faltam monitores é a INV-EXP-08,
   documentada e defensável, com o aviso explícito de que a cobertura será 0%. Não é defeito.)

**Fora daqui**: as env vars de negação. `envvar=ENV_SKIP_STATIC_ANALYSIS` está ligada à forma
**positiva** do par (`--static-analysis/--skip-static`), então fora do Docker
`RV_SKIP_STATIC_ANALYSIS=true` **liga** a análise estática; dentro do container o entrypoint traduz
(`docker-entrypoint.sh:84-88`). O defeito é real, mas já tem casa própria em
`openspec/changes/gh-tbd-env-vars-architecture/` (0 de 37 tarefas), e o próprio comentário do código
o nomeia como gambiarra com escopo à parte.

~~Ordem sugerida: **D1 → D2 → D3 → D9 → D4 → D6 → D5 → D10 → D7 → D8**, com D0 em paralelo.~~

**[rev. 3] A ordem foi decidida pelo pesquisador e é outra — o D9 vem primeiro.** Ver §15.3. A razão
é que a rev. 2 subordinava o D9 à contabilidade, e é o contrário: enquanto o mecanismo do colapso não
for determinado, **não se consegue separar "a chave estava errada" (D2) de "o denominador colapsou"
(D9)** — são causas independentes com o mesmo sintoma, e o corpus tem as duas. Reparar o D2 antes
mede uma melhora que não se sabe atribuir.

**[rev. 4] A investigação foi feita e a razão da ordem se confirmou, com um critério mecânico no
lugar da intuição**: um APK colapsa por D9 se, e somente se, nenhuma classe compilada começa com o
pacote do manifesto **e** o pacote de código casa um padrão de `libPackages.txt`. Sobre os 162, isso
separa os quatro do D9 dos demais denominadores pequenos sem ambiguidade. O D9 continua em primeiro
porque agora *habilita* o D2: com a atribuição decidida, a melhora que o D2 medir é dele.

---

## 12. Não-objetivos e armadilhas

- **Não consertar o ajc.** Decisão do pesquisador. Entra como referência e fonte de atribuição.
- **Não tratar caractere.** A pergunta certa não é "converter `$` ou não", é "qual autoridade responde
  a fronteira pacote/classe". No denominador a autoridade é o artefato do GATOR, e ela já respondeu.
- **Não resolver a chave só com uma lista maior de sufixos.** A lista resolve 162/162 no corpus do
  artigo e 179/219 no amplo; `com.learntube.app` prova que o espaço é aberto (`.debug.$branch`). A
  lista sem portão troca um silêncio por outro.
- **Não excluir APKs para fazer o número fechar.** Foi a recomendação de 2025 e já aconteceu por outra
  via — o funil do artigo tirou 55 apps pelo portão do denominador. Os APKs afetados são a testemunha
  do reparo.
- **Não tratar `mop_errors_total > 0` com `cov_method == 0` como anomalia de app.** É o sinal mais
  forte disponível de que o cruzamento falhou. Já foi tratado assim uma vez, em `broken_apks.csv`, e
  custou o descarte de dois APKs válidos.
- **Não tratar `cov_method == 0` como acusação automática.** Há pelo menos **quatro** causas
  distintas — denominador vazio pela chave, chave inalcançável pelo normalizador, colapso do
  denominador no rebaixamento do GATOR, e escopo legítimo do tecelão — e uma delas não é defeito:
  `com.google.android.stardroid_1678` tem denominador correto (705 classes), zero violações e 0% em
  99/99, porque o `PackageFilter` exclui `com.google` por projeto.
- **Não confundir "a chave estava errada" com "o denominador colapsou".** São causas independentes, e
  o corpus tem as duas. **[rev. 4]** Ambas são reparáveis por regra, e o critério que as separa é
  mecânico: o colapso exige que nenhuma classe compilada comece com o pacote do **manifesto** e que
  o pacote de código case um padrão de `libPackages.txt`. Se só a primeira condição vale, é a chave.
- **[rev. 4] Não atribuir o colapso ao Soot nem ao multidex.** `set_process_multiple_dex` não existe
  no Soot 4.7.1, o Soot lê os 18 DEX e marca as 36.800 classes como aplicação, e o rebaixamento é
  código nosso. A hipótese durou duas revisões porque ninguém tinha instrumentado uma corrida.
- **Não tomar "`Mneut` cobre 100% das classes" como prova de que a chave foi `Mneut`.** `Mneut` é
  prefixo da chave sufixada, então um resíduo passaria no mesmo teste. O teste discriminante é
  "existe classe sob o prefixo sufixado?" — e a resposta, em 231 artefatos, é não.
- **Não confiar em "a aritmética fecha".** INV-ANA-62 fecha e a cobertura está errada; o descarte
  acontece depois do parser.
- **Não confiar na mediana global.** Trocar a chave em 30 de 219 APKs mudou 26 medianas por APK, com
  fatores de ×7 a ÷5,6, e moveu a mediana global de 17,63 para 17,92.

---

## 13. Âncoras e medições

### Medições da rev. 6 (30/08/2026) — a implementação medida

Corridas reais desta implementação. Evidência bruta em
`openspec/changes/gh111-cadeia-medicao/evidence/`.

- **aceitação do D9** (`evidence/acceptance/`): `com.github.cvzi.screenshottile_148` sob
  `--package-detector`, chave eleita `com.github.cvzi`, `len(reachability)` **21** com o jar
  pré-mudança e **535** com o reconstruído. Artefato pós: `codePackage=com.github.cvzi`,
  `codePackageSource=detector`, `class_defs_under_key=539`, zero classes `R`/`BuildConfig`/`Manifest`.
  Os quatro logs mostram `Executing analysis` e nenhum mostra `Analysis result already exists`.
- **controle** `me.zhanghai.android.untracker_9`: **330** dos dois lados do rebuild,
  `class_defs_under_key=332`.
- **shas dos jars**: pré `4708d63c…` (gator) / `dab75ca7…` (client); pós `6ce00738…` / `df18057e…`.
- **api level**: derivado do `apktool.yml` de cada APK, não fixo — `android-36` para o
  `screenshottile`, `android-37` para o `untracker`. Os `android-35` são das corridas da sonda.
- **D3 sobre os 162**: **215.430** classes parseadas, **0** artefatos parseando para zero, **0**
  nomes inventados pelo parser (eram 465 em 7 APKs). Instrumento: parsear cada artefato e comparar
  o conjunto de nomes parseados contra o conjunto que o próprio arquivo carrega.
- **custo, e a assimetria que o explica**: no mesmo `screenshottile`, com tudo igual, a perna
  **pré** levou **91 s** e a **pós** levou **3.141 s** — 34×. Não é ruído: sob o jar pré-mudança a
  guarda compara contra o manifesto, rebaixa todas as classes do app a biblioteca e o Soot analisa
  quase nada; sob o jar reconstruído as 535 classes ficam na Scene e o grafo de chamadas é
  construído sobre elas. **O custo de uma análise é fixado por quantas classes sobrevivem ao
  rebaixamento**, que é exatamente a grandeza que esta change repara. É o que dimensiona a tarefa
  3.15: a perna de *baseline* dela roda sob a chave com sufixo, onde nada casa — o lado barato; a de
  *tratamento* roda sob a chave neutralizada, com o universo inteiro do app na Scene — o lado caro,
  30 a 60 min, e uma das duas corridas aqui não terminou dentro de uma hora. A âncora da gh91
  (1.800–5.400 s por APK) descreve bem a perna de tratamento.
- **a perna pós do controle estourou o timeout de 3.600 s** e seu artefato é truncado: sem o flag
  `complete` e com `transitions` vazio. O 330 continua sendo o número certo — `reachability` é a
  primeira seção que o escritor descarrega, por desenho (INV-ANA-06) —, mas a comparação não é
  simétrica: uma corrida `--skip-wtg` completa contra uma corrida cheia truncada. Um controle limpo
  refaria a perna pós com `--skip-wtg`. Registrado, e não apresentado em silêncio como um par.
- **decomposição cru → entregue** (`evidence/probe/README.md`, sonda): petals 771 → 762, unchained
  1.971 → 1.952, feeder 3.589 → 3.578, screenshottile 550 → **535**, pachli 6.467 → 6.336. As três
  primeiras não se movem sob o alargamento da INV-ANA-71 porque suas classes de recurso já estavam
  na raiz da chave; as duas últimas são as que carregam o argumento inteiro.

### Medições e leituras da rev. 5 (29/08/2026) — a cadeia de identificadores e a procedência da lista

Nenhuma medição nova sobre o corpus: são leituras de código feitas para escrever a change, e três
delas contradizem a rev. 4.

- **`App.code_package` é o manifesto por default**: `app.py:146-147` — `if not self.package_detector:
  return self.package_name`. O único produtor de um `codePackage` diferente do manifesto, hoje, é o
  `package_detector`, que a decisão D-A aposenta. Logo o D9 sozinho é inerte na via de produção.
- **A cadeia `codePackage`**: `app.py:132` → `static_analysis.py:277` → `config.py:395-397`
  (`-clientParam codePackage=`) → `Configs.clientParams` → `RvsecAnalysisClient.java:244-250`. O
  `AnalysisEntrypoint` não aparece nessa cadeia.
- **`SignatureNormalizer` tem um consumidor**: grep por
  `signature_normalizer|SignatureNormalizer|normalize_signature|normalize_parameter` em
  `modules/*/src` devolve só `static_analysis_parser.py` (7 linhas, 1 import, 1 campo, 2 chamadas,
  3 docstrings).
- **A assinatura não é normalizada**: `static_analysis_parser.py:390` guarda `signature=signature`;
  `repository_initializer.py:61-71` chaveia `MethodCoverageData` por essa assinatura verbatim.
- **`Coverage.aj:64` usa `getDeclaringClass().getName()`** — idêntico nos três `Coverage.aj` gerados
  do acervo. Refuta a atribuição do `$` ao AspectJ feita em `docs/NOVO/06_normalizacao_inner_classes.md`.
- **`SignatureFormatter.toFqn`** (dexlib2) converte o descritor DEX no ponto de emissão: tira `[`
  contando profundidade, mapeia os primitivos de uma letra, e para referências pega `L…;` e troca
  `/` por `.`. **O descritor DEX nunca escapa do tecelão.**
- **`libPackages.txt`**: 2.170 linhas, **todas** terminadas em `.*`; zero em `$*`; zero nomes exatos.
  127 de um segmento (`c.*`, `a.a.*`, `domain.*`, `flow.*`), 2.043 de dois. `git log --follow`
  devolve um único commit, `d94e33cc` (25/09/2024). md5 `9296d262…` nas duas cópias. Cadeia de forks
  em `sootandroid/README.md`: OSU → `limerick1718` → `phtcosta` → aqui.
- **A denylist casa com fronteira de ponto**, a guarda não: `Configs.isLibraryClass:176-186` faz
  `startsWith(pkg.substring(0, len-1))` e o padrão termina em `.*`, então o ponto sobrevive;
  `AnalysisEntrypoint:119` faz `startsWith(appPkg)` cru.
- **`processLibraryPkgFile` engole exceção**: `catch (Exception e) {}` vazio em `Configs.java:200-203`.
  Arquivo ausente → lista vazia → default de dois padrões → denominador inflado, em silêncio.
- **A semeadura de alvos ignora parâmetros no caminho normal**: `TargetMethod.MatchPolicy.LENIENT`
  casa `(owner, nome)`; `TargetResolver.paramsMatch` só roda no STRICT, comparando
  `method.getParameterType(i).toString()` com a string declarada. E `MopMethod.signature` é o **texto
  do pointcut** (`MethodPattern.toString()`), nunca usado para casar — é registro, não chave.

### Medições da rev. 4 (28/08/2026, fim de tarde) — a investigação do D9

Relatório completo em `docs/20260828_d9_colapso_denominador.md`; sonda em
`docs/20260828_d9_colapso_denominador/D9Probe.java`.

- **carga do Soot (sonda, `petals`, 13 s)**: `Scene=38932 app=36800 lib=2055 phantom=77`. O Soot
  carrega **as 36.800 classes dos 18 DEX** e marca **todas** como aplicação. **771** delas estão sob
  `br.com.colman.petals` antes do rebaixamento.
- **o rebaixamento**: com a guarda em `br.com.colman.petals.debug` (o manifesto) → **33.089**
  rebaixadas, `#AppClasses = 3711`, **1** sob o prefixo do app. É byte a byte o `#AppClasses` do log
  da campanha (`SA_RERUN_gh91/logs/br.com.colman.petals_3040000.apk.log:47-49`). Com a guarda em
  `br.com.colman.petals` (o `codePackage`) → 32.319 rebaixadas, `#AppClasses = 4481`, **771** sob o
  prefixo.
- **os quatro e o controle** (denominador de classes, guarda=manifesto → guarda=`codePackage`):
  `petals` 1 → **771**; `unchained` 2 → **1.971**; `feeder.play` 6 → **3.589**;
  `screenshottile` 21 → **550**; e `app.pachli` 6.467 → **6.467** (invariante — mesmo sufixo de
  build-type, guarda igualmente morta, mas `app.pachli` não casa `libPackages.txt`).
- **as classes do artefato são as `<activity>` do manifesto sob o pacote do app**, nome a nome:
  `petals` 4 activities / 1 sob o pacote / 1 no artefato; `unchained` 3 / 2 / 2;
  `feeder.play` 10 / 6 / 6; `screenshottile` 23 / 21 / 21. *Receivers*, *services* e *providers* do
  app estão ausentes, porque o ramo de resgate só lê `<activity>`.
- **previsão sobre o corpus**: dos 162, **75** têm a guarda morta, **10** casam `libPackages.txt`, e
  a conjunção dá **exatamente os 4** — sem falso positivo nem falso negativo. Os 6 que casam a lista
  sem sufixo têm 330 a 3.300 classes.
- **sobre os 219 executados**: **119** com guarda morta, **27** com o pacote sob um padrão da lista
  (`info.metadude.*` 13, `io.github.*` 5, `com.github.*` 4, e mais 5), e **4** com a conjunção e
  denominador não-vazio — os mesmos quatro, todos `selected`. Outros 14 satisfazem a conjunção mas
  têm `A(Mneut) = ∅`: são defeito de chave (D2), não de classificação.
- **DEX do `petals`**: `classes.dex` 17.076 classes / 0 do app; `classes2` 407 / 8 do app;
  `classes3..14` 763 do app; `classes15..18` 18.554 / 0 do app. Total 36.800.
- **`multiple_dex` não existe no Soot 4.7.1**: a string não aparece em nenhum dos 2.759 `.class` do
  pacote `soot/` do jar (controle: `process_dir` aparece em `Scene`, `Main`, `PackManager`,
  `Options`); `soot.dexpler.DexFileProvider.acceptFile` é `{ return true; }`.
- **os três `-exclude` são inertes**: diferencial no `petals` — `kotlin.`/`kotlinx.`/`androidx.compose.`
  → `app=36800`; os mesmos com `.*` → `app=12842`, `lib=26013`.

### Medições da rev. 3 (28/08/2026, tarde) — reproduzidas por mim sobre o corpus

Corpus: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`
(162 `.apk.json`, 162 `.apk`; `reachability` vazio em 0 deles).

- **chave**: manifesto é prefixo de ≥1 classe em **87**; não é prefixo de classe nenhuma em **75**.
  Confere com a rev. 2 e com o gh102. Os 75 têm todos manifesto sufixado e **zero** classes sob o
  prefixo sufixado — o teste discriminante da §3.3 confirmado por medição independente.
- **denominador**: 215.430 classes no total; min **1**, p10 **102**, mediana **671**, máx **14.860**;
  **6** APKs com ≤30 classes, **16** com ≤100. Os oito menores:
  `petals` 1/35, `unchained` 2/45, `feeder.play` 6/115, `passportreader` 18/77,
  `screenshottile` 21/394, `org.cry.otp` 23/97, `lstopo_80283` 37/182, `barcodescanner` 51/246
  (classes/métodos).
- **normalizador**: rodando `SignatureNormalizer.normalize_class_name` de produção sobre todo
  `className` de todo `reachability[]`, **465 de 215.430 classes (0,22%) em 7 de 162 APKs** —
  `quicksearch` 305/6059 (5,0%), `deku` 75/505 (14,9%), `bitbanana` 35/2147 (1,6%),
  `owncloudnewsreader` 19/528 (3,6%), `mtgfam` 15/457 (3,3%), `packagemanager` 14/390 (3,6%),
  `lstopo_80283` 2/37 (5,4%). Lista e frações idênticas às da rev. 2.

### Medições das rev. 1 e 2 (27–28/08/2026)

**Corpus e campanhas**
- campanha do artigo: 219 APKs × 11 tools × 3 reps × 3 timeouts = **21.681 tasks**; 16
  `experiment_config.json`, todos com pré-processamento desligado
- base publicada: `ase-journal/dataset/results/summary.csv`, **16.137 runs / 163 APKs**;
  `cov_method` médio **21,881%** (bate com o `21.88%` da prosa)
- funil: 219 → 164 (`keep(Mneut)`) → 163; **`\denomScopeExcl` = 55**
- 235 logcats sem `RVSEC-COV` (1,08%), 189 determinísticos (`qtesting` × `activity-alias`)

**A chave de escopo**
- `FINAL_selected162`: manifesto cru cobre 100% das classes em **87/162**; `Mneut` em **162/162**
- `experimento-20260706` (219): manifesto 99, `Mneut` 179, **40 (18,3%) que nenhuma regra de string
  resolve**
- censo de sufixos (162): 60 `.debug`, 7 `.dev`, 4 `.beta`, 1 `.current`, 1 `.BETA`, 1 `.qa.debug`,
  1 flavor divergente = **75**
- **0 classes** de qualquer artefato começam pelo package registrado em `package`; **162/162**
  começam pelo `Mneut`
- gh91 antes/depois (só a chave muda): **26 de 219** medianas de `cov_method` alteradas;
  `org.fossify.paint` 5,07 → 35,57; `org.fossify.math` 8,76 → 42,01; `com.jerboa` 50,87 → 17,75;
  `swati4star.createpdf` 20,00 → 3,60; `org.wikipedia` 0,00 → 0,89 (era `cov==0` **com** violações);
  mediana global 17,63 → 17,92

**O normalizador**
- acervo de calibração: **413 classes (1,09%), 2.725 métodos (1,41%), 9 de 195 APKs**, sobre 8.328
  artefatos
- corpus do artigo: **7 de 162 APKs, 465 de 215.430 classes**, de 1,6% a 14,9%
- lstopo dexlib2 (`com.hwloc.lstopo_80283`, 99 logcats): 9.902 linhas `RVSEC-COV`, **todas `I`**;
  **1.080** ocorrências de `ZoomView.ZoomView` com ponto, **0** com cifrão; GATOR co-locado 42 com
  ponto e 5 com `$` (aninhamento genuíno) — **medição pendente da rev. 1, fechada**
- o normalizador também corrompe o caso já correto:
  `...ZoomView.ZoomView$ZoomViewListener` → `...ZoomView$ZoomView$ZoomViewListener`

**O artefato da análise estática**
- 7 chaves de topo, invariantes em **381 artefatos**; `reachability` = 76–78% dos bytes
- `complete: true` em 219/219, 162/162 e nos 30 `.pkgdet`; **nenhum artefato incompleto**
- `transitions == 0` em **83/219 (37,9%)**; `windows == 0` em 0; `widgets == 0` em 65/219
- distribuição (219): classes min 1 / mediana **707** / máx 14.860; métodos min 24 / mediana **3.883**
  / máx 62.448; soma 295.096 classes e 1.454.628 métodos
- `reachesTarget ≥ 1`: **219/219 e 162/162** — o critério transitivo é vácuo
- `directlyReachesTarget ≥ 1`: **94/219 (42,9%)**; soma de 469 métodos no corpus inteiro
- a troca de chave do gh91 moveu o denominador do mesmo APK em **+35.060 métodos**
  (`org.wikipedia`: 4.890 → 39.950) e em **−9.649** (`org.fossify.paint`: 10.096 → 447)

**Denominadores degenerados e saturação**
- **0 de 21.681** linhas de summary com métrica > 100%
- `cov_class == 100%`: 186 linhas / **2 APKs**, ambos com denominador de 1 e 2 classes
- `cov_act == 100%`: 6.540 linhas / 97 APKs
- distribuição de classes no denominador (162 APKs): min **1**, p10 102, mediana **671**, máx 14.860;
  6 APKs ≤ 30 classes, 16 ≤ 100
- colapso idêntico em ajc e dexlib2: petals 1/1, unchained 2/2, feeder.play 6/6, screenshottile 21/21
- `petals`: log do GATOR com a chave **certa** (`Filter package: br.com.colman.petals`),
  `Processed classes: 3711`, `Application classes: 1`; APK define **36.800 classes em 18 DEX**;
  **551 classes sob `br.com.colman.*` executadas** numa corrida de 300 s
- ~~`set_process_multiple_dex` **nunca é chamado** (5 usos de `Options.v()` em toda a árvore); a
  hipótese "só lê `classes.dex`" está **refutada** (58 de 60 APKs têm 0 ocorrências do prefixo em
  `classes.dex`, inclusive os saudáveis)~~ — **[rev. 4] a observação é certa e irrelevante**: a opção
  não existe no Soot 4.7.1, e o Soot lê os 18 DEX. Ver as medições da rev. 4 abaixo

**O cruzamento**
- varredura de **22 APKs × todos os logcats = 11.598.621 linhas `RVSEC-COV`**
- **87.761 de 170.131 assinaturas distintas (51,6%)** sem correspondente literal no denominador
- por APK: mín. 17,67% · mediana **59,95%** · máx. 99,82%; ponderada por linha, mediana 64,38%
- classes ausentes: **21.422 de 45.365 (47,2%)**
- decomposição: **82.064 fora do escopo (95%)** × **4.212 dentro do escopo (5%)**, dos quais 4.192
  (99,5%) em três artefatos colapsados (petals 1.908, unchained 1.348, screenshottile 936)
- nos APKs saudáveis a lacuna dentro do escopo é de **1 ou 2 assinaturas**, sempre `BuildConfig` e
  `R$styleable` — que o `isAppClass` exclui e o instrumentador tece
- **0 assinaturas não parseáveis** em 11,6 milhões de linhas
- denominador co-locado × atual difere em **4 de 22** APKs; `org.wikipedia` 93,17% → 43,06%

**Granularidade**
- `jca`: 120 assinaturas carregadas → **68 pares** `(classe, método)` → 76 `SootMethod` resolvidos;
  **11 pares mortos** por `<init>`. `jca_android`: 207 → **113** → 27 mortos. `generic`: 296 → 284 → 46
- inflação do LENIENT contra `android.jar` API 30: `jca` **1,121×** (17 extras em 13 pares);
  `jca_android` **1,072×**
- **90% dos pointcuts escrevem a lista de tipos** (130/144 no `jca`, 207/221 no `jca_android`); só
  9,7% e 6,3% usam `..`
- denominador por assinatura × por nome, nos 162: `total_methods` **1.058.685 × 982.521 (−7,19%)**;
  `total_target_methods` 308.881 × 286.611 (−7,21%); 70.466 pares com >1 assinatura; **5.691 pares
  mistos em `reachesTarget`**; 158 de 162 APKs têm ao menos um par sobrecarregado
- numerador: 514.323 `(apk, signature)` × 487.471 `(apk, class, method)` — **5,22%**
- violação: 629 triplas distintas; **392 (62,3%) de classes ausentes do denominador**; 3 (0,5%)
  ambíguas entre sobrecargas — **5,26% das resolvíveis**
- 300 sítios `new ErrorDescription(...)`: o campo de localização é **sempre** `"" + __LOC`
  (jca 50/50, jca_android 250/250); nenhuma spec usa `thisJoinPoint`
- `RandomStringPassword.mop` contribui **zero alvos**: todo `cov_reaches_target` medido saiu de
  **22 das 23 specs** do `jca`

**A chave: teste discriminante**
- **0 de 231** artefatos com sufixo no manifesto têm qualquer classe sob o prefixo sufixado
  (162 dexlib2 + 106 ajc + 219 dexlib2, somando 231 casos sufixados)

**Outras**
- 1.618.087 linhas `RVSEC-COV` reais, 100% no formato Soot, 0 no formato `:::`
- acervo misto: amostra de 60 logcats → 50 dexlib2 (`I`), 10 ajc (`V`)
- par controlado ajc×dexlib2: 135 vs 378 distintas, interseção 132, recall 0,9778 (portão 0,99)
- `com.google.android.stardroid_1678`: 705 classes, `complete: true`, 0 violações, **0% em 99/99** —
  causa legítima (`PackageFilter` exclui `com.google`)

### Código — fluxo do rv-experiment
`rv-experiment/__main__.py:394-766,1147,1258-1299`; `experiment/experiment_controller.py:137-223,241-311`;
`experiment/workflow/pre_processor.py:63-120,122-180,182-267,269-289,291-392,394-428,430-494`;
`experiment/workflow/post_processor.py:91-126`; `execution_controller.py:100-147,219-260,307-318`;
`rv-platform/platform.py:128-205,207-266,268-333,335-367,369-479,624-655`;
`rv-platform/execution/executor.py:181-270,286-363,365-468`;
`rv-platform/components/static_analysis.py:67-98,109-168,170-246`;
`rv-platform/storage/task_storage.py:58-89,912-954`; `docker/rvandroid/docker-entrypoint.sh:84-88`

### Código — a chave
`rv-android-core/domain/app.py:62-68,121-128,130-150,152-162`;
`rv-static-analysis/analysis/static/static_analysis.py:234-243,270-276,283-289`;
`rv-static-analysis/config.py:393-397`;
`rvsec-gator/client/.../RvsecAnalysisClient.java:85-90,256-270,277-286,1325`;
`rvsec-gator/client/.../json/JsonReportWriter.java:84`;
`rvsec-gator/client/.../reach/ReachabilityEnricher.java:92-105`;
`ase-journal/data-analysis/mneut_scope.py:69-102,150-157,180-191`;
`scripts/gh91_sa_rerun.py:279,344,634`; `scripts/gh91_record.py:192-195,210-222`;
`rvsec-dataset/src/rvsec_dataset/build/builder.py:154-160`;
`openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/proposal.md`;
`openspec/changes/archive/2026-08-07-gh98-manifest-package-default/design.md:87,202`;
`openspec/changes/archive/2026-08-16-gh102-artifact-scoped-parse/proposal.md:9`

### Código — o artefato, o carregamento e o rebaixamento
`rvsec-gator/client/.../json/JsonReportWriter.java:84-86,94-96,100-101,105-106,110-115,122,148-152`;
`rvsec-gator/client/.../json/JsonSchema.java:28-104`;
`rvsec-gator/client/.../RvsecAnalysisClient.java:165-208,283-285,297-309,1301-1359,1361-1382,1426-1546,1690-1739`;
`rvsec-gator/client/.../reach/ReachabilityEngine.java:63-95`;
`rvsec-gator/.../Main.java:286-287`; `rvsec-gator/.../Configs.java:250-252` (os cinco únicos usos de
`Options.v()`; `set_process_multiple_dex` ausente — **[rev. 4]** e a opção não existe no Soot 4.7.1);
**[rev. 4]** `rvsec-gator/.../AnalysisEntrypoint.java:77-82,87-94,96-106,111-126,129-130` (o
rebaixamento e a guarda); `rvsec-gator/.../Configs.java:176-186,188-204,292`
(`isLibraryClass`, `processLibraryPkgFile`, `getClientParamCode`);
`rvsec-gator/.../Main.java:117-121,214-230` (`-libraryPackageListFile` e os três `-exclude` inertes);
`rvsec-gator/.../Hierarchy.java:299-323`; `rvsec-gator/.../gui/Flowgraph.java:261,462-464`;
`rvsec-gator/client/.../RvsecAnalysisClient.java:86-90` (a outra chave de escopo);
`rv-android/lib/gator/{gator:90-101,libPackages.txt}`;
`docs/20260828_d9_colapso_denominador.md` e a sonda em `docs/20260828_d9_colapso_denominador/`;
`ase-journal/data-analysis/stage_denominator_scope.py:26-38`; `.../reduce_to_163.py`;
`SA_RERUN_gh91/{REGISTRO.md,logs/*.log,record/sa_rerun_record.csv}`;
`docs/20260812_registro_execucao_prontidao_e3.md:309-330`;
`experimento-comp162-ajc/analise_previa/20260813_checks_offline_75.md:82-101` (atribuição refutada)

### Código — granularidade
`rvsec-gator/client/.../target/MopSpecsTargetSource.java:31,34-39,41`;
`.../target/TargetResolver.java:17-18,46-70,71-84`; `.../target/TargetMethod.java:22-27`;
`.../target/SignatureFileTargetSource.java:87-96`; `RvsecAnalysisClient.java:118,571-604,624-626`;
`.../target/MopSpecsParityTest.java:85`;
`rvsec-mop-extractor/.../UsedJcaMethodsVisitor.java:38,70-77,80-90`;
`rv-android-core/.../domain/classes.py:128-150,210-211,435-441`;
`rv-android-core/.../domain/coverage.py:222-224,275,665,879-890`;
`rv-android-core/.../util/android/repository_initializer.py:60-70`;
`rv-static-analysis/.../static_analysis_parser.py:378-392`;
`dexlib2/.../coverage/SignatureFormatter.java:27-40,43-69`; `rv-coverage/.../logcat_parser.py:695-702`;
`rv-android-core/.../domain/log.py:443-445`;
`rv-monitor/.../output/monitor/BaseMonitor.java:501-502`; `.../HandlerMethod.java:45`;
`.../RawMonitor.java:104-105`; `.../output/Util.java:7-8`;
`rv-monitor-rt/.../ViolationRecorder.java:53-60,99-116`; `rvsec-core/.../ErrorDescription.java:26,128-146`;
`rvsec-core/.../ErrorSummary.java:105-164,176-178`;
`openspec/changes/gh69-generic-subtype-target-matching/{proposal.md:191-208,design.md:215-226,tasks.md}`;
`openspec/changes/gh104-legible-violation-reports/tasks.md:264` (task 10.0, entregue) +
`.../tasks/E10-integration.md:7` + `.../design.md:99,582`;
`rv-experiment/config.py:645-704` (`resolve_spec_set_dir`, sem entrada para `generic_new`), `:968-992`
(`mop_dir` resolvido); `rv-static-analysis/config.py:196-207` (o default literal que a 10.0 deixou de
alcançar);
`docs/20260821_gh69_veredito_coringas.md`; `docs/adr/0004-*.md:40`;
`modules/rv-static-analysis/CLAUDE.md:27-28` (as três cláusulas falsas e a régua vencida)

### Código — cobertura
`coverage-weaver/CoverageWeaver.java:120-135,189-190`; `SignatureFormatter.java:43-69`;
`PackageFilter.java:22-43`; `monitor-builder/CoverageSourceEmitter.java:47,55`;
`validator/CoverageValidator.java:51`; `advice-emitter/.../SignatureFormatterTest.java:76-82`

### Código — violação
`rvsec-logger-logcat/.../ErrorCollector.java:53,66-72,83-85`;
`rvsec-core/.../ErrorSummary.java:96-103,177`; `rvsec-core/.../ErrorDescription.java:26,128-146`;
`rv-monitor/.../BaseMonitor.java:501-502`; `rv-monitor/.../Util.java:7-8`;
`rv-monitor-rt/.../ViolationRecorder.java:53-60,99-116`;
`rv-coverage/.../logcat_parser.py:52-97,575-606,699-712`; `rv-android-core/.../domain/log.py:157-160`;
`rv-android-core/.../domain/coverage.py:676-688,733-748`;
`rv-android-core/.../util/android/logcat_manager.py:194-212`

### Código — cruzamento e relatório
`rv-android-core/.../signature_normalizer.py:246-312`;
`rv-android-core/.../domain/coverage.py:402-449` (`_percentage` em `:446-449`), `:453-521`,
`:640-674` (descartes em `:660` e `:672`), `:720-748`, `:895-930` (`diagnose`);
`rv-android-core/.../domain/task.py:353-356,429-452`;
`rv-static-analysis/.../static_analysis_parser.py:1-52,365-396`;
`rv-platform/.../result_processor.py:47-61,151-213,245-325,407-453,572-610,714-760,823-868,929-981,1150-1161`;
`rv-platform/.../performance_processor.py:84-94`;
`rv-android-core/.../util/logging/manager.py:153-200`

### Referência histórica
`rvsec-regerar-resultados/docs/NOVO/06_normalizacao_inner_classes.md` (`:101-107`, `:220-244`);
`.../07_pacotes.md`; commit `16ca70b2` (20/02/2025)

### Documentos companheiros
`docs/20260827_relatorio_final_validacao_jca_android.md` — a validação das 48 specs `jca_android`, com
os reparos R1–R6 e as decisões D-1…D-* **já adjudicados**; é ele que define o que a campanha vai
acusar. Os dois de gravidade ALTA que tocam esta cadeia: **R1** (`:88-102`, `getEntry`/`setEntry`
nunca tecem sob dexlib2 → FN silencioso e `KEYSTORE-ORDER-00` falso) e **R6** (`:159-176`, a
divergência `after()`, com a opção (b) já escolhida como reparo).
`openspec/changes/gh109-crysl-coverage/` — a change que produz o conjunto `jca_android` da campanha
(59 de 66 tarefas em 28/08).
`docs/20260827_achados_instrumentador_dexlib2.md` — o tecelão de advice.
`docs/20260827_divergencia_after_dexlib2_ajc.md` — a semântica `after`/`finally`.
`experimento-20260706/docs/residual/{NOCOV_LOGCATS.md,ZEROCOV_STARDROID.md}` — as perdas já
documentadas pela campanha.

---

## 14. Procedência desta análise

A rev. 1 foi levantada por sete auditorias paralelas de subagentes. A rev. 2 acrescenta seis, e
**re-verifiquei diretamente na fonte primária** todos os achados de maior consequência.

**[rev. 4] Verificado nesta revisão — tudo por leitura direta e medição própria, sem subagente:**

- o laço de `AnalysisEntrypoint.java:111-126` e o `Configs.isLibraryClass` lidos na fonte;
- `soot.Scene.loadNecessaryClasses`, `soot.SourceLocator.getClassesUnder`,
  `soot.dexpler.DexFileProvider.{getDexFromSource,mappingForFile,acceptFile}` e `soot.Scene.isExcluded`
  lidos por `javap` sobre o `soot-4.7.1.jar` do repositório local, porque não há jar de fontes;
- **a corrida instrumentada**: sonda própria (`docs/20260828_d9_colapso_denominador/D9Probe.java`)
  contra o fat jar já construído, cinco execuções (os quatro colapsados e o controle `app.pachli`),
  reproduzindo `#AppClasses = 3711` e os denominadores 1 / 2 / 6 / 21;
- o diferencial dos `-exclude` com e sem `.*`, na mesma sonda;
- o mapa dos 18 DEX do `petals`, por leitura própria dos cabeçalhos (`class_defs`, tabela de tipos);
- a previsão sobre os 162 e sobre os 219, esta última importando `mneut_scope` do repositório do
  artigo (leitura, sem escrita);
- que `mneut_scope.classes_under` opera sobre `dex_classes.zip` e não sobre artefato do GATOR — que é
  o que derruba a atribuição dos 33 `denominator_collapse` ao D9.

**Não verificado na rev. 4, e declarado como tal:** as contagens de **método** com a guarda correta.
A sonda não constrói corpos nem grafo de chamadas; só as contagens de **classe** são medidas. Os
números de método dos quatro só saem de uma corrida completa do GATOR, que leva ~40 min por APK.

**[rev. 3] Verificado nesta revisão, com comando reproduzível ou leitura direta:**

- as três medições de corpus da §13 (chave, denominador, normalizador), executadas por mim;
- o ciclo de vida do emulador que refuta a contaminação do logcat (`executor.py:388,400-407`,
  `emulator_manager.py:133-144`, `android.py:140,144`, `logcat_manager.py:184-191`);
- o comportamento real das três flags `--skip-*` e a contradição entre `pre_processor.py:83-90` e
  `:318`/`:406-412`; que o conjunto executado vem de `execution_controller.py:258-260` +
  `platform.py:350-351`, e não da lista filtrada;
- que o resume força os três flags de pré-processamento a `False` (`__main__.py:1267-1269`,
  `1282-1284`) e que `specification_set`/`instrumentation_variant` não existem no `PlatformConfig`;
- que o checksum de resume nunca diverge (`platform.py:171` antes de `:178`);
- que a gh69 tem 22/47 na árvore de trabalho e que `UsedJcaMethodsVisitor.java:118-135` já traz o
  `<init>` e o log-and-skip;
- que o `CoverageValidator` só é alcançável pelo subcomando manual `layer5`
  (`ValidationCli.java:451-458`);
- que os reparos de spec estão mapeados no G8 da gh109 e que nenhum foi aplicado no reator;
- que não existe nenhuma regra de neutralização de sufixo no `rv-android`, só no `mneut_scope.py`
  do repositório do artigo;
- que o `ajc_instrumentation.py:854-900` usa `code_package` como guarda anti-quarentena.

**Verificado na rev. 2, com comando reproduzível:**

- o censo de sufixos e a cobertura das chaves nos seis diretórios de APKs instrumentados;
- que zero classes começam pelo package registrado e 162/162 começam pelo `Mneut`;
- a regra `neutralize` lida diretamente em `ase-journal/data-analysis/mneut_scope.py:97-102`, e o
  portão `keep(X)` em `:180-191` (que depende de ground truth adjudicado);
- o antes/depois do gh91 sobre `summary_all{,_pre_gh91}.csv` (26 medianas alteradas);
- a corrupção do normalizador sobre os 162 artefatos do corpus do artigo (7 APKs, 465 classes),
  executando o normalizador de produção sobre os nomes reais;
- a medição dexlib2 do lstopo (9.902 linhas `I`, 1.080 com ponto, 0 com cifrão, 99 logcats);
- os denominadores degenerados e a distribuição de classes; as 0 linhas > 100% e as 186 em 100%;
- as 16 configurações de campanha com pré-processamento desligado;
- a base do artigo (16.137 runs / 163 APKs / 21,881%);
- **o teste discriminante da chave** (0 de 231 com classe sob o prefixo sufixado) e os nomes de
  classe dos cinco artefatos colapsados, que refutam a atribuição ao sufixo feita em
  `experimento-comp162-ajc/analise_previa/20260813_checks_offline_75.md:82-101`;
- o log do GATOR do `petals`, verbatim, com a chave correta e `Application classes: 1`;
- os quatro sítios que estabelecem as duas granularidades: `MopSpecsTargetSource.java:34-39`
  (LENIENT hard-coded), `TargetResolver.java:46-70`, `classes.py:128-150,435-441` e `coverage.py:665`;
- que a task 10.0 da gh104 **foi entregue** (`tasks.md:264` marcada, `config.py:987` no lugar), o que
  invalida a razão de bloqueio registrada na `proposal.md` da gh69, e que `resolve_spec_set_dir`
  (`config.py:645-704`) não tem entrada para `generic_new`;
- os sítios de código citados em §2, §3.2, §3.7 e §4.6.

**Relato de subagente, com âncora, não re-verificado por mim:** os totais agregados sobre 8.328
artefatos do acervo de calibração e a lista dos 9 APKs; a medição do par controlado ajc×dexlib2; o
levantamento das claims do artigo por arquivo `.tex`; o inventário de `data/results/_analysis`; a
comparação por AST do normalizador com o histórico; o levantamento do elo de violação; a varredura
das 11.598.621 linhas do cruzamento e sua decomposição escopo × lacuna; o censo de 381 artefatos e a
distribuição dos três predicados de alcance; a contagem de `class_defs_size` do `petals`; e o
mapeamento do fluxo do `rv-experiment` da §2 (verifiquei por amostragem os sítios que sustentam
conclusões, não os 26 itens da tabela de flags).

**Não verificado, e declarado como tal:**

- nenhum número corrigido foi recalculado. Todos os "tetos" de viés são limites superiores analíticos
  (fração de métodos com chave inalcançável), não o delta real — que será **menor**, porque nem todo
  método corrompido foi executado;
- o teto de 0,333 pp vale para `cov_method`; não medi a fração corrompida do denominador de
  `cov_directly_reaches_mop`;
- a mediana de `cov_method` "0,75% (n=4)" da rev. 1 não foi reproduzida; pelo corte desta análise são
  cinco APKs acima de 10% de classes afetadas. O filtro exato que produziu n=4 não foi identificado;
- a proveniência do conjunto `G` do portão `keep(X)` — se veio ou não do parser normalizado. O
  mecanismo sugere que não afeta (o `startswith` do gate é insensível à troca `.`→`$` depois do
  prefixo), mas não foi traçado;
- o efeito da chave corrompida sobre o *ranking* dos 131 trials da calibração Optuna;
- ~~**o mecanismo do colapso do Soot.** A hipótese multidex simples está refutada; o que resta exige
  instrumentar uma corrida do GATOR. Registrado como hipótese testável;~~ **[rev. 4] fechado** — a
  corrida foi instrumentada, o mecanismo é o rebaixamento de `AnalysisEntrypoint.java:111-126` e não
  o Soot (§4.3, `docs/20260828_d9_colapso_denominador.md`);
- a causa dos 53 artefatos com `transitions` vazio que não são do gh91 — não é decidível pelos
  artefatos, porque WTG genuinamente vazio e exceção no builder gravam a mesma coisa;
- **a inflação de 1,07–1,12× do LENIENT não foi medida contra o `Scene` de um APK real** — foi
  calculada contra o `android.jar` API 30 mais os pointcuts das specs. O número correto exige
  instrumentar `resolveInScene` e contar com e sem `paramsMatch`. Além disso, `T+` com base ≠ `Object`
  (2 entradas no `jca`, 8 no `jca_android`) foi tratado como casando qualquer coisa, o que
  **subestima** os extras;
- as 180 triplas de violação sem artefato co-locado (28,6% das 629) não puderam ser classificadas —
  são APKs dos 219 fora dos 162, então a fração ambígua real pode diferir das 3/57 medidas;
- se o caminho dexlib2 da violação produz frames fora dos quatro prefixos filtrados por
  `ViolationRecorder.java:99-116`; vale cruzar com
  `docs/20260827_divergencia_after_dexlib2_ajc.md`;
- a reconciliação entre "62 com sufixo `.debug`" (nota de 13/08) e "75 com sufixo" (gh102 e este
  censo). A leitura provável é que 62 conta só a forma `.debug` e 75 conta todas as formas — o censo
  da §3.1 dá 60 `.debug` puros nos 162, o que é compatível mas não idêntico. Importa se o
  dimensionamento de uma correção depender do número.

---

## 15. Verificação, decisões e escopo — rev. 3 a rev. 6 (28-30/08/2026)

Esta seção é o resumo executivo. As seções 1–14 continuam sendo a análise; esta diz **o que sobreviveu
à verificação, o que o pesquisador decidiu, e qual é o escopo da change**. As §§15.1–15.4 são da
rev. 3, atualizadas em linha onde a rev. 4 e a rev. 5 as contradizem; a **§15.5** é o que a rev. 4
fechou; a **§15.6** é o que a rev. 5 corrigiu, e é onde o escopo sai deste documento e entra na
issue #111; a **§15.7** é o que a rev. 6 mediu, escrita já com a change implementada.

### 15.1 O que foi verificado, e o que não sobreviveu

**Reproduzido diretamente sobre o corpus** (`APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`,
162 artefatos) — os três números conferem:

| medição | rev. 2 | rev. 3 (medido) |
|---|---|---|
| artefatos cujo manifesto não é prefixo de classe nenhuma | 75/162 | **75/162** |
| denominador: min / mediana / APKs com ≤30 classes | 1 / 671 / 6 | **1 / 671 / 6** |
| corrupção do normalizador | 465 classes, 7 de 162 APKs | **465 classes, 7 de 162 APKs**, mesma lista e mesmas frações |

**Verificado na fonte, e confirma a rev. 2**: `app.py:146-147` (manifesto verbatim), `app.py:62-68`
(default falso), `RvsecAnalysisClient.java:289-291` (`startsWith` cru), `JsonReportWriter.java:84` +
`RvsecAnalysisClient.java:159` (o artefato grava o manifesto, não a `codePackage`),
`ReachabilityEnricher.topLevelMetadata()` sem chamador de produção,
`coverage.py:660,672` (dois descartes sem contador), `diagnose()` só em teste,
`ParserDiagnostics.to_dict()` só em teste, ausência de qualquer regra de neutralização de sufixo no
`rv-android`.

**Não sobreviveu — afirmações sobre comportamento, todas corrigidas em linha:**

| # | o que a rev. 2 dizia | veredito |
|---|---|---|
| 1 | contaminação do logcat entre tasks é real ("a limpeza de buffer mitiga, não elimina") | **falso** — quatro mecanismos independentes impedem; D6 retirado |
| 2 | `--skip-static` faz o experimento rodar sobre APKs não instrumentados | **falso** — roda sobre os instrumentados; o fallback é cosmético e o warning mente. O defeito real é a INV-EXP-16 não valer |
| 3 | a chave tem **um** consumidor funcional; o ajc não a usa | **falso** — o `ajc_instrumentation.py:854-900` a usa como guarda anti-quarentena, hoje inerte nos apps sufixados |
| 4 | a gh69 está em "1 de 47 checkboxes, zero código" | **falso** — 22/47 na árvore de trabalho, fases 1–3 implementadas; o D9a **já está escrito** |
| 5 | D3 é "uma chamada removida" | **incompleto** — são duas (`:371` e `:455`), acopladas por INV-ANA-60 |
| 6 | `setup_file_logging` "nunca é chamado em produção" | **impreciso** — tem chamador, mas o guard é autorreferencial e o chamador também não tem chamador |
| 7 | as env vars de negação "fazem o oposto" | **verdadeiro**, mas já tem dono: `gh-tbd-env-vars-architecture` |
| 8 | a chave de escopo pede um canal curado por APK | **sobredimensionado** — ver 15.2 |

**Sobre o `_is_in_namespace`**: uma nota da discussão que não deve virar folclore. O
`PackageDetector._is_in_namespace` (`package_detector.py:341`) faz casamento por namespace de
verdade, com comentário explicando que é para `com.foobar` não casar `com.foo`. Mas ele vive **dentro
do `PackageDetector`**, que só roda com `package_detector=True` — o caminho desligado por default e
que será aposentado. No caminho default **não existe lógica de fronteira de ponto em lugar nenhum do
lado Python**. Não é verdade, portanto, que "os dois lados do pipeline discordam": o que existe é uma
implementação correta dentro de um componente que sai de cena, e um GATOR que nunca a teve.

### 15.2 Decisões do pesquisador (28/08/2026)

**D-A — A chave de escopo: manifesto verbatim continua sendo a regra; uma flag global de run remove o
sufixo de build-type.**
O `rv-android` é genérico. O sufixo não é regra do mundo: é consequência de o `rvsec-dataset` rodar
`assembleDebug`. Portanto **não** se cria canal por-APK, **não** se cria mapa curado, e a política
segue escalar por run — igual ao `package_detector`, coerente com INV-EXP-34. A regra que a flag
aplica é a **denylist fixa**, a mesma já normativa no `mneut_scope.py`:

```
BUILD_TYPE_DENYLIST = {debug, dev, beta, staging, qa, nightly, alpha, snapshot, current, head, indev}
MIN_SEGMENTS = 2
```
aplicada **repetidamente** (é o que trata `.qa.debug` e `.debug.HEAD`) e em **minúsculas** (é o que
trata `.BETA`), nunca abaixo de 2 segmentos.

A denylist **não é total** — `com.learntube.app` usa `applicationIdSuffix = ".debug.$branch"`, o nome
do branch git, e o espaço é aberto por construção. É por isso que o **D1 continua sendo
pré-requisito**: a flag resolve o caso comum, e o portão de não-vacuidade recusa o silêncio no caso
que ela não cobre. Uma lista sem portão só troca um silêncio por outro (§12).

**D-B — A flag NÃO vale para o instrumentador ajc.**
O ajc está fora da mesa de reparo. Aplicar a chave neutralizada aos 8 sítios `App(` ativaria a guarda
anti-quarentena de `ajc_instrumentation.py:854-885`, hoje inerte exatamente nos apps sufixados — o
que é mudança no caminho de instrumentação, não no de análise. A divergência entra **registrada**,
não corrigida. Nota de projeto: isso significa que o pipeline passa a ter, deliberadamente, duas
respostas para `code_package` conforme o consumidor — e o comentário em `ajc_instrumentation.py:858-866`
já antecipa essa tensão. A escolha é consciente e o registro é o que a mantém honesta.

**D-C — O `isAppClass` do GATOR NÃO ganha fronteira de ponto agora; a decisão fica para depois do D9.**
Muda medição e não bloqueia nada. Com a chave sendo um pacote completo, a colisão irmã exige que o
pacote de um app seja prefixo estrito do de outro — raro, mas real: o acervo tem
`rocks.poopjournal.fucksgiven` casando `…fucksgivenwatch.*`, e `com.jerboa`, cuja chave antiga era um
**nome de classe** (`com.jerboa.MainActivity`). Reparo de poucas linhas em Java, reavaliado quando o
D9 fechar.

**D-D — Retirados do escopo, por decisão:** D5 (procedência em colunas e checksum), D6 (filtro de
logcat), Q8 (filtrar violação contra a estática).

### 15.3 Escopo da change, na ordem decidida

Uma change única. Track sugerida: **FF SDD** — o D2 carrega decisão de design real (a flag e seu
alcance), e os requisitos já estão fechados por este documento, o que dispensa a cerimônia das seis
fases do Full SDD.

| ordem | item | o que é | muda medição? |
|---|---|---|---|
| **1º** | **D9** | **[rev. 4] investigação feita; virou reparo.** A guarda de `AnalysisEntrypoint.java:119` passa a consultar `Configs.getClientParamCode("codePackage=")`, com fallback ao manifesto. Um sítio, poucas linhas, no `rvsec-gator`. Denominadores de classe: 1 → 771, 2 → 1.971, 6 → 3.589, 21 → 550. **[rev. 5] o efeito é conjunto com o D2** — §15.6 | **sim, com o D2** |
| 2º | **D1** | contadores `unmatched_*` separados em fora-de-escopo × dentro-do-escopo, + portão de não-vacuidade do denominador | não |
| 3º | **D2** | flag global de sufixo de build-type (denylist) + registro da chave efetiva; não vale para o ajc | **sim** |
| 4º | **D3** | remover as duas chamadas do normalizador (`:371` e `:455`) | **sim** |
| 5º | **D4** | serializar `ParserDiagnostics` e `TaskResult.write_errors`; criar a chamada de `setup_file_logging` num entry point | não |
| 6º | **D10'** | `--skip-instrument` que mata a estática; INV-EXP-16 que não vale; reuso silencioso de monitores | não |
| 7º | **D9b** | corrigir `rv-static-analysis/CLAUDE.md:27-28` e o cabeçalho de `pre_processor.py:83-90` | não |

**Por que o D9 primeiro** — e é a inversão mais importante da rev. 3: enquanto o mecanismo do colapso
não estiver determinado, **não se consegue separar "a chave estava errada" (D2) de "o denominador
colapsou" (D9)**. São causas independentes com o mesmo sintoma, e o corpus tem as duas. Reparar o D2
antes mede uma melhora que não se sabe atribuir. É também o único item que hoje **infla** um número.

**[rev. 4] A investigação foi feita e a ordem se mantém, agora por razão mais forte.** O critério que
separa as duas causas deixou de ser intuição e virou teste: um APK colapsa por D9 se, e somente se,
nenhuma classe compilada começa com o pacote do **manifesto** **e** o pacote de código casa um padrão
de `libPackages.txt`. Sobre os 162, isso isola os quatro sem ambiguidade. **Três consequências para o
resto da tabela:**

- o D9 **muda medição** (a coluna dizia "—" e estava errada, porque a rev. 3 o via como investigação);
- o **D1** ganha um segundo modo de falha para cobrir: o portão precisa recusar o denominador
  **degenerado**, não só o vazio — 1 classe de 771 não é vazio, e um portão de não-vacuidade não teria
  pego nenhum dos quatro;
- o **D2** fica com o escopo intacto e **não** deve absorver o D9: o `AnalysisEntrypoint` recebe a
  chave de código já resolvida, em vez de repetir a regra de neutralização.

**Fora desta change, com destino nomeado:**

| item | onde fecha |
|---|---|
| D9a (`new`→`<init>` e log-and-skip) | **gh69** — já implementado na árvore de trabalho; falta verificar e commitar |
| R1–R6, D-1…D-9 das specs | **gh109**, grupo G8 (na árvore de trabalho, não commitado) |
| R1 raiz (`TypeResolver`) e `after()` opção (a) | change própria do módulo **dexlib2** |
| env vars de negação | **gh-tbd-env-vars-architecture** |
| D5, D6, D7, D8, Q8 | retirados |
| checksum que nunca diverge (`platform.py:171` antes de `:178`) | anotado; sem dono |

**[rev. 5] E a coluna que faltava: o que não está em lugar nenhum.** A §9 lista 19 componentes com
achados. A change leva 7, quatro destinos levam o resto do que foi roteado, e três itens foram
retirados por decisão. Sobra isto, que não está na change, não foi roteado e não foi retirado — e
que a tabela acima fazia parecer inexistente:

| achado | onde está na análise | por que ficou de fora |
|---|---|---|
| portão insatisfazível do `CoverageValidator` + regex que trunca `<init>` | §9, D8 | D8 diz "fora desta change"; nenhum destino nomeado. Só roda por invocação manual (`ValidationCli.java:451-458`) |
| fallback do split de frame no `ErrorDescription` (frame inteiro nos três campos) | §9, D7 | D7 some da tabela final sem decisão explícita |
| denominadores não publicados nos CSVs; dois esquemas de `performance.csv` | §9, Q7 | Q7 sem resposta. **[parcialmente resolvido]** — a gh111 leva os denominadores e os contadores, não a procedência |
| checksum de resume que nunca diverge | §11, D5 (resíduo) | "anotado; sem dono" |
| `if static_data:` sempre verdadeiro; retorno de `copy_static_analysis_files` descartado | §9 | nunca virou item D |
| pós-condição do `static_analysis.py` só de existência de arquivo | §9 | nunca virou item D |
| ramo `:::` morto no `logcat_parser` | §9 | nunca virou item D |
| poda do `libPackages.txt`; os três `-exclude` inertes de `Main.java:225-227` | §4.3, §15.4 | dívida declarada; podar muda medição para todos os apps |
| granularidade (Q3d): `LENIENT` hard-coded, `STRICT` inalcançável pelo caminho MOP, alvo semeado por nome × cobertura casada por assinatura | §9, Q3d | pergunta aberta, sem decisão |

Nove achados. A gh111 encosta em um (os denominadores). Os outros oito continuam sem casa, e o
registro existe para que não sumam na próxima campanha.

### 15.4 O que continua em aberto depois de tudo isto

*[rev. 4] Eram três buracos; o primeiro foi fechado pela investigação do D9. Sobram dois, e nenhum é
resolvido pela change:*

1. ~~**O mecanismo do colapso do Soot** é hipótese até o D9 fechar.~~ **[rev. 4] FECHADO.** Não é o
   Soot: é a guarda de `AnalysisEntrypoint.java:119`, que compara com o pacote do manifesto, mais o
   `libPackages.txt`, que rebaixa o resto. Determinado e reproduzido ao vivo — §4.3 e
   `docs/20260828_d9_colapso_denominador.md`. **No lugar dele entra uma dívida menor**: a poda de
   `libPackages.txt`, que contém namespaces de autores de app (`com.nononsenseapps.*`,
   `info.metadude.*`, `me.zhanghai.*`) e padrões largos como `c.*` e `domain.*`. Com o D9 reparado
   ~~ela deixa de causar dano no denominador, mas continua governando o que o GATOR trata como
   biblioteca em análise legítima.~~ **[rev. 5] a razão está corrigida, e é mais estreita.** Com o
   D9 reparado a lista **não alcança mais o denominador**: tudo sob o prefixo do app sai do laço na
   guarda de `:119` e nunca chega ao `isLibraryClass`, e o que ela ainda rebaixa está fora do
   prefixo, que o `isAppClass` do cliente já excluía. O que ela continua governando é
   `hier.appClasses` — logo o `FlowgraphRebuilder`, o `WTGHelper` e a descoberta de entry points, e
   portanto os predicados `reachable` e `reachesTarget`. A dívida deixou de ser de denominador e
   virou de alcance. Sem dono, e **fora** desta change: podar muda medição para todos os apps.
   Procedência, conteúdo e o desvio de finalidade em §4.3.
2. **A fronteira de ponto do `isAppClass`** (D-C) fica adiada, e muda medição quando for decidida.
   **[rev. 4]** O D9 não a bloqueia nem a torna urgente: o rebaixamento é anterior ao `isAppClass` e
   independente dele.
3. **A assimetria da violação** (§4.2) permanece por desenho: 62,3% dos sítios de violação são de
   classes fora do denominador, e isso não é defeito — é o que permite medir um APK sem análise
   estática e contar violações de bibliotecas que o app usa.

### 15.5 O que a rev. 4 fechou — a investigação do D9

Relatório completo: `docs/20260828_d9_colapso_denominador.md`. Sonda:
`docs/20260828_d9_colapso_denominador/D9Probe.java`. Mecanismo em §4.3, medições em §13.

**O mecanismo.** O Soot carrega as 36.800 classes dos 18 DEX do `petals` e marca **todas** como
aplicação. Quem colapsa o denominador é o GATOR, em `AnalysisEntrypoint.java:111-126`: a guarda de
`:119` compara o nome da classe com o pacote do **manifesto** (`br.com.colman.petals.debug`, lido
verbatim em `:87-94`), nenhuma classe do app começa com esse prefixo, e o padrão `br.com.*` do
`libPackages.txt` rebaixa 33.089 classes a biblioteca. Sobra **1** classe sob o prefixo do app — a
`MainActivity`, devolvida pelo ramo de resgate de `:112`, que só conhece `<activity>`.

**A prova.** A sonda reproduz `#AppClasses = 3711` — byte a byte o log da campanha — em 13 segundos,
e os quatro denominadores 1 / 2 / 6 / 21. Com a guarda no `codePackage`: 771 / 1.971 / 3.589 / 550.
O controle `app.pachli` (mesmo sufixo de build-type, guarda igualmente morta, mas fora da lista) é
invariante. Sobre os 162, a conjunção das duas condições seleciona **exatamente os quatro**.

**O que não sobreviveu — afirmações da rev. 2/3 sobre o D9:**

| # | o que a rev. 2/3 dizia | veredito |
|---|---|---|
| 9 | "o colapso não é a chave, é o **carregamento**" (título da §4.3) | **falso** — é a **classificação**: o carregamento traz tudo; o GATOR rebaixa depois |
| 10 | `set_process_multiple_dex` nunca chamado, "o Soot roda no default para multidex" | **vazio** — a opção **não existe** no Soot 4.7.1; `DexFileProvider.acceptFile` é `{ return true; }` |
| 11 | os 4 artefatos "são a manifestação em disco do mesmo defeito" dos 33 `denominator_collapse` do funil | **falso** — o funil avalia a chave contra as classes compiladas, offline; o artefato do GATOR não entra na conta. São defeitos independentes |
| 12 | "parte dos 55 volta com D2 **e** D9" (§6.2) | **impreciso** — o crédito é todo do D2; o D9 não devolve nenhum dos 55 |
| 13 | D9 "não muda medição" (coluna da tabela da §15.3) | **falso** — muda, em 4 dos 162, e na direção que **derruba** `cov_class` |

**O que a rev. 4 acrescenta como achado novo:**

- **os três `-exclude` de `Main.java:225-227` são inertes** (`Scene.isExcluded` exige `.*`).
  Configuração morta; **registrada, não reparada** — mexer nela muda medição. Mesma disciplina da
  decisão D-B;
- **`libPackages.txt` contém namespaces de autores de app** (`com.nononsenseapps.*`, `info.metadude.*`,
  `me.zhanghai.*`, `uk.org.*`) e padrões largos (`c.*`, `a.a.*`, `domain.*`, `flow.*`). Com o D9
  reparado a lista deixa de danificar o denominador, mas continua governando o que é biblioteca.
  Dívida sem dono, **fora** desta change (§15.4, item 1);
- **exposição da campanha nova**: 27 de 219 apps (12,3%) têm o pacote sob um padrão da lista.
  Enquanto a guarda usar o manifesto, qualquer um deles colapsa assim que tiver sufixo de build-type.
  O corpus atual só mostra 4 porque as duas condições precisam coincidir.

**O que isto não muda.** A ordem do escopo (§15.3) continua **D9 → D1 → D2 → D3 → D4 → D10' → D9b**,
e as decisões D-A, D-B e D-D seguem valendo. A **D-C** (fronteira de ponto do `isAppClass`) pode ser
reavaliada agora, como ela mesma previa: o D9 não a bloqueia — o rebaixamento é anterior ao
`isAppClass` e independente dele.

### 15.6 O que a rev. 5 corrigiu — e a issue #111 que ela fechou

A rev. 5 foi escrita ao abrir a change. Ler o código que a change ia tocar devolveu duas contradições
e completou um item. Registro do que sai e do que entra.

**O que não sobreviveu — afirmações da rev. 3/4:**

| # | o que a rev. 3/4 dizia | veredito |
|---|---|---|
| 14 | o D9 "independe de D2 e de D3" (§11, §15.5) | **falso como efeito.** Independem como sítios de código; na via de produção são **conjuntivos**. `App.code_package` devolve o manifesto por default (`app.py:146-147`), então a guarda reparada leria o valor de hoje. Os números da sonda foram medidos com a chave já neutralizada |
| 15 | o D9 "muda medição em 4 dos 162" isoladamente (§15.5, item 13) | **impreciso.** Muda nos quatro **quando o D2 estiver em pé**. Sozinho, na via de produção, é inerte — e não é verificável pelo pipeline, só pela sonda |
| 16 | a atribuição do `$` ao AspectJ, herdada de `docs/NOVO/06_normalizacao_inner_classes.md` e usada como contexto histórico do D3 | **falso.** `Coverage.aj:64` usa `Class.getName()`, que nunca insere `$` em fronteira de pacote. O `$` era do normalizador |
| 17 | o D3 é "remover as duas chamadas" (§11, §15.3) | **incompleto.** É remover a classe: `SignatureNormalizer` tem um consumidor em todo `modules/*/src/`, e o P3 manda deletar o arquivo, o teste e a INV-ANA-02 |
| 18 | a dívida do `libPackages.txt` "continua governando o que o GATOR trata como biblioteca em análise legítima" (§15.4) | **impreciso, e mais estreito.** Depois do D9 ela não alcança o denominador de forma nenhuma. O que ela governa é `hier.appClasses`, logo os predicados `reachable`/`reachesTarget` |

**O que a rev. 5 acrescenta como achado novo:**

- **a procedência e o desvio de finalidade do `libPackages.txt`** (§4.3). A lista é upstream do
  GATOR, entrou no import inicial do fork em 25/09/2024 e nunca foi editada. Ela existe para
  **escopar uma análise de GUI**, papel em que falso positivo custa precisão; o `RvsecAnalysisClient`
  a reaproveita como **denominador de métrica publicada**, papel em que falso positivo é erro de
  medição. Ninguém reautorizou a lista para o papel novo. É a mesma classe de defeito que o §8 nomeia,
  numa forma que o documento ainda não tinha registrado: não uma transformação textual silenciosa,
  mas uma **classificação herdada usada fora da finalidade para a qual foi curada**;
- **o normalizador nunca poderia ter reparado, nem por acidente** (§5.1): ele toca o `class_name` e
  não a `signature`, e o cruzamento testa os dois;
- **os nove achados sem casa** (§15.3): não estão na change, não foram roteados, não foram retirados.

**O que isso muda na verificação da change** — e é a consequência prática da correção 14:

- o **D9 não tem testemunha no pipeline**. A aceitação dele é a sonda `D9Probe.java` rodada contra o
  jar reconstruído: 771 / 1.971 / 3.589 / 550 nos quatro, e invariância no `app.pachli`. A tarefa 1.4
  e a 1.5 da `tasks.md` fazem disso um checkpoint explícito;
- a **ordem D9 → D1 → D2 → D3 continua**, e a razão fica mais simples de enunciar: o D9 é
  pré-requisito porque **habilita** o D2, não porque separa uma atribuição. A separação de
  atribuição continua valendo entre D2 e D3, que são independentes entre si e cada um com sua
  testemunha (os 75 artefatos que parseiam zero, e o `com.hwloc.lstopo_80283`);
- a **D-C** (fronteira de ponto do `isAppClass`) não muda de estado.

**Onde o escopo foi parar.** A issue **#111** e a change `openspec/changes/gh111-cadeia-medicao/`
carregam os sete itens desta seção, com as cinco correções da rev. 5 já incorporadas. O `proposal.md`
traz o mapa da cadeia elo a elo — a forma do identificador em cada ponto, onde a assinatura é
completa e onde é só classe+nome, e onde o descritor DEX vira FQN — que este documento tinha
espalhado por §3, §4 e §5. Delta specs em `analysis`, `core`, `experiment` e `platform`;
INV-ANA-65…69, INV-CORE-58…62, INV-EXP-35…38, INV-PLT-33/34; INV-ANA-02 retirada.

---

### 15.7 O que a rev. 6 fechou — a change implementada, e o que a medição devolveu

A rev. 6 (30/08) é a primeira revisão escrita **de dentro da implementação**. As anteriores
analisavam; esta registra o que a execução da `gh111` mediu, e o que duas verificações
independentes estabeleceram antes dela: a adjudicação das cinco revisões externas
(`docs/20260829_adjudicacao_revisoes_gh111.md`) e a verificação de consistência das dez dimensões
(`docs/20260830_verificacao_consistencia_gh111.md`). As correções da rev. 6 estão marcadas
**[rev. 6]**.

**O que não sobreviveu — afirmações da rev. 5:**

| # | o que a rev. 5 dizia | veredito |
|---|---|---|
| 19 | a correção C1: o D9 "não tem testemunha no pipeline" e "é inerte na via de produção" (§15.6) | **estreito demais.** O correto é *"não observável **sob a política padrão**, que é como toda corrida registrada executou"*. O `--package-detector` é política viva (`rv-experiment/__main__.py:282-295,584`, normativa pela INV-EXP-34) e produz uma chave diferente do manifesto sem D2 nenhum. A ordenação D9 → D2 sobrevive intacta; o que muda é que o D9 passa a ter aceitação de pipeline |
| 20 | a aceitação do D9 é a sonda `D9Probe.java` (§15.6) | **falso como aceitação.** A sonda não importa nada de `presto.android`, reimplementa o predicado de rebaixamento e imprime as duas guardas **sem mutar a Scene** — editar `AnalysisEntrypoint:119` muda a saída dela por exatamente zero. Ela é **predição**, e continua valendo como tal (~13 s por APK). A aceitação é uma corrida real do `rv-static-analysis` contra o jar reconstruído |
| 21 | os denominadores do D9 são **771 / 1.971 / 3.589 / 550** (§15.6) | **são os números crus, não os entregues.** O `RvsecAnalysisClient.isAppClass` remove as classes geradas antes de escrever o artefato; os denominadores entregues são **762 / 1.952 / 3.578 / 535**. E os 550 do `screenshottile` eram, além de crus, contaminados — ver a linha 22 |
| 22 | o `app.pachli_50` é o controle de invariância (§15.6, e a tarefa 1.8 original) | **um controle que não pode falhar.** Nenhum padrão do `libPackages.txt` casa `app.pachli.*` (as únicas entradas iniciadas em `app` são `apparat.*`), então o laço de rebaixamento nunca roda e o controle não tem como acusar um alargamento da guarda. O controle passa a ser um dos seis APKs de guarda viva, e a corrida usou `me.zhanghai.android.untracker_9` |
| 23 | a dívida do `libPackages.txt` "não alcança o denominador de forma nenhuma" (§15.6, linha 18) | **verdadeiro e insuficiente.** Depois do D9 ela deixa de alcançar o denominador **de classes**; continua governando `hier.appClasses` e portanto os predicados `reachable` / `reachesTarget` / `directlyReachesTarget`, que são os denominadores de **três das seis** colunas de cobertura publicadas. Deixa de ser risco para um denominador e continua sendo para três |

**Achados novos da rev. 6 — os três primeiros são de medição, os três últimos de entrega:**

**O vazamento das classes de recurso (D9c, INV-ANA-71).** O `isAppClass` ancorava o teste das classes
geradas (`R`, `R$*`, `BuildConfig`, `Manifest$*`) na **raiz** da chave de escopo. Duas consequências
medidas sobre os 162 artefatos: 505 classes geradas estão hoje **dentro** do denominador — 117 só no
`app.pachli_50`, uma `R` por módulo Gradle —, carregando 547 métodos dos quais **zero** são não
triviais; e, no caso da chave-ancestral, o vazamento é total. O detector elege `com.github.cvzi` para
o `screenshottile`, e o sufixo de `com.github.cvzi.screenshottile.R` é `.screenshottile.R`, que não
casa padrão nenhum ancorado na raiz: sob a regra antiga a filtragem removia **zero** classes e
entregava 550. Era esse 550 que a tarefa 1.8 ia fixar como número de aceitação do D9 — um
denominador com quinze classes de recurso dentro. O teste passou a ser sobre o **último segmento** do
nome da classe, e a aceitação passou a ser 535. Uma change cujo assunto é o denominador não pode
ratificar um contaminante conhecido dentro dele.

**As seções `## Invariants` dos deltas nunca chegam à spec base.** Verificado executando o próprio
motor de merge do `openspec` (`buildUpdatedSpec`): o `sync`/`archive` reconstrói apenas a seção
`## Requirements`, e os invariantes do delta são descartados em silêncio. `openspec validate --strict`
não vê a diferença. Arquivar a `gh111` como estava entregaria os requisitos e jogaria fora os 22
invariantes novos, as reafirmações e as emendas — inclusive a reafirmação da INV-PLT-19, que é a
única coisa que levanta o congelamento de colunas herdado da `gh104`. A `gh104` mediu o mesmo e
escreveu uma tarefa de sincronização à mão (a 10.8 dela); a `gh111` ganhou a equivalente, a 8.17.

**Quatro requisitos da base contradizem a change e não eram emendados.** Um deles manda escrever
`0.00` exatamente no caso em que a INV-PLT-35 proíbe; outro manda **excluir da execução** os APKs sem
análise estática, que é o oposto da decisão D-10; e o bloco `Domain Models (FR33)` do `core` diz, em
três passagens, que remover sufixo de build-type "pertence a quem cura o corpus, não a este modelo" —
que é literalmente o que o D2 faz. Foram emendados como cláusulas, não substituídos como blocos.

**A colisão de arquivamento com a `gh104`.** O bloco `Result Generation (FR14)` desta change foi
copiado da versão da `gh104`, não da base, e a reafirmação da INV-PLT-19 substitui o texto da `gh104`
pelo nome. Se a `gh111` arquivar primeiro, a `gh104` reaparece por cima. A ordem é
**`gh104` → `gh111`**, e a tarefa 8.16 é a porta que a verifica antes de qualquer escrita em
`openspec/specs/`. **Em 30/08 essa porta está fechada**: `grep -c 'code, event'` na
`openspec/specs/platform/spec.md` devolve `0`, a `gh104` não está arquivada e a INV-PLT-19 da base
ainda carrega o `errors.csv` de onze colunas. A `gh111` está implementada e **não pode sincronizar**
até que a `gh104` feche as três tarefas que lhe faltam (10.4, 10.5, 10.8 — validação em dispositivo
e o sync à mão dela).

**O que a implementação mediu.** Todos os números abaixo são de corridas desta implementação, não
predições:

- **aceitação do D9, ponta a ponta** (`com.github.cvzi.screenshottile_148`, `--package-detector`,
  chave eleita `com.github.cvzi`, manifesto `com.github.cvzi.screenshottile.debug`): `len(reachability)`
  **21 → 535** entre o jar pré-mudança (`lib/gator-pre/`, sha `4708d63c…` / `dab75ca7…`) e o
  reconstruído (`6ce00738…` / `df18057e…`). O artefato pós registra `codePackage=com.github.cvzi`,
  `codePackageSource=detector`, `class_defs_under_key=539` e **zero** classes `R`/`BuildConfig`/`Manifest`
  — a razão do portão é 535/539 = 0,993, muito acima do limiar 0,15;
- **controle de invariância** (`me.zhanghai.android.untracker_9`, chave casada por padrão do
  `libPackages.txt` e sem sufixo de build-type, logo com o laço de rebaixamento realmente rodando):
  pré e pós **idênticos em 330** classes, `class_defs_under_key=332`. Se o reparo tivesse *alargado*
  a guarda em vez de redirecioná-la, é esse número que teria se mexido;
- **D3 sobre o corpus inteiro**: os 162 artefatos parseiam **215.430** classes, **0** deles parseia
  para zero, e o parser inventa **0** nomes — nenhum nome no conjunto parseado está ausente do
  arquivo. Sobre os sete APKs afetados, 465 → **0** nomes inventados, com a contagem de classes e a
  de janelas **invariantes** (6/6, 3/3, 180/180, 11/11, 7/7, 15/15, 6/6, e os mesmos subconjuntos
  ACTIVITY) — o resultado nulo que confirma que os dois sítios de chamada saíram juntos;
- **testes**: 1.071 (`rv-android-core`), 348+1s (`rv-platform`), 271 (`rv-experiment`), 165
  (`rv-static-analysis`), 301 (`rv-coverage`), 218 de paridade sob `RV_GATOR_REQUIRED=1` (que é o
  que faz os testes dependentes do jar rodarem em vez de pularem), e do lado do reator os três ITs que o
  `client/pom.xml:18` mantém desligados — `BaselineComparisonIT` (11), `GenericSubtypeMatchingIT` (8),
  `RvsecAnalysisClientIT` (14) — verdes com `-DskipITs=false`.

**O portão que recusava sem impedir nada.** Achado da revisão de código desta implementação, e vale
registrar porque é a forma mais fina do padrão que o §8 nomeia. A INV-ANA-69 manda o portão *falhar
alto*, e o código o fazia: uma recusa devolvia um `StaticAnalysisResult` com `success=False`. Só que
nada a jusante lê esse objeto — o `_report_missing_static_analysis` monta a lista dele com
`os.path.exists(<apk>.apk.json)` e o `_resolve_static_data` localiza o arquivo pelo nome. O artefato
recusado continuava no disco, era reparseado e o denominador colapsado saía publicado como
percentual com `measured=true`, que é exatamente o que o cenário da própria INV-ANA-69 proíbe em
tantas palavras. O portão era, na prática, uma linha de log — a mesma forma de defeito que a D-5
existe para encerrar, uma camada adiante. A recusa passou a **renomear** o artefato para
`<apk>.apk.json.refused`: os consumidores o veem como ausente, a linha toma o caminho honesto que já
existia (células vazias, `measured=false`), e o arquivo fica para diagnóstico, porque a recusa é um
alarme de jar velho ou de chave não resolvida e é o próprio artefato que nomeia a causa.

**Um desvio de método a registrar.** A reconstrução do reator (tarefa 1.5) rodou com `-DskipTests`,
contra o que a decisão D-13 prescreve, porque o `rvsec-mop` falha sobre edições `jca_android/*.mop`
não commitadas de outra sessão — uma dependência que não é da `gh111`. As suítes que a D-13 nomeia
foram então rodadas explicitamente sobre os módulos do gator (`mvn test -pl …/sootandroid,…/client`:
214 + 22 testes, 0 falhas), e a passagem com ITs desta seção as cobre de novo. O desvio é de
comando, não de cobertura.
