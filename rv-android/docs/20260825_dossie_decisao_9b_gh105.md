# Dossiê de decisão — bloco 9.B da gh105

**Data**: 2026-08-25 (terceira sessão do dia) · **Árvore**: `d31e2a04`
**Objeto**: as nove tarefas de `openspec/changes/gh105-predicate-wiring/tasks.md` §9.B —
o bloco que **muda o conjunto de programas que a especificação acusa** e que, por isso, não
anda sem go/no-go do pesquisador, tarefa a tarefa.
**Fontes**: os 18 vereditos de `docs/20260825_verificacao_grupo9_gh105.md`, as cinco evidências
`data/gh105/evidence/f6-*.md`, o `conformance_record.csv` (massas), os `.mop` de hoje e os dois
oráculos. Nada aqui é citação de auditoria externa não reconferida.

## Como ler as massas

Toda massa citada vem do consolidado da campanha publicada, medido sobre o **conjunto `jca`
congelado**. É **teto do que o reparo poderia mover, nunca atribuição causal**: o tecelão foi
reparado entre aquela campanha e hoje, e o sucessor difere do semeador em 24 arquivos. Onde a
auditoria externa deu número que a árvore não deriva ("100 %", "corpus zero"), o número está
etiquetado como estimativa e não entra na recomendação.

## O estado que força a decisão agora

Dois dos três gates novos da 9.7 **já estão vermelhos, e exatamente nestas tarefas**:

```
G-SIG:  416 checked, 1 failed   → o único achado é a 9.1
G-FORB:  18 checked, 2 failed   → os dois achados são a 9.9 (um por oráculo)
G-BIND: 843 checked, 0 failed   → verde
```

A 9.18 exige as quatro suítes verdes para fechar o grupo. Não há terceira via: ou a tarefa é
aprovada e o gate fecha, ou o adiamento ganha a sua linha de `gate_allowlist.csv` — como as
nove divergências de ordenação que esta change já mantém de propósito. **Adiar é uma resposta
legítima; adiar sem registrar não é.**

---

## Achado estrutural: as tarefas do `SSLContextSpec` têm ordem obrigatória

Quatro das nove tocam o mesmo arquivo, e a ordem entre elas não é preferência — é o que separa
um reparo de um falso positivo novo. O `fsm` de hoje é:

```
start [ g1 -> s1   g2 -> s1 ]        s1 [ init -> end ]        end [ engine -> end ]
```

`engine` só está listado em `end`; nos demais estados a linha é `fail` (`{3,1,3,3}` no monitor
regenerado). E `SSLContextSpec_engineEvent` faz `FindOrCreateEntry`: **cria monitor em estado 0
quando não há um**. Logo, no dia em que a 9.1 revive o evento, todo `SSLContext` cujo nascimento
o conjunto não observou passa a acusar `SSLCONTEXT-ORDER-00` no primeiro `createSSLEngine()`.

Hoje há **três** maneiras de um `SSLContext` chegar vivo sem monitor em `s1`:

| origem | hoje | quem fecha |
|---|---|---|
| `getInstance(String, Provider)` — sem pointcut nos 5 specs | sem monitor | **9.16** |
| `getInstance("TLSv1", provider)` — `g2` com guarda de protocolo não dispara | monitor criado em estado 0 | **9.17** |
| `getDefault()` — FORBIDDEN, sem evento | sem monitor | **9.9** (e continua acusando, por desenho) |

**Consequência**: aprovar a 9.1 sem a 9.16 e a 9.17 compra falso positivo de ordem em duas
populações que nada tem a ver com o defeito que a 9.1 repara. A ordem correta é
**9.17 → 9.16 → 9.9 → 9.1**.

---

## Decisão 1 — 9.1 + 9.9, juntas (`SSLContextSpec`)

**9.1** — `call(public void SSLContext.createSSLEngine(..))` onde o android-30 declara
`public final SSLEngine createSSLEngine()`. Os dois tecelões filtram o tipo de retorno
exatamente: o advice é gerado e **nunca disparou**. Varredura de assinaturas dos 143 sítios
`call(...)` do conjunto: **é o único mismatch de tipo de retorno**.

**9.9** — `getDefault()` é FORBIDDEN nos **dois** oráculos (`SSLContext.crysl:10-11`, api30
`SSLContext.cryptsl`) e o conjunto não tem evento para ele. `SSLContext.getDefault()` é
silêncio total hoje. A omissão não aparece em registro nenhum — não é decisão, é inconsistência,
e a única outra cláusula FORBIDDEN **com `.mop` no conjunto** (os dois construtores do
`PBEKeySpec`) **está** implementada, com `ErrorType.ForbiddenMethod` e códigos próprios.

### Por que decidem juntas, e o que o precedente já resolveu

Se a 9.9 entra e a 9.1 não, `getDefault()` acusa FORB e o `createSSLEngine()` seguinte continua
mudo. Se a 9.1 entra e a 9.9 não, `getDefault().createSSLEngine()` acusa **ORDER-00** — o código
errado para o defeito certo, que é precisamente a classe que a 9.17 repara noutro ponto do mesmo
arquivo e que o G-FORB achou no `jca` congelado.

A pergunta de desenho — o evento novo deve fazer o `engine` calar? — **já foi respondida nesta
change**, no `PBEKeySpecSpec`. O idioma é `ere: (f1 | f2)* c1 (f1 | f2)* c2 (f1 | f2)*`: o evento
proibido é **auto-laço em toda posição**, levanta o seu FORB no corpo, e a ORDER segue como se
ele não tivesse acontecido. E o resíduo está escrito no arquivo (`:183-189`):

> *absorver um construtor proibido por um grupo de Kleene silencia o relato de ordenação na
> própria chamada proibida, mas não na chamada obrigatória que a segue (...) Silenciar isso
> significaria modelar `f1` como abertura alternativa da ordenação, que é o oposto do que
> FORBIDDEN diz.*

Aplicado aqui: `getDefault` entra com auto-laço em `start`, `s1` e `end`; `engine` **não** ganha
laço em `start`. `getDefault().createSSLEngine()` tira FORB-00 **e** ORDER-00, e esse segundo é
o mesmo resíduo que a change já ratificou uma vez. A alternativa (dar `engine -> start`) compra
o silêncio ao preço de uma divergência **nova** de G-ORDER — o autômato ficaria mais permissivo
que `Gets, Init, Engine?` —, e o arquivo já carrega uma divergência de ordenação aberta
(task 7.1).

### Delta esperado

| programa | hoje | depois de 9.9+9.1 (com 9.16 e 9.17 já dentro) |
|---|---|---|
| `getInstance` → `init` → `createSSLEngine()` | silêncio | silêncio + escrita de `GENERATE_SSL_ENGINE` (sem leitor, INV-INS-137) |
| `getDefault()` | silêncio | **SSLCONTEXT-FORB-00** |
| `getDefault().createSSLEngine()` | silêncio | **FORB-00 + ORDER-00** (resíduo registrado, precedente `PBEKeySpecSpec`) |
| `createSSLEngine()` antes do `init` | — | inalcançável: lança `IllegalStateException`, e um `after returning` não dispara |

**Massa**: nenhuma. O registro que a 9.1 aposenta (`conformance_record.csv:62`) diz que o
não-reparo foi decisão do pesquisador em 2026-08-18 justamente porque *"the published corpus
cannot size that"*. É a única tarefa do bloco sem teto medido.

**Recomendação: GO nas duas, nesta ordem, e depois da 9.17 e da 9.16.** A 9.9 é reparo de falso
negativo licenciado pelos dois oráculos e fecha o G-FORB; a 9.1 sem ela troca um evento morto
por acusação com o código errado. Juntas, e atrás das outras duas, o delta se reduz a *acusar
`getDefault()`, que é o que os oráculos mandam*. Se o adiamento for a escolha, são **três**
linhas de `gate_allowlist.csv` (uma G-SIG, duas G-FORB) e a 9.1 continua sendo um evento que o
conjunto declara e nunca dispara.

---

## Decisão 2 — 9.17 (`SSLContextSpec`, guarda do `g2`)

`g2` ainda carrega `condition(ConscryptAliasTable.matches(...))` que a task 3.6 tirou do `g1`.
Com a condição falsa o evento não dispara — mas o despachante **cria o monitor assim mesmo**
(`FindOrCreateEntry` roda antes da condição), ele fica em estado 0, e o `init` seguinte cai em
`fail` de lá (`init[0] = 3`). Resultado: **um protocolo rejeitado é relatado como sequência de
chamadas errada.** A api30 ordena `Gets, Init, Engine?` com o protocolo em CONSTRAINTS
(`SSLContext.cryptsl:39,:43`) — `getInstance` é um `Gets` seja qual for o protocolo pedido.

**Delta**: troca de código, não de volume. `getInstance("TLSv1", provider); init(...)` sai de
`SSLCONTEXT-ORDER-00` e entra em `SSLCONTEXT-PROTO-00`, uma vez, pelo corpo do `init`.
**Resíduo** (o mesmo da 3.6): um contexto rejeitado que nunca é `init`-ado fica sem acusação.

**Massa**: sem linha própria; a 3.6 mediu a metade `g1` do mesmo defeito.

**Recomendação: GO.** Espelha exatamente a 3.6, já executada e medida nesta change; corrige uma
acusação mal classificada — a mesma classe que o G-FORB achou no `jca` congelado (construtor
proibido relatado como sequência errada). Precisa escrever a linha `behavioural` do
`divergence_record.csv` que hoje **não existe** para este resíduo (verificado: não está entre as
nove). É também precondição da 9.1.

---

## Decisão 3 — 9.16 + 9.14, juntas (`KeyStoreSpec` e mais quatro)

**9.16** — `getInstance(String, Provider)` não tem pointcut em `KeyStoreSpec`, `SignatureSpec`,
`MacSpec`, `KeyPairGeneratorSpec` e `SSLContextSpec`, embora o android-30 declare a sobrecarga
nas cinco. O objeto obtido por ela chega ao evento seguinte com o monitor em estado 0, onde toda
linha é `fail`: `Signature i1[0]=8`, `Mac i1[0]=4`, `KeyStore load[0]=5`,
`KeyPairGenerator init1[0]=4`, `SSLContext init[0]=3` (lidas no monitor regenerado). Em quatro
dos cinco o reparo **alarga o pointcut de dois argumentos e não cria evento**; só o
`KeyStoreSpec` não tem nenhum 2-arg e precisa de um evento novo — tem 7 de 17, cabe.

**9.14** — `KeyStoreSpec` declara `ks` e todos os sete eventos ligam `k`, então o gerador emite
**um monitor por processo**, não um por key store: um segundo `getInstance` antes do primeiro
`load` falha. Parametrizar.

**Por que juntas**: mesmo arquivo, mesma massa publicada, e a 9.16 cria um evento no arquivo que
a 9.14 reparametriza. Sequenciar como uma decisão só, na ordem 9.14 → 9.16.

**Delta**: os dois removem acusação. A parametrização tem um efeito de segunda ordem que vale
declarar: hoje o monitor único, uma vez em `fail` (sumidouro), absorve tudo o que vem depois numa
acusação só; parametrizado, cada store acusa por si — então o **número de linhas pode subir**
mesmo com o conjunto de programas acusados encolhendo. As linhas novas são corretas; a contagem
bruta não é a métrica.

**Massa**: 8.655 `InvalidSequenceOfMethodCalls` + 2.005 `InvalidKeyStoreType` sobre 22 apps
(`conformance_record.csv:65`, item (a)); a fatia do `KeyStoreSpec` na 9.16 são as mesmas 10.660.
É a **maior massa do bloco**.

**Recomendação: GO nas duas.** A 9.16 é a mais barata do bloco em quatro dos cinco arquivos
(alargar pointcut, nenhum evento novo) e fecha uma lacuna de plataforma pura — o `.mop` não vê
uma sobrecarga que existe. Preferir `Object+` a `..` onde a aridade é conhecida: um curinga na
assinatura do `call` para o resolvedor do arnês no primeiro tipo curinga
(`KeyManagerFactorySpec.mop:88-90`). A 9.14 é a maior devolução de falso positivo do bloco.

---

## Decisão 4 — 9.13 (`CipherSpec`, duas transições)

Duas divergências de ORDER, ambas reparáveis por transição sobre eventos que já existem — o
`fsm` não ganha evento e o teto de 17 não é tocado (o que corrige a observação do item (e) de
que reparar "would need new events").

**Licenciado pelos dois oráculos**:
- `s3` não tem laço de `update`, então `init; update; update` falha onde a api30 dá `updates+`
  (`Cipher.cryptsl:117`) e o expert dá `Update+` (`Cipher.crysl:85`) — acrescentar `u*` em `s3`;
- `s2` não tem laço de `init`, então `init; init` falha onde os dois dão `Inits+`/`Init+` —
  acrescentar `i1`/`i2 -> s2`.

**NÃO licenciado por nenhum**: re-`init` em `end` (o "Cipher reusado"). Nenhuma das duas ORDER
retorna do grupo dos finais para `Inits`. Essa transição tornaria o `.mop` **mais permissivo que
os dois oráculos** — se for desejada é decisão própria, com linha de registro, e não faz parte
de um reparo de conformidade.

**Delta**: remove acusação, nas duas transições licenciadas.
**Massa**: 10.814 linhas sobre 21 apps (`conformance_record.csv:69`, item (e)) — teto **das duas
classes juntas**, o registro não as separa.

**Recomendação: GO nas duas transições licenciadas, NO na terceira.** É conformidade estrita:
os dois oráculos concordam, nenhum evento novo, e é a segunda maior massa do bloco.

---

## Decisão 5 — 9.11 (`KeyPairSpec`, construtor obrigatório)

`ere: c1 (gpu | gpr)*` torna o construtor `KeyPair(PublicKey, PrivateKey)` obrigatório. No
Android praticamente todo `KeyPair` vem de `generateKeyPair()`, que **nunca dispara `c1`** — e aí
todo `getPublic()`/`getPrivate()` tira `KEYPAIR-ORDER-00`.

**A forma do reparo é `ere: (c1 | epsilon) (gpu | gpr)*`, não `c1?`**: a gramática ERE do
rv-monitor (`EREParser.jj:52-57,:137-145`) tem `~ | * +` e `epsilon`, e **não tem `?`** — o
atalho não parseia.

**Os oráculos discordam aqui, e isso vai na linha do reparo**: a api30 (`KeyPair.cryptsl:27`)
ordena `co?, (pu*, pr*)*` — construtor opcional; o expert (`KeyPair.crysl:20`) ordena
`Con, (GetPubl | GetPriv)*` — obrigatório. O `.mop` de hoje é tradução fiel do expert; o reparo
segue a convenção do projeto (**ORDER responde à api30**, valores respondem ao expert — D-15). A
divergência fica escrita, não implícita.

**Delta**: remove acusação. **Massa**: 668 linhas sobre 8 apps (`conformance_record.csv:70`,
item (f)). O "100 % das linhas desta especificação" da auditoria é estimativa dela, não derivável
do registro.

**Recomendação: GO.** Uma linha, convenção de projeto já estabelecida, e o falso positivo mais
sistemático do bloco em plataforma Android.

---

## Decisão 6 — 9.10 (normalizador de `Cipher`, toca Java)

`CipherSpec` é a única das doze especificações que carregam valor que **não normaliza**: os seus
cinco sítios `isValid(...)` (`:85`, `:92`, `:100`, `:108`, `:181`) chamam a congelada
`CipherTransformationUtil`, enquanto as outras onze comparam por `ConscryptAliasTable.matches`,
que dobra caixa e resolve alias. Os defeitos conferem linha a linha: `alg(t).equals("AES")` e
`modes.contains(mode(t))` sensíveis a caixa (`:44`, `:45`; só o padding faz `toUpperCase()`,
`:46`); lista CBC `[PKCS5PADDING, ISO10126PADDING, PKCS5PADDING]` (`:35` — duplicata, sem
PKCS7); ramo RSA só `""`/`"ECB"` (`:64-65`).

**Falsos positivos deriváveis**: `AES/CBC/PKCS7Padding`, `aes/cbc/pkcs5padding`,
`AES/cbc/PKCS5Padding`, `RSA/None/PKCS1Padding`.

**Não reabre a D-15, e a licença é o mecanismo**: o expert (`Cipher.crysl:113`) não lista PKCS7,
mas os mapeamentos são registrações `Alg.Alias` do provider pinado que o projeto já extraiu —
`alias_table.csv` `Cipher,AES/CBC/PKCS7Padding,AES/CBC/PKCS5Padding,380` e
`Cipher,RSA/None/PKCS1Padding,RSA/ECB/PKCS1Padding,334`, hoje sem leitor — e resolver-alias-
então-comparar-com-o-expert é exatamente o que a D-15 ratificou para as outras onze. **Não
reviver `Api30CipherTransformationUtil`**: ela transcreve o catálogo api30 (admite `AES/ECB`,
`ARC4`, `BLOWFISH`) e a própria doc encerra *"It is not to be given a caller again"*.

**Há uma segunda exposição, maior, e ela vai na direção contrária**: `IvChainJunction` **não
chama `isValid`** e já dobra caixa nos dois testes de modo (`:139`, `:173`, `Locale.ROOT`) — mas
extrai `mode()` da transformação **não resolvida** (`:136`). Uma grafia de alias como
`PBEWithHmacSHA1AndAES_128` (canônico `AES_128/CBC/PKCS5PADDING`, `alias_table:394-398`) dá
`mode() == ""` e **fura as cláusulas de IV e GCM em silêncio**. Resolver o alias antes do parse
**acrescenta** acusação — fecha falso negativo.

**Delta**: nos dois sentidos. Os cinco sítios `isValid` **removem** falso positivo de grafia; o
`IvChainJunction` **acrescenta** acusação verdadeira. As duas metades podem ser decididas
separadamente, se preferir.
**Massa**: "corpus zero" é estimativa da auditoria externa; **não é derivável desta árvore** (o
consolidado da campanha não está aqui). O par de arnês é a evidência, com essa etiqueta.
**Custo**: é a única tarefa do bloco que toca Java — classe nova em `rvsec-core` ao lado da
congelada, e build do reator.

**Recomendação: GO nas duas metades.** A inconsistência é pura: onze specs normalizam, uma não.
Mas é a tarefa mais cara em tempo e a única que pede build do reator — se o orçamento apertar,
é a primeira a adiar, e adiar aqui não deixa gate vermelho.

---

## Decisão 7 — 9.15 (`Cipher*Stream` não-paramétricas)

`CipherInputStreamSpec` e `CipherOutputStreamSpec` não declaram parâmetro (`:10` nos dois), então
cada uma é uma instância única por processo e dois streams entrelaçados falham no segundo
construtor.

**Massa: 0 linhas de 97.018** (`conformance_record.csv:66`, item (b)). O reparo é **livre de
consequência de corpus** — e é por isso que a tarefa oferece explicitamente as duas saídas.

**Recomendação: GO, fraca.** É o jeito mais barato de aposentar o item (b), e reparar a 9.14
deixando estas duas não-paramétricas mantém no conjunto a inconsistência que a change existe
para tirar. Mas o par de arnês vai vir `unchanged` por construção e não haverá evidência de
melhora — se preferir deixar registrado em vez de reparado, é escolha defensável e custa zero.

---

## Não é decisão — 9.12 pertence ao 9.A

A 9.12 foi reescrita: **o defeito de spec já estava reparado** pela task 4.5 (commit
`a7e97294`). O `fsm` de hoje lista `next2 -> end` e o monitor regenerado lê
`Prop_1_transition_next2 = {3,1,1,3}` — um segundo `nextBytes()` é auto-laço. O que resta é
`conformance_record.csv:68` dizendo "Recorded, not repaired", contradizendo a árvore.

Pelo critério do próprio grupo — *muda o conjunto de programas acusado?* — **não muda nada**: é
higiene de registro, a mesma classe da 9.8 e da 9.19(b), que estão no 9.A. **Proponho mover a
9.12 para o 9.A e executá-la sem go/no-go**, reescrevendo a linha para nomear o reparo da 4.5 e
declarando de qual conjunto fala cada metade da massa 12.400/43 (medida sobre o `jca` publicado,
que continua com a omissão).

---

## Quadro para a decisão

| # | tarefa | direção do delta | massa (teto) | custo | recomendação |
|---|---|---|---|---|---|
| 1 | **9.17** `g2` sem guarda | troca de código (ORDER→PROTO) | — | baixo | **GO** — precondição da 9.1 |
| 2 | **9.16** + **9.14** KeyStore | remove acusação | **10.660** / 22 apps | médio | **GO** — precondição da 9.1 |
| 3 | **9.9** + **9.1** SSLContext | acrescenta (`getDefault`) | nenhuma medida | médio | **GO**, atrás de 1 e 2 |
| 4 | **9.13** Cipher (2 de 3) | remove acusação | **10.814** / 21 apps | baixo | **GO** nas 2 licenciadas, **NO** na 3ª |
| 5 | **9.11** KeyPair | remove acusação | **668** / 8 apps | baixo | **GO** |
| 6 | **9.10** normalizador | remove **e** acrescenta | não derivável | **alto** (Java + reator) | **GO**, primeira a adiar |
| 7 | **9.15** Cipher*Stream | remove acusação | **0** / 97.018 | baixo | **GO** fraco — ou registrar |
| — | 9.12 | nenhuma | — | baixo | **mover para 9.A** |

**Se tudo for aprovado**, a ordem de execução é 9.17 → 9.14 → 9.16 → 9.9 → 9.1 → 9.13 → 9.11 →
9.15 → 9.10, e cada uma leva: edição do `.mop` → monitor regenerado → par de arnês → hunk keyed
no `divergence_record.csv` → `codes.csv` re-ancorado → evidência `f6-*.md` → `[x]`. Nenhuma fecha
por exit code de gate (R5/R6).

**Se alguma for adiada**, a linha de `gate_allowlist.csv` entra junto com a decisão — para 9.1 e
9.9 isso é obrigatório, porque os gates estão vermelhos hoje e a 9.18 exige as quatro suítes
verdes.
