# Metodologia e loop autônomo de calibração LLM do APE-RV

**Data**: 2026-07-21
**Status**: Proposta de design (aguardando aprovação; nenhuma implementação nem OpenSpec change criada ainda)
**Escopo**: (i) o pipeline metodológico completo da calibração — cada passo com contrato explícito de entrada→saída, na ordem de dependência epistêmica; (ii) o desenho do loop autônomo que executa iterações de calibração de ponta a ponta; (iii) a divisão das changes entre os repos `rvsec/rv-android` e `ape`.
**Complementa**: `docs/20260721_plano_calibracao_llm.md` (rev. 2 — hipóteses, braços, estatística), `docs/20260721_sota_llm_gui_testing.md`.

---

## 1. Princípios metodológicos (por que esta ordem)

1. **Instrumento antes de medição**: nada roda antes de o aparato de medição (parser, auditoria de config, consolidação) estar validado — senão toda inferência posterior herda erro de instrumento (validade de constructo).
2. **Amostra antes de tratamento**: o subset é fixado e validado ANTES de qualquer braço rodar; selecionar/ajustar amostra depois de ver resultados é viés de seleção.
3. **Screening seleciona, confirmação conclui**: com MDE≈3,3pp em n=40 (plano §5-0.4) e efeitos reais de 0,15–2,8pp, p-valor não discrimina braços no screening. Fases A/B ranqueiam por efeito + proxies mecanísticos; só a Fase C (n=80–100, testes unilaterais pré-registrados, SESOI 2,0pp, desfecho GO/NO-GO/INCONCLUSIVE) tem valor confirmatório — e a confirmação definitiva é o experimento final no 181.
4. **Predição mecanística como guarda**: cada braço carrega uma predição quantitativa derivada do diagnóstico llm-gap (Δações/task × +46%/ação ⇒ Δcov esperado). Braço cujo resultado diverge muito da predição não é promovido sem explicação — resultado sem mecanismo entendido não sobrevive a replicação.
5. **Verificação independente por iteração**: todo dado que alimenta uma decisão passa por um verificador que NÃO produziu o dado (agente separado, checklist adversarial). Padrão já usado nas campanhas cmp*.
6. **Autonomia com portões humanos fixos**: o loop executa sozinho tudo que é reversível e config-only; qualquer mudança no repo `ape`, qualquer alteração de config de experimento em curso e a conclusão final são decisões humanas (regras permanentes do projeto).

## 2. Pipeline metodológico — passos e contratos entrada→saída

Cada passo declara: ENTRADA (artefatos que consome), SAÍDA (artefato que produz — sempre arquivo versionável), GATE (critério objetivo para avançar). A saída de cada passo é literalmente a entrada do seguinte.

### Etapa P1 — Validação do instrumento (offline)
- ENTRADA: `analyze_cmpv2_llm.py` (gramática d90c1f4), traces reais do cmpm_base + 1 trace novo da imagem 0.9.3 (smoke do cmp_llm, quando rodar).
- AÇÃO: selftest do parser nas duas gramáticas; tabela de mapeamento taxonomia antiga→nova (`no_match`(grounding)→`llm_tap`; `no_match` residual = boundary/degenerate/policy); checklist de auditoria `[APE-LLM-CONFIG]`/`[APE-LLM-CONFIG-ACK]`.
- SAÍDA: `calibracao/instrument_validation.md` + parser aprovado.
- GATE: selftest 100%; mapeamento revisado.

### Etapa P2 — Fase 0.4: análise de poder (feita)
- ENTRADA: `data/results/cmpma_consolidado/per_apk_paired.csv`.
- SAÍDA: MDEs por métrica e n (já no plano §5-0.4); tamanhos de Fase C (n=80–100) e SESOI (2,0pp) fixados.
- GATE: números registrados no plano ANTES de qualquer rodada (pré-registro). ✔ concluída 2026-07-21.

### Etapa P3 — Fase 0.1: subset
- ENTRADA: `per_apk_paired.csv` + traces cmpm_base (proxies LLM por APK) + dataset físico selected181.
- AÇÃO: estratificação (quantis de `ape__cov_mop` + fração mop_unique>0 ≈70% + proxy LLM llm_tap/chamadas) + otimização gulosa; verificação leave-10-out da estabilidade do ranking histórico entre os 5 braços do cmpma no subset.
- SAÍDA: `calibracao/subset40.txt` (+ `subset90.txt` para Fase C), `filters/` gerados, memo de representatividade (médias, KS, estratos).
- GATE: |Δmédia|≤1,0pp nas métricas-alvo; KS n.s.; `.apk`+`.apk.json` presentes para todos.

### Etapa P4 — Fase 0.2: decomposição causal dos no-matches
- ENTRADA: traces cmpm_base (~200 chamadas no_match/null) + tabela de mapeamento de P1.
- AÇÃO: classificar em parse/denormalização/grounding/política; medir distribuição de `nearest_dist` dos groundings.
- SAÍDA: `calibracao/nomatch_decomposition.md` — dimensiona H4 e fixa o valor-candidato da tolerância de snapping para a change do `ape`.
- GATE: ≥90% das chamadas classificadas sem ambiguidade.

### Etapa P5 — Preparação Python (rvsec-side, via OpenSpec — §4 change R1)
- ENTRADA: tabela de braços do plano §6.
- AÇÃO: variantes nomeadas `cal_*` (todas as chaves LLM explícitas), guard test `LLM_ARM_KEYS`, compose interleaved (SGLang compartilhado + 8 containers multi-tool com rotação de ordem de braços), smoke 11-braços com auditoria `[APE-LLM-CONFIG]` por braço, script Friedman/bootstrap multi-arm (reutilizando `rvsec-calibracao/scripts/stats_utils.py`).
- SAÍDA: variantes + testes verdes + composes + scripts.
- GATE: pytest do módulo verde; dry-run do gerador de tasks mostra 11 identidades distintas × 40 APKs × 2 reps.

### Etapa P6 — Decisão de modelo (H7, externa)
- ENTRADA: resultado do cmp_llm_20260721 (base×v2).
- SAÍDA: modelo fixado para a calibração.
- GATE: cmp_llm consolidado e verificado. (Fase 0 inteira roda em paralelo a isso.)

### Etapa P7 — Fase A (`cala`): smoke → run → consolidação → verificação → decisão
Conforme plano §6. A decisão produz o artefato-chave:
- SAÍDA: `calibracao/cala_decision.md` — ranking com CIs bootstrap, gates aplicados, predição-vs-observado por braço, 2–3 sobreviventes, e as hipóteses/predições da Fase B **pré-registradas**.

### Etapa P8 — Changes no `ape` (humano; ape-side — §4 changes J1–J4)
- ENTRADA: `nomatch_decomposition.md` (P4) + sobreviventes (P7).
- SAÍDA: commits no `ape` master + imagem nova auditada (jar por bytecode, padrão cmp_llm).
- GATE: aprovação humana; diff auditado; commits pushed antes do build.

### Etapa P9 — Fase B (`calb`): idem P7 na imagem nova
- SAÍDA: `calibracao/calb_decision.md` — config candidata final + pré-registro da Fase C.

### Etapa P10 — (opcional) micro-Optuna encaixotado
Conforme plano §12. SAÍDA: config candidata refinada (nunca conclusão). GATE de entrada: sobreviventes-B estáveis e budget aprovado.

### Etapa P11 — Fase C (`calc`): confirmação
- ENTRADA: candidata única + pré-registro de P9/P10 + `subset90.txt`.
- SAÍDA: `calibracao/calc_veredicto.md` — GO/NO-GO/INCONCLUSIVE com CIs, effect sizes e partição throughput×qualidade.
- GATE: veredicto humano-ratificado → config do experimento final (181).

## 3. Loop autônomo de calibração (desenho)

O loop é a automação das etapas P7/P9 (e P10): dado um manifesto de braços, ele executa smoke→run→monitor→consolida→verifica→analisa→decide e itera. Uma "iteração" = uma rodada completa de experimento multi-arm.

### 3.1 Máquina de estados por iteração

```
CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE
     ↑                                                                              |
     └─────────────────────── próxima iteração (ou terminal) ←──────────────────────┘
```

1. **CONFIG-GEN**: entrada = decisão da iteração anterior (ou plano §6 na 1ª). Gera `iterN/manifest.json`: por braço, nome da variante, dict completo de chaves (todas explícitas), string `[APE-LLM-CONFIG]` esperada, identidades previstas. Gera composes/filters a partir do manifesto (nunca à mão).
2. **PRE-FLIGHT (verificador independente)**: agente separado audita manifesto×composes×`get_variants()`: chaves completas, 11+ identidades distintas, digest da imagem = jar pretendido (timestamp vs `git log` do `ape`), SGLang compose correto. GATE: PASS.
3. **SMOKE**: 4 APKs × braços extremos, 90s, 1 rep. Gates: COMPLETED, cov>0, `[APE-LLM-CONFIG]` de cada braço == manifesto (comparação campo a campo), `server_model` correto, 0 VerifyError. Falha → aborta iteração, reporta, NÃO ajusta config sozinho.
4. **RUN+MONITOR**: compose up; monitor com cadência fixa; auto-restart só de containers OOM exit 137 (autorização permanente existente); auto-resume de tasks ERROR (identidade dedup). Critério de conclusão = logcats não-vazios por identidade (lição exp20260706), não contagem de COMPLETED. Nunca alterar config em curso.
5. **CONSOLIDATE**: dos logcats (anti-gh58), dedup por identidade; produz `iterN/per_apk_paired.csv` + `iterN/tel_proxies.csv`.
6. **VERIFY (verificador independente)**: agente separado re-deriva as contagens dos logcats crus por caminho independente; audita config-ack por task vs manifesto (100% das tasks LLM); checa colisões de identidade, completude pareada (APKs presentes em todos os braços), sanidade de contenção (time_ms por braço vs mediana). Veredicto: dados admissíveis / quarentena (métrica ou braço excluído com justificativa escrita).
7. **ANALYZE**: gates do plano §6 na ordem pré-declarada (proxy → ranking bootstrap → checagem mecanística → determinismo); gera `iterN/analysis.md` com predição-vs-observado.
8. **DECIDE**: regras declarativas por fase (screening: promover top-k que passam gates; micro-Optuna: ask/tell TPE com budget box; confirmação: aplicar critérios pré-registrados e PARAR). Toda decisão escreve `iterN/decision.md` com justificativa e a config da próxima iteração. Estados terminais: vencedor-confirmado / budget-esgotado / NO-GO-com-poder (reportar teto honesto).

### 3.2 Journal e proveniência

Diário append-only `calibracao/journal.jsonl`: um registro por transição de estado (timestamp, iteração, estado, artefato produzido, hash). Qualquer resultado citado em doc/paper rastreia até logcat cru via journal.

### 3.3 Portões humanos (fixos, não negociáveis)

- **G1**: aprovação do plano + budget de iterações antes do loop iniciar.
- **G2**: qualquer mudança no repo `ape` (P8) — o loop no máximo PROPÕE um diff/spec; nunca commita lá.
- **G3**: lançamento de cada experimento (compose up da rodada completa) — até ordem em contrário, o loop prepara e pede go; se o usuário conceder autorização permanente de lançamento, G3 colapsa no G1.
- **G4**: ratificação do veredicto final (P11) e da config do experimento 181.

### 3.4 O que o loop NUNCA faz

Gerenciar emulador manualmente; alterar config de experimento em curso; tocar em `backup/`; usar `@override` para distinguir braços; declarar vitória por p-valor de screening; usar números do cmpm_v2; modificar o repo `ape`.

## 4. Divisão de changes entre repos (propostas — a criar via workflow OpenSpec de cada repo)

### rvsec/rv-android (via `opsx:new`, issue gh a abrir)

- **R1 — `gh<N>-cal-llm-arms`**: variantes nomeadas `cal_*` em `aperv-tool` (todas as chaves LLM explícitas), guard `LLM_ARM_KEYS` (fecha o gap do INV-APV-14 para chaves LLM: `_LLM_FLAGS` hoje omite `llm_percentage`/`llm_prompt_variant`), mappings novos (`llm_max_tokens`→`ape.llmMaxTokens`, `llm_snap_tolerance_px`→propriedade nova do J1 — 1 linha cada em `APERV_PROPERTY_MAPPING`).
- **R2 — `gh<N>-cal-experiment-scaffold`**: template `experimento-cal/` (gerador manifesto→compose com SGLang compartilhado + rotação de ordem de braços; smoke multi-braço com auditoria `[APE-LLM-CONFIG]`; monitor/resume; consolidação N-braços + script bootstrap/Friedman reutilizando `rvsec-calibracao/scripts/stats_utils.py`; journal).
- **R3 (opcional, pós-Fase B) — `gh<N>-cal-optuna-micro`**: driver ask/tell local encaixotado (SQLite; coordinator/worker de `rvsec-calibracao` em modo local), só se P10 for aprovado.

R1 e R2 são pré-requisitos da Fase A (etapa P5). Fase 0 (P1–P4) é análise offline e não exige change — os artefatos vão para `docs/`/`calibracao/`.

### ape (workflow próprio daquele repo; humano — G2)

- **J1 — formato + snapping configurável** (H4): endurecer instruções/tool-schema; `ape.llmSnapTolerancePx` e bandas de boundary como properties (valores default = atuais: max(50,min(w,h)/2), 5%/94%); preservar `llm_tap`.
- **J2 — prompt MOP-targeted por proxy** (H5): variante nova injetando widgets `[DM]/[M]` com `visitedCount==0`.
- **J3 — memória de platô** (H6): tentativas de escape falhas no platô atual; opcional cache de escape p≈0,8.
- **J4 — superfície de calibração**: `ape.llmMaxTokens`; time_ms nos caminhos de falha + `[APE-LLM-ERROR]` na falha de screenshot (fecha o viés de medição); opcional `ape.llmStagnationThreshold` desacoplado do restart (pré-requisito do H8/gatilho MOP-plateau).

Racional do bundle: um único rebuild na Fase B converte todos os knobs futuros em properties — depois disso o loop autônomo alcança todo o espaço de busca sem tocar em código Java (limite estrutural da autonomia: o loop só varia properties).

## 5. Ordem de execução consolidada

```
P1 instrumento ──┐
P2 poder (✔) ────┤ (offline, paralelo entre si e ao cmp_llm)
P3 subset ───────┤
P4 no-match ─────┘
P5 change R1+R2 (rvsec) ──────► P7 Fase A (cala)  [G3]
P6 cmp_llm → modelo (H7) ─────►      │
                                     ▼
                        P8 changes J1–J4 (ape) [G2]
                                     ▼
                              P9 Fase B (calb) [G3]
                                     ▼
                        P10 micro-Optuna (opcional)
                                     ▼
                              P11 Fase C (calc) [G4]
                                     ▼
                    experimento final 181 (fora deste plano)
```
