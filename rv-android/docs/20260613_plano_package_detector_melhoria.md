# Plano — Melhoria do PackageDetector: afinidade com manifest, robustez a libs merged e avaliação formal

**Data**: 2026-06-13 · **Status**: 🟡 DRAFT para refinamento (nenhuma issue/change criada) · **Módulo**: rv-android-core (único) · **Track sugerido**: FF SDD (`/opsx:ff`)

**Insumos**:
- Auditoria empírica dos 169 APKs do exp-20260604 (`out/package_detector_audit/run_audit.py` + `results.json`)
- Pesquisa SOTA de detecção de pacote/lib em Android (`docs/20260613_pesquisa_package_detection_sota.md`)
- Memória de projeto `project_package_detector_improvement_plan`

**Princípio gh63-style**: vale para experimentos **futuros**. A cópia pinada no ase-journal **não** é re-sincronizada neste ciclo (proveniência do artigo — ver ase-journal `docs/20260611_plano_acao_correcoes.md` §9).

---

## 1. Problema (evidência empírica, 169 APKs)

Distribuição dos métodos de detecção: 99 same_package / 29 most_common / 17 common_prefix / 11 single_package / 8 similarity_match / 5 no_consensus. 42 mismatches manifest≠código. **Zero divergência** vs `apks_complete.csv` pinado (gh63 == experimento).

**4 lib-picks confirmados** (detector seleciona pacote de biblioteca):
- `de.readeckapp` → `net.openid.appauth` (AppAuth, merged via manifest) — `most_common` 2/3
- `com.github.wgh136.venera` e `org.codeberg.theoden8.webspace` → `com.pichillilorenzo.flutter_inappwebview_android` (plugin Flutter)
- `org.woheller69.whobird` → `org.tensorflow.lite` (app derivado de exemplo TFLite) — `single_package/high`
- (estreito, não-lib) `app.passwordstore.agrahn` → `app.passwordstore.ui` (ZXing destrói o prefixo comum)

**Achado contraintuitivo central**: a ofuscação **mascara** o erro em vez de amplificá-lo. Os components do manifest NÃO são ofuscados (R8 os preserva por serem referenciados); o input do detector é limpo. O estrago da ofuscação é **a jusante** — as classes dex repackageadas (`I3.c`, `j2.a`) nunca casam com pacote nenhum, certo ou errado. Por isso o impacto nos 27/527 app-code misuses do artigo é ≈ nulo (o pick errado fica inerte). Confirma o framing "piso" da 4.7 do plano do artigo.

**5 defeitos de código**:
1. `most_common` conta components de libs merged em pé de igualdade (limiar 60%).
2. `extract_package` não remove o nome da classe em pacotes rasos (`de.readeckapp.MainActivity` vira "pacote").
3. `common_prefix` é tudo-ou-nada (1 component de lib o destrói).
4. Truncagem fixa em `level=3` (mismatch espúrio `io.github.drumber.kitsune`→`io.github.drumber`; whobird aterrissa no namespace da lib).
5. Pick errado emitido com `confidence=high` (whobird).

---

## 2. O que a pesquisa SOTA muda (cruzamento)

A literatura (LibScout, LibRadar, LibD, LibPecker, LibID, survey Zhan ASE'20) é unânime: **detecção por nome/estrutura de pacote é frágil sob R8** — a categoria do nosso detector. A resposta SOTA é abandonar nomes e usar assinaturas estruturais resilientes (Merkle hashtrees, frequência de API Android, opcode-hashing, dependência de classe, CFG basic-blocks).

**Mas o nosso contexto difere e justifica um caminho pragmático**: a literatura assume tudo ofuscado; nós medimos que os **components do manifest sobrevivem ao R8**. Logo a heurística baseada em nome de component é viável como **primeira linha**, com fallback. Não precisamos virar um LibScout.

| Item original do draft | Veredito pós-pesquisa |
|---|---|
| Afinidade-com-manifest (tiers) | **MANTÉM** — justificativa: nomes do manifest sobrevivem ao R8 |
| Crescer `FRAMEWORK_PREFIXES` ad-hoc | **EVOLUI** → catálogo curado de perfis de libs merged (estilo LibScout) |
| Escopo dex (assinaturas/clustering) | **FORA** (D1) — LibD homogeny-union / LibRadar clustering são SOTA mas pesados → change futura |
| Validação (era diff-vs-baseline) | **VIRA CIDADÃO DE 1ª CLASSE** — ground truth manual + P/R/F1 |

**Caveats obrigatórios** (declarar em qualquer texto/limitação):
1. **Inversão**: a literatura cataloga LIBS; nós inferimos a APP (= complemento residual). Precisão da app depende do recall do catálogo de libs, e SOTA tem recall <50% (melhor F1 LibScout 65,2%) → subtração pura de libs é arriscada (reforça manter manifest-affinity).
2. **Sem solução publicada** para fork-domina-dex (problema 4) e app-É-namespace-da-lib (problema 3) → nossas heurísticas aí são **novas**, validadas como tal, com limitações declaradas.
3. Todas as técnicas estruturais degradam sob package flattening / class repackaging agressivo / control-flow obfuscation.
4. **NÃO citar** (refutados): PDG>PHS em confiabilidade; números exatos de colapso por repackaging do LibID.

---

## 3. Design proposto

### 3.1 Mudança central — prioridade de afinidade com o manifest (nova Priority 2.5)

Antes de `common_prefix`/`most_common`, particionar os candidatos em tiers de afinidade com o manifest:
- **Tier 1** — relação de prefixo (`candidate ⊑ manifest` ou `manifest ⊑ candidate`, por segmento)
- **Tier 2** — compartilham os 2 primeiros segmentos com o manifest
- **Tier 3** — estrangeiros (resto)

Se T1 ou T2 não-vazio: detectar **dentro do tier mais forte** (prefixo comum do tier; 1 candidato → ele mesmo). Tiers inferiores só entram quando os superiores estão vazios. **Forks legítimos (sagernet, securesms, newpipe) caem no fluxo atual** (sem candidato afim — comportamento preservado).

Efeito validado contra os casos reais:

| APK | Hoje | Com a mudança |
|---|---|---|
| de.readeckapp | `net.openid.appauth` ❌ | `de.readeckapp` ✓ (T1; exige fix do extract_package) |
| app.passwordstore.agrahn | `app.passwordstore.ui` (estreito) | `app.passwordstore` ✓ (T2, prefixo do cluster) |
| venera / webspace | plugin Flutter ❌ | `com.github.wgh136[.venera]` ✓ (T1) |
| org.fossify.notes | `org.fossify` (absorve commons) | `org.fossify.notes` (T1 > T2) — ver D2 |
| whobird | `org.tensorflow.lite` ❌ | inalterado (sem candidato afim) + flag `foreign_namespace` |
| forks (sagernet, securesms, …) | corretos | inalterados |

### 3.2 Mudanças de suporte

- **Fix `extract_package`**: strip do nome da classe (rsplit no último `.`) **antes** da truncagem por nível. Pré-requisito do Tier 1.
- **Profundidade adaptativa**: nível = `max(3, profundidade do manifest)`; 4 níveis para namespaces de hospedagem (`io.github`, `com.github`, `org.codeberg`, `io.gitlab`). Mata o mismatch espúrio do kitsune. (Parte mais invasiva — ver Risco; pode ser cortada como D5.)
- **Flag `foreign_namespace: bool`** no `PackageDetectionResult` + teto de confiança `medium` quando não há afinidade nem game engine. Consumidor único hoje é `App.code_package` (só loga) — mudança aditiva.
- **Catálogo de perfis de libs merged** (estilo LibScout, curado a partir do dataset): `net.openid.appauth.`, `com.journeyapps.`, `com.pichillilorenzo.`, `io.flutter.`, `dev.fluttercommunity.`, `com.mikepenz.`, `org.unifiedpush.`, `com.jakewharton.`. Substitui o crescimento ad-hoc de `FRAMEWORK_PREFIXES` por uma estrutura nomeada/documentada. (Ver D1 — escopo desta change ou separado.)
- **Documentar o caminho `"fallback"`** hoje não documentado na docstring do `detect_package`.

---

## 4. Decisões (resolvidas 2026-06-13)

- **D1 — ✅ Catálogo de libs merged: versão curada barata.** Lista nomeada de ~8 prefixos + razão, no código (substitui o crescimento ad-hoc de `FRAMEWORK_PREFIXES`). Assinaturas dex reais (LibScout/LibD) ficam para change futura.
- **D2 — ✅ fossify.commons vira lib (aceito).** Com T1, `org.fossify.notes` vence e `org.fossify.commons` vira lib no split (muda comportamento em 12 APKs fossify). Código do app = código daquele app; commons é first-party compartilhada.
- **D3 — ✅ whobird errado-com-flag (aceito).** Mantém `org.tensorflow.lite` mas marca `foreign_namespace` e rebaixa confiança; limitação documentada (a pesquisa confirma que não há solução publicada sem analisar o dex).
- **D4 — ✅ Nomes aceitos**: `manifest_affinity_tier1` / `manifest_affinity_tier2`.
- **D5 — ✅ Profundidade adaptativa ADIADA** (parte mais invasiva — toca todas as detecções; corte perde só o fix do kitsune). **Registrada em 4 locais para não esquecer**: (a) este plano; (b) memória de projeto; (c) **issue GitHub de backlog #68**; (d) **TODO no código** (`extract_package` em `package_detector.py`, referenciando #68) inserido como tarefa da Change B. Kitsune fica como limitação conhecida até lá.
- **D6 — ✅ Avaliação formal = CHANGE SEPARADA, especificada AGORA (antes do detector).** Ground truth rotulado **por mim (Claude)**, auditado pelo usuário numa amostra; reportar precision/recall/F1/accuracy + ameaças à validade. Estabelece a medição ANTES de mexer no detector (pré-registro: a métrica não é enviesada por conhecer a implementação). Satisfaz o A-1 do artigo. Ver §8.

---

## 5. Sequenciamento (duas changes)

A ordem é deliberada (pré-registro científico): **primeiro a change de validação** estabelece a medição e a baseline sobre o detector ATUAL (pinado); **depois a change do detector** melhora e mede o delta contra essa baseline.

- **Change A — Validação formal** (`gh67-package-detector-eval`, issue #67): ground truth + métricas + baseline do detector atual. Especificada AGORA, antes de implementar A ou B. Ver §8.
- **Change B — Melhoria do detector** (`gh<M>-package-detector-manifest-affinity`, issue a criar): tiers de afinidade + catálogo + flag. Implementada DEPOIS, medida contra a baseline da Change A. Profundidade adaptativa adiada para #68 (D5). Ver §6.

---

## 6. Change B — Tarefas (detector; FF SDD) — NÃO implementar ainda

1. Issue GitHub `#M` + `/opsx:ff` → `gh<M>-package-detector-manifest-affinity`
2. Fix `extract_package` (TDD)
3. Tiers de afinidade + nova prioridade na cascata (TDD)
4. **TODO no código** em `extract_package` registrando a profundidade adaptativa adiada (D5) + link p/ issue de backlog
5. Flag `foreign_namespace` + teto de confiança + documentar `"fallback"`
6. Catálogo curado de libs merged (~8 prefixos nomeados + razão)
7. Validação empírica 169 + diff enumerado (4 picks corrigidos, fossify×12→T1, **zero** mudança nos 99 same_package e forks; kitsune permanece mismatch — adiado D5)
8. Reportar métricas P/R/F1 da Change A antes/depois
9. `/rv-verify` → `/opsx:verify` → archive

Gate de aceite (Change B): TDD fixtures dos casos reais (readeckapp, passwordstore, venera, whobird, fossify.notes, dumdum, tofshare) RED→GREEN; diff enumerado nos 169; `/rv-verify`.

---

## 7. Riscos

- **Comportamento muda em ~16 APKs** (4 fixes + 12 fossify; kitsune adiado D5) — mitigado pelo gate de diff enumerado.
- **Avaliação formal** depende de rotulagem por Claude — concordância humana via auditoria de amostra (ver §8); ameaça à validade declarada.
- Cópia pinada no ase-journal diverge mais do upstream — política aceita (gh63), registrar no §9 do plano do artigo.
- **Inversão app-vs-lib** (recall <50% do catálogo): não construir o detector como subtração pura de libs — manter manifest-affinity como decisor primário.

---

## 8. Change A — Avaliação formal (especificação)

> Esta é a change a ser especificada AGORA via OpenSpec (`/opsx:ff` ou `/opsx:new`). Esboço de requisitos abaixo; os artefatos formais (proposal/specs/design/tasks) são gerados pelos skills, não à mão.

**Objetivo**: medir rigorosamente a acurácia do `package_detector` (atual e futuro) com métricas reportáveis no artigo (A-1), estabelecendo a baseline do detector pinado.

**Ground truth (rotulado por Claude, auditado pelo usuário)**:
- Universo: os 169 APKs do exp-20260604 (ou amostra estratificada por método de detecção: same_package / most_common / common_prefix / single_package / similarity / no_consensus).
- Para cada APK: rótulo do `code_package` correto, com **evidência explícita** (components do manifest, repo F-Droid/upstream, namespace dominante no dex via androguard). Rótulos persistidos em CSV versionado com a evidência.
- **Mitigação do anotador único** (Claude): (a) cada rótulo carrega evidência auditável; (b) o usuário audita/adjudica uma amostra (ex.: todos os 42 mismatches + amostra dos same_package); (c) discordâncias resolvidas e registradas. Declarar como ameaça à validade.

**Métricas**: precision/recall/F1/accuracy de `code_package == ground_truth` (exato e por-namespace), estratificadas por método de detecção; matriz de confusão app-vs-lib; taxa de lib-pick. Reportar sobre o detector ATUAL (baseline) e reservar para o futuro (pós-Change B).

**Artefatos**: script de avaliação reproduzível (`scripts/` ou módulo de eval), CSV de ground truth + evidência, relatório de métricas. Reusa o harness `out/package_detector_audit/`.

**Ameaças à validade**: anotador único (mitigado por auditoria); ground truth sem método sistemático (reconhecido pela própria literatura — LibD); ofuscação cega o dex como fonte de evidência (declarar quais APKs); detector pinado ≠ versão gh63 (registrar o hash).
