# Auditoria de consistência — `20260821_conformidade_mop_crysl.md`

**Data:** 21 de agosto de 2026
**Alvo:** `docs/20260821_conformidade_mop_crysl.md` (1283 linhas)
**Método:** sete auditorias independentes contra as fontes primárias, mais uma verificação por
execução (achado A4, arnês em `docs/handoff/20260821_arnes_auditoria/`) — specs `.mop` dos cinco
conjuntos, `MetaCrySL/generated/api30`, `rvsec-cognicrypt/CrySL-Rules`, os CSV de
`data/jca_android/`, o código do `rvsec-core`, os fontes do `javamop`, os jars do `CrySLParser`,
o `android.jar` das APIs 26/30/33/35/36, o `git log` e o arnês `docs/handoff/20260821_arnes_validacoes/`.
Cada auditoria recontou do zero em vez de conferir o número impresso.
**Escopo:** consistência. Nenhum arquivo do documento auditado nem do corpus foi modificado; a
auditoria acrescentou apenas este relatório e o seu arnês de sondas.

---

## Veredito

O documento é **substancialmente correto onde mediu e frágil onde tabulou**. Essa não é uma frase de
cortesia: é o padrão que as sete auditorias encontraram independentemente, e ele é nítido o bastante
para separar o documento em duas metades com estatuto epistêmico diferente.

Tudo que passou por execução reproduz-se quando reexecutado, com frequência dígito a dígito: o censo
de 62/55 cláusulas de `CONSTRAINTS` e a matriz A/B/C/D/Ausente inteira; as 92 cláusulas de predicado
decompostas em 54/36/2; os 32 predicados distintos e a partição 59/33 de aridade; os denominadores
73, 54 e 44; as 8 cadeias produtor→consumidor idênticas em `jca` e `jca_android`; a precedência
invertida do gate e a tabela de três palavras que a demonstra; 214/214 no parse; 96→64 no
`DumpVisitor`; 167 eventos e 61 agregados no `api30`. Em vários casos a recontagem independente saiu
**exata**, a partir de fonte diferente da que o documento usou.

A metade frágil tem três causas distintas, e vale separá-las porque exigem respostas diferentes:

1. **§10 não tem arnês.** É a única seção do documento cujos números não existem em lugar nenhum
   fora da própria tabela — e três deles não fecham aritmeticamente.
2. **Correções da quarta rodada aplicadas pela metade.** Três correções do
   `20260821_validacoes_conformidade_mop_crysl.md` foram absorvidas numa seção e não na outra,
   deixando o documento a contradizer-se.
3. **Números sem carimbo de commit sobre um corpus que o gh105 move todo dia.** Sete tabelas
   envelheceram entre a medição e a redação — em alguns casos por horas.

Nenhum achado derruba o desenho do componente, a arquitetura de §12 ou a tese de §1. Vários derrubam
proposições que o documento afirma como fato, e um deles (§12 × 31/33) derruba um denominador que o
documento usa do começo ao fim.

---

## 1. Achados que mudam o que o documento afirma

### A1 — §10 inteiro carece de evidência, e três dos seus números não fecham

O contraste com o resto do documento é o achado mais importante desta auditoria. As seções §5 e §8
têm arnês executável (`v1/`–`v10/`, `crysl.json`, `mop.json`, `maps/*.map`, `m2/M2.java`), e foi por
isso que a recontagem independente as confirmou. A tabela-cabeçalho de §10 não tem nada disso: um
`grep` exaustivo em `docs/`, `data/` e no arnês inteiro — incluindo as 344 linhas de
`NOTAS-BRUTAS.md` — não encontra **nenhum** de `152/167`, `22/22`, `7/22`, `11/22`, `10/22`,
`16/55`, `47/55`, `87/92`, `67,6 %`, `9 %` ou `97/97` fora das linhas 744-748 e 776 do próprio
documento. As "sete investigações paralelas" da terceira rodada não depositaram evidência.

Três desses números são internamente inconsistentes:

| Afirmação | O problema |
|---|---|
| `87/92` com "**4** lacunas do `PredicateStore`" (e §10.4: "reduzido de 19 para **4**") | 92 − 87 = **5**. Como 94,6 % é o arredondamento correto de 87/92, o 87 é o número vivo e falta nomear a quinta lacuna. Não é detalhe: §10.4 conclui "catorze acima do teto humano" a partir de 87−73; com 88 seriam quinze. |
| `16/55` "sem decisão alguma" + `47/55` "sob uma política declarada" | 16 + 47 = **63 > 55**. Só fecha se os conjuntos forem aninhados, e o ponto-e-vírgula lê como disjunção. |
| `67,6 %` (template + derivável) + `9 %` de código | Soma **76,6 %**. Os 23,4 % restantes não têm nome nem destino. |

E dois têm denominador mal-posto:

- **`22/22` cláusulas `ORDER` parseáveis.** Todas as **33** regras `api30` têm seção `ORDER`
  (verificado, 33/33). O 22 é rastreável — é o número de regras `api30` pareadas com uma `.mop`
  (23 specs menos `RandomStringPassword`, que não tem regra) — e a soma de `CONSTRAINTS` sobre
  essas mesmas 22 dá exatamente 55, o outro denominador da tabela. Mas a coluna diz "cláusulas
  `ORDER`", que é afirmação sobre o lado CrySL, onde o número é 33. O denominador troca
  silenciosamente de "regras" para "pares (regra, spec)".
- **`7/22` idênticas + `11/22` equivalentes = 18.** As outras 4 não são mencionadas. Não-equivalentes?
  incomparáveis? não comparadas? §5.2, a única medição de M2 com arnês, cobre 5 specs, e duas delas
  **não** são equivalentes.
- **`97/97`** é órfão total: não bate com nenhuma contagem obtenível — 120 declarações `event` no
  `jca_android`, 63 `target(`, 70 `returning(`, 140 eventos nas 22 regras pareadas, 167 no total.

**Recomendação:** ou a terceira rodada deposita o arnês que produziu esses números, como V1–V10
fizeram para §5 e §8, ou a tabela é marcada como **estimativa não medida**. Como está, ela contamina
por vizinhança a única parte do documento cujos números se reproduzem dígito a dígito.

### A2 — A decisão de §12 derruba o 31/33 que o documento usa inteiro

§12 decide: *"Leitura CrySL | um `CrySLModelReader` **por regra**: o escopo de `OBJECTS` vaza entre
regras no mesmo leitor"*. Mas todo "as 31 regras que carregam" do documento — a varredura de
determinismo de §5.2, a tabela de §8, §10.2, o "no-op nas 31 regras de hoje" de §12, as "129 linhas
de assinatura resolvida" — foi medido lendo o **diretório inteiro num leitor só**. O `NOTAS-BRUTAS`
é explícito: `Signature.crysl` sozinho num leitor novo **falha**; lido depois de `GCMParameterSpec`,
**carrega**.

Sob a decisão que o próprio §12 toma, o corpus é **30/33**, não 31/33. O documento nunca faz essa
conta.

Agrava: a frase de §9 pendura a consequência no ramo errado — *"tem de ler cada regra num leitor
novo, ou declarar a ordem de leitura como configuração — e nesse caso `Signature` não carrega"*.
Pela medição é o inverso: é no **leitor novo** que `Signature` falha, e é **declarando a ordem**
(alfabética) que ela carrega.

### A3 — §8 diz cinco substituições; §12 ainda diz quatro

Correção do documento de validações aplicada pela metade:

- §8: *"uma camada de normalização de **cinco** substituições leva 20→**31**"*, e lista as cinco.
- §12, tabela "Forma do módulo": *"`CrySLParser:4.0.6` + normalização léxica de **4** substituições"*.
- O documento de validações, Correções #6: *"São **cinco** substituições e levam a **31/33**"*.

§12 é a tabela que vira proposta e que alguém vai implementar, e a substituição que sobra é
justamente `length(…)`→`length[…]` — a que o próprio §8 mede como responsável pelo salto 30→31.

### A4 — A primeira testemunha do `CipherSpec` é refutada por execução

§5.2 dá `g1 i1 f1` como testemunha de `MOP \ regra`, com a justificativa *"o pointcut `doFinal(..)`
também casa `doFinal()`, então o monitor aceita um doFinal sem update"*. A justificativa está certa e
a conclusão que ela sustenta está errada, pelo motivo que ela mesma introduz.

`jca_android/CipherSpec.mop` declara **dois** eventos que casam a mesma chamada — `f1:198`
(`call(public byte[] Cipher.doFinal())`) e `f2:205` (`call(public byte[] Cipher.doFinal(..))`) — e
**nenhum dos dois tem `condition(...)`**, ao contrário do par `g1`/`g4` que §4.1 analisa. Nada os
torna mutuamente exclusivos, então ambos disparam.

**Medido**, com o pipeline real (`javamop` 0.9.3-SNAPSHOT → `rv-monitor` → `ajc` 1.9.25.1, JSE, JDK
25 do host). Arnês em `docs/handoff/20260821_arnes_auditoria/`.

Sonda A — `ere` permissivo, só para revelar a ordem de disparo:

```
[EV] g1
[EV] i2
[PROG] chamando doFinal() -- UMA chamada
[EV] f1   <-- declarado PRIMEIRO
[EV] f2   <-- declarado DEPOIS
```

Uma chamada, **dois** eventos, na ordem de declaração.

Sonda B — o `fsm` real do `CipherSpec` (`s2` tem `f2`, não tem `f1`), com a trajetória que o
documento apresenta como aceita:

```
=== A testemunha do documento: getInstance; init; doFinal() ===
[EV] g1
[EV] i2
[EV] f1
   >>> [FAIL ] ev=f1
[EV] f2
   >>> [FAIL ] ev=f2

=== Controle: getInstance; init; update; doFinal(pt) ===
[EV] g1  [EV] i2  [EV] u1  [EV] f2
   >>> [MATCH] ev=f2
```

O monitor **acusa** exatamente onde o documento diz que ele aceita. O controle mostra que o `fsm` da
sonda funciona.

Sonda C — a mesma spec com `f2` declarado **antes** de `f1`, para testar se o resultado depende da
precedência do AspectJ:

```
[EV] g1  [EV] i2
[EV] f2
   >>> [MATCH] ev=f2
[EV] f1
   >>> [FAIL ] ev=f1
```

A ordem de disparo inverte junto com a declaração — confirmando que o mecanismo é a ordem de
declaração, e não um acidente da implementação — **mas o veredito não muda**: nem `s2` nem `end` têm
transição de `f1`, então a trajetória termina em `FAIL` nas duas ordens. A refutação não depende de
como o AspectJ ordena advices `after` no mesmo aspecto.

Note ainda que a justificativa do documento descreve `f2`, não `f1` — `f1` já é `doFinal()` literal.

**O veredito INCOMPARÁVEIS continua de pé**, por testemunha substituta:
`g1 i1 wkb1 f2` (`getInstance; init; wrap(key); doFinal(pt)`). O `fsm` aceita
(`s2 --wkb1--> end --f2--> end`, `:260`,`:281`) e a regra rejeita sob **as duas** leituras de
precedência, porque a terceira parte do `ORDER` é `w+` **ou** `(FINWOU|(updates+,DOFINALS))+`, nunca
misturado. `wkb1` mapeia mesmo `w` (`CipherSpec.mop:188-189` ↔ `Cipher.cryptsl:111`). Esta substituta
foi derivada por leitura do `fsm` e da regra, **não** executada — ao contrário da refutação acima.

> **Executada em 22/08/2026 (R5): a substituta é válida como palavra e impossível como programa.**
> `wrap` exige `WRAP_MODE` e `doFinal` exige `ENCRYPT_MODE`/`DECRYPT_MODE`; a JCA lança
> `IllegalStateException` nos dois sentidos. Ou seja: o `javax.crypto.Cipher` tem uma máquina de
> estados de modo que nem o `.mop` nem a regra modelam — os dois **sobre-aproximam** —, e uma palavra
> pode ser aceita pelo MOP, rejeitada pela regra e inexecutável em Java. O veredito `INCOMPARÁVEIS`
> sobrevive pela direção `regra \ MOP` (`g1 i2 i2 f2`, a reinicialização), que é independente e
> realizável. Toda testemunha publicada precisa dizer se é `ABSTRACT` ou `CONCRETE`.

**Consequência que passa do documento para o corpus.** O co-disparo `f1`/`f2` não é artefato da
sonda: está no `CipherSpec` de produção. Toda chamada `doFinal()` sem argumentos emite dois eventos,
e o segundo cai num estado que não o espera. Isto é candidato a defeito da spec — pertence à tabela
de §9, e não está lá.

### A5 — As testemunhas declaradas "idênticas" às do V4 não são as do V4

§5.2 afirma: *"Refeita a comparação com o `StateMachineGraph` que o `CrySLParser` devolve, o veredito
é o mesmo e as **duas testemunhas saem idênticas**"*. Mas:

| | §5.2 | documento de validações, V4 |
|---|---|---|
| MOP \ regra | `g1 i1 f1` | `g1 i2 doFinal()` |
| regra \ MOP | `g1 i1 i1 f2` | `g1 i2 i2 doFinal(byte[])` |

E o `mop.json` do arnês decide contra o documento-mãe: `CipherSpec.i1 = call(void Cipher.init(int,
Certificate, ..))` e `i2 = call(void Cipher.init(int, Key, ..))`. A expansão em prosa do §5.2
— *"init(ENCRYPT,k); init(DECRYPT,k)"* — é `i2 i2`, não `i1 i1`. O bloco do §5.2 não foi reescrito
quando os vereditos foram refeitos sobre o parser; só o parágrafo "Reconfirmado" foi acrescentado por
cima.

### A6 — A "formulação a usar" de §6 perde a maior das três parcelas

§6 apresenta como *"a única versão que um revisor não pode ler errado"*:

> Das 92 cláusulas […] 73 pertencem a regras que o conjunto cobre. Dessas, 54 são exprimíveis no
> substrato atual e 26 estão implementadas fielmente — 48 % do exprimível. As **19** restantes
> exigem `PredicateStore`; as outras **19** exigem specs que não existem.

26 + 19 + 19 = **64 ≠ 92**. A decomposição de §5.4 é `26 + 28 + 19 + 19`, e a parcela que a
formulação apaga é justamente o **débito de fiação (28)** — a maior das três e a única que §5.4
chama de "trabalho de spec". Pior, "as 19 restantes" vem logo depois de "26 de 54", onde o restante
natural é 28.

> **Recalibrado em 22/08/2026 (R5): a aritmética acima testa uma estrutura que o §6 não afirma; o
> defeito é de redação, e a evidência dele é melhor.** O §6 enunciava um **encaixe**
> (`92 ⊃ 73 ⊃ 54 ⊃ 26`), não uma partição: `73 − 54 = 19` e `92 − 73 = 19` fecham, e nada ali
> contradiz o §5.4. O que sustenta o achado é a última frase deste parágrafo, não a primeira — e ela
> ficou empiricamente demonstrada: **três leitores independentes** (esta auditoria e duas das três
> revisões externas) leram a mesma frase como partição e concluíram que faltava uma parcela. Isso
> falsifica a auto-afirmação do §6 de ser "a única versão que um revisor não pode ler errado". O
> reparo aplicado foi escrever a parcela de 28 por extenso e retirar a auto-afirmação — não corrigir
> uma conta que estava certa.

### A7 — Duas contagens de §5.4 não são derivá­veis de nenhum artefato

- **"SEM-BASE 16".** Onze agregações diferentes de `predicate_graph.csv` foram tentadas (67, 47, 30,
  26, 27, 22, 21, 35, 8, 6) e nenhuma dá 16. O `MOP-SEM-BASE` de `constraint_table.csv` é 4, e é
  outra métrica (M3). Só a metade "**8** são `remove()` em `@fail`" é verificável — e **confere
  exatamente** no commit medido.
- **A tabela FIEL 26 / PROJETADO 13 / CONFLADO 5 / AUSENTE 29.** Aritmeticamente coerente e coerente
  como partição (13 PROJETADO ⊆ as 19 aridade-2 em `ExecutionContext`; 5 CONFLADO + 23 de AUSENTE =
  o débito de fiação de 28; sem dupla contagem). Mas **nenhum arquivo registra a classificação por
  cláusula**: no snapshot, o `predicate_graph.csv` cita uma cláusula CrySL em apenas **18 das 85
  linhas** (14 distintas). A métrica de abertura de §5.4 repousa num censo manual não publicado.

Há ainda uma lacuna de definição: quando `PROJETADO` e `CONFLADO` se aplicam ao mesmo sítio — o caso
de `Mac ENSURES macced[out,inp]` → `setProperty(GENERATED_MAC, output)`, que é aridade-2 achatada
**e** sob `Property` de outro nome — o documento não dá critério de desempate. E o CSV marca esse
mesmo sítio com a coluna `clause` **vazia**, contradizendo o Javadoc de `Property.java`, que
argumenta que ele implementa `macced`.

### A8 — Três contagens refutadas por recontagem

| Onde | Doc | Medido |
|---|---:|---:|
| §12 e §13, specs multi-parâmetro no `generic` | **93** (39/28/18/7/1) | ~~97~~ — **REFUTADO em 22/08/2026 (R5): o documento está certo.** Parse real com `SpecExtractor` dá `buckets={1:25,2:39,3:28,4:18,5:7,6:1} multi=93`, literalmente os *buckets* do documento. O 97 é a contagem do **texto do cabeçalho**; a AST deduplica parâmetro por nome (`MOPParameters.add`), e essa dedup é ela própria um defeito — 11 specs do `generic` perdem declarações, e o tipo sobrevivente na tupla de indexação pode não ser o que os eventos ligam. O que faltava ao documento era **declarar a regra de contagem**. |
| §2, specs que absorvem uso incorreto | **12 das 23** | **16 das 23**, por dois critérios independentes que convergem. As 7 que não absorvem: `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`, `KeyPairSpec`, `RandomStringPassword`, `SecretKeySpec`. O sinal é **maior** do que o documento diz. |
| §3, constantes de `Property.java` | **24** | **26** — em todos os commits da janela (25 antes do gh105). Nunca foi 24. |

A legenda de §3 sobre esse mesmo arquivo também não se sustenta: *"O Javadoc de cada constante cita a
cláusula CrySL correspondente"* — apenas **3 das 26** têm Javadoc de cláusula (`GENERATED_CIPHER`,
`MACED`, `PREPARED_KEY_MATERIAL`); o quarto bloco `/**` do arquivo é o do próprio enum. Precisado em
22/08/2026 (R5).

A linha das "12 × 16 specs que absorvem uso incorreto" **não foi remedida** na quinta rodada e
continua em aberto.

### A9 — §9, "6 de 21 specs parametrizadas": a prosa contradiz as próprias frações

A linha afirma *"**Nenhum evento liga o parâmetro declarado**"* e em seguida lista `KeyPairSpec` 2/3,
`PBEKeySpecSpec` 2/4, `TrustManagerFactorySpec` 3/4. As seis frações **conferem exatamente** contra
`jca_android`, e o "21 de 23 parametrizadas" também. Mas em três das seis o parâmetro **liga** e o
fatiamento **funciona** — o que há ali é um evento fora da fatia (`c1` no `KeyPairSpec`, `f1`/`f2` no
`PBEKeySpecSpec`, `gtm1` no `TrustManagerFactorySpec`). A consequência declarada — *"o fatiamento é
no-op e a spec degenera para autômato global"* — só vale para as três com 0/N. A linha funde dois
defeitos distintos sob uma consequência que vale para metade deles.

### A10 — §11.5 afirma uma verificação que o documento de validações nega ter feito

- §11.5: *"o *nearest-wins* do Maven resolve `scala-library` para 2.13.14 sozinho, **verificado na
  árvore**"*.
- V10, no mesmo documento e no `NOTAS-BRUTAS`: *"A resolução *nearest-wins* de §11.5 **não foi
  exercitada** porque não declarei Scala 3."*

A mesma seção afirma e desafirma. Precisão adicional: `scala-library` nunca é "declaração direta" —
vem transitiva do `scala3-library_3` (profundidade 2), e é por isso que ganha do 2.11.12
(profundidade 3+). O mecanismo funciona; a formulação não. E o par 3.3.4 ↔ 2.13.14 não está checado
em lugar nenhum.

### A11 — §11.5: a ressalva sobre `main.basedir` está com a causa invertida

§11.5: *"a propriedade resolve para o alias `/pedro/...`, que não abre na JVM"*.

Medido diretamente: `/pedro` é o **ponto de montagem real** (`/dev/sda1`, ext4, via `mount`);
`/home/pedro/desenvolvimento` é que é o *symlink* para ele (`readlink -f`). Com a JVM do host,
`new File(p).exists()` e `canRead()` devolvem `true` para **os dois** caminhos. A JVM abre
`/pedro/...` sem problema — a restrição observada em outras ocasiões é do harness ou do container,
não do runtime Java.

### A12 — V10 não é reproduzível a partir do estado atual, e o documento-mãe não avisa

§11.5 relata que os quatro `pom.xml` foram *"acrescentados a `rvsec/pom.xml`"* e que os quatro
constroem. Hoje, `rvsec/rvsec/pom.xml` lista 7 módulos e nenhum é `rvsec-crysl`;
`git log --all -- '*rvsec-crysl*'` não devolve nada. Os poms sobrevivem **arquivados fora do reator**,
em `docs/handoff/20260821_arnes_validacoes/v10/rvsec-crysl/`. O documento de validações **diz** que
restaurou a árvore; o documento-mãe omite isso, e um leitor conclui que os módulos existem.

### A13 — §10.6: uma citação entre aspas que a fonte não tem — **REFUTADO em 22/08/2026 (R5)**

> **Este achado está errado, e o modo como errou importa mais que o erro.** A frase existe:
> `rvsec-paper/main.tex:811-814` traz *"First, these \csl \specs were validated by \crypto experts.
> Second, the \csl and JavaMOP \spec languages are similar. Third, …"* — é a **segunda das três
> *main reasons***, e esta auditoria citou a primeira e parou. A frase está também no draft de 2022,
> noutra redação. E o "22" está certo: `macros.tex:132` define `\nrules`=22 e `main.tex:824-825` diz
> *"In total, we write 22 JavaMOP \specs"*.
>
> A causa: o cofre `ase-journal/docs/notes/@torres-tse-2023.md` é indexado **por uso** — cada entrada
> é `## Use: <arquivo:linha>`, doze excertos escolhidos porque sustentam doze afirmações. Ausência
> ali nunca foi evidência de ausência no paper. Ler o fonte, que está na árvore em `$W/rvsec-paper/`.
> (Cuidado adicional: o `main.pdf` da árvore tem 12 páginas e é o draft pré-aceitação; o `main.tex` é
> que corresponde à edição publicada.)

O texto original do achado, mantido para registro:

§10.6 atribui ao TSE 2023 a frase *"the CrySL and JavaMOP specification languages are similar"*. O
cofre de citações do próprio grupo (`ase-journal/docs/notes/@torres-tse-2023.md`), com 12 excertos
conferidos contra o PDF publicado, **não contém essa frase nem nada próximo**. O excerto que cobre a
justificação é outro: *"we start from an existing set of CrySL JCA specifications for three main
reasons. First, these CrySL specifications were validated by crypto experts."* É paráfrase
apresentada como citação literal.

Duas ressalvas na mesma seção: o título completo é *Runtime Verification of Crypto APIs: **An
Empirical Study*** (TSE 49(10):4510-4525, DOI 10.1109/TSE.2023.3301660), e §10.6 corta o subtítulo. E
a tensão 22 × 23 specs **já foi resolvida em outro lugar do repositório**:
`ase-journal/openspec/changes/archive/2026-07-29-fix-factual-and-citation-accuracy/` identifica o 23º
como `SecretKeySpec.mop` e decidiu **parar de atribuir contagem de specs ao Torres**. §10.6
reintroduz a contagem sem a ressalva.

As demais citações estão corretas: Chen & Roşu, OOPSLA 2007; Meredith, Jin, Griffith, Chen & Roşu,
STTT 14(3), 2012.

### A14 — O "teto do oráculo" de §5.3 está subdimensionado por uma ordem de grandeza

§5.3 e §6 introduzem o teto do oráculo com base em três regras que perderam a seção `CONSTRAINTS`
inteira, "~9 cláusulas normativas apagadas". Isso **confere exatamente** (1+5+3, e a perda está mesmo
em `samples/jca/base/`, verificado nos três lugares). Mas o enquadramento geral subestima muito: a
recontagem das 33 regras contra `CrySL-Rules/` mostra **95 cláusulas no original contra 62 no
`api30`**, com **16 regras** perdendo cláusulas, não 3. Todo `offset >= 0`/`len > 0` sumiu; os quatro
`notHardCoded` sumiram; `SecretKeySpec` perdeu a allow-list `keyAlgorithm in {...}` **e** o
`neverTypeOf[keyMaterial, String]`; MessageDigest foi de 7 para 3, Signature de 4 para 1, Mac de 5
para 3.

> **Confirmado e precisado em 22/08/2026 (R5), com a regra de contagem declarada.** Sob R1 — uma
> cláusula por `;` dentro de `CONSTRAINTS`, comentários removidos, conjunções `&&` não separadas —
> os números batem: upstream 95 nas 33 regras, `api30` 62, e a diferença é **−33 líquido em 16
> regras** (34 deleções contra 1 acréscimo, `AlgorithmParameters` 1→2). Restrito às 22 regras que têm
> `.mop`, o vão é 80 → 55. Por conjunto de cláusulas: limites 45→15, `notHardCoded` 3→0 (**três**, e
> o quarto está fora das 33), `instanceOf` 2→0, `x in {…}` 19→17, `neverTypeOf` 6→5, implicações
> 20→25. Sob outras regras de contagem os totais mudam muito (separar `&&` dá 101/71; separar os
> lados de `=>` dá 117/87), então **nenhum número upstream deve entrar no artigo sem a regra escrita
> ao lado**.
>
> E há um modo de perda que esta contagem não captura: parte dos "limites" não foi deletada, foi
> **substituída** — a tríade `length[x] >= off+len; off >= 0; len > 0` virou `len > off`, que nada diz
> sobre o array. Somado à inversão de operador do `Cipher`, isso faz o teto do oráculo errar em três
> direções, não numa (§5.3 do plano).

Isso tem consequência direta sobre uma decisão de ferramenta: §5.3 conclui que *"o reconhecedor não
precisa suportar"* `notHardCoded` e `instanceOf` porque têm zero ocorrências no `api30`. O `grep`
confirma o zero — mas `notHardCoded` está em 4 regras originais (três delas cobertas por `.mop`) e
`instanceOf` em `Cipher.crysl`. A conclusão de ferramenta é tirada de um oráculo que o próprio §5.3
acabou de declarar defeituoso dois parágrafos antes.

---

## 2. Achados de precisão

Não mudam vereditos, mas um revisor os apontaria.

| Onde | Afirmação | Fonte |
|---|---|---|
| §4.2 | *"aceitaria um `doFinal()` solto"* | Falso. `Cipher.cryptsl:93` define `f1: doFinal()` e `:107` `FINWOU := f2\|f4\|f5\|f6\|f7` — `f1` **não** está em `FINWOU`, e `[f1]` é rejeitado sob **as duas** leituras. O que o gate aceita sozinho é `f2` = `doFinal(plainText)`, exatamente como a tabela três linhas acima diz. A prosa contradiz a própria tabela. |
| §5.3 | *"`Cipher:139..169` (11 cláusulas)"* | O intervalo contém **16** cláusulas. O 11 é o subconjunto *deferido*; `:141`–`:149` estão dentro do intervalo e **estão** transcritas. O número está certo, a citação de intervalo não. |
| §5.3 | *"8 delas são de fato mais permissivas […] e suas 158 linhas de alias"* | Das 8, só **4** ganham alcance de alias (MessageDigest 12, KeyGenerator 23, Mac 24, TrustManagerFactory 1). KeyStore, KeyManagerFactory, SecureRandom e SSLContext têm **zero** — ali `matches()` só acrescenta dobra de caixa. O próprio parágrafo diz "zero para KeyStore, SSLContext e SecureRandom" duas linhas adiante, o que torna a frase autocontraditória; e KeyManagerFactory, também zero, fica de fora da lista. |
| §5.4 | *"2 `NEGATES`"* (¶1) e *"2 cláusulas negadas no `MacSpec`"* (¶4) | Quatro cláusulas distintas. Os `NEGATES` são `SecretKey.cryptsl:30` e `PBEKeySpec.cryptsl:50`; as do Mac são `REQUIRES` com polaridade negada. Há ainda uma quinta cláusula negativa que o documento nunca menciona: `Cipher REQUIRES !macced[_, plainText]`. |
| §5.4 | *"8 das **44** arestas normativas"* | O 44 **é** derivável e reproduz-se exatamente (triplas distintas produtor-consumidor-predicado sobre as 33 regras), mas o documento nunca declara a definição, e as duas definições vizinhas dão 45 e 40. As 8 cadeias e as 3 no nível de `Property` foram reproduzidas com conjuntos byte-idênticos nos dois corpora — é a afirmação mais bem verificada de §5.4. |
| §5.2, §10.2 | *"`init ×8`, `update ×4`"* para o `Cipher` | O `Cipher` tem `updates := u1..u5` (**cinco**), confirmado no `crysl.json`. O `×4` é do `MessageDigest`/`Signature`. O par mistura duas regras. |
| §5.2 | *"Isto corrige o §13, que dizia 'dois dos três'"* | A correção **foi** aplicada — §13 hoje diz "Generaliza em 3". O problema é o inverso: a referência ficou órfã, e quem for ao §13 conferir não acha a frase citada. |
| §12 | *"os **8** casos não-emitíveis do §10.5"* | §10.5 tem **5** bullets; contando cláusulas dão **10**. Nenhuma leitura dá 8. |
| §13 | *"M4 tem teto desconhecido \| **MEDIDO — 74 % hoje**"* | Em §5.4, 74,0 % é o **teto**; a medição de hoje é 35,6 %. O advérbio troca teto por medição — exatamente o erro de leitura que §6 inteiro existe para prevenir. |
| §5.3 × §3 | *"9 das 11 allow-lists idênticas"* × *"7 idênticas / 3 alargadas / 1 estreitada"* | Mesmo denominador, numeradores diferentes, oráculos diferentes e não declarados: o anexo 04 compara `jca` contra `CrySL-Rules`; §5.3 compara contra o `api30`. São os dois eixos opostos do diagrama do próprio §2. |
| §8 | *"`neverTypeOf`/`noCallTo`/`callTo`/`notHardCoded` com parênteses (**6 arquivos**)"* | São **4** (`Cipher`, `KeyStore`, `KeyManagerFactory`, `PBEKeySpec`); `notHardCoded` não ocorre no `api30`. Os 6 só aparecem na união com `length(`, que o parágrafo seguinte apresenta como "um terceiro, medido depois". Número certo, atribuído ao conjunto errado. |
| §8 | a escada 20→22→30→**31** | Não fecha com os arquivos afetados: há **3** arquivos com `length(` (`Cipher`, `Mac`, `SecretKeySpec`), mas o salto é de **+1**. Como as duas residuais são nomeadas, dois desses três teriam de carregar com `length(` não corrigido — contradizendo a premissa de que a substituição é necessária. Só re-execução decide qual número está errado. |
| §8 | *"**3** são achado real"* com dois nomes de classe | Não há erro: `DSAGenParameterSpec.cryptsl` declara 2 eventos e `HMACParameterSpec` 1. O documento de validações escreve `DSAGenParameterSpec (×2)`; o `×2` perdeu-se na transcrição para §8. Basta repô-lo. |
| §8 | `155` eventos conferidos | Não reconcilia: as 2 regras rejeitadas declaram 7+3 = 10 eventos, e 167 − 10 = **157**. Sobra de 2 não explicada. A conclusão (3 achados reais) não depende disso. Some-se que `129` é grandeza diferente (assinaturas deduplicadas, não eventos) e é posta ao lado de 155 e 167 sem dizê-lo. |
| §5.1 | *"Três observações […] todas verificadas nos 23 monitores"*, com `RVM_eventNames` no bloco | Em `results/gh99_jca_android_monitors/…/MultiSpec_1RuntimeMonitor.java` as outras três linhas existem, mas **não há nenhuma ocorrência de `eventNames`** no arquivo inteiro. O array é emitido por umas gerações e não por outras — o M2-eff não pode depender dele sem qualificar a geração. |
| §7 | *"`getRetType()` é sempre `null`"* | É `null` só fora de `around` (`javamop.jj:1414,1433,1443`). O corpus não usa `around`, então a consequência sobrevive, mas "sempre" é falso. A segunda metade também escorrega: `MethodPattern.getType()` devolve um **padrão** com curinga `*` por omissão, não um tipo resolvido. |
| §7 | *"as chaves de `getHandlers()` vêm em minúsculas"* | Verdade em `PropertyAndHandlersExt`. Mas o `ast.PropertyAndHandlers` — o que se alcança pelo `MOPSpecFile` que `SpecExtractor.parse` devolve, o caminho que §11.1 recomenda — monta as chaves em `JavaMOPExtender.java:160-165` **sem `toLowerCase()`**. A instrução engana quem seguir §11.1. |
| §9 | `jca/KeyPairGeneratorSpec.mop:130` | O arquivo `jca` tem 118 linhas; o `@fail` está em **:110**. O defeito existe nos dois conjuntos e a unicidade confere nos dois, mas a linha compartilhada é do `jca_android` — e é a do `jca` que sustenta a consequência forte ("está no congelado, logo infla as medições publicadas"). |
| §9 | `PrettyPrinter.rsc:49` | `FORBIDDEN:` está em **:47**; `:49` está dentro do mesmo literal multilinha. `:139` está exato. |
| §9 | quatro linhas citam `.mop` sem nomear o conjunto | `TrustManagerFactorySpec.mop:101` e `:98-99`, `SecretKeySpecSpec.mop:45`, `KeyPairGeneratorSpec.mop:40-48` — todas `jca_android`. E os defeitos do `TrustManagerFactorySpec` **também estão no `jca` congelado** (`:62-65`), então o alcance real é maior do que a linha sugere. |
| §9 | *"`mechanism` desatualizado […] o CSV ainda diz o contrário"* | A coluna dessas duas linhas está **vazia**, não contrária. O defeito é "coluna em branco onde caberia `store`". |
| §9 | *"Typo em 1.5.2 **e** 3.0.1"* e *"a 3.0.1 removeu o objeto"* | Não checável aqui, e a evidência local vai na direção oposta: o único corpus não-1.5.2 na árvore (`CryptoAnalysis`, 2.8.0-SNAPSHOT) **não tem o typo** e **mantém** o objeto `alg`. |
| §9 | *"São 47 regras efetivas, não 49"* como consequência do typo do `SSLEngine` | 49 → 47 exige contar **também** a `OAEPParameterSpec`, que tem linha própria na tabela. A queda de 2 é atribuída a um defeito só, duplicando a contagem entre duas linhas. |
| §9, §4.2 | *"é **a** que o gate reporta como falha"* | `Cipher` é mesmo a única regra afetada pela precedência (verificado nos 33 `ORDER`), mas o G-ORDER reporta **4** divergências. A frase lida literalmente sugere falha única — e §13 fala das "outras duas falhas do gate". |
| §12 | *"`SecretKeySpec.mop` e `RandomStringPassword.mop` são exatamente isso hoje"* (`@match` sem `@fail`) | Confirmado nos JCA, mas a mesma forma ocorre em mais **7** arquivos do `generic_new`. Um defeito de 9 arquivos apresentado como defeito de 2. |
| §12 | `PBEKeySpecSpec.mop:26-32` | Correto em `jca_android`; em `jca` essas linhas são o evento `f2`. Sem o nome do conjunto a citação é ambígua. |
| §4.3 | *"traduz `encrypted[…] after **Updates**`"* | `Cipher.cryptsl:189` e o comentário do `.mop` escrevem `updates` minúsculo. `Updates` é o agregado do `Mac`/`Signature`. O documento afirma que "o comentário no arquivo diz isso" — diz com outro nome. |
| §4.3 | *"18 eventos órfãos em `jca`"* | Confere exatamente numa direção. Na outra, `jca/GCMParameterSpecSpec.mop:48` tem `ere : c1 \| c2` com os dois eventos nomeados `c1` — o símbolo `c2` não tem evento. Sob a definição de duas direções são 19 anomalias. |
| §5.2 | *"31 são determinísticas e nenhuma é não-determinística"* | Verdadeiro e conservador; a varredura independente sobre as **33** (Glushkov, precedência da gramática, agregados expandidos) dá **33/33**. Mede o corpus pela via que §8 diz que o componente **não** vai usar, e a segunda metade da frase é redundante. |
| §3 | *"14 dos 18 scripts parseiam `.mop` por regex"* | 14 importam `re`, mas um deles (`gh104_identity_discontinuity.py`) lê `.md`. O par exato é **13 de 18**. |
| §7 | *"zero `execution`"* | Zero como *pointcut*, mas a palavra ocorre 2 vezes em comentários. Convém dizer "nenhum pointcut `execution`". |
| §11.2 | `javamop.jj:234-255` | A região vai até **:256**. Off-by-one. |
| §11.2 | *"96 para 64 linhas, e as 12 de comentário viram zero"* | Reexecutado: 96→64 ✓ e 12 comentários ✓. Mas 96−64 = 32, e a diferença é 12 de comentário + **14 em branco** + 6 de reformatação. O documento omite que o writer também come as linhas em branco; quem confiar no "12" conclui que se perdem 20 linhas de código. |

---

## 3. Deriva de alvo móvel

O documento nunca carimba as suas tabelas com o commit medido, e o gh105 move o corpus todo dia. Sete
medições já não correspondem ao disco. Varridos 22 commits do diretório de dados, **não existe estado
em que `predicate_graph.csv` = 85 e `divergence_record.csv` = 181 coexistam** — os números de §3 vêm
de momentos diferentes.

| Onde | Doc | Estado atual | Onde o valor era verdadeiro |
|---|---:|---:|---|
| §3, `predicate_graph.csv` | 85 l. | **78** dados | `d64f3a40` / `5222a5d9` |
| §3, `divergence_record.csv` | 181 l. | **205** | `a7e97294` |
| §3, `Property.java` | 24 const. | **26** | nunca |
| §3, tarefas do gh105 | 30/74 | **34**/74 | o commit mais recente fala em 33/74 |
| §7, `condition(` em `jca_android` | 41 | **38** | — |
| §7, `ExecutionContext`/`PredicateStore`/migrados | 64/21/5 | **54/24/6** | `d64f3a40` (exato) |
| §9, `remove()` em `@fail` | 8 | **7** | `d64f3a40` (exato) |

O padrão é benigno na origem — no commit `d64f3a40` **quase todos** esses números são exatos, o que é
outra evidência de que a medição foi feita a sério — e maligno na apresentação: `5222a5d9` e
`e86bd270` saíram no mesmo dia, e o `predicate_graph.csv` foi tocado às 15h46 contra o documento às
16h03.

**Recomendação:** carimbar as tabelas de §3, §5.4 e §7 com o hash do commit medido. É a correção mais
barata do lote e a que mais protege o documento.

---

## 4. Duas afirmações de enquadramento

### O cabeçalho é auto-indulgente

*"Nenhuma [validação] derrubou uma conclusão deste documento."* O documento de validações, mais
cuidadoso, diz outra coisa: *"Nenhuma validação falseou o **desenho**."* A promoção de "desenho" para
"uma conclusão deste documento" não sobrevive ao próprio registro, que abre com *"Seis correções e
sete achados novos"*. Pelo menos quatro dessas correções derrubam proposições afirmadas como fato: o
mecanismo do §4.1 ("errado nas **duas** metades", incluindo a palavra `g4 g1` que §5.2 usava como
testemunha); o *"`Signature.cryptsl:51` não carrega"* de §9; o *"4 substituições levam 20→30"* de §8;
o *"dois dos três vereditos"* de §13. Acrescente-se o teto do oráculo, que muda o denominador de M3
**depois** de §13 já ter publicado "MEDIDO — 45,5 %", e o alcance de dois defeitos de §9 rebaixado de
vivo para latente.

A formulação honesta — e que o documento sabe escrever, porque escreve exatamente assim em cada bloco
de correção — é: *"nenhuma derrubou o desenho; seis derrubaram conclusões de detalhe, todas com
substituto medido, e uma derrubou uma via."*

### A declaração de escopo está desatualizada, e o remédio já existe

*"Escopo: análise, sem implementação"* era verdade nas três primeiras rodadas e deixou de ser na
quarta: §10 relata um gerador escrito e três specs geradas até compilar; §11.2 relata uma subclasse
de 37 linhas escrita e testada; V10 montou quatro `pom.xml` dentro de `rvsec/` e os construiu; e o
arnês tem 20 arquivos `.java` e 3 `.mop` versionados sob `docs/handoff/`.

O que continua verdadeiro é a distinção que o documento de validações faz e o cabeçalho não herdou:
*"Nenhuma linha de código de **produção** escrita; nenhum artefato OpenSpec criado; nenhuma issue
aberta"*, com a árvore restaurada ao fim do V10. O cabeçalho deveria dizer isso. Como está, um leitor
que abra §10 ou `v10/rvsec-crysl/` encontra código executado e conclui que o cabeçalho mente sobre
algo que na verdade está sob controle.

---

## 5. O que resistiu

Vale registrar, porque é a maior parte e porque a lista de defeitos acima dá impressão contrária.

**Reproduzido exatamente, de fonte independente:**

- §5.3 — 62 cláusulas nas 33 regras, 55 nas pareadas, e a matriz A/B/C/D/Ausente **inteira**
  (linhas 17/12/7/6/5/5/3, colunas 11/3/4/7/30), com a coluna Ausente saindo idêntica das 30 linhas
  `CRYSL-NAO-IMPLEMENTADO` do CSV classificadas por forma. As 55 chaves casam 55/55 com o `api30`,
  sem sobra nem falta. Os percentuais 45,5 % e 25,5 % reconstituem-se.
- §5.4 — 92 cláusulas (54/36/2), 32 predicados distintos, aridade 59/33 com máximo 2, 73 em regras
  cobertas, 54 exprimíveis (reconstruído do zero: 46 aridade-1 + 8 aridade-2 migradas), 19 de
  cobertura, 8 `remove()` em `@fail`, 64/21/5 sítios. Todos os quocientes conferem. As **8 cadeias
  realizadas e as 3 no nível de `Property`** saíram com conjuntos byte-idênticos nos dois corpora.
- §5.4 — o "11 specs que não existem" **está certo**, e a objeção óbvia (33−23 = 10) é que está
  errada: são 22 regras pareadas, porque `RandomStringPassword.mop` não tem contraparte CrySL.
- §4.2 — a precedência invertida do gate, com o docstring citado **literal, palavra por palavra**; a
  gramática Xtext nas linhas 103-134 exatas; a tabela de três palavras reproduzida por implementação
  independente dos dois parsers; e o censo "exatamente uma regra mistura `,` e `|` sem parênteses"
  confirmado por análise de profundidade sobre as 33.
- §5.2 — as três EREs citadas são literais; os formalismos conferem; `next(int)` é `protected`
  (`javap`); o pointcut de `f2` cobre mesmo `{f1,f2,f4}`; `s2` não tem transição de `init`.
- §4.1 — a guarda de `g4` lê o campo, o corpo de `g1` escreve o campo, `g1:39` antes de `g4:65`.
- §4.3 — zero `addError` em `@match` nos dois conjuntos (21 handlers cada); 18 órfãos no `jca` exatos;
  `alias match2 = s3` com o comentário citado.
- §9 — 19 das 25 linhas confirmadas contra arquivo e linha, incluindo a verificação empírica contra o
  `android.jar` real das APIs 26/30/33/35/36 (`DSAGenParameterSpec` ausente em 26/30/33, presente em
  35/36; nenhuma entrada `javax/xml/crypto/*` em nenhum nível).
- §7 — o parse 214/214 **reexecutado**; `call(`/`args(`/`target(` = 128/82/63; zero `execution`,
  `within`, `cflow`, `this` como pointcut; zero `full binding`/`perthread`; as armadilhas do
  `BlockStmt`, do `MOPNameSpace` e do campo estático do `JavaMOPParser` confirmadas com arquivo:linha;
  ambos os defeitos de sintaxe do `jca`.
- §11 — `DumpVisitor` 1670 linhas; `RVDumpVisitor` existe; `ptltl` 891 linhas; o pom raiz com
  21/2.11.12/19.0; a cadeia `javamop → rv-monitor → ptltl`; os dois jars no repositório local.
- §2 — a allow-list do `MessageDigestSpec` é **verbatim** o `api30:63` (seis literais, mesma ordem)
  contra `{SHA-256, SHA-384, SHA-512}` do original; o custo de 5.892/6.048 está no
  `divergence_record.csv:50-53`; as cinco allow-lists do anexo são subconjunto próprio das sete
  idênticas, sem incoerência.
- §8 — `CrySLSemanticSequencer` no jar e `bindISerializer()` no `RuntimeModule` (bytecode); a
  gramática tem exatamente 423 linhas; as 9 palavras reservadas são keywords; `SSLEngine` faz mesmo a
  disjunção de permutações; 158 alias com a procedência do Conscrypt no Javadoc; o conflito Guava
  33.5.0-jre × 19.0 lido direto dos dois poms.
- §10 — as três specs geradas **existem** em `v2/gerados/` com o `Gen.java`, e os quatro
  denominadores (5 eventos, 3 `ORDER`, 2 `CONSTRAINTS`, 5 predicados) batem exatamente com as regras
  de origem; 167 eventos e 140 sem tipo de retorno, ao número; `Mac.cryptsl:33,35` idênticos; 8
  gêmeos negativos; `KeyPairGeneratorSpec.mop:128`; 18 de 18 cabeçalhos apontando para o oráculo
  Java SE.

**Nenhum caminho citado como evidência está ausente.** O arnês bate item a item com o seu `README`.

---

## 6. Recomendações, em ordem de retorno

1. **Investigar o co-disparo `f1`/`f2` como defeito do `CipherSpec`** e, se confirmado, acrescentá-lo
   à tabela de §9 (A4). Vem primeiro porque é o único achado desta auditoria que aponta para o
   **corpus**, não para o texto: está na spec de produção e afeta o que o monitor acusa.
2. **Marcar a tabela de §10 como estimativa não medida**, ou depositar o arnês que a produziu. É o
   único bloco do documento sem evidência, e três dos seus números não fecham (A1).
3. **Corrigir §12: "4 substituições" → "5"** (A3). Uma palavra, e é a tabela que vira proposta.
4. **Fazer a conta de 30/33** que a decisão "um leitor por regra" implica, e corrigir a frase de §9
   que pendura a consequência no ramo errado (A2).
5. **Reescrever o bloco de testemunhas do `CipherSpec` em §5.2**, adotando `g1 i2 i2 f2` e a
   substituta `g1 i1 wkb1 f2`, e retirar a afirmação de que as testemunhas "saem idênticas" às do V4
   (A4, A5). A testemunha `g1 i1 f1` está refutada **por execução**, não por leitura.
6. **Repor a parcela de 28 na formulação de §6** (A6).
7. **Carimbar §3, §5.4 e §7 com o hash do commit medido** (§3). Correção mais barata do lote.
8. **Recontar o `generic`** (93 → 97, em três lugares) e as duas outras contagens refutadas: 12→16
   specs que absorvem, 24→26 constantes (A8).
9. **Publicar a classificação por cláusula de M4**, ou declarar a tabela como censo manual — e
   resolver o desempate PROJETADO × CONFLADO. Idem o "SEM-BASE 16", hoje não derivável (A7).
10. **Redimensionar o teto do oráculo** para 95→62 em 16 regras, e revisitar a conclusão de que o
   reconhecedor não precisa de `notHardCoded`/`instanceOf` (A14).
11. **Reescrever o cabeçalho** adotando a formulação do documento de validações, tanto quanto ao
    "nenhuma derrubou uma conclusão" quanto ao escopo (§4).
12. **Retirar as aspas da frase atribuída ao TSE 2023** e alinhar o 22 × 23 com a decisão já
    arquivada no `ase-journal` (A13).
12. **Corrigir §11.5**: retirar o "verificado na árvore" do *nearest-wins*, e retirar a ressalva sobre
    `/pedro/` não abrir na JVM, que é falsa (A10, A11). Registrar que a árvore foi restaurada depois
    do V10 (A12).
