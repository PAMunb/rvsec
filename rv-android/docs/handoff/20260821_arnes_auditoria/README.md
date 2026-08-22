# Arnês da auditoria — o co-disparo `f1`/`f2` do `CipherSpec`

Sondas descartáveis, não código de produção. O documento que as interpreta é
`docs/20260821_auditoria_conformidade_mop_crysl.md`, achado **A4**.

## A pergunta

§5.2 de `20260821_conformidade_mop_crysl.md` dá `g1 i1 f1` como testemunha de que o `CipherSpec`
aceita um `doFinal` sem `update`, com a justificativa de que *"o pointcut `doFinal(..)` também casa
`doFinal()`"*. Mas `jca_android/CipherSpec.mop` declara **dois** eventos que casam a mesma chamada —
`f1:198` (`call(public byte[] Cipher.doFinal())`) e `f2:205` (`call(public byte[] Cipher.doFinal(..))`)
— e nenhum dos dois tem `condition(...)`, ao contrário do par `g1`/`g4` que §4.1 analisa. A pergunta
é o que acontece quando os dois casam a mesma chamada.

## As três sondas

| | O que isola | Resultado |
|---|---|---|
| **A** `OrderProbeSpec` | ordem de disparo, com `ere` permissivo que aceita tudo | uma chamada `doFinal()` emite **`f1` e depois `f2`** |
| **B** `FsmProbeSpec` | o veredito, com o `fsm` real do `CipherSpec` (`s2` tem `f2`, não `f1`) | a testemunha do documento dá **`[FAIL]` em `f1`** |
| **C** `SwapProbeSpec` | robustez: idêntica à B, com `f2` declarado **antes** de `f1` | a ordem de disparo inverte, e a trajetória **falha na mesma** |

A sonda C é o que fecha o argumento: a ordem de disparo segue a ordem de declaração (invertê-la
inverte o disparo), mas o veredito **não depende dela** — no `fsm` real nem `s2` nem `end` têm
transição de `f1`, então a trajetória `getInstance; init; doFinal()` termina em `FAIL` nas duas
ordens.

## Como reproduzir

```bash
cd rvsec/javamop && mvn -o -q dependency:build-classpath -Dmdep.outputFile=/tmp/jmcp.txt
JM=/home/pedro/desenvolvimento/repository/br/unb/cic/javamop/javamop/0.9.3-SNAPSHOT/javamop-0.9.3-SNAPSHOT.jar
CPM="$JM:$(cat /tmp/jmcp.txt)"
RVBIN=rvsec/rv-monitor/target/release/rv-monitor/bin/rv-monitor   # o script, nao a classe:
                                                                 # ele define LOGICPLUGINPATH
R=/home/pedro/desenvolvimento/repository
AJTOOLS=$R/org/aspectj/aspectjtools/1.9.25.1/aspectjtools-1.9.25.1.jar
AJRT=$R/org/aspectj/aspectjrt/1.9.25.1/aspectjrt-1.9.25.1.jar
RT=$R/br/unb/cic/rvmonitor/rv-monitor-rt/0.9.3-SNAPSHOT/rv-monitor-rt-0.9.3-SNAPSHOT.jar

cd B
java -cp "$CPM" javamop.JavaMOPMain -merge -d . FsmProbeSpec.mop
$RVBIN -merge -d . FsmProbeSpec.rvm
mkdir -p out && java -cp "$AJTOOLS" org.aspectj.tools.ajc.Main -1.8 -nowarn \
  -cp "$AJRT:$RT" -d out Prog.java FsmProbeSpecRuntimeMonitor.java FsmProbeSpecMonitorAspect.aj
java -cp "out:$AJRT:$RT" Prog
```

Tudo na JSE, `ajc` 1.9.25.1, JDK 25 do host. Nenhum emulador envolvido.

## Duas armadilhas do arnês, medidas

- **`rvmonitor.Main` não é a classe principal.** É
  `com.runtimeverification.rvmonitor.java.rvj.Main`, e invocá-la diretamente dá
  `Logic Engine Error: null` porque os plugins de lógica são localizados pela variável de ambiente
  `LOGICPLUGINPATH`. Use o script `bin/rv-monitor`, que a define.
- **No `fsm`, o handler de aceitação chama-se pelo alias.** `@match` dá
  `match is not a supported state in this logic, fsm`; o correto é `@match1`, `@match2`, … — que é
  o que o `CipherSpec` real faz.
