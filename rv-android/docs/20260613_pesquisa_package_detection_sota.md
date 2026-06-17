# Pesquisa — Detecção de pacote de aplicação vs biblioteca em Android (SOTA)

**Data**: 2026-06-13 · **Origem**: deep-research workflow (run wf_c297f403-4e7; 5 ângulos, 15 fontes, 67 claims extraídos, 25 verificados adversarialmente, 23 confirmados / 2 refutados, 7 achados sintetizados). Contexto: melhorar o `package_detector.py` do rv-android-core (ver `project_package_detector_improvement_plan` na memória).

## Resumo executivo

A literatura estado-da-arte de detecção de TPL (Third-Party Library) em Android — **LibScout** (Derr, CCS'16), **LibRadar** (Ma, ICSE'16), **LibD** (Li, ICSE'17 + TSE'18), **LibPecker** (Yang, SANER'18), **LibID** (Zhang, ISSTA'19), survey **Zhan et al.** (ASE'20) — converge num ponto que atinge diretamente o nosso detector: **detecção baseada em nome/estrutura de pacote (whitelists, applicationId, prefixos comuns) é frágil e quebra sob ofuscação R8/ProGuard**. ProGuard renomeia `com.google`→`a.c`; >50% das TPLs Android estão ofuscadas. A solução robusta abandona nomes como feature primária e usa **assinaturas estruturais resilientes à ofuscação**.

## Achados confirmados (vote 3-0, alta confiança salvo nota)

**F1 — Nomes de pacote são frágeis (causa-raiz dos nossos problemas 2 e 4).** Whitelist/applicationId/prefixo quebram sob R8. Fontes: Zhan ASE'20, Derr CCS'16 (`com.google`→`a.c`), Ma ICSE'16, arXiv 2509.04091 (2025).

**F2 — Cinco mecanismos estruturais resilientes (substituem nomes):**
- **LibScout**: hashtree Merkle de profundidade fixa 3 (pacotes/classes/métodos), derivada só da hierarquia de classes, independente do código → resiliente a renaming/control-flow/string encryption/API hiding.
- **LibRadar**: frequência de chamadas distintas à **API Android** por pacote — não-ofuscável (APIs do framework não são renomeadas).
- **LibD**: hash de sequências de **opcodes em basic blocks**, ignorando operandos → derrota renaming de classe/método.
- **LibPecker**: assinaturas de **dependência de classe** (herança, field-in, argumento de método) + fuzzy matching adaptativo.
- **LibID**: assinaturas de **basic block do CFG** invariantes a renaming/shrinking/control-flow + features de classe (access flag, superclasse, interfaces SDK, descritor de método).

**F3 — Manifest-merger / libs multi-pacote (nosso problema 1):** NÃO assumir que uma lib é uma subárvore contígua única (premissa do LibRadar que falha). LibD: "homogeny package union" p/ libs multi-pacote (5.141 = 8,4% das libs). LibRadar: clustering multi-nível — une features de classes/subpacotes, agrupa, seleciona o maior cluster como raiz da lib.

**F4 — Perfis de SDK originais > clustering sobre apps:** construir perfis a partir dos binários SDK originais (LibScout) reduz FP quando libs partilham raiz (`com.google` em Play Services/Gson/Guice) e permite inferir versão exata. LibScout lida com dead-code elimination via score de similaridade vs SDKs baseline (não match exato).

**F5 — Alta precisão, recall baixo (<50%):** empiricamente (Zhan ASE'20, dataset não-ofuscado, 5 tools): recall 9,44% (ORLIS) a 49,03% (LibScout); melhor precisão LibRadar 97,90%; melhor F1 LibScout 65,20%. ⚠️ LibPecker auto-reporta recall 91%/precisão 98,1% mas sob ground-truth baseado em nome de pacote (favorece recall) — ler com cautela (passou só 2-1).

**F6 — Validação rigorosa (metodologia):** (a) LibD — 1.000 apps aleatórios, inspeção manual, label de pacote como TPL se nome é domínio legal (ou subdomínio confirmado via motor de busca) → 2.613 libs; (b) dataset 2025 (arXiv 2509.04091) — anotações ao nível de versão p/ deps remotas E locais, 6.000+ apps, 10 tools. Métricas: precision/recall/F1. Ambos admitem "não há método sistemático de ground truth" como ameaça à validade.

**F7 — Taxonomia de referência (4 passos):** preprocessing/decompile → library instance construction → feature extraction → identification. Na construção de instância, além de package name (PN): Package Hierarchy Structure (PHS, árvore — LibID/LibPecker/LibRadar), homogeny graph (LibD), Package Dependency Graph (PDG — LibSift/AdDetect).

## Refutados (NÃO usar)

- Que tools PDG (LibSift/AdDetect) são "mais confiáveis" que PHS (vote 1-2 — sem base empírica).
- Números específicos de colapso LibScout/LibPecker sob class repackaging (0,7%/9,6% vs LibID 98,4%) do paper LibID (vote 1-2 — tendência qualitativa OK, números exatos não verificados).

## Caveats críticos para o nosso contexto

1. **Inversão do problema**: a literatura cataloga LIBS; nós queremos o pacote da APP. A ponte é analítica: **app = complemento residual após isolar as libs**. Logo a precisão na detecção do app depende do **recall do catálogo de libs** — e recall <50% torna a pura subtração de libs arriscada.
2. **Limite universal**: todas as técnicas resilientes resistem a renaming/shrinking, mas **degradam sob package flattening, class repackaging agressivo e ofuscação de control-flow**. Nenhuma é universalmente robusta.
3. **Vantagem específica nossa (não capturada na literatura)**: empiricamente, os **components do manifest NÃO são ofuscados** (R8 os preserva por serem referenciados pelo manifest). O input do nosso detector é limpo — diferente do problema TPL geral onde tudo está ofuscado. Isso **justifica** manter heurística baseada em nome de component como primeira linha, com fallback estrutural.
4. arXiv 2509.04091 é preprint (não peer-reviewed); ">50% TPLs ofuscadas" é citação de 2ª mão (Zhan ref [51]).

## Perguntas em aberto (sem resposta na literatura — nossas hard cases)

- **Fork vs lib quando o fork domina o DEX** (nosso problema 4: Session→securesms): nenhuma heurística publicada de "dominância no DEX"/afinidade com applicationId + assinaturas estruturais. Requer ground truth manual.
- **App derivado de exemplo/template** (problema 3: TensorFlow examples) onde o código da app **É genuinamente** o namespace da lib: nenhuma fonte aborda; qual sinal desempata (entry-points do manifest, Activities instanciadas em runtime, mapping file R8)?
- **Mapping files R8/ProGuard**: custo/benefício de exigi-los (quando disponíveis) vs técnicas puramente estruturais — não coberto.
- **Detecção nativa de Androguard/Soot/FlowDroid**: parte (A) ficou sem fonte primária dedicada a essas ferramentas.

## Fontes primárias

- LibScout: https://trust.cispa.saarland/publication/derr-16-ccs/derr-16-ccs.pdf · https://github.com/reddr/LibScout
- LibRadar: https://yaoguopku.github.io/papers/Ma-ICSE-16.pdf
- LibD: https://faculty.ist.psu.edu/wu/papers/LibD.pdf · https://faculty.ist.psu.edu/wu/papers/LibD-TSE-18.pdf
- LibPecker: https://yangzhemin.github.io/papers/libpecker-saner2018.pdf
- LibID: https://www.cl.cam.ac.uk/~arb33/papers/ZhangBeresfordKollmann-LibID-ISSTA2019.pdf
- Survey/benchmark: https://lilicoding.github.io/papers/zhan2020automated.pdf
- Dataset 2025 (preprint): https://arxiv.org/abs/2509.04091
