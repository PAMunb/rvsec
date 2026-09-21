# Smoke `estudo02-20260916-smoke` — veredito

**Data:** 16/09/2026, 13:10:47 → 13:40:39 (~30 min)
**Desenho:** 12 containers × 1 APK × 11 braços × 1 rep × 60 s = 132 identidades (plano §7.4)
**Imagem:** `phtcosta/rvandroid:0.9.4` (rvsec `fc51ab64`); corpus sha256 `84a03578f0c7203b`
**Máquina:** reiniciada antes do smoke e dedicada à campanha; preflight de smoke com 22 PASS
**Saída completa dos portões:** `smoke_gates.out`, ao lado

## Resultado formal: 7 de 9 portões passam; o 3 e o 5 reprovam

| portão | resultado | resumo |
|---|---|---|
| 1 — 132 identidades COMPLETED, `error_message` vazio | PASSA | 132/132 (três depois do religamento automático, ver abaixo) |
| 2 — C2 ferramenta ≥ 55 s, C3 traço com passo | PASSA | todos os pares |
| 3 — C4 ≥ 1 `RVSEC-COV`, C5 cobertura > 0 | **REPROVA** | 3 pares com zero; 2 são o zero estrutural do `qtesting` (conhecido); **1 é novo: `droidmate` × `mtgfam`** |
| 4 — humanoid falou com o sidecar; sem irmão órfão | PASSA | 382 requisições; 0 órfãos |
| 5 — ≥ 1 violação legível por APK | **REPROVA** | `aegis` = 0 e `mtgfam` = 0; os outros 10 APKs de 14 a 591; 0 mensagens mudas |
| 6 — zero `VerifyError` | PASSA | nenhum |
| 7 — códigos rotulados; `vfp`/`vcls` só em `-NOBS-` e fora do `unique_msg` | PASSA | 556 de 1 612 linhas com código rotulado, nos seis rótulos; 285 de 627 `-NOBS-` com evidência; 0 fora de `-NOBS-`; 0 no `unique_msg` |
| 8 — nenhum `-ORDER-` com gatilho `g2` nas três specs do A1 | PASSA | 0 linhas |
| 9 — saída 0, sem OOM, seis arquivos da exportação | PASSA | 12/12 saíram 0, nenhum OOM; os seis arquivos em todos (A6) |

Os consertos que o smoke existia para verificar — rótulos, evidência, fim do disparo duplo,
exportação sem OOM, ausência de `VerifyError` — passaram todos.

## Portão 5: `aegis` e `mtgfam` quase não mostram violação em 60 s

Na `estudo02` (`estudo02_consolidado/errors.csv`), execuções de 60 s com ≥ 1 violação:

| APK | `estudo02`, 60 s | smoke |
|---|---|---|
| `com.beemdevelopment.aegis_81` | **0 de 33** (as 30 linhas dele são de 180 e 300 s; a primeira aos 129 s) | 0 de 11 |
| `com.gelakinetic.mtgfam_99` | **1 de 33** (`monkey`, rep 2) | 0 de 11 |
| os outros 10 APKs do smoke | 4 a 33 de 33 | 14 a 591 violações cada |

Com essa taxa, zero em 11 execuções era o esperado para os dois. O `aegis` entrou no smoke pelo
A3 (gancho em destino de desvio) e o `mtgfam` por chave/IV fixos; nenhum dos dois foi escolhido
por alcançar violação em 60 s. O A3 está verificado estaticamente no corpus inteiro
(`tecelagem.md`, (c) = 0 de 7 951).

## Portão 3: o DroidMate consumiu os 60 s no próprio bootstrap

`droidmate` × `mtgfam` (`smoke_03`): o trace vai de 13:24:22 a 13:25:20. O DroidMate passou 29 s
compilando o monitor de API, reinstalou o APK, abriu a exploração às 13:25:13 e o traço termina
no primeiro `LaunchApp`. O logcat não tem nenhuma linha do app.

O bootstrap do DroidMate (primeira linha do trace → `Exploration start time`) e o passo de
compilação do monitor (`Injecting API redirection` → `…compilation directories cleaned`):

| execução | compilação | bootstrap |
|---|---|---|
| smoke, 12 containers (a única execução do DroidMate em cada um) | 19–29 s, mediana 22 | **31–51 s**; o `mtgfam` foi o de 51 s |
| smoke da `estudo02`, 2 containers (também primeira execução) | 14 e 18 s | 23 e 26 s |
| `estudo02`, **primeira** execução do DroidMate em cada um dos 10 containers | 17–20 s (9 de 10) | — |
| `estudo02`, execuções seguintes (400 de 60 s) | mediana 2–3 s | mediana 15 s, p90 22, máx 34 |

**A compilação é fria só na primeira execução de cada container**, e o smoke só tem essa. Por cima
disso, os 12 containers rodaram o DroidMate na mesma janela (13:24–13:28), porque a ordem dos
braços é a mesma em todos: a CPU média do host na janela ficou em 50 % usuário, 40 % ocioso,
iowait 0,4 % (`sar`), o que soma uns 5–25 s ao caso frio. Na campanha, cada container tem ~126
execuções do DroidMate e só a primeira é fria.

## Falhas de instalação e religamento automático

Três identidades terminaram em `ERROR` na primeira passada, todas com o mesmo mecanismo: o emulador é
dado como ligado (`bootanim` parado), o `adb root` falha um segundo depois e o `adb install -r -g`
recebe `adb: device offline`. A instalação é tentada uma vez.

| container | APK | braço |
|---|---|---|
| `smoke_10` | `myexpenses` | `droidbot:bfs_greedy` |
| `smoke_03` | `mtgfam` | `ape` |
| `smoke_07` | `dsub2000` | `ares` |

**3 de 132 (2,3 %)**, contra ~1 % na `estudo02` com 10 containers. Em cada caso o `rv-experiment`
saiu ≠ 0, o `on-failure:50` religou o container (`RestartCount = 1`) e o resume refez só a
identidade que faltava. As três terminaram COMPLETED; nenhum `docker restart` manual.

## Calibração de contenção (plano §4)

| medida | smoke, 12 containers | `estudo02`, 10 | limiar do plano |
|---|---|---|---|
| boot + install, mediana | **61,5 s** | 54,0 s | ≤ 60 s |
| overhead total por task, mediana | **72,8 s** | 65,3 s | ≤ 75 s; recuar para 10–11 só acima de 90 s |
| projeção | maior lote 14 × 7,07 h/APK → **4,12 dias** de máquina | — | ~4,1 d (§4.2) |

O boot + install passa do limiar de 60 s em 1,5 s; o overhead total fica dentro dos 75 s e longe
dos 90 s que mandam recuar. Nenhum OOM de host (`journalctl -k -g oom-kill` vazio).

## O que fica para decisão

Os portões 3 e 5 são bloqueantes pelo plano (§7.4) e reprovaram. As duas reprovações têm causa
identificada, nenhuma delas no que a gh114 mudou, mas **dispensar um portão bloqueante é decisão
do responsável pela campanha, não deste registro**. Também para decisão:

- a taxa de 2,3 % de falha de instalação por `device offline` logo após o boot, recuperada pelo
  religamento automático;
- o boot + install em 61,5 s, 1,5 s acima do limiar de 60 s.

## Decisão (Pedro, 16/09/2026)

Aprovadas as três, depois de ler este veredito:

1. **Portões 3 e 5 dispensados** pelas causas acima (DroidMate frio e sincronizado; `aegis` e
   `mtgfam` sem violação alcançável em 60 s). O smoke não se repete.
2. **Falha de instalação de 2,3 %** aceita: o `on-failure:50` e o resume a recuperam.
3. **12 containers mantidos**, com boot + install em 61,5 s.

Próximo passo: `preflight.sh campanha` e launch.
