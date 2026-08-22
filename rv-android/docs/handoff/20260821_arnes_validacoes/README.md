# Arnês das validações V1–V10 (21/08/2026)

Código de sonda, não de produção. O documento que o interpreta é
`docs/20260821_validacoes_conformidade_mop_crysl.md`; as notas brutas estão em `NOTAS-BRUTAS.md`.

## Como reproduzir

```bash
# classpath do javamop
cd rvsec/javamop && mvn -o -q dependency:build-classpath -Dmdep.outputFile=/tmp/jmcp.txt
JM=/home/pedro/desenvolvimento/repository/br/unb/cic/javamop/javamop/0.9.3-SNAPSHOT/javamop-0.9.3-SNAPSHOT.jar
CPM="$JM:$(cat /tmp/jmcp.txt)"

# classpath do CrySLParser (um pom com a dependencia CrySLParser:4.0.6 basta)
CPC=...   # ver v6/LiftCrysl.java
GSON=.../gson-2.13.1.jar

# normalizacao lexica do api30 -> .crysl (CINCO substituicoes, ver o documento §V3)
# leitores -> JSON
java -cp "$CPC:$GSON:." LiftCrysl <dir_api30_normalizado> crysl.json
java -cp "$CPM:$GSON:." LiftMop   <dir_jca_android>       mop.json
# nucleo: comparacao M2 com testemunha
java -cp "$GSON:." M2 crysl.json mop.json maps/MessageDigest.map maps/Cipher.map ...
# gerador
java -cp "$CPM:$GSON:." Gen crysl.json GCMParameterSpec.crysl saida.mop
```

## Conteudo

| caminho | o que e |
|---|---|
| `v1/` | `MOPSpecFile` montado a mao pelo `DumpVisitor` (V1) |
| `v2/Gen.java`, `v2/gerados/` | gerador crysl->mop e as tres specs geradas (V2) |
| `v3/V3.java`, `v3/ApiCheck.java` | leitura com/sem `android.jar`; conferencia contra a API 30 (V3) |
| `v4/`, `v4/synth/` | dump do `StateMachineGraph`, varredura de nao-determinismo, sinteticas (V4) |
| `v5/V5.java` | AST EMF: nomes de evento e agregado, procedencia (V5) |
| `v6/LiftCrysl.java`, `v6/LiftMop.java` | os dois leitores da costura JSON (V6) |
| `m2/Aut.java`, `m2/M2.java` | nucleo: ERE, fsm, subconjunto, N1, equivalencia com testemunha |
| `maps/*.map` | mapas de alfabeto MOP->CrySL das cinco specs comparadas |
| `v8/` | specs sonda e programas do teste de fatiamento na JSE (V8) |
| `v9/`, `v9/synth/` | sondas dos dois achados de subagente (V9) |
| `v10/rvsec-crysl/` | o esqueleto de quatro poms que compilou no reator (V10) |
| `crysl.json`, `mop.json` | o modelo canonico serializado, 33 regras e 23 specs |

`v8` exige `ajc` (aspectjtools 1.9.25.1) e `rv-monitor-rt`; roda inteiro na JSE, sem emulador.
