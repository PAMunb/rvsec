# Tarefas 5.2 e 5.3 — a cadeia do Mac, e as três cláusulas que o oráculo não fecha

**Data**: 2026-08-22 · **Lote**: B1, o primeiro do Grupo 5 a fechar duas tarefas num commit
**Arquivo editado**: um só — `rvsec/rvsec-mop/src/main/resources/jca_android/MacSpec.mop`
**Cláusulas**: ledger #21 (5.2), #22 e #23 (5.3)
**Resultado em uma linha**: das três cláusulas, **uma é fiada e duas são registradas** — e a que
é fiada exigiu reparar um evento que acusava todo programa que passasse por ele.

---

## O que as tarefas pediram, e o que a árvore respondeu

A 5.2 pediu para fiar `preparedHMAC[params]`. A 5.3 pediu para fiar `!encrypted[output1, _]` e
`!encrypted[output2, _]` por `validateAbsent`. As três cláusulas eram wireable no ledger: o
consumidor e o produtor têm `.mop` no conjunto.

Ter `.mop` dos dois lados não é o mesmo que a plataforma admitir a composição. Três medições
mudaram a disposição de duas das três cláusulas, e uma quarta mudou o que a terceira custa.

| medição | resultado |
|---|---|
| `javax/xml/crypto` no `android.jar` do api30 | **zero entradas**; `javax/crypto/Mac` e `javax/crypto/spec/PBEParameterSpec` estão lá |
| `Mac.init(key, params)` sobre os 12 algoritmos do allow-list da própria regra (Temurin 21) | nenhum aceita `HMACParameterSpec`; os seis `Hmac*` recusam qualquer params, os cinco `PBEwithHmac*` só aceitam `PBEParameterSpec`, e `PBEwithHmacSHA` não existe |
| identidade do array devolvido por `Mac.doFinal()` / `doFinal(byte[])` | array novo em toda chamada; nunca o objeto do texto cifrado |
| `MacSpec.f2` nas três traces novas, nos três snapshots | **acusa `MAC-ORDER-00` em todas**, inclusive na conforme |

---

## #21 — `preparedHMAC[params]`: registrada, não lida

O produtor é `HMACParameterSpec.cryptsl:21 preparedHMAC[this]`, realizado por
`HMACParameterSpecSpec.mop:35` no ponto de aceitação desde a 4.14. O consumidor seria
`MacSpec.i2` (`MacSpec.mop:106` na pré-imagem), que liga `params` diretamente — **há sítio**, e a
pergunta que a 5.1 teve de responder com um arquivo novo não se repete aqui.

O que não há é programa.

A classe produtora é `javax.xml.crypto.dsig.spec.HMACParameterSpec`, do módulo `java.xml.crypto`
— XML-DSig, não JCA. O `android.jar` do api30, que é o nível contra o qual as regras deste
conjunto são geradas, **não tem entrada nenhuma sob `javax/xml/crypto`**. Na plataforma que o
conjunto mira, o construtor que o `HMACParameterSpecSpec` casa não pode existir em aplicação
nenhuma.

Na JVM, onde a classe existe, nenhum `Mac` a aceita. Medido, não deduzido, sobre os doze
algoritmos que a própria `Mac.cryptsl:71` declara:

```
HmacSHA1 · HmacSHA224 · HmacSHA256 · HmacSHA384 · HmacSHA512 · HmacMD5
   init(key, <qualquer params>) -> InvalidAlgorithmParameterException: HMAC does not use parameters
PBEwithHmacSHA1 · ...SHA224 · ...SHA256 · ...SHA384 · ...SHA512
   init(key, HMACParameterSpec) -> InvalidAlgorithmParameterException: PBEParameterSpec type required
   init(key, PBEParameterSpec)  -> ok
PBEwithHmacSHA
   getInstance -> NoSuchAlgorithmException          (está no allow-list da regra e não existe)
```

E o `i2` é `after`, que é *after finally*: dispara também na chamada que lança. O único programa
que poderia chegar a uma leitura com o predicado presente é um que levanta
`InvalidAlgorithmParameterException` naquela mesma linha — o programa "conforme" seria um que
quebra.

Escrever a leitura acusaria `NOT_OBSERVED` em todo `init` de dois argumentos conforme que existe.
É a forma exata dos dezessete acusadores órfãos que o Grupo 3 removeu. **Registrada** (decisão 53),
com a razão no `predicate_graph.csv` sobre a linha do produtor, em `disposition=omission` — que é
como a linha G-PRED2 dela fecha sem leitor.

Achado maior, registrado no `conformance_record.csv` e não reparado: **o
`HMACParameterSpecSpec.mop` instrumenta uma classe ausente do Android.** Uma das 24 especificações
do conjunto não pode disparar em APK nenhum. Se ela deve sair do conjunto é mudança de escopo, e
não se decide aqui.

---

## #23, e a metade retornada da #22: registradas vacuosas

O alfabeto do `.mop` não corresponde ao da regra pelos nomes, e isso decide as duas cláusulas.

| evento da regra | evento do `.mop` | o que o `byte[]` é |
|---|---|---|
| `f1: output1 = doFinal()` | `f1` (`returning`) | array que a chamada devolve |
| `f2: output2 = doFinal(input)` | `f1` também — o `\|\|` do pointcut funde os dois | array que a chamada devolve |
| `f3: doFinal(output1, outOffset)` | **`f2`** (`args(output, outOffset)`) | **buffer do chamador** |

A JCA aloca o array devolvido a cada chamada. Medido sobre HmacSHA1, HmacSHA256 e HmacSHA512: o
array devolvido nunca é o mesmo objeto que um texto cifrado produzido ao lado. Como
`validateAbsent` **nunca** devolve `NOT_OBSERVED` — ausência é conformidade para cláusula negada —
uma leitura no `MacSpec.f1` só poderia responder `SATISFIED`. Seria sítio sem caminho até
acusação, que a decisão 19 apaga em vez de escrever.

`output2` só aparece no `f2` da regra, que é retorno. A #23 **não tem outro sítio** e é registrada
vacuosa por inteiro. A #22 tem o segundo sítio, abaixo (decisão 54).

---

## #22 — fiada, e o acusador falso que o reparo calou

`MacSpec.f2` traduz o `f3` da regra, o único evento cujo `byte[]` pertence ao chamador. Um
programa que entrega o seu texto cifrado a essa chamada destrói os bytes que pretende autenticar
e autentica o que eles eram. É a cláusula.

O sítio não casava. O evento declarava `target(m)` **sem nomear `m` entre os formais** — a
transmissão de ligação vazia registrada em `conformance_record.csv:67` item (c). O gerador dá a um
evento assim o mapa sem parâmetro da especificação, e ele cai num monitor raiz que não viu
`getInstance` nem `init`, que o `ere` rejeita.

Medido nas três traces novas, contra a pré-imagem, esta árvore e o controle congelado:

| trace | pré-imagem | árvore editada | controle congelado |
|---|---|---|---|
| `MacSpec-encrypted-buffer.txt` (viola) | `MAC-ORDER-00` em `f2` | **`MAC-CONSTR-00` em `f2`** | `MAC-ORDER-00` em `f2` |
| `MacSpec-fresh-buffer.txt` (conforme) | `MAC-ORDER-00` em `f2` | **silêncio** | `MAC-ORDER-00` em `f2` |
| `MacSpec-decrypt-buffer.txt` (custo) | `MAC-ORDER-00` em `f2` | `MAC-CONSTR-00` em `f2` | `MAC-ORDER-00` em `f2` |

`unresolved: []` nas três, nos três snapshots.

A linha da conforme é o resultado: **o evento acusava todo programa que passasse por ele**, e o
reparo o calou. No monitor gerado, `MacSpec__Map` — o mapa sem parâmetro — **desapareceu inteiro**,
e `MacSpec_f2Event` passou a receber `Mac m`.

O reparo viaja com a cláusula (decisão 55), como o da 6.2 viaja com a 5.9: sem ele a leitura não
tem objeto que ler, e a acusação que ela produz não se distinguiria do relato de ordenação
espúrio que já estava lá. **Nenhuma das 104 traces existentes alcança este evento** — só as três
novas chamam `doFinal(byte[], int)` — então o reparo não move nada já medido.

---

## O custo, por inteiro

`Cipher.cryptsl` enuncia `encrypted[cipherText, plainText]` **sem guarda sobre `encmode`**. Um
`Cipher` inicializado para decifrar que chegue ao estado de aceitação marca a saída dele do mesmo
modo que um que cifra. Um `Mac` que escreva a tag nesse buffer é acusado, embora o buffer tenha o
texto claro e nenhum texto cifrado tenha sido destruído.

A imprecisão é do oráculo, não deste conjunto: o `CipherSpec.@match1` traduz a cláusula como a
regra a enuncia. `MacSpec-decrypt-buffer.txt` é a testemunha, para que o relatório tenha medição
e não alegação.

Registrado e não reparado, na mesma linha: a regra tem uma terceira cláusula,
`encrypted[cipherBuffer, plainBuffer]`, sobre a forma de `doFinal` que escreve num buffer do
chamador. Um `Mac` que escreva sobre *esse* buffer não seria acusado.

---

## O harness diferencial

Contra `backup/gh105-preimage/jca_android`, cumulativo, 107 traces:

| classe | antes (104) | agora (107) |
|---|---|---|
| `unchanged` | 67 | **67** |
| `moved` | 21 | **23** |
| `introduced` | 9 | **9** |
| `removed` | 7 | **8** |

As três traces novas respondem por toda a diferença: duas `moved` (a violadora e a de custo, que
trocam `MAC-ORDER-00` por `MAC-CONSTR-00`) e uma `removed` (a conforme, que fica em silêncio).

E a asserção mais forte:

```
$ git diff --stat -- data/gh105/evidence/harness/
 rv-android/data/gh105/evidence/harness/f2-MacSpec.md | ...
 1 file changed
```

**Um só relatório mudou**, e é o da especificação editada. Nenhum dos outros 23 se moveu.

---

## Os portões

| portão | antes | agora |
|---|---|---|
| G-PRED2 | 9 | **6** |
| `structural_findings` na baseline | 9 | **6** |
| linhas no `predicate_graph.csv` | 46 | **47** |
| `read` + `read-absent` no censo | 15 | **16** |
| `polarity=negated` | 0 | **1** |
| `verdict=read-absent:body` | 0 | **1** |
| traces do corpus | 104 | **107** |
| linhas no `codes.csv` | 71 | **72** |

As três linhas G-PRED2 que fecharam:

```
[G-PRED2] repaired jca_android/CipherSpec.mop match1/ENCRYPTED
[G-PRED2] repaired jca_android/CipherSpec.mop match2/ENCRYPTED
[G-PRED2] repaired jca_android/HMACParameterSpecSpec.mop match/PREPARED_HMAC
```

As duas primeiras porque `ENCRYPTED` ganhou leitor; a terceira porque `PREPARED_HMAC` ganhou
registro de omissão deliberada. **Duas cláusulas registradas fecham uma linha de portão que
nenhuma leitura fecharia** — é o mecanismo D-13 fazendo o que foi desenhado para fazer.

`MacSpec` não ganha linha no `order_alphabet_map.csv`: o alfabeto não se move, e o arquivo é um
dos treze que a 7.1 ainda deve mapear, então o G-ORDER o pula declaradamente nas duas direções.

---

## Registro de divergência

Dez entradas do `MacSpec` ficaram `stale` e sete hunks novos entraram, absorvendo as razões das
dez. O `b88fa244dfc3` (n=20) fundiu o corpo do `f2` com o bloco de comentário acima do `ere`, que
é por que a linha daquele bloco ficou `stale` sem que o bloco tenha mudado. CRLF preservado, 281
terminadores, nenhum LF solto; anexadas ao fim, sem reordenar.

`275 hunk(s), all recorded; 5 narrative entr(ies)`.

---

## Achados sobre o instrumento

1. **Uma cláusula pode ter os dois lados no conjunto e nenhum programa que os componha.** O
   ledger classifica por "existe `.mop` dos dois lados", que é condição necessária e não
   suficiente. As categorias `unmonitored-*`, `vacuous` e `unclosable` não cobriam este caso:
   produtor e consumidor existem, e é a **plataforma** que recusa. Quem escrever a 5.4 a 5.10
   deve medir a composição, não só a existência dos dois lados.
2. **Um evento sem o formal que o seu `target(...)` nomeia acusa tudo o que passa por ele.**
   Não é só um evento mudo: é um acusador falso. O `conformance_record.csv:67` registrava o
   defeito de forma; o que faltava era a medição do efeito. Restam três sítios da mesma família
   no conjunto — `PBEKeySpecSpec.f1/f2`, `SSLContextSpec.unsafe_protocol` e
   `TrustManagerFactorySpec.g3/gtm1` — e nenhum deles foi medido assim.
3. **Nome de evento no `.mop` não é nome de evento na regra.** O `f2` do `MacSpec` é o `f3` da
   `Mac.cryptsl`, e o `f1` do `.mop` é o `f1` **e** o `f2` da regra fundidos. Mapear evento a
   evento antes de decidir onde a cláusula vai; os nomes coincidem o bastante para enganar.
4. **`bind x = <chamada>` aceita método `void`** (`ks.load(null)` no corpus), que é como uma
   trace faz o objeto real existir sem despachar advice. E uma linha com `->` **executa**: foi
   preciso para que o mesmo array fluísse do `Cipher` ao `Mac`. São as primeiras traces do corpus
   com `->` num `doFinal`.
5. **O achado 4 me pegou.** A primeira versão da trace de decrypt decifrava zeros direto e
   lançava `BadPaddingException`; o `produce()` caiu no fallback, o array chegou nulo,
   `validateAbsent(…, null)` respondeu `SATISFIED` e a trace não acusou nada — passando por
   "conforme". Uma trace tem de descrever um programa que **roda**, e os tamanhos são
   carga: 32 bytes de texto claro cifram para 48, decifram para 32, e a tag do HmacSHA256 tem 32.

---

## Recontagem dos censos que as tarefas afirmam

- `tasks.md:446` afirma que o G-PRED2 tem **"its ten rows"**. A `gate_baseline.json` e o gate
  diziam **nove** antes desta passagem. Corrigido pela skill junto com a marcação.
- O enunciado da 5.2 chama as leituras que a 4.9 apagou de *"propagation reads"* — rótulo que a
  própria evidência da 4.9 (`f2-MacSpec.md`) já havia corrigido — e diz que elas são
  *"re-derived here"*, o que sugere restauração. Nada foi restaurado: a leitura desta passagem é
  de outro predicado, em outro evento, sobre outro objeto.
- O enunciado da 5.2 confirma-se num ponto: **`Mac` não requer `generatedKey`**. Conferido em
  `Mac.cryptsl` — não aparece em REQUIRES, CONSTRAINTS nem ENSURES.

---

## Arquivos

**Editados**
- `rvsec/rvsec-mop/src/main/resources/jca_android/MacSpec.mop` (+3 imports, o registro da #21 no
  `i2`, o registro vacuoso no `f1`, o reparo do binding e a leitura no `f2`)
- `rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv` (+`MAC-CONSTR-00`; as três âncoras
  antigas reconferidas contra a árvore)
- `data/jca_android/predicate_graph.csv` (+1 linha; `disposition=omission` na linha do produtor)
- `data/jca_android/divergence_record.csv` (−10 `stale`, +7)
- `data/jca_android/conformance_record.csv` (+1 linha; a linha (c) diz que o `MacSpec.f2` saiu)
- `data/jca_android/gate_baseline.json` + `data/jca_android/evidence/gate_baseline_report.md`
- `tests/parity/test_gh105_predicate_gates.py` (um censo movido, uma asserção nova)

**Novos**
- `data/gh104/traces/MacSpec-encrypted-buffer.txt`
- `data/gh104/traces/MacSpec-fresh-buffer.txt`
- `data/gh104/traces/MacSpec-decrypt-buffer.txt`
- este arquivo

---

## O que fica para o resto do Grupo 5

- **A #8 (`!macced`, tarefa 5.7) herda o mapeamento de alfabeto medido aqui.** O produtor
  `MACED` que ela tem de criar vai sobre a tag e o dado autenticado, aridade 2, e o `MacSpec.f1`
  é o evento que liga a tag — mas ele funde dois eventos da regra, e a `args(input)` que a
  cláusula `macced[output1, pre_input]` precisa **não está ligada** no `f1` de hoje.
- **A 5.4 e a 5.8 devem medir a composição, não a existência.** O achado 1 acima.
- **Três sítios de ligação vazia continuam no conjunto** e nenhum foi medido como acusador. O
  achado 2 acima; o reparo é da 6.2 para um deles.
- **A 5.11 encontra o G-PRED2 em 6**, e duas das que fecharam aqui fecharam por registro, não
  por leitura.
