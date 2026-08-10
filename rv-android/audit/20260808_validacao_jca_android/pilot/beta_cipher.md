# Parecer Beta — CipherSpec (`jca_android`) — toolchain e Android

Agente Beta (red team da toolchain), 2026-08-08. Escopo: falsificar a cadeia
.mop → .rvm + MonitorAspect.aj/descriptor → RuntimeMonitor.java → advice/monitorCall e medir
custo real. Sem leitura de outros pareceres. Autômato efetivo: `beta_autometa_efetivo_cipher.md`.

## 0. Insumos e comandos (reprodutibilidade)

- Spec: `RVSEC/rvsec/rvsec-mop/src/main/resources/jca_android/CipherSpec.mop`, copiada para
  scratch antes de qualquer execução; SHA-256 `c9deafb2acb2b2d75e55fe1c62b4f948685aa7e23142a71c5d883c8bb74d2de5`.
- Pipeline replicado exatamente como a produção monta os comandos:
  - JavaMOP: `javamop -d <out> -merge --emit-descriptor <specs>/*.mop` —
    flags montados em `rv-android/modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:211-215`
    (`emit_descriptor` default True: `config.py:70-80`); workaround do `-d` (mover `.rvm`)
    em `:221-223`; RV-Monitor: `rv-monitor -d <out> -merge <out>/*.rvm` — `:267-272`.
  - Binários efetivos conferidos por hash com `fase0/toolchain_ambiente.md`
    (javamop jar `ab4e3765…`; rv-monitor.jar `fab40319…`; plugins fsm `f88b066b…`/ere `eb2c92dc…`).
- Execuções em `SCRATCH/beta/gen_cipher` (individual), `gen_merge` (par) e `gen_full`
  (23 specs, modo de produção), cada uma com `/usr/bin/time -v`.

### Hashes dos artefatos gerados (individual)

| Artefato | SHA-256 |
|---|---|
| `CipherSpec.rvm` | `5d7b16bfc4af0ffc9381b0bd685dc1839fddd6fca56dde304a1133493c8c2851` |
| `CipherSpecMonitorAspect.aj` | `c1d012e7ac15d2330e69f07a8dcfa0d509dbc8855d7d1d3118f0a5d6eb043527` |
| `CipherSpecMonitorAspect.json` | `4424124df0224fcad578d032e3ade488e8f8eedccdae143f1ebb7f039802c94c` |
| `CipherSpecRuntimeMonitor.java` | `3cc74f2e80a19046779026bcb660bf01363a1076fa59ae88301e5d7d9cab6e0e` |

Lista completa no scratch `beta/hashes_artifacts.txt`. Par/full: `MultiSpec_1MonitorAspect.aj` `bfb20d14…`/`310fae06…`, `.json` `92b6459a…`/`e91570ce…`,
`RuntimeMonitor` `88ddfa7b…`/`d6228eac…`. O `.rvm` é **byte-idêntico** nos três modos.

## 1. Geração e custo — MEDIDO

| Execução | Ferramenta | Wall | RSS pico | Saída |
|---|---|---|---|---|
| individual | javamop | 0,45 s | 91 MB | limpa (exit 0, stderr vazio) |
| individual | rv-monitor | 6,66 s | 1,04 GB | limpa |
| par (Cipher+GCM) | javamop / rv-monitor | 0,46 s / 7,01 s | 93 MB / 1,02 GB | limpa |
| **produção (23 specs)** | javamop / rv-monitor | 0,67 s / **28,09 s** | 170 MB / **1,71 GB** | limpa; 119 advices, 140 monitorCalls |

Orçamento (CoenableProbe da skill, plugins de produção, comando no scratch `probe_cipher.out`):
`events=14`, `states_after_min=5` (não conta o fail), `coenable_sets[fail]=229.362` **=
14×(2¹⁴−1) — saturado** (`saturated_predict` igual), `coenable_sets[match1]=156`,
`coenable_chars=8.144.778`. Custo real 6,66 s / 1,04 GB coerente com a tabela da skill.
**A alegação D-S11 de 14 eventos confere no artefato**: 14 declarações `event` no `.mop`,
14 tabelas (`RuntimeMonitor:405-418`), 14 wrappers estáticos, 14 sítios de criação de monitor.
Margem ao teto prático: 17−14 = 3 eventos.

## 2. Cadeia de advice — OBSERVADO_EM_ARTEFATO

- **Cardinalidade/ordem**: 13 pointcuts, 13 advices, **14 monitorCalls** (aspecto e descriptor
  concordam 1:1). O advice `CipherSpec_g1` carrega **2 monitorCalls em ordem g1;g3**
  (`CipherSpecMonitorAspect.aj:60-66`; descriptor `advices[0].monitorCalls`), exatamente a
  forma N>1 governada por INV-INS-104. Nenhum evento com dois pointcuts (sem risco
  double-fire estrutural); disjunção verificada no matcher (§4).
- **before/after/returning**: init2/3/4 `before` (como no `.mop`); g1, u1, wkb1, f1, f2
  `after returning` com binding do retorno; u3, u5, f3, f5, f7 `after` puro (o `.mop` não
  liga retorno nesses). Fiel ao `.mop` cláusula a cláusula.
- **Bindings**: todos os argumentos que as cláusulas usam são ligados no pointcut e passados
  ao monitor na ordem do descriptor (conferido nos 14 `args` do descriptor contra as
  assinaturas `Prop_1_event_*`). `ranGen`, `params`, `plainText` e `keyOrCert` chegam;
  discriminação por `instanceof` nos corpos (RuntimeMonitor `:518-526`, `:541-547`).
- **`__LOC`**: presente em 9 pontos dos corpos + @fail; expande para
  `com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()`
  (RuntimeMonitor `:501,519,521,524,543,544,546,621,646,671`) — resolução em **runtime** por
  varredura de pilha (ver ameaça A2).
- **condition(...)**: as guardas dos 5 eventos condicionados (g1, g3, init2, init3, init4)
  são compiladas como prólogo do corpo com `return false` ANTES de `handleEvent`
  (ex.: `:461-470`, `:494-505`) — supressão silenciosa sem transição. É o comportamento
  documentado pelo próprio `.mop` (comentário das linhas 136-149). Ponto de falsificação
  encontrado no mecanismo genérico: **BETA-CIP-06** abaixo.

### BETA-CIP-06 — handlers disparados por flags obsoletas em evento suprimido

O wrapper estático chama `matchedEntry.Prop_1_event_X(...)` e **ignora o retorno booleano**;
em seguida testa as flags voláteis `Category_fail`/`Category_match1` e executa os handlers
(`RuntimeMonitor:917-924`, padrão repetido nos 14 wrappers). Quando a condição falha, o evento
retorna `false` antes de atualizar as flags — que retêm o valor do **evento anterior** daquele
monitor. Sequência concreta: cipher em `end` via f2 (match1=true, handler já executou) →
`init(...)` com chave não validada → init2 suprimido → wrapper vê match1==true →
**`Prop_1_handler_match1` re-executa**. Para o fail não há re-disparo: o handler fail termina
em `__RESET` e `reset()` zera as flags (`:684-689`). Impacto nesta spec: benigno
(`setObjectAsInAcceptingState(cipher)` re-aplicado a objeto já aceitante), mas é um defeito
de mecanismo do gerador: viola a distinção obrigatória (c) do modelo semântico §5 — supressão
não deveria produzir efeito de handler. Em specs cujo @match tem efeito não idempotente,
vira FP de predicado. PROVADO por leitura do artefato (determinístico).

## 3. Autômato efetivo — OBSERVADO_EM_ARTEFATO

Ver `beta_autometa_efetivo_cipher.md`. Resumo da conferência: todas as transições do bloco
`fsm` do `.mop` presentes; completamento implícito → fail; `start`/`unsafeAlg` fundidos pelo
minimizador (linhas idênticas — sem efeito de linguagem); fail executa handler e reseta para
o estado inicial; todo evento é creation event (monitor nasce em qualquer evento).

## 4. Matcher vs API real — MEDIDO (PointcutBudget de produção)

Harness da skill sobre o `PointcutMatcher` de produção (pointcut-engine `target/classes` +
classpath offline), membros extraídos por `api_members.py` do
`$ANDROID_HOME/platforms/android-30/android.jar` (SHA-256 `96ccfdc8…`, o mesmo congelado na
fase 0). 28 membros na mesa (incl. vizinhos getIV, unwrap, updateAAD). Saída integral:
scratch `beta/budget_cipher.out`.

| Evento | Esperado (regra) | Capturado | Veredito |
|---|---|---|---|
| g1/g3 | getInstance ×3 (g1, g2 com `_`) | `getInstance/1, /2, /2#2` | Esperado ⊆ Capturado ✓ |
| init2 | i1, i3 (aridade 2) | `init/2, init/2#2` | ✓ |
| init3 | i2, i4, i5, i8 (aridade 3) | `init/3, /3#2, /3#3, /3#4` | ✓ |
| init4 | i6, i7 (aridade 4) | `init/4, init/4#2` | ✓ |
| u1 | u1, u2 | `update/1, update/3` | ✓ |
| u3 | u3, u4 | `update/4, update/5` | ✓ |
| u5 | u5 | `update/2` | ✓ |
| wkb1 | wrap | `wrap/1` | ✓ |
| f1 | f1 | `doFinal/0` | ✓ |
| f2 | f2, f4 | `doFinal/1, doFinal/3` | ✓ |
| f3 | f3 | `doFinal/2` | ✓ |
| f5 | f5, f6 | `doFinal/4, doFinal/5` | ✓ |
| f7 | f7 | `doFinal/2#2` | ✓ |

`DISJOINT no member is matched by two candidates`; `UNMATCHED [getIV/0, unwrap/3,
updateAAD/1, updateAAD/3, updateAAD/1#2]` — exatamente os vizinhos que NÃO devem casar.
Cobertura 28/28 particionada: 3+8+5+7+1 casados, 5 vizinhos livres. **Capturado ∩ Vizinhos = ∅**.

**Impacto do achado G10 (android.jar lexicográfico) medido**: mesma mesa extraída do
`android-37.0/android.jar` (o que a variante dexlib2 resolve de fato) → **conjunto de membros
idêntico** para getInstance/init/update/doFinal/wrap/getIV/unwrap/updateAAD e mesma saída do
matcher (DISJOINT, mesmos UNMATCHED). Para CipherSpec o defeito G10 não altera o matching hoje.

## 5. Hipóteses GH100 — verificação nos artefatos de hoje

| Modo de falha (gh100) | Estado no artefato/código de hoje | Evidência |
|---|---|---|
| Emissão só do 1º monitorCall (INV-INS-104) | ausente no emissor: laço sobre todos os calls | `advice-emitter/.../MonitorInvokeBuilder.java:69-78`; descriptor de hoje tem N=2 (g1) e, no conjunto, 18×N=2 e 1×N=4 |
| Colisão de chave de wrapper (D-B1) | wrapper fundido por chamada; registry falha-alto | `WrapperEmitter.java:243` (merge), `DexWeaver.java:172-173` (`IllegalStateException`) |
| commonPointcut fail-open | parse falha o weave | `DexWeaver.java:876-880` |
| Validador lê só o 1º monitorCall (INV-INS-106) | itera todos | `validator/.../BaksmaliDiffer.java:235` |

Nível DEX (invokes de fato tecidos, multiplicidade por sítio): **NÃO_VERIFICADO nesta rodada**
— sem weaving de APK no piloto; a evidência V0/V2 de `openspec/changes/gh100-*/evidence/`
permanece alegação de terceiro.

## 6. Ameaças à validade registradas

- **A1 — creation em todo evento**: um `Cipher` cujo `getInstance` ocorre em código excluído
  pelo `BaseAspect.notwithin()` (ex.: dentro de `javax..*`/biblioteca) tem o primeiro evento
  observado no `init` → monitor nasce em 0 e init: 0→fail → FP de sequência. Mecanismo
  JavaMOP, não desta tradução; requer APK para quantificar.
- **A2 — `__LOC` sob DEX**: `ViolationRecorder.makeRelevantList` só filtra um frame se
  `fileName != null` (`rv-monitor-rt/.../ViolationRecorder.java:87-105`). Em DEX sem atributo
  SourceFile, frames `mop.*` têm `fileName == null` e **não são filtrados** → `__LOC` pode
  apontar o frame do próprio monitor em vez do app. INCONCLUSIVE sem dispositivo.
- **A3 — semântica de `after` puro entre weavers**: ajc implementa `after()` como
  after-finally (dispara também em exceção — p.ex. `BadPaddingException` em `doFinal`);
  o emissor dexlib2 insere o invoke inline imediatamente após o call
  (`AfterEmitter.java:17-20`), cujo comentário alega semântica finally, mas uma instrução
  inline após o call não executa quando a exceção propaga sem handler. Divergência potencial
  ajc×dexlib2 na dimensão 7 para u3/u5/f3/f5/f7 (em exceção: ajc transiciona para `end`
  — aceitação de uma operação que falhou —, dexlib2 não transiciona). INCONCLUSIVE sem
  weave+execução; nenhum dos dois lados foi exercitado aqui.
- **A4 — javamop exit 0 com erro**: com diretório de saída inexistente o binário escreve o
  erro em stderr e **retorna 0** (medido). A produção compensa (cria o diretório antes e
  trata stderr como falha — `rv_android_core/util/utils.py:42-47`); uso manual fora do
  pipeline é fail-open.

## 7. Síntese

Geração limpa e determinística nos três modos; orçamento saturado confirmado em
14×(2¹⁴−1)=229.362 com custo real 6,66 s/1,04 GB (individual) e 28,09 s/1,71 GB no conjunto
de produção; cadeia advice→monitorCall fiel (cardinalidade, ordem, bindings, posições);
matcher de produção particiona exatamente os 28 membros do android-30 (e do android-37.0)
sem vazamento. Defeito de mecanismo real: re-disparo de handler @match sobre evento suprimido
(BETA-CIP-06, minor aqui, major como padrão). Pendências de dispositivo/APK: multiplicidade
no DEX, `__LOC` sob DEX, semântica de `after` em exceção.
