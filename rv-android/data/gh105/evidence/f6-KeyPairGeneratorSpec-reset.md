# Tarefa 9.2 — o `__RESET` que faltava, e a medição que o arnês não entrega

**Data**: 2026-08-25 · **Commit da árvore**: `70877f67`
**A** `~/tmp-gh104/g9impl/A0` (o conjunto antes do reparo) ·
**B** `rvsec/rvsec-mop/src/main/resources/jca_android` · **corpus** `data/gh104/traces` (159)

## 1. O reparo

`KeyPairGeneratorSpec.mop`, bloco `@fail`: entra `__RESET;`. Era o **único** `@fail` do
conjunto sem ele — 20 dos 21 já resetavam — e o desequilíbrio estava registrado desde a task 8.7
como o achado W2 de revisão, com uma linha narrativa própria em `divergence_record.csv`.

## 2. Por que a re-emissão acontecia

Lidos no monitor **regenerado desta sessão** (`~/tmp-gh104/g9impl/monitors/`):

- `fail` é sumidouro: toda linha de transição leva `fail → fail`.
- `KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4` é reatribuída em **sete**
  pontos do despachante, um por família de evento.
- O despachante chama o handler sempre que a categoria vale — **inclusive em despachos cuja
  `condition(...)` é falsa**, que não transicionam e portanto não recalculam a flag que os fez
  disparar.

Com o reset, a categoria volta a `false` e esses despachos silenciosos param de reacusar. Um
evento posterior que **de fato** transicione continua acusando, de `start` para `fail` outra
vez — que é o único relatório que uma sequência rejeitada deve.

## 3. A evidência: o monitor gerado, não a classe do arnês

Antes (`~/tmp-gh104/gh105-verif-g9/monitors/MultiSpec_1RuntimeMonitor.java:6124-6126`):

```java
ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, ...));
kp = null;
}
```

Depois (`~/tmp-gh104/g9impl/monitors/MultiSpec_1RuntimeMonitor.java`, classe
`KeyPairGeneratorSpecMonitor`):

```java
ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, ...));
kp = null;
this.reset();
}

final void reset() {
    this.pairValue.set(this.calculatePairValue(-1, 0));
    KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = false;
    KeyPairGeneratorSpecMonitor_Prop_1_Category_match = false;
}
```

O `reset()` limpa a categoria **e** devolve o par ao estado 0. É esta a evidência do reparo.

## 4. O que o arnês diz, e por que não podia dizer outra coisa

```
A=g9impl/A0  B=g9impl/B2   →   {"unchanged": 159}
```

159 de 159 `unchanged`, **`KeyPairGeneratorSpec-sticky-fail.txt` incluído** — o trace que a
task 8.15 escreveu exatamente para este defeito. Não é o arnês desmentindo o reparo; é o
instrumento sendo estruturalmente cego a ele, por duas razões independentes e medidas:

1. **`ErrorCollector.addError` deduplica.** A chave é
   `(spec, código, evento, classe, método, local)`, num `HashSet`
   (`rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:51-54`, via `ErrorSummary.equals`).
   A re-emissão no **mesmo sítio** nunca vira linha nova.
2. **O TraceRunner tem um único sítio sintético.** Todos os despachos de um trace compartilham
   o mesmo `__LOC`, então o lado A cai inteiro na dedup.

Segue-se que o delta observável em `errors.csv` é **no máximo uma linha por sítio de chamada
distinto**, e vem sobretudo dos despachos condition-false. O critério que uma redação anterior
da tarefa exigia — "a classe é `removed`, nunca `unchanged`" — é **insatisfazível pelo
instrumento que a própria tarefa exigia**, e a tarefa foi reescrita para dizê-lo antes de ser
implementada.

## 5. O que este reparo NÃO faz

- Não muda o que é acusado: nenhum programa passa a ser acusado, nenhum deixa de ser. É por
  isso que a tarefa está no bloco 9.A, que dispensa decisão do pesquisador.
- Não corrige a outra metade da assimetria que o W2 nomeava: `kp = null;` limpa um campo
  encenado enquanto `algorithm` continua setado, onde o irmão
  `KeyGeneratorSpec.mop:169-176` limpa os dois. Fora do escopo desta tarefa, e a linha do
  registro continua dizendo-o.
- Não traz a medição de corpus que a linha W2 dizia estar esperando. Ela não foi feita e não é
  o que licencia o reparo; o que licencia é o monitor gerado acima.

## 6. Registro

`divergence_record.csv`: o hunk `ea1bc52595fd` (kind `predicate-removal`, task 9.2) absorve
o `ee86d177e08f` das tasks 7.5/4.14; a linha narrativa W2 passa a dizer **REPAIRED**, com as
duas ressalvas acima escritas nela.
