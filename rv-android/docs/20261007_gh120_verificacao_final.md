# gh120: verificação do GATOR final (07/10, 14:55–15:20)

GATOR: `rv-android/lib/gator`, jars de 14:30. Variáveis da campanha (`RV_STRIP_BUILD_TYPE_SUFFIX=true`,
`RV_PACKAGE_DETECTOR=false`), 12 g por JVM, no máximo 72 GB somados. Saídas, logs e scripts em
`worktrees-gator/v53/` (`progress.tsv`, `out_*/`, `logs/`, `compare_53.py`, `compare_54.py`,
`listeners_breakdown.py`). Nada escrito em `rvsec-dataset/jca_android/static_analysis/`.

Rótulos: **[conferido]** = medido ou aberto por mim nesta rodada; **[hipótese]** = inferência.

## Resumo

| o que foi implementado | APK que exercita | resultado |
|---|---|---|
| distância e alvo de fronteira (5.3) | treehouses, cry.otp, giggity | idêntico ao protótipo [conferido] |
| JSON parcial carrega as seções novas (5.4) | dsub2000 | idêntico ao completo, com `--skip-wtg` e com a JVM morta dentro da WTG [conferido] |
| fragments por transação, pager e layout | treehouses, dsub2000, etesync | janelas FRAGMENT com widgets; nada perdido [conferido] |
| Navigation (grafo XML) | broccoli, iyps | os 4 destinos `Fragment` do broccoli viram FRAGMENT; iyps tem 6 FRAGMENT e 5 arestas de navegação [conferido] |
| DataBinding (`DataBindingUtil.inflate`) | broccoli, etesync | os 5 pontos de inflação do broccoli viram janelas com widgets [conferido] |
| ViewBinding | treehouses, iyps | widgets recuperados [conferido] |
| diálogos / DialogFragment / bottom sheet / adapters | sexytopo, broccoli, iyps, etesync | janelas HOSTED com widgets [conferido] |
| aresta de lambda | treehouses (45 métodos false→true), cry.otp, etesync (6) | [conferido] |
| spinners com array de recurso | cry.otp | 5 de 5 com opções (sessão 8) |
| Compose (fora do escopo da gh120) | linxshare (só Compose), deku (misto) | não quebra: completo, nada perdido; a UI Compose não é modelada, como esperado [conferido] |

Em nenhum dos 10 APKs comparados com setembro houve janela, widget, par (id, host) ou listener perdido.

## Detalhe

### 5.3: distâncias = protótipo

O protótipo `worktrees-gator/dist` (o `DistanceExporter` do experimento da manhã) foi rodado de novo
com `--skip-wtg` e comparado com o JSON final, por assinatura:

| APK | alvos diretos | fronteira | pares (método, alvo, d) |
|---|---|---|---|
| treehouses | 12 = 12, mesma ordem | 9 = 9 | 153 = 153 |
| cry.otp | 3 = 3 | 0 = 0 | 13 = 13 |
| giggity | 1 = 1 | 0 = 0 | 1 = 1 |

O JSON final usado é o de `worktrees-gator/acc/out/` (jar das 13:36). O jar das 14:30 mudou só o
extrator de spinners; a distância é o mesmo código.

### 5.4: JSON parcial

dsub2000, artefato completo contra dois parciais:

| artefato | `complete` | alvos | 5 176 métodos (flags + distâncias) | 465 widgets FRAGMENT/HOSTED |
|---|---|---|---|---|
| `--skip-wtg` | `true` | iguais | iguais | iguais |
| JVM morta 3 s depois do JSON pré-WTG | **ausente** | iguais | iguais | iguais |

- O parcial sai **sem** a chave `complete`, não com `"complete": false` como diz o hand-off.
  É a convenção dos parciais de setembro.
- Corte por `--analysis-timeout` de 150 s e 165 s: caíram antes do JSON pré-WTG (a WTG do dsub2000
  dura ~20–30 s), sem JSON. O wrapper loga "partial JSON preserved" mesmo sem haver JSON.

### Features novas, contra setembro

| APK | janelas novas | listeners set → hoje | widgets marcados no derive (set → hoje) |
|---|---|---|---|
| broccoli (DataBinding + Navigation) | FRAGMENT 6, HOSTED 7 | 4 → 19 | 0 → 0 |
| etesync (DataBinding) | FRAGMENT 29, HOSTED 8 | 93 → 207 | 0 → 4 |
| iyps (Navigation, ViewBinding) | FRAGMENT 6, HOSTED 15 | 0 → 741 | 0 → 110 |
| linxshare (só Compose) | nenhuma | 0 → 0 | 0 → 0 |
| deku (misto) | nenhuma | 1 → 1 | 0 → 0 |

- broccoli, Navigation: dos 7 destinos do `mobile_navigation.xml`, os 4 que estendem `Fragment` têm
  janela FRAGMENT; os 3 que estendem `PreferenceFragmentCompat` (Settings, About, BackupAndRestore)
  não têm layout de views para modelar, só tela de preferências.
- DataBinding: as janelas existem e têm widgets, mas os listeners declarados em XML
  (`android:onClick="@{…}"`) estão fora do escopo da gh120, e por isso o broccoli continua com poucos listeners.

## Achados para decisão

1. **Custo da WTG no iyps.** Setembro: 106 s no total. Hoje o JSON pré-WTG já estava escrito
   aos 11 min (o horário exato não foi medido), e a WTG (estágio 3) seguia rodando, com 12 núcleos. A causa provável são as 21
   janelas novas que entram na WTG [hipótese]. Se isso se repetir no corpus, mais APKs vão acabar
   no teto de 1 800 s com o JSON parcial. Esse parcial guarda alcance, distância e janelas, mas
   perde as transições da WTG. Para a sua rodada de hoje, isso significa mais APKs "sem `complete`" do que em setembro.
2. **Sexytopo: 137 → 3 071 listeners.**
   - ×13: o diálogo `LegDialogs` é aberto pelo `onOptionsItemSelected` da `SexyTopoActivity`, base de
     todas as activities, e 12 das 13 activities têm o mesmo menu de 14 itens. Uma janela por activity
     segue o código [conferido]; que o item de adicionar estação esteja no submenu de cada uma, eu não conferi [hipótese].
   - os 5 listeners por campo de texto são reais (TextWatcher com 3 métodos, validação, foco) [conferido].
   - **excesso: a mesma árvore do formulário aparece 3 vezes, idêntica, em cada janela** (39 ids × 3).
     Provavelmente é uma cópia por chamada que monta o diálogo (addStation, addSplay, editLeg) [hipótese].
     Não marca widget errado; triplica o volume (JSON 1,4 → 2,95 MB). Corrigir é mudança no GATOR.
3. O nome do dono de algumas janelas HOSTED é a classe de binding gerada (`iyps …#ActivityMainBinding`),
   não o fragment ou a activity. O host está certo; só o sufixo fica feio [conferido].

## Atualização 15:55: WTG do iyps e remoção de duplicados

### WTG lenta: só no iyps, causada pelo código de fragments/ViewBinding

O iyps foi rodado com os jars de cada worktree intermediária [conferido]:

| GATOR | o que contém | segundos |
|---|---|---|
| setembro | — | 106 |
| `dist` | distância + aresta de lambda | 126 |
| `dlg` | diálogos, DataBinding, adapters | 107 |
| `frag` | fragments F1/F2, ViewBinding, fluxo `onCreateView` → `onViewCreated`/`getView` | **991** |
| final | tudo | 1 031 |

- Amostras de pilha (jstack, 5 amostras durante a WTG) [conferido]: o tempo vai no estágio 3 da
  WTG (`CloseWindowEdgeBuilder`), que roda uma `ConstantAnalysis` por callback; o ponto quente é
  `QueryHelper.backwardReachableNodes` sobre o flowgraph. O iyps foi de 0 para 741 listeners e de
  9 para 153 transições: há muito mais callbacks a analisar, e as arestas novas do fluxo de
  fragment deixam o flowgraph mais conectado, de modo que cada consulta para trás percorre mais
  nós [hipótese para a segunda parte; a primeira é contagem].
- Não se repete nos outros. Dos 163, 69 usam ViewBinding, e 15 tinham 0 listeners em setembro,
  como o iyps. Três deles, medidos: pixiv 68 → 57 s, bibleverse 76 → 81 s, lnaddr2invoice
  182 → 137 s (0 → 134 listeners). Nos 12 APKs anteriores, só o iyps ficou mais lento.
- Efeito: um APK como o iyps bate o teto com o JSON pré-WTG completo (alcance, distância,
  janelas); só as transições da WTG ficam de fora.

### Remoção de widgets repetidos (implementada)

`RvsecAnalysisClient.dropRepeatedWidgets`, no fim de `prepareWindows`: em cada janela, de
qualquer tipo, mantém o primeiro dos registros de widget iguais em todos os campos.
Testes `OwnedWindowsTest` (+2), 238 testes do client verdes, build do reator ok, jars em
`lib/gator` às 15:30 [conferido].

| APK | registros antes → depois | conteúdo distinto perdido | listeners |
|---|---|---|---|
| sexytopo | 2 642 → 2 118 | 0 | 3 071 → 2 109 |
| etesync | 920 → 731 | 0 | 207 → 179 |

Os 2 109 listeners restantes do sexytopo são as 13 janelas do `LegDialogs`, uma por activity,
legítimas. As janelas `ACTIVITY` também tinham poucas cópias exatas, vindas do GATOR de
setembro (3 a 12 por APK); elas também saem, e a comparação por multiplicidade com setembro as conta
como "perdidas", sem perda de conteúdo.

A mudança ainda não está nos artefatos da change gh120 (design/spec/tasks).

## Não testado

- APKs grandes (faircode, bitbanana, redreader) e openbible (só Compose, que de manhã bateu 1 800 s antes do JSON pré-WTG).
- fosdem e os demais da aceitação original de 20 APKs.
