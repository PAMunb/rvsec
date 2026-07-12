# Residual do experimento-20260706 — modo de falha `monkey × timeout-longo`

Data da análise: 2026-07-12 (~09:45 local). Snapshot: 20.978 ok / 612 err de 21.681 tasks-alvo (96,76% ok real; 99,6% terminal).

## Resumo executivo

O residual de erro do experimento **não é OOM transitório aleatório de concorrência**. É um modo de
falha **sistemático, específico da tool `monkey` em corridas longas**, uniforme nas 4 VMs. Das ~612
identidades net-ERROR, **~608 (≈99,3%) são `monkey`**; as 10 demais tools completam praticamente
100% em todos os timeouts, inclusive 300s.

Decisão (autorizada pelo usuário, 2026-07-12): **documentar o residual como limitação conhecida e
não iterar mais m3/m4** com retry/mop-up. m1/m2 seguem até o fim do walk corrente (encolhem um pouco
mais, mas convergem para o mesmo piso monkey-p300).

## Mecanismo

`monkey` injeta eventos de UI a taxa altíssima, sem pacing (throttle 0 por padrão). Sob a
instrumentação RVSEC-COV (que loga cada método coberto no logcat), a taxa de eventos do monkey faz o
processo do app + a captura de coverage crescerem em memória muito mais rápido que sob as tools
model-based (droidbot, ape, droidmate, humanoid, ares, fastbot, qtesting), que pausam entre ações.
Em runs longos, a memória estoura e o processo é morto **por fora** (container/host OOM), mid-run.

Evidência do logcat (`org.fossify.paint_7.apk__1__300__monkey.logcat`): o app roda normal, com stream
contínuo de `RVSEC-COV` (dialogs, color pickers sendo exercitados), e o arquivo **corta no meio**
(~08:58) **sem CRASH/ANR/FATAL/OutOfMemory no log** — assinatura de kill externo, não de crash do app.

## Quatro pilares da evidência

1. **Só o monkey falha.** As outras 10 tools fecham 468/468 (m4) / 495/495 (m3) em TODOS os timeouts.
   OOM genérico de concorrência derrubaria todas ocasionalmente; não derruba.
2. **Monotônico no timeout.** Quanto mais longa a corrida, mais o monkey falha (ver tabela). Assinatura
   de saturação de memória acumulada ao longo do run.
3. **Sem crash no app.** Logcat mostra execução saudável cortada mid-run, sem exceção/ANR.
4. **Lever de baixa concorrência esgotado.** A m4 já rodou mop-up 2-container (concluído 08:24) + retry:
   residual foi de 109 → 108 (ganho 1). Motivo: `docker-compose.mopup.yml` usa 2×16g = **32g > 31 GiB
   da VM** — ainda oversubscreve; dois monkey-p300 pesados simultâneos ainda excedem a RAM do host.
   "Menos containers, mais memória" foi levado ao limite do 2-container e rendeu ~0.

## Composição do residual por VM (deduplicado por identidade)

| VM | net-ERROR | monkey | outras | monkey por timeout (60·180·300) | APKs monkey distintos |
|----|----:|----:|----|----|----:|
| m1 | 155 | 155 | — | 6 · 36 · 113 | 50 |
| m2 | 179 | 178 | 1 fastbot | 3 · 55 · 120 | 53 |
| m3 | 170 | 168 | 1 droidbot + 1 ape | 3 · 49 · 116 | 51 |
| m4 | 108 | 108 | — | 0 · 24 · 84 | 43 |
| **Σ** | **612** | **~609** | **3** | monotônico em todas | — |

Snapshot: m1/m2 ainda rodavam quando medido — seus números encolhem um pouco antes de fechar, pelo
mesmo mecanismo (piso monkey-p300).

## APKs com falha determinística (todas as 9 identidades monkey: 60/180/300 × 3 reps)

- m2: `com.yogeshpaliyal.deepr_28.apk`
- m3: `inc.flide.vi8_170500.apk`

Estes falham o monkey até em 60s → não é só timeout-longo; é incompatibilidade monkey×app determinística.

## Padrão de codebase compartilhado

Na m3, toda a família `info.metadude.android.*.schedule` (apps de agenda de conferência — FOSDEM, CLT,
Datenspuren, DiVOC, FOSSGIS, GPN, HOPE, MRMCD, etc., mesmo template de codebase) falha o monkey em bloco
no 180/300. Reforça a natureza sistemática (não aleatória): o mesmo padrão de app produz a mesma falha.

## Listas completas por (APK, tool, rep, timeout)

Uma linha por identidade net-ERROR (`apk,tool,rep,timeout`):

- `docs/residual/residual_m1.csv` (155)
- `docs/residual/residual_m2.csv` (179)
- `docs/residual/residual_m3.csv` (170)
- `docs/residual/residual_m4.csv` (108)

## Métrica de conclusão correta: logcats não-vazios, não COMPLETED

A métrica de progresso do experimento **não é o estado COMPLETED das tasks** — é o
**número de logcats não-vazios por identidade `(apk,rep,timeout,tool)` sob `results/exp_*/`**
(excluindo `results/smoke/`).

Motivo: uma task marcada ERROR (monkey morto mid-run) **ainda grava um logcat com dado usável**:
- `RVSEC-COV` — eventos de cobertura (entrada de método instrumentado);
- `RVSEC` (tag pura, sem hífen) — eventos MOP / violações JCA no formato
  `Spec,classe,classeSimples,método,arquivo:linha,TipoViolação,detalhe`
  (ex.: `UnsafeAlgorithm`, `UnsafeProtocol`, `InvalidSequenceOfMethodCalls`).

Verificação (2026-07-12): das 108 identidades net-ERROR-monkey da m4, **100% têm cobertura**
(mediana 1.272 linhas RVSEC-COV) e 42 têm eventos MOP; na m3, 168/169 têm cobertura e 109 têm MOP.
A consolidação offline (`scripts/regenerate_results/regenerate_container.py` via
`consolidate_offline.sh`) **reparsa TODO `.logcat` do container sem filtrar por estado** — o dado
das ERROR entra automaticamente no coverage/errors regen. O gate "dedup COMPLETED" da Fase 1 é
apenas validação read-only, não filtra o regen.

**Como contar (correto):** `find results/exp_* -name '*.logcat' -size +0c` + dedup por identidade.
NUNCA `wc -l` de `results/` cru — o `results/smoke/` infla a contagem. Exemplo m1: `find results`
cru deu 5.588 = **5.544 reais** (4 containers exp_00..03, APKs 100% disjuntos, 11 tools, 99
logcats/APK) **+ 44 do smoke** (2 APKs × 22). Overlap de APK entre containers ou tool/variante extra
seriam bug — confirmado que NÃO ocorrem. O smoke é inofensivo e já ignorado pelo pipeline.

**Consequência:** o "residual ~612 ERROR" **não é perda de dado**. A perda real é apenas os poucos
logcats vazios/ausentes (~4: 1 na m4, ~3 na m3). O alvo real do experimento é
**21.681 logcats-por-identidade não-vazios**, e o dado de coverage+MOP das tasks ERROR é aproveitável.

## Implicação para leituras futuras / paper

O residual é uma propriedade conhecida e explicável do setup (`monkey` + instrumentação de coverage +
timeout longo em VM de 31 GiB), não um bug do harness nem perda de dados. Para os 10 tools model-based
a cobertura é completa (≈100% das identidades COMPLETED). Ao reportar resultados por tool, o monkey em
300s tem cobertura reduzida por esse teto de memória — deve ser tratado como *threat to validity*
declarado, não como falha silenciosa.
