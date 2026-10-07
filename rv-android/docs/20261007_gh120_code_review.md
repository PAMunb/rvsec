# Revisão de código da gh120 (commit `c1203805` + docs não comitadas)

Data: 07/10/2026. Escopo: `git show c1203805` (GATOR Java em `rvsec/rvsec-android/rvsec-gator`,
Python em `rv-android-core`, `rv-static-analysis` e `aperv-tool`) e as edições não comitadas de
`rvsec-gator/CLAUDE.md`, `client/docs/architecture.md` e `sootandroid/docs/architecture.md`.
Artefatos conferidos: `openspec/changes/gh120-gator-distance-hosted-windows/` (proposal, design
D1–D14, specs `analysis` e `aperv`, tasks).

Nenhum arquivo foi editado. Os caminhos Java abaixo são relativos a
`rvsec/rvsec-android/rvsec-gator/`; os Python, a `rv-android/modules/`.

## 1. O que foi verificado

- Leitura integral das classes novas (`LambdaEdges`, `TargetDistances`, `FragmentHostResolver`,
  `FragmentWindows`, `HostedWindowExtractor`, `HostResolver`, `NavGraphUses`,
  `BindingListenerRecovery`, `FragmentViewFlow`, `LibraryInflateModel`) e dos diffs de
  `RvsecAnalysisClient`, `SpinnerItemExtractor`, `ReachabilityEnricher`, `JsonReportWriter`,
  `JsonSchema`, `Flowgraph`, `GUIAnalysis`, `Main` e dos três arquivos Python.
- Conferência contra o `ReachabilityEngine` (sementes e grafo da busca reversa), `collectWidgets`,
  `enrichFromXml`, o parser Python e o derive (`_index_reachability`, `_derive_listener_flags`,
  `_build_widget_map`, `_rekey_dialogs`).
- Sondagem dos quatro artefatos de aceitação em `workspace-rv/worktrees-gator/acc/out/`
  (dsub2000, treehouses, giggity, cry.otp): ids de janela, pares de distância, INV-ANA-74.
  Nos quatro, todo par `[i, d]` tem `0 ≤ i < |distanceTargets|` e `0 ≤ d ≤ 10`, e nenhum método
  com `targetDistances` tem `reachesTarget: false` (INV-ANA-74 vale nos dados).
- Testes Python executados (um módulo por vez, `--import-mode=importlib -o "addopts="`):
  derive 72 ok, `test_window` 19 ok, parser 74 ok; `tests/parity`: 224 ok, **2 falhas** (achado A2).
- Os testes Java do módulo `client` não foram reexecutados nesta revisão (o build do reator é
  recurso serializado e havia outros agentes ativos); a task 2.8 registra 238 verdes.

### Métricas (sub-skills de complexidade e código morto)

| Arquivo | SLOC | MI | Funções acima de CC 10 | Código morto |
|---|---|---|---|---|
| `aperv-tool/.../derive_mop_artifact.py` | 540 | 23,3 (abaixo de 40) | `_build_widget_map` 15, `_index_reachability` 14, `_rekey_dialogs` 13, `_build_wtg` 13, `_derive_widget_flags` 12 | nenhum |
| `rv-static-analysis/.../static_analysis_parser.py` | 480 | 48,1 | `_parse_windows` 12, `_parse_transitions` 12, `parse_file` 11 | parâmetro `window_name` sem uso em `_parse_listener` (pré-existente) |
| `rv-android-core/.../domain/window.py` | 222 | 54,1 | `Windows.get_window` 13 | `Window.get_widgets`, `Windows.get_windows` sem chamador (pré-existente) |

O diff da gh120 nesses arquivos é pequeno (4, 7 e ~25 linhas de código); nenhuma das funções acima
de CC 10 cresceu por causa dele. O MI baixo do derive vem do tamanho do arquivo (1 229 linhas, 440
de docstring), não desta change. Nada disso bloqueia.

## 2. Achados

Cada achado leva a classificação pedida: **[comportamental]** quando corrigir muda o que o GATOR
(ou o derive) emite; **[reparo puro]** quando não muda a saída em nenhum APK em que o caminho
hoje funciona.

### Crítico (corrigir antes do arquivamento)

**A2. A paridade de alcançabilidade está vermelha com o jar implantado** [reparo puro]

- Arquivos: `rv-android/modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` (linha de
  base, de 15/09) contra `rv-android/lib/gator/rvsec-analysis-client.jar` (07/10 15:30).
- Falham `tests/parity/test_reachability_parity.py::test_targets_set_matches_baseline` e
  `tests/parity/test_baseline_freshness.py::test_baseline_not_older_than_jar`.
- A deriva é exatamente a pretendida pela D3:
  `<br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0: void onClick(android.view.View)>`
  passou a `reachesTarget: true`. A fixture do derive (`aperv-tool/tests/fixtures/cryptoapp.apk.json`)
  foi atualizada no commit; a linha de base do parser, que alimenta a paridade, não. As tasks 6.3 e
  6.4 rodaram só a paridade de chaves (`test_json_keys.py`).
- Correção: regenerar a linha de base com o jar implantado, depois de confirmar que o único delta
  de `reachesTarget` e de `reachable` é esse wrapper.

### Avisos (deveriam ser corrigidos)

**A1. Uma exceção no passo hospedado pode apagar o artefato inteiro** [reparo puro]

- `client/.../RvsecAnalysisClient.java:1599-1601` constrói `new HostedWindowExtractor(...)` fora
  de qualquer `try`. O construtor (`hosted/HostedWindowExtractor.java:68-72`) cria o
  `HostResolver`, cujo construtor roda `indexUses()` (`hosted/HostResolver.java:308-314, 400-438`):
  percorre todos os corpos de classe do app. Só a recuperação do corpo é protegida, e apenas
  contra `RuntimeException`.
- O `try` de `extendInto` (`HostedWindowExtractor.java:82-93`) só cobre o que vem depois. A
  escrita pré-WTG (`RvsecAnalysisClient.java:208-215`) captura só `IOException`.
- Cenário de falha: um `OutOfMemoryError`, ou uma `RuntimeException` inesperada, dentro de
  `indexUses` na primeira chamada de `prepareWindows` sai de `run()`. **Nenhum JSON é escrito**,
  nem a seção de alcançabilidade, que é calculada antes. Isso contradiz a tabela de Error Handling
  do design ("artefact without those windows") e o "done" da task 2.3 ("hosted pass catches in
  `extendInto`"). A probabilidade é baixa, mas a perda é total para o APK.
- Correção: criar o `HostResolver` dentro do `try` de `extendInto`, ou envolver a chamada em
  `prepareWindows` como já é feito com as janelas de fragment (linhas 1590-1597).

**A3. Itens de spinner somem quando o adapter é criado em dois ramos** [comportamental: devolve itens que setembro emitia]

- `client/.../SpinnerItemExtractor.java:253-263` (`adapterSite`) aceita só uma definição que
  alcança o uso. Em `:230`, `siteItems.get(adapterSite(...))` recebe `null` quando há duas.
- Cenário de falha:
  `ArrayAdapter a; if (pro) a = new ArrayAdapter(ctx, L, new String[]{"x","y"}); else a = new ArrayAdapter(ctx, L, new String[]{"z"}); spinner.setAdapter(a);`
  - O `LocalSplitter` do Soot põe as duas definições na mesma local, porque ambas alcançam o mesmo
    uso.
  - O código de setembro indexava pela `Local` e emitia `entries == ["x","y","z"]`. O novo emite
    `[]`.
  - A troca de chave (D13) foi feita para o caso oposto (uma local reutilizada para adapters em
    sequência, no `ProfileSetup` do cry.otp), e esse caso continua resolvido.
  - Os 14 APKs da aceitação não exercitaram o padrão.
- Correção: devolver todas as definições que alcançam o uso e que criam o adapter, e unir os itens
  delas. Uma definição que não cria adapter continua sem itens.

**A4. Os dois resolvedores de host tratam a activity base de forma diferente** [comportamental]

- `hosted/HostResolver.java:332-335`: toda classe em `output.getActivities()` hospeda a si mesma
  e para a busca ali.
  - `output.getActivities()` são todas as subclasses concretas de `Activity` do app: o
    `Flowgraph.activityNode` só exclui as abstratas.
  - Só as bases abstratas passam pelo ramo que expande para as subclasses (`:336-341`).
- `fragment/FragmentHostResolver.java:968-979` (`launchedActivities`) leva qualquer activity a
  todas as subclasses declaradas no manifest.
- Cenário:
  - Uma `BaseActivity` concreta e fora do manifest abre um diálogo em `onOptionsItemSelected`. Sai
    uma janela HOSTED `BaseActivity#XDialog`.
  - O derive guarda os widgets sob a chave `BaseActivity`, que nunca é a activity em execução. Os
    widgets e a marca de MOP dessa janela ficam inalcançáveis para o APE-RV.
  - A mesma base, ao mostrar um fragment, gera janelas FRAGMENT em cada subclasse declarada.
  - Uma base declarada (dsub: `SubsonicActivity`) recebe HOSTED só para si.
- É perda de recall, não um host errado. A correção muda quais janelas saem, então pertence a
  outra change, com decisão sua.
- Correção sugerida: passar o ramo `activities.contains(x)` de `hostsOf` pela mesma expansão para
  as subclasses declaradas que o `FragmentHostResolver` usa.

**A5. O conjunto `reachable` (denominador de cobertura) também muda com as arestas de lambda** [comportamental, não documentado]

- `LambdaEdges.addTo` entra no grafo antes do `ReachabilityEngine` (`RvsecAnalysisClient.java:155-161`).
  A busca para a frente a partir dos pontos de entrada (`ReachabilityEngine.run`,
  `multiSourceBfs(graph, entryPoints)`) atravessa as arestas novas, então o corpo de um lambda
  alcançado só pelo wrapper passa a `reachable: true`.
- A task 1.1 registra isso no giggity ("2 app methods turned `reachable` (also lambda effect)"),
  mas a D3, os Risks e o texto da spec falam só de `reachesTarget`.
- Na paridade, o portão `G_paridade_reachability` passou no cryptoapp. A mudança existe mesmo
  assim: qualquer comparação de cobertura entre artefatos de setembro e os novos passa a ter
  denominadores diferentes.
- Correção: registrar a consequência na D3 e na spec, ou dizer explicitamente que ela é aceita.

**A6. Uma falha das arestas de lambda tira as marcas do derive em silêncio** [comportamental, se corrigida com chave nova]

- Se `LambdaEdges.addTo` lança (o erro é capturado em `RvsecAnalysisClient.java:157-161`), ou se
  o corpo de um wrapper não carrega (`reach/LambdaEdges.java:155-158`), o wrapper sai listado com
  `reachesTarget: false`.
- Pela INV-DRV-09, o derive confia nessa marca e não recorre mais à recuperação por classe.
- O resultado é o mesmo da D9 com artefato antigo: perda de marcas. Aqui acontece numa execução
  nova, sem nada no artefato que mostre que isso ocorreu (só uma linha no stdout).
- Correção: escrever no artefato a contagem de arestas e de corpos pulados, ou fazer a falha de
  `addTo` abortar. Qualquer das duas acrescenta saída; a decisão é sua.

**A7. O `enrichFromXml` passou a custar janelas × layouts** [reparo puro: desempenho]

- `RvsecAnalysisClient.java:1236-1275` relê com DOM todos os `res/layout/*.xml` para cada janela.
  A gh120 estendeu o filtro a FRAGMENT e HOSTED (`:1248-1249`).
- No treehouses são 98 janelas próprias contra 8 activities, e `prepareWindows` roda duas vezes.
- Correção: analisar cada layout uma vez por escrita e indexar os elementos por `android:id`. A
  saída é a mesma, desde que se preserve a regra "anota o último registro" da D7.

### Sugestões

**S1. Janelas HOSTED que repetem a activity** [comportamental]

- No treehouses, `InitialActivity#...ActivityInitial2Binding` (6/6 widgets),
  `SSHConsole#...ActivitySshConsoleBinding` (37/37) e semelhantes repetem registro por registro a
  janela ACTIVITY do mesmo host.
- Também surgem `Host#Host` (`InitialActivity#InitialActivity`), vindas de `inflate` no próprio
  código da activity.
- Como o consumidor dobra tudo no mesmo balde, o efeito é só de tamanho.
- `dropRepeatedOwnedWindows` (`RvsecAnalysisClient.java:1639-1651`) poderia descartar também a
  janela própria cuja lista de widgets está contida na da ACTIVITY do mesmo host.

**S2. A ligação de view dos fragments falha por inteiro com um único corpo ruim** [reparo puro]

- `GUIAnalysis.java:91-96` envolve `FragmentViewFlow.link` inteiro num só `try`.
- Basta um `body.getParameterLocal(0)` lançar (`FragmentViewFlow.java:80`) em um único
  `onViewCreated` malformado para todas as arestas de view de fragment do app se perderem.
- Correção: um `try` por método, como na INV-ANA-17.

**S3. Lógica duplicada (P1)**

- A mesma interface funcional existe duas vezes: `FragmentWindows.WidgetCollector` e
  `HostedWindowExtractor.WidgetCollector`.
- O teste de fragment aparece três vezes: `FRAGMENT_BASES`/`isFragment` em `FragmentViewFlow` e
  em `FragmentHostResolver`, além de `isSubclass` em `HostResolver` e de `extendsClass`/`outerClass`
  em `FragmentHostResolver`.
- Há dois leitores de grafo de Navigation com regras diferentes:
  - `NavGraphUses.record` aceita destinos `<activity>` e `<dialog>` e lê também
    `<argument android:name>`, que é inofensivo porque `containsClass` falha.
  - `FragmentHostResolver.collectDestinations` exclui `<activity>` e `<dialog>` e qualifica nomes
    relativos (`.Foo`). O `NavGraphUses` não qualifica, então perde destinos relativos.
- `attr`/`parse` de XML estão duplicados.
- A4 é um sintoma dessa duplicação.

**S4. Código sem uso**

- `FragmentWindows.pairs()` e os campos públicos de `FragmentWindows.Pair` não são lidos fora da
  classe.
- `FragmentHostResolver.isDialogFragment` é público, mas só tem uso interno.

**S5. Lacunas de teste**

- A linha do design "`JsonOutputTest` (keys present, omitted when empty)" não tem teste
  correspondente. Faltam testes para `JsonReportWriter.writeDistanceTargets` e para a emissão de
  `targetDistances` em `writeReachabilitySection` (`RvsecAnalysisClient.java:1721-1729`).
- Também falta o teste de que os argumentos de `Main` não contêm `-exclude`, que está na linha
  INV-ANA de exclusões do mapeamento.
- `HostResolver.hostsOf`, `NavGraphUses` (closure), `BindingListenerRecovery.key` e
  `dropRepeatedOwnedWindows` com FRAGMENT antes de HOSTED são testáveis sem o solver. Hoje, cerca
  de 2 000 linhas (fragment/hosted/flow) só são cobertas pela aceitação.
- O arquivo não rastreado `sootandroid/src/test/java/presto/android/AnalysisEntrypointTest.java`
  é da INV-ANA-65, não desta change.

**S6. Texto que descreve mal o código (P2/P4)**

- `rv-static-analysis/.../static_analysis_parser.py:110-112`: o comentário chama `distanceTargets`
  de "list of direct callers". A lista também tem os alvos `boundary`.
- `rv-android-core/.../domain/window.py:26-27`: o comentário de `HOSTED` diz "non-Activity class
  (adapter, custom view)". HOSTED também cobre diálogos, DialogFragment, layouts de binding e
  `Host#Host`.
- `sootandroid/docs/architecture.md`: a edição não comitada só toca nos argumentos do Soot. As três
  mudanças no flowgraph do solver (`FragmentViewFlow`, `LibraryInflateModel` e o op node
  `ViewBindings.findChildViewById`) aparecem só no `CLAUDE.md`, não na arquitetura do módulo que
  elas alteram.
- A task 2.7 diz que o mapa de arrays é construído "once". `appArrayItemsById()` roda em cada
  `extractWindows`, ou seja, duas vezes por execução. É irrelevante na prática.

O resto das docs não comitadas confere com o código:
- contagem de arquivos (26/180);
- ~2 120 linhas do cliente;
- `Main.java:230-249` e `:282-286`;
- "`distanceTargets` omitted only when the pass failed", que corresponde a `writeDistanceTargets`
  com enricher `null`;
- numeração a partir de 900000 acima do maior id.

## 3. Mudanças no que o GATOR emite × reparos puros

**Comportamentais (a saída muda):**
1. Chaves novas `distanceTargets` (topo) e `targetDistances` (por método). São aditivas.
2. Arestas de lambda: `reachesTarget` e também `reachable` mudam para wrappers e implementações
   SAM e para os corpos que eles alcançam (D3; ver A5).
3. Janelas novas FRAGMENT e HOSTED. Com elas, o derive marca mais widgets e mais activities
   hospedeiras.
4. Modelos novos no solver (`FragmentViewFlow`, `findChildViewById`, `LibraryInflateModel`) e
   `BindingListenerRecovery`. Eles também mudam janelas que já existiam:
   - ACTIVITY ganha widgets e listeners (iyps: de 0 para 741 listeners);
   - a WTG ganha transições (iyps: de 9 para 153) e tempo (de 106 para 1 031 s).
5. `dropRepeatedWidgets` em todo tipo de janela, inclusive ACTIVITY: muda a multiplicidade (D14).
6. Spinner:
   - itens novos vindos de array de recurso;
   - itens deduplicados por spinner;
   - id de `findViewById` resolvido no próprio statement, o que pode trocar o widget que recebe os
     itens;
   - regressão do A3.
7. Derive: um wrapper listado vale pela própria marca (INV-DRV-09).
8. Parser: o tipo `HOSTED` passa a ser mapeado.

**Sem mudança de saída:** a remoção dos três `-exclude` (inertes, medido na D1), a resolução do
cast em `resolveSpinnerWidgetId` no ponto de definição (antes era no ponto de uso) e as docs.

Dos achados: A1, A2 e A7 são reparos puros; A3, A4, A5 e A6 mudam a saída e convém tratá-los
separadamente. A3 devolve o que setembro emitia; A4 e A6 acrescentam ou realocam saída e pedem
decisão sua.

## 4. Conformidade P1–P4

- **P1 (simplicidade):** em geral, conforme. As exceções são a duplicação de S3, com dois
  resolvedores de host de regras divergentes, e as interfaces repetidas.
- **P2 (legibilidade):** os Javadocs explicam o porquê com números medidos, como a D11/D14 com o
  dsub e o sexytopo. As exceções são os dois comentários imprecisos de S6.
- **P3 (sem retrocompatibilidade):** conforme. `DistanceExporter`, `ExcludeMode` e
  `RVSEC_DIST_DIR` foram apagados, e o derive não tem guarda para artefato de setembro (D9,
  decisão registrada). O construtor de quatro argumentos do `ReachabilityEnricher` continua lá
  "for callers that carry no provenance — the tests". É pré-existente e não é um shim desta change.
- **P4 (estado atual):** conforme. Não há histórico de migração nos comentários novos.

## 5. Avaliação

**REQUEST CHANGES**, de escopo pequeno:
- A2 (paridade vermelha) precisa ficar verde antes do arquivamento.
- A1 é uma linha (pôr o construtor dentro do `try`) e fecha a única via de perda total do
  artefato que esta change abriu.
- A7 é desempenho puro.
- A3, A4, A5 e A6 mudam saída. Recomendo registrá-los e decidir fora desta change, exceto
  documentar A5 na D3.

Correção, cobertura das invariantes INV-ANA-73/74/75/77/78 e o lado Python estão corretos no que
foi conferido em código e nos quatro artefatos de aceitação.
