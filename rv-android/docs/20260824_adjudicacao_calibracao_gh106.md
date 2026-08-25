# Adjudicação da calibração do componente de conformidade (gh106, G12) — 24/08/2026

Este documento registra **todas** as divergências reais encontradas ao calibrar o componente
MOP↔CrySL contra as oito grandezas medidas por rotas independentes, e como cada uma foi
adjudicada. Ele existe porque uma divergência resolvida em silêncio é indistinguível de um
instrumento ajustado até concordar — e, seis meses depois, ninguém consegue separar as duas coisas
(INV-CONF-14, D-13, RISK-005).

A regra que governa tudo o que está abaixo: **uma divergência é um achado, não um sinal de
ajuste.** Quando o componente e um alvo discordam, medem-se os dois lados, publicam-se as duas
medições com as duas regras de contagem, e adjudica-se com evidência. Não se mexe no componente
para ele concordar, e não se afrouxa uma asserção.

## Sumário

| # | Divergência | Lados | Adjudicação |
|---|---|---|---|
| 1 | Duas implementações de pareamento dentro do componente (23 × 22) | `M4PredicateCorpusTest` × `SpecRulePairing` | **`SpecRulePairing` está certo**; a aproximação por nome simples contava `Cipher.crysl` duas vezes |
| 2 | A tabela do M3 omite duas especificações que o M1 compara | M1 (21) × M3 (19) | **Não é divergência de pareamento**: as duas regras pareadas têm `CONSTRAINTS` vazio |
| 3 | `101/71` e `117/87` cláusulas sob outras regras de contagem | `spec.md` §M3 × três rotas independentes | **Irreproduzíveis** — e `101` é impossível em princípio; publicado o valor do componente com a regra dele |
| 4 | O alvo 6 só reproduz sob injetividade, que o INV-CONF-11 não enuncia | invariante escrito × regra aplicada | **Dívida de artefato** para `/opsx:update`; o portão nomeia a regra que de fato aplicou |
| 5 | Aposentadoria do `NotWiredException`/`NOT_WIRED` | consequência de ligar o `calibrate` | Código morto **removido** (P3), com cópia em `backup/gh106/` |

**Os oito alvos foram reproduzidos.** Nenhum ficou em estado *mismatch não adjudicado*, que é a
condição de fechamento que o RISK-005 pede. As divergências 1 e 2 são internas ao componente — duas
partes dele discordando entre si — e foram encontradas exatamente porque o portão obriga a comparar.

## Carimbos (D-17): por corpus, nunca um escalar por rodada

| Corpus | Repositório | Carimbo da **rota** | Carimbo **desta rodada** |
|---|---|---|---|
| os cinco corpora `.mop` | `rvsec` | `5fbe8173` | `6192b57a` — **diferem** |
| `generic` | `rvsec` | `5fbe8173` | `6192b57a` — **diferem** |
| `jca_android` | `rvsec` | `5fbe8173` | `6192b57a` — **diferem** |
| `CrySL-Rules` | `rvsec-cognicrypt` | `f2f4d3b` | `f2f4d3b` |
| `android.jar` | SDK | `android-30` | `android-30` |

O `rvsec` andou quatro vezes durante a mudança; o `rvsec-cognicrypt` não anda desde maio (e o
diretório `CrySL-Rules` não muda desde `801e330`, de 04/12/2025). É precisamente esse caso que uma
coluna única de carimbo esconderia, e é por isso que o relatório imprime as duas lado a lado.

**As oito rotas foram re-executadas no HEAD atual**, e nenhuma derivou: o `Census.java` devolve
`215/215` e os mesmos *buckets*; o `Binding.java` devolve as mesmas cinco especificações; o
`V3Fresh.java` devolve `47 de 49` com as mesmas duas falhas; o censo R1 em texto cru devolve
`119`/`80`; o mapa de alfabeto declara os mesmos dois *skips*; e a passagem nova do
`rv-monitor-generator` devolve as mesmas cinco especificações sem `MapOfMonitor`. Nada foi assumido
como tendo "carregado" do commit em que o alvo foi fixado.

## Divergência 1 — duas implementações de pareamento (tarefa 12.0)

**O que discordava.** O G07 construiu `core/metric/SpecRulePairing.java`: pareamento por tipo
declarado, **injetivo**, desempate por cobertura de assinaturas. Ele alcança **22 de 24**. O censo
de M4 do G09 não o chamava: mantinha um mapa próprio, do nome simples da regra para a regra, e
alcançava **23**. O G09 declarou a aproximação em vez de escondê-la, então isso é dívida de
integração e não defeito do grupo — mas M1 e M4 passaram a reportar sobre conjuntos de pares
diferentes, e um relatório cujas duas métricas discordam sobre *quais especificações foram
comparadas* não pode ser publicado.

**O item que diferia, nomeado.** `IvChainJunction.mop:67` declara `IvChainJunctionSpec(Cipher c)` e
`CipherSpec.mop:47` declara `CipherSpec(Cipher c)` — o mesmo tipo declarado, byte a byte. Uma
*função* por tipo declarado pareia os dois com `Cipher.crysl`; a injetividade manda a regra para a
especificação que cobre mais das assinaturas declaradas por ela, que é `CipherSpec`.

**As duas regras de contagem.**

- Rota de registro (`SpecRulePairing`): *pelo tipo declarado; nomes dobram para o nome simples só
  quando um dos lados não é qualificado; o pareamento é injetivo, e uma regra que duas
  especificações declaram vai para a que cobre mais assinaturas dela sob R-M1, depois para a que
  declara mais eventos, depois para a primeira em ordem lexicográfica.*
- Aproximação (removida): *especificações cujo nome simples do tipo declarado é o nome simples de
  uma regra que carrega* — sem injetividade.

**Adjudicação: a implementação injetiva está certa.** A razão não é de estilo. Todo agregado do
componente é enunciado sobre "as regras pareadas" — o denominador que o M3 conta, o conjunto sobre
o qual o M4 conta predicados — e uma regra lida duas vezes é uma regra contada duas vezes em cada
um deles. Sob a aproximação, as cláusulas de `Cipher.crysl` entravam no `absent` do M4 **duas
vezes**: uma contra `CipherSpec` e outra contra a junção. O número antigo superestimava o que o
corpus deixa de implementar. Além disso, a leitura injetiva é a única que torna verdadeira a outra
figura publicada na proposta — "12 das 22 **regras** pareadas".

**O deslocamento, medido antes e depois, no mesmo corpus e no mesmo commit** (é isso que torna a
mudança visível em vez de silenciosa):

| | pares | present | absent | inverted | linhas | derivadas | fração derivada |
|---|---:|---:|---:|---:|---:|---:|---:|
| antes (aproximação por nome) | 23 | 50 | 53 | 0 | 123 | 103 | 0,837 |
| depois (`SpecRulePairing`) | 22 | 44 | 44 | 0 | 106 | 88 | 0,830 |

As nove cláusulas que saem de `absent` são o ponto: eram a contagem dupla de `Cipher.crysl`. A
fração derivada quase não se move, que é o esperado ao remover um par duplicado — e não uma classe
de julgamento.

**O que passou a existir para isso não voltar.** `OnePairingImplementationTest` roda um `compare`
completo sobre `jca_android` e afirma, **sobre os arquivos emitidos** e não sobre objetos em
memória, que M1, M2, M3 e M4 nomeiam as mesmas especificações. A checagem é feita no artefato porque
é o artefato que alguém recebe: se a tabela do M3 nomeia uma especificação que a do M4 não nomeia,
a discordância está no que foi publicado, faça o código o que fizer.

## Divergência 2 — o M3 omite duas especificações que o M1 compara

**O que discordava.** Escrevendo o teste acima, o conjunto do M1 (21 especificações) e o do M3 (19)
não bateram. Faltavam no `constraint_table.csv`: `HMACParameterSpecSpec` e `KeyPairSpec`.

**Adjudicação: não é divergência de pareamento, e a asserção que dizia que era estava errada.**
`HMACParameterSpec.crysl` e `KeyPair.crysl` têm seção `CONSTRAINTS` vazia — `0` cláusulas sob R1,
confirmado pelo censo em texto cru. O M3 é uma tabela de **linhas por cláusula**: sem cláusula, não
há linha, e a especificação desaparece do arquivo sem nunca ter deixado de ser comparada. A asserção
foi corrigida para exigir `M3 ⊆ M1` e para **nomear** as duas ausências esperadas, em vez de ser
afrouxada para uma tolerância. Nomear é o que mantém a asserção uma medição: se um dia sumir uma
terceira, o teste fica vermelho.

## Divergência 3 — `101/71` e `117/87` não reproduzem (tarefa 12.10)

**O que discordava.** O `spec.md` §M3 e a tarefa 8.6 afirmam que, sob outras regras de contagem, o
corpus dá `101/71` (dividindo `&&`) ou `117/87` (dividindo os dois lados de `=>`).

**As três rotas independentes**, que concordam dígito a dígito sobre as 49 regras *upstream*: a
rota textual do G08, a rota da fachada CrySL (`114` para as 47 que carregam, mais `5` pelas duas que
não parseiam, `= 119`) e uma contagem em texto cru, em Python, sem nenhum dos dois parsers.

| regra de contagem | total (49 regras) | pareadas (22) |
|---|---:|---:|
| **R1** — uma cláusula por `;`, comentários removidos, `&&` **não** dividido | **119** | **80** |
| dividindo `&&` (6 ocorrências em `CONSTRAINTS`) | **125** | **86** |
| dividindo os lados de `=>` (26 ocorrências) | **145** | **99** |

**Adjudicação: irreproduzíveis, e `101` é impossível em princípio.** Dividir uma cláusula só pode
*aumentar* uma contagem; um total "dividido" abaixo do total não dividido (119) não pode estar
certo. Como hipótese — registrada como hipótese, e não como resultado — o par publicado deve ter
sido medido sobre o corpus `api30` abandonado, que apaga cláusulas em relação ao *upstream*; é a
única forma de um total dividido cair abaixo de 119. Não vale a pena perseguir: o D-06 abandonou
aquele oráculo. Seguindo a tarefa 12.10, as duas figuras são registradas como irreproduzíveis, com
o valor do componente **e a regra dele** ao lado, exatamente como se fez na Fase 0 com `129`,
`12 de 23`, `10/26` e `28 de 55`. O portão imprime esse registro em toda rodada, e o
`CountingRule` já o carrega no Javadoc. **Dívida de artefato:** as duas figuras precisam ser
corrigidas ou retiradas do `spec.md` via `/opsx:update` (G14 14.7-bis).

### Nota de precisão sobre a rota do alvo 6

Os artefatos da mudança dizem que os dois não pareados estão "nomeados na coluna `disposition` do
`order_alphabet_map.csv`". A coluna `disposition` existe e é por linha; os dois *skips*, porém, são
declarados em **prosa no cabeçalho** do arquivo, e de propósito: qualquer linha de dados, mesmo
vazia, tiraria a especificação da condição de *skip* (`build_automata` pula em `if not rows`) e
faria o portão procurar uma regra que não existe. A rota é a mesma e continua sendo um artefato que
o componente não produz; o que muda é a descrição, que o alvo agora enuncia corretamente. Item
menor de dívida de artefato, junto com os do `/opsx:update`.

## Divergência 4 — o alvo 6 só reproduz sob uma regra que o invariante não enuncia

O INV-CONF-11 diz que o pareamento é "por tipo declarado" e **não** diz que é injetivo, nem enuncia
o desempate. Como mostra a divergência 1, sem injetividade o componente responde `23 de 24` e o
alvo 6 (`22 de 24`, pela coluna `disposition` do `order_alphabet_map.csv`) falharia. Um alvo que só
reproduz sob uma regra não escrita não é um alvo calibrado.

**Adjudicação: dívida de artefato, e o portão nomeia a regra que de fato aplicou.** O invariante
precisa ser emendado via `/opsx:update` (G14 14.7-bis) para dizer *injetivo, com desempate derivado
de assinaturas e nunca de nomes*. Enquanto isso, o campo `note` do alvo 6 e a regra de contagem que
o componente publica dizem em voz alta que a injetividade é o que faz o número fechar — de modo que
ninguém leia `22 de 24` como consequência do invariante como está escrito hoje.

## Divergência 5 — `NotWiredException` e `ExitCode.NOT_WIRED` ficaram sem produtor

Ligar o `calibrate` (tarefa 12.8) removeu o último sítio de construção do `NotWiredException`. O
próprio Javadoc do `ExitCode` já previa: *"não é um modo de falha de uma ferramenta terminada e
espera-se que desapareça"*. Pelo P3, código superseded é apagado inteiro, sem *shims*: a classe foi
copiada para `backup/gh106/NotWiredException.java` e removida, junto com a constante `NOT_WIRED` e
o braço de `catch`. O teste do CLI que a exercia foi reescrito para a checagem que continua valendo
— `calibrate` recusa um corpus ilegível **antes** de medir qualquer coisa, com
`CORPUS_READ_ERROR`, em vez de responder "0 de 0, reproduzido", que seria o verde vazio que o
componente inteiro existe para eliminar.

## Os oito alvos, com as duas medições e as duas regras

Todos **REPRODUZIDOS**. As regras de contagem completas estão em
`CalibrationTargets.java` (rota) e em `CalibrateRun.java` (componente); o portão imprime as duas em
toda rodada.

| # | Alvo | Rota (classe) | Valor da rota | Valor do componente | Regras de contagem |
|---|---|---|---|---|---|
| 1 | leitura dos cinco corpora `.mop` | `Census.java` (sonda independente) | `215 files, 215 ok, 0 fail` | idem | rota: `SpecExtractor.parse` não lança · componente: `MopLifter.read` devolve `MopLift` |
| 2 | multi-parâmetro em `generic` | `Census.java` | `93 de 118`, `{1:25, 2:39, 3:28, 4:18, 5:7, 6:1}` | idem | ambas: `spec.getParameters().size() > 1`; a segunda lê a contagem que o *lift* carregou |
| 3 | multi-parâmetro em `jca_android` | `Census.java` | `0 de 24` | idem | idem |
| 4 | regras *upstream* que carregam | `V3Fresh.java` | `47 de 49` (`OAEPParameterSpec`, `SSLEngine`) | idem | ambas: um `CrySLModelReader` novo por regra, sem normalização léxica |
| 5 | denominador do M3 sob R1 | censo R1 em texto cru + tabela §2.2 do mapeamento | `80 de 119` | idem | rota: um `;` por cláusula, texto cru, sem parser · componente: um `ISLConstraint` da fachada, mais R1 no texto das duas que não parseiam |
| 6 | pareamento `.mop` ↔ regra | `order_alphabet_map.csv`, os dois *skips* declarados (artefato comitado) | `22 de 24` (`IvChainJunction`, `RandomStringPassword`) | idem | rota: as 24 menos os dois *skips* declarados no cabeçalho do arquivo — prosa, e nunca linha de dados, de propósito — com a razão escrita para cada um · componente: `SpecRulePairing`, por tipo declarado e injetivo |
| 7 | ligação parcial de parâmetro | `Binding.java` | `5 de 22` (`HMACParameterSpecSpec`, `KeyPairSpec`, `KeyStoreSpec`, `PBEKeySpecSpec`, `RandomStringPassword`) | idem | ambas: eventos cujo `getMOPParametersOnSpec()` é vazio, sobre as 22 que declaram parâmetro |
| 8 | sem `MapOfMonitor` | monitores **regerados** (artefato regerado) | `5 de 24` (`CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`, `KeyStoreSpec`, `RandomStringPassword`) | idem | rota: campo `MapOfMonitor<XMonitor> X_..._Map` no `MultiSpec_1RuntimeMonitor.java` · componente: proxy da AST do M0.1 |

**Sobre o alvo 8, que é o mais caro e o mais informativo.** O M0.1 sempre disse, no próprio texto
da regra, que é um *proxy* e que o oráculo verdadeiro é o monitor gerado. A passagem do
`rv-monitor-generator` sobre uma cópia em *scratch* das 24 especificações foi feita, e as duas
medições dão as mesmas cinco especificações. A concordância agora é **medida**, não presumida — que
é exatamente a diferença que o D-18 comprou ao custo de uma geração. As especificações são copiadas
para o *scratch* antes de gerar porque o gerador move os `.rvm` que o JavaMOP deixa *ao lado das
specs*: gerar no diretório do corpus escreveria dentro dele, o que o INV-CONF-12 proíbe.

**Sobre o alvo 5, e o que ele não é.** O `constraint_table.csv` comitado (`25 de 55`, ancorado no
`api30`, julgamento humano sobre `jca_android`) **não** é rota de calibração: é uma reconciliação
histórica rotulada. Calibrar o M3 contra ele mediria concordância com uma leitura humana anterior, e
não correção — e é uma das tabelas que esta mudança existe para substituir (RISK-006).

## Composição das rotas (RISK-006)

Seis dos oito alvos vêm de sondas independentes, um de artefato comitado e um de artefato regerado.
**Nenhum** vem de "a própria regra do componente reenunciada" — as duas grandezas que estavam
escritas assim (o pareamento "por nome" e o censo de `MapOfMonitor` pelo proxy da AST) foram
reencaminhadas pelo D-18, e um teste afirma essa propriedade em vez de deixá-la para revisão:
`test_no_target_restates_the_component`. Um alvo classificado como
`SAME_ALGORITHM_RESTATEMENT` é publicado como **checagem de consistência interna rotulada** e não
conta como calibração.

## Como a supressão por métrica funciona (tarefa 12.4)

Cada alvo declara **uma** métrica pela qual responde. Um *mismatch* suspende a publicação daquela
métrica e de mais nenhuma — não há cascata. Uma métrica errada não pode suprimir sete certas (um
portão que reprova rodadas inteiras ensina seus usuários a desligá-lo), e uma métrica certa não pode
licenciar uma errada. O relatório imprime a decisão por métrica com o alvo que causou cada recusa
nomeado, e a exceção `CalibrationMismatch` carrega o relatório **inteiro** — as discordâncias e as
concordâncias — para que as duas informações de que o leitor precisa cheguem juntas.

## Reprodução

```bash
# o portão, sozinho: mede as oito grandezas e confere cada uma contra a rota que produziu o alvo
java -cp <classpath> br.unb.cic.rvsec.crysl.crysl.cli.ConformanceCli calibrate \
  --mop-root $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources \
  --rules-dir <...>/rvsec-cognicrypt/CrySL-Rules \
  --commit 6192b57a --oracle-commit f2f4d3b \
  --monitor $SCRATCH/out/MultiSpec_1RuntimeMonitor.java

# a passagem de geração que dá a rota do alvo 8 (escreve só em scratch)
mkdir -p $SCRATCH/specs $SCRATCH/out
cp $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/*.mop $SCRATCH/specs/
cd rv-android && uv run rv-monitor-generator generate \
  --specs-dir $SCRATCH/specs --output $SCRATCH/out

# a suíte, com o alvo 8 ligado
RVSEC_GENERATED_MONITOR=$SCRATCH/out/MultiSpec_1RuntimeMonitor.java \
  mvn -o -f rvsec/rvsec-crysl/pom.xml test
```

Os testes que leem o oráculo ou os monitores regerados levam a etiqueta `oracle-dependent`, que o
workflow de CI exclui pelo nome — o verde que a CI imprime fica honestamente rotulado. Localmente,
quem não tem o insumo recebe um *skip* que **nomeia o caminho que faltou**, em vez de um verde
silencioso.

---

# Adenda de 24/08/2026 (noite) — os cinco achados da revisão, reparados e medidos

A `/rv-code-reviewer` devolveu **REQUEST CHANGES** sobre a change `gh106-mop-crysl-conformance`.
Cada um dos cinco achados mexe — ou podia mexer — em número publicado. Isso é legítimo: o que se
reparou aqui é **defeito do instrumento**, não ajuste do instrumento para concordar com um alvo,
que é o que o INV-CONF-14 proíbe. O preço dessa distinção é que **cada reparo foi medido antes e
depois e o portão de calibração foi re-executado no fim**. As oito grandezas continuam
reproduzindo (`8 alvos, 0 mismatches`), e isso está registrado abaixo junto com o que se moveu.

Carimbo desta passagem: `rvsec` **`6192b57a`**, `rvsec-cognicrypt` **`f2f4d3b`**, JDK 25.
Nada foi commitado. Os `.mop`, o oráculo e os `.csv` de `data/jca_android/` foram lidos e nunca
escritos (INV-CONF-12; a verificação está no fim desta adenda).

## Achado 1 — a coluna publicada que mudava sozinha (bloqueante)

**O que estava errado.** Três coleções imutáveis do JDK — `Set.of` em
`M3Constraints.TRANSFORMATION_HELPERS` e `TYPE_TEST_HELPERS`, `Map.copyOf` em `M3Result.byIdiom`,
`Set.copyOf` em `Event.signatures` — têm ordem de iteração **sorteada uma vez por JVM**. Nenhuma
delas é um detalhe interno: as três chegam a arquivo emitido.

**A medição do defeito.** Seis JVMs separadas, mesmo corpus (`jca_android` em `6192b57a`), mesmo
comando `compare`, comparando os arquivos emitidos com os dois carimbos de relógio (`mop_read_at`,
`oracle_read_at`) normalizados — eles são hora de parede por projeto, não conteúdo:

| arquivo | conteúdos distintos em 6 corridas |
|---|---|
| `constraint_table.csv` | **2** |
| `conformance_report.json` | **6** |
| `predicate_graph.csv`, `divergence_record.csv`, `m1_events.md`, `m2_order.md`, `m4_predicates.md` | 1 (estáveis) |

O que variava, nomeado: (a) a coluna `mop_line` das 8 linhas de `CipherSpec` × `Cipher.crysl:88`,
alternando entre `CipherSpec:85` e `CipherSpec:159` — `externalHelper` devolve o **primeiro** nome
que encontra, e `CipherSpec` chama `isValid` na linha 85 e `alg` na 159; (b) a ordem das quatro
chaves de `byIdiom` no JSON; (c) os campos `evidence`/`site` das mesmas linhas.

**O reparo.** Cada ordenação publicada passou a ter uma regra escrita, em vez de depender da ordem
de iteração: `TRANSFORMATION_HELPERS`/`TYPE_TEST_HELPERS` viraram `List` em **ordem de
precedência** (`isValid` antes de `alg`, `mode`, `pad` — a checagem da transformação inteira decide
a cláusula, `alg` decide só uma parte dela) e `externalHelper` passou a receber `List`;
`byIdiom` virou `EnumMap` não modificável, que itera na ordem de declaração do enum;
`Event.signatures` passou a preservar a ordem em que o *lifter* a montou (`LinkedHashSet` não
modificável), que é a ordem em que o *pointcut* escreve as assinaturas.

**A prova de determinismo.** **Nove** JVMs separadas depois do reparo: **todos os sete arquivos
byte-idênticos em todas as nove**, com a mesma normalização dos dois carimbos de relógio. Um teste
novo (`DeclaredOrderTest`, em `-core`, 3 casos) afirma a propriedade que torna o sorteio
irrelevante — a ordem de iteração é a ordem declarada pelo chamador — porque dentro de **uma** JVM
o sorteio já foi tirado e nenhum teste consegue observá-lo.

**O que se moveu.** Uma coluna publicada: o `mop_line` das 8 linhas de `CipherSpec` é agora sempre
`CipherSpec:85`, antes era 85 **ou** 159 conforme a corrida. Nenhum agregado (M0–M4) mudou.

**A chave de pareamento, medida separadamente.** `MopLifter.declaredTypeOf` faz
`signatures().stream().findFirst()`, e o resultado é a chave do pareamento (alvo 6). Sondado em
**oito** JVMs separadas sobre os 215 arquivos dos cinco corpora, o tipo declarado saiu
**byte-idêntico nas oito** já antes do reparo: toda especificação sem parâmetro tem, no primeiro
evento com assinatura, assinaturas de um **único** tipo declarante — inclusive as duas com duas
assinaturas (`Object_MonitorOwner`, `ServerSocket_Backlog`). O risco era real e **latente**; o
reparo o remove sem mover o pareamento. Nenhuma especificação mudou de tipo declarado por causa
deste achado.

## Achado 2 — o `+` de subtipo que nunca era removido em `PointcutExpander.resolve`

**O que estava errado.** `namedTypes` removia o `+` do padrão de subtipo do AspectJ; `resolve` —
por onde passam o dono do *pointcut*, seus parâmetros e seu tipo de retorno — não removia. As duas
rotas discordavam sobre o mesmo nome escrito. `CharSequence+` não é nome de tipo: é
`CharSequence` mais a regra de casamento "e qualquer subtipo dele". Mantido, o nome erra **todas**
as buscas a que é submetido — os `import` do arquivo, a sonda `java.lang` e, por fim, o índice do
`android.jar` — e o erro era publicado como `Unknown{UnresolvedSignature, mode: CLASSE-AUSENTE}`:
o defeito do expansor vestido de ausência na plataforma Android. É a mesma classe de erro do
`java.lang` já reparado no G06.

**Antes e depois, por rota:**

| grandeza | antes | depois |
|---|---|---|
| M0.3, censo de `CLASSE-AUSENTE` em `generic_new` | **82 recusas em 23 especificações** | **73 em 19** |
| M0.3 em `generic` | 121 em 38 | 121 em 38 (o corpus não escreve `+`) |
| M0.3 em `jca`, `jca_android`, `jca_android_bug_predicate` | 1 (`HMACParameterSpecSpec`) | 1 (idem) |
| M1 sobre `jca_android`: cobertura | 119 de 137 | 119 de 137 |
| M1: `ruleOnly` / `mopOnly` | 18 / 18 | 18 / 18 |
| tipo declarado (chave do pareamento) | 7 arquivos de `generic_new` com `+` | os mesmos 7, corrigidos |
| conjunto de pares | `jca_android` 22 de 24; `generic_new` 0 | **idênticos** |

As quatro especificações que perdem **todas** as recusas são `CharSequence_UndefinedHashCode`,
`Comparable_CompareToNull`, `Comparable_CompareToNullException` e `Object_MonitorOwner`;
`ListIterator_Set` cai de 6 para 5 e `Map_UnsafeIterator` de 15 para 14.

As duas listas de diferença do M1 não mudam de **tamanho**, mas duas entradas mudam de **grafia**:
`javax.crypto.Cipher.getInstance(java.lang.String,Object+)` passa a
`...,java.lang.Object)`, e o mesmo em `KeyGenerator`. É o que o reparo deveria fazer e nada além.

Os sete tipos declarados corrigidos: `Set+`→`Set`, `CharSequence+`→`java.lang.CharSequence`,
`Closeable+`→`Closeable`, `Comparable+`→`java.lang.Comparable` (dois arquivos),
`Object+`→`java.lang.Object`, `Collection+`→`Collection`. **O pareamento não se moveu** porque
nenhuma regra CrySL declara esses tipos: `generic_new` tinha 0 pares antes e tem 0 depois. Um
teste novo em `MopLiftCorpusTest` afirma o invariante sobre os cinco corpora — nenhuma assinatura
levantada guarda `+` em qualquer posição de tipo.

## Achado 3 — a negação entre parênteses que `PredicateIdioms.negatedAt` não via

**O que estava errado.** O leitor só reconhecia `condition(!EC.instance().validate(…))`. Os
corpora escrevem também `condition(!(EC.instance().validate(…)))`, e essa forma levantava como
`POSITIVE` — uma aresta do M4 publicada como presente que é, na verdade, invertida. Um sítio em
cada corpus de substrato A, a mesma linha nos dois: `PBEParameterSpecSpec.mop:47`.

**Antes e depois:**

| grandeza | antes | depois |
|---|---|---|
| censo de referências negadas no *lift* (`jca` / `jca_android` / `bug_predicate`) | **6 / 5 / 25** | **7 / 5 / 26** |
| M4 em `jca`: presentes / ausentes / invertidas | 54 / 46 / 6 | **53 / 46 / 7** |
| M4 em `jca_android_bug_predicate` | 61 / 28 / 23 | **60 / 28 / 24** |
| M4 em `jca_android` | 43 / 43 / 0 | 43 / 43 / 0 |
| `predicate_graph.csv`, polaridade `negated` (`jca` / `bug_predicate`) | 9 / 27 | 10 / 28 |

Uma aresta do M4 muda de estado em cada um dos dois corpora de substrato A: de **presente** para
**invertida**. É exatamente o que se esperava — a referência é a mesma, a polaridade é que estava
lida ao contrário.

**As duas asserções foram atualizadas para a realidade corrigida, com o motivo escrito ao lado, e
nenhuma foi afrouxada:** `MopLiftCorpusTest.test_negated_references_per_corpus` (a tripla
6/5/25 → 7/5/26) e `M4PredicateCorpusTest.test_polarity_is_read_on_both_substrates` (6 → 7). Os
comentários dizem que nenhum arquivo dos corpora mudou e que a contagem anterior era subcontagem do
leitor.

## Achado 4 — o M3 devolvendo `absent` onde o leitor falhou

**O que estava errado, e a doutrina.** `consequentValues` devolve conjunto vazio quando não
consegue ler o átomo de valor da cláusula, e `boundNames` devolve vazio quando não encontra
operando nenhum. Buscar na especificação por um conjunto **vazio** de valores, ou de nomes, não
casa com nada por construção: a busca **não pode** ter sucesso, então o fracasso dela não diz nada
sobre a especificação. Cair daí em `absent` publica limitação do instrumento como defeito do
sujeito, que é a porta que o `Unknown{UnrecognizedConstraint}` existe para fechar.

**O reparo.** As três rotas que caíam em `absent` (`transformationPart`, `valueList`, `arithmetic`)
passam pelo `unreadable(...)`, que emite `Unknown{UnrecognizedConstraint}` e conta no teto do
instrumento. Dois testes novos em `M3ConstraintsTest` afirmam a regra.

**O vetor M3 corrigido — e ele não se moveu:**

| | antes | depois |
|---|---|---|
| implementadas / ausentes / recusadas, sobre 80 | **31 / 36 / 13** | **31 / 36 / 13** |
| por idioma (A / B / C / D) | 12 / 7 / 4 / 8 | 12 / 7 / 4 / 8 |
| recusas por etiqueta | `UntranslatableConstraint` 10, `UnrecognizedConstraint` 3 | idem |
| teto do instrumento | 3 | 3 |
| veredictos de `constraint_table.csv` | 36 `CRYSL-NAO-IMPLEMENTADO`, 13 `NAO-DERIVADO`, 16 `IGUAL`, 15 `MOP-MAIS-PERMISSIVO` | idem |

**Por que zero, e a discordância com a revisão — que é achado e não é absorvida.** A revisão diz
que **34 das 80 linhas** estão afetadas. Medido, com a regra de contagem escrita: *uma linha é
falha de leitura quando a rotina que fornece a chave de busca devolve vazio* — `consequentValues`
vazio para `VALUE_LIST`/`TRANSFORMATION_PART`, `boundNames` vazio para `ARITHMETIC`. Sob essa
regra, das 80 linhas exatamente **1** é falha de leitura (uma cláusula `TRANSFORMATION_PART` de
`Cipher.crysl`, cujo último átomo `VC:` vem sem lista de valores), e essa **não** chega à porta do
`absent`, porque a busca pelo auxiliar externo casa antes dela. Logo, zero linhas mudam de
veredicto.

Os 34 da revisão são `32 ARITHMETIC-ausentes + 2 INSTANCE_OF-ausentes`. Sob a regra "toda busca que
não encontrou é falha de leitura", as 34 mudariam — e a categoria `absent` ficaria com 2 linhas,
o que contradiz a taxonomia de três vias que a própria classe declara. Para as 32 `ARITHMETIC` há
contra-evidência direta: `boundNames` extrai os operandos **corretamente** (`{data, offset, len}`,
`{prePlainText, prePlainTextOffset, prePlainTextLen}` etc.), e o Javadoc de `SpecificationIdioms`
registra que `GCMParameterSpecSpec` **apagou de propósito** os conjuntos
`offset >= 0 && len >= 0 && src.length >= offset + len`, com a medição que justificou a deleção
escrita no comentário do arquivo. Ausência medida, não cláusula ilegível.

**A colocação alternativa, medida e recusada.** Pôr a guarda **antes** da busca pelo auxiliar
externo moveria aquela única linha de `Cipher` de `D_EXTERNAL_HELPER` para recusada: o vetor
passaria a **30 / 36 / 14** de 80 e o teto do instrumento a 4. Não foi feito. O achado nomeia a
porta do `absent`; fechar também a porta do `implemented` mudaria **o que é acusado** com base num
juízo que o achado não faz, e essa é a segunda espécie de mudança — a que se adia e se registra.

## Achado 5 — os quatro comentários que descreviam outra coisa (P4)

Três eram história de migração e viraram descrição do estado atual: `MopLift.java` ("até isto
viajar para cá, um auxiliar da árvore de teste de `-crysl` reparseava cada arquivo…"),
`package-info.java` ("a reavaliação pós-troca-de-oráculo confirmou o corte…") e `RoundTripGate.java`
("promovido de portão interno a métrica publicada").

O quarto é o sério e foi verificado contra a fonte. O comentário de `MopLifter.read` afirmava que
`MOPNameSpace.init()` torna o *lift* de um arquivo independente do que foi levantado antes dele.
**Não torna.** Lido em `javamop/src/main/java/javamop/util/MOPNameSpace.java:44-46`, `init()` faz
`used = false` e **nada mais**: as três listas acumuladoras (`userVariables`, `mopVariables`,
`mapVars`) sobrevivem à chamada. O comentário foi corrigido para dizer o que o código faz — a
chamada devolve a permissão de registrar novos identificadores, que `addUserVariable()` recusa
depois que `getMOPVar()` levanta a bandeira ("Cannot update MOPNameSpace after once used").

**O código não foi mexido, e ele não está errado:** sem a chamada, o primeiro *lift* que gerasse um
nome faria o *parse* de todo arquivo seguinte lançar. O nulo medido (215/905/381 com e sem a
chamada) se mantém porque nada no caminho do *lift* chega a `getMOPVar()` — o nulo é medição, não
prova de que a linha seja morta.

## O portão de calibração, re-executado depois de tudo

`ConformanceCli calibrate --commit 6192b57a --oracle-commit f2f4d3b --monitor <scratch>` →
**8 alvos, 0 recusas de auto-consistência, 0 `mismatches`**, `exit 0`. Os oito, com o mesmo valor
dos dois lados:

| alvo | grandeza | rota × componente |
|---|---|---|
| T1 | arquivos `.mop` que levantam | `215 de 215 ok` × idem |
| T2 | multi-parâmetro em `generic` | `93 de 118` × idem |
| T3 | multi-parâmetro em `jca_android` | `0 de 24` × idem |
| T4 | regras *upstream* que carregam | `47 de 49` × idem |
| T5 | denominador do M3 sob R1 | `80 de 119` × idem |
| T6 | pareamento | `22 de 24` × idem |
| T7 | ligação parcial de parâmetro | `5 de 22` × idem |
| T8 | sem `MapOfMonitor` (monitores **regerados** nesta passagem) | `5 de 24` × idem |

**Nenhum alvo se moveu.** Os quatro que poderiam ter se movido, e por quê não: T1 (o `+` e a
negação não impedem nenhum arquivo de levantar), T4 (não se tocou no leitor CrySL), T5 (o
denominador é do oráculo, e o M3 não mudou de vetor) e T6 — o mais exposto, porque o Achado 1
mexe na chave de pareamento e o Achado 2 mexe no tipo declarado de sete arquivos; os sete são de
`generic_new`, que não pareia com regra nenhuma, e `jca_android` continua em 22 de 24.

O alvo 8 exigiu geração de monitor: as 24 especificações foram **copiadas** para *scratch* antes de
gerar, porque o gerador move os `.rvm` que o JavaMOP deixa ao lado das *specs* e gerar no diretório
do corpus escreveria dentro dele (INV-CONF-12).

## A suíte, nos dois modos, com as contagens reais

| módulo | corrida local completa (com `RVSEC_GENERATED_MONITOR`) | passo da CI (`-DexcludedGroups=oracle-dependent`) |
|---|---:|---:|
| `rvsec-crysl-core` | **171** | **171** |
| `rvsec-crysl-mop` | **59** | **58** |
| `rvsec-crysl-crysl` | **102** | **38** |
| **total** | **332**, 0 falhas, 0 *skips* | **267**, 0 falhas |

Sem a variável do monitor a corrida local é 331 mais um *skip*, e o *skip* nomeia o caminho que
faltou. Os seis testes novos (5 em `-core`, 1 em `-mop`) mudaram os totais, então a divisão
declarada no comentário do `ci.yml` — que era `65 de 326` — foi **re-medida e re-escrita** para
`65 de 332`, com a tabela por módulo atualizada. Uma divisão declarada que derivou é pior do que
uma não declarada, porque o leitor confia nela.

## Somente leitura sobre os corpora (INV-CONF-12)

`git status --porcelain` sobre `rvsec/rvsec-mop/src/main/resources/` (os cinco corpora `.mop`):
**vazio**. Sobre `rvsec-cognicrypt`: nenhuma modificação — há um único arquivo não rastreado,
`results/cognicrypt_metrics (Cópia).csv`, com data de **04/12/2025**, muito anterior a esta
sessão. Sobre `rv-android/data/jca_android/`: `divergence_record.csv` aparece modificado, com
carimbo de **20:12 de hoje**, anterior ao início deste trabalho (22:17) — nenhuma execução desta
adenda escreveu em `data/`, todas as saídas de `compare` foram para *scratch*.

## O reator inteiro, re-executado depois dos cinco reparos

A adenda acima mede o componente. O reator que o contém não tinha sido reconferido desde os
consertos, e o aprendizado nº 25 desta linhagem existe justamente porque `-DskipTests` **não** pula a
*compilação* dos testes: uma fonte de teste quebrada trava o `install` de 48 módulos, e o componente
publica agora seis testes que não existiam quando o reator foi medido pela última vez.

```
cd $W/rvsec && mvn clean install -DskipMopAgent      # testes ligados, JDK 25
```

| grandeza | na emissão do handoff | agora |
|---|---:|---:|
| módulos | 48 | **48**, todos `SUCCESS` |
| testes | 2 034 | **2 040** |
| falhas / erros | 0 / 0 | **0 / 0** |
| *skips* | — | **1** |

Os seis testes a mais são exatamente os seis que os reparos trouxeram (cinco em `-core`, um em
`-mop`), e a soma fecha sem sobra: `2 034 + 6 = 2 040`. O único *skip* é o alvo 8, que nesta corrida
não recebeu `RVSEC_GENERATED_MONITOR` — ele pula **nomeando o caminho que faltou**, que é a diferença
entre um insumo ausente e um verde silencioso. Com a variável ligada o mesmo alvo roda e reproduz,
como a seção da calibração registra.

**A contagem é a do `Tests run:`, nunca a do código de saída.** Registrado porque uma soma pelos
XMLs de `target/surefire-reports/` devolveu 331 nesta sessão contra os 332 da corrida viva: aquele
diretório acumula relatórios de execuções anteriores e responde por uma corrida que não é a que se
acabou de fazer.
