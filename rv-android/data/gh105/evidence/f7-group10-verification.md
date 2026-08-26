# Tarefa 10.11 — a verificação do grupo 10, item por item

**Data**: 2026-08-26 · **Monitor**: `~/tmp-gh104/verif10/monitors/` (gerado nesta tarefa a partir
de `rvsec/rvsec-mop/src/main/resources/jca_android`, 24 especificações)

Espelho da 9.18, com a mesma regra: **nada aqui fecha por código de saída** (R5/R6). Cada uma das
seis exigências que a 10.11 lista tem abaixo o artefato que a responde, e onde a exigência pedia
uma medida que ainda não existia — o vermelho-verde da asserção do G-2a — ela foi feita nesta
tarefa e não herdada.

## 1. `gh104_gates.py` sai 0 sobre o `jca_android`

```
EXIT=0   ok=true   skipped=[]
```

| portão | falhas | observação |
|---|---|---|
| G-2 | 0 | 0 órfãos crus |
| **G-2a** | **0** | as quatro linhas da 10.1 cobrindo os quatro acusadores absorvidos |
| G-2b' | 0 | |
| G-2c | 0 | |
| G-2d | 0 | |
| G-6' | 0 | |
| G-ERE | 0 | |
| G-CONF | 0 | 80 cláusulas anotadas, oráculo de valor = cópia expert fixada |
| G-PRED | 0 | **`superseded`**, com o sucessor nomeado por escrito |

`skipped` vazio importa tanto quanto o exit code: um insumo ausente não é aprovação, e um portão
que pulou não passou. O `superseded` do G-PRED é o terceiro estado que a 10.2 criou — não é skip
(skip reprova) e é o único compatível com verde. O critério é medido, nunca por nome: o conjunto lê
predicados pela `PredicateStore` e não nomeia `ExecutionContext` em arquivo nenhum (INV-INS-130),
então a comparação de identidade byte a byte contra a semente congelada não tem sítio comparável
para fazer. O trinco do `jca` continua intacto — a suíte de paridade afirma os seus 134 sítios
`ExecutionContext` e zero falhas (`test_gh104_structural_gates.py:298-299`).

Os portões que rodam fora dessa CLI, todos sobre a mesma árvore:

| portão | veredito |
|---|---|
| `gh104_mop_lint.py` | `ok: true`, `counts: {}` |
| `gh104_message_gate.py` | `ok: true`, `counts: {}` — inclui o `code-anchor`, que é o que a 10.7 mexeu |
| G-SIG | 418 checados, **0 falhas**, 7 allow-listados |
| G-FORB | 18 checados, **0 falhas**, 12 allow-listados |
| G-BIND | 854 checados, **0 falhas**, 30 allow-listados |
| G-ORDER | 14 passados, **0 falhas**, 8 allow-listados, 2 pulados declaradamente |
| `gh105_expert_ledger.py --check` | exit 0 |

Os dois pulos do G-ORDER são os dois arquivos sem regra (`IvChainJunction`, `RandomStringPassword`),
declarados e contados, como a 11.2 vai reafirmar contra o catálogo expert.

## 2. A asserção do G-2a: vermelho e verde, medidos

A 10.2 acrescentou `test_jca_android_has_no_inert_event_without_a_row`
(`tests/parity/test_gh104_structural_gates.py:414-429`) porque a suíte afirmava G-2, G-ERE, G-6',
lint, mensagem e G-CONF para este conjunto e **nunca o G-2a** — foi assim que o pytest ficou verde
enquanto a CLI estava vermelha. Uma asserção que nunca se viu falhar não é cobertura, então ela foi
posta para falhar.

**O verde** é a passagem completa da §6: a asserção está entre os 185 que passam.

**O vermelho** foi medido tirando do `gate_allowlist.csv` a linha `SecureRandomSpec.g4` e rodando
só esse teste:

```
E   AssertionError: assert [{'event': 'g...eRandomSpec'}] == []
E     Left contains one more item: {'event': 'g4', 'row': [0, 1, 2, 3], 'spec': 'SecureRandomSpec'}
tests/parity/test_gh104_structural_gates.py:429: AssertionError
1 failed in 132.25s
```

O arquivo foi restaurado na mesma passagem e conferido por sha256 —
`003ba677f7e70f8564d475930836e33eb0723c8b9884b7344599b750c74de2fa` antes e depois, árvore limpa.

**As quatro linhas são carregadas, uma a uma.** O teste sozinho só prova que *alguma* linha
importa. Sobre o mesmo monitor, quatro passagens da CLI, cada uma sem exatamente uma das quatro
linhas que a 10.1 escreveu:

| linha retirada | exit | falhas do G-2a |
|---|---|---|
| `PBEKeySpecSpec.f1` | 1 | `PBEKeySpecSpec.f1` |
| `PBEKeySpecSpec.f2` | 1 | `PBEKeySpecSpec.f2` |
| `SSLContextSpec.getDefault` | 1 | `SSLContextSpec.getDefault` |
| `SecureRandomSpec.g4` | 1 | `SecureRandomSpec.g4` |

Nenhuma sobra, nenhuma cobre a outra: as quatro são decisões distintas, cada uma com a sua razão e
a tarefa que criou a forma. É também o que faz a regra do registro valer — linha com razão vazia
não perdoa nada.

## 3. O portão do grafo de predicados depois da 10.4

```
universe: 215 .mop enumerados      findings: 0 failing, 0 allow-listed, 21 informative
  jca_android   files=24  read=24  skipped=0  sites=70
```

Zero falhando, zero perdoado. Os 21 informativos são de conjuntos que o portão relata e não
governa (`jca`, `jca_android_bug_predicate`, `generic`) — o mesmo número da 9.18, o que diz que a
refeitura de registro da 10.4 corrigiu o `predicate_graph.csv` sem mover o veredito do portão, que
é exatamente o que uma tarefa 10.A pode fazer. Restrito ao conjunto (`--sets jca_android`) o
relatório traz `0 failing, 0 allow-listed, 0 informative`: os informativos são todos de fora.

## 4. As contagens do README, re-derivadas e não lidas

A 10.11 pede que os números da 10.3 sejam **recontados pelo parser do censo**, nunca afirmados como
literal. O parser é o `error_sites` do `gh104_mop_lint.py` — o mesmo que o portão de mensagem lê — e
o `codes.csv` foi lido como CSV:

| | três argumentos | quatro argumentos | comentado | total vivo |
|---|---|---|---|---|
| `jca` (a semente) | 25 | 25 | 1 | **50** |
| `jca_android` hoje | **0** | **115** | **0** | **115** |

Bate com as três linhas da tabela do README (`data/jca_android/README.md:344-348`) e com as quatro
afirmações de prosa que a 10.3 tocou:

- **115 sítios vivos**, todos de quatro argumentos, nenhum report comentado — README `:358-364`;
- **`IvChainJunction` 14, `SignatureSpec` 11, `KeyGeneratorSpec` 8**, os três maiores
  contribuidores — README `:361-362`, re-contados arquivo a arquivo;
- **`codes.csv` com 115 linhas e 115 códigos distintos**, bijetivo com o censo — README `:420`;
  por família: `CONSTR` 41, `NOBS` 30, `ORDER` 21, `ALG` 17, `FORB` 3, `KEYSIZE` 1, `KSTYPE` 1,
  `PROTO` 1;
- **oito linhas G-ORDER** no `gate_allowlist.csv` para este conjunto — README `:501`, que a 10.3
  corrigiu de nove e que o próprio G-ORDER confirma na §1 (8 allow-listados).

O mesmo recontar dá as 12 linhas G-2a do conjunto: as oito que já existiam mais as quatro da 10.1.

## 5. Um par de arnês por tarefa que mexeu em texto de especificação

| tarefa | o que mexeu | par | veredito |
|---|---|---|---|
| 10.6 | texto de mensagem emitida (`KeyPairGeneratorSpec.mop:151`, o `exp=` reancorado na regra expert) | `harness/f7-KeyPairGeneratorSpec.md` | **`unchanged` ×8** |
| 10.7 | dois imports no `GCMParameterSpecSpec.mop` | `f7-GCMParameterSpec-imports.md` | byte-diff do monitor: **duas linhas de import, e só de posição** |
| 10.10 | nada — opção C do pesquisador | — | é registro, não par |

A 10.6 é o caso que a tarefa manda provar em vez de argumentar: editar o texto de uma mensagem
**parece** mudar o que é acusado. Não muda, porque a comparação do arnês é sobre `(evento, código)`
desde a 11.11 da gh104, e nem o evento nem o código se movem — o par mede `unchanged` nos oito
traços, com os envelopes dos dois lados escritos lado a lado para que a única diferença visível
seja o `exp='...'`. As outras sete edições da 10.6 — `GCMParameterSpecSpec`, `IvChainJunction`,
`KeyPairSpec`, `MacSpec`, `PBEKeySpecSpec`, `PBEParameterSpecSpec` e `SecretKeySpec` — são
comentário puro e não emitem nada; o que elas moveram foram sete âncoras do `codes.csv`, pelo
mesmo mecanismo da 10.7, e o portão de mensagem fecha em `{}` com as âncoras reancoradas.

A 10.7 é o inverso: o reparo é de dependência, não de comportamento, e o que prova isso é o diff
byte a byte dos dois monitores gerados pelo pipeline real — `import java.util.Arrays;` e
`import java.util.List;` mudam de **posição** no bloco (já estavam lá, contribuídos pelo
`IvChainJunction`), e as outras dezessete mil linhas são idênticas. O efeito colateral que a
tarefa registrou — duas linhas no topo do arquivo deslocam sete âncoras do `codes.csv` — está
fechado: o `code-anchor` do portão de mensagem fecha em `{}` na §1.

A 10.10 é decisão de pesquisador (`docs/20260825_dossie_decisao_10b_gh105.md` §5, opção C:
registrar e não mexer). Nenhuma linha de especificação se moveu, então não há par a commitar; o
que existe é a linha narrativa `behavioural` do registro, com o mecanismo medido e as duas
perguntas que a tarefa mandou responder antes da decisão.

## 6. O registro de divergências, e as passagens de paridade

```
gh104_divergence_record.py --check  ->  exit 0
306 hunk(s), all recorded; 26 narrative entr(ies)
```

Contra os `304 hunks / 21 narrative` da 9.18: **+2 hunks** (o import do `GCMParameterSpecSpec`,
`f4cae18baba1`, tarefa 10.7; e o título do `PBEParameterSpecSpec`, tarefa 10.6) e **+5 narrativas**
(os quatro achados comportamentais da 10.8 e a decisão da 10.10). As outras edições **re-chavearam
hunks que já existiam** — seis da 10.6 (linhas 56, 119, 126, 161, 192 e 223) e sete da 10.5
(91, 95, 96, 134, 210, 288 e 292), todas passando a citar `10.5` ou `10.6` ao lado da tarefa
original. A sétima edição de comentário da 10.6, no `IvChainJunction.mop`, não re-chaveia hunk
nenhum e por isso não aparece na lista: o arquivo é novo no sucessor e entra no registro como uma
linha só (63, espécie `junction`, "present only in the successor set"), sem hunks por dentro.
Toda linha das 10.5 e 10.8 está chaveada; a 10.5(c) — o resíduo
que o comentário do `TrustManagerFactorySpec.mop:74-78` prometia e nenhuma linha guardava — entrou
absorvida na razão do hunk `dce8a7c2dc82`, com a evidência do arnês (`f1-TrustManagerFactorySpec.md`,
traço `sunx509-no-init`, classe `removed`) citada ali dentro.

Paridade, contrato de CI, com `RVSEC_HOME`, `ANDROID_HOME` e `ANDROID_SDK_HOME` setados:

```
3 failed, 185 passed in 286.86s
```

As três falhas são as mesmas três de sempre, todas de outras frentes e nenhuma desta change:
`test_baseline_not_older_than_jar` (o baseline do gator é mais velho que o jar),
`test_repo_is_clean` (o token `reachesMop` vive todo em `modules/aperv-tool/`) e
`test_real_gator_json_parses_with_complete_true` (`parse_file()` chamado com um argumento a mais).
**Nenhuma quarta falha** — que é a propriedade pela qual a linha de base existe: o conjunto de
falhas de hoje e o de 25/08 são o mesmo, nome por nome.

Os passados subiram de 182 para 185, e a atribuição vai até onde a medida alcança: duas das três
são as asserções que a 10.2 escreveu (`test_jca_android_has_no_inert_event_without_a_row` e
`test_jca_android_gates_exit_zero_and_say_which_gate_withdrew`) — as **únicas** funções de teste
que entraram em `tests/parity/` desde o commit da 9.18, 148 antes e 150 hoje, contadas nas duas
árvores. A terceira não foi rastreada: a suíte coleta 188 itens hoje, e reproduzir a coleção da
árvore de 25/08 custaria um checkout antigo inteiro por um número que não decide nada aqui. O que
decide — que nenhuma falha nova apareceu — está medido.
