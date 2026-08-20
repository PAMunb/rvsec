# Agente F — auditoria da decisão §3.1-bis (classe nova, antiga depreciada)

Data: 2026-08-20. Somente leitura; nenhum arquivo do repo foi editado.

Caminhos-base:
- `EC` = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java
- `RES` = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources

## Tarefa 1 — Superfície completa? VEREDITO: SIM, com uma omissão trivial (`instance()`)

### (a) Todos os membros públicos de `ExecutionContext.java`

| membro | linha | na lista do handoff? |
|---|---|---|
| `static ExecutionContext instance()` | 40 | **não** — omitido |
| `@Deprecated remove(Property)` | 52-57 | sim |
| `remove(Property, Object)` | 59-66 | sim |
| `setProperty(Property, Object)` | 80-87 | sim |
| `boolean validate(Property, Object)` | 96-98 | sim |
| `boolean isInAcceptingState(Object)` | 103-105 | sim |
| `setObjectAsInAcceptingState(Object)` | 112-114 | sim |
| `unsetObjectAsInAcceptingState(Object)` | 122 | sim |
| `boolean hasEnsuredPredicate(Object)` | 131-138 | sim |
| `reset()` | 143-146 | sim |

Não há outros membros públicos (construtor é privado; campos são privados). A única omissão
da lista do handoff é o acessador estático `instance()` — todo sítio de spec passa por ele
(`ExecutionContext.instance().<método>`), então "preservar a superfície" o inclui por
implicação; vale registrar no design.md, mas não muda a decisão.

### (b) Métodos chamados via ExecutionContext, por conjunto (grep sobre *.mop)

| método | jca | jca_android | bug_predicate | generic | generic_new |
|---|---:|---:|---:|---:|---:|
| `remove` (total) | 9 | 9 | 13 | 0 | 0 |
| `setProperty` | 49 | 49 | 58 | 0 | 0 |
| `validate` | 27 | 27 | 56 | 0 | 0 |
| `setObjectAsInAcceptingState` | 19 | 19 | 19 | 0 | 0 |
| `unsetObjectAsInAcceptingState` | 6 | 6 | 6 | 0 | 0 |

**Nenhuma spec chama nada fora da lista.** Prova de fechamento (jca): o censo do gate
(`tests/parity/test_gh104_specset_gates.py`, EXPECTED_CONSTRUCTS) fecha em 134 linhas =
23 imports + 27 validate + 49 setProperty + 9 remove + 25 accepting-state (19+6) + 1
comentário (`jca/MessageDigestSpec.mop:25`, menção em prosa). Não sobra linha para
`reset`, `hasEnsuredPredicate` ou `isInAcceptingState`. Não há chamadas multi-linha
(nenhuma linha termina em `ExecutionContext.instance()` pendurado).

### (c) Os 4 sítios de `remove(Property)` de 1 argumento no jca — CONFIRMADOS

- `jca/KeyManagerFactorySpec.mop:91` — `remove(Property.GENERATED_KEY_MANAGERS)`
- `jca/MacSpec.mop:87` — `remove(Property.GENERATED_MAC)`
- `jca/TrustManagerFactorySpec.mop:87` — `remove(Property.GENERATED_TRUST_MANAGER)`
- `jca/TrustManagerFactorySpec.mop:88` — `remove(Property.GENERATED_TRUST_MANAGERS)`

Os outros 5 `remove` do jca são de 2 argumentos. `jca_android` tem os MESMOS 4 sítios
1-arg (linhas 104, 99, 100, 101 — é cópia da semente). `jca_android_bug_predicate` tem
ZERO sítios 1-arg (os 13 são todos 2-arg). Ou seja: os únicos consumidores da sobrecarga
@Deprecated são o congelado e o alvo — e no alvo eles somem na migração (a classe nova
não a oferece), o que é coerente com §3 do plano (esses removes não traduzem cláusula
CrySL alguma).

### (d) `hasEnsuredPredicate` e `isInAcceptingState`: ZERO sítios em .mop — CONFIRMADO

Grep sobre os 5 conjuntos (214 .mop): zero ocorrências (os hits de `reset(` em
generic_new/jca são pointcuts de `InputStream.reset()`/`MessageDigest.reset()`, não do
store). Aparecem apenas em código Java de teste:

- Wrapper: `rvsec/rvsec-agent/src/test/java/br/unb/cic/misc/Assertions.java` —
  `mustBeInAcceptingState`/`mustNotBeInAcceptingState` (→ `isInAcceptingState`),
  `hasEnsuredPredicate(Object)`/`notHasEnsuredPredicate` (→ `hasEnsuredPredicate`),
  `hasEnsuredPredicate(Property,Object)` (→ `validate`).
- Consumidores (bench01, rvsec-agent/src/test/java/br/unb/cic/mop/bench01/): 16 testes —
  CipherInputStreamTest, CipherOutputStreamTest, CipherTest, DHGenParameterSpecTest,
  GCMParameterSpecTest, HMACParameterSpecTest, IvParameterSpecTest, KeyGeneratorTest,
  KeyManagerFactoryTest, KeyPairGeneratorTest, KeyStoreTest, MacTest, MessageDigestTest,
  PBEKeySpecTest, PBEParameterSpecTest, SecureRandomTest, SSLContextTest,
  TrustManagerFactoryTest (17 arquivos usam Assertions; SecureRandomTest:19 chama ainda
  `ExecutionContext.instance().reset()` direto — único sítio de `reset` fora da própria classe).
- Importante: `rvsec-agent/pom.xml:106` aponta `pathToMopFiles` para `resources/jca` —
  esses testes rodam contra o **jca** tecido, então continuam coerentes com a classe antiga.
- Não há NENHUM teste de ExecutionContext em rvsec-core/src/test nem rvsec-mop/src/test
  (rvsec-core testa eh/ e jca/util/; rvsec-mop testa o harness TraceRunner, que usa só
  ErrorCollector).
- Outro consumidor Java (não-teste): `rvsec-mop-defsuses/.../UseDefVisitor.java:21` usa a
  string `"ExecutionContext.instance()"` como prefixo de parsing (módulo a aposentar, §8).

## Tarefa 2 — Contagem por conjunto. VEREDITO: CONFIRMADA

Arquivos .mop que citam `ExecutionContext` / total de .mop:

| conjunto | citam | total |
|---|---:|---:|
| jca | 23 | 23 |
| jca_android | 23 | 23 |
| jca_android_bug_predicate | 23 | 23 |
| generic | **0** | 118 |
| generic_new | **0** | 27 |

Bate exatamente com a tabela do handoff §3.1-bis.

## Tarefa 3 — Viabilidade da classe nova. VEREDITO: VIÁVEL — nada em F0 exige tocar a antiga

F0 (plano, linhas 556-583) pede: chave híbrida (identidade no vínculo do objeto, valor
case-insensitive com splitters nas posições String/int/Integer), aridade N, retorno de
três valores em validate, chaves fracas com expurgo, thread-safety (ConcurrentHashMap +
newKeySet + holder estático). Nenhum item requer editar `ExecutionContext.java`:

**(a) validate() de 3 valores confinado — SIM.** A classe nova é um tipo novo; a assinatura
`boolean validate(Property,Object)` da antiga (EC:96) permanece intocada e os 27 sítios do
jca continuam ligando a ela. Confirmei 27 sítios de validate no jca (e 27 no jca_android,
que serão reescritos de qualquer forma em F2/F3). Única ressalva técnica: `condition()`
do JavaMOP exige expressão booleana — o retorno de 3 valores só é consumível no corpo do
evento, o que é exatamente o que F2 planeja (mover as leituras de condition() para o
corpo). Coerente, não bloqueante.

**(b) Estado estático compartilhado — existe na antiga, mas NÃO precisa ser compartilhado.**
A antiga é singleton (`private static ExecutionContext instance`, EC:23; lazy init
não-sincronizada; HashMap/HashSet não-thread-safe — os mapas são campos de instância do
singleton, i.e., estado global de processo na prática). A nova tem seu próprio singleton;
zero acoplamento. Risco de duas semânticas no mesmo runtime: um APK é instrumentado a
partir de UM conjunto de specs (o monitor é gerado por `--specification-set`; CLAUDE.md
diz que os conjuntos são usados separadamente por experimento), então só um store recebe
chamadas em runtime — as duas classes coexistem no jar do rvsec-core, mas nenhum caminho
de código as conecta. Cenários residuais a registrar no design.md: (i) `custom`
(`--custom-specs-dir`) permitiria misturar .mop das duas famílias num mesmo monitor —
aí cada spec escreve no seu store e predicados não cruzam; é degradação silenciosa, vale
uma linha de doc ou gate; (ii) se `rvsec-agent/pom.xml` um dia apontar para `jca_android`,
o `Assertions.java` (que lê a classe antiga) passa a asserir contra um store nunca escrito
— item de migração futura, não desta change. `aspect/Coverage.aj` não usa ExecutionContext.

**(c) Envelope gh104 e ErrorType — independentes.** O envelope `v=1 code=... ev=...` é
emitido pelos .mop via `ErrorCollector`/`ErrorDescription` e parseado em
`rvsec-core/.../eh/ErrorDescription.java` (ENVELOPE_MARKER "v=1 ", linha 49; ENVELOPE_CODE
linha 63; ENVELOPE_EVENT linha 65). Grep: o pacote `eh` tem ZERO referências a
ExecutionContext, e ExecutionContext tem zero referências a `eh`. A classe nova não precisa
reimplementar nada do envelope; as specs continuam usando `import br.unb.cic.mop.eh.*`
inalterado. `Property.java` também é arquivo separado — a nova pode reusá-lo ou não, sem
tocar a antiga (aridade N provavelmente pede representação própria de predicado; decisão
de design da F0, não obstáculo).

## Tarefa 4 — G-PRED hoje e o que quebra. VEREDITO: reformulação necessária e MAIOR que trocar uma referência

**O que G-PRED assevera hoje (duas encarnações):**

1. `scripts/gh104_gates.py` (`predicate_divergences`, linhas 1014-1051; fiação 1454-1468):
   deriva o conjunto do monitor (nunca por CLI), resolve a semente congelada
   `resolve_set_dir("jca")` via RVSEC_HOME, e compara POR ARQUIVO a SEQUÊNCIA de linhas
   que contêm o marcador `PREDICATE_MARKER = "ExecutionContext"` (linha 1011) do conjunto
   sob teste contra o arquivo homônimo do jca — igualdade de lista ordenada, byte a byte
   por linha. Trivialmente verde no jca (semente = ela mesma, por design).
2. `tests/parity/test_gh104_specset_gates.py::test_jca_android_predicates_preserved`
   (INV-INS-128): jca_android deve carregar TODA linha-ExecutionContext do jca, mesma
   ordem, byte a byte; mais censo exato por construto (import 23, validate 27,
   setProperty 49, remove 9, accepting-state 25, comment 1 = 134 linhas) e 23 specs; mais
   ausência de predicate_removal.csv/predicate_omissions.csv.

**O que quebra na migração:** tudo acima, em todos os 23 arquivos — o import muda, cada
chamada muda de classe/assinatura. G-PRED reportaria 23 divergências e o pytest falharia
em todas as asserções. E há dano colateral FORA do G-PRED, no mesmo script:

- `accept_requires` (gh104_gates.py:1189-1191): decide se REQUIRES "limpa" no split de
  órfãos do G-2 procurando a substring `"ExecutionContext"` nas specs. Se a classe nova
  não contiver essa substring no nome, o jca_android passa a ser lido como "sem
  predicados" → REQUIRES deixa de limpar → falsos vermelhos no G-2.
- `PREDICATE_CALL` (gh104_gates.py:514-517): regex
  `ExecutionContext.instance().validate(Property.X, obj)` usada pelo G-2 para mapear
  condition() → cláusula CrySL. Fica cega para a classe nova (e para aridade N).

**Dimensionamento da reformulação** (não implementado, como pedido):

- Para o **jca**: G-PRED continua fazendo sentido como auto-verificação do congelamento
  (trivialmente verde). Manter.
- Para o **jca_android**: a premissa "sucessor preserva a semente byte a byte" é
  invalidada POR DESIGN (F1-F4 reescrevem sítios de propósito). Não é trocar referência
  nem redefinir baseline textual simples: o gate certo vira o par G-PRED2 +
  `predicate_graph.csv` da F5 (fechamento semântico: todo acusador da semente tem
  sucessor, todo predicado lido tem produtor), possivelmente com um baseline snapshot
  próprio do jca_android pós-migração se quiser manter detecção de deriva textual.
  Ou seja: **aposentar G-PRED para jca_android e criar gate novo**, mantendo G-PRED
  ativo só como cadeado do jca.
- Custo adicional: atualizar PREDICATE_MARKER/PREDICATE_CALL/accept_requires para
  reconhecer a classe nova (3 pontos no script), reescrever/aposentar
  `test_jca_android_predicates_preserved`, e decidir a política do INV-INS-118
  (`test_jca_android_hunks_all_recorded` + gh104_divergence_record.py): cada linha
  reescrita vira hunk contra a semente — são ~134 linhas × 23 arquivos que precisarão de
  linhas no divergence_record.csv OU de uma reformulação desse gate também. Este último
  ponto não está orçado no handoff e é o maior custo operacional.
- Tamanho: médio (meio-dia a um dia de trabalho de gates + decisão de política do
  divergence record), não uma linha.

## Tarefa 5 — Gate de disciplina de import. VEREDITO: FACTÍVEL, com um reforço recomendado

Como os imports aparecem: cada .mop do jca_android tem exatamente
`import br.unb.cic.mop.ExecutionContext;` (linha 6-9 do arquivo, conforme o header).
Não existe wildcard `import br.unb.cic.mop.*;` em nenhum conjunto (só `br.unb.cic.mop.eh.*`
e `...jca.util...`), então não há rota de escape por wildcard.

Predicado exato (uma linha, forma pytest/shell):

```bash
# forma import-only (a proposta do handoff):
grep -rl '^import br\.unb\.cic\.mop\.ExecutionContext;' \
  "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" --include='*.mop' | wc -l   # deve ser 0

# forma recomendada (mais forte — pega também uso fully-qualified sem import e comentários enganosos):
grep -rlw 'ExecutionContext' \
  "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" --include='*.mop' | wc -l   # deve ser 0
```

A forma por identificador (`-w 'ExecutionContext'`) é preferível: um .mop pode referenciar
`br.unb.cic.mop.ExecutionContext.instance()` sem linha de import, e a proposta do handoff
não pegaria. Falso positivo possível: menção em comentário (como MessageDigestSpec.mop:25
no jca) — aceitável tratar como vermelho mesmo (comentário citando a classe morta no
conjunto migrado é lixo a limpar). Encaixa no contrato de genericidade §8-bis: aplica-se
só ao diretório jca_android, zero-custo nos demais.

## Tarefa 6 — §8 / MOPSpecDefsUses. VEREDITO: alegação CONFIRMADA NA SUBSTÂNCIA, atribuição de arquivo ERRADA

A primeira auditoria não localizou porque procurou no arquivo errado. O `main()` não está
em `MOPSpecDefsUses.java` (que é só o modelo de dados, sem main) e sim em:

- **`rvsec/rvsec-mop-defsuses/src/main/java/br/unb/cic/mop/defsuses/DefsUsesGraph.java:65-66`**:

```java
public static void main(String[] args) {
    File mopDir = new File("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources");
```

Confirma tudo o que o plano alega, e mais: (1) caminho absoluto, apontando para a RAIZ de
`resources` (que só contém subdiretórios — aspect/, generic/, jca/...); (2)
`getDefsUses()` usa `mopSpecsDir.listFiles()` sem descida recursiva (DefsUsesGraph.java:23),
então encontra zero `.mop` e imprime diagrama vazio; (3) agravante não citado no plano: o
caminho usa o alias `/pedro/...`, que a JVM não resolve (memória do projeto: processos
Java precisam de `/home/pedro/...`) — `listFiles()` devolveria `null` e o main morre em
NPE engolido pelo `catch(Exception) e.printStackTrace()`; (4) o módulo está no reator
(`rvsec/pom.xml:27`). **Correção a fazer no plano: trocar "o main() de MOPSpecDefsUses"
por "o main() de DefsUsesGraph (DefsUsesGraph.java:65-66)" — a alegação NÃO deve ser
removida.** O handoff §7 (linha 415) pode fechar esse item como confirmado.

## Síntese

A decisão §3.1-bis é sólida: a superfície está completa (só falta citar `instance()`),
nenhuma spec chama nada fora dela, os números 23/23/23/0/0 batem, e nada em F0 exige
tocar a classe antiga. Os dois custos reais a orçar são (i) a reformulação do G-PRED, que
é maior do que o handoff sugere porque arrasta accept_requires/PREDICATE_CALL do G-2 e a
política do divergence record (INV-INS-118), e (ii) trivial: o gate de import, que deve
ser por identificador e não por linha de import.
