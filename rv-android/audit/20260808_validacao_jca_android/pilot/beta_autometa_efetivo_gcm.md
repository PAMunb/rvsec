# Autômato efetivo — GCMParameterSpecSpec (extraído do artefato gerado)

Agente Beta, 2026-08-08. Fonte: `GCMParameterSpecSpecRuntimeMonitor.java` gerado em scratch
pela toolchain efetiva a partir de `GCMParameterSpecSpec.mop` SHA-256
`18c84f8f64f3b5dde60ee06aee1e2cfd86e5468c32b005567f5e79f1e4355fe5`.
Artefato: SHA-256 `2f3ba6f442b63e9271f64fded80b31a8d1342f25eb547cc26afda72577e83076`
(scratch `beta/gen_gcm/out/GCMParameterSpecSpecRuntimeMonitor.java`). `.rvm` `e5e50fbc…`
byte-idêntico nas gerações individual, em par e no conjunto de 23.

## Alfabeto efetivo: {c1} — o `c2` do ERE não existe no artefato

O `.mop` declara **duas** definições de evento ambas nomeadas `c1` (linhas 23 e 34 — a segunda
era claramente para chamar-se `c2`) e o ERE é `c1 | c2` (linha 48). A toolchain aceitou sem
warning (exit 0 nas duas fases). No monitor gerado:

- existe **uma única tabela de transição**, `Prop_1_transition_c1` — `GCMParameterSpecSpecRuntimeMonitor.java:93`;
- as duas definições viram **dois carriers do mesmo evento** (métodos sobrecarregados
  `Prop_1_event_c1`, `:135` e `:152`; wrappers estáticos `GCMParameterSpecSpec_c1Event`,
  `:270` e `:327`), um por construtor;
- `c2` é símbolo morto: nenhuma tabela, nenhum advice, nenhum wrapper.

## Codificação dos estados

Tabela: `Prop_1_transition_c1[] = {1, 2, 2}` (`:93`), indexada pelo estado corrente.
Estado inicial 0 (construtor `:101`; `reset()` `:186` → 0 e zera flags).
Categorias (`:146-148`, `:163-165`): **match = estado 1**, **fail = estado 2**.

| Código | Papel | Handler |
|---|---|---|
| 0 | start | — |
| 1 | aceitante (match) | `:176-181`: `setProperty(PREPARED_GCM, spec)` + `setObjectAsInAcceptingState(spec)` |
| 2 | fail | `:169-174`: `ErrorCollector.addError(InvalidSequenceOfMethodCalls, "GCMParameterSpecSpec", __LOC)` + `reset()` |

## Tabela de transições efetiva

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (qualquer dos 2 construtores, condição satisfeita) | 1 | 2 | 2 | `:93` |
| c1 com `condition(false)` | sem transição (return false antes de `handleEvent`, `:137-143`/`:154-160`) | idem | idem |

Linguagem efetiva: **exatamente uma ocorrência de c1** = exatamente uma construção conforme
(qualquer aridade). Idêntica à intenção do ERE `c1 | c2` com c2 = segunda sobrecarga — a
colisão de nomes é neutralizada pelo acaso (dois carriers de um evento ≡ união dos dois
eventos quando cada um ocorreria no máximo uma vez e o ERE é uma disjunção 1-de-2).

## Alcançabilidade do fail (do artefato, não da sintaxe)

O estado 2 exige um **segundo** c1 no MESMO monitor. O monitor é indexado pelo objeto
`GCMParameterSpec s` ligado no `returning` — cada construção produz objeto novo, logo monitor
novo em estado 0. Consequência: **o @fail do GCM é inalcançável em execução real** e o
`InvalidSequenceOfMethodCalls` desta spec nunca é emitido. Violações de `tagLen`/`RANDOMIZED`
são supressões por condição (sem transição, sem erro local): `PREPARED_GCM` simplesmente não é
gravado e a acusação aparece uma chamada adiante, no `CipherSpec.init` (resíduo D-S9,
`CipherSpec.mop:88-92`).
