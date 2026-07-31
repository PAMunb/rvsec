# gh91 — relatório do grupo 5: instalação no corpus, re-consolidação e verificação

**Data:** 2026-07-31
**Sessão:** rv-android (`modules`), executando o grupo 5 da change gh91
**Destino deste texto:** continuar o trabalho na sessão do `ase-journal`

---

## 0. Onde está a change (caminho absoluto)

```
/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh91-sa-rerun-manifest-key/
```

Artefatos: `proposal.md`, `design.md` (ver §Consolidation), `tasks.md` (38 tarefas).
Repositório rv-android: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`
(`/pedro` e `/home/pedro` são a MESMA árvore — mesmo inode; os dois caminhos funcionam).

O handoff que originou esta sessão:
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260731_gh91_handoff_grupo5.md`

---

## 1. O que o grupo 5 precisava fazer

Os 30 JSONs de análise estática re-analisados sob a chave `Mneut` já existiam e já tinham
passado no portão de validação (grupo 3), mas **o corpus continuava intocado**. Sem instalá-los,
a re-análise não tem efeito nenhum: o caminho de consolidação lê o `STATIC_DIR` plano, e não as
cópias co-localizadas na árvore de RESULTS. O grupo 5 é, portanto:

1. instalar os 30 no corpus preservando os antecessores (5.1);
2. re-consolidar as planilhas a partir dos `.logcat` preservados (5.2);
3. auditar antes de promover (5.3);
4. provar que as violações MOP não se moveram (5.4);
5. entregar o estágio 2 no `ase-journal` (5.5).

---

## 2. O que foi feito, e como foi verificado

### 2.1 Instalação dos 30 no corpus (tarefa 5.1) — CONCLUÍDA

Script (auditável, não foi feito ad hoc no shell):
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/scripts/gh91_install_static.py`

Destino:
`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/`

Procedimento:

1. **Antes de copiar**, o corpus inteiro foi re-conferido contra o manifesto pré-instalação da
   tarefa 4.4 (`sha256sum -c`, saída 0) — para provar que nada havia derivado entre a tomada do
   manifesto e a cópia.
2. A instalação **recusa o lote inteiro** antes de tocar em qualquer arquivo se faltar uma
   origem, faltar um antecessor ou já existir um `.pkgdet`. Uma instalação pela metade é
   indistinguível de um corpus corrompido depois que a prova roda.
3. Por app: preserva o antecessor como `<apk>.json.pkgdet` **primeiro**, depois sobrescreve.

**Prova, em três vias** — P1 e P2 sozinhas passariam mesmo se um antecessor tivesse se perdido
no caminho, e por isso existe a P3:

| Asserção | Resultado |
|---|---|
| P1 — os 30 instalados batem com `manifest_sa_rerun_30.sha256` | PASS |
| P2 — os outros 189 são byte-idênticos ao manifesto pré-instalação | PASS |
| P3 — cada `.pkgdet` bate com o sha256 pré-instalação do seu antecessor | PASS |
| cardinalidade (219 `.json`, 30 `.pkgdet`, conjunto de `.json` inalterado) | PASS |
| **exatamente 30 arquivos mudaram, 189 byte-idênticos** | PASS |

10 asserções, todas PASS. Commit `ebca778c`.

Observação: `.pkgdet` não casa com o glob `*.json`, então o guarda de sanidade do
`consolidate_offline.sh` continuou vendo 219 JSONs, como esperado.

**Não foi feito, deliberadamente:** sincronizar `rvsec-dataset/static_analysis/` e as cópias
co-localizadas em `RESULTS/m*/.../<apk>/`. Nenhuma das duas é lida por este caminho de
consolidação, e deixá-las intactas mantém uma segunda cópia independente dos antecessores.

### 2.2 Re-consolidação (tarefa 5.2) — CONCLUÍDA

Comando (o override de `RESULTS_ROOT` é obrigatório; o default do script aponta para um
diretório que não existe e o guarda aborta com exit 2):

```bash
RESULTS_ROOT=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS \
  bash experimento-20260706/scripts/consolidate_offline.sh
```

**Executado 2026-07-31 10:23:15 → 10:38:03 BRT (~15 min), exit 0.** O script termina com o
código de saída do `verify.py`, então exit 0 já significa auditoria aprovada.
Log: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/consolidation/consolidate_offline.log`

- **Fase 1** — portão VerifyError: **0 arquivos nas quatro VMs** (esperado 0).
  Reportou 21 243/21 681 COMPLETED (97,98%) a partir dos `tasks.json`. **Isso não é dado
  faltando**: é exatamente o gotcha de resume que o próprio cabeçalho do script descreve, e a
  fase 3 resolve a questão ao encontrar 21 681 arquivos `.logcat` e regenerar 21 681 linhas.
- **Fase 2** — todos os 16 containers concluíram (o `run_all.sh` aborta se qualquer um sair
  diferente de zero, e ele chegou ao nível 2). Alvos por VM batidos exatamente: m1 5544,
  m2 5544, m3 5445, m4 5148.
- **Fase 3** — `verify.py --full`: **C1–C4 todos PASS**, `summary_rows=21681`,
  `logcat_files=21681`.

| Arquivo | Regenerado | Baseline 2026-07-12 | Δ |
|---|---|---|---|
| `summary_regen.csv` | **21 681** linhas | 21 681 | 0 (= `TARGET_TOTAL`) |
| `errors_regen.csv` | **165 999** linhas | 165 999 | 0 |
| `coverage_regen.csv` | **20 884 554** linhas | 20 825 013 | +59 541 |

O `+59 541` **não ficou como número solto** — está atribuído em §3.3/§4.

**Antes de rodar**, foram preservados (a promoção da 5.3 sobrescreve os `*_all.csv`, e sem
isso a 5.4 ficaria sem baseline):

- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/baseline/manifest_results_baseline.sha256`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/baseline/verification_report_baseline_20260712.md`
  (baseline: 21 681 linhas, C1–C4 PASS)

### 2.3 Verificação contra o baseline (tarefas 5.3/5.4)

Script: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/scripts/gh91_compare_consolidation.py`
Log: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/consolidation/compare_baseline_vs_regen.log`

O detalhe metodológico importante está em §3: a comparação ingênua responde à pergunta errada
**três vezes**, e as asserções tiveram que ser reescritas para isolar cada confundidor.

---

## 3. Os três confundidores — por que uma comparação ingênua mente

Este é o miolo do relatório. As três diferenças abaixo aparecem num diff direto e **nenhuma
delas** é efeito da troca de chave de análise.

### 3.1 Ordem das linhas

O nível 1 regenera 16 containers em paralelo, então a ordem de concatenação das linhas de um
mesmo app não é estável entre execuções. Uma comparação sensível à ordem acusa quase todos os
apps como alterados enquanto o conteúdo é idêntico — foi exatamente o que aconteceu na primeira
tentativa (148 apps "diferentes" em `errors`, todos por ordem).

**Correção:** toda comparação passou a ser de **multiconjunto**, com hash comutativo
(contagem + soma dos digests das linhas). É O(1) de memória sobre arquivo de 6 GB e cego à
ordem por construção.

### 3.2 Deriva de código entre o baseline e hoje

O baseline foi produzido em 2026-07-12. Dois fixes de parser entraram **depois**, e ambos mexem
legitimamente em colunas — nenhum tem relação com a chave de análise:

- **`cf234788` (2026-07-28, closes #89)** — a posição de origem estava vazando para as colunas
  `class` **e** `method` e, por consequência, para a chave de unicidade de misuse.
- **`79fea6dd` (2026-07-19, refs #83)** — timing da reconstrução; menciona explicitamente que o
  `coverage.csv` havia perdido a ordem cronológica.

O driver de regeneração em si (`scripts/regenerate_results/`) **não mudou** desde o baseline —
conferido por `git log`. A deriva está só nos dois parsers.

**Consequência direta:** `errors_*.csv` **não pode** ser byte-idêntico ao baseline, e a redação
literal da tarefa 5.4 ("byte-identical") é insatisfazível contra esse baseline. O que a 5.4
realmente protege é a afirmação por baixo dela — *violações derivam do logcat e independem da
chave de análise* — e isso se testa **projetando fora** as colunas que os fixes tocam.

### 3.3 Empate de timestamp no coverage

Fora dos 30, linhas de coverage **diferem**, e o motivo não é a chave nem perda de dado: eventos
que compartilham o mesmo timestamp trocam de posição entre execuções. Verificado num caso
concreto (`app.eduroam.geteduroam_2685.apk`, tarefa `1/180/ape`): mesmas 756 linhas, conjunto de
eventos idêntico, **valores finais idênticos** (37.2 / 50.0 / 21.4 / 17.15) — mas `<init>` e
`<clinit>`, ambos em `time=0`, trocaram de lugar.

Aqui houve uma **correção de rumo minha**: eu primeiro assertei que a *curva* ordenada de `cov_*`
seria idêntica. Ela não é, e não deveria ser: quando dois eventos empatados diferem em *se
introduzem uma classe nova*, o valor cumulativo intermediário depende de qual veio primeiro.
Assertar isso seria assertar uma propriedade que o dado nunca teve. O que **não** depende da
ordem é o multiconjunto de eventos e o **ponto final** — e é isso que passou a ser assertado
(C3 e C4). A diferença da curva ficou registrada como nota, visível e não escondida.

---

## 4. Resultado das asserções

### Lado do `summary` (todas as 219 apps)

| # | Asserção | Resultado |
|---|---|---|
| — | grade tem 21 681 linhas; conjunto de chaves `(apk,rep,timeout,tool)` inalterado; 219 apps | PASS |
| **S1** | `mop_errors_total` idêntico para as 219 apps | **PASS — 0 apps se moveram** |
| S1b | `mop_errors_unique` nunca **aumentou** (um fix de dedup só pode fundir) | PASS — 0 linhas |
| **S2** | `cov_*` mudou **apenas** em apps de `30_apks.csv` | **PASS — 0 fora dos 30** |

Nota S1b: `mop_errors_unique` **caiu** em 2136 linhas, em 32 apps — efeito esperado do
`cf234788`/#89, e só para baixo.
Nota S2: `cov_*` mudou em 27 dos 30. Os 3 inalterados: `br.com.colman.petals_3040000.apk`,
`com.github.cvzi.screenshottile_148.apk`, `com.github.livingwithhippos.unchained_60.apk`.

### Lado do `errors`

| # | Asserção | Resultado |
|---|---|---|
| **E1** | identidade da violação `(apk,rep,timeout,tool,spec,message)`, multiconjunto, 219 apps | **PASS — 0 apps se moveram** |
| E1b | coluna `time` deslocou **apenas** dentro dos 30 | PASS — 0 fora dos 30 |
| E2 | nenhum app mudou sua **contagem** de linhas de erro | PASS — 0 apps |
| **E3** | o fix na origem reproduz o reparo in-place do `ase-journal` | **PASS — 0 apps divergem** |

Total de linhas de erro: 165 999 no baseline e 165 999 no regenerado.

Sobre E1b: `time` deslocou em 4 apps, **todos dentro dos 30** — `app.pachli_50.apk`,
`com.jerboa_87.apk`, `net.osmtracker_73.apk`, `org.wikipedia_50595.apk`, que são 4 dos 5 apps
cuja chave **alargou**. Mecanismo verificado no código: o `regenerate_container.py` deriva `t0`
como o evento registrado mais antigo e escreve `time = max(0, int(evento - t0))`; uma chave mais
larga registra mais eventos de coverage, `t0` anda para trás e a linha do tempo inteira do app
desloca. Medido: em 3 deles o deslocamento é de no máximo 1 s em poucas linhas (fronteira de
truncamento do `int()`); em `org.wikipedia` são as 87 tarefas, deslocamento **uniformemente
positivo de 2 a 10 s**, constante dentro de 54 tarefas e variando em exatamente 1 s em 33.
É efeito de escopo legítimo, confinado aos 30 — fora deles seria bug.

### Lado do `coverage`

| # | Asserção | Resultado |
|---|---|---|
| **C1** | identidade do evento `(apk,rep,timeout,tool,time,class,method,signature)`, por app, fora dos 30 | **PASS — 0 fora dos 30** |
| C2 | curva ordenada de `cov_*` | *reportada, não assertada* (§3.3) |
| **C3** | multiconjunto de eventos por tarefa, fora dos 30 | **PASS — 0 fora dos 30** |
| **C4** | `cov_*` **final** por tarefa mudou apenas dentro dos 30 | **PASS — 27 apps se moveram, todos dentro dos 30; 0 fora** |

C1 explica o `+59 541`: o multiconjunto de eventos se moveu em **23 apps, todos dentro dos 30**.
Nenhum app fora dos 30 ganhou ou perdeu evento.

O C4 também mostrou que o conjunto de **tarefas com linhas de coverage** cresceu de 21 302 para
21 348 (46 tarefas que antes não produziam nenhuma linha de coverage agora produzem). Essas 46
pertencem a apps **dentro dos 30** — é o que o próprio C4 prova, já que ele conta como "movida"
qualquer tarefa presente em um lado e ausente no outro, e mesmo assim não achou nenhum app fora
dos 30. É o efeito esperado de uma chave mais larga passar a reconhecer eventos que antes caíam
fora do escopo.

**Procedência dos logs (importante para reproduzir):** o log
`compare_baseline_vs_regen.log` foi gerado por uma execução que ainda tratava o C2 como
asserção — ele aparece lá como `[FAIL]`, e §3.3 explica por que esse invariante foi rebaixado a
nota. O C4 foi medido em separado e está em `c4_final_coverage.log`. O script na árvore já está
corrigido (C2 é nota, C4 é asserção); uma reexecução completa não foi feita apenas para
embelezar o log, porque custaria mais 8 passadas sobre 6 GB sem produzir evidência nova.

---

## 5. O ponto central para o `ase-journal`: equivalência com `fix-rv-key-granularity`

Este é o item que mais importa para a sessão de lá.

**A pergunta:** o defeito da chave de misuse foi corrigido em **dois lugares diferentes**, por
duas mãos, em pontas opostas da cadeia:

- no `ase-journal`, **in place na planilha**, pela change `fix-rv-key-granularity` (arquivada
  em 2026-07-28), via `data-analysis/repair_frame_keys.py`, com 13 macros re-derivados
  (`\uniqueMisusesMOP` 567 → 541 entre eles);
- no rv-android, **no parser**, pelo commit `cf234788` — que é onde o fix deve morar.

Duas correções para o mesmo defeito só são seguras se **concordarem**. Se não concordassem,
entregar estas CSVs contradiria em silêncio uma change arquivada e fechada, e os números
publicados junto com ela.

**Como foi testado:** o `repair_frame_keys.py` **do próprio `ase-journal`** foi importado
verbatim (`is_frame`, `split_frame` — não uma reimplementação), aplicado ao baseline não
reparado, e o resultado comparado com as colunas `class`/`method` regeneradas.

**Resultado:**

- `errors_regen.csv` tem **0 valores em forma de frame** — o fix na origem funciona;
- os **20 872** valores em forma de frame do baseline, passados pelo `split_frame` deles,
  reproduzem **exatamente** as colunas regeneradas — **0 apps divergem, nas 219**.

**Conclusões práticas para o `ase-journal`:**

1. O fix está no lugar certo (parser). O reparo in-place foi remediação pontual de planilhas já
   consolidadas com o parser defeituoso; agora que a consolidação foi refeita a partir dos
   `.logcat` com o parser corrigido, a chave nasce certa na origem.
2. `repair_frame_keys.py` passa a ser **no-op byte a byte** sobre os arquivos entregues (0
   valores em forma de frame para reparar). Rodá-lo continua sendo inofensivo.
3. **O aviso do `reduce_to_181.py` deixa de valer.** Ele diz hoje: *"errors_bck.csv keeps the
   frame-form (class, method) keys upstream … any re-run of this script resurrects them in the
   reduced errors.csv. After re-running, ALWAYS run repair_frame_keys.py"*. Com o `_bck`
   regenerado, não há o que ressuscitar. Atualizar esse aviso é decisão de lá — não editei nada
   no repositório do artigo.

---

## 6. O que isso significa para a entrega (estágio 2)

### 6.1 Mapeamento verificado dos arquivos

Conferido por sha256 e tamanho, não por suposição:

| `ase-journal` (`dataset/results/`) | origem (caminho absoluto) | observação |
|---|---|---|
| `errors_bck.csv` | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/errors_regen.csv` | o `errors_bck.csv` atual é **byte-idêntico** ao nosso baseline (`5dacef02…`) — mapeamento confirmado |
| `summary_bck.csv` | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/summary_regen.csv` | **exige rename de cabeçalho**, ver 6.2 |
| `coverage.csv` | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/coverage_regen.csv` | 6,0 GB |
| 30 × `<apk>.json.pkgdet` | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/` | criados na 5.1 |

### 6.2 ARMADILHA: o cabeçalho do `summary` difere

`summary_bck.csv` do `ase-journal` e `summary_all.csv` nosso diferem em **exatamente uma linha —
o cabeçalho** (as 21 681 linhas de dados são idênticas). Eles renomearam duas colunas:

| nosso `summary_regen.csv` | `ase-journal/summary_bck.csv` |
|---|---|
| `cov_reaches_target` | `cov_reaches_mop` |
| `cov_directly_reaches_target` | `cov_directly_reaches_mop` |

É a terminologia MOP que o `CLAUDE.md` do rv-android exige ("não use 'security' para MOP").
**Entregar o arquivo regenerado sem renomear esse cabeçalho quebraria os scripts de análise de
lá.** Os cabeçalhos de `errors` são idênticos nos dois repositórios — só o `summary` tem isso.

### 6.3 Decisões do dono já tomadas nesta sessão

- **Promoção (5.3):** promover `_regen.csv` → `_all.csv` **preservando** o baseline como
  `*_all_pre_gh91.csv` (reversível).
- **Coverage (5.5):** copiar o CSV regenerado, **sem** mexer nas 9 partes `.gz`. Consequência a
  registrar: as partes `.gz` versionadas ficam **desatualizadas** em relação ao `coverage.csv`.
- **`reduce_to_181.py`:** **não** rodar daqui. Entrega-se os `_bck` regenerados + pins, e a
  derivação da base 181 e os macros do artigo ficam com o dono, no repositório do artigo.

### 6.4 O que esperar quando a base 181 for derivada lá

- `summary.csv` = 17 919 linhas de dados; `errors.csv` = 142 580 — números que continuam válidos.
- Os macros de misuse único já estão na era 541 (pós-`fix-rv-key-granularity`); as CSVs
  entregues **concordam** com essa era, então não deve haver movimento por conta da chave de
  frame. O que muda é o que a mudança de chave de pacote produz nos 30, e só neles.
- `mop_errors_total` não se move em nenhum app — `\totalViolations` não deve mudar.

---

## 7. Estado no fechamento deste relatório

**Concluídas e verificadas: 5.1, 5.2, 5.3 e 5.4.**

**Promoção (5.3) — FEITA, e reversível.** Os três `*_all.csv` foram renomeados para
`*_all_pre_gh91.csv` (rename, instantâneo, sem cópia de 6 GB) e os `*_regen.csv` copiados por
cima. Assim o `_regen` continua existindo para a entrega e os bytes do baseline continuam em
disco — não apenas como pins. Conferido por sha256: `_all.csv` e `_regen.csv` batem exatamente
nos três arquivos.

Pins novos:
`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/consolidation/manifest_results_gh91.sha256`

```
8da24e2aab7b4da342f33a312c65beeb672707a6956b83524af671563ed626e9  summary_regen.csv  (= summary_all.csv)
3cf3d47d7db99194e8f1d4dae1f5273b80e8632a80f0ba1a141a568c9588f3c5  errors_regen.csv   (= errors_all.csv)
39ec856802128ccea582d2fb72c23f05d058069c94bd6796fa813a24ff4910dc  coverage_regen.csv (= coverage_all.csv)
```

Baseline preservado (bytes em disco, não só hash):
`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/{summary,errors,coverage}_all_pre_gh91.csv`

Nota: `errors_all.csv` **encolheu** de 47 886 964 para 45 161 863 bytes. É legítimo — os valores
em forma de frame duplicavam um stack frame inteiro em duas colunas e foram substituídos pelo
split correto de `class`/`method` (§5).

**Pendentes:**

- **5.5** — montar a entrega do estágio 2 com pins sha256 e o rename de cabeçalho do 6.2;
- **4.6 (resto)** — emendar a tarefa 0.1 de
  `ase-journal/openspec/changes/remove-package-detector/tasks.md`: trocar "swap dos JSONs
  co-localizados + `rv-platform run --process-results`" por "instalar os 30 no `STATIC_DIR`
  plano + `RESULTS_ROOT=… consolidate_offline.sh`". Artefato de outra change, no outro
  repositório — **nada foi editado lá**.

---

## 8. Aprendizados que custaram tempo (não re-derivar)

- **`--process-results` LÊ o JSON co-localizado.** As duas metades da tarefa 0.1 upstream são
  coerentes entre si; a objeção é a **escolha do caminho**, não a localização do JSON. A
  armadilha real: trocar só as cópias co-localizadas e rodar o `consolidate_offline.sh` deixa a
  re-análise **sem efeito nenhum** — esse caminho lê o `STATIC_DIR`
  (`regenerate_container.py:114`) — e a saída parece perfeitamente normal.
- **Comparar duas consolidações exige neutralizar ordem e deriva de código** antes de qualquer
  conclusão (§3). Um diff direto acusa ~148 apps em `errors` e ~187 em `coverage`, e nenhum
  desses é efeito da chave.
- **A curva cumulativa não é invariante sob empate de timestamp.** Só o multiconjunto de eventos
  e o ponto final são.
- **O baseline `*_all.csv` é destruído pela promoção.** Pinar sha256 e preservar o
  `verification_report.md` **antes** de rodar foi o que manteve a 5.4 possível.

---

## 9. Artefatos produzidos (caminhos absolutos)

Scripts (rv-android):

- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/scripts/gh91_install_static.py`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/scripts/gh91_compare_consolidation.py`

Registro e provas:

- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/` — `sa_rerun_record.csv`,
  `PROVENANCE.md`, `HANDSHAKE.md`, `manifest_sa_rerun_30.sha256`,
  `manifest_static_dir_pre_install.sha256`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/baseline/` — pins e
  relatório de auditoria do baseline 2026-07-12
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/record/consolidation/` — log da
  consolidação, log da comparação, log do C4

Planilhas regeneradas:

- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/summary_regen.csv`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/errors_regen.csv`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/coverage_regen.csv`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS/verification_report.md`

Estágio 1 (já entregue, não commitado) em `ase-journal/dataset/pkgdet_validation/`:
`sa_rerun_record.csv` (+ `.sha256`), `sa_rerun_provenance.md`, `sa_rerun_handshake.md`,
`sa_rerun_manifest_30.sha256`, `sa_rerun_static_dir_pre_install.sha256`.
