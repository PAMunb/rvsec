# Handoff — análise rigorosa do plano de mensagens JavaMOP

**Data de origem:** 2026-08-15
**Objetivo desta sessão:** submeter o plano `docs/20260815_javamop_mensagens.md` a uma análise
rigorosa e adversarial. **Não implementar nada.**

---

## 1. O que estamos fazendo

O RVSEC reporta violações de runtime verification que um humano não consegue ler. No dataset de
referência (`ase-journal/dataset/results/errors.csv`, 97.018 linhas), **72,93% das mensagens são a
literal `unknown`**, e existem apenas **19 mensagens distintas** no corpus inteiro.

Na sessão anterior foi feita a investigação de causa raiz (sete subagentes, tudo verificado no
fonte com `arquivo:linha`) e escrito um plano de remediação. **O alvo é a próxima campanha
experimental, não o artigo** — o `ase-journal` foi usado apenas como medida do problema, e nada nele
deve ser revisado.

Esta sessão deve **criticar o plano**, não executá-lo.

---

## 2. O que já foi feito

### 2.1 Artefato principal

`docs/20260815_javamop_mensagens.md` (~600 linhas, em inglês). Estrutura:

| Seção | Conteúdo |
|---|---|
| §1 | O achado em uma página |
| §2 | Base de evidência — toda medida, não estimada |
| §3 | Análise de causa raiz em sete camadas (L1–L7) |
| §4 | O que um relatório acionável precisa conter (Q1–Q5), comparado ao CogniCrypt/CrySL |
| §5 | O plano — oito workstreams (WS-1..WS-8), sequenciados em Fases A/B/C |
| §6 | Oito decisões do pesquisador (D-1..D-8) |
| §7 | Critérios de aceitação para a próxima campanha |
| §8 | Registro de 50 defeitos (D01–D50) com `arquivo:linha` e severidade A/B/C |
| §9 | As quatro afirmações marcadas `[inferred]` — não lidas diretamente no fonte |

### 2.2 Achados centrais que o plano sustenta

1. **L1 — construtor mudo.** `ErrorDescription.java:34-36`: o construtor de 3 args grava o literal
   `"unknown"`. Todos os 21 `@fail` do `jca` e do `jca_android` usam esse construtor. Nenhum sítio
   no repositório emite `InvalidSequenceOfMethodCalls` **com** mensagem. A equivalência é perfeita
   nos dois sentidos.

2. **L2 — evento órfão (a causa do volume).** O gerador constrói função de transição **total** com
   sumidouro explícito (`fsm/JavaFSM.java:158`, `ere/FSM.java:52-58`, `fsm/FSMMin.java:24-28,53-55`).
   Todo evento declarado e ausente do bloco `fsm:`/`ere:` cai no sumidouro. São **18 eventos**
   criados só para reportar um erro específico → cada violação emite um par: informativo + mudo mal
   classificado. Medido: **27,0% do CSV inteiro é duplicata-sombra**; em `TrustManagerFactorySpec`,
   1.733 de 1.748 sítios têm contagem idêntica dos dois tipos.

3. **L3 — `REQUIRES` como `condition()` de pointcut.** Condição falsa **descarta o evento**
   (`BaseMonitor.java:604-610`), abre um buraco no traço, e a FSM interpreta o buraco como erro de
   ordem. Predicado faltando vira "sequência inválida". 18 de 24 `Property` são escritas e nunca
   lidas.

4. **L4 — não existe verificação de fim de traço.** `IncompleteOperationError` do CrySL não colapsa
   no balde mudo: **não existe**. `grep` por `@end`/`__END` no `jca/` retorna zero.

5. **L5 — localização.** `__LOC` é substituição textual para `ViolationRecorder.getLineOfCode()`,
   que descarta N−1 frames. 73,4%–88% dos erros caem em biblioteca — **política de escopo, não bug**
   (`DescriptorWriter.java:233-249` tem doze prefixos, nenhum cobrindo `android`/`kotlin`/`com.google`/
   `okhttp3`). E `RegisterShifter.cloneInstructions` (`:174-267`) destrói toda a debug info dos
   métodos que clona.

6. **L6 — identidade.** A mensagem está fora de `equals/hashCode` (`ErrorSummary.java:73-120`), então
   **um registro mudo que chegue primeiro suprime permanentemente o informativo** no mesmo sítio.

7. **L7 — o parser fabrica campos.** `logcat_parser.py:305-316` e `:366-368` gravam
   `error_type := spec` e `source := "Unknown Source:1"` como se fossem dados reais.

8. **A alavanca que torna o plano barato:** no `@fail`, o monitor tem em escopo `Prop_N_state`,
   `RVM_lastevent`, as tabelas `Prop_N_transition_<ev>[]` (das quais os eventos legais são deriváveis
   por indexação) e o objeto monitorado. O corpo do `@fail` é **inlinado verbatim** num método de
   instância da mesma classe — logo Java escrito no `.mop` alcança esses campos **sem mexer no
   gerador**. Sete dos 21 handlers já leem esses campos na linha seguinte ao `addError` mudo.

### 2.3 Duas correções feitas durante a investigação (não repetir os erros)

- **O artigo NÃO usa `unique_msg`.** `grep` em todos os `.tex` dá zero. A chave publicada é
  `(apk, class, method, spec)`, que descarta `message` **e** `error_type`. Nenhum número publicado
  quebra por causa do `unknown`. Não propor retificação do artigo.
- **A tese "as specs genéricas não têm certos campos, por isso as planilhas não têm certas colunas"
  está direcionalmente certa mas o mecanismo é outro.** `RvErrorLog` sempre teve os seis campos; a
  convergência acontece no **parser**, e é coerciva — ele fabrica, não omite. As duas colunas
  ausentes têm causas separadas e nenhuma é a `generic`: `source` foi acrescentada em `cf234788`
  (2026-07-28, posterior ao experimento) e já está no escritor atual
  (`result_processor.py:562-576`, 11 colunas); `error_type` nunca foi coluna em escritor nenhum.

---

## 3. O que esta sessão deve fazer

**Análise rigorosa e adversarial do plano.** O plano foi escrito pela mesma sessão que fez a
investigação — logo carrega o viés de quem produziu as evidências. O trabalho aqui é tentar
derrubá-lo.

### 3.1 Eixos obrigatórios da crítica

**A. Verificação factual.** O plano cita ~120 referências `arquivo:linha`. Amostrar e **verificar
abrindo o fonte**, com prioridade nas que sustentam decisões:
- `ErrorDescription.java:34-36` (L1)
- `fsm/JavaFSM.java:158`, `ere/FSM.java:52-58`, `fsm/FSMMin.java:24-28,53-55` (L2 — a semântica do
  sumidouro é o pilar do plano inteiro)
- `BaseMonitor.java:604-610` (L3), `:428-453` (ordem de disparo), `:786` vs `:951-973` (o `__RESET`
  não limpa variáveis de spec)
- `RegisterShifter.java:174-267` (L5c)
- `DescriptorWriter.java:233-249` (L5b)
- `ErrorSummary.java:73-120` (L6)
- Os três pointcuts que nunca casam: `SignatureSpec.mop:99,106`, `TrustManagerFactorySpec.mop:62`,
  contra o aspecto gerado `.aj:979,984,1037`

**B. As quatro afirmações `[inferred]` (§9).** São o ponto mais frágil. Resolver cada uma:
1. Qual caminho de tecelagem produz as 8.371 linhas com valor observado vazio em
   `TrustManagerFactorySpec`? O mecanismo (`currentAlgorithmInstance` inicial `""` + evento de
   criação implícito) está verificado; o caminho específico não.
2. Uma declaração `static final String[]` escrita no bloco de declarações de um `.mop` sobrevive à
   emissão do gerador? (WS-1.3 depende disso.)
3. Volume estimado do WS-4 (`IncompleteOperationError`) no Android — não existe medida.
4. Re-habilitar `RVM_loc` (WS-5.8) ainda funciona? O código está comentado em cinco arquivos.

**C. Crítica do desenho, não só dos fatos.** Perguntas que a análise deve responder:
- A Fase A realmente entrega o que promete **sem tocar em infraestrutura compartilhada**? Há alguma
  dependência oculta de WS-1/WS-2/WS-3 no `rv-monitor` ou no `rvsec-core`?
- O sequenciamento WS-7 → WS-2 → WS-1 → WS-3 está certo? Há ordem melhor? Alguma dependência
  invertida?
- WS-2 (dar transição aos eventos órfãos) muda a semântica medida. A alternativa — **remover** os
  eventos órfãos do alfabeto em vez de lhes dar transição — foi considerada? Qual é melhor e por quê?
- WS-1 propõe compor a mensagem no `.mop` (tabelas escritas à mão) em vez de no gerador. Isso
  duplica ~23 tabelas por conjunto × 4 conjuntos. É a escolha certa, ou o custo de manutenção
  supera o risco de mexer no gerador?
- WS-6.1 (incluir a mensagem na identidade) **aumenta** o volume do CSV, enquanto WS-2 o reduz. Os
  dois efeitos foram compostos, ou o plano os trata isoladamente?
- Os critérios de aceitação (§7) são todos verificáveis? Algum é inverificável na prática?
- Falta algum workstream? Em particular: performance (o `new Exception()` por violação sob o lock
  global), e o comportamento sob reinício de processo.

**D. Riscos não tratados.** Procurar o que o plano não viu. Candidatos a investigar:
- Efeito das mudanças sobre o `aperv-tool` e a camada de análise (`gh103-campaign-analysis-layer`),
  que consome `errors.csv`.
- Efeito sobre invariantes já registrados nos specs OpenSpec (`openspec/specs/`).
- Se mudar a mensagem quebra `experimento-cal` ou outros consumidores.

**E. Proporcionalidade.** O plano tem 8 workstreams e 50 defeitos. Isso é executável? Qual é o
subconjunto mínimo que torna a próxima campanha defensável? O plano deveria recomendar um corte, e
não recomenda.

### 3.2 Formato da entrega

Escrever a análise em `docs/20260815_javamop_mensagens_analise.md`, **em inglês** (para casar com o
plano analisado), contendo no mínimo:
- Veredito por seção do plano (confirmado / impreciso / errado / incompleto), com evidência.
- Lista de correções necessárias ao plano, com `arquivo:linha`.
- Resolução das quatro afirmações `[inferred]`.
- Recomendação de recorte mínimo e de sequenciamento revisado.
- Riscos que o plano não cobre.

**Não editar** `docs/20260815_javamop_mensagens.md` sem autorização explícita. A análise é um
artefato separado; se o plano precisar mudar, propor as mudanças e perguntar.

---

## 4. Arquivos relacionados

### Plano e evidência
| Caminho | Papel |
|---|---|
| `rv-android/docs/20260815_javamop_mensagens.md` | **o plano a ser analisado** |
| `ase-journal/dataset/results/errors.csv` | 97.018 linhas — a evidência. Somente leitura |

### Especificações
| Caminho | Papel |
|---|---|
| `rvsec/rvsec-mop/src/main/resources/jca/` | 23 `.mop` — conjunto do experimento |
| `rvsec/rvsec-mop/src/main/resources/jca_android/` | 23 `.mop` — variante Android, com os reparos |
| `rvsec/rvsec-mop/src/main/resources/generic/` | 118 `.mop` — `Log.v` direto, sem `ErrorCollector` |
| `rvsec/rvsec-mop/src/main/resources/generic_new/` | 27 `.mop` — em construção, mensagens boas |
| `Crypto-API-Rules/JavaCryptographicArchitecture/` | 48 regras CrySL — o ground truth da tradução |
| `CryptoAnalysis/CryptoAnalysis/src/main/java/crypto/analysis/errors/` | as categorias de erro do CogniCrypt |

### Runtime e geração
| Caminho | Papel |
|---|---|
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/` | `ErrorDescription`, `ErrorSummary`, `ErrorType` |
| `rvsec/rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java` | emissor Android (sem escaping) |
| `rvsec/rvsec-logger-csv/.../ErrorCollector.java` | emissor JSE (com escaping) — a referência canônica |
| `rv-monitor/rv-monitor-rt/.../ViolationRecorder.java` | `getLineOfCode()` |
| `rv-monitor/rv-monitor/.../output/monitor/` | `BaseMonitor`, `RawMonitor`, `SuffixMonitor`, `HandlerMethod` |
| `rv-monitor/rv-monitor/.../logicpluginshells/fsm/` e `.../ere/` | `JavaFSM`, `FSMMin`, `EREPlugin`, `FSM` |
| `javamop/src/main/java/javamop/output/descriptor/DescriptorWriter.java` | `commonPointcut` e a lista `notwithin` |

### Instrumentação e pipeline
| Caminho | Papel |
|---|---|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` | weaver DEX-nativo (`DexWeaver`, `RegisterShifter`, `CoverageWeaver`, `WrapperEmitter`) |
| `rv-android/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` | os três formatos de parsing |
| `rv-android/modules/rv-android-core/src/rv_android_core/domain/log.py` | `RvErrorLog`, `unique_msg` |
| `rv-android/modules/rv-platform/src/rv_platform/components/result_processor.py` | escritor do `errors.csv` (11 colunas) |

### Artefatos gerados (oráculos do que o gerador emite)
| Caminho |
|---|
| `rv-android/results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java` |
| `rv-android/results/gh99_jca_android_monitors/monitors/MultiSpec_1MonitorAspect.json` |
| `rv-android/results/gh101_group8_jca_android/monitors/MultiSpec_1MonitorAspect.aj` |

---

## 5. Comandos úteis

```bash
# Distribuição de mensagens e tipos no CSV de referência
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('errors.csv')))
print(len(rows), 'linhas')
print(collections.Counter(r['message'] for r in rows).most_common(5))
print(collections.Counter(r['unique_msg'].split(':::')[3] for r in rows))
"

# Sítios addError de 3 args (mudos) vs 4 args
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
grep -c 'addError' jca/*.mop | sort -t: -k2 -rn | head

# Eventos declarados vs eventos usados na FSM/ERE de uma spec
sed -n '/^ *\(fsm\|ere\) *:/,/^ *\(alias\|@\)/p' jca/SecureRandomSpec.mop

# Tabelas de transição no monitor gerado (a semântica do sumidouro)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/gh99_jca_android_monitors/monitors
grep -n 'static final int Prop_1_transition' MultiSpec_1RuntimeMonitor.java | head -20

# Testes (contrato de CI — sem estas flags a coleta quebra)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
uv run pytest --import-mode=importlib -o "addopts=" modules/<modulo>/tests
```

---

## 6. Aprendizados e armadilhas

1. **`@fail` não é "evento sem transição".** É estado. `Category_fail = (Prop_N_state == <sumidouro>)`,
   avaliado após **todo** evento. Quem raciocinar como "evento ilegal" erra a análise.

2. **`__RESET` não limpa variáveis de spec.** `HandlerMethod.java:39` mapeia para `this.reset()`, e o
   `reset()` gerado (`BaseMonitor.java:951-973`) reemite `localDeclaration` mas **não**
   `monitorDeclaration` (emitido uma só vez em `:786`). `currentAlgorithmInstance` sobrevive. Isso já
   foi hipótese descartada uma vez — não refazer.

3. **O corpo do evento roda ANTES da transição e do cálculo de categoria**
   (`BaseMonitor.java:428-453`). É isso que torna o duplo relato determinístico: informativo primeiro,
   mudo depois.

4. **Verificar o código antes de afirmar mecanismo.** Handoff, relatório de subagente e aritmética
   não são verificação. Abrir o fonte e citar `arquivo:linha`. Vários relatórios desta investigação
   contêm afirmações fortes — tratá-las como hipóteses a confirmar, não como fato.

5. **Não mexer no artigo.** O `ase-journal` é evidência, não alvo.

6. **Geração de monitores não é paralelizável** — o JavaMOP estagia `.rvm` no diretório de specs
   compartilhado. Não disparar gerações concorrentes.

7. **`/tmp` é tmpfs nesta máquina** (62 GiB em RAM). Usar o scratchpad da sessão ou exportar
   `TMPDIR` para `/pedro` em qualquer coisa pesada.

8. **NUNCA gerenciar emuladores manualmente.** Regra permanente do `CLAUDE.md`. Se a análise sugerir
   validação em dispositivo, ela é feita via `rv-experiment run` / `rv-platform run` — e provavelmente
   está fora do escopo desta sessão, que é de análise.

9. **Granularidade é `(classe, método)`, nunca assinatura** — o runtime usa `StackTraceElement` sem
   descritor. Sobrecargas não são distinguidas, e o artigo já declara isso como limitação.

---

## 7. Workflow — seguir rigorosamente

- **`docs/WORKFLOW.md`** é a referência de processo. **`.claude/AGENTS.md`** documenta skills e
  orquestradores. **`.claude/project-info.md`** tem caminhos, variáveis de ambiente e comandos.
- **Princípios P1–P4 do `CLAUDE.md` são inegociáveis**: P1 simplicidade, P2 documentação narrativa e
  autocontida (explicar o *porquê*), P3 sem retrocompatibilidade (código morto é deletado, com backup
  em `backup/`), P4 comentários descrevem o estado atual.
- **Se esta análise levar a uma mudança de código, ela vira uma change OpenSpec** —
  `openspec/changes/gh<N>-<nome-curto>/` — e os artefatos são criados **exclusivamente pelas skills**
  (`Skill` tool: `openspec-new-change`, `openspec-propose`, `openspec-continue-change`, etc.).
  **Nunca escrever `proposal.md`/`design.md`/`tasks.md` com `Write`/`Edit` diretamente.** Esta regra
  sobrepõe qualquer outro instinto.
- Convenção de referência cruzada: diretório `gh<N>-<nome>` sem prefixo de data; `proposal.md` com
  `GitHub Issue: #N`; commits com `refs #N` durante o trabalho e `closes #N` no final.
- **Commits: nunca adicionar `Co-Authored-By` nem qualquer trailer de coautoria.** O usuário é o
  único autor.
- Português do Brasil sempre com acentuação correta. Código e comentários em inglês.
- Changes OpenSpec ativas que podem colidir com este trabalho: `gh103-campaign-analysis-layer`,
  `gh102-artifact-scoped-parse`, `gh101-jca-spec-conformance`, `gh100-weaver-emission-fidelity`.
  Verificar antes de propor qualquer coisa nova.

---

## 8. Primeiro passo sugerido

1. Ler `docs/20260815_javamop_mensagens.md` inteiro.
2. Ler `docs/WORKFLOW.md` e `.claude/AGENTS.md`.
3. Verificar, abrindo o fonte, o pilar do plano: a semântica do sumidouro da FSM
   (`fsm/JavaFSM.java:158` + `ere/FSM.java:52-58` + `fsm/FSMMin.java:24-28,53-55`) e a inlinação
   verbatim do corpo do `@fail` no monitor gerado.
4. Se esse pilar cair, o plano inteiro precisa ser reescrito — reportar imediatamente antes de
   continuar.
5. Só então avançar para os demais eixos da §3.1.
