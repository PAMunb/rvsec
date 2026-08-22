# Handoff — componente de conformidade MOP–CrySL: **validar antes de virar change**

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `ea9f7b12`
**Estado**: análise fechada em três rodadas, **nenhuma linha de código de produção escrita**
**Documento-mãe**: `docs/20260821_conformidade_mop_crysl.md` (1058 linhas)
**Issue GitHub**: **não existe ainda** — precisa ser aberta antes de qualquer artefato OpenSpec

> **O objetivo desta próxima sessão NÃO é implementar, e NÃO é criar a change.**
> É executar as validações que ainda faltam para que o plano deixe de ter hipótese não testada.
> Só quando todas fecharem — ou quando as que falharem tiverem desenho alternativo definido — é que
> se abre a issue e se entra no workflow OpenSpec.

---

## O que estamos fazendo

Projetando um componente que verifica mecanicamente se as especificações JavaMOP do RVSec dizem o
que as regras CrySL de que foram traduzidas exigem, e — descoberta da terceira rodada — que também
pode **gerar** as specs a partir das regras. Os dois produtos partilham modelo canônico, autômato e
portão de validação, e por isso moram no mesmo componente.

Contexto de por que isso existe: o mapeamento CrySL↔JavaMOP já foi feito à mão e está espalhado por
seis artefatos, nenhum durável, mais ~10.400 linhas de Python em 18 scripts `scripts/gh10*.py`, com
**três implementações independentes** da comparação de `ORDER` e **cinco leitores de CrySL** ad hoc.
14 dos 18 scripts parseiam `.mop` por expressão regular tendo um parser de verdade disponível.

O documento-mãe tem 13 seções. Leia-o inteiro antes de agir — este handoff não o substitui.

---

## REGRA NÃO NEGOCIÁVEL DE WORKFLOW

1. **Não crie artefato OpenSpec nesta sessão** enquanto houver validação aberta na lista abaixo.
   O pedido do pesquisador foi explícito: *"o plano deve ter tudo já conferido e definido, para só
   então poder virar change openspec"*.
2. Quando chegar a hora, siga `docs/WORKFLOW.md` **rigorosamente** e invoque as skills OpenSpec pelo
   `Skill` tool. **Nunca** use `Write`/`Edit` diretamente para criar ou reescrever `proposal.md`,
   `design.md`, `tasks.md`, `specs/**`. Isso está em `CLAUDE.md` como regra que sobrepõe qualquer
   outro instinto.
3. Diretório da change: `openspec/changes/gh<N>-<nome-curto>/`, minúsculo, sem prefixo de data.
   `proposal.md` traz `GitHub Issue: #N`; commits usam `refs #N` e o último `closes #N`.
4. **Nunca** adicione `Co-Authored-By` a mensagem de commit.
5. Português com acentuação correta em toda a documentação. O pesquisador escreve sem acento por
   causa do teclado; você não.
6. **Nunca** inicie, pare ou gerencie emulador Android. Regra permanente do `CLAUDE.md`.
7. Princípios P1–P4 (`CLAUDE.md`) governam código, comentário, spec e documento. P1 em especial:
   este componente tem duas linguagens de entrada e um caso de uso — nada de framework com plugins
   de dialeto.

---

## Leitura obrigatória, nesta ordem

| Arquivo | Por quê |
|---|---|
| `docs/20260821_conformidade_mop_crysl.md` | O documento-mãe. §10 é a direção da geração, §11 as decisões medidas, §12 a forma do módulo, §13 o que falta |
| `data/jca_android/order_alphabet_map.csv` | O mapa de alfabeto feito à mão; declara explicitamente que um mapeamento nunca é inferido |
| `data/jca_android/constraint_table.csv` | Censo de 55 cláusulas; colunas `mop_line`/`verdict` já envelhecidas |
| `data/jca_android/predicate_graph.csv` | 85 sítios; casamento 85/85 com censo independente |
| `openspec/changes/gh105-predicate-wiring/` | A change viva que reescreve `jca_android` agora; o alvo se move enquanto esta análise corre |
| `docs/WORKFLOW.md` e `.claude/AGENTS.md` | O processo e as skills |

---

## O que foi feito

**Rodada 1** levantou o terreno. **Rodada 2** executou parsing, censo e comparação de autômatos.
**Rodada 3** (esta) inverteu a pergunta — *dá para gerar `.mop` a partir da regra?* — usando sete
investigações paralelas, e fechou por execução as decisões de engenharia.

Os números por camada da geração estão no §10 do documento. Resumo do que ficou **decidido e
verificado**:

| Decisão | Evidência | Onde |
|---|---|---|
| Escrever pelo writer da tecnologia, não por `StringBuilder` | `DumpVisitor`: dump 73/73, reparse 73/73, zero falhas em `jca`+`jca_android`+`generic_new` | §11.1 |
| Descartar comentários | `Node.getBeginLine()` devolve 0 nos nós de spec e 1 em **todos** os eventos; posição não existe no AST | §11.2 |
| Java 21 nos leitores, Scala 3.3 admissível no núcleo | núcleo do M2 escrito nas duas: 59 linhas Scala × 83 Java, mesma resposta sobre caso real | §11.4 |
| **Não** excluir o `ptltl` | *nearest-wins* já resolve `scala-library` para 2.13.14 sozinho; e o M2-eff precisa do `rv-monitor` com plugins | §11.5 |
| Decomposição por tecnologia, não por direção | construir `MOPSpecFile` exige os tipos do `javamop`, logo o emissor mora ao lado do leitor | §12 |
| JSON como costura entre leitores e núcleo | isola os classpaths hostis (Guava 33.5 × 19.0) por construção | §12 |

E **10 defeitos novos** foram acrescentados ao §9, entre eles a precedência invertida em
`MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70` (o mesmo defeito do `gh105_order_gate.py`, na
outra ponta do pipeline, invisível porque o pretty-printer preserva o texto).

---

## As validações que faltam — **o trabalho desta sessão**

Ordenadas por quanto derrubariam do desenho se falhassem. Cada uma diz o que a falsearia.

### V1 — Montar um `MOPSpecFile` do zero e passá-lo pelo `DumpVisitor`

**A metade não testada da decisão de escrita.** Os 73/73 provam que o writer reimprime o que o
*parser* produziu; não provam que um objeto montado à mão atravessa. O gerador só monta à mão.

Faça a menor spec possível — um pacote, um import, um evento, um `ere`, um `@fail` — e dumpe.
Depois reparseie o resultado.

**Falsearia o desenho se**: o `DumpVisitor` depender de estado que só o parser preenche (campos
internos, listas nulas onde ele espera vazias). Nesse caso a emissão volta a ser texto, e o §12 muda:
o emissor deixa de precisar dos tipos do `javamop` e pode voltar para o núcleo.

**Custo**: uma hora. **É pré-requisito de tudo que envolve geração.**

### V2 — Gerar uma spec inteira ponta a ponta

Escolha `DHGenParameterSpec` — `ORDER` de um único evento (`c1`), o caso mais simples com `.mop`
correspondente. Gere a partir de `MetaCrySL/generated/api30/DHGenParameterSpec.cryptsl` e compare
contra `rvsec/rvsec-mop/src/main/resources/jca_android/DHGenParameterSpecSpec.mop` pelas quatro
métricas.

**É o experimento que converte as previsões do §10 em medição.** Hoje todo percentual daquela seção
é inferência estrutural, não artefato. Se der certo, repita com `GCMParameterSpec` e
`PBEParameterSpec` (dois eventos, constraints aritméticas) antes de tirar conclusão.

**Falsearia o desenho se**: o gerado não compilar pelo pipeline `javamop`, ou divergir do gabarito
humano por razão que não seja uma das políticas já nomeadas no §10.3.

**Custo**: um dia. **É a validação central. Sem ela o plano continua sendo hipótese.**

### V3 — `CrySLParser` com o `android.jar` da API 30

Nunca foi feito, e agora sabe-se que é mais difícil do que passar um caminho: o
`CrySLModelReaderClassPath` monta o classpath num `HashSet`, então a ordem é não determinística e o
`javax.crypto.Cipher` do JDK do host disputa com o do `android.jar`. Mirar a API 30 pelo construtor
virtual não é confiável.

Teste as duas vias: (a) construtor virtual com o caminho do `android.jar`; (b) JVM cujo classpath de
aplicação já contenha só o `android.jar`. Compare os tipos resolvidos e as assinaturas.

**Falsearia o desenho se**: não houver como fixar o classpath sem substituir o `ClasspathTypeProvider`.
Aí o lado normativo Android exige um fork do CrySL, e o §12 muda de custo.

**Custo**: meio dia. **É o único ponto onde a leitura do lado normativo pode divergir do medido.**

### V4 — Determinizar o `StateMachineGraph`

O parser entrega uma NFA de Glushkov, não determinizada e não minimizada; `ORDER Con, A?, A` produz
duas arestas `a` do mesmo nó. **Toda comparação de linguagem desta análise foi feita sobre autômatos
construídos à parte, nunca sobre o que o parser entrega.**

Escreva a determinização, rode-a sobre as 33 regras `api30`, e refaça as quatro comparações do §5.2
(`MessageDigest`, `Signature`, `KeyGenerator`, `SecureRandom`, `Cipher`) usando o autômato do parser.

**Falsearia o desenho se**: os vereditos mudarem. Os três `EQUIVALENTES` do §5.2 são o alicerce da
afirmação de que a normalização generaliza.

**Custo**: meio dia.

### V5 — Preservar os nomes de agregado

O `StateMachineGraph` achata `Gets := A | B` numa aresta rotulada `[a(), b()]` e o nome some. O
corpus humano escreve `ere: (g1|g2) (update+ …)`, misturando eventos concretos com agregados.
Recuperar os nomes exige a AST EMF, que a fachada `CrySLParser` descarta — replicar ~10 linhas de
`CrySLModelReader` (`CrySLStandaloneSetup` → `XtextResourceSet` → `ClasspathTypeProvider`).

Confirme que essas ~10 linhas funcionam fora do jar publicado.

**Falsearia o desenho se**: o `Domainmodel` não for alcançável sem forkar. Aí o alfabeto do `.mop`
gerado é o dos eventos concretos, o que muda a comparação com o corpus humano.

**Custo**: duas horas. Amarre com V3, que precisa do mesmo caminho.

### V6 — A costura JSON com os dois classpaths reais

O §12 propõe que cada leitor rode como processo próprio e despeje JSON, para que Guava 33.5 e Guava
19.0 nunca dividam JVM. **Isso nunca foi montado.** Faça o esqueleto mínimo: dois processos, um
schema JSON, e um terceiro que lê os dois e compara.

**Falsearia o desenho se**: o modelo canônico não for serializável sem perda — em particular o
autômato e os `Unknown` com texto cru e sítio.

**Custo**: meio dia.

### V7 — O `.mop` gerado atravessa o pipeline inteiro do `javamop`

Só o *parser* foi testado (214/214). A **geração** de monitor nunca. Pegue o `.mop` de V2, rode o
pipeline completo, e verifique que sai monitor com as tabelas `Prop_1_transition_*`.

**Falsearia o desenho se**: o gerado parsear e não gerar. Também vale para a pergunta aberta do §13
sobre as duas specs com defeito de sintaxe em `jca`.

**Custo**: duas horas.

### V8 — A semântica de fatiamento paramétrico

Nenhum monitor foi executado. A normalização N1 — no máximo um evento criador por monitor — é
dedução da semântica AspectJ, não medição em traço. **Se o `rv-monitor` divergir do padrão
paramétrico, N1 cai e dois dos três vereditos de equivalência do §5.2 voltam a "mais permissiva".**

Um programa de teste minúsculo com dois `getInstance` em sequência, contra uma spec instrumentada,
resolve. Isso **não** exige emulador — roda na JSE com o agente.

**Custo**: meio dia. **É a validação que sustenta a correção do MessageDigest no §4.1.**

### V9 — Confirmar independentemente dois achados de subagente

Vieram de investigação automatizada e não foram reconferidos à mão:

- `CrySLModelReader.getStatesForMethods`: `after <Agregado>` resolveria para conjunto de nós **vazio**
  quando o `ORDER` não referencia o agregado literalmente, sem aviso.
- `CipherTransformationUtil.mode("AES/")` lançaria `ArrayIndexOutOfBoundsException`, alcançável de
  `condition(...)` do `CipherSpec`, dentro de advice, na thread do app monitorado.

O segundo, se confirmado, é defeito em produção e vale conserto imediato, fora do escopo do componente.

**Custo**: uma hora.

### V10 — O módulo mínimo compila no reator

Monte os quatro `pom.xml` do §12 com uma classe vazia em cada e construa junto com o reator. Verifique
Guava, Scala, e se o `main.basedir` resolve.

**Falsearia o desenho se**: a herança de `rvsec-parent` não puder ser sobrescrita como o §11.5 prevê.

**Custo**: duas horas.

---

## Aprendizados operacionais — leia antes de rodar qualquer coisa

- **Caminhos**: use `/home/pedro/desenvolvimento/...`. O alias `/pedro/...` **não abre na JVM**.
- **Repositório Maven local**: `~/.m2/settings.xml` redireciona `localRepository` para
  `/home/pedro/desenvolvimento/repository`. Não é modo offline — **há rede**, o `settings.xml` só
  redireciona. Scala 3 foi baixado nesta sessão.
- **JDK**: só existe o 25 na máquina; o reator mira 21 e constrói assim mesmo.
- **Build do reator**: `mvn clean install -DskipMopAgent -DskipTests`.
- **`javamop` já instalado**: `/home/pedro/desenvolvimento/repository/br/unb/cic/javamop/javamop/0.9.3-SNAPSHOT/javamop-0.9.3-SNAPSHOT.jar` (bytecode major 65 = Java 21).
- **`CrySLParser` já instalado**: `.../de/darmstadt/tu/crossing/CrySL/CrySLParser/4.0.6/`.
  A primeira invocação leva ~2 min (setup Xtext standalone); as seguintes, não.
- **Não paralelize o parse de `.mop`** — `JavaMOPParser` guarda instância em campo estático, e
  `MOPNameSpace` é global e não é reinicializado por `SpecExtractor.parse`.
- **`BlockStmt.getStmts()` devolve `null`**, não lista vazia, para bloco `{ }`. O corpus tem vários.
- **"Parseou" não é oráculo de sanidade**: `jca/GCMParameterSpecSpec.mop` declara dois eventos `c1` e
  referencia um `c2` inexistente, e o `SpecExtractor` aceita calado.
- **Fork do JavaParser**: `javamop.parser.ast.*` é cópia vendorizada do `japa.parser` de 2007
  (gramática Java 1.5), estendida com `mopspec/` e `aspectj/`. É incompatível com
  `com.github.javaparser` 3.25.0, que o reator também declara e que `rvsec-mop-defsuses` usa. A única
  ponte entre os dois é `toString()`.

### Comandos que funcionaram

```bash
# classpath do javamop para probes avulsas
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/javamop
mvn -o -q dependency:build-classpath -Dmdep.outputFile=/tmp/jmcp.txt
CP="/home/pedro/desenvolvimento/repository/br/unb/cic/javamop/javamop/0.9.3-SNAPSHOT/javamop-0.9.3-SNAPSHOT.jar:$(cat /tmp/jmcp.txt)"
```

Arnês de round-trip usado em §11.1 (base para V1 e V2):

```java
import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.visitor.DumpVisitor;
import java.io.File;
public class RT {
  static String dump(File f) throws Exception {
    MOPSpecFile m = SpecExtractor.parse(f);
    DumpVisitor v = new DumpVisitor(); m.accept(v, null); return v.getSource();
  }
}
```

Forma do pom que compilou Scala 3 contra `javamop` (para V10, se for a via escolhida):
`scala-maven-plugin` **4.9.2** (a 4.6.3 do reator não serve para Scala 3), `scala3-library_3:3.3.4`,
`maven.compiler.release=21`. Emite bytecode major 65.

---

## Consertos que valem independentemente do componente

Não são desta change, mas estão medidos e são baratos. Decida com o pesquisador se saem antes:

1. `scripts/gh105_order_gate.py:136-200` — precedência invertida; muda o veredito do `Cipher`.
2. `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:62-70` — o mesmo defeito na outra ponta.
3. `MetaCrySL/src/generator/PrettyPrinter.rsc:49,139` — duas linhas, destrava 7 de 33 regras-oráculo.
4. Checador de sanidade de `.mop`: ids únicos + alfabeto da fórmula ⊆ ids. Vinte linhas sobre a AST,
   fecha uma classe inteira que o parser não vê.

---

## Só depois das validações: a change OpenSpec

Quando V1–V10 fecharem:

1. **Abra a issue no GitHub.** Não existe ainda. Título na linha de "componente de conformidade
   MOP–CrySL", track `full-sdd` (é projeto de módulo novo, não correção pontual).
2. Nome do diretório sugerido: `gh<N>-mop-crysl-conformance`.
3. **Nome pelo fim, não pelo meio**: *conformidade*, não *tradutor*. Quem lê o nome não fica tentado
   a pedir um compilador genérico depois.
4. A proposta tem de declarar, no corpo, qual das duas coisas cada métrica mede — "ordem correta" ×
   "uso correto" (§2), e `TypestateError` × `IncompleteOperationError` (§10.5). Essa é a armadilha
   metodológica que o §6 inteiro existe para evitar.
5. Escopo mínimo defensável para a primeira change: **o núcleo e os dois leitores, com M2 e M4**.
   M1 e M3 depois. O gerador é change separada — não misture.

---

## O que **não** fazer

- Não crie a change antes das validações. Foi pedido explicitamente.
- Não agregue as quatro métricas num score único. Um número esconde qual seção está ruim e convida a
  otimizar o número. Se o artigo exigir valor, que seja o vetor por seção (§6).
- Não rode o comparador de `S_android` contra `R_java` — mistura divergência de tradução com
  adaptação de plataforma e acusa como infidelidade exatamente a contribuição do artigo (§2).
- Não exclua o `ptltl` do `javamop`. É desnecessário e quebraria o M2-eff (§11.5).
- Não trate os percentuais do §10 como medição. São previsões até V2 fechar.
- Não escreva artefato OpenSpec com `Write`/`Edit`. Use as skills.
