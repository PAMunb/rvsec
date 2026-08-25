# Tarefa 9.11 — o construtor obrigatório que nenhum `KeyPair` do Android chama

**Data**: 2026-08-25 · **Decisão**: GO (pesquisador, 25/08)
**Par**: `A = pós-9.13` · `B = A + 9.11` · `~/tmp-gh104/g9b/pair-911b.json`
(o `pair-911.json` é a primeira passagem, medida antes do reparo do `c1` que ela mesma expôs;
fica registrada porque foi ela que o expôs, e não é o par desta tarefa)

## O reparo

```
ere: c1 (gpu | gpr)*        ->        ere: (c1 | epsilon) (gpu | gpr)*
```

`c1` é `KeyPair(PublicKey, PrivateKey)`. No Android praticamente todo `KeyPair` sai de
`generateKeyPair()`, que **não dispara `c1`** — e aí todo `getPublic()`/`getPrivate()` sobre o par
gerado tirava `KEYPAIR-ORDER-00`.

### Não é `c1?`

A gramática ERE do rv-monitor
(`rv-monitor/plugins_logicrepository/ere/.../EREParser.jj:49-60`) declara os operadores
`~ & | * + ^` e exatamente duas palavras, `epsilon` e `empty`. **Não tem `?`** — lido no arquivo, o
atalho não parseia. A forma implementável é `(c1 | epsilon)`.

### Um defeito de gate saiu junto

O primeiro `gh104_mop_lint.py` sobre o conjunto reparado acusou
`` `epsilon` is named in the ere and declared nowhere ``. O sweep de símbolos compartilhado com o
G-ERE (`gh104_gates.py:formula_symbols`) tratava as palavras-chave da gramática como nomes de
evento. **É defeito pré-existente, não meu**: o mesmo sweep acusava
`generic_new/ListIterator_Set.mop:36`, que usa `epsilon` desde antes desta change e num conjunto
que nenhuma tarefa toca. Corrigido excluindo `epsilon` e `empty` do sweep, com a razão escrita na
constante. Caminho vermelho: `generic_new` estava vermelho antes e verde depois, sem que nada
naquele conjunto mudasse.

## Os oráculos discordam, e isso vai escrito

| oráculo | ORDER | construtor |
|---|---|---|
| api30 `KeyPair.cryptsl:27` | `co?, (pu*, pr*)*` | opcional |
| expert `KeyPair.crysl:20` | `Con, (GetPubl \| GetPriv)*` | **obrigatório** |

O que estava no `.mop` era tradução fiel do expert. O reparo segue a convenção do projeto — **ORDER
responde à api30, valores respondem ao expert** (D-15) — e a divergência entra na linha do reparo,
não fica implícita.

## O medido

O trace `KeyPairSpec-generated.txt` usa a forma `bind`, que produz o objeto e não dispara nada:
é o que torna o caso expressável no arnês, porque o monitor nunca vê um `c1`.

Duas passagens, e a diferença entre elas é a matéria da seção "A quinta linha" abaixo. A primeira
mediu o `ere` sozinho, com o `c1` ainda ligando pelo nome errado; a segunda — o par desta tarefa —
mede o reparo inteiro, `ere` e ligação, contra o mesmo lado A:

```
pair-911:  172 traces  {"unchanged": 167, "removed": 4, "moved": 1}   <- só o `ere`
pair-911b: 172 traces  {"unchanged": 167, "removed": 5}               <- `ere` + `returning(keyPair)`
```

É o maior delta do bloco, e **quatro dos cinco traces já estavam no corpus** — o falso positivo
estava medido e aceito havia tempo:

| trace | A | B (`pair-911`) | B (`pair-911b`) |
|---|---|---|---|
| `KeyPairSpec-generated.txt` (novo) | `gpu:KEYPAIR-ORDER-00`, `gpr:KEYPAIR-ORDER-00` | *(nada)* | *(nada)* |
| `KeyPairSpec-generated-cipher.txt` | `gpu:KEYPAIR-ORDER-00` | *(nada)* | *(nada)* |
| `SignatureSpec-generated-pubkey.txt` | `gpu:KEYPAIR-ORDER-00` | *(nada)* | *(nada)* |
| `SignatureSpec-generated-privkey.txt` | `gpr:KEYPAIR-ORDER-00` | *(nada)* | *(nada)* |
| `KeyPairSpec-observed-halves.txt` | `gpu:KEYPAIR-ORDER-00`, `gpr:KEYPAIR-ORDER-00` | **`c1:KEYPAIR-ORDER-00`** | *(nada)* |

O lado A é o mesmo snapshot (`B-913`) nas duas passagens, e o `B-911b` difere do `B-913` num
arquivo só, o `KeyPairSpec.mop`: o delta é atribuível a esta tarefa e a mais nada.

Lido no monitor gerado, o `(c1 | epsilon)` compila exatamente como pedido:

| | `c1` | `gpu`/`gpr` | `Category_match` |
|---|---|---|---|
| **A** | `{1,2,2}` | `{2,1,2}` | `state == 1` |
| **B** | `{1,2,2}` | `{1,1,2}` | `state == 0 \|\| state == 1` |

O estado 0 passa a ser aceitante (é o `epsilon`) e `gpu`/`gpr` de lá vão para 1 em vez de 2.

## A quinta linha: um defeito que este reparo desmascarou

`KeyPairSpec-observed-halves.txt` é o **caso conforme** documentado do corpus, e no lado B ele
ganhou uma acusação. Não era falha do `ere`. Era isto:

```
KeyPairSpec(KeyPair keyPair)                  <- o parâmetro declarado
event c1 ... returning(KeyPair kp)            <- o nome que o evento liga
```

O gerador chaveia o monitor paramétrico pelos parâmetros do evento **cujo nome é o parâmetro
declarado**. `kp` não é `keyPair`, então o `c1` **não ligava objeto monitorado nenhum**: recebia o
mapa sem parâmetro e rodava no monitor raiz e em todo monitor vivo da especificação — a mesma
difusão que a task 9.3 fechou no `PBEKeySpecSpec`, chegando por um nome em vez de por uma cláusula
ausente. É o defeito da 9.14 (`ks` contra `k`) num arquivo diferente.

Por que só apareceu agora: com o construtor obrigatório, o `gpu`/`gpr` do par gerado levava aquele
monitor a `fail`, o `__RESET` o devolvia a `start`, e um `c1` difundido é aceito em `start`. Com o
construtor opcional as leituras deixam o monitor no estado aceitante, e o `c1` difundido chega onde
`c1` é `fail`. **O reparo não criou o defeito; tirou o que o escondia.**

Corrigido no mesmo lugar: `returning(KeyPair keyPair)`.

## O G-BIND foi estendido, e o que ele acha prova que precisava ser

O G-BIND checava presença de cláusula: "tem `returning(...)` ou `target(...)`?". O `c1` tinha, com
o tipo certo, e ligava nada. O gate passa a **comparar o nome ligado** com o parâmetro declarado.

Varredura do universo depois da extensão, com o `c1` já reparado:

| conjunto | achados |
|---|---|
| `jca_android` (vivo) | 3 — `HMACParameterSpecSpec.c`, `RandomStringPassword.vo`/`gb`, os dois inertes |
| `jca` (congelado) | 11 — **o `KeyStoreSpec` inteiro** (os sete eventos), `KeyPairSpec.c1`, e as demais |
| `jca_android_bug_predicate` (arquivado) | 11 — as mesmas, herdadas |

Sobre o congelado o gate **redescobriu sozinho o defeito que a 9.14 reparou** — `KeyStoreSpec`
declarando `ks` e ligando `k` nos sete eventos — sem que ninguém lhe dissesse onde olhar. É a
mesma prova que o G-SIG deu ao achar três defeitos de assinatura já reparados. Os 22 do congelado e
do arquivado entram por congelamento com o reparo do sucessor nomeado; os três vivos entram com a
razão medida (o `HMACParameterSpec` está **ausente** do android-30, e o `RandomStringPassword` não
tem `@fail` e tem `@match` vazio — não acusa nada).

## A remedição, e o que ela fecha

O `pair-911b` foi rodado em 25/08 com `A = B-913` e `B = B-913 + o KeyPairSpec.mop da árvore viva`
— o `ere` opcional **e** o `returning(KeyPair keyPair)`. As cinco linhas viraram `removed`, a
`KeyPairSpec-observed-halves.txt` inclusive: o caso conforme do corpus deixa de ser acusado, que é
o que a primeira passagem prometia e o `c1` difundido impedia.

O `B-911b` foi montado a partir do `B-913`, e não do `B-911`, por um detalhe que vale registrar: o
`B-911` carregava um `jca_android/` aninhado, cópia acidental do próprio conjunto dentro do
snapshot. Como o gerador recebe o diretório e não a lista de arquivos, um snapshot com uma segunda
cópia lá dentro não é o conjunto que se quis medir. Partir do `B-913` limpo e sobrepor o único
arquivo editado dá a isolação que o par afirma ter — `diff -rq B-913 B-911b` responde
`KeyPairSpec.mop` e nada mais.

## Massa

**668 linhas sobre 8 apps** (`conformance_record.csv` item (f)), teto e não atribuição causal. O
"100 % das linhas desta especificação" da auditoria externa é estimativa dela e **não é derivável
desta árvore**.
