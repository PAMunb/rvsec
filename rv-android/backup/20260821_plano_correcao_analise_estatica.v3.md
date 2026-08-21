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
**Natureza**: Fase 0 do `docs/WORKFLOW.md` — material de referência, não artefato OpenSpec
**Origem**: `docs/20260821_relatorio_analise_estatica_defeitos.md`
**Supersede**: `docs/20260821_verificacao_relatorio_analise_estatica.md`
**Status**: nada implementado, nenhuma issue aberta, nenhuma change criada. A gh105 não foi tocada.

---

## 0. O que sobrou, em uma frase

Dos treze defeitos que a revisão 1 alegava, **quatro** têm dano demonstrável, e só **um** tem prova
de dano em artefato real. O resto era comportamento especificado, guarda já existente, ou defeito
latente com frequência zero. Esses quatro entram numa **única change de trilha Quick Path** (§5) —
três deles somam menos de dez linhas.

Critério de admissão, mantido da revisão 1 e agora aplicado com mais rigor: nada entra sem
(a) citação `arquivo:linha` e (b) resposta à pergunta **"existe invariante, spec ou guarda que já
cobre isto?"**. Foi essa segunda pergunta que matou a maioria dos itens.

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
eles passam. O `scripts/gh91_campaign.py:133-147` já compensa à mão (exige sentinela **e**
`timed_out == False` do `_progress`); o pipeline `rv-platform` não compensa.

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

Esse `mop_dir` vira `-clientParam mopDir=...` no argv do GATOR (`rv-static-analysis/config.py:369`).
O `RvsecAnalysisClient` extrai dali a lista de métodos-alvo, que produz `reachesTarget` no
`.apk.json`, que o `result_processor.py:487-490` converte em `cov_reaches_target` e
`cov_directly_reaches_target`.

**Gravidade por conjunto** — é o que a revisão 1 não graduou, e muda a leitura do defeito:

| Conjunto | `.mop` em disco | Efeito |
|---|---|---|
| `jca` | 23 | nenhum — coincide com o default |
| `jca_android` | 23 | **desprezível**: 120 vs 119 assinaturas, 68 vs 67 pares, os mesmos 22 owners |
| `generic` | **118** | **a métrica reportada não é a do que foi monitorado** — ver abaixo |
| `custom` | arbitrário | idem, imprevisível |

Os alvos **não** saem da spec instalada; saem do diretório para onde o GATOR é apontado, e ele
aponta para `jca` sempre. Num run `--specification-set generic`, o APK sai tecido com 118 monitores
de `ReentrantLock`/`Condition`/`Iterator` (`generic/FSM1.mop` não menciona criptografia em lugar
nenhum), e `cov_reaches_target` responde *"quantos métodos do app alcançam uma chamada JCA?"* — uma
pergunta sobre um conjunto que não está instalado. A pergunta correta nunca é calculada.

**Por que ninguém tropeçou**: nenhuma campanha rodou `generic` pelo `rv-experiment` (verificado por
varredura nos `experimento-*/`), e o caminho manual já contorna —
`scripts/static_analysis_sweep_generic.py:878-879` aceita `--mop-dir` explícito.

Formulação honesta do D2: **o `generic` e o `custom` são inutilizáveis para cobertura pelo caminho
do `rv-experiment`; o `jca_android` erra por uma assinatura em 120.**

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
acontece no `except`. Uma linha. Enquanto isso valer, nenhum código de saída serve para automação ou
teste de aceitação.

**O reparo é de uma linha; o raio não é** — e isto precisa estar declarado antes de a change abrir.
Os dois entrypoints Docker fazem `exec uv run ... rv-experiment run`
(`docker/rvandroid/docker-entrypoint.sh:101`, `docker-entrypoint.frozen-no-dev.sh:94`), de modo que
o código de saída do container passa a ser o do CLI: um run que hoje termina "verde" com falha
parcial na Fase 2 passará a marcar o container como falho. Como a campanha gh104 está em preparação,
o critério de aceitação do P3 tem de incluir a verificação de que nenhum orquestrador de campanha
trata container ≠ 0 como fatal ou como gatilho de re-run.

### D1 + G1 — a raiz do SDK nunca chega ao GATOR

| Onde | Especificado? |
|---|---|
| `rv-static-analysis/config.py:336-406` (nunca emite `--sdk`) + `lib/gator/gator:62-64` (subscrito nu em `ANDROID_SDK_HOME`) | não previsto |

Fazer **as duas camadas**:

| Opção | Cobertura | Custo |
|---|---|---|
| **A — fallback em `lib/gator/gator:62-64`** | 10 portas de entrada, incluindo os chamadores que montam o argv por conta própria | 3 linhas, **zero** testes tocados |
| **B — emitir `--sdk` em `get_tool_command()`** | as 5 portas que passam por lá | ~6 asserções de argv |

A opção B fecha uma incoerência real: hoje o config Python lê `ANDROID_HOME`, deriva
`android_platforms_dir` e `android_jar` — e **descarta tudo**, deixando o `gator` recalcular seu
próprio `android.jar` a partir de outra variável, não validada.

**Duas armadilhas:**

1. O flag é **`--sdk`** (`lib/gator/gator:195`, `dest='sdkpath'`). **Não existe `--sdkpath`** — e
   como `:254` usa `parse_known_args()`, passá-lo não dá erro: o token vai para a JVM e o `KeyError`
   dispara igual. Verificado por execução. O nome errado está em três documentos (§4).
2. Emitir `--sdk` incondicionalmente quebra quem tem só `ANDROID_SDK_HOME` exportado, que é o que a
   documentação vem mandando desde julho. Emitir **apenas quando a raiz for resolvível** custa o
   mesmo e não regride ninguém.

**Frequência real**: só morde fora do Docker — a imagem exporta a variável.

### Faxina — entra de carona, sem decisão

| # | Item | Onde |
|---|---|---|
| **G2** | `call(cmd, timeout=...)` descarta o exit code da JVM; o `gator` sai 0 sempre | `lib/gator/gator:111` |
| **G3** | o timeout externo (`Command`) e o `--timeout` interno recebem **o mesmo** `analysis_timeout`; o externo mata primeiro → `remove_temp_dirs()` nunca roda e o ramo `TimeoutExpired` é código morto | `:112-113`, `:119` vs `static_analysis.py:279` |
| **G4** | `<sdk>/tools/bin/sdkmanager` é layout legado; funciona só porque `docker/android/Dockerfile:53-56` fabrica o symlink | `:95` |
| **G5** | `parse_known_args()` repassa flags desconhecidas à JVM — é o que faz `--sdkpath` falhar em silêncio | `:254` + `:104` |
| — | parâmetro `apks` de `_create_platform_config` recebido e nunca lido | `execution_controller.py:221` |

**Sobre o G2, correção à revisão 1**: eu o classifiquei como "muda o que é acusado" e exigi decisão.
Está errado. A cadeia inteira: JVM morre de OOM depois de escrever `reachability` → o JSON parcial
fica em disco → a pós-condição de `static_analysis.py:285` passa. Com G2 corrigido → exceção →
`StaticAnalyzer.analyze()` a captura ela mesma (`:259-268`) → `result.success = False` → o laço do
`pre_processor.py:358-361` loga `warning` e vai para o próximo APK → **o JSON parcial continua em
disco** → o INV-EXP-16 continua admitindo o APK → ele executa igual. **Ninguém consome
`result.success`.** G2 muda a linha de log e um campo sem leitor: é observabilidade pura, três
linhas, sem corrida de calibração.

Também não foi decisão de projeto: `git blame` põe a linha em `2649eae0` (2024-09-25, *"including
gator in rv-android libs"*) — é código do GATOR upstream, importado como veio. As duas únicas
edições locais no arquivo são `--jvm-memory` (gh9, `912269e4`) e `-cgAlgorithm` (gh51, `1086ebaf`),
que é também o precedente de que **o arquivo é editável**: o reator só copia o jar
(`rvsec-gator/pom.xml:82-89`, um único `<include>`), e o `gator` é rastreado no git.

---

## 2. Alegações refutadas — não rederivar

### 2.1 Mortas nesta revisão

| Alegação | Veredito |
|---|---|
| **D3** — "a lista filtrada pelo INV-EXP-16 chega ao `_create_platform_config` e nunca é lida; o platform instala APKs que a análise estática excluiu" | **comportamento especificado.** INV-PLT-05 (`platform/spec.md:164`): *"Static analysis data loading failure MUST NOT prevent task execution... it MUST return `True` and log a warning."* O `rv-platform` **apenas executa** — não sabe nem se importa se o APK foi instrumentado, e carrega o `.apk.json` se existir. O cenário que citei (`experiment/spec.md:238-241`) só obriga `get_instrumented_apks()` a **devolver** 6 de 7, e ela devolve. A obrigação de o platform honrar a lista eu inferi; não está escrita. Some-se a isto o que a própria revisão 1 já media: divergência exige falha **parcial** de análise estática, e a frequência real é **zero**. Sobra código morto (§1, faxina) |
| **P1** — "`validate_on_init=False` no único construtor de produção" | **impacto ~zero, e ligar regride.** As quatro checagens de `config.py:242-318`: `lib_dir`/`output_dir` são sempre preenchidos pelo chamador; launcher e jar ausentes já falham com mensagem específica na pós-condição de `:285`; `mop_dir` é *sempre* o default `jca`, que existe em qualquer instalação — **a checagem não tem como disparar**; e a do SDK valida um `android_jar` que **ninguém consome** (o `gator` recalcula o dele), então ligá-la faria falhar quem tem só `ANDROID_SDK_HOME` exportado. Só passa a significar algo **depois** do D2 e do D1-B |
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
| **N9** | `UsedJcaMethodsVisitor` descarta pointcut cujo owner não está em import explícito; `RandomStringPassword.mop` contribui **zero** alvos em `jca` e `jca_android`, em toda campanha já rodada | **vai para a gh69** — `docs/20260821_handoff_gh69_coringas.md` |
| **B4 da gh104** | **não reabrir.** O estágio 2 reusa os `.apk.json` da `comp162`, a análise estática não roda e o `mop_dir` fixo nunca é consultado. Reabrir custaria o desenho pareado (denominadores diferentes entre `comp162` e gh104) e uma varredura de análise estática sobre 162 APKs com timeouts de 7200 s. O preço já está declarado em `experimento-gh104/CONTEXTO.md:147`: `cov_mop` da gh104 é a régua da `comp162` aplicada aos dois lados, de propósito. O D2 corrigido **não muda a gh104**, precisamente porque lá a análise não roda — a correção é segura de aterrissar antes da campanha |

---

## 4. Ordem de execução

Sem dependências fortes entre os quatro. A ordem é por custo crescente:

| | Passo | Custo |
|---|---|---|
| 1 | **P3** — o CLI consome o booleano e sai ≠ 0 | 1 linha |
| 2 | **D1-A + G1** — fallback da raiz do SDK no `gator` | 3 linhas, zero testes |
| 3 | **G2, G3, G4, G5** + o parâmetro morto | faxina, entram junto com o passo 2 |
| 4 | **J1** — o sentinela só na escrita pós-WTG | pequeno, lado Java; exige rebuild do reator |
| 5 | **D1-B** — `--sdk` emitido quando a raiz for resolvível | ~6 asserções de argv |
| 6 | **D2** — o `mop_dir` deriva do `specification_set` | o de maior alcance; toca os dois lados do mapa |

**Pendência documental que acompanha o passo 5**: `--sdkpath` → `--sdk` em
`openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/design.md:143`, `.../tasks.md:69` e
`docs/20260730_verificacao_consistencia_gh91.md:617`.

---

## 5. Trilha e escopo da change

**Uma única change, trilha Quick Path** (`docs/WORKFLOW.md:150-196`, schema `quick-path`, 3 fases,
artefatos `plan` → `tasks`). O guia de decisão da §3 do WORKFLOW responde direto: *"Is it a bug fix,
cleanup, or documentation update? Yes → **Quick Path**"* e *"Does it remove/refactor without adding
new documented behavior? Yes → **Quick Path**"*.

Os quatro reparos **não introduzem comportamento novo** — eles fazem o código passar a obedecer
invariantes que já existem (INV-ANA-31 no J1, decisão 7 no D2) ou a devolver o que a spec já manda
(`experiment/spec.md:276` no P3). Nada aqui pede proposal, delta spec ou design.

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

**Não fracionar em várias changes.** Os quatro compartilham a mesma superfície (o acoplamento
experimento ↔ análise estática), tocam seis arquivos do lado Python mais dois da árvore Java, e três
deles somam menos de dez linhas. Quatro changes para isso seria o anti-padrão que a própria §3 do
WORKFLOW nomeia — *"a sledgehammer to crack a nut"*.

**Escopo da change**: J1 + D2 + P3 + D1(A e B) + a faxina do `gator` (G2, G3, G4, G5) + o parâmetro
morto de `_create_platform_config` + as pendências documentais da §8, que são reparo puro e não
pedem decisão — **com uma ressalva**: duas delas editam artefatos **arquivados**
(`archive/2026-07-31-gh91-.../design.md:143` e `.../tasks.md:69`), o que altera registro histórico.
Decidir na abertura da change se entram ou se a correção do nome do flag fica só nos documentos
vivos.

**Único ponto de escalonamento**: se, ao mexer no D2, ficar decidido **remover** o default `jca` de
`rv-static-analysis/config.py:199-208` em vez de só passar o `mop_dir` correto, isso muda o
comportamento de todo chamador standalone e aí a change escala para Fast-Forward SDD. Enquanto o
default continuar de pé como rede, Quick Path basta.

**Ordem sugerida dentro da change**: a da §4. O J1 é o único que exige rebuild do reator Java
(`mvn clean install -DskipMopAgent -DskipTests`, com JDK 21 no prefixo), então convém agrupá-lo com
o commit que recopia os jars.

Nota de método que sobrevive a qualquer escolha: a assinatura *"`coverage.csv` só com cabeçalho"*
já tem **pelo menos três causas distintas** conhecidas (a da gh102, o D1, e o descarte não contado
de `coverage.py:655-674`). Um diagnóstico futuro não pode assumir a causa.

## 6. Módulos afetados

| Módulo | Arquivos |
|---|---|
| `rv-experiment` | `__main__.py` (P3), `config.py` (D2), `experiment/workflow/execution_controller.py` (parâmetro morto) |
| `rv-static-analysis` | `config.py` (D1-B, D2), `analysis/static/static_analysis.py` (G3) |
| `lib/gator/gator` | `:62-64` (G1), `:111` (G2), `:95` (G4), `:254` (G5) — **editável, com precedente** |
| árvore Java (reator `rvsec`) | `JsonReportWriter.java:111`, `RvsecAnalysisClient.java:157-170` (J1) |
| Testes | teste do sentinela pós-WTG (INV-ANA-31, lado Java); asserções de argv para o `--sdk` (D1-B); asserção de `mop_dir` por conjunto (D2) |
| Docs | `docs/architecture/static-analysis.md` §3, §4 (o argv literal de `:85`), §7 (`:143`), as três correções de `--sdkpath`, e o registro do acoplamento `specification_set → mop_dir` |
| OpenSpec | **nenhuma spec principal editada** — ver §5 |

---

## 7. Como reproduzir

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
# esperado: 5 APKs, todos complete=True, trans=0, rc=206 — executado em 2026-08-21
```

### D1 — a precedência real dos argumentos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator
env -u ANDROID_SDK_HOME python3 ./gator a --sdkpath /tmp/fake -p x.apk --out /tmp/o.json
#   -> KeyError: 'ANDROID_SDK_HOME'   (o argumento foi engolido por parse_known_args)
env -u ANDROID_SDK_HOME python3 ./gator a --sdk /tmp/fake -p x.apk --out /tmp/o.json
#   -> passa de :64 e morre adiante por outro motivo
```

### D2 — o tamanho dos conjuntos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
for d in jca jca_android generic; do echo "$d: $(ls $d/*.mop | wc -l) specs"; done
# jca: 23 / jca_android: 23 / generic: 118
head -25 generic/FSM1.mop   # ReentrantLock, Condition, TimeUnit — zero criptografia
```

### Contagem de alvos por conjunto

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
java -cp rvsec/rvsec-mop-extractor/target/mop-extractor.jar:<scratch> Count \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca \
    $PWD/rvsec/rvsec-mop/src/main/resources/jca_android
# medido 2026-08-21: jca 120 assinaturas / 68 pares / 22 owners
#                    jca_android 119 / 67 / 22
# (o Count.java está em docs/20260821_handoff_gh69_coringas.md §5)
```

---

## 8. Pendências documentais (reparo puro, sem decisão)

| Item | Onde |
|---|---|
| `--sdkpath` → `--sdk` | `openspec/changes/archive/2026-07-31-gh91-.../design.md:143`, `.../tasks.md:69`, `docs/20260730_verificacao_consistencia_gh91.md:617` |
| "linha 267" → linha 182 | `docs/20260821_relatorio_analise_estatica_defeitos.md` §2.4 |
| contagens 70/69 → 120/119 assinaturas (68/67 pares) | `docs/20260821_relatorio_analise_estatica_defeitos.md` §3.3 |
| logs das duas sondas não commitados (vivem em `/tmp`) | copiar `probe_run.log` e `probe_run_b.log` para `data/gh105/evidence/reach-probe/` |
| *"end at `validateInputs()`"* — a última linha `RVSEC-COV` é `setupHmacUI()` | `data/gh105/evidence/f2-reach-probe.md` |
| a rota descrita não é a que o código percorre | `pre_processor.py:448-450` e `openspec/specs/experiment/spec.md:209` |
| o comentário afirma o oposto do código | `RvsecAnalysisClient.java:157-163` |
| issue #102 aberta apesar de arquivada | GitHub |

---

## 9. Referências

* `backup/20260821_plano_correcao_analise_estatica.v1.md` — revisão 1, com a tabela integral das
  onze refutações originais.
* `docs/20260821_relatorio_analise_estatica_defeitos.md` — relatório de origem (D1/D2/D3).
* `docs/20260821_handoff_gh69_coringas.md` — o N9 e o que fazer na gh69.
* `docs/architecture/static-analysis.md` — arquitetura do subsistema.
* `openspec/changes/archive/2026-07-22-gh86-dexlib2-apk-paths-contract/` e
  `openspec/changes/archive/2026-05-25-gh59-fix-wide-slot-binding/` — precedentes de **trilha**:
  Quick Path com `plan.md` + `tasks.md` apenas, sem edição de `openspec/specs/`.
* `openspec/changes/archive/2026-08-16-gh102-artifact-scoped-parse/` — precedente de **artefato e de
  assinatura observável**, não de trilha: a gh102 correu sob o schema `rv-sdd`, com proposal,
  design e delta specs.
* `data/gh105/evidence/f2-reach-probe.md` e `data/gh105/evidence/reach-probe/` — evidência das
  sondas; auditada e byte-idêntica aos originais em `results/`.
