# E1 executado: a identidade de composable chega ao runtime, e custa 1,8 µs por composable

**Data**: 2026-08-06
**Escopo**: execução do experimento E1 (`20260803_compose_identidade_composable_design.md` §9), seus resultados, e as correções que a execução impôs aos documentos 4 e 5 da série.
**Status**: resultado experimental. **A Via A passou.** O gate seguinte (Fase 2, saturação do alcance transitivo) continua aberto e não é tocado aqui.

**Sexto de uma série** sobre gator × Compose:

1. `20260730_compose_gator_substrato_estatico.md` — *por que* a WTG colapsa (diagnóstico).
2. `20260731_gator_compose_viabilidade.md` — *o que dá para fazer* no desenho atual (quatro vias reprovadas).
3. `20260731_sota_analise_estatica_compose.md` — *o que o mundo faz*, e a opção que isso reabriu.
4. `20260803_compose_identidade_composable_design.md` — *como* essa opção seria construída (D1/D2/D3, E1).
5. `20260803_compose_d1_decisao_plano_rearch.md` — *qual* desenho foi escolhido e como se encaixa na rearquitetura.
6. **este** — *o E1 rodou*: o que ele mediu, e os dois pontos em que os documentos 4 e 5 estavam errados sobre a mecânica de injeção.

---

## 1. Sumário executivo

O E1 perguntava uma coisa binária — *a informação de fonte do Compose chega ao runtime, e a que custo?* — com poder de refutação total sobre D1, D2 e D3. Ele rodou em 2026-08-06 sobre `dev.itsvic.parceltracker_10501000.apk`, e a resposta é:

1. **A Via A funciona.** Registrando um `CompositionTracer` por `java.lang.reflect.Proxy` no campo estático `ComposerKt.compositionTracer`, o probe capturou **343 payloads distintos** em 30 s de exploração, cada um no formato `FQN (Arquivo.kt:linha)` — exatamente o payload rico que o desenho precisa. A rota de instalação que funcionou foi a do acessor sintético `access$setCompositionTracer$p`, o que confirma em execução a inferência do doc 4 §4.2 de que o campo sobrevive ao R8 e não é `final`.
2. **A Via B está morta, como o doc 3 previa.** `distinct=0` nos cinco snapshots, sem exceção, apesar de a Activity ter sido entregue ao probe e a caminhada custar 34–100 ms. A *side table* de `sourceInformation` está desligada por padrão desde o Compose 1.6.0, e este corpus não a religa.
3. **Os payloads casam com o lado estático por igualdade de string, sem normalização.** Dos payloads de runtime recuperados, **242 de 248 (97,6%)** têm correspondente exato entre os 2.302 extraídos do bytecode. Restringindo ao código do próprio app — que é o que a tabela `FQN → alcance` indexaria —, o casamento é **27 de 27, com zero payloads de runtime sem par estático**. A relação é de subconjunto perfeito.
4. **O custo é desprezível, e por um motivo estrutural, não por sorte.** 26 ms acumulados dentro do tracer em 14.374 chamadas — **~1,8 µs por composable**. E a *leitura* do estado é O(1): o tracer empurra a informação para um `Set`, então consultar "quais composables estão nesta tela" é ler uma estrutura em memória, não percorrer árvore alguma.

O ponto 4 merece destaque porque **muda o enquadramento do custo**. Os limiares de decisão do doc 4 §9 (~80 ms viável por passo, ~800 ms restringe a instantâneo por estado novo) foram herdados da trajetória do bitdrift, que mede `asTree()`/`mapTree()` — isto é, o custo de **percorrer a composição**, que é a Via B. A Via A não percorre nada. A pergunta "cabe no orçamento de decisão por passo?" nem chega a ser interessante: o custo por passo é uma leitura de `Set`.

**O que este documento não decide.** E1 aprovado não implica D1 viável. O risco registrado no doc 5 (fato novo 3) — saturação do alcance transitivo, `reachesTarget` = 96,1% contra `directlyReachesTarget` = 0,00% — segue intacto e é o gate da Fase 2. O E1 mostrou que a chave existe dos dois lados; não mostrou que ela discrimina.

---

## 2. O que efetivamente rodou

Quatro tentativas, e vale registrar as três primeiras porque cada uma queimou uma hipótese.

| # | Nome do run | Desfecho | O que ensinou |
|---|---|---|---|
| 1 | `e1_compose_probe` | emulador não bootou em 300 s | orçamento de boot insuficiente sob contenção, não defeito (§6.1) |
| 2 | `e1_compose_probe_t2` | app rodou, só `attach` disparou | o `boot` em `<clinit>` **nunca foi tecido** (§5.1) |
| 3 | `e1_compose_probe_t3` | Via A funcionou, sem dump | snapshots até 40 s; o dump de payloads estava agendado para 80 s e o run abortou aos 51 s |
| 4 | `e1_compose_probe_t4` | **completo** | dump antecipado para 10/20/30 s; é o run reportado aqui |

Nas quatro tentativas o `rv-experiment` geriu o emulador integralmente, conforme a regra permanente. O ambiente estava sob a campanha `cmp163` em 8 containers — 2.505% de CPU só em qemu, *load average* 67 em 64 núcleos —, o que é a origem tanto do boot lento quanto dos abortos de exploração (§6.2).

O procedimento, em duas etapas:

```bash
# 1. injeção offline no APK ORIGINAL (não no do corpus, que já traz classes10.dex com monitores)
java -jar modules/rv-instrumentation-dexlib2/lib/instr-cli.jar instrument <apk-original> \
  --descriptor <E1>/ComposeProbeAspect.json --monitor-src-dir <E1>/monitor-src \
  --no-coverage --output <E1>/out --work-dir <E1>/work \
  --keystore modules/rv-instrumentation/assets/keystore.jks \
  --keystore-pass password --key-alias server --key-pass password

# 2. execução pela plataforma, com o par APK + .apk.json do corpus
RV_EMULATOR_BOOT_TIMEOUT=1800 RV_ADB_CMD_TIMEOUT=60 RV_APK_INSTALL_TIMEOUT=1200 \
uv run rv-experiment run --name e1_compose_probe_t4 --tools monkey --apks-dir <E1>/run \
  --skip-monitors --skip-instrument --skip-static --timeouts 120 --repetitions 1
```

Artefatos preservados em `backup/e1-compose-probe/` (gitignored): descritor, probe, logcat do run 4, payloads de runtime e a extração estática.

---

## 3. Via A: os números

Cinco snapshots no *main looper*, contados a partir da instalação do tracer:

| t | FQNs distintos | chamadas ao tracer | ms acumulados no tracer | µs/chamada |
|---:|---:|---:|---:|---:|
| 2 s | 181 | 388 | 3 | 7,7 |
| 5 s | 305 | 2.131 | 6 | 2,8 |
| 10 s | 326 | 4.256 | 8 | 1,9 |
| 20 s | 332 | 7.525 | 18 | 2,4 |
| 30 s | **343** | **14.374** | **26** | **1,8** |

Três leituras:

**A instalação pegou a primeira composição.** 181 FQNs distintos já aos 2 s. Isso importa porque a guarda `isTraceInProgress()` é avaliada *dentro* do corpo de cada composable: um tracer instalado tarde demais não veria nada até a primeira recomposição, e "instalado tarde" seria indistinguível de "a via não funciona". O sítio de costura escolhido (§5.2) garante a ordem.

**O custo por chamada cai com o volume**, de 7,7 µs para 1,8 µs — é o perfil normal de JIT aquecendo. O número a citar é o assintótico, 1,8 µs.

**A curva de descoberta satura, e isso é sobre a exploração, não sobre a via.** De 326 (10 s) a 343 (30 s) são 17 FQNs novos enquanto as chamadas quase quadruplicaram: o monkey estava recompondo as mesmas telas. O que limita a cobertura é o explorador, não o mecanismo.

---

## 4. Via B: reprovada em execução, como previsto

`distinct=0` nos cinco snapshots, com a Activity presente (`attach: activity=dev.itsvic.parceltracker.MainActivity`) e a caminhada custando 34–100 ms. Não é falha de acoplamento: o probe chegou ao ponto de percorrer e não havia grupos com `sourceInfo` para ler.

Isso confirma em execução o que o doc 3 §5.2 levantou a partir da documentação: a *side table* que alimenta `CompositionData.sourceInformation` está desligada por padrão desde o Compose 1.6.0. O corolário de desenho é que **a família incondicional de strings, apesar de incondicional na emissão, não tem destino de runtime** — e portanto a única família utilizável é a rica, que era justamente a que parecia bloqueada. A inversão é completa em relação ao que os documentos 3 e 4 supunham como "a rota mais provável".

---

## 5. Duas correções à mecânica de injeção

Ambas são sobre o `rvsec-instrumentation-dexlib2`, não sobre Compose. Nenhuma foi consertada aqui.

### 5.1 `staticinitialization` sem Signature é descartado em silêncio

**Este é o ponto em que o doc 5 §11 e o doc 4 §11.2(c) precisam ser corrigidos, e a correção anda para trás.**

O doc 4 §11.2(c) afirmava que o alvo não cabia no descritor JSON e exigiria um weaver novo em Java. A emenda de 2026-08-06 ao doc 5 (§11) revogou isso: `staticinitialization(...)` tem casamento real por padrão de tipo em `PointcutMatcher.matchStaticInit` (`:517-529`) e um pré-passe dedicado em `DexWeaver.weaveStaticInit` (`:569-654`), logo a costura seria expressável no descritor e o E1 não precisaria de código novo no tool.

**A parte sobre o matcher está certa. A conclusão está errada**, porque o pré-passe tem uma guarda que nenhum dos dois documentos leu:

```java
// DexWeaver.java, dentro de weaveStaticInit
if (!StaticInitializationEmitter.deliversSignature(advice)) {
    // Non-Signature staticinit advice is out of §4.Y's scope;
    // skip rather than emit a malformed event.
    continue;
}
```

`deliversSignature` só é verdadeiro quando o advice passa exatamente um argumento e ele é o token `thisJoinPoint.getStaticPart().getSignature()`. O advice do E1 declarava `"args": []` — precisamente a forma que a emenda julgava barata —, então foi descartado.

A leitura que produziu o erro é compreensível e vale registrar como armadilha: `StaticInitializationEmitter.emit()` **de fato** trata advice sem Signature, caindo no `MonitorInvokeBuilder.buildInvoke` genérico. Só que esse caminho é inalcançável para este pointcut, porque o pré-passe o detém por inteiro — o próprio `DexWeaver:399` diz que *"staticinitialization(...) advice is owned entirely by"* o pré-passe. O emissor genérico é código morto para `staticinitialization`.

**O agravante é o silêncio.** O descarte não incrementa `plansSkipped`, não incrementa `plansSkippedUnresolvedBinding`, não emite WARN. A injeção reportou `success=true` com `advices=2, matchesApplied=5, plansSkipped=0` — indistinguível de uma costura perfeita. Só a desmontagem do `<clinit>` do `MainActivity` revelou que o `invoke-static` do `boot()` não estava lá, e nem em lugar nenhum do APK. Um contador ou um WARN teria poupado uma tentativa inteira.

### 5.2 A saída, que é melhor do que a costura original

O advice sobrevivente — `call(...setContent$default(...)) && args(act, ...)` — é `"position": "before"`. Ele executa **antes** da chamada a `setContent`, e portanto antes da primeira composição, que é toda a garantia de ordem que o `<clinit>` fornecia. Bastou chamar `boot()` de dentro de `attach()`.

Duas observações de valor durável:

- **O advice de `call` não era "melhor-esforço".** O README do probe e o doc 4 tratavam-no como frágil (risco de parser no `$default`, binding possivelmente não resolvido). Ele casou, resolveu o binding e entregou a Activity: `plansSkippedUnresolvedBinding=0`, e o log confirma. A ressalva era pessimista.
- **O `<clinit>` nunca foi necessário.** A justificativa para preferi-lo era a ordem em relação à primeira composição, e o `before` sobre o `call` a satisfaz igualmente. Se um dia a rota de `staticinitialization` for aberta (dando Signature ao advice, o que exige `org.aspectj.lang.Signature` no classpath do `javac` do `MonitorBuilder`), ela não traz vantagem para este uso.

### 5.3 `--no-coverage` não desliga o coverage

A flag existe, é `negatable`, e é propagada até `BatchRunner` (`InstrumentationCli:98` → `EffectiveConfig:22` → `ConfigResolver:82` → `BatchRunner:197,327`). Ainda assim, com `--no-coverage` o resultado traz `coverageInstrumented=9559`, e o `CoverageSourceEmitter` escreveu `Coverage.java` e `MonitorWrappers.java` **dentro** do diretório passado em `--monitor-src-dir`.

Para o E1 isso foi tolerável — o probe compilou e foi dexado do mesmo jeito —, mas tem dois efeitos que num experimento de custo não seriam inócuos: acrescenta 9.559 sítios instrumentados ao app medido, e polui um diretório de fonte que o chamador considera seu. Merece issue própria.

---

## 6. Ameaças à validade

### 6.1 O ambiente estava saturado

A campanha `cmp163` ocupava 8 containers durante todo o E1. Efeitos observados e como cada um foi tratado:

- **Boot do emulador**: 5 min 35 s contra o orçamento padrão de 300 s. Resolvido com `RV_EMULATOR_BOOT_TIMEOUT=1800`. Não é defeito do sistema — a prova é que o `adb emu kill` da tentativa 1 teve sucesso, ou seja, o device já estava alcançável no instante em que o orçamento estourou.
- **Abortos da exploração**: as três execuções que chegaram a rodar terminaram com `System appears to have crashed`, entre 51 s e 65 s. A causa registrada no trace é ANR de `com.google.android.gms.persistent` sob pressão de memória — **não** do app sob teste, e não do probe.
- **Efeito nos números de custo**: a contenção só pode ter **inflado** os tempos. Um custo medido de 1,8 µs/chamada sob *load* 67 é um teto; a medida em máquina livre seria menor. Como a conclusão é "desprezível", o viés é conservador e a conclusão sobrevive. Se algum número desta série for reusado como orçamento fino, refazer com a máquina ociosa.

### 6.2 O logcat descartou linhas do dump

O snapshot de 30 s reportou `total=343`, mas a recuperação por `grep` sobre o arquivo salvo rendeu 248 payloads únicos somando os três dumps. A diferença é descarte do próprio logcat sob rajada — o probe emite uma linha por payload e o buffer limita.

Isso **não** afeta a conclusão de casamento, e é importante ser preciso sobre por quê: a métrica que decide é "existe payload de runtime **sem** correspondente estático?", e a resposta foi **zero no código do app**. Descartar linhas só pode esconder casamentos, nunca inventar divergências. O que a perda afeta é a contagem de cobertura (quantos dos 104 foram exercitados), que não é critério de E1.

### 6.3 Um APK, não uma amostra

O E1 é de refutação, não de estimativa: um único app bastava para derrubar a via, e bastou para mostrá-la viável. Generalizar a **prevalência** exige a varredura que o doc 4 §4 já fez no lado estático (174/174 com informação de fonte) mais um piloto de runtime em N apps, que é a Fase 1 do plano do doc 5.

### 6.4 O corpus é F-Droid

O casamento depende de os nomes `androidx.compose.runtime.ComposerKt` e do acessor sintético sobreviverem ao R8. Sobreviveram aqui, e o doc 4 mediu 174/174 no corpus. Num app com ofuscação agressiva de bibliotecas isso pode não valer, e qualquer texto de tese que reporte a cobertura deve dizer que a premissa é do corpus, não do ecossistema.

---

## 7. O que isto libera

**Do plano do doc 5 §7**, a Trilha A (E1 + piloto offline) tem sua primeira etapa cumprida. O gate seguinte é a **Fase 2**, e ele é independente deste resultado: construir a tabela `FQN → {reaches, minHops}` para uma amostra e verificar se ela discrimina, ou se reproduz a tautologia do `activityHasMop` um nível abaixo. O doc 5 já antecipou que a tabela precisa ser **graduada, não booleana**, exatamente por causa desse risco.

**Nada muda no gator agora.** A extração do lado produtor (doc 4 §10) continua na Fase 3, depois do piloto, e continua custando a re-análise dos 348 APKs. A regra de não mexer no gator não foi tocada por este experimento — o E1 não tocou o gator, não tocou o APE-RV e não exigiu revogar nenhuma decisão de governança, exatamente como projetado.

**O que mudou de estatuto** é a §16 do doc 4 ("se E1 falhar"): ela não vira texto de tese. O resultado negativo da série continua valendo para tudo o que os documentos 1–3 reprovaram — join por resource-id, por texto, por saco de textos, por `testTag` —, mas a identidade de composable sobrevive como a única chave que existe integralmente dos dois lados, e agora isso está medido em execução, não inferido.

---

## 8. Método e reprodutibilidade

- **APK**: `dev.itsvic.parceltracker_10501000.apk`, original (não o instrumentado do corpus).
- **Probe**: `backup/e1-compose-probe/monitor-src/mop/ComposeProbeRuntimeMonitor.java` — reflexão pura, sem referência de compilação a `androidx.compose.*`, `CompositionTracer` implementado via `java.lang.reflect.Proxy`.
- **Descritor**: `backup/e1-compose-probe/ComposeProbeAspect.json`. O advice `ComposeProbe_boot` permanece no arquivo e permanece inerte — deixado como registro do descarte silencioso da §5.1.
- **Extração estática**: desmontagem por `apktool d --no-res`, depois `grep -B4 "ComposerKt;->traceEventStart"` filtrando `const-string`. Rendeu 2.302 payloads, dos quais **104 do próprio app** — número idêntico ao que o doc 4 §4.3 registrou por outro caminho, o que serve de verificação cruzada da extração.
- **Cruzamento**: `comm -12` / `comm -23` com `LC_ALL=C sort -u` dos dois lados.
- **Tag de logcat**: o probe emite sob a tag `RVSEC` com prefixo `E1 `. Isso não é cosmético — a captura da plataforma é uma *whitelist* de tags (`RVSEC:V RVSEC-COV:V ApeRvHb:V AndroidRuntime:E art:E dalvikvm:E ActivityManager:W`), e a tag original `RVSEC-E1` era descartada do arquivo `.logcat` salvo. Qualquer instrumentação futura que precise aparecer nos artefatos tem de usar uma tag da lista.

---

## 9. Documentos relacionados

- `20260803_compose_identidade_composable_design.md` — §9 (o desenho do E1), §11.2(c) (corrigida aqui, na §5.1).
- `20260803_compose_d1_decisao_plano_rearch.md` — §7 (o plano em trilhas), §11 (a emenda corrigida aqui, na §5.1).
- `20260731_verificacao_analise_percepcao.md` — §1.2, a verificação adversarial que estabeleceu que o colapso MOP em Compose é `flagged=0` no GATOR, não `resource-id`, e que por isso a chave observável em runtime é a única rota disponível.
