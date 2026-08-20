# Relatório — Agente C (2ª passada): custo do gerador FSM e onde nasce o OOM

Data: 2026-08-20. Ambiente: JDK 25.0.3 (Temurin), 123 GB RAM (heap default do HotSpot ≈ 31 GB),
64 cores. Release usado: `rv-monitor/target/release/rv-monitor` (fsm.jar buildado em 2026-08-20).
Nenhum arquivo do repo foi editado; todo código de teste está neste diretório.

## TAREFA 1 — driver direto sobre `FSMCoenables`

`Drive.java` (neste diretório): FSM de 6 estados (start, s1, s2, s3, m + `fail` implícito),
cadeia start→s1→s2→s3→m→s1, alfabeto de n símbolos, demais transições caem em `fail`
(absorvente com auto-laço em todos os símbolos — mesma forma da `CipherSpec`). Compilado contra
`fsm-0.9.3-SNAPSHOT.jar` + `logicrepository-0.9.3-SNAPSHOT.jar`; executado com `java -Xss1g`.

| n | categoria `fail` (medido) | n·(2ⁿ−1) | aritmética | tempo | sem `fail` |
|---:|---:|---:|:--:|---:|---|
| 14 | 229.362 | 14·16.383 = 229.362 | ✓ | 1,26 s | 7 entradas, 2,2 ms |
| 16 | 1.048.560 | 16·65.535 = 1.048.560 | ✓ | 5,27 s | 7 entradas, 2,1 ms |
| 17 | 2.228.207 | 17·131.071 = 2.228.207 | ✓ | 10,7 s | 7 entradas, 2,1 ms |
| 18 | 4.718.574 | 18·262.143 = 4.718.574 | ✓ | 22,7 s (sob `-Xmx2g`) | 7 entradas, 2,5 ms |

- Os quatro valores da auditoria estão corretos **na aritmética e na medição** — igualdade exata.
- Sem `fail` a contagem é constante e ~2 ms em qualquer n (a auditoria mediu 10 entradas; aqui 7 —
  diferença de fiação do autômato sintético, irrelevante: o ponto é a constância).
- `toString()` a n=18: **200.540.491 caracteres** em 4,0 s, e **cabe** em `-Xmx2g` no driver
  isolado (o driver inteiro, cômputo + toString, roda sob 2 GB).
- n=18 sob `-Xmx2g` **não estoura** no driver (22,7 s) — reproduz a correção da 1ª auditoria.

## TAREFA 2 — o pipeline real e ONDE nasce a falha

Caminho real: `javamop` **não** invoca o logic repository (nenhum `Runtime.exec` para ele; o
autômato vai no `.rvm`). Quem paga o custo é o `rv-monitor` (`rvj.Main`), que lança o filho
`logicrepository.Main` via `LogicRepositoryConnector.executeProgram` com `java -Xss1g` **sem
`-Xmx`** (`LogicRepositoryConnector.java:151`), coleta stdout+stderr por `StreamGobbler` e
concatena os dois antes do parse XML (`:229`).

Specs usadas: `SyntheticSpec.rvm` (18 eventos, mesmo autômato do driver, `@fail`+`@match1`) e a
**`CipherSpec.rvm` real** (17 eventos, de `results/gh51_e2e_test/monitors/`). Heap do filho
controlada por um wrapper de `java` no PATH (o connector resolve `java` pelo PATH herdado);
heap do pai por `-Xmx` explícito na linha de comando.

### Matriz medida

| run | spec | pai | filho | resultado |
|---|---|---|---|---|
| baseline | n=18 | default (~31g) | default | **rc=1, `StackOverflowError` no PAI** (regex), 40,8 s |
| p24g-c2g | n=18 | 24g | 2g | filho OK (29,8 s, exit 0, RSS 2,2 GB); **PAI SOE** em 37,3 s |
| p2g-c2g | n=18 | 2g | 2g | filho OK; **PAI SOE** em 35,8 s |
| p1g-cdef | n=18 | 1g | default | filho OK; **PAI SOE** em 38,5 s |
| pdef-c1g | n=18 | default | 1g | **FILHO OOM** ("Java heap space", exit 1, 26,8 s) → pai imprime `Logic Engine Error: null` e **sai com rc=0**, sem monitor |
| default | Cipher 17 | default | default | **PASSA**, 54,2 s, monitor gerado |
| p2g-c2g | Cipher 17 | 2g | 2g | **PASSA**, 52,5 s (filho 16,7 s) |
| p1g-c1g | Cipher 17 | 1g | 1g | **PASSA**, 53,1 s (filho RSS 1,19 GB) |

### Onde nasce cada falha

1. **n=18, o modo dominante não é OOM — é `StackOverflowError` no PAI**, dentro de
   `java.util.regex` chamado por `EnableSet.parseSets` (`EnableSet.java:66-116`, via
   `CoEnableSet` sobre a string de coenables da categoria `fail`). O padrão
   `...(\s*\,\s*\[...\])*...` recursa um frame de `Pattern$Loop` por repetição — profundidade
   proporcional às 4,7 M entradas. Ocorre com **qualquer** heap (1g, 2g, 24g, 31g default).
2. **`-Xss` já está no máximo.** Este JDK rejeita qualquer valor acima de 1g
   (`-Xss1025m` → "Invalid thread stack size"). O `-Xss1g` do launcher e do connector é o teto
   absoluto da JVM. Logo **n=18 não é destravável por flag nenhuma** — nem `-Xmx`, nem `-Xss`.
   n=17 (2,2 M entradas) passa com o mesmo 1 GB de stack; o teto duro do parser está entre 17 e 18.
3. **OOM existe, mas só no FILHO e só com heap < ~2 GB** (a n=18): com `-Xmx1g` o filho morre de
   "Java heap space" ao computar/serializar. O OOM "histórico" é este modo: numa máquina/container
   com pouca RAM, a heap default do filho (¼ da RAM, não configurável — o connector não passa
   `-Xmx`) fica abaixo do necessário. Em containers de 8 GB, default do filho = 2 GB: o limiar
   exato de n=18.
4. **A falha é duplamente mascarada** (confirma e agrava a R5): (i) o OOM do filho vai para o
   stderr, que o pai concatena **depois** do XML → `SAXParseException` → `RVMException("Logic
   Engine Error: null")` → o `Main` imprime e **sai com exit 0**, sem gerar monitor; (ii) medimos
   ao vivo que **qualquer byte no stderr do filho** quebra o parse — a linha
   "Picked up JAVA_TOOL_OPTIONS" bastou para matar uma geração que o filho completou com sucesso
   (exit 0). O pipeline não distingue "filho OOM" de "filho falou no stderr".
5. Custo real da `CipherSpec` (17 eventos) hoje: ~53 s por geração, dos quais ~18 s no filho e
   ~35 s no pai (parse regex da string de 82,4 M chars). Cabe em 1 GB de heap dos dois lados.

## Vereditos

**(a) Fórmula e custos do `FSMCoenables` — SUSTENTADO.** n·(2ⁿ−1) exato nas quatro linhas,
aritmética conferida (229.362 / 1.048.560 / 2.228.207 / 4.718.574), tempos compatíveis com a 1ª
auditoria (1,26/5,3/10,7/22,7 s vs 1,3/6,6/11,0/23,7 s), sem `fail` constante em ~2 ms.

**(b) Atribuição do OOM — REFINADO.** A auditoria acertou que a falha não é do `FSMCoenables` e
que nasce no pipeline; errou o mecanismo dominante. A n=18 o pipeline **não morre de OOM em
condições normais de heap**: morre de `StackOverflowError` no parser regex do PAI
(`EnableSet.parseSets`), independente de `-Xmx`, com `-Xss` já no máximo da JVM. O OOM verídico é
o do **filho** com heap < ~2 GB (default de ¼ da RAM em máquina pequena/container), e ele se
manifesta exatamente como a auditoria previu para a R5: mascarado — `Logic Engine Error: null`,
**exit 0**, nenhum monitor. O `toString()` gigante é o multiplicador de custo, mas o
`StreamGobbler` do pai não foi o ponto de estouro em nenhuma configuração medida.

**(c) Conclusão prática sobre o CipherSpec — REVERTIDO (nos dois sentidos úteis).**
"Passar `-Xmx` maior destrava um CipherSpec de 17-18 eventos" é **falso**:
- **17 eventos não precisa ser destravado** — a `CipherSpec` real gera hoje com 1 GB/1 GB em 53 s.
  O re-orçamento 17→14 do plano **não é necessário para viabilidade** (continua válido como
  otimização de 53 s→ms por spec, se quiser).
- **18 eventos não é destravável por `-Xmx`** (nem por `-Xss`, já no teto). O teto de 17 do
  INV-INS-115 é um **teto duro do parser do pai**, não da heap, e só cai com patch no rv-monitor
  (reescrever `parseSets` sem regex com backtracking linear no nº de conjuntos, ou não emitir/
  truncar os coenables de `fail`). Enquanto o alfabeto do `Cipher` ficar ≤ 17, nenhuma ação é
  necessária; qualquer 18º evento exige o patch.

Ressalvas de escopo: JDK 25 nesta máquina (o limiar exato do SOE pode deslocar-se com outro JDK,
mas a natureza — stack do regex, não heap — não); spec de 18 eventos é sintética com nomes curtos
(nomes reais alongam a string e só pioram); `javamop` confirmado fora do caminho do custo.

## Arquivos

- `Drive.java` / `Drive.class` — driver da Tarefa 1.
- `pipeline/SyntheticSpec.rvm`, `pipeline/CipherSpec.rvm` — specs.
- `pipeline/run3.sh` (+ variantes `-ss*`) — harness da matriz; `jwrap/java` — wrapper do filho.
- `pipeline/*.log|.err`, `pipeline/childlogs/` — evidência bruta de cada run.
