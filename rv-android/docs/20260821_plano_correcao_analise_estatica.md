# Plano de correção — acoplamento experimento ↔ análise estática

**Data**: 2026-08-21 · **Sessão**: `bug-analise-estatica`
**Revisão 2** (mesmo dia): a primeira versão listava sete itens principais e seis decisões
pendentes. Três itens caíram na verificação contra o código e as specs, e cinco das seis decisões
deixaram de existir. Versão anterior em `backup/20260821_plano_correcao_analise_estatica.v1.md`.
**Revisão 3** (mesmo dia): auditoria de consistência antes de abrir a issue. Nenhum defeito mudou de
veredito — as duas reproduções (§7) foram executadas e conferem. Corrigiram-se o script do J1, que
não rodava; o caminho e as linhas do consumidor; a contradição de trilha entre a §5 e a §6 (a edição
de spec principal saiu do escopo); a contagem de arquivos; o precedente de trilha da §9; e o P3
ganhou o impacto que faltava declarar.
**Revisão 4** (mesmo dia): auditoria de consistência independente, com as quatro reproduções da §7
executadas. Nenhum defeito mudou de veredito. Corrigiram-se: a contagem de edições locais no
`gator` (eram três, não duas); a linha da spec que sustenta a refutação do D3; a linha do
`CONTEXTO.md` que declara o preço da gh104; o bloco de contagem da §7; a pendência dos logs das
sondas, que não existem mais; um quarto sítio de `--sdkpath`; e um defeito documental novo em
`static-analysis.md:85`. Versão anterior em `backup/20260821_plano_correcao_analise_estatica.v3.md`.
**Revisão 5** (2026-08-21): **triagem de necessidade**, decidida com o pesquisador. As 38 citações
foram conferidas contra a árvore e as quatro reproduções reexecutadas — todas conferem. O escopo
caiu de nove itens para seis: **a faxina inteira do `gator` saiu**, a segunda camada do reparo do
SDK saiu, e a §8 encolheu de nove linhas para três. Corrigiram-se três erros de consistência: a
alegação de "código morto" no ramo de timeout do `gator` (é falsa — `rc=206` é esse ramo), a
contradição entre a §5 e a §8 (que mandava editar uma spec principal), e o ponteiro da pós-condição
de `static_analysis.py`. Mediu-se o que faltava: o conjunto `generic` tem **296 assinaturas / 284
pares / 95 owners**, com interseção **zero** com o `jca`. Versão anterior em
`backup/20260821_plano_correcao_analise_estatica.v4.md`.
**Revisão 6** (mesmo dia): fechamento das lacunas que impediam o plano de servir de entrada para a
change. Acrescentaram-se a §4.1 (complexidade, risco e critério de aceitação por item) e a §4.2, que
corrige a afirmação mais errada da revisão anterior: **não falta teste do sentinela** — existem três
camadas e nenhuma alcança o J1, e o módulo que as hospeda tem `skipTests=true` no pom. Declarou-se
também o efeito colateral do reparo do `mop_dir` (um run `generic` passa de 120 para 296
assinaturas).
**Natureza**: Fase 0 do `docs/WORKFLOW.md` — material de referência, não artefato OpenSpec
**Origem**: `docs/20260821_relatorio_analise_estatica_defeitos.md`
**Supersede**: `docs/20260821_verificacao_relatorio_analise_estatica.md`
**Status**: nada implementado, nenhuma issue aberta, nenhuma change criada. A gh105 não foi tocada.

---

## 0. O que sobrou, em uma frase

Dos treze defeitos que a revisão 1 alegava, **quatro** têm dano demonstrável, e só **um** tem prova
de dano em artefato real. A revisão 5 passou a faxina pelo mesmo crivo que matou os outros nove e
ela não sobreviveu: dos cinco itens de faxina, **quatro saíram** e um entrou. O que resta é **uma
única change de trilha Quick Path** (§5) com seis itens — quatro reparos, um parâmetro morto e três
correções documentais de uma linha cada.

Critério de admissão, mantido da revisão 1 e endurecido na revisão 5: nada entra sem (a) citação
`arquivo:linha` conferida, (b) resposta à pergunta **"existe invariante, spec ou guarda que já
cobre isto?"**, e (c) **um consumidor que leia o que o reparo conserta**. Foi a segunda pergunta que
matou quinze das vinte e quatro alegações; foi a terceira que matou a faxina.

---

## 1. O que vale reparar

### J1 — o sentinela `complete` mente (único item com prova de dano)

| Onde | Especificado? |
|---|---|
| `JsonReportWriter.java:111` + `RvsecAnalysisClient.java:165-170` | **viola INV-ANA-31** |

O `"complete": true` é emitido ao fim de **toda** chamada bem-sucedida de `write()`, inclusive a
escrita pré-WTG. Um run que estourou o timeout durante o WTG deixa em disco um artefato marcado
como completo.

> `openspec/specs/analysis/spec.md:363`, INV-ANA-31 — *"The JSON output of a successful
> (non-truncated) GATOR run MUST end with the literal field `"complete": true`...
> **Truncated outputs MUST NOT contain this field.**"*

**Prova em artefato.** Cinco APKs do `SA_RERUN_gh91_wtg` com `timed_out: true` e `returncode: 206`
(7200 s) no `_progress/`:

| APK | `complete` | `reachability` | `transitions` |
|---|---|---|---|
| `app.pachli_50` | **true** | 6453 | 0 |
| `ch.rmy.android.http_shortcuts` | **true** | 7016 | 0 |
| `it.niedermann.owncloud.notes` | **true** | 1318 | 0 |
| `org.glpi.inventory.agent` | **true** | 179 | 0 |
| `com.github.livingwithhippos.unchained` | **true** | 2 | 0 |

**Há consumidor real e o portão é atravessado**: `aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py:249-253`
levanta `DerivationError` quando o sentinela falta — existe exatamente para rejeitar esses cinco, e
eles passam. O `scripts/gh91_campaign.py:126-147` já compensa à mão (exige sentinela **e**
`timed_out == False` do `_progress`); o pipeline `rv-platform` não compensa. Como a gh104 usa o
APE-RV, este é o consumidor que a campanha em preparação atravessa.

O comentário de `RvsecAnalysisClient.java:157-163` afirma o oposto do que o código faz —
*"the pre-WTG write does NOT emit the sentinel"*.

**Delimitação honesta**: o denominador de cobertura (`reachability`) está **íntegro** nos cinco — é
escrito antes do WTG. Perde-se `transitions`/`windows`. Não há inflação de cobertura.

**Reparo**: emitir o sentinela só na escrita pós-WTG (parâmetro `emitSentinel` no `write()`), e
corrigir o comentário.

### D2 — o denominador vem de um conjunto de specs, o numerador de outro

| Onde | Especificado? |
|---|---|
| `rv-experiment/config.py:949-958` + `rv-static-analysis/config.py:199-208` | **viola** `experiment/spec.md:67` (decisão 7) |

Duas configurações nascem do mesmo `specification_set` por caminhos independentes:

| | Quem constrói | Resultado |
|---|---|---|
| Monitores tecidos no APK (o que acusa violação) | `get_monitor_generation_config()`, `config.py:695-719` | despacha **certo** os quatro valores |
| Alvos de alcançabilidade (o denominador da cobertura) | `get_static_analysis_config()`, `config.py:949-958` | **não passa `mop_dir`** → o default de `rv-static-analysis/config.py:199-208` fixa o literal `jca` |

A string `mop_dir` não aparece **em lugar nenhum** de `modules/rv-experiment/src/` — não é um valor
errado sendo passado, é um valor que nunca é passado. Ele vira `-clientParam mopDir=...` no argv do
GATOR (`rv-static-analysis/config.py:369`). O `RvsecAnalysisClient` extrai dali a lista de
métodos-alvo via `MopSpecsTargetSource:30-31`, que produz `reachesTarget` no `.apk.json`, que o
`result_processor.py:487-490` converte em `cov_reaches_target` e `cov_directly_reaches_target`.

**Gravidade por conjunto** — é o que a revisão 1 não graduou, e muda a leitura do defeito. Os
números abaixo saem do `JavamopFacade`, que é **o mesmo código** que o GATOR usa para resolver
alvos (§7):

| Conjunto | `.mop` | assinaturas | pares | owners | Efeito |
|---|---|---|---|---|---|
| `jca` | 23 | 120 | 68 | 22 | nenhum — coincide com o default |
| `jca_android` | 23 | 119 | 67 | 22 | **desprezível**: um par de diferença, `(MessageDigest, reset)` |
| `generic` | 118 | **296** | **284** | **95** | **interseção com `jca`: zero pares** — ver abaixo |
| `custom` | arbitrário | — | — | — | idem, imprevisível |

Os alvos **não** saem da spec instalada; saem do diretório para onde o GATOR é apontado, e ele
aponta para `jca` sempre. Num run `--specification-set generic`, o APK sai tecido com monitores
sobre 284 pares `(classe, método)` de `ReentrantLock`/`Condition`/`Iterator`, e `cov_reaches_target`
responde *"quantos métodos do app alcançam um dos 68 pares JCA?"* — e esses dois conjuntos não têm
**um único elemento em comum**. Não é imprecisão de medida: é outra pergunta. A correta nunca é
calculada.

**Por que ninguém tropeçou**: nenhuma campanha rodou `generic` pelo `rv-experiment` (varredura em
todos os `experiment_config.json` fora de `backup/`: 46 `jca`, 3 `jca_android`, 1 `custom`). O único
run `custom` — `results/gh99_jca_android_monitors`, apontando para `jca_android` — tem
`run_static_analysis: false`, então o defeito não teve como morder. Os dois únicos runs de fato
expostos são as sondas gh105 (`jca_android` com análise ligada), onde o delta é um par e a medição
de ponta a ponta deu **0 vereditos diferentes em 106 métodos** (relatório §3.3). O caminho manual já
contorna: `scripts/static_analysis_sweep_generic.py:878-879` aceita `--mop-dir` explícito.

Formulação honesta do D2: **o dano observado em toda a história do projeto é zero; o `generic` e o
`custom` são inutilizáveis para cobertura pelo caminho do `rv-experiment`, e o modo de falha é
silencioso — uma coluna do `summary.csv` com um número plausível e errado.**

**Efeito colateral do reparo, que precisa estar declarado antes da change abrir**: hoje todo run
aponta o GATOR para 120 assinaturas, qualquer que seja o conjunto. Depois do reparo, um run
`generic` passa a apontar para **296** — o custo da resolução de alvos e o conteúdo de
`reachesTarget` no `.apk.json` mudam para esse conjunto. Não regride ninguém, porque nenhuma
campanha roda `generic` pelo `rv-experiment`, mas é mudança de comportamento observável e o critério
de aceitação tem de medi-la em vez de supô-la.

> `openspec/specs/experiment/spec.md:67`, decisão 7 — *"**Specification set isolation.** Each
> experiment uses exactly one specification set... **Specification sets are never mixed within a
> single experiment.**"* A frase seguinte fala só de geração de monitores; o acoplamento com a
> análise estática nunca foi escrito, e é essa a lacuna.

**Reparo**: extrair o mapa `specification_set → dir` de `get_monitor_generation_config()`
(`config.py:695-719`, que já despacha os quatro valores e levanta `ConfigurationError` no default)
para um método único, e chamá-lo dos dois lados.

### P3 — o CLI declara sucesso incondicional

| Onde | Especificado? |
|---|---|
| `rv-experiment/__main__.py:747-749` | lacuna: `experiment/spec.md:276` (e `:281`) **manda** `run()` devolver `False`, e esse valor não tem leitor |

O retorno de `execute_with_config()` é descartado — e ele **é** declarado `-> bool`
(`experiment_controller.py:386-400`), devolvendo o `False` que `ExperimentController.run()` produz
quando a Fase 2 acusa falha. `✅ Experiment completed successfully!` sai sempre, e `sys.exit(1)` só
acontece no `except`. Uma linha, e o `__main__.py:747` é o **único** chamador da função no
repositório inteiro. Enquanto isso valer, nenhum código de saída serve para automação ou teste de
aceitação.

**O reparo é de uma linha; o raio não é — e a revisão 5 mediu o raio.** Os dois entrypoints Docker
fazem `exec uv run ... rv-experiment run` (`docker/rvandroid/docker-entrypoint.sh:101`,
`docker-entrypoint.frozen-no-dev.sh:94`), de modo que o código de saída do container passa a ser o
do CLI. Varredura em todos os orquestradores de campanha, procurando quem lê `State.ExitCode`:

| Orquestrador | O que faz com o código de saída | Efeito do reparo |
|---|---|---|
| `experimento-gh104/scripts/cycle.sh:30-33` | chaveia o resume em `State != "running"` — **não olha o código** | **nenhum**; a campanha em preparação é indiferente |
| `experimento-20260706/scripts/restart_exited.sh:12-20` | só reinicia `ExitCode 137` (OOM-kill), *"e SOMENTE esses"* | nenhum; sair 1 não dispara re-run |
| `experimento-20260604/scripts/run_smoke.sh:19-25` | `exit $EXIT` — aborta o smoke se ≠ 0 | **muda**: um smoke com falha parcial na Fase 2 passa a reprovar, que é o desfecho correto |

Os demais (`monitor_*.sh`, `rv_status.py`) leem `State.Status`, não o código. O critério de
aceitação do P3 é essa tabela: nenhum orquestrador trata container ≠ 0 como fatal ou como gatilho de
re-run, e o único gate que muda de resposta passa a dar a resposta certa.

### D1 + G1 — a raiz do SDK nunca chega ao GATOR

| Onde | Especificado? |
|---|---|
| `lib/gator/gator:62-64` (subscrito nu em `ANDROID_SDK_HOME`) | não previsto |

O `gator` lê `os.environ['ANDROID_SDK_HOME']` sem `get`, sem default e sem alternativa. Quem tem só
`ANDROID_HOME` exportado — o que é o normal fora do Docker — recebe um `KeyError` cru.

**Reparo: fallback em `lib/gator/gator:62-64`.** Três linhas, **zero** testes tocados, e cobre as
10 portas de entrada, incluindo os chamadores que montam o argv por conta própria (`gh91_sa_rerun`,
os sweeps em `scripts/`). Verificado por execução, os dois ramos (§7).

**Duas armadilhas:**

1. O flag é **`--sdk`** (`lib/gator/gator:195`, `dest='sdkpath'`). **Não existe `--sdkpath`** — e
   como `:254` usa `parse_known_args()`, passá-lo não dá erro: o token vai para a JVM e o `KeyError`
   dispara igual. Verificado por execução. O nome errado está em quatro documentos (§8).
2. O fallback deve valer **apenas quando a raiz for resolvível**, para não regredir quem tem só
   `ANDROID_SDK_HOME` exportado, que é o que a documentação vem mandando desde julho.

**Frequência real**: só morde fora do Docker — a imagem exporta a variável. Mas as campanhas gh91 e
gh105 rodaram no host, então o caminho do host é o que importa.

**A segunda camada saiu do escopo na revisão 5.** A revisão 4 propunha também emitir `--sdk` em
`get_tool_command()` (~6 asserções de argv). São duas camadas para o mesmo defeito, e a de baixo
cobre 10 portas onde a de cima cobre 5. O argumento a favor era de coerência — hoje o config Python
lê `ANDROID_HOME`, deriva `android_platforms_dir` e `android_jar` e **descarta tudo** — mas essa
coerência é teórica enquanto `validate_on_init=False` (`rv-experiment/config.py:956`) impedir que
qualquer coisa derivada dali seja validada. Fica registrado como incoerência conhecida, sem reparo.

### O parâmetro morto — o único item de faxina que entra

`_create_platform_config` (`execution_controller.py:219-228`) recebe `apks: List[App]` e **nunca o
lê**: o corpo resolve o diretório por conta própria (`:260-262`). Remover custa quatro sítios — a
assinatura, o chamador de `:140` e dois casos de teste em
`tests/experiment/test_execution_controller.py:207,232`. Entra por P3 do `CLAUDE.md` (código morto
é deletado inteiro), não por dano.

### Faxina do `gator` — examinada na revisão 5 e **descartada**

A revisão 4 levava quatro itens do `gator` "de carona, sem decisão". A revisão 5 aplicou a eles as
mesmas perguntas que mataram as outras alegações, e nenhum sobreviveu. Ficam registrados aqui para
não serem rederivados.

| Item | Onde | Por que saiu |
|---|---|---|
| **G2** — `call(cmd, timeout=...)` descarta o exit code da JVM | `:111` | `result.success` tem **um único leitor** em todo o repositório: um `logger.warning` em `pre_processor.py:359`. O reparo muda uma linha de log. Além disso o sentinela consertado (J1) entrega, com prova em disco, o sinal que este ia aproximar |
| **G3** — timeout externo e interno com o mesmo `analysis_timeout` | `:112-113`, `:119` vs `static_analysis.py:279` | **a alegação da revisão 4 estava errada** — ver abaixo. E mexer no par de timeouts é calibração: muda *quando* runs morrem |
| **G4** — `<sdk>/tools/bin/sdkmanager` é layout legado | `:95` | o ramo só roda quando falta o `android.jar` do nível alvo, e **não disparou em nenhum dos 30 logs** da campanha `SA_RERUN_gh91_wtg`. Corrigir o caminho não remove o symlink de `docker/android/Dockerfile:53-56`; só acrescenta um segundo jeito de funcionar |
| **G5** — `parse_known_args()` repassa flags desconhecidas à JVM | `:254` + `:104` | **e ainda bem que repassa.** O parser declara onze flags (`:183-246`) e **nenhuma** delas é `-client`, `-clientParam`, `-cgAlgorithm`, `-cgDelegation` ou `-sootandroidDir`. Esse repasse *é* o mecanismo pelo qual todo parâmetro do cliente RVSEC chega ao `presto.android.Main`. "Consertar" quebraria toda invocação do repositório |

**Correção à revisão 4 sobre o G3.** Ela afirmava que o ramo `except TimeoutExpired: sys.exit(-50)`
de `:112-113` é código morto porque o timeout externo mata primeiro. **É falso, e a prova está na
própria evidência do J1**: `-50` sai como código 206 (256−50), e `rc: 206` é exatamente o que os
cinco `_progress/*.json` registram. O ramo é inalcançável **apenas** pelo caminho do `rv-experiment`,
onde `static_analysis.py:279` arma um `Command` com o mesmo valor e o mata antes
(`command.py:181`, que conta desde antes do apktool decode). Pelo caminho das campanhas, que dirigem
o `gator` direto com folga externa, ele é a saída normal.

O que sobra de verdadeiro no G3, e fica sem reparo: qualquer que seja o timeout que vença,
`remove_temp_dirs()` (`:119`) não roda, e o diretório do apktool fica em `/tmp` (há resíduos
`/tmp/gator-*` agora). Não foi medido o tamanho acumulado — os que restam estão vazios. Se disco
apertar, é uma issue própria, não parte desta change.

**Sobre a proveniência do arquivo**: `git blame` põe todas essas linhas em `2649eae0` (2024-09-25,
*"including gator in rv-android libs"*) — é código do GATOR upstream, importado como veio. As
**três** edições locais são o nome do jar mais `-outputFile` (`cf649214`, 2024-10-05), `--jvm-memory`
(gh9, `912269e4`) e `-cgAlgorithm` (gh51, `1086ebaf`) — e são elas o precedente de que **o arquivo
é editável**: o reator só copia o jar (`rvsec-gator/pom.xml:82-89`, um único `<include>`), e o
`gator` é rastreado no git. É esse precedente que sustenta o reparo do D1, que continua no escopo.

---

## 2. Alegações refutadas — não rederivar

### 2.1 Mortas nesta revisão

| Alegação | Veredito |
|---|---|
| **D3** — "a lista filtrada pelo INV-EXP-16 chega ao `_create_platform_config` e nunca é lida; o platform instala APKs que a análise estática excluiu" | **comportamento especificado.** INV-PLT-05 (`platform/spec.md:164`): *"Static analysis data loading failure MUST NOT prevent task execution... it MUST return `True` and log a warning."* O `rv-platform` **apenas executa** — não sabe nem se importa se o APK foi instrumentado, e carrega o `.apk.json` se existir. O cenário "Mixed instrumentation results filter downstream phases" (`experiment/spec.md:239-244`) só obriga, na linha que nomeia `get_instrumented_apks()` (`:244`), a **devolver** 6 de 7 — e ela devolve. A obrigação de o platform honrar a lista eu inferi; não está escrita. Some-se a isto o que a própria revisão 1 já media: divergência exige falha **parcial** de análise estática, e a frequência real é **zero**. Sobra o parâmetro morto de `_create_platform_config` (§1) |
| **P1** — "`validate_on_init=False` no único construtor de produção" | **impacto ~zero, e ligar regride.** As quatro checagens de `config.py:242-318`: `lib_dir`/`output_dir` são sempre preenchidos pelo chamador; launcher e jar ausentes já falham com mensagem específica na pós-condição de `static_analysis.py:287-291`; `mop_dir` é *sempre* o default `jca`, que existe em qualquer instalação — **a checagem não tem como disparar**; e a do SDK valida um `android_jar` que **ninguém consome** (o `gator` recalcula o dele), então ligá-la faria falhar quem tem só `ANDROID_SDK_HOME` exportado. Só passaria a significar algo depois do D2, e a checagem do SDK continuaria sem consumidor mesmo assim — foi por isso que a segunda camada do reparo do SDK saiu do escopo na revisão 5 (§1) |
| **P2** — "falha de geração de monitores vira `warning` e a instrumentação segue sobre diretório vazio" | **guarda já existe, nas duas variantes.** `ajc`: `config.py:501` chama `_validate_monitor_artifacts()`, que levanta `ConfigurationError` sem `*.aj` **ou** sem `*.java`. `dexlib2` (a que as campanhas usam): `dexlib_instrumentation.py:77-82` e `:508-514` exigem ao menos um descritor `MultiSpec_*MonitorAspect.json`, com exceção dedicada em `errors.py:10`. Há ainda a verificação por hash (`ajc_instrumentation.py:1698-1712`), que recusa APK byte-idêntico ao original. O desfecho real é: aviso → instrumentação recusa cada APK → INV-EXP-08 copia originais → run a 0% de cobertura com os 162 no `instrument_errors.json`. **Degradação especificada e registrada em artefato**, não silêncio |
| "o `mop_dir` efetivo vira coluna do `summary.csv`" | **redundante.** `experiment_config.json` já é gravado por run (`experiment_controller.py:377`) e já carrega `specification_set` — verificado em `results/gh105_reach_probe_b/experiment_config.json`. Depois do D2, `spec_set → mop_dir` é função. Coluna nova não acrescenta nada e mexe em header |

### 2.2 Mortas na revisão 1

Onze alegações, em sua maioria por serem comportamento especificado. A tabela integral está em
`backup/20260821_plano_correcao_analise_estatica.v1.md` §2, com a citação que decide cada uma.
Em resumo: INV-EXP-08 (originais copiados), INV-ANA-11 (cache por existência de arquivo),
INV-PLT-12 (escopo do checksum de resume), INV-ANA-25 (retorno antecipado de `coverage.py`),
INV-PLT-15/16 (`_percentage()` com total zero), `experiment/spec.md:125,154` +
INV-EXP-02 (`post_processing_completed`), `docs/architecture/static-analysis.md:171` (a sonda de API
levels), `MopSpecsParityTest` (`mopDir` vazio), INV-EXP-08/15/16 (`if not success`),
INV-PLT-05 (o platform desiste da análise em silêncio).

**Lição de método, registrada de propósito**: das vinte e quatro alegações levantadas nesta sessão,
**quinze** morreram por eu não ter perguntado *"existe invariante ou guarda que já cobre isto?"*
antes de chamar de defeito. Essa checagem é obrigatória para qualquer achado novo neste sistema.

---

## 3. Fora desta change

| # | Item | Estado |
|---|---|---|
| **N9** | `UsedJcaMethodsVisitor:70-77` descarta **em silêncio** — sem `else`, sem log — o pointcut cujo owner não está em import explícito. `RandomStringPassword.mop` é 1 das 23 specs do `jca` e contribui **zero** alvos, em toda campanha já rodada, enquanto os seus dois pointcuts são tecidos e vivos (`rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879`) | **vai para a gh69 como RISK-013, nível High** (2026-08-21) — ver abaixo |
| **B4 da gh104** | **não reabrir.** O estágio 2 reusa os `.apk.json` da `comp162`, a análise estática não roda e o `mop_dir` fixo nunca é consultado. Reabrir custaria o desenho pareado (denominadores diferentes entre `comp162` e gh104) e uma varredura de análise estática sobre 162 APKs com timeouts de 7200 s. O preço já está declarado em `experimento-gh104/CONTEXTO.md:159-161` (a linha `:147` é só a célula "não morde" da tabela B): `cov_mop` da gh104 é a régua da `comp162` aplicada aos dois lados, de propósito. O D2 corrigido **não muda a gh104**, precisamente porque lá a análise não roda — a correção é segura de aterrissar antes da campanha |

---

**Sobre o N9, e por que ele é grave — leia antes de tratar a §3 como "só encaminhamento".** Este
plano repara, no D2, um numerador e um denominador que vêm de conjuntos diferentes. O N9 é a **mesma
doença dentro do `jca`**: todo `cov_reaches_target` já publicado a partir da régua congelada foi
calculado sobre **22 das 23** specs, porque uma delas some antes de virar alvo. Três propriedades o
tornam grave, e nenhuma delas é o tamanho: o descarte é **silencioso**, é **estrutural e repetível**
para qualquer spec futura com owner não importado, e cai sobre a **régua**, não sobre um
diagnóstico. Delimitação honesta, medida em 2026-08-21: em todas as campanhas da árvore aparecem 16
specs distintas no `errors.csv` e `RandomStringPasswordSpec` não é uma delas — nenhuma contagem de
violação publicada está errada; o denominador de alcance é que está.

Registrado como **RISK-013 (High)** em
`openspec/changes/gh69-generic-subtype-target-matching/risk-register.md`, com a anotação propagada
para `proposal.md`, `design.md` (Non-Goals), `tasks.md` (1.3(b), 1.5, 5.6) e a delta spec
(INV-ANA-40, scope boundary (c)). A gh69 quita a metade que o tornava grave — o silêncio — logando o
owner descartado; o reparo da medição continua diferido, porque a meia-correção é medidamente pior
(74 call sites, 17 tecidos, 57 falsos positivos).

## 4. Ordem de execução

Sem dependências fortes entre os seis. A ordem é por custo crescente:

| | Passo | Custo |
|---|---|---|
| 1 | **P3** — o CLI consome o booleano e sai ≠ 0 | 1 linha |
| 2 | **D1 + G1** — fallback da raiz do SDK no `gator` | 3 linhas, zero testes |
| 3 | **parâmetro morto** de `_create_platform_config` | 4 sítios (assinatura, 1 chamador, 2 testes) |
| 4 | **as três correções documentais** da §8 | 3 edições de uma linha |
| 5 | **J1** — o sentinela só na escrita pós-WTG | pequeno, lado Java; exige rebuild do reator |
| 6 | **D2** — o `mop_dir` deriva do `specification_set` | o de maior alcance; toca os dois lados do mapa |

O J1 é o único que exige rebuild do reator Java
(`mvn clean install -DskipMopAgent -DskipTests`, com JDK 21 no prefixo), então convém agrupá-lo com
o commit que recopia os jars. A correção do comentário de `RvsecAnalysisClient.java:157-163` é parte
do passo 5, não da §8.

### 4.1 Complexidade, risco e critério de aceitação por item

Esta é a tabela que a `tasks.md` da change consome. Complexidade é tamanho da edição; risco é o que
pode dar errado *depois* de a edição estar certa.

| # | Item | Complexidade | Risco | O que prova que está feito |
|---|---|---|---|---|
| 1 | exit code do CLI | trivial, 1 linha | **médio** — muda o código de saída do container | a tabela de orquestradores da §1 reconferida: gh104 indiferente, `restart_exited` só 137, smoke de 2026-06-04 passa a reprovar falha parcial |
| 2 | fallback da raiz do SDK | trivial, 3 linhas | baixo — acrescenta caminho, não remove | as duas invocações da §7 rodam: sem `ANDROID_SDK_HOME` e com só `ANDROID_HOME`, o `gator` passa de `:64` |
| 3 | parâmetro `apks` morto | trivial, 4 sítios | baixo — quebra em compilação/teste | `uv run pytest --import-mode=importlib -o "addopts=" tests/` verde em `rv-experiment` |
| 4 | três frases documentais | trivial | nulo | `grep -r -- "--sdkpath"` não acha mais nos dois documentos vivos |
| 5 | sentinela `complete` | média + rebuild do reator | **médio-alto** — ver §4.2 | os cinco APKs da §1 reprocessados deixariam de sair com `complete=true`; e o teste novo da §4.2 rodando **com os testes ligados** |
| 6 | `mop_dir` do conjunto | média, dois lados | médio — ponto de escalonamento de trilha (§5) | asserção de `mop_dir` por conjunto nos quatro valores; e a medida do efeito colateral: run `generic` passa de 120 para 296 assinaturas |

### 4.2 O item 5 já tem três camadas de teste, e nenhuma alcança o defeito

Isto é o que a revisão 4 não dizia, e é a informação mais importante para quem implementar: **não é
verdade que falta teste do sentinela.** Existem três, e todas passam enquanto o defeito existe.

| Camada | O que assere | Por que não pega o J1 |
|---|---|---|
| `rvsec-gator/client/src/test/java/.../json/SentinelEmissionTest.java` | replica **em teste** a sequência do writer e injeta `RuntimeException` em cada fronteira de seção: abortou → sem sentinela | o J1 **não tem exceção**. É uma chamada de `write()` bem-sucedida, só que a pré-WTG. E o próprio cabeçalho do teste declara: *"What it does NOT test: the production `JsonReportWriter.write(...)` method itself"* |
| `tests/parity/test_sentinel_emission.py` | roda o GATOR de ponta a ponta no `cryptoapp` e confere os bytes finais do arquivo | é um run **completo**: a segunda escrita sobrescreve a primeira, e o sentinela está no lugar certo. O caso do J1 é o run que nunca chega à segunda |
| `modules/rv-static-analysis/tests/parser/test_sentinel.py` | quatro formas do lado do **parser** (presente/ausente/false/truncado) | testa quem lê, com fixtures sintéticas; não tem opinião sobre quem escreve |

O buraco é preciso: **ninguém exercita a escrita pré-WTG isolada**, porque hoje ela não é
isolável — só acontece dentro de um run que segue adiante. É o parâmetro `emitSentinel` do reparo
que a torna testável pela primeira vez. O teste a acrescentar, então, não é "mais um teste do
sentinela": é a chamada direta de `write(..., emitSentinel=false)` asserindo que o arquivo
resultante **não contém** a chave `complete` — o caso que os cinco APKs do `SA_RERUN_gh91_wtg`
provam existir em produção.

**E ele não roda por padrão.** `rvsec/rvsec-android/rvsec-gator/pom.xml:18` fixa
`<skipTests>true</skipTests>`, de modo que o módulo **compila** os testes e **não os executa**: o
build do reator dá verde sem ter rodado nada. O critério de aceitação do item 5 tem de incluir a
execução explícita com os testes ligados, senão o reparo entra sem prova — e essa é exatamente a
armadilha que o `-DskipTests` do comando de build da §7 esconde.

---

## 5. Trilha e escopo da change

**Uma única change, trilha Quick Path** (`docs/WORKFLOW.md:150-196`, schema `quick-path`, 3 fases,
artefatos `plan` → `tasks`). O guia de decisão da §3 do WORKFLOW responde direto: *"Is it a bug fix,
cleanup, or documentation update? Yes → **Quick Path**"* e *"Does it remove/refactor without adding
new documented behavior? Yes → **Quick Path**"*.

Os quatro reparos **não introduzem comportamento novo** — eles fazem o código passar a obedecer
invariantes que já existem (INV-ANA-31 no J1, decisão 7 no D2) ou a devolver o que a spec já manda
(`experiment/spec.md:276` no P3). Nada aqui pede proposal, delta spec ou design.

**Escopo da change — seis itens, fechado na revisão 5:**

1. **J1** — o sentinela só na escrita pós-WTG, mais a correção do comentário que o desmente.
2. **D2** — o `mop_dir` deriva do `specification_set`, pelos dois lados do mesmo mapa.
3. **P3** — o CLI consome o booleano e sai ≠ 0.
4. **D1 + G1** — fallback da raiz do SDK em `lib/gator/gator:62-64`.
5. O parâmetro `apks` morto de `_create_platform_config`.
6. As três pendências documentais da §8.

**Nenhuma spec principal é editada, e isso é condição da trilha.** Acrescentar o acoplamento à
decisão 7 de `openspec/specs/experiment/spec.md` seria texto normativo novo — exatamente o gatilho
da §3 do WORKFLOW (*"introduce new behavior that must be documented in specs? → Full ou FF SDD"*) —
e a Quick Path não tem como sincronizá-lo, já que arquiva com `--skip-specs`. Os dois precedentes de
trilha confirmam a regra na prática: `gh86-dexlib2-apk-paths-contract` e `gh59-fix-wide-slot-binding`
têm só `plan.md` + `tasks.md`, e seus commits não tocaram `openspec/specs/`. O acoplamento
experimento ↔ análise estática fica registrado em `docs/architecture/static-analysis.md`, que é
documentação de arquitetura, não contrato. Se a decisão 7 tiver mesmo de crescer, isso é uma segunda
change, de trilha FF SDD, depois desta. (*"INV-ANA-31 ganha teste"* continua no escopo: teste para
invariante que já existe não é edição de spec.)

**Esta regra vale também para a §8**, e a revisão 4 a contradizia: ela listava
`openspec/specs/experiment/spec.md:209` como pendência documental. Saiu — ver §8.

**Não fracionar.** Os seis compartilham a mesma superfície (o acoplamento experimento ↔
análise estática), tocam cinco arquivos do lado Python, um do lançador e dois da árvore Java, e dois
deles somam quatro linhas (P3 uma, D1 três); o J1 é um parâmetro, uma guarda e dois chamadores.
Seis changes para isso seria o anti-padrão que a própria §3 do WORKFLOW nomeia — *"a sledgehammer to
crack a nut"*.

**A objeção previsível, e a resposta.** A §1 diz que o acoplamento com a análise estática nunca foi
escrito, e é essa a lacuna — de modo que alguém pode ler o D2 como comportamento novo, que pediria
trilha maior. Não é: o acoplamento **já existe de fato**, com o valor errado. O reparo faz o código
deixar de contradizer a decisão 7, que já manda um conjunto por experimento. O que falta na spec é a
*menção* ao acoplamento, não uma regra nova — e essa menção, se tiver de existir, é a segunda change
já prevista dois parágrafos acima.

**Ponto de escalonamento**: se, ao mexer no D2, ficar decidido **remover** o default `jca` de
`rv-static-analysis/config.py:199-208` em vez de só passar o `mop_dir` correto, isso muda o
comportamento de todo chamador standalone e aí a change escala para FF SDD. Enquanto o default
continuar de pé como rede, Quick Path basta.

Nota de método que sobrevive a qualquer escolha: a assinatura *"`coverage.csv` só com cabeçalho"*
já tem **pelo menos três causas distintas** conhecidas (a da gh102, o D1, e o descarte não contado
de `coverage.py:655-674`). Um diagnóstico futuro não pode assumir a causa.

## 6. Módulos afetados

| Módulo | Arquivos |
|---|---|
| `rv-experiment` | `__main__.py` (P3), `config.py` (D2), `experiment/workflow/execution_controller.py` (parâmetro morto) |
| `rv-static-analysis` | `config.py` (D2) |
| `lib/gator/gator` | `:62-64` (D1/G1) — **editável, com precedente** (§1) |
| árvore Java (reator `rvsec`) | `JsonReportWriter.java:111`, `RvsecAnalysisClient.java:157-170` (J1) |
| Testes | ver §4.1 — a cobertura do sentinela **já existe em três camadas** e nenhuma delas alcança o J1; asserção de `mop_dir` por conjunto (D2); os dois casos de `test_execution_controller.py` que passam `apks` |
| Docs | `docs/architecture/static-analysis.md` §3 (a afirmação de validação de `:85` que o `validate_on_init=False` desmente) e o registro do acoplamento `specification_set → mop_dir` |
| OpenSpec | **nenhuma spec principal editada** — ver §5 |

---

## 7. Como reproduzir

Todos os blocos abaixo foram executados em 2026-08-21 e reexecutados na revisão 5.

### J1 — o sentinela que mente

```bash
python3 - <<'EOF'
import json, glob, os
D = "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
for p in glob.glob(os.path.join(D, "_progress", "*.json")):
    d = json.load(open(p))
    if not d.get("timed_out"): continue
    # o registro em _progress/ e o artefato têm o MESMO nome (`<pkg>_<vc>.apk.json`);
    # tirar sufixo aqui é o que fazia a versão anterior deste script não achar nada
    name = os.path.basename(p)
    hits = [h for h in glob.glob(os.path.join(D, "**", name), recursive=True) if "_progress" not in h]
    if hits:
        a = json.load(open(hits[0]))
        print(name, "complete=", a.get("complete"), "reach=", len(a.get("reachability", [])),
              "trans=", len(a.get("transitions", [])), "rc=", d.get("returncode"))
EOF
# esperado: 5 APKs, todos complete=True, trans=0, rc=206
# rc=206 é `sys.exit(-50)` de gator:113 — o ramo TimeoutExpired, que a revisão 4
# chamava de código morto (§1, correção ao G3)
```

### D1 — a precedência real dos argumentos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator
env -u ANDROID_SDK_HOME python3 ./gator a --sdkpath /tmp/fake -p x.apk --out /tmp/o.json
#   -> KeyError: 'ANDROID_SDK_HOME'   (o argumento foi engolido por parse_known_args)
env -u ANDROID_SDK_HOME python3 ./gator a --sdk /tmp/fake -p x.apk --out /tmp/o.json
#   -> passa de :64 e morre adiante por outro motivo (apktool.yml inexistente)
```

### D2 — o tamanho dos conjuntos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
for d in jca jca_android generic; do echo "$d: $(ls $d/*.mop | wc -l) specs"; done
# jca: 23 / jca_android: 23 / generic: 118
head -25 generic/FSM1.mop   # ReentrantLock, Condition, TimeUnit — zero criptografia
```

### D2 — quais conjuntos já rodaram, e com análise ligada

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
find . -name experiment_config.json -not -path "*/backup/*" |
  xargs grep -h -o '"specification_set": "[a-z_]*"' | sort | uniq -c
# 46 jca / 3 jca_android / 1 custom / 0 generic
# o único `custom` (results/gh99_jca_android_monitors) tem run_static_analysis: false
```

### Contagem de alvos por conjunto, e a interseção

Estes números saem do `JavamopFacade`, que é o mesmo código que o GATOR usa
(`MopSpecsTargetSource:30-31`) — não é aproximação por expressão regular. O `Count.java` e o `javac`
que o compila estão em `docs/20260821_handoff_gh69_coringas.md` §8.1; copie o bloco de lá inteiro,
porque só a linha do `java` não roda sem a classe compilada. Depois de gerá-la em `$S`:

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
S=/tmp/gh69_scratch   # o mesmo $S onde o handoff compilou Count.class
java -cp $PWD/rvsec/rvsec-mop-extractor/target/mop-extractor.jar:$S Count \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca_android \
    $PWD/rvsec/rvsec-mop/src/main/resources/generic
# RESULT jca          signatures=120 pairs=68  owners=22
# RESULT jca_android  signatures=119 pairs=67  owners=22
# RESULT generic      signatures=296 pairs=284 owners=95
```

A interseção, que é o número que gradua o D2 (mesma classe `Count`, trocando o corpo por um
`retainAll` entre os dois conjuntos de pares):

```
jca=68  generic=284  interseção=0  []
```

Zero pares em comum. Num run `generic`, o denominador da cobertura e o conjunto tecido no APK são
universos disjuntos.

### P3 — quem lê o código de saída do container

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
grep -rn "State.ExitCode" --include="*.sh" --include="*.py" scripts/ experimento-*/scripts/ |
  grep -v results/
# experimento-20260706/scripts/restart_exited.sh  -> só 137 (OOM), "e SOMENTE esses"
# experimento-20260604/scripts/run_smoke.sh:19    -> aborta o smoke se != 0
# a gh104 não aparece: cycle.sh:30-33 chaveia em State != "running"
```

---

## 8. Pendências documentais — três, depois da triagem

Entram na change:

| Item | Onde |
|---|---|
| `--sdkpath` → `--sdk` nos dois documentos **vivos** | `docs/20260730_verificacao_consistencia_gh91.md:617` e `docs/20260821_relatorio_analise_estatica_defeitos.md:92` |
| a doc de arquitetura afirma uma validação que não roda: *"validates that the gator launcher, the analysis-client JAR, `android.jar` and the MOP/targets source exist"* — com `validate_on_init=False` (`rv-experiment/config.py:956`) nada disso é checado no caminho do `rv-experiment` | `docs/architecture/static-analysis.md:85` |
| o registro do acoplamento `specification_set → mop_dir`, que o D2 passa a garantir | `docs/architecture/static-analysis.md` §3 |

O comentário de `RvsecAnalysisClient.java:157-163`, que a revisão 4 listava aqui, é **parte do
reparo do J1** (§1) e não uma pendência à parte.

**O que saiu, e por quê** — para não ser rederivado:

| Item da revisão 4 | Por que saiu |
|---|---|
| `--sdkpath` em `archive/2026-07-31-gh91-.../design.md:143` e `.../tasks.md:69` | altera o registro histórico de uma change **arquivada**, para consertar uma nota que os dois documentos vivos já vão corrigir |
| `"linha 267"` → 182, e `70/69` → `120/119` no relatório de origem | erratas de um documento que este plano supersede e cuja tabela de erros **é** esta seção; editá-lo é redundante |
| os logs perdidos das sondas, e *"end at `validateInputs()`"* | ambos em `data/gh105/evidence/` — território da **gh105**, em andamento (33/74) no mesmo branch. Não tocar |
| *"a rota descrita não é a que o código percorre"* (`pre_processor.py:448-450` + `openspec/specs/experiment/spec.md:209`) | prescreve editar uma **spec principal**, o que a §5 proíbe e que quebraria a trilha. E a alegação é meia-verdade: o fallback de `pre_processor.py:485` só dispara quando a lista fica *vazia*; no caso misto os originais copiados somem em vez de rodar a 0% — cenário sem ocorrência, já que `_copy_original_apks()` é tudo-ou-nada |
| fechar a issue **#102** no GitHub | conferido: está **OPEN**. É uma ação de dez segundos no GitHub, não uma edição de arquivo; não precisa de change para acontecer |

---

## 9. Referências

* `backup/20260821_plano_correcao_analise_estatica.v1.md` — revisão 1, com a tabela integral das
  onze refutações originais.
* `backup/20260821_plano_correcao_analise_estatica.v4.md` — revisão 4, para ver o que a triagem da
  revisão 5 cortou (`diff -u`).
* `docs/20260821_relatorio_analise_estatica_defeitos.md` — relatório de origem (D1/D2/D3).
* `docs/20260821_handoff_gh69_coringas.md` — o N9 e o que fazer na gh69; a §8.1 tem o `Count.java`.
* `docs/architecture/static-analysis.md` — arquitetura do subsistema.
* `openspec/changes/archive/2026-07-22-gh86-dexlib2-apk-paths-contract/` e
  `openspec/changes/archive/2026-05-25-gh59-fix-wide-slot-binding/` — precedentes de **trilha**:
  Quick Path com `plan.md` + `tasks.md` apenas, sem edição de `openspec/specs/`.
* `openspec/changes/archive/2026-08-16-gh102-artifact-scoped-parse/` — precedente de **artefato e de
  assinatura observável**, não de trilha: a gh102 correu sob o schema `rv-sdd`, com proposal,
  design e delta specs.
* `data/gh105/evidence/f2-reach-probe.md` e `data/gh105/evidence/reach-probe/` — evidência das
  sondas; auditada e byte-idêntica aos originais em `results/`. **Território da gh105 — não tocar.**
