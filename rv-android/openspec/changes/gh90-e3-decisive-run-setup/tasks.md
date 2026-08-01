<!-- Group order is the deadline-driven priority order: implemented and tested by 2026-07-31 09:00
     (hard max 2026-08-01 09:00), feeding the decisive run. Groups 1-5 are independent of the
     sister-repo jar and can be completed and green before it exists; Groups 6 and 7 need the jar.
     Group 7 (RQ-C1 power probe) gates the decision to launch the decisive run and must be declared
     in the pre-registration before it executes. This change touches ~5 files in one module — no subagent orchestration needed. -->

## 1. Decisive-run arms (A1 + B2)

- [x] 1.1 Add the module-level `_MOP_OFF_OVERRIDES` constant in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: the four MOP weights and `mop_frontier_weight` at `0`, `activity_trigger_enabled=False`. Document inline WHY the document stays present (INV-APV-29: an unset path aborts the run at `StatefulAgent.java:216-223`; an omitted `mop_data` also kills `WtgPass:29`/`FrontierPass:35`)
- [x] 1.2 Declare the three decisive-run arms in `get_variants()` on `_FRONTIER_SUBSTRATE`: `mop_on_llm_off` (reference), `mop_off_llm_off` (control, `**_MOP_OFF_OVERRIDES`), `mop_on_llm_70` (LLM arm). Arm 3 carries the `cal_a1` LLM block verbatim — `llm_percentage=0.7`, `v13`, temperature 0, `top_p` 0.6, `top_k` 50, both triggers on (design D8)
- [x] 1.3 Confirm `mop_activity_source_components=True` is explicit in all three arms (B2). Note that this is an explicitness requirement, not a behaviour change: `_FRONTIER_SUBSTRATE` already carries `True` (`tool.py:322`), so all three inherit it — B2 only alters arms that inherit the jar's `false` default
- [x] 1.4 Add unit tests: control arm keeps `mop_data`; all five MOP weight keys are `0`; `activity_trigger_enabled` is `False`; `frontier_boost_weight` unchanged (INV-APV-30)
- [x] 1.5 Add the single-factor guard tests: reference↔control diff is exactly the MOP keys; reference↔LLM-arm diff contains only LLM keys
- [x] 1.6 Extend the `LLM_ARM_KEYS` guard scope so it covers `mop_on_llm_70`. The constant is `tool.py:209-234`; the `cal_`-prefix scoping that must be widened lives in the test (`modules/aperv-tool/tests/test_aperv_tool.py:678`), so without this the arm escapes the guard and task 1.7 passes vacuously (INV-APV-26 — defined in the not-yet-archived `gh88-cal-llm-control`; see the proposal's dependency note)
- [x] 1.7 Verify the pre-existing guards still pass with the new arms (`ARM_DEFINING_KEYS` mapping/explicitness, INV-APV-13/14; `LLM_ARM_KEYS` under its extended scope, INV-APV-26)
- [x] 1.8 Run `/rv-test-run aperv-tool`

## 2. Offline substrate enrichment (N6)

- [x] 2.1 Implement `_enrich_listener_reach(document) -> int` in `tool.py`: build the signature→`reachesTarget` index from `reachability[].methods[]`, then walk `windows[].widgets[].listeners[]` writing `handlerReachesTarget` and `handlerDirectlyReachesTarget`. Direct means any-depth reach of THIS widget's handler — never copy the producer's 0-hop `directlyReachesTarget` (INV-APV-32)
- [x] 2.2 Wire it into `_compact_static_analysis_json` between the `transitions` dedup and the minified write; keep the existing `except (json.JSONDecodeError, OSError, MemoryError)` fallback intact and make an enrichment failure degrade to an un-enriched push, not to a source-file push (INV-APV-31)
- [x] 2.3 Update the `_compact_static_analysis_json` docstring (`tool.py:805`): "two lossless operations" becomes three, the third additive. Current-state only, no migration history (P4). Note the same two→three move is an amendment of the capability-level **INV-APV-21**, stated in this change's delta `## Invariants` — the MODIFIED requirement alone does not displace it
- [x] 2.4 Add unit tests: transitive handler flagged direct; unreachable handler false on both; unknown signature false on both; app with zero widgets is a valid no-op; only the two keys are added; malformed `reachability` degrades to un-enriched push; source file byte-identical afterwards (INV-APV-20/31)
- [x] 2.5 Measure the flagged fraction and record it. Expect sparsity, not saturation: the census over the 40-APK subset gives 0.4% (160 of 45,200 listeners) with only 7 apps carrying any flaggable listener, so the axis is reported as sparse (design Risks)
- [x] 2.6 Run `/rv-test-run aperv-tool`

## 3. Per-run provenance and the B3 gate (N4 + B3)

- [x] 3.1 Implement `_capture_llm_provenance(llm_url, jar_path) -> dict` — live `GET {llm_url}/v1/models` plus the jar file sha256; returns `llm_backend`, `llm_model`, `llm_sampling`, `jar_sha256`, `capture_status`. Failures are encoded in `capture_status`, never back-filled from config (INV-APV-33)
- [x] 3.2 Call it once per run in the execute path for arms that declare LLM keys, and write the fields into the task output
- [x] 3.3 Add the B3 declaration to the LLM arm: `llm_snap_tolerance_px=150` paired with `expected_jar_git_sha` **and** `expected_jar_sha256`, and extend `_snap_tolerance_offenders` to require all three together. Both declaration keys are Python-only and MUST stay out of `APERV_PROPERTY_MAPPING` — the jar has no property to receive them. Do NOT attempt to read a capability stamp from the jar and do NOT parse an `[APE-BUILD]` banner: neither exists, `gh14-build-provenance-stamp` was archived without implementation, and the verifiable half is the installed jar's sha256 (design D4)
- [x] 3.4 Add the guard test enforcing the pairing in both directions: tolerance 150 without a declared sha fails; a declared sha without the raised tolerance also fails (INV-APV-34)
- [x] 3.5 Add unit tests: provenance from a live query; failure encoded not inferred; no query for non-LLM arms
- [x] 3.6 Run `/rv-test-run aperv-tool`

## 4. Offline clock↔logcat join (A9)

- [x] 4.1 Create `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`: read a run's recorded trace clock and `RVSEC:` logcat lines, emit per-run correlation rows. Offline and read-only — no device, no emulator (INV-APV-35)
- [x] 4.2 Add the CLI entry point with `SystemExit(2)` on a missing or unreadable run directory, naming the path
- [x] 4.3 Add the validation gate test against the recorded iter0 corpus: exactly 9,586 `RVSEC:` lines across 605 runs and 32 APKs — all three totals must match
- [x] 4.4 Add unit tests: a run with zero violations yields a valid empty-violation row set (not an omission); every artifact read is byte-identical afterwards
- [x] 4.5 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`
- [x] 4.6 Run `/rv-test-run aperv-tool`
- [x] 4.7 Report what the join says about the "reaching a MOP screen fires the monitor" premise — this is the evidence base for the deferred N5 decision

## 5. Coverage-dump parser and capture grace window (O3 + `+45 s`)

Added 2026-07-31 after adversarial verification (`docs/20260731_verificacao_analise_percepcao.md`); rationale in design **D9**. Independent of the sister jar: the parser reads recorded traces, and the grace window is a harness constant.

- [x] 5.1 Create `modules/aperv-tool/src/aperv_tool/analysis/coverage_dump.py`: parse `[APE-RV] UICOV` and `[APE-RV] UICOV-ACT` per run. Match the tags as **substrings** — every logcat line is prefixed `[APE] `, and the `Logger.format` lines carry it *without* the `*** INFO *** ` the others have, so no regex may anchor at `^`. Use `discovered`/`interacted` (integers) as the computation source, never `gap` (one decimal, `Locale.ROOT`) (INV-APV-36)
- [x] 5.2 Cross-run aggregation at Activity grain only; `UICOV` lines parsed for intra-run use and never joined across runs (INV-APV-36). Document inline WHY: `StateKey.toString()` embeds a JVM identity hash, measured cross-replica Jaccard 0.000
- [x] 5.3 Dump status per run — complete / partial / absent — with a truncated final line retained as partial, and no run omitted for lacking a dump (INV-APV-37)
- [x] 5.4 Record that `mopReach` exists on `UICOV` and not on `UICOV-ACT`: report its absence at Activity grain rather than inferring it (the jar-side propagation is item O2, not in either change)
- [x] 5.5 Widen the capture grace window in `tool.py` from `timeout_seconds + 15` to `timeout_seconds + 45` (the call site is `Command("adb", cmd_args, timeout_seconds + 15)` at `tool.py:991`), with an inline comment stating it is a hypothesis about censored teardown durations, not a measurement. The spec change is the MODIFIED `ApeRVTool Execution Flow` (step 7), which also carries the `RVToolTimeoutError` contract — grep the `aperv` spec for `+ 15` and confirm no upstream statement of the old value survives
- [x] 5.6 Unit tests against recorded iter0 traces as read-only fixtures: a run with a complete dump; a run with no dump (reported, not dropped); a synthetic truncated tail (partial); per-arm dump presence reproduces the recorded 43.8%–65.0% range over the ten `aperv` arms and 462/800 overall; every fixture byte-identical afterwards
- [x] 5.7 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/analysis/coverage_dump.py`
- [x] 5.8 Run `/rv-test-run aperv-tool`

## 6. Cross-repository integration (needs the sister jar)

- [x] 6.1 Record both the git sha and the sha256 of the `ape-rv.jar` build containing B1, and put both in the LLM arm's declaration (task 3.3)
- [x] 6.2 Real smoke via `rv-platform` against a real SGLang server — infrastructure scope: 3 APKs × 3 arms, short timeout, all tasks COMPLETED, coverage > 0, SGLang answers. The APK set MUST include `freeotpplus` and `aegis` (task 6.5 is unreachable on the other 33). No mock LLM. **Never start, stop, or manage an emulator manually** — rv-platform owns the whole lifecycle
- [x] 6.3 Smoke gate: the `jar_sha256` captured at run start matches the arm's declared `expected_jar_sha256`; a mismatch fails before the decisive run launches, naming both digests and the declared git sha (INV-APV-34)
- [x] 6.4 Smoke gate: in the control arm, `decision_source=MOP` count == 0 AND the `mop=` field is always 0 across every step. This is the one behavioural gate the smoke carries, because it is the single failure that invalidates the whole run
- [x] 6.5 Smoke gate: the pushed `static_analysis.json` carries the two handler-reach booleans, and `[DM]` markers appear for widgets whose handlers reach JCA — verifiable only on the 7 apps with flaggable listeners (design Risks)
- [ ] 6.6 Smoke gate: provenance fields present in the task output, naming the model actually served
- [ ] 6.7 Fix the provenance query's address, found failing by gate 6.6 on 2026-08-01. `_capture_llm_provenance` runs host-side (or container-side) but queries the arm's `llm_url`, whose value is the emulator-only alias `10.0.2.2` — a QEMU user-mode networking alias that exists only inside the Android guest. The query timed out on all three LLM-arm runs (`capture_status=query_failed`, `llm_model=null`) while the jar, which runs *inside* the emulator, reached the server normally. **The defect is not smoke-specific**: the compose file sets no `APERV_LLM_BASE_URL`, so the decisive run would carry the same default and lose the same field. Resolve the alias to `127.0.0.1` for the query only, never mutating what reaches `ape.properties` — that address is correct in both environments (host: the published SGLang port; container: the `socat` bridge the entrypoint binds to `127.0.0.1:30000`, `docker/rvandroid/docker-entrypoint.sh:38-40`). Then re-run the LLM arm alone (3 runs) to close 6.6

## 7. Sonda de poder do RQ-C1, antes de comprometer a corrida decisiva (needs the sister jar)

Adicionada 2026-07-31; fundamentação em design **D10**, e a sonda está descrita na proposal em *What Changes*. **Motivo**: a verificação adversarial mostrou que o McNemar exato exige ≥7 pares discordantes a Holm α=0,025, e os análogos da iter0 preveem 3–4 nos dois contrastes (`docs/20260731_verificacao_analise_percepcao.md` §1.1.2; pré-registro §3, "O poder do primário"). Nenhum braço da iter0 fixa o substrato frontier e desliga o MOP — o `ape:default` difere em 18 chaves, não nas 6 do contraste real —, então **nada do que já foi gravado responde se o contraste primário do RQ-C1 tem pares discordantes**. Esta sonda responde isso por ~1/5 do custo da corrida completa. É diagnóstico de desenho, não desfecho.

- [ ] 7.1 **Declarar a sonda no pré-registro ANTES de rodá-la** (`docs/20260730_preregistro_corrida_decisiva.md`, §7 análises exploratórias): que ela existe, que roda em orçamento distinto do decisivo, que seus resultados **não entram na análise confirmatória** em hipótese alguma, e o que se fará com cada desfecho dela (7.6). Sem essa declaração prévia a sonda é *peeking* sobre o contraste pré-registrado e contamina o congelamento — esta task é bloqueante para todas as demais deste grupo
- [ ] 7.2 **Orçamento: 300 s, não 1800 s** — decisão de desenho, e o motivo é o isolamento. A 300 s a sonda (a) não produz os runs da corrida decisiva, então não há dado reutilizado nem descartado, e (b) é diretamente comparável ao análogo confundido da iter0 (`ape:default` × `sata_mop_act_frontier`, n_disc=4), isolando exatamente o que muda: um braço MOP-off que **mantém** o substrato frontier. Se o autor preferir 1800 s, a sonda deixa de ser sonda e vira a metade RQ-C1 da corrida decisiva — decisão legítima, mas então a estrutura de multiplicidade do §4 do pré-registro precisa ser refeita antes, porque decidir sobre o RQ-C3 depois de ver o RQ-C1 muda a família de testes. Nota de rigor: o §4 fixa a família (Holm sobre os dois contrastes dentro de cada desfecho) e **não** diz nada sobre ordenação ou teste sequencial — esta conclusão é inferência a partir dele, não citação dele
- [ ] 7.3 Escopo: os **dois braços do RQ-C1** apenas — `mop_on_llm_off` e `mop_off_llm_off`, ambos com LLM desligado. 40 APKs × 1 rep × 2 braços = 80 runs. Sem SGLang: nenhum dos dois braços chama o modelo, o que elimina a dependência de servidor e o modo de falha do disjuntor. Estimativa ≈ 1,5 h em 8 containers
- [ ] 7.4 Reusar os portões de validade já definidos: o `jar_sha256` capturado no início do run bate com o `expected_jar_sha256` declarado no braço (6.3), e no braço de controle `decision_source=MOP` == 0 **e** `mop=` == 0 em todo passo (6.4). Um portão reprovado invalida a sonda inteira — não se "ajusta a leitura"
- [ ] 7.5 Computar o desfecho binário `achou = mop_unique > 0` por APK e a tabela 2×2 pareada; reportar **n_discordante**, o McNemar exato, e a decomposição por estrato Compose/View. Reportar também quantos dos 40 são concordantes-em-zero, que é o outro modo de o teste não ter o que medir
- [ ] 7.6 **Regra de leitura, fixada aqui antes do resultado** — a sonda informa uma decisão de desenho, não a hipótese:
  - **n_disc ≥ 7** → a corrida decisiva roda como pré-registrada; a sonda confirmou que o contraste tem o que medir
  - **n_disc entre 4 e 6** → roda, e o relatório declara de antemão que o poder é marginal (a 300 s; 1800 s pode melhorar, e é justamente o que a corrida testa)
  - **n_disc ≤ 3** → **decisão do autor, não automática**: rodar assim mesmo com a falta de poder registrada, acrescentar o 4º braço opcional (§8 do pré-registro), ou revisar o desfecho primário antes de congelar. A sonda não decide sozinha; ela impede que a decisão seja tomada depois de ver o resultado que interessa
- [ ] 7.7 Registrar o resultado da sonda no `calibracao/journal.jsonl` com o sha256 do relatório, **separado** do carimbo de congelamento do pré-registro, para que a ordem dos dois eventos fique auditável
- [ ] 7.8 **Never start, stop, or manage an emulator manually** — a sonda roda por `rv-platform`/`rv-experiment`, que detêm o ciclo de vida inteiro

## 8. Verification

- [x] 8.1 Run `/rv-qa-lint-fix aperv-tool`
- [x] 8.2 Run `/rv-verify aperv-tool` — full suite green under the CI contract (`--import-mode=importlib -o "addopts="`)
- [x] 8.3 Invoke `/rv-code-reviewer` via the Skill tool on the change set — **NOT EXECUTED: author decided on 2026-07-31 not to run the `rv-*` skills**
- [x] 8.4 Run `openspec validate "gh90-e3-decisive-run-setup"` — clean, artifacts coherent with the implemented state
- [x] 8.5 Run `/rv-docs-sync aperv-tool` — **NOT EXECUTED as a skill: author decided on 2026-07-31 not to run the `rv-*` skills. The two doc edits it would have made were applied by hand (`modules/aperv-tool/CLAUDE.md`: variant count 26→29 with the three arms tabulated, the two new `analysis/` modules listed, and the `+15s` grace gotcha updated to `+45s`)**. Original scope: run `/rv-docs-sync aperv-tool` — update `modules/aperv-tool/CLAUDE.md` (variant table gains three arms; the compaction gotcha becomes three operations)
- [ ] 8.6 Check off every satisfied acceptance criterion in issue #90 before closing it
