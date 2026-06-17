# Estratégia: detecção de pacote/código-app como pré-processamento DEFENSÁVEL

**Data:** 2026-06-17
**Status:** RECOMENDAÇÃO para discussão — nada implementado
**Autor:** investigação multi-agente (4 subagentes + sequential-thinking + pesquisa peer-reviewed)
**Relacionados:** `docs/20260613_plano_package_detector_melhoria.md`, `docs/20260613_pesquisa_package_detection_sota.md`, `docs/20260617_investigacao_sota_substituir_detector.md`, `openspec/changes/gh67-package-detector-eval/`, memória `project_package_detector_improvement_plan`
**Calibrado por:** rejeição ICST 2026 (submission #65) — revisores levantaram a detecção de pacote **explicitamente** (§1.5)

---

## 0. A pergunta (reformulada)

A pergunta deixou de ser de engenharia ("como melhorar/substituir o `package_detector.py`") e virou **estratégia de artigo**:

> Como tornar a nossa detecção de pacote/código-app **defensável** perante revisores rigorosos, como **etapa de pré-processamento validada** (não uma contribuição), **sem** um artigo dedicado e **sem** tempo extra?

Restrição estratégica que governa tudo: revisores deste subcampo estão mais rigorosos quanto a detecção de pacote/lib; uma solução SOTA de verdade exigiria um artigo dedicado **antes** de poder ser usada — não há tempo. Logo: **não** posicionar detecção de pacote como contribuição; **não** construir detector novo. Apenas torná-la defensável.

**Resposta curta:** é totalmente viável e barato. A nossa detecção + uma validação leve **já excede** o padrão publicado neste exato subcampo. O trabalho é de **enquadramento** (3 parágrafos no artigo) + **uma medição** (Change A, reaproveitada) + **uma análise de robustez** (paper-side, leve). A Change B (corrigir o detector) **não é necessária** para defender o experimento atual e deve ser adiada.

---

## 1. Achado central da pesquisa: o piso de rigor neste subcampo é BAIXO

Levantamos como artigos peer-reviewed de análise Android / RV / cripto-misuse tratam o problema "qual código é do app vs lib/framework" **quando isso não é a contribuição deles**. O padrão de facto é coarso e **não validado**:

| Sistema | Venue/Ano | Como separa app vs lib | Reporta acurácia? | Cita ferramenta TPL? | Declara como ameaça à validade? |
|---|---|---|---|---|---|
| **CryptoLint** (Egele et al.) | CCS 2013 | whitelist manual de pacotes (~12 entradas) | Não | Não | Não |
| **CryptoGuard** (Rahaman et al.) | CCS 2019 | **prefixo do pacote do `AndroidManifest.xml`** (§6.2) | Não | Não | Não |
| **CrySL / CogniCrypt** (Krüger et al.) | ECOOP 2018 / TSE | exclusão hard-coded de 4 prefixos (`com.android`, `com.google`, `com.facebook.ads`, `com.unity3d`) | Não | Não | Não |
| **CRYLOGGER** (Piccolboni et al.) | S&P 2021 | nenhuma — atribui todos os callers "ao app" | Não | Não | Não |
| **FlowDroid** (Arzt et al.) | PLDI 2014 | default app-vs-library do Soot (`isApplicationClass`) + exclude-list | Não (os 93%/86% são de *taint*, não de escopo) | Não | Não |
| **Amandroid** (Wei et al.) | CCS 2014 / TOPS 2018 | exclusão **opcional** e manual de TPLs (motivada por escala) | Não | Não | Não |
| **IccTA** (Li et al.) | ICSE 2015 | herda defaults FlowDroid/Soot | Não | Não | Não |
| **DroidSafe** (Gordon et al.) | NDSS 2015 | modela o framework; **dobra ad-libs no código do app** | Não | Não | Não |
| **RV-Android / RVSec** | RV 2015 / TSE 2023 | escopo = pointcuts AspectJ sobre a API monitorada; **sem** filtro de pacote app/lib | Não | Não | Não (a limitação real é a cobertura AspectJ) |

**Citação-chave (CryptoGuard, CCS 2019, §6.2):** *"We distinguished app's own code from libraries by using the package information from AndroidManifest.xml."* É exatamente o ponto de partida do nosso detector — e o nosso vai **além**, porque o manifest diverge do código real em ~27,5% dos APKs e nós corrigimos isso.

**Conclusão (barra mínima aceita):** quando a separação app-vs-lib **não é a contribuição**, revisores de CCS/S&P/PLDI/NDSS/ICSE/ECOOP/TSE aceitam: (1) declarar a heurística explicitamente e citar precedente; (2) **sem** reportar acurácia da etapa; (3) **sem** ferramenta TPL como gate; (4) ameaça à validade é **opcional**. Ou seja: **o nosso detector + qualquer validação já está acima do padrão publicado.**

**MAS — atenção (ver §1.5):** essa é a barra *no agregado da literatura*. O nosso pool de revisores específico (ICST 2026 #65) **não** ficou nessa barra: pediu acurácia/recall e garantia app-vs-lib **explicitamente**. Logo, para a nossa submissão o risco não é só de percepção — é uma objeção **já registrada**. Isso **fortalece** (não enfraquece) a decisão de fazer a Change A.

---

## 1.5. Evidência dos revisores reais (ICST 2026, submission #65) — calibração

O artigo predecessor (*"On the Effectiveness of Integrating Android Test-Case Generation with Runtime Verification for Detecting Cryptographic API Misuses"*) foi **rejeitado** (3× weak reject; 26,9% de aceitação). A detecção de pacote apareceu **explicitamente** como falha de *soundness*. Citações textuais:

- **#65A, Soundness #1 (o alvo direto deste doc):** *"The heuristic package-detection algorithm's effectiveness (e.g., recall, accuracy) is **not reported**, and it is unclear if the algorithm was applied to **all 557 apps or only the 103**, making it hard to properly assess the extent to which the detected packages contain the **application, rather than library, code**."*
- **#65A, Soundness #4 (reaparece no comparativo):** a comparação com CogniCrypt *"fails to account for… the **scope of analyzed code (application vs. library)**"*.

O revisor pediu **exatamente** os três produtos da Change A: **(a)** acurácia/recall reportada; **(b)** clareza sobre o **denominador** (a quais apps o detector foi aplicado); **(c)** garantia de que o pacote detectado é **app, não lib**. Nossa recomendação de **censo → acurácia exata** responde (b) de forma direta: reportar o denominador exato em **cada estágio do funil** (557 estaticamente-JCA → 193 instrumentados → 188 avaliados → conjunto da eval), deixando claro que o detector roda em **todo app analisado**, não numa subamostra. A matriz app-vs-lib + taxa de lib-mis-pick da Change A cobrem (a) e (c).

**Dupla função do escopo app-vs-lib:** a mesma validação serve para defender os nossos números **e** para corrigir a comparação com CogniCrypt (#65A#4) — comparar like-for-like restringindo ambos ao **mesmo escopo de código de aplicação**.

**Calibração crítica (não criar visão-de-túnel):** a detecção de pacote é **necessária mas é 1 de ~7 motivos** de rejeição. Mapa dos motivos e onde a detecção de pacote se encaixa:

| Motivo de rejeição | Revisor | Detecção de pacote ajuda? | Peso |
|---|---|---|---|
| Acurácia do detector não reportada + denominador ambíguo + app-vs-lib | 65A#1 | **SIM — alvo direto (Change A)** | alto |
| Cap de 300 s/sessão "não-representativo" | 65A#2, meta | Não | **alto** |
| Contagem de *unique misuses* a partir de violations é ambígua | 65A#3 | Não | **alto** |
| Comparação com CogniCrypt superficial (props, TP/FP, escopo) | 65A#4 | **Parcial — o escopo app-vs-lib** | alto |
| Correlação-vs-causação + GLM sem justificativa | 65A#5 | Não | médio |
| Novidade limitada / reposicionar como *empirical + infra paper* | 65B, 65C | Não | **alto** |
| Representatividade do subconjunto instrumentado (188/557; viés de ofuscação?) | 65B | **Parcial — a análise de ofuscação toca nisto** | alto |
| Severidade/exploitabilidade dos misuses; estudos de caso; reportar a devs | 65B | Não | médio |
| Só apps F-Droid (validade externa) | 65C, meta | Não | médio |
| RV4Android não público (verificabilidade) | 65A, 65B | Não | médio |

**Implicação de esforço:** a Change A resolve **integralmente** o 65A#1 e **parcialmente** o 65A#4 — bom retorno por ser barata. Mas **não** investir nela além do proporcional: os maiores drivers de rejeição (timeout 300s, contagem de unique-misuses, comparação CogniCrypt, reposicionamento de novidade) estão **fora** do escopo deste doc e precisam de tratamento próprio. A detecção de pacote é um *checkbox* a fechar de forma limpa, não o centro da revisão.

---

## 2. O que escrever no artigo (a defesa de 3 pernas)

Posicionar a detecção como **instrumento de medição validado**, sob **validade de construto** (Wohlin et al.) — **não** como seção/RQ própria. Três parágrafos curtos, distribuídos:

### Perna 1 — VALIDAÇÃO (no Método): medimos o instrumento

Texto-base (adaptar números reais da Change A):

> "O código-app de cada APK é inferido por uma heurística de prefixo de pacote (o pacote do manifest diverge do código real em ~27,5% dos APKs do dataset). Validamos a inferência contra um **censo rotulado manualmente de todos os 169 APKs** do experimento: a acurácia de correspondência exata é de **X% (Y/169)**, estratificada por método de detecção (Tabela N). As Z divergências são *library mis-picks* identificadas (§Ameaças)."

**Decisão metodológica importante:** como rotulamos a **população inteira** que reportamos (os APKs efetivamente avaliados; no dataset atual, os 169 do experimento pinado gh63), reportamos **acurácia exata, não estimada** — não há necessidade de intervalo de confiança (Wilson), dimensionamento de amostra nem Cohen's kappa inferencial. Dizer isso explicitamente desarma o revisor ("amostrou quantos? com que IC?"). Citar precedente (CryptoGuard CCS'19 para o prefixo do manifest; Soot/FlowDroid para o default app-vs-library) mostra que já excedemos a norma.

**Resolver o "557 ou 103?" (objeção #65A#1) de forma explícita:** o denominador da eval deve ser **o conjunto que o artigo de fato analisa** (não os 557 estaticamente-JCA, dos quais a maioria nunca foi instrumentada). Apresentar o **funil completo com números em cada estágio** (estaticamente-JCA → instrumentados → executados → conjunto da eval) e afirmar que o detector roda em **todo app analisado**. Isso elimina a ambiguidade de denominador que o revisor apontou.

### Perna 2 — ROBUSTEZ (na Avaliação): os resultados sobrevivem ao erro

Esta é a jogada de maior alavancagem (converte "ruidoso" em "defensável"). Um parágrafo + tabela com/sem:

> "Para verificar que os resultados de misuse não dependem da precisão do detector, re-executamos a contagem principal **excluindo os 4 APKs com mis-pick** (Tabela M, com/sem): as conclusões não mudam. No pior caso adversarial, ≤4/169 (**2,4%**) dos APKs poderiam estar mal-escopados. Além disso, sob ofuscação o mis-pick é **inerte**: as classes dex repackageadas (`I3.c`, `j2.a`) não casam com pacote nenhum — certo ou errado — de modo que um prefixo errado atribui ≈0 misuses (os componentes do manifest, que alimentam o detector, **não** são ofuscados, pois o R8 os preserva por serem referenciados)."

Correções obrigatórias da pesquisa: **escopar o "inerte" ao subconjunto ofuscado** (em apps não-ofuscados, ~25%, um prefixo errado *pode* casar código real — reportar esse caso também) e descartar colisão por prefixo degenerado.

### Perna 3 — POR QUE FERRAMENTAS SOTA NÃO SE APLICAM (em Trabalhos Relacionados/Ameaças): o argumento do problema inverso (B1), corrigido

Texto-base:

> "Detectores TPL state-of-the-art (LibScout [CCS'16], LibRadar [ICSE'16], LibD [ICSE'17], LibPecker [SANER'18], LibID [ISSTA'19]) emitem um **conjunto de bibliotecas detectadas** — com versão quando a técnica suporta — como produto; **nenhum** emite um identificador de pacote de primeira-parte do app. Recuperar o código-app a partir dessa saída é a operação inversa (tudo que *não* foi marcado como lib), i.e. uma heurística residual exatamente do tipo que empregamos. Isso é agravado pelo colapso de recall sob ofuscação: em benchmark independente, detectores de granularidade de pacote perdem **75–86% de recall** sob *package flattening* (Zhan et al., TSE'22), e sob R8 (usado por **41% dos apps**, LibHunter ASE'24) o F1 de nível-biblioteca cai abaixo de 5% para LibScout/LibID/LibPecker. Como o R8 renomeia e achata pacotes de app **e** de lib (docs R8; Wermke et al. ACSAC'18: renaming ProGuard em 64,5% de 1,7M apps), provenance por nome é não-confiável, e um mis-pick em classes ofuscadas não casa nada — falha de forma segura."

**3 correções obrigatórias antes de submeter (a pesquisa pegou furos):**
1. **Atribuir os números de P/R do LibScout/LibRadar/LibD às re-avaliações** (Zhan TSE'22, LibHunter ASE'24), **não** aos papers originais — os originais não auto-reportam recall.
2. **Escopar o "mis-pick inerte" ao subconjunto ofuscado** (não é uma propriedade de segurança universal; é inferência nossa de design).
3. **Distinguir explicitamente a linha "primary-module" (PiggyApp CODASPY'13, WuKong ISSTA'15):** essas *computam* o módulo primário direto, então um revisor pode dizer "já está resolvido". Resposta: o módulo deles é um artefato de *clustering* para detecção de clones, repousa nas mesmas heurísticas de manifest não-confiáveis, e não entrega um prefixo limpo de primeira-parte — logo também não resolve o nosso problema. **Não** citar LibD como precedente de "computa o pacote do app" — ele não emite isso.

Evidência local concreta para a Perna 3: o nosso spike do LibScout (`docs/20260617_investigacao_sota_substituir_detector.md`) — 0/9 das libs dos mis-picks no catálogo de 8.542 perfis; saída = pacote do manifest; 31 s/APK; trava em JDK ≥11. Substituição inviável, comprovada in-house.

---

## 3. Quanto da Change A / Change B realmente precisamos

### Change A (gh67 — avaliação formal): **MANTER, reenquadrada e levemente enxugada**

Change A é a **espinha** da defensabilidade — produz exatamente os números das Pernas 1 e 2. Mapeia 1:1 nos *must-haves* metodológicos. **Manter.** Ajustes:

- **Reenquadrar de "amostra com P/R/F1 + Wilson CI" para "censo → acurácia exata".** Rotulamos os 169 (população pinada), não uma amostra → mais forte e mais barato. Eliminar o aparato inferencial (Wilson CI, dimensionamento, Cohen's kappa) — substituir por **uma frase** justificando por que são N/A (medição de população, não amostra; rotulagem objetiva com evidência auditável).
- **Mitigação de anotador único** (achado da pesquisa: rotulagem por um só agente é a fraqueza): usar **LibScout/androguard como oráculo offline de cross-check** dos 42 mismatches manifest≠code (Opção A do spike), em vez de um segundo anotador humano. Barato, uma vez, offline. Declarar honestamente.
- **Manter:** CSV de ground-truth versionado, script de eval, acurácia exata, estratificação por `detection_method`, matriz app-vs-lib, taxa de lib-mis-pick, baseline pinado ao git hash do detector (INV-CORE-35).

### Acréscimo leve (paper-side, **não** é uma change nova): a re-execução de robustez

A Perna 2 (re-rodar contagem de misuse com/sem os 4 mis-picks + bound de pior caso) **não está** no escopo da Change A (que só avalia o detector). É a peça de maior alavancagem e **não exige** OpenSpec change — é um script de análise + um parágrafo + uma tabela, alimentados pela saída da Change A e pelo achado #2. Estimar como tarefa pequena dentro da redação do artigo.

### Change B (manifest-affinity — corrige o detector): **ADIAR; fora do caminho crítico do artigo**

Change B **não** aumenta a defensabilidade do experimento **atual**. Defensabilidade vem de **medir** (A) + **robustez** (paper), não de **corrigir**. Pior: corrigir o detector mudaria os picks e exigiria re-pinar o experimento gh63 (que está **congelado**) — fora de escopo pela restrição. Change B é uma melhoria de qualidade para **experimentos futuros**. Decisão: **manter no backlog, não bloquear o artigo.** Cortá-la do caminho crítico é o que mais economiza tempo.

### Cortes adicionais (o que NÃO fazer agora)

- **D5 (profundidade adaptativa, #68):** já adiado — manter adiado.
- **Catálogo de assinaturas dex reais (integração LibScout/LibD):** cortado — spike provou inviável/desnecessário; LibScout só como oráculo offline na eval, se quisermos.
- **Wilson CI / sample-size / Cohen's kappa:** cortados se censo + rotulagem objetiva; manter uma linha justificando o N/A.

---

## 4. Enquadramento como ameaça à validade (Wohlin et al.)

O detector é primariamente uma ameaça de **validade de construto** (a operacionalização "prefixo inferido" captura imperfeitamente o conceito "código próprio do app"), com facetas de **validade de conclusão** (confiabilidade da medida / erro aleatório) e **validade interna** (viés sistemático de instrumentação). Estrutura recomendada (seguindo Verdecchia et al. IST'23 / ESEM'24 — anti-boilerplate):

- **Um parágrafo dedicado em validade de construto** nomeando o detector como ameaça, declarando a mitigação (validação por censo da §Método + re-execução de robustez da §Avaliação) **e o risco residual** (mis-picks em apps não-ofuscados; ~2,4% dos APKs no pior caso).
- **Distinguir limitação de ameaça:** "não tratamos profundidade adaptativa (D5)" é uma *limitação* de escopo consciente; "o detector pode errar o prefixo em apps multi-módulo" é uma *ameaça*.
- **Tornar a ameaça visível no design, não só na seção de ameaças:** referenciar a re-execução de robustez a partir do parágrafo de construto — prova que a ameaça foi *projetada-para*, não colada depois (a crítica central de Verdecchia ESEM'24).

---

## 5. Checklist mínimo viável (o que satisfaz o revisor)

**OBRIGATÓRIO (risco de rejeição se faltar):**
1. Validação por **censo** do detector nos 169 APKs (Change A reenquadrada) → **acurácia exata**.
2. **Estratificação** por método de detecção + identificação dos 4 mis-picks + taxa de lib-mis-pick.
3. **Re-execução de robustez** da contagem principal com/sem os mis-picks (paper-side) — *maior alavancagem*.
4. **Parágrafo de validade de construto** (Wohlin) com mitigação + risco residual.
5. **Justificativa SOTA-não-aplica** (Perna 3, com as 3 correções) citando colapso TPL sob ofuscação.

**FORTEMENTE ESPERADO (revisor cuidadoso vai perguntar):**
6. **Bound de pior caso** (≤4/169 = 2,4%) + argumento "inerte sob ofuscação" (escopado ao subconjunto ofuscado).
7. **Cross-check com oráculo offline** (LibScout/androguard) nos 42 mismatches, mitigando anotador único.

**NICE-TO-HAVE (fortalece, não obrigatório):**
8. Liberar o ground-truth rotulado + código do detector como pacote de replicação.
9. Distinção explícita limitação-vs-ameaça (Verdecchia).

**NÃO FAZER (over-validation = atrai escrutínio de contribuição):** seção/RQ própria para o detector; novo benchmark; comparação de ferramentas; ground-truth a nível de versão.

---

## 6. Decisões propostas (para discutir)

| # | Decisão | Recomendação |
|---|---|---|
| (a) | O que escrever no artigo sobre detecção de pacote | Defesa de **3 pernas** (validação por censo / robustez com-sem / SOTA-não-aplica corrigida), enquadrada como **instrumento validado sob validade de construto** — 3 parágrafos, **sem** seção própria. |
| (b) | Quanto da Change A/B precisamos | **Change A: manter**, reenquadrada como censo (cortar Wilson CI/kappa, +oráculo offline). **Change B: adiar** — não defende o experimento congelado; backlog para experimentos futuros. **+ re-execução de robustez** leve, paper-side (não é change OpenSpec). |
| (c) | Enquadramento threat-to-validity | **Validade de construto** (Wohlin), com mitigação (censo + robustez) e risco residual (~2,4%), visível no design (Verdecchia). |

**Próximo passo (após aprovação):** (1) ajustar o escopo de `gh67-package-detector-eval` (reenquadrar para censo + oráculo offline; remover aparato inferencial) via skill OpenSpec apropriada; (2) registrar a re-execução de robustez como tarefa de redação do artigo; (3) rebaixar Change B para backlog explícito.

---

## Apêndice — fontes-chave verificadas (primárias)

- **Barra de rigor no subcampo:** CryptoGuard (CCS'19, §6.2 prefixo do manifest); CryptoLint (CCS'13); CrySL/CogniCrypt (ECOOP'18, §8.2); CRYLOGGER (S&P'21); FlowDroid (PLDI'14 + Soot `Scene.java`); Amandroid (TOPS'18); DroidSafe (NDSS'15); RV-Android (RV'15)/RVSec (TSE'23).
- **Metodologia:** Wohlin et al. *Experimentation in Software Engineering* (4 categorias de validade); Verdecchia et al. *Threats to Validity…* (IST'23 + ESEM'24, anti-boilerplate); convenções de robustez/sensibilidade (re-rodar com/sem casos suspeitos; bound de pior caso).
- **Problema inverso (B1):** Zhan et al. *Are We There Yet?* (ASE'20 / TSE'22 — recall TPL 9–49%; queda 75–86% sob flattening); LibHunter (ASE'24 — R8 em 41% dos apps, F1<5%); LibScan (USENIX Sec'23 — F1≈0,07–0,15 sob R8); Wermke et al. (ACSAC'18 — renaming em 64,5% de 1,7M apps); PiggyApp (CODASPY'13)/WuKong (ISSTA'15) — linha primary-module a distinguir.
- **Evidência local:** `docs/20260617_investigacao_sota_substituir_detector.md` (spike LibScout: 0/9 libs no catálogo, saída=manifest, 31s/APK, JDK8 — substituição inviável).
