#!/bin/bash
# Para cada logcat: TOTAL = linhas 'RVSEC\s*:' ; MATCH = linhas que casam o regex do consolidate_compare.py ;
# NAME = contagem por primeiro campo (token antes da vírgula).
f="$1"
G=/usr/bin/grep
t=$($G -cE '\bRVSEC[[:space:]]*:' "$f")
m=$($G -cE '\bRVSEC[[:space:]]*:[[:space:]]*[A-Za-z]+Spec,.+$' "$f")
printf '%s\tTOTAL\t-\t%s\n' "$f" "$t"
printf '%s\tMATCH\t-\t%s\n' "$f" "$m"
if [ "$t" != "0" ]; then
  $G -oE '\bRVSEC[[:space:]]*:[[:space:]]*[^,]*' "$f" | sed -E 's/^RVSEC[[:space:]]*:[[:space:]]*//' | sort | uniq -c | awk -v f="$f" '{printf "%s\tNAME\t%s\t%s\n", f, ($2==""?"<EMPTY>":$2), $1}'
fi
