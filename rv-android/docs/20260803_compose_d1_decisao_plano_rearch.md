# Decisão: D1 (sinal por tela) e plano de integração com a rearquitetura do APE-RV

**Data**: 2026-08-03
**Escopo**: registro da decisão entre os três desenhos de `20260803_compose_identidade_composable_design.md` (D1/D2/D3), das verificações em código que a sustentam, das correções que essa verificação impôs ao próprio design doc, e do plano de implementação integrado às sete changes `rearch-*` do repositório `ape`.
**Status**: decisão de planejamento. **Nada foi implementado.** A decisão permanece condicionada ao experimento E1 (design doc, §9) — este documento fixa *o que* será construído se E1 passar e *onde* cada peça se encaixa, não antecipa o resultado de E1.

**Quinto de uma série** sobre gator × Compose:

1. `20260730_compose_gator_substrato_estatico.md` — *por que* a WTG colapsa (diagnóstico).
2. `20260731_gator_compose_viabilidade.md` — *o que dá para fazer* no desenho atual (quatro vias reprovadas).
3. `20260731_sota_analise_estatica_compose.md` — *o que o mundo faz*, e a opção que isso reabriu.
4. `20260803_compose_identidade_composable_design.md` — *como* essa opção seria construída (D1/D2/D3, E1).
5. **este** — *qual* desenho foi escolhido, *o que a verificação corrigiu* no doc 4, e *como* o plano se encaixa na rearquitetura do APE-RV.

**Emenda posterior**: a §11 (2026-08-06) corrige a §3 deste documento e a §11.2(c) do doc 4 — a costura do E1 é expressável no descritor, e o hook tem de ser em `<clinit>`, não em `onCreate`. Nenhuma conclusão de desenho muda, e **o E1 continua sem rodar**.

**Emenda de 2026-08-06, à noite — o E1 rodou, e a emenda acima estava errada na mecânica.** Ver `20260806_compose_e1_resultado.md` (sexto da série). Dois pontos: (a) a costura por `<clinit>` **não** é expressável no descritor — o pré-passe `DexWeaver.weaveStaticInit` descarta, sem contador e sem WARN, todo advice `staticinitialization` que não entregue o token `thisJoinPoint.getStaticPart().getSignature()`, e o advice do E1 declarava `args: []`; (b) isso não custou nada ao desenho, porque o advice `before` sobre `call(setContent$default)` já precede a primeira composição, que era a única razão de preferir o `<clinit>`. **O resultado**: a Via A passou — 343 FQNs distintos em runtime, casando com a extração estática por igualdade de string, a ~1,8 µs por composable; a Via B ficou em `distinct=0`, como o doc 3 previa. O gate da Fase 2 (saturação do alcance transitivo, §6) segue aberto e não foi tocado.

**Método desta sessão**: três verificações independentes de escopo disjunto — (a) as sete changes `rearch-01..07` lidas por completo (proposal, design, tasks, delta specs, ~7.200 linhas); (b) o consumidor APE-RV (`MopData`, `MopScorer`, passes, `GUITreeBuilder`, `StatefulAgent`, `ApePromptBuilder`, `Config`, e a varredura de todos os canais de arquivo em runtime); (c) o produtor rvsec (pipeline `dexlib2`, gancho no gator, writer/parser do `.apk.json`, e os vereditos dos docs 1–3 reconferidos). Mais a incorporação de `20260731_verificacao_analise_percepcao.md`, que o doc 4 não consumiu.

---

## 1. Sumário executivo

**A opção escolhida é a D1 — sinal por tela, sem o segundo join —, condicionada ao E1.** D2 fica como extensão futura apenas se D1 mostrar valor na Fase 2 *e* os três elos de API do J2 forem verificados; D3 está descartado como desenho (efeito observador), mas uma variante mínima dele reaparece como candidata a **canal** (§5.2), por ironia da própria rearquitetura.

Quatro fatos novos desta sessão refinam o design doc:

1. **D1 não é mais "a melhor opção" — é a única rota.** A verificação adversarial (`20260731_verificacao_analise_percepcao.md`, §1.2) corrigiu a causa do colapso MOP em Compose: não é o `resource-id`, é o GATOR entregando `flagged=0` em 22/22 apps. O conserto no substrato estático de widgets permanece vetado pela regra do gator; a chave de junção observável em runtime "passa de uma alternativa entre duas para a única rota disponível" (item D6 daquela verificação). A série e a verificação adversarial, por caminhos independentes, convergem na mesma via.
2. **O canal proposto na §13 do design doc morre na rearquitetura.** A change `rearch-02-runspec` deleta o mecanismo `xPathlets` inteiro e cria o invariante INV-RUN-06 (o jar não lê input comportamental de `/sdcard` além de `ape.properties`). O "molde do `applyXPathlets`" deixa de existir e fica normativamente proibido. A decisão de canal é reaberta (§5.2) — e pode esperar até a Fase 4.
3. **Existe um risco de valor que o design doc não registra: saturação do alcance transitivo.** `reachesTarget` = 96,1% entre métodos `@Composable` e `directlyReachesTarget` = 0,00% (doc 1, §4.3, reconfirmado). Uma tabela `FQN → bool` pode ser quase-constante 1 — a mesma tautologia do `activityHasMop`, um nível abaixo. Isso muda o formato da tabela (graduada, não booleana) e o gate da Fase 2 (§6).
4. **O momento é excepcionalmente favorável.** As sete changes `rearch-*` têm **zero tarefas concluídas** (verificado em 2026-08-03). As costuras Compose podem ser antecipadas por edição de spec, ao custo de ~10 linhas cada, antes de qualquer código existir — depois, cada uma custa um bump de schema, uma emenda de invariante ou retrabalho de parser.

O plano tem três trilhas (§7): **A** — E1 e piloto offline, imediatos e 100% paralelos à rearquitetura (só tocam rvsec/rv-android); **B** — três antecipações de spec nas changes `rearch-02/04/07`; **C** — o consumidor como `rearch-08-compose-screen-signal`, depois da etapa 7.

---

## 2. A decisão, e o que a sustenta

### 2.1 Por que D1

O argumento é de ordem de refutação e de honestidade sobre qual problema existe:

- **D1 depende de um fato não verificado** (E1: a informação de fonte chega ao runtime). **D2** depende desse fato mais três elos de API do J2 (composição → `LayoutNode` → `SemanticsNode.id` → nó de acessibilidade), nenhum verificado em execução. **D3** depende de tudo isso mais reescrita da árvore de acessibilidade do app sob teste — num experimento cujo desfecho é contagem de violações, o efeito observador é uma ameaça à validade quase eliminatória.
- **D1 ataca o problema que existe.** O impulso por widget mede 0 de 629.417 em Compose (doc 2, §2); restaurá-lo (D2/D3) é restaurar um mecanismo de valor especulativo nesse estrato. A falta de contraste no sinal por estado é o problema medido — e D1 é a intervenção com hipótese falseável mais barata.
- **O estrato Compose custa poder estatístico ao experimento inteiro.** Os 22/22 apps Compose são binário-concordantes entre os braços `aperv` (verificação de percepção, §1.1.1; confirmado pela corrida decisiva de 2026-08-02): 55% do corpus não contribui um único par discordante para o desfecho primário, e o McNemar exige ≥7. D1 é o único mecanismo em cima da mesa capaz de *criar contraste* nesse estrato. Este é o argumento de tese, mais forte que "sinal mais granular".

### 2.2 O que D1 entrega — com a correção do consumidor

A verificação do consumidor corrigiu uma premissa do design doc: **`activityHasMop` não entra na pontuação de ações hoje.** `MopScorer` é discriminative-only por decisão registrada (`MopScorer.java:50-54`: um boost uniforme por estado "shifted every candidate equally and could not re-rank them" — a objeção formal que qualquer proposta de sinal por tela tem que responder). O sinal por activity existe como predicado (4 sítios), como piso de `stateMopDensity` (tiebreaks de navegação) e como telemetria.

Consequência: **um `ScoringPass` novo com boost uniforme por tela seria no-op de re-ranking.** O valor de D1 entra por onde um sinal por estado realmente age:

| Encaixe | Onde | Efeito |
|---|---|---|
| Predicado `screenHasMop` no lugar de `activityHasMop` | `MopScorer.java:117` (`scoreWtg`), `:147` (`stateMopDensity`), `MopFrontierPass.java:115`, `SataAgent.java:345` | recupera discriminação onde a união A′ satura (constante 1 em 30% dos apps Compose) |
| Termo em `stateMopDensity` | `MopScorer.java:142-173`; consumidores em `SataAgent.java:1221-1234` e `:1472-1487` | **o único lugar onde sinal por estado re-ranqueia de fato** — tiebreaks comparam estados entre si, não ações dentro de um estado. Em Compose hoje a densidade é o piso `1` em toda tela |
| Contexto por tela no prompt do LLM | `ApePromptBuilder.buildExplorationContext` (`:560-605`) | corrige o `0/n MOP.` invariável em Compose — sinal hoje **ativamente enganoso** para o LLM |
| Seam F′ de roteamento adaptativo | `Config.llmPercentageNoSubstrate` (`Config.java:208-213`, sem consumidor) | D1 é o mecanismo que o preenche (§5.4) |
| Telemetria por estado | registro `STATE` do NDJSON (rearch-04) | `STATE.mop` + lista de composables ativos — atribuição por canal offline |

Se além do conjunto de FQNs o probe expuser estrutura (qual composable alcança qual), o precedente arquitetural para boost dirigido é o `MenuGatewayPass` (`MenuGatewayPass.java:35-51`): sinal de tela → boost de um **tipo** de ação, aceito no desenho vigente. O short-circuit determinístico (`SataAgent.selectUnvisitedMopTarget:700-712`) lê exclusivamente `mopBoost` por ação — um sinal puramente por estado nunca o dispara, e isso fica registrado como limite conhecido de D1, não como defeito.

### 2.3 O que D1 abre mão

O impulso por widget. Ele mede 0/629.417 no estrato Compose — não se abre mão de um efeito existente. Se a Fase 2 mostrar valor e houver apetite pelo D2, o caminho está descrito no design doc (§7, D2) e depende dos três elos de J2, a verificar em execução antes de qualquer decisão.

---

## 3. O que a verificação em código confirmou (lado produtor)

Todas as afirmações mecânicas do design doc §11 conferem com o código atual — e o E1 é **mais barato** do que o doc estima:

- **Injeção sem mudança estrutural**: `MonitorBuilder.java:69-76` compila qualquer `.java` em `--monitor-src-dir` sem filtro; `MultidexMerger.java:126-132` anexa em `classes<N>.dex`; repack/assinatura inalterados. O d8 não arrasta `android.jar` para o dex (`:104-128`) — correto para um probe reflexivo.
- **Weaver seletivo**: `CoverageWeaver.java` é o molde exato (o par `CONST_STRING` + `INVOKE_STATIC` em `:181-190`; o spill de registradores historicamente perigoso já resolvido em `RegisterShifter.java:610`, reutilizável sem cópia). O `InheritanceResolver` já construído em `BatchRunner.java:191-195` responde "é subtipo de `android.app.Activity`?". Confirmado que o descritor JSON **não** expressa o alvo (`PointcutMatcher.java:509-515` ignora o `TypePattern` de `execution`; `within` é always-match em `:134-137`) — o weaver tem que ser Java. **Superado pela emenda da §11**: `staticinitialization` expressa o alvo, e o weaver Java deixa de ser necessário para o E1.
- **Custo real do E1**: `ComposeProbe.java` (~80 linhas reflexivas) + `ComposeProbeSourceEmitter` (~70, cópia de `CoverageSourceEmitter`) + `ComposeProbeWeaver` (~150) + ~15 linhas em 4 arquivos do CLI (`InstrumentationCli`, `EffectiveConfig`, `ConfigResolver`, `BatchRunner:197/:280/:328`). **Para E1, o wrapper Python é dispensável**: invocar o fat jar diretamente com `--no-coverage` (flag negável existente) — o único requisito irredutível é um descriptor JSON válido (`BatchRunner.java:132-135` falha sem ele). A flag definitiva `--compose-probe` entra depois, via CLI e não via env var (`_build_subprocess_env` só repassa cinco variáveis, INV-EXP-30). **Revisado para baixo pela §11**: um `.json` e um `.java`, sem nada do lado do tool.
- **Dois refinamentos técnicos** sobre o design doc: o hook deve ser em **`onCreate`** (Compose típico sempre o sobrescreve para chamar `setContent`; `onResume` pode não existir na subclasse), e o probe precisa **adiar a primeira leitura** (`postDelayed`/`Choreographer`) — em `onCreate` a primeira composição ainda não existe. **O primeiro refinamento está corrigido na §11.2**: para a Via A, `onCreate` é tarde demais. O segundo continua válido e é o que absorve a antecipação.
- **Varredura no gator**: estritamente análoga às existentes. `scanInvokesInAppClasses` (`RvsecAnalysisClient.java:513-556`) entrega a `InvokeExpr` inteira ao visitor; precedentes de leitura de `StringConstant` (inclusive com back-track de atribuição) em `MenuExtractor.java:208-209` e `SpinnerItemExtractor.java:253-280`. Detalhe de assinatura: em `traceEventStart(int,int,int,String)` a string é `getArg(3)`.
- **Achado colateral de qualidade**: as seções do `.apk.json` são escritas com string literais, não com `JsonSchema.Keys` — o teste de paridade INV-ANA-32 valida `Keys ↔ _JK`, mas não garante que o writer emita esses nomes. A seção nova deve usar as `Keys` e entrar no bloco barato (logo após `components`), para não ser perdida por timeout de WTG.

---

## 4. Correções ao design doc (doc 4)

Quatro pontos do doc 4 estão superados ou incompletos. **O doc 4 permanece válido como desenho técnico**; estas correções valem a partir deste documento.

**4.1 — O canal da §13 morre na rearch-02.** A §13 aponta `applyXPathlets` (`GUITreeBuilder.java:89-125`) como "o ponto de extensão de menor atrito". A change `rearch-02-runspec` (design D-9) deleta `xPathlets`, `XPathletReader`, `XPathActionController` e o pacote `ape.model.xpathaction`, e normatiza a proibição: INV-RUN-06 ("o jar não lê input comportamental de `/sdcard` além de `ape.properties`") e o requisito "No XPathlet Overlay Input" na spec de `ui-tree` ("nenhum input de filesystem participa da construção da árvore"). Além disso, a verificação do consumidor mostrou que o molde já era mais fraco do que a §13 sugere: a leitura do `ape.xpath` é one-shot em bloco `static{}` (não por passo) e o reader mata o processo em erro de parse (`XPathletReader.java:53-59`, `System.exit(1)`). Ver §5.2 para as saídas.

**4.2 — A change `telemetry-proof-llm-efficacy` não está mais aberta.** O doc 4 (§17, §20) a cita como "change aberta do APE-RV". Ela foi **arquivada em 2026-08-02** (`ape/openspec/changes/archive/2026-08-02-telemetry-proof-llm-efficacy/`) e a linha de governança "exclui do escopo anything in rvsec-gator" migrou de fato para a série `rearch-*`. As correções da verificação de percepção (338/800, o hook que recupera zero, D9 retificado) **já foram absorvidas** pelos artefatos arquivados e pela própria rearquitetura (`ape/docs/20260802_verificacao_consistencia_rearch.md` registra a realocação dos requisitos).

**4.3 — A premissa sobre o consumo do sinal por estado estava imprecisa.** Ver §2.2: `activityHasMop` não participa da pontuação; o desenho do consumidor de D1 é predicado + densidade + prompt + seam F′, não um passe de boost uniforme.

**4.4 — `stateMopDensity` em Compose retorna 1, não 0.** O piso `1 + count` (`MopScorer.java:172`) é alcançado porque `activityHasMop` é verdadeiro em todos os 22 apps Compose (`mopActivities` entre 2 e 9, via A′). O sinal por estado existe e está *saturado no piso* — exatamente o que D1 substitui. (Correção herdada da verificação de percepção, que o doc 4 não consumiu.)

---

## 5. Encaixe na rearquitetura do APE-RV

As sete changes (`rearch-01-parity-oracle` … `rearch-07-compact-static-artifact`, todas de 2026-08-02, implementação prevista em branch `rearch` única com merge após a etapa 7) tocam exatamente os pontos onde D1 se pluga. Estado verificado em 2026-08-03: **zero tarefas concluídas em todas**.

### 5.1 O mapa de contato

| Change | O que muda (relevante a D1) | Efeito sobre D1 |
|---|---|---|
| 01 parity-oracle | goldens de decisão, test-only; INV-ORA-07 congela goldens durante 02/03 | **janela proibida**: nada de Compose entre 01 e 03. Depois, D1 exige regeneração deliberada de goldens + preset/cenário `compose` novo |
| 02 runspec | `RunSpec`/`Feature`/fail-fast; **deleta o canal da §13** (INV-RUN-06) | precisa da `Feature COMPOSE` declarada (senão o teste de totalidade de chaves bloqueia qualquer `ape.compose*` futuro); reabre a decisão de canal |
| 03 decision-pipeline | stages; `ScoringPipeline.fromParams`; pesos por `ScoringParams` (INV-ARCH-11) | passe/predicado Compose fica **mais fácil depois** (injeção real, testável sem mutar `Config`); roster "seven passes" exige emenda para um oitavo |
| 04 step-ndjson | um `StepRecord` por passo; `activity_has_mop` vira fato estático em `ACT.mop`; **INV-SEL-06 amarra o bit à activity** | o sinal por tela entra no registro `STATE` (`mop` + `comp[]` + dicionário `COMPOSABLE`); INV-SEL-06 tem que ser reescrito — a redação atual **proíbe** o refinamento por tela |
| 05 thin-python-arms | arms declarativos; INV-APV-44 exige diff vazio por arm durante a migração | **janela proibida** para arm novo; depois, um arm Compose é `{preset, overrides}` trivial |
| 06 memory-surgical | disciplina de caches do `GUITreeBuilder` (INV-TREE-13) | qualquer cache Compose por árvore/nó **depois** de 06 adere à disciplina; antes, recria o vazamento que 06 corrige |
| 07 compact-static-artifact | `MopData` reescrito (1212 → ≤450 LOC); artefato compacto `formatVersion: 1` gerado no host; deleta `isWidgetlessSubstrate()` | a tabela de composables **pertence ao schema compacto** (INV-DRV-06 proíbe chaves `*Target` e call-graph no wire); parsing Compose escrito no `MopData` atual seria deletado na etapa 7 |

**A rearquitetura já sabe do problema e está internamente inconsistente sobre ele** — três peças que a proposta Compose deve reconciliar: as specs de llm-routing (rearch-03/04) reconhecem "Compose trees that expose no meaningful widget class name at all" (único reconhecimento explícito de Compose em ~7.200 linhas); a rearch-02 mantém o seam `llmPercentageNoSubstrate` justificado por "F′ vai ler `isWidgetlessSubstrate()`"; e a rearch-07 **deleta** `isWidgetlessSubstrate()`, deixando como substituto apenas `stats.widgetsTotal`. D1 é o preenchimento da lacuna que as próprias changes sinalizam.

### 5.2 A decisão de canal (reaberta, adiável até a Fase 4)

Com o molde da §13 morto, as saídas para o canal probe → APE-RV são:

1. **Escrita mínima na árvore de acessibilidade** — o probe publica o conjunto de FQNs ativos como propriedade de um nó sentinela do `ComposeView` (semantics). Satisfaz a spec pós-rearch-02 literalmente ("a árvore deriva somente de `AccessibilityNodeInfo`"), não cria canal novo nem IPC. Custo: é uma escrita na UI do app sob teste — fração do risco de D3 (um sentinela, não identidade por widget) — e exige excluir o sentinela da abstração de estado e do conjunto de ações, senão cada tela vira estado novo.
2. **Emenda explícita a INV-RUN-06** — arquivo dinâmico lido por estado novo, com a disciplina de erro do `MopData.load` (nunca propaga, retorna nulo, emite status) e handshake por contador monotônico contra a corrida probe-assíncrono × snapshot da árvore. É revogação de invariante publicada, negociada como tal — não "reaproveitamento de molde".
3. **Logcat — proibido**, reafirmado em duas specs (`action-selection` e `mop-guidance` da rearch-07).

**E1 e a Fase 2 não precisam de canal** (o probe mede a si mesmo; o piloto é offline). A escolha fica registrada como questão aberta da change da Fase 4, com a opção 1 como hipótese preferida e o custo de validade (efeito observador do sentinela) explicitado no braço de controle.

---

## 6. O risco novo: saturação do alcance transitivo

`reachesTarget` = **96,1%** entre métodos `@Composable`; `directlyReachesTarget` = **0,00%** (doc 1, §4.3; reconfirmado pela verificação adversarial). Consequências:

- Uma tabela `FQN → bool` transitiva pode ser quase-constante 1 — a tautologia do `activityHasMop` reproduzida um nível abaixo. O *conjunto* de composables por tela ainda discriminaria telas entre si, mas o *predicado* "esta tela tem MOP" pode não ter contraste.
- A gradação `none|direct|transitive` é vazia na prática: `direct` é 0% no corpus (composables não chamam JCA diretamente; o fluxo passa por viewmodels/camadas de domínio).

**Mitigação, incorporada ao plano**: a tabela é **graduada** — `fqn → {reaches: bool, minHops: int}` (distância mínima no call graph até o alvo) ou `fqn → [classes-alvo]` — e o gate da Fase 2 é reescrito para medir a distribuição antes de declarar valor:

> **WHEN** nos ~5 APKs do piloto o conjunto de FQNs ativos difere entre telas da mesma activity
> **AND** um corte sobre o sinal graduado (min-hops ≤ k, ou densidade por tela) separa ≥2 classes de tela em ≥1 app onde `activityHasMop` é constante 1
> **THEN** D1 tem valor demonstrado e a Fase 3 se justifica.
>
> **WHEN** >90% dos composables de toda tela alcançam alvo sob qualquer corte testado
> **THEN** o sinal booleano está saturado; se nem o graduado discriminar, D1 morre por falta de valor — com E1 aprovado ou não — e o resultado entra na série como medição, não como plano abandonado.

### 6.1 Emenda de 2026-08-07: o que é derivável, e o que o pré-gate offline já mostra

Duas correções à mitigação acima, ambas medidas.

**`minHops` não é derivável do artefato existente.** A Fase 2 da Trilha A promete a tabela graduada "por script sobre o dex + `reachability[]` existente", sem tocar o gator. Isso vale para a densidade, não para `minHops`. O `.apk.json` carrega, por método, exatamente cinco campos — `name`, `signature`, `reachable`, `reachesTarget`, `directlyReachesTarget` —, todos booleanos: não há contagem de hops nem lista de classes-alvo. Das três gradações consideradas, só a **densidade por tela** sai do que já existe; `minHops` e `[classes-alvo]` são mudança de produtor, sujeitas à regra do gator.

O consolo é que a mudança é mínima *em computação*. O `ReachabilityEngine` já inverte o grafo e roda BFS multi-fonte a partir dos alvos (`multiSourceBfs`, `RvsecAnalysisClient.java:417-441`), e **`minHops` é exatamente a camada em que a BFS visita o método** — trocar o `Set<V> visited` por um `Map<V,Integer>` de distâncias dá o valor na mesma passada, mesma complexidade. O booleano de hoje é essa informação calculada e descartada (`reachesTarget` ≡ `minHops < ∞`; `directlyReachesTarget` ≡ `minHops == 1`). O custo é de governança, não de CPU — e o `int` ainda teria de caber no schema compacto da rearch-07, cujo INV-DRV-06 proíbe chaves `*Target` e call-graph no wire.

**A densidade — a única variante barata — quase reprova no pré-gate.** Tela não existe offline, então o proxy é a classe declarante (composable de topo compila para `<Arquivo>Kt`, logo classe ≈ arquivo ≈ tela). O proxy é assimétrico e é por isso que vale: se em toda classe 100% dos composables alcançam alvo, então toda tela — subconjunto de composables de uma ou mais classes — também está em 100%, e a densidade não pode discriminar. Sobre 7.743 classes com ≥3 composables em 116 apps Compose:

| | classes | |
|---|---:|---|
| em 100% (saturadas) | 6.964 | **89,9%** |
| em 0% | 200 | 2,6% |
| parciais (0<f<1) — onde a gradação viveria | 579 | **7,5%** |

Mediana por app: **93% das classes em 100%**. Em **26 dos 116 apps (22,4%) toda classe está em 100%** — ali a refutação é estrita. Só **18 de 116 (15,5%)** têm ao menos 20% das classes fora da saturação.

E há um agravante estrutural: uma tela compõe composables de **várias** classes, então a densidade por tela é uma média sobre o conjunto ativo. Média sobre um universo em que 90% dos itens valem 1 puxa quase toda tela para perto de 1 — **agregar reduz variância**, então a densidade por tela real tende a discriminar *menos* que este proxy. O número acima é o caso otimista.

**O que isto decide.** Sobre o substrato como ele existe hoje, a densidade herda a saturação da §4.3 do doc 1 e não escapa dela. Não decide o caso geral: a medição é feita sobre os mesmos dados suspeitos de saturação artificial, e as duas rodadas do doc 1 §6.5 não conseguiram estabelecer se a causa é artefato de análise. Se for, um grafo corrigido poderia produzir densidade discriminativa. A refutação é do substrato atual, não da ideia.

**Consequência para o plano**: se a Fase 2 rodar, o piloto não deve sortear ~5 APKs — deve olhar os 18 com massa não-saturada, que são o único lugar onde a densidade tem chance de mostrar contraste. E a variante que teria chance real de discriminar, `minHops`, deixou de ser "offline, não toca gator".

---

## 7. O plano, em três trilhas

### Trilha A — imediata, paralela à rearquitetura (só rvsec/rv-android)

| Fase | O que | Custo | Gate |
|---|---|---|---|
| **1 — E1** | probe reflexivo (vias A: tracer de `traceEventStart`; B: `CompositionData`) injetado em `dev.itsvic.parceltracker` via fat jar com `--no-coverage`; run pela plataforma (gestão de emulador é da plataforma, sem exceção) | 1 descritor `.json` + 1 `.java`, ambos descartáveis + 1 run (§11) | FQNs aparecem **e** leitura < ~80 ms (fallback: instantâneo por estado novo — encaixa no APE-RV, que tem o hook "1× por estado novo" em `registerScreenElements`) |
| **2 — Piloto D1 offline** | tabela graduada `FQN → {reaches, minHops}`, ~5 APKs; probe emite conjunto ativo por estado. **`minHops` não sai do `reachability[]` existente** — ver §6.1 | dias para a densidade; `minHops` **toca o gator** | o gate da §6, já parcialmente antecipado pela §6.1 |

Quando a Fase 2 iniciar, abrir issue GitHub + change `gh<N>-compose-screen-signal` neste repositório, pelas skills OpenSpec (convenção do projeto).

### Trilha B — antecipações nas changes `rearch-*` (edições de spec, agora)

Custo total: ~30 linhas de spec, enquanto nenhuma linha de código existe.

1. **rearch-02**: declarar `Feature COMPOSE` no roster (activation key `ape.composeTablePath`, `dependencies = {MOP}`, valores neutros) e registrar a decisão de canal (§5.2) como questão aberta vinculada a INV-RUN-06.
2. **rearch-04**: prever `mop` e `comp[]` no registro `STATE` (mais o dicionário `COMPOSABLE` run-local, o mecanismo INV-SNK-06 é exatamente a máquina certa para FQNs repetidos) e reescrever INV-SEL-06 para `st → STATE.mop` com fallback `→ ACT.mop`.
3. **rearch-07**: incluir a seção `composables` **graduada** (§6) no schema `formatVersion: 1` (evita um bump); excluí-la explicitamente do gate de equivalência de corpus (não tem contraparte no parser antigo); e reconciliar o seam F′ (a referência da rearch-02 a `isWidgetlessSubstrate()` contra a deleção na rearch-07 — o substituto é `stats.widgetsTotal` ou o próprio sinal Compose).

Estas edições são feitas no repositório `ape`, pelo fluxo OpenSpec de lá, como atualização das changes ainda não implementadas.

### Trilha C — o consumidor, como `rearch-08-compose-screen-signal` (depois da 07)

Escopo previsto: parse da seção `composables` no `MopData` fino; `screenHasMop` nos 4 sítios de predicado; termo graduado em `stateMopDensity`; linha por tela em `buildExplorationContext` como **variante de prompt nova** (não edição da corrente — protege os arms congelados e os goldens LLM); `STATE.mop`/`comp[]` na telemetria; preset/cenário `compose` no oráculo de paridade com regeneração deliberada de goldens; a decisão de canal (§5.2); arm novo na `aperv-tool` só após o sign-off da rearch-05.

**Janelas proibidas** (independentes de tudo acima): nada de Compose no jar durante 01→03 (goldens congelados por INV-ORA-07 — uma divergência Compose no meio da extração das stages inutiliza o oráculo como diagnóstico) e nenhum arm novo durante a migração da 05 (INV-APV-44 exige diff vazio por arm).

---

## 8. Riscos consolidados

| Risco | Gravidade | Tratamento |
|---|---|---|
| **Saturação do alcance transitivo** (96,1% / 0,0%) | mata o *valor* de D1 mesmo com E1 aprovado | tabela graduada + gate da Fase 2 reescrito (§6) |
| E1 falhar (informação não chega ao runtime) | mata a via (D1/D2/D3 juntos) | E1 primeiro; resultado negativo completa a série (doc 4, §16) |
| Custo de leitura da composição (80 ms / 800 ms) | mata decisão por passo | snapshot por estado novo; hook existente no APE-RV |
| Canal probe→APE (§5.2) | bloqueio de desenho na Fase 4 | decisão adiada; duas opções viáveis registradas; nenhuma bloqueia Fases 1–2 |
| Corrida probe-assíncrono × snapshot da árvore | dado atrasado ≥1 frame | contador monotônico no probe; descarte com log no consumidor |
| Instabilidade de API do Compose (trajetória bitdrift) | degradação entre versões | probe reflexivo com degradação graciosa; via A não depende de `ui.tooling` (presente em 87,3%) |
| Efeito observador (sobretudo canal-opção-1) | ameaça à validade do desfecho | braço de controle obrigatório na avaliação; sentinela excluído da abstração de estado |
| Generalidade sob R8/ofuscação | ameaça à tese, não ao experimento | corpus F-Droid não ofusca; registrar como limitação |
| Re-análise do corpus (348 APKs) | custo real | só na Fase 3, após o gate da Fase 2 |
| Timing contra a rearquitetura | retrabalho | Trilha B agora; Trilha C após 07; janelas proibidas respeitadas |

---

## 9. Governança

- **As Fases 1 e 2 não revogam nada**: não tocam o gator, não tocam o APE-RV, não criam canal. A regra "não mexer no gator" só é tocada na Fase 3 (produtor), e a Fase 2 é exatamente a via offline que a regra admite.
- `INV-ANA-16` (exclusão `androidx.compose.*` no Soot) **não** precisa ser revogado — a exclusão remove corpos do framework, não sítios de chamada no app (doc 2, §3; reconfirmado).
- A tabela de revogações do doc 4 (§17) fica emendada em duas linhas: a referência à change `telemetry-proof-llm-efficacy` sai (arquivada, §4.2); entra a família de invariantes da rearquitetura afetados pela Trilha B/C — INV-RUN-06 (canal, se opção 2), INV-SEL-06 (reescrita prevista), INV-ORA-07 (regeneração deliberada de goldens no rearch-08).
- Convenção de rastreamento: issue `gh<N>` + change OpenSpec neste repo a partir da Fase 2; changes do lado `ape` no fluxo OpenSpec de lá (Trilhas B e C).

---

## 10. Documentos relacionados

- Docs 1–4 da série (cabeçalho deste documento).
- `20260731_analise_percepcao_e_telemetria.md` e `20260731_verificacao_analise_percepcao.md` — a correção causal (`flagged=0`), o "única rota" (item D6), a concordância 22/22 e a aritmética de poder incorporadas na §2.1.
- `20260802_resultados_corrida_decisiva.md` — confirmação empírica do estrato (zero pares discordantes em Compose).
- `ape/openspec/changes/rearch-01..07/` — as sete changes mapeadas na §5; `ape/docs/20260802_verificacao_consistencia_rearch.md` e `ape/docs/20260803_procedimento_worktree_rearch.md` — consistência e procedimento da rearquitetura.
- `ape/openspec/changes/archive/2026-08-02-telemetry-proof-llm-efficacy/` — a change que o doc 4 citava como aberta (§4.2).

---

## 11. Emenda de 2026-08-06 — a costura do E1 não precisa de código no tool

Sessão de verificação sobre o bytecode do APK-alvo (`dev.itsvic.parceltracker_10501000.apk`, o **original**, não o instrumentado) e sobre o `rvsec-instrumentation-dexlib2`. **O E1 continua sem rodar**; o que muda é o custo de montá-lo e a forma do probe. Nenhuma conclusão de desenho — D1 sobre D2/D3, o gate da Fase 2, a decisão de canal — é afetada.

### 11.1 O alvo *é* expressável no descritor (corrige o doc 4, §11.2(c), e a §3 acima)

A §11.2(c) do doc 4 conclui, a partir de `execution` (padrão ignorado, casa qualquer método no índice 0) e `within` (always-match), que nenhum pointcut expressa o alvo e que portanto seria preciso um weaver em Java. A inferência generaliza de dois casos para todos, e há um terceiro pointcut com casamento real:

- `PointcutMatcher.matchStaticInit` (`:517-529`) compara o FQN da classe contra o `typePattern` e expande `T+` pela hierarquia via `InheritanceResolver`.
- `DexWeaver.weaveStaticInit` (`:569-654`) é um pré-passe dedicado: prepende no `<clinit>` existente ou **sintetiza um** pelo `StaticInitSynthesizer` para classes que não têm.
- Com `args` vazio, `deliversSignature` é falso e o `StaticInitializationEmitter` cai no `MonitorInvokeBuilder.buildInvoke` genérico — `invoke-static` limpo, sem `ClassSignature` nem registrador extra.

`staticinitialization(dev.itsvic.parceltracker.MainActivity)` dá um sítio único. `MainActivity` já tem `<clinit>`, então é prepend, não síntese.

Amarrações verificadas para o descritor ficar coerente com o probe: o dono do invoke vem de `DexWeaver.monitorOwnerFor` como `"Lmop/" + shortName + "RuntimeMonitor;"`; a assinatura vem de `MonitorInvokeBuilder.buildMethodReference`, com os tipos lidos de `advice.parameters[].type` na ordem de `monitorCall.args`; e `matchArgs` trata posição de *binding name* como coringa (`expected == null` → aceita qualquer argumento), o que permite declarar um parâmetro como `java.lang.Object` sem quebrar o casamento.

**Custo do E1 revisado**: um descritor `.json` e um `.java` no `--monitor-src-dir`, ambos descartáveis. Saem do plano `ComposeProbeSourceEmitter` e `ComposeProbeWeaver`, e com eles o rebuild do fat jar — que importa por governança, não por esforço: o jar é binário rastreado, e um E1 que o modifique vaza para dentro de um commit futuro.

### 11.2 Para a Via A, `onCreate` é tarde demais (corrige o refinamento da §3)

A §3 refinou o hook de `onResume` para `onCreate`. Para a Via A isso é insuficiente, e a razão é mecânica: a guarda `isTraceInProgress()` é avaliada **dentro do corpo compilado de cada composable**. Composables que já executaram antes de o tracer existir não emitem nada e só reapareceriam em recomposição — instalar de `onCreate` perde a primeira composição, justamente a que interessa observar. O `<clinit>` roda no carregamento da classe, antes de `onCreate` e portanto antes de `setContent`.

A antecipação não custa nada porque o segundo refinamento da §3 já era obrigatório: em `<clinit>` não existe composição alguma, e a leitura tem que ser adiada de qualquer forma.

Uma restrição que vem junto: `boot()` roda durante inicialização de classe, onde uma exceção escapando vira `ExceptionInInitializerError` e derruba o app — um probe falho viraria um run falho. Todo o corpo tem que estar sob `try/catch (Throwable)`.

### 11.3 As duas vias, agora ancoradas em símbolos medidos

Antes a §5 do doc 4 descrevia as vias pela documentação do Compose. Medido agora no APK-alvo (parser próprio de `string_ids`/`method_ids`/`field_ids` do DEX):

| Símbolo | Presença | Serve para |
|---|---|---|
| `ComposerKt.compositionTracer:CompositionTracer` (campo estático) | sim | slot de instalação da Via A |
| `ComposerKt.access$setCompositionTracer$p(CompositionTracer)V` | sim | rota de instalação preferida; sua sobrevivência ao R8 indica campo não-`final`, o que valida a escrita direta como fallback |
| `CompositionTracer` como **interface** (`isTraceInProgress()Z`, `traceEventStart(IIILjava/lang/String;)V`, `traceEventEnd()V`) | sim | permite implementar com `java.lang.reflect.Proxy`, satisfazendo a restrição (a) da §11.2 do doc 4 sem nenhuma referência de compilação |
| `CompositionImpl.slotTable:SlotTable` + `SlotTable.getCompositionGroups()` + `CompositionGroup.getSourceInfo()` | sim | caminho **barato** da Via B: caminhada direta pelos grupos, sem `SlotTreeKt.asTree()` — que é exatamente a chamada medida em ~800 ms no bitdrift |
| `androidx.compose.ui.R$id.wrapped_composition_tag` | sim | âncora view → composição |
| `ComponentActivityKt.setContent$default(...)` | sim | sítio de `call(...)` que entrega a Activity à Via B |

A rota pública `Composer.Companion.setTracer` **não** sobreviveu ao R8 neste APK — só o acessor sintético. Uma implementação que dependesse apenas da API pública documentada teria falhado e o resultado seria lido como "a via não funciona".

Duas ressalvas de método: o segundo sítio (`call(...setContent$default(...))`, que alimenta a Via B) é melhor-esforço — se o parser tropeçar no `$default` ou o binding não resolver, o weaver conta `plansSkipped`/`UnresolvedBindingException`, emite WARN e segue, e a Via A responde sozinha à pergunta decisiva. E o probe deve medir **dois custos distintos**: o tempo acumulado dentro do tracer (custo contínuo da Via A, já que a guarda aberta faz cada composable chamá-lo a cada composição) e o tempo de parede de uma caminhada completa (custo pontual da Via B). São grandezas diferentes, e o critério dos ~80 ms do doc 4 §9 se aplica à segunda.

### 11.4 O que continua não verificado

Exatamente o que o E1 mede: se o `<clinit>` costurado passa na verificação do ART neste APK, se qualquer das vias produz FQN em execução, e a que custo. A presença estática nunca esteve em dúvida — é o trânsito até o runtime que está.

Nota operacional para a execução: a injeção tem de ser sobre o APK **original**. O do corpus já traz o dex de monitores (`classes10.dex`, 77 referências `Lmop/`), e uma segunda passada do pipeline re-emitiria `mop/Coverage` e os `MultiSpec_*`, produzindo `Type defined multiple times`. O `.apk.json` do corpus permanece válido para o par — o probe acrescenta um dex e uma chamada no `<clinit>`, não altera activities nem reachability.
