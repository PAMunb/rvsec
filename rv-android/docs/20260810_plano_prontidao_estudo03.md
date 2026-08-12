# Plano de prontidão — Estudo 03

**Data:** 2026-08-10
**Escopo:** deixar os artefatos prontos para a execução do experimento final (estudo 03).
**Fora do escopo:** a execução em si, seus parâmetros, e a escrita da tese.
**Branch de trabalho:** `modules` (não se cria branch nova).

---

## 1. Onde estamos e como chegamos aqui

O estudo 03 é o último experimento da tese. A linha dos três estudos é: (E1) mostrou que a
solução de RV é viável em bibliotecas Java; (E2) explorou RV em Android comparando oito
ferramentas de geração de teste em onze configurações, e concluiu que o gargalo é a cobertura
do código que toca a API JCA diretamente (média 8,04 %, pico 10,63 %); (E3) customiza o APE —
a melhor ferramenta do E2 — para guiar a exploração por operações monitoradas (MOP), e mede
se essa guia resolve o gargalo.

Entre 2026-08-06 e 2026-08-09 o projeto tomou um desvio: criou um conjunto de especificações
adaptado ao Android (`jca_android`, changes gh100 e gh101) e o submeteu a uma auditoria
adversarial de sete fases. O veredito foi **NOT READY, 22/22 specs REPROVADAS**. O conjunto
não é utilizável como está.

**A decisão que este plano executa: o estudo 03 usa o conjunto `jca`, o mesmo do estudo 02.**
`jca_android` não será corrigido nem usado.

Dois achados da auditoria continuam valendo e precisam ser carregados adiante:

- **34 dos 50 fenômenos com claim crítica (126 de 165 claims críticas, 76 %) têm proveniência
  `jca-inherited`.** Voltar para `jca` não escapa deles; herda quase todos. Só 3 fenômenos / 6
  claims críticas foram introduzidos pela gh101. A reprovação não é da gh101 — é da tradução
  CrySL↔JavaMOP como um todo, mais o toolchain.
- **O estudo 03 mede um contraste pareado entre braços de exploração sob o mesmo conjunto de
  specs.** Sob esse desenho, FP e FN sistemáticos dependentes de spec se cancelam em grande
  medida. Duas exceções não cancelam e precisam ser declaradas: `FEN-KPG-NPE` (crash dependente
  de trajetória — braços que alcançam mais o `KeyPairGenerator` crasham mais, enviesando
  *contra* o braço melhor) e o colapso de dedupe no collector (`ErrorDescription.equals` exclui
  `expecting` — braços que exercitam mais sítios são mais subcontados, comprimindo o delta).

Boa notícia colateral: o gate **G12** da auditoria (a análise estática resolve o diretório
literal `jca` porque `get_static_analysis_config` não passa `mop_dir` —
`modules/rv-experiment/src/rv_experiment/config.py:942-951` e
`modules/rv-static-analysis/src/rv_static_analysis/config.py:199-208`) é **fatal para
`jca_android` e inerte para `jca`**. Numa corrida `jca`, visão estática e dinâmica coincidem
por acidente. A volta ao `jca` neutraliza esse defeito sem esforço.

---

## 2. Decisões congeladas

| # | Decisão | Justificativa |
|---|---|---|
| D1 | Conjunto de specs: **`jca`** | `jca_android` REPROVADO 22/22; `jca` é o conjunto do E2 e está congelado desde `7e7acb69` |
| D2 | Corpus: **163** (base analisada do E2) | Única opção que fecha homogênea na chave de pacote sem trabalho adicional. CogniCrypt e testes unitários saem do escopo do E3 (ficam no E2), então o pareamento com os 219 deixa de ser necessário |
| D3 | Manter o **reparo do weaver** (gh100, `48b57fc5`) | O defeito era o weaver perder eventos; medir com ele quebrado não é opção |
| D4 | **Reverter `ExecutionContext.java`** (gh101, `233df18a`) para `efdd0541` | Mudança feita para o `jca_android`; o `jca` a herdou de carona sem passar pelo portão de congelamento (que só verifica os `.mop`). Das 27 leituras `condition(...)` do conjunto congelado, 8 mudam de resposta |
| D5 | Trabalho na branch **`modules`** | Sem branch nova |
| D6 | Análise estática e instrumentação **no host**, sem Docker | Rota já usada nas campanhas anteriores de SA; o CLI suporta `--skip-execution` |
| D7 | **Reanalisar os 30** com WTG e `codePackage=Mneut` | Único grupo cuja chave usada está errada para ambos os fins |
| D8 | **Não reanalisar os truncados** (36 dos 133 que entram no corpus; 45 nos 163 da Phase-7) | Eles já rodaram sob o código pós-gh66 e mesmo assim deram `transitions: []` — quatro deles já com 5400 s. O WTG é *timeout-bound* por laço quadrático, não por orçamento (§3.5) |
| D9 | **Reinstrumentar os 163** com o substrato congelado | Corpus meio-instrumentado com código velho é indetectável depois |
| D10 | **Sem pin do repositório Maven**; build único | Repositório local é `/home/pedro/desenvolvimento/repository` |
| D11 | **Diretório novo e auto-contido**, sem hardlink | Preserva os artefatos do E2 intactos e força a decisão explícita da fonte de cada JSON |
| D12 | **Piloto de instrumentação antes do lote** | Na Phase 8 um piloto de 10 APKs pegou o DEX-035, que teria comprometido 136 de 225 APKs |
| D13 | Resultados do E2 **serão reusados** na tese | Mecanismo analítico em aberto; não condiciona a prontidão |

### Consequência de D4 que precisa estar visível

Reverter `ExecutionContext.java` na `modules` **quebra a aresta `generatedCipher` do
`jca_android`**, que depende do store por identidade. Como `jca_android` está fora do
experimento, isso é aceito. A change gh101 continua aberta e deve registrar essa reversão
quando for retomada ou fechada.

### Consequência de D3 que precisa estar visível

O reparo do weaver muda o resultado do braço `jca` em relação ao E2, na direção de **mais
violações reportadas**. A evidência é o censo de
`openspec/changes/gh100-weaver-emission-fidelity/evidence/green_deltas.md:53-56`: **no nível do
descritor**, 9 eventos que o caminho inline descartava passam a ser emitidos — 8 deles emissores
de erro, 7 de `UnsatisfiedConstraint` e 1 de `UnsafeAlgorithm` — e os sítios de truncamento vão
de 3 para 0, com o descritor e o roteamento inalterados.

O efeito **por APK depende de quais sítios o APK contém**, e não é 9 em todo APK. Na sonda
`cryptoapp` (`:23-38`) só **2 dos 9** se manifestaram (`IvParameterSpecSpec_c3Event` ×4 e
`SecretKeySpecSpec_c3Event` ×5); os outros 7 não casaram sítio nenhum naquele APK.

Não confundir com o contador `wrappersGenerated`, que **caiu** de 96 para 84 (`:69`, `:86-90`):
são 12 wrappers duplicados que antes eram emitidos, registrados e imediatamente sobrescritos, e
agora são mesclados. `wrappersSubstituted` fica inalterado em 74 — nenhum sítio de chamada
ganhou ou perdeu wrapper. **Isso é neutro no comportamento observável e não é evidência de mais
violações.**

Vale ainda a ressalva do próprio documento (`:92-98`): V0 e V2 provam emissão e chegada no DEX
tecido, **não** chegada no logcat em tempo de execução — o braço de runtime da Layer 3 não rodou.

As contagens de violação do estudo 03 **não são comparáveis em valor absoluto** com as do estudo
02. Isto é proveniência do dado, não pendência.

---

## 3. Fatos medidos (base de evidência do plano)

Tudo abaixo foi medido nos artefatos em disco, não inferido de documentação.

### 3.1 O funil, reconstituído

```
3941 → 3553 → 1604 → 730 → 348 → 342 → 225 → 219 executados → 164 em escopo → 163 analisados
```

Fonte gerada por script: `ase-journal/data-analysis/stats/selection_funnel_stats.txt`. Lista
autoritativa: `ase-journal/dataset/dataset.csv` (`funnel_stage == 'selected'` → 163).

**O "165" não é estágio do funil.** É o arm alternativo *"M neutralizado (+flavor)"* em
`ase-journal/docs/20260730_relatorio_remocao_package_detector.md:196-197`, descartado em favor
do 164. O relatório registra que a escolha do denylist "não é load-bearing" (move 1 app).

### 3.2 A chave de pacote está homogênea

Regra canônica de neutralização
(`ase-journal/docs/20260730_relatorio_remocao_package_detector.md:202-207`): remover
repetidamente o último segmento pontuado quando pertencer a
`{debug, dev, beta, staging, qa, nightly, alpha, snapshot, current, head, indev}`, preservando
no mínimo 2 segmentos.

Comparando a chave efetivamente usada em cada rodada (linha `[RvsecAnalysisClient] Filter
package:` de `rvsec-dataset-sa/logs/*.log`, impressa por `RvsecAnalysisClient.java:107`) com o
`Mneut` recalculado:

| grupo | n | chave já correta | diverge |
|---|---:|---:|---:|
| `selected` | 163 | 133 | **30** |
| `filtered_zero_coverage` | 1 | 1 | 0 |
| **escopo do estudo (164)** | **164** | **134** | **30** |
| `filtered_denominator_scope` (os 55) | 55 | 15 | 40 |

Os 30 divergentes são **exatamente** os do `30_apks.csv`, sem sobra nem falta. Confirma a
afirmação da gh91 (`proposal.md:7-12`) por medição independente.

### 3.3 As divergências dos 30 e dos 55 têm naturezas opostas

| relação entre a chave usada e `Mneut` | os 30 | os 55 |
|---|---:|---:|
| iguais | 0 | 15 |
| a chave usada é **prefixo** de `Mneut` (detector foi raso demais) | **25** | **13** |
| `Mneut` é **prefixo** da chave usada (detector foi fundo demais) | **5** | 0 |
| **disjuntos — namespace diferente** | **0** | **27** |

A direção dominante é o detector ter parado **acima** do pacote do app: `de.markusfisch.android`
onde o correto é `de.markusfisch.android.binaryeye`. O caso oposto existe em 5 dos 30
(`net.osmtracker.activity` onde o correto é `net.osmtracker`). Confere com a coluna `relation`
do próprio `30_apks.csv` (`detected_prefix_of_Mneut` 25, `Mneut_prefix_of_detected` 5).

Os 30 são todos *prefix-related*: mesma família de namespace, o detector só errou a
profundidade. Aí `Mneut` é a correção certa.

Os 27 disjuntos dos 55 são forks e renomeações — `io.vespucci` vs `de.blau.android`,
`com.learntube.app.debug.HEAD` vs `org.schabi.newpipe`, doze `info.metadude.*.schedule` vs
`nerd.tuxmobil.fahrplan`. Para esses, `Mneut` é a chave **errada** e o detector é o certo:
filtrar por `io.vespucci` casaria zero classes. É por isso que colapsam o denominador e foram
cortados. **Reanalisá-los sob `Mneut` pioraria.** Registrado aqui porque explica por que o
corpus 219 exigiria uma campanha própria, e por que 163 é a escolha barata.

### 3.4 O WTG é o eixo de heterogeneidade dominante

A contagem abaixo é sobre os **JSON da Phase-7** (`rvsec-dataset/static_analysis/`), que é a
fonte de onde o passo 13 tira os 133 não-30. A classificação cruza `len(transitions)` do JSON
com `timed_out` do `_progress`.

| estado | os 163 | os 133 não-30 |
|---|---:|---:|
| `transitions > 0` | 117 | **96** |
| `== 0` por **timeout de WTG** (falha silenciosa) | **45** | **36** |
| `== 0` genuíno (`eu.faircode.email_2322`, `timed_out: false`) | 1 | 1 |
| **soma** | **163** | **133** |

Os 30 aparecem na coluna dos 163 com o resultado de junho (21 com WTG, 9 truncados), mas **não
entram no corpus de entrega por essa fonte** — para eles vale o resultado da Fase A. A partição
que a Fase C tem de fechar é, portanto, **96 / 36 / 1 dos 133, mais os 30 da Fase A**.

Nos 55 excluídos: mais 15 sem WTG, todos por timeout. Sobre os 219 seriam **60 em 218**
(27,5 %), ou 61 contando o único `filtered_zero_coverage`.

**Corroboração independente da contagem de timeouts.** Os 348 `_progress` registram 82
`timed_out: true`, e são **exatamente** os 82 logs em que a linha `...... target level:` não
aparece: o `print()` do launcher fica no buffer de stdout e morre junto com o `kill` do grupo de
processos. Os dois conjuntos coincidem sem diferença. Desses 82, **45 estão nos 163**.

**A falha é silenciosa e o sentinela não a detecta.** `RvsecAnalysisClient.java:169-170`
escreve o JSON com `wtg=null` **antes** de `WTGBuilder.build()` (`:189`); um kill durante o WTG
deixa `"transitions": []`. E `JsonReportWriter.java:111` emite `"complete": true`
**incondicionalmente** ao fim de toda escrita bem-sucedida — inclusive a pré-WTG. Verificado em
disco: `com.swordfish.lemuroid_252.apk.json` termina com `"transitions": [], "complete": true`
apesar de `timed_out: true`.

Isso **refuta** duas afirmações registradas no projeto:
1. o comentário em `RvsecAnalysisClient.java:157-164` ("the pre-WTG write does NOT emit the
   sentinel");
2. `docs/20260731_gh91_handoff_grupo5.md:126` ("Completeness = the `complete: true` sentinel,
   nothing else").

Pior: o portão do `aperv-tool` (`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py:249`)
só checa esse sentinela — JSON sem WTG passa calado.

**O marcador correto é `timed_out: true` no `_progress`**, não o `returncode`: o runner marca
`timed_out = True` e fixa `returncode = -1` no timeout
(`rvsec-dataset/src/rvsec_dataset/static_analysis/runner.py:231-233`).

### 3.5 Os truncados não são recuperáveis

A evidência mais forte é a própria Phase-7, e ela é direta: os 45 truncados **já rodaram sob o
código pós-gh66** — a otimização do laço (`4280f3bd`) entrou em 2026-06-17, nove dias antes da
varredura — e mesmo assim deram `transitions: []`. Quatro deles estouraram **já com 5400 s**
(`at.techbee.jtx`, `com.jerboa`, `eu.darken.sdmse`, `org.totschnig.myexpenses`); a maioria dos
demais, com 3600 s. Não é orçamento: é o laço quadrático.

Duas citações usadas antes neste plano precisam de qualificação, porque dizem menos do que
parecem:

- `docs/20260617_sweep_gh66_validacao_wtg.md:38` — *"B=3600s/8w/14g (yield ~nulo)"* é medição da
  **baseline, antes do gh66**. A própria linha `:36` classifica o Estágio B pós-gh66 como "o
  teste interessante", isto é, ainda não rodado quando o documento foi escrito. Serve como
  indício, não como prova do caso pós-otimização — para essa, vale o parágrafo acima.
- `rvsec-dataset/docs/20260628_phase7-recovery-and-funnel-reconcile.md:213-216` — o
  *"time bound, not heap-bound — more memory does not help"* é sobre **timeout na construção do
  call graph do Spark** em 3 APKs `failed_timeout_no_json`, não sobre o WTG. A conclusão é
  análoga, mas o sítio é outro.

O que continua valendo sem ressalva: `--succ-depth` está provado como alavanca errada
(`20260617_sweep_gh66_validacao_wtg.md:128` — recuperação de 24/97 com `sDepth=3` deu **0**), e
a change que atacaria o laço (gh70) foi **revertida como não-viável**.

### 3.6 O estrato acionável do braço MOP é 10/163

O braço guiado não consome "tem WTG" nem "alcança JCA". Consome o artefato MOP derivado, que
exige três sinais simultâneos. Rodando `derive_mop_artifact.derive()` sobre os JSONs reais:

**As marginais dependem de qual JSON se lê, e a coluna decisiva não.** No diretório operante
(`APKS_INSTRUMENTED_..._selected163/`) os 30 estão na versão gh91, sem WTG; nos JSON da Phase-7
eles têm o WTG de junho, sob a chave errada. Medido nas duas fontes:

| corpus | fonte | `flagged>0` | `wtgEdges>0` | `mopActivities>0` | **os três** |
|---|---|---:|---:|---:|---:|
| subset40 | Phase-7 | 8/40 | 15/40 | 8/40 | **4/40** |
| **163** | diretório operante | 30 | 41 | 34 | **10** |
| **163** | **Phase-7** | **34** | **48** | **37** | **10** |
| 219 | diretório operante | 36 | 54 | 41 | **13** |
| 219 | Phase-7 | 40 | 61 | 44 | **13** |

A coluna "os três" é **invariante entre as duas fontes** — é o que sustenta o estrato. As
marginais publicadas em `docs/20260805_handoff_gh97_campaign_execution.md:262-264` e
`docs/20260806_cmp163.md:80-87` são as do diretório operante; como o passo 13 monta o corpus a
partir da Phase-7 para os 133, é a linha Phase-7 que descreve o corpus de entrega. O "4/40" está
**confirmado, não corrigido**.

**Causa raiz medida:** `_build_wtg` (`derive_mop_artifact.py:931-990`) só aceita arestas cujo
evento é `click`. Nos JSONs:

| APK | transições | tipos de evento |
|---|---:|---|
| `org.fossify.calendar_20` | 63 | `implicit_rotate` 21, `implicit_home` 21, `implicit_power` 21 — **zero cliques** |
| `org.wikipedia_50595` | 237 | idem, 79 de cada — **zero cliques** |
| `net.osmtracker_73` | 287 | **`click` 161** + implícitos → 97 arestas derivadas |

`calendar` e `wikipedia` rodaram o WTG **até o fim, sem timeout** (1885 s e 2302 s,
`returncode 0`) e produziram só transições implícitas de ciclo de vida. Nos 163, **117 têm
`transitions > 0` mas só 41 têm arestas acionáveis** — 76 APKs têm WTG e mesmo assim zero
cliques. É a análise de listeners do GATOR falhando em UI moderna, o que casa com o registro de
que o guia MOP é inerte em Compose.

**Consequência para a rodada dos 30:** sob a chave correta, 7 dos 30 já têm `flagged > 0` e
`mopActivities > 0` e só lhes falta a aresta de WTG (`binaryeye`, `fossify.calendar`,
`fossify.math`, `fossify.musicplayer`, `fossify.notes`, `wikipedia`, `glpi.agent`). Mas cinco
deles já tiveram WTG bem-sucedido em junho e mesmo assim deram zero arestas (só implícitos), e
dois estouraram timeout. **O teto realista de ganho é 2 APKs**: o estrato iria de 10 para no
máximo 12. A rodada se justifica por integridade do corpus, não por ganho de estrato.

### 3.7 Correções factuais a registros existentes

1. **`docs/20260805_handoff_gh97_*`** — a afirmação *"os dois apps mais flagged (aegis 50,
   de.blau 42) têm WTG vazio: é propriedade do corpus"* é **falsa**. Medido:
   `com.beemdevelopment.aegis_81` (`dRT=24`) e `de.blau.android_3404` (`dRT=3`) têm
   `transitions=0` **com `timed_out: true`**. É falha de ferramenta. Idem
   `com.owncloud.android_48000100` (`dRT=14`) e `com.darkrockstudios.app.securecamera_31`
   (`dRT=17`).
2. **Os 30 nunca foram uma expansão de corpus.** Os 16 que estavam como `filtered_pkgdet_scope`
   já voltaram: hoje os 30 são `selected` em `dataset.csv`. A correção da chave moveu nos dois
   sentidos — trouxe 16 de volta e expulsou 34 pelo novo portão de denominador (147 + 16 = 163).
   Os 163 **já são** o corpus pós-correção.
3. **`sa_engine`** gravado no dataset é `gator`, não `gator-soot4.7.1`.

### 3.8 Eixos de homogeneidade verificados

| eixo | status | evidência |
|---|---|---|
| Chave de pacote | **HOMOGÊNEO** após a rodada dos 30 | §3.2 |
| Fonte do GATOR | **HOMOGÊNEO** (inferido, ver ressalva) | Último commit em `rvsec-gator/*/src/main`: `4280f3bd` (2026-06-17), **antes** da Phase-7 (2026-06-26). Depois disso só POMs (bumps 0.9.1→0.9.2→0.9.3, plugin jacoco) e comentários — nenhuma mudança de dependência |
| Soot / dependências | **HOMOGÊNEO** | `soot.version=4.7.1` inalterado desde 2023-11-23 |
| `android.jar` do GATOR | **HOMOGÊNEO** | `lib/gator/gator:87-97` resolve por `targetSdk` do `apktool.yml`, **não** por ordem lexicográfica. O defeito do weaver dexlib2 não se aplica. 0/348 logs dispararam fallback |
| `mopDir` / specs `jca` | **HOMOGÊNEO** | 348/348 logs passam `.../resources/jca`; último commit em `resources/jca/`: 2026-06-12, antes da Phase-7 |
| apktool | **HOMOGÊNEO** | `Using Apktool 2.10.0` em 348/348 |
| **WTG** | **HETEROGÊNEO** | §3.4 — tratado por declaração (`wtg_status`), não por rodada |

**Ressalva sobre a inércia do GATOR.** O que está provado é que a **fonte** não mudou desde
`4280f3bd`; que o **jar** reconstruído em 2026-08-08 seja byte-a-byte equivalente em
comportamento ao usado na Phase-7 é inferência a partir do git log, não medição. Entra como
limitação declarada (P13). Provar exigiria reconstruir o gator num worktree em `4280f3bd` e
comparar as entradas `.class` do fat jar com `lib/gator/rvsec-analysis-client.jar`, normalizando
os timestamps do zip.

**Ressalva sobre o alcance das linhas de log.** As evidências que dependem da saída do launcher
(`target level`, fallback de `android.jar`) só existem nos **266 logs que não foram mortos**: nos
82 com timeout o buffer de stdout se perdeu com o `kill` (§3.4). Para esses, "0 fallback" é
verdadeiro mas vazio. A versão do apktool e o `mopDir` vêm de fontes que sobrevivem (saída de
subprocesso e a linha `# cmd:`), e aí os 348/348 valem.

---

## 4. O plano

### Fase 0 — Congelar o substrato

Trabalho na branch `modules`.

1. **Reverter o `ExecutionContext`.** O estado-alvo é `233df18a^`, isto é
   **`efdd0541fbb43bf8c896a159c6bb3abbc479252e`** — antes disso o arquivo não era tocado desde
   `256ea84e`.
   ```bash
   cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
   git checkout efdd0541 -- rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java
   git rm rvsec/rvsec-core/src/test/java/br/unb/cic/mop/ExecutionContextTest.java
   ```
   Diff esperado no `ExecutionContext.java`: saem os imports `Collections` e `IdentityHashMap`,
   volta `HashSet`, some o helper `identitySet()`, e o construtor e o `setProperty` voltam a
   `new HashSet<>()`.

   O `ExecutionContextTest.java` **entrou junto** com `233df18a` e afirma a semântica de
   identidade (dois `SecretKeySpec` iguais, `assertFalse(validate(GENERATED_KEY, second))`).
   Reverter só a classe principal o deixa vermelho: o `-DskipTests` do passo 2 esconde, mas a
   árvore fica inconsistente e qualquer `mvn test` ou `-Pcheck` quebra depois. Por isso ele sai
   no mesmo commit — um commit, um estado consistente (P3).

   **Manter** `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java` — as constantes
   `GENERATED_CIPHER` e `MACED` são aditivas e nenhum `.mop` do `jca` as lê. **Manter** o reparo
   do weaver de `48b57fc5`.
2. **Construir o reator**, populando `/home/pedro/desenvolvimento/repository`:
   ```bash
   cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
   mvn clean install -DskipTests -DskipMopAgent
   ```
   `-DskipMopAgent` é obrigatório: um `mvn install` de raiz falha sem ele (descoberta da gh100).
3. **Registrar a proveniência** num arquivo do diretório de entrega:
   - SHA do commit da `modules` após o revert
   - sha256 de `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`
   - sha256 de `/home/pedro/desenvolvimento/repository/br/unb/cic/rvsec-core/0.9.3-SNAPSHOT/rvsec-core-0.9.3-SNAPSHOT.jar`
   - sha256 de `lib/gator/rvsec-gator.jar` (atual: `30160481ee3dbc19def68e4036c781377a3f111ce0c479be86b73d547f4b9f19`)
   - sha256 de `lib/gator/rvsec-analysis-client.jar` (atual: `207b61f7fb9cc29b721fc8b357b8b7566b90fb09c4ce7f199348b0e9793847a4`)
   - sha256 dos 23 `.mop` de `rvsec/rvsec-mop/src/main/resources/jca/`

**Gate 0:** o `rvsec-core` novo no repositório local tem mtime posterior ao build e o
`ExecutionContext.class` **não** contém `IdentityHashMap`/`newSetFromMap`.

---

### Fase A — Análise estática dos 30 *(paralela à Fase B)*

Reexecuta a campanha gh91 **sem** `skipWtg`, mantendo a chave `Mneut`.

4. **Quatro edições**, todas necessárias. As três primeiras em `scripts/gh91_sa_rerun.py`; sem
   elas o script nem inicia. A quarta em `scripts/gh91_campaign.py`; sem ela a campanha roda,
   mas mente.

   | arquivo:linha | hoje | passa a ser | por quê |
   |---|---|---|---|
   | `gh91_sa_rerun.py:83` | `APKS_CSV` aponta para `openspec/changes/gh91-sa-rerun-manifest-key/30_apks.csv` | `RV_ANDROID / "30_apks.csv"` | a change foi arquivada; o diretório não existe mais e o script morre em `:240-241` |
   | `gh91_sa_rerun.py:90` | `OUT_DIR = DATASET_ROOT / "SA_RERUN_gh91"` | `DATASET_ROOT / "SA_RERUN_gh91_wtg"` | `SA_RERUN_gh91/` é entregável assinado com `record/` e manifests sha256; não se sobrescreve. `REGISTRO`, `_campaign_state.json` e `_superseded/` derivam de `drv.OUT_DIR` (`gh91_campaign.py:86-88`), então a troca propaga sozinha |
   | `gh91_sa_rerun.py:309` | `"-clientParam", "skipWtg=true",` | linha removida | é o objetivo da rodada |
   | `gh91_campaign.py:99` | `has_sentinel()` é o único critério de "pronto" | exigir também `timed_out is False` no `_progress` (ou `transitions` não vazias) | ver abaixo — **sem isto o round 2 nunca acontece** |

   **Por que a quarta edição é obrigatória.** A campanha decide tudo por `has_sentinel()`:
   `pending_for_round` pula quem tem sentinela (`:264`), `classify` devolve `CLASS_COMPLETE` se
   tem sentinela (`:130-131`), e `retryable` usa a mesma predicação (`:243`). Mas o §3.4 prova
   que **um kill durante o WTG deixa em disco a escrita pré-WTG, já com o sentinela**. Logo, um
   APK que estourar o WTG no round 1 será contado como COMPLETE, **não será promovido ao round 2
   (120 g / 7200 s)**, e a campanha reportará sucesso.

   Isso era invisível na gh91 porque `skipWtg=true` fazia o cliente retornar logo depois da
   escrita pré-WTG (`RvsecAnalysisClient.java:180-184`) — ali "sentinela" e "completo" eram a
   mesma coisa. **Remover o `skipWtg` é exatamente o que ativa o defeito.** E o alvo não é
   hipotético: 9 dos 30 já estouraram timeout na Phase-7 (`app.pachli`, `http_shortcuts`,
   `securecamera`, `unchained`, `jerboa`, `binaryeye`, `owncloud.notes`, `glpi.agent`,
   `createpdf`).

   O passo 8 detecta a falha **depois**, quando a escada já se recusou a subir. Detectar não
   substitui promover.

5. **Conferir antes de rodar:**
   ```bash
   cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
   export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
   uv run python scripts/gh91_sa_rerun.py --plan
   uv run python scripts/gh91_sa_rerun.py --dry-run | head -20   # NÃO pode conter skipWtg=true
   ```
   Não exportar `JAVA_HOME` para 21 — Java 25 é o default da máquina.
   `ANDROID_SDK_HOME` não precisa: `_gator_env()` (`:329-341`) cai para `ANDROID_HOME`.

6. **Gate barato antes de queimar a janela** — um APK com resultado conhecido:
   ```bash
   uv run python scripts/gh91_sa_rerun.py --only net.osmtracker_73.apk \
       --jvm-memory 32g --timeout 3600
   ```
   Esperado: log com `[RvsecAnalysisClient] Filter package: net.osmtracker` e
   **`transitions ≥ 287`**, com eventos de `click` presentes.

   O critério **não** é igualdade com os 287 da Phase-7. Junho rodou este APK com a chave do
   detector (`net.osmtracker.activity`, **140 application classes**, 72,5 s); a rodada nova usa
   `Mneut = net.osmtracker`, e a gh91 já mediu **232 application classes** sob essa chave. O
   universo é maior, então a contagem deve subir e o tempo também — não espere os 72 s. O que o
   gate prova é que a cadeia (jar, SDK, chave, WTG ligada) está de pé, não que reproduz junho.

7. **Campanha completa**, em background rastreado pelo harness (nunca `nohup`/`setsid`):
   ```bash
   uv run python scripts/gh91_campaign.py --max-rounds 2
   ```
   Ladder: round 1 = 32 g / 3600 s, round 2 = 120 g / 7200 s, budget de memória 100 GiB
   (`gh91_campaign.py:66-67`). O dispatcher admite jobs enquanto `Σ --jvm-memory ≤ budget`
   (`gh91_sa_rerun.py:463-475`), ordenando *cheapest-first*.
   **Orçamento esperado: 8–14 h.** Referência: os mesmos 30 com WTG na Phase-7 somaram 16,55 h
   serial com 9 timeouts; sem WTG na gh91 somaram 10,16 h serial / 4,77 h de relógio.
   Acompanhar com `tail -f <DATASET>/SA_RERUN_gh91_wtg/REGISTRO.md`.

8. **Verificação pós-rodada — obrigatória, não opcional.** O sentinela `complete: true` não
   distingue WTG vazio de WTG truncado (§3.4). Cruzar com `_progress`:
   ```bash
   uv run python - <<'PY'
   import json, glob, os
   D="/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
   for f in sorted(glob.glob(D+"/_progress/*.json")):
       p=json.load(open(f)); j=p.get("json_path")
       n=len(json.load(open(j)).get("transitions",[])) if j and os.path.exists(j) else -1
       flag="SILENT-EMPTY" if (n==0 and p.get("timed_out")) else ""
       print(f"{p['apk']:48} tr={n:<6} {p['sa_status']:12} to={p.get('timed_out')} rc={p['returncode']} {flag}")
   PY
   ```

**Gate A:** 30/30 JSON escritos; cada um classificado como `ok` / `truncated` /
`genuine_empty`; nenhum `transitions == 0` sem classificação.

**Riscos conhecidos**
- **Resume mascara retry.** O resume é por existência do JSON (`gh91_sa_rerun.py:614-620`).
  Qualquer arquivo deixado para trás faz o round 2 pular exatamente o APK que falhou. A
  campanha resolve movendo para `_superseded/` antes do retry. Por isso o `OUT_DIR` novo.
- **Vazamento de temp dir.** No timeout, `sys.exit(-50)` (`lib/gator/gator:113`) pula
  `remove_temp_dirs()` (`:119`). Com 30 APKs × 2 rounds isso soma GB em `/tmp`. Limpar depois.
- **Tamanho do JSON — risco menor do que se pensava.** Com WTG os arquivos crescem, e nos 163 da
  Phase-7 o maior é `org.quantumbadger.redreader_117.apk.json` com **48,3 MiB**. Isso **não** é
  um problema de dispositivo: o que sobe para o aparelho é o **artefato derivado**, não o
  `.apk.json` — e o derivado do `redreader` tem **0,25 MiB**. Não existe guard de ~32 MB:
  `MopData.java:202` é a porta de `formatVersion` (INV-MOP-34), e o único limite de tamanho é
  `readFile` (`:707-712`), que só rejeita acima de `Integer.MAX_VALUE`. O que importa conferir é
  espaço em disco e tempo de derivação, não um teto de 32 MB.

---

### Fase B — Instrumentação dos 163 *(paralela à Fase A)*

Roda no host, sem Docker. A rota existe no CLI: `--skip-execution` (`__main__.py:502`), que pula
a Fase 2 inteira do `ExperimentController` (`:189-197`) — **nenhum emulador sobe no lote**.

**Custo medido: esta é a fase mais cara, não a mais barata.** A campanha real de instrumentação
(`rvsec-dataset-instrument/results/`, 2026-06-30/07-01) fez 228 APKs em 8 containers paralelos,
~5 h de relógio, a **485–681 s por APK** (~600 s), ≈38 h serial. E o `pre_processor` instrumenta
em **laço sequencial** (`pre_processor.py:282, 323, 417, 485` — não há pool). No host, sem
Docker, 163 × ~600 s ≈ **27 h**. Ver §5.

9. **Preflight com exit code.** O defeito nomeado em
   `rvsec-dataset/openspec/changes/rerun-corpus-jca-android/proposal.md:59-62` — as quatro
   variáveis de caminho da instrumentação (`RVSEC_INSTRUMENTED_APKS_DIR`,
   `RVSEC_INSTRUMENT_WORK_DIR`, `RVSEC_INSTRUMENT_RESULTS_DIR`, `RVSEC_INSTRUMENT_PROGRESS_DIR`)
   e `RVSEC_DATASET_CSV` — **não se aplica a esta rota**. Essas variáveis existem só em
   `rvsec-dataset/src/rvsec_dataset/config.py:32-39,496-505`; nada em `rv-android/modules/` ou
   `rv-android/scripts/` as lê. O `rv-experiment` escreve no `--output-dir` e não toca
   `dataset.csv`.

   O preflight que esta fase precisa é outro, e vale escrever com exit ≠ 0 e **probar
   negativamente** (fazer falhar de propósito uma vez, para provar que o gate morde):

   | asserção | por quê |
   |---|---|
   | `RVSEC_HOME` aponta para o `rvsec` deste workspace | sem ele a geração de monitores e a resolução de libs de runtime falham |
   | `repository/br/unb/cic/rvsec-core/0.9.3-SNAPSHOT/rvsec-core-0.9.3-SNAPSHOT.jar` tem mtime posterior ao build da Fase 0 e não contém `IdentityHashMap` | é o jar que vai ser dexado dentro de cada APK |
   | `--output-dir` **não existe ainda** | um diretório reaproveitado mistura substratos e é indetectável depois |
   | o arquivo do `--apks-filter` existe e tem exatamente 163 linhas, todas casando com um `.apk` de `APKS/` | o Click já exige existência (`exists=True`), mas não cardinalidade |
   | a variante resolvida é `dexlib2` | o default do CLI é `ajc` |

10. **Piloto obrigatório de 10 APKs** (5 grandes, 5 pequenos), instrumentados e validados em
    emulador via rv-platform. Razão concreta: na Phase 8 o piloto pegou o DEX-035, que teria
    comprometido 136 de 225 APKs. E aqui o risco é maior que o normal — o `rvsec-core`
    revertido sobre o weaver reparado é uma **combinação inédita, nunca tecida em APK nenhum**.
    Critério: 10/10 instrumentam, instalam e lançam; nenhum `VerifyError`; `RVSEC-COV` presente
    no logcat.

    O piloto é uma corrida própria, sobre 10 APKs, com o mesmo perfil do lote — inclusive
    `--skip-execution`:
    ```bash
    uv run rv-experiment run \
      --specification-set jca \
      --instrumentation-variant dexlib2 \
      --generate-monitors \
      --instrument-apks \
      --skip-static \
      --skip-execution \
      --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS \
      --apks-filter <lista dos 10 do piloto> \
      --output-dir <saída do piloto> \
      --name e3_piloto
    ```
    Este comando prova a metade de instrumentação do critério (10/10 tecidos, sem falha
    rebaixada) — que é onde defeitos de classe DEX-035 aparecem. A outra metade (instala, lança,
    `RVSEC-COV` no logcat, nenhum `VerifyError`) exige uma corrida com execução, que este plano
    não escreve: `--skip-execution` pula a Fase 2 inteira do `ExperimentController`
    (`:189-197`), que é onde o emulador vive. Fica nomeado como o passo de validação que falta
    fechar antes do Gate B.

    Gestão do emulador é do rv-platform — **nenhum comando manual de emulador, em nenhum
    contexto**.

11. **Lote dos 163:**
    ```bash
    cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
    uv run rv-experiment run \
      --specification-set jca \
      --instrumentation-variant dexlib2 \
      --generate-monitors \
      --instrument-apks \
      --skip-static \
      --skip-execution \
      --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS \
      --apks-filter <lista dos 163> \
      --output-dir <saída da fase B> \
      --name e3_preproc
    ```
    `dexlib2` **tem de ser forçado** — o default do CLI é `ajc`
    (`modules/rv-instrumentation/.../config.py:199-201`), e todas as campanhas reais usaram
    `dexlib2`. Armadilha de leitura conhecida: `experiment_config.json` grava `"ajc"` junto de
    `"instrument_apks": false`.

    APKs de entrada: `RV_ANDROID_NOVO_DATASET/APKS/` (348, todos os 163 presentes). Medido: de
    mesmo tamanho que os de `rvsec-dataset/head_apks/` em 163/163, e byte-idênticos por sha256
    em amostra de 10.

    **A lista dos 163** não existe como arquivo e precisa ser gerada. A fonte é
    `ase-journal/dataset/dataset.csv` com `funnel_stage == 'selected'` — uma linha por nome de
    APK, terminador LF, sem espaço à direita: o parsing é
    `read_text().strip().splitlines()` com casamento por *basename* (`config.py:584-586`), então
    um `\r` ou um espaço sobrando faz o APK sumir da corrida em silêncio. Conferir a cardinalidade
    (163) no preflight.

    Saída: os APKs tecidos vão para `<output-dir>/instrumented_apks/`.

**Gate B:** 163/163 instrumentados; `instrument_results.json` sem falhas silenciosas
rebaixadas; nenhum APK com `VerifyError` no piloto de validação (passo 10).

**Rollback.** Não existe retomada no meio: o `--resume-dir` força os três flags de
pré-processamento a `False` (INV-EXP-13), e um `instrumented_apks/` parcial é indistinguível de
um completo para o `get_instrumented_apks()`, que casa por presença de arquivo (INV-EXP-16). O
procedimento, portanto, é **recomeço**, e é barato porque o lote só escreve no `--output-dir`
novo: (i) critério de "abortou no meio" — `len(instrumented_apks/*.apk) < 163` ou
`instrument_errors.json` não vazio; (ii) `rm -rf <output-dir>` e rodar de novo, **nunca**
reaproveitar o parcial; (iii) registrar antes do lote o sha256 do `rvsec-core` do repositório
local, para provar depois que o recomeço usou o mesmo substrato.

---

### Fase C — Montar o diretório de entrega

12. **Criar o diretório**, auto-contido, **sem hardlink**:
    ```
    /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/
    ```
    Sem hardlink porque é exatamente o padrão que hoje faz `APKS_INSTRUMENTED_..._selected163/`
    mudar sozinho quando alguém mexe no diretório de 219 — verificado: **mesmo inode em 20/20**
    numa amostra, com `st_nlink = 3`.

    **Disco:** ~4,3 GiB no total. Medido nos artefatos existentes: 163 APK instrumentados somam
    **3,81 GiB** (média 23,9 MiB, e o tecido é **0,80× do original** — o `dexlib2` reempacota
    menor), e os 163 `.apk.json` da Phase-7 somam **0,47 GiB** (média 2,9 MiB, maior 48,3 MiB).
    Havia 1,8 TiB livres em `/pedro` na medição; não é restrição.

13. **Popular:** os 163 APK instrumentados da Fase B + os 163 `.apk.json` **co-locados** (a
    co-location é o "bilhete de entrada" da fase de execução):
    - **133** de `rvsec-dataset/static_analysis/` — medido: idênticos aos do diretório operante
      para todos os não-30
    - **30** da Fase A

    Esta cópia explícita é o ponto em que se resolve a divergência conhecida: `dataset.csv` já
    mistura Phase-7 (134) + gh91 (30), enquanto `rvsec-dataset/static_analysis/` discorda dele
    exatamente nesses 30. E `rvsec-dataset/src/rvsec_dataset/config.py:32` cai por default em
    `rvsec-dataset/static_analysis` — quem regerar `sa_*` sem `RVSEC_STATIC_ANALYSIS_DIR`
    **regride os 30 em silêncio**.

14. **Acrescentar `wtg_status` por APK**, como coluna declarada do corpus. A partição fecha em
    duas parcelas — os 133 vêm da Phase-7 e têm valor conhecido; os 30 vêm da Fase A e só se
    conhecem depois dela:

    | valor | 133 não-30 | os 30 | significado |
    |---|---:|---|---|
    | `ok` | **96** | conforme Fase A | `transitions > 0` |
    | `truncated` | **36** | conforme Fase A | `transitions == 0` com `timed_out: true` — irrecuperável (§3.5) |
    | `genuine_empty` | **1** | conforme Fase A | `eu.faircode.email_2322`, sem timeout |
    | **soma** | **133** | **30** | **163** |

    Estes são os números do §3.4, não os que circulavam antes: sobre os 163 da Phase-7 são
    117 `ok` / 45 `truncated` / 1 `genuine_empty`, e é a subtração dos 30 que dá 96 / 36 / 1.
    Nenhuma leitura fecha em 38.

15. **Manifesto `sha256`** do diretório inteiro. É o que transforma "instrumentei tudo com o
    código congelado" em algo verificável depois.

---

### Fase D — Portão de prontidão

16. **Artefatos:** 163 APK + 163 JSON presentes e casados por nome; manifesto fechado;
    `wtg_status` preenchido para os 163; nenhum JSON com `transitions: []` sem classificação;
    todos os 163 derivam sem exceção por `derive_mop_artifact.derive()`.

    Não há teto de tamanho de JSON a checar: o maior dos 163 tem 48,3 MiB
    (`org.quantumbadger.redreader_117`, que é o primeiro do estrato) e o artefato derivado dele
    ocupa 0,25 MiB. O "guard de ~32 MB" não existe em `MopData.java` — ver o risco da Fase A.
17. **Proveniência:** o arquivo do passo 3 existe e cobre commit + os cinco jars + os 23 `.mop`.
18. **Não-destruição:** nada foi tocado em `rvsec-dataset/static_analysis/`,
    `rvsec-dataset/instrumented_apks/`, `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`,
    `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_*` nem nas colunas `sa_*` de
    `ase-journal/dataset/dataset.csv`.

Cumpridos os três, o estudo 03 está **pronto para executar**.

---

## 5. Ordem e paralelismo

```
Fase 0  (build do reator, ~30 min)
   │
   ├──► Fase A  análise estática dos 30            8–14 h    (CPU/RAM: até 100 GiB)
   │
   └──► Fase B  piloto 10 APKs → lote dos 163      ~27 h     (CPU, serial)
                                    │
                       ambas ───────┴──► Fase C  montagem      ~1 h
                                              │
                                              └──► Fase D  portão   ~1 h
```

As Fases A e B são independentes, e isso está verificado no código, não só na proposta: o
instrumentador `dexlib2` não tem **nenhuma** referência a `codePackage`, `.apk.json` ou saída de
análise estática em `modules/rv-instrumentation-dexlib2/src/` — o único casamento de busca é um
comentário. Nada do que a Fase A produz entra na Fase B.

**A Fase B é a mais cara, não a mais barata.** São ~600 s por APK num laço sequencial
(`pre_processor.py:282, 323, 417, 485` — não há pool), ou seja ~27 h para os 163, contra 8–14 h
da Fase A. A referência é a campanha de 2026-06-30/07-01, que fez 228 APKs a 485–681 s cada,
em 8 containers paralelos.

Isso inverte a política de contenção: **quem espera é a Fase A**, que é a mais curta e a que
pede memória (até 100 GiB de budget numa máquina de 123 GiB). O caminho crítico é a Fase B, e
começar por ela é o que encurta o relógio total. Se a janela apertar, a alternativa é
paralelizar a instrumentação em containers — o que hoje D6 proíbe e teria de ser reaberto
explicitamente.

---

## 6. Fora do escopo, registrado para as próximas etapas

### Execução do experimento
Braços, orçamento por execução, número de containers, infraestrutura, SGLang e imagem
`phtcosta/rvandroid:0.9.3`. Nada disso é decidido aqui. Anotações úteis já levantadas:

- O braço chama-se **`mop_on_llm_70`**, não `mop_on_llm_on`
  (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:441`). O nome é a chave de identidade
  do resume e a coluna da consolidação.
- **`mop_off_llm_off` não é o APE original.** O APE original é a tool `ape`, cujo jar
  (`modules/rv-tools/src/rv_tools/builtin/ape/ape.jar`) é o binário upstream comitado por
  Tianxiao Gu. O fork tem 36 arquivos modificados no núcleo (`StatefulAgent` +814/−147,
  `SataAgent` +709/−70) e o preset `aperv` liga onze flags inexistentes no original. Na cmp163
  os dois diferiram com significância em `cov_method` (p = 0,024) e `mop_total` (p = 0,003).
  Manter os dois braços é obrigatório.
- **DroidBot tem de ser `dfs_greedy`** — as variantes `*_naive` e `random` param em 1.000
  eventos (`builtin/droidbot/tool.py:142-156`) e nunca alcançam um timeout longo.
- O jar do worktree `ape` master está **stale** (`386ce08d…`, perna A) enquanto o instalado é
  `a7eddf5a…` (rearch). Precisa `mvn install -Drvsec_home=…` antes de rodar.
- O `Dockerfile:27` clona o `ape` **sem pin de SHA** (decisão gh71 D3). O pin efetivo é o
  bind-mount `:ro` do jar no compose (`docker-compose.cmp163.yml:49`).

### Reuso do estudo 02 na tese
Decidido que **será reusado**; o mecanismo analítico fica em aberto e não condiciona a
prontidão.

### Escrita da tese
Item de lista, sem desdobramento neste plano.

---

## 7. Pendências herdadas — declaradas, não corrigidas

Entram como ameaças à validade ou notas de proveniência, não como trabalho.

| # | Pendência | Impacto |
|---|---|---|
| P1 | **Estrato acionável do braço MOP = 10/163** (§3.6), com causa raiz na ausência de eventos de clique no WTG do GATOR sob UI moderna | O tratamento é aplicável em 6 % do corpus; nos outros 94 % os braços `mop_on` e `mop_off` recebem estímulo idêntico |
| P2 | **APKs com WTG truncado**, irrecuperáveis (§3.5) — 45 nos 163 da Phase-7, dos quais 36 entram no corpus de entrega (os outros 9 estão nos 30 e serão redecididos pela Fase A) | Declarados via `wtg_status` |
| P3 | **`FEN-KPG-NPE`** — `jca/KeyPairGeneratorSpec.mop:26,29`: `String algorithm;` sem inicializador, `switch(algorithm)` → NPE propagada ao caller | Crash dependente de trajetória; **não cancela** no contraste pareado — enviesa contra o braço que alcança mais o KPG |
| P4 | **Colapso de dedupe no collector** — `ErrorDescription.equals/hashCode` exclui `expecting` (`rvsec-core/.../eh/ErrorDescription.java:108-139`) | Duas violações distintas no mesmo sítio colapsam em um registro; **não cancela** — comprime o delta entre braços |
| P5 | **`FEN-SRD-NEXTBYTES-FP`** — `jca/SecureRandomSpec.mop:155-161`: `next2` ausente do estado `end` | FP no traço canônico; casa com o maior estrato histórico do `errors.csv` (12.400 linhas). Contagens de violação **não são contagens de misuse** |
| P6 | **Reparo do weaver muda o resultado do `jca`** em relação ao E2, para cima | Nota de proveniência; comparabilidade absoluta com o E2 está quebrada por decisão consciente |
| P7 | **Divergência `dataset.csv` × `rvsec-dataset/static_analysis/`** nos 30, e o default de `rvsec_dataset/config.py:32` | Resolvida dentro do diretório de entrega (passo 13); permanece no repositório de origem |
| P8 | **`APKS_INSTRUMENTED_..._selected181/`** traz só 14 dos 30 e não é superconjunto dos 163 | Inconsistente; não usar. Candidato a remoção |
| P9 | Comentário errado em `RvsecAnalysisClient.java:157-164` e em `docs/20260731_gh91_handoff_grupo5.md:126` sobre o sentinela | Correção de documentação pendente |
| P10 | Registro do gh97 afirma que `aegis`/`de.blau` têm WTG vazio "por propriedade do corpus" — é falha de ferramenta (§3.7) | Correção de documentação pendente |
| P11 | Reverter o `ExecutionContext` quebra a aresta `generatedCipher` do `jca_android` | gh101 continua aberta e deve registrar isso |
| P12 | As 10 decisões do pesquisador em `audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` §7 | Em aberto; não bloqueiam o estudo 03 com `jca` |
| P13 | **Inércia comportamental dos jars do GATOR é inferida do git log**, não provada byte a byte (§3.8) | Ameaça de validade declarada. Prova possível: reconstruir o gator num worktree em `4280f3bd` e comparar as entradas `.class` do fat jar com `lib/gator/rvsec-analysis-client.jar`, normalizando timestamps do zip |
| P14 | **A validação em emulador do piloto não tem comando neste plano** — `--skip-execution` pula a fase onde o emulador vive (passo 10) | Metade do critério do Gate B (instala, lança, `RVSEC-COV`, sem `VerifyError`) fica sem procedimento escrito |

---

## 8. Índice de artefatos

| artefato | caminho |
|---|---|
| **Registro de execução das Fases A e B** (o que aconteceu ao rodar este plano, com os quatro defeitos medidos) | `rv-android/docs/20260812_registro_execucao_prontidao_e3.md` |
| Lista dos 30 | `rv-android/30_apks.csv` |
| Driver da rodada de SA | `rv-android/scripts/gh91_sa_rerun.py`, `gh91_campaign.py`, `gh91_gate.py`, `gh91_record.py` |
| Change da rodada anterior | `rv-android/openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/` |
| Execução anterior (sem WTG) | `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/` — JSONs, `REGISTRO.md`, `logs/`, `_progress/`, `record/` |
| Handoff da rodada anterior | `rv-android/docs/20260731_gh91_handoff_grupo5.md` |
| Varredura original com WTG | `rvsec-dataset/static_analysis/` + `rvsec-dataset-sa/logs/` + `_progress/` |
| Docs da Phase-7 | `rvsec-dataset/docs/20260628_phase7-recovery-and-funnel-reconcile.md`, `20260628_phase7-sa-failure-triage.md` |
| Evidência do teto do WTG | `rv-android/docs/20260617_sweep_gh66_validacao_wtg.md` |
| Corpus e funil do E2 | `ase-journal/dataset/dataset.csv`, `ase-journal/data-analysis/stats/selection_funnel_stats.txt` |
| Regra de neutralização | `ase-journal/docs/20260730_relatorio_remocao_package_detector.md:202-207` |
| Auditoria `jca_android` | `rv-android/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` |
| Evidência do reparo do weaver | `rv-android/openspec/changes/gh100-weaver-emission-fidelity/evidence/green_deltas.md` |
| Campanha cmp163 (3 dos 5 braços, 163 APKs, jca) | `rv-android/docs/20260806_cmp163.md`, `data/results/cmp163_consolidado/` |
| Plano abandonado, útil como referência | `rvsec-dataset/openspec/changes/rerun-corpus-jca-android/` |
