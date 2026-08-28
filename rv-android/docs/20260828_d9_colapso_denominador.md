# D9 — o colapso do denominador: mecanismo determinado — 28/08/2026

**Entregável da investigação D9** pedida em `docs/handoff/20260828_d9_investigacao_prompt.md`
(lá o arquivo estava previsto como `20260829_d9_colapso_soot.md`; o nome mudou porque **o mecanismo
não está no Soot** — manter "soot" no nome perpetuaria a hipótese que esta investigação derrubou).

Documento principal da linhagem: `docs/20260828_cadeia_medicao_rvandroid.md` (rev. 3), §4.3 e §15.3.

---

## 1. O achado, em três frases

O Soot carrega **as 36.800 classes dos 18 arquivos DEX** do `br.com.colman.petals_3040000.apk` e
marca **todas** como classes de aplicação. Logo em seguida, **o próprio GATOR rebaixa 33.089 delas a
classes de biblioteca** num laço de `AnalysisEntrypoint.run()` cuja guarda usa o **pacote do
manifesto** (`br.com.colman.petals.debug`) em vez do pacote de código (`br.com.colman.petals`) —
e a lista `libPackages.txt` contém o padrão `br.com.*`. Sobram 3.711 classes de aplicação, e **uma
única** sob o prefixo do app: a `MainActivity`, resgatada por um ramo do mesmo laço que devolve à
condição de aplicação as *activities* declaradas no manifesto.

O número 3.711 do log da campanha foi **reproduzido ao vivo, em 13 segundos**, por uma sonda
independente. Não é hipótese.

---

## 2. O mecanismo, linha a linha

O sítio é `rvsec-gator/sootandroid/src/main/java/presto/android/AnalysisEntrypoint.java:111-126`:

```java
for (SootClass c : Scene.v().getClasses()) {
  if (activityNames.contains(c.getName())) {          // :112  resgate: activities do manifesto
    if (!c.isApplicationClass()) c.setApplicationClass();
    continue;
  }
  if (c.getName().startsWith(appPkg))                 // :119  A GUARDA — appPkg é o MANIFESTO
    continue;
  if (Configs.isLibraryClass(c.getName())) {          // :121  libPackages.txt (2.170 padrões)
    if ((!c.isPhantomClass()) && c.isApplicationClass())
      c.setLibraryClass();                            // :123  o rebaixamento
  }
}
```

`appPkg` é lido do `AndroidManifest.xml` decodificado, em `:87-94` — `Configs.manifestLocation`,
verbatim, sem neutralização de sufixo. Para os APKs de debug do `rvsec-dataset`, isso é
`….debug`, e **nenhuma classe compilada do app começa com esse prefixo**. A guarda de `:119` nunca
dispara, e as classes do app caem no teste de `:121`.

`Configs.isLibraryClass` (`Configs.java:176-186`) é casamento de prefixo contra
`lib/gator/libPackages.txt` — 2.170 padrões, todos `<algo>.*`. A lista contém, entre outros,
`br.com.*`, `com.github.*`, `io.github.*`, `com.nononsenseapps.*`, `info.metadude.*`,
`me.zhanghai.*`, `uk.org.*`, `androidx.*`, `android.*`, e padrões tão largos quanto `c.*`, `a.a.*`,
`domain.*`, `flow.*`, `examples.*`. Vários deles **não são bibliotecas: são namespaces de autores de
aplicativo**.

O ramo de resgate de `:112` só conhece `<activity>` (`:96` — `getElementsByTagName("activity")`).
*Services*, *receivers* e *providers* do app não são resgatados. É por isso que o artefato do
`petals` traz a `MainActivity` mas **não** traz `br.com.colman.petals.widgets.AddLastUseWidgetReciever`,
que está declarado no mesmo manifesto.

### As duas condições

O colapso exige **as duas** simultaneamente:

1. **A guarda está morta** — o pacote do manifesto não é prefixo de classe compilada nenhuma
   (o sufixo de build-type do `applicationIdSuffix`); e
2. **o pacote de código do app casa um padrão de `libPackages.txt`**.

Se só (1) vale, as classes do app não casam a lista e sobrevivem. Se só (2) vale, a guarda de `:119`
dispara e as protege. É a conjunção que mata.

### A chave de escopo não é a mesma nos dois pontos

O `RvsecAnalysisClient` **prefere** o `codePackage` ao manifesto
(`RvsecAnalysisClient.java:86-90`: `filterPackage = (codePackage != null) ? codePackage : manifestPackage`).
O `AnalysisEntrypoint`, que roda **antes** e decide quais classes existem para o cliente filtrar,
usa o manifesto sem alternativa. **A mesma corrida tem duas chaves de escopo, e a primeira é sempre
o manifesto.** É esta assimetria que torna o contorno manual da campanha (passar `codePackage=` na
linha de comando) incapaz de reparar o D9: ele conserta o filtro do cliente e não toca a guarda que
já esvaziou a `Scene`.

---

## 3. As provas

### 3.1 Reprodução ao vivo (a prova principal)

Sonda `D9Probe.java` — carrega a `Scene` com as mesmas opções do GATOR em modo APK
(`Configs.java:247-252` + `Main.java:214-230`), **sem grafo de chamadas** (o custo dominante: a
corrida original do `petals` levou 2.440 s; a sonda leva 13 s), e simula o laço de `:111-126` com as
duas guardas possíveis, sem mutar a `Scene`.

```
[carga] 10,0s | Scene=38932 app=36800 lib=2055 phantom=77
[carga] app classes sob 'br.com.colman.petals' ANTES do rebaixamento: 771
[manifesto] package=br.com.colman.petals.debug | 4 activities
[guarda=br.com.colman.petals.debug] rebaixadas=33089  #AppClasses=3711  sob 'br.com.colman.petals'=1
[guarda=br.com.colman.petals]       rebaixadas=32319  #AppClasses=4481  sob 'br.com.colman.petals'=771
```

`#AppClasses=3711` é **exatamente** o número do log da campanha
(`SA_RERUN_gh91/logs/br.com.colman.petals_3040000.apk.log:47-49`:
`[STAT] #Classes: 39708, #AppClasses: 3711` / `[App: 3711, Lib : 35067, Phantom: 930]`), e
`sob o prefixo = 1` é exatamente o `Application classes: 1` do artefato. A pequena diferença nos
totais da `Scene` (38.932 contra 39.708) é o que o pipeline completo resolve a mais ao construir o
grafo de chamadas com spark; não afeta o conjunto de aplicação.

Os quatro APKs colapsados e o controle:

| APK | `codePackage` | padrão que casa | #AppClasses sob a chave, guarda=manifesto | idem, guarda=`codePackage` |
|---|---|---|---:|---:|
| `br.com.colman.petals_3040000` | `br.com.colman.petals` | `br.com.*` | **1** | **771** |
| `com.github.livingwithhippos.unchained_60` | `…unchained` | `com.github.*` | **2** | **1.971** |
| `com.nononsenseapps.feeder.play_4025` | `com.nononsenseapps.feeder` | `com.nononsenseapps.*` | **6** | **3.589** |
| `com.github.cvzi.screenshottile_148` | `…screenshottile` | `com.github.*` | **21** | **550** |
| *(controle)* `app.pachli_50` | `app.pachli` | **nenhum** | 6.467 | 6.467 |

Os quatro valores da penúltima coluna são, um a um, os denominadores publicados nos artefatos
(1, 2, 6, 21). O controle `app.pachli` tem o mesmo sufixo de build-type (`app.pachli.current`,
guarda igualmente morta) e é **invariante** sob a troca de guarda, porque `app.pachli` não casa
padrão nenhum da lista. A condição (2) é necessária, e o controle prova.

### 3.2 A previsão sobre o corpus inteiro

Sobre os **162 artefatos** do corpus do artigo, a conjunção "guarda morta ∧ casa `libPackages`"
seleciona **exatamente os quatro** — sem falso positivo e sem falso negativo:

- 75/162 têm manifesto diferente do pacote de código (guarda morta);
- 10/162 têm o pacote de código sob um padrão de `libPackages.txt`;
- a interseção é 4, e é a lista dos quatro colapsados.

Os seis que casam a lista **sem** sufixo (`me.zhanghai.android.untracker`, `com.github.gotify`,
`io.github.samolego.canta`, `uk.org.ngo.squeezer`, `io.github.jd1378.otphelper`,
`io.github.garemat.lunachron`) têm denominadores de 330 a 3.300 — saudáveis, como a guarda prevê.
E os outros denominadores pequenos do corpus (`com.tananaev.passportreader` 18, `org.cry.otp` 23,
`com.hwloc.lstopo` 37) **não** satisfazem nenhuma das duas condições: são aplicativos genuinamente
pequenos, causa diferente.

### 3.3 A lista de classes bate, nome a nome

Em cada um dos quatro, o conjunto de classes do artefato é **precisamente** o conjunto de
`<activity>` do manifesto cujo nome está sob o pacote do app:

| APK | activities no manifesto | sob o pacote do app | classes no artefato |
|---|---:|---:|---:|
| `petals` | 4 | 1 | **1** |
| `unchained` | 3 | 2 | **2** |
| `feeder.play` | 10 | 6 | **6** |
| `screenshottile` | 23 | 21 | **21** |

As *activities* que não entram são as de biblioteca (`androidx.compose.ui.tooling.PreviewActivity`,
`ly.count.android.sdk.messaging.CountlyPushActivity`, `com.burhanrashid52.photoediting.*`) — filtradas
depois pelo `isAppClass` do cliente. E os *receivers*/*services* do próprio app estão todos ausentes,
como o ramo de resgate restrito a `<activity>` prevê. Não sobra grau de liberdade.

---

## 4. O que foi refutado

### 4.1 A hipótese multidex está morta, e por uma razão mais forte do que se supunha

Não é só que `set_process_multiple_dex` nunca é chamado: **a opção não existe no Soot 4.7.1**. A
string `multiple_dex` não aparece em nenhum dos 2.759 `.class` do pacote `soot/` do
`soot-4.7.1.jar` (controle: `process_dir` aparece em `Scene`, `Main`, `PackManager`, `Options`). O
filtro por DEX que existia em versões antigas foi removido:
`soot.dexpler.DexFileProvider.acceptFile` é literalmente `{ return true; }`, e
`SourceLocator.getClassesUnder` itera **todos** os contêineres devolvidos por `getDexFromSource`.

A sonda confirma na prática: `app=36800` para um APK com 36.800 classes distribuídas em 18 DEX. **O
Soot lê tudo.** A ausência de `set_process_multiple_dex` na árvore do `rvsec-gator` não é defeito
nenhum — é uma opção que não existe mais.

Para o registro, o mapa dos DEX do `petals` (lido dos cabeçalhos, `class_defs_size` e a tabela de
tipos): `classes.dex` 17.076 classes / 0 sob o prefixo do app; `classes2` traz 8 classes do app e
`classes3..14` as outras 763; `classes15..18` somam 18.554, nenhuma do app. Isso explica
também por que a contagem por ocorrência de string em `classes.dex` da rev. 2 dava sinal
contraditório: o pacote do app pode estar em qualquer DEX, e não é isso que decide nada.

### 4.2 Achado lateral: os três `-exclude` do GATOR são inertes

`Main.java:225-227` passa `-exclude kotlin.`, `-exclude kotlinx.`, `-exclude androidx.compose.`.
`soot.Scene.isExcluded(String)` só faz casamento de prefixo quando o padrão termina em `.*` ou `$*`;
caso contrário exige igualdade exata. Nenhum dos três termina em `.*`.

Diferencial medido sobre o `petals`:

```
-exclude kotlin. , kotlinx. , androidx.compose.      -> Scene=38932 app=36800 lib=2055
-exclude kotlin.*, kotlinx.*, androidx.compose.*     -> Scene=38932 app=12842 lib=26013
```

As três linhas são configuração morta. **Não é o D9** (o rebaixamento acontece depois, e a diferença
de 23.958 classes seria absorvida pelo `libPackages`), mas é uma linha que qualquer leitor do código
interpreta errado, e mexer nela muda medição. Fica **registrado, não reparado** — decisão de escopo
análoga à D-B da §15.2.

---

## 5. Respostas às cinco perguntas da §3 do handoff

**1. Quantas classes o Soot carrega, de quais DEX, e por que para em 3.711?**
Carrega 36.800, de todos os 18 DEX, e marca todas como aplicação. **Não para em 3.711** — chega a
3.711 depois, porque o GATOR rebaixa 33.089 (`AnalysisEntrypoint.java:121-124`).

**2. Por que sobram exatamente os componentes do manifesto?**
Porque o ramo `:112-118` do mesmo laço devolve à condição de aplicação toda classe cujo nome está na
lista de `<activity>` do manifesto. Não é `getApplicationClasses()` vs `getClasses()`, nem resolução
preguiçosa: é um resgate explícito, e restrito a `<activity>`.

**3. Depende de `set_process_multiple_dex`, ou de outra coisa?**
De nenhuma opção do Soot. Depende de duas propriedades do app: o sufixo de build-type no
`applicationId` e a presença do pacote do app em `libPackages.txt`.

**4. É reparo ou é limitação do Soot com que se tem de conviver?**
É **reparo**, e está em código nosso, não no Soot. Superfície mínima na §6.

**5. Quantos dos 55 APKs excluídos pelo funil do artigo voltariam?**
**Nenhum** — e a pergunta, como estava posta, tem premissa errada. O funil do artigo é calculado
*offline*, sobre as classes compiladas do APK: `mneut_scope.py:150-158` define `A(X)` como o conjunto
de classes compiladas sob o prefixo `X`, lido de `dataset/pkgdet_validation/dex_classes.zip`, e o
`denominator_collapse` dos 33 é `A(Mneut) = ∅` — a chave neutralizada não nomeia classe compilada
nenhuma. **O artefato do GATOR não entra nessa conta.** O funil mede a qualidade da *chave*; o D9 é
um defeito da *classificação* que acontece depois. São coisas independentes.

Medido sobre os 219 executados: 119 têm a guarda morta, 27 têm o pacote sob um padrão de
`libPackages`, e a conjunção com denominador não-vazio dá **exatamente 4** — os mesmos quatro, todos
já `selected`. Outros 14 satisfazem a conjunção mas têm `A(Mneut) = ∅` (13 da família
`info.metadude.android.congress.schedule` e `io.github.quillpad`): esses estão fora por defeito de
chave, que é assunto do D2, e o D9 não os alcança.

**O que o reparo do D9 faz, então, é outra coisa e é maior do que trazer APKs de volta**: ele corrige
o denominador de quatro apps que **estão dentro** da base de análise do artigo e hoje publicam número
inflado — dois deles com `cov_class = 100,00%` sobre uma e duas classes.

| APK | hoje (classes/métodos) | classes sob a chave com a guarda correta |
|---|---:|---:|
| `br.com.colman.petals_3040000` | 1 / 35 | **771** |
| `com.github.livingwithhippos.unchained_60` | 2 / 45 | **1.971** |
| `com.nononsenseapps.feeder.play_4025` | 6 / 115 | **3.589** |
| `com.github.cvzi.screenshottile_148` | 21 / 394 | **550** |

(As contagens de método com a guarda correta exigem uma corrida completa do GATOR — a sonda não
constrói corpos nem grafo de chamadas. As de classe são diretas e bastam para dimensionar.)

**A exposição da campanha nova**, que é o que a pergunta 5 servia para decidir: 27 de 219 apps
(12,3%) têm o pacote sob um padrão de `libPackages.txt`. Enquanto a guarda usar o manifesto,
**qualquer** desses 12,3% colapsa assim que o APK tiver sufixo de build-type. O corpus atual só
mostra 4 porque as duas condições precisam coincidir.

---

## 6. A superfície do reparo

**Reparo (a) — a guarda passa a usar a chave de código.** `AnalysisEntrypoint.java:119` consulta
`Configs.getClientParamCode("codePackage=")` e cai no manifesto só quando o parâmetro está ausente.
`Configs.getClientParamCode` vive em `sootandroid` (`Configs.java:292`) e `Configs.clientParams` já
está preenchido quando `AnalysisEntrypoint.run()` executa (o parsing acontece em `Main.main`, antes
de `setupAndInvokeSoot()`), então não há dependência nova entre módulos. Poucas linhas, um sítio.

Isso alinha as duas chaves da corrida: a guarda passa a proteger exatamente o conjunto que o
`RvsecAnalysisClient` vai filtrar depois. Medido na sonda: restaura 771 / 1.971 / 3.589 / 550, e é
**invariante** para todo app cujo pacote não casa a lista — o `app.pachli` é a testemunha. É o reparo
mínimo que o princípio P1 pede.

**Reparo (b) — podar `libPackages.txt`.** Tirar da lista os namespaces que são de autores de app
(`br.com.*`, `com.github.*`, `io.github.*`, `com.nononsenseapps.*`, `info.metadude.*`,
`me.zhanghai.*`, `uk.org.*`, e os largos como `c.*`, `a.a.*`, `domain.*`, `flow.*`). **Não
recomendo agora**: muda medição para *todos* os apps (a lista também governa o que o GATOR trata como
biblioteca em análise legítima), o raio de alcance é o corpus inteiro, e o reparo (a) já fecha o
defeito. Fica anotado como dívida com dono a definir.

**O que NÃO reparar**: o ramo de resgate restrito a `<activity>` (`:96`). Com (a) aplicado, ele deixa
de ser load-bearing para as classes do app — vira o que sempre quis ser, uma rede de segurança para
componentes que o Soot classificou mal. Ampliá-lo para *services*/*receivers*/*providers* mudaria
medição sem cenário que o exija.

**Nota de fronteira**: (a) é reparo no `rvsec-gator`, dentro do escopo que o handoff autoriza. Ele
não toca o lado Python, não toca o `ajc`, e não interage com a flag de sufixo do D2 — o D2 conserta a
chave que o cliente usa para filtrar; o D9 conserta a guarda que decide o que existe para filtrar.
São reparos independentes no mesmo sintoma, que é exatamente por que a §15.3 pôs o D9 primeiro.

---

## 7. O que isto muda no escopo da change

A ordem decidida em §15.3 (**D9 → D1 → D2 → D3 → D4 → D10' → D9b**) continua correta, e a razão dela
fica mais forte: as duas causas do denominador degenerado agora estão **separadas e nomeadas**, com
critério mecânico para atribuir cada APK a uma delas.

- **D9** deixa de ser investigação e vira reparo de escopo conhecido: uma guarda,
  `AnalysisEntrypoint.java:119`. Muda medição em 4 dos 162 (e em 12,3% dos apps sob risco em
  qualquer campanha futura). **Isto atualiza a coluna "muda medição?" da tabela da §15.3, que hoje
  traz "—" para o D9.**
- **D1** (portão de não-vacuidade) ganha um segundo modo de falha para cobrir: o portão precisa
  recusar tanto o denominador vazio quanto o **degenerado** — 1 classe de 771 não é vazio, e é o modo
  que hoje publica 100,00%. Um portão só de não-vacuidade não teria pego nenhum dos quatro.
- **D2** fica com o escopo intacto: a flag de sufixo conserta a chave do cliente. Ela **não** conserta
  o D9, e não convém que conserte — o `AnalysisEntrypoint` deve receber a chave de código já
  resolvida, não repetir a regra de neutralização.
- **A fronteira de ponto do `isAppClass` (D-C)** pode ser reavaliada agora, como a decisão previa.
  Nada no D9 a bloqueia, e nada no D9 a torna urgente: o rebaixamento é anterior ao `isAppClass` e
  independente dele.

O D9 está fechado. A change pode ser aberta.

---

## 8. Âncoras e reprodução

**Código**
- `rvsec-gator/sootandroid/.../AnalysisEntrypoint.java:77-82` (default da lista), `:87-94` (`appPkg`
  do manifesto), `:96-106` (as `<activity>`), **`:111-126` (o laço)**, `:129-130` (o `[STAT]`)
- `rvsec-gator/sootandroid/.../Configs.java:176-186` (`isLibraryClass`), `:188-204`
  (`processLibraryPkgFile`), `:247-252` (modo APK), `:292` (`getClientParamCode`)
- `rvsec-gator/sootandroid/.../Main.java:117-118` (`-libraryPackageListFile`), `:119-121`
  (`-libraryPackageName`), `:214-230` (args do Soot, com os três `-exclude`), `:286-287`
- `rvsec-gator/sootandroid/.../Hierarchy.java:299-323` (`appClasses` = classes de aplicação da
  `Scene`), `rvsec-gator/.../gui/Flowgraph.java:261` (a análise só percorre `hier.appClasses`),
  `:462-464` (`Processed classes`)
- `rvsec-gator/client/.../RvsecAnalysisClient.java:86-90` (a **outra** chave), `:267-280` (o filtro),
  `:289-297` (`isAppClass`)
- `rv-android/lib/gator/gator:90-101` (a invocação; `-libraryPackageListFile`),
  `rv-android/lib/gator/libPackages.txt` (2.170 padrões; idêntico byte a byte a
  `rvsec-gator/sootandroid/libPackages.txt`)
- Soot 4.7.1: `soot.Scene.loadNecessaryClasses` (marca aplicação tudo que vem do `-process-dir`),
  `soot.SourceLocator.getClassesUnder`, `soot.dexpler.DexFileProvider.acceptFile` (`return true`),
  `soot.Scene.isExcluded` (exige `.*`)

**Dados**
- `SA_RERUN_gh91/logs/br.com.colman.petals_3040000.apk.log:47-49,508-521`;
  `SA_RERUN_gh91/record/sa_rerun_record.csv` (o `petals` levou 2.440,4 s; o `pachli`, 1.704,3 s)
- `APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/*.apk.json` (os 162)
- `ase-journal/data-analysis/mneut_scope.py:97-102` (`neutralize`), `:137-158`
  (`iter_dex_classes`, `classes_under`), `:160-190` (`arm_metrics`, `would_collapse`);
  `stage_denominator_scope.py:26-38` (a taxonomia dos 55)

**Como reproduzir**

A sonda usada nesta investigação (`docs/20260828_d9_colapso_denominador/D9Probe.java`)
carrega a `Scene` com as opções do GATOR em modo APK, sem grafo de chamadas, e simula o laço
com as duas guardas. Ela roda contra o fat jar já construído, sem rebuild do reator:

```bash
javac -cp rv-android/lib/gator/rvsec-gator.jar -d classes D9Probe.java
java -Xmx24G -cp classes:rv-android/lib/gator/rvsec-gator.jar D9Probe \
     <apk> <AndroidManifest.xml> <android.jar do api-35> \
     rv-android/lib/gator/libPackages.txt <codePackage>
```

O manifesto pode ser sintetizado a partir do próprio artefato (`package` + `components.activities`),
que é o registro que o GATOR fez dele — foi assim que as cinco corridas desta investigação foram
feitas, e o casamento exato com o `#AppClasses` da campanha valida a síntese.

A previsão sobre o corpus é uma passagem sobre os `.apk.json` mais o casamento de
`libPackages.txt`: um APK colapsa se, e somente se, nenhuma classe compilada começa com o pacote do
manifesto **e** o pacote de código casa um padrão da lista.
