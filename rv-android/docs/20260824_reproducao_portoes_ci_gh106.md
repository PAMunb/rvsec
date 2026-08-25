# Reprodução dos portões de CI pelo componente MOP–CrySL (gh106, G13b)

**Data:** 2026-08-24 · **Change:** `openspec/changes/gh106-mop-crysl-conformance/` · **Grupo:** G13b
· **Nenhum arquivo foi apagado por este documento.**

## Por que este documento existe

O critério de aposentadoria dos comparadores *ad hoc* é um só:

> **o *ad hoc* morre quando o componente reproduz o veredito dele, não quando o componente compila.**

Aposentar um portão antes de a substituição reproduzi-lo perde cobertura em silêncio — a mesma classe
de falha que esta linhagem já entregou duas vezes. Este documento é a **evidência de reprodução**: o
que foi rodado, com qual invocação literal, o que concordou, o que discordou, e quem estava certo em
cada discordância — decidido por medição, nunca por antiguidade.

**Resultado, em uma frase: nenhum dos cinco portões está reproduzido. Nenhum pode ser apagado hoje.**

## Carimbos da medição

Todas as medições abaixo foram tomadas sobre o mesmo corpus, no mesmo commit, na mesma máquina.

| Insumo | Estado |
|---|---|
| `.mop` `jca_android` (24 arquivos) | `rvsec@6192b57a`, árvore limpa (`git status --porcelain` vazio) |
| Oráculo do componente | `rvsec-cognicrypt@f2f4d3b`, `CrySL-Rules/` (49 regras, 47 sobem) |
| Oráculo dos portões `gh105`/`gh101`/`gh104` | `MetaCrySL/generated/api30/` (33 `.cryptsl` gerados) |
| Oráculo de valor do `gh104_gates.py` (D-15) | `RVSec-replication-package/tools/rules/` (49 `.crysl`) |
| Índice de observabilidade | `android.jar` API 30 (`$ANDROID_HOME/platforms/android-30`) |
| Mapa de alfabeto | `data/jca_android/order_alphabet_map.csv`, lido e nunca escrito (INV-CONF-12) |
| `data/jca_android/` ao fim das medições | limpo, exceto o *append* declarado na seção "Fronteiras de escopo" |

Nada foi escrito em `data/`: toda saída do componente foi para um diretório de rascunho.

## O fato que atravessa quatro dos cinco portões

Os quatro portões `gh10*` leem o corpus **gerado** `MetaCrySL/generated/api30/*.cryptsl`. O
componente lê **um único oráculo**, o *upstream* `rvsec-cognicrypt/CrySL-Rules` (decisão D-06), e o
lê pelo `CrySLModelReader` do próprio Xtext, byte a byte, sem normalizador (INV-CONF-12 proíbe
consertar o insumo no lugar).

Isso foi medido, não suposto. Copiando os 33 `.cryptsl` para `.crysl` e passando-os ao levantador do
componente:

```
OK 20  FAILED 13
```

**13 das 33 regras geradas estão fora da gramática CrySL** — entre elas exatamente as que sustentam
os vereditos mais interessantes dos portões: `Cipher`, `KeyGenerator`, `KeyPairGenerator`,
`KeyStore`, `Mac`, `SSLContext`, `Signature`, `SecretKeySpec`, `PBEKeySpec`, `KeyManagerFactory`,
`AlgorithmParameters`, `DigestInputStream`, `DigestOutputStream`. As causas, lidas do próprio erro do
leitor, são duas: a palavra reservada `alg` usada como nome de objeto (o mesmo defeito que o
`OAEPParameterSpec` do *upstream* tem) e argumentos de predicado escritos entre parênteses onde a
gramática pede colchetes (`mismatched input '(' expecting '['`).

Consequência para este documento: onde um portão decide sobre uma dessas 13 regras, **o componente
não tem como reproduzir o veredito sobre o mesmo insumo histórico**. Isso não é um defeito do
componente nem do portão — é uma medição, e ela limita o que a reprodução pode alcançar.

---

## Portão 1 · `scripts/gh105_order_gate.py` × M2 do componente

### Invocações (literais)

```
uv run python scripts/gh105_order_gate.py --sets jca_android          # saída: 13 passed, 0 failed, 9 allow-listed, 2 skipped de 24; exit 0
uv run python <scratch>/dump_order_gate.py                            # mesma execução, nome a nome (o JSON do portão só conta os acordos)
```

```
java -cp <componente + classpath runtime> br.unb.cic.rvsec.crysl.crysl.cli.ConformanceCli compare \
  --mop-dir   rvsec/rvsec/rvsec-mop/src/main/resources/jca_android \
  --corpus    jca_android --commit 6192b57a \
  --rules-dir rvsec-cognicrypt/CrySL-Rules --oracle-commit f2f4d3b \
  --alphabet  rvsec/rv-android/data/jca_android/order_alphabet_map.csv \
  --android-jar $ANDROID_HOME/platforms/android-30/android.jar \
  --out <scratch>/compare-out
```

Saída, que reproduz dígito por dígito as figuras de registro do G05 5.8:

```
specifications: 24 lifted, 0 did not lift
rules:          47 lifted, 2 did not lift
pairing:        22 pairs, by declared type
vitality:       2 refused by M0, 21 paired specifications received M1-M4
exit 0
```

E uma **execução de controle**, que é o que torna a adjudicação decidível: o mesmo `compare` com
`--rules-dir` apontando para os `.cryptsl` do `api30` copiados como `.crysl` — ou seja, o componente
com o oráculo do portão. Ela produz 12 pares e 11 vereditos M2 (as outras 13 regras não sobem).

### Tabela veredito a veredito (24 especificações)

`plena` = mesma existência de divergência **e** mesma direção · `parcial` = mesma existência,
direção diferente · `discorda` = existência diferente.

| # | Especificação | G-ORDER (`api30`) | M2 do componente (*upstream*) | Controle (M2 sobre `api30`) | Acordo |
|---:|---|---|---|---|---|
| 1 | CipherInputStreamSpec | allow-listed · `c1 r1 c` na regra | EQUIVALENT (N-REN) | EQUIVALENT **sob N2** | discorda |
| 2 | CipherOutputStreamSpec | allow-listed · `c2 c` no `.mop` | MOP_MORE_PERMISSIVE | MOP_MORE_PERMISSIVE | plena |
| 3 | CipherSpec | allow-listed · `g1 i1 u1` no `.mop` | INCOMPARABLE (1 recusa) | regra não sobe | parcial |
| 4 | DHGenParameterSpecSpec | pass | EQUIVALENT | EQUIVALENT | plena |
| 5 | GCMParameterSpecSpec | pass | EQUIVALENT | EQUIVALENT | plena |
| 6 | HMACParameterSpecSpec | pass | EQUIVALENT | EQUIVALENT | plena |
| 7 | IvChainJunction | skipped · sem linhas no mapa | sem par (24 → 22 pares) | sem par | plena (ambos declinam) |
| 8 | IvParameterSpec | pass | EQUIVALENT | EQUIVALENT | plena |
| 9 | KeyGeneratorSpec | allow-listed · `g1 g1 gk` no `.mop` | MOP_MORE_RESTRICTIVE (N-REN + N1, 1 recusa) | regra não sobe | parcial |
| 10 | KeyManagerFactorySpec | pass | EQUIVALENT (1 recusa) | regra não sobe | plena |
| 11 | KeyPairGeneratorSpec | pass | MOP_MORE_RESTRICTIVE (2 recusas) | regra não sobe | discorda |
| 12 | KeyPairSpec | allow-listed · sequência vazia na regra | EQUIVALENT | **MOP_MORE_RESTRICTIVE, testemunha ε** | discorda |
| 13 | KeyStoreSpec | allow-listed · `g2 l1` na regra | MOP_MORE_RESTRICTIVE (1 recusa) | regra não sobe | plena |
| 14 | MacSpec | pass | INCOMPARABLE (1 recusa) | regra não sobe | discorda |
| 15 | MessageDigestSpec | pass | MOP_MORE_RESTRICTIVE (1 recusa) | **MOP_MORE_RESTRICTIVE (1 recusa)** | discorda |
| 16 | PBEKeySpecSpec | pass | EQUIVALENT | regra não sobe | plena |
| 17 | PBEParameterSpecSpec | pass | EQUIVALENT | EQUIVALENT | plena |
| 18 | RandomStringPassword | skipped · sem linhas no mapa | sem par + recusada por M0 | idem | plena (ambos declinam) |
| 19 | SSLContextSpec | allow-listed · `g1 Init se1 se1` no `.mop` | MOP_MORE_PERMISSIVE | regra não sobe | plena |
| 20 | SecretKeySpec | allow-listed · `d` na regra | **recusada por M0 — sem veredito** | recusada por M0 | discorda |
| 21 | SecretKeySpecSpec | pass | EQUIVALENT | regra não sobe | plena |
| 22 | SecureRandomSpec | allow-listed · `c1 c1` no `.mop` | MOP_MORE_RESTRICTIVE (2 recusas) | **INCOMPARABLE** | parcial |
| 23 | SignatureSpec | pass | EQUIVALENT | regra não sobe | plena |
| 24 | TrustManagerFactorySpec | pass | EQUIVALENT (1 recusa) | regra não sobe | plena |

**Contagem: 15 plena · 3 parcial · 6 discorda.**

### Adjudicação de cada discordância e de cada parcial

Nenhuma delas se decide por antiguidade. O portão já leu o `ORDER` com precedência invertida na
própria história (gh105 tarefa 7.1), então a suspeita é simétrica; o que decide é a medição de
controle.

**1 · CipherInputStreamSpec — os dois estão certos sobre o mesmo fato, e discordam sobre onde
escrevê-lo.** O `c1` da regra `api30` é `CipherInputStream(InputStream)`, que o android-30 declara
`protected`. Lido nas duas regras: o `api30` declara `c1: CipherInputStream(is)` e
`c2: CipherInputStream(is, ciph)`; o *upstream* declara **só** o construtor de dois argumentos. O
portão reporta a divergência e a guarda em `gate_allowlist.csv` com a razão; o componente lê o *access
flag* do `android.jar` (`Observability`) e aplica **N2** — o controle sai `EQUIVALENT under N2`,
com a exceção impressa ao lado do veredito em vez de guardada num CSV. Sob o *upstream* a pergunta
nem existe. **Fato reproduzido; veredito não, porque a exceção foi internalizada.**

**12 · KeyPairSpec — a discordância é o oráculo, e o controle reproduz o portão letra por letra.**
`api30`: `ORDER co?, (pu*, pr*)*` — o construtor é opcional, logo a sequência vazia é aceita pela
regra e recusada pelo `ere`. *Upstream*: `ORDER Con, (GetPubl | GetPriv)*` — o construtor é
obrigatório, e as duas linguagens coincidem. Entregando ao componente o oráculo do portão, ele emite
`MOP_MORE_RESTRICTIVE` com testemunha **ε**, que é exatamente `the empty sequence is accepted by the
api30 ORDER and rejected by the specification`. **O portão está certo sobre o `api30`; o componente
está certo sobre o *upstream*; a decisão de qual é o oráculo é D-06.**

**15 · MessageDigestSpec — aqui o oráculo não é a causa, e o controle prova isso.** Sob o `api30`, o
componente também diz `MOP_MORE_RESTRICTIVE`, com 1 recusa. A causa é **D-20**: o levantamento recusa
`getInstance` como `Unknown{OverlappingDispatch}` porque um evento aceito e seu gêmeo negado
reivindicam a mesma chamada sob `condition`s complementares, e a letra sai de `SpecModel.order`. O
portão não modela despacho separado por guarda e mantém a letra. **Os dois comparam linguagens
diferentes, e só o componente diz isso**: projetando a letra recusada também para fora da regra, o
veredito volta a `EQUIVALENT`, que é o `pass` do portão. Nenhum dos dois erra; o componente revela um
estreitamento que o portão resolve em silêncio.

**11 · KeyPairGeneratorSpec e 14 · MacSpec — mesma causa que 15.** Ambos são *refusal-borne* (2 e 1
recusas). O G10 registra que `KeyPairGeneratorSpec` volta a `EQUIVALENT` quando a letra recusada sai
também da regra. `MacSpec` fica `INCOMPARABLE` porque, além da recusa, carrega a ε-erasure declarada
de `updateBuffer` (`update(ByteBuffer)`, sobrecarga que o android-30 declara e o `api30` não). Em
ambos, **o portão mede a linguagem do arquivo e o componente mede a linguagem que ele conseguiu ler,
com a diferença anotada** — e a anotação é o produto, não o defeito.

**20 · SecretKeySpec — fronteira de escopo deliberada, não erro de nenhum lado.** M0 recusa a
especificação (`@match` não vazio, sem `@fail`, sem `addError`) e INV-CONF-09 diz que uma
especificação recusada **não recebe** os vereditos de M1–M4: a passagem por M2 nem é invocada. O
portão emite um veredito assim mesmo (`d` = `destroy()`, que o `.mop` não observa porque lança em
ambas as implementações). **O componente decidiu não medir aqui; isso está registrado como fronteira
de escopo** (ver a seção final).

**3 · CipherSpec (parcial) — as duas testemunhas se reproduzem mutuamente.** O portão acha só a
palavra do lado `.mop`, `g1 i1 u1`; o componente acha `INCOMPARABLE` e sua testemunha do lado `.mop`
é `javax.crypto.Cipher.getInstance · init · update` — **a mesma palavra, letra por letra**. A direção
extra (`regra \ MOP`) vem do oráculo *upstream* e é a `g1 i2 i2 f2` publicada, que o G10 já registrou
como reproduzida. **Acordo no que é comparável; a diferença é o oráculo.**

**9 · KeyGeneratorSpec (parcial) — a diferença é N1, e N1 é declarada.** O portão acha `g1 g1 gk`: a
folga da repetição `g1+`. O componente aplica **N1** (fatiamento paramétrico: o monitor gerado indexa,
`MapOfMonitor` por M0.1, logo uma instância vê no máximo uma criação), o que apaga exatamente palavras
com dois `g1`, e sobra a direção oposta. **O portão está certo sobre o `ere` lido sem fatiamento; o
componente está certo sobre a linguagem que o monitor gerado pode exibir** — e imprime a normalização
ao lado do veredito, que é o que torna os dois vereditos comparáveis em vez de apenas diferentes.

**22 · SecureRandomSpec (parcial) — o controle mostra que o componente também acha a palavra do
portão.** Sob o `api30`, o componente sai `INCOMPARABLE`, isto é, com as duas direções vivas — a do
portão (`c1 c1`) inclusive. Sob o *upstream* sobra só `MOP_MORE_RESTRICTIVE`, por dois motivos já
medidos no G10 10.13: **N2 é vazia contra o *upstream*** (o `next(int)` protegido para o qual ela foi
escrita é um artefato do `api30`) e as linhas `order-unmapped` de `next1`/`next3` apagam chamadas que
a regra *upstream* de fato ordena.

### Veredito do portão 1

> **Ainda não.** 15 de 24 em acordo pleno. As nove restantes têm causa medida em cada caso, e **duas
> delas são estruturais**: o oráculo é outro (D-06) e 13 das 33 regras `api30` não são legíveis pela
> gramática CrySL. Enquanto o portão for a única coisa que mede o `api30`, apagá-lo perde cobertura.

---

## Portão 2 · `tests/parity/test_gh105_predicate_gates.py` × M4 do componente

### Invocações (literais)

```
uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh105_predicate_gates.py
→ 73 passed in 5.51s · exit 0
```

```
cp data/jca_android/predicate_graph.csv <scratch>/graph_seed.csv
uv run python scripts/gh105_predicate_graph.py --sets jca_android --graph <scratch>/graph_seed.csv --emit
→ jca_android files=24 read=24 skipped=0 sites=70 · findings: 0 failing, 0 allow-listed, 0 informative · exit 0
→ a cópia regenerada é byte a byte idêntica ao CSV commitado (data/jca_android intocado)
```

O lado do componente é o `predicate_graph.csv` emitido pelo mesmo `compare` do portão 1 (103 linhas:
60 sítios mais 43 cláusulas sem sítio).

### Tabela sítio a sítio (contagem por arquivo, chave `predicado × polaridade × aridade`)

| Arquivo | Sítios no portão | Sítios no componente | Acordo |
|---|---:|---:|---|
| CipherSpec | 7 | 7 | sim |
| DHGenParameterSpecSpec | 1 | 1 | sim |
| GCMParameterSpecSpec | 3 | 3 | sim |
| HMACParameterSpecSpec | 1 | 1 | sim |
| **IvChainJunction** | **8** | **0** | **não — sem par** |
| IvParameterSpec | 3 | 3 | sim |
| KeyGeneratorSpec | 4 | 4 | sim |
| KeyManagerFactorySpec | 3 | 3 | sim |
| KeyPairGeneratorSpec | 1 | 1 | sim |
| KeyPairSpec | 4 | 4 | sim |
| KeyStoreSpec | 3 | 3 | sim |
| MacSpec | 3 | 3 | sim |
| MessageDigestSpec | 1 | 1 | sim |
| PBEKeySpecSpec | 3 | 3 | sim |
| PBEParameterSpecSpec | 3 | 3 | sim |
| SSLContextSpec | 4 | 4 | sim |
| **SecretKeySpec** | **2** | **0** | **não — recusada por M0** |
| SecretKeySpecSpec | 3 | 3 | sim |
| SecureRandomSpec | 5 | 5 | sim |
| SignatureSpec | 5 | 5 | sim |
| TrustManagerFactorySpec | 3 | 3 | sim |
| **total** | **70** | **60** | 60 de 60 nos 21 arquivos compartilhados |

Sobre os 21 arquivos que os dois medem, o *multiconjunto* de sítios é **idêntico**: zero chaves só do
portão, zero chaves só do componente.

### O censo de colocação, que é o que o teste afirma

`test_the_graph_reproduces_the_measured_placement_census` afirma sete números. Comparando-os com o
que o componente emite, restrito aos 21 arquivos compartilhados:

| Veredito | Portão (21 arquivos) | Componente | Acordo |
|---|---:|---:|---|
| `read:condition-guard` | 0 | — (sem discriminador) | **não verificável** |
| `read:body` | 26 | 26 | sim |
| `read-absent:body` | 3 | 3 | sim |
| `write:acceptance` | 25 | — | **não reproduzido** |
| `write:body` | 5 | 30 | — |
| `write:*` (dobrado) | 30 | 30 | sim |
| `negate:body` | 1 | 1 | sim |
| `remove:fail` / `bookkeeping:*` | 0 | 0 | sim |

**Adjudicação — o componente declara a perda, e ela está no código, não escondida.**
`CompareRun.sitesOf` diz, textualmente, que *"o evento em que um sítio se encontra e se ele está no
corpo de um evento ou num handler `@match` não têm fonte no levantamento atual, de modo que todo
sítio atravessa como sítio de corpo sem nome de evento"*. As consequências, medidas:

1. a coluna `event` do CSV emitido é **vazia** nas 60 linhas;
2. `write:acceptance` nunca é emitido — o tipo `SiteKind.MATCH` existe em `-core` e nada o produz;
3. `read:condition-guard == 0` — a asserção mais importante do censo, porque é a que a migração do
   gh105 dirigiu a zero — **não tem contraparte**: se uma leitura em guarda reaparecesse, o componente
   não a acusaria.

O item 3 é o bloqueio real deste portão. Os itens 1 e 2 são perdas de refinamento; o item 3 é perda de
cobertura.

### O que dos 73 testes não é reprodutível por natureza

Cerca de cinquenta dos 73 testam o **leitor Python** (`scripts/gh105_predicate_graph.py`):
neutralização de comentários e literais preservando *offsets*, o discriminador `Property.`, resolução
de `alias`, divisão de argumentos em vírgulas de topo, arquivo desbalanceado reportado e não meio
lido. Eles não têm veredito para o componente reproduzir — testam um leitor que o levantamento Java
substitui. **Morrem com o leitor, não por reprodução**, e isso é uma decisão sobre o leitor, não sobre
o portão.

### Veredito do portão 2

> **Ainda não.** O censo de sítios reproduz exatamente (60 de 60 nos 21 arquivos compartilhados) e a
> distribuição de vereditos reproduz uma vez dobrado `write:acceptance` em `write:body`. Faltam três
> coisas: os 10 sítios dos dois arquivos que o componente não mede, a divisão
> `body`/`acceptance` com o nome do evento, e — o que bloqueia de fato — a asserção
> `read:condition-guard == 0`, que o componente não sabe fazer.

---

## Portão 3 · `scripts/gh101_conformance_check.py`

### Invocação (literal)

```
uv run python scripts/gh101_conformance_check.py -o <scratch>/gh101.csv
→ "23 verdicts, none blank" · exit 0
→ 11 uncontradicted · 10 anchored · 2 no-anchor
```

O portão roda sobre o conjunto **arquivado** `jca_android_bug_predicate/` (23 `.mop`) contra o
`api30`, e não sobre o `jca_android` de hoje — é assim de propósito (INV-INS-118: o congelamento e os
registros de divergência do gh101 continuam resolvendo sobre o artefato em que foram computados).
Para comparar sobre **o mesmo insumo histórico**, o componente foi rodado com `--mop-dir` no conjunto
arquivado e `--rules-dir` nas regras `api30`:

```
… compare --mop-dir …/jca_android_bug_predicate --corpus jca_android_bug_predicate --commit 6192b57a \
          --rules-dir <scratch>/api30-rules --oracle-commit MetaCrySL-generated-api30 …
→ 23 lifted, 0 did not lift · 20 rules lifted, 13 did not · 12 pairs · 2 refused by M0, 11 received M1-M4
```

### Tabela veredito a veredito (23 especificações)

| Especificação | gh101 | M3 do componente sobre o mesmo insumo | Alcançável? |
|---|---|---|---|
| CipherInputStreamSpec | uncontradicted | 1 `CRYSL-NAO-IMPLEMENTADO` (cláusula de comprimento, não de pertinência) | sim, coerente |
| CipherOutputStreamSpec | uncontradicted | 1 `CRYSL-NAO-IMPLEMENTADO` (idem) | sim, coerente |
| CipherSpec | no-anchor | — | **não: `Cipher.cryptsl` não sobe** |
| DHGenParameterSpecSpec | uncontradicted | sem cláusula | sim, concorda |
| GCMParameterSpecSpec | uncontradicted | 1 `IGUAL` | sim, escopos diferentes |
| HMACParameterSpecSpec | uncontradicted | sem cláusula | sim, concorda |
| IvParameterSpec | uncontradicted | sem cláusula | sim, concorda |
| KeyGeneratorSpec | anchored | — | **não: regra não sobe** |
| KeyManagerFactorySpec | anchored | — | **não: regra não sobe** |
| KeyPairGeneratorSpec | anchored | — | **não: regra não sobe** |
| KeyPairSpec | uncontradicted | sem cláusula | sim, concorda |
| KeyStoreSpec | anchored | — | **não: regra não sobe** |
| MacSpec | anchored | — | **não: regra não sobe** |
| MessageDigestSpec | anchored | 1 `IGUAL` + 2 `CRYSL-NAO-IMPLEMENTADO` | **sim, reproduz** |
| PBEKeySpecSpec | uncontradicted | — | **não: regra não sobe** |
| PBEParameterSpecSpec | uncontradicted | 1 `IGUAL` | sim, escopos diferentes |
| RandomStringPassword | no-anchor | sem par | sim, concorda |
| SSLContextSpec | anchored | — | **não: regra não sobe** |
| SecretKeySpec | uncontradicted | recusada por M0 | **não** |
| SecretKeySpecSpec | uncontradicted | — | **não: regra não sobe** |
| SecureRandomSpec | anchored | 1 `IGUAL` | **sim, reproduz** |
| SignatureSpec | anchored | — | **não: regra não sobe** |
| TrustManagerFactorySpec | anchored | 1 `IGUAL` | **sim, reproduz** |

**Alcançáveis: 9 de 23.** Dos quatro `anchored` alcançáveis, três reproduzem como `IGUAL` (a lista
segue a cláusula de pertinência da regra gerada) — o quarto não existe: todos os demais `anchored`
caem nas 13 regras ilegíveis. Dos `uncontradicted`, os que o componente alcança concordam, com uma
ressalva de escopo: `uncontradicted` do gh101 é uma afirmação **sobre cláusulas de pertinência**
(`x in {…}`), enquanto o M3 mede a seção `CONSTRAINTS` inteira, de modo que `GCMParameterSpecSpec` e
`PBEParameterSpecSpec` recebem um `IGUAL` sobre uma cláusula que o gh101 nem olha.

### O que do gh101 fica **fora** do escopo do componente

- **`spelling_variants`** — grupos *dentro* da própria lista permitida que nomeiam o mesmo algoritmo
  (`HMAC-SHA256` ao lado de `HmacSHA256`), calculados **sem referência a regra nenhuma**. O componente
  compara artefato contra oráculo e nunca faz um censo intralista. Nada a reproduzir.
- **`changed_from_jca`** — o *diff* contra a semente congelada `jca`. O componente compara um corpus
  contra o oráculo, nunca dois corpora entre si.
- **`aliases`** parcialmente: o componente conhece a tabela de *alias* (é o que produz
  `MOP-MAIS-PERMISSIVO`), mas não classifica um literal como "ausente da regra e dobrando sobre um
  membro dela".

### Veredito do portão 3

> **Ainda não.** 9 de 23 vereditos são alcançáveis sobre o insumo histórico; 14 não são, e 12 desses
> por um motivo estrutural (a regra `api30` correspondente está fora da gramática CrySL). Duas colunas
> do portão medem coisas que o componente decidiu não medir.

---

## Portão 4 · `scripts/gh104_gates.py`

### Invocação (literal)

O portão exige um monitor gerado, que não está na árvore; foi gerado para esta medição:

```
uv run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android --output <scratch>/monitors
→ 24 specification(s) · MultiSpec_1RuntimeMonitor.java is generated · exit 0 (1m15s)

uv run python scripts/gh104_gates.py \
  --monitor <scratch>/monitors/MultiSpec_1RuntimeMonitor.java \
  --allowlist data/jca_android/gate_allowlist.csv \
  --crysl ../../MetaCrySL/generated/api30 \
  --value-crysl ../../RVSec-replication-package/tools/rules \
  --alias data/jca_android/alias_table.csv \
  --constraint-table data/jca_android/constraint_table.csv --json <scratch>/gh104_gates.json
→ exit 1  ("ok": false)
```

**O portão está vermelho hoje, e por razões que antecedem esta change.** Registrado sem rodeios,
porque um documento que dissesse "verde" aqui seria o próprio defeito que esta change existe para
remover.

| Portão interno | Achados | Falhas | Em escopo do componente? |
|---|---:|---:|---|
| G-2 (linha toda-`fail`, dividida por cláusula) | 0 | 0 | **não** — lê as linhas de transição do monitor gerado |
| G-2a (evento inerte) | 11 | **3** | **não** — idem |
| G-2b' (laço no estado inicial) | 18 | 0 | **não** — idem |
| G-2c (estado inalcançável) | 2 | 0 | **não** — idem |
| G-2d (índice do `fail`) | 3 | 0 | **não** — idem |
| G-6' (métodos gerados × linhas de transição) | 0 | 0 | **não** — idem |
| G-ERE (símbolo sem declaração de evento) | 0 | 0 | parcial — M0/M1 leem o `.mop`, não o monitor |
| **G-CONF** (lista permitida × `CONSTRAINTS … in {…}`) | 80 notas | 0 | **sim** — é M3 |
| **G-PRED** (sítio de predicado perdido face à semente `jca`) | 23 | **23** | parcial — é M4, com outro oráculo |

As três falhas de G-2a são `PBEKeySpecSpec.f1`, `PBEKeySpecSpec.f2` e `SecureRandomSpec.g4` — eventos
cuja linha de transição é a identidade no monitor gerado. **Isso é exatamente o que o componente
declara não medir**: a nota de M0 no relatório diz que `M0.1` é um *proxy* de AST e que *"o oráculo
real é o monitor gerado"*. Sete dos nove portões internos leem o monitor gerado; o componente lê o
`.mop`. São medições diferentes, e nenhuma substitui a outra.

### G-CONF × M3, veredito a veredito

Os dois produzem **80 linhas** cada, no mesmo esquema (`spec,cryptsl_line,mop_line,verdict`) — o
mesmo esquema do `data/jca_android/constraint_table.csv` commitado. Ordem dos quatro vereditos abaixo:
`IGUAL / MOP-MAIS-PERMISSIVO / NAO-DERIVADO / CRYSL-NAO-IMPLEMENTADO`.

| Especificação | G-CONF | M3 do componente | Commitado | Acordo |
|---|---|---|---|---|
| CipherInputStreamSpec | 0/0/0/3 | 0/0/0/3 | 0/0/0/3 | sim |
| CipherOutputStreamSpec | 0/0/0/3 | 0/0/0/3 | 0/0/0/3 | sim |
| CipherSpec | 0/0/14/11 | 8/0/4/13 | 0/0/14/11 | **não** |
| DHGenParameterSpecSpec | 1/0/0/0 | 1/0/0/0 | 1/0/0/0 | sim |
| GCMParameterSpecSpec | 1/0/0/3 | 1/0/0/3 | 3/0/0/1 | sim |
| IvParameterSpec(Spec) | 2/0/0/1 | 3/0/0/0 | 2/0/0/1 | **não** |
| KeyGeneratorSpec | 1/0/0/1 | 0/1/0/1 | 1/0/0/1 | **não** (alias) |
| KeyManagerFactorySpec | 1/0/0/2 | 0/1/2/0 | 1/0/0/2 | **não** (alias + taxonomia) |
| KeyPairGeneratorSpec | 5/0/0/0 | 0/5/0/0 | 5/0/0/0 | **não** (alias) |
| KeyStoreSpec | 0/1/0/4 | 0/1/4/0 | 1/0/0/4 | **não** (taxonomia) |
| MacSpec | 0/1/0/4 | 0/1/0/4 | 0/1/0/4 | sim |
| MessageDigestSpec | 1/0/0/6 | 0/1/0/6 | 1/0/0/6 | **não** (alias) |
| PBEKeySpecSpec | 1/0/0/2 | 1/0/2/0 | 1/0/0/2 | **não** (taxonomia) |
| PBEParameterSpecSpec | 1/0/0/0 | 1/0/0/0 | 1/0/0/0 | sim |
| SSLContextSpec | 0/1/0/0 | 0/1/0/0 | 1/0/0/0 | sim |
| SecretKeySpecSpec | 1/1/0/1 | 1/1/1/0 | 1/1/0/1 | **não** (taxonomia) |
| SecureRandomSpec | 1/0/0/0 | 0/1/0/0 | 1/0/0/0 | **não** (alias) |
| SignatureSpec | 1/0/0/3 | 0/1/0/3 | 1/0/0/3 | **não** (alias) |
| TrustManagerFactorySpec | 1/0/0/0 | 0/1/0/0 | 1/0/0/0 | **não** (alias) |

**7 de 20 em acordo no veredito de quatro valores.** Projetando para *implementada × não
implementada* — isto é, dobrando `IGUAL`+`MOP-MAIS-PERMISSIVO` de um lado e
`NAO-DERIVADO`+`CRYSL-NAO-IMPLEMENTADO` do outro — sobem para **17 de 19**.

**Adjudicação, com as duas causas separadas e medidas:**

- **Alias (7 especificações).** `CompareRun.constraintVerdict` classifica como `MOP-MAIS-PERMISSIVO`
  toda cláusula implementada cuja lista é consultada *através da tabela de alias*, com a razão escrita
  ao lado: *"uma lista permitida transcrita caractere por caractere é mais permissiva que a regra
  quando é consultada através da tabela"*. O G-CONF chama a mesma cláusula de `IGUAL`. **Não é
  discordância sobre o fato; é uma regra de contagem diferente, e a do componente é mais informativa
  porque separa transcrição de dobramento.** Nenhum dos dois está errado.
- **Taxonomia da recusa (4 especificações).** `NAO-DERIVADO` (a cláusula foi recusada) e
  `CRYSL-NAO-IMPLEMENTADO` (a cláusula existe e a especificação não a implementa) trocam de lugar em
  `KeyManagerFactorySpec`, `KeyStoreSpec`, `PBEKeySpecSpec` e `SecretKeySpecSpec`. Aqui os dois
  **discordam de fato** sobre qual é a natureza da omissão, e a causa não pôde ser isolada porque o
  oráculo estrutural do G-CONF é o `api30` e o do componente é o *upstream*: as regras
  correspondentes estão entre as 13 que não sobem.
- **CipherSpec (25 cláusulas dos dois lados).** As 11 cláusulas finais de comprimento/deslocamento
  concordam exatamente (`CRYSL-NAO-IMPLEMENTADO` nos dois). Nas 14 primeiras — as de valor — o G-CONF
  diz `NAO-DERIVADO` para todas e o componente diz 8 `IGUAL`, 3 `NAO-DERIVADO` e 2+1
  `CRYSL-NAO-IMPLEMENTADO`. `Cipher.crysl` é **a única regra** em que o oráculo de valor do portão
  (cópia *expert* congelada, D-15) difere do oráculo do componente: o *expert* traz `"CCM"` em duas
  cláusulas que o `rvsec-cognicrypt@f2f4d3b` não traz. Os outros 48 arquivos são idênticos byte a
  byte. **Nem o oráculo de valor explica sozinho a diferença**, e o oráculo estrutural (`Cipher` do
  `api30`) não sobe, então esta discordância **fica em aberto** e não pode ser adjudicada com o que
  está medido aqui.
- **IvParameterSpec.** O portão nomeia a especificação pelo nome da regra (`IvParameterSpecSpec`) e o
  componente pelo nome do arquivo (`IvParameterSpec.mop`); dobradas, ainda restam 3 cláusulas
  implementadas contra 2+1. Também em aberto.

### G-PRED, e por que suas 23 falhas não são sobre o componente

G-PRED compara o conjunto sob teste contra a semente congelada `jca` e reporta como *perdido* todo
sítio da semente que não reaparece. Os 23 relatórios têm a mesma forma:
`"lost": ["import br.unb.cic.mop.ExecutionContext;", "ExecutionContext.instance().validate(...)", …]`.
Ou seja: o portão está medindo **a migração de substrato do gh105**, que tirou o `jca_android` do
`ExecutionContext` e o pôs no `PredicateStore` (trajetória 64/21/5 → … → 0/70/21, que o componente
imprime na própria regra de contagem de M4). `"predicate_sites": 0` no relatório do portão é a mesma
notícia dita de outro jeito. **O portão está desatualizado em relação ao conjunto que guarda**, e essa
é uma conclusão sobre o portão, não sobre o componente.

### Veredito do portão 4

> **Ainda não** — e o portão está vermelho por conta própria (`exit 1`). Sete dos seus nove portões
> internos leem o **monitor gerado** e estão declaradamente fora do escopo do componente. Do que está
> em escopo: G-CONF reproduz 7 de 20 no veredito de quatro valores e 17 de 19 na projeção
> implementada/não-implementada, com duas causas identificadas e duas discordâncias em aberto; G-PRED
> mede a migração de substrato contra uma semente que a migração tornou obsoleta.

---

## Portão 5 · `scripts/gh104_baseline.py`

### Invocação (literal)

```
uv run python scripts/gh104_baseline.py --out <scratch>/gh104_baseline
→ "envelopes: 87; with an expected value: 63; disagreements: 0" · exit 0
→ diff -q data/gh104/baseline.json <scratch>/gh104_baseline/baseline.json → idêntico
```

O `--out` aponta para o rascunho de propósito: o `baseline.json` commitado não foi tocado, e a
identidade byte a byte é a prova de que a linha de base continua reprodutível.

### O que ele mede, e por que o critério não se aplica

O `gh104_baseline.py` é o instrumento da linha de base E0 do gh104: **legibilidade de relatórios de
violação**. Suas oito seções (`android_tier`, `article`, `comp162`, `definitions`, `inputs`,
`instrument`, `spec_sets`, `change`) leem CSVs de resultado de experimento — dois corpora produzidos
por *pipelines* diferentes, com leitores congelados dentro do próprio arquivo — e contam tipos de
erro, *mutes* por especificação, pegada estrutural e sítios `new ErrorDescription(`.

**Nenhuma dessas medidas está no escopo do componente.** O componente compara uma especificação
declarada com a regra que a ordena; não lê traço de execução, não lê CSV de violação e não conta
argumentos de `ErrorDescription`. A única seção que sequer toca o texto `.mop` é o censo
`addError`/`Log.v` por conjunto, e ele é sobre o `jca` congelado e o conjunto arquivado, não sobre o
`jca_android`.

### Veredito do portão 5

> **Não reproduzido — e não reprodutível por construção.** Ele não é candidato à aposentadoria pelo
> critério desta change, porque não há veredito seu para o componente reproduzir. Sobrevive por razão
> própria, não por dívida do componente.

---

## Quadro final

| Portão | Rodou? | Veredito | Acordos / discordâncias |
|---|---|---|---|
| `scripts/gh105_order_gate.py` | sim, `exit 0` | **ainda não** | 15 plena · 3 parcial · 6 discorda (de 24) |
| `tests/parity/test_gh105_predicate_gates.py` | sim, 73 passed | **ainda não** | 60/60 sítios · censo reproduz dobrado · 3 lacunas |
| `scripts/gh101_conformance_check.py` | sim, `exit 0` | **ainda não** | 9 de 23 alcançáveis · 14 fora de alcance |
| `scripts/gh104_gates.py` | sim, `exit 1` | **ainda não** | G-CONF 7/20 (17/19 dobrado) · 7 de 9 portões internos fora de escopo |
| `scripts/gh104_baseline.py` | sim, `exit 0` | **não aplicável** | 0 verificações em escopo |

**Nenhum arquivo foi apagado.** A aposentadoria de cada portão é uma change separada, com verificação
própria; embuti-la nesta esconderia a remoção dentro de uma change sobre outra coisa.

A continuação está aberta como **[PAMunb/rvsec#107](https://github.com/PAMunb/rvsec/issues/107)**,
com um bloqueio nomeado por portão e a regra de que nada é apagado antes de o item correspondente
estar fechado.

## Fronteiras de escopo registradas em `data/jca_android/divergence_record.csv`

Um portão que mede algo que o componente decidiu não medir não é uma falha do componente: é uma
**fronteira de escopo**, e precisa estar escrita como tal. Foram acrescentadas cinco linhas ao
`divergence_record.csv` — o único arquivo de `data/jca_android/` que este grupo pode escrever — no
esquema commitado (`file,hunk,kind,summary,reason,task`), com `kind = gate-scope` e `task = 13b.7`.
Nenhuma linha existente foi alterada.

| `file` | Fronteira |
|---|---|
| `jca_android/SecretKeySpec.mop` | M0 recusa a especificação e INV-CONF-09 lhe nega os vereditos de M1–M4; o G-ORDER emite um veredito assim mesmo (`d` = `destroy()`) |
| `jca_android/IvChainJunction.mop` | não emparelha com regra alguma (24 arquivos → 22 pares), logo não recebe M4; o grafo de predicados do gh105 conta 8 sítios nela |
| `jca_android/` (`predicate_graph.csv`, coluna `site_kind`) | o levantamento não distingue corpo de *handler* `@match` nem carrega o nome do evento: `write:acceptance` nunca é emitido e a coluna `event` sai vazia |
| `jca_android/` (`predicate_graph.csv`, `read:condition-guard`) | não há discriminador guarda/corpo; a asserção `read:condition-guard == 0`, que a migração do gh105 dirigiu a zero, não tem contraparte |
| `MetaCrySL/generated/api30/` | o componente lê um oráculo só (D-06) pelo `CrySLModelReader` do *upstream*; 13 das 33 regras geradas estão fora dessa gramática e nenhum veredito sobre elas é alcançável |

**Uma inconsistência declarada:** `data/jca_android/README.md` descreve os `kind` do
`divergence_record.csv` e não conhece `gate-scope`. O README é somente-leitura para este grupo
(INV-CONF-12), então a atualização fica para a change de aposentadoria, junto com a remoção dos
portões.
