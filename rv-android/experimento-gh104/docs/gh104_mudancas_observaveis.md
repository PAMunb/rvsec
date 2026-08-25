# gh104 — o que muda de forma observável na saída de um experimento

Levantamento feito em 2026-08-18 sobre `openspec/changes/gh104-legible-violation-reports/`
(`proposal.md`, `design.md`, `tasks.md`, os 10 `tasks/*.md` e os 6 `specs/*/spec.md`),
**reconciliado em 2026-08-24** contra o HEAD `6192b57a`. Abaixo, `$C` = esse diretório.

> **A change está implementada, menos três tarefas.** 106 de 109 marcadas em 24/08; abertas: 10.4 e
> 10.5 (o piloto de dispositivo, que é o P6 desta campanha) e 10.8 (o sync de invariantes, que roda
> no arquivamento). Em `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/` existem `jca/` (23 `.mop`,
> congelado), `jca_android/` (**24** `.mop` + `codes.csv`) e `jca_android_bug_predicate/` (23, o
> derivado da gh101 reprovado, renomeado e não selecionável). `data/gh104/` e `data/jca_android/`
> existem e estão povoados.
>
> **Duas coisas mudaram o conteúdo deste arquivo depois de 18/08, e não só os números:**
> 1. a **D-15** (24/08) re-ancorou o oráculo das listas de **valor** às 49 regras validadas por
>    especialistas, retirando a âncora api30 — que continua valendo para `ORDER`, alfabetos de
>    evento e predicados. Isso inverte parte da §5;
> 2. a **gh105** ligou os predicados, acrescentou `IvChainJunction.mop` e introduziu a família de
>    códigos `NOBS`, que não existia em nenhum conjunto anterior.
>
> Cada número abaixo carrega a data em que foi medido. Sem data e sem commit, um escalar não é
> checável.

---

## 1. A mensagem

### Antes

`ErrorDescription` de 3 argumentos delega com o literal `"unknown"`
(`$C/design.md:19`, citando `ErrorDescription.java:34-36`); `toString()` renderiza
`[%s] %s at %s expecting %s`. No `jca` congelado há **51** sítios `new ErrorDescription(`:
**25 de 3 args** (21 `@fail` + `IvParameterSpec:48,55` + `PBEKeySpecSpec:24,30`) e 26 de 4 args.

16 sítios de `but found` interpolam um **campo do monitor** (`currentAlgorithmInstance`,
`currentTransformation`, `currentKSType`, `currentProtocol`, `algorithm`) ainda vazio, e por isso
renderizam `but found .` (`$C/specs/instrumentation/spec.md:240`, `$C/tasks/E1-messages.md:78`).

### Depois — envelope v1

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observado>' exp='<esperado>' msg='<texto livre>'
```

Regras (`$C/design.md:146`, `$C/specs/instrumentation/spec.md:233`): sem `st=`; vírgulas
permitidas dentro de valores; `\n` e `:::` proibidos; `'` escapado como `\'`; `val` limitado a
512 caracteres pelo produtor; aspa final não fechada significa registro truncado.

`KIND ∈ {ORDER, ALG, CONSTR, KEYSIZE, KSTYPE, PROTO, FORB, NOBS}`. `REQ` foi descartado junto com
a remoção de predicados que a **D-11 depois retirou**.

> **`NOBS` é o oitavo KIND e não estava no levantamento de 18/08.** A gh105 introduziu a leitura de
> predicado três-valorada, e a **INV-INS-143** exige que o veredito `NOT_OBSERVED` chegue ao
> envelope com **família de código própria, distinta da de violação** — "so no intermediate state
> exists where the third value is computed but indistinguishable downstream". Medido no `codes.csv`
> de 24/08: **30 dos 114 códigos são `NOBS`**, em 14 especificações. O `error_type` deles é
> `UnsatisfiedConstraint`, o mesmo de códigos `CONSTR` — então **o `error_type` sozinho não
> distingue violação de não-observação**; só o `code` distingue. Qualquer leitor que agregue por
> `error_type` colapsa as duas coisas.

Exemplos literais da change:

```
v=1 code=TMF-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='init() before getInstance()'
v=1 code=TMF-ALG-01 ev=g3 obj=TrustManagerFactory val='SunX509' exp='PKIX' msg='expecting one of PKIX but found SunX509'
```

Linha de logcat completa (`$C/specs/analysis/spec.md:61`):

```
RVSEC: TrustManagerFactorySpec,okhttp3.internal.tls.X,X,get,X.java:12,UnsafeAlgorithm,v=1 code=TMF-ALG-01 ev=g3 obj=TrustManagerFactory val='X509' exp='PKIX,SunX509' msg='expecting one of PKIX,SunX509 but found X509'
```

**O que substitui `unknown`:** o quarto argumento passa a existir em todos os sítios
(INV-INS-119). Nos 21 `@fail` — a maior parte dos 25 mudos — o envelope fica
`code=<SPEC>-ORDER-00 ev=<evento> ... val='' exp='' msg='<frase>'`: `val`/`exp` continuam vazios
ali, mas **`ev=` passa a nomear o evento que levou ao `fail`**.

**O que substitui `but found .`:** o getter do **objeto-alvo** que o evento liga —
`c.getAlgorithm()`, `k.getAlgorithm()`, `k.getType()`, `m.getAlgorithm()`, `digest.getAlgorithm()`,
`s.getAlgorithm()`, `ctx.getProtocol()`, `mf.getAlgorithm()` — nunca o campo do monitor. Nenhum
dos 16 eventos liga o argumento algoritmo/tipo/protocolo; todos ligam o alvo.

### Correções de texto que também mudam a saída literal

`$C/tasks/E1-messages.md:59-74`:

- `PBEKeySpecSpec:50` e `PBEParameterSpecSpec:50`: `1000` → `10000`.
- `MessageDigestSpec:70,92`: lista de 3 → lista transcrita de 6 (com MD5 e SHA-1).
- `CipherSpec:61,76`: some o literal `...`.
- **`SecureRandomSpec:82`: junta a lista com `","` em vez de `" or "`** — separador único no
  conjunto; quebra qualquer consumidor que fatie por `" or "`.
- espaços faltantes/sobrando em `KeyGeneratorSpec:64`, `KeyStoreSpec:68`, `MacSpec:50,62`,
  `KeyManagerFactorySpec:55`, `KeyPairGeneratorSpec:72`, `SecretKeySpecSpec:49,56`.
- `msg` não pode começar com `expecting` (o `toString` já prefixa).

### `ErrorType`

Ganha **`ForbiddenMethod`**, e só isso; `RequiredPredicate` **não** entra (D-13). Correções:
`PBEKeySpecSpec:24,30` `InvalidSequenceOfMethodCalls` → `ForbiddenMethod`;
`PBEParameterSpecSpec:49` `UnsafeAlgorithm` → `UnsatisfiedConstraint`.
**Isso muda a distribuição da coluna `error_type`.**

---

## 2. Esquema de saída

### `errors.csv`: 11 → 13 colunas

```
apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg
```

`code` e `event` entram **depois de `source`** (`$C/specs/platform/spec.md:19,32,72`). Nenhuma
coluna é renomeada ou removida — mas leitores posicionais quebram. Valem o sentinela
`UNSPECIFIED` (nunca string vazia) quando o registro não traz envelope.

### `unique_msg`: 5 → 7 partes

```
class:::method:::spec:::error_type:::code:::event:::message
```

(INV-CORE-25). Contagem ≠ 7 deve contar como *unparsed*, não ser reinterpretada. Os **4
construtores duplicados são deletados** (`result_processor.py:631,:999,:1038`,
`regenerate_container.py:244`); passa a existir um só.

### Campos fabricados → sentinelas explícitos

| hoje fabrica | passa a ser | contador |
|---|---|---|
| `Unknown Source:1` (Format 3) | `source=UNSPECIFIED:0` | `sentinel_source` |
| `No additional message` | `message=""` | — |
| `error_type` vazio | `UNSPECIFIED` | `sentinel_error_type` |
| sem envelope | `code`/`event` = `UNSPECIFIED` | `sentinel_code`, `sentinel_event` |

### Transporte `ErrorCollector` → csv (grupo E3)

- **logcat** (`ErrorCollector.java:36-40`): escaping ligado (`\n` → `\\n`, vírgulas mantidas);
  `expecting == null` → envelope-sentinela. Hoje o método de escape existe mas **a chamada está
  comentada** na `:38`.
- **csv** (`ErrorCollector.escape()`): mesma regra; header inalterado.
- **`ViolationRecorder.makeRelevantList:87-105`**: frame de runtime com `fileName == null` passa a
  ser **excluído** → muda o `location` reportado, que faz parte da identidade de dedupe.
- **`logcat_parser.py`**: `ParserDiagnostics` com **13 contadores** carregado em
  `LogcatRepository.parser_diagnostics`. Format-1 com regex falhando **deixa de cair** no caminho
  de vírgulas (que fabricava registros JCA a partir de nomes de classe com 5 vírgulas).
  `parse_logcat_file` **re-levanta** exceção em vez de devolver repositório parcial.
- **`result_processor`**: falha de escrita é contada e logada como ERROR com o número de linhas
  perdidas, não engolida como WARNING (INV-PLT-30).
- **A forma da linha de logcat não muda**: continuam 7 campos separados por vírgula; só o conteúdo
  do 7º muda.

### Artefatos novos ou alterados

| artefato | onde |
|---|---|
| `instrument_results.json` ganha `advicesExcludedByArity` ao lado de `wrappersGenerated` | `$C/specs/instrumentation/spec.md:22,363` |
| `weave_counts` (Python) carrega a mesma chave | `$C/tasks.md:101` |
| `rvsec-mop/.../jca_android/codes.csv` (`spec,code,error_type,site_kind,event,file_line`) | `$C/tasks/S-seed.md:24` |
| `data/jca_android/{divergence,conformance,alias_table,gate_allowlist,predicate_removal,constraint_table}.csv` | `$C/tasks/S-seed.md:33` |
| `data/gh104/{baseline.md,baseline.json,definitions.md,consumer_matrix.md,identity_discontinuity.md}` | `$C/tasks/E0-baseline.md:12-14` |
| `results/gh104_derived_pre_generator_control/monitors/` + manifesto sha256 | `$C/tasks/G-eventname.md:62` |

### Consumidores que quebram

`$C/proposal.md:31`, `$C/tasks.md:117`: `ase-journal/.../owasp_cwe_mapping_gen.py:47-54` (regex
`but found (.*?)`, declarado *frozen*), `experimento-gov/scripts/consolidate_gov.py:26-37`,
`validator/oracles/cryptoapp-oracle.yaml` (6 substrings que dirigem `TraceComparator.java:596-598`),
`scripts/rv_oracle_common.py:73-81`, `experimento-comp162-ajc/scripts/mop_diff.py:26`,
`experimento-gov/scripts/violations_detail.py:9,22`,
`rv_android_core/domain/coverage.py:397,575,627`.

---

## 3. `__EVENTNAME`

**Camada: apenas o gerador `rv-monitor`.** Não o weaver, não o `.mop` à mão, não o `javamop`
(`$C/tasks/G-eventname.md:3,9`).

- Macro expandida em 3 sítios: `BaseMonitor.java:350-368` (corpo de evento → **literal**, ex.
  `"g3"`), `HandlerMethod.java:36-48` (corpo de handler → **lookup** na tabela),
  `RawMonitor.java:90-105` (espelho).
- **Tabela de nomes** emitida uma vez por classe de monitor em `BaseMonitor.toString():806-812`,
  iterando `this.events` em ordem de `getIdNum()`.
- No `@fail`, resolve pelo índice do último evento, ciente das duas formas de monitor:
  `this.getLastEvent()` para as 15 classes atômicas, campo `RVM_lastevent` para as 8
  não-atômicas. Índice `-1` → sentinela **`none`**.
- **Fail-closed**: se o literal `__EVENTNAME` sobreviver em qualquer Java gerado, a geração aborta
  nomeando arquivo e linha.
- **Proibido bookkeeping manual** no `.mop` (INV-INS-120); o lint falha nisso.

Onde `ev` aparece: dentro do envelope (campo 7 do logcat) → `RvErrorLog.event` → coluna `event` do
`errors.csv` + parte 6 do `unique_msg` → `ViolationEvent.event` no `aperv-tool`.

Vale para **dexlib2 e ajc** igualmente, porque está no monitor gerado.

### Efeito colateral do mesmo grupo — INV-INS-129

O gerador passa a emitir `try/finally` em volta da região travada dos 134 dispatchers
(`Advice.java:176-177` / `:254-256`). Hoje: **134 `tryLock()`, 134 `unlock()`, zero blocos
`finally`**. Como os waiters giram em `tryLock()` dentro de um laço `Thread.yield()`, qualquer
exceção dentro de um handler **retém o lock para sempre** e converte o app instrumentado num
livelock que **parece um timeout**. Observável: runs que hoje morrem por timeout silencioso
deixam de morrer.

---

## 4. Identidade / dedupe

`ErrorSummary.equals/hashCode` passa de `(spec, error, class, method, location)` para
**`(spec, error, class, method, location, code, event)`** (INV-INS-126). O texto livre da mensagem
continua fora. `ErrorSummary.toString()` **não muda** → a forma da linha de logcat não muda.

**Efeito: mais linhas.** O `ErrorCollector` deduplica sobre um `HashSet<ErrorSummary>`; identidade
mais fina = mais elementos distintos. Caso citado: `KeyManagerFactorySpec`, 296 linhas em
`TlsUtil.newKeyManager:191`, 9 sítios, duas causas candidatas hoje inseparáveis.

Âncoras: na `comp162`, **6.344 identidades de 5 campos** para 19.664 linhas (67,74 % de repetição,
máximo 49 por identidade, 0 % vindo de replicação).

**Gate:** em `comp162` a descontinuidade é **zero por construção** (corpus pré-envelope, todo
`event` = `UNSPECIFIED`) — registra-se, não se usa como critério. A recontagem num corpus **com**
`ev=` tem de ser ≠ 0; se for 0, o grupo E6 não entra e a decisão D-5 é reaberta.

**Duas eras** de todo número deduplicado (`unique_errors`, `mop_errors_unique`, coluna
`unique_msg`); INV-CORE-57 exige rotular a era em qualquer publicação.

---

## 5. Specs

### Qual conjunto

- **`jca`** (23 specs): congelado no commit `7e7acb69`, intocado — `git diff` vazio, reverificado
  em 24/08. Continua reproduzindo.
- **`jca_android_bug_predicate`** (23 specs): o derivado da gh101, reprovado 22/22 pela auditoria
  de 2026-08-08. O `git mv` foi feito; não é selecionável por nenhum valor de CLI. Medido em 24/08:
  **176** ocorrências de `ExecutionContext`.
- **`jca_android`** (**24** specs + `codes.csv`): o conjunto sucessor, semeado byte-a-byte do `jca`
  congelado. Medido em 24/08: **0** `ExecutionContext`.
- A enumeração da CLI **não cresce**: continuam `jca`, `jca_android`, `generic`, `custom`.

### Tamanho — 24, não 21

Medido em 2026-08-24 (HEAD `6192b57a`): `ls jca_android/*.mop | wc -l` → **24**.

O 21 do levantamento de 18/08 tinha duas correções pela frente, em direções opostas:

- **+2**: a deleção de `RandomStringPassword.mop` e `SecretKeySpec.mop` **foi retirada pela D-11**
  (`$C/proposal.md:58`, `$C/design.md:137`). Os dois propagadores puros ficam no conjunto. O
  `SecretKeySpec.mop` virou o produtor da cláusula #32 (`preparedKeyMaterial`) da gh105; o
  `RandomStringPassword.mop` fica sem nenhum sítio de predicado, e sem nenhum sítio de report.
- **+1**: a gh105 acrescentou **`IvChainJunction.mop`** (commit `889da829`, tarefa 5.1). Ele existe
  porque a cláusula do IV liga o terceiro argumento de `Cipher.init`, que o `CipherSpec.i2` não
  liga sob `args(mode, key, ..)` — e o `CipherSpec` está em **17 de 17 eventos**, o teto do gerador,
  com headroom **zero** (INV-INS-145). Nenhum evento novo cabe ali, então a ligação saiu para um
  arquivo de junção que **não declara `ORDER`** (`ere : use*`) e portanto nunca falha por ordem, e
  não tem `@fail`.

`23 + 1 = 24`. Normatizado em `openspec/changes/gh105-predicate-wiring/specs/instrumentation/spec.md:422`.

> **Armadilha de leitura.** A própria gh104 continua dizendo **23** em todos os seus artefatos
> (`$C/proposal.md:56,58,79`, `$C/design.md:137`, `$C/specs/instrumentation/spec.md:59,215,561`) e
> menciona `IvChainJunction` uma única vez, de passagem (`$C/tasks.md:298`). E sobrevivem nela seis
> lugares com o texto da deleção retirada — entre eles o comando literal
> `$C/tasks/S-seed.md:271` (`rm jca_android/RandomStringPassword.mop … # 21`), que contradiz o
> critério de aceitação vinte linhas abaixo, no mesmo arquivo. **Nenhum arquivo em `$C/tasks/*.md`
> foi atualizado depois de 20/08**, portanto todos são anteriores à D-15. Ao conferir contagem,
> confie no disco, não no artefato.

### Outros números do conjunto (medidos em 24/08)

- **Sítios de report: 114** (`grep -ro 'new ErrorDescription(' jca_android/ | wc -l`), contra 51 no
  `jca`. A aritmética de 18/08 apontava 45 "A RECALCULAR na execução" — mais que dobrou. A gh105
  atribui a diferença: os grupos 5 a 7 levaram 50 → 112, com `IvChainJunction` contribuindo 14,
  `SignatureSpec` 11 e `KeyGeneratorSpec` 8; os 2 restantes até 114 são
  `SECRETKEYSPEC-ALG-00/-01`, acrescentados depois pela D-15.
- **`codes.csv`: 114 códigos.** Por KIND: `CONSTR` 41 · `NOBS` 30 · `ORDER` 21 · `ALG` 17 · `FORB`
  2 · `KEYSIZE` 1 · `KSTYPE` 1 · `PROTO` 1. Por `error_type`: `UnsatisfiedConstraint` 71 ·
  `InvalidSequenceOfMethodCalls` 21 · `UnsafeAlgorithm` 17 · `ForbiddenMethod` 2 · `InvalidKeySize`
  1 · `InvalidKeyStoreType` 1 · `UnsafeProtocol` 1.
- **Predicados: 0 / 70 / 21** — zero `ExecutionContext.instance()`, 70 `PredicateStore.instance()`,
  21 arquivos com ao menos uma. Assinatura pinada em `5fbe8173` e remedida idêntica no HEAD atual.
  A regra de contagem é código, não prosa: `SubstrateTrajectory.COUNTING_RULE`. A trajetória inteira
  — `64/21/5` → `47/26/7` → `28/35/12` → `0/45/19` → `0/70/21` — é dado carimbado por commit.
  O `jca` tem **134** `ExecutionContext` nos seus 23 arquivos rastreados (o 135º está num
  `MultiSpec_1MonitorAspect.aj` gitignorado, que não é do conjunto).
- **`predicate_removal.csv` não existe.** O levantamento de 18/08 previa 30 linhas. A D-11 retirou
  a remoção de predicados e a gh105 os religou; o arquivo está em
  `backup/gh104-predicate-revert/predicate_removal.csv`. O que existe hoje em `data/jca_android/`
  é `predicate_graph.csv`, com **70** linhas de dados — uma por sítio.
- Registros vivos em `data/jca_android/` (linhas de dados, 24/08): `alias_table.csv` 169 ·
  `constraint_table.csv` 80 · `conformance_record.csv` 116 · `divergence_record.csv` 316 ·
  `gate_allowlist.csv` 23 · `order_alphabet_map.csv` 206 · `predicate_graph.csv` 70.

### D-15 — o oráculo de valor mudou, e metade desta seção mudou com ele

**Decisão do pesquisador em 2026-08-24**, `$C/design.md:346`, sobre a auditoria registrada em
`docs/20260824_auditoria_specs_jca_android.md` (commit `5fbe8173`). O que ela decidiu:

- **Valores** (allow-lists, testes de valor, e as tabelas de transformação do Cipher em Java):
  transcrição literal dos `CONSTRAINTS` das **49 regras validadas por especialistas** de
  `RVSec-replication-package/tools/rules/*.crysl`, **pinadas por sha256** como freeze item.
- **`ORDER`, alfabetos de evento e a fiação de predicados da gh105**: continuam ancorados em
  `MetaCrySL/generated/api30/`. Re-ancorar isso reabriria as nove divergências registradas do
  G-ORDER e o ledger de 36 cláusulas, sem ganho de detecção.
- **Todo veredito passa a dizer de qual oráculo veio.**

Por quê, em uma frase que vale registrar: os `.ref` do tier Android foram derivados de *registries
de provider*, então toda lista "refinada para api30" é um **catálogo de disponibilidade**, não um
juízo de segurança. É por isso que a api30 admitia `MD5`, `SHA-1`, `SSL`, `TLSv1`, `HmacMD5`,
`ARC4` — e `AES/ECB`. Além disso, a transcrição manual MetaCrySL perdeu 16 das 49 regras e
danificou 19 das 33 sobreviventes (comparadores invertidos, cláusulas fabricadas, um `FORBIDDEN`
em método inexistente, `notHardCoded[password]` apagado das três regras que o tinham).

A pinagem é por cópia congelada, não por branch: o `master` upstream de hoje **removeu `CBC`/`PCBC`
dos modos AES**, e re-ancorar nele acusaria `AES/CBC/PKCS5Padding`, a transformação mais comum do
corpus. A cópia do replication-package difere do upstream `6d844ab` em exatamente um valor (`CCM`
nos modos AES), registrado como linha de proveniência.

### O que passa a ser acusado — **menos**

Estas quatro linhas continuam silenciosas, e é o **critério bilateral** que a D-15 se impôs
(`$C/design.md:421-432`):

| família / valor | volume no dataset publicado | por quê, **sob a D-15** |
|---|---|---|
| `SSLContextSpec / UnsafeProtocol / TLS` | **8.648 eventos / 60 apps / 65 misuses** | entrada `platform-value` (tarefa 11.4), citando Conscrypt `android11-release` `OpenSSLProvider.java:81`: `SSLContext.TLS` liga à implementação TLSv1.2/TLSv1.3, então quem pede `TLS` na api30 comprovadamente obtém um protocolo que a regra expert admite |
| `KeyStoreSpec / InvalidKeyStoreType / AndroidKeyStore` | **2.005 / 11 / 12** | entrada `platform-value` — a lista expert é JSE-only (`{JCEKS, JKS, DKS, PKCS11, PKCS12}`) e não nomeia tipo Android nenhum |
| `TrustManagerFactorySpec / UnsafeAlgorithm / X509` | **643 / 3 / 5** | alias Conscrypt `X509 → PKIX` (regra de normalização da tarefa 2.5); `PKIX` está na lista expert. **Não** precisou de entrada `platform-value` |
| `SignatureSpec / UnsafeAlgorithm / SHA256WITHRSA` | **4 / 1 / 1** | comparação case-insensitive |
| `MessageDigestSpec.reset` removido | ≥ 100 linhas / 7 sítios (piso) | evento sem `condition()`, linha `{4,4,4,4,4}` — acusava **todo** `reset()` |
| **17 acusadores órfãos** em 9 specs (gh105) | — | o `InvalidSequenceOfMethodCalls` espúrio que o gerador dá a todo evento fora do autômato some. Num caso medido (`TrustManagerFactorySpec-sunx509`) o órfão estava **suprimindo** o achado real: saíam dois `TRUSTMANAGERFACTORY-ORDER-00` e nenhuma acusação de algoritmo; agora sai um `TRUSTMANAGERFACTORY-ALG-00 val='SunX509' exp='PKIX'` |

**As cinco entradas `platform-value` são fechadas e citadas, e não há sexta**: `SSLContextSpec +=
TLS`, `KeyStoreSpec += {AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}`. Só `AndroidKeyStore`
tem evidência de corpus; os outros três entram pela citação. Um candidato sem citação é descartado
e **continua acusado** (`$C/specs/instrumentation/spec.md:45`).

**`SSL` não ganhou linha** — decisão do pesquisador, 24/08. `OpenSSLProvider.java:80` liga
`SSLContext.SSL` à mesma implementação que `TLS`, então os **103 eventos** acusados de fato
receberam um contexto TLS em runtime; mas é um `put` e não um `Alg.Alias`, a cláusula expert nomeia
só `TLSv1.2`/`TLSv1.3`, e pedir `"SSL"` ao provider é exatamente o *misuse* de que a regra trata.
A razão está escrita na linha `behavioural` de `data/jca_android/divergence_record.csv:307`.

### O que passa a ser acusado — **mais**

Esta lista **inverteu** em relação ao levantamento de 18/08. A tabela antiga tinha MD5/SHA-1 do
lado "menos", com o rótulo "custo declarado, não regressão". A D-15 devolveu todos eles:

| volta a ser acusado | volume | por quê |
|---|---|---|
| `MessageDigestSpec` **MD5 e SHA-1** | **5.892 linhas** (3.552 `MD5`, 1.915 `SHA-1`, 424 `SHA1`, 1 `SHA`) | a api30 os admitia por disponibilidade; a regra expert lista só `{SHA-256, SHA-384, SHA-512}` + grafias |
| `SSLContextSpec` **`SSL`** | **103** | ver acima |
| `SignatureSpec` **`NONEwithRSA`** | **4** | idem, mais `MD5withRSA`, `SHA1withRSA`, `SHA1withDSA` |
| `CipherSpec` **`AES/ECB`** | não aparece no corpus publicado | **tarefa 11.3, commit `5bc5c893`**: o `CipherSpec` volta a importar a `CipherTransformationUtil` congelada. A `Api30CipherTransformationUtil` **admitia** `AES/ECB/PKCS5Padding` — `ECB` era membro da cláusula de modo AES e nenhuma cláusula de padding cobria `ECB`, então `isValid` caía no `return true`. Falso negativo que a D-10 nunca nomeou. A classe api30 **não é deletada**: fica sem chamador, como registro da âncora retirada |
| `MacSpec` `HmacMD5`/`HmacSHA1`, `KeyGeneratorSpec` `ARC4`/`DESede`/`BLOWFISH`/`ChaCha20` | — | mesma causa |

E o que é **novo**, não "de volta":

- **A família `NOBS` inteira**: 30 códigos, 14 especificações. Uma classe de relato que não existia
  em nenhum conjunto anterior. Medido pela gh105: a cláusula `preparedKeyMaterial` sozinha muda 18
  de 128 traces (15 tiram `SECRETKEYSPEC-NOBS-00`, 11 tiram `CIPHER-NOBS-00` em cascata, 4 tiram
  `IVPARAMETERSPEC-NOBS-00`); a cadeia TLS dá `NOBS` a seis traces antes silenciosas.
- **`IvChainJunctionSpec` abre balde próprio de *unique misuse*** no mesmo `(classe, método)`, por
  construção — a gh105 **exige** que esta campanha o conte como acusador próprio, nunca dobrado no
  balde do typestate (`openspec/changes/gh105-predicate-wiring/design.md:415-425`).
- **10 guardas por predicado** que silenciavam a spec voltam a rodar (`recovered check`).
- **`SignatureSpec:99,:106`**: pointcuts mortos por tipo de retorno (`byte` contra `byte[]`/`int`)
  reparados → `sign()` sem `getInstance`/`update` passa a acusar (`introduced`).
- Identidade de 7 campos (§4).

**Restaurações que a D-10 tinha estreitado e a D-15 desfez**: `SunX509` volta às duas factory
lists, RSA `3072` e `DiffieHellman` voltam ao `KeyPairGeneratorSpec`, a allow-list do
`SecretKeySpecSpec` — que a D-10 tinha **removido inteira** — é restaurada, e `NativePRNG*`,
`Windows-PRNG`, `PKCS11`, `JKS`, `JCEKS`, `DKS` ficam nas listas, inertes. Nesses valores a
acusação **diminui**, ao contrário do que dizia a nota de 18/08.

### O saldo medido, no arnês diferencial

Tarefa 11.9, sobre **159 traces** (131 herdados + 28 escritos para a D-15):
**`unchanged 119 · moved 22 · removed 12 · introduced 6`**, com cada delta atribuído nominalmente
em `data/jca_android/evidence/d15_harness_attribution.md`.

> **A primeira execução da mesma tarefa, sobre os mesmos dois snapshots, reportou `unchanged 132 ·
> moved 9`.** A diferença de treze linhas **era o instrumento, não o conjunto**. O arnês comparava
> *nomes de evento acusador*; um evento cujo corpo levanta duas acusações independentes — como
> `SignatureSpec.i1`, que emite `SIGNATURE-ALG-00` e `SIGNATURE-NOBS-00` — lia como "nada mudou".
> A tarefa 11.11 passou a comparar pares **`(evento, código)`** (commit `9cba65ee`) e a registrar
> **toda** acusação que o evento acrescenta, diffando o sink contra um snapshot tirado antes do
> advice em vez de varrer o `HashSet` acumulado (commit `21aa1b66`, lado Java).
>
> **O `msg_diff.py` desta campanha tinha o mesmo ponto cego; foi corrigido em 25/08.** Ele junta
> por sítio e compara por código: `viol[apk][sítio][code]`, com uma linha por par
> `(sítio, código)`. O código **não** entrou na chave de junção — a era antiga não tem envelope, e
> uma chave com código faria todo sítio do lado A virar `so_A` e todo sítio do lado B virar
> `so_B`, sem nenhuma linha `ambos`. Ver `../CONTEXTO.md` §7, defeito F2.

### O que **continua** sendo acusado

- `CipherSpec / UnsafeAlgorithm / RSA/ECB/OAEPWithSHA1AndMGF1Padding` (**109 eventos**): a grafia
  sem hífen em `SHA1` não é registrada por nenhum provider; fica como divergência com evidência
  comportamental.
- As 9 divergências estruturais herdadas (a)–(i) — medidas, não reparadas. Duas dominam a contagem
  de `InvalidSequenceOfMethodCalls` e **são específicas do `dexlib2`**:
  - **(i) double-fire DEX** — `getInstance(String)` dispara `g1`+`g2`(+`g3`/`g4`), então todo
    `TrustManagerFactory.getInstance("PKIX")` e `SecureRandom.getInstance("SHA1PRNG")` **seguro**
    acusa. Na `comp162`: TMF 2.855 de sequência contra 61 de `UnsafeAlgorithm`; SecureRandom 2.882
    contra 0. **Não acontece sob `ajc`** (o AspectJ exige a aridade de `args`).
  - **(h) duplo report dos 17 órfãos com cláusula** — cada disparo emite o report do corpo **e** um
    `InvalidSequenceOfMethodCalls` do `@fail`.
- `KeyPairGeneratorSpec` ganha `__RESET` no `@fail` (era o único sem) → o estado `fail` deixa de
  ser pegajoso → **menos** reports repetidos.

---

## 6. Instrumentação — o que é específico do `dexlib2`

- **O contador de aridade (grupo E2) é dexlib2-only.** "AspectJ enforces `args` arity itself, so
  the `ajc` variant needs nothing, and the counter is dexlib2-only" (`$C/design.md:177`).
- O contador **não filtra nada**: a emissão fica byte-a-byte idêntica e `wrappersGenerated` não se
  move (D-6). Se `wrappersGenerated` mudar, o filtro vazou — é o próprio teste do grupo.
- Domínio do contador: **48** dos 115 advices do descritor congelado (48 `after` não-construtor com
  `args()`; 44 sem `args()`; 9 `before` com `args()`; 14 `after`-em-construtor).
  **`advicesExcludedByArity` é fração de 48, não de 115** — ler o número sem o parágrafo D-6 leva a
  conclusão errada.
- `MessageDigestSpec.reset` é advice `before`: **não tem wrapper** no DEX, mas é tecido inline nos
  dois caminhos. A remoção afeta ambos.
- `SignatureSpec:99/:106`: o gate de tipo de retorno é exato nos dois weavers → mortos nos dois,
  revividos nos dois.
- **Em aberto:** a tarefa 2.2 deixa para a execução decidir se `MultiSpec_1MonitorAspect.aj` viaja
  com o conjunto. Para a rota `dexlib2` o artefato relevante é o **descritor `.json`**, então isso
  nos afeta pouco.

Tudo o mais da change — envelope v1, `__EVENTNAME`, as allow-lists (**expert**, sob a D-15), a
fiação de predicados da gh105, os 6 reparos E4, o `try/finally` do lock — está no `.mop`/monitor
gerado e vale igual para as duas variantes.

**Atualizações medidas em 24/08:**

- `advicesExcludedByArity` **existe** desde 2026-08-19 (commit `b43f500e`), `weaveCounts` foi de 19
  para **20** campos. O contador cobre apenas *after*-advices do caminho de wrapper: `before` e
  construtor nunca chegam ao laço de agrupamento.
- **A partição 48/44/9/14 = 115 é do descritor congelado do `jca`.** Com 24 specs e 134 eventos, o
  descritor do sucessor é outro — a fração muda de denominador, e o parágrafo D-6 continua sendo o
  que impede a leitura errada.
- **`wrappersGenerated` = 84 no `jca` já é o valor pós-`gh100`**: a fusão de wrappers levou 96 → 84
  juntando os 12 que antes eram descartados em silêncio, sem mover `wrappersSubstituted` (74 → 74).
  Nenhum contador foi renomeado; só `wrappersGenerated` mudou de semântica (um wrapper por
  *chamada*, não por *advice*).
- **Modo de falha novo, da `gh100`**: `parseCommonPointcut` levanta `UnsupportedAspectConstructError`
  em vez de devolver `null` (`DexWeaver.java:888-893`). Um `commonPointcut` malformado deixa de
  degradar em silêncio tecendo o que as exclusões existiam para excluir.

---

## 7. Critérios de verificação já definidos pela change

### Baselines congeladas (grupo E0)

| grandeza | valor |
|---|---|
| artigo: linhas / mensagens distintas / `unknown` | 97.018 / 19 / 70.760 = **72,93 %** |
| artigo: `but found .` | **8.843** = TMF 8.371 + Signature 234 + MessageDigest 156 + SSLContext 51 + Mac 31 |
| artigo: colunas | 10 (`apk,rep,timeout,tool,time,spec,class,method,message,unique_msg`) |
| `comp162`: linhas / mudas / sítios mudos | **19.664 / 15.714 (79,91 %) / 296** |
| `comp162`: muda+legível | 3.950 linhas em 101 sítios |
| `comp162`: muda+muda | 838 linhas em 12 sítios (todos `IvParameterSpecSpec`) |
| `comp162`: só-muda | 10.926 linhas em 183 sítios |
| `comp162`: mudas por spec (top 8) | SSLContext 2.916 · SecureRandom 2.882 · TMF 2.855 · MessageDigest 2.008 · Cipher 1.461 · KeyStore 1.136 · IvParameterSpec 838 · SecretKeySpec 820 |
| `comp162`: `but found .` | **98** |
| `comp162`: identidades de 5 campos | **6.344** |
| MD5/SHA-1 | 5.892 de 15.444 `UnsafeAlgorithm` = 38,15 % |
| `jca` | 23 arquivos / 21 `addError` / 0 `Log.v` / 51 `new ErrorDescription` = 25 + 26 |
| razões estruturais | artigo: SSLContext 17.510 seq contra 8.802 `UnsafeProtocol`; TMF 9.015 contra 9.014. `comp162`: TMF 2.855 contra 61; SecureRandom 2.882 contra 0 |

### O gate de dispositivo (tarefas 10.4 / 10.5) — **é o nosso**, e é o que fecha a change

Texto atual em `$C/tasks.md:258-259` (as duas continuam **abertas** em 24/08; o arquivo de grupo
`$C/tasks/E10-integration.md` é de 19/08 e **carrega a versão pré-D-15** da 10.5 — não o use como
critério).

**10.4** — um comando só:
`uv run rv-experiment run --tools monkey --specification-set jca_android --timeouts 180 --apks-dir <dir>`
com 4 APKs: `com.owncloud.android_48000100`, `eu.opencloud.android_9`,
`de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700`. Registrar em
`data/gh104/evidence/device_validation.md`:

- **`unknown` = 0** (de 79,91 % na `comp162` — reverificado por portão em 24/08).
- **`but found .` = 0** (de 98 na `comp162` — idem).
- Campos de envelope populados: `ev`, `val`, `exp`.
- `advicesExcludedByArity` **e** `wrappersGenerated` presentes no results JSON (dexlib2).
- Contadores do parser (`parser_diagnostics`) presentes.
- Também: `wrappersGenerated` e **qual diretório a análise estática usou** (exigência da 10.0).
- A plataforma gerencia o emulador. **Nenhum comando manual de emulador.**
- O ambiente precisa de `TMPDIR` fora de tmpfs: `export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR`.

**10.5** — leitura de **forma**, não de contagem (Monkey é estocástico), e a lista encolheu de
cinco linhas para **três**:

| linha | esperado | mecanismo |
|---|---|---|
| `TrustManagerFactorySpec` `X509` | não reportada | normalização da tarefa 2.5 → `PKIX`, que está na lista expert |
| `KeyStoreSpec` `AndroidKeyStore` | não reportada | entrada `platform-value` da 11.4 |
| `SSLContextSpec` `TLS` | não reportada | entrada `platform-value` da 11.4 |

Saíram: `SignatureSpec` `SHA256WITHRSA` (case-insensitive resolve) e `CipherSpec`
`RSA/ECB/OAEPWithSHA1AndMGF1Padding` — este **nunca esteve** na metade silenciosa; era erro de
contabilidade da D-10, corrigido pela tarefa 11.5. Continua acusado.

A 10.5 diz **"Runs only after Group 11"**, e o Grupo 11 fechou em 24/08. Sítio não alcançado ≠
reparo comprovado.

**Esta campanha é o experimento conjunto**: ela fecha 10.4 e 10.5 da gh104 e, pelo arquivamento que
a segue, destrava a 8.8 da gh105 — que está `[BLOCKED — external: gh104 archive]` por construção, e
não por atraso (`openspec/changes/gh105-predicate-wiring/tasks.md:3-7`).

### Portões estruturais (baseline no `jca` congelado)

| gate | `jca` esperado | `jca_android` alvo |
|---|---|---|
| G-2 (órfão sem cláusula CrySL) | 18 órfãos em 10 specs → 3 `orphan-without-clause` | **0** |
| G-2a (inércia) | 1 (`SecretKeySpec.e1`) | computado |
| G-2b′ (redundante em q0) | 8 | allowlisted com motivo |
| G-2c (estados mortos) | 1 | — |
| G-2d (sink ≠ fail) | 2 | — |
| G-6′ (métodos ≠ linhas de transição) | 1 (`GCMParameterSpecSpec`) | **0** |
| G-ERE (símbolo do `ere` sem `event`) | 1 (`GCMParameterSpecSpec:48` `c2`) | **0** |
| G-CONF (allow-list contra api30) | reproduz `constraint_table.csv` | **verde** |
| G-PRED (`ExecutionContext`) | **134** (controle negativo) | **0** — verificado em 24/08 |

> **G-PRED foi reescopado pela gh105.** Ele hoje vale como controle negativo sobre o `jca`
> congelado; sobre o sucessor a pergunta virou outra — a assinatura de substrato **`0/70/21`**
> (zero `ExecutionContext.instance()`, 70 `PredicateStore.instance()`, 21 arquivos com ao menos
> uma), pinada em `5fbe8173` e remedida idêntica no HEAD atual. O segundo G-PRED que o
> `preflight.py` desta campanha carregava — de polaridade oposta, esperando *zero predicados* no
> sucessor — **foi retirado** pela tarefa 2.7 da gh105; depois da fiação ele avisaria em toda
> corrida correta.

### Outros critérios mensuráveis

- **E2**: `wrappersGenerated` idêntico antes/depois no descritor congelado; partição
  48/44/9/14 = 115.
- **G (gerador)**: regenerar o `jca` e diferir contra o controle — únicas diferenças admissíveis
  são a tabela de nomes, a macro expandida e o framing `try/finally`; e
  `grep -c tryLock == grep -c unlock == grep -c finally` = **134/134/134**.
- **E1**: o harness pós-Grupo-2 contra E1 deve dar `unchanged` na acusação; só o envelope e o valor
  observado mudam.
- **Parser**: soma de registros + linhas contadas = linhas lidas (INV-ANA-62).
- **`errors.csv`**: header com exatamente 13 colunas; `read_errors_csv` levanta `ValueError` em 10 e
  11 colunas.
- **Registros**: `predicate_removal.csv` = 30 linhas; `alias_table.csv` = 158 linhas, 114 com
  `in_api30_allowlist=yes`.
- **Baseline**: dois runs → `baseline.json` byte-idêntico.
- **Freeze (10.1)**: `git diff 7e7acb69 -- .../jca .../CipherTransformationUtil.java` vazio;
  rename `R100` com zero hunks de conteúdo contra o SHA `pre-rename-head`; `MetaCrySL/` limpo.

---

## 8. Riscos e efeitos colaterais

1. **A comparabilidade com o dataset publicado quebra em 4 eixos simultâneos** — allow-lists,
   mensagens, autômatos e regime de predicados. A change exige que toda comparação **nomeie a qual
   deles atribui a diferença**. Não há como separar as contribuições a posteriori sem o harness.
2. **Duas eras de todo número deduplicado** (INV-CORE-57).
3. **A contagem cai muito**: 11.409 eventos / 84 misuses (18,5 % dos 454) do tier publicável deixam
   de ser reportados, por decisão; mais 5.892 linhas de `MessageDigestSpec`.
4. **E sobe em outros pontos**: identidade de 7 campos, 10 guardas recuperadas, `s1/s2` revividos.
5. **A `comp162` deixa de ser legível pelo `aperv-tool`**: `ERRORS_CSV_HEADER` vira 13 colunas e
   `read_errors_csv` levanta em 11 → é preciso um **leitor congelado de 11 colunas** (D-9).
6. **Custo de geração**: `CipherSpec` no teto de 17 eventos; geração não paralelizável; `TMPDIR`
   fora de tmpfs; `RVSEC_HOME` obrigatório.
7. **Rebuild do reator ~12 min**, e `rvsec-agent/pom.xml:94-111` **regenera o monitor do agente JSE
   a partir de `resources/jca` em todo build sem `-DskipMopAgent=true`**.
8. **Consumidores com regex no texto livre quebram** (§2).
9. ~~**Análise estática com o conjunto errado**~~ — **resolvido em 24/08** pelo commit `86a8f178`:
   `get_static_analysis_config()` passa `mop_dir=self.resolve_spec_set_dir(rvsec_root)`
   (`modules/rv-experiment/src/rv_experiment/config.py:982`), e o mapeamento conjunto→diretório
   vive num método só, consumido pela geração de monitores e pela análise estática. Isso **não**
   muda a decisão D-c desta campanha (reusar os `.apk.json`), mas muda a razão dela de "não temos
   alternativa" para "escolhemos preservar o denominador".
10. **Ruído estrutural do `dexlib2` permanece** (double-fire e duplo report dos órfãos).
11. **Monkey/APE são estocásticos** — ler forma, não contagem.

---

## 9. Em aberto na própria change — releitura de 24/08

| item de 18/08 | estado em 24/08 |
|---|---|
| Numeração `NN` de cada `code` | **fechado** — `codes.csv` existe com 114 códigos |
| Contagem final de sítios de report (45 ou 46) | **fechado, e muito acima do previsto**: **114** medidos no disco |
| Totais de `constraint_table.csv` (74 provisório; reconstrução deu 65) | **superado** — o arquivo vivo tem **80** linhas de dados e foi re-derivado pela tarefa 11.7 com a regra expert como coluna-âncora. A `gh106` mede o mesmo denominador sob a sua regra R1 e chega a **80 nas 22 regras pareadas** (119 nas 49) |
| Se `MultiSpec_1MonitorAspect.aj` viaja com o conjunto | **irrelevante para nós** — para a rota `dexlib2` o artefato é o descritor `.json`. Nota de fato: o `jca/` tem um `.aj` gitignorado, que é a 135ª ocorrência de `ExecutionContext` do diretório e **não** do conjunto |
| Quais dos 30 `deferred-constant` são transcritos ou adiados | parcialmente fechado; a key-size do AES ficou explicitamente diferida |
| Qual corpus decide a descontinuidade de identidade | fechado — `data/gh104/identity_discontinuity.{json,md}` existem, e `scripts/gh104_identity_discontinuity.py:970-975` **sai 1 quando a descontinuidade é zero no corpus decisivo**, reabrindo a D-5 |
| Qual provider aceita `RSA/ECB/OAEPWithSHA1AndMGF1Padding` | **ainda aberto** — continua registro `behavioural`, e o valor continua acusado |

### Aberto de verdade, hoje

- **As três tarefas da gh104**: 10.4, 10.5 (esta campanha, P6) e 10.8 (o sync de invariantes, que
  roda no arquivamento). O sync não começou: `openspec/specs/instrumentation/spec.md` para em
  **INV-INS-115**, e nem os 12 IDs da gh104 (118–129) nem os 19 da gh105 (130–148) estão lá.
- **`$C/tasks/*.md` não foi atualizado depois de 20/08.** Todos são anteriores à D-15, e vários
  ainda mandam ler o oráculo api30 ou usar a `Api30CipherTransformationUtil`. O `tasks.md` e o
  `design.md` são a fonte; os arquivos de grupo, não.
- **Contradições internas vivas na delta da gh104**, que valem como aviso a quem for conferir
  contagem contra o artefato: `specs/instrumentation/spec.md:38` (INV-INS-118 dizendo 21),
  `:75`, `:599` e `design.md:200` são resíduo da deleção que a D-11 retirou, e contradizem
  `:59`, `:215`, `:228` e `:561` do mesmo arquivo. Isso é matéria da change, não deste plano —
  registrado aqui só para que ninguém "corrija" o disco para casar com o artefato errado.
