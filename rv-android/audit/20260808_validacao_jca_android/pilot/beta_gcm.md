# Parecer Beta — GCMParameterSpecSpec (`jca_android`) — toolchain e Android

Agente Beta (red team da toolchain), 2026-08-08. Mesmo protocolo do `beta_cipher.md`
(comandos de produção replicados de `runtime_verification_generator.py:211-215/267-272`,
execução exclusivamente em scratch). Autômato efetivo: `beta_autometa_efetivo_gcm.md`.

## 0. Insumos e hashes

Spec copiada de `RVSEC/rvsec/rvsec-mop/src/main/resources/jca_android/GCMParameterSpecSpec.mop`,
SHA-256 `18c84f8f64f3b5dde60ee06aee1e2cfd86e5468c32b005567f5e79f1e4355fe5`
(byte-idêntica ao congelado `jca` conforme fase 0 — a geração de hoje também testa D-S10).

| Artefato (individual) | SHA-256 |
|---|---|
| `GCMParameterSpecSpec.rvm` | `e5e50fbc2140fac59e193690eea7e097abe292e00389cf135f4787632745c614` |
| `GCMParameterSpecSpecMonitorAspect.aj` | `d2314ae02d46ff049438c806dbef91d12b8efc02b42a2a05228f285d95859192` |
| `GCMParameterSpecSpecMonitorAspect.json` | `76e39ffc9d1a4b798913a50a41b77523935a15e309c1770bb30c341c8d761d72` |
| `GCMParameterSpecSpecRuntimeMonitor.java` | `2f3ba6f442b63e9271f64fded80b31a8d1342f25eb547cc26afda72577e83076` |

`.rvm` byte-idêntico nas gerações individual, em par e no conjunto de 23 (mesmo hash).

## 1. Geração e custo — MEDIDO

| Ferramenta | Wall | RSS pico | Saída |
|---|---|---|---|
| javamop (individual) | 0,41 s | 87 MB | limpa (exit 0, stderr vazio) |
| rv-monitor (individual) | 0,91 s | 86 MB | limpa |

Orçamento (CoenableProbe, plugins de produção; scratch `probe_gcm.out`): com o alfabeto que o
ERE declara ({c1, c2}): `events=2`, `states_after_min=2`, `coenable_sets[fail]=6` =
2×(2²−1) saturado, `coenable_sets[match]=0`, `coenable_chars=107`. Trivial; sem qualquer
proximidade do teto de 17.

## 2. Defeito textual da spec — BETA-GCM-02 (o achado central)

O `.mop` declara **dois eventos com o mesmo nome `c1`** (linhas 23 e 34 — a segunda definição
era evidentemente para ser `c2`) e o ERE referencia `c1 | c2` (linha 48), onde `c2` **não
existe**. A toolchain inteira aceita isso **sem warning** (javamop e rv-monitor, exit 0,
stderr vazio — medido). Efeitos verificados no artefato:

- as duas definições viram dois *carriers* (sobrecargas) do MESMO evento `c1` — um por
  construtor (`RuntimeMonitor:135` e `:152`);
- `c2` entra no alfabeto do autômato como símbolo morto e é eliminado: uma única tabela
  `Prop_1_transition_c1 = {1,2,2}` (`:93`), nenhum advice/wrapper para c2;
- linguagem efetiva: exatamente um `c1` — **coincide com a intenção** (`c1 | c2` com cada
  evento ocorrendo no máximo uma vez por objeto). Classificação:
  `DIVERGÊNCIA_EQUIVALENTE_COMPROVADA` (equivalência provada no artefato, não na sintaxe),
  com registro de **defeito latente**: o texto só é equivalente por acaso estrutural, e a
  aceitação silenciosa de símbolo indefinido no ERE é fail-open do gerador (um typo futuro
  em spec maior mudaria a linguagem sem qualquer diagnóstico).

## 3. Cadeia de advice — OBSERVADO_EM_ARTEFATO

- 2 pointcuts de construtor (`call(public GCMParameterSpec.new(int, byte[]))` e
  `(int, byte[], int, int)`), 2 advices `after returning(s)`, **1 monitorCall cada**, ambos
  para `GCMParameterSpecSpec_c1Event` (sobrecargas por aridade) — `MonitorAspect.aj:38-47`;
  descriptor 1:1 com o aspecto (2 advices, uniqueIds `c1_3`/`c1_4`, args na ordem
  `tagLen, src[, offset, len], s`, `position=after`+`returning`, `countCond=null`).
- `before/after`: correto — evento de construção só pode ligar `s` no retorno.
- **`__LOC`**: só no handler @fail; expande para `ViolationRecorder.getLineOfCode()`
  (`RuntimeMonitor:171`). Mesma ameaça A2 do parecer Cipher (frames DEX com
  `fileName==null` não são filtrados — `ViolationRecorder.java:87-105`).
- **condition(...)**: guardas (`validLengths.contains(tagLen) && validate(RANDOMIZED, src)`
  [+ offsets na aridade 4]) compiladas como prólogo com `return false` antes de
  `handleEvent` (`:137-143`, `:154-160`). Supressão silenciosa; nenhum erro local. Ver §4.
- Sem múltiplos pointcuts por evento no mesmo join point → sem risco de double-fire.
- Wrappers estáticos: mesmo padrão do Cipher (flags checadas sem consultar o retorno,
  `:311-315`/`:363-367`); aqui o re-disparo de @match por evento suprimido exigiria dois
  eventos no mesmo monitor, o que não ocorre (objeto novo por construção) — defeito de
  mecanismo presente, inerte nesta spec.
- Nota de robustez: `List`/`Arrays` são usados no `.mop` sem import próprio e compilam
  porque o rv-monitor injeta `java.util.*` no monitor (`RuntimeMonitor:8`) e o javamop no
  aspecto (`MonitorAspect.aj:8`) — dependência acidental do preâmbulo gerado, registrada.

## 4. Diagnóstico — @fail inalcançável e resíduo D-S9

Do autômato efetivo: fail exige um segundo `c1` no mesmo monitor; o monitor é indexado pelo
objeto retornado, novo a cada construção ⇒ **o handler @fail nunca executa em execução
real** (dead code de diagnóstico) e o `ErrorType.InvalidSequenceOfMethodCalls` do GCM não é
observável. Uma construção não conforme (tagLen fora de {96,104,112,120,128}, src não
randomizado, offsets inválidos) é suprimida sem transição: `PREPARED_GCM` não é gravado e a
acusação emerge uma chamada adiante como `UnsatisfiedConstraint` no `CipherSpec.init`
(`CipherSpec.mop:88-92`) — o resíduo D-S9 congelado pela GH101. Impacto: FN local de
diagnóstico (a spec nunca acusa em nome próprio), sem FN de detecção no conjunto desde que
o Cipher correspondente seja inicializado em modo GCM. Um `GCMParameterSpec` malformado que
NUNCA chega a um `Cipher.init` monitorado passa em silêncio — limite herdado do desenho,
a registrar na matriz normativa.

## 5. Matcher vs API real — MEDIDO

Membros: 2 construtores confirmados por `javap` no `android-30/android.jar` (`96ccfdc8…`) +
vizinhos `getTLen`/`getIV`. `api_members.py` **pula construtores por construção**
(`api_members.py:94-97`), então a mesa dos ctors foi escrita à mão a partir do `javap` e o
harness stock foi complementado por uma variante em scratch (`PointcutBudgetCtor.java`) que
usa o MESMO `PointcutMatcher` de produção, mudando apenas o call-site sintético para
`new-instance` + `invoke-direct <init>` (a forma DEX real; o gate de construtor do matcher é
`cp.isConstructor() && "<init>"` — `PointcutMatcher.java:433-438`).

| Candidato | Capturado | Vizinhos |
|---|---|---|
| `c1_3 = GCMParameterSpec.new(int, byte[])` | `ctor/2` apenas | — |
| `c1_4 = GCMParameterSpec.new(int, byte[], int, int)` | `ctor/4` apenas | — |

`DISJOINT`; `UNMATCHED [getTLen/0, getIV/0]`. **Triangulação**: o harness stock
(invoke-virtual) produziu o MESMO resultado — o caminho de match não depende do opcode —
e o `android-37.0` tem os mesmos 2 construtores, logo o achado G10 não altera o matching
desta spec. Esperado ⊆ Capturado ✓; Capturado ∩ Vizinhos = ∅ ✓; disjunção ✓.
Saídas: scratch `budget_gcm.out`.

## 6. Hipóteses GH100

Mesma tabela do parecer Cipher (§5 de `beta_cipher.md`): emissor itera todos os monitorCalls
(`MonitorInvokeBuilder.java:69-78`), wrapper merge (`WrapperEmitter.java:243`), registry
fail-loud (`DexWeaver.java:172-173`), commonPointcut fail-loud (`DexWeaver.java:876-880`),
validador itera monitorCalls (`BaksmaliDiffer.java:235`). Para o GCM os dois advices têm
N=1, então INV-INS-104 é trivialmente satisfeito na forma. Nível DEX: NÃO_VERIFICADO
(sem weaving no piloto).

## 7. Síntese

Geração limpa e barata (0,41 s + 0,91 s, ~87 MB); autômato efetivo de alfabeto {c1} com a
linguagem pretendida apesar do defeito textual c1/c1/c2 aceito sem warning (fail-open do
gerador, achado central); cadeia de advice 1:1 e matcher exato sem vazamento (validado por
dois harnesses sobre o matcher de produção, e insensível ao G10); @fail inalcançável —
diagnóstico local inexistente por desenho (resíduo D-S9), a registrar como limitação, não
como aderência.
