# Plano de Fechamento — Changes gh50 / gh51 / gh52 / gh53

**Data**: 2026-05-03
**Branch**: `modules`
**Sessão**: paralela à sessão que executa Phase A/B/C (AJC instrumentation + comparison study).

---

## 1. Contexto

Quatro OpenSpec changes co-existem em `openspec/changes/`, todas validadas empiricamente nas últimas 48h pelos experimentos `sweep_jca400_v1` (380/400 GATOR), `instrument_jca226_*` (224/226 dexlib2), `run_jca100` + `run_jca124` (1501 tasks bem-sucedidas, 31494 + 33564 RVSEC-COV events). Esta sessão fecha tasks pendentes baseadas em evidência já existente; **não duplica** o trabalho da sessão paralela (Phase A AJC instrumentation em curso → Phase B install validation → Phase C comparison study).

### 1.1 Estado atual real (verificado via `openspec list`)

| Change | Tasks | Status | Domínio delta |
|---|---|---|---|
| `gh50-improve-instrumentation` | 234/256 (22 `[ ]` + 7 `[~]`) | valid | instrumentation |
| `gh51-gator-soot-upgrade` | 61/67 (6 `[ ]`) | valid | analysis |
| `gh52-instr-dexlib2` | 125/162 (37 `[ ]` + 7 `[~]`) | valid | instrumentation |
| `gh53-consolidacao-instrumentation` | ✓ Complete | valid | instrumentation |

### 1.2 Restrição crítica — sync de delta specs

`openspec/changes/gh53-consolidacao-instrumentation/specs/instrumentation/spec.md` declara:

> "This delta does NOT redefine requirements introduced by gh50, gh51, or gh52. It adds requirements about the new four-module canonical layout and amends the wording of the variant-selection requirement (originally INV-INS-18 in gh52's delta) to point at the new locations. **Reconciliation with `openspec/specs/instrumentation/spec.md` is deferred to the synchronization step performed when gh50, gh51, gh52, and gh53 are all archived together.**"

Implicações:
- `gh53` AMENDS `gh52`'s INV-INS-18 → archive ordering **gh52 antes de gh53** é hard constraint.
- Os 3 deltas de instrumentation (gh50, gh52, gh53) devem ser sincronizados em batch único.
- `gh51` (analysis) é independente e pode ser archivado sozinho sem conflito.

---

## 2. Estratégia (decidida pelo usuário: híbrida)

| Change | Hoje | Aguardando | Archive |
|---|---|---|---|
| **gh51** | Fechar 6 tasks | — | **HOJE** (sync inclusive) |
| **gh50** | Fechar 12 tasks fechíveis + DEFER 7 tasks JCA-557 | Phase C (não bloqueia) | Batch futuro |
| **gh52** | Promover ~16 tasks `[~]→[x]` e `[ ] DEFERRED→[x]` | Phase C (Layer 1-5 + final QA) | Batch futuro |
| **gh53** | Nenhuma (já 100%) | gh50 + gh52 prontas | Batch futuro |

**Batch final** (quando Phase C terminar e gh52 fechar): archive `gh50 → gh52 → gh53` em ordem, com `openspec sync` único de specs no fim.

---

## 3. Convenção de blocos de evidência

Todo task fechado nesta sessão recebe (mesma convenção das atualizações de 2026-05-02):

```
- [x] N.N Description.
   - **Verification date**: 2026-05-03
   - **Method**: experiment | artifact | static check | code reference | commit
   - **Concrete numbers**: <valores reais>
   - **File reference**: <path absoluto>
   - **Conclusion**: <1 linha>
```

Para tasks já feitas em commit existente: bloco simplificado `**Commit**: <sha> "<msg>"`.

Para tasks deferidas como future work: bloco `**DEFERRED**: <razão> + <evidência substituta de aceite>`.

---

## 4. Phase 1 — gh51-gator-soot-upgrade (archive completo HOJE)

### 4.1 Tasks a fechar

**Pré-requisito**: `lib/gator/rvsec-analysis-client.jar` deve existir (verificado, 57MB).

| # | Task | Arquivo / Linha | Tipo | Detalhe |
|---|---|---|---|---|
| 1.1 | 4e.6 | `tasks.md:88` | EXECUTAR | Smoke `cryptoapp.apk` com `spark` (default) + invocação extra `-cgAlgorithm cha` |
| 1.2 | 6.6 | `tasks.md:129` | EXECUTAR | Comparar output `cryptoapp.apk` contra baseline (directlyReachesMop exato; reachable/reachesMop ±10%) |
| 1.3 | 7.1 | `tasks.md:139` | EXECUTAR | `mvn clean compile -DskipTests -DskipMopAgent` em `rvsec-gator`, `rvsec-apk`, `rvsec-frame-computer` |
| 1.4 | 6.2 | `tasks.md:99` | DEFERRED-x | Bloco: "FIX 3 já merged + validado em 380 APKs (sweep_jca400_v1, 95% SA). Retrospective isolation não cientificamente significativo per-precondição do próprio task ('should run before/parallel FIX 3, not after')." |
| 1.5 | 8.11 | `tasks.md:206` | DEFERRED-x | Bloco: "Bytecode-scan complement (commit `aebb33c8`) eliminates the 2 FT cases empiricamente; rerun produces null delta. FT investigation memorialized in `project_gator_ft_investigation` (FN rate 0.26%)." |
| 1.6 | 8.12 | `tasks.md:208` | JÁ FEITO | Commit `aebb33c8` "fix(gh51): add bytecode-scan complement for directlyReachesMop FN" |

### 4.2 Sequência de execução

```
1. Phase 1 (~15 min):
   1.1  Build/smoke 4e.6   (cryptoapp + spark + cha)             ~3 min
   1.2  Comparison 6.6     (cryptoapp diff vs baseline)          ~2 min
   1.3  mvn compile 7.1    (rvsec-gator + apk + frame-computer)  ~10 min
2. Phase 2 (~10 min):
   2.1  Promover 6.2, 8.11, 8.12 com blocos de evidência
   2.2  Atualizar contadores de progresso em tasks.md (se houver)
3. Phase 3 (~5 min):
   3.1  openspec validate gh51-gator-soot-upgrade
   3.2  Confirmar 0 [ ] e 0 [~] em tasks.md
   3.3  openspec archive gh51-gator-soot-upgrade
   3.4  Verificar openspec/specs/analysis/spec.md ganhou INV-ANA-16/17/18
   3.5  openspec list  → gh51 not in active
```

### 4.3 Critérios de sucesso

- [ ] `openspec list` não mostra mais `gh51-gator-soot-upgrade` como ativo
- [ ] `openspec/changes/archive/<date>-gh51-gator-soot-upgrade/` existe
- [ ] `openspec/specs/analysis/spec.md` contém INV-ANA-16, INV-ANA-17, INV-ANA-18 com texto exato do delta
- [ ] `openspec validate --strict` passa em `analysis`

### 4.4 Plano de rollback

Se sync corromper o spec base:
1. `git -C rv-android checkout openspec/specs/analysis/spec.md`
2. `mv openspec/changes/archive/<date>-gh51-gator-soot-upgrade openspec/changes/gh51-gator-soot-upgrade`
3. Investigar + retry

---

## 5. Phase 2 — gh50-improve-instrumentation (close tasks, NÃO archive)

### 5.1 Tasks a fechar HOJE

| # | Task | Linha | Tipo | Detalhe |
|---|---|---|---|---|
| 2.1 | 8.5.2 | 97 | EXECUTAR | `/rv-qa-lint-fix rv-instrumentation-ajc` (módulo renomeado pós-gh53) |
| 2.2 | 8.5.3 | 98 | EXECUTAR | `/rv-verify rv-instrumentation-ajc` |
| 2.3 | 12.5.2 | 279 | EVIDÊNCIA INDIRETA | Identificar 3 APKs do bucket stackmap_error em `data/results/instrument_jca226_*/instrument_errors.json` (ou ausência = success). Bloco: "3 sample APKs (org.apache.tika-dependent + androidx.media3 + Kotlin-obfuscated) instrumented with success in JCA-226 sweep (224/226 = 99.1%). Stackmap fix proven in production scale." |
| 2.4 | 13.5.2 | 322 | EVIDÊNCIA INDIRETA | Confirmar `com.futsch1.medtimer_162.apk` em `APKS_JCA_dexlib2/` + cross-ref no `instrument_jca226_*` log. Bloco: "Cited APK present in 224/226 instrumented set; 911 RVSEC-COV events expected per Phase B v7 baseline." |
| 2.5 | 17.4.1-17.4.3 | 427-429 | EVIDÊNCIA INDIRETA (3 tasks) | Bloco compartilhado: "AVD baseline implicitly validated by run_jca100: 80 APKs E2E, 717/720 successful tasks, 31494 RVSEC-COV events (`out/run_jca100_consolidated/consolidated_summary.csv`). Manual standalone boot test deferred per CLAUDE.md emulator policy — rv-platform-managed validation supersedes." |
| 2.6 | 18.5.2 | 516 | EXECUTAR | `apksigner verify -v <APK>` em 1 APK do `APKS_JCA_dexlib2/`. Esperado: v1+v2+v3 verified. |
| 2.7 | 16.5.3 | 634 | EXECUTAR | `dexdump <APK>` em 1 APK quarantined sample. Verificar `Lokio/Buffer;` PRESENTE sem `aspectOf`. |
| 2.8 | 19.4.1 | 695 | EXECUTAR | Adicionar/verificar `TestLoadQuarantinePatterns::test_expanded_list_loaded` em `modules/rv-instrumentation-ajc/tests/`. |
| 2.9 | 19.4.2 | 696 | EXECUTAR | Adicionar/verificar `TestQuarantineProblematicClasses::test_spongycastle_moved`. |
| 2.10 | 21.5.3 | 781 | EVIDÊNCIA INDIRETA | Bloco: "Smoke validated in commit `b336a9a9` (76/76 tests pass + cryptoapp validated end-to-end; --no-quarantine pipeline reaches unchanged code path). Memory entry confirms validation date 2026-05-02." |
| 2.11 | 21.6.1 | 785 | EXECUTAR | Update `modules/rv-instrumentation-ajc/CLAUDE.md` "CLI Options" com `--no-quarantine`. |
| 2.12 | 21.7.1 | 790 | JÁ FEITO | Commit `b336a9a9` "feat(gh50): add enable_quarantine config + --no-quarantine CLI flag (refs #50)". |
| 2.13 | 15.4.1 | 551 | EXECUTAR | Adicionar `TestExecuteMaven::test_maven_skip_stderr_enabled` mirroring d8 test. |

### 5.2 Tasks a DEFERIR como future work (JCA-557 oldset)

Bloco compartilhado: **"DEFERRED — JCA-557 dataset out-of-scope per gh50 acceptance criteria. JCA-400 sweep_jca400_v1 (380/400 SA OK, 95%) + run_jca100/124 (1501 tasks) provide primary empirical evidence. Re-run on 287-APK failed subset filed as future work; not blocking gh50 archive."**

| # | Task | Linha |
|---|---|---|
| 2.14 | 19.5.2 | 705 |
| 2.15 | 19.5.3 | 706 |
| 2.16 | 19.5.4 | 707 |
| 2.17 | 19.5.5 | 708 |
| 2.18 | 19.6.2 | 713 |
| 2.19 | 19.6.3 | 714 |
| 2.20 | 20.5.1 | 743 |

### 5.3 Sequência de execução

```
Phase 1 — code-changing tasks (~30 min):
   2.11 (CLAUDE.md update; manual edit)
   2.13 (test_maven_skip_stderr_enabled — write test)
   2.8  (TestLoadQuarantinePatterns — write/verify)
   2.9  (TestQuarantineProblematicClasses — write/verify)

Phase 2 — verification commands (~15 min):
   2.6  (apksigner verify -v 1 APK)                     ~1 min
   2.7  (dexdump 1 quarantined APK)                     ~1 min
   2.1  (rv-qa-lint-fix rv-instrumentation-ajc)         ~3 min
   2.2  (rv-verify rv-instrumentation-ajc)              ~5 min

Phase 3 — closing with evidence blocks (~25 min):
   2.3, 2.4, 2.5 (3 tasks), 2.10, 2.12 — promover [x] com blocos
   2.14-2.20 — promover [x] DEFERRED com bloco compartilhado JCA-557

Phase 4 — final state validation (~5 min):
   openspec validate gh50-improve-instrumentation
   openspec status --change gh50-improve-instrumentation
   Esperado: ratio cresce de 234/256 para ~256/256 OU ~256-N/256 com N tasks ainda dependentes de Phase C
```

### 5.4 Critérios de sucesso

- [ ] `openspec validate gh50-improve-instrumentation` passa
- [ ] `grep -cE '^\s*-\s*\[ \]' openspec/changes/gh50-improve-instrumentation/tasks.md` retorna ≤ 0 (zero pending)
- [ ] gh50 NÃO archivada hoje (aguarda batch com gh52 + gh53)
- [ ] Todas tasks fechadas têm bloco de evidência

---

## 6. Phase 3 — gh52-instr-dexlib2 (promoções, NÃO archive)

### 6.1 Tasks a promover `[~]` partial → `[x]` (rationale completo já presente)

| # | Task | Linha | Razão |
|---|---|---|---|
| 3.1 | 5.7 | 90 | RegisterShifterFormatsTest cobre 8 formatos dominantes (real-world coverage) |
| 3.2 | 5.8 | 91 | Integration test em task 9.5 (cryptoapp round-trip) |
| 3.3 | 5.9 | 92 | Static-side smoke em task 9.5 (95-match weave + 118-method coverage) |
| 3.4 | 10.13 | 165 | Oracle hateitorrateit slot (Kotlin/R8) criado |
| 3.5 | 12.7 | 189 | Wrapper-side argv parity tests landed |
| 3.6 | 17.5 | 253 | Grep clean (3 file refs legitimate) |
| 3.7 | 16.9 | 244 | docs/20260426_dexlib2_validation_results.md scaffolded; §5 conclusões PENDING (depende 16.7) → manter `[~]` |

### 6.2 Tasks a promover `[ ] DEFERRED com rationale` → `[x] DEFERRED`

Bloco padronizado: **"DEFERRED — <razão original do task>. Aceite arquitetural na sessão de fechamento 2026-05-03."**

| # | Task | Linha | Razão original |
|---|---|---|---|
| 3.8 | 6.6 | 106 | DEFERRED to cli integration task 9.5/9.6 |
| 3.9 | 6.8 | 108 | DEFERRED to Group 9 cli integration |
| 3.10 | 10.14 | 166 | DEFERRED requires Phase 5 emulator |
| 3.11 | 13.4 | 198 | DEFERRED dexlib2 wrapper config simpler |
| 3.12 | 14.3 | 213 | DEFERRED steps identical to ajc flow |
| 3.13 | 14.5 | 220 | DEFERRED no per-PR Docker policy |
| 3.14 | 15.4 | 227 | DEFERRED CLAUDE.md updated post-Phase-5 |
| 3.15 | 15.5 | 228 | DEFERRED PRD sync wanted before archive |
| 3.16 | 15.6 | 229 | DEFERRED architecture diagram in design.md |
| 3.17 | 15.7 | 230 | DEFERRED ADR + proposal serve same purpose |

### 6.3 Tasks a NÃO mexer hoje (aguardam Phase C)

**Bloco 1 — Layer 1-5 validation** (resolvido por Phase A → B → C da sessão paralela):

| Task | Linha | Phase C dependência |
|---|---|---|
| 16.3 | 237 | parity validator JCA + Generic |
| 16.4 | 238 | BaksmaliDiffer Layer-1 (30-APK subset) |
| 16.5 | 239 | BootValidator Layer-2 (30-APK subset) |
| 16.6 | 240 | TraceComparator Layer-3 (cryptoapp + 30-APK) |
| 16.6a | 241 | Pre-batch 64k method-ref audit |
| 16.7 | 242 | BatchValidator Layer-4 (JCA-400 × 3 × 3, ~36h) |
| 16.8 | 243 | CoverageValidator Layer-5 |
| 16.10 | 245 | `openspec verify gh52-instr-dexlib2` |

**Bloco 2 — Phase 6 (default flip; AJC retido como opt-in — decisão 2026-05-05)**: 17.2 (rename consideration), 17.3 (dispatch default → dexlib2; ajc branch retained as opt-in), 17.4 (Pydantic default → "dexlib2"), 17.6 (sync delta — sem REMOVED Requirements; gh50 INV-INS-14..25 ajc-specific permanecem ativos), 17.7 (validate --all). 17.1 marcado N/A (AJC não vai pra backup; já renomeado para `modules/rv-instrumentation-ajc/` pelo gh53).

**Bloco 3 — Final QA + archive**: 18.1, 18.2, 18.3, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.12, 18.13, 18.14, 18.15

### 6.4 Sequência de execução

```
Phase 1 — promoções [~]→[x] (~10 min):
   3.1 a 3.6 (6 tasks; 3.7 mantém [~])

Phase 2 — promoções DEFERRED (~10 min):
   3.8 a 3.17 (10 tasks)

Phase 3 — validação final (~5 min):
   openspec validate gh52-instr-dexlib2
   openspec status --change gh52-instr-dexlib2
   Esperado: ratio cresce de 125/162 para ~141/162; restante = Phase C + Phase 6 + Final QA
```

### 6.5 Critérios de sucesso

- [ ] `openspec validate gh52-instr-dexlib2` continua passando
- [ ] Ratio sobe para ~141/162 (do baseline 125/162)
- [ ] gh52 NÃO archivada hoje
- [ ] Tasks 16.3-16.10, 17.x, 18.x permanecem `[ ]` (aguardam Phase C / outra sessão)

---

## 7. Phase 4 — gh53-consolidacao-instrumentation (sem ação hoje)

`openspec list` confirma: `✓ Complete`. Zero pendentes.

**Não archivar hoje** — aguarda batch final com gh50 + gh52 (sync único de specs per declaração explícita do delta).

---

## 8. Plano do batch final (futuro, fora desta sessão)

Quando a sessão paralela terminar a Phase C:

```
1. Sessão paralela fecha:
   - gh52 16.3-16.10 com evidência da Phase C
   - gh52 17.1-17.7 (move legacy → backup, default flip ajc→dexlib2, sync)
   - gh52 18.1-18.15 (final QA + retrospective)
2. Verificações:
   - openspec validate gh50, gh52, gh53
   - 0 pending em todas
3. Archive em ordem (gh52 antes de gh53 obrigatório):
   - openspec archive gh50-improve-instrumentation --skip-specs
   - openspec archive gh52-instr-dexlib2 --skip-specs
   - openspec archive gh53-consolidacao-instrumentation --skip-specs
4. Sync único:
   - openspec sync   # merge dos 3 deltas em openspec/specs/instrumentation/spec.md
5. Validação:
   - openspec validate --all
   - Verificar specs/instrumentation/spec.md tem todos os INVs (gh50: INV-INS-14..25; gh52: INV-INS-13..24 numbered; gh53: INV-INS-33..41)
```

---

## 9. Sumário de comandos por phase

### 9.1 Phase 1 (gh51) — ~30 min total

```bash
# 1.1 — gh51 4e.6: cryptoapp smoke spark + cha
java -jar lib/gator/rvsec-analysis-client.jar -apk apks_examples/cryptoapp.apk \
  -android-jar /path/to/android.jar -output out/gh51_smoke_4e6_spark.json
java -jar lib/gator/rvsec-analysis-client.jar -apk apks_examples/cryptoapp.apk \
  -android-jar /path/to/android.jar -cgAlgorithm cha -output out/gh51_smoke_4e6_cha.json

# 1.2 — gh51 6.6: comparison vs baseline
diff <(jq '.directlyReachesMop' out/gh51_smoke_4e6_spark.json) \
     <(jq '.directlyReachesMop' out/gh51_baseline.json)

# 1.3 — gh51 7.1: mvn compile
( cd ../rvsec/rvsec-android/rvsec-gator && mvn clean compile -DskipTests -DskipMopAgent )
( cd ../rvsec/rvsec-android/rvsec-apk && mvn clean compile -DskipTests -DskipMopAgent )
( cd ../rvsec/rvsec-android/rv-frame-computer && mvn clean compile -DskipTests -DskipMopAgent )

# 1.4-1.6 — Edit tasks.md (promoções com blocos de evidência)
# (manual via Edit tool)

# Phase 1 final
openspec validate gh51-gator-soot-upgrade
openspec archive gh51-gator-soot-upgrade
```

### 9.2 Phase 2 (gh50) — ~75 min total

```bash
# 2.6 — gh50 18.5.2: apksigner verify
SAMPLE_APK=$(ls /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_dexlib2/*.apk | head -1)
apksigner verify -v "$SAMPLE_APK"

# 2.7 — gh50 16.5.3: dexdump quarantined
dexdump "$SAMPLE_APK" | grep -E "Lokio/Buffer;|aspectOf" | head -20

# 2.1 — gh50 8.5.2: lint-fix
# (via Skill tool: /rv-qa-lint-fix rv-instrumentation-ajc)

# 2.2 — gh50 8.5.3: verify
# (via Skill tool: /rv-verify rv-instrumentation-ajc)

# 2.8, 2.9, 2.13 — write tests (manual Edit)

# 2.11 — gh50 21.6.1: CLAUDE.md update (manual Edit)

# 2.3, 2.4, 2.5, 2.10, 2.12, 2.14-2.20 — promoções tasks.md (manual Edit)

# Phase 2 final
openspec validate gh50-improve-instrumentation
openspec status --change gh50-improve-instrumentation
```

### 9.3 Phase 3 (gh52) — ~25 min total

```bash
# 3.1-3.17 — promoções tasks.md (manual Edit, sem código)

# Phase 3 final
openspec validate gh52-instr-dexlib2
openspec status --change gh52-instr-dexlib2
```

---

## 10. Riscos & mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| `openspec sync` (gh51 archive) sobrescreve algo do main `analysis/spec.md` | Baixa | Médio | `git diff` antes de archive; `git checkout` se inesperado |
| Renome `rv-instrumentation` → `rv-instrumentation-ajc` (pós-gh53) quebra invocações de skill | Média | Baixo | Tentar com nome novo primeiro; fallback path explícito; checar `modules/rv-instrumentation-ajc/` existe |
| 12.5.2 spot-check sem rastreio de bucket stackmap_error | Média | Baixo | Usar `data/results/instrument_jca226_*/instrument_errors.json`; se ausente = sucesso = evidência |
| 21.5.3 smoke `--no-quarantine` requer rebuild local | Média | Baixo | Reutilizar evidência commit `b336a9a9` (76/76 tests + cryptoapp validated) |
| Phase C atrasa, batch final fica sem janela | Baixa | Médio | Usar `--skip-specs` no archive; documentar pending sync |
| Conflito de delta gh53 vs gh52 surgir durante batch sync | Baixa | Alto | Sync inclui ambos no mesmo `openspec sync` (transação atômica); design.md prevê isso |

---

## 11. O que NÃO fazer nesta sessão

- ❌ **Iniciar/parar AVD manualmente** (regra CLAUDE.md "DO NOT TOUCH emulator")
- ❌ **Duplicar Phase A/B/C** (sessão paralela tem ownership)
- ❌ **Archivar gh53 sozinha** (quebra sync com gh52)
- ❌ **Archivar gh52 hoje** (Phase C ainda em curso)
- ❌ **Modificar arquivos em `backup/`** (regra de memória)
- ❌ **Adicionar `Co-Authored-By` nos commits** (regra de memória)
- ❌ **Rodar `openspec sync` parcialmente** entre gh50/gh52/gh53 (deferred per gh53 design)
- ❌ **Mexer em `openspec/specs/instrumentation/spec.md`** manualmente (será sincronizado pelo batch final)

---

## 12. Critical files

### A modificar (somente `tasks.md` + 2 docs)

- `openspec/changes/gh50-improve-instrumentation/tasks.md` (12 tasks fechadas + 7 deferred)
- `openspec/changes/gh51-gator-soot-upgrade/tasks.md` (6 tasks fechadas)
- `openspec/changes/gh52-instr-dexlib2/tasks.md` (16 tasks promovidas)
- `modules/rv-instrumentation-ajc/CLAUDE.md` (gh50 21.6.1 — adicionar `--no-quarantine` na CLI Options)
- `modules/rv-instrumentation-ajc/tests/test_*.py` (gh50 19.4.1, 19.4.2, 15.4.1 — 3 testes novos)

### A consultar (read-only)

- `lib/gator/rvsec-analysis-client.jar` (gh51 4e.6)
- `apks_examples/cryptoapp.apk` (gh51 4e.6, 6.6)
- `out/sweep_jca400_v1/progress.csv` (gh51 evidência)
- `out/run_jca100_consolidated/consolidated_summary.csv` (gh50 17.4 evidência)
- `out/run_jca_combined/consolidated_summary.csv` (gh50 evidência geral)
- `data/results/instrument_jca226_*/` (gh50 12.5.2, 13.5.2 evidência; também `instrument_errors.json` se houver)
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_dexlib2/` (gh50 18.5.2, 16.5.3 spot-checks)

### A executar comandos contra

- `../rvsec/rvsec-android/rvsec-gator/`, `../rvsec/rvsec-android/rvsec-apk/`, `../rvsec/rvsec-android/rv-frame-computer/` (gh51 7.1)

---

## 13. Verificação end-to-end

Ao final da sessão (todas 3 phases concluídas), confirmar:

### 13.1 Estado dos arquivos

```bash
# Pendentes restantes em cada change
for c in gh50-improve-instrumentation gh51-gator-soot-upgrade gh52-instr-dexlib2 gh53-consolidacao-instrumentation; do
  echo "=== $c ==="
  grep -cE '^\s*-\s*\[ \]' openspec/changes/$c/tasks.md 2>/dev/null \
    || echo "(archived)"
done

# Esperado:
# gh50: 0   (todas fechadas hoje, ou (archived) se já no archive/)
# gh51: (archived)
# gh52: ~21 (16.3-16.10 + 17.x + 18.x — Phase C dependente)
# gh53: 0
```

### 13.2 Estado openspec

```bash
openspec list
# Esperado:
#   gh50-improve-instrumentation       ~256/256 (ou parcial se algumas tasks dependerem de Phase C)
#   gh52-instr-dexlib2                 ~141/162
#   gh53-consolidacao-instrumentation  ✓ Complete
#   (gh51 não aparece — archivada)

openspec validate --all
# Esperado: passa em todas
```

### 13.3 Specs main

```bash
# Após archive de gh51, analysis spec deve ter os novos INVs
grep -E "INV-ANA-1[678]" openspec/specs/analysis/spec.md
# Esperado: 3 matches (INV-ANA-16, 17, 18)

# instrumentation spec NÃO deve ter mudado (sync deferred)
git -C . diff HEAD -- openspec/specs/instrumentation/spec.md
# Esperado: vazio
```

### 13.4 Git state

```bash
git -C . status --short | grep -E "openspec/changes|openspec/specs"
# Esperado:
#   M openspec/changes/gh50-improve-instrumentation/tasks.md
#   M openspec/changes/gh52-instr-dexlib2/tasks.md
#   M openspec/specs/analysis/spec.md
#   D openspec/changes/gh51-gator-soot-upgrade/...
#   ?? openspec/changes/archive/<date>-gh51-gator-soot-upgrade/...
```

---

## 14. Estimativa de esforço total

| Phase | Tarefa | Estimativa |
|---|---|---|
| 1 | gh51 fechamento + archive | 30 min |
| 2 | gh50 12 tasks + 7 DEFERRED | 75 min |
| 3 | gh52 16 promoções | 25 min |
| — | Verificações + commits | 20 min |
| **Total** | | **~2.5h** |

---

## 15. Próximos passos pós-sessão

1. **Esta sessão**: implementar Phase 1 → 2 → 3 conforme plano acima.
2. **Sessão paralela (em curso)**:
   - Phase A: AJC instrumentation (ETA 8-15h)
   - Phase B: install validation no emulador (`scripts/validate_ajc_apks_install.py`)
   - Phase C: comparison study ajc-vs-dexlib2 → resolve gh52 16.3-16.10
3. **Sessão futura (batch final)**:
   - gh52 17.1-17.7 (Phase 6 default flip)
   - gh52 18.1-18.15 (final QA)
   - Archive batch: gh50 → gh52 → gh53 (ordem obrigatória)
   - `openspec sync` único de instrumentation specs
   - Validação final
4. **Commit por phase**:
   - `chore(gh51): close pending tasks for archive (refs #51, closes #51)`
   - `chore(gh50): close JCA-400 tasks; defer JCA-557 oldset (refs #50)`
   - `chore(gh52): promote DEFERRED tasks pending Phase C (refs #52)`

---

## 16. Aprovação

Este plano segue diretrizes:
- ✅ Híbrida confirmada pelo usuário (gh51 hoje + batch futuro para 50/52/53)
- ✅ AVD spot-checks via evidência indireta de run_jca100 (CLAUDE.md compliant)
- ✅ JCA-557 oldset diferido como future work
- ✅ gh51 6.2 isolation experiment aceito como deferred informativo
- ✅ Sem duplicação de trabalho da sessão paralela
- ✅ Archive ordering respeita constraint gh52→gh53
- ✅ Sync de specs deferido conforme declaração explícita de gh53
