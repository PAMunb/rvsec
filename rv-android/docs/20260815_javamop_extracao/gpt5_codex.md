# Lista de extração — gpt5_codex (validação externa 4)

**Fonte:** `docs/20260815_javamop_mensagens_gpt5_codex.md` (480 linhas), lida integralmente.
**Alvo do casamento:** `docs/20260815_javamop_mensagens_FINAL.md` (521 linhas), lido integralmente.
**Total de itens:** 202 | carregados: 166 | parciais: 16 | ausentes: 20

Convenção de classes: `cor-plano` = correção ao plano · `cor-review` = correção ao review ·
`anom` = anomalia nova · `prop` = proposta · `verif` = verificação confirmatória (inclui as linhas
de tabela de veredito, mesmo as que apenas confirmam).

Onde a coluna "rótulo próprio" diz **sem rótulo**, o relatório não dá identificador citável ao item
(caso de toda a §5 e de toda a §7, e de todas as linhas das tabelas §3).

| ID | linha | bloco | rótulo próprio | classe | conteúdo | status | onde no FINAL |
|---|---|---|---|---|---|---|---|
| X-001 | codex:7-13 | §0 Status and scope qualification | sem rótulo | verif | Este é um relatório de validação de primeiro estágio, não o protocolo científico completo pedido por `20260815_javamop_mensagens_validacao_prompt.md`; suficiente para bloquear o plano, insuficiente para certificar as 23 specs ou estabelecer causalidade runtime histórica por estrato do CSV | AUSENTE | — |
| X-002 | codex:19-24 | §1 Overall verdict | sem rótulo | cor-plano | O plano é INCOMPLETE e materially stale, embora o diagnóstico central seja sólido | CARREGADO | FINAL:72-73 (F9/F10); FINAL:113 (x-A1,x-A2) |
| X-003 | codex:20-23 | §1 Overall verdict | sem rótulo | cor-review | O review é mais forte e majoritariamente correto, mas não é prova independente: várias afirmações são exageradas, uma razão declarada para código morto é contradita pelo fonte atual, e a reprodução numérica não é preservada como artefato | CARREGADO | FINAL:143 (x-B2,x-B9); FINAL:502-506 (§10 errata) |
| X-004 | codex:28 | §1 durable core | sem rótulo | verif | O construtor de três argumentos de `ErrorDescription` literalmente fornece `"unknown"` (`ErrorDescription.java:34-36`) | CARREGADO | FINAL:47 |
| X-005 | codex:29 | §1 durable core | sem rótulo | verif | JavaFSM completa transições ausentes num sink implícito e define `@fail` como o predicado do estado sink | CARREGADO | FINAL:64 (F1) |
| X-006 | codex:30 | §1 durable core | sem rótulo | verif | O texto do handler é inserido num método de instância do monitor | CARREGADO | FINAL:65 (F2) |
| X-007 | codex:31 | §1 durable core | sem rótulo | verif | O CSV de referência tem 70.760 linhas `unknown`, exatamente as 70.760 linhas `InvalidSequenceOfMethodCalls` | CARREGADO | FINAL:43-44 (72,93 % de 97.018, "all and only") |
| X-008 | codex:33 | §1 Overall verdict | sem rótulo | cor-plano | O plano precede o reparo gh100, ignora gh101 e a rejeição de `jca_android`, trata um `jca` congelado como editável, erra semântica CrySL, assume um estado pré-falha indisponível em `@fail`, e propõe mudanças de esquema/identidade sem antes mudar os contratos registrados | CARREGADO | FINAL:73 (F10), 83-88 (§3), 66 (F3), 347-354 (§7.3) |
| X-009 | codex:37 | §1 Knocked down | sem rótulo | cor-review | Derrubado: a explicação do review de que `BaseMonitor.getHandlerCallingCode` é morto porque `EventDefinition.condition` nunca é atribuído é falsa — o construtor da AST JavaMOP atribui e remove `condition()` do pointcut (`EventDefinition.java:150-156`) | CARREGADO | FINAL:67 (F4); FINAL:111 (x-B1 "resolved") |
| X-010 | codex:38 | §1 Knocked down | sem rótulo | cor-review | Derrubado: "o merge de wrappers do gh100 é a causa direta de todo caso de valor vazio corrigido" é amplo demais; o efeito runtime pós-reparo não foi exercitado; o próprio gh100 registra que chegada de descriptor/DEX não prova chegada no logcat | CARREGADO | FINAL:146 (x-B3, x-B5) |
| X-011 | codex:39 | §1 Knocked down | sem rótulo | cor-review | Derrubado: o review rotula sua passagem de CSV como remedida independentemente mas não deixa script/saída duráveis; sua evidência numérica é `MEASURED`, não `PROVEN` | CARREGADO | FINAL:143 (x-B2); FINAL:427-432 (C-0) |
| X-012 | codex:43 | §1 Confirmations | sem rótulo | verif | CONFIRMADO: 97.018 linhas, 19 mensagens, 70.760 `unknown`, zero contraexemplos a `unknown ⇔ InvalidSequenceOfMethodCalls` | CARREGADO | FINAL:43-44, 72 (F9) |
| X-013 | codex:44 | §1 Confirmations | sem rótulo | verif | CONFIRMADO: entradas FSM faltantes são completadas para o sink extra e `fail condition` testa esse sink | CARREGADO | FINAL:64 (F1) |
| X-014 | codex:45 | §1 Confirmations | sem rótulo | verif | CONFIRMADO: o Study 03 usa `jca` congelado, mantém o reparo do weaver gh100 e reverte o `ExecutionContext` chaveado por identidade; `jca_android` continua NOT READY | CARREGADO | FINAL:73 (F10) |
| X-015 | codex:49-53 | §1 Recommendation | sem rótulo | prop | Refinar o corte T0/T1 do review em três portões: B0 (só evidência), T0 (contratos e transporte), T1 (conjunto sucessor autorizado, só após o pesquisador resolver a §7 da auditoria) | CARREGADO | FINAL:139 (x-B10); FINAL:403-423 (§8) |
| X-016 | codex:55 | §1 Recommendation | sem rótulo | prop | Mudanças de gerador/runtime (`previousState`, tabelas de nomes de evento, IDs estáticos de site, suporte a fim de traço) devem ser um T2 posterior, justificado por medições do T1 | CARREGADO | FINAL:196 (x-D1.5); FINAL:482-490 (O-1/O-2/O-7/O-8, "only if C-0/C-3 measurements justify") |
| X-017 | codex:61-73 | §2 Protocol and deviations | sem rótulo | verif | Desvio de protocolo: três subagentes cobriram três dimensões cada, não os nove passes isolados por dimensão exigidos; contexto cruzado pode ter influenciado conclusões | AUSENTE | — |
| X-018 | codex:75 | §2 Protocol and deviations | sem rótulo | verif | O revisor primário reabriu fontes materiais e rerodou as medições do CSV; concordância entre passes foi usada só para selecionar checagens discriminantes, nunca como prova | AUSENTE | — |
| X-019 | codex:77-85 | §2 Protocol and deviations | sem rótulo | verif | O MCP `sequential-thinking` não estava disponível e não foi simulado; substituído por um log científico explícito (Question/Hypothesis/Test/Evidence/Result/Uncertainty/Next decision) | AUSENTE | — |
| X-020 | codex:87 | §2 Protocol and deviations | sem rótulo | verif | Nenhum emulador iniciado/gerenciado; nenhuma geração de monitor necessária; computações temporárias via stdin; o repositório já estava muito sujo e todas as mudanças pré-existentes foram preservadas | PARCIAL | FINAL:89 (§3 "no emulator by hand") — a ressalva do repositório sujo não foi carregada |
| X-021 | codex:89-100 | §2 activities not represented as completed | sem rótulo | verif | Sete atividades deliberadamente não representadas como completas (sem geração/compilação fresca; sem harness JVM/mutação/model checker; sem replay G10/dispositivo; V4 não readjudicou todo D01–D50; 558 claims/119 fenômenos da auditoria não reproduzidos; pacote gh100/gh101 não rematerializado byte a byte; pacote durável script/hash/output não criado) | PARCIAL | FINAL:365-376 (§7.5 como portões propostos), FINAL:427-432 (C-0) — ver X-184, X-186 |
| X-022 | codex:105-111 | §2 Evidence classes | sem rótulo | prop | Taxonomia de cinco classes de evidência: PROVEN / MEASURED / OBSERVED_IN_ARTIFACT / INFERRED / NOT_VERIFIED | PARCIAL | FINAL:103 usa esquema próprio `R`/`V+`/`V−`/`V±`/`U`; só `INFERRED` sobrevive (FINAL:74) |
| X-023 | codex:121 | §3 V1 (tabela) | sem rótulo | verif | Erros de três argumentos viram `unknown`: `ErrorDescription.java:34-36` `this(type, spec, location, "unknown")` — CONFIRMED | CARREGADO | FINAL:47 |
| X-024 | codex:122 | §3 V1 | sem rótulo | verif | Mensagem fora da identidade runtime: `ErrorDescription.java:132-134`; `ErrorSummary.java:73-119` compara spec/type/class/method/location — CONFIRMED | CARREGADO | FINAL:69 (F6) |
| X-025 | codex:123 | §3 V1 | sem rótulo | verif | O comportamento é deliberadamente fixado: `ErrorDescriptionTest.java:179-193`, dois `expecting` distintos são iguais e deduplicam em um — CONFIRMED | CARREGADO | FINAL:69 (F6, `:179-220`) |
| X-026 | codex:124 | §3 V1 | sem rótulo | verif | Transições faltantes entram num sink: `JavaFSM.java:112,133-142`, default é `countState`, sink anexado mapeia para si — CONFIRMED | CARREGADO | FINAL:64 (F1) |
| X-027 | codex:125 | §3 V1 | sem rótulo | verif | `@fail` é o predicado do sink: `JavaFSM.java:158` `fail condition = $state$ == countState` — CONFIRMED | CARREGADO | FINAL:64 (F1) |
| X-028 | codex:126 | §3 V1 | sem rótulo | verif | Corpo do handler inserido literalmente após substituições: `HandlerMethod.java:39-49,81-106`, `__RESET`→`this.reset()`, `ret += handlerCode` — CONFIRMED | CARREGADO | FINAL:65 (F2) |
| X-029 | codex:127 | §3 V1 | sem rótulo | verif | O corpo do evento precede o cálculo de estado/categoria: `BaseMonitor.java:434-454`, `monitoringBody` é emitido antes do código de categoria — CONFIRMED | CARREGADO | FINAL:337-338 (§7.2: "the body runs before the transition") |
| X-030 | codex:128 | §3 V1 | sem rótulo | cor-plano | Nomes de campo diretos não são portáveis em `@fail`: `BaseMonitor.java:145-165` pode selecionar um monitor atômico; `IMonitor.java:19,25` fornece acessadores — PLAN WRONG; REVIEW CONFIRMED | CARREGADO | FINAL:66 (F3); FINAL:112 (x-A8..A10) |
| X-031 | codex:129 | §3 V1 | sem rótulo | cor-plano | Estado pré-falha NÃO está disponível em `@fail`: JavaFSM transiciona antes da avaliação de categoria; só existem acessadores de estado atual e último evento — WRONG | CARREGADO | FINAL:66 (F3); FINAL:112 |
| X-032 | codex:130 | §3 V1 | sem rótulo | verif | A mensagem precisa ser composta antes do reset: `BaseMonitor.java:951-970` reseta último evento, estado e flags — CONFIRMED | CARREGADO | FINAL:338-341 (§7.2, "before `__RESET`") |
| X-033 | codex:131 | §3 V1 | sem rótulo | cor-plano | `condition()` é removido do pointcut e emitido como prólogo: `EventDefinition.java:150-156` atribui/remove; `RVDumpVisitor.java:47-51` emite `if (!(cond)) return false` — REVIEW CONFIRMED no mecanismo | CARREGADO | FINAL:67 (F4) |
| X-034 | codex:132 | §3 V1 | sem rótulo | cor-review | "`EventDefinition.condition` nunca é atribuído" — REVIEW WRONG; o mesmo `EventDefinition.java:150-154` atribui explicitamente | CARREGADO | FINAL:67 (F4); FINAL:111 (x-B1) |
| X-035 | codex:133 | §3 V1 | sem rótulo | cor-review | "`BaseMonitor.java:604-610` é morto" — REVIEW OVERSTATED: o fonte atual tem um ramo de condição em `:603-610` e nenhuma prova de fluxo de dados foi executada; classe `NOT_VERIFIED` | CARREGADO | FINAL:67 (F4 resolve como morto, "0 in oracles"); FINAL:111 |
| X-036 | codex:134 | §3 V1 | sem rótulo | verif | O collector Android não escapa mensagens: `ErrorCollector.java:36-40` chama `Log.v` cru; a chamada de escape está comentada — PLAN/REVIEW CONFIRMED | CARREGADO | FINAL:70 (F7) |
| X-037 | codex:135 | §3 V1 | sem rótulo | cor-plano | "Reabilitar a chamada comentada é seguro" — WRONG: `ErrorCollector.java:44-49` reconstrói o texto citado a partir do `data` original, preservando newline, e citaria a linha CSV inteira | CARREGADO | FINAL:70 (F7); FINAL:442-443 (C-1 "keep the whole-line call off") |
| X-038 | codex:136 | §3 V1 | sem rótulo | cor-review | "O collector JSE é plenamente canônico" — IMPRECISE: o collector CSV `:40-43,83-90` escapa só `expecting` e contém o mesmo bug de newline | CARREGADO | FINAL:70 (F7); FINAL:119 (x-B11) |
| X-039 | codex:137 | §3 V1 | sem rótulo | verif | O parser fabrica campos genéricos: `logcat_parser.py:305-316,352-368`, `error_type := spec`; a fonte do Format 3 é `Unknown Source:1` — CONFIRMED | CARREGADO | FINAL:70 (F7) |
| X-040 | codex:138 | §3 V1 | sem rótulo | verif | O writer atual tem onze colunas e `source`: cabeçalho exato em `result_processor.py:562-575` — CONFIRMED | CARREGADO | FINAL:71 (F8) |
| X-041 | codex:139 | §3 V1 | sem rótulo | verif | `unique_msg` tem cinco campos `:::` e exclui `source`: `log.py:90-113` — CONFIRMED | CARREGADO | FINAL:71 (F8) |
| X-042 | codex:140 | §3 V1 | sem rótulo | anom | A localização dinâmica guarda apenas um quadro: `ViolationRecorder.java:53-59` retorna `relevantStack.get(0)` — CONFIRMED | PARCIAL | FINAL:180 (c-C36, "runtime frame has no callee") e FINAL:489 (O-8) cobrem o entorno; a retenção de um único quadro e `relevantStack.get(0)` não são declaradas |
| X-043 | codex:141 | §3 V1 | sem rótulo | anom | Aloca uma stack a cada tentativa: `ViolationRecorder.java:37-38` `new Exception().getStackTrace()` — CONFIRMED | CARREGADO | FINAL:69 (F6); FINAL:184 ("`getStack` per attempt") |
| X-044 | codex:143 | §3 V1 (prosa) | sem rótulo | verif | A cobertura amostral excedeu quarenta localizações reabertas quando as entradas V3–V7 são incluídas | AUSENTE | — |
| X-045 | codex:151 | §3 V2 (tabela) | sem rótulo | verif | Linhas: todas as linhas de dados = 97.018 — ambos os documentos confirmados | CARREGADO | FINAL:43 |
| X-046 | codex:152 | §3 V2 | sem rótulo | cor-plano | Apps com erros: `apk` distintos em `errors.csv` = 113; os 163 do plano são contexto incompleto (163 é o corpus selecionado mais amplo) | CARREGADO | FINAL:72 (F9, "113 apps with errors of 163") |
| X-047 | codex:153 | §3 V2 | sem rótulo | verif | Mensagens distintas = 19 — confirmado | CARREGADO | FINAL:44, 72 |
| X-048 | codex:154 | §3 V2 | sem rótulo | verif | `message == "unknown"` = 70.760 (72,93 %) — confirmado | CARREGADO | FINAL:43, 72 |
| X-049 | codex:155 | §3 V2 | sem rótulo | verif | Erros do bicondicional (XOR de unknown e InvSeq) = 0 — confirmado | CARREGADO | FINAL:44 ("all and only") |
| X-050 | codex:156 | §3 V2 | sem rótulo | cor-plano | Sombra de pareamento: soma de `min(InvSeq, concrete)` por `(apk,rep,tool,spec,class,method)` = 26.152; número do plano confirmado, prosa imprecisa | PARCIAL | FINAL:72 (F9) mantém a distinção como "shadow 27 % is a min-pairing count"; o valor absoluto 26.152 e a chave de agrupamento não foram carregados |
| X-051 | codex:157 | §3 V2 | sem rótulo | cor-plano | Sombra de co-localização: linhas InvSeq em grupos contendo qualquer linha concreta = 32.411; correção do review confirmada | PARCIAL | FINAL:72 ("co-location gives 33,4 %"); valor absoluto 32.411 não carregado |
| X-052 | codex:158 | §3 V2 | sem rótulo | cor-plano | Grupos por chave temporal `(apk,rep,tool,time,spec,class,method)`: 46.330 no total; 20.507 mistos; 32.232 unknown em grupos mistos — confirmado, mas "evento" é mais forte do que a resolução do timestamp prova | PARCIAL | FINAL:72 carrega apenas "`time` is seconds"; os três quantitativos (46.330 / 20.507 / 32.232) não aparecem |
| X-053 | codex:159 | §3 V2 | sem rótulo | cor-plano | Funil: `(apk,spec,class,method,message)` distintos, depois remover unknown, depois vazios = 661 → 207 → 136 — confirmado | AUSENTE | FINAL:114 traz apenas "funnel 24–59 by definition" (número da ext. 1); 661/207/136 não constam |
| X-054 | codex:160 | §3 V2 | sem rótulo | cor-plano | Chaves exatas de dez colunas (linhas completas distintas) = 85.257 — confirmado | AUSENTE | — |
| X-055 | codex:161 | §3 V2 | sem rótulo | cor-plano | Excesso de duplicação: soma `(tamanho do grupo − 1)` para linhas exatas = 11.761 — definição confirmada | AUSENTE | — |
| X-056 | codex:162 | §3 V2 | sem rótulo | cor-plano | Maior grupo exato: multiplicidade máxima de linha exata = 6; os 3.098 do plano estão errados, review confirmado | CARREGADO | FINAL:72 (F9, "largest 10-column group = 6") |
| X-057 | codex:163 | §3 V2 | sem rótulo | cor-plano | Valor observado vazio: mensagem termina em `but found .` = 8.843 — confirmado | AUSENTE | FINAL só traz 8.371 (F11, número do review para o estrato pré-gh100) e 98 residuais no E3 (FINAL:128) |
| X-058 | codex:165 | §3 V2 (prosa) | sem rótulo | cor-plano | O quarto estágio do funil não é fato estável até "third-party" ser definido formalmente; "28 actionable findings", "73,4 %" e a amplificação 3.465× são **WRONG como medições universais** e podem ser saídas de um classificador não divulgado | CARREGADO | FINAL:72 (F9); FINAL:114 (x-A3..A5); FINAL:296 (D-F) |
| X-059 | codex:171 | §3 V3 (tabela) | sem rótulo | verif | Completude do sink: `JavaFSM.java:112-142,158` — CONFIRMED | CARREGADO | FINAL:64 (F1) |
| X-060 | codex:172 | §3 V3 | sem rótulo | anom | `@fail` persistente: o sink faz self-loop, as categorias do handler são avaliadas após eventos subsequentes, o reset normalmente rearma — CONFIRMED, com risco de volume por KPG sem reset | CARREGADO | FINAL:64 (F1); FINAL:259-262 (§5.2, KeyPairGeneratorSpec sem `__RESET`) |
| X-061 | codex:173 | §3 V3 | sem rótulo | verif | Reset: `BaseMonitor.java:951-970` reseta estado/flags locais gerados, não campos arbitrários da especificação — CONFIRMED | CARREGADO | FINAL:68 (F5); FINAL:184 ("root-slice inheritance") |
| X-062 | codex:174 | §3 V3 | sem rótulo | verif | Ordem do corpo do evento: `BaseMonitor.java:434-454` — CONFIRMED | CARREGADO | FINAL:337-338 (§7.2) |
| X-063 | codex:175 | §3 V3 | sem rótulo | cor-plano | Condição: prólogo JavaMOP em `RVDumpVisitor.java:47-51`; o mecanismo do plano está errado, mas a conclusão do buraco de traço é plausível | CARREGADO | FINAL:67 (F4); FINAL:111 |
| X-064 | codex:176 | §3 V3 | sem rótulo | verif | Forma do monitor: seleção atômica em `BaseMonitor.java:145-165`; acessadores portáveis em `IMonitor.java:15-25` — review confirmado | CARREGADO | FINAL:66 (F3) |
| X-065 | codex:177 | §3 V3 | sem rótulo | cor-plano | Estado pré-falha não é retido pela interface pública do monitor: WS-1.4 não é viável sem bookkeeping/suporte do gerador | CARREGADO | FINAL:66 (F3); FINAL:332-341 (§7.2 bookkeeping `stateBefore`) |
| X-066 | codex:178 | §3 V3 | sem rótulo | verif | IDs de evento: artefatos gerados enumeram métodos de evento em ordem de declaração — CONFIRMED para o gerador atual, deve ser testado por contrato antes de tabelas escritas à mão | CARREGADO | FINAL:77 (F14); FINAL:125 (x-A25); FINAL:369 (G-1, `EVENT_NAMES.length == getNumberOfEvents()`) |
| X-067 | codex:179 | §3 V3 | sem rótulo | cor-plano | IDs de estado: produzidos após minimização e podem fundir/renumerar estados simbólicos — tabela de estados escrita à mão rejeitada | CARREGADO | FINAL:125 ("never state names") |
| X-068 | codex:180 | §3 V3 | sem rótulo | verif | Declarações estáticas: declarações cruas do usuário e modificadores Java têm caminho de emissão válido; existe exemplo nos exemplos do JavaMOP — viável, mas não gerado num oráculo RVSEC aqui | CARREGADO | FINAL:65 (F2); FINAL:126 (`static final String[]` viabilidade, `U` no oráculo); FINAL:369 (G-1) |
| X-069 | codex:181 | §3 V3 | sem rótulo | cor-plano | `RVM_loc`: existem fragmentos comentados/threaded, mas a chamada de descriptor do dexlib2 carrega apenas argumentos de advice — não é um "re-enable"; é feature cross-tool | CARREGADO | FINAL:124 (c-A33, x-A23); FINAL:489 (O-8) |
| X-070 | codex:182 | §3 V3 | sem rótulo | cor-plano | Fim de traço: JavaMOP tem mecanismos `endProgram`/`endObject`; as specs RVSEC e o dexlib2 não os integram — plano incompleto, o raio proposto é gerador + weaver/runtime | CARREGADO | FINAL:77 (F14); FINAL:488 (O-7) |
| X-071 | codex:184 | §3 V3 (prosa) | sem rótulo | verif | Fan-out sem parâmetros/root-slice e clonagem são importantes mas não foram reexecutados dinamicamente; a magnitude da contaminação permanece `INFERRED` | CARREGADO | FINAL:68 (F5); FINAL:116 (x-A14) |
| X-072 | codex:190 | §3 V4 (tabela) | sem rótulo | anom | SecureRandom `nextBytes` repetido: `SecureRandom.crysl:38-39` permite `End*`; `SecureRandomSpec.mop:155-161` omite `next2` de `end` — desvio de tradução, falso positivo real | CARREGADO | FINAL:278 (§5.3); FINAL:466 (C-4) |
| X-073 | codex:191 | §3 V4 | sem rótulo | cor-plano | Cipher `doFinal()` sem update: `Cipher.crysl:75-85` exclui `f1` de `FINWOU` e exige `Update+` antes de `DoFinal`; `.mop:176-195` espelha a distinção — a alegação do plano de "código comum correto" está errada; o CrySL é intencionalmente estrito | CARREGADO | FINAL:282 (§5.3, "CrySL strictness (not a defect)"); FINAL:117 (x-A11..A13) |
| X-074 | codex:192 | §3 V4 | sem rótulo | cor-plano | Cipher re-init após conclusão: o `ORDER` do CrySL tem `Init+` só antes do uso — o rótulo de falso positivo do plano está errado contra o oráculo declarado | CARREGADO | FINAL:275 (§5.3 readjudica como defeito de tradução, `Update+`/`Init+`); FINAL:117, FINAL:155 |
| X-075 | codex:193 | §3 V4 | sem rótulo | anom | Construtor de KeyPair: `KeyPair.crysl:19-20` original começa com `Con`; api30 usa `co?` opcional; o `.mop` congelado `:23-41` exige o construtor e `jca_android` ainda exige — fiel ao oráculo original mas divergente do api30; os documentos precisam nomear o oráculo antes de chamar isso de falso positivo | CARREGADO | FINAL:279 (§5.3, "oracle choice"); FINAL:117, FINAL:158; FINAL:292 (D-B) |
| X-076 | codex:194 | §3 V4 | sem rótulo | anom | MessageDigest reset: o bloco event/order do CrySL não contém reset; `.mop:74-76` o declara mas `.mop:108` o omite da ERE — defeito de tradução "declarado mas não ordenado" | CARREGADO | FINAL:184 ("MD reset"); FINAL:298 (D-H, "declared-but-unordered events") |
| X-077 | codex:195 | §3 V4 | sem rótulo | anom | Propriedade privada de KeyPair: `.mop:35-39` armazena a chave privada como `GENERATED_PUBLIC_KEY` — defeito de autoria, já reparado no trabalho derivado | CARREGADO | FINAL:184 ("KeyPair slot") — rótulo comprimido, sem o nome `GENERATED_PUBLIC_KEY` |
| X-078 | codex:197 | §3 V4 (prosa) | sem rótulo | prop | Toda correção futura deve registrar a classe do oráculo como `[jca]`, `[gh101]`, `[tool]` ou `[oracle]`; "mais permissivo" não é sinônimo de "mais correto" — regras de disponibilidade e de recomendação diferem intencionalmente | CARREGADO | FINAL:292 (D-B, "More permissive ≠ more correct"); FINAL:212 (provenance tags); FINAL:358-360 (§7.4) |
| X-079 | codex:203 | §3 V5 (tabela) | sem rótulo | verif | Colisão pré-gh100: `gh92_e2e2/.../MonitorWrappers.java:588-616` contém múltiplos wrappers TMF de mesma assinatura; o gh100 registra perda por last-write e merge — mecanismo histórico confirmado | CARREGADO | FINAL:74 (F11) |
| X-080 | codex:204 | §3 V5 | sem rótulo | cor-plano | Truncamento: o censo do gh100 registra nove eventos descartados, oito emissores de erro — plano incompleto, review confirmado | PARCIAL | FINAL:73 (F10, "nine truncated events restored"); "oito emissores de erro" não foi carregado |
| X-081 | codex:205 | §3 V5 | sem rótulo | verif | Casamento de retorno: o `PointcutMatcher` do dexlib2 compara descriptors de retorno exceto com wildcard — defeitos de pointcut de Signature/TMF são reais no Android | CARREGADO | FINAL:75 (F12, `PointcutMatcher.java:361-364`) |
| X-082 | codex:206 | §3 V5 | sem rótulo | anom | Perda de debug: `RegisterShifter.cloneInstructions` reconstrói instruções/try blocks mas não itens de debug — mecanismo confirmado, impacto de campanha não medido | CARREGADO | FINAL:489 (O-8, "debug-item preservation in `RegisterShifter` + spill counter") |
| X-083 | codex:207 | §3 V5 | sem rótulo | anom | Escopo: as exclusões de descriptor omitem namespaces comuns de Android/Kotlin/Google/okhttp; a cobertura tem um filtro divergente — divisão de política confirmada | AUSENTE | Nenhuma menção; o `okio.` do FINAL:114/296 é o classificador de terceiros (item da ext. 1), não a política de exclusão de instrumentação |
| X-084 | codex:208 | §3 V5 | sem rótulo | verif | 8.371 vazios + 643 X509: colisão + herança de valor global/root prevê ambos os estratos e casa com o artefato pré-fix — alta confiança, não é prova runtime controlada | CARREGADO | FINAL:74 (F11); FINAL:139 (x-B3 via §4) |
| X-085 | codex:209 | §3 V5 | sem rótulo | verif | SecureRandom 12.400: o perfil de call-site e o descasamento CrySL/autômato sustentam o `next2` faltante; a colisão não explica os sites dominantes de `nextBytes` — hipótese preferida do review é mais forte, ainda não PROVEN sem replay | CARREGADO | FINAL:74 (F11); FINAL:140 (x-B4) |
| X-086 | codex:211 | §3 V5 (prosa) | sem rótulo | prop | O review acerta ao rebaixar a preservação de debug de "maior valor" para "real mas não medido"; um manifesto estático de sites de weave é uma primitiva de localização melhor do que expandir a stack dinâmica a cada violação, desde que o ID seja estável entre instrumentações e os joins não dependam de tabelas de linha removidas | PARCIAL | FINAL:489 (O-8) carrega o manifesto e a preservação de debug; as duas condições (ID estável entre instrumentações; joins não dependerem de tabelas de linha removidas) não aparecem |
| X-087 | codex:217 | §3 V6 (tabela) | sem rótulo | anom | Mensagem livre rica: vírgulas sobrevivem porque o Format 2 rejunta `parts[6:]`; newline pode virar um segundo registro RVSEC; `:::` corrompe o contrato de identidade de cinco partes | CARREGADO | FINAL:70 (F7) |
| X-088 | codex:218 | §3 V6 | sem rótulo | anom | Novas colunas CSV: quebram os testes do writer de onze colunas exatas, `INV-PLT-19`, o leitor de cabeçalho exato do gh103 e consumidores de campanha congelados, a menos que haja um delta OpenSpec coordenado | CARREGADO | FINAL:71 (F8); FINAL:347-354 (§7.3); FINAL:420 (C-2) |
| X-089 | codex:219 | §3 V6 | sem rótulo | prop | Sentinela sintética: muda valores genéricos de `unique_msg` e o agrupamento downstream, mas corrige a semântica de dados fabricados; deve ser explícita e versionada | CARREGADO | FINAL:326-327 (§7.1 sentinelas); FINAL:191 (x-D1.2) |
| X-090 | codex:220 | §3 V6 | sem rótulo | anom | Mensagem na identidade: inverte `ErrorDescriptionTest:179-193`, eleva a cardinalidade com valores observados e fica ilimitada se identidade de objeto aparecer no texto | CARREGADO | FINAL:319 (§7.1, "the free text never does"); FINAL:454 (C-2) |
| X-091 | codex:221 | §3 V6 | sem rótulo | prop | ID estruturado de evento/cláusula: alternativa limitada; requer modelo de runtime, mudanças de parser/esquema e de contrato de consumidor juntas | CARREGADO | FINAL:316-319 (§7.1 `code`); FINAL:200 (x-D2); FINAL:420 (C-2) |
| X-092 | codex:222 | §3 V6 | sem rótulo | cor-plano | Escaping: corrigir o helper é seguro enquanto ele estiver dormente; habilitar a citação de linha inteira é incompatível com o parser posicional atual | CARREGADO | FINAL:70 (F7); FINAL:442-443 (C-1) |
| X-093 | codex:223 | §3 V6 | sem rótulo | prop | Dedupe/rate limit: muda contagens por design; os totais suprimidos precisam ser emitidos para que a medição continue auditável | CARREGADO | FINAL:295 (D-E); FINAL:390 (§7.6.7); FINAL:485 (O-4) |
| X-094 | codex:225 | §3 V6 (prosa) | sem rótulo | prop | A heurística de três formatos do parser não é um esquema; o caminho gradual deve introduzir um marcador explícito de formato/versão antes de adicionar campos; até lá, manter a mensagem humana por último, em uma linha e livre de `:::` | CARREGADO | FINAL:307-314 (§7.1 envelope v1); FINAL:146 (x-B8) |
| X-095 | codex:231 | §3 V7 (tabela) | sem rótulo | cor-plano | gh101 design D-S0: `jca` permanece byte-idêntico; as correções aterrissam em `jca_android` — plano incompleto, review confirmado | CARREGADO | FINAL:73 (F10); FINAL:83-84 (§3) |
| X-096 | codex:232 | §3 V7 | sem rótulo | cor-review | Estado do gh101: a change continua aberta; conclusão de tarefas não implica prontidão de pesquisa — review confirmado | CARREGADO | FINAL:73 (F10); FINAL:146 (x-B6) |
| X-097 | codex:233 | §3 V7 | sem rótulo | verif | Auditoria global §10.1: `jca_android` NOT READY, 22/22 specs auditadas rejeitadas — confirmado | CARREGADO | FINAL:73 (F10); FINAL:85-86 (§3) |
| X-098 | codex:234 | §3 V7 | sem rótulo | verif | Auditoria global §7: dez decisões do pesquisador continuam necessárias — bloqueador confirmado para o tier de especificação | CARREGADO | FINAL:298 (D-H, as dez decisões nomeadas) |
| X-099 | codex:235 | §3 V7 | sem rótulo | cor-plano | Auditoria global §9: a lista de reparo de mensagem/spec já se sobrepõe a WS-1/2/3/7 — confirmado; os programas precisam se fundir | CARREGADO | FINAL:86-88 (§3, "folded into it (lane C)") |
| X-100 | codex:236 | §3 V7 | sem rótulo | verif | Study 03 D1: usa `jca` — confirmado | CARREGADO | FINAL:73 (F10); FINAL:83-84 |
| X-101 | codex:237 | §3 V7 | sem rótulo | verif | Study 03 D3: mantém o reparo gh100 — confirmado | CARREGADO | FINAL:73 (F10) |
| X-102 | codex:238 | §3 V7 | sem rótulo | verif | Study 03 D4: reverte `ExecutionContext` para semântica de igualdade — confirmado | CARREGADO | FINAL:73 (F10); FINAL:297 (D-G) |
| X-103 | codex:239 | §3 V7 | sem rótulo | cor-review | Consequência do D3: nove eventos de descriptor restaurados, mas a chegada runtime/logcat não foi demonstrada — o review precisa preservar essa limitação | CARREGADO | FINAL:146 (x-B5) |
| X-104 | codex:241 | §3 V7 (prosa) | sem rótulo | cor-plano | Achados da auditoria insuficientemente integrados por ambos os documentos: checagens de geração/compilação fail-closed, tratamento de primeiro disjunto, busca de membro apenas declarada, estreitamento de varargs, descriptors de tipo aninhado, seleção explícita de `android.jar` e o descasamento de conjunto no caminho estático — podem invalidar a interpretação da mensagem antes da qualidade dela | CARREGADO | FINAL:487 (O-6, os seis primeiros); FINAL:446 (C-1.7, "static-path set mismatch (G12)") |
| X-105 | codex:243 | §3 V7 (prosa) | sem rótulo | cor-review | O texto de status precisa de cuidado: o ledger do gh101 está 84/84 checado, mas a change continua aberta e seu produto foi depois rejeitado/revertido em parte; "task-complete" não é "READY", e "implementação inacabada" também enganaria | CARREGADO | FINAL:146 (x-B6, "'84/84' ≠ accepted") |
| X-106 | codex:247 | §3 V8 | sem rótulo | cor-plano | A Fase A original é internamente inconsistente: WS-3.1 muda `rvsec-core`, logo não é "só especificação" | CARREGADO | FINAL:121 (c-A30, x-A16); FINAL:418 (C-1 inclui `rvsec-core`) |
| X-107 | codex:247 | §3 V8 | sem rótulo | prop | WS-1 é viável só em forma reduzida: `getLastEvent()` mais uma tabela estável de eventos, variáveis existentes da especificação e a classe do objeto, tudo composto antes do reset | CARREGADO | FINAL:332-343 (§7.2); FINAL:193 (x-D1.1); FINAL:421 (C-3) |
| X-108 | codex:247 | §3 V8 | sem rótulo | cor-plano | Continuações esperadas exigem suporte a pré-estado; hashes de identidade não podem entrar nem na mensagem nem na identidade | CARREGADO | FINAL:282 (§4 correção 8 correlata); FINAL:322-323 (§7.1, "never a hash"); FINAL:319 |
| X-109 | codex:250 | §3 V8 (bullets) | sem rótulo | prop | Medição de baseline é B0, não um tier de implementação | CARREGADO | FINAL:190 (x-D1.0); FINAL:416 (C-0, radius "none") |
| X-110 | codex:251 | §3 V8 | sem rótulo | prop | O trabalho de sentinela/esquema do parser deve ser coordenado com o gh103 e com invariantes registradas | CARREGADO | FINAL:347-354 (§7.3); FINAL:418 (C-1, "gh103 co-schedule") |
| X-111 | codex:252 | §3 V8 | sem rótulo | prop | Um discriminador de formato/versão precede a extensão de esquema | CARREGADO | FINAL:307-314 (§7.1, `v=1`); FINAL:146 (x-B8) |
| X-112 | codex:253 | §3 V8 | sem rótulo | prop | T1 precisa se fundir com o programa de reparo da auditoria e exigir portões formais de autômato | CARREGADO | FINAL:86-88 (§3, lane C); FINAL:365-376 (§7.5) |
| X-113 | codex:254 | §3 V8 | sem rótulo | prop | O trabalho de gerador/runtime é um T2 distinto, não trabalho miscelâneo apenas adiado | CARREGADO | FINAL:478-490 (§9, opções O-1..O-9 com gatilhos) |
| X-114 | codex:257 | §3 V8 (prosa) | sem rótulo | prop | Critérios de aceitação devem usar micro-traços controlados, não só linhas de campanha completa; em particular, traços Cipher CrySL-estritos devem produzir uma violação explicativa, não zero | CARREGADO | FINAL:384-386 (§7.6.4); FINAL:376 (G-8) |
| X-115 | codex:263 | §3 V9 | sem rótulo | cor-review | A alegação de método do review de que toda citação decisiva foi reaberta não é auditável externamente; os scripts numéricos foram efêmeros | CARREGADO | FINAL:143 (x-B2) |
| X-116 | codex:264 | §3 V9 | sem rótulo | cor-review | O review ocasionalmente substitui uma explicação categórica por outra antes do isolamento experimental (causalidade do SecureRandom; fechamento runtime pós-merge) | CARREGADO | FINAL:140 (x-B4); FINAL:146 (x-B3) |
| X-117 | codex:265 | §3 V9 | sem rótulo | cor-review | A justificativa "condition nunca é atribuído" é contradita pelo fonte JavaMOP atual | CARREGADO | FINAL:67 (F4); FINAL:111 |
| X-118 | codex:266 | §3 V9 | sem rótulo | cor-review | Várias afirmações citam artefatos gerados ou de auditoria como se fossem prova de execução; deveriam permanecer `OBSERVED_IN_ARTIFACT` | CARREGADO | FINAL:143 (x-B9, "causal claims graded unevenly") |
| X-119 | codex:267 | §3 V9 | sem rótulo | cor-review | O review marca corretamente o volume de fim de traço como não medido, mas algumas afirmações causais vizinhas não recebem a mesma contenção | CARREGADO | FINAL:143 (x-B9) |
| X-120 | codex:269 | §3 V9 (veredito) | sem rótulo | cor-review | Veredito sobre o review: IMPRECISE mas cientificamente útil; deve ser emendado, não descartado | CARREGADO | FINAL:494-506 (§10 errata, "do not edit; list for the issue") |
| X-121 | codex:275 | §4 Corrections to the plan | #1 | cor-plano | Adicionar gh100, gh101, a auditoria global, as decisões do Study 03, o congelamento de `jca` e `e204e2a4` | CARREGADO | FINAL:73 (F10); FINAL:113 (x-A1, x-A2) |
| X-122 | codex:276 | §4 plan | #2 | cor-plano | Substituir "próxima campanha" por um identificador explícito de campanha e um conjunto-alvo admissível | CARREGADO | FINAL:299 (D-I); FINAL:291 (D-A) |
| X-123 | codex:277 | §4 plan | #3 | cor-plano | Distinguir sombra de pareamento (26.152) de sombra de co-localização (32.411) | CARREGADO | FINAL:72 (F9, como 27 % vs 33,4 %); FINAL:296 (D-F) |
| X-124 | codex:278 | §4 plan | #4 | cor-plano | Remover 73,4 %, 28, 3.465× e 3.098 a menos que as definições de classificador/chave sejam publicadas | CARREGADO | FINAL:72 (F9); FINAL:114 (x-A3..A5, x-A26); FINAL:499 (§10 errata) |
| X-125 | codex:279 | §4 plan | #5 | cor-plano | Substituir as citações de completude por FSMMin por `JavaFSM.java:112-142` | CARREGADO | FINAL:110 (x-A6); FINAL:64 (F1); FINAL:496 (§10 errata) |
| X-126 | codex:280 | §4 plan | #6 | cor-plano | Reescrever `condition()` como prólogo de método de evento JavaMOP; não citar `BaseMonitor:604-610` como o mecanismo ativo | CARREGADO | FINAL:111 (x-A7); FINAL:67 (F4); FINAL:496 |
| X-127 | codex:281 | §4 plan | #7 | cor-plano | Usar `getState()`/`getLastEvent()`; reconhecer a perda de pré-estado e a forma de monitor atômica | CARREGADO | FINAL:112 (x-A8); FINAL:66 (F3); FINAL:496-497 |
| X-128 | codex:282 | §4 plan | #8 | cor-plano | Remover a promessa de derivar continuações esperadas em `@fail` sem novo estado | CARREGADO | FINAL:112 (x-A9); FINAL:66 (F3); FINAL:313 (§7.1: `exp` carrega valor, não estado esperado) |
| X-129 | codex:283 | §4 plan | #9 | cor-plano | Remover Cipher no-update/re-init e o construtor de KeyPair da lista de falsos positivos de tradução | CARREGADO | FINAL:117 (x-A11..A13); FINAL:279-282 (§5.3) |
| X-130 | codex:284 | §4 plan | #10 | cor-plano | Atribuir os gêmeos TMF/valores vazios pré-gh100 à colisão de wrapper mais comportamento de root-slice, não a eventos órfãos apenas | CARREGADO | FINAL:74 (F11); FINAL:134 (x-A14) |
| X-131 | codex:285 | §4 plan | #11 | cor-plano | Marcar todo trabalho em `.mop` como inadmissível para o `jca` congelado do Study 03 | CARREGADO | FINAL:83-84 (§3, "No `.mop` edit lands in `jca`") |
| X-132 | codex:286 | §4 plan | #12 | cor-plano | Fundir WS-1/2/3/7 com a §9 da auditoria em vez de abrir um fluxo de reparo concorrente | CARREGADO | FINAL:86-88 (§3, lane C) |
| X-133 | codex:287 | §4 plan | #13 | cor-plano | Substituir identidade por texto livre/hash de objeto por um ID de falha estruturado e limitado | CARREGADO | FINAL:316-319 (§7.1 `code`); FINAL:294 (D-D); FINAL:420 (C-2) |
| X-134 | codex:288 | §4 plan | #14 | prop | Adicionar gramática de mensagem: uma linha, sem `:::`, versão explícita, mensagem por último até a migração de esquema | CARREGADO | FINAL:307-314 (§7.1); FINAL:418 (C-1 "grammar v1") |
| X-135 | codex:289 | §4 plan | #15 | prop | Fazer das mudanças de esquema um delta de contrato OpenSpec cobrindo todo consumidor | CARREGADO | FINAL:347-354 (§7.3); FINAL:444-445 (C-1.5 consumer matrix); FINAL:456 (C-2.3) |
| X-136 | codex:290 | §4 plan | #16 | prop | Reescrever os critérios de aceitação contra o CrySL e traços controlados | CARREGADO | FINAL:378-391 (§7.6); FINAL:128 (x-A21) |
| X-137 | codex:294 | §4 Corrections to the review | #1 | cor-review | Retratar a razão "EventDefinition.condition nunca é atribuído"; provar alcançabilidade do ramo pelo modelo completo JavaMOP→RVM ou marcar como não resolvido | CARREGADO | FINAL:111 (x-B1, "resolved"); FINAL:67 (F4) |
| X-138 | codex:295 | §4 review | #2 | cor-review | Publicar o script de reprodução do CSV e as definições exatas do classificador num diretório de evidência durável | CARREGADO | FINAL:296 (D-F); FINAL:427-432 (C-0) |
| X-139 | codex:296 | §4 review | #3 | cor-review | Graduar a explicação de 8.371/643 como inferência apoiada em artefato, a menos que um replay pré-fix controlado seja executado | CARREGADO | FINAL:74 (F11, "attribution INFERRED pending replay") |
| X-140 | codex:297 | §4 review | #4 | cor-review | Manter a atribuição de SecureRandom 12.400 como `INFERRED`, pendente de G10-SRD-1 ou replay controlado equivalente | CARREGADO | FINAL:140 (x-B4); FINAL:74 (F11); FINAL:505 |
| X-141 | codex:298 | §4 review | #5 | cor-review | Declarar explicitamente que V0/V2 do gh100 prova emissão de descriptor/DEX, não entrega no logcat | CARREGADO | FINAL:146 (x-B5) |
| X-142 | codex:299 | §4 review | #6 | cor-review | Separar "tarefas completas" de "change aceita/arquivada/pronta" | CARREGADO | FINAL:146 (x-B6) |
| X-143 | codex:300 | §4 review | #7 | cor-review | Tratar o contrato de writer/cabeçalho como exato, mas não implicar que seja imutável; ele pode mudar por delta de spec coordenado | CARREGADO | FINAL:146 (x-B7); FINAL:328-330 (§7.1) |
| X-144 | codex:301 | §4 review | #8 | cor-review | Adicionar um formato de transporte versionado como pré-requisito para novas colunas | CARREGADO | FINAL:146 (x-B8); FINAL:307-314 (§7.1) |
| X-145 | codex:307 | §5 New anomalies (tabela, coluna `Finding`) | sem rótulo | anom | A justificativa de código morto do review contradiz o fonte: `EventDefinition.java:150-156` atribui `condition` e o remove do pointcut, logo a razão citada não estabelece deadness — `[tool]` | CARREGADO | FINAL:67 (F4); FINAL:111 (x-B1) |
| X-146 | codex:308 | §5 | sem rótulo | anom | Mensagem rica nula derruba os collectors: logcat `ErrorCollector.java:38`, collector CSV `:42`, construtor não normaliza em `ErrorDescription.java:38-43` — `trim()`/escape em null lança dentro do próprio reporting — `[tool]` | CARREGADO | FINAL:70 (F7, "`null` `expecting` NPEs"); FINAL:119 (x-B11); FINAL:442-443 (C-1.3 null guard) |
| X-147 | codex:309 | §5 | sem rótulo | anom | O escaper restaura o newline removido: ambos os helpers de collector constroem o resultado citado a partir do `data` original, então vírgula/aspa mais newline sobrevive, permitindo injeção/fabricação de registro — `[tool]` | CARREGADO | FINAL:70 (F7, "`\R` replacement discarded when a comma is present"); FINAL:442-443 (C-1.3) |
| X-148 | codex:310 | §5 | sem rótulo | anom | O parser de fallback não tem contador de integridade: `logcat_parser.py:370-372` — registros malformados avisam e desaparecem da contabilidade quantitativa — `[tool]` | CARREGADO | FINAL:70 (F7, "no drop counter"); FINAL:166 (x-C4); FINAL:440-441 (C-1.2) |
| X-149 | codex:311 | §5 | sem rótulo | anom | A identidade de runtime pode colapsar localizações cruas distintas: `ErrorDescriptionTest.java:196-206` documenta parsing de localização não injetivo; frames crus distintos podem virar o mesmo resumo, e o dedupe precede a preservação da evidência crua — `[tool]` | CARREGADO | FINAL:184 (x-C12..C17: "identity non-injective on raw location (`ErrorDescriptionTest:196-206`)") — citado no §4 com destino "—" |
| X-150 | codex:312 | §5 | sem rótulo | anom | A herança de variáveis de root-slice pode tornar diagnósticos obsoletos: o reset do handler não limpa campos arbitrários da spec e eventos sem parâmetro afetam o root slice, então uma mensagem com nome de evento pode ser correta enquanto o valor observado vem de um traço anterior/global — `[jca]/[tool]` | CARREGADO | FINAL:68 (F5); FINAL:184 ("root-slice inheritance") |
| X-151 | codex:313 | §5 | sem rótulo | anom | O discriminador do Format 1 é prosa mutável: `logcat_parser.py:305-306` — mudar o boilerplate muda silenciosamente a rota de parsing — `[tool]` | CARREGADO | FINAL:166 (x-C11, "prose discriminator") |
| X-152 | codex:314 | §5 | sem rótulo | anom | O regenerador de resultados ainda emite dez colunas: `$RVA/scripts/regenerate_results/regenerate_container.py:84,237-246` — arquivos regenerados perdem `source` silenciosamente e violam o contrato atual de onze colunas exatas — `[tool]` | CARREGADO | FINAL:168 (x-C9, caminho e linhas literais); FINAL:352 (§7.3) |
| X-153 | codex:315 | §5 | sem rótulo | anom | A comparação gh91 assume o cabeçalho legado: `$RVA/scripts/gh91_compare_consolidation.py:85-90` — comparações podem normalizar contra um esquema obsoleto — `[tool]` | CARREGADO | FINAL:168 (x-C10); FINAL:352 (§7.3) |
| X-154 | codex:316 | §5 | sem rótulo | anom | O helper de oráculo trunca mensagens `:::`: `$RVA/scripts/rv_oracle_common.py:73-81` retorna só o componente 5 enquanto o gh103 rejeita identidades que não tenham cinco partes, criando oráculos inconsistentes — `[tool]` | CARREGADO | FINAL:168 (x-C8); FINAL:352-353 (§7.3) |
| X-155 | codex:322 | §6 Rung 0 | Rung 0 | prop | Medir as primeiras saídas do Study 03 com ambas as definições de sombra, distribuições por spec, duplicação exata, observações vazias e atribuição app/biblioteca sob um classificador registrado; preservar script, hash de entrada, comando e saída; portão: os resultados reproduzem a partir do pacote de evidência e identificam `jca`, o commit gh100, versões de collector/parser e a semântica do `ExecutionContext` | CARREGADO | FINAL:190 (x-D1.0); FINAL:416, 427-432 (C-0) |
| X-156 | codex:326 | §6 Rung 1 | Rung 1 | prop | Só texto de mensagem; não pode entrar no `jca` congelado durante o Study 03, só num sucessor pós-E3 autorizado; construtor de quatro argumentos; campos: versão, spec estável, ID/nome de evento estável, classe do objeto e valores já escopados; usar `getLastEvent()`, compor antes de `__RESET`, proibir newline/`:::`, omitir hashes de identidade e estado "esperado" | CARREGADO | FINAL:193 (x-D1.1); FINAL:332-343 (§7.2); FINAL:421 (C-3) |
| X-157 | codex:328 | §6 Rung 1 (gate) | Rung 1 gate | prop | Portão: gerar em scratch em disco, compilar o monitor, rodar os testes de `rvsec-core`, rodar um micro-APK controlado apenas via `rv-experiment run`, reparsear o logcat e provar um registro pretendido por traço; registrar as mudanças esperadas de contagem | CARREGADO | FINAL:369 (G-1); FINAL:376 (G-8); FINAL:462 (C-3) |
| X-158 | codex:330 | §6 Rung 1 (formal gate) | Rung 1 formal | prop | Portão formal: extrair o autômato minimizado gerado; verificar que o mapeamento nome-de-evento da mensagem é total e injetivo sobre os IDs de evento declarados; todo traço `@fail` deve emitir um ID de falha estável e não vazio | CARREGADO | FINAL:374 (G-6, injetividade e `code` não vazio) |
| X-159 | codex:334 | §6 Rung 2 | Rung 2 | prop | Introduzir um envelope estruturado versionado (preferir key=value com escaping estrito a JSON-no-logcat até os limites de transporte serem medidos), sentinelas sintéticas explícitas e um ID de falha estruturado na identidade de runtime; corrigir ambos os helpers de escape e o comportamento com null; não habilitar a citação de linha inteira | CARREGADO | FINAL:199 (x-D2, "JSON rejected"); FINAL:307-330 (§7.1); FINAL:418 (C-1), 420 (C-2) |
| X-160 | codex:336 | §6 Rung 2 (gate) | Rung 2 gate | prop | Portão: testes de parser baseados em propriedades sobre vírgulas, aspas, newline, `:::`, Unicode e truncamento; matriz exata de compatibilidade de consumidores; deltas OpenSpec para `INV-CORE-25/41`, `INV-PLT-19`, `INV-ANA-08/46` e gh103 | CARREGADO | FINAL:440-445 (C-1.2/C-1.5, lista idêntica de propriedades); FINAL:71 (F8, as quatro INV); FINAL:347-354 (§7.3) |
| X-161 | codex:340 | §6 Rung 3 | Rung 3 | prop | Reparar só desvios autorizados pela procedência CrySL/api30; prioridades: tipos de retorno de Signature, guarda de KPG, `next2` repetido de SRD, contradições mensagem/condição e itens da §9 da auditoria; não "consertar" o comportamento CrySL-estrito de Cipher/KeyPair sem decisão de oráculo | CARREGADO | FINAL:422, 464-466 (C-4); FINAL:358-361 (§7.4, "CrySL-strictness items are **not** changed") |
| X-162 | codex:344-348 | §6 Rung 3 (formal gates) | Rung 3 formal | prop | Portões formais: traduzir CrySL ORDER e o `.mop` minimizado gerado para um alfabeto comum; checar equivalência onde a semântica é intencionalmente idêntica, senão inclusão na direção registrada; verificar INV-INS-110 (nenhum evento vinculado com linha toda-sink); produzir traços separadores mínimos para cada não-equivalência e executá-los no harness JVM; pontuar mutação da suíte deletando transições e trocando bindings e tipos de retorno | CARREGADO | FINAL:370-373 (G-2, G-3, G-4, G-5) |
| X-163 | codex:352 | §6 Rung 4 | Rung 4 | prop | Resolver identidade versus igualdade após `e204e2a4`; mover checagens de `condition()` para os corpos só junto com transições do autômato, porque um evento de predicado falho recém-emitido pode ele próprio entrar no sink; modelar escritores requeridos, leitores, escopo de remoção e aliasing | CARREGADO | FINAL:297 (D-G); FINAL:423, 468-470 (C-5, "no new orphans, G-2"); FINAL:298 (D-H, "folding/alias") |
| X-164 | codex:354 | §6 Rung 4 (formal gate) | Rung 4 formal | prop | Portão formal: checagem limitada/model checking do produto `autômato × abstração de predicado`; cada aresta REQUIRES tem produtor alcançável ou uma suposição externa explícita; checar ENSURES/NEGATES e identidade de objeto/material separadamente; comparar CogniCrypt e RVSEC nos mesmos micro-APKs | CARREGADO | FINAL:375 (G-7); FINAL:376 (G-8, "CogniCrypt on the same APKs as an external oracle") |
| X-165 | codex:358 | §6 Rung 5 | Rung 5 | prop | Considerar `previousState` emitido pelo gerador, tabelas de nomes de evento, IDs estáveis de site de weave, prefixos de traço e suporte a fim de traço; preferir um manifesto estático por site, unido offline, a caminhadas dinâmicas repetidas na stack | CARREGADO | FINAL:482 (O-1), 483 (O-2), 488 (O-7), 489 (O-8) |
| X-166 | codex:360 | §6 Rung 5 (gate) | Rung 5 gate | prop | Portão: diff do fonte gerado, compilação em ambas as formas de monitor (atômica/sincronizada), benchmark de desempenho/memória, invariantes exatas de mensagem, testes de descriptor/weave do dexlib2 e semântica controlada de morte de processo; fim de traço permanece só protótipo até ser medido | PARCIAL | FINAL:370 (G-2 "both monitor shapes") e FINAL:488 (O-7, "prototype-and-measure only"); benchmark de desempenho/memória e semântica de morte de processo não foram carregados |
| X-167 | codex:364 | §6 Rung 6 | Rung 6 | prop | Reutilizar a conjunção READY da auditoria em vez de inventar um limiar novo, e adicionar propriedades de mensagem: toda violação tem ID estável de evento/falha; modos de falha semanticamente distintos não colidem; mudanças no texto livre não mudam a identidade; totais de supressão reconciliam tentativas emitidas mais suprimidas | CARREGADO | FINAL:391 (§7.6.8, "audit's conjunction + G-6"); FINAL:374 (G-6); FINAL:319; FINAL:390 |
| X-168 | codex:370 | §7 Brainstorming (tabela, sem coluna de ID) | sem rótulo | prop | Envelope key=value versionado — base: lógica posicional do parser e identidade de cinco partes; Medium / C+P / risco de migração; escaping em logcat mais fácil que JSON aninhado | CARREGADO | FINAL:199 (x-D2, "Adopt `key=value` v1"); FINAL:307-314 (§7.1) |
| X-169 | codex:371 | §7 | sem rótulo | prop | IDs de cláusula CrySL como `CIP-ORDER-03` — base: categorias CrySL e procedência da auditoria; Medium / S+C+P / exige mapeamento estável de cláusula gerada | CARREGADO | FINAL:200 (x-D2, "Adopt as the structured id"); FINAL:316-317 (§7.1) |
| X-170 | codex:372 | §7 | sem rótulo | prop | Nomes de evento do gerador + estado anterior — base: tabelas do JavaFSM e pré-estado ausente; Medium / M / afeta todos os consumidores de monitor; remove drift de tabela manual | CARREGADO | FINAL:201 (x-D2); FINAL:482 (O-1) |
| X-171 | codex:373 | §7 | sem rótulo | prop | Prefixo de traço últimos-N por monitor — base: o monitor tem IDs de evento mas não contexto causal; Medium-high / M+C / risco de memória e de valor sensível; guardar só IDs | PARCIAL | FINAL:202 (c-D2.4, d-D2.3 — **sem `x-D2`**) e FINAL:483 (O-2); a ressalva "risco de memória e de valor sensível; guardar só IDs" não foi carregada |
| X-172 | codex:374 | §7 | sem rótulo | prop | Manifesto estático de sites de weave — base: o dexlib2 tem classe/método/callee/índice em escopo; Medium / I+P / joins de ID estável e ofuscação precisam ser desenhados | CARREGADO | FINAL:203 (x-D2); FINAL:489 (O-8) |
| X-173 | codex:375 | §7 | sem rótulo | prop | Chave de dedupe estruturada — base: o texto livre atual está excluído e o hash de objeto é ilimitado; Medium / C+P / a descontinuidade de contagem precisa ser declarada | CARREGADO | FINAL:204 (c-D2.6, d-D1.2 — **sem `x-D2`**); FINAL:294 (D-D, "declare the count discontinuity"); FINAL:420 (C-2) |
| X-174 | codex:376 | §7 | sem rótulo | prop | Supressão com contadores — base: o `HashSet` por processo perde histórico no restart; Medium / C+P / pode esconder rajadas a menos que a contagem suprimida seja de primeira classe | CARREGADO | FINAL:205 (x-D2); FINAL:295 (D-E); FINAL:485 (O-4) |
| X-175 | codex:377 | §7 | sem rótulo | prop | Mapeamento de categorias CogniCrypt (`Typestate`, `RequiredPredicate`, `IncompleteOperation`, constraints); Medium / S+C / equivalência de categoria nem sempre é um-para-um | CARREGADO | FINAL:206 (x-D2, "Adopt partially"); FINAL:324-325 (§7.1) |
| X-176 | codex:378 | §7 | sem rótulo | prop | Gerar autômatos/mensagens a partir do CrySL — base: defeitos repetidos de tradução manual; High / gerador+S / maior retorno de longo prazo, maior carga de validação | CARREGADO | FINAL:207 (x-D2); FINAL:490 (O-9) |
| X-177 | codex:379 | §7 | sem rótulo | prop | Modo de calibração diagnóstica — base: existe o caminho de comportamento interno do RV-Monitor; Medium / M+I / risco de desempenho e volume de log; nunca deve ser o modo padrão de campanha | CARREGADO | FINAL:208 (c-D2.10, d-D2.7 — **sem `x-D2`**); FINAL:483 (O-2, "for calibration runs") |
| X-178 | codex:380 | §7 | sem rótulo | prop | Orçamento de minimização de alfabeto — base: o gh101 mediu grande sensibilidade de custo de geração; Medium / S+ferramental formal / o folding pode esconder eventos semanticamente distintos | PARCIAL | FINAL:210 (c-D2.12 — **sem `x-D2`**) e FINAL:490 (O-9); a ressalva "o folding pode esconder eventos semanticamente distintos" não foi carregada |
| X-179 | codex:384 | §8 Threats to validity | sem rótulo | verif | Este é um validação de primeiro estágio, não uma auditoria final protocolo-completa; seu uso mais forte é bloquear a implementação do plano obsoleto e definir o próximo trabalho de verificação | PARCIAL | FINAL:8-9 (o FINAL de fato supersede o plano); a ressalva "não protocolo-completo" não é carregada — o FINAL cita a ext. 4 sem qualificação |
| X-180 | codex:386 | §8 | sem rótulo | verif | Três subagentes cobriram V1–V9 em grupos de três; os nove passes isolados por dimensão exigidos não foram realizados | AUSENTE | — |
| X-181 | codex:388 | §8 | sem rótulo | verif | Nenhum replay em emulador/dispositivo foi executado; o fechamento runtime do gh100 e a atribuição causal do SecureRandom permanecem não provados | CARREGADO | FINAL:74 (F11); FINAL:146 (x-B5); FINAL:140 (x-B4) |
| X-182 | codex:389 | §8 | sem rótulo | verif | Nenhum monitor foi regenerado; a viabilidade de declaração estática e a estabilidade atual de IDs de evento vieram de fonte/exemplos/artefatos, não de uma geração RVSEC fresca | CARREGADO | FINAL:126 (c-A35, d-B4: "`R` (grammar) / `U` (oracle)"); FINAL:369 (G-1 regenera) |
| X-183 | codex:390 | §8 | sem rótulo | verif | O corpus CrySL api30 foi amostrado em torno das disputas materiais, não readjudicado exaustivamente nas 23 especificações; a auditoria de 558 claims continua sendo o registro mais amplo | PARCIAL | FINAL:138 (c-B4, "review never opened api30 / opened here") e FINAL:271-283 (§5.3); a ressalva de não-exaustividade e a primazia da auditoria de 558 claims não foram carregadas |
| X-184 | codex:391 | §8 | sem rótulo | verif | D01–D50 não foram decididos um a um contra ambos os oráculos CrySL, e os 558 claims / 119 fenômenos da auditoria não foram reproduzidos independentemente | AUSENTE | — |
| X-185 | codex:393 | §8 | sem rótulo | verif | Nenhuma equivalência/inclusão formal, checagem de produto autômato × predicado, análise de mutação ou compilação standalone de monitor foi executada; elas aparecem como portões propostos, não alcançados | CARREGADO | FINAL:365-376 (§7.5, todos como portões a construir em C-V) |
| X-186 | codex:395 | §8 | sem rótulo | verif | Os artefatos de replicação do gh100/gh101 foram inspecionados mas não foram totalmente reconstruídos e comparados por hash nesta sessão | AUSENTE | — |
| X-187 | codex:397 | §8 | sem rótulo | verif | Os comandos de medição do CSV foram efêmeros; uma auditoria final precisa preservar scripts, hashes de entrada, comandos e saídas num pacote de evidência durável | CARREGADO | FINAL:143 (x-B2); FINAL:427-432 (C-0, "with hashes and the exact inputs", "Gate: byte-identical rerun") |
| X-188 | codex:399 | §8 | sem rótulo | verif | As contagens de terceiros/acionabilidade foram intencionalmente não substituídas por outro classificador arbitrário | CARREGADO | FINAL:296 (D-F, "the classifier ships in C-0 as code") |
| X-189 | codex:400 | §8 | sem rótulo | verif | O MCP `sequential-thinking` requisitado estava indisponível | AUSENTE | — |
| X-190 | codex:401 | §8 | sem rótulo | verif | As citações dos subagentes foram tratadas como auxílios de descoberta; o revisor primário reabriu os claims materiais usados na conclusão executiva, mas não toda entrada periférica do ledger da auditoria | AUSENTE | — |
| X-191 | codex:402 | §8 | sem rótulo | verif | O estado não commitado atual do repositório pode diferir dos commits descritos por documentos históricos; a procedência Git foi usada para história, o fonte atual para afirmações no presente | AUSENTE | — |
| X-192 | codex:406 | §8 Work required | #1 | prop | Rodar nove passes isolados V1–V9 e preservar cada ledger de evidência com citações `file:line` absolutas | AUSENTE | — |
| X-193 | codex:408 | §8 Work required | #2 | prop | Publicar scripts, hashes, definições e saídas duráveis de reprodução do CSV, incluindo o classificador de atribuição | CARREGADO | FINAL:296 (D-F); FINAL:427-432 (C-0.1/C-0.2) |
| X-194 | codex:410 | §8 Work required | #3 | prop | Readjudicar cada alegação material de falso positivo/defeito contra o CrySL original e o api30, contabilizando explicitamente a divergência de oráculo | CARREGADO | FINAL:271-283 (§5.3, ambos os oráculos); FINAL:292 (D-B); FINAL:422 (C-4) |
| X-195 | codex:412 | §8 Work required | #4 | prop | Gerar e compilar os monitores relevantes em scratch em disco, tanto standalone quanto merged, e validar as formas atômica e sincronizada | PARCIAL | FINAL:369 (G-1 compila `MultiSpec_1RuntimeMonitor.java` — só o merged) e FINAL:370 (G-2 "both monitor shapes"); o caso standalone não foi carregado |
| X-196 | codex:414 | §8 Work required | #5 | prop | Reexecutar os traços JVM decisivos da auditoria e construir o corpus diferencial/de mutação faltante | CARREGADO | FINAL:372-373 (G-4, G-5); FINAL:450 (C-V.5, "the audit's separating traces as first cases") |
| X-197 | codex:415 | §8 Work required | #6 | prop | Rematerializar e checar por hash os caminhos de evidência relevantes do gh100/gh101 | AUSENTE | — |
| X-198 | codex:416 | §8 Work required | #7 | prop | Executar o replay G10 autorizado através de `rv-experiment`/`rv-platform` para decidir a causalidade runtime histórica, especialmente SecureRandom e a chegada no logcat pós-gh100 | PARCIAL | FINAL:74 (F11, "pending replay") e FINAL:140; nenhuma change do §8 agenda o replay G10 — ele não vira C-n nem opção O-n |
| X-199 | codex:418 | §8 Work required | #8 | prop | Consolidar contradições numa segunda revisão do relatório; só então emitir uma opinião protocolo-completa | AUSENTE | — |
| X-200 | codex:469-474 | §10 Final opinion | sem rótulo | prop | A evidência é suficiente para uma decisão imediata: o problema de mensagem é real e severo, mas o plano não deve ser implementado como escrito, e "substituir `unknown`" ainda não é a primeira mudança segura de código; primeiro preservar um baseline pós-gh100 e explicitar o contrato de reporting, depois adicionar identidade de falha estruturada e limitada e texto com evento num conjunto sucessor autorizado, junto com checagens formais de autômato e predicado | CARREGADO | FINAL:403-412 (§8, escada C-0 → C-1 → C-2/C-3/C-4/C-5); FINAL:291 (D-A) |
| X-201 | codex:476-478 | §10 | sem rótulo | prop | O plano deve ser reescrito em torno dessa sequência; o review adversarial deve ser retido como o registro principal de correção, emendado para rebaixar suas inferências causais, preservar seus scripts de medição e corrigir a alegação sobre `EventDefinition.condition` | CARREGADO | FINAL:494-506 (§10 errata, incluindo "scripts must be durable" e a correção do `condition`) |
| X-202 | codex:478-480 | §10 | sem rótulo | verif | Este relatório não deve ser citado como certificação completa de nenhum dos documentos nem de nenhum dos conjuntos JavaMOP até que os oito itens de conclusão da §8 tenham sido executados | AUSENTE | — |

---

## Itens AUSENTES, em detalhe

São 20. Sete são de conteúdo técnico/quantitativo com consequência direta; treze são ressalvas de
método e de escopo do relatório (várias delas também com consequência, porque são exatamente o que
limita o uso do relatório).

### Conteúdo técnico e quantitativo

1. **X-083 — `codex:207` — política de escopo de instrumentação divergente.**
   "As exclusões de descriptor omitem namespaces comuns de Android/Kotlin/Google/okhttp; a cobertura
   tem um filtro divergente — divisão de política confirmada." Nenhum equivalente no FINAL. As duas
   ocorrências de `okio.` (FINAL:114 e FINAL:296) são do classificador de *terceiros* proposto pela
   ext. 1 para o D-F, um objeto diferente: o item do codex é sobre o que o **weaver** exclui versus
   o que a **cobertura** filtra. **Por que importa:** é a única anomalia da §5/§3 do codex que
   sobreviveu como um achado independente e desapareceu inteira; ela afeta o denominador de qualquer
   número de C-0 (o que foi instrumentado ≠ o que foi contado) e nenhuma change do §8 nem opção do
   §9 a endereça.

2. **X-053 — `codex:159` — funil 661 → 207 → 136.** O codex mediu independentemente o funil
   `(apk,spec,class,method,message)` distintos → remover unknown → vazios encontrados. O FINAL
   registra apenas "funnel 24–59 by definition" (FINAL:114), que é o número da ext. 1 para um
   *outro* estágio. **Por que importa:** o §4 do FINAL fecha esse grupo com "definitions differ per
   report — treat as 'publish the classifier'", o que apaga o fato de que o codex tinha uma medição
   completa e reprodutível dos três primeiros estágios, independente do classificador em disputa.

3. **X-054 — `codex:160` — 85.257 chaves exatas de dez colunas.** Não consta.
   **Por que importa:** é a linha-base contra a qual o "excesso de duplicação" e o "maior grupo = 6"
   (esse sim carregado, F9) fazem sentido. Sem ela, o único número de duplicação que sobrevive no
   FINAL é o "6", que é o *máximo*, não a *massa*.

4. **X-055 — `codex:161` — excesso de duplicação 11.761 (soma de `tamanho do grupo − 1`).**
   **Por que importa:** o C-0 (FINAL:427-432) manda medir "exact duplication" mas não herda nem o
   valor nem a definição operacional já calculada pelo codex; o item D-D fala em "declare the count
   discontinuity" sem um número de partida.

5. **X-057 — `codex:163` — 8.843 linhas cuja mensagem termina em `but found .`.**
   O FINAL só carrega 8.371 (F11, número do review para o estrato atribuído à colisão pré-gh100) e
   98 residuais no E3 (FINAL:128). **Por que importa:** 8.843 e 8.371 são medições do mesmo fenômeno
   no mesmo dataset com valores diferentes; ao carregar só um dos dois, o FINAL elimina uma
   discrepância de 472 linhas que era um contraexemplo direto à alegação de que a colisão de wrapper
   explica *todos* os valores vazios — precisamente o ponto que o próprio codex derruba em X-010.

6. **X-186 / X-197 — `codex:395` e `codex:415` — os artefatos de replicação do gh100/gh101 não
   foram reconstruídos nem comparados por hash, e fazê-lo é item de trabalho obrigatório.**
   O C-0 exige rerun byte-idêntico dos scripts do E3, mas nada no FINAL exige rematerializar e
   conferir por hash a evidência gh100/gh101. **Por que importa:** F10, F11 e a decisão D-C
   ("mesmo pé do gh100") repousam sobre artefatos gh100/gh101 lidos, não verificados.

7. **X-184 — `codex:391` — D01–D50 não foram decididos um a um contra ambos os oráculos, e os 558
   claims / 119 fenômenos da auditoria não foram reproduzidos.** **Por que importa:** o C-4
   (FINAL:422) escala "D11, D18–D20, D35–D40" como se a adjudicação estivesse feita; a ressalva de
   que a readjudicação por item ainda não ocorreu não sobreviveu.

### Ressalvas de método e de escopo do relatório

8. **X-001 (`codex:7-13`)** e **X-202 (`codex:478-480`)** — a moldura do relatório: é validação de
   primeiro estágio, não protocolo completo, e **não deve ser citado como certificação** até os oito
   itens da §8 serem executados. O FINAL o cita como "external validation 4 (480 lines)" (FINAL:22)
   e usa seus vereditos como `R`/`V+` sem essa qualificação. **Por que importa:** é a instrução
   explícita de uso que o relatório dá sobre si mesmo, e ela foi descartada.

9. **X-017 (`codex:61-73`)**, **X-180 (`codex:386`)** e **X-192 (`codex:406`)** — o desvio de
   protocolo (três subagentes × três dimensões em vez de nove passes isolados) e a exigência de
   rodar os nove passes isolados antes de declarar o protocolo completo. Ausentes.

10. **X-018 (`codex:75`)** — concordância entre passes usada só para selecionar checagens
    discriminantes, nunca como prova. Ausente. **Por que importa:** o FINAL faz o oposto no §2, onde
    F1/F7/F9/F10 são creditados a "ext. 1–4" — concordância entre relatórios usada como reforço.

11. **X-019 (`codex:77-85`)** e **X-189 (`codex:400`)** — o MCP `sequential-thinking` estava
    indisponível, não foi simulado, e foi substituído por um log científico explícito por decisão.

12. **X-190 (`codex:401`)** — as citações dos subagentes foram tratadas como auxílio de descoberta;
    entradas periféricas do ledger da auditoria não foram reabertas pelo revisor primário.

13. **X-191 (`codex:402`)** — o estado não commitado do repositório pode divergir dos commits
    descritos nos documentos históricos; procedência Git para história, fonte atual para o presente.
    **Por que importa:** todos os fatos F1–F14 do FINAL são afirmações no presente sobre uma árvore
    suja, e essa ressalva metodológica não aparece em lugar nenhum do FINAL.

14. **X-044 (`codex:143`)** — "a cobertura amostral excedeu quarenta localizações reabertas".
    Métrica de esforço, ausente.

15. **X-199 (`codex:418`)** — consolidar contradições numa segunda revisão do relatório antes de
    emitir opinião protocolo-completa.

---

## Itens PARCIAIS, em detalhe

São 16.

- **X-020 (`codex:87`)** — carregado o "nenhum emulador gerenciado à mão" (FINAL:89, que aliás é
  regra própria do projeto); perdida a ressalva de que o repositório já estava muito sujo e todas as
  mudanças pré-existentes foram preservadas.
- **X-021 (`codex:89-100`)** — das sete atividades declaradamente não realizadas, quatro sobrevivem
  como portões propostos no §7.5 e no C-0; três não (ver X-184, X-186 e o replay G10 em X-198).
- **X-022 (`codex:105-111`)** — das cinco classes de evidência, só `INFERRED` sobrevive
  (FINAL:74). O FINAL substitui a taxonomia pelo seu próprio esquema `R`/`V+`/`V−`/`V±`/`U`
  (FINAL:103), que é sobre *quem verificou*, não sobre *o que é a evidência*; `PROVEN`,
  `MEASURED`, `OBSERVED_IN_ARTIFACT` e `NOT_VERIFIED` não aparecem no FINAL.
- **X-042 (`codex:140`)** — `ViolationRecorder.java:53-59` retorna `relevantStack.get(0)`, isto é,
  a localização dinâmica guarda **um único** quadro. O FINAL carrega o custo (`new Exception()` por
  tentativa, F6 e "getStack per attempt" em FINAL:184) e o problema adjacente do callee ausente
  (c-C36, FINAL:180), mas nunca declara a retenção de um quadro só, que é o que limita O-8.
- **X-050 / X-051 (`codex:156-157`)** — as duas definições de sombra sobrevivem como percentuais
  (27 % e 33,4 %, FINAL:72); os valores absolutos 26.152 e 32.411 e a chave de agrupamento
  `(apk,rep,tool,spec,class,method)` não.
- **X-052 (`codex:158`)** — sobrevive só a ressalva "`time` is seconds" (FINAL:72). Os três
  quantitativos por chave temporal (46.330 grupos, 20.507 mistos, 32.232 unknown em grupos mistos)
  e a advertência de que "evento" é mais forte do que a resolução do timestamp prova não sobrevivem
  com números.
- **X-080 (`codex:204`)** — "nove eventos descartados" está em F10; "oito emissores de erro" não.
- **X-086 (`codex:211`)** — O-8 carrega o manifesto estático e a preservação de itens de debug, mas
  não as duas condições de projeto do codex (ID estável entre instrumentações; joins que não
  dependam de tabelas de linha removidas).
- **X-166 (`codex:360`)** — do portão do Rung 5 sobrevivem "ambas as formas de monitor" (G-2) e
  "protótipo até medir" (O-7); benchmark de desempenho/memória e semântica controlada de morte de
  processo não sobrevivem.
- **X-171 (`codex:373`)** e **X-178 (`codex:380`)** — ver a seção seguinte: conteúdo presente, mas
  sem a ressalva de risco e sem atribuição `x-D2`.
- **X-179 (`codex:384`)** — o FINAL de fato bloqueia o plano (FINAL:8-9), que era o "uso mais forte"
  declarado; a qualificação "não é auditoria protocolo-completa" não sobrevive.
- **X-183 (`codex:390`)** — o FINAL abriu o api30 (c-B4, §5.3), o que era o pedido; mas a ressalva
  de que a amostragem foi em torno das disputas materiais e não exaustiva sobre as 23 specs, e de
  que a auditoria de 558 claims continua sendo o registro mais amplo, não sobrevive.
- **X-195 (`codex:412`)** — G-1 compila só o `MultiSpec_1RuntimeMonitor.java` (merged); o caso
  standalone pedido pelo codex não entra no portão. G-2 cobre as duas formas de monitor.
- **X-198 (`codex:416`)** — F11 e o errata mantêm o SRD 12.400 como `INFERRED` "pending replay",
  mas nenhuma das changes C-0..C-5 nem das opções O-1..O-9 agenda o replay G10 que decidiria a
  causalidade histórica.

---

## As anomalias sem ID da §5 e as ideias sem ID da §7, uma a uma

### §5 — as 10 anomalias da tabela `Finding` (`codex:307-316`)

A tabela não tem coluna de ID, então nenhuma delas é citável por rótulo próprio; o casamento abaixo
é 100 % por conteúdo. **Veredito: as 10 foram carregadas.** É o resultado oposto ao caso gemini.
Sete delas aparecem no §4 com o caminho e as linhas de código literais, o que só é possível se o
extrator tiver lido a tabela linha a linha.

| # | linha | anomalia | onde no FINAL | observação |
|---|---|---|---|---|
| 1 | 307 | racional de código morto do review contradiz o fonte (`EventDefinition.java:150-156`) | FINAL:111 (`x-B1`, "resolved"), FINAL:67 (F4) | carregada e **adjudicada** — o FINAL fecha os dois lados |
| 2 | 308 | mensagem rica nula derruba os collectors (`ErrorCollector.java:38`, CSV `:42`, `ErrorDescription.java:38-43`) | FINAL:70 (F7), FINAL:119 (`x-B11`), FINAL:442 (C-1.3) | carregada; o FINAL comprime para "`null` `expecting` NPEs" |
| 3 | 309 | escaper restaura o newline removido, permitindo injeção de registro | FINAL:70 (F7), FINAL:442 (C-1.3) | carregada; o FINAL usa a formulação do review ("`\R` replacement discarded when a comma is present") |
| 4 | 310 | parser de fallback sem contador de integridade (`logcat_parser.py:370-372`) | FINAL:70 (F7), FINAL:166 (`x-C4`), FINAL:440 (C-1.2) | carregada |
| 5 | 311 | identidade colapsa localizações cruas distintas (`ErrorDescriptionTest.java:196-206`) | FINAL:184 (`x-C12..C17`) | carregada **só no §4**, com destino "—": não entra em nenhuma seção de decisão |
| 6 | 312 | herança de variável de root-slice torna diagnósticos obsoletos | FINAL:68 (F5), FINAL:184 | carregada |
| 7 | 313 | discriminador do Format 1 é prosa mutável (`logcat_parser.py:305-306`) | FINAL:166 (`x-C11`) | carregada |
| 8 | 314 | regenerador ainda emite dez colunas (`regenerate_container.py:84,237-246`) | FINAL:168 (`x-C9`), FINAL:352 (§7.3) | carregada com caminho e linhas literais |
| 9 | 315 | comparação gh91 assume cabeçalho legado (`gh91_compare_consolidation.py:85-90`) | FINAL:168 (`x-C10`), FINAL:352 | carregada com caminho e linhas literais |
| 10 | 316 | helper de oráculo trunca mensagens `:::` (`rv_oracle_common.py:73-81`) | FINAL:168 (`x-C8`), FINAL:352-353 | carregada com caminho e linhas literais |

Ressalva única: a anomalia 5 é citada no §4 mas o campo "→" é "—", isto é, o FINAL registra que ela
existe e não lhe dá destino. Ela não vira tarefa em nenhuma change nem opção. Isso não é perda de
transporte, é perda de disposição.

### §7 — as 11 ideias de brainstorming (`codex:370-380`) e o token `x-D2`

O `x-D2` é usado **7 vezes** no §4.3 do FINAL (linhas 199, 200, 201, 203, 205, 206, 207) para cobrir
11 ideias. A suspeita de compressão com perda se confirma **parcialmente**: as 11 ideias estão todas
presentes por conteúdo no FINAL, mas **4 delas chegam lá sem atribuição ao codex** (viajam de carona
nos itens `c-D2.*` / `d-D2.*`), e **2 perdem a ressalva de risco** que era a contribuição própria do
codex (a coluna "Cost / radius / risk", que nenhum outro relatório tem nesse formato).

| # | linha | ideia | `x-D2` citado? | conteúdo no FINAL | ressalva de risco preservada? |
|---|---|---|---|---|---|
| 1 | 370 | envelope key=value versionado | **sim** (FINAL:199) | §7.1 envelope `v=1`, JSON rejeitado | sim (o FINAL justifica a rejeição do JSON pelo parser posicional) |
| 2 | 371 | IDs de cláusula CrySL (`CIP-ORDER-03`) | **sim** (FINAL:200) | §7.1 `code`, `codes.csv` por conjunto | sim (mapeamento estável vira o `codes.csv` cross-checado na geração) |
| 3 | 372 | nomes de evento do gerador + estado anterior | **sim** (FINAL:201) | O-1 | sim (O-1 é opção, com gatilho) |
| 4 | 373 | prefixo de traço últimos-N por monitor | **não** (FINAL:202 cita só `c-D2.4, d-D2.3`) | O-2 | **não** — "risco de memória e de valor sensível; guardar só IDs" desapareceu |
| 5 | 374 | manifesto estático de sites de weave | **sim** (FINAL:203) | O-8 | parcial — "joins de ID estável e ofuscação precisam ser desenhados" não sobrevive (ver X-086) |
| 6 | 375 | chave de dedupe estruturada | **não** (FINAL:204 cita só `c-D2.6, d-D1.2`) | C-2, D-D | sim — a descontinuidade de contagem está em D-D |
| 7 | 376 | supressão com contadores | **sim** (FINAL:205) | O-4, D-E, §7.6.7 | sim — "contagem suprimida de primeira classe" está em D-E |
| 8 | 377 | mapeamento de categorias CogniCrypt | **sim** (FINAL:206) | §7.1 (`RequiredPredicate`, `ForbiddenMethod` em C-5) | sim — "adopt partially", equivalência não é um-para-um |
| 9 | 378 | gerar autômatos/mensagens do CrySL via MetaCrySL | **sim** (FINAL:207) | O-9 | sim — "option (long term)" |
| 10 | 379 | modo de calibração diagnóstica (`--internalbehavior`) | **não** (FINAL:208 cita só `c-D2.10, d-D2.7`) | O-2 | sim — O-2 é explicitamente "for calibration runs" |
| 11 | 380 | orçamento de minimização de alfabeto | **não** (FINAL:210 cita só `c-D2.12`) | O-9 | **não** — "o folding pode esconder eventos semanticamente distintos" desapareceu |

**Veredito sobre o `x-D2`:** 11 ideias entram, 11 saem por conteúdo, 7 saem com atribuição. Não há
ideia perdida; há atribuição perdida em 4 casos e ressalva de risco perdida em 2 (ideias 4 e 11,
mais parcialmente a 5). O token único `x-D2` é, portanto, um problema de rastreabilidade, não de
transporte: quem for refazer a consolidação contra os originais (como o próprio FINAL:30 manda) não
consegue saber, pelo §4, que o codex propôs as ideias 4, 6, 10 e 11.

### Sobre os tamanhos de `x-A`, `x-B` e `x-C`

O §4 do FINAL cita até `x-A27`, `x-B11` e `x-C18`. Isso é **coerente** com a fonte, contra a
primeira impressão: as §4 e §5 do codex têm apenas 16 + 8 + 10 itens numerados, mas as classes A/B/C
da passagem de extração se alimentam de todo o §3 (as 21 linhas de V1, 13 de V2, 12 de V3, 6 de V4,
7 de V5, 7 de V6, 9 de V7, mais V8 e V9), onde estão dezenas de correções e anomalias adicionais.
Minha enumeração encontra, nas classes correspondentes, 55 itens `cor-plano`, 21 `cor-review` e 22
`anom` — folga confortável para 27/11/18. **Nenhum ID alto é fantasma.**

O que a numeração revela é outra coisa: cinco IDs da faixa A — `x-A15`, `x-A18`, `x-A19`, `x-A20` e
`x-A24` — nunca são citados em lugar nenhum do §4, enquanto `x-B1..B11` e `x-C1..C18` aparecem
todos. Cinco lacunas contíguas ao lado de uma faixa `x-C` completa é consistente com os cinco itens
de conteúdo que o casamento por conteúdo encontrou desaparecidos das medições do V2 e do V5
(X-053, X-054, X-055, X-057, X-083) — todos itens que a extração classificaria como correções ao
plano. Não é prova, mas é a leitura mais econômica dos dois sinais.
