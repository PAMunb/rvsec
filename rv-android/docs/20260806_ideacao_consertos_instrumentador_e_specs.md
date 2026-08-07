# Ideação (Fase 0) — consertos no weaver dexlib2 e nas specs JCA/Android

**Data:** 2026-08-06
**Fase:** 0 — Ideação (`docs/WORKFLOW.md` §1). Documento de análise técnica, **não** é artefato OpenSpec.
**Entrada para:** `/opsx:new` ou `/opsx:explore` das changes propostas na §6.
**Estado do código:** nada implementado. Nenhum `.mop`, nenhuma fonte do weaver, nenhum arquivo sob `$WS/ase-journal/`, `$APKS` ou `$REPOS` foi modificado nesta sessão.
**Atualizado em 2026-08-06** (segunda sessão, após a análise do `rv-platform`): §5.5 (degrau V3), §6 (abertura), §6.4 (análise da plataforma e a decisão de não mexer no `rv-android`), §6.5 (o driver não é determinístico), §6.6 (critério de aceitação migrado), §7 (escopo da change 2) e §8 (decisão nº 2 fechada).

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
| **V3** | **Camada 3 no `cryptoapp`**: ajc × dexlib2, os 8 eventos do oráculo, com o nº 8 como discriminante | que o evento apagado voltou **em runtime**, contra referência independente | dias | **parado em 2026-08-06** (§6.4) — exigiria código novo no `rv-android`, e emulador à mão é proibido |
| **V4** | re-execução do corpus | quantas violações reais o defeito apagou (item 10 do relatório) | alto | V3 |

Três observações que valem mais que a tabela:

- **V3 tem referência dupla e independente**: o conserto faz o caminho inline concordar com (i) o caminho de wrapper do mesmo weaver e (ii) o AspectJ do grupo de controle. Duas referências que não se conversam, concordando — é a forma mais forte de evidência disponível sem re-executar o corpus.
- **V4 tem alvo barato definido**: `photok`, `aegis` e `org.cry.otp` são os três apps onde há sítio executado e mudo (relatório §11.3). Não é preciso re-rodar 219 APKs para o primeiro sinal.
- **Nenhum degrau autoriza tocar emulador à mão.** V4 passa por `rv-experiment run` / `rv-platform run`, que possuem o ciclo de vida inteiro (`CLAUDE.md`, regra permanente). Foi essa mesma regra que parou o V3 (§6.4): sem código novo na plataforma, não há janela legal para o driver.

---

## 6. Reviver a Camada 3 — decisão tomada

**Decidido em 2026-08-06:** a Camada 3 volta. Isto resolve a decisão nº 4 da §7.

**Corrigido no mesmo dia, depois da análise do `rv-platform`:** a camada volta **sem a L3-a**. O degrau V3 dependia de rodar o driver dentro da janela de emulador da plataforma, e isso exigiria código novo no `rv-android` — decidido contra (§6.4). O critério de aceitação do conserto de A passa a ser V0 e V2 (§6.6), do lado Java; L3-b e L3-c seguem inteiras, porque não dependem de driver nem de emulador.

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
| (a) | *"oracles are observation-driven (circular)"* | **Resolvida, e é o achado que reabre a camada.** Existem **duas** execuções das mesmas 23 specs tecidas por AspectJ: uma **pareada, em APK e em emulador** (`events_fair.csv`, 55.169 eventos) e uma em JVM via `-javaagent` (`errors_unit_tests.csv`) ✅ — detalhe na §6.3. Um evento observado sob **outro weaver** é ground truth **independente** do weaver sob teste. A circularidade era real enquanto o oráculo vinha de uma execução dexlib2; deixa de ser quando vem de qualquer um dos dois regimes. |
| (b) | *"INV-INS-59 multidex oracle never authored"* | **Continua aberta** — é a decisão nº 4 da §7, agora reduzida a "escrever o terceiro oráculo" × "baixar o mínimo com justificativa registrada". |
| (c) | *"determinism fragile (monkey -s 42 has emulator timing variance)"* | **Resolvida em código, e antes da objeção.** `scripts/drive_cryptoapp.py` é o nível 3.1.b do próprio plano de validação (taps explícitos, coordenadas fixas). A variância do monkey não é mais o caminho. |
| (d) | *"event-ordering pretension non-discriminating for atomic JCA calls"* | **Aceita — e o desenho muda por causa dela.** A camada revivida **abandona ordenação** como critério e passa a comparar **conjuntos** de `(spec, errorType, class, method)`. Para o defeito sob teste isso é estritamente mais forte: o que se quer saber é se o evento **existe**, não quando. |

### 6.3 Existem **dois** regimes AspectJ, e eles servem a defeitos diferentes

Correção a uma afirmação minha anterior, feita em 2026-08-06 e errada como generalização: *"o lado AspectJ vem de teste unitário em JVM"*. Isso vale **apenas** para o `errors_unit_tests.csv`. O `rv-instrumentation-ajc` instrumenta APK (dex2jar + ajc + d8) e **foi executado em emulador**, pareado com o dexlib2 ✅. O dado existe e ninguém o tinha cruzado com esta investigação:

| regime | fonte | o que é | tamanho ✅ |
|---|---|---|---|
| **R1 — pareado, em APK** | `out/run_jca_compare_consolidated/events_fair.csv` | mesmo corpus, mesmas tools (`ape`, `aperv:sata_mop`, `fastbot`), mesmo emulador, coluna `variant ∈ {ajc, dexlib2}` | 55.169 eventos (ajc 30.537 / dexlib2 24.632), 8 APKs com as duas variantes |
| **R2 — não pareado, em JVM** | `$RESULTS/errors_unit_tests.csv` | specs no `JavaMOPAgent.jar` via `-javaagent`, sem emulador e sem dexlib2 | 298 eventos, 134 tuplas, 32 apps |

**O que o R1 mostra, e é observação, não derivação** ✅:

| | ajc | dexlib2 |
|---|---:|---:|
| `TrustManagerFactorySpec` | **0** | **5.544** |
| `UnsafeAlgorithm` (categoria) | 10 | 2.842 |
| `UnsatisfiedConstraint` | **0** | **0** |

Nos 8 APKs pareados, o `TrustManagerFactorySpec` emite **zero sob ajc em todos**, contra 20 / 1.708 / 32 / 1.588 sob dexlib2. E não é silêncio por pipeline morto: em `com.wirelessalien.android.moviedb_33` o mesmo run ajc emitiu **15.640** eventos de `SSLContextSpec` e ainda assim **0** de TMF. **A fabricação da colisão de wrappers (defeito nº 1) deixa de ser derivada das guardas e passa a ser contraste pareado, sob a única variável que mudou — o weaver.**

**O que o R1 não mostra:** `UnsatisfiedConstraint` é **zero nos dois lados**, e a família de *parameter specs* que a truncagem apaga mal aparece. Isso não refuta o defeito nº 3 — é a mesma razão já medida no relatório (§11.3, §11.4): os eventos apagados moram em código de aplicação que a exploração de UI não alcança, e o teste unitário alcança. **O R2 continua sendo o único regime onde a categoria apagada existe.**

Daí a camada revivida ter três instrumentos, não dois:

**L3-a — pareada e estrita (`cryptoapp`).** Mesmo APK, mesmo driver (`drive_cryptoapp.py`), duas variantes, `--mandatory` ligado. Critério: os 8 eventos do oráculo nos dois lados. O **evento nº 8 é o discriminante do defeito nº 3** — a previsão é que hoje o dexlib2 falhe nele e o ajc passe, e que depois do conserto ambos passem. Teste que **falha antes e passa depois**.

**L3-b — pareada e ampla (R1).** Oráculos derivados do `events_fair.csv`, comparando por conjunto de tuplas nos 8 APKs pareados. É o instrumento do **defeito nº 1**: a previsão é que o TMF sob dexlib2 caia dos 5.544 para perto do zero do ajc depois da correção da colisão. Não depende de escrever driver nenhum — os runs já existem como linha de base.

**L3-c — não pareada e de presença (R2).** Oráculos derivados do `errors_unit_tests.csv` filtrado por `app_producao`, comparando **presença** de `(spec, errorType, class, method)`. Único instrumento com poder sobre a categoria `UnsatisfiedConstraint`. Gate apenas nos três apps de silêncio provado pelo join com `coverage.csv` — `photok`, `aegis`, `org.cry.otp`; o resto em modo relatório.

Ordem: **L3-a → L3-b → L3-c**. A ressalva do R1 que precisa ficar escrita: a cobertura média do ajc naqueles runs é baixa (`mean_cov_rv_method` ≈ 7–8% contra 31–37% do dexlib2, mediana ajc 0,0), efeito do estrato R8/Compose onde o ajc falha. Por isso o gate do L3-b só vale por APK em que o run ajc demonstrou estar vivo — critério objetivo: ter emitido evento de alguma outra spec.

### 6.4 O driver e o ciclo do `rv-platform` — analisado, e decidido contra

`drive_cryptoapp.py` declara como pré-requisito "emulator booted and running" e recebe `--serial`. Isso **não pode** ser satisfeito à mão: o ciclo de vida do emulador pertence ao `rv-platform`, sem exceção, inclusive para validação (`CLAUDE.md`, regra permanente). A pergunta era, portanto, como o driver entraria na janela que a plataforma já possui.

**A análise do `rv-platform` foi feita em 2026-08-06**, lendo `docs/architecture/rv-platform.md` contra o código. O que ela estabelece ✅:

| fato | sítio |
|---|---|
| a janela existe e é exatamente a que o driver pede: dentro de `_run_emulator_session`, quando a tool roda, o emulador está bootado (o boot é *gate* — `wait_for_boot()` vira `EmulatorError` antes de qualquer tool), o APK está instalado e o logcat já está gravando | `executor.py:388` (`with`), `:400-407` (install), `:414` (logcat), `:437` (tool) |
| a captura de logcat já é filtrada por tag `RVSEC`/`RVSEC-COV` — o arquivo por task é, sem adaptação, o insumo do comparador | `logcat_manager.py:79-82` |
| tools **não** recebem o `context`; o `context["android"]` injetado em `executor.py:393` não tem consumidor. O serial vem de `task.config.device_id`, derivado por `resolve_device()` — a mesma derivação do boot, do install e da captura (INV-PLT-28) | `tool_execution.py:111`, `platform.py:245`, `device.py` |
| o contrato de plugin são quatro métodos de `AbstractTool`; o registro é a lista de builtins ou o import guardado em `rv_platform/__init__.py`. **Não existe entry-point**, ao contrário do que afirma `modules/rvagent-tool/CLAUDE.md` | `abstract_tool.py`, `rv_tools/builtin/__init__.py:44-53` |
| `TraceComparator.batchAnalyze` consome **literalmente** o layout da árvore de resultados do `rv-platform` — `<results>/<apk>.apk/<apk>.apk__<rep>__<timeout>__<tool>.logcat` | `TraceComparator.java:83,191` × `task.py:722-731` |

E o que ela **refuta**: "componente do `TaskExecutor`" esbarra na classificação de fases por `isinstance` (`executor.py:314-324`), que obrigaria cirurgia no executor para hospedar algo específico de um app; "script invocado por hook" esbarra no fato de que os hooks `pre`/`post` existem mas ficam **fora** do `with` (`:214` e `:246`/`:267`) — não há ponto de extensão dentro da janela. Sobrava "tool do `rv-tools`", tecnicamente confirmada e barata.

**Decisão de 2026-08-06: não mexer no `rv-android`.** As três formas exigem código novo na árvore Python, e essa frente não será aberta agora.

**A consequência, sem atenuação:** a **L3-a por execução em emulador fica parada**. As únicas saídas restantes seriam emulador à mão (proibido por regra permanente) ou código na plataforma (recusado). O critério de aceitação do defeito nº 3 migra para os degraus do lado Java — V0 e V2 da §5.5 —, que ficam inteiramente dentro do `$DEXLIB2`; o que se perde nessa troca está dito na §6.6. **L3-b e L3-c não são afetadas**: nenhuma das duas precisa de driver, de emulador novo ou de uma linha de Python — os runs pareados do R1 já estão em disco e o R2 é JVM.

### 6.5 O driver não é determinístico — e é isso que o critério tem de contornar

Independentemente de onde o driver rode, o adjetivo "determinístico" que o script carrega no próprio docstring não se sustenta. Vale ficar escrito porque é a objeção (c) de 2026-05-06 voltando por outra porta: a §6.2 a declara "resolvida em código" porque o driver substitui o monkey — e substitui, mas o sorteio que importa **está dentro do app**, não na exploração.

**As fontes, em ordem de importância** ✅ (lidas do script e do oráculo):

1. **A moeda está no app.** `CipherUtil` sorteia `random.nextInt(10) > 6` a cada clique em Encrypt, e o oráculo confirma que são métodos distintos: eventos 3/4/5 em `CipherUtil.des`, evento nº 8 em `CipherUtil.aes`. Os 30 cliques do script existem só para que os dois ramos caiam: P(nenhum AES) = 0,7³⁰ ≈ 2,3·10⁻⁵. Ou seja, ~1 em 43 mil execuções perde **justamente o discriminante** — e um falso MISS depois do conserto leria como "o conserto não funcionou".
2. **Sincronização de UI** — esperas fixas de 0,6 s mais a espera implícita do `uiautomator2`, sobre SwiftShader. É a falha mais provável, mas falha **alto** (`UiObjectNotFoundError`), o que a torna distinguível de um evento ausente.
3. **Perda no ring buffer do logcat** — os 30 cliques despejam muita linha de coverage. É a única fonte que **imita** o defeito, porque a perda é silenciosa.
4. **Estado do monitor entre cenários** — os três cenários rodam no mesmo processo (`pm clear` só no início), e os eventos 3 e 7 são `InvalidSequenceOfMethodCalls`, cujo autômato é estado acumulado. A ordem fixa do script é o que os torna reprodutíveis; logo **a ordem é parte do oráculo**, e um crash que reinicie o processo no meio muda o resultado sem que nada esteja errado no weaver.

**O que o comparador faz com isso** ✅ — três fatos que mudam o desenho do gate:

- `matched()` é **existencial** (`TraceComparator.java:486-495`): multiplicidade não conta, 21 eventos DES valem o mesmo que 1. Clicar mais não infla TP.
- `matched()` **ignora o campo `location`** — casa por (spec, errorType, substring). O `location` do YAML é documentação, não discriminante; só o evento nº 8 tem substring realmente própria.
- `countFalsePositives()` (`:497-509`) conta **por ocorrência**, e o gate é F1 ≥ 0,98 sobre 1–2 entradas de oráculo por spec: 2 TP + 1 FP dá F1 = 0,8, reprovado. Os 30 cliques multiplicam por ~30 qualquer evento inesperado do caminho do Cipher. **O número de cliques é inofensivo do lado TP e perigoso do lado FP** — e com `--mandatory` qualquer FP reprova.

**O desenho que resolve**, e que precisa entrar na change se a L3-a for algum dia desbloqueada: **condicionar o veredito a uma testemunha independente do ramo**. A entrada em `CipherUtil.aes` produz uma linha `RVSEC-COV`, emitida pelo *coverage weaving* — não pela chamada de monitor que a truncagem apaga. O gate deixa de ser "o evento nº 8 apareceu?" e passa a ser: se `RVSEC-COV` mostra `CipherUtil.aes` **e** o evento nº 8 não aparece → defeito; se `CipherUtil.aes` não aparece → execução **inconclusiva**, repetir. O falso MISS de 2,3·10⁻⁵ deixa de existir como veredito. Complementos: clicar **até** a testemunha em vez de 30 vezes fixas; `adb logcat -G` contra a fonte 3; e, se o fonte do `cryptoapp` estiver disponível — não verificado —, trocar o sorteio por escolha de algoritmo na UI elimina a fonte 1 inteira, ao custo de mudar o APK sob teste e re-datar o oráculo.

Nada disso torna o roteiro determinístico. Torna o **veredito** determinístico condicionado a uma testemunha observável — que é o que um critério de aceitação precisa.

### 6.6 Critério de aceitação para a change do weaver

**Operativo hoje**, dado que a L3-a está parada (§6.4) — inteiramente dentro do `$DEXLIB2`, sem Python e sem emulador:

> **V0.** Um advice com N `monitorCalls` produz N invokes, na ordem do descritor. Falha antes do conserto e passa depois. Hoje nenhum teste exercita N > 1 porque os fixtures constroem o esperado pelo próprio `get(0)` (§5.4.2) — isso cai junto, senão o teste herda a premissa que deveria refutar.
> **V2.** No `cryptoapp` tecido antes e depois, os 9 eventos aparecem como `invoke-static` onde não apareciam, o que exige corrigir antes a mesma premissa em `BaksmaliDiffer.java:216` (§5.4.1).

**O que isso perde, e não deve ser maquiado:** V0 e V2 provam que o bytecode certo foi emitido, não que o evento chega ao logcat. É a mesma forma da troca de 2026-05-06 que a §5.3 critica — com uma diferença que precisa ficar explícita para a comparação ser justa: o substituto de então (`cov_rv_method`) era **estruturalmente cego** ao defeito, enquanto V0 e V2 **continuam discriminantes**, falhando antes e passando depois. É um instrumento mais fraco, não um instrumento surdo.

**Preservado para quando a L3-a for desbloqueada**, e falsificável:

> Antes do conserto de A, o gate estrito sobre o `cryptoapp` **reprova** o lado dexlib2 no evento nº 8 e aprova o lado ajc; depois do conserto aprova os dois, sem que nenhum dos outros 7 mude de estado. Se o dexlib2 já passar no evento nº 8 **antes** do conserto, a hipótese do defeito nº 3 está errada e a change para para reavaliação. O veredito de cada lado só vale condicionado à testemunha `RVSEC-COV` de `CipherUtil.aes` (§6.5); sem ela a execução é inconclusiva e se repete.

Duas correções de forma ao que estava escrito aqui antes ✅. O comando é `layer3 --batch --mandatory --ajc-results … --dexlib2-results …`, **não** `layer3 --mandatory`: o modo *analyze* espera um layout montado à mão (`<apkSubsetDir>/<oráculo>/{ajc,dexlib2}.logcat`, `TraceComparator.java:49-50,130-131`), enquanto o modo *batch* lê a árvore do `rv-platform` como ela é, e o `--mandatory` é honrado nos dois modos (`ValidationCli.java:208-218`). E o regex do batch captura a tool como `[^.]+`, então o nome `tool:variante` não pode conter ponto.

---

## 7. Decomposição proposta em changes

Recorte por **árvore** (Java irmão × Python) e por **risco** (mecânico × decisão de desenho), que é o que a §3 do WORKFLOW manda usar para escolher trilha.

| # | change | escopo | trilha sugerida | módulos | depende de |
|---|---|---|---|---|---|
| **1** | **contadores e observabilidade do weaver** | E (§3.4) + logar o `android.jar` de D (§3.3) | **FF SDD** — tem a decisão D-E1 (`batch` × `apk_paths`) | `$DEXLIB2/cli`, `rv-instrumentation-dexlib2`, `rv-instrumentation-core` | — |
| **2** | **reviver a Camada 3, sem a L3-a** | §6 menos o driver: desbloquear o gate de oráculos com oráculos derivados (§6.3), corrigir as premissas da §5.4 e executar **L3-b** e **L3-c** — nenhuma das duas precisa de driver, de emulador ou de Python | **Full SDD** — mudança de critério declarado (abandona ordenação, §6.2d), decisão sobre `MINIMUM_ORACLES` e o filtro de proveniência do L3-c | `$DEXLIB2/validator` | — (paralela a 1) |
| **3** | **fidelidade de emissão do weaver** | A (§3.1) + B (§3.2) + F (§3.5) | **Full SDD** — D-A1, D-A2, D-A3, D-B1 | `$DEXLIB2/{advice-emitter,dex-mutator,pointcut-engine}` | 1 (para observar) e 2 (para provar) |
| **4** | **correções de autoria das specs** | C (§4.1) nos **dois** conjuntos: binding + `fsm` + os três defeitos do `gtm1` | **FF SDD** — pouca decisão, mas altera comportamento documentado em spec e tem consequência de replicação (D1) | `$JCA`, `$JCA_ANDROID` | 3 (senão a lista corrigida continua não sendo lida) |
| **5** | **`CipherSpec` / `isValid` parametrizado** | G (§4.2) | **Full SDD** — decisão de arquitetura sobre código compartilhado entre conjuntos | `$CORE`, `$JCA`, `$JCA_ANDROID` | 4 |
| **6** | **reconexão do grafo de predicados** | H (§4.3) | **Full SDD** — 37 arestas, 11 exigem `Property` nova | `$JCA`, `$JCA_ANDROID`, `$CORE` | 4 |

Ordem defensável: **1 e 2 em paralelo → 3 → 4**, com 5 e 6 depois e independentes entre si.

Três razões, e nenhuma é de conveniência:

- **2 antes de 3** porque o critério de aceitação de 3 é um teste que precisa **falhar antes** do conserto (§6.6 — hoje V0 e V2). Consertar primeiro e validar depois torna o resultado inauditável — é exatamente o modo de falha que produziu o defeito nº 3, quando o instrumento discriminante foi substituído por um agregado e o defeito atravessou.
- **1 antes de 3** porque sem contador não se enxerga o efeito colateral de 3 (descarte por pressão de registrador).
- **3 antes de 4** porque a allow-list corrigida continua sendo lida de uma variável que a colisão impede de escrever.

**Restrição de calendário que não está nos outros documentos:** há **9 changes OpenSpec abertas**, três delas praticamente fechadas — `gh95` 56/57, `gh97` 66/67, `gh98` 45/48 ✅ —, o branch atual é `rearch-counterparts` e as contrapartes gateiam o merge. O plano §14 **D4** manda fechar as changes abertas e submeter antes de encarar esta frente. Abrir 1 e 2 agora compete com isso.

---

## 8. Decisões que dependem do usuário

**Já decidido nesta sessão:** reviver a Camada 3 (§6). O que decorre disso e ainda está em aberto:

1. **O terceiro oráculo** (§6.2b) — **decidido em 2026-08-06: derivar de execução AspectJ existente**, em vez de escrever o multidex à mão ou baixar o `MINIMUM_ORACLES`. Com a §6.3, a derivação passa a ter duas fontes com papéis distintos (R1 pareado para o defeito nº 1, R2 para a categoria apagada), e o mínimo de três passa a ser satisfeito por oráculos derivados, não por YAMLs escritos à mão.
2. **Integração do driver** (§6.4) — **decidido em 2026-08-06: não mexer no `rv-android`.** A análise da plataforma confirmou que a forma tecnicamente correta seria uma tool do `rv-tools` e refutou as outras duas, mas as três exigem código novo na árvore Python. Decorre disso a L3-a parada e o critério migrado para V0/V2 (§6.6). Reabrir isso é reabrir a decisão, não ajustar um detalhe de implementação.
3. **L3-b e L3-c entram na change 2 ou viram change própria?** Com a L3-a fora, elas são a change 2 inteira — a pergunta muda de "juntas ou separadas da L3-a" para "juntas ou separadas entre si". L3-b é quase de graça (os runs pareados já existem); L3-c exige gerador e a decisão do filtro de proveniência.

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

**Fontes de dado abertas nesta sessão e não usadas por nenhum dos documentos acima:**

| fonte | o que é | usada em |
|---|---|---|
| `out/run_jca_compare_consolidated/events_fair.csv` | **regime R1** — 55.169 eventos pareados `variant ∈ {ajc, dexlib2}`, mesmo corpus, mesmas tools, mesmo emulador; 8 APKs com as duas variantes | §6.3 |
| `out/run_jca_compare_consolidated/{per_apk_paired,tool_variant_comparison}.csv` | cobertura por APK e por tool/variante — base da ressalva sobre o estrato R8/Compose | §6.3 |
| `modules/rv-instrumentation-ajc/` | o instrumentador AspectJ de APK (dex2jar + ajc + d8) que produziu o lado ajc do R1 | §6.3 |
| `scripts/drive_cryptoapp.py` | driver de 369 linhas, escrito para reproduzir os 8 eventos do `cryptoapp-oracle.yaml` — e não determinístico, pelas razões da §6.5 | §6.1, §6.4, §6.5 |
| `$DEXLIB2/validator/src/main/java/.../{TraceComparator,OracleLoader,ValidationCli}.java` | o comparador, o gate `MINIMUM_ORACLES = 3` e o subcomando `layer3 --mandatory` | §5.1, §6.1, §6.5, §6.6 |
| `docs/architecture/rv-platform.md` + `modules/{rv-platform,rv-tools,rv-android-core}/src` | o subsistema de execução: contrato de plugin, ciclo do `TaskExecutor`, resolução de device, captura de logcat e layout da árvore de resultados | §6.4 |
| `docs/20260806_handoff_rv_platform_and_layer3_driver.md` | o handoff que originou a segunda sessão de 2026-08-06 (análise do `rv-platform` + decisões 2 e 3) | §6.4 |
