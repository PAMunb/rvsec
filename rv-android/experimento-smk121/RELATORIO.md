# Relatório — verificação do carimbo de handler (gh121, grupo 9)

Change `gh121-instr-handler-stamp`, issue #121. Execuções de 07/10/2026, no host, com o
`instr-cli.jar` de sha256 `8880e47f69738b5d5ed002e699a57756959fdc136f4e0ad7a30ba516687a15fb`
e, como referência anterior à change, `ref/instr-cli-pre-gh121.jar` (sha256
`11cb002ac7b3ad8892c61303095a961d1e8dbe5f4af164453171773f1dd28ed3`). Os comandos estão no
`README.md`; os logs, em `results/logs/`.

Quatro APKs: `com.beemdevelopment.aegis_81` (aegis), `dev.itsvic.parceltracker_10501000`
(parceltracker, Compose 1.7), `systems.sieber.droid_scep_7` (droid_scep) e `cryptoapp`.

## Resumo

| Passo | O que verifica | Resultado |
|---|---|---|
| 9.0 | insumos sem o carimbo (descritor `jca_android`, monitores, jars de runtime) | exit 0; `instrument_errors.json` = `{}` |
| 9.1 | desligado idêntico byte a byte ao instrumentador anterior; fonte e classes velhos removidos | 10/10 DEX idênticos; diretório compartilhado limpo, 7/7 DEX idênticos a uma rodada limpa |
| 9.2 | ligado difere só nos sítios do carimbo; contadores MOP iguais | só o DEX de monitores difere após normalização, nos 4 APKs |
| 9.3 | fallback `RVSEC_STAMP_HANDLERS` e opção negativa | 28 chaves com o fallback; 22 (as do desligado) com `--no-stamp-handlers` |
| 9.4 | pipeline no dispositivo: flag, captura, robustez | 4/4 tarefas; nenhum crash com frame do helper, 0 `VerifyError` |
| 9.5 | entrega dos extras a um cliente `UiAutomation` | PASS: 58 nós pareados (49 View, 9 Compose), 58/58 iguais, 0 divergência |

## 9.1 — Desligado é a saída de antes

**Identidade byte a byte.** O parceltracker instrumentado pelo jar de referência e pelo jar
novo sem a opção (e sem `RVSEC_STAMP_HANDLERS`) dá os mesmos 10 `classes*.dex`, 10/10
idênticos pelo md5 bruto (`results/logs/9.1-dexcmp.txt`), confirmados também por
`unzip -p | md5sum`.

**Diretório compartilhado.** Uma rodada com a opção seguida de uma sem ela, no mesmo
`--monitor-src-dir` e `--work-dir`, sobre o cryptoapp (`results/offline/9.1-shared-src/`,
logs `9.1b-*`):

- depois da rodada ligada: `mop/RvsecStamp.java` no diretório de fontes,
  `RvsecStamp.class` e `RvsecStamp$Delegate.class` em `work/monitor-build/classes`;
- depois da desligada: os três ausentes, apagados pelo `instr-cli`;
- o APK desligado tem 0 referências a `Lmop/RvsecStamp`, contra 5 no ligado;
- os 7 `classes*.dex` do APK desligado são idênticos byte a byte aos de uma rodada
  desligada em diretório limpo (`9.2-crypto-off`).

**Correção feita nesta verificação.** A primeira versão dessa checagem
(`results/offline/9.1-shared/`, logs `9.1-shared-*`) não exercitava o fonte velho: o
`instr_one.sh` recopia `<out>/monitors` quando nenhum diretório de monitores é dado, e os
horários dos arquivos mostram que o diretório foi recriado às 17:57:06.30, entre a rodada
ligada (terminada às 17:57:06.25) e a desligada. A metade das classes valia, porque o
`work/` não é recopiado; a metade do fonte foi refeita com o diretório de monitores fora de
`<out>`, como acima.

## 9.2 — Ligado muda só os sítios do carimbo

Para cada APK, ligado contra desligado (`results/logs/9.2-*-dexcmp.txt`, `dexdump`
normalizado):

| APK | DEX comparados | idênticos brutos | diferentes brutos, iguais normalizados | diferentes normalizados |
|---|---|---|---|---|
| aegis | 20 | 11 | 8 | 1 (monitores) |
| parceltracker | 10 | 6 | 3 | 1 (monitores) |
| droid_scep | 4 | 1 | 2 | 1 (monitores) |
| cryptoapp | 7 | 3 | 3 | 1 (monitores) |

Todo DEX do app sai igual após a normalização. O DEX de monitores ligado é o desligado
mais `Lmop/RvsecStamp;` e `Lmop/RvsecStamp$Delegate;`; das cerca de 310 classes comuns,
nenhuma difere quando se ignoram as linhas `Class #N`, cujo índice se desloca com as duas
classes inseridas. Nenhum `invoke-virtual` dos três setters sobra num DEX do app; os 4
restantes estão dentro do próprio helper.

Toda chave de `weaveCounts` que não começa por `stamp` tem o mesmo valor ligado e desligado
(por exemplo `advices` 193, `wrappersGenerated` 141; no aegis, `matchesApplied` 648 e
`wrappersSubstituted` 654). No aegis, os `method_ids` do `classes18` caem de 65 458 para
65 444.

**Correção do normalizador.** O `dexdump` abrevia as pseudo-instruções de payload
(`packed-switch-data`) com `...` na coluna hexadecimal. A regex `INSN` do `dexnorm.py` não
admitia `.` nessa coluna, de modo que o offset de arquivo dessas linhas não era removido e
todo DEX cujo tamanho mudasse aparecia como diferente. A regex passou a admitir o ponto, com
o teste `test_payload_lines_lose_their_file_offset`.

### Contadores do carimbo por APK

Medidos no 9.2 (linha `PerApkResult` de cada log) e de novo no 9.4
(`results/instrumented_apks/instrument_results.json`, caminho `batch` do pipeline), com
valores idênticos:

| APK | click | longClick | delegate | compose | invokeSuperSkipped | ownerNotView |
|---|---|---|---|---|---|---|
| aegis | 118 | 15 | 3 | 0 | 2 | 0 |
| parceltracker | 44 | 6 | 2 | 1 | 2 | 0 |
| droid_scep | 57 | 6 | 3 | 0 | 2 | 0 |
| cryptoapp | 47 | 7 | 3 | 0 | 2 | 0 |

`stampComposeSites` = 1 no parceltracker, o único APK com Compose; 0 nos três apps só de
View.

## 9.3 — Fallback de ambiente

Cryptoapp com `RVSEC_STAMP_HANDLERS=true` e sem a opção: `weaveCounts` com 28 chaves, as seis
`stamp*` entre elas, com os mesmos valores da tabela acima. Com
`RVSEC_STAMP_HANDLERS=true --no-stamp-handlers`: 22 chaves e nenhuma `stamp*`, o mesmo
conjunto das rodadas desligadas.

## 9.4 — Execução no dispositivo pelo pipeline

`rv-experiment run --tools ape --stamp-handlers ... --timeouts 120` sobre os quatro APKs, no
AVD `RVSec` do host (4096 MB de RAM, partição de dados de 8192 MB, 2 núcleos). Pré-
processamento das 18:24 às 18:31, execução das 18:31 às 18:42; 4 de 4 tarefas concluídas, exit 0.

- `experiment_config.json` registra `"stamp_handlers": true`.
- `instrument_errors.json` é `{}`; `instrument_results.json` traz os seis contadores por APK
  (tabela acima).
- 0 `VerifyError` nas quatro capturas; nenhuma linha de `AndroidRuntime` com frame `mop.`;
  nenhuma ocorrência de `RvsecStamp` nos logcats.

### Linhas `RVSEC-BIND` por APK (120 s de APE)

| APK | linhas | view | compose | handler XML `onClick` | remoções (`handler=-`) |
|---|---|---|---|---|---|
| aegis | 61 | 61 | 0 | 0 | 0 |
| parceltracker | 248 | 0 | 248 | 0 | 0 |
| droid_scep | 141 | 141 | 0 | 42 (29,8 %) | 0 |
| cryptoapp | 20 | 20 | 0 | 12 (60,0 %) | 0 |

No parceltracker, 218 das 248 linhas Compose (87,9 %) nomeiam lambdas do app, por exemplo
`dev.itsvic.parceltracker.MainActivityKt$ParcelAppNavigation$6$1$1$$ExternalSyntheticLambda1`
e `...ui.views.HomeViewKt$HomeView$1$1$$ExternalSyntheticLambda0`; as 30 restantes (12,1 %)
são classes internas do Compose (`CoreTextFieldKt` 21, `ExposedDropdownMenuKt` 9,
`CheckboxKt` 1), o limite do campo de texto que a spec registra. As linhas com
`AppCompatViewInflater$DeclaredOnClickListener` são o limite do `android:onClick` em XML,
também registrado; a spec cita 42 de 134 linhas no droid_scep do protótipo (relato), e esta
execução deu 42 de 141.

### Crashes

O critério da tarefa era "zero `FATAL EXCEPTION`". Houve 5, todos no código do próprio app,
e o Pedro aceitou como critério "nenhum crash com frame do helper e nenhum `VerifyError`":

| APK | n | Exceção | Diagnóstico |
|---|---|---|---|
| cryptoapp | 2 | `NullPointerException` em `Context.getPackageName()`, `MainActivity$1.onMenuItemClick:50` | bug proposital do app: `new Intent(null, MessageDigestActivity.class)` no fonte (`examples/cryptoapp`) e no APK original; listener de menu, que o carimbo não reescreve |
| droid_scep | 2 | `NumberFormatException: For input string: ""`, `MonitorFragment$1.afterTextChanged:71` | `Integer.parseInt` sobre campo vazio num `TextWatcher`, caminho que o carimbo não toca |
| aegis | 1 | `RuntimeException: State of SecuritySetupSlide not properly propagated`, `IntroActivity.onDonePressed:96` | lançada por uma checagem do próprio app; sem frame do helper; não comparado com uma rodada sem o carimbo |

### Medida (a): o limite de 4096 do `COMPOSE_LOGGED`

O mapa guarda uma entrada por `semanticsId` logado e é esvaziado ao passar de 4096. No
parceltracker, 120 s de APE produziram 248 linhas Compose com 243 `semanticsId` distintos:
243 entradas, 5,9 % do limite. Nenhum reinício do mapa ocorreu nesta duração. Não há
projeção para outras durações.

## 9.5 — Entrega ao cliente `UiAutomation`

`run_probe.py run --tools stampprobe` sobre os quatro APKs carimbados do 9.4, 60 s por
tarefa (45 s de orçamento da sonda), seguido de `check_delivery.py results/probe`: exit 0,
`paired_view=49 paired_compose=9 mismatch=0 -> PASS` (`results/logs/9.5-check.txt`).

| APK | passos | no app | cliques | `missing` | pareados View | pareados Compose | iguais | divergentes | ambíguos | carimbados sem linha | linhas sem par | linhas `RVSEC-BIND` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aegis | 3 | 2 | 2 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 10 | 16 |
| parceltracker | 3 | 3 | 2 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 11 |
| droid_scep | 17 | 17 | 7 | 9 | 39 | 0 | 39 | 0 | 0 | 0 | 0 | 38 |
| cryptoapp | 5 | 5 | 4 | 0 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 10 |
| **total** | 28 | 27 | 15 | 9 | 49 | 9 | 58 (100 %) | 0 | 0 | 0 | 10 | 75 |

"Pareados" conta nós por captura: o mesmo nó em três capturas conta três vezes. Em nós
distintos com extra, foram 3 (aegis), 9 (parceltracker), 20 (droid_scep) e 6 (cryptoapp).
Nenhuma das 4 capturas de logcat do 9.5 tem `FATAL EXCEPTION`.

O que a navegação alcançou:

- **parceltracker:** a tela inicial (2 nós Compose carimbados: configurações e o botão
  flutuante) e, pelo botão flutuante, a tela de cadastro, com 5 nós Compose pareados.
- **aegis:** a primeira tela é a introdução. O clique em "Import" abriu o seletor de
  arquivos do sistema (`com.google.android.documentsui`); a sonda voltou e relançou o app.
  As 10 linhas sem par são de nós que nenhuma captura mostrou.
- **droid_scep:** dos 16 alvos da primeira tela, 7 foram clicados, entre eles os dois itens
  da barra inferior, que levam a outras telas (5 e 9 nós View pareados). Os 9 `missing`
  (56 %) têm causa conferida: o clique no campo de senha abre o teclado e rola o formulário
  em 172 px; o `BACK` fecha o teclado, mas a rolagem fica, e a sonda procura o alvo pelos
  bounds exatos.
- **cryptoapp:** 4 cliques; o menu de opções (passo 1) abre uma janela popup sem nó pareado.
  Os três botões levam às telas de cada exemplo.

### Medidas (b) e (c) do Compose

- **(b) X → nenhuma ação → X:** um nó cujo extra está ausente enquanto a última linha diz
  um handler apareceria como divergência Compose. Houve 0 divergências Compose em 9 nós
  pareados.
- **(c) bounds do momento do log:** uma linha velha que coincidisse em bounds e classe com
  um nó não clicável também apareceria como divergência; houve 0. Linhas Compose sem par
  no parceltracker: 0.

Com 9 nós Compose pareados, de um só app, essas medidas mostram que os dois casos não
apareceram nesta execução, não que sejam raros em geral.

### Correções feitas nesta verificação

O 9.5 rodou três vezes; as duas primeiras estão guardadas, sem nada apagado:

1. `results/probe-falha1/`: as 4 tarefas falharam antes de a sonda rodar, com
   `'NoneType' object has no attribute 'decode'`. O `_execute_and_check_command` do
   `AbstractTool` usa `stdout=None` por padrão (não captura), e o `_adb` do `run_probe.py`
   só passava os streams quando quem chamava pedia. O `_adb` passou a usar `PIPE` por padrão.
2. `results/probe-raso/`: o check passou (29 View, 6 Compose, 0 divergência), mas toda
   captura pós-clique era a primeira tela de novo, 41 ms a 655 ms depois do `start`. O
   `waitForIdle(500, 5000)` retorna na hora quando já se passaram 500 ms do último evento,
   e logo depois do clique os eventos da nova tela ainda não chegaram. A sonda passou a
   esperar 1 s depois de cada clique e de cada `BACK`, antes do `waitForIdle`; os passos
   passaram a levar de 1,1 s a 3,7 s, e a navegação de um nível passou a acontecer.

A tabela acima é a da terceira rodada, `results/probe/`.

## Efetividade e despachantes (análise da revisão, tarefa 10.3)

Feita depois do grupo 9, sobre os mesmos dados: as capturas `results/probe/`, os logcats e
os traces do APE do 9.4 (`results/<apk>/`), o `dexdump` dos APKs originais e o fixture do
GATOR `modules/aperv-tool/tests/fixtures/cryptoapp.apk.json` (regenerado na gh120). Os
cruzamentos foram feitos com scripts de uso único, não guardados; o método está descrito em
cada medida.

### Quando há carimbo, ele está certo

É a medida do 9.5: 58 de 58 nós pareados com o mesmo handler da linha `RVSEC-BIND`, 0
divergência, 0 nó carimbado sem linha.

### Que fração dos cliques do APE caiu num nó carimbado

As ações `Select action … MODEL_CLICK` / `MODEL_LONG_CLICK` do trace de cada tarefa do 9.4
(428 no total, 120 s por app) foram cruzadas com as linhas `RVSEC-BIND` do mesmo logcat: nó
de View pelo `resource-id` e pelo tipo de evento; nó Compose pelos bounds e pelo tipo de
evento. Um nó conta como carimbado se alguma linha com handler diferente de `-` casa com
ele.

| App | cliques | handler do app | despachante de biblioteca | sem carimbo | View sem id (indeterminado) |
|---|---|---|---|---|---|
| aegis | 132 | 122 (92,4 %) | 0 | 10 | 0 |
| parceltracker | 99 | 43 (43,4 %) | 13 (13,1 %) | 43 | 0 |
| droid_scep | 106 | 6 (5,7 %) | 19 (17,9 %) | 55 | 26 |
| cryptoapp | 91 | 16 (17,6 %) | 2 (2,2 %) | 69 | 4 |
| **total** | 428 | 187 (43,7 %) | 34 (7,9 %) | 177 (41,4 %) | 30 (7,0 %) |

Os 177 cliques sem carimbo, por classe do nó: `EditText` 97 (54,8 %), `TextView` 43 (linhas
`text1` / `title` de listas, popups e menu de overflow, e textos selecionáveis),
`RadioButton` 12, `CheckedTextView` 10, `View` (Compose) 8, `Spinner` 6, `CheckBox` 1. São
nós cujo código do app não é um listener de clique (`TextWatcher`,
`setOnCheckedChangeListener`, `setOnItemSelectedListener`, `setOnItemClickListener`) ou que
caem nos limites registrados (`AlertDialog`); o carimbo cobre os três setters da spec.

Cliques sem `resource-id`: 129 de 428 (30,1 %; no E6 foram 58,6 %). No parceltracker, 56 dos
99 (56,6 %) caíram num nó carimbado; os 30 de droid_scep e cryptoapp são View sem id, que o
log de View não permite cruzar. Com o carimbo, os cliques com alguma chave (`resource-id`
ou carimbo) passam de 299/428 (69,9 %) para pelo menos 355/428 (82,9 %), todo o ganho no
parceltracker.

Ressalvas: o cruzamento por id superestima (um id repetido em várias views, como linhas de
lista, conta como carimbado se alguma tiver carimbo); o cruzamento Compose por bounds
subestima (a linha guarda os bounds do momento em que foi escrita, e 31 dos 43 cliques
Compose sem par têm bounds que nunca aparecem no log); a distribuição é a dos cliques do APE
em quatro apps e uma execução; ter chave não é ter distância do GATOR.

Na sonda do 9.5, medida exata mas pequena, os 24 alvos clicáveis das primeiras telas se
dividem em 6 com handler do app, 5 com despachante (3 `DeclaredOnClickListener`, 2
`NavigationBarMenuView$1`) e 13 sem carimbo (8 `EditText`, 2 `RadioButton`, 1 `Spinner`, 2
botões de overflow do menu).

### O que os despachantes chamam (bytecode dos APKs originais)

Das 470 linhas `RVSEC-BIND` com handler do 9.4, 145 (30,9 %) nomeiam uma classe de
biblioteca. O que cada uma faz no clique, conferido com `dexdump -d`:

| Despachante | linhas | o que chama |
|---|---|---|
| `AppCompatViewInflater$DeclaredOnClickListener` | 54 | `resolveMethod`: percorre a cadeia de `Context` da view (`getBaseContext()` dos `ContextWrapper`) e, em cada um não restrito, `getClass().getMethod(mMethodName, View.class)`; lança `IllegalStateException` se a cadeia acaba |
| `ToolbarWidgetWrapper$1` | 22 | `Window.Callback.onMenuItemSelected(0, mNavItem)`, isto é, a Activity |
| `ActionMenuItemView` | 8 | `MenuItemImpl.invoke`: o `OnMenuItemClickListener` do item; senão o callback do menu (`onOptionsItemSelected` da Activity e, se ela retorna falso, os MenuProviders via `MenuHostHelper`, Fragments inclusive); senão `mItemCallback`, o `Intent` do item e o `ActionProvider`; cada passo só se o anterior retornou falso |
| `NavigationBarMenuView$1` | 9 | `performItemAction` sobre o item; o `OnItemSelectedListener` do app, ou o `OnItemReselectedListener` quando o item já está selecionado |
| `SearchView$5` | 20 | um listener para cinco botões (busca, fechar, enviar, voz e o campo), escolhido pela view clicada; o repasse ao listener do app não foi seguido |
| Compose `CoreTextFieldKt$…$6` | 21 | só `tapToFocus`; o clique não roda código do app |
| Compose `ExposedDropdownMenuKt$expandable$2$1`, `CheckboxKt$Checkbox$1$1` | 10 | a lambda do app capturada em `$onExpandedChange` / `$onCheckedChange`, chamada sem condição |
| Compose `TextLinkScope…` | 1 | não conferido |

Os nomes de campo `mHostView`, `mMethodName`, `mResolvedContext` e `mItemData` estão
intactos nos quatro APKs.

No fixture do GATOR do cryptoapp, o botão `buttonCipher` (um `android:onClick`) tem o handler
`<br.unb.cic.cryptoapp.MainActivity: void showScreenCipher(android.view.View)>`, o mesmo par
classe-método que a resolução do `DeclaredOnClickListener` dá. Os itens de menu ficam numa
janela `OPTIONSMENU`, chaveados pelo `idName`: `menu_item_message_digest` tem o handler
`MainActivity$1.onMenuItemClick` (de `setOnMenuItemClickListener`), e `menu_item_cipher`
não tem handler, embora `MainActivity.onOptionsItemSelected` o trate
(`examples/cryptoapp/.../MainActivity.java:59-64`). Neste fixture, o GATOR não liga
`onOptionsItemSelected` ao item; a causa não foi investigada. Os nós da barra inferior do
droid_scep trazem o id do item de menu como `resource-id` (`action_scep`, `action_monitor`,
`action_extras`).

### Seguimentos possíveis (nada decidido)

- Resolver o `DeclaredOnClickListener` pelo mesmo algoritmo do `resolveMethod` e carimbar a
  classe e o método do app (54 das 145 linhas de biblioteca); é a chave do widget no GATOR.
- Carimbar, nos itens de menu e da barra inferior, o id do item e o primeiro listener do app
  na cadeia de despacho.
- Desembrulhar, no Compose, a lambda do app capturada nos campos `$on…` das lambdas de
  biblioteca.
- Rotear outros setters (`setOnCheckedChangeListener`, `setOnItemClickListener`,
  `setOnItemSelectedListener`).
- Atribuição por execução (o primeiro método do app que roda no despacho de um clique):
  vale para qualquer despachante, mas só depois do primeiro clique no nó; o log de
  cobertura atual não serve, porque só registra a primeira entrada de cada método.
- GATOR: ligar `onOptionsItemSelected` aos itens de menu que ele trata.

## Limites

- **Um nível de navegação.** A sonda clica só os nós clicáveis da primeira tela e captura a
  tela alcançada; telas mais fundas não são lidas. Alvos cujos bounds mudam entre o início
  e o clique (rolagem, teclado) ficam `missing`, sem clique.
- **Reciclagem de linhas não coberta.** Os extras de uma linha de lista reciclada, depois de
  uma troca de listener, não foram exercitados.
- **AVD do host, não o da imagem de campanha.** As execuções usaram o AVD `RVSec` do host
  (4096 MB, 2 núcleos), não o AVD da imagem Docker (1536 MB, 4 núcleos).
- **Um app Compose.** O lado Compose foi visto só no parceltracker (Compose 1.7).
- **Delegate do app embrulhado depois do carimbo não exercitado.** Quando uma view já tem um
  delegate do app ao receber o carimbo e o androidx depois embrulha o delegate (ações de
  acessibilidade do `ViewCompat`, item delegate do RecyclerView), o delegate anterior deixa
  de ser chamado; o carimbo e o comportamento do app fora da acessibilidade não mudam.
  Achado da revisão (10.3), registrado como limite conhecido na spec; nenhum app desta
  verificação passou por essa sequência.

## O que foi medido e o que é relato

**Medido nesta sessão:**
- a segunda checagem do diretório compartilhado do 9.1;
- os contadores do carimbo, de novo, pelo `instrument_results.json` do 9.4;
- o 9.4 e o 9.5 inteiros;
- os diagnósticos dos crashes, inclusive o bytecode do `cryptoapp` original;
- as contagens de linhas e a medida (a).

**Medido na sessão anterior, no mesmo dia, e conferido aqui nos logs de `results/logs/`:**
- a identidade 10/10 do 9.1;
- as comparações do 9.2 (as contagens da tabela por DEX);
- as 28 e 22 chaves do 9.3;
- `matchesApplied` 648 e `wrappersSubstituted` 654 do aegis.

**Medido na sessão anterior e não reconferido aqui:**
- as cerca de 310 classes comuns do DEX de monitores;
- os 4 `invoke-virtual` restantes dentro do helper;
- os `method_ids` do `classes18` do aegis.

**Relato do protótipo:** as 42 de 134 linhas de `android:onClick` no droid_scep, citadas na
spec.
