# Modelo do RQ1 com o desfecho sustentado — `estudo02`

Gerado por `experimento-estudo02/scripts/desfechos_sustentados.py`. Mesmo modelo de `rq1_estudo02.py` (NB2, alpha por ML, erros-padrão agrupados por app, Holm sobre as 10 comparações com o `monkey`); muda só o que se conta por execução.

## Os desfechos

| desfecho | maus usos | execuções com zero | apps com algum | alpha | zeros obs/esp | convergiu |
|---|---:|---:|---:|---:|---:|---|
| bruto (`mop_unique4`) | 27068 | 61.1 % | 91 | 3.80 | 1.021 | sim |
| sustentado (`mop_sustentado`) | 6278 | 82.0 % | 50 | 6.09 | 1.000 | sim |
| sustentado sem discutíveis (`mop_sustentado_sem_discutivel`) | 5899 | 82.0 % | 50 | 5.57 | 1.000 | sim |
| relevante (`mop_relevante`) | 1572 | 95.3 % | 14 | 21.31 | 1.000 | sim |

## Razões de taxa (IRR) e intervalos de 95 %

Referências: `monkey` e 60 s. `†` = rejeita H0 depois de Holm (comparações de ferramenta); `*` = p < 0,05 sem correção (orçamento e covariável).

| termo | bruto | sustentado | sustentado sem discutíveis | relevante |
|---|---|---|---|---|
| `timeout[180]` | 1.175 [1.085; 1.273] * | 1.139 [1.060; 1.225] * | 1.143 [1.061; 1.231] * | 1.066 [0.981; 1.158] |
| `timeout[300]` | 1.245 [1.132; 1.370] * | 1.209 [1.097; 1.332] * | 1.214 [1.099; 1.341] * | 1.122 [1.001; 1.259] * |
| `tool[ape]` | 1.026 [0.958; 1.098] | 1.045 [0.981; 1.113] | 1.047 [0.979; 1.121] | 1.133 [0.970; 1.323] |
| `tool[ares]` | 0.912 [0.860; 0.967] † | 0.973 [0.910; 1.040] | 0.974 [0.907; 1.045] | 0.957 [0.809; 1.131] |
| `tool[droidbot:bfs_greedy]` | 0.917 [0.840; 1.002] | 0.936 [0.852; 1.029] | 0.935 [0.846; 1.034] | 0.945 [0.787; 1.134] |
| `tool[droidbot:bfs_naive]` | 0.808 [0.704; 0.928] † | 0.883 [0.785; 0.994] | 0.880 [0.776; 0.998] | 0.952 [0.787; 1.150] |
| `tool[droidbot:dfs_greedy]` | 0.931 [0.843; 1.029] | 0.934 [0.838; 1.040] | 0.929 [0.828; 1.043] | 0.976 [0.814; 1.171] |
| `tool[droidbot:dfs_naive]` | 0.808 [0.700; 0.932] † | 0.874 [0.772; 0.989] | 0.870 [0.763; 0.992] | 0.952 [0.787; 1.150] |
| `tool[droidmate]` | 0.915 [0.811; 1.033] | 0.980 [0.894; 1.074] | 0.985 [0.893; 1.086] | 0.940 [0.772; 1.144] |
| `tool[fastbot]` | 0.890 [0.784; 1.011] | 0.935 [0.842; 1.037] | 0.924 [0.827; 1.033] | 1.010 [0.917; 1.113] |
| `tool[humanoid]` | 0.885 [0.800; 0.979] | 0.969 [0.909; 1.032] | 0.966 [0.903; 1.033] | 0.952 [0.813; 1.115] |
| `tool[qtesting]` | 0.764 [0.633; 0.922] † | 0.855 [0.734; 0.996] | 0.841 [0.716; 0.990] | 0.975 [0.823; 1.157] |
| `log(sa_methods_reaches_mop)` | 1.135 [0.987; 1.307] | 1.010 [0.811; 1.259] | 0.997 [0.803; 1.239] | 1.352 [0.940; 1.943] |

## Regra de leitura aplicada a cada desfecho contra o bruto

Uma conclusão se mantém quando a IRR fica do mesmo lado de 1 **e** cada estimativa cai dentro do intervalo da outra. Perder significância com intervalos que se sobrepõem é menos dado, não efeito diferente.

**sustentado**
- mudou de lado de 1: nenhum termo
- estimativa fora do intervalo da outra: tool[ares], tool[humanoid]
- Holm: rejeita nenhuma; perdeu tool[ares], tool[droidbot:bfs_naive], tool[droidbot:dfs_naive], tool[qtesting]; ganhou nenhuma

**sustentado sem discutíveis**
- mudou de lado de 1: log(sa_methods_reaches_mop)
- estimativa fora do intervalo da outra: tool[ares], tool[humanoid]
- Holm: rejeita nenhuma; perdeu tool[ares], tool[droidbot:bfs_naive], tool[droidbot:dfs_naive], tool[qtesting]; ganhou nenhuma

**relevante**
- mudou de lado de 1: tool[fastbot]
- estimativa fora do intervalo da outra: timeout[180], timeout[300], tool[ape], tool[droidbot:bfs_naive], tool[droidbot:dfs_naive], tool[fastbot], tool[qtesting], log(sa_methods_reaches_mop)
- Holm: rejeita nenhuma; perdeu tool[ares], tool[droidbot:bfs_naive], tool[droidbot:dfs_naive], tool[qtesting]; ganhou nenhuma

## `ape` contra cada ferramenta que não é a referência (Wald, agrupado por app, p sem correção)

| contraste | bruto | sustentado | sustentado sem discutíveis | relevante |
|---|---|---|---|---|
| ape × ares | 1.125 (p 0.0014) | 1.074 (p 0.0549) | 1.076 (p 0.0619) | 1.184 (p 0.0920) |
| ape × droidbot:bfs_greedy | 1.119 (p 0.0070) | 1.116 (p 0.0227) | 1.120 (p 0.0259) | 1.199 (p 0.0891) |
| ape × droidbot:bfs_naive | 1.269 (p 6.50e-05) | 1.183 (p 0.0062) | 1.191 (p 0.0070) | 1.191 (p 0.1023) |
| ape × droidbot:dfs_greedy | 1.102 (p 0.0222) | 1.119 (p 0.0397) | 1.127 (p 0.0378) | 1.160 (p 0.1530) |
| ape × droidbot:dfs_naive | 1.270 (p 6.88e-05) | 1.195 (p 0.0054) | 1.204 (p 0.0059) | 1.191 (p 0.1023) |
| ape × droidmate | 1.121 (p 0.0138) | 1.066 (p 0.1330) | 1.064 (p 0.1698) | 1.206 (p 0.0890) |
| ape × fastbot | 1.152 (p 0.0070) | 1.118 (p 0.0204) | 1.133 (p 0.0136) | 1.122 (p 0.1582) |
| ape × humanoid | 1.159 (p 5.77e-04) | 1.079 (p 0.0382) | 1.084 (p 0.0351) | 1.190 (p 0.0924) |
| ape × qtesting | 1.343 (p 5.25e-04) | 1.222 (p 0.0098) | 1.245 (p 0.0072) | 1.162 (p 0.1549) |

## Fração sustentada, descritiva

| tool | bruto | sustentado | fração | relevante | fração |
|---|---:|---:|---:|---:|---:|
| ape | 2863 | 632 | 0.221 | 159 | 0.056 |
| ares | 2502 | 590 | 0.236 | 141 | 0.056 |
| droidbot:bfs_greedy | 2524 | 567 | 0.225 | 140 | 0.055 |
| droidbot:bfs_naive | 2218 | 534 | 0.241 | 141 | 0.064 |
| droidbot:dfs_greedy | 2566 | 565 | 0.220 | 143 | 0.056 |
| droidbot:dfs_naive | 2222 | 528 | 0.238 | 141 | 0.063 |
| droidmate | 2545 | 592 | 0.233 | 140 | 0.055 |
| fastbot | 2435 | 564 | 0.232 | 145 | 0.060 |
| humanoid | 2419 | 586 | 0.242 | 139 | 0.057 |
| monkey | 2741 | 605 | 0.221 | 141 | 0.051 |
| qtesting | 2033 | 515 | 0.253 | 142 | 0.070 |

| timeout | bruto | sustentado | fração | relevante | fração |
|---|---:|---:|---:|---:|---:|
| 60 | 7858 | 1874 | 0.238 | 501 | 0.064 |
| 180 | 9331 | 2136 | 0.229 | 525 | 0.056 |
| 300 | 9879 | 2268 | 0.230 | 546 | 0.055 |

