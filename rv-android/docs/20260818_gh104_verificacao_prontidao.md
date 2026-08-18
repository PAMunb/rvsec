# gh104 — verificação rigorosa de consistência e prontidão para execução (2026-08-18)

Oito verificadores independentes, somente leitura, sobre `openspec/changes/gh104-legible-violation-reports/`:
(1) coerência proposal × design × tasks; (2) tasks.md × tasks/*.md × deltas de spec; âncoras de código dos grupos
(3) G rv-monitor, (4) S seed/MetaCrySL, (5) E2 dexlib2, (6) E3/E6 transporte, (7) E1/E4/EV .mop e monitor congelado;
(8) prontidão operacional + reprodução dos números empíricos. `openspec validate --strict`: válida.

## Veredito

**Pronta para executar após as correções ALTA nos artefatos (folded via `opsx:update` em 2026-08-18) e o commit/push
de rotina que precede a regeração da imagem Docker do experimento.** Nenhum grupo é "não executável"; a substância
(decisões, números, âncoras) está confirmada.

Números empíricos reproduzidos e corretos: artigo 97.018 / 70.760 `unknown` (72,93 %) / 8.843 `but found .` / 19 mensagens / 10 colunas;
comp162 19.664 / 15.714 mudas (79,91 %) / 296 sítios / 11 colunas; 6.344 identidades; 51 = 25+26 sítios; 134 eventos = 134 `tryLock` = 134 `unlock`, 0 `finally`;
115 advices = 48/44/9/14; 134 `ExecutionContext`; 21 eventos-predicado = 10+11 em 8 arquivos; 9 `remove(...)`; 13 `Arrays.asList`; 158/114 aliases;
G-2 18 órfãos em 10 specs; G-ERE = 1 (`GCMParameterSpecSpec:48 c2`); MetaCrySL api30 33 regras, pareamento 1:1 dos 21 `.mop`.

## Rotina pré-dispatch (não bloqueante — é o commit/push que antecede regerar a imagem Docker)

| # | Achado | Onde | Correção |
|---|---|---|---|
| R1 | 9 artefatos da change modificados e não commitados (design, proposal, specs/instrumentation, tasks.md, tasks/E10, E3, EV, G, S) + `docs/20260816_javamop_mensagens_change_handoff_prompt.md` untracked (fonte dos comandos do E0) | `git status` | Commitar antes de 2.1 congelar `pre-rename-head` |
| R2 | Working tree sujo em caminhos que a change edita: `modules/aperv-tool/{CLAUDE,README,docs/architecture}.md`, `lib/frame-computer/rv-frame-computer.jar`, `scripts/validate_instrument_jca190.py`, `experimento-cal/*`, docs apagadas | `git status` | Commit / stash / backup explícito |

## ALTA (fazem um subagente errar ou um gate nunca fechar)

| # | Achado | Onde | Correção |
|---|---|---|---|
| A1 | G-PRED inclui o padrão nu `validate(`; `KeyPairGeneratorSpec` tem `validate(int)` local que 8.4 mantém → 6.5, 7.6, 8.10 nunca verdes | tasks.md:126,152; S-seed.md:94 | Padrão `ExecutionContext.instance().validate(` |
| A2 | 2.4 decide os 30 clauses "quando 2.14 puder medir", mas 2.14 espera 6.9; 2.15 exige 2.4 decidida; S-seed.md:3 diz "no dependency" | tasks.md:71,81,82; S-seed.md:3,130-135 | Todo clause nasce `deferred-constant`; promoção só após 2.14 |
| A3 | E1: harness "post-Group-2 snapshot" (tasks 7.7, E1:9) vs comando `--a <seed snapshot>` e Acceptance "seed-vs-E1" | E1-messages.md:115,125 | Trocar para pós-2.7 |
| A4 | 2.3 instrui só 7 dos 11 acusadores; `PBEParameterSpecSpec c3` (parcial) e `CipherSpec i2`, `MacSpec i1/i2` (proveniência) sem instrução; 7.2 assume que os sítios sobrevivem (45) | tasks.md:70,137; design.md:245 | Instrução por evento para os 4 |
| A5 | 2.13 (repoint dos gates gh101) não está no S-seed.md e diz "two" scripts (são três); linhas reais `test_gh101_specset_gates.py:108,122` (não 116/127) | S-seed.md:238,255; tasks.md:80 | Seção 2.13 no S-seed.md |
| A6 | 3.4/D-4: ler `isAtomicMoniorUsed()` no construtor de `HandlerMethod` lança `IllegalStateException` (é decidido só em `toString()`, BM:665) e `RVM_lastevent` não existe na forma atômica; `this.getLastEvent()` existe nas duas formas (`AbstractSynchronizedMonitor.java:21`) | tasks.md:90; design.md D-4; G-eventname.md | Expandir para `this.getLastEvent()` (ou expandir em `HandlerMethod.toString()`); tratar `!isOutermost` no fail-closed |
| A7 | 10.1 / S-seed:39: `AndroidCipherTransformationUtil.java` não existe em `7e7acb69` (criada em gh101, +262) — gate "idêntica a 7e7acb69" falha | tasks.md:172; S-seed.md:39 | Base = `pre-rename-head` também para essa classe |
| A8 | Maven e geração de monitores em paralelo na onda 1 (grupos 2,3,4,5,6 rodam `mvn` no mesmo reator/`~/.m2`; 2.14, 3.0/3.5/3.8, 6.6/6.10 geram monitores; EV:7 diz "never in parallel") sem lock | tasks.md header; EV-validation.md:7 | Lock/ordem explícita para `mvn install`, rebuild de `lib/` e geração |
| A9 | D-8 / 5.7 afirmam que `step_bundle.py` tem parser próprio — falso: `:286` já usa `violations.read_logcat`; `test_step_bundle.py` já existe (422 l.); a tarefa continua necessária porque `read_logcat → (events, diagnostics)` quebra `:286` (5.6 e 5.7 no mesmo commit) | design.md D-8; tasks.md:115,118 | Reescrever motivo; "atualizar", não "novo" |
| A10 | Verificação `rg "RVSEC :"` da 5.9 não alcança `violations_detail.py`, `mop_diff.py`, `consolidate_gov.py` (escrevem `RVSEC   :`/`\s+`) e omite `scripts/consolida_comparacao_aperv.py`, `experimento-20260721/scripts/consolidate_compare.py`, `aperv_tool/analysis/loader.py`, `tests/domain/test_log.py`; `rg` não está instalado; `execution_status.py` fica na raiz de `A/` (untracked), não em `domain/` | tasks.md:117 | Padrão `RVSEC\s*:`; adicionar hits; instalar `rg` ou `grep -rE` |
| A11 | D-9 residual: design.md:75 e :201 ainda dizem que o baseline usa/importa `read_errors_csv` (contradiz D-9, 1.1, proposal:36) | design.md:75,201 | Reescrever |
| A12 | 4.2 `EmitResult` toca 29 call sites de teste (`WrapperEmitterTest` 25, `WrapperMergeTest` 3, `EmissionParityTest` 1) — "green by construction" não vale; `trailingRest`/`headCount` são locais privados de `matchArgs`, não helpers | tasks.md:100,102; E2:… | Explicitar; reimplementar 3 linhas |
| A13 | Cenário `advicesExcludedByArity MUST be 1` (spec instr.:343) só vale para descritor sintético; no congelado a previsão é 10 pares / 4 advices — e a unidade diverge (tasks 4.1 "pares" vs design:295 "advices") | specs/instrumentation:343; design.md:295 | Fixar unidade e escopo do cenário |
| A14 | Ambiente: JDK padrão 25 (reator quer 21: `sdk use java 21.0.12-tem` por shell); `TMPDIR` vazio e `/tmp` é tmpfs (grupos 2,3,6,7 exigem fora do tmpfs) | — | Exportar no brief de dispatch |

## MÉDIA

- Ordenação: E1∥E4 por arquivo (D-2 ii, design:140,342) vs "8 após 6 e 7 completos" (tasks:30); Grupo 7 depende também de 6.4/6.5/6.7/6.8/6.9 (7.6, 7.7) — cabeçalho diz "após 2 e 3"; E6 "device-side and last" (D-5) vs grupo 9 antes do 10; 9.1 pode depender do logcat de 10.4.
- Diffs admissíveis na regeneração: design:163,343,365 dizem "tabela + macro"; 3.8/D-14 acrescentam o framing do lock — um `--expect` da 1ª lista falha após 3.7.
- Sete vs nove divergências herdadas (design:132,349 vs tasks 8.11/8.12 (a)–(i)).
- D-6 (design:179): `IvParameterSpecSpec_c1/c2` não são os sítios 3-arg (são `c3/c4`, apagados no S).
- OAEP "behavioural" (proposal:26, design:213) sem tarefa.
- "3 `setProperty` deletions" (tasks 2.11, spec instr.:204) não corresponde a nada: 49 sítios no `jca`, 46 nos 21 que ficam, em 19 arquivos.
- "case-sensitive em 6" são 8 (KeyStore, KPG) — tasks 2.5 / D-10.
- 2.14: regra "anything else stops" não prevê `introduced` dos 10 guardas recuperados; "corrected verdict" não é classe do harness (`unchanged/moved/removed/introduced`).
- "30 clauses" fixo em S-seed.md:130,251 e tasks:71 vs provisório em 2.15 (reconstrução deu 65).
- Requisitos de delta sem tarefa: `\n` restaurado pelo parser (instr.:372-376) ausente de 5.3; `CsvDiagnostics.unique_msg_disagrees` (campaign-analysis) ausente de 5.6; `ParserDiagnostics` no `CoverageTracker` (analysis:21,35,53,125) ausente de 5.3.
- Tipo dos campos de envelope: `str | None` (E3, design API) vs `str` com `""`/`UNSPECIFIED` (deltas analysis/core).
- Ordem 5.4 antes de 5.3: `RvErrorLog` com `code/event` sem default quebra o parser (6 posicionais em `logcat_parser.py:309-316,341-350,366-368`).
- Gate grep do E3 (`':::'`) não detecta as f-strings `:::{` de `result_processor.py:631,999,1038` / `regenerate_container.py:244`; usar `:::{`. `regenerate_container.py:246` escreve 10 colunas (mais um layout para a matriz).
- 3.9: monitor do agente JSE é gitignored (`rvsec-agent/src/main/java/mop/.gitignore`) — não há "committed sources" para diffar; controle `jca` também não é versionado nem tem manifesto sha256.
- 3.0: caminho do manifesto sha256 e interface `--set` para diretório indefinidos; raiz de `evidence/` e `traces/` indefinida (4 grupos criam em paralelo).
- Rótulo "five-field" das 6.344 identidades: é a 8-tupla `(apk,rep,tool,spec,class,method,source,message)`; a 5-tupla de `ErrorSummary` dá 409.
- 7.3 ainda pede editar `SecretKeySpecSpec:49` que E1:70 diz ter sumido.
- Ids de decisão inexistentes: `D-a`, `D-b`, `D-c`, `D-30` (só existem D-1..D-14). `INV-INS-108` só existe no delta da gh100 (ativa, não sincronizada).
- Hint de dispatch aponta coletores em `rvsec-core/eh/`; estão em `rvsec-android/rvsec-logger-{logcat,csv}`. `scripts/gh104_*`, `tests/parity/`, `data/gh104/` são partilhados por vários grupos (nomes disjuntos, mas o hint atribui diretórios inteiros).
- `rvsec-mop/pom.xml` mínimo, sem junit — 6.9 exige adicionar dependências (a tarefa prevê; padrão em `rvsec-core/pom.xml:23-29`).
- 4.3 é só teste: `_parse_results_json:612-616` já copia o dict `weaveCounts` inteiro. `ResultsJsonReportingTest` não exercita `BatchRunner:199-201` (só serialização).

## BAIXA (editorial)

Nomes de teste/arquivo design≠tasks (`test_gh104_structural_gates.py`, `test_jca_android_has_no_execution_context`, `test_baseline_reproduces_byte_identical`, `gh104_mop_lint.py`/`gh104_message_gate.py`); numeração 10.8 antes de 10.7, "8.x"→8.1; 35 vs 31 `after` sem `args()`; 158 vs 114 linhas da alias table (classe Java = 158 ou 114?); "141 pointcuts on 135 lines" (são 137 linhas; 135 é `grep -c "call("`); linhas do monitor congelado deslocadas em ≤1 (`:5263`→`:5266`, `:8372-8373`→`:8375-8376`, `:12802/13302/13334/15919` +1); `ErrorCollector` logcat `:39`/`:44-51`; `createErrorSummary` é `:89-106` (não 216-233); `hashCodeMatchesEquals :179-194`; `test_near_miss` `:134`; `__main__.py:1193` não tem "derived"; `args(alg, provider)`→`args(alg, *)`; título antigo do requisito de aridade e `INV-INS-127` citado onde é `INV-INS-122`; exemplar atômico de aceitação: `TrustManagerFactorySpec` é não-atômica (usar `CipherSpec`/`SecretKeySpecSpec`); KeyStore "lacks (String,String)" vale para o `.mop`, não para o android-30; 9 linhas da alias table são de serviços sem spec (`AlgorithmParameters`, `SecretKeyFactory`); `WrapperMergeTest` só no E2 file; `SecureRandomSpec:82` só no E1 file; `constants.py:90-95` só no S file; `.aj` "travels with the set" decidido na execução sem registro em D-1/Open Questions.

## Confirmações relevantes (sem ação)

Todos os insumos existem: controle congelado gh101 (monitor, descritor, `MonitorWrappers.java`, 4 APKs), 8 shards comp162, dataset do artigo (26 MB), relatório OWASP, `backup/gh104-analise/*`, MetaCrySL api30 (árvore limpa), `RVSEC_HOME`, `ANDROID_HOME/android-30`, uv, openspec 1.7.0, 5 skills. gh100 não arquivada mas 57/57 tarefas fechadas; o código que E2 pressupõe está commitado — sem dependência oculta. `javamop.jj:1440` / `aspectj.jj:49` confirmados. Getters públicos no android-30 confirmados por `javap`. G-2 (18) e G-ERE (1) reproduzidos.
