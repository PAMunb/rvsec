# Conformidade MOP–CrySL — análise de projeto de um módulo Maven

**Data:** 21 de agosto de 2026
**Escopo:** análise, sem implementação
**Alvo:** novo módulo no reator `rvsec`
**Corpora:** `jca`, `jca_android`, `MetaCrySL/generated/api30`, `rvsec-cognicrypt/CrySL-Rules`

Este documento registra o levantamento de um componente para verificar mecanicamente se as
especificações JavaMOP do RVSec dizem o que as regras CrySL de que foram traduzidas exigem — e para
separar a divergência deliberada da não explicada.

Foi feito em quatro rodadas. A primeira levantou o terreno e concluiu que o desenho estava certo mas
que a corretude dos vereditos era hipótese não testada. A segunda testou: executou parsing, censo e
comparação de autômatos. A terceira inverteu a pergunta — *dá para gerar `.mop` a partir da regra?* —
e, ao respondê-la, fechou por execução as decisões de engenharia que as duas primeiras deixaram em
aberto: linguagem, escrita, forma do módulo. A quarta executou as dez validações que sobravam, e é
de onde vêm as correções marcadas ao longo do texto. Onde uma conclusão veio de leitura e não de
execução, está dito.

> **Estado em 21/08/2026, fim da quarta rodada.** As dez validações fecharam; nenhuma derrubou uma
> conclusão deste documento, e a única que derrubou uma *via* (mirar a API 30 no classpath do
> `CrySLParser`) saiu com substituto medido. O registro completo está em
> `docs/20260821_validacoes_conformidade_mop_crysl.md` e o arnês reproduzível em
> `docs/handoff/20260821_arnes_validacoes/`. O que muda daqui para a proposta está reunido no §13.

> **Quinta rodada, 22/08/2026 (R5) — revisão externa adjudicada.** Três modelos revisaram o documento
> de forma independente (`docs/analise_mop2crysl_*.md`) e oito verificadores remediram as suas claims
> contra a fonte primária. As correções marcadas `(R5)` ao longo do texto vêm daí, e o registro
> completo — inclusive as claims **refutadas**, que não devem ser reintroduzidas — está em
> `docs/20260822_adjudicacao_revisoes_externas.md`. Ao contrário da quarta rodada, esta **derrubou
> conclusões**: o alfabeto do modelo canônico (§12), a generalidade de N1 (§5.2), o que o M2-eff mede
> (§5.1), a justificativa da costura entre processos (§12) e a saída Scala 3 (§11.5).

> **Sexta rodada, 22/08/2026 (R6) — verificação de consistência.** Seis verificadores confrontaram
> este documento com os seus três artefatos irmãos, com o corpus no `HEAD` e consigo mesmo, e o
> relatório está em `docs/20260822_verificacao_consistencia_conformidade.md`, com o arnês em
> `docs/handoff/20260822_arnes_verificacao_r6/`. As marcas `(R6)` ao longo do texto são os **reparos
> mecânicos** dessa rodada: números certos num lugar e desatualizados noutro, ponteiros vencidos, e
> ressalvas que ficaram sem alcançar a frase que derrubavam. **Os reparos de julgamento não foram
> aplicados** — estão listados na §8.2 do relatório e são decisão do pesquisador. O que a rodada não
> reparou, e é o mais caro, é que quatro dos cinco vereditos de M2 do §5.2 nunca foram revisitados sob
> o modelo de alfabeto que o §12 passou a adotar.
>
> **Alvo móvel, medido:** o `HEAD` moveu-se **durante** a verificação (`f188c55b` → `8a33bc41`), e o
> commit `1fa22acb` migrou os sete últimos arquivos do `jca_android`. A premissa que abre o §7 —
> *"Dois substratos coexistem"* — deixou de valer, e a linha de baixo da tabela de teto do §5.4
> ("teto com migração completa") passou a ser o presente. As duas correções estão na §8.2 do
> relatório porque exigem julgamento, não troca de número.

> **Sétima rodada, 24/08/2026 (R7) — adjudicação, e as duas medições pendentes.** A R6 levantou 21
> pontos de julgamento e não os resolveu; a R7 os decidiu, junto com as sete decisões que a R5 deixara
> em aberto. As **28 decisões** estão em `docs/20260824_adjudicacao_plano_conformidade.md` §4, e as
> marcas `(R7)` ao longo deste texto são os **vinte e cinco** reparos que delas decorrem — três
> decisões não geram reparo de texto (J-03, J7 e J-06). Cada marca cita o texto anterior, pela mesma
> razão que as `(R5)`/`(R6)`: para que a rodada seguinte saiba o que foi trocado e por quê.
>
> As duas medições que este documento declarava como **pré-requisito da abertura da change** foram
> executadas e estão fechadas em `docs/20260824_medicoes_pre_change_conformidade.md`, com o arnês em
> `docs/handoff/20260824_arnes_adjudicacao/`: as 129 linhas de assinatura sob leitor novo por regra
> (são **141**, e o `android.jar` continua sem mudar uma linha), e o arnês do gh104 contra as cinco
> specs globais. A segunda produziu resultado novo — ver §5.5.
>
> **O corpus andou, e é ele que muda o veredito da R6.** O `jca_android` tem **24** specs, não 23;
> `ExecutionContext` saiu dele por inteiro; sete das linhas de defeito do §9 acusam defeitos que o
> gh105 já reparou — e todas continuam verdadeiras do `jca` congelado, que é onde as medições
> publicadas moram. Daí a coluna `conjunto` do §9. E **uma** das reparações que o §9 listava como
> pendente introduziria hoje o erro que pretendia corrigir: ver a marca `(R7)` no fim do §9.

---

## 1. O reenquadramento

O pedido original foi um tradutor `.mop` → `.crysl`, com a comparação de similaridade como possível
extensão. A investigação inverte a ordem: **a comparação é o produto; a tradução é o meio**, e o
texto `.crysl` gerado é subproduto.

Três razões, em ordem de peso:

1. **A regra sintetizada não tem consumidor.** As regras originais já existem. Gerar uma versão pior
   delas não alimenta o CogniCrypt nem nada mais no pipeline.
2. **A métrica determina quanta tradução é necessária.** Se a comparação de `ORDER` é equivalência
   de linguagens, o que se precisa é de um autômato — não de texto formatado. Fixar a métrica
   primeiro impede construir tradução demais.
3. **O terreno comum não é o texto.** Comparar `.crysl` gerado contra `.crysl` original de forma
   textual é frágil e sem sentido semântico.

A arquitetura que decorre disso:

```
.mop     ──lift──┐                     ┌──▶ comparar    ──▶ veredito + testemunha   [M0–M4]
                 ├──▶ MODELO CANÔNICO ──┤
.crysl   ─parse──┘                     ├──▶ mop.lower   ──▶ `.mop` gerado + portão de round-trip
                                       ┊
                                       ┄▶ crysl.lower  ──▶ `.crysl` legível   [FORA DE ESCOPO]
```

> **Reparado em 24/08/2026 (R7) — J-07 e J-14.** A figura desenhava **uma** seta de emissão, e era a
> do `mop2crysl`, que o §12 declara sem consumidor conhecido. Passa a mostrar as **duas** saídas que
> têm consumidor — o veredito, que é o produto do §1, e o `.mop` gerado, que é o produto do §10 e o
> que serve o portão de round-trip do §12 — e a terceira tracejada, porque J-14 a tira do escopo desta
> change. É a primeira coisa que um revisor externo vê, e passa a dizer o que o §12 decide.

A terceira rodada reabriu essa escolha por um flanco que a primeira não tinha considerado: a
direção **`.crysl` → `.mop`**. O argumento que matou o tradutor original não se aplica a ela — o
`.mop` sintetizado tem consumidor, que é o próprio pipeline do RVSec. O §10 mede essa direção e
conclui que ela é o produto mais forte dos dois, sem que isso desloque o comparador: os dois
partilham modelo, autômato e portão de validação, e é por isso que moram no mesmo componente.

O componente é um **verificador de conformidade a três bandas**: o que a spec realmente faz
(extraído do código), o que dizemos que ela faz (as tabelas CSV e o Javadoc de `Property`), e o que a
regra exige. O valor está nas discordâncias entre as três — e a segunda rodada mostrou que elas
discordam em pontos concretos e localizáveis.

---

## 2. São quatro artefatos, não dois

Este é o ponto metodológico que decide se os números significam alguma coisa.

```
        R_java  ────MetaCrySL────▶  R_android          (CrySL-Rules → generated/api30)
          │                            │
    tradução manual              tradução manual
          ▼                            ▼
        S_java  ───gh100..105────▶  S_android          (jca → jca_android)
```

Há dois eixos de divergência, com sinais opostos:

- **Vertical — divergência de tradução.** É ruído. É o que se quer medir.
- **Horizontal — divergência de plataforma.** É deliberado. É a contribuição do artigo.

Se o comparador rodar `S_android` contra `R_java`, mistura os dois e acusa como infidelidade
exatamente a adaptação Android. O anexo `ase-journal/docs/20260816_analise_tematica_anexos/04_assimetria_specs.md`
já demonstra que a distinção é decisiva: as cinco allow-lists "erradas para Android" são *verbatim
idênticas* à regra CrySL original — a inadequação é herdada do Java SE, não introduzida na tradução.

**Caso verificado.** Em `jca_android/MessageDigestSpec.mop` a allow-list aceita `MD5` e `SHA-1`.
Contra `CrySL-Rules/MessageDigest.crysl` (`{SHA-256, SHA-384, SHA-512}`) isso pareceria alargamento
grave. Contra `generated/api30/MessageDigest.cryptsl:63` é transcrição literal, e o
`divergence_record.csv` declara o custo: 5.892 de 6.048 linhas deixam de ser reportadas. Um
comparador de banda única daria o veredito errado.

### O sinal que a segunda rodada acrescentou

Numa parte grande do conjunto, a linguagem aceita pelo autômato é a *ordem* correta, não o *uso*
correto: eventos de uso incorreto foram deliberadamente absorvidos, com a acusação movida para o
corpo do evento. Contra a cláusula `ORDER` isolada isso é a comparação certa; contra "conformidade
com a regra inteira" erra em todos esses casos, sempre no mesmo sentido. **O protocolo tem de
declarar qual das duas está medindo.**

> **Reparado em 24/08/2026 (R7) — J-12: a regra de contagem, e o par de números.** Esta frase dizia
> **"12 das 23 specs"** e nunca declarou a regra que produz o 12. Sob a regra **R-abs** — `addError`
> em corpo de evento, antes da linha `ere`/`fsm`, comentários removidos — em `5fbe8173` são
> **18 das 24 specs de `jca_android`** e **15 das 23 de `jca`**. A regra foi rederivada em cinco
> commits: o `jca` dá 15 em todos eles, e o `jca_android` foi de 15 a 16 a 18. Testadas três regras
> mais estreitas, exigindo `ErrorType.<X>` no corpo: `UnsatisfiedConstraint` dá 4/15,
> `ForbiddenMethod` 0/1 e `InvalidSequenceOfMethodCalls` 1/0. **Nenhuma regra reconstruída dá 12.**
> O número publicado não é conferível, e o reparo não é caçar a regra perdida — é publicar as duas
> juntas. Arnês: `docs/handoff/20260824_arnes_adjudicacao/scripts/absorve.py`.
>
> E o fenômeno em si deixa de precisar de regra ad hoc: **M0** (§5.5) o mede como propriedade da AST,
> que é o que o torna comparável entre conjuntos e entre commits.

---

## 3. Metade já existe — a estrutural ad hoc, a comportamental não

O mapeamento CrySL↔JavaMOP já foi feito à mão e está espalhado por seis lugares, nenhum durável.

> **Carimbo e convenção, acrescentados em 22/08/2026 (R6).** Os tamanhos abaixo são **linhas totais
> do arquivo**, medidas no commit `8a33bc41`. Antes desta correção a coluna misturava três commits e
> duas convenções: o `order_alphabet_map.csv` estava em linhas totais, o `predicate_graph.csv` (73) e
> o `constraint_table.csv` (59) em linhas **de dados** e num commit anterior, e o
> `divergence_record.csv` trazia **181**, que é o valor do commit `a7e97294` — anterior ao `d64f3a40`
> a que o resto do documento está atado. Três dos quatro CSV se movem a cada tarefa do gh105
> (`predicate_graph.csv` foi de 86 linhas em `d64f3a40` a 46 hoje); o número só significa alguma coisa
> com o commit ao lado. `Property.java` é a exceção da coluna: conta **constantes**, não linhas.
>
> **Recarimbado em 24/08/2026 (R7) — J-20.** Os tamanhos passam a ser os de **`5fbe8173`**. Três dos
> quatro CSV cresceram desde `8a33bc41`: `order_alphabet_map.csv` **121 → 207** (a tarefa 7.1 fechou o
> mapa), `predicate_graph.csv` **46 → 71** e `divergence_record.csv` **283 → 289**;
> `constraint_table.csv` continua em **60**. A contagem de `Property.java` foi reconferida e continua
> **26** — e vale registrar a armadilha, porque ela custou uma medição errada dentro da própria R7: a
> regex que pede quatro espaços de indentação devolve 25, porque `GENERATED_KEY` está indentado com
> **tabulação** (`Property.java:8`), e a vigésima sexta, `PREPARED_KEY_MATERIAL`, é a última do enum e
> não tem vírgula. A regra certa conta identificadores do enum, não linhas que casam um recuo.

| Artefato | Tam. | O que carrega |
|---|---|---|
| `ase-journal/docs/20260816_analise_tematica_anexos/04_assimetria_specs.md` | 664 l. | Tabela de paridade de allow-lists (7 idênticas / 3 alargadas / 1 estreitada), matriz por tipo de erro CogniCrypt, cláusulas CrySL sem contraparte |
| `data/jca_android/order_alphabet_map.csv` | 207 l. | `spec, mop_event, order_symbol, symbol_kind, rule, rule_line, disposition` |
| `data/jca_android/predicate_graph.csv` | 71 l. | Cada sítio de predicado com a cláusula CrySL que traduz, polaridade, aridade, mecanismo, pertinência ao autômato |
| `data/jca_android/constraint_table.csv` | 60 l. | Vereditos `DIVERGENTE` / `CRYSL-NAO-IMPLEMENTADO` / `MOP-MAIS-RESTRITIVO` / `MOP-SEM-BASE` |
| `data/jca_android/divergence_record.csv` | 289 l. | Cada divergência deliberada, com evidência primária e custo declarado |
| `rvsec-core/.../br/unb/cic/mop/Property.java` | 26 const. | Os nomes de predicado projetados. **Corrigido em 22/08/2026 (R5):** são 26 constantes, não 24, e apenas **3** têm Javadoc citando a cláusula CrySL (`GENERATED_CIPHER`, `MACED`, `PREPARED_KEY_MATERIAL`) — as outras 23 não têm comentário nenhum |

**O maior precursor não é ad hoc, e faltava nesta lista** — acrescentado em 22/08/2026 (R5):

| Artefato | Tam. | O que faz |
|---|---|---|
| `rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` | 1255 l. | Replica um traço de chamadas de API por um **snapshot de monitor gerado** e registra o que ele acusa. Gramática de traço própria (`bind`, `->`); resolve cada chamada contra os pointcuts do próprio snapshot, lidos de `MultiSpec_1MonitorAspect.json`, para que os dois lados não precisem partilhar alfabeto; *class loader* novo por traço, porque o gerado guarda as tabelas de indexação em campos `static`; `Outcome.unresolved` separa "não acusado" de "não replicado" |
| `…/harness/TraceRunnerTest.java` | 243 l. | Auto-teste JUnit do próprio runner |
| `scripts/gh104_diff_harness.py` | 489 l. | Replica um arquivo de traços por **dois** snapshots e classifica cada diferença em `unchanged`/`moved`/`removed`/`introduced`; `--selftest` com uma mutação autorada por veredito |
| `data/gh104/traces/` | 94 traços | Corpus versionado, 1 a 9 por spec |
| `data/gh104/evidence/harness/` | 162 arq. | Evidência por spec, 23 por rodada |

**Um precursor aposentado, acrescentado em 24/08/2026 (R7) — J-21.** O `rvsec-mop-defsuses` era o
módulo do reator que fazia análise de definições e usos sobre `.mop`, e a R6 pedia que ele entrasse
aqui como precursor. **Entra como aposentado, que é informação melhor:** a tarefa 7.3 do gh105 está
concluída e o módulo saiu do reator — ausente de `rvsec/rvsec/pom.xml` `<modules>` e do disco. Vale
como precedente de que um módulo desta família **pode** ser retirado quando o seu trabalho encontra
domicílio melhor, que é exatamente o que a seção "o que morre" do §12 propõe para os comparadores
ad hoc.

O `TraceRunner` enuncia a tese que este documento precisa levar a sério: *"a structural gate measures
the artefact and not its behaviour"* (`:36-42`) — e cita os dois defeitos que a linhagem entregou
como sucesso (a fusão de *wrappers* do gh100, com `wrappersGenerated 96 -> 84` reportado como êxito,
e os reparos de autômato do gh101, que moveram a acusação para a chamada seguinte). **M1, M2, M3 e
M4 são todas estruturais.** O componente é a metade estrutural de um desenho de dois instrumentos
cuja metade comportamental já existe, tem auto-teste, corpus versionado e evidência reproduzível.

E há **~10.400 linhas de Python** em 18 scripts `rv-android/scripts/gh10*.py`, mais os scripts das
duas auditorias em `audit/`. Contando o que faz a mesma coisa:

- **Sete implementações independentes da comparação de `ORDER`** — 2.701 linhas, **sete `md5`
  distintos**: nenhuma é cópia de outra. Seis vivem em `audit/20260808_*` (`alfa_automata_check` ×3,
  `alfa_language_check` ×2, `juiz_walk_batchB`) e a sétima é `scripts/gh105_order_gate.py`.
- **Onze leitores de CrySL** distintos, todos ad hoc — 9.224 linhas.
- **14 dos 18 scripts parseiam `.mop` por expressão regular.**

> **Remedido em 24/08/2026 (R7) — J-05.** Este bloco dizia **três** comparadores e **cinco** leitores.
> Sob a regra declarada — *comparador* = arquivo Python que parseia um `ORDER` ou um `ere`/`fsm` e
> decide sobre ele; *leitor* = arquivo Python que abre um `.crysl`/`.cryptsl` — o censo em `5fbe8173`
> dá 7 e 11. Um arquivo, `audit/…/batchD/alfa_language_check.py`, conta nos dois: é a duplicação em
> estado puro. A disposição de cada categoria, com o critério de corte escrito, está na seção "o que
> morre" do §12. O argumento desta seção fica mais forte, não mais fraco: a duplicação não aconteceu
> três vezes, aconteceu sete.

A justificativa do componente não é "seria bom automatizar". É que a duplicação já aconteceu três
vezes por falta de um domicílio durável, e a análise manual não escala para um alvo que muda a cada
sítio fiado — o `jca_android` está sendo reescrito agora, e o progresso do gh105 é carimbado no §13
(corrigido em 22/08/2026, R6: esta linha dizia "30 de 74" e nunca foi atualizada; o §13 dizia 36 de
74, e no fecho daquela rodada eram 39 de 74. **Atualizado em 24/08/2026, R7: são 72 de 74 em
`5fbe8173`**, e as duas que restam — 8.8 e 8.9 — estão bloqueadas no arquivamento do gh104, não em
trabalho de spec. O alvo parou de se mover *nesta* frente, e é isso que torna a change abrível). O anexo 04 é
uma fotografia do conjunto `jca` congelado; o componente o transforma num invariante verificável.

---

## 4. O que a segunda rodada mudou

### 4.1 Correção — a testemunha do MessageDigest estava errada

A primeira versão desta análise afirmava que `MessageDigestSpec` era *mais permissiva* que a regra,
com testemunha `g1 g1 d2`. **É falso.** Sob a normalização correta as duas linguagens são
**idênticas**. A testemunha morre por duas razões independentes:

1. A guarda do `g4` lê o **campo** do monitor (`currentAlgorithmInstance`), não o argumento — e o
   corpo do `g1` escreve esse mesmo campo. Como o `g1` é declarado antes e a `condition` compila
   para dentro do método do evento, o advice do `g1` roda inteiro — guarda **e** corpo — antes de a
   guarda do `g4` ser avaliada, e ela fica falsa. **Exatamente um dos dois dispara por chamada.**
   É a classe que o gh104 batizou de `guard-on-field`.
2. **Fatiamento paramétrico** — dois `getInstance` devolvem dois objetos, logo dois monitores, e um
   monitor nunca vê dois eventos criadores.

Colapsar `g4 ≡ g1` foi a normalização errada; apagá-lo é a certa.

> **Correção de 21/08/2026, medida em traço (V8).** A primeira redação deste item dizia que `g1` e
> `g4` *co-disparam* e que uma chamada concreta produz a palavra `g4 g1`. As duas metades estão
> erradas. Uma spec sonda que replica a forma exata do `MessageDigestSpec`, instrumentada com `ajc`
> e executada na JSE, emite **só `g1`** para um algoritmo aceito e **só `g4`** para um rejeitado —
> a palavra é `g1` ou `g4`, nunca as duas. E, se co-disparassem, a ordem seria `g1 g4` (ordem de
> declaração, confirmada por sonda separada), que a ERE `(g4* g1 | …)` rejeitaria. A conclusão da
> seção **continua de pé, por razão mais forte**: a testemunha `g1 g1` morre por fatiamento (item 2,
> agora medido) e o par `g1`/`g4` é mutuamente exclusivo por construção da guarda. O veredito
> EQUIVALENTES foi reconfirmado de forma independente em §5.2. Evidência:
> `docs/20260821_validacoes_conformidade_mop_crysl.md`, V8.

### 4.2 Achado — o gate `gh105_order_gate.py` lê o ORDER com precedência invertida

A gramática CrySL (`audit/20260808_validacao_jca_android/fase0/upstream_CrySL_e92f5607.xtext:103-134`)
põe `Sequence` como produção mais externa e `Alternative` dentro dela — ou seja, **`|` liga mais
forte que `,`**. O gate descarta as vírgulas e reusa um parser de expressão regular, onde a
concatenação liga mais forte que a alternativa. O docstring declara a suposição literalmente:

> "Sequence is written `a, b` in an `ORDER` and by juxtaposition in an `ere`, and the two mean the
> same thing, so one parser reads both once the comma is gone."

Não significam. Executado sobre o `ORDER` do `Cipher.cryptsl`:

```
Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+

como o gate lê (`,` mais forte)          como a gramática manda (`|` mais forte)
  f2 sozinho                 aceito        f2 sozinho                 rejeitado
  getInstance;init;doFinal   rejeitado     getInstance;init;doFinal   aceito
  getInstance;init;upd;doFin rejeitado     getInstance;init;upd;doFin aceito
```

Sob a leitura do gate, a regra rejeitaria o uso mais banal de `Cipher` que existe e aceitaria um
`doFinal()` solto. **A regra está certa; o gate está errado.**

Raio de explosão medido: das 33 regras `api30`, **exatamente uma** mistura `,` e `|` no mesmo grupo
sem parênteses — `Cipher`, que é justamente a que o gate reporta como falha. O conserto é uma
produção a mais no parser.

### 4.3 O que se confirmou

- **Polaridade não é risco.** Nenhuma das 23 specs inverte: zero `addError` dentro de qualquer
  `@match`. O `@match` só marca estado aceitante ou grava predicado.
- **Múltiplos `alias matchN` não quebram a comparação** — são a codificação do `after <Evento>` do
  CrySL. O `alias match2 = s3` do `CipherSpec` traduz `encrypted[…] after Updates`, e o comentário
  no arquivo diz isso.
- **Zero eventos órfãos em `jca_android`; 18 em `jca`.** A comparação mecânica é viável no conjunto
  novo e seria degenerada no congelado.

---

## 5. As métricas

**Cinco** métricas: uma de vitalidade, que roda primeiro, e quatro de conteúdo, uma por seção do
CrySL. Cada uma com testemunha concreta em vez de percentual solto.

| | O que compara | Saída |
|---|---|---|
| **M0** Vitalidade | o `.mop` contra si mesmo e contra o `android.jar` | vive / recusa tipada. **Roda antes de M1–M4 e as bloqueia** quando recusa — ver §5.5 |
| **M1** Eventos | conjuntos de assinaturas concretas | cobertura + as duas diferenças listadas; alimenta o alinhamento de rótulos que M2 usa |
| **M2** Ordem | L(A_mop) vs L(A_crysl) | equivalente / mais permissiva (*candidata* a falso negativo) / mais estrita (*candidata* a falso positivo) / incomparáveis, + palavra-testemunha mais curta, com o seu estatuto `ABSTRACT` ou `CONCRETE` (§5.2). Corrigido em 22/08/2026 (R6): os rótulos anteriores afirmavam falso positivo e falso negativo **do monitor**, que é o que o §5.1 nega que qualquer variante de M2 possa estabelecer |
| **M3** Constraints | por variável: literais casados, divergentes, ausentes, não-reconhecidos | veredito por cláusula |
| **M4** Predicados | grafo `ENSURES`/`REQUIRES`/`NEGATES` | arestas presentes, ausentes, invertidas |

> **Acrescentado em 24/08/2026 (R7) — J3, decisão do pesquisador.** Esta tabela tinha **quatro**
> linhas, e a primeira frase da seção dizia *"Quatro métricas, uma por seção do CrySL"*. M0 entra
> porque um veredito de ordem sobre um monitor que não roda é vazio, e porque as três perguntas que
> ela faz são decidíveis dos artefatos que o desenho já produz. O §5.5 a define e traz a evidência
> medida que a motiva.

### 5.1 M2 tem duas variantes legítimas

| Variante | Entrada | Pergunta que responde |
|---|---|---|
| **M2-decl** | `ere`/`fsm` do `.mop` | "a especificação que escrevi diz o mesmo que a regra?" |
| **M2-eff** | `Prop_1_transition_*` do monitor gerado | "que autômato o gerador de fato emitiu?" — **e nada além disso** |

As duas são **observações diferenciais uma da outra**, e nenhuma responde sozinha "o monitor que
rodou aceita a mesma linguagem que a regra?". A diferença entre elas não é hipotética — o caso do
`SecureRandom` está documentado: a regra ordena `Ends*`, mas o estado `end` do monitor não tem
transição para `next2`.

> **Corrigido em 22/08/2026 (R5) — M2-eff não mede o que esta seção dizia que media.** A
> `condition(...)` compila para **dentro** do método de evento, a montante de `handleEvent`, e as
> tabelas não guardam vestígio dela:
>
> ```java
> final boolean Prop_1_event_g1(String alg, KeyGenerator k) {
>     if ( ! (ConscryptAliasTable.matches("KeyGenerator", alg, safeAlgorithms)) ) { return false; }
>     { keyGenerator = k; currentAlgorithmInstance = alg; }
>     int nextstate = this.handleEvent(0, Prop_1_transition_g1);   // a tabela só entra aqui
> ```
>
> Tecido com `ajc` e executado em JSE, `KeyGenerator.getInstance("DES"); generateKey()` — **ordem
> correta pela regra** — produz `KEYGENERATOR-ALG-00` *e* `InvalidSequenceOfMethodCalls`
> `KEYGENERATOR-ORDER-00`: uma acusação de ordem contra um programa que não viola ordem. Com `"AES"`,
> nenhum relatório. O mecanismo: `g1` reprova a guarda e não transita, `g3` transita `0 → 0`, e `gk1`
> sai de 0, onde `Prop_1_transition_gk1[0] = 5` = *fail*.
>
> Agravante: o monitor é criado (`FindOrCreateEntry`) **antes** de a guarda ser avaliada, então uma
> `condition` reprovada deixa um monitor vivo no estado 0 e o evento seguinte é julgado dali.
>
> O autômato efetivo é `⟨tabelas, guardas, ordem de fusão de advice⟩`; o M2-eff lê só a primeira
> componente e o M2-decl não vê a guarda (ela não aparece no `ere`). Para responder a pergunta
> original é preciso **executar traço** — o que o arnês do gh104 (§3) já sabe fazer.

> **Promovido em 24/08/2026 (R7) — J-02.** Este caso não é anomalia a esconder; é a **demonstração
> interna** da regra que o §1 enuncia, feita dentro do próprio corpus e medida por execução. Não há
> contradição formal a resolver: o `ORDER` do `KeyGeneratorSpec` **é** equivalente ao `ere` sob N1
> (§5.2) **e** o monitor acusa ordem contra um traço que a regra aceita. As duas coisas são
> verdadeiras ao mesmo tempo porque medem objetos diferentes — o autômato declarado e o monitor que
> rodou. É por isso que o caso é citado como evidência, e é a motivação medida de M0 (§5.5) existir:
> **equivalência de `ORDER` é estritamente mais fraca que conformidade**, e é o segundo dos quatro
> eixos da moldura do §13.

O monitor gerado expõe o autômato de forma inteiramente mecânica:

```java
static final int Prop_1_transition_g1[] = {4, 4, 5, 5, 5, 5};   // próximo estado por estado atual
static final String[] RVM_eventNames = {"g1","g2","load","store","ge1","se1","gk1"};
KeyStoreSpecMonitor_Prop_1_Category_fail  = Prop_1_state == 5;   // estado de falha, explícito
KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;   // estado aceitante, explícito
```

Três observações de implementação, todas verificadas nos 23 monitores gerados a partir do `jca`
congelado (carimbo acrescentado em 24/08/2026, R7 — J-20: o número descreve o censo que foi feito, e
não o conjunto de hoje; o `jca_android` de `5fbe8173` tem **24**, e este censo não foi refeito sobre
ele):

- **O gerador minimiza e renumera os estados.** `start` e `unsafeAlg` são fundidos quando têm
  transições idênticas. Isso é boa notícia: o lado MOP já chega minimizado. Os nomes de estado se
  perdem, mas os nomes de *alias* sobrevivem como variáveis de categoria, e é deles que se recupera
  o `after`.
- **Duas formas de código.** Monitores atômicos usam `nextstate = this.handleEvent(...)`; os demais
  usam `Prop_1_state = …`.
- **O mini-parser de ERE não é opcional.** O monitor só materializa o estado aceitante se a spec
  declarar `@match`. `CipherInputStreamSpec` e `CipherOutputStreamSpec` têm `@fail` e nenhum
  `@match` — para essas duas o conjunto aceitante só existe no `ere`. Simetricamente,
  `SecretKeySpec` (`ere : e1*`) e `RandomStringPassword` têm `@match` e nenhum `@fail`: são
  propagadores puros de predicado, e um veredito de ordem sobre elas é vazio.

### 5.2 M2 — a normalização generaliza?

Cinco specs comparadas contra a regra `api30`, com equivalência decidida por busca no produto, nas
duas direções. **Os vereditos abaixo foram refeitos em 21/08/2026 sobre o autômato que o
`CrySLParser` entrega** — a primeira versão usava autômatos construídos à parte (V4).

| Spec | Formalismo | Veredito | Testemunha mais curta | Estatuto em `5fbe8173` |
|---|---|---|---|---|
| `MessageDigestSpec` (controle) | ere | **M2-decl: EQUIVALENTES**, sob N1 | — | **válido** — autômato byte a byte idêntico ao de `d64f3a40` |
| `SignatureSpec` | ere | **M2-decl: EQUIVALENTES**, sob N1 | — | **válido** — idem |
| `SecureRandomSpec` | fsm | **M2-decl: MOP MAIS PERMISSIVA**, sob N1+N2 | `new SecureRandom(); generateSeed(20); setSeed(seed)` — `ABSTRACT` | **válido** — idem |
| `KeyGeneratorSpec` | ere | **a recalcular** | sem N1: `g1 g1 gk1` — `ABSTRACT` | **caduco** — o `ere` mudou; ver abaixo |
| `CipherSpec` | fsm | **M2-decl: INCOMPARÁVEIS**, pela direção `regra \ MOP` | `g1 i2 i2 f2` — `ABSTRACT` | **válido na direção viva** — ver abaixo |

> **Reparado em 24/08/2026 (R7) — J-01 e J-08.** A tabela publicava "EQUIVALENTES" sem dizer *de
> quê*, sem o conjunto de normalizações ao lado e sem o estatuto da testemunha. Três reparos, e um
> deles é uma invalidação medida:
>
> 1. **O rótulo passa a ser `M2-decl`, com as normalizações impressas.** O §5.1 prova que nenhuma
>    variante de M2 responde *"o monitor que rodou aceita a mesma linguagem que a regra?"*; escrever
>    "EQUIVALENTES" nu convida exatamente essa leitura. Um veredito de M2-decl não diz nada sobre o
>    que o monitor acusa — e o `KeyGeneratorSpec` é a demonstração interna disso (§5.1, J-02).
> 2. **Toda testemunha sai com `ABSTRACT`/`CONCRETE`** (J-08). Nenhuma das três desta tabela foi
>    executada; as três são `ABSTRACT`, e o §12 torna o campo obrigatório no `SpecModel`.
> 3. **O veredito do `KeyGeneratorSpec` foi calculado sobre um autômato que não existe mais.**
>    Comparados os quatro autômatos entre `d64f3a40` e `5fbe8173`, três são **byte a byte idênticos**
>    — logo os seus vereditos não foram invalidados por movimento de corpus, e isso é resultado, não
>    ausência de achado. O quarto mudou:
>
>    ```
>    d64f3a40:  (g3* g1+ | g3* g2+) ((init gk1) | gk1)
>    5fbe8173:  (g3* g1+ | g3* g2+) (((init | initRandom | initRandomSize | initRandomSpec) gk1) | gk1)
>    ```
>
>    O `order_alphabet_map.csv` registra o crescimento por escrito (*"KeyGeneratorSpec went from 5 to
>    8 and MacSpec from 8 to 12"*) e mapeia os quatro `init*` para os `i1`..`i5` da regra. O recálculo
>    contra a regra `api30` **não foi feito** e é trabalho do componente, não desta rodada.

**Onde N1 é carga.** Rodada a comparação com e sem a normalização N1, **só o `KeyGeneratorSpec`
muda de veredito**. `MessageDigestSpec` e `SignatureSpec` são equivalentes nas duas leituras, porque
as suas ERE já trazem um único evento criador na cabeça — `(g4* g1 | g4* g2 | g4* g3)` e `(g1|g2)` —
enquanto a do `KeyGeneratorSpec` traz `g1+`. Isto corrige o §13, que dizia "dois dos três". N1 está
confirmado por execução (V8), então o veredito do `KeyGeneratorSpec` está fechado.

**Critério de fidelidade do apagamento.** Apagar um evento MOP `e` (mapeá-lo a ε) preserva a
linguagem *se e somente se* `e` rotula um auto-laço em **todo** estado do autômato — ou se nenhuma
palavra realizável contém `e` junto com outros símbolos.

> **Reparado em 24/08/2026 (R7) — J-01: o apagamento deixa de ser inferência do comparador.** O
> critério acima continua correto e continua valendo como *checagem*, mas deixa de ser a fonte da
> decisão. Desde a tarefa 7.1 do gh105 o `order_alphabet_map.csv` traz uma coluna **`disposition`**
> que declara, linha a linha e com a razão escrita, por que um evento MOP não tem símbolo na regra —
> e é ela que M2 consome. Duas linhas do HEAD, verbatim:
>
> ```
> KeyGeneratorSpec,g3,,,KeyGenerator.cryptsl,,order-unmapped,"the rejected-algorithm twin over the
>   same getInstance(String) call as g1; the rule states the algorithm in CONSTRAINTS (:45) and an
>   ORDER has no symbol for a call it rejects on a constraint"
> SecureRandomSpec,g4,,,SecureRandom.cryptsl,,order-unmapped,"the invalid-algorithm accuser over the
>   same getInstance(String, ..) calls as g1/g2; task 3.1 absorbs it"
> ```
>
> A diferença importa: um apagamento **inferido** é uma decisão do comparador que ninguém revisou; um
> apagamento **declarado** é uma afirmação com dono, com razão e com procedência, que o comparador
> apenas confere. E vale registrar que o critério acima não é o que licencia apagar o `g3` do
> `KeyGeneratorSpec` — ele laça só no estado inicial. Quem o licencia é **N1**, válida ali pelo
> critério decidível do `MapOfMonitor`.

> **Corrigido em 22/08/2026 (R5).** O segundo disjunto quantifica sobre **programas Java** e não é
> decidível do `.mop`; escrito como está, parece checagem estática e o componente o aplicaria de
> forma não-sólida. É exatamente ele que torna N1 correta para o `KeyGeneratorSpec` (`g1 g1` é
> irrealizável porque cada `getInstance` devolve objeto novo) e **incorreta** para o `KeyStoreSpec`
> (`g1 g1` é realizável, porque o monitor é global) — e os dois casos são textualmente
> indistinguíveis. O substituto decidível é a **árvore de indexação do monitor gerado**, que o M2-eff
> já lê: a spec indexa se o gerado constrói um `MapOfMonitor`.

**Regras de normalização destiladas:**

| Regra | O que faz | Onde é obrigatória |
|---|---|---|
| 1:N sobre agregado | `update ↦ {u1..u4}`; o MOP funde por wildcard o que a regra separa por sobrecarga | MessageDigest, Signature, KeyGenerator, Cipher |
| 1:1 com renumeração cruzada | `g3↦gI`, `setSeed1↦s2` — nenhum heurístico acerta; só a tabela | SecureRandom, MessageDigest |
| ε-apagamento do gêmeo negado | `g4 ↦ ∅`, sujeito ao critério acima | quase todas |
| **N1 · fatiamento paramétrico** | no máximo um evento criador por monitor | KeyGenerator, SecureRandom, Cipher |
| **N2 · projeção de símbolo não-observável** | `next(int)` é `protected`: nenhum programa pode emiti-lo | SecureRandom |
| **N3 · aceitação ≠ todo `alias match*`** | `match2 = s3` é ponto de predicado, não fim legítimo | Cipher |
| **N4 · sobreposição de pointcuts** | `doFinal(..)` também casa `doFinal()`; os eventos MOP não são disjuntos | Cipher |

N2 é regra geral (o método é inacessível a qualquer programa). **N1 não é** — corrigido em
22/08/2026 (R5). Censo do monitor gerado, idêntico nos dois conjuntos: **5 das 23 specs de então não
constroem `MapOfMonitor`** e compilam para `Tuple2<Set, Monitor>`, isto é, **um monitor para o
programa inteiro** — `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`,
`KeyStoreSpec`, `RandomStringPassword`. Nelas o despachante faz `matchedEntry = Spec__Map` sem
consultar objeto nenhum, e a palavra `g1 g1` é realizável. N1 é propriedade da árvore de indexação
gerada, não do JavaMOP, e vale **por medição, spec a spec**. As três aplicações concretas desta seção
sobrevivem: `KeyGenerator`, `SecureRandom` e `Cipher` indexam integralmente.

(O discriminante é a ausência de `MapOfMonitor`. O comentário gerado `// RVMRef_x was suppressed to
reduce memory overhead` **não** discrimina nada: aparece 21 vezes, uma por spec paramétrica,
inclusive nas que indexam.)

> **Carimbado em 24/08/2026 (R7) — J-20.** O "5 das 23" é o censo do monitor gerado no conjunto de 23
> arquivos, e recebe carimbo em vez de troca: o censo **não foi refeito** sobre as 24 de `5fbe8173`.
> O que foi refeito é o **proxy decidível da AST** — spec com ligação `0/N` mais spec declarada sem
> parâmetro —, e ele dá **as mesmas cinco specs**, agora em 24. Não é a mesma medição: o oráculo real
> é o monitor gerado, e o proxy é o que M0 consegue calcular sem regerá-lo (§5.5).

N3 e N4 são o que faz do `CipherSpec` um caso especial — e N4 quebra uma premissa do
`order_alphabet_map.csv`, que assume cada evento MOP disjunto dos demais.

> **N4 é maior do que esta seção o trata, e é problema de multiplicidade, não de rotulagem** —
> medido em 22/08/2026 (R5). Varridos os 47 `.mop` de `jca` + `jca_android` (**268 eventos** —
> corrigido em 24/08/2026, R7 — J-20: dizia `46 .mop (254 eventos)`, que é o estado até `8a33bc41`;
> entrou o `IvChainJunction.mop`, e são 134 + 134) com interseção de aridade e tipo de retorno:
> **10 pares de eventos se sobrepõem no `jca_android` e 26 no `jca`**. **Nove** deles (22
> no `jca`) são separados por `condition` complementar — o idioma do gêmeo negado. **Corrigido em
> 22/08/2026 (R6):** dizia "vinte e um", que é maior que o próprio conjunto de 10. O valor sai do
> parágrafo abaixo: em `jca_android` há **um** par não separado, e `10 − 1 = 9`; em `jca` há quatro,
> e `26 − 4 = 22`, que já estava certo. O §10.3 publica o mesmo fenômeno como "8 gêmeos negativos".
>
> **Ressalva de contagem, acrescentada em 24/08/2026 (R7) — J-12 aplicado a este número.** O par
> `10`/`26` **não é reproduzível**: sob as duas regras que a R7 conseguiu reconstruir — tipos exatos
> sob `..`, e só aridade mais tipo de retorno — a varredura dá `15`/`32` e `22`/`40`, em qualquer
> commit. Nenhuma das duas dá `10`/`26`. Não é erro de nenhum dos lados; é uma regra de contagem que
> nunca foi escrita. Até que ela seja, publique-se **o par de pontas** — entre 15 e 22 pares no
> `jca_android`, entre 32 e 40 no `jca` — e nunca o `10`/`26` nu. Arnês:
> `docs/handoff/20260824_arnes_adjudicacao/probes/Overlap.java`, com as duas regras selecionáveis.
>
> Os que **não** são separados por `condition`:
>
> - **`IvChainJunction` `use` × `useRandomSpec`, sem `condition` de nenhum lado** — a testemunha viva,
>   trocada em 24/08/2026 (R7) — J2 e §3.7 da adjudicação. Os dois pointcuts casam
>   `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)`:
>
>   ```
>   use            : call(public void Cipher.init(int, Key, AlgorithmParameterSpec, ..))
>   useRandomSpec  : call(public void Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom))
>   ```
>
>   Uma única chamada casa os dois e emite **duas letras**, e o `ere` do arquivo aceita as duas. A
>   diferença para o `CipherSpec` é que aqui nenhuma acusa por ordem — mas os dois corpos rodam, e
>   para o modelo canônico é idêntico: **o alfabeto não é disjunto**. Testemunha `ABSTRACT` pela regra
>   de J-08: conferida na fonte (`IvChainJunction.mop:126-127` e `:251-252`) e pela aritmética de
>   interseção de assinaturas, **não** tecida com `ajc`.
> - ~~`CipherSpec` `f1` × `f2`, nos dois conjuntos, sem `condition` nenhuma. Tecido com `ajc` e
>   executado, `getInstance(t); init(ENCRYPT,k); doFinal()` emite **dois** relatórios de um único
>   *join point* — `CIPHER-ORDER-00 ev=f1` e `ev=f2`.~~ **Morta em 24/08/2026 (R7):** a tarefa 6.6 do
>   gh105 está concluída e estreitou o pointcut de `f2` de `doFinal(..)` para `doFinal(byte[], ..)`.
>   `doFinal()` nu já não casa `f2`, e os dois eventos ficaram disjuntos. A medição por execução
>   continua sendo verdade **do `jca` congelado**, e é lá que ela vale.
>
>   **O fenômeno é estrutural, e é isso que a troca prova.** A testemunha morreu e outra nasceu no
>   mesmo conjunto, no mesmo dia, por mecanismo independente. O `h⁻¹(L)` do §12 fica de pé por razão
>   mais forte do que tinha: não era acidente de um arquivo.
> - `jca/PBEKeySpecSpec` `err1` × `err2` × `err3`: as três têm `condition`, e as três condições não
>   são mutuamente exclusivas. Um único `new PBEKeySpec(pw, salt, 500, 128)` produz **seis
>   relatórios** — três `UnsatisfiedConstraint` e três `InvalidSequenceOfMethodCalls`, porque os três
>   eventos estão declarados e ausentes do `ere : c1 c2`. Uma chamada, três letras.
>
> A fusão de advices que o gerador faz é **subconjunto** disto: ele funde apenas pointcuts de texto
> idêntico (`jca_android` 112 advices, 8 fundidos, 7 specs; `jca` 115, 17, 13). As sobreposições
> semânticas saem como advices separados e o tecelão dispara os dois no mesmo *join point* assim
> mesmo.
>
> Ressalva para a normalização: `KeyGeneratorSpec:44/:60` e `MessageDigestSpec:44/:68` — corrigido em
> 22/08/2026 (R6): dizia `:65`, que hoje é o fim de um bloco de comentário; o `event g4` está em `:66`
> e a guarda que lê o campo, em `:68` — não são
> complementares sintaticamente — `g1` lê o argumento, `g3`/`g4` lê o campo
> `currentAlgorithmInstance`. Só são exclusivos porque o corpo de `g1` escreve o campo antes de `g3`
> ser despachado, dentro do mesmo advice fundido. **A separação depende da ordem de despacho, não da
> guarda.**

**O veredito do `CipherSpec`**, recalculado com a precedência correta e com o autômato extraído do
monitor gerado (M2-eff ponta a ponta):

```
MOP \ regra   g1 i2 f1    = getInstance(t); init(mode, key); doFinal()      [REFUTADA — ver abaixo]
              o raciocínio era: o pointcut `doFinal(..)` também casa `doFinal()`,
              então o monitor aceitaria um doFinal sem update. Está errado: o `.mop`
              declara um `f1` literal que dispara antes, e a palavra é `f1 f2`.

regra \ MOP   g1 i2 i2 f2 = getInstance(t); init(ENCRYPT,k); init(DECRYPT,k); doFinal(pt)
              reinicializar um Cipher é idiomático e a regra permite (Inits+);
              o fsm não: s2 não tem transição de init.
              FALSO POSITIVO — testemunha ABSTRACT, não executada.

VEREDITO: INCOMPARÁVEIS, pela segunda direção apenas
```

> **Corrigido em 22/08/2026 (R6), sem mudar o veredito.** Três reparos de notação e de estatuto, todos
> já estabelecidos pela R5 mais abaixo nesta mesma seção e que o bloco não tinha absorvido: as
> testemunhas escrevem `i2` (`init(Key)`), não `i1` (`init(Certificate)`) — o texto anterior glosava
> `i1 i1` como `init(ENCRYPT,k); init(DECRYPT,k)`, que é `i2`; a primeira testemunha está **refutada**
> e ficava apresentada como viva; e "FALSO POSITIVO REAL" afirmava comportamento sobre uma palavra que
> nunca foi executada, quando o estatuto correto é `ABSTRACT`.

Nenhuma delas é a que o gate reporta: a testemunha do gate (`f2` sozinho) é artefato da sua própria
precedência.

> **Corrigido em 22/08/2026 (R5) — a primeira testemunha está refutada, e "realizável" precisa de
> definição.** Três coisas, medidas:
>
> 1. **`g1 i1 f1` não é testemunha.** O `.mop` declara um `f1` literal (`:198-199`,
>    `call(public byte[] Cipher.doFinal())`) que dispara **antes** do `f2` no mesmo *join point*, e o
>    `fsm` não tem transição de `f1` a partir de `s2` (`:259-270`; `f1` só aparece em `s3`). Uma
>    chamada `doFinal()` nua emite a palavra `f1 f2` e **as duas letras acusam** — verificado por
>    execução. O raciocínio original aplicava o mapa de alfabeto como função (`doFinal() ↦ f2`, logo
>    aceito) e esquecia o `f1`. A refutação é estrutural: não precisava de execução.
> 2. **Palavra aceita ≠ traço executável.** A substituta `g1 i1 wkb1 f2` é válida no nível do
>    autômato e **impossível em Java**: `wrap` exige `WRAP_MODE` e `doFinal` exige
>    `ENCRYPT_MODE`/`DECRYPT_MODE`, e a JCA lança `IllegalStateException`. O `javax.crypto.Cipher`
>    tem uma máquina de estados de modo que nem o `.mop` nem a regra modelam — os dois
>    **sobre-aproximam**. Toda testemunha publicada precisa dizer se é `ABSTRACT` (palavra sobre o
>    alfabeto) ou `CONCRETE` (traço executado); hoje o texto promete a segunda e demonstra a primeira.
> 3. **A janela fechou.** A tarefa **6.6 do gh105** manda *"make the wider pointcut disjoint"*
>    exatamente neste par. **Atualizado em 24/08/2026 (R7): está concluída.** Esta linha dizia
>    "6.6 do gh105, **aberta**" e previa o efeito; o efeito aconteceu. No `5fbe8173` o pointcut é
>    `call(public byte[] Cipher.doFinal(byte[], ..))`, `doFinal()` nu emite só `f1`, e em `s2` o `f1`
>    não transita: o monitor rejeita, e a direção `MOP \ regra` ficou sem testemunha. O veredito
>    `INCOMPARÁVEIS` sustenta-se hoje **só** pela direção `regra \ MOP` (`g1 i2 i2 f2`, a
>    reinicialização), que é independente e continua viva.
>
> Na notação: as testemunhas do V4 escrevem `i2` (`init(Key)`), não `i1` (`init(Certificate)`).

**Reconfirmado sobre o autômato do parser (V4).** Refeita a comparação com o `StateMachineGraph` que
o `CrySLParser` devolve, o veredito é o mesmo e as **duas testemunhas saem idênticas**. De passagem,
a busca confirmava o reparo que o §9 registrava para o `order_alphabet_map.csv`: `CipherSpec.f2`
mapearia `{f1,f2,f4}`, porque o pointcut era `public byte[] Cipher.doFinal(..)` e as sobrecargas que
devolvem `byte[]` são `doFinal()`, `doFinal(byte[])` e `doFinal(byte[],int,int)` — era daí que a
primeira testemunha nascia.

> **Vencido em 24/08/2026 (R7) — J-19, e é o reparo de pior consequência se passasse.** O parágrafo
> acima está no pretérito porque a premissa dele caducou com a tarefa 6.6. O pointcut de hoje é
> `doFinal(byte[], ..)`, `doFinal()` nu não casa mais `f2`, e **`{f2, f4}` é a resposta certa** — que
> é exatamente o que o `order_alphabet_map.csv` do HEAD já diz, com a razão escrita na própria linha
> (*"Task 6.6 narrowed it off `doFinal()` … the pointcut now says what this row already claimed"*).
> **Aplicar a reparação que o §9 listava como pendente quebraria o mapa**, e por isso a linha sai do
> §9. É o caso que dá nome ao aprendizado: *antes de aplicar um reparo listado, meça se ele ainda é
> reparo.*

**A determinização é obrigatória por correção e é *no-op* neste corpus.** A NFA de Glushkov do §10.2
é real — `ORDER con, a?, a` produz mesmo duas arestas `a` do mesmo nó, verificado numa regra
sintética. Mas varridas as **30** regras `api30` que carregam sob a decisão do §12, **30 são
determinísticas e nenhuma é não-determinística**. O componente precisa da determinização para não
errar em regra futura; nas de hoje ela não muda nada.

> **Corrigido em 22/08/2026 (R5) — são 30, não 31, e o 31 vinha da via que o §12 proíbe.** Medido com
> `CrySLParser 4.0.6` (idêntico em JDK 17, 21 e 25): leitor **novo por regra** dá `ok=30/33` (falham
> `AlgorithmParameters`, `DigestOutputStream`, `Signature`); leitor partilhado em ordem alfabética dá
> 31; em ordem inversa, 29; e sobre 40 ordens aleatórias o histograma é `{29:3, 30:15, 31:22}`. Com
> leitor novo o resultado é invariante à ordem. Como o §12 decide "um `CrySLModelReader` por regra",
> **o número do corpus é 30** — e é ele que deve aparecer aqui, no §8, no §10.2 e na tabela do §12.
>
> **Reconfirmado por execução em 24/08/2026 (R7).** A medição P1 rodou o `CrySLParser 4.0.6` sobre o
> `api30` normalizado com leitor novo a cada regra, e o resultado é `ok=30 fail=3`, com as três
> residuais sendo exatamente `AlgorithmParameters`, `DigestOutputStream` e `Signature`. O leitor
> partilhado, na mesma passagem, dá `ok=31 fail=2` — e a regra que a diferença resgata é o
> `Signature`, por vazamento de `int offset`/`int len`. Registro:
> `docs/20260824_medicoes_pre_change_conformidade.md` §1.

### 5.3 M3 — o censo de constraints

62 cláusulas nas 33 regras `api30`; **55 em regras que têm `.mop`**. Cada uma classificada pelo
idioma com que está (ou não está) codificada.

**Antes do censo, uma ressalva sobre o denominador — achado de 21/08/2026 (V2).** As 62 cláusulas
são as do `api30`, e o `api30` **perdeu cláusulas que a regra CrySL de origem tem**. Três regras
saem do template base do MetaCrySL sem a seção `CONSTRAINTS` inteira:

| regra | na regra CrySL original | no `api30` |
|---|---|---|
| `DHGenParameterSpec` | 1 — `exponentSize < primeSize` | **0** |
| `DSAGenParameterSpec` | 5 — `primePLen`, `subPrimeQLen` e 3 implicações | **0** |
| `IvParameterSpec` | 3 — `length[iv] >= offset+len`, `offset >= 0`, `len > 0` | **0** |

São ~9 cláusulas normativas apagadas nessas três regras, e a perda acontece em
`MetaCrySL/samples/jca/base/`, não na geração — regerar o `api30` não as traz de volta. A
consequência é dupla: o denominador de M3 está subestimado, e uma spec `.mop` **fiel à regra de
origem** aparece como `MOP-SEM-BASE` quando medida contra o `api30`. É exatamente o caso de
`jca_android/DHGenParameterSpecSpec.mop`, que implementa `condition(exponentSize < primeSize)` —
cláusula que o oráculo já não pede. Ver o "teto do oráculo" no §6.

> **Ampliado e requantificado em 22/08/2026 (R5): as três regras acima são um subconjunto, e o teto
> tem três modos.** Recontagem com a regra declarada — **R1**: uma cláusula por `;` dentro de
> `CONSTRAINTS`, comentários removidos, conjunções `&&` **não** contadas à parte:
>
> | corpus | escopo | R1 |
> |---|---|---:|
> | upstream `CrySL-Rules` | 49 regras | 119 |
> | upstream | as 33 do `api30` | **95** |
> | upstream | as 22 que têm `.mop` | 80 |
> | `samples/jca/base` | 33 | 42 |
> | `api30` | 33 | **62** |
> | `api30` | as 22 que têm `.mop` | **55** ← o denominador desta seção |
>
> (Sob outras regras: separar `&&` dá 101/71; separar os lados de `=>` dá 117/87. Qualquer número
> upstream que entre no artigo precisa da regra de contagem escrita ao lado.)
>
> `95 → 62` é **−33 líquido em 16 regras**, não ~9 em 3. Por conjunto de cláusulas: limites 45→15,
> `notHardCoded` 3→0, `instanceOf` 2→0, `x in {literais}` 19→17, `neverTypeOf` 6→5, implicações 20→25.
>
> E o teto erra em **três direções diferentes**, das quais este documento só descrevia a primeira:
>
> 1. **Deleção** — a cláusula some, e uma spec fiel à origem vira `MOP-SEM-BASE`. É o caso das três
>    regras acima, e o censo já aplica o rótulo certo (`IvParameterSpec.mop:115`,
>    `DHGenParameterSpecSpec.mop:24`). **Corrigido em 22/08/2026 (R6):** o primeiro dizia `:35-37`,
>    transcrito do `constraint_table.csv:32`, cujos `mop_line` o §9 já declara desatualizados; hoje
>    `:35-37` é comentário e a guarda está em `:115`.
> 2. **Corrupção de operador** — `api30/Cipher.cryptsl:131,133,135` escrevem `length(x) <= off` onde o
>    upstream escreve `>=` (§9). As cláusulas sobrevivem com o sentido invertido.
> 3. **Substituição de predicado** — a tríade `length[x] >= off+len; off >= 0; len > 0` foi trocada
>    por `len > off`, um predicado sobre dois inteiros que nada diz sobre o array
>    (`base/{CipherInputStream,CipherOutputStream,DigestInputStream,DigestOutputStream,MessageDigest,Mac}`),
>    e em `base/{IvParameterSpec,GCMParameterSpec,Signature}` simplesmente sumiu.
>
> (2) e (3) erram na **direção oposta** a (1): fariam uma tradução fiel à origem aparecer como
> infidelidade. **Hoje têm zero ocorrências** — a família `length` no `api30` são exatamente 6
> cláusulas, das quais 5 estão ausentes do `.mop` e a única implementada
> (`SecretKeySpecSpec.mop:101`) traduz justamente a única correta no oráculo
> (`SecretKeySpec.cryptsl:29`, `>=`). É risco latente, e o custo de registrá-lo é o registro; o custo
> de não o registrar aparece na primeira spec de buffer que alguém escrever.

| Forma sintática | A | B | C | D | Ausente | Total |
|---|---:|---:|---:|---:|---:|---:|
| `part()` ⇒ `part()` | 0 | 0 | 0 | 6 | 11 | 17 |
| `x in {literais}` | 11 | 0 | 0 | 0 | 1 | 12 |
| comparação aritmética | 0 | 2 | 0 | 0 | 5 | 7 |
| `length[x] …` | 0 | 1 | 0 | 0 | 5 | 6 |
| `neverTypeOf` | 0 | 0 | 0 | 0 | 5 | 5 |
| `in {}` ⇒ `in {}` | 0 | 0 | 4 | 0 | 1 | 5 |
| demais formas com `part()` | 0 | 0 | 0 | 1 | 2 | 3 |
| **Total** | **11** | **3** | **4** | **7** | **30** | **55** |

Legenda dos idiomas: **A** = `Arrays.asList(...)` + `ConscryptAliasTable.matches(...)`;
**B** = aritmética direta na `condition(...)` ou no corpo, sobre variáveis ligadas por `args()`;
**C** = método auxiliar declarado dentro da spec; **D** = classe auxiliar externa em `rvsec-core`.

Formas com **zero** ocorrências em `api30`: `notHardCoded`, `instanceOf`, e `alg()`/`mode()`/`pad()`
como funções nuas. O reconhecedor não precisa suportá-las.

**A ressalva que muda a leitura do número.** Cobertura alta não é métrica correta. Comparando só os
conjuntos de literais, 9 das 11 allow-lists são idênticas à regra — mas 8 delas são de fato *mais
permissivas*, porque o teste passa por `ConscryptAliasTable.matches()` e suas 158 linhas de alias.
Um extrator literal daria "conforme" onde o correto é "mais permissivo". A tabela de alias é parte
da semântica da comparação, não decoração — e está distribuída de forma muito desigual (Signature
55 linhas, Cipher 29, Mac 24; **zero** para KeyStore, SSLContext e SecureRandom).

**Cláusulas ausentes de maior impacto**, as que mudariam o que é acusado:

- `KeyGenerator:47` — `alg in {"AES"} => keySize in {128,192,256}`. Única cláusula de tamanho de
  chave simétrica do conjunto. `AES/64` não é acusado. É a mais barata de fechar.
- `Cipher:127` — `encmode in {1,2,3,4}`. Os eventos já ligam `int mode`; falta o teste.
- `Cipher:123`/`:125` — `noCallTo(IWOIV)` / `callTo(iv)`: IV fixo em CBC/CTR/CFB/OFB/PCBC. O clássico
  static-IV. `CipherSpec` não declara sequer o evento `getIV()` — falta o alfabeto, não só a guarda.
- `Cipher:139..169` (11 cláusulas) — modo/padding de `DESede`, `BLOWFISH`, `ARC4`, `AES_128/256`,
  `ChaCha20`. `Api30CipherTransformationUtil.isValid` admite esses algoritmos em `part(0)` e depois
  retorna `true` sem restringir modo/padding. `BLOWFISH/ECB/PKCS5Padding` passa.
- As 5 `neverTypeOf(password, java.lang.String)` (`KeyStore` ×3, `KeyManagerFactory`, `PBEKeySpec`).
  Nota: é propriedade do tipo estático da origem; em runtime a assinatura já é `char[]`. É a
  candidata natural a ficar fora do escopo **por decisão explícita**, não por omissão.

### 5.4 M4 — o grafo de predicados e seu teto

> **Ressalva que acompanha todo número desta seção — acrescentada em 24/08/2026 (R7), J-04 e J-15.**
> Dois avisos, e eles valem para **cada** escalar abaixo, não só para a tabela que os carrega:
>
> 1. **A classificação FIEL / PROJETADO / CONFLADO / AUSENTE é julgamento humano semeado e propagado
>    por cópia, não medição derivável.** `scripts/gh105_predicate_graph.py` (1.845 linhas) nunca lê um
>    `.cryptsl`, e o próprio docstring diz que carrega *"the committed `data/jca_android/
>    predicate_graph.csv` for the judgment columns **no analyzer can re-derive**"* (`:34-35`);
>    `carry_judgments()` copia-as de uma versão anterior do próprio CSV. Até esta rodada a ressalva
>    morava só no §9, e os números saíam aqui sem ela. **Dar domicílio derivável a essas cinco colunas
>    é entregável nomeado do componente** — item 10 do §13.
> 2. **Nenhum escalar de M4 significa alguma coisa sem regra de contagem e commit ao lado.** A
>    assinatura de substrato do `jca_android` mudou **cinco vezes em quatro dias** — `64/21/5` →
>    `47/26/7` → `28/35/12` → `0/45/19` → **`0/70/21`** (sítios de `ExecutionContext` / de
>    `PredicateStore` / arquivos migrados) — e o `predicate_graph.csv` foi de 85 linhas de dados a 45
>    e voltou a **70**. É por isso que o campo `version : {commit, data, corpus}` do `SpecModel` (§12)
>    deixou de ser conveniência e virou requisito.

92 cláusulas normativas nas 33 regras (54 `ENSURES`, 36 `REQUIRES`, 2 `NEGATES`), 32 predicados
distintos, **aridade nunca passa de 2** (59 de aridade 1, 33 de aridade 2). 73 delas estão em regras
com `.mop`.

| Classe | n | % das 73 | O que é |
|---|---:|---:|---|
| FIEL | 26 | 35,6 % | mesma polaridade, mesma aridade, mesmas posições |
| PROJETADO | 13 | 17,8 % | aridade 2 achatada em 1 pelo `ExecutionContext` |
| CONFLADO | 5 | 6,8 % | implementado sob um `Property` que é outro predicado |
| AUSENTE | 29 | 39,7 % | nenhuma contraparte |
| SEM-BASE | 16 | — | sítios que a regra não pede (8 são `remove()` em `@fail` **em `d64f3a40`**; 7 em `c12f4689` e **zero** em `8a33bc41`, depois das tarefas 4.14/6.4 — R6) |

O teto é estrutural: `ExecutionContext` tem aridade 1, devolve booleano e não tem `validateAbsent`.
Num arquivo que só usa esse substrato, uma cláusula de aridade 2 ou negada é *inexprimível*, por
melhor que a spec seja.

> **Reparado em 24/08/2026 (R7) — J-16: o teto é do `jca` congelado, e no `jca_android` está pago.**
> O `jca_android` de `5fbe8173` tem **zero** sítios de `ExecutionContext.instance()`: a tarefa 4.14
> do gh105 migrou os últimos, e hoje são 70 sítios de `PredicateStore` em 21 dos 24 arquivos. Logo o
> teto que esta seção descreve **não limita mais o conjunto novo**. Ele continua descrevendo o `jca`
> congelado, onde os 23 arquivos ainda usam `ExecutionContext` — e é lá que ele importa, porque o
> congelado é o conjunto sobre o qual as medições publicadas do TSE 2023 foram feitas. O requisito do
> extrator não muda (ele precisa dos dois substratos); o argumento fica mais forte, porque passa a
> apontar para o conjunto que sustenta a literatura em vez de para um estado transitório do conjunto
> em obra.

| Cenário | das 73 cobertas | das 92 totais |
|---|---:|---:|
| medido hoje | 35,6 % | 28,3 % |
| teto com o substrato atual (5 arquivos migrados) | 74,0 % | 58,7 % |
| teto com migração completa a `PredicateStore` | 100 % | 79,3 % |

> **Instantâneo, carimbado em 22/08/2026 (R5): esta tabela e os números de M4 desta seção foram
> medidos no commit `d64f3a40`, não no `HEAD` de publicação.** A linha do meio depende de "5 arquivos
> migrados", e hoje são 7 (8 na árvore de trabalho). Enquanto o gh105 correr, todo número de M4 é
> alvo móvel e só significa alguma coisa com o commit ao lado — ver §13.

Os 19 bloqueios do teto atual eram 17 cláusulas de aridade 2 em arquivo `ExecutionContext` e 2
cláusulas negadas no `MacSpec` que precisavam de `validateAbsent`.

> **Reparado em 24/08/2026 (R7) — J-16.** Pretérito, e os dois bloqueios caíram no conjunto novo. Não
> há mais arquivo `ExecutionContext` no `jca_android`, e as duas cláusulas negadas do `MacSpec` têm
> sítio hoje: `MacSpec.mop:303` valida `ENCRYPTED` ausente, e há mais três sítios de `validateAbsent`
> sobre `MACED` que esta decomposição não previa. São **5 sítios de chamada** de `validateAbsent` no
> `jca_android` — e vale a nota de contagem, porque a R7 quase publicou o número errado: são **9
> ocorrências do token** e **5 sítios**, porque quatro estão em comentário (`MacSpec.mop:250`,
> `CipherSpec.mop:259` e `:281`, `IvChainJunction.mop:328`). Os cinco reais são `MacSpec.mop:303`,
> `CipherSpec.mop:292` e `:304`, `IvChainJunction.mop:341` e `:351`.

**A distância decompõe-se exatamente:**

```
    26   fiéis hoje
  + 28   débito de FIAÇÃO      → editar specs que já existem
  + 19   débito de SUBSTRATO   → concluir a migração p/ PredicateStore
  + 19   débito de COBERTURA   → escrever 11 specs que não existem
  ────
    92   cláusulas normativas do oráculo api30
```

Três parcelas, três causas, três donos, três custos, três prazos. O débito de fiação é trabalho de
spec; o de substrato é uma decisão de engenharia já tomada e a meio caminho; o de cobertura é escopo
de projeto — e talvez uma escolha deliberada de nunca fazer. Colapsar isso num só percentual apaga
exatamente a distinção que decide o que fazer na semana seguinte.

> **Carimbado em 24/08/2026 (R7) — J-15 e J-16.** **A decomposição continua correta como estrutura, e
> os seus quatro valores estão vencidos.** A parcela de **19 de SUBSTRATO está paga** — a migração a
> `PredicateStore` terminou no `jca_android` (`0` sítios de `ExecutionContext` em `5fbe8173`) —, e as
> outras três dependem da classificação por julgamento humano da ressalva de abertura desta seção. O
> re-censo das quatro parcelas **não foi feito** nesta rodada e é trabalho do componente: é
> precisamente o tipo de número que só passa a ser derivável quando as cinco colunas de julgamento
> ganharem domicílio. Publique-se a estrutura `fiéis + fiação + substrato + cobertura`, com o commit
> ao lado; não se publiquem os quatro escalares de `d64f3a40` como se fossem de hoje.

**Achado sobre o gh105.** Contando cadeias produtor→consumidor efetivamente realizadas, o número é
**idêntico em `jca` e `jca_android`**: 8 das 44 arestas normativas, e 3 cadeias no nível de
`Property` (`GENERATED_KEY`, `GENERATED_PUBLIC_KEY`, `RANDOMIZED`). O gh105 trocou o substrato
debaixo de cadeias que já existiam e reduziu ruído — a *topologia* ficou intacta. Isso não é
crítica: é o que permite dizer com precisão o que o próximo passo tem de fazer.

### 5.5 M0 — vitalidade do monitor

**Acrescentada em 24/08/2026 (R7) — J3, decisão do pesquisador.** M0 é a primeira métrica e ela
**recusa** a spec, com `Unknown` tipado, antes de M1–M4 rodarem. A razão é curta: um veredito de ordem
sobre um monitor que não roda é vazio, e as quatro métricas de conteúdo o produziriam com a mesma
confiança com que produzem um veredito verdadeiro.

**Três perguntas, todas decidíveis de artefatos que o desenho já produz:**

| | Pergunta | Como se decide | Saída quando falha |
|---|---|---|---|
| M0.1 | a spec **indexa**? | o monitor gerado constrói `MapOfMonitor`? Proxy da AST: ligação `0/N` ou spec sem parâmetro | fatiamento é *no-op*: a spec degenera para autômato global, e N1 deixa de valer nela |
| M0.2 | o **sítio de acusação** é alcançável? | há `@fail`? há `addError` alcançável em corpo de evento? o evento está no `ere`? | recusa: nenhum traço pode fazê-la acusar |
| M0.3 | o **pointcut resolve**? | conferência a posteriori de cada assinatura contra o `android.jar` da API 30 (§8) | `Unknown{UnresolvedSignature}` |

Mais o **checador não-normalizado sobre a AST** que o §12 já pedia para o portão do gerador — ids
únicos, alfabeto da fórmula ⊆ ids, todo evento declarado alcançável, todo `@match` com `@fail`. É a
mesma peça, promovida de portão interno a saída publicada, e é ela que pega a classe de defeito que
o §7 demonstra atravessar parser, gerador e compilador em silêncio.

M0 também absorve, sem regra ad hoc, o fenômeno que o §2 mede como *"absorve uso incorreto"*: a
pergunta *"a acusação está no `ere` ou no corpo do evento?"* é propriedade da AST, e medi-la em M0 é o
que a torna comparável entre conjuntos e entre commits.

**A evidência que motiva M0, medida por execução em 24/08/2026.** As cinco specs que o proxy da AST
marca como não-indexadoras — `CipherInputStreamSpec`, `CipherOutputStreamSpec`,
`HMACParameterSpecSpec`, `KeyStoreSpec`, `RandomStringPassword` — foram replicadas pelo arnês do
gh104 contra os dois conjuntos, com 13 traços versionados e **quatro controles negativos autorados com
a previsão escrita antes de rodar**. Registro completo em
`docs/20260824_medicoes_pre_change_conformidade.md` §2.

| spec | controle negativo | acusou? | o que isso decide |
|---|---|---|---|
| `CipherInputStreamSpec` | `c1 cl1` (fora da linguagem) | **sim**, em `cl1` | monitor **vivo** |
| `CipherOutputStreamSpec` | `c1 cl` | **sim**, em `cl` | monitor **vivo** |
| `HMACParameterSpecSpec` | `c c` | **sim**, no segundo `c` | vivo **na JSE**; morto no Android — a classe não existe em nível de API nenhum |
| `RandomStringPassword` | `gb` sozinho | **não** | **sem sítio de acusação**: `@match` vazio e nenhum `@fail` |
| `KeyStoreSpec` | (traços originais) | **sim**, em 3 de 5 | vivo e discriminando |

**Duas conclusões, e as duas mudam o desenho de M0.**

1. **"Não constrói `MapOfMonitor`" funde três fenômenos, e só um é defeito reparável.** Monitor vivo
   e cego para o fim do traço; monitor vivo cujo alvo não existe na plataforma; monitor sem sítio de
   acusação. M0 tem de os separar, porque a ação que cada um pede é diferente — o primeiro é linha de
   `divergence_record`, o segundo é `Unknown{UnresolvedSignature}`, e só o terceiro é recusa.
2. **A cegueira de `IncompleteOperationError` do §10.5 deixou de ser leitura de gramática.** Os dois
   traços que os próprios autores rotulam `# violating branch` — *"the stream is read and never
   closed"* e *"written and never closed"* — **não acusam em nenhum dos dois conjuntos**, e os
   controles provam que os mesmos monitores acusam quando a palavra de fato sai da linguagem. A causa
   é estrutural: `c1 r1` é **prefixo vivo** de `c1 (r1|r2)+ cl1`, o `@fail` do JavaMOP só dispara
   quando a palavra sai da linguagem, e não existe evento de fim de traço. É o terceiro eixo da
   moldura do §13, agora medido em vez de argumentado.

**E é a demonstração mais desconfortável do item 11 do §13.** Das três causas acima, **só a terceira
é decidível do `.mop`**: a primeira é propriedade do formalismo e a segunda exige o `android.jar`.
M0 é estrutural como as outras quatro. A metade comportamental não é complemento do componente — é o
que dá sentido ao veredito da metade estrutural.

---

## 6. Como reportar sem armar uma armadilha

As duas métricas quantificadas têm um denominador que não é óbvio, e os dois erram de formas
diferentes. Vale separar, porque a confusão entre elas é o modo mais fácil de publicar um número que
parece medição e não é.

| Tipo de teto | Onde | O que limita | Como o número engana |
|---|---|---|---|
| **Do sujeito** | M4 — 79,3 % | 19 cláusulas vivem em regras sem `.mop`; não podem ser fiéis por construção | O denominador inflado faz a tradução parecer **pior** do que é, por razão aritmética |
| **Do instrumento** | M3 — 25,5 % | Um extrator que cubra só os idiomas A e B não segue chamadas a `Api30CipherTransformationUtil` nem a métodos privados da spec | Faz a spec parecer **pior** do que é, por razão de ferramenta — e o erro é indistinguível de um achado real |
| **Do oráculo** | M3 — 3 regras | O `api30` perdeu cláusulas que a regra CrySL de origem tem (ver §5.3) | Faz a spec parecer **melhor** do que é nas 30 ausentes, e acusa de `MOP-SEM-BASE` justamente onde ela é fiel à regra original |

O teto do oráculo é o terceiro, e foi descoberto só em 21/08/2026. Ele erra na direção contrária aos
outros dois, e é por isso que precisa de linha própria: os dois primeiros fazem o sujeito parecer
pior, este faz o *denominador* parecer menor. Somados sem separação, dão a impressão de um número
estável que é a soma de três vieses.

Note a assimetria: os **45,5 % de M3 são o resultado**, não um teto. A spec de fato não checa 30 das
55 cláusulas que a regra exige, e isso é um achado forte. O que é teto ali são os 25,5 % — o que um
extrator subdimensionado conseguiria ver.

**Por que o `Unknown` explícito não é opcional.** Sem uma categoria `NÃO-RECONHECIDO` separada de
`AUSENTE`, "não consegui ler" e "não existe" saem pela mesma porta. No caso concreto: um extrator de
escopo mínimo acusaria **11 cláusulas implementadas** de ausentes. O relatório mentiria com números
que parecem medição, e ninguém teria como perceber.

### Os quatro modos de errar com um escalar

- **Atribuição.** "28 % de fidelidade" lê-se como "72 % das cláusulas foram traduzidas mal". São 21
  pontos inalcançáveis por definição e ~20 de substrato. O número acusa a tradução por um problema
  que não é dela.
- **Não-comparabilidade.** Escrever cinco das specs faltantes encolhe a parte inalcançável do
  denominador e o número sobe — sem que nenhuma tradução tenha melhorado. Isso mata qualquer
  afirmação de progresso ao longo do gh105 e qualquer comparação `jca` × `jca_android`.
- **Gradiente perverso.** O jeito mais barato de subir `26/92` não é melhorar fidelidade — é mexer no
  denominador. Excluir as regras sem `.mop` leva a 35,6 % com zero trabalho.
- **Esconde onde está o trabalho.** Um escalar não diz se a próxima semana deve ser fiação,
  substrato ou cobertura. O vetor `26 / 54 / 73 / 92` diz.

### A formulação a usar

Não um número, e sim o denominador declarado como decisão:

> Das 92 cláusulas de predicado do oráculo api30, 73 pertencem a regras que o conjunto cobre. Dessas,
> 54 são exprimíveis no substrato atual, e dessas 54, **26 estão implementadas fielmente e 28 são
> débito de fiação** — trabalho de spec que ainda não foi feito. As **19** cláusulas exprimíveis que
> faltam para 73 exigem `PredicateStore`; as outras **19** que faltam para 92 exigem specs que não
> existem. `26 + 28 + 19 + 19 = 92`.

Cinco frases, cada número com o seu referente colado, e a soma fechada por extenso.

> **Corrigido em 22/08/2026 (R5).** A formulação anterior enunciava um encaixe (`92 ⊃ 73 ⊃ 54 ⊃ 26`)
> e afirmava de si mesma ser *"a única versão que um revisor não pode ler errado"*. O encaixe estava
> aritmeticamente certo — `73 − 54 = 19` e `92 − 73 = 19` — mas **três leitores independentes leram-no
> como partição e acharam que faltava uma parcela**, porque o antecedente natural de "as 19
> restantes", logo depois de "26 … 48 % do exprimível", é o 54, cujo resto é 28. A auto-afirmação foi
> retirada, e a parcela de 28 — que é a maior das três e a única que o §5.4 chama de *trabalho de
> spec* — está escrita por extenso.

**Não agregue as métricas num score único.** Um número esconde qual seção está ruim e convida a
otimizar o número. Se o artigo exigir um valor, que seja o vetor por seção. (Corrigido em 24/08/2026,
R7 — J3: dizia "as **quatro** métricas", e são cinco desde que M0 entrou. E M0 é justamente a que
**não** se agrega com as outras: ela recusa, e uma recusa não tem lugar num vetor de cobertura.)

---

## 7. Viabilidade — o lado `.mop`

Melhor do que o esperado, e verificado por execução.

```
jca                        23   23 ok   0 fail
jca_android                24   24 ok   0 fail
jca_android_bug_predicate  23   23 ok   0 fail
generic                   118  118 ok   0 fail
generic_new                27   27 ok   0 fail
TOTAL = 215   OK = 215   FAIL = 0        (JDK 21, offline, só o jar do javamop no classpath)
```

> **Recontado em 24/08/2026 (R7) — J-20.** O censo dizia `jca_android 23` e `TOTAL = 214`. Entrou o
> `IvChainJunction.mop` pela tarefa 5.1 do gh105, e o `jca_android` tem **24**. Rederivado em
> `5fbe8173` com a sonda `Census.java`: `215/215 ok, 0 fail`, `905` eventos e `381` parâmetros nos
> cinco corpora. A conclusão — *o parser lê o corpus inteiro sem uma falha* — é a mesma; o
> denominador é que cresceu.

O parser é `javamop.parser.SpecExtractor.parse(File)`, do artefato
`br.unb.cic.javamop:javamop:0.9.3-SNAPSHOT` (instalado em `/home/pedro/desenvolvimento/repository`,
para onde o `~/.m2/settings.xml` redireciona o repositório local).

### O que a AST entrega

| Seção CrySL | Fonte na AST | Situação |
|---|---|---|
| `SPEC` | `JavaMOPSpec.getName()` + `getParameters()` + imports | Direto |
| `OBJECTS` | `MOPParameters` + `TypePattern` dos pointcuts | Direto |
| `EVENTS` | `MethodPointCut.getSignature()` → `MethodPattern` | Direto |
| `ORDER` | `Formula.getFormula()` — texto cru | Mini-parser |
| `CONSTRAINTS` | `getCondition()` (string) + `getAction()` (`BlockStmt`) | Idiomas |
| `REQUIRES`/`ENSURES`/`NEGATES` | chamadas em `getAction()` e `getHandlers()` | Idiomas |
| `FORBIDDEN` | eventos que só acusam `ForbiddenMethod` | Convenção |

O subconjunto de AspectJ realmente usado é minúsculo — em `jca_android`: 128 `call(`, 82 `args(`,
63 `target(`, 36 `condition(` (eram **40** em `d64f3a40` — corrigido em 22/08/2026, R6: dizia 41, e a
recontagem dá 40 por ocorrência e por linha), e **zero** `execution`, `within`, `cflow` ou
`this`. Nenhum
modificador de spec (`full binding`, `perthread`) é usado em lugar nenhum do corpus.

### Os idiomas de predicado são regulares

```java
// substrato A — ExecutionContext (aridade 1, chaveado por equals, booleano)
setProperty(Property.X, var)              → ENSURES  X[var]
validate(Property.X, var)                 → REQUIRES X[var]
remove(Property.X, var)                   → NEGATES  X[var]
set/unsetObjectAsInAcceptingState(o)      → a semântica CrySL de estado aceitante

// substrato B — PredicateStore (gh105: aridade N, identidade, três valores)
ensure(Property.X, bound, values...)      → ENSURES de aridade ≥ 2
validate(...) → SATISFIED | VIOLATED | NOT_OBSERVED
validateAbsent(...)                       → o !p[...] do CrySL

// constraints
List<String> algs = Arrays.asList(...) + ConscryptAliasTable.matches(svc, obs, algs)  → x in {...}
```

**O extrator precisa reconhecer os dois substratos — e a razão mudou de conjunto.**

> **Reescrito em 24/08/2026 (R7) — J-16.** Esta subseção abria com **"Dois substratos coexistem"**, e
> a premissa é falsa no `jca_android` de `5fbe8173`: são **zero** sítios de
> `ExecutionContext.instance()` e 70 de `PredicateStore.instance()`, em 21 dos 24 arquivos. A tarefa
> 4.14 do gh105 terminou a migração. A trajetória medida, commit a commit, é
> `64/21/5` (`d64f3a40`) → `47/26/7` (`c12f4689`) → `28/35/12` (`f188c55b`) → `0/45/19` (`8a33bc41`)
> → **`0/70/21`** (`5fbe8173`), onde os três números são sítios de `ExecutionContext`, sítios de
> `PredicateStore` e arquivos migrados.
>
> **O requisito do extrator não muda, e o argumento fica mais forte.** Ele precisa reconhecer o
> substrato A não porque o conjunto novo o use, mas porque o **`jca` congelado** o usa nos seus 23
> arquivos — e o congelado é o conjunto sobre o qual as medições publicadas do TSE 2023 foram feitas.
> Qualquer comparação histórica, e qualquer afirmação sobre o que o gh105 mudou, tem de conseguir ler
> os dois. A razão antiga era "o alvo se move"; a nova é "a literatura mora no conjunto antigo", e
> essa não caduca.

O que **não** muda com isso é a ordem de trabalho: começar pelo extrator de predicados (M4) continua
servindo o gh105 imediatamente, e agora com um alvo que parou de se mover — 72 das 74 tarefas
concluídas em `5fbe8173`.

### Armadilhas confirmadas do parser

- `BlockStmt.getStmts()` devolve **`null`**, não lista vazia, para bloco `{ }` — e o corpus tem vários.
- `MOPNameSpace` é estático global e `SpecExtractor.parse` não chama `init()`; acumula estado entre
  arquivos. **Decidido em 24/08/2026 (R7) — J-13: o componente chama `init()` por arquivo, e o custo
  medido é zero.** `JavaMOPMain:114,185` o chama; `SpecExtractor.java:23` não. Sonda executada sobre
  os cinco corpora, com e sem `MOPNameSpace.init()` antes de cada arquivo:

  ```
  init=false -> ok=215 fail=0 eventos=905 parametros=381
  init=true  -> ok=215 fail=0 eventos=905 parametros=381
  ```

  Idêntico nos três agregados. A decisão é **por determinismo e por simetria com "um
  `CrySLModelReader` por regra"** (§12), não porque mude número nenhum — e declarar que o impacto
  medido é nulo é a forma honesta de fechar a assimetria sem a inflar. Arnês:
  `docs/handoff/20260824_arnes_adjudicacao/probes/InitTest.java`.
- `JavaMOPParser` guarda instância em campo estático — **não paralelize o parse**.
- `JavaParserAdapter` engole exceções dos blocos Java: um handler malformado vira `BlockStmt == null` sem aviso.
- As chaves de `getHandlers()` vêm em minúsculas (`@match1` → `"match1"`).
- Os `BlockStmt` são do fork interno, não do `com.github.javaparser`; para usar o JavaParser moderno,
  re-parseie o `toString()`.
- `getRetType()` é sempre `null`; o tipo de retorno real vem de `MethodPattern.getType()` dentro do
  `MethodPointCut`.

**"Parseou" não é oráculo de sanidade.** `jca/GCMParameterSpecSpec.mop` declara dois eventos com o id
`c1` e uma fórmula `c1 | c2` que referencia um `c2` inexistente. O `SpecExtractor` aceita os dois
defeitos sem um único aviso. O mesmo vale para os parênteses desbalanceados de
`jca/SecretKeySpecSpec.mop`, que parseia — e parseia com a condição correta. Um checador de vinte
linhas sobre a AST (ids únicos + alfabeto da fórmula ⊆ ids) fecha essa classe inteira.
`jca_android` já está limpo.

**Decisão fechada:** o `.rvm` não serve como entrada. Verificado empiricamente — zero `call(` em
todos os `.rvm` gerados. Sem pointcut não há assinatura de método, logo não há `EVENTS`.

---

## 8. Viabilidade — o lado CrySL

A hipótese inicial era escrever um parser próprio para evitar arrastar Xtext, EMF e Tycho. **A
premissa estava errada:** o acoplamento ao Tycho existe para *construir* o CryptSL, não para
*usá-lo*. Um projeto Maven puro com uma dependência só compila e roda:

```xml
<dependency>
  <groupId>de.darmstadt.tu.crossing.CrySL</groupId>
  <artifactId>CrySLParser</artifactId>
  <version>4.0.6</version>
</dependency>
```

Já está no repositório local. Rodou offline, resultados idênticos em JDK 17 e 21.

### O que ele lê

**Escada remedida em 22/08/2026 (R5), com leitor novo por regra** — a configuração que o §12 decide.
A tabela anterior misturava degraus medidos em modo lote com degraus medidos isoladamente; os números
abaixo são de uma única configuração, degrau a degrau.

| Corpus | arquivos | lidos (leitor novo) | lidos (partilhado/alfabético) |
|---|---:|---:|---:|
| `CrySL-Rules` (JCA 1.5.2) | 49 | 47 | 47 |
| `generated/api30` cru | 33 | 20 | 20 |
| + `FORBIDDEN:`→`FORBIDDEN` | 33 | 22 | 22 |
| + `;;`→`;` | 33 | 22 | 22 |
| + `alg`→`algName` | 33 | 24 | 25 |
| + `(`→`[` nos predicados | 33 | 27 | 28 |
| + `length(…)`→`length[…]` | 33 | **30** | 31 |

As 2 falhas do `CrySL-Rules` são bugs das próprias regras. E `length(…)`→`length[…]` move **27→30**,
não 30→31: o degrau que o texto anterior rotulava "30" media 27 sob leitor novo.

**O `CrySLParser` 4.0.6 não lê o dialeto `.cryptsl` do MetaCrySL como está**, mas a distância é
majoritariamente léxica. Os dois bloqueios novos: `alg` virou palavra reservada na gramática 4.x e o
MetaCrySL a usa como nome de objeto (5 arquivos — `KeyGenerator`, `KeyPairGenerator`,
`AlgorithmParameters`, `SecretKeySpec`, `Signature`); e o MetaCrySL escreve `noCallTo(X)`,
`callTo(x)`, `neverTypeOf(a, T)` com parênteses onde o oficial usa colchetes — **4 arquivos**
(`Cipher`, `KeyStore`, `KeyManagerFactory`, `PBEKeySpec`), corrigido em 22/08/2026 (R5): o "6" era a
união com o grupo `length(`, que acrescenta `Mac` e `SecretKeySpec`. `notHardCoded` tem **zero**
ocorrências no `api30` — está na regra `sed` por precaução, não porque ocorra. Não há justificativa
para parser próprio: uma camada de normalização de **cinco** substituições leva 20→**30**, e as
residuais são bugs do MetaCrySL que precisam ser corrigidos na origem de qualquer forma — um parser
próprio só os esconderia.

As cinco, na ordem em que a escada acima as aplica — corrigido em 22/08/2026 (R6): a lista dizia "na
ordem em que se aplicam" e punha `alg`→`algName` por último, quando é ele o terceiro degrau, o que
move 22→24:
`FORBIDDEN:`→`FORBIDDEN` · `;;`→`;` · `alg`→`algName` ·
`neverTypeOf/noCallTo/callTo/notHardCoded(…)`→`[…]` · `length(…)`→`length[…]`.

**As residuais são três**, não duas — corrigido em 22/08/2026 (R5). Confrontadas com a regra oficial
correspondente em `rvsec-cognicrypt/CrySL-Rules/`, e não só com a mensagem do parser, as três são
defeitos reais do gerador MetaCrySL, e nenhuma é léxica:

| Regra | O quê | Como o oficial escreve |
|---|---|---|
| `AlgorithmParameters:47` | `alg in {"BLOWFISH"} => preparedIV[params];` dentro de `CONSTRAINTS` | as implicações com predicado ficam em `REQUIRES` — e o próprio arquivo já tem a forma certa três linhas abaixo |
| `DigestOutputStream:20` | `FORBIDDEN on(java.lang.String)` | `on(boolean)`; `javap` confirma que não existe sobrecarga com `String` |
| `Signature:51,59,65` | `offset` e `len` usados sem declaração em `OBJECTS` | o oficial declara `int offset;` e `int len;` |

A terceira só desaparecia porque o escopo de `OBJECTS` vazava de outra regra lida antes no mesmo
leitor (§9).

**A leitura pela AST EMF é mais permissiva ainda — e a permissividade tem preço.** Contornando a
fachada — `CrySLStandaloneSetup` → `XtextResourceSet` → `ClasspathTypeProvider`, ~10 linhas (§10.2) —
o `Domainmodel` sai para **33/33**, inclusive para as três que a fachada rejeita. É por essa via que
saem os nomes de evento, os agregados e a procedência, e ela é a que permite *relatar* uma regra
defeituosa em vez de simplesmente perdê-la. **Mas os 33 saem porque `getResource(…, true)` faz
recuperação de erro: validando com `IResourceValidator`, são 30 — os mesmos da fachada.** A via só é
segura consultando `resource.getErrors()`; sem isso, o `AlgorithmParameters` entra no modelo com a
implicação apagada em silêncio (§10.2). Usar a AST para *relatar* é certo; usá-la para *contar
regras válidas* não.

### O serializer existe e não formata

Verificado no bytecode publicado e por execução: `CrySLSemanticSequencer` está no jar,
`bindISerializer()` está no `RuntimeModule`, e um `Domainmodel` construído do zero via
`CrySLFactory` serializa para texto válido e reparseável. Só que **numa única linha**, com espaço
antes de cada `;`, `[` e `(` — não há formatter no projeto.

Desenho resultante:

| Papel | Como | Por quê |
|---|---|---|
| Ler `.crysl` | `crysl.CrySLParser` 4.0.6 | Uma dependência, já local; entrega o `ORDER` compilado em `StateMachineGraph` |
| Escrever `.crysl` | pretty-printer próprio (~400 l.) | Gramática tem 423 linhas e 12 seções; controle sobre formatação, comentários e parentização |
| Validar o gerado | `parser.parseRuleFromFile(...)` | Se reparseia, devolve o autômato — round-trip *semântico*, não só sintático |

### Três atritos reais na direção `.mop` → `.crysl`

1. **Sobrecarga resolve-se pelos tipos dos `OBJECTS`**, não pela assinatura escrita. O
   `CrySLScopeProvider` monta o escopo com os métodos cujos tipos de parâmetro casam com os objetos
   citados. O tradutor precisa *sintetizar objetos tipados* antes de emitir eventos.
2. **`ORDER` não tem operador de intercalação.** "Dois eventos em qualquer ordem" escreve-se como
   disjunção de permutações — o `SSLEngine` faz literalmente isso. Liberdade de ordem sobre *k*
   eventos explode em *k!*. Reportar como não-representável é resposta legítima.
3. **`!`, `*` e `/` estão na gramática mas lançam `UnsupportedOperationException` no leitor.**
   Território proibido. Idem as palavras reservadas que não podem nomear objeto: `alg`, `mode`,
   `pad`, `part`, `elements`, `in`, `this`, `after`, `throws`.

### Duas consequências operacionais

- **O classpath é parte da semântica.** `SPEC` e os tipos de `OBJECTS` são `JvmTypeReference`
  resolvidos de verdade — o parser pegou `DigestOutputStream.on(java.lang.String)`, que não existe
  na JDK. Ler regras destinadas ao Android contra a JDK do host e assumir o resultado válido seria
  erro.

  **Testado em 21/08/2026 (V3), e a conclusão mudou: não dá para mirar a API 30, e não faz falta.**
  O classpath virtual é estritamente **aditivo** — `CrySLModelReaderClassPath.getClassPath()`
  devolve a união do `java.class.path` com o virtual, e o `CrySLModelReader` constrói
  `new URLClassLoader(urls)` com pai padrão, então a resolução é *parent-first* e a JDK vence todo
  nome que ela tenha. Duas sondas decidem: `android.util.Base64.encodeToString` (só Android) **não**
  resolve sem o jar e **resolve** com ele; `java.util.HexFormat.formatHex` (JDK 17, ausente da API
  30) **resolve nos dois modos**. A via alternativa — uma JVM cujo classpath de aplicação contenha só
  o `android.jar` — também não funciona, por razão de princípio: `java.base` não vem do
  `java.class.path`, vem da camada de módulos, e nem `parent = null` a remove. Restringir a leitura
  exigiria substituir o `ClasspathTypeProvider`.

  **O impacto disso no corpus é zero, e agora está medido na configuração certa.** As **30** regras
  que carregam sob leitor novo por regra produzem **141** linhas de assinatura resolvida **idênticas**
  com e sem o `android.jar` (`diff` = 0). O desenho que substitui a via impossível é **conferir a
  posteriori**: indexar o `android.jar` e verificar cada assinatura resolvida. Medido em **141**
  eventos — é também o lado do `141 × 152` que o §10 e o §13 registram como divergência aberta —,
  dos quais 119 casam assinatura exata, 17 casam só por aridade (apagamento de genéricos e
  `AnyType`), 2 são limitação do conferidor (`SecretKey.destroy/getEncoded`, herdados), e **3 são
  achado real**: `java.security.spec.DSAGenParameterSpec` (só existe da API 35 em diante) e
  `javax.xml.crypto.dsig.spec.HMACParameterSpec` (o pacote `javax.xml.crypto` inteiro não existe em
  nenhum nível de API Android). E `jca_android/HMACParameterSpecSpec.mop` monitora essa segunda —
  uma das **24** specs do conjunto, **morta por construção** no Android. **Confirmado por execução em
  24/08/2026 (R7):** o arnês do gh104 replica a spec na JSE, onde a classe existe na JDK, e ela
  **acusa** sob o controle negativo `c c`; no Android o pointcut nunca casa. O monitor está vivo e é o
  alvo que não existe — ver §5.5.

> **Fechado em 24/08/2026 (R7) — a única pendência que este documento declarava como pré-requisito da
> abertura da change.** O texto anterior publicava **129** linhas de assinatura e **155** eventos
> conferidos, com duas ressalvas encadeadas (R5 e R6) dizendo que ambos vinham de uma sessão em modo
> lote, com **leitor partilhado** — a configuração que o §12 descarta. A remedição sob leitor novo por
> regra está em `docs/20260824_medicoes_pre_change_conformidade.md` §1, e dá:
>
> | passagem | regras que carregam | linhas `EVENT` | conferência contra o `android.jar` |
> |---|---:|---:|---|
> | **leitor novo por regra** (a configuração do §12) | **30 de 33** | **141** | 119 exata · 17 aridade · 3 classe-ausente · 2 limitação |
> | leitor partilhado (a antiga) | 31 de 33 | 155 | 131 · 19 · 3 · 2 |
>
> A linha de baixo **reproduz dígito a dígito** o `155: 131 + 19 + 2 + 3` que este parágrafo publicava
> — é o que calibra normalizador, sonda e conferidor contra a medição anterior antes de a nova entrar.
> E `155 − 141 = 14` é **exatamente** o número de eventos de `Signature.crysl`, a regra que só carrega
> sob leitor partilhado, por vazamento de `int offset`/`int len`. Não há segunda causa.
>
> **Três coisas não se movem, e é o que importa:** o `diff` continua zero, logo *o `android.jar` não
> muda uma única linha resolvida*; os **três achados reais** são literalmente os mesmos arquivos e as
> mesmas assinaturas; e as duas limitações do conferidor também.
>
> **O `129` não é reproduzível, e isso é achado.** Quatro configurações medidas — {5 substituições, 4
> substituições} × {leitor novo, partilhado} — dão 141, 155, 106 e 120; três regras de contagem mais
> estreitas sobre as saídas dão 126, 138, 75 e 81. **Nenhuma das sete dá 129.** É o aprendizado nº 1
> mordendo de novo: o número foi publicado sem a regra ao lado, e por isso não é conferível hoje. O
> reparo não é caçar a regra perdida; é publicar as duas juntas, que é o que esta tabela faz.

- **Dependências transitivas**, confirmadas por `dependency:tree` offline: Guava **33.5.0-jre**,
  Guice **7.0.0** e **`slf4j-simple` em escopo compile**. O `rvsec-parent` pina `guava.version=19.0`
  (**corrigido em 22/08/2026, R6:** dizia "presa ao Soot", e o §12 mede que nada liga o 19.0 ao Soot —
  o `javamop` não puxa nem Guava nem Soot; ver `:1431-1437`); se o `dependencyManagement` da raiz
  alcançar o módulo novo, força Guava 19
  debaixo de uma biblioteca que espera 33.5 — falha em runtime, não em compilação. O módulo não
  precisa de Soot, então dá para isolar, mas tem de ser decisão explícita no `pom`, com exclusão do
  `slf4j-simple`.

---

## 9. Defeitos encontrados

Achados que valem independentemente do módulo. Cada linha foi verificada nos arquivos ou por execução.

> **Coluna `conjunto`, acrescentada em 24/08/2026 (R7) — J-18, e é o reparo mais importante do §9.**
> Este inventário não dizia **de qual conjunto** falava, e o gh105 reparou coisas. Sete das linhas
> abaixo acusam defeitos **reparados no `jca_android`** e **vivos no `jca` congelado** — e o reparo
> não é apagá-las, é qualificá-las: todas continuam verdadeiras do congelado, que é o conjunto sobre
> o qual as medições publicadas do TSE 2023 moram. Sem a coluna, a proposta herdaria um inventário
> que acusa como aberto exatamente o que a change anterior fechou, que é o pior erro possível dele.
>
> Os valores da coluna: `jca` congelado · `jca_android` · **ambos** · `oráculo` (o `api30` e os
> templates do MetaCrySL) · `upstream` (as `CrySL-Rules`) · `ferramenta` (javamop, CrySLParser,
> gerador) · o módulo Java onde o defeito mora.

| Onde | conjunto | O quê | Consequência |
|---|---|---|---|
| `scripts/gh105_order_gate.py:136-200` | ambos (script) | Descarta as vírgulas e reusa precedência de expressão regular; a gramática CrySL tem `\|` ligando mais forte que `,` | **Veredito errado nas duas direções.** Uma regra afetada — `Cipher` — e é a que o gate reporta como falha. |
| `jca/KeyPairGeneratorSpec.mop:110` e `jca_android/…:128` (corrigidos em 22/08/2026, R6: os dois diziam `:130`, e o arquivo do `jca` congelado tem 118 linhas — aquele ponteiro nunca apontou para lugar nenhum; **atualizado em 24/08/2026, R7: o ponteiro do `jca_android` moveu-se de `:128` para `:158`**, e o do `jca` continua em `:110`) | **`jca` vivo · `jca_android` vivo, com dono** | Única spec com `@fail` sem `__RESET`; o estado de falha é absorvente e o dispatcher não tem trava | Uma vez em falha, **todo evento seguinte re-dispara o handler** — ORDER e `remove()` repetidos sem limite. Está no `jca` congelado, logo infla as medições publicadas. **Mudou de estatuto em 24/08/2026 (R7), e para melhor:** o commit `5fbe8173` (tarefa 8.7 do gh105) registrou-o no `divergence_record.csv` como **divergência comportamental deliberadamente não reparada**, com a medição ao lado (*"20 of the 21 `@fail` blocks of `jca_android` end in `__RESET`, and `KeyPairGeneratorSpec.mop:158` is the exception"*) e a razão de não reparar — é mudança de comportamento e exige medição de corpus própria. Deixa de ser defeito aberto sem dono e passa a ser divergência com dono e critério. |
| `MetaCrySL/src/generator/PrettyPrinter.rsc:49,139` | oráculo | `FORBIDDEN:` com dois-pontos e `;;` após `neverTypeOf` | 7 de 33 regras `api30` não são CrySL válido. Duas linhas de conserto. |
| `generated/api30/Signature.cryptsl:51` | oráculo | `offset` e `len` usados em `u3`/`s2`/`v2` sem declaração em `OBJECTS` | **Reafirmado em 22/08/2026 (R5):** é defeito da regra, e o oficial declara os dois. A regra carrega ou não **conforme quais outras foram lidas antes no mesmo leitor** — quem a resgata são exatamente `GCMParameterSpec`, `IvParameterSpec` e `Mac`, as três únicas que declaram ambos. O parser **não infere** tipo nenhum: herda a declaração vazada. Sob leitor novo por regra, `Signature` falha. |
| `generated/api30/DigestOutputStream.cryptsl:20` | oráculo | `FORBIDDEN on(java.lang.String)` — o método real recebe `boolean` | Regra não carrega. Só um parser que resolve tipos pega isso. |
| `generated/api30/AlgorithmParameters.cryptsl:47` | oráculo | `alg in {"BLOWFISH"} => preparedIV[params]` — predicado dentro de `CONSTRAINTS` | Cláusula no bloco errado; pertence a `REQUIRES`. Forma única no conjunto. |
| `CrySL-Rules/SSLEngine.crysl:12` | upstream | `EnableProtocol := cp1;` mas o evento é `ep1` | Typo em 1.5.2 *e* 3.0.1 — **a regra nunca carregou**. São 47 regras efetivas, não 49. |
| `CrySL-Rules/OAEPParameterSpec.crysl:8` | upstream | Declara `java.lang.String alg;`, hoje palavra reservada | Rejeitada pela gramática 4.x. Foi por isso que a 3.0.1 removeu o objeto. |
| `jca/GCMParameterSpecSpec.mop:23,34` | `jca` congelado | Dois eventos com id `c1`; o `ere` referencia um `c2` inexistente | Parseia em silêncio. Corrigido em `jca_android`; presente no conjunto arquivado. |
| `KeyPairSpec.mop:38` (ambos os conjuntos) | **`jca` congelado** — reparado no `jca_android` | O evento `gpr` (`getPrivate()`) grava `GENERATED_PUBLIC_KEY` | Chave privada registrada sob o predicado da pública. |
| `TrustManagerFactorySpec.mop:101` | **`jca` congelado** — reparado no `jca_android` | `generatedTrustManager[tms]` gravado como `GENERATED_KEY_MANAGERS` | Trust manager sob o predicado dos key managers. |
| `SecretKeySpecSpec.mop:45` e `SecretKeySpec.mop:26` | **`jca` congelado** — reparado no `jca_android` | `preparedKeyMaterial` implementado como `RANDOMIZED`, nas duas pontas | Funciona operacionalmente, mas usa o hub `RANDOMIZED`. ~~A constante `PREPARED_KEY_MATERIAL` existe e **não tem um único sítio**.~~ **Falso desde o gh105 — remedido em 24/08/2026 (R7), J-03:** são **três** sítios no `jca_android` (`SecretKeySpecSpec.mop:80` e `:134` leem, `SecretKeySpec.mop:125` escreve), e a constante ganhou Javadoc citando a cláusula CrySL (`Property.java:56-68`). A confusão que a linha descreve continua **viva no `jca` congelado** (`jca/…:29` e `:46`), que é o que a coluna `conjunto` agora diz. |
| `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70` | MetaCrySL | `sequence` (`,`) declarado com prioridade **maior** que `or` (`\|`) — invertido em relação à gramática Xtext oficial | Mesmo defeito do gate, na outra ponta do pipeline. Invisível hoje porque o `ppEventExp` só parenteteriza nós `parentheses()`: o texto sai igual ao que entrou e a AST errada não aparece. Um emissor `.mop` a exporia na hora. |
| `TrustManagerFactorySpec.mop:98-99` | **`jca` congelado** — reparado no `jca_android` | Três erros de copiar-e-colar no mesmo evento `gtm1`: tipo de retorno `KeyManager[]` no pointcut, ligação `TrustManager[][]`, e a `Property` errada | O pointcut declara um método que não existe com aquela assinatura. Um gerador que deriva de `EVENTS` + API real não produz nenhum dos três. |
| `generated/api30/Cipher.cryptsl:131,133,135` | oráculo | `length(x) <= off` — comparação invertida; a análoga implementada (`SecretKeySpec.cryptsl:29`) escreve `>=` | Transcritas literalmente, acusam **todo uso conforme** de `doFinal`. Vêm do template base (`MetaCrySL/samples/jca/base/Cipher.cryptsl:80-82`), logo regerar `api30` não as corrige. **Precisado em 22/08/2026 (R5):** o upstream (`CrySL-Rules/Cipher.crysl:122,123,127,128`) escreve as **quatro** com `>=`, logo não é perda de cláusula e sim **corrupção de operador** contra a fonte de verdade. |
| `MetaCrySL/samples/jca/base/Cipher.cryptsl:79` (→ `api30:129`) | oráculo | `length(pre_plaintext) >= pre_plain_off + len`, mas `len` é ligado pelos `doFinal`; quem liga o comprimento do `update` é `pre_len` — declarado (`api30:25`), ligado em `u3`/`u4`, e usado por cláusula nenhuma | A cláusula relaciona um buffer do `update` com um comprimento do `doFinal`. O upstream distinguia `prePlainTextLen` de `plainTextLen`. Imune a regeração. Achado de 22/08/2026 (R5). |
| `jca_android/MacSpec.mop:143-147` e `jca/MacSpec.mop` | **`jca` congelado** — reparado no `jca_android` | O evento `f2` declara `target(m)` sem `m` nas formais; o `ajc` trata `m` como **nome de tipo** — `[warning] no match for this type name: m [Xlint:invalidAbsoluteTypeName]` | **O pointcut nunca casa.** Como `f2` está no `ere` (`:160`), todo programa que fecha um `Mac` com `doFinal(byte[],int)` é acusado de `MAC-ORDER-00`. É `MacSpec` 7/8, e faltava na linha das specs com fatiamento quebrado. Achado de 22/08/2026 (R5). |
| `javamop/.../ast/mopspec/MOPParameters.java:41-51,84-94` | ferramenta | `add` descarta em silêncio parâmetro cujo **nome** já existe; `getParam` compara só o nome, ignorando o tipo. Sem log, sem exceção — ao contrário de evento duplicado, que é detectado e renomeado (`JavaMOPSpec.java:100-135`) | 11 specs do `generic` perdem declarações, e **o tipo sobrevivente na tupla de indexação pode não ser o que os eventos ligam**: `FSM123(InetAddress i, InetSocketAddress i)` gera `FSM123(InetAddress i)` com os três eventos ligando `InetSocketAddress i`, exit 0 e zero avisos. Achado de 22/08/2026 (R5). |
| monitor gerado, `Prop_1_event_*` | ferramenta | O monitor é criado (`FindOrCreateEntry`) **antes** de a `condition` ser avaliada | Uma guarda reprovada deixa um monitor vivo no estado 0, e o evento seguinte é julgado dali. É metade do mecanismo do falso `InvalidSequenceOfMethodCalls` do §5.1. Achado de 22/08/2026 (R5). |
| `generated/api30/SSLContext.cryptsl:52` | oráculo | `randomized[sr]`, mas `EVENTS` declara `Init: init(kms, tms, _)` — `sr` é anonimizado | Não existe ponto do programa em que `sr` tenha valor. Cláusula inligável por qualquer pointcut. |
| `generated/api30/KeyPairGenerator.cryptsl:64` | oráculo | `alg in {"EC"} => preparedEC[params]`, e **nenhuma** das 33 regras ensures `preparedEC` | Predicado órfão. Um tradutor que veja só esta regra emite uma leitura que nunca pode responder `SATISFIED`: todo `initialize(ECGenParameterSpec)` conforme vira report. |
| `rvsec-core/.../jca/util/CipherTransformationUtil.java:10-30` | `rvsec-core` | `mode("AES/")` lança `ArrayIndexOutOfBoundsException`; `alg("/")` também. As três utilitárias caem juntas, porque `Api30CipherTransformationUtil` e a arquivada delegam o parsing a esta | **Alcance corrigido em 21/08/2026 (V9):** o defeito existe, mas a entrada não chega. `Cipher.getInstance` rejeita toda transformação com barra final antes de retornar (`Invalid transformation format`), e todo sítio de `isValid` recebe uma transformação que já sobreviveu ao `getInstance` — por `args()` num `after … returning`, ou por `c.getAlgorithm()`. **Latente**, não crash vivo: vale a guarda de duas linhas, não vale urgência. |
| `KeyPairGeneratorSpec.mop:40-48` | ambos | `switch` total com `default: return false` fechando um conjunto **aberto** de implicações | `alg in {"ElGamal"}` não casa nenhuma cláusula, logo pelo oráculo o `keySize` fica irrestrito. Na prática `getInstance("ElGamal")` não emite erro e o `initialize(1024)` seguinte reporta `KEYPAIRGENERATOR-KEYSIZE-00`: acusa a violação errada e cala a certa. |
| **5 de 22** specs parametrizadas (era `7 de 21` — recontado em 24/08/2026, R7, J-20: `MacSpec` e `TrustManagerFactorySpec` repararam a ligação, e o denominador subiu com o `IvChainJunction`) | ambos | Ligação parcial ou nula do parâmetro declarado. **Rederivado em `5fbe8173` (R7):** `KeyStoreSpec` 0/7, `HMACParameterSpecSpec` 0/1, `RandomStringPassword` 0/2, `KeyPairSpec` 2/3, `PBEKeySpecSpec` 2/4 — ~~`TrustManagerFactorySpec` 3/4~~ e ~~**`MacSpec` 7/8**~~ **repararam a ligação no `jca_android`** e continuam na lista do `jca` congelado, onde a medição original vale | **Corrigido em 22/08/2026 (R5):** os seis números originais conferem contra o código gerado, mas a frase-cabeçalho ("nenhum evento liga") contradizia as três últimas linhas, que ligam parcialmente. Onde a ligação é **0/N** o fatiamento é no-op e a spec degenera para autômato global — `KeyStoreSpec(KeyStore ks)` declara `ks` e os 7 eventos usam uma variável livre `k`. O `MacSpec` faltava (linha própria acima). O oráculo decidível é o monitor gerado: **5 das 24 não constroem `MapOfMonitor`** (as três com 0/N, mais `CipherInputStreamSpec` e `CipherOutputStreamSpec`, que são declaradas **sem parâmetro** e por isso ficam fora destas 22 — o denominador era 23 e cresceu com o `IvChainJunction`; o conjunto das cinco é o mesmo). **E as cinco foram replicadas por execução em 24/08/2026 (R7):** quatro têm monitor vivo, uma não tem sítio de acusação nenhum, e as causas são três, não uma. Ver §5.5. |
| `jca/SignatureSpec.mop` — os eventos `s1`/`s2` | **`jca` congelado** — reparado no `jca_android` pela tarefa 6.3 | `call(public byte Signature.sign())` — o método devolve `byte[]`, não `byte`. **Acrescentado em 24/08/2026 (R7), J-21:** a tarefa 6.3 do gh105 registra o reparo no conjunto novo, e o achado que o §9 não tinha é o que sobra no congelado | **O pointcut não casa chamada nenhuma.** `s1` e `s2` são **produtores inexistentes** no conjunto sobre o qual as medições publicadas do TSE 2023 foram feitas — toda cadeia de predicado que dependa deles está morta lá, e nenhuma métrica estrutural que leia só o `.mop` percebe. |
| `CrySLModelReader.getStatesForMethods` | ferramenta | `after <Agregado>` resolve para **conjunto de nós vazio** quando **nenhum método** do agregado aparece no `ORDER` | **Confirmado por sonda em 21/08/2026 (V9):** `after Fora`, com `Fora := d2` e `d2` fora do `ORDER`, devolve `eventos=1 NOS=0` — o predicado vale em estado nenhum, a regra carrega sem erro e sem aviso. A resolução é **por método, não por nome de agregado**: `Sozinho := g1` com `ORDER Gets, d1` resolve normalmente. **Alcance no corpus: zero** — as 19 cláusulas `after` das 33 regras citam, todas, símbolo presente no `ORDER`. |

### Defeitos acrescentados em 21/08/2026 pela execução das validações

| Onde | O quê | Consequência |
|---|---|---|
| `crysl.parsing.CrySLModelReader` | **O escopo de `OBJECTS` vaza entre regras lidas pelo mesmo leitor, nos dois sentidos.** `Signature.crysl` usa `offset` e `len` sem declará-los: sozinho **falha**; depois de `GCMParameterSpec`, `IvParameterSpec` ou `Mac` — as três que declaram ambos —, **carrega**. E na direção contrária, `SecretKey.crysl` lido antes de `Key.crysl` **quebra** o `Key.crysl`, que sozinho carrega | O conjunto que carrega **não é função do corpus**: 40 ordens aleatórias com leitor partilhado dão `{29:3, 30:15, 31:22}`, e com leitor novo dá 30 invariavelmente. O vazamento esconde defeito *e* cria defeito. **Ampliado em 22/08/2026 (R5):** a razão para "um leitor por regra" não é o denominador, é **determinismo** — e é por isso que o número do corpus é 30 e não 31. |
| `MetaCrySL/samples/jca/base/{DHGen,DSAGen,Iv}ParameterSpec.cryptsl` | **Três templates base perderam a seção `CONSTRAINTS` inteira** em relação à regra CrySL de origem — ~9 cláusulas normativas | O oráculo `api30` pede menos do que a regra de origem. Uma spec `.mop` fiel à origem aparece como `MOP-SEM-BASE`. Regerar o `api30` não corrige: a perda está no template. Ver §5.3 e o "teto do oráculo" no §6. |
| `generated/api30/DSAGenParameterSpec.cryptsl` e `HMACParameterSpec.cryptsl` | **Especificam classes que não existem na plataforma Android.** `java.security.spec.DSAGenParameterSpec` só aparece na API 35; `javax.xml.crypto.dsig.spec.HMACParameterSpec` não existe em nenhum nível verificado (26, 30, 33, 35) | Duas de 33 regras do oráculo Android são sobre API que o Android não tem. E `jca_android/HMACParameterSpecSpec.mop` monitora a segunda: uma das 23 specs do conjunto, **morta por construção** — o pointcut nunca casa. É outro ângulo sobre o "0/1 parâmetro ligado" da linha acima. |
| pipeline `javamop` + `rv-monitor` + `javac` | **Os dois defeitos de sintaxe do `jca` congelado atravessam o pipeline inteiro em silêncio** | 23/23 `.rvm`, monitor gerado, e **compila com 0 erros**. Para `jca/GCMParameterSpecSpec.mop` o monitor sai com `RVM_eventNames = {"c1", "c1"}` e uma só `Prop_1_transition_c1`; o `c2` do `ere` **desaparece do alfabeto sem aviso**. Nem "parseou", nem "gerou monitor", nem "compilou" é oráculo de sanidade. |

### As tabelas manuais

Ambos os gabaritos foram conferidos linha a linha contra um censo independente. A enumeração está
correta nos dois; o que envelheceu foram colunas.

- **`constraint_table.csv`** — enumeração exata (55/55 cláusulas, 30/30 nas ausentes). Mas as colunas
  `mop_line` e `verdict` descrevem a semente `jca` congelada, não as specs `jca_android` de hoje: as
  linhas apontadas caem em comentários nos arquivos atuais. Uma linha `MOP-SEM-BASE` está aposentada
  (a allow-list de `SecretKeySpecSpec`, removida) e falta outra (a leitura `RANDOMIZED` sobre o
  *password* em `PBEKeySpecSpec.mop:108-118`).
- **`predicate_graph.csv`** — 85 linhas de dados no commit em que este censo foi feito (`d64f3a40`),
  casamento **85/85** com o censo independente, zero chaves de um lado só. Duas linhas com
  `mechanism` desatualizado: `SecureRandomSpec` `next1` e `next3` já migraram para `PredicateStore` e
  o CSV ainda diz o contrário. **Medido de novo em 22/08/2026 (R5): 73 linhas de dados em
  `c12f4689`** — o arquivo encolheu com a migração (`86 → 85 → 79 → 78 → 74` linhas totais), e é a
  segunda medição independente que carimba o instantâneo deste documento. **Remedido em 22/08/2026
  (R6): 63 em `f188c55b` e 45 em `8a33bc41`**, depois de a tarefa 4.14 migrar os sete últimos
  arquivos. **Remedido de novo em 24/08/2026 (R7): 70 linhas de dados em `5fbe8173`** — o arquivo
  encolheu com a migração e **voltou a crescer** com a fiação dos grupos 5 a 8. A trajetória completa
  é `85 → 73 → 63 → 45 → 70`, e é o argumento vivo para publicar regra de contagem e commit, nunca o
  escalar sozinho: dois dos cinco valores são iguais a menos de dez linhas e descrevem estados do
  arquivo separados por quatro dias e por sinais opostos de movimento.

  **E as cinco colunas de julgamento não são deriváveis de artefato nenhum.**
  `scripts/gh105_predicate_graph.py` (1845 linhas) nunca lê um `.cryptsl` — as três ocorrências de
  `crysl` no arquivo estão em prosa de comentário —, e o próprio docstring diz que carrega *"the
  committed `data/jca_android/predicate_graph.csv` for the judgment columns **no analyzer can
  re-derive**"* (`:34-35`, repetido em `:1028-1030`). `carry_judgments()` copia-as de uma versão
  anterior do próprio CSV. A classificação FIEL / PROJETADO / CONFLADO / AUSENTE do §5.4 é
  **julgamento humano semeado e propagado por cópia**, e tem de ser publicada como tal — não como
  medição. Dar-lhe domicílio derivável é uma das coisas que o componente resolve.

  > **Reparado em 24/08/2026 (R7) — J-04: a ressalva mudou de domicílio.** Ela morava **só aqui**, e
  > os números de M4 saíam no §5.4 e no §13 sem ela. Passa a abrir o §5.4, para acompanhar **todo**
  > número da métrica, e "dar domicílio derivável a essas cinco colunas" vira entregável nomeado —
  > item 10 do §13, e não subproduto.
- **`order_alphabet_map.csv`** — ~~o gate pula 13 das 23 specs por falta de linhas, incluindo
  `KeyGeneratorSpec` e `MessageDigestSpec` (dívida declarada da tarefa 7.1). Duas discordâncias de
  conteúdo: a razão registrada para `SecureRandomSpec.g4` está factualmente errada … e `CipherSpec.f2`
  deveria mapear `{f1,f2,f4}`, não `{f2,f4}`.~~

  > **As três reparações pendentes saíram — e uma delas hoje *introduziria* o erro que pretendia
  > corrigir. Reparado em 24/08/2026 (R7), J-19.**
  >
  > 1. **A cobertura foi fechada.** A tarefa 7.1 está concluída: o arquivo passou de 121 a **207
  >    linhas** e cobre as **22 specs pareáveis**, com as duas restantes declaradas *skip* e com razão
  >    escrita (`IvChainJunction` e `RandomStringPassword`). O "pula 13 das 23" não descreve mais nada.
  > 2. **A razão do `SecureRandomSpec.g4` foi corrigida na fonte.** A linha de hoje diz
  >    *"the invalid-algorithm accuser over the same `getInstance(String, ..)` calls as g1/g2; task
  >    3.1 absorbs it"*.
  > 3. **`CipherSpec.f2` mapear `{f1,f2,f4}` está errado hoje, e aplicá-lo quebraria o mapa.** A
  >    tarefa 6.6 estreitou o pointcut de `doFinal(..)` para `doFinal(byte[], ..)`; `doFinal()` nu já
  >    não casa `f2`, e **`{f2,f4}` é a resposta certa** — que é o que o CSV já diz, com a razão na
  >    própria linha. A reparação venceu. É o caso que ensina a medir se um reparo listado ainda é
  >    reparo antes de aplicá-lo, e o de pior consequência desta rodada se tivesse passado.

---

## 10. A direção inversa — gerar `.mop` a partir da regra

A terceira rodada perguntou o oposto do §1: em vez de traduzir `.mop` → `.crysl`, **traduzir
`.crysl` → `.mop`**, automaticamente. A pergunta muda o veredito daquela seção, e por um motivo
só: o argumento que matou o tradutor original era que a regra sintetizada não tem consumidor.
O `.mop` sintetizado tem — é o próprio pipeline do RVSec.

Sete investigações paralelas cobriram as camadas da tradução. Os números são por camada, nunca
agregados, pela mesma razão do §6.

> **Rebaixado a ESTIMATIVA NÃO MEDIDA em 22/08/2026 (R5), e é a correção mais importante deste
> documento.** A tabela abaixo anuncia percentuais de automação, mas nenhum dos seus números tem
> artefato de origem no repositório: `grep -rl` por `152/167`, `16/55` e `67,6` em toda a árvore
> devolve este documento, a auditoria e as revisões externas — **não** o registro de validações que
> esta seção cita como fonte, nem CSV, nem script. Não há contra o que recalcular. Além disso, quatro
> das cinco linhas não fecham aritmeticamente:
>
> - `152/167`: o percentual está certo, mas `167 − 152 = 15` e o texto só nomeia 12. E o §8 mede
>   **155** eventos conferidos contra o `android.jar` — as duas seções discordam entre si.
> - `7/22` + `11/22`: não fecha em leitura nenhuma. Disjunto dá 18, e as 4 restantes não são citadas;
>   aninhado, sobram 11, também não citadas. O "gêmeo negado (10/22)" não corresponde a nenhum dos dois.
> - `16/55` + `47/55` = **63 > 55**. E nenhum dos dois se reconcilia com a partição do §5.3
>   (`11+3+4+7+30`, presentes = 25).
> - `87/92` + "4 lacunas": `92 − 87 = 5`. O 87 é o número vivo (94,565 % arredonda para 94,6 %), mas
>   o §10.4 diz "reduzido de 19 para 4", que só vale com 88. Falta nomear a quinta lacuna.
> - `67,6 %` + `9 %` somam 76,6 %; os 23,4 % restantes não têm nome nem destino, e "linhas do arquivo"
>   nunca declara de quais arquivos.
>
> Contraste que isola o problema: a decomposição do §5.4 fecha exatamente (`26 + 28 + 19 + 19 = 92`) e
> o vetor `26/54/73/92` é coerente com ela. É esta seção que se solta. **Nada daqui entra na proposta
> sem arnês depositado**; o que está medido são as três specs geradas, abaixo.

| Camada | Automação **estimada** (não medida) | O que sobra para o humano |
|---|---|---|
| `OBJECTS`+`EVENTS` → pointcuts | 152/167 eventos (91 %) resolvem para assinatura única | política do `_` (12 eventos); `before` × `after` |
| `ORDER` → `ere`/`fsm` | 22/22 cláusulas parseáveis; 7/22 saem idênticas ao gabarito humano, 11/22 equivalentes em linguagem | sintetizar ou não o gêmeo negado (10/22) |
| `CONSTRAINTS` → Java | 16/55 sem decisão alguma; 47/55 sob uma política declarada | a relação de igualdade (§10.3) |
| `REQUIRES`/`ENSURES`/`NEGATES` | **87/92 (94,6 %)** | 4 lacunas do `PredicateStore` |
| Linhas do arquivo | 67,6 % (template + derivável) | 9 % de código |

> **Carimbo, acrescentado em 22/08/2026 (R6).** Esta tabela não tem commit **e não tem artefato** — é
> a única do documento em que as duas coisas faltam ao mesmo tempo, e é por isso que o bloco acima a
> rebaixa a estimativa. Os dois denominadores que dela dependem e que se movem são o `167`, que a via
> AST não validada produz (§10.2), e o `92`, que o Grupo 5 do gh105 altera. Enquanto o arnês não for
> depositado, nenhum número desta tabela deve ser citado fora do §10.

**Estes números continuam sendo previsão para o conjunto todo — mas deixaram de ser para três
specs.** Em 21/08/2026 um gerador foi escrito e três specs foram geradas de `api30`
(`DHGenParameterSpec`, `GCMParameterSpec`, `PBEParameterSpec`), comparadas contra o gabarito humano
`jca_android` pelas quatro métricas, e passadas pelo pipeline inteiro do `javamop` até compilar:

| | resultado sobre as três specs |
|---|---|
| **M1** eventos | 5/5 — mesmos ids, mesmas assinaturas de `call(...)` |
| **M2** ordem | 3/3 linguagens equivalentes |
| **M3** constraints | 2/2 sobre o que o oráculo pede, no mesmo idioma (corpo, não guarda) |
| **M4** predicados | 5/5 arestas emitidas |

As divergências contra o humano são três e todas nomeáveis: o oráculo `api30` perdeu uma cláusula que
a regra CrySL de origem tem (§5.3); o substrato de predicado é parâmetro, não dedução (§10.3); e
faltava ao §10.3 a política de acoplamento `ENSURES` ↔ `CONSTRAINTS`, que o corpus humano já
pratica. Nenhuma delas é ruído de tradução. Evidência:
`docs/20260821_validacoes_conformidade_mop_crysl.md`, V2 e V7.

### 10.1 O classpath é entrada obrigatória, não conveniência

Nada no texto CrySL diz se `getInstance(alg)` é estático ou de instância — `KeyGenerator.cryptsl:19`
(`g1: getInstance(alg);`) e `:25` (`i1: init(keySize);`) têm a mesma forma. O tipo de retorno falta em
140 dos 167 eventos. E o `_` de `getInstance(alg, _)` esconde 2 ou 3 sobrecargas conforme a classe.

Resolvidos contra o `android.jar` da API 30, os três desaparecem: `javap` diz estático/instância/
construtor, e a regra `ctor ou static → after … returning(SpecType p)` / `instância → target(p)`
reproduz 97/97 dos casos do corpus. Sem o classpath, a camada cai de 91 % para cerca de metade.

Essa resolução também é o que pega defeito de entrada: 2 das 33 regras têm assinatura que não existe
na API 30, e `Mac.cryptsl:33,35` declara dois eventos **literalmente idênticos** — coisas que um
parser puramente sintático aceita calado.

### 10.2 O `ORDER` chega compilado, com três ressalvas

`CrySLParser.parseRuleFromFile` devolve `CrySLRule.getUsagePattern()`, um `StateMachineGraph` com
`getNodes()`, `getEdges()`, `getAcceptingStates()`. As arestas já vêm com as sobrecargas agregadas
(`init ×8`, `update ×4`) — é a normalização "1:N sobre agregado" do §5.2, de graça. E como quem
parseia é a gramática Xtext oficial, o problema de precedência do §4.2 não existe desse lado.

As ressalvas, todas verificadas na fonte (`StateMachineGraphBuilder.java`):

- É uma **NFA de Glushkov, não determinizada e não minimizada**. `ORDER Con, A?, A` produz duas
  arestas `a` saindo do mesmo nó. Emitir `fsm:` exige determinizar. Há um bloco de fusão de estados
  comentado no construtor, com um `// TODO` — a minimização foi tentada e abandonada.
- Os rótulos são **métodos concretos, não agregados**: `Gets := A | B` vira uma aresta rotulada
  `[a(), b()]` e o nome `Gets` some. Como o corpus humano escreve `ere: (g1|g2) (update+ …)` —
  misturando eventos concretos com agregados —, preservar os nomes exige caminhar a AST EMF, e a
  fachada `CrySLParser` a descarta. São ~10 linhas replicando `CrySLModelReader` para recuperá-la.
- `wrapUpCreation()` **precisa ser chamado à mão**; sem isso `getHopsToAccepting()` devolve
  `Integer.MAX_VALUE`. Nenhum ponto do repositório CrySL o chama.

**As três, medidas em 21/08/2026 (V4, V5):**

- O não-determinismo é real — a sintética `ORDER con, a?, a` produz mesmo duas arestas `a` do mesmo
  nó — mas **nenhuma das 30 regras `api30` que carregam o exibe**. A determinização entra por
  correção geral, não por necessidade deste corpus.
- As ~10 linhas funcionam fora do jar publicado, e entregam mais do que se pedia: `Domainmodel` para
  **33/33** arquivos, **167 nomes de evento**, **61 agregados** com os membros, o texto cru do
  `ORDER`, e a procedência `arquivo:linha` por `NodeModelUtils` — que é o que o §11.3 pedia e supunha
  ter de vir de varredura de texto do lado CrySL.

  > **Ressalva obrigatória, medida em 22/08/2026 (R5): o 33/33 é verdadeiro e é vazio.**
  > `getResource(…, true)` devolve a árvore com recuperação de erro; ninguém validou. Chamando
  > `IResourceValidator` explicitamente sobram **30**, os mesmos da fachada com leitor novo. E usar os
  > três recusados é ativamente perigoso: `Signature` dá `NullPointerException` em
  > `resolveEventsToCryslMethods` e em `buildSMG`; `DigestOutputStream` dá `NullPointerException` em
  > `CrySLReaderUtils.toCrySLMethod(forbidden)`; e o `AlgorithmParameters` **trunca em silêncio** —
  > `alg in {"BLOWFISH"} => preparedIV[params];` é lido como `algName in {"BLOWFISH"}`, com a
  > implicação e o predicado apagados sem sinal, de modo que a regra passa a *exigir* que o algoritmo
  > seja BLOWFISH. Nem `v5/V5.java` nem `v6/LiftCrysl.java` consultam `resource.getErrors()` hoje.
  > O que a via ganha de verdade: os agregados (a fachada os descarta; a AST os entrega em 23/33 com
  > procedência) e o `ORDER` compilado (`StateMachineGraphBuilder.buildSMG` é `public static`, 32/33).
  > O que ela perde: a árvore `ISLConstraint` de `CONSTRAINTS` e a montagem de `CrySLPredicate` —
  > métodos privados de `CrySLModelReader`, que só expõe `readRule`.
- `wrapUpCreation()` confirmado: `getHopsToAccepting()` do nó inicial é `2147483647` antes e o valor
  correto depois, em cinco regras.

### 10.3 O acoplamento CONSTRAINTS ↔ ORDER

As duas camadas não se traduzem de forma independente. No estilo humano, uma allow-list gera um
**par** de eventos sobre o mesmo join point — `g1` com `condition(matches(...))` e `g3` com
`condition(!matches(...))` — e o negativo entra no alfabeto do autômato. São 8 gêmeos negativos no
`jca_android`, e a ERE teve de mudar para acomodá-los: o `g3*` de `KeyPairGeneratorSpec.mop:128` é um
prefixo de laço que o `ORDER` da regra não tem. O `order_alphabet_map.csv` registra esses símbolos
como `order-unmapped`, com a justificativa escrita: *"an ORDER has no symbol for a call it rejects on
a constraint"*.

Há duas saídas, e o gerador tem de escolher uma:

1. **CONSTRAINTS só em corpo de evento** (`if (…) addError(…)`). O alfabeto fica intacto e as duas
   camadas desacoplam.
2. **Par positivo/negativo**, e então o gerador precisa emitir simultaneamente o `.mop` **e** o mapa
   de alfabeto, porque sem as linhas `order-unmapped` a comparação de ordem fica errada.

O corpus escolheu (1) onde a cláusula é aritmética e (2) onde é allow-list. A migração do gh105 vem
movendo casos de (2) para (1), e o motivo está escrito em `PBEParameterSpecSpec.mop:80-83`: uma
`condition` compila para `if (!(guarda)) return false;` **antes** do corpo e **antes** da transição,
então guarda falsa tira a chamada do autômato e a chamada seguinte é acusada de sequência errada —
um defeito que o programa não tem. **O default do gerador deve ser (1).**

O mesmo raciocínio fixa onde vai a leitura de `REQUIRES`: sempre no corpo, nunca em `condition(...)`,
nunca em `@fail`. Isso é decidível pelo bloco em que a cláusula aparece — o gerador não escolhe nada.

Uma terceira decisão é anterior ao gerador e não pode ficar implícita: **a relação de igualdade**.
`ConscryptAliasTable.matches("KeyGenerator", alg, algs)` é estritamente mais fraco que
`algs.contains(alg)` em dois eixos (dobra de caixa e resolução de alias), e 28 das 55 cláusulas mudam
de veredito conforme a escolha. A forma correta é o gerador emitir `EQ.in(service, x, LISTA)` com
`EQ` injetado, e o humano declarar `EQ = literal` (fiel ao oráculo) ou `EQ = plataforma` (o que o
corpus faz). A tabela em si é derivável: as 158 linhas carregam a fonte primária
(`OpenSSLProvider.java` do Conscrypt, branch `android11-release`) e poderiam ser extraídas.

**Uma quarta decisão, descoberta ao gerar (V2): o `ENSURES` não vale para uma construção que quebrou
uma cláusula.** O corpus humano escreve isto, e a primeira versão do gerador não escrevia:

```java
boolean conforms = true;
if (!validLengths.contains(tagLen)) { …addError…; conforms = false; }
…
if (conforms) { spec = s; }        // o campo que o @match lê só é ligado no ramo conforme
```

Sem essa política o gerador grava `preparedGCM` sobre um objeto construído com um tag length que a
regra recusa — o predicado passa a afirmar o contrário do que a regra diz. É acoplamento
`ENSURES` ↔ `CONSTRAINTS` e não é dedutível de nenhuma das duas cláusulas isoladamente: tem de ser
política declarada do gerador. O humano já a pratica; o §10.3 não a nomeava.

**E uma quinta, que é parâmetro e não política: o substrato de predicado.** `ExecutionContext` é
binário e emite um código por leitura; `PredicateStore` é três-valorado e emite dois
(`VIOLATED` e `NOT_OBSERVED`). A regra CrySL não diz qual usar — é estado da migração do gh105, e o
gerador tem de recebê-lo. Medido em V2: é a **única** divergência de M4 entre o gerado e o gabarito
humano das três specs.

### 10.4 O gerado seria melhor que o traduzido à mão

Não marginalmente. Na camada de predicados, um gerador com o grafo global das 33 regras emitiria
**87 das 92 cláusulas** — catorze acima do *teto* da tradução manual (73, §5.4), não da medição atual.
A razão é estrutural: a geração dissolve duas das três parcelas daquela decomposição. O débito de
cobertura some, porque emitir 33 specs custa o mesmo que emitir 23; o débito de fiação some, porque
aridade achatada e `Property` errada são erros de uma camada de indireção que a geração elimina.
Sobra o débito de substrato, reduzido de 19 para 4.

E há uma classe inteira de defeito que o gerador **não consegue cometer**, porque o nome do predicado
CrySL passa a ser a chave e não há vocabulário Java intermediário onde errar:

| Defeito humano | Por que o gerador não o cometeria |
|---|---|
| `@fail` sem `__RESET` em 1 de 21 | template não esquece a vigésima primeira ocorrência |
| Dois eventos com id `c1` | o nome sai de uma enumeração |
| Chave privada sob `GENERATED_PUBLIC_KEY` | `generatedPrivkey` ≠ `generatedPubkey` como chave |
| Trust manager sob `GENERATED_KEY_MANAGERS` | idem — o vocabulário Java oferecia três candidatos para um predicado |
| Fatiamento paramétrico quebrado em **5 de 22** specs (era `7 de 21` — recontado em 24/08/2026, R7, J-20) | `SPEC <Tipo>` nomeia o parâmetro; `target`/`returning` sai por construção |
| 18 de 18 cabeçalhos citando o oráculo errado | a procedência é emitida junto |

### 10.5 O que não se traduz

- **`neverTypeOf` e `notHardCoded`** (5 cláusulas) são propriedade do tipo estático da origem. Em
  runtime a assinatura já é `char[]`. Registro `Unknown{UntranslatableConstraint}` tipado, não
  comentário: comentário não é contável e não entra em métrica.

  > **Reparado em 24/08/2026 (R7) — J-17: o argumento fraco sai e um forte entra.** Esta alínea
  > terminava dizendo que *"o corpus cobre o defeito por outra via — o taint `String.toCharArray()` de
  > `RandomStringPassword.mop:18-23` alimentando um `REQUIRES randomized`"*. **Não cobre, e o próprio
  > arquivo escreve por quê**: em `5fbe8173` o cabeçalho de `RandomStringPassword.mop:18-40` declara
  > que **os quatro sítios de predicado da ponte foram apagados**, com a medição sobre os três tipos
  > de origem que o conjunto sabe pôr nela — `byte[]` converte pela identidade (`"[B@726f3b58"`),
  > `SecureRandom` converte para a constante literal `"SecureRandom"`, e `Integer`, a única conversão
  > fiel, não sobrevive ao chaveamento por identidade fora do cache `-128..127`. Das três, as duas que
  > propagam não carregam aleatoriedade e a que carrega não propaga.
  >
  > **O que entra no lugar é melhor do que o que saiu:** uma ponte de propagação de predicado **sobre
  > conversões de tipo** é, ela própria, uma classe de defeito que o componente detecta — predicado
  > escrito e lido sobre objetos que não são o mesmo objeto. É decidível do grafo de M4 (o produtor e
  > o consumidor têm tipos incompatíveis, ou o chaveamento é por identidade sobre um valor recriado),
  > e vai para a lista do §13. O caso concreto está confirmado por execução em 24/08/2026: as duas
  > rotas replicadas pelo arnês do gh104 (`RandomStringPasswordSpec-bytes-route` e `-int-route`) não
  > acusam em nenhum dos dois conjuntos — ver §5.5.
- **`IncompleteOperationError` não tem contraparte em `.mop`.** No CogniCrypt ele dispara no fim do
  tempo de vida do objeto, observado estaticamente. `@fail` cobre transição inválida e `@match` cobre
  aceitação; a terceira categoria exigiria um evento sintético de fim de escopo que nenhuma cláusula
  CrySL fornece. **Isto também limita o comparador**: quando M2 diz "linguagens equivalentes", está
  comparando palavras aceitas — captura `TypestateError` e é cego para `IncompleteOperationError`.
  O protocolo tem de declarar isso, como já declara "ordem correta" × "uso correto".
- **`noCallTo`/`callTo`** (`Cipher.cryptsl:123,125`) parecem constraints mas são predicados sobre
  símbolos do ORDER. E `:125` exige o evento `getIV()`, que `CipherSpec.mop` sequer declara.
- **3 cláusulas sairiam silenciosamente invertidas.** `Cipher.cryptsl:131,133,135` escrevem
  `length(x) <= off`, quando a análoga implementada (`SecretKeySpec.cryptsl:29`) escreve `>=`.
  Transcritas ao pé da letra acusam todo uso conforme de `doFinal`. O humano implementou zero das
  quatro cláusulas `length` do `Cipher` e implementou a do `SecretKeySpec` literalmente — a
  assimetria é a assinatura de um filtro humano que o gerador não tem.

### 10.6 A posição honesta sobre a contribuição

Um tradutor que funciona é **engenharia, não contribuição**. O JavaMOP é multi-lógica por desenho
(Chen & Roşu, OOPSLA 2007; Meredith et al., STTT 2012) e acrescentar um formalismo é uso previsto da
ferramenta. E o TSE 2023 do próprio grupo (Torres et al., *Runtime Verification of Crypto APIs: An
Empirical Study*, TSE 49(10):4510-4525, DOI `10.1109/TSE.2023.3301660`) já fez a tradução manual das
22 specs e a justificou dizendo que *"the CrySL and JavaMOP specification languages are similar"*
(`rvsec-paper/main.tex:811-814`) — a viabilidade não é a pergunta em aberto. **A citação foi
conferida na fonte em 22/08/2026 (R5)** e está correta, assim como o "22" (`macros.tex:132`,
`main.tex:824-825`); o corpus é que cresceu para 23 depois da publicação. O paper traz ainda uma
segunda justificação, mais forte e que este documento não citava: *"the rules are defined as EREs
over method call sequences and JavaMOP has native support for ERE as a spec language"*
(`main.tex:2825`) — que é precisamente o que o §10.2 apresenta como achado.

**A alegação de lacuna precisa ser mais estreita** — corrigida em 22/08/2026 (R5). O CrySL **já é
compilado para artefato executável** pela sua própria implementação de referência
(`CogniCrypt_SAST`; o compilador está descrito no CrySL, ECOOP 2018, não no CogniCrypt/ASE 2017 —
**ambos** já estão em `references.bib` do paper do grupo, `:324` e `:752`; precisado em 22/08/2026,
R6, porque a redação anterior sugeria que só o ASE estava lá), e linguagens de padrão sobre traço com backend
compilado existem desde 2005 — *tracematches* (Allan et al., OOPSLA 2005) compila padrão regular
sobre traço **com variáveis livres** em monitores AspectJ, que é literalmente o fatiamento
paramétrico do `.mop`; PQL (Martin, Livshits & Lam, OOPSLA 2005) é uma linguagem única com backends
estático e dinâmico. A formulação defensável é: *até onde apuramos, o CrySL não foi compilado para um
monitor de RV executável* — menos impressionante e não derrubável por uma citação de 2005.

O que responde "o que isto acrescenta?" é o inverso: **a tradução como instrumento, o mapa medido do
que não se traduz como resultado.** Um compilador que traduz o fragmento traduzível e **recusa
explicitamente** o resto, medindo sobre corpus real qual fração de cada seção do CrySL é traduzível
mecanicamente, traduzível com perda declarada, ou não monitorável sob o alfabeto escolhido. Isso tem
corpus, baseline humano publicado, categoria `Unknown` explícita e um resultado negativo defensável.

> **Mas a manchete escolhida já está publicada, e pelo próprio grupo** — verificado em 22/08/2026
> (R5). O `main.tex:1953` abre a subseção **"Inherent Limitation of RVSec"**, e `:1970-1974` traz um
> quadro destacado: *"Main reason for RVSec's false negatives: It is hard to write RV specs to check
> if a variable was initialized to a hard-coded string constant."* Dizer que o `notHardCoded` "deixa
> de ser limitação embaraçosa e vira o achado" é reapresentar um resultado que o TSE 2023 imprimiu em
> caixa. (Idem o débito de cobertura: `main.tex:1471-1480` já aponta as specs faltantes para classes
> JCA pouco usadas como trabalho futuro.)
>
> O que sobra, e é o que esta seção deve elevar: (i) as palavras `neverTypeOf`, `notHardCoded` **como
> categoria**, `IncompleteOperationError` e *monitorabilidade* não aparecem em nenhum `.tex` do paper
> — o TSE dá uma observação **qualitativa sobre um caso**, e aqui se propõe uma **medida por corpus,
> por seção do CrySL, com `Unknown` contável**, o que é diferente em espécie e não em grau; (ii) o
> achado sobre `IncompleteOperationError` é inteiramente novo e, notavelmente, **limita o próprio
> comparador M2**; e (iii) a qualidade medida do oráculo `api30` (§5.3, §9) — deleção, corrupção de
> operador e substituição de predicado —, que é falsificável, tem público próprio (os mantenedores do
> CrySL) e não depende de nenhuma escolha de engenharia deste grupo.
>
> E enquanto não houver teorema, a palavra *monitorabilidade* não deve ser usada no sentido
> técnico — a formulação honesta é "o que este substrato não monitora sob o alfabeto escolhido".

> **Decidido em 24/08/2026 (R7) — J6, decisão do pesquisador: a moldura são quatro eixos, nesta
> ordem, e a manchete do `notHardCoded` sai.** A R5 mediu que a manchete já estava publicada; faltava
> decidir o que a substitui. Substituem-na quatro:
>
> 1. **A qualidade medida do oráculo `api30`** — deleção, corrupção de operador e substituição de
>    predicado, com `−33` cláusulas líquidas em 16 regras sob a regra R1 (§5.3). É o **primeiro**
>    porque é falsificável, tem público próprio (os mantenedores do CrySL e do MetaCrySL) e não
>    depende de nenhuma escolha de engenharia deste grupo. E é ele que exige comparar contra **dois
>    oráculos** (J5): a diferença entre `api30` e `CrySL-Rules` **é** a medida.
> 2. **Equivalência de `ORDER` é estritamente mais fraca que conformidade** — com a demonstração
>    interna, medida por execução, do `KeyGeneratorSpec` (§5.1, J-02): o `ORDER` é equivalente **e** o
>    monitor acusa ordem contra um traço que a regra aceita.
> 3. **`IncompleteOperationError` não tem contraparte em `.mop`** — achado novo, limite do próprio
>    comparador M2, e desde 24/08/2026 **medido por execução** em duas specs, dois traços e dois
>    conjuntos, com controle negativo (§5.5). Deixou de ser leitura de gramática.
> 4. **A medida por corpus do que não se traduz, com `Unknown` contável** — diferente em espécie, e
>    não em grau, da observação qualitativa que o TSE 2023 publica sobre um caso.
>
> O eixo (iii) da lista anterior desta nota **é** o eixo 1 desta; o (i) é o eixo 4; o (ii) é o eixo 3.
> A novidade é o eixo 2, e a ordem — que agora começa pelo que não depende de nós.

---

## 11. Decisões de engenharia, medidas

A terceira rodada fechou por execução as escolhas que as duas primeiras deixaram em aberto. Cada
linha abaixo foi testada nesta máquina, offline salvo onde dito.

### 11.1 Escrever pelo writer da tecnologia, não por `StringBuilder`

O `javamop` tem um pretty-printer completo — `javamop.parser.ast.visitor.DumpVisitor`, 1670 linhas,
com `visit()` para `MOPSpecFile`, `JavaMOPSpec`, `EventDefinition` e `Formula`, e `getSource()`. O
construtor de `MOPSpecFile` é público, então o objeto é montável programaticamente:

```java
MOPSpecFile m = SpecExtractor.parse(f);       // ler
DumpVisitor v = new DumpVisitor();
m.accept(v, null);
String texto = v.getSource();                 // escrever
```

**Medido em 73 specs** (`jca`, `jca_android`, `generic_new`): dump 73/73, reparse 73/73, zero falhas.
A saída não é idempotente, mas a diferença é cosmética — um espaço a mais depois de `ere:` e uma
linha em branco. Nada semântico se perde.

Do lado CrySL a simetria existe e o §8 já a verificou: `CrySLFactory` constrói o `Domainmodel` e o
`CrySLSemanticSequencer` serializa para texto válido e reparseável, numa linha só.

A consequência de desenho é que **o mapeamento é objeto ↔ objeto, nunca texto**, e a validade
sintática do gerado vem por construção. É também o que decide a forma do módulo (§12): construir um
`MOPSpecFile` exige os tipos do `javamop`, logo o emissor mora do lado da tecnologia, não num núcleo
sem dependências.

**A metade que faltava, fechada em 21/08/2026 (V1).** Os 73/73 provam que o writer reimprime o que o
*parser* produziu; o gerador monta à mão. Montado à mão — pacote, imports, campo, `creation event`
com `args()` e `condition()`, `ere`, `@fail` e `@match` —, o objeto **atravessa e reparseia com a
semântica preservada**. Três coisas ficaram claras:

- **O emissor não constrói AST de AspectJ.** O construtor de `EventDefinition` recebe o pointcut como
  *string* e o parseia sozinho. Corpos de evento e handlers saem de `new JavaMOPParser(is).Block()`,
  e declarações de campo de `ClassOrInterfaceBodyDeclaration(false)`. Isso enfraquece — sem derrubar
  — o argumento de §12: o que exige os tipos do `javamop` é o `MOPSpecFile`/`EventDefinition`, não o
  pointcut.
- **Armadilha**: `ClassOrInterfaceBody(boolean)` **não** consome chaves. Passar `{ T x; }` produz um
  *initializer estático* contendo uma variável local, não um campo — e reparseia calado.
- A não-idempotência é a mesma já registrada, e continua cosmética.

### 11.2 Comentários: descartados, por impossibilidade

O `DumpVisitor` descarta comentários — `KeyGeneratorSpec.mop` sai de 96 para 64 linhas, e as 12 de
comentário viram zero. Isso importaria para reescrever specs existentes, porque o `jca_android`
carrega centenas de linhas de justificativa do gh105 dentro dos arquivos.

Recuperá-los parecia viável: em `javamop.jj:234-255` os comentários são `SPECIAL_TOKEN`, não `SKIP`,
logo o JavaCC os mantém no fluxo de tokens; e o `DumpVisitor` é extensível por desenho (`printer` é
`protected`, `RVDumpVisitor extends DumpVisitor` já é precedente). Uma subclasse de 37 linhas que
reancora por número de linha foi escrita e testada: recuperou 754 de 754 linhas de comentário e os 23
arquivos reparseavam.

**Mas no lugar errado**, e a causa é definitiva:

```
JavaMOPSpec.getBeginLine()  = 0      (a declaração está na linha 21)
event g1 … g2 … g3 … init … gk1      todos com getBeginLine() = 1
PropertyAndHandlers = 0,  Formula = 0
declarations = 2, 10, 12, 13, 15     (as reais são 26, 34, 36, 37, 39 — relativas ao bloco)
```

As ações da gramática não preenchem posição nos nós de nível MOP, e nos nós Java a posição é relativa
ao bloco embutido. Reancorar por linha não é difícil: é impossível, porque a informação não está no
AST. A alternativa seria alterar `javamop.jj` para anexar os `SPECIAL_TOKEN` aos nós e recompilar a
gramática — forkar o fork.

**Decisão: descartar comentários.** Isso não custa nada ao gerador, que os emite em vez de
preservá-los; o mesmo padrão de subclasse serve para injetar procedência (a regra e a linha da
cláusula CrySL que cada evento traduz), o que de passagem corrige o defeito dos 18 cabeçalhos que
hoje apontam para o oráculo errado.

### 11.3 Procedência: de onde sai a coluna `arquivo:linha`

O modelo canônico (§12) pede `provenance` por item, e as tabelas que ele substitui têm essa coluna
(`rule_line` em `order_alphabet_map.csv`, `mop_line` em `constraint_table.csv` — esta última já
envelhecida, apontando para comentários). É campo de **relatório**, não entrada da comparação: a
comparação é estrutural sobre o modelo, e a linha só diz ao leitor onde olhar.

Do lado CrySL a posição é recuperável da AST EMF via `NodeModelUtils`, com o mesmo desvio da fachada
descrito em §10.2. Do lado `.mop` ela **não vem do parser**, pelo que o §11.2 mostrou, e sai de uma
varredura de texto em paralelo — um índice `evento → linha`, não uma segunda leitura da spec.

### 11.4 Linguagem

O reator mira Java 21 e já declara Scala 2.11.12, usado por um módulo real
(`rv-monitor/plugins_logicrepository/ptltl`, 891 linhas, com `scala-parser-combinators`). Os fatos
medidos:

| | Scala 2.11.12 | Scala 3.3.4 LTS | Java 21 |
|---|---|---|---|
| Compila contra `javamop` (major 65) | sim | sim | — |
| Lê `record`/`sealed` do Java 21 | sim | sim | — |
| Bytecode emitido | **major 50 (Java 6)** | **major 65** | major 65 |
| ADT + pattern matching | sim | sim, com `enum` | `sealed interface` + `record` + `switch` |

O núcleo do M2 — ADT de regex, derivadas de Brzozowski, equivalência por busca no produto com
testemunha mínima — foi escrito nas duas linguagens, compilado, e produz a mesma resposta sobre um
caso real do corpus (`KeyGenerator`: regra `Gets, Inits?, gk` contra o `ere` do `.mop`, testemunha
`g1 g1 gk`). **59 linhas em Scala contra 83 em Java** — 29 % a menos, concentrados nos construtores e
na BFS; as funções recursivas empatam. A distância que justificaria uma segunda linguagem em 2015
encolheu: `sealed interface` + `record` + `switch` com padrões dão a exaustividade e a desestruturação
que eram o argumento inteiro.

**Escolha, medida nesta seção: Java 21 nos módulos de tecnologia, Scala 3.3 admissível no núcleo.**
**Superada em 22/08/2026 (R5), e marcada aqui em 22/08/2026 (R6):** o §11.5 decide **Java 21 em
tudo**, porque a sobrescrita de `scala.version` que o Scala 3 exigiria mata o `ptltl`. O que sobrevive
desta subseção é a medição — 59 linhas contra 83, os 29 % —, não a escolha. O trabalho de dirigir
API Java mutável — `getStmts()` devolvendo `null`, grafo EMF do Xtext, Guice — é hostil a idioma
funcional e concentra-se nos leitores; o núcleo é modelo algébrico, autômato e comparação, onde os
29 % valem. Se a preferência for uma linguagem só, Java 21 em tudo continua correto. O que não se
justifica é Scala 2.11: bytecode Java 6 num reator Java 21, sem `enum` e sem `Either` right-biased,
e sem vantagem alguma sobre a 3.3.

### 11.5 Resolução de dependências

`javamop` arrasta `scala-library:2.11.12` transitivamente, por `rv-monitor → ptltl`.

> **Reescrito em 22/08/2026 (R5). A saída Scala 3 desta seção não existe, e a medição que a sustentava
> mostra o contrário do que se afirmou.** Três coisas, todas por sonda executada:
>
> 1. **O *nearest-wins* nunca roda.** A raiz **gerencia** `org.scala-lang:scala-library` via
>    `dependencyManagement` (`rvsec/pom.xml:141-145`), e gerenciamento vence *nearest-wins* para
>    transitivas. Com `scala3-library_3:3.3.4` declarado direto e sem tocar na propriedade, a árvore
>    dá `scala-library:jar:2.11.12:compile (version managed from 2.13.14)` — o gerenciamento
>    **rebaixa**. O Scala 3 rodaria sobre uma `scala-library` 2.11.12 sem `ArraySeq`. A frase
>    "verificado na árvore" era falsa: a árvore mostra o oposto.
> 2. **Sobrescrever `scala.version` mata o `ptltl`.** Com `2.13.14`, o classpath inteiro do componente
>    passa a resolver `scala-library:2.13.14` (e o `scala-parser-combinators_2.11` fica), e
>    `PTLTL.mkFSM("(*) a")` por reflexão dá `NoClassDefFoundError: scala/Serializable` — classe que
>    existe no jar 2.11.12 e não existe no 2.13.14. Sob 2.11.12 a mesma chamada funciona. O `ptltl` é
>    2.11 (bytecode *major* 50, `ScalaSignature`, `$$anonfun$`).
> 3. Logo o §11.4/§11.5 estava preso entre as duas: **ou** sobrescreve e quebra o `ptltl` que ele
>    próprio proíbe excluir, **ou** não sobrescreve e o Scala 3 não resolve.
>
> **Decisão: Java 21 em tudo, e `scala.version` não é sobrescrito.** O ganho comprado com Scala no
> núcleo eram 24 linhas (§11.4); o custo é a única fonte de autômato do M2-eff.
>
> Nuance medida que vale registrar, mas que não resgata a sobrescrita: **nenhuma das 24 specs de
> `jca_android` usa `ptltl`** — **19 usam `ere` e 5 usam `fsm`, e 19 + 5 = 24**. A proibição de
> excluí-lo não é sustentada pelo corpus atual; o que a sustenta é não querer descobrir isso numa
> spec futura.
>
> **Recontado em 24/08/2026 (R7) — J-20, e a correção anterior estava certa quando foi feita.** O
> texto dizia `18 ere + 5 fsm`, com uma nota `(R6)` explicando que o `19` anterior era erro porque
> `19+5=24` num conjunto de 23. O raciocínio da R6 era válido em `8a33bc41` — e caducou quatro dias
> depois, por razão legítima: o `IvChainJunction.mop` entrou, usa `ere`, e o conjunto passou a ter 24.
> Hoje `19 + 5 = 24` é a aritmética certa, não o sintoma de erro. É o aprendizado nº 11 na sua forma
> mais limpa: **um reparo pode criar a inconsistência seguinte**, e o encadeamento tem de ser
> verificado a cada rodada.

O `dependencyManagement` do `rvsec-parent` é *property-driven* (`${guava.version}`, `${scala.version}`),
então o pom-pai do componente sobrescreve as propriedades e a herança segue junto. É por aí que o
conflito de Guava se resolve, e a análise corrigida está no §12: uma linha de `guava.version` basta, e
os dois parsers rodam na mesma JVM.

**Verificado no reator em 21/08/2026 (V10).** Montados os quatro `pom.xml` do §12 com uma classe
vazia em cada e acrescentados a `rvsec/pom.xml`, os quatro constroem. A sobrescrita funciona como
previsto: `<guava.version>33.5.0-jre</guava.version>` no pom-pai do componente dá propriedade efetiva
`33.5.0-jre`. **Corrigido em 22/08/2026 (R5):** a árvore mostra `guava:jar:33.5.0-jre:compile` num
filho só, o `-crysl`; o `-mop` **não tem Guava nenhum** no classpath resolvido, porque o `javamop` não
a puxa. Gerenciar uma versão não a coloca no classpath de quem não a pede. A exclusão do
`slf4j-simple` deixa só `org.slf4j:slf4j-api:2.0.17`. O `rvsec-crysl-mop` recebe
`scala-library:2.11.12` transitivamente por `javamop → rv-monitor → ptltl`, como previsto, e não
atrapalha — o módulo é Java 21. E o `main.basedir` resolve:
o `directory-maven-plugin` roda em `initialize` no módulo novo. Duas ressalvas medidas:
`mvn help:evaluate` devolve `null` para `main.basedir` **em qualquer módulo**, inclusive no
`rvsec-agent` que a usa — é artefato de o `help:evaluate` não rodar o ciclo de vida; e a propriedade
resolve para `/pedro/...`. **Corrigido em 22/08/2026 (R5):** `/pedro` é ponto de montagem real e a
JVM do host o abre — a ressalva anterior estava errada e sai.

---

## 12. Forma do módulo

Coerente com o reator e com P1. Duas tentações a resistir: fazer um framework de tradução com
plugins de dialeto (há duas linguagens e um caso de uso), e perseguir round-trip perfeito do texto
(o consumidor do `.crysl` é humano — e o §11.2 fechou a questão dos comentários).

A decomposição é **por tecnologia, não por direção**, e a razão é a do §11.1: construir um
`MOPSpecFile` para entregá-lo ao `DumpVisitor` exige os tipos do `javamop`, então o emissor mora ao
lado do leitor. Cada módulo de tecnologia é um adaptador de duas mãos.

```
rvsec-crysl                    (pom-pai; sobrescreve guava.version — e NÃO scala.version, §11.5)
├── rvsec-crysl-core           modelo canônico · autômatos · comparação M1–M4      [zero deps]
├── rvsec-crysl-mop            lift : SpecExtractor      → modelo                  [javamop]
│                              lower: modelo → MOPSpecFile → DumpVisitor
└── rvsec-crysl-crysl          lift : CrySLParser        → modelo                  [CrySLParser 4.0.6]
                               lower: modelo → Domainmodel → CrySLSemanticSequencer
```

Os produtos caem dessa forma sem módulo próprio:

- **comparador** (o produto do §1) = `mop.lift` + `crysl.lift` → `core.compare`
- **`crysl2mop`** (o gerador do §10) = `crysl.lift` → `core` → `mop.lower`
- **`mop2crysl`** = `mop.lift` → `core` → `crysl.lower` — **fora de escopo**

> **Decidido em 24/08/2026 (R7) — J1 e J-06, decisão do pesquisador: uma JVM, três módulos Maven.**
> A alternativa era costurar três processos por JSON, e ela caiu por três razões medidas: a
> justificativa antiga era falsa (o `javamop` não puxa Guava nem Soot — ver a subseção seguinte); uma
> linha de `<guava.version>33.5.0-jre</guava.version>` no pom-pai põe os dois parsers no mesmo
> processo, verificado por sonda; e um dos três custos que a costura cobrava — *"um erro de leitura
> vira código de saída em vez de item `Unknown` tipado"* — **contradiz frontalmente** o primeiro dos
> dois pontos não-negociáveis desta mesma seção.
>
> **Caem do documento, com a decisão:** o parser próprio de `ere`/`fsm` no núcleo, o contrato de
> numeração de estados do DFA no fio, e a política de erro dentro do *lift*. **O JSON continua sendo
> a saída do modelo canônico, e deixa de ser candidato a formato de intercâmbio.**

> **Decidido em 24/08/2026 (R7) — J-14: `crysl.lower` fica como trabalho futuro, com razão escrita.**
> Ele não tem consumidor conhecido e o §11.1 orça ~400 linhas de *pretty-printer* para ele — o projeto
> CrySL não tem formatter. Com J1 decidido, o módulo `rvsec-crysl-crysl` existe de qualquer forma
> pelo *lift*, então cortá-lo não custa um módulo; custa uma seta na figura do §1, que passa a
> tracejada. O `mop.lower`, ao contrário, **fica e ganha estimativa**: é ele que serve o produto forte
> (`crysl2mop`, §10) e é ele que sustenta o portão de round-trip desta seção. Cortar a direção sem
> consumidor e orçar a que tem é a troca certa.

| Item | Escolha |
|---|---|
| Local | `rvsec/rvsec-crysl/` — irmão de `rvsec-mop-extractor` |
| Coordenadas | `br.unb.cic:rvsec-crysl` (pai) e os três filhos |
| Entrada MOP | `javamop.parser.SpecExtractor` — **215/215** verificados em `5fbe8173` (era `214/214`; recontado em 24/08/2026, R7, J-20), com `MOPNameSpace.init()` **por arquivo** (J-13; impacto medido no corpus: nulo) |
| Saída MOP | `DumpVisitor` — 73/73 reparseiam (§11.1) |
| Entrada CrySL | `crysl.CrySLParser:4.0.6` + normalização léxica de **5** substituições (§8) — a quinta é `length(…)`→`length[…]`, e sem ela o corpus para em 27 |
| Saída CrySL | `CrySLSemanticSequencer` + formatador próprio (o projeto CrySL não tem formatter) |
| Classpath | JDK do host para *ler*; `android.jar` da API 30 como **conferidor a posteriori** de cada assinatura resolvida. Fixar o classpath do parser é impossível (§8) |
| Autômato MOP | preferir o **monitor gerado** (já minimizado); `ere`/`fsm` como fallback obrigatório |
| Autômato CrySL | `StateMachineGraph`, com determinização própria (§10.2) — obrigatória por correção, *no-op* nas 30 regras de hoje |
| Oráculos | **dois**: `api30` e `CrySL-Rules` (J5). A diferença entre os dois **é** a medida do teto do oráculo, classificada nos três modos do §5.3 — deleção, corrupção de operador, substituição de predicado |
| `crysl.lower` | **fora de escopo** (J-14): entrega-se o *lift* do lado CrySL e o `mop.lower` do lado MOP. Ver a nota abaixo |
| Leitura CrySL | um `CrySLModelReader` **por regra**: o escopo de `OBJECTS` vaza entre regras no mesmo leitor (§9) |
| Parâmetro múltiplo | fora de escopo, com **recusa tipada** `Unknown{MultiSlicedOrder, params:[…]}` — custo medido **0 de 24** em `jca_android` e 0 de 23 em `jca`; 93 de 118 no `generic` (§12) |
| Linguagem | **Java 21 em tudo**; `scala.version` não é sobrescrito (§11.5). Corrigido em 22/08/2026 (R6): esta célula dizia "Scala 3.3 admissível no núcleo", decisão que o §11.5 derrubou por sonda |
| Saída | JSON + CSV nos esquemas de `data/jca_android/*.csv`; Markdown como `evidence/*.md` |
| Exclusões | `slf4j-simple`. **Não** excluir o `ptltl` (§11.5) |
| Molde | `rvsec-mop-extractor` pela *forma* (pom, CLI, facade, visitor, writer) — não pelo código |

### O JSON como saída — e a costura entre processos como escolha, não como consequência

**Corrigido em 22/08/2026 (R5); a justificativa anterior estava factualmente errada.** O texto dizia
que `javamop` "vive num reator que pina Guava 19.0 por causa do Soot". Medido com `mvn -o
dependency:tree`: **o `javamop` não puxa Guava e não puxa Soot** — a árvore inteira é `rv-monitor`
(+ plugins de lógica), AspectJ, `commons-lang3`, `commons-io`, `jcommander` e `jackson-databind`. E o
Soot 4.7.1 não declara Guava: ela chega por `heros:1.2.4 → guava:999.0.0-HEAD-jre-SNAPSHOT`, um
*placeholder*, e o único módulo do reator que usa Soot (`rvsec-gator`) já sobrescreve para 27.1-jre.
Nada liga o valor `19.0` ao Soot.

**O conflito existe, por outro mecanismo.** O `dependencyManagement` da **raiz** (`rvsec/pom.xml:41`
e `:158-160`) impõe Guava 19.0 a qualquer descendente, inclusive a um que só dependa do
`CrySLParser` — a árvore mostra `guava:jar:19.0:compile (version managed from 33.5.0-jre)`. Com o pin
herdado, uma sonda compila limpa e morre em runtime, exatamente como o texto previa:

```
javac limpo; parse do .mop OK sob Guava 19
new CrySLModelReader() → NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()   (Guice 7 → Guava ≥31)
```

**Mas uma linha o resolve, e os dois parsers dividem JVM.** Acrescentando
`<guava.version>33.5.0-jre</guava.version>` ao `<properties>` do pom-pai do componente, um módulo
**único** roda os dois em sequência no mesmo processo:

```
== Guava carregado: guava-33.5.0-jre.jar
== parse .mop  : spec=MessageDigestSpec eventos=8 props=1
== ler regra   : rule=java.security.MessageDigest eventos=9 objects=10 · ORDER=9 transições
OK: os dois parsers rodaram na mesma JVM.   EXIT=0
```

O `javamop` é **indiferente** ao Guava — parseou sob 19.0 e sob 33.5.0-jre — porque não o toca. O V6
mostrou que três processos **funcionam**; nunca rodou o controle de que um processo falha, e ele não
falha.

Logo: o JSON continua sendo a **saída** do modelo canônico, e isso não está em questão. Usá-lo também
como **formato de intercâmbio**, com três processos, passa a ser uma escolha a justificar por
inspecionabilidade e isolamento — não uma consequência de conflito de dependência. Se a escolha for
mantida, o custo a declarar é concreto: o núcleo passa a precisar do seu próprio parser de `ere`/`fsm`
(o *lift* do V6 grava o `ORDER` como `{formalism, text}`), a numeração de estados do DFA no fio não
está fixada por nada, e um erro de leitura dentro do *lift* vira código de saída em vez de item
`Unknown` tipado.

Correção correlata ao V10: a sobrescrita de `guava.version` funciona, mas o efeito aparece em **um**
filho, o `-crysl`. O `-mop` não tem Guava nenhum no classpath resolvido — nem 19.0 nem 33.5.0.

### O modelo canônico

```
SpecModel {
  version     : { commit, data, corpus }     // R5 — sem isto duas execuções não são comparáveis
  type        : FQN                          // SPEC
  objects     : Set<ObjectDecl>
  events      : List<Event{ label, pointcut, Set<Signature>, guard: Constraint?, declIndex }>
                                             // ORDENADA: a ordem de declaração é a ordem de despacho
  order       : autômato simbólico sobre Signature, transições com guarda opcional
                                             // o DFA mínimo sobre Labels é vista calculada, não a forma armazenada
  constraints : List<Constraint>             // lista, não conjunto: cláusulas repetidas têm procedências distintas
                                             // + Unknown{textoCru, sítio}
  ensures / requires / negates : List<PredicateRef>
  forbidden   : Set<Signature>
  provenance  : arquivo:linha por item       // ver §11.3 — carimbado, não parseado
}

Witness {                                    // R7 — J-08: nenhuma testemunha sai sem estatuto
  word    : List<Signature>
  status  : ABSTRACT | CONCRETE              // ABSTRACT = palavra sobre o alfabeto
                                             // CONCRETE = traço executado, com o arnês que o executou
  normalizations : List<N>                   // R7 — J-01: as normalizações aplicadas, impressas
}
```

> **Acrescentado em 24/08/2026 (R7) — J-08, e a regra ganha dente.** A distinção
> `ABSTRACT`/`CONCRETE` já era enunciada no §5.2 e aplicada em dois lugares, mas não era campo do
> modelo — logo não era obrigatória, e "testemunha" aparece dezoito vezes neste documento. Passa a
> ser campo, e com uma proibição explícita: **uma testemunha `ABSTRACT` não pode ser publicada com a
> palavra "falso positivo" ao lado.** Palavra aceita pelo autômato não é traço executável — o §5.2 tem
> o caso medido (`g1 i1 wkb1 f2` é válida no autômato e impossível em Java, porque a máquina de modos
> do `javax.crypto.Cipher` não é modelada nem pelo `.mop` nem pela regra).

> **Reescrito em 22/08/2026 (R5).** A forma anterior — `events : Map<Label, Set<Signature>>` e
> `order : DFA mínimo sobre Labels` — pressupõe que **cada chamada observada contribui com exatamente
> uma letra**. No corpus, não contribui: são 10 pares de eventos sobrepostos no `jca_android` e 26 no
> `jca`, e uma chamada `doFinal()` nua emite a palavra `f1 f2`, com as duas letras acusando (§5.2).
> Qual letra sai também pode depender de guarda sobre estado do monitor, e a guarda mora a montante
> das tabelas de transição (§5.1) — nenhum mapa léxico exprime isso.
>
> Formalmente o objeto a comparar é `h⁻¹(L)`, onde `h : Σ_sig* → Label*` leva cada assinatura à
> **concatenação, em ordem de declaração, de todo rótulo cujo pointcut a casa**. Morfismo inverso
> preserva regularidade, então a comparação continua decidível e continua barata; o que faltava era
> onde guardar o `h`. Com esta forma, **N4 deixa de ser normalização aplicada a um modelo que já
> perdeu a informação e vira passo de construção** — e a alternativa honesta, onde a guarda não for
> estática, é `Unknown{OverlappingDispatch, labels:[…]}`.
>
> Duas mudanças menores pela mesma razão: `Set` vira `List` nas cláusulas e nos predicados, porque
> cláusulas idênticas em sítios diferentes têm procedências diferentes e um conjunto as colapsa; e o
> modelo ganha `version`, porque os números deste documento estão presos a um commit (§13) e duas
> execuções do componente com um dia de distância não são comparáveis sem ele.

### A taxonomia `Unknown`, fechada e enumerada

**Acrescentada em 24/08/2026 (R7) — J-09.** Até esta rodada o documento nomeava **três** tags em
lugares diferentes — `textoCru/sítio`, `OverlappingDispatch` e `MultiSlicedOrder` — e usava a
categoria **sem tag** em outros quatro; e o `OverlappingDispatch` perdia o campo `labels` entre um
sítio e outro. Uma categoria de recusa que não tem esquema fixo não é contável, e o §6 depende
inteiramente de ela ser contável. A lista é **fechada**: o componente não emite tag que não esteja
aqui, e acrescentar uma é mudança de contrato.

| Tag | Quando | Campos | De onde veio |
|---|---|---|---|
| `UnrecognizedConstraint` | a `condition`/`action` não casa idioma A, B, C nem D | `{textoCru, sítio}` | §5.3, §6 — é a que separa *"não consegui ler"* de *"não existe"* |
| `OverlappingDispatch` | dois ou mais rótulos casam a mesma assinatura e a guarda **não** é estática | `{labels: […], signature, sítio}` | §5.2 (N4), J2. O campo `labels` é obrigatório: sem ele a recusa não diz quantas letras a chamada emite |
| `MultiSlicedOrder` | spec de *k*>1 parâmetros cuja `ORDER` intercala eventos sobre objetos diferentes | `{params: […], sítio}` | a fronteira do parâmetro único, abaixo |
| `UnresolvedSignature` | a assinatura resolvida pelo parser não existe no `android.jar` da API 30 | `{signature, classe, modo: CLASSE-AUSENTE\|METODO-AUSENTE, sítio}` | §8 — a conferência a posteriori; **consumida por M0.3** (§5.5) |
| `UntranslatableConstraint` | a cláusula é sobre o tipo estático da origem ou sobre símbolos do `ORDER`, não sobre valores de runtime | `{cláusula, família, sítio}` | §10.5 — `neverTypeOf`, `notHardCoded`, `noCallTo`, `callTo` |

As duas últimas são exigência desta rodada: `UnresolvedSignature` porque M0 passou a consumir a
conferência contra o `android.jar` (J3), e `UntranslatableConstraint` porque os casos do §10.5
saíam como comentário, e comentário não entra em métrica.

### Os dois vocabulários de M3 e os dois de M4

**Acrescentado em 24/08/2026 (R7) — J-10.** Esta seção promete que a saída do componente
*"substitui as tabelas manuais"*, e o documento nunca mapeou o seu vocabulário no delas. Sem o mapa,
a promessa não é verificável. Medido em `5fbe8173`:

| Métrica | Vocabulário deste documento | Vocabulário do CSV | Como reconciliam |
|---|---|---|---|
| **M3** | *idioma*: `A` / `B` / `C` / `D` / `Ausente` (§5.3) | *veredito*, em `constraint_table.csv`: `IGUAL` 8 · `MOP-MAIS-PERMISSIVO` 9 · `MOP-MAIS-RESTRITIVO` 3 · `DIVERGENTE` 5 · `CRYSL-NAO-IMPLEMENTADO` 30 · `MOP-SEM-BASE` 4 | `59 − 4 = 55` cláusulas; `55 − 30 = 25` implementadas; **25/55 = 45,5 %** — reproduz exatamente o número do §13 no HEAD |
| **M4** | *fidelidade*: `FIEL` / `PROJETADO` / `CONFLADO` / `AUSENTE` / `SEM-BASE` (§5.4) | `predicate_graph.csv`, **duas** colunas: `disposition` (57 vazias · 12 `omission` · 1 `propagation`) e `verdict` (`read:body` 33 · `write:acceptance` 26 · `read-absent:body` 5 · `write:body` 5 · `negate:body` 1), sobre 70 linhas | não há bijeção: o CSV descreve **o sítio**, o §5.4 descreve **a cláusula**. A saída emite **as duas colunas**, lado a lado |

A linha de M4 é a que importa: as duas classificações não são a mesma coisa vista de dois ângulos —
são dois objetos diferentes. Emitir só uma delas e chamá-la de substituta da outra seria trocar uma
tabela manual por uma tabela automática que mede outra coisa.

Dois pontos não-negociáveis:

- **`Unknown` explícito.** Sem ele o componente mente por omissão e o score infla. Cada constraint
  não reconhecida vira item do relatório, com a taxa de reconhecimento por seção. É a diferença
  entre instrumento e brinquedo — ver §6. Na direção da geração ele é ainda mais necessário: os 8
  casos não-emitíveis do §10.5 têm de sair como registro tipado, não como comentário no `.mop`.
- **`order` como autômato desde a construção.** `a,(b|c)` e `(a,b)|(a,c)` são a mesma linguagem;
  comparar ASTs de regex acusaria divergência inexistente. Autômato mínimo é mais simples *e* mais
  correto.

A saída deve **substituir** as tabelas manuais, não criar uma ilha paralela — é o que faz o
componente se encaixar no fluxo existente em vez de virar mais um script.

Nome pelo fim, não pelo meio: *conformidade*, não *tradutor*. Quem lê o nome não fica tentado a pedir
um compilador genérico depois.

### A fronteira do parâmetro único

JavaMOP fatia sobre uma **tupla** de parâmetros; CrySL nomeia **um** tipo em `SPEC` e não tem
autômato conjunto sobre um par de objetos. A resposta de CrySL para relação entre dois objetos é
**predicado** (`ENSURES generatedKey[key, algName]`), não ordem conjunta — é a mesma aridade-2 do
§5.4 vista pelo outro lado.

| Conjunto | specs | com mais de um parâmetro |
|---|---:|---|
| `jca` | 23 | **0** — buckets `{0:2, 1:21}` |
| `jca_android` | **24** | **0** — buckets `{0:2, 1:22}` |
| `generic_new` | 27 | 4 |
| `generic` | 118 | **93** — 39 com dois, 28 com três, 18 com quatro, 7 com cinco, 1 com seis |

**A regra de contagem é a AST, e precisa estar escrita** — acrescentado em 22/08/2026 (R5). Os
números acima vêm de `spec.getParameters().size()` depois do parse, não do texto do cabeçalho. Contar
o cabeçalho dá **97**, com outra distribuição (`{2:40, 3:30, 4:17, 5:6, 6:4}`). A diferença não é
estilo: `MOPParameters.add` descarta parâmetro cujo **nome** já existe, sem diagnóstico, e 11 specs do
`generic` perdem declarações por isso (§9). Para o comparador vale a AST — é ela que descreve o
monitor que roda —, mas a divergência entre as duas contagens é ela própria um sinal a reportar.

Na direção **`.crysl` → `.mop`** o problema não existe: `SPEC` nomeia um tipo, logo a spec gerada tem
sempre um parâmetro. É até propriedade boa — é por construção que o gerador não comete o defeito das
**5 de 22** specs com fatiamento quebrado (§9; era `7 de 21` — recontado em 24/08/2026, R7, J-20).

No **comparador** e na direção `.mop` → `.crysl`, uma spec de *k*>1 parâmetros não tem imagem em
CrySL quando a `ORDER` de fato intercala eventos sobre objetos diferentes. A saída certa é **recusa
tipada** — `Unknown{MultiSlicedOrder, params:[…]}` —, nunca achatamento silencioso, pela mesma razão
do §6: sem a categoria explícita, "não sei traduzir" e "traduzi" saem pela mesma porta.

**Custo da restrição no corpus do componente: `0 de 24` em `5fbe8173`, medido pela AST.**

> **A previsão desta seção foi falsificada — reparado em 24/08/2026 (R7), §3.3 da adjudicação.** O
> texto anterior dizia: *"a tarefa **5.1 do gh105, aberta**, cria `IvChainJunction.mop` … é a primeira
> spec multi-parâmetro do `jca_android` **por definição de mecanismo** … a fronteira vai a ≥1/24
> durante a janela em que o componente seria construído"*, e citava a delta-spec da própria change
> (*"one multi-parameter JavaMOP specification per chain"*).
>
> **A tarefa 5.1 está concluída, e o arquivo que ela entregou declara `IvChainJunctionSpec(Cipher c)`
> — um parâmetro** (`IvChainJunction.mop:62`). A junção não liga uma tupla: lê o `PredicateStore`
> chaveado por identidade, e o cabeçalho do arquivo diz exatamente isso (`:20-40`). Medido pela AST,
> que é a regra que esta própria seção declara: `jca_android files=24 ok=24 multiparam=0
> buckets={0=2, 1=22}`.
>
> **Logo a fronteira custa `0 de 24` no HEAD, e a data de validade que esta seção marcava para si
> mesma não venceu.** Isto não é achado contra o gh105: a change entregou a junção por um mecanismo
> **mais barato** do que a delta-spec previa, e é a delta-spec que descreve mal o que foi construído.
> O que sobrevive do argumento — e é o que deve entrar na proposta — é o dado do `generic`: **93 de
> 118**, medido e não contestado. A dívida existe, e ela mora lá.

### O portão de round-trip

O gerador precisa validar o que emite, e a máquina para isso é a mesma do comparador: construir o
autômato do `.mop` gerado, compará-lo por busca no produto contra o autômato da regra, e falhar a
geração se as linguagens diferirem.

> **Corrigido em 22/08/2026 (R5): são dois portões com estatutos diferentes, e o de equivalência é
> cego às duas falhas nomeadas abaixo.** Um portão de equivalência de linguagens compara a saída do
> gerador com a regra **através da mesma camada de normalização** que o comparador usa, logo não pega
> defeito que more dentro do próprio quociente. E as duas falhas listadas a seguir não precisam de
> busca no produto e não são alcançáveis por ela: "evento declarado e ausente do `ere`" é local, e
> pode inclusive ser apagado pela ε-normalização do gêmeo negado; "`@match` sem `@fail`" é sobre
> **handlers**, e duas specs que diferem só na presença do handler têm linguagem idêntica. O portão
> certo é (1) um **checador não-normalizado sobre a AST gerada** — ids únicos, alfabeto da fórmula ⊆
> ids, todo evento declarado alcançável, todo `@match` com `@fail`, todo pointcut resolvendo contra o
> `android.jar` — que é barato, não-circular e pega as duas; e (2) a busca no produto mantida como
> **evidência**, com o conjunto de normalizações aplicadas impresso ao lado de cada veredito, porque
> uma spec que só passa sob N3+N4 está dizendo alguma coisa.
>
> **Precisado em 24/08/2026 (R7) — J3 e J-01.** O checador não-normalizado de (1) é **a mesma peça**
> que M0 (§5.5): deixa de ser portão interno do gerador e passa a ser métrica publicada, com a lista
> das quatro checagens idêntica nos dois usos. E o "conjunto de normalizações aplicadas" de (2) deixa
> de ser inferido: o apagamento vem da coluna `disposition` do `order_alphabet_map.csv`, declarada com
> razão escrita, e o que o portão faz é **conferi-la**, não decidi-la. Com J-14, o portão apoia-se no
> `mop.lower` — que é o lado que tem consumidor.

Sem portão nenhum, dois modos de falha passam calados:

- **Evento declarado e ausente do `ere`** ganha uma linha de transição toda-`fail`, e acusa todo
  monitor vivo da spec quando dispara. Já aconteceu e está registrado em `PBEKeySpecSpec.mop:26-32`.
- **`@match` sem `@fail`** produz uma spec que compila, roda e nunca acusa nada. `SecretKeySpec.mop`
  e `RandomStringPassword.mop` são exatamente isso hoje.

Isso também é o que resolve a decisão que a segunda rodada deixou aberta — Java ou consolidação do
Python. O comparador e o gerador partilham autômato, modelo e portão; mantê-los em duas linguagens
duplicaria a peça mais delicada de ambos. O domicílio único é o `core`.

### O que morre

**Acrescentada em 24/08/2026 (R7) — J-05, decisão do pesquisador: substituir o ad hoc, preservar os
portões de CI.** Esta seção faltava, e a sua ausência era a única lacuna que a proposta não conseguia
sequer **registrar como aberta**: P3 manda que código superado seja deletado por inteiro, com
*backup* antes, e sem essa lista não há o que deletar nem como saber quando.

Censo em `5fbe8173`, sob a regra declarada no §3 — *comparador* = arquivo Python que parseia um
`ORDER` ou um `ere`/`fsm` e decide sobre ele; *leitor* = arquivo Python que abre um `.crysl`/`.cryptsl`:

| Categoria | n | Linhas | Disposição |
|---|---:|---:|---|
| comparadores de `ORDER` em `audit/20260808_*` — `alfa_automata_check` ×3, `alfa_language_check` ×2, `juiz_walk_batchB` | 6 | 1.530 | → `backup/`, **nesta change**. São fotografia de uma auditoria encerrada |
| leitores de CrySL sob `audit/` (inclui `batchD/alfa_language_check.py`, que é também comparador) | 7 | 2.377 | → `backup/`, **nesta change** |
| `scripts/gh105_order_gate.py` | 1 | 1.171 | **sobrevive** até o componente reproduzir os seus vereditos; a troca é change própria |
| `scripts/gh10{1,4}_*.py` que abrem `.cryptsl` — `gh101_conformance_check`, `gh104_baseline`, `gh104_gates` | 3 | 4.340 | **sobrevive**: são portões vivos do gh104/gh105 |
| `tests/parity/test_gh105_predicate_gates.py` | 1 | 2.507 | **sobrevive**: portão de pytest vivo, e o verde dele é o critério de corte |

Totais: **7 comparadores de `ORDER`** (2.701 linhas, **7 `md5` distintos** — nenhum é cópia de outro)
e **11 leitores de CrySL** (9.224 linhas). Um arquivo conta nos dois.

**O critério de corte, escrito:** *o ad hoc morre quando o componente **reproduz o seu veredito**, não
quando ele compila.* É a diferença entre substituir um instrumento e trocá-lo por outro que ninguém
calibrou — e é por isso que a deleção se parte em duas. A categoria `backup/` sai **nesta** change,
porque nada de CI depende dela. Os portões de CI saem numa change de limpeza posterior, depois de o
componente passar pela calibração contra os números que eles produzem.

---

## 13. Confiança e o que ficou verificado

Dos cinco riscos nomeados na primeira rodada, quatro caíram e um se confirmou.

| Risco da 1ª rodada | Situação | Evidência |
|---|---|---|
| Normalização de ORDER validada em n=1 | RESOLVIDO, com correção | 5 specs decididas por autômato, refeitas sobre o autômato do parser. Generaliza em 3; o exemplo original estava errado e foi corrigido. |
| Polaridade pode inverter em silêncio | NÃO SE MATERIALIZA | 0 inversões em 23. Substituído por um risco maior e nomeável: **sob a regra R-abs, 18 das 24 specs de `jca_android` e 15 das 23 de `jca` absorvem uso incorreto** em `5fbe8173` (era "12 de 23", número sem regra de contagem — recontado em 24/08/2026, R7, J-12). |
| Taxa de reconhecimento de constraints desconhecida | MEDIDO — **45,5 % implementadas**; teto do instrumento **25,5 %** (§6, R6) | Censo de 55 cláusulas conferido 55/55 contra o gabarito manual. Ressalva nova: o denominador do `api30` já é uma perda (§5.3). |
| M4 tem teto desconhecido | MEDIDO — teto de substrato **74,0 % em `d64f3a40`**; a medição daquele commit é 35,6 % (§5.4) | 92 cláusulas normativas censadas; casamento 85/85 com o gabarito **em `d64f3a40`** — hoje o `predicate_graph.csv` tem 45 linhas de dados. Corrigido em 22/08/2026 (R6): a célula dava o teto como se fosse a medição, e o advérbio contradizia o carimbo do próprio §13. |
| Alvo em movimento (gh105) | CONFIRMADO | Specs alteradas durante esta própria análise; monitor gerado já defasado numa delas. |

A terceira rodada acrescentou um risco próprio, da direção da geração: os números por camada do §10
vinham de leitura de corpus e de execução do *parser*, nunca de um gerador em funcionamento. **A
quarta rodada fechou esse risco para três specs** — um gerador foi escrito, gerou, e o gerado passou
pelas quatro métricas e pelo pipeline até compilar (§10, V2/V7). Para o conjunto todo os números
continuam sendo previsão.

### As dez validações da quarta rodada

Executadas em 21/08/2026. Registro completo em
`docs/20260821_validacoes_conformidade_mop_crysl.md`; arnês reproduzível em
`docs/handoff/20260821_arnes_validacoes/`.

| | O que testava | Resultado |
|---|---|---|
| V1 | `MOPSpecFile` montado à mão pelo `DumpVisitor` | passa (§11.1) |
| V2 | gerar uma spec inteira e medir contra o gabarito | passa — M1 5/5, M2 3/3, M4 5/5, M3 2/2 (§10) |
| V3 | `CrySLParser` com o `android.jar` da API 30 | **a via é impossível**; impacto medido zero; desenho alternativo em §8 e §12 |
| V4 | determinizar o `StateMachineGraph`; refazer os vereditos | vereditos confirmados; **30/30** já determinísticas sob leitor novo por regra (§5.2, R5) |
| V5 | preservar os nomes de agregado | passa, com procedência de brinde (§10.2) |
| V6 | a costura JSON com os dois classpaths reais | passa, **sem o controle** — R5 mostrou que um processo também funciona, e que o núcleo precisa do seu próprio parser de `ere` (§12) |
| V7 | o `.mop` gerado no pipeline inteiro | passa, e o monitor compila (§9, §10) |
| V8 | a semântica de fatiamento paramétrico | N1 confirmado em traço **nas specs sonda**; §4.1 corrigido. R5: não generaliza — 5 das 23 compilam para monitor global (§5.2) |
| V9 | dois achados de subagente | ambos confirmados, ambos com alcance menor (§9) |
| V10 | o módulo mínimo compila no reator | passa — Guava (num filho só), `slf4j-simple`, `main.basedir`. R5 derrubou a saída Scala 3 (§11.5) |

### O que ainda não foi verificado

A lista tinha **nove** itens: três da quarta rodada e seis acrescentados pela quinta. **Corrigido em
22/08/2026 (R6):** esta frase dizia "encolheu a três itens, e nenhum bloqueia a change", e não foi
atualizada quando a lista triplicou. A segunda metade também não valia para todos: as **129 linhas**
eram declaradas pelo próprio §8 como pendência a fechar *antes* de a proposta ser aberta.

**Atualizado em 24/08/2026 (R7): a lista tem sete itens, e nenhum bloqueia a abertura da change.** Os
dois que bloqueavam foram fechados nesta rodada — as **129 linhas** (hoje **141**, §8) e o `12 de 23`
do §2 (hoje o par 18/24 e 15/23, J-12), e os dois estão riscados abaixo. Os sete que restam são
trabalho do componente ou pendência de medição sobre APK.

- **Nenhum monitor do corpus foi executado sobre um traço de APK real.** Corrigido em 22/08/2026
  (R5): a redação anterior dizia "sobre um traço real", e isso é falso — o gh104 gerou monitores **das
  specs do corpus** (`rv-monitor-generator generate --specs-dir …/jca` e `…/jca_android`) e replicou
  traços sobre eles; o auto-teste sozinho replica 63 traços sobre o `jca`, e há 94 traços versionados
  e 162 arquivos de evidência por spec (§3). O que continua verdadeiro é o escopo restrito de V8 (que
  usou specs sonda) e o comportamento das 23 specs **sobre APK**, que segue não medido. **Carimbado
  em 24/08/2026 (R7) — J-20:** o "23" descreve a pendência tal como foi enunciada, sobre o conjunto de
  então; o `jca_android` de `5fbe8173` tem **24**, e a pendência sobre APK continua aberta para as 24.
  Recebe carimbo em vez de troca porque o que envelheceu foi o conjunto, não a afirmação.
- **Posicionamento no autômato para as 19 cláusulas com `after`** foi conferido em 3 specs,
  classificado por polaridade e aridade nas outras 16. Se M4 exigir também a posição, o número de
  fiéis cai. V9 fechou o risco vizinho — nenhuma das 19 cai no conjunto vazio do
  `getStatesForMethods` — mas não este.
- **`SSLContextSpec` e `TrustManagerFactorySpec`**, as outras duas falhas do gate, não foram
  analisadas — provavelmente têm os mesmos artefatos.

**Acrescentado em 22/08/2026 (R5), depois da revisão externa e da verificação:**

- **Os números de M4 do §5.4/§7/§9 estão medidos em `d64f3a40`, não no `HEAD` de publicação.** A
  assinatura "64 sítios de `ExecutionContext`, 21 de `PredicateStore`, 5 de 23 arquivos migrados"
  ocorre em exatamente um dos 25 commits que tocam o diretório; então era **47 / 26 / 7** (45 / 28 / 8
  na árvore de trabalho). **Remedido em 22/08/2026 (R6): `28 / 35 / 12` em `f188c55b` e `0 / 45 / 19`
  em `8a33bc41`** — a tarefa 4.14 migrou os sete últimos arquivos, e o `jca_android` deixou de ter
  dois substratos. **Remedido de novo em 24/08/2026 (R7): `0 / 70 / 21` em `5fbe8173`**, sobre 24
  arquivos — cinco assinaturas em quatro dias, e é exatamente por isso que J-15 proíbe escalar de M4
  sem commit ao lado. O `predicate_graph.csv` confirma por segunda via: 85 linhas de dados em
  `d64f3a40`, 73 em `c12f4689`, 63 em `f188c55b`, 45 em `8a33bc41`, **70** em `5fbe8173` — encolheu
  com a migração e voltou a crescer com a fiação. O §7 registrava 41 `condition(` e já está corrigido lá para 36 — e o valor de `d64f3a40` é
  **40**, não 41 (recontado em 22/08/2026, R6, pelos dois métodos de contagem). A linha de teto `74,0 % / 58,7 %` foi calculada
  sobre um estado de substrato que já não vale. **Toda tabela precisa de carimbo de commit antes de
  virar proposta**, e o `SpecModel` ganhou campo de versão por isso (§12).
- ~~**O gh105 move três "custos zero" durante a janela do componente.**~~ **FECHADO em 24/08/2026
  (R7): as quatro tarefas correram, e o gh105 está em 72 de 74.** Era 36 de 74 (R5) e 39 de 74 (R6,
  `8a33bc41`); as duas que restam — 8.8 e 8.9 — estão bloqueadas no arquivamento do gh104, não em
  trabalho de spec. Uma a uma, com o que de fato aconteceu:
  - a **5.1** criaria "a primeira spec multi-parâmetro do `jca_android`" — **criou uma spec de um
    parâmetro**, e a previsão foi falsificada; a fronteira continua custando `0 de 24` (§12);
  - a **6.6** apagaria a sobreposição `f1`/`f2` — **apagou**, e a testemunha do §5.2 teve de ser
    trocada por `IvChainJunction` `use`/`useRandomSpec`, nascida no mesmo conjunto;
  - a **5.3** criaria as duas primeiras leituras negadas — **criou cinco sítios** de `validateAbsent`
    (9 ocorrências do token, quatro delas em comentário);
  - a **6.4** apagaria os `remove()` em `@fail` — **apagou**: 8 em `d64f3a40`, 7 em `c12f4689`, zero
    de `8a33bc41` em diante, absorvidos pela 4.14.
- **Acrescentado em 22/08/2026 (R6): a 4.15 e a 6.1 também correm nesta janela.** A **4.15** leva a
  zero os `set/unsetObjectAsInAcceptingState` do `jca_android` — eram 17 em `c12f4689`, 11 em
  `f188c55b` e **zero** em `8a33bc41` —, o que retira do `jca_android` um dos idiomas que o §7 lista
  para o extrator reconhecer; ele passa a existir só no `jca` congelado. A metade `KeyPairSpec.mop:38`
  da **6.1** já está feita (pela tarefa 4.13): o `jca_android` grava `GENERATED_PRIVATE_KEY` em `:71`,
  e a linha correspondente do §9 precisa de revisão.
- ~~**`12 de 23 specs absorvem uso incorreto`** (§2) não foi remedido nesta rodada; uma das revisões
  externas conta 16. Fica em aberto.~~ **FECHADO em 24/08/2026 (R7) — J-12.** Rederivado em cinco
  commits sob a regra R-abs, e o resultado é o par **18 de 24** (`jca_android`) e **15 de 23** (`jca`)
  em `5fbe8173`. Nenhuma das quatro regras testadas reproduz o 12; o número publicado não tinha regra
  ao lado. Ver §2.
- **`152/167` × `141`**: o §10 e o §8 discordam entre si, e a resolução dos 167 contra o `android.jar`
  não foi refeita. A aritmética do §10 foi auditada (§10); a resolução, não. **Atualizado em
  24/08/2026 (R7):** a ponta do §8 passou de `155` a **141** sob leitor novo por regra, com a regra de
  contagem declarada; a divergência com o `152` continua aberta e é trabalho do componente.
- **`28 das 55 cláusulas que mudam de veredito conforme a relação de igualdade`** (§10.3) não é
  derivável de nenhuma regra de contagem que esta rodada tenha conseguido reconstruir.
- ~~**As 129 linhas de assinatura idênticas com e sem `android.jar`** (§8) foram medidas em modo lote
  e precisam de remedição sob leitor novo por regra.~~ **FECHADO em 24/08/2026 (R7).** Remedido: são
  **141** linhas sob leitor novo por regra, e o `diff` entre as passagens com e sem `android.jar`
  continua **zero**. A conferência a posteriori foi refeita junto — 141 eventos, 119 exata, 17
  aridade, 3 classe-ausente, 2 limitação do conferidor —, e a passagem com leitor partilhado reproduz
  dígito a dígito o `155: 131+19+2+3` antes publicado, o que calibra a cadeia. Era a **única**
  pendência que este documento declarava como pré-requisito da abertura da change. Registro:
  `docs/20260824_medicoes_pre_change_conformidade.md` §1.

**Posição honesta:** o desenho está certo, a viabilidade está demonstrada por execução nas duas
direções, e as métricas quantificadas vêm com denominadores que precisam ser declarados — agora são
três tetos, não dois. **Nenhuma validação da quarta rodada derrubou uma conclusão do documento** —
uma derrubou uma via, e
o substituto está medido. A direção da geração deixou de ser "peça a peça, produto nenhum
construído": há três specs geradas que compilam.

### O que a proposta tem de declarar, além do que já estava previsto

1. **O teto do oráculo** (§6), além dos dois anteriores — e com os **três modos** do §5.3, porque dois
   deles erram na direção oposta ao primeiro.
2. **O substrato de predicado como parâmetro** do gerador, não como dedução (§10.3).
3. **A política de acoplamento `ENSURES` ↔ `CONSTRAINTS`** (§10.3).
2b. **O substrato de predicado como parâmetro** — **muda em 24/08/2026 (R7), J-16:** no `jca_android`
   já não há dois substratos; o parâmetro existe pelo **`jca` congelado**, que é onde as medições
   publicadas moram.
4. **A fronteira do parâmetro único**, com a recusa tipada `Unknown{MultiSlicedOrder, params:[…]}`
   como saída. **Muda em 24/08/2026 (R7):** o custo é **`0 de 24` em `5fbe8173`**, medido pela AST; a
   previsão de `≥1/24` a partir da tarefa 5.1 **foi falsificada** — a junção entregue tem um
   parâmetro. O custo declarado passa a ser o do `generic`, **93 de 118** (§12).
5. **Um `CrySLModelReader` por regra** — por **determinismo**, não por denominador; e o número do
   corpus que daí sai é 30, não 31 (§8, §9).
6. **A conferência a posteriori contra o `android.jar`** no lugar da tentativa de fixar o classpath
   do parser (§8). **Muda em 24/08/2026 (R7), J3:** passa a ser **consumida por M0** e a emitir
   `Unknown{UnresolvedSignature}`; e o número é **141**, não 155 (§8).

Acrescentados em 22/08/2026 (R5):

7. **O alfabeto não é disjunto**, e o modelo canônico guarda `events` ordenado com sobreposição, mais
   um autômato simbólico guardado sobre assinaturas (§12). Onde a guarda não for estática, a saída é
   `Unknown{OverlappingDispatch, labels:[…]}` — **com** o campo `labels`, que J-09 tornou obrigatório.
   **Muda em 24/08/2026 (R7), J2:** a testemunha é `IvChainJunction` `use`/`useRandomSpec`, não
   `CipherSpec` `f1`/`f2` — a primeira morreu com a tarefa 6.6 e a segunda nasceu no mesmo conjunto e
   no mesmo dia, o que prova que o fenômeno é estrutural e não acidente de um arquivo (§5.2).
8. **A regra de contagem de cada censo publicado** — a AST e não o texto, para parâmetros (§12); R1
   para cláusulas de `CONSTRAINTS` (§5.3).
9. **O instantâneo**: commit carimbado em toda tabela de M4, e campo `version` no `SpecModel` (§12,
   §13).
10. **A classificação FIEL/PROJETADO/CONFLADO/AUSENTE é julgamento humano**, não medição derivável —
    e dar-lhe domicílio derivável é parte do que o componente entrega (§9).
11. **O componente é a metade estrutural** de um desenho de dois instrumentos; a metade comportamental
    é o arnês do gh104, que já existe (§3). **Muda em 24/08/2026 (R7), J4:** rodá-lo contra as cinco
    specs globais era **pré-requisito da change**, e está **cumprido** — o resultado está no §5.5 e é
    a demonstração mais forte que este item tem, porque das três causas de silêncio que ele separou
    **só uma é decidível do `.mop`**.

Acrescentados em 24/08/2026 (R7):

12. **A moldura científica retargetada**, nos quatro eixos de J6 e nesta ordem: (i) **a qualidade
    medida do oráculo `api30`** — deleção, corrupção de operador e substituição de predicado, com
    `−33` cláusulas líquidas em 16 regras sob a regra R1 (§5.3), falsificável e com público próprio;
    (ii) **equivalência de `ORDER` é estritamente mais fraca que conformidade**, com a demonstração
    interna medida do `KeyGeneratorSpec` (§5.1); (iii) **`IncompleteOperationError` não tem
    contraparte em `.mop`** — agora medido por execução, não argumentado (§5.5, §10.5), e é também
    limite do próprio comparador M2; (iv) **a medida por corpus do que não se traduz, com `Unknown`
    contável** — diferente em espécie, e não em grau, da observação qualitativa do TSE.
    **A manchete do `notHardCoded` sai**: já está publicada em quadro destacado em
    `rvsec-paper/main.tex:1970-1974`, e reapresentá-la seria vender como novo o que o grupo já
    publicou.
13. **M0 — vitalidade do monitor** como primeira métrica, com recusa tipada antes de M1–M4 (§5.5).
14. **A forma do artefato: uma JVM, três módulos Maven** — `rvsec-crysl` (pai) + `-core` + `-mop` +
    `-crysl` (§12, J1). O JSON é **saída** do modelo canônico, não formato de intercâmbio.
15. **A taxonomia `Unknown` fechada e enumerada**, com esquema de campos fixo por tag (§12, J-09).
16. **O que morre**, com o censo de 7 comparadores e 11 leitores, o critério de corte escrito e a
    janela de convivência com os portões de CI (§12, J-05).

E duas coisas que a proposta **não** vai declarar, por decisão: o **`crysl.lower`** fica como trabalho
futuro, com razão escrita (J-14), e a promoção do arnês do gh104 a **oráculo de M2** fica aberta, com
critério de desbloqueio nomeado — as duas peças que faltam são o enumerador de palavras e o mapa
evento → chamada com argumentos (J4).

### Próximos passos sugeridos, em ordem de retorno

Os cinco primeiros da terceira rodada foram executados como V1–V10. O que sobra:

1. **Adicionar o checador de sanidade de `.mop`** (ids únicos + alfabeto da fórmula ⊆ ids). Vinte
   linhas sobre a AST, e V7 mostrou que é o **único** ponto do pipeline inteiro capaz de pegar essa
   classe — parser, gerador de monitor e compilador passam calados.
2. **Corrigir `PrettyPrinter.rsc:49,139`** no MetaCrySL e regerar `api30`. As cinco substituições
   léxicas medidas em §8 dizem exatamente o que consertar.
3. **Corrigir a precedência** em `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70` — conferido em
   24/08/2026 (R7) e **ainda invertido**: `> left sequence` acima de `> left or`, o oposto da
   gramática Xtext oficial. O parser de `ORDER` do gerador da quarta rodada já traz a precedência
   correta e serve de referência executável. **Reparado em 24/08/2026 (R7), J-19:** a metade
   `scripts/gh105_order_gate.py:136-200` **sai deste item — já foi executada**. As linhas `:164-197`
   do arquivo de hoje põem a vírgula mais fraca que `|` e separam as duas notações por escrito.
4. **Restaurar as `CONSTRAINTS`** dos três templates base do MetaCrySL (§5.3). São ~9 cláusulas
   normativas apagadas do oráculo, e o efeito é sobre o denominador de M3, não sobre uma spec só.
5. **Guarda de duas linhas** em `CipherTransformationUtil.alg/mode/pad` — latente, sem urgência (§9).
6. **Abrir a issue no GitHub** e entrar no workflow OpenSpec. **As três condições que este documento
   punha para esse passo estão cumpridas em 24/08/2026 (R7):** as dez validações fecharam (quarta
   rodada); as 129 linhas de assinatura foram remedidas sob leitor novo por regra e são **141** (§8);
   e o arnês do gh104 rodou contra as cinco specs globais (§5.5). É o próximo passo, e o único que
   resta antes de a change existir.

Acrescentados em 22/08/2026 (R5), em ordem de retorno:

7. ~~**Rodar o arnês do gh104 contra as 5 specs globais e as guardadas, antes de escrever qualquer
   linha do componente.**~~ **EXECUTADO em 24/08/2026 (R7) — J4.** Era o teste mais barato do
   risco-mãe (medir o autômato declarado e concluir sobre o monitor que rodou) e o instrumento já
   existia. Resultado no §5.5 e registro em `docs/20260824_medicoes_pre_change_conformidade.md` §2:
   131 traços replicados contra os dois conjuntos, mais quatro controles negativos autorados com a
   previsão escrita antes de rodar. **Quatro das cinco specs têm monitor vivo; a quinta não tem sítio
   de acusação nenhum; e as duas specs de *stream* calam sobre o traço que os próprios autores
   rotulam como violador, nos dois conjuntos** — a cegueira de `IncompleteOperationError`, medida.
8. **Corrigir `MacSpec.f2`**: `target(m)` sem `m` nas formais faz o pointcut nunca casar, e todo `Mac`
   fechado com `doFinal(byte[],int)` é acusado de `MAC-ORDER-00`. Nos dois conjuntos (§9).
9. **Dar diagnóstico ao `MOPParameters.add`** — um aviso de parâmetro duplicado, no molde do que já
   existe para evento duplicado. Onze specs do `generic` perdem declarações em silêncio hoje (§9).
10. **Depositar o arnês do §10 ou rebaixar a tabela** — feito o rebaixamento; o depósito continua
    pendente e é pré-requisito de qualquer número daquela seção entrar no artigo.
