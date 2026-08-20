# Handoff — segunda passada de verificação do plano de fiação de predicados

**Este arquivo é um prompt de entrada para uma nova sessão. Leia-o inteiro antes de agir.**

---

## 1. O que esta sessão tem de fazer

**Verificar rigorosamente a consistência do plano** em
`docs/20260820_plano_fiacao_predicados.md` — o documento de ideação (Fase 0) da change que vai
ligar corretamente os predicados CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) nas specs JavaMOP do
conjunto `jca_android`.

**Isto é uma segunda passada.** Uma primeira auditoria já rodou e está registrada em
`docs/20260820_auditoria_plano_predicados.md` — 47 alegações, 33 confirmadas, 10 corrigidas, 3
refutadas, 1 não verificável. As correções já foram aplicadas ao plano, marcadas com **[auditado]**.

Portanto o trabalho desta sessão é diferente do da anterior. Ele tem três frentes:

1. **Auditar a auditoria.** Os vereditos da primeira passada não são sagrados. Onde ela diz
   `CONFIRMADO`, reconfira por amostragem; onde diz `CORRIGIDO` ou `REFUTADO`, reconfira
   **integralmente**, porque uma correção errada é pior que o erro original. Ela introduziu
   números novos (35 pares, 25 valores de enum, 299/322 no venn, 59/29/2 nas aridades) e afirmações
   novas de semântica — todas precisam do mesmo escrutínio que o plano recebeu.
2. **Fechar o que ficou aberto.** §7 abaixo lista o que não foi verificado e o que a auditoria
   deixou como decisão, não como fato.
3. **Verificar a coerência do plano corrigido como um todo.** As edições foram cirúrgicas; nada
   garante que as seções continuem se sustentando mutuamente depois delas. §6 abaixo.

**Não é para implementar.** Não crie issue, não crie change OpenSpec, não edite spec `.mop`. O
produto é o plano ainda mais correto e um registro do que mudou.

O critério é o do domínio: **JavaMOP é método formal e tudo depende da corretude das specs.** Uma
afirmação que não resista à verificação tem de ser corrigida **antes** de virar artefato OpenSpec.
Já houve duas tentativas fracassadas de fiação; um erro aqui custa a terceira.

---

## 2. Onde estamos

### 2.1 A change antecessora (gh104)

`openspec/changes/gh104-legible-violation-reports/` — **87 de 96 tarefas fechadas.** As 9 abertas
são **todas** do Grupo 10 (integração final: lint, verify, validação em dispositivo, code review,
docs-sync, sync de invariantes).

**O Grupo 10 NÃO deve ser implementado agora.** Decisão do pesquisador: a validação final das duas
changes — a gh104 e esta nova — será feita **por um mesmo experimento**, separado, em
`experimento-gh104/`. Não rode o Grupo 10, não marque suas caixas, não o antecipe.

### 2.2 A deriva já foi resolvida — não a reabra do zero

O plano foi escrito enquanto a gh104 implementava o **Grupo 7**. Hoje o **Grupo 9** está
concluído, então os Grupos 8 (E4 — reparos estruturais) e 9 (E6 — identidade) landaram depois das
medições originais.

**A primeira auditoria reconferiu isso e o resultado é limpo:** os Grupos 8/9 tocaram 12 dos 23
arquivos de `jca_android` (mais `codes.csv`), mas **a distribuição de predicados é idêntica valor a
valor entre `d27c48e9` (coleta original) e `bd61abea` (reancoragem)**. O gate G-PRED sustentou. As
contagens do plano estão reancoradas ao `HEAD`.

Confira que o `HEAD` ainda é `bd61abea`. **Se mudou, refaça a reconferência** — o comando está em
§5.1.

**Podemos reverter.** O plano é a alteração **final** das specs, e o critério é a compatibilidade
com as regras CrySL. Se um reparo do Grupo 8/9 conflitar com o que o plano prescreve, isso é
material de decisão, não algo intocável. Registre o conflito; não desfaça nada nesta sessão.

### 2.3 O que a gh104 entregou e que esta change herda

1. **O maquinário de predicados preservado** — 134 linhas de `ExecutionContext` byte a byte do
   `jca` congelado (decisão D-11), com o gate G-PRED invertido para asseverar preservação. A
   decomposição está em `data/jca_android/README.md`: 23 `import`, 27 `validate(`, 49
   `setProperty(`, 9 `remove(`, 25 chamadas de estado de aceitação e 1 comentário.
2. **O instrumento**: `scripts/gh104_diff_harness.py` (replay de traços por dois snapshots, com
   classificação `unchanged`/`moved`/`removed`/`introduced`), `scripts/gh104_gates.py`
   (G-2, G-2a, G-2b', G-2c, G-2d, G-6', G-ERE, G-CONF, G-PRED), `scripts/gh104_message_gate.py`,
   `scripts/gh104_mop_lint.py`, o `TraceRunner` em `rvsec-mop` (escopo de teste) e os traços
   versionados em `data/gh104/traces/`.
3. **O envelope de mensagem** `v=1 code=… ev=… obj=… val=… exp=… msg='…'`, a macro `__EVENTNAME`
   emitida pelo gerador, e `jca_android/codes.csv` com os códigos de falha.
4. **Os registros** em `data/jca_android/`: `conformance_record.csv` (74 linhas, literais de
   allow-list), `constraint_table.csv` (60 linhas, CONSTRAINTS regra a regra), `divergence_record.csv`,
   `alias_table.csv`, `gate_allowlist.csv`, `README.md`.

A gh104 declarou esta change no seu `design.md` D-11, textualmente: *"Wiring the predicates
correctly is a change of its own. It is the right repair and it is not attempted here. Its
prerequisite is the instrument this change builds: the differential harness."*

---

## 3. Escopo e restrições

### 3.1 O que muda

**Somente as specs de `rvsec/rvsec-mop/src/main/resources/jca_android/`** (23 `.mop` +
`codes.csv`), mais o substrato Java que elas chamam (`rvsec-core`) e a camada de gates
(`rv-android/scripts/`, `tests/parity/`).

**Os outros conjuntos não são consertados.** `jca` continua congelado, `generic` e `generic_new`
continuam como estão, `jca_android_bug_predicate` continua arquivado. O foco é `jca_android` e só.

### 3.1-bis Decisão do pesquisador: classe nova, classe antiga depreciada

**As nossas classes não podem quebrar com as specs antigas.** A estratégia é criar **classes
novas**, usá-las apenas nas specs `jca_android`, e marcar as antigas como `@Deprecated` — sem
removê-las e sem alterá-las — até que uma change futura faça as devidas migrações.

Isto **substitui** a formulação anterior do plano ("uma implementação de store por conjunto de
specs") por algo mais simples e mais seguro, e resolve o R1 por construção: se a classe antiga não
é tocada, o congelamento do `jca` não pode ser quebrado por acidente — nem pelo caminho que já
falhou uma vez (`233df18a` → revertido em `e204e2a4`), que era exatamente mudar a classe
compartilhada achando que o gate do `jca` cobria.

**O levantamento que torna a decisão barata** (medido em `bd61abea`):

| conjunto | specs que chamam `ExecutionContext` |
|---|---:|
| `jca` (congelado) | 23 |
| `jca_android` (o alvo) | 23 |
| `jca_android_bug_predicate` (arquivado) | 23 |
| `generic` | **0** |
| `generic_new` | **0** |

Ou seja: **`generic` e `generic_new` não tocam o substrato de predicados.** Depois que
`jca_android` migrar para a classe nova, os únicos consumidores da antiga serão o conjunto
congelado e o arquivado — ambos read-only por política. A classe antiga pode então ser depreciada
por inteiro, sem adaptador, sem shim e sem risco.

**A superfície pública a preservar intacta na classe antiga** (`ExecutionContext.java`):
`remove(Property)` (a sobrecarga `@Deprecated`, com 4 sítios no `jca`), `remove(Property, Object)`,
`setProperty`, `validate`, `isInAcceptingState`, `setObjectAsInAcceptingState`,
`unsetObjectAsInAcceptingState`, `hasEnsuredPredicate` e `reset`. Nota útil:
`hasEnsuredPredicate` e `isInAcceptingState` têm **zero sítios em qualquer `.mop`** de qualquer
conjunto — só testes os chamam. A classe nova simplesmente **não os oferece**; isso não é remoção,
é ausência, e não quebra ninguém.

**Consequência para o P3 (sem retrocompatibilidade).** Não há conflito: o P3 manda deletar código
**morto ou superseded**, e a classe antiga continua **viva**, servindo o `jca` congelado. `@Deprecated`
aqui é sinalização de intenção para a change futura, não um shim de compatibilidade. Registre isso
no `design.md` quando a change for criada, para que a leitura do P3 não gere discussão depois.

**O que a verificação desta sessão tem de checar sobre isso:**
- a lista de métodos acima está completa e nenhuma spec antiga chama algo fora dela;
- a classe nova consegue oferecer o que a F0 pede — chave híbrida, aridade N, **três valores**,
  chaves fracas, thread-safety — **sem** tocar a antiga;
- a mudança de assinatura de `validate()` para três valores fica confinada à classe nova (é o que
  torna a decisão possível: com duas classes, os 27 sítios do `jca` não são atingidos);
- o gate G-PRED da gh104, que assevera preservação byte a byte do maquinário, continua fazendo
  sentido quando `jca_android` passar a chamar outra classe — **muito provavelmente ele precisa ser
  reformulado, e isso é trabalho a orçar.**

### 3.2 O que NÃO muda — inegociável

- **`jca/`** — congelado (gh101 D-S0, INV-INS-109). É a linha-base publicada no artigo
  `ase-journal`. Não descongelar, não reparar, não remedir.
- **`jca_android_bug_predicate/`** — registro da auditoria de 2026-08-08. Não reparar, não
  estender, não usar como semente. Hunks dele podem ser **reimplementados sob evidência própria**,
  nunca replicados por serem dele.
- **`generic/`, `generic_new/`** — não são alvo desta change (mas ver §3.3).
- **MetaCrySL** — as regras api30 são oráculo de leitura. Defeito de regra vira linha de
  `divergence_record.csv`, nunca edição a montante.
- **O weaver e a instrumentação** — fora de escopo.
- **Grupo 10 da gh104** — ver §2.1.

### 3.3 A restrição de genericidade

Embora só `jca_android` seja **alterado**, **a solução tem de ser genérica o bastante para aceitar
qualquer spec JavaMOP, inclusive as que não têm predicado algum.** Isso vale principalmente para a
camada de gates e para o `predicate_graph.csv` que o plano propõe.

O universo real está em
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources`:

| conjunto | `.mop` | observação |
|---|---:|---|
| `generic` | **118** | maior conjunto; sem predicados; caminho `Log.v`; nunca rodou; **82% multiparamétrico, até k=6** |
| `generic_new` | 27 | **17 delas não têm bloco `fsm`/`ere` algum** (event-only) |
| `jca` | 23 | congelado |
| `jca_android` | 23 | **o alvo** |
| `jca_android_bug_predicate` | 23 | arquivado |
| `aspect` | 0 | só `.aj` |
| **total** | **214** | |

A primeira auditoria levantou **seis lacunas de genericidade** e as escreveu na §8-bis do plano.
**Verifique a lista e procure a sétima.** As seis são: specs sem autômato (17 em `generic_new`);
`generic` não dá verde trivial (1 órfão em `FSM246.mop`); degradação nos 11 arquivos com nome de
parâmetro duplicado e na colisão de `import` de `FSM358.mop:4,6`; G-ORDER tem de pular
declaradamente specs sem regra CrySL; `predicate_graph.csv` com zero linhas tem de ser verde; e o
gate novo G-PARAM.

---

## 4. O que a primeira auditoria achou — e que precisa ser reconferido

Três achados reordenaram o plano. **São os que mais importam reconferir**, porque decisões de
arquitetura passaram a depender deles.

### 4.1 `byte[]` não pode ser parâmetro de spec do JavaMOP (§7.5 do plano)

Alegação: declarar `byte[]` ou `int[]` na lista de parâmetros de uma spec faz o JavaMOP **apagar a
lista inteira** — não só o parâmetro ofensor — e emitir um monitor global sem parametrização, com
`rc=0` e a mensagem normal de sucesso. `Object[]`, `Object` e `String` funcionam. O contorno é
declarar `Object` e ligar no pointcut contra o argumento `byte[]`, o que produz indexação por
identidade genuína (`CachedWeakReference`).

**Consequências que dependem disso** — e portanto caem se ele cair:
- a recomendação do D4 ("híbrido, mas B **não** como padrão");
- a troca do piloto de `Mac`/`Key` para a cadeia do IV;
- o gate novo G-PARAM;
- o risco novo R6.

**Reconfira reproduzindo** (receita em §5.4). Investigue também o que a auditoria **não** fez:
*por que* o JavaMOP faz isso — se é o parser da lista de parâmetros, o resolvedor de tipos, ou o
tradutor `.mop` → `.rvm`. Se houver correção barata a montante no `javamop`, isso muda o D4 de
novo. E teste `char[]` explicitamente: a auditoria inferiu por analogia com `byte[]`/`int[]` e
**não mediu** — é o tipo do `PBEKeySpec`.

### 4.2 O D1 está superestimado em ~2× (§10 do plano)

Alegação: a linha-base publicada (`RV=454, CC=423, both=112, só-RV=342, só-CC=311`) foi reproduzida
dígito a dígito. As allow-lists api30 sozinhas movem **zero** células do venn. Sob a leitura mais
agressiva — resolução de alias e descarte da chave inteira — o resultado é **299 / 322**, não os
255 / 354 que o plano alegava. E o risco editorial vem do **reparo dos acusadores órfãos (E5)**,
não das allow-lists.

**É a alegação com maior consequência para o pesquisador.** Reconfira (receita em §5.5).
Atenção aos pontos frágeis: a modelagem trata "a chave cai se **qualquer** evento
`UnsafeAlgorithm` seu foi silenciado" como o **máximo**; verifique se existe leitura defensável
mais agressiva que chegue aos 255. E o mapeamento spec → serviço usado no
`ConscryptAliasTable.matches` foi escrito à mão na auditoria — confira-o contra
`data/jca_android/alias_table.csv`.

### 4.3 `@fail` é o custo inteiro do gerador, não o gatilho (§7.3 do plano)

Alegação: sem `fail` na lista de categorias, n=18 custa **2 ms** e 10 entradas; com ele, 23,7 s e
4.718.574. A fórmula `n·(2ⁿ−1)` bate exata em n=14/16/17/18. **Mas o OOM com `-Xmx2g` em n=18 não
se reproduziu** — gerou em 23,7 s. A auditoria atribuiu o estouro ao pipeline completo (o
`toString()` de 82,4 M caracteres + o `StreamGobbler`), não ao `FSMCoenables`.

Essa atribuição é **hipótese, não medição**. Se for possível medir o pipeline real com `-Xmx`
variável e confirmar onde o estouro nasce, a conclusão "passar `-Xmx` destrava o `CipherSpec`"
fica ancorada — ou cai. **É o item aberto de maior valor prático**, porque decide se o
re-orçamento do alfabeto do `CipherSpec` (17→14) é necessário.

### 4.4 As dez correções numéricas

Reconfira todas; são baratas e a §5.1 traz os comandos.

| item | valor anterior do plano | valor da auditoria |
|---|---|---|
| valores do enum `Property` | 24 | **25** |
| escritas sem consumidor | 17 valores, 33 sítios | **18 valores, 35 sítios** |
| properties com zero sítios | `MACED`, `GENERATED_CIPHER`, `GENERATED_TRUST_MANAGERS` | **só as duas primeiras** |
| "19 arestas" | 19 arestas | **19 predicados conectáveis; 35 pares; 44 arestas** — F3 é de 35 itens |
| aridade das cláusulas CrySL | "a maioria binários" | **59 unárias, 29 binárias, 2 quaternárias** |
| cláusulas `NEGATES` no oráculo | implícito: os 9 `remove()` a traduzem | **2 cláusulas; ≤1 dos 9 corresponde** |
| extração imprecisa | geração antiga "cala-se" | **`ImpreciseValueExtractionError` existe e é lançado** — mas só no caminho de CONSTRAINTS |
| posições de predicado | "posição 0 = objeto, ≥1 = valor" | **decidido por tipo** (`trackedTypes = String/int/Integer`), não por posição |
| citação do registro de CONSTRAINTS | `conformance_record.csv`, 60 linhas | **`constraint_table.csv`, 60 linhas**; o outro tem 74 |
| D1 | 342→255, 311→354 | **342→299, 311→322** |

---

## 5. Comandos

**Cuidado com o caminho.** O alias `/pedro/...` não abre em processos Java (JVM). Use sempre
`/home/pedro/...` para qualquer coisa que passe por Maven, JavaMOP ou rv-monitor.

**As três ferramentas que a auditoria construiu ficaram no scratchpad da sessão e não sobrevivem.**
As receitas abaixo as reconstroem. Elas ainda **não são gates** — se forem promovidas, vão para a
camada da §8 do plano, com o contrato de genericidade da §8-bis.

### 5.1 Reconferir as medições

```bash
R=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
cd $R

# grafo de predicados
grep -ho "setProperty(Property\.[A-Z_]*" jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
grep -ho "validate(Property\.[A-Z_]*"    jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
grep -ho "remove(Property\.[A-Z_]*"      jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c

# censo das 134 linhas
grep -c "ExecutionContext" jca_android/*.mop | awk -F: '{s+=$2} END {print s}'

# nao houve deriva? (compara HEAD com o ponto de coleta original)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
git rev-parse --short HEAD    # esperado: bd61abea
git grep -ho "setProperty(Property\.[A-Z_]*" d27c48e9 -- 'rvsec/rvsec-mop/src/main/resources/jca_android/*.mop' \
  | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
```

### 5.2 O analisador estrutural das `.mop` (substitui regex)

Reconstrua um script Python que, para cada `.mop`: neutraliza comentários e literais de string
antes de varrer; casa chaves para delimitar corpos de evento e blocos `@handler`; casa parênteses
para delimitar `condition(...)`; localiza o bloco `fsm`/`ere` e coleta os identificadores nele; e
classifica cada sítio `validate`/`setProperty`/`remove` como `condition` / `body` / `@match` /
`@fail` / `other`. **Ele tem de tratar spec sem `fsm`/`ere` como forma legítima**, não como 100%
órfã.

Resultados a reproduzir:

```
jca_android   17 orfaos em 9 specs   validate: 27 (todos condition)   setProperty: 42 body / 7 handler   remove: 8 @fail / 1 body
jca           18 orfaos em 10 specs  (idem)
jca_android_bug_predicate  0 orfaos  validate: 56 (33 condition, 23 fora)
generic       1 orfao (FSM246.mop, event_2)
generic_new   17 specs SEM fsm/ere
```

### 5.3 O driver do `FSMCoenables`

```bash
W=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor
CP=$W/plugins_logicrepository/fsm/target/fsm-0.9.3-SNAPSHOT.jar
```

Escreva um `Drive.java` que monte um FSM de 6 estados com n símbolos, chame
`new FSMCoenables(start, events, states, categories, aliases, stateMap)` e some
`getCoenables()` por categoria — parametrizado por **n** e por **incluir ou não `State.get("fail")`
na lista de categorias**. Rode com `java -Xss1g`.

Esperado: com `fail`, a categoria produz exatamente `n·(2ⁿ−1)` (229.362 / 1.048.560 / 2.228.207 /
4.718.574 para n=14/16/17/18); sem `fail`, 10 entradas e 2 ms em qualquer n.

### 5.4 O teste de fumaça de tipo de parâmetro

```bash
JM=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/javamop/target/release/javamop/javamop
RM=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/target/release/rv-monitor

# uma spec minima de 2 eventos, variando so o tipo do parametro do meio
$JM/bin/javamop -s T.mop          # gera T.rvm e TMonitorAspect.aj
grep -m1 "^T(" T.rvm              # <- a lista de parametros sobreviveu?
$RM/bin/rv-monitor -merge T.rvm
grep -c "CachedWeakReference" TRuntimeMonitor.java   # 0 = monitor global, sem fatiamento
```

Matriz a reproduzir: `byte[]` e `int[]` → lista **vazia**; `Object[]`, `Object`, `String` →
preservada. Controle: `javamop/examples/agent/many/rvm/ere/SafeSyncMap.mop` preserva os três
parâmetros. **Acrescente `char[]`, que a auditoria não mediu.**

### 5.5 O venn do D1

```bash
AJ=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal
# o script canonico exige pandasql (ausente no .venv); reproduza o merge em pandas puro
sed -n '80,145p' $AJ/data-analysis/rvsec/rq1_rv_cc.py
```

Chave do venn: `(apk, class, method, spec)`. Política: `keep_default_na=False`, merge interno com
`cc_rv_mapping.csv`, descarte das regras None-mapeadas. Linha-base a reproduzir:
`RV=454, CC=423, both=112, só-RV=342, só-CC=311`.

Para o filtro api30, use as classes Java **reais**, não aproximação:

```bash
CORE=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/target/classes
# br.unb.cic.mop.jca.util.Api30CipherTransformationUtil.isValid(String)
# br.unb.cic.mop.jca.util.CipherTransformationUtil.isValid(String)
# br.unb.cic.mop.jca.util.ConscryptAliasTable.matches(String service, String observed, List<String> allow)
```

### 5.6 Build, gates e testes

```bash
# reator (JDK 21 no prefixo; ja buildou sob JDK 25 — trocar de JDK nao e pre-requisito)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests

# gates e harness da gh104
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
uv run python scripts/gh104_diff_harness.py --selftest
uv run pytest tests/parity/test_gh104_specset_gates.py --import-mode=importlib -o "addopts="
```

**Contrato de teste (obrigatório):** `uv run pytest <caminho> --import-mode=importlib -o "addopts="`.
Sem esses dois argumentos o isolamento de `conftest` quebra entre módulos e a coleta falha.

---

## 6. A auditoria de coerência do plano corrigido

As edições da primeira passada foram cirúrgicas. Verifique se o documento continua se sustentando:

- **§7.4 vs §7.5/§7.6.** A §7.4 ainda argumenta a favor do mecanismo B com a cadeia do IV como
  exemplo trabalhado; a §7.5 mostra que essa cadeia exata não compila. A §7.6 reconcilia — mas
  confirme que um leitor que leia na ordem não sai com a conclusão errada. **Pode ser necessário
  emendar a §7.4 no ponto onde ela apresenta a `IvChainSpec`.**
- **§4.2 (clonagem) vs §7.5.** A §4.2 declara que a limitação da clonagem é **neutra** entre os
  dois mecanismos. Isso continua verdadeiro. Mas agora existe uma assimetria real (a §7.5), e a
  §4.2 não a menciona. Confirme que o texto não induz o leitor a achar que **nada** distingue A
  de B.
- **As fases F0–F5.** F0 continua condicionada à decisão do mecanismo; F3 foi redimensionada para
  35; F5 ganhou o G-PARAM. Verifique se F1 e F2 continuam íntegras e se a ordem F0→F5 ainda faz
  sentido dado que o piloto mudou.
- **R1–R6 e D1–D4.** Cobrem tudo que o corpo levanta? A auditoria acrescentou o R6 e reformulou o
  D3 e o D4. Faltou risco para o mapeamento de alfabeto do G-ORDER — a auditoria o registrou como
  ausência e **não** o adicionou. Decida se entra.
- **A escada C1–C5 e a lógica de três valores.** A auditoria observou que os três valores mudam a
  assinatura de `validate()`, atingem os 27 sítios e o envelope da gh104, e que isso reforça o R1.
  Confirme que a §5 do plano diz isso com clareza suficiente para virar tarefa.
- **§8 (`rvsec-mop-defsuses`).** Os argumentos foram confirmados exceto um. Ver §7.

---

## 7. O que ficou aberto

| item | estado | o que falta |
|---|---|---|
| **R4 — `equals` das chaves concretas do Android** (`OpenSSLRSAPublicKey`, `BCRSAPublicKey`) | NÃO VERIFICÁVEL localmente | as classes não estão nos fontes locais; exige teste em dispositivo. Muda o veredito de `GENERATED_KEY`/`GENERATED_PUBLIC_KEY`. **Não gerencie emulador manualmente** — ver §8. |
| **Caminho absoluto no `main()` de `MOPSpecDefsUses`** (§8 do plano) | não localizado | as outras quatro alegações da §8 se confirmaram; esta ficou sem evidência. Confirme ou remova a afirmação do plano. |
| **`char[]` como parâmetro de spec** | inferido, não medido | ver §5.4. É o tipo do `PBEKeySpec`. |
| **A causa raiz do colapso de parâmetro** | não investigada | onde no `javamop` a lista é descartada? Há correção barata a montante? |
| **Onde nasce o OOM do gerador** | hipótese | ver §4.3. Item aberto de maior valor prático. |
| **O piloto da cadeia do IV** | recomendado, não executado | rodá-lo contra o harness diferencial é o que decide o D4 de fato, em vez de no papel. |
| **Reformulação do gate G-PRED** | consequência nova da decisão de §3.1-bis | o gate assevera preservação byte a byte do maquinário; quando `jca_android` chamar a classe nova, ele deixa de fazer sentido na forma atual. Dimensione o trabalho. |
| **Gate de disciplina de import** | proposto, não escrito | nenhuma spec `jca_android` pode importar a classe antiga. É verificação de uma linha e substitui a vigilância manual do R1. |
| **D1, D2, D3, D4** | decisões do pesquisador | não decida por ele; deixe os números prontos. |

---

## 8. Workflow — seguir rigorosamente

`docs/WORKFLOW.md` é a referência autoritativa. Regras que valem nesta sessão:

1. **Esta sessão é verificação, ainda Fase 0.** Não crie change OpenSpec, não crie issue, não edite
   `.mop`. O produto é o plano corrigido e o registro do que mudou.
2. **Se e quando a change for criada** (outra sessão): use **as skills OpenSpec via a ferramenta
   `Skill`** — `openspec-new-change`, `openspec-continue-change`, `openspec-propose`. **NUNCA** use
   `Write`/`Edit` para criar ou reescrever artefatos OpenSpec (`proposal.md`, `design.md`,
   `tasks.md`, deltas de spec). Isto é não-negociável e está no `CLAUDE.md`.
3. Convenção de nomes: `openspec/changes/gh<N>-<short-name>/`, `proposal.md` com
   `GitHub Issue: #N`, commits com `refs #N` durante o trabalho e `closes #N` no final.
4. **Nunca** adicionar `Co-Authored-By` a mensagem de commit. O usuário é o autor único.
5. **Nunca** iniciar, parar ou gerenciar emulador Android manualmente — em nenhum contexto. Se uma
   tarefa exigir emulador, use `rv-experiment run` ou `rv-platform run`.
6. Princípios P1–P4 do `CLAUDE.md` valem para tudo que for escrito: simplicidade, documentação
   narrativa e autocontida (explique o *porquê*), sem retrocompatibilidade (código morto é deletado
   com backup em `backup/`), comentários no estado presente.
7. Português com acentuação correta; código e comentários de código em inglês.
8. Tratamento: **você**, nunca "o senhor".

---

## 9. Aprendizados — as armadilhas que já custaram caro

As doze primeiras vêm do post-mortem da gh101 e da auditoria de 2026-08-08; estão na §6 do plano.
As três últimas vieram da primeira auditoria.

1. **Predicado nunca entra em `condition(...)`.** Guarda falsa não transita: o evento sai do
   autômato e a chamada seguinte é acusada de ordem. Leitura de `REQUIRES` vai no **corpo** do
   evento, reportando `UnsatisfiedConstraint`. Hoje 27 de 27 leituras estão do lado errado.
2. **Nunca declarar evento fora do `fsm`/`ere`** — o gerador lhe dá linha toda-`fail` e ele acusa
   duas vezes.
3. **Nunca adicionar leitura sem o produtor modelado no mesmo conjunto e na mesma tarefa** —
   `validate` de chave ausente devolve `false`, então leitor sem produtor acusa toda chamada
   conforme.
4. **Nunca consertar binding sem pôr o evento no autômato na mesma edição** — converte evento morto
   em acusador incondicional.
5. **Nunca mudar código Java compartilhado achando que o portão de congelamento cobre.** O gate do
   `jca` verifica `.mop`, não as classes que eles chamam. Foi assim que a correção de identidade
   entrou (`233df18a`) e teve de ser revertida três dias depois (`e204e2a4`). **Corolário: um
   substrato compartilhado não pode ter duas semânticas.**
6. **O alfabeto é recurso escasso, mas o teto não é 17** — é função da heap e, sobretudo, do
   `@fail`.
7. **Nunca ancorar um registro numa versão de regra diferente da que o conjunto usa** — a premissa
   "REQUIRES não varia entre versões" foi falsificada e invalidou vereditos inteiros.
8. **Nunca consertar conteúdo de spec enquanto o weaver apaga a categoria** — `UnsatisfiedConstraint`
   deu 0 em 97.018 eventos no caminho dexlib2 contra 43 no controle AspectJ.
9. **Nunca medir com instrumento agregado o que só um discriminante enxerga.** O `errors.csv`
   agregado **não** decide a hipótese dos acusadores órfãos; a tabela de transição gerada decide.
10. **"Reparar é caro" não implica "remover é barato"** — as duas afirmações precisam de medições
    distintas (é a própria D-11 da gh104).
11. **A tentativa falha não foi toda errada.** Dos 106 hunks: 51 de reparo de autômato com veredito
    `PROVADO`/`PASS`, ~21 de re-orçamento de alfabeto com `FID`, e 42 de fiação com `G7 FAIL`. Ela
    zerou os 18 acusadores órfãos. **Resgatar, não refazer.**
12. **Três oráculos antes de classificar um defeito.** A regra CrySL sozinha já inverteu dois
    diagnósticos; leia também o monitor gerado e o traço.
13. **[novo] Esta cadeia de ferramentas erra em silêncio, e o silêncio parece sucesso.** O JavaMOP
    apaga a lista de parâmetros e devolve `rc=0` com a mensagem de sucesso; o
    `LogicRepositoryConnector` faz `waitFor()` sem timeout, nunca consulta `getExitValue()` e
    concatena stderr ao stdout. **Inspecione o artefato gerado, nunca o código de saída.**
14. **[novo] Um piloto que só sabe passar não decide nada.** O piloto `Mac`/`Key` proposto era de
    tipos-objeto — passaria, e não teria dito nada sobre a família `byte[]`, que é a maioria das
    leituras vivas. Escolha o piloto pelo caso difícil.
15. **[novo] Confira a unidade, não só o número.** "19 arestas" era 19 *predicados*; o trabalho
    real é de 35 pares. Um número certo na unidade errada subdimensiona uma fase pela metade.

---

## 10. Arquivos relacionados

### O plano, a auditoria e este handoff
```
docs/20260820_plano_fiacao_predicados.md              ← o objeto (corrigido, ~1.054 linhas)
docs/20260820_auditoria_plano_predicados.md           ← a primeira passada (550 linhas)
docs/20260820_handoff_verificacao_plano_predicados.md ← o handoff da primeira passada
docs/20260820_handoff_verificacao_plano_predicados_v2.md ← este arquivo
```

### As specs (mesmo repo, subárvore `rvsec/`)
```
../rvsec/rvsec-mop/src/main/resources/jca_android/                ← alvo, 23 .mop + codes.csv
../rvsec/rvsec-mop/src/main/resources/jca/                        ← congelado
../rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/  ← tentativa falha, arquivada
../rvsec/rvsec-mop/src/main/resources/generic/                    ← 118 .mop, teste de genericidade
../rvsec/rvsec-mop/src/main/resources/generic_new/                ← 27 .mop, 17 sem automato
```

### O substrato Java
```
../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java
../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java
../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorType.java
../rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/   ← Api30CipherTransformationUtil, ConscryptAliasTable
../rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java
```

### O instrumento da gh104
```
scripts/gh104_diff_harness.py    scripts/gh104_gates.py       scripts/gh104_message_gate.py
scripts/gh104_mop_lint.py        scripts/gh104_baseline.py    scripts/gh104_regen_diff.py
data/gh104/traces/               data/gh104/evidence/         data/gh104/definitions.md
data/jca_android/                ← conformance_record.csv (74), constraint_table.csv (60),
                                   divergence_record.csv, alias_table.csv, gate_allowlist.csv, README.md
tests/parity/test_gh104_specset_gates.py
tests/parity/test_gh104_structural_gates.py
```

### Evidência de primeira mão já usada
```
results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java
   Prop_1_event_i2 (o `return false` da guarda, :3713)
   Prop_1_transition_reset[] = {4,4,4,4,4} e Category_fail = nextstate == 4
   Prop_1_transition_next2[] = {3,3,1,3} contra next1[] = {3,1,1,3}
```

### A change antecessora
```
openspec/changes/gh104-legible-violation-reports/{proposal.md,design.md,tasks.md,tasks/,specs/}
openspec/changes/archive/2026-08-16-gh101-jca-spec-conformance/
openspec/changes/archive/2026-08-06-gh99-metacrysl-jca-android/
openspec/changes/gh100-weaver-emission-fidelity/
audit/20260808_validacao_jca_android/   ← a auditoria que reprovou a tentativa falha
data/gh101/                             ← divergence_record.csv, predicate_edges.csv, README.md
```

### Oráculos e ferramentas externas
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/
   MetaCrySL/generated/api30/*.cryptsl        ← ORÁCULO: 33 regras (54 ENSURES, 36 REQUIRES, 2 NEGATES, 32 predicados)
   CryptoAnalysis/                            ← o analisador, geração ANTIGA (349073ff, 2026-07-25)
      .../analysis/AnalysisSeedWithSpecification.java   ← doPredsMatch :475, trackedTypes :563
      .../constraints/ConstraintSolver.java             ← ImpreciseValueExtractionError :174, :484
      CryptoAnalysis-Android/.../CogniCryptAndroidAnalysis.java  ← run() com runCryptoAnalysis() comentado
   rvsec/javamop/                             ← parser e gerador de aspecto
      examples/agent/many/rvm/ere/SafeSyncMap.mop       ← exemplo multiparâmetro canônico
   rvsec/rv-monitor/                          ← gerador + rv-monitor-rt
      plugins_logicrepository/fsm/.../FSMCoenables.java
      rv-monitor/.../logicclient/LogicRepositoryConnector.java   ← :151 -Xss1g, :223 waitFor
      rv-monitor/.../output/EnableSet.java                       ← :121-125 noopt1
      rv-monitor-rt/.../ref/CachedWeakReference.java             ← :16 identityHashCode
      rv-monitor-rt/.../tablebase/WeakRefHashTable.java          ← :474 key == this.ref
   ase-journal/                               ← o artigo e o dataset publicado
      dataset/results/errors.csv              ← 97.018 eventos
      data-analysis/rvsec/rq1_rv_cc.py        ← o join do venn
/home/pedro/tmp/CryptSL/                      ← a LINGUAGEM CrySL (gramática Xtext; Order em :99-134)
```

### O experimento de validação (das duas changes)
```
experimento-gh104/CONTEXTO.md   ← ponto de entrada
experimento-gh104/PRONTIDAO.md  experimento-gh104/README.md
```

### Documentação de arquitetura
```
docs/architecture/monitor-generation.md   docs/architecture/instrumentation-java.md
docs/WORKFLOW.md   .claude/AGENTS.md   .claude/project-info.md   CLAUDE.md
```

---

## 11. Produto desta sessão

1. **Registro da segunda passada** — uma linha por alegação reexaminada, com veredito
   (`SUSTENTADO` / `REVERTIDO` / `REFINADO` / `AINDA ABERTO`) e a evidência. Sugestão de caminho:
   `docs/20260820_verificacao_plano_predicados_v2.md`. Se a segunda passada reverter algo da
   primeira, **diga qual e por quê** — a auditoria anterior é um documento vivo, não uma lápide.
2. **O plano ainda mais correto** — edições diretas em `docs/20260820_plano_fiacao_predicados.md`,
   mantendo a convenção da marca `[auditado]`.
3. **Os itens de §7 fechados** — os que forem fecháveis sem dispositivo e sem implementar.
4. **Uma recomendação sobre o D4** fundamentada, se o piloto da cadeia do IV for executado.

**Não** crie issue nem change. **Não** implemente o Grupo 10 da gh104. **Não** toque em `jca/`,
`generic/`, `generic_new/` nem `jca_android_bug_predicate/`.
