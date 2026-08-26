# Dossiê de decisão — grupo 10.B da gh105 (tarefa 10.10)

**Data**: 2026-08-25 · **Estado**: aguardando decisão do pesquisador · **Escopo**: uma tarefa
**Regra que se aplica**: mudança do que é acusado não entra sem decisão por cláusula

---

## 1. O defeito

`CipherSpec.mop:166-167`, evento `i2`:

```java
PredicateVerdict asSecretKey = PredicateStore.instance().validate(Property.GENERATED_KEY, key,
    alg(c.getAlgorithm()));
```

O `alg(...)` aí é o **congelado** `CipherTransformationUtil.alg` (importado estaticamente na
linha 36): parte a string no `/` e devolve o primeiro pedaço, sem resolver alias. Todo o resto
dos sítios de valor do mesmo arquivo passa pelo `CipherTransformationNormalizer` desde a 9.10.
É a terceira exposição do mesmo defeito que aquela tarefa reparou.

**O mecanismo, verificado nesta adjudicação e não presumido.** A loja dobra posições de valor
`String` para minúscula (`PredicateStore.java:171`), então variantes de caixa **já casam** — a
hipótese "aes vs AES" da auditoria está refutada. O que fica exposto é grafia por alias e
composta: `Cipher.getInstance("AES_128/CBC/PKCS5Padding")` com chave de um
`KeyGenerator("AES")` forma a tupla `("aes_128")` contra a do produtor, `("aes")` → VIOLATED →
um `CIPHER-CONSTR-00` falso, que o envelope apresenta como evidência positiva de mau uso.

## 2. As duas perguntas que a tarefa mandou responder antes da decisão

Medidas sobre as classes compiladas do reator (`rvsec-core/target/classes`), não lidas:

| transformação | `alg` congelado | `alg` normalizador | `isValid` |
|---|---|---|---|
| `AES_128/CBC/PKCS5Padding` | `AES_128` | `AES_128` | false |
| `AES_128/ECB/PKCS7Padding` | `AES_128` | `AES_128` | false |
| `PBEWithHmacSHA1AndAES_128` | `PBEWithHmacSHA1AndAES_128` | `AES_128` | false |
| `AES/CBC/PKCS5Padding` | `AES` | `AES` | true |
| `AES/CBC/PKCS7Padding` | `AES` | `AES` | true |
| `RSA/None/PKCS1Padding` | `RSA` | `RSA` | true |
| `aes/cbc/pkcs5padding` | `aes` | `AES` | true |

**(i) O reparo como escrito não fecha o caso que o motivou.** Para as grafias compostas
`AES_128/...` o normalizador devolve `AES_128` igualzinho ao congelado — porque a tabela de
alias pinada já tem `AES_128/CBC/PKCS5Padding` como forma canônica (`alias_table.csv:22`) — de
modo que a tupla continua sendo `("aes_128")` contra `("aes")` do produtor. A **única** classe
de grafia cujo `alg` de fato muda é a família PBE de uma palavra: `PBEWithHmacSHA1AndAES_128`
sai de si mesma para `AES_128`.

E há um risco de sentido contrário, que só a medição mostra: se o programa obteve a chave de um
`KeyGenerator("PBEWithHmacSHA1AndAES_128")`, hoje as duas pontas usam a string crua e **casam**;
com o consumidor normalizado e o produtor não, passariam a divergir. Rotear só o consumidor
troca um falso positivo por outro.

**(ii) Não há risco de silêncio novo.** As três grafias afetadas têm `isValid = false`, ou seja,
cada uma já tira `CIPHER-ALG-0x` do teste de valor no mesmo programa. O `CONSTR` falso sempre
anda em cima de uma acusação verdadeira, e retirá-lo é higiene de categoria: o programa continua
acusado, pela razão certa.

## 3. As opções

**A. Rotear o divisor pelo normalizador e nada mais.** Fecha a família PBE de uma palavra, não
fecha as compostas `AES_128/...`, e abre a divergência produtor-cru/consumidor-normalizado
descrita acima. Não recomendo isoladamente.

**B. Rotear as duas pontas e dobrar a família de serviço `AES_128/192/256` em `AES` na
comparação.** Fecha o caso que motivou a tarefa. É uma decisão de valor: passa a tratar
`AES_128` e `AES` como o mesmo algoritmo para efeito de origem de chave — o que é verdade no
Conscrypt (são o mesmo serviço com tamanho fixo) e não está escrito em nenhuma regra.

**C. Registrar a família como divergência deliberada e não mexer.** Custa um `CIPHER-CONSTR-00`
falso por programa que use grafia composta, sempre acompanhado do `CIPHER-ALG-0x` verdadeiro.
Zero risco, e a linha de registro fica.

## 4. O que a decisão dispara

Qualquer opção que edite `.mop` ou Java entra com a disciplina do 9.B: par de arnês
satisfaz/viola, linha de divergência, e a evidência commitada. A opção C é só linha de registro.
