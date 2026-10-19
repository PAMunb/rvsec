# gh-tbd-gator-distance-paths — evidências do apply (19/10/2026)

Change `gh-tbd-gator-distance-paths` (sem issue), worktree `worktrees-gator/paths`, branch `wip/gator-paths` a partir de `37efe5ed`. Todas as medições foram feitas nesta sessão, no host, com o JDK 25.0.3 do host para o GATOR e o SDK Android local. Os APKs foram lidos sem alteração de `rvsec-study03-replication-package/data/raw/e6-corpus/` e de `apks_examples/`.

Configuração das análises, igual à do `task.sh` da campanha E6 (`experiments/E6-campaign/static-analysis/task.sh` do replication package): specs `jca_android`, SPARK, `--cg-delegation true`, heap 12g, `RV_STRIP_BUILD_TYPE_SUFFIX=true`. Esta última variável é necessária: sem ela, o freeotp usa o pacote do manifesto `org.fedorahosted.freeotp.debug`, nenhuma classe cai sob essa chave e a análise é recusada. Script: `scripts/run_gator.sh`. Comparações: `scripts/compare.py` e `scripts/check_steps.py`, com as saídas gravadas em `compare-effect-cases.txt`, `compare-empty-paths.txt`, `inv90-check.txt` e `new/steps-*.txt`.

## 1. Jars

| | `rvsec-analysis-client.jar` | `rvsec-gator.jar` |
|---|---|---|
| baseline (jar da árvore principal, compilado em 10/10 a partir da fonte do HEAD) | `e65eb662…` | `024ccdfb…` |
| novo (build da tarefa 5.3) | `3b0e60d5…` | `bd477140…` |
| novo (build da tarefa 5.5, arestas de sítio vazio retiradas antes da WTG) | `d4cf9f10…` | `b3d0ddf2…` |

O hash completo está em `baseline/SHA256`, `new-jars.SHA256` e `new-jars-5.5.SHA256`. Entre o commit do jar do replication package (`02f973c8`) e o HEAD, o rvsec-gator só recebeu a gh125 e um commit de testes.

Build com testes (5.3): 292 testes unitários do client e 24 do sootandroid, depois 33 ITs (`-DskipITs=false`), todos verdes. Duas intervenções foram necessárias:

- O processador de anotações `ClassIndex` não aceita `record` do Java. O `record Step` de `TargetDistances` virou uma classe estática.
- `BaselineComparisonIT` fixava `reachable = 55` no cryptoapp com tolerância de ±10 %. O jar novo dá 61, que é o aumento pretendido por A/B/C. O valor fixado passou a 61. No mesmo IT, windows, transitions e `directlyReachesTarget` do cryptoapp continuam exatamente iguais.

Python (5.4): paridade de chaves e de constantes, 5 testes verdes. aperv-tool: 712 testes verdes, 74 pulados.

## 2. Conjunto de APKs

O design pedia cryptoapp mais cinco APKs do corpus. Dois deles foram trocados por decisão do Pedro em 19/10, para caber no tempo: `app.maskan.chat_90` e `com.kin.easynotes_14` levam cerca de 30 min por análise. Nesses dois APKs, a WTG e o cliente levam cerca de 15 s; os outros ~1 700 s vão no carregamento do Soot e no SPARK, sobre ~33 mil classes. No lugar deles entraram `com.vrem.wifianalyzer_71` e `systems.sieber.droid_scep_7`, dois APKs rápidos que têm casos entre os 63. Com a troca, o cenário Application do spec (maskan) e o de campo injetado pelo Hilt (easynotes) não são conferidos ponta a ponta; o primeiro fica coberto pelo teste unitário `FrameworkCreatedEntryPointsTest`.

Tempo de parede do baseline, com WTG: giggity 65 s, cryptoapp 72 s, cry.otp 138 s, freeotp 174 s, wifianalyzer 133 s, droid_scep 181 s.

**O baseline local diverge do replication package na classificação `direct`/`boundary` dos alvos.** No cry.otp, `MD5.<init>` é `direct` no replication package e `boundary` aqui; a varredura de bytecode acha 2 chamadores diretos em vez de 3. No freeotp são 15 chamadores diretos contra 23. O jar é o mesmo, a menos da gh125. O que muda é o ambiente: o replication package rodou num container com JDK 25.0.2 e o SDK em `/opt/android`; aqui o GATOR roda no host. A causa não foi investigada. A comparação antes/depois abaixo não é afetada, porque as duas rodadas usam o mesmo ambiente.

## 3. Os casos dos 63 (tarefa 6.2)

`targets63.csv` lista os 63 alvos diretos com `reachable = False` e `executed = True` (29 APKs, 10 sítios de mau uso). Seis deles estão nos APKs medidos.

| APK | alvo | mau uso | antes | depois |
|---|---|---|---|---|
| org.cry.otp_31 | `HOTP.hmac_sha1` | sim | reachable=False | reachable=True |
| net.gaast.giggity_769 | `Schedule$Item.hashCode` | sim | reachable=False | reachable=True |
| com.vrem.wifianalyzer_71 | `AccessPointsAdapterData.calculateChildType` | sim | reachable=False | reachable=True |
| com.vrem.wifianalyzer_71 | `GraphWrapper.calculateGraphType` | sim | reachable=False | reachable=True |
| org.fedorahosted.freeotp_48 | `Token.parse` | não | reachable=False | reachable=True |
| systems.sieber.droid_scep_7 | `ScepClient.CertReq` | não | reachable=False | reachable=True |

Os seis já tinham `reachesTarget = True` antes, porque cada um chama o alvo JCA diretamente. Os seis passaram a `reachable = True`.

Cenários do delta conferidos pelo subcomando `path`, no documento compacto com paths:

- cry.otp (A): `Home$1.onClick → HOTP.gen → HOTP.generateOTP → HOTP.hmac_sha1`, `d = 3`, exatamente a cadeia do cenário "The chains of a handler".
- freeotp (C): `Activity.onNewIntent → Activity.addToken → Token.parse`, `d = 2`, o par do cenário "A call on `this` inside an activity gets its edge". `addToken` só é alcançado de `onNewIntent` pela aresta de sítio vazio.
- maskan (`initDatabaseEncryption`) e easynotes (`encryptNote`) não foram medidos (seção 2).

## 4. Tamanho do efeito (tarefa 6.3), baseline full → novo full

| APK | reachable | reachesTarget | directlyReachesTarget | pares | distanceTargets | transitions |
|---|---|---|---|---|---|---|
| cryptoapp | 55 → 61 | 34 → 35 | 23 → 23 | 72 → 73 | iguais | 35 → 35 |
| giggity_769 | 294 → 623 | 1 → 53 | 0 → 0 | 1 → 41 | iguais | 431 → 1 622 |
| cry.otp_31 | 46 → 88 | 13 → 13 | 2 → 2 | 13 → 13 | iguais | 1 443 → 1 443 |
| freeotp_48 | 131 → 409 | 36 → 62 | 15 → 15 | 109 → 261 | iguais | 47 → 53 |
| wifianalyzer_71 | 574 → 1 269 | 12 → 39 | 0 → 0 | 12 → 39 | iguais | 94 → 169 |
| droid_scep_7 | 22 → 75 | 17 → 20 | 4 → 4 | 36 → 39 | iguais | 18 → 18 |

Em todos os APKs, `distanceTargets` e o conjunto de métodos com `directlyReachesTarget` são idênticos (INV-ANA-96). windows não muda em nenhum APK.

A e B só mexem em `reachable`. As sementes entram apenas na busca para frente, e `reachesTarget`, `directlyReachesTarget` e as distâncias vêm da busca reversa a partir dos alvos e do conjunto direto. Por isso o crescimento de `reachesTarget` e dos pares vem só de C. A separação foi feita pela leitura do código; não houve rodada com C desligado.

### Arestas de sítio vazio (C) e fan-out

| APK | sítios de invoke de instância | sítios vazios | arestas adicionadas | maior fan-out |
|---|---|---|---|---|
| cryptoapp | 551 | 281 | 1 | 1 |
| giggity_769 | 4 489 | 2 218 | 761 | 14 |
| cry.otp_31 | 781 | 462 | 32 | 1 |
| freeotp_48 | 1 999 | 1 178 | 243 | 12 |
| wifianalyzer_71 | 4 276 | 1 541 | 1 252 | 41 |
| droid_scep_7 | 1 085 | 558 | 10 | 2 |

Os maiores fan-outs estão em sítios cujo tipo nomeado é uma interface de biblioteca:

- wifianalyzer: 41 em cada chamada de `kotlin.jvm.functions.Function1.invoke`. Os 10 maiores sítios do APK são todos desse tipo.
- giggity: 14 em `java.lang.Runnable.run`.
- freeotp: 12 em `android.view.View$OnClickListener.onClick`.

Nesses sítios a aresta vai para cada implementador concreto da interface no app, porque o despacho percorre os subtipos do app de qualquer tipo nomeado. Isso confere com INV-ANA-96 ("the receiver's declared type and its app subtypes"). Em sítios cujo tipo é uma classe do app, o fan-out fica entre 1 e 8. Os 10 maiores sítios de cada APK estão em `compare-empty-paths.txt`.

### Custo de C na WTG com `cgDelegation=true`

Com `cgDelegation=true` (configuração da campanha), a WTG lê o grafo de chamadas do Soot, então recebe as arestas de C. Tempo do cliente (`[RvsecAnalysisClient] End`), baseline → novo:

| APK | cliente antes | cliente depois |
|---|---|---|
| cryptoapp | 6,7 s | 14,6 s |
| giggity_769 | 9,7 s | 31,5 s |
| cry.otp_31 | 33,5 s | 36,8 s |
| freeotp_48 | 40,2 s | 268,9 s |
| wifianalyzer_71 | 29,0 s | 348,3 s |
| droid_scep_7 | 15,0 s | 14,5 s |

O freeotp com o jar novo e `--skip-wtg` termina o cliente em 3,8 s, então o acréscimo está na construção da WTG, não em `EmptySiteEdges` nem nos paths. Com isso, a análise do freeotp passa de 174 s para 417 s de parede, e a do wifianalyzer de 133 s para 452 s. As transições também mudam onde o grafo ganhou arestas: giggity 431 → 1 622, wifianalyzer 94 → 169, freeotp 47 → 53. O design registra que C chega à WTG só com `cgDelegation=true`, mas não mediu esse efeito.

## 5. Paths (tarefas 6.1, 6.4, 6.4b)

Tamanho do documento, em bytes:

| APK | full | compacto | compacto + paths | full + paths |
|---|---|---|---|---|
| cryptoapp | 79 823 | 50 784 | 53 661 | 84 459 |
| giggity_769 | 7 778 762 | 5 477 714 | 5 481 746 | — |
| cry.otp_31 | 2 628 022 | 1 798 112 | 1 799 163 | 2 629 462 |
| freeotp_48 | 411 606 | 278 045 | 285 877 | — |
| wifianalyzer_71 | 1 196 352 | 826 685 | 830 995 | — |
| droid_scep_7 | 220 102 | 137 745 | 140 003 | — |

A passada dos paths levou de 1 a 7 ms em todos os APKs (`[RvsecAnalysisClient] Distance paths`). No modo compacto foram 10 a 148 passos e 13 a 61 métodos por APK.

- **INV-ANA-90:** o compacto com paths, sem os dois membros, é igual em bytes ao compacto sem paths até `transitions`, em todos os APKs; `transitions` tem as mesmas arestas em outra ordem. É a mesma não determinância registrada na gh125 (ordem por identity hash na WTG), e ela aparece também entre duas rodadas do mesmo jar.
- **INV-ANA-91 e INV-ANA-93:** em cada documento com paths (6 compactos e 2 full), a cadeia de cada par escrito foi reconstruída pelos passos. Toda cadeia tem `d` passos e termina no alvo, nenhum passo fica fora de alguma cadeia, `pathMethods` está ordenado e os passos estão ordenados por `(i, v)`, com um passo por `(i, v)`.
- **INV-ANA-92:** duas rodadas do cry.otp com paths deram `pathMethods` e `distancePaths` idênticos; o arquivo só difere na ordem de `transitions`.
- **Passos app→app contra o bytecode (androguard):** são 192 passos nos 6 APKs. Em 183, o método de origem tem um invoke com o nome do destino. 1 entra num corpo de lambda. Os outros 8 são arestas implícitas que o grafo de chamadas já modelava: `Thread.start` para `run`, e `Handler.post`/`postDelayed`/`send*Message` para `run`/`handleMessage`. Conferi no bytecode que a origem chama esses métodos (giggity 5 passos, wifianalyzer 3). Nenhum passo ficou sem explicação.

## 6. Conversor (tarefa 6.5)

- O documento full com paths do cry.otp é recusado com exit 1, uma linha no stderr que nomeia o arquivo, e nenhum arquivo de saída.
- Nos 6 APKs, o conversor aplicado ao full sem paths dá o compacto do GATOR igual em bytes até `transitions`, e `transitions` com as mesmas arestas (INV-ANA-87, com a mesma ressalva de ordem).

## 7. Respostas às questões abertas do design

- **Maior fan-out de C:** 41, em `Function1.invoke` no wifianalyzer. Nos sítios cujo tipo é uma classe do app, ele fica entre 1 e 8. O crescimento de `reachesTarget` vai de 0 % a 15× (giggity 1 → 53), e o de pares escritos no full de 0 a 41× (giggity 1 → 41). O teto, se houver, é decisão do Pedro; nenhum foi implementado.
- **Custo dos paths:** de 1 a 7 ms por APK e de +0,1 % a +5,7 % no tamanho do compacto (cry.otp +1 051 B, cryptoapp +2 877 B).
- **Novo, para decisão:** com `cgDelegation=true`, C deixa a WTG até 12× mais lenta em dois dos seis APKs (seção 4) e muda as transições.

## 8. Arestas de sítio vazio fora da WTG (tarefa 6.7, jar da 5.5)

Por decisão do Pedro em 19/10, a WTG fica como era: as arestas que `EmptySiteEdges` acrescenta saem do grafo de chamadas do Soot depois das distâncias e antes de `analyzeFragments` e da WTG (tarefa 5.5). Os seis APKs rodaram de novo no modo completo, com a mesma configuração da seção 1, em `new/full-5.5/`. Comparação: `scripts/compare.py rerun55`.

- **WTG igual à do baseline nos seis APKs.** `windows` é idêntico, comparado como objeto JSON (ids incluídos). `transitions` é igual como conjunto, tanto pela chave (janela de origem, janela de destino, tipo do evento, handler) quanto pelo evento inteiro, com widget: cryptoapp 36, giggity 4 182, cry.otp 1 828, freeotp 153, wifianalyzer 294, droid_scep 18 eventos. A ordem das transições segue o hash de identidade e não foi comparada.
- **Alcançabilidade igual à da rodada 5.3** (`new/full`) nos seis APKs: `reachable`, `reachesTarget`, `directlyReachesTarget`, `targetDistances` de cada método e `distanceTargets`.
- **O log registra a retirada**, com o mesmo número de arestas que `EmptySiteEdges` acrescentou: cryptoapp 1, giggity 761, cry.otp 32, freeotp 243, wifianalyzer 1 252, droid_scep 10.
- **O resto do documento é igual ao baseline**, exceto `components`, que já mudava na 5.3 e é reflexo do aumento de `reachesTarget`: as atividades cujos métodos de ciclo de vida passaram a alcançar um alvo ganham `reachesTarget: true` e `targetMethods` (giggity: `ScheduleViewActivity` com `onCreate`, `onResume`, `onPause`, e `SettingsActivity` com `onDestroy`; wifianalyzer: `MainActivity` com `onResume` e `onStart`).
- **Paths inalterados.** O cry.otp em modo completo com `--distance-paths` (`new/full-paths-5.5/`) dá `pathMethods` (13) e `distancePaths` (10 passos) iguais aos da 5.3, e `rv-static-analysis path` imprime a cadeia do spec, `Home$1.onClick → HOTP.gen → HOTP.generateOTP → HOTP.hmac_sha1`, d = 3.

Tempo do cliente (`[RvsecAnalysisClient] End`) e de parede da análise:

| APK | cliente baseline | cliente 5.3 | cliente 5.5 | parede baseline | parede 5.3 | parede 5.5 |
|---|---|---|---|---|---|---|
| cryptoapp | 6,7 s | 14,6 s | 7,0 s | 72 s | 73 s | 55 s |
| giggity_769 | 9,7 s | 31,5 s | 8,6 s | 65 s | 69 s | 46 s |
| cry.otp_31 | 33,5 s | 36,8 s | 25,0 s | 138 s | 106 s | 105 s |
| freeotp_48 | 40,2 s | 268,9 s | 36,0 s | 174 s | 417 s | 169 s |
| wifianalyzer_71 | 29,0 s | 348,3 s | 19,3 s | 133 s | 452 s | 114 s |
| droid_scep_7 | 15,0 s | 14,5 s | 10,4 s | 181 s | 186 s | 171 s |

O tempo do cliente voltou ao do baseline. As diferenças de parede para baixo não são efeito do jar: as seis análises rodam em paralelo e disputam a máquina de modo diferente a cada rodada. Com isso, a questão nova da seção 7 sobre o custo na WTG fica resolvida pela 5.5.


### Correções da revisão de código (tarefa 5.6)

Depois da revisão (8.3), três correções no Java, nenhuma com efeito na saída: o mapa de chamadores das distâncias é liberado depois do cálculo dos caminhos, para não ficar na memória durante a WTG; as arestas de sítio vazio entram numa lista do chamador à medida que entram no grafo, para que uma falha no meio da passada não deixe arestas para a WTG; e um `android:name` vazio no `<application>` passa a valer como ausente, em vez de derrubar a leitura do manifesto. Jars: client `434e8614…`, gator `dca2b1e9…` (`new-jars-review.SHA256`). Build com testes: 293 unitários do client, 33 ITs, verdes.

Uma rodada só, no cryptoapp em modo completo com `--distance-paths` (`new/full-paths-review/`), confere a ordem dentro do `run()`, que os testes unitários não exercitam: `pathMethods`, `distancePaths`, `reachability`, `distanceTargets` e `components` iguais aos da rodada da 5.3 com caminhos; `windows` e o conjunto de transições iguais ao baseline; cliente em 6,7 s.
