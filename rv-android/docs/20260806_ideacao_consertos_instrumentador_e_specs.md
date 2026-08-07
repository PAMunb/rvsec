# Ideação (Fase 0) — consertos no weaver dexlib2 e nas specs JCA/Android

**Data:** 2026-08-06
**Fase:** 0 — Ideação (`docs/WORKFLOW.md` §1). Documento de análise técnica, **não** é artefato OpenSpec.
**Entrada para:** `/opsx:new` ou `/opsx:explore` das changes propostas na §6.
**Estado do código:** nada implementado. Nenhum `.mop`, nenhuma fonte do weaver, nenhum arquivo sob `$WS/ase-journal/`, `$APKS` ou `$REPOS` foi modificado nesta sessão.

## 0. O que este documento é

A Fase 0 do workflow existe para responder três perguntas antes de escolher trilha e abrir change: **o que exatamente quero mudar**, **por que isso importa** e **quais partes do sistema são afetadas** (`docs/WORKFLOW.md` §1). Ela não tem artefato obrigatório, mas quando produz um documento técnico, esse documento vira material de referência das fases seguintes — é o que dá profundidade aos artefatos OpenSpec depois.

Este é esse documento. Ele **não repete** a investigação: ela está em

| documento | papel | linhas |
|---|---|---|
| `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` | **o relatório** — investigação em 6 revisões: os três defeitos de tecelagem, o grafo de predicados, o grupo de controle, a travessia para o `jca_android` | 1387 |
| `docs/20260806_plano_specs_jca_android.md` | **o plano** — fases F0–F7 da adaptação das specs ao Android, decisões D1–D6 | 581 |
| `docs/20260423_plano_validacao.md` | o framework de validação em 6 camadas, com gates pré-registrados | 469 |
| `docs/20260426_dexlib2_validation_results.md` | o que das 6 camadas foi de fato executado, e o veredito de ratificação da Fase 5 | 490 |

O que este documento acrescenta: **(i)** a verificação independente do relatório e do plano (§2); **(ii)** a especificação concreta de cada conserto no weaver, com as decisões de desenho que estão escondidas dentro deles (§3); **(iii)** o que sobrou nas specs depois da gh99 (§4); **(iv)** a análise da validação — que é a parte que faltava e é a mais importante (§5); **(v)** a decisão de **reviver a Camada 3**, com as objeções de 2026-05-06 respondidas uma a uma (§6); **(vi)** a decomposição proposta em changes (§7).

Convenção de caminhos idêntica à do relatório (`$WS`, `$DEXLIB2`, `$JCA`, `$JCA_ANDROID`, `$CORE`, `$RESULTS`, `$APKS`). Marcadores de confiança idênticos: ✅ verificado por mim contra fonte nesta sessão · ⚠️ herdado, não re-derivado · ❌ verificado e falso.

---

## 1. Ponto de partida: o que a gh99 fechou e o que ela não fechou

A change `gh99-metacrysl-jca-android` está **arquivada** (`openspec/changes/archive/2026-08-06-gh99-metacrysl-jca-android`) ✅. Ela entregou a fase F2 do plano: o conjunto `$JCA_ANDROID` com 23 `.mop` derivados do MetaCrySL para o API 30, sem `.aj` — 10 arquivos adaptados, 13 verbatim ✅ (conferido arquivo a arquivo).

**O que ela deliberadamente não fez, e por isso continua aberto:**

A gh99 mexeu **apenas em allow-lists**. Verifiquei o diff dos dois conjuntos linha a linha: das 23 specs, **13 são byte-idênticas** e as **10 divergentes diferem só em conteúdo de lista** — nenhuma linha divergente toca `call(`, `event`, `fsm`, `ere`, `returning`, `args(`, `target(` ou `addError` ✅. Consequência direta, e é o eixo deste documento:

> Os defeitos de autoria de spec — que são independentes de plataforma — **atravessaram intactos para o conjunto novo, nas mesmas linhas**. `$JCA/TrustManagerFactorySpec.mop:44` e `$JCA_ANDROID/TrustManagerFactorySpec.mop:44` são a mesma linha defeituosa; idem `SSLContextSpec.mop:46` nos dois ✅.

Duas correções de spec **já tinham sido aplicadas** ao `jca` antes da gh99 e portanto vieram junto: a negação da guarda do `KeyManagerFactorySpec` (`9cec468b`, 2026-06-04) e a canonicalização dos rótulos das specs PBE (`2fa44ff5`, 2026-06-12) ✅. As que faltam estão na §4.

E há a dívida que a própria gh99 registrou e não pôde quitar: o `CipherSpec` não tem allow-list própria — delega a `isValid()` em Java compartilhado pelos dois conjuntos (§4.3).

---

## 2. Verificação do plano e do relatório

Re-derivei as alegações verificáveis. O núcleo **sobreviveu inteiro**; o que segue são as correções e os pontos que mereciam ser mais precisos.

### 2.1 Confirmado por re-derivação independente nesta sessão ✅

| alegação | como conferi |
|---|---|
| truncagem inline: sítios | `EmitContext.java:51-52`, `MonitorInvokeBuilder.java:238-241`, `StaticInitializationEmitter.java:145-148`, `AfterThrowingEmitter.java:72`; `WrapperEmitter.java:637` itera |
| **7 advices truncados, 9 eventos descartados** | recontado do zero sobre `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` aplicando o critério real de despacho — bateu **exatamente**, inclusive a composição por spec |
| colisão de wrapper | chave em `DexWeaver.java:145`, `put` nu em `:159`, guarda `containsKey` já existente em `:208` |
| causa-raiz no javamop | `EventManager.java:91` (`retVal.equals`) + `MOPParameter.java:22-23` (compara tipo **e** nome) |
| `matchNamedRef` falha fechado | `PointcutMatcher.java:161`; commit `3af5b3aa`, **2026-05-29 22:50**, antes da campanha de julho |
| `parseCommonPointcut` fail-open | `DexWeaver.java:856-864`, dois `return null` |
| `android.jar` lexicográfico | reproduzido no host: `ANDROID_HOME` correto, 27/27 plataformas com `android.jar`, escolhido = **`android-4`** |
| grupo de controle | `errors_unit_tests.csv`: 43 `UnsatisfiedConstraint`, `tool=unit_test`; **0** em `errors.csv` e em `errors_bck.csv` |
| bases | 97.018 e 165.999 eventos; `SSLContextSpec` 26.312 (27,1%); TMF 18.029; `InvalidSequenceOfMethodCalls` 70.760 (72,9%) |
| a conta dos 17.175 | fecha exatamente: 8.371 + (9.015 − 427) + 216 |
| descritor | 115 advices, 17 com mais de uma `monitorCall` |
| grafo de predicados | 83% `ENSURES` / 22% `REQUIRES`, 37 arestas ausentes |
| `javax.xml.crypto` inexistente no Android | 0 entradas no `android.jar` das APIs 30 e 36 |
| `sourceLeaf.clone()` | `$MONITOR:17952`, arquivo de 2026-07-08 |

**Não re-verificado** (custo alto, ~75 min): o censo dos 219 APKs — 96 wrappers, 152/157/0 sítios, 15–22 mortos. Continua como resultado herdado do relatório, com o marcador dele.

### 2.2 Correções

1. ❌ **"o plano nunca foi atualizado desde `31f7b883`"** — falso. O plano recebeu +35 linhas em `3a88cb06` (a própria gh99), registrando na §9 que a F2 foi executada por derivação, corrigindo três previsões da §9.2 e apontando L1.5 como "primeiro alvo de uma change seguinte" ✅. O que falta reconciliar é o plano **com o relatório**, não com a gh99.

2. ⚠️→✅ **"nenhuma métrica derivável dá 116"** (relatório §2.3) — forte demais. O dedup ingênuo `grep -ho 'call([^)]*)[^)]*)' | sort -u` sobre os 23 `.mop` devolve **exatamente 116** ✅. A regra tolerante a espaço dá 144 ocorrências / 122 assinaturas, e a diferença são os dois `call (` de `PBEKeySpecSpec.mop:22,28` ✅. Ou seja: o número do plano é reprodutível e **explicável**, o que é melhor do que refutá-lo — a correção do relatório permanece válida, só a frase "nenhuma métrica" não.

3. **A truncagem inline é inteiramente o ramo do construtor.** O relatório diz que o advice cai no inline "quando `shouldWrap` é falso **ou** quando o alvo é construtor". Verifiquei: `shouldWrap(a) = "after".equals(a.getPosition())` (`WrapperEmitter.java:138-140`) e **todos os 17 advices fundidos do descritor de produção são `after`** ✅. Logo o ramo `shouldWrap`-falso contribui **zero** neste descritor, e os 7 truncados são, sem exceção, advices sobre `new(...)` barrados pelo `continue` explícito de `WrapperEmitter.java:215-219` ✅. Isso **estreita** a superfície do conserto e torna a mudança mais segura do que o relatório sugere.

4. **Os contadores do weaver: o diagnóstico da §12.4 está certo mas incompleto.** O relatório diz que o Python descarta `weaveCounts` no parse — verdade ✅. Mas isso não é o motivo pelo qual a campanha não tem contador nenhum. O motivo é anterior: `--results-json` só existe no subcomando **`batch`** (`InstrumentationCli.java:129-137`) ✅, e o caminho de produção — quando `apk_paths` vem preenchido, que é como o rv-experiment chama — usa o subcomando **`instrument`, um JVM por APK, sem `--results-json`** (`dexlib_instrumentation.py:245-252`) ✅, reconstruindo sucesso/erro em Python só por presença de arquivo. Evidência: em toda a árvore `rv-android` há **289 `instrument_errors.json` e zero `instrument_results.json`** ✅; na campanha, três `instrument_errors.json`, todos `{}` ✅. Consequência prática para o escopo da change: **consertar só o parse e o modelo Pydantic não restauraria nada** no caminho realmente usado.

5. **`parseCommonPointcut` tem um chamador, não quatro.** `DexWeaver.java:299`; `:310`, `:348` e `:412` são usos do `commonAst` resultante ✅. Não muda o defeito, muda a superfície de teste.

---

## 3. O que muda no weaver — item por item

Cada item traz: **sítio**, **mecanismo**, **mudança**, **as decisões de desenho que estão escondidas dentro dela** (é isso que decide a trilha SDD) e **risco**.

### 3.1 [A] Truncagem inline — `monitorCalls.get(0)`

**Sítio.** `$DEXLIB2/advice-emitter/.../MonitorInvokeBuilder.java` (`:48` `buildInvoke`, `:128` `buildMethodReference`, `:213` `registersFor`), `EmitContext.java:50-53`, `StaticInitializationEmitter.java:145-148`, `AfterThrowingEmitter.java:72`.

**Mecanismo.** Quando o javamop funde dois eventos num advice (regra de fusão: mesma posição, mesmo `retVal`, mesmo `throwVal` — `EventManager.java:91`), o descritor carrega uma lista de `monitorCalls`. O caminho de wrapper itera (`WrapperEmitter.java:637`); o caminho inline lê só o primeiro. Os três métodos do `MonitorInvokeBuilder` **re-derivam** `primaryMonitorCall(advice)` cada um por conta própria, o que é a razão de a truncagem estar em três lugares e não em um.

**Escopo exato, re-derivado ✅** — 7 advices, 9 eventos, todos sobre construtor, todos os descartados sendo emissores de erro:

| spec | advice (alvo) | mantido | descartado |
|---|---|---|---|
| `IvParameterSpecSpec` | `IvParameterSpec.new(byte[])` | `c1` | `c3` |
| `IvParameterSpecSpec` | `IvParameterSpec.new(byte[],int,int)` | `c2` | `c4` |
| `PBEKeySpecSpec` | `PBEKeySpec.new(char[],byte[],int,int)` | `c1` | `err1`, `err2`, `err3` |
| `PBEParameterSpecSpec` | `PBEParameterSpec.new(byte[],int)` | `c1` | `c3` |
| `SecretKeySpecSpec` | `SecretKeySpec.new(byte[],String)` | `c1` | `c3` |
| `SecretKeySpecSpec` | `SecretKeySpec.new(byte[],int,int,String)` | `c2` | `c4` |
| `SecureRandomSpec` | `SecureRandom.new(byte[])` | `c2` | `c3` |

`get(0)` preserva a ordem de declaração do `.mop`, e o idioma da tradução declara o caso válido primeiro — daí o viés ser sistemático e sempre na mesma direção (**falso negativo**).

**A mudança.** Passar o `MonitorCallDescriptor` como parâmetro em vez de cada método re-derivar `get(0)`, e o chamador iterar a lista emitindo N invokes, na ordem do descritor. É exatamente a forma que o `WrapperEmitter` já usa — o conserto **alinha o caminho inline ao caminho de wrapper do mesmo weaver**, não inventa semântica.

**Decisões de desenho embutidas** (é o que exige artefato de spec, não só plano):

- **D-A1 — falha parcial.** Hoje um binding não resolvido devolve `null`, derruba o plano inteiro e incrementa `plansSkippedUnresolvedBinding`. Com N chamadas: uma irresolúvel derruba as outras, ou emite as resolúveis e conta a perdida? A segunda é a única que não troca um silêncio por outro, mas muda a semântica de um contador existente.
- **D-A2 — ordem e atomicidade.** As N chamadas precisam sair na ordem do descritor (o monitor tem typestate; `c1` antes de `c3` não é a mesma coisa que o contrário). Nada garante isso hoje porque nunca houve mais de uma.
- **D-A3 — degrau ou conserto.** O relatório propõe (a) falhar alto / contar quando `monitorCalls.size() > 1` cai no inline, e (b) iterar. (a) sozinho **não restaura evento nenhum** — é instrumento de medida. Vale como passo 1 se e somente se estiver dito que é degrau.

**Risco.** Pressão de registrador: N invokes seguidos podem cair no funil `HighRegisterNonContiguous` / `plansSkippedHighRegister`. É observável — **mas só se os contadores sobreviverem**, o que hoje não acontece (§3.4). Daí a dependência A ⟵ E.

**Impacto.** Restaura 9 eventos, 4 specs e a categoria `UnsatisfiedConstraint` inteira. Medido contra o grupo de controle sob AspectJ, onde a categoria dispara 43 vezes ✅.

### 3.2 [B] Colisão de wrapper — `registerWrapper`

**Sítio.** `DexWeaver.java:145` (chave pela assinatura **original**), `:159` (`put` nu), `:208` (guarda `containsKey` que já existe, para o caminho de aliasing de subtipo).

**Mecanismo.** Dois advices geram wrapper para a mesma assinatura original; o último sobrescreve. O perdedor deixa de escrever a variável que a guarda do evento seguinte vai ler, e o inicializador `""` produz relato com valor vazio — **falso positivo**, e é o único dos três defeitos que *fabrica* violação.

**A mudança.** "Falhar alto" — que é o que o handoff propõe — **não é conserto, é detector**: para a instrumentação, não faz o evento perdido voltar. O conserto é o wrapper único chamar os dois conjuntos de eventos, que é a mesma forma do item A do outro lado do weaver. Sequência defensável: (1) detectar e contar; (2) medir quantos sítios; (3) fundir.

**Decisão embutida — D-B1:** fundir dois wrappers exige decidir a ordem das chamadas de monitor e o que fazer quando as duas assinaturas de retorno divergem. É decisão de desenho, não mecânica.

**Impacto.** ≈17.175 dos 18.029 eventos do `TrustManagerFactorySpec` (95,3%) e a má-atribuição de sítio do `SSLContextSpec` (26.312 eventos, 27,1% do dataset) ⚠️ — derivação do relatório, não medição.

### 3.3 [D] Resolução do `android.jar`

**Sítio.** `ConfigResolver.resolveAndroidJarFromEnv` (`$DEXLIB2/cli/.../ConfigResolver.java:111-127`) — `max()` por `String.compareTo` sobre os nomes de diretório.

**Mudança.** Comparar por nível de API numérico, **logar o jar resolvido** e falhar alto na ambiguidade. Mecânico, sem decisão de desenho.

**Por que importa mesmo com a campanha ilesa.** No Docker a regra acerta por sorte (`android-10`…`android-36`); no host escolhe `android-4` ✅, e piora conforme o SDK é atualizado. Nada loga a escolha — é a classe de defeito que só aparece depois de contaminar um resultado.

### 3.4 [E] Contadores do weaver — e é maior do que parece

**Sítio.** `BatchRunner.java` (~19 `counts.put`, dos quais 11 no bloco do laço de tecelagem `:291-304`), `writeResultsJson` `:423-431`, `PerApkResult` `:448-455`; `InstrumentationCli.java:129-137`; `dexlib_instrumentation.py:191/245-252/334-335/494-528`; `results.py:32-67`.

**Mudança.** Três partes, e as três são necessárias: (i) o subcomando `instrument` passa a emitir contadores (ou o driver deixa de usar o caminho `apk_paths`); (ii) `_parse_results_json` lê `weaveCounts`; (iii) `InstrumentationResults` ganha onde guardá-los.

**Decisão embutida — D-E1:** unificar em torno do `batch` significa perder o respeito ao subconjunto explícito de APKs, que é a razão declarada de o caminho `apk_paths` existir (o comentário no código diz que a alternativa seria uma "symlink farm"). É escolha entre duas arquiteturas, não conserto.

**Por que é pré-requisito.** Sem contadores não há como observar se A introduziu descarte por pressão de registrador, nem quantificar B. Hoje toda campanha perde o dado, e a próxima — a do `jca_android` — perderia de novo.

### 3.5 [F] `parseCommonPointcut` fail-open

**Sítio.** `DexWeaver.java:856-864`, chamador único em `:299`.

**Mecanismo.** Retorna `null` quando o `commonPointcut` está ausente **ou** é inparseável; o chamador lê `null` como "sem exclusões". Um `commonPointcut` malformado derruba silenciosamente **todas** as exclusões daquele weave. É o único caminho fail-open da cadeia, e é o oposto da decisão tomada em `3af5b3aa` para `matchNamedRef`.

**Mudança.** Distinguir ausente (legítimo, `null`) de inparseável (erro). O usuário pediu explicitamente que isso fosse **testado e registrado** — hoje está verificado em código e nunca exercitado por teste ✅.

---

## 4. O que muda nas specs — depois da gh99

### 4.1 [C] Os dois defeitos de binding, e eles precisam cair nos dois conjuntos

| spec | sítio (idêntico em `$JCA` e `$JCA_ANDROID`) ✅ | hoje | conserto |
|---|---|---|---|
| `TrustManagerFactorySpec` | `:44` | `event g3 after(String alg) returning(TrustManagerFactory k)` | renomear o binding para `mf` |
| `SSLContextSpec` | `:46` | `event unsafe_protocol after(String protocol):` — sem `returning` | acrescentar `returning(SSLContext ctx)` |

**A parte 2 não é opcional.** Verifiquei: nem `g3` nem `unsafe_protocol` aparecem no `fsm`/`ere` da própria spec ✅. O gerador dá a eles `{3,3,3,3}` — transição para `fail` a partir de todo estado. Consertar só o binding faria todo algoritmo fora da allow-list emitir um `InvalidSequenceOfMethodCalls` espúrio. Os eventos precisam entrar no `fsm` junto.

**No mesmo arquivo, os três defeitos de copiar-e-colar do `gtm1`** (`:62-65`, idênticos nos dois conjuntos ✅): grava `Property.GENERATED_KEY_MANAGERS` onde deveria ser o de trust managers; liga `TrustManager[][]` (dois níveis de array); e o pointcut declara retorno `KeyManager[]` para `getTrustManagers()`, que nunca casa.

**Ordem importa, e o plano a inverte.** A allow-list é consultada contra uma variável que a colisão impede de ser escrita. Corrigir lista antes de binding não muda relato nenhum — e no `SSLContextSpec` do `jca_android` a lista mais larga só **troca o rótulo** de `"found TLS"` para `"found ."` ⚠️ (derivação do relatório §12.3).

**Decisão pendente, e ela já foi tomada:** o plano §14 **D1** ✔ decide *"corrigir também no lado Java; a camada 2 é corrigida nos dois conjuntos"*, com a consequência registrada de que a reprodução exata dos números publicados deixa de valer. Não é pergunta aberta — é decisão a honrar no pacote de replicação.

### 4.2 [G] `CipherSpec` / `CipherTransformationUtil` — a dívida que a gh99 deixou

`CipherSpec.mop` é a única das 23 sem allow-list própria: delega a `isValid()` (`$CORE/jca/util/CipherTransformationUtil.java:32`), compilada no `rvsec-core` e **compartilhada pelos dois conjuntos** ✅. `isValid()` aceita duas famílias (AES, RSA) ✅; a regra Android derivada admite oito algoritmos. Resultado: o `jca_android` **gera chaves que depois marca em uso** (`ChaCha20`, `DESede`, `BLOWFISH`, `ARC4`) ⚠️.

Editar a classe compartilhada muda retroativamente o que qualquer campanha `jca` teria reportado — foi por isso que a gh99 parou. A saída que remove a segunda tradução à mão (a ameaça W3, que é a razão de a gh99 ter existido) é parametrizar `isValid` por tabelas vindas da mesma derivação. É a única parte deste documento que toca Java de runtime dos dois conjuntos ao mesmo tempo.

### 4.3 [H] Reconexão do grafo de predicados

83% das cláusulas `ENSURES` do CrySL têm contrapartida escrita; **apenas 22% dos `REQUIRES` têm leitor** ✅. São 37 arestas ausentes em quatro baldes: 23 defeitos de tradução, 11 que exigem constante `Property` nova, 2 omissões deliberadas, 1 inexpressível. Maior item do conjunto e o mais separável — a maior parte é edição de `.mop`; os 11 tocam `rvsec-core`.

**Ameaça correlata, do relatório §12:** não existe vínculo, nem em compilação nem em runtime, entre a constante `Property` escrita e a lida. Constante errada falha em silêncio, e **duas já existem hoje** (`KeyPairSpec.mop:38`, `TrustManagerFactorySpec.mop:65`).

---

## 5. A validação — a parte que decide se algo disso é demonstrável

### 5.1 O que existe

O `rvsec-instrumentation-dexlib2` tem um framework de validação em 6 camadas, desenhado em `docs/20260423_plano_validacao.md` e implementado no módulo `validator/` (14 classes de produção, 12 de teste) ✅:

| camada | instrumento | gate pré-registrado |
|---|---|---|
| 0 | invariantes `INV-INS-*` | 6/6 verdes |
| 1 | `BaksmaliDiffer` — diff estático de hooks no DEX | hook recall ≥ 0,95 em 30 APKs |
| 2 | `BootValidator` — install & boot | zero regressões de `VerifyError` |
| 3 | **`TraceComparator`** — mesmo APK, mesmo driver, **ajc × dexlib2**, contra oráculo YAML | F1 ≥ 0,98 e κ ≥ 0,9 **por spec** |
| 4 | `BatchValidator` — TOST de Wilcoxon pareado, α = 0,05 | bounds em `oracles/layer4-thresholds.yaml`, commitado em 2026-04-25 |
| 5 | `CoverageValidator` | recall ≥ 0,99 |

A Camada 3 é a que interessa: ela compara **conjuntos de eventos**, não médias. E o oráculo canônico `oracles/cryptoapp-oracle.yaml` (8 eventos, `full_coverage_required: true`, *"both ajc and dexlib2 pipelines must produce all 8 events"*) tem como **evento nº 8** ✅:

```yaml
spec: SecretKeySpecSpec
error_type: UnsatisfiedConstraint
location: { class: CipherUtil, method: aes }
expected_message_substring: "keyMaterial.length not randomized"
```

`SecretKeySpecSpec_c3Event` é **um dos 9 que a truncagem inline descarta** (§3.1). Ou seja: **o gate que pegaria o defeito nº 3 foi desenhado corretamente e pré-registrado em abril, antes de o defeito ser conhecido.**

### 5.2 O que de fato rodou

| momento | o que aconteceu |
|---|---|
| 2026-04-26 (run1, 5 APKs aleatórios) | Camada 3 executou e deu **FAIL com 0 linhas** — nenhum oráculo casava com nenhum dos 5 APKs; o `cryptoapp` não estava no subset e o oráculo `hateitorrateit` é um template com `expected_events: []` ✅ |
| 2026-05-06 (fechamento da Fase 5) | Camada 3 declarada **N/A — "design weakness + substituted"**: oráculos observacionais (circulares), o terceiro oráculo (multidex, `INV-INS-59`) nunca escrito, determinismo frágil, ordenação de eventos não discriminante para chamadas JCA atômicas ✅ |
| — | substituída por `validacao_full`: 851 tarefas pareadas ajc × dexlib2, com Δ `cov_rv_method` = 3,6 pp no estrato legado ✅ |

Estado hoje: `OracleLoader.MINIMUM_ORACLES = 3` e existem **dois** arquivos de oráculo ✅; `TraceComparatorTest` exercita a aritmética do comparador com logcats sintéticos em `@TempDir` ✅, nunca uma execução real.

### 5.3 Por que a substituição é estruturalmente cega ao defeito nº 3

Este é o ponto central deste documento, e é um argumento, não uma opinião:

> A evidência substituta mede **cobertura de métodos** (`cov_rv_method`, Δ 3,6 pp). A truncagem inline **não altera cobertura de método nenhuma**: o sítio continua tecido, `c1Event` continua sendo chamado no mesmo lugar; o que some são as chamadas de monitor *adicionais* do mesmo advice fundido. Um weaver que apaga 9 emissores de erro tem exatamente a mesma cobertura de métodos de um que não apaga.

A Camada 3 mede conjunto de eventos e teria visto. A substituta mede cobertura agregada e **não pode** ver, por construção. Não foi azar: foi troca de um instrumento discriminante por um não discriminante, documentada e assinada — e o custo dessa troca só apareceu quinze meses de trabalho depois, na forma de uma categoria de erro inteira ausente de 97.018 eventos.

Vale registrar que as objeções de 2026-05-06 **eram legítimas** (oráculo observacional é circular; determinismo de monkey é frágil). O que faltou não foi rigor, foi notar que o substituto respondia a outra pergunta.

### 5.4 Consertos na própria validação, antes de validar qualquer coisa

Três, e o primeiro é bloqueante:

1. **`BaksmaliDiffer.java:216` faz `getMonitorCalls().get(0)`** ✅ para atribuir spec a wrapper. **O oráculo estático compartilha a premissa do defeito** — não consegue enxergar o conserto de A. Precisa ser corrigido *antes*, senão a Camada 1 valida nada. (Independente disso, a Camada 1 já tem a lacuna de normalização de forma de hook documentada em 2026-05-06: recall 0,0 por comparar `ajc$before/after_*` com `mop.MonitorWrappers.*` por string crua.)
2. **Os testes herdaram a premissa.** `EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121` constroem fixtures via `getMonitorCalls().get(0)` ✅. Um advice com N > 1 não é exercitado em lugar nenhum.
3. **`MINIMUM_ORACLES = 3` com dois arquivos** bloqueia a Camada 3 estruturalmente. Ou se popula o oráculo #2 e se escreve o #3, ou se baixa o mínimo com justificativa registrada — e a segunda opção precisa ser decisão explícita, não efeito colateral. **Tratado na §6**, que é onde a decisão de reviver a camada foi tomada.

### 5.5 Escada de validação proposta

Do mais barato ao mais caro; cada degrau só faz sentido depois do anterior:

| # | degrau | o que prova | custo | pré-requisito |
|---|---|---|---|---|
| **V0** | teste unitário de emissão: advice com N `monitorCalls` produz N invokes, **na ordem do descritor** | que o conserto de A faz o que diz, deterministicamente | minutos | corrigir os fixtures (§5.4.2) |
| **V1** | paridade intra-weaver: para o mesmo advice fundido, o plano inline e o de wrapper emitem o mesmo conjunto de chamadas | que os dois caminhos do weaver concordam entre si | horas | V0 |
| **V2** | Camada 1 sobre um APK tecido antes/depois: os 9 eventos aparecem como `invoke-static` onde não apareciam | que a mudança chegou ao DEX | horas | `BaksmaliDiffer` corrigido (§5.4.1) |
| **V3** | **Camada 3 no `cryptoapp`**: ajc × dexlib2, os 8 eventos do oráculo, com o nº 8 como discriminante | que o evento apagado voltou **em runtime**, contra referência independente | dias | **§6 — decidido**; execução **só** via `rv-experiment` |
| **V4** | re-execução do corpus | quantas violações reais o defeito apagou (item 10 do relatório) | alto | V3 |

Três observações que valem mais que a tabela:

- **V3 tem referência dupla e independente**: o conserto faz o caminho inline concordar com (i) o caminho de wrapper do mesmo weaver e (ii) o AspectJ do grupo de controle. Duas referências que não se conversam, concordando — é a forma mais forte de evidência disponível sem re-executar o corpus.
- **V4 tem alvo barato definido**: `photok`, `aegis` e `org.cry.otp` são os três apps onde há sítio executado e mudo (relatório §11.3). Não é preciso re-rodar 219 APKs para o primeiro sinal.
- **Nenhum degrau autoriza tocar emulador à mão.** V3 e V4 passam por `rv-experiment run` / `rv-platform run`, que possuem o ciclo de vida inteiro (`CLAUDE.md`, regra permanente).

---

## 6. Reviver a Camada 3 — decisão tomada

**Decidido em 2026-08-06:** a Camada 3 volta. Isto resolve a decisão nº 4 da §7 e reordena a §5.5 — o degrau V3 deixa de ser opcional e passa a ser o critério de aceitação do conserto de A.

### 6.1 O que já existe, e é mais do que o veredito de 2026-05-06 sugere

Levantamento nesta sessão ✅:

| peça | onde | estado |
|---|---|---|
| comparador | `$DEXLIB2/validator/.../TraceComparator.java` | implementado; modos `analyze` e `batch` |
| CLI | `validator-cli layer3 --oracles --apks [--batch] [--mandatory]` | implementado, com o **gate `--mandatory`** (gh56 `INV-INS-73`) que reprova o par diante de **qualquer** desvio — evento faltando ou sobrando no traço dexlib2 |
| oráculo canônico | `validator/oracles/cryptoapp-oracle.yaml` | 8 eventos, `full_coverage_required: true`; o **evento nº 8** é `SecretKeySpecSpec`/`UnsatisfiedConstraint`, um dos 9 que a truncagem apaga |
| APK | `apks_examples/cryptoapp.apk` | presente |
| **driver determinístico** | `scripts/drive_cryptoapp.py` (369 linhas) | escrito para "reproduzir cada evento do `cryptoapp-oracle.yaml`", percorrendo as três activities; declara-se a "canonical reference run" porque a exploração estocástica do APE-RV não alcança os ramos inseguros em 300 s |
| pipeline de comparação | `rv-instrumentation-ajc` + `--instrumentation-variant {ajc,dexlib2}` no `rv-experiment` | ambos vivos; o ajc segue como padrão (`project_ajc_retained_as_optin`) |
| gate de diversidade | `OracleLoader.MINIMUM_ORACLES = 3`; `validator-cli oracles` | implementado — e **é o bloqueio**: existem dois arquivos |

Ou seja: reviver não é construir. É **desbloquear o gate de oráculos e executar o par** — mais os consertos de premissa da §5.4.

### 6.2 As quatro objeções de 2026-05-06, respondidas uma a uma

O fechamento da Fase 5 declarou a camada N/A por "design weakness". As objeções eram legítimas; três delas hoje têm resposta que **não existia** naquela data.

| # | objeção (verbatim, `20260426_dexlib2_validation_results.md` §5.3) | resposta hoje |
|---|---|---|
| (a) | *"oracles are observation-driven (circular)"* | **Resolvida, e é o achado que reabre a camada.** O `$RESULTS/errors_unit_tests.csv` é uma execução das **mesmas 23 specs tecidas por AspectJ** via `-javaagent` — *"No emulator, no dexlib2"* verbatim na fonte ✅. Um evento observado sob **outro weaver** é ground truth **independente** do weaver sob teste. A circularidade era real enquanto o oráculo vinha de uma execução dexlib2; deixa de ser quando vem do controle. Ninguém tinha aberto esse arquivo em maio de 2026. |
| (b) | *"INV-INS-59 multidex oracle never authored"* | **Continua aberta** — é a decisão nº 4 da §7, agora reduzida a "escrever o terceiro oráculo" × "baixar o mínimo com justificativa registrada". |
| (c) | *"determinism fragile (monkey -s 42 has emulator timing variance)"* | **Resolvida em código, e antes da objeção.** `scripts/drive_cryptoapp.py` é o nível 3.1.b do próprio plano de validação (taps explícitos, coordenadas fixas). A variância do monkey não é mais o caminho. |
| (d) | *"event-ordering pretension non-discriminating for atomic JCA calls"* | **Aceita — e o desenho muda por causa dela.** A camada revivida **abandona ordenação** como critério e passa a comparar **conjuntos** de `(spec, errorType, class, method)`. Para o defeito sob teste isso é estritamente mais forte: o que se quer saber é se o evento **existe**, não quando. |

### 6.3 Dois instrumentos, não um

A camada revivida tem duas formas, com custos e poderes diferentes. São complementares.

**L3-a — pareada e estrita (`cryptoapp`).** Mesmo APK, mesmo driver (`drive_cryptoapp.py`), duas variantes de instrumentação, `--mandatory` ligado. Critério: os 8 eventos do oráculo presentes nos dois lados. O **evento nº 8 é o discriminante do defeito nº 3** — hoje a previsão é que o dexlib2 falhe nele e o ajc passe; depois do conserto de A, ambos passam. É um teste que **falha antes e passa depois**, que é a única forma de validação que prova alguma coisa.

**L3-b — ampla e não pareada (grupo de controle).** Gerar oráculos a partir de `$RESULTS/errors_unit_tests.csv` (+ `categoria_unit_tests.csv` para proveniência) e comparar por **presença** de tupla, não por traço. Cobre **32 apps / 134 tuplas** ✅ em vez de um. Não é pareada — o lado ajc vem de teste unitário em JVM e o lado dexlib2 de execução em emulador, com drivers diferentes —, então não sustenta F1/κ; sustenta a pergunta que interessa: *a categoria que o dexlib2 emite zero vezes reaparece?* Como o piso atual é **exatamente zero** em 97.018 e em 165.999 eventos ✅, qualquer valor não nulo é sinal, e a diferença de driver não confunde o resultado.

Ordem: **L3-a primeiro** (barato, determinístico, discriminante), L3-b depois (mais amplo, resolve de quebra a objeção (b), porque 32 apps de ground truth independente valem mais que três YAMLs escritos à mão).

### 6.4 Ponto de integração que precisa de decisão

`drive_cryptoapp.py` declara como pré-requisito "emulator booted and running" e recebe `--serial`. Isso **não pode** ser satisfeito à mão: o ciclo de vida do emulador pertence ao `rv-platform`, sem exceção, inclusive para validação (`CLAUDE.md`, regra permanente). Reviver a camada exige, portanto, decidir **como o driver entra no ciclo que a plataforma já possui** — como tool do `rv-tools`, como componente do `TaskExecutor`, ou como script invocado dentro da janela em que a plataforma já tem emulador e APK instalados. É decisão de arquitetura e pertence à change da §7.

### 6.5 Critério de aceitação proposto para a change do weaver

Fica escrito aqui para virar critério de aceitação do artefato OpenSpec, e é falsificável:

> Antes do conserto de A, `validator-cli layer3 --mandatory` sobre o `cryptoapp` **reprova** o lado dexlib2 no evento nº 8, e aprova o lado ajc. Depois do conserto, aprova os dois, sem que nenhum dos outros 7 eventos mude de estado. Se o dexlib2 já passar no evento nº 8 **antes** do conserto, a hipótese do defeito nº 3 está errada e a change para para reavaliação.

---

## 7. Decomposição proposta em changes

Recorte por **árvore** (Java irmão × Python) e por **risco** (mecânico × decisão de desenho), que é o que a §3 do WORKFLOW manda usar para escolher trilha.

| # | change | escopo | trilha sugerida | módulos | depende de |
|---|---|---|---|---|---|
| **1** | **contadores e observabilidade do weaver** | E (§3.4) + logar o `android.jar` de D (§3.3) | **FF SDD** — tem a decisão D-E1 (`batch` × `apk_paths`) | `$DEXLIB2/cli`, `rv-instrumentation-dexlib2`, `rv-instrumentation-core` | — |
| **2** | **reviver a Camada 3** | §6 inteira: desbloquear o gate de oráculos, corrigir as premissas da §5.4, integrar `drive_cryptoapp.py` ao ciclo do `rv-platform`, executar L3-a e produzir o teste que **falha hoje** | **Full SDD** — decisão de arquitetura (§6.4), mudança de critério declarado (abandona ordenação, §6.2d) e decisão sobre `MINIMUM_ORACLES` | `$DEXLIB2/validator`, `rv-platform`, `rv-tools`, `scripts/` | — (paralela a 1) |
| **3** | **fidelidade de emissão do weaver** | A (§3.1) + B (§3.2) + F (§3.5) | **Full SDD** — D-A1, D-A2, D-A3, D-B1 | `$DEXLIB2/{advice-emitter,dex-mutator,pointcut-engine}` | 1 (para observar) e 2 (para provar) |
| **4** | **correções de autoria das specs** | C (§4.1) nos **dois** conjuntos: binding + `fsm` + os três defeitos do `gtm1` | **FF SDD** — pouca decisão, mas altera comportamento documentado em spec e tem consequência de replicação (D1) | `$JCA`, `$JCA_ANDROID` | 3 (senão a lista corrigida continua não sendo lida) |
| **5** | **`CipherSpec` / `isValid` parametrizado** | G (§4.2) | **Full SDD** — decisão de arquitetura sobre código compartilhado entre conjuntos | `$CORE`, `$JCA`, `$JCA_ANDROID` | 4 |
| **6** | **reconexão do grafo de predicados** | H (§4.3) | **Full SDD** — 37 arestas, 11 exigem `Property` nova | `$JCA`, `$JCA_ANDROID`, `$CORE` | 4 |

Ordem defensável: **1 e 2 em paralelo → 3 → 4**, com 5 e 6 depois e independentes entre si.

Três razões, e nenhuma é de conveniência:

- **2 antes de 3** porque o critério de aceitação de 3 é um teste que precisa **falhar antes** do conserto (§6.5). Consertar primeiro e validar depois torna o resultado inauditável — é exatamente o modo de falha que produziu o defeito nº 3, quando o instrumento discriminante foi substituído por um agregado e o defeito atravessou.
- **1 antes de 3** porque sem contador não se enxerga o efeito colateral de 3 (descarte por pressão de registrador).
- **3 antes de 4** porque a allow-list corrigida continua sendo lida de uma variável que a colisão impede de escrever.

**Restrição de calendário que não está nos outros documentos:** há **9 changes OpenSpec abertas**, três delas praticamente fechadas — `gh95` 56/57, `gh97` 66/67, `gh98` 45/48 ✅ —, o branch atual é `rearch-counterparts` e as contrapartes gateiam o merge. O plano §14 **D4** manda fechar as changes abertas e submeter antes de encarar esta frente. Abrir 1 e 2 agora compete com isso.

---

## 8. Decisões que dependem do usuário

**Já decidido nesta sessão:** reviver a Camada 3 (§6). O que decorre disso e ainda está em aberto:

1. **O terceiro oráculo** (§6.2b) — escrever o oráculo multidex, ou baixar `MINIMUM_ORACLES` com justificativa registrada? A L3-b (§6.3) é uma terceira saída: 32 apps de ground truth independente valem mais que três YAMLs à mão, e o mínimo poderia passar a contar oráculos **derivados do controle**.
2. **Integração do driver** (§6.4) — `drive_cryptoapp.py` como tool do `rv-tools`, como componente do `TaskExecutor`, ou como script invocado dentro da janela que o `rv-platform` já possui?
3. **L3-b entra na change 2 ou vira change própria?** Ela é ampla e mexe em geração de oráculo a partir de dado de campanha; L3-a sozinha já basta como critério de aceitação de 3.

Independentes da decisão acima:

4. **Trilha e granularidade** da §7 — seis changes, ou fundir 1+3 (uma change de weaver) e 4+5 (uma change de specs)?
5. **D-A3** — o degrau "contar antes de consertar" entra como tarefa da change 3, ou o conserto vai direto?
6. **D-E1** — unificar no subcomando `batch` (perde o subconjunto explícito de APKs) ou estender o subcomando `instrument`?
7. **Sequenciamento contra o board** (§7, fim) — abrir agora ou depois de fechar `gh95`/`gh97`/`gh98`?

Duas coisas que **não** são perguntas, e é bom que fique escrito para não serem re-litigadas:

- **O destino do `jca`** já está decidido (plano §14 **D1** ✔): corrige-se nos dois conjuntos, e a perda de reprodução exata dos números publicados vai para o pacote de replicação.
- **O item 12** do relatório (validade de `InvalidSequenceOfMethodCalls` como métrica — 70.760/97.018, co-emissão 100% nos dois regimes) está instrumentado com números e sem julgamento. É pergunta de artigo, não de change.

---

## 9. Referências

- `docs/20260806_grafo_predicados_e_pcd_dexlib2.md` — a investigação. §2.2/§2.3 (PCD), §3 (colisão), §4.5 (grafo), §4.8 (truncagem inline), §10 (`CipherSpec`), §11 (grupo de controle), §12 (`jca_android`)
- `docs/20260806_plano_specs_jca_android.md` — §4.1 (suporte a PCD), §9 (F2, atualizada pela gh99), §13 (sequenciamento), §14 (decisões D1–D6), §15 (riscos)
- `docs/20260423_plano_validacao.md` — 6 camadas, gates, `INV-INS-58`/`INV-INS-59`
- `docs/20260426_dexlib2_validation_results.md` — §4.1 (run1), §5.3 (Camada 3 declarada N/A), §5.7 (veredito de ratificação)
- `docs/WORKFLOW.md` — §1 (Fase 0), §3 (seleção de trilha)
- `openspec/changes/archive/2026-08-06-gh99-metacrysl-jca-android/` — a change arquivada; `docs/20260806_metacrysl_tier_map.md` para tiers, rastreabilidade e dívida
- `docs/20260806_handoff_plan_review_and_changes.md` — o handoff que originou esta sessão; correções a ele na §2.2
