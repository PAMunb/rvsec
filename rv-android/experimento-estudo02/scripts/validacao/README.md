# Detectores da validação de 14/09/2026

Scripts que produziram `experimento-estudo02/docs/20260914_validacao_execucao.md`. Todos são somente
leitura sobre `data/results/estudo02_NN/estudo02_NN/` e `data/results/estudo02_consolidado/`. Os intermediários vão para `VALIDACAO_DIR`
(padrão: diretório corrente). Ordem, a partir da raiz do `rv-android`, com nenhum container
`estudo02_*` de pé:

```bash
export VALIDACAO_DIR=/caminho/de/trabalho
find data/results/estudo02_[0-9][0-9]/estudo02_[0-9][0-9] -name '*.logcat' -print0 > $VALIDACAO_DIR/logcats.lst

# I1: linhas RVSEC por spec, contra a regex do consolidador (scan.tsv)
xargs -0 -n1 -P 40 experimento-estudo02/scripts/validacao/scan_one.sh < $VALIDACAO_DIR/logcats.lst > $VALIDACAO_DIR/scan.tsv

# G1, G2, E3, I4, matriz H4, Z3 direto; grava best.json (melhor registro por identidade)
uv run python experimento-estudo02/scripts/validacao/index_static.py

# uma passagem por logcat: linhas, RVSEC-COV, cabeçalhos, chatty, FATAL/ANR/died, maior lacuna, inversões
printf 'file\tlines\tcov\trvsec\thdr\thdrmid\tchatty\tfatal\tanr\tdied\tmaxgap_ms\tinv\tmaxinv_ms\tmidnight\tfirst\tlast\n' > $VALIDACAO_DIR/lc_stats.tsv
xargs -0 -n1 -P 40 experimento-estudo02/scripts/validacao/lc_stats.sh < $VALIDACAO_DIR/logcats.lst >> $VALIDACAO_DIR/lc_stats.tsv
uv run python experimento-estudo02/scripts/validacao/logcat_integrity.py      # L1, L2, L3, carimbos, C4 direto

# todas as linhas RVSEC, com o nome do arquivo (saída por lote: escrita concorrente num único arquivo embaralha linhas)
mkdir -p $VALIDACAO_DIR/rvparts
xargs -0 -n 40 -P 40 sh -c '/usr/bin/grep -H -E "\bRVSEC[[:space:]]*:" "$@" > '$VALIDACAO_DIR'/rvparts/$$.$RANDOM.txt' _ < $VALIDACAO_DIR/logcats.lst
cat $VALIDACAO_DIR/rvparts/*.txt > $VALIDACAO_DIR/rv_lines.txt
uv run python experimento-estudo02/scripts/validacao/violations.py           # I2, I3, I5, R3 alternativo

# inversões restritas às linhas RVSEC do próprio app, só nos arquivos com inversão
awk -F'\t' 'NR>1 && $12>0 {print $1}' $VALIDACAO_DIR/lc_stats.tsv | xargs -d '\n' -n1 -P 40 experimento-estudo02/scripts/validacao/rv_inv.sh > $VALIDACAO_DIR/rv_inv.tsv
```

Depois da regeração das tabelas (`scripts/regenerate_tables.py`) e da consolidação, os detectores
que leem tabela:

```bash
# G3, Z4, R1, R2 (com confronto contra as médias sem arredondar), R3, E2 — ~1 min
uv run python experimento-estudo02/scripts/validacao/tabelas.py

# E1: reconstrói cada identidade com o caminho do exportador e registra as não casadas dentro
# do escopo; um processo por container (~11 min cada, em paralelo), depois o veredito
for i in 00 01 02 03 04 05 06 07 08 09; do
  uv run python experimento-estudo02/scripts/validacao/e1_unmatched.py estudo02_$i > $VALIDACAO_DIR/e1_$i.log 2>&1 &
done; wait
uv run python experimento-estudo02/scripts/validacao/e1_report.py
```

`grep` aqui é o `/usr/bin/grep` do GNU: neste host o `grep` do shell é um wrapper do ugrep, com
outra sintaxe de classes de caracteres.
