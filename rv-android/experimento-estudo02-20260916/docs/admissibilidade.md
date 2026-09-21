# Admissibilidade C1–C6 — `estudo02-20260916`

**Varredura completa rodada em 20/09/2026, das 14:56:40 às 15:05:43** (9 min 03 s), com os 12
containers já parados (`Exited (0)`, conferido às 14:56:25) e sem `--skip-artifacts`: C3 e C4
abriram os 16 137 traços e logcats.

```bash
uv run python experimento-estudo02-20260916/scripts/admissibility.py \
    --json experimento-estudo02-20260916/docs/admissibilidade.json
```

Saída íntegra em `admissibilidade.out`; veredictos por identidade em `admissibilidade.json`
(6,8 MB). Esta é a varredura que vale: a leitura parcial de 20/09 10:10, em `--skip-artifacts`,
não conseguia rotular o zero estrutural nem a parada da ferramenta e foi descartada.

## Veredito

| | `estudo02-20260916` | `estudo02` (antes do reparo) |
|---|---|---|
| identidades observadas | **16 137** | 16 137 |
| admissíveis | **15 602** (96,7 %) | 15 614 (96,8 %) |
| zero estrutural (`qtesting`) | **171** | 171 |
| parada da ferramenta | **246** (82 células, 35 APKs) | 249 (85 células, 37 APKs) |
| lançamento fora do app | **45** | 45 |
| inadmissíveis | **76** (0,47 %) | 58 (0,36 %) |

A coluna da direita é a etapa comparável da campanha de setembro — a primeira varredura **com as
três categorias declaradas já em vigor e antes do reparo**, registrada em
`experimento-estudo02/docs/20260914_validacao_execucao.md` (Parte IV, item 2). Não é o estado final
daquela campanha (15 650 admissíveis, 22 inadmissíveis), que só se alcança depois do reparo.

**As três categorias declaradas reproduziram-se quase exatamente.** O zero estrutural deu 171 nos
mesmos 19 APKs, e o lançamento fora do app deu as mesmas 45 identidades da `org.wikipedia_50595`
sob a família droidbot, entrando pela `leakcanary.internal.activity.LeakLauncherActivity`. A parada
da ferramenta caiu de 249 para 246, com a mesma composição por braço
(`droidbot:dfs_naive` 132, `ares` 60, `droidbot:bfs_naive` 54; lá eram 144/60/51).

**O C6 fecha:** 16 137 observadas contra 16 137 previstas pelo manifesto, conjunto idêntico.

## Inadmissíveis: 76, das quais 73 voltam à fila

```
por critério (uma identidade pode reprovar em mais de um)
  C2  51        C4  24        C5  31

por braço                        por combinação de critérios (as 73 puras)
  ares                  34         C2          45
  fastbot               11         C4+C5       15
  droidbot:dfs_naive     9         C5           7
  droidmate              9         C2+C4+C5     6
  qtesting               7
  monkey                 3       por orçamento: 60 s → 25, 180 s → 27, 300 s → 21
  ape                    2
  humanoid               1
```

As 76 do relatório são **73 identidades inadmissíveis puras** mais **3 que já estão numa categoria
declarada e guardaram uma reprovação residual**: as `ares@300 s` da `de.markusfisch.android.binaryeye_174`,
rotuladas parada da ferramenta (o C2 sai da lista) mas ainda sem cobertura nenhuma (C4+C5). Pela
regra do `repair.py`, parada da ferramenta não volta à fila, então essas 3 ficam onde estão.

Das 73 puras, **uma já tem duas tentativas** (`de.luhmer.owncloudnewsreader_196.apk|ares|1|180`,
C2+C4+C5) e portanto sairá como `REVISAR`, não como reparável. O dry-run do `repair.py` deve, por
essa contagem, oferecer **72 identidades**. Contra a `estudo02`, que ofereceu 57 e recuperou 36.

Contagem por APK, do mais afetado para baixo: `binaryeye` 16, `giggity` 5, `mtgfam` 4,
`sharetoinputstick` 4, `greenstash` 3, e mais dez APKs com 2 cada. Por container, `_05` concentra
25 das 76; os outros onze ficam entre 2 e 8.

## A diferença que precisa de explicação: 76 contra 58

O aumento de 18 inadmissíveis não está espalhado. **Dezesseis das 76 (21 %) são um único APK, a
`de.markusfisch.android.binaryeye_174`, dentro de uma janela de 32 minutos do container `_05`.**

Reconstruí o bloco desse APK pelo `tasks.json` do `_05`. Ele ocupou o container de 18/09 12:50:44 a
18:52:12, um braço de cada vez, e nove dos onze braços correram normais. A degradação começa às
17:48 e termina às 18:20:

| janela (18/09) | braço | o que aconteceu |
|---|---|---|
| 12:50 → 17:41 | `monkey`, as quatro estratégias do `droidbot`, `ape`, `droidmate`, `humanoid` | normais; 1 reprovação isolada (`ape` rep3@60, C5) |
| 17:48 → 18:03 | `ares` | 6 das 9 identidades reprovam; tempos de ferramenta de 39 a 82 s |
| 18:03 → 18:20 | `fastbot` | **as 9 identidades** abaixo do piso; 33 a 109 s de ferramenta |
| 18:20 → 18:52 | `qtesting` | normal de novo (74/64/63, 191/185/183, 303/302/323 s) |

O traço do `ares` dessa janela diz o que foi: `adb: device offline`, e só **depois** disso o `ares`
imprime o seu `Too Many Times tried`. O traço do `fastbot` simplesmente corta no meio de um
`ACTION_MOVE`, sem mensagem de parada.

**Na `estudo02` essas mesmas 18 identidades eram todas admissíveis**, com tempo de ferramenta
normal (`fastbot` 71/190/311 s, `ares` 311–313 s em 300 s). Não é propriedade do par (APK,
ferramenta): é um episódio de emulador/adb de ~32 min, confinado a um container, que apanhou dois
braços em sequência. É transiente, e é exatamente o que o reparo existe para tratar.

Descontados esses 16, sobram 60 inadmissíveis contra as 58 da `estudo02` — a mesma ordem de
grandeza que o procedimento esperava. As inadmissíveis não se concentram em nenhum dia: 0,30 % a
0,68 % das identidades encerradas por dia, sem episódio dominante além deste.

O que sobe em relação à `estudo02` são o C4 (13 → 24) e o C5 (16 → 31), quase todo em identidades
que rodaram o orçamento inteiro e não publicaram cobertura nenhuma — `droidmate` 9 e `ares` 11.
Na `estudo02` o `droidmate` tinha reprovações nessa mesma forma e **todas se recuperaram no
reparo** (terminou com zero). É a assinatura da falha silenciosa que o reparo recupera, não um
defeito novo.

## Candidatas à exclusão: 45 APKs, e nenhum excluído

O script calcula e para por aí — nenhuma aplicação sai da análise sem decisão sua. Dos 45 APKs com
ao menos uma célula `(apk, braço, orçamento)` sem réplica admissível:

- **44 são apenas categoria declarada** — zero estrutural do `qtesting`, parada da ferramenta ou o
  lançamento fora do app da Wikipedia. São células que o artigo publicou com zero e que
  permaneceram na análise.
- **1 é por outro motivo**, e é a `binaryeye`: as três células do `fastbot` (60, 180 e 300 s), todas
  as nove réplicas em C2. É o episódio de 18/09 descrito acima. Se o reparo recuperar essas nove,
  ela deixa de ser candidata — como a Wikipedia deixou de ser na `estudo02` depois que o
  lançamento fora do app virou categoria.

## Duas coisas para você decidir antes do reparo

Nenhuma delas eu resolvo sozinho; as duas são mudança de desenho ou decisão de campanha.

1. **As 3 `ares@300 s` da `binaryeye` estão rotuladas parada da ferramenta e, por isso, não voltam
   à fila.** O rótulo está correto pela regra escrita — as três réplicas ficaram abaixo do piso com
   o marcador `Too Many Times tried` no traço —, mas o traço mostra que o marcador veio *depois* de
   `adb: device offline`. Na `estudo02` as mesmas três rodaram 311–313 s e foram admissíveis. Se
   você quiser tentá-las de novo, o caminho previsto sem mexer em critério nenhum é o
   `repair.py --rerun de.markusfisch.android.binaryeye_174.apk,ares,<rep>,300`, que o cabeçalho do
   script descreve como decisão sua. **Não alterei `TOOL_STOP_MARKERS` nem a regra da célula.**
2. **O `fastbot` não tem marcador registrado em `TOOL_STOP_MARKERS`**, então as suas 9 reprovações
   na `binaryeye` entram cruas como C2 e o reparo vai devolvê-las à fila. Aqui isso é o que se
   quer, porque a causa foi transiente. Registro só para você saber que, se algum dia o `fastbot`
   parar de propósito, a regra atual o lerá como C2 e o devolverá à fila indefinidamente.

## Próximo passo

Depois da sua leitura: o dry-run do `repair.py` (sem `--apply`) sobre os doze containers, que deve
oferecer as 72 reparáveis e a `owncloudnewsreader|ares|1|180` como `REVISAR`.

## Dry-run do reparo (20/09, 15:44:23 → 15:44:55)

```bash
uv run python experimento-estudo02-20260916/scripts/repair.py estudo02-20260916_00 ... _11
```

Sem `--apply`: nada foi mutado. Levou 32 s, e não os ~9 min da varredura, porque os artefatos
ainda estavam no cache de página.

```
resumo: 72 a reparar, 1 para revisar, 0 já em ERROR (o resume alcança),
        462 em categoria declarada — zero estrutural, parada da ferramenta,
        lançamento fora do app (não voltam à fila)
nenhum APK foi excluído, filtrado ou removido
```

Bate com a contagem feita sobre o `admissibilidade.json`. A única `REVISAR` é a
`de.luhmer.owncloudnewsreader_196.apk | ares | rep1 | 180 s` (C2+C4+C5 após 2 tentativas). Cada
reparável preserva 2 artefatos — logcat e traço —, 146 arquivos e 27,4 MB ao todo, em
`backup/estudo02-20260916-inadmissiveis/`.

Por braço: `ares` 26, `fastbot` 10, `droidmate` 9, `droidbot:dfs_naive` 8, `qtesting` 7,
`monkey` 3, `ape` 2, `humanoid` 1. Por container, o `_05` leva 22 das 72 (13 delas são a
`binaryeye`); os outros onze ficam entre 2 e 6.

Custo estimado da passada de resume seguinte: ~4,7 h de máquina, com o relógio de parede dado
pelo container mais carregado — o `_05`, com ~1,4 h.

## Reparo aplicado (20/09, 15:57:49 → 15:58:31)

Decisões suas de 20/09: aplicar as 72; **não** usar `--rerun` nas 3 `ares@300 s` da `binaryeye`,
que ficam como parada da ferramenta.

Os doze containers foram conferidos `running=false` às 15:57:06. A primeira tentativa recusou com
`EXIT=2` — dentro do `docker run` não há `docker.sock`, a guarda não consegue consultar o estado e
para, que é o comportamento certo. Repetida com `--assume-stopped`, já com a evidência do host.

```
resumo: 72 reparadas, 1 para revisar, 0 já em ERROR, 462 em categoria declarada
```

Conferido depois: **72 identidades sem nenhum registro `COMPLETED`**, todas com a `error_message`
do `repair.py`, e **144 artefatos (28 MB)** preservados em
`backup/estudo02-20260916-inadmissiveis/`, já com dono do host.

## Passada de resume (20/09, 15:59:14 → 17:33:11)

`docker compose … up -d`. Antes: sidecar `rv-humanoid` de pé, nenhum irmão órfão, 113 g de RAM
disponível, pressão de I/O em 0,56 %.

Às 16:02:55 os doze logs mostravam o resume pegando **exatamente** as reparadas de cada container
(2, 3, 4, 7, 6, 22, 3, 6, 6, 5, 5, 3), com pulado + restante fechando 1 386 e 1 287 por lote.

Os doze saíram `exit=0`, **sem OOM nenhum**, e reescreveram os seis arquivos da exportação
(`summary.csv` de novo com 1 386 e 1 287, somando 16 137). Quatro tiveram um religamento — o padrão
de esvaziar a fila, sair, o Docker religar e a passada seguinte exportar. O `_05` fechou por
último, 1 h 34 min depois do `up`, contra a estimativa de ~1,4 h.

## Admissibilidade depois do reparo (20/09, 17:34:12 → 17:38:02)

Gravada em `admissibilidade_pos_reparo.json`, ao lado do veredito de antes — a comparação entre os
dois é o que mede a recuperação.

| | antes do reparo | **depois** | `estudo02` (final) |
|---|---|---|---|
| admissíveis | 15 602 | **15 653** (97,0 %) | 15 650 |
| zero estrutural | 171 | **171** | 171 |
| parada da ferramenta | 246 | **246** | 249 |
| lançamento fora do app | 45 | **45** | 45 |
| inadmissíveis | 76 | **25** | 22 |

**C6 fecha:** 16 137 observadas / 16 137 previstas, conjunto idêntico ao manifesto.

**Das 72 reparadas, 51 se recuperaram e 21 repetiram a falha.** Na `estudo02` foram 36 de 57
recuperadas e — por coincidência — as mesmas 21 a repetir. **Nenhuma identidade nova ficou
inadmissível**: o conjunto de depois está contido no de antes, então a passada de resume não
introduziu defeito.

Recuperadas por braço: `ares` 15, `fastbot` 11, `droidmate` 8, `qtesting` 6, `droidbot:dfs_naive` 5,
`monkey` 3, `ape` 2, `humanoid` 1. As que repetiram concentram-se no `ares` (15 de 21), com
`droidbot:dfs_naive` 4, `droidmate` 1 e `qtesting` 1 — e por APK em `giggity` 4, `mtgfam` 4 e
`sharetoinputstick` 3.

**O episódio da `binaryeye` era mesmo transiente: as 13 reparadas dela recuperaram-se, todas.**
Com isso a `binaryeye` deixa de ser candidata à exclusão por outro motivo, e o relatório passa a
listar **45 APKs candidatos, os 45 apenas por categoria declarada e nenhum por outro motivo** — o
mesmo desfecho a que a `estudo02` chegou depois do seu reparo. A única célula morta que resta nela
é a `ares@300 s`, a parada da ferramenta que você decidiu manter.

As 25 inadmissíveis finais (0,15 % das 16 137) são C2 21, C4 5, C5 5, em `ares` 19,
`droidbot:dfs_naive` 4, `droidmate` 1 e `qtesting` 1. Três delas são as `ares@300 s` da `binaryeye`,
que já estão em categoria declarada e guardam só a reprovação residual de cobertura.

## O que a consolidação faz com estes veredictos

Conferido no `consolidate_compare.py` e nos arquivos em 20/09 19:24:46, porque a pergunta —
"nenhuma task se perde, nem as que deram zero?" — é a que decide se os veredictos acima viram
dado ou viram filtro.

**O `per_task.csv` leva as 16 137, e nenhuma é filtrada.** O consolidador escreve uma linha por
identidade, guardando o **último registro `COMPLETED`** de cada uma — para as 72 reparadas, é a
re-execução de hoje, não a execução ruim, que ficou em `backup/`. É o mesmo registro que a
admissibilidade julga, então as duas leituras não divergem. Conferido: 16 137 identidades com
registro `COMPLETED`, exatamente as previstas.

**Os zeros medidos entram como zeros.** Os 171 zeros estruturais, as 246 paradas da ferramenta, os
45 lançamentos fora do app e as 25 inadmissíveis vão todos para o CSV, com `cov_act = 0` onde foi 0.

**A admissibilidade entra como coluna, não como filtro.** O script acrescenta `category`,
`admissible` e `fails`, e a agregação não filtra por elas — o cabeçalho dele diz "elas sao COLUNAS,
a agregacao nao filtra por elas — excluir e' decisao humana", e ele imprime
`admissibilidade (colunas, nao filtro): {...}` ao terminar.

**Zero não medido nunca vira zero.** Logcat ausente, ou `<apk>.json` ausente, **abortam a
consolidação inteira** em vez de escrever 0 — a lição do bug gh58, em que cobertura zerada por
artefato ausente virava dado. Pré-conferido: 0 identidades sem `logcat_file` no índice, 0 logcats
ausentes no disco, 0 `<apk>.json` ausentes nos 163 APKs.

### Ressalva registrada a pedido do Pedro (20/09)

**As médias de `per_apk_paired.csv`, `per_tool_summary.csv` e o Wilcoxon incluem os zeros das
categorias declaradas.** É o comportamento certo — o artigo publicou esses mesmos zeros —, mas
quer dizer que **as médias não são "só admissíveis"**. Qualquer número lido dessas tabelas carrega
os 171 zeros estruturais do `qtesting`, as 246 paradas da ferramenta e os 45 lançamentos fora do
app junto com as execuções íntegras, e quem citar um desses números tem de dizer isso.

Se em algum momento se quiser a sensibilidade "só admissíveis", **as colunas `admissible` e
`category` do `per_task.csv` estão lá justamente para recortá-la sem reconsolidar** — não é preciso
rodar nada de novo nem mexer no consolidador.

Onde não existe célula nenhuma, o `per_apk_paired.csv` escreve `nan`, e não 0; e o Wilcoxon só
pareia os APKs em que as duas ferramentas têm a célula.

## Consolidação (20/09, 19:26:26 → 19:26:45)

```bash
uv run python .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py \
    estudo02-20260916 --admissibility experimento-estudo02-20260916/docs/admissibilidade_pos_reparo.json
```

```
admissibilidade (colunas, nao filtro): {'admissivel': 15653, 'inadmissivel': 22,
    'estrutural': 171, 'parada_ferramenta': 246, 'lancamento_externo': 45}
unidades (apk, timeout) pareadas: 489 | timeouts: [60, 180, 300] | tasks: 16137 | tools: 11
```

Saída em `data/results/estudo02-20260916_consolidado/`:

| arquivo | linhas | o que é |
|---|---|---|
| `per_task.csv` | **16 137** | uma linha por identidade, com as três colunas de admissibilidade |
| `per_apk_paired.csv` | 489 | as unidades pareadas (163 APKs × 3 orçamentos) |
| `per_apk_static.csv` | 163 | a covariável estática por APK |
| `per_tool_summary.csv` | 33 | 11 braços × 3 orçamentos |
| `wilcoxon.csv` | 825 | 55 pares × 5 métricas × 3 orçamentos |

Conferido no CSV: **16 137 linhas e 16 137 identidades distintas**, 163 APKs, 11 braços, e as
categorias somando exatamente 16 137. Um zero estrutural do `qtesting` aparece com
`cov_act = 0`, `cov_method = 0` e `category = estrutural` — medido, rotulado e presente, que era o
ponto.

### Por que o consolidador diz 22 inadmissíveis e a admissibilidade diz 25

Não é divergência: são duas perguntas. O consolidador atribui **uma** categoria por linha, nesta
ordem — estrutural, parada da ferramenta, lançamento fora do app, inadmissível, admissível. As 3
`ares@300 s` da `binaryeye` são parada da ferramenta **e** guardam a reprovação residual de
cobertura (C4+C5), então o CSV as conta em `parada_ferramenta` e o relatório de admissibilidade as
conta entre as que têm `fails`. 22 + 3 = 25, e os totais fecham 16 137 dos dois lados.

Registrar isto importa porque os dois números vão aparecer lado a lado em qualquer leitura
posterior, e a diferença de 3 tem explicação, não erro.
