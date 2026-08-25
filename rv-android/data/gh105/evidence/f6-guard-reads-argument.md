# Tarefa 9.4 — as duas guardas negadas que liam o campo em vez do argumento

**Data**: 2026-08-25 · **Commit da árvore**: `70877f67`
**A** `~/tmp-gh104/g9impl/B3` · **B** `rvsec/rvsec-mop/src/main/resources/jca_android` ·
**corpus** `data/gh104/traces` (159)

## 1. O reparo

| arquivo | antes | depois |
|---|---|---|
| `KeyGeneratorSpec.mop` | `condition(!matches("KeyGenerator", currentAlgorithmInstance, safeAlgorithms))` | `... , alg, ...)` |
| `MessageDigestSpec.mop` | `condition(!matches("MessageDigest", currentAlgorithmInstance, algorithms))` | `... , alg, ...)` |

Eram as duas únicas das **oito** guardas `condition(!...)` do conjunto que liam o campo do
monitor em vez do argumento ligado. As outras seis já liam o argumento: `KeyStoreSpec:63`
(`ksType`), `MacSpec:81`, `KeyManagerFactorySpec:64`, `KeyPairGeneratorSpec:77`,
`SecureRandomSpec:135` e `CipherSpec:100` (sobre `transformation`). Depois do reparo, as oito
leem o argumento.

## 2. Por que estava correto, e por que isso não bastava

O campo nasce `""` e só o gêmeo positivo `g1`/`g2` o escreve, quando o algoritmo é admitido.
Num monitor novo a guarda negada valia — **mas só porque** o aspecto gerado emite `g1Event`
antes de `g3Event`/`g4Event` no pointcut compartilhado
(`MultiSpec_1MonitorAspect.aj:366-371`, `:524-529`), e **nada na árvore assere essa ordem**:
grep por asserções sobre ela em `scripts/` e `tests/` volta vazio.

A hipótese de falso negativo histórico foi retirada e a retirada está certa: o monitor é por
objeto, os g-eventos são de criação e ocorrem uma vez por binding, e para a guarda errar seria
preciso um monitor com campo seguro recebendo `alg` inseguro — o que exigiria dois
`getInstance` devolvendo o mesmo objeto. Não há achado maior escondido aqui.

## 3. Os dois gêmeos não correm o mesmo risco

- **`MessageDigestSpec.g4` acusa no corpo** (`MESSAGEDIGEST-ALG-02`). Se a ordem de despacho
  invertesse, todo `MessageDigest.getInstance(String)` **seguro** seria reportado com o
  envelope autocontraditório `expecting one of SHA-256,... but found SHA-256` — a assinatura
  `but found .` que a task 8.16 reparou nas guardas `if` dos corpos e que não alcançou dentro
  de uma cláusula `condition()`.
- **`KeyGeneratorSpec.g3` não emite envelope algum**: o corpo só rebinda o campo, e a acusação
  mora a jusante, em `gk1` (`:156-160`). A inversão ali seria **silenciosa no autômato**. Por
  isso esta metade do par é higiene contra uma dependência latente, não reparo de um relatório
  observado. A tarefa dizia "the envelope they emit reports the argument `alg`" para os dois;
  vale só para o MessageDigest, e o texto foi corrigido antes da implementação.

## 4. O arnês

```
A=g9impl/B3  B=árvore   →   {"unchanged": 159}
```

Os 18 traces de `KeyGeneratorSpec` e `MessageDigestSpec` — incluindo os `*-guard-on-field.txt`
e todos os `*-d15-*` — com listas de sítios **idênticas evento a evento**. Amostra:

| trace | A e B |
|---|---|
| `KeyGeneratorSpec-d15-desede.txt` | `gk1:KEYGENERATOR-ALG-00`, `gk1:KEYGENERATOR-ORDER-00`, `init:KEYGENERATOR-ORDER-00` |
| `KeyGeneratorSpec-guard-on-field.txt` | `gk1:KEYGENERATOR-ORDER-00`, `init:KEYGENERATOR-ORDER-00` |
| `MessageDigestSpec-d15-sha1.txt` | `d1:MESSAGEDIGEST-ORDER-00`, `g4:MESSAGEDIGEST-ALG-02`, `update:MESSAGEDIGEST-ALG-00`, `update:MESSAGEDIGEST-ORDER-00` |
| `MessageDigestSpec-md5-only.txt` | `g4:MESSAGEDIGEST-ALG-02` |

Comportamento inalterado por construção, e a previsão da tarefa confirmada empiricamente. É o
que põe esta tarefa no bloco 9.A.

## 5. Registro

`divergence_record.csv`: hunks `dc45378c76c1` e `cf20ec7172ba` (KeyGenerator),
`2d83810f0b2b` e `32cc72cebfd3` (MessageDigest), kind `automaton`, task 9.4, absorvendo os
hunks `d75cef8a1ccf` e `956338571658` da task 2.4. A família guard-on-field tem registro
(task 8.16, `conformance_record.csv:53-61`) mas para os **corpos**; estes dois sítios
`condition()` não tinham linha própria, o que é o que a tarefa alegava e se sustenta com esse
escopo.
