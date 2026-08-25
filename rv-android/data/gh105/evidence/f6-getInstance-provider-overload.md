# Tarefa 9.16 — a sobrecarga `getInstance(String, Provider)` que cinco specs não viam

**Data**: 2026-08-25 · **Decisão**: GO (pesquisador, 25/08), sequenciada após a 9.14
**Par**: `A = pós-9.14` · `B = A + 9.16` · `~/tmp-gh104/g9b/pair-916.json`

## O reparo

O android-30 declara `getInstance(String, Provider)` nas cinco classes, e nenhuma das cinco specs
tinha pointcut para ela. Um objeto obtido por essa sobrecarga chegava ao evento seguinte com o
monitor em **estado 0**, onde toda linha é `fail` — lido no monitor regenerado: `Signature i1[0]=8`,
`Mac i1[0]=4`, `KeyStore load[0]=5`, `KeyPairGenerator init1[0]=4`, `SSLContext init[0]=3`.

Em **quatro dos cinco** o reparo alarga o pointcut de dois argumentos e **não cria evento**:

```
call(public static X X.getInstance(String, String))  →  call(public static X X.getInstance(String, Object+))
event g2 after(String alg, String provider)          →  event g2 after(String alg, Object provider)
```

Só o `KeyStoreSpec` não tinha nenhuma forma de 2 argumentos e leva um evento novo, `g3` — o arquivo
vai de 7 para 8 dos 17 que o teto permite. Ele carrega a guarda do `g1` (não a do `g2`, negada) e
entra no `ere` como alternativa: `(g2* (g1 | g3) load (...)*)+`. É a forma que o `KeyGeneratorSpec`
já tem — lá o gêmeo negado `g3` é declarado só sobre a forma de um argumento.

### `Object+`, não `..`

O resolvedor do arnês de traces percorre os tipos declarados da assinatura do `call(...)` e **para
no primeiro curinga** (`KeyManagerFactorySpec.mop:87-90`): um `..` faria todo `getInstance` caber
neste pointcut. `Object+` mantém a aridade conhecida e a segunda posição tipada. O precedente é o
`KeyGeneratorSpec.g2`, que lê a sobrecarga assim desde a task 2.4. E o oráculo concorda com a
forma: o expert escreve `g2: getInstance(protocol, _)`.

Conferido no `javap` do android-30 que o `KeyStore` tem as duas formas de dois argumentos; as
outras duas sobrecargas (`getInstance(File, char[])` e `getInstance(File, KeyStore$LoadStoreParameter)`)
abrem sobre um arquivo, são um `Gets` que a regra não nomeia, e não cabem num pointcut cuja
primeira posição é declarada `String`.

## O medido

O corpus não conseguia sequer expressar o caso: os argumentos de um trace são literais de string,
inteiros, `null`, nomes ligados ou os marcadores de array. Um `Provider` **é** expressável, por um
`bind` sobre um método estático qualquer — `bind p = Security.getProvider("SunJSSE")` —, e é assim
que os dois traces novos foram escritos.

```
pair-916: 172 traces  {"unchanged": 170, "removed": 1, "moved": 1}
```

| trace | A | B |
|---|---|---|
| `KeyStoreSpec-provider-object.txt` | `load:KEYSTORE-ORDER-00` | *(nada)* |
| `SSLContextSpec-provider-object.txt` | `init:NOBS-00`, `init:NOBS-01`, **`init:SSLCONTEXT-ORDER-00`** | `init:NOBS-00`, `init:NOBS-01` |

Nos dois casos o programa é conforme e era acusado de sequência errada. As duas linhas `NOBS` do
segundo trace são sobre os arrays de manager nulos e não se movem — elas isolam o delta.

## Massa e precondição

A fatia do `KeyStoreSpec` é a mesma massa da 9.14: **10.660 linhas sobre 22 apps**
(`conformance_record.csv` itens (a) e (g)), teto e não atribuição causal.

Este reparo é a segunda precondição da 9.1: fecha a origem `getInstance(String, Provider)`, que era
uma das três maneiras de um `SSLContext` chegar vivo sem monitor — exatamente a população que a
9.1, ao reviver o `engine`, acusaria por engano.
