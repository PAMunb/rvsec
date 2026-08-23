# Tarefa 8.3 — o corpus C5 como comparação de oráculo

**Data**: 2026-08-23 · **Commit da árvore**: `519f2ff8`
**Corpus**: `../../ase-journal/dataset/results/errors_unit_tests.csv` (repositório irmão, leitura
apenas, gh89) — **299 linhas, 298 de dados**, colunas
`apk,rep,timeout,tool,time,spec,class,method,message,unique_msg`.

---

## 1. Por que não é um replay, e o que é em vez disso

O corpus é um agregado de **erros já reportados**, não de traces. Não há sequência de chamadas
para reexecutar: cada linha diz que uma execução do conjunto **semente** acusou uma classe num
método com uma mensagem. O bench replayável do repositório é `rvsec/rvsec-agent/src/test`, e ele
tece o **`jca` congelado** (`rvsec-agent/pom.xml:106`) — valida a semente, não o sucessor, e é
citado aqui só para dizer por que não é o instrumento.

O que dá para perguntar, e é o que esta tarefa pergunta, é uma coisa por **família de linha**:

> o conjunto corrigido ainda acusa a má utilização que esta linha registra, e parou de acusar o
> que os reparos declararam espúrio?

**O instrumento não é o harness.** A tarefa 8.4 mediu que `TraceRunner.envelope(...)` devolve um
envelope por evento acusador, escolhido varrendo o conjunto acumulado — quando um corpo de evento
levanta duas acusações, só uma aparece no relatório. Ler veredictos daí subcontaria. O instrumento
é o **código de acusação do conjunto corrigido**, interrogado diretamente: os `.mop`, o
`codes.csv` e uma sonda Java sobre o mesmo classpath que o harness usa, que faz às
`ConscryptAliasTable.matches` e `Api30CipherTransformationUtil.isValid` exatamente a pergunta que
o corpo do evento faz.

## 2. A forma do corpus

| | |
|---|---|
| linhas de dados | **298** |
| APKs distintos | 32 |
| classes distintas | 52 |
| `unique_msg` distintos | 161 |
| **`message = unknown`** | **212 (71,1 %)** |
| linhas com mensagem legível | 86 |
| famílias de mensagem | **23** (13 especificações) |

Os 71,1 % de `unknown` são o defeito que a gh104 existe para reparar, medido aqui de novo num
corpus que ela não usou: a semente escreve `@fail` sem `expecting`, e o agregado registra a
ausência como a palavra `unknown`.

## 3. Veredicto por família — as 86 linhas com mensagem

| n | spec | a linha do corpus diz | o conjunto corrigido | por quê |
|---|---|---|---|---|
| 26 | `MessageDigestSpec` | `expecting one of {SHA-256, SHA-384, SHA-512} but found SHA-1` | **não acusa mais** | a lista transcrita da api30 é `{MD5, SHA-224, SHA-256, SHA-1, SHA-512, SHA-384}`: `SHA-1` está nela |
| 9 | `MessageDigestSpec` | `… but found MD5` | **não acusa mais** | `MD5` está na mesma lista |
| 14 | `SSLContextSpec` | `expecting one of {TLSv1.2, TLSv1.3} but found TLS` | **não acusa mais** | a lista da api30 é `{Default, TLSv1.2, TLSv1.1, SSL, TLSv1, TLS, TLSv1.3}` |
| 1 | `SSLContextSpec` | `… but found SSL` | **não acusa mais** | `SSL` está na mesma lista |
| 19 | `SecretKeySpecSpec` | `Using either an invalid algorithm or keyMaterial.length is not randomized` | **acusa a metade que a regra tem** | a lista de algoritmos **foi removida** — `SecretKeySpec.cryptsl` declara `CONSTRAINTS length(keyMaterial) >= off + len` e nada sobre o algoritmo; a metade da aleatoriedade continua, e virou `SECRETKEYSPEC-NOBS-00/01` sobre `preparedKeyMaterial` |
| 5 | `CipherSpec` | `expecting one of {AES/CBC/PKCS5Padding, …} but found AES/CBC/PKCS7Padding` | **não acusa mais** | `Api30CipherTransformationUtil.isValid("AES/CBC/PKCS7Padding")` = `true`; o `CipherTransformationUtil` da semente dizia `false` |
| 5 | `PBEKeySpecSpec` | `first argument should have been randomized` | **não acusa mais** | a api30 `REQUIRES randomized[salt]` e não diz nada sobre a senha; sobre ela declara `neverTypeOf(password, java.lang.String)`, que é outra cláusula. A leitura de `randomized[password]` foi apagada |
| 5 | `PBEKeySpecSpec` | `second argument should have been randomized` | **continua acusando** | `PBEKEYSPEC-NOBS-01` (não observado) e `PBEKEYSPEC-CONSTR-02` (predicado que a regra não admite), sobre o salt |
| 1 | `PBEKeySpecSpec` | `third argument should be >= 1000` | **continua acusando, mais apertado** | `PBEKEYSPEC-CONSTR-00`, com a fronteira da api30: `>= 10000` |
| 1 | `TrustManagerFactorySpec` | `expecting one of PKIX,SunX509 but found X509` | **não acusa mais** | `alias_table.csv` tem a linha `TrustManagerFactory,X509,PKIX,90,yes`: no Conscrypt `X509` **é** `PKIX`. A inversão vale registrar — a lista corrigida é `{PKIX}` só, então `SunX509` passa a ser acusado |

**Resumo das 86**: 56 deixam de ser acusadas, 6 continuam, 19 continuam pela metade que a regra
tem, e 1 muda de sentido. Nenhuma das 56 é perda de cobertura por acidente: cada uma tem uma
linha do `divergence_record.csv` que a declara espúria contra a regra CrySL gerada para a api30.

## 4. Veredicto para as 212 linhas `unknown`

`unknown` é a mensagem de uma acusação de **ordem** que a semente emitia sem `expecting`. Duas
perguntas, e as duas se respondem sem replay:

**Ainda se acusa?** Sim, nas treze. Todas as 13 especificações que o corpus nomeia mantêm um
código `ORDER` no `codes.csv` do conjunto corrigido:

```
CIPHER-ORDER-00 · CIPHERINPUTSTREAM-ORDER-00 · CIPHEROUTPUTSTREAM-ORDER-00
IVPARAMETERSPEC-ORDER-00 · KEYPAIR-ORDER-00 · KEYSTORE-ORDER-00 · MAC-ORDER-00
MESSAGEDIGEST-ORDER-00 · PBEKEYSPEC-ORDER-00 · SSLCONTEXT-ORDER-00
SECRETKEYSPEC-ORDER-00 · SECURERANDOM-ORDER-00 · TRUSTMANAGERFACTORY-ORDER-00
```

**Ainda se pode reportar `unknown`?** Não. Toda acusação do conjunto carrega o envelope
`v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`, e isso é portão: `G-CONF 0` e o `message-gate`
saindo 0 sobre os 24 arquivos. A palavra `unknown` deixa de ser produzível — 212 linhas do
corpus que hoje não dizem nada passariam a dizer qual regra, qual valor e o que se esperava.

Uma ressalva escrita em vez de subentendida: **a contagem de linhas `unknown` que o conjunto
corrigido produziria não é derivável deste corpus.** Onze das 24 especificações fundiram gêmeos
negados ou absorveram órfãos, o que muda quantas vezes uma execução acusa; medir isso pede
execução, e é o que o experimento conjunto da gh104 faz.

## 5. O que o conjunto corrigido acusa e o corpus não podia registrar

Três famílias novas, que nenhuma linha do C5 tem porque a semente não as acusava:

| código | o que acusa |
|---|---|
| `PBEKEYSPEC-FORB-00` / `-FORB-01` | os dois construtores que `PBEKeySpec.cryptsl` declara `FORBIDDEN` — `PBEKeySpec(char[])` e `PBEKeySpec(char[], byte[], int)`. A semente os reportava como sequência de chamadas errada, o que mandava o leitor procurar uma chamada que falta quando o achado é o próprio construtor |
| a família `NOBS` (30 dos 112 códigos) | *não observado* separado de *violado*: um predicado que o programa nunca produziu deixa de ser confundido com um que foi retirado |
| `IVCHAINJUNCTION-*` | a especificação de junção inteira, que liga as três cláusulas do `Cipher` que o `CipherSpec` não consegue ligar sozinho |

## 6. Um alargamento que vale registrar e esta change não repara

`Api30CipherTransformationUtil.isValid("AES/ECB/PKCS5Padding")` = **`true`**, enquanto o
`CipherTransformationUtil` da semente dizia `false`. O modo ECB passa a ser admitido, e a razão é
a transcrição literal da regra CrySL gerada para a api30, não uma decisão desta change. É o mesmo
tipo de achado que a `KeyPairGeneratorSpec`/EC gerou (linha `api30-omits` do
`divergence_record.csv`): **um defeito de modelagem no MetaCrySL, registrado e não reparado
aqui**, porque a regra é entrada desta change e não sua saída.

## 7. O que este dossiê não afirma

- **Não afirma taxas.** O corpus tem 298 linhas de 32 APKs sob `unit_test`; qualquer número de
  precisão ou de recobrimento sairia de uma amostra que não foi desenhada para isso.
- **Não afirma que as 56 linhas que deixam de ser acusadas eram falsas.** Afirma que a regra
  CrySL gerada para a api30 as admite, e que cada uma tem uma linha de registro que diz sob que
  regra e por quê. Se a api30 estiver errada num ponto — e a secção 6 mostra um —, o alargamento
  é da regra.
- **Não substitui o experimento conjunto.** Este é um oráculo estático sobre o que o conjunto
  *pode* acusar; quantas vezes acusa numa campanha é medição de execução.
