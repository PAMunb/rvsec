# Segunda passada de auditoria — agente A
Ponto de medição: reator rvsec em `bd61abea` (confirmado por `git rev-parse HEAD`).
Data: 2026-08-20.

## Item 1 — Enum `Property` tem 25 valores — SUSTENTADO
Leitura integral de `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java`. Constantes:
GENERATED_KEY, DIGESTED, ENCRYPTED, GENERATED_CIPHER, GENERATED_MAC, MACED, GENERATED_PRIVATE_KEY,
GENERATED_PUBLIC_KEY, GENERATE_SSL_CONTEXT, GENERATE_SSL_ENGINE, GENERATED_KEY_MANAGERS,
GENERATED_KEY_PAIR, GENERATED_TRUST_MANAGER, GENERATED_TRUST_MANAGERS, GENERATED_KEY_STORE,
PREPARED_DH, PREPARED_GCM, PREPARED_HMAC, PREPARED_PBE, PREPARED_IV, RANDOMIZED, SIGNED,
SPECCED_KEY, VERIFIED, WRAPPED_KEY = **25**. A correção da auditoria (24→25) está certa.

## Item 2 — Distribuição em jca_android — SUSTENTADO
Comando: `grep -ho '<call>(Property\.[A-Z_]*' *.mop | sed 's/.*Property\.//' | sort | uniq -c`
em `rvsec/rvsec-mop/src/main/resources/jca_android/`.

| Property | setProperty | validate | remove |
|---|---:|---:|---:|
| DIGESTED | 3 | — | — |
| ENCRYPTED | 11 | — | — |
| GENERATED_KEY | 3 | 4 | 2 |
| GENERATED_KEY_MANAGERS | 3 | — | 1 |
| GENERATED_KEY_PAIR | 1 | — | 1 |
| GENERATED_KEY_STORE | 1 | — | 1 |
| GENERATED_MAC | 2 | — | 1 |
| GENERATED_PRIVATE_KEY | — | 1 | — |
| GENERATED_PUBLIC_KEY | 2 | 1 | — |
| GENERATED_TRUST_MANAGER | 1 | — | 1 |
| GENERATED_TRUST_MANAGERS | — | — | 1 |
| GENERATE_SSL_CONTEXT | 1 | — | — |
| GENERATE_SSL_ENGINE | 1 | — | — |
| PREPARED_DH | 1 | — | — |
| PREPARED_GCM | 1 | — | — |
| PREPARED_HMAC | 1 | — | — |
| PREPARED_IV | 1 | — | — |
| PREPARED_PBE | 1 | — | — |
| RANDOMIZED | 9 | 21 | — |
| SIGNED | 2 | — | — |
| SPECCED_KEY | 1 | — | 1 |
| VERIFIED | 2 | — | — |
| WRAPPED_KEY | 1 | — | — |
| **Total** | **49** | **27** | **9** |

Valores escritos: 21 (em 49 sítios). Valores lidos: 4 (RANDOMIZED 21, GENERATED_KEY 4,
GENERATED_PUBLIC_KEY 1, GENERATED_PRIVATE_KEY 1). Tudo idêntico à auditoria.

## Item 3 — Escritas sem consumidor: 18 valores, 35 sítios — SUSTENTADO
Conjunto escrito (21) − conjunto lido presente nas escritas ({GENERATED_KEY, GENERATED_PUBLIC_KEY,
RANDOMIZED}; GENERATED_PRIVATE_KEY é lido mas nunca escrito, não subtrai) = **18 valores**:
DIGESTED(3), ENCRYPTED(11), GENERATED_KEY_MANAGERS(3), GENERATED_KEY_PAIR(1),
GENERATED_KEY_STORE(1), GENERATED_MAC(2), GENERATED_TRUST_MANAGER(1), GENERATE_SSL_CONTEXT(1),
GENERATE_SSL_ENGINE(1), PREPARED_DH(1), PREPARED_GCM(1), PREPARED_HMAC(1), PREPARED_IV(1),
PREPARED_PBE(1), SIGNED(2), SPECCED_KEY(1), VERIFIED(2), WRAPPED_KEY(1).
Soma dos sítios = **35** = 49 − (9+3+2) por RANDOMIZED/GENERATED_KEY/GENERATED_PUBLIC_KEY.

## Item 4 — Zero sítios: exatamente MACED e GENERATED_CIPHER — SUSTENTADO
`grep -ho 'Property\.[A-Z_]*' jca_android/*.mop | sort | uniq -c` lista 23 dos 25 valores.
Ausentes em qualquer contexto (inclusive comentários): **MACED** e **GENERATED_CIPHER**.
`GENERATED_TRUST_MANAGERS` tem exatamente 1 sítio — `TrustManagerFactorySpec.mop:101`,
`remove(Property.GENERATED_TRUST_MANAGERS)` (sobrecarga de 1 argumento) — logo a refutação
da alegação do plano está correta.

## Item 5 — Censo das 134 linhas de ExecutionContext — SUSTENTADO (com nota sobre 42+7)
`grep -c "ExecutionContext" jca_android/*.mop | awk -F: '{s+=$2} END {print s}'` = **134**.
Decomposição medida vs README (`rv-android/data/jca_android/README.md`):

| categoria | README | medido |
|---|---:|---:|
| linhas `import` | 23 | 23 |
| linhas `validate(` | 27 | 27 |
| linhas `setProperty(` | 49 | 49 |
| linhas `remove(` | 9 | 9 |
| chamadas de estado de aceitação | 25 | 25 (19 `setObjectAsInAcceptingState` + 6 `unsetObjectAsInAcceptingState`) |
| comentário | 1 | 1 |
| **soma** | **134** | **134** |

Sobre 42+7=49: não há diferença entre ocorrências e linhas (49 ocorrências de `setProperty(` em
49 linhas; nenhuma linha tem duas chamadas). O 42/7 da auditoria é OUTRA partição dos mesmos 49
sítios: **42 em corpo de evento, 7 dentro de handler `@match`** (classificador por último marcador
`event`/`@match`/`@fail` precedente; nenhuma escrita em `@fail`). Confirmado: 42 [body] + 7 [match].
Nota menor: o comentário citado pelo README como `MessageDigestSpec.mop:25` está na linha 25 do
**seed `jca`** (o README fala do seed, correto) e na linha 37 do arquivo de `jca_android`.

## Item 6 — Sem deriva bd61abea ↔ d27c48e9 — SUSTENTADO
`git grep -ho '<call>(Property\.[A-Z_]*' <rev> -- 'rvsec/rvsec-mop/src/main/resources/jca_android/*.mop'`
para as três chamadas nas duas revisões; `diff` das distribuições ordenadas: **IDENTICO** para
setProperty, validate e remove, valor a valor.

## Item 7 — Oráculo api30: 33 regras, 54/36/2 cláusulas, 32 predicados — SUSTENTADO
Metodologia: parser por seções (cabeçalhos SPEC/OBJECTS/EVENTS/ORDER/CONSTRAINTS/FORBIDDEN/
REQUIRES/ENSURES/NEGATES em linha própria); dentro de ENSURES/REQUIRES/NEGATES o texto é
concatenado e dividido em cláusulas por `;`, cada cláusula devendo conter `pred[...]` (cláusulas
com guarda `... => pred[...]` contam uma vez, pelo predicado do lado direito). Verificação cruzada
por método independente (awk, linhas contendo `[` dentro da seção): mesmos números.
- Arquivos `.cryptsl`: **33**. Cláusulas: **ENSURES 54, REQUIRES 36, NEGATES 2**.
- Predicados distintos (E+R+N, e também só E+R): **32**.

## Item 8 — Aridade 59/29/2 — REFINADO
Aritmética: 59+29+2 = 90 = 54 ENSURES + 36 REQUIRES (NEGATES fora — as 2 cláusulas NEGATES são
binárias e não entram nas 90). Isso confere.
Porém a partição 29 binárias + 2 quaternárias é um **artefato de contagem ingênua de vírgulas**:
as duas "quaternárias" são `Cipher.cryptsl:174 generatedKey[key, part(0,"/",transformation)]` e
`Cipher.cryptsl:178 preparedAlg[param, part(0,"/",transformation)]`, onde `part(i,sep,var)` é um
único parâmetro CrySL (objeto com splitter); contando vírgulas de nível superior (fora de
parênteses) a distribuição estrutural é **59 unárias, 31 binárias, 0 quaternárias**, e a aridade
máxima estrutural é **2** — a linha "aridade máxima (generatedKey) 4 — CONFIRMADO" da auditoria
não se sustenta estruturalmente (todas as 6 cláusulas `generatedKey[...]` do api30 são binárias).
O que sobrevive intacto: a conclusão substantiva da auditoria — "31 das 90 cláusulas precisam de
aridade ≥ 2" — e o REFUTADO de "a maioria binários" (a maioria é unária em ambas as contagens).

## Item 9 — 19 conectáveis / 35 pares / 44 arestas — REFINADO (34 pares distintos; 35 como sítios-cláusula)
Definições da auditoria (§1, "As quatro correções"): predicados exigidos por alguma regra = 20;
`preparedEC` não tem produtor ⇒ **19 predicados conectáveis** — CONFIRMADO (medido: 20 exigidos,
só `preparedEC` sem ENSURES em regra alguma; único sítio: `KeyPairGenerator.cryptsl`,
`alg in {"EC"} => preparedEC[params]`).
**Arestas** regra-produtora→regra-consumidora (por predicado, conjuntos): Σ |produtores(p)| ×
|consumidores(p)| = **44** — CONFIRMADO.
**Pares (predicado, regra-consumidora)**: distintos são **34**, não 35. A diferença é
`Mac.cryptsl`, que exige `encrypted` em DUAS cláusulas (`!encrypted[output1,_]` e
`!encrypted[output2,_]`) — mesmo par, dois sítios. Contando **cláusulas REQUIRES cujo predicado é
conectável** dá exatamente **35** (36 cláusulas − 1 de `preparedEC`). Para dimensionar F3 o número
35 continua defensável — cada cláusula é uma obrigação de fiação distinta (variáveis diferentes) —
mas o rótulo correto é "sítios-cláusula consumidores", não "pares (predicado, regra)".

## Item 10 — NEGATES: 2 cláusulas; no máximo 1 dos 9 remove() corresponde — SUSTENTADO
As 2 cláusulas NEGATES do oráculo:
- `SecretKey.cryptsl:30` — `generatedKey[this, _] after d;` (d = destroy())
- `PBEKeySpec.cryptsl` — `speccedKey[this, _] after cP;` (cP = clearPassword())

Os 9 sítios de `remove()` em jca_android, com contexto:
| sítio | Property | contexto | contraparte NEGATES? |
|---|---|---|---|
| MacSpec.mop:99 | GENERATED_MAC (1 arg, @Deprecated) | @fail | não |
| KeyGeneratorSpec.mop:89 | GENERATED_KEY | @fail | não (NEGATES de generatedKey é after destroy, e nenhuma spec tem evento destroy) |
| KeyManagerFactorySpec.mop:104 | GENERATED_KEY_MANAGERS (1 arg) | @fail | não |
| KeyPairGeneratorSpec.mop:119 | GENERATED_KEY_PAIR | @fail | não |
| PBEKeySpecSpec.mop:74 | SPECCED_KEY, s | **corpo do evento c2 = clearPassword()** | **SIM — speccedKey after cP** |
| KeyStoreSpec.mop:92 | GENERATED_KEY | @fail | não |
| KeyStoreSpec.mop:93 | GENERATED_KEY_STORE | @fail | não |
| TrustManagerFactorySpec.mop:100 | GENERATED_TRUST_MANAGER (1 arg) | @fail | não |
| TrustManagerFactorySpec.mop:101 | GENERATED_TRUST_MANAGERS (1 arg) | @fail | não |

8 em `@fail` + 1 em corpo; exatamente **1** correspondência (PBEKeySpecSpec.mop:74). `grep destroy
jca_android/*.mop` vazio confirma que o NEGATES do SecretKey não tem contraparte. Os 4 usos da
sobrecarga de 1 argumento (@Deprecated, apaga para o processo) também conferem.
