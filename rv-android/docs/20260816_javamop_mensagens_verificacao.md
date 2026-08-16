# Verificação adversarial da linhagem de análises sobre mensagens JavaMOP

**Data:** 2026-08-16
**Natureza:** quarta sessão sobre a linhagem, e a primeira que a audita **de fora**. Nada foi
implementado, nenhuma change foi criada, nenhuma issue foi aberta, nenhum emulador foi tocado.
Nenhuma decisão de pesquisador foi tomada aqui.
**Alvo:** os quinze documentos de `docs/20260815_javamop_mensagens*` + `docs/20260815_javamop_extracao/`
+ `docs/20260816_javamop_mensagens_correcao_handoff_prompt.md` — 9.032 linhas — e as afirmações que
eles fazem sobre o código, os dados e o trabalho anterior.

**Método.** Oito subagentes com recortes disjuntos, todos sob ordem de **medição cega** (medir
primeiro no artefato, comparar com o documento depois) e **leitura integral, nunca amostragem**;
mais medições próprias de arbitragem, marcadas **[arbitrado aqui]**. Onde um subagente e um
documento divergiram, quem decidiu foi o artefato. Onde dois subagentes divergiram, idem.
**Uma conclusão de subagente e duas hipóteses minhas foram derrubadas por medição própria e estão
registradas na §10** — a do subagente teria declarado a etapa 1 inviável.

---

## 1. Veredito

**O núcleo numérico reproduz. O aparato de atribuição causal não. E o problema mais caro não é
nenhum dos que a linhagem diagnostica: é que ela redescobriu, com menos precisão e sem citar,
trabalho que já estava medido, decidido e commitado no repositório desde 2026-08-08.**

Três frases para resumir:

1. **Aritmética sólida.** Das grandezas que remedi, praticamente todas reproduzem exatamente —
   inclusive as mais improváveis, como `5.892 = 3.552 + 1.915 + 424 + 1`. A linhagem não inventa
   números.
2. **Atribuição frágil.** Onde ela diz *"esta causa explica estas N linhas"*, o registro
   frequentemente não tem como sustentar a frase — porque o `@fail` não nomeia o evento que o
   disparou, e portanto o `errors.csv` não separa causas concorrentes. Isso não é descuido de quem
   contou: é o defeito que o trabalho existe para corrigir, aplicado a ele mesmo.
3. **Redescoberta.** `data/gh101/frozen_set_debt.md` (250 l.) e
   `openspec/changes/gh101-jca-spec-conformance/design.md` (decisão **D-S9**) já contêm os 18 eventos
   órfãos com lista nominal, a "Forma B" nomeada e escopada em **treze** especificações, o reparo que
   a sessão 3 propõe como gate **considerado e rejeitado com razões escritas**, a declaração
   explícita de que o `INV-INS-110` **não** cobre isso, e a atribuição correta do `but found .` — que
   a sessão 3 contradiz sem citar.

E há uma quarta, que só aparece quando se olha a gh100 e a gh101 como objetos e não como fontes:
**a lacuna real do programa não é gate nenhum dos que a linhagem propõe.** Os oito gates de C-V
medem propriedades **estáticas** de artefatos. As duas changes já repararam com evidência estática,
declararam por escrito que era insuficiente — a gh100 pôs V4 (re-executar o corpus) fora de escopo,
a gh101 pôs "re-measuring the corpus" nos não-objetivos — e **as duas produziram um reparo que
deslocou o defeito em vez de removê-lo**: a gh100 trocou "um advice perdido" por "advices demais"
(que é a mudança C-1a), a gh101 trocou Forma A por Forma B. O que falta, e continua faltando em
todo o plano, é um **instrumento diferencial**: comparar comportamento antes e depois do reparo
sobre o mesmo insumo. G-2b e G-7a são mais gates estáticos; não resolvem isso.

A conclusão operacional da sessão 3 ("o documento está pronto para virar issues depois das
correções") **continua de pé**, mas a lista de correções muda de conteúdo, não só de tamanho: pelo
menos **quatro** das vinte correções prescritas estão erradas ou mal dirigidas, incluindo a que a
própria linhagem classifica como *"a mais barata com maior efeito a jusante"*.

E há uma boa notícia que a linhagem não vê: **a etapa 1 — ajustar as mensagens das specs — é mais
barata e mecanicamente mais sólida do que os documentos supõem.** Ver §9.

---

## 2. Cronologia, que é ela própria um achado

`docs/` recebeu 21 arquivos em 2026-08-15:

| hora | arquivo |
|---|---|
| 13:49 | `20260815_gh103_sessao2_handoff_prompt.md` — gh103 em 7/49 tarefas |
| 16:16 | `20260815_gh103_analysis_layer.md` — a camada de análise, concluída e arquivada |
| **16:24** | `20260815_javamop_mensagens.md` — **o plano** |
| 18:24–18:55 | encomenda e entrega da revisão adversarial |
| 19:14–20:02 | prompt e as quatro validações externas |
| 20:26 | `_FINAL.md` — o documento de design |
| 21:08–21:11 | sessão 1 e a encomenda da sessão 2 |
| 22:04–22:14 | as quatro listas de extração e a sessão 2 |
| 22:28–23:44 | encomenda e entrega da sessão 3 |
| 00:57 (16/08) | o handoff de correção |

**A linhagem inteira — 9.032 linhas, "três sessões", quatro validações externas — foi produzida em
7 h 20 min de uma noite.** Isso explica mecanicamente a patologia da §4: ninguém teve tempo de abrir
`data/gh101/`, que são 955 linhas de trabalho anterior commitado sobre exatamente o mesmo objeto.

Os dois documentos daquele dia que **não** são da linhagem são, ironicamente, os mais relevantes ao
plano. `20260815_gh103_analysis_layer.md`, escrito **oito minutos antes de o plano começar**,
documenta a camada `aperv_tool.analysis` da gh103 — offline, genérica, com `violations` já como
leitor de camada 3 — e contém três frases que decidem coisas que a linhagem passou a noite
redescobrindo mal:

> **"cmp162 is a fixture, not a corpus. No number computed on it answers a research question."**

> **"Every number leaves with its envelope... A fraction whose denominator nobody wrote down is
> unreadable."**

> **"Reproducing a campaign's number proves the pipeline is unchanged. It proves nothing whatever
> about whether the estimator is right — if the original was wrong, parity reproduces the error
> exactly."**

Toda percentagem da linhagem é calculada sobre o comp162. E a terceira frase derruba o veredito de
manchete da sessão 3: *"de vinte grandezas remedidas, dezessete reproduzem"* é uma afirmação de
**paridade** apresentada como afirmação de **correção**. A distinção estava escrita no mesmo
diretório, na mesma tarde.

---

## 3. O que se confirma

Medido de forma independente e cega. Denominador declarado em todos os casos.

| Grandeza | Documento | Medido |
|---|---|---|
| dataset do artigo | 97.018 linhas / 19 mensagens / 70.760 `unknown` = 72,93 % | idem (72,9349 %) |
| colunas do dataset do artigo | — | **10 colunas, sem `source`** |
| comp162 | 19.664 / 15.714 mudas / 79,91 % / 16 mensagens / 11 colunas | idem, 8 arquivos |
| partição de sítios (comp162) | 296 = 101 + 12 + 183 sítios; 3.950 + 838 + 10.926 linhas | idem |
| gêmeas = legíveis | 3.950 = 3.950; zero sítios só-legíveis | idem |
| "registro que não deveria existir" | 4.788 = 30,5 % | 4.788 / 15.714 = 30,4696 % |
| `UnsafeAlgorithm` → MD5/SHA-1 | 15.444 → 6.048 → 5.892 → 38,15 % | idem, incluindo a única linha `but found SHA.` |
| repetição de identidade | 6.344 identidades, 67,74 %, máx 49 | idem, sob `(apk, rep, tool, spec, class, method, source, message)` |
| linhas com número de linha | 100 % | 19.664 / 19.664; zero `:0` |
| eventos órfãos | `jca` 18 em 10 specs; pós-gh101 = 0 | idem, lista nominal, nos quatro oráculos |
| slice-raiz | 26 de 134 eventos em 10 specs; 21 de 140 pós-gh101 | idem, por duas derivações |
| conjuntos `.mop` | 23 / 23 / 118 / 27 = 191; `addError` 21/21/0/0; `Log.v` 0/0/118/27 | idem |
| AWT/Swing no `generic` | 32 dos 118 | idem (o plano conta 34, incluindo `java.beans`) |
| `@fail` sem `__RESET` | 21 blocos em cada conjunto, **exatamente 1** sem, o mesmo arquivo | idem (`jca:110`, `jca_android:137`) |
| `ErrorDescription` no `jca` | 51 = 25 de 3 args + 26 de 4 args | idem (1 dos de 4 args está comentado) |
| grafo de predicados | 21 escritas / 49 sítios; 4 lidas / 27 sítios; interseção 3; 35/49 = 71 % | idem; reconcilia com "23 propriedades, 18 sem leitor, 1 sem produtor" |
| divergência entre conjuntos | 19 de 23 specs, 882 linhas | idem |
| `CipherSpec` | 17/17 eventos, o teto do `INV-INS-115` | idem |
| campanhas | 63 manifestos, todos `"jca"`; nenhum `errors.csv` com spec `FSM*` | idem (784 `errors.csv`, 17 nomes de spec, todos JCA) |
| invariantes | spec principal para em INV-INS-103; 109 e 110 duplos; primeiro livre 116 | idem; **35** citações dentro das duas changes, 204 na árvore |
| changes | gh100 3/58 abertas; gh101 84/84; gh102 28/28; primeiro `gh` livre = 104 | idem (gh102 é 26/28 em HEAD; 28/28 só na working tree) |
| listas de extração | 581 = 193+202+113+73 = 450+70+61 | idem, contado linha a linha |

Também confirmado, e importante para a etapa 1: **o corpo do evento roda antes da transição.**
Verificado exaustivamente nos quatro monitores gerados — 134/134 e 140/140 métodos, **zero
anomalias**, nas duas formas de monitor. Ver §9.

---

## 4. A gh100 e a gh101: o que já estava feito, e o que elas próprias erraram

### 4.1 A linhagem redescobriu trabalho já commitado

Este é o item que mais muda o trabalho, e nenhum documento da linhagem o registra.

`data/gh101/frozen_set_debt.md` está no repositório desde **2026-08-08** — uma semana antes de a
linhagem começar. É citado como *fonte* na tabela `_analise.md:782` e no prompt das validações
externas (`_validacao_prompt.md:130`), e **não foi lido**. Ele contém:

**Os 18 eventos órfãos do `jca`.** `frozen_set_debt.md:69-101`: *"Generating monitors from both sets
and reading the transition tables gives the exact count: **the frozen set has 18 such events**, not
the two the change originally named. `scripts/gh101_monitor_transition_check.py` is the check."*
Segue a lista nominal — que é **byte-a-byte a mesma** que a sessão 2 publica em `_lacunas.md:628` como
escopo de reparo de `jca_v2`. A sessão 1 apresenta esses 18 como o seu achado de manchete
(*"o documento nunca tinha registrado isso"*), e o handoff §9 generaliza: *"a sessão 1 achou os 18
órfãos rodando o G-2 que o documento propunha como gate futuro e **nunca tinha aplicado ao conjunto
em produção**"*. Tinha: o script existe, o teste de paridade existe
(`tests/parity/test_gh101_specset_gates.py`), e o resultado está commitado.

**A "Forma B", nomeada, escopada e com o reparo rejeitado.** `frozen_set_debt.md:222-250`, seção
*"The residue both sets keep: a violating branch does not absorb what follows it (task 3b.11b)"*:

> *"Giving a violating event a place in the automaton stops it accusing on its own call. It does not
> make the state it lands in accept the calls that legitimately follow. […] The accusation moves from
> the violating call to the next one; it is not removed."*
>
> *"**It affects thirteen specifications** and predates this change […] No issue has been opened for
> it; that is the user's call."*

A sessão 3 §4.2 apresenta isso como achado estrutural inédito, conta **cinco** specs (invisíveis ao
gate) ou **seis** (família), e o handoff §3 o promove a segundo dos três achados estruturais. A gh101
conta treze e nomeia-as.

**O gate G-2b foi considerado e rejeitado, com razões.** `gh101/design.md:166-190` (D-S9):

> *"The alternative considered was an absorbing state — the violating event poisons the object and
> nothing afterwards can accuse it […] It was **rejected**, for two reasons […] First, it is stricter
> than that repair […] Adopting absorption for four files would leave the set with two repair
> philosophies […] Second, absorption trades a false positive for a false negative: after poisoning,
> a genuine misuse of the same object — `sign()` with no preceding `update()` — goes unreported."*

Propor G-2b como gate obrigatório sem enfrentar D-S9 é um retrocesso de argumento, não um avanço.

**A cegueira do `INV-INS-110` é escopo declarado, não defeito descoberto.** Mesma seção:
*"it belongs in the frozen set's debt list and in an issue of its own, **not inside a change scoped to
INV-INS-110, which asks only that a bound event have a row that is not `fail` from every state**."*

**A atribuição do `but found .` foi medida e a linhagem a reverte.** `frozen_set_debt.md:88-95`:
*"**Task 8.1 measured it and the attribution was wrong** — the empty label came from the weaver, not
from the specification."* E `:195-200` dá a distribuição completa, *"with nothing left over"*: 643
`X509` + 8.648 `TLS` quando sobreviveu o advice do ramo inseguro sobre argumento **fora** da
allowlist; 8.371 + 51 rótulos vazios quando o argumento estava **dentro** dela e nada foi escrito.
A sessão 3 §4.4 atribui os mesmos rótulos vazios a eventos não ligados, órfãos e `__RESET` — uma
causa spec-side — sem citar a medição que a refutou. O `FINAL:74` (F11) tinha a atribuição certa; a
sessão 3 a regride.

**O gate de predicados que a §4.5 pede como novo (G-7a) já é executável.**
`scripts/gh101_predicate_pairing_check.py` + `tests/parity/test_gh101_specset_gates.py::test_every_written_constant_is_read_or_recorded`,
com o registro de omissões deliberadas em `data/gh101/predicate_omissions.csv` (20 entradas, cada uma
com a razão CrySL). E as razões mostram que boa parte das "arestas mortas" **é correta**: o predicado
é terminal porque nenhuma regra o REQUER. Exemplo (`predicate_omissions.csv`, `DIGESTED`):
*"The predicate is terminal: that a byte array is a digest is stated and never consulted, so a reader
would have to be invented rather than transcribed."* Logo **"35 dos 49 sítios de escrita (71 %) gravam
numa propriedade que ninguém lê" não mede defeito: mede a forma do oráculo.** O defeito real da §4.5 é
outro e é um só — a palavra errada em `jca/KeyPairSpec.mop:38`.

**A disciplina epistêmica que a linhagem enuncia como lição já estava escrita.**
`frozen_set_debt.md:138-148`: *"**Read this as a ceiling, not as a cause.** […] the `@fail` handler
emits no message naming the event that triggered it, so the published record cannot separate an
error caused by one of the eighteen from an error caused by the same specification's language being
left legitimately."*

**Circunstância agravante:** uma das quatro validações externas **reportou** isso.
`claude_fable5.md:341-349` cita `gh101/design.md:166-190`, D-S9, e *"recorded residue 'the accusation
reappears one call later'"*. A lista de extração classificou o item como PARCIAL (`C-138`) e o
transportou para `FINAL:484` (O-3) e `FINAL:490` (O-9) — isto é, **transportou a alternativa
descartada e perdeu a decisão já tomada**.

**Nota de justiça, em dois pontos.** Primeiro, a sessão 1 **sabia** que a gh101 reparou os órfãos:
`_FINAL_analise.md:593` manda *"publicar o censo dos 18 eventos órfãos do `jca` em C-0 **e reconhecer
que a gh101 já os reparou**"*. O inédito é relativo ao `FINAL.md`, não ao repositório — mas o
handoff §9 transforma isso em *"nunca tinha aplicado ao conjunto em produção"*, que é falso.
Segundo, a medição de **volume** da Forma B no comp162 (3.038 / 5.046 linhas mudas) e a observação de
que o reparo **converte** Forma A em Forma B com a linha de `init` byte-idêntica **são genuinamente
novas** e valem. O que não vale é o enquadramento de descoberta estrutural.

**E uma afirmação da sessão 3 é falsa.** `validacao.md:687-688` diz que a gh101 corrigiu a constante
errada do `gpr` *"sem registrar como divergência"*. `data/gh101/divergence_record.csv` carrega o hunk
explicitamente, com razão (*"gpr marked the private key it had just retrieved as
GENERATED_PUBLIC_KEY — a copy of gpu with the value changed and the constant left behind"*), e
`data/gh101/README.md:79` tabula *"2 writes moved to the right constant"*, nomeando o `gpr` do
`KeyPairSpec` e o `gtm1` do `TrustManagerFactorySpec` — que é, aliás, o segundo bug de slot que a
§8 desta verificação lista como não catalogado pela linhagem, e que a gh101 já tinha.

### 4.2 O que as duas changes de fato entregaram

**gh100 — *Weaver Emission Fidelity and the Layer-3 Gate*.** 58 tarefas, 55 feitas, 3 abertas
(7.4 duplicada, 7.5 `/rv-code-reviewer`, 7.6 `/rv-docs-sync`). Reparou o truncamento de advices
fundidos (`getMonitorCalls().get(0)` → iteração), a colisão de registro de wrapper e o parse
fail-open; censo mecânico pré/pós (`truncation sites 3→0`, `eventos perdidos 9→0`); evidência
vermelha commitada; sete invariantes (INV-INS-104..110) com testes Java. Fora de escopo, **declarado**:
L3-a (arma de runtime), **V4 — re-executar o corpus para quantificar violações apagadas** —, reparos
do lado da spec, e a causa-raiz upstream da fusão no JavaMOP.

**gh101 — *JCA Specification Conformance, Cipher Tables, and the Predicate Graph*.** 84/84 tarefas.
Reparou os 18 eventos toda-`fail`, criou `AndroidCipherTransformationUtil`, fechou 36 arestas de
predicado, re-orçou `CipherSpec` de 17 para 14 eventos e `MacSpec` de 8 para 11, tornou `jca_android`
selecionável, e deixou **sete artefatos de dados, seis scripts e cinco gates pytest**. Fora de escopo:
corrigir o `jca` (D-S0), **re-medir o corpus**, e o resíduo Forma B (task 3b.11b, *"No issue has been
opened for it; that is the user's call"*).

Os registros commitados que a linhagem não usou, com o que contêm:

| arquivo | linhas | conteúdo |
|---|---:|---|
| `data/gh101/README.md` | 705 | inventário de predicados antes/depois, omissões, mapa de arestas, verditos, divergência, identidade, o teto do `Cipher` |
| `data/gh101/frozen_set_debt.md` | 250 | o que o `jca` retém conscientemente: tabelas Cipher, os 18 acusadores, o que o Grupo 8 mediu, e a Forma B |
| `data/gh101/algorithm_naming.md` | 151 | o gap entre o que a spec compara e o que a plataforma resolve; 9 sítios; 2 defeitos de regra novos |
| `conformance_record.csv` | 23 verditos | **10 `anchored`, 11 `uncontradicted`, 2 `no-anchor`, 0 `contradicted`** |
| `divergence_record.csv` | 106 hunks | `layer-2-repair` 51 · `predicate-graph` 42 · `allow-list` 12 · `cipher-import` 1, em 19 arquivos |
| `predicate_omissions.csv` | 20 | a lista de omissões deliberadas que o INV-INS-111 exige, com razão CrySL por entrada |
| `predicate_inventory_jca.csv` | 85 sítios | **49 WRITE, 27 READ, 9 REMOVE** — a base dos "71 %" da sessão 3 |

**Consequência para a §4.5 da sessão 3.** Os "35 dos 49 sítios (71 %) gravam numa propriedade que
ninguém lê" são uma re-derivação do registro commitado da gh101, que já publica o mesmo número em
`README.md:53-59`. E a gh101 já o **decompôs**: das 18 constantes escritas sem leitor, **sete são
terminais nas duas âncoras CrySL** — nenhuma regra as REQUER, então a ausência de leitor é
propriedade do oráculo e não da tradução (`DIGESTED`, `SIGNED`, `VERIFIED`, `WRAPPED_KEY`,
`GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `GENERATED_KEY_PAIR`). Apresentar 71 % como defeito
sem essa decomposição **superestima o defeito em pelo menos sete constantes**.

**E D-B já está decidido em princípio.** O enquadramento que o `FINAL:292` recomenda como default
("api30 para disponibilidade, 1.5.2 para recomendação, nunca misturados em silêncio") é literalmente
um requisito MUST da gh101, em seis lugares, e já aplicado por spec no `conformance_record.csv`:

> *"The derived profile models **availability, not recommendation**. […] Any report comparing
> violation counts across the two sets MUST carry that caveat, because a lower count under the
> derived set is not evidence of better analysed code."* — `gh101/specs/instrumentation/spec.md:69`

D-B não é uma decisão em aberto; é **a mesma decisão, de novo, para um conjunto novo** — que é
consequência de D-A, não causa dela.

### 4.3 O que as duas changes erraram

Não as tratei como oráculo.

**Um grupo inteiro de tarefas `[x]` descreve código que foi revertido.** As tarefas 4b.1–4b.4 da
gh101, a decisão **D-S10** e a seção inteira `data/gh101/README.md:255-317` descrevem o
`ExecutionContext` re-chaveado por **identidade**. O commit `e204e2a4` (*"revert(e3): the predicate
store goes back to equality, and its test goes with it"*, 2026-08-11, três dias após o fechamento)
desfez isso, e a classe hoje usa `HashMap`/`HashSet`. **Nenhum artefato da gh101 registra a
reversão** — o `README.md:308-317` ainda afirma *"After 4b.1 the freeze check still passes"*. Pior:
o próprio D-S10 e o commit de reversão concordam que a aresta `generatedCipher` (task 5.1) só faz
sentido sob `==`; com o store de volta a `equals`, a única aresta que a gh101 conseguiu fechar está
semanticamente quebrada e nada o diz. A linhagem viu metade disso (`FINAL:73`, `c-B1`/`c-C19`,
marcado `U`) e registrou como *"o revert não está registrado no README"* — é maior que isso.

**Cinco invariantes sem gate executável.** Cruzando os doze INV-INS-104..115 com `tests/` e
`scripts/`: sem gate ficam **INV-INS-108** (evidência vermelha — puramente processual),
**INV-INS-110 da gh101** (os órfãos: o script existe e é completo, inclusive lendo as duas formas de
monitor, mas **nenhum teste o invoca**), **INV-INS-112**, **INV-INS-114** e **INV-INS-115** (o teto
de eventos: medido uma vez, e nada falha se uma spec passar de 17). Três deles — 110, 114, 115 — são
exatamente os que um conjunto sucessor precisaria. Isso confirma, por outro caminho, a conclusão da
sessão 2 de que **C-V é pré-requisito duro de C-4**.

**A auditoria reprova a gh101 num gate que é sobre ela.** O G11 do juiz global falha, e não é só
diferença de critério: registra três defeitos **introduzidos** pela gh101 (`GENCIPHER-EXTRA` da task
5.1, `SSL-RANDOMIZED-EXTRA` da task 3.2, resíduo de posicionamento do `KPG initError`) e a
falsificação da premissa de âncora do `predicate_edges.csv`. Do outro lado, registra que os reparos
que se sustentaram permanecem. "84/84 completa" e "REPROVADA 22/22" são compatíveis porque medem
objetos diferentes — a gh101 contra sete invariantes que ela mesma definiu, a auditoria contra
catorze gates pré-registrados que incluem inclusão de linguagem, FP/FN e qualidade de diagnóstico.

**Afirmações não sustentadas pelo artefato.** Além da reversão: `frozen_set_debt.md:200` diz *"That
is the whole distribution, with nothing left over"* sobre uma distribuição que cobre TMF+SSL (8.422
linhas) e **não** cobre as 421 de `Signature`, `MessageDigest` e `Mac` do mesmo `errors.csv` — o
escopo é real e não é declarado na frase, e **essas 421 podem muito bem ter a causa spec-side que a
sessão 3 propõe**; o `gh100/proposal.md:7` apresenta "7 advices, 9 eventos" como fato quando o
`design.md:112` admite que veio *"by inspection"*; o verdito **PASS** de V2 (`gh100/tasks.md:83`)
verifica 2 dos 9 eventos, com 7 em `n/a`; a leitura de `plansSkippedHighRegister` (6.4) é `n=1`
quando o cenário do delta pede o mesmo conjunto de APKs; e a tabela do D-S10 tipava as leituras de
semente do `SecureRandomSpec` como `long` boxed quando são `byte[]` — o `README.md:281-287` corrige,
e a contagem de 8 sobreviveu por coincidência (*"The count of 8 is right; the composition was not"*).

---

## 5. Erros que mudam decisão

### 5.1 A correção nº 1 da lista está errada — e o número **reproduz**

`_lacunas.md:715` abre as onze correções com *"Corrigir `FINAL:114` — a linha do `okio.`/85,44 %. A
fonte citada refuta o número"*, e chama-a de *"a correção mais barata com maior efeito a jusante"*.
O handoff §4 escala: *"o mais caro é a linha do `okio.`/85,44 %, que registra como concordância um
número que a fonte refuta"*. Nenhuma das três sessões mediu.

**[arbitrado aqui]**, sobre o dataset do artigo:

| lista de prefixos | linhas | % de 97.018 |
|---|---:|---:|
| a lista de 7 vendors nomeada pelo plano | 76.154 | **78,49 %** |
| + `okio.` | 80.204 | **82,67 %** |
| + `okio.` + `org.spongycastle.` | **82.890** | **85,44 %** |

O `85,44 %` do plano **é exatamente reproduzível**, sob uma lista de nove prefixos. E `org.spongycastle`
é o *fork* Android do BouncyCastle, que a lista do plano nomeia — logo, lido com caridade, o número
reproduz sob a própria lista declarada, mais `okio.`.

Portanto: `deepseek` acertou os dois números que mediu (78,49 e 82,67) e errou a conclusão categórica
("não reproduzível"); `claude_fable5` errou ao dizer "só com `okio.`"; o `FINAL:114` transportou a
versão do fable5; e três sessões adversariais discutiram **quem disse o quê** sem abrir o CSV. A
correção correta não é *"a fonte refuta"* — é *"duas fontes externas mediram a mesma grandeza no
mesmo arquivo e discordaram em 2,8 pontos, ninguém arbitrou, e a lista de prefixos que produz o
número tem nove entradas e não sete"*. O default de **D-F** deve nomear as nove.

### 5.2 `KeyStoreSpec` é o **sexto** maior produtor de mudas, não o terceiro

A sessão 3 §4.3.3 e o handoff §3 dizem *"o terceiro maior produtor de linhas mudas do corpus"*.
**[arbitrado aqui]**, comp162: SSLContext 2.916 · SecureRandom 2.882 · TMF 2.855 · MessageDigest
2.008 · Cipher 1.461 · **KeyStore 1.136**. Sexto. O argumento da §4.3 não depende disso, mas o
superlativo é o que carrega a urgência.

### 5.3 O comp162 não são "8 réplicas"

O handoff §7 e a §8 descrevem `experimento-comp162/results/*/*/errors.csv` como **"8 réplicas"**.
**[arbitrado aqui]**: são **8 shards com conjuntos de APKs disjuntos** — 112 APKs distintos, zero
interseção entre arquivos —, cada um rodando 3 ferramentas × 3 repetições, 896 células de execução.
As 6.344 identidades distintas pertencem cada uma a exatamente um arquivo (soma por arquivo = total
global). Consequência: **0 % dos 67,74 % de repetição é artefato de replicação**; toda ela é
re-disparo dentro de uma mesma execução. O número publicado é o mais conservador possível — mas
quem ler "8 réplicas" vai supor variância replicada que não existe.

### 5.4 A definição de "sítio" troca entre os dois corpora, sem declaração

O handoff §8 fixa: *"**sítio** = a 4-tupla `(spec, class, method, source)`"* e adverte que *"as
definições importam mais do que o comando"*. Mas o dataset do artigo tem **10 colunas e não tem
`source`**. A metade-artigo do achado central da sessão 2 (`_lacunas.md:318-320`: 157 sítios mudos, 64
gêmeos, 32.411 mudas gêmeas, 38.349 solitárias, zero só-legíveis) **[arbitrado aqui] reproduz
exatamente — sob a 3-tupla `(spec, class, method)`**. Sítio mais grosso funde mais linhas e portanto
produz mais gêmeos por construção. E a propriedade que impressiona no comp162 — mudas gêmeas =
total de legíveis — **não replica** no artigo (32.411 contra 26.258). "O padrão replica no dataset de
referência" é verdade só para a metade fraca da afirmação.

### 5.5 As 296 linhas do `KeyManagerFactorySpec` são creditadas a duas causas — e os dados não separam

`_lacunas.md:671` credita a C-1a *"3.151 linhas mudas conhecidas e evitáveis (TMF 2.855 + **KMF 296**)"*.
A sessão 3 §4.2.4 conta as **mesmas 296** na família Forma B invisível ao gate, e usa
*"296 mudas, zero legíveis — a spec nunca consegue dizer nada"* como sinal de que a leitura está certa.

**[arbitrado aqui]**: as 296 são 9 sítios, 100 % `InvalidSequenceOfMethodCalls`, todos de aquisição
(`TlsUtil.newKeyManager` 191, `SSLParametersImpl.createDefaultX509KeyManager` 105), em **três triplas
de linhas-fonte consecutivas em lockstep** (36 de 37 células com contagem idêntica nas três linhas).
E as duas causas **não são separáveis com este artefato**: o `errors.csv` não carrega o nome do
evento, nem o estado do autômato, nem o valor do algoritmo; ambas as hipóteses produzem a mesma
tupla observável; e ambas aterrissam nos mesmos sítios. Somar os ganhos de C-1a e do reparo de
autômato infla o total em 296 linhas (1,9 % do corpus mudo).

Pior, e mais geral: **a sessão 3 exige perfil de sítios para negar a atribuição do `SecureRandomSpec`
a C-1a (§3.1c) e aceita atribuição por spec inteira para a Forma B (§4.2.4).** Dois padrões de prova
no mesmo documento, o mais rigoroso aplicado contra a tese alheia.

### 5.6 `gh56-smoke` não é o oráculo do `jca` congelado

O handoff §7 designa `results/gh56-smoke/monitors/` como *"o oráculo que diz a verdade"* para o `jca`
congelado, e os quatro comandos de reprodução do §8 recebem esse arquivo como argumento.
**[arbitrado aqui]**, por `mtime` e `git log`:

| artefato / commit | data |
|---|---|
| `results/gh56-smoke/monitors/` gerado | **2026-05-14** |
| `9cec468b fix(jca): negate KeyManagerFactorySpec init guard…` | 2026-06-04 |
| `2fa44ff5 fix(rvsec-mop): canonicalize PBE spec error labels…` | 2026-06-12 |
| dataset do artigo | 2026-07-06 |
| `7e7acb69` — congela o `jca` | 2026-08-07 |
| `results/gh101_group8_jca_frozen_control/` gerado | 2026-08-08 |

O `gh56-smoke` antecede o congelamento em três meses e duas correções de fonte. O `diff` contra o
controle congelado tem 7 linhas, e uma é semântica: em `gh56-smoke` o guard de
`KeyManagerFactorySpec.init` está com a **polaridade invertida**, reportando `UnsafeAlgorithm`
exatamente quando o algoritmo é seguro.

As tabelas de transição são idênticas, então **as contagens de órfãos, Forma B e slice-raiz
sobrevivem**. O que não sobrevive é a designação: quem seguir o handoff e ler qualquer coisa além das
tabelas — as guardas de `condition()` inlinadas, que é justamente o que decide a leitura semântica da
Forma B e o que a etapa 1 depende — lê código pré-correção, na spec que a sessão 3 usa como *"a
anatomia"* do defeito.

### 5.7 Erros menores, mas que estão em tabelas de decisão

- **`@severity` no `generic_new`.** A sessão 3 §4.1.3 diz *"os 27 arquivos carregam `@severity
  warning`"*. Medido: **18 `error`, 7 `warning`, 2 `suggestion`**. O campo existe e tem três valores,
  o que fortalece o argumento — mas o valor citado está errado.
- **"os 118 são idênticos exceto pelo nome"** (§4.1.2). Falso: 118 esqueletos distintos, de 26 a 235
  linhas, de 1 a 9 eventos, sobre tipos monitorados sem relação. O que é rigorosamente uniforme é o
  **bloco de reporte** — que é a tese, e ela se sustenta.
- **`ViolationRecorder.java:94`** (§4.7, O-8): descrito como *"ao ver `fileName` nulo desliga o filtro
  inteiro em vez de pular o quadro"*. O código faz o oposto: é *fail-open por quadro* — o quadro é
  **incluído**. O efeito prático é pior do que o descrito: `getLineOfCode()` devolve
  `relevantStack.get(0)`, então um quadro do próprio runtime de monitoramento entra no topo e vira o
  campo `location`, que **entra na identidade do `ErrorSummary`**.
- **`INV-CAN-04`** (§4.1.4): o descarte silencioso do `logcat_parser` não o viola — o invariante é
  escopado a `modules/aperv-tool/src/aperv_tool/analysis/` (`campaign-analysis/spec.md:5`), e o
  parser é do `rv-coverage`. É satisfeito **vacuamente** a jusante: `read_errors_csv` conta
  fielmente as linhas de um arquivo do qual os registros já foram removidos. E existe divergência
  ativa: a mesma linha `[helper] ::: …` produz 1 violação por `aperv_tool` e 0 por `rv-coverage`.
- **A acusação do "16/23"** (§3.3): **improcede**. O review diz `16/23` **uma** vez, não duas; o
  número do `FINAL` (15/23) é o **correto** — medido no oráculo, 15 `AbstractAtomicMonitor` + 8
  `AbstractSynchronizedMonitor` —; e o `FINAL` **declara** a correção em duas linhas (`:120`, `:502`).
  É correção declarada de um erro da fonte, não citação falsa.

### 5.8 Contagens internas da própria sessão 3

Todas verificadas por leitura integral: *"13 arquivos casam o glob"* (são **14**); *"quatro opções
mudam de estado"* e a seção lista **cinco**; *"a lista cresce de 11 para 11 + 9"* e a §5 enumera
**seis**; *"duas conclusões de agente foram corrigidas"* e a §6 registra **três**; *"os três números
que não reproduzem"* e a §3.1 entrega **seis**; o número `6.033`, que ela apresenta como refutado,
**não existe em documento nenhum da linhagem** — só nela própria; e as suas citações a
`logcat_parser.py` derivam de uma linha (`:305` onde é `:306`), que é exatamente a falta que ela imputa
ao `FINAL` na acusação sobre F4. Nenhuma delas muda uma conclusão; todas fragilizam o documento que
mais insiste em rigor de contagem.

---

## 6. Erros de desenho, que nenhuma das três sessões auditou

As três sessões auditaram **proveniência** e **aritmética**. Nenhuma auditou o artefato proposto como
desenho. Cinco consequências, todas verificadas em código:

### 6.1 A mudança C-2 é um no-op para a classe dominante de registro

`FINAL:316-317` põe o `code` na identidade de dedup e mantém o texto livre fora dela. `FINAL:341-343`
define **um código por bloco `@fail`** (`<SPEC>-ORDER-00`). Como há exatamente um `@fail` por spec
— medido: 21 das 23 specs do `jca` têm `fail=1`, duas têm `fail=0`, **nenhuma tem dois** —, o `code`
da família `InvalidSequenceOfMethodCalls` é **função de `spec`**.

E a identidade já contém `spec`: `ErrorSummary.equals` compara `(classQualifiedName, error, location,
methodName, spec)`. Acrescentar um campo implicado por um dos cinco não refina partição alguma —
`(P₁∧…∧P₅∧code_eq) ≡ (P₁∧…∧P₅)`. **O `HashSet` do coletor produz exatamente o mesmo conjunto de
sobreviventes antes e depois.** Logo a "descontinuidade de contagem" que C-2 manda declarar é zero
para 72,93 % dos registros, e o campo que de fato discriminaria — `ev`, o nome do evento ofensor —
é justamente o que fica no texto livre, excluído da identidade por decisão explícita.

`_lacunas.md:738` chegou a levantar a pergunta (*"decidir se `ev` entra na identidade de dedup, sem o
que a dedup descarta exatamente o que a mudança existe para mostrar"*) e ela **não entrou** nem nas
vinte correções nem nas duas perguntas de Fase 0 do handoff. **É a terceira pergunta de pesquisador,
e é a que decide se C-2 vale a pena existir.**

### 6.2 O gate G-2b não é computável nos termos em que é vendido

A sessão 3 §4.2.7 enuncia: *"para toda especificação com um evento de instanciação insegura, o
alfabeto de saída do estado inseguro deve conter o alfabeto de saída do estado seguro
correspondente"*, e afirma ser *"computável sobre as mesmas tabelas de transição que G-2 já lê, sem
CrySL, sem DFA, sem oráculo"*.

Os três termos exigem rótulo externo, e o central **não existe no artefato**: em `CipherSpec` e
`KeyManagerFactorySpec` o autor escreveu um estado `unsafeAlg` cujo conjunto de arestas de saída é
idêntico ao de `start`, e a minimização os funde. É por isso que a tabela mostra `δ(q0, g3) = q0`.
E isso é estrutural, não acidental: **se o estado inseguro sobrevivesse à minimização, o seu alfabeto
de saída já seria diferente e a condição do gate já estaria decidida; se os alfabetos forem iguais —
que é o caso de interesse — o estado não existe mais.** O gate é vacuamente inaplicável exatamente
onde deveria morder.

O que é de fato computável sobre as tabelas, e foi rodado nos quatro oráculos:

| gate | definição | `jca` |
|---|---|---|
| G-2 (já existe) | `∀s: δ(s,e) = sink` | 18 eventos |
| **G-2a** inércia global | `∀s: δ(s,e) = s` — o evento nunca muda estado | 1 (`SecretKeySpec.e1`) |
| **G-2b′** redundância em q0 | `δ(q0,e) = q0` | 8 specs |
| **G-2c** estados mortos | inalcançável de q0, ou de onde o aceitante é inalcançável | 1 |
| **G-2d** sink ≠ `fail` | maior índice não é o estado de `Category_fail` | 2 specs |
| **G-6′** injetividade | `#métodos *Event(` por spec ≠ `#linhas de transição` | 1 (`GCMParameterSpecSpec`) |

O gate semanticamente correto exige **um bit por evento no `.mop`** — uma anotação de "instanciação
insegura" com ponteiro para o evento seguro par. Com ela o cheque é trivial; sem ela, não existe.

### 6.3 A definição de "Forma B" classifica o **reparo** como a doença

Rodada nos quatro oráculos, a definição estrutural da sessão 3 casa 5 specs no `jca` — e **11 no
`jca_android` pós-gh101**. A causa é direta e está documentada pelo próprio autor do reparo
(`jca_android/SSLContextSpec.mop:95-101`): *"unsafeProtocol mirrors the unsafeAlg state
KeyManagerFactorySpec uses for the same event shape"* — isto é, o reparo copiou deliberadamente o
idioma de uma das cinco specs que a Forma B chama de defeituosas.

**Se Forma B é defeito, a gh101 mais que dobrou o número de defeitos ao consertar; se a gh101
consertou, Forma B não é defeito.** A definição não pode ser usada como gate sem uma allowlist — que
é, de novo, um rótulo semântico.

Além disso a definição tem três falsos negativos: a pré-condição "zero órfãos" exclui
`KeyPairGeneratorSpec` e `MessageDigestSpec`, que têm **exatamente a mesma estrutura**, só porque um
evento **não relacionado** é órfão; e exclui `SecretKeySpec`, que é o pior monitor do conjunto (§6.4).

### 6.4 O gate G-2, que a linhagem trata como pedra angular, é frágil

Dois modos de falha medidos:

1. **Dois monitores não têm categoria `fail`** — `SecretKeySpec` e `RandomStringPasswordSpec`, nos
   quatro oráculos. Neles o "sink = maior índice" não é estado de violação, e o gate pode acusar
   como órfão algo cuja semântica é o oposto.
2. **`SecretKeySpec` no `jca` é um detector nulo, e o gate dá verde.** `Prop_1_transition_e1 = {0,1}`,
   único evento, `δ(s,e) = s` para todo `s`, estado 1 **inalcançável**, `Category_match` sempre
   verdadeiro, nenhum `@fail`. A spec não pode reportar nada, jamais. Nenhum documento da linhagem a
   menciona. (Corrigida no `jca_android` pós-gh101.)

### 6.5 A razão escrita da ordem da onda C morreu no próprio documento que a escreve

O handoff §4 ordena *"onda C = **C-4 → C-3 sequenciadas** (a mensagem nomeia estados que C-4 vai
criar, então a ordem importa e a intercalação 'por arquivo' que o documento propõe não funciona)"*.
Duas seções antes, o mesmo arquivo registra a decisão **`st=` sai do contrato** — a mensagem passa a
não nomear estado nenhum. A razão escrita da ordenação está morta.

É exatamente o defeito que a sessão 3 diagnosticou na decisão de ordem (§3.2, *"a razão escrita de
uma decisão tomada é uma alegação retratada"*), cometido pelo documento que a corrige. A ordenação
pode continuar defensável — a origem dela é `_FINAL_analise.md:536-537`, e C-4 pode mexer no alfabeto
—, mas precisa de razão nova.

### 6.6 O que falta no plano não é gate: é um instrumento diferencial

Os oito gates de C-V medem propriedades **estáticas** de artefatos — tabelas de transição, listas de
eventos, arestas de predicado, gramática de mensagem. Nenhum compara **comportamento antes e depois
de um reparo sobre o mesmo insumo**. E o histórico deste repositório mostra que é exatamente aí que
os defeitos nascem:

| reparo | o que removeu | o que criou | o gate viu? |
|---|---|---|---|
| gh100, D-B1 (fusão de wrappers) | descarte silencioso de 12 wrappers | advices de aridade incompatível disparando no mesmo sítio | **não** — `wrappersGenerated 96→84` foi reportado como sucesso |
| gh101, Grupos 3/3b | 18 eventos toda-`fail` | Forma B: a acusação se move para a chamada seguinte | **não** — o gate conta linhas toda-`fail` e por construção passa a reportar zero |
| gh101, D-S10 (identidade) | leituras que respondiam sobre o objeto errado | 8 leituras cuja resposta muda no conjunto congelado | declarado, não verificado — e revertido três dias depois |

O que chega perto e para antes: o INV-INS-108 prova que um teste **discrimina**, não que o reparo não
abriu outra via; o `EmissionParityTest` da gh100 compara inline × wrapper **para o mesmo advice**, e
não advices distintos fundidos no mesmo wrapper — que é precisamente o buraco de C-1a; o
`gh101_monitor_transition_check.py` é zerado pelo reparo por construção; o registro de divergência
enumera **hunks**, não consequências. O INV-INS-109 da gh101 é o único que chega a declarar o limite
— *"Byte-identity of the frozen paths, and of the monitor generated from them, does **not** establish
that the frozen set behaves as it did"* — mas declara, não verifica.

**As duas changes sabiam.** A gh100 pôs V4 (re-executar o corpus) fora de escopo; a gh101 pôs
"re-measuring the corpus" nos não-objetivos. Repararam com a única evidência que tinham — estática —
e registraram que era insuficiente. Os três deslocamentos acima são a fatura.

Acrescentar G-2b e G-7a não paga essa fatura: são mais gates estáticos, e um deles não é
implementável (§6.2). O que fecharia é modesto e já tem precedente na própria gh101 — a tarefa 8.1,
que rodou **quatro APKs em dois braços diferindo só no conjunto de specs** e por isso conseguiu
corrigir uma atribuição registrada. Um harness com essa forma, aplicado antes/depois de cada reparo
de C-1a, C-3 e C-4, vale mais do que os cinco gates estáticos que faltam.

## 7. A independência das quatro validações externas é ilusória

`FINAL:60` institui como cabeçalho da tabela de fatos: *"Verified in source by the review and
**re-verified by ≥2 external validations** unless marked"*, e as linhas F1–F14 carregam `ext. 1–4`,
`ext. 1,2,3`, `ext. 1,4`. Medido contra o prompt que os quatro receberam
(`_validacao_prompt.md`, 349 linhas):

- **Dez dos catorze fatos F1–F14 são premissas literais do prompt** (§2:82-103 e §4, "Lessons and
  pitfalls"), incluindo o pilar do sink, o `condition()` como prólogo, `BaseMonitor:604-610` morto, a
  identidade que exclui a mensagem com o teste que a fixa, o fan-out do slice-raiz com clonagem, e as
  correções numéricas.
- **As quatro linhas creditadas a `ext. 1–4`** — a unanimidade — são **F1, F7, F9 e F10**:
  precisamente as quatro premissas mais explícitas do briefing.
- Onze das treze propostas `c-D2.*` estão no prompt §7, com os **tokens literais** (`CIP-ORDER-03`,
  `__EVENTNAME`/`__PREVSTATE`, o manifesto estático, `--internalbehavior`, o número do re-orçamento
  de alfabeto). Sete dos oito gates formais estão no prompt §6. A escada C-0..C-5 é a escada do
  prompt renomeada.
- **O próprio prompt, linha 31, diz: *"Agreement between agents is not proof; a round number is not
  proof."*** O `gpt5_codex:75` repete (*"Agreement between passes was used only to select
  discriminating checks, never as proof"*), `codex:7-13` declara-se de primeiro estágio,
  `codex:478-480` proíbe a citação como certificação, e `claude_fable5:684` escreve *"Agreement is not
  proof; the quotes are."* **Nenhuma das quatro ressalvas aparece no `FINAL`.**
- `FINAL:27` promete reproduzir *"each report's own evidence class"*. As classes que os quatro
  declararam — `PROVEN`, `MEASURED`, `OBSERVED_IN_ARTIFACT`, `NOT_VERIFIED` — têm **zero ocorrências**
  no documento. Foram substituídas por `R`/`V+`/`V−`/`V±`/`U`, que medem **quem verificou**, não **o
  que é a evidência**.
- **A ponderação entre as fontes era impossível**, porque a extração perdeu os dados que a
  permitiriam: `deepseek:31` declara **não ter usado subagentes** (o prompt §1:21-23 exige);
  `deepseek` e `gemini` não usaram o MCP obrigatório e não declararam; e `gemini:63` intitula a
  dimensão V1 *"40+ `file:line` Samples"* e entrega **21 linhas** (o prompt §5 exige ≥40). Nada disso
  está em nenhuma das 581 linhas das listas.

**O sinal de independência genuína existia e foi apagado.** Onde o prompt mandou medir sem dar a
resposta (o estágio 4 do funil; a atribuição a terceiros), os três relatórios que fizeram a conta
chegaram a **três respostas incompatíveis**, com uma refutação frontal do `85,44 %` contra uma
confirmação. O `FINAL` comprimiu isso em *"funnel 24–59 by definition"* e adotou como padrão a
configuração refutada. Tratou como ruído a única informação de primeira ordem que o exercício de
quatro produziu.

**Valor marginal.** `claude_fable5` carregou o peso sozinho: 117 IDs `c-` no §4 contra 49 `x-`, 48
`d-` e 24 `g-`; é o único que abriu o E3 (`experimento-comp162`) e o oráculo api30; é a origem da
§5.1 inteira, da mudança C-1a e da decisão D-C. `gpt5_codex` pagou-se com três scripts consumidores e
com a disciplina epistêmica — que foi integralmente descartada (13 dos seus 20 "ausentes" são
ressalvas de método). `deepseek` pagou-se com uma coisa só, a medição do `85,44 %`, que foi
invertida no transporte. `gemini` foi o mais fraco por qualquer métrica e produziu os **dois únicos
achados que desapareceram inteiramente** (a guarda `fileName` do `ViolationRecorder` e o D16) — o
quarto relatório justificou-se por acidente, e o mecanismo de consolidação, que pontua por
concordância, anulou o acidente.

**Corolário desconfortável:** onde o `FINAL` escreve `ext. 1` (uma só validação) estão os achados
que de fato são novos; `ext. 1–4` marca os que já estavam no briefing. **A contagem de concordância
correlaciona negativamente com o valor informativo do item.**

**As listas de extração.** Os totais reproduzem exatamente (581 = 193+202+113+73 = 450+70+61) e não
são somáveis: três listas declaram a mesma regra de fusão e a densidade abre **1,87×**; a quarta
declara a política oposta e cai no meio; há **15 rótulos de status distintos** colapsados em três
baldes, um deles `CARREGADO (refutado)`; e **catorze fatos** — não seis — recebem estados diferentes
contra a mesma célula do `FINAL`, dois deles divergindo **dentro da mesma lista**. As 61 ausências
são **45 fatos distintos**, e a recontagem honesta dá **39–40**, confirmando o número da sessão 3. O
que ela não diz é a distribuição: **16 % são a re-baseline inteira do E3** — que a mudança C-0 manda
medir de novo — e **16 % são as ressalvas de validade das próprias validações**, das quais nenhuma
sobreviveu.

---

## 8. Defeitos que ninguém listou

Achados na leitura integral dos 191 `.mop`, dos quatro monitores gerados e da camada Python. Nenhum
aparece em documento algum da linhagem.

**Graves**

1. **`SecretKeySpecSpec.mop:27-30` tem parênteses desbalanceados, nos dois conjuntos.** Único arquivo
   desbalanceado dos 191. O `))` da linha 29 já fecha `validate(` e `condition(`; o `)` da linha 30
   sobra. Comparando com o `c3` (`:44-47`), que é a cópia negada, fica claro que o `!(` foi removido e
   o `)` extra ficou. **Não corrigido pela reescrita que tocou 19 dos 23 arquivos.**
2. **`GCMParameterSpecSpec` declara dois eventos `c1` e a `ere` referencia um `c2` inexistente**
   (`:23`, `:34`, `:48`, nos dois conjuntos). O monitor gerado tem **dois métodos** `c1` com ids de
   evento diferentes e **uma** linha de transição; `c2` sumiu em silêncio. O construtor de 4
   argumentos do `GCMParameterSpec` está fora da linguagem aceita. **Não corrigido pela gh101.**
3. **`jca/TrustManagerFactorySpec.mop:62-66` tem quatro defeitos empilhados** — retorno declarado
   `TrustManager[][]`, pointcut declarando `KeyManager[]` para `getTrustManagers()`, binding em `k`
   quando o parâmetro da spec é `mf`, e escrita em `GENERATED_KEY_MANAGERS`, o slot do gerenciador de
   **chaves**. É o **segundo** bug de slot errado do conjunto, além do `gpr` que a §4.5 da sessão 3
   nomeia. O `jca_android:97-110` corrige os quatro e os documenta — prova de que os autores
   conheciam o defeito no `jca`.
4. **`SecretKeySpec` no `jca` é um detector nulo** (§6.4), e o gate G-2 dá verde nele.
5. **`jca/KeyPairGeneratorSpec.mop:26`**: `String algorithm;` sem inicializador, e `validate(int)`
   faz `switch(algorithm)` — NPE em Java para `null`. A mensagem de `:72` interpolaria `but found
   null.`

**De mensagem — a lista da sessão 3 está incompleta**

6. **`jca/KeyGeneratorSpec.mop:64`**: o mesmo bug de espaço do `KeyStoreSpec` (`"expecting one of" +
   String.join(...)`), não relatado. Sobrevive no `jca_android:111`.
7. **`jca/MacSpec.mop:62`**: a mensagem perde o verbo — `"one of " + …` sai como `one of HmacSHA256,…
   but found .`, sem `expecting`.
8. **`jca_android/MessageDigestSpec.mop:70-71,88-89`: a mentira piorou.** A lista de `:16-17` passou a
   ter **nove** entradas, incluindo `MD5` e `SHA-1`, e a mensagem continua prometendo
   `{SHA-256, SHA-384, SHA-512}` — o relato afirma que MD5 é inaceitável no momento em que a spec o
   aceita.
9. **`jca/SecretKeySpecSpec.mop:49`**: diz `keyMaterial.length is not randomized`; a condição de `:46`
   testa o **array**, não o `length`.
10. **`jca/CipherSpec.mop:61,76`**: a lista de esperados é literalmente `{AES/CBC/PKCS5Padding,
    AES/PCBC/ISO10126Padding, ...}` — o `...` é texto, e o conjunto real vive em
    `CipherTransformationUtil` e nunca chega ao relato.
11. **Os 25 relatos de 3 argumentos do `jca` dizem `expecting unknown`** — 49 % dos relatos do
    conjunto. Não é mentira: é ausência total de conteúdo, e é a origem mecânica do problema (§9).

**De infraestrutura**

12. **O javadoc de `PackageFilter.java:9-11` afirma paridade com o `Coverage.aj` legado (INV-INS-53).
    É falso.** O `Coverage.aj:22-46` tem 24 cláusulas; o `PackageFilter` não exclui `jakarta`,
    `com.sun`, `com.android`, `com.facebook`, `org.apache` (só `commons`/`geronimo`), `libcore`,
    `br.unb.cic.mop` nem `Coverage+`, e **exclui** `Lkotlinx/`, que o `Coverage.aj` não exclui. As
    variantes `ajc` e `dexlib2` não têm recall equivalente.
13. **O `jca` chama a sobrecarga `remove(Property)` `@Deprecated` em 4 sítios** — que apaga o conjunto
    inteiro da propriedade. Uma falha de sequência de uma fábrica apaga a marca de todas as outras no
    processo. O `jca_android` eliminou a forma e documenta a razão.
14. **`generic`: 11 dos 118 arquivos têm nomes de parâmetro duplicados** na mesma assinatura (não
    compilam em Java) e `FSM358.mop:4,6` tem colisão de import (`RVMLogging.Level` × `java.util.logging.Level`).

---

## 9. O que isto muda no plano, etapa por etapa

O plano é o `FINAL.md` §8 — oito mudanças, quatro ondas — com as correções do handoff. Não existe
change OpenSpec para nada disto: as ativas são gh100, gh101, gh102 (e cinco de outros assuntos); o
maior `gh<N>` usado é 103, arquivado, e é a camada de **análise** (consumidora do `errors.csv`), não
o produtor das mensagens. **O primeiro número livre é 104.**

### 9.1 O plano em uma página

**Fluxo do processo:**

```
Fase 0 · 3 decisões do pesquisador ──┐
Fase 1 · corrigir o FINAL.md         ├──→ Fase 3 · abrir issues + criar changes ──→ Fase 4 · implementar
Fase 2 · destravar o processo        ──┘        (gh104 em diante)
```

- **Fase 0** — (a) onde a etapa 1 aterrissa (D-A: `jca_v2` custa 94 hunks já escritos mais o
  re-orçamento do `CipherSpec` de 17 para 14); (b) oráculo por família de cláusula (D-B: já é
  requisito MUST da gh101, falta reafirmá-lo para o conjunto novo); (c) **nova** — `ev` entra na
  identidade de dedup? Sem ela, C-2 não refina nada.
- **Fase 1** — as 20 correções, das quais quatro estão erradas como escritas (§5).
- **Fase 2** — arquivar gh101/gh102, resolver a colisão `INV-INS-109/110`, fechar 7.5 e 7.6 da gh100.

**Fluxo das etapas de implementação:**

```
E0 baseline ─┬─ E1 mensagens ──────────────┐
             ├─ E2 aridade do weaver       ├─→ E4 autômatos ──→ E5 predicados
             └─ E3 transporte ─────────────┘         │
             EV validação ── atravessa todas ────────┘
                                        E6 identidade — só se a decisão (c) for "sim"
```

| Etapa | O que faz | Por quê | Depende de | Aceitação |
|---|---|---|---|---|
| **E0** baseline | Medir o orçamento residual sobre o E3; **ler o `errors.csv` por `aperv_tool.analysis.violations`**, não por um parser novo; registrar classificador e definições com a disciplina de *freeze item* da gh103 (§9.3) | 16 % das "ausências" das listas já são medições do E3 feitas e descartadas; e o `unique_msg` já é construído em quatro lugares — um quinto leitor de `errors.csv` repete o defeito que E3 existe para fechar | — | rerun byte-idêntico; todo número sai com numerador e denominador declarados; nenhuma definição com default implícito |
| **E1** mensagens | 4º argumento nos **25 sítios de 3 args** (21 `@fail` + 4); corrigir as **11 mensagens que mentem**; trocar **campo → argumento** nos 17 sítios `but found` | `message == 'unknown'` ⟺ construtor de 3 args. É o conteúdo mecânico inteiro do problema: ~25 edições em 21 arquivos | D-A (onde pousa) · o censo das mentiras é **pré-condição**, não consequência | zero `unknown`; zero `but found .`; literais numéricos da mensagem casam com os da condição que a guarda |
| **E2** aridade | Impor aridade posicional de `args()` ao agrupar advices no wrapper, com a regra de três cláusulas | Resíduo **introduzido** pela gh100 e não registrado por ela; a regra original apagaria 66,6 % das linhas legíveis | D-C (decidido) · fechar 7.5/7.6 da gh100 | teste de que os 16 advices sem `args()` sobrevivem ao agrupamento, mais o caso positivo; contador de excluídos |
| **E3** transporte | Gramática `key=value` v1, sentinelas, contadores de descarte, escapers e guarda de nulo, matriz de consumidores | Há pelo menos seis pontos de descarte silencioso no parser, e o `INV-CAN-04` não os alcança | E0 | testes de propriedade (vírgula, aspas, `\n`, `:::`, truncamento); todo descarte contado |
| **EV** validação | Gates. **2 dos 8 já existem** (G-2 como script, G-7 como pytest). G-2b **não é implementável** — trocar por G-2a/G-2b′/G-2c/G-2d/G-6′. O item que falta de verdade é o **harness diferencial** (§6.6) | Os gates propostos medem só estática; gh100 e gh101 deslocaram defeitos sem que gate nenhum visse | — (começa no dia 1; vira pré-requisito duro de E4) | G-2 vira pytest; G-6′ pega o `c1` duplo do `GCMParameterSpecSpec`; o harness roda antes/depois de cada reparo |
| **E4** autômatos | Reparos de tradução mais os defeitos novos da §8 (`SecretKeySpecSpec` desbalanceado, `SecretKeySpec` inerte, `c2` inexistente, `gtm1`) | São defeitos de tradução, não escolhas de oráculo | D-A · D-B · EV (G-2..G-5) | cada edição = linha + registro de divergência + exemplo regressivo. **Teto: `CipherSpec` está em 17/17 e um evento novo estoura a geração** |
| **E5** predicados | `RequiredPredicate`/`ForbiddenMethod`, produtores faltantes, `condition()` para o corpo | O gate já roda e a lista de omissões já existe | E4 · decisão sobre o `ExecutionContext` | G-7 verde, sem omissão nova não justificada |
| **E6** identidade | `code` na identidade e colunas no `errors.csv` | **Só faz sentido se `ev` entrar junto** — `code` é função de `spec`, que já está na identidade | decisão (c) · E1 · E3 | descontinuidade de contagem declarada e **não nula** |

**O que mudou em relação ao plano da linhagem:** E1 subiu e ficou barata, porque a premissa mecânica
está verificada; E6 deixou de ser etapa firme e virou condicional; EV encolheu e ganhou o item certo;
a ordem C-4 → C-3 caiu, porque a razão escrita dela morreu quando `st` saiu do contrato; e E4 ganhou
um teto declarado que nenhum documento contabilizava.

### 9.2 Etapa 1 — as mensagens das specs: mais barata e mais sólida do que a linhagem supõe

**A mecânica exata do `unknown`.** O campo `message` do `errors.csv` **é** o campo `expecting` do
`ErrorDescription` — o coletor concatena `err.getExpecting().trim()` como sétimo campo da linha de
logcat, e o parser rejunta `parts[6:]`. E o construtor de 3 argumentos (`ErrorDescription.java:34-36`)
faz `this(type, spec, location, "unknown")`.

> **`message == 'unknown'` ⟺ o sítio de relato usou o construtor de 3 argumentos.** São **25 dos 51**
> sítios do `jca`: os 21 blocos `@fail` mais 4 outros.

Dar um quarto argumento a esses 25 sítios é o conteúdo mecânico **inteiro** de "eliminar o
`unknown`". São ~25 edições em 21 arquivos.

**A premissa mecânica do desenho está verificada, e ao contrário do que um dos meus subagentes
concluiu, ela funciona.** Verificado nos quatro monitores gerados, 134/134 e 140/140 métodos de
evento, zero anomalias, nas duas formas de monitor: **o corpo do evento escrito no `.mop` é inlinado
antes da transição.** Forma canônica:

```java
final boolean Prop_1_event_c1(...) {
    { if ( ! (cond) ) { return false; }    // a guarda da condition()
      { /* corpo do usuário */ } }
    int nextstate = this.handleEvent(0, Prop_1_transition_c1);   // a transição
    this...Category_fail = nextstate == 2;
    return true;
}
```

Um subagente concluiu daí que a escrituração spec-side (`lastEventName = "g3";` no início do corpo)
está quebrada, porque um evento que reprova a `condition()` retorna antes de escrever. **[arbitrado
aqui] a conclusão é um exagero, e a correção importa para a etapa 1:** um evento que reprova a
guarda **não transita**, logo não é ele que dispara o `@fail`. O evento que dispara o `@fail` é
exatamente um que passou a guarda — e portanto escreveu o nome. **O mecanismo é correto.**

Dois riscos residuais, ambos nomeáveis e pequenos:

- **flags obsoletas.** Um evento que reprova a guarda retorna sem atualizar `Category_fail`, e o
  chamador re-executa os handlers sobre a flag anterior. Onde o `@fail` chama `__RESET`, as flags são
  zeradas e não há re-disparo — o que vale para 20 dos 21. **Sobra exatamente uma spec:
  `KeyPairGeneratorSpec`**, o único `@fail` sem `__RESET` nos dois conjuntos. Lá o registro duplica,
  com o nome correto.
- **dois eventos passando a guarda na mesma chamada.** `jca/KeyGeneratorSpec.mop:47` testa
  `!safeAlgorithms.contains(currentAlgorithmInstance)` — o **campo**, não o argumento —, e no monitor
  recém-criado o campo é `""`, então `g3` dispara junto com `g1`. A ordem de despacho decide o nome.
  É um defeito de spec já na lista de reparos (o falso negativo do `KeyGeneratorSpec`), e a spec emite
  **zero** linhas no comp162.

**O que o `@fail` pode e não pode dizer:**

| campo | disponível no handler? |
|---|---|
| nome da spec | sim (redundante — já é coluna) |
| nome do evento ofensor | **sim**, via escrituração no corpo do evento (acima) |
| estado pré-falha | **não** por `getState()` — dentro do `@fail` ele já devolve o estado **pós**-transição, o sink. Só por escrituração no corpo. E com `st` fora do contrato, deixou de ser necessário |
| classe do objeto monitorado | sim, pelos campos — que podem ser nulos |
| valor observado | sim, mas **é aqui que está o defeito de maior retorno** (abaixo) |

**Declarações do bloco `declarations` são emitidas verbatim** no corpo da classe do monitor,
incluindo métodos privados — verificado em `KeyPairGeneratorSpec`. Duas ressalvas: **não existe
nenhuma declaração `static` no corpus**, então `static final String[] EVENT_NAMES` continua sem
verificação empírica (é o `U (oracle)` de `c-A35`, ainda aberto); e as declarações caem num escopo
onde o gerador já ocupa `Prop_N_state`, `Prop_N_transition_*`, `pairValue`, `RVM_lastevent`, `reset`,
`getState`, `getLastEvent`, `handleEvent`, `clone` — colisão de nome é erro de compilação.

**O nome do evento não é injetivo**, e o gate barato existe: `GCMParameterSpecSpec` tem dois eventos
`c1` (dois métodos, uma linha de transição). O cheque `#métodos *Event( por spec == #linhas
Prop_N_transition_*` pega tanto a colisão de nome quanto o símbolo ERE evaporado. Custo: um grep.

**O item de maior retorno e menor custo do programa inteiro, e ele está enterrado.** As 8.843 linhas
`but found .` do dataset do artigo têm causa nomeável e reparo de uma linha por sítio: **17 dos 18
sítios `but found` do `jca` interpolam um campo do monitor** (`currentAlgorithmInstance`,
`currentProtocol`, `currentKSType`, `currentTransformation`), vazio até um evento de instanciação
disparar na mesma fatia. O único que interpola o argumento é `SecureRandomSpec.mop:82` — e o código
**comentado pelos próprios autores** em `MessageDigestSpec.mop:58` também. Trocar campo por argumento
é a mesma edição, nos mesmos 21 arquivos, na mesma etapa.

**O bloqueio real da etapa 1 é um só: as mensagens que mentem.** São onze confirmadas (as quatro que
a sessão 3 nomeia mais as sete da §8 acima). Reescrever o texto de um relato cuja constante numérica
está errada por um fator de 10, cujo `ErrorType` não corresponde ao que é testado, e cuja lista de
esperados tem metade das entradas reais, é **certificar a mentira com um `code`**. A sessão 3 já diz
isso (§4.4, "pré-condição e não consequência") e está certa — só faltava a lista completa.

**Um risco que a linhagem escalou indevidamente:** o acoplamento entre o texto da mensagem e o
reconhecimento de formato do parser (`logcat_parser.py:306`, `endswith("went into an error state.")`)
é um problema do conjunto **`generic`**, não do `jca`. O `jca` emite pelo `ErrorCollector` e cai no
Formato 2, que é reconhecido pela **estrutura** (contagem de vírgulas dos 6 campos do `ErrorSummary`),
não pelo texto. Reescrever as mensagens do `jca` não derruba o reconhecimento.

**Onde a etapa 1 pode aterrissar** é decisão de pesquisador, não de implementador. O `jca` está
congelado (`INV-INS-109` no sentido gh101, com gate de paridade que roda). A decisão D-A escolheu
criar `jca_v2`, com o argumento de que o `jca` *"parte de um conjunto cujos defeitos nunca foram
procurados"*. **Esse argumento é falso como afirmação de fato, e o custo de (ii) é quantificável:**

- o `jca` tem **mais de 130 defeitos catalogados** — os 18 acusadores, as tabelas `Cipher` cobrindo 2
  famílias contra 8 da regra, as 13 specs com o resíduo Forma B, as 8 leituras sensíveis a
  identidade, mais `predicate_omissions.csv` (20) e `algorithm_naming.md` (9 sítios + 2 defeitos de
  regra novos) — todos em `data/gh101/`, cada um com o reparo já escrito e validado no derivado;
- `divergence_record.csv` diz exatamente quanto (ii) manda re-derivar: **94 hunks** de reparo
  confinados ao derivado (51 `layer-2-repair`, 42 `predicate-graph`, 1 `cipher-import`), em 19
  arquivos — `CipherSpec` 28, `MacSpec` 12, `TrustManagerFactorySpec` 9, `KeyPairGeneratorSpec` 7,
  `SSLContextSpec` 7…;
- e há uma **restrição dura** que nenhum documento contabiliza: `jca/CipherSpec.mop` tem **17
  eventos, exatamente o teto medido do gerador**. A gh101 mediu `n × (2ⁿ − 1)` conjuntos coenable:
  14 eventos geram em 6,9 s / 1,02 GB; 17 geram em 53,5 s / 3,3 GB; **18 estouram com
  `StackOverflowError` em `EnableSet.parseSets`**. Vários itens de C-4 exigem eventos novos no
  `CipherSpec` (desdobrar `f4`, `getIV()` para `callTo(iv)`, `getInstance(String,..)`, ligar
  `plainText`). **`jca_v2` teria de refazer o re-orçamento de 17→14 que a gh101 já fez** — e a lista
  de reparos de D-A não o menciona.

A decisão continua sendo do pesquisador, e a razão dela (não invalidar a reprodutibilidade de E2/E3)
é boa. O que muda é o preço declarado.

### 9.3 As demais mudanças, em detalhe

| mudança | veredito | por quê |
|---|---|---|
| **C-0** (linha de base + definições como código) | **manter; reusar o leitor, copiar a disciplina, não mudar de casa** | Ver a nota abaixo sobre a gh103 — a relação é mais estreita do que parece à primeira vista. E 16 % das ausências das listas de extração são medições do E3 **já feitas** que C-0 mandaria refazer. |
| **C-1a** (aridade `args()` no weaver) | **manter, com a regra de três cláusulas** | A regra original apagaria 66,6 % das linhas legíveis; a correção da sessão 2 está certa. Mas o ganho de **3.151** não é somável ao ganho do reparo de autômato (§5.5), e as 296 do KMF não são atribuíveis. |
| **C-1** (transporte e parser) | **manter; acrescentar duas tarefas** | (a) desacoplar o reconhecimento de formato do texto **antes** de o `generic` ser habilitado; (b) contar os descartes do `logcat_parser` — hoje há pelo menos seis pontos de descarte silencioso, e o `INV-CAN-04` não os alcança. |
| **C-V** (toolkit de validação) | **manter, reduzir, reordenar e acrescentar o que falta de verdade** | Medido item a item contra `scripts/` e `tests/`: **2 dos 8 já entregues** — G-2 existe como script completo (lê as duas formas de monitor) mas **não é pytest**, e G-7 existe integralmente na metade que importa (`gh101_predicate_pairing_check.py` + pytest + 20 omissões). G-5 existe em forma degenerada (mutação de uma constante, manual). **G-1, G-2b, G-3, G-4, G-6 e G-8 são genuinamente ausentes.** E **G-2b não é implementável como enunciado** (§6.2) — substituir por G-2a/G-2b′/G-2c/G-2d/G-6′. C-V não inventaria quatro gates pytest vivos da gh101 (freeze check, inventário congelado, divergence record, conformance record). O item de maior valor não está na lista: o harness diferencial da §6.6. |
| **C-2** (`code` na identidade) | **reabrir** | É um no-op como desenhada (§6.1). A pergunta de pesquisador é se `ev` entra na identidade. |
| **C-3** (mensagem no conjunto nomeado) | **é a etapa 1 — manter e antecipar** | §9.2. |
| **C-4** (autômatos e pointcuts) | **manter; ampliar o catálogo e declarar o teto** | Acrescentar os defeitos da §8 — os parênteses do `SecretKeySpecSpec`, o detector nulo do `SecretKeySpec`, o `c2` inexistente do `GCMParameterSpecSpec`. **Enfrentar D-S9 por escrito** antes de propor absorção. E declarar o teto: `CipherSpec` está em 17/17, e todo item de C-4 que exige um evento novo nessa spec estoura a geração. |
| **C-5** (predicados) | **manter, sem urgência** | O gate que ela precisa já roda; o registro de omissões já existe. |

**Nota — qual é, exatamente, a relação de C-0 com a gh103.** É fácil exagerá-la, e eu exagerei numa
primeira redação. A camada `aperv_tool.analysis` **não é o lugar** desta medição, e ela própria diz
por quê: é genérica por construção (*"No research-question identifier outside `callers/`"*), é
escopada às perguntas da campanha final via `rq_map.toml`, e declara explicitamente
`20260815_gh103_analysis_layer.md`: *"**cmp162 is a fixture, not a corpus. No number computed on it
answers a research question.**"* Pôr a análise das mensagens lá dentro violaria as próprias
fronteiras dela. A relação real são **duas coisas concretas e uma advertência**:

1. **O leitor.** `aperv_tool.analysis.violations` é o leitor canônico do `errors.csv` — tem
   `ERRORS_CSV_HEADER`, levanta se o cabeçalho divergir, extrai `violation_type = parts[3]` e
   **conta** o que não parseia (`unique_msg_unparsed`). A linhagem já registra que o `unique_msg` é
   construído em **quatro** lugares; um script novo de C-0 que releia o CSV por conta própria é o
   quinto. Usar `read_errors_csv` custa uma linha de import.
2. **A disciplina, não a casa.** O *freeze-item rule* (`FreezeItemUnset` em vez de default implícito;
   *"omitting the key is an error, not a way of saying none"*) é exatamente o que **D-F** pede
   — definições registradas antes de qualquer número publicado. E o `Envelope` (*"a bare float cannot
   be emitted"*) é a forma executável da lição de denominador que a linhagem enuncia em prosa. C-0
   deve copiar os dois padrões para onde quer que os seus scripts morem.
3. **A advertência que vale para o programa inteiro.** *"Reproducing a campaign's number proves the
   pipeline is unchanged. It proves nothing whatever about whether the estimator is right — if the
   original was wrong, parity reproduces the error exactly."* É a distinção paridade × correção da
   §2, e é o que separa "a linha de base é reprodutível" de "a linha de base está certa".

**Limite prático a registrar:** `read_errors_csv` **não lê o dataset publicado do artigo** — ele tem
10 colunas e não tem `source`, e o leitor levanta `ValueError` (verificado por execução). Toda
medição de C-0 sobre o corpus do artigo precisa de um caminho declarado à parte, e isso é uma
descontinuidade de instrumento que a linha de base tem de registrar.

### 9.4 As perguntas de Fase 0 são três, não duas

O handoff leva duas ao pesquisador (o destino da WS-8 / conjunto `generic`; e D-B, o oráculo). Falta a
terceira, e é a que decide se uma mudança inteira vale a pena:

> **`ev` (o nome do evento ofensor) entra na identidade de deduplicação?** Se não entrar, C-2 não
> refina nada (§6.1) e a atribuição por evento continua impossível — que é o defeito que o programa
> existe para corrigir. Se entrar, a contagem de violações muda de forma descontínua e todo número
> publicado sobre dedup passa a ter duas eras.

E as duas perguntas existentes ganham contexto novo: a de D-B fica menor do que parecia (é MD5/SHA-1
numa spec, 38 % da categoria e não 97 %), e a da WS-8 ganha um argumento a favor de adiar — o
conjunto `generic` nunca rodou, e os seus 118 arquivos têm defeitos de compilação (§8, item 14) que
nenhuma campanha jamais exercitou.

---

## 10. Onde esta verificação corrigiu a si mesma

1. **Derrubei a conclusão de um subagente sobre a etapa 1.** Ele afirmou que a escrituração spec-side
   do nome do evento está quebrada pela guarda da `condition()`. Está certo sobre o mecanismo e errado
   sobre a consequência: o evento que reprova a guarda não transita, logo não dispara o `@fail`
   (§9.2). Se eu tivesse aceitado, a etapa 1 teria sido declarada inviável.
2. **Derrubei uma hipótese minha sobre o `FINAL:43-44`.** Suspeitei que a afirmação *"all and only
   `InvalidSequenceOfMethodCalls`"* fosse contradita pelas 419 linhas `UnsatisfiedConstraint` mudas.
   Medido: no dataset do artigo o bicondicional é **exato** nos dois sentidos (0 contraexemplos); a
   quebra é do comp162, e o `FINAL` atribui a frase ao artigo. A afirmação está correta como escrita.
3. **Derrubei a minha própria suspeita sobre as "8 réplicas".** Suspeitei que a repetição de 67,74 %
   fosse inflada por replicação. Medido: são shards disjuntos, e **nenhuma** parte da repetição é
   artefato de replicação (§5.3). O erro está no rótulo, não no número.
4. **Não arbitrei** a trajetória 26 → 21 de eventos no slice-raiz entre conjuntos por uma terceira
   derivação, nem a classificação item a item das 131 ausências e parciais; ambas vêm de subagente com
   leitura integral declarada.

---

## 11. O que continua não verificado

- **Nada foi executado em device.** Vale para todo este documento.
- **`static final String[] EVENT_NAMES` não foi verificado empiricamente** — não existe declaração
  `static` no corpus e o gerador não foi rodado. É a única premissa da etapa 1 que continua aberta, e
  fecha com uma geração em scratch.
- **As duas causas das 296 linhas do `KeyManagerFactorySpec` não são separáveis** com os dados atuais
  (§5.5). Separar exige um registro que nomeie o evento — isto é, exige a etapa 1 já landada.
- **Se o `gh56-smoke` é o artefato que produziu as medições publicadas do `jca`** (§5.6). Há uma
  divergência semântica com o controle congelado e o repositório não resolve a proveniência.
- **A confiabilidade da atribuição `source` → statement.** As três triplas em lockstep do
  `KeyManagerFactorySpec` (48/48/48, 35/35/35, 15/16/16 em linhas-fonte consecutivas) sugerem que ou
  a atribuição de `__LOC` está deslocada, ou há um evento a mais disparando. Nos dois casos, a
  granularidade de statement não é confiável.
- **A verdade factual dos 581 itens das listas de extração.** Auditei a cadeia extração →
  consolidação, não o conteúdo de cada item.
- **Os testes Java da gh100 não foram executados.** Verifiquei que os arquivos existem
  (`EmissionCardinalityTest`, `EmissionParityTest`, `WrapperMergeTest`, `WrapperRegistryGuardTest`,
  `OracleLoaderTest`, `TraceComparatorTest`, `DexWeaverDegradationTest`,
  `MonitorCallsPremiseContractTest`); não rodei `mvn` no reator compartilhado.
- **As 421 linhas `but found .` de `Signature`, `MessageDigest` e `Mac`** estão fora da explicação
  medida da gh101, que cobre TMF+SSL. O mecanismo spec-side que a sessão 3 propõe pode ser a
  explicação correta **para elas** — nenhuma das duas partes mediu esse recorte.
- **Se `e204e2a4` afetou outros artefatos da gh101** além do `ExecutionContext`.
- **`predicate_edges.csv` linha a linha**, em particular as linhas que o juiz global cita como
  falsificando a premissa de âncora (`FEN-D-REGISTER-ANCHOR-DRIFT`). Reportei a acusação sem
  confirmá-la nas linhas.

---

## 12. Referências

### A linhagem auditada, arquivo a arquivo

Tudo em `rv-android/docs/`. Os 18 primeiros somam **9.032 linhas** e estão untracked.

| # | Arquivo | Linhas | Papel |
|---|---|---:|---|
| 1 | `20260815_javamop_mensagens.md` | 982 | **o plano**: causa-raiz L1–L8, WS-1..8, D-1..8, D01–D50. O único que conhece o conjunto `generic/` |
| 2 | `20260815_javamop_mensagens_analise_handoff_prompt.md` | 311 | encomenda da revisão do plano |
| 3 | `20260815_javamop_mensagens_analise.md` | 797 | revisão adversarial do plano, seis passes |
| 4 | `20260815_javamop_mensagens_validacao_prompt.md` | 349 | **o prompt dado aos quatro LLMs externos** — a peça que a §7 audita |
| 5 | `20260815_javamop_mensagens_claude_fable5.md` | 751 | validação externa 1 — a que carregou o peso |
| 6 | `20260815_javamop_mensagens_gpt5_codex.md` | 480 | validação externa 2 — declara-se de primeiro estágio |
| 7 | `20260815_javamop_mensagens_gemini36flash.md` | 286 | validação externa 3 |
| 8 | `20260815_javamop_mensagens_deepseek_v4_flash.md` | 237 | validação externa 4 |
| 9 | **`20260815_javamop_mensagens_FINAL.md`** | **521** | **o documento de design** — entrada de Fase 0, C-0..C-5, D-A..D-I, G-1..G-8, O-1..O-9 |
| 10 | `20260815_javamop_mensagens_FINAL_analise.md` | 648 | sessão 1 — análise adversarial do FINAL; achou os 18 órfãos |
| 11 | `20260815_javamop_mensagens_FINAL_analise_handoff_prompt.md` | 308 | encomenda da sessão 2 |
| 12 | `20260815_javamop_mensagens_FINAL_analise_lacunas.md` | 818 | sessão 2 — lacunas fechadas, **as quatro decisões (§6)**, **as 11 correções (§7.1)** |
| 13 | `20260815_javamop_mensagens_validacao_handoff_prompt.md` | 425 | encomenda da sessão 3 |
| 14 | **`20260815_javamop_mensagens_validacao.md`** | **850** | sessão 3 — validação da linhagem; as 9 correções novas e os 3 achados estruturais |
| 15–18 | `20260815_javamop_extracao/{claude_fable5,gpt5_codex,deepseek_v4_flash,gemini36flash}.md` | 509 / 423 / 169 / 168 | as quatro listas de extração — 581 itens casados contra o FINAL |
| 19 | `20260816_javamop_mensagens_correcao_handoff_prompt.md` | 610 | o handoff de correção — as 11 + 9 correções e as cinco fases |
| **20** | **`20260816_javamop_mensagens_verificacao.md`** | — | **este documento** |

### Documentos do mesmo dia, fora da linhagem, mas relevantes ao plano

- `20260815_gh103_analysis_layer.md` — a camada de análise da gh103 (paridade × correção; *freeze
  items*; *"cmp162 is a fixture, not a corpus"*). Ver a nota de §9.3.
- `20260815_gh103_sessao2_handoff_prompt.md` — o handoff da sessão 2 da gh103.

### Outros documentos de análise relacionados

- **Auditoria do `jca_android`:** `docs/20260808_validar_specs_jca_android.md` e a árvore
  `audit/20260808_validacao_jca_android/` (`fase0/pre_registro.md` = escopo e critério READY;
  `global/juizglobal_relatorio.md` §10 = veredito REPROVADA 22/22, G11 sobre a gh101;
  `global/juizglobal_gates.csv`)
- **Planejamento anterior das specs:** `docs/20260806_plano_specs_jca_android.md` (o D1 que a gh101
  reverteu com D-S0)
- **Estudo 03:** `docs/20260810_plano_prontidao_estudo03.md`, `docs/20260812_comp162.md`,
  `docs/20260812_registro_execucao_prontidao_e3.md`, `docs/20260813_comp162ajc.md`
- **gh100** (`openspec/changes/gh100-weaver-emission-fidelity/`): `proposal.md`, `design.md` (D-E1,
  D-A1..A3, D-B1, D-O1..O6), `tasks.md` (58, 3 abertas), `specs/instrumentation/spec.md`
  (INV-INS-104..110), `evidence/census_{pre,post}_repair.json`
- **gh101** (`openspec/changes/gh101-jca-spec-conformance/`): `proposal.md`, `design.md` (D-S0..S14,
  em especial **D-S9**), `tasks.md` (84/84), `specs/instrumentation/spec.md` (INV-INS-109..115),
  `specs/experiment/spec.md`
- **Registros de dados da gh101, não citados pela linhagem:** `data/gh101/README.md` (705 l.),
  `frozen_set_debt.md` (250 l.), `algorithm_naming.md`, `conformance_record.csv`,
  `divergence_record.csv`, `predicate_omissions.csv`, `predicate_edges.csv`,
  `predicate_inventory_{jca,jca_android}.csv`, `edge_counts_per_file.csv`
- **Gates já executáveis:** `scripts/gh101_monitor_transition_check.py`,
  `scripts/gh101_predicate_pairing_check.py`, `scripts/gh101_divergence_record.py`,
  `scripts/gh101_conformance_check.py`, `tests/parity/test_gh101_specset_gates.py` (5 testes)
- **Auditoria:** `audit/20260808_validacao_jca_android/fase0/pre_registro.md`,
  `global/juizglobal_relatorio.md` (§10 veredito, G11 sobre a gh101), `global/juizglobal_gates.csv`
- **Camada de análise (gh103):** `docs/20260815_gh103_analysis_layer.md`,
  `modules/aperv-tool/src/aperv_tool/analysis/`,
  `openspec/changes/archive/2026-08-15-gh103-campaign-analysis-layer/`
- **Datasets:** `/home/pedro/…/ase-journal/dataset/results/errors.csv` (97.018 l., 10 colunas, **sem
  `source`**); `experimento-comp162/results/*/*/errors.csv` (8 shards disjuntos, 112 APKs, 19.664 l.,
  11 colunas)
- **Oráculos de monitor:** `results/{gh56-smoke, gh99_jca_android_monitors, gh101_group8_jca_android,
  gh101_group8_jca_frozen_control}/monitors/MultiSpec_1RuntimeMonitor.java` (66.359 linhas lidas)
- **Specs:** `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/` (191
  arquivos, 11.984 linhas, lidos integralmente)
- **Runtime e weaver:** `rvsec/rvsec-core/` (`ErrorDescription.java`, `ErrorSummary.java`,
  `ExecutionContext.java`, `Property.java`), os dois `ErrorCollector`,
  `rv-monitor-rt/…/ViolationRecorder.java`,
  `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (`WrapperEmitter`, `PointcutMatcher`,
  `PackageFilter`)
- **Consumidores:** `modules/rv-coverage/…/logcat_parser.py`, `modules/rv-platform/…/result_processor.py`,
  `modules/rv-android-core/…/domain/log.py`, `modules/aperv-tool/…/analysis/violations.py`
