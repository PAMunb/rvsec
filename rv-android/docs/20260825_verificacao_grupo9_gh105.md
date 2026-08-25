# Verificação rigorosa do grupo 9 da gh105 — 18 vereditos

**Data**: 2026-08-25 (segunda sessão do dia; contraditório da adjudicação de
`docs/20260825_adjudicacao_analises_specs_jca_android.md`)
**Objeto**: as 18 tarefas do grupo 9 de `openspec/changes/gh105-predicate-wiring/tasks.md`
**Método**: cada premissa foi refeita contra os quatro oráculos — o `.mop` de hoje, o
**monitor regenerado nesta sessão** a partir do conjunto atual
(`~/tmp-gh104/gh105-verif-g9/monitors/`, gerado porque o monitor de 24/08 precedia
13 `.mop` editados depois dele), a regra CrySL (expert congelado para valores, api30 para
ORDER/alfabeto/predicados) e a API real (android-30.jar, com presença de classe conferida
**no zip do jar**, não via `javap` — ver 9.7). Três varreduras independentes foram
reexecutadas do zero (assinaturas `call(...)`, guardas negadas, eventos sem binding), e
dois pares diferenciais rodaram no arnês (`__RESET` do 9.2; guarda-lê-argumento do 9.4).
Nenhuma citação do dossiê foi aceita sem releitura da fonte.

## Resumo

| Tarefa | Veredito | Núcleo |
|---|---|---|
| 9.1 | **CONFIRMADA COM CORREÇÃO — reclassificar para 9.B** | a premissa é verdadeira e é o único mismatch de retorno do conjunto, mas o reparo **muda o que é acusado**: `engine` é evento de criação e `start→fail` |
| 9.2 | **CONFIRMADA COM CORREÇÃO** | mecanismo real, mas o arnês devolve `unchanged` (159/159, medido) — o critério "removed, never unchanged" é insatisfazível pelo instrumento exigido |
| 9.3 | **CONFIRMADA COM CORREÇÃO** | broadcast real na emissão, invisível no registro (dedup por sítio); são de fato os dois últimos sítios |
| 9.4 | **CONFIRMADA COM CORREÇÃO** | tudo confere; "the envelope they emit" só vale para o gêmeo do MessageDigest; arnês: 159/159 `unchanged` (medido) |
| 9.5 | **CONFIRMADA COM CORREÇÃO — apagar é inviável** | os quatro estão na lista de congelamento do `test_property_append_only` e três são lidos pelo `jca` congelado; sobra só o reparo do javadoc |
| 9.6 | **REDUNDANTE** | o `proposal.md:17` já diz 21 — a correção foi aplicada na sessão anterior |
| 9.7 | **CONFIRMADA COM CORREÇÃO** | G-FORB: são **quatro** regras com FORBIDDEN por oráculo, não duas; G-SIG: `javap` vaza classes do JDK e daria verde falso |
| 9.8 | **CONFIRMADA** | 175 no `OpenSSLProvider.java` pinado, 169 na tabela, os seis exatos localizados (:195-197, :200-201, :500) |
| 9.9 | **CONFIRMADA COM CORREÇÃO** | tudo confere; falta declarar a interação com 9.1 e escopar "of the set" |
| 9.10 | **CONFIRMADA COM CORREÇÃO** | defeitos do `isValid` conferem linha a linha; `IvChainJunction` **não chama `isValid`** e já dobra caixa — sua exposição real é outra |
| 9.11 | **CONFIRMADA COM CORREÇÃO** | o ERE do rv-monitor **não tem `?`** — `c1?` não parseia; a forma é `(c1 \| epsilon)`; "100 %" não é derivável do registro |
| 9.12 | **REDUNDANTE** | já reparada pela task 4.5 (commit `a7e97294`); o fsm de hoje tem `next2 -> end` e o monitor regenerado tem `next2 = {3,1,1,3}` |
| 9.13 | **CONFIRMADA COM CORREÇÃO** | laço de `update` em s3 e `Inits+` em s2 são licenciados pelos oráculos; **re-`init` em `end` não é** — nenhum ORDER o admite |
| 9.14 | **CONFIRMADA** | não-paramétrica confirmada no arquivo e no monitor; massas conferem |
| 9.15 | **CONFIRMADA** | headers sem parâmetro; 0/97.018 confere com o registro (b) |
| 9.16 | **CONFIRMADA** | javap nas cinco classes, pointcuts atuais, linhas de estado-0 no monitor regenerado — todas as cinco conferem |
| 9.17 | **CONFIRMADA COM CORREÇÃO** | resultado certo, mecanismo errado (o monitor **existe**, em estado 0) e a citação de registro está errada (não há linha `behavioural` própria) |
| 9.18 | **CONFIRMADA COM CORREÇÃO** | "um par de arnês por tarefa" não se aplica a 9.5/9.6/9.8, e as contagens mudam com 9.6/9.12 |

Nenhuma tarefa caiu por premissa falsa; duas caem por redundância (9.6, 9.12); uma muda
de grupo (9.1 → 9.B); uma perde o ramo principal (9.5, apagar); e o critério de
aceitação de duas (9.2, e por extensão 9.18) precisa trocar de instrumento.

---

## Vereditos, tarefa a tarefa

### 9.1 — `createSSLEngine` `void` → `SSLEngine` · CONFIRMADA COM CORREÇÃO, **vai para 9.B**

**Premissa confere.** `SSLContextSpec.mop:171` declara
`call(public void SSLContext.createSSLEngine(..))`; `javap` no android-30 dá
`public final SSLEngine createSSLEngine()` / `(String, int)`. Varredura independente
desta sessão (143 sítios `call(...)` extraídos com regex tolerante a `..`/`Object+`/
quebra de linha, resolvidos contra o zip do jar): **este é o único mismatch de tipo de
retorno do conjunto** — os demais achados são as famílias já registradas (classe ausente:
`HMACParameterSpec`; membros herdados: `SecretKey.getEncoded` de `Key`,
`SecureRandom.nextInt/ints` de `Random`, conformance_record.csv:73).

**A classificação em 9.A é falsa.** O monitor regenerado decide:

- `Prop_1_transition_engine = {3, 1, 3, 3}` (mapeamento 0=start, 2=s1, 1=end, 3=fail):
  `engine` em `start` → **fail**, em `s1` → **fail**, e só em `end` é auto-laço.
- `SSLContextSpec_engineEvent` faz `FindOrCreateEntry` e **cria monitor novo em estado 0**
  quando não há um — todo evento deste gerador é evento de criação.
- Logo, com o evento vivo, `SSLContext.getDefault().createSSLEngine()` (contexto
  inicializado, sem monitor porque `getDefault` não tem evento) cria monitor em `start`,
  transiciona para `fail` e **acusa SSLCONTEXT-ORDER-00 onde hoje há silêncio**. O mesmo
  vale para um contexto do caminho `g2`-suprimido (9.17) que foi `init`-ado e depois criou
  engine (pós-`__RESET`, estado 0).
- O caminho `s1 → fail` é inalcançável na prática: `createSSLEngine()` sem `init` lança
  `IllegalStateException`, e um advice `after returning` não dispara.

O próprio registro que a tarefa manda aposentar já dizia isso:
conformance_record.csv:62 — *"Reviving it would accuse every createSSLEngine outside the
accepting state"*, e o não-reparo foi **decisão do pesquisador (2026-08-18)** exatamente
porque "reviving it only adds accusations and the published corpus cannot size that". A
sessão anterior citou a metade do registro que servia ("likely magnitude ≈ 0 no corpus")
e pôs a tarefa no grupo que dispensa decisão. Pela definição do próprio grupo — "split by
whether a task changes the set of programs the specification accuses" — magnitude não
entra; conjunto acusado, sim.

**Correções**: mover para 9.B com par de arnês e go/no-go; declarar o efeito
`getDefault().createSSLEngine()` → ORDER-00; declarar a **interação com 9.9** (abaixo);
manter a nota de que o bookkeeping `@match1` (escrita de `GENERATE_SSL_ENGINE`, sem
leitor, INV-INS-137) é o único efeito **no caminho aceito**.

### 9.2 — `__RESET` no `@fail` do `KeyPairGeneratorSpec` · CONFIRMADA COM CORREÇÃO

**Premissa confere**: `KeyPairGeneratorSpec.mop:167-171` é o único `@fail` sem `__RESET`
(20 de 21, medido bloco a bloco em divergence_record.csv:7, registro W2/decisão 7 —
a linha cita `:158`, número de linha hoje desatualizado). No monitor: `fail` é sumidouro
(toda linha de transição tem `fail→fail`), `Category_fail = (nextstate == 4)` é
reavaliada a cada evento e o despachante chama o handler sempre que ela vale — inclusive
em **despachos com `condition` falsa**, que não transicionam e não recalculam a flag
(mecânica confirmada no código gerado; é o caso do trace
`data/gh104/traces/KeyPairGeneratorSpec-sticky-fail.txt`, escrito na task 8.15).

**Duas correções substantivas:**

1. **A re-emissão em sítio igual é invisível.** `ErrorCollector.addError` deduplica por
   `(spec, código, evento, classe, método, local)` num `HashSet`
   (rvsec-logger-logcat `ErrorCollector.java:51-54`; `ErrorSummary.equals`). "Re-raises
   for every remaining event of the binding" vale na emissão, não no registro: o delta
   observável é **no máximo uma linha extra por sítio de chamada distinto**, e vem
   sobretudo dos despachos condition-false. Com `__RESET`, eventos condition-true
   posteriores **continuam** acusando (`start → fail → reset` a cada um) — o reset só
   silencia os condition-false.
2. **O arnês não prova o delta — medido nesta sessão.** Par diferencial rodado
   (A = conjunto atual, B = mutante com `__RESET`): **159/159 traces `unchanged`,
   incluindo `KeyPairGeneratorSpec-sticky-fail.txt`** — em ambos os lados uma única
   linha `gen:KEYPAIRGENERATOR-ORDER-00`. No TraceRunner todos os despachos compartilham
   o mesmo sítio sintético, então a re-emissão do lado A cai na dedup e o instrumento é
   estruturalmente cego para este defeito. O critério da tarefa — "the class is
   `removed`, never `unchanged`" — é **insatisfazível pelo instrumento que ela exige**.
   A evidência do reparo tem de ser outra: inspeção do monitor gerado B (o `reset()`
   limpa a flag) + o registro W2; ou um TraceRunner que materialize sítios distintos
   por linha de trace, que é trabalho de arnês, não desta tarefa.

O reparo continua correto e barato; o texto precisa parar de prometer uma medição que o
instrumento não entrega.

### 9.3 — `returning(PBEKeySpec s)` em `f1`/`f2` · CONFIRMADA COM CORREÇÃO

**Tudo estrutural confere.** `PBEKeySpecSpec.mop:33-45`: `f1`/`f2` sem `returning` e sem
`target`; no monitor gerado, `PBEKeySpecSpec_f1Event` despacha para
`PBEKeySpecSpec__Map`/`stateTransitionedSet` e cria o monitor-raiz — o corpo (que emite
`PBEKEYSPEC-FORB-00/01`) roda uma vez por monitor vivo mais a raiz. Varredura
independente do conjunto: **f1/f2 são os únicos dois eventos de spec paramétrica sem
binding** — MacSpec.f2 foi reparado na 5.3, `unsafe_protocol` removido na 3.6, e os
`g3`/`gtm1` do TrustManagerFactorySpec (a outra família, binding com formal errado)
foram reparados (o arquivo de hoje declara `returning(TrustManager[])` e `target(mf)`).
"Closes the last two" confere. Precedente `MacSpec.f2`/5.3 confere
(conformance_record.csv:67). O automato não muda: `(f1|f2)*` já é laço benigno
(`.mop:182`, divergence_record.csv:192).

**Correções**: (a) a multiplicidade emitida é real, mas a **dedup por sítio** (mesma dos
9.2) faz o fan-out ser invisível em `errors.csv` — o valor do reparo é semântica por
objeto, fim do broadcast e o G-BIND, não redução de linhas; o par de arnês esperado é
`unchanged`, e a tarefa deve dizê-lo. (b) O comentário do arquivo não está errado como a
tarefa diz: `:27-29` descreve o despacho ao conjunto **no presente**; o que está no
passado (`pushed`, `:31`) é só a linha all-fail que a 3.5 removeu. A reescrita do
comentário após o reparo procede, mas a acusação de "past tense" não.

### 9.4 — guardas negadas lendo o campo · CONFIRMADA COM CORREÇÃO

**Refiz o raciocínio do zero no monitor gerado, como o prompt pediu.** O conjunto tem
oito `condition(!...)` (varredura desta sessão); exatamente dois leem o campo:
`KeyGeneratorSpec.mop:76` e `MessageDigestSpec.mop:73`; os outros seis leem o argumento
(KeyStoreSpec:63, MacSpec:81, KeyManagerFactorySpec:64, KeyPairGeneratorSpec:77,
SecureRandomSpec:135, CipherSpec:100 sobre `transformation`). No aspecto gerado, o
pointcut compartilhado emite `g1Event` **antes** de `g3Event`/`g4Event`
(`MultiSpec_1MonitorAspect.aj:366-371, :524-529`), e nada na árvore assere essa ordem
(grep em scripts/ e tests/: vazio).

**A retirada da hipótese de falso negativo histórico está certa.** O monitor é por
objeto; g-eventos são de criação e ocorrem uma vez por binding; o campo nasce `""`; para
a guarda errar seria preciso um monitor com campo seguro recebendo `alg` inseguro, o que
exigiria dois `getInstance` devolvendo o mesmo objeto — impossível. Não há achado maior
escondido.

**Correções**: (a) *"the envelope they emit reports the argument `alg`"* — só vale para
`MessageDigestSpec.g4` (`:75-76`, emite `MESSAGEDIGEST-ALG-02` no corpo).
`KeyGeneratorSpec.g3` **não emite envelope** (`:77`, o corpo só rebinda o campo); sua
acusação mora a jusante, em `gk1` (`:156-160`). O contrafactual da inversão de ordem —
"todo `getInstance` seguro acusaria" — vale para o MessageDigest; para o KeyGenerator a
inversão seria silenciosa no automato. (b) A família guard-on-field tem registro (8.16;
conformance_record.csv:53-61) — mas para os **corpos**; os dois sítios `condition()` não
têm linha própria, então o "não registrado" da tarefa se sustenta, dito com esse escopo.
(c) **Par de arnês medido nesta sessão**: A = atual, B = mutante lendo `alg` nas duas
condições → **159/159 `unchanged`**, acusações idênticas evento a evento — a previsão
"unchanged by construction; the harness pair proves it" confirmou empiricamente.

### 9.5 — quatro constantes de `Property` · CONFIRMADA COM CORREÇÃO — **apagar é inviável**

**Premissa parcial confere**: `GENERATED_CIPHER`, `GENERATED_MAC`,
`GENERATED_TRUST_MANAGERS` e `WRAPPED_KEY` têm zero sítios **nos 24 `.mop` de
`jca_android`**, e o javadoc de `GENERATED_CIPHER` (`Property.java:11-22`) descreve uma
escrita nos eventos de `init` que não existe em nenhum conjunto vivo.

**O ramo "delete" não sobrevive a duas verificações que a tarefa não fez:**

1. Os quatro constam de `PROPERTY_CONSTANTS_AT_FREEZE`
   (tests/parity/test_gh101_specset_gates.py:71-97), e `test_property_append_only`
   (`:209`) falha em qualquer remoção — é a materialização da INV-INS-132
   (design.md:85,122,166). "Append-only was the rule for adding" está errado: a regra
   como escrita é "never removed, renamed or reordered", e a medição de
   `ordinal()`/`values()` licenciou insensibilidade a **ordem**, não remoção.
2. Três dos quatro são **lidos por conjuntos congelados e código Java vivo**:
   `GENERATED_MAC` por `jca/MacSpec.mop` e por
   `rvsec-crysl-mop` (`PredicateSite.java`, `PredicateIdioms.java`,
   `PredicateSubstrateTest.java`); `GENERATED_TRUST_MANAGERS` por
   `jca/TrustManagerFactorySpec.mop` e `PredicateStoreTest.java`; `WRAPPED_KEY` por
   `jca/CipherSpec.mop`. O `jca` é byte-congelado (INV-INS-109) **e é o lado A do
   arnês diferencial** — apagar as constantes quebra a compilação do monitor que o
   próprio instrumento desta change gera.

Sobra o ramo que a tarefa já oferecia como alternativa: **corrigir os quatro javadocs
para o que é verdade** (P4), dizendo de onde cada constante é lida (jca congelado /
conjunto arquivado) e que nenhum conjunto vivo a escreve.

### 9.6 — contradição proposal × design · REDUNDANTE

`proposal.md:17` hoje diz *"Of the 35 connectable REQUIRES clauses, 25 have both ends
monitored in the set; **21 of those are wired**"*, com a derivação das quatro cláusulas
de fora (#30/#23 `vacuous`, #21/#17 `unreachable-composition`) — idêntico a
`design.md:490+`. A correção que a tarefa descreve **já foi aplicada pela sessão
anterior** (o próprio handoff a lista como artefato 3). A tarefa descreve o estado
pré-correção como se fosse atual. Reescrever como registro do que foi feito (a mudança
está na working tree, não commitada) ou marcar concluída.

### 9.7 — G-SIG, G-FORB, G-BIND · CONFIRMADA COM CORREÇÃO

- **G-FORB — a contagem da premissa é falsa.** Varredura desta sessão nos dois oráculos:
  **quatro** regras com FORBIDDEN em cada um, não duas — além de `PBEKeySpec` (dois
  construtores) e `SSLContext` (`getDefault()`), **`DigestInputStream`** e
  **`DigestOutputStream`** carregam `FORBIDDEN on(boolean)` (expert) /
  `on(boolean)`/`on(java.lang.String)` (api30). Nenhuma das duas tem `.mop` no conjunto
  (estão entre as 27 regras sem spec, fora de escopo) — então o gate **como escrito**
  ("every FORBIDDEN clause of both oracles has an accusing event in the set") nasce
  vermelho por regra que o escopo exclui. Correção: escopar a regras com `.mop` no
  conjunto (e registrar as demais como skip declarado). Com esse escopo, a aritmética
  da tarefa volta a valer: dois FORBIDDEN no conjunto, um implementado, um não. O mesmo
  erro de contagem está no dossiê (N1: "o conjunto inteiro tem exatamente duas regras
  com FORBIDDEN").
- **G-SIG — o instrumento proposto dá verde falso.** Demonstrado nesta sessão: `javap`
  resolve `javax.xml.crypto.dsig.spec.HMACParameterSpec` **do módulo do próprio JDK**
  mesmo com `-cp` apontando só para o android.jar, e `--system none`/`-bootclasspath`
  não impedem (JDK 25). O android-30.jar tem **zero** entradas sob `javax/xml/crypto`
  (verificado no zip). Um G-SIG ingênuo declararia presente a única classe que o
  registro sabe ausente. Correção de desenho: presença de classe conferida por entrada
  no zip do jar; `javap` só depois, e com resolução de membros herdados
  (`SecretKey.getEncoded` vem de `Key`; `SecureRandom.nextInt`/`ints` de `Random` —
  família registrada em conformance_record.csv:73) e de classes internas
  (`KeyStore$ProtectionParameter`).
- **G-BIND — confirma.** Varredura própria: exatamente os dois sítios de 9.3, nenhum
  outro. Decidível e barato como dito.

A disciplina red-path (mutar, rodar, reverter) confere com o padrão do grupo 8.

### 9.8 — seis linhas ausentes da `ConscryptAliasTable` · CONFIRMADA

Verificado contra a fonte pinada `backup/gh104-analise/OpenSSLProvider.java` (607
linhas, mantida local conforme data/jca_android/README.md:131-132): **175** registros
`Alg.Alias` no arquivo; **169** linhas na tabela (`alias_table.csv`, 169 dados; javadoc
da classe diz 169). Os seis ausentes, com linha da fonte: `KeyFactory`
`1.2.840.113549.1.1.1→RSA` (:195), `1.2.840.113549.1.1.7→RSA` (:196),
`2.5.8.1.1→RSA` (:197), `1.2.840.10045.2.1→EC` (:200), `1.3.133.16.840.63.0.2→EC`
(:201); `CertificateFactory` `X.509→X509` (:500). A alegação de completude está em
`ConscryptAliasTable.java` (§ "kept in the table so that the extraction stays
complete"). Nenhum `.mop` chama `matches` com esses serviços → sem efeito de veredito.
Correção menor de texto: nomear também `alias_table.csv` entre os artefatos a atualizar
(o `ConscryptAliasTableTest` assere igualdade linha a linha entre classe e CSV, então os
dois mudam juntos).

### 9.9 — `getDefault()` FORBIDDEN sem evento · CONFIRMADA COM CORREÇÃO

Confirmado nos dois oráculos (expert `SSLContext.crysl:10-11` — `getDefault() => Get`;
api30 `SSLContext.cryptsl` — `getDefault() => Gets`), na API
(`public static SSLContext getDefault()`, javap) e no conjunto (4 eventos, nenhum o
cobre). **Ausência nos cinco CSVs verificada por grep**: `getdefault` não aparece em
nenhum arquivo de `data/jca_android/` — só no próprio texto do grupo 9. O contraste com
`PBEKeySpec` (FORB-00/01 implementados, `.mop:36,43`) confere. A advertência dos
auto-laços é validada pela mecânica geral (linha all-fail para evento fora do automato —
conformance_record.csv:72 documenta a família) e pelo histórico 3.2/3.6
(divergence_record.csv:211,213; o comentário de `SSLContextSpec.mop:58-86`).
`SSLContextSpec` tem 4 de 17 eventos ✓.

**Correções**: (a) escopar a frase "the only other FORBIDDEN clause of the set" — vale
para regras **com `.mop` no conjunto**; no oráculo inteiro são quatro (ver 9.7).
(b) **Declarar a interação com 9.1**: com ambos os reparos, `getDefault()` cria monitor
via o novo evento (auto-laço em `start`), e o `createSSLEngine()` seguinte dispara
`engine` em `start` → `fail` → exatamente o falso positivo de ordem que a tarefa promete
evitar. As duas tarefas precisam decidir juntas a linha de `engine` (ou do estado do
novo evento) para o contexto-getDefault — ou registrar o residuo deliberadamente.

### 9.10 — normalização do Cipher · CONFIRMADA COM CORREÇÃO

**Os defeitos do `isValid` conferem linha a linha**
(`CipherTransformationUtil.java`): `alg(t).equals("AES")` sensível a caixa (:44),
`modes.contains(mode(t))` sensível a caixa (:45,:33), só o padding faz `toUpperCase()`
(:46), lista CBC `[PKCS5PADDING, ISO10126PADDING, PKCS5PADDING]` — duplicata e sem
PKCS7 (:35), ramo RSA só `""`/`"ECB"` (:64-65).

**"Não reabre a D-15" se sustenta, com o argumento certo.** O expert
(`Cipher.crysl:113`) **não** lista `PKCS7Padding`; o que licencia o mapeamento é o
mecanismo que a D-15 já abençoou para as outras 11 specs — resolução de alias por
registro pinado do provider —, e as duas linhas existem na tabela auditável:
`alias_table.csv` `Cipher,AES/CBC/PKCS7Padding,AES/CBC/PKCS5Padding,380` e
`Cipher,RSA/None/PKCS1Padding,RSA/ECB/PKCS1Padding,334` (hoje sem leitor, como a tarefa
diz). Dobrar caixa é grafia pura (o JCA resolve case-insensitive). O normalizador
resolve o alias **e então** compara com o valor que o expert admite — mesma classe da
entrada `TLS` do SSLContextSpec, já ratificada.

**`Api30CipherTransformationUtil` lida por inteiro, como o prompt pediu: a sessão
anterior acertou, por razão mais forte do que deu.** A classe transcreve o **catálogo
api30** (`ALGORITHMS` com ARC4, BLOWFISH, DESede, ChaCha20; `AES_MODES` com **ECB**) —
dar-lhe um chamador reabriria a D-15 de fato (admitiria `AES/ECB/PKCS5Padding` etc.,
que a própria doc da classe lista como o delta medido) — e a doc encerra: *"It is not
to be given a caller again."* (:75).

**Correções**: (a) **`IvChainJunction` não chama `isValid`** — chama só o parser
`mode()` (`:136`) e **já dobra caixa** nos dois testes de modo
(`.trim().toUpperCase(Locale.ROOT)`, `:139,:173`). A exposição real dele é outra e está
fora do texto da tarefa: extrai `mode()` da transformação **não resolvida**, então um
alias PBE (`PBEWithHmacSHA1AndAES_128` → canônico `AES_128/CBC/PKCS5PADDING`,
alias_table:394-398) tem `mode()==""` e **fura a cláusula de IV/GCM silenciosamente** —
o normalizador deve resolver o alias antes de extrair o modo, e aí sim os dois arquivos
o consomem. (b) "migrate the six call sites" — são **5** sítios `isValid` no CipherSpec
(:85,:92,:100,:108,:181) mais o `mode()` do IvChainJunction; recontar e dizer o quê
migra. (c) "Corpus mass ... is zero" não é derivável dos registros na árvore (o corpus
consolidado da campanha não está aqui) — manter como estimativa da auditoria externa,
com essa etiqueta, ou remover.

### 9.11 — `KeyPairSpec` construtor obrigatório · CONFIRMADA COM CORREÇÃO

Premissa confere: `ere: c1 (gpu | gpr)*` (`.mop:130`), api30 `KeyPair.cryptsl:27` ordena
`co?, (pu*, pr*)*`, massa 668/8 no registro (f) (conformance_record.csv:70; os dois
sítios nomeados somam 648 — o registro não é exaustivo por sítio).

**Três correções**: (a) **`c1?` não parseia** — a gramática ERE do rv-monitor
(`plugins_logicrepository/ere/.../EREParser.jj:52-57,:137-145`) tem `~ | * +` e
`epsilon`, **não tem `?`**; a forma implementável é
`ere: (c1 | epsilon) (gpu | gpr)*`. (b) "100 % of this specification's rows" não é
derivável do registro em árvore — mesma etiqueta da 9.10(c). (c) Registrar na linha do
reparo que o **expert discorda**: `KeyPair.crysl:20` ordena `Con, (GetPubl | GetPriv)*`
— construtor obrigatório; a spec de hoje é tradução fiel do expert, e o reparo segue a
convenção do projeto (ORDER responde à api30). A divergência entre oráculos deve ficar
escrita, não implícita.

### 9.12 — `SecureRandomSpec` `end` sem `next2` · REDUNDANTE

**Já reparada dentro da própria gh105.** Task 4.5 (concluída) diz textualmente *"the
`end`-state `next2` omission is repaired here"* (tasks.md:235-237); commit `a7e97294`
("dá ao `Ends*` a linha que faltava"); o fsm de hoje lista `next2 -> end`
(`SecureRandomSpec.mop`, bloco `end`), e o monitor **regenerado nesta sessão** tem
`Prop_1_transition_next2 = {3,1,1,3}` — o segundo `nextBytes()` é auto-laço em `end`.
A linha citada pela tarefa (`next2 = {3,3,1,3}`) é do monitor pré-4.5.

O que sobra é higiene: **conformance_record.csv:68 (item d) está obsoleta** — diz
"Recorded, not repaired" contradizendo a árvore. Reescrever a tarefa como retirada/
atualização dessa linha (com a ressalva de que a massa 12.400/43 foi medida sob o `jca`
congelado da campanha publicada, que continua com o defeito — a linha deve dizer sobre
qual conjunto fala). A sessão anterior copiou o item (d) do registro sem conferir a
árvore — exatamente o erro que o registro W2 do 9.2 não cometeu.

### 9.13 — automato do `CipherSpec` · CONFIRMADA COM CORREÇÃO

Premissas conferem no fsm de hoje (`CipherSpec.mop:339+`): `s3` lista só
`f1,f2,f3,f5,f6,f7` (sem laço de `update` → `init; update; update` falha) e `s2`/`end`
não listam `i1`/`i2`. Massa 10.814/21 ✓ (registro (e), conformance_record.csv:69).
Nenhum evento novo ✓ — e a observação do registro (e) de que o reparo "would need new
events" está errada para estes dois reparos: só transições.

**Correção substantiva — o alcance licenciado pelos oráculos é menor que o texto.**
api30 `Cipher.cryptsl:117`: `Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+`;
expert `Cipher.crysl:85`: `Get, Init+, AADUpdate*, WKB+ | (FINWOU | (Update+, DoFinal))+`.
**Nenhum dos dois admite re-`init` depois dos finais** — não há retorno de
`(...)+` para `Inits`. O que os oráculos licenciam: laço de `update` em `s3`
(`updates+`) e laço de `init` em `s2` (`Inits+`). Re-`init` em `end` ("a reused
Cipher") tornaria o `.mop` **mais permissivo que os dois oráculos** — se for desejado,
é decisão própria com linha de registro, não conformização. Reescrever a tarefa
separando os dois reparos licenciados da terceira transição não licenciada.

### 9.14 — `KeyStoreSpec` não-paramétrica · CONFIRMADA

`KeyStoreSpec.mop:23` declara `ks`; todos os sete eventos ligam `k` (`:53-87`);
monitor gerado process-wide confirmado (classe `KeyStoreSpecMonitor` sincronizada,
mapa único). Massa 8.655 + 2.005 / 22 ✓ (registro (a), conformance_record.csv:65).
Sequenciar com 9.16 como uma decisão ✓ — mesmo arquivo, mesma massa.

### 9.15 — `Cipher*Stream` não-paramétricas · CONFIRMADA

Headers sem parâmetro (`CipherInputStreamSpec.mop:10`, `CipherOutputStreamSpec.mop:10`);
0 de 97.018 ✓ (registro (b), conformance_record.csv:66); a alternativa "deixar
registrado" é legítima e a tarefa a oferece ao pesquisador ✓.

### 9.16 — sobrecarga `getInstance(String, Provider)` · CONFIRMADA

Tudo verificado nas quatro fontes: `javap` mostra a sobrecarga nas cinco classes (e
`KeyStore.getInstance(String, String)` + as duas de `File`); os quatro specs têm o
pointcut de 2 argumentos a alargar (Signature `:91`, Mac `:72`, KeyPairGenerator `:68`,
SSLContext `:95`, todos `(String, String)`); `KeyStoreSpec` não tem nenhum 2-arg (g1/g2
são o mesmo 1-arg com polaridade de guarda — gate_allowlist.csv:21, testemunha `g2 l1`
✓) e tem 7 de 17 eventos ✓ (um `getInstance(String, Object+)` cobre as duas formas e
respeita o teto). As cinco linhas de estado-0 conferem **no monitor regenerado**:
`Signature i1 = {8,...}[0]=8`, `Mac i1[0]=4`, `KeyStore load = {5,5,5,5,1,5}[0]=5`,
`KeyPairGenerator init1 = {4,4,4,2,4}[0]=4`, `SSLContext init = {3,3,1,3}[0]=3`.
Preferência por `Object+` com aridade conhecida ✓ (precedente `KeyGeneratorSpec.g2`;
nota do resolvedor em `KeyManagerFactorySpec.mop:87-90` confere). 10.660 = 8.655+2.005 ✓.

### 9.17 — guarda do `g2` do `SSLContextSpec` · CONFIRMADA COM CORREÇÃO

Premissa confere: `g2` guarda `condition(ConscryptAliasTable.matches(...))` (`:97`),
que `g1` perdeu na 3.6; api30 ordena `Gets, Init, Engine?` com o protocolo em
CONSTRAINTS (`SSLContext.cryptsl:39,:43`) ✓; o reparo espelha 3.6 e o `init` acusa uma
vez com PROTO-00 ✓; classificado em 9.B ✓ (o residuo — contexto rejeitado nunca
`init`-ado fica sem acusação — é o mesmo da 3.6).

**Duas correções**: (a) mecanismo — com a condição falsa **o monitor existe**:
`g2Event` faz `FindOrCreateEntry` antes de avaliar a condição; o objeto fica com
monitor em estado 0, e é de lá que o `init` cai em `fail` (`init[0]=3`). O resultado
que a tarefa descreve está certo; o "no monitor exists for that instance" não.
(b) registro — **não há linha `behavioural` própria** para o residuo do `g2` em
divergence_record.csv (as 9 linhas behavioural não o incluem); o adiamento vive no
comentário de `SSLContextSpec.mop:81-86` e na prosa dos hunks (:211,:213). Corrigir a
citação e criar a linha quando reparar.

### 9.18 — verificação do grupo · CONFIRMADA COM CORREÇÃO

Coerente com a disciplina R5/R6, mas: (a) "one harness pair committed per task" não se
aplica a 9.5 (javadoc Java), 9.6 (artefato OpenSpec) e 9.8 (tabela sem efeito de
veredito) — escopar aos reparos de spec; (b) para 9.2 o par vem `unchanged` por
construção (medido nesta sessão) — a evidência é outra (ver 9.2); (c) com 9.6 e 9.12
redundantes, as contagens e a lista de hunks mudam; (d) os três gates de 9.7 entram com
as correções de desenho (escopo do G-FORB; presença-no-zip do G-SIG).

---

## O que foi verificado e NÃO confirmou

1. **"O efeito visível [do 9.1] é só bookkeeping do `@match1`"** — falso; o evento
   revivido acusa ORDER-00 fora do estado aceitante, o monitor é criado pelo próprio
   evento, e o registro de origem já o dizia (conformance_record.csv:62). É a aposta
   do prompt que se confirmou.
2. **"O conjunto inteiro tem exatamente duas regras com FORBIDDEN"** (dossiê N1 e
   tarefa 9.7) — falso; são quatro por oráculo (`DigestInputStream`,
   `DigestOutputStream` além das duas).
3. **"The class is `removed`, never `unchanged`"** (9.2) — falso no instrumento
   exigido; medido: 159/159 `unchanged`, dedup por sítio no TraceRunner.
4. **"IvChainJunction ... call `isValid`"** (9.10) — falso; chama só `mode()` e já
   dobra caixa. A exposição real (alias antes do parse) é outra e maior.
5. **"Repair is `c1?`"** (9.11) — não parseia; a gramática ERE não tem `?`.
6. **A tarefa 9.12 inteira como reparo de spec** — o defeito já estava reparado na
   árvore (task 4.5); o que resta é o registro obsoleto.
7. **"Delete the four constants"** (9.5) — inviável; teste de paridade + leitores no
   `jca` congelado e em `rvsec-crysl-mop`.
8. **"proposal.md:17 says 24"** (9.6) — já diz 21.
9. **"no monitor exists for that instance"** (9.17) — o monitor existe, em estado 0.
10. **"re-init em s2/end conforme a api30"** (9.13) — a api30 (e o expert) não admitem
    re-`init` depois dos finais; metade do reparo não tem licença de oráculo.

## As exclusões da sessão anterior ("também vale verificar")

- **OPUS5-15 — exclusão errada em parte.** Recomputei as 22 linhas `IGUAL` da
  `constraint_table.csv` contra o expert e os `.mop`: **duas estão comprovadamente
  erradas** — `KeyStoreSpec | KeyStore.crysl:52` (expert admite 5 tipos; o `.mop`
  admite 9, com as adições deliberadas AndroidKeyStore/AndroidCAStore/BKS/BouncyCastle)
  e `SSLContextSpec | SSLContext.crysl:29` (expert admite 2 protocolos; o `.mop` admite
  3, com o `TLS` deliberado). Ambas deveriam ser `MOP-MAIS-PERMISSIVO` com justificativa
  registrada — são exatamente as duas permissividades deliberadas que a alegação
  apontava. As demais linhas `IGUAL` amostradas se sustentam (as cláusulas numéricas têm
  implementação ou razão registrada). Merece tarefa 9.A barata de recomputo.
- **OPUS5-16 — exclusão errada.** As 15 linhas `transcription` do
  `conformance_record.csv` têm a coluna `rule` apontando para `generated/api30/` (o
  âncora que a D-15 retirou) e `mop_literals` pré-D-15: CipherSpec cita
  `Api30CipherTransformationUtil` (hoje sem chamador), MessageDigest lista
  `MD5, SHA-224, SHA-1...` (a lista api30; a de hoje é SHA-256/384/512),
  SSLContext lista os 7 protocolos da api30 (hoje 3), KeyGenerator lista ChaCha20/ARC4/
  etc., KeyPairGenerator perde o 3072 restaurado. Higiene de registro, 9.A.
- **OPUS5-21 — exclusão certa para o grupo 9.** Método de contagem da campanha
  publicada, não conteúdo de spec; a "refutação barata" pertence ao lado do experimento
  (`experimento-gh104/`), e recomendo registrá-la lá como pendência, não silenciá-la.
- **OPUS5-26 — exclusão certa, verificada.** As escritas sobre o array em
  `TrustManagerFactorySpec:179` e `KeyManagerFactorySpec:149` estão no corpo do evento
  **que aterrissa no estado aceitante naquela mesma transição** (`:173-174`,
  `:140-144`), e um handler não vê o parâmetro — é a exceção registrada da INV-INS-134,
  com razão no arquivo e em `predicate_graph.csv`.
- **GPT5-21 / OPUS5-A1..A7 — parcialmente certo excluir.** O que virou 9.7 cobre três
  lacunas; desta sessão saem duas adições baratas para a mesma tarefa: a guarda
  anti-vazamento do `javap` (nova, demonstrada) e um verificador de **frescor de
  registro** (o caso 9.12 — linha de CSV contradizendo a árvore — seria pego por um
  check que recomputa claims mecânicos dos registros contra `.mop`/monitor).

## Implicações cruzadas

- **9.1 → 9.9**: decidem juntas o que `getDefault().createSSLEngine()` desenha; hoje o
  texto de cada uma promete um resultado que a outra desfaz.
- **9.1 sai de 9.A**: 9.A fica com 7 tarefas e nenhuma delas muda acusação — o grupo
  volta a poder seguir sem decisão, que era o desenho.
- **9.12 cai**: o item (d) sai do backlog e vira higiene; nenhuma outra tarefa dependia
  dele (9.11/9.13-9.16 apoiam-se em itens distintos do registro, todos reconferidos).
- **9.2/9.3**: a dedup por sítio do ErrorCollector é o mesmo fato para as duas —
  qualquer contagem de inflação futura deve contar **sítios**, não emissões.
- **As massas 9.11/9.13/9.14/9.15/9.16** foram todas reconferidas contra
  `conformance_record.csv` (linhas 65,66,69,70,71) e batem; continuam sendo teto, não
  atribuição causal, como o próprio grupo já dizia.

## O que esta sessão não conseguiu verificar

Nada foi rodado em emulador ou campanha; o monitor regenerado foi compilado e exercitado
pelo TraceRunner (classpath JSE do arnês), não com o classpath Android completo nem
tecido num APK — as duas afirmações sobre o tecelão DEX (gate de tipo de retorno no
caminho dexlib2) foram aceitas do registro (conformance_record.csv:62,:73), não
reproduzidas. Os riders de corpus que só o consolidado da campanha decide ("100 %" da
9.11, "corpus zero" da 9.10) não são deriváveis dos registros na árvore e ficaram
etiquetados como estimativa externa. A identificação exata das outras duas linhas
`IGUAL` que a OPUS5-15 alega (além das duas confirmadas) exigiria recomputo completo
das 22 — amostrei as de maior risco e não achei terceira.

## Anexo — pares de arnês desta sessão

- **9.2** (`A=jca_android`, `B=+__RESET` no `@fail` do KPG): `{"unchanged": 159}`;
  `KeyPairGeneratorSpec-sticky-fail.txt` com uma única linha
  `gen:KEYPAIRGENERATOR-ORDER-00` em ambos os lados.
- **9.4** (`A=jca_android`, `B=condition(!matches(alg))` nos dois gêmeos):
  `{"unchanged": 159}` — acusações idênticas evento a evento em todos os traces de
  `KeyGeneratorSpec` e `MessageDigestSpec` (incluindo os `*-guard-on-field.txt` e os
  `*-d15-*.txt`). A previsão da tarefa — comportamento inalterado por construção,
  provável pelo arnês — confirmou empiricamente.
