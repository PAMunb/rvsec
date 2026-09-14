# Tabelas por ferramenta — estudo02 (`jca_android`) ao lado do artigo (`jca`)

Agregação do artigo: média das 3 repetições por app; depois soma (contagens) ou média (coberturas) sobre os 163 apps. Valores da campanha vêm de `estudo02_consolidado/` (todas as 16 137 identidades, sem filtro de admissibilidade); os do artigo, de `ase-journal/tabs/*.tex`. O corpus tem 162 apps em comum; o monkey roda com `ignore_crashes/ignore_timeouts` só na campanha.

### Maus usos únicos por ferramenta e orçamento

Chave do artigo, `(apk, classe, método, spec)` por execução (`mop_unique4`). Soma sobre apps.

| ferramenta | 60 s | 180 s | 300 s | ganho 300/60 | artigo 60 | artigo 180 | artigo 300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ape | 272 | 330 | 352 | 29.7 % | 294 | 340 | 372 |
| ares | 242 | 290 | 301 | 24.3 % | 262 | 313 | 316 |
| droidbot:bfs_greedy | 219 | 302 | 320 | 46.1 % | 257 | 312 | 327 |
| droidbot:bfs_naive | 216 | 255 | 268 | 24.4 % | 249 | 279 | 290 |
| droidbot:dfs_greedy | 241 | 301 | 314 | 30.5 % | 260 | 310 | 320 |
| droidbot:dfs_naive | 222 | 257 | 262 | 18.0 % | 247 | 278 | 286 |
| droidmate | 260 | 286 | 302 | 16.1 % | 279 | 312 | 315 |
| fastbot | 248 | 265 | 298 | 20.0 % | 276 | 306 | 300 |
| humanoid | 233 | 269 | 305 | 30.9 % | 259 | 309 | 316 |
| monkey | 260 | 320 | 334 | 28.3 % | 286 | 318 | 317 |
| qtesting | 207 | 235 | 236 | 14.4 % | 232 | 250 | 256 |

### Eventos de violação por ferramenta e orçamento

Linhas `RVSEC` no logcat (`mop_total`). Soma sobre apps.

| ferramenta | 60 s | 180 s | 300 s | ganho 300/60 | artigo 60 | artigo 180 | artigo 300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ape | 1069 | 1724 | 2680 | 150.7 % | 772 | 1287 | 1943 |
| ares | 1129 | 1503 | 1773 | 57.1 % | 803 | 1061 | 1186 |
| droidbot:bfs_greedy | 613 | 1022 | 1362 | 122.0 % | 469 | 739 | 945 |
| droidbot:bfs_naive | 612 | 737 | 822 | 34.4 % | 446 | 510 | 546 |
| droidbot:dfs_greedy | 624 | 878 | 1309 | 109.9 % | 454 | 656 | 865 |
| droidbot:dfs_naive | 578 | 719 | 731 | 26.5 % | 429 | 500 | 489 |
| droidmate | 674 | 1195 | 2001 | 196.8 % | 477 | 880 | 1444 |
| fastbot | 698 | 1199 | 1711 | 145.1 % | 507 | 862 | 1281 |
| humanoid | 604 | 842 | 1127 | 86.5 % | 443 | 632 | 718 |
| monkey | 682 | 944 | 1126 | 65.0 % | 473 | 556 | 557 |
| qtesting | 1440 | 4647 | 7864 | 446.0 % | 997 | 3047 | 5363 |

### Cobertura de métodos (%)

`cov_method`, média sobre apps.

| ferramenta | 60 s | 180 s | 300 s | artigo 60 | artigo 180 | artigo 300 |
|---|---:|---:|---:|---:|---:|---:|
| ape | 22.33 | 30.01 | 32.86 | 22.29 | 30.33 | 33.06 |
| ares | 15.86 | 23.16 | 25.89 | 16.50 | 23.06 | 24.94 |
| droidbot:bfs_greedy | 16.21 | 22.23 | 24.52 | 16.35 | 22.41 | 24.60 |
| droidbot:bfs_naive | 15.43 | 20.60 | 21.98 | 15.70 | 20.91 | 22.14 |
| droidbot:dfs_greedy | 16.95 | 21.94 | 23.92 | 17.24 | 22.30 | 23.99 |
| droidbot:dfs_naive | 15.47 | 20.34 | 21.61 | 15.99 | 20.59 | 21.71 |
| droidmate | 17.85 | 24.43 | 26.69 | 17.78 | 24.32 | 25.94 |
| fastbot | 19.46 | 22.36 | 23.78 | 19.67 | 23.09 | 24.09 |
| humanoid | 16.90 | 23.57 | 26.28 | 17.39 | 23.83 | 26.11 |
| monkey | 19.46 | 25.37 | 28.49 | 20.64 | 24.37 | 22.91 |
| qtesting | 15.95 | 19.75 | 21.36 | 16.03 | 20.18 | 21.60 |

### Cobertura de métodos que alcançam diretamente API monitorada (%)

`cov_directly_reaches_target` do `summary.csv` regerado (= `cov_directly_reaches_mop` do artigo), média sobre apps.

| ferramenta | 60 s | 180 s | 300 s | artigo 60 | artigo 180 | artigo 300 |
|---|---:|---:|---:|---:|---:|---:|
| ape | 9.22 | 12.77 | 13.19 | 7.55 | 10.68 | 10.63 |
| ares | 6.78 | 10.37 | 11.48 | 5.43 | 8.25 | 8.24 |
| droidbot:bfs_greedy | 7.65 | 10.97 | 11.40 | 5.62 | 9.53 | 9.45 |
| droidbot:bfs_naive | 7.44 | 10.03 | 10.69 | 5.58 | 8.65 | 8.17 |
| droidbot:dfs_greedy | 7.84 | 10.10 | 11.47 | 5.34 | 8.86 | 9.28 |
| droidbot:dfs_naive | 7.44 | 10.18 | 9.60 | 5.79 | 8.06 | 7.15 |
| droidmate | 8.58 | 10.73 | 11.40 | 6.53 | 8.77 | 8.90 |
| fastbot | 8.51 | 9.95 | 10.74 | 8.15 | 8.36 | 8.11 |
| humanoid | 8.22 | 10.81 | 11.19 | 5.95 | 9.13 | 9.17 |
| monkey | 8.79 | 11.23 | 12.39 | 6.76 | 9.68 | 8.42 |
| qtesting | 7.86 | 10.00 | 10.52 | 6.35 | 9.53 | 9.29 |

### Maus usos únicos, chave de sete partes da campanha (sem equivalente no artigo)

`mop_unique` = `coverage_metrics.total_errors` (`class:::method:::spec:::error_type:::code:::event:::message`). Soma sobre apps. Não comparável ao artigo.

| ferramenta | 60 s | 180 s | 300 s | ganho 300/60 | artigo 60 | artigo 180 | artigo 300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ape | 662 | 782 | 841 | 27.1 % | — | — | — |
| ares | 588 | 700 | 728 | 23.7 % | — | — | — |
| droidbot:bfs_greedy | 541 | 710 | 761 | 40.8 % | — | — | — |
| droidbot:bfs_naive | 526 | 624 | 658 | 25.0 % | — | — | — |
| droidbot:dfs_greedy | 580 | 706 | 740 | 27.7 % | — | — | — |
| droidbot:dfs_naive | 530 | 625 | 639 | 20.6 % | — | — | — |
| droidmate | 628 | 689 | 727 | 15.8 % | — | — | — |
| fastbot | 606 | 645 | 713 | 17.8 % | — | — | — |
| humanoid | 575 | 666 | 724 | 25.9 % | — | — | — |
| monkey | 644 | 765 | 796 | 23.6 % | — | — | — |
| qtesting | 513 | 589 | 589 | 14.9 % | — | — | — |

