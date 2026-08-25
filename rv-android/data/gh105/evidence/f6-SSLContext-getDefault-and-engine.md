# Tarefas 9.9 e 9.1 — a cláusula FORBIDDEN sem acusador, e o evento que nunca disparou

**Data**: 2026-08-25 · **Decisão**: GO nas duas, juntas, com o idioma do `PBEKeySpecSpec`
(pesquisador, 25/08) · **Pares**: `pair-909` (`A = pós-9.16`, `B = A + 9.9`) e
`pair-901` (`A = pós-9.9`, `B = A + 9.1`)

As duas decidiram juntas porque cada uma, sozinha, desfaz o que a outra promete: a 9.9 sem a 9.1
acusa o `getDefault()` e deixa o `createSSLEngine()` seguinte mudo; a 9.1 sem a 9.9 acusa
`getDefault().createSSLEngine()` com **SSLCONTEXT-ORDER-00** — o código errado para o defeito
certo. Os dois pares abaixo são a mesma decisão medida em dois passos.

## A pergunta de desenho já tinha resposta nesta change

Os dois oráculos escrevem a cláusula como `getDefault() => Gets` — leem a chamada proibida como
ocupando a posição de ORDER que o `getInstance` legítimo ocupa. Seguir isso ao pé da letra faria o
evento novo abrir a ordenação, e aí `getDefault().createSSLEngine()` ficaria em silêncio de
ordenação.

O `PBEKeySpecSpec` já respondeu isso, sobre a cláusula **idêntica** `PBEKeySpec(char[]) => Con`. O
idioma é `ere: (f1 | f2)* c1 (f1 | f2)* c2 (f1 | f2)*` — o evento proibido é auto-laço em toda
posição, levanta o seu FORB no corpo, e a ORDER segue como se ele não tivesse acontecido. E o
resíduo está escrito no arquivo (`:183-189`):

> *absorver um construtor proibido por um grupo de Kleene silencia o relato de ordenação na própria
> chamada proibida, mas não na chamada obrigatória que a segue (...) Silenciar isso significaria
> modelar `f1` como abertura alternativa da ordenação, que é o oposto do que FORBIDDEN diz.*

Aplicado aqui: `getDefault` entra no `fsm` com auto-laço em `start`, `s1` e `end`; o `engine` **não**
ganha laço em `start`. A alternativa (`engine -> start`) tornaria a 9.1 neutra em acusação, mas ao
preço de uma divergência **nova** de G-ORDER num arquivo que já carrega uma aberta (`g1 Init se1 se1`,
task 7.1). Recusada.

## 9.9 — o medido

```
pair-909: 172 traces  {"unchanged": 170, "introduced": 2}
```

| trace | A | B |
|---|---|---|
| `SSLContextSpec-getdefault.txt` | *(nada)* | `getDefault:SSLCONTEXT-FORB-00` |
| `SSLContextSpec-getdefault-engine.txt` | *(nada)* | `getDefault:SSLCONTEXT-FORB-00` |

Silêncio de ponta a ponta antes; uma acusação com `ErrorType.ForbiddenMethod` depois. Note que o
segundo trace tira **só** o FORB neste par: o `engine` ainda está morto, porque a 9.1 não entrou.

O corpo do evento não escreve campo nenhum — nem `context`, nem `currentProtocol`. O auto-laço
mantém o monitor onde estava, `@match1` só é alcançável de `end`, e nenhuma rota daqui chega lá:
um contexto de `getDefault()` que depois é `init`-ado vai `start -> fail`. Duas escritas que
handler nenhum lê são exatamente o bookkeeping que a INV-INS-137 manda parar de escrever.

O `getDefault` entrou no `order_alphabet_map.csv` como `order-unmapped`, mesma disposição dos
`PBEKeySpecSpec.f1`/`f2` e pela mesma razão. Sem essa linha o G-ORDER **pulava** o
`SSLContextSpec` inteiro — e pular não é passar.

## 9.1 — o medido

O pointcut declarava `call(public void SSLContext.createSSLEngine(..))` onde o android-30 declara
`public final SSLEngine createSSLEngine()`. Os dois tecelões filtram o tipo de retorno exatamente:
o advice era gerado, ficava no monitor e **nunca disparou**. A varredura de assinaturas dos 143
sítios `call(...)` do conjunto achou este como o **único** mismatch de tipo de retorno.

```
pair-901: 172 traces  {"unchanged": 171, "moved": 1}
```

| trace | A (pós-9.9) | B (pós-9.1) |
|---|---|---|
| `SSLContextSpec-getdefault-engine.txt` | `getDefault:SSLCONTEXT-FORB-00` | **`engine:SSLCONTEXT-ORDER-00`**, `getDefault:SSLCONTEXT-FORB-00` |

**O delta observável da 9.1 sobre os 172 traces é essa única linha** — e ela é o resíduo declarado,
sobre um programa que os dois oráculos já condenam pela chamada anterior.

O que não se move é a prova de que a ordem das tarefas estava certa. `SSLContextSpec.txt` — o
programa legítimo `getInstance("TLSv1.2"); init(...); createSSLEngine()` — vem **`unchanged`**: o
evento revivido chega em `end`, é auto-laço, e o único efeito é a escrita de bookkeeping do
`@match1` (`GENERATE_SSL_ENGINE`, sem leitor, INV-INS-137). E os traces das outras duas origens de
`SSLContext` sem monitor, que a 9.1 acusaria por engano, também vêm `unchanged` — porque a 9.16 e a
9.17 já as fecharam nos pares anteriores. Aprovar a 9.1 antes delas teria comprado falso positivo
em duas populações que nada têm com o defeito que ela repara.

`createSSLEngine()` antes do `init` não alcança nada: lança `IllegalStateException`, e um advice
`after returning` não roda num throw. O caminho `s1 -> fail` fica como o autômato lê a regra.

## Os dois gates que estavam vermelhos aqui fecharam

Antes deste bloco, sobre o universo dos cinco conjuntos:

```
G-SIG:  416 checked, 1 failed    <- o único achado era a 9.1
G-FORB:  18 checked, 2 failed    <- os dois achados eram a 9.9, um por oráculo
```

Depois:

```
G-SIG:  418 checked, 0 failed, 7 allow-listed,  7 skipped, 16 notes
G-FORB:  18 checked, 0 failed, 12 allow-listed, 14 skipped, 0 notes
```

Nenhum adiamento precisou de linha de `gate_allowlist.csv`, que era a outra saída honesta.

## O que continua aceito do registro e não reproduzido

As duas afirmações sobre o portão de tipo de retorno no caminho do tecelão DEX
(`conformance_record.csv:62,:73`) continuam **aceitas do registro**. Nada aqui foi rodado em
emulador nem tecido num APK: o monitor é compilado e exercitado pelo TraceRunner com o classpath
JSE do arnês. O que o G-SIG prova é que a assinatura do pointcut agora bate com o `android.jar`;
não prova o que o tecelão faz com ela.
