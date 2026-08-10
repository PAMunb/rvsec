# GAMA — Auditoria de suficiência diagnóstica (piloto: CipherSpec, GCMParameterSpecSpec)

Agente Gama · 2026-08-08 · postura adversarial. Specs auditadas (hashes SHA-256):
- `CipherSpec.mop` `c9deafb2acb2b2d75e55fe1c62b4f948685aa7e23142a71c5d883c8bb74d2de5`
- `GCMParameterSpecSpec.mop` `18c84f8f64f3b5dde60ee06aee1e2cfd86e5468c32b005567f5e79f1e4355fe5` (byte-idêntica à `jca`, confirmado por `cmp`)

Artefatos gerados **somente em scratch** (specs copiadas; árvore de specs intocada):
`<scratch>/gama/gen_cipher/CipherSpecRuntimeMonitor.java`, `<scratch>/gama/gen_gcm/GCMParameterSpecSpecRuntimeMonitor.java`
(`javamop -merge` + `rv-monitor -merge`, jars de `javamop/target/release/.../bin/javamop` e `rv-monitor/target/release/rv-monitor/bin/rv-monitor`).
Scratch = `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/09214a58-1d36-4fe0-b3e1-5797ee8cd23e/scratchpad/gama/`.

## 1. Veredito do gate diagnóstico (pré-registrado)

| Spec | Gate | Motivo |
|---|---|---|
| CipherSpec | **FAIL** | (i) todo `@fail` emite `expecting="unknown"`; (ii) `@fail` espúrio acompanha erro específico no caminho `g3→init*`; (iii) acusação deslocada (D-S9) atribui a violação ao evento e sítio errados |
| GCMParameterSpecSpec | **FAIL** | handler `@fail` é código morto (inalcançável por objeto); violações da própria regra (CONSTRAINTS/REQUIRES) nunca são reportadas por esta spec — fail-silent com deslocamento para CipherSpec |

## 2. Itens (a)–(g) por handler

### CipherSpec `@fail` (CipherSpec.mop:330-333)
`new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "CipherSpec", "" + __LOC)` — construtor de 3 argumentos.

| Item | Estado | Evidência |
|---|---|---|
| (a) categoria + ID regra/cláusula | **FAIL** | categoria genérica `InvalidSequenceOfMethodCalls`; nenhuma cláusula CrySL nomeada |
| (b) spec + versão | **PARCIAL/FAIL** | nome "CipherSpec" presente; **nenhum campo distingue `jca` de `jca_android`** — mesma string de spec e mesmos literais de mensagem nos dois conjuntos (ErrorSummary.java:123-124: 6 campos + expecting; nenhum é o conjunto) |
| (c) evento observado + esperado | **FAIL** | `@fail` do rv-monitor não conhece o evento gatilho; `expecting="unknown"` (ErrorDescription.java:34-36) |
| (d) estado anterior/novo | **FAIL** | ausente da mensagem; o monitor tem o estado (`getState()`, `getLastEvent()` — RuntimeMonitor gerado, `handleEvent`) mas o handler não o serializa |
| (e) `__LOC` | **PASS com ressalva** | `__LOC` → `ViolationRecorder.getLineOfCode()` (rv-monitor `output/Util.java:7-8`; ViolationRecorder.java:53-59) = primeiro frame "relevante". Ressalvas: no caminho deslocado aponta o sítio da **chamada seguinte**; frames com `fileName==null` (dex sem SourceFile) escapam do filtro `mop.*` (ViolationRecorder.java:86-104) e podem nomear o wrapper `mop.MonitorWrappers` (WrapperEmitter.java:65-67); retorno "(Unknown)" colapsa no fallback do ErrorSummary |
| (f) identidade do monitor/objeto | **FAIL** | nenhum campo; impossível separar dois Ciphers no mesmo sítio |
| (g) chave de dedupe estável | **FAIL** | três chaves distintas por camada, mutuamente inconsistentes (§4) |

Material sensível: **PASS** — nenhuma chave/plaintext serializado (transformation string é o único dado do app; ver GAMA-CIP-07 para o risco de injeção).

### CipherSpec handlers específicos (corpo de evento)
- `reportUnsafeTransformation` (CipherSpec.mop:53-58): categoria específica `UnsafeAlgorithm`; conjunto esperado **elidido** — literal `"{AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...}"` não é a allow-list real de `AndroidCipherTransformationUtil` (item (c) parcial). Encontrado no histórico como único literal UnsafeAlgorithm do CipherSpec (109 linhas).
- `reportUnrandomized` / `reportUnpreparedParams` / `reportMacedPlainText` (CipherSpec.mop:63-106): todos `UnsatisfiedConstraint` com mensagem específica e `__LOC` correto — os melhores handlers do conjunto — **mas** colidem entre si no dedupe in-JVM (§4).

### GCMParameterSpecSpec `@fail` (GCMParameterSpecSpec.mop:50-53)
**Código morto, provado pelo autômato efetivo.** Tabela de transição gerada
(`gen_gcm/GCMParameterSpecSpecRuntimeMonitor.java:93`): `Prop_1_transition_c1[] = {1, 2, 2}` —
estado 0 (start) → 1 (match) → 2 (fail). O único evento é o construtor (`after returning`),
que dispara **uma vez por identidade de objeto**; o monitor é indexado por `s`; o estado 2 exige
um segundo `c1` no **mesmo** monitor — impossível. Logo `@fail` (e seu `"unknown"`) jamais executa.
Corroboração no histórico: **0 linhas** de `GCMParameterSpecSpec` em 97.018 (errors.csv, seção histórico).

Consequência diagnóstica (mais grave que o dead code): as violações da regra —
`tLen ∉ {96,104,112,120,128}` (CONSTRAINTS) e `src` não-RANDOMIZED (REQUIRES) — estão dobradas
para dentro do `condition(...)` do evento de criação (GCMParameterSpecSpec.mop:26-29, 37-43).
`condition==false` ⇒ **nenhum evento, nenhum monitor, nenhum report**. A detecção é deslocada
para `CipherSpec.reportUnpreparedParams` (CipherSpec.mop:88-92), que só dispara **se** o objeto
inválido for usado num `init` GCM, e reporta o requisito ("requires a GCMParameterSpec established…"),
não a causa-raiz (tag curto × src não aleatório × nunca monitorado — indistinguíveis).
Objeto inválido construído e nunca usado em init ⇒ **FN realizável** para a regra GCMParameterSpec.

### Anomalia de alfabeto (GCM)
Os dois eventos declaram-se `c1` (GCMParameterSpecSpec.mop:23 e 34) e o `ere` é `c1 | c2`
(linha 48) com `c2` **nunca declarado**. javamop e rv-monitor aceitam sem erro nem warning
(gerado em scratch, saída limpa); o `c2` órfão é descartado silenciosamente pela síntese e o
autômato efetivo tem 1 evento. A linguagem sai correta **por acidente** (ambos os construtores
mapeiam para `c1`); o texto da spec mente sobre o próprio alfabeto e o pipeline é fail-open
para símbolo indefinido em `ere`.

## 3. Cruzamento com o resíduo D-S9 (acusação deslocada)

Provado no autômato efetivo (`gen_cipher/CipherSpecRuntimeMonitor.java:405-418`; 6 estados,
`fail=5`, `match1=4`; `start` e `unsafeAlg` foram **fundidos no estado 0** pela minimização —
`transition_g3[0]=0`, `transition_g1[0]=3`):

1. **`@fail` espúrio junto de erro específico**: após `g3` (transformação inválida), qualquer
   `init*` com chave validada executa o corpo (→ `UnsafeAlgorithm`, específico) **e** transita
   `0→5` (→ `InvalidSequenceOfMethodCalls`, "unknown") **na mesma chamada** — ordem provada no
   método gerado `Prop_1_event_init2` (corpo → `handleEvent` → handler). Viola o gate
   pré-registrado textualmente.
2. **Acusação uma chamada adiante**: `init*` com chave não validada → `condition==false` →
   `return false` **antes** de `handleEvent` (código gerado) → sem transição, sem report, sem
   `GENERATED_CIPHER`; o `doFinal` seguinte transita `s1(3)→5` (`transition_f2[3]=5`) e o
   `@fail` acusa **o evento errado** (`doFinal`, não `init`), **no sítio errado** (`__LOC` da
   chamada seguinte). Se `init` e `doFinal` estão em métodos diferentes do app, a chave de
   misuse `(apk, classe, método, spec)` aponta o **método errado** — impacto diagnóstico:
   além de categoria genérica, localização incorreta; FP de localização, não de existência.
   É o resíduo registrado (frozen_set_debt, 3b.11b) — registrado ≠ aprovado no gate.

Achado lateral (generalizável): o wrapper gerado **ignora o retorno** de `Prop_1_event_*`
(gen_gcm/...RuntimeMonitor.java:38-44): após evento suprimido por condition, os flags
`Category_*` **do evento anterior** persistem e o handler `@match` pode re-executar
espuriamente (re-marca accepting; benigno aqui, mas é semântica não-óbvia do gerador).

## 4. Cadeia de serialização (monitor → logcat → parser → errors.csv)

Fio: handler → `ErrorCollector.addError` (rvsec-logger-logcat/ErrorCollector.java:36-42)
→ `Log.v("RVSEC", ErrorSummary.toString() + "," + expecting.trim())`
→ logcat threadtime → `logcat_parser._parse_logcat_line` (logcat_parser.py:267)
→ `_parse_error_message` Formato 2 (logcat_parser.py:318-350) → `RvErrorLog` → CSV.

- **Formato**: `spec,classFQN,classSimples,método,localização,tipo[,expecting…]` (ErrorSummary.java:123-124). Parser mapeia parts[0,1,3,4,5] e rejunta `parts[6:]` como mensagem (logcat_parser.py:347-349) — **vírgulas dentro de `expecting` sobrevivem** (ex.: "PKIX,SunX509"); `classSimples` (parts[2]) é descartado. PASS para mensagens bem-formadas.
- **Escape morto**: `escapeSpecialCharacters` existe e está **comentado** (ErrorCollector.java:39-40, 44-51). `expecting` contém a transformation do app; um `\n` nela fragmenta a linha do logcat e a continuação não casa o Formato 2 → registro perdido/garbled (warning logcat_parser.py:371). Não exercitado — INFERIDO.
- **Truncamento do logcat**: payload máximo ~4068 bytes (limite de plataforma liblog; NÃO_VERIFICADO nesta árvore). Mensagens atuais < 300 chars — risco baixo, mas sem guarda.
- **`__LOC` não sobrevive até o dataset**: `RvErrorLog` guarda `source`, mas `unique_msg = class:::method:::spec:::error_type:::message` (log.py:113) e as colunas do errors.csv **não têm** a posição de fonte — a linha morre entre parser e CSV. Item (e) vale só até o logcat.
- **Colisões de dedupe — três chaves inconsistentes**:
  1. In-JVM (`HashSet<ErrorDescription>`, ErrorCollector.java:37): identidade = `ErrorSummary` = (spec, tipo, classe, método, **linha**), `expecting` **excluído** (ErrorDescription.java:109-139). Consequência provada: dois `UnsatisfiedConstraint` de cláusulas diferentes no mesmo sítio (ex.: `init4` com ranGen não monitorado **e** IV não preparado, mesmo `__LOC`) colidem — **só o primeiro é emitido, para sempre (na vida do processo)**.
  2. Reinício de processo zera o `HashSet` → re-emissão; contagem de linhas no dataset depende do ciclo de vida do app (variável por tool).
  3. Dataset: `unique_msg` inclui a mensagem e exclui a linha; a chave de misuse documentada `(apk, classe, método, spec)` (ErrorDescription.java:66-88) exclui o **tipo** — `UnsafeAlgorithm` e o `InvalidSeq` espúrio no mesmo sítio fundem num só misuse (mascara o double-fire, e conflate categorias).

## 5. Comandos (reprodução)

```
sha256sum .../jca_android/{CipherSpec,GCMParameterSpecSpec}.mop
cmp .../jca/GCMParameterSpecSpec.mop .../jca_android/GCMParameterSpecSpec.mop
cd <scratch>/gama/gen_gcm && javamop -merge -d . GCMParameterSpecSpec.mop && rv-monitor -merge -d . GCMParameterSpecSpec.rvm
cd <scratch>/gama/gen_cipher && javamop -merge -d . CipherSpec.mop && rv-monitor -merge -d . CipherSpec.rvm
```
