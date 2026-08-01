# Corrida decisiva E3 — `experimento-e3-decisiva`

A corrida que decide se a guia MOP e se o LLM entram no desenho final do APE-RV. É a execução do
change `gh90-e3-decisive-run-setup`, e o plano de análise está **pré-registrado** em
`../docs/20260730_preregistro_corrida_decisiva.md`.

O pré-registro é o que dá peso probatório ao resultado: ele fixa desfechos, testes, correção de
multiplicidade e regra de decisão **antes de qualquer dado ser visto**. Depois do congelamento — o
registro do sha256 do arquivo em `../calibracao/journal.jsonl` — nada nele pode mudar, e toda análise
não prevista lá é exploratória por definição. **Congelar antes de dar `up -d`.**

## O desenho

| | |
|---|---|
| Braços | `mop_on_llm_off` · `mop_off_llm_off` · `mop_on_llm_70` |
| Corpus | 40 APKs — `../calibracao/subset40.txt` |
| Repetições | 3 |
| Timeout | 1800 s por task |
| Total | 360 runs, 8 containers, ≈ 23–24 h |
| Imagem | `phtcosta/rvandroid:0.9.3` |

Os três braços são de **fator único** e compartilham a mesma referência, que é o ponto do desenho:
cada contraste isola uma coisa só.

- **RQ-C1** — `mop_on_llm_off` × `mop_off_llm_off`. Mantido todo o resto fixo, a guia MOP aumenta a
  detecção? Os dois braços diferem exatamente nas cinco chaves de peso MOP e em
  `activity_trigger_enabled`. Este contraste nunca foi medido: **toda execução do APE-RV até hoje teve
  a guia MOP ligada**, então nenhuma diferença já observada é atribuível a ela e não à exploração
  baseline do APE.
- **RQ-C3** — `mop_on_llm_off` × `mop_on_llm_70`. Sob MOP fixo, o LLM acrescenta algo? Diferem apenas
  em chaves LLM. A dose 0,7 e o bloco `cal_a1` (v13, temp 0, top_p 0,6, top_k 50) são carregados
  verbatim do iter0 — é a única dose com contrapartida medida a 300 s neste substrato e subset, que é
  o que permite ler o resultado a 1800 s como interação dose × orçamento.

O substrato frontier (`_FRONTIER_SUBSTRATE`) é constante nos três braços. Ele **não** é variável do
experimento; é o chão sobre o qual os três rodam.

## Como rodar

```bash
cd experimento-e3-decisiva
docker compose up -d
bash scripts/monitor.sh            # ou: watch -n 120 bash scripts/monitor.sh
```

**Resume**: re-rodar o mesmo `docker compose up -d`. A identidade de um run é
`(apk, tool, variant, repetition, timeout)`, então o que já completou não é refeito e tasks FAILED
transientes são recuperadas.

**Não dar `down` antes de extrair os traces** — os artefatos vivem no device e são efêmeros.

## Particionamento

`filters/batch_00.txt` … `batch_07.txt`, 5 APKs cada, split determinístico em ordem alfabética do
`subset40.txt` (conferido: união == subset, sem duplicata nem perda).

Cada container roda os **três braços sobre os seus próprios 5 APKs**. Isso é deliberado e não é
detalhe de paralelização: o pareamento estatístico é por APK, então manter os três braços de um APK
no mesmo container garante que uma falha de container derrube o par inteiro em vez de meio par — o
que o resume recupera de forma limpa, enquanto meio par exigiria descarte.

## Portões de validade — validade antes de desfecho

Nenhum desfecho é lido antes destes passarem (pré-registro §2). Um portão reprovado invalida o que
ele protege; não se ajusta a análise para contornar.

1. **Controle limpo** (bloqueante). No braço `mop_off_llm_off`, `decision_source=MOP` == 0 **e** o
   campo `mop=` == 0 em todo passo. Se vazou guia MOP no controle, o RQ-C1 não mede nada.
   Ancorar o padrão com `(?<![a-z_])mop=` — um `grep -o 'mop=[0-9]*'` solto também casa a cauda de
   `activity_has_mop=1` e reporta centenas de violações fantasmas.
2. **Jar correto** (bloqueante). O `jar_sha256` capturado no início do run bate com o
   `expected_jar_sha256` declarado no braço LLM (`386ce08d…d24e69`). O valor é gravado num sidecar
   `*.provenance.json` ao lado do trace, **não** dentro de `results.json`.
3. **Atribuição de braço** (bloqueante). O `[APE-LLM-CONFIG]` de cada run bate com o manifesto,
   40/40 por braço.
4. **Integridade de tasks**. Toda task COMPLETED; ERROR re-executados no resume até esgotar. Runs
   perdidos são reportados em número, não silenciados.

## Ambiente — o que quebra e por quê

- **A GPU é pedida como dispositivo CDI** (`devices: [nvidia.com/gpu=0]`), e não por
  `deploy.resources.reservations.devices` com driver `nvidia`. O host roda Docker 29 com o NVIDIA
  container toolkit instalado mas com o runtime nvidia **não registrado** no daemon, então a reserva
  por driver falha com `could not select device driver "nvidia" with capabilities: [[gpu]]`.
- **O spec CDI vive em `/var/run/cdi/nvidia.yaml`, que é tmpfs** e não sobrevive a um reboot.
  Persistir com `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml`.
- **O modelo é o stock `Qwen/Qwen3-VL-4B-Instruct`**, não o tunado. Trocá-lo quebraria a leitura entre
  orçamentos do §7 do pré-registro, que compara com o `cal_a1`@300 s do iter0.
- **A ponte do LLM é socat** (`docker/rvandroid/docker-entrypoint.sh:38-40`): com
  `RVSMART_LLM_MODE=true` o container liga `127.0.0.1:30000` ao container `sglang`. O jar lê `llm_url`
  de dentro do emulador, onde `10.0.2.2` é o alias de host-loopback do QEMU.

## Estado

Artefatos prontos, **corrida não executada**. Antes do `up -d`:

1. Congelar o pré-registro (sha256 em `../calibracao/journal.jsonl`).
2. Corrigir o §2 do pré-registro, portão 2, que ainda cita o banner `[APE-BUILD]` — banner que não
   existe e nunca existiu (`gh14-build-provenance-stamp` foi arquivado sem implementação). O portão
   hoje é o sha256 do jar instalado.
3. Corrigir o §7, que descreve a sonda de poder do RQ-C1 — cancelada em 2026-08-01 por decisão do
   autor, por não alterar nenhuma ação subsequente. O risco de poder que ela mediria é lido no fim,
   sobre os resultados da própria corrida, como o §3 já declara.
