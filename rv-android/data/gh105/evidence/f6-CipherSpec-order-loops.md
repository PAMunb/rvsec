# Tarefa 9.13 — as duas transições que os oráculos licenciam, e a terceira que nenhum licencia

**Data**: 2026-08-25 · **Decisão**: GO nas duas licenciadas, **NO na terceira** (pesquisador, 25/08)
**Par**: `A = pós-9.1` · `B = A + 9.13` · `~/tmp-gh104/g9b/pair-913.json`

## O que entrou

Duas transições sobre eventos que já existem. O `fsm` **não ganha evento** e o teto de 17 não é
tocado — o que corrige a observação do item (e) do `conformance_record.csv` de que reparar isso
"would need new events".

```
s2 [ + i1 -> s2   + i2 -> s2 ]        s3 [ + u1..u5 -> s3 ]
```

- **`s3` não tinha laço de `update`**, então `init; update; update` falhava onde a api30
  (`Cipher.cryptsl:117`, `updates+`) e o expert (`Cipher.crysl:85`, `Update+`) **os dois** admitem.
- **`s2` não tinha laço de `init`**, então `init; init` falhava onde os dois dizem `Inits+`/`Init+`.

## O que ficou de fora, e por quê

O primeiro texto da tarefa pedia uma terceira: re-`init` em `end`, o "Cipher reusado". **Nenhum dos
dois oráculos a licencia** — nem a api30 nem o expert retornam do grupo dos finais para `Inits`:

```
api30   Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+
expert  Get, Init+, AADUpdate*, WKB+ | (FINWOU | (Update+, DoFinal))+
```

Aceitá-la tornaria esta especificação **mais permissiva que os dois oráculos**. Isso não é
conformização: é decisão de projeto, e não foi tomada. Se um dia for desejada, precisa de linha
própria de `divergence_record.csv` declarando a permissividade. O trace `CipherSpec-init-init.txt`
diz isso no seu próprio cabeçalho, para que a ausência do caso não seja lida como esquecimento.

## O medido

Dois traces novos, porque o corpus não tinha nem `update; update` nem `init; init`:
`CipherSpec-update-update.txt` e `CipherSpec-init-init.txt`.

```
pair-913: 172 traces  {"unchanged": 170, "moved": 2}
```

| trace | A | B |
|---|---|---|
| `CipherSpec-update-update.txt` | `f1:CIPHER-ORDER-00`, `i2:CIPHER-NOBS-00`, **`u1:CIPHER-ORDER-00`** | `i2:CIPHER-NOBS-00` |
| `CipherSpec-init-init.txt` | `f1:CIPHER-ORDER-00`, `i2:CIPHER-NOBS-00`, **`i2:CIPHER-ORDER-00`** | `f1:CIPHER-ORDER-00`, `i2:CIPHER-NOBS-00` |

O `NOBS` das duas é sobre a chave vinda de um `bind` que o monitor não observou nascer, e não se
move: isola o delta.

### O `f1` que sobra no segundo trace é fiel ao oráculo, não defeito

Em `update-update` o lado B fica limpo do `f1` também; em `init-init` ele fica. Vale explicar,
porque parece um reparo pela metade e não é. A api30 ordena

```
Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+      FINWOU := f2 | f4 | f5 | f6 | f7
                                                         DOFINALS := FINWOU | f1 | f3
```

`f1` é `cipherText = doFinal()` e está em `DOFINALS`, **não** em `FINWOU`. Ou seja: um `doFinal()`
sem argumento só é admitido **depois de um `updates+`** — que é exatamente o que o
`update-update` tem e o `init-init` não. O `s2` do `.mop` não lista `f1` e está certo. A
acusação que sobra é o autômato sendo fiel à regra, e não a metade que faltou reparar.

## Massa

**10.814 linhas sobre 21 apps** (`conformance_record.csv` item (e)) — é **teto das duas classes
juntas**, o registro não as separa, e é teto e não atribuição causal: foi medido na campanha
publicada sobre o `jca` congelado.
