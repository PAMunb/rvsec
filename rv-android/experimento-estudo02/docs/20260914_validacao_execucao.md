# Validação da `estudo02` — execução dos detectores e correções ao handoff

**Data:** 14/09/2026 · **Estado da campanha:** encerrada, 16 137/16 137 identidades `COMPLETED`
**Plano executado:** `20260912_validacao_anomalias.md` (detectores G*, Z*, I*, E*, L*), naquilo
que roda sem as tabelas que a exportação não escreveu.
**Scripts:** `experimento-estudo02/scripts/validacao/` (README com a ordem exata de execução).

## Veredito em três linhas

1. **A medição está íntegra.** Grade completa, nenhuma identidade duplicada, nenhuma spec fora do
   alfabeto, nenhum sinal de perda de linha no logcat, cobertura ao vivo igual à reconstruída
   nas 5 079 identidades em que as duas existem.
2. **A consolidação, como está, produziria número errado.** Não pelo defeito F1 do handoff
   (0,067 % das linhas) e sim porque `consolidate_compare.py` não encontra o logcat de **seis dos
   onze braços** (8 802 identidades) e os descarta do pareamento e do Wilcoxon.
3. **Três premissas do handoff não sobrevivem à fonte:** o exemplo-âncora da "parada natural da
   ferramenta" é um crash determinístico do `ares`; a inflação de `mop_unique` vem de
   `error_type`+`message`, não do envelope v1; e o corpus não é o do artigo, difere em um app.

---

## Parte I — O que o handoff afirmava e o que a fonte mostra

| # | Handoff | Fonte | Consequência |
|---|---|---|---|
| H1 | F1: a regex de `mop_total` perde `IvChainJunction`, `MGF1ParameterSpecSpec` e `X509EncodedKeySpecSpec`, "concentrado nos APKs mais criptográficos" | `IvChainJunction.mop` emite o literal `IvChainJunctionSpec` (casa). `MGF1ParameterSpecSpec`: **0** linhas no corpus. Só `X509EncodedKeySpecSpec` é perdida: **93 de 139 657 linhas (0,067 %)**, 2 APKs, 81 identidades, no máximo 5,7 % do `mop_total` de uma identidade | F1 é real e desprezível. Corrigir a regex é higiene, não decisão de artigo |
| H2 | O consolidador "lê `tasks.json` + logcats direto" | `consolidate_compare.py:73-82` monta o nome do logcat como `<tool>:<variant>`; os braços com `variant='default'` gravam `…__monkey.logcat`. `FileNotFoundError` é engolido → `mop_total=0` em **8 802 identidades** (monkey, ares, droidmate, fastbot, humanoid, qtesting). O rótulo `monkey:default` não bate com o meta e a linha 109 **derruba os seis braços** de `per_apk_paired`, `per_tool_summary` e `wilcoxon` | Nada foi consolidado ainda (`estudo02_consolidado/` não existe). Rodar como está produz 5 braços em vez de 11. O registro já traz `result.logcat_file` com o caminho certo |
| H3 | F2: `code`/`event` do envelope v1 são o que separa a chave de 7 partes da de 4; "não se conserta com código" | Recontagem das 139 657 linhas: **k5 = k7 em todas as 16 137 identidades** — `code`/`event` não subdividem nada que `error_type`+`message` já não subdividissem. k7/k4 = **2,42** (estável por braço, 2,35–2,51). A chave de 4 é reconstruível dos campos 1, 2 e 4 da linha `RVSEC` | O I5 é implementável no consolidador: coluna `mop_unique4` ao lado de `mop_unique`. O contraste não é `jca × jca_android` dentro da campanha (só há `jca_android` nela): é estudo02 (7 partes) × artigo (4) |
| H4 | "Exatamente o mesmo desenho" do artigo | Corpus: **162 em comum**. `info.dvkr.screenstream_44000` saiu (falha do instrumentador no funil `jca_android`, `rvsec-dataset/jca_android/FUNIL.md:90`), `com.shatteredpixel.shatteredpixeldungeon_896` entrou. A saída do screenstream não está registrada na campanha. `monkey` roda com `ignore_crashes=true,ignore_timeouts=true` (commit `f34cb120`); o artigo rodou sem os flags (`docker-compose.gcp.yml:37`), e o monkey é a referência do modelo NB | Duas diferenças de protocolo a declarar na tese. Nenhuma invalida a campanha |
| H5 | A exportação estoura memória porque as caches sobrevivem "de um escritor para o outro" | `docker logs`: a morte ocorre **dentro do primeiro escritor** (`_generate_coverage_csv`); nenhum container chegou a `errors.csv`. Nas 10 últimas tentativas, o kill vem quando a soma de métodos parseados atinge 2,8–4,7 M, com 179–726 tasks — o limite é proporcional a objetos-método retidos por task (`static_data` memoizado **por task**, não por APK, `result_processor.py:331-361`) | Soltar `task.repository` depois do último escritor não bastaria. Já existe extrator por execução: `scripts/regenerate_results/regenerate_container.py` (pool, cache de estático por APK). Faltam-lhe `app_events.csv`, 3 colunas de alcançabilidade em `coverage`, `source/code/event` em `errors` e o `time` a partir de `tool_execution_start` |
| H6 | 151 das 172 abaixo do piso "acompanham as irmãs" = ferramenta esgotou a estratégia; exemplo `goodtime_348`/ares 92/90/93 s | O traço das nove réplicas do goodtime termina em `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` (`__main__:main:213`) e `Too Many Times tried`; tempo de ferramenta 43–51 s **nos três orçamentos**. É crash determinístico do `ares`, não parada natural. **66/66** C2 do ares carregam o marcador; **101/101** C2 do droidbot naive terminam em `The app cannot be started` + `DroidBot Stopped` | O oráculo das irmãs não distingue crash reproduzível de exploração esgotada. A divisão 151/21 não se reproduz com nenhuma regra declarada (varredura de tolerância: 140/32 a 152/20) |
| H7 | C2 = decorrido < orçamento − 45 s | `execution_time_seconds` é `end − start` da **tarefa**: inclui boot, instalação e teardown, sobrecarga mediana **53 s** (mín. 38). O piso de 60 − 45 = 15 s é **inalcançável**: as 0 reprovações em 60 s são vácuo, não saúde. O registro guarda `tool_execution_start`; medido por `end − tool_execution_start`, ficam abaixo do piso 103 identidades em 180 s (não 46) e 149 em 300 s (não 126) | O C2 precisa ser redefinido sobre o tempo da ferramenta antes de qualquer isenção |
| H8 | Detectores I2, I5, L4, L5 leem "registros persistidos" | O `result` do `tasks.json` tem só `coverage_metrics` (5 números), `detected_errors_count`, tempos e caminhos. Não há lista de violações, `unique_msg`, `truncated` nem contadores do parser em lugar nenhum | Os quatro detectores só existem via reprocessamento do logcat (feito abaixo para I2 e I5; L4/L5 exigem exportar os contadores no regenerador) |
| H9 | `crashes` vem de `detected_errors_count` | `detected_errors_count = 0` nas 16 137. O logcat tem `FATAL EXCEPTION` em **521** identidades (85/192/244 por orçamento) e `ANR in` em 1 066/1 467 do monkey | Coluna zero por construção (V9). Z4 acusaria; o contador real só existe no logcat |
| H10 | Catálogo de 2025 em `../rvsec-regerar-resultados` | O caminho correto a partir de `rv-android` é `../../rvsec-regerar-resultados` | Só corrigir a referência |

Três portões que o handoff afirmava e que **confirmam**: F3 (nenhum `codePackage` sob prefixo
excluído, 163 estáticos idênticos ao dataset, zero `.refused`); os 19 APKs do zero estrutural do
`qtesting` (mesma lista, nome a nome, do `summary.csv` do artigo); os commits `b2c80574`,
`6bc71179`, `e838cfd5` no branch `modules`, sem nada pendente nos caminhos da campanha.

---

## Parte II — Detectores executados

Contagem sempre por identidade `(apk, braço, rep, orçamento)`, melhor registro (`COMPLETED` de
`end_time` mais recente). 16 646 registros, 16 137 identidades, 509 registros `ERROR` superados pelo
resume (385 identidades com mais de um registro).

| Detector | Invariante | Resultado | Veredito |
|---|---|---|---|
| **G1** | 163 × 11 × 3 × 3 = 16 137; 3 reps por célula | 16 137 identidades; 5 379 células, todas com 3 reps; 11 braços; {60,180,300} | PASSA |
| **G2** | nenhuma identidade com dois `COMPLETED` | 0 | PASSA |
| **C6** | observado = manifesto | 16 137 / 16 137 | PASSA |
| **E3** | nenhum `codePackage` sob prefixo do weaver (`PackageFilter.java:22-40`) | 0 de 163. 76 APKs com `package ≠ codePackage`, todos `codePackageSource=manifest-neutralized` (sufixo de build neutralizado pelo lado estático); `class_defs_under_key > 0` nos 163 | PASSA |
| **I4** (estático) | `x.replace('$','.')` sem colisão | 0 colisões em 163 modelos | PASSA |
| **Z3** (direto) | `mop_unique > 0 ⇒ linhas RVSEC > 0`; `mop_unique ≤ linhas` | 0 e 0 violações em 16 137 | PASSA |
| **I1** | contra-regex frouxa × regex do consolidador | 139 657 linhas; 93 perdidas (`X509EncodedKeySpecSpec`); 20 specs emitem, 27 nunca | F1 confirmado, desprezível |
| **I2** | spec observada ∈ alfabeto do `jca_android` | 20 observadas ⊂ 45 emissoras (2 dos 47 `.mop` não têm `ErrorDescription`) | PASSA |
| **I3** | nenhum campo classe/método com `(Arquivo:linha)` | 0 em 139 657 | PASSA. Métodos com `$` são lambdas Kotlin legítimas (`digest$…`, 7 530 linhas), não vazamento de frame |
| **I5** | chave de 4 × 7 partes | Σ por identidade: k4 = **27 061**, k5 = k7 = **65 392**, razão 2,42. Distintos `(apk, class, method, spec)` na campanha: **476** (artigo, `jca`: 454); por braço 245 (`qtesting`) a 400 (`monkey`) | Entregável; ver tabela abaixo |
| **R3** (alt.) | k7 recontado do logcat = `total_errors` do índice | 16 135 / 16 137; 2 diferem em 1 (qtesting@300, `traficparis` e `moememos`, 91 e 217 linhas) | PASSA com ressalva; conferir após regenerar `errors.csv` |
| **L2** | sem descarte do `logd`, sem rotação | `chatty`: 0 linhas. Cabeçalhos: 3 em 15 551 arquivos, 4 em 586 — o quarto é `beginning of crash`, buffer que abre no primeiro crash, não rotação | PASSA |
| **Carimbos** | inversões e virada de meia-noite | 1 930 arquivos com inversão (2 201 no total, máx. ~7 s), todas entre buffers (`kernel`/`system` × `main`). Restritas às linhas `RVSEC*` do app: **10 inversões em 9 arquivos, máx. 112 ms**. Meia-noite: 0. O parser fixa offset negativo em 0 (`_stamp_time`, `logcat_parser.py:102-107`); não descarta | PASSA. O defeito de 2025 (offset negativo → linha descartada) não existe aqui |
| **L1** | maior lacuna entre carimbos | p50/p90/p99/máx (s): 60 s → 6/10/17/30; 180 s → 20/38/60/85; 300 s → 33/80/150/203. 52 identidades em 300 s com lacuna > 150 s, sem `FATAL`/`ANR` em 50 delas, concentradas em droidbot (30) e ares (8) | Inconclusivo: lacuna silenciosa é ferramenta parada, não perda; separá-las exige o traço |
| **L3** | taxa de `RVSEC-COV`/s vs irmãs | 104 identidades abaixo de 25 % da mediana das irmãs; 89 sem nenhum marcador de crash | **Acusa demais** (lição de 2025). Sem valor sem oráculo externo |
| **C4** (direto) | ≥ 1 linha `RVSEC-COV` | 184 sem cobertura: 171 `qtesting` (estrutural) + 12 `droidmate` + 1 `fastbot` | Os 13 não estruturais são C4+C5 na admissibilidade |
| **H4** (matriz APK × braço) | cobertura zero nas 9 identidades da célula | 19 células, todas `qtesting`; nenhum APK zerado nas 11 configurações; 12 células parciais (11 droidmate, 1 fastbot) | Critério do artigo não exclui ninguém |
| **A1** (`admissibility.py`, varredura completa, 16 min) | C1–C6 por identidade | admissíveis **15 737**; zero estrutural **171** (19 APKs); inadmissíveis **229**: C2 172, C4 13, C5 61 (4 sobrepostas C2+C5). 38 APKs com célula sem réplica admissível (9 só pelo estrutural), **nenhum excluído** | Ver Parte III |
| **L6** (parcial) | ao vivo × offline | `cov_method` da última linha de cada identidade no `coverage.csv` parcial = `coverage_metrics.method_coverage` em **5 079/5 079** identidades completas; as 9 divergentes são a última identidade de cada arquivo, cortada pelo OOM | PASSA no que existe |
| G3, Z4, R1, R2, R3, E1, E2 | — | Rodados sobre as tabelas regeradas; ver a subseção seguinte | 5 PASSAM; R2 e E2 acusam e caem no confronto com a fonte |
| L4, L5, M1, M2 | — | Não executáveis: L4/L5 dependem de contadores do parser que ninguém persiste; M1/M2 são especificação do modelo | Passo 3 (modelo) |

### Detectores sobre as tabelas regeradas (G3, Z4, R1, R2, R3, E1, E2)

Rodados em 14/09, depois da regeração, sobre `data/results/estudo02_consolidado/` e
`data/results/estudo02_regen/estudo02_NN/`. Scripts: `scripts/validacao/tabelas.py` (G3, Z4, R1,
R2, R3, E2) e `scripts/validacao/e1_unmatched.py` (E1). **Limiares fixados antes da execução**
(este parágrafo foi escrito antes de o primeiro script rodar e não foi mexido depois):

| Detector | Limiar declarado | Acusa quando |
|---|---|---|
| **G3** | variação zero | algum APK tem mais de um par `(classes_total, methods_total)` nas suas linhas de `summary.csv`, ou não tem exatamente 99 linhas. Secundário: `methods_total` = `sa_methods` de `per_apk_static.csv` |
| **Z4** | ≥ 2 valores distintos | alguma métrica de `per_task.csv` (`cov_method`, `cov_act`, `cov_mop`, `mop_unique`, `mop_total`, `mop_unique4`, `crashes`, `anrs`, `tool_seconds`) ou coluna numérica de `summary.csv` é constante no total ou dentro de um dos 11 braços. Nenhuma exceção declarada de antemão: toda coluna constante é confrontada com a fonte |
| **R1** | \|diferença\| ≤ 5·10⁻⁵ | a média por `(apk, orçamento, braço)` recalculada de `per_task.csv` difere da célula de `per_apk_paired.csv` além do arredondamento a 4 casas; ou alguma célula tem n ≠ 3 ou valor vazio. Esperado: 5 379 células × 8 métricas |
| **R2** | `n_apks = 163`; \|diferença\| ≤ 5·10⁻⁴ | alguma das 33 linhas de `per_tool_summary.csv` tem `n_apks ≠ 163`, ou média/mediana recalculada de `per_apk_paired.csv` difere além do arredondamento a 3 casas |
| **R3** | exatamente as 2 conhecidas | por identidade, `\|{unique_msg}\|` de `errors.csv` ≠ `mop_unique` de `per_task.csv` fora de `traficparis` e `moememos` (qtesting@300, diferença 1). Secundários, tolerância zero: nº de linhas de `errors.csv` por identidade = `mop_errors_total` de `summary.csv` = `mop_total` de `per_task.csv` |
| **E1** | ≥ 99 % dos eventos | (a) a recontagem com gancho no `LogcatRepository` difere de `unmatched_in_scope`/`unmatched_out_of_scope` de `summary.csv` em alguma identidade (tolerância zero: valida o gancho); (b) menos de 99 % dos eventos `unmatched_in_scope` da campanha caem em classe gerada — nome simples `R`, `R$*`, `BuildConfig`, `Manifest`, `Manifest$*`, ou último segmento `$Log`. Todo APK com evento não explicado é listado e confrontado com o `.apk.json`. A estabilidade entre as 99 identidades se lê como propriedade do **conjunto** de `(classe, assinatura)` não casadas, não da contagem, que escala com a atividade da ferramenta |
| **E2** | `cov_method < 1,0` e `unmatched_out_of_scope ≥ 100` e `measured = true` | existe identidade nessas três condições. Esperado: zero |

**Resultados** (limiares acima, sem ajuste depois de ver o dado):

| Detector | Resultado | Veredito |
|---|---|---|
| **G3** | 163 APKs, 99 linhas cada, um único par `(classes_total, methods_total)` por APK; `methods_total = sa_methods` nos 163 | PASSA |
| **Z4** | nenhuma coluna constante, nem no total nem dentro de braço, em `per_task.csv` (9 métricas) e `summary.csv` (12 colunas numéricas). `crashes` e `anrs` variam nos 11 braços | PASSA |
| **R1** | 489 unidades × 11 braços = 5 379 células, todas com 3 réplicas; 43 032 valores; maior diferença 5,0·10⁻⁵ (o próprio arredondamento) | PASSA |
| **R2** | `n_apks = 163` nas 33 linhas. **Acusou 4 medianas** de `cov_method` (`ares`@60, `humanoid`@180, `monkey`@300, `ape`@300) com diferença 5,0·10⁻⁴, na borda do limiar | **Falso positivo do detector**: recalculadas das médias sem arredondar de `per_task.csv` (a entrada real do consolidador), as 4 batem na terceira casa. O desvio vem de arredondar duas vezes (4 casas em `per_apk_paired`, 3 em `per_tool_summary`), e o limiar declarado não previa a soma das duas folgas |
| **R3** | 16 135 iguais; as 2 conhecidas (`traficparis`, `moememos`, qtesting@300) diferem em 1; nenhuma identidade só no `errors.csv`. Secundário: linhas de `errors.csv` por identidade = `mop_errors_total` = `mop_total` nas 16 137 (Σ 139 657 nos três) | PASSA |
| **E1** | (a) recontagem com gancho = `summary.csv` nas 16 137 identidades, `unmatched_unclassified = 0` (a chave de escopo chegou a todo artefato). (b) **15 686 eventos in-scope, 100 % em classe gerada**: `BuildConfig` 12 856 e `R$*` 2 830, todos `class_absent`, em 80 APKs e 6 767 identidades, 1 a 4 assinaturas distintas por APK. (c) nenhum APK com evento não explicado. O conjunto é propriedade do artefato, não da ferramenta: 61 dos 80 APKs o exibem nos 11 braços, os 19 restantes em 1 a 10 | PASSA. Não há buraco de denominador na campanha |
| **E2** | **Acusou 69 identidades**, em três APKs: `org.wikipedia_50595` (45: as 9 de cada braço da família droidbot — quatro estratégias e `humanoid`), `cc.sovellus.vrcaa_300007` (23) e `com.shatteredpixel.shatteredpixeldungeon_896` (1, `bfs_naive` rep3@60, 0,61 contra 1,35 das irmãs) | **A chave de escopo não está errada em nenhuma**; ver o confronto abaixo. O detector achou outra coisa, e ela muda o passo 2 |

**Confronto do E2 com a fonte.**

- `cc.sovellus.vrcaa_300007`: `codePackage = cc.sovellus.vrcaa`, 2 360 de 2 360 classes do modelo sob a
  chave. A cobertura de métodos é baixa em **todos** os braços (máximo 2,07 %, `cov_act` 40 % em
  todas as 99), e os eventos fora do escopo são biblioteca (`cafe.adriel.voyager` 6 258,
  `okhttp3` 1 320, `leakcanary` ~950 no logcat de `qtesting` rep1@180). É propriedade do app
  (Compose, navegação em biblioteca), e o limiar de 1 % cortou uma distribuição que vive entre
  0,7 e 2 %.
- `org.wikipedia_50595`: `codePackage = org.wikipedia`, 8 088 classes sob a chave, e os braços que
  não são da família droidbot cobrem 4–19 % dos métodos. Nas 45 identidades da família droidbot,
  `cov_act = 0` e `cov_method ≈ 0,89`. O traço diz por quê: **`INFO:Device:Main activity:
  leakcanary.internal.activity.LeakLauncherActivity`**, nas 45. O build é de depuração e traz o
  `activity-alias` de lançamento do LeakCanary; o androguard do DroidBot devolve esse alias como
  atividade principal, e as quatro estratégias e o `humanoid` exploraram a interface do LeakCanary
  (`LeakLauncherActivity/TextView-Leaks` no traço), não a Wikipedia. O app principal é um
  `activity-alias` para `org.wikipedia.main.MainActivity`, e por isso o `mainActivity` do modelo
  estático é vazio e o app está entre os 19 do zero estrutural do `qtesting`. **O artigo tem o
  mesmo padrão**: `ase-journal/dataset/results/summary.csv` registra `cov_act = 0` nas 45
  identidades da Wikipedia sob a família droidbot. É zero determinístico da ferramenta, do mesmo
  tipo do `qtesting`: repetir reproduz. Varredura dos 7 335 traços da família (`Main activity:`
  contra `codePackage`/`package` do `.apk.json`): a Wikipedia é o **único** APK lançado por
  atividade de fora do app; nos outros 162 a atividade é do próprio app (12 traços do `gotify`
  são binários para o `grep` e não imprimem a linha, sem relação com o lançamento).

**Consequência para o passo 2.** A admissibilidade classifica essas 45 identidades como C5
(6 delas, `dfs_naive`@180/300, também como parada da ferramenta), e o `repair.py` as trata como
reparáveis: das **96** identidades que o dry-run sobre os dez containers devolveria à fila, **39
são da Wikipedia sob a família droidbot** e voltariam com o mesmo zero. As outras 57: C2 42,
C4+C5 11, C5 3, C2+C4+C5 1; mais 1 `REVISAR` (`gotify`/fastbot rep1@60, C2+C4+C5 após duas
tentativas).

**I5 por braço e orçamento** (Σ das chaves por identidade; `k4` é o que o artigo chama
`mop_errors_unique`, `k7` é o `mop_unique` da campanha):

| braço | 60 s k4 / k7 | 180 s k4 / k7 | 300 s k4 / k7 |
|---|---|---|---|
| ape | 815 / 1 986 | 991 / 2 347 | 1 057 / 2 524 |
| ares | 727 / 1 765 | 870 / 2 095 | 902 / 2 174 |
| droidbot:bfs_greedy | 657 / 1 622 | 907 / 2 129 | 960 / 2 284 |
| droidbot:bfs_naive | 647 / 1 579 | 766 / 1 872 | 805 / 1 973 |
| droidbot:dfs_greedy | 722 / 1 739 | 902 / 2 118 | 942 / 2 220 |
| droidbot:dfs_naive | 666 / 1 590 | 774 / 1 885 | 790 / 1 928 |
| droidmate | 772 / 1 849 | 857 / 2 068 | 907 / 2 182 |
| fastbot | 745 / 1 817 | 796 / 1 935 | 894 / 2 140 |
| humanoid | 698 / 1 725 | 807 / 1 998 | 914 / 2 171 |
| monkey | 780 / 1 931 | 960 / 2 296 | 1 001 / 2 387 |
| qtesting | 620 / 1 539 | 704 / 1 768 | 706 / 1 756 |

Por identidade: `i5_per_identity.csv` (colunas `apk, arm, rep, timeout, lines, k4, k5, k7,
mop_unique_tasks`) fica no diretório de trabalho da validação; é a coluna `mop_unique4` que o
consolidador deve passar a escrever.

---

## Parte III — C2: as 172 e a decisão pendente

Distribuição: 300 s → 126, 180 s → 46, 60 s → 0 (vácuo, ver H7). Por braço: `dfs_naive` 77,
`ares` 66, `bfs_naive` 24, `qtesting` 4, `droidmate` 1. Todas saíram com código 0 e
`error_message` vazio (código ≠ 0 já vira `ERROR`/C1).

O que o traço diz, censo completo:

| braço | C2 | marcador no traço | leitura |
|---|---|---|---|
| ares | 66 | 66/66 `Too Many Times tried` + `| ERROR`; 42 `TypeError(main:213)`, 6 `cannot unpack non-iterable NoneType`, 6 traceback netty | 42 são crash determinístico da ferramenta (reproduz nas 3 réplicas e nos 3 orçamentos); os demais, falha não determinística (irmãs exploraram até o fim, ex. `mtgfam` rep1@300: 63 s de ferramenta contra 318/312) |
| droidbot naive | 101 | 101/101 `stop sending events: The app cannot be started.` + `DroidBot Stopped` | a política desiste após 5 reinícios do app; 113 identidades admissíveis terminam igual, só que depois do piso |
| droidmate | 1 | exceção em `AdbWrapper.forwardPort` | infraestrutura; candidata legítima à fila |
| qtesting | 4 | `the state is added into Q-table mistakenly`, traço com 72–113 linhas (mediana 579) | saída silenciosa da ferramenta |

E 36 identidades **admissíveis** do ares carregam o mesmo `Too Many Times tried` — 35 em 60 s,
onde o crash cabe dentro do piso frouxo, e 1 em 180 s cravada no piso (135 = 135).

**Recomendação para a decisão (não editei nada):** a isenção proposta no handoff ("acompanha as
duas irmãs") classificaria 40 crashes determinísticos do ares como parada natural e devolveria à
fila ~30 identidades que vão parar no mesmo ponto. O oráculo que separa está todo no disco:
(a) marcador de erro no traço, por ferramenta; (b) tempo **da ferramenta**
(`end_time − tool_execution_start`) em vez do da tarefa; (c) invariância desse tempo entre os
três orçamentos do mesmo `(apk, braço, rep)`; (d) `FATAL EXCEPTION`/`ANR in`/`has died` no
logcat para separar app de emulador. Sob esse oráculo, "parada da ferramenta" (crash ou
desistência) é categoria própria, ao lado do zero estrutural: fica na análise como o artigo
manteve os zeros do `qtesting`, não volta à fila, e a tese a declara. Só voltam à fila as falhas
de infraestrutura (o `droidmate`) e as não determinísticas em que as irmãs mostram que a
exploração era possível.

---

## Parte IV — Decisões tomadas e executadas em 14/09

1. **Consolidador corrigido** (`.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py`):
   lê `result.logcat_file`; colapsa `variant='default'`; regex aceita dígitos; logcat ausente
   aborta em vez de virar zero; novas colunas `mop_unique4`, `crashes` (`FATAL EXCEPTION` no
   logcat), `anrs`, `tool_seconds`, `sa_methods`, `sa_methods_reaches_mop`; `--admissibility`
   traz `category`/`admissible`/`fails` como colunas, sem filtrar a agregação; `per_apk_static.csv`
   com a covariável do modelo NB. Rodado: 16 137 identidades, 11 braços, 489 unidades pareadas.
   Conferido contra a Parte II: Σ `mop_total` = 139 657, Σ `mop_unique4` = 27 061, 521
   identidades com crash, 299 abaixo do piso.
2. **C2 redefinido** em `admissibility.py`: tempo da ferramenta (`end_time − tool_execution_start`)
   contra `orçamento − 5 s`, porque a distribuição é bimodal (normal = orçamento + ~10 s; vazio
   entre 55–65, 170–190 e 290–310 s). Nova categoria **parada da ferramenta**: abaixo do piso,
   com marcador da ferramenta no traço (`Too Many Times tried`, `The app cannot be started`,
   `Q-table mistakenly`), nas três réplicas da célula. Não volta à fila; `repair.py` a trata
   como o zero estrutural. Primeira varredura, só com essas duas categorias: 15 614
   admissíveis, 171 estruturais, **255 paradas da ferramenta** (85 células, 37 APKs:
   `droidbot:dfs_naive` 144, `ares` 60, `droidbot:bfs_naive` 51), 103 inadmissíveis (C2 44 em
   células mistas, C4 13, C5 61). O dry-run do reparo devolveria 96 à fila, e 39 delas eram a
   Wikipedia sob a família droidbot (ver E2), o que levou à terceira categoria declarada,
   **lançamento fora do app** (traço com `Main activity:` fora do `package`/`codePackage`
   do `.apk.json`; não volta à fila). Com ela, antes do reparo: 15 614 admissíveis, 171
   estruturais, 249 paradas da ferramenta, 45 lançamentos fora do app, 58 inadmissíveis (C2 44,
   C4 13, C5 16); 57 reparáveis e 1 para revisar (`gotify`/fastbot rep1@60, já na segunda
   tentativa). **Depois do reparo (item 6)**: **15 650 admissíveis, 171 estruturais, 249
   paradas da ferramenta, 45 lançamentos fora do app, 22 inadmissíveis** (C2 21, C4 1, C5 2;
   `ares` 12, `droidbot:bfs_naive` 4, `droidbot:dfs_naive` 3, `monkey`, `fastbot` e `qtesting`
   1 cada). Veredictos em `docs/20260914_admissibilidade.json`. A Wikipedia deixa de ser
   candidata à exclusão "por outro motivo": suas 13 células sem réplica admissível (`bfs_greedy`,
   `bfs_naive`, `dfs_greedy` e `humanoid` nos três orçamentos, `dfs_naive`@60) são todas
   lançamento fora do app, e as outras duas de `dfs_naive` são parada da ferramenta. Nenhum APK
   excluído.
3. **Tabelas regeradas** por `scripts/regenerate_tables.py` (escritores do próprio
   `result_processor`, laço por identidade, estático cacheado por APK): 10 containers em
   paralelo, 5–11 min cada, RSS máximo 365 MB (contra os 10 GiB que o container estourou).
   Por container em `data/results/estudo02_regen/estudo02_NN/`; concatenadas em
   `data/results/estudo02_consolidado/{summary,errors,app_events,performance,coverage}.csv`
   (16 137 / 139 657 / 3 007 / 16 137 / 15 622 806 linhas). Cruzamentos: identidades de
   `summary.csv` = as do índice; `mop_errors_unique` = índice em 16 135 (nas 2 restantes, ambas
   `qtesting`@300 s, o índice diz 8 e o logcat gravado tem 7 chaves distintas: a oitava não
   existe no artefato); `cov_method` = índice em 16 120, e nas 17 restantes o offline é maior
   por 0,01–0,4 ponto, sempre para cima, com exatamente um método a mais que
   `total_method_calls` ao vivo (a última linha `RVSEC-COV` chegou ao arquivo depois do
   instantâneo). Em ambos os casos o arquivo é a fonte. Os diretórios dos containers são de
   `root`, por isso a saída foi para `estudo02_regen/`. Contra o `coverage.csv` parcial ao vivo:
   conjunto de (tempo, assinatura) e valores finais idênticos nas 99 identidades conferidas; só
   a ordem intra-segundo difere (hash seed). Com isso G3, Z4, R1, R2, E1, E2 e R3 passam a ser
   executáveis sobre as tabelas; L4/L5 continuam sem fonte (o regenerador não exporta os
   contadores do parser).
4. **Diferenças em relação ao artigo** registradas em `experimento-estudo02/README.md`
   (corpus 162 + 1, flags do monkey, orçamentos intercalados, imagem, diagnósticos, infra).
   Artigo e tese não foram tocados.
5. **Covariável** `sa_methods_reaches_mop` recomputada dos 163 `.apk.json` da campanha:
   mínimo 1, mediana 996, máximo 25 136, nenhum zero (o `log` do modelo está definido).

6. **Reparo executado.** Decisão do responsável: devolver à fila as 57 reparáveis, "salvar o
   máximo possível", sabendo que umas dez tinham cara de reproduzir. `repair.py --apply` dentro
   da imagem, como root; logcat e traço de cada uma preservados em
   `backup/estudo02-inadmissiveis/<container>/` antes da reescrita `COMPLETED → ERROR`. Os dez
   containers foram religados com `compose up -d` e, logo depois, `docker update --restart=no`:
   ao fim das tarefas cada um roda a exportação que estoura memória, e com `on-failure:20` seria
   religado vinte vezes à toa. Um vigia deu `docker stop` em cada container assim que todas as
   suas identidades ganharam registro novo. **Resultado: 36 das 57 se recuperaram, 21
   repetiram a falha.**

   | grupo | reparadas | recuperadas | repetiram |
   |---|---:|---:|---:|
   | `droidmate` sem cobertura (C4+C5) e `securecamera` (infraestrutura) | 12 | 12 | 0 |
   | `monkey`/`fastbot` C5 | 3 | 2 | 1 (`criticalmaps` monkey rep3@60, 70 s, C5 de novo) |
   | `qtesting` C2 | 5 | 4 | 1 (`faircode.email` rep1@300, 70 → 90 s, `Q-table mistakenly`) |
   | `droidbot` naive C2 | 12 | 5 | 7 (todas `The app cannot be started`) |
   | `ares` C2 | 25 | 13 | 12 (todas `Too Many Times tried`) |

   As que repetiram pararam como da primeira vez: o `ares` entre 38 e 67 s de ferramenta em
   qualquer orçamento, o `droidbot` naive entre 156 e 294 s com a mesma desistência. Duas delas
   receberam, por decisão do responsável, uma terceira tentativa (`repair.py --rerun`, que só
   toca identidades nomeadas e numera os artefatos de cada tentativa: `<nome>`, `<nome>.2`):
   `mtgfam`/ares rep1@300 parou aos 46 s com a mesma `StaleObjectException` na iteração 0, e
   `iyps`/bfs_naive rep2@300 aos 258 s com `The app cannot be started`, cobertura igual à das
   tentativas anteriores. Ficam inadmissíveis. O dry-run do `repair.py` depois do reparo lista
   as 22 como `REVISAR` e nenhuma como reparável: nada mais volta à fila sem decisão humana.

   Depois do reparo, as tabelas foram regeradas (dez containers, 11–25 min cada,
   `unresolved_static=0`, `write_errors=0`) e reconsolidadas: `summary.csv` 16 137 linhas,
   `errors.csv` 139 916 (eram 139 657), `app_events.csv` 2 996, `coverage.csv` 15 642 699;
   16 705 registros no índice. As métricas mudaram em 41 identidades, todas entre as
   reexecutadas; Σ `mop_unique4` 27 061 → 27 068, Σ `mop_total` 139 657 → 139 916, identidades
   abaixo do piso 299 → 276. Os detectores sobre as tabelas repetem o quadro anterior: G3, Z4,
   R1 e R3 passam (R3 com as mesmas 2 conhecidas; Σ `errors.csv` = Σ `mop_total` = 139 916), R2
   acusa as mesmas 4 medianas explicadas por arredondamento duplo, E2 acusa as mesmas 69
   identidades nos mesmos três APKs. E1 refeito nos dez containers: recontagem com gancho =
   `summary.csv` nas 16 137, e os 15 748 eventos in-scope (eram 15 686) caem 100 % em classe
   gerada.

Nada fica aberto na execução. O modelo e a comparação de specs sobre as tabelas finais estão em
`20260914_modelo_rq1.txt` e `20260914_specs_jca_vs_android.md`; a leitura, em
`20260914_veredito.md`.

## Fontes

- Consolidador: `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py` (35, 73-82, 109)
- Identidade: `modules/rv-android-core/src/rv_android_core/domain/log.py` (`unique_msg`, 119-160);
  `domain/coverage.py:743,795`; emissor Java `rvsec-logger-logcat/.../ErrorCollector.java:53-72`
- Exportação: `modules/rv-platform/src/rv_platform/components/result_processor.py` (245-250, 294-374, 525, 955)
- Parser: `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` (`_stamp_time` 102-107; 462-495; 582-615)
- Regenerador: `scripts/regenerate_results/regenerate_container.py`
- Artigo: `ase-journal/execution.tex:69-79`, `results-rq1.tex:15-16,249-265`, `data-analysis/rvsec/rq1_jca.py:185-228`
- Funil do corpus: `rvsec-dataset/jca_android/FUNIL.md:90,221`
