# Tarefa 9.18 — a verificação do grupo 9, e as duas coisas que ela achou

**Data**: 2026-08-25 · **Monitor**: `results/gh51_e2e_test/monitors/` (regenerado nesta tarefa)

A 9.18 não fecha por exit code (R5/R6). O que segue é o que foi inspecionado, com o que cada
exigência da tarefa responde hoje — inclusive as duas coisas que estavam vermelhas e que só a
verificação encontrou.

## 1. As suítes de portão sobre o conjunto reparado

| portão | veredito | escopo |
|---|---|---|
| G-SIG | 418 checked, **0 failed**, 7 allow-listed | universo |
| G-FORB | 18 checked, **0 failed**, 12 allow-listed | universo |
| G-BIND | 854 checked, **0 failed**, 30 allow-listed | universo (estendido na 9.11) |
| `gh104_mop_lint.py` | `ok: true` | `jca_android` |
| `gh104_message_gate.py` | `ok: true` | `jca_android` contra api30 |
| G-ORDER | 14 passed, **0 failed**, 8 allow-listed | 215 especificações |
| G-PRED-GRAPH | **0 failing**, 0 allow-listed, 21 informativos | universo |
| G-CONF | **0 failures** | `jca_android` — ver §4 |
| G-PARAM | 24 passed, **0 failed**, 0 skipped | `jca_android` — ver §3 |

Os três achados vivos de G-BIND (`HMACParameterSpecSpec.c`, `RandomStringPassword.vo`/`gb`)
continuam allow-listados com razão medida, como o bloco decidiu: o primeiro é sobre uma classe
ausente do android-30, o segundo sobre uma spec sem `@fail` e com `@match` vazio.

## 2. O registro de divergências

```
gh104_divergence_record.py --check  ->  exit 0
304 hunk(s), all recorded; 21 narrative entr(ies)
```

Todo hunk do 9.A e do 9.B está keyed. Os dois hunks da 9.11 são o `automaton` (o `ere` opcional,
com a divisão dos dois oráculos escrita na própria linha) e o `placement` (o reparo de ligação do
`c1`), ambos com `9.11` na coluna de tarefa.

## 3. O G-PARAM lia um monitor de abril, e regenerar não é um comando

Os três achados que o G-PARAM trazia — `CipherInputStreamSpec`, `CipherOutputStreamSpec`,
`KeyStoreSpec` — eram exatamente os arquivos cujo cabeçalho as tarefas 9.14 e 9.15 mudaram. Não
eram defeito: o portão comparava as specs de hoje com `.rvm` de 20/04.

`results/gh51_e2e_test/monitors/` **não é rastreado** (`/results/` está no `.gitignore`), e a
armadilha ao regenerá-lo merece registro porque custou uma passagem inteira:

- `rv-monitor-generator generate` **apaga os `.rvm`** depois que o rv-monitor os consome
  (`runtime_verification_generator.py`, `_execute_rvmonitor`, `delete_files_by_extension`). O
  `.rvm` é justamente o que o G-PARAM lê. Regenerar só pelo gerador deixa o portão comparando
  **nada** — e ele acusa isso com exit 2 e a frase "compared no specification at all", que é a
  forma certa: um portão que comparou zero não passou.
- Os `.rvm` vêm de rodar o javamop direto — `javamop -d <out> -merge <specs>/*.mop` — que os
  escreve **ao lado dos `.mop`**, não no `-d`. Por isso a corrida foi feita sobre uma cópia do
  conjunto num scratch: rodar na árvore viva deixaria 24 `.rvm` dentro do diretório de
  especificações.

Regenerado assim, o G-PARAM lê **24 de 24, nenhum pulado**. O teste de paridade foi apertado junto:
era `23 comparados + 1 pulado` (o `IvChainJunction.mop` é arquivo desta change e abril não tinha
`.rvm` dele), agora afirma lista de pulados **vazia** — a forma mais forte da mesma promessa.

## 4. O G-CONF estava vermelho, e a causa era a 9.17

Uma cláusula sem lastro: `SSLContext.crysl:29`, `protocol in {"TLSv1.2","TLSv1.3"}`, veredito
`CRYSL-NAO-IMPLEMENTADO`. O veredito era falso — a cláusula está em `SSLContextSpec.mop:195` — e a
causa é que a 9.17 tirou do `g2` a guarda que o casador do portão lia, deixando a lista num evento
(`init`) que não liga o objeto `protocol`.

O diagnóstico inteiro, a alternativa recusada e a extensão do `_list_guarding` estão na evidência
da tarefa que causou o efeito: `f6-SSLContextSpec-g2-guard.md`, seção "O segundo resíduo". Medida
sobre as 80 cláusulas, a extensão move uma linha e só ela.

## 5. Um par de arnês por tarefa de spec

Onze evidências `f6-*.md`. Os nove pares do 9.B, com o da 9.11 refeito nesta tarefa:

| tarefa | par | veredito |
|---|---|---|
| 9.17 | `pair-917` | `moved` ×1 |
| 9.14 | `pair-914` | `removed` ×1 |
| 9.16 | `pair-916` | `removed` ×1, `moved` ×1 |
| 9.9 | `pair-909` | `introduced` ×2 |
| 9.1 | `pair-901` | `moved` ×1 |
| 9.13 | `pair-913` | `moved` ×2 |
| 9.11 | **`pair-911b`** | `removed` ×5 |
| 9.15 | `pair-915` | `removed` ×1 |
| 9.10 | `pair-910` | `moved` ×3 |

Uma correção que a conferência dos JSON produziu: a nota de decisão da 9.15 dizia que o par leria
`unchanged` "por construção", já que a massa medida é 0 linhas de 97.018. O par medido lê
`removed` ×1. Não há contradição — a massa é do corpus da campanha, e o delta é do arnês, onde um
trace de dois streams entrelaçados foi escrito para o caso justamente porque os 159 traces
originais não o exercitavam. A previsão da nota valia para o corpus; o par mede outra coisa.

As tarefas sem par são as que a própria 9.18 isenta: 9.5 (javadoc), 9.6 (artefato OpenSpec), 9.8
(registro sem efeito de veredito), 9.12 (higiene de registro) e 9.19 (recomputo de registro). O par
da 9.2 está commitado com o veredito `unchanged` medido e a inspeção de monitor que a tarefa pede.

## 6. Paridade

`uv run pytest tests/parity/ --import-mode=importlib -o "addopts="` com `RVSEC_HOME`,
`ANDROID_HOME` e `ANDROID_SDK_HOME` setados. Sem o `ANDROID_SDK_HOME` sete testes **erram** em vez
de falhar, e o erro (`KeyError: 'ANDROID_SDK_HOME'` dentro do `lib/gator/gator`) esconde o que eles
teriam dito.

Falhas que **não** são desta change, atribuídas:

- `test_no_legacy_mop::test_repo_is_clean` — o token `reachesMop` vive todo em
  `modules/aperv-tool/`, trabalho de outra sessão, que tem o próprio `check_no_legacy_mop.py` e o
  próprio teste modificados na árvore.
- `test_sentinel_emission::test_real_gator_json_parses_with_complete_true` — o teste chama
  `StaticAnalysisParser.parse_file()` com dois argumentos posicionais e o método declara um
  (`static_analysis_parser.py:205`). O arquivo de teste está modificado na árvore pela outra sessão;
  nada desta change toca o `rv-static-analysis`.
- `test_baseline_freshness::test_baseline_not_older_than_jar` — o baseline do gator é mais velho que
  o jar.

Com essas três, a suíte fecha **182 passed**.
