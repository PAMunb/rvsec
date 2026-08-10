# GAMA — Sinergia estático/dinâmico (piloto: Cipher, GCMParameterSpec)

Agente Gama · 2026-08-08.

## 1. Resolução do specification-set no caminho da análise estática — **FAIL**

Caminho dinâmico (monitores): mapeamento explícito por nome, sem fallback
(`modules/rv-experiment/src/rv_experiment/config.py:685-712`; inválido rejeitado). **Correto.**

Caminho estático (GATOR/mop-extractor): **cai silenciosamente em `jca`**:

1. `get_static_analysis_config()` (`rv_experiment/config.py:892-951`) constrói
   `RVStaticAnalysisConfig` **sem passar `mop_dir` nem `targets_file`** — o specification_set
   do experimento não entra na chamada.
2. `RVStaticAnalysisConfig.model_post_init` → `_resolve_paths()` → `_apply_default_paths()`
   roda **incondicionalmente** (`modules/rv-static-analysis/src/rv_static_analysis/config.py:152-161`;
   `validate_on_init=False` só pula a validação, não a resolução) e defaulta
   `mop_dir = <RVSEC>/rvsec/rvsec-mop/src/main/resources/`**`jca`**
   (`rv_static_analysis/config.py:199-206`, literal hardcoded).
3. GATOR recebe `-clientParam mopDir=<path>` (`rv_static_analysis/config.py:67-71`).

Consequência: numa execução `--specification-set jca_android`, o APK é instrumentado com o
conjunto derivado, mas mop-reachability, `mop_method_coverage` e a priorização MOP são
computados contra o conjunto **congelado**. Contradiz a ressalva da Fase 0 ("sem fallback
silencioso" — verdadeira apenas para o caminho dos monitores). Magnitude prática limitada pela
sobreposição em granularidade (classe, método) entre os dois conjuntos (não quantificada aqui —
NÃO_VERIFICADO), mas a identidade de regra está quebrada por construção.

Agravante correlato: o probe de `android_jar` da análise estática tenta as APIs
`["33","29","28","27","26"]` (`rv_static_analysis/config.py:186-194`) — **API 30, o oráculo,
não está na lista**; a estática nunca roda contra `android-30` por default.

## 2. Identidade compartilhada estático × dinâmico

- Lado estático: `rvsec-mop-extractor` emite `MopMethod(className, name, parameters, signature)`
  (`rvsec/rvsec-mop-extractor/.../model/MopMethod.java:10-19`).
- Lado dinâmico: `ErrorSummary` = (spec, tipo, classeFQN, método, linha) — **sem descritor**
  (`rvsec-core/.../eh/ErrorSummary.java`), pois vem de `StackTraceElement`.
- Join efetivo: **(classe, método)** apenas. Identidade de regra/cláusula CrySL **não existe em
  nenhum dos lados** — o estático não sabe qual cláusula alcançou; o dinâmico não nomeia
  cláusula (gate diagnóstico FAIL). `_`, agregados (`Inits`, `DOFINALS`, `Cons`) e semântica
  REQUIRES/ENSURES/NEGATES são invisíveis à estática (o extractor só extrai alvos de call).

## 3. Tabela por cláusula — Cipher.cryptsl (api30) × CipherSpec.mop

| Regra/cláusula | Fato estático possível | Binding/predicate no .mop | Evento/estado dinâmico | Diagnóstico emitido | Terceiro estado / limitação |
|---|---|---|---|---|---|
| ORDER `Gets, Inits+, w+ \| (FINWOU \| (updates+, DOFINALS))+` | alcançabilidade de cada membro (classe,método); ordem NÃO verificável estaticamente | fsm 6 estados (CipherSpec.mop:288-326); fusões D-S11 por aridade | transições; violação → estado 5 | `InvalidSeq` + "unknown", sem evento/estado | site inalcançável ≠ conforme; `condition(false)` suprime transição (não é aceitação) |
| CONSTRAINT allow-list transformation | string constante às vezes extraível; sem avaliação de `part()` | `isValid()` em `AndroidCipherTransformationUtil` (import CipherSpec.mop:14) | `g1`×`g3` por `condition` (117-130); reporte nos init (53-58) | `UnsafeAlgorithm` específico, conjunto esperado elidido "..." | transformação dinâmica (variável) invisível à estática |
| REQUIRES `generatedKey[key,…]` | aresta produtor KeyGenerator→Cipher no grafo de chamadas (aproximação) | `condition(...)` valida GENERATED_KEY/PUBLIC/PRIVATE (150-159, 171-179, 193-200) | condition false ⇒ **sem transição, sem report** | nada no init; `InvalidSeq` deslocado no doFinal seguinte | terceiro estado por excelência: supressão silenciosa (resíduo D-S9) |
| REQUIRES `randomized[ranGen]` | co-ocorrência SecureRandom no método (aprox.) | `reportUnrandomized` no corpo (63-68), lê RANDOMIZED | evento init3/init4 via `instanceof` | `UnsatisfiedConstraint` específico | colide no dedupe in-JVM com outras UnsatisfiedConstraint do mesmo sítio |
| REQUIRES `preparedIV[params]` / `preparedGCM[params]` (condicionais a modo) | co-ocorrência IvParameterSpec/GCMParameterSpec | `reportUnpreparedParams` (79-93); tabelas de modo no util | leitura no corpo (deliberado, não em condition) | `UnsatisfiedConstraint` específico; não distingue causa-raiz (ver GCM §4) | writer pode ter sido suprimido no produtor — o leitor não sabe |
| REQUIRES `!macced[_, plainText]` | não expressável estaticamente | `reportMacedPlainText` (101-106), lê MACED (projeção 2º lugar) | f2/f5 | `UnsatisfiedConstraint` específico | FN `ByteBuffer`; sobre-reporte cache de `Byte` (D-S13, registrados) |
| REQUIRES `preparedAlg[param,…]` | co-ocorrência AlgorithmParameters | **sem leitor** (arg ligado, leitura omitida — comentário 167-170) | init3/init5-branch | nada | omissão registrada (produtor sem .mop); leitor reportaria sempre |
| ENSURES `encrypted[...]` ×3 | n/a | `setProperty(ENCRYPTED, …)` em u*/f* | writes nos corpos | n/a (predicado) | write ocorre mesmo em trace que falha depois |
| ENSURES `generatedCipher[this]` (âncora 1.5.2, não api30) | n/a | write GENERATED_CIPHER dentro do condition dos init (161, 188, 207) | acoplado ao REQUIRES da chave (deliberado) | n/a | âncora dupla: nenhuma regra api30 nomeia o predicado |
| `noCallTo(IWOIV)` / `callTo(iv)` | **só a estática poderia**: presença de chamada a getIV/init-sem-IV é fato sintático | fora de escopo (tarefa 4.11; sem evento `getIV`) | não monitorado | nada | OMITIDA registrada — candidata a verificação estática, hoje nem estática nem dinâmica |

## 4. Tabela por cláusula — GCMParameterSpec.cryptsl (api30) × GCMParameterSpecSpec.mop

| Regra/cláusula | Fato estático possível | Binding/predicate | Evento/estado dinâmico | Diagnóstico | Terceiro estado / limitação |
|---|---|---|---|---|---|
| ORDER `Cons` (c1\|c2) | sítios de `new GCMParameterSpec` | dois eventos, ambos declarados `c1`; `ere: c1\|c2` com `c2` indefinido (mop:48) | autômato efetivo 1 evento, {1,2,2} | `@fail` **morto** | símbolo indefinido aceito fail-open pelo gerador |
| CONSTRAINT `tLen in {128,120,96,112,104}` | constante do arg às vezes extraível | dobrado no `condition` (mop:27, 38) | condition false ⇒ sem evento | **nenhum** — fail-silent | violação = silêncio; FN realizável se objeto não usado |
| REQUIRES `randomized[src]` | co-ocorrência SecureRandom.nextBytes (aprox.) | `validate(RANDOMIZED, src)` no `condition` (mop:28, 39) | idem | **nenhum** desta spec; deslocado p/ CipherSpec.init GCM | leitor downstream não distingue causa-raiz |
| ENSURES `preparedGCM[this]` | n/a | `@match`: `setProperty(PREPARED_GCM, spec)` (mop:56) | estado match (1) | n/a | só objetos plenamente conformes marcam — correto p/ CrySL, mas torna o par (writer suprimido, reader acusando requisito) indissociável |

Interpretação de `_` compartilhada: no CrySL de GCM não há `_`; no Cipher, `getInstance(transformation, _)`
vira `..` no pointcut (CipherSpec.mop:118) — consistente. Agregados (`Cons`, `Inits`, `DOFINALS`)
existem só no dinâmico (fsm); a estática não os representa. REQUIRES/ENSURES: a estática não tem
noção de predicado — qualquer gate "estático diz seguro" é inválido; `unknown`/não alcançado/não
observável são terceiros estados e o pipeline atual não os representa em lugar algum (um método
não listado no JSON do GATOR é indistinguível de "sem operação monitorada").
