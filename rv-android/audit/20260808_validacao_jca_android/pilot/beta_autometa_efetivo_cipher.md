# Autômato efetivo — CipherSpec (extraído do artefato gerado)

Agente Beta, 2026-08-08. Fonte: `CipherSpecRuntimeMonitor.java` gerado em scratch pela toolchain
efetiva (JavaMOP jar `ab4e3765…`, rv-monitor.jar `fab40319…`) a partir de
`CipherSpec.mop` SHA-256 `c9deafb2acb2b2d75e55fe1c62b4f948685aa7e23142a71c5d883c8bb74d2de5`.
Artefato: SHA-256 `3cc74f2e80a19046779026bcb660bf01363a1076fa59ae88301e5d7d9cab6e0e`
(scratch `beta/gen_cipher/out/CipherSpecRuntimeMonitor.java`). O `.rvm` intermediário
(`5d7b16bf…`) é byte-idêntico nas gerações individual, em par e no conjunto completo de 23 specs.

## Codificação dos estados

Tabelas de transição: `CipherSpecRuntimeMonitor.java:405-418` (uma tabela `int[]` por evento,
indexada pelo estado corrente). Estado inicial: `0` (construtor, `:426`; `__RESET` → `:685`).
Categorias (`:472-473` e homólogas): **fail = estado 5**, **match1 = estado 4**.

| Código | Nome reconstruído (vs `.mop`) | Observação |
|---|---|---|
| 0 | `start` ∪ `unsafeAlg` | **fundidos pelo minimizador** — no `.mop` os dois estados têm linhas idênticas (g3→unsafeAlg≡0, g1→s1), logo são bisimilares; a fusão preserva a linguagem |
| 3 | `s1` | pós-getInstance |
| 1 | `s2` | pós-init |
| 2 | `s3` | pós-update |
| 4 | `end` (= alias `match1`) | aceitante; handler `Prop_1_handler_match1` (`:676-680`): `setObjectAsInAcceptingState(cipher)` |
| 5 | `fail` | toda célula não declarada no `.mop`; handler `Prop_1_handler_fail` (`:669-674`): `ErrorCollector.addError(InvalidSequenceOfMethodCalls, …)` + `reset()` → estado 0 |

## Tabela de transições efetiva (linha = evento; coluna = estado corrente; célula = próximo estado)

Transições implícitas (não declaradas no `.mop`) estão marcadas `*` — todas vão a 5 (fail).

| evento | 0 start/unsafeAlg | 3 s1 | 1 s2 | 2 s3 | 4 end | 5 fail | fonte |
|---|---|---|---|---|---|---|---|
| g1 | 3 | 5* | 5* | 5* | 5* | 5* | `:405` `{3,5,5,5,5,5}` |
| g3 | 0 | 5* | 5* | 5* | 5* | 5* | `:406` `{0,5,5,5,5,5}` |
| init2 | 5* | 1 | 5* | 5* | 5* | 5* | `:407` `{5,5,5,1,5,5}` |
| init3 | 5* | 1 | 5* | 5* | 5* | 5* | `:408` idem |
| init4 | 5* | 1 | 5* | 5* | 5* | 5* | `:409` idem |
| u1 | 5* | 5* | 2 | 5* | 2 | 5* | `:410` `{5,2,5,5,2,5}` |
| u3 | 5* | 5* | 2 | 5* | 2 | 5* | `:411` idem |
| u5 | 5* | 5* | 2 | 5* | 2 | 5* | `:412` idem |
| wkb1 | 5* | 5* | 4 | 5* | 4 | 5* | `:413` `{5,4,5,5,4,5}` |
| f1 | 5* | 5* | 5* | 4 | 5* | 5* | `:414` `{5,5,4,5,5,5}` |
| f2 | 5* | 5* | 4 | 4 | 4 | 5* | `:415` `{5,4,4,5,4,5}` |
| f3 | 5* | 5* | 5* | 4 | 5* | 5* | `:416` `{5,5,4,5,5,5}` |
| f5 | 5* | 5* | 4 | 4 | 4 | 5* | `:417` idem f2 |
| f7 | 5* | 5* | 4 | 4 | 4 | 5* | `:418` idem f2 |

Conferência contra o bloco `fsm` do `.mop` (linhas 288-326): todas as transições declaradas
estão presentes com o mesmo destino; nenhuma transição extra além do completamento implícito
para fail. `f1` e `f3` **não** são admitidos em `s2` nem em `end` (comentário do `.mop`:
"s2 admits no bare doFinal() by design"); `end` re-admite u\*/wkb1/f2/f5/f7 e o efetivo
confirma (coluna 4).

## Semântica operacional que a tabela sozinha não mostra (do artefato)

1. **fail não é absorvente na prática**: o handler fail executa `reset()` (`:672-673` via
   `__RESET`) → o monitor volta ao estado 0 com flags limpas (`reset()` `:684-689` zera
   `Category_fail`/`Category_match1`).
2. **`condition(false)` não transiciona**: cada `Prop_1_event_*` avalia a condição traduzida
   como guarda no prólogo do corpo e faz `return false` ANTES de `handleEvent` (ex.: g1 em
   `:461-470`, init2 em `:494-505`). Supressão silenciosa — nem transição, nem handler novo
   (mas vide claim BETA-CIP-06 sobre flags obsoletas).
3. **Todo evento é creation event**: os 14 wrappers estáticos criam monitor quando não há
   entrada no mapa (14 ocorrências de `new CipherSpecMonitor()`, ex. `:907-915`). Um `init`
   sobre um Cipher cujo `getInstance` não foi observado cria monitor em 0 e transiciona
   init: 0→5 = fail imediato.
4. **g1/g3 são disparados pelo MESMO advice** (um pointcut, dois monitorCalls, ordem g1;g3 —
   `CipherSpecMonitorAspect.aj:60-66`); a discriminação é feita pelas guardas complementares
   `isValid` / `!isValid` dentro do monitor: exatamente um dos dois transiciona por chamada.
