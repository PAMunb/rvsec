# Autômatos efetivos — Batch A (extraídos dos artefatos gerados)

Agente Beta, 2026-08-09. Fonte: os `*RuntimeMonitor.java` do insumo comum da rodada
(`batchA/generation_manifest.md`), hashes conferidos antes do uso (20/20 idênticos) e
**re-gerados de forma independente** neste parecer (byte-idênticos — ver `beta_report.md` §0).
Formato do piloto (`pilot/beta_autometa_efetivo_gcm.md`): codificação de estados, tabelas por
evento, eventos de criação, estados fail/match, tudo citado por arquivo:linha do artefato.

Convenções comuns aos cinco monitores:

- **Estados**: 0 = start (inicial), 1 = match (aceitante), 2 = fail. Categorias calculadas
  após cada `handleEvent`: `fail = (nextstate == 2)`, `match = (nextstate == 1)`.
- **Criação**: todo evento é evento de criação — cada wrapper estático faz FindOrCreateEntry
  e cria o monitor se ausente (ex.: `SecretKeySpecSpecRuntimeMonitor.java:402-410`).
- **`condition(false)` = supressão sem transição**: o prólogo `return false` executa **antes**
  de `handleEvent` (padrão confirmado em todos; ex.: SKS `:187` antes de `:194`).
- **@fail** executa `ErrorCollector.addError(InvalidSequenceOfMethodCalls, <spec>, __LOC)` +
  `reset()` → estado volta a 0. **@match** grava as Properties do `.mop` e
  `setObjectAsInAcceptingState`.
- Tabelas idênticas no artefato por spec e no `MultiSpec_1RuntimeMonitor.java` do modo
  -merge de produção (verificado por extração nas duas gerações; ver `beta_report.md` §6).

## DHGenParameterSpecSpec — alfabeto {c1}

Arquivo: `gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecRuntimeMonitor.java`
(sha256 `90aaf45b…`). Tabela `:68`; evento `:110-125`; handlers fail `:127`, match `:135`;
reset `:143`. Indexação **por objeto** `s` (`MapOfMonitor`, `:206`).

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (ctor 2-int, `exponentSize < primeSize`) | 1 | 2 | 2 | `:68` |
| c1 com `condition(false)` | — (sem transição, `:113`) | — | — | `:110-114` |

Linguagem efetiva por objeto: exatamente um c1 conforme. fail = 2 exige **segundo** c1 no
mesmo monitor — inalcançável em execução real (objeto novo por construção; demonstrado
executável em `beta_BetaDrive.java`, cenário DHG-c: só um segundo evento artificial no mesmo
objeto dispara o @fail).

## HMACParameterSpecSpec — alfabeto {c} — **monitor GLOBAL (não paramétrico)**

Arquivo: `gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecRuntimeMonitor.java`
(sha256 `adebef51…`). Tabela `:94`; evento `:128-141` (backend síncrono: `Prop_1_state`,
`:138-140` — este monitor usa `AbstractSynchronizedMonitor`, `:79`, e não o backend atômico
dos outros quatro); handlers fail `:144`, match `:152`; reset `:160`.

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c (ctor 1-int, sem condition) | 1 | 2 | 2 | `:94` |

**Escopo do monitor**: a árvore de indexação é um `Tuple2` estático único
(`HMACParameterSpecSpec__Map`, `:212`; FindOrCreateEntry retorna sempre a mesma tupla,
`:236-239`) — **um único monitor por processo**, porque o parâmetro da spec
(`hmacParameterSpec`) não é ligado por nenhum evento (o evento liga `s`;
`HMACParameterSpecSpec.mop:17,21`; `.rvm:7,10`; `// RVMRef_hmacParameterSpec was
suppressed`, `:167`). Consequência sobre o trace global: a **segunda construção legal**
de um `HMACParameterSpec` distinto leva o monitor único de 1→2 e dispara
`InvalidSequenceOfMethodCalls` — FP demonstrado em execução (3 repetições idênticas,
`beta_betadrive_hmc.out`), com o segundo objeto negado `PREPARED_HMAC`. Mesmo `Tuple2`
global no artefato -merge de produção (`MultiSpec_1RuntimeMonitor.java:9462`).

## PBEParameterSpecSpec — alfabeto {c1, c2, c3}

Arquivo: `gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecRuntimeMonitor.java`
(sha256 `42bf007b…`). Tabelas `:115-117`; eventos `:159` (c1), `:176` (c2), `:193` (c3);
handlers fail `:210`, match `:218`; reset `:226`. Indexação por objeto `s` (`:307`).

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (ctor 2-arg, iter≥10000 ∧ RANDOMIZED(salt)) | 1 | 2 | 2 | `:115` |
| c2 (ctor 3-arg, mesma condição) | 1 | 2 | 2 | `:116` |
| c3 (ctor 2-arg, ¬condição; corpo emite UnsafeAlgorithm) | 0 | 2 | 2 | `:117` |
| qualquer evento com `condition(false)` | — (sem transição) | — | — | `:162/:179/:196` |

Linguagem efetiva por objeto: `c3* (c1 | c2)` — fiel ao ERE do `.mop`. **Não há c4**: a
construção 3-arg violadora (c2 com condição falsa) não tem evento negativo — nenhuma
transição, nenhum erro (silêncio total, demonstrado executável). fail = 2 inalcançável em
execução real (mesmo argumento por objeto).

## IvParameterSpecSpec — alfabeto {c1, c2, c3, c4}

Arquivo: `gen_IvParameterSpec/out/IvParameterSpecRuntimeMonitor.java` (sha256 `0fb95150…`).
Nota de nomeação: classe pública derivada do NOME DO ARQUIVO (`IvParameterSpecRuntimeMonitor`,
`:340`), classes internas e wrappers derivados do NOME DA SPEC (`IvParameterSpecSpecMonitor`,
`:123`; `IvParameterSpecSpec_c1Event`, `:374`). Tabelas `:137-140`; eventos `:182` (c1),
`:199` (c2), `:216` (c3), `:233` (c4); reset `:266`. Indexação por objeto `s` (`:356`).

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (ctor 1-arg, RANDOMIZED(iv)) | 1 | 2 | 2 | `:137` |
| c2 (ctor 3-arg, RANDOMIZED ∧ offsets válidos) | 1 | 2 | 2 | `:138` |
| c3 (ctor 1-arg, ¬RANDOMIZED; corpo emite UnsatisfiedConstraint) | 0 | 2 | 2 | `:139` |
| c4 (ctor 3-arg, ¬RANDOMIZED; idem) | 0 | 2 | 2 | `:140` |

Linguagem efetiva por objeto: `(c3 | c4)* (c1 | c2)` — fiel ao ERE. Partição de condições:
c1/c3 complementares; c2/c4 **não** complementares no espaço de predicados (RANDOMIZED ∧
offsets inválidos ⇒ nenhum evento), mas a lacuna é inalcançável via `after returning` na
implementação JDK (toda construção com offsets inválidos lança exceção — medido,
`beta_betadrive_run1.out`, IVP-e; libcore Android INFERIDO igual, ameaça registrada).
fail = 2 inalcançável em execução real.

## SecretKeySpecSpec — alfabeto {c1, c2, c3, c4}

Arquivo: `gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java` (sha256
`2216bf9a…`). Tabelas `:139-142`; eventos `:184` (c1), `:201` (c2), `:218` (c3), `:235`
(c4); handlers fail `:252`, match `:260` (grava GENERATED_KEY **e** SPECCED_KEY, `:263-264`);
reset `:269`. Indexação por objeto `secretKeySpec` (`:359`).

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (ctor 2-arg, alg∈whitelist ∧ RANDOMIZED(km)) | 1 | 2 | 2 | `:139` |
| c2 (ctor 4-arg, alg∈whitelist ∧ len ok — **sem** RANDOMIZED) | 1 | 2 | 2 | `:140` |
| c3 (ctor 2-arg, ¬(c1); corpo emite UnsatisfiedConstraint) | 0 | 2 | 2 | `:141` |
| c4 (ctor 4-arg, ¬(c2); idem) | 0 | 2 | 2 | `:142` |

Linguagem efetiva por objeto: `(c3 | c4)* (c1 | c2)` — fiel ao ERE. c1/c3 e c2/c4
complementares (exatamente um evento por construção — demonstrado executável). O parêntese
excedente no `.mop` (`SecretKeySpecSpec.mop:30`) foi engolido pelo parser sem diagnóstico e
não altera a condição efetiva (`.rvm` byte-idêntico ao de uma cópia corrigida — sonda p1/p2,
`beta_report.md` §7). fail = 2 inalcançável em execução real.

## Advice → wrappers (par por pointcut compartilhado)

Nos três specs com ramos violadores (PBE, IVP, SKS) o gerador funde os eventos de MESMO
pointcut em **um advice com dois monitorCalls em sequência** (ex.:
`SecretKeySpecSpecMonitorAspect.aj:39-44` chama `c1Event` e depois `c3Event`; descriptor
1:1 na mesma ordem). Toda construção monitorada executa os dois wrappers sobre o MESMO
monitor; a discriminação é feita pelas conditions complementares (um dos dois faz
`return false` antes de `handleEvent`). O wrapper do evento suprimido ainda testa as flags
de categoria — **obsoletas** do evento anterior — e re-executa o handler (@match roda duas
vezes por construção conforme; demonstrado executável por remoção-e-reescrita da Property,
`beta_betadrive_run1.out` PBE-a-stale/SKS-a-stale). Benigno aqui (handlers idempotentes);
defeito de mecanismo do gerador, herdado do piloto (FEN-SET-flags-obsoletas).
