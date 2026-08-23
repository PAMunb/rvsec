# F5 — o mapa completo, o parser que lia a regra ao contrário, e dois autômatos gêmeos

**Lote B8** · tarefas **7.1**, **7.2** e **7.3** · um commit · 2026-08-23

O lote fecha três tarefas do Grupo 7. A 7.1 completou o `order_alphabet_map.csv`, reparou o parser
de precedência do G-ORDER e reparou dois autômatos; a 7.2 mediu-se satisfeita e ganhou o portão
que faltava; a 7.3 retirou o `rvsec-mop-defsuses`.

O achado que governa o lote é este: **mapear honestamente as doze specs que faltavam levantou sete
divergências que o pulo escondia**. Nenhuma delas é nova no conjunto — todas estavam lá desde
antes desta change —, e o que o mapa fez foi torná-las dizíveis.

---

## 1. O parser: `,` liga mais fraco que `|`, e o Cipher era o único a saber

`CrySL.xtext:103-120` faz de `Sequence` (a vírgula) a produção mais externa, logo o **operador mais
fraco**: `a, b | c` é `a, (b | c)`. O gate lia ao contrário — a `tokenize` descartava a vírgula e o
resto era justaposição, a convenção da expressão regular — e das 33 regras do api30 só a `Cipher`
distingue as duas leituras, porque só ela deixa um `|` de topo ao lado de vírgulas de topo.

O reparo é o que `data/gh105/evidence/f1-order-gate-precedence.md` desenhou, e a medição confirma o
que ela previu: **as contagens não se movem** (6 passa / 4 diverge / 14 pula, antes e depois) e um
único testemunho se inverte.

| | antes | depois |
|---|---|---|
| `CipherSpec` | `f2` aceito pelo ORDER, recusado pela especificação | `g1 i1 u1` aceito pela especificação, recusado pelo ORDER |

O testemunho antigo dizia que a regra do Cipher permite um `doFinal()` avulso, sem `getInstance()`
nem `init()` — e que a especificação é estrita demais. Um reparo guiado por ele teria **afrouxado o
`ere` na direção errada**. O novo diz o que de facto diverge: o `fsm` aceita um Cipher que faz
`getInstance → init → update` e termina sem finalizar.

O teste que fixava a precedência foi invertido e ganhou o caso que a leitura velha recusava
(`g1 i2 f2`, o uso canônico), que é a regressão que ele existe para apanhar.

### O oráculo não é unânime, e isso fica registrado

`MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:67-68` — a gramática Rascal do **gerador** que produziu
`generated/api30/` — ordena `sequence` acima de `or`, o que em Rascal significa `,` ligando **mais
forte**: exatamente o que o parser fazia antes. O texto do Cipher é idêntico na fonte escrita à mão
(`samples/jca/base/Cipher.cryptsl:71`) e no gerado, e o `PrettyPrinter.rsc:110-118` só preserva os
parênteses explícitos, então o round-trip não deixa evidência de qual árvore o gerador construiu.

**Decisão do pesquisador (2026-08-23): seguir o Xtext.** Três razões medidas: a fonte é escrita no
dialeto CrySL do CogniCrypt, que é o consumidor que dá semântica às regras; sob a leitura Rascal a
ORDER do Cipher aceita `f2` sozinho e recusa `g1 i2 f2`, e as duas linguagens discordam em **795**
palavras de comprimento ≤ 3; e a leitura Xtext produz uma divergência verificável do `fsm`, ao passo
que a outra produzia um testemunho que teria guiado um reparo errado.

---

## 2. O mapa completo: 22 specs decididas, 2 pulos declarados

O arquivo cobria 10 das 24 specs. Foram escritas **61 linhas** para as doze que traduzem uma regra
api30, cada uma com a assinatura que a justifica e a linha da regra conferida contra o oráculo.

| | antes | depois |
|---|---|---|
| specs com linha | 10 | **22** |
| linhas de dados | 75 | **136** |
| G-ORDER | 6 passa · 4 diverge · 14 pula | **13 passa · 9 diverge · 2 pula** |

As duas que sobram não podem ganhar linha: `RandomStringPassword` (a ponte de fluxo sobre
`String.valueOf(Object)` e `String.toCharArray()`, que nenhuma regra do oráculo ordena) e
`IvChainJunction` (a junção do Grupo 5, cujo `ere` aceita toda sequência dos próprios eventos, o
que é a afirmação de que não ordena nada). O cabeçalho do mapa passa a declará-las, com a razão de
formato: `read_map` agrupa por spec e `build_automata` pula em `if not rows`, então **qualquer**
linha de dados — mesmo vazia — tiraria o arquivo do pulo e faria o gate procurar uma regra que não
existe. Um pulo declarado é prosa, nunca linha.

**Cinco specs passam de primeira**: `MacSpec`, `MessageDigestSpec`, `DHGenParameterSpecSpec`,
`GCMParameterSpecSpec`, `HMACParameterSpecSpec`.

### As sete divergências que o mapa levantou

| spec | testemunha | diagnóstico |
|---|---|---|
| `KeyManagerFactorySpec` | `g1 i1 gkm` | defeito do `fsm`, **reparado aqui** (§3) |
| `KeyPairSpec` | a sequência vazia | o `co?` da regra é opcional e o `ere` exige o construtor: um `KeyPair` vindo de `generateKeyPair()` seguido de `getPublic()` é acusado. O próprio `.mop` já media isto nos comentários e deferia para a 7.1 |
| `SecretKeySpec` | `d` | `destroy()`, que o `.mop` deliberadamente não observa (INV-INS-137: lança `DestroyFailedException` nas duas implementações que este conjunto vê, logo um advice `after returning` não tem caminho de execução). O formato do mapa não tem disposição do lado da regra — `order-unmapped` apaga evento do `.mop`, não símbolo da regra |
| `KeyStoreSpec` | `g2 l1` | o `.mop` não declara evento para `getInstance(String, String)`: os seus `g1` e `g2` casam a **mesma** sobrecarga de um argumento, sob guarda negada. Um programa que usa a sobrecarga com provider não é observado no `getInstance`, e o `load` cai no `@fail` — acusação contra programa conforme |
| `KeyGeneratorSpec` | `g1 g1 gk` | folga benigna do `g1+`/`g2+`, herdada do conjunto `jca` congelado |
| `CipherInputStreamSpec` | `c1 r1 c` | **alfabeto da regra**: o `c1` do api30 é o construtor de um argumento, que o android-30 declara `protected`. Nenhum sítio de aplicação o alcança e o pointcut pede `public`, corretamente. A regra ordena um evento que programa monitorado nenhum produz |
| `CipherOutputStreamSpec` | `c2 c` | o `fl` (`flush()`) está dentro do grupo de repetição obrigatória do `ere`, então um stream que só dá flush e fecha é aceito. A regra não declara `flush` em lugar nenhum, e a isenção não fabricou a divergência: revelou-a |

Nenhuma foi reparada — cada uma é mudança comportamental que a decisão 7 desta change proíbe entrar
sem medição própria, e duas (`KeyGeneratorSpec`, `KeyStoreSpec`) são herdadas do conjunto congelado.
Todas ficam na `gate_baseline.json`, que passa de 4 para 9 linhas de G-ORDER.

---

## 3. Os dois autômatos gêmeos, e a aresta que quase se reparou errado

`KeyManagerFactorySpec` e `TrustManagerFactorySpec` tinham a mesma aresta escrita duas vezes:
`gkm1 -> start` e `gtm1 -> start`, saindo do estado de aceitação. A api30 ordena `Gets, Init, gkm?`
e `Gets, Init, gtm?`, e as duas linguagens discordavam na palavra canônica.

**A primeira tentativa foi `-> final`**, o auto-laço no estado aceitante — uma palavra em cada
arquivo. Medida, ela fecha o testemunho relatado e abre outro:

```
G-ORDER com `-> final`:  KeyManagerFactorySpec   `g1 i1 g1 i1` aceito pela especificação
                         TrustManagerFactorySpec `g1 i1 g1 i1` aceito pela especificação
```

E, pior que a contagem: o auto-laço passa a aceitar `g1 i1 gkm gkm`, que o `?` da regra **recusa**.
O comentário do próprio `TrustManagerFactorySpec.mop` já dizia isso por escrito — "essa acusação é
fiel: a api30 ordena `Gets, Init, gtm?` e o `?` recusa a repetição também" — de modo que o reparo
teria silenciado uma acusação correta. **A prosa do arquivo era o oráculo, e discordava do reparo.**

O reparo que a regra descreve é um segundo estado de aceitação, terminal:

```
      final [
        gkm1 -> taken
      ]
      taken [
      ]

    alias match1 = final
    alias match2 = taken
```

Um alias é como esta notação diz que um estado aceita — e é o que o G-ORDER lê para decidir
equivalência. O `@match2` é vazio, e o arquivo diz por quê: a escrita sobre a fábrica é do
`@match1`, e a escrita sobre o array está no corpo do `gkm1`, o único lugar onde o array é visível
(um handler não vê parâmetro do evento que segue).

| medição | resultado |
|---|---|
| G-ORDER | as duas specs saem dos achados: 11 → **13 passa**, 11 → **9 diverge** |
| corpus (131 traces) | **131 unchanged** — o reparo não move nenhum programa |
| segunda tomada dos managers | continua acusada, dos dois lados |
| tabela de transição, lida no monitor gerado | `gkm1 = {4, 4, 4, 2, 4}` e `gtm1 = {4, 2, 4, 4, 4}`, caindo no estado 2, que é `@match2` |

A consequência que a tarefa 7.1 antecipava — "as duas escritas movem-se para o ponto de aceitação"
— realiza-se sem mover código: com a aresta reparada, o corpo do evento **é** o ponto de aceitação,
porque a transição entra no estado que aceita. O que impede a escrita de morar no handler não é a
colocação e sim o array, e as duas linhas do `predicate_graph.csv` passam a registar isso.

### Duas sondas novas no corpus (129 → 131)

`KeyManagerFactorySpec-managers-taken-twice.txt` e a gêmea para o TMF. Elas foram escritas para
medir a tentativa `-> final` e **ficam**, agora com o papel inverso: são a guarda de regressão
contra exatamente o reparo errado que quase entrou. Foram construídas sobre a keystore carregada,
para que `generatedKeyStore` fique calada e a acusação de ordem seja a única coisa que a trace pode
reportar — a primeira versão, com `init(null, ...)`, arrastava um `NOBS-00` legítimo junto.

---

## 4. A 7.2 estava feita, e o que faltava era o portão

Medido sobre a árvore: **112 acusadores ↔ 112 códigos**, zero acusador sem código, zero código
órfão, zero âncora `file_line` derivada, e o message gate verde. É a quarta tarefa desta change a
verificar-se em vez de se executar.

O que faltava era o que o B6 e o B7 pediram por escrito: **nenhum portão conferia a âncora**. O B6
achou seis âncoras derivadas e o B7 moveu cinco, e as duas vezes só porque alguém reancorou o
arquivo inteiro por script. A `code-anchor` entra no `gh104_message_gate.py`, ao lado da
`code-bijection` que já existia, e compara o `file_line` de cada linha com a linha de onde o código
é de facto emitido.

Auditada como o achado 100 pede — mudar uma âncora de `CipherInputStreamSpec.mop:25` para `:24` na
cópia produz exatamente um achado, com o texto que nomeia as duas linhas.

---

## 5. A 7.3: o módulo que ninguém chamava

`rvsec-mop-defsuses` (5 arquivos Java, 1735 linhas, das quais 1528 são um visitor do JavaParser e a
sua especialização) foi para `rv-android/backup/gh105-retired/rvsec-mop-defsuses/`, com um
`RETIREMENT.md` que diz o que era e por que sai. Medido antes de mover: **dois** pontos de pom (a
linha de `<modules>` e o próprio artefato), **zero** dependências no reator inteiro (63 poms), e
três referências de código/config — a entrada da skip-list do `check_no_legacy_mop.py`, o
comentário dela e o mapa de módulos do `CLAUDE.md` do reator. As três saíram; a do skip-list porque
`backup/` já é ignorado por outra entrada, então mantê-la seria referência pendurada.

O que o módulo computava lendo código-fonte, esta change deriva das especificações e mantém sob
versão: o `predicate_graph.csv` tem uma linha por sítio de predicado, com cláusula, mecanismo e
disposição, e quatro portões decidem contra ele.

---

## 6. Um achado que vale mais que as tarefas: a evidência do harness já não reproduzia

O `git diff --stat data/gh105/evidence/harness/` é a medida que este trabalho usa para dizer "não
mexi em mais nada". Depois deste lote ela acusou **dez** arquivos, e eu tinha tocado duas specs.

Não é ruído aleatório, e foi medido em três passos: duas réplicas idênticas sobre o mesmo monitor
dão resultado **idêntico**; duas gerações independentes do mesmo conjunto dão um monitor
**byte a byte igual**; e, regenerando a evidência **a partir do `HEAD`**, com a mesma toolchain de
hoje, **dez dos 24 relatórios não reproduzem o que está commitado**.

As classes não mudam — 60 unchanged / 31 moved / 31 introduced / 7 removed nos dois casos. O que
muda é o texto do envelope: o campo `ev=` dentro da mensagem, e num caso o envelope inteiro. E muda
**dos dois lados**, inclusive no lado A, que é a pré-imagem congelada.

Separando as duas coisas com a mesma toolchain:

| comparação | arquivos que diferem |
|---|---|
| evidência commitada × `HEAD` de hoje | **10** (deriva pré-existente) |
| `HEAD` de hoje × árvore de hoje | **2** — `KeyManagerFactorySpec`, `TrustManagerFactorySpec` |

A pegada real deste lote são as duas specs que ele tocou. A deriva é de outra coisa — a hipótese
mais provável é uma recompilação do `TraceRunner`/`ErrorCollector` entre a passagem que escreveu a
evidência e hoje — e fica registrada aqui porque **enquanto ela existir, o `git diff` da evidência
não decide sozinho o que uma passagem tocou**. Quem quiser usá-lo como medida tem de regenerar do
`HEAD` primeiro e comparar contra isso, que custa uma passagem de harness.
