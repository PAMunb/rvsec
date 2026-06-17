# Veredito — abordagem RESIDUAL para detecção de código-app (app = tudo − libs − sistema)

**Data:** 2026-06-17
**Status:** VEREDITO para decisão — **nada implementado** (análise + plano de medição)
**Método:** 4 subagentes paralelos de verificação em **fonte primária** (com instrução explícita de marcar UNVERIFIED e separar self-report de reavaliação) + 1 subagente de inspeção dos artefatos locais + sequential-thinking (5 passos: bound de erro, puro-vs-híbrido, correção dos mis-picks, ofuscação, matriz comparativa) + skill `scientific-critical-thinking`.
**Calibrado por:** rejeição ICST 2026 #65 — objeções #65A#1 e #65A#4 (verbatim em `docs/20260219_icst2026_pareceres_65.md`, confirmadas nesta rodada).
**Estende / não substitui:** `docs/20260617_veredito_deteccao_pacote_modulo_primario.md` (veredito principal — A′/D/F). Este doc aprofunda **especificamente** a abordagem residual, que o veredito principal só tocava de relance (Opção F/§2-A.1).
**Continuação (CONSULTAR):** `docs/20260617_solucoes_blackbox_deteccao_codigo_app.md` — analisa LibHunter (ASE'24) e o leque de soluções **black-box** (AndroLibZoo/Exodus/AndroSpecter, A3Ident estrutural), e confronta a restrição de **ofuscação** (prefixo morre sob R8-renaming). Este doc aqui refuta o residual como mecanismo; o de soluções mostra o que sobra de válido sob black-box+ofuscação.
**Relacionados:** `docs/20260617_investigacao_sota_substituir_detector.md` (spike LibScout), `docs/20260613_pesquisa_package_detection_sota.md`, `openspec/changes/gh67-package-detector-eval/`.

---

## 0. TL;DR (o veredito em um parágrafo)

A abordagem **residual pura** (`app = todos_os_pacotes − libs_detectadas − sistema`) **não sobrevive como mecanismo de detecção** e a refutação central **se confirma quantitativamente**, não é contornada: com o melhor detector de TPL a **recall = 49,03%** (LibScout, condição *não-ofuscada* C1 — verificado verbatim em Zhan et al. ASE 2020), **mais da metade das bibliotecas presentes vaza para o resíduo** e é atribuída ao app; sob R8 (presente em **41,1%** do corpus F-Droid — LibHunter ASE 2024) o LibScout colapsa a **F1 1,1%** e o vazamento vira ~100%. Como bibliotecas são **cripto-densas** (AppAuth/Tink/OkHttp/BouncyCastle), o viés é **para cima** na contagem de *misuses* — exatamente a direção que infla o resultado do nosso estudo e que o revisor ataca. A versão **híbrida** (âncora do manifest mantém o app + TPL subtrai libs conhecidas) é o construto correto (= A3Ident, validado a 96,11% em F-Droid), mas **fracassa empiricamente nos nossos casos**: o catálogo do subtrator (LibScout) não cobre **8 de 9** das libs que causam nossos mis-picks (AppAuth/Flutter/TFLite ausentes) → a subtração não dispara. E o sinal residual *catalog-free* (histograma de classes do dex) **só corrige 1 dos 4 mis-picks** (readeck), falhando em apps **thin-dex** (Flutter: venera/webspace) e em **fork com reúso de namespace** (whobird) — e introduz um **novo modo de falha sistemático** (apps Flutter/RN/Unity). **Conclusão:** a ideia residual é **certa como oráculo de validação e errada como mecanismo de detecção**. O caminho recomendado continua sendo **A′** (validar o detector atual contra um oráculo **independente** — applicationId do repositório F-Droid, autoritativo, + histograma de classes do dex como segundo sinal onde os nomes sobrevivem — com Wilson CI + κ, estratificado por método e ofuscação), agora com a **justificativa quantitativa** de por que residual-como-detector está descartado. Reimplementar A3Ident é a "residual feita certo", mas é um **mini-projeto** (ICC ausente + revalidação + descongela o gh63), não um atalho.

---

## 1. O bound de erro da subtração residual (quantificado)

### 1.1 Modelo

Seja, para um APK:
- **A** = conjunto de pacotes do código-app real;
- **L** = conjunto de pacotes de biblioteca presentes;
- **R** = recall do detector de TPL (fração de **L** corretamente identificada).

Resíduo = `(A ∪ L) − libs_detectadas − sistema = A ∪ L_perdido`, com `|L_perdido| = (1−R)·|L|`.

**Contaminação do conjunto-app** = `(1−R)·|L| / (|A| + (1−R)·|L|)`.

### 1.2 Os números (verificados)

| Condição | R (recall TPL) | Fração de libs que vaza `(1−R)` | Fonte (verbatim) |
|---|---|---|---|
| **Não-ofuscado** (C1, melhor tool) | **49,03%** (LibScout) | **50,97%** | Zhan ASE 2020: *"all tools have low recall (i.e., less than 50%)… existing tools can only detect less than half of the TPLs"* — §6.1, dataset C1 (221 apps reais Google Play) |
| Não-ofuscado (2º melhor) | 45,79% (LibID) | 54,21% | mesmo, §6.1 |
| Não-ofuscado (pior) | 9,44% (ORLIS) | 90,56% | mesmo, §6.1 (P 57,5% / R 9,44%) |
| **Ofuscado por R8** (41,1% do corpus) | ~0 (LibScout F1 **1,1%**) | **~100%** | LibHunter ASE 2024, Tab. 2 (Opt+Obf+Srk): LibScout F1 1,1%; LibPecker 4,3%; LibScan 41,1%; só LibHunter 71,4% |

**Agravante estrutural:** em Android tipicamente `|L| ≫ |A|` (dezenas de libs contra punhado de pacotes-app). Com `R ≈ 0,49` e `|L|` grande, **o resíduo é dominado pelas libs vazadas**, não pelo app. Não é um erro de cauda — é o regime comum.

### 1.3 Direção do viés (o ponto que tinha de ser enfrentado)

As libs que vazam para o conjunto-app têm suas operações de cripto **atribuídas ao app**. Bibliotecas são **cripto-densas por natureza** (AppAuth = OAuth/PKCE; Tink = cripto; OkHttp = TLS; BouncyCastle = provider JCA) → densidade de *misuse* por pacote em **L** ≥ em **A**. Logo o viés não é só presente, é **amplificado e para CIMA** na contagem de *misuses*. Para um estudo de **prevalência de cripto-misuse**, super-escopar é o erro mais perigoso: infla a contagem de misuses do app (atribui misuse de lib ao app) — precisamente o que #65A#1/#65A#4 atacam. **A armadilha se confirma; não é contornável por prosa.**

> Comparação honesta: o detector **atual** (ancorado no manifest) erra em **24,9%** dos 169 APKs (difere do manifest; auditoria local `out/package_detector_audit/`), com erro de lib-mis-pick **detectado** de ~2,4% (4/169). A subtração residual pura, no melhor caso não-ofuscado, contamina **>50%** das libs presentes da maioria dos apps lib-pesados — **ordens de grandeza pior** que o detector atual. Residual pura não é um upgrade; é um downgrade.

---

## 2. Residual PURO vs HÍBRIDO

### 2.1 Puro (`app = tudo − libs − sistema`) — ❌ descartado

Refutado pela §1: dominado por vazamento, viés para cima, **catastrófico sob R8** (onde está 41% do corpus). Some-se: sob R8 os nomes de pacote do **próprio app** também são renomeados (`a.b.c`), então mesmo o "resíduo" que sobrar tem nomes inúteis como prefixo para os consumidores (GATOR `codePackage=`, filtro do parser, `within()` do AJC). Puro falha duas vezes sob ofuscação: não acha as libs **e** não nomeia o app.

### 2.2 Híbrido (âncora manifest + subtração de libs conhecidas) — construto certo, fracasso empírico

O híbrido é o que o **A3Ident (ICSME 2020)** faz e validou a **96,11% em F-Droid** (vs PiggyApp 81,18% — Tab. IV, verificado). O nosso detector é uma **instância single-prefix** dele. Conceitualmente correto porque a **âncora do manifest identifica o app POSITIVAMENTE** (não como resíduo) → a exposição ao recall-de-lib fica **limitada ao caso estreito** em que uma lib declara componentes no manifest e vence a votação (`most_common`/`single_package`). Esse caso estreito **é exatamente os nossos 4 mis-picks**.

**O golpe empírico (spike `out/sota_spike/`):** o subtrator precisa **conhecer** a lib ofensora. O catálogo do LibScout (8.542 versões, congelado em **2019-07-16**) cobre **1 de 9** das nossas libs *merged* (só OkHttp; **AppAuth, Tink, ZXing, Flutter, UnifiedPush, mikepenz, TensorFlow Lite ausentes**). No `de.readeckapp` o LibScout detectou só Facebook e **perdeu `net.openid.appauth`** — o exato mis-pick a subtrair. Logo a subtração **não dispara** em readeck/venera/webspace/whobird → **benefício ~zero** nos casos conhecidos. O híbrido-via-ferramenta degrada para *(detector atual + peso morto que não toca nossos erros)*.

**E o subtrator catalog-free?** Clustering estrutural (LibRadar/LibD) pegaria libs desconhecidas (o plugin Flutter), evitando o gap de catálogo. Mas: (a) tooling **morto** (LibRadar = Py2.7+Redis; LibD = Py2 sem licença — verificado); (b) recall ainda <50%; (c) reimplementar = A3Ident = **ICC + Louvain + o MESMO passo subespecificado** (Algoritmo 1, linha 3, *"identify contained libraries"* — confirmado como subrotina externa não-resolvida) + revalidação + **descongela o gh63**. Não é atalho.

**Veredito §2:** híbrido é o **construto defensável** (e cita-se A3Ident como precedent validado), mas **não é construível barato agora** e o subtrator pronto **não cobre nossas libs**. Híbrido-via-reimplementação = Opção D/F do veredito principal, não uma jogada nova.

---

## 3. Qual TPL detector como subtrator? (ranqueado por veículo × runnability 2026)

Verificado em fonte primária. Métricas separadas: self-report vs reavaliação independente (LibHunter ASE 2024 reavaliou os baselines sob R8).

| Ferramenta | Veículo / tier | Emite | Recall/F1 (verificado) | Cobre nossas 9 libs? | Runnable 2026 | Veredito como subtrator |
|---|---|---|---|---|---|---|
| **LibScan** | **USENIX Sec 2023** (top) | libs + versão (correspondência de classes) | F1 **41,1%** sob R8 (reaval. LibHunter Tab.2); alto sem ofusc. (self-report) | ❌ exige **construir** a DB de fingerprints (não traz catálogo geral) | ✅ **único limpo** (Python 3, MIT, mantido) | Melhor *engenharia*, mas catálogo é problema do usuário → herda nosso gap |
| **LibHunter** | ASE 2024 (sólido) | libs + versão; robusto a R8 | **71,4%** lib-F1 sob R8 (self-report, single-eval) | ❌ idem (precisa de fingerprints) | ⚠️ Python, **sem licença** (github.com/CGCL-codes/LibHunter) | Único que aguenta R8, mas sem licença + DB própria |
| **LibScout** | ESEC/FSE 2016 | match por perfil | recall **49,03%** / F1 **65,2%** (C1, Zhan ASE'20); **1,1%** F1 sob R8 | ❌ **1/9** (catálogo 2019) | ⚠️ JDK8, perfis prontos | Colapsa sob ofusc.; catálogo velho (= nosso spike) |
| LibRadar | clustering (→ de WuKong ISSTA'15) | conjunto de libs (catalog-free) | recall **UNVERIFIED** (40,39% só no gráfico de Zhan) | catalog-free (pegaria Flutter) | ❌ **morto** (Py2.7 + Redis) | inviável |
| LibD | ICSE 2017 | libs; **lê o manifest p/ remover o app-code** | FP 25,0% / FN 43,9% (GT **próprio** dos autores, não independente) | catalog-free | ❌ **morto** (Py2, sem licença, 2019) | inviável; mas **precedent citável** (manifest p/ host) |
| LibPecker | TSE 2018 | score de similaridade (sem conjunto) | F1 **4,3%** sob R8 | — | ❌ JDK7, só score | não emite conjunto |
| LibID | TSE 2020 | libs | recall **45,79%** (C1) | — | ❌ Py2 + **Gurobi** (licença comercial) | inviável |
| ATVHunter | ICSE 2021 | libs + versão | — | — | ❌ **sem artefato** localizável | inviável |

**Linha de detecção de código-app DIRETA (não de lib):**

| Ferramenta | Veículo | Valida output de código-app? | Acurácia | Artefato |
|---|---|---|---|---|
| **A3Ident** | ICSME 2020 | **Sim** (Louvain + âncora MainActivity/manifest + ICC) | **96,11%** F-Droid (Tab.IV); Pkg P96/R97,7/F196/Acc95,8 (Tab.I) | ❌ **nenhum** (verificado) — e Algo 1 L3 *"identify contained libraries"* é subespecificado |
| PiggyApp | CODASPY 2013 | Sim (PDG + clustering) | 81,18% reaval. F-Droid (A3Ident Tab.IV) | ❌ nenhum |

**Conclusão §3:** o único subtrator **runnable e limpo** é o **LibScan** (Py3/MIT), mas ele **não traz catálogo** (você constrói a DB) → herda integralmente o nosso gap de cobertura. O único que **aguenta R8** (LibHunter) **não tem licença**. Os catalog-free que evitariam o gap estão **mortos**. **Nenhum entrega o subtrator que o híbrido precisaria** sem virar um projeto de engenharia + manutenção de catálogo.

---

## 4. Ofuscação (R8 em 41,1%) — a assimetria que inverte a intuição

R8 renomeia **app E libs** para `a.b.c`. Efeitos por método:

| Sinal | Sob R8 (41% do corpus) | Não-ofuscado (~59%) |
|---|---|---|
| Subtração TPL (catálogo) | **colapsa** (LibScout F1 1,1%) | recall 49% (vaza >50%) |
| Histograma de classes do dex | ranqueia por contagem, mas **nomes inúteis** como prefixo | nomes reais → sinal usável |
| **Âncora do manifest** | **sobrevive** — R8 preserva nomes de classe referenciados no manifest (componentes são citados por string) | sobrevive |
| **applicationId do repo F-Droid** | **autoritativo** (independe de ofuscação; app é open-source) | autoritativo |

**A intuição "residual é mais robusto" inverte-se:** sob R8 o **manifest degrada graciosamente** (ainda tem nomes reais dos componentes de entrada) enquanto o **residual degrada catastroficamente** (não acha lib e não nomeia o app). Por isso o **applicationId do repo F-Droid é a espinha** do oráculo (vale sempre), e o histograma do dex é **segundo sinal só onde os nomes sobrevivem**. Estratificar por ofuscação é obrigatório (detectar via fração de segmentos de 1 letra, ou se as classes do applicationId sobrevivem no dex).

---

## 5. A subtração residual corrige os 4 mis-picks? (caso a caso — honesto)

Sinal residual *catalog-free* testável hoje = **histograma de classes do dex** (ranquear pacotes por nº de classes, pegar o dominante não-lib).

| Mis-pick (app → pick errado) | Branch | Residual/histograma corrige? | Por quê |
|---|---|---|---|
| `de.readeckapp` → `net.openid.appauth` | most_common (2/3) | ✅ **SIM** | App tem muitas classes; AppAuth é OAuth pequeno → histograma ranqueia `de.readeckapp` primeiro |
| `venera` → `com.pichillilorenzo.flutter_inappwebview_android` | most_common | ❌ **NÃO** | App **Flutter**: lógica em Dart → `libapp.so` (nativo). O dex é shell fino + Java do plugin → **plugin tem mais classes dex** que o app → histograma confirma o erro |
| `webspace` → idem Flutter | most_common | ❌ **NÃO** | mesmo modo thin-dex |
| `org.woheller69.whobird` → `org.tensorflow.lite.examples.soundclassifier` | single_package | ❌ **NÃO** | **Fork** do exemplo TFLite: o código do app **vive sob o namespace da lib**. Histograma concorda com o "errado" — e é ambíguo se é errado (o app genuinamente é esse código) |

**Placar: 1/4.** Pior: o residual **introduz um modo de falha sistemático novo** — apps **thin-dex** (Flutter/React Native/Unity, onde a lógica não está em classes dex) — que o detector por manifest **não tem** (o manifest lista o componente real do app). E não resolve **fork/reúso de namespace**, que é mal-posto para qualquer método.

**Implicação decisiva:** o histograma residual **discorda do detector exatamente nos casos interessantes** (e às vezes acerta, às vezes erra). Isso é a assinatura de um bom **sinal de cross-check**, não de um detector. Seu lugar certo é **oráculo independente na avaliação (A′)**, medido por **κ** contra o detector e contra o repo — **não** o detector, **não** um subtrator.

---

## 6. Plano de medição empírica (169 APKs + 4 mis-picks)

Objetivo: medir, com dados, (i) se a subtração residual corrigiria os mis-picks, (ii) quantos novos erros ela introduz, (iii) a acurácia do detector atual contra oráculo independente. **Não toca GATOR/parser/AJC; não descongela o gh63.**

### 6.1 Construir o oráculo independente (script offline, novo)

1. **applicationId do repo F-Droid** (espinha autoritativa). Os 169 são F-Droid open-source → o `applicationId` do `build.gradle` upstream é o pacote-app **real e conhecível**. Cruzar via metadata F-Droid (`fdroiddata`) por package name. Resolve a circularidade do Golpe 1 (§veredito principal): oráculo **independente do detector**.
2. **Histograma de classes do dex** (segundo sinal). Enumerar todas as classes do dex e contar por pacote (nível 3). **⚠️ CAVEAT (corrige premissa da tarefa):** androguard neste checkout é **`3.4.0a1`, não 4.1.4** (`pyproject.toml`/`uv.lock`/runtime — verificado), e **nenhuma enumeração de classes dex está implementada** hoje. Fontes possíveis: `AnalyzeAPK`/`dx.get_classes()` do androguard 3.x, **ou dexlib2** (já usado em `rvsec-instrumentation-dexlib2`). É **código novo barato**, mas **não "grátis in-process"** como a premissa dizia.
3. **Detecção de ofuscação** por APK (fração de segmentos de 1–2 letras nos nomes de pacote do dex) → estratificar ofuscado vs não.

### 6.2 Medições

| # | Medição | Como | Responde |
|---|---|---|---|
| M1 | **Acurácia do detector atual** | `code_package` vs applicationId F-Droid, amostra estratificada por `detection_method` (99/29/17/11/8/5) **e** por ofuscação; **Wilson CI** | #65A#1 (recall/accuracy) |
| M2 | **κ detector × histograma dex** (não-ofuscados) | Cohen's κ entre o pick do detector e o pick do histograma | quantifica concordância de 2 sinais independentes |
| M3 | **Residual corrige os mis-picks?** | rodar histograma nos 4 (readeck/venera/webspace/whobird) + amostra | mede 1/4 da §5 empiricamente; expõe thin-dex |
| M4 | **Residual introduz novos erros?** | nos 99 `same_package` (hoje corretos), o histograma residual erraria quantos? (esp. apps Flutter/RN) | quantifica o **custo** de trocar para residual |
| M5 | **Gap prefixo-vs-conjunto** | nos 46 não-triviais (most_common+common_prefix): quantos têm footprint multi-pacote; % de misuses fora do prefixo | #65A#1 (app-vs-lib) + decide fallback D |
| M6 | **Taxa de lib-mis-pick + matriz de confusão app-vs-lib** | 4 mis-picks como first-class | #65A#4 (scope app vs lib) |

### 6.3 Critério de decisão (pré-registrado)

- **M3 ≤ 1/4 e M4 alto** (residual quebra muitos `same_package`, esp. Flutter) → **residual descartado como detector, confirmado empiricamente**; usa-se o histograma só como oráculo (M2). *(hipótese atual, §5)*
- **M5 gap pequeno** → defende-se o prefixo único **com dados**; sem código; gh63 fica pinado.
- **M5 gap grande** → escalar para conjunto (Opção D) em **experimento futuro**; reportar como ameaça de construto quantificada no artigo atual.

---

## 7. Matriz comparativa final (residual vs A′ vs reimplementar A3Ident)

| Opção | O que é | Sobrevive ao revisor? | Custo | Risco gh63 | Veredito |
|---|---|---|---|---|---|
| **Residual PURO** | app = tudo − libs − sistema | ❌ **Não** — vaza >50% das libs (R=49%), ~100% sob R8; viés **para cima** em misuses; novo modo thin-dex | baixo | — | ❌ **REFUTADO** (§1, §5) |
| **Residual HÍBRIDO via ferramenta** | manifest + subtração TPL pronta | ❌ catálogo cobre **1/9** → não toca nossos mis-picks; clustering catalog-free **morto** | médio | — | ❌ **inviável** (§2.2, §3) |
| **Reimplementar A3Ident** | híbrido "feito certo" (ICC+Louvain+âncora) | construto validado (96% F-Droid) **mas** carrega o MESMO passo "identify libraries" + exige **ICC** (ausente do androguard 3.4.0a1) + métrica diferente → **revalidação** | alto | muda picks → **descongela** | 🔮 **futuro** (= Opção D/F); citável como precedent |
| **A′** (recomendada) | validar detector atual vs **oráculo independente** (applicationId F-Droid + histograma dex), Wilson CI + κ, estratificado, gap quantificado, 4 mis-picks first-class | ✅ **Sim** — data-driven, oráculo independente; **realoca o sinal residual** para onde seu recall<50% **não morde** (cross-check, não detector) | baixo-médio | **nenhum** | ✅ **RECOMENDADA** |

**A síntese (refutação-survivente):** a ideia residual é **certa como oráculo e errada como detector**. O `recall<50%` que a mata como mecanismo **é inofensivo** quando o histograma é **um de dois sinais de oráculo** — o `applicationId` do repo F-Droid é a **espinha autoritativa** (open-source ⇒ ground truth conhecível, vale até sob R8), o histograma do dex **corrobora onde os nomes sobrevivem**, e a concordância vira **κ**. **Não dribla a recall<50%; relocaliza o sinal residual** para um papel onde sua fraqueza não pesa. Custo×rigor×risco: **A′ vence** — não toca gh63, responde literalmente a #65A#1 e parte de #65A#4, e a medição (§6) **fecha** se residual corrigiria ou pioraria, em vez de assumir.

**Calibração (não-visão-de-túnel):** detecção é **1 de 7** drivers da rejeição. A′ fecha #65A#1 e parte de #65A#4 a custo baixo. **Não super-investir**: residual-como-detector está descartado; reimplementar A3Ident fica no backlog/futuro acoplado à redefinição de construto (Opção D), nunca como bloqueio da ressubmissão (cujos números estão pinados).

---

## 8. Correções de integridade (premissas da tarefa que a verificação refutou)

1. **androguard = `3.4.0a1`, NÃO 4.1.4** neste checkout (pyproject/uv.lock/runtime). Nenhuma enumeração de classes dex implementada. O histograma do dex é **código novo barato** (via androguard 3.x `AnalyzeAPK` ou dexlib2), **não** capacidade "grátis in-process". *(corrige o fato #4 da tarefa)*
2. **Differ-from-manifest na auditoria dos 169 = 24,9%** (42/169), não 27,5% (27,5% é o número project-wide em docs/CLAUDE.md). Distribuição: same_package 99 / most_common 29 / common_prefix 17 / single_package 11 / similarity 8 / no_consensus 5.
3. **`passwordstore` NÃO é lib-mis-pick** — `app.passwordstore.ui` é código-app genuíno (sufixo de flavor `.agrahn`). Mis-picks de lib reais = **4 apps / 3 libs**: readeck→AppAuth, venera+webspace→Flutter, whobird→TFLite.
4. **Catálogo LibScout cobre 1/9** (OkHttp presente, 58 versões), 8/9 ausentes. O "0/9" da tarefa era autocontraditório; o ponto substantivo (8/9 ausentes, incl. todas as que causam mis-pick) **se mantém**.
5. **Recall por tool de Zhan ASE'20:** LibScout 49,03% / LibID 45,79% / ORLIS 9,44% e F1 LibScout 65,2% = **CONFIRMADOS verbatim** (§6.1, dataset C1 não-ofuscado). **LibRadar 40,39% e LibPecker 36,85% = UNVERIFIED** (vivem só na Figura 2, gráfico de barras não-extraível). **Citar Zhan como DOI 10.1145/3324884.3416582 — NÃO arXiv:2108.03787** (que é outro paper).
6. **R8 em 41,1%** = LibHunter ASE 2024 (título real *"How Does Code Optimization Impact Third-party Library Detection…"*), §3.1, população **2.347 apps F-Droid** (citar com esse escopo). Baselines sob R8 (Tab.2): LibScan F1 41,1% / LibScout 1,1% / LibPecker 4,3% / LibID 0,6%; LibHunter 71,4% (self-report single-eval).

---

## 9. Decisões propostas (para discutir ANTES de implementar)

| # | Decisão | Recomendação |
|---|---|---|
| (a) | Residual como **mecanismo de detecção** | ❌ **Descartar** (puro e híbrido-via-ferramenta). Bound de erro >50% (§1), 1/4 nos mis-picks (§5), novo modo thin-dex. |
| (b) | Sinal residual (histograma dex) como **oráculo de validação** | ✅ **Adotar em A′** como 2º sinal independente (κ), espinha = applicationId F-Droid. |
| (c) | Reimplementar A3Ident | 🔮 **Backlog/futuro** (= Opção D), acoplado à redefinição de construto p/ conjunto; não na ressubmissão. |
| (d) | Caminho da ressubmissão | **A′** (veredito principal §5), agora com a justificativa quantitativa de por que residual-detector está fora. |
| (e) | Caveat técnico | androguard 3.4.0a1 (não 4.1.4); histograma = código novo (dexlib2 é alternativa). Registrar no gh67. |
| (f) | Calibração | Detecção = 1 de 7 drivers; não super-investir; medição (§6) decide o fallback, não o otimismo. |

**Próximo passo (após aprovação):** dobrar isto na `gh67-package-detector-eval` via skill OpenSpec (não editar artefatos à mão) — adicionar M1–M6 como tarefas de medição, registrar o caveat do androguard, e manter A3Ident/conjunto (D) no backlog.

---

## Apêndice — status de verificação (fonte primária)

**CONFIRMADO verbatim:**
- Zhan et al., ASE 2020, **DOI 10.1145/3324884.3416582** (PDF do autor `lilicoding.github.io/papers/zhan2020.pdf`): recall <50% (C1), LibScout 49,03% R / 65,2% F1, LibID 45,79%, ORLIS 9,44%, definição de recall (§6.3).
- LibHunter, ASE 2024 (`xzf1234.github.io/pdfs/ASE24_LibHunter.pdf`): R8 41,1% (2.347 F-Droid, §3.1); Tab.2 baselines sob R8.
- LibScan, USENIX Sec 2023 (github.com/wyf295/LibScan): Py3, MIT, exige construir DB.
- A3Ident, ICSME 2020 (arXiv:2008.13768, ar5iv): 96,11% F-Droid (Tab.IV), Algo 1 L3 subespecificado, ICC via IC3-DialDroid, sem artefato.
- LibD, ICSE 2017: *"identify application code according to the manifest files… trimmed off on the call graph"*; FP 25%/FN 43,9% (GT próprio dos autores — **não** independente).
- Runnability: LibScan (Py3/MIT) único limpo; LibHunter (Py, sem licença); LibRadar/LibD/LibID Py2 mortos; LibPecker JDK7 score-only; ATVHunter sem artefato.
- Reviewer #65A#1 e #65A#4 (`docs/20260219_icst2026_pareceres_65.md` linhas 33, 36).

**UNVERIFIED (marcado, não citar como número exato):**
- LibRadar recall 40,39% / LibPecker recall 36,85% (Zhan Fig.2, gráfico não-extraível) — exigem leitura visual do PDF.
- Membership por nome das libs modernas nos catálogos (LibScout-Profiles 2019 / LibRadar 2017) — plausível ausência por data de congelamento, não confirmada item-a-item (exceto as 9 do spike, contadas localmente: 1/9).
- LibHunter 71,4% sob R8 = self-report single-eval (não reavaliado por terceiro).

**Evidência local:** `out/package_detector_audit/results.json` (169 APKs, distribuição §8.2); `out/sota_spike/json_out/` (LibScout: só Facebook+OkHttp, perde AppAuth, 31s/APK, 1/9 catálogo); `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py` (17 FRAMEWORK_PREFIXES, 4 GAME_ENGINES, manifest-only, single-string, most_common ≥60%).
