# Adjudicação das quatro análises externas das specs `jca_android`

**Data**: 2026-08-25
**Entrada**: `docs/analise_gh105_{gemini3,gpt5,mimo-v2-7b-free,opus5}.md`
**Objeto**: os 24 `.mop` de `rvsec/rvsec-mop/src/main/resources/jca_android/`
**Saída**: os candidatos aprovados viram tarefas do grupo 9 da gh105.

## Como cada alegação foi julgada

Nenhuma alegação entrou por concordância entre modelos. Cada uma foi confrontada
com quatro fontes, na ordem em que uma derruba a anterior:

1. o `.mop` de hoje;
2. a regra expert congelada (`RVSec-replication-package/tools/rules/`, sha256 pinado) —
   oráculo dos valores desde a D-15;
3. a regra `MetaCrySL/generated/api30/` — oráculo de ORDER, alfabeto e predicados;
4. a API real, por `javap -cp $ANDROID_HOME/platforms/android-30/android.jar`.

E, antes de qualquer coisa, os registros do próprio projeto — `conformance_record.csv`,
`divergence_record.csv`, `constraint_table.csv`, `gate_allowlist.csv`,
`predicate_graph.csv`. Essa consulta é o filtro que mais trabalhou: **a maioria dos
achados fortes das quatro análises já está registrada**, com massa de corpus medida, sob
`measured-not-repaired`, `deferred-constant` ou `behavioural`. Eles não são descobertas;
são um backlog que o projeto assumiu conscientemente e adiou. O que o pedido de hoje
muda é o momento de agendá-los.

Duas alegações convergentes entre modelos foram **refutadas** na verificação, e uma veio
de alucinação. Convergência não foi tratada como evidência.

## Achados novos — não registrados em nenhum CSV

### N1 · `SSLContext.getDefault()` é FORBIDDEN nos dois oráculos e não tem evento

Os dois oráculos declaram a cláusula (`SSLContext.crysl:10-11`,
`MetaCrySL/generated/api30/SSLContext.cryptsl`, `getDefault() => Get`).
`SSLContextSpec.mop` tem quatro eventos — `g1`, `g2`, `init`, `engine` — e nenhum a cobre.
`SSLContext.getDefault().createSSLEngine()` produz silêncio total.

Varri as 33 regras api30 e as 49 expert: o conjunto inteiro tem exatamente **duas** regras
com FORBIDDEN, e elas concordam entre os oráculos — `PBEKeySpec` (dois construtores) e
`SSLContext.getDefault()`. A primeira **é** implementada, com dois sítios
`ErrorType.ForbiddenMethod` e códigos `PBEKEYSPEC-FORB-00/01` próprios. A segunda não é, e
a omissão não aparece em `divergence_record.csv`, `conformance_record.csv`,
`constraint_table.csv`, `gate_allowlist.csv` nem nos artefatos da gh105. O conjunto é
internamente inconsistente nesse ponto, e nenhum portão cobre "FORBIDDEN → evento", que é
por que passou.

Cuidado que o reparo exige: o evento novo precisa entrar na `fsm` com auto-laços. Um
evento fora do autômato recebe do gerador uma linha que leva todo estado a `fail`, e o
reparo trocaria um falso negativo por um falso positivo de ordem.

Origem: encontrado independentemente por mim e pela análise opus5 (O-10).

### N2 · `CipherSpec` e `IvChainJunction` não normalizam grafia nem alias

Das 24 specs, 11 comparam valores através de `ConscryptAliasTable.matches`, que dobra
caixa e resolve alias. `CipherSpec` e `IvChainJunction` são as duas únicas com allow-list
de valor que **não** o fazem: usam `isValid(...)` de `CipherTransformationUtil`, importado
estaticamente. Lendo a classe:

- `alg(transformation).equals("AES")` — sensível a caixa;
- `modes.contains(mode(transformation))` — sensível a caixa;
- só o *padding* faz `toUpperCase()`;
- a lista de padding do CBC é `[PKCS5PADDING, ISO10126PADDING, PKCS5PADDING]` — sem
  `PKCS7Padding`, que o Conscrypt registra como alias de `PKCS5Padding` para AES;
- no ramo RSA só `mode == ""` e `mode == "ECB"` passam, então a grafia `RSA/None/...`
  cai fora.

Falsos positivos diretamente deriváveis: `AES/CBC/PKCS7Padding`, `aes/cbc/pkcs5padding`,
`AES/cbc/PKCS5Padding`, `RSA/None/PKCS1Padding`. As linhas de serviço `Cipher` da
`alias_table.csv` não têm leitor.

**Isto não conflita com a D-15.** Normalizar a grafia não altera o conjunto de valores que
o oráculo expert admite; é exatamente o que as outras 11 specs já fazem. O que muda é o
mapeamento de uma grafia da plataforma para o valor já admitido.

Origem: análise opus5 (O-2), verificada por leitura da classe.

### N3 · Duas guardas de gêmeo negativo leem o campo do monitor, não o argumento

O conjunto tem oito `condition(!...)`. Seis leem o argumento do evento
(`KeyStoreSpec:63`, `MacSpec:81`, `KeyManagerFactorySpec:64`, `KeyPairGeneratorSpec:77`,
`SecureRandomSpec:135`, e `CipherSpec:100` sobre `transformation`). **Duas leem o campo do
monitor**: `KeyGeneratorSpec:76` e `MessageDigestSpec:73` testam
`currentAlgorithmInstance`, enquanto a mensagem que emitem reporta `alg`.

O campo nasce `""` e o gêmeo positivo `g1` tem guarda positiva, então só escreve o campo
quando o algoritmo é aceito. Como o monitor é por objeto e cada `getInstance` devolve um
objeto novo, a guarda acerta **apenas porque** o gerador emite `g1Event` antes de
`g4Event`/`g3Event` no mesmo pointcut. Se a ordem invertesse, todo `getInstance` seguro
passaria a acusar com o envelope autocontraditório `expecting one of SHA-256,… but found
SHA-256` — que é a assinatura `but found .` que a task 8.16 reparou nos `if` de corpo e
não alcançou nestes dois `condition()`.

Nada no repositório assere essa ordem de emissão. Hoje o efeito é nulo; o risco é latente
e de massa.

Origem: análise opus5 (O-27), verificada nos oito sítios.

### N4 · `proposal.md` e `design.md` discordam sobre quantas cláusulas foram fiadas

`proposal.md:17` diz "24 of those are wired"; `design.md:490` diz "Of the 25 wireable,
**21 are wired**". É contradição entre dois artefatos da mesma change, e a errada é a que
um leitor externo cita.

Origem: análise opus5 (O-12).

### N5 · Quatro constantes de `Property` sem sítio, uma delas com javadoc que descreve o que não existe

`GENERATED_CIPHER`, `GENERATED_MAC`, `GENERATED_TRUST_MANAGERS` e `WRAPPED_KEY` têm zero
ocorrências nos 24 `.mop`. O javadoc de `GENERATED_CIPHER` afirma que a marca é escrita
nos eventos de `init` — descrição de um programa que não existe, o inverso do P4.

Origem: análise opus5 (O-14), verificada por contagem.

### N6 · `PBEKeySpecSpec.f1`/`f2` não ligam objeto e difundem a acusação

`f1` e `f2` são `after(char[] password)` e `after(char[], byte[], int)`, sem `returning`
e sem `target`: ligam o `char[]`, nunca o `PBEKeySpec`. O gerador despacha para o conjunto
inteiro de monitores, e uma construção proibida emite `PBEKEYSPEC-FORB-00` uma vez por
monitor vivo mais a raiz.

O comentário do próprio arquivo descreve o problema no passado — mas o que foi aplicado
foi a absorção em Kleene, que tirou o `fail`; a difusão da acusação continua. O reparo tem
precedente exato no conjunto: `MacSpec.f2`, task 5.3. O autômato não muda, porque
`(f1|f2)*` já é laço benigno.

Origem: análise opus5 (O-6); registrado como item (c) do `conformance_record.csv` apenas
quanto ao broadcast, não quanto à cardinalidade da acusação.

## Confirmados, porém já registrados como adiados

Estes são reais e verificados, e a decisão de adiá-los está escrita. Entram como tarefas
porque o pedido de hoje é reparar as specs, não porque sejam novidade.

| # | Defeito | Registro | Massa medida |
|---|---|---|---|
| R1 | `createSSLEngine` com retorno `void` onde a API devolve `SSLEngine` — advice gerado que nunca dispara | `conformance_record.csv`, `measured-not-repaired` | não dimensionável |
| R2 | `@fail` do `KeyPairGeneratorSpec` sem `__RESET` — único do conjunto (20 de 21 resetam) | gh105 task 8.7, decisão 7, `behavioural` | inflação linear por ligação |
| R3 | `ere` do `KeyPairSpec` exige o construtor `c1`, que `generateKeyPair()` nunca dispara | `measured-not-repaired` (f) | 668 eventos / 8 apps — 100 % da spec |
| R4 | `getInstance(String, Provider)` sem pointcut em 5 specs | `measured-not-repaired` (g) | monitor no estado 0, toda linha é fail |
| R5 | `SecureRandomSpec`: `end` omite `next2` | `measured-not-repaired` (d) | 12.400 linhas / 43 apps |
| R6 | `CipherSpec`: `s3` sem laço de `update`, `s2`/`end` sem re-`init` | `measured-not-repaired` (e) | 10.814 linhas / 21 apps |
| R7 | `KeyStoreSpec` não-paramétrica (declara `ks`, todo evento liga `k`) | `measured-not-repaired` (a) | 8.655 + 2.005 linhas / 22 apps |
| R8 | guarda do `g2` do `SSLContextSpec` suprime o evento para protocolo rejeitado | `divergence_record.csv`, `behavioural` | herdada da task 3.6 |
| R9 | `Cipher*Stream` não-paramétricas | `measured-not-repaired` (b) | 0 de 97.018 |

Sobre R4, uma correção à minha própria varredura: cheguei a concluir que a lacuna era
maior que o registro dizia, incluindo `KeyManagerFactory`, `TrustManagerFactory` e
`SecureRandom`. Estava errado — essas três já usam `getInstance(String, ..)`. O registro
estava certo e a lacuna é exatamente nas cinco specs que ele nomeia. Em quatro delas
(`KeyPairGenerator`, `Mac`, `Signature`, `SSLContext`) o reparo é trocar `String` por `..`
na segunda posição, a custo zero de evento; só `KeyStore` precisa de evento novo, e tem
7 de 17.

## Refutados

| Alegação | Origem | Por quê |
|---|---|---|
| `KeyGenerator`: `alg in {AES} => keysize in {128,192,256}` não implementada, `init(64)` passaria em silêncio | gemini3, gpt5 | O fato é verdadeiro e está registrado três vezes como `deferred-constant` (promoção é a task 2.14, depende da harness 6.9). O exemplo não executa: `init(64)` lança `InvalidParameterException` na própria JCA, e `generateKey()` nunca é alcançado. A correção como escrita também não funciona — não existe evento que ligue o `int`. |
| `SecretKey.destroy()` sem evento e sem o `NEGATES` | gpt5, mimo | Registrado em quatro lugares sob INV-INS-137. `destroy()` não é declarado em `SecretKeySpec` (herda o default de `Destroyable`), e o default sempre lança `DestroyFailedException`: um `after returning` seria código morto. A variante que dispararia (`after throwing`) está semanticamente invertida — `destroy()` que lança significa que a chave **não** foi revogada. |
| `PBEKeySpecSpec.mop:85` usaria `ErrorType.UnsafeAlgorithm` para a guarda de `iterationCount` | mimo | Alucinação. O arquivo usa `UnsatisfiedConstraint` em `:104,130,135` e `ForbiddenMethod` em `:36,43`; não há `UnsafeAlgorithm` nem `reportError`. Esse rótulo exato já foi corrigido nas tasks 7.3/7.5, e o modelo reproduziu um defeito reparado. |

## Fora de escopo deste reparo

- **Artigo `ase-journal`** — decisão permanente do pesquisador; os números novos servem às
  próximas campanhas. Todas as alegações que pedem revisão de texto publicado ficam de fora.
- **Família `NOBS` e desenho de três braços** — é protocolo de experimento e método de
  contagem, não conteúdo de spec. Merece decisão antes da campanha, em outro lugar.
- **As 27 regras expert sem `.mop`** (`SecretKeyFactory`, `KeyFactory`,
  `AlgorithmParameters`, superfície TLS de execução) — é change nova, não reparo da gh105.
- **`KeyGenParameterSpec`, `setEnabledProtocols`, Network Security Config** — não há regra
  CrySL correspondente; escrever spec sem oráculo é o que esta pesquisa evita.

## Leitura das quatro análises

- **opus5** é a mais forte com folga: leu o monitor gerado como terceiro oráculo, executou
  os portões, mediu contra `errors.csv`, e é a fonte de cinco dos seis achados novos. Também
  é a única que declara quando não mediu.
- **gpt5** acerta nos dois silêncios do `SSLContext` e na leitura de que os portões não
  conferem assinatura contra o `android.jar` — o que é auto-referente e correto, já que foi
  por aí que o `createSSLEngine` passou.
- **gemini3** é sólida no catálogo e converge nos itens de autômato, mas seu veredito de que
  "não há nenhum `DEFEITO-PERMISSIVO` ativo" contradiz cinco de seus próprios achados.
- **mimo-v2-7b** tem a forma de uma auditoria e substância desigual: contradições internas
  reincidentes, números de precisão fabricada e um achado proposto e refutado no mesmo
  bloco. Uma alegação verificável era alucinação. Serve como lista de pistas, não como
  evidência.
