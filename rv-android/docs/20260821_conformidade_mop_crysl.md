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
.mop     ──lift──┐
                 ├──▶ MODELO CANÔNICO ──▶ comparar ──▶ veredito + testemunha
.crysl   ─parse──┘                     └──▶ (opcional) emitir .crysl legível
```

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

Em **12 das 23 specs**, a linguagem aceita pelo autômato é a *ordem* correta, não o *uso* correto:
eventos de uso incorreto foram deliberadamente absorvidos, com a acusação movida para o corpo do
evento. Contra a cláusula `ORDER` isolada isso é a comparação certa; contra "conformidade com a
regra inteira" erra em 12 casos, sempre no mesmo sentido. **O protocolo tem de declarar qual das
duas está medindo.**

---

## 3. Metade já existe — a estrutural ad hoc, a comportamental não

O mapeamento CrySL↔JavaMOP já foi feito à mão e está espalhado por seis lugares, nenhum durável.

| Artefato | Tam. | O que carrega |
|---|---|---|
| `ase-journal/docs/20260816_analise_tematica_anexos/04_assimetria_specs.md` | 664 l. | Tabela de paridade de allow-lists (7 idênticas / 3 alargadas / 1 estreitada), matriz por tipo de erro CogniCrypt, cláusulas CrySL sem contraparte |
| `data/jca_android/order_alphabet_map.csv` | 121 l. | `spec, mop_event, order_symbol, symbol_kind, rule, rule_line, disposition` |
| `data/jca_android/predicate_graph.csv` | 73 l. | Cada sítio de predicado com a cláusula CrySL que traduz, polaridade, aridade, mecanismo, pertinência ao autômato |
| `data/jca_android/constraint_table.csv` | 59 l. | Vereditos `DIVERGENTE` / `CRYSL-NAO-IMPLEMENTADO` / `MOP-MAIS-RESTRITIVO` / `MOP-SEM-BASE` |
| `data/jca_android/divergence_record.csv` | 181 l. | Cada divergência deliberada, com evidência primária e custo declarado |
| `rvsec-core/.../br/unb/cic/mop/Property.java` | 26 const. | Os nomes de predicado projetados. **Corrigido em 22/08/2026 (R5):** são 26 constantes, não 24, e apenas **3** têm Javadoc citando a cláusula CrySL (`GENERATED_CIPHER`, `MACED`, `PREPARED_KEY_MATERIAL`) — as outras 23 não têm comentário nenhum |

**O maior precursor não é ad hoc, e faltava nesta lista** — acrescentado em 22/08/2026 (R5):

| Artefato | Tam. | O que faz |
|---|---|---|
| `rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` | 1255 l. | Replica um traço de chamadas de API por um **snapshot de monitor gerado** e registra o que ele acusa. Gramática de traço própria (`bind`, `->`); resolve cada chamada contra os pointcuts do próprio snapshot, lidos de `MultiSpec_1MonitorAspect.json`, para que os dois lados não precisem partilhar alfabeto; *class loader* novo por traço, porque o gerado guarda as tabelas de indexação em campos `static`; `Outcome.unresolved` separa "não acusado" de "não replicado" |
| `…/harness/TraceRunnerTest.java` | 243 l. | Auto-teste JUnit do próprio runner |
| `scripts/gh104_diff_harness.py` | 489 l. | Replica um arquivo de traços por **dois** snapshots e classifica cada diferença em `unchanged`/`moved`/`removed`/`introduced`; `--selftest` com uma mutação autorada por veredito |
| `data/gh104/traces/` | 94 traços | Corpus versionado, 1 a 9 por spec |
| `data/gh104/evidence/harness/` | 162 arq. | Evidência por spec, 23 por rodada |

O `TraceRunner` enuncia a tese que este documento precisa levar a sério: *"a structural gate measures
the artefact and not its behaviour"* (`:36-42`) — e cita os dois defeitos que a linhagem entregou
como sucesso (a fusão de *wrappers* do gh100, com `wrappersGenerated 96 -> 84` reportado como êxito,
e os reparos de autômato do gh101, que moveram a acusação para a chamada seguinte). **M1, M2, M3 e
M4 são todas estruturais.** O componente é a metade estrutural de um desenho de dois instrumentos
cuja metade comportamental já existe, tem auto-teste, corpus versionado e evidência reproduzível.

E há **~10.400 linhas de Python** em 18 scripts `rv-android/scripts/gh10*.py`, mais os scripts das
duas auditorias em `audit/`. Contando o que faz a mesma coisa:

- **Três implementações independentes da comparação de `ORDER`** — `alfa_automata_check.py`,
  `alfa_language_check.py` (auditoria de 08/08) e `gh105_order_gate.py`.
- **Cinco leitores de CrySL** distintos, todos ad hoc.
- **14 dos 18 scripts parseiam `.mop` por expressão regular.**

A justificativa do componente não é "seria bom automatizar". É que a duplicação já aconteceu três
vezes por falta de um domicílio durável, e a análise manual não escala para um alvo que muda a cada
sítio fiado — o `jca_android` está sendo reescrito agora, 30 de 74 tarefas do gh105. O anexo 04 é
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

Quatro métricas, uma por seção do CrySL, cada uma com testemunha concreta em vez de percentual solto.

| | O que compara | Saída |
|---|---|---|
| **M1** Eventos | conjuntos de assinaturas concretas | cobertura + as duas diferenças listadas; alimenta o alinhamento de rótulos que M2 usa |
| **M2** Ordem | L(A_mop) vs L(A_crysl) | equivalente / mais permissiva (falsos negativos) / mais estrita (falsos positivos) / incomparáveis, + palavra-testemunha mais curta |
| **M3** Constraints | por variável: literais casados, divergentes, ausentes, não-reconhecidos | veredito por cláusula |
| **M4** Predicados | grafo `ENSURES`/`REQUIRES`/`NEGATES` | arestas presentes, ausentes, invertidas |

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

O monitor gerado expõe o autômato de forma inteiramente mecânica:

```java
static final int Prop_1_transition_g1[] = {4, 4, 5, 5, 5, 5};   // próximo estado por estado atual
static final String[] RVM_eventNames = {"g1","g2","load","store","ge1","se1","gk1"};
KeyStoreSpecMonitor_Prop_1_Category_fail  = Prop_1_state == 5;   // estado de falha, explícito
KeyStoreSpecMonitor_Prop_1_Category_match = Prop_1_state == 1;   // estado aceitante, explícito
```

Três observações de implementação, todas verificadas nos 23 monitores:

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

| Spec | Formalismo | Veredito | Testemunha mais curta |
|---|---|---|---|
| `MessageDigestSpec` (controle) | ere | **EQUIVALENTES** | — |
| `SignatureSpec` | ere | **EQUIVALENTES** | — |
| `KeyGeneratorSpec` | ere | **EQUIVALENTES** (depende de N1) | sem N1: `g1 g1 gk1` |
| `SecureRandomSpec` | fsm | **MOP MAIS PERMISSIVA** | `new SecureRandom(); generateSeed(20); setSeed(seed)` |
| `CipherSpec` | fsm | **INCOMPARÁVEIS** | ver abaixo |

**Onde N1 é carga.** Rodada a comparação com e sem a normalização N1, **só o `KeyGeneratorSpec`
muda de veredito**. `MessageDigestSpec` e `SignatureSpec` são equivalentes nas duas leituras, porque
as suas ERE já trazem um único evento criador na cabeça — `(g4* g1 | g4* g2 | g4* g3)` e `(g1|g2)` —
enquanto a do `KeyGeneratorSpec` traz `g1+`. Isto corrige o §13, que dizia "dois dos três". N1 está
confirmado por execução (V8), então o veredito do `KeyGeneratorSpec` está fechado.

**Critério de fidelidade do apagamento.** Apagar um evento MOP `e` (mapeá-lo a ε) preserva a
linguagem *se e somente se* `e` rotula um auto-laço em **todo** estado do autômato — ou se nenhuma
palavra realizável contém `e` junto com outros símbolos.

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
22/08/2026 (R5). Censo do monitor gerado, idêntico nos dois conjuntos: **5 das 23 specs não
constroem `MapOfMonitor`** e compilam para `Tuple2<Set, Monitor>`, isto é, **um monitor para o
programa inteiro** — `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`,
`KeyStoreSpec`, `RandomStringPassword`. Nelas o despachante faz `matchedEntry = Spec__Map` sem
consultar objeto nenhum, e a palavra `g1 g1` é realizável. N1 é propriedade da árvore de indexação
gerada, não do JavaMOP, e vale **por medição, spec a spec**. As três aplicações concretas desta seção
sobrevivem: `KeyGenerator`, `SecureRandom` e `Cipher` indexam integralmente.

(O discriminante é a ausência de `MapOfMonitor`. O comentário gerado `// RVMRef_x was suppressed to
reduce memory overhead` **não** discrimina nada: aparece 21 vezes, uma por spec paramétrica,
inclusive nas que indexam.)

N3 e N4 são o que faz do `CipherSpec` um caso especial — e N4 quebra uma premissa do
`order_alphabet_map.csv`, que assume cada evento MOP disjunto dos demais.

> **N4 é maior do que esta seção o trata, e é problema de multiplicidade, não de rotulagem** —
> medido em 22/08/2026 (R5). Varridos os 46 `.mop` (254 eventos) com interseção de aridade e tipo de
> retorno: **10 pares de eventos se sobrepõem no `jca_android` e 26 no `jca`**. Vinte e um deles (22
> no `jca`) são separados por `condition` complementar — o idioma do gêmeo negado. Os que **não** são:
>
> - `CipherSpec` `f1` × `f2`, nos dois conjuntos, sem `condition` nenhuma. Tecido com `ajc` e
>   executado, `getInstance(t); init(ENCRYPT,k); doFinal()` emite **dois** relatórios de um único
>   *join point* — `CIPHER-ORDER-00 ev=f1` e `ev=f2`. O tecelão despacha `f1` primeiro; `f1` vai a
>   *fail*, o `__RESET` leva a 0, e `f2` de 0 também é *fail*. **A palavra é `f1 f2`, e as duas letras
>   acusam.**
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
> Ressalva para a normalização: `KeyGeneratorSpec:44/:60` e `MessageDigestSpec:44/:65` não são
> complementares sintaticamente — `g1` lê o argumento, `g3`/`g4` lê o campo
> `currentAlgorithmInstance`. Só são exclusivos porque o corpo de `g1` escreve o campo antes de `g3`
> ser despachado, dentro do mesmo advice fundido. **A separação depende da ordem de despacho, não da
> guarda.**

**O veredito do `CipherSpec`**, recalculado com a precedência correta e com o autômato extraído do
monitor gerado (M2-eff ponta a ponta):

```
MOP \ regra   g1 i1 f1    = getInstance(t); init(mode, cert); doFinal()
              o pointcut `doFinal(..)` também casa `doFinal()`, então o monitor aceita
              um doFinal sem update; a regra exige FINWOU ou updates+ antes.

regra \ MOP   g1 i1 i1 f2 = getInstance(t); init(ENCRYPT,k); init(DECRYPT,k); doFinal(pt)
              reinicializar um Cipher é idiomático e a regra permite (Inits+);
              o fsm não: s2 não tem transição de init. FALSO POSITIVO REAL.

VEREDITO: INCOMPARÁVEIS
```

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
> 3. **A janela está agendada para fechar.** A tarefa **6.6 do gh105, aberta**, manda *"make the wider
>    pointcut disjoint"* exatamente neste par. Feita, `doFinal()` nu passa a emitir só `f1`, que em
>    `s2` não transita: o monitor rejeita, e a direção `MOP \ regra` fica sem testemunha. O veredito
>    `INCOMPARÁVEIS` sustenta-se hoje pela direção `regra \ MOP` (`g1 i2 i2 f2`, a reinicialização),
>    que é independente.
>
> Na notação: as testemunhas do V4 escrevem `i2` (`init(Key)`), não `i1` (`init(Certificate)`).

**Reconfirmado sobre o autômato do parser (V4).** Refeita a comparação com o `StateMachineGraph` que
o `CrySLParser` devolve, o veredito é o mesmo e as **duas testemunhas saem idênticas**. De passagem,
a busca confirma o reparo que o §9 registra para o `order_alphabet_map.csv`: `CipherSpec.f2` mapeia
mesmo `{f1,f2,f4}`, porque o pointcut é `public byte[] Cipher.doFinal(..)` e as sobrecargas que
devolvem `byte[]` são `doFinal()`, `doFinal(byte[])` e `doFinal(byte[],int,int)` — é daí que a
primeira testemunha nasce.

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
>    regras acima, e o censo já aplica o rótulo certo (`IvParameterSpec.mop:35-37`,
>    `DHGenParameterSpecSpec.mop:24`).
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

92 cláusulas normativas nas 33 regras (54 `ENSURES`, 36 `REQUIRES`, 2 `NEGATES`), 32 predicados
distintos, **aridade nunca passa de 2** (59 de aridade 1, 33 de aridade 2). 73 delas estão em regras
com `.mop`.

| Classe | n | % das 73 | O que é |
|---|---:|---:|---|
| FIEL | 26 | 35,6 % | mesma polaridade, mesma aridade, mesmas posições |
| PROJETADO | 13 | 17,8 % | aridade 2 achatada em 1 pelo `ExecutionContext` |
| CONFLADO | 5 | 6,8 % | implementado sob um `Property` que é outro predicado |
| AUSENTE | 29 | 39,7 % | nenhuma contraparte |
| SEM-BASE | 16 | — | sítios que a regra não pede (8 são `remove()` em `@fail`) |

O teto é estrutural: `ExecutionContext` tem aridade 1, devolve booleano e não tem `validateAbsent`.
Num arquivo que só usa esse substrato, uma cláusula de aridade 2 ou negada é *inexprimível*, por
melhor que a spec seja.

| Cenário | das 73 cobertas | das 92 totais |
|---|---:|---:|
| medido hoje | 35,6 % | 28,3 % |
| teto com o substrato atual (5 arquivos migrados) | 74,0 % | 58,7 % |
| teto com migração completa a `PredicateStore` | 100 % | 79,3 % |

> **Instantâneo, carimbado em 22/08/2026 (R5): esta tabela e os números de M4 desta seção foram
> medidos no commit `d64f3a40`, não no `HEAD` de publicação.** A linha do meio depende de "5 arquivos
> migrados", e hoje são 7 (8 na árvore de trabalho). Enquanto o gh105 correr, todo número de M4 é
> alvo móvel e só significa alguma coisa com o commit ao lado — ver §13.

Os 19 bloqueios do teto atual são 17 cláusulas de aridade 2 em arquivo `ExecutionContext` e 2
cláusulas negadas no `MacSpec` que precisam de `validateAbsent`.

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

**Achado sobre o gh105.** Contando cadeias produtor→consumidor efetivamente realizadas, o número é
**idêntico em `jca` e `jca_android`**: 8 das 44 arestas normativas, e 3 cadeias no nível de
`Property` (`GENERATED_KEY`, `GENERATED_PUBLIC_KEY`, `RANDOMIZED`). O gh105 trocou o substrato
debaixo de cadeias que já existiam e reduziu ruído — a *topologia* ficou intacta. Isso não é
crítica: é o que permite dizer com precisão o que o próximo passo tem de fazer.

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

**Não agregue as quatro métricas num score único.** Um número esconde qual seção está ruim e convida
a otimizar o número. Se o artigo exigir um valor, que seja o vetor por seção.

---

## 7. Viabilidade — o lado `.mop`

Melhor do que o esperado, e verificado por execução.

```
jca                        23   23 ok   0 fail
jca_android                23   23 ok   0 fail
jca_android_bug_predicate  23   23 ok   0 fail
generic                   118  118 ok   0 fail
generic_new                27   27 ok   0 fail
TOTAL = 214   OK = 214   FAIL = 0        (JDK 21, offline, só o jar do javamop no classpath)
```

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
63 `target(`, 36 `condition(` (eram 41 em `d64f3a40`), e **zero** `execution`, `within`, `cflow` ou
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

**Dois substratos coexistem.** Em `d64f3a40`, o `jca_android` tinha 64 sítios de `ExecutionContext`
e 21 de `PredicateStore`, com 5 dos 23 arquivos migrados; no `HEAD` `c12f4689` são **47 / 26 / 7**
(medido em 22/08/2026, R5, varrendo os 25 commits que tocam o diretório). O extrator precisa reconhecer os dois — e o
alvo se move enquanto o gh105 corre. Isso é argumento para começar pelo extrator de predicados (M4)
e servir o gh105 imediatamente, em vez de esperar ele terminar.

### Armadilhas confirmadas do parser

- `BlockStmt.getStmts()` devolve **`null`**, não lista vazia, para bloco `{ }` — e o corpus tem vários.
- `MOPNameSpace` é estático global e `SpecExtractor.parse` não chama `init()`; acumula estado entre arquivos.
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

As cinco, na ordem em que se aplicam:
`FORBIDDEN:`→`FORBIDDEN` · `;;`→`;` · `neverTypeOf/noCallTo/callTo/notHardCoded(…)`→`[…]` ·
`length(…)`→`length[…]` · `alg`→`algName`.

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

  **O impacto disso no corpus é zero**: as regras que carregam produzem 129 linhas de assinatura
  resolvida idênticas com e sem o `android.jar`. **Ressalva de 22/08/2026 (R5):** essa medição foi
  feita em modo lote, com leitor partilhado — a configuração que o §12 descarta. Sob leitor novo por
  regra são 30 regras, e as 129 linhas precisam ser remedidas antes de entrar na proposta. O desenho que substitui a via impossível é
  **conferir a posteriori**: indexar o `android.jar` e verificar cada assinatura resolvida. Medido em
  155 eventos — 131 casam assinatura exata, 19 casam só por aridade (apagamento de genéricos e
  `AnyType`), 2 são limitação do conferidor (`SecretKey.destroy/getEncoded`, herdados), e **3 são
  achado real**: `java.security.spec.DSAGenParameterSpec` (só existe da API 35 em diante) e
  `javax.xml.crypto.dsig.spec.HMACParameterSpec` (o pacote `javax.xml.crypto` inteiro não existe em
  nenhum nível de API Android). E `jca_android/HMACParameterSpecSpec.mop` monitora essa segunda —
  uma das 23 specs do conjunto, **morta por construção** no Android.
- **Dependências transitivas**, confirmadas por `dependency:tree` offline: Guava **33.5.0-jre**,
  Guice **7.0.0** e **`slf4j-simple` em escopo compile**. O `rvsec-parent` pina `guava.version=19.0`
  (presa ao Soot); se o `dependencyManagement` da raiz alcançar o módulo novo, força Guava 19
  debaixo de uma biblioteca que espera 33.5 — falha em runtime, não em compilação. O módulo não
  precisa de Soot, então dá para isolar, mas tem de ser decisão explícita no `pom`, com exclusão do
  `slf4j-simple`.

---

## 9. Defeitos encontrados

Achados que valem independentemente do módulo. Cada linha foi verificada nos arquivos ou por execução.

| Onde | O quê | Consequência |
|---|---|---|
| `scripts/gh105_order_gate.py:136-200` | Descarta as vírgulas e reusa precedência de expressão regular; a gramática CrySL tem `\|` ligando mais forte que `,` | **Veredito errado nas duas direções.** Uma regra afetada — `Cipher` — e é a que o gate reporta como falha. |
| `jca/KeyPairGeneratorSpec.mop:130` e `jca_android/…:130` | Única spec com `@fail` sem `__RESET`; o estado de falha é absorvente e o dispatcher não tem trava | Uma vez em falha, **todo evento seguinte re-dispara o handler** — ORDER e `remove()` repetidos sem limite. Está no `jca` congelado, logo infla as medições publicadas. |
| `MetaCrySL/src/generator/PrettyPrinter.rsc:49,139` | `FORBIDDEN:` com dois-pontos e `;;` após `neverTypeOf` | 7 de 33 regras `api30` não são CrySL válido. Duas linhas de conserto. |
| `generated/api30/Signature.cryptsl:51` | `offset` e `len` usados em `u3`/`s2`/`v2` sem declaração em `OBJECTS` | **Reafirmado em 22/08/2026 (R5):** é defeito da regra, e o oficial declara os dois. A regra carrega ou não **conforme quais outras foram lidas antes no mesmo leitor** — quem a resgata são exatamente `GCMParameterSpec`, `IvParameterSpec` e `Mac`, as três únicas que declaram ambos. O parser **não infere** tipo nenhum: herda a declaração vazada. Sob leitor novo por regra, `Signature` falha. |
| `generated/api30/DigestOutputStream.cryptsl:20` | `FORBIDDEN on(java.lang.String)` — o método real recebe `boolean` | Regra não carrega. Só um parser que resolve tipos pega isso. |
| `generated/api30/AlgorithmParameters.cryptsl:47` | `alg in {"BLOWFISH"} => preparedIV[params]` — predicado dentro de `CONSTRAINTS` | Cláusula no bloco errado; pertence a `REQUIRES`. Forma única no conjunto. |
| `CrySL-Rules/SSLEngine.crysl:12` | `EnableProtocol := cp1;` mas o evento é `ep1` | Typo em 1.5.2 *e* 3.0.1 — **a regra nunca carregou**. São 47 regras efetivas, não 49. |
| `CrySL-Rules/OAEPParameterSpec.crysl:8` | Declara `java.lang.String alg;`, hoje palavra reservada | Rejeitada pela gramática 4.x. Foi por isso que a 3.0.1 removeu o objeto. |
| `jca/GCMParameterSpecSpec.mop:23,34` | Dois eventos com id `c1`; o `ere` referencia um `c2` inexistente | Parseia em silêncio. Corrigido em `jca_android`; presente no conjunto arquivado. |
| `KeyPairSpec.mop:38` (ambos os conjuntos) | O evento `gpr` (`getPrivate()`) grava `GENERATED_PUBLIC_KEY` | Chave privada registrada sob o predicado da pública. |
| `TrustManagerFactorySpec.mop:101` | `generatedTrustManager[tms]` gravado como `GENERATED_KEY_MANAGERS` | Trust manager sob o predicado dos key managers. |
| `SecretKeySpecSpec.mop:45` e `SecretKeySpec.mop:26` | `preparedKeyMaterial` implementado como `RANDOMIZED`, nas duas pontas | Funciona operacionalmente, mas usa o hub `RANDOMIZED`. A constante `PREPARED_KEY_MATERIAL` existe e **não tem um único sítio**. |
| `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70` | `sequence` (`,`) declarado com prioridade **maior** que `or` (`\|`) — invertido em relação à gramática Xtext oficial | Mesmo defeito do gate, na outra ponta do pipeline. Invisível hoje porque o `ppEventExp` só parenteteriza nós `parentheses()`: o texto sai igual ao que entrou e a AST errada não aparece. Um emissor `.mop` a exporia na hora. |
| `TrustManagerFactorySpec.mop:98-99` | Três erros de copiar-e-colar no mesmo evento `gtm1`: tipo de retorno `KeyManager[]` no pointcut, ligação `TrustManager[][]`, e a `Property` errada | O pointcut declara um método que não existe com aquela assinatura. Um gerador que deriva de `EVENTS` + API real não produz nenhum dos três. |
| `generated/api30/Cipher.cryptsl:131,133,135` | `length(x) <= off` — comparação invertida; a análoga implementada (`SecretKeySpec.cryptsl:29`) escreve `>=` | Transcritas literalmente, acusam **todo uso conforme** de `doFinal`. Vêm do template base (`MetaCrySL/samples/jca/base/Cipher.cryptsl:80-82`), logo regerar `api30` não as corrige. **Precisado em 22/08/2026 (R5):** o upstream (`CrySL-Rules/Cipher.crysl:122,123,127,128`) escreve as **quatro** com `>=`, logo não é perda de cláusula e sim **corrupção de operador** contra a fonte de verdade. |
| `MetaCrySL/samples/jca/base/Cipher.cryptsl:79` (→ `api30:129`) | `length(pre_plaintext) >= pre_plain_off + len`, mas `len` é ligado pelos `doFinal`; quem liga o comprimento do `update` é `pre_len` — declarado (`api30:25`), ligado em `u3`/`u4`, e usado por cláusula nenhuma | A cláusula relaciona um buffer do `update` com um comprimento do `doFinal`. O upstream distinguia `prePlainTextLen` de `plainTextLen`. Imune a regeração. Achado de 22/08/2026 (R5). |
| `jca_android/MacSpec.mop:143-147` e `jca/MacSpec.mop` | O evento `f2` declara `target(m)` sem `m` nas formais; o `ajc` trata `m` como **nome de tipo** — `[warning] no match for this type name: m [Xlint:invalidAbsoluteTypeName]` | **O pointcut nunca casa.** Como `f2` está no `ere` (`:160`), todo programa que fecha um `Mac` com `doFinal(byte[],int)` é acusado de `MAC-ORDER-00`. É `MacSpec` 7/8, e faltava na linha das specs com fatiamento quebrado. Achado de 22/08/2026 (R5). |
| `javamop/.../ast/mopspec/MOPParameters.java:41-51,84-94` | `add` descarta em silêncio parâmetro cujo **nome** já existe; `getParam` compara só o nome, ignorando o tipo. Sem log, sem exceção — ao contrário de evento duplicado, que é detectado e renomeado (`JavaMOPSpec.java:100-135`) | 11 specs do `generic` perdem declarações, e **o tipo sobrevivente na tupla de indexação pode não ser o que os eventos ligam**: `FSM123(InetAddress i, InetSocketAddress i)` gera `FSM123(InetAddress i)` com os três eventos ligando `InetSocketAddress i`, exit 0 e zero avisos. Achado de 22/08/2026 (R5). |
| monitor gerado, `Prop_1_event_*` | O monitor é criado (`FindOrCreateEntry`) **antes** de a `condition` ser avaliada | Uma guarda reprovada deixa um monitor vivo no estado 0, e o evento seguinte é julgado dali. É metade do mecanismo do falso `InvalidSequenceOfMethodCalls` do §5.1. Achado de 22/08/2026 (R5). |
| `generated/api30/SSLContext.cryptsl:52` | `randomized[sr]`, mas `EVENTS` declara `Init: init(kms, tms, _)` — `sr` é anonimizado | Não existe ponto do programa em que `sr` tenha valor. Cláusula inligável por qualquer pointcut. |
| `generated/api30/KeyPairGenerator.cryptsl:64` | `alg in {"EC"} => preparedEC[params]`, e **nenhuma** das 33 regras ensures `preparedEC` | Predicado órfão. Um tradutor que veja só esta regra emite uma leitura que nunca pode responder `SATISFIED`: todo `initialize(ECGenParameterSpec)` conforme vira report. |
| `rvsec-core/.../jca/util/CipherTransformationUtil.java:10-30` | `mode("AES/")` lança `ArrayIndexOutOfBoundsException`; `alg("/")` também. As três utilitárias caem juntas, porque `Api30CipherTransformationUtil` e a arquivada delegam o parsing a esta | **Alcance corrigido em 21/08/2026 (V9):** o defeito existe, mas a entrada não chega. `Cipher.getInstance` rejeita toda transformação com barra final antes de retornar (`Invalid transformation format`), e todo sítio de `isValid` recebe uma transformação que já sobreviveu ao `getInstance` — por `args()` num `after … returning`, ou por `c.getAlgorithm()`. **Latente**, não crash vivo: vale a guarda de duas linhas, não vale urgência. |
| `KeyPairGeneratorSpec.mop:40-48` | `switch` total com `default: return false` fechando um conjunto **aberto** de implicações | `alg in {"ElGamal"}` não casa nenhuma cláusula, logo pelo oráculo o `keySize` fica irrestrito. Na prática `getInstance("ElGamal")` não emite erro e o `initialize(1024)` seguinte reporta `KEYPAIRGENERATOR-KEYSIZE-00`: acusa a violação errada e cala a certa. |
| 7 de 21 specs parametrizadas | Ligação parcial ou nula do parâmetro declarado — `KeyStoreSpec` 0/7, `HMACParameterSpecSpec` 0/1, `RandomStringPassword` 0/2, `KeyPairSpec` 2/3, `PBEKeySpecSpec` 2/4, `TrustManagerFactorySpec` 3/4, **`MacSpec` 7/8** | **Corrigido em 22/08/2026 (R5):** os seis números originais conferem contra o código gerado, mas a frase-cabeçalho ("nenhum evento liga") contradizia as três últimas linhas, que ligam parcialmente. Onde a ligação é **0/N** o fatiamento é no-op e a spec degenera para autômato global — `KeyStoreSpec(KeyStore ks)` declara `ks` e os 7 eventos usam uma variável livre `k`. O `MacSpec` faltava (linha própria acima). O oráculo decidível é o monitor gerado: **5 das 23 não constroem `MapOfMonitor`** (as três com 0/N, mais `CipherInputStreamSpec` e `CipherOutputStreamSpec`, que são declaradas **sem parâmetro** e por isso ficam fora destas 21). |
| `CrySLModelReader.getStatesForMethods` | `after <Agregado>` resolve para **conjunto de nós vazio** quando **nenhum método** do agregado aparece no `ORDER` | **Confirmado por sonda em 21/08/2026 (V9):** `after Fora`, com `Fora := d2` e `d2` fora do `ORDER`, devolve `eventos=1 NOS=0` — o predicado vale em estado nenhum, a regra carrega sem erro e sem aviso. A resolução é **por método, não por nome de agregado**: `Sozinho := g1` com `ORDER Gets, d1` resolve normalmente. **Alcance no corpus: zero** — as 19 cláusulas `after` das 33 regras citam, todas, símbolo presente no `ORDER`. |

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
  o CSV ainda diz o contrário. **Medido de novo em 22/08/2026 (R5): hoje são 73 linhas de dados** — o
  arquivo encolheu com a migração (`86 → 85 → 79 → 78 → 74` linhas totais), e é a segunda medição
  independente que carimba o instantâneo deste documento.

  **E as cinco colunas de julgamento não são deriváveis de artefato nenhum.**
  `scripts/gh105_predicate_graph.py` (1845 linhas) nunca lê um `.cryptsl` — as três ocorrências de
  `crysl` no arquivo estão em prosa de comentário —, e o próprio docstring diz que carrega *"the
  committed `data/jca_android/predicate_graph.csv` for the judgment columns **no analyzer can
  re-derive**"* (`:34-35`, repetido em `:1028-1030`). `carry_judgments()` copia-as de uma versão
  anterior do próprio CSV. A classificação FIEL / PROJETADO / CONFLADO / AUSENTE do §5.4 é
  **julgamento humano semeado e propagado por cópia**, e tem de ser publicada como tal — não como
  medição. Dar-lhe domicílio derivável é uma das coisas que o componente resolve.
- **`order_alphabet_map.csv`** — o gate pula 13 das 23 specs por falta de linhas, incluindo
  `KeyGeneratorSpec` e `MessageDigestSpec` (dívida declarada da tarefa 7.1). Duas discordâncias de
  conteúdo: a razão registrada para `SecureRandomSpec.g4` está factualmente errada (`args(alg)` casa
  exatamente um argumento, então `g4` não cobre `g2` — e um `getInstance` de dois argumentos com
  algoritmo rejeitado *não é acusado por ninguém*); e `CipherSpec.f2` deveria mapear `{f1,f2,f4}`,
  não `{f2,f4}`.

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
| Fatiamento paramétrico quebrado em 6 de 21 specs | `SPEC <Tipo>` nomeia o parâmetro; `target`/`returning` sai por construção |
| 18 de 18 cabeçalhos citando o oráculo errado | a procedência é emitida junto |

### 10.5 O que não se traduz — e é isto que é publicável

- **`neverTypeOf` e `notHardCoded`** (5 cláusulas) são propriedade do tipo estático da origem. Em
  runtime a assinatura já é `char[]`. Registro `Unknown` tipado, não comentário: comentário não é
  contável e não entra em métrica. Note que o corpus cobre o *defeito* por outra via — o taint
  `String.toCharArray()` de `RandomStringPassword.mop:18-23` alimentando um `REQUIRES randomized`.
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
(`CogniCrypt_SAST`; o compilador está descrito no CrySL, ECOOP 2018, não no CogniCrypt/ASE 2017 que
já está em `references.bib` do paper do grupo), e linguagens de padrão sobre traço com backend
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

**Escolha: Java 21 nos módulos de tecnologia, Scala 3.3 admissível no núcleo.** O trabalho de dirigir
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
> Nuance medida que vale registrar, mas que não resgata a sobrescrita: **nenhuma das 23 specs usa
> `ptltl`** — 19 usam `ere` e 5 usam `fsm`. A proibição de excluí-lo não é sustentada pelo corpus
> atual; o que a sustenta é não querer descobrir isso numa spec futura.

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
rvsec-crysl                    (pom-pai; sobrescreve guava.version e scala.version)
├── rvsec-crysl-core           modelo canônico · autômatos · comparação M1–M4      [zero deps]
├── rvsec-crysl-mop            lift : SpecExtractor      → modelo                  [javamop]
│                              lower: modelo → MOPSpecFile → DumpVisitor
└── rvsec-crysl-crysl          lift : CrySLParser        → modelo                  [CrySLParser 4.0.6]
                               lower: modelo → Domainmodel → CrySLSemanticSequencer
```

Os produtos caem dessa forma sem módulo próprio:

- **comparador** (o produto do §1) = `mop.lift` + `crysl.lift` → `core.compare`
- **`crysl2mop`** (o gerador do §10) = `crysl.lift` → `core` → `mop.lower`
- **`mop2crysl`** = `mop.lift` → `core` → `crysl.lower` — subproduto, sem consumidor conhecido

| Item | Escolha |
|---|---|
| Local | `rvsec/rvsec-crysl/` — irmão de `rvsec-mop-extractor` |
| Coordenadas | `br.unb.cic:rvsec-crysl` (pai) e os três filhos |
| Entrada MOP | `javamop.parser.SpecExtractor` — 214/214 verificados |
| Saída MOP | `DumpVisitor` — 73/73 reparseiam (§11.1) |
| Entrada CrySL | `crysl.CrySLParser:4.0.6` + normalização léxica de **5** substituições (§8) — a quinta é `length(…)`→`length[…]`, e sem ela o corpus para em 27 |
| Saída CrySL | `CrySLSemanticSequencer` + formatador próprio (o projeto CrySL não tem formatter) |
| Classpath | JDK do host para *ler*; `android.jar` da API 30 como **conferidor a posteriori** de cada assinatura resolvida. Fixar o classpath do parser é impossível (§8) |
| Autômato MOP | preferir o **monitor gerado** (já minimizado); `ere`/`fsm` como fallback obrigatório |
| Autômato CrySL | `StateMachineGraph`, com determinização própria (§10.2) — obrigatória por correção, *no-op* nas 30 regras de hoje |
| Leitura CrySL | um `CrySLModelReader` **por regra**: o escopo de `OBJECTS` vaza entre regras no mesmo leitor (§9) |
| Parâmetro múltiplo | fora de escopo, com **recusa tipada** — custo medido 0/23 em `jca`+`jca_android`, 93/118 no `generic` (§12) |
| Linguagem | Java 21 nos leitores; Scala 3.3 admissível no núcleo (§11.4) |
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
```

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
| `jca` | 23 | **0** |
| `jca_android` | 23 | **0** — todas com 0 ou 1 |
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
6 de 21 specs com fatiamento quebrado (§9).

No **comparador** e na direção `.mop` → `.crysl`, uma spec de *k*>1 parâmetros não tem imagem em
CrySL quando a `ORDER` de fato intercala eventos sobre objetos diferentes. A saída certa é **recusa
tipada** — `Unknown{MultiSlicedOrder, params:[…]}` —, nunca achatamento silencioso, pela mesma razão
do §6: sem a categoria explícita, "não sei traduzir" e "traduzi" saem pela mesma porta.

**Custo da restrição no corpus do componente: zero em `HEAD`, e a data de validade já está marcada.**
Corrigido em 22/08/2026 (R5): a tarefa **5.1 do gh105, aberta**, cria `IvChainJunction.mop` para a
cadeia `SecureRandom → byte[] → IvParameterSpec → Cipher`, e a delta-spec da própria change é
explícita — *"the wiring SHALL use a junction specification: **one multi-parameter JavaMOP
specification per chain**"*. É a primeira spec multi-parâmetro do `jca_android` **por definição de
mecanismo**, é a primeira das onze tarefas do Grupo 5, e as 5.4/5.9 preveem mais junções. A fronteira
vai a ≥1/24 durante a janela em que o componente seria construído.

Isso não muda a resposta — a recusa tipada continua sendo o certo —, mas muda o que se pode escrever
sobre ela: é fronteira de escopo **com custo conhecido e crescente no próprio conjunto**, não
fronteira sem custo. E vira dívida maior no dia em que apontarem o comparador para o `generic`, onde
são 93 de 118.

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

Sem portão nenhum, dois modos de falha passam calados:

- **Evento declarado e ausente do `ere`** ganha uma linha de transição toda-`fail`, e acusa todo
  monitor vivo da spec quando dispara. Já aconteceu e está registrado em `PBEKeySpecSpec.mop:26-32`.
- **`@match` sem `@fail`** produz uma spec que compila, roda e nunca acusa nada. `SecretKeySpec.mop`
  e `RandomStringPassword.mop` são exatamente isso hoje.

Isso também é o que resolve a decisão que a segunda rodada deixou aberta — Java ou consolidação do
Python. O comparador e o gerador partilham autômato, modelo e portão; mantê-los em duas linguagens
duplicaria a peça mais delicada de ambos. O domicílio único é o `core`.

---

## 13. Confiança e o que ficou verificado

Dos cinco riscos nomeados na primeira rodada, quatro caíram e um se confirmou.

| Risco da 1ª rodada | Situação | Evidência |
|---|---|---|
| Normalização de ORDER validada em n=1 | RESOLVIDO, com correção | 5 specs decididas por autômato, refeitas sobre o autômato do parser. Generaliza em 3; o exemplo original estava errado e foi corrigido. |
| Polaridade pode inverter em silêncio | NÃO SE MATERIALIZA | 0 inversões em 23. Substituído por um risco maior e nomeável: 12 de 23 absorvem uso incorreto. |
| Taxa de reconhecimento de constraints desconhecida | MEDIDO — 45,5 % | Censo de 55 cláusulas conferido 55/55 contra o gabarito manual. Ressalva nova: o denominador do `api30` já é uma perda (§5.3). |
| M4 tem teto desconhecido | MEDIDO — 74 % hoje | 92 cláusulas normativas censadas; casamento 85/85 com o gabarito. |
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

A lista encolheu a três itens, e nenhum bloqueia a change.

- **Nenhum monitor do corpus foi executado sobre um traço de APK real.** Corrigido em 22/08/2026
  (R5): a redação anterior dizia "sobre um traço real", e isso é falso — o gh104 gerou monitores **das
  specs do corpus** (`rv-monitor-generator generate --specs-dir …/jca` e `…/jca_android`) e replicou
  traços sobre eles; o auto-teste sozinho replica 63 traços sobre o `jca`, e há 94 traços versionados
  e 162 arquivos de evidência por spec (§3). O que continua verdadeiro é o escopo restrito de V8 (que
  usou specs sonda) e o comportamento das 23 specs **sobre APK**, que segue não medido.
- **Posicionamento no autômato para as 19 cláusulas com `after`** foi conferido em 3 specs,
  classificado por polaridade e aridade nas outras 16. Se M4 exigir também a posição, o número de
  fiéis cai. V9 fechou o risco vizinho — nenhuma das 19 cai no conjunto vazio do
  `getStatesForMethods` — mas não este.
- **`SSLContextSpec` e `TrustManagerFactorySpec`**, as outras duas falhas do gate, não foram
  analisadas — provavelmente têm os mesmos artefatos.

**Acrescentado em 22/08/2026 (R5), depois da revisão externa e da verificação:**

- **Os números de M4 do §5.4/§7/§9 estão medidos em `d64f3a40`, não no `HEAD` de publicação.** A
  assinatura "64 sítios de `ExecutionContext`, 21 de `PredicateStore`, 5 de 23 arquivos migrados"
  ocorre em exatamente um dos 25 commits que tocam o diretório; hoje é **47 / 26 / 7** (45 / 28 / 8 na
  árvore de trabalho). O `predicate_graph.csv` confirma por segunda via: 85 linhas de dados lá, 73
  hoje. E o §7 diz "41 `condition(`" onde hoje são 36. A linha de teto `74,0 % / 58,7 %` foi calculada
  sobre um estado de substrato que já não vale. **Toda tabela precisa de carimbo de commit antes de
  virar proposta**, e o `SpecModel` ganhou campo de versão por isso (§12).
- **O gh105 move três "custos zero" durante a janela do componente.** Está em 36 de 74. A tarefa 5.1
  (aberta) cria a primeira spec multi-parâmetro do `jca_android`; a 6.6 (aberta) apaga a sobreposição
  `f1`/`f2` em que a testemunha do `CipherSpec` se apoia; a 5.3 cria as duas primeiras leituras
  negadas do corpus (`validateAbsent` tem hoje zero *call sites*) e a 6.4 apaga os 7 `remove()` em
  `@fail`.
- **`12 de 23 specs absorvem uso incorreto`** (§2) não foi remedido nesta rodada; uma das revisões
  externas conta 16. Fica em aberto.
- **`152/167` × `155`**: o §10 e o §8 discordam entre si, e a resolução dos 167 contra o `android.jar`
  não foi refeita. A aritmética do §10 foi auditada (§10); a resolução, não.
- **`28 das 55 cláusulas que mudam de veredito conforme a relação de igualdade`** (§10.3) não é
  derivável de nenhuma regra de contagem que esta rodada tenha conseguido reconstruir.
- **As 129 linhas de assinatura idênticas com e sem `android.jar`** (§8) foram medidas em modo lote e
  precisam de remedição sob leitor novo por regra.

**Posição honesta:** o desenho está certo, a viabilidade está demonstrada por execução nas duas
direções, e as métricas quantificadas vêm com denominadores que precisam ser declarados — agora são
três tetos, não dois. Nenhuma validação derrubou uma conclusão do documento; uma derrubou uma via, e
o substituto está medido. A direção da geração deixou de ser "peça a peça, produto nenhum
construído": há três specs geradas que compilam.

### O que a proposta tem de declarar, além do que já estava previsto

1. **O teto do oráculo** (§6), além dos dois anteriores — e com os **três modos** do §5.3, porque dois
   deles erram na direção oposta ao primeiro.
2. **O substrato de predicado como parâmetro** do gerador, não como dedução (§10.3).
3. **A política de acoplamento `ENSURES` ↔ `CONSTRAINTS`** (§10.3).
4. **A fronteira do parâmetro único**, com a recusa tipada como saída e o custo declarado como *zero
   em `HEAD`, ≥1 a partir da tarefa 5.1 do gh105* (§12).
5. **Um `CrySLModelReader` por regra** — por **determinismo**, não por denominador; e o número do
   corpus que daí sai é 30, não 31 (§8, §9).
6. **A conferência a posteriori contra o `android.jar`** no lugar da tentativa de fixar o classpath
   do parser (§8).

Acrescentados em 22/08/2026 (R5):

7. **O alfabeto não é disjunto**, e o modelo canônico guarda `events` ordenado com sobreposição, mais
   um autômato simbólico guardado sobre assinaturas (§12). Onde a guarda não for estática, a saída é
   `Unknown{OverlappingDispatch}`.
8. **A regra de contagem de cada censo publicado** — a AST e não o texto, para parâmetros (§12); R1
   para cláusulas de `CONSTRAINTS` (§5.3).
9. **O instantâneo**: commit carimbado em toda tabela de M4, e campo `version` no `SpecModel` (§12,
   §13).
10. **A classificação FIEL/PROJETADO/CONFLADO/AUSENTE é julgamento humano**, não medição derivável —
    e dar-lhe domicílio derivável é parte do que o componente entrega (§9).
11. **O componente é a metade estrutural** de um desenho de dois instrumentos; a metade comportamental
    é o arnês do gh104, que já existe (§3).

### Próximos passos sugeridos, em ordem de retorno

Os cinco primeiros da terceira rodada foram executados como V1–V10. O que sobra:

1. **Adicionar o checador de sanidade de `.mop`** (ids únicos + alfabeto da fórmula ⊆ ids). Vinte
   linhas sobre a AST, e V7 mostrou que é o **único** ponto do pipeline inteiro capaz de pegar essa
   classe — parser, gerador de monitor e compilador passam calados.
2. **Corrigir `PrettyPrinter.rsc:49,139`** no MetaCrySL e regerar `api30`. As cinco substituições
   léxicas medidas em §8 dizem exatamente o que consertar.
3. **Corrigir a precedência** em `scripts/gh105_order_gate.py:136-200` e em
   `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70`. O parser de `ORDER` do gerador da quarta
   rodada já traz a precedência correta e serve de referência executável.
4. **Restaurar as `CONSTRAINTS`** dos três templates base do MetaCrySL (§5.3). São ~9 cláusulas
   normativas apagadas do oráculo, e o efeito é sobre o denominador de M3, não sobre uma spec só.
5. **Guarda de duas linhas** em `CipherTransformationUtil.alg/mode/pad` — latente, sem urgência (§9).
6. **Abrir a issue no GitHub** e entrar no workflow OpenSpec. É o passo que o handoff condicionava ao
   fechamento das dez validações.

Acrescentados em 22/08/2026 (R5), em ordem de retorno:

7. **Rodar o arnês do gh104 contra as 5 specs globais e as guardadas, antes de escrever qualquer
   linha do componente.** É o teste mais barato do risco-mãe — medir o autômato declarado e concluir
   sobre o monitor que rodou —, e o instrumento já existe (§3).
8. **Corrigir `MacSpec.f2`**: `target(m)` sem `m` nas formais faz o pointcut nunca casar, e todo `Mac`
   fechado com `doFinal(byte[],int)` é acusado de `MAC-ORDER-00`. Nos dois conjuntos (§9).
9. **Dar diagnóstico ao `MOPParameters.add`** — um aviso de parâmetro duplicado, no molde do que já
   existe para evento duplicado. Onze specs do `generic` perdem declarações em silêncio hoje (§9).
10. **Depositar o arnês do §10 ou rebaixar a tabela** — feito o rebaixamento; o depósito continua
    pendente e é pré-requisito de qualquer número daquela seção entrar no artigo.
