# experimento-smk124 — relatório

Verificação da change `gh124-compose-stamp-f0-material` (issue #124): o carimbo Compose segue o nó
clicável por `f$0` quando ele é um `androidx.compose.foundation.AbstractClickableNode` e desembrulha uma
vez um handler `androidx.compose.material*` com exatamente um campo `kotlin.jvm.functions.Function*`
(também no fallback da lambda da ação, decisão confirmada pelo Pedro em 10/10/2026).

## Jars

| Jar | sha256 | Origem |
|---|---|---|
| referência (`baseline/instr-cli.jar`) | `8880e47f69738b5d5ed002e699a57756959fdc136f4e0ad7a30ba516687a15fb` | `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` de 07/10 17:40; o recurso `RvsecStamp.java` dentro dele é idêntico ao do HEAD `af520e4e` (`diff` vazio) |
| gh124 (`equiv/new-instr-cli.jar`) | `582e75208b4547769151cc29ee9994ef37e10e434ed4a3fa47adae33360f3e7a` | build do reator de 10/10 09:29 (`mvn clean install -o -DskipMopAgent -DskipTests`, JDK 21, BUILD SUCCESS em 1:36) |

## Testes (4.2, 4.3)

`mvn -o test` em `rvsec-instrumentation-dexlib2` (log em `equiv/test.log`): 626 testes em 10
submódulos, 0 falhas, 0 erros, 0 pulados. Em `monitor-builder`, `RvsecStampComposeTest` 13/13 e
`StampSourceEmitterTest` 3/3 (inclui `theSourceCompilesAgainstAndroidJarAtJava8`).

Execução vermelha (2.4), com o `RvsecStamp.java` do HEAD posto à frente no classpath de teste:
13 testes, 6 falhas — exatamente os de `f$0` e Material (`fZeroClickableNodeIsUnwrapped`,
`fZeroToggleableReadsOnValueChange`, `fZeroCombinedLongClick`, `checkboxD8FormIsUnwrapped`,
`checkboxKotlincFormIsUnwrapped`, `materialActionLambdaFallbackIsUnwrapped`). Passaram os de
`this$0`, `f$0` que não é nó, ação ausente, embrulho mantido (função de biblioteca, duas funções,
função nula) e handler fora de Material.

Depois da revisão (6.3), o teste ganhou dois casos do passo do nó por `f$0`: `ToggleableNode` com
`onValueChange` nulo cai em `onClick` (`fZeroToggleableWithNullOnValueChangeReadsOnClick`), e nó com
`onClick` nulo cai na lambda da ação (`fZeroNodeWithNullOnClickFallsBackToActionLambda`). Além disso, o
harness passou a relançar um `Error` do helper sem cast para `Exception`. Com `mvn -o test` em
`monitor-builder`, `RvsecStampComposeTest` deu 15/15 e `StampSourceEmitterTest` 3/3, nada pulado.
`RvsecStamp.java` não mudou, de modo que o jar `582e7520…` e o smoke abaixo continuam valendo.

## Equivalência no saucenao (4.4)

`com.luk.saucenao_27.apk` original (`rvsec-dataset/head_apks`), instrumentado no host pelos dois jars
com `--stamp-handlers` e monitores `jca_android` do smk121 (`scripts/instrument.py`). Comparação por
`experimento-smk121/scripts/dexcmp.py` (saída em `equiv/dexcmp.txt`):

- `classes.dex` … `classes9.dex` (os DEX do app): **idênticos byte a byte** (md5 bruto igual nos 9).
- `classes10.dex` (o DEX do monitor): difere; `method_ids` 3767 → 3771.
- `weaveCounts`: **iguais em todos os campos** (`matchesApplied 16`, `advices 193`,
  `stampClickSites 21`, `stampLongClickSites 5`, `stampDelegateSites 2`, `stampComposeSites 1`, …).

No DEX do monitor, separado por classe e normalizado pelo `dexnorm` (saída em
`equiv/monitor_dex_per_class.txt`): 308 classes nos dois, nenhuma a mais ou a menos; só
`mop.RvsecStamp` e `mop.RvsecStamp$Delegate` diferem. No `Delegate` a diferença é apenas de
informação de depuração — os números de linha da tabela de posições (deslocados pelos Javadocs novos do
mesmo arquivo-fonte) e o índice de `source_file_idx` — sem nenhuma instrução diferente. A mudança de
código fica dentro de `mop.RvsecStamp`.

## Smoke no dispositivo (5.1–5.5)

APKs originais de `rvsec-dataset/head_apks`, instrumentados no host pelo jar gh124 (`582e7520…`) com
`--stamp-handlers` (`scripts/instrument.py`; log em `apks/instrument.log`), 3/3 com sucesso, todos com
`stampComposeSites=1`. Cada `.apk.json` é o do e6-corpus (o do saucenao é idêntico ao do A/B), ligado ao
lado do APK. Imagem `phtcosta/rvandroid:0.9.5` local = `643954ddc72f` (criada 10/10 08:32; o `1f34ddec`
do A/B não existe mais; a imagem não altera o carimbo, que vai no DEX do monitor do APK). Braço
`aperv:mopd_on_llm_off`, 300 s, 1 rep, um container por APK (`docker-compose.yml`, `restart: "no"`),
lançados às 09:43; 3/3 tarefas COMPLETED (09:49–09:52). Análise por `scripts/analyze.py` (saídas em
`results/_analysis_<apk>.txt`; o `.mop.json` de cada execução, lido por um container descartável, em
`results/_mop/`).

| APK | foundation / forma | entradas `RVSEC-BIND` Compose app / material / outras libs | classes do app distintas (em `handlers`) | formas da gh124 no BIND | `stampNodes` / `stampHits` | decisões `src=MOP` | FATAL com `mop.RvsecStamp` / `VerifyError` |
|---|---|---:|---:|---:|---:|---:|---:|
| `com.luk.saucenao_27` | 1.9.5 / `f$0` | 811 / 0 / 48 | 8 (8) | 0 | 2140 / 137 | 30 | 0 / 0 |
| `at.techbee.jtx_216000015` | 1.11.2 / `f$0` | 499 / 592 / 70 | 88 (88) | 0 | 3844 / 144 | 86 | 0 / 0 |
| `app.plugbrain.android_154` | 1.7.8 / `this$0` | 68 / 0 / 10 | 7 (7) | 0 | 910 / 50 | 0 | 0 / 0 |

("Entradas" conta `handler=` e `longClickHandler=` de cada linha; "formas da gh124" são
`AbstractClickableNode$$ExternalSyntheticLambda*`, `CheckboxKt$$ExternalSyntheticLambda6` e
`CheckboxKt$Checkbox$1$1`.) Nenhum bloco `FATAL EXCEPTION` nos três logcats.

- Toda classe do app que o carimbo nomeia é chave de `handlers` (103 de 103).
- No saucenao, as linhas de Checkbox que no A/B patched nomeavam `CheckboxKt$$ExternalSyntheticLambda6`
  (262) nomeiam agora a `Function1` do app.
- No plugbrain (forma `this$0`, foundation 1.7.8), nenhuma entrada nomeia lambda de nó clicável
  da foundation; as 10 de outras libs são a semântica do campo de texto (`CoreTextFieldKt$CoreTextField$semanticsModifier$1$1$6`/`$7`, 5 + 5). Neste app a guia não tomou
  decisão MOP em 300 s, embora `stampHits = 50`.

### Onde a etapa Material mudou o carimbo (5.4)

O logcat grava só a classe final, não a anterior à etapa Material. A atribuição abaixo é **inferência**
por fatos estáticos do DEX instrumentado: o papel do nó (`node=`), a interface `Function*` da classe e o
componente a que o código do app passa a lambda (rastreio linear de `new-instance` → argumento).

| APK | classe do app (entradas) | nó | interface | recebida por | origem inferida |
|---|---|---|---|---|---|
| saucenao | `MainScreenKt$$ExternalSyntheticLambda44` (357) | `android.widget.CheckBox` | `Function1` | `material3.CheckboxKt.Checkbox` | Material, via nó |
| jtx | `DatePickerDialogKt$$ExternalSyntheticLambda5` (6) | `CheckBox` | `Function1` | `CheckboxKt.Checkbox` | Material, via nó |
| jtx | `DatePickerDialogKt$$ExternalSyntheticLambda12` (6) | `CheckBox` | `Function1` | `CheckboxKt.Checkbox` | Material, via nó |
| jtx | `ListCardKt$$ExternalSyntheticLambda38` (4) | `CheckBox` | `Function1` | `CheckboxKt.Checkbox` | Material, via nó |
| jtx | `ProgressElementKt$$ExternalSyntheticLambda7` (4) | `CheckBox` | `Function1` | `CheckboxKt.Checkbox` | Material, via nó |
| jtx | `ListScreenTabContainerKt$$ExternalSyntheticLambda4` (1) | `CheckBox` | `Function1` | (rastreio não resolveu) | Material, via nó (provável) |

- **Fallback (lambda da ação sem nó):** nenhum caso inferido. Nenhuma classe do app carimbada é
  recebida só por um componente cujo clique é a semântica do próprio Material (scrim/sheet/drawer); as
  três entradas de sheet/drawer que apareceram ficaram com a classe Material (abaixo).
- **plugbrain:** a única `Function1` (`AppsSelectionScreenKt$InstalledAppsList$1$1$2$1$1`, 24 entradas)
  está em `node=android.view.View` e é passada a `InstalledAppItem`, que chama `ToggleableKt.toggleable`
  e `CheckboxKt.Checkbox`; nenhuma linha em nó `CheckBox`. Leitura: `onValueChange` de uma linha
  `toggleable`, pelo passo do nó — não pela etapa Material.
- As demais classes do app são `Function0` passadas a `Button`, `IconButton`, `TextButton`, `Tab`,
  `FilterChip`, `DropdownMenuItem`, `Card`… que repassam o callback direto ao `clickable`; o passo do nó
  já as alcança.

Handlers `androidx.compose.material*` que restam (todos no jtx, 592 entradas):

| classe | entradas | leitura |
|---|---:|---|
| `material3.DatePickerKt$$ExternalSyntheticLambda2` | 309 | célula do DatePicker (limite conhecido) |
| `material3.TimePickerKt$$ExternalSyntheticLambda35` | 192 | relógio do TimePicker (limite conhecido) |
| `material3.internal.BasicTooltipKt$$ExternalSyntheticLambda6` | 28 | tooltip; não listado nos limites da spec |
| `material3.TimePickerKt$$ExternalSyntheticLambda10` | 12 | TimePicker |
| `material3.DatePickerKt$DisplayModeToggleButton$1$$ExternalSyntheticLambda0` | 9 | DatePicker |
| `material3.DatePickerKt$$ExternalSyntheticLambda29` / `30` / `31` | 9 / 9 / 9 | DatePicker |
| `material3.TimePickerKt$$ExternalSyntheticLambda29` / `30` | 6 / 6 | TimePicker |
| `material3.ModalBottomSheetKt$$ExternalSyntheticLambda4` | 1 | sheet, mantido |
| `material3.ModalBottomSheetKt$ModalBottomSheetContent$7$2$1$$ExternalSyntheticLambda0` | 1 | sheet, mantido |
| `material3.NavigationDrawerKt$$ExternalSyntheticLambda0` | 1 | scrim do drawer, mantido |

Por que cada um desses foi mantido (função capturada de biblioteca, duas ou mais funções, ou nenhuma)
não é observável no logcat; os do DatePicker/TimePicker são os limites conhecidos da spec.

### Veredito

Critério do gh121 mantido: nenhum crash com frame do helper e nenhum `VerifyError` nos três. As linhas
Compose nomeiam classes do app que são chaves de `handlers`, nas formas `f$0` (saucenao, jtx) e
`this$0` (plugbrain); o Checkbox é desembrulhado nas 6 classes acima.
