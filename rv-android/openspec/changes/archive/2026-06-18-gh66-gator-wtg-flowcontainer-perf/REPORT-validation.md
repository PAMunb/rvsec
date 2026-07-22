# gh66 — Relatório de validação empírica (sweep WTG, 169 APKs JCA)

**Data:** 2026-06-18
**Corpus:** 169 APKs JCA do `experimento-20260604` (symlinks em `out/sweep_20260604_apks`).
**Baseline:** `out/sweep_20260604_wtg_spark` (169 JSONs, 72 com `transitions>0`).
**Candidato gh66:** `out/sweep_gh66_wtg_spark`.
**Config (idêntica à baseline):** `--cg-algorithm spark --cg-delegation true`, WTG ligada (**sem `--skip-wtg`**), **sem `--succ-depth`**. JAR gh66 (Java 25, build 2026-06-17, 3 símbolos novos confirmados).

Este relatório registra os resultados de §4.1 (invariância/diff-zero) e §4.2 (recuperação), o **achado central** sobre o teto de recuperação da WTG, e as ressalvas metodológicas. Documenta também um ajuste no gate de invariância e um caveat da mecânica de resume do sweep.

---

## 1. Execução em estágios

| Estágio | Subset | workers/timeout/jvm | Resultado |
|---------|--------|---------------------|-----------|
| **A** (bulk) | 169 | 6→8w† / 1800s / 12g | 164 `complete`, 5 `failed` (4 `failed_timeout_no_json`, 1 `failed_no_json`=OOM `com.infomaniak.meet_28`); **69 `tr>0`** |
| **B** (timeouts) | `pending_timeout` | 6w / 3600s / 14g | re-rodou só os **4** `failed_timeout_no_json` (ver §4); todos → `complete`; **+3 `tr>0` → 72**; 168 JSONs |
| **C** (OOM) | `pending_oom` (1) | 2w / 60g | **pendente** (reachability OOM; gh66 não afeta — só completa os 169) |

† Stage A rodou com 8 workers; B com 6 (a pedido).

Estado atual: **168 JSONs, 72 `tr>0`**, faltando apenas `com.infomaniak.meet_28` (Stage C) e a recuperação de `com.opennotes_8` (ver §4/§5).

---

## 2. §4.1 — Gate de invariância (diff-zero): **PASS nos invariantes**

`scripts/wtg_sweep_invariance.py` (baseline × gh66, 168 comparados):

- **`invariant-field diffs: 0`** — `package`/`mainActivity`/`reachability` idênticos em todos; `windows`/`components` idênticos por identidade estrutural (ver §3).
- **`transitions violations: 1`** — apenas `com.opennotes_8` (`−5`), um caso de fronteira de timeout (ver §4), a recuperar via re-run a 3600s.
- Nos **72** APKs `tr>0` da baseline que completam em ambos: **diff-zero exato** (INV-ANA-39 vale).

**Conclusão §4.1:** o gh66 é **semântica-preservante** — não perturba reachability/windows/components e produz conjunto de transições idêntico onde a WTG completa. (PASS pleno depende só de recuperar o `opennotes`.)

---

## 3. Ajuste no gate de invariância (windows/components por identidade estrutural)

**Problema descoberto:** ao comparar dois runs **independentes** (não o mesmo arquivo), 5 APKs deram FAIL por divergência de **conteúdo** de `windows`/`components` — com **contagens idênticas**. Diagnóstico:

1. O gh66 só toca `buildFlowThroughContainer` (→ transitions); windows/components vêm da análise de GUI, anterior e independente. **4 dos 5 FAILs tinham transitions idênticas/recuperadas** ⇒ a divergência não pode ter origem no gh66.
2. Os **68 APKs `tr>0`-em-ambos (limpos) passaram 100%**; os 5 FAILs eram **todos** de fronteira de timeout (lado `tr=0`/recuperação).
3. Divergência **bidirecional** (às vezes o gh66 tinha *mais* conteúdo, com *menos* tempo) — assinatura de **não-determinância do GATOR/SPARK** na resolução de widgets obfuscados (R8) e intent-filters, não de truncamento nem de regressão.

**Causa raiz:** `windows[].widgets[]` e `components[].intentFilters[]` **não são bit-reproduzíveis entre execuções independentes** do GATOR (a validação anterior do comparador foi baseline-vs-baseline/mutação, que nunca expõe isso).

**Ajuste:** o gate agora compara `windows`/`components` pela **identidade estrutural estável**, não pelo conteúdo aninhado:
- `windows` → conjunto de `name` (telas de GUI descobertas);
- `components` → conjunto de `(categoria, className)` (activities/receivers/services/providers do manifesto).

O conteúdo aninhado (widgets, intent-filters, `reachesTarget`/`targetMethods`) é tolerado como ruído conhecido. `reachability`/`package`/`mainActivity` seguem **estritos** (conteúdo completo); `transitions` segue **diff-zero**. Validação do gate ajustado: baseline×baseline → **PASS** (169/169, sem falso-positivo). É um **threat-to-validity** a registrar no paper (a invariância de GUI é estrutural, não byte-a-byte).

---

## 4. §4.2 — Recuperação: **teto de WTG é timeout-bound; gh66 não o eleva**

| Métrica | Valor |
|---------|-------|
| baseline `tr>0` | 72 / 169 |
| gh66 `tr>0` (atual) | **72** (→ 73 ao recuperar `opennotes`) |
| candidatos a recuperação (baseline `tr==0`) | 96 (comparados) |
| **recuperados pelo gh66** (bl 0 → gh `>0`) | **1** — `org.fossify.musicplayer_14` (0 → 54 arestas) |
| perdidos a 1800s (bl `>0` → gh 0) | 1 — `com.opennotes_8` (recupera a 3600s) |

**Achado central (resposta a "foi por timeout?"):** os **96** APKs `complete`-com-`tr0` **TODOS bateram no timeout** — `analysis_seconds` = 1800s (mediana 1800, mín 1800), e o único re-rodado a 3600s (`com.patch4code.logline_4`) **também** estourou (3600s, `tr0`). **Zero** completaram rápido. Ou seja: **não são apps "sem transições" — são timeouts de WTG**. A WTG simplesmente não termina de construir nesses APKs.

**Interpretação:** o gh66 remove **um** gargalo (`buildFlowThroughContainer`, o laço quadrático `O(W×R)`), mas a construção da WTG nesses APKs é dominada por **outro** gargalo, deixado fora do escopo de propósito (**Fix 2 adiado** — a chamada `graphUtil.reachableNodes()` por alloc-node, `FlowgraphRebuilder.java:319`, marcada como Non-Goal). Removido o primeiro, o segundo passa a mandar e os APKs continuam estourando o tempo. O §4.3 (jstack) deve confirmar que o hotspot **saiu** de `getReadContainerField`/`SootMethodRefImpl.resolve` (prova de que a otimização funciona mecanicamente), mas isso não basta para a WTG completar nos timeouts.

**Recuperação líquida do gh66 ≈ +1** (`fossify`), chegando ao mesmo patamar da baseline (72→73). **Não** é "recupera os 97 timeouts".

---

## 5. Ressalvas metodológicas

### 5a. Mecânica de resume mascara timeouts de WTG como `complete`
`classify_status` (`scripts/static_analysis_sweep.py:357`) marca `complete` sempre que a **seção** `transitions` existe — **mesmo vazia (`[]`)**. Um timeout de WTG grava `"transitions": []` ⇒ status `complete` ⇒ o resume **nunca re-tenta** (`complete: nothing to gain`, `DEFAULT_RETRY_STATUSES` exclui `complete`).

Consequência: o Stage B mirado nos 99 `pending_timeout` re-rodou **só os 4** `failed_timeout_no_json` (sem JSON); os **95** `complete`-`tr0` (incluindo `com.opennotes_8`) foram **pulados**. O `opennotes` (baseline `tr=5`, necessário para o gate) **não recupera sozinho** — exige re-run forçado/isolado a 3600s.

Não é defeito do gh66 nem dos dados — é da mecânica do script (confunde "WTG completou com 0 transições" e "WTG estourou o tempo e gravou 0").

### 5b. Os 96 timeouts não foram propriamente re-testados a 3600s no gh66
Por 5a, no gh66 os 96 só foram testados a **1800s** (Stage A). O único a 3600s (`logline`) também estourou. A **baseline** os testou a 3600s (Stage B/C) e recuperou só ~4 (68→72). Logo a evidência (baseline + `logline`) indica que **dobrar o timeout rende ~nada** — mas, em rigor, o gh66 não foi re-testado a 3600s no conjunto dos 96. Decisão em aberto:
- **(A)** Aceitar a conclusão (corroborada pela baseline + `logline`): WTG é timeout-bound por outro gargalo; recupera-se só o `opennotes` (fecha o gate) + Stage C, e fecha.
- **(B)** Rigor pleno: forçar o re-run dos 96 a 3600s (contornando 5a) para medir a recuperação real do gh66 a tempo estendido — custa horas para rendimento provavelmente ~nulo.

---

## 6. Valor do gh66 (avaliação honesta)

A contribuição **não é** "recupera os timeouts da WTG". É:
1. **Otimização semântica-preservante** — diff-zero exato nos 72 APKs `tr>0` (INV-ANA-39 provado).
2. **Remove o hotspot documentado** de `buildFlowThroughContainer` (§4.3 jstack como prova).
3. **Diagnóstico empírico:** o próximo gargalo da WTG é o Fix 2 (`reachableNodes`, linha 319) — informa a decisão de seguir (ou não) com ele (design D5).

---

## 7. Itens em aberto (antes do §5 — fechamento)

- [ ] Recuperar `com.opennotes_8` (re-run isolado a 3600s + cópia) → gate PASS pleno (73 `tr>0`).
- [ ] Stage C — `com.infomaniak.meet_28` (OOM, 2w/60g) → 169/169 com JSON.
- [ ] §4.3 jstack re-probe (`ch.famoser.mensa`) — confirmar hotspot fora de `getReadContainerField`.
- [ ] §4.4 NFR04 — num APK que ainda estoura, conferir reachability+windows+components populados com `transitions[]` vazio.
- [ ] Decisão (A) vs (B) do §5b.
- [ ] §5 (commit/docs/review) — **não iniciado** (aguarda revisão do usuário).
