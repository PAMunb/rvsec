# Verificação no corpus — o que a correção muda nos 162 artefatos

Produzido por `verify_corpus.py` sobre
`APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162` (162 `.apk.json`), com o parser
já corrigido. A coluna "antes" **não é citada de memória**: o script reexecuta o filtro apagado
(`applicationId not in className`) contra os mesmos artefatos, então a comparação é contra o que o
código antigo de fato fazia. A tabela por APK está em `corpus_verification.csv`.

**Resultado: PASS** nos três critérios do grupo 4.

## O agregado

| Medida | Antes | Depois |
|---|---:|---:|
| Classes | 110.692 | **215.430** |
| Métodos | 536.178 | **1.058.685** |
| Activities admitidas | 601 | **1.131** |

O denominador de cobertura praticamente dobra, e é isso que estava em jogo: cada classe descartada
ali era um método que a cobertura nunca poderia reportar como executado.

## Os três critérios

**4.2 — o universo analisado é o do produtor (INV-ANA-59).** Em **162 de 162** artefatos, o número
de classes que o parser carrega é exatamente `len(reachability)`. Zero divergências. O parser não
tira nem acrescenta nada ao que o GATOR escreveu.

**4.2 — as aplicações que o filtro esvaziava.** **75 de 162** mediam zero classes e zero métodos
antes; **nenhuma** continua em zero. São precisamente os builds com `applicationIdSuffix`, e o
número bate com o que a proposal declara. Nenhuma delas seria admitida pelo critério C5, de modo que
a `comp162` fecharia em n=87 em vez de n=162.

As maiores recuperações:

| APK | applicationId declarado | classes | métodos | activities |
|---|---|---:|---:|---:|
| `app.pachli_50` | `app.pachli.current` | 0 → 6.453 | 0 → 36.172 | 0 → 27 |
| `com.tk.quicksearch_65` | `com.tk.quicksearch.debug` | 0 → 6.059 | 0 → 35.563 | 0 → 6 |
| `ch.rmy.android.http_shortcuts_1104060001` | `ch.rmy.android.http_shortcuts.debug` | 0 → 7.016 | 0 → 32.548 | 0 → 10 |
| `org.totschnig.myexpenses_858` | `org.totschnig.myexpenses.debug` | 0 → 5.597 | 0 → 30.997 | 0 → 46 |
| `com.sakethh.linkora_50` | `com.sakethh.linkora.debug` | 0 → 3.958 | 0 → 20.153 | 0 → 2 |
| `eu.faircode.email_2322` | `eu.faircode.email.debug` | 0 → 3.777 | 0 → 17.250 | 0 → 20 |
| `com.owncloud.android_48000100` | `com.owncloud.android.debug` | 0 → 2.980 | 0 → 16.594 | 0 → 24 |
| `com.craxiom.networksurvey_114` | `com.craxiom.networksurvey.dev` | 0 → 3.470 | 0 → 16.579 | 0 → 1 |

**Nas 87 aplicações que já funcionavam, nada se move.** Classes idênticas antes e depois nas 87, e
activities idênticas (601 → 601). Era a previsão de D1 — o filtro de classes era comprovadamente um
no-op onde a chave concordava — e agora está medida nos dois lados, não só na contagem de classes
fora da chave.

**4.3 — a regra nova reproduz a decisão da chave (D2).** A pergunta "esta ACTIVITY é da aplicação?"
foi feita das duas formas sobre as **1.526** janelas do tipo ACTIVITY do corpus: por pertencimento a
`reachability` (a regra nova) e pela chave do produtor (a decisão antiga, reconstruída pela regra
determinística do §7.5 do handoff). **Zero divergências.** Das 1.526, **1.131 entram** e **395 são
recusadas** — activities de framework e de biblioteca que o GATOR não escopa e que inflariam o
denominador de `cov_act`.

Isso é o que sustenta manter o segundo filtro em vez de apagar os dois: ele carrega peso real, e a
regra nova o carrega pelo mesmo caminho, derivando a resposta do artefato em vez de uma chave.

## Uma nota sobre o número 1.526

O `tasks.md` (4.3) fala em "1526 activities, zero divergence". As 1.526 são a **população
examinada** — todas as janelas ACTIVITY dos 162 artefatos —, não o total admitido. Admitidas são
1.131. A concordância de 162/162 é sobre as 1.526 decisões individuais.

## Um caso previsto que não ocorre

O filtro antigo também podia **truncar** um denominador em vez de zerá-lo, quando a chave resolvida
era mais longa que a do produtor (foi o que atingiu cinco APKs da `cmp163`, §7.3 do handoff). Sob o
`App.code_package` de hoje — o applicationId declarado — esse caso **não aparece em nenhum dos 162**:
o filtro ou era inócuo (87) ou esvaziava por completo (75), nunca truncava parcialmente. O
truncamento da `cmp163` veio do `PackageDetector`, que está fora desde então.
