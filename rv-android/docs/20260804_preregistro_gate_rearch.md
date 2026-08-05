# Pré-registro — portão empírico da re-arquitetura do APE-RV

**Data**: 2026-08-04 · **Estado**: a congelar antes de construir o jar ·
**Escopo**: G1, G2 e G3 — a condição de merge da linha `rearch` do APE-RV
**Change**: `openspec/changes/gh97-rearch-ab-gate/` · **Issue**: #97

Este documento fixa o plano de análise **antes de qualquer resultado da perna B existir** — e, mais
que isso, antes de o próprio jar da perna B ser construído. Depois do congelamento nada aqui pode ser
alterado; toda análise não prevista abaixo é exploratória por definição e será rotulada como tal ao
ser reportada.

O congelamento é o registro do sha256 deste arquivo em `calibracao/journal.jsonl` (append-only,
INV-CAL-11) sob o estado `FREEZE-PREREGISTRO` e `iter: 2` — a campanha de calibração é a `iter: 0`, a
corrida decisiva E3 é a `iter: 1`, e esta é a terceira. O registro é o que dá o carimbo temporal
auditável. A ordem importa e é verificável de fora: a entrada `FREEZE-PREREGISTRO` deste arquivo
precede o build do jar (task 6.2), o build da imagem (6.4), o smoke (7.1) e a campanha (8.1), e todos
deixam rastro datado. Análise rodada antes desse
registro não conta como confirmatória.

**A perna A não é objeto deste pré-registro.** Ela já rodou, sob o seu próprio pré-registro
(`docs/20260730_preregistro_corrida_decisiva.md`, congelado em 2026-08-01T15:02:33Z) e está
congelada em `experimento-e3-decisiva/per_apk_paired.csv`. O que se congela aqui é a leitura da
perna B contra ela.

**Fontes dos fatos e das decisões já tomadas**: `openspec/changes/gh97-rearch-ab-gate/{proposal,
design,tasks}.md` (o desenho e as decisões D1–D9) e `docs/20260804_gh97_notas_de_trabalho.md` (o
caderno de campo — cada número abaixo foi medido nesta árvore, e a nota registra o comando). Onde
este documento e as notas divergirem, **este documento vence**: as notas continuam sendo editáveis, e
este não.

---

## 1. O que a campanha é

| | |
|---|---|
| Braços | `mop_on_llm_off` (referência) · `mop_off_llm_off` (controle) · `mop_on_llm_70` (LLM) |
| Corpus | os 40 APKs de `calibracao/subset40.txt` |
| `corpus_basis` | `subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4` |
| Repetições | 3 |
| Timeout | 1800 s por task |
| Total | 360 runs (3 braços × 40 aplicações × 3 réplicas), **10 containers** (emenda 01), ≈ 18,6 h |
| Particionamento | `filters10/batch_00.txt` … `batch_09.txt`, **4 aplicações cada** (emenda 01), mesma regra alfabética determinística; **não** byte-idênticos aos da perna A |
| Conjunto de especificações | `jca` |
| Binários | os **mesmos** APKs instrumentados da perna A (jca/dexlib2, campanha 20260706); `RV_SKIP_MONITORS`, `RV_SKIP_INSTRUMENT` e `RV_SKIP_STATIC_ANALYSIS` ligados |
| Dose LLM | `llm_percentage=0.7`, prompt `v13`, temperatura 0, `llmSnapTolerancePx=150` |
| Modelo | `Qwen/Qwen3-VL-4B-Instruct` (stock, o mesmo da perna A) |
| Semente do bootstrap | 42, B = 10.000 |
| Diretório | `experimento-rearch-aperv/` |

**O desenho é idêntico ao da perna A por exigência, não por preferência.** O valor por aplicação da
perna A é a média de três réplicas (`consolidate_cal.py:311`). Rodar uma réplica só aqui tornaria a
diferença pareada assimetricamente mais ruidosa — mais variância de um lado de uma diferença que
depois é testada contra zero. É o mecanismo por trás da falsa catástrofe de 2026-06-19, em que um
smoke não pareado de 16 aplicações exibiu −4,7 pp que, pareado a n≈70, era empate exato.

O particionamento byte-idêntico não é economia: significa que cada aplicação roda no
mesmo container-índice das duas vezes, então efeitos de container ficam pareados junto com o resto.
E os binários são os mesmos: reinstrumentar produziria APKs diferentes dos que a análise estática
descreve, quebrando tanto o join com os `.apk.json` quanto o pareamento com a perna A.

### Emenda 01 (2026-08-05, **antes** de a campanha começar) — 8 → 10 containers

**O que muda**: o particionamento passa de 8 × 5 para **10 × 4** aplicações, em `filters10/`. A regra
é a mesma — split alfabético determinístico do `subset40.txt` —, só o tamanho do bloco muda. União ==
subset, sem duplicata e sem perda, verificado na geração. Os 8 arquivos da perna A ficam intactos em
`filters/`, porque são a partição dela e portanto evidência.

**O que NÃO muda, e é o essencial**: os três braços, as 40 aplicações, as **3 réplicas**, o timeout de
**1800 s**, os 360 runs, os binários instrumentados, a dose de LLM, o modelo, a semente do bootstrap,
os desfechos, as margens e as três regras de decisão. **Nenhum elemento da grade estatística é
tocado.** O argumento do D5 — a perna A é média de três réplicas, e reduzir réplicas tornaria a
diferença pareada assimetricamente mais ruidosa — permanece integralmente satisfeito, que é a razão de
a emenda mexer em paralelismo e não em escopo.

**O que se sacrifica, dito sem atenuação**: o pareamento de efeito-de-container declarado no parágrafo
acima. Com 10 partições, uma aplicação já não roda no mesmo container-índice das duas vezes, então
variação entre containers deixa de cancelar na diferença pareada e passa a entrar como ruído não
controlado. O pareamento **por aplicação** — que é o que sustenta G1, G2 e G3 — continua intacto, e é
sobre ele que os intervalos de confiança são construídos; o efeito-de-container era um refinamento de
segunda ordem sobre ele, não o seu fundamento. A margem derivada com piso de 1,5 pp (§ das margens)
existe justamente para absorver variabilidade não controlada entre campanhas, e passa a absorver
também esta.

**Por quê**: o orçamento de relógio. Medido no smoke desta mesma campanha, o ciclo por run é de
~1857 s a 1800 s de timeout (1800 + ~12 s de flush + ~45 s de instalação/teardown). Com 8 containers
são 45 runs cada, ≈ 23,2 h; com 10 são 36 cada, ≈ 18,6 h. O host comporta: uso real medido de
**4,04 GiB** por container (o limite de 10 GiB é teto, não reserva) e ~1 núcleo ativo, contra 104 GB
livres e 64 CPUs.

**Sobre a honestidade desta emenda**: ela é registrada **antes** de a campanha rodar e antes de
qualquer desfecho existir, com entrada própria no `calibracao/journal.jsonl` e sha256 novo, ao lado do
sha256 do congelamento original — que é o mecanismo pelo qual um leitor verifica que ela não é ajuste
pós-hoc. Ela também não é corte de escopo: os 360 runs são preservados, o que é o que a decisão
registrada sobre não reduzir a corrida decisiva por prazo protege.

**Os braços**, e o que exatamente os separa:

| Braço | Papel | Preset | O que o define |
|---|---|---|---|
| `mop_on_llm_off` | referência | `mop` | substrato frontier + guia MOP ligada (`mopFrontierWeight=200`, `activityTriggerEnabled=true`) |
| `mop_off_llm_off` | **controle** | `mop` | idêntico ao anterior com os **cinco pesos MOP zerados** e o gatilho de atividade desligado |
| `mop_on_llm_70` | LLM | `llm_mop` | idêntico à referência + dose LLM de 0,7 |

**Duas coisas diferem da perna A, e ambas são o ponto.** A imagem é uma tag nova
(`0.9.3-rearch`): reconstruir `0.9.3` no lugar tornaria as duas pernas indistinguíveis por tag e
reproduziria a forma do gh71 na camada de imagem. E o jar sob teste chega por **bind-mount**, porque
o `docker/rvandroid/Dockerfile` clona `phtcosta/ape` sem `--branch` e sem pin de SHA e, no momento da
campanha, `rearch` ainda não está em merge — existem portanto **dois jars dentro do container**, e
`RUN_START.build.sha` é o único que diz qual deles rodou.

---

## 2. Proveniência das duas pernas

### A perna A — medida, completa e imutável

| Campo | Valor |
|---|---|
| Imagem | `phtcosta/rvandroid:0.9.3`, ID `sha256:b2904fdfc3ddfc81ad455abd5e5685ddc97666c9411c4d994fec9111311aedec` |
| Criada em | `2026-08-01T11:47:43-03:00`; `:latest` aponta para o **mesmo ID** |
| Jar | `ape-rv.jar` sha256 `386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69` |
| Commit do jar | `5dcf225976b26ce78d8b31dd88d7f858dad29d43` — repositório **`ape`**, branch `master`, 2026-07-31 |
| Harness na imagem | `1eed28919674a0ea496666e39f6d0fc3fa2e800f` — `PAMunb/rvsec`, branch `modules` (label `rvsec.branch`), 2026-08-01 11:26:23 -03:00 |
| CSV congelado | `experimento-e3-decisiva/per_apk_paired.csv`, sha256 `a90b34cbc0ebcd85776fd288ac94129e7a6806e8bd672efd492e3b7c779e3031`, 41 linhas |
| Execução | 2026-08-01/02, 360 runs, relatada em `docs/20260802_resultados_corrida_decisiva.md` |

O registro do `:latest` é o que torna a linha necessária: uma retag futura não deixaria rastro no ID,
e sem esta linha alguém poderia lê-la como um rebuild da perna A. O commit `5dcf2259…` vive no
repositório `ape` e **não** nesta árvore — procurá-lo aqui devolve `fatal: Not a valid object name`,
o que é o esperado.

O commit do harness foi lido da própria imagem em 2026-08-04, com ela ainda presente localmente, e é
**um segundo git sha, não o mesmo**: a camada de estágio 4 do Dockerfile clona `PAMunb/rvsec` no
momento do build, então a imagem carrega uma versão desta árvore congelada em `1eed2891`, 21 minutos
antes de a imagem ser criada. As duas pernas têm, portanto, dois shas cada — o do jar (`ape`) e o do
harness (`rvsec`) —, e é por isso que a task 6.3 exige empurrar os commits **antes** de construir a
imagem: trabalho não empurrado fica silenciosamente ausente dela.

A coluna `apk` do CSV é idêntica ao conteúdo de `calibracao/subset40.txt`, aplicação por aplicação,
sem sobra dos dois lados. É isso que autoriza a perna B a parear contra a perna A por nome de
aplicação.

### A perna B — o que se declara agora e o que só existirá depois

| Campo | Valor |
|---|---|
| Imagem | `phtcosta/rvandroid:0.9.3-rearch` — tag declarada; **ID a registrar na task 6.5** |
| Jar | build do worktree `ape-rearch`, branch `rearch`; **sha256 a registrar na task 6.2** |
| Commit do jar | o commit de `rearch` efetivamente construído; **a registrar na task 6.2** |
| Harness na imagem | branch `rearch-counterparts`, empurrado antes do build (task 6.3); **commit a registrar na task 6.5** |
| CSV a produzir | `experimento-rearch-aperv/per_apk_paired.csv` |

**Quatro valores desta tabela ainda não existem, e é deliberado que o congelamento os preceda.** O jar
não pode ser construído antes de as contrapartes `gh94` e `gh95` estarem aplicadas e de os estágios
`rearch-03`…`rearch-07` fecharem do lado do `ape`; congelar só depois disso significaria escrever o
plano já sabendo qual jar se está julgando. A ordem correta é a inversa, e é a que a lista de tasks
impõe.

**A regra que governa o preenchimento, declarada aqui para que não seja inventada depois**: os
quatro valores entram no §11 deste documento como **apêndice de fatos medidos**, com a data de
medição, e **nada mais** do documento pode ser tocado na mesma edição. Um apêndice que registra qual jar rodou
não é uma mudança do plano de análise: ele não move desfecho, margem, braço nem regra de decisão. O
sha256 congelado no journal é o do documento **sem** o apêndice, e a entrada de apêndice no journal é
separada e posterior — de modo que qualquer leitor consegue verificar que o plano precedeu o binário.

---

## 3. Os desfechos, e de onde cada número vem

Seis desfechos por braço, os mesmos da perna A, lidos das mesmas colunas e construídos pela mesma
rotina — `consolidate.py` é cópia do `consolidate_cal.py`, com **apenas** o caminho de leitura de
trace adaptado (§10).

| Desfecho | Coluna no CSV | Origem imediata |
|---|---|---|
| `cov_method` | `aperv:<braço>__cov_method` | `tasks.json` → `method_coverage` |
| `cov_act` | `aperv:<braço>__cov_act` | `tasks.json` → `activities_coverage` |
| `cov_mop` | `aperv:<braço>__cov_mop` | `tasks.json` → `methods_mop_reachable_coverage` |
| `mop_unique` | `aperv:<braço>__mop_unique` | `tasks.json` → `total_errors` |
| `mop_total` | `aperv:<braço>__mop_total` | recontagem das linhas `RVSEC` do **logcat** bruto |
| `crashes` | `aperv:<braço>__crashes` | `tasks.json` → `detected_errors_count` |

Os dois CSVs — `experimento-e3-decisiva/per_apk_paired.csv` e o desta campanha — são as **únicas**
entradas do `compare.py`. Nenhum desfecho é recomputado a partir dos resultados brutos da perna A.

**Agregação**: o valor de uma aplicação num braço é a **média das três réplicas**, que é a convenção
do CSV da perna A. Réplicas cujo run não completou não são substituídas por zero; a integridade das
tasks é portão de validade (§4), não ajuste de análise.

**O estimando, declarado porque não é o óbvio.** `stats_utils.paired_bootstrap_ci` estima a
**diferença de médias aparadas a 10%**, recomputada a cada reamostra, com reamostragem pareada por
aplicação (B = 10.000, semente 42). **Não** é a média das diferenças pareadas, e a distinção não é
acadêmica: no contraste `cov_act` da perna A a média das diferenças dá +14,006 e o estimando aparado
dá **+14,916** — que é o número publicado no relatório do E3. `stats_utils.py` é cópia byte-idêntica
justamente para que as duas pernas computem a mesma coisa, e o teste
`TestEstimandMatchesLegA::test_g2_reproduces_the_published_e3_contrast` fecha o laço reproduzindo
+14,916 [7,754; 22,039] a partir do CSV congelado.

**Unidade de pareamento**: a aplicação. Sem semente compartilhada entre braços — o pareamento é por
aplicação e não depende de trajetórias replicáveis. A única semente do plano é a do bootstrap.

**Sem exclusão de aplicação depois de ver resultado.** As 40 entram. Aplicação ausente de um dos
lados de um contraste é descartada **daquele par** (listwise) e o `n` efetivo é reportado ao lado de
cada estimativa, nunca imputada.

---

## 4. Ordem dos portões — validade antes de desfecho

Nenhum desfecho é lido antes destes portões passarem. Um portão reprovado invalida o que ele protege;
não se ajusta a análise para contorná-lo.

1. **Pre-flight, antes da campanha** (bloqueante). Sobre os traces do smoke, 3/3 braços PASS nas
   quatro checagens do §10. A campanha não começa sem isso.
2. **Controle limpo** (bloqueante). No braço `mop_off_llm_off`, `decision_source=MOP` == 0 **e** o
   campo `mop=` == 0 em todo passo, com o padrão ancorado em `(?<![a-z_])mop=` para não casar também
   a cauda de `activity_has_mop=1`. Se vazou guia MOP no controle, o G1 não mede a reescrita e a
   campanha não é lida.
3. **Jar e preset** (bloqueante). As checagens do pre-flight valem sobre a campanha inteira, por
   amostragem por braço, e não apenas sobre o smoke.
4. **Atribuição de braço** (bloqueante). O plano efetivo de cada run bate com o braço declarado,
   40/40 por braço.
5. **Integridade de tasks**. Toda task COMPLETED com cobertura > 0; runs perdidos são reportados em
   número, nunca silenciados. Contagem por **identidade distinta**, nunca por `grep COMPLETED` no
   `tasks.json` — que duplica através de `state_transitions`.

O `verify.py` roda esses portões por re-derivação independente, e só então o `consolidate.py`
produz os CSVs.

---

## 5. A regra de decisão, em três partes

### G1 (bloqueante) — a reescrita, isolada no braço de controle

Perna B contra perna A, **só no braço `mop_off_llm_off`**, pareado por aplicação (n = 40), sobre os
seis desfechos. Direção do delta: **perna B − perna A**.

Esse braço zera os cinco pesos MOP e desliga o gatilho de atividade mantendo o `mop_data` presente:
ele carrega o substrato e não pontua nada por ele. A mudança de substrato do gh96 entra em
comportamento **apenas** por `mopWeightDirect`/`mopWeightTransitive` e por `activity_has_mop`, e os
dois canais estão fechados nesse braço. Isso foi medido, não argumentado: o portão de validade 1 do
E3 estabeleceu `decision_source=MOP` == 0 e `mop=` == 0 em todo passo do braço, nas 40 aplicações. O
que se move nesse contraste é a reescrita.

**As margens, e de onde vêm.** Regra congelada:

```
margem(desfecho) = max( 1,5 pp ,  2 × SD_mediana(média de 3 réplicas, braço de controle) )
```

| Desfecho | SD da média de 3 réplicas | 2 × | Piso | **Margem** |
|---|---:|---:|---:|---:|
| `cov_method` | 0,958 | 1,916 | 1,5 | **1,92 pp** |
| `cov_act` | 0,000 | 0,000 | 1,5 | **1,50 pp** |
| `cov_mop` | 1,046 | 2,092 | 1,5 | **2,09 pp** |
| `mop_unique` | 0,000 | 0,000 | — | não bloqueia |
| `mop_total` | 3,469 | 6,938 | — | não bloqueia |
| `crashes` | 0,000 | 0,000 | — | não bloqueia |

Os dois termos têm justificativas distintas. **O piso** é o dobro do drift entre campanhas já
documentado — −0,743 pp de `cov_mop`, p = 0,0099, sem nenhuma mudança de código: um portão que
exigisse apenas "IC exclui zero" reprovaria a fusão em cima desse drift. **O fator 2 sobre a
dispersão** aplica à dispersão medida a mesma conservadoria que o piso aplica ao drift, porque a
dispersão intra-campanha é **limite inferior** da variabilidade entre campanhas: as duas pernas
rodam com dias de diferença, imagem diferente e carga de host diferente, e tomá-la como estimativa
direta subestimaria por construção.

A dispersão foi medida sobre as **mesmas definições** que a perna A usa — o script importa o
`consolidate_cal.py` em vez de reimplementá-lo — sobre 360 identidades e 120 células `(apk, braço)`,
todas com 3 réplicas.

**Três desfechos não bloqueiam, e a decisão é anterior à campanha**, não escolhida depois de ver qual
desfecho se moveu:

- **`crashes`** tem mediana 0 nos três braços da perna A e SD identicamente zero. Um IC pareado sobre
  um vetor constante em zero não decide nada, e tratá-lo como portão fabricaria veredito a partir de
  ruído.
- **`mop_unique`** ficou plano o bastante na perna A para o McNemar primário ter dado
  `n_discordante = 0` nos dois contrastes; SD mediana 0,0 entre réplicas, nível mediano 5,0.
- **`mop_total`** conta **linhas de violação**, não violações distintas — um laço que re-dispara a
  mesma violação infla o desfecho sem que a detecção tenha mudado. É o mais ruidoso dos cinco: SD
  mediana de 6,01 linhas contra nível mediano de 40,5 no braço de controle, p90 de 21,7 e uma
  aplicação com SD de 99,2. E no próprio contraste E3 entre braços que diferem **por desenho** ele
  deu +2,52 com IC95 [−2,14; 7,62], incluindo zero: um desfecho que não separa braços deliberadamente
  diferentes não vai separar uma regressão da reescrita.

Os três continuam sendo **reportados com seus ICs**, como todos os demais. O que muda é que não
bloqueiam sozinhos.

### G2 (bloqueante, unilateral) — a guia ainda guia, dentro da campanha nova

Contraste **dentro da perna B**: `mop_on_llm_off` − `mop_off_llm_off` em `cov_act`. Passa quando o
contraste **mantém o sinal positivo e seu IC95 exclui zero**. Referência da perna A: **+14,916,
IC95 [7,754; 22,039]** (`docs/20260802_resultados_corrida_decisiva.md`, contraste RQ-C1).

O G2 existe porque o G1, **por construção**, nunca exercita o escore ponderado por MOP — que é
exatamente o código que o `rearch-03-decision-pipeline` reescreveu (o lançador MOP, seus contadores,
os estágios de pontuação). O G2 fecha essa lacuna sem comparar níveis através do corte de substrato:
seus dois termos são medidos sobre o **mesmo** substrato, então ele é imune ao confundimento do §6.
Uma reescrita que quebrou a guia colapsa esse contraste na direção do zero; um substrato que
deslocou a superfície sinalizada não muda o sinal dele.

**É unilateral, e a razão está declarada antes de qualquer dado**: `cov_act` está no teto nos dois
braços guiados — mediana 100,0 e **31 das 40 aplicações exatamente em 100,0** (§7). Regressão é
detectável; melhora não é. O G2 afirma que o contraste continua positivo e com IC excluindo zero, e
**não** que ele cresceu. Um G2 lido nos dois lados prometeria detectar uma melhora que o instrumento
não tem como exibir.

### G3 (descritivo) — os níveis de operações monitoradas, ao lado do deslocamento esperado

Reporta os desfechos MOP (`cov_mop`, `mop_unique`, `mop_total`) dos dois braços guiados, perna B
contra perna A, ao lado do deslocamento de substrato calculado no host **antes** do congelamento
(§6). **Não bloqueia e não prediz direção.**

---

## 6. O confundimento de substrato — declarado antes, não descoberto depois

Esta seção existe para que nenhuma leitura posterior possa apresentar como descoberta o que já se
sabe agora.

O `gh96-mop-artifact-derivation` **mudou de propósito** a semântica do substrato de operações
monitoradas, e já está implementado nesta árvore — ou seja, ele está do lado da perna B do corte e
não tem como estar do lado da perna A. Comparar níveis de `cov_mop`, `mop_unique` ou `mop_total`
entre as duas campanhas mede, somadas, **a reescrita e uma mudança de substrato intencional**.

**A direção esperada, medida sobre as 40 aplicações do portão** (notas §3.4):

| | Widgets sinalizados | Atividades sinalizadas |
|---|---:|---:|
| Semântica antiga (perna A) | 104 | 38 |
| Semântica nova (perna B) | 159 | 49 |
| Delta | **+55 (+52,9%)** | **+11 (+28,9%)** |

O deslocamento é **concentrado, não difuso**: 36 das 40 aplicações não mudam nada. As quatro que se
movem são `de.blau.android_3404` (+41 widgets), `com.smartpack.packagemanager_79` (+10),
`com.beemdevelopment.aegis_81` (+3) e `com.owncloud.android_48000100` (+1). Em atividades
sinalizadas movem-se duas — `smartpack` de 0 para 6 e `de.blau` de 2 para 7 —, e essa é a coluna que
mais importa para o comportamento, porque `activity_has_mop` é o que arma o gatilho de atividade: a
`smartpack` rodava os braços guiados da perna A sem nenhuma orientação por atividade e na perna B
passa a ter seis.

O método foi validado antes de ser usado: os dois lados passam pelo **mesmo** `derive()`, com o lado
antigo obtido reproduzindo em memória o enriquecimento que a produção fazia, de modo que o delta
seja a mudança semântica sozinha; e, recomputado sobre o corpus fixado de 345 aplicações, ele
reproduz exatamente os totais que o gh96 registrou (3.733 antiga / 4.965 nova).

**A direção da superfície é conhecida; a direção do desfecho não é, e nenhuma magnitude é predita.**
São três os motivos, e nenhum deles é resolvível antes de rodar:

1. O gh96 **amplia** a superfície sinalizada e ao mesmo tempo **achata o ranking** entre os widgets
   sinalizados — mais alvos, cada um menos distinguível dos demais. Os dois efeitos empurram a
   exploração em sentidos opostos e não há como pesá-los sem medir.
2. Todo widget antes sinalizado **muda de camada**, de `direct` para `transitive`, e as duas entram
   no escore por pesos diferentes (`mopWeightDirect` contra `mopWeightTransitive`). A contagem acima
   não mede isso.
3. Mais sítios sinalizados não é mais detecção: o desfecho depende de a exploração alcançar os
   sítios dentro do orçamento de 1800 s, e um alvo a mais compete pelo mesmo tempo com os que já
   existiam.

Um pré-registro não deve afirmar um sinal que não consegue justificar. Por isso o **G3 é descritivo**
e por isso o **G1 se apoia no braço de controle**, onde os dois canais do substrato estão fechados —
a isolação é obtida por construção, e não por ajuste posterior.

---

## 7. Premissas declaradas

Registradas como premissas falsificáveis da campanha, não como fatos estabelecidos.

- **O teto do `cov_act`.** Medido na perna A: controle 81,50 de média e 87,99 de mediana com 18/40
  aplicações em 100,0; os dois braços guiados com mediana 100,0 e **31/40 exatamente em 100,0**.
  Consequência assimétrica, declarada antes de qualquer resultado: **regressão é detectável, melhora
  não é**. É o que torna o G2 unilateral (§5) e é também por isso que a margem do `cov_act` no G1 vem
  inteira do piso de 1,5 pp — a SD mediana entre réplicas desse desfecho é **zero** porque mais da
  metade das aplicações não varia.

- **O guarda de pegada não represava nada na perna A.** O guarda vive no jar
  (`utils/MopData.java:197`) e rejeita quando `fileSize > Runtime.maxMemory() / 6`; o gh96 o removeu.
  Se ele tivesse disparado na perna A, sua remoção inflaria a perna B por um caminho que nada tem a
  ver com a reescrita. Verificado no host, reproduzindo byte a byte o documento que a produção
  empurrava: o maior entre as 40 é de **15,50 MB** (`org.prauga.messages_8.apk`) e **0 de 40** seriam
  rejeitadas, inclusive na hipótese pessimista de heap de 128 MB (limiar 21,33 MB, 1,4× de folga) —
  menor que os ~192 MB do emulador. **Nenhuma aplicação a declarar.** A verificação teve de ser por
  tamanho porque os logcats da perna A não trazem nenhuma linha `[APE-MOP-DATA]`: ali, ausência de
  linha de rejeição não prova nada.

- **O drift entre campanhas não é controlado.** As duas pernas rodam com dias de diferença, imagem
  diferente e carga de host diferente. A margem com o piso de 1,5 pp existe exatamente para isso, e
  o resíduo — que uma margem calibrada em drift de `cov_mop` seja aplicada também aos outros
  percentuais — fica declarado aqui em vez de virar nota de rodapé depois.

- **O G1 mede a reescrita *como entregue*, telemetria incluída.** O estágio 4 grava um registro
  NDJSON por passo, e isso custa tempo de passo; menos passos em 1800 s significa menos cobertura. O
  G1 não separa as duas coisas, e é deliberado: uma condição de merge deve medir o que será fundido.
  O custo isolado da telemetria é portão do lado do `ape` (INV-SNK-13, passos por minuto), não deste.

- **Oito das 40 aplicações não são independentes.** Os seis `info.metadude.*.schedule`,
  `at.linuxtage.Eventfahrplan_1700028` e `ch.digitale_gesellschaft.winterkongress.schedule_118`
  declaram todos a mesma `mainActivity` — é uma base de código com oito empacotamentos, e seis delas
  compartilham inclusive um `.apk.json` byte-idêntico. O bootstrap pareado trata as 40 como
  independentes, então os ICs deste plano são **otimistas em precisão**. O subset permanece com as
  40 (decisão do autor na perna A, mantida aqui — trocar o corpus entre as pernas destruiria o
  pareamento, que é o ativo do portão), e a dependência fica declarada em todo IC reportado. A
  premissa é herdada da perna A, que a declarou sob o seu próprio pré-registro.

- **A perna A não é re-executável.** O gh96 já está implementado nesta árvore e o jar da perna A não
  sabe ler o artefato que o `tool.py` de hoje empurra; reproduzi-la exigiria reverter o repositório e
  manter uma segunda imagem. Toda escolha deste plano que dependesse de re-medir a linha de base está
  fora da mesa por construção, e não por preferência.

---

## 8. A regra de empate

**Empate ⇒ o portão não se opõe ao merge.** Operacionalmente: se nenhum achado bloqueante do §5
ocorrer, o veredito registrado é **"o portão não encontrou regressão"**, e não "inconclusivo".

A assimetria é deliberada e é **oposta à da perna A**, o que exige justificativa, já que o mesmo
autor congelou as duas. Na corrida decisiva o tratamento era o LLM e a guia MOP: capacidades novas,
de custo real e contínuo, cujo ônus da prova era demonstrar benefício — por isso lá o empate fazia o
algoritmo mais simples vencer. Aqui o "tratamento" é uma **re-arquitetura já justificada por outros
critérios** (os sete portões de estágio do lado do `ape`, que são de host e de JVM), e este portão
não foi convocado para mostrar que ela melhora o comportamento — nenhuma das sete mudanças promete
isso. Ele foi convocado para responder **se ela piorou**, porque nenhum dos sete portões executa o
código mudado sobre aplicações reais. Um portão que exigisse melhora rejeitaria por construção uma
reescrita corretamente neutra, que é precisamente o resultado que se espera de uma re-arquitetura
bem-feita.

O ônus da prova, portanto, é de quem alega **regressão**, e o §5 diz exatamente quanta evidência isso
exige. Em compensação, o portão não é barato de passar: G1 exige que a reescrita não afunde o braço
que a isola, e o G2 exige que a guia MOP continue funcionando dentro da campanha nova — e o G2 é
justamente o que uma reescrita quebrada reprovaria mesmo saindo ilesa do G1.

**Não há reanálise, troca de desfecho, nem aumento de n em busca de um veredito diferente.** Um
empate é resultado válido e útil, e é reportado como tal, com seus ICs e com as premissas do §7
reafirmadas. Se o G1 vier com ICs largos ao ponto de não distinguir regressão de neutralidade, isso
também é reportado — "não detectou regressão" e "não tinha como detectá-la" não são a mesma frase, e
distingui-las depois de ver o resultado seria escolha post-hoc.

---

## 9. O que conta como regressão bloqueante

**No G1, um achado bloqueante exige as duas condições abaixo, nunca uma só** — para cada um dos três
desfechos que bloqueiam (`cov_method`, `cov_act`, `cov_mop`):

1. o **IC95 exclui zero na direção danosa** — e, como todos os desfechos são "mais é melhor" e o
   delta é perna B − perna A, a direção danosa é a negativa: o teto do IC abaixo de zero
   (`ci_hi < 0`); **e**
2. **|Δ| acima da margem** do desfecho (§5): 1,92 pp para `cov_method`, 1,50 pp para `cov_act`,
   2,09 pp para `cov_mop`.

A condição danosa é verificada **no IC e não no ponto**: uma estimativa pontual negativa cujo IC
atravessa o zero é exatamente o ruído sobre o qual esta regra existe para não agir. `mop_unique`,
`mop_total` e `crashes` são reportados com IC e **não bloqueiam sozinhos**, quaisquer que sejam seus
valores.

**No G2**, o achado é bloqueante quando o contraste `mop_on_llm_off − mop_off_llm_off` em `cov_act`
**perde o sinal** (estimativa pontual ≤ 0) **ou** seu **IC95 inclui zero** (`ci_lo ≤ 0`). Aqui as
condições são alternativas e não cumulativas, e a diferença em relação ao G1 é proposital: o G1
pergunta se algo piorou o suficiente para importar, enquanto o G2 pergunta se um mecanismo
**continua existindo**. Um contraste que perdeu o sinal ou que deixou de excluir o zero já não
sustenta a afirmação de que a guia guia, e não há margem que conserte isso.

**Qualquer achado bloqueante — no G1 ou no G2 — opõe o portão ao merge da linha `rearch`.** Não há
soma, ponderação ou compensação entre desfechos: um basta. O `compare.py` implementa exatamente esta
regra e sai com código 1 quando ela dispara; o veredito humano é registrado na task 10.4 com uma
entrada `DECIDE` no `calibracao/journal.jsonl`.

O G3 **nunca** bloqueia, por mais que se mova.

---

## 10. O pre-flight, e por que ele é bloqueante

Quatro checagens sobre a **primeira linha** (`RUN_START`) de um trace por braço, executadas sobre o
smoke. A campanha não começa sem **3/3 braços PASS em todas as quatro**.

1. **`props_digest`** bate com o sha256 do `ape.properties` que o harness empurrou. Prova o
   transporte sem ambiguidade de mapeamento: o jar leu exatamente os bytes enviados.
2. **`preset` + `params`** batem com o plano declarado do braço. É a única execução que o `gh95`
   adiou para cá: sem ela, um jar anterior ao estágio 2 trataria `ape.preset` como chave desconhecida
   e colapsaria todos os braços aos defaults, com o diretório de resultados ainda carregando o nome
   do braço.
3. **`build.sha`** bate com o commit `rearch` construído. É a checagem que sustenta as outras: com
   dois jars no container, ela é o único discriminador. Uma divergência aqui é o modo de falha do
   gh71 — o jar do branch default vencendo o mount —, apanhado antes de 24 h serem gastas.
4. **`corpus_basis`** bate com o sha256 recomputado de `calibracao/subset40.txt`. Faz papel duplo, e
   por isso bloqueia em vez de só reportar: **ausente** significa que o caminho de parâmetros do DSL
   perdeu o valor antes do `ape.properties`; **divergente** significa que ele chegou carregando a
   lista errada.

Uma sutileza fixada por teste, para que a checagem 2 não reprove corridas saudáveis: uma chave
declarada **ausente** de `params` não é falha, porque o jar omite do eco toda chave que já está no
seu próprio default — e duas chaves desta campanha, `frontierBoostWeight=200` e
`activityTriggerEnabled=true`, são exatamente os defaults. O que autoriza ler ausência como "está no
default" é a checagem 1, que já provou que o jar recebeu os bytes empurrados. E, para que a checagem
não fique vazia por esse caminho, um braço em que **nenhuma** chave declarada pôde ser comparada
**reprova**.

O pre-flight é script de operador sobre trace gravado. Ele **não** vive no `tool.py` e não roda em
caminho de execução nenhum: o `run-spec` INV-RUN-03 declara o `RUN_START` write-only em nível 0, e o
`gh95` D1 repete a declaração deste lado.

**Sobre os scripts de análise**: são cópias, e os originais de `experimento-cal/scripts/` não se
tocam (INV-APV-55). A adaptação é estreita de propósito — **apenas** o caminho de leitura de trace
migra para `aperv_tool.analysis.trace_ndjson`; os caminhos de logcat e de `tasks.json`, que produzem
todo desfecho de manchete e o `per_apk_paired.csv` inteiro, ficam intactos, de modo que as duas
pernas permaneçam idênticas em coluna e em agregação. `stats_utils.py` é cópia byte-idêntica.

---

## 11. Apêndice de proveniência — a preencher depois do congelamento

Reservado para os quatro valores que ainda não existem quando este documento é congelado, sob a regra
declarada no §2: **fatos medidos, com data de medição, e nada mais do documento alterado na mesma
edição.**

| Campo | Valor | Task | Estado |
|---|---|---|---|
| Jar da perna B — sha256 | `a7eddf5a776ce20f7299911d7d9acb3a0f1342cdc1512b3e28aa00488e582a94` | 6.2 | medido 2026-08-05 |
| Jar da perna B — commit `rearch` | `9e948102875519ada533e02681fa012e1e4db937` | 6.2 | medido 2026-08-05 |
| Imagem `0.9.3-rearch` — ID | `sha256:2cc5c3aada3dd741434d78bfb38da4dd87cded80d05ab7967bbbe725e61472d7` | 6.5 | medido 2026-08-05 |
| Harness na imagem da perna B — commit | `19ae3da10d79ce40a7c3949fa40abdf60d8c5d15` | 6.5 | medido 2026-08-05 |

Notas de medição, todas de 2026-08-05, e nenhuma delas altera plano, desfecho, margem ou braço.

- O jar foi construído no worktree `ape-rearch` com o carimbo fornecido pela linha de comando e o
  `git-commit-id-maven-plugin` desligado (design D10): dentro de uma worktree o plugin carimba o HEAD
  do `master`. Conferido **antes** do deploy — `BuildInfo.GIT_SHA` lê `9e948102`, e não `c638142`.
- A imagem foi construída com `--build-arg RVSEC_BRANCH=rearch-counterparts`; o default do
  `Dockerfile` é `modules` e teria produzido uma imagem sem nenhuma das contrapartes. A imagem **não**
  foi empurrada para o registry (decisão do dono, 2026-08-05): a campanha roda neste host e o compose
  não declara `pull_policy`.
- O commit do harness foi lido de dentro da imagem, não do repositório local, e é o mesmo `19ae3da1`
  que a task 6.3 empurrou para `rearch-counterparts`.
- As tags da perna A foram relidas depois do build e continuam imóveis: `0.9.3` e `:latest` ambas em
  `sha256:b2904fdf…aedec`.
- O jar **próprio** da imagem — o que a camada clona do `master` do `ape` — hasheia
  `386ce08d…`, byte-idêntico ao jar da perna A. É a favor da checagem 3 do pre-flight: se o
  bind-mount não vencer, o container roda o jar legado, que não emite `RUN_START`, e o pre-flight
  falha na primeira leitura em vez de comparar campos.

---

## 12. Análises exploratórias

Tudo o que não estiver previsto acima é **exploratório por definição** e será rotulado como tal no
relatório de resultados (task 10.3): decomposições por canal de decisão, cortes por estrato
(Compose/View ou qualquer outro), leituras de telemetria do `tel_proxies.csv`, comparações com a
calibração ou com qualquer campanha anterior, e qualquer análise por aplicação além das quatro
nomeadas no §6.

Elas geram hipótese e não decidem nada. Em particular, **nenhuma delas pode alterar o veredito de
merge**, que sai inteiro do §5 e do §9.
