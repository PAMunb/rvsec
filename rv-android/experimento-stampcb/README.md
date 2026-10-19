# experimento-stampcb — A/B do carimbo com o callback do app

## Propósito

O carimbo da gh121/gh124 (`mop.RvsecStamp`) grava em `rvsec.click` a classe do listener ligado
à view. Em menu, navegação, botão "up" da toolbar, linha de preferência e botão de diálogo
AppCompat, esse listener é um despachante da biblioteca: `ActionMenuItemView`,
`NavigationMenuPresenter$1`, `ToolbarWidgetWrapper$1`, `Preference$1`, `AlertController$1`. O
artefato derivado (`derive_mop_artifact.py`) só cria registro em `handlers` para `onClick(View)`,
`onLongClick(View)` e `invoke`, então o callback do app atrás do despachante também não tem
registro. A guia MOP não enxerga esses cliques.

Os números estão no relatório do mini-experimento,
`rv-android/data/e03igg_analysis/out/rp_guidance/RESULTS.md`, seções B, K e N:

- 47,6 % das linhas `RVSEC-BIND kind=click` dos apps view-only nomeiam classe de biblioteca;
- 616 callbacks com alvo a d ≤ 3 em 52 dos 108 apps de Views e mistos, só 7 deles na tabela;
- passos guiados de 0,6 % nos apps de Views que só têm alvo pela tabela.

Este A/B mede se corrigir os dois elos muda a guia e o que é executado. É experimento, não
change: se compensar, a correção entra por OpenSpec.

## O que muda no braço tratamento

**Carimbo** (`rvsec/.../monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java`,
só o DEX do monitor; os DEX do app não mudam). Ao montar o nó, `Delegate.onInitializeAccessibilityNodeInfo`
chama `RvsecStamp.callback(host, listener)`. Quando o listener é de biblioteca, a função procura
o callback do app:

| despachante | callback lido |
|---|---|
| item de menu (`getItemData()` → `MenuItemImpl`) | `mClickListener` do item; senão o `listener` da `NavigationView`, o `selectedListener` da `NavigationBarView`, ou o `mOnMenuItemClickListener` / provedores da `Toolbar` ancestral; senão o menu de opções da activity |
| `ToolbarWidgetWrapper$1` (up/home) | menu de opções da activity |
| `Preference$1` | `mOnClickListener`, depois `mOnChangeListener`, depois o `mOnPreferenceTreeClickListener` do `PreferenceManager` |
| `AlertController$1` | `obj` da `Message` do botão (o `DialogInterface.OnClickListener`) |

"Menu de opções da activity" significa:
- a própria activity, quando uma classe de app da hierarquia dela declara `onOptionsItemSelected`;
- senão, o primeiro `MenuProvider` de app registrado no `MenuHostHelper` dela.

Achado o callback, a classe dele **substitui** a do despachante em `rvsec.click`, e o logcat ganha a linha
`RVSEC-BIND view kind=callback … handler=<despachante> callback=<app>`. Quando nada é achado,
o nó fica como antes. A substituição nunca perde registro, porque nenhum despachante de
biblioteca está na tabela `handlers`. Toda leitura é por reflexão dentro de `catch (Throwable)`.

**Artefato** (`mount/treatment/derive_mop_artifact.py`, cópia do c6865a73 com
`derive_treatment.patch`): os métodos abaixo também preenchem o evento `click` do registro da
classe:
- `onOptionsItemSelected`, `onNavigationItemSelected`, `onMenuItemClick` e `onMenuItemSelected`, com parâmetro `MenuItem`;
- `onPreferenceClick` e `onPreferenceTreeClick` (`Preference`), e `onPreferenceChange` (`Preference`, `Object`);
- `onClick(DialogInterface, int)`.

**Jar** (ape-rv): não muda. Ele já lê `rvsec.click` e procura a classe em `handlers`.

**Limites conhecidos do tratamento:**
- O `onOptionsItemSelected` de fragment não é nomeado: o carimbo nomeia a activity.
- Com vários `MenuProvider`, só o primeiro é nomeado.
- Ficam de fora: o item do menu overflow (popup sem listener ligado), o `AdapterView.onItemClick`, o `CompoundButton.onCheckedChanged` (exigiria tecer setter novo), o `AlertDialog` do framework e o `android.preference`.
- A distância do callback vale para o método inteiro. Todos os itens de um mesmo menu recebem o mesmo registro: a guia aponta o menu, não o item.
- Quando a activity também é `OnClickListener`, o registro dela funde `onClick(View)` com `onOptionsItemSelected` (OR das marcas, mínimo das distâncias). É a imprecisão da opção mínima; a alternativa é uma chave separada no nó, com mudança no jar.

## Desenho

- **APKs** (`apks.txt`), escolhidos por `scripts/select_apks.py` (`candidates.csv`). Todos têm, no logcat do e03igg, despachantes de menu/preferência/diálogo ligados, e callbacks que o carimbo novo consegue nomear com registro a d ≤ 3:
  - `be.digitalia.fosdem` — âncora: 0 passos guiados no e03igg;
  - `com.beemdevelopment.aegis` — preferência + diálogo, 2 alvos JCA diretos só atrás de callback;
  - `app.michaelwuensch.bitbanana` — `certToPEM` só atrás de callback;
  - `se.arctosoft.vault` — `deleteBiometricSecretKey` só atrás de callback;
  - `org.openhab.habdroid` — menu e preferência; site de misuse okio a d 4;
  - `me.timschneeberger.rootlessjamesdsp` — preferência pesada; `getMd5`, misuse visto só no `mop`.
- **Braço** `aperv:mop`, preset do snapshot `c6865a73_k1` (o `mop` da e03igg3), 3 réplicas × 300 s. Imagem 0.9.5 `cdaeba4a`.
- **Controle**: APKs do corpus E6 v2 (rep pack `data/raw/e6-corpus`) + `mount/control`, byte-idêntico a `data/e03igg_mount/c6865a73_k1` (ver `SHA256SUMS`).
- **Tratamento**: `apks_treatment/` + `mount/treatment`.
- **Contêineres**: 4, dois por braço (`filters/half_a.txt`, `half_b.txt`), 3 APKs cada; ≈ 1 h de relógio.

### Jar de instrumentação do tratamento

`jar/instr-cli-treatment.jar` (sha256 `2f93e001…`) é o próprio `instr-cli.jar` da imagem de
instrumentação do corpus (`7ea5a6f5`, sha256 `7ef7e0d2…`), com só
`br/unb/cic/rv/builder/stamp/RvsecStamp.java` trocado pelo da worktree. O jar 582e7520 do
repositório e o da imagem têm o mesmo `RvsecStamp.java`; diferem em 3 classes porque a imagem
compila com JDK 25. Partir do jar da imagem deixa o patch do helper como a única diferença
para o corpus.

## Passos

1. **Instrumentar** (CPU, sem emulador, ~minutos):
   `docker compose -p stampcb-instr -f docker-compose.instrument.yml up`
2. **Montar e conferir**: `scripts/stage_treatment.sh`. Copia os APKs para `apks_treatment/`,
   junto do `.apk.json` do corpus, e roda `check_dex.py`. Portão: em cada APK, todos os
   `classes*.dex` idênticos ao corpus, salvo um, o que define `Lmop/RvsecStamp;`.
3. **Rodar o A/B**: `docker compose -p stampcb -f docker-compose.ab.yml up -d`.
4. **Analisar** (script a escrever depois da corrida):
   - entrega: linhas `RVSEC-BIND kind=callback` por APK e por família;
   - sanidade: nenhum crash com frame de `mop.RvsecStamp` e nenhum `VerifyError`;
   - guia: fração de passos com `dec.mopd` e `dec.mops` com origem STAMP por braço;
   - execução: os callbacks nomeados e os alvos JCA diretos "só atrás de callback" (RVSEC-COV);
   - misuses: `RVSEC-OCC` por braço.

Verificação offline já feita:
- `scripts/compare_handlers.py` mostra que, no fosdem, o tratamento dá registro a d ≤ 3 a
  `MainActivity`, `MainActivity$$ExternalSyntheticLambda0`,
  `ExternalBookmarksListFragment$onViewCreated$menuProvider$1` e
  `SettingsFragment$$ExternalSyntheticLambda5`;
- 32/32 testes do monitor-builder passam, incluindo os 7 novos em `RvsecStampCallbackTest`
  (caminho de preferência e de provedores de menu; os caminhos que precisam de `View` só são
  testáveis no dispositivo).

## Resultados (corrida de 19/10/2026, 15:19–16:15)

A opção 1 (o carimbo grava o callback do app em `rvsec.click`, e o derive dá registro `click` aos
métodos de callback) é implementada pela change OpenSpec `gh-tbd-stamp-app-callback`.

36/36 tarefas (2 braços × 6 APKs × 3 réplicas × 300 s), os 4 contêineres saíram com 0. Tabelas
em `analysis/`, geradas por `python -I scripts/analyze.py`; o cruzamento dos crashes do vault, por
`python -I scripts/vault_crash.py results`. Rótulos: **[conferido]** lido nos logcats/traces;
**[inferido]** interpretação.

**Entrega** [conferido]. O tratamento escreveu 3 163 linhas `RVSEC-BIND view kind=callback`
(controle: 0), nos 6 APKs: preferência 2 105, menu/navegação/toolbar 808, diálogo 250
(`delivery.csv`). Nomeou 167 classes de callback distintas (`callbacks.csv`); 41 delas são
classes que o derive do tratamento passa a ter com par a d ≤ 3 (`added_handlers.csv`: 104 no total
nos 6 APKs). As demais são nomeadas mas seguem sem distância.

**Sanidade** [conferido]. Nenhum frame `mop.RvsecStamp` e nenhum `VerifyError` em 36 logcats. Os
`FATAL EXCEPTION` do processo do app (`sanity.csv`): controle 36, tratamento 48; por APK
11/11 fosdem, 10/14 aegis, 4/3 bitbanana, 6/18 vault, 5/2 habdroid, 0/0 rootlessjamesdsp. Todos
são exceções do próprio app, dos mesmos tipos nos dois braços. A diferença está no vault: o NPE
`DirHash.hash()` (3 × 13) e o `PasswordFragment not attached` saem de uma thread de fundo do app
(`DirectoryFragment.addRootFolders`), e os 24 crashes do vault vêm todos depois de um passo de
origem `sata`, nunca `mop`: "Unlock" com senha aleatória seguido de BACK no estado desbloqueado
(BACK em `g0s3` por réplica 3/0/4 no controle, 6/4/6 no tratamento; crashes 3/0/3 e 8/4/6). O
handler do Unlock (`PasswordFragment$$ExternalSyntheticLambda1`) é `onClick` direto, fora das
famílias tratadas. [inferido: corrida do app entre o BACK que tranca o cofre e a thread que lê a
chave; o SATA a disparou mais vezes no tratamento, sem papel do carimbo.]

**Guia** [conferido] (`steps_summary.csv`; por réplica em `steps.csv`).

| APK | passos con / tre | `dec.mopd` con | `dec.mopd` tre | `mops = s` con | `mops = s` tre |
|---|---:|---:|---:|---:|---:|
| fosdem | 696 / 709 | 0 (0,0 %) | 39 (5,5 %) | 13 (1,9 %) | 289 (40,8 %) |
| aegis | 877 / 951 | 36 (4,1 %) | 73 (7,7 %) | 119 (13,6 %) | 332 (34,9 %) |
| bitbanana | 1 093 / 1 081 | 191 (17,5 %) | 198 (18,3 %) | 283 (25,9 %) | 317 (29,3 %) |
| vault | 874 / 892 | 86 (9,8 %) | 125 (14,0 %) | 152 (17,4 %) | 230 (25,8 %) |
| habdroid | 650 / 762 | 58 (8,9 %) | 114 (15,0 %) | 64 (9,8 %) | 243 (31,9 %) |
| rootlessjamesdsp | 952 / 892 | 43 (4,5 %) | 98 (11,0 %) | 245 (25,7 %) | 353 (39,6 %) |
| **todos** | 5 142 / 5 287 | **414 (8,1 %)** | **647 (12,2 %)** | 876 (17,0 %) | 1 764 (33,4 %) |

- No tratamento, 289 dos 647 passos com `dec.mopd` têm `dec.hnd` numa classe que só o derive do
  tratamento põe a d ≤ 3; os outros 358 ficam perto dos 414 do controle.
- Passos de origem `mop`: 177 → 335.
- `dec.mopd` por réplica (%), controle | tratamento: fosdem 0/0/0 | 4,4/6,5/5,5; aegis 3,7/3,2/5,3 |
  0,0/15,6/11,5; bitbanana 15,0/19,6/17,5 | 16,4/14,6/23,1; vault 9,8/9,0/10,7 | 14,8/13,6/13,7;
  habdroid 14,4/4,8/8,6 | 14,9/15,1/14,9; rootlessjamesdsp 2,8/8,6/1,9 | 9,7/10,6/13,3.
- A réplica 1 do aegis no tratamento ficou presa na `IntroActivity` (`btnNext` 81 e `btnImport` 73
  dos 415 passos, todos `sata`) e não chegou a tela com registro. [inferido: o onboarding, não o
  tratamento.]

**Execução** [conferido]. Das 167 classes de callback nomeadas, RVSEC-COV viu um método de
callback da classe (método da família, ou qualquer método de classe lambda) em pelo menos uma
réplica: 90 no controle, 109 no tratamento (réplicas somadas 185 × 231). 54 classes subiram no
tratamento e 29 desceram; o ganho está em habdroid (20 → 29) e bitbanana (10 → 17). Os 7 alvos JCA
diretos "só atrás de callback" (faixas 2 e 4 de `r_direct_full.csv`; `direct.csv`) não mudaram:
`isAppLockActive` (bitbanana) e `enableBiometrics` (vault) executaram nas 3 réplicas dos dois
braços; `certToPEM`, `KeyStoreHandle.<init>`, `KeyStoreHandle.generateKey`,
`VaultEntryIcon.generateHash` e `deleteBiometricSecretKey` em nenhuma.

**Misuses** [conferido] (`misuses.csv`; site primário = classe, método, spec com rótulo
`violation` ou `sequence`, como `extract.py`). União das réplicas, controle × tratamento: fosdem
0 × 0, aegis 2 × 2 (`HOTP.getHash`, em 1 réplica cada), bitbanana 4 × 4, vault 0 × 0, habdroid
2 × 3, rootlessjamesdsp 0 × 0. O site a mais do habdroid é `PrfAesCmac.compute` (CipherSpec, tink),
em 2 das 3 réplicas do tratamento. Linhas RVSEC-OCC: 1 763 × 2 036.

**Leitura** [inferido]. Os dois elos consertados juntos fazem a guia chegar aos cliques de menu,
preferência e diálogo: a fração de passos com `dec.mopd` sobe de 8,1 % para 12,2 % no total, e
fosdem sai de zero. Isso aumenta a execução de callbacks, mas pouco e com ruído (3 réplicas). Não
alcança nenhum alvo JCA novo só atrás de callback, e só acrescenta um site de misuse, de
biblioteca. Com 6 APKs e 3 réplicas, o efeito na guia é claro; o efeito em misuses não se
distingue de zero.

### H2 e H3 (análise de 19/10/2026, sobre os mesmos dados)

Pedidas pela sessão `aperv`: a guia subiu de 8,1 % para 12,2 %, mas nenhum alvo só atrás de
callback ganhou cobertura. Scripts `scripts/h2_preferences.py` e `scripts/h3_never_run.py`
(definições e janelas na docstring); tabelas `analysis/h2_*.csv` e `analysis/h3_never_run.csv`.
O derive offline confere com o `MOP_DATA` dos 36 traces (handlers e alvos) [conferido].

**Parâmetros do jar** [conferido]. Os 36 `RUN_START` têm `ape.mopCoinLedgerMaxInteractions = 2`
(o `tool.py` do mount fixa 2; o default do jar é 1) e nenhum sobrescreve `ape.mopRetireAfter`,
que fica no default 3 (`KeyOwnership`, jar 2cfa8ee2). Regra de aposentadoria
(`MopRetirement.onFirstInteraction`, `StatefulAgent.recordMopInteraction`): na **primeira**
interação de cada chave (activity, `xpath|ActionType`) com peso > 0, soma 1 a cada alvo que está a
d* no registro que deu o peso; com contagem ≥ 3 o alvo sai e aparece em `dec.ret` do passo. O
k = 2 limita só a elegibilidade da moeda MOP por chave, não a aposentadoria.

#### H2 — as preferências diluem a guia?

**H2.1 Família dos 647 passos guiados do tratamento** [conferido] (família do despachante nas
linhas `kind=callback` da mesma tarefa que nomeiam o `dec.hnd`; `dec.hnd` só existe com
`mops = s`, então `mops = i` é o caminho por id):

| APK | preferência | menu/nav | diálogo | carimbo original | id | controle (todos originais) |
|---|---:|---:|---:|---:|---:|---:|
| fosdem | 11 | 28 | 0 | 0 | 0 | 0 |
| aegis | 26 | 11 | 6 | 22 | 8 | 36 |
| bitbanana | 0 | 12 | 0 | 170 | 16 | 191 |
| vault | 20 | 0 | 0 | 105 | 0 | 86 |
| habdroid | 44 | 44 | 3 | 23 | 0 | 58 |
| rootlessjamesdsp | 84 | 0 | 0 | 14 | 0 | 43 |
| **todos** | **185 (28,6 %)** | **95 (14,7 %)** | **9 (1,4 %)** | **334** | **24** | **414** |

Nenhum `dec.hnd` foi nomeado em duas famílias. As preferências respondem por 185 dos 289 passos
guiados das famílias novas (64,0 %), concentrados em rootlessjamesdsp (84 de 98 guiados) e
habdroid (44 de 114).

**H2.2 O passo guiado é seguido pela execução do alvo ponderado?** Alvo ponderado = pares a
d = `dec.mopd` do registro que deu o peso (derive do braço). Execução = `RVSEC-COV` da assinatura
do alvo. Janela: o intervalo do próprio passo, [t_s, t_{s+1}) (N = 0), porque o callback de um
clique roda na thread de UI antes do passo seguinte; e mais dois passos (N = 2) para caminhos com
um diálogo ou transição no meio. Como `RVSEC-COV` só registra a primeira execução por processo,
passos cujos alvos já tinham sido registrados no processo corrente não podem ser testados e vão à
parte ("já executado") [conferido, salvo a escolha do processo corrente, que é o pid da última
linha COV antes do passo: inferido].

| família (tratamento) | guiados | já executado | testados | executou, N = 0 | executou, N = 2 |
|---|---:|---:|---:|---:|---:|
| preferência | 185 | 98 (53,0 %) | 87 | 37 (42,5 %) | 48 (55,2 %) |
| menu/nav | 95 | 59 (62,1 %) | 36 | 22 (61,1 %) | 22 (61,1 %) |
| diálogo | 9 | 2 | 7 | 6 | 6 |
| carimbo original | 334 | 231 (69,2 %) | 103 | 58 (56,3 %) | 68 (66,0 %) |
| id | 24 (8 sem registro achado) | 0 | 16 | 0 | 4 |
| controle, carimbo original | 384 | 249 (64,8 %) | 135 | 54 (40,0 %) | 65 (48,1 %) |

- Todos os passos de preferência têm d = 2 ou 3; nenhum é d = 0, que seria o próprio callback
  (`h2_followed_by_d.csv`). A d = 3, preferência executa o alvo em 14 de 50 testados (N = 2), o
  carimbo original em 39 de 59; a d = 2, 34 de 37 contra 18 de 30 [conferido].
- Alvos distintos executados após um passo guiado (N = 2, `h2_novel.csv`): preferência 22, dos
  quais 3 não aparecem em nenhuma réplica do controle (2 do habdroid em `MainSettingsFragment` e
  `ServerEditorFragment`, `BenchmarkManager.clearBenchmarks` do rootlessjamesdsp); menu/nav 5,
  diálogo 2, carimbo original 16, id 1 — nenhum novo em relação ao controle [conferido]. São
  alvos `boundary`, não JCA direto.

**H2.3 A guia migra para telas de configuração?** Tela de preferência = estado do APE (`st`) que
tem linha de preferência androidx: o carimbo escreve `kind=click handler=androidx.preference.Preference$1`
nos dois braços quando a linha é ligada, no intervalo antes do primeiro passo que vê a tela
[inferido: a regra acha 151 dos 185 passos guiados de preferência, 81,6 %].

| APK | passos em tela de pref. con → tre | guiados fora da família preferência con → tre | só caminho original con → tre |
|---|---|---|---|
| fosdem | 40/696 → 62/709 | 0 → 28 | 0 → 0 |
| aegis | 211/877 → 70/951 | 36 → 47 | 36 → 30 |
| bitbanana | 7/1 093 → 16/1 081 | 191 → 198 | 191 → 186 |
| vault | 74/874 → 71/892 | 86 → 105 | 86 → 105 |
| habdroid | 118/650 → 298/762 | 58 → 70 | 58 → 23 |
| rootlessjamesdsp | 436/952 → 454/892 | 43 → 14 | 43 → 14 |
| **todos** | 886/5 142 (17,2 %) → 971/5 287 (18,4 %) | **414 → 462** | **414 → 358** |

- No total, a exploração não migra para as telas de preferência (17,2 % → 18,4 % dos passos) e
  os guiados fora da família preferência sobem de 414 para 462 [conferido].
- Há deslocamento em dois APKs [conferido]: no rootlessjamesdsp os guiados que não são de preferência caem de 43
  para 14 enquanto os de preferência são 84; no habdroid os passos em tela de preferência sobem
  de 18,2 % para 39,1 % e o caminho original cai de 58 para 23, compensado por 44 de menu/nav e
  44 de preferência. [inferido: a moeda MOP prefere o widget de maior peso, e as linhas de
  preferência, que somam pares a d 2–3 numa tela com muitas linhas, passam à frente dos widgets
  do caminho original.]
- A queda do aegis em telas de preferência (211 → 70) acompanha a réplica 1 presa na
  `IntroActivity` [inferido].

**H2.4 Aposentadoria** [conferido] (`h2_retired.csv`). O tratamento aposentou 31 alvos-passo
(preferência 11, menu/nav 11, carimbo original 9), o controle 11 (todos carimbo original); todos
em passos de origem `mop`. Nenhum dos 11 aposentados por um passo de preferência tinha sido ou
foi depois ponderado por um passo guiado de outra família na mesma tarefa. O único alvo
aposentado que outra família ponderava é `EditEntryActivity.showGroupSelectionDialog` (aegis),
aposentado pelo carimbo original e ponderado antes por 4 passos de id, nos dois braços (controle
3 réplicas, tratamento 2).
Mecanismo que pesa [conferido no vault, H3]: como todas as linhas de uma tela de preferência
compartilham o registro do mesmo callback (H1), três linhas (ou três nós da mesma linha) clicadas
pela primeira vez aposentam juntos todos os alvos a d* desse registro, inclusive um que os
cliques não executam.

**Leitura de H2** [inferido]. Há diluição, mas local: em rootlessjamesdsp e habdroid a guia passa
para as linhas de preferência e o caminho original perde passos guiados. No total não há
deslocamento, e os passos de preferência executam o alvo ponderado numa proporção próxima da do
caminho original (42,5 % × 56,3 % em N = 0), com 3 alvos `boundary` novos. As preferências não
explicam a ausência de alvo JCA novo; H3 explica.

#### H3 — os 5 alvos nunca executados

Cadeias pela `targetDistances` do JSON completo do GATOR (um único método por nível de distância
em cada caso) e todos os elos lidos no baksmali do APK do corpus [conferido]:

| alvo | callback (d) | intermediários | registro na tabela, con / tre |
|---|---|---|---|
| `certToPEM` (bitbanana) | `CertInputView$1.onTabSelected` (2) | `CertificateUtil.DER_To_PEM` (1) | sem / sem |
| `KeyStoreHandle.<init>` (aegis) | `SecurityPreferencesFragment$$ExternalSyntheticLambda3.onPreferenceChange` (3) | `$r8$lambda$q1q2…` (2), `lambda$onCreatePreferences$5` (1) | sem / click d 3 |
| `KeyStoreHandle.generateKey` (aegis) | o mesmo (4) | `$r8$lambda` (3), `lambda$5` (2), `BiometricSlotInitializer.authenticate` (1) | sem / sem par (d 4 > 3) |
| `VaultEntryIcon.generateHash` (aegis) | `AssignIconsActivity.onOptionsItemSelected` (3) | `saveAndFinish` (2), `VaultEntryIcon.<init>` (1) | sem / click d 3 |
| `deleteBiometricSecretKey` (vault) | `SettingsFragment$$ExternalSyntheticLambda6.onPreferenceChange` (3) | `$r8$lambda$Jf4c…` (2), `lambda$onCreatePreferences$8` (1) | sem / click d 3 |

Condições no bytecode e o que rodou [conferido, salvo onde marcado]:

- **`deleteBiometricSecretKey`.** `lambda$8` chama `enableBiometrics()` quando o novo valor é
  `true` e `deleteBiometricSecretKey()` quando é `false`. `enableBiometrics` devolve `false` (o
  switch não liga) quando `BiometricManager.canAuthenticate(0xf) != 0`, antes de
  `getBiometricCipher`. O callback executou nas 6 réplicas (controle por passos `sata`,
  tratamento 1 por `sata` e 2 por `mop`); `enableBiometrics` em todas; `getBiometricCipher` em
  nenhuma. Logo o switch nunca ficou ligado, e desligá-lo é a única entrada do alvo. No
  tratamento, a moeda escolheu o switch 5 vezes por réplica nas réplicas 2 e 3 (duas chaves × 2,
  o k = 2, mais uma terceira chave), todas com `mopd = 3`; a terceira primeira interação
  aposentou juntos `enableBiometrics` (3) e `deleteBiometricSecretKey` (15), nos passos 26 e 202.
  O ledger não atrapalhou: nenhum número de cliques liga o switch sem biometria cadastrada no
  emulador.
- **`KeyStoreHandle.<init>` e `generateKey`.** `lambda$5` chega a `<init>` nos dois ramos: sem
  `BiometricSlot` e com `BiometricsHelper.isAvailable` (o mesmo `canAuthenticate(0xf) == 0`) →
  `BiometricSlotInitializer.authenticate`, que cria o `KeyStoreHandle` e chama `generateKey`; ou
  com `BiometricSlot` já existente → remoção do slot. `updateEncryptionPreferences` só deixa o
  switch visível com o cofre cifrado e só o habilita com `isAvailable`. `PasswordSlot.<init>`
  não rodou em nenhuma das 6 réplicas, nem `SecuritySetupSlide.showBiometricPrompt`; nenhuma linha
  `kind=callback` nomeou o `Lambda3` no tratamento, e nenhum passo teve esse `dec.hnd`. [inferido:
  cofre sem senha, switch invisível; e, mesmo com senha, o emulador não tem biometria cadastrada,
  como o vault mostra no mesmo AVD.] `generateKey` ainda está a d 4 do callback, fora da tabela.
- **`VaultEntryIcon.generateHash`.** `saveAndFinish` só cria `VaultEntryIcon` para entradas com
  `getNewIcon() != null`, o que exige um pacote de ícones importado (`IconPacksManagerFragment
  .importIconPack`: 0 em 6 réplicas). A activity só é aberta pelo fluxo do pacote de ícones; nas
  6 réplicas o lançador MOP (`EVENT_TRIGGER_ACTIVITY`) a abriu diretamente e ela caiu com
  `NullPointerException` no `onCreate` (falta o extra da intent): 0 passos nela. O outro caminho,
  `EditEntryActivity.onSave` → `parseEntry` (rodou em 3 réplicas), só chega a
  `toVaultEntryIcon` com `_hasChangedIcon` e `_hasCustomIcon`, isto é, com um ícone escolhido
  (imagem ou pacote); não rodou. Esse callback (`EditEntryActivity.onOptionsItemSelected`) está
  a d 4.
- **`certToPEM`.** `onTabSelected` lê o texto da aba; só "PEM" chama `DER_To_PEM`, cuja primeira
  chamada é `certToPEM`, sem outra condição. `CertInputView` foi construída em 4 réplicas
  (controle 1, tratamento 1–3), na `ManualSetup`; `onTabSelected` rodou uma vez (tratamento,
  réplica 2, passo 139, `sata`/`roulette_early`) e a aba escolhida foi Base64
  (`convertCurrentDataToBase64` rodou). `onTabSelected` é listener de `TabLayout`, fora das
  famílias do tratamento: nem o carimbo nem o derive o cobrem, nos dois braços não há registro.

**Classificação** (a: callback nunca alcançado; b: alcançado, mas exige estado ou entrada; c:
caminho irreal em tempo de execução):

| alvo | classe | motivo |
|---|---|---|
| `deleteBiometricSecretKey` | **b** [conferido] | callback em 6/6 réplicas; exige o switch ligado, que exige biometria cadastrada |
| `KeyStoreHandle.<init>` | **a**, por estado [conferido; causa inferida] | switch invisível sem cofre cifrado e desabilitado sem biometria |
| `KeyStoreHandle.generateKey` | **a**, por estado e fora de d ≤ 3 [conferido] | idem, e o callback está a d 4 |
| `VaultEntryIcon.generateHash` | **a**, por estado [conferido] | exige pacote de ícones importado; o lançamento direto da activity cai |
| `certToPEM` | **b** [conferido] | callback alcançado 1 vez sem guia; exige escolher a aba PEM; fora do escopo do tratamento |

Nenhum é (c): todos os elos existem no bytecode. **Leitura de H3** [inferido]: os 5 alvos não
dependem de a guia chegar ao callback, e sim de estado que o emulador ou a exploração não criam
(biometria cadastrada, cofre cifrado, pacote de ícones) ou de uma entrada específica (aba PEM).
Dois deles (`certToPEM` por família, `generateKey` por d 4) estão fora do alcance do tratamento
por desenho. Responder se cadastrar biometria no AVD ou semear um pacote de ícones mudaria o
quadro exige corrida nova; não foi feita.
