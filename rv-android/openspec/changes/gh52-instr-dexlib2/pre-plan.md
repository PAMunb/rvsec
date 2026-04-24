# Pre-Plan — gh52-instr-dexlib2

> **Phase 0 (Ideação) do SDD** — documento técnico que alimenta os artefatos formais (proposal/specs/design/tasks). Após aprovação, mover para `rv-android/openspec/changes/gh52-instr-dexlib2/pre-plan.md` junto aos demais artefatos da change.

| Campo | Valor |
|---|---|
| Change name | `gh52-instr-dexlib2` |
| Issue | #52 (a ser criado — Feature template) |
| Track | **Full SDD** (multi-módulo, decisão arquitetural) |
| Branch | `gh52-instr-dexlib2` saindo de **`modules`**, remota desde dia 1 |
| Spec primário afetado | `openspec/specs/instrumentation/spec.md` |
| Specs secundários potencialmente afetados | `core` (se App/Task ganhar campo `instr_variant`), `experiment` (variant flag), `platform` (deploy path) |
| Data | 2026-04-24 |
| Deadline da defesa | 2026-04-13 (já passou — finalização em #48) |

---

## 1. Contexto

### O que mudou

A pipeline atual de instrumentação (`rv-instrumentation`) executa um round-trip lossy `APK → dex2jar → ajc → d8 → APK assinado`. Em 2026-04 descobriu-se que esse round-trip é **estruturalmente irreparável** para APKs Kotlin/R8 modernos:

- **Causa raiz**: JVMS §4.10.1.9 type-consistency proíbe expressar idiomas DEX otimizados pelo R8 (class-inlining, horizontal/vertical class merging, lambda merging, enum unboxing, constructor outlining, staticizer, nest-based access). dex2jar resolve colapsando tipos (`Sub` vira `Parent` no `new`/`<init>`), o que produz `iput Sub.field` sobre referência `Parent` — `VerifyError` no boot.
- **Impacto empírico**: 63.6% dos APKs do JCA-400 têm 0% de cobertura em runtime (apesar de 74.5% de "pipeline success"). Documentado em `docs/20260421_problema_dex2jar.md` §3-5.
- **Tentativa de remediação por flags ajc/d8 (gh50)** mitigou parte mas não resolve a impossibilidade de expressar o padrão R8 em JVM bytecode. gh50 é band-aid; gh52 é a correção arquitetural.

### Por que esta mudança importa

1. **Recuperar dataset**: ~30-40% dos APKs hoje "falham silenciosamente" passariam a emitir eventos. Isto eleva o N efetivo do estudo experimental de ~188 para ~270+.
2. **Defensa do paper**: revisores cobrarão evidência rigorosa de que a substituição **preserva semântica** (toda construção AspectJ usada em produção tem equivalente DEX provado). Pipeline atual já é defensável; a nova precisa atingir o mesmo nível ou superior.
3. **Eliminar dependências frágeis**: dex2jar/jar2dex/ajc são ferramentas estagnadas (último plugin AspectJ+Gradle moderno: 2022). dexlib2 é mantido (versão 3.0.8).
4. **Performance**: weaving DEX-nativo elimina ~60-180s de round-trip por APK. Estimativa: 10-30s/APK no novo pipeline.

### O que já existe (insumo de Phase 0)

| Artefato | Localização | Status |
|---|---|---|
| Diagnóstico do problema | `docs/20260421_problema_dex2jar.md` | Completo |
| Investigação LSPatch (rejeitado) | `docs/20260422_lspatch.md` | Completo (gap Coverage.aj não escala) |
| Investigação JavaMOP descritor | `docs/20260423_javamop.md` | Completo + implementado |
| Plano do protótipo | `docs/20260423_plano_prototipo.md` | Completo |
| Plano de validação rigorosa | `docs/20260423_plano_validacao.md` | Completo (6-layer framework) |
| **Protótipo funcional** | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/prototipo-dexlib2` | Validado E2E em 2 APKs (cryptoapp + hateitorrateit) |
| **Patch JavaMOP `--emit-descriptor`** | branch `emit-descriptor` em `rvsec/javamop/` | Commit 79547700, ainda não pushed |

O protótipo prova a tese central: **ajc crasha imediato em SDK ≥ 36; dexlib2 boota e emite eventos**. cryptoapp: 7 eventos byte-exatos. hateitorrateit (Kotlin/R8 obfuscado): 4342 eventos RVSEC-COV em 30s. Zero VerifyError em ambos.

---

## 2. Escopo da change

### Em escopo

1. **Novo módulo Maven multi-módulo**: `rv-android/modules/rv-instrumentation-dexlib2/` (Java) — graduação refatorada do protótipo.
2. **Wrapper Python**: novo módulo `rv-android/modules/rv-instrumentation-dexlib2-py/` com classe `DexlibInstrumentation` que honra contrato `instrument_apks(apks_dir, results_dir) → InstrumentationResults` (mesma assinatura usada hoje por rv-experiment).
3. **Variant flag em `rv-experiment`**: `--instrumentation-variant ajc|dexlib2` (default `ajc` enquanto valida; vira `dexlib2` após Layer 4 ratificada).
4. **Patch JavaMOP `--emit-descriptor`** integrado ao build oficial do `rvsec/javamop`. Commit 79547700 promovido + documentado.
5. **Validation harness** como módulo Maven `validator/` dentro do novo módulo: BaksmaliDiffer, TraceComparator, FeatureMappingChecker, ConstructionInventoryGenerator.
6. **Documentos rigor-paper**:
   - `docs/AJ_CONSTRUCTIONS_INVENTORY.md` — toda construção AspectJ usada em produção (JCA + generic_new + custom aspects), com file:line.
   - `docs/AJ_TO_DEXLIB2_MAPPING.md` — tabela 1:1 construção → componente/função/smali pattern; gaps explícitos.
   - `docs/LIMITATIONS.md` — features AspectJ não suportadas (around, cflow, handler, get/set) com defesa por inventário ("0 usos no nosso domínio").
7. **Re-execução do dataset JCA-400** com baseline ajc vs dexlib2 (Layer 4 do plano de validação), análise estatística (Mann-Whitney U, F1 ≥ 0.98, recovery rate ≥ 90%).
8. **Atualização de `openspec/specs/instrumentation/spec.md`** com novos FRs/INVs cobrindo o pipeline DEX-nativo (não substitui FRs antigos enquanto coexistir; após substituição, FRs antigos viram REMOVED).
9. **Quarentena do `rv-instrumentation` antigo** após Layer 4 ratificada: mover para `backup/2026-MM-DD-rv-instrumentation-ajc/` (P3).
10. **Patch JavaMOP `--emit-descriptor` pushed remoto** (branch `emit-descriptor` → mergeada em `master` do rvsec ou mantida como integration branch da gh52 — decisão técnica em Phase 2).

### Fora de escopo

- LSPatch / Xposed (rejeitado em `docs/20260422_lspatch.md`, gap Coverage.aj).
- Source-build de APKs F-Droid (gray-box, deferido para post-defesa).
- Otimização de estratégia de exploração UI (orthogonal, em `docs/20260421_exploration_strategy_analysis.md`).
- Suporte a `around()`, `cflow()`, `cflowbelow()`, `handler()`, `get()`/`set()` (0 usos confirmados em todo o conjunto de specs do RVSEC; documentado em `LIMITATIONS.md`).
- Reformulação de `rv-monitor-generator` (continua gerando .aj + .java; .aj agora **somente** consumido pelo pipeline ajc legado durante coexistência; descritor JSON usado pelo dexlib2).

### Restrições / não-negociáveis

- **Contrato Python público estável**: `RVInstrumentation.instrument_apks(apks_dir, results_dir) → InstrumentationResults` deve continuar funcionando para rv-experiment sem mudanças. (Variant flag muda implementação por baixo, não API.)
- **Coverage.aj catch-all** preservado: instrumentar 100% de métodos de app code; filtros canônicos idênticos aos atuais.
- **Specs do JavaMOP** continuam sendo a única fonte de verdade da semântica de monitoramento. dexlib2 NÃO interpreta semântica do monitor, apenas **transporta eventos** para `MultiSpec_*RuntimeMonitor`.
- **Reprodutibilidade**: mesma APK + mesmo descritor → mesmo APK woven (determinismo). dexlib2 preserva splits multidex de entrada.
- **Sem dependência de LSPatch / Xposed** no APK final (APK woven é auto-contido, igual ao pipeline atual).

---

## 3. Estratégia de Branch

```
modules (origem, remota)
   │
   └── gh52-instr-dexlib2 (criada, remota desde dia 1)
         ├── commits Phase 1-5 (Explore → Implement)
         ├── push frequente para origin/gh52-instr-dexlib2
         └── PR final → modules (após Layer 4 ratificada)
```

- Branch criada **a partir de `modules`** (não master). Justificativa: o módulo novo encaixa no esquema `modules/` que já vive na branch modules.
- Nome: `gh52-instr-dexlib2` (segue convenção das mudanças anteriores: `gh48-`, `gh50-`, `gh51-`).
- Push remoto desde o primeiro commit (`git push -u origin gh52-instr-dexlib2`).
- Patch do JavaMOP (`emit-descriptor` em rvsec): decidir em Phase 2 entre (a) merge em master do rvsec antes da gh52 começar, ou (b) manter como branch separada e gh52 referenciá-la como dependência. Recomendação preliminar: **(a)** — JavaMOP é dependência upstream estável; o patch é não-invasivo (adiciona uma flag).
- Protótipo `prototipo-dexlib2` (workspace-rv level) **NÃO** é mergeado. Ele é **insumo**: código relevante é refatorado/reescrito conforme arquitetura nova (§4) e copiado linha a linha onde fizer sentido. Após gh52 archived, prototipo-dexlib2 é arquivado em `backup/2026-MM-DD-prototipo-dexlib2/` ou removido (decisão pós-archive).

---

## 4. Arquitetura proposta — `rv-instrumentation-dexlib2`

A arquitetura a seguir **refatora** o protótipo (que colapsava muitas responsabilidades em `DexWeaver`). Componentes com fronteiras claras, contratos explícitos, testáveis isoladamente.

### 4.1 Decomposição de módulos Maven

```
rv-android/modules/rv-instrumentation-dexlib2/         ← multi-module Maven parent
│
├── descriptor-reader/         ← POJO + Jackson (ZERO lógica de weaving)
│   └── domain: AspectDescriptor, AdviceDescriptor, MonitorCallDescriptor,
│               PointcutExpression (interface) + variantes (CallPC, ExecutionPC,
│               ArgsPC, TargetPC, NotWithinPC, CombinedPC, IfPC, StaticInitPC)
│
├── pointcut-engine/           ← matching: descriptor → DEX targets
│   ├── PointcutExpressionParser   (string → AST tipado)
│   ├── PointcutMatcher            (AST + DEX class/method → Match? + arg bindings)
│   ├── TypeResolver               (simple name + imports → DEX descriptor)
│   ├── AndroidClassIndex          (ASM index de android.jar para overload expansion)
│   └── InheritanceResolver        (X+ semântica via android.jar + classes do APK)
│
├── advice-emitter/            ← gera "instructions a injetar" por tipo de advice
│   ├── AdviceEmitter (interface)
│   ├── BeforeEmitter, AfterEmitter, AfterReturningEmitter, AfterThrowingEmitter
│   ├── StaticInitializationEmitter   (NEW — injeta hook em <clinit>)
│   ├── IfGuardEmitter                (NEW — if-eqz antes do invoke-static)
│   ├── ThisJoinPointEmitter          (NEW — pré-computa string getSignature)
│   └── WrapperEmitter                (gera mop.MonitorWrappers.java sob demanda)
│
├── dex-mutator/               ← manipulação DEX low-level
│   ├── DexWeaver                   (orquestra ClassDef iteration + delega para emitters)
│   ├── InstructionInjector         (primitivas: insertBefore, insertAfter, replaceInvoke)
│   ├── RegisterAllocator           (encapsula scratch register + spill decisions)
│   └── RegisterShifter             (4-bit overflow expansion; 20+ formats DEX)
│
├── coverage-weaver/           ← execution(* *.*(..)) catch-all separado
│   ├── CoverageWeaver
│   ├── PackageFilter               (filtro canônico app vs framework)
│   └── SignatureFormatter          (Soot-style: <FQN: RetType method(params)>)
│
├── monitor-builder/           ← javac + d8 (do protótipo, polished)
│   └── MonitorBuilder, BuilderCli
│
├── multidex-merger/           ← apksigner v3 + zipalign (do protótipo, polished)
│   └── MultidexMerger, MergerCli
│
├── cli/                       ← entrada unificada (graduação do PrototypeCli stub)
│   ├── InstrumentationCli          (Picocli — instrument <APK> --descriptor X --out Y)
│   ├── ConfigResolver              (CLI flags > env vars > config file > defaults)
│   └── BatchRunner                 (paralelismo opcional; reusa contrato instrument_apks)
│
└── validator/                 ← MÓDULO PRÓPRIO (não mistura com weaver)
    ├── BaksmaliDiffer              (Layer 1: hook count diff ajc vs dexlib2)
    ├── TraceComparator             (Layer 3: event diff em corrida pareada)
    ├── FeatureMappingChecker       (estático: cada construção AspectJ usada tem mapping?)
    ├── ConstructionInventoryGenerator (gera AJ_CONSTRUCTIONS_INVENTORY.md programaticamente)
    └── ValidationCli               (orchestra layers 1-5 do plano de validação)
```

### 4.2 Componentes Python (interface com rv-experiment)

```
rv-android/modules/rv-instrumentation-dexlib2-py/
└── src/rv_instrumentation_dexlib2/
    ├── dexlib_instrumentation.py   ← classe DexlibInstrumentation
    │     ├── instrument_apks(apks_dir, results_dir) → InstrumentationResults
    │     │     [API IDÊNTICA a RVInstrumentation; trocável por composição]
    │     └── _invoke_java_cli(apk_path) → CliResult
    ├── config.py                   ← DexlibInstrumentationConfig (Pydantic)
    └── error_phase.py              ← reusa contrato @ErrorHandler.handle_errors do rv-android-core
```

E em `rv-experiment/.../pre_processor.py`:
```python
variant = experiment_config.instrumentation_variant  # NEW field, default "ajc"
if variant == "ajc":
    instrumentation = RVInstrumentation(experiment_config.get_rv_instrumentation_config())
elif variant == "dexlib2":
    instrumentation = DexlibInstrumentation(experiment_config.get_dexlib_instrumentation_config())
results = instrumentation.instrument_apks(apks_dir, results_dir)
```

### 4.3 Contratos / interfaces

| Boundary | Contrato | Owner |
|---|---|---|
| rv-experiment → instrumentation (qualquer variante) | Python: `instrument_apks(apks_dir, results_dir) → InstrumentationResults` | rv-android-core (interface) |
| rv-monitor-generator → instrumentation | Filesystem: `monitor_output_dir/` com `MultiSpec_*MonitorAspect.aj`, `MultiSpec_*RuntimeMonitor.java`, `coverage.aj`, **`MultiSpec_*MonitorAspect.json`** (NEW — emitido pelo --emit-descriptor) | rv-monitor-generator |
| dexlib-py → dexlib-java CLI | `java -cp ... InstrumentationCli instrument <apk> -d <descriptor.json> -o <out>` (exit 0 = ok) | new module |
| descriptor-reader → pointcut-engine | `AspectDescriptor` POJO | descriptor-reader |
| pointcut-engine → advice-emitter | `Match { ClassDef class; Method method; int instructionIdx; List<Binding> args }` | pointcut-engine |
| advice-emitter → dex-mutator | `EmitPlan { List<Instruction> toInsert; InsertionPoint point; RegisterRequest regs }` | advice-emitter |
| dex-mutator → output | `MutableDexFile` ready for d8/multidex-merger | dex-mutator |
| validator → CI | exit 0 + JSON report; falha bloqueia merge | validator |

### 4.4 Por que esta decomposição (não copiar 1:1 o protótipo)

- **Protótipo colapsa**: `DexWeaver` faz parsing + matching + register allocation + injection. ~3400 LOC em uma classe. Difícil testar isoladamente, difícil estender.
- **Nova decomposição**: cada componente tem responsabilidade única. `pointcut-engine` é puro (entrada: descriptor + DEX; saída: matches). `advice-emitter` é puro (entrada: match; saída: instructions). `dex-mutator` é o único que muta. Permite:
  - Test-first por componente (P1 simplicity + TDD)
  - Substituição independente (futura troca de `pointcut-engine` por implementação baseada em ANTLR sem tocar weaver)
  - Validação rigorosa (FeatureMappingChecker é estático: olha pointcut-engine para enumerar construções suportadas; comparar com inventário)
- **`validator/` separado**: critério de aceitação do paper. Validation logic não pode misturar com weaver (separação evidence/code).
- **`coverage-weaver/` separado**: tem ciclo de vida diferente (atinge TODOS os métodos, vs business advices que atingem joinpoints específicos). Filtros canônicos próprios.

---

## 5. Estratégia de Coexistência (A/B) e Substituição

```
Phase 4 (Implement) — final state
├── modules/rv-instrumentation/                  (legacy ajc — INTACTO)
├── modules/rv-instrumentation-dexlib2/          (NEW — Java multi-module)
└── modules/rv-instrumentation-dexlib2-py/       (NEW — Python wrapper)

rv-experiment configuração:
└── instrumentation_variant: "ajc" | "dexlib2"  (default "ajc")

Pós-Layer 4 ratificada (Phase 5 → 6):
├── backup/2026-MM-DD-rv-instrumentation-ajc/   (legacy MOVED)
├── modules/rv-instrumentation/                  (NEW — agora aponta para dexlib2; rename ou novo conteúdo)
└── (módulo dexlib2-py vira o conteúdo padrão de rv-instrumentation-py)
```

**Sequência:**
1. Phase 4 implementa coexistência. rv-experiment ganha variant flag (default `ajc`).
2. Phase 5 (Verify) executa Layers 1-5 da validação. Em paralelo: ajc vs dexlib2 no mesmo dataset.
3. Se Layer 4 passar (recovery rate ≥ 90%, F1 ≥ 0.98, sem regressão estatística): tarefa de Phase 6 é a substituição (P3).
4. Se Layer 4 NÃO passar: change parada para retrabalho; legacy continua sendo default; documento `LIMITATIONS.md` atualizado.

---

## 6. Plano de Validação rigorosa (paper-grade)

Reusa integralmente o framework de 6 camadas de `docs/20260423_plano_validacao.md`, agora **operacionalizado como módulo `validator/`** dentro da change.

| Layer | Componente validator | Gate | Onde no SDD |
|---|---|---|---|
| 0 — Conformance (INV-INS-*) | `validator/ConformanceChecker` | 12/12 invariantes verdes | Phase 4 (built-in) |
| 1 — Static hook diff (baksmali) | `BaksmaliDiffer` | recall ≥ 0.95 em ≥90% de 30 APK subset | Phase 5 |
| 2 — Install & boot | `BootValidator` (adb wrapper) | 0 regressões vs ajc baseline | Phase 5 |
| 3 — Trace equivalence | `TraceComparator` | F1 ≥ 0.98, Kappa ≥ 0.9, MWU p > 0.05 | Phase 5 |
| 4 — Large-scale JCA-400 | `BatchValidator` (945 tasks, ~36h) | recovery_rate ≥ 90%, sem regressão estatística | Phase 5 (paralelo a doc) |
| 5 — Coverage.aj recall | `CoverageValidator` | recall RVSEC-COV ≥ 0.99, delta ≤ 1pp | Phase 5 |
| 6 — OpenSpec sync | `/opsx:archive` | specs atualizados, change archived | Phase 6 |

### Documentos mandatórios para defesa do paper

1. **`docs/AJ_CONSTRUCTIONS_INVENTORY.md`** — gerado por `ConstructionInventoryGenerator`:
   - Toda construção AspectJ usada (call, execution, before, after, after-returning, after-throwing, target, args, !within, staticinitialization, if, thisJoinPoint, adviceexecution-as-filter)
   - Para cada construção: lista de file:line em rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new,aspect}
   - Atualizado **automaticamente** a cada release (CI step)

2. **`docs/AJ_TO_DEXLIB2_MAPPING.md`** — tabela:
   ```
   | AspectJ construct | dexlib2 component | Function | Smali pattern | Test |
   | call(T.m(args))   | pointcut-engine + dex-mutator | DexWeaver.matchInvoke | invoke-static {regs} L<monitor>;.<event>(...) | t01_call.dex |
   | ...               | ...               | ...      | ...           | ...  |
   ```
   - **Toda linha tem teste em `validator/`** que prova mapping (FeatureMappingChecker assert).

3. **`docs/LIMITATIONS.md`** — gaps explícitos:
   - `around()`: 0 usos no nosso domínio (citação ConstructionInventory) → não suportado, defensável.
   - `cflow()`, `cflowbelow()`: idem.
   - `handler()`: idem.
   - `get()`, `set()`: idem.
   - `initialization()`, `preinitialization()`: subsumido por `call(T.new(..))`, ok.
   - Cada item: rationale + condições para suporte futuro.

---

## 7. Reuso do protótipo

| Do protótipo | Reusado como | Local na nova arquitetura |
|---|---|---|
| `descriptor-reader/` (197 LOC) | Quase 1:1 | `descriptor-reader/` (mesmo) |
| `DexWeaver` (~3400 LOC) | **Refatorado** em pointcut-engine + advice-emitter + dex-mutator | distribuído |
| `PointcutExpressionParser` | 1:1 inicial; substituível por ANTLR depois | `pointcut-engine/PointcutExpressionParser` |
| `TypeResolver` | 1:1 + adicionar `InheritanceResolver` | `pointcut-engine/` |
| `AndroidClassIndex` | 1:1 | `pointcut-engine/AndroidClassIndex` |
| `WrapperGenerator` | 1:1 → renomear `WrapperEmitter`; mover para `advice-emitter/` | `advice-emitter/WrapperEmitter` |
| `CoverageWeaver` | 1:1, separar PackageFilter + SignatureFormatter | `coverage-weaver/` |
| `RegisterShifter` | 1:1 | `dex-mutator/RegisterShifter` |
| `MonitorBuilder` | 1:1 polish (logging, error msgs, externalizar paths) | `monitor-builder/` |
| `MultidexMerger` | 1:1 polish | `multidex-merger/` |
| `run_e2e.sh` | Substituído por `InstrumentationCli` (Picocli) + `BatchRunner` | `cli/` |
| `verify_baksmali_diff.sh` | Embebido em `validator/BaksmaliDiffer` | `validator/` |
| Test fixtures (`MultiSpec_1.json`) | Reusados como golden files do `validator/` | `validator/src/test/resources/` |
| **Patch JavaMOP `emit-descriptor`** | **Promovido** (commit 79547700) — pushed e mergeado em master rvsec | `rvsec/javamop/` |

**Que NÃO é reusado:**
- `cli/PrototypeCli` stub embrionário — substituído por `InstrumentationCli` graduado.
- Hardcoded paths em `run_e2e.sh` (keystore, ~/.m2/) — substituídos por `ConfigResolver`.

---

## 8. Sequência por Phase do SDD (Full SDD)

| Phase | Atividades chave | Artefatos | Estimativa |
|---|---|---|---|
| **Phase 0 (Ideação)** | Este documento (`pre-plan.md`) | `pre-plan.md` | ✅ feito |
| **Phase 1 (Explore)** | `/opsx:explore`; `/rv-analyze-module rv-instrumentation`; `/rv-impact-analyzer`; criar issue #52; criar branch `gh52-instr-dexlib2` from modules; merge patch JavaMOP em master rvsec | exploração; issue criada; branch remota | 1-2 dias |
| **Phase 2 (Propose)** | `/opsx:new gh52-instr-dexlib2`; redigir `proposal.md` (FRs, NFRs, impactos); delta specs em `specs/instrumentation/spec.md` (REQ-INS-13+, INV-INS-13+ para pipeline DEX-nativo + variant flag) | proposal.md, delta specs | 2-3 dias |
| **Phase 3 (Design)** | `design.md` (arquitetura §4 deste pre-plan, expandida); `tasks.md` (decomposição por módulo, anotações `/rv-doc-code`); `/rv-doc-adr ADR-DEX-NATIVE` registrando decisão arquitetural; `/rv-risk gh52-instr-dexlib2` | design.md, tasks.md, ADR | 2-3 dias |
| **Phase 4 (Implement)** | `/opsx:apply` com subagent orchestration (5 grupos paralelos: Java modules, Python wrapper, JavaMOP patch promotion, rv-experiment variant, validator harness); `/rv-test-add` por componente; `/rv-doc-code` por classe nova | código + testes | 3-4 semanas |
| **Phase 5 (Verify)** | `/rv-verify rv-instrumentation-dexlib2`; `/rv-verify rv-instrumentation-dexlib2-py`; rodar Layers 1-5 do validator; `/opsx:verify`; `/rv-code-reviewer` | reports validação, testes verdes | 2-3 semanas (Layer 4 = ~36h compute) |
| **Phase 6 (Archive)** | Quarentenar `rv-instrumentation` legado (P3, mover para backup/); rename module dirs; `/opsx:sync` + `/opsx:archive`; `/rv-docs-sync`; PR para modules; `/rv-retrospective` | specs main atualizados, change archived, PR mergeado | 3-5 dias |

**Total estimado**: 6-9 semanas. Como deadline de defesa (2026-04-13) já passou, este projeto ocorre em janela de finalização (gh48). Coordenar com gh48.

---

## 9. Riscos & mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Layer 4 (945 tasks, 36h) revela regressão estatística em subset de APKs | Média | Alto (bloqueia merge) | Análise por categoria de APK; documentar gaps em `LIMITATIONS.md`; manter ajc como variant `"ajc"` no longo prazo se necessário |
| `staticinitialization(T+)` injection em `<clinit>` sintético quebra inicialização de classes | Média | Médio | Phase 4 inclui task dedicada; validator Layer 1 detecta via baksmali diff antes de boot |
| Multidex split mudar entre input e output | Baixa | Médio | dex-mutator preserva splits de entrada; teste explícito com APK > 65k methods |
| JavaMOP upstream tem release nova durante a change e perdemos o patch | Baixa | Baixo | rvsec/javamop é vendored; manter patch como série de commits aplicáveis |
| `rv-experiment` outros consumidores não suportam variant flag | Baixa | Baixo | Default permanece `"ajc"` enquanto valida; switch só após Layer 4 |
| Docker images (jca400-aperv etc.) precisam novas dependências (apksigner, dexlib2 jar) | Alta | Baixo | Tarefa em Phase 4 atualiza Dockerfiles; reusa imagens existentes onde possível |
| Tempo: 6-9 semanas em janela de finalização | Alta | Médio | Não é bloqueante para defesa (já passou); bloqueia paper. Considerar paralelizar Phase 5 com escrita do paper |

---

## 10. Critical files (pontos de tocar)

### Existentes (a serem lidos / modificados)

| Path | Razão |
|---|---|
| `rv-android/openspec/specs/instrumentation/spec.md` | Adicionar REQ-INS-13+, INV-INS-13+ para pipeline DEX-nativo + variant |
| `rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py` | Referência do contrato Python a preservar |
| `rv-android/modules/rv-instrumentation/src/rv_instrumentation/config.py` | Modelo Pydantic — espelhar em DexlibInstrumentationConfig |
| `rv-android/modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py` | Adicionar invocação `--emit-descriptor` ao chamar javamop |
| `rv-android/modules/rv-experiment/src/.../pre_processor.py` | Adicionar dispatch por variant flag |
| `rv-android/modules/rv-experiment/.../config.py` | Adicionar `instrumentation_variant: Literal["ajc","dexlib2"]` |
| `rvsec/javamop/src/main/java/javamop/output/AspectJDescriptor.java` | Patch existente — promover (commit 79547700) |
| `rvsec/javamop/src/main/java/javamop/output/descriptor/DescriptorWriter.java` | Patch existente — promover |
| `rv-android/CLAUDE.md` | Documentar nova variante de instrumentação |

### Novos (a serem criados)

| Path | Conteúdo |
|---|---|
| `rv-android/openspec/changes/gh52-instr-dexlib2/pre-plan.md` | Este documento |
| `rv-android/openspec/changes/gh52-instr-dexlib2/proposal.md` | Phase 2 |
| `rv-android/openspec/changes/gh52-instr-dexlib2/specs/instrumentation/spec.md` | Delta specs Phase 2 |
| `rv-android/openspec/changes/gh52-instr-dexlib2/design.md` | Phase 3 |
| `rv-android/openspec/changes/gh52-instr-dexlib2/tasks.md` | Phase 3 |
| `rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md` | Phase 3 |
| `rv-android/modules/rv-instrumentation-dexlib2/` | Módulo Java multi-module (Phase 4) |
| `rv-android/modules/rv-instrumentation-dexlib2-py/` | Wrapper Python (Phase 4) |
| `rv-android/docs/AJ_CONSTRUCTIONS_INVENTORY.md` | Phase 4 (gerado) |
| `rv-android/docs/AJ_TO_DEXLIB2_MAPPING.md` | Phase 4 |
| `rv-android/docs/LIMITATIONS.md` | Phase 4 |

---

## 11. Verificação (como saberemos que funciona)

### Verificação contínua (Phase 4)

```bash
# Por componente
cd rv-android/modules/rv-instrumentation-dexlib2
mvn -pl descriptor-reader test
mvn -pl pointcut-engine test
mvn -pl advice-emitter test
mvn -pl dex-mutator test
mvn -pl coverage-weaver test
mvn -pl validator test
mvn -pl monitor-builder test
mvn -pl multidex-merger test

# E2E mínimo (smoke)
java -jar cli/target/rv-instr-dexlib2.jar instrument <apk> -d <descriptor.json> -o <out>
```

### Verificação de aceitação (Phase 5)

```bash
# Layer 1 — static hook diff
java -jar validator/target/validator.jar diff --baseline ajc --candidate dexlib2 --apks <30-apk-subset>
# Gate: recall ≥ 0.95 em ≥27/30 APKs

# Layer 2 — boot
validator/scripts/boot_check.sh <30-apk-subset>
# Gate: 0 regressões vs ajc

# Layer 3 — trace equivalence
java -jar validator/target/validator.jar trace --oracle cryptoapp --apks <30-apk-subset>
# Gate: F1 ≥ 0.98, Kappa ≥ 0.9

# Layer 4 — large scale
docker compose -f rv-android/docker/docker-compose.jca400-aperv.yml up validator-batch
# Gate: recovery_rate ≥ 90%, MWU p > 0.05

# Layer 5 — coverage recall
java -jar validator/target/validator.jar coverage --apks <30-apk-subset>
# Gate: recall RVSEC-COV ≥ 0.99, delta ≤ 1pp

# OpenSpec
cd rv-android && openspec validate --change gh52-instr-dexlib2
openspec verify --change gh52-instr-dexlib2
```

### Critério final de "pronto para merge"

- ✅ Todos os 6 gates de validação verdes
- ✅ `AJ_CONSTRUCTIONS_INVENTORY.md`, `AJ_TO_DEXLIB2_MAPPING.md`, `LIMITATIONS.md` redigidos
- ✅ `FeatureMappingChecker` assert: cada construção do inventário tem teste em validator/
- ✅ `/rv-code-reviewer` aprovou
- ✅ `/opsx:verify` ok
- ✅ Spec delta `instrumentation/spec.md` mergeada via `/opsx:sync`
- ✅ `rv-instrumentation` antigo movido para `backup/`
- ✅ Default de `instrumentation_variant` mudado para `"dexlib2"` em rv-experiment
- ✅ PR `gh52-instr-dexlib2 → modules` mergeado
- ✅ Issue #52 fechada com checklist de aceitação completa

---

## 12. Próximos passos imediatos (ao aprovar este pre-plan)

1. **Mover este arquivo** para `rv-android/openspec/changes/gh52-instr-dexlib2/pre-plan.md` (criar a estrutura da change com `openspec new change "gh52-instr-dexlib2"`).
2. **Criar GitHub Issue #52** (Feature template) com link para este pre-plan.
3. **Criar branch remota** `gh52-instr-dexlib2` saindo de `modules` e push.
4. **Promover patch JavaMOP** (`emit-descriptor` em rvsec): commit, push, PR para master do rvsec.
5. **Phase 1 (Explore) começar** com `/opsx:explore` e `/rv-analyze-module rv-instrumentation`.
