# Análise da `estudo02-20260916` — pré-requisitos para continuar

**Registrado em 21/09/2026, 09:25.** A etapa 20 do README (a análise do plano §9) **não continua
nesta sessão nem neste repositório**, e este documento diz o que falta para ela rodar em outro
lugar.

## Por que não continua aqui

A análise precisa das planilhas, e **as planilhas não viajam com o repositório**: o consolidado
fica em `data/results/estudo02-20260916_consolidado/`, e `/data/results/` está no `.gitignore`
(linha 22). Quem clonar o `rv-android` não recebe nenhuma delas.

**Decisão do Pedro em 21/09:** a análise será feita em outra sessão, no repositório
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study02-replication-package`.
**Nada foi escrito lá por esta sessão** — nem arquivo, nem diretório, nem commit.

## O que precisa estar lá antes de começar

### 1. As tabelas consolidadas (não estão no git)

`data/results/estudo02-20260916_consolidado/`, 2,4 MB em cinco arquivos, gerados em 20/09 19:26:

| arquivo | tamanho | linhas | o que é |
|---|---|---|---|
| `per_task.csv` | 2,1 MB | 16 137 | uma linha por identidade, com `category`/`admissible`/`fails` |
| `per_apk_paired.csv` | 197 KB | 489 | as unidades pareadas (163 APKs × 3 orçamentos) |
| `wilcoxon.csv` | 65 KB | 825 | 55 pares × 5 métricas × 3 orçamentos |
| `per_apk_static.csv` | 6,7 KB | 163 | a covariável `sa_methods_reaches_mop` do modelo |
| `per_tool_summary.csv` | 3,5 KB | 33 | 11 braços × 3 orçamentos |

### 2. Os veredictos de admissibilidade por identidade

Estes **estão** no git, em `docs/admissibilidade_veredictos.zip` (640 KB), com os dois JSONs —
antes e depois do reparo. O que vale para a análise é o **`admissibilidade_pos_reparo.json`**; o
outro fica só como registro da etapa. Os dois soltos continuam no disco desta máquina, fora do git.

### 3. O `errors.csv` concatenado — **não existe, e é preciso gerar**

É a lacuna mais provável de travar o desfecho por rótulos. O `consolidate_compare.py` **não produz**
um `errors.csv` consolidado: ele escreve só os cinco arquivos da tabela acima. Os `errors.csv` por
container existem — doze arquivos, **65 MB somados** em
`data/results/estudo02-20260916_NN/estudo02-20260916_NN/errors.csv` — e precisam ser concatenados,
como a `estudo02` fez ao gerar `data/results/estudo02_consolidado/errors.csv`.

### 4. O vocabulário de rótulos da gh114

`rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv`, no repositório **irmão** `rvsec`, e a
mesma cópia dentro da imagem `phtcosta/rvandroid:0.9.4` em
`/opt/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv`. Conferido em 21/09: **330
códigos** e dez rótulos distintos —

```
violation 145   not-observed 64   sequence 44   creation-unobserved 43
upstream-refused 12   creation-refused 12   platform-default 5
reuse-after-final 2   random-key-material 2   application-manager 1
```

O desfecho "violação" são os 145 com `label = violation`; os outros nove rótulos **contam-se à
parte**, e um código sem rótulo **nunca** se soma em silêncio (plano §9).

### 5. Os valores de referência do artigo (só leitura)

Os scripts da `estudo02` leem do `ase-journal` e **nunca escrevem lá** — conferido nos 15 scripts
Python daquela campanha:

- `ase-journal/data-analysis/stats/rq1_jca_stats.txt` — o modelo publicado;
- `ase-journal/dataset/results/{errors,summary}.csv` — os dados do artigo;
- `ase-journal/tabs/*.tex` — as tabelas publicadas.

**Não mexer no `ase-journal` é decisão permanente.** Ele entra como fonte congelada de comparação.

### 6. Os dois scripts, que não existem

- **Adaptação do `rq1_estudo02.py`** (`experimento-estudo02/scripts/rq1_estudo02.py`): hoje
  `N_EXPECTED = 16137` e `TABLES = ROOT/"data"/"results"/"estudo02_consolidado"` estão **fixos no
  código**, e o `N_EXPECTED` do artigo, que o `contrastes_ferramentas.py` usa, **tem de se separar**
  do da campanha. O modelo é binomial negativo, com SE por app, Holm, e `monkey` e 60 s como
  referência.
- **Desfecho por rótulos**: script a escrever, sobre o `errors.csv` concatenado cruzado com
  `codes.csv.label`.

### 7. Dependências

O `rq1_estudo02.py` importa `statsmodels`, `scipy`, `patsy` (via fórmula), `numpy` e `pandas`.

## O que tem de viajar junto com os números

Três ressalvas já apuradas nesta campanha, que qualquer leitura posterior herda:

1. **Descontinuidade declarada** (plano §2): o A1 e o crédito por elemento removem relatos, o A5
   acrescenta, o RSA passa a acusar 1024 e deixa de acusar 3072. **Uma contagem bruta desta campanha
   não é comparável à da `estudo02` por subtração.** Comparam-se leituras do modelo.
2. **As médias de `per_apk_paired.csv`, `per_tool_summary.csv` e o Wilcoxon incluem os zeros das
   categorias declaradas** — 171 zeros estruturais, 246 paradas da ferramenta e 45 lançamentos fora
   do app. É o comportamento certo, porque o artigo publicou esses mesmos zeros, mas as médias
   **não são "só admissíveis"**. As colunas `admissible`/`category` do `per_task.csv` recortam essa
   sensibilidade sem reconsolidar.
3. **Duas chaves de "maus usos únicos" convivem** e não são numericamente comparáveis: `mop_unique`
   (chave de sete partes) e `mop_unique4` (chave de quatro partes, a do artigo). Na `estudo02` a
   razão era ~2,4×. Todo número publicado tem de dizer a qual pertence.

## O que não entra no `rv-android`

Nada amarrado ao corpus — catálogo de vereditos por trecho de código, por aplicação ou por
biblioteca. Os dois scripts acima não precisam disso: trabalham sobre agregados.
