# Veredito — detecção de pacote/código-app à luz do SOTA de módulo primário (ICST 2026 #65)

**Data:** 2026-06-17
**Status:** VEREDITO para decisão — nada implementado
**Método:** 4 subagentes paralelos (3 de pesquisa web com verificação em fonte primária + 1 de crítica algorítmica adversarial) + sequential-thinking + skill scientific-critical-thinking. **Adendo (tarde):** +3 subagentes sobre substituição por ferramenta validada + extração/leitura local do PDF do A3Ident (§2-A).
**Calibrado por:** rejeição ICST 2026 #65 (objeção #65A#1 e #65A#4 — verbatim em `docs/20260219_icst2026_pareceres_65.md`)
**Refuta/refina:** `docs/20260617_estrategia_deteccao_pacote_defensavel.md` (a recomendação anterior "só validar + 3 parágrafos" — ver §1, REFUTADA em parte)
**Relacionados:** `docs/20260613_plano_package_detector_melhoria.md`, `docs/20260613_pesquisa_package_detection_sota.md` (ponto cego TPL), `docs/20260617_investigacao_sota_substituir_detector.md` (spike LibScout), `openspec/changes/gh67-package-detector-eval/`
**Aprofundamentos posteriores (mesma data):** `docs/20260617_veredito_abordagem_residual_deteccao_pacote.md` (refuta o residual como mecanismo, bound de erro quantificado) · `docs/20260617_solucoes_blackbox_deteccao_codigo_app.md` (LibHunter ASE'24 + soluções black-box + restrição de ofuscação)

---

## 0. TL;DR (o veredito em um parágrafo)

A recomendação anterior — **censo auto-rotulado → acurácia exata + 3 parágrafos + robustez, cortando o aparato inferencial** — **não sobrevive a um revisor determinado** e foi refutada em dois fundamentos *metodológicos* (não retóricos): (1) um censo rotulado por Claude e auditado pelo próprio autor mede **auto-consistência, não acurácia** — não responde ao que o revisor #65A pediu ("recall/accuracy"); (2) o "≤2,4%" é um **piso vendido como teto** e o "inerte sob ofuscação" tem **contraexemplo vivo** (`net.openid.appauth` é biblioteca que *usa* cripto). O caminho recomendado é a versão **honesta e ainda barata**: medir a acurácia contra um **oráculo independente** — histograma de pacotes por contagem de classes no dex (sinal que o detector **não** usa) cruzado com o **pacote declarado no repositório F-Droid upstream** (autoritativo, porque os apps são open-source) — numa amostra estratificada, com intervalo de confiança, tratando o censo como **distribuição descritiva**, e **medindo o gap prefixo-vs-conjunto**. Isso responde literalmente a #65A#1/#65A#4, não toca GATOR/parser/AJC, não descongela o gh63 — e o resultado da medição do gap define o *fallback* (se o gap for grande, escalar para redefinição de construto). A pesquisa de SOTA de **módulo primário** (PiggyApp, WuKong, DroidLegacy, Li Li TIFS'17) **fortalece** a defesa: ninguém produz um prefixo único — todos emitem conjuntos/clusters e todos ancoram no manifest, cuja fragilidade é **limitação comunitária documentada** (citável como *threat*, não como falha exclusivamente nossa).

**Adendo sobre substituição (§2-A):** investigada a hipótese de **substituir o detector por uma ferramenta existente validada** (com o contrato relaxado para um conjunto de pacotes). Veredito: **não há binário**. As duas abordagens que validam o output de código-app diretamente — **A3Ident (ICSME'20, 96,11% acc em F-Droid, verificado no PDF)** e **PiggyApp (CODASPY'13, 81%)** — não têm artefato público, e o A3Ident **pressupõe** um identificador de bibliotecas (Algoritmo 1) sem resolvê-lo — é clustering por cima do mesmo catálogo de lib que queríamos eliminar, além de exigir análise ICC ausente do androguard. Reimplementá-lo é um mini-projeto (= variante de D) com revalidação obrigatória, não um atalho. **Ganho real:** A3Ident é o **melhor precedent citável** (a âncora MainActivity/manifest é o método validado do SOTA, batendo PiggyApp) e valida o **construto-conjunto** — o nosso detector é uma instância single-prefix dele. Reforça A′, não a substitui.

---

## 1. Refutação séria da opção "só texto" (a recomendação anterior)

A recomendação anterior (doc `20260617_estrategia...`, §3 e §6) decidiu: "Change A: manter, **reenquadrada como censo** (cortar Wilson CI/kappa)"; "validar + 3 parágrafos basta"; "Change B: adiar". A skill exigia que essa conclusão sobrevivesse a uma tentativa séria de refutação. **Não sobrevive como está.** Dois golpes:

### Golpe 1 — censo auto-rotulado ≠ acurácia (validade da medição)

O revisor #65A pediu, literalmente, *"effectiveness (e.g., recall, accuracy)"*. A recomendação anterior propôs **rotular os 169 APKs com Claude** e o **autor auditar uma amostra**, reportando **acurácia exata** e **cortando Wilson CI/kappa** sob o argumento "é população, não amostra".

O erro é de **categoria**: a métrica não falha por ser amostra-vs-população; falha porque **o oráculo não é independente do preditor**. O ground truth é produzido pela mesma família de análise que o artefato sob teste (LLM lendo o mesmo manifest que o detector lê; auditoria pelo próprio autor do detector). Isso mede **auto-consistência**, não correção. Ataque do revisor (fatal em venue de topo): *"o ground truth foi produzido por um LLM e auditado pelo autor da ferramenta; recall medido contra um oráculo não-independente mede auto-consistência, não correção; sem ground truth independente, o número é infalsificável."* É exatamente uma objeção de **validade de medição** — três parágrafos não suprem um oráculo que não foi rodado.

Pior: cortar Wilson CI/kappa **remove justamente o que daria credibilidade**. A recomendação anterior otimizou na direção errada.

### Golpe 2 — "≤2,4%" é piso vendido como teto; "inerte sob ofuscação" é falso no universal

- **O bound 2,4% (4/169) é a taxa de erro DETECTADA, não um teto.** "Pior caso ≤2,4%" exige P(mis-pick não detectado)=0. Mas a auditoria usou o **próprio detector** + inspeção manual do autor → não pode limitar o erro *desconhecido* do artefato. Os 99 `same_package` **não** foram auditados com o mesmo rigor (e `same_package` também erra: se o pacote do manifest for um namespace de 3 segmentos compartilhado com uma lib que declara componentes sob o mesmo prefixo, dispara e super-escopa silenciosamente). O denominador "auditado a fundo" é < 169. Mesmo aceitando 4/169 como proporção amostral, o **Wilson upper bound 95% ≈ 6%**, não 2,4%. Reportar 2,4% como "pior caso" sem intervalo será sinalizado como ingenuidade estatística.
- **"Inerte sob ofuscação" só vale condicionalmente.** Vale quando: (i) o app é ofuscado por R8/ProGuard agressivo; (ii) classes reais viram `I3.c`/`j2.a` → um prefixo errado casa 0 classes. **Falha** nos ~25% **não-ofuscados**: aí `net.openid.appauth.*` está no dex com nome real, e o detector atribui as misuses **da biblioteca** (AppAuth usa cripto!) ao app → **inflação**, não inércia. Um revisor que puxe esse APK e verifique que não é ofuscado tem refutação limpa, e o parágrafo "inerte" passa a ler-se como *motivated reasoning*. O argumento neutraliza **1 de 3 modos de erro** (super-escopo p/ lib sob ofuscação agressiva), e **nada** faz pela deflação (narrow-pick/fork/multi-módulo), que não depende de ofuscação.

### O que da recomendação anterior SOBREVIVE

- A **calibração de não-visão-de-túnel** (§1.5): detecção é 1 de ~7 drivers; não super-investir. **Mantida e reforçada** (ver §6).
- O enquadramento **validade de construto (Wohlin)**: correto, mas precisa de mais corpo (ver §5).
- A decisão de **adiar a Change B**: sobrevive — mas por uma razão *mais forte* do que a dada (ver §4).
- A **Perna 3** (por que TPL-tools não se aplicam): sobrevive, com 3 correções de integridade que a própria pesquisa nova confirma/refina (ver §3.4).

---

## 2. O SOTA propriamente pesquisado: identificação de MÓDULO PRIMÁRIO (o ponto cego)

A rodada anterior pesquisou **detecção de TPL** (LibScout/LibRadar/LibD/LibPecker/LibID) e concluiu "só detectam libs". O ponto cego era a linha de **identificação do módulo primário / código-app**, que *computa diretamente* o código próprio do app. Pesquisada agora a fundo, com verificação em fonte primária. Achado central, com duas faces.

### 2.1 Tabela — o que cada sistema EMITE e de que depende

| Sistema | Venue/Ano | O que emite p/ "código-app" | Ancora no manifest? | Acurácia (auto-reportada) | Prefixo único limpo? |
|---|---|---|---|---|---|
| **PiggyApp** (Zhou et al.) | CODASPY 2013 | **cluster de pacotes** (PDG + clustering aglomerativo) | **Sim** — módulo com `ACTION.MAIN`; desempate por nome do app | 96,5% decoupling / 92,2% módulo primário (200 apps manuais) | **Não** — artefato de clustering |
| **WuKong** (Wang et al.) | ISSTA 2015 | **resíduo** após remover TPLs por clustering (→ virou LibRadar) | Não (filtro estrutural) | >10k variantes TPL / 105.299 apps | **Não** — conjunto de pacotes |
| **DroidLegacy** (Deshotels et al.) | PPREW@POPL 2014 | **módulos** (conjuntos de classes) por decoupling de call-graph | não verificado | UNVERIFIED (só abstract) | **Não** — módulo = conjunto |
| **Li Li et al.** (Piggybacking) | TIFS 2017 / TR'16 | **lista ranqueada** de pacotes candidatos a entry-point do rider | **Sim** — nome do pacote no manifest + LAUNCHER | 97% precisão; loc. acc@1≈68%, acc@5=83% | **Não** — lista ranqueada |
| **HookRanker** (Li et al.) | MOBILESoft 2017 | pacotes do rider ranqueados; **single-APK** (não precisa do original) | type1 hooks (não nome) | acc@5 = 83,6%/89,4% (500 pares) | **Não** — lista ranqueada |
| **LibD** (Li et al.) | ICSE 2017 | libs (conjunto); **lê o manifest p/ identificar o código-app e removê-lo** | **Sim** — *"identify application code according to the manifest files"* | GT indep.: 25% FP / 44% FN | host **removido**, não emitido |

*Citações de maior peso (verbatim, fonte primária):*
- **PiggyApp / Li Li TIFS'17:** *"using an agglomerative algorithm to cluster the packages, they select a primary module"* (mecanismo confirmado em dois papers independentes).
- **Li Li TIFS'17, finding F10:** documenta **73 casos** em que o piggybacker troca deliberadamente o Launcher para um pacote do payload, **quebrando** a suposição nome-do-pacote↔launcher. → A *exata* parede que o nosso detector enfrenta é **limitação comunitária documentada**.
- **HookRanker:** *"does not require access to the original benign version… in order to perform some form of diff analysis."* (único da família repackaging que serve ao nosso cenário single-APK).
- **LibD:** *"We identify application code according to the manifest files in the input apps; the application code… are trimmed off on the call graph."* → precedent citável de **identificação de host por manifest como pré-processamento de rotina**.
- **Rebooting survey (Li et al., TSE 2019/2021):** *"it remains challenging to distinguish which app is the original… the literature often relies on heuristics… not fully reliable."*

### 2.2 As duas faces do achado

**Face que nos FORTALECE (a maioria):**
1. **Ninguém emite um prefixo único de app.** Toda a linha opera em granularidade de módulo/cluster/lista porque a tarefa a jusante (comparação de similaridade, assinatura de malware, filtro de TPL) consome conjuntos. → Reduzir o módulo a **um prefixo** é uma **escolha de engenharia legítima e citável**, não um gap em relação ao SOTA. O SOTA não faz melhor o que precisamos — ele faz outra coisa.
2. **Computar o módulo primário é precedent aceito, não-trivial e empiricamente imperfeito** (PiggyApp reporta só 92,2% mesmo em conjunto curado). Citável como "esta etapa é reconhecidamente difícil", desarmando "vocês deviam ter resolvido".
3. **Todos ancoram no manifest/nome e admitem a fragilidade** (Li Li F10; Rebooting survey). → A nossa dependência do manifest é **a norma**, e a fragilidade é *threat* documentada — não falha exclusivamente nossa.
4. **A família repackaging carrier-vs-rider quase toda exige o app original** (diff pairwise) → **não se aplica** ao nosso single-APK. Exceções single-APK: HookRanker (rider ranqueado) e LibD (host por manifest). → Reforça que não há ferramenta "pronta" que entregue o nosso contrato.

**Face que nos AMEAÇA (convergente com a crítica algorítmica, §3.5):**
5. **O construto que o SOTA modela é um CONJUNTO de pacotes, não um prefixo.** PiggyApp/DroidLegacy = clusters; WuKong = resíduo; Li Li = lista. Que *toda* a literatura represente "código-app" como conjunto é evidência forte de que **o nosso prefixo único é uma simplificação lossy** — e um revisor informado sabe disso. Isso é o que a opção "só texto" não consegue tapar (ver §3).

### 2.3 Oráculo de validação a partir do SOTA?

- **PiggyApp / Li Li** dão um oráculo conceitual (módulo primário ancorado no launcher), e o corpus público de Li Li (1.497 pares piggyback, `github.com/serval-snt-uni-lu/Piggybacking`) é rotulado. **Mas** são pesados (PDG completo + clustering) → oráculo *batch*, não cross-check leve. **Veredito: usar como CITAÇÃO/precedent, não rodar.** O equivalente funcional barato é o histograma de classes do dex (§3.6) — mesmo princípio (estrutura do dex, não nome do manifest), sem a maquinaria.

---

## 2-A. Substituição completa por ferramenta de detecção de código-app? (investigação 2026-06-17, tarde)

**Pergunta do usuário:** relaxando o contrato a jusante para aceitar um **conjunto de pacotes-app** (em vez de uma string única), qual ferramenta **existente e validada** (ranqueada por veículo) pode **substituir completamente** o `package_detector`? Investigado com 3 subagentes (fonte primária) + leitura/extração local do PDF do A3Ident.

### 2-A.1 O contrato relaxado muda o bloqueio — mas não o gargalo

Aceitar um conjunto derruba o bloqueio **B1** ("uma string", do `docs/20260617_investigacao_sota_substituir_detector.md`). **Mas detecção de TPL (app = resíduo de lib) continua sendo o problema INVERSO e é descartada:** herda o **recall <50%** das ferramentas de lib (Zhan ASE'20 — libs perdidas vazam para o "conjunto-app" → super-escopo). O foco correto é a linha que **computa o código-app diretamente** (módulo primário), não a de lib.

### 2-A.2 Matriz — linha de detecção de código-app, ranqueada por veículo (verificada em fonte primária)

| Ferramenta | Veículo / tier | Output | Valida o output de **código-app** direto? | Acurácia (código-app) | Single-APK | Âncora manifest? | Artefato público |
|---|---|---|---|---|---|---|---|
| **A3Ident** (Wang, Meng, Wang, Chen, Ge, Li) | **ICSME 2020** (IEEE, SE sólido) | **módulo primário a nível de PACOTE** (partição app vs não-app via Louvain) | **Sim, diretamente** (Tab. I/IV) | **96,11% acc / 97,35% P / 96,11% R / 95,70% F1 em 416 apps F-Droid** (verificado no PDF) | **Sim** | **Sim** (MainActivity via manifest) | **Nenhum** (verificado: nada no PDF, nem em IEEE/arXiv/homepage do autor) |
| **PiggyApp** (Zhou et al.) | CODASPY 2013 (ACM, segurança médio) | módulo primário = **conjunto de pacotes** (PDG + clustering aglomerativo) | Sim | 92,2% self-report / **81,18% reavaliado** (Tab. IV do A3Ident, F-Droid) | Sim | Sim (ACTION.MAIN) | **Nenhum** |
| WuKong (Wang et al.) | ISSTA 2015 (top SE) | app = **resíduo** pós-clustering de lib | Não (subproduto; validação indireta via clone detection) | não medida | parcial | não | só LibRadar (Py2.7) |
| DroidLegacy (Deshotels et al.) | PPREW@POPL 2014 (**workshop, baixo**) | clusters de **classes** | Não | não medida | só p/ detecção | não | mirror Py2 abandonado |
| HookRanker / Li Li | MOBILESoft'17 / **TIFS 2017** (top journal) | localiza o **rider** (código injetado) | **Direção errada** (acha o injetado, não o host) | — | sim (HookRanker) | parcial | só **dataset** (`*/Piggybacking`, 950 pares) |

**Correção factual importante:** os repos `lilicoding/Piggybacking` e `serval-snt-uni-lu/Piggybacking` que aparecem em busca **NÃO são o PiggyApp** — são o trabalho posterior de Li Li ("Ungrafting", TIFS'17), um **dataset rotulado** (não ferramenta) que localiza o **rider**, não o host. Não servem como substituto.

### 2-A.3 Verificação direta do A3Ident (li o PDF, extração local `pdftotext`)

- **Âncora (verbatim, §III–IV):** *"The primary module can be determined according to where MainActivity is located… it can be easily identified by querying AndroidManifest.xml."* → **a mesma heurística do nosso detector**.
- **Acurácia (Tabela I, granularidade Package):** P 96,00% · R 97,69% · F1 95,99% · Acc 95,81%. **Tabela IV (F-Droid, 416 apps):** A3Ident Acc **96,11%** vs **PiggyApp 81,18%**. → método validado **no nosso ecossistema (F-Droid)**, batendo PiggyApp.
- **Métrica:** os 96% medem a **acurácia da partição por autor** (precision/recall/F1 do agrupamento de pacotes), **não** "o prefixo de código-app está certo" — métrica *adjacente* à nossa, não idêntica.
- **Artefato:** **nenhum link de replicação no PDF** (só refs a libs de terceiros: `python-louvain`, `aosp-mirror`). Busca web confirma ausência de repositório.

### 2-A.4 Análise do algoritmo (reimplementabilidade)

Decoupling em 5 passos: (1) **grafo de pacotes** com 3 arestas ponderadas — call, inheritance, **ICC**; (2) **agregação** (Algoritmo 1): mesma id para pacotes da mesma lib e para componentes do manifest; (3) **merge por ciclo** (DFS); (4) **Louvain** sobre peso `sim(u,v)=max(nor(corr),nor(struc))` — `corr=e^(−min Floyd-dist)`, `struc=Σ1/i` sobre profundidade do NCP; (5) **módulo primário** = cluster da `MainActivity`.

| Componente | Fonte | Temos? | Custo |
|---|---|---|---|
| Pacotes + filtro android/x; arestas **call**, **inheritance**; merge por ciclo; Floyd; corr/struc/sim; Louvain; âncora MainActivity | androguard + `networkx` + `python-louvain` | ✅ in-process | baixo |
| Aresta **ICC** | análise ICC de intents | ⚠️ não no androguard | **alto** (IC3/Epicc, ou GATOR) |
| **Identificar libs** (Algo 1, linha 3) | — | ❌ **subespecificado** | **= o nosso problema atual** |

**Furo 1 (crítico):** o A3Ident **não resolve** "quais pacotes são lib" — ele **pressupõe** um identificador de lib (Algo 1, linha 3, *"identify contained libraries"*, e critica LibScout/LibD por "detectar só um subconjunto"). É uma **camada de clustering por cima de um filtro de lib** — exatamente a heurística (`FRAMEWORK_PREFIXES`/catálogo) que queríamos substituir. **Não há fuga do catálogo de lib.**
**Furo 2:** a aresta ICC exige tooling ausente (IC3/Epicc, ou inverter a ordem do GATOR que hoje consome `code_package`); largar ICC degrada → os 96% deixam de transferir.
**Furo 3:** métrica validada ≠ nossa métrica → reimplementação não-idêntica exige **revalidação** de qualquer forma (o 96% é deles).

### 2-A.5 Veredito de substituição

**Não existe substituição por ferramenta pronta.** As duas únicas que validam o output de código-app diretamente (A3Ident 96% F-Droid; PiggyApp 81%) **não têm artefato público**. Mesmo como *método reimplementado*, o A3Ident (a) carrega a **mesma dependência de catálogo de lib**, (b) exige **ICC**, (c) tem **métrica diferente** → re-validação obrigatória. É um **mini-projeto de engenharia + revalidação**, não uma troca.

**O que o A3Ident realmente entrega:** o **melhor precedent citável** — prova peer-reviewed de que a âncora MainActivity/manifest é o **método validado do SOTA** (96% em F-Droid, batendo PiggyApp), **e** valida o **construto-conjunto** que o usuário quer. O nosso detector é uma **instância simplificada** (single-prefix em vez de clustering) desse método. Confirma o veredito geral: o gargalo "quais pacotes são lib" **não é resolvido por ferramenta alguma** — é sempre heurística + catálogo.

→ Acrescenta duas opções à matriz §4: **F** (reimplementar A3Ident como detector-conjunto in-process) e o reforço de que **citar A3Ident/PiggyApp** fortalece a Opção A′.

---

## 3. Avaliação honesta do nosso detector (crítica algorítmica adversarial)

### 3.1 Validade de construto: "um prefixo" é defensável?

**Não, em geral.** O detector colapsa o *conjunto* de pacotes-app em uma string via 4 operações lossy (`extract_package(level=3)`, `find_common_prefix` sobe a árvore, `most_common` pega 1 dominante, fallback=manifest). Como o `code_package` é usado como **filtro** em GATOR/parser/AJC, o erro tem duas direções. Quebras estruturais:

| Quebra | Exemplo | Branch que dispara | Viés na contagem de misuses |
|---|---|---|---|
| **Multi-módulo first-party** | `org.fossify.notes` + `org.fossify.commons` | `common_prefix`→`org.fossify` (super) **ou** `most_common`→só `.notes` (sub) | **Bidirecional**: inflação (puxa commons/vendored) ou **deflação** (perde cripto em `commons`) |
| **Fork com upstream dominante** | rider domina o dex | `most_common`→namespace upstream | **Deflação** do código *novo* do fork (o mais interessante p/ misuse) |
| **Namespace de hospedagem** | `io.github.alice.app` + `io.github.bob.lib` | `common_prefix`→`io.github`, e `is_valid_prefix` **aceita** (manifest startswith) | **Inflação massiva**: toda lib hospedada no GitHub vira "app" |
| **Pacotes não relacionados** | SDK adquirido + shell fino | sem prefixo comum → fallback manifest | **Deflação** (~0% cobertura, ~0 misuses) |

O ponto crítico: **a direção do erro não é controlada pelo construto, é controlada por acidente do manifest** (qual branch dispara depende do limiar de 60% e da contagem de componentes). E a deflação esconde preferencialmente misuses em **código compartilhado/adicionado** — exatamente o alvo de maior valor de um estudo de cripto-misuse.

Os casos `most_common` (29) + `common_prefix` (17) = **46/169 (27%)** são exatamente os que não reduzem trivialmente. Não é corner case.

### 3.2 Deveria ser um CONJUNTO?

**Sim, principiadamente** — "código-app" é intrinsecamente um conjunto de namespaces (convergente com §2.2 face 5). Um conjunto é estritamente mais expressivo e degrada ao prefixo quando é singleton; não há custo científico, só de engenharia. Versão de baixa engenharia: **GATOR com escopo amplo + post-filtro preciso contra o conjunto** (`any(startswith(p) for p in set)` no parser; união de `within()` no AJC) — *escopar amplo, filtrar preciso*. **Mas** mudar o detector muda os picks → muda o experimento → **descongela o gh63 pinado** → fora do escopo da ressubmissão (cujos números são fixos). Logo o conjunto é **fix futuro OU acionado se a medição do gap (§3.6) for grande**, não a jogada padrão agora.

### 3.3 A matemática de robustez é sólida?

**Não como está** (ver Golpe 2, §1). O "≤2,4%" assume completude da auditoria (que nada estabelece) e usa um oráculo que é o próprio suspeito. A re-execução com/sem os 4 mis-picks testa sensibilidade aos **4 conhecidos** — não diz nada sobre um 5º não-encontrado. Para ser honesto: erro estimado por **oráculo independente**, com **intervalo de confiança**, distinguindo "erro nos casos auditados" de "erro no corpus".

### 3.4 Correções de integridade obrigatórias (a pesquisa nova pegou erros factuais do doc anterior)

A `docs/20260617_estrategia...` (§1, tabela) e qualquer texto do artigo devem corrigir:

1. **CryptoLint (Egele, CCS'13):** são **11** pacotes na whitelist (Tabela 1), **não ~12**; e é um **guarda anti-over-counting** (descarta o app só se o *único* uso de cripto está nessas libs), **não** um separador app-vs-lib geral.
2. **CrySL/CogniCrypt — NÃO citar a lista de "4 prefixos" (`com.android`/`com.google`/`com.facebook.ads`/`com.unity3d`).** Essa lista é um **script R de pós-processamento** (`rbonifacio/TR-Meta-CrySL-Package/.../violation-analysis.Rmd`), **não a ferramenta**. (Atenção: `rbonifacio` = Rodrigo Bonifácio, **co-autor do nosso paper** — é script *nosso*, não do CogniCrypt.) A ferramenta real exclui apenas `android`/`androidx` e usa **`Soot isApplicationClass()`**. Citar isso.
3. **CryptoGuard (CCS'19, §6.2):** citação **CONFIRMADA verbatim** — *"We distinguished app's own code from libraries by using the package information from AndroidManifest.xml."* Sem acurácia reportada; **não** declarado como threat. (É o precedent que excedemos.)
4. **CRYLOGGER (S&P'21):** **CONFIRMADO** — nenhuma separação app-vs-lib (instrumenta a camada JCA/JCE compartilhada; app + libs juntos).
5. **FlowDroid (PLDI'14):** os números são **93% recall / 86% precision** (sobre *taint* no DroidBench, **não** escopo app-vs-lib); mecanismo de escopo = `Scene.getApplicationClasses()`/`isApplicationClass()` via `-process-dir` + `-include`/`-exclude`. Não há opção literal `set-application-classes`.
6. **Amandroid (TOPS'18, §6.1):** **CONFIRMADO** — exclusão **opcional e manual** de TPLs por escala.

### 3.5 Existe definição canônica de "código-app" na literatura recente?

**Não.** (Resultado verificado.) O campo **não tem** definição canônica e validada da fronteira app-vs-lib. As heurísticas de fronteira em tools de cripto/taint são todas **não-validadas** pelos próprios autores (whitelist por nome; prefixo do manifest; flag de application-class do Soot). Os detectores de TPL *são* benchmarkados (Zhan et al., ASE 2020), mas (a) o ground truth é um conjunto de TPLs *conhecidas*, validando *detectores*, não uma partição de um app arbitrário em "código próprio vs lib"; e (b) recall **< 50%** mesmo nos melhores. → **Podemos honestamente escrever: o campo usa heurísticas não-validadas; avaliar a nossa explicitamente já atinge/excede o padrão prevalecente, sem superdimensionar.**

### 3.6 A saída: oráculo independente (alta alavancagem)

O **histograma de pacotes por contagem de classes no dex** (via androguard/dexlib2 — já temos) é um sinal que o detector **não** usa (ele usa *componentes do manifest*; o histograma usa *todas as classes do dex*). Cruzado com o **pacote declarado no repositório F-Droid/upstream** (autoritativo, porque os apps são **open-source** — o pacote real é *conhecível*, não inferido), produz um oráculo **genuinamente independente**. Numa amostra estratificada por `detection_method`, com **segundo anotador (mantenedor) → Cohen's κ** e **Wilson CI**, isso de um golpe:
- converte **censo → acurácia real** (mata a circularidade do Golpe 1);
- **quantifica o gap prefixo-vs-conjunto** (§3.1/§3.2): quantos dos 46 não-triviais têm footprint multi-pacote; quantas misuses caem **fora** do prefixo escolhido;
- **limita mis-picks não-detectados** (ataca o Golpe 2 / completude);
- **não toca** GATOR/parser/AJC nem descongela o gh63.

**Reframe poderoso:** a queixa "só F-Droid" (#65C) vira **ativo** — open-source ⇒ ground truth **autoritativo** disponível. E há **complementaridade limpa**: app ofuscado → o histograma dex degrada, mas aí o mis-pick é de fato inerte (claim condicional vale) E o repo ainda dá o pacote; app não-ofuscado → o histograma dex funciona e *pega* o mis-pick (o caso perigoso do Golpe 2 fica coberto pela medição, não pela narrativa).

---

## 4. Matriz de opções (rigor × tempo × risco de re-rodar gh63)

| Opção | O que é | Rigor / sobrevive ao revisor? | Custo | Risco gh63 | Veredito |
|---|---|---|---|---|---|
| **A** | Só validar (censo auto-rotulado) + threats + robustez (**= rec. anterior**) | **Não** — oráculo não-independente; piso-como-teto | baixo | nenhum | ❌ **REFUTADA** |
| **A′** | Validar com **oráculo INDEPENDENTE** (dex-histograma + repo F-Droid), amostra estratificada, **Wilson CI + κ**, censo só descritivo, **+ medir gap prefixo-vs-conjunto** | **Sim** (data-driven, não narrado) | baixo-médio | **nenhum** | ✅ **RECOMENDADA** |
| **B** | A′ + Change B (manifest-affinity no detector) | parcial — fixa inflação (`io.github`/appauth) mas **piora deflação** (`fossify.commons`); não substitui o conjunto | médio | muda picks → **descongela gh63** | ⏸️ **ADIAR** (backlog/futuro) |
| **C** | A′ cruzando com SOTA primary-module (PiggyApp/Li Li) como oráculo rodado | alto, mas **pesado** (PDG+clustering batch); dex-histograma é equivalente barato | alto | nenhum | ↪️ usar como **CITAÇÃO**, não rodar |
| **D** | Redefinir construto p/ **conjunto** (GATOR amplo + post-filtro) | o fix principiado e completo | alto (3 tools) | muda experimento → **descongela gh63** | 🔮 **futuro**, OU acionado se gap grande |
| **F** | **Substituir por ferramenta de detecção de código-app existente e validada** | — | — | — | ❌ **NÃO EXISTE** binário; A3Ident/PiggyApp sem artefato (§2-A). Reimplementar A3Ident = mini-projeto que **carrega o mesmo catálogo de lib + ICC + revalidação** → vira variante de D, não atalho |
| **E** | **Combinação recomendada** | — | — | — | **A′ agora (citando A3Ident/PiggyApp como precedent validado do método); D condicional ao gap; B/C/F backlog** |

**Por que F (substituição) não é viável:** §2-A. Não há ferramenta pronta que emita pacote-app validado; as duas que validam o output (A3Ident ICSME'20 96% F-Droid; PiggyApp CODASPY'13 81%) não têm artefato, e o A3Ident **pressupõe** um identificador de lib (Algo 1) — não elimina o gargalo. Reimplementá-lo = D com custo extra de ICC + revalidação. **Mas A3Ident é o melhor precedent citável** e reforça A′ (nosso detector = instância single-prefix do método validado).

**Por que A′ e não A:** A′ é a *versão honesta* de A. Mesmo custo de ordem de grandeza (rotular amostra + script de oráculo dex que já temos via androguard + cross-ref de repos), mas troca um número infalsificável por um número defensável. A diferença não é de esforço — é de validade.

**Por que B continua adiada (razão mais forte que a anterior):** a crítica mostrou que manifest-affinity **troca inflação por deflação** — ao prender o pick ao namespace do manifest, torna `org.fossify.commons` *mais* provável de ser excluído, piorando os falsos negativos em código compartilhado (onde helpers de cripto vivem). B é um **patch parcial do sintoma**, não substituto do conjunto. Além de não ajudar os números **pinados** do artigo.

---

## 5. Caminho recomendado + fallback (com refutação embutida)

### Recomendado: **A′ — medição com oráculo independente** (Change A reenquadrada — ver §6)

1. **Denominador explícito (resolve #65A#1 "557 ou 103?"):** funil completo com números em cada estágio (estaticamente-JCA → instrumentados → executados → conjunto da eval) + afirmar que o detector roda em **todo app analisado**.
2. **Acurácia contra oráculo INDEPENDENTE** numa amostra estratificada por `detection_method` (incluindo `same_package`): oráculo = histograma de classes dex (androguard) **+** pacote declarado no repo F-Droid/upstream. Reportar **accuracy com Wilson CI** + **Cohen's κ** entre o oráculo e a rotulagem do mantenedor.
3. **Censo dos 169 = distribuição descritiva** (99 same_package / 29 most_common / …), **não** apresentado como acurácia.
4. **Gap prefixo-vs-conjunto quantificado:** % dos 46 não-triviais com footprint multi-pacote; % de misuses fora do prefixo. **É o número que decide o fallback.**
5. **Matriz de confusão app-vs-lib + taxa de lib-mis-pick** (os 4 mis-picks como first-class) — resolve a face app-vs-lib de #65A#1 e #65A#4.
6. **Parágrafo de obfuscação na versão CONDICIONAL verificada** (não o universal): *"sob ofuscação agressiva (X% do corpus, medido), um prefixo de lib super-escopado casa poucas/nenhuma classe renomeada; verificamos nos APKs afetados que 0 misuses foram atribuídas ao prefixo errado."*

### Fallback (acionado pelo resultado do passo 4)

- **Gap pequeno** → defende-se a simplificação de prefixo único **com dados** (o gap medido vira o threat quantificado). Para aqui. Sem código.
- **Gap grande** → não há prosa que salve. Escalar para **(D)** — post-filtro por conjunto (GATOR amplo + filtro preciso, baixa engenharia) para experimentos futuros — **e** reportar o gap como limitação de construto forte no artigo atual (honestidade > esconder). gh63 permanece pinado; o conjunto entra em experimento futuro.

### Por que isto sobrevive à refutação (auto-teste)

- *"Seu oráculo dex também é heurística"* → é **independente** do sinal do detector; e para open-source o **repo dá o pacote declarado real** (autoritativo). κ entre fontes. Sobrevive.
- *"Dex degrada sob ofuscação"* → aí o mis-pick é inerte (claim condicional) **e** o repo cobre. Complementaridade. Sobrevive.
- *Residual honesto:* se o gap for grande, A′ sozinha não basta — por isso o fallback D está explícito. O veredito é **condicional à medição**, não um novo otimismo.

---

## 6. O que escrever no artigo (respondendo literalmente a #65A#1 e #65A#4)

**#65A#1** (*"effectiveness (recall, accuracy) not reported; unclear if applied to all 557 or only 103; app vs library code"*):
- (a) **Acurácia:** acurácia exata na amostra estratificada **com Wilson CI**, contra oráculo independente (dex-histograma + repo), **+ κ**. Censo dos 169 como distribuição descritiva.
- (b) **Denominador:** funil completo; detector roda em **todo app analisado** (não numa subamostra).
- (c) **App-vs-lib:** matriz de confusão + taxa de lib-mis-pick; construto declarado (prefixo único) com o **gap prefixo-vs-conjunto quantificado** como threat.

**#65A#4** (*comparação CogniCrypt ignora "scope of analyzed code (application vs. library)"*):
- Restringir **ambos** (nosso + CogniCrypt) ao **mesmo escopo de código-app**. Citar **CryptoGuard CCS'19 §6.2** (prefixo do manifest) como precedent; descrever que **CogniCrypt usa Soot `isApplicationClass()` + `android`/`androidx`** (NÃO a lista de 4 prefixos — §3.4 correção 2).

**Enquadramento (Trabalhos Relacionados / Ameaças):**
- Precedent de **identificação de host por manifest como pré-processamento de rotina**: **LibD (ICSE'17)** (*"identify application code according to the manifest files"*); **CryptoGuard (CCS'19)**.
- Precedent de que **computar o módulo primário a nível de pacote é método validado do SOTA, ancorado no manifest**: **A3Ident (ICSME'20)** — *"the primary module… where MainActivity is located… identified by querying AndroidManifest.xml"*, **96,11% acc em F-Droid**, batendo PiggyApp (81%) — o nosso detector é uma **instância single-prefix** desse método. Precedent de que a etapa é aceita, não-trivial e imperfeita: **PiggyApp (CODASPY'13)** (92,2% mesmo curado), **Li Li (TIFS'17)**.
- Fragilidade do manifest/nome como **limitação comunitária documentada** (não falha só nossa): **Li Li TIFS'17 finding F10** (73 casos de launcher trocado); **Rebooting survey (TSE'19/21)** (*"challenging… heuristics… not fully reliable"*).
- Por que TPL-tools SOTA **não** se aplicam: emitem **conjunto de libs** (não `code_package`); recall <50% sob ofuscação (Zhan ASE'20); spike LibScout in-house (0/9 libs no catálogo, 31s/APK — `docs/20260617_investigacao_sota_substituir_detector.md`).

---

## 7. Quanto da Change A / B é necessário (revisado à luz do SOTA)

### Change A (gh67) — **REENQUADRAR (reverter o corte do aparato inferencial)**

A revisão anterior cortou Wilson CI/kappa e adotou "censo→acurácia exata". **Isto é o que a refutação derruba.** Change A deve:
- **ADICIONAR oráculo independente** = histograma de classes dex (androguard) **+** cross-ref do repo F-Droid/upstream. (Substitui/eleva a ideia de "LibScout como oráculo offline" — o dex-histograma é mais barato, in-process, e o repo é autoritativo.)
- **MANTER/RESTAURAR Wilson CI + Cohen's κ** numa **amostra estratificada** (não cortar — é o que dá credibilidade).
- **Censo dos 169 = descritivo** (distribuição por método), não acurácia.
- **ADICIONAR a métrica do gap prefixo-vs-conjunto** (decide o fallback §5).
- **MANTER:** CSV de ground-truth versionado com evidência, script reproduzível, estratificação por `detection_method`, matriz app-vs-lib, taxa de lib-mis-pick, baseline pinado ao git hash (INV-CORE-35).
- A re-execução de robustez (paper-side) permanece, mas **enquadrada como teste de sensibilidade aos 4 conhecidos**, não como bound de pior caso.

→ Ação OpenSpec: ajustar `gh67-package-detector-eval` (design.md D-B/D-D e tasks) via skill apropriada. **Não** é o "censo enxuto" da rec anterior; é "amostra com oráculo independente + CI + κ + gap", mantendo o censo como descritivo.

### Change B (manifest-affinity) — **ADIAR** (confirmado, razão mais forte)

Patch parcial: fixa inflação, **piora deflação**; não substitui o conjunto; não ajuda números pinados. Backlog para experimentos futuros (junto com D5/#68). Se um dia implementada, vir **acoplada ao conjunto (D)**, não isolada.

---

## 8. Enquadramento threat-to-validity (Wohlin et al.)

- **Validade de construto** (principal): "prefixo único" operacionaliza imperfeitamente "código próprio do app" — o SOTA modela como **conjunto** (§2.2/§3.2). Mitigação: **gap prefixo-vs-conjunto quantificado** (§3.6). Risco residual: apps multi-módulo/fork/hosting.
- **Validade de conclusão:** taxa de erro estimada por **oráculo independente com CI** (não o piso 2,4%). Mitigação do erro aleatório de rotulagem: **κ** entre anotador e oráculo.
- **Validade interna:** viés sistemático de instrumentação (o filtro por prefixo enviesa contagens **na direção da variável dependente** — §3.1). Tornar **visível no design**, não só na seção de ameaças (crítica anti-boilerplate de Verdecchia ESEM'24): referenciar a medição do gap a partir do parágrafo de construto.
- **Distinção limitação vs ameaça:** "não tratamos multi-módulo por conjunto neste experimento (pinado)" = *limitação* de escopo; "o prefixo pode super/sub-escopar em apps multi-módulo, enviesando contagens" = *ameaça* (com a mitigação medida).

---

## 9. Decisões propostas (para discutir antes de implementar)

| # | Decisão | Recomendação |
|---|---|---|
| (a) | Caminho | **E** = A′ agora (oráculo independente dex+repo, Wilson CI, κ, censo descritivo, gap prefixo-vs-conjunto); **D** condicional ao gap; **B/C** backlog/citação. |
| (b) | Change A | **Reenquadrar revertendo o corte:** + oráculo independente, + Wilson CI/κ em amostra, + métrica do gap; censo só descritivo. (Não o "censo enxuto" anterior.) |
| (c) | Change B | **Adiar** (patch parcial; se feita, acoplada ao conjunto D). |
| (d) | Construto | Declarar "prefixo único" como ameaça de construto **quantificada**; conjunto (D) é fallback acionado por gap grande / futuro. |
| (e) | Integridade | Corrigir CryptoLint (11, guarda), **remover** lista de 4-prefixos do CogniCrypt (é script nosso, citar Soot `isApplicationClass`), FlowDroid 93%R/86%P. |
| (f) | Calibração | Detecção = 1 de 7 drivers; A′ fecha #65A#1 e parte de #65A#4. **Não super-investir** — os drivers de maior peso (cap 300s, contagem unique-misuse, reposicionamento de novidade) são tratados fora deste doc. |

**Próximo passo (após aprovação):** ajustar `gh67-package-detector-eval` via skill OpenSpec (não editar artefatos à mão); registrar a medição de gap + re-execução de robustez como tarefas; manter Change B/D no backlog.

---

## Apêndice — fontes primárias verificadas nesta rodada

**Módulo primário / piggyback (ponto cego, novo):**
- **A3Ident — Wang, Meng, Wang, Chen, Ge, Li, ICSME 2020** (arXiv:2008.13768; DOI 10.1109/ICSME46990.2020.00064). **PDF lido e extraído localmente nesta sessão.** Decoupling de autoria: grafo de pacotes (call/inheritance/ICC) → agregação (Algo 1, libs+componentes do manifest) → merge por ciclo → Louvain (`sim=max(nor(corr),nor(struc))`) → módulo primário = cluster da MainActivity. **Verbatim:** *"The primary module can be determined according to where MainActivity is located… easily identified by querying AndroidManifest.xml."* **Tab. I (Package):** P 96,00% / R 97,69% / F1 95,99% / Acc 95,81%. **Tab. IV (416 F-Droid):** A3Ident Acc 96,11% vs PiggyApp 81,18%. **Sem artefato público** (verificado no PDF + busca). Furos p/ reimplementação: Algo 1 linha 3 *"identify contained libraries"* subespecificado (= nosso problema); aresta ICC ausente do androguard.
- PiggyApp — Zhou et al., CODASPY 2013 (PDG + clustering aglomerativo; primário ancorado em `ACTION.MAIN`; 96,5%/92,2% em 200 apps self-report; **reavaliado pelo A3Ident a 81,18% em F-Droid** — *re-checar % do PDF da ACM antes de citar o número self-report*). Sem artefato público.
- WuKong — Wang et al., ISSTA 2015 (resíduo pós-TPL; → LibRadar).
- DroidLegacy — Deshotels et al., PPREW@POPL 2014 (módulos; números UNVERIFIED — só abstract).
- Li Li et al., "Understanding Android App Piggybacking", IEEE TIFS 2017 (lista ranqueada; finding F10: 73 launchers trocados); HookRanker, MOBILESoft 2017 (single-APK, acc@5 83,6%/89,4%); Ungrafting TR-SNT-2016-2.
- LibD — Li et al., ICSE 2017 (*"identify application code according to the manifest files"*; GT 25%FP/44%FN).
- Li et al., SANER 2016 (whitelist por clustering de nome de pacote, 3 segmentos).
- Survey Rebooting — Li, Bissyandé, Klein, TSE 2019/2021 (arXiv:1811.08520; separação original/injetado "challenging… heuristics… not fully reliable").
- Survey TPL — Zhan et al., ASE 2020 (arXiv:2108.03787; recall TPL <50%).

**Escopo app-vs-lib em cripto/taint (verificado/corrigido):**
- CryptoGuard — Rahaman et al., CCS 2019, §6.2 (manifest prefix — CONFIRMADO verbatim; sem acurácia; não-threat).
- CryptoLint — Egele et al., CCS 2013 (11 pacotes, guarda anti-over-counting — CORRIGIDO).
- CrySL/CogniCrypt — Krüger et al., ECOOP 2018/TSE (Soot `isApplicationClass` + `android`/`androidx`; lista de 4 prefixos é script R do co-autor, NÃO a tool — REFUTADO/corrigido).
- CRYLOGGER — Piccolboni et al., S&P 2021 (sem separação — CONFIRMADO).
- FlowDroid — Arzt et al., PLDI 2014 (93%R/86%P taint; `Scene.getApplicationClasses`/`-process-dir`).
- Amandroid/Argus-SAF — Wei et al., TOPS 2018, §6.1 (exclusão TPL opcional/manual — CONFIRMADO).

**Evidência local:** `docs/20260617_investigacao_sota_substituir_detector.md` (spike LibScout: 0/9 libs no catálogo, saída=manifest, 31s/APK); `out/package_detector_audit/` (auditoria 169 APKs); `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py` (o detector).

**Itens a re-verificar antes de citar número exato:** % de decoupling do PiggyApp (96,5%/92,2% — fonte única academia.edu); internals/numéros do DroidLegacy (UNVERIFIED); corpo do PDF do WuKong (números via abstract+survey).
