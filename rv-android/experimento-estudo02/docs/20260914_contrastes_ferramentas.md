# Contrastes entre ferramentas: artigo (`jca`) × estudo02 (`jca_android`)

Mesmo modelo nos dois lados (NB2, `mop_unique4 ~ C(timeout) + C(tool) + log(sa_methods_reaches_mop)`, erros robustos por APK). O ajuste do artigo foi refeito dos dados publicados e reproduz os IRRs de `rq1_jca_stats.txt` (maior diferença 4.9e-05). Cada linha é a razão de taxas `a ÷ b` com teste de Wald; Holm sobre os 55 pares, separadamente em cada campanha. Gerado por `scripts/contrastes_ferramentas.py`.

- pares significativos após Holm: artigo 5, estudo02 4, nos dois 4
- pares que mudam de direção (IRR de um lado de 1 para o outro): 4, todos sem significância nos dois lados
- pares com `monkey`: 10 de 55

## Pares sem `monkey`, significativos após Holm em pelo menos uma campanha

| a | b | artigo IRR | p | Holm | estudo02 IRR | p | Holm |
|---|---|---:|---:|---:|---:|---:|---:|
| ape | droidbot:dfs_naive | 1.225 | 1.96e-05 | 0.0011 | 1.270 | 6.88e-05 | 0.0037 |
| ape | ares | 1.122 | 2.20e-05 | 0.0012 | 1.125 | 0.0014 | 0.0698 |
| ape | droidbot:bfs_naive | 1.215 | 2.71e-05 | 0.0014 | 1.269 | 6.50e-05 | 0.0036 |
| ape | qtesting | 1.311 | 2.26e-04 | 0.0117 | 1.343 | 5.25e-04 | 0.0278 |
| ape | humanoid | 1.127 | 3.20e-04 | 0.0163 | 1.159 | 5.77e-04 | 0.0300 |

## Pares com `monkey`

| a | b | artigo IRR | p | Holm | estudo02 IRR | p | Holm |
|---|---|---:|---:|---:|---:|---:|---:|
| ape | monkey | 1.078 | 0.0022 | 0.1015 | 1.026 | 0.4594 | 1.0000 |
| monkey | droidbot:dfs_naive | 1.136 | 0.0043 | 0.1907 | 1.238 | 0.0035 | 0.1628 |
| monkey | droidbot:bfs_naive | 1.127 | 0.0057 | 0.2434 | 1.237 | 0.0024 | 0.1149 |
| monkey | qtesting | 1.216 | 0.0101 | 0.3757 | 1.309 | 0.0051 | 0.2273 |
| monkey | ares | 1.040 | 0.1885 | 1.0000 | 1.097 | 0.0021 | 0.0989 |
| monkey | humanoid | 1.045 | 0.1974 | 1.0000 | 1.130 | 0.0182 | 0.6909 |
| monkey | droidbot:dfs_greedy | 1.042 | 0.2313 | 1.0000 | 1.074 | 0.1632 | 1.0000 |
| monkey | droidbot:bfs_greedy | 1.035 | 0.2745 | 1.0000 | 1.090 | 0.0541 | 1.0000 |
| monkey | fastbot | 1.043 | 0.3463 | 1.0000 | 1.123 | 0.0735 | 1.0000 |
| monkey | droidmate | 1.026 | 0.5097 | 1.0000 | 1.093 | 0.1524 | 1.0000 |

## Pares sem `monkey`, sem significância após Holm em nenhuma campanha

| a | b | artigo IRR | p | Holm | estudo02 IRR | p | Holm |
|---|---|---:|---:|---:|---:|---:|---:|
| ape | droidbot:dfs_greedy | 1.123 | 0.0011 | 0.0560 | 1.102 | 0.0222 | 0.8006 |
| ape | droidmate | 1.106 | 0.0013 | 0.0631 | 1.121 | 0.0138 | 0.5515 |
| ape | droidbot:bfs_greedy | 1.115 | 0.0018 | 0.0845 | 1.119 | 0.0070 | 0.3000 |
| humanoid | droidbot:dfs_naive | 1.087 | 0.0021 | 0.1005 | 1.096 | 0.0407 | 1.0000 |
| humanoid | droidbot:bfs_naive | 1.078 | 0.0030 | 0.1371 | 1.095 | 0.0223 | 0.8006 |
| fastbot | droidbot:dfs_naive | 1.090 | 0.0057 | 0.2434 | 1.102 | 0.0018 | 0.0878 |
| droidbot:bfs_greedy | droidbot:dfs_naive | 1.098 | 0.0072 | 0.2936 | 1.135 | 0.0323 | 0.9986 |
| ape | fastbot | 1.124 | 0.0074 | 0.2976 | 1.152 | 0.0070 | 0.3000 |
| fastbot | droidbot:bfs_naive | 1.081 | 0.0088 | 0.3423 | 1.102 | 0.0012 | 0.0603 |
| droidbot:bfs_greedy | droidbot:bfs_naive | 1.090 | 0.0099 | 0.3757 | 1.135 | 0.0272 | 0.9245 |
| droidbot:dfs_greedy | droidbot:dfs_naive | 1.091 | 0.0108 | 0.3905 | 1.153 | 0.0155 | 0.6061 |
| droidmate | droidbot:dfs_naive | 1.107 | 0.0117 | 0.4084 | 1.133 | 0.0067 | 0.2946 |
| droidmate | droidbot:bfs_naive | 1.098 | 0.0175 | 0.5951 | 1.132 | 0.0083 | 0.3394 |
| droidbot:dfs_greedy | droidbot:bfs_naive | 1.082 | 0.0177 | 0.5951 | 1.152 | 0.0187 | 0.6930 |
| droidbot:bfs_greedy | qtesting | 1.176 | 0.0191 | 0.6107 | 1.200 | 0.0401 | 1.0000 |
| droidmate | qtesting | 1.185 | 0.0202 | 0.6274 | 1.198 | 0.0273 | 0.9245 |
| fastbot | qtesting | 1.166 | 0.0215 | 0.6460 | 1.165 | 0.0322 | 0.9986 |
| droidbot:dfs_greedy | qtesting | 1.167 | 0.0241 | 0.7001 | 1.219 | 0.0277 | 0.9245 |
| ares | qtesting | 1.169 | 0.0255 | 0.7150 | 1.193 | 0.0444 | 1.0000 |
| humanoid | qtesting | 1.163 | 0.0256 | 0.7150 | 1.159 | 0.0593 | 1.0000 |
| ares | droidbot:dfs_naive | 1.092 | 0.0288 | 0.7494 | 1.129 | 0.0440 | 1.0000 |
| ares | droidbot:bfs_naive | 1.083 | 0.0470 | 1.0000 | 1.128 | 0.0369 | 1.0000 |
| droidbot:bfs_naive | qtesting | 1.079 | 0.2314 | 1.0000 | 1.058 | 0.4209 | 1.0000 |
| droidbot:dfs_naive | qtesting | 1.070 | 0.2825 | 1.0000 | 1.057 | 0.4284 | 1.0000 |
| droidbot:bfs_naive | droidbot:dfs_naive | 1.008 | 0.4797 | 1.0000 | 1.001 | 0.9606 | 1.0000 |
| droidmate | humanoid | 1.019 | 0.5010 | 1.0000 | 1.034 | 0.4435 | 1.0000 |
| droidbot:bfs_greedy | droidbot:dfs_greedy | 1.007 | 0.6596 | 1.0000 | 0.985 | 0.5064 | 1.0000 |
| droidmate | ares | 1.014 | 0.7009 | 1.0000 | 1.004 | 0.9489 | 1.0000 |
| droidmate | fastbot | 1.016 | 0.7223 | 1.0000 | 1.028 | 0.5516 | 1.0000 |
| droidmate | droidbot:dfs_greedy | 1.015 | 0.7368 | 1.0000 | 0.983 | 0.7843 | 1.0000 |
| droidbot:bfs_greedy | humanoid | 1.010 | 0.7395 | 1.0000 | 1.036 | 0.3952 | 1.0000 |
| droidbot:bfs_greedy | fastbot | 1.008 | 0.8285 | 1.0000 | 1.030 | 0.6080 | 1.0000 |
| droidbot:bfs_greedy | ares | 1.006 | 0.8471 | 1.0000 | 1.006 | 0.8725 | 1.0000 |
| droidmate | droidbot:bfs_greedy | 1.008 | 0.8547 | 1.0000 | 0.998 | 0.9742 | 1.0000 |
| ares | humanoid | 1.005 | 0.8741 | 1.0000 | 1.030 | 0.4719 | 1.0000 |
| droidbot:dfs_greedy | humanoid | 1.003 | 0.9149 | 1.0000 | 1.052 | 0.2749 | 1.0000 |
| fastbot | humanoid | 1.003 | 0.9339 | 1.0000 | 1.006 | 0.8822 | 1.0000 |
| ares | droidbot:dfs_greedy | 1.002 | 0.9543 | 1.0000 | 0.979 | 0.5899 | 1.0000 |
| ares | fastbot | 1.002 | 0.9573 | 1.0000 | 1.024 | 0.6813 | 1.0000 |
| droidbot:dfs_greedy | fastbot | 1.001 | 0.9818 | 1.0000 | 1.046 | 0.4402 | 1.0000 |

