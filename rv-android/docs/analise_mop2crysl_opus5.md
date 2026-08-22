# Revisão externa — componente de conformidade MOP↔CrySL

**Revisor:** Claude Opus 5 (`claude-opus-5`)
**Data:** 21 de agosto de 2026
**Alvo:** `docs/20260821_conformidade_mop_crysl.md` (1283 l.), `docs/20260821_validacoes_conformidade_mop_crysl.md` (484 l.), `docs/20260821_auditoria_conformidade_mop_crysl.md` (505 l.) e os corpora
**Commit da árvore no início da revisão:** `0290caf5` (`gh105` em **35/74** tarefas; era 30/74 no plano e 34/74 na auditoria — moveu duas vezes desde)
**Escopo:** análise. Nenhum arquivo sob revisão foi modificado. Sondas em `/tmp/claude-1000/`.

---

## 1. Veredito

O desenho **procede, emendado** — mas as emendas atingem mais fundo do que a auditoria de consistência sugere, e não são de tabulação. O núcleo algorítmico está certo e eu o defendo contra as alternativas que o §D7 do handoff convida: modelo canônico, autômato em vez de AST de regex, equivalência por busca no produto com testemunha mínima, e `Unknown` tipado são as escolhas corretas, e model checker, prova SMT ou mineração de regras seriam piores. O que está errado é outra coisa: **o modelo canônico não consegue representar o corpus para o qual foi desenhado** (§4.1), **a decisão de arquitetura mais cara do documento resolve um conflito que não existe** (§4.2), **existe um eixo de divergência que as quatro métricas contam com o sinal trocado** (§4.3), e **o instrumento que enxergaria a classe de defeito que este corpus de fato produz já está construído na árvore e o plano não o menciona** (§4.4).

Nenhum desses quatro é uma correção de número. Os três primeiros mudam o §12; o quarto muda o escopo. Em compensação, a parte do documento que passou por execução reproduz-se: eu recontei do zero e o censo M3 (62/55 e a matriz A/B/C/D/Ausente inteira), o censo M4 (92 = 54/36/2, 32 predicados, aridade 59/33, denominadores 73/54/44) e a precedência invertida do `ORDER` saíram exatos. O padrão que a auditoria nomeou — *"correto onde mediu, frágil onde tabulou"* — confere, e eu acrescento que ele tem uma terceira faixa: **frágil onde raciocinou sem executar**, que é de onde vêm os quatro achados acima.

---

## 2. Método

Onze subagentes paralelos, mais verificação própria e o servidor MCP `sequential-thinking` (**disponível**; usado para a síntese e para o D7).

| Frente | O que verificou | Modo |
|---|---|---|
| D1a | Recontagem de M4 (§5.4) e dos dez números do §10 | recontagem de fonte primária |
| D1b | Recontagem de M3 (§5.3), teto do oráculo, escada léxica do §8 | recontagem de fonte primária |
| D1c | Precedência do `ORDER` nas três gramáticas; raio de explosão | leitura de gramática + execução do gate |
| D2 | Coerência interna: referências cruzadas, correções pela metade | varredura do documento × registro de validações |
| D3 | Arquitetura: módulos, costura JSON, modelo canônico, portão | leitura + **sonda Maven/JVM executada** |
| D4 | Validade metodológica: eixos, tetos, vacuidade, comparabilidade | análise + corpus |
| D5 | Execução: parse 214, contagens refutadas, testemunha do `CipherSpec` | **pipeline real** |
| D6 | Contribuição científica, trabalho relacionado, o paper do TSE | leitura do fonte do paper |
| D8 | Adversarial: quebrar N1–N4, o portão, o estado estático do parser | **sondas executadas** |
| — | Revisão da própria auditoria de consistência | adjudicação independente |
| — | Achados próprios (§4.1–§4.4, §7) | fonte primária + `sequential-thinking` |

**Declaração de independência.** Esta análise não consultou as revisões paralelas de outros modelos presentes em `docs/analise_mop2crysl_*.md`. Um subagente foi lançado para resumi-las e foi **abortado antes de produzir saída** quando ficou claro que o mesmo prompt fora dado a vários modelos e que a independência é o produto. Uma contaminação acidental ocorreu e é declarada: o agente do D6, procurando o fonte do paper do TSE, tropeçou num desses arquivos e citou uma linha sobre o nome do arquivo de saída; **esse item foi descartado** e a §9 abaixo argumenta o ponto pela estrutura do próprio plano.

---

## 3. Os quatro achados que mudam o desenho

Estes são os achados desta revisão que não estão no plano nem na auditoria de consistência. Cada um traz a evidência primária.

### 3.1 O modelo canônico não representa o corpus — o alfabeto não é um alfabeto  ·  **ALTA**

O §12 fixa `order : DFA mínimo sobre Labels` e `events : Map<Label, Set<Signature>>`. Isso pressupõe que **cada chamada observada contribui com exatamente uma letra**. No corpus, não contribui.

**A cadeia, medida:**

1. `api30/Cipher.cryptsl:93-105` declara `f1..f7`; `:107` define `FINWOU := f2 | f4 | f5 | f6 | f7`. O `f1` (`doFinal()` sem argumento) e o `f3` **não** estão em `FINWOU` — um `doFinal` sem argumento exige `updates` antes. Isso é deliberado na regra.
2. `jca_android/CipherSpec.mop` declara os eventos `f1, f2, f3, f5, f6, f7` — **não há `f4`**. Os ids do `.mop` espelham os da regra, e o papel do `f4` é absorvido pelo curinga do `f2`:
   ```
   :198  event f1 … call(public byte[] Cipher.doFinal())
   :205  event f2 … call(public byte[] Cipher.doFinal(..))
   ```
   O pointcut do `f2` cobre as sobrecargas que devolvem `byte[]` — `doFinal()`, `doFinal(byte[])`, `doFinal(byte[],int,int)` — isto é, `{crysl.f1, crysl.f2, crysl.f4}`. Logo **a imagem do `f1` é subconjunto próprio da imagem do `f2`**.
3. **Nenhum dos dois tem `condition(...)`** (verificado; sonda em `/tmp/claude-1000/mine/overlap.py`). Ao contrário do par `g1`/`g4` que o §4.1 analisa — onde a guarda torna o disparo mutuamente exclusivo —, aqui nada os separa. Pela regra que o próprio handoff registra como medida (*"Two events on the same join point both fire, in declaration order"*), **uma chamada `doFinal()` emite a palavra `f1 f2`**, não a letra `f2`.
4. O `fsm` do próprio `.mop` (`CipherSpec.mop:261-264`) dá, a partir de `s2`, transições para `f2, f5, f6, f7` — **não há transição de `f1`**.

**Consequência imediata: a testemunha `g1 i1 f1` do §5.2 está refutada pelo próprio `fsm` da spec, antes de qualquer execução.** O §5.2 conclui que o MOP *aceita* um `doFinal` sem `update` "porque o pointcut `doFinal(..)` também casa `doFinal()`". Esse raciocínio aplica o mapa de alfabeto como **função** (`doFinal()` ↦ `f2`, logo aceito) e esquece que o `.mop` também declara um `f1` literal, que dispara primeiro e não tem transição. A auditoria de consistência refutou a testemunha **por execução** (sondas A/B/C); o ponto aqui é mais forte e mais barato: ela é refutável **por leitura estrutural**, e sobreviveu a quatro rodadas porque o modelo mental do documento é o modelo do §12.

**A generalização é o achado.** O erro não é um deslize; é a saída do modelo:

- **M2-decl** compara um autômato sobre um alfabeto que não modela a entrada real.
- **M2-eff não salva.** O §5.1 prefere M2-eff justamente por ler o monitor gerado — mas a multiplicidade mora na **camada de tecelagem** do AspectJ, acima das tabelas `Prop_1_transition_*`. Ler as tabelas não vê dois advices no mesmo join point.
- O `order_alphabet_map.csv` **assume disjunção**, e o plano diz isso (`§5.2`: *"N4 quebra uma premissa do `order_alphabet_map.csv`, que assume cada evento MOP disjunto dos demais"*).
- O plano lista **N4 · sobreposição de pointcuts** como normalização, mas a trata como problema de **rotulagem** (o `f2` mapeia `{f1,f2,f4}`), nunca como problema de **multiplicidade**. São coisas diferentes e só a segunda é fatal.

**Pior: o mapa induzido não é sequer estático.** No par positivo/negativo do §10.3 (`KeyStoreSpec.mop:43,51` são dois eventos com pointcut **byte-idêntico**, separados só pela `condition`), qual das duas letras sai é decidido por uma guarda sobre estado do monitor — foi exatamente isso que o V8 mediu para `g1`/`g4` no `MessageDigestSpec`. Nenhum `Map<Label,Set<Signature>>` léxico, ordenado ou não, exprime isso.

**Raio de explosão, medido por mim nos dois corpora.** Varrendo os 23 `.mop` de cada conjunto atrás de pares com subsunção `(..)` não-guardada:

| conjunto | specs com par subsumido e não-guardado |
|---|---|
| `jca_android` | **1** — `CipherSpec` (`f2` ⊃ `f1`) |
| `jca` (congelado) | **1** — `CipherSpec`, idêntico |

Os outros 16 specs com mais de um evento no mesmo nome de método são disjuntos por aridade/tipo, ou são os gêmeos guardados do §10.3. **Severidade: ALTA para o modelo, BAIXA para o corpus** — mas note que o único caso é a spec mais complexa do conjunto, é a que o plano usa como exemplo-bandeira, **e está também no `jca` congelado**, de onde vêm as medições publicadas.

**Emenda.** Trocar a forma armazenada. Em vez de DFA sobre rótulos com um mapa à parte:

```
events : List<Event{ label, pointcut, Set<Signature>, guard: Constraint?, declIndex }>   // ORDENADA
order  : autômato simbólico sobre Signature, transições com guarda opcional
```

e derivar o DFA sobre rótulos como **vista calculada**, aplicando o morfismo ordenado e guardado. Formalmente o que se quer comparar é `h⁻¹(L)` onde `h : Σ_sig* → Label*` leva cada assinatura à **concatenação, em ordem de declaração, de todo rótulo cujo pointcut a casa**. Morfismo inverso preserva regularidade, então isto continua decidível e continua barato — o modelo é que não tinha onde guardar o `h`. Assim o N4 vira **passo de construção** em vez de normalização aplicada a um modelo que já perdeu a informação.

### 3.2 A costura JSON resolve um conflito que não existe  ·  **ALTA**

O §12 toma sua decisão de arquitetura mais cara — **três processos, JSON como formato de intercâmbio, "os dois nunca dividem JVM"** — com esta justificativa: *"`CrySLParser` traz Guava 33.5.0-jre e Guice 7, enquanto `javamop` vive num reator que pina Guava 19.0 por causa do Soot, e a incompatibilidade falharia em runtime."*

**Medido: `javamop` não puxa Guava e não puxa Soot.** Árvore offline completa (`mvn -o dependency:tree` em `$W/rvsec/javamop`): `rv-monitor` (+ plugins de lógica → `scala-library:2.11.12`), `aspectjtools/weaver/rt`, `commons-lang3`, `commons-io`, `jcommander`, `jackson-databind`, junit. `grep -nE "guava|soot"` na árvore: **nenhuma ocorrência**. O Guava 19 é declarado em `rvsec-agent/pom.xml:61` e nos módulos `gator` — **nenhum no caminho da comparação**.

Logo há **exatamente um** consumidor de Guava no componente (o `CrySLParser`), e conflito de versão exige dois.

**E o pino do `dependencyManagement` da raiz — que é o mecanismo real, porque alcança transitivas — já foi neutralizado pelo próprio V10**, que sobrescreve `guava.version` no pom-pai do componente. Sonda de módulo **único** com `javamop` + `CrySLParser` no mesmo classpath, executada:

```
$ mvn -o dependency:tree   → 59 deps; com.google.guava:guava:jar:33.5.0-jre:compile  (única guava)
$ java -cp out:$CP OneJvm MessageDigestSpec.mop MessageDigest.crysl
MOP   ok: javamop.parser.ast.MOPSpecFile
CrySL ok: java.security.MessageDigest  order-nodes=5
guava from: .../guava/33.5.0-jre/guava-33.5.0-jre.jar
```

Os dois parsers rodam na mesma JVM, com uma cópia do Guava, sem shading e sem classloader.

**O erro epistêmico é o mesmo que o documento critica em outros.** O V6 "validou" a costura mostrando que **três processos funcionam**. Nunca rodou o controle: *um processo falha?* É controle ausente — e o documento tem a frase certa para isso em outro lugar (*"'parseou' não é oráculo de sanidade"*).

**O que se perde com a fronteira de processo**, contra a afirmação *"nada de essencial se perde"*:

1. **A testemunha.** As testemunhas do §5.2 são palavras sobre rótulos que precisam ser rematerializadas como assinaturas concretas **nos dois lados ao mesmo tempo** (`getInstance(t); init(ENCRYPT,k); init(DECRYPT,k); doFinal(pt)`). Numa JVM o núcleo tem os handles vivos de `MOPSpecFile` e `CrySLRule` e caminha até o nó da AST. Através de JSON só tem o que o *lift* serializou — e a serialização do V6 grava `ORDER` como `{formalism, text}`, delegando ao núcleo o parse do `ere`/`fsm`. Ou seja: **o núcleo passa a conter um segundo parser de ERE**, que é exatamente a duplicação que o §3 diz que o componente existe para acabar.
2. **Fidelidade do DFA no fio.** Nada fixa numeração de estados, então isomorfismo de DFA mínimo e estabilidade de diff entre execuções não são garantidos; e o alinhamento dos dois alfabetos fica por igualdade de string de rótulo, sem garantia de esquema de que N1–N4 foram aplicados dos dois lados.
3. **O `Unknown` tipado degrada.** Um erro de parse dentro do lift vira código de saída + stderr, não item tipado no modelo — e o §12 chama o `Unknown` de não-negociável.
4. Rastro de pilha, breakpoint e execução incremental (3 JVMs × bootstrap do Xtext/Guice a cada invocação).

**Emenda.** Um módulo, uma JVM, entrega de objeto. Manter o JSON estritamente como **artefato de saída** — que o §12 já queria — preserva 100% do benefício de "modelo canônico inspecionável" e 0% do custo da costura.

### 3.3 Há um quarto eixo de divergência, e as métricas o contam com o sinal trocado  ·  **ALTA**

O §2 monta dois eixos: **vertical** = infidelidade de tradução (ruído, é o que se mede) e **horizontal** = adaptação Android (deliberada, é a contribuição). Falta um terceiro fenômeno, com sinal oposto ao primeiro: **o tradutor humano corrigindo silenciosamente defeitos do oráculo.**

**A evidência, medida por mim nas duas pontas.** O upstream escreve as quatro cláusulas de limite do `Cipher` com `>=`:

```
CrySL-Rules/Cipher.crysl:122   length[prePlainText]  >= prePlainTextOffset + prePlainTextLen;
CrySL-Rules/Cipher.crysl:123   length[preCipherText] >= preCipherTextOffset;
CrySL-Rules/Cipher.crysl:127   length[plainText]     >= plainTextOffset + plainTextLen;
CrySL-Rules/Cipher.crysl:128   length[cipherText]    >= cipherTextOffset;
```

O `api30` escreve:

```
generated/api30/Cipher.cryptsl   length(pre_plaintext)  >= pre_plain_off + len;      ← certa
                                 length(pre_ciphertext) <= pre_ciphertext_off;       ← INVERTIDA
                                 length(plainText)      <= plain_off + len;          ← INVERTIDA
                                 length(cipherText)     <= ciphertext_off;           ← INVERTIDA
```

O plano registra a inversão (§10.5) e a localiza no template base. **Não registra que o upstream as tem certas** — isto é, que não se trata de perda de cláusula mas de **corrupção de operador** em relação à fonte de verdade. Isso é mais grave que o "teto do oráculo" do §6, que só fala em cláusulas *ausentes*.

**Agora o cruzamento.** Das seis cláusulas `length[x]` do censo M3, quatro são do `Cipher` e estão classificadas **AUSENTE**; a sexta é `SecretKeySpec.cryptsl:29` (`length(keyMaterial) >= off + len`), correta no oráculo, e **está implementada** (idioma B, `SecretKeySpecSpec.mop:101`).

Ou seja: **o humano implementou a única cláusula de limite que o oráculo enuncia corretamente e omitiu as três que ele enuncia ao contrário.** O §10.5 chega a notar a assimetria e a chama de *"a assinatura de um filtro humano que o gerador não tem"* — mas não tira a conclusão. Sob M3 como está, as quatro contam como AUSENTE: quatro débitos contra a fidelidade da tradução, dos quais **três são a tradução estando certa e o oráculo errado**.

**Por que isto não é mais um teto.** Os três tetos do §6 são limites sobre **agregados**, e toda a maquinaria do §6 — denominador declarado, vetor `26/54/73/92`, proibição de escalar único — existe para impedir que o número agregado seja lido pior do que a realidade. Aqui o problema é **inversão de sinal item a item**: a métrica pontua uma decisão de engenharia correta como infidelidade. Nenhuma higiene de denominador conserta isso, porque o defeito não está no denominador.

Categorias que a divergência `S_android × R_android` pode ter, e que as quatro métricas fundem em duas:

| | o oráculo está certo | o oráculo está errado |
|---|---|---|
| **spec concorda** | FIEL | **defeito do oráculo copiado** (crédito indevido) |
| **spec discorda** | infidelidade (o ruído a medir) | **reparo humano** (débito indevido) |

**Emenda, e é barata.** Rodar M3/M4 contra **os dois oráculos** — `api30` (= R_android) e `CrySL-Rules` (= R_java) — e tratar a **discordância entre oráculos** como sinal de primeira classe. Cada item ganha veredito de 2 bits, `(spec × R_android)` × `(R_android × R_java)`, e as quatro combinações nomeiam exatamente as quatro causas acima.

O §2 adverte contra rodar `S_android` contra `R_java` porque isso **conflata** os eixos. A advertência está certa para uma comparação isolada; a conclusão tirada dela ("nunca olhar o `R_java`") não está. Olhar os dois **e diferenciá-los** é o que **separa** os eixos — que é o objetivo declarado.

**Custo medido:** as duas famílias de nomes alinham. Das 23 specs, **21 têm regra no `api30` e no upstream** (as duas de fora são `IvParameterSpec`, cujo arquivo `.mop` tem nome irregular, e `RandomStringPassword`, que não tem regra nenhuma); e as 33 regras do `api30` têm, **todas as 33**, contraparte upstream. O §8 já mede que o `CrySLParser` lê 47 das 49 regras upstream. É um segundo *lift* de um corpus que já está na árvore e já parseia.

### 3.4 O instrumento que veria esta classe de defeito já existe, e o plano não o cita  ·  **ALTA**

O §3 (*"Metade já existe, ad hoc"*) inventaria os precursores: três implementações da comparação de `ORDER`, cinco leitores de CrySL, 14 de 18 scripts parseando `.mop` por regex, ~10.400 linhas de Python. **Fica de fora o maior e o único não-ad-hoc:**

| artefato | tamanho | o que faz |
|---|---|---|
| `rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` | **1255 l.** | Replica um traço de chamadas de API através de **um snapshot de monitor gerado** e registra o que ele acusa. Gramática de traço própria (`bind`, `->`, placeholders); resolve cada chamada contra os pointcuts **do próprio snapshot**, lidos do descritor `MultiSpec_1MonitorAspect.json`, para que os dois lados não precisem partilhar alfabeto; recarrega o monitor por traço porque o gerado guarda as tabelas de indexação em campos `static`. |
| `scripts/gh104_diff_harness.py` | 489 l. | Replica um arquivo de traços através de **dois** snapshots e classifica cada diferença em `unchanged` / `moved` / `removed` / `introduced`. Tem `--selftest` com mutações autorais, uma por veredito. |
| `data/gh104/traces/` | **94 traços** | corpus de traços versionado |
| `data/gh104/evidence/harness/` | **162 arquivos** | evidência por spec, 23 por rodada |

E o docstring do próprio arnês enuncia a tese em termos que são exatamente o argumento contra as quatro métricas do plano:

> *"A static gate measures the artefact. This measures what the artefact does, which is the only way to see the two failures the lineage shipped as successes: gh100's wrapper merge, which removed twelve silently discarded wrappers and reported `wrappersGenerated 96 -> 84`; and gh101's automaton repairs, which removed eighteen all-`fail` rows and moved the accusation to the call that follows. Both are invisible to a gate that counts rows."*

**O projeto já aprendeu, duas vezes e ao custo de dois defeitos entregues como sucesso, que portão estrutural não vê regressão de comportamento.** M1, M2, M3 e M4 são **todas estruturais**. E o defeito do §3.1 acima é precisamente desta família: invisível a qualquer variante do M2, visível ao arnês — que foi, aliás, como a auditoria de consistência o pegou.

**Correção de uma afirmação do §13.** A lista "o que ainda não foi verificado" abre com: *"Nenhum monitor do corpus foi executado sobre um traço real. V8 mediu … com specs sonda que replicam a forma do corpus, **não com o corpus**."* A segunda metade está errada: o gh104 gerou monitores **das specs do corpus** e replicou traços sobre eles — o auto-teste sozinho replicou 63 traços sobre o `jca`, e há 94 traços versionados, com evidência por spec para o `jca_android` (`e1-*.md`, `e4-*.md`, 23 arquivos cada). O que continua verdadeiro é o resto da frase — *"o comportamento das 23 specs sobre APK real, não"*. A entrada de risco superdimensiona a lacuna ao ignorar um instrumento existente.

**Emenda.** Duas opções, e a escolha é de escopo, não técnica:

1. **Mínima e honesta:** o §3 passa a inventariar o arnês; o §12 declara que o componente é a metade **estrutural** de um desenho de dois instrumentos cuja metade **comportamental** já existe; e o §13 corrige a frase.
2. **Mais forte, e é a que eu recomendaria:** promover o traço a oráculo do M2. Em vez de decidir equivalência só por busca no produto sobre autômatos declarados, enumerar palavras curtas sobre o alfabeto partilhado, executá-las pelo `TraceRunner` e comparar o veredito do monitor com o veredito do autômato da regra. Isso mede `L(monitor real)` em vez de `L(autômato declarado)`, e é a única variante que vê `condition` removendo a chamada do autômato, co-disparo de pointcut, `@match` sem `@fail`, pointcut morto e parâmetro não ligado. O custo alegado — um programa de apoio por tipo JCA — **já foi pago**: é o que os 94 traços são.

---

## 4. Achados por dimensão

### D1 — Fatos e números

**O que se reproduz exatamente**, recontado do zero e de fonte diferente da que o documento usou:

| Afirmação | Veredito |
|---|---|
| 92 cláusulas normativas = 54 `ENSURES` + 36 `REQUIRES` + 2 `NEGATES` | **CONFIRMADO**, tabela por arquivo |
| 32 predicados distintos; aridade 59/33, máximo 2 | **CONFIRMADO** (59+33 = 92) |
| 73 em regras com `.mop`; 19 em regras sem; 11 specs que não existem | **CONFIRMADO** |
| 26/73 = 35,6 % · 26/92 = 28,3 % · 54/73 = 74,0 % · 54/92 = 58,7 % · 73/92 = 79,3 % · 26/54 = 48 % | **CONFIRMADOS, os seis** |
| 19 bloqueios = 17 aridade-2 em `ExecutionContext` + 2 negadas no `MacSpec` | **CONFIRMADO por derivação independente** (27 aridade-2 cobertas − 8 já migradas = 19; as 2 negadas são `Mac.cryptsl:82,84`). É o número mais bem sustentado do §5.4. |
| 62 cláusulas de `CONSTRAINTS` nas 33 regras; 55 nas pareadas | **CONFIRMADO**, tabela por arquivo, e conferido de segunda via pelo `constraint_table.csv` |
| Matriz A/B/C/D/Ausente inteira (linhas 17/12/7/6/5/5/3; colunas 11/3/4/7/30) | **CONFIRMADO**, somas e 10 classificações conferidas contra os `.mop` |
| 45,5 % = 25/55 e 25,5 % = 14/55 | **CONFIRMADOS** |
| 8 de 44 cadeias realizadas; 3 no nível de `Property`; idênticas em `jca` e `jca_android` | **CONFIRMADO**, conjuntos byte-idênticos nos dois corpora e em dois commits |
| 167 eventos e 61 agregados no `api30` | **CONFIRMADO**, tabela por arquivo |
| 158 linhas de alias (Signature 55, Cipher 29, Mac 24; zero para KeyStore/SSLContext/SecureRandom) | **CONFIRMADO** |
| 9 das 11 allow-lists idênticas, 8 de fato mais permissivas | **CONFIRMADO**, e o "8 = 9 − 1" fecha (a exceção é `GCMParameterSpec`, teste literal sobre `Integer`) |
| Precedência: `\|` liga mais forte que `,` | **CONFIRMADO** em três fontes independentes |

**O que não se reproduz:**

| # | Afirmação | Veredito | Evidência |
|---|---|---|---|
| N1 | §5.4 "**SEM-BASE 16**" | **NÃO DERIVÁVEL** | Reconstruções dão 15 (sítio cujo `Property` nenhuma cláusula pede) ou 21 (todo `remove()` em `@fail`). Nenhuma dá 16. A submetade "8 são `remove()` em `@fail`" **confere exatamente** no commit medido. |
| N2 | §5.4 classificação FIEL 26 / PROJETADO 13 / CONFLADO 5 / AUSENTE 29 | **NÃO DERIVÁVEL** | Nenhum artefato da árvore atribui classe a cláusula. O `predicate_graph.csv` **não pode** produzi-la por construção: `gh105_predicate_graph.py` nunca lê um `.cryptsl`, e o próprio docstring diz que as colunas de julgamento *"no analyzer can re-derive"*. Só FIEL é aproximável, e dá **27**, não 26. |
| N3 | §10 "**152/167** eventos resolvem para assinatura única" | **REFUTADO** | Resolvidos os 167 contra o `android.jar` da API 30: **155/167** (153 únicos + 2 falsos-negativos do conferidor). E 167 − 152 = 15 não resolvidos, mas o texto só nomeia 12 (a política do `_`); 3 ficam sem destino. A submetade "12 eventos de `_`" e "140 dos 167 sem tipo de retorno" **conferem exatamente**. |
| N4 | §10 "**87/92**" com "**4 lacunas** do `PredicateStore`", e §10.4 "reduzido de 19 para 4" | **REFUTADO por contradição interna** | 92 − 87 = **5**. As três frases não podem valer juntas. Importa porque §10.4 conclui "catorze acima do teto humano" a partir de 87 − 73. |
| N5 | §10 "**16/55** sem decisão + **47/55** sob política declarada" | **REFUTADO como partição** | 16 + 47 = 63 > 55. Ou são aninhados (nunca dito) ou uma das linhas está errada. |
| N6 | §10 "**67,6 %** de linhas + **9 %** de código" | **REFUTADO** | Soma 76,6 %. Os 23,4 % restantes não têm nome, destino, nem denominador declarado (quais arquivos?). |
| N7 | §10.3 "**28 das 55** cláusulas mudam de veredito conforme a relação de igualdade" | **NÃO DERIVÁVEL** | A contagem defensável é **35** (toda cláusula com comparação de literal-string), ou 33 excluindo `noCallTo`/`callTo`. Chega-se a 28 só excluindo as 5 `in{} ⇒ in{}`, exclusão que não se sustenta — os antecedentes delas *são* strings, e `KeyPairGeneratorSpec.mop:41` literalmente chama `ConscryptAliasTable.canonical(...)` para avaliá-las. |
| N8 | §8 a escada `20 → 22 → 30 → 31` | **PARCIALMENTE REFUTADO** | Os extremos reproduzem exatamente pelas pré-condições textuais: 33 − 13 arquivos bloqueados = **20** ✓; +2 (`FORBIDDEN:`/`;;`) = **22** ✓; e 31 é consistente. Mas o terceiro degrau prediz **28**, não 30 — e daí o último salto seria +3, não +1. O "30" é o número suspeito. |
| N9 | §8 "`neverTypeOf`/`noCallTo`/`callTo`/`notHardCoded` com parênteses (**6 arquivos**)" | **REFUTADO** | São **4** (`Cipher`, `KeyStore`, `KeyManagerFactory`, `PBEKeySpec`); `notHardCoded` tem zero ocorrências no `api30`. O 6 é o tamanho da união com o grupo `length(` — número certo, atribuído ao conjunto errado. |
| N10 | §10.1 "2 das 33 regras têm assinatura que não existe na API 30" | **NÃO REPRODUZÍVEL** | Tratadas classes aninhadas (`KeyStore$LoadStoreParameter`) e membros herdados, todos os eventos resolvem. |

**Três dos "órfãos" do §10 são órfãos de exposição, não de medição** — deriváveis, mas com o denominador nunca declarado no texto: **55** (cláusulas de `CONSTRAINTS` sobre as 22 regras pareadas), **22** (regras pareadas com `ORDER`; todas as 33 têm `ORDER`, então a coluna "cláusulas `ORDER`" troca silenciosamente de "regras" para "pares"), e **97** — que a auditoria chama de "órfão total" e **não é**: é `56 target(<param>) + 41 returning(… <param>)` = 97 sítios de ligação de parâmetro no `jca_android`, com tabela por arquivo. Idem o **44** do §5.4: derivável sob exatamente uma definição natural (triplas distintas `(regra produtora, predicado, regra consumidora)`), que o documento nunca enuncia; definições vizinhas dão 79, 19 e 36.

**O achado de instantâneo, e é estrutural.** Os números de M4 do §5.4/§7/§9 foram medidos no commit **`d64f3a40`**, não no `HEAD` com que o documento foi publicado. Prova: "64 sítios de `ExecutionContext`, 21 de `PredicateStore`, 5 dos 23 arquivos migrados" reproduz **exatamente** em `d64f3a40` e em nenhum outro commit. Hoje é 47/26/7 (medido agora). O `predicate_graph.csv` que o §9 cita com 85 linhas tem **73 linhas de dados** no disco. O documento não carimba instantâneo em lugar nenhum, e a linha de teto `74,0 % / 58,7 %` está calculada sobre um estado de substrato que já não vale.

### D2 — Coerência interna

Além das contradições que a auditoria de consistência já cataloga (e que eu confirmo: §8 "cinco" × §12 "quatro"; §11.5 afirmando e desafirmando o *nearest-wins*; as testemunhas do §5.2 × V4 com `i1`/`i2` trocados), quatro que ela não tem:

| # | Onde | O quê | Sev |
|---|---|---|---|
| E1 | §12:1106 decide "um `CrySLModelReader` **por regra**" × §5.2:311, §8:587, §8:606, §8:655, §10.2:806, §12:1105 | **Nenhuma seção faz a conta que a decisão do §12 implica.** Todos os "as 31 regras que carregam" foram medidos lendo o diretório inteiro num leitor só — a configuração que o §12 proíbe. Sob a decisão, o corpus é 30/33. Pior que o denominador: o "impacto medido zero" do V3 e o conferidor de 155 eventos **foram ambos medidos em modo lote**, logo a evidência que sustenta a via alternativa do §8 foi produzida na configuração descartada. | **ALTA** |
| E2 | §5.3:321-336 declara o denominador de M3 subestimado × §6:445 e §13:1207 publicam "45,5 %" | O documento descobre que o denominador está errado e **continua publicando o número calculado sobre ele**, inclusive na linha "MEDIDO" do §13. Das três regras que perderam `CONSTRAINTS`, duas têm `.mop` (`DHGenParameterSpec` +1, `IvParameterSpec` +3): o denominador corrigido seria ~59 e o resultado ~42 %. | **ALTA** |
| E3 | V2 (registro de validações) regista uma **quarta** divergência do gerado — falta de `import java.security.spec.AlgorithmParameterSpec`, spec que *"parseava e não compilaria"* × §10:762 "As divergências contra o humano são **três** e todas nomeáveis… Nenhuma delas é ruído de tradução" | A quarta foi descartada, e é exatamente ruído de ferramenta — o único caso da lista que **é** ruído. Contradiz também §11.1:954: *"a validade sintática do gerado vem por construção"*. | **ALTA** |
| E4 | §13 tabela V2 "passa — M1 5/5, M2 3/3, M4 5/5, M3 2/2" × V2 no registro | As três specs geradas são **todas da mesma família** (`DHGenParameterSpec`, `GCMParameterSpec`, `PBEParameterSpec` — eventos que são construtores do tipo do `SPEC`), a mais fácil do conjunto. O §10 e o §13 nunca dizem isso, e o §13 usa o resultado para fechar o risco da direção da geração. | **ALTA** |

**Sobre a "formulação a usar" do §6 — eu discordo da auditoria, e o achado real é melhor.** A auditoria (A6) diz que a formulação perde a parcela de 28 porque `26 + 19 + 19 = 64 ≠ 92`. **A aritmética da auditoria testa a estrutura errada.** O §6 enuncia um **encaixe**, não uma partição: `92 ⊃ 73 ⊃ 54 ⊃ 26`. "As 19 restantes exigem `PredicateStore`" são `73 − 54 = 19` ✓; "as outras 19 exigem specs que não existem" são `92 − 73 = 19` ✓. Nada no §6 contradiz o §5.4, e o débito de fiação está lá, implícito, como `54 − 26 = 28`, que é o que os "48 % do exprimível" exprimem.

Mas o §6 afirma da própria formulação: *"Quatro frases, nenhuma ambígua… a única versão que um revisor não pode ler errado."* **Essa afirmação está empiricamente falsificada.** O antecedente natural de "as 19 restantes", vindo logo depois de "26 estão implementadas fielmente — 48 % do exprimível", é o **54** — cujo resto é 28, não 19. Nesta revisão, **dois leitores independentes leram errado exatamente assim**: a auditoria de consistência, e um dos meus próprios subagentes, que reportou "the remainder of 54 is 28, not 19" sem conhecer a auditoria. Dois de três leitores independentes errando a mesma frase é a medição do defeito. O reparo não é aritmético, é escrever a parcela de 28 por extenso — que é a maior das três e a única que o §5.4 chama de "trabalho de spec".

**A citação do TSE 2023 — a auditoria está errada, e eu verifiquei diretamente.** A auditoria (A13) afirma que a frase *"the CrySL and JavaMOP specification languages are similar"* *"não contém essa frase nem nada próximo"*. Ela procurou em `ase-journal/docs/notes/@torres-tse-2023.md`, um cofre de excertos derivado. **O fonte do paper está na árvore**, em `$W/rvsec-paper/`, e a frase está lá, quase literal:

```
rvsec-paper/main.tex:812-813
   for three main reasons.
   First, these \csl \specs were validated by \crypto
   experts. Second, the \csl
   and JavaMOP \spec languages are similar. Third, …
```

Também confirmado: `rvsec-paper/macros.tex:132` define `\nrules` = **22**, e `main.tex:825` diz "In total, we write 22 JavaMOP specs" — logo o "22" do §10.6 está **certo** para o TSE 2023, e a tensão 22 × 23 é crescimento do corpus depois da publicação, não erro. **A A13 da auditoria é REFUTADA nas duas metades.** É um erro instrutivo: ausência num arquivo de notas derivado foi tratada como ausência na fonte.

### D3 — Solidez arquitetural

Além do §3.1 e do §3.2 acima:

| # | Achado | Sev |
|---|---|---|
| A1 | **A razão fundadora do §12 é um non sequitur.** *"Construir um `MOPSpecFile` … exige os tipos do `javamop`, então o emissor mora ao lado do leitor"* estabelece que `mop.lower` precisa do `javamop` — mas `mop.lift` também precisa. O argumento produz **dois conjuntos de dependências**, nunca **quatro artefatos Maven**. Pacotes Java dão a mesma co-locação de graça. E o §11.1 já enfraqueceu o argumento por conta própria (o emissor recebe o pointcut como *string*), o que remove a única assimetria que poderia distinguir `lower` de `lift`. | ALTA |
| A2 | **Nenhum dos dois produtos vivos precisa de escrita de CrySL.** O comparador compara sobre o modelo; o `crysl2mop` escreve `.mop`. Só o `mop2crysl` — que o §12 declara *"sem consumidor conhecido"* — precisa. Mesmo assim o desenho compra o caminho `CrySLFactory`/`CrySLSemanticSequencer`, um **pretty-printer de ~400 linhas**, um formatador, e o ramo "(opcional) emitir `.crysl` legível" do diagrama do §1. São 400+ linhas de violação de P1, e é o que faz do `rvsec-crysl-crysl` "um adaptador de duas mãos". | ALTA |
| A3 | **O `scala.version` sobrescrito quebra o `ptltl` — e o `ptltl` é obrigatório.** Medido: com `<scala.version>2.13.14</scala.version>` no pom-pai, a árvore passa a resolver `scala-library:2.13.14` para **todo o classpath do componente**, incluindo o `ptltl` (compilado em 2.11, e 2.11↔2.13 não são binariamente compatíveis) e o `scala-parser-combinators_2.11`. E o §11.5 **proíbe excluir o `ptltl`**, porque o M2-eff precisa do `rv-monitor` com os plugins de lógica. A opção Scala 3 e a fonte de autômato do M2-eff são mutuamente exclusivas, e o plano enuncia as duas como desenho. Ganho comprado: 24 linhas. | ALTA |
| A4 | **O mecanismo do *nearest-wins* está errado, não só não verificado.** A auditoria mostra que o §11.5 se autodesmente (V10 diz que não foi exercitado). A razão de fundo é mais forte: a raiz **gerencia** `org.scala-lang:scala-library` via `dependencyManagement`, e gerenciamento vence *nearest-wins* para transitivas — logo o *nearest-wins* **nunca roda**. Medido: com `scala3-library_3:3.3.4` e sem sobrescrever a propriedade, a árvore resolve `scala-library:2.11.12`, não 2.13.14. | MÉDIA |
| A5 | **O modelo promete três bandas e implementa duas.** O §1 define o componente como verificador "a três bandas": o que a spec faz, **o que dizemos que ela faz (os CSV e o Javadoc de `Property`)**, e o que a regra exige. Há dois *lifts* e nenhum leitor de `Property.java` nem dos CSV. Pior, é autodestrutivo: o §12 diz que a saída deve **substituir** as tabelas manuais — se os CSV passam a ser gerados da banda 1, a banda 2 deixa de existir como oráculo independente, e o componente perde a capacidade de detectar "dissemos algo que a spec não faz", que o §9 apresenta como **classe de defeito encontrada** (os 18 cabeçalhos apontando para o oráculo errado). Escolher uma das duas: ou existe um terceiro *lift*, ou o §1 larga a moldura de três bandas. | ALTA |
| A6 | **A costura Java↔Python não está especificada.** Os consumidores dos CSV são 18 scripts Python em `rv-android`, que **não está no reator** (a única integração é a entrega de jar via `main.basedir`). O §12 fixa a localização do módulo e o molde (`rvsec-mop-extractor`), mas não configura `outputDirectory`, não nomeia quem invoca, e cria um acoplamento de ordem de build não declarado: hoje os portões gh10x rodam sobre CSV versionados com zero pré-requisito Java; se os CSV passarem a ser gerados, rodar um portão passa a exigir `mvn install` do reator dentro de um contrato de CI Python. Três processos ⇒ três artefatos executáveis ⇒ três configurações de shade/assembly, nenhuma mencionada. | ALTA |
| A7 | **P3 não está agendado.** O §3 justifica o componente pela duplicação (três comparadores de `ORDER`, cinco leitores de CrySL, ~10.400 linhas de Python). O §12 nunca lista o que é **apagado**. Como está, o componente vira o **quarto** comparador de `ORDER` e o **sexto** leitor de CrySL. P3 exige deleção com cópia em `backup/`. | MÉDIA |

**Sobre o portão de round-trip — é circular e cego às duas falhas que ele mesmo nomeia.** O §5.2 estabelece que a equivalência só vale **depois** de N1–N4. O portão compara a saída do gerador com a regra **através da mesma camada de normalização que o comparador usa** — não pega defeito que more dentro do próprio quociente. E as duas falhas nomeadas não precisam de busca no produto e não são alcançáveis por ela:

- *"Evento declarado e ausente do `ere`"* é puramente local, e o **checador de 20 linhas que o próprio plano propõe duas vezes** (ids únicos + alfabeto ⊆ ids) o pega. Pode, aliás, ser **apagado** pela ε-normalização do gêmeo negado.
- *"`@match` sem `@fail`"* é sobre **handlers**, não sobre estrutura de autômato. Duas specs que diferem só na presença do handler têm **linguagem idêntica**. Um portão de equivalência de linguagens é demonstravelmente cego a isso.

Recomendação: dois portões com estatutos diferentes — (1) um checador **não-normalizado** sobre a AST gerada (ids únicos, alfabeto ⊆ ids, todo evento declarado alcançável na fórmula, todo `@match` com `@fail`, todo evento no mapa de alfabeto), que é barato, não-circular e pega as duas; e (2) a busca no produto mantida, mas reportada como **evidência** com o conjunto de normalizações aplicadas impresso ao lado de cada veredito. Uma spec que só passa sob N3+N4 está dizendo alguma coisa.

### D4 / D8 — Validade metodológica e adversarial

Esta é a dimensão com mais achados novos, e três deles derrubam normalizações que o §5.2 declara **leis gerais**.

#### N1 não é lei geral — refutado por execução  ·  **ALTA**

O §5.2: *"N1 e N2 são regras **gerais**, não remendos: valem para qualquer spec paramétrica."* N1 é propriedade da **árvore de indexação gerada**, não do JavaMOP, e é falsa para 5 das 23 specs. O discriminante é mecânico e lê-se do monitor gerado:

```
$ for f in *RuntimeMonitor.java; do grep -q MapOfMonitor $f && echo SLICED || echo GLOBAL; done
GLOBAL  CipherInputStreamSpec   CipherOutputStreamSpec   HMACParameterSpecSpec
GLOBAL  KeyStoreSpec            RandomStringPassword
SLICED  (as outras 18)
```

Uma spec `GLOBAL` compila para `private static final Tuple2<Set,Monitor>` — **um monitor para o programa inteiro**, com o comentário gerado `// RVMRef_ks was suppressed to reduce memory overhead`. Testemunha executada, `KeyStoreSpec`, dois `KeyStore` distintos cada um usado exatamente como a regra manda (`getInstance` depois `load`):

```
ks1 == ks2 ? false
    ACCUSED: KeyStoreSpec,…,InvalidSequenceOfMethodCalls
    ACCUSED: KeyStoreSpec,…,InvalidSequenceOfMethodCalls
    ACCUSED: KeyStoreSpec,…,InvalidSequenceOfMethodCalls
```

`Prop_1_transition_g1[] = {4,4,5,5,5,5}` — do estado 4 um segundo `g1` vai para 5 = falha. A palavra `g1 g1`, que o §4.1 diz que *"morre por fatiamento"*, está viva. Segunda testemunha: `CipherInputStreamSpec`, que **não está na lista de seis do §9** e declara zero parâmetros.

**A lista de seis do §9 está errada nas duas direções.** `KeyPairSpec`, `PBEKeySpecSpec` e `TrustManagerFactorySpec` **indexam** (um evento ligando basta); `CipherInputStreamSpec` e `CipherOutputStreamSpec` **não indexam** e não estão listados. O critério "quantos eventos ligam o parâmetro declarado" é o errado; o certo é "o monitor gerado constrói um `MapOfMonitor`?" — e o M2-eff **já lê esse arquivo**, então o conserto é barato.

Consequência para M2: nas 5 specs globais, `L(A_mop)` é linguagem sobre traço **global do processo** enquanto `L(A_crysl)` é sobre traço **por objeto**. Qualquer veredito de M2 sobre elas é erro de categoria, com N1 ou sem.

#### O critério de apagamento é indecidível pelo componente  ·  **ALTA**

O §5.2 dá: apagar `e` preserva a linguagem sse `e` rotula auto-laço em todo estado *"ou se **nenhuma palavra realizável** contém `e` junto com outros símbolos"*. O segundo disjunto quantifica sobre **programas Java**. Não é decidível do `.mop`, e o plano não dá ao componente nenhum oráculo de realizabilidade. E ele é exatamente o que **torna N1 correta** para o `KeyGeneratorSpec` (`g1 g1` é irrealizável porque `getInstance` devolve objeto novo) e **incorreta** para o `KeyStoreSpec` (`g1 g1` é realizável porque há um monitor global) — e os dois casos são **textualmente indistinguíveis** no `.mop`. Escrito como está, parece checagem estática e não é: o componente vai aplicá-lo **de forma não-sólida**. O substituto decidível é a árvore de indexação.

#### M2-eff não mede o que o §5.1 diz que mede  ·  **ALTA**

O §5.1 vende o M2-eff como *"o monitor que rodou no experimento aceita a mesma linguagem que a regra?"*. Não aceita. A `condition(...)` compila para dentro de `Prop_1_event_g1`, **antes** de `handleEvent` — isto é, **a montante das tabelas de transição**:

```java
final boolean Prop_1_event_g1(String alg, KeyGenerator k) {
    { if ( ! (ConscryptAliasTable.matches("KeyGenerator", alg, safeAlgorithms)) ) { return false; }
      { keyGenerator = k; currentAlgorithmInstance = alg; } }
    int nextstate = this.handleEvent(0, Prop_1_transition_g1);   // ← a guarda está ANTES
```

Executado sobre o `KeyGeneratorSpec` de produção, dois traços com **ordem de chamada idêntica**, diferindo só no algoritmo:

```
--- AES: getInstance; generateKey   (ordem certa, alg seguro)      → sem acusação
--- DES: getInstance; generateKey   (ordem certa, alg inseguro)
    ACCUSED: InvalidSequenceOfMethodCalls   ← erro de sequência que o programa NÃO tem
    ACCUSED: UnsafeAlgorithm                ← o real
```

Logo o autômato efetivo é `⟨tabelas, guardas, ordem de fusão de advice⟩`, e o M2-eff lê **só a primeira componente**. M2-decl também não vê (a guarda não aparece no `ere`). **Nenhuma das duas variantes de M2 vê a classe de defeito que o §10.3 documenta como a razão da migração do gh105.**

#### N4 é mais largo: o aspecto gerado **funde** pointcuts sobrepostos  ·  **ALTA**

Meu §3.1 achou a sobreposição estática só no `CipherSpec`. O aspecto **gerado** mostra que é maior: pointcuts sobrepostos viram **um corpo de advice com despacho sequencial**:

```java
// KeyGeneratorSpecMonitorAspect.aj
after (String alg) returning (KeyGenerator k) : KeyGeneratorSpec_g1(alg) {
    KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g1Event(alg, k);   // g1
    KeyGeneratorSpecRuntimeMonitor.KeyGeneratorSpec_g3Event(alg, k);   // g3 — mesmo join point
}
```

Um join point emite a palavra de **duas letras** `g1 g3`. `Prop_1_transition_g3[] = {0,5,5,5,5,5}` — `g3` a partir do estado pós-`g1` é falha. A spec só se salva porque o corpo do `g1` escreve `currentAlgorithmInstance` **antes** de a guarda do `g3` o ler. A mesma forma fundida aparece no `KeyStoreSpec`. **O alfabeto não é disjunto em lugar nenhum do corpus**, não só no `CipherSpec`.

#### O estado estático do parser `.mop` — espelho do vazamento de escopo do CrySL  ·  **ALTA, nova**

O §9 encontra e celebra o vazamento de escopo do `CrySLModelReader`. O lado `.mop` tem o defeito gêmeo e o plano não o marca. `SpecExtractor.parse` nunca chama `MOPNameSpace.init()`, e `JavaMOPSpecExt.assignEventIds` aloca `uniqueId` sondando essa lista global. Mesmo arquivo, três vezes, uma JVM:

```
parse #1 : GCMParameterSpecSpec: c1/c1_3   c1/c1_4
parse #2 : GCMParameterSpecSpec: c1/c1_7   c1/c1_8
parse #3 : GCMParameterSpecSpec: c1/c1_11  c1/c1_12
```

E entre arquivos, o modelo de B depende de A ter sido lido antes. Consequências: o modelo canônico **não é função do arquivo**; `provenance` e qualquer diff de JSON entre duas execuções são instáveis; e a disciplina "um leitor por regra" do §12 tem de ser espelhada como **`MOPNameSpace.init()` (ou JVM nova) por spec** do lado MOP.

#### A vacuidade — cinco formas, 22 sítios, e nenhuma métrica tem palavra para elas  ·  **ALTA**

O §12 nomeia duas formas de spec vazia (`@match` sem `@fail`; evento declarado e ausente do `ere`). O corpus tem cinco:

| forma | sítios | o que é |
|---|---:|---|
| `@fail` inalcançável | 5 specs | `ere : c1 \| c2` num monitor chaveado pelo objeto que `c1`/`c2` cria ⇒ um evento por monitor, estado de erro nunca entrado. **Cinco códigos de erro de ORDER que nunca podem ser emitidos.** Dois arquivos dizem isso de si mesmos. |
| guarda-e-reconferência | 8 | `getInstance` guardado por `condition(matches(alg, lista))` e depois um corpo a jusante retesta `obj.getAlgorithm()` contra a mesma lista. Inalcançável por construção. O `MacSpec:152` nomeia o padrão; o `CipherSpec` não foi reparado. |
| ramos `VIOLATED` intomáveis | 11 | `PredicateStore.validate` só devolve `VIOLATED` sobre entrada negada ou tupla de aridade trocada. `RANDOMIZED` nunca é negado e todo uso é aridade 1 ⇒ 10 ramos mortos, + `CipherSpec:132`. |
| condições constantes de plataforma | 2 | `SecretKeySpecSpec:101` (`if (keyMaterial.length < offset + len)` nunca verdadeiro num `after…returning` — o construtor já lançou) e `IvParameterSpec:115` (o `else` inalcançável). |
| escritas sem leitor | **26 de 34** sítios de `ENSURES` | só 8 alimentam alguma leitura. `PREPARED_DH`, `PREPARED_GCM`, `PREPARED_HMAC`, `PREPARED_IV`, `PREPARED_PBE`, `SIGNED`, `VERIFIED`, `DIGESTED`, `ENCRYPTED`, `GENERATE_SSL_*` — escritos, nunca lidos. |

**A última linha é a que dói: M4 pontuaria quase toda ela como FIEL.** Um `setProperty` com o `Property` certo, aridade certa e posição certa é uma aresta M4 **perfeita** e um no-op em execução.

Contado por camadas de "morto": **6 sítios de predicado (8 %) em specs que não emitem relatório nenhum; 17 (23 %) somando `@fail` inalcançável; 26 (36 % dos 73) somando ligação de parâmetro quebrada.** Todos os 26 são elegíveis a FIEL / PROJETADO / CONFLADO. O vetor `26 / 54 / 73 / 92` não os distingue dos vivos.

**E há a forma dual, que nem o plano nem o censo de vacuidade têm:** o check que **nunca deixa de disparar**. `PBEKeySpecSpec.mop:108` lê `PredicateStore.validate(RANDOMIZED, password)` sobre um `char[]`; **nenhuma spec do conjunto carimba `RANDOMIZED` sobre um `char[]`** (os escritores são `SecretKeySpec.mop:26` sobre uma chave, e cinco sítios do `SecureRandomSpec` sobre `int`/`byte[]`/`SecureRandom`). Logo o veredito é permanentemente `NOT_OBSERVED` e o `PBEKEYSPEC-NOBS-00` sai em **toda** construção de `PBEKeySpec`, com `conforms = false` e o `ensure(SPECCED_KEY, …)` de `:131` morto.

> **Ressalva importante, e ela corrige um subagente meu.** Um dos meus agentes reportou isto como *regressão introduzida durante esta revisão* pelo commit `5f64c8de` (18:25), que apagou a ponte de predicados do `RandomStringPassword`. **Verifiquei e é falso.** A deleção é deliberada, documentada no cabeçalho do próprio arquivo e em quatro linhas novas do `divergence_record.csv`, e não muda comportamento observável: a leitura já estava no `PredicateStore` enquanto a escrita apagada estava no `ExecutionContext`, isto é, **a ponte já estava inerte** — *"nothing had reached it since… Its sole consumer keeps reporting exactly what it reported before"*. O registro ainda nota que a leitura não traduz cláusula nenhuma (o `api30` pede `randomized[salt]`, e sobre o password pede `neverTypeOf(password, java.lang.String)`) e que a divergência fica registrada contra o `PBEKeySpecSpec`, *"and is not repaired from here"*. O achado que sobrevive é metodológico, não operacional: **M3 classifica isso como `MOP-SEM-BASE` (uma divergência de escopo) quando o seu efeito de execução é um falso positivo incondicional** — e nenhuma das quatro métricas mede "isto sempre dispara".

#### Um gerador de falso positivo vivo, vindo da divisão de substratos  ·  **ALTA**

`ExecutionContext` (booleano, chaveado por `equals`) e `PredicateStore` (três-valorado, chaveado por identidade) são armazéns **disjuntos**. `GENERATED_KEY` é escrito nos **dois**: no `PredicateStore` por `SecretKeySpecSpec.mop:153`, no `ExecutionContext` por `KeyGeneratorSpec.mop:80` e `KeyStoreSpec.mop:83`. E `CipherSpec.mop:118` lê **só o novo**. Logo um `Cipher` inicializado com chave produzida por `KeyGenerator` ou `KeyStore` reporta `CIPHER-NOBS-00` **contra código conforme**. O §5.4 conta isso como **teto de expressividade** ("débito de substrato"); do lado da execução é **fonte viva de acusação errada**. A distinção importa: teto é limite do que se pode medir, isto é defeito a reparar.

#### O corpus se moveu durante esta revisão — medido  ·  **ALTA**

O `HEAD` avançou **duas vezes** enquanto eu revisava:

| | commit | hora | efeito |
|---|---|---|---|
| início da revisão | `0290caf5` | 18:01 | gh105 em 35/74 |
| | `e9bfb0d7` | 18:07 | *"o plano ganha o que faltava para servir de entrada da change"* |
| fim da revisão | `5f64c8de` | 18:25 | apaga 4 sítios de predicado; gh105 em **36/74** |

E o §5.4/§7/§9 estão medidos num terceiro commit, `d64f3a40`, mais antigo que o `HEAD` de publicação do próprio documento. O `SpecModel` do §12 tem `provenance : arquivo:linha` e **nenhum campo de versão**. Duas execuções do componente não são comparáveis com um dia de distância, quanto mais com um mês. Isto não é ressalva de redação: é requisito faltando no modelo canônico.

#### O que a gh105 **em aberto** já quebra

| "custo zero" do plano | tarefa gh105 aberta que o torna não-zero |
|---|---|
| fronteira do parâmetro único, **0/23** | **5.1** — `IvChainJunction.mop`, uma spec de junção para `SecureRandom → byte[] → IvParameterSpec → Cipher`, a entrar em `jca_android/`. Junção relaciona ≥2 objetos por construção. 5.2–5.10 acrescentam mais. **A fronteira vai a ≥1/24 durante a janela em que o componente seria construído.** |
| `CipherSpec` INCOMPARÁVEIS, testemunha `g1 i1 f1` | **6.6** — *"`CipherSpec` `f1`/`f2` … both match the argument-less call — one call, two transitions; **make the wider pointcut disjoint**"*. Apaga exatamente a sobreposição em que a testemunha se apoia. **A testemunha publicada tem data de validade agendada.** |
| M4 = 26 fiéis, 19 de débito de substrato | **5.3, 4.15, 6.1–6.4** — `validateAbsent` para as duas cláusulas negadas do `MacSpec` (exatamente 2 dos 19), leituras de `condition` movidas para corpos, os `remove()` em `@fail` apagados. **Todo número do §5.4 é alvo móvel.** |

### D6 — Contribuição científica

**A citação do TSE 2023 é real** (`rvsec-paper/main.tex:812-813`), e isso é pior para o argumento do que se fosse falsa. O paper existe na árvore, em `$W/rvsec-paper/`, com `main.tex` e `main.pdf`. Além da frase citada, `main.tex:2825` traz uma segunda justificação, **mais forte e não citada pelo plano**: *"the rules are defined as EREs over method call sequences and JavaMOP has native support for ERE as a spec language"* — que é precisamente o que o §10.2 apresenta como achado ("o `ORDER` chega compilado").

**O que o TSE 2023 já publicou e o plano trata como novo:**

| O plano apresenta como achado | Já está no TSE 2023 |
|---|---|
| §10.5: `notHardCoded`/`neverTypeOf` é inexprimível — *"deixa de ser limitação embaraçosa e vira o achado"* | `main.tex:1962-1977`, num **quadro destacado**: *"Main reason for RVSec's false negatives: It is hard to write RV specs to check if a variable was initialized to a hard-coded string constant."* Descrito como *"inherent limitation"*. |
| §10.2: o `ORDER` é liftável porque CrySL é baseado em ERE | `main.tex:2825` e `:375-381` |
| §5.3/§5.4: débito de cobertura (regras sem `.mop`) | `main.tex:1471-1477`: *"RV specs for infrequently used JCA classes (e.g. SecretKeyFactory and TrustManagerFactory). Future work should write specs for these classes."* |

O achado que o §10.6 elege como manchete é a reformulação de um resultado **em quadro destacado** do artigo anterior do próprio grupo.

**A classificação das cinco categorias do §10.5.** O §10.6 promete *"inexprimível em RV **por resultado de monitorabilidade**"*. Um resultado de monitorabilidade no sentido Pnueli–Zaks / Bauer–Leucker–Schallhart é afirmação sobre uma **propriedade**. Classificando cada categoria como **(a)** limite genuíno de monitorabilidade, **(b)** limite do JavaMOP/CrySL como linguagem, **(c)** limite do substrato/alfabeto atual, **(d)** feature não implementada ou defeito do oráculo:

| categoria | n | classe | por quê |
|---|---:|---|---|
| `neverTypeOf` / `notHardCoded` | 5 | **(c)**, com fio de (b) | Procedência é propriedade de traço sobre alfabeto mais rico. **O plano refuta-se no mesmo bullet:** o corpus já monitora o defeito por outra via, o taint de `String.toCharArray()` em `RandomStringPassword.mop:18-23`. Se uma instância é monitorável acrescentando evento, a classe não é imonitorável — é **não-monitorada sob o alfabeto escolhido**. |
| `IncompleteOperationError` | — | **(c)** | "O objeto chega a estado aceitante antes do fim do seu tempo de vida" é propriedade de **co-segurança**; a teoria diz que co-segurança dá veredito em *alguma* extensão finita, e a resposta padrão de RV é um evento de fim de escopo. Java não tem destrutor determinístico — dificuldade de instrumentação, não imonitorabilidade. E o RV-Monitor já carrega as categorias *presumably true/false* da mesma literatura. |
| `noCallTo` / `callTo` | 2 | **(d)** | O próprio plano diz: *"parecem constraints mas são predicados sobre símbolos do ORDER"*. `noCallTo` é segurança pura, fechada por prefixo — a classe **mais fácil**. O obstáculo declarado é que o `CipherSpec.mop` não declara o evento `getIV()`. É linha faltando. |
| cláusulas `length` invertidas | 3 | **(d)**, e mal-arquivadas | Traduzem-se perfeitamente; traduzem-se para algo **errado**. É achado de qualidade de oráculo, o melhor material do documento, no cabeçalho errado. |
| parâmetro múltiplo | — | **(b)**, direção abandonada, custo 0 | Limita o **CrySL**, e só na direção `.mop → .crysl`, que o §1 e o §12 declaram morta. Custo medido no corpus do artigo: **0/23**. |

**(a) = 0 de 5. (b) = 1, na direção abandonada. (c) = 2. (d) = 2.** Zero limites genuínos de monitorabilidade. Essa classificação **é** a contribuição prometida, e sai vazia. O título honesto do §10.5 não é "o que não se traduz" e sim "o que este substrato ainda não monitora, e um defeito no oráculo".

**O baseline e o `87/92 vs 73`.** É troca de denominador, e adjudico que sim: 73 é o teto sobre as **23 regras que o humano cobriu**; 87 é sobre as **33**. Catorze dos catorze pontos de ganho são **cobertura**, não fidelidade — e o §10.4 admite isso ("O débito de cobertura some") e mesmo assim reporta o número combinado como resultado de qualidade. **A comparação de mesmo denominador nunca é enunciada.** Pior: o gerador é avaliado contra **o oráculo de que ele lê**; só pode falhar por bug de implementação. É teste de ida-e-volta, não medição de fidelidade. O humano foi avaliado contra um oráculo que nunca teve (o `api30` é posterior às specs). São dois sujeitos em provas diferentes, e a diferença é reportada como resultado.

**Validade externa.** Uma família de API (JCA); um conjunto de regras gerado pelo **MetaCrySL do próprio grupo** e medido como defeituoso; uma linguagem-alvo escolhida no TSE 2023 **precisamente por ser parecida** com CrySL — seleção sobre a variável dependente; e um baseline humano escrito pelos coautores. O revisor escreve isso numa frase e não há resposta no documento.

**O que sobrevive como ciência**, e é o que eu recomendaria mirar: (i) a **corrupção e a perda do oráculo `api30`** — invariante sob qualquer trabalho de engenharia do grupo, falsificável, e com público (os mantenedores do CrySL); e (ii) o resultado metodológico de que **equivalência de linguagem de `ORDER` é estritamente mais fraca que conformidade com a regra**, sendo cega ao `IncompleteOperationError` e às specs que absorvem uso incorreto. Largar a palavra *monitorabilidade* enquanto não houver teorema, e citar Falcone–Fernandez–Mounier (STTT 2012) e Bauer–Leucker–Schallhart (TOSEM 2011) — hoje ausentes — se houver.

**Trabalho relacionado que o plano não cita e que estreita a lacuna:** *tracematches* (Allan et al., OOPSLA 2005) compila padrão declarativo de traço com variáveis livres em monitores AspectJ — é literalmente "spec declarativa de protocolo → monitor, compilado"; PQL (Martin, Livshits & Lam, OOPSLA 2005) é uma linguagem com **dois backends**, estático e dinâmico, que é a moldura mais próxima desta; e o CogniCrypt (Krüger et al., ASE 2017) já compila CrySL em artefatos executáveis. A frase correta não é *"nenhum tradutor CrySL → RV foi encontrado"* e sim: *"o CrySL já é compilado para autômato pela sua própria implementação de referência; até onde sabemos não foi compilado para um monitor de RV executável"* — honesto e bem menos impressionante.

---

## 5. Revisão da auditoria de consistência

A auditoria é boa, o seu veredito-resumo (*"substancialmente correto onde mediu e frágil onde tabulou"*) é o certo, e eu confirmo a maioria dos seus achados estruturais: A1 (o §10 sem arnês e três números que não fecham), A2 (a decisão do §12 derruba o 31/33), A3 (cinco × quatro substituições), A4 (a primeira testemunha do `CipherSpec` refutada), A5 (as testemunhas do V4 não são as do §5.2), A7 (SEM-BASE 16 e a classificação de M4 não deriváveis), A9, A10, A11, A12 e a deriva de alvo móvel. Onde eu discordo:

| # | Afirmação da auditoria | Meu veredito | Evidência |
|---|---|---|---|
| **A13** | A frase atribuída ao TSE 2023 *"não contém essa frase nem nada próximo"* | **REFUTADA** | A auditoria procurou em `ase-journal/docs/notes/@torres-tse-2023.md`, um cofre de excertos derivado. O **fonte do paper está na árvore**: `rvsec-paper/main.tex:812-813` traz a frase quase literal. E `macros.tex:132` define `\nrules`=22, logo o "22 specs" do §10.6 também está **certo**. Erro instrutivo: ausência num artefato derivado tratada como ausência na fonte. |
| **A6** | A formulação do §6 perde a parcela de 28: `26+19+19 = 64 ≠ 92` | **REFUTADA como aritmética, CONFIRMADA como defeito** | O §6 enuncia um **encaixe** (`92 ⊃ 73 ⊃ 54 ⊃ 26`), não uma partição: `73−54=19` e `92−73=19` fecham. Mas o §6 afirma que a formulação é *"a única versão que um revisor não pode ler errado"*, e **dois leitores independentes a leram errado do mesmo jeito nesta revisão** — a própria auditoria e um subagente meu que não a conhecia. Isso mede o defeito melhor que a objeção aritmética: o antecedente natural de "as 19 restantes" é o 54, cujo resto é 28. Reparo: escrever o 28 por extenso. |
| **§10, "97/97 é órfão total"** | não bate com nenhuma contagem obtenível | **REFUTADA** | É derivável: `56 target(<param>) + 41 returning(… <param>) = 97` sítios de ligação de parâmetro no `jca_android`, com tabela por arquivo. O defeito é de **exposição** — o denominador nunca é declarado —, não de medição. Idem `55` e `22`, que a auditoria trata como mal-postos e que são deriváveis sob definição que o texto omite. |
| **A14** | O teto do oráculo está subdimensionado **por uma ordem de grandeza**: 95→62 em 16 regras | **CONFIRMADA nos números, SUPERDIMENSIONADA na moldura** | O `95 → 62` reproduz exatamente, e o "16 regras" é 15 que perdem + 1 que ganha. Mas as 34 cláusulas perdidas não são um fenômeno só: **23** são a tríade de limites remodelada por convenção do MetaCrySL (upstream escreve `length[x] >= off+len ∧ off>=0 ∧ len>0` como 3 cláusulas, o MetaCrySL escreve 1), **3** são `notHardCoded` excluído por escopo declarado, e **8** são deleção genuína sem substituto. Na base contábil do próprio plano o déficit é **~11 cláusulas em 6 regras**, ou **7 dentro das regras com `.mop`** — subestimação de 25–55 %, não de uma ordem de grandeza. **A afirmação literal do plano ("três regras perderam a seção inteira, ~9 cláusulas") confere exatamente**; o que está refutado é o **escopo** que o §6 lhe dá ("M3 — 3 regras"). |
| **A8**, item `generic` 93 → 97 | multi-parâmetro no `generic` é 97, não 93 | **REFUTADA — o plano está certo** | É disputa de definição, e a definição do plano é a defensável. Contadas as duas vias: o **texto do cabeçalho** dá 97 (`1:21, 2:40, 3:30, 4:17, 5:6, 6:4`); a **AST** (`JavaMOPSpec.getParameters()`) dá **93**, com histograma `39/28/18/7/1` — **exatamente a tabela do plano**. A causa é um defeito do próprio `javamop`: `MOPParameters` deduplica por **nome** de parâmetro e descarta silenciosamente a declaração posterior, seja qual for o tipo. Onze specs do `generic` têm nome duplicado; quatro caem de 2 para 1. Prova direta: `FSM123.mop:9` declara `FSM123(InetAddress i, InetSocketAddress i)` e o `.rvm` gerado sai `FSM123(InetAddress i)`. Como tudo a jusante (indexação do monitor, extração do M2) lê o artefato gerado, **93 é o número certo**. A auditoria observou algo real no texto-fonte e contou a grandeza errada. |
| **A8**, itens `Property.java` 24 → 26 e "absorvem uso incorreto" 12 → 16 | | **CONFIRMADOS os dois** | `Property.java` é um `enum` com **26** constantes, confirmado por reflexão sobre `Property.values()`; e o `git log` mostra 23 → 25 → 26, isto é, **nunca foi 24** — não é sequer instantâneo velho. Uma correção **à auditoria**: são **3** constantes com Javadoc, não 4 (o quarto bloco `/**` é o da classe), então a afirmação do §3 (*"o Javadoc de cada constante cita a cláusula CrySL"*) é 3/26, pior do que a auditoria diz. E as specs que absorvem uso incorreto são 16/23 por dois critérios independentes que convergem, com as mesmas 7 exceções. |

**A testemunha substituta: dois dos meus agentes a executaram e discordaram — e a reconciliação é o achado.**
A auditoria refuta a primeira testemunha do `CipherSpec` por execução e reconstrói o veredito sobre uma
substituta que declara **não ter executado** (`g1 i1 wkb1 f2`). Eu mandei executá-la duas vezes, por
caminhos diferentes, e os resultados parecem opostos:

```
(1) FSM estruturalmente idêntico sobre receptor de fachada
    [EV] g1 / [EV] i1 / [EV] wkb1 >>> [MATCH1-end] / [EV] f2 >>> [MATCH1-end]     — sem FAIL
    e no lado da regra, o StateMachineGraph do api30 Cipher: o nó alcançado por `wrap`
    tem UMA aresta de saída, `wrap -> ele mesmo`; NÃO há aresta `doFinal`.
    => o MOP aceita, a regra rejeita. A testemunha é válida no nível do autômato.

(2) `javax.crypto.Cipher` real
    [EV] g1 / [EV] i1 / [EV] wkb1 >>> [MATCH]
    java.lang.IllegalStateException: Cipher not initialized for encryption/decryption
            at javax.crypto.Cipher.checkCipherState / Cipher.doFinal
```

Os dois estão certos, sobre coisas diferentes, e juntos dizem mais do que qualquer um sozinho:
**a testemunha é válida como palavra e impossível como programa.** `wrap` exige `WRAP_MODE`,
`doFinal` exige `ENCRYPT_MODE`/`DECRYPT_MODE`, e o autômato do MOP não tem aresta de `init` a
partir de `end` — não há reinicialização que faça a ponte.

**Isto expõe um terceiro autômato que ninguém modela: o do próprio `javax.crypto.Cipher`.** A
implementação da JCA mantém a sua máquina de estados de modo e lança em runtime. Tanto o `.mop`
quanto a regra CrySL **sobre-aproximam** o que um `Cipher` real consegue fazer, porque nenhum dos
dois modela essa máquina. Uma palavra pode portanto ser aceita pelo MOP, rejeitada pela regra, e
**inexecutável em Java** — e nenhuma das quatro métricas tem como saber.

Adjudicação, em duas camadas, porque o plano usa dois critérios e só declara um:

- **No nível de linguagem**, o veredito `INCOMPARÁVEIS` **sobrevive**: a substituta foi verificada
  mecanicamente nos dois lados, e a segunda testemunha (`g1 i2 i2 f2`, regra∖MOP) é independente e
  também se sustenta (`Cipher.cryptsl:117` tem `Inits+`; o `fsm` de produção não tem aresta de `init`
  a partir de `s2`). A auditoria acerta ao dizer que refutar uma testemunha não derruba o veredito.
- **No nível de acionabilidade**, que é o critério que o próprio §5.2 enuncia — *"as duas testemunhas
  são realizáveis e acionáveis"* —, a direção MOP∖regra **ficou sem testemunha**: a primeira está
  refutada por execução e a substituta não roda. O documento tem de escolher qual dos dois critérios
  está reportando, e hoje afirma o segundo enquanto só demonstra o primeiro.

Dois reparos menores à auditoria no mesmo bloco: a **sonda C dela contradiz a conclusão tirada dela**
— o transcrito mostra `[MATCH]` (o monitor **aceitando**) e o texto reporta só que a trajetória
*"termina em FAIL nas duas ordens"*, o que vale apenas do **último** veredito emitido; e as três
sondas são **reduções**, não a spec de produção, coisa que a auditoria não declara (conferi a redução
e ela é fiel para esta trajetória: `f1:198` antes de `f2:205` ✓, `s2` sem aresta `f1` ✓, `s3` com `f1` ✓).

Uma precisão que nenhum dos dois documentos tem, e que vem das tabelas geradas: na **ordem de
produção** (`f1` primeiro) a trajetória dá **dois FAIL e nenhum MATCH**; na ordem invertida o
`@match1` **roda antes** do FAIL, de modo que o `ensure(Property.ENCRYPTED, …)` é gravado **e em
seguida** vem a acusação. O co-disparo não é só relatório espúrio — é relatório **mais escrita de
predicado**.

Dois reparos menores à própria auditoria, no mesmo bloco: a **sonda C dela contradiz a conclusão que ela tira dela** — o transcrito mostra `[MATCH]` (o monitor **aceitando**) e o texto reporta só que a trajetória *"termina em FAIL nas duas ordens"*, o que é verdade apenas do **último** veredito emitido e esconde a aceitação; e as três sondas são **reduções** do `CipherSpec`, não a spec de produção, coisa que a auditoria não declara. Conferi a redução contra `jca_android/CipherSpec.mop` e ela é fiel **para esta trajetória** (ordem de declaração `f1:198` antes de `f2:205` ✓; `s2` sem aresta `f1` ✓; `s3` com `f1` ✓); a auditoria tinha o direito de dizer isso e não disse.

**E o vazamento de escopo do `CrySLModelReader` corre nos dois sentidos** — a auditoria viu só o resgate. Executado, 33 regras normalizadas, `CrySLParser` 4.0.6:

```
leitor partilhado, ordem alfabética : ok=31/33   falham [AlgorithmParameters, DigestOutputStream]
leitor novo por regra               : ok=30/33   falham [+ Signature]
leitor partilhado, alfabética inversa: ok=29/33  falham [+ Signature, Key]
40 ordens aleatórias, leitor partilhado: histograma {29:3, 30:15, 31:22}
                                        falhas por regra: Key=15/40, Signature=6/40
```

Bissectado: **`SecretKey.crysl` lido antes de `Key.crysl` quebra o `Key.crysl`.** Ou seja, o vazamento não só resgata regra inválida — também **envenena** regra individualmente válida, e o conjunto que carrega **não é função do corpus**: varia de 29 a 31 conforme a ordem de leitura. Isso muda a crítica: não é *"o §12 derruba o denominador"*, e sim **"o §12 acerta por uma razão que nenhum dos dois documentos dá — determinismo — e o §8 mediu a escada 20→22→30→31 com o leitor que o §12 descarta."**

**O que a auditoria não pegou** — e é a crítica que eu faria a ela: ela auditou **consistência**, e por isso passou ao lado de tudo que só aparece **executando**. Os achados §3.1, §3.4, N1 refutado, M2-eff cego às guardas, o estado estático do `MOPNameSpace`, o censo de vacuidade e o falso positivo de `GENERATED_KEY` não são inconsistências do texto — são propriedades do artefato. A auditoria chega a tocar o primeiro (a sonda A do `CipherSpec`) e trata-o como *"candidato a defeito da spec"*, sem ver que ele **refuta o modelo canônico do §12**. É a mesma lição que o docstring do arnês do gh104 já tinha escrito: *"a static gate measures the artefact and not its behaviour"* — e uma auditoria de consistência é um portão estático sobre um documento.

**Dois achados novos que vêm de executar, e que nenhum dos dois documentos tem:**

- **O `api30` carrega 30/33, não 31/33 — e a escada léxica do §8 está errada no meio.** Executado o `CrySLParser` 4.0.6 por níveis de normalização sobre cópias: L0 = 20/33, +`FORBIDDEN:` = 22, +`;;` = 22, +`alg`→`algName` = 24, +as reescritas de colchete **incluindo `length(`** = **30**. Sem `length(` = 27. Ou seja, `length(…)`→`length[…]` move **27→30** (desbloqueia `Cipher`, `Mac` e `SecretKeySpec`), não 30→31 como o §8 diz e a auditoria repete. E as três residuais são defeitos reais das regras que nenhuma substituição alcança: `AlgorithmParameters:47` (implicação dentro de `CONSTRAINTS`), `DigestOutputStream:20` (`on` não declarado) e `Signature:51,59,65` (`offset`/`len` fora de `OBJECTS`). **Nenhum modo de leitura produz 31.**
- **Determinismo confirmado com margem maior que a do plano:** 30/30 das que carregam em L4, e **0 não-determinísticas em todos os seis níveis** — inclusive 20/20 sem normalização nenhuma. O teste expandiu cada aresta nos métodos concretos do rótulo e agrupou por `(nó, método)`, o que também pega rótulos que se **intersectam**, não só idênticos.

**Calibração:** a A4 está com severidade alta pelo motivo certo mas com a consequência subdimensionada; a A13 e a A6 deveriam cair; e o item da tabela de precisão sobre `RVM_eventNames` deve **cair**, não subir: regenerados os 23 `.rvm` do `jca_android` individualmente, o array está presente em **23/23** — e também em 23/23 no `jca` e 118/118 no `generic`. As 17 ausências estão todas no `generic_new`, e são specs **sem propriedade** (`TreeMap_Comparable` e afins declaram eventos e nenhum bloco `ere:`/`fsm:`), onde não há autômato a extrair. A afirmação da auditoria é literalmente verdadeira e **não toca o M2-eff**. O que compromete o M2-eff é outra coisa, e é grave: ele não vê as guardas (D4/D8).

---

## 6. As dez afirmações estruturantes

| # | Afirmação | Veredito |
|---|---|---|
| 1 | *"A comparação é o produto; a tradução é o meio."* | **Meio certa, e o documento não integrou a própria virada.** O argumento que matou o `mop2crysl` (regra sintetizada sem consumidor) está correto. Mas o §10 conclui que a geração é o produto mais forte, e a estrutura do documento continua centrada no comparador: o diagrama do §1 é desenhado `.mop`-primeiro e a única seta de emissão nele é `(opcional) emitir .crysl legível` — a saída do produto que o §12 desautoriza; o §10 é a décima de treze seções; e a fronteira do parâmetro único, um dos trechos mais bem medidos do §12, tem **custo zero na direção da geração**. Não são dois produtos fundidos para justificar um módulo — são um produto e um subproduto, com o subproduto ocupando o centro do texto. |
| 2 | *"`ORDER` deve ser comparado por equivalência de linguagens."* | **Certa, e eu a defendo.** Simulação/bissimulação seriam **erradas**: são propriedades de tempo ramificado sobre autômatos de alfabetos diferentes ligados por um mapa de normalização, e reportariam diferenças espúrias de estrutura de estados que a equivalência de linguagens corretamente ignora. Um pré-ordem de refinamento colapsaria "INCOMPARÁVEIS" numa direção só e daria uma testemunha; o reticulado de quatro com **duas** testemunhas é mais informativo, não menos. "Incomparável" **é** acionável, desde que sempre acompanhado das duas testemunhas — o que o §5.2 faz. **O que compromete o M2 não é a relação escolhida; é o alfabeto (§3.1) e a cegueira às guardas (D4/D8).** |
| 3 | *"A precedência do `ORDER`: `\|` liga mais forte que `,`."* | **CONFIRMADA em três fontes independentes**, e o raio de explosão confirmado e ampliado. A gramática que o jar 4.0.6 embarca é **byte-idêntica** ao snapshot `e92f5607`; a gramática ANTLR gerada dentro do jar concorda. `Cipher` é a única regra afetada no `api30` (1/33), no `base` (1/33) **e** no upstream (1/49). A inversão do `ConcreteSyntax.rsc` do MetaCrySL é real e hoje invisível — verificado não só pelo argumento do §9 (o `ppEventExp` só parenteteriza nós `parentheses()`) mas empiricamente: as sequências de tokens de `ORDER` saem **idênticas para 33/33** de `base` para `api30`. Uma imprecisão: a linha 2 da tabela do §4.2 devia nomear a sobrecarga — `getInstance;init;doFinal()` é `f1`, que é corretamente **rejeitado sob as duas leituras** (`f1 ∉ FINWOU`); quem inverte é `doFinal(pt)` = `f2`. |
| 4 | *"Preferir M2-eff a M2-decl."* | **REFUTADA como enunciada.** As tabelas `Prop_1_transition_*` são o autômato **declarado com os nomes de estado apagados**, não o efetivo: as `condition(...)` compilam **a montante** de `handleEvent`, e a fusão de advices sobrepostos acontece no aspecto, acima das tabelas. Executado: `getInstance("DES"); generateKey()` — ordem correta — desenha um `InvalidSequenceOfMethodCalls`. (O `RVM_eventNames`, ao contrário do que a auditoria sugere, **não** é o problema: está presente em 23/23 no `jca_android`. O problema é a guarda.) O M2-eff não responde *"o monitor que rodou aceita a mesma linguagem?"*; para responder isso é preciso **executar traço**. |
| 5 | *"N1 — no máximo um evento criador por monitor."* | **REFUTADA como lei geral, por execução.** Falsa para 5 das 23 specs, que compilam para monitor global (`Tuple2`, não `MapOfMonitor`). Duas testemunhas executadas de falso positivo. E o critério de fidelidade do apagamento que a sustenta é **indecidível pelo componente**. O veredito do `KeyGeneratorSpec` sobrevive — mas por medição, não pela lei. |
| 6 | *"`IncompleteOperationError` não tem contraparte; M2 é cego a ele."* | **Fronteira de escopo honesta, e é o melhor parágrafo do §10.5** — mas não é limite de monitorabilidade (é co-segurança; falta o evento de fim de escopo, que é dificuldade de instrumentação em Java). Como limitação de conformidade é séria e está bem declarada; como contribuição científica não sustenta a moldura do §10.6. |
| 7 | *"Fronteira do parâmetro único, com recusa tipada; custo 0/23."* | **Princípio certo, custo já vencido.** A recusa tipada é a resposta correta e é coerente com o `Unknown`. Mas o custo **não é zero durante a janela do componente**: a tarefa **5.1 do gh105, em aberto**, cria `IvChainJunction.mop` — uma spec de junção que relaciona `SecureRandom → byte[] → IvParameterSpec → Cipher` — e as 5.2–5.10 acrescentam mais. A fronteira vai a ≥1/24 antes de o componente existir. |
| 8 | *"JSON como costura, processos separados."* | **REFUTADA. Superengenharia sobre um conflito inexistente** — ver §3.2. `javamop` não puxa Guava nem Soot; há um só consumidor de Guava; o V10 já neutralizou o pino da raiz; e uma sonda de módulo único roda os dois parsers na mesma JVM. O V6 provou que três processos **funcionam** e nunca rodou o controle. Perde-se a testemunha (o núcleo passa a reparsear o `ere`), a fidelidade do DFA no fio e o `Unknown` tipado nos erros de leitura. |
| 9 | *"`ExecutionContext` × `PredicateStore`: o substrato é parâmetro do gerador."* | **Certa como decisão de gerador, incompleta como leitura do presente.** Tratar o substrato como parâmetro é correto. O que falta é que a coexistência dos dois armazéns **disjuntos** não é só um teto de expressividade: é um **gerador vivo de falso positivo** (`GENERATED_KEY` escrito nos dois, lido só no novo pelo `CipherSpec.mop:118`). O teto de aridade 2 é da implementação, não do desenho — o `PredicateStore` já é aridade N. |
| 10 | *"O mapa do que não se traduz é a contribuição."* | **REFUTADA como enunciada.** Zero das cinco categorias é limite de monitorabilidade (a=0, b=1 na direção abandonada, c=2, d=2); a manchete escolhida está publicada em quadro destacado no TSE 2023 do próprio grupo; e o `87/92 vs 73` é troca de denominador. **Sobrevive outra coisa, e é melhor:** a corrupção medida do oráculo e o resultado metodológico de que equivalência de `ORDER` é estritamente mais fraca que conformidade. |

---

## 7. Alternativas (D7)

O núcleo algorítmico do plano está certo e as alternativas radicais são piores. Digo isso explicitamente porque o convite era para propô-las:

| Alternativa convidada | Veredito |
|---|---|
| **Uma linguagem intermediária única em que ambos compilam** | O plano **já a tem** — o `SpecModel` é isso. A versão radical (a IL vira a linguagem de autoria, e `.crysl`/`.mop` são gerados) custa reescrever 23 specs numa linguagem que ninguém conhece e perder a comparabilidade com o artefato publicado. **Rejeitada**; a metade boa já está lá. |
| **Derivar o corpus `.mop` do CrySL como passo de build — conformidade verdadeira por construção** | **Rejeitada na forma pura, e o §3.3 diz por quê:** gerar do `api30` embarca as três `length` invertidas (que acusam todo `doFinal` conforme), o `randomized[sr]` inligável do `SSLContext`, o `preparedEC` órfão do `KeyPairGenerator` e duas specs para classes que o Android não tem. "Verdadeiro por construção" só é verdadeiro relativo a um oráculo que não é verdadeiro. **Sobrevive uma versão mais fraca e atraente:** gerar o **esqueleto** — eventos, pointcuts, fatiamento, fiação de predicado, que é onde o humano demonstravelmente erra (6/21 de fatiamento quebrado, `Property` errada, `__RESET` esquecido) — e deixar `CONSTRAINTS` para revisão humana, que é onde o humano demonstravelmente acerta (omitiu 3 de 3 cláusulas invertidas). Divide o corpus por quem é melhor em quê, e é implementável já. |
| **Teste diferencial / baseado em propriedades sobre traços gerados** | **É a alternativa forte, e não é hipótese: está construída** (§3.4). Não substitui a comparação de autômatos — resolve o que ela não vê. Recomendo promovê-la a oráculo do M2. |
| **Refinamento com model checker de prateleira** | **Rejeitada.** Decidir equivalência de dois DFA com <20 estados sobre alfabeto pequeno é busca no produto, ~60–80 linhas, e o §11.4 já a mediu nas duas linguagens. Trazer SPIN/NuSMV/LTSmin é dependência pior que o Guava. |
| **Codificar os dois lados num provador/SMT** | **Rejeitada agora, certa a longo prazo para uma camada só.** A camada `ORDER` é regular e decidível sem solver. A camada `CONSTRAINTS` é onde um solver ajudaria de verdade — transformaria M3 de comparação de conjuntos em checagem de implicação e responderia formalmente à pergunta do §10.3 sobre a relação de igualdade. Mas o gargalo do M3 não é o solver: é **extrair a semântica de corpo Java arbitrário**, que é o "teto do instrumento" de 25,5 %. O solver não move o gargalo. |
| **Inverter: minerar regras CrySL de traços observados** | **Rejeitada para este fim.** Diz o que os apps fazem, não se a spec diz o que a regra exige. Não valida tradução. Direção de pesquisa separada. |

**A redesenho que eu argumento** não é algorítmico; são quatro emendas ao §12, todas já justificadas acima:

1. **Um módulo, uma JVM** (§3.2). JSON só como saída.
2. **Autômato simbólico guardado sobre assinaturas, com ordem de declaração preservada**; o DFA sobre rótulos passa a ser vista calculada (§3.1). Isto é o que torna N4 construção em vez de remendo, e é pré-requisito para que qualquer veredito sobre `CipherSpec`, `KeyGeneratorSpec` ou `KeyStoreSpec` signifique alguma coisa.
3. **Comparação de dois oráculos** — `api30` e `CrySL-Rules` —, com a discordância entre eles como sinal de primeira classe e veredito de 2 bits por item (§3.3). 21 das 23 specs são elegíveis hoje.
4. **Uma quinta métrica, M0 — vitalidade do monitor**, antes de M1–M4: o monitor gerado indexa (`MapOfMonitor`) ou é global? a spec tem algum sítio de acusação (`@fail` presente, `addError` > 0, `@fail` alcançável)? todo pointcut resolve contra o `android.jar` alvo? Todas as três são decidíveis de artefatos que o desenho já produz, e sem elas M1–M4 avaliam uma spec que não pode falar — 26 dos 73 sítios de predicado (36 %) estão em specs mortas ou de fatiamento quebrado, e M4 os pontuaria como FIEL.

---

## 8. Riscos, ordenados

| # | Risco | Como descobrir cedo, e barato |
|---|---|---|
| 1 | **O componente mede o autômato declarado e conclui sobre o monitor que rodou.** É o risco-mãe: §3.1, N1, M2-eff cego às guardas e a vacuidade são todos instâncias. | Rodar o arnês do gh104 contra as 5 specs `GLOBAL` e as 8 de guarda-e-reconferência **antes** de escrever qualquer linha do componente. Custo: horas, e o arnês já existe. |
| 2 | **O alvo se move mais rápido que a medição.** Medido: `HEAD` andou duas vezes em 25 minutos; `gh105` foi de 35 para 36/74; o §5.4 está preso a um terceiro commit. | Carimbar commit em toda tabela **hoje**, e acrescentar campo de versão ao `SpecModel` antes de qualquer implementação. É a correção mais barata do lote. |
| 3 | **Construir três módulos e uma costura JSON e descobrir que uma classe bastava.** | A sonda de módulo único já foi executada nesta revisão e passa. Refazê-la em 30 minutos antes de decidir. |
| 4 | **O gh105 invalida três "custos zero" durante a construção** (tarefas 5.1, 6.6, 5.3/4.15/6.x, todas abertas). | Ler `tasks.md` do gh105 e reescrever as três linhas do §12 que dizem "custo medido zero" como "zero **em `HEAD`=X**, e a tarefa N o torna não-zero". |
| 5 | **O artigo é rejeitado por reafirmar o TSE 2023.** | Escrever hoje o parágrafo "o que isto acrescenta ao TSE 2023" com a manchete trocada para a qualidade do oráculo, e submetê-lo a um leitor hostil interno. Se não convencer em cinco frases, não convence um PC. |
| 6 | **O oráculo defeituoso contamina o gerador.** Se `crysl2mop` virar produto, as 3 `length` invertidas viram monitores que acusam código conforme. | Rodar o gerador nas 33 regras e diferenciar contra o gabarito humano — o próprio §13 admite que fora das 3 specs os números "continuam sendo previsão". |
| 7 | **Testemunhas válidas e inexecutáveis.** A JCA tem a sua própria máquina de estados (o `Cipher` rejeita `doFinal` depois de `wrap` com `IllegalStateException`), que nem o `.mop` nem a regra modelam: os dois **sobre-aproximam**. Uma testemunha pode ser aceita pelo MOP, rejeitada pela regra e impossível em Java — foi o que aconteceu com a substituta do `CipherSpec`. | Antes de publicar qualquer testemunha, **executá-la**. É o que o §5.2 já promete ("realizáveis e acionáveis") e não faz. Custo: um programa por testemunha, e o arnês do gh104 já sabe rodá-los. |
| 8 | **O `scala.version` sobrescrito quebra o `ptltl` em runtime**, e o `ptltl` é obrigatório para o M2-eff. | Não sobrescrever. Java 21 em tudo. Decisão de uma linha. |

---

## 9. Recomendações, por retorno

### Mecânicas (inequívocas, sem decisão humana)

1. §12: "4 substituições" → **5**. Uma palavra, e é a tabela que vira proposta.
2. Carimbar `§3`, `§5.4`, `§7` e `§9` com o hash do commit medido (é `d64f3a40`, não o `HEAD` de publicação), e acrescentar campo de versão ao `SpecModel`.
3. Fazer a conta de **30/33** que a decisão "um leitor por regra" implica, e registrar que o "impacto zero" do V3 e o conferidor de 155 eventos foram ambos medidos **em modo lote** — a configuração que o §12 proíbe.
4. Reescrever o bloco de testemunhas do `CipherSpec`: adotar `g1 i2 i2 f2` e a substituta `g1 i1 wkb1 f2`, retirar *"as duas testemunhas saem idênticas"* (o V4 escreve `i2`, o §5.2 escreve `i1`), e **acrescentar o co-disparo `f1`/`f2` à tabela de defeitos do §9**.
5. Escrever a parcela de **28** por extenso na formulação do §6.
6. Retirar as três afirmações refutadas do §11.5: o *"verificado na árvore"* do *nearest-wins* (que não pode ter rodado, porque gerenciamento vence *nearest-wins*), e a ressalva de que `/pedro/...` não abre na JVM (é falsa — `/pedro` é o ponto de montagem real).
7. Corrigir `152/167` → **155/167**, e nomear as 15 não resolvidas (o texto só nomeia 12); reconciliar `87/92` com "4 lacunas" (a diferença é 5); declarar se `16/55` e `47/55` são aninhados; nomear os 23,4 % que faltam em `67,6 % + 9 %`.
8. **Não** recontar o `generic` para 97: o **93 do plano está certo**. O que falta é declarar a regra de contagem (a AST, não o texto do cabeçalho) e registrar o defeito que a diferença expõe — `MOPParameters` deduplica parâmetros por **nome**, e 11 specs do `generic` perdem declarações em silêncio (`FSM123(InetAddress i, InetSocketAddress i)` vira `FSM123(InetAddress i)` no `.rvm`). Recontar sim, e corrigir, o `Property.java`: são **26**, e nunca foram 24.
9. Corrigir a escada léxica do §8: `length(…)`→`length[…]` move **27→30**, não 30→31, e **nenhum modo de leitura produz 31** — o `api30` carrega **30/33** mesmo com leitor partilhado, e as três residuais (`AlgorithmParameters:47`, `DigestOutputStream:20`, `Signature:51`) são defeitos de regra que substituição nenhuma alcança.
10. Declarar os denominadores que existem e não estão escritos: o **44** do §5.4, e o **55**, **22** e **97** do §10. Os três últimos **são** deriváveis — a auditoria erra ao chamar o 97 de órfão.
11. Marcar a tabela-cabeçalho do §10 como **estimativa não medida**, ou depositar o arnês.
12. Corrigir a atribuição da A13: a citação do TSE **existe** (`rvsec-paper/main.tex:812-813`) e o "22" está certo. O que se deve corrigir é outra coisa — o §10.6 corta o subtítulo (*An Empirical Study*) e não cita a segunda justificação do paper, que é mais forte.
13. Redimensionar o teto do oráculo com a decomposição correta: 95→62 no bruto, mas **23** disso é remodelação sistemática da tríade de limites, **3** é `notHardCoded` excluído por escopo, e **~8** é deleção genuína — dentro das regras com `.mop`, o déficit normativo é **7**, não 9 nem 34.
14. Corrigir a linha do §9 sobre as "6 de 21 specs": três delas **ligam** o parâmetro (2/3, 2/4, 3/4) e o fatiamento **funciona**; a consequência declarada vale para as três com 0/N. E o critério certo é o `MapOfMonitor`, que muda a lista nas duas direções.

### De julgamento (o humano decide)

13. **Colapsar para um módulo e uma JVM**, e apagar `crysl.lower`, o pretty-printer de ~400 linhas e o formatador até que alguém peça um arquivo `.crysl` (§3.2, D3-A1/A2).
14. **Trocar a forma armazenada do `order`** para autômato simbólico guardado sobre assinaturas (§3.1). Sem isto, o `CipherSpec`, o `KeyGeneratorSpec` e o `KeyStoreSpec` não têm veredito com significado.
15. **Acrescentar M0 (vitalidade do monitor)** antes de M1–M4, e um estado por item para "implementado e vácuo" e para "sempre dispara" — nenhum dos dois cabe nas quatro categorias atuais.
16. **Adotar a comparação de dois oráculos** com veredito de 2 bits (§3.3), e parar de reportar como infidelidade o que é reparo humano de oráculo corrompido.
17. **Decidir o que fazer com o arnês do gh104** (§3.4): inventariá-lo como precursor e declarar o componente como a metade estrutural, ou promovê-lo a oráculo do M2. Não deixá-lo fora do documento.
18. **Java 21 em tudo**; não sobrescrever `scala.version`.
19. **Resolver a banda 2**: ou existe um terceiro *lift* que lê `Property.java` e os CSV como oráculo independente, ou o §1 larga a moldura de três bandas. Gerar os CSV a partir da banda 1 **apaga** a banda 2.
20. **Especificar a costura Java↔Python** antes da proposta: `outputDirectory`, quem invoca, e a lista de deleção que P3 exige.
21. **Retargetar a moldura científica** para a qualidade do oráculo e para o resultado metodológico, largar a palavra *monitorabilidade* enquanto não houver teorema, e reportar gerador × humano **no mesmo denominador de 73** antes que um revisor o calcule.
22. **Renomear o trabalho e redesenhar o §1.** Não pelo nome do arquivo, mas porque o diagrama do §1 é desenhado `.mop`-primeiro e a sua única seta de emissão é a do produto que o §12 desautoriza. Se a geração é o produto mais forte, o §1 desenha `.crysl → modelo → .mop`, com o comparador como portão de validação — que é o que o §12 já diz que ele é.

---

## 10. Não verificado

- **O gerador sobre as 33 regras.** Continua previsão, como o §13 admite. Acrescento que as três specs geradas no V2 são **todas da mesma família** (eventos que são construtores do tipo do `SPEC`), a mais fácil do conjunto — nem o §10 nem o §13 dizem isso, e o §13 usa o resultado para fechar o risco da direção da geração.
- **O total de cláusulas `CONSTRAINTS` do corpus upstream.** Duas recontagens minhas, independentes, discordam: uma dá **95** cláusulas nas 33 regras `CrySL-Rules` correspondentes, outra dá **116**. As duas concordam no `api30` (**62**) e no `base` (**42**), então a divergência está na regra de contagem do lado upstream (provavelmente conjunções `&&` contadas como uma cláusula ou como várias). **Não resolvi.** Isso não move a conclusão — as duas concordam na direção e em quais regras perdem —, mas qualquer número upstream que entre no documento precisa da regra de contagem escrita junto.
- **A relação de igualdade e o "28 das 55".** Não consegui derivar 28 sob nenhuma regra de contagem defensável; a contagem que eu defendo é 35. Pode haver uma definição que eu não reconstruí.
- **`SSLContextSpec` e `TrustManagerFactorySpec`**, as outras duas divergências que o G-ORDER reporta, seguem sem análise — como o §13 já registra.
- **Posicionamento no autômato das 19 cláusulas `after`.** Não conferido além do que o plano já diz.
- **Reprodução direta das sondas A/B/C da auditoria.** Confirmei o mecanismo do co-disparo por leitura estrutural (`FINWOU`, os pointcuts, as transições do `fsm`) e por convergência com duas execuções independentes de subagentes meus, não reexecutando o arnês da auditoria.
- **O efeito de execução das 5 specs `GLOBAL` sobre APK real.** As testemunhas de falso positivo do `KeyStoreSpec` e do `CipherInputStreamSpec` foram executadas na JSE, não sobre aplicativo.
- **`main.pdf` do TSE 2023.** Verifiquei a frase no fonte LaTeX (`main.tex:812-813`) e o `\nrules`=22 em `macros.tex:132`; não abri o PDF publicado para confirmar que o texto compilado é o mesmo.

### Uma correção a um subagente meu, declarada

Um dos meus agentes reportou como **regressão introduzida durante esta revisão** que o commit `5f64c8de` (18:25) teria criado um falso positivo incondicional no `PBEKeySpecSpec`. **Verifiquei e a causalidade é falsa.** A deleção é deliberada, documentada no cabeçalho do arquivo e em quatro linhas novas do `divergence_record.csv`, e não muda comportamento observável — a leitura já estava no `PredicateStore` enquanto a escrita apagada estava no `ExecutionContext`, isto é, a ponte já estava inerte. Registro isto porque é exatamente o modo de falha que o handoff nomeia como o pior resultado possível de uma revisão: uma afirmação confiante e não verificada. O achado que sobrevive é metodológico e está no §D4.
